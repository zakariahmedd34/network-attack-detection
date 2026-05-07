# 03_submit.ps1 -- submit the cleaning job to Spark
# Run from project root: .\scripts\03_submit.ps1

$ErrorActionPreference = "Stop"

$CONTAINER = "spark-master"
$NAMENODE  = "namenode"
$SCRIPT    = Join-Path (Split-Path $PSScriptRoot -Parent) "04_clean.py"
$REMOTE    = "/tmp/04_clean.py"

$running = docker ps --format "{{.Names}}"

if ($running -notcontains $CONTAINER) {
    Write-Host "ERROR: spark-master is not running. Start containers first:"
    Write-Host "  cd 'C:\Users\Zakaria\Downloads\docker-hadoop-spark-jupyter\docker-hadoop-spark-jupyter'"
    Write-Host "  docker compose up -d"
    exit 1
}
if ($running -notcontains $NAMENODE) {
    Write-Host "ERROR: namenode is not running."
    exit 1
}
if (-not (Test-Path $SCRIPT)) {
    Write-Host "ERROR: 04_clean.py not found at $SCRIPT"
    exit 1
}

Write-Host "Copying script to container..."
docker cp $SCRIPT "${CONTAINER}:${REMOTE}"

Write-Host "Submitting job (takes ~5-10 min)..."
docker exec $CONTAINER /spark/bin/spark-submit `
    --master spark://spark-master:7077 `
    --deploy-mode client `
    --driver-memory 512m `
    --executor-memory 1500m `
    --conf "spark.executor.cores=1" `
    --conf "spark.sql.shuffle.partitions=4" `
    --conf "spark.pyspark.python=python3" `
    $REMOTE

$exitCode = $LASTEXITCODE
docker exec $CONTAINER rm -f $REMOTE 2>$null

if ($exitCode -ne 0) {
    Write-Host "ERROR: spark-submit failed (exit $exitCode)"
    exit 1
}

Write-Host "Output in HDFS:"
docker exec $NAMENODE hdfs dfs -ls -h /user/bigdata/ids2017/processed/cleaned
Write-Host "Done."
