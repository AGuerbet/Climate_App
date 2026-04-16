from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
import pandas as pd

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"status": "Climate API running"}

@app.get("/climate-fast")
def climate_fast(lat: float, lon: float):

    url = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date=1995-01-01&end_date=2024-12-31&daily=temperature_2m_mean,precipitation_sum&timezone=auto"

    data = requests.get(url).json()

    df = pd.DataFrame(data["daily"])
    df["time"] = pd.to_datetime(df["time"])
    df["year"] = df["time"].dt.year

    temp = df.groupby("year")["temperature_2m_mean"].mean()
    rain = df.groupby("year")["precipitation_sum"].sum()

    return {
        "temperature_trend": temp.to_dict(),
        "rainfall_trend": rain.to_dict()
    }