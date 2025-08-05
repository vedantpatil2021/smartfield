#!/bin/bash

# K3s Setup Script for SmartField Application
# This script installs K3s and sets up the cluster for the SmartField application

set -e

echo "🚀 Starting K3s setup for SmartField application..."

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo "❌ This script should not be run as root for security reasons"
   echo "   Please run as a regular user with sudo privileges"
   exit 1
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check system requirements
echo "📋 Checking system requirements..."

# Check if curl is installed
if ! command_exists curl; then
    echo "❌ curl is required but not installed. Please install curl first."
    exit 1
fi

# Check available memory (minimum 1GB recommended)
available_memory=$(free -m | awk 'NR==2{printf "%.0f", $7/1024}')
if [ "$available_memory" -lt 1 ]; then
    echo "⚠️  Warning: Less than 1GB memory available. K3s may not perform optimally."
fi

# Install K3s
echo "📦 Installing K3s..."
if command_exists k3s; then
    echo "✅ K3s is already installed"
    k3s --version
else
    echo "⬇️  Downloading and installing K3s..."
    curl -sfL https://get.k3s.io | sh -s - --write-kubeconfig-mode 644
    
    # Wait for K3s to be ready
    echo "⏳ Waiting for K3s to be ready..."
    timeout=300
    while [ $timeout -gt 0 ]; do
        if sudo k3s kubectl get nodes >/dev/null 2>&1; then
            break
        fi
        sleep 5
        timeout=$((timeout - 5))
    done
    
    if [ $timeout -eq 0 ]; then
        echo "❌ K3s failed to start within 5 minutes"
        exit 1
    fi
    
    echo "✅ K3s installed and running successfully"
fi

# Setup kubectl alias
echo "🔧 Setting up kubectl configuration..."
if ! grep -q "alias kubectl" ~/.bashrc 2>/dev/null; then
    echo 'alias kubectl="sudo k3s kubectl"' >> ~/.bashrc
    echo "✅ kubectl alias added to ~/.bashrc"
fi

# Export kubeconfig for current session
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml

# Create necessary directories
echo "📁 Creating required directories..."
sudo mkdir -p /opt/smartfield/{logs,loki-data,grafana-data,services/openpasslite/mission,mission}
sudo chown -R $USER:$USER /opt/smartfield
echo "✅ Directories created successfully"

# Copy project files to the appropriate locations
echo "📋 Setting up project files..."
if [ -d "./services/openpasslite/mission" ]; then
    cp -r ./services/openpasslite/mission/* /opt/smartfield/services/openpasslite/mission/
    echo "✅ OpenPassLite mission files copied"
fi

if [ -d "./mission" ]; then
    cp -r ./mission/* /opt/smartfield/mission/
    echo "✅ Mission files copied"
elif [ ! -d "/opt/smartfield/mission" ]; then
    echo "⚠️  Warning: No mission directory found. Creating empty directory."
    mkdir -p /opt/smartfield/mission
fi

# Build Docker images
echo "🐳 Building Docker images..."
if command_exists docker; then
    echo "Building OpenPassLite image..."
    docker build -t smartfield/openpasslite:latest ./services/openpasslite/
    
    echo "Building SmartField image..."
    docker build -t smartfield/smartfield:latest ./services/smartfields/
    
    echo "Building WildWings image..."
    docker build -t smartfield/wildwings:latest ./services/wildwings/
    
    echo "✅ All Docker images built successfully"
else
    echo "❌ Docker is not installed. Please install Docker first."
    echo "   You can install Docker using: curl -fsSL https://get.docker.com | sh"
    exit 1
fi

# Import images to K3s
echo "📥 Importing Docker images to K3s..."
sudo k3s ctr images import <(docker save smartfield/openpasslite:latest)
sudo k3s ctr images import <(docker save smartfield/smartfield:latest)
sudo k3s ctr images import <(docker save smartfield/wildwings:latest)
echo "✅ Images imported to K3s successfully"

# Create storage class
echo "💾 Setting up storage class..."
sudo k3s kubectl apply -f - <<EOF
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: local-storage
provisioner: kubernetes.io/no-provisioner
volumeBindingMode: WaitForFirstConsumer
EOF
echo "✅ Storage class created"

# Verify K3s cluster status
echo "🔍 Verifying K3s cluster status..."
sudo k3s kubectl get nodes
sudo k3s kubectl get pods -A

echo ""
echo "🎉 K3s setup completed successfully!"
echo ""
echo "📝 Next steps:"
echo "   1. Update ConfigMaps in k3s-manifests.yaml with your actual config files"
echo "   2. Run './start_application.sh' to deploy the SmartField application"
echo ""
echo "💡 Useful commands:"
echo "   - Check cluster status: sudo k3s kubectl get nodes"
echo "   - View all pods: sudo k3s kubectl get pods -A"
echo "   - Access logs: sudo k3s kubectl logs -n smartfield <pod-name>"
echo "   - Uninstall K3s: /usr/local/bin/k3s-uninstall.sh"
echo ""