# AgentWatch Backend

AI-powered autonomous agent observability and governance platform — backend API.

---

## Tech Stack

| Layer       | Technology                          |
|-------------|-------------------------------------|
| Framework   | FastAPI (Python 3.12)               |
| ORM         | SQLAlchemy 2.0 (async)              |
| Database    | PostgreSQL 16                       |
| Migrations  | Alembic                             |
| Auth        | JWT (access + refresh tokens)       |
| Validation  | Pydantic v2                         |
| Container   | Docker + docker-compose             |
| Logging     | Structured JSON logging             |

---

## Project Structure

```
backend/
├── app/
│   ├── api/           # Route handlers (auth, projects, sessions, reports, health)
│   ├── core/          # Configuration, security, logging
│   ├── db/            # Database session and engine
│   ├── models/        # SQLAlchemy ORM models
│   ├── schemas/       # Pydantic v2 request/response schemas
│   ├── services/      # Business logic layer
│   ├── middleware/     # CORS, request logging, error handlers
│   ├── utils/         # Shared utilities
│   └── main.py        # FastAPI app factory
├── tests/             # pytest test suite
├── alembic/           # Database migrations
├── alembic.ini
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env
```

---

## Quick Start

### Prerequisites

- Python 3.12+
- Docker & Docker Compose (or a running PostgreSQL 16 instance)

### 1. Clone & environment

```bash
cp .env.example .env
# Edit .env if needed
```

### 2. Run with Docker (recommended)

```bash
docker compose up --build
```

The API will be available at `http://localhost:8000`.

### 3. Run locally

```bash
python -m venv venv
source venv/bin/activate   # Linux/Mac
# venv\Scripts\Activate.ps1  # Windows

pip install -r requirements.txt

# Ensure PostgreSQL is running and DATABASE_URL in .env is correct
alembic upgrade head

uvicorn app.main:app --reload
```

---

## API Endpoints

### Health
| Method | Path     | Description          |
|--------|----------|----------------------|
| GET    | `/health`| Health check         |

### Authentication
| Method | Path            | Description          |
|--------|-----------------|----------------------|
| POST   | `/auth/register`| Register new user    |
| POST   | `/auth/login`   | Login, get tokens    |
| POST   | `/auth/refresh` | Refresh access token |

### Projects
| Method | Path              | Description          |
|--------|-------------------|----------------------|
| GET    | `/projects`       | List user's projects |
| POST   | `/projects`       | Create project       |
| GET    | `/projects/{id}`  | Get project by ID    |
| PUT    | `/projects/{id}`  | Update project       |
| DELETE | `/projects/{id}`  | Delete project       |

### Research Sessions
| Method | Path              | Description          |
|--------|-------------------|----------------------|
| GET    | `/sessions`       | List sessions        |
| POST   | `/sessions`       | Create session       |
| GET    | `/sessions/{id}`  | Get session by ID    |

### Reports
| Method | Path              | Description          |
|--------|-------------------|----------------------|
| GET    | `/reports`        | List reports         |
| POST   | `/reports`        | Create report        |

---

## Authentication

All protected endpoints require a Bearer token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

- Access tokens expire in 30 minutes
- Refresh tokens expire in 7 days
- Use `/auth/refresh` to obtain a new token pair

### User Roles

| Role         | Permissions                        |
|--------------|------------------------------------|
| `admin`      | Full access                        |
| `researcher` | Create and manage own projects     |
| `viewer`     | Read-only access                   |

---

## Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "description"

# Apply all pending migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1
```

---

## Running Tests

```bash
pytest -v
```

---

## API Documentation

Once the server is running:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Environment Variables

| Variable              | Default                                    | Description                    |
|-----------------------|--------------------------------------------|--------------------------------|
| `DATABASE_URL`        | `postgresql+asyncpg://...`                 | PostgreSQL connection string   |
| `SECRET_KEY`          | `change-me-in-production`                  | JWT signing secret             |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30`                                | Access token TTL               |
| `REFRESH_TOKEN_EXPIRE_DAYS`    | `7`                                 | Refresh token TTL              |
| `ALLOWED_ORIGINS`     | `["http://localhost:3000"]`                | CORS origins                   |
| `LOG_LEVEL`           | `INFO`                                     | Logging level                  |
| `DEBUG`               | `false`                                    | Debug mode                     |
