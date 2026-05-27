#!/usr/bin/env bash
# =============================================================================
# Network Attack Detection — end-to-end pipeline orchestrator
# =============================================================================
# Runs every stage in order, but SKIPS any stage whose _SUCCESS marker already
# exists in HDFS — so you can re-run this safely without retraining.
#
# Requires: the Hadoop/Spark Docker cluster already running.
# Run from the project root:
#     bash run_pipeline.sh
# =============================================================================
set -euo pipefail

CYAN="\033[36m"; GREEN="\033[32m"; YELLOW="\033[33m"; RED="\033[31m"; RESET="\033[0m"
say()      { printf "${CYAN}==>${RESET} %s\n" "$*"; }
ok()       { printf "${GREEN}OK${RESET}  %s\n" "$*"; }
skip()     { printf "${YELLOW}SKIP${RESET} %s\n" "$*"; }
fail()     { printf "${RED}FAIL${RESET} %s\n" "$*"; exit 1; }

# ---- preflight: cluster running? --------------------------------------------
say "Preflight: checking cluster containers"
for c in namenode datanode spark-master spark-worker-1; do
  if docker ps --format '{{.Names}}' | grep -q "^${c}$"; then
    ok "$c running"
  else
    fail "$c not running — start the cluster: cd docker-hadoop-spark-jupyter && docker compose up -d"
  fi
done

# Numpy is needed for Spark MLlib jobs. Idempotent install.
docker exec spark-master   bash -lc "apk add --no-cache py3-numpy"   >/dev/null 2>&1 || true
docker exec spark-worker-1 bash -lc "apk add --no-cache py3-numpy"   >/dev/null 2>&1 || true

# ---- helpers -----------------------------------------------------------------
hdfs_has_success() {
  docker exec namenode hdfs dfs -test -e "$1/_SUCCESS" 2>/dev/null
}

run_or_skip() {
  local name="$1" hdfs_path="$2" cmd="$3"
  say "Stage: $name"
  if hdfs_has_success "$hdfs_path"; then
    skip "$hdfs_path/_SUCCESS already exists"
    return 0
  fi
  eval "$cmd"
  if hdfs_has_success "$hdfs_path"; then
    ok "$hdfs_path now has _SUCCESS"
  else
    fail "$name did not produce $hdfs_path/_SUCCESS"
  fi
}

# ---- 1. Upload CSVs ---------------------------------------------------------
say "Stage: Upload raw CSVs to HDFS"
bash scripts/02_upload_hdfs.sh
ok "upload step done (script is idempotent — it skips existing files)"

# ---- 2. Cleaning ------------------------------------------------------------
run_or_skip "Cleaning (04_clean.py)" \
  "/user/bigdata/ids2017/processed/cleaned" \
  "bash scripts/03_submit.sh"

# ---- 3. Feature engineering -------------------------------------------------
run_or_skip "Feature engineering (05_feature_engineering.py)" \
  "/user/bigdata/ids2017/processed/ml_ready_binary" \
  "bash scripts/05_submit_features.sh"

# ---- 4. Model A: Logistic Regression ----------------------------------------
# No .sh launcher — falls back to spark-submit directly.
if [ -f scripts/06_submit_baseline.sh ]; then
  MODEL_A_CMD="bash scripts/06_submit_baseline.sh"
else
  MODEL_A_CMD="docker exec spark-master /spark/bin/spark-submit \
      --master spark://spark-master:7077 \
      --conf spark.executor.memory=1500m \
      --conf spark.executor.cores=1 \
      --conf spark.driver.memory=512m \
      /workspace/06_model_baseline.py"
fi
run_or_skip "Model A: Logistic Regression" \
  "/user/bigdata/ids2017/results/model_a_baseline" \
  "$MODEL_A_CMD"

# ---- 5. Model B: Deep Learning MLP ------------------------------------------
run_or_skip "Model B: Deep Learning MLP" \
  "/user/bigdata/ids2017/results/model_b_deep_learning/predictions" \
  "bash scripts/07_submit_improved.sh"

# ---- 6. Model C: Random Forest ----------------------------------------------
run_or_skip "Model C: Random Forest" \
  "/user/bigdata/ids2017/results/model_c_random_forest/predictions" \
  "bash scripts/08_submit_random_forest.sh"

# ---- 7. Comparison of all 3 models ------------------------------------------
run_or_skip "Comparison of all 3 models" \
  "/user/bigdata/ids2017/results/model_comparison_all/metrics" \
  "bash scripts/09_submit_compare_all.sh"

# ---- 8. Export HDFS outputs to local readable files -------------------------
say "Stage: Export HDFS outputs to local CSV/HTML"
python3 scripts/10_export_readable_outputs.py
ok "outputs/readable_exports/ refreshed"

# ---- 9. Build dashboard figures (8 PNGs) ------------------------------------
say "Stage: Build paper figures (scripts/reporting/13_build_dashboard.py)"
python3 scripts/reporting/13_build_dashboard.py
ok "reports/figures/*.png regenerated"

# ---- 10. Build standalone HTML dashboard ------------------------------------
say "Stage: Build standalone HTML dashboard (scripts/reporting/14_build_html_dashboard.py)"
python3 scripts/reporting/14_build_html_dashboard.py
ok "reports/dashboard.html written"

# ---- 11. Rebuild architecture diagram ---------------------------------------
say "Stage: Architecture diagram (scripts/reporting/15_build_architecture_diagram.py)"
python3 scripts/reporting/15_build_architecture_diagram.py
ok "reports/architecture.png written"

# ---- Final summary -----------------------------------------------------------
echo ""
say "Pipeline complete."
echo ""
echo "Final artefacts:"
echo "  HDFS comparison:        /user/bigdata/ids2017/results/model_comparison_all"
echo "  HTML team report:       reports/model_comparison_report.html"
echo "  HTML dashboard:         reports/dashboard.html"
echo "  Figures (8 PNGs):       reports/figures/"
echo "  Architecture diagram:   reports/architecture.png"
echo "  Paper section (.docx):  reports/Section4_System_Architecture.docx  (manually authored)"
echo "  Interactive dashboard:  streamlit run dashboard/app.py"
echo ""
echo "Re-running this script is safe: every Spark stage skips if _SUCCESS exists."
