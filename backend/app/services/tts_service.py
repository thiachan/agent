import os
import base64
import logging
import warnings
from typing import Tuple, Optional, List
from io import BytesIO
from app.core.config import settings

# Suppress pydub/ffmpeg warnings at module level
warnings.filterwarnings("ignore", category=RuntimeWarning, module="pydub")

logger = logging.getLogger(__name__)

class TTSService:
    """Service for converting text to speech audio files with OpenAI TTS"""
    
    def __init__(self):
        self.supported_formats = ["mp3", "wav"]
        self.default_language = "en"
        # OpenAI TTS voices: alloy, echo, fable, onyx, nova, shimmer
        self.openai_voices = {
            "host": settings.OPENAI_TTS_VOICE_HOST or "nova",
            "guest": settings.OPENAI_TTS_VOICE_GUEST or "onyx"
        }
    
    def text_to_speech(
        self, 
        text: str, 
        audio_format: str = "mp3", 
        language: str = "en",
        slow: bool = False,
        use_dialogue: bool = True
    ) -> bytes:
        """
        Convert text to speech audio
        
        Args:
            text: Text to convert to speech
            audio_format: Output format ("mp3" or "wav")
            language: Language code (default: "en")
            slow: Whether to speak slowly (default: False)
        
        Returns:
            bytes: Audio file data
        """
        if audio_format not in self.supported_formats:
            raise ValueError(f"Unsupported audio format: {audio_format}. Supported: {self.supported_formats}")
        
        # Try OpenAI TTS first (high quality, multiple voices)
        if settings.OPENAI_API_KEY:
            try:
                return self._text_to_speech_openai(text, audio_format, use_dialogue)
            except Exception as e:
                logger.warning(f"OpenAI TTS failed: {e}. Falling back to gTTS.")
        
        # Fallback to gTTS if OpenAI not available
        try:
            return self._text_to_speech_gtts(text, audio_format, language, slow)
        except Exception as e:
            logger.error(f"TTS conversion failed: {e}", exc_info=True)
            raise ValueError(f"TTS conversion failed: {str(e)}")
    
    def _text_to_speech_openai(
        self, 
        text: str, 
        audio_format: str = "mp3",
        use_dialogue: bool = True
    ) -> bytes:
        """Convert text to speech using OpenAI TTS API with dialogue support"""
        try:
            from openai import OpenAI
            
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            
            # Check if text contains dialogue markers
            has_dialogue = use_dialogue and ("[Host]" in text or "[Guest]" in text or "Host:" in text or "Guest:" in text)
            
            if has_dialogue:
                # Parse dialogue and generate with different voices
                return self._generate_dialogue_audio(client, text, audio_format)
            else:
                # Single voice generation
                response = client.audio.speech.create(
                    model="tts-1",  # or "tts-1-hd" for higher quality (more expensive)
                    voice=self.openai_voices["host"],
                    input=text[:4096],  # OpenAI TTS limit
                    response_format=audio_format
                )
                
                audio_data = b""
                for chunk in response.iter_bytes():
                    audio_data += chunk
                
                logger.info(f"Successfully converted {len(text)} characters to {audio_format.upper()} audio using OpenAI TTS")
                return audio_data
                
        except ImportError:
            raise ValueError("OpenAI library not installed. Install with: pip install openai")
        except Exception as e:
            logger.error(f"OpenAI TTS error: {e}", exc_info=True)
            raise
    
    def _generate_dialogue_audio(self, client, dialogue_text: str, audio_format: str) -> bytes:
        """Generate audio with different voices for Host and Guest"""
        # Parse dialogue into segments
        dialogue_segments = self._parse_dialogue(dialogue_text)
        
        audio_data_list = []
        
        for i, segment in enumerate(dialogue_segments):
            speaker = segment["speaker"]
            text = segment["text"]
            
            if not text.strip():
                continue
            
            # Determine voice based on speaker
            if speaker.lower() in ["host", "host:"]:
                voice = self.openai_voices["host"]
            elif speaker.lower() in ["guest", "guest:"]:
                voice = self.openai_voices["guest"]
            else:
                # Default to host voice
                voice = self.openai_voices["host"]
            
            # Generate audio for this segment
            try:
                response = client.audio.speech.create(
                    model="tts-1",  # or "tts-1-hd" for higher quality
                    voice=voice,
                    input=text[:4096],
                    response_format=audio_format  # Use requested format directly
                )
                
                segment_audio = b""
                for chunk in response.iter_bytes():
                    segment_audio += chunk
                
                if segment_audio:
                    audio_data_list.append(segment_audio)
                    logger.info(f"✓ Generated audio segment {i+1}/{len(dialogue_segments)} for {speaker} ({len(segment_audio)} bytes)")
                else:
                    logger.warning(f"Empty audio segment {i+1} for {speaker}")
                
            except Exception as e:
                logger.error(f"✗ Failed to generate audio for segment {i+1} ({speaker}): {e}", exc_info=True)
                continue
        
        if not audio_data_list:
            logger.error(f"No audio segments generated from {len(dialogue_segments)} dialogue segments")
            raise ValueError("No audio segments generated")
        
        logger.info(f"Successfully generated {len(audio_data_list)} audio segments, attempting to merge...")
        
        # Try to merge using pydub if available and ffmpeg is installed
        try:
            merged_audio = self._merge_audio_segments(audio_data_list, audio_format)
            logger.info(f"✓ Successfully merged {len(audio_data_list)} segments using pydub/ffmpeg")
            return merged_audio
        except Exception as merge_error:
            logger.warning(f"⚠ Audio merging with pydub failed: {merge_error}")
            logger.info("Falling back to simple MP3 concatenation (works without ffmpeg)")
            # Fallback: concatenate MP3 files directly (works without ffmpeg, may have small gaps)
            try:
                concatenated = self._simple_concatenate_audio(audio_data_list)
                logger.info(f"✓ Successfully concatenated {len(audio_data_list)} MP3 segments")
                return concatenated
            except Exception as concat_error:
                logger.error(f"✗ Simple concatenation also failed: {concat_error}")
                # Last resort: return first segment (better than nothing)
                logger.warning(f"⚠ Returning first segment only ({len(audio_data_list[0])} bytes)")
                return audio_data_list[0]
    
    def _merge_audio_segments(self, audio_data_list: List[bytes], audio_format: str) -> bytes:
        """Merge multiple audio segments into one file"""
        try:
            import warnings
            # Suppress pydub/ffmpeg warnings
            warnings.filterwarnings("ignore", category=RuntimeWarning, module="pydub")
            
            from pydub import AudioSegment
            from io import BytesIO
            
            # Try to set pydub to use ffmpeg
            try:
                AudioSegment.converter = "ffmpeg"
            except:
                pass
            
            audio_segments = []
            
            for i, audio_data in enumerate(audio_data_list):
                try:
                    # Load audio segment
                    if audio_format == "mp3":
                        audio_seg = AudioSegment.from_mp3(BytesIO(audio_data))
                    elif audio_format == "wav":
                        audio_seg = AudioSegment.from_wav(BytesIO(audio_data))
                    else:
                        # Try MP3 as default
                        audio_seg = AudioSegment.from_mp3(BytesIO(audio_data))
                    
                    # Add small pause between speakers (500ms) except for first segment
                    if audio_segments:
                        pause = AudioSegment.silent(duration=500)
                        audio_seg = pause + audio_seg
                    
                    audio_segments.append(audio_seg)
                except Exception as e:
                    logger.warning(f"Failed to load audio segment {i+1}: {e}. This may require ffmpeg installation.")
                    # If pydub fails, we'll fall back to simple concatenation
                    raise
            
            # Combine all audio segments
            combined_audio = sum(audio_segments)
            
            # Export in requested format
            output_buffer = BytesIO()
            combined_audio.export(output_buffer, format=audio_format)
            output_buffer.seek(0)
            
            logger.info(f"Successfully merged {len(audio_segments)} audio segments")
            return output_buffer.getvalue()
            
        except Exception as e:
            # If merging fails (likely due to missing ffmpeg), raise to trigger fallback
            raise Exception(f"Audio merging requires ffmpeg: {str(e)}")
    
    def _simple_concatenate_audio(self, audio_data_list: List[bytes]) -> bytes:
        """Simple concatenation of MP3 files (works without ffmpeg, may have small gaps)"""
        # MP3 files can be concatenated directly at byte level
        # This works but may have small gaps or clicks between segments
        # For proper merging with pauses, install ffmpeg
        total_size = sum(len(seg) for seg in audio_data_list)
        combined = b"".join(audio_data_list)
        logger.info(f"Concatenated {len(audio_data_list)} MP3 segments ({total_size} bytes total)")
        logger.info("Note: For smoother merging with pauses, install ffmpeg")
        return combined
    
    def _parse_dialogue(self, text: str) -> List[dict]:
        """Parse dialogue text into speaker segments"""
        segments = []
        lines = text.split('\n')
        current_speaker = None
        current_text = []
        
        for line in lines:
            line = line.strip()
            if not line:
                # Empty line - save current segment if any
                if current_speaker and current_text:
                    segments.append({
                        "speaker": current_speaker,
                        "text": " ".join(current_text)
                    })
                    current_text = []
                continue
            
            # Check for speaker labels: [Host]:, [Guest]:, Host:, Guest:
            if line.startswith('[') and ']:' in line:
                # Format: [Host]: text or [Guest]: text
                parts = line.split(']:', 1)
                speaker = parts[0].strip('[').strip()
                text_content = parts[1].strip() if len(parts) > 1 else ""
                
                # Save previous segment
                if current_speaker and current_text:
                    segments.append({
                        "speaker": current_speaker,
                        "text": " ".join(current_text)
                    })
                
                # Start new segment
                current_speaker = speaker
                current_text = [text_content] if text_content else []
                
            elif line.startswith(('Host:', 'Guest:')):
                # Format: Host: text or Guest: text
                parts = line.split(':', 1)
                speaker = parts[0].strip()
                text_content = parts[1].strip() if len(parts) > 1 else ""
                
                # Save previous segment
                if current_speaker and current_text:
                    segments.append({
                        "speaker": current_speaker,
                        "text": " ".join(current_text)
                    })
                
                # Start new segment
                current_speaker = speaker
                current_text = [text_content] if text_content else []
                
            else:
                # Continuation of current speaker's text
                if current_speaker:
                    current_text.append(line)
                else:
                    # No speaker identified, treat as host
                    current_speaker = "Host"
                    current_text = [line]
        
        # Save last segment
        if current_speaker and current_text:
            segments.append({
                "speaker": current_speaker,
                "text": " ".join(current_text)
            })
        
        return segments
    
    def _text_to_speech_gtts(
        self, 
        text: str, 
        audio_format: str = "mp3", 
        language: str = "en",
        slow: bool = False
    ) -> bytes:
        """Fallback: Convert text to speech using gTTS"""
        try:
            from gtts import gTTS
            
            # Clean text - remove speaker labels
            cleaned_text = self._clean_dialogue_text(text)
            
            # Create TTS object
            tts = gTTS(text=cleaned_text, lang=language, slow=slow)
            
            # Generate audio to bytes buffer
            audio_buffer = BytesIO()
            tts.write_to_fp(audio_buffer)
            audio_buffer.seek(0)
            
            audio_data = audio_buffer.getvalue()
            
            # Convert MP3 to WAV if needed
            if audio_format == "wav":
                audio_data = self._convert_mp3_to_wav(audio_data)
            
            logger.info(f"Successfully converted {len(text)} characters to {audio_format.upper()} audio using gTTS")
            return audio_data
            
        except ImportError:
            raise ValueError("gTTS library not installed. Install with: pip install gtts")
    
    def _clean_dialogue_text(self, text: str) -> str:
        """Clean dialogue text for TTS by removing speaker labels and formatting"""
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Remove speaker labels like [Host]: or [Guest]:
            if line.startswith('[') and ']:' in line:
                # Extract text after the label
                parts = line.split(']:', 1)
                if len(parts) > 1:
                    line = parts[1].strip()
                else:
                    # If no text after label, skip this line
                    continue
            
            # Skip markdown-style headers or metadata
            if line.startswith('#') or line.startswith('---') or line.startswith('Note:'):
                continue
            
            if line:
                cleaned_lines.append(line)
        
        # Join with periods for natural pauses
        cleaned_text = '. '.join(cleaned_lines)
        
        # Add natural pauses for dialogue
        cleaned_text = cleaned_text.replace('[Host]', 'Host says')
        cleaned_text = cleaned_text.replace('[Guest]', 'Guest says')
        
        return cleaned_text
    
    def _convert_mp3_to_wav(self, mp3_data: bytes) -> bytes:
        """Convert MP3 audio data to WAV format"""
        try:
            import warnings
            # Suppress pydub/ffmpeg warnings
            warnings.filterwarnings("ignore", category=RuntimeWarning, module="pydub")
            
            from pydub import AudioSegment
            from io import BytesIO
            
            # Load MP3 from bytes
            audio = AudioSegment.from_mp3(BytesIO(mp3_data))
            
            # Export as WAV
            wav_buffer = BytesIO()
            audio.export(wav_buffer, format="wav")
            wav_buffer.seek(0)
            
            return wav_buffer.getvalue()
        except ImportError:
            logger.warning("pydub not available for WAV conversion. Returning MP3 data.")
            return mp3_data
        except Exception as e:
            logger.error(f"Error converting MP3 to WAV: {e}")
            # Return MP3 as fallback
            return mp3_data
    
    def text_to_speech_dialogue(
        self,
        text: str,
        audio_format: str = "mp3",
        language: str = "en",
        use_dialogue: bool = True
    ) -> bytes:
        """
        Wrapper for text_to_speech that supports dialogue parsing control.
        Use use_dialogue=False for monologue/speech generation (single voice).
        """
        return self.text_to_speech(text, audio_format, language, slow=False, use_dialogue=use_dialogue)
    
    def text_to_speech_base64(
        self, 
        text: str, 
        audio_format: str = "mp3", 
        language: str = "en"
    ) -> str:
        """Convert text to speech and return as base64 encoded string"""
        audio_data = self.text_to_speech(text, audio_format, language)
        return base64.b64encode(audio_data).decode('utf-8')

# Global instance
tts_service = TTSService()

