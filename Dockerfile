# Use Python 3.10
FROM python:3.10-slim-buster

# Install FFmpeg (for video) AND Node.js (for YouTube)
RUN apt-get update && \
    apt-get install -y ffmpeg curl gnupg && \
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot.py"]
