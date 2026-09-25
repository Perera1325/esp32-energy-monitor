# Occupancy-Aware IoT Energy Monitoring and Rule-Based Decision Support System

A low-cost ESP32-based energy monitoring system that fuses **electrical**, **thermal**, and **occupancy** sensor data through a rule-based decision engine to detect energy waste, developing equipment faults, and supply-side issues in real time — with a live, remotely accessible web dashboard and an optional machine-learning fault-diagnosis layer.

Developed as a BTEC HND Unit 5001 Research Project, SLT–Mobitel Nebula Institute of Technology.

---

## Overview

Most low-cost energy monitors only look at current draw in isolation, which means they can't tell the difference between a fan legitimately running in an occupied room and the same fan wasting electricity in an empty one. This project addresses that gap by fusing three data streams — current, voltage, temperature, and PIR-based occupancy — into a single rule-based decision engine that classifies system state into one of three categorised alerts:

| Alert | Trigger Condition |
|---|---|
| **WASTE** | Room unoccupied (PIR = no motion) while load current remains above threshold |
| **MAINTENANCE** | Elevated temperature combined with sustained current draw |
| **SUPPLY_FAULT** | Supply voltage outside the normal 200–240V band |
| **NONE** | No alert condition met |

Results are pushed to a Firebase Realtime Database and displayed on a live, Netlify-hosted web dashboard, viewable from any browser without needing to be on the same local network as the device — plus a local OLED display for on-device status.

An additional **machine-learning fault-diagnosis layer** extends this further, using a trained decision-tree classifier to distinguish six operating conditions (NORMAL, ENERGY_WASTE, BEARING_WEAR, OVERLOAD_BLOCKAGE, SUPPLY_VOLTAGE_FAULT, INTERMITTENT_CONNECTION) — including two mechanical-fault categories the rule engine alone cannot detect.

---

## Features

- Real-time current, voltage, temperature and occupancy sensing
- Three-category rule-based alert engine (WASTE / MAINTENANCE / SUPPLY_FAULT)
- Live OLED on-device status display
- Firebase Realtime Database + Netlify-hosted live web dashboard (works from anywhere, not just the local network)
- 4-channel relay output for automated load switching
- Machine-learning fault-diagnosis layer (6-class decision-tree classifier, 100% test-set accuracy)
- Automatic Wi-Fi/Firebase reconnection (~30s recovery from a dropped connection)
- Built entirely from low-cost, widely available hobbyist components (verified final hardware cost: **≈ LKR 5,775**)

---

## Hardware

| Component | Specification | Verified Cost (LKR) |
|---|---|---|
| Microcontroller | ESP32 DevKit V1 | 2,550 |
| Current sensor | ACS712 (20A) | 605 |
| Voltage sensor | ZMPT101B | 450 |
| Temperature sensor | DS18B20 (waterproof probe) | 230 |
| Occupancy sensor | PIR motion sensor (HC-SR501) | 290 |
| Relay module | 4-channel 5V relay | 650 |
| Status display | SSD1306 OLED 128×64 (I2C) | 650 |
| Misc. (wiring, resistors, perfboard) | — | ~350 |
| **Total** | | **≈ 5,775** |

### Pin Mapping

| Function | GPIO |
|---|---|
| ACS712 (current) | 34 (ADC1) |
| ZMPT101B (voltage) | 35 (ADC1) |
| DS18B20 (temperature) | 4 |
| PIR (occupancy) | 13 |
| Relay – Lamp | 25 |
| Relay – Fan | 26 |
| Relay – Pump | 27 |
| Relay – Spare | 14 |
| OLED (I2C) | 21 (SDA) / 22 (SCL) |

> ADC1 pins (34, 35) were deliberately chosen over ADC2 pins, since ADC2 is unreliable on the ESP32 while Wi-Fi is active.

---

## Software Stack

