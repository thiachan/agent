"""
Podcast Service - Completely independent service for podcast/dialogue generation
Has its own configuration, parameters, and LLM settings
"""
import logging
import asyncio
import json
from typing import Dict, Any, Optional, List
from app.services.model_manager import model_manager
from app.core.config import settings

logger = logging.getLogger(__name__)

class PodcastServiceConfig:
    """Independent configuration for Podcast Service"""
    # LLM Configuration
    TEMPERATURE: float = 0.9  # Higher temperature for more natural, varied dialogue
    MAX_TOKENS: int = 12000  # More tokens for longer podcast dialogues
    MODEL_ID: str = "auto"
    
    # Content Configuration
    MIN_LENGTH: int = 1000  # Minimum characters
    TARGET_LENGTH: int = 4000  # Target length for podcasts
    
    @classmethod
    def from_env(cls):
        """Load configuration from environment variables if needed"""
        import os
        return cls(
            temperature=float(os.getenv("PODCAST_TEMPERATURE", cls.TEMPERATURE)),
            max_tokens=int(os.getenv("PODCAST_MAX_TOKENS", cls.MAX_TOKENS)),
            model_id=os.getenv("PODCAST_MODEL_ID", cls.MODEL_ID),
        )

class PodcastService:
    """Completely independent service for podcast/dialogue generation"""
    
    def __init__(self, config: Optional[PodcastServiceConfig] = None):
        self.config = config or PodcastServiceConfig()
        logger.info(f"PodcastService initialized with temperature={self.config.TEMPERATURE}, max_tokens={self.config.MAX_TOKENS}")
    
    async def generate_script(
        self,
        content: str,
        topic: Optional[str] = None,
        user_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate podcast script - completely independent from other services"""
        try:
            logger.info(f"PodcastService: Generating script from {len(content)} characters")
            
            # Create prompt using this service's own configuration
            podcast_prompt = self._create_prompt(content, topic)
            
            # Get LLM with this service's own parameters
            llm = model_manager.get_chat_model(
                model_id=self.config.MODEL_ID,
                temperature=self.config.TEMPERATURE
            )
            
            # Generate podcast using this service's own max_tokens setting
            response = await self._invoke_llm(llm, podcast_prompt)
            
            # Extract podcast text
            podcast = self._extract_response(response)
            
            logger.info(f"PodcastService: Generated script ({len(podcast)} characters)")
            return podcast
            
        except Exception as e:
            logger.error(f"PodcastService error: {e}", exc_info=True)
            raise ValueError(f"Podcast generation failed: {e}")
    
    def _create_prompt(self, content: str, topic: Optional[str] = None) -> str:
        """Create podcast prompt using this service's configuration"""
        return f"""Create an engaging, comprehensive, and natural-sounding podcast dialogue by extracting ALL key information from the content below.

CRITICAL INSTRUCTIONS:
1. **EXTRACT ALL KEY POINTS**: Extract ALL important information, features, benefits, details, examples, and insights from the content. Be thorough and comprehensive.

2. **NATURAL DIALOGUE**: Create a conversation between Host and Guest that flows naturally. Use conversational language, questions, answers, and back-and-forth exchanges.

3. **BE COMPREHENSIVE**: Include all relevant information that would be valuable to listeners. Cover numbers, statistics, specific features, benefits, use cases, and technical details.

4. **STRUCTURE WELL**: Organize the podcast logically with:
   - An engaging introduction where Host introduces the topic and Guest
   - Multiple segments covering different aspects of the topic
   - Natural transitions between topics
   - A strong conclusion that summarizes key takeaways

5. **MAKE IT ENGAGING**: Use varied language, enthusiasm, questions, and natural conversational elements. Make it sound like a real podcast conversation.

6. **FORMAT**: Use this exact format:
   Host: [dialogue]
   Guest: [dialogue]
   Host: [dialogue]
   Guest: [dialogue]
   (and so on...)

**TOPIC:** {topic or 'the subject matter'}

**CONTENT TO LEARN FROM:**
{content}

Now create a comprehensive, engaging podcast dialogue that transforms this information into a natural conversation suitable for audio presentation."""
    
    async def _invoke_llm(self, llm, prompt: str):
        """Invoke LLM with this service's max_tokens configuration"""
        from langchain_core.messages import HumanMessage
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
            logger.debug(f"PodcastService: Set max_tokens={max_tokens_value} via bind()")
        except Exception:
            # Fallback - use default
            response = await asyncio.to_thread(llm.invoke, messages, **invoke_kwargs)
            logger.debug(f"PodcastService: Using default max_tokens")
        
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
podcast_service = PodcastService()





