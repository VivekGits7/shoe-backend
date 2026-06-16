from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.database import Base, engine
from app.routes import activities, devices, sessions, users

Base.metadata.create_all(bind=engine)

with engine.begin() as conn:
    conn.execute(
        text(
            "ALTER TABLE activity_sessions "
            "ADD COLUMN IF NOT EXISTS user_id VARCHAR(100)"
        )
    )
    conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_activity_sessions_user_id "
            "ON activity_sessions (user_id)"
        )
    )

app = FastAPI(title="Activity Tracker API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?|https://([a-z0-9-]+\.)*vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(activities.router)
app.include_router(devices.router)
app.include_router(sessions.router)
app.include_router(users.router)


@app.get("/health")
def health():
    return {"status": "ok"}
