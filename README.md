# FastAPI Student Management System

A comprehensive FastAPI application with student management, PDF document Q&A using LLM, JWT authentication, and real-time chat capabilities.

## 🚀 Features

- **Student Management**: Full CRUD operations with role-based access control
- **PDF Document Q&A**: Upload PDFs and ask questions using Ollama LLM
- **Real-time Chat**: SSE streaming responses with conversation history
- **JWT Authentication**: Secure login with admin/teacher/student roles
- **Bulk Operations**: CSV/Excel upload for batch student creation
- **Vector Search**: ChromaDB-powered semantic document search

## 📁 Project Structure

```
FastAPI/
├── frontend/                 # Chat UI assets
│   ├── index.html           # Main chat interface
│   ├── styles.css           # Theme and styling
│   └── app.js               # Client-side logic
├── student/                  # Main application package
│   ├── api/                 # API layer
│   │   ├── main.py          # FastAPI app entry point
│   │   ├── chats_router.py  # Chat management endpoints
│   │   └── ws_router.py     # Streaming chat endpoint
│   ├── core/                # Core utilities
│   │   ├── database.py      # SQLAlchemy models & DB setup
│   │   ├── models.py        # Pydantic schemas
│   │   └── celerey_app.py   # Celery configuration
│   ├── routers/             # API route handlers
│   │   ├── auth.py          # Authentication endpoints
│   │   ├── students.py      # Student CRUD endpoints
│   │   └── bulk_upload.py   # Bulk import/export
│   ├── doc_summarizer/      # PDF processing
│   │   ├── endpoint.py      # Document API endpoints
│   │   └── services/        # Embedding & search services
│   ├── middleware/          # Auth dependencies
│   ├── utils/               # Helpers (LLM, memory, etc.)
│   └── workers/             # Celery background tasks
├── tests/                   # Test suite
├── uploads/                 # Uploaded PDF storage (gitignored)
├── requirements.txt         # Python dependencies
└── .vscode/tasks.json       # VS Code run tasks
```

## 🛠️ Installation

### Prerequisites
- Python 3.11+
- MySQL database
- Redis server
- Ollama with llama3.2 model

### Setup

1. **Clone and create virtual environment**
```bash
git clone https://github.com/Shivam-432-bit/fastapi-student-app.git
cd fastapi-student-app
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Set environment variables**
```bash
export MYSQL_USER=root
export MYSQL_PASSWORD=yourpassword
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_DATABASE=school
export SECRET_KEY=your-secret-key
export ALGORITHM=HS256
export ACCESS_TOKEN_EXPIRE_MINUTES=30
```

4. **Start services**
```bash
# Terminal 1: Redis
redis-server

# Terminal 2: Ollama
ollama serve

# Terminal 3: Celery worker
celery -A student.core.celerey_app.celery_app worker --loglevel=info

# Terminal 4: FastAPI
uvicorn student.api.main:app --reload --host 0.0.0.0 --port 8000
```

Or use VS Code tasks: `Cmd+Shift+P` → "Run Task" → "Start All Services"

## 📚 API Endpoints

### Authentication (`/api/auth`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Register new user |
| POST | `/auth/login` | Get JWT token |
| GET | `/auth/me` | Current user info |

### Students (`/api/students`)
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/students/` | Create student | Any |
| GET | `/students/` | List students | Any |
| GET | `/students/{id}` | Get student | Any |
| PUT | `/students/{id}` | Update student | Admin/Teacher |
| DELETE | `/students/{id}` | Delete student | Admin |

### Bulk Operations (`/api/bulk`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/bulk/upload-students` | CSV/Excel import |
| GET | `/bulk/template/students` | Download template |
| POST | `/bulk/export-students` | Export to CSV/Excel |

### Documents (`/api`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/pdf/list` | List uploaded PDFs |
| POST | `/upload-and-process` | Upload PDF |
| GET | `/documents` | List processed docs |
| POST | `/search` | Vector search |
| POST | `/ask` | Ask question about doc |

### Chat (`/api/chats`, `/chat`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/chats` | List user chats |
| POST | `/api/chats/new` | Create chat |
| GET | `/api/chats/{id}` | Get chat history |
| DELETE | `/api/chats/{id}` | Delete chat |
| POST | `/api/chats/{id}/rename` | Rename chat |
| POST | `/chat/stream` | SSE streaming Q&A |

## 🎨 Frontend

Access the chat UI at `http://localhost:8000/`

Features:
- Theme switcher (Light/Dark/Coffee)
- PDF document selector
- Real-time streaming responses
- Chat history sidebar
- Markdown rendering

## 🧪 Testing

```bash
# Run all tests
pytest tests/

# Run specific test
pytest tests/test_health.py -v
```

## 📝 API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🔧 Tech Stack

- **Backend**: FastAPI, SQLAlchemy, Pydantic
- **Database**: MySQL, Redis, ChromaDB
- **LLM**: Ollama (llama3.2)
- **Task Queue**: Celery
- **Frontend**: Vanilla JS, CSS3

## 📄 License

MIT License

---

Built with ❤️ using FastAPI
