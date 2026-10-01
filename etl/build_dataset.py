"""ETL: INE raw CSVs -> clean star schema (CSV + DuckDB) for SQL and Power BI.

Sources (INE, downloaded as 'CSV: separado por ;'):
  data/raw/2074.csv   Hotel Occupancy Survey (EOH): travellers & overnight stays by region, residence
  data/raw/10823.csv  FRONTUR: international tourist arrivals by main destination region
  data/raw/10839.csv  EGATUR: international tourist spending by main destination region

Output (data/processed/):
  dim_date.csv, dim_region.csv, dim_market.csv,
  fact_hotel.csv          one row per month x region x market (travellers, overnight_stays)
  fact_international.csv  one row per month x region (tourists, spend_meur, avg spend, avg stay)
  tourism.duckdb          the same tables, ready for SQL
"""
from pathlib import Path
import duckdb
import pandas as pd
from ine import read_ine_csv, clean_region

ROOT = Path(__file__).resolve().parents[1]
RAW, OUT = ROOT / "data" / "raw", ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)

# Regions present in both FRONTUR/EGATUR and EOH, so they are comparable
REGIONS = {
    "Total Nacional": "Spain (total)",
    "Total": "Spain (total)",
    "Balears, Illes": "Balearic Islands",
    "Canarias": "Canary Islands",
    "Cataluña": "Catalonia",
    "Andalucía": "Andalusia",
    "Comunitat Valenciana": "Valencian Community",
    "Madrid, Comunidad de": "Madrid",
}
MARKETS = {"Total": "All guests", "Residentes en España": "Domestic (Spain)",
           "Residentes en el Extranjero": "International"}


def hotel() -> pd.DataFrame:
    d = read_ine_csv(RAW / "2074.csv")
    ccaa, prov = "Comunidades y Ciudades Autónomas", "Provincias"
    # keep national totals and region-level rows (not province rows, which would double count)
    d = d[d[prov].isna()].copy()
    d["region_raw"] = d[ccaa].map(clean_region).fillna("Total Nacional")
    d["market_raw"] = d["Residencia: Nivel 2"].fillna("Total")
    d = d[d.region_raw.isin(REGIONS)]
    d["metric"] = d["Viajeros y pernoctaciones"].map({"Viajero": "travellers", "Pernoctaciones": "overnight_stays"})
    f = (d.pivot_table(index=["date", "region_raw", "market_raw"], columns="metric", values="value", aggfunc="sum")
           .reset_index())
    f["region"] = f.region_raw.map(REGIONS)
    f["market"] = f.market_raw.map(MARKETS)
    return f[["date", "region", "market", "travellers", "overnight_stays"]]


def international() -> pd.DataFrame:
    fr = read_ine_csv(RAW / "10823.csv")
    fr = fr[fr["Tipo de dato"] == "Dato base"].copy()
    fr["region_raw"] = fr["Comunidades autónomas"].map(clean_region)
    fr = fr[fr.region_raw.isin(REGIONS)][["date", "region_raw", "value"]].rename(columns={"value": "tourists"})

    eg = read_ine_csv(RAW / "10839.csv")
    eg = eg[eg["Tipo de dato"] == "Dato base"].copy()
    eg["region_raw"] = eg["Comunidades  autónomas"].map(clean_region)
    eg = eg[eg.region_raw.isin(REGIONS)]
    names = {"Gasto total": "spend_meur", "Gasto medio por persona": "spend_per_tourist_eur",
             "Gasto medio diario por persona": "spend_per_day_eur", "Duración media de los viajes": "avg_stay_days"}
    eg["metric"] = eg["Gastos y duración media de los viajes"].map(names)
    eg = eg.pivot_table(index=["date", "region_raw"], columns="metric", values="value").reset_index()

    f = fr.merge(eg, on=["date", "region_raw"], how="outer")
    f["region"] = f.region_raw.map(REGIONS)
    return f[["date", "region", "tourists", "spend_meur", "spend_per_tourist_eur",
              "spend_per_day_eur", "avg_stay_days"]]


def dim_date(dates) -> pd.DataFrame:
    d = pd.DataFrame({"date": sorted(set(dates))})
    d["date_key"] = d.date.dt.strftime("%Y%m").astype(int)
    d["year"], d["month"], d["quarter"] = d.date.dt.year, d.date.dt.month, d.date.dt.quarter
    d["month_name"] = d.date.dt.strftime("%b")
    d["season"] = d.month.map(lambda m: "Peak (Jun-Sep)" if m in (6, 7, 8, 9) else
                              "Shoulder (Apr-May, Oct)" if m in (4, 5, 10) else "Low (Nov-Mar)")
    d["is_covid_period"] = d.date.between("2020-03-01", "2021-12-01")
    return d


def main():
    h, i = hotel(), international()
    dd = dim_date(list(h.date) + list(i.date))
    regions = sorted(set(REGIONS.values()))
    dr = pd.DataFrame({"region_key": range(1, len(regions) + 1), "region": regions})
    dr["is_island"] = dr.region.isin(["Balearic Islands", "Canary Islands"])
    dm = pd.DataFrame({"market_key": [1, 2, 3], "market": list(MARKETS.values())})

    def keys(f):
        f = f.merge(dd[["date", "date_key"]], on="date").merge(dr[["region", "region_key"]], on="region")
        return f.drop(columns=["date", "region"])

    fh = keys(h).merge(dm, on="market").drop(columns="market")
    fh = fh[["date_key", "region_key", "market_key", "travellers", "overnight_stays"]].sort_values(
        ["date_key", "region_key", "market_key"])
    fi = keys(i)[["date_key", "region_key", "tourists", "spend_meur", "spend_per_tourist_eur",
                  "spend_per_day_eur", "avg_stay_days"]].sort_values(["date_key", "region_key"])

    tables = {"dim_date": dd.assign(date=dd.date.dt.date), "dim_region": dr, "dim_market": dm,
              "fact_hotel": fh, "fact_international": fi}
    db_path = OUT / "tourism.duckdb"
    db_path.unlink(missing_ok=True)
    con = duckdb.connect(str(db_path))
    for name, t in tables.items():
        t.to_csv(OUT / f"{name}.csv", index=False)
        con.register("t", t)
        con.execute(f"CREATE TABLE {name} AS SELECT * FROM t")
        con.unregister("t")
        print(f"{name:20s} {len(t):>7,} rows")
    con.close()


if __name__ == "__main__":
    main()
