"""
Security Agent - Security & Secrets Management Agent
Handles security scans, vulnerability checks, secrets management with Vault, and encryption.
"""

import logging
import os
import hashlib
import re
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager
from datetime import datetime

import hvac
import httpx
import redis.asyncio as redis
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
from cryptography.fernet import Fernet

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter('security_agent_requests_total', 'Total requests', ['endpoint'])
SECURITY_SCANS = Counter('security_agent_scans_total', 'Security scans', ['scan_type'])

# Vault client setup
VAULT_ADDR = os.getenv("VAULT_ADDR", "http://vault:8200")
VAULT_TOKEN = os.getenv("VAULT_TOKEN", "dev-token")

try:
    vault_client = hvac.Client(url=VAULT_ADDR, token=VAULT_TOKEN)
except Exception as e:
    logger.warning(f"Vault client initialization failed: {e}")
    vault_client = None

# Redis client
redis_client: Optional[redis.Redis] = None

# Encryption key (in production, use proper key management)
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", Fernet.generate_key())
cipher_suite = Fernet(ENCRYPTION_KEY)

# Pydantic Models
class ScanRequest(BaseModel):
    target_type: str = Field(..., description="Type: code, config, secrets, container")
    target_path: str = Field(..., description="Path or identifier to scan")
    severity_threshold: str = Field(default="medium", description="low, medium, high, critical")

class SecretRequest(BaseModel):
    path: str = Field(..., description="Secret path in Vault")
    data: Optional[Dict[str, str]] = Field(default=None, description="Secret data to store")
    operation: str = Field(default="read", description="read, write, delete, list")

class EncryptRequest(BaseModel):
    data: str = Field(..., description="Data to encrypt")
    method: str = Field(default="fernet", description="Encryption method")

class DecryptRequest(BaseModel):
    encrypted_data: str = Field(..., description="Data to decrypt")
    method: str = Field(default="fernet", description="Encryption method")

class PolicyRequest(BaseModel):
    name: str = Field(..., description="Policy name")
    rules: Optional[str] = Field(default=None, description="HCL policy rules")
    operation: str = Field(default="read", description="read, create, update, delete")

class AgentResponse(BaseModel):
    result: Any
    operation: str
    success: bool
    timestamp: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    global redis_client
    redis_client = redis.from_url("redis://redis:6379", decode_responses=True)
    logger.info("Security Agent starting up...")
    
    yield
    
    if redis_client:
        await redis_client.close()
    logger.info("Security Agent shutting down...")

