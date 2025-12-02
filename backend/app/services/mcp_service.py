from typing import Dict, List, Optional, Any
import httpx
from app.core.config import settings

class MCPService:
    """Service for interacting with MCP (Model Context Protocol) agents"""
    
    def __init__(self):
        self.registered_agents: Dict[str, Dict] = {
            "create_video": {
                "name": "Find Demo Video",
                "description": "Search for existing demo videos in the knowledge base and return YouTube links",
                "endpoint": None,  # Will be configured
            },
            "create_ppt": {
                "name": "Create PowerPoint",
                "description": "Generate PowerPoint presentations",
                "endpoint": None,
            },
            "create_doc": {
                "name": "Create Document",
                "description": "Generate Word documents",
                "endpoint": None,
            },
            "submit_leave": {
                "name": "Submit Leave Request",
                "description": "Submit PTO and sick leave requests",
                "endpoint": None,
            },
            "generate_report": {
                "name": "Generate Report",
                "description": "Generate business reports",
                "endpoint": None,
            },
            "check_pto": {
                "name": "Check PTO",
                "description": "Check PTO availability and balance",
                "endpoint": None,
            },
            "text_to_speech": {
                "name": "Text to Speech",
                "description": "Convert text to MP3/WAV audio using TTS",
                "endpoint": None,
            },
            "find_demo_video": {
                "name": "Find Demo Video",
                "description": "Search for demo videos by keywords and return YouTube links",
                "endpoint": None,
            },
            "video_generate": {
                "name": "Generate Video",
                "description": "Generate video using HeyGen API from script content",
                "endpoint": None,
            },
        }
    
    def register_agent(self, agent_id: str, config: Dict):
        """Register a new MCP agent"""
        self.registered_agents[agent_id] = config
    
    def list_agents(self) -> List[Dict]:
        """List all available agents"""
        return [
            {
                "id": agent_id,
                **config
            }
            for agent_id, config in self.registered_agents.items()
        ]
    
    async def call_agent(self, agent_id: str, params: Dict[str, Any], user_context: Dict) -> Dict:
        """Call an MCP agent with parameters"""
        if agent_id not in self.registered_agents:
            raise ValueError(f"Agent {agent_id} not found")
        
        agent = self.registered_agents[agent_id]
        
        # If agent has an endpoint, call it via HTTP
        if agent.get("endpoint"):
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    agent["endpoint"],
                    json={
                        "params": params,
                        "user_context": user_context
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
        
        # Otherwise, handle locally
        return await self._handle_local_agent(agent_id, params, user_context)
    
    async def _handle_local_agent(self, agent_id: str, params: Dict, user_context: Dict) -> Dict:
        """Handle agent calls locally (placeholder implementation)"""
        if agent_id == "check_pto":
            # Placeholder: In real implementation, this would query HR system
            return {
                "status": "success",
                "data": {
                    "available_pto": 15,
                    "used_pto": 5,
                    "pending_requests": 2
                }
            }
        elif agent_id == "submit_leave":
            # Placeholder: In real implementation, this would submit to HR system
            return {
                "status": "success",
                "message": f"Leave request submitted for {params.get('start_date')} to {params.get('end_date')}",
                "request_id": "REQ-12345"
            }
        elif agent_id == "create_video":
            # Search for existing demo videos only (video generation not available)
            from app.services.demo_video_service import demo_video_service
            import logging
            logger = logging.getLogger(__name__)
            
            topic = params.get("topic") or params.get("description") or params.get("content", "")
            user_role = user_context.get("role", "user")
            limit = params.get("limit", 5)
            
            if not topic:
                return {
                    "status": "error",
                    "message": "Please specify what demo video you're looking for (e.g., 'encrypted visibility engine', 'firewall demo')."
                }
            
            # Check for existing demo videos in RAG
            logger.info(f"Searching for demo video: {topic}")
            demo_result = demo_video_service.find_demo_videos(
                query=topic,
                user_role=user_role,
                limit=limit
            )
            
            if demo_result.get("status") == "success" and demo_result.get("videos"):
                # Found demo videos - format with watch button
                videos_with_button = []
                for video in demo_result["videos"]:
                    button_html = f'<a href="{video["url"]}" target="_blank" style="display: inline-block; padding: 10px 20px; background-color: #FF0000; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">Watch the Demo Video</a>'
                    
                    videos_with_button.append({
                        "video_id": video["video_id"],
                        "url": video["url"],
                        "embed_url": video["embed_url"],
                        "title": video["title"],
                        "description": video["description"],
                        "source_document": video.get("source_document", "Unknown"),
                        "watch_button": button_html,
                        "watch_button_text": "Watch the Demo Video",
                        "watch_button_url": video["url"]
                    })
                
                return {
                    "status": "success",
                    "videos": videos_with_button,
                    "message": f"Found {len(videos_with_button)} demo video(s) for '{topic}':",
                    "count": len(videos_with_button),
                    "source": "demo_video_library"
                }
            else:
                # No videos found
                return {
                    "status": "success",
                    "videos": [],
                    "message": "No demo videos available today.",
                    "count": 0
                }
        elif agent_id == "create_ppt":
            # PowerPoint generation using Presenton.ai API or fallback
            from app.services.document_generator import DocumentGenerator
            import logging
            logger = logging.getLogger(__name__)
            
            # Extract parameters
            content = params.get("content") or params.get("description") or params.get("text", "")
            topic = params.get("topic")
            template_id = params.get("template_id")
            session_id = params.get("session_id")
            
            if not content:
                return {
                    "status": "error",
                    "message": "No content provided for PowerPoint generation"
                }
            
            try:
                logger.info(f"Creating PowerPoint with content length: {len(content)}, topic: {topic}, template_id: {template_id}")
                generator = DocumentGenerator()
                
                # Generate PowerPoint (will try Presenton.ai first if configured, then fallback to local)
                ppt_data, filename, content_type = await generator.generate(
                    content=content,
                    doc_type="ppt",
                    user_context=user_context,
                    session_id=session_id,
                    topic=topic,
                    template_id=template_id
                )
                
                # Check if this is a Presenton.ai response (JSON with path)
                if content_type == "application/json":
                    import json
                    presenton_result = json.loads(ppt_data.decode('utf-8'))
                    return {
                        "status": "success",
                        "presentation_id": presenton_result.get("presentation_id"),
                        "path": presenton_result.get("path"),  # Download URL
                        "edit_path": presenton_result.get("edit_path"),
                        "credits_consumed": presenton_result.get("credits_consumed"),
                        "filename": filename,
                        "format": "pptx",
                        "message": f"Successfully generated PowerPoint presentation. Click to download."
                    }
                else:
                    # Local generation - return base64 encoded data
                    import base64
                    return {
                        "status": "success",
                        "ppt_data": base64.b64encode(ppt_data).decode('utf-8'),
                        "filename": filename,
                        "format": "pptx",
                        "content_type": content_type,
                        "message": f"Successfully generated PowerPoint presentation ({len(ppt_data)} bytes)"
                    }
            except Exception as e:
                logger.error(f"PowerPoint generation error: {e}", exc_info=True)
                return {
                    "status": "error",
                    "message": f"Failed to generate PowerPoint: {str(e)}"
                }
        elif agent_id == "text_to_speech":
            # Use TTS service to convert text to audio
            from app.services.tts_service import tts_service
            text = params.get("text", "")
            audio_format = params.get("format", "mp3")  # mp3 or wav
            language = params.get("language", "en")
            
            if not text:
                return {
                    "status": "error",
                    "message": "No text provided for TTS conversion"
                }
            
            try:
                audio_data = tts_service.text_to_speech(text, audio_format, language)
                return {
                    "status": "success",
                    "audio_data": audio_data,  # Base64 encoded audio
                    "format": audio_format,
                    "message": f"Successfully converted {len(text)} characters to {audio_format.upper()} audio"
                }
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"TTS conversion error: {e}", exc_info=True)
                return {
                    "status": "error",
                    "message": f"Failed to convert text to speech: {str(e)}"
                }
        elif agent_id == "find_demo_video":
            # Search for demo videos using RAG
            from app.services.demo_video_service import demo_video_service
            import logging
            logger = logging.getLogger(__name__)
            
            query = params.get("query") or params.get("keywords") or params.get("search", "")
            user_role = params.get("user_role", user_context.get("role", "user"))
            limit = params.get("limit", 5)
            
            if not query:
                return {
                    "status": "error",
                    "message": "No search query provided. Please specify keywords to search for demo videos."
                }
            
            try:
                logger.info(f"Searching for demo videos with query: {query}")
                result = demo_video_service.find_demo_videos(
                    query=query,
                    user_role=user_role,
                    limit=limit
                )
                
                # Format response for frontend display
                if result["status"] == "success" and result["videos"]:
                    # Build HTML/embed code for video display
                    videos_with_embed = []
                    for video in result["videos"]:
                        embed_html = f'<iframe width="560" height="315" src="{video["embed_url"]}" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>'
                        videos_with_embed.append({
                            **video,
                            "embed_html": embed_html
                        })
                    
                    return {
                        "status": "success",
                        "videos": videos_with_embed,
                        "message": result["message"],
                        "count": len(videos_with_embed)
                    }
                else:
                    return result
                    
            except Exception as e:
                logger.error(f"Demo video search error: {e}", exc_info=True)
                return {
                    "status": "error",
                    "message": f"Failed to search for demo videos: {str(e)}",
                    "videos": []
                }
        elif agent_id == "video_generate":
            # HeyGen video generation is disabled in production
            # Code kept for reference but not used
            # from app.services.heygen_service import heygen_service
            import logging
            logger = logging.getLogger(__name__)
            
            logger.info("HeyGen video generation is disabled - only demo videos are available")
            return {
                "status": "error",
                "message": "Video generation is not available. Please check for existing demo videos instead."
            }
            
            # DISABLED CODE BELOW - Kept for reference
            # script = params.get("script") or params.get("content") or params.get("text", "")
            # topic = params.get("topic") or params.get("title", "")
            # image_key = params.get("image_key")
            # voice_id = params.get("voice_id")
            # video_orientation = params.get("video_orientation")
            # fit = params.get("fit")
            # custom_motion_prompt = params.get("custom_motion_prompt")
            # enhance_custom_motion_prompt = params.get("enhance_custom_motion_prompt", False)
            # audio_url = params.get("audio_url")
            # audio_asset_id = params.get("audio_asset_id")
            # 
            # if not script:
            #     return {
            #         "status": "error",
            #         "message": "No script content provided for video generation"
            #     }
            # 
            # try:
            #     logger.info(f"Generating video with HeyGen Avatar IV: topic={topic}, script_length={len(script)}")
            #     result = await heygen_service.generate_video(
            #         script=script,
            #         topic=topic,
            #         image_key=image_key,
            #         voice_id=voice_id,
            #         video_orientation=video_orientation,
            #         fit=fit,
            #         custom_motion_prompt=custom_motion_prompt,
            #         enhance_custom_motion_prompt=enhance_custom_motion_prompt,
            #         audio_url=audio_url,
            #         audio_asset_id=audio_asset_id
            #     )
            #     
            #     return {
            #         "status": "success",
            #         "video_id": result.get("video_id"),
            #         "video_url": result.get("video_url"),
            #         "filename": result.get("filename"),
            #         "credits_consumed": result.get("credits_consumed", 0),
            #         "estimated_duration": result.get("estimated_duration", 0),
            #         "message": f"Video generated successfully! Credits used: {result.get('credits_consumed', 0)}"
            #     }
            # except Exception as e:
            #     logger.error(f"HeyGen video generation error: {e}", exc_info=True)
            #     return {
            #         "status": "error",
            #         "message": f"Failed to generate video: {str(e)}"
            #     }
        else:
            return {
                "status": "pending",
                "message": f"Agent {agent_id} is not yet fully implemented"
            }

# Global instance
mcp_service = MCPService()

