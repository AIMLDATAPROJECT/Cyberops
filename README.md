# AI PLATFORM
## Complete Setup & Installation Guide

**Dev Environment · Docker Compose · Step-by-Step**

---

**Team Size:** 8 Engineers | **Phases:** 6 | **Services:** 20+  
**OS Support:** Windows 11 · macOS · Ubuntu/Linux

---

## ABOUT

This guide takes you from a fresh machine to a fully running AI Platform dev environment. Follow every step in order. **Do not skip steps.**

---

## TIME

**Estimated time:** 2-4 hours for first setup. After setup, starting everything takes **2 minutes with one command**.

---

# SECTION 0 — BEFORE YOU START

Complete this checklist before running any install commands. Every item is required.

---

## 0.1 Hardware Requirements

| Component | Minimum | Recommended (best) |
|-----------|---------|-------------------|
| **CPU** | 4 cores / 8 threads | 8+ cores (for parallel agents) |
| **RAM** | 16 GB | 32 GB (for LLM + all agents) |
| **Disk** | 50 GB free | 100 GB+ SSD (models are large) |
| **GPU** | Not required (CPU fallback) | NVIDIA 8GB+ VRAM for real LLM |
| **Internet** | Required for downloads | Stable broadband (5-10 GB downloads) |

---

## 0.2 Pre-Install Checklist

- [ ] I have a machine with 16 GB+ RAM
- [ ] I have 50 GB+ free disk space
- [ ] I have stable internet connection
- [ ] Docker Desktop is installed (latest version)
- [ ] Docker Compose is available (v2.0+)
- [ ] Git is installed
- [ ] Ports 8000-8005, 3000, 5432, 6379, 9000, 9090, 11434 are free

---

## 0.3 Supported Operating Systems

| OS | Version | Notes |
|-----|---------|-------|
| **Windows** | 10/11 (Pro/Enterprise) | Use WSL2 for best performance |
| **macOS** | 12+ (Monterey+) | Both Intel & Apple Silicon supported |
| **Linux** | Ubuntu 20.04+, CentOS 8+, Debian 11+ | Native Docker support |

---

# SECTION 1 — INSTALL DEPENDENCIES

## 1.1 Install Docker

### Windows
```powershell
# Download from https://docs.docker.com/desktop/install/windows-install/
# Or use winget:
winget install Docker.DockerDesktop
```

### macOS
```bash
# Download from https://docs.docker.com/desktop/install/mac-install/
# Or use Homebrew:
brew install --cask docker
```

### Ubuntu/Linux
```bash
# Remove old versions
sudo apt-get remove docker docker-engine docker.io containerd runc

# Install prerequisites
sudo apt-get update
sudo apt-get install ca-certificates curl gnupg lsb-release

# Add Docker's official GPG key
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Set up the repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Verify installation
sudo docker run hello-world
```

---

## 1.2 Verify Docker Compose Version

```bash
docker compose version
# Should show: Docker Compose version v2.x.x
```

---

## 1.3 (Optional) Install Make

### Windows (via chocolatey)
```powershell
choco install make
```

### macOS
```bash
# Included with Xcode Command Line Tools
xcode-select --install
```

### Ubuntu/Linux
```bash
sudo apt-get install make
```

---

# SECTION 2 — GET THE CODE

## 2.1 Clone Repository

```bash
git clone https://github.com/your-org/ai-platform.git
cd ai-platform
```

## 2.2 Project Structure

```
ai-platform/
├── docker-compose.yml          # Main orchestration file
├── Makefile                    # Helper commands
├── .env                        # Environment variables (create from .env.example)
├── .env.example                # Environment template
├── README.md                   # This file
│
├── config/
│   ├── prometheus.yml          # Metrics collection config
│   ├── nginx/
│   │   └── nginx.conf          # Reverse proxy config
│   └── grafana/
│       └── provisioning/       # Dashboard datasources
│
├── services/
│   ├── orchestrator/           # Central coordinator
│   │   ├── main.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   └── agents/
│       ├── ai/                 # AI/ML Agent
│       ├── data/               # Data Processing Agent
│       ├── devops/             # DevOps/Infrastructure Agent
│       ├── netmon/             # Network Monitoring Agent
│       └── security/           # Security/Secrets Agent
│
├── logs/                       # Service logs (auto-created)
├── models/                     # AI model files (auto-created)
├── shared/                     # Shared data between services
└── terraform/                  # Infrastructure as Code
```

---

# SECTION 3 — CONFIGURE ENVIRONMENT

## 3.1 Create Environment File

```bash
# Copy the example file
cp .env.example .env

# Edit with your settings
nano .env  # or use VS Code: code .env
```

## 3.2 Required Environment Variables

```bash
# Security
JWT_SECRET=your-super-secret-key-change-this

# AI Services (optional - falls back to local Ollama)
OPENAI_API_KEY=sk-your-openai-key-here
ANTHROPIC_API_KEY=sk-your-anthropic-key-here

# Storage
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# Monitoring
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=admin

# Vault (for secrets management)
VAULT_TOKEN=dev-token
```

---

# SECTION 4 — BUILD & START

