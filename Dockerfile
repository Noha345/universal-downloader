# Use an official Python runtime as a parent image
FROM python:3.10-slim-buster

RUN apt-get update && apt-get install -y ffmpeg

# Install FFmpeg (Required for video processing/merging)
RUN apt-get update && \
    apt-get install -y ffmpeg git && \
    apt-get clean

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file first (to cache dependencies)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Command to run the bot
CMD ["python", "main.py"]
