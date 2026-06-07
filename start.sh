#!/bin/bash
set -e

# 1. Start MLflow server in background
mlflow server \
  --backend-store-uri sqlite:///mlflow.db \
  --default-artifact-root ./mlruns \
  --host 0.0.0.0 \
  --port 5000 &

# Wait until MLflow is ready
echo "Waiting for MLflow..."
until curl -sf http://localhost:5000/health > /dev/null 2>&1; do
  sleep 2
done
echo "MLflow is up."

# 2. Start uvicorn in background
uvicorn src.api.server:app --reload --host 0.0.0.0 --port 8000 &

# Wait until uvicorn is ready
echo "Waiting for uvicorn..."
until curl -sf http://localhost:8000/v1/health > /dev/null 2>&1; do
  sleep 2
done
echo "Uvicorn is up."

# 3. Start Streamlit in foreground (keeps container alive)
streamlit run app.py --server.port 7860
