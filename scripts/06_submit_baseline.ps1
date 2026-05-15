docker cp .\06_model_baseline.py spark-master:/tmp/06_model_baseline.py

docker exec spark-master /spark/bin/spark-submit `
--master spark://spark-master:7077 `
/tmp/06_model_baseline.py