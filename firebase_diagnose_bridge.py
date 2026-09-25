"""
firebase_diagnose_bridge.py

The missing link between your trained fault-diagnosis model and your live
dashboard. Run this manually (or via Windows Task Scheduler) whenever you
want a fresh diagnosis:

    python firebase_diagnose_bridge.py

What it does, in order:
  1. Pulls the last N minutes of readings from your Firebase Realtime
     Database's /history node (written by the firmware's new
     pushHistoryToFirebase() function).
  2. Computes the same 10 engineered features the model was trained on
     (mean/std/slope of current, voltage, temperature + occupancy fraction).
  3. Loads your already-trained fault_model.joblib and runs a real
     prediction on that real feature window.
  4. Writes the result to /diagnosis in Firebase, which your dashboard
     (dashboard/index.html) can then display.

REQUIREMENTS BEFORE THIS WILL PRODUCE ANYTHING MEANINGFUL:
  - Your firmware must be running the updated sketch (the one with
    pushHistoryToFirebase() added) for at least WINDOW_MINUTES minutes,
    so there is actually a window of /history data to read.
  - fault_model.joblib must already exist in this folder (produced by
    running train_fault_model.py once).

This talks to Firebase over its plain REST API (no Admin SDK needed),
which works because your database rules are currently open
(.read/.write: true, test mode). If you tighten your rules later, this
script's requests will need an auth token added.

Usage:
    pip install requests joblib numpy pandas
    python firebase_diagnose_bridge.py
    python firebase_diagnose_bridge.py --window-minutes 10   (optional)
"""

import argparse
import sys
import time

import numpy as np
import pandas as pd
import requests
import joblib

# ============================================================
#  YOUR FIREBASE DATABASE URL -- confirmed earlier in this
#  project against the console. No trailing slash.
# ============================================================
DATABASE_URL = "https://esp32-energy-monitor-9d94d-default-rtdb.asia-southeast1.firebasedatabase.app"

FEATURE_COLUMNS = [
    "current_mean", "current_std", "current_slope",
    "voltage_mean", "voltage_std", "voltage_slope",
    "temp_mean", "temp_std", "temp_slope",
    "occupancy_fraction",
]

RECOMMENDATIONS = {
    "NORMAL": "No fault indicated. Continue routine monitoring.",
    "ENERGY_WASTE": (
        "Load is drawing current with no occupancy detected. Verify the load "
        "was not left switched on unintentionally; no mechanical fault indicated."
    ),
    "BEARING_WEAR": (
        "Gradual, correlated rise in current and temperature at stable voltage is "
        "consistent with developing mechanical wear (e.g. bearing friction). "
        "Recommend a physical inspection and lubrication/bearing check before the "
        "trend worsens."
    ),
    "OVERLOAD_BLOCKAGE": (
        "Sudden increase in current alongside a rapid temperature rise is "
        "consistent with a mechanical obstruction or excessive load (e.g. a "
        "blocked pump inlet). Recommend an immediate inspection for blockage "
        "and, if found, an immediate load-side shutdown to prevent damage."
    ),
    "SUPPLY_VOLTAGE_FAULT": (
        "Voltage has drifted outside the normal 200-240V supply band while "
        "current remains largely unaffected, indicating a supply-side issue "
        "rather than a fault in the monitored load. Recommend checking the "
        "incoming mains supply and wiring connections rather than the "
        "equipment itself."
    ),
    "INTERMITTENT_CONNECTION": (
        "Elevated noise/variance on both current and voltage readings, with "
        "normal average values, is consistent with a loose or degraded "
        "electrical connection rather than a load-side fault. Recommend "
        "checking terminal connections and wiring integrity."
    ),
}


def fetch_recent_history(window_minutes: float) -> pd.DataFrame:
    """Pull /history entries from the last `window_minutes` via REST."""
    cutoff_ms = int((time.time() - window_minutes * 60) * 1000)

    url = f"{DATABASE_URL}/history.json"
    params = {
        "orderBy": '"timestamp"',
        "startAt": cutoff_ms,
    }

    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    if not data:
        return pd.DataFrame(columns=["current", "voltage", "temperature", "occupied", "timestamp"])

    rows = list(data.values())
    return pd.DataFrame(rows)


def compute_slope(values: np.ndarray) -> float:
    """Linear trend (slope) across the window -- same method used in
    generate_synthetic_dataset.py, so the model sees consistent features."""
    if len(values) < 2:
        return 0.0
    x = np.arange(len(values))
    slope, _ = np.polyfit(x, values, 1)
    return float(slope)


def build_feature_row(df: pd.DataFrame) -> pd.DataFrame:
    current = df["current"].to_numpy(dtype=float)
    voltage = df["voltage"].to_numpy(dtype=float)
    temp = df["temperature"].to_numpy(dtype=float)
    occupied = df["occupied"].astype(bool).to_numpy()

    row = {
        "current_mean": float(np.mean(current)),
        "current_std": float(np.std(current)),
        "current_slope": compute_slope(current),
        "voltage_mean": float(np.mean(voltage)),
        "voltage_std": float(np.std(voltage)),
        "voltage_slope": compute_slope(voltage),
        "temp_mean": float(np.mean(temp)),
        "temp_std": float(np.std(temp)),
        "temp_slope": compute_slope(temp),
        "occupancy_fraction": float(np.mean(occupied)),
    }
    return pd.DataFrame([row])


def push_diagnosis(predicted_class: str, confidence: float, recommendation: str, n_samples: int):
    payload = {
        "class": predicted_class,
        "confidence": round(confidence, 3),
        "recommendation": recommendation,
        "window_samples": n_samples,
        "computed_at": {".sv": "timestamp"},
    }
    url = f"{DATABASE_URL}/diagnosis.json"
    resp = requests.put(url, json=payload, timeout=15)
    resp.raise_for_status()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, default="fault_model.joblib")
    parser.add_argument("--window-minutes", type=float, default=5.0)
    args = parser.parse_args()

    print(f"Fetching last {args.window_minutes} minute(s) of /history from Firebase...")
    df = fetch_recent_history(args.window_minutes)

    if len(df) < 5:
        print(
            f"Only found {len(df)} history sample(s) in that window -- need at least a "
            "few samples for a meaningful window. Make sure the updated firmware "
            "(with pushHistoryToFirebase) has been running for a while, then try again."
        )
        sys.exit(1)

    print(f"Found {len(df)} samples. Computing feature window...")
    feature_row = build_feature_row(df)
    print(feature_row.to_string(index=False))

    print(f"Loading model from {args.model}...")
    bundle = joblib.load(args.model)
    model = bundle["model"]
    features = bundle["features"]

    pred = model.predict(feature_row[features])[0]
    proba = model.predict_proba(feature_row[features])[0]
    confidence = float(np.max(proba))
    recommendation = RECOMMENDATIONS[pred]

    print()
    print(f"Predicted class : {pred}  (confidence {confidence:.2f})")
    print(f"Recommendation  : {recommendation}")

    print()
    print("Writing result to /diagnosis in Firebase...")
    push_diagnosis(pred, confidence, recommendation, len(df))
    print("Done. Refresh your dashboard to see it.")


if __name__ == "__main__":
    main()
