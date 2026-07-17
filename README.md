# UrbanFlow
**An Online City Planning Simulator and Road Network Optimisation Tool**

---

## Project Structure

```
urbanflow/
├── app.py                        # Flask entry point
├── requirements.txt
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
│       └── traffic_service.py    # ML congestion prediction
└── frontend/
    ├── templates/
    │   └── index.html
    └── static/
        ├── css/main.css
        └── js/
            ├── map.js            # Leaflet layer management
            ├── api.js            # Backend API calls
            └── app.js            # UI wiring & state
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

Open **http://localhost:5000** in your browser.

---

## How to Use

1. **Load Road Network** — click *Draw Bounding Box*, drag a rectangle over the area you want on the map (e.g. Nairobi CBD), then click *Fetch Network*. The road graph loads from OpenStreetMap.

2. **Route Optimisation** — click any node on the map to set your **origin**, then click another for the **destination**. Choose Dijkstra or A*, select distance or travel time, and click *Compute Route*. The optimal path is highlighted in yellow.

3. **Traffic Prediction** — select an hour and day of week, then click *Predict Congestion*. Each road segment is coloured green / amber / red based on the ML model's prediction.

4. **Scenarios** — type a name and click *Save Current Network* to store the current graph. Saved scenarios can be reloaded or deleted at any time.

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
| DELETE | `/api/scenarios/<id>` | Delete a scenario |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11 + Flask |
| Routing | NetworkX (Dijkstra, A*) |
| OSM Data | OSMnx |
| ML Prediction | scikit-learn (Ridge regression) |
| Database | SQLite |
| Frontend | Vanilla HTML/CSS/JS |
| Map | Leaflet.js + OpenStreetMap tiles |
