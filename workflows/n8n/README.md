# AI Platform - Full Automation System

Complete AI-driven automation for managing 20-system infrastructure with 5 specialized agents.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    🤖 AI Master Coordinator                   │
│                    (n8n + AI Agent)                          │
└──────────────┬──────────────────────────────────────────────┘
               │
    ┌──────────┴──────────┐
    │                     │
┌───▼───┐ ┌──────────┐ ┌──▼────┐ ┌────────┐ ┌─────────┐
│ 🌐    │ │ 📊       │ │ ⚙️    │ │ 🔒     │ │ 🤖      │
│NetMon │ │Data Agent│ │DevOps │ │Security│ │AI Agent │
│       │ │          │ │       │ │        │ │         │
└───┬───┘ └────┬─────┘ └───┬───┘ └───┬────┘ └────┬────┘
    │          │          │         │           │
    └──────────┴──────────┴─────────┴───────────┘
                  Redis Message Bus
```

## Agent Roles

### 1. 🤖 AI Agent (Master Coordinator)
**Location:** `http://ai-agent:8001`
**Capabilities:**
- Natural language understanding
- Task routing and delegation
- Generate reports and summaries
- Chat interface for humans
- Analyze complex data

### 2. 🌐 NetMon Agent (Network Scout)
**Location:** `http://netmon-agent:8004`
**Responsibilities:**
- Auto-discover all 20 systems
- Continuous network monitoring
- Ping tests and connectivity checks
- Port scanning for open services
- Bandwidth monitoring
- Alert on network anomalies

**Auto-Triggers:**
- Every 4 hours: Full network discovery
- Every 5 minutes: Health checks
- On anomaly: Alert Security Agent

### 3. 📊 Data Agent (Data Guardian)
**Location:** `http://data-agent:8002`
**Responsibilities:**
- Data validation and verification
- Database query optimization
- Data transformation
- Backup automation
- Deduplication and cleanup

**Auto-Triggers:**
- Every 6 hours: Data validation
- On failure: Alert DevOps (DB issues)
- On backup completion: Store to MinIO

### 4. ⚙️ DevOps Agent (Infrastructure Keeper)
**Location:** `http://devops-agent:8003`
**Responsibilities:**
- CI/CD pipeline automation
- Docker/Kubernetes management
- Service scaling (auto-scale on load)
- Health checks and restarts
- Auto-rollback on deployment failure

**Auto-Triggers:**
- On git push: Build & Deploy
- On health check fail: Restart service
- On high load: Auto-scale
- On deploy failure: Auto-rollback

### 5. 🔒 Security Agent (Security Shield)
**Location:** `http://security-agent:8005`
**Responsibilities:**
- Continuous vulnerability scanning
- Configuration security audit
- Secret rotation automation
- Policy compliance checks
- Auto-remediation of critical issues

**Auto-Triggers:**
- Twice daily: Full vulnerability scan
- On network anomaly: Deep inspection
- On critical finding: Auto-remediate
- On policy violation: Alert + Fix

## Automation Flow

### 1. Self-Healing System
```
Health Check (Every 5 min)
    ↓
[Agent Offline?] → Yes → Restart Container
    ↓ No
[Service Unhealthy?] → Yes → Auto-Restart
    ↓ No
[High Load?] → Yes → Auto-Scale
    ↓ No
[Deploy Failed?] → Yes → Auto-Rollback
```

### 2. Network Auto-Discovery
```
Every 4 Hours
    ↓
NetMon Agent: Discover subnet 192.168.1.0/24
    ↓
Data Agent: Store device inventory
    ↓
AI Agent: Analyze network topology
    ↓
Security Agent: Scan new devices
    ↓
Report stored in MinIO
```

### 3. CI/CD Pipeline
```
Git Push Detected
    ↓
DevOps Agent: Build Docker image
    ↓
Security Agent: Scan image for vulnerabilities
    ↓
DevOps Agent: Deploy to staging
    ↓
DevOps Agent: Run health checks
    ↓
[Health OK?] → Yes → Deploy to production
    ↓ No
DevOps Agent: Auto-rollback
    ↓
AI Agent: Summarize incident
```

### 4. Security Response
```
Vulnerability Scan (Twice daily)
    ↓
[Critical Found?] → Yes
    ↓
Security Agent: Auto-remediate
    ↓
DevOps Agent: Isolate affected system
    ↓
AI Agent: Generate incident report
    ↓
Slack Alert: #security-alerts
```

## Quick Start

### 1. Start All Services
```bash
docker compose up -d
```

