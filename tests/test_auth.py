
from fastapi.testclient import TestClient
from sqlalchemy import select

from main import app
from database import User, get_db
from auth import get_current_user


def test_register_user(client: TestClient):
    response = client.post(
        "/auth/register",
        json={
            "first_name": "Alice",
            "last_name": "Smith",
            "username": "alice",
            "email": "alice@example.com",
            "password": "securepass123",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "alice"
    assert data["email"] == "alice@example.com"
    assert "password" not in data
    assert "password_hash" not in data


def test_login_with_username(client: TestClient):
    response = client.post(
        "/auth/login",
        json={
            "identifier": "testuser",
            "password": "test-password-123",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]


def test_login_with_invalid_password(client: TestClient):
    response = client.post(
        "/auth/login",
        json={
            "identifier": "testuser",
            "password": "wrong-password",
        },
    )

    assert response.status_code == 401


def test_login_with_unknown_user(client: TestClient):
    response = client.post(
        "/auth/login",
        json={
            "identifier": "unknown-user",
            "password": "securepass123",
        },
    )

    assert response.status_code == 401


def test_todo_requires_authentication():
    app.dependency_overrides.pop(get_current_user, None)

    try:
        with TestClient(app) as test_client:
            response = test_client.get("/todos")
            assert response.status_code == 401
    finally:
        # The client fixture will set up its overrides when used.
        app.dependency_overrides.clear()


def test_login_with_email(client: TestClient):
    response = client.post(
        "/auth/login",
        json={
            "identifier": "testuser@example.com",
            "password": "test-password-123",
        },
    )

    assert response.status_code == 200
    assert response.json()["access_token"]