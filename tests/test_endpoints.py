import pytest

def get_auth_headers(client, username, password):
    response = client.post("/auth/login", json={"username": username, "password": password})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "running"

def test_admin_users_endpoint_success(client):
    headers = get_auth_headers(client, "admin", "admin123")
    response = client.get("/admin/users", headers=headers)
    assert response.status_code == 200
    users = response.json()
    assert isinstance(users, list)
    assert len(users) >= 1
    assert users[0]["username"] == "admin"

def test_admin_users_endpoint_forbidden(client):
    headers = get_auth_headers(client, "user_alice", "user123")
    response = client.get("/admin/users", headers=headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Requires one of: admin"

def test_chat_history_empty_initially(client):
    headers = get_auth_headers(client, "user_alice", "user123")
    response = client.get("/chat/history", headers=headers)
    assert response.status_code == 200
    assert response.json() == []

# We won't test the full /chat/ endpoint here directly without mocking Gemini/Jev 
# to avoid hitting real APIs. That will be done in another test file with proper mocks.
