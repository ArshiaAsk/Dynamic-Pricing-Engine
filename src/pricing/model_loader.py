import mlflow
import mlflow.xgboost

MODEL_NAME = "demand_forecasting_model"
MLFLOW_TRACKING_URI = "http://localhost:5000"

def load_production_model():
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    model_uri = f"models:/{MODEL_NAME}/Production"
    return mlflow.xgboost.load_model(model_uri)
