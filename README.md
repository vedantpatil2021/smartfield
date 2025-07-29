Build Images

# Navigate to project root
cd "/Users/vedantsmac/Library/CloudStorage/OneDrive-TheOhioStateUniversity/Research Prof. Stewart/smartfield"

# Build all services
podman build -t smartfields:latest ./services/smartfields
podman build -t openpasslite:latest ./services/openpasslite
podman build -t wildwings:latest ./services/wildwings

Save Images for K3s

# Export images as tar files
podman save smartfields:latest -o smartfields.tar
podman save openpasslite:latest -o openpasslite.tar
podman save wildwings:latest -o wildwings.tar

Import to K3s

# Import images to K3s containerd
sudo k3s ctr images import smartfields.tar
sudo k3s ctr images import openpasslite.tar
sudo k3s ctr images import wildwings.tar

# Verify images
sudo k3s ctr images list | grep smartfield

## Alternative: Run with Podman Compose

# Use podman-compose instead of docker-compose
podman-compose up --build

# Or use podman play kube with docker-compose
podman play kube docker-compose.yml