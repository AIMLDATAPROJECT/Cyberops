"""
AI Platform Orchestrator
Central service that manages and coordinates all AI agents.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

import httpx
import redis.asyncio as redis
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, String, DateTime, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database setup
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:postgres@postgres:5432/aipm"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Prometheus metrics
REQUEST_COUNT = Counter('orchestrator_requests_total', 'Total requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('orchestrator_request_duration_seconds', 'Request duration')
AGENT_TASKS = Counter('orchestrator_agent_tasks_total', 'Tasks sent to agents', ['agent_type'])

# Agent URLs
AGENTS = {
    "ai": "http://ai-agent:8001",
    "data": "http://data-agent:8002",
    "devops": "http://devops-agent:8003",
    "netmon": "http://netmon-agent:8004",
    "security": "http://security-agent:8005",
}

# Database Models
class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(String, primary_key=True)
    agent_type = Column(String, nullable=False)
    status = Column(String, default="pending")  # pending, running, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    input_data = Column(JSON)
    output_data = Column(JSON)
    error_message = Column(Text)

# Create tables
Base.metadata.create_all(bind=engine)

# Pydantic Models
class TaskCreate(BaseModel):
    agent_type: str = Field(..., description="Type of agent: ai, data, devops, netmon, security")
    input_data: Dict[str, Any] = Field(..., description="Input data for the task")
    priority: int = Field(default=5, ge=1, le=10, description="Priority 1-10")

class TaskResponse(BaseModel):
    id: str
    agent_type: str
    status: str
    created_at: datetime
    updated_at: datetime
    input_data: Optional[Dict]
    output_data: Optional[Dict]
    error_message: Optional[str]

class AgentStatus(BaseModel):
    agent_type: str
    status: str
    healthy: bool
    last_check: datetime

# Redis client
redis_client: Optional[redis.Redis] = None

async def get_redis() -> redis.Redis:
    global redis_client
    if redis_client is None:
        redis_client = redis.from_url("redis://redis:6379", decode_responses=True)
    return redis_client

def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    global redis_client
    redis_client = redis.from_url("redis://redis:6379", decode_responses=True)
    logger.info("Orchestrator starting up...")
    
    yield
    
    # Shutdown
    if redis_client:
        await redis_client.close()
    logger.info("Orchestrator shutting down...")

app = FastAPI(
    title="AI Platform Orchestrator",
    description="Central service for managing AI agents",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connections manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "orchestrator", "timestamp": datetime.utcnow().isoformat()}

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/agents", response_model=List[AgentStatus])
async def list_agents():
    """List all registered agents and their status"""
    agents_status = []
    
    async with httpx.AsyncClient() as client:
        for agent_type, agent_url in AGENTS.items():
            try:
                response = await client.get(f"{agent_url}/health", timeout=5.0)
                healthy = response.status_code == 200
                status = "online" if healthy else "unhealthy"
            except Exception as e:
                healthy = False
                status = "offline"
                logger.warning(f"Agent {agent_type} health check failed: {e}")
            
            agents_status.append(AgentStatus(
                agent_type=agent_type,
                status=status,
                healthy=healthy,
                last_check=datetime.utcnow()
            ))
    
    return agents_status

@app.post("/tasks", response_model=TaskResponse)
async def create_task(task: TaskCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Create a new task for an agent"""
    import uuid
    
    if task.agent_type not in AGENTS:
        raise HTTPException(status_code=400, detail=f"Unknown agent type: {task.agent_type}")
    
    task_id = str(uuid.uuid4())
    
    # Store in database
    db_task = Task(
        id=task_id,
        agent_type=task.agent_type,
        status="pending",
        input_data=task.input_data
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    
    # Queue for processing
    background_tasks.add_task(process_task, task_id, task.agent_type, task.input_data)
    
    AGENT_TASKS.labels(agent_type=task.agent_type).inc()
    
    logger.info(f"Created task {task_id} for agent {task.agent_type}")
    
    return TaskResponse(
        id=db_task.id,
        agent_type=db_task.agent_type,
        status=db_task.status,
        created_at=db_task.created_at,
        updated_at=db_task.updated_at,
        input_data=db_task.input_data,
        output_data=db_task.output_data,
        error_message=db_task.error_message
    )

@app.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, db: Session = Depends(get_db)):
    """Get task status and results"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return TaskResponse(
        id=task.id,
        agent_type=task.agent_type,
        status=task.status,
        created_at=task.created_at,
        updated_at=task.updated_at,
        input_data=task.input_data,
        output_data=task.output_data,
        error_message=task.error_message
    )

@app.get("/tasks", response_model=List[TaskResponse])
async def list_tasks(agent_type: Optional[str] = None, status: Optional[str] = None, db: Session = Depends(get_db)):
    """List all tasks with optional filtering"""
    query = db.query(Task)
    
    if agent_type:
        query = query.filter(Task.agent_type == agent_type)
    if status:
        query = query.filter(Task.status == status)
    
    tasks = query.order_by(Task.created_at.desc()).limit(100).all()
    
    return [
        TaskResponse(
            id=task.id,
            agent_type=task.agent_type,
            status=task.status,
            created_at=task.created_at,
            updated_at=task.updated_at,
            input_data=task.input_data,
            output_data=task.output_data,
            error_message=task.error_message
        )
        for task in tasks
    ]

@app.post("/execute/{agent_type}")
async def execute_direct(agent_type: str, data: Dict[str, Any]):
    """Execute a task directly on an agent (synchronous)"""
    if agent_type not in AGENTS:
        raise HTTPException(status_code=400, detail=f"Unknown agent type: {agent_type}")
    
    agent_url = AGENTS[agent_type]
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{agent_url}/execute",
                json=data,
                timeout=60.0
            )
            return response.json()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Agent execution timeout")
    except Exception as e:
        logger.error(f"Error executing task on {agent_type}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates"""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo back for now - can be extended for commands
            await websocket.send_json({"type": "echo", "data": data})
    except WebSocketDisconnect:
        manager.disconnect(websocket)

