# Use Python 3.10 on Debian Bookworm (Current Stable)
FROM python:3.10-slim-bookworm

# 1. Install System Dependencies
# - FFmpeg: Required for merging video+audio
# - curl & gnupg: Required to setup Node.js
RUN apt-get update && \
    apt-get install -y ffmpeg curl gnupg && \
    apt-get clean

# 2. Install Node.js (Required for yt-dlp to bypass YouTube blocks)
# We use the official NodeSource setup script for Debian Bookworm
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 3. Set Working Directory
WORKDIR /app

# 4. Install Python Libraries
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy Your Code
COPY . .

# 6. Start the Bot
CMD ["python", "main.py"]
