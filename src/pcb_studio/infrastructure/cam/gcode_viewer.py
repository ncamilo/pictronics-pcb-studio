"""Standalone offline SVG/HTML viewer for validated, comment-only previews."""
import json
from html import escape
from math import dist
from pcb_studio.infrastructure.cam.gcode_readback import read_gcode_preview, compare_gcode_preview

COLORS = {"isolation":"#56e0b2","drill":"#69b9ff","mill_slot":"#c69bff",
          "cutout_internal":"#f1b66e","cutout_external":"#f1b66e"}
LABELS = {"isolation":"Isolation","drill":"Drilling","mill_slot":"Slot milling",
          "cutout_internal":"Internal cutout","cutout_external":"External cutout"}


def viewer_data(trace, text):
    """Only accept a preview that matches its validated CAM source."""
    report = compare_gcode_preview(trace, text)
    parsed = read_gcode_preview(text)
    stages = [{"label":LABELS[b.stage.operation],"color":COLORS[b.stage.operation],
               "tool":b.tool.tool_id,"diameter":b.effective_diameter_mm}
              for b in trace.bound.stages]
    events = [{"kind":e.kind,"stage":e.stage_index,"a":e.start,"b":e.end,
               "feed":e.feed_mm_min} for e in parsed.events]
    points = [parsed.initial]+[e.end for e in parsed.events]
    bounds = [[min(p[i] for p in points),max(p[i] for p in points)] for i in range(3)]
    return {"name":trace.bound.job.project_name,"initial":parsed.initial,"events":events,
            "stages":stages,"bounds":bounds,"safe":parsed.initial[2],
            "moves":report.movement_count,"error":report.max_coordinate_error_mm,
            "diagnostics":list(report_code.code for report_code in trace.bound.job.diagnostics)}


def _projection(bounds,axes,rect):
    x,y,w,h=rect
    a,b=(bounds[i] for i in axes)
    span_a=max(a[1]-a[0],1e-9)
    span_b=max(b[1]-b[0],1e-9)
    scale=min(w/span_a,h/span_b)
    def point(p):
        return (x+w/2+(p[axes[0]]-(a[0]+a[1])/2)*scale,
                y+h/2-(p[axes[1]]-(b[0]+b[1])/2)*scale)
    return point


def render_svg(data):
    """Actual centerlines read back from G-code; two orthographic projections."""
    parts=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 690" role="img" aria-label="Offline toolpath preview">',
           '<rect width="1000" height="690" fill="#101a27"/>',
           '<g font-family="Arial,sans-serif" fill="#e5edf6">',
           '<text x="32" y="38" font-size="24" font-weight="bold">Pictronics PCB Studio | G-code preview</text>',
           f'<text x="32" y="64" font-size="14" fill="#a8bacc">{escape(data["name"])} · {data["moves"]} movements · OFFLINE ONLY</text>']
    for label,axes,rect in (("XY | Top view",(0,1),(50,112,900,330)),
                           ("XZ | Side view",(0,2),(50,491,900,110))):
        x,y,w,h=rect
        point=_projection(data["bounds"],axes,rect)
        parts.extend([f'<rect x="{x-18}" y="{y-24}" width="{w+36}" height="{h+48}" rx="8" fill="#182638" stroke="#33465c"/>',
                      f'<text x="{x}" y="{y-7}" font-size="14">{label}</text>'])
        # Batch independent line segments into one path per color and kind.
        groups={}
        marks={}
        for e in data["events"]:
            kind=e["kind"]
            if kind=="tool_setup":
                continue
            color=data["stages"][e["stage"]]["color"]
            a,b=point(e["a"]),point(e["b"])
            if axes==(0,1) and kind in ("plunge","retract"):
                if kind=="plunge":
                    marks[(round(b[0],2),round(b[1],2),color)]=True
                continue
            if a==b:
                continue
            groups.setdefault((kind,color),[]).append(f'M{a[0]:.2f},{a[1]:.2f}L{b[0]:.2f},{b[1]:.2f}')
        for (kind,color),segments in sorted(groups.items(),key=lambda item:item[0][0]!="rapid_xy"):
            stroke="#8092aa" if kind=="rapid_xy" else color
            dash=' stroke-dasharray="4 4" opacity=".65"' if kind=="rapid_xy" else ""
            parts.append(f'<path d="{" ".join(segments)}" stroke="{stroke}" stroke-width="1.5" fill="none"{dash}/>')
        for px,py,color in marks:
            parts.append(f'<circle cx="{px}" cy="{py}" r="2.8" stroke="{color}" stroke-width="1.2" fill="#182638"/>')
    parts.append('<text x="32" y="647" font-size="13" fill="#a8bacc">Dashed grey: rapid travel · Circles: plunge positions · Centerlines only, not swept tool area</text>')
    x=32
    for s in data["stages"]:
        label=escape(s["label"])
        parts.append(f'<circle cx="{x+5}" cy="670" r="5" fill="{s["color"]}"/><text x="{x+16}" y="675" font-size="13">{label}</text>')
        x+=180
    parts.append('</g></svg>')
    return "".join(parts)


