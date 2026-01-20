# 1. Use Python 3.11 (Required for newer yt-dlp)
FROM python:3.11-slim

# 2. Install System Dependencies (FFmpeg is CRITICAL here)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your code
COPY . .

# Run the bot
CMD ["python", "bot.py"]
