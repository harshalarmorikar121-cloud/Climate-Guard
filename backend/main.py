from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import httpx

app = FastAPI(title="ClimateGuard AI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

WEATHER_WORKER_URL = (
    "https://climateguard-weather.samdadesrushti1.workers.dev/api/weather"
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
    params = {
        "latitude": latitude,
        "longitude": longitude
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                WEATHER_WORKER_URL,
                params=params
            )

        if response.status_code != 200:
            try:
                error_data = response.json()
            except ValueError:
                error_data = {}

            print("Weather Worker error:", error_data)

            return {
                "status": "error",
                "message": "Weather service request failed",
                "worker_status": response.status_code,
                "provider_status": error_data.get("provider_status")
            }

        data = response.json()

        if data.get("status") != "success":
            return {
                "status": "error",
                "message": data.get(
                    "message",
                    "Weather data unavailable"
                )
            }

        return {
            "status": "success",
            "location": data.get("location"),
            "weather": data.get("weather"),
            "source": data.get("source")
        }

    except httpx.HTTPError as exc:
        print(
            f"Weather connection error: "
            f"{type(exc).__name__}: {exc}"
        )

        return {
            "status": "error",
            "message": "Unable to connect to weather service",
            "error_type": type(exc).__name__
        }
