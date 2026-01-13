from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response, JSONResponse, FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Literal, Optional
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.document_generator import DocumentGenerator
from app.services.mcp_service import mcp_service
from app.services.job_tracker import job_tracker, JobStatus
import logging
import threading
import os
import time
from pathlib import Path

router = APIRouter()
logger = logging.getLogger(__name__)

# Directory to store generated files temporarily
TEMP_FILES_DIR = Path(__file__).parent.parent.parent / "temp_generated_files"
TEMP_FILES_DIR.mkdir(exist_ok=True)

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

# ============================================================================
# ASYNC GENERATION ENDPOINTS (for long-running tasks like podcast)
# ============================================================================

@router.post("/async")
async def generate_document_async(
    request: GenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start async document generation - returns job ID immediately"""
    
    # Create a job
    job = job_tracker.create_job(
        job_type=f"generate_{request.type}",
        user_id=current_user.id
    )
    
    # Start generation in background thread
    def generate_in_background():
        try:
            logger.info(f"[Job {job.job_id}] Starting {request.type} generation...")
            job_tracker.update_job(
                job.job_id,
                status=JobStatus.PROCESSING,
                progress=5,
                message="Preparing generation..."
            )
            
            # Stage-based progress tracking based on type
            if request.type == 'podcast':
                job_tracker.update_job(job.job_id, progress=15, message="Generating podcast script...")
                
                def update_podcast_status():
                    logger.info(f"[StatusThread] Started for podcast job {job.job_id}")
                    time.sleep(8)
                    if job_tracker.get_job(job.job_id) and job_tracker.get_job(job.job_id).status == JobStatus.PROCESSING:
                        job_tracker.update_job(job.job_id, progress=25, message="Script ready! Creating audio segments...")
                    time.sleep(10)
                    if job_tracker.get_job(job.job_id) and job_tracker.get_job(job.job_id).status == JobStatus.PROCESSING:
                        job_tracker.update_job(job.job_id, progress=50, message="Generating audio with TTS (this takes ~30-45 sec)...")
                    time.sleep(15)
                    if job_tracker.get_job(job.job_id) and job_tracker.get_job(job.job_id).status == JobStatus.PROCESSING:
                        job_tracker.update_job(job.job_id, progress=75, message="Still creating audio segments...")
                    time.sleep(10)
                    if job_tracker.get_job(job.job_id) and job_tracker.get_job(job.job_id).status == JobStatus.PROCESSING:
                        job_tracker.update_job(job.job_id, progress=90, message="Merging all segments...")
                    logger.info(f"[StatusThread] Finished for podcast job {job.job_id}")
                
                threading.Thread(target=update_podcast_status, daemon=True).start()
                
            elif request.type == 'speech':
                job_tracker.update_job(job.job_id, progress=15, message="Generating speech script...")
                
                def update_speech_status():
                    logger.info(f"[StatusThread] Started for speech job {job.job_id}")
                    time.sleep(6)
                    if job_tracker.get_job(job.job_id) and job_tracker.get_job(job.job_id).status == JobStatus.PROCESSING:
                        job_tracker.update_job(job.job_id, progress=30, message="Script ready! Creating audio...")
                    time.sleep(10)
                    if job_tracker.get_job(job.job_id) and job_tracker.get_job(job.job_id).status == JobStatus.PROCESSING:
                        job_tracker.update_job(job.job_id, progress=60, message="Generating audio with TTS (takes ~20-30 sec)...")
                    time.sleep(10)
                    if job_tracker.get_job(job.job_id) and job_tracker.get_job(job.job_id).status == JobStatus.PROCESSING:
                        job_tracker.update_job(job.job_id, progress=90, message="Finalizing audio...")
                    logger.info(f"[StatusThread] Finished for speech job {job.job_id}")
                
                threading.Thread(target=update_speech_status, daemon=True).start()
                
            elif request.type == 'ppt':
                job_tracker.update_job(job.job_id, progress=15, message="Analyzing content structure...")
                
                def update_ppt_status():
                    logger.info(f"[StatusThread] Started for PPT job {job.job_id}")
                    time.sleep(5)
                    if job_tracker.get_job(job.job_id) and job_tracker.get_job(job.job_id).status == JobStatus.PROCESSING:
                        job_tracker.update_job(job.job_id, progress=30, message="Creating slides...")
                    time.sleep(8)
                    if job_tracker.get_job(job.job_id) and job_tracker.get_job(job.job_id).status == JobStatus.PROCESSING:
                        job_tracker.update_job(job.job_id, progress=60, message="Adding content and formatting...")
                    time.sleep(5)
                    if job_tracker.get_job(job.job_id) and job_tracker.get_job(job.job_id).status == JobStatus.PROCESSING:
                        job_tracker.update_job(job.job_id, progress=90, message="Generating PowerPoint file...")
                    logger.info(f"[StatusThread] Finished for PPT job {job.job_id}")
                
                threading.Thread(target=update_ppt_status, daemon=True).start()
                
            else:
                job_tracker.update_job(job.job_id, progress=10, message=f"Generating {request.type}...")
            
            # Generate the document
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            generator = DocumentGenerator()
            file_data, filename, content_type = loop.run_until_complete(
                generator.generate(
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
            )
            
            # Save file to temp directory
            job_tracker.update_job(
                job.job_id,
                progress=95,
                message="Saving file..."
            )
            
            file_path = TEMP_FILES_DIR / f"{job.job_id}_{filename}"
            with open(file_path, 'wb') as f:
                f.write(file_data)
            
            logger.info(f"[Job {job.job_id}] Generation complete! File saved: {file_path}")
            
            # Update job as completed
            job_tracker.update_job(
                job.job_id,
                status=JobStatus.COMPLETED,
                progress=100,
                message="Podcast ready to download!",
                result={
                    "filename": filename,
                    "content_type": content_type,
                    "size": len(file_data),
                    "file_path": str(file_path)
                }
            )
            
        except Exception as e:
            logger.error(f"[Job {job.job_id}] Generation failed: {e}", exc_info=True)
            job_tracker.update_job(
                job.job_id,
                status=JobStatus.FAILED,
                progress=0,
                message="Generation failed",
                error=str(e)
            )
    
    # Start background thread
    thread = threading.Thread(target=generate_in_background, daemon=True)
    thread.start()
    
    return JSONResponse(content={
        "job_id": job.job_id,
        "status": job.status.value,
        "message": "Generation started"
    })

@router.get("/job/{job_id}")
async def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user)
):
    """Check status of an async generation job"""
    
    job = job_tracker.get_job(job_id)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Verify user owns this job
    if job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return JSONResponse(content=job.to_dict())

@router.get("/download/{job_id}")
async def download_generated_file(
    job_id: str,
    current_user: User = Depends(get_current_user)
):
    """Download a completed generated file"""
    
    job = job_tracker.get_job(job_id)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Verify user owns this job
    if job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Check if job is completed
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job is not completed yet. Current status: {job.status.value}"
        )
    
    # Get file path from job result
    file_path = job.result.get("file_path")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generated file not found"
        )
    
    # Return file
    filename = job.result.get("filename", "generated_file")
    content_type = job.result.get("content_type", "application/octet-stream")
    
    return FileResponse(
        path=file_path,
        media_type=content_type,
        filename=filename,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )

@router.get("/jobs")
async def list_user_jobs(
    current_user: User = Depends(get_current_user),
    limit: int = 10
):
    """List user's generation jobs"""
    
    jobs = job_tracker.get_user_jobs(current_user.id, limit=limit)
    
    return JSONResponse(content={
        "jobs": jobs
    })