# =============================================================================
# Smartfield Dashboard — UI container (PyQt6 + OpenCV)
#
# This container runs a PyQt6 GUI application and requires a host X11 display.
#
# HOW TO RUN (after docker compose wires this up):
#   xhost +local:docker                              # allow container X access
#   docker run --rm \
#     -e DISPLAY=$DISPLAY \
#     -v /tmp/.X11-unix:/tmp/.X11-unix \
#     -v $(pwd)/config.toml:/app/config.toml \
#     -v $(pwd)/logs/mission:/logs/mission \
#     -e CONFIG_PATH=/app/config.toml \
#     -e LOGS_DIR=/logs/mission \
#     -e SMARTFIELD_URL=http://localhost:9988 \
#     -e SUBSCRIBER_URL=http://localhost:9987 \
#     --network host \
#     smartfield-ui
#
# NOTE: Approve in docker-compose only after UI is reviewed and signed off.
# =============================================================================

FROM ubuntu:22.04

ARG DEBIAN_FRONTEND=noninteractive

# ── system dependencies ────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3-pip \
    python3-setuptools \
    # OpenCV runtime dependencies
    libgstreamer1.0-0 \
    libgstreamer-plugins-base1.0-0 \
    # Qt6 XCB / X11 platform plugin dependencies
    libgl1-mesa-glx \
    libgl1 \
    libegl1 \
    libglib2.0-0 \
    libxcb-xinerama0 \
    libxcb-cursor0 \
    libxkbcommon-x11-0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-shape0 \
    libdbus-1-3 \
    libfontconfig1 \
    libxrender1 \
    fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/*

RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1 && \
    update-alternatives --install /usr/bin/pip     pip     /usr/bin/pip3       1

# ── Python dependencies ────────────────────────────────────────────────────────
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ── application source ─────────────────────────────────────────────────────────
COPY . .

ENV QT_QPA_PLATFORM=xcb \
    DISPLAY=:0 \
    CONFIG_PATH=/app/config.toml \
    LOGS_DIR=/logs/mission \
    SMARTFIELD_URL=http://localhost:9988 \
    SUBSCRIBER_URL=http://localhost:9987

CMD ["python3", "dashboard.py"]
