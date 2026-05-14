#!/bin/bash
# 05_submit_features.sh -- submit Member 2 feature engineering job to Spark
# Run from project root:
# bash scripts/05_submit_features.sh

set -e

CONTAINER="spark-master"
NAMENODE="namenode"
SCRIPT="$(cd "$(dirname "$0")/.." && pwd)/05_feature_engineering.py"
REMOTE="/tmp/05_feature_engineering.py"

if ! docker ps --format "{{.Names}}" | grep -q "$CONTAINER"; then
    echo "ERROR: spark-master is not running. Start containers first:"
    echo "  cd path/to/docker-hadoop-spark-jupyter"
    echo "  docker compose up -d"
    exit 1
fi

if ! docker ps --format "{{.Names}}" | grep -q "$NAMENODE"; then
    echo "ERROR: namenode is not running."
    exit 1
fi

if [ ! -f "$SCRIPT" ]; then
    echo "ERROR: 05_feature_engineering.py not found at $SCRIPT"
    exit 1
fi

if ! docker exec "$NAMENODE" hdfs dfs -test -e /user/bigdata/ids2017/processed/cleaned; then
    echo "ERROR: Member 1 cleaned data not found in HDFS."
    echo "Run Member 1 cleaning job first:"
    echo "  bash scripts/03_submit.sh"
    exit 1
fi

echo "Copying Member 2 script to container..."
docker cp "$SCRIPT" "$CONTAINER:$REMOTE"

echo "Submitting Member 2 feature engineering job..."
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

echo "Member 2 output in HDFS:"
docker exec "$NAMENODE" hdfs dfs -ls -h /user/bigdata/ids2017/processed/ml_ready_binary

echo "Done."