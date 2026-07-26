from flask import Blueprint, request, jsonify
from backend.services.routing_service import run_dijkstra, run_astar

routing_bp = Blueprint("routing", __name__)


VALID_WEIGHTS = ("length", "travel_time")


def _extract_routing_params(body):
    required = ["graph", "origin_lat", "origin_lon", "dest_lat", "dest_lon"]
    missing = [k for k in required if k not in body]
    if missing:
        return None, None, None, None, None, None, f"Missing fields: {missing}"

    graph = body["graph"]
    if not isinstance(graph, dict) or "nodes" not in graph or "edges" not in graph:
        return None, None, None, None, None, None, \
            "Field 'graph' must be an object with 'nodes' and 'edges'."

    try:
        origin_lat = float(body["origin_lat"])
        origin_lon = float(body["origin_lon"])
        dest_lat   = float(body["dest_lat"])
        dest_lon   = float(body["dest_lon"])
    except (TypeError, ValueError):
        return None, None, None, None, None, None, \
            "origin_lat, origin_lon, dest_lat and dest_lon must be numbers."

    weight = body.get("weight", "length")   # 'length' or 'travel_time'
    if weight not in VALID_WEIGHTS:
        return None, None, None, None, None, None, \
            f"weight must be one of {VALID_WEIGHTS}"

    return graph, origin_lat, origin_lon, dest_lat, dest_lon, weight, None


@routing_bp.route("/dijkstra", methods=["POST"])
def dijkstra():
    """
    POST /api/routing/dijkstra
    Body: { graph, origin_lat, origin_lon, dest_lat, dest_lon, weight? }
    """
    body = request.get_json(silent=True) or {}
    graph, olat, olon, dlat, dlon, weight, err = _extract_routing_params(body)
    if err:
        return jsonify({"error": err}), 400
    try:
        result = run_dijkstra(graph, olat, olon, dlat, dlon, weight)
    except (KeyError, ValueError, TypeError) as e:
        return jsonify({"error": f"Malformed graph data: {e}"}), 400
    if "error" in result:
        return jsonify(result), 404
    return jsonify(result)


@routing_bp.route("/astar", methods=["POST"])
def astar():
    """
    POST /api/routing/astar
    Body: { graph, origin_lat, origin_lon, dest_lat, dest_lon, weight? }
    """
    body = request.get_json(silent=True) or {}
    graph, olat, olon, dlat, dlon, weight, err = _extract_routing_params(body)
    if err:
        return jsonify({"error": err}), 400
    try:
        result = run_astar(graph, olat, olon, dlat, dlon, weight)
    except (KeyError, ValueError, TypeError) as e:
        return jsonify({"error": f"Malformed graph data: {e}"}), 400
    if "error" in result:
        return jsonify(result), 404
    return jsonify(result)
