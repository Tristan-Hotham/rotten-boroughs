"""Step 1. Every borough named in the Reform Act 1832 (England and Wales): its 1831 figures, where it is, and what it is today.

Reads (in place, never copied):
  _data10/wikipedia_batch10.json.gz   English Wikipedia wikitext (CC BY-SA 4.0), retrieved 27 Oct 2026:
                                      the constituency articles of Category:Rotten boroughs, "Rotten and pocket boroughs",
                                      "Cornish rotten and pocket boroughs", "Old Sarum"
  _data10/wd_osm_bundle10.json.gz     Wikidata constituencies (CC0), used as a fallback for coordinates
  osnames_gb.tsv                      OS Open Names (OGL v3): populated places
  _data8/ons_geo.json                 BUA22 points and areas, MSOA21 population-weighted centroids, MSOA to BUA lookup (OGL v3)
  _data8/lsoa21_bua22_lookup.json     LSOA21 to BUA22 best-fit lookup (OGL v3)
  _data8/census/census2021-ts001-*.csv Census 2021 usual residents (OGL v3)
  _data8/uk_bundle_wikidata_osm.json  Wikidata settlement populations (CC0), for civil parishes too small for a BUA figure
  _data8/ons_msoa_income_fye2023.xlsx ONS income estimates for small areas, FYE2023 (OGL v3)
  _data9/wikipedia_wikitext.json      "List of towns and cities in England by historical population" (1801 table)

Writes data/boroughs.csv (one row per borough in Schedules A to D plus Weymouth) and data/msoa_income.csv.
"""
import csv
import gzip
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict

import openpyxl

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schedules import A, B, C, D, W, LIST_URL  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H = "/home/claude/hist"
OUT = os.path.join(ROOT, "data")
os.makedirs(OUT, exist_ok=True)
KX, KY = 111.32 * math.cos(math.radians(52.5)), 110.57


def km(lon1, lat1, lon2, lat2):
    return math.hypot((lon1 - lon2) * KX, (lat1 - lat2) * KY)


wiki = json.load(gzip.open(f"{H}/_data10/wikipedia_batch10.json.gz", "rt", encoding="utf-8"))
ART = wiki["articles"]

# ---------------- 0. check Schedule A against the list printed in "Rotten and pocket boroughs"
rp = ART["Rotten and pocket boroughs"]["text"]
seg = rp[rp.find("disfranchised the 56 boroughs"):rp.find("{{col-end}}")]
listed = re.findall(r"^\*\s*\[\[[^|\]]+\|([^\]]+)\]\]", seg, re.M)
norm = lambda s: s.replace(", Isle of Wight", "").replace("Yarmouth", "Yarmouth (Isle of Wight)").replace("Newtown", "Newtown (Isle of Wight)").strip()
listed = sorted(norm(x) for x in listed)
mine = sorted(r[0].replace("Newport (Cornwall)", "Newport") for r in A)
assert len(listed) == 56 and len(A) == 56, (len(listed), len(A))
assert sorted(x.replace("Newport (Cornwall)", "Newport") for x in listed) == mine, set(listed) ^ set(mine)
assert len(B) == 30 and len(C) == 22 and len(D) == 21
print("Schedule A matches the on-disk list of 56")

# ---------------- 1. 1831 figures from the constituency articles
def clean(t):
    t = re.sub(r"<ref[^>]*/>", "", t)
    t = re.sub(r"<ref.*?</ref>", "", t, flags=re.S)
    t = re.sub(r"\{\{0\|?0*\}\}", "", t)
    return t


def box_electors(text, year="1831"):
    """electors in the article's election box for the general election of that year (History of Parliament based)."""
    for m in re.finditer(r"\{\{Election box begin[^\n]*?\[\[" + year + r" United Kingdom general election", text):
        end = text.find("{{Election box end}}", m.end())
        box = text[m.end():end]
        e = re.search(r"electors\s*=\s*(?:\{\{circa\|)?\s*(?:c\.\s*)?([\d,]+)", box)
        if e:
            return int(e.group(1).replace(",", "")), ("c. " if "circa" in box[e.start():e.end()] else "")
    return None, ""


