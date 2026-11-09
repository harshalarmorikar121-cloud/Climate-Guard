
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pathlib import Path
import pandas as pd
import httpx
import joblib

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

# Load the trained dengue model
MODEL_PATH = (
    Path(__file__).resolve().parent
    / "models"
    / "climateguard_dengue_model.pkl"
)

model = None
model_error = None

try:
    model = joblib.load(MODEL_PATH)
    print("Dengue model loaded successfully!")

except Exception as exc:
    model_error = str(exc)
    print("Dengue model loading failed:", model_error)


# District names used during model training
VALID_DISTRICTS = {
    "Nandurbar", "Dhule", "Jalgaon", "Buldhana",
    "Akola", "Washim", "Amravati", "Wardha",
    "Nagpur", "Bhandara", "Gondia", "Gadchiroli",
    "Chandrapur", "Yeotmal", "Nanded", "Hingoli",
    "Parbhani", "Jalna", "Aurangabad", "Nashik",
    "Thane", "Palghar", "Raigad", "Pune",
    "Ahmednagar", "Beed", "Latur", "Osmanabad",
    "Solapur", "Satara", "Ratnagiri", "Sindhudurg",
    "Kolhapur", "Sangli"
}


# Input format for dengue prediction
class DenguePredictionInput(BaseModel):
    district: str = Field(min_length=2)
    year: int = Field(ge=2021, le=2100)
    temperature: float = Field(ge=-10, le=60)
    humidity: float = Field(ge=0, le=100)
    rainfall: float = Field(ge=0, le=10000)
    previous_year_rate: float = Field(ge=0)


@app.get("/")
def home():
    return {
        "message": "ClimateGuard AI Backend is running",
        "status": "success"
    }


# Existing weather API - preserved
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


# Check whether the dengue model is loaded
@app.get("/api/model-status")
def model_status():
    return {
        "status": "success" if model is not None else "error",
        "model_loaded": model is not None,
        "message": (
            "Dengue model is ready"
            if model is not None
            else "Dengue model could not be loaded"
        )
    }


# New dengue prediction API
@app.post("/api/predict/dengue")
def predict_dengue(data: DenguePredictionInput):

    if model is None:
        raise HTTPException(
            status_code=503,
            detail="Dengue prediction model is not available"
        )

    district = data.district.strip()

    if district not in VALID_DISTRICTS:
        raise HTTPException(
            status_code=400,
            detail="District name does not match the model dataset"
        )

    input_data = pd.DataFrame([{
        "District": district,
        "Year": data.year,
        "Average_Temperature": data.temperature,
        "Average_Humidity": data.humidity,
        "Total_Rainfall": data.rainfall,
        "Previous_Year_Rate": data.previous_year_rate
    }])

    prediction = float(model.predict(input_data)[0])

    prediction = max(0, prediction)

    return {
        "status": "success",
        "district": district,
        "year": data.year,
        "predicted_dengue_rate": round(prediction, 2),
        "unit": "cases per 100,000 using 2011 population",
        "model": "Population-Adjusted Random Forest",
        "disclaimer": (
            "Experimental model estimate, not an official "
            "dengue outbreak warning."
        )
    }
