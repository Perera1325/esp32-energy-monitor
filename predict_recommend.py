"""
predict_recommend.py

Loads the trained fault-diagnosis model and turns a predicted fault class
into a specific, actionable maintenance recommendation -- this is the
"recommendation" half of the feature discussed in Chapter 6 of the report
(the rule engine already raises a generic MAINTENANCE alert; this module
is what would go a step further and suggest a likely cause and action).

This module is deliberately kept separate from the existing rule engine
(Section 3.1) rather than replacing it: the rule engine continues to make
the fast, transparent, threshold-based WASTE / MAINTENANCE / SUPPLY FAULT
call in real time; this ML layer only activates to add diagnostic detail
once a MAINTENANCE-type condition has already been flagged, computed from
the same 5-minute feature window described in generate_synthetic_dataset.py.

Usage (after running generate_synthetic_dataset.py and train_fault_model.py):
    python predict_recommend.py --model fault_model.joblib
"""

import argparse
import joblib
import numpy as np
import pandas as pd

RECOMMENDATIONS = {
    "NORMAL": (
        "No fault indicated. Continue routine monitoring."
    ),
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


def build_feature_row(current_mean, current_std, current_slope,
                       voltage_mean, voltage_std, voltage_slope,
                       temp_mean, temp_std, temp_slope,
                       occupancy_fraction):
    return pd.DataFrame([{
        "current_mean": current_mean, "current_std": current_std, "current_slope": current_slope,
        "voltage_mean": voltage_mean, "voltage_std": voltage_std, "voltage_slope": voltage_slope,
        "temp_mean": temp_mean, "temp_std": temp_std, "temp_slope": temp_slope,
        "occupancy_fraction": occupancy_fraction,
    }])


def diagnose(model_bundle, feature_row):
    model = model_bundle["model"]
    features = model_bundle["features"]
    pred = model.predict(feature_row[features])[0]
    proba = model.predict_proba(feature_row[features])[0]
    confidence = float(np.max(proba))
    return pred, confidence, RECOMMENDATIONS[pred]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, default="fault_model.joblib")
    args = parser.parse_args()

    bundle = joblib.load(args.model)

    # Three illustrative example windows -- NOT real sensor data, just
    # demonstrating the interface. Replace with real windows computed from
    # logged Firebase readings once the hardware has been tested.
    examples = {
        "example_normal": build_feature_row(0.35, 0.03, 0.0, 225, 2.0, 0.0, 30, 0.5, 0.0, 0.6),
        "example_bearing_wear": build_feature_row(0.40, 0.03, 0.25, 224, 2.0, 0.0, 33, 0.6, 9.0, 0.6),
        "example_overload": build_feature_row(1.1, 0.08, 0.6, 224, 2.5, 0.0, 36, 1.0, 15.0, 0.6),
    }

    for name, row in examples.items():
        pred, confidence, recommendation = diagnose(bundle, row)
        print(f"\n[{name}]")
        print(f"  Predicted class : {pred}  (confidence {confidence:.2f})")
        print(f"  Recommendation  : {recommendation}")


if __name__ == "__main__":
    main()
