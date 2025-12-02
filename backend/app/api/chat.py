from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Tuple
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.chat import ChatSession, ChatMessage
from app.services.rag_service import rag_service
from app.services.mcp_service import mcp_service
from app.services.document_generator import DocumentGenerator
import re
import json
import logging
import base64

logger = logging.getLogger(__name__)

router = APIRouter()

class ChatMessageRequest(BaseModel):
    model_config = {"protected_namespaces": ()}  # Disable protected namespace warning for model_id
    
    message: str
    session_id: Optional[int] = None
    model_id: Optional[str] = "auto"  # Model selection: "auto" or specific model ID
    content_type: Optional[str] = None  # Content type: "doc", "ppt", "mp4", "podcast", "speech"

class ChatMessageResponse(BaseModel):
    message_id: int
    role: str
    content: str
    metadata: Optional[Dict[str, Any]] = None

def _format_rag_as_video_script(rag_content: str, topic: str = "") -> Tuple[str, bool]:
    """
    Format RAG content into a video script suitable for narration
    Limits script to 180 seconds (3 minutes) maximum
    
    Args:
        rag_content: The RAG-generated content
        topic: The topic/title of the video
    
    Returns:
        Tuple of (formatted script text, was_truncated)
    """
    import re
    
    # Remove markdown formatting, URLs, and citations
    script = rag_content
    
    # Remove markdown links [text](url) -> text
    script = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', script)
    
    # Remove URLs
    script = re.sub(r'https?://[^\s]+', '', script)
    
    # Remove citation markers like [1], (Source: ...), etc.
    script = re.sub(r'\[(\d+)\]', '', script)
    script = re.sub(r'\(Source:[^\)]+\)', '', script)
    script = re.sub(r'Sources?:[^\n]+', '', script, flags=re.IGNORECASE)
    
    # Remove excessive line breaks
    script = re.sub(r'\n{3,}', '\n\n', script)
    
    # Clean up whitespace
    script = ' '.join(script.split())
    
    # Add a brief introduction if topic is provided
    if topic:
        intro = f"Today, we'll explore {topic}. "
        script = intro + script
    
    # Limit to 120 seconds (2 minutes) maximum
    # Using 150 words per minute as average speaking rate
    # 120 seconds = 2 minutes = 300 words maximum
    # But to be safe, we'll use 280 words to account for pauses and variations
    words = script.split()
    was_truncated = False
    
    if len(words) > 280:
        script = ' '.join(words[:280])
        was_truncated = True
        # Add a natural ending
        if not script.endswith(('.', '!', '?')):
            script += "."
    
    return script.strip(), was_truncated

