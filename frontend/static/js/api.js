/* api.js — thin wrapper around all backend API calls */

const API = (() => {
  const BASE = "/api";

  async function _post(url, body) {
    const res = await fetch(BASE + url, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data;
  }

  async function _get(url) {
    const res  = await fetch(BASE + url);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data;
  }

  async function _delete(url) {
    const res  = await fetch(BASE + url, { method: "DELETE" });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data;
  }

  async function _put(url, body) {
    const res = await fetch(BASE + url, {
      method:  "PUT",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data;
  }

  return {
    fetchNetwork: (bbox)                  => _post("/network/fetch", bbox),
    routeDijkstra: (payload)              => _post("/routing/dijkstra", payload),
    routeAstar: (payload)                 => _post("/routing/astar", payload),
    predictTraffic: (graph, hour, day)    => _post("/traffic/predict", { graph, hour, day_of_week: day }),
    listScenarios: ()                     => _get("/scenarios/"),
    saveScenario: (name, bbox, graphData) => _post("/scenarios/", { name, bbox, graph_data: graphData }),
    getScenario:  (id)                    => _get(`/scenarios/${id}`),
    updateScenario: (id, fields)          => _put(`/scenarios/${id}`, fields),
    deleteScenario: (id)                  => _delete(`/scenarios/${id}`),
  };
})();
