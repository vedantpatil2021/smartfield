# Use Ubuntu 22.04 as base (recommended by Olympe docs)
FROM ubuntu:22.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies required for olympe
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3.10-venv \
    python3-pip \
    python3.10-dev \
    curl \
    wget \
    git \
    build-essential \
    cmake \
    pkg-config \
    libssl-dev \
    libffi-dev \
    libavcodec-dev \
    libavformat-dev \
    libavutil-dev \
    libswscale-dev \
    libswresample-dev \
    libsdl2-dev \
    libglfw3-dev \
    libgl1-mesa-dev \
    libegl1-mesa-dev \
    libgles2-mesa-dev \
    libx11-dev \
    libxrandr-dev \
    libxinerama-dev \
    libxcursor-dev \
    libxi-dev \
    libgstreamer1.0-dev \
    libgstreamer-plugins-base1.0-dev \
    libgstreamer-plugins-bad1.0-dev \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav \
    libjson-c-dev \
    libcurl4-gnutls-dev \
    libprotobuf-dev \
    libprotobuf-c-dev \
    protobuf-compiler \
    protobuf-c-compiler \
    rsync \
    && rm -rf /var/lib/apt/lists/*

# Ensure we're using Python 3.10 as default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.10 1

# Upgrade pip to meet Olympe requirements (>=20.3)
RUN python3 -m pip install --upgrade pip setuptools wheel

# Set working directory
WORKDIR /app

# Create necessary directories
RUN mkdir -p /app/logs

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install other Python dependencies first
RUN pip3 install --no-cache-dir fastapi uvicorn[standard] toml python-multipart opencv-python

# Install olympe separately with verbose output to debug any issues
RUN pip3 install --no-cache-dir --verbose parrot-olympe>=7.7.0

# Set library paths for native libraries
ENV LD_LIBRARY_PATH=/usr/local/lib/python3.10/dist-packages/olympe_deps:/usr/local/lib:$LD_LIBRARY_PATH
ENV PYTHONPATH=/app:$PYTHONPATH

# Copy application code
COPY . .

# Create a non-root user for security
RUN useradd -m -u 1000 droneuser && \
    chown -R droneuser:droneuser /app

# Test olympe import before switching users
RUN python3 -c "import olympe; print('Olympe imported successfully')"

USER droneuser

# Expose the port (matching config.toml)
EXPOSE 2177

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:2177/ || exit 1

# Run the application
CMD ["python3", "main.py"]