async def process_task(task_id: str, agent_type: str, input_data: Dict):
    """Process a task on the appropriate agent"""
    db = SessionLocal()
    
    try:
        # Update status to running
        task = db.query(Task).filter(Task.id == task_id).first()
        task.status = "running"
        task.updated_at = datetime.utcnow()
        db.commit()
        
        # Notify via WebSocket
        await manager.broadcast({
            "type": "task_started",
            "task_id": task_id,
            "agent_type": agent_type
        })
        
        # Execute on agent
        agent_url = AGENTS[agent_type]
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{agent_url}/execute",
                json=input_data,
                timeout=300.0
            )
            result = response.json()
        
        # Update task with result
        task.status = "completed"
        task.output_data = result
        task.updated_at = datetime.utcnow()
        db.commit()
        
        # Notify completion
        await manager.broadcast({
            "type": "task_completed",
            "task_id": task_id,
            "agent_type": agent_type,
            "result": result
        })
        
        logger.info(f"Task {task_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}")
        task.status = "failed"
        task.error_message = str(e)
        task.updated_at = datetime.utcnow()
        db.commit()
        
        await manager.broadcast({
            "type": "task_failed",
            "task_id": task_id,
            "error": str(e)
        })
    finally:
        db.close()

# ============ INTER-AGENT COMMUNICATION ============

from pydantic import BaseModel
from typing import Dict, Any, Optional
import uuid

class AgentMessageRequest(BaseModel):
    sender: str
    recipient: str
    message_type: str = "request"
    content: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None

class AgentResponse(BaseModel):
    status: str
    message_id: str
    data: Optional[Dict[str, Any]] = None

class CreateSessionRequest(BaseModel):
    participants: list[str]  # list of agent types
    initial_context: Optional[Dict[str, Any]] = None

class SessionInfo(BaseModel):
    session_id: str
    participants: list[str]
    created_at: str
    status: str

@app.post("/communicate/message")
async def send_agent_message(request: AgentMessageRequest):
    """Send a message from one agent to another"""
    try:
        redis_client = await get_redis()
        
        message_id = str(uuid.uuid4())
        message = {
            "message_id": message_id,
            "sender": request.sender,
            "recipient": request.recipient,
            "message_type": request.message_type,
            "content": request.content,
            "context": request.context,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "pending"
        }
        
        # Store in Redis
        await redis_client.setex(
            f"message:{message_id}",
            300,  # 5 min TTL
            json.dumps(message)
        )
        
        # Publish to recipient's channel
        channel = f"agent:{request.recipient}"
        await redis_client.publish(channel, json.dumps(message))
        
        # Also publish to orchestrator channel for monitoring
        await redis_client.publish("orchestrator:messages", json.dumps(message))
        
        logger.info(f"Message {message_id} from {request.sender} to {request.recipient}")
        
        return {
            "status": "sent",
            "message_id": message_id,
            "timestamp": message["timestamp"]
        }
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/communicate/session/create")
async def create_session(request: CreateSessionRequest):
    """Create a multi-agent conversation session"""
    try:
        redis_client = await get_redis()
        session_id = str(uuid.uuid4())
        
        session_data = {
            "session_id": session_id,
            "participants": request.participants,
            "created_at": datetime.utcnow().isoformat(),
            "status": "active",
            "context": request.initial_context or {}
        }
        
        # Store session
        await redis_client.setex(
            f"session:{session_id}",
            3600,  # 1 hour TTL
            json.dumps(session_data)
        )
        
        # Add participants to session set
        for agent in request.participants:
            await redis_client.sadd(f"session:{session_id}:agents", agent)
        
        logger.info(f"Created session {session_id} with {request.participants}")
        
        return {
            "status": "created",
            "session": session_data
        }
    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/communicate/session/{session_id}")
