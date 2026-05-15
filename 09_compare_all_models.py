from html import escape

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.ml.evaluation import (
    BinaryClassificationEvaluator,
    MulticlassClassificationEvaluator
)


MODEL_PATHS = [
    (
        "Model A - Logistic Regression",
        "hdfs://namenode:9000/user/bigdata/ids2017/results/model_a_baseline"
    ),
    (
        "Model B - Deep Learning MLP",
        "hdfs://namenode:9000/user/bigdata/ids2017/results/model_b_deep_learning/predictions"
    ),
    (
        "Model C - Random Forest",
        "hdfs://namenode:9000/user/bigdata/ids2017/results/model_c_random_forest/predictions"
    ),
]

HDFS_OUTPUT = "hdfs://namenode:9000/user/bigdata/ids2017/results/model_comparison_all"
LOCAL_REPORT = "/tmp/model_comparison_report.html"


def evaluate_predictions(predictions):
    accuracy_eval = MulticlassClassificationEvaluator(
        labelCol="label",
        predictionCol="prediction",
        metricName="accuracy"
    )

    precision_eval = MulticlassClassificationEvaluator(
        labelCol="label",
        predictionCol="prediction",
        metricName="weightedPrecision"
    )

    recall_eval = MulticlassClassificationEvaluator(
        labelCol="label",
        predictionCol="prediction",
        metricName="weightedRecall"
    )

    f1_eval = MulticlassClassificationEvaluator(
        labelCol="label",
        predictionCol="prediction",
        metricName="f1"
    )

    raw_col = "rawPrediction" if "rawPrediction" in predictions.columns else "probability"
    auc_eval = BinaryClassificationEvaluator(
        labelCol="label",
        rawPredictionCol=raw_col,
        metricName="areaUnderROC"
    )

    return {
        "accuracy": accuracy_eval.evaluate(predictions),
        "precision": precision_eval.evaluate(predictions),
        "recall": recall_eval.evaluate(predictions),
        "f1": f1_eval.evaluate(predictions),
        "auc_roc": auc_eval.evaluate(predictions),
    }


def metric_bar_chart(metrics_by_model):
    metric_names = ["accuracy", "precision", "recall", "f1", "auc_roc"]
    colors = ["#2563eb", "#059669", "#dc2626"]
    width = 1120
    row_height = 42
    group_gap = 30
    label_width = 115
    chart_width = 650
    height = 60 + len(metric_names) * (row_height * 3 + group_gap)
    y = 35
    svg = [
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Model metrics bar chart">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<text x="0" y="20" font-size="18" font-weight="700" fill="#111827">Metric comparison</text>',
    ]

    for metric in metric_names:
        svg.append(
            f'<text x="0" y="{y + 18}" font-size="14" font-weight="700" fill="#111827">'
            f'{escape(metric.upper())}</text>'
        )
        for i, (model, model_metrics) in enumerate(metrics_by_model.items()):
            value = model_metrics[metric]
            bar_width = max(2, int(chart_width * value))
            row_y = y + 30 + (i * row_height)
            svg.append(f'<text x="{label_width}" y="{row_y + 17}" font-size="12" fill="#374151">{escape(model)}</text>')
            svg.append(
                f'<rect x="{label_width + 210}" y="{row_y}" width="{chart_width}" height="22" '
                f'rx="4" fill="#e5e7eb"/>'
            )
            svg.append(
                f'<rect x="{label_width + 210}" y="{row_y}" width="{bar_width}" height="22" '
                f'rx="4" fill="{colors[i % len(colors)]}"/>'
            )
            svg.append(
                f'<text x="{label_width + 220 + chart_width}" y="{row_y + 16}" '
                f'font-size="12" fill="#111827">{value:.4f}</text>'
            )
        y += row_height * 3 + group_gap

    svg.append("</svg>")
    return "\n".join(svg)


def confusion_heatmap(model, rows):
    counts = {(int(row["label"]), int(row["prediction"])): int(row["count"]) for row in rows}
    max_count = max(counts.values()) if counts else 1
    labels = [(0, "BENIGN"), (1, "ATTACK")]
    cell = 110
    offset_x = 155
    offset_y = 70
    width = 420
    height = 320

    svg = [
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{escape(model)} confusion matrix">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="0" y="22" font-size="17" font-weight="700" fill="#111827">{escape(model)}</text>',
        '<text x="190" y="48" font-size="13" font-weight="700" fill="#374151">Predicted</text>',
        '<text x="8" y="180" font-size="13" font-weight="700" fill="#374151" transform="rotate(-90 8 180)">Actual</text>',
    ]

    for col_idx, (_, pred_name) in enumerate(labels):
        svg.append(
            f'<text x="{offset_x + col_idx * cell + 18}" y="{offset_y - 12}" '
            f'font-size="12" fill="#374151">{pred_name}</text>'
        )

    for row_idx, (actual_value, actual_name) in enumerate(labels):
        svg.append(
            f'<text x="55" y="{offset_y + row_idx * cell + 60}" '
            f'font-size="12" fill="#374151">{actual_name}</text>'
        )
        for col_idx, (pred_value, _) in enumerate(labels):
            count = counts.get((actual_value, pred_value), 0)
            intensity = 0.15 + 0.75 * (count / max_count)
            blue = int(255 - 110 * intensity)
            green = int(255 - 65 * intensity)
            fill = f"rgb({blue},{green},255)"
            x = offset_x + col_idx * cell
            y = offset_y + row_idx * cell
            svg.append(f'<rect x="{x}" y="{y}" width="{cell - 8}" height="{cell - 8}" rx="6" fill="{fill}"/>')
            svg.append(
                f'<text x="{x + 52}" y="{y + 58}" text-anchor="middle" '
                f'font-size="18" font-weight="700" fill="#111827">{count}</text>'
            )

    svg.append("</svg>")
    return "\n".join(svg)


