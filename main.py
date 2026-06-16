from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from config import settings
from error import setup_error_handlers
from limiter import limiter
from logger import get_logger, setup_logging
from routers.activities import router as activities_router
from routers.devices import router as devices_router
from routers.sessions import router as sessions_router
from routers.users import router as users_router
from services.database import close_db_pool, create_db_pool

setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_pool()
    logger.info("Application started")
    yield
    await close_db_pool()
    logger.info("Application shut down")


app = FastAPI(
    title="Activity Tracker API",
    description="Tracks shoe/sandal activity sessions per user.",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    openapi_url="/openapi.json" if not settings.is_production else None,
)

# Rate limiter
app.state.limiter = limiter
setup_error_handlers(app)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# CORS
allowed_origins = ["*"] if not settings.is_production else [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?|https://([a-z0-9-]+\.)*vercel\.app",
    allow_credentials=allowed_origins != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(users_router)
app.include_router(activities_router)
app.include_router(devices_router)
app.include_router(sessions_router)


@app.get("/", tags=["Health"])
async def root():
    return {"message": "Activity Tracker API", "version": "2.0.0"}


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy", "service": "shoe-backend"}
