FROM python:3.11-slim

# Set working directory
WORKDIR /workspace

# Install system dependencies
RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends \
        curl \
        git \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install OpenCode
RUN curl -fsSL https://raw.githubusercontent.com/opencode-ai/opencode/refs/heads/main/install | bash

# Set up OpenCode environment
ENV PATH="/root/.opencode/bin:$PATH"

# Create config directory
RUN mkdir -p /root/.config/opencode

# Copy OpenCode configuration
COPY opencode_config.json /root/.config/opencode/config.json

# Set environment variables for Vertex AI
ENV VERTEXAI_PROJECT=summit-ai-platform
ENV VERTEXAI_LOCATION=us-central1

# Create entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Set entrypoint
ENTRYPOINT ["/entrypoint.sh"] 