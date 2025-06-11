# RunPod Worker Dockerfile for Qwen 2.5 + OpenCode Integration
FROM runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /workspace

# Install Python dependencies in stages to avoid timeouts
RUN pip install --upgrade pip

# Install core dependencies first
RUN pip install --no-cache-dir \
    runpod \
    transformers>=4.35.0 \
    accelerate>=0.20.0

# Install tokenization and utility libraries
RUN pip install --no-cache-dir \
    sentencepiece \
    tiktoken \
    einops

# Skip bitsandbytes for now - it's problematic in Docker builds
# and not essential for basic inference
# RUN pip install bitsandbytes

# Copy our handler code
COPY runpod_handler_for_bridge.py handler.py

# RunPod expects the handler to be named handler.py
# and the handler function to be accessible

# Start command
CMD ["python", "handler.py"] 