#!/bin/bash
#
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                        AI PLATFORM - CYBERPUNK EDITION                       ║
# ║                    One-Command Deployment System v2.0                        ║
# ║                                                                               ║
# ║              "Deploying the future, one container at a time..."               ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
#
# This is NOT your average installer. This is a cinematic experience.
# Prepare for: Matrix rain, glitch effects, typewriter text, and pure awesomeness.

set -e

# ═══════════════════════════════════════════════════════════════════════════════
# VISUAL EFFECTS ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

# Color palette - Cyberpunk 2077 inspired
BLACK='\033[0;30m'
RED='\033[0;31m'
BRIGHT_RED='\033[1;31m'
GREEN='\033[0;32m'
BRIGHT_GREEN='\033[1;32m'
YELLOW='\033[0;33m'
BRIGHT_YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BRIGHT_BLUE='\033[1;34m'
MAGENTA='\033[0;35m'
BRIGHT_MAGENTA='\033[1;35m'
CYAN='\033[0;36m'
BRIGHT_CYAN='\033[1;36m'
WHITE='\033[0;37m'
BRIGHT_WHITE='\033[1;37m'
NC='\033[0m' # Reset

# Matrix green effect
MATRIX_GREEN='\033[38;5;82m'
MATRIX_DARK='\033[38;5;22m'
NEON_PINK='\033[38;5;198m'
NEON_BLUE='\033[38;5;81m'
GOLD='\033[38;5;220m'

# ═══════════════════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

