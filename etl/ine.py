"""Helpers to read INE (Instituto Nacional de Estadística) CSV exports.

INE 'CSV: separado por ;' files look like:
    Comunidades y Ciudades Autónomas;...;Periodo;Total
    04 Balears, Illes;...;2024M07;1.234.567
Numbers use '.' for thousands and ',' for decimals; missing values are '..' or empty.
"""
import re
import pandas as pd


def to_number(s: pd.Series) -> pd.Series:
    s = s.astype(str).str.strip().replace({"..": None, "": None, "nan": None, ".": None})
    s = s.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    return pd.to_numeric(s, errors="coerce")


def parse_period(p: str):
    """'2024M07' -> 2024-07-01, '2024T3' -> quarter start, '2024' -> 2024-01-01."""
    p = str(p).strip()
    if m := re.fullmatch(r"(\d{4})M(\d{2})", p):
        return pd.Timestamp(int(m[1]), int(m[2]), 1)
    if m := re.fullmatch(r"(\d{4})T(\d)", p):
        return pd.Timestamp(int(m[1]), 3 * int(m[2]) - 2, 1)
    if re.fullmatch(r"\d{4}", p):
        return pd.Timestamp(int(p), 1, 1)
    return pd.NaT


def read_ine_csv(path) -> pd.DataFrame:
    for enc in ("utf-8-sig", "latin-1"):
        try:
            df = pd.read_csv(path, sep=";", dtype=str, encoding=enc)
            break
        except UnicodeDecodeError:
            continue
    df.columns = [c.strip() for c in df.columns]
    df = df.rename(columns={"Total": "value", "Periodo": "period"})
    df["value"] = to_number(df["value"])
    df["date"] = df["period"].map(parse_period)
    for c in df.columns:
        if df[c].dtype == object and c not in ("period",):
            df[c] = df[c].str.strip()
    return df


def clean_region(name: str) -> str:
    """'04 Balears, Illes' -> 'Balears, Illes'; 'Total Nacional' stays."""
    if not isinstance(name, str):
        return name
    return re.sub(r"^\d{2}\s+", "", name).strip()
