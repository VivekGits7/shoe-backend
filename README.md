# Backend — Activity Tracker API

FastAPI + SQLAlchemy + PostgreSQL backend for the Activity Tracker dashboard.

---

## Folder Structure

```
backend/
├── .env                    ← DB credentials (never commit)
├── requirements.txt        ← Python packages list
├── pyrefly.toml            ← IDE type-checker config
├── venv/                   ← Virtual environment
└── app/
    ├── __init__.py         ← Empty (Python package marker)
    ├── config.py           ← .env loader
    ├── database.py         ← DB connection setup
    ├── models.py           ← Table definition (ORM)
    ├── activities.py       ← Activity list constant
    ├── schemas.py          ← Request/response validation
    ├── main.py             ← FastAPI app entry point
    └── routes/
        ├── __init__.py     ← Empty (package marker)
        ├── activities.py   ← GET /api/activities
        └── sessions.py     ← POST/GET /api/sessions
```

---

## How to Run

### Step 1 — Open a terminal and go to backend folder

```bash
cd "/Users/diwakarbhatt/Documents/work 19 dashboard new/backend"
```

### Step 2 — Activate virtual environment

```bash
source venv/bin/activate
```

After this, your prompt shows `(venv)` prefix.

### Step 3 — Start the server

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

### Step 4 — Verify

Open in browser: **http://127.0.0.1:8000/docs** — Swagger UI shows all endpoints.

### Stop

Press `Ctrl + C` in the terminal.

---

## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/health` | Sanity check — backend is alive |
| GET | `/api/activities` | Dropdown options for frontend |
| POST | `/api/sessions` | Save a new activity session (Stop button) |
| GET | `/api/sessions?limit=N` | List recent sessions (history table) |

### `GET /api/activities`

Returns the list of valid activities for the dropdown.

**Response:**
```json
[
  {"value": "walking", "label": "Walking"},
  {"value": "running", "label": "Running"},
  {"value": "jumping", "label": "Jumping"},
  {"value": "cycling", "label": "Cycling"},
  {"value": "yoga",    "label": "Yoga"}
]
```

### `POST /api/sessions`

Saves an activity session.

**Request body:**
```json
{
  "user_name": "Diwakar",
  "activity": "running",
  "start_time": "2026-05-07T07:30:00Z",
  "end_time":   "2026-05-07T07:45:30Z"
}
```

**Validation:**
- `user_name`: 1–100 characters
- `activity`: must be one of the values from `/api/activities`
- `start_time`, `end_time`: ISO datetime in UTC
- `end_time` must be after `start_time` (else 400)
- `duration_seconds` is computed by the server, not the client

**Response (201 Created):**
```json
{
  "id": 1,
  "user_name": "Diwakar",
  "activity": "running",
  "start_time": "2026-05-07T07:30:00Z",
  "end_time":   "2026-05-07T07:45:30Z",
  "duration_seconds": 930,
  "created_at": "2026-05-07T06:45:40.772106Z"
}
```

### `GET /api/sessions?limit=20`

Returns recent sessions across all users, latest first.

**Query param:** `limit` (default 20, min 1, max 100)

**Response:** Array of session objects (same shape as POST response).

---

## File-by-File Explanation

### 1. `backend/.env`

```bash
POSTGRES_DB_HOST=72.60.220.164
POSTGRES_DB_PORT=6001
POSTGRES_DB=shoe-labling
POSTGRES_USER=kuberyauser
POSTGRES_PASSWORD=kuberayaisolutions@2026
```

DB credentials. **Never commit to git** — these are secrets.

---

### 2. `backend/requirements.txt`

```
fastapi==0.115.0
uvicorn[standard]==0.32.0
sqlalchemy==2.0.36
psycopg2-binary==2.9.10
pydantic==2.9.2
pydantic-settings==2.6.1
python-dotenv==1.0.1
```

Python packages with exact versions. Install with `pip install -r requirements.txt`.

| Package | Purpose |
|---------|---------|
| `fastapi` | Web framework for building REST APIs |
| `uvicorn` | ASGI server that runs FastAPI |
| `sqlalchemy` | ORM — Python objects ↔ SQL tables |
| `psycopg2-binary` | PostgreSQL driver used by SQLAlchemy |
| `pydantic` | Data validation (request body checks) |
| `pydantic-settings` | Loads settings from `.env` file |

---

### 3. `backend/app/__init__.py`

Empty file. Makes Python treat `app/` as a package, which lets you do `from app.config import ...`.

---

### 4. `backend/app/config.py`

```python
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    POSTGRES_DB_HOST: str
    POSTGRES_DB_PORT: int
    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str

    @property
    def database_url(self) -> str:
        user = quote_plus(self.POSTGRES_USER)
        password = quote_plus(self.POSTGRES_PASSWORD)
        return (
            f"postgresql+psycopg2://{user}:{password}"
            f"@{self.POSTGRES_DB_HOST}:{self.POSTGRES_DB_PORT}/{self.POSTGRES_DB}"
        )


settings = Settings()
```

