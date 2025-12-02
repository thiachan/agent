from fastapi import APIRouter, Depends
from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.model_manager import model_manager

router = APIRouter()

@router.get("/")
async def list_models(current_user: User = Depends(get_current_user)):
    """List all available AI models"""
    import logging
    logger = logging.getLogger(__name__)
    try:
        models = model_manager.list_models()
        logger.info(f"Listing {len(models)} models: {[m.get('id') for m in models]}")
        
        # Filter out "auto" - only return actual models
        actual_models = [m for m in models if m.get("id") != "auto"]
        if len(actual_models) == 0:
            return {
                "models": [{
                    "id": "cisco-gpt-4.1",
                    "name": "No models configured",
                    "provider": "none",
                    "model_id": "none",
                    "type": "chat"
                }],
                "default": "cisco-gpt-4.1",
                "warning": "Please configure CISCO_CLIENT_ID/SECRET to use AI features"
            }
        return {
            "models": actual_models,
            "default": actual_models[0]["id"] if actual_models else "cisco-gpt-4.1"
        }
    except Exception as e:
        logger.error(f"Error listing models: {e}", exc_info=True)
        return {
            "models": [{
                "id": "cisco-gpt-4.1",
                "name": "No models configured",
                "provider": "none",
                "model_id": "none",
                "type": "chat"
            }],
            "default": "cisco-gpt-4.1",
            "error": str(e)
        }

