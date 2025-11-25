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
    
    #todo: add production cors origins whilee deploying
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:3001"]
    
    cookie_secure: bool = False
    cookie_httponly: bool = True
    cookie_samesite: str = "lax"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

