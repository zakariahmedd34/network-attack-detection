import os
import csv
from html import escape
from pyspark.sql import SparkSession

OUT = "/tmp/ids2017_readable_exports"
os.makedirs(OUT, exist_ok=True)

spark = (
    SparkSession.builder
    .appName("IDS2017-Export-Readable-Outputs")
    .master("spark://spark-master:7077")
    .config("spark.executor.memory", "1500m")
    .config("spark.executor.cores", "1")
    .config("spark.driver.memory", "512m")
    .config("spark.sql.shuffle.partitions", "4")
    .getOrCreate()
)
spark.sparkContext.setLogLevel("WARN")

paths = {
    "member1_cleaned": "hdfs://namenode:9000/user/bigdata/ids2017/processed/cleaned",
    "member2_ml_ready": "hdfs://namenode:9000/user/bigdata/ids2017/processed/ml_ready_binary",

    "model_a_predictions": "hdfs://namenode:9000/user/bigdata/ids2017/results/model_a_baseline",

    "model_b_predictions": "hdfs://namenode:9000/user/bigdata/ids2017/results/model_b_deep_learning/predictions",
    "model_b_metrics": "hdfs://namenode:9000/user/bigdata/ids2017/results/model_b_deep_learning/metrics",
    "model_b_confusion": "hdfs://namenode:9000/user/bigdata/ids2017/results/model_b_deep_learning/confusion_matrix",

    "model_c_predictions": "hdfs://namenode:9000/user/bigdata/ids2017/results/model_c_random_forest/predictions",
    "model_c_metrics": "hdfs://namenode:9000/user/bigdata/ids2017/results/model_c_random_forest/metrics",
    "model_c_confusion": "hdfs://namenode:9000/user/bigdata/ids2017/results/model_c_random_forest/confusion_matrix",

    "comparison_metrics": "hdfs://namenode:9000/user/bigdata/ids2017/results/model_comparison_all/metrics",
    "comparison_confusion": "hdfs://namenode:9000/user/bigdata/ids2017/results/model_comparison_all/confusion_matrix",
}

def read_parquet(key):
    try:
        print(f"Reading {key}: {paths[key]}")
        return spark.read.parquet(paths[key])
    except Exception as e:
        print(f"SKIPPED {key}: {e}")
        return None

def save_csv(df, filename, limit=None, preferred_cols=None):
    if df is None:
        return

    if preferred_cols:
        cols = [c for c in preferred_cols if c in df.columns]
        if cols:
            df = df.select(*cols)

    if limit:
        df = df.limit(limit)

    rows = df.collect()
    out_path = os.path.join(OUT, filename)

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(df.columns)
        for row in rows:
            writer.writerow([("" if row[c] is None else str(row[c])) for c in df.columns])

    print(f"Saved {filename} with {len(rows)} rows")

def save_schema(df, filename):
    if df is None:
        return

    out_path = os.path.join(OUT, filename)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("Columns:\n")
        for col_name, col_type in df.dtypes:
            f.write(f"- {col_name}: {col_type}\n")
        f.write("\nSchema:\n")
        f.write(df._jdf.schema().treeString())

    print(f"Saved {filename}")

# Member 1 and Member 2 readable samples
member1 = read_parquet("member1_cleaned")
save_schema(member1, "member1_cleaned_schema.txt")
save_csv(member1, "member1_cleaned_sample_50.csv", limit=50)

member2 = read_parquet("member2_ml_ready")
save_schema(member2, "member2_ml_ready_schema.txt")
save_csv(
    member2,
    "member2_ml_ready_sample_100.csv",
    limit=100,
    preferred_cols=["label_original", "label"]
)

# Model A baseline sample
model_a = read_parquet("model_a_predictions")
save_schema(model_a, "model_a_baseline_schema.txt")
save_csv(
    model_a,
    "model_a_baseline_prediction_sample_200.csv",
    limit=200,
    preferred_cols=["label_original", "label", "prediction", "probability", "rawPrediction"]
)

# Model B readable outputs
model_b_metrics = read_parquet("model_b_metrics")
model_b_confusion = read_parquet("model_b_confusion")
model_b_predictions = read_parquet("model_b_predictions")

save_csv(model_b_metrics, "model_b_deep_learning_metrics.csv")
save_csv(model_b_confusion, "model_b_deep_learning_confusion_matrix.csv")
save_csv(
    model_b_predictions,
    "model_b_deep_learning_prediction_sample_200.csv",
    limit=200,
    preferred_cols=["label_original", "label", "prediction", "probability"]
)

# Model C readable outputs
model_c_metrics = read_parquet("model_c_metrics")
model_c_confusion = read_parquet("model_c_confusion")
model_c_predictions = read_parquet("model_c_predictions")

save_csv(model_c_metrics, "model_c_random_forest_metrics.csv")
save_csv(model_c_confusion, "model_c_random_forest_confusion_matrix.csv")
save_csv(
    model_c_predictions,
    "model_c_random_forest_prediction_sample_200.csv",
    limit=200,
    preferred_cols=["label_original", "label", "prediction", "probability"]
)

# Final comparison readable outputs
comparison_metrics = read_parquet("comparison_metrics")
comparison_confusion = read_parquet("comparison_confusion")

save_csv(comparison_metrics, "final_model_comparison_metrics.csv")
save_csv(comparison_confusion, "final_model_comparison_confusion_matrix.csv")

# Simple HTML summary
metrics_rows = comparison_metrics.collect() if comparison_metrics is not None else []
confusion_rows = comparison_confusion.collect() if comparison_confusion is not None else []

html_rows = ""
for r in metrics_rows:
    html_rows += f"<tr><td>{escape(str(r['model']))}</td><td>{escape(str(r['metric']))}</td><td>{float(r['value']):.6f}</td></tr>"

conf_rows = ""
for r in confusion_rows:
    conf_rows += (
        f"<tr><td>{escape(str(r['model']))}</td>"
        f"<td>{escape(str(r['label']))}</td>"
        f"<td>{escape(str(r['prediction']))}</td>"
        f"<td>{escape(str(r['count']))}</td></tr>"
    )

html = f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>IDS2017 Readable Output Summary</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 30px; }}
table {{ border-collapse: collapse; width: 100%; margin-bottom: 30px; }}
th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
th {{ background: #f2f2f2; }}
</style>
</head>
<body>
<h1>IDS2017 Readable Output Summary</h1>

<h2>Final Model Metrics</h2>
<table>
<tr><th>Model</th><th>Metric</th><th>Value</th></tr>
{html_rows}
</table>

<h2>Final Confusion Matrices</h2>
<table>
<tr><th>Model</th><th>Actual Label</th><th>Predicted Label</th><th>Count</th></tr>
{conf_rows}
</table>
</body>
</html>
"""

with open(os.path.join(OUT, "readable_summary_report.html"), "w", encoding="utf-8") as f:
    f.write(html)

with open(os.path.join(OUT, "README_readable_outputs.txt"), "w", encoding="utf-8") as f:
    f.write("""Readable outputs exported from HDFS Parquet files.

This folder contains:
- CSV samples from Member 1 cleaned data
- CSV samples from Member 2 ML-ready data
- CSV prediction samples for Model A, Model B, and Model C
- CSV metrics and confusion matrices
- HTML summary report
- Schema TXT files

The original full outputs remain saved in HDFS as Parquet.
""")

print("Readable export finished:", OUT)
spark.stop()
