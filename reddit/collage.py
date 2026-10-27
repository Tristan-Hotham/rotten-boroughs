"""Reddit collage (2400 x 3000 px): rotten boroughs as a Georgian broadside.
Usage: python3 reddit/collage.py [font_dir]    (run from anywhere; reads ../data)
Every number comes from data/results.json and data/boroughs.csv.
"""
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager as fm

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
F = sys.argv[1] if len(sys.argv) > 1 else "/tmp/claude-0/-home-claude/c232619d-81e0-53f3-9de6-41e973630753/scratchpad/fonts"
for f in ["FrauncesVar.ttf", "IBMPlexMono-Regular.ttf", "IBMPlexMono-Medium.ttf", "SourceSerif4-Regular.ttf", "SourceSerif4-Semibold.ttf", "SourceSerif4-It.ttf"]:
    fm.fontManager.addfont(os.path.join(F, f))
DISP = fm.FontProperties(fname=os.path.join(F, "FrauncesVar.ttf"), weight=900)
SER, MONO = "Source Serif 4", "IBM Plex Mono"
BG, FG, MUT, RULE, LAND = "#F4EDDC", "#211B16", "#6A5E4E", "#CDBB94", "#E6DAC0"
HOT, OTH = "#8E1B2E", "#1F3A5F"
CLS = [("Town", "#3A3029"), ("Village", "#B4802A"), ("Hamlet", "#6E8A4B"), ("Part of a larger town", "#6D82A0"), ("Deserted site", "#8E1B2E")]

R = json.load(open(os.path.join(ROOT, "data", "results.json")))
d = pd.read_csv(os.path.join(ROOT, "data", "boroughs.csv"))
A, NEW = d[d.schedule == "A"], d[d.schedule.isin(["C", "D"])]
K = np.cos(np.radians(52.8))

fig = plt.figure(figsize=(12, 15), dpi=200, facecolor=BG)
# broadside frame: double rule
fr = fig.add_axes([0, 0, 1, 1]); fr.axis("off"); fr.set_xlim(0, 1); fr.set_ylim(0, 1)
for m, lw in [(0.018, 2.4), (0.025, 0.8)]:
    fr.add_patch(plt.Rectangle((m, m * 0.8), 1 - 2 * m, 1 - 1.6 * m, fill=False, ec=FG, lw=lw))

fig.text(0.05, 0.955, "THE REFORM ACT OF 1832  ·  EVERY BOROUGH IT ABOLISHED OR CREATED  ·  WHERE ARE THEY NOW?", family=MONO, fontsize=10.5, color=HOT, va="top")
fig.text(0.05, 0.937, "Two MPs for seven voters", fontproperties=DISP, fontsize=50, color=FG, va="top")
fig.text(0.05, 0.874, f"Before 1832 Gatton in Surrey had {R['gatton_voters']} voters and two MPs, and Manchester had none. "
                      f"The Reform Act\nabolished {R['n_A']} rotten boroughs and gave seats to {R['n_new']} towns. Two centuries on, most of the old boroughs are\nquiet villages and small towns of the south.",
         family=SER, fontsize=14.5, color=FG, va="top", linespacing=1.38)

# hero map
coast = []
for f in json.load(open("/home/claude/hist/_data3/ne/geojson/ne_10m_coastline.geojson"))["features"]:
    g = f["geometry"]
    for ln in (g["coordinates"] if g["type"] == "MultiLineString" else [g["coordinates"]]):
        a = np.array(ln)
        if ((a[:, 0] > -6.5) & (a[:, 0] < 2) & (a[:, 1] > 49.8) & (a[:, 1] < 55.9)).any():
            coast.append(a)
ax = fig.add_axes([0.035, 0.295, 0.56, 0.5])
for a in coast:
    ax.fill(a[:, 0] * K, a[:, 1], color=LAND, lw=0) if (np.hypot(*(a[0] - a[-1])) < 1e-6 and len(a) > 50) else None
    ax.plot(a[:, 0] * K, a[:, 1], color="#B9A782", lw=0.6)
