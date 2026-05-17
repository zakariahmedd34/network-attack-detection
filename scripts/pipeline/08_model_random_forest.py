from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.ml.classification import RandomForestClassifier
from pyspark.ml.evaluation import (
    BinaryClassificationEvaluator,
    MulticlassClassificationEvaluator
)


HDFS_INPUT = "hdfs://namenode:9000/user/bigdata/ids2017/processed/ml_ready_binary"
HDFS_OUTPUT = "hdfs://namenode:9000/user/bigdata/ids2017/results/model_c_random_forest"

BASELINE_METRICS = {
    "accuracy": 0.9585880108125299,
    "f1": 0.9584670602051522,
    "auc_roc": 0.9781193521671149,
}


def evaluate(predictions):
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

    auc_eval = BinaryClassificationEvaluator(
        labelCol="label",
        rawPredictionCol="rawPrediction",
        metricName="areaUnderROC"
    )

    return {
        "accuracy": accuracy_eval.evaluate(predictions),
        "precision": precision_eval.evaluate(predictions),
        "recall": recall_eval.evaluate(predictions),
        "f1": f1_eval.evaluate(predictions),
        "auc_roc": auc_eval.evaluate(predictions),
    }


spark = (
    SparkSession.builder
    .appName("IDS2017-RandomForest")
    .master("spark://spark-master:7077")
    .config("spark.executor.memory", "1500m")
    .config("spark.executor.cores", "1")
    .config("spark.driver.memory", "512m")
    .config("spark.sql.shuffle.partitions", "4")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("WARN")

print("READING ML-READY DATASET...")

df = spark.read.parquet(HDFS_INPUT)

print("Dataset loaded!")
print("Rows:", df.count())

train_df, test_df = df.randomSplit([0.8, 0.2], seed=42)

print("Training rows:", train_df.count())
print("Testing rows :", test_df.count())

rf = RandomForestClassifier(
    featuresCol="features",
    labelCol="label",
    numTrees=80,
    maxDepth=12,
    maxBins=32,
    seed=42,
    featureSubsetStrategy="sqrt",
    impurity="gini"
)

print("Training model: Random Forest...")

model = rf.fit(train_df)

predictions = model.transform(test_df).cache()

metrics = evaluate(predictions)

print("========== MODEL C: RANDOM FOREST RESULTS ==========")
print("Accuracy :", metrics["accuracy"])
print("Precision:", metrics["precision"])
print("Recall   :", metrics["recall"])
print("F1 Score :", metrics["f1"])
print("AUC ROC  :", metrics["auc_roc"])

print("========== COMPARISON WITH MODEL A: LOGISTIC REGRESSION ==========")
print("Baseline Accuracy:", BASELINE_METRICS["accuracy"])
print("Random Forest Accuracy:", metrics["accuracy"])
print("Accuracy Change       :", metrics["accuracy"] - BASELINE_METRICS["accuracy"])
print("Baseline F1           :", BASELINE_METRICS["f1"])
print("Random Forest F1      :", metrics["f1"])
print("F1 Change             :", metrics["f1"] - BASELINE_METRICS["f1"])
print("Baseline AUC ROC      :", BASELINE_METRICS["auc_roc"])
print("Random Forest AUC ROC :", metrics["auc_roc"])
print("AUC ROC Change        :", metrics["auc_roc"] - BASELINE_METRICS["auc_roc"])

print("========== CONFUSION MATRIX ==========")
predictions.groupBy("label", "prediction").count().orderBy("label", "prediction").show()

metrics_df = spark.createDataFrame(
    [
        ("Model A - Logistic Regression", "accuracy", BASELINE_METRICS["accuracy"]),
        ("Model A - Logistic Regression", "f1", BASELINE_METRICS["f1"]),
        ("Model A - Logistic Regression", "auc_roc", BASELINE_METRICS["auc_roc"]),
        ("Model C - Random Forest", "accuracy", metrics["accuracy"]),
        ("Model C - Random Forest", "precision", metrics["precision"]),
        ("Model C - Random Forest", "recall", metrics["recall"]),
        ("Model C - Random Forest", "f1", metrics["f1"]),
        ("Model C - Random Forest", "auc_roc", metrics["auc_roc"]),
    ],
    ["model", "metric", "value"]
)

confusion_df = (
    predictions
    .groupBy("label", "prediction")
    .count()
    .withColumn("label", F.col("label").cast("double"))
    .withColumn("prediction", F.col("prediction").cast("double"))
)

print("Saving predictions, metrics, and confusion matrix...")

predictions.select("features", "label", "label_original", "prediction", "probability").write.mode("overwrite").parquet(
    f"{HDFS_OUTPUT}/predictions"
)

metrics_df.write.mode("overwrite").parquet(f"{HDFS_OUTPUT}/metrics")
confusion_df.write.mode("overwrite").parquet(f"{HDFS_OUTPUT}/confusion_matrix")

print("Results saved!")
print("Output path:", HDFS_OUTPUT)

predictions.unpersist()
spark.stop()
