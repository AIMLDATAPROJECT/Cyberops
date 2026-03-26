#!/bin/bash
#
# AI Platform - Complete Uninstaller
# Safely removes all AI Platform components from the system
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

INSTALL_DIR="${INSTALL_DIR:-/opt/ai-platform}"
BACKUP_DIR="/opt/ai-platform-backup-$(date +%Y%m%d-%H%M%S)"

log() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1"; }
cyber() { echo -e "${MAGENTA}[◈]${NC} $1"; }

# Show cyberpunk banner
show_banner() {
    echo -e "${RED}"
    cat << 'EOF'
    
    ▄████▄   ██▓ ██▓  ▄▄▄█████▓ ██▓ ▒█████   ███▄    █ 
   ▒██▀ ▀█  ▓██▒▓██▒  ▓  ██▒ ▓▒▓██▒▒██▒  ██▒ ██ ▀█   █ 
   ▒▓█    ▄ ▒██▒▒██░  ▒ ▓██░ ▒░▒██▒▒██░  ██▒▓██  ▀█ ██▒
   ▒▓▓▄ ▄██▒░██░▒██░  ░ ▓██▓ ░ ░██░▒██   ██░▓██▒  ▐▌██▒
   ▒ ▓███▀ ░░██░░██████▒▒██▒ ░ ░██░░ ████▓▒░▒██░   ▓██░
   ░ ░▒ ▒  ░░▓  ░ ▒░▓  ░▒ ░░   ░▓  ░ ▒░▒░▒░ ░ ▒░   ▒ ▒ 
     ░  ▒    ▒ ░░ ░ ▒  ░  ░     ▒ ░  ░ ▒ ▒░ ░ ░░   ░ ▒░
   ░         ▒ ░  ░ ░   ░       ▒ ░░ ░ ░ ▒     ░   ░ ░ 
   ░ ░       ░      ░  ░        ░      ░ ░           ░ 
   ░                                                   

EOF
    echo -e "${NC}"
    echo -e "${RED}╔════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║         ⚠️  AI PLATFORM COMPLETE UNINSTALLER ⚠️                            ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════════════════════════════════════╝${NC}"
    echo
}

# Confirmation
confirm_uninstall() {
    echo
    warn "This will COMPLETELY REMOVE the AI Platform from your system!"
    warn "Including: All containers, data, images, and configuration."
    echo
    
    # Show what will be removed
    echo -e "${YELLOW}The following will be removed:${NC}"
    echo "  • All running containers"
    echo "  • All Docker images (ai-platform-*)"
    echo "  • All Docker volumes"
    echo "  • Installation directory: $INSTALL_DIR"
    echo "  • CLI tool: /usr/local/bin/aipm"
    echo "  • Systemd service (if exists)"
    echo
    
    echo -en "${RED}Type 'UNINSTALL' to proceed: ${NC}"
    read -r confirmation
    
    if [[ "$confirmation" != "UNINSTALL" ]]; then
        error "Uninstall cancelled."
        exit 1
    fi
}

# Create backup option
offer_backup() {
    echo
    log "Would you like to backup your data before uninstalling?"
    echo -en "${CYAN}Create backup? [Y/n]: ${NC}"
    read -r backup_choice
    
    if [[ ! "$backup_choice" =~ ^[Nn]$ ]]; then
        log "Creating backup at $BACKUP_DIR..."
        
        if [ -d "$INSTALL_DIR" ]; then
            sudo mkdir -p "$BACKUP_DIR"
            
            # Backup .env
            if [ -f "$INSTALL_DIR/.env" ]; then
                sudo cp "$INSTALL_DIR/.env" "$BACKUP_DIR/"
            fi
            
            # Backup .credentials
            if [ -f "$INSTALL_DIR/.credentials" ]; then
                sudo cp "$INSTALL_DIR/.credentials" "$BACKUP_DIR/"
            fi
            
            # Backup PostgreSQL data if possible
            if docker ps -q -f name=ai-platform-postgres | grep -q .; then
                log "Backing up PostgreSQL database..."
                sudo docker exec ai-platform-postgres pg_dumpall -U postgres > "$BACKUP_DIR/postgres-backup.sql" 2>/dev/null || warn "PostgreSQL backup failed"
            fi
            
            # Backup Redis
            if docker ps -q -f name=ai-platform-redis | grep -q .; then
                log "Backing up Redis data..."
                sudo docker exec ai-platform-redis redis-cli SAVE > /dev/null 2>&1 || true
                sudo docker cp ai-platform-redis:/data/dump.rdb "$BACKUP_DIR/" 2>/dev/null || warn "Redis backup failed"
            fi
            
            # Backup n8n workflows
            if [ -d "$INSTALL_DIR/workflows" ]; then
                sudo cp -r "$INSTALL_DIR/workflows" "$BACKUP_DIR/" 2>/dev/null || true
            fi
            
            sudo chown -R $USER:$USER "$BACKUP_DIR"
            success "Backup created at: $BACKUP_DIR"
        fi
    fi
}

