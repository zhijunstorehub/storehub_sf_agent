# 🚀 Development Guide

## Quick Start

### 1. Initial Setup
```bash
# Run setup (installs dependencies, creates .env)
python3 setup.py

# Update .env file with your credentials
cp .env_template .env
# Edit .env with your actual values
```

### 2. Start Development
```bash
# Start both frontend and backend
npm run dev

# Or start separately:
npm run backend    # FastAPI server on port 8000
npm run frontend   # Next.js app on port 3000
```

## 📁 Project Structure (Simplified)

```
salesforce-ai-colleague/
├── server.py              # 🚀 Backend entry point  
├── setup.py               # 📦 Setup script
├── package.json           # 🔧 Development scripts
├── .env                   # 🔐 Your credentials
│
├── src/                   # 🐍 Python backend
│   ├── app/
│   │   ├── api/          # FastAPI servers
│   │   ├── db/           # Database services
│   │   ├── services/     # Business logic
│   │   └── extractor/    # Salesforce extraction
│   └── config.py         # Configuration
│
├── frontend/              # ⚛️  React frontend
│   ├── src/app/          # Next.js pages
│   └── package.json      # Frontend dependencies
│
└── data/                  # 📊 SQLite database & temp files
```

## 🔧 Available Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start both frontend + backend |
| `npm run backend` | Start FastAPI server only |
| `npm run frontend` | Start Next.js app only |
| `npm run setup` | Run setup script |
| `npm run install-all` | Install all dependencies |

## 🌐 URLs

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## 🔧 Backend Details

### Automatic Backend Selection
The `server.py` automatically chooses:
- **Supabase backend** if credentials are in `.env`
- **SQLite backend** if no Supabase credentials

### Database Location
- SQLite: `data/salesforce_metadata.db`
- Supabase: Cloud database (URL in `.env`)

## 🛠️ Troubleshooting

### Python Import Errors
```bash
# Make sure you're running from project root
cd /path/to/salesforce-ai-colleague
python3 server.py
```

### Port Already in Use
```bash
# Kill existing servers
pkill -f "fastapi"
pkill -f "next-dev"

# Or use different ports
PORT=3001 npm run frontend
```

### Missing Dependencies
```bash
# Reinstall everything
npm run install-all
```

### Salesforce CLI Issues
```bash
# Check if CLI is installed
sf --version

# Login to your org
sf org login web --alias myorg
```

## 📝 Development Tips

1. **Backend Changes**: Auto-reload enabled with `reload=True`
2. **Frontend Changes**: Hot reload automatically works
3. **Database**: SQLite file in `data/` directory
4. **Logs**: Check terminal output for errors
5. **API Testing**: Use http://localhost:8000/docs

## 🎯 Next Steps

1. Update your `.env` file with real credentials
2. Run `npm run dev`
3. Open http://localhost:3000
4. Start building! 🚀 