# 05_submit_features.ps1 -- submit Member 2 feature engineering job to Spark
# Run from project root:
# .\scripts\05_submit_features.ps1

$CONTAINER = "spark-master"
$NAMENODE = "namenode"
$SCRIPT = Join-Path (Get-Location) "05_feature_engineering.py"
$REMOTE = "/tmp/05_feature_engineering.py"

# Check spark-master
$containers = docker ps --format "{{.Names}}"
if ($containers -notcontains $CONTAINER) {
    Write-Host "ERROR: spark-master is not running. Start containers first:"
    Write-Host "  cd path\to\docker-hadoop-spark-jupyter"
    Write-Host "  docker compose up -d"
    exit 1
}

# Check namenode
if ($containers -notcontains $NAMENODE) {
    Write-Host "ERROR: namenode is not running."
    exit 1
}

# Check script exists
if (!(Test-Path $SCRIPT)) {
    Write-Host "ERROR: 05_feature_engineering.py not found at $SCRIPT"
    exit 1
}

# Check Member 1 cleaned data exists
docker exec $NAMENODE hdfs dfs -test -e /user/bigdata/ids2017/processed/cleaned
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Member 1 cleaned data not found in HDFS."
    Write-Host "Run Member 1 cleaning job first:"
    Write-Host "  .\scripts\03_submit.ps1"
    exit 1
}

Write-Host "Copying Member 2 script to container..."
docker cp $SCRIPT "${CONTAINER}:${REMOTE}"

Write-Host "Submitting Member 2 feature engineering job..."
docker exec $CONTAINER /spark/bin/spark-submit `
    --master spark://spark-master:7077 `
    --deploy-mode client `
    --driver-memory 512m `
    --executor-memory 1500m `
    --conf "spark.executor.cores=1" `
    --conf "spark.sql.shuffle.partitions=4" `
    --conf "spark.pyspark.python=python3" `
    $REMOTE

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Member 2 spark-submit failed."
    exit 1
}

docker exec $CONTAINER rm -f $REMOTE 2>$null

Write-Host "Member 2 output in HDFS:"
docker exec $NAMENODE hdfs dfs -ls -h /user/bigdata/ids2017/processed/ml_ready_binary

Write-Host "Done."