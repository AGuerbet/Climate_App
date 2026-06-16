import requests
import pandas as pd
import numpy as np
from datetime import datetime


def get_fast_climate(lat, lon):

    end_date = datetime.today().strftime('%Y-%m-%d')

    url = (
        f"https://archive-api.open-meteo.com/v1/archive?"
        f"latitude={lat}"
        f"&longitude={lon}"
        f"&start_date=1980-01-01"
        f"&end_date={end_date}"
        f"&daily="
        f"temperature_2m_mean,"
        f"temperature_2m_max,"
        f"temperature_2m_min,"
        f"precipitation_sum,"
        f"cloud_cover_mean,"
        f"shortwave_radiation_sum"
        f"&timezone=auto"
    )

    response = requests.get(url)

    if response.status_code != 200:
        return {
            "error": f"API request failed ({response.status_code})",
            "details": response.text
        }

    data = response.json()

    if "daily" not in data or data["daily"] is None:
        return {"error": "No data returned"}

    df = pd.DataFrame(data["daily"])

    df["time"] = pd.to_datetime(df["time"])
    df["year"] = df["time"].dt.year

    # Remove current incomplete year
    current_year = datetime.today().year
    df = df[df["year"] < current_year]

    # -----------------------------
    # Baseline (1980–2024)
    # -----------------------------
    baseline = df[
        (df["year"] >= 1980) &
        (df["year"] <= 2024)
    ]

    if len(baseline) == 0:
        return {"error": "Baseline period contains no data"}

    # -----------------------------
    # Temperature thresholds
    # -----------------------------
    tx90 = np.percentile(
        baseline["temperature_2m_max"].dropna(),
        90
    )

    tn10 = np.percentile(
        baseline["temperature_2m_min"].dropna(),
        10
    )

    # -----------------------------
    # Rainfall thresholds
    # -----------------------------
    r95 = np.percentile(
        baseline["precipitation_sum"].dropna(),
        95
    )

    r99 = np.percentile(
        baseline["precipitation_sum"].dropna(),
        99
    )

    # -----------------------------
    # SPI baseline
    # -----------------------------
    annual_rain = (
        baseline
        .groupby("year")["precipitation_sum"]
        .sum()
    )

    rain_mean = annual_rain.mean()
    rain_std = annual_rain.std()

    results = []

    # -----------------------------
    # Annual calculations
    # -----------------------------
    for year, g in df.groupby("year"):

        # ===== TEMPERATURE =====

        mean_temp = g["temperature_2m_mean"].mean()

        tx90p = (
            g["temperature_2m_max"] > tx90
        ).mean() * 100

        tn10p = (
            g["temperature_2m_min"] < tn10
        ).mean() * 100

        # ===== RAINFALL =====

        rain_total = g["precipitation_sum"].sum()

        spi = (
            (rain_total - rain_mean) / rain_std
            if rain_std != 0
            else 0
        )

        r95p = g.loc[
            g["precipitation_sum"] > r95,
            "precipitation_sum"
        ].sum()

        r99p = g.loc[
            g["precipitation_sum"] > r99,
            "precipitation_sum"
        ].sum()

        # ===== CLOUD COVER =====

        cloud_cover_mean = (
            g["cloud_cover_mean"].mean()
            if "cloud_cover_mean" in g.columns
            else np.nan
        )

        # ===== SOLAR RADIATION =====

        ssrd_annual = (
            g["shortwave_radiation_sum"].sum()
            if "shortwave_radiation_sum" in g.columns
            else np.nan
        )

        ssrd_daily_mean = (
            g["shortwave_radiation_sum"].mean()
            if "shortwave_radiation_sum" in g.columns
            else np.nan
        )

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
            },

            "cloud_radiation": {
                "cloud_cover_mean": (
                    float(cloud_cover_mean)
                    if pd.notna(cloud_cover_mean)
                    else None
                ),

                "ssrd_annual": (
                    float(ssrd_annual)
                    if pd.notna(ssrd_annual)
                    else None
                ),

                "ssrd_daily_mean": (
                    float(ssrd_daily_mean)
                    if pd.notna(ssrd_daily_mean)
                    else None
                )
            }
        })

    return {
        "data": results,
        "baseline": "1980-2024",
        "period": f"1980-{current_year-1}",
        "mode": "scientific (complete years only)",
        "source": "Open-Meteo ERA5 Reanalysis"
    }