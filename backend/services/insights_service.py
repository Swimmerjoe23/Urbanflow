"""
Insights service.

Rule-based analysis over a road network + its traffic prediction, surfaced
as a short, ranked list of plain-language findings (not a learned model —
deterministic checks over data the app already computes):

  - Bottleneck: a segment predicted congested but with only one lane.
  - Single point of failure: a junction whose removal would disconnect
    the network (a graph articulation point / cut vertex).
"""

import math
import statistics

import networkx as nx

from backend.services.network_service import dict_to_graph

# The congestion model's output range varies by network (it's a regression,
# not a fixed 0-1 spread), so "congested" is defined relative to this
# network's own predictions — mean + 1 stdev — with a floor so a network
# that's uniformly free-flowing doesn't get flagged over noise.
BOTTLENECK_MIN_CONGESTION_FLOOR = 0.35
BOTTLENECK_MAX_LANES = 1
MAX_INSIGHTS = 3


def _parse_lanes(raw):
    if isinstance(raw, list):
        raw = raw[0] if raw else 1
    try:
        return int(str(raw).split()[0])
    except (ValueError, TypeError):
        return 1


def _edge_label(edge):
    name = edge.get("name")
    if isinstance(name, list):
        name = name[0] if name else ""
    if name:
        return name
    hw = edge.get("highway", "road")
    if isinstance(hw, list):
        hw = hw[0] if hw else "road"
    return f"This {str(hw).replace('_', ' ')} segment"


def _midpoint(nodes_by_id, source_id, target_id):
    a, b = nodes_by_id.get(source_id), nodes_by_id.get(target_id)
    if not a or not b or a.get("lat") is None or b.get("lat") is None:
        return None
    return {"lat": (a["lat"] + b["lat"]) / 2, "lon": (a["lon"] + b["lon"]) / 2}


def _find_bottlenecks(graph_data, predictions, nodes_by_id, limit=2):
    scores = [p.get("congestion", 0) for p in predictions]
    if not scores:
        return []
    mean = statistics.fmean(scores)
    stdev = statistics.pstdev(scores) if len(scores) > 1 else 0
    threshold = max(mean + stdev, BOTTLENECK_MIN_CONGESTION_FLOOR)

    edges_by_id = {e["id"]: e for e in graph_data.get("edges", [])}
    candidates = []
    for p in predictions:
        if p.get("congestion", 0) < threshold:
            continue
        edge = edges_by_id.get(p.get("edge_id"))
        if not edge or _parse_lanes(edge.get("lanes", 1)) > BOTTLENECK_MAX_LANES:
            continue
        candidates.append((p["congestion"], edge))
    candidates.sort(key=lambda c: c[0], reverse=True)

    insights = []
    for congestion, edge in candidates[:limit]:
        loc = _midpoint(nodes_by_id, edge["source"], edge["target"])
        if not loc:
            continue
        lanes = _parse_lanes(edge.get("lanes", 1))
        insights.append({
            "type": "bottleneck",
            "severity": congestion,
            "edge_id": edge["id"],
            "location": loc,
            "title": "Likely bottleneck",
            "message": f"{_edge_label(edge)} is {round(congestion * 100)}% congested but has only 1 lane.",
            "why": "Predicted congestion is high while the road's lane capacity is low — demand likely exceeds what this segment can carry.",
            "suggestion": (
                f"Consider widening to {lanes + 1} lanes, or providing a parallel alternate route, "
                "to add capacity where demand is concentrated."
            ),
        })
    return insights


def _haversine_m(a, b):
    """Approximate distance in metres between two {lat, lon} points (small distances, flat-earth ok)."""
    dlat = (a["lat"] - b["lat"]) * 111000
    dlon = (a["lon"] - b["lon"]) * 111000 * math.cos(math.radians(a["lat"]))
    return math.hypot(dlat, dlon)


def _suggest_connector(UG, cut_node, nodes_by_id):
    """Removing `cut_node` splits UG into pieces; find the shortest possible new
    road (closest node pair across the two largest resulting pieces) that
    would reconnect them, so the suggestion is a concrete, buildable option
    rather than a generic "add redundancy" line."""
    H = UG.copy()
    H.remove_node(cut_node)
    components = [c for c in nx.connected_components(H) if len(c) > 0]
    if len(components) < 2:
        return None
    components.sort(key=len, reverse=True)
    comp_a, comp_b = components[0], components[1]

    best_dist, best_pair = None, None
    for na in comp_a:
        pa = nodes_by_id.get(na)
        if not pa or pa.get("lat") is None:
            continue
        for nb in comp_b:
            pb = nodes_by_id.get(nb)
            if not pb or pb.get("lat") is None:
                continue
            d = _haversine_m(pa, pb)
            if best_dist is None or d < best_dist:
                best_dist, best_pair = d, (na, nb)

    if best_dist is None:
        return None
    return (
        f"Consider adding a connector road (about {round(best_dist)}m) between the two halves of "
        "the network at their closest points, to remove this single point of failure."
    )


def _find_single_points_of_failure(graph_data, nodes_by_id, limit=1):
    G = dict_to_graph(graph_data)
    UG = nx.Graph(G.to_undirected())
    if UG.number_of_nodes() < 3:
        return []
    try:
        cut_nodes = list(nx.articulation_points(UG))
    except nx.NetworkXError:
        return []
    cut_nodes.sort(key=lambda n: UG.degree(n), reverse=True)

    insights = []
    for node_id in cut_nodes[:limit]:
        node = nodes_by_id.get(node_id)
        if not node or node.get("lat") is None:
            continue
        suggestion = _suggest_connector(UG, node_id, nodes_by_id)
        insights.append({
            "type": "single_point_of_failure",
            "severity": 1.0,
            "node_id": node_id,
            "location": {"lat": node["lat"], "lon": node["lon"]},
            "title": "No alternate route",
            "message": "This junction is the only connection between two parts of the network.",
            "why": "Removing this junction would split the road network into disconnected pieces (a cut vertex), so there's no redundant path around it.",
            "suggestion": suggestion or (
                "Consider adding a redundant road elsewhere in the network to remove this single "
                "point of failure."
            ),
        })
    return insights


def generate_insights(graph_data: dict, predictions: list) -> list:
    """Return up to MAX_INSIGHTS ranked, plain-language findings."""
    nodes_by_id = {n["id"]: n for n in graph_data.get("nodes", [])}
    insights = (
        _find_bottlenecks(graph_data, predictions, nodes_by_id, limit=2)
        + _find_single_points_of_failure(graph_data, nodes_by_id, limit=1)
    )
    insights.sort(key=lambda i: i["severity"], reverse=True)
    return insights[:MAX_INSIGHTS]
