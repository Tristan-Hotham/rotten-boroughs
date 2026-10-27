"""Step 3. Build index.html from code/page_template.html.

Every number in the text is a {{key|format}} token filled from data/results.json, so the page cannot drift
from the analysis. The borough table (data/boroughs.csv) is embedded for the map, charts and table, so the page
works as a single file.

Usage:
    python3 code/03_build_page.py
"""
import csv
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = json.load(open(os.path.join(ROOT, "data", "results.json"), encoding="utf-8"))


def get(path):
    v = R
    for k in path.split("."):
        v = v[int(k)] if isinstance(v, list) else v[k]
    return v


def fmt(v, f):
    if f in (None, "raw"):
        return str(v)
    if f == "int":
        return f"{round(v):,}"
    if f == "f1":
        return f"{v:.1f}"
    if f == "f2":
        return f"{v:.2f}"
    if f == "p0":
        return f"{round(v)}%"
    if f == "p1":
        return f"{v:.1f}%"
    if f == "abs1":
        return f"{abs(v):.1f}%"
    if f == "gbp":
        return f"£{round(v):,}"
    if f == "p":
        return f"= {v:.2g}" if v >= 0.001 else "< 0.001"
    raise ValueError(f)


def num(x):
    if x in ("", None):
        return None
    v = float(x)
    return int(v) if v == int(v) else round(v, 1)


def short_src(s):
    if not s:
        return ""
    if s.startswith("Census"):
        return "Census 2021 built-up area"
    if s.startswith("civil parish"):
        return "civil parish (Wikidata)"
    return s.split(";")[0]


def site_rows():
    out = []
    for r in csv.DictReader(open(os.path.join(ROOT, "data", "boroughs.csv"), encoding="utf-8")):
        out.append([r["name"], r["schedule"], r["county_historic"], round(float(r["lat"]), 4), round(float(r["lon"]), 4),
                    int(r["seats_before"]), int(r["seats_after"]), num(r["pop1831"]), num(r["houses1831"]), num(r["voters1831"]),
                    r["voters_source"].replace("constituency article, ", "")[:120], r["today_class"], num(r["pop_today"]),
                    short_src(r["pop_today_source"]), num(r["income_place"]), num(r["income_vs_ring_pct"]),
                    num(r["pop1801_top_table"]), num(r["rank1801"]), r["la_today"], r["region"],
                    "Wikipedia" if r["place_method"].startswith("Wikipedia") else "OS Open Names"])
    return out


used = []


def sub(m):
    used.append(m.group(1))
    return fmt(get(m.group(1)), m.group(3))


if __name__ == "__main__":
    tpl = open(os.path.join(ROOT, "code", "page_template.html"), encoding="utf-8").read()
    html = re.sub(r"\{\{([^}|]+)(\|(\w+))?\}\}", sub, tpl)
    slim = {k: R[k] for k in ["A_by_county", "cornwall_mps_1821", "cornwall_mps_1832", "top1801_new", "smallest_electorates",
                              "ew_msoa_income_median", "A_today_class"]}
    html = html.replace("/*SITE*/", json.dumps(site_rows(), ensure_ascii=False, separators=(",", ":")))
    html = html.replace("/*RESULTS*/", json.dumps(slim, ensure_ascii=False, separators=(",", ":")))
    assert "{{" not in html
    with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("index.html", len(html.encode()), "bytes;", len(used), "tokens filled")
    # README from its template, numbers from results.json
    RR = dict(R, A_voters_median_i=int(R["A_voters_median"]), top1801_new_pop_total_c=f"{R['top1801_new_pop_total']:,}")
    rd = open(os.path.join(ROOT, "code", "README_template.md"), encoding="utf-8").read()
    rd = re.sub(r"\{\{(\w+)\}\}", lambda m: str(RR[m.group(1)]), rd)
    assert "{{" not in rd
    open(os.path.join(ROOT, "README.md"), "w", encoding="utf-8").write(rd)
    print("README.md written")
