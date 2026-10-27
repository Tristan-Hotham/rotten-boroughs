"""Step 2. Every number used on the page, in the paper, the blog post and the collage -> data/results.json.

Reads data/boroughs.csv (from step 1) and, for Cornwall's seats, the on-disk Wikipedia article
"Parliamentary representation from Cornwall" (CC BY-SA 4.0).
Also writes data/boroughs.geojson (points, for reuse and for the page).
"""
import gzip
import json
import math
import os
import re
from collections import Counter

import numpy as np
import pandas as pd
from scipy import stats

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H = "/home/claude/hist"
d = pd.read_csv(os.path.join(ROOT, "data", "boroughs.csv"))
R = {}

A = d[d.schedule == "A"].copy()
Bs = d[d.schedule == "B"].copy()
NEW = d[d.schedule.isin(["C", "D"])].copy()

# ---------- the Act's arithmetic (must match the schedules)
R["n_A"], R["n_B"], R["n_C"], R["n_D"] = len(A), len(Bs), int((d.schedule == "C").sum()), int((d.schedule == "D").sum())
R["seats_A"] = int(A.seats_before.sum())
R["seats_B_lost"] = int((Bs.seats_before - Bs.seats_after).sum())
R["seats_weymouth_lost"] = 2
R["seats_removed"] = R["seats_A"] + R["seats_B_lost"] + R["seats_weymouth_lost"]
R["seats_C"] = int(d[d.schedule == "C"].seats_after.sum())
R["seats_D"] = int(d[d.schedule == "D"].seats_after.sum())
R["seats_new_boroughs"] = R["seats_C"] + R["seats_D"]
R["n_new"] = R["n_C"] + R["n_D"]
R["n_new_wales"] = int((NEW.country == "Wales").sum())
assert R["seats_removed"] == 143, R["seats_removed"]  # Reform Act 1832 article: 143 borough seats abolished in England
assert R["seats_new_boroughs"] == 65  # 65 new borough seats in England and Wales

# ---------- Cornwall
R["n_A_cornwall"] = int((A.county_historic == "Cornwall").sum())
R["n_B_cornwall"] = int((Bs.county_historic == "Cornwall").sum())
R["seats_lost_cornwall"] = 2 * R["n_A_cornwall"] + R["n_B_cornwall"]
R["pct_A_cornwall"] = round(100 * R["n_A_cornwall"] / R["n_A"], 1)
art = json.load(gzip.open(f"{H}/_data10/wikipedia_batch10.json.gz", "rt", encoding="utf-8"))["articles"]
ct = art["Parliamentary representation from Cornwall"]["text"]
mp = ct[ct.find("Summary of members of parliament by type and period"):]
hdr = re.search(r"!Type!!(.*)", mp).group(1).split("!!")
tot = re.search(r"\|'''Total'''\s*\|\|(.*)", mp).group(1).split("||")
cw = {h.strip(): int(v.strip()) for h, v in zip(hdr, tot) if v.strip().isdigit()}
R["cornwall_mps_1821"], R["cornwall_mps_1832"] = cw["1821"], cw["1832"]
cs = ct[ct.find("Summary of constituencies by type and period"):]
hdr2 = re.search(r"!Type!!(.*)", cs).group(1).split("!!")
bor = re.search(r"\|Borough\s*\|\|(.*)", cs).group(1).split("||")
cb = {h.strip(): int(v.strip()) for h, v in zip(hdr2, bor) if v.strip().isdigit()}
R["cornwall_boroughs_1529"], R["cornwall_boroughs_1584"] = cb["1529"], cb["1584"]
A_by_county = Counter(A.county_historic)
R["A_by_county"] = dict(A_by_county.most_common())
R["n_A_wiltshire"] = A_by_county["Wiltshire"]

# ---------- geography: south and west versus north and midlands (today's regions)
south = {"South West", "South East", "London", "Eastern"}
R["n_A_south"] = int(A.region.isin(south).sum())
R["n_new_north_mid_wales"] = int(NEW.region.isin({"North West", "North East", "Yorkshire and the Humber", "West Midlands", "East Midlands", "Wales"}).sum())
R["median_lat_A"] = round(float(A.lat.median()), 2)
R["median_lat_new"] = round(float(NEW.lat.median()), 2)
R["lat_gap_km"] = round((R["median_lat_new"] - R["median_lat_A"]) * 110.57)
R["n_A_sw_region"] = int((A.region == "South West").sum())

