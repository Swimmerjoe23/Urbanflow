import osmnx as ox
import networkx as nx
import json
import requests

_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
_USER_AGENT = "OnlineRoadNetworkTrafficPlanner-CapstoneProject/1.0"


def search_places(query: str, limit: int = 6) -> list:
    """
    Search for places by name using OSM's Nominatim geocoder, biased to
    Kenya since this tool is built around Nairobi. Returns a list of
    candidate matches (each with its own bounding box) for autocomplete
    style suggestions, rather than resolving to a single "best" place.
    """
    resp = requests.get(
        _NOMINATIM_URL,
        params={
            "q": query,
            "format": "json",
            "limit": limit,
            "addressdetails": 0,
            "countrycodes": "ke",
        },
        headers={"User-Agent": _USER_AGENT},
        timeout=8,
    )
    resp.raise_for_status()

    places = []
    for r in resp.json():
        try:
            south, north, west, east = (float(v) for v in r["boundingbox"])
        except (KeyError, ValueError, TypeError):
            continue
        places.append({
            "south": south, "west": west, "north": north, "east": east,
            "display_name": r.get("display_name", query),
        })
    return places


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
    if "nodes" not in data or "edges" not in data:
        raise KeyError("graph data must contain 'nodes' and 'edges'")

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
