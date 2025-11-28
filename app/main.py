from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database.connection import init_db
from app.auth.routes import router as auth_router
from app.admin.routes import router as admin_router
from app.scheduler.routes import router as scheduler_router
from app.crew.routes import router as crew_router
from app.engineer.routes import router as engineer_router


app = FastAPI(
    title="AeroSync API",
    description="Backend API for AeroSync",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(scheduler_router)
app.include_router(crew_router)
app.include_router(engineer_router)

@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    """
    return {"status": "healthy", "message": "AeroSync API is running"}


@app.get("/")
async def root():
    """
    Root endpoint.
    """
    return {
        "message": "Welcome to AeroSync API",
        "health": "/health"
    }