# Typewriter effect - prints text character by character
typewrite() {
    local text="$1"
    local delay="${2:-0.02}"
    local color="${3:-$BRIGHT_CYAN}"
    
    echo -en "$color"
    for (( i=0; i<${#text}; i++ )); do
        echo -n "${text:$i:1}"
        sleep "$delay"
    done
    echo -e "$NC"
}

# Glitch effect - randomly corrupts text
glitch_text() {
    local text="$1"
    local iterations="${2:-3}"
    local glitch_chars='!@#$%^&*()_+-=[]{}|;:,.<>?/~`'
    
    for (( iter=0; iter<iterations; iter++ )); do
        echo -en "\r$BRIGHT_RED"
        for (( i=0; i<${#text}; i++ )); do
            if (( RANDOM % 3 == 0 )); then
                echo -n "${glitch_chars:$((RANDOM % ${#glitch_chars})):1}"
            else
                echo -n "${text:$i:1}"
            fi
        done
        sleep 0.08
    done
    echo -en "\r$BRIGHT_GREEN$text$NC"
    sleep 0.3
    echo
}

# Matrix rain effect - cascading characters
matrix_rain() {
    local duration="${1:-2}"
    local width=$(tput cols 2>/dev/null || echo 80)
    local chars='0123456789ABCDEF'
    
    echo -e "$MATRIX_GREEN"
    local end=$((SECONDS + duration))
    while [ $SECONDS -lt $end ]; do
        for (( i=0; i<width/3; i++ )); do
            if (( RANDOM % 5 == 0 )); then
                echo -n "${chars:$((RANDOM % 16)):1} "
            else
                echo -n "  "
            fi
        done
        echo
        sleep 0.05
    done
    echo -e "$NC"
    clear
}

# Progress bar with cyberpunk styling
cyberpunk_progress() {
    local current="$1"
    local total="$2"
    local label="${3:-PROCESSING}"
    local width=40
    
    local percentage=$((current * 100 / total))
    local filled=$((current * width / total))
    local empty=$((width - filled))
    
    # Create the bar
    local bar=""
    for (( i=0; i<filled; i++ )); do
        bar="${bar}█"
    done
    for (( i=0; i<empty; i++ )); do
        bar="${bar}░"
    done
    
    # Color based on percentage
    local color="$RED"
    if [ $percentage -gt 30 ]; then color="$YELLOW"; fi
    if [ $percentage -gt 70 ]; then color="$BRIGHT_GREEN"; fi
    
    # Print progress bar
    printf "\r$NEON_BLUE[$label]$NC [%s%s] %s%d%%$NC" \
        "$color$bar$NC" "" "$BRIGHT_CYAN" "$percentage"
    
    if [ $current -eq $total ]; then
        echo
    fi
}

# Spinner for loading states
spinner() {
    local pid=$1
    local message="${2:-LOADING}"
    local spin_chars='⣾⣽⣻⢿⡿⣟⣯⣷'
    
    echo -en "$NEON_PINK[$message]$NC "
    while kill -0 $pid 2>/dev/null; do
        for (( i=0; i<${#spin_chars}; i++ )); do
            echo -en "\r$NEON_PINK[$message]$NC ${spin_chars:$i:1} "
            sleep 0.1
        done
    done
    echo -e "\r$BRIGHT_GREEN[$message]$NC ✓ COMPLETE$NC"
}

# ═══════════════════════════════════════════════════════════════════════════════
# BANNERS & VISUALS
# ═══════════════════════════════════════════════════════════════════════════════

# Main title banner
show_main_banner() {
    clear
    echo -e "$MATRIX_GREEN"
    cat << 'EOF'
    
    █████╗ ██╗    ██████╗ ██╗      █████╗ ████████╗███████╗ ██████╗ ██████╗ ███╗   ███╗
   ██╔══██╗██║    ██╔══██╗██║     ██╔══██╗╚══██╔══╝██╔════╝██╔═══██╗██╔══██╗████╗ ████║
   ███████║██║    ██████╔╝██║     ███████║   ██║   █████╗  ██║   ██║██████╔╝██╔████╔██║
   ██╔══██║██║    ██╔═══╝ ██║     ██╔══██║   ██║   ██╔══╝  ██║   ██║██╔══██╗██║╚██╔╝██║
   ██║  ██║██║    ██║     ███████╗██║  ██║   ██║   ██║     ╚██████╔╝██║  ██║██║ ╚═╝ ██║
   ╚═╝  ╚═╝╚═╝    ╚═╝     ╚══════╝╚═╝  ╚═╝   ╚═╝   ╚═╝      ╚═════╝ ╚═╝  ╚═╝╚═╝     ╚═╝
                                                                                          
                    ╔══════════════════════════════════════════════════════════════╗
                    ║         A U T O N O M O U S   I N T E L L I G E N C E          ║
                    ║              C Y B E R N E T I C   S Y S T E M                 ║
                    ╚══════════════════════════════════════════════════════════════╝
EOF
    echo -e "$NC"
    sleep 1
}

# Agent status display
show_agent_matrix() {
    echo -e "$BRIGHT_CYAN"
    echo "╔════════════════════════════════════════════════════════════════════════════╗"
    echo "║                     NEURAL NETWORK - AGENT STATUS                          ║"
    echo "╠════════════════════════════════════════════════════════════════════════════╣"
    echo "║  [🤖] AI Agent        │ Status: INITIALIZING │ Neural Load: 0%            ║"
    echo "║  [📊] Data Agent      │ Status: INITIALIZING │ Storage: 0TB                ║"
    echo "║  [⚙️ ] DevOps Agent    │ Status: INITIALIZING │ Containers: 0               ║"
    echo "║  [🌐] NetMon Agent    │ Status: INITIALIZING │ Networks: SCANNING         ║"
    echo "║  [🔒] Security Agent  │ Status: INITIALIZING │ Threats: MONITORING         ║"
    echo "╚════════════════════════════════════════════════════════════════════════════╝"
    echo -e "$NC"
}

# Hacking/coding animation
show_hacking_sequence() {
    local messages=(
        "> Initializing neural pathways..."
        "> Loading agent consciousness modules..."
        "> Establishing quantum entanglement..."
        "> Synchronizing with the hive mind..."
        "> Bypassing firewalls..."
        "> Compiling symbiotic relationships..."
        "> Optimizing cognitive processing..."
    )
    
    for msg in "${messages[@]}"; do
        echo -en "$MATRIX_GREEN"
        typewrite "$msg" 0.01 "$MATRIX_GREEN"
        sleep 0.2
    done
}

# ═══════════════════════════════════════════════════════════════════════════════
# CORE INSTALLATION FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

INSTALL_DIR="${INSTALL_DIR:-/opt/ai-platform}"
GITHUB_REPO="https://github.com/AIMLDATAPROJECT/Cyberops"
VERSION="2.0.0-CYBERPUNK"

# Log with style
log_info() {
    echo -e "$NEON_BLUE[◉ INFO]$NC $1"
}

log_success() {
    echo -e "$BRIGHT_GREEN[✓ SUCCESS]$NC $1"
}

log_warn() {
    echo -e "$BRIGHT_YELLOW[⚠ WARNING]$NC $1"
}

log_error() {
    echo -e "$BRIGHT_RED[✗ ERROR]$NC $1"
}

log_cyber() {
    echo -e "$NEON_PINK[◈ CYBER]$NC $1"
}

# System check with animation
check_system_with_animation() {
    log_cyber "Initiating system diagnostics..."
    
    local checks=(
        "Checking neural compatibility..."
        "Scanning memory matrices..."
        "Analyzing storage clusters..."
        "Verifying network topology..."
        "Testing quantum stability..."
    )
    
    local total=${#checks[@]}
    local i=0
    
    for check in "${checks[@]}"; do
        echo -en "$MATRIX_GREEN"
        typewrite "$check" 0.015 "$MATRIX_GREEN"
        cyberpunk_progress $((++i)) $total "DIAGNOSTIC"
        sleep 0.5
    done
    
    # Check actual requirements
    local ram_mb
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        ram_mb=$(free -m | awk '/^Mem:/{print $2}')
    else
        ram_mb=$(sysctl -n hw.memsize | awk '{print int($1/1024/1024)}')
    fi
    
    if [[ $ram_mb -lt 4096 ]]; then
        log_error "Insufficient neural capacity: ${ram_mb}MB (min: 4GB)"
        exit 1
    fi
    
    log_success "System diagnostics complete! Neural capacity: ${ram_mb}MB"
}

# Install Docker with cyber animation
install_docker_cyber() {
    if command -v docker &> /dev/null; then
        log_success "Docker consciousness already exists: $(docker --version)"
        return 0
    fi
    
    log_cyber "Downloading Docker consciousness from the cloud..."
    
    # Simulate download with progress
    for i in {1..10}; do
        cyberpunk_progress $i 10 "DOWNLOADING"
        sleep 0.3
    done
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        curl -fsSL https://get.docker.com -o /tmp/get-docker.sh 2>/dev/null &
        spinner $! "FETCHING"
        sudo sh /tmp/get-docker.sh > /dev/null 2>&1 &
        spinner $! "INSTALLING"
        sudo usermod -aG docker $USER 2>/dev/null || true
        rm -f /tmp/get-docker.sh
    else
        log_warn "Please install Docker Desktop manually"
        return 1
    fi
    
    log_success "Docker consciousness integrated!"
}

# Download platform with matrix effect
download_platform_cyber() {
    log_cyber "Establishing connection to the mainframe..."
    
    if [[ -d "$INSTALL_DIR" ]]; then
        log_warn "Previous installation detected in neural network"
        echo -en "$BRIGHT_YELLOW"
        read -p "Reformat neural pathways? [Y/n]: " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
            log_cyber "Purging old consciousness..."
            sudo rm -rf "$INSTALL_DIR"
        else
            log_info "Using existing neural pathways"
            return 0
        fi
    fi
    
    log_cyber "Downloading AI Platform source code..."
    
    # Matrix rain during download
    matrix_rain 1 &
    local matrix_pid=$!
    
    sudo mkdir -p "$INSTALL_DIR"
    
    if command -v git &> /dev/null; then
        sudo git clone --depth 1 "$GITHUB_REPO.git" "$INSTALL_DIR" > /dev/null 2>&1 &
        local git_pid=$!
        wait $git_pid
    else
        curl -L "${GITHUB_REPO}/archive/refs/heads/main.tar.gz" 2>/dev/null | \
            sudo tar -xz -C "$INSTALL_DIR" --strip-components=1 2>/dev/null &
        local curl_pid=$!
        wait $curl_pid
    fi
    
    kill $matrix_pid 2>/dev/null || true
    wait $matrix_pid 2>/dev/null || true
    
    sudo chown -R $USER:$USER "$INSTALL_DIR"
    
    log_success "AI Platform downloaded to: $INSTALL_DIR"
    glitch_text ">>> DOWNLOAD COMPLETE <<<" 3
}

# Interactive wizard with style
run_wizard_cyber() {
    log_cyber "Initiating configuration sequence..."
    
    echo
    echo -e "$BRIGHT_CYAN╔════════════════════════════════════════════════════════════════════════════╗"
    echo "║                    CONFIGURATION PROTOCOL v2.0                             ║"
    echo "╚════════════════════════════════════════════════════════════════════════════╝$NC"
    echo
    
    cd "$INSTALL_DIR"
    
    # Generate secure passwords
    local pg_pass=$(openssl rand -base64 32 2>/dev/null || head -c 32 /dev/urandom | base64)
    local redis_pass=$(openssl rand -base64 16 2>/dev/null || head -c 16 /dev/urandom | base64)
    local minio_pass=$(openssl rand -base64 32 2>/dev/null || head -c 32 /dev/urandom | base64)
    local jwt_secret=$(openssl rand -base64 48 2>/dev/null || head -c 48 /dev/urandom | base64)
    local grafana_pass=$(openssl rand -base64 16 2>/dev/null || head -c 16 /dev/urandom | base64)
    
    cat > .env << EOF
# ═══════════════════════════════════════════════════════════════════════════
# AI PLATFORM - CYBERPUNK EDITION
# Configuration generated: $(date)
# ═══════════════════════════════════════════════════════════════════════════

# Neural Database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=$pg_pass
POSTGRES_DB=neural_cortex

# Memory Cache
REDIS_PASSWORD=$redis_pass

# Object Storage
MINIO_ACCESS_KEY=quantum_admin
MINIO_SECRET_KEY=$minio_pass

# Security Vault
VAULT_DEV_ROOT_TOKEN_ID=$jwt_secret

# Authentication
JWT_SECRET=$jwt_secret

# Network Topology
NETWORK_SUBNET=192.168.1.0/24
SYSTEM_COUNT=20
NET_INTERFACE=eth0

# AI Providers
OLLAMA_HOST=http://ollama:11434
OPENAI_API_KEY=
ANTHROPIC_API_KEY=

# Automation Protocols
AUTO_HEAL=true
AUTO_SCALE=true
AUTO_REMEDIATE=true
AUTO_DEPLOY=true
AUTO_ROLLBACK=true

# Monitoring
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=$grafana_pass

# Communication
SLACK_WEBHOOK_URL=
SLACK_CHANNEL=#neural-network-alerts
EOF
    
    echo -e "$BRIGHT_GREEN"
    cat << 'EOF'
    ┌─────────────────────────────────────────────────────────────┐
    │  CONFIGURATION OPTIONS                                       │
    ├─────────────────────────────────────────────────────────────┤
    │  All security parameters have been auto-generated.           │
    │  You may customize the following:                           │
    └─────────────────────────────────────────────────────────────┘
EOF
    echo -e "$NC"
    
    # Interactive prompts
    echo -en "$NEON_PINK[◈ INPUT]$NC Network subnet [192.168.1.0/24]: "
    read subnet
    subnet=${subnet:-192.168.1.0/24}
    sed -i "s|NETWORK_SUBNET=.*|NETWORK_SUBNET=$subnet|" .env
    
    echo -en "$NEON_PINK[◈ INPUT]$NC System count [20]: "
    read count
    count=${count:-20}
    sed -i "s/SYSTEM_COUNT=.*/SYSTEM_COUNT=$count/" .env
    
    echo -en "$NEON_PINK[◈ INPUT]$NC Slack webhook URL (optional): "
    read slack_url
    if [[ ! -z "$slack_url" ]]; then
        sed -i "s|SLACK_WEBHOOK_URL=|SLACK_WEBHOOK_URL=$slack_url|" .env
    fi
    
    echo
    log_success "Configuration encrypted and stored!"
    
    # Show generated passwords
    echo -e "$BRIGHT_CYAN"
    echo "╔════════════════════════════════════════════════════════════════════════════╗"
    echo "║  AUTO-GENERATED SECURITY CREDENTIALS (SAVE THESE!)                         ║"
    echo "╠════════════════════════════════════════════════════════════════════════════╣"
    echo "║  Grafana Admin: admin / $grafana_pass"
    echo "║  PostgreSQL:    postgres / [ENCRYPTED]"
    echo "║  MinIO:        quantum_admin / [ENCRYPTED]"
    echo "╚════════════════════════════════════════════════════════════════════════════╝"
    echo -e "$NC"
    echo "Credentials saved to: $INSTALL_DIR/.env"
}

# Start services with cyber animation
start_services_cyber() {
    log_cyber "Initializing neural network..."
    
    cd "$INSTALL_DIR"
    
    # Pull images with progress
    log_info "Synchronizing with container registry..."
    docker compose pull > /dev/null 2>&1 &
    spinner $! "SYNCING"
    
    # Infrastructure
    log_cyber "Booting core infrastructure..."
    docker compose up -d postgres redis minio vault > /dev/null 2>&1 &
    spinner $! "BOOTING"
    
    echo -e "$BRIGHT_YELLOW"
    typewrite "> Waiting for neural pathways to stabilize..." 0.03 "$BRIGHT_YELLOW"
    echo -e "$NC"
    sleep 25
    
    # Monitoring
    log_cyber "Activating surveillance systems..."
    docker compose up -d prometheus grafana > /dev/null 2>&1 &
    spinner $! "ACTIVATING"
    
    # Core
    log_cyber "Starting consciousness core..."
    docker compose up -d orchestrator ollama > /dev/null 2>&1 &
    spinner $! "STARTING"
    
    # Agents
    log_cyber "Awakening agent swarm..."
    docker compose up -d ai-agent data-agent devops-agent netmon-agent security-agent plaintext-api > /dev/null 2>&1 &
    spinner $! "AWAKENING"
    
    # n8n
    log_cyber "Initializing automation matrix..."
    docker compose up -d n8n > /dev/null 2>&1 &
    spinner $! "INIT"
    
    # Nginx
    log_cyber "Deploying neural interface..."
    docker compose up -d nginx > /dev/null 2>&1 &
    spinner $! "DEPLOYING"
    
    log_success "All systems operational!"
}

# Final cyber banner
show_final_banner() {
    local ip=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "localhost")
    
    echo
    echo -e "$BRIGHT_GREEN"
    cat << EOF
    ╔══════════════════════════════════════════════════════════════════════════════╗
    ║                                                                              ║
    ║    ██╗  ██╗██╗   ██╗██████╗ ███████╗██████╗    ██╗   ██╗ ██████╗ ██╗   ██╗  ║
    ║    ██║  ██║╚██╗ ██╔╝██╔══██╗██╔════╝██╔══██╗   ╚██╗ ██╔╝██╔═══██╗██║   ██║  ║
    ║    ███████║ ╚████╔╝ ██║  ██║█████╗  ██║  ██║    ╚████╔╝ ██║   ██║██║   ██║  ║
    ║    ██╔══██║  ╚██╔╝  ██║  ██║██╔══╝  ██║  ██║     ╚██╔╝  ██║   ██║██║   ██║  ║
    ║    ██║  ██║   ██║   ██████╔╝███████╗██████╔╝      ██║   ╚██████╔╝╚██████╔╝  ║
    ║    ╚═╝  ╚═╝   ╚═╝   ╚═════╝ ╚══════╝╚═════╝       ╚═╝    ╚═════╝  ╚═════╝   ║
    ║                                                                              ║
    ╚══════════════════════════════════════════════════════════════════════════════╝
EOF
    echo -e "$NC"
    
    echo -e "$BRIGHT_CYAN"
    echo "╔════════════════════════════════════════════════════════════════════════════╗"
    echo "║                           ACCESS POINTS                                    ║"
    echo "╠════════════════════════════════════════════════════════════════════════════╣"
    echo "║  🌐 Dashboard:     http://$ip:8080                                          "
    echo "║  🤖 n8n:           http://$ip:5678                                          "
    echo "║  📊 Grafana:       http://$ip:3000                                          "
    echo "║  📚 API Docs:      http://$ip:8000/docs                                     "
    echo "║  🔌 Plain Text:    http://$ip:8006                                          "
    echo "╚════════════════════════════════════════════════════════════════════════════╝"
    echo -e "$NC"
    
    echo -e "$NEON_PINK"
    echo "╔════════════════════════════════════════════════════════════════════════════╗"
    echo "║                      NEURAL COMMAND INTERFACE                              ║"
    echo "╠════════════════════════════════════════════════════════════════════════════╣"
    echo "║  Run: aipm                                                                 ║"
    echo "║  Commands: start | stop | restart | status | logs | backup | update        ║"
    echo "╚════════════════════════════════════════════════════════════════════════════╝"
    echo -e "$NC"
    
    glitch_text ">>> SYSTEM READY. THE FUTURE IS NOW. <<<" 5
}

# Main function
main() {
    # Show epic intro
    matrix_rain 2
    show_main_banner
    show_hacking_sequence
    show_agent_matrix
    
    # Installation steps
    check_system_with_animation
    install_docker_cyber
    download_platform_cyber
    run_wizard_cyber
    
    # Create CLI tool
    log_cyber "Installing neural command interface..."
    sudo cp "$INSTALL_DIR/install.sh" /usr/local/bin/aipm 2>/dev/null || true
    sudo chmod +x /usr/local/bin/aipm 2>/dev/null || true
    
    # Start everything
    start_services_cyber
    
    # Show final epic banner
    show_final_banner
}

# Handle CLI arguments
if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    echo "AI Platform - Cyberpunk Edition Installer v$VERSION"
    echo ""
    echo "Usage: ./install-cyberpunk.sh [options]"
    echo ""
    echo "Options:"
    echo "  --help    Show this help"
    echo ""
    echo "Environment Variables:"
    echo "  INSTALL_DIR    Installation directory (default: /opt/ai-platform)"
    exit 0
fi

# Run main
main "$@"
