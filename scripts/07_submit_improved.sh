#!/usr/bin/env bash
set -euo pipefail

# 07_submit_improved.sh -- submit Member 4 improved model job to Spark
# Run from project root:
# bash scripts/07_submit_improved.sh

CONTAINER="spark-master"
NAMENODE="namenode"
SCRIPT="$(pwd)/07_model_improved.py"
REMOTE="/tmp/07_model_improved.py"

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
    echo "ERROR: 07_model_improved.py not found at $SCRIPT"
    exit 1
fi

if ! docker exec "$NAMENODE" hdfs dfs -test -e /user/bigdata/ids2017/processed/ml_ready_binary; then
    echo "ERROR: ML-ready dataset not found in HDFS."
    echo "Run Member 2 feature engineering first:"
    echo "  bash scripts/05_submit_features.sh"
    exit 1
fi

echo "Copying Member 4 improved model script to container..."
docker cp "$SCRIPT" "${CONTAINER}:${REMOTE}"

echo "Submitting Member 4 improved model job..."
docker exec "$CONTAINER" /spark/bin/spark-submit \
    --master spark://spark-master:7077 \
    --deploy-mode client \
    --driver-memory 512m \
    --executor-memory 1500m \
    --conf "spark.executor.cores=1" \
    --conf "spark.sql.shuffle.partitions=4" \
    --conf "spark.pyspark.python=python3" \
    "$REMOTE"

docker exec "$CONTAINER" rm -f "$REMOTE" 2>/dev/null || true

echo "Member 4 output in HDFS:"
docker exec "$NAMENODE" hdfs dfs -ls -h /user/bigdata/ids2017/results/model_b_improved

echo "Done."
