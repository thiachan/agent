"""
Podcast Service - Completely independent service for podcast generation
Has its own configuration, parameters, and LLM settings
"""
import logging
import asyncio
import json
from typing import Dict, Any, Optional, Tuple
from app.services.model_manager import model_manager
from app.core.config import settings

logger = logging.getLogger(__name__)

class PodcastServiceConfig:
    """Independent configuration for Podcast Service"""
    # LLM Configuration
    TEMPERATURE: float = 0.95  # Higher temperature for creative, engaging dialogue with 10% creative freedom
    MAX_TOKENS: int = 16000  # Allow comprehensive, long-form scripts
    MODEL_ID: str = "auto"  # Use auto model selection
    
    # Content Configuration
    MIN_EXCHANGES: int = 15  # Minimum dialogue exchanges
    MAX_EXCHANGES: int = 40  # Maximum dialogue exchanges for comprehensive content
    MIN_SENTENCES_PER_TURN: int = 3
    MAX_SENTENCES_PER_TURN: int = 5
    
    # RAG Configuration (if needed)
    RAG_LIMIT: int = 20  # More chunks for comprehensive podcasts
    
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
    """Completely independent service for podcast generation"""
    
    def __init__(self, config: Optional[PodcastServiceConfig] = None):
        self.config = config or PodcastServiceConfig()
        logger.info(f"PodcastService initialized with temperature={self.config.TEMPERATURE}, max_tokens={self.config.MAX_TOKENS}")
    
    async def generate_script(
        self,
        content: str,
        topic: Optional[str] = None,
        user_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate podcast dialogue script - completely independent from other services"""
        try:
            logger.info(f"PodcastService: Generating script from {len(content)} characters")
            
            # Create prompt using this service's own configuration
            dialogue_prompt = self._create_prompt(content, topic)
            
            # Get LLM with this service's own parameters
            llm = model_manager.get_chat_model(
                model_id=self.config.MODEL_ID,
                temperature=self.config.TEMPERATURE
            )
            
            # Generate dialogue using this service's own max_tokens setting
            response = await self._invoke_llm(llm, dialogue_prompt)
            
            # Extract and validate dialogue
            dialogue = self._extract_response(response)
            dialogue = self._validate_dialogue_format(dialogue)
            
            logger.info(f"PodcastService: Generated script ({len(dialogue)} characters)")
            return dialogue
            
        except Exception as e:
            logger.error(f"PodcastService error: {e}", exc_info=True)
            raise ValueError(f"Podcast generation failed: {e}")
    
    def _create_prompt(self, content: str, topic: Optional[str] = None) -> str:
        """Create podcast prompt using this service's configuration"""
        return f"""You are creating a professional, engaging podcast dialogue between a knowledgeable Host and an expert Guest. Your goal is to transform the comprehensive information below into a natural, flowing conversation that educates and engages listeners.

**CREATIVE FREEDOM (10%):**
- You have 10% creative freedom - you don't need to follow the content 100% strictly
- Feel free to add natural conversational elements, engaging transitions, and creative phrasing
- You can slightly rephrase, expand, or add context to make the dialogue more engaging
- The goal is natural conversation, not verbatim transcription - be creative while staying true to the core information

**YOUR ROLE:**
- Study the content deeply and understand ALL key concepts, details, examples, and insights
- Create a dialogue that feels natural and conversational, not robotic or scripted
- The Host should ask thoughtful questions and guide the conversation with personality
- The Guest should provide expert insights, real-world examples, and detailed explanations with enthusiasm
- Both speakers should sound intelligent, engaging, and passionate about the topic
- Add your own creative touches: engaging questions, natural reactions, conversational flow

**CONTENT ANALYSIS:**
- Extract ALL important information: concepts, features, benefits, use cases, examples, statistics, technical details
- Identify the main themes and how they connect
- Find compelling examples and real-world applications
- Note any specific details, numbers, or facts that add credibility
- Understand the full context and depth of the topic
- But remember: you can creatively present this information - it doesn't have to be word-for-word

**DIALOGUE CREATION:**
- Create a natural conversation flow - Host asks questions, Guest provides detailed answers
- Each speaker turn should be substantial ({self.config.MIN_SENTENCES_PER_TURN}-{self.config.MAX_SENTENCES_PER_TURN} sentences) with complete thoughts
- Use varied language - don't repeat the same phrases, be creative with your word choices
- Include transitions and natural follow-up questions that feel spontaneous
- Make it engaging with enthusiasm, examples, and practical insights
- Add personality: humor, curiosity, excitement, thoughtful pauses
- Cover ALL major topics comprehensively - but present them creatively, not robotically

**FORMATTING:**
- ALWAYS alternate between [Host] and [Guest] - never have two of the same speaker in a row
- Start with an engaging introduction that hooks the listener
- Develop the conversation logically through all key topics with natural flow
- End with a thoughtful conclusion that summarizes key takeaways memorably

**LENGTH:**
- For comprehensive content: Create {self.config.MIN_EXCHANGES}-{self.config.MAX_EXCHANGES}+ exchanges to thoroughly cover everything
- For shorter content: Create {self.config.MIN_EXCHANGES} exchanges minimum
- Quality over brevity - be thorough and engaging

**TOPIC:** {topic or 'the subject matter'}

**CONTENT TO LEARN FROM (use this as your foundation, but feel free to be creative in how you present it):**
{content}

Now create an engaging, intelligent podcast dialogue that transforms this information into a natural, creative conversation. Make it sound like two experts having a fascinating, spontaneous discussion - not a dry recitation of facts. Use your creative freedom to make it more engaging while staying true to the core information."""
    
    async def _invoke_llm(self, llm, prompt: str):
        """Invoke LLM with this service's max_tokens configuration"""
        from langchain.schema import HumanMessage
        from langchain_openai import AzureChatOpenAI, ChatOpenAI
        from langchain_aws import ChatBedrock, BedrockLLM
        
        messages = [HumanMessage(content=prompt)]
        invoke_kwargs = {}
        
        # Add Cisco appkey if needed
        if isinstance(llm, AzureChatOpenAI) and settings.CISCO_APPKEY:
            user_data = {"appkey": settings.CISCO_APPKEY}
            invoke_kwargs["user"] = json.dumps(user_data)
        
        # Set max_tokens using this service's configuration
        max_tokens_value = self.config.MAX_TOKENS
        response = None
        
        # Method 1: Try bind() first
        try:
            llm_with_max_tokens = llm.bind(max_tokens=max_tokens_value)
            response = await asyncio.to_thread(llm_with_max_tokens.invoke, messages, **invoke_kwargs)
            logger.debug(f"PodcastService: Set max_tokens={max_tokens_value} via bind()")
        except Exception as bind_error:
            logger.debug(f"PodcastService: bind() failed, trying alternatives: {bind_error}")
            
            # Method 2: Try invoke kwargs
            try:
                invoke_kwargs_with_tokens = {**invoke_kwargs, "max_tokens": max_tokens_value}
                response = await asyncio.to_thread(llm.invoke, messages, **invoke_kwargs_with_tokens)
                logger.debug(f"PodcastService: Set max_tokens={max_tokens_value} via invoke kwargs")
            except Exception as kwarg_error:
                logger.debug(f"PodcastService: max_tokens in kwargs failed: {kwarg_error}")
                
                # Method 3: Try model_kwargs
                try:
                    if hasattr(llm, 'model_kwargs'):
                        original_kwargs = llm.model_kwargs or {}
                        llm.model_kwargs = {**original_kwargs, "max_tokens": max_tokens_value}
                        response = await asyncio.to_thread(llm.invoke, messages, **invoke_kwargs)
                        llm.model_kwargs = original_kwargs  # Restore
                        logger.debug(f"PodcastService: Set max_tokens={max_tokens_value} via model_kwargs")
                    else:
                        raise ValueError("No model_kwargs available")
                except Exception as model_kwarg_error:
                    # Method 4: Fallback - use default
                    logger.warning(f"PodcastService: Could not set max_tokens, using default: {model_kwarg_error}")
                    response = await asyncio.to_thread(llm.invoke, messages, **invoke_kwargs)
        
        if response is None:
            raise ValueError("Failed to get response from LLM")
        
        return response
    
    def _extract_response(self, response) -> str:
        """Extract text from LLM response"""
        if hasattr(response, 'content'):
            return response.content
        elif isinstance(response, str):
            return response
        else:
            return str(response)
    
    def _validate_dialogue_format(self, dialogue: str) -> str:
        """Validate and fix dialogue format issues"""
        if not dialogue:
            return dialogue
        
        lines = dialogue.split('\n')
        fixed_lines = []
        last_speaker = None
        
        for line in lines:
            line = line.strip()
            if not line:
                fixed_lines.append('')
                continue
            
            # Check if this line starts with a speaker tag
            if line.startswith('[Host]') or line.startswith('[host]'):
                current_speaker = '[Host]'
            elif line.startswith('[Guest]') or line.startswith('[guest]'):
                current_speaker = '[Guest]'
            else:
                # Not a speaker line, keep as is
                fixed_lines.append(line)
                continue
            
            # Fix capitalization
            if line.startswith('[host]'):
                line = '[Host]' + line[6:]
            elif line.startswith('[guest]'):
                line = '[Guest]' + line[7:]
            
            # Check for consecutive same speakers
            if last_speaker == current_speaker:
                # Alternate to the other speaker
                if current_speaker == '[Host]':
                    line = '[Guest]' + line[6:]
                    current_speaker = '[Guest]'
                else:
                    line = '[Host]' + line[7:]
                    current_speaker = '[Host]'
                logger.debug(f"PodcastService: Fixed consecutive speaker: changed to {current_speaker}")
            
            fixed_lines.append(line)
            last_speaker = current_speaker
        
        return '\n'.join(fixed_lines)

# Global instance - can be customized per service
podcast_service = PodcastService()

