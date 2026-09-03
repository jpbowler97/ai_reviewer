# /// script
# requires-python = ">=3.11"
# dependencies = ["fastapi>=0.110", "uvicorn>=0.29", "python-multipart>=0.0.9", "anthropic>=1", "pydantic>=2", "openpyxl>=3.1"]
# ///
"""Browser UI for human review. Start with:  uv run app.py   then open http://localhost:8000

Drop a CSV of applications, the model screens them, you work through the review queue one row at a time
and record your decision. Decisions are saved to results/<set>_decisions.csv as you go; Export merges them
with the model's output.
"""
import csv, io, os, sys, threading, time
from datetime import datetime
from pathlib import Path

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

import screen

HERE = Path(__file__).parent
RESULTS, UPLOADS = HERE / "results", HERE / "data/uploads"
app = FastAPI()
JOBS: dict[str, dict] = {}


def decisions_path(name: str) -> Path:
    return RESULTS / f"{name}_decisions.csv"


def load_decisions(name: str) -> dict:
    p = decisions_path(name)
    if not p.exists():
        return {}
    return {r[screen.ID]: r for r in csv.DictReader(p.open(encoding="utf-8"))}


def load_set(name: str) -> list[dict]:
    p = RESULTS / f"{name}.csv"
    if not p.exists():
        raise HTTPException(404, f"No results for {name}")
    rows = list(csv.DictReader(p.open(encoding="utf-8")))
    dec = load_decisions(name)
    for r in rows:
        d = dec.get(r[screen.ID], {})
        r["Reviewer decision"] = d.get("Reviewer decision", "")
        r["Reviewer note"] = d.get("Reviewer note", "")
    return rows


def screen_in_background(name: str, rows: list[dict], rerun: bool) -> None:
    job = JOBS[name]
    try:
        def progress(done, total):
            job.update(done=done, total=total)
        results = screen.run(rows, RESULTS / name, rerun, progress)
        screen.write_outputs(rows, results, RESULTS / name)
        job.update(status="done")
    except Exception as e:  # surfaced to the browser
        job.update(status="error", error=str(e))


@app.get("/", response_class=HTMLResponse)
def index():
    return HTML


@app.get("/favicon.ico")
def favicon():
    return JSONResponse(None, status_code=204)


@app.get("/api/sets")
def sets():
    names = sorted(p.stem for p in RESULTS.glob("*.csv") if not p.stem.endswith("_decisions"))
    return {"sets": names}


@app.post("/api/upload")
async def upload(file: UploadFile = File(...), rescreen: bool = Form(False)):
    if "ANTHROPIC_API_KEY" not in os.environ:
        raise HTTPException(400, "ANTHROPIC_API_KEY is not set in the shell that started the app.")
    text = (await file.read()).decode("utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(text)))
    need = [screen.ID, screen.NAME, *screen.FIELDS]
    missing = [c for c in need if not rows or c not in rows[0]]
    if missing:
        raise HTTPException(400, f"CSV is missing columns: {missing}. Needed: {need}")
    name = Path(file.filename).stem
    UPLOADS.mkdir(parents=True, exist_ok=True)
    (UPLOADS / f"{name}.csv").write_text(text, encoding="utf-8")
    JOBS[name] = {"status": "running", "done": 0, "total": len(rows)}
    threading.Thread(target=screen_in_background, args=(name, rows, rescreen), daemon=True).start()
    return {"set": name, "total": len(rows)}


@app.get("/api/status/{name}")
def status(name: str):
    return JOBS.get(name, {"status": "done" if (RESULTS / f"{name}.csv").exists() else "unknown"})


@app.get("/api/set/{name}")
def get_set(name: str):
    rows = load_set(name)
    return {"rows": rows, "fields": screen.FIELDS}


@app.post("/api/decision")
async def decision(payload: dict):
    name, cid = payload["set"], payload["id"]
    dec = load_decisions(name)
    tool = next((r["Overall decision"] for r in load_set(name) if r[screen.ID] == cid), "")
    dec[cid] = {screen.ID: cid, "Tool decision": tool, "Reviewer decision": payload.get("decision", ""),
                "Reviewer note": payload.get("note", ""), "Timestamp": datetime.now().isoformat(timespec="seconds")}
    with decisions_path(name).open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=[screen.ID, "Tool decision", "Reviewer decision", "Reviewer note", "Timestamp"])
        w.writeheader(); w.writerows(dec.values())
    return {"ok": True, "decided": len([d for d in dec.values() if d["Reviewer decision"]])}


