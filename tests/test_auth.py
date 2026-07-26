def test_protected_route_redirects_when_not_logged_in(client):
    resp = client.get("/app")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_login_wrong_password_shows_error(client):
    resp = client.post("/login", data={"username": "demo", "password": "wrong"})
    assert resp.status_code == 200
    assert b"Incorrect username or password" in resp.data


def test_login_correct_credentials_redirects_to_app(client):
    resp = client.post("/login", data={"username": "demo", "password": "urbanflow"})
    assert resp.status_code == 302
    assert "/app" in resp.headers["Location"]


def test_login_then_access_protected_route(client):
    client.post("/login", data={"username": "demo", "password": "urbanflow"})
    resp = client.get("/app")
    assert resp.status_code == 200


def test_login_rate_limited_after_repeated_failures(client):
    for _ in range(5):
        client.post("/login", data={"username": "demo", "password": "wrong"})
    resp = client.post("/login", data={"username": "demo", "password": "wrong"})
    assert resp.status_code == 429
