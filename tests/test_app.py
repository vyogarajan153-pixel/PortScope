from app import app

def test_homepage():
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b"PortScope" in response.data

def test_health():
    client = app.test_client()

    response = client.get("/health")

    assert response.status_code == 200

def test_public_ip_is_blocked():
    client = app.test_client()

    response = client.post(
        "/api/scan",
        json={
            "target": "8.8.8.8",
            "ports": [80]
        }
    )

    assert response.status_code == 403
