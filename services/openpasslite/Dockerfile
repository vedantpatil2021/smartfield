FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for Parrot Olympe
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    cmake \
    git \
    libavcodec-dev \
    libavformat-dev \
    libavutil-dev \
    libswscale-dev \
    libgstreamer1.0-dev \
    libgstreamer-plugins-base1.0-dev \
    libgtk-3-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 2177

CMD ["python", "main.py"]