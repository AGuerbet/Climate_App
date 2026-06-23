import requests
import pandas as pd
import numpy as np
from datetime import datetime
from scipy.stats import gamma, norm


def get_fast_climate(lat, lon):

    current_year = datetime.today().year
    end_date = f"{current_year-1}-12-31"

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

    try:
        response = requests.get(url, timeout=120)

    except Exception as e:
        return {
            "error": "Connection error",
            "details": str(e)
        }

    if response.status_code != 200:

        print("OPEN-METEO ERROR")
        print(response.status_code)
        print(response.text)

        return {
            "error": f"API request failed ({response.status_code})",
            "details": response.text
        }

    try:
        data = response.json()

    except Exception as e:
        return {
            "error": "Invalid JSON response",
            "details": str(e)
        }

    if "daily" not in data:
        return {
            "error": "No daily data returned",
            "details": data
        }

    df = pd.DataFrame(data["daily"])

    if len(df) == 0:
        return {"error": "Empty dataframe"}

    df["time"] = pd.to_datetime(df["time"])
    df["year"] = df["time"].dt.year

    required_columns = [
        "temperature_2m_mean",
        "temperature_2m_max",
        "temperature_2m_min",
        "precipitation_sum",
        "cloud_cover_mean",
        "shortwave_radiation_sum"
    ]

    for col in required_columns:
        if col not in df.columns:
            df[col] = np.nan

    baseline = df[
        (df["year"] >= 1980) &
        (df["year"] <= current_year - 1)
    ]

    if len(baseline) == 0:
        return {"error": "Baseline contains no data"}

    tx90 = np.percentile(
        baseline["temperature_2m_max"].dropna(),
        90
    )

    tn10 = np.percentile(
        baseline["temperature_2m_min"].dropna(),
        10
    )

    r95 = np.percentile(
        baseline["precipitation_sum"].dropna(),
        95
    )

    annual_rain = (
        baseline
        .groupby("year")["precipitation_sum"]
        .sum()
        .dropna()
    )

    spi_dict = {}

    try:

        shape, loc, scale = gamma.fit(
            annual_rain,
            floc=0
        )

        cdf = gamma.cdf(
            annual_rain,
            shape,
            loc=loc,
            scale=scale
        )

        cdf = np.clip(
            cdf,
            1e-6,
            1 - 1e-6
        )

        spi_values = norm.ppf(cdf)

        spi_dict = dict(
            zip(
                annual_rain.index,
                spi_values
            )
        )

    except Exception as e:

        print("SPI ERROR")
        print(str(e))

    results = []

    for year, g in df.groupby("year"):

        mean_temp = g["temperature_2m_mean"].mean()

        tx90p = (
            g["temperature_2m_max"] > tx90
        ).mean() * 100

        tn10p = (
            g["temperature_2m_min"] < tn10
        ).mean() * 100

        rain_total = g["precipitation_sum"].sum()

        spi = spi_dict.get(year, np.nan)

        r95p = g.loc[
            g["precipitation_sum"] > r95,
            "precipitation_sum"
        ].sum()

        cloud_cover_mean = g["cloud_cover_mean"].mean()

        cloud_variability = (
            g["cloud_cover_mean"]
            .dropna()
            .std()
        )

        ssrd_annual = (
            g["shortwave_radiation_sum"]
            .sum()
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
                "spi": (
                    float(spi)
                    if not np.isnan(spi)
                    else None
                ),
                "r95p": float(r95p)
            },

            "cloud_radiation": {

                "cloud_cover_mean":
                    float(cloud_cover_mean)
                    if pd.notna(cloud_cover_mean)
                    else None,

                "cloud_variability":
                    float(cloud_variability)
                    if pd.notna(cloud_variability)
                    else None,

                "ssrd_annual":
                    float(ssrd_annual)
                    if pd.notna(ssrd_annual)
                    else None
            }
        })

    return {
        "data": results,
        "baseline": f"1980-{current_year-1}",
        "period": f"1980-{current_year-1}",
        "mode": "scientific",
        "source": "Open-Meteo ERA5"
    }