POP_PAT = [r"population of the (?:borough|constituency) was (?:just over |about |approximately |only |estimated at )?([\d,]+)",
           r"(?:borough|it) had (?:an estimated |a )?population of (?:approximately |just |about )?([\d,]+)",
           r"population of (?:only |just )?([\d,]+)",
           r"population (?:in 1831 )?of ([\d,]+)",
           r"population was ([\d,]+) in 1831"]
HOUSE_PAT = [r"([\d,]+) houses"]

# hand-checked figures, each tied to its sentence (the regexes below are only a first pass; these win)
# keys: pop1831, houses1831, voters1831, voters_note
MANUAL = {
    "Aldborough": dict(pop1831=None, pop_note="article: 'a population only just over 500' at the time of the Reform Act (not used: not an 1831 figure)"),
    "Bramber": dict(pop1831=170, pop_note="article: 'in 1831 the borough contained 35 houses and a population of approximately 170'"),
    "Downton": dict(pop1831=None, pop_note="article gives 166 houses in the borough in 1831 and about 450 people in the parish: population not used"),
    "Gatton": dict(pop1831=146, pop_note="article: 'a population in 1831 of 146, and 23 houses' (village)"),
    "Heytesbury": dict(pop1831=81, houses1831=None, pop_note="article: 'the borough had a population of only 81' (parish 1,394)"),
    "Hindon": dict(pop1831=921, houses1831=185),
    "Okehampton": dict(pop1831=1508, houses1831=318),
    "Orford": dict(pop1831=1302, houses1831=246, pop_note="article: 'by the time of the Great Reform Act in 1832, the population of the borough was only 1,302, in 246 houses'"),
    "Seaford": dict(pop1831=None, houses1831=201, pop_note="article: 'just over 1,000' at the time of the Reform Act (not used as a number)"),
    "Steyning": dict(pop1831=None, houses1831=218, pop_note="article: 'just over 1,000' in 1831 (not used as a number)"),
    "Whitchurch": dict(pop1831=1673, houses1831=214, pop_note="article: town population about 1,673 and 261 houses, 214 of them in the borough"),
    "Amersham": dict(pop1831=1347, houses1831=247),
    "Appleby": dict(pop1831=1233, houses1831=None),
    "Mitchell": dict(pop1831=90, houses1831=23),
    "Newtown (Isle of Wight)": dict(pop1831=68, houses1831=14, pop_note="population 68 from the constituency article; 14 houses from the table in 'Rotten and pocket boroughs'"),
    "Old Sarum": dict(pop1831=0, houses1831=3, pop_note="no residents: 'an uninhabited hill' (Unreformed House of Commons); 3 houses in the table in 'Rotten and pocket boroughs'"),
    "Dunwich": dict(pop1831=232, houses1831=44),
    "East Looe": dict(pop1831=865, houses1831=167),
    "West Looe": dict(pop1831=593, houses1831=126),
    "Newport (Cornwall)": dict(pop1831=595, houses1831=106, pop_note="population from the constituency article; houses from the table in 'Cornish rotten and pocket boroughs'"),
    "Bossiney": dict(pop1831=308, houses1831=67),
    "Ludgershall": dict(pop1831=535, houses1831=None),
    "Corfe Castle": dict(pop1831=960, houses1831=156),
    "Ilchester": dict(pop1831=965, houses1831=231),
    "Wendover": dict(pop1831=802, houses1831=171),
    "Wootton Bassett": dict(pop1831=1500, houses1831=349),
    "New Romney": dict(pop1831=978, houses1831=165),
    "Winchelsea": dict(pop1831=772, houses1831=148),
    "Higham Ferrers": dict(pop1831=965, houses1831=169),
    "Wallingford": dict(pop1831=2500, houses1831=485),
    "Hedon": dict(pop1831=1080, houses1831=217),
    "Boroughbridge": dict(pop1831=947, houses1831=154),
    "Newton": dict(pop1831=2139, houses1831=285),
    "Shaftesbury": dict(pop1831=2742, houses1831=474),
    "Launceston": dict(pop1831=2669, houses1831=429),
    "Calne": dict(pop1831=2640, houses1831=487),
    "Tregony": dict(pop1831=1127, houses1831=234),
    "Yarmouth (Isle of Wight)": dict(pop1831=586, houses1831=114, pop_note="article: 'At the time that it was disfranchised, there were 114 houses in the borough and town, and a population of only 586'"),
    "Beeralston": dict(pop1831=None, houses1831=None, pop_note="article: 'The population was not separately recorded in the census'"),
}
# voters stated in the article text for 1831, used when the 1831 election box has no electorate
TEXT_VOTERS = {
    "Gatton": (7, "'only 7 qualified voters in 1831'"),
    "Old Sarum": (11, "'At its final election, in 1831, there were eleven voters'"),
    "Bossiney": (25, "'only 25 being entitled to vote' (1831)"),
    "Callington": (225, "'the Parliamentary return of 1831 reported that 225 were qualified' (42 in 1816)"),
    "Camelford": (31, "'estimated to be 31 in 1831' (the Reform Act article gives 25)"),
    "East Looe": (38, "'in 1831 the number of eligible voters was 38'"),
    "Fowey": (331, "'there were 331 voters in 1831'"),
    "Higham Ferrers": (33, "'in 1831 this comprised a total of 33 voters'"),
    "Hindon": (170, "'it was estimated that these amounted to 170 eligible voters' (1831)"),
    "Launceston": (17, "'about 17 voters in Launceston in 1831'"),
    "Mitchell": (7, "'reduced by 1831 to just seven'"),
    "Newport (Cornwall)": (12, "'by 1831 the number was only about 12'"),
    "Newton": (52, "'by 1831 it was estimated that the electorate had fallen to about 52'"),
    "St Germans": (7, "'there were only seven voters in 1831'"),
    "St Mawes": (87, "'there were 87 voters in 1831'"),
    "Seaford": (94, "'only 94 qualified voters in 1831'"),
    "Shaftesbury": (359, "'359 people voted in that year's election' (1831; about 400 properties rated)"),
    "Wallingford": (300, "'about 300 men qualified to vote in 1831'"),
    "Wendover": (130, "'about 130 voters in 1831'"),
    "West Looe": (19, "'19 in 1831'"),
    "Winchelsea": (11, "'by 1831 there were just 11' freemen"),
    "Orford": (22, "'about 22 men entitled to vote' (1832)"),
    "Whitchurch": (84, "'the number of \"voters\" was estimated to be about 84' (at the Reform Act)"),
    "Dunwich": (32, "'the maximum number of freemen had been set at 32' (the Reform Act article: Dunwich (32 voters))"),
    "Lostwithiel": (24, "table 'Boroughs with statistics for 1831' in 'Cornish rotten and pocket boroughs'"),
    "Saltash": (154, "table 'Boroughs with statistics for 1831' in 'Cornish rotten and pocket boroughs'"),
    "Tregony": (280, "table 'Boroughs with statistics for 1831' gives '260 to 300' voters; midpoint used"),
    "Bramber": (20, "table in 'Rotten and pocket boroughs' (20 voters); the article says 20 in 1816"),
    "Newtown (Isle of Wight)": (23, "'39 burgage tenements, held by 23 burgesses'; table in 'Rotten and pocket boroughs': 23 voters"),
    "Plympton Erle": (40, "table in 'Rotten and pocket boroughs' (40 voters)"),
}

