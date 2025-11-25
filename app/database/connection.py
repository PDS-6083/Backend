from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.config import settings
from app.database.models import Base

# Ensure database URL uses PyMySQL driver
database_url = settings.database_url
if database_url.startswith("mysql://") or database_url.startswith("mysql+mysqldb://"):
    database_url = database_url.replace("mysql://", "mysql+pymysql://").replace("mysql+mysqldb://", "mysql+pymysql://")

connect_args = {
    "charset": "utf8mb4",
    "connect_timeout": 10,
}

engine = create_engine(
    database_url,
    pool_pre_ping=True,
    echo=settings.debug,
    connect_args=connect_args if "pymysql" in database_url else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """
    Dependency function to get database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database tables.
    """
    Base.metadata.create_all(bind=engine)

