# Power BI version — step by step

The ETL already produces a clean **star schema** in `data/processed/`. This guide rebuilds the dashboard in Power BI Desktop
(≈ 1 hour). It covers the skills the PL-300 exam checks: importing, modelling, DAX and report design.

## 1. Load the tables
*Home → Get data → Text/CSV* and load these five files from `data/processed/`:

| Table | Type | Grain |
|---|---|---|
| `dim_date.csv` | Dimension | one row per month |
| `dim_region.csv` | Dimension | Spain + 6 main destinations |
| `dim_market.csv` | Dimension | All guests / Domestic / International |
| `fact_hotel.csv` | Fact | month × region × market |
| `fact_international.csv` | Fact | month × region |

In Power Query, check that `date` in `dim_date` is typed as **Date** and that all numeric columns are **Decimal number**.

## 2. Build the model (Model view)
Create these one-to-many, single-direction relationships:

```
dim_date[date_key]     1 ──▶ * fact_hotel[date_key]
dim_region[region_key] 1 ──▶ * fact_hotel[region_key]
dim_market[market_key] 1 ──▶ * fact_hotel[market_key]
dim_date[date_key]     1 ──▶ * fact_international[date_key]
dim_region[region_key] 1 ──▶ * fact_international[region_key]
```
Mark `dim_date` as a date table (*Table tools → Mark as date table → date*). Sort `month_name` by `month`.
Hide all `*_key` columns in report view.

## 3. DAX measures
Create a table called `_Measures` (*Enter data* with one empty column) and add:

```DAX
Hotel Nights =
CALCULATE ( SUM ( fact_hotel[overnight_stays] ), dim_market[market] = "All guests" )

Hotel Guests =
CALCULATE ( SUM ( fact_hotel[travellers] ), dim_market[market] = "All guests" )

Avg Nights per Guest = DIVIDE ( [Hotel Nights], [Hotel Guests] )

International Share % =
DIVIDE (
    CALCULATE ( SUM ( fact_hotel[overnight_stays] ), dim_market[market] = "International" ),
    [Hotel Nights]
)

Hotel Nights 2019 =
CALCULATE ( [Hotel Nights], dim_date[year] = 2019, REMOVEFILTERS ( dim_date[year] ) )

Growth vs 2019 % = DIVIDE ( [Hotel Nights], [Hotel Nights 2019] ) - 1

Hotel Nights PY = CALCULATE ( [Hotel Nights], SAMEPERIODLASTYEAR ( dim_date[date] ) )

YoY % = DIVIDE ( [Hotel Nights] - [Hotel Nights PY], [Hotel Nights PY] )

Peak Season Share % =
DIVIDE (
    CALCULATE ( [Hotel Nights], dim_date[season] = "Peak (Jun-Sep)" ),
    CALCULATE ( [Hotel Nights], REMOVEFILTERS ( dim_date[season], dim_date[month], dim_date[month_name] ) )
)

Share of Year % =
DIVIDE ( [Hotel Nights],
         CALCULATE ( [Hotel Nights], REMOVEFILTERS ( dim_date[month], dim_date[month_name], dim_date[season] ) ) )

Intl Tourists = SUM ( fact_international[tourists] )

Intl Spend (€M) = SUM ( fact_international[spend_meur] )

Spend per Tourist (€) = DIVIDE ( [Intl Spend (€M)] * 1e6, [Intl Tourists] )

Share of Spain Nights % =
DIVIDE ( [Hotel Nights],
         CALCULATE ( [Hotel Nights], dim_region[region] = "Spain (total)" ) )
```

## 4. Report pages
**Page 1 — Overview** (filter `dim_region[region] = Balearic Islands`, slicer on `year`)
- 5 cards: `Hotel Nights`, `Intl Tourists`, `Intl Spend (€M)`, `Spend per Tourist (€)`, `Peak Season Share %`
- Line chart: x = `dim_date[date]`, y = `Hotel Nights`, legend = `region` (Balearic Islands + one comparison)

**Page 2 — Seasonality**
- Line chart: x = `month_name`, y = `Share of Year %`, legend = `region`, slicer on `year`
- Column chart: x = `month_name`, y = `Growth vs 2019 %` (filter year = 2025), conditional colour by `season`

**Page 3 — Benchmark**
- Table: `region`, `Hotel Nights`, `Growth vs 2019 %`, `Intl Tourists`, `Spend per Tourist (€)`, `Peak Season Share %`
  with data bars on `Peak Season Share %`

## 5. Check your numbers
With year = 2025 and region = Balearic Islands you should see: **63.4M** hotel nights, **15.7M** international tourists,
**€21,060M** spend, **€1,340** per tourist, **66%** of nights in Jun–Sep. If a number differs, check the market filter
in `Hotel Nights` and the relationships.

Save as `balearic_tourism.pbix`, export a screenshot of each page to `images/powerbi_*.png` and add them to the README.
