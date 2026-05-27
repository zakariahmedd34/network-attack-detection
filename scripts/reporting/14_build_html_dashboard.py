"""
Network Attack Detection — static HTML dashboard.
Alternative to Streamlit for environments where
exposing port 8501 is inconvenient (e.g. inside the Jupyter container).

Run after 13_build_dashboard.py:
    python 14_build_html_dashboard.py

Opens reports/dashboard.html in any browser. No server needed.
"""
from __future__ import annotations
import json
import base64
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent  # scripts/reporting/ → scripts/ → project root
FIG_DIR = ROOT / "reports" / "figures"
OUT_HTML = ROOT / "reports" / "dashboard.html"


def img_data_uri(path: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()


def main() -> None:
    if not FIG_DIR.exists():
        raise SystemExit("Run 13_build_dashboard.py first to populate reports/figures/")

    METRICS_DIR = ROOT / "reports" / "metrics"
    with open(METRICS_DIR / "04_confusion_matrices.json") as f:
        cm = json.load(f)
    with open(METRICS_DIR / "05_roc_auc.json") as f:
        auc = json.load(f)

    sections = [
        ("1 · Dataset distribution", [
            "01_attack_type_distribution.png",
            "02_binary_class_distribution.png",
        ]),
        ("2 · Model comparison (bar chart)", [
            "03_metric_comparison.png",
        ]),
        ("3 · Confusion matrices", [
            "04_confusion_model_a__logistic_regression.png",
            "04_confusion_model_b__deep_learning_mlp.png",
            "04_confusion_model_c__random_forest.png",
        ]),
        ("4 · ROC curves", [
            "05_roc_curves.png",
        ]),
        ("5 · Pipeline data flow", [
            "06_pipeline_data_flow.png",
        ]),
    ]

    body = []
    for title, files in sections:
        body.append(f"<section><h2>{title}</h2><div class='grid'>")
        for f in files:
            uri = img_data_uri(FIG_DIR / f)
            body.append(f"<figure><img src='{uri}' alt='{f}'/></figure>")
        body.append("</div></section>")

    auc_rows = "".join(
        f"<tr><td>{m}</td><td>{v:.4f}</td></tr>" for m, v in auc.items()
    )

    html = f"""<!doctype html>
<html><head><meta charset='utf-8'>
<title>IDS2017 - Network Attack Detection Dashboard</title>
<style>
body{{font-family:Arial,Helvetica,sans-serif;margin:0;background:#f8fafc;color:#111827}}
main{{max-width:1200px;margin:0 auto;padding:32px 24px}}
h1{{margin:0 0 6px}}
.caption{{color:#475569;margin:0 0 24px}}
section{{background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:18px 22px;margin:18px 0}}
h2{{margin:0 0 14px;font-size:18px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:14px}}
figure{{margin:0;background:#fff}}
img{{width:100%;height:auto;border-radius:6px;border:1px solid #e5e7eb}}
table{{width:auto;border-collapse:collapse;margin-top:8px}}
th,td{{padding:8px 14px;border-bottom:1px solid #e5e7eb;text-align:left;font-size:14px}}
th{{background:#f1f5f9}}
.kpi{{display:flex;gap:18px;flex-wrap:wrap;margin:6px 0 18px}}
.kpi div{{background:#fff;border:1px solid #e5e7eb;padding:14px 18px;border-radius:10px;min-width:180px}}
.kpi b{{display:block;font-size:22px;color:#2563eb}}
</style></head>
<body><main>
<h1>Network Attack Detection</h1>
<p class='caption'>CIC-IDS2017 Network Intrusion Detection &middot; Hadoop + Spark + Spark MLlib</p>
<div class='kpi'>
  <div><b>Random Forest</b>Best model (F1)</div>
  <div><b>0.9954</b>Best F1 score</div>
  <div><b>0.9999</b>Best AUC-ROC</div>
  <div><b>157,348</b>Test rows per model</div>
</div>
<section><h2>AUC summary</h2>
<table><thead><tr><th>Model</th><th>AUC-ROC</th></tr></thead>
<tbody>{auc_rows}</tbody></table></section>
{''.join(body)}
</main></body></html>"""

    OUT_HTML.write_text(html, encoding="utf-8")
    print("Wrote:", OUT_HTML)
    print("Open it in your browser - it is fully self-contained (images embedded).")


if __name__ == "__main__":
    main()
