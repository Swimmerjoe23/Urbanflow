import osmnx as ox
import networkx as nx
import json


def fetch_network(south: float, west: float, north: float, east: float) -> dict:
    """
    Download the road network for a bounding box from OpenStreetMap
    and return a JSON-serialisable dict of nodes and edges.
    """
    bbox = (north, south, east, west)   # osmnx order: N, S, E, W
    G = ox.graph_from_bbox(
        *bbox,
        network_type="drive",
        simplify=True
    )
    return graph_to_dict(G)


def graph_to_dict(G: nx.MultiDiGraph) -> dict:
    """Serialise a NetworkX graph to a plain dict for JSON transport."""
    nodes = []
    for node_id, data in G.nodes(data=True):
        nodes.append({
            "id":  str(node_id),
            "lat": data.get("y"),
            "lon": data.get("x"),
        })

    edges = []
    for u, v, key, data in G.edges(keys=True, data=True):
        edges.append({
            "id":          f"{u}_{v}_{key}",
            "source":      str(u),
            "target":      str(v),
            "length":      round(data.get("length", 0), 2),      # metres
            "speed_kph":   data.get("maxspeed", 50),
            "lanes":       data.get("lanes", 1),
            "highway":     data.get("highway", "unclassified"),
            "name":        data.get("name", ""),
            "oneway":      data.get("oneway", False),
        })

    return {"nodes": nodes, "edges": edges}


def dict_to_graph(data: dict) -> nx.MultiDiGraph:
    """Reconstruct a NetworkX graph from the serialised dict."""
    G = nx.MultiDiGraph()
    for node in data["nodes"]:
        G.add_node(node["id"], y=node["lat"], x=node["lon"])
    for edge in data["edges"]:
        speed = edge.get("speed_kph", 50)
        try:
            speed = float(str(speed).split()[0])  # handle "50 mph" strings
        except (ValueError, TypeError):
            speed = 50.0
        travel_time = (edge["length"] / 1000) / speed * 3600  # seconds
        G.add_edge(
            edge["source"], edge["target"],
            length=edge["length"],
            speed_kph=speed,
            travel_time=travel_time,
            lanes=edge.get("lanes", 1),
            highway=edge.get("highway", "unclassified"),
            name=edge.get("name", ""),
            oneway=edge.get("oneway", False),
        )
    return G
