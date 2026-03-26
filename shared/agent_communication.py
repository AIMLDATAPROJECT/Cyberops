"""
Inter-Agent Communication Module
Enables agents to send messages and share context with each other.
"""

import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable
import asyncio
import redis.asyncio as redis
from pydantic import BaseModel
from enum import Enum

class MessageType(str, Enum):
    REQUEST = "request"
    RESPONSE = "response"
    BROADCAST = "broadcast"
    CONTEXT_SHARE = "context_share"
    TASK_DELEGATE = "task_delegate"

class AgentMessage(BaseModel):
    message_id: str
    sender: str
    recipient: str  # "broadcast" for all agents
    message_type: MessageType
    content: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None
    timestamp: str
    reply_to: Optional[str] = None
    ttl: int = 300  # seconds

class AgentCommunicator:
    """Handles inter-agent messaging via Redis Pub/Sub"""
    
    def __init__(self, redis_url: str = "redis://redis:6379"):
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None
        self.message_handlers: Dict[str, Callable] = {}
        self.agent_id: Optional[str] = None
        
    async def connect(self, agent_id: str):
        """Connect to Redis and subscribe to agent's channel"""
        self.agent_id = agent_id
        self.redis_client = await redis.from_url(self.redis_url)
        self.pubsub = self.redis_client.pubsub()
        
        # Subscribe to personal channel and broadcast
        await self.pubsub.subscribe(f"agent:{agent_id}", "agent:broadcast")
        
        # Start listening for messages
        asyncio.create_task(self._listen_messages())
        
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.pubsub:
            await self.pubsub.unsubscribe()
        if self.redis_client:
            await self.redis_client.close()
            
    def register_handler(self, message_type: MessageType, handler: Callable):
        """Register a handler for specific message type"""
        self.message_handlers[message_type] = handler
        
    async def send_message(
        self,
        recipient: str,
        message_type: MessageType,
        content: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        reply_to: Optional[str] = None
    ) -> AgentMessage:
        """Send message to another agent"""
        message = AgentMessage(
            message_id=str(uuid.uuid4()),
            sender=self.agent_id,
            recipient=recipient,
            message_type=message_type,
            content=content,
            context=context,
            timestamp=datetime.utcnow().isoformat(),
            reply_to=reply_to
        )
        
        # Store in Redis for persistence
        await self.redis_client.setex(
            f"message:{message.message_id}",
            message.ttl,
            message.json()
        )
        
        # Publish to channel
        channel = f"agent:{recipient}" if recipient != "broadcast" else "agent:broadcast"
        await self.redis_client.publish(channel, message.json())
        
        return message
    
    async def broadcast(self, message_type: MessageType, content: Dict[str, Any], context: Optional[Dict[str, Any]] = None):
        """Broadcast message to all agents"""
        return await self.send_message("broadcast", message_type, content, context)
    
    async def request_agent(
        self,
        target_agent: str,
        action: str,
        params: Dict[str, Any],
        timeout: int = 30
    ) -> Optional[AgentMessage]:
        """Send request to agent and wait for response"""
        # Send request
        request = await self.send_message(
            recipient=target_agent,
            message_type=MessageType.REQUEST,
            content={"action": action, "params": params}
        )
        
        # Wait for response
        response_key = f"response:{request.message_id}"
        
        for _ in range(timeout):
            response_data = await self.redis_client.get(response_key)
            if response_data:
                await self.redis_client.delete(response_key)
                return AgentMessage.parse_raw(response_data)
            await asyncio.sleep(1)
            
        return None  # Timeout
    
    async def respond_to(self, original_message: AgentMessage, content: Dict[str, Any], context: Optional[Dict[str, Any]] = None):
        """Send response to a request"""
        response = await self.send_message(
            recipient=original_message.sender,
            message_type=MessageType.RESPONSE,
            content=content,
            context=context,
            reply_to=original_message.message_id
        )
        
        # Store response for the requester to pick up
        await self.redis_client.setex(
            f"response:{original_message.message_id}",
            300,
            response.json()
        )
        
        return response
    
    async def share_context(self, key: str, data: Any, ttl: int = 600):
        """Share context/data with all agents"""
        await self.redis_client.setex(
            f"shared_context:{key}",
            ttl,
            json.dumps({"data": data, "agent": self.agent_id, "timestamp": datetime.utcnow().isoformat()})
        )
        
        # Notify agents
        await self.broadcast(
            MessageType.CONTEXT_SHARE,
            {"key": key, "shared_by": self.agent_id}
        )
    
    async def get_shared_context(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve shared context"""
        data = await self.redis_client.get(f"shared_context:{key}")
        if data:
            return json.loads(data)
        return None
    
    async def _listen_messages(self):
        """Background task to listen for messages"""
        async for message in self.pubsub.listen():
            if message["type"] == "message":
                try:
                    agent_message = AgentMessage.parse_raw(message["data"])
                    await self._process_message(agent_message)
                except Exception as e:
                    print(f"Error processing message: {e}")
                    
    async def _process_message(self, message: AgentMessage):
        """Process received message"""
        handler = self.message_handlers.get(message.message_type)
        if handler:
            await handler(message)

class ConversationSession:
    """Manages multi-agent conversation sessions"""
    
    def __init__(self, session_id: str, redis_client: redis.Redis):
        self.session_id = session_id
        self.redis = redis_client
        self.participants: List[str] = []
        
    async def add_participant(self, agent_id: str):
        """Add agent to conversation"""
        await self.redis.sadd(f"session:{self.session_id}:agents", agent_id)
        
    async def get_participants(self) -> List[str]:
        """Get all participants"""
        agents = await self.redis.smembers(f"session:{self.session_id}:agents")
        return [a.decode() if isinstance(a, bytes) else a for a in agents]
    
    async def add_message(self, agent_id: str, message: str):
        """Add message to conversation history"""
        entry = {
            "agent": agent_id,
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.redis.lpush(f"session:{self.session_id}:history", json.dumps(entry))
        
    async def get_history(self, limit: int = 50) -> List[Dict]:
        """Get conversation history"""
        messages = await self.redis.lrange(f"session:{self.session_id}:history", 0, limit - 1)
        return [json.loads(m.decode() if isinstance(m, bytes) else m) for m in messages]
    
    async def broadcast_to_session(self, sender: str, message: str):
        """Broadcast to all session participants"""
        participants = await self.get_participants()
        for agent in participants:
            if agent != sender:
                # This would be implemented with the communicator
                pass
