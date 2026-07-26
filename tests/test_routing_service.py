import pytest

from backend.services.routing_service import run_dijkstra, run_astar, find_nearest_node
from backend.services.network_service import dict_to_graph


def test_dijkstra_finds_shortest_path(simple_graph):
    result = run_dijkstra(simple_graph, 0.0, 0.0, 0.0018, 0.0, weight="length")
    assert result["algorithm"] == "dijkstra"
    assert result["node_ids"] == ["A", "B", "C"]
    assert result["total_length_m"] == pytest.approx(200.0)
    assert result["total_time_s"] is None


def test_astar_finds_same_path_as_dijkstra(simple_graph):
    result = run_astar(simple_graph, 0.0, 0.0, 0.0018, 0.0, weight="length")
    assert result["algorithm"] == "astar"
    assert result["node_ids"] == ["A", "B", "C"]
    assert result["total_length_m"] == pytest.approx(200.0)


def test_travel_time_weight_reports_time_not_length(simple_graph):
    result = run_dijkstra(simple_graph, 0.0, 0.0, 0.0018, 0.0, weight="travel_time")
    assert result["total_length_m"] is None
    assert result["total_time_s"] is not None
    assert result["total_time_s"] > 0


def test_no_path_between_disconnected_nodes():
    graph = {
        "nodes": [
            {"id": "A", "lat": 0.0, "lon": 0.0},
            {"id": "B", "lat": 1.0, "lon": 1.0},
        ],
        "edges": [],
    }
    result = run_dijkstra(graph, 0.0, 0.0, 1.0, 1.0)
    assert "error" in result


def test_find_nearest_node_empty_graph_raises():
    G = dict_to_graph({"nodes": [], "edges": []})
    with pytest.raises(ValueError):
        find_nearest_node(G, 0.0, 0.0)


def test_dict_to_graph_missing_keys_raises():
    with pytest.raises(KeyError):
        dict_to_graph({"nodes": []})
