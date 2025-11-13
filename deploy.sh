#!/bin/bash

set -e

REPO_URL="git@github.com:Gennadynemchin/AssistantBot.git"
APP_DIR="AssistantBot"
ENV_FILE=".env"
KEY_FILE="credentials/authorized_key.json"
IMAGE_NAME="assistant_bot"
CONTAINER_NAME="assistant-bot"

# 1. Clone the repository if it doesn't exist
if [ ! -d "$APP_DIR" ]; then
  echo "Cloning repository..."
  git clone "$REPO_URL"
else
  echo "Repository already cloned."
fi

cd "$APP_DIR"

# 2. Create .env from sample if not exists
if [ ! -f "$ENV_FILE" ]; then
  echo "Creating .env file from sample..."
  if [ -f "sample.env" ]; then
    cp sample.env .env
    echo "✅ Please edit the .env file to include your real credentials before continuing!"
    exit 1
  else
    echo "❌ sample.env file not found!"
    exit 1
  fi
fi

# 3. Check for authorized key
if [ ! -f "$KEY_FILE" ]; then
  echo "❌ Service account key file ($KEY_FILE) not found!"
  echo "Please place it at: $APP_DIR/$KEY_FILE"
  exit 1
fi

# 4. Build the Docker image
echo "Building Docker image..."
docker build -t "$IMAGE_NAME:latest" .

# 5. Stop and remove old container if exists
if [ "$(docker ps -aq -f name=$CONTAINER_NAME)" ]; then
  echo "Stopping and removing old container..."
  docker stop "$CONTAINER_NAME" || true
  docker rm "$CONTAINER_NAME" || true
fi

# 6. Run the Docker container
echo "Running Docker container..."
docker run -d \
  --name "$CONTAINER_NAME" \
  --env-file .env \
  -v "$PWD/$KEY_FILE:/app/authorized_key.json" \
  --restart always \
  "$IMAGE_NAME:latest"

echo "✅ AssistantBot deployed successfully!"
