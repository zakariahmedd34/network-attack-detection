from pyspark.sql import SparkSession
from pyspark.ml.classification import LogisticRegression
from pyspark.ml.evaluation import (
    BinaryClassificationEvaluator,
    MulticlassClassificationEvaluator
)

spark = (
    SparkSession.builder
    .appName("IDS2017-Baseline")
    .master("spark://spark-master:7077")
    .config("spark.executor.memory", "1500m")
    .config("spark.executor.cores", "1")
    .config("spark.driver.memory", "512m")
    .config("spark.sql.shuffle.partitions", "4")
    .getOrCreate()
)

print("READING ML-READY DATASET...")

df = spark.read.parquet(
    "hdfs://namenode:9000/user/bigdata/ids2017/processed/ml_ready_binary"
)

print("Dataset loaded!")

train_df, test_df = df.randomSplit([0.8, 0.2], seed=42)

print("Training rows:", train_df.count())
print("Testing rows :", test_df.count())

lr = LogisticRegression(
    featuresCol="features",
    labelCol="label",
    maxIter=10
)

print("Training model...")

model = lr.fit(train_df)

predictions = model.transform(test_df)

accuracy_eval = MulticlassClassificationEvaluator(
    labelCol="label",
    predictionCol="prediction",
    metricName="accuracy"
)

accuracy = accuracy_eval.evaluate(predictions)

f1_eval = MulticlassClassificationEvaluator(
    labelCol="label",
    predictionCol="prediction",
    metricName="f1"
)

f1 = f1_eval.evaluate(predictions)

auc_eval = BinaryClassificationEvaluator(
    labelCol="label",
    rawPredictionCol="rawPrediction",
    metricName="areaUnderROC"
)

auc = auc_eval.evaluate(predictions)

print("========== RESULTS ==========")

print("Accuracy:", accuracy)
print("F1 Score:", f1)
print("AUC ROC :", auc)

predictions.write.mode("overwrite").parquet(
    "hdfs://namenode:9000/user/bigdata/ids2017/results/model_a_baseline"
)

print("Results saved!")

spark.stop()