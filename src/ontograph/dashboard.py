"""Interactive knowledge graph dashboard served from a local HTTP server.

Renders a force-directed graph visualization using D3.js. The initial view
shows the most-connected entity (hub) with its top 50 relationships. Users
can click nodes to expand their connections on demand, preventing memory
issues with large graphs.

Usage:
    ontograph dashboard
    ontograph dashboard --port 9000
    ontograph dashboard --db project.db --no-browser
"""

from __future__ import annotations

import json
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from ontograph.db import GraphDB
from ontograph.models import Entity


def _entity_dict(entity: Entity) -> dict:
    """Convert an Entity to a JSON-serializable dict with parsed attributes."""
    row = entity.to_row()
    if isinstance(row["attributes"], str):
        row["attributes"] = json.loads(row["attributes"]) if row["attributes"] else {}
    return row


def find_hub_entity_id(db: GraphDB) -> str | None:
    """Find the entity with the most relationship connections."""
    row = db.conn.execute(
        "SELECT entity_id, COUNT(*) as cnt FROM ("
        "  SELECT source_id as entity_id FROM relationships"
        "  UNION ALL"
        "  SELECT target_id as entity_id FROM relationships"
        ") GROUP BY entity_id ORDER BY cnt DESC LIMIT 1"
    ).fetchone()
    if row:
        return row["entity_id"]
    entities = db.list_entities()
    if entities:
        return entities[0].id
    return None


def get_connection_count(db: GraphDB, entity_id: str) -> int:
    """Count total relationships for an entity."""
    row = db.conn.execute(
        "SELECT COUNT(*) as cnt FROM relationships "
        "WHERE source_id = ? OR target_id = ?",
        (entity_id, entity_id),
    ).fetchone()
    return row["cnt"]


def get_node_with_connections(db: GraphDB, entity_id: str, limit: int = 50) -> dict:
    """Get an entity with its connections for the dashboard."""
    entity = db.get_entity(entity_id)
    if entity is None:
        return {"center": None, "connections": [], "total_connections": 0}

    rels = db.get_relationships(entity_id)
    connections = []
    for rel in rels[:limit]:
        if rel.source_id == entity_id:
            neighbor = db.get_entity(rel.target_id)
            is_outgoing = True
        else:
            neighbor = db.get_entity(rel.source_id)
            is_outgoing = False

        if neighbor is None:
            continue

        connections.append({
            "entity": _entity_dict(neighbor),
            "connection_count": get_connection_count(db, neighbor.id),
            "relationship": {
                "id": rel.id,
                "type": rel.relationship_type,
                "directed": rel.directed,
                "is_outgoing": is_outgoing,
                "attributes": rel.attributes,
            },
        })

    return {
        "center": _entity_dict(entity),
        "center_connection_count": len(rels),
        "connections": connections,
        "total_connections": len(rels),
        "showing": min(limit, len(rels)),
    }


def make_handler(db_path: str) -> type:
    """Create a request handler class bound to a specific database path."""

    class DashboardHandler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass  # suppress default access logs

        def _json_response(self, data: dict, status: int = 200) -> None:
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _html_response(self, html: str) -> None:
            body = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/") or "/"

            if path == "/":
                self._html_response(DASHBOARD_HTML)
                return

            db = GraphDB(db_path)
            try:
                if path == "/api/stats":
                    stats = db.stats()
                    # Add entity type breakdown
                    rows = db.conn.execute(
                        "SELECT entity_type, COUNT(*) as cnt "
                        "FROM entities GROUP BY entity_type ORDER BY cnt DESC"
                    ).fetchall()
                    stats["type_counts"] = {r["entity_type"]: r["cnt"] for r in rows}
                    self._json_response(stats)

                elif path == "/api/hub":
                    hub_id = find_hub_entity_id(db)
                    if hub_id is None:
                        self._json_response({"center": None, "connections": []})
                    else:
                        data = get_node_with_connections(db, hub_id)
                        self._json_response(data)

                elif path.startswith("/api/expand/"):
                    entity_id = path.split("/api/expand/")[1]
                    data = get_node_with_connections(db, entity_id)
                    self._json_response(data)

                else:
                    self.send_error(404, "Not found")
            finally:
                db.close()

    return DashboardHandler


