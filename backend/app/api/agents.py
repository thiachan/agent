from fastapi import APIRouter, Depends
from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.mcp_service import mcp_service
from pydantic import BaseModel
from typing import Dict, Any

router = APIRouter()

class AgentCallRequest(BaseModel):
    agent_id: str
    params: Dict[str, Any]

@router.get("/")
async def list_agents(current_user: User = Depends(get_current_user)):
    """List all available MCP agents"""
    agents = mcp_service.list_agents()
    return {"agents": agents}

@router.post("/call")
async def call_agent(
    request: AgentCallRequest,
    current_user: User = Depends(get_current_user)
):
    """Call an MCP agent"""
    try:
        result = await mcp_service.call_agent(
            request.agent_id,
            request.params,
            {
                "user_id": current_user.id,
                "email": current_user.email,
                "role": current_user.role.value,
                "full_name": current_user.full_name
            }
        )
        return {
            "status": "success",
            "result": result
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

