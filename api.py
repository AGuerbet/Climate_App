from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from climate import get_fast_climate

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
    return {"message": "Climate API is running"}

@app.get("/climate-fast")
def climate_fast(lat: float, lon: float):
    return get_fast_climate(lat, lon)