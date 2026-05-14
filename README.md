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

## Important Running Rule

Use two different folders:

| Folder | Used for |
|---|---|
| `docker-hadoop-spark-jupyter/docker-hadoop-spark-jupyter` | Starting the Docker Hadoop/Spark/Jupyter cluster only |
| `network-attack-detection` | Running all project scripts |

So normally you:

1. Start the cluster from the Docker cluster folder.
2. Go back to the project repo folder.
3. Run project scripts from the project repo folder.

---

## Running the Pipeline (Member 1 task)

### Step 1 — Start the cluster

**Windows:**
```powershell
cd "C:\path\to\docker-hadoop-spark-jupyter\docker-hadoop-spark-jupyter"
docker compose up -d
```

**Mac/Linux:**
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

**Mac/Linux:**
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

**Mac/Linux:**
```bash
bash scripts/03_submit.sh
```

Takes about 5–10 minutes. When done it prints the label distribution and saves the cleaned data to HDFS as Parquet.

---

### Optional Jupyter Notebook (Member 1 EDA walkthrough)

Copy the notebook into the Jupyter container folder:

**Windows:**
```powershell
Copy-Item ".\notebook\04_cleaning.ipynb" "C:\path\to\docker-hadoop-spark-jupyter\docker-hadoop-spark-jupyter\notebooks\04_cleaning.ipynb"
```

**Mac/Linux:**
```bash
cp notebook/04_cleaning.ipynb ~/path/to/docker-hadoop-spark-jupyter/docker-hadoop-spark-jupyter/notebooks/
```

Open your browser at `http://localhost:8888`.

To get the login token:

**Windows PowerShell:**
```powershell
docker logs jupyter 2>&1 | Select-String "token="
```

**Mac/Linux:**
```bash
docker logs jupyter 2>&1 | grep "token="
```

---

## For Members 2–5 — Where to Start After Member 1

After Member 1 runs the pipeline, the cleaned data is available at:

```text
hdfs://namenode:9000/user/bigdata/ids2017/processed/cleaned
```

Read it in any PySpark notebook or script:

```python
from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .master("spark://spark-master:7077") \
    .config("spark.executor.memory", "1500m") \
    .config("spark.executor.cores", "1") \
    .config("spark.driver.memory", "512m") \
    .config("spark.sql.shuffle.partitions", "4") \
    .getOrCreate()

df = spark.read.parquet("hdfs://namenode:9000/user/bigdata/ids2017/processed/cleaned")
df.printSchema()
```

**Dataset info after Member 1 cleaning:**

| Property | Value |
|---|---|
| Rows | 785,583 |
| Columns | 122 |
| Column names | snake_case, e.g. `bytes_rate`, `fwd_packets_count` |
| Feature type | Double |
| Label column | `label` string |

**Label values after Member 1 cleaning:**

| Label | Count |
|---|---:|
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

> `WEB_ATTACK` combines three original classes: Web Brute Force, XSS, and SQL Injection.

---

## Member 2 — Preprocessing Part B + Feature Engineering

Member 2 starts from Member 1's cleaned Parquet output:

```text
hdfs://namenode:9000/user/bigdata/ids2017/processed/cleaned
```

Member 2 creates the final machine-learning-ready dataset for Members 3 and 4.

### Member 2 Main File

```text
05_feature_engineering.py
```

### Member 2 Tasks

- Read the cleaned Parquet data from HDFS.
- Preserve the original multiclass label in `label_original`.
- Convert the target into binary classification:
  - `BENIGN` → `0.0`
  - any attack type → `1.0`
- Create engineered network-flow features:
  - `total_packets`
  - `total_payload_bytes`
  - `avg_payload_per_packet`
  - `fwd_bwd_packet_ratio`
  - `log_duration`
  - `log_bytes_rate`
  - `log_packets_rate`
- Select all numeric columns using Spark numeric data types.
- Convert numeric columns to `double`.
- Convert NaN values to null.
- Handle outliers using percentile capping:
  - values below the 1st percentile are capped
  - values above the 99th percentile are capped
- Fill remaining missing numeric values with `0.0`.
- Assemble all numeric feature columns into one Spark MLlib vector column named `features`.
- Save the final ML-ready dataset to HDFS.

### Run Member 2 Job

Run from the `network-attack-detection` project folder.

**Windows:**
```powershell
.\scripts\05_submit_features.ps1
```

