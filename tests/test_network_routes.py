def test_fetch_missing_fields_returns_400(client):
    resp = client.post("/api/network/fetch", json={"south": -1.3})
    assert resp.status_code == 400


def test_geocode_missing_query_returns_400(client):
    resp = client.post("/api/network/geocode", json={})
    assert resp.status_code == 400


def test_geocode_blank_query_returns_400(client):
    resp = client.post("/api/network/geocode", json={"query": "   "})
    assert resp.status_code == 400


def test_geocode_too_long_query_returns_400(client):
    resp = client.post("/api/network/geocode", json={"query": "a" * 201})
    assert resp.status_code == 400
