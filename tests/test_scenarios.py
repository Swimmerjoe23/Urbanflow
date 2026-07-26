def test_create_and_get_scenario(client, simple_graph):
    resp = client.post("/api/scenarios/", json={
        "name": "Nairobi CBD",
        "description": "Test scenario",
        "bbox": [-1.29, 36.81, -1.28, 36.82],
        "graph_data": simple_graph,
    })
    assert resp.status_code == 201
    scenario_id = resp.get_json()["id"]

    resp = client.get(f"/api/scenarios/{scenario_id}")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["name"] == "Nairobi CBD"
    assert body["graph_data"]["nodes"][0]["id"] == "A"


def test_create_scenario_duplicate_name_returns_409(client, simple_graph):
    payload = {"name": "Dup Scenario", "bbox": None, "graph_data": simple_graph}
    first = client.post("/api/scenarios/", json=payload)
    assert first.status_code == 201
    second = client.post("/api/scenarios/", json=payload)
    assert second.status_code == 409


def test_create_scenario_missing_name_returns_400(client, simple_graph):
    resp = client.post("/api/scenarios/", json={"graph_data": simple_graph})
    assert resp.status_code == 400


def test_create_scenario_invalid_bbox_returns_400(client, simple_graph):
    resp = client.post("/api/scenarios/", json={
        "name": "Bad Bbox", "bbox": [200, 0, 0, 0], "graph_data": simple_graph,
    })
    assert resp.status_code == 400


def test_get_nonexistent_scenario_returns_404(client):
    resp = client.get("/api/scenarios/9999")
    assert resp.status_code == 404


def test_update_scenario_rename(client, simple_graph):
    created = client.post("/api/scenarios/", json={
        "name": "Original Name", "graph_data": simple_graph,
    }).get_json()

    resp = client.put(f"/api/scenarios/{created['id']}", json={"name": "New Name"})
    assert resp.status_code == 200

    fetched = client.get(f"/api/scenarios/{created['id']}").get_json()
    assert fetched["name"] == "New Name"


def test_delete_scenario(client, simple_graph):
    created = client.post("/api/scenarios/", json={
        "name": "To Delete", "graph_data": simple_graph,
    }).get_json()

    resp = client.delete(f"/api/scenarios/{created['id']}")
    assert resp.status_code == 200

    assert client.get(f"/api/scenarios/{created['id']}").status_code == 404


def test_list_scenarios(client, simple_graph):
    client.post("/api/scenarios/", json={"name": "Listed One", "graph_data": simple_graph})
    resp = client.get("/api/scenarios/")
    assert resp.status_code == 200
    names = [s["name"] for s in resp.get_json()]
    assert "Listed One" in names