def build_report(metrics_by_model, confusion_by_model, best_model):
    metric_chart = metric_bar_chart(metrics_by_model)
    confusion_charts = "\n".join(
        f'<section class="panel">{confusion_heatmap(model, rows)}</section>'
        for model, rows in confusion_by_model.items()
    )

    rows = []
    for model, metrics in metrics_by_model.items():
        rows.append(
            "<tr>"
            f"<td>{escape(model)}</td>"
            f"<td>{metrics['accuracy']:.4f}</td>"
            f"<td>{metrics['precision']:.4f}</td>"
            f"<td>{metrics['recall']:.4f}</td>"
            f"<td>{metrics['f1']:.4f}</td>"
            f"<td>{metrics['auc_roc']:.4f}</td>"
            "</tr>"
        )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>IDS2017 Model Comparison</title>
  <style>
    body {{
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      color: #111827;
      background: #f8fafc;
    }}
    main {{
      max-width: 1120px;
      margin: 0 auto;
      padding: 32px 20px 48px;
    }}
    h1, h2 {{
      margin: 0 0 14px;
    }}
    .summary {{
      margin-bottom: 22px;
      padding: 16px 18px;
      border-left: 5px solid #2563eb;
      background: #ffffff;
    }}
    .panel {{
      margin: 18px 0;
      padding: 18px;
      border: 1px solid #e5e7eb;
      background: #ffffff;
      border-radius: 8px;
      overflow-x: auto;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: #ffffff;
    }}
    th, td {{
      padding: 11px 12px;
      border-bottom: 1px solid #e5e7eb;
      text-align: left;
      font-size: 14px;
    }}
    th {{
      background: #f1f5f9;
      font-weight: 700;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
      gap: 18px;
    }}
  </style>
</head>
<body>
  <main>
    <h1>IDS2017 Model Comparison</h1>
    <section class="summary">
      <strong>Best model by F1-score:</strong> {escape(best_model)}
    </section>

    <section class="panel">
      <h2>Metrics Table</h2>
      <table>
        <thead>
          <tr>
            <th>Model</th>
            <th>Accuracy</th>
            <th>Precision</th>
            <th>Recall</th>
            <th>F1</th>
            <th>AUC ROC</th>
          </tr>
        </thead>
        <tbody>
          {''.join(rows)}
        </tbody>
      </table>
    </section>

    <section class="panel">
      {metric_chart}
    </section>

    <h2>Confusion Matrices</h2>
    <div class="grid">
      {confusion_charts}
    </div>
  </main>
</body>
</html>
"""


spark = (
    SparkSession.builder
    .appName("IDS2017-Compare-All-Models")
    .master("spark://spark-master:7077")
    .config("spark.executor.memory", "1500m")
    .config("spark.executor.cores", "1")
    .config("spark.driver.memory", "512m")
    .config("spark.sql.shuffle.partitions", "4")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("WARN")

metrics_rows = []
confusion_rows = []
metrics_by_model = {}
confusion_by_model = {}

for model_name, path in MODEL_PATHS:
    print("Reading predictions for:", model_name)
    print("Path:", path)
    predictions = spark.read.parquet(path).cache()

    metrics = evaluate_predictions(predictions)
    metrics_by_model[model_name] = metrics

    for metric_name, value in metrics.items():
        metrics_rows.append((model_name, metric_name, float(value)))

    confusion = (
        predictions
        .groupBy("label", "prediction")
        .count()
        .withColumn("label", F.col("label").cast("double"))
        .withColumn("prediction", F.col("prediction").cast("double"))
        .orderBy("label", "prediction")
    )

    collected_confusion = confusion.collect()
    confusion_by_model[model_name] = collected_confusion

    for row in collected_confusion:
        confusion_rows.append(
            (model_name, float(row["label"]), float(row["prediction"]), int(row["count"]))
        )

    print("Metrics:", metrics)
    print("Confusion matrix:")
    confusion.show()

    predictions.unpersist()

best_model = max(metrics_by_model.items(), key=lambda item: item[1]["f1"])[0]

print("========== BEST MODEL BY F1 ==========")
print(best_model)

metrics_df = spark.createDataFrame(metrics_rows, ["model", "metric", "value"])
confusion_df = spark.createDataFrame(confusion_rows, ["model", "label", "prediction", "count"])

metrics_df.write.mode("overwrite").parquet(f"{HDFS_OUTPUT}/metrics")
confusion_df.write.mode("overwrite").parquet(f"{HDFS_OUTPUT}/confusion_matrix")

report_html = build_report(metrics_by_model, confusion_by_model, best_model)
with open(LOCAL_REPORT, "w", encoding="utf-8") as f:
    f.write(report_html)

print("Comparison tables saved to:", HDFS_OUTPUT)
print("HTML report saved to:", LOCAL_REPORT)

spark.stop()
