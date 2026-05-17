"""
Local-only end-to-end runner.

Reads the saved Parquet outputs under outputs/hdfs_export/ and regenerates
every figure, the standalone HTML dashboard, the architecture diagram, and
the paper section .docx. No Docker, no Spark, no HDFS required.

Run:
    pip install -r requirements.txt
    python run_dashboard_only.py
"""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HDFS_EXPORT = ROOT / "outputs" / "hdfs_export"

if not HDFS_EXPORT.exists():
    sys.exit(
        f"ERROR: {HDFS_EXPORT} missing. The saved Parquets are required.\n"
        "Either pull them from git, or run the full cluster pipeline first via "
        "`bash run_pipeline.sh`."
    )

scripts = [
    "13_build_dashboard.py",
    "14_build_html_dashboard.py",
    "15_build_architecture_diagram.py",
    "16_build_paper_docx.py",
]

for s in scripts:
    print(f"\n=== Running {s} ===")
    subprocess.check_call([sys.executable, str(ROOT / s)])

print("\n=== All done ===")
print("Open the dashboard:   open reports/dashboard.html")
print("Open the diagram:     open reports/architecture.png")
print("Open the paper docx:  open reports/Section4_System_Architecture.docx")
