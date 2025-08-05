#!/bin/bash

# SmartField Application Startup Script for K3s
# This script deploys the complete SmartField application stack to K3s

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting SmartField Application Deployment...${NC}"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check if K3s is installed and running
echo -e "${BLUE}📋 Checking K3s status...${NC}"
if ! command_exists k3s; then
    echo -e "${RED}❌ K3s is not installed. Please run './setup-k3s.sh' first.${NC}"
    exit 1
fi

if ! sudo k3s kubectl get nodes >/dev/null 2>&1; then
    echo -e "${RED}❌ K3s is not running. Please check K3s installation.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ K3s is running${NC}"

# Check if required files exist
echo -e "${BLUE}📁 Checking required files...${NC}"
required_files=("k3s-manifests.yaml" "config.toml" "promtail-config.yml")
for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo -e "${RED}❌ Required file '$file' not found${NC}"
        exit 1
    fi
done
echo -e "${GREEN}✅ All required files found${NC}"

# Create ConfigMaps from actual configuration files
echo -e "${BLUE}🔧 Creating ConfigMaps from actual configuration files...${NC}"

# Create ConfigMaps directly from files (more reliable than inline editing)
echo -e "${YELLOW}📝 Creating smartfield-config ConfigMap...${NC}"
sudo k3s kubectl create configmap smartfield-config \
  --from-file=config.toml=config.toml \
  --namespace=smartfield \
  --dry-run=client -o yaml > smartfield-config-cm.yaml

echo -e "${YELLOW}📝 Creating promtail-config ConfigMap...${NC}"
sudo k3s kubectl create configmap promtail-config \
  --from-file=config.yml=promtail-config.yml \
  --namespace=smartfield \
  --dry-run=client -o yaml > promtail-config-cm.yaml

# Create a version of manifests without the placeholder ConfigMaps
echo -e "${YELLOW}📝 Preparing deployment manifests...${NC}"
# Remove the placeholder ConfigMaps from the original manifest (more reliable approach)
awk '
BEGIN { skip = 0; buffer = "" }
/^---$/ { 
    if (buffer != "") print buffer
    buffer = "---"
    next 
}
/^kind: ConfigMap$/ { skip = 1; buffer = ""; next }
skip == 1 && /^---$/ { skip = 0; buffer = "---"; next }
skip == 1 { next }
{ 
    if (buffer != "") { print buffer; buffer = "" }
    print $0 
}
END { if (buffer != "") print buffer }
' k3s-manifests.yaml > k3s-manifests-temp.yaml

# Deploy the application
echo -e "${BLUE}🚀 Deploying SmartField application to K3s...${NC}"

# Apply the manifests in order
sudo k3s kubectl apply -f k3s-manifests-temp.yaml --validate=false
sudo k3s kubectl apply -f smartfield-config-cm.yaml
sudo k3s kubectl apply -f promtail-config-cm.yaml

# Wait for namespace to be created
echo -e "${YELLOW}⏳ Waiting for namespace to be ready...${NC}"
sudo k3s kubectl wait --for=condition=Active namespace/smartfield --timeout=60s

# Wait for PVCs to be bound
echo -e "${YELLOW}⏳ Waiting for storage to be ready...${NC}"
timeout=120
while [ $timeout -gt 0 ]; do
    if sudo k3s kubectl get pvc -n smartfield | grep -q "Bound"; then
        break
    fi
    sleep 5
    timeout=$((timeout - 5))
done

# Wait for deployments to be ready
echo -e "${YELLOW}⏳ Waiting for deployments to be ready...${NC}"
deployments=("openpasslite" "smartfield" "wildwings" "loki" "promtail" "grafana")

for deployment in "${deployments[@]}"; do
    echo -e "${YELLOW}   Waiting for $deployment...${NC}"
    sudo k3s kubectl wait --for=condition=available deployment/$deployment -n smartfield --timeout=300s
done

# Clean up temporary files
rm -f k3s-manifests-temp.yaml smartfield-config-cm.yaml promtail-config-cm.yaml

# Get node IP for service access
NODE_IP=$(sudo k3s kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')
if [ -z "$NODE_IP" ]; then
    NODE_IP="localhost"
fi

# Display deployment status
echo -e "\n${GREEN}🎉 SmartField Application Deployed Successfully!${NC}\n"

echo -e "${BLUE}📊 Deployment Status:${NC}"
sudo k3s kubectl get pods -n smartfield

echo -e "\n${BLUE}🌐 Service Access URLs:${NC}"
echo -e "${GREEN}OpenPassLite:${NC} http://$NODE_IP:32177"
echo -e "${GREEN}SmartField:${NC}   http://$NODE_IP:32188"
echo -e "${GREEN}WildWings:${NC}    http://$NODE_IP:32199"
echo -e "${GREEN}Grafana:${NC}      http://$NODE_IP:31000 (admin/admin)"
echo -e "${GREEN}Loki:${NC}         http://$NODE_IP:31100"

echo -e "\n${BLUE}💾 Storage Information:${NC}"
sudo k3s kubectl get pvc -n smartfield

echo -e "\n${BLUE}🔧 Useful Commands:${NC}"
echo -e "${YELLOW}View application logs:${NC}"
echo "  sudo k3s kubectl logs -n smartfield -l app=openpasslite -f"
echo "  sudo k3s kubectl logs -n smartfield -l app=smartfield -f"
echo "  sudo k3s kubectl logs -n smartfield -l app=wildwings -f"

echo -e "\n${YELLOW}Scale applications:${NC}"
echo "  sudo k3s kubectl scale deployment openpasslite -n smartfield --replicas=2"

echo -e "\n${YELLOW}Update application:${NC}"
echo "  sudo k3s kubectl rollout restart deployment/openpasslite -n smartfield"

echo -e "\n${YELLOW}Monitor cluster:${NC}"
echo "  sudo k3s kubectl get pods -n smartfield -w"

echo -e "\n${YELLOW}Access pod shell:${NC}"
echo "  sudo k3s kubectl exec -it deployment/openpasslite -n smartfield -- /bin/bash"

echo -e "\n${YELLOW}Delete application:${NC}"
echo "  sudo k3s kubectl delete namespace smartfield"

echo -e "\n${GREEN}✅ Application is ready for use!${NC}"

# Health check
echo -e "\n${BLUE}🏥 Performing health checks...${NC}"
sleep 10

for service in openpasslite:32177 smartfield:32188 wildwings:32199; do
    service_name=$(echo $service | cut -d: -f1)
    port=$(echo $service | cut -d: -f2)
    
    if curl -s --connect-timeout 5 http://$NODE_IP:$port >/dev/null; then
        echo -e "${GREEN}✅ $service_name is responding${NC}"
    else
        echo -e "${YELLOW}⚠️  $service_name is not yet responding (may still be starting)${NC}"
    fi
done

echo -e "\n${BLUE}🎯 Deployment completed at $(date)${NC}"