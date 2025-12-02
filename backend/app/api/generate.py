from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response, JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Literal, Optional
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.document_generator import DocumentGenerator
from app.services.mcp_service import mcp_service
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class GenerateRequest(BaseModel):
    content: str
    type: Literal["ppt", "mp4", "doc", "pdf", "mp3", "wav", "speech", "podcast"]
    session_id: Optional[int] = None
    topic: Optional[str] = None
    template_id: Optional[int] = None  # ID of uploaded PowerPoint template

class ConfirmPPTRequest(BaseModel):
    content: str  # The assistant's message content to use for PowerPoint generation
    topic: Optional[str] = None
    session_id: Optional[int] = None
    template_id: Optional[int] = None

@router.post("/document")
async def generate_document(
    request: GenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate a document (PPT, MP4, DOC, PDF, MP3, WAV, Speech, Podcast) from chat content"""
    
    # For MP4 video requests, only check for demo videos (HeyGen generation disabled)
    if request.type == "mp4":
        try:
            # Check for existing demo videos
            from app.services.demo_video_service import demo_video_service
            demo_result = demo_video_service.find_demo_videos(
                query=request.topic or request.content[:100],  # Use topic or first 100 chars as query
                user_role=current_user.role.value,
                limit=5
            )
            
            # If demo videos found, return error suggesting to use chat interface
            if demo_result.get("status") == "success" and demo_result.get("videos"):
                videos = demo_result.get("videos", [])
                video_list = "\n".join([f"- {v.get('title', 'Demo Video')}: {v.get('url', '')}" for v in videos])
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Found {len(videos)} existing demo video(s) for this topic. Please use the chat interface to access them.\n\n{video_list}"
                )
            
            # No demo videos found
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No demo video available right now."
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error checking demo videos: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No demo video available right now."
            )
    
    # For other document types, use DocumentGenerator
    generator = DocumentGenerator()
    
    try:
        file_data, filename, content_type = await generator.generate(
            content=request.content,
            doc_type=request.type,
            user_context={
                "user_id": current_user.id,
                "role": current_user.role.value,
                "full_name": current_user.full_name
            },
            session_id=request.session_id,
            topic=request.topic,
            template_id=request.template_id
        )
        
        return Response(
            content=file_data,
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate document: {str(e)}"
        )

@router.post("/confirm-ppt")
async def confirm_generate_ppt(
    request: ConfirmPPTRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Confirm and generate PowerPoint presentation after user preview"""
    try:
        # Call the agent to generate PowerPoint
        agent_result = await mcp_service.call_agent(
            "create_ppt",
            {
                "content": request.content,
                "topic": request.topic,
                "session_id": request.session_id,
                "template_id": request.template_id
            },
            {
                "user_id": current_user.id,
                "role": current_user.role.value,
                "full_name": current_user.full_name
            }
        )
        
        # Return the agent result (which includes Presenton.ai path or base64 data)
        return JSONResponse(content={
            "status": "success",
            "agent_result": agent_result
        })
    except Exception as e:
        logger.error(f"Failed to generate PowerPoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate PowerPoint: {str(e)}"
        )

