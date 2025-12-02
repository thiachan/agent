from typing import Dict, List, Optional, Literal, Union
from langchain_openai import ChatOpenAI, OpenAIEmbeddings, AzureChatOpenAI
from langchain_aws import ChatBedrock, BedrockLLM
from app.core.config import settings
import boto3
import base64
import httpx
import time
import logging

logger = logging.getLogger(__name__)

ModelProvider = Literal["openai", "bedrock", "auto"]

class ModelManager:
    """Manages multiple AI models from different providers"""
    
    def __init__(self):
        self.bedrock_client = None
        self.cisco_access_token = None
        self.cisco_token_expires_at = None  # Track token expiration time
        self._initialize_bedrock()
        self._initialize_cisco()
        self.available_models = self._load_available_models()
    
    def _initialize_bedrock(self):
        """Initialize AWS Bedrock client if credentials are available"""
        # Bedrock is now hidden, but keep initialization for fallback
        if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
            self.bedrock_client = boto3.client(
                'bedrock-runtime',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION
            )
    
    def _initialize_cisco(self):
        """Initialize Cisco OpenAI endpoint access token"""
        if settings.CISCO_CLIENT_ID and settings.CISCO_CLIENT_SECRET:
            try:
                # Get OAuth2 access token using client credentials flow
                token_url = "https://id.cisco.com/oauth2/default/v1/token"
                credentials = base64.b64encode(
                    f"{settings.CISCO_CLIENT_ID}:{settings.CISCO_CLIENT_SECRET}".encode()
                ).decode()
                
                response = httpx.post(
                    token_url,
                    headers={
                        "Authorization": f"Basic {credentials}",
                        "Content-Type": "application/x-www-form-urlencoded"
                    },
                    data={"grant_type": "client_credentials"},
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    token_data = response.json()
                    self.cisco_access_token = token_data.get("access_token")
                    
                    # Track token expiration (tokens typically expire in 3600 seconds / 1 hour)
                    expires_in = token_data.get("expires_in", 3600)  # Default to 1 hour if not provided
                    # Set expiration time with 5 minute buffer to refresh early
                    self.cisco_token_expires_at = time.time() + expires_in - 300
                    
                    logger.info(f"Cisco OAuth2 token obtained successfully (expires in {expires_in}s)")
                else:
                    logger.warning(f"Failed to get Cisco token: {response.status_code} - {response.text}")
            except Exception as e:
                logger.warning(f"Failed to initialize Cisco authentication: {e}", exc_info=True)
    
    def _get_cisco_token(self) -> Optional[str]:
        """Get or refresh Cisco access token (auto-refreshes if expired)"""
        # Check if token is missing or expired (with 5 minute buffer)
        current_time = time.time()
        if (not self.cisco_access_token or 
            not self.cisco_token_expires_at or 
            current_time >= self.cisco_token_expires_at):
            logger.info("Cisco token expired or missing, refreshing...")
            self._initialize_cisco()
        return self.cisco_access_token
    
    def _load_available_models(self) -> List[Dict]:
        """Load all available models from configuration - Only Cisco GPT-4.1 for RAG/chat"""
        models = []
        
        # Only Cisco GPT-4.1 for RAG ingestion and prompt handling
        if settings.CISCO_CLIENT_ID and settings.CISCO_CLIENT_SECRET:
            models.append({
                "id": "cisco-gpt-4.1",
                "name": "GPT-4.1 (Cisco)",
                "provider": "cisco",
                "model_id": "gpt-4.1",
                "type": "chat"
            })
        
        return models
    
    def get_chat_model(self, model_id: Optional[str] = None, temperature: float = 0) -> Union[ChatOpenAI, AzureChatOpenAI, ChatBedrock, BedrockLLM]:
        """Get a chat model instance"""
        # If no model_id or "auto", default to cisco-gpt-4.1
        if model_id == "auto" or not model_id:
            model_id = "cisco-gpt-4.1"
        
        # Reload models to ensure we have the latest configuration
        available_models = self._load_available_models()
        model_info = next((m for m in available_models if m["id"] == model_id), None)
        if not model_info:
            # Fallback to default
            return self._get_default_model(temperature)
        
        provider = model_info["provider"]
        model_identifier = model_info["model_id"]
        
        if provider == "cisco":
            # Cisco uses Azure OpenAI-compatible endpoint
            token = self._get_cisco_token()
            if not token:
                raise ValueError("Failed to obtain Cisco access token. Check CISCO_CLIENT_ID and CISCO_CLIENT_SECRET.")
            
            # Extract deployment name from endpoint or use configured override
            # Endpoint format: https://chat-ai.cisco.com/openai/deployments/gpt-4.1/chat/completions
            # Deployment name: gpt-4.1 (or gpt-4o-mini, etc.)
            if settings.CISCO_DEPLOYMENT:
                # Use explicitly configured deployment name
                deployment_name = settings.CISCO_DEPLOYMENT
            else:
                # Extract from endpoint URL
                endpoint_parts = settings.CISCO_ENDPOINT.split("/")
                deployment_name = None
                for i, part in enumerate(endpoint_parts):
                    if part == "deployments" and i + 1 < len(endpoint_parts):
                        deployment_name = endpoint_parts[i + 1]
                        break
                
                if not deployment_name:
                    # Fallback: use model_identifier or default to gpt-4.1
                    deployment_name = model_identifier if model_identifier else "gpt-4.1"
            
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Creating AzureChatOpenAI for Cisco with deployment: {deployment_name}")
            
            # Cisco uses Azure OpenAI format with api-key header
            # Use AzureChatOpenAI which supports api-key header natively
            azure_endpoint = "https://chat-ai.cisco.com"
            api_version = "2024-08-01-preview"
            
            return AzureChatOpenAI(
                azure_endpoint=azure_endpoint,
                azure_deployment=deployment_name,
                openai_api_key=token,  # This will be used as api-key header
                openai_api_version=api_version,
                temperature=temperature
            )
        elif provider == "openai":
            return ChatOpenAI(
                model_name=model_identifier,
                openai_api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL,
                temperature=temperature
            )
        elif provider == "bedrock":
            if not self.bedrock_client:
                raise ValueError("AWS Bedrock client not initialized. Check your AWS credentials.")
            
            # Clean up model ID - remove region prefixes and extract from ARN if needed
            if model_identifier.startswith("arn:aws:bedrock"):
                # Extract model ID from ARN
                parts = model_identifier.split("/")
                if len(parts) > 1:
                    actual_model_id = parts[-1]  # Get model:version part
                else:
                    actual_model_id = model_identifier.split(":")[-1]
                
                # Extract region from ARN if different
                arn_parts = model_identifier.split(":")
                if len(arn_parts) >= 4:
                    arn_region = arn_parts[3]
                    use_region = arn_region if arn_region != settings.AWS_REGION else settings.AWS_REGION
                else:
                    use_region = settings.AWS_REGION
            else:
                actual_model_id = model_identifier
                use_region = settings.AWS_REGION
            
            # Remove region prefixes like "us.", "eu.", etc. from model ID
            # Format might be: us.meta.llama3-1-8b-instruct-v1:0
            # Should be: meta.llama3-1-8b-instruct-v1:0
            if "." in actual_model_id and ":" in actual_model_id:
                first_part = actual_model_id.split(".")[0]
                if first_part in ["us", "eu", "ap", "cn"] and len(first_part) == 2:
                    actual_model_id = ".".join(actual_model_id.split(".")[1:])
            
            # Check if model requires LLM interface (doesn't support chat)
            # Some models only support LLM, not ChatBedrock
            # Note: DeepSeek actually supports chat format (messages), so we use ChatBedrock
            models_requiring_llm = []  # Currently no models require LLM - all support chat
            requires_llm = any(model_type in actual_model_id.lower() for model_type in models_requiring_llm)
            
            # Validate model_id is not empty
            if not actual_model_id or not actual_model_id.strip():
                raise ValueError(f"Invalid Bedrock model identifier: {model_identifier}")
            
            try:
                import logging
                logger = logging.getLogger(__name__)
                
                # Create bedrock client with correct region if needed
                if use_region != settings.AWS_REGION:
                    bedrock_client = boto3.client(
                        'bedrock-runtime',
                        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                        region_name=use_region
                    )
                else:
                    bedrock_client = self.bedrock_client
                
                # Use LLM interface for models that don't support chat
                if requires_llm:
                    logger.info(f"Creating BedrockLLM with model_id: {actual_model_id}, region: {use_region}")
                    bedrock_model = BedrockLLM(
                        model_id=actual_model_id,
                        client=bedrock_client,
                        region_name=use_region,
                        model_kwargs={"temperature": temperature}
                    )
                    logger.info(f"Successfully created BedrockLLM instance for {actual_model_id}")
                else:
                    logger.info(f"Creating ChatBedrock with model_id: {actual_model_id}, region: {use_region}")
                    bedrock_model = ChatBedrock(
                        model_id=actual_model_id,
                        client=bedrock_client,
                        region_name=use_region,
                        model_kwargs={"temperature": temperature}
                    )
                    logger.info(f"Successfully created ChatBedrock instance for {actual_model_id}")
                
                return bedrock_model
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error creating Bedrock model instance: {e}, model_id: {actual_model_id}, region: {use_region}", exc_info=True)
                raise ValueError(f"Failed to initialize Bedrock model {actual_model_id}: {str(e)}")
        else:
            return self._get_default_model(temperature)
    
    def get_embedding_model(self, model_id: Optional[str] = None):
        """Get an embedding model instance - Only OpenAI embeddings"""
        # Only use OpenAI embeddings (no Bedrock, no HuggingFace)
        if settings.OPENAI_API_KEY:
            return OpenAIEmbeddings(openai_api_key=settings.OPENAI_API_KEY)
        else:
            raise ValueError("OpenAI API key not configured. Please set OPENAI_API_KEY for embeddings.")
    
    def _select_best_model(self) -> str:
        """Select the best available model - Only Cisco GPT-4.1"""
        # Only Cisco GPT-4.1 is available
        return "cisco-gpt-4.1"
    
    def _get_default_model(self, temperature: float = 0):
        """Get default model as fallback - Only Cisco GPT-4.1"""
        # Only Cisco GPT-4.1 for RAG/chat
        if settings.CISCO_CLIENT_ID and settings.CISCO_CLIENT_SECRET:
            token = self._get_cisco_token()
            if token:
                base_url = settings.CISCO_ENDPOINT.rsplit("/chat/completions", 1)[0]
                if not base_url.endswith("/v1"):
                    base_url = base_url.rstrip("/") + "/v1"
                return ChatOpenAI(
                    model_name="gpt-4.1",
                    openai_api_key=token,
                    base_url=base_url,
                    temperature=temperature
                )
        
        raise ValueError("Cisco GPT-4.1 model not configured. Please set CISCO_CLIENT_ID and CISCO_CLIENT_SECRET.")
    
    def list_models(self) -> List[Dict]:
        """List all available models (reloads to ensure current config)"""
        # Reload models to ensure we have the latest configuration
        # This is important in case env vars were updated after initialization
        models = self._load_available_models()
        return models

# Global instance
model_manager = ModelManager()

