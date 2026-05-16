"""
Network Attack Detection — Streamlit interactive dashboard.

Loads the locally-committed Parquet outputs under ../outputs/hdfs_export/
and renders an interactive dashboard for the final presentation/demo.

Run from the project root:
    pip install streamlit pandas pyarrow matplotlib scikit-learn numpy
    streamlit run dashboard/app.py
"""
from __future__ import annotations
import glob
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from sklearn.metrics import roc_curve, auc as sk_auc

ROOT = Path(__file__).resolve().parent.parent
HDFS_EXPORT = ROOT / "outputs" / "hdfs_export"

MODELS = {
    "Model A - Logistic Regression":
        HDFS_EXPORT / "results" / "model_a_baseline",
    "Model B - Deep Learning MLP":
        HDFS_EXPORT / "results" / "model_b_deep_learning" / "predictions",
    "Model C - Random Forest":
        HDFS_EXPORT / "results" / "model_c_random_forest" / "predictions",
}

PALETTE_MODELS = ["#93c5fd", "#3b82f6", "#1e3a8a"]
PALETTE_BINARY = ["#93c5fd", "#1e3a8a"]
PALETTE_PRIMARY = "#2563eb"

st.set_page_config(page_title="IDS2017 — Network Attack Detection",
                   layout="wide")


@st.cache_data
def read_parquet_dir(path_str: str, columns=None) -> pd.DataFrame:
    files = sorted(glob.glob(f"{path_str}/*.parquet"))
    if not files:
        raise FileNotFoundError(f"No parquet in {path_str}")
    return pd.concat([pd.read_parquet(f, columns=columns) for f in files],
                     ignore_index=True)


def extract_prob_class1(prob_series):
    return np.array([float(v["values"][1]) for v in prob_series.values])


st.title("Network Attack Detection — IDS2017")
st.caption("CSCI461 Big Data project · "
           "Hadoop + Spark + Spark MLlib")

# -------------------------- Top KPIs --------------------------
metrics_df = read_parquet_dir(str(HDFS_EXPORT / "results" /
                                   "model_comparison_all" / "metrics"))
pivot = metrics_df.pivot(index="model", columns="metric",
                         values="value").sort_index()

best_model = pivot["f1"].idxmax()
best_f1 = pivot["f1"].max()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Best model (by F1)", best_model.replace("Model ", ""))
c2.metric("Best F1 score", f"{best_f1:.4f}")
c3.metric("Models compared", len(pivot))
c4.metric("Test rows (per model)", "157,348")

st.divider()

# -------------------------- Dataset distribution --------------
st.header("1 · Dataset distribution")
ml_ready = read_parquet_dir(
    str(HDFS_EXPORT / "processed" / "ml_ready_binary"),
    columns=["label", "label_original"],
)
colA, colB = st.columns(2)

with colA:
    st.subheader("Original attack-type distribution")
    counts = ml_ready["label_original"].value_counts().sort_values()
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.barh(counts.index, counts.values, color=PALETTE_PRIMARY)
    for i, v in enumerate(counts.values):
        ax.text(v, i, f" {v:,}", va="center", fontsize=9)
    ax.set_xlabel("Flow count")
    ax.set_title("Original (multiclass) labels")
    st.pyplot(fig)

with colB:
    st.subheader("Binary BENIGN vs ATTACK")
    bin_counts = ml_ready["label"].value_counts().sort_index()
    labels = ["BENIGN" if k == 0.0 else "ATTACK" for k in bin_counts.index]
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.pie(bin_counts.values, labels=labels,
           colors=PALETTE_BINARY,
           autopct="%1.2f%%", startangle=90)
    ax.set_title("Binary class share")
    st.pyplot(fig)

st.divider()

# -------------------------- Metrics table & bars --------------
st.header("2 · Model comparison")
st.subheader("Metrics table")
display = pivot[["accuracy", "precision", "recall", "f1", "auc_roc"]] \
    .round(4)
st.dataframe(display.style.highlight_max(axis=0, color="#dcfce7"),
             use_container_width=True)