# ---------- 1831: voters and people
v = A[A.voters1831.notna()].copy()
v["voters_per_mp"] = v.voters1831 / v.seats_before
R["n_A_voters_known"] = len(v)
R["A_voters_known_total"] = int(v.voters1831.sum())
R["A_voters_known_seats"] = int(v.seats_before.sum())
R["A_voters_median"] = float(v.voters1831.median())
R["A_voters_per_mp_median"] = float(v.voters_per_mp.median())
R["n_A_under_50_voters"] = int((v.voters1831 < 50).sum())
R["n_A_under_20_voters"] = int((v.voters1831 < 20).sum())
small = v.sort_values("voters1831").head(8)
R["smallest_electorates"] = [{"name": r["name"], "voters": int(r.voters1831), "seats": int(r.seats_before)} for _, r in small.iterrows()]
R["seats_of_smallest_ten"] = int(v.sort_values("voters1831").head(10).seats_before.sum())
R["voters_of_smallest_ten"] = int(v.sort_values("voters1831").head(10).voters1831.sum())
for nm, key in [("Old Sarum", "oldsarum"), ("Gatton", "gatton"), ("Dunwich", "dunwich"), ("Mitchell", "mitchell"), ("St Germans", "stgermans"),
                ("Newtown (Isle of Wight)", "newtown"), ("Bossiney", "bossiney"), ("Camelford", "camelford"), ("Fowey", "fowey")]:
    r = d[d.name == nm].iloc[0]
    R[f"{key}_voters"] = None if pd.isna(r.voters1831) else int(r.voters1831)
    R[f"{key}_pop1831"] = None if pd.isna(r.pop1831) else int(r.pop1831)
    R[f"{key}_houses1831"] = None if pd.isna(r.houses1831) else int(r.houses1831)
    R[f"{key}_pop_today"] = None if pd.isna(r.pop_today) else int(r.pop_today)
p = A[A.pop1831.notna()]
R["n_A_pop1831_known"] = len(p)
R["A_pop1831_median"] = float(p.pop1831.median())
R["A_pop1831_total"] = int(p.pop1831.sum())
R["A_pop1831_total_seats"] = int(p.seats_before.sum())
R["n_A_pop1831_under_1000"] = int((p.pop1831 < 1000).sum())

# 1801: the largest towns without MPs of their own
t1801 = json.load(open(os.path.join(ROOT, "data", "_t1801.json")))
R["n_top1801_table"] = len(t1801)
nt = NEW[NEW.pop1801_top_table.notna()].sort_values("pop1801_top_table", ascending=False)
R["n_top30_1801_new_1832"] = len(nt)
R["top1801_new"] = [{"name": r["name"], "pop1801": int(r.pop1801_top_table), "rank": int(r.rank1801)} for _, r in nt.iterrows()]
R["top1801_new_pop_total"] = int(nt.pop1801_top_table.sum())
R["manchester_pop1801"] = int(d[d.name == "Manchester"].pop1801_top_table.iloc[0])
R["birmingham_pop1801"] = int(d[d.name == "Birmingham"].pop1801_top_table.iloc[0])
R["leeds_pop1801"] = int(d[d.name == "Leeds"].pop1801_top_table.iloc[0])
R["sheffield_pop1801"] = int(d[d.name == "Sheffield"].pop1801_top_table.iloc[0])
R["manchester_rank1801"] = int(d[d.name == "Manchester"].rank1801.iloc[0])
# Manchester 1801 against the people of the rotten boroughs in 1831
R["manchester1801_vs_A_pop1831_x"] = round(R["manchester_pop1801"] / R["A_pop1831_total"], 1)

