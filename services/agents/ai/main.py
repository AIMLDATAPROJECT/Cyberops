"""
AI Agent - Natural Language Processing & Generation Agent
Handles text generation, analysis, embeddings, and conversational AI.
"""

import logging
import os
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager
from datetime import datetime

import httpx
import redis.asyncio as redis
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter('ai_agent_requests_total', 'Total requests', ['endpoint'])
REQUEST_DURATION = Histogram('ai_agent_request_duration_seconds', 'Request duration')
LLM_CALLS = Counter('ai_agent_llm_calls_total', 'LLM API calls', ['provider'])

# Configuration
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Redis client
redis_client: Optional[redis.Redis] = None

# Pydantic Models
class GenerateRequest(BaseModel):
    prompt: str = Field(..., description="Input prompt for generation")
    model: str = Field(default="llama2", description="Model to use")
    max_tokens: int = Field(default=500, ge=1, le=4000)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    system_prompt: Optional[str] = Field(default=None, description="System context")

class AnalyzeRequest(BaseModel):
    text: str = Field(..., description="Text to analyze")
    analysis_type: str = Field(default="sentiment", description="Type of analysis: sentiment, entities, summary")

class EmbedRequest(BaseModel):
    texts: List[str] = Field(..., description="List of texts to embed")
    model: str = Field(default="all-MiniLM-L6-v2", description="Embedding model")

class ChatRequest(BaseModel):
    messages: List[Dict[str, str]] = Field(..., description="Conversation history")
    model: str = Field(default="llama2", description="Model to use")
    stream: bool = Field(default=False)

class AgentResponse(BaseModel):
    result: Any
    model_used: str
    tokens_used: Optional[int] = None
    processing_time_ms: float
    timestamp: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    global redis_client
    redis_client = redis.from_url("redis://redis:6379", decode_responses=True)
    logger.info("AI Agent starting up...")
    
    yield
    
    if redis_client:
        await redis_client.close()
    logger.info("AI Agent shutting down...")

app = FastAPI(
    title="AI Agent",
    description="Natural Language Processing & Generation Agent",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "ai-agent",
        "timestamp": datetime.utcnow().isoformat(),
        "capabilities": ["generation", "analysis", "embeddings", "chat"]
    }

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/execute")
async def execute(data: Dict[str, Any]):
    """Main execution endpoint for orchestrator"""
    action = data.get("action", "generate")
    
    if action == "generate":
        req = GenerateRequest(**data.get("params", {}))
        return await generate_text(req)
    elif action == "analyze":
        req = AnalyzeRequest(**data.get("params", {}))
        return await analyze_text(req)
    elif action == "embed":
        req = EmbedRequest(**data.get("params", {}))
        return await create_embeddings(req)
    elif action == "chat":
        req = ChatRequest(**data.get("params", {}))
        return await chat_completion(req)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {action}")

@app.post("/generate", response_model=AgentResponse)
async def generate_text(request: GenerateRequest):
    """Generate text using LLM"""
    import time
    start_time = time.time()
    
    REQUEST_COUNT.labels(endpoint="generate").inc()
    
    try:
        # Try Ollama first (local)
        async with httpx.AsyncClient() as client:
            payload = {
                "model": request.model,
                "prompt": request.prompt,
                "stream": False,
                "options": {
                    "temperature": request.temperature,
                    "num_predict": request.max_tokens
                }
            }
            
            if request.system_prompt:
                payload["system"] = request.system_prompt
            
            response = await client.post(
                f"{OLLAMA_HOST}/api/generate",
                json=payload,
                timeout=120.0
            )
            
            if response.status_code == 200:
                result = response.json()
                LLM_CALLS.labels(provider="ollama").inc()
                
                processing_time = (time.time() - start_time) * 1000
                
                return AgentResponse(
                    result=result.get("response", ""),
                    model_used=f"ollama:{request.model}",
                    tokens_used=result.get("eval_count"),
                    processing_time_ms=processing_time,
                    timestamp=datetime.utcnow().isoformat()
                )
    except Exception as e:
        logger.warning(f"Ollama failed: {e}, falling back to OpenAI")
    
    # Fallback to OpenAI if key available
    if OPENAI_API_KEY:
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=OPENAI_API_KEY)
            
            messages = []
            if request.system_prompt:
                messages.append({"role": "system", "content": request.system_prompt})
            messages.append({"role": "user", "content": request.prompt})
            
            response = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=request.max_tokens,
                temperature=request.temperature
            )
            
            LLM_CALLS.labels(provider="openai").inc()
            processing_time = (time.time() - start_time) * 1000
            
            return AgentResponse(
                result=response.choices[0].message.content,
                model_used="openai:gpt-3.5-turbo",
                tokens_used=response.usage.total_tokens,
                processing_time_ms=processing_time,
                timestamp=datetime.utcnow().isoformat()
            )
        except Exception as e:
            logger.error(f"OpenAI failed: {e}")
    
    raise HTTPException(status_code=503, detail="No LLM service available")

