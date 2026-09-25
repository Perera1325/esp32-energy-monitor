"""
train_fault_model.py

Trains and evaluates the fault-diagnosis classifier on the dataset produced
by generate_synthetic_dataset.py, and saves the trained model for use by
predict_recommend.py.

A Decision Tree classifier is used deliberately instead of a more complex
model (e.g. a neural network). Reasons, for the report's methodology
justification (Section 3.x / Chapter 6):
  1. Interpretability -- the exact decision logic can be printed and
     inspected as if/else rules, which keeps the system auditable and
     consistent with this project's rule-based philosophy (Section 1.2),
     rather than introducing an unexplainable black box.
  2. Appropriate for the dataset size and feature count (10 engineered
     features, a few thousand synthetic samples) -- a deep model would be
     both unnecessary and prone to overfitting on this scale of data.
  3. Runs comfortably off-device (a laptop or small cloud function), which
     matches the "off-device inference" scope agreed for this stage of the
     project.

IMPORTANT: every number this script prints (accuracy, precision, recall,
F1, confusion matrix) is a REAL, measured result of running this exact
script on the synthetic dataset -- nothing is pre-written or assumed. Do
not copy example figures from README.md into the report; copy the actual
numbers this script prints when you run it yourself.

Usage:
    python generate_synthetic_dataset.py --n-per-class 400 --out dataset.csv
    python train_fault_model.py --data dataset.csv --model fault_model.joblib
"""

import argparse
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier, export_text
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score

FEATURE_COLUMNS = [
    "current_mean", "current_std", "current_slope",
    "voltage_mean", "voltage_std", "voltage_slope",
    "temp_mean", "temp_std", "temp_slope",
    "occupancy_fraction",
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=str, default="dataset.csv")
    parser.add_argument("--model", type=str, default="fault_model.joblib")
    parser.add_argument("--max-depth", type=int, default=6,
                         help="tree depth cap -- keeps the tree small enough to read/export")
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    df = pd.read_csv(args.data)
    X = df[FEATURE_COLUMNS]
    y = df["label_name"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=args.test_size, random_state=args.seed, stratify=y
    )

    clf = DecisionTreeClassifier(max_depth=args.max_depth, random_state=args.seed)
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)

    print("=" * 70)
    print(f"Trained on {len(X_train)} windows, tested on {len(X_test)} windows")
    print(f"Test-set accuracy: {accuracy_score(y_test, y_pred):.4f}")
    print("=" * 70)
    print("\nClassification report (test set):\n")
    print(classification_report(y_test, y_pred))

    print("Confusion matrix (rows = true class, columns = predicted class):")
    labels_sorted = sorted(y.unique())
    cm = confusion_matrix(y_test, y_pred, labels=labels_sorted)
    cm_df = pd.DataFrame(cm, index=labels_sorted, columns=labels_sorted)
    print(cm_df)

    print("\nFeature importances (higher = more influential in the trained tree):")
    importances = pd.Series(clf.feature_importances_, index=FEATURE_COLUMNS).sort_values(ascending=False)
    print(importances)

    print("\nDecision tree rules (for Appendix / Methodology inclusion):\n")
    print(export_text(clf, feature_names=FEATURE_COLUMNS))

    joblib.dump({"model": clf, "features": FEATURE_COLUMNS}, args.model)
    print(f"\nSaved trained model to {args.model}")


if __name__ == "__main__":
    main()
