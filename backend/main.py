from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import morphology, etymology, phonetics, srs, glossing, production, auth
from core.config import settings
from core.database import engine, Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables if needed
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        print(f"Warning: Could not connect to database: {e}")
        print("App will start but database features won't work")
    yield
    # Shutdown: cleanup
    try:
        await engine.dispose()
    except Exception:
        pass


app = FastAPI(
    title="Lingua API",
    description="Advanced language learning platform with morphological pattern recognition, etymology-first acquisition, and phonological awareness training",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(morphology.router, prefix="/api/morphology", tags=["morphology"])
app.include_router(etymology.router, prefix="/api/etymology", tags=["etymology"])
app.include_router(phonetics.router, prefix="/api/phonetics", tags=["phonetics"])
app.include_router(srs.router, prefix="/api/srs", tags=["srs"])
app.include_router(glossing.router, prefix="/api/glossing", tags=["glossing"])
app.include_router(production.router, prefix="/api/production", tags=["production"])


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "0.1.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=settings.APP_DEBUG,
    )