# ---------- today: what the places are
cls = Counter(A.today_class)
R["A_today_class"] = dict(cls.most_common())
R["n_A_town"] = cls["Town"] + cls["City"]
R["n_A_village"] = cls["Village"]
R["n_A_hamlet"] = cls["Hamlet"]
R["n_A_absorbed"] = cls["Part of a larger town"]
R["n_A_deserted"] = cls["Deserted site"]
R["n_A_village_or_smaller"] = cls["Village"] + cls["Hamlet"] + cls["Deserted site"]
R["n_B_town"] = int(Bs.today_class.isin(["Town", "City"]).sum())
R["A_absorbed_names"] = list(A[A.today_class == "Part of a larger town"].name)
R["A_village_names"] = list(A[A.today_class == "Village"].name)
R["A_hamlet_names"] = list(A[A.today_class == "Hamlet"].name)
R["A_town_names"] = list(A[A.today_class.isin(["Town", "City"])].name)

# ---------- today: people
pt = A[A.pop_today.notna()].copy()
R["n_A_pop_today"] = len(pt)
dedup = pt.drop_duplicates(subset=["pop_today", "bua22"]) if "bua22" in pt else pt
R["A_pop_today_total"] = int(dedup.pop_today.sum())
R["A_pop_today_median"] = float(pt.pop_today.median())
R["n_A_pop_today_census_bua"] = int(pt.pop_today_source.str.startswith("Census").sum())
R["n_A_pop_today_wd_parish"] = int(pt.pop_today_source.str.startswith("civil parish").sum())
R["n_A_under_1000_today"] = int((pt.pop_today < 1000).sum())
R["n_A_over_10000_today"] = int((pt.pop_today >= 10000).sum())
ntd = NEW[NEW.pop_today.notna()]
R["n_new_pop_today"] = len(ntd)
R["new_pop_today_median"] = float(ntd.pop_today.median())
R["manchester_bua_2021"] = int(d[d.name == "Manchester"].pop_today.iloc[0])
R["birmingham_bua_2021"] = int(d[d.name == "Birmingham"].pop_today.iloc[0])
R["leeds_bua_2021"] = int(d[d.name == "Leeds"].pop_today.iloc[0])
R["A_today_vs_manchester_pct"] = round(100 * R["A_pop_today_total"] / R["manchester_bua_2021"], 1)
R["A_today_vs_birmingham_pct"] = round(100 * R["A_pop_today_total"] / R["birmingham_bua_2021"], 1)
R["new_pop_today_total"] = int(ntd.drop_duplicates(subset=["bua22"]).pop_today.sum())
R["new_vs_A_today_x"] = round(R["new_pop_today_total"] / R["A_pop_today_total"])

# growth, 1831 borough to today (different boundaries; a rough guide)
# Heytesbury is left out: its 1831 figure (81) is the borough, a small part of a parish of 1,394, while today's figure is the parish
NOGROWTH = {"Heytesbury"}
R["growth_excluded"] = sorted(NOGROWTH)
g = A[(A.pop1831 > 0) & A.pop_today.notna() & ~A.name.isin(NOGROWTH)].copy()
g["growth"] = g.pop_today / g.pop1831
R["n_A_growth"] = len(g)
R["A_growth_median"] = round(float(g.growth.median()), 1)
R["n_A_shrank"] = int((g.growth < 1).sum())
R["n_A_grew_5x"] = int((g.growth >= 5).sum())
R["A_shrank"] = [{"name": r["name"], "pop1831": int(r.pop1831), "pop_today": int(r.pop_today), "source": r.pop_today_source[:40]} for _, r in g[g.growth < 1].sort_values("growth").iterrows()]
R["A_top_growth"] = [{"name": r["name"], "pop1831": int(r.pop1831), "pop_today": int(r.pop_today), "x": round(float(r.growth), 1)} for _, r in g.sort_values("growth", ascending=False).head(6).iterrows()]
rho, pv = stats.spearmanr(g.pop1831, g.pop_today)
R["A_growth_spearman"], R["A_growth_spearman_p"] = round(float(rho), 2), float(f"{pv:.2g}")
# England and Wales 1801 to 2021, for scale (Unreformed House of Commons table: 1801 population England 8,331,434 and Wales 541,546; Census 2021 TS001)
import csv
ctry = {}
with open(f"{H}/_data8/census/census2021-ts001-ctry.csv", encoding="utf-8") as f:
    for x in csv.reader(f):
        if x[0] == "2021":
            ctry[x[1]] = int(x[3])