@app.get("/api/export/{name}")
def export(name: str):
    rows = load_set(name)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=screen.COLS); w.writeheader(); w.writerows(rows)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="{name}_reviewed.csv"'})


HTML = r"""<!doctype html><html><head><meta charset="utf-8"><title>Application screener</title>
<style>
:root{font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;font-size:14px;color:#222}
body{margin:0;background:#f6f7f9}
header{background:#fff;border-bottom:1px solid #ddd;padding:12px 20px;display:flex;align-items:baseline;gap:16px}
header h1{font-size:18px;margin:0}header .sub{color:#666}
main{padding:16px 20px;max-width:1500px;margin:0 auto}
#drop{border:2px dashed #9aa;border-radius:8px;padding:28px;text-align:center;background:#fff;cursor:pointer}
#drop.over{background:#eef4ff;border-color:#4a7}
.row{display:flex;gap:12px;align-items:center;margin:10px 0;flex-wrap:wrap}
button{border:1px solid #bbb;background:#fff;border-radius:6px;padding:6px 12px;cursor:pointer;font-size:13px}
button.primary{background:#2b6cb0;color:#fff;border-color:#2b6cb0}button.ok{background:#2f855a;color:#fff;border-color:#2f855a}
button.no{background:#c53030;color:#fff;border-color:#c53030}button:disabled{opacity:.5;cursor:default}
.chips{display:flex;gap:10px;flex-wrap:wrap;margin:8px 0 14px}.chip{background:#fff;border:1px solid #ddd;border-radius:16px;padding:4px 12px}
.chip b{margin-right:4px}
#layout{display:grid;grid-template-columns:minmax(420px,1fr) minmax(480px,1.2fr);gap:16px}
table{width:100%;border-collapse:collapse;background:#fff;font-size:13px}
th{background:#d9e2f3;text-align:left;padding:6px 8px;position:sticky;top:0}
td{padding:6px 8px;border-top:1px solid #eee;vertical-align:top;cursor:pointer}
tr.sel td{background:#fff7d6}tr.done td{color:#777}
.tag{display:inline-block;border-radius:4px;padding:1px 6px;font-size:12px;white-space:nowrap}
.tag.p{background:#e2efda}.tag.d{background:#ededed}.tag.f{background:#fde2e2}
.panel{background:#fff;border:1px solid #ddd;border-radius:8px;padding:14px 16px}
.panel h2{margin:0 0 4px;font-size:17px}.muted{color:#666}
.gate{display:grid;grid-template-columns:160px 1fr;gap:6px 12px;margin:10px 0}
.gate .k{font-weight:600}.score{font-size:22px;font-weight:700}
textarea{width:100%;box-sizing:border-box;min-height:56px;border:1px solid #ccc;border-radius:6px;padding:6px;font:inherit}
details{margin-top:10px}summary{cursor:pointer;font-weight:600}pre{white-space:pre-wrap;font:inherit;background:#fafafa;border:1px solid #eee;padding:10px;border-radius:6px;max-height:340px;overflow:auto}
#bar{height:10px;background:#e5e7eb;border-radius:5px;overflow:hidden;margin-top:8px}#bar div{height:100%;background:#2b6cb0;width:0}
.small{font-size:12px}.hidden{display:none}
</style></head><body>
<header><h1>Application screener</h1><span class="sub">The model screens every application against the rubric and explains each score. You decide.</span></header>
<main>
<section id="start">
  <div id="drop">Drop a CSV of applications here, or click to choose<br><span class="small muted">Columns: Synthetic ID, Synthetic name, CV text, AI-risk view shift, Hardest problem</span></div>
  <input type="file" id="file" accept=".csv" class="hidden">
  <div class="row"><label><input type="checkbox" id="rescreen"> Re-screen even if this file was screened before</label>
    <span class="muted">or open an earlier run:</span><select id="sets"></select><button id="open">Open</button></div>
  <div id="progress" class="hidden"><span id="ptext"></span><div id="bar"><div></div></div></div>
</section>
<section id="review" class="hidden">
  <div class="row"><button id="back">&larr; New file</button><b id="setname"></b><span style="flex:1"></span><button id="export" class="primary">Export reviewed CSV</button></div>
  <div class="chips" id="chips"></div>
  <div id="layout">
    <div>
      <table id="queue"><thead><tr><th>#</th><th>Applicant</th><th>Model says</th><th>Score</th><th>Why</th><th>You</th></tr></thead><tbody></tbody></table>
      <details id="filtered"><summary></summary><table id="ftable"><thead><tr><th>Applicant</th><th>Model says</th><th>Score</th><th>Why</th><th>You</th></tr></thead><tbody></tbody></table></details>
    </div>
    <div class="panel" id="detail"><p class="muted">Select a row. Keys: j / k move, a agree, p progress, d do not progress.</p></div>
  </div>
</section>
</main>
<script>
const $=s=>document.querySelector(s);let SET=null,ROWS=[],FIELDS=[],SEL=null;
const drop=$('#drop'),file=$('#file');
drop.onclick=()=>file.click();
['dragenter','dragover'].forEach(e=>drop.addEventListener(e,ev=>{ev.preventDefault();drop.classList.add('over')}));
['dragleave','drop'].forEach(e=>drop.addEventListener(e,ev=>{ev.preventDefault();drop.classList.remove('over')}));
drop.addEventListener('drop',ev=>upload(ev.dataTransfer.files[0]));file.onchange=()=>upload(file.files[0]);
async function upload(f){if(!f)return;const fd=new FormData();fd.append('file',f);fd.append('rescreen',$('#rescreen').checked);
 const r=await fetch('/api/upload',{method:'POST',body:fd});const j=await r.json();if(!r.ok){alert(j.detail);return}
 $('#progress').classList.remove('hidden');poll(j.set,j.total)}
async function poll(name,total){const s=await (await fetch('/api/status/'+name)).json();
 if(s.status==='error'){alert('Screening failed: '+s.error);$('#progress').classList.add('hidden');return}
 if(s.status==='running'){$('#ptext').textContent=`Screening ${s.done} of ${s.total} applications (one model call each)`;$('#bar div').style.width=(100*s.done/Math.max(1,s.total))+'%';setTimeout(()=>poll(name,total),700);return}
 $('#ptext').textContent='Done';$('#bar div').style.width='100%';openSet(name)}
async function loadSets(){const j=await (await fetch('/api/sets')).json();$('#sets').innerHTML=j.sets.map(s=>`<option>${s}</option>`).join('')}
$('#open').onclick=()=>openSet($('#sets').value);$('#back').onclick=()=>{$('#review').classList.add('hidden');$('#start').classList.remove('hidden');$('#progress').classList.add('hidden');loadSets()};
$('#export').onclick=()=>location.href='/api/export/'+SET;
function setHash(n){history.replaceState(null,'','#set='+n)}
async function openSet(name){SET=name;setHash(name);const j=await (await fetch('/api/set/'+name)).json();ROWS=j.rows;FIELDS=j.fields;
 $('#start').classList.add('hidden');$('#review').classList.remove('hidden');$('#setname').textContent=name;render();
 const first=ROWS.findIndex(r=>r.Queue==='Review'&&!r['Reviewer decision']);select(first>=0?first:0)}
function tag(d){return d==='Progress'?'<span class="tag p">Progress</span>':d==='Do not progress'?'<span class="tag d">Do not progress</span>':d?`<span class="tag">${d}</span>`:''}
function render(){const rev=ROWS.filter(r=>r.Queue==='Review'),fil=ROWS.filter(r=>r.Queue!=='Review'),dec=ROWS.filter(r=>r['Reviewer decision']).length;
 const prog=ROWS.filter(r=>r['Overall decision']==='Progress').length;
 $('#chips').innerHTML=`<span class="chip"><b>${ROWS.length}</b>screened by the model</span><span class="chip"><b>${prog}</b>recommended Progress</span><span class="chip"><b>${rev.length}</b>for your review</span><span class="chip"><b>${fil.length}</b>filtered out automatically (listed below, still yours to overturn)</span><span class="chip"><b>${dec}</b>decided by you</span>`;
 $('#queue tbody').innerHTML=rev.map((r,i)=>row(r,i+1,true)).join('');
 $('#filtered summary').textContent=`Filtered out (${fil.length}): manipulation attempts, impressiveness 0 to 1, or impressiveness 2 with low safety motivation`;
 $('#ftable tbody').innerHTML=fil.map(r=>row(r,null,false)).join('');
 document.querySelectorAll('tr[data-i]').forEach(tr=>tr.onclick=()=>select(+tr.dataset.i))}
function row(r,n,num){const i=ROWS.indexOf(r);const you=r['Reviewer decision'];
 return `<tr data-i="${i}" class="${i===SEL?'sel':''} ${you?'done':''}">${num?`<td>${n}</td>`:''}<td><b>${r['Synthetic name']}</b><br><span class="small muted">${r['Synthetic ID']}${r.Flags?' &middot; <span class="tag f">'+r.Flags+'</span>':''}</span></td><td>${tag(r['Overall decision'])}</td><td>${r['Score /10']}</td><td class="small">${r.Why}</td><td>${you?tag(you):'<span class="muted small">pending</span>'}</td></tr>`}
function select(i){SEL=i;const r=ROWS[i];if(!r)return;render();document.querySelector(`tr[data-i="${i}"]`)?.scrollIntoView({block:'nearest'});
 $('#detail').innerHTML=`<h2>${r['Synthetic name']} <span class="muted small">${r['Synthetic ID']} &middot; ${r.Queue==='Review'?'review queue':'filtered out'}</span></h2>
 <div class="row"><span class="score">${r['Score /10']}<span class="muted small">/10</span></span>${tag(r['Overall decision'])}<span class="muted">${r.Why}</span>${r.Flags?'<span class="tag f">'+r.Flags+'</span>':''}</div>
 <div class="gate"><span class="k">Impressiveness ${r['Impressiveness /5']}/5 <span class="muted small">(hard gate, pass at 3)</span></span><span>${r['Impressiveness reason']}</span>
 <span class="k">Safety motivation ${r['Safety /5']}/5 <span class="muted small">(adds to score)</span></span><span>${r['Safety reason']}</span></div>
 <div class="row"><b>Your decision</b><button class="ok" onclick="decide('${r['Overall decision']}')">Agree with model</button><button onclick="decide('Progress')">Progress</button><button onclick="decide('Do not progress')">Do not progress</button><span class="muted">${r['Reviewer decision']?'Recorded: '+r['Reviewer decision']:'not yet decided'}</span></div>
 <textarea id="note" placeholder="Note (optional): what you checked, what you disagree with">${r['Reviewer note']||''}</textarea>
 <div class="row"><button onclick="next()">Next undecided &rarr;</button></div>
 ${FIELDS.map(f=>`<details ${f!=='CV text'?'open':''}><summary>${f}</summary><pre>${esc(r[f])}</pre></details>`).join('')}`}
function esc(s){return (s||'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]))}
async function decide(d){const r=ROWS[SEL];const note=$('#note').value;
 await fetch('/api/decision',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({set:SET,id:r['Synthetic ID'],decision:d,note})});
 r['Reviewer decision']=d;r['Reviewer note']=note;next()}
function next(){const order=[...ROWS.filter(r=>r.Queue==='Review'),...ROWS.filter(r=>r.Queue!=='Review')];const cur=order.indexOf(ROWS[SEL]);
 const nxt=order.slice(cur+1).find(r=>!r['Reviewer decision'])||order.find(r=>!r['Reviewer decision']);select(nxt?ROWS.indexOf(nxt):SEL)}
document.addEventListener('keydown',e=>{if($('#review').classList.contains('hidden')||e.target.tagName==='TEXTAREA')return;
 const order=[...ROWS.filter(r=>r.Queue==='Review'),...ROWS.filter(r=>r.Queue!=='Review')];const cur=order.indexOf(ROWS[SEL]);
 if(e.key==='j'&&cur<order.length-1)select(ROWS.indexOf(order[cur+1]));if(e.key==='k'&&cur>0)select(ROWS.indexOf(order[cur-1]));
 if(e.key==='a')decide(ROWS[SEL]['Overall decision']);if(e.key==='p')decide('Progress');if(e.key==='d')decide('Do not progress')});
loadSets().then(()=>{const m=location.hash.match(/set=([\w.-]+)/);if(m)openSet(m[1])});
</script></body></html>"""


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"Open http://localhost:{port}", file=sys.stderr)
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
