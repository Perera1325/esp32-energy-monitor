# Fault Diagnosis & Recommendation Model (Proof-of-Concept)

## Status: synthetic-data proof-of-concept, NOT yet validated against real hardware

This is the ML add-on discussed in Chapter 6 of the final report: once the
existing rule engine (Section 3.1) raises a MAINTENANCE-type alert, this
model goes a step further and suggests a *likely cause* and a *specific
recommended action*, instead of only "MAINTENANCE alert raised."

It is built and trained on **synthetic data**, not real sensor readings,
because the soldered board has not yet been powered up, calibrated, or run
through a real fault (Project Log, Sheet 12, 11 Sep 2026). This is stated
plainly here and must be stated equally plainly in the report — every
number this pipeline produces describes how well the model fits the
documented synthetic assumptions in `generate_synthetic_dataset.py`, not
real-world diagnostic accuracy. Treat it as a working prototype of the
*pipeline* (data → features → model → recommendation), not as evidence the
system correctly diagnoses real faults yet.

## Why a Decision Tree, not a bigger model

Chosen deliberately, for the same reason the core system uses a rule engine
rather than a black-box model (Section 1.2 of the report): a decision tree
can be printed out as readable if/else logic, which keeps the diagnostic
layer auditable rather than opaque, and it's an appropriate amount of model
for ~10 engineered features and a few thousand samples — a larger model
would just overfit the synthetic data harder, not diagnose faults better.

## Files

| File | Purpose |
|---|---|
| `generate_synthetic_dataset.py` | Builds the labelled synthetic training set. Class definitions and generation logic are documented in the file's docstring — read it before citing this in the report, since it explains exactly what assumptions the "results" rest on. |
| `train_fault_model.py` | Trains the Decision Tree, prints real accuracy/precision/recall/F1/confusion-matrix/feature-importance/rule-text output. |
| `predict_recommend.py` | Loads the trained model and demonstrates turning a feature window into a diagnosis + recommendation string. |

## How to run it (on your own machine)

Bash tool access on my side is currently down (Windows-update-related sandbox
issue, unrelated to your code), so you'll need Python installed locally for
now. If you've got Python 3.9+:

```bash
pip install numpy pandas scikit-learn joblib

python generate_synthetic_dataset.py --n-per-class 400 --out dataset.csv
python train_fault_model.py --data dataset.csv --model fault_model.joblib
python predict_recommend.py --model fault_model.joblib
```

The middle command is the one whose printed output — accuracy, the
classification report, the confusion matrix — is what you should copy into
Chapter 4 / Chapter 6 of the report, clearly labelled as "measured on the
synthetic dataset described in [X]." Do not estimate or guess these numbers
yourself, and don't ask me to guess them either — copy exactly what the
script prints when you run it. I can also run this myself the moment my
sandbox recovers, and hand you the real output directly.

## What "real data later" looks like

Once the board is continuity-tested, powered up, and calibrated (the next
steps already logged in Sheet 12), the natural upgrade path is:

1. Keep logging the same 10 features (mean/std/slope per sensor +
   occupancy fraction) computed over rolling 5-minute windows from the
   *real* Firebase-logged readings, using the same feature definitions as
   `generate_synthetic_dataset.py` so the pipeline doesn't need to change.
2. When a real fault is deliberately induced or naturally occurs during
   testing, label that window with its true cause.
3. Retrain `train_fault_model.py` on a dataset that blends real labelled
   windows with the synthetic set (or replaces it entirely once enough
   real examples exist), and re-report accuracy — that second number is
   the one an examiner will trust, and the gap between it and the
   synthetic-only number is itself worth discussing in Chapter 4.

## Fault classes and their report-facing justification

| Class | Rule-engine relationship | Physical meaning |
|---|---|---|
| NORMAL | matches NONE | no fault |
| ENERGY_WASTE | matches existing WASTE rule | load on, room unoccupied |
| BEARING_WEAR | new — refines MAINTENANCE | slow correlated current+temp rise |
| OVERLOAD_BLOCKAGE | new — refines MAINTENANCE | sudden current+temp step-up |
| SUPPLY_VOLTAGE_FAULT | matches existing SUPPLY FAULT rule | voltage outside 200–240V band |
| INTERMITTENT_CONNECTION | new — refines MAINTENANCE | elevated noise, normal means |

The three "new" classes are exactly the value this ML layer adds beyond the
existing rule engine: the rule engine can already say *something is wrong*
(MAINTENANCE), this model attempts to say *what kind of something*.
