#!/usr/bin/env bash
set -euo pipefail

# 09_submit_compare_all.sh -- compare Logistic Regression, Deep Learning, and Random Forest
# Run from project root after all three model jobs:
# bash scripts/09_submit_compare_all.sh

CONTAINER="spark-master"
NAMENODE="namenode"
SCRIPT="$(pwd)/09_compare_all_models.py"
REMOTE="/tmp/09_compare_all_models.py"
REMOTE_REPORT="/tmp/model_comparison_report.html"
LOCAL_REPORT_DIR="$(pwd)/reports"
LOCAL_REPORT="$LOCAL_REPORT_DIR/model_comparison_report.html"

if ! docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
    echo "ERROR: spark-master is not running. Start containers first:"
    echo "  cd path/to/docker-hadoop-spark-jupyter"
    echo "  docker compose up -d"
    exit 1
fi

if ! docker ps --format '{{.Names}}' | grep -qx "$NAMENODE"; then
    echo "ERROR: namenode is not running."
    exit 1
fi

if [ ! -f "$SCRIPT" ]; then
    echo "ERROR: 09_compare_all_models.py not found at $SCRIPT"
    exit 1
fi

required_paths=(
    "/user/bigdata/ids2017/results/model_a_baseline"
    "/user/bigdata/ids2017/results/model_b_deep_learning/predictions"
    "/user/bigdata/ids2017/results/model_c_random_forest/predictions"
)

for path in "${required_paths[@]}"; do
    if ! docker exec "$NAMENODE" hdfs dfs -test -e "$path"; then
        echo "ERROR: Missing required model output in HDFS: $path"
        echo "Run the model jobs before comparing all three."
        exit 1
    fi
done

echo "Copying comparison script to container..."
docker cp "$SCRIPT" "${CONTAINER}:${REMOTE}"

echo "Submitting all-model comparison job..."
docker exec "$CONTAINER" /spark/bin/spark-submit \
    --master spark://spark-master:7077 \
    --deploy-mode client \
    --driver-memory 512m \
    --executor-memory 1500m \
    --conf "spark.executor.cores=1" \
    --conf "spark.sql.shuffle.partitions=4" \
    --conf "spark.pyspark.python=python3" \
    "$REMOTE"

mkdir -p "$LOCAL_REPORT_DIR"
docker cp "${CONTAINER}:${REMOTE_REPORT}" "$LOCAL_REPORT"
docker exec "$CONTAINER" rm -f "$REMOTE" "$REMOTE_REPORT" 2>/dev/null || true

echo "Comparison output in HDFS:"
docker exec "$NAMENODE" hdfs dfs -ls -h /user/bigdata/ids2017/results/model_comparison_all

echo "HTML report saved locally:"
echo "  $LOCAL_REPORT"
echo "Done."