rows = []
for sched, lst in (("A", A), ("B", B), ("W", W), ("C", C), ("D", D)):
    for name, county, osname, hint, title in lst:
        seats_before = {"A": 2, "B": 2, "W": 4, "C": 0, "D": 0}[sched]
        seats_after = {"A": 0, "B": 1, "W": 2, "C": 2, "D": 1}[sched]
        if name == "Higham Ferrers":
            seats_before = 1
        r = dict(name=name, schedule=sched, county_historic=county, seats_before=seats_before, seats_after=seats_after,
                 country="Wales" if name in ("Merthyr Tydfil", "Swansea") else "England", wiki_article=title or "")
        if title and title in ART and ART[title]["text"]:
            raw = ART[title]["text"]
            t = clean(raw)
            ev, circa = box_electors(raw, "1831")
            evsrc = "1831 general election box" if ev else ""
            if ev is None:
                ev, circa = box_electors(raw, "1830")
                evsrc = "1830 general election box" if ev else ""
            r["electors_box"] = ev
            r["electors_box_source"] = (circa + evsrc) if ev else ""
            sents = [s for s in re.split(r"(?<=[.;])\s", t) if "1831" in s or "Reform Act" in s]
            pop = houses = None
            for s in sents:
                if pop is None:
                    for p in POP_PAT:
                        m = re.search(p, s)
                        if m:
                            pop = int(m.group(1).replace(",", ""))
                            break
                if houses is None:
                    m = re.search(HOUSE_PAT[0], s)
                    if m:
                        houses = int(m.group(1).replace(",", ""))
            r["pop1831"], r["houses1831"] = pop, houses
            r["pop_note"] = "constituency article (1831 census figure for the borough)" if pop is not None else ""
        if name in MANUAL:
            r.update(MANUAL[name])
            r.setdefault("pop_note", "constituency article (1831 census figure for the borough)")
            if "pop_note" not in MANUAL[name] and r.get("pop1831") is not None:
                r["pop_note"] = "constituency article (1831 census figure for the borough)"
        # voters: the 1831 election box first, else the article text or tables
        if r.get("electors_box"):
            r["voters1831"] = r["electors_box"]
            r["voters_source"] = "constituency article, " + r["electors_box_source"]
        elif name in TEXT_VOTERS:
            r["voters1831"], q = TEXT_VOTERS[name]
            r["voters_source"] = "article text: " + q
        if name in TEXT_VOTERS:
            r["voters_text_alt"] = TEXT_VOTERS[name][0]
        r["_osname"], r["_hint"] = osname, hint
        rows.append(r)

