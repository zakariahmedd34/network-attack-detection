# 09_submit_compare_all.ps1 -- compare Logistic Regression, Deep Learning, and Random Forest
# Run from project root after all three model jobs:
# .\scripts\09_submit_compare_all.ps1

$CONTAINER = "spark-master"
$NAMENODE = "namenode"
$SCRIPT = Join-Path (Get-Location) "09_compare_all_models.py"
$REMOTE = "/tmp/09_compare_all_models.py"
$REMOTE_REPORT = "/tmp/model_comparison_report.html"
$LOCAL_REPORT_DIR = Join-Path (Get-Location) "reports"
$LOCAL_REPORT = Join-Path $LOCAL_REPORT_DIR "model_comparison_report.html"

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
    Write-Host "ERROR: 09_compare_all_models.py not found at $SCRIPT"
    exit 1
}

$requiredPaths = @(
    "/user/bigdata/ids2017/results/model_a_baseline",
    "/user/bigdata/ids2017/results/model_b_deep_learning/predictions",
    "/user/bigdata/ids2017/results/model_c_random_forest/predictions"
)

foreach ($path in $requiredPaths) {
    docker exec $NAMENODE hdfs dfs -test -e $path
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Missing required model output in HDFS: $path"
        Write-Host "Run the model jobs before comparing all three."
        exit 1
    }
}

Write-Host "Copying comparison script to container..."
docker cp $SCRIPT "${CONTAINER}:${REMOTE}"

Write-Host "Submitting all-model comparison job..."
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
    Write-Host "ERROR: model comparison spark-submit failed."
    exit 1
}

if (!(Test-Path $LOCAL_REPORT_DIR)) {
    New-Item -ItemType Directory -Path $LOCAL_REPORT_DIR | Out-Null
}

docker cp "${CONTAINER}:${REMOTE_REPORT}" $LOCAL_REPORT
docker exec $CONTAINER rm -f $REMOTE $REMOTE_REPORT 2>$null

Write-Host "Comparison output in HDFS:"
docker exec $NAMENODE hdfs dfs -ls -h /user/bigdata/ids2017/results/model_comparison_all

Write-Host "HTML report saved locally:"
Write-Host "  $LOCAL_REPORT"
Write-Host "Done."
