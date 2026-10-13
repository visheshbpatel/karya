
from datetime import datetime, timedelta, timezone

import jwt
from fastapi.testclient import TestClient

from main import app
from database import get_db
from auth import get_current_user, SECRET_KEY, ALGORITHM


def test_todos_reject_missing_token(client):
    app.dependency_overrides.pop(get_current_user, None)

    try:
        response = client.get("/todos")
        assert response.status_code == 401
    finally:
        # Restore the fixture's dependency override for cleanup.
        app.dependency_overrides[get_current_user] = (
            client._test_current_user_override
        )


def test_todos_reject_invalid_token(client):
    app.dependency_overrides.pop(get_current_user, None)

    try:
        response = client.get(
            "/todos",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code == 401
    finally:
        app.dependency_overrides[get_current_user] = (
            client._test_current_user_override
        )


def test_expired_token_is_rejected(client):
    app.dependency_overrides.pop(get_current_user, None)

    expired_token = jwt.encode(
        {
            "sub": str(client.test_user_id),
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

    try:
        response = client.get(
            "/todos",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert response.status_code == 401
    finally:
        app.dependency_overrides[get_current_user] = (
            client._test_current_user_override
        )
