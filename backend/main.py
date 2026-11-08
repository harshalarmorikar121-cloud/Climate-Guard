
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import httpx

app = FastAPI(title="ClimateGuard AI Backend")

# Allow the frontend to communicate with the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {
        "message": "ClimateGuard AI Backend is running",
        "status": "success"
    }


@app.get("/api/weather")
async def get_weather(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180)
):
    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "precipitation,"
            "wind_speed_10m"
        )
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        return {
            "status": "success",
            "location": {
                "latitude": latitude,
                "longitude": longitude
            },
            "weather": data.get("current", {}),
            "source": "Open-Meteo"
        }

    except httpx.HTTPError as exc:
        print(f"Weather API Error: {type(exc).__name__}: {exc}")

        return {
            "status": "error",
            "message": "Unable to fetch weather data",
            "error_type": type(exc).__name__,
            "details": str(exc)
        }