**What it does:**
- `BaseSettings` auto-reads variables from `.env`.
- Type annotations (`str`, `int`) auto-convert values.
- `database_url` property builds the full Postgres connection string.
- `quote_plus()` URL-encodes the password, because the `@` character in the password would otherwise collide with the `user:pass@host` URL format.
- `settings = Settings()` creates a single instance imported by other files.

---

### 5. `backend/app/database.py`

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**Three key objects:**

1. **`engine`** — actual DB connection pool. `pool_pre_ping=True` checks the connection is alive before each query (handles idle disconnects).
2. **`SessionLocal`** — factory for creating DB sessions, one per request.
   - `autocommit=False` — must call `db.commit()` explicitly (safer).
   - `autoflush=False` — explicit control over when ORM sends data to DB.
3. **`Base`** — all ORM models inherit from this. SQLAlchemy uses it to know which tables to create.

**`get_db()`** — FastAPI dependency. For each request:
- Opens a session
- Yields it to the route handler
- Closes the session in `finally` after the request finishes

---

### 6. `backend/app/models.py`

```python
from sqlalchemy import Column, Integer, String, DateTime, Index
from sqlalchemy.sql import func

from app.database import Base


class ActivitySession(Base):
    __tablename__ = "activity_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_name = Column(String(100), nullable=False)
    activity = Column(String(50), nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    duration_seconds = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_activity_sessions_created_at", "created_at"),
    )
```

The **DB table represented as a Python class** (ORM model).

| Column | Type | Constraint | Purpose |
|--------|------|------------|---------|
| `id` | Integer | Primary key, auto-increment | Unique row ID |
| `user_name` | VARCHAR(100) | NOT NULL | User's name |
| `activity` | VARCHAR(50) | NOT NULL | walking/running/etc. |
| `start_time` | TIMESTAMPTZ | NOT NULL | UTC start time |
| `end_time` | TIMESTAMPTZ | NOT NULL | UTC end time |
| `duration_seconds` | Integer | NOT NULL | Computed duration |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Row insert time (set by Postgres) |

- `DateTime(timezone=True)` = Postgres `TIMESTAMPTZ` (stored in UTC).
- `Index(...)` on `created_at` makes history queries fast.

When the backend starts, `Base.metadata.create_all` (called in `main.py`) auto-creates this table if it doesn't exist.

---

### 7. `backend/app/activities.py`

```python
ACTIVITIES: list[dict[str, str]] = [
    {"value": "walking", "label": "Walking"},
    {"value": "running", "label": "Running"},
    {"value": "jumping", "label": "Jumping"},
    {"value": "cycling", "label": "Cycling"},
    {"value": "yoga", "label": "Yoga"},
]

ACTIVITY_VALUES: set[str] = {a["value"] for a in ACTIVITIES}
```

**Single source of truth** for the activity list.

- `ACTIVITIES` — the list returned by `GET /api/activities`.
- `ACTIVITY_VALUES` — set of valid values used by `schemas.py` for validation.

To add a new activity, just add an entry here — both validation and the API endpoint update automatically.

---

### 8. `backend/app/schemas.py`

```python
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.activities import ACTIVITY_VALUES


class SessionCreate(BaseModel):
    user_name: str = Field(min_length=1, max_length=100)
    activity: str
    start_time: datetime
    end_time: datetime

    @field_validator("activity")
    @classmethod
    def validate_activity(cls, v: str) -> str:
        if v not in ACTIVITY_VALUES:
            raise ValueError(
                f"activity must be one of: {sorted(ACTIVITY_VALUES)}"
            )
        return v


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_name: str
    activity: str
    start_time: datetime
    end_time: datetime
    duration_seconds: int
    created_at: datetime
```

**Pydantic models for request/response validation.**

- **`SessionCreate`** — request body for `POST /api/sessions`. FastAPI auto-validates:
  - `user_name`: 1–100 characters
  - `activity`: must be in `ACTIVITY_VALUES` (custom validator)
  - `start_time`, `end_time`: valid datetime
  - Invalid data → automatic `422 Unprocessable Entity`
- **`SessionOut`** — response shape. `from_attributes=True` lets FastAPI convert ORM objects directly to JSON.

**Models vs Schemas:**
- **Models** (`models.py`) = DB table shape
- **Schemas** (`schemas.py`) = API request/response shape

---

### 9. `backend/app/routes/__init__.py`

Empty package marker, like the parent `__init__.py`.

---

### 10. `backend/app/routes/activities.py`

```python
from fastapi import APIRouter
from pydantic import BaseModel

from app.activities import ACTIVITIES

router = APIRouter(prefix="/api/activities", tags=["activities"])


class ActivityOption(BaseModel):
    value: str
    label: str


@router.get("", response_model=list[ActivityOption])
def list_activities():
    return ACTIVITIES
```

