import requests
import pandas as pd
import numpy as np
from datetime import datetime
from scipy.stats import gamma, norm


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
    # Rainfall threshold (ONLY R95p)
    # -----------------------------
    r95 = np.percentile(
        baseline["precipitation_sum"].dropna(),
        95
    )

    # -----------------------------
    # SPI (Gamma-based, robust)
    # -----------------------------
    annual_rain = (
        baseline
        .groupby("year")["precipitation_sum"]
        .sum()
        .dropna()
    )

    shape, loc, scale = gamma.fit(annual_rain, floc=0)

    cdf = gamma.cdf(annual_rain, shape, loc=loc, scale=scale)

    # avoid infinities
    cdf = np.clip(cdf, 1e-6, 1 - 1e-6)

    spi_values = norm.ppf(cdf)

    spi_dict = dict(zip(annual_rain.index, spi_values))

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

        spi = spi_dict.get(year, np.nan)

        # R95p ONLY (clean ETCCDI index)
        r95p = g.loc[
            g["precipitation_sum"] > r95,
            "precipitation_sum"
        ].sum()

        # ===== CLOUD REGIME =====
        cloud_cover_mean = g["cloud_cover_mean"].mean()

        cloud_variability = g["cloud_cover_mean"].dropna().std()

        # ===== SOLAR RADIATION =====
        ssrd_annual = g["shortwave_radiation_sum"].sum()

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
                "r95p": float(r95p)
            },

            "cloud_radiation": {
                "cloud_cover_mean": (
                    float(cloud_cover_mean)
                    if pd.notna(cloud_cover_mean)
                    else None
                ),

                "cloud_variability": (
                    float(cloud_variability)
                    if pd.notna(cloud_variability)
                    else None
                ),

                "ssrd_annual": (
                    float(ssrd_annual)
                    if pd.notna(ssrd_annual)
                    else None
                )
            }
        })

    return {
        "data": results,
        "baseline": "1980-2024",
        "period": f"1980-{current_year-1}",
        "mode": "scientific (R95p + SPI + cloud variability)",
        "source": "Open-Meteo ERA5 Reanalysis"
    }