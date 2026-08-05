"""Seed additional demo scenarios into the real instance database.

Fetches the real road network for each named Nairobi area already offered as a
quick-pick in the UI, then saves several named scenario variants per area so
the Compare tab has realistic saved data to demo. Run once from the project
root:

    python scripts/seed_scenarios.py

Safe to re-run: scenario names that already exist are skipped. Each area's
network is fetched from OpenStreetMap only once and reused across its variants.
"""
import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.network_service import fetch_network

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "instance", "urbanflow.db")

# name -> [south, west, north, east], matching the quick-pick chips in index.html
AREAS = {
    "CBD": [-1.2921, 36.8219, -1.2721, 36.8419],
    "Westlands": [-1.2634, 36.7896, -1.2434, 36.8096],
    "Kibera": [-1.3100, 36.7700, -1.2900, 36.7900],
    "Kasarani": [-1.2500, 36.8500, -1.2300, 36.8700],
    "South B": [-1.3200, 36.8200, -1.3000, 36.8400],
    "Parklands": [-1.2700, 36.8100, -1.2500, 36.8300],
}

VARIANTS = [
    ("Baseline", "Initial fetch of the current road network for this area, used as a reference point for later comparisons."),
    ("Morning Peak Review", "Saved while reviewing predicted congestion during the 7-9am morning peak."),
    ("Evening Peak Review", "Saved while reviewing predicted congestion during the 5-7pm evening peak."),
    ("Alternate Route Study", "Saved while comparing an alternate route against the default shortest path."),
]


def main():
    if not os.path.exists(DB_PATH):
        print(f"No database found at {DB_PATH}. Run the app once first so it can be initialised.")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    inserted, skipped = [], []
    for area_name, bbox in AREAS.items():
        graph = None  # fetch lazily, only if at least one variant for this area is missing
        for suffix, description in VARIANTS:
            name = f"{area_name} {suffix}"
            existing = conn.execute("SELECT id FROM scenarios WHERE name = ?", (name,)).fetchone()
            if existing:
                skipped.append(name)
                continue
            if graph is None:
                south, west, north, east = bbox
                print(f"Fetching road network for {area_name}...")
                graph = fetch_network(south=south, west=west, north=north, east=east)
                print(f"  {len(graph['nodes'])} nodes / {len(graph['edges'])} edges")
            conn.execute(
                "INSERT INTO scenarios (name, description, bbox, graph_data) VALUES (?, ?, ?, ?)",
                (name, description, json.dumps(bbox), json.dumps(graph)),
            )
            inserted.append(name)
        conn.commit()

    total = conn.execute("SELECT COUNT(*) AS n FROM scenarios").fetchone()["n"]
    conn.close()

    print(f"\nInserted {len(inserted)} new scenarios:")
    for name in inserted:
        print(f"  {name}")
    if skipped:
        print(f"Skipped {len(skipped)} already-existing scenario names: {', '.join(skipped)}")
    print(f"Total scenarios in {DB_PATH} now: {total}")


if __name__ == "__main__":
    main()
