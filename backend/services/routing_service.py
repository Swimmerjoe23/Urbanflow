import networkx as nx
import math
from backend.services.network_service import dict_to_graph


def _haversine(lat1, lon1, lat2, lon2) -> float:
    """Straight-line distance in metres between two lat/lon points."""
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi  = math.radians(lat2 - lat1)
    dlam  = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def find_nearest_node(G: nx.MultiDiGraph, lat: float, lon: float) -> str:
    """Return the node ID closest to (lat, lon)."""
    best_node, best_dist = None, float("inf")
    for node_id, data in G.nodes(data=True):
        d = _haversine(lat, lon, data["y"], data["x"])
        if d < best_dist:
            best_dist = d
            best_node = node_id
    return best_node


def run_dijkstra(graph_data: dict, origin_lat: float, origin_lon: float,
                 dest_lat: float, dest_lon: float, weight: str = "length") -> dict:
    """
    Shortest path using Dijkstra's algorithm.
    weight: 'length' (metres) or 'travel_time' (seconds)
    """
    G = dict_to_graph(graph_data)
    origin = find_nearest_node(G, origin_lat, origin_lon)
    dest   = find_nearest_node(G, dest_lat,   dest_lon)

    try:
        path = nx.dijkstra_path(G, origin, dest, weight=weight)
        cost = nx.dijkstra_path_length(G, origin, dest, weight=weight)
    except nx.NetworkXNoPath:
        return {"error": "No path found between the selected points."}

    return _path_response(G, path, cost, weight, "dijkstra")


def run_astar(graph_data: dict, origin_lat: float, origin_lon: float,
              dest_lat: float, dest_lon: float, weight: str = "length") -> dict:
    """
    Shortest path using the A* algorithm with a haversine heuristic.
    """
    G = dict_to_graph(graph_data)
    origin = find_nearest_node(G, origin_lat, origin_lon)
    dest   = find_nearest_node(G, dest_lat,   dest_lon)

    dest_lat_coord = G.nodes[dest]["y"]
    dest_lon_coord = G.nodes[dest]["x"]

    def heuristic(u, v):
        u_lat = G.nodes[u]["y"]
        u_lon = G.nodes[u]["x"]
        return _haversine(u_lat, u_lon, dest_lat_coord, dest_lon_coord)

    try:
        path = nx.astar_path(G, origin, dest, heuristic=heuristic, weight=weight)
        cost = sum(
            min(d.get(weight, 0) for d in G[u][v].values())
            for u, v in zip(path[:-1], path[1:])
        )
    except nx.NetworkXNoPath:
        return {"error": "No path found between the selected points."}

    return _path_response(G, path, cost, weight, "astar")


def _path_response(G, path, cost, weight, algorithm) -> dict:
    """Build the API response dict for a computed path."""
    coordinates = [
        {"lat": G.nodes[n]["y"], "lon": G.nodes[n]["x"]}
        for n in path
    ]
    return {
        "algorithm":    algorithm,
        "weight":       weight,
        "node_count":   len(path),
        "total_length_m":  cost if weight == "length" else None,
        "total_time_s":    cost if weight == "travel_time" else None,
        "coordinates":  coordinates,
        "node_ids":     [str(n) for n in path],
    }
