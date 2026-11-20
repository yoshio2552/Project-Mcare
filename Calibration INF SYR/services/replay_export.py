"""ส่งออกการเล่นซ้ำเป็นไฟล์ HTML ไฟล์เดียว (ผู้ใช้ 2026-11-20 "Motion html แบบเหมือนรันเทสสด") — ไม่มี Qt

เปิดได้ทุกเบราว์เซอร์ ไม่ต้องต่อเน็ต (ไม่มีไลบรารีภายนอก — วาดด้วย canvas เอง) · เล่น/หยุด/ความเร็ว/เลื่อนตำแหน่ง
กราฟ 4 ช่องเหมือนหน้าทดสอบ + การ์ดตัวเลข + หัวกระดาษข้อมูลงาน · ธีมสว่าง/มืดตามเครื่อง · ข้อมูลเยอะคัดจุดให้ ≤ MAX_POINTS
ตัวเลขทุกตัวมาจาก ReplayData (services/replay_session.py) = ตรงกับผลที่บันทึก · ท้ายไฟล์มีเลขผล + SHA-256 ของข้อมูลดิบ
"""
from __future__ import annotations

import html
import json
import math

import numpy as np

from config.constants import APP_NAME, APP_VERSION

MAX_POINTS = 6000


def _decimate(idx: np.ndarray, limit: int = MAX_POINTS) -> np.ndarray:
    if len(idx) <= limit:
        return idx
    step = math.ceil(len(idx) / limit)
    return idx[::step]


def _r(value, places=4):
    return None if value is None or (isinstance(value, float) and not math.isfinite(value)) else round(float(value), places)


def payload(data) -> dict:
    """ข้อมูลที่ฝังในไฟล์ (JSON)"""
    results = data.results
    n = len(results)
    keep = _decimate(np.arange(n))
    series = {"t": [], "w": [], "q": [], "ca": [], "cb": [], "call": []}
    for i in keep:
        r = results[int(i)]
        series["t"].append(_r(r.t, 3))
        series["w"].append(_r(r.weight, 4))
        series["q"].append(_r(r.slope_flow, 4))
        c = r.cumulative
        series["ca"].append(_r(c.flow_a, 4) if c else None)
        series["cb"].append(_r(c.flow_b, 4) if c else None)
        series["call"].append(_r(c.flow_all, 4) if c else None)
    intervals, extrema, means = [], [], []
    for r in results:
        if r.interval is not None:
            iv = r.interval
            intervals.append({"t": _r(r.t, 3), "end": _r(iv.t, 3), "dur": _r(iv.duration_s, 3), "f": _r(iv.flow, 4),
                              "e": _r(iv.error_pct, 3), "c": iv.chain})
            if r.stats is not None:
                means.append([_r(r.t, 3), _r(iv.t, 3), _r(r.stats.mean_flow, 4), _r(r.stats.mean_error_pct, 3),
                              r.stats.count])
        if r.extremum is not None:
            extrema.append([_r(r.t, 3), _r(r.extremum.t, 3), _r(r.extremum.flow, 4), r.extremum.kind == "TOP"])
    return {"series": series, "intervals": intervals, "extrema": extrema, "means": means,
            "t0": _r(data.t_start, 3), "t1": _r(data.t_end, 3), "target": data.target, "tol": data.tolerance,
            "chains": data.chains}


def build_html(data, meta: dict, labels: dict, lang: str = "en") -> str:
    """meta: title, subtitle, verdict, rows [(ชื่อ, ค่า)], footer · labels: ข้อความบนจอ (แปลแล้ว)"""
    body = json.dumps({"data": payload(data), "meta": meta, "labels": labels}, ensure_ascii=False,
                      separators=(",", ":"))
    title = html.escape(meta.get("title", "DeltaM replay"))
    return _TEMPLATE.replace("__TITLE__", title).replace("__LANG__", html.escape(lang)) \
        .replace("__PAYLOAD__", body.replace("</", "<\\/")) \
        .replace("__APP__", html.escape(f"{APP_NAME} {APP_VERSION}"))


