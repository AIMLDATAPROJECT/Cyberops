"""
DevOps Agent - Infrastructure & Deployment Agent
Handles Docker, Kubernetes, CI/CD, and Infrastructure as Code operations.
"""

import logging
import os
import subprocess
import json
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager
from datetime import datetime

import docker
import httpx
import redis.asyncio as redis
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter('devops_agent_requests_total', 'Total requests', ['endpoint'])
DEPLOYMENTS = Counter('devops_agent_deployments_total', 'Deployments', ['type'])

# Docker client - initialized lazily to handle connection errors
docker_client = None

def get_docker_client():
    global docker_client
    if docker_client is None:
        try:
            docker_client = docker.DockerClient(base_url='unix:///var/run/docker.sock')
        except Exception as e:
            logger.warning(f"Docker client not available: {e}")
            return None
    return docker_client

# Redis client
redis_client: Optional[redis.Redis] = None

# Pydantic Models
class DockerBuildRequest(BaseModel):
    context_path: str = Field(..., description="Path to build context")
    dockerfile: str = Field(default="Dockerfile", description="Dockerfile name")
    tag: str = Field(..., description="Image tag")
    build_args: Optional[Dict[str, str]] = Field(default_factory=dict)

class DockerDeployRequest(BaseModel):
    image: str = Field(..., description="Docker image to deploy")
    container_name: str = Field(..., description="Container name")
    ports: Optional[Dict[str, int]] = Field(default_factory=dict)
    env_vars: Optional[Dict[str, str]] = Field(default_factory=dict)
    volumes: Optional[Dict[str, str]] = Field(default_factory=dict)
    network: Optional[str] = Field(default=None)

class K8sDeployRequest(BaseModel):
    namespace: str = Field(default="default")
    manifest: Dict[str, Any] = Field(..., description="Kubernetes manifest")
    wait: bool = Field(default=True)

class TerraformRequest(BaseModel):
    working_dir: str = Field(..., description="Terraform working directory")
    action: str = Field(..., description="init, plan, apply, destroy")
    vars: Optional[Dict[str, str]] = Field(default_factory=dict)

class CommandRequest(BaseModel):
    command: str = Field(..., description="Shell command to execute")
    working_dir: Optional[str] = Field(default="/app")
    timeout: int = Field(default=60)

class AgentResponse(BaseModel):
    result: Any
    operation: str
    success: bool
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    timestamp: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    global redis_client
    redis_client = redis.from_url("redis://redis:6379", decode_responses=True)
    logger.info("DevOps Agent starting up...")
    
    yield
    
    if redis_client:
        await redis_client.close()
    logger.info("DevOps Agent shutting down...")