R["england_2021"] = ctry.get("England")
R["wales_2021"] = ctry.get("Wales")
R["england_1801"] = 8331434
R["england_growth_1801_2021"] = round(R["england_2021"] / R["england_1801"], 1)

# ---------- today: income against neighbours (5 to 25 km)
def inc_stats(x, key):
    x = x[x.income_vs_ring_pct.notna()]
    R[f"{key}_n_income"] = len(x)
    R[f"{key}_income_vs_ring_median"] = round(float(x.income_vs_ring_pct.median()), 1)
    R[f"{key}_n_richer"] = int((x.income_vs_ring_pct > 0).sum())
    R[f"{key}_pct_richer"] = round(100 * (x.income_vs_ring_pct > 0).mean())
    R[f"{key}_income_median"] = int(x.income_place.median())
    return x


ai = inc_stats(A, "A")
bi = inc_stats(Bs, "B")
ni = inc_stats(NEW, "new")
w = stats.wilcoxon(ai.income_vs_ring_pct)
R["A_income_wilcoxon_p"] = float(f"{w.pvalue:.2g}")
mw = stats.mannwhitneyu(ai.income_vs_ring_pct, ni.income_vs_ring_pct)
R["A_vs_new_income_mw_p"] = float(f"{mw.pvalue:.2g}")
wn = stats.wilcoxon(ni.income_vs_ring_pct)
R["new_income_wilcoxon_p"] = float(f"{wn.pvalue:.2g}")
msoa = pd.read_csv(os.path.join(ROOT, "data", "msoa_income.csv"))
R["ew_msoa_income_median"] = int(msoa.income_fye2023.median())
R["n_A_above_ew_median"] = int((ai.income_place > R["ew_msoa_income_median"]).sum())
R["n_new_above_ew_median"] = int((ni.income_place > R["ew_msoa_income_median"]).sum())
R["A_richest"] = [{"name": r["name"], "pct": float(r.income_vs_ring_pct)} for _, r in ai.sort_values("income_vs_ring_pct", ascending=False).head(5).iterrows()]
R["A_poorest"] = [{"name": r["name"], "pct": float(r.income_vs_ring_pct)} for _, r in ai.sort_values("income_vs_ring_pct").head(5).iterrows()]
# village and town split for the rotten boroughs
for k, m in [("Atown", ai.today_class.isin(["Town", "City"])), ("Avillage", ai.today_class.isin(["Village", "Hamlet"]))]:
    R[f"{k}_income_vs_ring_median"] = round(float(ai[m].income_vs_ring_pct.median()), 1)
    R[f"{k}_n_income"] = int(m.sum())

# ---------- sources and coverage
cat = json.load(gzip.open(f"{H}/_data10/wikipedia_batch10.json.gz", "rt", encoding="utf-8"))["categories"]["Category:Rotten boroughs"]
R["n_category_members"] = len(cat)
R["n_category_constituency_articles"] = sum(1 for t in cat if "constituency" in t)
R["n_articles_used_A"] = int(A.wiki_article.notna().sum())
R["n_placed"] = int(d.lat.notna().sum())
R["n_rows"] = len(d)
R["place_methods"] = dict(Counter("OS Open Names" if str(m).startswith("OS") else "Wikipedia (Old Sarum hill)" for m in d.place_method))
R["retrieved"] = "27 October 2026"

# ---------- page data and GeoJSON
feats = []
for _, r in d.iterrows():
    props = {k: (None if (isinstance(v, float) and math.isnan(v)) else v) for k, v in r.items() if k not in ("lat", "lon")}
    feats.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [r.lon, r.lat]}, "properties": props})
json.dump({"type": "FeatureCollection", "features": feats}, open(os.path.join(ROOT, "data", "boroughs.geojson"), "w"), ensure_ascii=False)


def clean(o):
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items()}
    if isinstance(o, list):
        return [clean(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    return o


json.dump(clean(R), open(os.path.join(ROOT, "data", "results.json"), "w"), indent=1, ensure_ascii=False)
for k, v in R.items():
    print(k, "=", v)
