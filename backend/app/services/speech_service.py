"""
Speech Service - Completely independent service for speech/monologue generation
Has its own configuration, parameters, and LLM settings
"""
import logging
import asyncio
import json
from typing import Dict, Any, Optional
from app.services.model_manager import model_manager
from app.core.config import settings

logger = logging.getLogger(__name__)

class SpeechServiceConfig:
    """Independent configuration for Speech Service"""
    # LLM Configuration
    TEMPERATURE: float = 0.7  # Moderate temperature for clear, focused speech
    MAX_TOKENS: int = 8000  # Sufficient for speeches
    MODEL_ID: str = "auto"
    
    # Content Configuration
    MIN_LENGTH: int = 500  # Minimum characters
    TARGET_LENGTH: int = 2000  # Target length for speeches
    
    @classmethod
    def from_env(cls):
        """Load configuration from environment variables if needed"""
        import os
        return cls(
            temperature=float(os.getenv("SPEECH_TEMPERATURE", cls.TEMPERATURE)),
            max_tokens=int(os.getenv("SPEECH_MAX_TOKENS", cls.MAX_TOKENS)),
            model_id=os.getenv("SPEECH_MODEL_ID", cls.MODEL_ID),
        )

class SpeechService:
    """Completely independent service for speech/monologue generation"""
    
    def __init__(self, config: Optional[SpeechServiceConfig] = None):
        self.config = config or SpeechServiceConfig()
        logger.info(f"SpeechService initialized with temperature={self.config.TEMPERATURE}, max_tokens={self.config.MAX_TOKENS}")
    
    async def generate_script(
        self,
        content: str,
        topic: Optional[str] = None,
        user_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate speech script - completely independent from other services"""
        try:
            logger.info(f"SpeechService: Generating script from {len(content)} characters")
            
            # Create prompt using this service's own configuration
            speech_prompt = self._create_prompt(content, topic)
            
            # Get LLM with this service's own parameters
            llm = model_manager.get_chat_model(
                model_id=self.config.MODEL_ID,
                temperature=self.config.TEMPERATURE
            )
            
            # Generate speech using this service's own max_tokens setting
            response = await self._invoke_llm(llm, speech_prompt)
            
            # Extract speech text
            speech = self._extract_response(response)
            
            logger.info(f"SpeechService: Generated script ({len(speech)} characters)")
            return speech
            
        except Exception as e:
            logger.error(f"SpeechService error: {e}", exc_info=True)
            raise ValueError(f"Speech generation failed: {e}")
    
    def _create_prompt(self, content: str, topic: Optional[str] = None) -> str:
        """Create speech prompt using this service's configuration"""
        return f"""Create a compelling, comprehensive, and well-structured speech or monologue by extracting ALL key information from the content below.

CRITICAL INSTRUCTIONS:
1. **EXTRACT ALL KEY POINTS**: Dig deep and extract ALL important information, features, benefits, details, and examples from the content. Don't just summarize - include specific details.

2. **BE COMPREHENSIVE**: Include all relevant information that would be valuable to the audience. Extract numbers, statistics, specific features, benefits, use cases, and technical details.

3. **STRUCTURE WELL**: Organize the speech logically with:
   - An engaging introduction that hooks the audience
   - Clear main points with supporting details
   - Compelling examples and real-world applications
   - A strong conclusion that reinforces key takeaways

4. **MAKE IT ENGAGING**: Use varied language, rhetorical devices, and enthusiasm. Make it sound like a professional speaker addressing an audience.

5. **BE THOROUGH**: Cover ALL major topics and details from the content. Don't skip important information.

**TOPIC:** {topic or 'the subject matter'}

**CONTENT TO LEARN FROM:**
{content}

Now create a comprehensive, engaging speech that transforms this information into a compelling monologue suitable for presentation."""
    
    async def _invoke_llm(self, llm, prompt: str):
        """Invoke LLM with this service's max_tokens configuration"""
        from langchain.schema import HumanMessage
        from langchain_openai import AzureChatOpenAI
        
        messages = [HumanMessage(content=prompt)]
        invoke_kwargs = {}
        
        # Add Cisco appkey if needed
        if isinstance(llm, AzureChatOpenAI) and settings.CISCO_APPKEY:
            user_data = {"appkey": settings.CISCO_APPKEY}
            invoke_kwargs["user"] = json.dumps(user_data)
        
        # Set max_tokens using this service's configuration
        max_tokens_value = self.config.MAX_TOKENS
        
        # Try to set max_tokens
        try:
            llm_with_max_tokens = llm.bind(max_tokens=max_tokens_value)
            response = await asyncio.to_thread(llm_with_max_tokens.invoke, messages, **invoke_kwargs)
            logger.debug(f"SpeechService: Set max_tokens={max_tokens_value} via bind()")
        except Exception:
            # Fallback - use default
            response = await asyncio.to_thread(llm.invoke, messages, **invoke_kwargs)
            logger.debug(f"SpeechService: Using default max_tokens")
        
        return response
    
    def _extract_response(self, response) -> str:
        """Extract text from LLM response"""
        if hasattr(response, 'content'):
            return response.content
        elif isinstance(response, str):
            return response
        else:
            return str(response)

# Global instance - can be customized per service
speech_service = SpeechService()

