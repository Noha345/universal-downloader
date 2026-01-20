# 1. Use Python 3.11 (Required for newer yt-dlp)
FROM python:3.11-slim

# 2. Install System Dependencies (FFmpeg is CRITICAL here)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# 3. Set Working Directory
WORKDIR /app

# ... (rest of your Dockerfile: COPY requirements, RUN pip, etc.)
