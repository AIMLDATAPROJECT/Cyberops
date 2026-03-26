"""
Plain Text API - Natural Language Interface for AI Platform
Converts simple text commands to agent actions without JSON.
"""

import re
import json
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import httpx

app = FastAPI(title="Plain Text AI Interface")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Agent capability patterns
AGENT_PATTERNS = {
    "netmon": {
        "keywords": ["ping", "network", "scan", "discover", "bandwidth", "connectivity", "port", "ip", "host", "internet", "reachable"],
        "actions": {
            "ping": ["ping", "check connectivity", "is up", "reachable", "can you ping", "test connection", "check if", "is online"],
            "discover": ["discover", "find devices", "scan network", "network devices", "find all", "what devices", "list devices", "show me"],
            "scan": ["port scan", "vulnerability scan", "security scan", "open ports", "scan ports", "check ports"],
            "bandwidth": ["bandwidth", "speed test", "network speed", "throughput", "internet speed", "how fast"],
            "monitor": ["monitor", "watch", "track network", "keep an eye"]
        }
    },
    "data": {
        "keywords": ["data", "query", "database", "validate", "backup", "clean", "transform", "sql", "store", "save"],
        "actions": {
            "validate": ["validate", "check data", "verify data", "data quality", "is the data", "check if data"],
            "query": ["query", "select", "get data", "fetch", "search database", "find data", "show me", "get me", "tell me"],
            "backup": ["backup", "save data", "export", "snapshot", "create backup", "save a copy"],
            "cleanup": ["clean", "cleanup", "deduplicate", "remove duplicates", "delete old", "clear"],
            "transform": ["transform", "convert", "format", "process data", "change format"],
            "ingest": ["ingest", "import", "load", "add data", "put data"]
        }
    },
    "devops": {
        "keywords": ["deploy", "build", "docker", "restart", "scale", "service", "container", "health", "stop", "start"],
        "actions": {
            "deploy": ["deploy", "release", "push to production", "go live", "put in production", "make live"],
            "build": ["build", "compile", "create image", "docker build", "make image"],
            "restart": ["restart", "reboot", "reload", "refresh", "start again", "turn off and on"],
            "scale": ["scale", "replicas", "instances", "horizontal", "more copies", "increase replicas"],
            "health_check": ["health", "status", "check service", "is running", "is working", "check if running", "how is"],
            "logs": ["logs", "get logs", "view logs", "tail", "show logs", "what happened", "error logs"],
            "stop": ["stop", "shutdown", "turn off", "kill", "terminate"],
            "start": ["start", "turn on", "boot up", "launch"]
        }
    },
    "security": {
        "keywords": ["security", "scan", "vulnerability", "encrypt", "secret", "policy", "compliance", "audit", "protect"],
        "actions": {
            "vuln_scan": ["vulnerability", "vuln scan", "security scan", "cve", "check for vulnerabilities", "find weaknesses"],
            "config_scan": ["config scan", "configuration", "security check", "check config", "verify settings"],
            "encrypt": ["encrypt", "secure", "protect", "cipher", "hide", "encode", "lock"],
            "decrypt": ["decrypt", "decode", "unlock", "reveal", "show"],
            "rotate_secret": ["rotate", "change password", "new secret", "refresh credentials", "update password", "change key"],
            "policy_check": ["policy", "compliance", "check policy", "rules", "verify compliance"],
            "audit": ["audit", "security audit", "review", "assessment", "examine"]
        }
    },
    "ai": {
        "keywords": ["analyze", "summarize", "generate", "chat", "text", "language", "understand", "explain", "help", "what", "how", "why", "when", "who"],
        "actions": {
            "generate": ["generate", "create", "write", "compose", "make", "produce"],
            "analyze": ["analyze", "examine", "study", "review", "assess", "look at", "check", "investigate"],
            "summarize": ["summarize", "summary", "brief", "overview", "tl;dr", "condense", "short version"],
            "chat": ["chat", "talk", "conversation", "discuss", "ask", "tell me", "explain", "help me", "what is", "how to", "why is"],
            "embed": ["embed", "vector", "embedding", "semantic", "similarity"],
            "translate": ["translate", "convert language", "change language", "in english", "to hindi"]
        }
    }
}

class TextCommand(BaseModel):
    command: str
    context: Optional[str] = None

class TextResponse(BaseModel):
    agent: str
    action: str
    result: str
    raw_data: Optional[Dict] = None

