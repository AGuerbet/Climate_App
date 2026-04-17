import requests
import pandas as pd
from datetime import datetime

def get_fast_climate(lat, lon):

    end_date = datetime.today().strftime('%Y-%m-%d')

    # ---- CORE VARIABLES (ALWAYS WORK) ----
    url_core = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date=1995-01-01&end_date={end_date}&daily=temperature_2m_mean,temperature_2m_max,temperature_2m_min,precipitation_sum&timezone=auto"

    core = requests.get(url_core).json()

    if "daily" not in core or core["daily"] is None:
        return {"error": "Core data unavailable"}

    df = pd.DataFrame(core["daily"])

    # ---- SECONDARY VARIABLES (TRY / OPTIONAL) ----
    url_extra = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date=1995-01-01&end_date={end_date}&daily=relative_humidity_2m,shortwave_radiation_sum&timezone=auto"

    extra = requests.get(url_extra).json()

    if "daily" in extra and extra["daily"] is not None:
        df_extra = pd.DataFrame(extra["daily"])
        df["humidity"] = df_extra.get("relative_humidity_2m", None)
        df["radiation"] = df_extra.get("shortwave_radiation_sum", None)
    else:
        df["humidity"] = None
        df["radiation"] = None

    # ---- TIME ----
    df["time"] = pd.to_datetime(df["time"])
    df["year"] = df["time"].dt.year

    # ---- AGGREGATION ----
    temp_mean = df.groupby("year")["temperature_2m_mean"].mean()
    temp_max = df.groupby("year")["temperature_2m_max"].mean()
    temp_min = df.groupby("year")["temperature_2m_min"].mean()

    rainfall = df.groupby("year")["precipitation_sum"].sum()

    humidity = df.groupby("year")["humidity"].mean()
    radiation = df.groupby("year")["radiation"].sum()

    # ---- EXTREMES ----
    df["hot_day"] = df["temperature_2m_max"] > 35
    hot_days = df.groupby("year")["hot_day"].sum()

    return {
        "temperature_mean": temp_mean.to_dict(),
        "temperature_max": temp_max.to_dict(),
        "temperature_min": temp_min.to_dict(),
        "rainfall": rainfall.to_dict(),
        "humidity": humidity.fillna(0).to_dict(),
        "radiation": radiation.fillna(0).to_dict(),
        "hot_days": hot_days.to_dict(),
        "source": "Open-Meteo (ERA5 reanalysis)",
        "last_updated": end_date
    }