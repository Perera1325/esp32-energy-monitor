"""
generate_synthetic_dataset.py

Generates a SYNTHETIC, DOCUMENTED training dataset for the fault-diagnosis-
and-recommendation model discussed in Chapter 6 of the final report.

WHY SYNTHETIC DATA:
The soldered hardware board has not yet been continuity-tested, powered up,
or run through a real fault event, so no real fault-labelled sensor history
exists yet (see Project Log, Sheet 12, 11 Sep 2026). Training on synthetic
data lets the model architecture, pipeline, and recommendation logic be
built and demonstrated now. It MUST be clearly labelled in the report as a
proof-of-concept pending validation against real fault events collected
from the physical hardware -- the numbers this produces describe how well
the model learns the assumptions below, not how well it will perform on
real faults.

GENERATION LOGIC (documented so it can be defended to an examiner):
Each sample represents one 5-minute monitoring window (150 readings at the
system's real 2-second sample interval -- see Section 3.1 of the report).
Instead of storing all 150 raw readings, each window is summarised into 9
engineered features per sensor stream (mean, standard deviation, and linear
trend/slope across the window) plus the fraction of the window during which
occupancy was detected. This mirrors what would realistically be computed
on the ESP32/Firebase side without needing to ship raw time-series data.

Six classes are used, chosen because they are distinguishable using the
engineered features above and map onto physically meaningful fault
mechanisms relevant to the pump/motor and lighting loads this system
targets. Class boundaries are deliberately generated with overlapping noise
(not cleanly separable) to avoid producing an artificially perfect,
unrealistic dataset.

    0 NORMAL                  - stable current/voltage/temperature, no fault
    1 ENERGY_WASTE             - current above idle threshold, room unoccupied
                                  (matches the existing rule engine's WASTE case)
    2 BEARING_WEAR             - slow upward drift in current AND temperature,
                                  voltage stable (progressive mechanical wear)
    3 OVERLOAD_BLOCKAGE        - sudden step-up in current and rapid temperature
                                  rise (obstruction / excess mechanical load)
    4 SUPPLY_VOLTAGE_FAULT     - voltage drifts outside the 200-240V band,
                                  current largely unaffected (matches the
                                  existing rule engine's SUPPLY FAULT case)
    5 INTERMITTENT_CONNECTION  - elevated noise (std) on both current and
                                  voltage with normal means (loose wiring/
                                  poor contact, not a clean threshold event)

Usage:
    python generate_synthetic_dataset.py --n-per-class 400 --out dataset.csv
"""

import argparse
import numpy as np
import pandas as pd

RNG_SEED = 42
IDLE_CURRENT_A = 0.15      # matches Section 3.1 WASTE threshold
TEMP_FAULT_C = 45.0        # matches Section 3.1 MAINTENANCE threshold
VOLTAGE_LOW = 200.0        # matches Section 3.1 SUPPLY FAULT band
VOLTAGE_HIGH = 240.0

CLASS_NAMES = [
    "NORMAL",
    "ENERGY_WASTE",
    "BEARING_WEAR",
    "OVERLOAD_BLOCKAGE",
    "SUPPLY_VOLTAGE_FAULT",
    "INTERMITTENT_CONNECTION",
]

WINDOW_SAMPLES = 150  # 5 minutes at a 2-second sample interval


def _window_stats(series):
    """Return (mean, std, slope) for a 1D array using simple linear fit for slope."""
    x = np.arange(len(series))
    mean = float(np.mean(series))
    std = float(np.std(series))
    slope = float(np.polyfit(x, series, 1)[0]) if len(series) > 1 else 0.0
    return mean, std, slope


