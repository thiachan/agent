import httpx
import logging
import os
from typing import Tuple, Optional, Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)

class PresentonService:
    """Service for integrating with Presenton.ai PowerPoint generation API"""
    
    def __init__(self):
        self.api_key = settings.PRESENTON_API_KEY
        self.api_url = settings.PRESENTON_API_URL.rstrip('/')
        self.max_slides = settings.PRESENTON_MAX_SLIDES
    
    async def generate_powerpoint(
        self,
        content: str,
        topic: Optional[str] = None,
        template_path: Optional[str] = None
    ) -> Tuple[Dict[str, Any], str]:
        """
        Generate PowerPoint presentation using Presenton.ai API
        
        Args:
            content: The content to generate slides from
            topic: Optional topic/title for the presentation
            template_path: Path to the template PPTX file (not used for now, using "general" template)
        
        Returns:
            Tuple of (response_dict with path, filename)
            The response_dict contains: presentation_id, path (download URL), edit_path, credits_consumed
        """
        if not self.api_key:
            raise ValueError("Presenton.ai API key not configured")
        
        try:
            logger.info("=" * 60)
            logger.info("PRESENTON.AI SERVICE: Starting PowerPoint generation")
            logger.info(f"   API URL: {self.api_url}")
            logger.info(f"   Max slides: {self.max_slides}")
            logger.info("=" * 60)
            
            # Prepare the request payload according to Presenton.ai API
            payload = {
                "content": content,
                "n_slides": 12,  # Fixed to 12 slides
                "language": "English",
                "template": "custom-31ec1f9f-6111-43d8-95db-217e051a021b",  # Using cisco custom template
                "theme": "36dada46-7c64-47f2-aad8-4930660e3e7b",  # Using custom theme
                "export_as": "pptx",
                "tone": "professional",
                "verbosity": "standard",
                "image_type": "stock",
                "include_table_of_contents": True,
                "include_title_slide": True
            }
            
            # Note: Template file upload not supported in current API, using "general" template
            if template_path and os.path.exists(template_path):
                logger.info(f"Template file found: {template_path}, but using 'general' template as per API")
            
            # Make the request to Presenton.ai API
            endpoint = f"{self.api_url}/api/v1/ppt/presentation/generate"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=300.0) as client:
                logger.info(f"Calling Presenton.ai API: {endpoint}")
                logger.info(f"Payload: {payload}")
                
                response = await client.post(
                    endpoint,
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                
                # Parse JSON response
                result = response.json()
                logger.info(f"Presenton.ai response: {result}")
                
                # Extract download path
                if "path" not in result:
                    raise ValueError(f"Presenton.ai API did not return a download path. Response: {result}")
                
                download_path = result["path"]
                presentation_id = result.get("presentation_id", "unknown")
                credits_consumed = result.get("credits_consumed", 0)
                
                logger.info(f"✅ Presentation generated successfully!")
                logger.info(f"   Presentation ID: {presentation_id}")
                logger.info(f"   Download path: {download_path}")
                logger.info(f"   Credits consumed: {credits_consumed}")
                
                # Generate filename from topic or content
                filename = f"presentation_{topic or 'generated'}.pptx".replace(' ', '_')[:100]
                
                # Return the full response dict so frontend can use the path directly
                return {
                    "presentation_id": presentation_id,
                    "path": download_path,
                    "edit_path": result.get("edit_path"),
                    "credits_consumed": credits_consumed,
                    "filename": filename
                }, filename
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Presenton.ai API HTTP error: {e.response.status_code} - {e.response.text}")
            raise ValueError(f"Presenton.ai API error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            logger.error(f"Error calling Presenton.ai API: {e}", exc_info=True)
            raise ValueError(f"Failed to generate PowerPoint using Presenton.ai: {str(e)}")

# Create singleton instance
presenton_service = PresentonService()

