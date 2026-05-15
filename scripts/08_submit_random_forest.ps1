# 08_submit_random_forest.ps1 -- submit Random Forest model job to Spark
# Run from project root:
# .\scripts\08_submit_random_forest.ps1

$CONTAINER = "spark-master"
$NAMENODE = "namenode"
$SCRIPT = Join-Path (Get-Location) "08_model_random_forest.py"
$REMOTE = "/tmp/08_model_random_forest.py"

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
    Write-Host "ERROR: 08_model_random_forest.py not found at $SCRIPT"
    exit 1
}

docker exec $NAMENODE hdfs dfs -test -e /user/bigdata/ids2017/processed/ml_ready_binary
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: ML-ready dataset not found in HDFS."
    Write-Host "Run Member 2 feature engineering first:"
    Write-Host "  .\scripts\05_submit_features.ps1"
    exit 1
}

Write-Host "Copying Random Forest script to container..."
docker cp $SCRIPT "${CONTAINER}:${REMOTE}"

Write-Host "Submitting Random Forest job..."
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
    Write-Host "ERROR: Random Forest spark-submit failed."
    exit 1
}

docker exec $CONTAINER rm -f $REMOTE 2>$null

Write-Host "Random Forest output in HDFS:"
docker exec $NAMENODE hdfs dfs -ls -h /user/bigdata/ids2017/results/model_c_random_forest

Write-Host "Done."
