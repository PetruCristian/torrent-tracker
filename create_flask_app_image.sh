#!/bin/bash

IMAGE_NAME="tracker-web-app:latest"
SOURCE_DIR="./flask_app"

echo "Building Docker image: $IMAGE_NAME..."

docker build -t $IMAGE_NAME $SOURCE_DIR

if [ $? -eq 0 ]; then
    echo "Image '$IMAGE_NAME' is ready."
    echo "Run with: docker stack deploy -c docker-stack.yml tracker_stack"
else
    echo "Build failed."
    exit 1
fi