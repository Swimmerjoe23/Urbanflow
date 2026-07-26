def test_predict_happy_path(client, simple_graph):
    resp = client.post("/api/traffic/predict", json={
        "graph": simple_graph, "hour": 8, "day_of_week": 0,
    })
    assert resp.status_code == 200
    body = resp.get_json()
    assert len(body["predictions"]) == len(simple_graph["edges"])
    assert "insights" in body


def test_predict_missing_graph_returns_400(client):
    resp = client.post("/api/traffic/predict", json={"hour": 8})
    assert resp.status_code == 400


def test_predict_invalid_hour_returns_400(client, simple_graph):
    resp = client.post("/api/traffic/predict", json={
        "graph": simple_graph, "hour": 99, "day_of_week": 0,
    })
    assert resp.status_code == 400


def test_predict_non_numeric_hour_returns_400_not_500(client, simple_graph):
    resp = client.post("/api/traffic/predict", json={
        "graph": simple_graph, "hour": "not-a-number",
    })
    assert resp.status_code == 400
