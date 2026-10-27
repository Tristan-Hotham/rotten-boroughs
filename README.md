# Rotten Boroughs: Where Are They Now?

Before 1832, places like Old Sarum, Gatton and Dunwich sent two MPs to Westminster with a handful of voters, while Manchester and Birmingham had none. This study maps every borough named in the Reform Act 1832's schedules and follows the places to Census 2021 and the ONS income estimates.

**Interactive version:** https://tristan-hotham.github.io/rotten-boroughs/

**Paper:** https://doi.org/10.5281/zenodo.23691900

This repository holds the interactive page, the datasets, the computed results and the analysis code for a data study by Dr Tristan Hotham (Independent researcher).

## Headline results

- The Act's schedules as used here: 56 boroughs disfranchised (Schedule A, 111 seats), 30 cut to one member (Schedule B), Weymouth and Melcombe Regis cut from four to two: 143 borough seats removed. 43 new boroughs (22 with two members, 21 with one) received 65 seats.
- 47 of the 56 disfranchised boroughs lie in today's South West, South East and East of England; 32 of the 43 new boroughs lie in the North, the Midlands or Wales. Cornwall alone had 13 of the 56, and its MPs fell from 44 to 14.
- For the 34 disfranchised boroughs with a known 1831 electorate, the median was 39 voters; Gatton, Mitchell and St Germans had 7 each. 12 of England's 30 largest towns in 1801 (with 352,572 people between them) had no MP of their own before 1832.
- Today, by OS Open Names, 27 of the 56 disfranchised boroughs are towns, 23 villages, one a hamlet (Newtown, Isle of Wight), 4 parts of larger towns, and Old Sarum an empty hill: 25 are villages, a hamlet or an empty site.
- Where both figures exist (33 boroughs), the median grew 4.6 times since 1831; 7 have fewer people now, among them Dunwich and Castle Rising.
- In household income (FYE2023) the disfranchised boroughs are level with the area 5 to 25 km around them (median 0.0%, 26 of 56 above). The new boroughs of 1832 are below theirs (median -4.8%, 10 of 43 above; Mann-Whitney p = 0.028 for the difference between the groups).

These are descriptions, not causes.

## Files

- `index.html`: the interactive page (map of every borough, charts, sortable table). Data embedded; works as a single file.
- `header.png`: social card (1200 by 630).
- `data/boroughs.csv`: one row per borough in Schedules A to D and Weymouth (130 rows): schedule, county, seats before and after, 1831 population, houses and voters with the source of each, alternative figures where sources disagree, coordinates and how they were found, OS Open Names place type today, built-up area and its Census 2021 population, Wikidata civil parish population, the population used today and its source, 1801 population and rank (largest towns only), household income and the comparison ring.
- `data/boroughs.geojson`: the same as points.
- `data/msoa_income.csv`: the ONS FYE2023 mean household income for each MSOA in England and Wales with its population-weighted centroid and 2021 population (the comparison base).
- `data/_t1801.json`: the 1801 table of the 30 largest towns, as parsed.
- `data/results.json`: every number quoted on the page, in the paper, the blog post and the collage.
- `code/schedules.py`: the four schedules, with the OS Open Names lookups.
- `code/01_boroughs.py`: 1831 figures from the Wikipedia articles (with the hand-checked values and the sentence each comes from), placing, today's population and income.
- `code/02_analyse.py`: counts, comparisons and tests; writes `results.json` and the GeoJSON.
- `code/03_build_page.py`: fills `code/page_template.html` from `results.json` to make `index.html`.
- `code/04_header.py`: renders `header.png` with Playwright.
- `release/`: the paper (PDF, LaTeX source and figures), the blog post and figures, and the Zenodo files. Rebuild with `python3 release/make_figures.py [font_dir]`, `python3 release/paper/build_paper.py`, `python3 release/blog/build_post.py` and `python3 release/build_release_meta.py`.
- `reddit/`: the collage, its script and the post text.

## How to rerun

The scripts read the source files in place (paths at the top of each script): the Wikipedia and Wikidata bundles retrieved on 27 October 2026, OS Open Names, ONS geography lookups, Census 2021 TS001, the ONS small area income estimates for FYE2023, and the Natural Earth coastline (header and figures only).

```
python3 code/01_boroughs.py
python3 code/02_analyse.py
python3 code/03_build_page.py
python3 code/04_header.py [font_dir]
```

It needs Python 3 with pandas, numpy, scipy, openpyxl, matplotlib and playwright.

## Method in brief

- Schedules: Wikipedia's List of constituencies enfranchised and disfranchised by the Reform Act 1832, with Schedule A checked against the list in Rotten and pocket boroughs. The seat counts reproduce the Act's totals.
- 1831 voters: the electorate in the constituency article's box for the 1831 general election (or 1830), otherwise a figure in the text, otherwise the 1831 tables in Cornish rotten and pocket boroughs and Rotten and pocket boroughs. Populations and houses from the text, checked by hand.
- Places: OS Open Names populated places, matched by name and county. Old Sarum is placed on the hill from Wikipedia's coordinates, because OS Open Names' Old Sarum is a new estate about 1.4 km away.
- Population today: Census 2021, summed over best-fit LSOAs to the built-up area (BUA22), used for places of 5,000 or more; otherwise the civil parish population on Wikidata.
- Income: ONS mean total household income FYE2023, averaged over the place's built-up area MSOAs (or the nearest MSOA for villages), compared with the population-weighted mean of MSOAs 5 to 25 km away.

## Known limits

- Electorates before 1832 are estimates; found for 34 of 56 Schedule A boroughs and few Schedule B boroughs. Alternatives are kept in the data.
- The 1831 borough and today's built-up area or parish rarely share boundaries; growth ratios are rough. Heytesbury is left out of growth (borough of 81 people inside a parish of 1,394).
- Wikidata parish populations do not record their census year in the extract used.
- Gatton, Mitchell, St Mawes, Newtown and Aldborough have no population figure today in these sources.
- MSOAs hold several thousand people, so villages take the income of a wider rural area.
- Schedules from a Wikipedia list rather than the Act's text; Scotland and Ireland are not included.

## Sources and licences

- Wikipedia articles (List of constituencies enfranchised and disfranchised by the Reform Act 1832; Reform Act 1832; Rotten and pocket boroughs; Unreformed House of Commons; Cornish rotten and pocket boroughs; Parliamentary representation from Cornwall; Old Sarum; the constituency articles in Category:Rotten boroughs; List of towns and cities in England by historical population): CC BY-SA 4.0, retrieved 27 October 2026.
- Wikidata (civil parish populations): CC0.
- Census 2021 (TS001) and Income estimates for small areas, England and Wales, financial year ending 2023: Office for National Statistics, Open Government Licence v3.0.
- OS Open Names and ONS geography (BUA22, MSOA and LSOA lookups and centroids): contains OS data © Crown copyright and database right 2026; Open Government Licence v3.0.
- Coastline (header and static figures): Natural Earth, public domain.
- Base map tiles: Esri.

The data in `data/` and the text of the page are released under CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/), because they derive from Wikipedia. The code (`code/`) is released under the MIT licence (see `LICENSE`).

## Citation

Hotham, T. (2026). Rotten Boroughs: Where Are They Now? England's Disfranchised Boroughs of 1832 and Their Places Today. Zenodo. https://doi.org/10.5281/zenodo.23691900

I wrote the text, with drafting and editing assistance from Claude (Anthropic), which also helped prepare the analysis code. I reviewed and checked all text and results.
