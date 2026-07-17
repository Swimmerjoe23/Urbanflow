/* map.js — Leaflet map setup and layer management */

const MapManager = (() => {
  let map, bboxLayer, networkLayer, routeLayer, trafficLayer, editLayer, labelLayer, insightLayer;
  let bboxRect = null;
  let drawingBbox = false;
  let bboxStart = null;
  let _graphData = null;
  let _clickCallback = null;
  let _edgeClickCallback = null;

  // Road type colours
  const ROAD_COLOURS = {
    motorway:    '#ef4444',
    trunk:       '#f97316',
    primary:     '#eab308',
    secondary:   '#22c55e',
    tertiary:    '#3b82f6',
    residential: '#8b5cf6',
    unclassified:'#64748b',
  };

  function init() {
    map = L.map('map', { zoomControl: true }).setView([-1.286389, 36.817223], 14);

    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      attribution: '© OpenStreetMap contributors © CARTO',
      subdomains: 'abcd', maxZoom: 19,
    }).addTo(map);

    bboxLayer    = L.layerGroup().addTo(map);
    networkLayer = L.layerGroup().addTo(map);
    trafficLayer = L.layerGroup().addTo(map);
    routeLayer   = L.layerGroup().addTo(map);
    editLayer    = L.layerGroup().addTo(map);
    labelLayer   = L.layerGroup().addTo(map);
    insightLayer = L.layerGroup().addTo(map);

    map.on('click', (e) => {
      if (drawingBbox) return;
      if (_clickCallback) _clickCallback(e.latlng);
    });
  }

  // ── Bounding box ────────────────────────────────────────────
  function startBboxDraw() {
    drawingBbox = true;
    bboxStart   = null;
    map.getContainer().style.cursor = 'crosshair';
    map.once('mousedown', (e) => {
      bboxStart = e.latlng;
      map.dragging.disable();
      map.on('mousemove', onBboxMove);
      map.once('mouseup', onBboxEnd);
    });
  }

  function onBboxMove(e) {
    if (!bboxStart) return;
    bboxLayer.clearLayers();
    L.rectangle([bboxStart, e.latlng], {
      color: '#3b82f6', weight: 2, fillOpacity: .08, dashArray: '6 4'
    }).addTo(bboxLayer);
  }

  function onBboxEnd(e) {
    map.off('mousemove', onBboxMove);
    map.dragging.enable();
    map.getContainer().style.cursor = '';
    drawingBbox = false;
    if (!bboxStart) return;
    const b = L.latLngBounds(bboxStart, e.latlng);
    bboxRect = { south: b.getSouth(), west: b.getWest(), north: b.getNorth(), east: b.getEast() };
    bboxLayer.clearLayers();
    L.rectangle(b, { color: '#3b82f6', weight: 2, fillOpacity: .05, dashArray: '6 4' }).addTo(bboxLayer);
    document.dispatchEvent(new CustomEvent('bbox-drawn', { detail: bboxRect }));
  }

  function getBbox() { return bboxRect; }

  // ── Network rendering ────────────────────────────────────────
  function renderNetwork(graphData, colourByType = false) {
    _graphData = graphData;
    networkLayer.clearLayers();
    trafficLayer.clearLayers();
    routeLayer.clearLayers();
    labelLayer.clearLayers();

    const nodeMap = {};
    graphData.nodes.forEach(n => { nodeMap[n.id] = [n.lat, n.lon]; });

    graphData.edges.forEach(edge => {
      const from = nodeMap[edge.source];
      const to   = nodeMap[edge.target];
      if (!from || !to) return;

      let hw = edge.highway;
      if (Array.isArray(hw)) hw = hw[0];
      const colour = colourByType
        ? (ROAD_COLOURS[hw] || ROAD_COLOURS.unclassified)
        : 'rgba(148,163,184,0.6)';

      const line = L.polyline([from, to], {
        color: colour, weight: colourByType ? 3 : 2, opacity: .8,
      }).addTo(networkLayer);

      const label = edge.name
        ? `<b>${edge.name}</b><br>${hw || 'road'} · ${edge.speed_kph || 50} kph`
        : `${hw || 'road'} · ${edge.speed_kph || 50} kph`;
      line.bindTooltip(label, { sticky: true, className: 'road-label-tag' });

      if (_edgeClickCallback) {
        line.on('click', (ev) => {
          L.DomEvent.stopPropagation(ev);
          _edgeClickCallback(edge, line);
        });
      }
    });
  }

  function rerenderWithTypes(colourByType, colours) {
    if (colours) Object.assign(ROAD_COLOURS, colours);
    if (_graphData) renderNetwork(_graphData, colourByType);
  }

  // ── Traffic overlay ──────────────────────────────────────────
  function renderTraffic(predictions, graphData) {
    trafficLayer.clearLayers();
    const nodeMap = {};
    graphData.nodes.forEach(n => { nodeMap[n.id] = [n.lat, n.lon]; });
    predictions.forEach(p => {
      const from = nodeMap[p.source];
      const to   = nodeMap[p.target];
      if (!from || !to) return;
      L.polyline([from, to], { color: p.colour, weight: 5, opacity: .85 })
        .addTo(trafficLayer)
        .bindTooltip(`${Math.round(p.congestion * 100)}% congestion`, { sticky: true, className: 'road-label-tag' });
    });
  }

  function clearTraffic() { trafficLayer.clearLayers(); }

  // ── Insight callouts ────────────────────────────────────────
  const INSIGHT_COLOUR = { bottleneck: '#E2685A', single_point_of_failure: '#EAB308' };

  function renderInsights(insights) {
    insightLayer.clearLayers();
    insights.forEach(ins => {
      const colour = INSIGHT_COLOUR[ins.type] || '#5C95E8';
      L.circleMarker([ins.location.lat, ins.location.lon], {
        radius: 6, color: colour, fillColor: colour, fillOpacity: 1, weight: 2,
      }).addTo(insightLayer);

      const icon = L.divIcon({
        className: 'insight-bubble-wrap',
        html: `<div class="insight-bubble">
                 <div class="insight-head" style="color:${colour}"><span class="insight-dot" style="background:${colour}"></span>${ins.title}</div>
                 <div class="insight-msg">${ins.message}</div>
                 <div class="insight-actions">
                   <span class="insight-why">Why</span>
                   <span class="insight-fly">Fly to</span>
                 </div>
                 <div class="insight-why-body" style="display:none">${ins.why}</div>
               </div>`,
        iconSize: null,
      });
      const marker = L.marker([ins.location.lat, ins.location.lon], { icon, interactive: true, zIndexOffset: 1000 }).addTo(insightLayer);
      const el = marker.getElement();
      L.DomEvent.disableClickPropagation(el);
      el.querySelector('.insight-why').addEventListener('click', () => {
        const body = el.querySelector('.insight-why-body');
        body.style.display = body.style.display === 'none' ? '' : 'none';
      });
      el.querySelector('.insight-fly').addEventListener('click', () => {
        map.flyTo([ins.location.lat, ins.location.lon], 17, { duration: 0.8 });
      });
    });
  }

  function clearInsights() { insightLayer.clearLayers(); }
  function setInsightsVisible(visible) {
    if (visible) { if (!map.hasLayer(insightLayer)) map.addLayer(insightLayer); }
    else if (map.hasLayer(insightLayer)) map.removeLayer(insightLayer);
  }

  // ── Route overlay ────────────────────────────────────────────
  function renderRoute(routeData) {
    routeLayer.clearLayers();
    if (!routeData.coordinates || routeData.coordinates.length < 2) return;
    const latlngs = routeData.coordinates.map(c => [c.lat, c.lon]);

    // Glow effect — two layers
    L.polyline(latlngs, { color: 'rgba(250,204,21,0.25)', weight: 12, opacity: 1 }).addTo(routeLayer);
    L.polyline(latlngs, { color: '#facc15', weight: 4, opacity: .95 }).addTo(routeLayer);

    L.circleMarker(latlngs[0], { radius: 7, color: '#22c55e', fillColor: '#22c55e', fillOpacity: 1, weight: 2 })
      .addTo(routeLayer).bindPopup('<b>Origin</b>');
    L.circleMarker(latlngs[latlngs.length - 1], { radius: 7, color: '#ef4444', fillColor: '#ef4444', fillOpacity: 1, weight: 2 })
      .addTo(routeLayer).bindPopup('<b>Destination</b>');
  }

  function clearRoute() { routeLayer.clearLayers(); }

  // ── Edit helpers ─────────────────────────────────────────────
  function highlightEdge(line, colour = '#facc15') {
    line.setStyle({ color: colour, weight: 5 });
  }

  function onMapClick(cb)      { _clickCallback = cb; }
  function onEdgeClick(cb)     { _edgeClickCallback = cb; }
  function getGraphData()      { return _graphData; }
  function setGraphData(g)     { _graphData = g; }
  function getRoadColours()    { return ROAD_COLOURS; }

  return {
    init, startBboxDraw, getBbox,
    renderNetwork, rerenderWithTypes,
    renderTraffic, clearTraffic,
    renderInsights, clearInsights, setInsightsVisible,
    renderRoute, clearRoute,
    onMapClick, onEdgeClick,
    getGraphData, setGraphData, getRoadColours,
    highlightEdge,
    getLeafletMap: () => map,
    flyToBbox: (s,w,n,e) => { map.flyToBounds([[s,w],[n,e]], {duration:1}); bboxRect={south:s,west:w,north:n,east:e}; document.dispatchEvent(new CustomEvent("bbox-drawn",{detail:bboxRect})); },
  };
})();
