"""
Traffic prediction service.

Uses a Ridge regression model trained on synthetic historical traffic data.
The model predicts a congestion score (0.0 = free flow, 1.0 = gridlock)
for each road segment given: hour of day, day of week, road type, speed limit.

Replace synthetic profiles with real Nairobi traffic counts when available.
"""

import numpy as np
from sklearn.linear_model import Ridge

# ---------------------------------------------------------------------------
# Road type definitions
# ---------------------------------------------------------------------------
HIGHWAY_TYPES = [
    "motorway", "trunk", "primary", "secondary",
    "tertiary", "residential", "unclassified"
]

_CONGESTION_PROFILE = {
    "motorway":    [.1,.1,.1,.1,.1,.1,.3,.7,.9,.7,.5,.5,.5,.5,.5,.6,.8,.9,.7,.5,.3,.2,.1,.1],
    "trunk":       [.1,.1,.1,.1,.1,.1,.4,.8,.9,.7,.5,.5,.5,.5,.5,.7,.9,.9,.7,.5,.3,.2,.1,.1],
    "primary":     [.2,.1,.1,.1,.1,.2,.5,.9,.9,.6,.5,.5,.5,.6,.5,.7,.9,.9,.7,.5,.3,.2,.2,.1],
    "secondary":   [.2,.1,.1,.1,.1,.2,.4,.8,.8,.6,.5,.4,.4,.5,.5,.7,.8,.8,.6,.4,.3,.2,.2,.1],
    "tertiary":    [.2,.2,.1,.1,.1,.2,.4,.7,.7,.5,.4,.4,.4,.4,.4,.6,.7,.7,.5,.4,.3,.2,.2,.2],
    "residential": [.1,.1,.1,.1,.1,.1,.3,.6,.6,.4,.3,.3,.3,.3,.3,.5,.6,.6,.5,.3,.2,.2,.1,.1],
    "unclassified":[.2,.1,.1,.1,.1,.2,.3,.5,.5,.4,.3,.3,.3,.3,.3,.5,.5,.5,.4,.3,.2,.2,.2,.1],
}

# Numeric index for each highway type (used as model feature)
_HW_INDEX = {hw: i for i, hw in enumerate(HIGHWAY_TYPES)}


def _build_model():
    """Build and fit a Ridge regression model on synthetic data."""
    rng = np.random.default_rng(42)
    rows = []
    targets = []

    for day in range(7):
        for hour in range(24):
            for hw in HIGHWAY_TYPES:
                base = _CONGESTION_PROFILE.get(
                    hw, _CONGESTION_PROFILE["unclassified"]
                )[hour]
                if day >= 5:   # weekend
                    base *= 0.6
                noise = rng.normal(0, 0.04)
                congestion = float(np.clip(base + noise, 0.0, 1.0))
                # Features: hour, day, hw_index, speed_kph
                rows.append([hour, day, _HW_INDEX[hw], 50])
                targets.append(congestion)

    X = np.array(rows, dtype=float)
    y = np.array(targets)

    model = Ridge(alpha=1.0)
    model.fit(X, y)
    return model


# Train once at import time (fast — synthetic data only)
_MODEL = _build_model()


def predict_congestion(graph_data: dict, hour: int, day_of_week: int) -> list:
    """
    Return a congestion score for every edge in graph_data.

    Args:
        graph_data:   dict with 'edges' list from network_service
        hour:         0-23
        day_of_week:  0=Monday … 6=Sunday

    Returns:
        List of dicts: {edge_id, source, target, congestion, colour}
    """
    edges = graph_data.get("edges", [])
    if not edges:
        return []

    rows = []
    for edge in edges:
        hw = edge.get("highway", "unclassified")
        if isinstance(hw, list):
            hw = hw[0]
        if hw not in _HW_INDEX:
            hw = "unclassified"

        speed = edge.get("speed_kph", 50)
        try:
            speed = float(str(speed).split()[0])
        except (ValueError, TypeError):
            speed = 50.0

        rows.append([hour, day_of_week, _HW_INDEX[hw], speed])

    X = np.array(rows, dtype=float)
    scores = _MODEL.predict(X)
    scores = np.clip(scores, 0.0, 1.0)

    results = []
    for edge, score in zip(edges, scores):
        results.append({
            "edge_id":    edge["id"],
            "source":     edge["source"],
            "target":     edge["target"],
            "congestion": round(float(score), 3),
            "colour":     _score_to_colour(float(score)),
        })
    return results


def _score_to_colour(score: float) -> str:
    """Map a 0–1 congestion score to a hex colour (green → amber → red)."""
    if score < 0.33:
        return "#2ecc71"   # green
    elif score < 0.66:
        return "#f39c12"   # amber
    else:
        return "#e74c3c"   # red