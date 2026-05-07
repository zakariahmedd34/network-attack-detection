# 02_upload_hdfs.ps1 -- upload CSVs from data\raw\CSVs\ to HDFS
# Run from project root: .\scripts\02_upload_hdfs.ps1

$ErrorActionPreference = "Stop"

$LOCAL = ".\data\raw\CSVs"
$HDFS  = "/user/bigdata/ids2017/raw"

$running = docker ps --format "{{.Names}}"
if ($running -notcontains "namenode") {
    Write-Host "ERROR: namenode is not running. Start containers first:"
    Write-Host "  cd 'C:\Users\Zakaria\Downloads\docker-hadoop-spark-jupyter\docker-hadoop-spark-jupyter'"
    Write-Host "  docker compose up -d"
    exit 1
}

docker exec namenode hdfs dfs -mkdir -p $HDFS

$files = @(
    "thursday_benign.csv",
    "dos_hulk.csv", "ddos_loit.csv", "dos_golden_eye.csv",
    "dos_slowhttptest.csv", "dos_slowloris.csv",
    "ftp_patator.csv", "ssh_patator-new.csv",
    "portscan.csv", "botnet_ares.csv", "heartbleed.csv",
    "web_brute_force.csv", "web_xss.csv", "web_sql_injection.csv"
)

foreach ($f in $files) {
    $exists = docker exec namenode hdfs dfs -test -e "$HDFS/$f" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "SKIP $f (already in HDFS)"
        continue
    }
    Write-Host "Uploading $f ..."
    docker cp "$LOCAL\$f" "namenode:/tmp/$f"
    docker exec namenode hdfs dfs -put "/tmp/$f" "$HDFS/$f"
    docker exec namenode rm "/tmp/$f"
}

Write-Host "Done. HDFS contents:"
docker exec namenode hdfs dfs -du -s -h $HDFS
