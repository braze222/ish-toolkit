"""Loopback-only dashboard. This server deliberately exposes read-only APIs."""
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse,parse_qs
import json
from . import __version__
from .engine import OPPORTUNITIES,match_opportunities
from .evidence import list_evidence

PAGE=r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Elmatrix Standalone</title><style>
:root{color-scheme:dark}body{margin:0;background:#0b1018;color:#edf2fb;font:16px system-ui}main{max-width:1050px;margin:auto;padding:24px}h1{letter-spacing:-.04em}p,small{color:#a8b4c9}.panel{background:#141d2b;border:1px solid #2a374c;border-radius:16px;padding:16px;margin:14px 0}.controls{display:flex;gap:12px;flex-wrap:wrap}label{display:grid;gap:6px;color:#b9c5d8}input{background:#0b1018;color:#fff;border:1px solid #394963;border-radius:8px;padding:10px;max-width:100%}button{padding:10px 14px;border:0;border-radius:8px;background:#b9f39a;color:#152019;font-weight:700;cursor:pointer}article{padding:14px 0;border-top:1px solid #2a374c}.score{float:right;color:#b9f39a;font-weight:700}.tag{display:inline-block;border:1px solid #3a4962;border-radius:20px;padding:3px 8px;margin:4px;font-size:12px;color:#c2cce0}.notice{border-left:3px solid #e6c66d;padding-left:12px}</style></head><body><main><h1>ELMATRIX <small>STANDALONE / 0.3.0</small></h1><p>Source-aware research prototype. Starter opportunities are hypotheses, not claims of profitability.</p><section class="panel"><div class="controls"><label>Budget<input id="budget" type="number" min="0" value="0"></label><label>Hours / week<input id="hours" type="number" min="1" max="168" value="5"></label><label>Skills, comma-separated<input id="skills" value="writing,research"></label><label>Business models<input id="models" value="service,digital-products"></label><label>Region<input id="region" value="ZA"></label></div><p><button id="match">Match opportunities</button> <button id="all">Show catalog</button> <button id="evidence">View collected evidence</button></p><p class="notice">Research records are not automatically attributed to a niche. Review relevance before treating any source as support for a market claim.</p></section><section id="results" aria-live="polite"></section><script>
const root=document.querySelector('#results');
function el(tag,text,cls){const n=document.createElement(tag);n.textContent=text;if(cls)n.className=cls;return n}
async function load(path){root.replaceChildren(el('p','Loading…'));try{const response=await fetch(path);if(!response.ok)throw Error('HTTP '+response.status);const data=await response.json();root.replaceChildren();if(path.startsWith('/api/evidence')){root.append(el('h2','Collected source observations'));if(!data.length)root.append(el('p','No evidence collected yet. Use the CLI research command to collect a permitted public RSS/Atom feed.'));for(const x of data){const a=el('article','');a.append(el('strong',x.title),el('p',x.observation),el('p',x.source_name+' · retrieved '+x.retrieved_at),el('a',x.canonical_url));if(/^https?:\/\//i.test(x.canonical_url))a.lastChild.href=x.canonical_url;a.lastChild.target='_blank';a.lastChild.rel='noopener noreferrer';root.append(a)}return}for(const x of data){const a=el('article','', 'panel');a.append(el('strong',x.title));if(x.score!==undefined)a.append(el('span',x.score+' / 100','score'));a.append(el('p',x.customer+' — '+x.offer));const tags=el('div','');for(const t of [x.category,...x.models])tags.append(el('span',t,'tag'));a.append(tags);a.append(el('p','Validation: '+x.validation));a.append(el('p',x.score_type||'Starter hypothesis; unverified.'));root.append(a)}}catch(e){root.replaceChildren(el('p','Request failed: '+e.message))}}
document.querySelector('#match').onclick=()=>{const q=new URLSearchParams();for(const k of ['budget','hours','skills','models','region'])q.set(k,document.querySelector('#'+k).value);load('/api/match?'+q)};
document.querySelector('#all').onclick=()=>load('/api/opportunities');
document.querySelector('#evidence').onclick=()=>load('/api/evidence');
document.querySelector('#match').click();
</script></main></body></html>"""

class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def send_body(self,status,body,ctype):
        self.send_response(status);self.send_header("Content-Type",ctype);self.send_header("Content-Length",str(len(body)));self.send_header("X-Content-Type-Options","nosniff");self.send_header("Content-Security-Policy","default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'");self.send_header("Cache-Control","no-store");self.send_header("Referrer-Policy","no-referrer");self.end_headers();self.wfile.write(body)
    def do_GET(self):
        allowed = {"127.0.0.1:" + str(self.server.server_port), "localhost:" + str(self.server.server_port)}
        hosts = self.headers.get_all('Host', [])
        origins = self.headers.get_all('Origin', [])
        if len(hosts) != 1 or hosts[0] not in allowed or (origins and (len(origins) != 1 or origins[0] != 'http://' + hosts[0])):
            self.send_body(403,b'{"error":"local origin required"}',"application/json"); return
        if len(self.path) > 4096 or not self.path.startswith('/'):
            self.send_body(400,b'{"error":"invalid request"}',"application/json"); return
        try:
            u=urlparse(self.path)
            if u.path=="/": self.send_body(200,PAGE.replace("STANDALONE / 0.3.0", "STANDALONE / " + __version__).encode(),"text/html; charset=utf-8");return
            if u.path=="/api/opportunities": rows=[x.to_dict() for x in OPPORTUNITIES]
            elif u.path=="/api/evidence": rows=list_evidence(limit=100)
            elif u.path=="/api/match":
                q=parse_qs(u.query,max_num_fields=5)
                if set(q) - {"budget","hours","skills","models","region"} or any(len(v)!=1 for v in q.values()):
                    raise ValueError("Invalid query parameters.")
                def val(k,d):return q.get(k,[d])[0]
                budget=max(0,min(int(val("budget","0")),10**9));hours=max(1,min(int(val("hours","5")),168))
                rows=match_opportunities(budget=budget,hours=hours,skills=val("skills","").split(","),models=val("models","").split(","),region=val("region","global")[:80])
            else:self.send_body(404,b'{"error":"not found"}',"application/json");return
            self.send_body(200,json.dumps(rows,ensure_ascii=False).encode(),"application/json; charset=utf-8")
        except (ValueError,RuntimeError) as exc:
            self.send_body(400,json.dumps({"error":str(exc)}).encode(),"application/json; charset=utf-8")
        except Exception:
            self.send_body(500,b'{"error":"internal error"}',"application/json")
    def log_message(self,*args):pass

def main():
    server=HTTPServer(("127.0.0.1",8765),Handler)
    print("Elmatrix dashboard: http://127.0.0.1:8765 (loopback only)")
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
if __name__=="__main__":main()