**Mac/Linux:**
```bash
bash scripts/05_submit_features.sh
```

Mac/Linux users may need to make the script executable first:

```bash
chmod +x scripts/05_submit_features.sh
```

### Member 2 Output

Member 2 saves the ML-ready dataset at:

```text
hdfs://namenode:9000/user/bigdata/ids2017/processed/ml_ready_binary
```

Final output columns:

| Column | Description |
|---|---|
| `features` | Spark MLlib vector containing all numeric features |
| `label` | Binary target label: `0.0 = BENIGN`, `1.0 = ATTACK` |
| `label_original` | Original attack type before binary conversion |

Check that the output exists:

```bash
docker exec namenode hdfs dfs -ls -h /user/bigdata/ids2017/processed/ml_ready_binary
```

If the folder contains `_SUCCESS` and `.parquet` files, Member 2 completed successfully.

### Optional Jupyter Notebook (Member 2 walkthrough)

A walkthrough notebook is included for explanation/demo:

```text
notebook/05_feature_engineering.ipynb
```

Copy it into the Jupyter notebooks folder.

**Windows:**
```powershell
Copy-Item ".\notebook\05_feature_engineering.ipynb" "C:\path\to\docker-hadoop-spark-jupyter\docker-hadoop-spark-jupyter\notebooks\05_feature_engineering.ipynb"
```

**Mac/Linux:**
```bash
cp notebook/05_feature_engineering.ipynb ~/path/to/docker-hadoop-spark-jupyter/docker-hadoop-spark-jupyter/notebooks/
```

Open Jupyter at:

```text
http://localhost:8888
```

The notebook is optional. The main executable implementation is `05_feature_engineering.py`.

---

## For Members 3 and 4 — Start Modeling

Members 3 and 4 should start from the ML-ready dataset produced by Member 2:

```text
hdfs://namenode:9000/user/bigdata/ids2017/processed/ml_ready_binary
```

This dataset already contains:

- `features`
- `label`
- `label_original`

So modeling members do not need to repeat cleaning, binary label conversion, missing-value handling, outlier handling, or feature vector assembly.

### Step 1 — Check that ML-ready data exists

Run from the project folder after the cluster is running:

```bash
docker exec namenode hdfs dfs -ls -h /user/bigdata/ids2017/processed/ml_ready_binary
```

If the folder exists and contains `_SUCCESS`, start modeling directly.

If it does not exist, run Member 2 first:

**Windows:**
```powershell
.\scripts\05_submit_features.ps1
```

**Mac/Linux:**
```bash
bash scripts/05_submit_features.sh
```

If Member 1 cleaned data also does not exist, run the full pipeline:

**Windows:**
```powershell
.\scripts\02_upload_hdfs.ps1
.\scripts\03_submit.ps1
.\scripts\05_submit_features.ps1
```

**Mac/Linux:**
```bash
bash scripts/02_upload_hdfs.sh
bash scripts/03_submit.sh
bash scripts/05_submit_features.sh
```

### Step 2 — Read the ML-ready dataset in PySpark

```python
from pyspark.sql import SparkSession

spark = (
    SparkSession.builder
    .appName("IDS2017-Modeling")
    .master("spark://spark-master:7077")
    .config("spark.executor.memory", "1500m")
    .config("spark.executor.cores", "1")
    .config("spark.driver.memory", "512m")
    .config("spark.sql.shuffle.partitions", "4")
    .getOrCreate()
)

df = spark.read.parquet("hdfs://namenode:9000/user/bigdata/ids2017/processed/ml_ready_binary")

df.printSchema()
df.groupBy("label").count().show()
df.show(5, truncate=False)
```

Expected schema:

```text
features: vector
label: double
label_original: string
```

### Suggested Member 3 Work

Member 3 should build the baseline model.

Suggested files:

```text
06_model_baseline.py
scripts/06_submit_baseline.ps1
scripts/06_submit_baseline.sh
```

Suggested baseline models:

- Logistic Regression
- Decision Tree

Suggested result path:

```text
hdfs://namenode:9000/user/bigdata/ids2017/results/model_a_baseline
```

Member 3 should report baseline evaluation metrics such as accuracy, precision, recall, F1-score, and AUC-ROC.

### Suggested Member 4 Work

Member 4 should build the improved model and compare it with Model A.

Suggested files:

```text
07_model_improved.py
scripts/07_submit_improved.ps1
scripts/07_submit_improved.sh
```

