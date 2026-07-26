import logging

from flask import Blueprint, request, jsonify
from backend.services.network_service import fetch_network

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
