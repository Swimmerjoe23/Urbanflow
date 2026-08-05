import json


def _login_admin(client):
    return client.post("/login", data={"username": "demo", "password": "urbanflow"})


def test_admin_api_requires_login(client):
    resp = client.get("/api/admin/users")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_admin_page_requires_login(client):
    resp = client.get("/admin")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_non_admin_is_forbidden(client):
    _login_admin(client)
    client.post("/api/admin/users", json={"username": "alice", "password": "plannerpw", "role": "planner"})
    client.get("/logout")

    client.post("/login", data={"username": "alice", "password": "plannerpw"})
    resp = client.get("/api/admin/users")
    assert resp.status_code == 403


def test_seeded_demo_users_have_correct_roles(client):
    _login_admin(client)
    resp = client.get("/api/admin/users")
    users = resp.get_json()
    assert len(users) == 2
    by_username = {u["username"]: u for u in users}
    assert by_username["demo"]["role"] == "admin"
    assert by_username["planner"]["role"] == "planner"
    assert "password_hash" not in by_username["demo"]


def test_create_and_delete_user(client):
    _login_admin(client)
    resp = client.post("/api/admin/users", json={"username": "bob", "password": "bobspassword", "role": "planner"})
    assert resp.status_code == 201
    user_id = resp.get_json()["id"]

    resp = client.get("/api/admin/users")
    assert len(resp.get_json()) == 3

    resp = client.delete(f"/api/admin/users/{user_id}")
    assert resp.status_code == 200
    resp = client.get("/api/admin/users")
    assert len(resp.get_json()) == 2


def test_create_user_validation(client):
    _login_admin(client)
    resp = client.post("/api/admin/users", json={"username": "", "password": "longenough", "role": "planner"})
    assert resp.status_code == 400

    resp = client.post("/api/admin/users", json={"username": "shortpw", "password": "short", "role": "planner"})
    assert resp.status_code == 400

    resp = client.post("/api/admin/users", json={"username": "badrole", "password": "longenough", "role": "root"})
    assert resp.status_code == 400


def test_duplicate_username_conflicts(client):
    _login_admin(client)
    resp = client.post("/api/admin/users", json={"username": "demo", "password": "longenough", "role": "planner"})
    assert resp.status_code == 409


def test_cannot_delete_last_admin(client):
    _login_admin(client)
    resp = client.get("/api/admin/users")
    demo_id = next(u["id"] for u in resp.get_json() if u["username"] == "demo")

    resp = client.delete(f"/api/admin/users/{demo_id}")
    assert resp.status_code == 400


def test_cannot_demote_last_admin(client):
    _login_admin(client)
    resp = client.get("/api/admin/users")
    demo_id = next(u["id"] for u in resp.get_json() if u["username"] == "demo")

    resp = client.put(f"/api/admin/users/{demo_id}", json={"role": "planner"})
    assert resp.status_code == 400


def test_demote_allowed_when_another_admin_exists(client):
    _login_admin(client)
    resp = client.post("/api/admin/users", json={"username": "second-admin", "password": "adminpassword", "role": "admin"})
    assert resp.status_code == 201

    resp = client.get("/api/admin/users")
    demo_id = next(u["id"] for u in resp.get_json() if u["username"] == "demo")

    resp = client.put(f"/api/admin/users/{demo_id}", json={"role": "planner"})
    assert resp.status_code == 200


def test_traffic_profile_get_shape(client):
    _login_admin(client)
    resp = client.get("/api/admin/traffic-profile")
    assert resp.status_code == 200
    profile = resp.get_json()
    assert set(profile.keys()) == {
        "motorway", "trunk", "primary", "secondary", "tertiary", "residential", "unclassified",
    }
    for values in profile.values():
        assert len(values) == 24
        assert all(0 <= v <= 1 for v in values)


def test_traffic_profile_update_and_predict(client):
    _login_admin(client)
    new_values = [0.9] * 24
    resp = client.put("/api/admin/traffic-profile", json={"motorway": new_values})
    assert resp.status_code == 200
    assert resp.get_json()["motorway"] == new_values

    graph = {
        "nodes": [{"id": "A", "lat": 0.0, "lon": 0.0}, {"id": "B", "lat": 0.001, "lon": 0.0}],
        "edges": [{
            "id": "A_B_0", "source": "A", "target": "B", "length": 100.0,
            "speed_kph": 50, "lanes": 1, "highway": "motorway", "name": "M1", "oneway": False,
        }],
    }
    resp = client.post("/api/traffic/predict", json={"graph": graph, "hour": 3, "day_of_week": 1})
    assert resp.status_code == 200
    congestion = resp.get_json()["predictions"][0]["congestion"]
    assert congestion > 0.55


def test_traffic_profile_reset(client):
    _login_admin(client)
    client.put("/api/admin/traffic-profile", json={"motorway": [0.05] * 24})
    resp = client.post("/api/admin/traffic-profile/reset")
    assert resp.status_code == 200
    assert resp.get_json()["motorway"] != [0.05] * 24


def test_traffic_profile_rejects_bad_values(client):
    _login_admin(client)
    resp = client.put("/api/admin/traffic-profile", json={"motorway": [1.5] * 24})
    assert resp.status_code == 400

    resp = client.put("/api/admin/traffic-profile", json={"motorway": [0.5] * 10})
    assert resp.status_code == 400

    resp = client.put("/api/admin/traffic-profile", json={"not-a-real-type": [0.5] * 24})
    assert resp.status_code == 400
