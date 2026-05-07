# Network Attack Detection — CSCI461 Big Data

## Team

| Member | Task |
|---|---|
| Member 1 | Data Ingestion + Preprocessing |
| Member 2 | Preprocessing Part B + Feature Engineering |
| Member 3 | Model A — Baseline |
| Member 4 | Model B (Improved) + Comparison |
| Member 5 | Integration + Visualization + Pipeline Execution |

---

## Setup (do this once)

### 1. Install Docker Desktop
- Windows: https://docs.docker.com/desktop/install/windows-install/
- Mac: https://docs.docker.com/desktop/install/mac-install/

Make sure Docker Desktop is running before any of the steps below.

### 2. Clone the repo
```bash
git clone https://github.com/zakariahmedd34/network-attack-detection.git
cd network-attack-detection
```

### 3. Get the Hadoop + Spark cluster folder
Download the `docker-hadoop-spark-jupyter` folder from the shared Google Drive (same link as the CSVs). Place it anywhere on your machine — you just need to know the path.

### 4. Get the dataset CSVs
Download the 14 CSV files from the shared Google Drive link (sent in the group chat, ~600 MB total). Put all files inside:

```
network-attack-detection/
└── data/
    └── raw/
        └── CSVs/        <-- all 14 .csv files go here
```

---

## Running the Pipeline (Member 1 task)

### Step 1 — Start the cluster

**Windows:**
```powershell
cd "C:\path\to\docker-hadoop-spark-jupyter\docker-hadoop-spark-jupyter"
docker compose up -d
```

**Mac:**
```bash
cd ~/path/to/docker-hadoop-spark-jupyter/docker-hadoop-spark-jupyter
docker compose up -d
```

Wait about 30 seconds, then confirm everything started:
```bash
docker ps
```
You should see at minimum: `namenode`, `datanode`, `spark-master`, `spark-worker`, `jupyter`.

---

### Step 2 — Upload CSVs to HDFS

Open a terminal in the `network-attack-detection` folder.

**Windows:**
```powershell
.\scripts\02_upload_hdfs.ps1
```

**Mac:**
```bash
bash scripts/02_upload_hdfs.sh
```

This copies the 14 CSVs into HDFS inside the cluster. It skips any file already there, so it is safe to run again.

---

### Step 3 — Run the cleaning job

**Windows:**
```powershell
.\scripts\03_submit.ps1
```

**Mac:**
```bash
bash scripts/03_submit.sh
```

Takes about 5–10 minutes. When done it prints the label distribution and saves the cleaned data to HDFS as Parquet.

---

### Jupyter Notebook (EDA walkthrough)

Copy the notebook into the Jupyter container folder:

**Windows:**
```powershell
Copy-Item ".\notebook\04_cleaning.ipynb" "C:\path\to\docker-hadoop-spark-jupyter\docker-hadoop-spark-jupyter\notebooks\04_cleaning.ipynb"
```

**Mac:**
```bash
cp notebook/04_cleaning.ipynb ~/path/to/docker-hadoop-spark-jupyter/docker-hadoop-spark-jupyter/notebooks/
```

Open your browser at `http://localhost:8888`. To get the login token:
```bash
docker logs jupyter 2>&1 | grep token
```

---

## For Members 2–5 — Where to Start

After Member 1 runs the pipeline, the cleaned data is available at:

```
hdfs://namenode:9000/user/bigdata/ids2017/processed/cleaned
```

Read it in any PySpark notebook or script:

```python
spark = SparkSession.builder \
    .master("local[*]") \
    .config("spark.hadoop.fs.defaultFS", "hdfs://namenode:9000") \
    .getOrCreate()

df = spark.read.parquet("hdfs://namenode:9000/user/bigdata/ids2017/processed/cleaned")
df.printSchema()
```

**Dataset info:**

| Property | Value |
|---|---|
| Rows | 785,583 |
| Columns | 122 |
| Column names | snake_case (e.g. `bytes_rate`, `fwd_packets_count`) |
| Feature type | Double |
| Label column | `label` (string) |

**Label values:**

| Label | Count |
|---|---|
| DOS_HULK | 349,240 |
| PORT_SCAN | 161,323 |
| BENIGN | 133,770 |
| DDOS_LOIT | 95,733 |
| FTP-PATATOR | 9,531 |
| DOS_GOLDENEYE | 8,364 |
| DOS_SLOWHTTPTEST | 6,860 |
| SSH-PATATOR | 5,949 |
| BOTNET_ARES | 5,508 |
| DOS_SLOWLORIS | 5,177 |
| WEB_ATTACK | 4,116 |
| HEARTBLEED | 12 |

> WEB_ATTACK combines three original classes: Web Brute Force, XSS, and SQL Injection.

---

## Useful URLs (while cluster is running)

| Service | URL |
|---|---|
| Jupyter | http://localhost:8888 |
| HDFS browser | http://localhost:9870 |
| Spark UI | http://localhost:8080 |

---

## File Structure

```
network-attack-detection/
├── 04_clean.py                  <- Spark cleaning job
├── scripts/
│   ├── 02_upload_hdfs.ps1       <- Upload CSVs to HDFS (Windows)
│   ├── 02_upload_hdfs.sh        <- Upload CSVs to HDFS (Mac)
│   ├── 03_submit.ps1            <- Run cleaning job (Windows)
│   └── 03_submit.sh             <- Run cleaning job (Mac)
├── notebook/
│   └── 04_cleaning.ipynb        <- EDA + step-by-step cleaning walkthrough
└── data/
    └── raw/
        └── CSVs/                <- dataset goes here (not in git)
```

---

## Common Issues

**Docker says containers are not running**
Make sure Docker Desktop is open and the green icon shows it is running. Then run `docker compose up -d` from the cluster folder.

**Permission denied on Mac when running .sh scripts**
```bash
chmod +x scripts/02_upload_hdfs.sh scripts/03_submit.sh
```

**HDFS already has old data from a previous run**
The upload script skips existing files automatically. If you need a clean HDFS:
```bash
docker exec namenode hdfs dfs -rm -r /user/bigdata/ids2017
```
Then run the upload script again.

**Jupyter token not showing**
```bash
docker logs jupyter 2>&1 | grep "token="
```