# Rotten and pocket boroughs table (houses and voters for 9 examples) as a cross-check column
tab = rp[rp.find("+Examples of rotten boroughs"):]
tab = tab[:tab.find("|}")]
for line in tab.split("\n|-"):
    m = re.search(r"\[\[[^|\]]+\|([^\]]+)\]\]\s*\|\|[^|]*\|\|\s*([\d{}|0 ]*)\|\|\s*([\d{}|0 ]*)\|\|", line)
    if m:
        nm = norm(m.group(1))
        h = re.sub(r"\{\{0[^}]*\}\}|\s", "", m.group(2))
        v = re.sub(r"\{\{0[^}]*\}\}|\s", "", m.group(3))
        for r in rows:
            if r["name"] == nm:
                r["rp_table_houses"] = int(h) if h else None
                r["rp_table_voters"] = int(v) if v else None

# ---------------- 2. place each borough
ORDER = {"City": 0, "Town": 1, "Village": 2, "Suburban Area": 3, "Hamlet": 4, "Other Settlement": 5}
want = {r["_osname"] for r in rows}
osn = defaultdict(list)
with open(f"{H}/osnames_gb.tsv", encoding="utf-8") as f:
    for o in csv.DictReader(f, delimiter="\t"):
        if o["type"] != "populatedPlace":
            continue
        for nm in (o["name1"], o["name2"]):
            if nm in want:
                osn[nm].append(o)
for r in rows:
    c = [o for o in osn.get(r["_osname"], []) if r["_hint"].lower() in (o["district"] + " " + o["county"] + " " + o["populated_place"] + " " + o["region"]).lower()]
    c.sort(key=lambda o: ORDER.get(o["local_type"], 9))
    if c:
        o = c[0]
        r.update(lat=float(o["lat"]), lon=float(o["lon"]), os_name=o["name1"] if o["name1"] == r["_osname"] else o["name2"],
                 os_type=o["local_type"], os_district=o["district"] or o["county"], region=o["region"],
                 place_method=f"OS Open Names populated place '{r['_osname']}' ({o['local_type']}, {o['district'] or o['county']})")
    else:
        r.update(lat=None, lon=None, os_type="", place_method="NOT PLACED")
