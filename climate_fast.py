import requests
import pandas as pd
from datetime import datetime

def get_fast_climate(lat, lon):

    # ✅ always use latest available date
    end_date = datetime.today().strftime('%Y-%m-%d')

    url = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date=1995-01-01&end_date={end_date}&daily=temperature_2m_mean,temperature_2m_max,temperature_2m_min,precipitation_sum,soil_moisture_0_to_7cm&timezone=auto"

    response = requests.get(url)
    data = response.json()

    # safety check
    if "daily" not in data:
        return {"error": "No data returned"}

    df = pd.DataFrame(data["daily"])
    df["time"] = pd.to_datetime(df["time"])
    df["year"] = df["time"].dt.year

    # -----------------------
    # BASIC TRENDS
    # -----------------------
    temp_mean = df.groupby("year")["temperature_2m_mean"].mean()
    temp_max = df.groupby("year")["temperature_2m_max"].mean()
    rain = df.groupby("year")["precipitation_sum"].sum()
    soil_moist = df.groupby("year")["soil_moisture_0_to_7cm"].mean()

    # -----------------------
    # DERIVED VARIABLES
    # -----------------------

    # ❄️ frost days (min temp < 0°C)
    df["frost_day"] = df["temperature_2m_min"] < 0
    frost_days = df.groupby("year")["frost_day"].sum()

    # 🧊 freezing days (max temp < 0°C → entire day freezing)
    df["freezing_day"] = df["temperature_2m_max"] < 0
    freezing_days = df.groupby("year")["freezing_day"].sum()

    # 🔥 heat extreme proxy (very useful)
    df["hot_day"] = df["temperature_2m_max"] > 35
    hot_days = df.groupby("year")["hot_day"].sum()

    return {
        "temperature_mean": temp_mean.to_dict(),
        "temperature_max": temp_max.to_dict(),
        "rainfall": rain.to_dict(),
        "soil_moisture": soil_moist.to_dict(),
        "frost_days": frost_days.to_dict(),
        "freezing_days": freezing_days.to_dict(),
        "hot_days": hot_days.to_dict(),
        "source": "Open-Meteo reanalysis",
        "last_updated": end_date
    }