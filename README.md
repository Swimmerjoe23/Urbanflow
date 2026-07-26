# Online Road Network & Traffic Planner

A road network planning, route optimisation and traffic congestion prediction tool for Nairobi, Kenya.

---

## Project Structure

```
urbanflow/
├── app.py                        # Flask entry point, login/session, rate limiting
├── requirements.txt
├── pytest.ini
├── tests/                        # pytest suite (routing, traffic, scenarios, auth)
├── .env
├── backend/
│   ├── models/
│   │   └── database.py           # SQLite schema + helpers
│   ├── routes/
│   │   ├── network.py            # POST /api/network/fetch
│   │   ├── routing.py            # POST /api/routing/dijkstra|astar
│   │   ├── traffic.py            # POST /api/traffic/predict
│   │   └── scenarios.py          # CRUD /api/scenarios/
│   └── services/
│       ├── network_service.py    # OSMnx fetch + graph serialisation
│       ├── routing_service.py    # Dijkstra & A* implementations
│       ├── traffic_service.py    # ML congestion prediction (Ridge, synthetic training data)
│       └── insights_service.py   # Rule-based bottleneck / single-point-of-failure analysis
└── frontend/
    ├── templates/
    │   ├── landing.html          # Public landing page
    │   ├── login.html            # Demo-credential login form
    │   ├── about.html            # Tech stack + synthetic-data disclaimer
    │   └── index.html            # The app itself (behind login)
    └── static/
        ├── css/main.css
        └── js/
            ├── map.js            # Leaflet layer management
            ├── api.js            # Backend API calls
            ├── simulation.js     # Canvas-overlay animated vehicle simulation
            └── app.js            # UI wiring & state (analyse / edit / compare modes, printable report)
```

---

## Setup

### 1. Clone / create the project folder
```bash
cd urbanflow
```

### 2. Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the development server
```bash
python app.py
```

Open **http://localhost:5050** in your browser. You'll land on the public landing/about pages first; click through to the login page and sign in with the demo credentials below to reach the app itself (`/app`).

Demo login: username `demo`, password `urbanflow` (override via the `DEMO_USERNAME` / `DEMO_PASSWORD` env vars — see `.env`).

### 5. Run the test suite (optional)
```bash
python -m pytest
```

---

## How to Use

1. **Load Road Network** — click *Draw Bounding Box*, drag a rectangle over the area you want on the map (e.g. Nairobi CBD), then click *Fetch Network*. The road graph loads from OpenStreetMap.

2. **Route Optimisation** — click any node on the map to set your **origin**, then click another for the **destination**. Choose Dijkstra or A*, select distance or travel time, and click *Compute Route*. The optimal path is highlighted in yellow.

3. **Traffic Prediction** — select an hour and day of week, then click *Predict Congestion*. Each road segment is coloured green / amber / red based on the ML model's prediction. The model is trained on synthetic, hand-authored congestion profiles (not real Nairobi traffic counts) — see the in-app disclaimer on the About page and next to the traffic controls.

4. **Insights** — after a traffic prediction, the app surfaces up to 3 plain-language findings: likely bottlenecks (high predicted congestion on a single-lane segment) and single points of failure (junctions whose removal would disconnect the network, via graph articulation points).

5. **Simulation** — click *Start* to animate vehicles moving along the loaded network (a mix of route-following and roaming vehicles), rendered on a canvas overlay above the Leaflet map.

6. **Edit mode** — switch to the Edit tab to add roads (connect two nodes) or otherwise adjust the loaded network before re-running routing/traffic analysis on it.

7. **Compare mode** — load two saved scenarios side by side to compare edge counts and predicted congestion between them.

8. **Scenarios** — type a name and click *Save Current Network* to store the current graph. Saved scenarios can be reloaded, renamed or deleted at any time.

9. **Report** — click the report button to generate a printable summary of the current route, traffic prediction and insights, including the synthetic-data disclaimer.

---

## API Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| POST | `/api/network/fetch` | Fetch OSM road network for a bounding box |
| POST | `/api/routing/dijkstra` | Shortest path via Dijkstra |
| POST | `/api/routing/astar` | Shortest path via A* |
| POST | `/api/traffic/predict` | Congestion prediction for hour + day |
| GET  | `/api/scenarios/` | List saved scenarios |
| POST | `/api/scenarios/` | Save a scenario |
| GET  | `/api/scenarios/<id>` | Retrieve a scenario |
| PUT  | `/api/scenarios/<id>` | Rename / update a scenario's description |
| DELETE | `/api/scenarios/<id>` | Delete a scenario |

All `/api/*` routes accept and return JSON, and validate their input — malformed
requests get a `400` with an `{"error": "..."}` body rather than a stack trace.
The web UI (`/app`) itself sits behind a session-based login (`/login`), rate
limited to 5 attempts per IP per minute.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11 + Flask |
| Routing | NetworkX (Dijkstra, A*) |
| OSM Data | OSMnx |
| ML Prediction | scikit-learn (Ridge regression, synthetic training data) |
| Database | SQLite |
| Testing | pytest |
| Frontend | Vanilla HTML/CSS/JS |
| Map | Leaflet.js + OpenStreetMap tiles |
