import requests
import pandas as pd

def get_fast_climate(lat, lon):

    url = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date=1995-01-01&end_date=2024-12-31&daily=temperature_2m_mean,precipitation_sum&timezone=auto"

    response = requests.get(url)
    data = response.json()

    df = pd.DataFrame(data["daily"])
    df["time"] = pd.to_datetime(df["time"])
    df["year"] = df["time"].dt.year

    temp_trend = df.groupby("year")["temperature_2m_mean"].mean()
    rain_trend = df.groupby("year")["precipitation_sum"].sum()

    return {
        "temperature_trend": temp_trend.to_dict(),
        "rainfall_trend": rain_trend.to_dict(),
        "source": "Open-Meteo reanalysis"
    }