st.subheader("Metric bar chart")
metric_order = ["accuracy", "precision", "recall", "f1", "auc_roc"]
x = np.arange(len(metric_order))
width = 0.25
colors = PALETTE_MODELS
fig, ax = plt.subplots(figsize=(10, 5))
for i, model in enumerate(pivot.index):
    ax.bar(x + (i - 1) * width, pivot.loc[model, metric_order].values,
           width, label=model, color=colors[i % 3])
ax.set_xticks(x)
ax.set_xticklabels([m.upper() for m in metric_order])
ax.set_ylim(0.9, 1.02)
ax.set_ylabel("Score")
ax.legend(loc="lower right")
ax.grid(axis="y", linestyle=":", alpha=0.5)
st.pyplot(fig)

st.divider()

# -------------------------- Confusion matrices ----------------
st.header("3 · Confusion matrices")
cm_df = read_parquet_dir(str(HDFS_EXPORT / "results" /
                              "model_comparison_all" / "confusion_matrix"))
cols = st.columns(3)
for col, model_name in zip(cols, pivot.index):
    with col:
        st.subheader(model_name.replace("Model ", "M"))
        sub = cm_df[cm_df["model"] == model_name]
        cm = np.zeros((2, 2), dtype=int)
        for _, row in sub.iterrows():
            cm[int(row["label"]), int(row["prediction"])] = int(row["count"])
        fig, ax = plt.subplots(figsize=(4, 4))
        im = ax.imshow(cm, cmap="Blues")
        ax.set_xticks([0, 1]); ax.set_xticklabels(["BENIGN", "ATTACK"])
        ax.set_yticks([0, 1]); ax.set_yticklabels(["BENIGN", "ATTACK"])
        ax.set_xlabel("Predicted"); ax.set_ylabel("Actual")
        thresh = cm.max() / 2
        for i in range(2):
            for j in range(2):
                ax.text(j, i, f"{cm[i, j]:,}", ha="center", va="center",
                        color="white" if cm[i, j] > thresh else "black",
                        fontsize=12, fontweight="bold")
        st.pyplot(fig)

st.divider()

# -------------------------- ROC curves ------------------------
st.header("4 · ROC curves")
fig, ax = plt.subplots(figsize=(7, 6))
for (model_name, path), color in zip(MODELS.items(), PALETTE_MODELS):
    df = read_parquet_dir(str(path), columns=["label", "probability"])
    y_true = df["label"].astype(int).values
    y_score = extract_prob_class1(df["probability"])
    fpr, tpr, _ = roc_curve(y_true, y_score)
    auc_val = sk_auc(fpr, tpr)
    ax.plot(fpr, tpr, label=f"{model_name} (AUC = {auc_val:.4f})",
            color=color, linewidth=2)
ax.plot([0, 1], [0, 1], "--", color="#9ca3af", label="Random")
ax.set_xlabel("False Positive Rate")
ax.set_ylabel("True Positive Rate")
ax.set_title("ROC — Model A vs B vs C")
ax.legend(loc="lower right")
ax.grid(linestyle=":", alpha=0.5)
st.pyplot(fig)

st.divider()

# -------------------------- Pipeline & paths -------------------
st.header("5 · Pipeline (system architecture)")
st.code("""
14 raw CSVs   ──►  HDFS /user/bigdata/ids2017/raw
                       │
                       ▼  04_clean.py  (Spark)
              HDFS /processed/cleaned          (785,583 × 122)
                       │
                       ▼  05_feature_engineering.py  (Spark)
              HDFS /processed/ml_ready_binary  (features, label, label_original)
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
   06_baseline    07_improved    08_random_forest
   (Spark MLlib)  (Spark MLlib)  (Spark MLlib)
        │              │              │
        ▼              ▼              ▼
  /results/         /results/      /results/
  model_a_         model_b_       model_c_
  baseline         deep_learning  random_forest
        └──────────────┼──────────────┘
                       ▼  09_compare_all_models.py
              /results/model_comparison_all  +  HTML report
""", language="text")

st.caption(
    "Best model by every metric: **Random Forest** "
    "(accuracy 0.9954, F1 0.9954, AUC-ROC 0.9999). "
    "Inputs read from `outputs/hdfs_export/`, which mirrors HDFS exactly."
)
