#!/bin/bash
# 02_upload_hdfs.sh -- upload CSVs from data/raw/CSVs/ to HDFS
# Run from project root: bash scripts/02_upload_hdfs.sh

set -e

LOCAL="./data/raw/CSVs"
HDFS="/user/bigdata/ids2017/raw"

if ! docker ps --format "{{.Names}}" | grep -q "namenode"; then
    echo "ERROR: namenode is not running. Start containers first:"
    echo "  cd path/to/docker-hadoop-spark-jupyter"
    echo "  docker compose up -d"
    exit 1
fi

docker exec namenode hdfs dfs -mkdir -p "$HDFS"

FILES=(
    "thursday_benign.csv"
    "dos_hulk.csv" "ddos_loit.csv" "dos_golden_eye.csv"
    "dos_slowhttptest.csv" "dos_slowloris.csv"
    "ftp_patator.csv" "ssh_patator-new.csv"
    "portscan.csv" "botnet_ares.csv" "heartbleed.csv"
    "web_brute_force.csv" "web_xss.csv" "web_sql_injection.csv"
)

for f in "${FILES[@]}"; do
    if docker exec namenode hdfs dfs -test -e "$HDFS/$f" 2>/dev/null; then
        echo "SKIP $f (already in HDFS)"
        continue
    fi
    echo "Uploading $f ..."
    docker cp "$LOCAL/$f" "namenode:/tmp/$f"
    docker exec namenode hdfs dfs -put "/tmp/$f" "$HDFS/$f"
    docker exec namenode rm "/tmp/$f"
done

echo "Done. HDFS contents:"
docker exec namenode hdfs dfs -du -s -h "$HDFS"
