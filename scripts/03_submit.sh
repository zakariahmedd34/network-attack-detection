#!/bin/bash
# 03_submit.sh -- submit the cleaning job to Spark
# Run from project root: bash scripts/03_submit.sh

set -e

CONTAINER="spark-master"
NAMENODE="namenode"
SCRIPT="$(cd "$(dirname "$0")/.." && pwd)/04_clean.py"
REMOTE="/tmp/04_clean.py"

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
    echo "ERROR: 04_clean.py not found at $SCRIPT"
    exit 1
fi

echo "Copying script to container..."
docker cp "$SCRIPT" "$CONTAINER:$REMOTE"

echo "Submitting job (takes ~5-10 min)..."
set +e
docker exec "$CONTAINER" /spark/bin/spark-submit \
    --master spark://spark-master:7077 \
    --deploy-mode client \
    --driver-memory 512m \
    --executor-memory 1500m \
    --conf "spark.executor.cores=1" \
    --conf "spark.sql.shuffle.partitions=4" \
    --conf "spark.pyspark.python=python3" \
    "$REMOTE"
EXIT=$?
set -e
docker exec "$CONTAINER" rm -f "$REMOTE" 2>/dev/null || true

if [ $EXIT -ne 0 ]; then
    echo "ERROR: spark-submit failed (exit $EXIT)"
    exit 1
fi

echo "Output in HDFS:"
docker exec "$NAMENODE" hdfs dfs -ls -h /user/bigdata/ids2017/processed/cleaned
echo "Done."
