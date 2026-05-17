import mlflow
import mlflow.xgboost



class MlflowTracker:

    def __init__(self, experiment_name: str):
        mlflow.set_experiment(experiment_name)

    def start_run(self, run_name: str = None):
        return mlflow.start_run(run_name=run_name)
    
    def log_params(self, params: dict):
        mlflow.log_params(params)

    def log_metrics(self, metrics: dict):
        mlflow.log_metrics(metrics)

    def log_model(self, model, artifact_path="model"):
        mlflow.xgboost.log_model(model, artifact_path)

    def log_artifact(self, file_path: str):
        mlflow.log_artifact(file_path)