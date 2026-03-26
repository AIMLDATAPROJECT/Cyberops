"""
Network Monitoring Agent - Network Performance & Diagnostics Agent
Handles network monitoring, latency tests, bandwidth monitoring, and diagnostics.
"""

import logging
import os
import socket
import subprocess
import platform
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager
from datetime import datetime
import time

import psutil
import httpx
import redis.asyncio as redis
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter('netmon_agent_requests_total', 'Total requests', ['endpoint'])
NETWORK_LATENCY = Gauge('netmon_network_latency_ms', 'Network latency in ms', ['target'])
BANDWIDTH_USAGE = Gauge('netmon_bandwidth_usage_bytes', 'Bandwidth usage in bytes', ['direction'])
PACKET_LOSS = Gauge('netmon_packet_loss_percent', 'Packet loss percentage', ['target'])

# Redis client
redis_client: Optional[redis.Redis] = None

# Pydantic Models
class PingRequest(BaseModel):
    target: str = Field(..., description="Host to ping")
    count: int = Field(default=4, ge=1, le=20)
    timeout: int = Field(default=5)

class ScanRequest(BaseModel):
    target: str = Field(..., description="Network to scan")
    port_range: str = Field(default="1-1000", description="Port range to scan")

class BandwidthTestRequest(BaseModel):
    test_type: str = Field(default="speedtest", description="Type of bandwidth test")
    server: Optional[str] = Field(default=None)

class MonitorStartRequest(BaseModel):
    interface: str = Field(..., description="Network interface to monitor")
    duration: int = Field(default=60, description="Monitoring duration in seconds")
    interval: int = Field(default=5, description="Sampling interval in seconds")

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
    logger.info("Network Monitoring Agent starting up...")
    
    yield
    
    if redis_client:
        await redis_client.close()
    logger.info("Network Monitoring Agent shutting down...")

