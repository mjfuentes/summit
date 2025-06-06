# Summit AI Web Server

## Quick Start

### Automated Startup (Recommended)

**Choose your platform:**

**Python (All platforms):**
```bash
python3 web/start.py
```

**Mac/Linux:**
```bash
cd web && ./start.sh
```

### Manual Startup

```bash
cd web
python3 server.py
```

## Features

- **Automatic dependency installation**  
- **Cross-platform compatibility**  
- **Automatic browser opening** (Python script)  
- **Error checking and helpful messages**  
- **Clean shutdown handling**  

## Access Points

Once started, access Summit through:

- **Web Interface:** http://localhost:8000
- **API Documentation:** http://localhost:8000/docs  
- **Health Check:** http://localhost:8000/health

## Web Interface Features

### 💡 Ask for Advice
Get AI-powered advice on any topic with optional context

### 🧠 Share Knowledge  
Share experiences, insights, and observations with categorization

### 📊 System Status
Real-time status dashboard showing:
- Server uptime
- Knowledge base items  
- Daily budget usage

### 📈 Analytics & Insights
- Search analytics and performance metrics
- Content insights and knowledge gaps analysis
- Query suggestions

## API Endpoints

### Core Endpoints
- `POST /api/advice` - Get AI advice
- `POST /api/share` - Share knowledge
- `POST /api/learn` - Search knowledge base
- `GET /api/status` - System status
- `GET /api/cost-report` - Cost tracking
- `POST /api/analytics` - Search analytics
- `GET /api/insights` - Content insights

### Advanced Endpoints  
- `POST /api/learn-capability` - Learn new capabilities via Codespaces
- `GET /api/codespace-status` - Check development environments
- `POST /api/deploy` - Deploy changes
- `POST /api/cleanup` - Clean up environments

### Utility Endpoints
- `GET /health` - Health check
- `GET /` - Web interface

## Stopping the Server

Press `Ctrl+C` in the terminal to stop the server gracefully.

## Troubleshooting

**Port 8000 already in use:**
```bash
# Find and kill process using port 8000
lsof -ti:8000 | xargs kill -9
```

**Missing dependencies:**
```bash
pip install fastapi uvicorn
```

**Permission denied (Mac/Linux):**
```bash
chmod +x web/start.sh
```

## Development

The web server runs with auto-reload enabled, so changes to the code will automatically restart the server during development.

**Server Configuration:**
- Host: `0.0.0.0` (accessible from other devices on network)
- Port: `8000`  
- Reload: `True` (development mode)
- Log Level: `info` 