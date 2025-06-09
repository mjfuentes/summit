FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies including FastMCP
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir fastmcp>=0.4.1

# Copy source code
COPY . .

# Set environment variables
ENV PYTHONPATH="/app"
ENV PYTHONUNBUFFERED=1
ENV MCP_TRANSPORT="sse"

# Expose port
EXPOSE 8080

# Run the FastMCP server
CMD ["python", "-m", "src.fastmcp_server"] 