"""
Network Attack Detection — architecture diagram generator.

Produces reports/architecture.png at print quality using the same blue
palette as the other dashboard figures. No external tools needed.

Run:
    python 15_build_architecture_diagram.py
"""
from __future__ import annotations
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

ROOT = Path(__file__).resolve().parent.parent.parent  # scripts/reporting/ → scripts/ → project root
OUT = ROOT / "reports" / "architecture.png"
OUT.parent.mkdir(parents=True, exist_ok=True)

PAL = {
    "source":  "#cbd5e1",
    "hdfs":    "#93c5fd",
    "compute": "#3b82f6",
    "model":   "#1e3a8a",
    "output":  "#1e40af",
    "text":    "#0f172a",
    "edge":    "#0f172a",
    "stroke":  "#0f172a",
}

W, H = 16, 11
fig, ax = plt.subplots(figsize=(W, H))
ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")


def box(x, y, w, h, color, title, subtitle="", *, text_color="#0f172a"):
    rect = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.06,rounding_size=0.12",
        linewidth=1.2, edgecolor=PAL["stroke"], facecolor=color,
    )
    ax.add_patch(rect)
    ax.text(x + w / 2, y + h * 0.62, title, ha="center", va="center",
            fontsize=11, fontweight="bold", color=text_color)
    if subtitle:
        ax.text(x + w / 2, y + h * 0.28, subtitle, ha="center", va="center",
                fontsize=9, color=text_color)


def arrow(x1, y1, x2, y2, label="", *, offset=(0.18, 0)):
    a = FancyArrowPatch(
        (x1, y1), (x2, y2),
        arrowstyle="-|>", mutation_scale=18,
        linewidth=1.6, color=PAL["edge"],
    )
    ax.add_patch(a)
    if label:
        mx, my = (x1 + x2) / 2 + offset[0], (y1 + y2) / 2 + offset[1]
        ax.text(mx, my, label, fontsize=8.5, color="#334155",
                ha="left", va="center",
                bbox=dict(boxstyle="round,pad=0.18", facecolor="white",
                          edgecolor="none", alpha=0.95))


ax.text(W / 2, H - 0.45, "Network Attack Detection — System Architecture",
        ha="center", fontsize=15, fontweight="bold", color=PAL["text"])
ax.text(W / 2, H - 0.85,
        "Hadoop (HDFS) · Apache Spark · Spark MLlib · CIC-IDS2017",
        ha="center", fontsize=10, color="#475569")

bw, bh = 3.2, 0.95

box(6.4, 8.7, bw, bh, PAL["source"], "14 raw CSVs", "~600 MB · CIC-IDS2017")
box(6.4, 7.4, bw, bh, PAL["hdfs"], "HDFS  /raw", "Hadoop distributed file system")
box(6.4, 6.1, bw, bh, PAL["hdfs"], "HDFS  /processed/cleaned",
    "Parquet · 785,583 rows × 122 cols",
    text_color="#0f172a")
box(6.4, 4.8, bw, bh, PAL["hdfs"], "HDFS  /processed/ml_ready_binary",
    "features · label · label_original")

mw, mh = 2.6, 0.95
mx_a, mx_b, mx_c = 1.6, 6.7, 11.8
box(mx_a, 3.0, mw, mh, "#93c5fd", "Model A",
    "Logistic Regression\n(Spark MLlib)")
box(mx_b, 3.0, mw, mh, "#3b82f6", "Model B",
    "Deep Learning MLP\n(Spark MLlib)", text_color="white")
box(mx_c, 3.0, mw, mh, PAL["model"], "Model C",
    "Random Forest\n(Spark MLlib)", text_color="white")

rw, rh = 2.6, 0.7
box(mx_a, 1.7, rw, rh, "#dbeafe", "model_a_baseline", "Parquet · /results")
box(mx_b, 1.7, rw, rh, "#dbeafe", "model_b_deep_learning", "Parquet · /results")
box(mx_c, 1.7, rw, rh, "#dbeafe", "model_c_random_forest", "Parquet · /results")

box(6.4, 0.55, bw, bh, PAL["compute"],
    "Comparison & Reports", "09_compare_all_models.py · 13_build_dashboard.py",
    text_color="white")

arrow(8.0, 8.7, 8.0, 8.35,  "hdfs dfs -put  (02_upload_hdfs.sh)")
arrow(8.0, 7.4, 8.0, 7.05,  "Spark · 04_clean.py")
arrow(8.0, 6.1, 8.0, 5.75,  "Spark · 05_feature_engineering.py")
arrow(8.0, 4.8, mx_a + mw / 2, 3.95, "randomSplit(0.8, 0.2)")
arrow(8.0, 4.8, mx_b + mw / 2, 3.95, "")
arrow(8.0, 4.8, mx_c + mw / 2, 3.95, "")
arrow(mx_a + mw / 2, 3.0, mx_a + mw / 2, 2.4, "")
arrow(mx_b + mw / 2, 3.0, mx_b + mw / 2, 2.4, "")
arrow(mx_c + mw / 2, 3.0, mx_c + mw / 2, 2.4, "")
arrow(mx_a + mw / 2, 1.7, 8.0, 1.5, "metrics · confusion · AUC")
arrow(mx_b + mw / 2, 1.7, 8.0, 1.5, "")
arrow(mx_c + mw / 2, 1.7, 8.0, 1.5, "")

legend_items = [
    (PAL["source"],  "Source data (CSV)"),
    (PAL["hdfs"],    "Storage layer (HDFS · Parquet)"),
    (PAL["compute"], "Compute layer (Apache Spark)"),
    (PAL["model"],   "Models (Spark MLlib)"),
]
for i, (c, label) in enumerate(legend_items):
    lx, ly = 0.5, H - 1.55 - i * 0.35
    ax.add_patch(plt.Rectangle((lx, ly), 0.3, 0.22, color=c,
                                ec=PAL["stroke"], linewidth=0.8))
    ax.text(lx + 0.4, ly + 0.11, label, va="center", fontsize=9,
            color=PAL["text"])

plt.tight_layout()
plt.savefig(OUT, dpi=200, bbox_inches="tight",
            facecolor="white")
plt.close()
print("Architecture diagram saved:", OUT)
