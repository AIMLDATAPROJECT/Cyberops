#!/bin/bash
#
# AI Platform - Complete Automated Installer
# One command = Full deployment with auto-configuration
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

INSTALL_DIR="${INSTALL_DIR:-/opt/ai-platform}"
GITHUB_REPO="https://github.com/AIMLDATAPROJECT/Cyberops"

log() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1"; }

# Auto-detect public IP
get_public_ip() {
    # Try multiple methods to get public IP
    local ip
    ip=$(curl -s ifconfig.me 2>/dev/null || \
         curl -s icanhazip.com 2>/dev/null || \
         curl -s api.ipify.org 2>/dev/null || \
         hostname -I | awk '{print $1}')
    echo "$ip"
}

# Wait for service to be healthy
wait_for_service() {
    local service=$1
    local port=$2
    local max_attempts=${3:-30}
    
    log "Waiting for $service on port $port..."
    
    for i in $(seq 1 $max_attempts); do
        if curl -s "http://localhost:$port/health" > /dev/null 2>&1 || \
           curl -s "http://localhost:$port" > /dev/null 2>&1; then
            success "$service is ready!"
            return 0
        fi
        echo -n "."
        sleep 2
    done
    
    error "$service failed to start after $max_attempts attempts"
    return 1
}

# Update dashboard with public IP
update_dashboard_ip() {
    local public_ip=$1
    
    log "Configuring dashboard for IP: $public_ip"
    
    # Replace localhost with actual IP in dashboard
    if [ -f "$INSTALL_DIR/dashboard/index.html" ]; then
        sed -i "s/localhost/$public_ip/g" "$INSTALL_DIR/dashboard/index.html"
        success "Dashboard URLs updated to $public_ip"
    fi
}

# Install Docker if missing
install_docker() {
    if command -v docker &> /dev/null; then
        success "Docker already installed"
        return 0
    fi
    
    log "Installing Docker..."
    curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
    sudo sh /tmp/get-docker.sh
    sudo usermod -aG docker $USER 2>/dev/null || true
    rm -f /tmp/get-docker.sh
    success "Docker installed"
}

# Download platform
download_platform() {
    if [ -d "$INSTALL_DIR/.git" ]; then
        log "Updating existing installation..."
        cd "$INSTALL_DIR"
        sudo git pull origin main
    elif [ -d "$INSTALL_DIR" ]; then
        warn "Directory exists but not a git repo"
        read -p "Remove and reinstall? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            sudo rm -rf "$INSTALL_DIR"
            sudo git clone --depth 1 "$GITHUB_REPO.git" "$INSTALL_DIR"
        fi
    else
        log "Downloading AI Platform..."
        sudo git clone --depth 1 "$GITHUB_REPO.git" "$INSTALL_DIR"
    fi
    
    sudo chown -R $USER:$USER "$INSTALL_DIR"
    cd "$INSTALL_DIR"
}

# Create environment file
create_env() {
    log "Creating environment configuration..."
    
    if [ -f .env ]; then
        warn ".env already exists, backing up to .env.backup"
        cp .env .env.backup.$(date +%s)
    fi
    
    # Generate secure passwords
    local pg_pass=$(openssl rand -base64 32 2>/dev/null | tr -d '/+=' | cut -c1-25)
    local redis_pass=$(openssl rand -base64 16 2>/dev/null | tr -d '/+=' | cut -c1-20)
    local minio_pass=$(openssl rand -base64 32 2>/dev/null | tr -d '/+=' | cut -c1-25)
    local jwt_secret=$(openssl rand -base64 48 2>/dev/null | tr -d '/+=' | cut -c1-40)
    local grafana_pass=$(openssl rand -base64 16 2>/dev/null | tr -d '/+=' | cut -c1-15)
    
    cat > .env << EOF
# AI Platform Configuration
# Auto-generated on $(date)

POSTGRES_USER=postgres
POSTGRES_PASSWORD=$pg_pass
POSTGRES_DB=aipm

REDIS_PASSWORD=$redis_pass

MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=$minio_pass

VAULT_DEV_ROOT_TOKEN_ID=$jwt_secret
JWT_SECRET=$jwt_secret

NETWORK_SUBNET=192.168.1.0/24
SYSTEM_COUNT=20

OLLAMA_HOST=http://ollama:11434

AUTO_HEAL=true
AUTO_SCALE=true
AUTO_REMEDIATE=true
AUTO_DEPLOY=true
AUTO_ROLLBACK=true

GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=$grafana_pass
EOF
    
    success "Environment file created"
    echo "Grafana Password: $grafana_pass" > .credentials
    chmod 600 .credentials
}

# Start infrastructure first
start_infrastructure() {
    log "Starting infrastructure services..."
    
    # Start DB, Redis, MinIO, Vault
    docker compose up -d postgres redis minio vault
    
    # Wait for PostgreSQL
    log "Waiting for PostgreSQL..."
    for i in {1..30}; do
        if docker exec ai-platform-postgres pg_isready -U postgres > /dev/null 2>&1; then
            success "PostgreSQL is ready"
            break
        fi
        echo -n "."
        sleep 2
    done
    
    # Wait for Redis
    log "Waiting for Redis..."
    for i in {1..30}; do
        if docker exec ai-platform-redis redis-cli ping > /dev/null 2>&1; then
            success "Redis is ready"
            break
        fi
        echo -n "."
        sleep 1
    done
    
    sleep 5
}

