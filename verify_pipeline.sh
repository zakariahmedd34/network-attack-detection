#!/usr/bin/env bash
# =============================================================================
# Network Attack Detection — pipeline verification
# =============================================================================
# Prints a one-screen status report:
#   - which HDFS stages have completed (_SUCCESS markers)
#   - which local artefacts exist
#   - final metrics summary
#
# Run from the project root:
#     bash verify_pipeline.sh
# =============================================================================
GREEN="\033[32m"; RED="\033[31m"; CYAN="\033[36m"; RESET="\033[0m"
pass() { printf "  ${GREEN}✓${RESET}  %s\n" "$*"; }
fail() { printf "  ${RED}✗${RESET}  %s\n" "$*"; FAILED=1; }
say()  { printf "${CYAN}==>${RESET} %s\n" "$*"; }

FAILED=0

# ---- HDFS stages -------------------------------------------------------------
if docker ps --format '{{.Names}}' | grep -q '^namenode$'; then
  say "HDFS stages (cluster reachable)"
  declare -a HDFS_PATHS=(
    "/user/bigdata/ids2017/processed/cleaned"
    "/user/bigdata/ids2017/processed/ml_ready_binary"
    "/user/bigdata/ids2017/results/model_a_baseline"
    "/user/bigdata/ids2017/results/model_b_deep_learning/predictions"
    "/user/bigdata/ids2017/results/model_c_random_forest/predictions"
    "/user/bigdata/ids2017/results/model_comparison_all/metrics"
  )
  for p in "${HDFS_PATHS[@]}"; do
    if docker exec namenode hdfs dfs -test -e "$p/_SUCCESS" 2>/dev/null; then
      pass "$p/_SUCCESS"
    else
      fail "$p/_SUCCESS MISSING"
    fi
  done
else
  say "HDFS stages (cluster not running — checking local Parquet exports instead)"
  declare -a LOCAL_PARQUET=(
    "outputs/hdfs_export/processed/cleaned"
    "outputs/hdfs_export/processed/ml_ready_binary"
    "outputs/hdfs_export/results/model_a_baseline"
    "outputs/hdfs_export/results/model_b_deep_learning/predictions"
    "outputs/hdfs_export/results/model_c_random_forest/predictions"
    "outputs/hdfs_export/results/model_comparison_all/metrics"
  )
  for p in "${LOCAL_PARQUET[@]}"; do
    if [ -f "$p/_SUCCESS" ]; then
      pass "$p/_SUCCESS"
    else
      fail "$p/_SUCCESS MISSING"
    fi
  done
fi

# ---- Local artefacts ---------------------------------------------------------
say "Local artefacts"
declare -a ARTEFACTS=(
  "reports/model_comparison_report.html"
  "reports/dashboard.html"
  "reports/architecture.png"
  "reports/Section4_System_Architecture.docx"
  "reports/figures/01_attack_type_distribution.png"
  "reports/figures/02_binary_class_distribution.png"
  "reports/figures/03_metric_comparison.png"
  "reports/figures/04_confusion_model_a__logistic_regression.png"
  "reports/figures/04_confusion_model_b__deep_learning_mlp.png"
  "reports/figures/04_confusion_model_c__random_forest.png"
  "reports/figures/05_roc_curves.png"
  "reports/figures/06_pipeline_data_flow.png"
)
for f in "${ARTEFACTS[@]}"; do
  if [ -f "$f" ]; then pass "$f"; else fail "$f MISSING"; fi
done

# ---- Metric summary ----------------------------------------------------------
if [ -f reports/figures/03_metric_comparison.csv ]; then
  say "Final metrics (from reports/figures/03_metric_comparison.csv)"
  cat reports/figures/03_metric_comparison.csv | column -t -s,
fi

echo ""
if [ "$FAILED" -eq 0 ]; then
  printf "${GREEN}ALL CHECKS PASSED — pipeline is end-to-end valid.${RESET}\n"
  exit 0
else
  printf "${RED}One or more checks failed. Run: bash run_pipeline.sh${RESET}\n"
  exit 1
fi