# Old Sarum: OS Open Names 'Old Sarum' is the modern housing development by the airfield; the borough was the hill.
osr = ART["Old Sarum"]["coord"]
for r in rows:
    if r["name"] == "Old Sarum":
        r["os_village_modern"] = f"OS Open Names 'Old Sarum' village (the modern estate) at {r['lat']:.5f}, {r['lon']:.5f}"
        r.update(lat=osr["lat"], lon=osr["lon"],
                 place_method="Wikipedia article 'Old Sarum' coordinates (the hillfort and castle site); the OS 'Old Sarum' village point is the new estate about 1.4 km away")
missing = [r["name"] for r in rows if r["lat"] is None]
print("not placed:", missing)

# what each place is today (OS Open Names local type), with plain-English classes
for r in rows:
    t = r.get("os_type", "")
    cls = {"City": "City", "Town": "Town", "Village": "Village", "Hamlet": "Hamlet",
           "Suburban Area": "Part of a larger town", "Other Settlement": "Other settlement"}.get(t, "")
    if r["name"] == "Old Sarum":
        cls = "Deserted site"
    if r["name"] == "Tower Hamlets":
        cls = "Part of a larger town"
    r["today_class"] = cls

# ---------------- 3. today: Census 2021 built-up areas, Wikidata parish populations, income
geo = json.load(open(f"{H}/_data8/ons_geo.json", encoding="utf-8"))
bua = {b["BUA22CD"]: b for b in geo["bua22_gb"]}
lsoa_pop = {}
with open(f"{H}/_data8/census/census2021-ts001-lsoa.csv", encoding="utf-8") as f:
    for x in csv.reader(f):
        if x[0] == "2021":
            lsoa_pop[x[2]] = int(x[3])
msoa_pop = {}
with open(f"{H}/_data8/census/census2021-ts001-msoa.csv", encoding="utf-8") as f:
    for x in csv.reader(f):
        if x[0] == "2021":
            msoa_pop[x[2]] = int(x[3])
bua_pop = Counter()
bua_nlsoa = Counter()
for x in json.load(open(f"{H}/_data8/lsoa21_bua22_lookup.json", encoding="utf-8")):
    if x["BUA22CD"] and x["LSOA21CD"] in lsoa_pop:
        bua_pop[x["BUA22CD"]] += lsoa_pop[x["LSOA21CD"]]
        bua_nlsoa[x["BUA22CD"]] += 1
bua_by_name = defaultdict(list)
for b in bua.values():
    bua_by_name[b["BUA22NM"].split(" (")[0]].append(b)
BUANAME = {"Royal Wootton Bassett": "Royal Wootton Bassett", "Plympton St Maurice": "Plymouth", "Devonport": "Plymouth",
           "East Looe": "Looe", "West Looe": "Looe", "Newport": "Launceston", "Stepney": "Tower Hamlets",
           "Greenwich": "Greenwich", "Brighton": "Brighton and Hove", "Stoke-on-Trent": "Stoke-on-Trent",
           "Newton-le-Willows": "Newton-le-Willows", "Appleby-in-Westmorland": "Appleby-in-Westmorland",
           "Merthyr Tydfil": "Merthyr Tydfil", "Swansea": "Swansea", "Droitwich Spa": "Droitwich Spa",
           "Grimsby": "Grimsby", "Weymouth": "Weymouth"}

wd = json.load(open(f"{H}/_data8/uk_bundle_wikidata_osm.json", encoding="utf-8"))["wd_settlements_pop_tsv"].split("\n")
wdpop = defaultdict(list)
for line in wd[1:]:
    p = line.split("\t")
    if len(p) < 5 or not p[4]:
        continue
    m = re.match(r"Point\((\S+) (\S+)\)", p[3], re.I)
    if not m:
        continue
    lab = p[1].strip('"').replace('"@en', "")
    lab = re.sub(r'"@en$', "", p[1]).strip('"')
    wdpop[lab].append(dict(item=p[0].strip("<>").split("/")[-1], cls=p[2].split('"')[1] if '"' in p[2] else p[2],
                           lon=float(m.group(1)), lat=float(m.group(2)), pop=float(p[4])))

