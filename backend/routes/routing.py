from flask import Blueprint, request, jsonify
from backend.services.routing_service import run_dijkstra, run_astar

routing_bp = Blueprint("routing", __name__)


def _extract_routing_params(body):
    required = ["graph", "origin_lat", "origin_lon", "dest_lat", "dest_lon"]
    missing = [k for k in required if k not in body]
    if missing:
        return None, None, None, None, None, None, f"Missing fields: {missing}"

    graph      = body["graph"]
    origin_lat = float(body["origin_lat"])
    origin_lon = float(body["origin_lon"])
    dest_lat   = float(body["dest_lat"])
    dest_lon   = float(body["dest_lon"])
    weight     = body.get("weight", "length")   # 'length' or 'travel_time'
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
    result = run_dijkstra(graph, olat, olon, dlat, dlon, weight)
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
    result = run_astar(graph, olat, olon, dlat, dlon, weight)
    if "error" in result:
        return jsonify(result), 404
    return jsonify(result)