def parse_command(text: str) -> Dict[str, Any]:
    """Parse plain text command into structured action"""
    text_lower = text.lower()
    
    # Extract IP addresses
    ips = re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}(?:/\d{1,2})?\b', text)
    
    # Extract service names
    services = re.findall(r'(?:service|app|application|container)\s+(\w+)', text_lower)
    
    # Extract numbers
    numbers = re.findall(r'\b(\d+)\b', text)
    
    # Determine target agent and action
    best_agent = None
    best_action = None
    best_score = 0
    
    for agent, config in AGENT_PATTERNS.items():
        score = 0
        detected_action = None
        
        # Check keywords
        for keyword in config["keywords"]:
            if keyword in text_lower:
                score += 1
        
        # Check specific actions
        for action, patterns in config["actions"].items():
            for pattern in patterns:
                if pattern in text_lower:
                    score += 3  # Higher weight for action match
                    detected_action = action
                    break
        
        if score > best_score:
            best_score = score
            best_agent = agent
            best_action = detected_action
    
    # Default to AI agent for general queries
    if not best_agent:
        best_agent = "ai"
        best_action = "analyze"
    
    # Build params based on extracted data
    params = {}
    if ips:
        params["target"] = ips[0]
        params["targets"] = ips
    if services:
        params["service"] = services[0]
    if numbers:
        params["count"] = int(numbers[0])
        params["replicas"] = int(numbers[0])
    
    return {
        "agent": best_agent,
        "action": best_action or "execute",
        "params": params,
        "original_text": text
    }

def format_response(agent: str, action: str, raw_result: Dict) -> str:
    """Convert raw JSON result to human-friendly text"""
    
    # Extract key info
    result_data = raw_result.get("result", raw_result)
    
    if agent == "netmon":
        if action == "ping":
            if isinstance(result_data, dict):
                success = result_data.get("success_rate", 0)
                return f"✅ Ping test complete. Success rate: {success}%. Network connectivity is {'good' if success > 80 else 'having issues'}."
            return f"✅ Ping completed: {json.dumps(result_data, indent=2)}"
        
        elif action == "discover":
            devices = result_data.get("devices", []) if isinstance(result_data, dict) else []
            return f"🔍 Network discovery complete. Found {len(devices)} devices on your network."
        
        elif action == "scan":
            ports = result_data.get("open_ports", []) if isinstance(result_data, dict) else []
            vulns = result_data.get("vulnerabilities", []) if isinstance(result_data, dict) else []
            return f"🔍 Scan complete. {len(ports)} open ports found. {len(vulns)} potential issues detected."
    
    elif agent == "data":
        if action == "validate":
            if isinstance(result_data, dict):
                valid = result_data.get("valid", False)
                errors = result_data.get("errors", [])
                return f"{'✅' if valid else '⚠️'} Data validation {'passed' if valid else 'failed'}. {len(errors)} issues found."
            return f"✅ Data validation: {json.dumps(result_data, indent=2)}"
        
        elif action == "query":
            count = result_data.get("count", 0) if isinstance(result_data, dict) else 0
            return f"📊 Query executed. Retrieved {count} records from the database."
        
        elif action == "backup":
            backup_id = result_data.get("backup_id", "N/A") if isinstance(result_data, dict) else "N/A"
            return f"💾 Backup created successfully. Backup ID: {backup_id}"
    
    elif agent == "devops":
        if action == "deploy":
            status = result_data.get("status", "unknown") if isinstance(result_data, dict) else "unknown"
            return f"🚀 Deployment {status}. Service is now running."
        
        elif action == "health_check":
            healthy = result_data.get("healthy", False) if isinstance(result_data, dict) else False
            return f"{'✅' if healthy else '❌'} Health check: Service is {'healthy' if healthy else 'unhealthy'}."
        
        elif action == "restart":
            success = result_data.get("success", False) if isinstance(result_data, dict) else False
            return f"{'✅' if success else '❌'} Service restart {'successful' if success else 'failed'}."
        
        elif action == "scale":
            current = result_data.get("current_replicas", 0) if isinstance(result_data, dict) else 0
            return f"⚖️ Service scaled. Now running {current} replicas."
    
    elif agent == "security":
        if action == "vuln_scan":
            vulns = result_data.get("vulnerabilities", []) if isinstance(result_data, dict) else []
            score = result_data.get("risk_score", 0) if isinstance(result_data, dict) else 0
            if score > 7:
                return f"🚨 HIGH RISK! Found {len(vulns)} vulnerabilities. Risk score: {score}/10. Immediate attention required!"
            return f"🔒 Scan complete. {len(vulns)} vulnerabilities found. Risk score: {score}/10."
        
        elif action == "config_scan":
            violations = result_data.get("violations", []) if isinstance(result_data, dict) else []
            return f"🔒 Configuration scan: {len(violations)} security violations found."
        
        elif action == "encrypt":
            return f"🔐 Data encrypted successfully and stored securely."
    
    elif agent == "ai":
        if isinstance(result_data, dict):
            content = result_data.get("content", result_data.get("response", result_data.get("result", "")))
            if content:
                return f"🤖 {content}"
        return f"🤖 {json.dumps(result_data, indent=2)}"
    
    # Fallback to formatted JSON
    return f"✅ {agent} agent completed {action}. Result:\n{json.dumps(result_data, indent=2)}"

