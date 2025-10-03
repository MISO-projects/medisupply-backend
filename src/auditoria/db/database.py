import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

TEST_DATABASE_URL = "sqlite:///./test.db"

def get_database_uri():
    user = os.getenv("POSTGRES_USER", 'root')
    password = os.getenv("POSTGRES_PASSWORD", 'medisupply-pass')
    host = os.getenv("POSTGRES_HOST", "pg_db")
    port = os.getenv("POSTGRES_PORT", "5432")
    db_name = os.getenv("POSTGRES_DB", "medisupply-db")
    return f"postgresql://{user}:{password}@{host}:{port}/{db_name}"

if os.getenv("TESTING"):
    SQLALCHEMY_DATABASE_URL = TEST_DATABASE_URL
else:
    SQLALCHEMY_DATABASE_URL = get_database_uri()

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args=(
        {"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
    ),
    pool_size=20,
    max_overflow=30,
    pool_timeout=60,
    pool_recycle=1800
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