def detect_agent_intent(message: str) -> Optional[Dict[str, Any]]:
    """Detect if message requires an agent call"""
    message_lower = message.lower()
    
    # Check for PTO/leave requests
    if any(keyword in message_lower for keyword in ["pto", "leave", "vacation", "sick leave", "time off"]):
        if "check" in message_lower or "available" in message_lower or "balance" in message_lower:
            return {"agent": "check_pto", "params": {}}
        elif "submit" in message_lower or "request" in message_lower:
            # Try to extract dates
            date_pattern = r'\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4}'
            dates = re.findall(date_pattern, message)
            return {
                "agent": "submit_leave",
                "params": {
                    "start_date": dates[0] if len(dates) > 0 else None,
                    "end_date": dates[1] if len(dates) > 1 else None
                }
            }
    
    # Check for video mentions - always check demo videos first, then offer HeyGen if none found
    # Also check for phrases that indicate video generation intent (even without "video" keyword)
    video_keywords = ["video", "generate video", "create video", "make video", "produce video"]
    script_to_video_phrases = ["use that script", "use this script", "use the script", "generate from script", "create from script", "make from script"]
    
    has_video_keyword = any(keyword in message_lower for keyword in video_keywords)
    has_script_phrase = any(phrase in message_lower for phrase in script_to_video_phrases)
    
    if has_video_keyword or has_script_phrase:
        # Extract topic from message
        topic = re.sub(r'\b(i want to|show|watch|see|demo|video|a|the|me|i|need|please|that|about|for|to|generate|create|make|help me|use|script|from)\b', '', message_lower, flags=re.IGNORECASE)
        topic = ' '.join(topic.split()).strip()
        if len(topic) < 3:
            topic = message
        
        # Check if user explicitly wants to generate (skip demo check in this case)
        explicit_generate = any(phrase in message_lower for phrase in [
            "generate", "create", "make", "produce", "use that script", "use this script", "use the script"
        ]) or has_script_phrase
        
        # Always use video_generate agent - it will check demo videos first, then HeyGen if needed
        logger.info(f"Detected video request. Topic: {topic}, Explicit generate: {explicit_generate}")
        return {
            "agent": "video_generate", 
            "params": {
                "topic": topic, 
                "description": message,
                "force_generate": explicit_generate  # Flag to skip demo check if explicitly generating
            }
        }
    
    # Check for podcast creation
    if any(keyword in message_lower for keyword in ["create podcast", "make podcast", "generate podcast", "podcast"]):
        # Extract topic from message
        topic = re.sub(r'\b(i want to|generate|create|make|a|the|me|i|need|please|that|about|for|to|podcast)\b', '', message_lower, flags=re.IGNORECASE)
        topic = ' '.join(topic.split()).strip()
        if len(topic) < 3:
            topic = message
        return {"agent": "create_podcast", "params": {"topic": topic, "description": message}}
    
    # Check for PPT creation
    if any(keyword in message_lower for keyword in ["create ppt", "make presentation", "generate ppt", "powerpoint"]):
        return {"agent": "create_ppt", "params": {"description": message}}
    
    # Check for report generation
    if any(keyword in message_lower for keyword in ["generate report", "create report", "build report"]):
        return {"agent": "generate_report", "params": {"description": message}}
    
    return None