async def get_session(session_id: str):
    """Get session details"""
    try:
        redis_client = await get_redis()
        
        session_data = await redis_client.get(f"session:{session_id}")
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return json.loads(session_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/communicate/session/{session_id}/message")
async def send_session_message(session_id: str, message: Dict[str, Any]):
    """Send message to all participants in a session"""
    try:
        redis_client = await get_redis()
        
        # Get session
        session_data = await redis_client.get(f"session:{session_id}")
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = json.loads(session_data)
        
        # Broadcast to all participants
        message_id = str(uuid.uuid4())
        full_message = {
            "message_id": message_id,
            "session_id": session_id,
            "sender": message.get("sender"),
            "content": message.get("content"),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Store in session history
        await redis_client.lpush(
            f"session:{session_id}:history",
            json.dumps(full_message)
        )
        
        # Publish to all participants
        for agent in session["participants"]:
            if agent != message.get("sender"):
                await redis_client.publish(
                    f"agent:{agent}",
                    json.dumps({**full_message, "type": "session_message"})
                )
        
        return {
            "status": "broadcasted",
            "message_id": message_id,
            "participants_notified": len(session["participants"]) - 1
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send session message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/communicate/session/{session_id}/history")
async def get_session_history(session_id: str, limit: int = 50):
    """Get conversation history for a session"""
    try:
        redis_client = await get_redis()
        
        history = await redis_client.lrange(
            f"session:{session_id}:history",
            0,
            limit - 1
        )
        
        return {
            "session_id": session_id,
            "messages": [json.loads(m) for m in history]
        }
    except Exception as e:
        logger.error(f"Failed to get history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/communicate/delegate")
async def delegate_task(data: Dict[str, Any]):
    """Delegate a task from one agent to another and wait for response"""
    source_agent = data.get("from")
    target_agent = data.get("to")
    task_data = data.get("task", {})
    
    if target_agent not in AGENTS:
        raise HTTPException(status_code=400, detail=f"Unknown agent: {target_agent}")
    
    try:
        agent_url = AGENTS[target_agent]
        
        # Execute on target agent
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{agent_url}/execute",
                json=task_data,
                timeout=120.0
            )
            result = response.json()
        
        # Log the delegation
        logger.info(f"Task delegated from {source_agent} to {target_agent}")
        
        return {
            "status": "completed",
            "delegated_by": source_agent,
            "executed_by": target_agent,
            "result": result
        }
    except Exception as e:
        logger.error(f"Delegation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/communicate/shared-context/{key}")
async def get_shared_context(key: str):
    """Get shared context data"""
    try:
        redis_client = await get_redis()
        data = await redis_client.get(f"shared_context:{key}")
        if data:
            return json.loads(data)
        return None
    except Exception as e:
        logger.error(f"Failed to get context: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/communicate/shared-context/{key}")
async def set_shared_context(key: str, data: Dict[str, Any]):
    """Set shared context data"""
    try:
        redis_client = await get_redis()
        ttl = data.get("ttl", 600)  # default 10 min
        
        await redis_client.setex(
            f"shared_context:{key}",
            ttl,
            json.dumps({
                "data": data.get("value"),
                "timestamp": datetime.utcnow().isoformat(),
                "ttl": ttl
            })
        )
        
        # Notify agents
        await redis_client.publish(
            "agent:broadcast",
            json.dumps({
                "type": "context_updated",
                "key": key,
                "timestamp": datetime.utcnow().isoformat()
            })
        )
        
        return {"status": "stored", "key": key, "ttl": ttl}
    except Exception as e:
        logger.error(f"Failed to set context: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
