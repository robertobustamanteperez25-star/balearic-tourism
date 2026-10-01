"""Builds the interactive dashboard from the DuckDB star schema.
Outputs docs/index.html (GitHub Pages) with the data embedded as JSON."""
import json
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parents[1]
con = duckdb.connect(str(ROOT / "data/processed/tourism.duckdb"), read_only=True)
m = con.sql("""
    SELECT r.region, d.year, d.month,
           SUM(overnight_stays) FILTER (WHERE m.market = 'All guests')    AS nights,
           SUM(overnight_stays) FILTER (WHERE m.market = 'International') AS nights_intl
    FROM fact_hotel f JOIN dim_date d USING (date_key) JOIN dim_region r USING (region_key)
    JOIN dim_market m USING (market_key)
    WHERE d.year >= 2015 GROUP BY ALL ORDER BY 1, 2, 3""").fetchall()
i = con.sql("""
    SELECT r.region, d.year, SUM(tourists), SUM(spend_meur), COUNT(*)
    FROM fact_international f JOIN dim_date d USING (date_key) JOIN dim_region r USING (region_key)
    GROUP BY ALL ORDER BY 1, 2""").fetchall()
data = {"monthly": {}, "intl": {}}
for reg, y, mo, n, ni in m:
    data["monthly"].setdefault(reg, []).append([y, mo, int(n), int(ni)])
for reg, y, t, s, k in i:
    data["intl"].setdefault(reg, []).append([y, round(t), round(s, 2), k])

body = (ROOT / "dashboard/template.html").read_text(encoding="utf-8").replace(
    "/*DATA*/null", json.dumps(data, separators=(",", ":")))
(ROOT / "dashboard/dashboard_body.html").write_text(body, encoding="utf-8")
page = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        '<style>body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>\n</head>\n<body>\n'
        + body + "\n</body>\n</html>\n")
(ROOT / "docs").mkdir(exist_ok=True)
(ROOT / "docs/index.html").write_text(page, encoding="utf-8")
print("docs/index.html written,", len(page) // 1024, "KB")
