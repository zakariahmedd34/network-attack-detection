docker cp .\scripts\pipeline\06_model_baseline.py spark-master:/tmp/06_model_baseline.py

docker exec spark-master bash -lc "
export PYSPARK_PYTHON=python3 && \
export PYSPARK_DRIVER_PYTHON=python3 && \
/spark/bin/spark-submit \
--master spark://spark-master:7077 \
/tmp/06_model_baseline.py
"