def serve(db_path: str, host: str = "127.0.0.1", port: int = 8484,
          open_browser: bool = True) -> None:
    """Start the dashboard HTTP server."""
    handler = make_handler(db_path)
    server = ThreadingHTTPServer((host, port), handler)
    url = f"http://{host}:{port}"
    print(f"ontograph dashboard running at {url}")
    print(f"Database: {db_path}")
    print("Press Ctrl+C to stop.")

    if open_browser:
        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()


# ── Dashboard HTML ──

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ontograph dashboard</title>
<script src="https://d3js.org/d3.v7.min.js"></script>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg: #0d1117;
  --surface: #161b22;
  --border: #30363d;
  --text: #e6edf3;
  --text-dim: #8b949e;
  --accent: #58a6ff;
}

body {
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
  font-size: 14px;
  overflow: hidden;
  height: 100vh;
  display: flex;
  flex-direction: column;
}

header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 20px;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

header h1 {
  font-size: 16px;
  font-weight: 600;
  color: var(--accent);
  letter-spacing: 0.5px;
}

.stat-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 12px;
  font-size: 12px;
  color: var(--text-dim);
}

.stat-pill .val {
  color: var(--text);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

main {
  display: flex;
  flex: 1;
  overflow: hidden;
}

#graph-container {
  flex: 1;
  position: relative;
  overflow: hidden;
}

#graph-container svg {
  width: 100%;
  height: 100%;
  cursor: grab;
}

#graph-container svg:active { cursor: grabbing; }

.link {
  stroke: #30363d;
  stroke-width: 1.5;
  fill: none;
}

.link.highlighted {
  stroke: var(--accent);
  stroke-width: 2.5;
}

.link-label {
  font-size: 10px;
  fill: var(--text-dim);
  pointer-events: none;
  opacity: 0;
}

.link-label.visible { opacity: 1; }

.node circle {
  stroke-width: 2;
  cursor: pointer;
  transition: stroke-width 0.15s;
}

