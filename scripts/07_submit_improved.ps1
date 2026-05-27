# 07_submit_improved.ps1 -- submit Deep Learning MLP model job to Spark
# Run from project root:
# .\scripts\07_submit_improved.ps1

$CONTAINER = "spark-master"
$NAMENODE = "namenode"
$SCRIPT = Join-Path (Get-Location) "07_model_improved.py"
$REMOTE = "/tmp/07_model_improved.py"

$containers = docker ps --format "{{.Names}}"
if ($containers -notcontains $CONTAINER) {
    Write-Host "ERROR: spark-master is not running. Start containers first:"
    Write-Host "  cd path\to\docker-hadoop-spark-jupyter"
    Write-Host "  docker compose up -d"
    exit 1
}

if ($containers -notcontains $NAMENODE) {
    Write-Host "ERROR: namenode is not running."
    exit 1
}

if (!(Test-Path $SCRIPT)) {
    Write-Host "ERROR: 07_model_improved.py not found at $SCRIPT"
    exit 1
}

docker exec $NAMENODE hdfs dfs -test -e /user/bigdata/ids2017/processed/ml_ready_binary
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: ML-ready dataset not found in HDFS."
    Write-Host "Run the feature engineering job first:"
    Write-Host "  .\scripts\05_submit_features.ps1"
    exit 1
}

Write-Host "Copying Deep Learning MLP script to container..."
docker cp $SCRIPT "${CONTAINER}:${REMOTE}"

Write-Host "Submitting Deep Learning MLP job..."
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
    Write-Host "ERROR: spark-submit failed."
    exit 1
}

docker exec $CONTAINER rm -f $REMOTE 2>$null

Write-Host "Deep Learning MLP output in HDFS:"
docker exec $NAMENODE hdfs dfs -ls -h /user/bigdata/ids2017/results/model_b_improved

Write-Host "Done."
