"""`army serve`: a zero-dependency web playground for every template (binds to localhost by default)."""
from __future__ import annotations

import json
import secrets
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .llm import get_llm

PAGE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Agent Army Playground</title>
<style>
:root{--bg:#0b1026;--panel:#141a3a;--line:#2a3266;--text:#e8ebff;--muted:#9aa3d6;--accent:#22d3ee;--accent2:#8b5cf6}
*{box-sizing:border-box}body{margin:0;font:15px/1.5 system-ui,sans-serif;background:var(--bg);color:var(--text)}
header{padding:16px 24px;border-bottom:1px solid var(--line);display:flex;gap:12px;align-items:center}
header b{font-size:18px}header span{color:var(--muted)}
main{display:grid;grid-template-columns:320px 1fr;min-height:calc(100vh - 60px)}
aside{border-right:1px solid var(--line);overflow:auto;max-height:calc(100vh - 60px)}
input,textarea,select,button{font:inherit;color:inherit}
#q{width:calc(100% - 24px);margin:12px;padding:8px 10px;background:var(--panel);border:1px solid var(--line);border-radius:8px}
.cat{padding:10px 16px 4px;color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.06em}
.t{padding:8px 16px;cursor:pointer;border-left:3px solid transparent}.t:hover{background:var(--panel)}
.t.on{border-left-color:var(--accent);background:var(--panel)}.t small{display:block;color:var(--muted)}
section{padding:24px;max-width:980px}h2{margin:0 0 4px}.about{color:var(--muted);white-space:pre-wrap}
textarea{width:100%;min-height:110px;padding:12px;background:var(--panel);border:1px solid var(--line);border-radius:10px}
.row{display:flex;gap:10px;margin:12px 0;flex-wrap:wrap}.row input{flex:1;min-width:200px;padding:8px 10px;background:var(--panel);border:1px solid var(--line);border-radius:8px}
button{padding:9px 18px;border:0;border-radius:8px;background:linear-gradient(90deg,var(--accent),var(--accent2));color:#0b1026;font-weight:600;cursor:pointer}
button:disabled{opacity:.5}pre{white-space:pre-wrap;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px;overflow:auto}
details{margin-top:12px;color:var(--muted)}@media(max-width:760px){main{grid-template-columns:1fr}aside{max-height:260px}}
</style></head><body>
<header><b>Agent Army</b><span>Playground</span></header>
<main><aside><input id="q" placeholder="Search templates"><div id="list"></div></aside>
<section><h2 id="title">Pick a template</h2><p class="about" id="about"></p>
<textarea id="task" placeholder="Describe the task"></textarea>
<div class="row"><input id="model" placeholder="model, e.g. ollama:llama3.2 (blank = default)"><input id="opts" placeholder='options JSON, e.g. {"docs":"./my-docs"}'><button id="go" disabled>Run</button></div>
<pre id="out">Output appears here.</pre><details><summary>Step trace</summary><pre id="trace"></pre></details></section></main>
<script>
let T=[],cur=null;const $=id=>document.getElementById(id);
fetch('/api/templates').then(r=>r.json()).then(d=>{T=d;draw()});
function draw(){const q=$('q').value.toLowerCase();let html='',last='';
for(const t of T){if(q&&!(t.name+t.title+t.description).toLowerCase().includes(q))continue;
if(t.category_title!==last){html+=`<div class="cat">${t.category_title}</div>`;last=t.category_title}
html+=`<div class="t ${cur&&cur.name===t.name?'on':''}" data-n="${t.name}">${t.title}<small>${t.description}</small></div>`}
$('list').innerHTML=html;document.querySelectorAll('.t').forEach(e=>e.onclick=()=>pick(e.dataset.n))}
function pick(n){cur=T.find(t=>t.name===n);$('title').textContent=cur.title;$('about').textContent=cur.about;$('task').value=cur.example;
$('opts').value=Object.keys(cur.options).length?JSON.stringify(cur.options):'';$('go').disabled=false;draw()}
$('q').oninput=draw;
$('go').onclick=async()=>{$('go').disabled=true;$('out').textContent='Running...';$('trace').textContent='';
let opts={};try{opts=$('opts').value?JSON.parse($('opts').value):{}}catch(e){$('out').textContent='Options must be JSON';$('go').disabled=false;return}
const r=await fetch('/api/run',{method:'POST',headers:{'content-type':'application/json','x-army-token':TOKEN},body:JSON.stringify({template:cur.name,task:$('task').value,model:$('model').value,options:opts})});
const d=await r.json();$('out').textContent=d.error||d.output;
$('trace').textContent=(d.steps||[]).map(s=>`[${s.agent}] ${s.kind}${s.tool?' '+s.tool+'('+JSON.stringify(s.args)+')':''}\n${s.content.slice(0,600)}`).join('\n\n')+(d.seconds?`\n\n${d.seconds}s`:'');
$('go').disabled=false};
</script></body></html>"""


def serve(host: str = "127.0.0.1", port: int = 8765):
    from .cli import CATEGORIES, find, load_templates

    catalog = [
        {
            "name": t.name, "title": t.title, "about": t.about, "description": t.meta["description"],
            "example": t.meta["example"], "category": t.meta["category"],
            "category_title": CATEGORIES[t.meta["category"]], "options": {k: str(v) for k, v in t.options.items()},
        }
        for t in sorted(load_templates(), key=lambda t: list(CATEGORIES).index(t.meta["category"]))
    ]
    lock = threading.Lock()
    token = secrets.token_urlsafe(24)  # only pages served by this process know it
    page = PAGE.replace("<script>", f"<script>const TOKEN={json.dumps(token)};", 1).encode()
    allowed_hosts = {f"{h}:{port}" for h in ("127.0.0.1", "localhost", "[::1]", host)}

    class Handler(BaseHTTPRequestHandler):
        def _send(self, code: int, body: bytes, ctype: str):
            self.send_response(code)
            self.send_header("content-type", ctype)
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _json(self, obj, code: int = 200):
            self._send(code, json.dumps(obj).encode(), "application/json")

        def log_message(self, *a):
            pass

        def _host_ok(self) -> bool:
            # Rejecting unknown Host headers blocks DNS-rebinding pages from talking to the playground.
            if self.headers.get("host", "") in allowed_hosts:
                return True
            self._send(403, b"forbidden host", "text/plain")
            return False

        def do_GET(self):
            if not self._host_ok():
                return
            if self.path == "/":
                self._send(200, page, "text/html; charset=utf-8")
            elif self.path == "/api/templates":
                self._json(catalog)
            else:
                self._send(404, b"not found", "text/plain")

        def do_POST(self):
            if not self._host_ok():
                return
            if self.path != "/api/run":
                return self._send(404, b"not found", "text/plain")
            # Other websites can't read the token or send a custom header without a CORS preflight,
            # so they can't make the playground run agents (and spend your API keys).
            if not secrets.compare_digest(self.headers.get("x-army-token", ""), token):
                return self._json({"error": "missing or invalid playground token; reload the page"}, 403)
            if not self.headers.get("content-type", "").startswith("application/json"):
                return self._json({"error": "content-type must be application/json"}, 415)
            try:
                req = json.loads(self.rfile.read(int(self.headers.get("content-length", 0))))
                t = find(req["template"])
                llm = get_llm(req["model"]) if req.get("model") else None
                started = time.time()
                with lock:  # one run at a time keeps tool sandboxes predictable
                    result = t.build(llm=llm, **(req.get("options") or {})).run(req["task"])
                self._json({
                    "output": result.output, "seconds": round(time.time() - started, 1),
                    "steps": [{"agent": s.agent, "kind": s.kind, "tool": s.tool, "args": s.args, "content": s.content} for s in result.steps],
                })
            except SystemExit as e:
                self._json({"error": str(e)}, 400)
            except Exception as e:
                self._json({"error": f"{type(e).__name__}: {e}", "trace": traceback.format_exc()[-2000:]}, 500)

    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Agent Army playground: http://{host}:{port}  ({len(catalog)} templates, Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
