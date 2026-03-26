# AI Platform - Deployment Guide

Complete guide to deploy AI Platform on any infrastructure.

---

## 📋 Prerequisites

### System Requirements
- **OS:** Linux (Ubuntu 20.04+ / CentOS 8+ / Debian 11+) or macOS
- **RAM:** Minimum 8GB (16GB recommended for production)
- **CPU:** 4 cores minimum
- **Disk:** 50GB free space
- **Network:** Internet access for Docker images

### Required Software
```bash
# 1. Docker
sudo apt update
sudo apt install -y docker.io
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 2. Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 3. Git (optional)
sudo apt install -y git
```

### Ports Required
Make sure these ports are available:
```
8000-8006  # Agent APIs
5432       # PostgreSQL
6379       # Redis
9000       # MinIO
8200       # Vault
5678       # n8n
3000       # Grafana
9090       # Prometheus
8080       # Nginx/Dashboard
```

---

## 🚀 Installation Methods

### Method 1: Direct Download (Recommended)

```bash
# 1. Download project
cd /opt
sudo mkdir ai-platform
sudo chown $USER:$USER ai-platform
cd ai-platform

# 2. Copy all files from development machine
# Use scp, rsync, or any file transfer method
# Example:
# rsync -avz /path/to/ai-platform/ user@server:/opt/ai-platform/

# 3. Or clone if using git
git clone https://github.com/your-repo/ai-platform.git .
```

### Method 2: Fresh Setup Script

```bash
# Create setup script
cat > setup.sh << 'EOF'
#!/bin/bash
set -e

echo "🚀 AI Platform Installation"

# Create directories
mkdir -p {logs,models,data-storage,n8n_data/workflows}
mkdir -p services/{orchestrator,agents/{ai,data,devops,netmon,security},plaintext}
mkdir -p {shared,config/{nginx,prometheus},dashboard,workflows/n8n,scripts}

# Create .env file
cat > .env << 'ENVFILE'
# Database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=aipm

# Redis
REDIS_PASSWORD=

# MinIO
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# Vault
VAULT_DEV_ROOT_TOKEN_ID=root

# JWT
JWT_SECRET=your-super-secret-key-change-this

# AI
OLLAMA_HOST=http://ollama:11434
OPENAI_API_KEY=
ANTHROPIC_API_KEY=

# Network
NETWORK_SUBNET=192.168.1.0/24
SYSTEM_COUNT=20

# Automation
AUTO_HEAL=true
AUTO_SCALE=true
AUTO_REMEDIATE=true
AUTO_DEPLOY=true
AUTO_ROLLBACK=true

# Slack (optional)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
SLACK_CHANNEL=#ai-platform-alerts
ENVFILE

echo "✅ Directories created"
echo "✅ .env file created"
echo "⚠️  IMPORTANT: Edit .env and change default passwords!"
EOF

chmod +x setup.sh
./setup.sh
```

---

## ⚙️ Configuration

### 1. Edit Environment Variables

```bash
nano .env
```

**Required Changes:**
```env
# Security - CHANGE THESE!
POSTGRES_PASSWORD=your-secure-password
MINIO_SECRET_KEY=your-secure-key
JWT_SECRET=your-random-secret-key-here

# AI Providers (if using external)
OPENAI_API_KEY=sk-your-openai-key
ANTHROPIC_API_KEY=sk-your-anthropic-key

# Slack for alerts (optional but recommended)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXX
```

### 2. Network Configuration (Optional)

For specific network subnet:
```env
NETWORK_SUBNET=10.0.0.0/24
SYSTEM_COUNT=20
NET_INTERFACE=eth0
```

### 3. SSL/TLS Setup (Production)

```bash
# Create certs directory
mkdir -p certs

# Generate self-signed certs (dev only)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout certs/nginx.key \
  -out certs/nginx.crt \
  -subj "/C=US/ST=State/L=City/O=Org/CN=localhost"

# Or use Let's Encrypt for production
certbot certonly --standalone -d your-domain.com
```

---

## 🏃 Start Services

### Quick Start
```bash
# Start everything
docker compose up -d

# Verify all running
docker compose ps
```

### Step-by-Step (Recommended for First Time)

