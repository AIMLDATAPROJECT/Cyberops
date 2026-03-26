# AI Platform - One-Command Installer

🚀 **Deploy a complete AI-driven automation platform in minutes!**

## Quick Start

Install on any Linux/macOS server with a single command:

```bash
curl -fsSL https://raw.githubusercontent.com/AIMLDATAPROJECT/Cyberops/main/install.sh | bash
```

**That's it!** The installer will:
1. Check system requirements
2. Install Docker & Docker Compose (if needed)
3. Download the AI Platform
4. Run interactive configuration wizard
5. Start all services automatically
6. Give you access URLs

## What You Get

### 🤖 5 AI Agents
- **AI Agent** - Natural language processing & chat
- **Data Agent** - Data validation, backup, transformation
- **DevOps Agent** - CI/CD, Docker management, deployments
- **NetMon Agent** - Network discovery & monitoring
- **Security Agent** - Vulnerability scanning & auto-remediation

### 🎛️ Master Dashboard
Single control panel at `http://your-server:8080`
- Live agent status
- Plain text command interface
- Service monitoring
- Quick actions
- Logs viewer

### 🤖 7 n8n Automation Workflows
- **Master Coordinator** - Orchestrates all agents
- **Auto-Healing** - Self-repairing system
- **Security Response** - Auto-remediate threats
- **CI/CD Pipeline** - Auto-deploy with rollback
- **Monitoring Alerts** - Slack notifications
- **Network Discovery** - Auto-scan network
- **Data Pipeline** - Auto-validate & backup

### 🔧 Infrastructure Services
| Service | Port | Purpose |
|---------|------|---------|
| Dashboard | 8080 | Web UI |
| Orchestrator | 8000 | Central API |
| n8n | 5678 | Workflow automation |
| Grafana | 3000 | Monitoring |
| Prometheus | 9090 | Metrics |
| AI API | 8006 | Plain text interface |

## System Requirements

- **OS:** Linux (Ubuntu 20.04+, CentOS 8+, Debian 11+) or macOS
- **RAM:** 8GB minimum (16GB recommended)
- **CPU:** 4 cores
- **Disk:** 50GB free space
- **Network:** Internet access for Docker images

## Installation Methods

### Method 1: One-Liner (Recommended)
```bash
curl -fsSL https://raw.githubusercontent.com/AIMLDATAPROJECT/Cyberops/main/install.sh | bash
```

### Method 2: Download & Run
```bash
# Download installer
curl -O https://raw.githubusercontent.com/AIMLDATAPROJECT/Cyberops/main/install.sh
chmod +x install.sh

# Run installer
./install.sh
```

### Method 3: Manual Install
```bash
# Clone repository
git clone https://github.com/AIMLDATAPROJECT/Cyberops.git /opt/ai-platform
cd /opt/ai-platform

# Run installer
./install.sh
```

## Configuration Wizard

During installation, an interactive wizard will ask:
1. Network subnet (default: 192.168.1.0/24)
2. System count (default: 20)
3. Slack webhook URL (optional)
4. Slack channel (default: #ai-platform-alerts)
5. OpenAI API key (optional)

All other settings (passwords, tokens) are auto-generated securely.

## Management CLI

After installation, use the `aipm` command to manage the platform:

```bash
# Start/stop/restart
aipm start      # Start all services
aipm stop       # Stop all services
aipm restart    # Restart all services

# Check status
aipm status     # Show service status

# View logs
aipm logs                    # All logs
aipm logs orchestrator       # Specific service logs

# Maintenance
aipm update     # Update to latest version
aipm backup     # Create backup
aipm reset      # ⚠️ Reset all data

# Configuration
aipm wizard     # Re-run configuration wizard
```

## Access URLs

After installation, access your platform at:

| Service | URL | Default Login |
|---------|-----|---------------|
| Dashboard | http://localhost:8080 | No login |
| n8n | http://localhost:5678 | First-time setup |
| Grafana | http://localhost:3000 | admin / (from .env) |
| API Docs | http://localhost:8000/docs | - |

## Post-Installation

### 1. Import n8n Workflows
1. Open http://localhost:5678
2. Create account (first time only)
3. Workflows → Import from File
4. Import all JSON files from `workflows/n8n/`
5. Activate each workflow

### 2. Configure Slack (Optional)
1. Create webhook at https://api.slack.com/messaging/webhooks
2. Run `aipm wizard` to update configuration
3. Test alerts

### 3. First Test
Try plain text commands:
```
"ping google.com"
"discover all network devices"
"check all health"
```

## Architecture

```
┌─────────────────────────────────────────┐
│           Nginx (Port 8080)            │
│      Reverse Proxy + Dashboard         │
└──────────────┬──────────────────────────┘
               │
    ┌──────────┴──────────┐
    │                     │
┌───▼────┐         ┌──────▼──────┐
│ n8n    │         │ Plain Text  │
│ 5678   │         │ API 8006    │
└───┬────┘         └──────┬──────┘
    │                      │
    └──────────┬───────────┘
               │
        ┌──────▼──────┐
        │ Orchestrator│
        │   8000      │
        └──────┬──────┘
               │
    ┌──────────┼──────────┐
    │          │          │
┌───▼───┐ ┌───▼───┐ ┌───▼───┐
│  AI   │ │ Data  │ │DevOps │
│ 8001  │ │ 8002  │ │ 8003  │
└───────┘ └───────┘ └───────┘

┌─────────────────────────────────────────┐
│ Infrastructure: PostgreSQL, Redis,    │
│ MinIO, Vault, Prometheus, Grafana      │
└─────────────────────────────────────────┘
```

## Troubleshooting

### Port Already in Use
```bash
# Find and kill process
sudo lsof -i :8080
sudo kill -9 <PID>
```

### Service Won't Start
```bash
# Check logs
aipm logs <service-name>

# Common fix: Restart
aipm restart
```

### Out of Memory
```bash
# Add swap space
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### Reset Everything
```bash
aipm reset  # ⚠️ Deletes all data!
```

## Advanced Options

### Custom Installation Directory
```bash
export INSTALL_DIR=/custom/path
./install.sh
```

### Silent/Automated Install
```bash
# Pre-create .env file
cp .env.example .env
# Edit .env with your settings
./install.sh
```

### Update Platform
```bash
aipm update
```

## Security Considerations

1. **Change default passwords** - Run `aipm wizard` to regenerate
2. **Enable firewall** - Only expose necessary ports (8080, 5678, 3000)
3. **Use HTTPS** - Set up SSL certificates in production
4. **Regular backups** - Run `aipm backup` daily

## Support & Documentation

- **Full Documentation:** See `IMPLEMENTATION.md` and `DEPLOYMENT.md`
- **GitHub:** https://github.com/AIMLDATAPROJECT/Cyberops
- **Issues:** https://github.com/AIMLDATAPROJECT/Cyberops/issues

## License

MIT License - Free for personal and commercial use.

---

**Built with:** FastAPI, n8n, Redis, PostgreSQL, Docker, Prometheus, Grafana

**Version:** 1.0.0
