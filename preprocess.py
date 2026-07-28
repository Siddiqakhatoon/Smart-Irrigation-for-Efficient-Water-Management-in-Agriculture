"""
preprocess.py
--------------
Handles loading, cleaning, and encoding the irrigation CSV dataset.

Steps:
1. Load CSV (auto-generate if missing)
2. Add Soil_Moisture column if absent
3. Encode categorical columns -> numerical
4. Return feature matrix X and target vector y

Future Scope:
- Add real-time sensor data ingestion (Arduino/Raspberry Pi serial port)
- Integrate OpenWeatherMap API for live temperature/humidity/rain
"""

import pandas as pd
import numpy as np
import os


# Encoding maps (used both in training & prediction)
RAIN_MAP = {"No": 0, "Yes": 1}
CROP_MAP = {"Rice": 0, "Wheat": 1, "Cotton": 2}
IRRIGATION_MAP = {"No": 0, "Yes": 1}
IRRIGATION_INV_MAP = {0: "No", 1: "Yes"}


def load_and_preprocess(csv_path="irrigation_data.csv"):
    """
    Loads the CSV file, cleans it, and returns features and labels.

    Parameters:
        csv_path (str): Path to the irrigation CSV dataset

    Returns:
        X (pd.DataFrame): Feature matrix
        y (pd.Series): Target labels (0 = No irrigation, 1 = Yes)
        df (pd.DataFrame): Full processed DataFrame
    """

    # Auto-generate dataset if not found
    if not os.path.exists(csv_path):
        print("[!] Dataset not found. Auto-generating...")
        from generate_dataset import generate_irrigation_dataset
        generate_irrigation_dataset(n_samples=600, output_path=csv_path)

    print(f"[OK] Loading dataset from: {csv_path}")
    df = pd.read_csv(csv_path)

    # Basic cleaning
    df.dropna(inplace=True)
    df.reset_index(drop=True, inplace=True)

    # Add Soil_Moisture if missing
    if "Soil_Moisture" not in df.columns:
        print("[!] 'Soil_Moisture' column missing. Generating programmatically...")
        np.random.seed(0)
        base = np.random.uniform(20, 80, len(df))
        rain_boost = np.where(df["Rain"] == "Yes", np.random.uniform(10, 25, len(df)), 0)
        df["Soil_Moisture"] = np.clip(base + rain_boost, 0, 100).round(1)

    # Encode categorical columns
    df["Rain_Enc"] = df["Rain"].map(RAIN_MAP).fillna(0).astype(int)
    df["Crop_Enc"] = df["Crop_Type"].map(CROP_MAP).fillna(0).astype(int)
    df["Label"] = df["Irrigation_Needed"].map(IRRIGATION_MAP).fillna(0).astype(int)

    # Feature selection
    features = ["Temperature", "Humidity", "Rain_Enc", "Soil_Moisture", "Crop_Enc"]
    X = df[features]
    y = df["Label"]

    print(f"[OK] Preprocessing complete. Samples: {len(df)}, Features: {features}")
    return X, y, df


def encode_user_input(temperature, humidity, rain, soil_moisture, crop_type):
    """
    Encodes a single user input row for model prediction.

    Parameters:
        temperature (float): Current temperature in C
        humidity (float): Current humidity %
        rain (str): "Yes" or "No"
        soil_moisture (float): Soil moisture 0-100
        crop_type (str): "Rice", "Wheat", or "Cotton"

    Returns:
        list: Encoded feature row
    """
    rain_enc = RAIN_MAP.get(rain.strip().capitalize(), 0)
    crop_enc = CROP_MAP.get(crop_type.strip().capitalize(), 0)
    return [[temperature, humidity, rain_enc, soil_moisture, crop_enc]]