@app.post("/analyze", response_model=AgentResponse)
async def analyze_text(request: AnalyzeRequest):
    """Analyze text (sentiment, entities, summary)"""
    import time
    start_time = time.time()
    
    REQUEST_COUNT.labels(endpoint="analyze").inc()
    
    try:
        if request.analysis_type == "sentiment":
            # Simple rule-based sentiment (can be enhanced with transformers)
            text_lower = request.text.lower()
            positive_words = ["good", "great", "excellent", "amazing", "love", "best", "happy"]
            negative_words = ["bad", "terrible", "awful", "hate", "worst", "sad", "angry"]
            
            pos_score = sum(1 for w in positive_words if w in text_lower)
            neg_score = sum(1 for w in negative_words if w in text_lower)
            
            if pos_score > neg_score:
                sentiment = "positive"
                score = min(1.0, 0.5 + (pos_score - neg_score) * 0.1)
            elif neg_score > pos_score:
                sentiment = "negative"
                score = max(0.0, 0.5 - (neg_score - pos_score) * 0.1)
            else:
                sentiment = "neutral"
                score = 0.5
            
            result = {
                "sentiment": sentiment,
                "confidence": score,
                "positive_words": pos_score,
                "negative_words": neg_score
            }
            
        elif request.analysis_type == "summary":
            # Generate summary using LLM
            summary_req = GenerateRequest(
                prompt=f"Summarize the following text in 2-3 sentences:\n\n{request.text}",
                max_tokens=150,
                temperature=0.3
            )
            summary_response = await generate_text(summary_req)
            result = {"summary": summary_response.result}
            
        elif request.analysis_type == "entities":
            # Simple entity extraction
            import re
            emails = re.findall(r'\S+@\S+', request.text)
            urls = re.findall(r'http[s]?://\S+', request.text)
            numbers = re.findall(r'\b\d+\b', request.text)
            
            result = {
                "emails": emails,
                "urls": urls,
                "numbers": numbers,
                "word_count": len(request.text.split())
            }
        else:
            raise HTTPException(status_code=400, detail=f"Unknown analysis type: {request.analysis_type}")
        
        processing_time = (time.time() - start_time) * 1000
        
        return AgentResponse(
            result=result,
            model_used="rule-based",
            tokens_used=len(request.text.split()),
            processing_time_ms=processing_time,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/embed", response_model=AgentResponse)
async def create_embeddings(request: EmbedRequest):
    """Create text embeddings"""
    import time
    start_time = time.time()
    
    REQUEST_COUNT.labels(endpoint="embed").inc()
    
    try:
        # Use sentence-transformers or Ollama embeddings
        async with httpx.AsyncClient() as client:
            embeddings = []
            
            for text in request.texts:
                response = await client.post(
                    f"{OLLAMA_HOST}/api/embeddings",
                    json={"model": request.model, "prompt": text},
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    embeddings.append(result.get("embedding", []))
            
            processing_time = (time.time() - start_time) * 1000
            
            return AgentResponse(
                result=embeddings,
                model_used=f"ollama:{request.model}",
                tokens_used=sum(len(t.split()) for t in request.texts),
                processing_time_ms=processing_time,
                timestamp=datetime.utcnow().isoformat()
            )
            
    except Exception as e:
        logger.error(f"Embedding failed: {e}")
        raise HTTPException(status_code=503, detail="Embedding service unavailable")

@app.post("/chat", response_model=AgentResponse)
async def chat_completion(request: ChatRequest):
    """Chat completion with conversation history"""
    import time
    start_time = time.time()
    
    REQUEST_COUNT.labels(endpoint="chat").inc()
    
    try:
        # Convert messages to prompt for Ollama
        prompt = ""
        for msg in request.messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                prompt += f"System: {content}\n"
            elif role == "user":
                prompt += f"User: {content}\n"
            elif role == "assistant":
                prompt += f"Assistant: {content}\n"
        prompt += "Assistant:"
        
        # Use Ollama generate endpoint
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{OLLAMA_HOST}/api/generate",
                json={
                    "model": request.model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=120.0
            )
            
            if response.status_code == 200:
                result = response.json()
                LLM_CALLS.labels(provider="ollama").inc()
                
                processing_time = (time.time() - start_time) * 1000
                
                return AgentResponse(
                    result={"role": "assistant", "content": result.get("response", "")},
                    model_used=f"ollama:{request.model}",
                    processing_time_ms=processing_time,
                    timestamp=datetime.utcnow().isoformat()
                )
                
    except Exception as e:
        logger.error(f"Chat failed: {e}")
        
        # Fallback to OpenAI
        if OPENAI_API_KEY:
            try:
                from openai import AsyncOpenAI
                client = AsyncOpenAI(api_key=OPENAI_API_KEY)
                
                response = await client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=request.messages
                )
                
                LLM_CALLS.labels(provider="openai").inc()
                processing_time = (time.time() - start_time) * 1000
                
                return AgentResponse(
                    result={"role": "assistant", "content": response.choices[0].message.content},
                    model_used="openai:gpt-3.5-turbo",
                    tokens_used=response.usage.total_tokens,
                    processing_time_ms=processing_time,
                    timestamp=datetime.utcnow().isoformat()
                )
            except Exception as oe:
                logger.error(f"OpenAI chat failed: {oe}")
    
    raise HTTPException(status_code=503, detail="Chat service unavailable")

# ============ INTER-AGENT MESSAGING ============

import asyncio
import json
from typing import Dict, Any, Optional

# Message inbox for this agent
message_inbox: List[Dict[str, Any]] = []

@app.post("/message/receive")
async def receive_message(message: Dict[str, Any]):
    """Receive message from another agent via orchestrator"""
    try:
        message["received_at"] = datetime.utcnow().isoformat()
        message_inbox.append(message)
        
        logger.info(f"Received message from {message.get('sender')}: {message.get('message_id')}")
        
        # Auto-process if it's a request
        if message.get("message_type") == "request":
            # Process the request content
            content = message.get("content", {})
            action = content.get("action")
            
            if action == "generate":
                result = await generate_text(GenerateRequest(**content.get("params", {})))
            elif action == "analyze":
                result = await analyze_text(AnalyzeRequest(**content.get("params", {})))
            elif action == "chat":
                result = await chat_completion(ChatRequest(**content.get("params", {})))
            else:
                result = {"error": f"Unknown action: {action}"}
            
            # Send response back via orchestrator
            async with httpx.AsyncClient() as client:
                await client.post(
                    "http://orchestrator:8000/communicate/message",
                    json={
                        "sender": "ai",
                        "recipient": message.get("sender"),
                        "message_type": "response",
                        "content": {"result": result.dict() if hasattr(result, 'dict') else result},
                        "context": {"reply_to": message.get("message_id")}
                    }
                )
        
        return {"status": "received", "message_id": message.get("message_id")}
    except Exception as e:
        logger.error(f"Error receiving message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/message/inbox")
async def get_inbox(limit: int = 50):
    """Get received messages"""
    return {
        "agent": "ai",
        "messages": message_inbox[-limit:],
        "total": len(message_inbox)
    }

@app.post("/message/send")
async def send_message_to_agent(data: Dict[str, Any]):
    """Send message to another agent via orchestrator"""
    try:
        recipient = data.get("to")
        content = data.get("content", {})
        message_type = data.get("message_type", "request")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://orchestrator:8000/communicate/message",
                json={
                    "sender": "ai",
                    "recipient": recipient,
                    "message_type": message_type,
                    "content": content,
                    "context": data.get("context")
                }
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(status_code=response.status_code, detail="Failed to send message")
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/delegate")
async def delegate_to_agent(data: Dict[str, Any]):
    """Delegate task to another agent and wait for response"""
    try:
        target_agent = data.get("to")
        task = data.get("task", {})
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://orchestrator:8000/communicate/delegate",
                json={
                    "from": "ai",
                    "to": target_agent,
                    "task": task
                },
                timeout=120.0
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(status_code=response.status_code, detail="Delegation failed")
    except Exception as e:
        logger.error(f"Error delegating task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Subscribe to Redis messages on startup
async def subscribe_to_messages():
    """Subscribe to Redis Pub/Sub for real-time messages"""
    try:
        if redis_client:
            pubsub = redis_client.pubsub()
            await pubsub.subscribe("agent:ai", "agent:broadcast")
            
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        data["received_at"] = datetime.utcnow().isoformat()
                        message_inbox.append(data)
                        logger.info(f"Received via Pub/Sub: {data.get('message_id')}")
                    except Exception as e:
                        logger.error(f"Error processing pubsub message: {e}")
    except Exception as e:
        logger.error(f"Pub/Sub error: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