app = FastAPI(
    title="Network Monitoring Agent",
    description="Network Performance & Diagnostics Agent",
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
    # Get network interface info
    net_io = psutil.net_io_counters()
    
    return {
        "status": "healthy",
        "service": "netmon-agent",
        "timestamp": datetime.utcnow().isoformat(),
        "capabilities": ["ping", "bandwidth_test", "port_scan", "traffic_monitor", "dns_lookup"],
        "network_stats": {
            "bytes_sent": net_io.bytes_sent,
            "bytes_recv": net_io.bytes_recv,
            "packets_sent": net_io.packets_sent,
            "packets_recv": net_io.packets_recv
        }
    }

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/execute")
async def execute(data: Dict[str, Any]):
    """Main execution endpoint for orchestrator"""
    action = data.get("action", "ping")
    
    if action == "ping":
        req = PingRequest(**data.get("params", {}))
        return await ping_host(req)
    elif action == "bandwidth_test":
        req = BandwidthTestRequest(**data.get("params", {}))
        return await bandwidth_test(req)
    elif action == "port_scan":
        req = ScanRequest(**data.get("params", {}))
        return await port_scan(req)
    elif action == "monitor":
        req = MonitorStartRequest(**data.get("params", {}))
        return await monitor_traffic(req)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {action}")

@app.post("/ping", response_model=AgentResponse)
async def ping_host(request: PingRequest):
    """Ping a host and return latency statistics"""
    REQUEST_COUNT.labels(endpoint="ping").inc()
    
    try:
        logger.info(f"Pinging {request.target}...")
        
        # Use ping3 library for cross-platform compatibility
        from ping3 import ping
        
        latencies = []
        packet_loss = 0
        
        for _ in range(request.count):
            delay = ping(request.target, timeout=request.timeout)
            if delay is not None:
                latencies.append(delay * 1000)  # Convert to ms
            else:
                packet_loss += 1
            time.sleep(0.5)
        
        # Update metrics
        if latencies:
            avg_latency = sum(latencies) / len(latencies)
            NETWORK_LATENCY.labels(target=request.target).set(avg_latency)
        
        packet_loss_pct = (packet_loss / request.count) * 100 if request.count > 0 else 0
        PACKET_LOSS.labels(target=request.target).set(packet_loss_pct)
        
        result = {
            "target": request.target,
            "packets_sent": request.count,
            "packets_received": len(latencies),
            "packet_loss_percent": packet_loss_pct,
            "latencies_ms": latencies,
            "min_ms": min(latencies) if latencies else None,
            "max_ms": max(latencies) if latencies else None,
            "avg_ms": sum(latencies) / len(latencies) if latencies else None
        }
        
        return AgentResponse(
            result=result,
            operation="ping",
            success=len(latencies) > 0,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Ping failed: {e}")
        return AgentResponse(
            result=None,
            operation="ping",
            success=False,
            timestamp=datetime.utcnow().isoformat()
        )

@app.post("/bandwidth", response_model=AgentResponse)
async def bandwidth_test(request: BandwidthTestRequest):
    """Test internet bandwidth"""
    REQUEST_COUNT.labels(endpoint="bandwidth").inc()
    
    try:
        logger.info("Starting bandwidth test...")
        
        import speedtest
        
        st = speedtest.Speedtest()
        st.get_best_server()
        
        download_speed = st.download()  # in bytes/s
        upload_speed = st.upload()      # in bytes/s
        
        # Update metrics
        BANDWIDTH_USAGE.labels(direction="download").set(download_speed)
        BANDWIDTH_USAGE.labels(direction="upload").set(upload_speed)
        
        result = {
            "download_mbps": download_speed / 1_000_000 * 8,
            "upload_mbps": upload_speed / 1_000_000 * 8,
            "ping_ms": st.results.ping,
            "server": {
                "name": st.results.server["name"],
                "location": st.results.server["country"],
                "host": st.results.server["host"]
            },
            "client": {
                "ip": st.results.client["ip"],
                "isp": st.results.client["isp"]
            }
        }
        
        return AgentResponse(
            result=result,
            operation="bandwidth_test",
            success=True,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Bandwidth test failed: {e}")
        return AgentResponse(
            result=None,
            operation="bandwidth_test",
            success=False,
            timestamp=datetime.utcnow().isoformat()
        )

@app.post("/scan", response_model=AgentResponse)
async def port_scan(request: ScanRequest):
    """Scan ports on a target"""
    REQUEST_COUNT.labels(endpoint="scan").inc()
    
    try:
        logger.info(f"Scanning {request.target} ports {request.port_range}")
        
        # Parse port range
        if "-" in request.port_range:
            start, end = map(int, request.port_range.split("-"))
        else:
            start = end = int(request.port_range)
        
        open_ports = []
        
        for port in range(start, end + 1):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.5)
                result = sock.connect_ex((request.target, port))
                if result == 0:
                    try:
                        service = socket.getservbyport(port)
                    except:
                        service = "unknown"
                    open_ports.append({"port": port, "service": service})
                sock.close()
            except:
                pass
        
        return AgentResponse(
            result={
                "target": request.target,
                "ports_scanned": end - start + 1,
                "open_ports": open_ports
            },
            operation="port_scan",
            success=True,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Port scan failed: {e}")
        return AgentResponse(
            result=None,
            operation="port_scan",
            success=False,
            timestamp=datetime.utcnow().isoformat()
        )

@app.post("/monitor", response_model=AgentResponse)
async def monitor_traffic(request: MonitorStartRequest):
    """Monitor network traffic for a specified duration"""
    REQUEST_COUNT.labels(endpoint="monitor").inc()
    
    try:
        logger.info(f"Monitoring interface {request.interface} for {request.duration}s")
        
        # Get initial stats
        initial_io = psutil.net_io_counters(pernic=True).get(request.interface)
        if not initial_io:
            return AgentResponse(
                result=None,
                operation="monitor",
                success=False,
                timestamp=datetime.utcnow().isoformat()
            )
        
        samples = []
        
        for _ in range(request.duration // request.interval):
            time.sleep(request.interval)
            current_io = psutil.net_io_counters(pernic=True).get(request.interface)
            
            sample = {
                "timestamp": datetime.utcnow().isoformat(),
                "bytes_sent": current_io.bytes_sent - initial_io.bytes_sent,
                "bytes_recv": current_io.bytes_recv - initial_io.bytes_recv,
                "packets_sent": current_io.packets_sent - initial_io.packets_sent,
                "packets_recv": current_io.packets_recv - initial_io.packets_recv,
                "errin": current_io.errin,
                "errout": current_io.errout,
                "dropin": current_io.dropin,
                "dropout": current_io.dropout
            }
            samples.append(sample)
            initial_io = current_io
        
        return AgentResponse(
            result={
                "interface": request.interface,
                "duration": request.duration,
                "samples": samples,
                "total_bytes_sent": sum(s["bytes_sent"] for s in samples),
                "total_bytes_recv": sum(s["bytes_recv"] for s in samples)
            },
            operation="monitor",
            success=True,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Traffic monitor failed: {e}")
        return AgentResponse(
            result=None,
            operation="monitor",
            success=False,
            timestamp=datetime.utcnow().isoformat()
        )

@app.get("/interfaces")
async def list_interfaces():
    """List all network interfaces"""
    try:
        interfaces = psutil.net_if_addrs()
        result = {}
        
        for name, addrs in interfaces.items():
            result[name] = [
                {
                    "family": addr.family.name if hasattr(addr.family, 'name') else str(addr.family),
                    "address": addr.address,
                    "netmask": addr.netmask,
                    "broadcast": addr.broadcast
                }
                for addr in addrs
            ]
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/connections")
async def list_connections():
    """List current network connections"""
    try:
        connections = psutil.net_connections()
        result = [
            {
                "fd": conn.fd,
                "family": conn.family.name if hasattr(conn.family, 'name') else str(conn.family),
                "type": conn.type.name if hasattr(conn.type, 'name') else str(conn.type),
                "local_address": conn.laddr._asdict() if conn.laddr else None,
                "remote_address": conn.raddr._asdict() if conn.raddr else None,
                "status": conn.status,
                "pid": conn.pid
            }
            for conn in connections
        ]
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/dns/{hostname}")
async def dns_lookup(hostname: str):
    """DNS lookup for a hostname"""
    try:
        addresses = socket.getaddrinfo(hostname, None)
        result = [
            {
                "family": addr[0].name if hasattr(addr[0], 'name') else str(addr[0]),
                "type": addr[1].name if hasattr(addr[1], 'name') else str(addr[1]),
                "ip": addr[4][0]
            }
            for addr in addresses
        ]
        return {"hostname": hostname, "addresses": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