```bash
# Step 1: Start infrastructure
docker compose up -d postgres redis minio vault

# Wait 30 seconds for initialization
sleep 30

# Step 2: Start monitoring
docker compose up -d prometheus grafana

# Step 3: Start orchestrator
docker compose up -d orchestrator

# Step 4: Start all agents
docker compose up -d ai-agent data-agent devops-agent netmon-agent security-agent

# Step 5: Start supporting services
docker compose up -d plaintext-api

# Step 6: Start n8n
docker compose up -d n8n

# Step 7: Start nginx (last)
docker compose up -d nginx
```

---

## ✅ Verification

### Check Services
```bash
# All services status
docker compose ps

# Check logs for errors
docker compose logs --tail=20

# Specific service logs
docker compose logs orchestrator --tail=50
docker compose logs plaintext-api --tail=20
```

### Test APIs
```bash
# Test orchestrator
curl http://localhost:8000/health

# Test agents
curl http://localhost:8000/agents

# Test plain text API
curl -X POST http://localhost:8006/text/command \
  -H "Content-Type: application/json" \
  -d '{"command": "ping google.com"}'

# Test dashboard
curl http://localhost:8080 | head -20
```

### Expected Output
```json
// /agents
[
  {"agent_type": "ai", "status": "online"},
  {"agent_type": "data", "status": "online"},
  {"agent_type": "devops", "status": "online"},
  {"agent_type": "netmon", "status": "online"},
  {"agent_type": "security", "status": "online"}
]
```

---

## 🔧 Post-Installation Setup

### 1. Configure n8n Workflows

1. **Access n8n:**
   ```
   http://your-server-ip:5678
   ```

2. **Setup n8n:**
   - Create account (first time only)
   - Skip email setup (optional)

3. **Import Workflows:**
   - Go to **Workflows** menu
   - Click **Import from File**
   - Import these files from `workflows/n8n/`:
     - `01-master-coordinator.json`
     - `02-network-discovery.json`
     - `03-data-pipeline.json`
     - `06-auto-healing.json`
     - `07-security-response.json`
     - `08-cicd-pipeline.json`
     - `09-monitoring-alerts.json`

4. **Configure Slack Node:**
   - Open any workflow with Slack
   - Edit Slack node
   - Add your webhook URL
   - Test connection

5. **Activate Workflows:**
   - Open each workflow
   - Toggle **Active** switch
   - Workflows now run automatically!

### 2. Setup Grafana Dashboards

1. **Access Grafana:**
   ```
   http://your-server-ip:3000
   ```
   - Default login: `admin/admin`
   - Change password on first login

2. **Add Prometheus Data Source:**
   - Configuration → Data Sources → Add
   - Select Prometheus
   - URL: `http://prometheus:9090`
   - Save & Test

3. **Import Dashboards (optional):**
   - Create → Import
   - Upload dashboard JSON or use ID

### 3. Configure Backup (Production)

```bash
# Create backup script
cat > backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/backup/$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

# Backup PostgreSQL
docker exec ai-platform-postgres pg_dump -U postgres aipm > $BACKUP_DIR/database.sql

# Backup Redis (if persistence enabled)
docker cp ai-platform-redis:/data/dump.rdb $BACKUP_DIR/redis.rdb || true

# Backup n8n workflows
cp -r n8n_data $BACKUP_DIR/

# Backup shared context
cp -r shared $BACKUP_DIR/

echo "Backup complete: $BACKUP_DIR"
EOF

chmod +x backup.sh

# Add to crontab (daily backup at 2 AM)
crontab -e
# Add: 0 2 * * * /opt/ai-platform/backup.sh
```

---

## 🔒 Security Hardening

### 1. Firewall Setup

```bash
# UFW (Ubuntu)
sudo ufw allow 8080/tcp  # Dashboard
sudo ufw allow 5678/tcp  # n8n (restrict to admin IPs)
sudo ufw allow 3000/tcp  # Grafana (restrict to admin IPs)
sudo ufw enable

# Or restrict to specific IPs
sudo ufw allow from 10.0.0.0/8 to any port 5678
```

### 2. Change Default Passwords