### 2. Import n8n Workflows
```bash
# Access n8n at http://localhost:5678
# Go to Workflows → Import from File
# Import these 5 workflows:
# - 01-master-coordinator.json
# - 02-network-discovery.json
# - 03-data-pipeline.json
# - 04-cicd-pipeline.json
# - 05-security-monitor.json
```

### 3. Activate Workflows
In n8n interface:
1. Open each workflow
2. Click "Activate" toggle
3. Workflows will auto-run on schedules

### 4. Access Dashboard
```
http://localhost:8080
```
Dashboard features:
- Agent status monitoring
- Manual task execution
- Multi-agent chat/conversation
- View agent inboxes
- Shared context management

## API Endpoints

### Inter-Agent Communication
```bash
# Send message between agents
POST http://localhost:8000/communicate/message
{
  "sender": "ai",
  "recipient": "data",
  "message_type": "request",
  "content": {"action": "query", "sql": "SELECT * FROM logs"}
}

# Create multi-agent session
POST http://localhost:8000/communicate/session/create
{
  "participants": ["ai", "data", "security"],
  "initial_context": {"incident_id": "INC-001"}
}

# Delegate task with response
POST http://localhost:8000/communicate/delegate
{
  "from": "ai",
  "to": "netmon",
  "task": {"action": "ping", "params": {"target": "192.168.1.1"}}
}
```

### Direct Agent Execution
```bash
# Execute on any agent
POST http://localhost:8000/execute/{agent_type}
{
  "action": "{capability}",
  "params": {...}
}

# Examples:
curl -X POST http://localhost:8000/execute/netmon \
  -d '{"action": "discover", "params": {"subnet": "192.168.1.0/24"}}'

curl -X POST http://localhost:8000/execute/data \
  -d '{"action": "validate", "params": {"dataset": "customers"}}'

curl -X POST http://localhost:8000/execute/devops \
  -d '{"action": "deploy", "params": {"service": "api", "version": "v2.0"}}'

curl -X POST http://localhost:8000/execute/security \
  -d '{"action": "vuln_scan", "params": {"target": "all_systems"}}'
```

## Environment Configuration

### For 20 System Infrastructure
Update `.env`:
```env
# Network Configuration
NETWORK_SUBNET=192.168.1.0/24
SYSTEM_COUNT=20

# Auto-Healing Settings
AUTO_HEAL=true
HEALTH_CHECK_INTERVAL=300
MAX_RESTART_ATTEMPTS=3

# Auto-Scaling
AUTO_SCALE=true
SCALE_THRESHOLD_CPU=80
SCALE_THRESHOLD_MEM=85
MIN_REPLICAS=2
MAX_REPLICAS=10

# Security
AUTO_REMEDIATE=true
SECURITY_SCAN_SCHEDULE=0 2,14 * * *
ISOLATE_ON_BREACH=true

# CI/CD
AUTO_DEPLOY=true
AUTO_ROLLBACK=true
REQUIRE_SECURITY_SCAN=true
```

## Monitoring

### Prometheus Metrics
All agents expose metrics at `/metrics`:
- `agent_requests_total` - Request count
- `agent_tasks_total` - Task execution count
- `agent_errors_total` - Error count
- `agent_response_time` - Response time histogram

### Grafana Dashboards
Access at: `http://localhost:3000`
- Pre-built dashboards for each agent
- Infrastructure overview
- Alert configurations

## Troubleshooting

### Agent Offline
```bash
# Check agent status
curl http://localhost:8000/agents

# Restart specific agent
docker compose restart {agent-name}

# View logs
docker compose logs {agent-name} --tail 50
```

### Workflow Not Running
```bash
# Check n8n execution log
# In n8n UI: Executions → View history

# Test workflow manually
# In n8n: Open workflow → Execute Workflow
```

### Communication Issues
```bash
# Test Redis connection
docker compose exec redis redis-cli ping

# Check message bus
curl http://localhost:8000/communicate/shared-context/test
```

## Extending the System

### Add New Agent Capability
1. Update `shared/agent_capabilities.py`
2. Restart orchestrator
3. Update n8n workflow
4. Test via dashboard

### Custom Automation Rules
Edit n8n workflows:
- Add new trigger nodes
- Connect to different agents
- Add custom conditions
- Send notifications

## Support

For issues or questions:
1. Check logs: `docker compose logs -f`
2. Review dashboard: `http://localhost:8080`
3. Test APIs: `http://localhost:8000/docs`
4. n8n executions: `http://localhost:5678`

---

**Built with:** FastAPI, n8n, Redis, PostgreSQL, MinIO, Docker