@app.post("/text/command", response_model=TextResponse)
async def text_command(cmd: TextCommand):
    """Execute a plain text command"""
    
    # Parse the command
    parsed = parse_command(cmd.command)
    
    agent = parsed["agent"]
    action = parsed["action"]
    params = parsed["params"]
    
    try:
        # Execute via orchestrator
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://orchestrator:8000/execute/" + agent,
                json={
                    "action": action,
                    "params": params
                },
                timeout=120.0
            )
            
            raw_result = response.json()
            
            # Format as friendly text
            friendly_result = format_response(agent, action, raw_result)
            
            return TextResponse(
                agent=agent,
                action=action,
                result=friendly_result,
                raw_data=raw_result if cmd.context == "debug" else None
            )
            
    except Exception as e:
        return TextResponse(
            agent=agent,
            action=action,
            result=f"❌ Error executing command: {str(e)}",
            raw_data=None
        )

@app.post("/text/chat")
async def text_chat(message: Dict[str, str]):
    """Simple chat interface that understands context"""
    text = message.get("message", "")
    history = message.get("history", [])
    
    # Check if it's a command or chat
    parsed = parse_command(text)
    
    # If it's a clear command, execute it
    if parsed["action"] and parsed["agent"] != "ai":
        return await text_command(TextCommand(command=text))
    
    # Otherwise, treat as AI chat
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://orchestrator:8000/execute/ai",
                json={
                    "action": "chat",
                    "params": {
                        "messages": [
                            {"role": "system", "content": "You are an AI infrastructure assistant. Help manage systems, answer questions, and execute commands."},
                            *[{"role": "user" if i % 2 == 0 else "assistant", "content": msg} for i, msg in enumerate(history[-4:])],
                            {"role": "user", "content": text}
                        ],
                        "model": "llama2"
                    }
                },
                timeout=120.0
            )
            
            result = response.json()
            content = result.get("result", {}).get("content", "I'm not sure how to help with that.")
            
            return {
                "response": content,
                "type": "chat",
                "suggested_actions": []
            }
    except Exception as e:
        return {
            "response": f"Sorry, I encountered an error: {str(e)}",
            "type": "error"
        }

@app.get("/text/agents")
async def list_agents():
    """List all agents and their capabilities in plain text"""
    agents_info = []
    
    for agent, config in AGENT_PATTERNS.items():
        actions_list = ", ".join(config["actions"].keys())
        agents_info.append(f"• {agent.upper()}: Can perform {actions_list}")
    
    return {
        "description": "Available AI Agents:",
        "agents": agents_info,
        "example_commands": [
            "ping 192.168.1.1",
            "discover network devices",
            "validate customer data",
            "deploy auth-service",
            "scan for vulnerabilities",
            "restart nginx service",
            "backup database"
        ]
    }

@app.get("/text/help")
async def help_text():
    """Provide help text"""
    return {
        "help": """
🤖 AI PLATFORM - PLAIN TEXT COMMANDS

Simply type what you want to do in natural language!

EXAMPLES:
• "ping google.com" - Check network connectivity
• "discover devices on 192.168.1.0/24" - Find network devices
• "scan port 80 on 192.168.1.100" - Port scanning
• "validate user data" - Check data quality
• "backup customer database" - Create backup
• "deploy api-service version 2.0" - Deploy application
• "restart nginx" - Restart service
• "scale auth-service to 5 replicas" - Scale horizontally
• "check health of all services" - Health monitoring
• "scan for vulnerabilities" - Security scanning
• "encrypt this data: secret123" - Data encryption
• "summarize yesterday's logs" - AI analysis

The AI will automatically route your command to the right agent!
        """.strip()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8006)