sz = np.clip(np.sqrt(NEW.pop_today.fillna(30000)) / 2.0, 25, 520)
ax.scatter(NEW.lon * K, NEW.lat, s=sz, color=OTH, alpha=0.78, lw=0.8, edgecolor=BG, zorder=3)
ax.scatter(A.lon * K, A.lat, s=46, color=HOT, edgecolor=BG, lw=0.8, zorder=4)
for nm, dx, dy, ha in [("Old Sarum", -10, -2, "right"), ("Gatton", 10, -10, "left"), ("Dunwich", -10, 6, "right"), ("Mitchell", -6, 14, "right"),
                       ("Manchester", 16, -10, "left"), ("Birmingham", 16, 0, "left"), ("Leeds", 14, 8, "left")]:
    r = d[d.name == nm].iloc[0]
    ax.annotate(nm, (r.lon * K, r.lat), xytext=(dx, dy), textcoords="offset points", family=SER, fontsize=11.5, color=FG, ha=ha, va="center",
                arrowprops=dict(arrowstyle="-", color=FG, lw=0.6, shrinkA=0, shrinkB=3))
ax.set_xlim(-5.85 * K, 1.85 * K); ax.set_ylim(49.9, 55.9); ax.set_aspect(1); ax.axis("off")
ax.scatter([], [], s=46, color=HOT, label=f"Abolished in 1832 (Schedule A): {R['n_A']}")
ax.scatter([], [], s=120, color=OTH, alpha=0.8, label=f"New borough in 1832: {R['n_new']} (sized by people today)")
lg = ax.legend(loc="upper left", bbox_to_anchor=(0.0, 1.0), frameon=False, prop={"family": MONO, "size": 10}, labelcolor=FG, handletextpad=0.3)

# right column: big numbers
tx = fig.add_axes([0.62, 0.30, 0.35, 0.5]); tx.axis("off")
notes = [(f"{R['gatton_voters']} voters", f"at Gatton in 1831, for two MPs. Mitchell and\nSt Germans also had {R['mitchell_voters']}. The median abolished\nborough had {R['A_voters_median']:.0f} ({R['n_A_voters_known']} with a known electorate)."),
         (f"{R['manchester_pop1801']:,}", f"people in Manchester in 1801, with no MP of\nits own. {R['n_top30_1801_new_1832']} of England's 30 largest towns\nhad to wait until 1832."),
         (f"{R['n_A_village_or_smaller']} of {R['n_A']}", f"abolished boroughs are villages, a hamlet or\nan empty hill today. {R['n_A_cornwall']} of the {R['n_A']} were in\nCornwall, whose MPs fell from {R['cornwall_mps_1821']} to {R['cornwall_mps_1832']}."),
         (f"{abs(R['A_income_vs_ring_median']):.1f}%", f"median household income gap between the old\nboroughs and the area 5 to 25 km around them.\nThe new towns of 1832: {R['new_income_vs_ring_median']:+.1f}%.".replace("-", "−"))]
for (big, small), y in zip(notes, [1.0, 0.75, 0.5, 0.25]):
    tx.text(0, y, big, fontproperties=DISP, fontsize=30, color=HOT, va="top", transform=tx.transAxes)
    tx.text(0, y - 0.085, small, family=SER, fontsize=12, color=FG, va="top", transform=tx.transAxes, linespacing=1.3)

# bottom row: three panels
fig.add_artist(plt.Line2D([0.05, 0.95], [0.268, 0.268], color=FG, lw=0.8))
# (1) contrast
b1 = fig.add_axes([0.05, 0.093, 0.28, 0.152]); b1.axis("off")
fig.text(0.05, 0.257, "VOTERS 1831  vs  PEOPLE 1801, NO MP", family=MONO, fontsize=10, color=MUT, va="top")
L, T = R["smallest_electorates"][:5], R["top1801_new"][:5]
S = lambda v: np.log10(v) / 5 * 0.42
for i, (a, b) in enumerate(zip(L, T)):
    y = -i
    b1.barh(y, -S(a["voters"]), left=-0.01, color=HOT, height=0.6)
    b1.text(-0.03 - S(a["voters"]), y, f"{a['name']} {a['voters']}", ha="right", va="center", family=SER, fontsize=10, color=FG)
    b1.barh(y, S(b["pop1801"]), left=0.01, color=OTH, height=0.6)
    b1.text(0.03 + S(b["pop1801"]), y, f"{b['name']}\n{b['pop1801']:,}", ha="left", va="center", family=SER, fontsize=9.5, color=FG, linespacing=1.0)