def _make_window(rng, current_base, current_drift, current_noise,
                  voltage_base, voltage_drift, voltage_noise,
                  temp_base, temp_drift, temp_noise,
                  occupancy_prob):
    t = np.arange(WINDOW_SAMPLES)
    current = current_base + current_drift * (t / WINDOW_SAMPLES) + rng.normal(0, current_noise, WINDOW_SAMPLES)
    voltage = voltage_base + voltage_drift * (t / WINDOW_SAMPLES) + rng.normal(0, voltage_noise, WINDOW_SAMPLES)
    temp = temp_base + temp_drift * (t / WINDOW_SAMPLES) + rng.normal(0, temp_noise, WINDOW_SAMPLES)
    occupancy = rng.random(WINDOW_SAMPLES) < occupancy_prob

    current = np.clip(current, 0, None)
    voltage = np.clip(voltage, 0, None)

    c_mean, c_std, c_slope = _window_stats(current)
    v_mean, v_std, v_slope = _window_stats(voltage)
    t_mean, t_std, t_slope = _window_stats(temp)
    occ_frac = float(np.mean(occupancy))

    return {
        "current_mean": c_mean, "current_std": c_std, "current_slope": c_slope,
        "voltage_mean": v_mean, "voltage_std": v_std, "voltage_slope": v_slope,
        "temp_mean": t_mean, "temp_std": t_std, "temp_slope": t_slope,
        "occupancy_fraction": occ_frac,
    }


def generate_class_samples(rng, label_idx, n):
    rows = []
    for _ in range(n):
        if label_idx == 0:  # NORMAL
            row = _make_window(rng, 0.35, 0.0, 0.03, 225, 0.0, 2.0, 30, 0.0, 0.5, occupancy_prob=0.6)
        elif label_idx == 1:  # ENERGY_WASTE
            row = _make_window(rng, 0.45, 0.0, 0.04, 225, 0.0, 2.0, 30, 0.0, 0.5, occupancy_prob=0.03)
        elif label_idx == 2:  # BEARING_WEAR
            row = _make_window(rng, 0.35, rng.uniform(0.15, 0.35), 0.03, 225, 0.0, 2.0,
                                30, rng.uniform(6, 12), 0.6, occupancy_prob=0.6)
        elif label_idx == 3:  # OVERLOAD_BLOCKAGE
            row = _make_window(rng, 0.9, rng.uniform(0.4, 0.8), 0.08, 224, 0.0, 2.5,
                                33, rng.uniform(12, 20), 1.0, occupancy_prob=0.6)
        elif label_idx == 4:  # SUPPLY_VOLTAGE_FAULT
            direction = rng.choice([-1, 1])
            row = _make_window(rng, 0.35, 0.0, 0.03,
                                225 + direction * rng.uniform(30, 50), 0.0, 3.0,
                                30, 0.0, 0.5, occupancy_prob=0.5)
        elif label_idx == 5:  # INTERMITTENT_CONNECTION
            row = _make_window(rng, 0.35, 0.0, 0.18, 225, 0.0, 9.0, 30, 0.0, 0.5, occupancy_prob=0.5)
        else:
            raise ValueError(label_idx)
        row["label"] = label_idx
        row["label_name"] = CLASS_NAMES[label_idx]
        rows.append(row)
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-per-class", type=int, default=400,
                         help="number of synthetic windows to generate per fault class")
    parser.add_argument("--out", type=str, default="dataset.csv")
    parser.add_argument("--seed", type=int, default=RNG_SEED)
    args = parser.parse_args()

    rng = np.random.default_rng(args.seed)

    all_rows = []
    for label_idx in range(len(CLASS_NAMES)):
        all_rows.extend(generate_class_samples(rng, label_idx, args.n_per_class))

    df = pd.DataFrame(all_rows)
    df = df.sample(frac=1.0, random_state=args.seed).reset_index(drop=True)  # shuffle
    df.to_csv(args.out, index=False)
    print(f"Wrote {len(df)} synthetic windows ({args.n_per_class} per class, "
          f"{len(CLASS_NAMES)} classes) to {args.out}")
    print(df["label_name"].value_counts())


if __name__ == "__main__":
    main()
