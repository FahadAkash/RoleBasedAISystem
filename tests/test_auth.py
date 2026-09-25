import pytest
from backend.auth import hash_password, verify_password, create_access_token

def test_password_hashing():
    password = "supersecretpassword"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrongpassword", hashed) is False

def test_create_access_token():
    data = {"sub": "testuser"}
    token = create_access_token(data)
    assert isinstance(token, str)
    assert len(token) > 20

def test_login_endpoint_success(client):
    response = client.post(
        "/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert response.status_code == 200
    json_data = response.json()
    assert "access_token" in json_data
    assert json_data["token_type"] == "bearer"
    assert json_data["role"] == "admin"

def test_login_endpoint_failure(client):
    response = client.post(
        "/auth/login",
        json={"username": "admin", "password": "wrongpassword"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username or password"

def test_login_endpoint_nonexistent_user(client):
    response = client.post(
        "/auth/login",
        json={"username": "nobody", "password": "nopassword"},
    )
    assert response.status_code == 401
