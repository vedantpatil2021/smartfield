#!/bin/bash

# ===========================================
# CLOUD MACHINE (USB SERVER) - Run this script
# ===========================================
setup_usb_server() {
    # Install and setup
    sudo apt update && sudo apt install -y usbip
    sudo modprobe usbip-core usbip-host
    
    # List USB devices
    echo "Available USB devices:"
    lsusb
    
    # Bind all USB devices (or specify specific busid)
    for device in $(usbip list -l | grep -o "[0-9]-[0-9]"); do
        sudo usbip bind -b $device
        echo "Bound device: $device"
    done
    
    # Start server
    sudo usbipd -D
    echo "USB server started on port 3240"
    
    # Open firewall
    sudo ufw allow 3240 2>/dev/null || true
}

# ===========================================
# EDGE MACHINE (USB CLIENT) - Run this script
# ===========================================
connect_usb_client() {
    CLOUD_IP=$1
    
    if [ -z "$CLOUD_IP" ]; then
        echo "Usage: $0 <cloud-machine-ip>"
        exit 1
    fi
    
    # Install and setup
    sudo apt update && sudo apt install -y usbip
    sudo modprobe usbip-core vhci-hcd
    
    # List and attach all remote USB devices
    echo "Available remote USB devices:"
    usbip list -r $CLOUD_IP
    
    # Auto-attach all devices
    for device in $(usbip list -r $CLOUD_IP | grep -o "[0-9]-[0-9]"); do
        sudo usbip attach -r $CLOUD_IP -b $device
        echo "Attached device: $device"
    done
    
    echo "USB devices forwarded successfully!"
    lsusb
}

# ===========================================
# AUTO-DETECT AND RUN
# ===========================================
if [ "$1" = "server" ]; then
    setup_usb_server
elif [ "$1" = "client" ]; then
    connect_usb_client $2
else
    echo "Usage:"
    echo "  Cloud machine:  $0 server"
    echo "  Edge machine:   $0 client <cloud-ip>"
fi