import logging

from flask import Blueprint, request, jsonify
from backend.services.network_service import fetch_network, search_places

network_bp = Blueprint("network", __name__)
logger = logging.getLogger(__name__)


@network_bp.route("/fetch", methods=["POST"])
def fetch():
    """
    POST /api/network/fetch
    Body: { "south": float, "west": float, "north": float, "east": float }
    Returns: { nodes: [...], edges: [...] }
    """
    body = request.get_json(silent=True) or {}
    required = ["south", "west", "north", "east"]
    missing = [k for k in required if k not in body]
    if missing:
        return jsonify({"error": f"Missing fields: {missing}"}), 400

    try:
        graph = fetch_network(
            south=float(body["south"]),
            west=float(body["west"]),
            north=float(body["north"]),
            east=float(body["east"]),
        )
        return jsonify(graph)
    except Exception:
        logger.exception("Failed to fetch network for bbox %s", body)
        return jsonify({"error": "Failed to fetch the road network for this area."}), 500


@network_bp.route("/geocode", methods=["POST"])
def geocode():
    """
    POST /api/network/geocode
    Body: { "query": "Njiru" }
    Returns: { results: [{ south, west, north, east, display_name }, ...] }
    """
    body = request.get_json(silent=True) or {}
    query = (body.get("query") or "").strip()
    if not query:
        return jsonify({"error": "Missing field: query"}), 400
    if len(query) > 200:
        return jsonify({"error": "query must be at most 200 characters"}), 400

    try:
        results = search_places(query)
    except Exception:
        logger.exception("Failed to search for query %r", query)
        return jsonify({"error": "Failed to search for that place."}), 502

    return jsonify({"results": results})
