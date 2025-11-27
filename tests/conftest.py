import os
from typing import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base, get_db
from app.main import app

# Use SQLite test DB
TEST_DATABASE_URL = "sqlite:///./test_db.sqlite3"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables for test DB
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)


def override_get_db() -> Generator:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


def get_client() -> TestClient:
    return TestClient(app)
