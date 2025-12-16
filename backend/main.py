from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import morphology, etymology, phonetics, srs, glossing, production, curriculum, ingest
from core.config import settings
from core.database import engine, Base
from core.logging import configure_logging, get_logger
from core.middleware import RequestLoggingMiddleware, SlowRequestMiddleware
from core.errors import register_error_handlers

# Initialize logging before anything else
configure_logging(
    level=settings.LOG_LEVEL,
    json_logs=settings.LOG_JSON,
    log_sql=settings.LOG_SQL,
)

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("startup", message="Lingua API starting up")
    
    # Database initialization
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        log.info("database_connected", message="Database tables initialized")
    except Exception as e:
        log.warning("database_unavailable", error=str(e), message="App starting without database")
    
    yield
    
    # Shutdown
    log.info("shutdown", message="Lingua API shutting down")
    try:
        await engine.dispose()
        log.debug("database_disposed", message="Database connections closed")
    except Exception:
        pass


app = FastAPI(
    title="Lingua API",
    description="Advanced language learning platform with morphological pattern recognition, etymology-first acquisition, and phonological awareness training",
    version="0.1.0",
    lifespan=lifespan,
)

# Register structured error handlers
register_error_handlers(app)

# Middleware (order matters: last added = first executed)
app.add_middleware(SlowRequestMiddleware, slow_threshold_ms=1000)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers

app.include_router(morphology.router, prefix="/api/morphology", tags=["morphology"])
app.include_router(etymology.router, prefix="/api/etymology", tags=["etymology"])
app.include_router(phonetics.router, prefix="/api/phonetics", tags=["phonetics"])
app.include_router(srs.router, prefix="/api/srs", tags=["srs"])
app.include_router(glossing.router, prefix="/api/glossing", tags=["glossing"])
app.include_router(production.router, prefix="/api/production", tags=["production"])
app.include_router(curriculum.router, prefix="/api/curriculum", tags=["curriculum"])
app.include_router(ingest.router, prefix="/api/ingest", tags=["ingest"])


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "0.1.0"}


if __name__ == "__main__":
    import uvicorn
    
    log.info("server_config", host=settings.BACKEND_HOST, port=settings.BACKEND_PORT, debug=settings.APP_DEBUG)
    uvicorn.run(
        "main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=settings.APP_DEBUG,
        log_config=None,  # Disable uvicorn's default logging, we handle it
    )