# Static SVG remains visible if JavaScript is disabled. No external resources.
SCRIPT = """
const d=JSON.parse(document.getElementById('data').textContent);
const range=document.getElementById('step'), cv=document.getElementById('canvas');
const ctx=cv.getContext('2d'), label=document.getElementById('status');
const rapid=document.getElementById('rapid'), stage=document.getElementById('stage');
range.max=d.events.length; range.value=d.events.length;
for(let i=0;i<d.stages.length;i++){let o=document.createElement('option');o.value=i;o.textContent=d.stages[i].label+' / '+d.stages[i].tool;stage.append(o);}
function draw(){
 const n=Number(range.value), f=stage.value;
 ctx.fillStyle='#182638';ctx.fillRect(0,0,cv.width,cv.height);
 for(const [axes,r,title] of [[[0,1],[40,38,920,330],'XY | Top view'],[[0,2],[40,415,920,110],'XZ | Side view']]){
  const [x,y,w,h]=r,A=d.bounds[axes[0]],B=d.bounds[axes[1]],s=Math.min(w/Math.max(A[1]-A[0],1e-9),h/Math.max(B[1]-B[0],1e-9));
  const p=v=>[x+w/2+(v[axes[0]]-(A[0]+A[1])/2)*s,y+h/2-(v[axes[1]]-(B[0]+B[1])/2)*s];
  ctx.font='16px system-ui';ctx.fillStyle='#dbe7f2';ctx.fillText(title,x,y-10);
  for(let i=0;i<n;i++){
   const e=d.events[i];if(e.kind==='tool_setup'||(f!=='all'&&Number(f)!==e.stage)||(!rapid.checked&&e.kind==='rapid_xy'))continue;
   const a=p(e.a),b=p(e.b);ctx.strokeStyle=e.kind==='rapid_xy'?'#8092aa':d.stages[e.stage].color;
   ctx.lineWidth=1.5;ctx.setLineDash(e.kind==='rapid_xy'?[4,4]:[]);
   ctx.beginPath();
   if(axes[1]===1&&(e.kind==='plunge'||e.kind==='retract')){if(e.kind==='retract')continue;ctx.arc(b[0],b[1],3,0,Math.PI*2);}
   else {ctx.moveTo(...a);ctx.lineTo(...b);}
   ctx.stroke();
  }
  const current=n?d.events[n-1].b:d.initial, q=p(current);
  ctx.setLineDash([]);ctx.fillStyle='#ffffff';ctx.beginPath();ctx.arc(...q,4,0,Math.PI*2);ctx.fill();
 }
 const e=n?d.events[n-1]:null,v=e?e.b:d.initial;
 label.textContent=n+'/'+d.events.length+' | '+(e?d.stages[e.stage].label+' / '+e.kind:'Start')+' | X '+v[0].toFixed(3)+' Y '+v[1].toFixed(3)+' Z '+v[2].toFixed(3)+' mm';
}
for(const control of [range,rapid,stage])control.addEventListener('input',draw);
document.getElementById('prev').onclick=()=>{range.value=Math.max(0,Number(range.value)-1);draw();};
document.getElementById('next').onclick=()=>{range.value=Math.min(d.events.length,Number(range.value)+1);draw();};
document.getElementById('static').hidden=true;document.getElementById('interactive').hidden=false;draw();
"""


def render_html(data):
    payload=json.dumps(data,allow_nan=False,separators=(",",":")).replace("<","\\u003c")
    return ('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>Pictronics PCB Studio | Offline G-code viewer</title>'
            '<style>body{background:#101a27;color:#e5edf6;font:15px system-ui;margin:20px auto;max-width:1040px;padding:0 12px} '
            'canvas,svg{width:100%;height:auto}button,select{padding:8px;background:#26384c;color:white;border:1px solid #526981;border-radius:5px} '
            'input[type=range]{width:100%}.controls{display:flex;gap:12px;flex-wrap:wrap;align-items:center}small{color:#a8bacc}[hidden]{display:none!important}</style>'
            '<h1>Pictronics PCB Studio</h1><p>Offline G-code viewer — no machine connection</p>'
            '<div id="static">'+render_svg(data)+'</div><div id="interactive" hidden>'
            '<div class="controls"><button id="prev">Previous</button><button id="next">Next</button>'
            '<label>Stage <select id="stage"><option value="all">All stages</option></select></label>'
            '<label><input type="checkbox" id="rapid" checked> Rapid travel</label></div>'
            '<p id="status" aria-live="polite"></p><input id="step" type="range" min="0" step="1" aria-label="Motion event">'
            '<canvas id="canvas" width="1000" height="560"></canvas>'
            '<p>White dot: current tool-tip position. Dashed grey: rapid travel. Colored lines: centerlines, not cutter footprints.</p></div>'
            '<p><small>Nominal coordinates only. Not a collision check or a runnable program.</small></p>'
            '<script type="application/json" id="data">'+payload+'</script><script>'+SCRIPT+'</script></html>')
