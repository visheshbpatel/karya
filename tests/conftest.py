import pytest
from datetime import datetime, timedelta, timezone
import routes
from fastapi.testclient import TestClient
from fastapi import Depends
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from main import app
from database import Base, get_db, User
from auth import get_current_user
from security import hash_password



@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )

    Base.metadata.create_all(bind=engine)

    with TestingSessionLocal() as db:
        test_user = User(
        first_name="Test",
        last_name="User",
        username="testuser",
        email="testuser@example.com",
        password_hash=hash_password("test-password-123"),
        is_verified=True,
    )
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        test_user_id = test_user.id

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    def override_get_current_user(
        db: Session = Depends(get_db),
    ):
        return db.get(User, test_user_id)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    try:
        with TestClient(app) as test_client:
            test_client.test_user_id = test_user_id
            test_client.TestingSessionLocal = TestingSessionLocal
            test_client._test_current_user_override = override_get_current_user
            yield test_client
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
