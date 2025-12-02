import httpx
import logging
import asyncio
from typing import Tuple, Optional, Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)

class HeyGenService:
    """Service for integrating with HeyGen API for video generation"""
    
    def __init__(self):
        self.api_key = settings.HEYGEN_API_KEY
        self.api_url = settings.HEYGEN_API_URL.rstrip('/')
        self.image_key = settings.HEYGEN_IMAGE_KEY  # Image key for Avatar IV
        self.voice_id = settings.HEYGEN_VOICE_ID  # Configured voice ID
        self.video_orientation = settings.HEYGEN_VIDEO_ORIENTATION  # "portrait" or "landscape"
        self.fit = settings.HEYGEN_FIT  # "cover" or "contain"
        self.max_video_length = settings.HEYGEN_MAX_VIDEO_LENGTH  # Max 3 minutes
        self._cached_voices = None  # Cache for available voices
    
    async def generate_video(
        self,
        script: str,
        topic: Optional[str] = None,
        image_key: Optional[str] = None,
        voice_id: Optional[str] = None,
        video_orientation: Optional[str] = None,
        fit: Optional[str] = None,
        custom_motion_prompt: Optional[str] = None,
        enhance_custom_motion_prompt: bool = False,
        audio_url: Optional[str] = None,
        audio_asset_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate video using HeyGen API with Avatar IV (av4)
        
        Args:
            script: The script text for the video narration
            topic: Optional topic/title for the video
            image_key: Optional image key (if not provided, will use configured image_key)
            voice_id: Optional voice ID (if not provided, will use default voice)
            video_orientation: Optional orientation ("portrait" or "landscape")
            fit: Optional fit mode ("cover" or "contain")
            custom_motion_prompt: Optional custom motion prompt
            enhance_custom_motion_prompt: Whether to enhance custom motion prompt
            audio_url: Optional audio URL
            audio_asset_id: Optional audio asset ID
        
        Returns:
            Dict containing: video_id, video_url, status, credits_consumed, etc.
        """
        if not self.api_key:
            raise ValueError("HeyGen API key not configured")
        
        if not image_key and not self.image_key:
            raise ValueError("Image key is required for Avatar IV. Please set HEYGEN_IMAGE_KEY in environment variables.")
        
        try:
            logger.info("=" * 60)
            logger.info("HEYGEN SERVICE: Starting Avatar IV video generation")
            logger.info(f"   Base API URL: {self.api_url}")
            logger.info(f"   Image Key: {image_key or self.image_key}")
            logger.info(f"   Configured Voice ID: {self.voice_id or 'None (will fetch from API)'}")
            logger.info(f"   Video Orientation: {video_orientation or self.video_orientation}")
            logger.info(f"   Fit: {fit or self.fit}")
            logger.info(f"   Script length: {len(script)} chars")
            logger.info("=" * 60)
            
            # Estimate video length (assuming ~150 words per minute)
            words = len(script.split())
            estimated_seconds = (words / 150) * 60  # Convert to seconds
            estimated_minutes = estimated_seconds / 60
            
            logger.info(f"📊 INITIAL SCRIPT ANALYSIS:")
            logger.info(f"   Word count: {words} words")
            logger.info(f"   Character count: {len(script)} characters")
            logger.info(f"   Estimated duration: {estimated_seconds:.1f} seconds ({estimated_minutes:.1f} minutes)")
            
            # Enforce 120 seconds (2 minutes) maximum limit
            # Use 280 words to be extra safe (280 words = ~112 seconds at 150 wpm)
            # This leaves buffer for HeyGen's scene processing which might interpret scenes differently
            max_words = 280
            max_seconds = 120  # 2 minutes
            if words > max_words:
                words_list = script.split()
                original_word_count = len(words_list)
                script = ' '.join(words_list[:max_words])
                if not script.endswith(('.', '!', '?')):
                    script += "."
                words = len(script.split())
                estimated_seconds = (words / 150) * 60
                estimated_minutes = estimated_seconds / 60
                logger.warning(f"⚠️ Script exceeded limit. Truncated from {original_word_count} to {words} words.")
                logger.warning(f"   New estimated duration: {estimated_seconds:.1f} seconds ({estimated_minutes:.1f} minutes)")
            
            if estimated_seconds > max_seconds:
                raise ValueError(f"Script is too long. Maximum duration is {max_seconds} seconds (2 minutes), but estimated duration is {estimated_seconds:.1f} seconds ({estimated_minutes:.1f} minutes). Please shorten the script.")
            
            logger.info(f"✅ FINAL SCRIPT ANALYSIS:")
            logger.info(f"   Word count: {words} words")
            logger.info(f"   Character count: {len(script)} characters")
            logger.info(f"   Estimated duration: {estimated_seconds:.1f} seconds ({estimated_minutes:.1f} minutes)")
            logger.info(f"   Script preview (first 200 chars): {script[:200]}...")
            
            # Get voice ID
            try:
                voice_id_to_use = voice_id or await self._get_default_voice_id()
                logger.info(f"Selected voice ID: {voice_id_to_use}")
            except Exception as e:
                logger.error(f"Failed to get voice ID: {e}")
                raise ValueError(f"Unable to get voice ID. Please set HEYGEN_VOICE_ID in environment variables. Error: {str(e)}")
            
            # Prepare the request payload for Avatar IV API
            payload = {
                "image_key": image_key or self.image_key,
                "video_title": topic or "Generated Video",
                "script": script,
                "voice_id": voice_id_to_use,
                "video_orientation": video_orientation or self.video_orientation,
                "fit": fit or self.fit
            }
            
            # Add optional fields if provided
            if custom_motion_prompt:
                payload["custom_motion_prompt"] = custom_motion_prompt
                payload["enhance_custom_motion_prompt"] = enhance_custom_motion_prompt
            
            if audio_url:
                payload["audio_url"] = audio_url
            
            if audio_asset_id:
                payload["audio_asset_id"] = audio_asset_id
            
            # Make the request to HeyGen API v2 Avatar IV endpoint
            base_url = self.api_url.rstrip('/')
            if '/v2/video/av4/generate' in base_url:
                # Remove any existing path
                base_url = base_url.split('/v2')[0]
            endpoint = f"{base_url}/v2/video/av4/generate"
            headers = {
                "X-Api-Key": self.api_key,
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=600.0) as client:
                logger.info("=" * 80)
                logger.info("🚀 SUBMITTING TO HEYGEN AVATAR IV API")
                logger.info("=" * 80)
                logger.info(f"Endpoint: {endpoint}")
                logger.info(f"Headers: {list(headers.keys())}")
                logger.info(f"Payload structure:")
                logger.info(f"   - image_key: {payload['image_key']}")
                logger.info(f"   - video_title: {payload['video_title']}")
                logger.info(f"   - voice_id: {voice_id_to_use}")
                logger.info(f"   - video_orientation: {payload['video_orientation']}")
                logger.info(f"   - fit: {payload['fit']}")
                logger.info(f"   - script length: {len(payload['script'])} characters")
                logger.info(f"   - script word count: {len(payload['script'].split())} words")
                logger.info(f"   - script preview (first 300 chars): {payload['script'][:300]}...")
                logger.info(f"   - script preview (last 200 chars): ...{payload['script'][-200:]}")
                logger.info("=" * 80)
                
                response = await client.post(
                    endpoint,
                    json=payload,
                    headers=headers
                )
                
                response.raise_for_status()
                
                # Parse JSON response
                result = response.json()
                logger.info("=" * 80)
                logger.info("📥 HEYGEN AVATAR IV API RESPONSE")
                logger.info("=" * 80)
                logger.info(f"Status Code: {response.status_code}")
                logger.info(f"Response: {result}")
                logger.info("=" * 80)
                
                # Extract video information
                # Avatar IV API returns video_id at root level: {"video_id": "..."}
                video_id = result.get("video_id") or result.get("data", {}).get("video_id")
                if not video_id:
                    raise ValueError(f"HeyGen API did not return a video_id. Response: {result}")
                
                logger.info(f"✅ Avatar IV video generation started successfully!")
                logger.info(f"   Video ID: {video_id}")
                
                # Poll for video completion (HeyGen doesn't return URL immediately)
                logger.info("Polling for video status...")
                video_url = await self._poll_video_status(video_id)
                
                # Generate filename from topic or content
                filename = f"video_{topic or 'generated'}.mp4".replace(' ', '_')[:100]
                
                # Calculate credits consumed (Avatar IV pricing may vary, using 1 credit per minute as estimate)
                credits_consumed = int(estimated_minutes) + (1 if estimated_minutes % 1 > 0 else 0)
                
                return {
                    "video_id": video_id,
                    "video_url": video_url,
                    "status": "completed",
                    "credits_consumed": credits_consumed,
                    "filename": filename,
                    "estimated_duration": estimated_minutes
                }
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HeyGen API HTTP error: {e.response.status_code} - {e.response.text}")
            raise ValueError(f"HeyGen API error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            logger.error(f"Error calling HeyGen API: {e}", exc_info=True)
            raise ValueError(f"Failed to generate video using HeyGen: {str(e)}")
    
    async def _poll_video_status(self, video_id: str, max_attempts: int = 60, interval: int = 10) -> str:
        """
        Poll HeyGen API to check video generation status
        
        Uses HeyGen v1 API: GET /v1/video_status.get?video_id={video_id}
        
        Args:
            video_id: The video ID to check
            max_attempts: Maximum number of polling attempts
            interval: Seconds between polling attempts
        
        Returns:
            Video URL when ready
        """
        base_url = self.api_url.rstrip('/')
        if '/v2' in base_url:
            base_url = base_url.split('/v2')[0]
        
        # HeyGen uses v1 API for status checks: GET /v1/video_status.get?video_id={video_id}
        endpoint = f"{base_url}/v1/video_status.get"
        headers = {
            "X-Api-Key": self.api_key,
            "Accept": "application/json"
        }
        
        for attempt in range(max_attempts):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    # GET request with video_id as query parameter
                    response = await client.get(
                        endpoint,
                        params={"video_id": video_id},
                        headers=headers
                    )
                    
                    response.raise_for_status()
                    result = response.json()
                    
                    # HeyGen response format:
                    # {
                    #   "code": 100,
                    #   "message": "Success",
                    #   "data": {
                    #     "status": "completed",
                    #     "video_url": "https://...",
                    #     ...
                    #   }
                    # }
                    data = result.get("data", {})
                    status = data.get("status")
                    
                    logger.info(f"Video status check {attempt + 1}/{max_attempts}: {status}")
                    
                    if status == "completed":
                        video_url = data.get("video_url")
                        if video_url:
                            logger.info(f"✅ Video ready! URL: {video_url}")
                            return video_url
                        else:
                            # Construct URL from video_id if not provided (fallback)
                            logger.warning("Video completed but no URL in response, constructing URL...")
                            return f"{base_url}/v1/videos/{video_id}/video.mp4"
                    
                    elif status == "failed":
                        error = data.get("error", {})
                        error_code = error.get("code", "unknown") if isinstance(error, dict) else str(error)
                        error_message = error.get("message", str(error)) if isinstance(error, dict) else str(error)
                        error_detail = error.get("detail", "") if isinstance(error, dict) else ""
                        
                        logger.error("=" * 80)
                        logger.error("❌ HEYGEN VIDEO GENERATION FAILED")
                        logger.error("=" * 80)
                        logger.error(f"Error Code: {error_code}")
                        logger.error(f"Error Message: {error_message}")
                        if error_detail:
                            logger.error(f"Error Detail: {error_detail}")
                        logger.error(f"Full error data: {error}")
                        logger.error("=" * 80)
                        
                        raise ValueError(f"Video generation failed: {error}")
                    
                    # If status is "processing" or "pending", continue polling
                    if status in ["processing", "pending", "in_progress", "generating"]:
                        logger.debug(f"Video still {status}, will poll again in {interval} seconds...")
                    elif status is None:
                        logger.warning(f"Status is None in response: {result}")
                    
                    # Wait before next poll
                    await asyncio.sleep(interval)
                    
            except httpx.HTTPStatusError as e:
                logger.warning(f"Status check error: {e.response.status_code} - {e.response.text[:200]}")
                await asyncio.sleep(interval)
            except Exception as e:
                logger.warning(f"Error checking video status: {e}")
                await asyncio.sleep(interval)
        
        # If we get here, try to construct a download URL as fallback
        logger.warning(f"Polling timed out after {max_attempts * interval} seconds, attempting to construct video URL")
        return f"{base_url}/v1/videos/{video_id}/video.mp4"
    
    async def _get_default_photo_avatar_id(self) -> str:
        """Get default photo avatar ID - fetch from API if not configured"""
        # If avatar ID is configured, use it
        if self.avatar_id:
            return self.avatar_id
        
        # Otherwise, fetch available avatars and use the first photo avatar
        try:
            avatars = await self.list_avatars()
            if avatars:
                # Find first photo avatar that's actually available
                # Try to find avatars that are marked as available or have the right format
                for avatar in avatars:
                    avatar_type = avatar.get("type", "").lower() or avatar.get("avatar_type", "").lower()
                    # Check if avatar is available (some might be restricted)
                    is_available = avatar.get("available", True)  # Default to True if not specified
                    if not is_available:
                        continue
                    
                    if "photo" in avatar_type or avatar_type == "":
                        # Try different possible ID fields
                        avatar_id = (
                            avatar.get("avatar_id") or 
                            avatar.get("id") or 
                            avatar.get("avatarId") or
                            avatar.get("avatar_name")  # Sometimes the name is the ID
                        )
                        if avatar_id:
                            logger.info(f"Trying photo avatar: {avatar.get('name', avatar_id)} (ID: {avatar_id})")
                            return avatar_id
                
                # If no photo avatar found, use first available avatar
                for avatar in avatars:
                    is_available = avatar.get("available", True)
                    if not is_available:
                        continue
                    avatar_id = (
                        avatar.get("avatar_id") or 
                        avatar.get("id") or 
                        avatar.get("avatarId") or
                        avatar.get("avatar_name")
                    )
                    if avatar_id:
                        logger.info(f"Using first available avatar: {avatar.get('name', avatar_id)} (ID: {avatar_id})")
                        return avatar_id
        except Exception as e:
            logger.warning(f"Failed to fetch avatars: {e}")
        
        # Fallback: return empty string to let API error show what's available
        raise ValueError("No avatar ID configured and unable to fetch available avatars. Please set HEYGEN_AVATAR_ID in environment variables or check your API key.")
    
    async def _get_default_voice_id(self) -> str:
        """Get default voice ID - fetch from API if not configured"""
        # If voice ID is configured, use it
        if self.voice_id:
            return self.voice_id
        
        # Otherwise, fetch available voices and use the first one
        try:
            voices = await self.list_voices()
            if voices:
                first_voice = voices[0]
                voice_id = first_voice.get("voice_id") or first_voice.get("id")
                if voice_id:
                    logger.info(f"Using voice: {first_voice.get('name', voice_id)} (ID: {voice_id})")
                    return voice_id
        except Exception as e:
            logger.warning(f"Failed to fetch voices: {e}")
        
        # Fallback: return empty string to let API error show what's available
        raise ValueError("No voice ID configured and unable to fetch available voices. Please set HEYGEN_VOICE_ID in environment variables or check your API key.")
    
    async def list_avatars(self) -> list:
        """List available avatars from HeyGen"""
        if not self.api_key:
            raise ValueError("HeyGen API key not configured")
        
        # Use cached avatars if available
        if self._cached_avatars is not None:
            logger.debug(f"Using cached avatars ({len(self._cached_avatars)} found)")
            return self._cached_avatars
        
        logger.info("Fetching available avatars from HeyGen API...")
        
        try:
            # Try v2 API first
            endpoint = f"{self.api_url}/v2/avatars"
            headers = {
                "X-Api-Key": self.api_key,
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(endpoint, headers=headers)
                response.raise_for_status()
                result = response.json()
                avatars = result.get("data", {}).get("avatars", [])
                if avatars:
                    self._cached_avatars = avatars
                    logger.info(f"✓ Found {len(avatars)} avatar(s) from v2 API")
                    # Log first few avatars for debugging
                    for i, avatar in enumerate(avatars[:3], 1):
                        avatar_id = avatar.get("avatar_id") or avatar.get("id", "N/A")
                        avatar_name = avatar.get("name", "Unnamed")
                        logger.info(f"   {i}. {avatar_name} (ID: {avatar_id})")
                    return avatars
        except Exception as e:
            logger.warning(f"v2 avatars endpoint failed, trying v1: {e}")
        
        # Fallback to v1 API
        try:
            endpoint = f"{self.api_url}/v1/avatars"
            headers = {
                "X-Api-Key": self.api_key,
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(endpoint, headers=headers)
                response.raise_for_status()
                result = response.json()
                avatars = result.get("data", {}).get("avatars", [])
                if avatars:
                    self._cached_avatars = avatars
                    logger.info(f"✓ Found {len(avatars)} avatar(s) from v1 API")
                    # Log first few avatars for debugging
                    for i, avatar in enumerate(avatars[:3], 1):
                        avatar_id = avatar.get("avatar_id") or avatar.get("id", "N/A")
                        avatar_name = avatar.get("name", "Unnamed")
                        logger.info(f"   {i}. {avatar_name} (ID: {avatar_id})")
                    return avatars
        except Exception as e:
            logger.error(f"Error listing avatars: {e}", exc_info=True)
            return []
        
        logger.warning("No avatars found from either v1 or v2 API")
        return []
    
    async def list_voices(self) -> list:
        """List available voices from HeyGen"""
        if not self.api_key:
            raise ValueError("HeyGen API key not configured")
        
        # Use cached voices if available
        if self._cached_voices is not None:
            logger.debug(f"Using cached voices ({len(self._cached_voices)} found)")
            return self._cached_voices
        
        logger.info("Fetching available voices from HeyGen API...")
        
        try:
            # Try v2 API first
            endpoint = f"{self.api_url}/v2/voices"
            headers = {
                "X-Api-Key": self.api_key,
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(endpoint, headers=headers)
                response.raise_for_status()
                result = response.json()
                voices = result.get("data", {}).get("voices", [])
                if voices:
                    self._cached_voices = voices
                    logger.info(f"✓ Found {len(voices)} voice(s) from v2 API")
                    # Log first few voices for debugging
                    for i, voice in enumerate(voices[:3], 1):
                        voice_id = voice.get("voice_id") or voice.get("id", "N/A")
                        voice_name = voice.get("name", "Unnamed")
                        logger.info(f"   {i}. {voice_name} (ID: {voice_id})")
                    return voices
        except Exception as e:
            logger.warning(f"v2 voices endpoint failed, trying v1: {e}")
        
        # Fallback to v1 API
        try:
            endpoint = f"{self.api_url}/v1/voices"
            headers = {
                "X-Api-Key": self.api_key,
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(endpoint, headers=headers)
                response.raise_for_status()
                result = response.json()
                voices = result.get("data", {}).get("voices", [])
                if voices:
                    self._cached_voices = voices
                    logger.info(f"✓ Found {len(voices)} voice(s) from v1 API")
                    # Log first few voices for debugging
                    for i, voice in enumerate(voices[:3], 1):
                        voice_id = voice.get("voice_id") or voice.get("id", "N/A")
                        voice_name = voice.get("name", "Unnamed")
                        logger.info(f"   {i}. {voice_name} (ID: {voice_id})")
                    return voices
        except Exception as e:
            logger.error(f"Error listing voices: {e}", exc_info=True)
            return []
        
        logger.warning("No voices found from either v1 or v2 API")
        return []

# Create singleton instance
heygen_service = HeyGenService()

