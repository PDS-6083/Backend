from pydantic_settings import BaseSettings
from typing import List

#fastapi settings
class Settings(BaseSettings):
    database_url: str

    # JWT
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    
    # CORS origins - for development, include common frontend ports
    # When using credentials, you cannot use ["*"] - specify explicit origins
    # Example: ["http://localhost:3000", "http://localhost:8001", "http://localhost:5173"]
    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:8001", 
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8001",
        "http://127.0.0.1:5173",
    ]
    
    cookie_secure: bool = False
    cookie_httponly: bool = True
    cookie_samesite: str = "lax"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