for r in rows:
    if r["lat"] is None:
        continue
    nm = BUANAME.get(r["_osname"], r["_osname"])
    c = [b for b in bua_by_name.get(nm, []) if km(b["LONG"], b["LAT"], r["lon"], r["lat"]) < 12]
    if c:
        b = min(c, key=lambda b: km(b["LONG"], b["LAT"], r["lon"], r["lat"]))
        r.update(bua22cd=b["BUA22CD"], bua22=b["BUA22NM"], bua_pop2021=bua_pop.get(b["BUA22CD"], 0),
                 bua_area_ha=round(b["Shape__Area"] / 1e4, 1))
    cands = []
    for lab in {r["_osname"], r["name"].split(" (")[0], r["name"]}:
        for w in wdpop.get(lab, []):
            if km(w["lon"], w["lat"], r["lon"], r["lat"]) < 4 and w["cls"] in ("civil parish", "village", "town", "hamlet", "market town", "community"):
                cands.append(w)
    par = [w for w in cands if w["cls"] == "civil parish"] or cands
    if par:
        w = max(par, key=lambda w: w["pop"])
        r.update(wd_parish_item=w["item"], wd_parish_pop=int(w["pop"]), wd_parish_class=w["cls"])

# choose the population today
for r in rows:
    bp = r.get("bua_pop2021") or 0
    pp = r.get("wd_parish_pop")
    absorbed = r["today_class"] == "Part of a larger town"
    if r["name"] == "Old Sarum":
        r.update(pop_today=0, pop_today_source="no residents on the hill today (English Heritage site); the modern 'Old Sarum' estate nearby is a separate place")
    elif absorbed and r["name"] not in ("East Looe", "West Looe", "Lambeth", "Greenwich", "Tower Hamlets"):
        r.update(pop_today=None, pop_today_source="now part of a larger built-up area; no separate figure")
    elif bp >= 5000:
        r.update(pop_today=bp, pop_today_source="Census 2021, built-up area (BUA22) " + r["bua22"] + " (sum of best-fit LSOAs)")
    elif pp:
        r.update(pop_today=pp, pop_today_source=f"civil parish population on Wikidata ({r['wd_parish_item']}; census year not recorded in the extract)")
    elif bp > 0:
        r.update(pop_today=bp, pop_today_source="Census 2021, built-up area (BUA22) " + r["bua22"] + " (sum of best-fit LSOAs)")
    else:
        r.update(pop_today=None, pop_today_source="no figure found")
    if r["name"] in ("East Looe", "West Looe"):
        r["pop_today_source"] += "; shared by East and West Looe (counted once in totals)"

# income: the MSOA whose population-weighted centroid is nearest, and the ring of MSOAs 5 to 25 km away
inc = {}
ws = openpyxl.load_workbook(f"{H}/_data8/ons_msoa_income_fye2023.xlsx", read_only=True)["Total annual income"]
for i, x in enumerate(ws.iter_rows(values_only=True)):
    if i >= 4 and x[0] and isinstance(x[6], (int, float)):
        inc[x[0]] = dict(name=x[1], lad=x[3], rgn=x[5], inc=x[6])
