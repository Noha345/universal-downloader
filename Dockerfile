# Use Python 3.10 (Stable and fast)
FROM python:3.10-slim-buster

# 1. Install System Dependencies
# - FFmpeg: For merging video+audio
# - Node.js: REQUIRED for yt-dlp to bypass YouTube restrictions
RUN apt-get update && \
    apt-get install -y ffmpeg curl gnupg && \
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean

# 2. Set Working Directory
WORKDIR /app

# 3. Install Python Libraries
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy Your Code
COPY . .

# 5. Start the Bot
CMD ["python", "bot.py"]]