_TEMPLATE = r"""<!doctype html>
<html lang="__LANG__">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
:root{--bg:#F4F6F8;--surface:#FFFFFF;--alt:#EEF1F4;--border:#DDE2E8;--text:#18212B;--muted:#5D6B7A;--faint:#98A3B0;
--accent:#0E9F8E;--ok:#059669;--bad:#DC2626;--warn:#C2700A;--a:#0891B2;--b:#DB2777;--all:#059669;--mean:#CA8A04;
--slope:#2563EB;--weight:#7C3AED;--band:rgba(5,150,105,.10);--grid:rgba(24,33,43,.08)}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#0E1217;--surface:#161B22;--alt:#1D242D;
--border:#2A323D;--text:#E6EAF0;--muted:#8793A3;--faint:#5B6675;--accent:#2DD4BF;--ok:#34D399;--bad:#F87171;
--warn:#FBBF24;--a:#22D3EE;--b:#F472B6;--all:#34D399;--mean:#FACC15;--slope:#60A5FA;--weight:#A78BFA;
--band:rgba(52,211,153,.10);--grid:rgba(230,234,240,.08)}}
:root[data-theme=dark]{--bg:#0E1217;--surface:#161B22;--alt:#1D242D;--border:#2A323D;--text:#E6EAF0;--muted:#8793A3;
--faint:#5B6675;--accent:#2DD4BF;--ok:#34D399;--bad:#F87171;--warn:#FBBF24;--a:#22D3EE;--b:#F472B6;--all:#34D399;
--mean:#FACC15;--slope:#60A5FA;--weight:#A78BFA;--band:rgba(52,211,153,.10);--grid:rgba(230,234,240,.08)}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:14px/1.45 "Segoe UI","Leelawadee UI","Noto Sans Thai",system-ui,sans-serif}
.wrap{max-width:1500px;margin:0 auto;padding:18px 16px 28px}
header{display:flex;gap:16px;align-items:flex-start;justify-content:space-between;flex-wrap:wrap}
h1{font-size:22px;margin:0 0 2px;font-weight:700}
.sub{color:var(--muted)}
.verdict{font-size:22px;font-weight:800;padding:6px 16px;border-radius:999px;border:2px solid currentColor}
.meta{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:6px 18px;margin:14px 0;padding:12px 14px;
background:var(--surface);border:1px solid var(--border);border-radius:12px}
.meta div span{display:block;color:var(--muted);font-size:12px}
.tiles{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:10px;margin-bottom:10px}
.tile{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:10px 12px;min-width:0}
.tile span{display:block;font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);
white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tile b{font-size:24px;font-variant-numeric:tabular-nums}
.tile i{font-style:normal;color:var(--muted);margin-left:4px;font-size:12px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.card{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:8px 10px 6px}
.card h3{margin:0 0 4px;font-size:13px;display:flex;gap:12px;align-items:center;flex-wrap:wrap}
.lg{font-weight:400;color:var(--muted);font-size:12px}
.lg::before{content:"";display:inline-block;width:12px;height:3px;border-radius:2px;margin-right:5px;vertical-align:middle;background:var(--c)}
canvas{width:100%;height:260px;display:block}
.bar{display:flex;align-items:center;gap:10px;margin-top:10px;padding:10px 12px;background:var(--surface);
border:1px solid var(--border);border-radius:12px;position:sticky;bottom:8px}
button,select{font:inherit;color:var(--text);background:var(--alt);border:1px solid var(--border);border-radius:8px;
padding:7px 12px;cursor:pointer}
button.primary{background:var(--accent);border-color:var(--accent);color:#04201C;font-weight:700;min-width:96px}
input[type=range]{flex:1;accent-color:var(--accent)}
.pos{font-variant-numeric:tabular-nums;min-width:120px;text-align:right}
.seg button{border-radius:0;margin-left:-1px}.seg button:first-child{border-radius:8px 0 0 8px}
.seg button:last-child{border-radius:0 8px 8px 0}.seg button.on{background:var(--accent);color:#04201C;border-color:var(--accent)}
footer{margin-top:14px;color:var(--faint);font-size:12px;display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}
@media (max-width:900px){.grid{grid-template-columns:1fr}.tiles{grid-template-columns:repeat(3,minmax(0,1fr))}
canvas{height:220px}.bar{flex-wrap:wrap}}
</style>
</head>
<body>
<div class="wrap">
<header><div><h1 id="title"></h1><div class="sub" id="subtitle"></div></div><div class="verdict" id="verdict"></div></header>
<div class="meta" id="meta"></div>
<div class="tiles" id="tiles"></div>
<div class="grid">
 <div class="card"><h3 id="h0"></h3><canvas id="c0"></canvas></div>
 <div class="card"><h3 id="h1"></h3><canvas id="c1"></canvas></div>
 <div class="card"><h3 id="h2"></h3><canvas id="c2"></canvas></div>
 <div class="card"><h3 id="h3"></h3><canvas id="c3"></canvas></div>
</div>
<div class="bar">
 <button id="restart" title="⏮">⏮</button><button id="play" class="primary"></button>
 <select id="speed"></select><input id="seek" type="range" min="0" max="1000" value="1000">
 <span class="pos" id="pos"></span>
 <span class="seg" id="range"></span>
</div>
<footer><span id="foot"></span><span>__APP__</span></footer>
</div>
<script id="payload" type="application/json">__PAYLOAD__</script>
<script>
(function(){
"use strict";
var P=JSON.parse(document.getElementById("payload").textContent),D=P.data,M=P.meta,L=P.labels,S=D.series;
var css=function(n){return getComputedStyle(document.documentElement).getPropertyValue(n).trim();};
var $=function(id){return document.getElementById(id);};
function esc(s){return String(s==null?"":s).replace(/[&<>"]/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c];});}
$("title").textContent=M.title;$("subtitle").textContent=M.subtitle||"";
var vd=$("verdict");vd.textContent=M.verdict||"";vd.style.color=M.verdict==="PASS"?css("--ok"):M.verdict==="FAIL"?css("--bad"):css("--warn");
$("meta").innerHTML=(M.rows||[]).map(function(r){return "<div><span>"+esc(r[0])+"</span>"+esc(r[1])+"</div>";}).join("");
$("foot").textContent=M.footer||"";
var tiles=[["time",""],["flow","ml/h"],["mean","ml/h"],["error","%"],["count",""],["weight","g"]];
$("tiles").innerHTML=tiles.map(function(t){return '<div class="tile"><span>'+esc(L["tile_"+t[0]])+'</span><b id="v_'+t[0]+'">—</b><i>'+t[1]+"</i></div>";}).join("");
var titles=[[L.cumulative,[["--a",L.chain_a]].concat(D.chains>1?[["--b",L.chain_b],["--all",L.overall]]:[])],
 [L.intervals,[["--a",L.chain_a]].concat(D.chains>1?[["--b",L.chain_b]]:[]).concat([["--mean",L.moving]])],
 [L.slope,[["--slope",L.slope_line]].concat(D.extrema.length?[["--bad",L.peak]]:[])],[L.weight,[["--weight",L.weight_line]]]];
titles.forEach(function(t,i){$("h"+i).innerHTML=esc(t[0])+t[1].map(function(l){return '<span class="lg" style="--c:var('+l[0]+')">'+esc(l[1])+"</span>";}).join("");});
var speeds=[1,2,5,10,30,60,120],sp=$("speed");speeds.forEach(function(v){var o=document.createElement("option");o.value=v;o.textContent=v+"×";if(v===10)o.selected=true;sp.appendChild(o);});
var ranges=[["full",L.full],["auto",L.auto],["zoom",L.zoom]],mode="full",rg=$("range");
ranges.forEach(function(r){var b=document.createElement("button");b.textContent=r[1];b.onclick=function(){mode=r[0];mark();draw();};b.dataset.k=r[0];rg.appendChild(b);});
function mark(){Array.prototype.forEach.call(rg.children,function(b){b.className=b.dataset.k===mode?"on":"";});}
mark();
var t0=D.t0,t1=D.t1,T=t1,playing=false,last=0,target=D.target,tol=D.tol;
function idx(arr,t){var lo=0,hi=arr.length;while(lo<hi){var m=(lo+hi)>>1;if(arr[m]<=t)lo=m+1;else hi=m;}return lo;}
var ts=S.t,ivT=D.intervals.map(function(i){return i.t;}),mT=D.means.map(function(m){return m[0];}),eT=D.extrema.map(function(e){return e[0];});
function clock(s){var g=s<0?"−":"";s=Math.abs(s);var h=Math.floor(s/3600),m=Math.floor(s%3600/60),x=Math.floor(s%60);
 return g+(h?h+":"+String(m).padStart(2,"0"):String(m).padStart(2,"0"))+":"+String(x).padStart(2,"0");}
function fmt(v,p){return v==null?"—":Number(v).toFixed(p);}
function view(){if(mode==="full")return [Math.min(0,t0),Math.max(t1,10)];var w=mode==="zoom"?60:Math.max(60,6*(D.intervals.length?(D.intervals[0].dur||60):60));
 return [Math.max(t0,T-w),Math.max(T,t0+w)];}
function setup(c){var r=c.getBoundingClientRect(),d=window.devicePixelRatio||1;c.width=Math.round(r.width*d);c.height=Math.round(r.height*d);
 var g=c.getContext("2d");g.setTransform(d,0,0,d,0,0);return {g:g,w:r.width,h:r.height};}
function axes(o,x0,x1,y0,y1,yl){var g=o.g,L0=54,R=10,T0=8,B=26,pw=o.w-L0-R,ph=o.h-T0-B;
 g.clearRect(0,0,o.w,o.h);g.font="11px Segoe UI, sans-serif";g.fillStyle=css("--muted");g.strokeStyle=css("--grid");g.lineWidth=1;
 var sx=function(x){return L0+(x-x0)/(x1-x0||1)*pw;},sy=function(y){return T0+(y1-y)/(y1-y0||1)*ph;};
 var ny=5;for(var i=0;i<=ny;i++){var yv=y0+(y1-y0)*i/ny,yy=sy(yv);g.beginPath();g.moveTo(L0,yy);g.lineTo(L0+pw,yy);g.stroke();
  g.textAlign="right";g.fillText(Number(yv).toFixed(Math.abs(y1-y0)<0.1?3:Math.abs(y1-y0)<5?2:1),L0-6,yy+4);}
 var step=nice((x1-x0)/6);for(var x=Math.ceil(x0/step)*step;x<=x1;x+=step){var xx=sx(x);g.beginPath();g.moveTo(xx,T0);g.lineTo(xx,T0+ph);g.stroke();
  g.textAlign="center";g.fillText(Math.round(x),xx,T0+ph+16);}
 g.strokeStyle=css("--border");g.strokeRect(L0,T0,pw,ph);return {sx:sx,sy:sy,L:L0,T:T0,pw:pw,ph:ph};}
function nice(v){var p=Math.pow(10,Math.floor(Math.log10(v||1))),f=v/p;return (f<1.5?1:f<3.5?2:f<7.5?5:10)*p;}
function band(o,a){if(!target)return;var g=o.g,lo=target*(1-tol/100),hi=target*(1+tol/100);g.fillStyle=css("--band");
 var y0=a.sy(hi),y1=a.sy(lo);g.fillRect(a.L,Math.max(a.T,y0),a.pw,Math.min(a.T+a.ph,y1)-Math.max(a.T,y0));
 g.setLineDash([4,4]);g.strokeStyle=css("--faint");g.beginPath();g.moveTo(a.L,a.sy(target));g.lineTo(a.L+a.pw,a.sy(target));g.stroke();g.setLineDash([]);}
function line(o,a,xs,ys,color,width,from,to,stepped){var g=o.g;g.save();g.beginPath();g.rect(a.L,a.T,a.pw,a.ph);g.clip();
 g.strokeStyle=color;g.lineWidth=width;g.beginPath();var pen=false;
 for(var i=from;i<to;i++){var y=ys[i];if(y==null){pen=false;continue;}var X=a.sx(xs[i]),Y=a.sy(y);if(!pen){g.moveTo(X,Y);pen=true;}else g.lineTo(X,Y);}
 g.stroke();g.restore();}
function flowRange(){if(!target)return [0,1];var s=0.2;return [target*(1-s),target*(1+s)];}
function draw(){var v=view(),x0=v[0],x1=v[1],n=idx(ts,T);
 // 0 cumulative
 var o=setup($("c0")),r=flowRange(),a=axes(o,x0,x1,r[0],r[1]);band(o,a);
 line(o,a,ts,S.ca,css("--a"),1.6,0,n);if(D.chains>1){line(o,a,ts,S.cb,css("--b"),1.6,0,n);line(o,a,ts,S.call,css("--all"),2.4,0,n);}
 // 1 intervals (steps) + moving mean
 o=setup($("c1"));a=axes(o,x0,x1,r[0],r[1]);band(o,a);var k=idx(ivT,T),g=o.g;g.save();g.beginPath();g.rect(a.L,a.T,a.pw,a.ph);g.clip();
 for(var c=0;c<D.chains;c++){g.strokeStyle=css(c?"--b":"--a");g.lineWidth=2;g.beginPath();
  for(var i=0;i<k;i++){var iv=D.intervals[i];if(iv.c!==c)continue;var ys=a.sy(Math.max(r[0],Math.min(r[1],iv.f)));
   g.moveTo(a.sx(iv.end-iv.dur),ys);g.lineTo(a.sx(iv.end),ys);}g.stroke();}
 var mk=idx(mT,T);g.strokeStyle=css("--mean");g.lineWidth=2.2;g.beginPath();for(var j=0;j<mk;j++){var m=D.means[j],X=a.sx(m[1]),Y=a.sy(m[2]);j?g.lineTo(X,Y):g.moveTo(X,Y);}g.stroke();g.restore();
 // 2 slope + extrema
 o=setup($("c2"));var lo=Infinity,hi=-Infinity;for(var q=0;q<n;q++){var val=S.q[q];if(val==null||S.t[q]<x0)continue;if(val<lo)lo=val;if(val>hi)hi=val;}
 if(!isFinite(lo)){lo=r[0];hi=r[1];}var pad=Math.max((hi-lo)*0.08,target*0.02||0.01);a=axes(o,x0,x1,lo-pad,hi+pad);band(o,a);
 line(o,a,ts,S.q,css("--slope"),1.6,0,n);var ek=idx(eT,T);g=o.g;g.save();g.beginPath();g.rect(a.L,a.T,a.pw,a.ph);g.clip();
 for(var e=0;e<ek;e++){var ex=D.extrema[e];g.fillStyle=css(ex[3]?"--bad":"--ok");var px=a.sx(ex[1]),py=a.sy(ex[2]);g.beginPath();
  if(ex[3]){g.moveTo(px-5,py-6);g.lineTo(px+5,py-6);g.lineTo(px,py+2);}else{g.moveTo(px-5,py+6);g.lineTo(px+5,py+6);g.lineTo(px,py-2);}g.fill();}g.restore();
 // 3 weight
 o=setup($("c3"));lo=Infinity;hi=-Infinity;for(var wq=0;wq<n;wq++){if(S.t[wq]<x0)continue;var wv=S.w[wq];if(wv<lo)lo=wv;if(wv>hi)hi=wv;}
 if(!isFinite(lo)){lo=0;hi=1;}pad=Math.max((hi-lo)*0.08,0.003);a=axes(o,x0,x1,lo-pad,hi+pad);line(o,a,ts,S.w,css("--weight"),1.8,0,n);
 // tiles
 var last=n?n-1:0,flow=null;for(var b=last;b>=0&&b>last-400;b--){if(S.q[b]!=null){flow=S.q[b];break;}}
 var mm=mk?D.means[mk-1]:null;$("v_time").textContent=clock(T);$("v_flow").textContent=fmt(flow,3);
 $("v_mean").textContent=mm?fmt(mm[2],3):"—";var ve=$("v_error");ve.textContent=mm?(mm[3]>=0?"+":"")+fmt(mm[3],2):"—";
 ve.style.color=mm?(Math.abs(mm[3])<=tol?css("--ok"):css("--bad")):"";$("v_count").textContent=mm?mm[4]:0;
 $("v_weight").textContent=n?fmt(S.w[last],3):"—";$("pos").textContent=clock(T)+" / "+clock(t1);
 $("seek").value=Math.round((T-t0)/((t1-t0)||1)*1000);$("play").textContent=playing?"❚❚ "+L.pause:"▶ "+L.play;}
function frame(now){if(!playing)return;var dt=(now-last)/1000;last=now;T=Math.min(t1,T+dt*Number(sp.value));if(T>=t1)playing=false;draw();if(playing)requestAnimationFrame(frame);}
$("play").onclick=function(){if(playing){playing=false;draw();return;}if(T>=t1){T=t0;if(mode==="full"){mode="auto";mark();}}playing=true;last=performance.now();requestAnimationFrame(frame);};
$("restart").onclick=function(){T=t0;draw();};
$("seek").oninput=function(){T=t0+(t1-t0)*this.value/1000;draw();};
window.addEventListener("resize",draw);
document.addEventListener("keydown",function(ev){if(ev.code==="Space"&&ev.target.tagName!=="SELECT"){ev.preventDefault();$("play").click();}});
draw();
})();
</script>
</body>
</html>
"""
