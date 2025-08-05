#!/bin/bash

# Fix SmartField K3s Deployment Issues
# This script fixes image pull and configuration issues

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🔧 Fixing SmartField K3s Deployment Issues...${NC}"

# Check if images exist locally in Docker
echo -e "${BLUE}📦 Checking Docker images...${NC}"
if ! docker image inspect smartfield/openpasslite:latest >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  OpenPassLite image not found, building...${NC}"
    docker build -t smartfield/openpasslite:latest ./services/openpasslite/
fi

if ! docker image inspect smartfield/smartfield:latest >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  SmartField image not found, building...${NC}"
    docker build -t smartfield/smartfield:latest ./services/smartfields/
fi

if ! docker image inspect smartfield/wildwings:latest >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  WildWings image not found, building...${NC}"
    docker build -t smartfield/wildwings:latest ./services/wildwings/
fi

# Re-import images to K3s with proper containerd namespace
echo -e "${BLUE}📥 Re-importing images to K3s...${NC}"

# Create temporary directory for image exports
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

echo "Exporting and importing OpenPassLite image..."
docker save smartfield/openpasslite:latest > "$TEMP_DIR/openpasslite.tar"
sudo k3s ctr images import --base-name smartfield/openpasslite:latest "$TEMP_DIR/openpasslite.tar"

echo "Exporting and importing SmartField image..."
docker save smartfield/smartfield:latest > "$TEMP_DIR/smartfield.tar"
sudo k3s ctr images import --base-name smartfield/smartfield:latest "$TEMP_DIR/smartfield.tar"

echo "Exporting and importing WildWings image..."
docker save smartfield/wildwings:latest > "$TEMP_DIR/wildwings.tar"
sudo k3s ctr images import --base-name smartfield/wildwings:latest "$TEMP_DIR/wildwings.tar"

# Verify images are imported
echo -e "${BLUE}✅ Verifying imported images...${NC}"
sudo k3s ctr images list | grep smartfield

# Delete the old pods to force recreation with imagePullPolicy: Never
echo -e "${BLUE}🔄 Restarting failed deployments...${NC}"
sudo k3s kubectl delete pod -n smartfield -l app=openpasslite
sudo k3s kubectl delete pod -n smartfield -l app=smartfield
sudo k3s kubectl delete pod -n smartfield -l app=wildwings

# Apply the updated manifests with imagePullPolicy: Never
echo -e "${BLUE}📝 Applying updated manifests...${NC}"
sudo k3s kubectl apply -f k3s-base-manifests.yaml

# Create missing ConfigMaps
echo -e "${BLUE}🗂️  Creating missing ConfigMaps...${NC}"
if ! sudo k3s kubectl get configmap promtail-config -n smartfield >/dev/null 2>&1; then
    sudo k3s kubectl create configmap promtail-config \
      --from-file=config.yml=promtail-config.yml \
      --namespace=smartfield
fi

if ! sudo k3s kubectl get configmap smartfield-config -n smartfield >/dev/null 2>&1; then
    sudo k3s kubectl create configmap smartfield-config \
      --from-file=config.toml=config.toml \
      --namespace=smartfield
fi

# Restart promtail to pick up the config
sudo k3s kubectl delete pod -n smartfield -l app=promtail

# Check for volume permission issues and fix them
echo -e "${BLUE}📁 Fixing volume permissions...${NC}"
sudo mkdir -p /opt/smartfield/{logs,loki-data,grafana-data}
sudo chown -R 472:472 /opt/smartfield/grafana-data  # Grafana user
sudo chown -R 10001:10001 /opt/smartfield/loki-data  # Loki user
sudo chmod 755 /opt/smartfield/logs

# Restart loki and grafana to fix CrashLoopBackOff
echo -e "${BLUE}🔄 Restarting monitoring services...${NC}"
sudo k3s kubectl delete pod -n smartfield -l app=loki
sudo k3s kubectl delete pod -n smartfield -l app=grafana

# Wait for pods to be ready
echo -e "${YELLOW}⏳ Waiting for pods to be ready...${NC}"
timeout=300
while [ $timeout -gt 0 ]; do
    ready_pods=$(sudo k3s kubectl get pods -n smartfield --no-headers | grep -c "1/1.*Running" || echo "0")
    total_pods=$(sudo k3s kubectl get pods -n smartfield --no-headers | wc -l)
    
    echo -e "${YELLOW}   $ready_pods/$total_pods pods ready...${NC}"
    
    if [ $ready_pods -eq $total_pods ] && [ $total_pods -gt 0 ]; then
        break
    fi
    
    sleep 10
    timeout=$((timeout - 10))
done

# Display final status
echo -e "\n${GREEN}🎉 Deployment fix completed!${NC}\n"

echo -e "${BLUE}📊 Final Pod Status:${NC}"
sudo k3s kubectl get pods -n smartfield

echo -e "\n${BLUE}🔍 If any pods are still failing, check logs with:${NC}"
echo "  sudo k3s kubectl logs -n smartfield <pod-name>"

echo -e "\n${BLUE}🌐 Service URLs (once all pods are running):${NC}"
NODE_IP=$(sudo k3s kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')
echo -e "${GREEN}OpenPassLite:${NC} http://$NODE_IP:32177"
echo -e "${GREEN}SmartField:${NC}   http://$NODE_IP:32188"
echo -e "${GREEN}WildWings:${NC}    http://$NODE_IP:32199"
echo -e "${GREEN}Grafana:${NC}      http://$NODE_IP:31000 (admin/admin)"
echo -e "${GREEN}Loki:${NC}         http://$NODE_IP:31100"