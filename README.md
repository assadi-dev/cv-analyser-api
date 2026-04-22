# Job Optimizer API

AI-powered personal job application tracker — FastAPI backend.

## Stack
- **Python 3.12** + FastAPI
- **SQLAlchemy 2.x** (async) + Alembic + PostgreSQL 16
- **LangGraph** + LangChain for AI agents
- **SSE** for real-time streaming
- **better-auth** token exchange bridge

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

## Architecture

```
app/
├── core/          # Config, DB, security, logging, exceptions, handlers
├── models/        # SQLAlchemy ORM models
├── schemas/       # Pydantic request/response schemas
├── repositories/  # Data access layer (base + domain repos)
├── api/v1/        # FastAPI routers (auth, candidatures, CVs, analyses, settings)
├── agents/        # LangGraph pipeline (state, nodes, graph)
└── services/      # Business logic (analyse, CV parser, provider)
```
