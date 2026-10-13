
from fastapi.testclient import TestClient


def register_and_login(client: TestClient, username: str, email: str):
    password = "secure-password-123"

    registration = client.post(
        "/auth/register",
        json={
            "first_name": username.capitalize(),
            "last_name": "Test",
            "username": username,
            "email": email,
            "password": password,
        },
    )
    assert registration.status_code == 201

    login = client.post(
        "/auth/login",
        json={
            "identifier": username,
            "password": password,
        },
    )
    assert login.status_code == 200

    return login.json()["access_token"]


def test_users_cannot_access_each_others_todos(client: TestClient):
    # Remove the fixture override so requests use real JWT verification.
    client.app.dependency_overrides.pop(
        __import__("auth").get_current_user, None
    )

    token_a = register_and_login(
        client, "alice", "alice@example.com"
    )
    token_b = register_and_login(
        client, "bob", "bob@example.com"
    )

    response = client.post(
        "/todo",
        json={"task": "Alice private task"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert response.status_code == 201
    todo_id = response.json()["id"]

    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Bob cannot read Alice's task.
    response = client.get(f"/todo/{todo_id}", headers=headers_b)
    assert response.status_code == 404

    # Bob cannot update Alice's task.
    response = client.patch(
        f"/todo/{todo_id}",
        json={"task": "Modified by Bob"},
        headers=headers_b,
    )
    assert response.status_code == 404

    # Bob cannot delete Alice's task.
    response = client.delete(f"/todo/{todo_id}", headers=headers_b)
    assert response.status_code == 404

    # Bob's task list must not contain Alice's task.
    response = client.get("/todos", headers=headers_b)
    assert response.status_code == 200
    assert all(todo["id"] != todo_id for todo in response.json())