Suggested improved models:

- Random Forest
- Tuned Decision Tree
- Gradient-Boosted Tree, if suitable

Suggested result path:

```text
hdfs://namenode:9000/user/bigdata/ids2017/results/model_b_improved
```

Member 4 should compare Model A and Model B using:

- Accuracy
- Precision
- Recall
- F1-score
- AUC-ROC

---

## For Member 5 — Integration + Visualization + Pipeline Execution

Member 5 should verify that the whole pipeline runs end-to-end and prepare final visual outputs.

Suggested inputs:

```text
hdfs://namenode:9000/user/bigdata/ids2017/processed/ml_ready_binary
hdfs://namenode:9000/user/bigdata/ids2017/results/model_a_baseline
hdfs://namenode:9000/user/bigdata/ids2017/results/model_b_improved
```

Suggested work:

- Verify that the full pipeline can run from raw CSVs to final results.
- Build visualizations for dataset distribution and model metrics.
- Compare Model A and Model B visually.
- Prepare charts/dashboard outputs for the final presentation.
- Confirm final HDFS outputs and file paths.

Suggested visualizations:

- Original attack type distribution
- Binary BENIGN vs ATTACK distribution
- Model A vs Model B metric comparison
- Confusion matrix visualization
- ROC/AUC comparison, if available

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
├── 04_clean.py                         <- Member 1 Spark cleaning job
├── 05_feature_engineering.py           <- Member 2 feature engineering job
├── scripts/
│   ├── 02_upload_hdfs.ps1              <- Upload CSVs to HDFS (Windows)
│   ├── 02_upload_hdfs.sh               <- Upload CSVs to HDFS (Mac/Linux)
│   ├── 03_submit.ps1                   <- Run Member 1 cleaning job (Windows)
│   ├── 03_submit.sh                    <- Run Member 1 cleaning job (Mac/Linux)
│   ├── 05_submit_features.ps1          <- Run Member 2 feature engineering job (Windows)
│   └── 05_submit_features.sh           <- Run Member 2 feature engineering job (Mac/Linux)
├── notebook/
│   ├── 04_cleaning.ipynb               <- Member 1 EDA + cleaning walkthrough
│   └── 05_feature_engineering.ipynb    <- Member 2 feature engineering walkthrough
└── data/
    └── raw/
        └── CSVs/                       <- dataset goes here (not in git)
```

---

## Common Issues

**Docker says containers are not running**

Make sure Docker Desktop is open and the green icon shows it is running. Then run `docker compose up -d` from the cluster folder.

---

**Permission denied on Mac/Linux when running `.sh` scripts**

```bash
chmod +x scripts/02_upload_hdfs.sh scripts/03_submit.sh scripts/05_submit_features.sh
```

---

**HDFS already has old data from a previous run**

The upload script skips existing files automatically. If you need a clean HDFS:

```bash
docker exec namenode hdfs dfs -rm -r /user/bigdata/ids2017
```

Then run the upload script again.

---

**Jupyter token not showing**

**Windows PowerShell:**
```powershell
docker logs jupyter 2>&1 | Select-String "token="
```

**Mac/Linux:**
```bash
docker logs jupyter 2>&1 | grep "token="
```

---

**PySpark ML error: `ModuleNotFoundError: No module named 'numpy'`**

Install NumPy inside the Spark containers:

```bash
docker exec spark-master bash -lc "apk add --no-cache py3-numpy"
docker exec spark-worker-1 bash -lc "apk add --no-cache py3-numpy"
```

Then rerun the Spark job.

---

**Member 2 says cleaned data is missing**

Check Member 1 output:

```bash
docker exec namenode hdfs dfs -ls -h /user/bigdata/ids2017/processed/cleaned
```

If it does not exist, run Member 1 first:

**Windows:**
```powershell
.\scripts\02_upload_hdfs.ps1
.\scripts\03_submit.ps1
```

**Mac/Linux:**
```bash
bash scripts/02_upload_hdfs.sh
bash scripts/03_submit.sh
```

---

**Members 3 or 4 cannot find `ml_ready_binary`**

Check Member 2 output:

```bash
docker exec namenode hdfs dfs -ls -h /user/bigdata/ids2017/processed/ml_ready_binary
```

If it does not exist, run Member 2:

**Windows:**
```powershell
.\scripts\05_submit_features.ps1
```

**Mac/Linux:**
```bash
bash scripts/05_submit_features.sh
```
