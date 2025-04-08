#!/bin/bash
# deployment.sh for QRcode FastAPI application
set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting QRcode application deployment...${NC}"


# Install Docker if not installed
install_docker() {
    if ! command -v docker &> /dev/null; then
        echo -e "${GREEN}Installing Docker...${NC}"
        # Alternative installation method using apt
        sudo apt-get update
        sudo apt-get install -y \
            apt-transport-https \
            ca-certificates \
            curl \
            gnupg \
            lsb-release
        
        # Add Docker's official GPG key
        sudo mkdir -p /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        # Add Docker's official GPG key
        sudo mkdir -p /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        
        # Set up the repository
        echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
        $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
        # Install Docker Engine
        sudo apt-get update
        sudo apt-get install -y docker-ce docker-ce-cli containerd.io
        # Add current user to docker group
        sudo usermod -aG docker $USER
        
        echo -e "${GREEN}Docker installed successfully${NC}"
        echo -e "${YELLOW}You may need to log out and back in for group changes to take effect${NC}"
    else
        echo -e "${GREEN}Docker is already installed${NC}"
    fi
}

# Install Docker Compose if not installed
install_docker_compose() {
    if ! command -v docker-compose &> /dev/null; then
        echo -e "${GREEN}Installing Docker Compose...${NC}"
        sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
        echo -e "${GREEN}Docker Compose installed successfully${NC}"
    else
        echo -e "${GREEN}Docker Compose is already installed${NC}"
    fi
}
# Create necessary directories and set permissions
setup_directories() {
    echo -e "${GREEN}Setting up directories...${NC}"
    mkdir -p /app/auth-qrcode
    sudo chown -R $USER:$USER /app/auth-qrcode
}

# Pull latest code (assuming you're using git)
update_code() {
    echo -e "${GREEN}Updating code...${NC}"
    if [ -d "/app/auth-qrcode/.git" ]; then
        cd /app/auth-qrcode
        git pull
    else
        echo -e "${RED}Please manually copy your project files to /app/auth-qrcode${NC}"
        exit 1
    fi
}
# Deploy the application
deploy_application() {
    echo -e "${GREEN}Deploying application...${NC}"
    cd /app/auth-qrcode

    # Copy example env if .env doesn't exist
    if [ ! -f .env ]; then
        if [ -f .env.example ]; then
            cp .env.example .env
            echo -e "${RED}Please update the .env file with your configuration${NC}"
        else
            echo -e "${RED}No .env or .env.example file found${NC}"
            exit 1
        fi
    fi

    # Build and start containers
    docker-compose down
    docker-compose build --no-cache
    docker-compose up -d

    echo -e "${GREEN}Deployment completed successfully${NC}"
}
# Check deployment status
check_status() {
    echo -e "${GREEN}Checking deployment status...${NC}"
    docker-compose ps
    echo -e "\n${GREEN}Container logs:${NC}"
    docker-compose logs --tail=50
}
# Main execution
main() {
    install_docker
    install_docker_compose
    setup_directories
    update_code
    deploy_application
    check_status
}
# Run main function
main

echo -e "${GREEN}Deployment script completed!${NC}"