app = FastAPI(
    title="Security Agent",
    description="Security & Secrets Management Agent",
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
    vault_status = "unknown"
    if vault_client:
        try:
            vault_status = "healthy" if vault_client.is_authenticated() else "unauthenticated"
        except:
            vault_status = "unreachable"
    
    return {
        "status": "healthy",
        "service": "security-agent",
        "timestamp": datetime.utcnow().isoformat(),
        "capabilities": ["security_scan", "secrets_management", "encryption", "policy_management"],
        "vault_status": vault_status
    }

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/execute")
async def execute(data: Dict[str, Any]):
    """Main execution endpoint for orchestrator"""
    action = data.get("action", "scan")
    
    if action == "scan":
        req = ScanRequest(**data.get("params", {}))
        return await security_scan(req)
    elif action == "secret":
        req = SecretRequest(**data.get("params", {}))
        return await manage_secret(req)
    elif action == "encrypt":
        req = EncryptRequest(**data.get("params", {}))
        return await encrypt_data(req)
    elif action == "decrypt":
        req = DecryptRequest(**data.get("params", {}))
        return await decrypt_data(req)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {action}")

@app.post("/scan", response_model=AgentResponse)
async def security_scan(request: ScanRequest):
    """Perform security scan"""
    REQUEST_COUNT.labels(endpoint="scan").inc()
    SECURITY_SCANS.labels(scan_type=request.target_type).inc()
    
    try:
        logger.info(f"Starting {request.target_type} scan on {request.target_path}")
        
        findings = []
        
        if request.target_type == "secrets":
            # Scan for secrets in code/config
            secret_patterns = {
                "API Key": r'[Aa][Pp][Ii][-_]?[Kk][Ee][Yy]\s*[:=]\s*["\']?([a-zA-Z0-9_-]{16,})["\']?',
                "Password": r'[Pp][Aa][Ss][Ss][Ww][Oo][Rr][Dd]\s*[:=]\s*["\']([^"\']+)["\']',
                "Private Key": r'-----BEGIN (RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----',
                "AWS Key": r'AKIA[0-9A-Z]{16}',
                "GitHub Token": r'gh[pousr]_[A-Za-z0-9_]{36,}',
                "Slack Token": r'xox[baprs]-[0-9]{10,13}-[0-9]{10,13}',
            }
            
            for pattern_name, pattern in secret_patterns.items():
                matches = re.findall(pattern, request.target_path)
                if matches:
                    findings.append({
                        "type": "secret_exposure",
                        "severity": "critical",
                        "pattern": pattern_name,
                        "matches": matches
                    })
        
        elif request.target_type == "config":
            # Check for insecure configurations
            insecure_patterns = [
                {"pattern": r"password\s*=\s*\"[^\"]+\"", "severity": "high", "type": "hardcoded_password"},
                {"pattern": r"debug\s*=\s*true", "severity": "medium", "type": "debug_enabled"},
                {"pattern": r"ssl_verify\s*=\s*false", "severity": "high", "type": "ssl_disabled"},
                {"pattern": r"allow_origin\s*:\s*\"\*\"", "severity": "medium", "type": "permissive_cors"},
            ]
            
            for check in insecure_patterns:
                if re.search(check["pattern"], request.target_path, re.IGNORECASE):
                    findings.append({
                        "type": check["type"],
                        "severity": check["severity"],
                        "description": f"Insecure configuration detected: {check['type']}"
                    })
        
        elif request.target_type == "hash":
            # Calculate file/directory hash
            if os.path.isfile(request.target_path):
                with open(request.target_path, 'rb') as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()
                findings.append({"type": "file_hash", "path": request.target_path, "sha256": file_hash})
            else:
                findings.append({"type": "error", "message": "Path not found or not a file"})
        
        return AgentResponse(
            result={
                "scan_type": request.target_type,
                "target": request.target_path,
                "findings_count": len(findings),
                "findings": findings,
                "risk_score": calculate_risk_score(findings)
            },
            operation="security_scan",
            success=True,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Security scan failed: {e}")
        return AgentResponse(
            result=None,
            operation="security_scan",
            success=False,
            timestamp=datetime.utcnow().isoformat()
        )

def calculate_risk_score(findings: List[Dict]) -> int:
    """Calculate risk score based on findings"""
    severity_weights = {"critical": 10, "high": 5, "medium": 2, "low": 1}
    score = 0
    for finding in findings:
        severity = finding.get("severity", "low")
        score += severity_weights.get(severity, 1)
    return min(score, 100)  # Cap at 100

@app.post("/secret", response_model=AgentResponse)
async def manage_secret(request: SecretRequest):
    """Manage secrets in Vault"""
    REQUEST_COUNT.labels(endpoint="secret").inc()
    
    if not vault_client or not vault_client.is_authenticated():
        return AgentResponse(
            result=None,
            operation="secret_management",
            success=False,
            timestamp=datetime.utcnow().isoformat()
        )
    
    try:
        if request.operation == "read":
            secret = vault_client.secrets.kv.v2.read_secret_version(path=request.path)
            result = {"data": secret["data"]["data"]}
        
        elif request.operation == "write":
            if not request.data:
                raise HTTPException(status_code=400, detail="No data provided for write operation")
            
            vault_client.secrets.kv.v2.create_or_update_secret(
                path=request.path,
                secret=request.data
            )
            result = {"message": f"Secret written to {request.path}"}
        
        elif request.operation == "delete":
            vault_client.secrets.kv.v2.delete_metadata_and_all_versions(path=request.path)
            result = {"message": f"Secret deleted from {request.path}"}
        
        elif request.operation == "list":
            list_response = vault_client.secrets.kv.v2.list_secrets(path=request.path)
            result = {"keys": list_response["data"]["keys"]}
        
        else:
            raise HTTPException(status_code=400, detail=f"Unknown operation: {request.operation}")
        
        return AgentResponse(
            result=result,
            operation=f"secret_{request.operation}",
            success=True,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Secret management failed: {e}")
        return AgentResponse(
            result=None,
            operation=f"secret_{request.operation}",
            success=False,
            timestamp=datetime.utcnow().isoformat()
        )

@app.post("/encrypt", response_model=AgentResponse)
async def encrypt_data(request: EncryptRequest):
    """Encrypt data"""
    REQUEST_COUNT.labels(endpoint="encrypt").inc()
    
    try:
        if request.method == "fernet":
            encrypted = cipher_suite.encrypt(request.data.encode()).decode()
            result = {"encrypted": encrypted, "method": "fernet"}
        elif request.method == "sha256":
            hashed = hashlib.sha256(request.data.encode()).hexdigest()
            result = {"hash": hashed, "method": "sha256"}
        else:
            raise HTTPException(status_code=400, detail=f"Unknown encryption method: {request.method}")
        
        return AgentResponse(
            result=result,
            operation="encrypt",
            success=True,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        return AgentResponse(
            result=None,
            operation="encrypt",
            success=False,
            timestamp=datetime.utcnow().isoformat()
        )

@app.post("/decrypt", response_model=AgentResponse)
async def decrypt_data(request: DecryptRequest):
    """Decrypt data"""
    REQUEST_COUNT.labels(endpoint="decrypt").inc()
    
    try:
        if request.method == "fernet":
            decrypted = cipher_suite.decrypt(request.encrypted_data.encode()).decode()
            result = {"decrypted": decrypted, "method": "fernet"}
        else:
            raise HTTPException(status_code=400, detail=f"Unknown decryption method: {request.method}")
        
        return AgentResponse(
            result=result,
            operation="decrypt",
            success=True,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        return AgentResponse(
            result=None,
            operation="decrypt",
            success=False,
            timestamp=datetime.utcnow().isoformat()
        )

@app.post("/policy", response_model=AgentResponse)
async def manage_policy(request: PolicyRequest):
    """Manage Vault policies"""
    REQUEST_COUNT.labels(endpoint="policy").inc()
    
    if not vault_client or not vault_client.is_authenticated():
        return AgentResponse(
            result=None,
            operation="policy_management",
            success=False,
            timestamp=datetime.utcnow().isoformat()
        )
    
    try:
        if request.operation == "read":
            policy = vault_client.sys.read_policy(name=request.name)
            result = {"policy": policy["data"]["rules"]}
        
        elif request.operation == "create" or request.operation == "update":
            if not request.rules:
                raise HTTPException(status_code=400, detail="No rules provided")
            
            vault_client.sys.create_or_update_policy(name=request.name, policy=request.rules)
            result = {"message": f"Policy {request.name} created/updated"}
        
        elif request.operation == "delete":
            vault_client.sys.delete_policy(name=request.name)
            result = {"message": f"Policy {request.name} deleted"}
        
        elif request.operation == "list":
            policies = vault_client.sys.list_policies()
            result = {"policies": policies["data"]["policies"]}
        
        else:
            raise HTTPException(status_code=400, detail=f"Unknown operation: {request.operation}")
        
        return AgentResponse(
            result=result,
            operation=f"policy_{request.operation}",
            success=True,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Policy management failed: {e}")
        return AgentResponse(
            result=None,
            operation=f"policy_{request.operation}",
            success=False,
            timestamp=datetime.utcnow().isoformat()
        )

@app.get("/audit/logs")
async def get_audit_logs(limit: int = 100):
    """Get recent security audit events"""
    try:
        # This would typically query an audit log database
        # For now, return a placeholder
        return {
            "events": [],
            "message": "Audit logging configured but no events recorded yet"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
