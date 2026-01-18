#!/bin/bash

IMAGE_NAME="nginx-router:latest"
SOURCE_DIR="./nginx_router"

echo "Building Docker image: $IMAGE_NAME..."

docker build -t $IMAGE_NAME $SOURCE_DIR

if [ $? -eq 0 ]; then
    echo "Image '$IMAGE_NAME' is ready."
    echo "Run with: docker stack deploy -c docker-stack.yml tracker_stack"
else
    echo "Build failed."
    exit 1
fi