.node circle:hover { stroke-width: 3; }
.node.selected circle { stroke: #fff; stroke-width: 3; }

.node text {
  font-size: 11px;
  fill: var(--text-dim);
  pointer-events: none;
  text-anchor: middle;
  dominant-baseline: hanging;
}

.node.selected text { fill: var(--text); font-weight: 600; }

.node .expand-badge {
  font-size: 10px;
  fill: var(--bg);
  pointer-events: none;
  text-anchor: middle;
  dominant-baseline: central;
  font-weight: 700;
}

marker path { fill: #30363d; }

aside {
  width: 320px;
  background: var(--surface);
  border-left: 1px solid var(--border);
  overflow-y: auto;
  flex-shrink: 0;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

aside h2 {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 4px;
}

aside h3 {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  padding: 4px 0;
  font-size: 13px;
}

.detail-row .label { color: var(--text-dim); }
.detail-row .value { color: var(--text); font-weight: 500; text-align: right; max-width: 180px; word-break: break-word; }

.type-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
}

.rel-item {
  padding: 6px 0;
  border-bottom: 1px solid var(--border);
  font-size: 12px;
  cursor: pointer;
}

.rel-item:hover { color: var(--accent); }
.rel-item:last-child { border-bottom: none; }

.rel-arrow { color: var(--text-dim); margin: 0 4px; }

button {
  padding: 8px 16px;
  background: var(--accent);
  color: var(--bg);
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  width: 100%;
}

button:hover { opacity: 0.9; }
button:disabled { opacity: 0.4; cursor: default; }
button.secondary { background: var(--border); color: var(--text); }

footer {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 8px 20px;
  background: var(--surface);
  border-top: 1px solid var(--border);
  flex-shrink: 0;
  flex-wrap: wrap;
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: var(--text-dim);
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}

.hint {
  margin-left: auto;
  font-size: 11px;
  color: var(--text-dim);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 12px;
  color: var(--text-dim);
}

.empty-state h2 { color: var(--text); font-size: 18px; }
</style>
</head>
<body>

<header>
  <h1>ontograph</h1>
  <div id="stats-bar"></div>
</header>

<main>
  <div id="graph-container">
    <svg id="graph"></svg>
  </div>
  <aside id="sidebar">
    <div class="empty-state">
      <h2>Select a node</h2>
      <p>Click any node to see details. Double-click to expand its connections.</p>
    </div>
  </aside>
</main>

<footer id="footer"></footer>

<script>
// ── Constants ──
const TYPE_COLORS = {
  person: '#58a6ff',
  project: '#3fb950',
  album: '#d2a8ff',
  organization: '#f0883e',
  award: '#f778ba',
  topic: '#79c0ff',
  event: '#ffd33d',
  location: '#56d364',
  single: '#ff7b72',
  team: '#a5d6ff',
  date: '#ffa657',
  document: '#d2a8ff',
};

function typeColor(type) {
  return TYPE_COLORS[type] || '#8b949e';
}

// ── State ──
let nodes = [];
let links = [];
let nodeMap = {};
let linkSet = new Set();
let simulation;
let selectedNodeId = null;
let expandedNodes = new Set();

// ── API ──
async function fetchJSON(url) {
  const res = await fetch(url);
  return res.json();
}

// ── Graph setup ──
const svg = d3.select('#graph');
const defs = svg.append('defs');

// Arrow marker
defs.append('marker')
  .attr('id', 'arrow')
  .attr('viewBox', '0 -5 10 10')
  .attr('refX', 20)
  .attr('refY', 0)
  .attr('markerWidth', 6)
  .attr('markerHeight', 6)
  .attr('orient', 'auto')
  .append('path')
  .attr('d', 'M0,-4L8,0L0,4')
  .attr('fill', '#30363d');

defs.append('marker')
  .attr('id', 'arrow-hl')
  .attr('viewBox', '0 -5 10 10')
  .attr('refX', 20)
  .attr('refY', 0)
  .attr('markerWidth', 6)
  .attr('markerHeight', 6)
  .attr('orient', 'auto')
  .append('path')
  .attr('d', 'M0,-4L8,0L0,4')
  .attr('fill', '#58a6ff');

const g = svg.append('g');
const linkGroup = g.append('g').attr('class', 'links');
const linkLabelGroup = g.append('g').attr('class', 'link-labels');
const nodeGroup = g.append('g').attr('class', 'nodes');

// Zoom
const zoomBehavior = d3.zoom()
  .scaleExtent([0.1, 4])
  .on('zoom', (e) => g.attr('transform', e.transform));
svg.call(zoomBehavior);

// Click on background to deselect
svg.on('click', (e) => {
  if (e.target === svg.node()) {
    selectedNodeId = null;
    updateSelection();
    renderSidebar(null);
  }
});

function nodeRadius(d) {
  const count = d.connection_count || 0;
  return Math.max(10, Math.min(35, 10 + Math.sqrt(count) * 4));
}

// ── Merge data from API response ──
function mergeData(data) {
  if (!data.center) return;

  const center = data.center;
  if (!nodeMap[center.id]) {
    center.connection_count = data.center_connection_count || data.total_connections || 0;
    nodes.push(center);
    nodeMap[center.id] = center;
  } else {
    nodeMap[center.id].connection_count = data.center_connection_count || data.total_connections || nodeMap[center.id].connection_count;
  }

  for (const conn of data.connections) {
    const entity = conn.entity;
    if (!nodeMap[entity.id]) {
      entity.connection_count = conn.connection_count || 0;
      // Position near the center node
      const centerNode = nodeMap[center.id];
      if (centerNode.x != null) {
        entity.x = centerNode.x + (Math.random() - 0.5) * 100;
        entity.y = centerNode.y + (Math.random() - 0.5) * 100;
      }
      nodes.push(entity);
      nodeMap[entity.id] = entity;
    }

    const rel = conn.relationship;
    const sourceId = rel.is_outgoing ? center.id : entity.id;
    const targetId = rel.is_outgoing ? entity.id : center.id;
    const linkKey = `${sourceId}-${targetId}-${rel.type}`;

    if (!linkSet.has(linkKey)) {
      linkSet.add(linkKey);
      links.push({
        source: sourceId,
        target: targetId,
        type: rel.type,
        directed: rel.directed,
        id: linkKey,
      });
    }
  }
}

// ── Render graph ──
function updateGraph() {
  const width = document.getElementById('graph-container').clientWidth;
  const height = document.getElementById('graph-container').clientHeight;

  // Links
  const linkSel = linkGroup.selectAll('.link')
    .data(links, d => d.id);

  linkSel.exit().remove();

  const linkEnter = linkSel.enter()
    .append('line')
    .attr('class', 'link')
    .attr('marker-end', d => d.directed ? 'url(#arrow)' : null);

  // Link labels
  const labelSel = linkLabelGroup.selectAll('.link-label')
    .data(links, d => d.id);

  labelSel.exit().remove();

  labelSel.enter()
    .append('text')
    .attr('class', 'link-label')
    .text(d => d.type);

  // Nodes
  const nodeSel = nodeGroup.selectAll('.node')
    .data(nodes, d => d.id);

  nodeSel.exit().remove();

  const nodeEnter = nodeSel.enter()
    .append('g')
    .attr('class', 'node')
    .call(d3.drag()
      .on('start', dragStarted)
      .on('drag', dragged)
      .on('end', dragEnded));

  nodeEnter.append('circle')
    .attr('r', d => nodeRadius(d))
    .attr('fill', d => typeColor(d.entity_type))
    .attr('stroke', d => d3.color(typeColor(d.entity_type)).darker(0.5));

  // Expand badge for unexpanded nodes with connections
  nodeEnter.append('text')
    .attr('class', 'expand-badge')
    .attr('dy', 1)
    .text(d => (d.connection_count > 0 && !expandedNodes.has(d.id)) ? '+' : '');

  nodeEnter.append('text')
    .attr('dy', d => nodeRadius(d) + 14)
    .text(d => d.name.length > 20 ? d.name.slice(0, 18) + '...' : d.name);

  // Click to select
  nodeEnter.on('click', (e, d) => {
    e.stopPropagation();
    selectedNodeId = d.id;
    updateSelection();
    renderSidebar(d);
  });

  // Double-click to expand
  nodeEnter.on('dblclick', async (e, d) => {
    e.stopPropagation();
    await expandNode(d.id);
  });

  // Simulation
  if (simulation) simulation.stop();

  simulation = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(links).id(d => d.id).distance(140))
    .force('charge', d3.forceManyBody().strength(-350))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collide', d3.forceCollide().radius(d => nodeRadius(d) + 15))
    .alphaDecay(0.025)
    .on('tick', ticked);

  // Center view on first render
  if (nodes.length <= 2) {
    svg.call(zoomBehavior.transform, d3.zoomIdentity.translate(width/2, height/2).scale(1));
  }

  updateSelection();
}

function ticked() {
  linkGroup.selectAll('.link')
    .attr('x1', d => d.source.x)
    .attr('y1', d => d.source.y)
    .attr('x2', d => d.target.x)
    .attr('y2', d => d.target.y);

  linkLabelGroup.selectAll('.link-label')
    .attr('x', d => (d.source.x + d.target.x) / 2)
    .attr('y', d => (d.source.y + d.target.y) / 2);

  nodeGroup.selectAll('.node')
    .attr('transform', d => `translate(${d.x},${d.y})`);
}

function updateSelection() {
  const connectedLinks = new Set();
  const connectedNodes = new Set();

  if (selectedNodeId) {
    connectedNodes.add(selectedNodeId);
    links.forEach(l => {
      const sid = typeof l.source === 'object' ? l.source.id : l.source;
      const tid = typeof l.target === 'object' ? l.target.id : l.target;
      if (sid === selectedNodeId || tid === selectedNodeId) {
        connectedLinks.add(l.id);
        connectedNodes.add(sid);
        connectedNodes.add(tid);
      }
    });
  }

  nodeGroup.selectAll('.node')
    .classed('selected', d => d.id === selectedNodeId)
    .style('opacity', d => selectedNodeId ? (connectedNodes.has(d.id) ? 1 : 0.2) : 1);

  linkGroup.selectAll('.link')
    .classed('highlighted', d => connectedLinks.has(d.id))
    .attr('marker-end', d => {
      if (!d.directed) return null;
      return connectedLinks.has(d.id) ? 'url(#arrow-hl)' : 'url(#arrow)';
    })
    .style('opacity', d => selectedNodeId ? (connectedLinks.has(d.id) ? 1 : 0.08) : 1);

  linkLabelGroup.selectAll('.link-label')
    .classed('visible', d => connectedLinks.has(d.id));
}

// ── Drag ──
function dragStarted(e, d) {
  if (!e.active) simulation.alphaTarget(0.3).restart();
  d.fx = d.x;
  d.fy = d.y;
}

function dragged(e, d) {
  d.fx = e.x;
  d.fy = e.y;
}

function dragEnded(e, d) {
  if (!e.active) simulation.alphaTarget(0);
  d.fx = null;
  d.fy = null;
}

// ── Expand node ──
async function expandNode(id) {
  if (expandedNodes.has(id)) return;
  expandedNodes.add(id);

  const data = await fetchJSON(`/api/expand/${id}`);
  mergeData(data);
  updateGraph();

  // Update badge
  nodeGroup.selectAll('.expand-badge')
    .text(d => (d.connection_count > 0 && !expandedNodes.has(d.id)) ? '+' : '');

  // Select the expanded node
  selectedNodeId = id;
  updateSelection();
  renderSidebar(nodeMap[id]);
}

// ── Sidebar ──
function renderSidebar(node) {
  const sidebar = document.getElementById('sidebar');

  if (!node) {
    sidebar.innerHTML = `
      <div class="empty-state">
        <h2>Select a node</h2>
        <p>Click any node to see details.<br>Double-click to expand connections.</p>
      </div>`;
    return;
  }

  const attrs = node.attributes || {};
  const attrKeys = Object.keys(attrs).filter(k => !k.startsWith('_'));

  // Find connected relationships
  const rels = links.filter(l => {
    const sid = typeof l.source === 'object' ? l.source.id : l.source;
    const tid = typeof l.target === 'object' ? l.target.id : l.target;
    return sid === node.id || tid === node.id;
  });

  let html = `
    <div>
      <h2>${escHtml(node.name)}</h2>
      <span class="type-badge" style="background:${typeColor(node.entity_type)}22;color:${typeColor(node.entity_type)}">${escHtml(node.entity_type)}</span>
    </div>
    <div>
      <div class="detail-row">
        <span class="label">ID</span>
        <span class="value" style="font-family:monospace;font-size:12px">${node.id}</span>
      </div>
      <div class="detail-row">
        <span class="label">Connections</span>
        <span class="value">${node.connection_count || 0} total</span>
      </div>
    </div>`;

  if (attrKeys.length > 0) {
    html += `<div><h3>Attributes</h3>`;
    for (const key of attrKeys) {
      let val = attrs[key];
      if (Array.isArray(val)) val = val.join(', ');
      if (typeof val === 'object') val = JSON.stringify(val);
      html += `<div class="detail-row">
        <span class="label">${escHtml(key)}</span>
        <span class="value">${escHtml(String(val))}</span>
      </div>`;
    }
    html += `</div>`;
  }

  const fileRefs = node.file_refs || [];
  if (fileRefs.length > 0) {
    html += `<div><h3>File References (${fileRefs.length})</h3>`;
    for (const ref of fileRefs) {
      const fname = ref.split('/').pop();
      html += `<div class="detail-row">
        <span class="value" style="font-size:12px;font-family:monospace;text-align:left;max-width:100%;word-break:break-all" title="${escHtml(ref)}">${escHtml(fname)}</span>
      </div>`;
    }
    html += `</div>`;
  }

  if (rels.length > 0) {
    html += `<div><h3>Relationships (${rels.length})</h3>`;
    for (const l of rels) {
      const sid = typeof l.source === 'object' ? l.source.id : l.source;
      const tid = typeof l.target === 'object' ? l.target.id : l.target;
      const otherId = sid === node.id ? tid : sid;
      const other = nodeMap[otherId];
      if (!other) continue;
      const arrow = sid === node.id ? '&rarr;' : '&larr;';
      html += `<div class="rel-item" onclick="clickRelNode('${otherId}')">
        <span style="color:${typeColor(l.type === node.entity_type ? other.entity_type : other.entity_type)}">${escHtml(other.name)}</span>
        <span class="rel-arrow">${arrow}</span>
        <span style="color:var(--text-dim)">${escHtml(l.type)}</span>
      </div>`;
    }
    html += `</div>`;
  }

  const isExpanded = expandedNodes.has(node.id);
  html += `<button onclick="expandNode('${node.id}')" ${isExpanded ? 'disabled' : ''}>
    ${isExpanded ? 'Expanded' : 'Expand connections'}
  </button>`;
  html += `<button class="secondary" onclick="resetView()">Reset to hub</button>`;

  sidebar.innerHTML = html;
}

function clickRelNode(id) {
  selectedNodeId = id;
  updateSelection();
  renderSidebar(nodeMap[id]);
}

function escHtml(s) {
  const div = document.createElement('div');
  div.textContent = s;
  return div.innerHTML;
}

// ── Stats bar ──
function renderStats(stats) {
  const bar = document.getElementById('stats-bar');
  bar.innerHTML = `
    <span class="stat-pill">entities <span class="val">${stats.entities}</span></span>
    <span class="stat-pill">relationships <span class="val">${stats.relationships}</span></span>
    <span class="stat-pill">documents <span class="val">${stats.documents}</span></span>
    <span class="stat-pill">aliases <span class="val">${stats.aliases}</span></span>`;
}

// ── Legend ──
function renderLegend(typeColors) {
  const footer = document.getElementById('footer');
  let html = '';
  for (const [type, color] of Object.entries(typeColors)) {
    html += `<span class="legend-item"><span class="legend-dot" style="background:${color}"></span>${type}</span>`;
  }
  html += `<span class="hint">click to select &middot; double-click to expand &middot; drag to move &middot; scroll to zoom</span>`;
  footer.innerHTML = html;
}

// ── Reset ──
async function resetView() {
  nodes = [];
  links = [];
  nodeMap = {};
  linkSet = new Set();
  expandedNodes = new Set();
  selectedNodeId = null;

  linkGroup.selectAll('.link').remove();
  linkLabelGroup.selectAll('.link-label').remove();
  nodeGroup.selectAll('.node').remove();

  const hub = await fetchJSON('/api/hub');
  mergeData(hub);
  if (hub.center) expandedNodes.add(hub.center.id);
  updateGraph();

  if (hub.center) {
    selectedNodeId = hub.center.id;
    updateSelection();
    renderSidebar(nodeMap[hub.center.id]);
  }

  // Reset zoom
  const width = document.getElementById('graph-container').clientWidth;
  const height = document.getElementById('graph-container').clientHeight;
  svg.transition().duration(500).call(
    zoomBehavior.transform,
    d3.zoomIdentity.translate(0, 0).scale(1)
  );
}

// ── Init ──
async function init() {
  const stats = await fetchJSON('/api/stats');
  renderStats(stats);

  // Build legend from actual types
  const legendColors = {};
  for (const type of Object.keys(stats.type_counts || {})) {
    legendColors[type] = typeColor(type);
  }
  renderLegend(legendColors);

  if (stats.entities === 0) {
    document.getElementById('graph-container').innerHTML = `
      <div class="empty-state">
        <h2>Empty graph</h2>
        <p>No entities found. Ingest some data first:</p>
        <code style="color:var(--accent);margin-top:8px">ontograph ingest --text "your text here"</code>
      </div>`;
    return;
  }

  const hub = await fetchJSON('/api/hub');
  mergeData(hub);
  if (hub.center) expandedNodes.add(hub.center.id);
  updateGraph();

  // Auto-select hub
  if (hub.center) {
    selectedNodeId = hub.center.id;
    updateSelection();
    renderSidebar(nodeMap[hub.center.id]);
  }
}

init();
</script>
</body>
</html>
"""