app = FastAPI(
    title="DevOps Agent",
    description="Infrastructure & Deployment Agent",
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
    docker_version = "unknown"
    try:
        docker_version = get_docker_client().version()["Version"]
    except:
        pass
    
    return {
        "status": "healthy",
        "service": "devops-agent",
        "timestamp": datetime.utcnow().isoformat(),
        "capabilities": ["docker", "kubernetes", "terraform", "ansible", "ssh"],
        "docker_version": docker_version
    }

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/execute")
async def execute(data: Dict[str, Any]):
    """Main execution endpoint for orchestrator"""
    action = data.get("action", "command")
    
    if action == "docker_build":
        req = DockerBuildRequest(**data.get("params", {}))
        return await docker_build(req)
    elif action == "docker_deploy":
        req = DockerDeployRequest(**data.get("params", {}))
        return await docker_deploy(req)
    elif action == "k8s_deploy":
        req = K8sDeployRequest(**data.get("params", {}))
        return await k8s_deploy(req)
    elif action == "terraform":
        req = TerraformRequest(**data.get("params", {}))
        return await run_terraform(req)
    elif action == "command":
        req = CommandRequest(**data.get("params", {}))
        return await run_command(req)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {action}")

@app.post("/docker/build", response_model=AgentResponse)
async def docker_build(request: DockerBuildRequest):
    """Build a Docker image"""
    REQUEST_COUNT.labels(endpoint="docker_build").inc()
    
    try:
        logger.info(f"Building Docker image: {request.tag}")
        
        image, build_logs = get_docker_client().images.build(
            path=request.context_path,
            dockerfile=request.dockerfile,
            tag=request.tag,
            buildargs=request.build_args,
            rm=True
        )
        
        log_output = ""
        for line in build_logs:
            if 'stream' in line:
                log_output += line['stream']
        
        DEPLOYMENTS.labels(type="docker_build").inc()
        
        return AgentResponse(
            result={"image_id": image.id, "tags": image.tags},
            operation="docker_build",
            success=True,
            stdout=log_output,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Docker build failed: {e}")
        return AgentResponse(
            result=None,
            operation="docker_build",
            success=False,
            stderr=str(e),
            timestamp=datetime.utcnow().isoformat()
        )

@app.post("/docker/deploy", response_model=AgentResponse)
async def docker_deploy(request: DockerDeployRequest):
    """Deploy a Docker container"""
    REQUEST_COUNT.labels(endpoint="docker_deploy").inc()
    
    try:
        logger.info(f"Deploying container: {request.container_name}")
        
        # Check if container exists
        try:
            old_container = get_docker_client().containers.get(request.container_name)
            old_container.stop()
            old_container.remove()
            logger.info(f"Removed existing container: {request.container_name}")
        except docker.errors.NotFound:
            pass
        
        # Run new container
        container = get_docker_client().containers.run(
            image=request.image,
            name=request.container_name,
            ports=request.ports,
            environment=request.env_vars,
            volumes=request.volumes,
            network=request.network,
            detach=True,
            restart_policy={"Name": "unless-stopped"}
        )
        
        DEPLOYMENTS.labels(type="docker_deploy").inc()
        
        return AgentResponse(
            result={
                "container_id": container.id,
                "name": container.name,
                "status": container.status,
                "ports": container.ports
            },
            operation="docker_deploy",
            success=True,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Docker deploy failed: {e}")
        return AgentResponse(
            result=None,
            operation="docker_deploy",
            success=False,
            stderr=str(e),
            timestamp=datetime.utcnow().isoformat()
        )

@app.post("/docker/stop/{container_name}", response_model=AgentResponse)
async def docker_stop(container_name: str):
    """Stop a Docker container"""
    try:
        container = get_docker_client().containers.get(container_name)
        container.stop()
        
        return AgentResponse(
            result={"name": container_name, "status": "stopped"},
            operation="docker_stop",
            success=True,
            timestamp=datetime.utcnow().isoformat()
        )
    except Exception as e:
        return AgentResponse(
            result=None,
            operation="docker_stop",
            success=False,
            stderr=str(e),
            timestamp=datetime.utcnow().isoformat()
        )

@app.get("/docker/containers")
async def list_containers(all: bool = True):
    """List Docker containers"""
    try:
        containers = get_docker_client().containers.list(all=all)
        return [
            {
                "id": c.id[:12],
                "name": c.name,
                "image": c.image.tags[0] if c.image.tags else "<none>",
                "status": c.status,
                "ports": c.ports,
                "created": c.attrs["Created"]
            }
            for c in containers
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/k8s/deploy", response_model=AgentResponse)
async def k8s_deploy(request: K8sDeployRequest):
    """Deploy to Kubernetes"""
    REQUEST_COUNT.labels(endpoint="k8s_deploy").inc()
    
    try:
        from kubernetes import client, config
        
        # Load kubeconfig
        try:
            config.load_incluster_config()
        except:
            config.load_kube_config()
        
        api = client.CoreV1Api()
        apps_api = client.AppsV1Api()
        
        kind = request.manifest.get("kind", "")
        name = request.manifest.get("metadata", {}).get("name", "")
        
        logger.info(f"Deploying {kind}/{name} to namespace {request.namespace}")
        
        if kind == "Deployment":
            apps_api.create_namespaced_deployment(
                namespace=request.namespace,
                body=request.manifest
            )
        elif kind == "Service":
            api.create_namespaced_service(
                namespace=request.namespace,
                body=request.manifest
            )
        elif kind == "ConfigMap":
            api.create_namespaced_config_map(
                namespace=request.namespace,
                body=request.manifest
            )
        elif kind == "Pod":
            api.create_namespaced_pod(
                namespace=request.namespace,
                body=request.manifest
            )
        else:
            # Generic resource creation
            return AgentResponse(
                result=None,
                operation="k8s_deploy",
                success=False,
                stderr=f"Unsupported resource kind: {kind}",
                timestamp=datetime.utcnow().isoformat()
            )
        
        DEPLOYMENTS.labels(type="k8s").inc()
        
        return AgentResponse(
            result={"kind": kind, "name": name, "namespace": request.namespace},
            operation="k8s_deploy",
            success=True,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"K8s deploy failed: {e}")
        return AgentResponse(
            result=None,
            operation="k8s_deploy",
            success=False,
            stderr=str(e),
            timestamp=datetime.utcnow().isoformat()
        )

@app.get("/k8s/pods")
async def list_pods(namespace: str = "default"):
    """List Kubernetes pods"""
    try:
        from kubernetes import client, config
        
        try:
            config.load_incluster_config()
        except:
            config.load_kube_config()
        
        api = client.CoreV1Api()
        pods = api.list_namespaced_pod(namespace=namespace)
        
        return [
            {
                "name": pod.metadata.name,
                "status": pod.status.phase,
                "ip": pod.status.pod_ip,
                "node": pod.spec.node_name,
                "created": pod.metadata.creation_timestamp.isoformat() if pod.metadata.creation_timestamp else None
            }
            for pod in pods.items
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/terraform", response_model=AgentResponse)
async def run_terraform(request: TerraformRequest):
    """Execute Terraform commands"""
    REQUEST_COUNT.labels(endpoint="terraform").inc()
    
    try:
        import terraform as tf
        
        working_dir = request.working_dir
        action = request.action
        
        logger.info(f"Running terraform {action} in {working_dir}")
        
        # Change to working directory
        import os as os_module
        original_dir = os_module.getcwd()
        os_module.chdir(working_dir)
        
        try:
            tf_path = subprocess.run(["which", "terraform"], capture_output=True, text=True).stdout.strip()
            
            if action == "init":
                result = subprocess.run(
                    [tf_path, "init", "-no-color"],
                    capture_output=True,
                    text=True,
                    timeout=120
                )
            elif action == "plan":
                result = subprocess.run(
                    [tf_path, "plan", "-no-color"] + [f"-var={k}={v}" for k, v in request.vars.items()],
                    capture_output=True,
                    text=True,
                    timeout=120
                )
            elif action == "apply":
                result = subprocess.run(
                    [tf_path, "apply", "-auto-approve", "-no-color"] + [f"-var={k}={v}" for k, v in request.vars.items()],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
            elif action == "destroy":
                result = subprocess.run(
                    [tf_path, "destroy", "-auto-approve", "-no-color"],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
            else:
                return AgentResponse(
                    result=None,
                    operation=f"terraform_{action}",
                    success=False,
                    stderr=f"Unknown action: {action}",
                    timestamp=datetime.utcnow().isoformat()
                )
            
            DEPLOYMENTS.labels(type="terraform").inc()
            
            return AgentResponse(
                result={"returncode": result.returncode},
                operation=f"terraform_{action}",
                success=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                timestamp=datetime.utcnow().isoformat()
            )
            
        finally:
            os_module.chdir(original_dir)
        
    except Exception as e:
        logger.error(f"Terraform failed: {e}")
        return AgentResponse(
            result=None,
            operation=f"terraform_{request.action}",
            success=False,
            stderr=str(e),
            timestamp=datetime.utcnow().isoformat()
        )

@app.post("/command", response_model=AgentResponse)
async def run_command(request: CommandRequest):
    """Execute a shell command"""
    REQUEST_COUNT.labels(endpoint="command").inc()
    
    try:
        logger.info(f"Executing command: {request.command}")
        
        result = subprocess.run(
            request.command,
            shell=True,
            cwd=request.working_dir,
            capture_output=True,
            text=True,
            timeout=request.timeout
        )
        
        return AgentResponse(
            result={"returncode": result.returncode},
            operation="command",
            success=result.returncode == 0,
            stdout=result.stdout,
            stderr=result.stderr,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except subprocess.TimeoutExpired:
        return AgentResponse(
            result=None,
            operation="command",
            success=False,
            stderr=f"Command timed out after {request.timeout} seconds",
            timestamp=datetime.utcnow().isoformat()
        )
    except Exception as e:
        return AgentResponse(
            result=None,
            operation="command",
            success=False,
            stderr=str(e),
            timestamp=datetime.utcnow().isoformat()
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
