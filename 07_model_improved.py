from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.ml.classification import MultilayerPerceptronClassifier
from pyspark.ml.evaluation import (
    BinaryClassificationEvaluator,
    MulticlassClassificationEvaluator
)
from pyspark.ml.feature import StandardScaler


HDFS_INPUT = "hdfs://namenode:9000/user/bigdata/ids2017/processed/ml_ready_binary"
HDFS_OUTPUT = "hdfs://namenode:9000/user/bigdata/ids2017/results/model_b_deep_learning"

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
        rawPredictionCol="probability",
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
    .appName("IDS2017-Improved-DeepLearning")
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

scaler = StandardScaler(
    inputCol="features",
    outputCol="scaled_features",
    withStd=True,
    withMean=False
)

print("Fitting feature scaler...")

scaler_model = scaler.fit(train_df)
train_scaled = scaler_model.transform(train_df).cache()
test_scaled = scaler_model.transform(test_df).cache()

input_size = train_scaled.select("scaled_features").first()["scaled_features"].size
hidden_1 = min(128, max(32, input_size // 2))
hidden_2 = min(64, max(16, input_size // 4))
layers = [input_size, hidden_1, hidden_2, 2]

print("Neural network layers:", layers)

mlp = MultilayerPerceptronClassifier(
    featuresCol="scaled_features",
    labelCol="label",
    predictionCol="prediction",
    probabilityCol="probability",
    layers=layers,
    maxIter=80,
    blockSize=256,
    seed=42,
)

print("Training improved model: Multilayer Perceptron neural network...")

model = mlp.fit(train_scaled)

predictions = model.transform(test_scaled).cache()

metrics = evaluate(predictions)

print("========== MODEL B: DEEP LEARNING RESULTS ==========")
print("Accuracy :", metrics["accuracy"])
print("Precision:", metrics["precision"])
print("Recall   :", metrics["recall"])
print("F1 Score :", metrics["f1"])
print("AUC ROC  :", metrics["auc_roc"])

print("========== COMPARISON WITH MODEL A: LOGISTIC REGRESSION ==========")
print("Baseline Accuracy:", BASELINE_METRICS["accuracy"])
print("Improved Accuracy:", metrics["accuracy"])
print("Accuracy Change  :", metrics["accuracy"] - BASELINE_METRICS["accuracy"])
print("Baseline F1      :", BASELINE_METRICS["f1"])
print("Improved F1      :", metrics["f1"])
print("F1 Change        :", metrics["f1"] - BASELINE_METRICS["f1"])
print("Baseline AUC ROC :", BASELINE_METRICS["auc_roc"])
print("Improved AUC ROC :", metrics["auc_roc"])
print("AUC ROC Change   :", metrics["auc_roc"] - BASELINE_METRICS["auc_roc"])

print("========== CONFUSION MATRIX ==========")
predictions.groupBy("label", "prediction").count().orderBy("label", "prediction").show()

metrics_df = spark.createDataFrame(
    [
        ("Model A - Logistic Regression", "accuracy", BASELINE_METRICS["accuracy"]),
        ("Model A - Logistic Regression", "f1", BASELINE_METRICS["f1"]),
        ("Model A - Logistic Regression", "auc_roc", BASELINE_METRICS["auc_roc"]),
        ("Model B - Deep Learning MLP", "accuracy", metrics["accuracy"]),
        ("Model B - Deep Learning MLP", "precision", metrics["precision"]),
        ("Model B - Deep Learning MLP", "recall", metrics["recall"]),
        ("Model B - Deep Learning MLP", "f1", metrics["f1"]),
        ("Model B - Deep Learning MLP", "auc_roc", metrics["auc_roc"]),
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
train_scaled.unpersist()
test_scaled.unpersist()
spark.stop()
