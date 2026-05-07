# 04_clean.py  -- \Data Ingestion & Cleaning
# Run via: .\scripts\03_submit.ps1

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType

HDFS_RAW       = "hdfs://namenode:9000/user/bigdata/ids2017/raw"
HDFS_PROCESSED = "hdfs://namenode:9000/user/bigdata/ids2017/processed/cleaned"

NON_NEGATIVE_COLS = [
    "duration", "fwd_packets_count", "bwd_packets_count",
    "fwd_total_payload_bytes", "bwd_total_payload_bytes",
    "bytes_rate", "packets_rate",
]

spark = (
    SparkSession.builder
    .appName("IDS2017-Cleaning")
    .master("spark://spark-master:7077")
    .config("spark.executor.memory", "1500m")
    .config("spark.executor.cores", "1")
    .config("spark.driver.memory", "512m")
    .config("spark.sql.shuffle.partitions", "4")
    .getOrCreate()
)
spark.sparkContext.setLogLevel("WARN")


# Step 1 -- Load
print("Step 1: Loading CSVs from HDFS")
df = spark.read.csv(HDFS_RAW, header=True, inferSchema=False,
                    ignoreLeadingWhiteSpace=True, ignoreTrailingWhiteSpace=True)
raw_rows = df.count()
print("  rows: " + str(raw_rows) + "  cols: " + str(len(df.columns)))


# Step 2 -- Fix column names
print("Step 2: Fixing column names")
seen, new_names = set(), []
for c in df.columns:
    s = c.strip()
    if s not in seen:
        new_names.append(s)
        seen.add(s)
dupes = len(df.columns) - len(new_names)
df = df.toDF(*new_names) if dupes == 0 else df.select(
    [F.col(df.columns[i]).alias(new_names[i]) for i in range(len(new_names))])
print("  dupes dropped: " + str(dupes) + "  cols: " + str(len(df.columns)))


# Step 3 -- Replace Infinity with null and cast to Double
print("Step 3: Casting to Double, replacing Infinity -> null")
INF = ["Infinity", "-Infinity", "inf", "-inf"]
df = df.select([
    F.col(c) if c == "label"
    else F.when(F.col(c).isin(INF), None).otherwise(F.col(c).cast(DoubleType())).alias(c)
    for c in df.columns
])


# Step 4 -- Deduplication skipped
# CICFlowMeter produces one row per flow; no real duplicates exist.
print("Step 4: Dedup skipped (no true duplicates in CICFlowMeter output)")


# Step 5 -- Remove impossible negative values (lazy)
print("Step 5: Filtering negative values")
cond = None
for c in NON_NEGATIVE_COLS:
    if c in df.columns:
        cond = (F.col(c) < 0) if cond is None else cond | (F.col(c) < 0)
if cond is not None:
    df = df.filter(~cond)


# Step 6 -- Standardize labels (lazy)
print("Step 6: Standardizing labels")
df = df.withColumn("label", F.trim(F.upper(F.col("label"))))
df = df.withColumn("label",
    F.when(F.col("label").contains("WEB"), "WEB_ATTACK").otherwise(F.col("label")))


# Step 7 -- Write Parquet (triggers full pipeline)
print("Step 7: Writing Parquet to HDFS...")
df.write.mode("overwrite").parquet(HDFS_PROCESSED)

df_out = spark.read.parquet(HDFS_PROCESSED)
final_rows = df_out.count()
print("\nLabel distribution:")
df_out.groupBy("label").count().orderBy(F.desc("count")).show(20, truncate=False)

print("Raw:   " + str(raw_rows))
print("Final: " + str(final_rows))
print("Done -- output: " + HDFS_PROCESSED)

spark.stop()
