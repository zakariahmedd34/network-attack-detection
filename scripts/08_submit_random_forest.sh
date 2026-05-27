#!/usr/bin/env bash
set -euo pipefail

# 08_submit_random_forest.sh -- submit Random Forest model job to Spark
# Run from project root:
# bash scripts/08_submit_random_forest.sh

CONTAINER="spark-master"
NAMENODE="namenode"
SCRIPT="$(pwd)/08_model_random_forest.py"
REMOTE="/tmp/08_model_random_forest.py"

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
    echo "ERROR: 08_model_random_forest.py not found at $SCRIPT"
    exit 1
fi

if ! docker exec "$NAMENODE" hdfs dfs -test -e /user/bigdata/ids2017/processed/ml_ready_binary; then
    echo "ERROR: ML-ready dataset not found in HDFS."
    echo "Run the feature engineering job first:"
    echo "  bash scripts/05_submit_features.sh"
    exit 1
fi

echo "Copying Random Forest script to container..."
docker cp "$SCRIPT" "${CONTAINER}:${REMOTE}"

echo "Submitting Random Forest job..."
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

echo "Random Forest output in HDFS:"
docker exec "$NAMENODE" hdfs dfs -ls -h /user/bigdata/ids2017/results/model_c_random_forest

echo "Done."
