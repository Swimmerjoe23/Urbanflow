from flask import Blueprint, request, jsonify
from backend.services.traffic_service import predict_congestion
from backend.services.insights_service import generate_insights

traffic_bp = Blueprint("traffic", __name__)


@traffic_bp.route("/predict", methods=["POST"])
def predict():
    """
    POST /api/traffic/predict
    Body: { graph, hour (0-23), day_of_week (0=Mon ... 6=Sun) }
    Returns: { predictions: [...], insights: [...] }
    """
    body = request.get_json(silent=True) or {}
    graph = body.get("graph")
    if not graph:
        return jsonify({"error": "Missing field: graph"}), 400

    hour        = int(body.get("hour", 8))
    day_of_week = int(body.get("day_of_week", 0))

    if not (0 <= hour <= 23):
        return jsonify({"error": "hour must be 0–23"}), 400
    if not (0 <= day_of_week <= 6):
        return jsonify({"error": "day_of_week must be 0–6"}), 400

    try:
        results = predict_congestion(graph, hour, day_of_week)
        insights = generate_insights(graph, results)
        return jsonify({"predictions": results, "insights": insights})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