| Layer | Tool |
|---|---|
| Firmware | Arduino IDE 2.3.10 |
| Dashboard (HTML/CSS/JS) | VS Code |
| Cloud database | Firebase Realtime Database |
| Dashboard hosting | Netlify |
| ML pipeline | Python 3.11 (pandas, scikit-learn, joblib) |

---

## Repository Structure

├── firmware/
│ └── main_firmware.ino # Full firmware: sensing, rule engine, OLED, Firebase
├── dashboard/
│ └── index.html # Live web dashboard (Firebase + Netlify)
├── ml_pipeline/
│ ├── generate_synthetic_dataset.py
│ ├── dataset.csv # 2,400 labelled feature windows, 6 fault classes
│ ├── train_fault_model.py
│ ├── fault_model.joblib # Trained decision-tree classifier
│ ├── predict_recommend.py
│ ├── firebase_diagnose_bridge.py
│ └── inject_test_history.py # Synthetic fault-injection testing tool
└── README.md


---

## How the Rule Engine Works

Sensor readings are sampled on a fixed interval and evaluated in priority order:

if (!occupied && current > 0.15A): → WASTE
elif (temp > 45°C && current > 0.15A): → MAINTENANCE
elif (voltage < 200V || voltage > 240V): → SUPPLY_FAULT
else: → NONE


Results are written to `/readings` in Firebase and read live by the dashboard.

---

## Machine Learning Fault-Diagnosis Layer

A decision-tree classifier trained on 2,400 synthetically generated, balanced feature windows (400 per class) achieves **100% accuracy** on a held-out test set across all six fault categories. Ten engineered features are used per window: mean, standard deviation, and slope of current, voltage and temperature, plus occupancy fraction.

temp_slope <= 0.02
├── voltage_std <= 2.50
│ ├── occupancy_fraction <= 0.27 → ENERGY_WASTE
│ └── occupancy_fraction > 0.27 → NORMAL
└── voltage_std > 2.50
├── voltage_std <= 5.51 → SUPPLY_VOLTAGE_FAULT
└── voltage_std > 5.51 → INTERMITTENT_CONNECTION
temp_slope > 0.02
├── current_slope <= 0.00 → BEARING_WEAR
└── current_slope > 0.00 → OVERLOAD_BLOCKAGE


Live inference is handled by `firebase_diagnose_bridge.py`, which pulls a recent window from Firebase, computes features, runs the model, and writes the predicted class, confidence, and a recommendation back to `/diagnosis` for the dashboard's AI Fault Diagnosis panel.

---

## Testing Summary

All test evidence, methodology and full result discussion are documented in Chapter 4 of the accompanying research report. Highlights:
- Voltage sensor calibrated to ~0% mean error against a real 12V AC reference
- Wi-Fi/Firebase reconnection measured at ~30 seconds after a dropped connection
- ML classifier: 100% test-set accuracy across 6 classes (480 test samples)
- Full hardware cost independently verified against live Sri Lankan supplier pricing

---

## Known Issues / Limitations

- Two rule-engine priority-order anomalies under specific test conditions (WASTE occasionally superseded by MAINTENANCE/SUPPLY_FAULT) — under investigation
- Current sensor (ACS712) validated for repeatability only, not against an independent reference instrument
- Firebase `/diagnosis` write-back has intermittently failed with 401 Unauthorized — Firebase security rules need hardening
- Four of six ML fault classes validated only on synthetic data, not yet on live hardware faults

Full defects log with severity ratings available in the research report, Section 4.15.

---

## Future Work

- Migration from perfboard to a fabricated PCB, with a proper protective enclosure
- Companion mobile app for remote control (not just viewing)
- ESP32-CAM integration for visual occupancy confirmation and remote fault inspection
- Live-hardware validation of remaining ML fault categories
- Firebase security rules hardening
- Multi-zone scaling (multiple ESP32 nodes, one dashboard)

---

## Author

B.V.R. Perera — SLT–Mobitel Nebula Institute of Technology, BTEC HND Unit 5001 Research Project (2026)

---

## License

This project was developed for academic purposes. Contact the author before reuse.
