"""Step 4. Make header.png (1200x630 social card) by rendering a small HTML card with Playwright.

Usage:
    python3 code/04_header.py [font_dir]

Fonts come from Google Fonts. Where Google Fonts is unreachable, pass a folder holding
FrauncesVar.ttf, IBMPlexMono-Regular.ttf, IBMPlexMono-Medium.ttf and SourceSerif4-Regular.ttf.
Coastline: Natural Earth 1:10m (public domain), read in place.
"""
import asyncio
import csv
import json
import os
import sys

from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = json.load(open(os.path.join(ROOT, "data", "results.json")))
FONTS = sys.argv[1] if len(sys.argv) > 1 else None
pts = [[round(float(r["lon"]), 3), round(float(r["lat"]), 3), r["schedule"]] for r in csv.DictReader(open(os.path.join(ROOT, "data", "boroughs.csv")))]
coast = []
for f in json.load(open("/home/claude/hist/_data3/ne/geojson/ne_10m_coastline.geojson"))["features"]:
    g = f["geometry"]
    for ln in (g["coordinates"] if g["type"] == "MultiLineString" else [g["coordinates"]]):
        if any(-6.5 < x < 2 and 49.8 < y < 55.9 for x, y in ln):
            coast.append([[round(x, 3), round(y, 3)] for x, y in ln[::2]])
dek = (f"Gatton had {R['gatton_voters']} voters and two MPs; Manchester had {R['manchester_pop1801']:,} people in 1801 and none. "
       f"Today {R['n_A_village_or_smaller']} of the {R['n_A']} abolished boroughs are villages, a hamlet or an empty hill.")

HTML = """<!doctype html><html><head><meta charset="utf-8">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,900&family=IBM+Plex+Mono:wght@400;500&family=Source+Serif+4:opsz,wght@8..60,400&display=swap">
<style>
body{margin:0;width:1200px;height:630px;background:#F4EDDC;color:#211B16;overflow:hidden;position:relative;font-family:'Source Serif 4',Georgia,serif}
.l{position:absolute;left:68px;top:58px;width:640px}
.k{font:500 17px/1 'IBM Plex Mono',monospace;letter-spacing:.14em;text-transform:uppercase;color:#6A5E4E;display:flex;gap:14px;align-items:center}
.k b{background:#8E1B2E;color:#fff;padding:8px 10px;font-weight:500}
h1{font:900 112px/.86 'Fraunces',Georgia,serif;letter-spacing:-.02em;margin:24px 0 0}
h1 em{font-style:normal;color:#8E1B2E}
h2{font:900 38px/1 'Fraunces',Georgia,serif;color:#6A5E4E;margin:14px 0 0}
p{font-size:25px;line-height:1.34;margin:22px 0 0;color:#2E2620;max-width:620px}
.f{position:absolute;left:68px;bottom:34px;font:400 15px/1 'IBM Plex Mono',monospace;letter-spacing:.12em;text-transform:uppercase;color:#6A5E4E}
.g{position:absolute;right:34px;bottom:30px;font:400 14px/1.5 'IBM Plex Mono',monospace;color:#6A5E4E;text-align:right}
.g i{display:inline-block;width:12px;height:12px;border-radius:50%;margin:0 6px 0 14px;vertical-align:-1px}
canvas{position:absolute;right:16px;top:8px}
</style></head><body>
<div class="l"><div class="k"><b>Data study</b><span>History × data</span></div>
<h1>Rotten<br><em>boroughs</em></h1><h2>Where are they now?</h2>
<p>__DEK__</p></div>
<div class="f">Dr Tristan Hotham · Independent researcher</div>
<div class="g"><i style="background:#8E1B2E"></i>abolished 1832<i style="background:#1F3A5F"></i>new in 1832</div>
<canvas id="c" width="900" height="1180" style="width:450px;height:590px"></canvas>
<script>
const P = __PTS__, C = __COAST__;
const cv = document.getElementById("c"), x = cv.getContext("2d"); x.scale(2, 2);
const k = Math.cos(52.8 * Math.PI / 180), lo0 = -5.9, lo1 = 1.9, la0 = 49.9, la1 = 55.2;
const sc = Math.min(450 / ((lo1 - lo0) * k), 590 / (la1 - la0));
const X = l => (l - lo0) * k * sc, Y = l => (la1 - l) * sc;
x.strokeStyle = "#B9A782"; x.lineWidth = 1.1;
C.forEach(ln => { x.beginPath(); ln.forEach((p, i) => i ? x.lineTo(X(p[0]), Y(p[1])) : x.moveTo(X(p[0]), Y(p[1]))); x.stroke(); });
P.filter(p => p[2] === "C" || p[2] === "D").forEach(([lo, la]) => { x.beginPath(); x.arc(X(lo), Y(la), 6, 0, 7); x.fillStyle = "rgba(31,58,95,.85)"; x.fill(); });
P.filter(p => p[2] === "A").forEach(([lo, la]) => { x.beginPath(); x.arc(X(lo), Y(la), 6, 0, 7); x.fillStyle = "#8E1B2E"; x.fill(); x.lineWidth = 1.4; x.strokeStyle = "#F4EDDC"; x.stroke(); });
</script></body></html>"""
html = HTML.replace("__DEK__", dek).replace("__PTS__", json.dumps(pts)).replace("__COAST__", json.dumps(coast, separators=(",", ":")))
if FONTS:
    css = "".join(f"@font-face{{font-family:'{fam}';src:url(file://{FONTS}/{f});font-weight:{w}}}" for fam, f, w in
                  [("Fraunces", "FrauncesVar.ttf", "100 900"), ("IBM Plex Mono", "IBMPlexMono-Regular.ttf", "400"),
                   ("IBM Plex Mono", "IBMPlexMono-Medium.ttf", "500"), ("Source Serif 4", "SourceSerif4-Regular.ttf", "400")])
    html = html.replace(html[html.find('<link rel="stylesheet"'):html.find("<style>")], f"<style>{css}</style>")


async def main():
    tmp = os.path.join(ROOT, "_header.html")
    open(tmp, "w", encoding="utf-8").write(html)
    async with async_playwright() as p:
        b = await p.chromium.launch(args=["--allow-file-access-from-files"])
        pg = await b.new_page(viewport={"width": 1200, "height": 630})
        await pg.goto("file://" + tmp)
        await pg.wait_for_timeout(1500)
        await pg.screenshot(path=os.path.join(ROOT, "header.png"))
        await b.close()
    os.remove(tmp)


asyncio.run(main())
print("header.png written")
