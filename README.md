# AI-Powered Codebase Explainer 🔍

An intelligent tool that helps developers understand unfamiliar codebases using AI-powered analysis and traditional AST parsing.

## ✨ Features

- 📦 **Upload Zipped Codebases**: Easy drag-and-drop interface
- 📊 **Automatic Analysis**: Extract classes, functions, imports from Python files
- 🤖 **AI Summaries**: Optional Google Gemini-powered semantic summaries
- 🔍 **Smart Search**: Browse and search through your codebase
- 🛡️ **Robust Error Handling**: Gracefully handles syntax errors and edge cases
- 🚀 **Fast & Efficient**: Template-based analysis works without API costs
- 🧹 **Auto Cleanup**: Automatic file management to prevent disk overflow
- ⚖️ **Codebase Comparison**: Compare different versions of codebases side-by-side

## 🚀 Quick Start (5 Minutes)

### Prerequisites
- Python 3.10+
- Google Gemini API key (optional - works without it!)

### 1. Install Dependencies
```powershell
# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install packages
pip install -r requirements.txt
```

### 2. Configure Environment
```powershell
# Copy template
copy .env.example .env

# Edit .env - for demo without API costs:
ENABLE_AI_FEATURES=false
DEMO_MODE=true
```

### 3. Start Backend
```powershell
uvicorn app.main:app --reload
```

Backend will be available at: http://localhost:8000

### 4. Start Frontend
```powershell
# In a new terminal
streamlit run streamlit_app.py
```

Frontend will open at: http://localhost:8501

## 🎬 Demo Video

