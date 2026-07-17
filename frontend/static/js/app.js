/* app.js */
document.addEventListener('DOMContentLoaded', () => {
  MapManager.init();
  Simulation.init(MapManager.getLeafletMap());

  // ── state ────────────────────────────────────────────────
  let graph = null, origin = null, dest = null;
  let mode = 'analyse', tool = null, editA = null;
  let typesOn = false, selEdge = null;

  // ── report state (last result of each analysis, for the report view) ──
  let lastArea = null, lastRoute = null, lastTraffic = null, lastCompare = null, lastInsights = [];
  let insightsVisible = true;

  // ── error messages ────────────────────────────────────────
  function friendlyError(raw) {
    if (!raw) return 'Something went wrong. Please try again.';
    const r = raw.toLowerCase();
    if (r.includes('networkerror') || r.includes('failed to fetch'))
      return 'Could not reach the server. Is the app running?';
    if (r.includes('timeout') || r.includes('timed out'))
      return 'The request timed out — the area may be too large. Try a smaller box.';
    if (r.includes('no path'))
      return 'No route found between those two points. Try different locations.';
    if (r.includes('500') || r.includes('internal server'))
      return 'Server error. The area may be too large — try a smaller bounding box.';
    if (r.includes('400'))
      return 'Invalid request. Please reload and try again.';
    return raw;
  }

  // ── helpers ──────────────────────────────────────────────
  const $ = id => document.getElementById(id);
  const st = (id, msg, cls='') => { const e=$(id); e.textContent=msg; e.className='status '+cls; };
  const load = (msg='Loading…') => { $('loading-msg').textContent=msg; $('loading').classList.remove('off'); };
  const unload = () => $('loading').classList.add('off');
  const toast = (msg, cls='info') => {
    const d=document.createElement('div'); d.className=`toast ${cls}`; d.textContent=msg;
    $('toasts').appendChild(d); setTimeout(()=>d.remove(), 3000);
  };
  const enableMain = () => {
    ['btn-route','btn-traffic','btn-save','btn-sim-go']
      .forEach(id => $(id).disabled = !graph);
  };

  // ── welcome ──────────────────────────────────────────────
  $('btn-welcome').onclick = () => {
    $('welcome').classList.add('off');
    setTimeout(()=>{ $('welcome').style.display='none'; }, 450);
  };

  // ── tooltip system ────────────────────────────────────────
  const TIPS = {
    'bbox-drawn':   { title:'📡 Ready to fetch', body:'Your area is selected. Click <strong>Fetch</strong> to load the road network from OpenStreetMap.', target:'btn-fetch', pos:'right' },
    'net-loaded':   { title:'🛣 Network loaded', body:'Click <strong>any two points</strong> on the map to set an origin and destination for routing.', target:'btn-route', pos:'right' },
    'route-done':   { title:'🔥 Predict traffic', body:'Select an hour and day then click <strong>Predict</strong> to see congestion levels on each road.', target:'btn-traffic', pos:'right' },
    'traffic-done': { title:'🚗 Run simulation', body:'Click <strong>Start</strong> to launch live vehicle simulation. Blue = oncoming, red-orange = outgoing.', target:'btn-sim-go', pos:'right' },
  };
  let muteTips = localStorage.getItem('uf-mute') === '1';
  $('tip-ok').onclick   = () => hideTip();
  $('tip-mute').onclick = () => { muteTips=true; localStorage.setItem('uf-mute','1'); hideTip(); };

  function showTip(key) {
    if (muteTips) return;
    const t = TIPS[key]; if (!t) return;
    $('tip-title').textContent = t.title;
    $('tip-body').innerHTML    = t.body;
    const tip = $('tip');
    tip.className = `tip-${t.pos}`;
    tip.style.display = 'block';
    tip.style.opacity = '0';
    const el = t.target ? $(t.target) : null;
    if (el) {
      el.classList.add('tip-pulse');
      setTimeout(()=>el.classList.remove('tip-pulse'), 2500);
      const r = el.getBoundingClientRect();
      if (t.pos === 'right') {
        tip.style.left = (r.right + 14) + 'px';
        tip.style.top  = (r.top + r.height/2 - 60) + 'px';
      }
    }
    requestAnimationFrame(()=>{ tip.style.transition='opacity 0.25s'; tip.style.opacity='1'; });
  }
  function hideTip() {
    const tip = $('tip');
    tip.style.opacity='0';
    setTimeout(()=>{ tip.style.display='none'; }, 260);
  }

  // ── progress ──────────────────────────────────────────────
  function prog(n) {
    for (let i=1; i<=4; i++) {
      const d=$(`pd${i}`), l=$(`pl${i}`);
      if (i<n)  { d.classList.add('done'); d.classList.remove('cur'); d.textContent='✓'; if(l) l.classList.add('done'); }
      if (i===n){ d.classList.add('cur'); d.classList.remove('done'); }
    }
  }

  // ── mode tabs ─────────────────────────────────────────────
  document.querySelectorAll('.mode-tab').forEach(t => {
    t.onclick = () => {
      document.querySelectorAll('.mode-tab').forEach(x=>x.classList.remove('active'));
      t.classList.add('active'); mode = t.dataset.mode;
      ['analyse','edit','compare'].forEach(m => $(`mode-${m}`).style.display = m===mode ? '' : 'none');
    };
  });

  // ── area chips ────────────────────────────────────────────
  let selectedAreaName = 'Custom area';
  document.querySelectorAll('.achip').forEach(c => {
    c.onclick = () => {
      document.querySelectorAll('.achip').forEach(x=>x.classList.remove('on'));
      c.classList.add('on');
      selectedAreaName = c.textContent;
      const [s,w,n,e] = c.dataset.bbox.split(',').map(Number);
      MapManager.flyToBbox(s,w,n,e);
      $('btn-fetch').disabled = false;
      $('welcome').classList.add('off');
      setTimeout(()=>{ $('welcome').style.display='none'; },450);
      st('st-load', `Area: ${c.textContent} — click Fetch`, 'info');
    };
  });

  // ── draw bbox ─────────────────────────────────────────────
  $('btn-draw').onclick = () => {
    document.querySelectorAll('.achip').forEach(x=>x.classList.remove('on'));
    selectedAreaName = 'Custom area';
    MapManager.startBboxDraw();
    st('st-load','Draw a rectangle on the map…','info');
  };
  document.addEventListener('bbox-drawn', () => {
    $('btn-fetch').disabled = false;
    st('st-load','Box drawn — click Fetch','info');
    showTip('bbox-drawn');
  });

  // ── fetch network ─────────────────────────────────────────
  $('btn-fetch').onclick = async () => {
    const bbox = MapManager.getBbox(); if (!bbox) return;
    load('Contacting OpenStreetMap — this can take 10–20 seconds…');
    st('st-load','');
    const loadingMsgs = [
      'Downloading road graph…',
      'Processing nodes and edges…',
      'Almost there…',
    ];
    let msgIdx = 0;
    const msgTimer = setInterval(() => {
      msgIdx = (msgIdx + 1) % loadingMsgs.length;
      $('loading-msg').textContent = loadingMsgs[msgIdx];
    }, 5000);
    try {
      graph = await API.fetchNetwork(bbox);
      MapManager.renderNetwork(graph, typesOn);
      st('st-load', `${graph.nodes.length} nodes · ${graph.edges.length} edges`, 'ok');
      enableMain();
      buildTypePanel(graph);
      lastArea = { name: selectedAreaName, bbox, nodeCount: graph.nodes.length, edgeCount: graph.edges.length };
      lastRoute = null; lastTraffic = null; lastInsights = [];
      MapManager.clearInsights(); $('insight-chip').classList.add('hidden');
      prog(2);
      showTip('net-loaded');
      toast(`Loaded ${graph.nodes.length} nodes`, 'ok');
      await loadScenarios();
    } catch(e) {
      const msg = friendlyError(e.message);
      st('st-load', msg, 'err');
      toast(msg, 'err');
    }
    finally { clearInterval(msgTimer); unload(); }
  };

  // ── road type panel ───────────────────────────────────────
  const RCOL = { motorway:'#ef4444', trunk:'#f97316', primary:'#eab308',
    secondary:'#22c55e', tertiary:'#3b82f6', residential:'#a78bfa', unclassified:'#6b7280' };

  function buildTypePanel(g) {
    const counts = {};
    g.edges.forEach(e=>{ let h=Array.isArray(e.highway)?e.highway[0]:(e.highway||'unclassified'); counts[h]=(counts[h]||0)+1; });
    const grid = $('road-type-grid'); grid.innerHTML='';
    Object.entries(counts).sort((a,b)=>b[1]-a[1]).forEach(([t,n])=>{
      const c=document.createElement('div'); c.className='rchip';
      c.style.setProperty('--chip-c', RCOL[t]||'#6b7280');
      c.innerHTML=`<span class="rchip-dot"></span>${t}<span style="color:var(--ink-4);font-size:10px;margin-left:auto">${n}</span>`;
      c.onclick=()=>{ c.classList.toggle('on'); typesOn=!!document.querySelectorAll('.rchip.on').length; MapManager.rerenderWithTypes(typesOn, RCOL); };
      grid.appendChild(c);
    });
    $('sec-types').style.display='';
  }

  // ── routing ───────────────────────────────────────────────
  MapManager.onMapClick(ll => {
    if (!graph) return;
    if (mode==='edit') { handleEditClick(ll); return; }
    if (mode!=='analyse') return;
    if (!origin) {
      origin={lat:ll.lat, lon:ll.lng};
      $('wp-a').innerHTML=`Origin — <span class="wp-val">${ll.lat.toFixed(5)}, ${ll.lng.toFixed(5)}</span>`;
    } else if (!dest) {
      dest={lat:ll.lat, lon:ll.lng};
      $('wp-b').innerHTML=`Destination — <span class="wp-val">${ll.lat.toFixed(5)}, ${ll.lng.toFixed(5)}</span>`;
      $('btn-route').disabled=false;
    } else {
      origin={lat:ll.lat,lon:ll.lng}; dest=null;
      $('btn-route').disabled=true;
      $('wp-a').innerHTML=`Origin — <span class="wp-val">${ll.lat.toFixed(5)}, ${ll.lng.toFixed(5)}</span>`;
      $('wp-b').innerHTML=`Destination — <span class="wp-val">not set</span>`;
      st('st-route',''); MapManager.clearRoute();
    }
  });

  $('btn-route').onclick = async () => {
    if (!graph||!origin||!dest) return;
    const algo=$('algo').value, wt=$('weight').value;
    const p={graph, weight:wt, origin_lat:origin.lat, origin_lon:origin.lon, dest_lat:dest.lat, dest_lon:dest.lon};
    load(`Computing ${algo.toUpperCase()} route…`);
    try {
      const r = algo==='astar' ? await API.routeAstar(p) : await API.routeDijkstra(p);
      MapManager.renderRoute(r);
      const dist=r.total_length_m?`${(r.total_length_m/1000).toFixed(2)} km`:'';
      const time=r.total_time_s?`${Math.round(r.total_time_s/60)} min`:'';
      st('st-route',`${r.node_count} nodes · ${[dist,time].filter(Boolean).join(' · ')}`,'ok');
      lastRoute = { algo, weight: wt, nodeCount: r.node_count, distKm: dist, timeMin: time };
      $('btn-clear-route').disabled=false;
      prog(3); showTip('route-done');
      toast(`Route: ${[dist,time].filter(Boolean).join(', ')}`,'ok');
    } catch(e) { st('st-route', friendlyError(e.message), 'err'); toast(friendlyError(e.message), 'err'); }
    finally { unload(); }
  };

  $('btn-clear-route').onclick = ()=>{ MapManager.clearRoute(); origin=dest=null; $('btn-route').disabled=true; $('btn-clear-route').disabled=true; $('wp-a').innerHTML='Origin — <span class="wp-val">not set</span>'; $('wp-b').innerHTML='Destination — <span class="wp-val">not set</span>'; st('st-route',''); };

  // ── traffic ───────────────────────────────────────────────
  $('hour').oninput = ()=>{ $('hour-val').textContent=String(parseInt($('hour').value)).padStart(2,'0')+':00'; };

  $('btn-traffic').onclick = async ()=>{
    if (!graph) return;
    load('Predicting congestion…');
    try {
      const hour=parseInt($('hour').value), day=parseInt($('day').value);
      const {predictions, insights} = await API.predictTraffic(graph, hour, day);
      MapManager.renderTraffic(predictions, graph);
      $('btn-clear-traffic').disabled=false;
      showTip('traffic-done');
      toast('Congestion overlay applied','ok');
      const n=predictions.length||1;
      const free=predictions.filter(p=>p.congestion<0.33).length;
      const moderate=predictions.filter(p=>p.congestion>=0.33&&p.congestion<0.66).length;
      const congested=predictions.filter(p=>p.congestion>=0.66).length;
      const dayNames=['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'];
      lastTraffic = { hour, day: dayNames[day], freePct: (free/n*100).toFixed(0), moderatePct: (moderate/n*100).toFixed(0), congestedPct: (congested/n*100).toFixed(0) };

      lastInsights = insights || [];
      insightsVisible = true;
      MapManager.renderInsights(lastInsights);
      MapManager.setInsightsVisible(true);
      const chip=$('insight-chip');
      if (lastInsights.length) {
        $('insight-chip-text').textContent = `${lastInsights.length} insight${lastInsights.length>1?'s':''} found`;
        chip.classList.remove('hidden');
      } else {
        chip.classList.add('hidden');
      }
    } catch(e) { toast(friendlyError(e.message), 'err'); }
    finally { unload(); }
  };
  $('btn-clear-traffic').onclick=()=>{
    MapManager.clearTraffic(); MapManager.clearInsights();
    $('btn-clear-traffic').disabled=true;
    $('insight-chip').classList.add('hidden');
    lastInsights=[];
  };
  $('insight-chip').onclick=()=>{
    insightsVisible=!insightsVisible;
    MapManager.setInsightsVisible(insightsVisible);
    $('insight-chip').style.opacity = insightsVisible ? '1' : '0.5';
  };

  // ── simulation ────────────────────────────────────────────
  $('sim-n').oninput=()=>$('sim-n-val').textContent=$('sim-n').value;
  $('sim-s').oninput=()=>{ $('sim-s-val').textContent=$('sim-s').value+'×'; Simulation.setSpeed(parseFloat($('sim-s').value)); };

  $('btn-sim-go').onclick=()=>{
    if (!graph) return;
    Simulation.stop();
    Simulation.loadGraph(graph);
    Simulation.spawnVehicles(parseInt($('sim-n').value), 0.4);
    Simulation.setSpeed(parseFloat($('sim-s').value));
    Simulation.start();
    $('btn-sim-go').disabled=true; $('btn-sim-stop').disabled=false;
    const s=Simulation.getStats();
    st('st-sim',`${s.route} route + ${s.roam} roaming`,'ok');
    prog(4); toast(`${s.total} vehicles running`,'ok');
  };
  $('btn-sim-stop').onclick=()=>{ Simulation.stop(); $('btn-sim-go').disabled=false; $('btn-sim-stop').disabled=true; st('st-sim','Stopped',''); toast('Simulation stopped','info'); };

  // ── edit ─────────────────────────────────────────────────
  document.querySelectorAll('.etool').forEach(t=>{
    t.onclick=()=>{
      document.querySelectorAll('.etool').forEach(x=>x.classList.remove('on'));
      tool = tool===t.dataset.tool ? null : t.dataset.tool;
      if (tool) { t.classList.add('on'); editA=null; }
      const hints={add:'Click first node, then second to add a road.',remove:'Click a road segment to delete it.',inspect:'Click a road to inspect and edit its attributes.'};
      st('st-edit', tool ? hints[tool] : '', tool?'info':'');
    };
  });

  MapManager.onEdgeClick((edge, line)=>{
    if (mode!=='edit') return;
    if (tool==='remove') {
      if (!confirm(`Remove: ${edge.name||edge.highway||'segment'}?`)) return;
      graph.edges=graph.edges.filter(e=>e.id!==edge.id);
      MapManager.setGraphData(graph); MapManager.renderNetwork(graph,typesOn); st('st-edit','Removed','ok'); toast('Road removed','info');
    } else if (tool==='inspect') {
      selEdge=edge;
      let h=Array.isArray(edge.highway)?edge.highway[0]:(edge.highway||'unclassified');
      $('a-type').value=h; $('a-speed').value=edge.speed_kph||50; $('a-lanes').value=edge.lanes||2; $('a-name').value=edge.name||'';
      MapManager.highlightEdge(line,'#eab308'); st('st-edit',`Inspecting: ${edge.name||h}`,'info');
      document.querySelector('[data-mode="edit"]').click();
    }
  });

  ['a-type','a-speed','a-lanes','a-name'].forEach(id=>{
    $(id).onchange=()=>{
      if (!selEdge||!graph) return;
      const e=graph.edges.find(x=>x.id===selEdge.id); if (!e) return;
      e.highway=$('a-type').value; e.speed_kph=parseFloat($('a-speed').value)||50;
      e.lanes=parseInt($('a-lanes').value)||2; e.name=$('a-name').value;
      MapManager.setGraphData(graph); st('st-edit','Updated','ok');
    };
  });

  function handleEditClick(ll) {
    if (tool!=='add'||!graph) return;
    let best=null, bd=Infinity;
    graph.nodes.forEach(n=>{ const d=Math.hypot(n.lat-ll.lat,n.lon-ll.lng); if(d<bd){bd=d;best=n;} });
    if (!best) return;
    if (!editA) { editA=best; st('st-edit','Node A set — click second node','info'); }
    else {
      const dist=Math.hypot((editA.lat-best.lat)*111000,(editA.lon-best.lon)*111000*Math.cos(editA.lat*Math.PI/180));
      graph.edges.push({ id:`c_${editA.id}_${best.id}_${Date.now()}`, source:editA.id, target:best.id, length:Math.round(dist), speed_kph:parseFloat($('a-speed').value)||50, lanes:parseInt($('a-lanes').value)||2, highway:$('a-type').value, name:$('a-name').value, oneway:false });
      MapManager.setGraphData(graph); MapManager.renderNetwork(graph,typesOn);
      editA=null; st('st-edit',`Added ${Math.round(dist)}m road`,'ok'); toast(`Road added (${Math.round(dist)}m)`,'ok');
      document.dispatchEvent(new Event('uf:edit-used'));
    }
  }

  // ── scenarios ─────────────────────────────────────────────
  const SC_NAME_MAX = 60, SC_NAME_RE = /^[A-Za-z0-9][A-Za-z0-9 _\-']*$/;

  function validateScenarioName(name) {
    if (!name) return 'Enter a name';
    if (name.length > SC_NAME_MAX) return `Name must be at most ${SC_NAME_MAX} characters`;
    if (!SC_NAME_RE.test(name)) return 'Name may only contain letters, numbers, spaces, hyphens, underscores and apostrophes';
    return null;
  }

  async function loadScenarios() {
    try {
      const sc=await API.listScenarios();
      const list=$('sc-list');
      if (!sc.length){list.innerHTML='<p class="hint">No scenarios yet.</p>';return;}
      list.innerHTML='';
      sc.forEach(s=>{
        const d=document.createElement('div'); d.className='sc-item';
        d.innerHTML=`<span class="sc-name">${s.name}</span><span class="sc-actions"><button class="sc-ren" onclick="renSc(${s.id},'${s.name.replace(/'/g,"\\'")}')">✎</button><button class="sc-load" onclick="loadSc(${s.id})">Load</button><button class="sc-del" onclick="delSc(${s.id})">✕</button></span>`;
        list.appendChild(d);
      });
      ['cmp-a','cmp-b'].forEach(id=>{
        const sel=$(id),cur=sel.value; sel.innerHTML='<option value="">— select —</option>';
        sc.forEach(s=>{const o=document.createElement('option');o.value=s.id;o.textContent=s.name;sel.appendChild(o);}); sel.value=cur;
      });
      $('btn-cmp').disabled=sc.length<2;
    } catch(_){}
  }

  $('btn-save').onclick=async()=>{
    const name=$('sc-name').value.trim();
    const err=validateScenarioName(name); if (err){toast(err,'err');return;}
    if (!graph) return;
    try { await API.saveScenario(name,MapManager.getBbox(),graph); $('sc-name').value=''; toast(`Saved: ${name}`,'ok'); await loadScenarios(); }
    catch(e){toast(e.message,'err');}
  };

  window.loadSc=async(id)=>{ load('Loading…'); try{ const s=await API.getScenario(id); graph=s.graph_data; MapManager.renderNetwork(graph,typesOn); buildTypePanel(graph); enableMain(); toast(`Loaded: ${s.name}`,'ok'); }catch(e){toast(e.message,'err');}finally{unload();} };
  window.delSc=async(id)=>{ if(!confirm('Delete?'))return; await API.deleteScenario(id); toast('Deleted','info'); await loadScenarios(); };
  window.renSc=async(id,oldName)=>{
    const name=prompt('Rename scenario:',oldName); if (name===null) return;
    const trimmed=name.trim(); const err=validateScenarioName(trimmed); if (err){toast(err,'err');return;}
    try { await API.updateScenario(id,{name:trimmed}); toast('Renamed','ok'); await loadScenarios(); }
    catch(e){toast(e.message,'err');}
  };

  $('btn-cmp').onclick=async()=>{
    const idA=$('cmp-a').value,idB=$('cmp-b').value;
    if (!idA||!idB||idA===idB){toast('Select two different scenarios','err');return;}
    load('Comparing…');
    try {
      const [sA,sB]=await Promise.all([API.getScenario(idA),API.getScenario(idB)]);
      const [pA,pB]=await Promise.all([API.predictTraffic(sA.graph_data,8,0),API.predictTraffic(sB.graph_data,8,0)]);
      const avg=p=>{const a=p.predictions||p;return a.length?a.reduce((s,x)=>s+x.congestion,0)/a.length:0;};
      $('ca-name').textContent=sA.name; $('cb-name').textContent=sB.name;
      $('ca-e').textContent=sA.graph_data.edges.length; $('cb-e').textContent=sB.graph_data.edges.length;
      $('ca-c').textContent=(avg(pA)*100).toFixed(1)+'%'; $('cb-c').textContent=(avg(pB)*100).toFixed(1)+'%';
      $('compare-bar').classList.remove('hidden'); st('st-cmp',`${sA.name} vs ${sB.name}`,'ok'); toast('Comparison ready','ok');
      lastCompare = {
        a: { name: sA.name, edges: sA.graph_data.edges.length, congestionPct: (avg(pA)*100).toFixed(1) },
        b: { name: sB.name, edges: sB.graph_data.edges.length, congestionPct: (avg(pB)*100).toFixed(1) },
      };
    } catch(e){toast(e.message,'err');}
    finally{unload();}
  };
  $('compare-close').onclick=()=>$('compare-bar').classList.add('hidden');

  loadScenarios();

  // ── report ────────────────────────────────────────────────
  function stat(label, value) {
    return `<div class="report-stat">${label}<b>${value}</b></div>`;
  }

  function renderReport() {
    $('report-generated').textContent = `Generated ${new Date().toLocaleString()}`;

    const areaGrid = $('rs-area-grid');
    if (lastArea) {
      const b = lastArea.bbox;
      areaGrid.innerHTML = stat('Area', lastArea.name)
        + stat('Nodes', lastArea.nodeCount)
        + stat('Edges', lastArea.edgeCount)
        + stat('Bounding box', [b.south,b.west,b.north,b.east].map(v=>v.toFixed(4)).join(', '));
    } else {
      areaGrid.innerHTML = '';
    }
    $('rs-area').style.display = lastArea ? '' : 'none';

    const routeGrid = $('rs-route-grid');
    if (lastRoute) {
      routeGrid.innerHTML = stat('Algorithm', lastRoute.algo==='astar'?'A*':'Dijkstra')
        + stat('Optimised for', lastRoute.weight==='travel_time'?'Travel time':'Distance')
        + stat('Path nodes', lastRoute.nodeCount)
        + stat('Distance', lastRoute.distKm||'—')
        + stat('Travel time', lastRoute.timeMin||'—');
    } else { routeGrid.innerHTML=''; }
    $('rs-route-empty').style.display = lastRoute ? 'none' : '';

    const trafficGrid = $('rs-traffic-grid');
    if (lastTraffic) {
      trafficGrid.innerHTML = stat('Hour', String(lastTraffic.hour).padStart(2,'0')+':00')
        + stat('Day', lastTraffic.day)
        + stat('Free flow', lastTraffic.freePct+'%')
        + stat('Moderate', lastTraffic.moderatePct+'%')
        + stat('Congested', lastTraffic.congestedPct+'%');
    } else { trafficGrid.innerHTML=''; }
    $('rs-traffic-empty').style.display = lastTraffic ? 'none' : '';

    const cmpGrid = $('rs-compare-grid');
    if (lastCompare) {
      cmpGrid.innerHTML = stat('Scenario A', lastCompare.a.name)
        + stat('A — edges / congestion', `${lastCompare.a.edges} / ${lastCompare.a.congestionPct}%`)
        + stat('Scenario B', lastCompare.b.name)
        + stat('B — edges / congestion', `${lastCompare.b.edges} / ${lastCompare.b.congestionPct}%`);
    } else { cmpGrid.innerHTML=''; }
    $('rs-compare-empty').style.display = lastCompare ? 'none' : '';

    const insightsList = $('rs-insights-list');
    const INSIGHT_COLOUR = { bottleneck: '#C23B2C', single_point_of_failure: '#B8740A' };
    if (lastInsights.length) {
      insightsList.innerHTML = lastInsights.map(ins => `
        <div class="report-insight">
          <div class="report-insight-title"><span class="dot" style="background:${INSIGHT_COLOUR[ins.type]||'var(--ink-3)'}"></span>${ins.title}</div>
          <div class="report-insight-msg">${ins.message}</div>
          <div class="report-insight-why">${ins.why}</div>
        </div>`).join('');
    } else { insightsList.innerHTML=''; }
    $('rs-insights-empty').style.display = lastInsights.length ? 'none' : '';
  }

  $('btn-report').onclick = () => { renderReport(); $('report-overlay').classList.remove('hidden'); };
  $('report-close').onclick = () => $('report-overlay').classList.add('hidden');
  $('report-print').onclick = () => window.print();
  $('report-overlay').addEventListener('click', e => { if (e.target.id==='report-overlay') $('report-overlay').classList.add('hidden'); });
});