Single endpoint — `GET /api/activities` — returns dropdown options.

- `APIRouter(prefix="/api/activities")` — all routes here are under this prefix.
- `tags=["activities"]` — Swagger UI groups them.
- `ActivityOption` enforces `{value, label}` response shape.
- `@router.get("")` — the path is `""`, combined with prefix it becomes `/api/activities`.

---

### 11. `backend/app/routes/sessions.py`

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ActivitySession
from app.schemas import SessionCreate, SessionOut

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", response_model=SessionOut, status_code=201)
def create_session(payload: SessionCreate, db: Session = Depends(get_db)):
    if payload.end_time <= payload.start_time:
        raise HTTPException(status_code=400, detail="end_time must be after start_time")

    duration = int((payload.end_time - payload.start_time).total_seconds())

    session = ActivitySession(
        user_name=payload.user_name.strip(),
        activity=payload.activity,
        start_time=payload.start_time,
        end_time=payload.end_time,
        duration_seconds=duration,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("", response_model=list[SessionOut])
def list_sessions(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return (
        db.query(ActivitySession)
        .order_by(ActivitySession.created_at.desc())
        .limit(limit)
        .all()
    )
```

**Two endpoints:**

#### `POST /api/sessions` — Save session
- `payload: SessionCreate` — FastAPI parses the request body and validates against `SessionCreate`. Invalid → 422 automatically.
- `db: Session = Depends(get_db)` — FastAPI injects a DB session from `get_db()`. Auto-closed after the request.
- **Manual check:** `end_time > start_time`, otherwise `400`.
- `duration` is computed server-side (don't trust the client).
- `db.add()` → stage the new row.
- `db.commit()` → write to DB.
- `db.refresh(session)` → reload from DB so `id` and `created_at` are populated.
- Return the ORM object — FastAPI converts it to JSON via `SessionOut`.

#### `GET /api/sessions?limit=20` — History list
- `limit`: query param, default 20, min 1, max 100.
- Query: order by `created_at` descending, take top N.
- Returns: list of sessions.

---

### 12. `backend/app/main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routes import activities, sessions

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Activity Tracker API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(activities.router)
app.include_router(sessions.router)


@app.get("/health")
def health():
    return {"status": "ok"}
```

**Application entry point.** When `uvicorn app.main:app` runs, this file executes:

1. **`Base.metadata.create_all(bind=engine)`** — creates the `activity_sessions` table if it doesn't exist.
2. **`app = FastAPI(...)`** — main FastAPI instance.
3. **`CORSMiddleware`** — frontend (browser) is on a different port (3000) from backend (8000). Browsers block cross-origin requests by default; this middleware allows them. The regex permits any port on `localhost` or `127.0.0.1`.
4. **`include_router(...)`** — registers both router files into the app.
5. **`/health`** — simple endpoint to check the server is alive.

---

### 13. `backend/pyrefly.toml`

```toml
project-includes = ["app"]
python-interpreter = "venv/bin/python"
```

Tells the IDE's type-checker (Pyrefly) where the venv is, so imports like `sqlalchemy.orm` resolve. No effect on running code.

---

## Request Flow (POST /api/sessions)

When the user clicks "Stop" in the browser:

```
1. Browser            → POST http://127.0.0.1:8000/api/sessions
                        body: { user_name, activity, start_time, end_time }

2. CORSMiddleware     → Origin check passes

3. routes/sessions.py → SessionCreate validates (Pydantic)
                        - activity check (schemas.py + activities.py)
                        - end_time > start_time check

4. get_db()           → Opens DB session

5. ActivitySession()  → ORM object created
                        db.add() → db.commit() → SQL INSERT

6. db.refresh()       → Reloads row from DB (id, created_at populated)

7. SessionOut         → Converted to JSON
                        Response: 201 Created + JSON body

8. get_db() finally   → Closes DB session
```

---

## Tech Stack

- **Python:** 3.12 (psycopg2-binary doesn't have a wheel for 3.9)
- **Framework:** FastAPI 0.115
- **ORM:** SQLAlchemy 2.0
- **DB:** PostgreSQL (remote, at `72.60.220.164:6001`)
- **Validation:** Pydantic 2
- **Server:** Uvicorn (with `--reload` in development)

---

## Adding a New Activity

1. Open [app/activities.py](app/activities.py).
2. Add a new entry to the `ACTIVITIES` list:
   ```python
   {"value": "swimming", "label": "Swimming"},
   ```
3. Save. With `--reload`, the backend picks it up automatically.
4. The frontend dropdown updates on next page load (it fetches from `/api/activities`).

No code changes needed elsewhere — `ACTIVITY_VALUES` and the schema validation pick up the new entry automatically.