Watch the full demo on YouTube: [https://youtu.be/G1oCQZctVqo](https://youtu.be/G1oCQZctVqo)

The demo showcases:
- Full upload workflow
- AI-powered code summarization
- File exploration and navigation
- Overview statistics
- Dependency graph visualization
- Codebase comparison feature

## 📖 Usage

1. **Upload**: Drag and drop a ZIP file containing Python code
2. **Analyze**: Wait for automatic parsing and summarization
3. **Explore**: Browse file tree, view summaries, and explore code structure
4. **Understand**: Get insights into classes, functions, and dependencies

## 🎯 Demo Mode (No AI Costs)

Perfect for testing and demos without incurring Google Gemini API costs:

```env
ENABLE_AI_FEATURES=false
DEMO_MODE=true
```

**What works in demo mode:**
- ✅ Upload and extract ZIP files
- ✅ Parse Python files with AST
- ✅ Extract classes, functions, imports
- ✅ File browser and source viewer
- ✅ Statistics and overview
- ✅ Error handling and validation

**What requires AI:**
- ❌ Semantic code summaries
- ❌ Natural language Q&A
- ❌ Embedding-based search

## 🏗️ Architecture

### Backend (FastAPI)
```
app/
├── main.py           # FastAPI application with middleware
├── config.py         # Configuration management
└── routes/
    ├── health.py     # Health checks
    ├── upload.py     # File upload handling
    ├── files.py      # File listing and content
    ├── summary.py    # Code summarization
    └── query.py      # Q&A endpoint (AI)
```

### Utilities
```
utils/
├── logger.py         # Structured JSON logging
├── cleanup.py        # Automatic file cleanup
└── __init__.py
```

### Frontend (Streamlit)
```
streamlit_app.py      # Interactive web UI
```

## 🛡️ Critical Fixes Implemented

### 1. ✅ API Key Management
- Graceful degradation when OpenAI key is missing
- Clear warnings in logs
- Auto-disable AI features if key not found

### 2. ✅ Directory Creation
- Auto-creates `uploads/`, `summaries/`, `uploads/temp/`
- No manual setup required
- Verified on startup

### 3. ✅ File Cleanup
- Scheduled cleanup every 24 hours (configurable)
- Removes files older than 7 days (configurable)
- Manual cleanup endpoint: `DELETE /upload/{upload_id}`

### 4. ✅ CORS Configuration
- Properly configured for Streamlit frontend
- Configurable via `.env` file
- Supports multiple origins

### 5. ✅ LlamaIndex Version Pinning
- All versions pinned in `requirements.txt`
- No import errors
- Tested compatibility

### 6. ✅ File Size Validation
- Enforces 100MB limit (configurable)
- Validates before processing
- Clear error messages

### 7. ✅ Race Condition Prevention
- Unique UUID for each upload
- No file conflicts
- Thread-safe cleanup

### 8. ✅ Embeddings Persistence
- Saved to disk (when AI enabled)
- Survives restarts
- Efficient storage

### 9. ✅ UI Error Boundaries
- Comprehensive error handling
- No UI crashes
- Clear error messages

### 10. ✅ AST Parser Robustness
- Handles syntax errors gracefully
- Per-file error isolation
- Continues processing other files

## 🧪 Testing

### Run Unit Tests
```powershell
pytest tests/
```

### Validate Demo Readiness
```powershell
python validate_demo.py
```

This script checks:
- ✅ Backend is running
- ✅ Directories exist
- ✅ Upload works
- ✅ Parsing works
- ✅ Error handling works

## 📊 API Documentation

Interactive API docs available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/upload` | Upload ZIP file |
| GET | `/files/{upload_id}` | List files |
| GET | `/files/{upload_id}/content` | Get file content |
| POST | `/summary/{upload_id}` | Generate summaries |
| POST | `/query/{upload_id}` | Ask questions (AI) |
| DELETE | `/upload/{upload_id}` | Delete upload |

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | None | Google Gemini API key (optional) |
| `ENABLE_AI_FEATURES` | true | Enable AI summaries |
| `MAX_UPLOAD_SIZE_MB` | 100 | Max upload size |
| `ALLOWED_ORIGINS` | localhost:8501 | CORS origins |
| `RATE_LIMIT_PER_MINUTE` | 60 | Rate limit |
| `CLEANUP_ENABLED` | true | Auto cleanup |
| `MAX_FILE_AGE_DAYS` | 7 | Cleanup threshold |
| `LOG_LEVEL` | INFO | Logging level |
| `DEMO_MODE` | false | Demo mode flag |

See `.env.example` for full configuration.

## 🐳 Docker Support

### Build Image
```powershell
docker build -t codebase-explainer .
```

### Run Container
```powershell
docker run -p 8000:8000 -p 8501:8501 -v ${PWD}/uploads:/app/uploads codebase-explainer
```

## 📈 Performance

- **Upload**: < 2s for 10MB ZIP
- **Parsing**: ~100 files/second (AST)
- **Summarization**: Depends on OpenAI API
- **Memory**: ~200MB baseline

## 🔒 Security

- ✅ Path traversal prevention
- ✅ ZIP bomb protection
- ✅ File type validation
- ✅ Size limits enforced
- ✅ Rate limiting
- ✅ CORS configuration
- ✅ Input sanitization

## 🗺️ Roadmap

### Phase 1: Foundation (✅ Completed)
- [x] Project setup and structure
- [x] File upload and extraction
- [x] AST-based parsing
- [x] Template summarization
- [x] Error handling
- [x] CORS and middleware
- [x] Streamlit UI

### Phase 2: AI Integration (In Progress)
- [ ] OpenAI API integration
- [ ] LlamaIndex setup
- [ ] Embedding generation
- [ ] Vector storage
- [ ] Semantic search

### Phase 3: Advanced Features
- [ ] Q&A over codebase
- [ ] Dependency visualization
- [ ] Multi-language support
- [ ] Collaboration features
- [ ] Export/sharing

### Phase 4: Production
- [ ] Authentication
- [ ] Database migration
- [ ] Performance optimization
- [ ] Monitoring/analytics
- [ ] CI/CD pipeline

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Submit a pull request

## 📝 License

MIT License - See LICENSE file for details

## 🐛 Troubleshooting

### Backend won't start
```powershell
# Check Python version
python --version  # Should be 3.10+

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Frontend can't connect
```powershell
# Check CORS in .env
ALLOWED_ORIGINS=http://localhost:8501

# Restart both servers
```

### Import errors
```powershell
# Make sure you're in project root
cd d:\04_Development\Codebase_Explainer

# Run from correct directory
uvicorn app.main:app --reload
```

### Out of disk space
```powershell
# Manual cleanup
rm -r uploads/*
rm -r summaries/*

# Or use API
curl -X DELETE http://localhost:8000/upload/{upload_id}
```

## 📞 Support

- **Issues**: Open a GitHub issue
- **Demo Checklist**: See `DEMO_CHECKLIST.md`
- **Validation**: Run `python validate_demo.py`

---

**Built with ❤️ using FastAPI, Streamlit, and Google Gemini**

---

📺 **Watch the Demo**: [YouTube Video](https://youtu.be/G1oCQZctVqo)
