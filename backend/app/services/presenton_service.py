import httpx
import logging
import base64
from typing import Tuple, Optional, Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)


class PresentonService:
    """Service for integrating with Presenton PowerPoint generation API"""
    
    def __init__(self):
        self.api_key = settings.PRESENTON_API_KEY
        self.api_url = settings.PRESENTON_API_URL.rstrip('/')
        self.max_slides = settings.PRESENTON_MAX_SLIDES
        self.require_auth = settings.PRESENTON_REQUIRE_AUTH
    
    async def generate_powerpoint(
        self,
        content: str,
        topic: Optional[str] = None,
        template_path: Optional[str] = None
    ) -> Tuple[Dict[str, Any], str]:
        """
        Generate PowerPoint presentation using Presenton API
        
        Args:
            content: The content to generate slides from
            topic: Optional topic/title for the presentation
            template_path: Path to template PPTX file (not used)
        
        Returns:
            Tuple of (response_dict, filename)
        """
        if self.require_auth and not self.api_key:
            raise ValueError("Presenton API authentication required but API key not configured")
        
        try:
            logger.info("=" * 60)
            logger.info("PRESENTON SERVICE: Starting PowerPoint generation")
            logger.info(f"   API URL: {self.api_url}")
            logger.info(f"   Auth Required: {self.require_auth}")
            logger.info(f"   Max slides: {self.max_slides}")
            logger.info("=" * 60)
            
            # Prepare API request payload
            payload = {
                "content": content,
                "n_slides": 12,
                "language": "English",
                "template": "custom-84bb7379-b8f2-47ce-b38d-2ac916ea31c3",
                "export_as": "pptx",
                "tone": "professional",
                "verbosity": "standard",
                "image_type": "stock",
                "include_table_of_contents": True,
                "include_title_slide": True
            }
            
            # Build headers - conditionally include authentication
            endpoint = f"{self.api_url}/api/v1/ppt/presentation/generate"
            headers = {"Content-Type": "application/json"}
            
            if self.require_auth:
                headers["Authorization"] = f"Bearer {self.api_key}"
                logger.info("Using authenticated request (Bearer token)")
            else:
                logger.info("Using non-authenticated request (internal ECS service)")
            
            async with httpx.AsyncClient(timeout=300.0) as client:
                logger.info(f"Calling Presenton API: {endpoint}")
                
                # Generate presentation
                response = await client.post(endpoint, json=payload, headers=headers)
                response.raise_for_status()
                
                result = response.json()
                logger.info(f"Presenton API response: {result}")
                
                # Validate response
                if "path" not in result:
                    raise ValueError(f"Presenton API did not return a download path. Response: {result}")
                
                download_path = result["path"]
                presentation_id = result.get("presentation_id", "unknown")
                credits_consumed = result.get("credits_consumed", 0)
                
                logger.info(f"✅ Presentation generated successfully!")
                logger.info(f"   Presentation ID: {presentation_id}")
                logger.info(f"   Download path: {download_path}")
                logger.info(f"   Credits consumed: {credits_consumed}")
                
                # Generate filename
                filename = f"presentation_{topic or 'generated'}.pptx".replace(' ', '_')[:100]
                
                # Handle local file path (ECS) vs external URL (public API)
                if download_path.startswith('/'):
                    # Local path - download file from ECS service
                    logger.info(f"Downloading file from ECS service: {download_path}")
                    download_url = f"{self.api_url}{download_path}"
                    
                    download_response = await client.get(download_url)
                    download_response.raise_for_status()
                    
                    file_data = download_response.content
                    logger.info(f"✅ Downloaded {len(file_data)} bytes from ECS")
                    
                    # Return base64 encoded data
                    base64_data = base64.b64encode(file_data).decode('utf-8')
                    
                    return {
                        "presentation_id": presentation_id,
                        "base64_data": base64_data,
                        "credits_consumed": credits_consumed,
                        "filename": filename,
                        "source": "ecs_presenton"
                    }, filename
                else:
                    # External URL - return path for direct download
                    return {
                        "presentation_id": presentation_id,
                        "path": download_path,
                        "edit_path": result.get("edit_path"),
                        "credits_consumed": credits_consumed,
                        "filename": filename
                    }, filename
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Presenton API HTTP error: {e.response.status_code} - {e.response.text}")
            raise ValueError(f"Presenton API error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            logger.error(f"Error calling Presenton API: {e}", exc_info=True)
            raise ValueError(f"Failed to generate PowerPoint using Presenton API: {str(e)}")


# Create singleton instance
presenton_service = PresentonService()
