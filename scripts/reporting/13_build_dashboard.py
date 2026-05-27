"""
Network Attack Detection — local dashboard PNG generator.

Reads the Parquet outputs already committed under outputs/hdfs_export/ and
produces all paper-ready charts under reports/figures/. No Spark, no HDFS,
no Docker required.

Run from the project root:
    pip install pandas pyarrow matplotlib scikit-learn numpy
    python 13_build_dashboard.py
"""
from __future__ import annotations
import os
import glob
import json
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics import roc_curve, auc as sk_auc

ROOT = Path(__file__).resolve().parent.parent.parent  # scripts/reporting/ → scripts/ → project root
HDFS_EXPORT = ROOT / "outputs" / "hdfs_export"
FIG_DIR = ROOT / "reports" / "figures"
TABLES_DIR = ROOT / "reports" / "tables"
METRICS_DIR = ROOT / "reports" / "metrics"
FIG_DIR.mkdir(parents=True, exist_ok=True)
TABLES_DIR.mkdir(parents=True, exist_ok=True)
METRICS_DIR.mkdir(parents=True, exist_ok=True)

MODELS = [
    ("Model A - Logistic Regression",
     HDFS_EXPORT / "results" / "model_a_baseline"),
    ("Model B - Deep Learning MLP",
     HDFS_EXPORT / "results" / "model_b_deep_learning" / "predictions"),
    ("Model C - Random Forest",
     HDFS_EXPORT / "results" / "model_c_random_forest" / "predictions"),
]

PALETTE = {
    "primary":  "#2563eb",
    "models":   ["#93c5fd", "#3b82f6", "#1e3a8a"],
    "binary":   ["#93c5fd", "#1e3a8a"],
    "stages":   ["#cbd5e1", "#93c5fd", "#3b82f6", "#1e3a8a"],
}


def read_parquet_dir(path: Path, columns=None) -> pd.DataFrame:
    files = sorted(glob.glob(str(path / "*.parquet")))
    if not files:
        raise FileNotFoundError(f"No parquet files in {path}")
    frames = [pd.read_parquet(f, columns=columns) for f in files]
    return pd.concat(frames, ignore_index=True)


def extract_prob_class1(prob_series: pd.Series) -> np.ndarray:
    """Spark VectorUDT serialised to a struct: take values[1] = P(class=1)."""
    out = np.empty(len(prob_series), dtype=float)
    for i, v in enumerate(prob_series.values):
        out[i] = float(v["values"][1])
    return out


def chart_attack_distribution():
    print("[1/6] Original attack-type distribution")
    df = read_parquet_dir(
        HDFS_EXPORT / "processed" / "ml_ready_binary",
        columns=["label_original"],
    )
    counts = df["label_original"].value_counts().sort_values(ascending=True)
    plt.figure(figsize=(10, 6))
    plt.barh(counts.index, counts.values, color=PALETTE["primary"])
    for i, v in enumerate(counts.values):
        plt.text(v, i, f" {v:,}", va="center", fontsize=9)
    plt.xlabel("Flow count")
    plt.title("CIC-IDS2017 — Original attack-type distribution")
    plt.tight_layout()
    out = FIG_DIR / "01_attack_type_distribution.png"
    plt.savefig(out, dpi=150)
    plt.close()
    counts.to_csv(TABLES_DIR / "01_attack_type_distribution.csv")
    print("  saved:", out)


