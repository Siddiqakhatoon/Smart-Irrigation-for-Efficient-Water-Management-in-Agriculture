"""
generate_dataset.py
--------------------
Generates a synthetic CSV dataset inspired by 2025 Telangana, India climate conditions.
Covers three major crops: Rice, Wheat, Cotton.

Future Scope:
- Replace with real sensor data
- Connect to weather API (e.g., OpenWeatherMap) for live conditions
"""

import pandas as pd
import numpy as np
import os

def generate_irrigation_dataset(n_samples=500, output_path="irrigation_data.csv"):
    """
    Generates a realistic synthetic dataset for smart irrigation.
    """
    np.random.seed(42)

    crop_types = ["Rice", "Wheat", "Cotton"]
    crops = np.random.choice(crop_types, size=n_samples, p=[0.4, 0.3, 0.3])

    temperature = np.round(np.random.uniform(20, 45, n_samples), 1)
    humidity = np.round(np.random.uniform(20, 95, n_samples), 1)

    rain_prob = (humidity / 100) * 0.6
    rain = np.where(np.random.rand(n_samples) < rain_prob, "Yes", "No")

    base_moisture = np.random.uniform(20, 80, n_samples)
    rain_boost = np.where(rain == "Yes", np.random.uniform(10, 25, n_samples), 0)
    soil_moisture = np.clip(base_moisture + rain_boost, 0, 100).round(1)

    irrigation_needed = []
    for i in range(n_samples):
        crop = crops[i]
        sm = soil_moisture[i]
        temp = temperature[i]
        hum = humidity[i]
        rained = rain[i] == "Yes"

        if rained and sm > 55:
            needed = "No"
        elif crop == "Rice":
            needed = "Yes" if sm < 65 or hum < 60 else "No"
        elif crop == "Wheat":
            needed = "Yes" if sm < 45 or temp > 38 else "No"
        elif crop == "Cotton":
            needed = "Yes" if sm < 40 and not rained else "No"
        else:
            needed = "No"

        irrigation_needed.append(needed)

    df = pd.DataFrame({
        "Temperature": temperature,
        "Humidity": humidity,
        "Rain": rain,
        "Soil_Moisture": soil_moisture,
        "Crop_Type": crops,
        "Irrigation_Needed": irrigation_needed
    })

    df.to_csv(output_path, index=False)
    print(f"[OK] Dataset generated: {output_path} ({n_samples} rows)")
    return df


if __name__ == "__main__":
    df = generate_irrigation_dataset(n_samples=600, output_path="irrigation_data.csv")
    print(df.head(10))
    print("\nClass distribution:")
    print(df["Irrigation_Needed"].value_counts())