b1.plot([0, 0], [-4.5, 0.5], color=FG, lw=0.8)
b1.set_xlim(-0.75, 0.85); b1.set_ylim(-4.6, 0.6)
fig.text(0.05, 0.08, "log scale, same both sides", family=MONO, fontsize=9, color=MUT)
# (2) waffle
fig.text(0.37, 0.257, f"THE {R['n_A']} ABOLISHED BOROUGHS TODAY", family=MONO, fontsize=10, color=MUT, va="top")
b2 = fig.add_axes([0.37, 0.1, 0.27, 0.14]); b2.axis("off")
order = [c for c, _ in CLS]; col = dict(CLS)
aa = A.assign(o=A.today_class.map(order.index)).sort_values(["o", "name"])
for i, (_, r) in enumerate(aa.iterrows()):
    b2.add_patch(plt.Rectangle((i % 8, -(i // 8)), 0.86, 0.86, color=col[r.today_class]))
for j, (c, cc) in enumerate(CLS):
    n = int((A.today_class == c).sum())
    b2.add_patch(plt.Rectangle((8.6, -j * 1.35 + 0.15), 0.6, 0.6, color=cc))
    b2.text(9.45, -j * 1.35 + 0.45, f"{c.replace('Part of a larger town', 'Part of a town')} {n}", va="center", family=SER, fontsize=10, color=FG)
b2.set_xlim(0, 15.5); b2.set_ylim(-6.2, 1); b2.set_aspect(1)
# (3) growth: shrank vs grew
fig.text(0.69, 0.257, "PEOPLE, 1831 TO TODAY", family=MONO, fontsize=10, color=MUT, va="top")
b3 = fig.add_axes([0.69, 0.103, 0.26, 0.142]); b3.axis("off")
rows = [(x["name"], x["pop1831"], x["pop_today"]) for x in R["A_top_growth"][:3]] + [(x["name"], x["pop1831"], x["pop_today"]) for x in R["A_shrank"][:3]]
for i, (nm, p0, p1) in enumerate(rows):
    y = -i
    c = HOT if p1 < p0 else "#3A3029"
    lx = lambda v: (np.log10(v) - 2) / 2.6
    b3.plot([lx(p0), lx(p1)], [y, y], color=c, lw=2.2)
    b3.scatter([lx(p0)], [y], s=26, color=BG, edgecolor=c, lw=1.4, zorder=3)
    b3.scatter([lx(p1)], [y], s=30, color=c, zorder=3)
    b3.text(-0.05, y, nm, ha="right", va="center", family=SER, fontsize=10, color=FG)
    b3.text(max(lx(p0), lx(p1)) + 0.04, y, f"{p0:,} to {p1:,}", va="center", family=MONO, fontsize=8.5, color=MUT)
b3.set_xlim(-0.55, 1.5); b3.set_ylim(-5.6, 0.6)
fig.text(0.69, 0.078, f"open: 1831, filled: today. Median growth\n{R['A_growth_median']:.1f}x ({R['n_A_growth']} boroughs); {R['n_A_shrank']} shrank", family=MONO, fontsize=9, color=MUT)

fig.text(0.05, 0.066, "Data: Wikipedia (Reform Act 1832 schedules, rotten borough constituency articles, historical town populations; CC BY-SA 4.0); Wikidata (CC0); ONS Census 2021\n"
                      "and income estimates FYE2023 (OGL v3); OS Open Names (contains OS data © Crown copyright and database right 2026); coastline Natural Earth.\n"
                      "Voters are estimates. Today: Census 2021 built-up area, or civil parish for small places. Analysis and chart: Tristan Hotham, with Python and matplotlib.",
         family=MONO, fontsize=7.9, color=MUT, va="top", linespacing=1.45)
fig.savefig(os.path.join(HERE, "two_mps_for_seven_voters.png"), facecolor=BG, dpi=200)
print("collage written")
