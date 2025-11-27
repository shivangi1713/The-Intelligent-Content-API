from fastapi import status

from .conftest import get_client


def test_signup_and_login_and_create_content():
    client = get_client()

    # 1) Signup
    signup_payload = {
        "email": "testuser@example.com",
        "password": "strongpassword",
    }
    r = client.post("/signup", json=signup_payload)
    assert r.status_code == status.HTTP_201_CREATED
    user = r.json()
    assert user["email"] == signup_payload["email"]
    assert "id" in user

    # 2) Login
    login_data = {
        "username": signup_payload["email"],  # OAuth2 uses "username"
        "password": signup_payload["password"],
    }
    r = client.post("/login", data=login_data)
    assert r.status_code == status.HTTP_200_OK
    token_data = r.json()
    assert "access_token" in token_data
    access_token = token_data["access_token"]

    headers = {"Authorization": f"Bearer {access_token}"}

    # 3) Create content
    content_payload = {
        "text": "This is a good day. I am very happy with the results."
    }
    r = client.post("/contents", json=content_payload, headers=headers)
    assert r.status_code == status.HTTP_201_CREATED
    content = r.json()
    assert content["text"] == content_payload["text"]
    assert content["summary"] is not None
    assert content["sentiment"] in ["Positive", "Negative", "Neutral"]

    # 4) List contents
    r = client.get("/contents", headers=headers)
    assert r.status_code == status.HTTP_200_OK
    items = r.json()
    assert len(items) >= 1
    assert any(item["id"] == content["id"] for item in items)
