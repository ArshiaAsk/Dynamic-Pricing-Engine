MODEL_NAME = "demand_forecasting_model"
MLFLOW_TRACKING_URI = "http://localhost:5000"

def load_production_model():
    # MLflow is optional: import it lazily so importing this module never
    # requires mlflow to be installed/importable.
    import mlflow
    import mlflow.xgboost

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    model_uri = f"models:/{MODEL_NAME}/Production"
    return mlflow.xgboost.load_model(model_uri)
