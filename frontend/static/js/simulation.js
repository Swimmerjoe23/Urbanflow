/* simulation.js — vehicle simulation layer */

const Simulation = (() => {
  let _map = null;
  let _graphData = null;
  let _vehicles = [];
  let _animFrame = null;
  let _running = false;
  let _lastTime = 0;
  let _canvas = null;
  let _ctx = null;
  let _nodeMap = {};
  let _adjacency = {};   // node -> [{ node, edge }]
  let _routeVehicles = [];
  let _roamVehicles  = [];
  let _speed = 1.0;      // simulation speed multiplier

  // ── Colours by vehicle type ──────────────────────────────
  const COLOURS = {
    route: '#E8724A',   // yellow  — route followers
    roam:  '#38bdf8',   // sky blue — roaming
    fast:  '#22c55e',
    slow:  '#ef4444',
  };

  // ── Init ─────────────────────────────────────────────────
  function init(leafletMap) {
    _map = leafletMap;
    _createCanvas();
    _map.on('move zoom', _repositionCanvas);
  }

  function _createCanvas() {
    // Overlay a full-size canvas on top of the Leaflet map pane
    const pane = _map.getPanes().overlayPane;
    _canvas = document.createElement('canvas');
    _canvas.style.cssText = 'position:absolute;top:0;left:0;pointer-events:none;z-index:450;';
    pane.appendChild(_canvas);
    _resizeCanvas();
    window.addEventListener('resize', _resizeCanvas);
  }

  function _resizeCanvas() {
    const container = _map.getContainer();
    _canvas.width  = container.clientWidth;
    _canvas.height = container.clientHeight;
    _ctx = _canvas.getContext('2d');
  }

  function _repositionCanvas() {
    const topLeft = _map.containerPointToLayerPoint([0, 0]);
    L.DomUtil.setPosition(_canvas, topLeft);
  }

  // ── Build graph lookup ───────────────────────────────────
  function loadGraph(graphData) {
    _graphData = graphData;
    _nodeMap = {};
    _adjacency = {};

    graphData.nodes.forEach(n => {
      _nodeMap[n.id] = n;
      _adjacency[n.id] = [];
    });

    graphData.edges.forEach(edge => {
      const s = edge.source, t = edge.target;
      if (_adjacency[s]) _adjacency[s].push({ node: t, edge });
      if (!edge.oneway && _adjacency[t]) _adjacency[t].push({ node: s, edge });
    });
  }

  // ── Spawn vehicles ───────────────────────────────────────
  function spawnVehicles(count = 40, routeRatio = 0.4) {
    _vehicles = [];
    _routeVehicles = [];
    _roamVehicles  = [];

    const nodeIds = Object.keys(_nodeMap);
    if (nodeIds.length < 2) return;

    const nRoute = Math.floor(count * routeRatio);
    const nRoam  = count - nRoute;

    // Route-following vehicles
    for (let i = 0; i < nRoute; i++) {
      const v = _makeRouteVehicle(nodeIds);
      if (v) { _vehicles.push(v); _routeVehicles.push(v); }
    }

    // Roaming vehicles
    for (let i = 0; i < nRoam; i++) {
      const v = _makeRoamVehicle(nodeIds);
      if (v) { _vehicles.push(v); _roamVehicles.push(v); }
    }
  }

  function _randomNode(nodeIds) {
    return nodeIds[Math.floor(Math.random() * nodeIds.length)];
  }

  function _makeRouteVehicle(nodeIds) {
    let origin = _randomNode(nodeIds);
    let dest   = _randomNode(nodeIds);
    let attempts = 0;
    while (origin === dest && attempts++ < 10) dest = _randomNode(nodeIds);

    const path = _dijkstraPath(origin, dest);
    if (!path || path.length < 2) return null;

    return {
      type:      'route',
      path,
      pathIdx:   0,
      progress:  Math.random(),   // 0-1 along current segment
      lat: _nodeMap[path[0]].lat,
      lon: _nodeMap[path[0]].lon,
      speed:     0.3 + Math.random() * 0.4,   // segments per second
      colour:    COLOURS.route,  // outgoing — rust orange
      radius:    3.5,
      origin, dest,
    };
  }

  function _makeRoamVehicle(nodeIds) {
    const startId = _randomNode(nodeIds);
    const start   = _nodeMap[startId];
    const next    = _pickNext(startId);
    if (!next) return null;

    return {
      type:     'roam',
      currentNode: startId,
      nextNode:    next.node,
      progress:    Math.random(),
      lat: start.lat,
      lon: start.lon,
      speed:    0.2 + Math.random() * 0.5,
      colour:   COLOURS.roam,  // oncoming — sky blue
      radius:   3,
    };
  }

  function _pickNext(nodeId) {
    const neighbours = _adjacency[nodeId];
    if (!neighbours || !neighbours.length) return null;
    return neighbours[Math.floor(Math.random() * neighbours.length)];
  }

  // ── Dijkstra (lightweight, returns node id array) ────────
  function _dijkstraPath(startId, endId) {
    const dist  = { [startId]: 0 };
    const prev  = {};
    const visited = new Set();
    const queue = [[0, startId]];   // [cost, nodeId]

    while (queue.length) {
      queue.sort((a, b) => a[0] - b[0]);
      const [cost, u] = queue.shift();
      if (visited.has(u)) continue;
      visited.add(u);
      if (u === endId) break;

      (_adjacency[u] || []).forEach(({ node: v, edge }) => {
        const newCost = cost + (edge.length || 100);
        if (dist[v] === undefined || newCost < dist[v]) {
          dist[v] = newCost;
          prev[v] = u;
          queue.push([newCost, v]);
        }
      });
    }

    if (prev[endId] === undefined && startId !== endId) return null;
    const path = [];
    let cur = endId;
    while (cur !== undefined) { path.unshift(cur); cur = prev[cur]; }
    return path.length > 1 ? path : null;
  }

  // ── Animation loop ───────────────────────────────────────
  function start() {
    if (_running) return;
    _running = true;
    _lastTime = performance.now();
    _tick();
  }

  function stop() {
    _running = false;
    if (_animFrame) cancelAnimationFrame(_animFrame);
    _ctx && _ctx.clearRect(0, 0, _canvas.width, _canvas.height);
  }

  function setSpeed(s) { _speed = s; }

  function _tick() {
    if (!_running) return;
    const now   = performance.now();
    const delta = Math.min((now - _lastTime) / 1000, 0.1) * _speed;
    _lastTime   = now;

    _update(delta);
    _draw();
    _animFrame = requestAnimationFrame(_tick);
  }

  function _update(delta) {
    _vehicles.forEach(v => {
      if (v.type === 'route') _updateRoute(v, delta);
      else                    _updateRoam(v, delta);
    });
  }

  function _updateRoute(v, delta) {
    v.progress += delta * v.speed;

    while (v.progress >= 1) {
      v.progress -= 1;
      v.pathIdx++;

      if (v.pathIdx >= v.path.length - 1) {
        // Respawn with a new route
        const nodeIds = Object.keys(_nodeMap);
        const newV = _makeRouteVehicle(nodeIds);
        if (newV) Object.assign(v, newV);
        return;
      }
    }

    const aId = v.path[v.pathIdx];
    const bId = v.path[v.pathIdx + 1];
    const a   = _nodeMap[aId];
    const b   = _nodeMap[bId];
    if (!a || !b) return;

    v.lat = a.lat + (b.lat - a.lat) * v.progress;
    v.lon = a.lon + (b.lon - a.lon) * v.progress;
  }

  function _updateRoam(v, delta) {
    v.progress += delta * v.speed;

    if (v.progress >= 1) {
      v.progress -= 1;
      v.currentNode = v.nextNode;
      const next = _pickNext(v.currentNode);
      if (next) {
        v.nextNode = next.node;
      } else {
        // Dead end — pick any node
        const nodeIds = Object.keys(_nodeMap);
        v.nextNode = nodeIds[Math.floor(Math.random() * nodeIds.length)];
      }
    }

    const a = _nodeMap[v.currentNode];
    const b = _nodeMap[v.nextNode];
    if (!a || !b) return;

    v.lat = a.lat + (b.lat - a.lat) * v.progress;
    v.lon = a.lon + (b.lon - a.lon) * v.progress;
  }

  // ── Drawing ──────────────────────────────────────────────
  function _draw() {
    const w = _canvas.width;
    const h = _canvas.height;
    _ctx.clearRect(0, 0, w, h);

    _vehicles.forEach(v => {
      const point = _map.latLngToContainerPoint([v.lat, v.lon]);
      const x = point.x, y = point.y;

      // Skip if off-screen
      if (x < -20 || x > w + 20 || y < -20 || y > h + 20) return;

      // Outer glow
      const glow = _ctx.createRadialGradient(x, y, 0, x, y, v.radius * 3);
      glow.addColorStop(0, v.colour + '55');
      glow.addColorStop(1, 'transparent');
      _ctx.beginPath();
      _ctx.arc(x, y, v.radius * 3, 0, Math.PI * 2);
      _ctx.fillStyle = glow;
      _ctx.fill();

      // Core dot
      _ctx.beginPath();
      _ctx.arc(x, y, v.radius, 0, Math.PI * 2);
      _ctx.fillStyle = v.colour;
      _ctx.shadowColor = v.colour;
      _ctx.shadowBlur  = 8;
      _ctx.fill();
      _ctx.shadowBlur = 0;
    });
  }

  function getStats() {
    return {
      total:  _vehicles.length,
      route:  _routeVehicles.length,
      roam:   _roamVehicles.length,
      running: _running,
    };
  }

  return { init, loadGraph, spawnVehicles, start, stop, setSpeed, getStats };
})();