def chart_binary_distribution():
    print("[2/6] Binary BENIGN vs ATTACK distribution")
    df = read_parquet_dir(
        HDFS_EXPORT / "processed" / "ml_ready_binary",
        columns=["label"],
    )
    counts = df["label"].value_counts().sort_index()
    labels = ["BENIGN (0.0)" if k == 0.0 else "ATTACK (1.0)" for k in counts.index]
    colors = PALETTE["binary"]

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    axes[0].pie(counts.values, labels=labels, colors=colors,
                autopct="%1.2f%%", startangle=90)
    axes[0].set_title("Binary class distribution (share)")
    axes[1].bar(labels, counts.values, color=colors)
    for i, v in enumerate(counts.values):
        axes[1].text(i, v, f"{v:,}", ha="center", va="bottom")
    axes[1].set_ylabel("Flow count")
    axes[1].set_title("Binary class distribution (count)")
    plt.tight_layout()
    out = FIG_DIR / "02_binary_class_distribution.png"
    plt.savefig(out, dpi=150)
    plt.close()
    counts.to_csv(TABLES_DIR / "02_binary_class_distribution.csv")
    print("  saved:", out)


def chart_metric_comparison():
    print("[3/6] Metric comparison across the 3 models")
    df = read_parquet_dir(HDFS_EXPORT / "results" / "model_comparison_all" / "metrics")
    pivot = df.pivot(index="model", columns="metric", values="value")
    metric_order = ["accuracy", "precision", "recall", "f1", "auc_roc"]
    pivot = pivot[metric_order]

    x = np.arange(len(metric_order))
    width = 0.25
    colors = PALETTE["models"]
    plt.figure(figsize=(11, 6))
    for i, model in enumerate(pivot.index):
        plt.bar(x + (i - 1) * width, pivot.loc[model].values, width,
                label=model, color=colors[i % 3])
        for j, v in enumerate(pivot.loc[model].values):
            plt.text(x[j] + (i - 1) * width, v + 0.005, f"{v:.3f}",
                     ha="center", fontsize=8)
    plt.xticks(x, [m.upper() for m in metric_order])
    plt.ylim(0.9, 1.02)
    plt.ylabel("Score")
    plt.title("Model A vs B vs C — Metric comparison")
    plt.legend(loc="lower right")
    plt.grid(axis="y", linestyle=":", alpha=0.5)
    plt.tight_layout()
    out = FIG_DIR / "03_metric_comparison.png"
    plt.savefig(out, dpi=150)
    plt.close()
    pivot.to_csv(TABLES_DIR / "03_metric_comparison.csv")
    print("  saved:", out)
    return pivot


def chart_confusion_matrices():
    print("[4/6] Confusion matrices (one per model)")
    df = read_parquet_dir(HDFS_EXPORT / "results" / "model_comparison_all" / "confusion_matrix")
    summary = {}
    for model_name in df["model"].unique():
        sub = df[df["model"] == model_name]
        cm = np.zeros((2, 2), dtype=int)
        for _, row in sub.iterrows():
            cm[int(row["label"]), int(row["prediction"])] = int(row["count"])
        summary[model_name] = cm.tolist()

        fig, ax = plt.subplots(figsize=(5, 4.5))
        im = ax.imshow(cm, cmap="Blues")
        ax.set_xticks([0, 1]); ax.set_xticklabels(["BENIGN", "ATTACK"])
        ax.set_yticks([0, 1]); ax.set_yticklabels(["BENIGN", "ATTACK"])
        ax.set_xlabel("Predicted"); ax.set_ylabel("Actual")
        ax.set_title(f"{model_name}\nConfusion matrix")
        thresh = cm.max() / 2
        for i in range(2):
            for j in range(2):
                ax.text(j, i, f"{cm[i, j]:,}", ha="center", va="center",
                        color="white" if cm[i, j] > thresh else "black",
                        fontsize=14, fontweight="bold")
        plt.colorbar(im, ax=ax, shrink=0.8)
        plt.tight_layout()
        safe = model_name.lower().replace(" ", "_").replace("-", "")
        out = FIG_DIR / f"04_confusion_{safe}.png"
        plt.savefig(out, dpi=150)
        plt.close()
        print("  saved:", out)

    with open(METRICS_DIR / "04_confusion_matrices.json", "w") as f:
        json.dump(summary, f, indent=2)