# Stop all services
stop_services() {
    echo
    cyber "Stopping all AI Platform services..."
    
    if [ -f "$INSTALL_DIR/docker-compose.yml" ]; then
        cd "$INSTALL_DIR"
        
        # Stop gracefully first
        sudo docker compose down --timeout 30 2>/dev/null || true
        
        # Force stop any remaining containers
        local containers=$(sudo docker ps -q -f name=ai-platform 2>/dev/null)
        if [ -n "$containers" ]; then
            log "Force stopping remaining containers..."
            sudo docker stop $containers 2>/dev/null || true
            sudo docker rm -f $containers 2>/dev/null || true
        fi
        
        success "All services stopped"
    fi
}

# Remove volumes
remove_volumes() {
    echo
    cyber "Removing Docker volumes..."
    
    local volumes=$(sudo docker volume ls -q -f name=ai-platform 2>/dev/null)
    if [ -n "$volumes" ]; then
        sudo docker volume rm -f $volumes 2>/dev/null || true
        success "Volumes removed"
    else
        log "No volumes to remove"
    fi
    
    # Also remove any orphaned volumes
    sudo docker volume prune -f 2>/dev/null || true
}

# Remove images
remove_images() {
    echo
    cyber "Removing Docker images..."
    
    # Remove ai-platform images
    local images=$(sudo docker images -q ai-platform-* 2>/dev/null)
    if [ -n "$images" ]; then
        sudo docker rmi -f $images 2>/dev/null || true
        success "AI Platform images removed"
    fi
    
    # Remove other project images
    local other_images=$(sudo docker images --format "{{.Repository}}:{{.Tag}}" | grep -E "(ollama|n8n|grafana|prometheus|postgres|redis|minio|vault|nginx)" | grep -v "<none>" 2>/dev/null)
    if [ -n "$other_images" ]; then
        echo
        log "Found infrastructure images. Remove them too?"
        echo -en "${CYAN}Remove infrastructure images? [y/N]: ${NC}"
        read -r remove_infra
        
        if [[ "$remove_infra" =~ ^[Yy]$ ]]; then
            for img in $other_images; do
                sudo docker rmi -f "$img" 2>/dev/null || warn "Failed to remove $img"
            done
            success "Infrastructure images removed"
        fi
    fi
}

# Remove networks
remove_networks() {
    echo
    cyber "Removing Docker networks..."
    
    local networks=$(sudo docker network ls -q -f name=ai-platform 2>/dev/null)
    if [ -n "$networks" ]; then
        sudo docker network rm $networks 2>/dev/null || true
        success "Networks removed"
    fi
}

# Remove installation directory
remove_installation() {
    echo
    cyber "Removing installation directory..."
    
    if [ -d "$INSTALL_DIR" ]; then
        sudo rm -rf "$INSTALL_DIR"
        success "Removed: $INSTALL_DIR"
    else
        log "Installation directory not found"
    fi
}