# Start monitoring
start_monitoring() {
    log "Starting monitoring stack..."
    docker compose up -d prometheus grafana
    sleep 5
}

# Start core services
start_core() {
    log "Starting core services..."
    
    # Start orchestrator and ollama
    docker compose up -d orchestrator ollama
    
    # Wait for orchestrator
    wait_for_service "orchestrator" "8000"
    
    sleep 5
}

# Start agents
start_agents() {
    log "Starting AI agents..."
    
    # Start all agents
    docker compose up -d ai-agent data-agent devops-agent netmon-agent security-agent plaintext-api
    
    # Wait for each agent
    for agent in ai-agent data-agent devops-agent netmon-agent security-agent; do
        local port
        case $agent in
            ai-agent) port=8001 ;;
            data-agent) port=8002 ;;
            devops-agent) port=8003 ;;
            netmon-agent) port=8004 ;;
            security-agent) port=8005 ;;
        esac
        
        # Quick check - don't fail if not ready
        for i in {1..10}; do
            if curl -s "http://localhost:$port/health" > /dev/null 2>&1; then
                success "$agent is ready"
                break
            fi
            sleep 2
        done
    done
    
    # Start plaintext API
    docker compose up -d plaintext-api
    sleep 3
}

# Start n8n
start_n8n() {
    log "Starting n8n automation..."
    docker compose up -d n8n
    
    # Wait for n8n
    for i in {1..30}; do
        if curl -s "http://localhost:5678" > /dev/null 2>&1; then
            success "n8n is ready"
            break
        fi
        echo -n "."
        sleep 2
    done
}

# Start nginx (must be last)
start_nginx() {
    log "Starting web server..."
    
    # Make sure n8n is running before nginx (nginx depends on it)
    docker compose up -d n8n
    sleep 5
    
    # Start nginx
    docker compose up -d nginx
    
    # Verify nginx
    for i in {1..10}; do
        if curl -s "http://localhost:8080" > /dev/null 2>&1; then
            success "Nginx is ready"
            return 0
        fi
        sleep 2
    done
    
    warn "Nginx may have issues, checking logs..."
    docker logs ai-platform-nginx --tail=20
}

# Install CLI tool
install_cli() {
    log "Installing aipm CLI..."
    
    sudo tee /usr/local/bin/aipm > /dev/null << 'EOF'
#!/bin/bash
INSTALL_DIR="${INSTALL_DIR:-/opt/ai-platform}"
cd "$INSTALL_DIR" || exit 1

case "$1" in
    start) docker compose up -d && echo "✅ AI Platform started" ;;
    stop) docker compose down && echo "✅ AI Platform stopped" ;;
    restart) docker compose restart && echo "✅ AI Platform restarted" ;;
    status) docker compose ps ;;
    logs) docker compose logs --tail=100 -f "${2:-}" ;;
    update) docker compose pull && docker compose up -d && echo "✅ Updated" ;;
    *) echo "Usage: aipm {start|stop|restart|status|logs|update}" ;;
esac
EOF
    
    sudo chmod +x /usr/local/bin/aipm
    success "CLI installed: aipm"
}

# Final status
show_final_status() {
    local public_ip=$1
    
    echo
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║         🎉 AI PLATFORM DEPLOYMENT COMPLETE! 🎉              ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo
    echo "🌐 Access URLs:"
    echo "   Dashboard:   http://$public_ip:8080"
    echo "   n8n:         http://$public_ip:5678"
    echo "   Grafana:     http://$public_ip:3000"
    echo "   API Docs:    http://$public_ip:8000/docs"
    echo
    echo "📋 Credentials saved in: $INSTALL_DIR/.credentials"
    echo
    echo "🚀 Quick Commands:"
    echo "   aipm status   - Check services"
    echo "   aipm logs     - View logs"
    echo "   aipm stop     - Stop platform"
    echo "   aipm start    - Start platform"
    echo
    echo "📁 Installation: $INSTALL_DIR"
    echo
}

# Main installation
main() {
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║          AI PLATFORM - AUTOMATED INSTALLER v2.0            ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo
    
    # Step 1: Pre-flight checks
    log "Detecting public IP..."
    PUBLIC_IP=$(get_public_ip)
    success "Public IP: $PUBLIC_IP"
    
    # Step 2: Install Docker
    install_docker
    
    # Step 3: Download platform
    download_platform
    
    # Step 4: Create environment
    create_env
    
    # Step 5: Update dashboard with public IP
    update_dashboard_ip "$PUBLIC_IP"
    
    # Step 6: Start services in order
    start_infrastructure
    start_monitoring
    start_core
    start_agents
    start_n8n
    start_nginx
    
    # Step 7: Install CLI
    install_cli
    
    # Step 8: Verify
    log "Verifying installation..."
    docker compose ps
    
    # Final status
    show_final_status "$PUBLIC_IP"
}

# Run
main "$@"
