-- =====================================================================
-- Balearic Islands tourism — business questions on the star schema
-- Engine: DuckDB   Run: duckdb data/processed/tourism.duckdb < sql/analysis.sql
-- =====================================================================

-- Convenience view: hotel facts with readable dimensions
CREATE OR REPLACE VIEW v_hotel AS
SELECT d.date, d.year, d.month, d.month_name, d.season, r.region, m.market,
       f.travellers, f.overnight_stays
FROM fact_hotel f
JOIN dim_date   d USING (date_key)
JOIN dim_region r USING (region_key)
JOIN dim_market m USING (market_key);

CREATE OR REPLACE VIEW v_intl AS
SELECT d.date, d.year, d.month, d.season, r.region, f.*
FROM fact_international f
JOIN dim_date   d USING (date_key)
JOIN dim_region r USING (region_key);

-- Q1. How big are the Balearic Islands within Spain? (share of hotel nights & international tourists, 2025)
WITH h AS (
    SELECT region, SUM(overnight_stays) AS nights
    FROM v_hotel WHERE market = 'All guests' AND year = 2025 GROUP BY region
), i AS (
    SELECT region, SUM(tourists) AS tourists, SUM(spend_meur) AS spend_meur
    FROM v_intl WHERE year = 2025 GROUP BY region
)
SELECT h.region,
       ROUND(h.nights / 1e6, 1)                                                   AS hotel_nights_m,
       ROUND(100 * h.nights / MAX(h.nights) FILTER (WHERE h.region = 'Spain (total)') OVER (), 1) AS share_nights_pct,
       ROUND(i.tourists / 1e6, 1)                                                 AS intl_tourists_m,
       ROUND(100 * i.spend_meur / MAX(i.spend_meur) FILTER (WHERE i.region = 'Spain (total)') OVER (), 1) AS share_spend_pct
FROM h JOIN i USING (region)
ORDER BY hotel_nights_m DESC;

-- Q2. Seasonality: what % of the year's hotel nights happen in Jun-Sep? (2025)
SELECT region,
       ROUND(100 * SUM(overnight_stays) FILTER (WHERE season = 'Peak (Jun-Sep)') / SUM(overnight_stays), 1) AS peak_share_pct,
       ROUND(MAX(overnight_stays) / MIN(overnight_stays), 1)                                              AS peak_to_trough_ratio
FROM v_hotel
WHERE market = 'All guests' AND year = 2025
GROUP BY region
ORDER BY peak_share_pct DESC;

-- Q3. Recovery vs pre-pandemic: hotel nights and international spend, index 2019 = 100
WITH y AS (
    SELECT h.region, h.year, SUM(h.overnight_stays) AS nights
    FROM v_hotel h WHERE market = 'All guests' AND year IN (2019, 2020, 2021, 2022, 2023, 2024, 2025)
    GROUP BY ALL
)
SELECT region, year,
       ROUND(100 * nights / FIRST_VALUE(nights) OVER (PARTITION BY region ORDER BY year), 1) AS nights_index_2019
FROM y
ORDER BY region, year;

-- Q4. Is growth coming from more tourists or from higher spending? (Balearics, 2019 vs 2025)
SELECT year,
       ROUND(SUM(tourists) / 1e6, 2)                    AS tourists_m,
       ROUND(SUM(spend_meur), 0)                        AS spend_meur,
       ROUND(1e6 * SUM(spend_meur) / SUM(tourists), 0)  AS spend_per_tourist_eur
FROM v_intl
WHERE region = 'Balearic Islands' AND year IN (2019, 2023, 2024, 2025)
GROUP BY year ORDER BY year;

-- Q5. Who fills the hotels? International vs domestic share of nights and average length of stay (2025)
SELECT region, market,
       ROUND(SUM(overnight_stays) / 1e6, 1)                 AS nights_m,
       ROUND(SUM(overnight_stays) / SUM(travellers), 2)     AS avg_nights_per_guest
FROM v_hotel
WHERE year = 2025 AND market <> 'All guests'
GROUP BY ALL
ORDER BY region, market;

-- Q6. Latest trend: year-over-year change for the most recent 6 months available (Balearics)
WITH m AS (
    SELECT date, SUM(overnight_stays) AS nights
    FROM v_hotel WHERE region = 'Balearic Islands' AND market = 'All guests'
    GROUP BY date
)
SELECT strftime(date, '%Y-%m') AS month, nights,
       ROUND(100 * (nights / LAG(nights, 12) OVER (ORDER BY date) - 1), 1) AS yoy_pct
FROM m
QUALIFY date > (SELECT MAX(date) FROM m) - INTERVAL 6 MONTH
ORDER BY month;

-- Q7. Shoulder-season opportunity: which months grew fastest since 2019? (Balearics, hotel nights)
WITH m AS (
    SELECT month, month_name, year, SUM(overnight_stays) AS nights
    FROM v_hotel WHERE region = 'Balearic Islands' AND market = 'All guests' AND year IN (2019, 2025)
    GROUP BY ALL
)
SELECT month_name,
       MAX(nights) FILTER (WHERE year = 2019) AS nights_2019,
       MAX(nights) FILTER (WHERE year = 2025) AS nights_2025,
       ROUND(100 * (MAX(nights) FILTER (WHERE year = 2025) / MAX(nights) FILTER (WHERE year = 2019) - 1), 1) AS growth_pct
FROM m GROUP BY month, month_name ORDER BY month;