@router.post("/message")
async def send_message(
    request: ChatMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get or create session
    if request.session_id:
        session = db.query(ChatSession).filter(
            ChatSession.id == request.session_id,
            ChatSession.user_id == current_user.id
        ).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found"
            )
    else:
        session = ChatSession(user_id=current_user.id, title=request.message[:50])
        db.add(session)
        db.commit()
        db.refresh(session)
    
    # Save user message
    user_message = ChatMessage(
        session_id=session.id,
        role="user",
        content=request.message
    )
    db.add(user_message)
    db.commit()
    
    # Detect agent intent - prioritize content_type if provided
    agent_intent = None
    if request.content_type:
        # Map content_type to agent intent
        # Note: "mp4" can mean either search (create_video) or generate (video_generate)
        # For "mp4", we need to check message content to distinguish between search and generate
        if request.content_type == "mp4":
            # Let detect_agent_intent decide based on message content
            agent_intent = detect_agent_intent(request.message)
            # If detect_agent_intent didn't find anything, default to search
            if not agent_intent:
                agent_intent = {"agent": "create_video", "params": {"topic": request.message, "description": request.message}}
        else:
            content_type_map = {
                "doc": "create_doc",
                "ppt": "create_ppt",
                "podcast": "create_podcast",
                "speech": "create_speech"
            }
            agent_name = content_type_map.get(request.content_type)
            if agent_name:
                agent_intent = {
                    "agent": agent_name,
                    "params": {"description": request.message, "content_type": request.content_type}
                }
    
    # Fall back to text-based detection if no content_type provided or no agent found
    if not agent_intent:
        agent_intent = detect_agent_intent(request.message)
    
    metadata = {}
    
    if agent_intent:
        # For PowerPoint generation, use RAG to get content and show it as normal response
        # User can then confirm to generate PowerPoint from that response
        if agent_intent["agent"] == "create_ppt":
            # Get conversation history for context
            conversation_history = []
            if session.id:
                previous_messages = db.query(ChatMessage).filter(
                    ChatMessage.session_id == session.id
                ).order_by(ChatMessage.created_at.asc()).all()
                conversation_history = [
                    {
                        "role": msg.role, 
                        "content": msg.content,
                        "metadata": msg.message_metadata or {}
                    }
                    for msg in previous_messages
                ]
            
            # Use RAG to get content - show as normal response
            try:
                # Clean the message - remove agent trigger words to get the actual topic
                clean_message = request.message
                for trigger in ["create ppt", "make presentation", "generate ppt", "powerpoint", "create a", "make a", "generate a"]:
                    clean_message = clean_message.lower().replace(trigger, "").strip()
                if not clean_message:
                    clean_message = request.message
                
                rag_result = rag_service.query(
                    clean_message, 
                    current_user.role.value,
                    model_id=request.model_id,
                    conversation_history=conversation_history,
                    content_type=request.content_type
                )
                
                # Use RAG answer as the normal assistant response
                assistant_content = rag_result["answer"]
                metadata["sources"] = rag_result.get("sources", [])
                
                # Store PowerPoint generation metadata for confirmation button
                metadata["ppt_generation"] = {
                    "topic": clean_message[:100],
                    "session_id": session.id,
                    "template_id": agent_intent["params"].get("template_id")
                }
                logger.info(f"RAG content extracted for PowerPoint generation: {len(assistant_content)} chars")
            except Exception as rag_error:
                # If RAG fails, use the message as content
                logger.warning(f"RAG failed for PPT generation: {rag_error}, using message as content")
                assistant_content = request.message
                metadata["ppt_generation"] = {
                    "topic": request.message[:100],
                    "session_id": session.id,
                    "template_id": agent_intent["params"].get("template_id")
                }
        elif agent_intent["agent"] == "create_podcast":
            # For podcast generation, generate script first, then offer button to generate MP3
            try:
                # Get conversation history for context
                conversation_history = []
                if session.id:
                    previous_messages = db.query(ChatMessage).filter(
                        ChatMessage.session_id == session.id
                    ).order_by(ChatMessage.created_at.asc()).all()
                    conversation_history = [
                        {
                            "role": msg.role, 
                            "content": msg.content,
                            "metadata": msg.message_metadata or {}
                        }
                        for msg in previous_messages
                    ]
                
                # Clean the message - remove agent trigger words to get the actual topic
                clean_message = request.message
                for trigger in ["create podcast", "make podcast", "generate podcast", "create a podcast", "make a podcast", "generate a podcast", "podcast"]:
                    clean_message = clean_message.lower().replace(trigger, "").strip()
                if not clean_message:
                    clean_message = request.message
                
                # Get RAG content for the podcast
                rag_result = rag_service.query(
                    clean_message, 
                    current_user.role.value,
                    model_id=request.model_id,
                    conversation_history=conversation_history,
                    content_type=request.content_type
                )
                
                rag_content = rag_result["answer"]
                metadata["sources"] = rag_result.get("sources", [])
                
                # Generate only the podcast dialogue script (not MP3 yet)
                try:
                    generator = DocumentGenerator()
                    topic = agent_intent["params"].get("topic", clean_message[:100])
                    
                    # Generate dialogue script only
                    dialogue_script = await generator.generate_podcast_script(
                        content=rag_content,
                        user_context={
                            "user_id": current_user.id,
                            "role": current_user.role.value,
                            "full_name": current_user.full_name
                        },
                        topic=topic
                    )
                    
                    # Store podcast metadata for button generation
                    metadata["podcast_generation"] = {
                        "topic": topic[:100],
                        "session_id": session.id,
                        "script": dialogue_script,
                        "ready_for_mp3": True  # Flag to show generate MP3 button
                    }
                    
                    assistant_content = f"I've created a podcast script about {topic}:\n\n{dialogue_script}"
                    logger.info(f"Podcast script generated for topic: {topic}")
                    
                except Exception as gen_error:
                    logger.error(f"Failed to generate podcast script: {gen_error}", exc_info=True)
                    # Fallback: show content with manual generation option
                    assistant_content = rag_content
                    metadata["podcast_generation"] = {
                        "topic": clean_message[:100],
                        "session_id": session.id,
                        "ready_for_mp3": False,
                        "error": str(gen_error)
                    }
                    
            except Exception as rag_error:
                logger.warning(f"RAG failed for podcast generation: {rag_error}, using message as content")
                assistant_content = request.message
                metadata["podcast_generation"] = {
                    "topic": request.message[:100],
                    "session_id": session.id,
                    "ready_for_mp3": False,
                    "error": str(rag_error)
                }
        elif agent_intent["agent"] == "create_doc":
            # For document generation, use RAG to get content and show it as normal response
            # User can then generate document from that response
            try:
                # Get conversation history for context
                conversation_history = []
                if session.id:
                    previous_messages = db.query(ChatMessage).filter(
                        ChatMessage.session_id == session.id
                    ).order_by(ChatMessage.created_at.asc()).all()
                    conversation_history = [
                        {
                            "role": msg.role, 
                            "content": msg.content,
                            "metadata": msg.message_metadata or {}
                        }
                        for msg in previous_messages
                    ]
                
                # Clean the message - remove agent trigger words to get the actual topic
                clean_message = request.message
                for trigger in ["create doc", "make document", "generate doc", "generate document", "create document", "doc", "document"]:
                    clean_message = clean_message.lower().replace(trigger, "").strip()
                if not clean_message:
                    clean_message = request.message
                
                rag_result = rag_service.query(
                    clean_message, 
                    current_user.role.value,
                    model_id=request.model_id,
                    conversation_history=conversation_history,
                    content_type=request.content_type
                )
                
                # Use RAG answer as the normal assistant response
                assistant_content = rag_result["answer"]
                metadata["sources"] = rag_result.get("sources", [])
                
                # Store document generation metadata for generation button
                metadata["doc_generation"] = {
                    "topic": clean_message[:100],
                    "session_id": session.id,
                    "ready_for_doc": True
                }
                logger.info(f"RAG content extracted for document generation: {len(assistant_content)} chars")
            except Exception as rag_error:
                # If RAG fails, use the message as content
                logger.warning(f"RAG failed for document generation: {rag_error}, using message as content")
                assistant_content = request.message
                metadata["doc_generation"] = {
                    "topic": request.message[:100],
                    "session_id": session.id,
                    "ready_for_doc": True
                }
        elif agent_intent["agent"] == "create_speech":
            # For speech generation, use RAG to get content and show it as normal response
            # User can then generate speech from that response
            try:
                # Get conversation history for context
                conversation_history = []
                if session.id:
                    previous_messages = db.query(ChatMessage).filter(
                        ChatMessage.session_id == session.id
                    ).order_by(ChatMessage.created_at.asc()).all()
                    conversation_history = [
                        {
                            "role": msg.role, 
                            "content": msg.content,
                            "metadata": msg.message_metadata or {}
                        }
                        for msg in previous_messages
                    ]
                
                # Clean the message - remove agent trigger words to get the actual topic
                clean_message = request.message
                for trigger in ["create speech", "make speech", "generate speech", "speech", "monologue", "voiceover"]:
                    clean_message = clean_message.lower().replace(trigger, "").strip()
                if not clean_message:
                    clean_message = request.message
                
                rag_result = rag_service.query(
                    clean_message, 
                    current_user.role.value,
                    model_id=request.model_id,
                    conversation_history=conversation_history,
                    content_type=request.content_type
                )
                
                # Use RAG answer as the normal assistant response
                assistant_content = rag_result["answer"]
                metadata["sources"] = rag_result.get("sources", [])
                
                # Store speech generation metadata for generation button
                metadata["speech_generation"] = {
                    "topic": clean_message[:100],
                    "session_id": session.id,
                    "ready_for_mp3": True
                }
                logger.info(f"RAG content extracted for speech generation: {len(assistant_content)} chars")
            except Exception as rag_error:
                # If RAG fails, use the message as content
                logger.warning(f"RAG failed for speech generation: {rag_error}, using message as content")
                assistant_content = request.message
                metadata["speech_generation"] = {
                    "topic": request.message[:100],
                    "session_id": session.id,
                    "ready_for_mp3": True
                }
        elif agent_intent["agent"] == "create_video":
            # For video agent, extract videos from RAG answer text (which has detailed descriptions)
            try:
                # Step 1: Get RAG explanation about the topic
                topic = agent_intent["params"].get("topic", "")
                conversation_history = []
                if session.id:
                    previous_messages = db.query(ChatMessage).filter(
                        ChatMessage.session_id == session.id
                    ).order_by(ChatMessage.created_at.asc()).all()
                    conversation_history = [
                        {
                            "role": msg.role, 
                            "content": msg.content,
                            "metadata": msg.message_metadata or {}
                        }
                        for msg in previous_messages
                    ]
                
                # Get RAG response about the topic
                rag_result = rag_service.query(
                    topic or request.message,
                    current_user.role.value,
                    model_id=request.model_id,
                    conversation_history=conversation_history,
                    content_type=request.content_type
                )
                rag_explanation = rag_result.get("answer", "")
                metadata["sources"] = rag_result.get("sources", [])
                
                # Step 2: Extract videos from RAG answer text (which has detailed descriptions)
                from app.services.demo_video_service import demo_video_service
                import re
                
                # Extract YouTube links from RAG answer
                youtube_patterns = [
                    r'https?://(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)',
                    r'https?://(?:www\.)?youtu\.be/([a-zA-Z0-9_-]+)',
                    r'https?://(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]+)',
                ]
                
                videos = []
                seen_video_ids = set()
                
                # Find all YouTube links in the RAG answer
                for pattern in youtube_patterns:
                    matches = re.finditer(pattern, rag_explanation, re.IGNORECASE)
                    for match in matches:
                        video_id = match.group(1)
                        
                        # Skip duplicates
                        if video_id in seen_video_ids:
                            continue
                        seen_video_ids.add(video_id)
                        
                        # Find the text before the link (likely the title/description)
                        url_start = match.start()
                        url_end = match.end()
                        
                        # Look backwards for title (up to 500 chars before to catch numbered list items)
                        text_before = rag_explanation[max(0, url_start - 500):url_start].strip()
                        
                        # Extract title - prioritize numbered list items (most common format)
                        title = None
                        lines = text_before.split('\n')
                        
                        # First, look for numbered list item (e.g., "1. Title" or "1. Title | More Info")
                        for line in reversed(lines):
                            line = line.strip()
                            # Check for numbered list (e.g., "1. Title" or "1. Title | More Info")
                            numbered_match = re.match(r'^\d+\.\s*(.+?)(?:\s*[-–—]|$)', line)
                            if numbered_match:
                                title = numbered_match.group(1).strip()
                                # Clean up title - remove trailing colons, dashes, etc.
                                title = re.sub(r'[:\-–—]\s*$', '', title).strip()
                                if title and len(title) > 5:
                                    break
                        
                        # If no numbered list found, check last line before URL
                        if not title and lines:
                            last_line = lines[-1].strip()
                            # Remove common prefixes like "Video Link:", "- Video Link:", etc.
                            for prefix in ['- Video Link:', 'Video Link:', '-', '•', 'Video:', 'Demo:', 'Link:', 'Watch:', 'View:']:
                                if last_line.lower().startswith(prefix.lower()):
                                    last_line = last_line[len(prefix):].strip()
                            # If the line is just the prefix, check the line before
                            if not last_line or len(last_line) < 5:
                                if len(lines) > 1:
                                    last_line = lines[-2].strip()
                            if last_line and len(last_line) > 5 and len(last_line) < 250:
                                title = last_line
                        
                        # If still no title, use a default
                        if not title:
                            title = f"Demo Video {len(videos) + 1}"
                        
                        # Get description from context around the video
                        start = max(0, url_start - 200)
                        end = min(len(rag_explanation), url_end + 100)
                        description = rag_explanation[start:end].strip()
                        if len(description) > 300:
                            description = description[:300] + "..."
                        
                        # Normalize URL format
                        url = f"https://www.youtube.com/watch?v={video_id}"
                        embed_url = f"https://www.youtube.com/embed/{video_id}"
                        
                        videos.append({
                            "video_id": video_id,
                            "url": url,
                            "embed_url": embed_url,
                            "title": title,
                            "description": description
                        })
                
                # Step 3: Use extracted videos or fallback to separate search if none found
                if videos:
                    # Use videos extracted from RAG answer
                    assistant_content = rag_explanation
                    
                    # Store videos in metadata for frontend to render buttons
                    metadata["videos"] = [
                        {
                            "url": v["url"],
                            "title": v["title"],
                            "video_id": v["video_id"],
                            "embed_url": v["embed_url"]
                        }
                        for v in videos
                    ]
                else:
                    # No videos found in RAG answer, try separate search as fallback
                    agent_result = await mcp_service.call_agent(
                        agent_intent["agent"],
                        agent_intent["params"],
                        {
                            "user_id": current_user.id,
                            "role": current_user.role.value,
                            "full_name": current_user.full_name
                        }
                    )
                    metadata["agent_call"] = {
                        "agent": agent_intent["agent"],
                        "result": agent_result
                    }
                    
                    if agent_result.get("status") == "success" and agent_result.get("videos"):
                        videos = agent_result["videos"]
                        assistant_content = rag_explanation
                        metadata["videos"] = [
                            {
                                "url": v.get("url"),
                                "title": v.get("title", "Demo Video"),
                                "video_id": v.get("video_id"),
                                "embed_url": v.get("embed_url")
                            }
                            for v in videos
                        ]
                    else:
                        # No videos found at all
                        assistant_content = rag_explanation + "\n\nNo demo videos available for this topic."
            except Exception as e:
                logger.error(f"Video agent error: {e}", exc_info=True)
                metadata["agent_error"] = str(e)
                assistant_content = "No demo videos available today."
        elif agent_intent["agent"] == "video_generate":
            # SIMPLE LOGIC: Only check for demo videos, no HeyGen generation
            try:
                topic = agent_intent["params"].get("topic", "")
                
                # Use the full message as query to preserve context
                # The demo_video_service will clean it internally
                search_query = topic or request.message
                
                # Check for existing demo videos
                from app.services.demo_video_service import demo_video_service
                logger.info(f"Checking for existing demo videos for query: '{search_query}'")
                
                demo_result = demo_video_service.find_demo_videos(
                    query=search_query,
                    user_role=current_user.role.value,
                    limit=10  # Allow multiple videos
                )
                
                logger.info(f"Demo video search result: status={demo_result.get('status')}, videos_found={len(demo_result.get('videos', []))}")
                
                # If demo videos found, return those
                videos = demo_result.get("videos", [])
                is_suggestion = demo_result.get("is_suggestion", False)
                suggestion_message = demo_result.get("message", "")
                
                if demo_result.get("status") == "success" and videos:
                    if is_suggestion:
                        logger.info(f"Found {len(videos)} suggested video(s) - returning suggestions")
                    else:
                        logger.info(f"Found {len(videos)} demo video(s) - returning those")
                    
                    # Get RAG explanation for context
                    conversation_history = []
                    if session.id:
                        previous_messages = db.query(ChatMessage).filter(
                            ChatMessage.session_id == session.id
                        ).order_by(ChatMessage.created_at.asc()).all()
                        conversation_history = [
                            {
                                "role": msg.role, 
                                "content": msg.content,
                                "metadata": msg.message_metadata or {}
                            }
                            for msg in previous_messages
                        ]
                    
                    rag_result = rag_service.query(
                        topic or request.message,
                        current_user.role.value,
                        model_id=request.model_id,
                        conversation_history=conversation_history,
                        content_type=request.content_type
                    )
                    rag_explanation = rag_result.get("answer", "")
                    metadata["sources"] = rag_result.get("sources", [])
                    
                    # RAG explanation already contains the video link in the source
                    # Just use the RAG explanation directly - no need to add extra "Found X videos" section
                    assistant_content = rag_explanation
                    
                    # If these are suggestions, prepend the suggestion message
                    if is_suggestion and suggestion_message:
                        assistant_content = f"{suggestion_message}\n\n{rag_explanation}"
                    
                    # Extract ALL video links from RAG explanation text
                    # The RAG explanation may contain multiple videos: "Source: ... | https://youtu.be/..." format
                    import re as re_module  # Use alias to avoid scoping issues
                    youtube_patterns = [
                        r'https?://(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)',
                        r'https?://(?:www\.)?youtu\.be/([a-zA-Z0-9_-]+)',
                        r'https?://(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]+)',
                    ]
                    
                    videos_from_rag = []
                    seen_video_ids = {v.get("video_id") for v in videos if v.get("video_id")}  # Track IDs from demo_video_service
                    
                    # Find all video links in RAG explanation
                    for pattern in youtube_patterns:
                        matches = re_module.finditer(pattern, rag_explanation, re_module.IGNORECASE)
                        for match in matches:
                            video_id = match.group(1)
                            
                            # Skip if we already have this video from demo_video_service
                            if video_id in seen_video_ids:
                                continue
                            
                            if 'youtu.be' in match.group(0):
                                video_url = f"https://www.youtube.com/watch?v={video_id}"
                            else:
                                video_url = match.group(0)
                            
                            videos_from_rag.append({
                                "url": video_url,
                                "title": "Demo Video",  # Default title, will be improved if we can extract from context
                                "video_id": video_id,
                                "embed_url": f"https://www.youtube.com/embed/{video_id}"
                            })
                            seen_video_ids.add(video_id)
                    
                    # Merge videos: prioritize demo_video_service results (they have better titles/metadata)
                    # but also include videos found in RAG explanation that aren't already in the list
                    all_videos = videos + videos_from_rag
                    
                    if all_videos:
                        logger.info(f"Total videos found: {len(videos)} from demo_video_service + {len(videos_from_rag)} from RAG = {len(all_videos)} total")
                        metadata["videos"] = [
                            {
                                "url": v.get("url"),
                                "title": v.get("title", "Demo Video"),
                                "video_id": v.get("video_id"),
                                "embed_url": v.get("embed_url")
                            }
                            for v in all_videos
                        ]
                    else:
                        # Fallback: use videos from demo_video_service only
                        logger.info(f"Using videos from demo_video_service only: {len(videos)} video(s)")
                        metadata["videos"] = [
                            {
                                "url": v.get("url"),
                                "title": v.get("title", "Demo Video"),
                                "video_id": v.get("video_id"),
                                "embed_url": v.get("embed_url")
                            }
                            for v in videos
                        ]
                    metadata["video_source"] = "existing_demo"
                else:
                    # No demo videos found - check if there are suggestions
                    if is_suggestion and videos:
                        # We have suggestions but they weren't processed above (shouldn't happen, but handle it)
                        logger.info(f"Found {len(videos)} suggested video(s) but not processed above")
                        # Get RAG explanation
                        conversation_history = []
                        if session.id:
                            previous_messages = db.query(ChatMessage).filter(
                                ChatMessage.session_id == session.id
                            ).order_by(ChatMessage.created_at.asc()).all()
                            conversation_history = [
                                {
                                    "role": msg.role, 
                                    "content": msg.content,
                                    "metadata": msg.message_metadata or {}
                                }
                                for msg in previous_messages
                            ]
                        
                        rag_result = rag_service.query(
                            topic or request.message,
                            current_user.role.value,
                            model_id=request.model_id,
                            conversation_history=conversation_history,
                            content_type=request.content_type
                        )
                        rag_explanation = rag_result.get("answer", "")
                        metadata["sources"] = rag_result.get("sources", [])
                        
                        assistant_content = f"{suggestion_message}\n\n{rag_explanation}"
                        
                        # Store videos in metadata
                        metadata["videos"] = [
                            {
                                "url": v.get("url"),
                                "title": v.get("title", "Demo Video"),
                                "video_id": v.get("video_id"),
                                "embed_url": v.get("embed_url")
                            }
                            for v in videos
                        ]
                        metadata["video_source"] = "existing_demo"
                    else:
                        # No demo videos found - simple message
                        logger.info(f"No demo videos found for topic: {topic}")
                        assistant_content = "No demo video available right now."
                    
            except Exception as e:
                logger.error(f"Video search error: {e}", exc_info=True)
                metadata["agent_error"] = str(e)
                assistant_content = "No demo video available right now."
        else:
            # For other agents, call them immediately
            # Call agent
            try:
                agent_result = await mcp_service.call_agent(
                    agent_intent["agent"],
                    agent_intent["params"],
                    {
                        "user_id": current_user.id,
                        "role": current_user.role.value,
                        "full_name": current_user.full_name
                    }
                )
                metadata["agent_call"] = {
                    "agent": agent_intent["agent"],
                    "result": agent_result
                }
                # Include agent result in response
                assistant_content = f"Agent Response: {json.dumps(agent_result, indent=2)}"
            except Exception as e:
                metadata["agent_error"] = str(e)
                assistant_content = f"I encountered an error calling the agent: {str(e)}"
    else:
        # Use RAG for regular Q&A
        try:
            # Get conversation history for context (include metadata to track document usage)
            conversation_history = []
            if session.id:
                previous_messages = db.query(ChatMessage).filter(
                    ChatMessage.session_id == session.id
                ).order_by(ChatMessage.created_at.asc()).all()
                conversation_history = [
                    {
                        "role": msg.role, 
                        "content": msg.content,
                        "metadata": msg.message_metadata or {}  # Include metadata to track sources
                    }
                    for msg in previous_messages
                ]
            
            rag_result = rag_service.query(
                request.message, 
                current_user.role.value,
                model_id=request.model_id,
                conversation_history=conversation_history,
                content_type=request.content_type
            )
            assistant_content = rag_result["answer"]
            metadata["sources"] = rag_result.get("sources", [])
            metadata["model_used"] = request.model_id or "auto"
        except Exception as e:
            assistant_content = f"I encountered an error: {str(e)}"
            metadata["error"] = str(e)
    
    # Save assistant message
    assistant_message = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=assistant_content,
        message_metadata=metadata
    )
    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)
    
    # Update session title if it's the first message
    if not session.title or session.title == request.message[:50]:
        session.title = request.message[:50] if len(request.message) > 50 else request.message
        db.commit()
    
    return {
        "session_id": session.id,
        "message": {
            "id": assistant_message.id,
            "role": assistant_message.role,
            "content": assistant_message.content,
            "metadata": assistant_message.message_metadata
        }
    }

@router.get("/sessions")
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 20
):
    sessions = db.query(ChatSession).filter(
        ChatSession.user_id == current_user.id
    ).order_by(ChatSession.updated_at.desc()).offset(skip).limit(limit).all()
    
    return {
        "items": [
            {
                "id": session.id,
                "title": session.title,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat()
            }
            for session in sessions
        ]
    }

@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found"
        )
    
    messages = db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id
    ).order_by(ChatMessage.created_at.asc()).all()
    
    return {
        "session_id": session.id,
        "title": session.title,
        "messages": [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "metadata": msg.message_metadata,
                "created_at": msg.created_at.isoformat()
            }
            for msg in messages
        ]
    }

@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found"
        )
    
    db.delete(session)
    db.commit()
    
    return {"message": "Session deleted successfully"}