## 4.1 Quick Start (Using Make)

```bash
# Setup directories
make setup

# Build all containers (first time: 10-20 minutes)
make build

# Start all services
make start
```

## 4.2 Manual Start (Without Make)

```bash
# Create required directories
mkdir -p logs models shared data

# Build containers
docker-compose build --parallel

# Start services
docker-compose up -d
```

## 4.3 Verify Everything is Running

```bash
# Check status
make status

# Or manually:
docker-compose ps

# Test health endpoints
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
curl http://localhost:8004/health
curl http://localhost:8005/health
```

---

# SECTION 5 — ACCESS SERVICES

Once running, access the platform at:

| Service | URL | Default Credentials |
|---------|-----|-------------------|
| **API/Orchestrator** | http://localhost:8000 | - |
| **API Documentation** | http://localhost:8000/docs | - |
| **Grafana** | http://localhost:3000 | admin/admin |
| **Prometheus** | http://localhost:9090 | - |
| **MinIO Console** | http://localhost:9001 | minioadmin/minioadmin |
| **Vault UI** | http://localhost:8200 | dev-token |
| **Nginx Proxy** | http://localhost:80 | - |

---

# SECTION 6 — FIRST AI MODEL SETUP

## 6.1 Download Your First Model

```bash
# Pull llama2 model into Ollama
make install-ollama-model MODEL=llama2

# Or manually:
docker-compose exec ollama ollama pull llama2
```

## 6.2 Test AI Agent

```bash
# Generate text
curl -X POST http://localhost:8001/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What is artificial intelligence?",
    "model": "llama2",
    "max_tokens": 200
  }'
```

---

# SECTION 7 — DAILY WORKFLOW

## 7.1 Start Platform

```bash
cd ai-platform
make start
```

## 7.2 View Logs

```bash
# All services
make logs

# Specific service
make logs-orchestrator
make logs-ai-agent
```

## 7.3 Stop Platform

```bash
make stop
```

## 7.4 Update Everything

```bash
make update
make restart
```

---

# SECTION 8 — TROUBLESHOOTING

## 8.1 Common Issues

### Issue: Port already in use
```bash
# Find and kill process on port 8000
lsof -ti:8000 | xargs kill -9
# Or change ports in docker-compose.yml
```

### Issue: Out of memory
```bash
# Increase Docker memory limit
# Docker Desktop → Settings → Resources → Memory (set to 8GB+)
```

### Issue: Container won't start
```bash
# Check logs
docker-compose logs [service-name]

# Rebuild specific service
docker-compose build --no-cache [service-name]
docker-compose up -d [service-name]
```

### Issue: GPU not detected
```bash
# Install nvidia-docker2
# Add to docker-compose.yml deploy section for AI agent
```

## 8.2 Reset Everything

```bash
# ⚠️ WARNING: This deletes all data!
make clean
```

---

# SECTION 9 — ADVANCED CONFIGURATION

## 9.1 Add External AI API Keys

Edit `.env`:
```bash
OPENAI_API_KEY=sk-your-key
ANTHROPIC_API_KEY=sk-your-key
```

Restart:
```bash
make restart
```

## 9.2 Configure Custom Domain

Edit `config/nginx/nginx.conf`:
```nginx
server {
    listen 80;
    server_name your-domain.com;
    # ...
}
```

## 9.3 Enable SSL/HTTPS

```bash
# Using Let's Encrypt
# Add to docker-compose.yml:
certbot:
  image: certbot/certbot
  volumes:
    - ./certbot/conf:/etc/letsencrypt
    - ./certbot/www:/var/www/certbot
```

---

# SECTION 10 — BACKUP & RECOVERY

## 10.1 Create Backup

```bash
make backup
```

Backups saved to `./backups/`:
- `postgres_YYYYMMDD_HHMMSS.sql` - Database dump
- `redis_YYYYMMDD_HHMMSS.tar.gz` - Cache data

## 10.2 Restore from Backup

```bash
# Restore database
docker-compose exec -T postgres psql -U postgres aipm < backups/postgres_YYYYMMDD_HHMMSS.sql

# Restore Redis
docker run --rm -v ai-platform_redis-data:/data -v $(PWD)/backups:/backup alpine tar xzf /backup/redis_YYYYMMDD_HHMMSS.tar.gz -C /data
```

---

# API QUICK REFERENCE

## Submit Task to Agent

```bash
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type": "ai",
    "input_data": {
      "action": "generate",
      "params": {
        "prompt": "Explain quantum computing",
        "model": "llama2"
      }
    }
  }'
```

## Check Task Status

```bash
curl http://localhost:8000/tasks/{task-id}
```

## List All Agents

```bash
curl http://localhost:8000/agents
```

## Direct Agent Execution

```bash
curl -X POST http://localhost:8000/execute/ai \
  -H "Content-Type: application/json" \
  -d '{"action": "generate", "params": {"prompt": "Hello!"}}'
```

---

# SUPPORT

- **Issues:** https://github.com/your-org/ai-platform/issues
- **Documentation:** https://docs.ai-platform.io
- **Discord:** https://discord.gg/ai-platform

---

**Happy Building!** 🚀
