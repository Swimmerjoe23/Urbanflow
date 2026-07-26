from backend.services.traffic_service import predict_congestion, _score_to_colour


def test_predict_congestion_returns_one_result_per_edge(simple_graph):
    results = predict_congestion(simple_graph, hour=8, day_of_week=0)
    assert len(results) == len(simple_graph["edges"])
    for r in results:
        assert 0.0 <= r["congestion"] <= 1.0
        assert r["colour"] in ("#2ecc71", "#f39c12", "#e74c3c")


def test_predict_congestion_empty_edges_returns_empty_list():
    assert predict_congestion({"edges": []}, hour=8, day_of_week=0) == []


def test_score_to_colour_boundaries():
    assert _score_to_colour(0.0) == "#2ecc71"
    assert _score_to_colour(0.32) == "#2ecc71"
    assert _score_to_colour(0.33) == "#f39c12"
    assert _score_to_colour(0.65) == "#f39c12"
    assert _score_to_colour(0.66) == "#e74c3c"
    assert _score_to_colour(1.0) == "#e74c3c"


def test_predict_congestion_handles_unknown_highway_type(simple_graph):
    simple_graph["edges"][0]["highway"] = "some_unrecognised_type"
    results = predict_congestion(simple_graph, hour=8, day_of_week=0)
    assert len(results) == 2
