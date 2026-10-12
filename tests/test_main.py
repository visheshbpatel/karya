# tests for karya 

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
    assert data['id'] == todo_id
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
    assert data['id'] == todo_id
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


def test_create_todo_default_priority(client):
    response = client.post(
        "/todo",
        json={"task": "Study migrations"},
    )

    assert response.status_code == 201
    assert response.json()["priority"] == 0


def test_create_todo_custom_priority(client):
    response = client.post(
        "/todo",
        json={"task": "Finish Karya", "priority": 2},
    )

    assert response.status_code == 201
    assert response.json()["priority"] == 2


def test_patch_todo_priority(client):
    create_response = client.post(
        "/todo",
        json={"task": "Study migrations"},
    )
    todo_id = create_response.json()["id"]

    response = client.patch(
        f"/todo/{todo_id}",
        json={"priority": 2},
    )

    assert response.status_code == 200
    assert response.json()["priority"] == 2
    assert response.json()["task"] == "Study migrations"


def test_filter_todos_by_completed(client):
    client.post("/todo", json={"task": "Task A"})
    create_response = client.post(
        "/todo",
        json={"task": "Task B"},
    )
    todo_id = create_response.json()["id"]

    client.patch(
        f"/todo/{todo_id}",
        json={"completed": True},
    )

    response = client.get("/todos?completed=false")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["task"] == "Task A"


def test_filter_todos_by_priority(client):
    client.post("/todo", json={"task": "Task A", "priority": 1})
    client.post("/todo", json={"task": "Task B", "priority": 2})
    client.post("/todo", json={"task": "Task C", "priority": 2})

    response = client.get("/todos?priority=2")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(todo["priority"] == 2 for todo in data)


def test_filter_todos_combined(client):
    client.post(
        "/todo",
        json={"task": "Task A", "completed": False, "priority": 2},
    )
    create_response = client.post(
        "/todo",
        json={"task": "Task B"},
    )
    todo_id = create_response.json()["id"]

    client.patch(
        f"/todo/{todo_id}",
        json={"completed": True},
    )
    client.post(
        "/todo",
        json={"task": "Task C", "completed": False, "priority": 1},
    )

    response = client.get("/todos?completed=false&priority=2")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["task"] == "Task A"


def test_sort_todos(client):
    client.post("/todo", json={"task": "Task A", "priority": 3})
    client.post("/todo", json={"task": "Task B", "priority": 1})
    client.post("/todo", json={"task": "Task C", "priority": 2})

    response = client.get("/todos?sort_by=priority&order=asc")

    assert response.status_code == 200
    data = response.json()
    assert [todo["priority"] for todo in data] == [1, 2, 3]

    response = client.get("/todos?sort_by=priority&order=desc")

    assert response.status_code == 200
    data = response.json()
    assert [todo["priority"] for todo in data] == [3, 2, 1]


def test_invalid_sort_parameters(client):
    response = client.get("/todos?sort_by=name")
    assert response.status_code == 400

    response = client.get("/todos?order=invalid")
    assert response.status_code == 400


def test_search_todos(client):
    client.post("/todo", json={"task": "Learn Python"})
    client.post("/todo", json={"task": "Learn FastAPI"})
    client.post("/todo", json={"task": "Practice Python DSA"})

    response = client.get("/todos?search=Python")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all("Python" in todo["task"] for todo in data)


def test_search_todos_no_match(client):
    client.post("/todo", json={"task": "Learn Python"})

    response = client.get("/todos?search=Java")

    assert response.status_code == 200
    assert response.json() == []


def test_search_with_completed_filter(client):
    client.post("/todo", json={"task": "Learn Python"})
    create_response = client.post(
        "/todo",
        json={"task": "Practice Python"},
    )
    todo_id = create_response.json()["id"]

    client.patch(
        f"/todo/{todo_id}",
        json={"completed": True},
    )

    response = client.get("/todos?search=Python&completed=true")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["task"] == "Practice Python"


def test_todos_limit(client):
    for task in ["Task A", "Task B", "Task C"]:
        client.post("/todo", json={"task": task})

    response = client.get("/todos?limit=2")

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_todos_skip_and_limit(client):
    for task in ["Task A", "Task B", "Task C", "Task D"]:
        client.post("/todo", json={"task": task})

    response = client.get("/todos?skip=1&limit=2")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert [todo["task"] for todo in data] == ["Task B", "Task C"]


def test_invalid_pagination_parameters(client):
    response = client.get("/todos?skip=-1")
    assert response.status_code == 422

    response = client.get("/todos?limit=0")
    assert response.status_code == 422