def chart_roc_curves():
    print("[5/6] ROC curves (all models on one plot)")
    plt.figure(figsize=(8, 7))
    auc_table = {}
    for (model_name, path), color in zip(MODELS, PALETTE["models"]):
        df = read_parquet_dir(path, columns=["label", "probability"])
        y_true = df["label"].astype(int).values
        y_score = extract_prob_class1(df["probability"])
        fpr, tpr, _ = roc_curve(y_true, y_score)
        auc = sk_auc(fpr, tpr)
        auc_table[model_name] = float(auc)
        plt.plot(fpr, tpr, label=f"{model_name} (AUC = {auc:.4f})",
                 color=color, linewidth=2)
        print(f"  {model_name}: AUC = {auc:.4f}")

    plt.plot([0, 1], [0, 1], "--", color="#9ca3af", label="Random (AUC = 0.5)")
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title("ROC curves — Model A vs B vs C")
    plt.legend(loc="lower right")
    plt.grid(linestyle=":", alpha=0.5)
    plt.tight_layout()
    out = FIG_DIR / "05_roc_curves.png"
    plt.savefig(out, dpi=150)
    plt.close()
    print("  saved:", out)

    with open(METRICS_DIR / "05_roc_auc.json", "w") as f:
        json.dump(auc_table, f, indent=2)


def chart_pipeline_data_flow():
    print("[6/6] Pipeline data-flow figure (text-based summary chart)")
    cleaned = read_parquet_dir(HDFS_EXPORT / "processed" / "cleaned",
                               columns=["label"])
    ml_ready = read_parquet_dir(HDFS_EXPORT / "processed" / "ml_ready_binary",
                                columns=["label"])
    pred_a = read_parquet_dir(MODELS[0][1], columns=["label"])
    stages = [
        ("Raw CSVs\n(14 files)", "~3,000,000", PALETTE["stages"][0]),
        ("Cleaned\nParquet", f"{len(cleaned):,}", PALETTE["stages"][1]),
        ("ML-ready\nbinary", f"{len(ml_ready):,}", PALETTE["stages"][2]),
        ("Test set\n(predictions)", f"{len(pred_a):,}", PALETTE["stages"][3]),
    ]
    fig, ax = plt.subplots(figsize=(11, 4))
    ax.axis("off")
    box_w = 2.0
    for i, (name, rows, color) in enumerate(stages):
        x = i * 2.7
        ax.add_patch(plt.Rectangle((x, 0.4), box_w, 1.6, facecolor=color,
                                    edgecolor="#111827", linewidth=1.2))
        ax.text(x + box_w / 2, 1.45, name, ha="center", va="center",
                fontsize=11, fontweight="bold")
        ax.text(x + box_w / 2, 0.9, f"rows: {rows}", ha="center", va="center",
                fontsize=10)
        if i < len(stages) - 1:
            ax.annotate("", xy=(x + box_w + 0.65, 1.2),
                        xytext=(x + box_w + 0.05, 1.2),
                        arrowprops=dict(arrowstyle="->", linewidth=2,
                                         color="#111827"))
    ax.set_xlim(-0.2, len(stages) * 2.7)
    ax.set_ylim(0, 2.4)
    ax.set_title("Pipeline data flow — rows persisted at each stage",
                 fontsize=12, fontweight="bold")
    plt.tight_layout()
    out = FIG_DIR / "06_pipeline_data_flow.png"
    plt.savefig(out, dpi=150)
    plt.close()
    print("  saved:", out)


if __name__ == "__main__":
    print("=== Network Attack Detection — dashboard PNG generator ===")
    print("Reading from:", HDFS_EXPORT)
    print("Writing to:  ", FIG_DIR)
    chart_attack_distribution()
    chart_binary_distribution()
    chart_metric_comparison()
    chart_confusion_matrices()
    chart_roc_curves()
    chart_pipeline_data_flow()
    print("\nAll figures generated. Open the folder:")
    print(" ", FIG_DIR)