pwc = [(m["MSOA21CD"], m["_x"], m["_y"]) for m in geo["msoa21_pwc"] if m["MSOA21CD"] in inc]
with open(os.path.join(OUT, "msoa_income.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["msoa21cd", "msoa_name", "lad", "region", "lon", "lat", "pop2021", "income_fye2023"])
    for code, x, y in pwc:
        w.writerow([code, inc[code]["name"], inc[code]["lad"], inc[code]["rgn"], round(x, 5), round(y, 5), msoa_pop.get(code, ""), inc[code]["inc"]])
msoa_bua = {x["MSOA21CD"]: x["BUA22CD"] for x in geo["msoa21_bua22_lookup"]}
bua_msoas = defaultdict(list)
for c, b in msoa_bua.items():
    if b and c in inc:
        bua_msoas[b].append(c)


def wmean(codes):
    p = sum(msoa_pop.get(c, 0) for c in codes)
    return sum(inc[c]["inc"] * msoa_pop.get(c, 0) for c in codes) / p if p else None


for r in rows:
    if r["lat"] is None:
        continue
    d = sorted(((km(x, y, r["lon"], r["lat"]), code) for code, x, y in pwc))
    dd, code = d[0]
    own = bua_msoas.get(r.get("bua22cd"), []) if r.get("today_class") != "Part of a larger town" or r["name"] in ("Lambeth", "Tower Hamlets", "Greenwich") else []
    if own:
        place_inc, how = wmean(own), f"built-up area {r['bua22']} ({len(own)} MSOAs, population-weighted)"
    else:
        place_inc, how = inc[code]["inc"], f"nearest MSOA {inc[code]['name']} ({dd:.1f} km to its population-weighted centre)"
    ring = [c for k, c in d if 5 <= k <= 25 and c not in own and c != code]
    ring_inc = wmean(ring)
    r.update(msoa21cd=code, msoa_name=inc[code]["name"], msoa_km=round(dd, 2), income_msoa=inc[code]["inc"],
             income_place=round(place_inc), income_place_method=how,
             income_ring_5_25km=round(ring_inc) if ring_inc else None, n_ring_msoa=len(ring),
             income_vs_ring_pct=round(100 * (place_inc / ring_inc - 1), 1) if ring_inc else None,
             la_today=inc[code]["lad"])

# ---------------- 4. 1801 populations from the historical population list (largest towns only)
text = json.load(open(f"{H}/_data9/wikipedia_wikitext.json", encoding="utf-8"))["List of towns and cities in England by historical population"]["text"]
tabs = re.findall(r"\{\|(.*?)\n\|\}", text, re.S)
t1801 = {}
for tb in tabs:
    cap = re.search(r"\|\+\s*([^<\n]*)", tb)
    if not cap or not cap.group(1).strip().startswith("1801"):
        continue
    body = re.sub(r"<ref.*?</ref>|<ref[^>]*/>", "", tb, flags=re.S)
    for x in body.split("\n|-"):
        m = re.search(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", x)
        num = re.search(r"\|\|\s*([\d,]{4,})", x[m.end():]) if m else None
        rk = re.match(r"\s*\|\s*(\d+)\s*\|\|", x.strip("\n"))
        if m and num:
            t1801[(m.group(2) or m.group(1)).split(",")[0].strip()] = (int(num.group(1).replace(",", "")), int(rk.group(1)) if rk else None)
print("1801 table rows", len(t1801))
ALIAS1801 = {"Stoke-upon-Trent": "Stoke-on-Trent", "Great Grimsby": "Grimsby", "Brighton": "Brighton"}
for r in rows:
    k = r["name"] if r["name"] in t1801 else ALIAS1801.get(r["name"], r["name"])
    if k in t1801:
        r["pop1801_top_table"], r["rank1801"] = t1801[k]
json.dump({k: v for k, v in t1801.items()}, open(os.path.join(OUT, "_t1801.json"), "w"))

cols = ["name", "schedule", "county_historic", "country", "seats_before", "seats_after", "wiki_article",
        "pop1831", "houses1831", "pop_note", "voters1831", "voters_source", "electors_box", "electors_box_source", "voters_text_alt",
        "rp_table_houses", "rp_table_voters",
        "lat", "lon", "place_method", "os_name", "os_type", "os_district", "region", "today_class", "os_village_modern",
        "bua22cd", "bua22", "bua_pop2021", "bua_area_ha", "wd_parish_item", "wd_parish_pop", "wd_parish_class",
        "pop_today", "pop_today_source", "pop1801_top_table", "rank1801",
        "msoa21cd", "msoa_name", "msoa_km", "la_today", "income_msoa", "income_place", "income_place_method", "income_ring_5_25km", "n_ring_msoa", "income_vs_ring_pct"]
with open(os.path.join(OUT, "boroughs.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        if r.get("lat") is not None:
            r["lat"], r["lon"] = round(r["lat"], 5), round(r["lon"], 5)
        w.writerow(r)
print("rows", len(rows), Counter(r["schedule"] for r in rows))
print("list source:", LIST_URL)
