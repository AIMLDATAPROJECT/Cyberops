"""
AI Platform - Agent Capability Registry
Defines what each agent can do for automated task routing.
"""

from typing import Dict, List, Any, Callable
from dataclasses import dataclass
from enum import Enum

class AgentType(str, Enum):
    AI = "ai"
    DATA = "data"
    DEVOPS = "devops"
    NETMON = "netmon"
    SECURITY = "security"

@dataclass
class AgentCapability:
    """Defines a capability that an agent possesses"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    priority: int = 5  # 1-10, lower = higher priority

class AgentRegistry:
    """Central registry of all agents and their capabilities"""
    
    AGENTS = {
        AgentType.AI: {
            "name": "AI Agent",
            "icon": "🤖",
            "description": "Natural language processing, text generation, analysis, and task coordination",
            "endpoint": "http://ai-agent:8001",
            "capabilities": [
                AgentCapability(
                    name="generate",
                    description="Generate text based on prompt",
                    input_schema={"prompt": "string", "model": "string"},
                    output_schema={"text": "string"},
                    priority=1
                ),
                AgentCapability(
                    name="analyze",
                    description="Analyze text for sentiment, entities, or summary",
                    input_schema={"text": "string", "analysis_type": "string"},
                    output_schema={"analysis": "object"},
                    priority=2
                ),
                AgentCapability(
                    name="chat",
                    description="Have a conversation with context",
                    input_schema={"messages": "array", "model": "string"},
                    output_schema={"response": "string"},
                    priority=1
                ),
                AgentCapability(
                    name="embed",
                    description="Generate embeddings for texts",
                    input_schema={"texts": "array", "model": "string"},
                    output_schema={"embeddings": "array"},
                    priority=3
                ),
                AgentCapability(
                    name="route_task",
                    description="Analyze and route tasks to appropriate agents",
                    input_schema={"task_description": "string", "context": "object"},
                    output_schema={"target_agent": "string", "action": "string", "params": "object"},
                    priority=1
                ),
                AgentCapability(
                    name="summarize",
                    description="Summarize data or conversations",
                    input_schema={"content": "any", "max_length": "number"},
                    output_schema={"summary": "string"},
                    priority=2
                ),
            ]
        },
        AgentType.DATA: {
            "name": "Data Agent",
            "icon": "📊",
            "description": "Data validation, transformation, querying, and storage management",
            "endpoint": "http://data-agent:8002",
            "capabilities": [
                AgentCapability(
                    name="validate",
                    description="Validate data against schema or rules",
                    input_schema={"data": "any", "schema": "object"},
                    output_schema={"valid": "boolean", "errors": "array"},
                    priority=1
                ),
                AgentCapability(
                    name="query",
                    description="Query datasets with SQL or filters",
                    input_schema={"dataset_id": "string", "query": "string", "query_type": "string"},
                    output_schema={"results": "array", "count": "number"},
                    priority=1
                ),
                AgentCapability(
                    name="transform",
                    description="Transform data format or structure",
                    input_schema={"data": "any", "transformation": "string", "options": "object"},
                    output_schema={"transformed_data": "any"},
                    priority=2
                ),
                AgentCapability(
                    name="ingest",
                    description="Ingest data from various sources",
                    input_schema={"source": "string", "format": "string", "config": "object"},
                    output_schema={"dataset_id": "string", "records_ingested": "number"},
                    priority=2
                ),
                AgentCapability(
                    name="backup",
                    description="Backup dataset to storage",
                    input_schema={"dataset_id": "string", "destination": "string"},
                    output_schema={"backup_id": "string", "size": "number"},
                    priority=3
                ),
                AgentCapability(
                    name="cleanup",
                    description="Clean and deduplicate data",
                    input_schema={"dataset_id": "string", "rules": "object"},
                    output_schema={"cleaned_records": "number", "removed_duplicates": "number"},
                    priority=3
                ),
            ]
        },
        AgentType.DEVOPS: {
            "name": "DevOps Agent",
            "icon": "⚙️",
            "description": "CI/CD pipelines, container management, deployments, infrastructure",
            "endpoint": "http://devops-agent:8003",
            "capabilities": [
                AgentCapability(
                    name="deploy",
                    description="Deploy application or service",
                    input_schema={"service": "string", "version": "string", "environment": "string"},
                    output_schema={"deployment_id": "string", "status": "string", "url": "string"},
                    priority=1
                ),
                AgentCapability(
                    name="build",
                    description="Build Docker image or artifact",
                    input_schema={"repository": "string", "branch": "string", "dockerfile": "string"},
                    output_schema={"image_tag": "string", "build_time": "number"},
                    priority=1
                ),
                AgentCapability(
                    name="scale",
                    description="Scale service instances",
                    input_schema={"service": "string", "replicas": "number"},
                    output_schema={"previous_replicas": "number", "current_replicas": "number"},
                    priority=2
                ),
                AgentCapability(
                    name="rollback",
                    description="Rollback to previous version",
                    input_schema={"service": "string", "version": "string"},
                    output_schema={"success": "boolean", "previous_version": "string"},
                    priority=1
                ),
                AgentCapability(
                    name="health_check",
                    description="Check service health status",
                    input_schema={"service": "string"},
                    output_schema={"healthy": "boolean", "checks": "array"},
                    priority=2
                ),
                AgentCapability(
                    name="logs",
                    description="Get service logs",
                    input_schema={"service": "string", "lines": "number", "since": "string"},
                    output_schema={"logs": "string"},
                    priority=3
                ),
                AgentCapability(
                    name="restart",
                    description="Restart service or container",
                    input_schema={"service": "string"},
                    output_schema={"success": "boolean", "restart_time": "number"},
                    priority=1
                ),
            ]
        },
        AgentType.NETMON: {
            "name": "NetMon Agent",
            "icon": "🌐",
            "description": "Network discovery, monitoring, scanning, and performance analysis",
            "endpoint": "http://netmon-agent:8004",
            "capabilities": [
                AgentCapability(
                    name="discover",
                    description="Auto-discover network devices and topology",
                    input_schema={"subnet": "string", "methods": "array"},
                    output_schema={"devices": "array", "topology": "object"},
                    priority=1
                ),
                AgentCapability(
                    name="ping",
                    description="Ping hosts for connectivity",
                    input_schema={"targets": "array", "count": "number"},
                    output_schema={"results": "array", "success_rate": "number"},
                    priority=2
                ),
                AgentCapability(
                    name="scan",
                    description="Port scan or vulnerability scan",
                    input_schema={"target": "string", "scan_type": "string", "ports": "array"},
                    output_schema={"open_ports": "array", "vulnerabilities": "array"},
                    priority=1
                ),
                AgentCapability(
                    name="bandwidth",
                    description="Measure network bandwidth",
                    input_schema={"interface": "string", "duration": "number"},
                    output_schema={"upload_mbps": "number", "download_mbps": "number"},
                    priority=3
                ),
                AgentCapability(
                    name="monitor",
                    description="Continuous network monitoring",
                    input_schema={"targets": "array", "interval": "number"},
                    output_schema={"metrics": "array", "alerts": "array"},
                    priority=2
                ),
                AgentCapability(
                    name="traceroute",
                    description="Trace network path",
                    input_schema={"target": "string"},
                    output_schema={"hops": "array"},
                    priority=3
                ),
            ]
        },
        AgentType.SECURITY: {
            "name": "Security Agent",
            "icon": "🔒",
            "description": "Security scanning, policy enforcement, encryption, and compliance",
            "endpoint": "http://security-agent:8005",
            "capabilities": [
                AgentCapability(
                    name="vuln_scan",
                    description="Scan for vulnerabilities",
                    input_schema={"target": "string", "scan_type": "string"},
                    output_schema={"vulnerabilities": "array", "risk_score": "number"},
                    priority=1
                ),
                AgentCapability(
                    name="config_scan",
                    description="Scan configuration for security issues",
                    input_schema={"config_path": "string", "standards": "array"},
                    output_schema={"violations": "array", "compliance_score": "number"},
                    priority=1
                ),
                AgentCapability(
                    name="encrypt",
                    description="Encrypt data or secrets",
                    input_schema={"data": "string", "method": "string"},
                    output_schema={"encrypted": "string", "key_id": "string"},
                    priority=2
                ),
                AgentCapability(
                    name="decrypt",
                    description="Decrypt data",
                    input_schema={"encrypted_data": "string", "key_id": "string"},
                    output_schema={"decrypted": "string"},
                    priority=2
                ),
                AgentCapability(
                    name="rotate_secret",
                    description="Rotate secrets or credentials",
                    input_schema={"secret_name": "string", "vault_path": "string"},
                    output_schema={"new_version": "string", "rotated_at": "string"},
                    priority=1
                ),
                AgentCapability(
                    name="policy_check",
                    description="Check against security policies",
                    input_schema={"resource": "string", "policy_set": "string"},
                    output_schema={"compliant": "boolean", "violations": "array"},
                    priority=2
                ),
                AgentCapability(
                    name="audit",
                    description="Generate security audit report",
                    input_schema={"scope": "string", "time_range": "string"},
                    output_schema={"report": "object", "findings": "array"},
                    priority=3
                ),
            ]
        }
    }
    
    @classmethod
    def get_agent_capabilities(cls, agent_type: AgentType) -> List[AgentCapability]:
        """Get capabilities for a specific agent"""
        agent_data = cls.AGENTS.get(agent_type, {})
        return agent_data.get("capabilities", [])
    
    @classmethod
    def get_all_capabilities(cls) -> Dict[str, List[AgentCapability]]:
        """Get all capabilities for all agents"""
        return {
            agent_type.value: agent_data["capabilities"]
            for agent_type, agent_data in cls.AGENTS.items()
        }
    
    @classmethod
    def find_best_agent(cls, task_description: str, required_action: str = None) -> AgentType:
        """Find the best agent for a given task"""
        task_lower = task_description.lower()
        
        # Direct action mapping
        if required_action:
            for agent_type, agent_data in cls.AGENTS.items():
                for cap in agent_data["capabilities"]:
                    if cap.name == required_action:
                        return agent_type
        
        # Keyword-based matching
        keywords = {
            AgentType.NETMON: ["network", "ping", "scan", "port", "bandwidth", "connectivity", "discover"],
            AgentType.DATA: ["data", "query", "validate", "transform", "backup", "database", "sql"],
            AgentType.DEVOPS: ["deploy", "build", "docker", "kubernetes", "scale", "restart", "pipeline"],
            AgentType.SECURITY: ["security", "vulnerability", "encrypt", "secret", "policy", "scan", "compliance"],
            AgentType.AI: ["analyze", "generate", "chat", "summarize", "text", "language", "understand"]
        }
        
        scores = {agent: 0 for agent in AgentType}
        for agent, words in keywords.items():
            for word in words:
                if word in task_lower:
                    scores[agent] += 1
        
        # Return agent with highest score
        best_agent = max(scores, key=scores.get)
        if scores[best_agent] > 0:
            return best_agent
        
        # Default to AI agent if no match
        return AgentType.AI
    
    @classmethod
    def route_task(cls, task_description: str, context: Dict = None) -> Dict[str, Any]:
        """Route a task to the appropriate agent with action details"""
        context = context or {}
        
        # Use AI to understand and route
        best_agent = cls.find_best_agent(task_description)
        agent_data = cls.AGENTS[best_agent]
        
        # Find best capability based on task
        capabilities = agent_data["capabilities"]
        best_cap = None
        
        for cap in capabilities:
            if any(keyword in task_description.lower() for keyword in cap.name.split("_")):
                best_cap = cap
                break
        
        # Default to first capability if no match
        if not best_cap and capabilities:
            best_cap = capabilities[0]
        
        return {
            "target_agent": best_agent.value,
            "agent_name": agent_data["name"],
            "action": best_cap.name if best_cap else "execute",
            "endpoint": agent_data["endpoint"],
            "confidence": 0.85,
            "reasoning": f"Task '{task_description}' requires {agent_data['name']} capabilities",
            "params": cls._infer_params(task_description, best_cap) if best_cap else {}
        }
    
    @classmethod
    def _infer_params(cls, task_description: str, capability: AgentCapability) -> Dict:
        """Infer parameters from task description"""
        params = {}
        
        # Extract common patterns
        import re
        
        # URL patterns
        urls = re.findall(r'https?://[^\s]+', task_description)
        if urls:
            params["url"] = urls[0]
        
        # IP addresses
        ips = re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', task_description)
        if ips:
            params["target"] = ips[0]
            params["targets"] = ips
        
        # Service names
        services = re.findall(r'service[s]?\s+(\w+)', task_description, re.IGNORECASE)
        if services:
            params["service"] = services[0]
        
        return params

# Create singleton instance
agent_registry = AgentRegistry()

if __name__ == "__main__":
    # Test routing
    test_tasks = [
        "Scan network 192.168.1.0/24 for devices",
        "Validate customer data in database",
        "Deploy the latest version of auth-service",
        "Check for security vulnerabilities in configs",
        "Generate a summary of yesterday's logs"
    ]
    
    for task in test_tasks:
        route = agent_registry.route_task(task)
        print(f"\nTask: {task}")
        print(f"→ Routed to: {route['agent_name']} ({route['target_agent']})")
        print(f"→ Action: {route['action']}")
        print(f"→ Endpoint: {route['endpoint']}")
