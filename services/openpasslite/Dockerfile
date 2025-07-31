FROM python:3.9-slim

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install system dependencies required for parrot-olympe and OpenCV
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    pkg-config \
    curl \
    wget \
    # FFmpeg and multimedia libraries for parrot-olympe video processing
    libavcodec-dev \
    libavformat-dev \
    libavutil-dev \
    libswscale-dev \
    libavdevice-dev \
    libavfilter-dev \
    # GStreamer for parrot-olympe streaming
    libgstreamer1.0-dev \
    libgstreamer-plugins-base1.0-dev \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav \
    gstreamer1.0-tools \
    # OpenCV dependencies
    libopencv-dev \
    python3-opencv \
    libgtk-3-dev \
    libglib2.0-0 \
    libglib2.0-dev \
    # Graphics libraries for OpenGL support
    libgl1-mesa-glx \
    libgl1-mesa-dev \
    libegl1-mesa-dev \
    libgles2-mesa-dev \
    # X11 and display libraries
    libx11-6 \
    libxext6 \
    libxrender1 \
    libxrandr2 \
    libxss1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxfixes3 \
    libxi6 \
    libxtst6 \
    libxcb1 \
    libxcb-glx0 \
    libxcb-shm0 \
    libxcb-dri2-0 \
    libxcb-dri3-0 \
    libxcb-present0 \
    libxcb-sync1 \
    libxshmfence1 \
    libxxf86vm1 \
    # Additional libraries for parrot-olympe
    libdrm2 \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libwebp-dev \
    # Network and protocol libraries
    libssl-dev \
    libffi-dev \
    # Python development headers
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Set display environment variable for headless operation
ENV DISPLAY=:99

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories for logs and media
RUN mkdir -p /app/logs /app/static /app/mission

# Set proper permissions
RUN chmod +x main.py

# Expose the port
EXPOSE 2177

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:2177/ || exit 1

# Run the application
CMD ["python", "main.py"]