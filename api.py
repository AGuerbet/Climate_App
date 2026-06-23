from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from climate import get_fast_climate

app = FastAPI(
    title="Faultline Echoes Climate API",
    version="1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {
        "status": "online",
        "message": "Climate API running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


@app.get("/climate-fast")
def climate_fast(lat: float, lon: float):

    try:
        return get_fast_climate(lat, lon)

    except Exception as e:

        print("BACKEND ERROR")
        print(str(e))

        return {
            "error": "Internal server error",
            "details": str(e)
        }