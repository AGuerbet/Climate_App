import requests
import pandas as pd
import numpy as np
from datetime import datetime

def get_fast_climate(lat, lon):

    end_date = datetime.today().strftime('%Y-%m-%d')

    url = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date=1995-01-01&end_date={end_date}&daily=temperature_2m_mean,temperature_2m_max,temperature_2m_min,precipitation_sum&timezone=auto"

    data = requests.get(url).json()

    if "daily" not in data or data["daily"] is None:
        return {"error": "No data returned"}

    df = pd.DataFrame(data["daily"])
    df["time"] = pd.to_datetime(df["time"])
    df["year"] = df["time"].dt.year

    # ❗ REMOVE CURRENT YEAR (scientific consistency)
    current_year = datetime.today().year
    df = df[df["year"] < current_year]

    # --------------------------
    # BASELINE (1995–2024)
    # --------------------------
    baseline = df[(df["year"] >= 1995) & (df["year"] <= 2024)]

    # Temperature thresholds
    tx90 = np.percentile(baseline["temperature_2m_max"], 90)
    tn10 = np.percentile(baseline["temperature_2m_min"], 10)

    # Rain thresholds
    r95 = np.percentile(baseline["precipitation_sum"], 95)
    r99 = np.percentile(baseline["precipitation_sum"], 99)

    # SPI baseline (annual totals)
    annual_rain = baseline.groupby("year")["precipitation_sum"].sum()
    rain_mean = annual_rain.mean()
    rain_std = annual_rain.std()

    results = []

    for year, g in df.groupby("year"):

        # ---- THERMAL ----
        mean_temp = g["temperature_2m_mean"].mean()
        tx90p = (g["temperature_2m_max"] > tx90).mean() * 100
        tn10p = (g["temperature_2m_min"] < tn10).mean() * 100

        # ---- HYDRO ----
        rain_total = g["precipitation_sum"].sum()

        spi = (rain_total - rain_mean) / rain_std if rain_std != 0 else 0

        r95p = g[g["precipitation_sum"] > r95]["precipitation_sum"].sum()
        r99p = g[g["precipitation_sum"] > r99]["precipitation_sum"].sum()

        results.append({
            "year": int(year),
            "thermal": {
                "mean_temp": float(mean_temp),
                "tx90p": float(tx90p),
                "tn10p": float(tn10p)
            },
            "hydrological": {
                "rain_total": float(rain_total),
                "spi": float(spi),
                "r95p": float(r95p),
                "r99p": float(r99p)
            }
        })

    return {
        "data": results,
        "baseline": "1995-2024",
        "mode": "scientific (complete years only)",
        "source": "Open-Meteo (ERA5 reanalysis)"
    }