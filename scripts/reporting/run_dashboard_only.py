"""
Local-only report regenerator.

Reads the saved Parquet outputs under outputs/hdfs_export/ and regenerates
all figures, the standalone HTML dashboard, and the architecture diagram.
No Docker, no Spark, no HDFS required.

Run from the project root:
    pip install -r requirements.txt
    python scripts/reporting/run_dashboard_only.py
"""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

# scripts/reporting/run_dashboard_only.py → parent=reporting/ → parent=scripts/ → parent=project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
REPORTING_DIR = Path(__file__).resolve().parent
HDFS_EXPORT = PROJECT_ROOT / "outputs" / "hdfs_export"

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
]

for s in scripts:
    script_path = REPORTING_DIR / s
    print(f"\n=== Running {s} ===")
    subprocess.check_call([sys.executable, str(script_path)])

print("\n=== All done ===")
print("Open the dashboard:   reports/dashboard.html")
print("Open the diagram:     reports/architecture.png")
print("Interactive app:      streamlit run dashboard/app.py")