# Remove CLI tool
remove_cli() {
    echo
    cyber "Removing CLI tool..."
    
    if [ -f "/usr/local/bin/aipm" ]; then
        sudo rm -f "/usr/local/bin/aipm"
        success "Removed: /usr/local/bin/aipm"
    fi
    
    # Also remove any aliases
    if [ -f "$HOME/.bashrc" ]; then
        sed -i '/ai-platform/d' "$HOME/.bashrc" 2>/dev/null || true
    fi
    if [ -f "$HOME/.zshrc" ]; then
        sed -i '/ai-platform/d' "$HOME/.zshrc" 2>/dev/null || true
    fi
}

# Remove systemd service if exists
remove_systemd() {
    echo
    cyber "Checking for systemd service..."
    
    if [ -f "/etc/systemd/system/ai-platform.service" ]; then
        sudo systemctl stop ai-platform 2>/dev/null || true
        sudo systemctl disable ai-platform 2>/dev/null || true
        sudo rm -f "/etc/systemd/system/ai-platform.service"
        sudo systemctl daemon-reload
        success "Removed systemd service"
    fi
}

# Clean up Docker system
cleanup_docker() {
    echo
    log "Running Docker system cleanup..."
    
    sudo docker system prune -f --volumes 2>/dev/null || true
    success "Docker cleanup complete"
}

# Optional: Remove Docker
offer_remove_docker() {
    echo
    log "Docker is still installed on this system."
    echo -en "${CYAN}Remove Docker completely? [y/N]: ${NC}"
    read -r remove_docker
    
    if [[ "$remove_docker" =~ ^[Yy]$ ]]; then
        log "Removing Docker..."
        
        if command -v apt-get &> /dev/null; then
            sudo apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true
            sudo apt-get purge -y docker-ce docker-ce-cli containerd.io 2>/dev/null || true
            sudo apt-get autoremove -y 2>/dev/null || true
        elif command -v yum &> /dev/null; then
            sudo yum remove -y docker docker-client docker-client-latest docker-common docker-latest docker-latest-logrotate docker-logrotate docker-engine 2>/dev/null || true
        fi
        
        # Remove Docker data
        sudo rm -rf /var/lib/docker
        sudo rm -rf /etc/docker
        
        success "Docker removed"
    fi
}

# Summary
show_summary() {
    echo
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║              ✅ AI PLATFORM UNINSTALLATION COMPLETE ✅                     ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════════════════════╝${NC}"
    echo
    
    if [ -d "$BACKUP_DIR" ]; then
        log "Backup saved at: $BACKUP_DIR"
        echo "  To restore: sudo cp -r $BACKUP_DIR/* $INSTALL_DIR/"
    fi
    
    echo
    log "Removed components:"
    echo "  ✓ All containers stopped and removed"
    echo "  ✓ All volumes removed"
    echo "  ✓ Installation directory deleted"
    echo "  ✓ CLI tool removed"
    echo "  ✓ System cleaned up"
    echo
    
    warn "Note: If you want to reinstall, run:"
    echo "  curl -fsSL https://raw.githubusercontent.com/AIMLDATAPROJECT/Cyberops/main/install-complete.sh | bash"
    echo
}

# Main uninstallation
main() {
    show_banner
    
    # Check if installed
    if [ ! -d "$INSTALL_DIR" ] && [ ! -f "/usr/local/bin/aipm" ]; then
        warn "AI Platform doesn't appear to be installed."
        echo "Nothing to uninstall."
        exit 0
    fi
    
    # Steps
    confirm_uninstall
    offer_backup
    stop_services
    remove_volumes
    remove_images
    remove_networks
    remove_systemd
    remove_cli
    remove_installation
    cleanup_docker
    offer_remove_docker
    show_summary
}

# Handle arguments
case "${1:-}" in
    --help|-h)
        echo "AI Platform Complete Uninstaller"
        echo ""
        echo "Usage: ./uninstall.sh [options]"
        echo ""
        echo "Options:"
        echo "  --help    Show this help"
        echo "  --yes     Skip confirmation (DANGEROUS)"
        echo ""
        echo "Environment Variables:"
        echo "  INSTALL_DIR    Installation directory (default: /opt/ai-platform)"
        exit 0
        ;;
    --yes)
        # Skip confirmation for automation
        confirm_uninstall() { :; }
        main
        ;;
    *)
        main
        ;;
esac
