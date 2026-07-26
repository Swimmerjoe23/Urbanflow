def test_dijkstra_happy_path(client, simple_graph):
    resp = client.post("/api/routing/dijkstra", json={
        "graph": simple_graph,
        "origin_lat": 0.0, "origin_lon": 0.0,
        "dest_lat": 0.0018, "dest_lon": 0.0,
    })
    assert resp.status_code == 200
    assert resp.get_json()["node_ids"] == ["A", "B", "C"]


def test_dijkstra_missing_fields_returns_400(client):
    resp = client.post("/api/routing/dijkstra", json={"graph": {"nodes": [], "edges": []}})
    assert resp.status_code == 400


def test_dijkstra_non_numeric_coordinates_returns_400_not_500(client, simple_graph):
    resp = client.post("/api/routing/dijkstra", json={
        "graph": simple_graph,
        "origin_lat": "not-a-number", "origin_lon": 0.0,
        "dest_lat": 0.0018, "dest_lon": 0.0,
    })
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_dijkstra_malformed_graph_returns_400_not_500(client):
    resp = client.post("/api/routing/dijkstra", json={
        "graph": {"not_nodes_or_edges": True},
        "origin_lat": 0.0, "origin_lon": 0.0,
        "dest_lat": 1.0, "dest_lon": 1.0,
    })
    assert resp.status_code == 400


def test_dijkstra_invalid_weight_returns_400(client, simple_graph):
    resp = client.post("/api/routing/dijkstra", json={
        "graph": simple_graph,
        "origin_lat": 0.0, "origin_lon": 0.0,
        "dest_lat": 0.0018, "dest_lon": 0.0,
        "weight": "not_a_real_weight",
    })
    assert resp.status_code == 400


def test_astar_happy_path(client, simple_graph):
    resp = client.post("/api/routing/astar", json={
        "graph": simple_graph,
        "origin_lat": 0.0, "origin_lon": 0.0,
        "dest_lat": 0.0018, "dest_lon": 0.0,
    })
    assert resp.status_code == 200
    assert resp.get_json()["node_ids"] == ["A", "B", "C"]
