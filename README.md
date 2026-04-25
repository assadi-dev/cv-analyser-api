# Job Optimizer API

AI-powered personal job application tracker — FastAPI backend.

## Stack
- **Python 3.12** + FastAPI
- **SQLAlchemy 2.x** (async) + Alembic + PostgreSQL 16
- **LangGraph** + LangChain for AI agents
- **SSE** for real-time streaming
- **better-auth** token exchange bridge

## Prerequisites

This project requires **Tesseract OCR** for text extraction from images/PDFs. Follow the instructions for your OS:

### Windows
1. Download the installer from [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki).
2. Install it (default path is usually `C:\Program Files\Tesseract-OCR`).
3. Add the installation folder to your system **PATH** environment variable.

### Linux
- **Ubuntu/Debian**:
  ```bash
  sudo apt update
  sudo apt install tesseract-ocr libtesseract-dev
  ```
- **Arch Linux**:
  ```bash
  sudo pacman -S tesseract
  ```

### macOS
```bash
brew install tesseract
```

## Setup

```bash
# Install dependencies
pip install -e ".[dev]"

# Copy and configure environment
cp .env.example .env

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload --port 8000
```

## Run tests
```bash
pytest tests/unit/ -v
pytest tests/ -v --cov=app
```

## Generate migration
```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
```

## API Docs
Available at `http://localhost:8000/docs` (development only)

## Project Structure

```
job-optimizer-api/
├── app/
│   ├── agents/        # LangGraph pipeline (state, nodes, graph)
│   ├── api/           # FastAPI routers
│   │   └── v1/        # API Version 1 endpoints (auth, candidate, etc.)
│   ├── core/          # Config, DB, security, logging, exceptions
│   ├── factory/       # Service & Agent factories
│   ├── middleware/    # Custom FastAPI middlewares
│   ├── models/        # SQLAlchemy ORM models
│   ├── repositories/  # Data access layer (async repositories)
│   ├── schemas/       # Pydantic request/response schemas
│   ├── services/      # Business logic (analysis, parsing, etc.)
│   └── main.py        # Application entry point
├── migrations/        # Alembic database migrations
├── tests/             # Pytest suite (unit & integration)
├── logs/              # Application log files
├── uploads/           # Temporary folder for uploaded files
├── pyproject.toml     # Project dependencies & configuration
└── alembic.ini       # Alembic configuration
```
