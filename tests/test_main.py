from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_home(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to Karya"}


def test_create_todo(client):
    response = client.post(
        "/todo",
        json = {"task":"learn pytest"}
    )

    assert response.status_code == 201

    data = response.json()
    assert data["id"] == 1
    assert data["task"] == "learn pytest"
    assert data["completed"] is False


def test_get_todo(client):
    create_response = client.post(
        "/todo",
        json = {"task":"learn pytest"}
    )

    todo_id = create_response.json()["id"]

    response = client.get(
        f"/todo/{todo_id}"
    )

    assert response.status_code == 200

    data = response.json()
    assert data['id'] == todo_id
    assert data['task'] == "learn pytest"
    assert data['completed'] is False


def test_get_todos(client):
    client.post(
        "/todo",
        json = {"task":"learn pytest"}
    )
    client.post(
        "/todo",
        json = {"task":"learn fastapi"}
    )

    response = client.get(
        "/todos"
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 2

    assert data[0]['id'] == 1
    assert data[0]['task'] == "learn pytest"
    assert data[0]['completed'] is False

    assert data[1]['id'] == 2
    assert data[1]['task'] == "learn fastapi"
    assert data[1]['completed'] is False


def test_todo_put(client):
    create_response = client.post(
        "/todo",
        json = {"task":"learn pytest"}
    )

    todo_id = create_response.json()["id"]


    response = client.put(
        f"/todo/{todo_id}",
        json = {
            "task": "learn pytest",
            "completed": True
        }
    )

    assert response.status_code == 200

    data = response.json()
    assert data['id'] == 1
    assert data['task'] == "learn pytest"
    assert data['completed'] is True



def test_todo_patch(client):
    create_response = client.post(
        "/todo",
        json = {"task":"learn pytest"}
    )

    todo_id = create_response.json()["id"]


    response = client.patch(
        f"/todo/{todo_id}",
        json = {
            "completed": True
        }
    )

    assert response.status_code == 200

    data = response.json()
    assert data['id'] == 1
    assert data['task'] == "learn pytest"
    assert data['completed'] is True


def test_todo_delete(client):
    create_response = client.post(
        "/todo",
        json = {"task":"learn pytest"}
    )

    todo_id = create_response.json()["id"]

    response = client.delete(
        f"/todo/{todo_id}"
    )

    assert response.status_code == 204
    assert response.content == b""

    response = client.get(f"/todo/{todo_id}")
    assert response.status_code == 404



def test_get_nonexistent_todo(client):
    response = client.get("/todo/999")

    assert response.status_code == 404


def test_put_nonexistent_todo(client):
    response = client.put(
        "/todo/999",
        json={
            "task": "Updated task",
            "completed": True,
        },
    )

    assert response.status_code == 404


def test_patch_nonexistent_todo(client):
    response = client.patch(
        "/todo/999",
        json={"completed": True},
    )

    assert response.status_code == 404


def test_delete_nonexistent_todo(client):
    response = client.delete("/todo/999")

    assert response.status_code == 404