```bash
# All passwords in .env must be changed
nano .env
# Change: POSTGRES_PASSWORD, MINIO_SECRET_KEY, JWT_SECRET, VAULT_TOKEN
```

### 3. Enable HTTPS

```bash
# Using Let's Encrypt
docker compose stop nginx

# Install certbot
sudo apt install -y certbot

# Get certificates
sudo certbot certonly --standalone \
  -d your-domain.com \
  -d www.your-domain.com

# Update nginx config to use certs
# Edit config/nginx/nginx.conf
# Change ssl_certificate paths

# Restart
docker compose start nginx
```

### 4. Vault Security

```bash
# Initialize Vault (first time)
docker exec -it ai-platform-vault vault operator init

# Store unseal keys securely!
# Unseal Vault
docker exec -it ai-platform-vault vault operator unseal

# Enable audit logging
docker exec -it ai-platform-vault vault audit enable file file_path=/vault/logs/audit.log
```

---

## 🐛 Troubleshooting

### Common Issues

#### 1. Port Already in Use
```bash
# Find what's using port 8080
sudo lsof -i :8080
# or
sudo netstat -tlnp | grep 8080

# Kill process or change port in docker-compose.yml
```

#### 2. Agent Not Starting
```bash
# Check logs
docker compose logs ai-agent --tail=50

# Restart specific agent
docker compose restart ai-agent

# Check dependencies
docker compose ps ollama redis
```

#### 3. Database Connection Failed
```bash
# Check PostgreSQL is running
docker compose ps postgres
docker compose logs postgres --tail=20

# Verify credentials in .env match
# Restart orchestrator
docker compose restart orchestrator
```

#### 4. n8n Webhook Not Working
```bash
# Check n8n URL in workflows
# Update from localhost to your server IP
# In workflow: Change webhook URL to http://your-server:5678

# Check n8n logs
docker compose logs n8n --tail=50
```

#### 5. Out of Memory
```bash
# Check memory usage
free -h
docker stats --no-stream

# Add swap if needed
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### Reset Everything
```bash
# WARNING: This deletes all data!
docker compose down -v
docker volume prune -f
docker system prune -f

# Then restart
docker compose up -d
```

---

## 📊 Production Checklist

Before going live:

- [ ] Changed all default passwords in .env
- [ ] Configured SSL/TLS certificates
- [ ] Set up firewall rules
- [ ] Configured backup scripts
- [ ] Set up monitoring alerts (Slack)
- [ ] Tested all agent capabilities
- [ ] Verified n8n workflows active
- [ ] Load tested APIs
- [ ] Documented custom configurations
- [ ] Set up log rotation
- [ ] Configured auto-updates (optional)

---

## 🔄 Updates & Maintenance

### Update Services
```bash
# Pull latest images
docker compose pull

# Restart with new images
docker compose up -d

# Check for issues
docker compose ps
docker compose logs --tail=20
```

### Update Specific Agent
```bash
# Rebuild from source
docker compose build ai-agent --no-cache
docker compose up -d ai-agent
```

### Check for Updates
```bash
# View current versions
docker compose images

# Check for newer images
docker compose pull --dry-run
```

---

## 🌐 Multi-Server Deployment

For production scale across multiple servers:

```bash
# Server 1: Core Services
docker compose -f docker-compose.core.yml up -d

# Server 2: Agents only
docker compose -f docker-compose.agents.yml up -d

# Server 3: Monitoring only  
docker compose -f docker-compose.monitoring.yml up -d

# See examples in docker-compose.*.yml files
```

---

## 📞 Support

### Getting Help
1. Check logs: `docker compose logs <service>`
2. Review documentation: `IMPLEMENTATION.md`
3. Test APIs directly: `curl http://localhost:8000/docs`
4. Check n8n executions: `http://localhost:5678/executions`

### Useful Commands
```bash
# View all logs
docker compose logs -f

# Restart all
docker compose restart

# Scale specific service
docker compose up -d --scale ai-agent=3

# Check resource usage
docker stats

# Clean up
docker system prune -a
```

---

**Version:** 1.0  
**Last Updated:** March 2026  
**Support:** See IMPLEMENTATION.md for architecture details
