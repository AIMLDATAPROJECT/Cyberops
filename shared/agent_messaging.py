"""
Shared Agent Messaging Module
Adds inter-agent communication capabilities to any agent.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import httpx
import redis.asyncio as redis

logger = logging.getLogger(__name__)

class AgentMessenger:
    """Helper class to add messaging capabilities to agents"""
    
    def __init__(self, agent_id: str, orchestrator_url: str = "http://orchestrator:8000"):
        self.agent_id = agent_id
        self.orchestrator_url = orchestrator_url
        self.message_inbox: List[Dict[str, Any]] = []
        self.redis_client: Optional[redis.Redis] = None
        
    async def init_redis(self, redis_url: str = "redis://redis:6379"):
        """Initialize Redis connection"""
        self.redis_client = await redis.from_url(redis_url, decode_responses=True)
        
    async def receive_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Receive and store a message"""
        message["received_at"] = datetime.utcnow().isoformat()
        self.message_inbox.append(message)
        logger.info(f"[{self.agent_id}] Received from {message.get('sender')}: {message.get('message_id')}")
        return {"status": "received", "message_id": message.get("message_id")}
        
    def get_inbox(self, limit: int = 50) -> Dict[str, Any]:
        """Get message inbox"""
        return {
            "agent": self.agent_id,
            "messages": self.message_inbox[-limit:],
            "total": len(self.message_inbox)
        }
        
    async def send_message(self, recipient: str, content: Dict[str, Any], 
                          message_type: str = "request", context: Optional[Dict] = None) -> Dict[str, Any]:
        """Send message to another agent via orchestrator"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.orchestrator_url}/communicate/message",
                    json={
                        "sender": self.agent_id,
                        "recipient": recipient,
                        "message_type": message_type,
                        "content": content,
                        "context": context
                    }
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"error": f"Failed to send: {response.status_code}"}
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return {"error": str(e)}
            
    async def delegate_task(self, target_agent: str, task: Dict[str, Any]) -> Dict[str, Any]:
        """Delegate task to another agent"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.orchestrator_url}/communicate/delegate",
                    json={
                        "from": self.agent_id,
                        "to": target_agent,
                        "task": task
                    },
                    timeout=120.0
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"error": f"Delegation failed: {response.status_code}"}
        except Exception as e:
            logger.error(f"Error delegating: {e}")
            return {"error": str(e)}
            
    async def share_context(self, key: str, data: Any, ttl: int = 600) -> Dict[str, Any]:
        """Share context with other agents"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.orchestrator_url}/communicate/shared-context/{key}",
                    json={"value": data, "ttl": ttl}
                )
                
                if response.status_code == 200:
                    return response.json()
                return {"error": "Failed to share context"}
        except Exception as e:
            logger.error(f"Error sharing context: {e}")
            return {"error": str(e)}
            
    async def get_shared_context(self, key: str) -> Optional[Dict[str, Any]]:
        """Get shared context"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.orchestrator_url}/communicate/shared-context/{key}"
                )
                
                if response.status_code == 200:
                    return response.json()
                return None
        except Exception as e:
            logger.error(f"Error getting context: {e}")
            return None
            
    def clear_inbox(self):
        """Clear message inbox"""
        self.message_inbox.clear()
        return {"status": "cleared"}

# FastAPI endpoint handlers that can be added to any agent

def create_message_routes(app, agent_id: str, handler_func=None):
    """Create messaging endpoints for an agent"""
    
    messenger = AgentMessenger(agent_id)
    
    @app.on_event("startup")
    async def startup():
        await messenger.init_redis()
    
    @app.post("/message/receive")
    async def receive_message(message: Dict[str, Any]):
        """Receive message from another agent"""
        result = await messenger.receive_message(message)
        
        # If custom handler provided, call it
        if handler_func and message.get("message_type") == "request":
            try:
                response_content = await handler_func(message.get("content", {}))
                # Send response back
                await messenger.send_message(
                    recipient=message.get("sender"),
                    content={"result": response_content},
                    message_type="response",
                    context={"reply_to": message.get("message_id")}
                )
            except Exception as e:
                logger.error(f"Handler error: {e}")
        
        return result
    
    @app.get("/message/inbox")
    async def get_inbox(limit: int = 50):
        """Get received messages"""
        return messenger.get_inbox(limit)
    
    @app.post("/message/send")
    async def send_message(data: Dict[str, Any]):
        """Send message to another agent"""
        return await messenger.send_message(
            recipient=data.get("to"),
            content=data.get("content", {}),
            message_type=data.get("message_type", "request"),
            context=data.get("context")
        )
    
    @app.post("/delegate")
    async def delegate_task(data: Dict[str, Any]):
        """Delegate task to another agent"""
        return await messenger.delegate_task(
            target_agent=data.get("to"),
            task=data.get("task", {})
        )
    
    @app.post("/context/share")
    async def share_context(data: Dict[str, Any]):
        """Share context with other agents"""
        return await messenger.share_context(
            key=data.get("key"),
            data=data.get("data"),
            ttl=data.get("ttl", 600)
        )
    
    @app.get("/context/get/{key}")
    async def get_context(key: str):
        """Get shared context"""
        result = await messenger.get_shared_context(key)
        return result or {"error": "Context not found"}
    
    @app.delete("/message/inbox")
    async def clear_inbox():
        """Clear message inbox"""
        return messenger.clear_inbox()
        
    return messenger
