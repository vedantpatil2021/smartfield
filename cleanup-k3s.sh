#!/bin/bash

# SmartField K3s Cleanup Script
# This script reverses all changes made by setup-k3s.sh and start_application.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧹 Starting SmartField K3s Cleanup...${NC}"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Stop and remove SmartField application from K3s
if command_exists k3s && sudo k3s kubectl get nodes >/dev/null 2>&1; then
    echo -e "${BLUE}🗑️  Removing SmartField application from K3s...${NC}"
    
    # Delete the SmartField namespace (this removes all resources)
    if sudo k3s kubectl get namespace smartfield >/dev/null 2>&1; then
        echo -e "${YELLOW}   Deleting smartfield namespace...${NC}"
        sudo k3s kubectl delete namespace smartfield --timeout=60s || true
        echo -e "${GREEN}✅ SmartField namespace deleted${NC}"
    fi
    
    # Delete storage class
    if sudo k3s kubectl get storageclass local-storage >/dev/null 2>&1; then
        echo -e "${YELLOW}   Deleting local-storage StorageClass...${NC}"
        sudo k3s kubectl delete storageclass local-storage || true
        echo -e "${GREEN}✅ Storage class deleted${NC}"
    fi
fi

# Remove Docker images
echo -e "${BLUE}🐳 Removing SmartField Docker images...${NC}"
if command_exists docker; then
    images=("smartfield/openpasslite:latest" "smartfield/smartfield:latest" "smartfield/wildwings:latest")
    for image in "${images[@]}"; do
        if docker images --format "table {{.Repository}}:{{.Tag}}" | grep -q "$image"; then
            echo -e "${YELLOW}   Removing $image...${NC}"
            docker rmi "$image" || true
        fi
    done
    echo -e "${GREEN}✅ Docker images removed${NC}"
fi

# Remove K3s images
if command_exists k3s; then
    echo -e "${BLUE}📥 Removing images from K3s...${NC}"
    images=("docker.io/smartfield/openpasslite:latest" "docker.io/smartfield/smartfield:latest" "docker.io/smartfield/wildwings:latest")
    for image in "${images[@]}"; do
        if sudo k3s ctr images list | grep -q "$image"; then
            echo -e "${YELLOW}   Removing $image from K3s...${NC}"
            sudo k3s ctr images rm "$image" || true
        fi
    done
    echo -e "${GREEN}✅ K3s images removed${NC}"
fi

# Uninstall K3s
echo -e "${BLUE}🗑️  Uninstalling K3s...${NC}"
if command_exists k3s; then
    if [ -f "/usr/local/bin/k3s-uninstall.sh" ]; then
        echo -e "${YELLOW}   Running K3s uninstall script...${NC}"
        sudo /usr/local/bin/k3s-uninstall.sh
        echo -e "${GREEN}✅ K3s uninstalled${NC}"
    else
        echo -e "${RED}❌ K3s uninstall script not found${NC}"
    fi
else
    echo -e "${GREEN}✅ K3s not installed${NC}"
fi

# Remove kubectl alias from bashrc
echo -e "${BLUE}🔧 Removing kubectl alias from ~/.bashrc...${NC}"
if [ -f ~/.bashrc ]; then
    if grep -q "alias kubectl" ~/.bashrc; then
        sed -i.bak '/alias kubectl="sudo k3s kubectl"/d' ~/.bashrc
        echo -e "${GREEN}✅ kubectl alias removed from ~/.bashrc${NC}"
    else
        echo -e "${GREEN}✅ kubectl alias not found in ~/.bashrc${NC}"
    fi
fi

# Remove SmartField directories
echo -e "${BLUE}📁 Removing SmartField directories...${NC}"
if [ -d "/opt/smartfield" ]; then
    echo -e "${YELLOW}   Removing /opt/smartfield...${NC}"
    sudo rm -rf /opt/smartfield
    echo -e "${GREEN}✅ /opt/smartfield directory removed${NC}"
else
    echo -e "${GREEN}✅ /opt/smartfield directory not found${NC}"
fi

# Clean up temporary manifest files
echo -e "${BLUE}🧹 Cleaning up temporary files...${NC}"
temp_files=("smartfield-config-cm.yaml" "promtail-config-cm.yaml")
for file in "${temp_files[@]}"; do
    if [ -f "$file" ]; then
        rm -f "$file"
        echo -e "${GREEN}✅ Removed $file${NC}"
    fi
done

# Clean up any remaining K3s files
echo -e "${BLUE}🧹 Cleaning up remaining K3s files...${NC}"
k3s_dirs=("/etc/rancher" "/var/lib/rancher" "/var/lib/kubelet" "/etc/systemd/system/k3s.service" "/etc/systemd/system/k3s-agent.service")
for dir in "${k3s_dirs[@]}"; do
    if [ -e "$dir" ]; then
        echo -e "${YELLOW}   Removing $dir...${NC}"
        sudo rm -rf "$dir" || true
    fi
done

# Reload systemd if systemd files were removed
if systemctl is-active --quiet systemd >/dev/null 2>&1; then
    echo -e "${YELLOW}   Reloading systemd daemon...${NC}"
    sudo systemctl daemon-reload || true
fi

# Clean up any remaining processes
echo -e "${BLUE}🔄 Checking for remaining K3s processes...${NC}"
if pgrep -f k3s > /dev/null; then
    echo -e "${YELLOW}   Killing remaining K3s processes...${NC}"
    sudo pkill -f k3s || true
    sleep 2
fi

# Final verification
echo -e "\n${BLUE}🔍 Verification:${NC}"
if ! command_exists k3s; then
    echo -e "${GREEN}✅ K3s is not installed${NC}"
else
    echo -e "${RED}❌ K3s command still exists${NC}"
fi

if [ ! -d "/opt/smartfield" ]; then
    echo -e "${GREEN}✅ /opt/smartfield directory removed${NC}"
else
    echo -e "${RED}❌ /opt/smartfield directory still exists${NC}"
fi

if ! docker images --format "table {{.Repository}}:{{.Tag}}" | grep -q "smartfield/"; then
    echo -e "${GREEN}✅ SmartField Docker images removed${NC}"
else
    echo -e "${YELLOW}⚠️  Some SmartField Docker images may still exist${NC}"
fi

echo -e "\n${GREEN}🎉 SmartField K3s cleanup completed!${NC}"
echo -e "\n${BLUE}📝 What was cleaned up:${NC}"
echo -e "   - SmartField application from K3s cluster"
echo -e "   - K3s cluster and all components"
echo -e "   - SmartField Docker images"
echo -e "   - /opt/smartfield directory and all data"
echo -e "   - kubectl alias from ~/.bashrc"
echo -e "   - K3s system files and processes"
echo -e "   - Storage classes and persistent volumes"
echo -e "\n${YELLOW}💡 Note: Your original project files remain untouched${NC}"
echo -e "${YELLOW}    Only the K3s cluster and deployed resources were removed${NC}"