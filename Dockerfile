FROM python:3.11-slim

# Install System Dependencies
# We added 'nodejs' here to fix the YouTube Signature Error
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    nodejs \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --upgrade yt-dlp

WORKDIR /app

# Install Python Requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Code and Start
COPY . .
CMD ["python", "bot.py"]
