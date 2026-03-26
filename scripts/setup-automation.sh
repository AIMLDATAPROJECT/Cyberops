#!/bin/bash
# AI Platform - Full Automation Setup Script
# Sets up complete AI-driven automation for 20-system infrastructure

echo "🚀 AI Platform Full Automation Setup"
echo "===================================="

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}Step 1: Creating shared directories...${NC}"
mkdir -p n8n_data/workflows
mkdir -p n8n_data/executions
mkdir -p n8n_data/logs
cp workflows/n8n/*.json n8n_data/workflows/

echo -e "${BLUE}Step 2: Starting core infrastructure...${NC}"
docker compose up -d postgres redis minio vault prometheus grafana n8n

echo -e "${YELLOW}Waiting for infrastructure to be ready...${NC}"
sleep 30

echo -e "${BLUE}Step 3: Starting orchestrator...${NC}"
docker compose up -d orchestrator

echo -e "${YELLOW}Waiting for orchestrator...${NC}"
sleep 10

echo -e "${BLUE}Step 4: Starting all agents...${NC}"
docker compose up -d ai-agent data-agent devops-agent netmon-agent security-agent

echo -e "${YELLOW}Waiting for agents to register...${NC}"
sleep 15

echo -e "${BLUE}Step 5: Checking agent status...${NC}"
curl -s http://localhost:8000/agents | jq '.[] | {agent: .agent_type, status: .status}'

echo -e "${BLUE}Step 6: Starting nginx...${NC}"
docker compose up -d nginx

echo -e "${GREEN}====================================${NC}"
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo -e "${GREEN}====================================${NC}"
echo ""
echo "📊 Dashboard: http://localhost:8080"
echo "🔧 n8n Workflows: http://localhost:5678"
echo "📈 Grafana: http://localhost:3000"
echo "🤖 Orchestrator API: http://localhost:8000/docs"
echo ""
echo "${YELLOW}Next Steps:${NC}"
echo "1. Import n8n workflows from /workflows/n8n/"
echo "2. Activate the Master Coordinator workflow"
echo "3. Watch your infrastructure run itself!"
echo ""
echo "${BLUE}Useful Commands:${NC}"
echo "  ./scripts/start-automation.sh  - Start automation"
echo "  ./scripts/stop-automation.sh   - Stop automation"
echo "  ./scripts/check-health.sh      - Check system health"
echo "  ./scripts/force-heal.sh        - Force healing cycle"
