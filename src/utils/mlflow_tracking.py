class MlflowTracker:

    def __init__(self, experiment_name: str):
        # MLflow is optional: import it lazily so importing this module never
        # requires mlflow to be installed/importable.
        import mlflow
        mlflow.set_experiment(experiment_name)

    def start_run(self, run_name: str = None):
        import mlflow
        return mlflow.start_run(run_name=run_name)
    
    def log_params(self, params: dict):
        import mlflow
        mlflow.log_params(params)

    def log_metrics(self, metrics: dict):
        import mlflow
        mlflow.log_metrics(metrics)

    def log_model(self, model, artifact_path="model"):
        import mlflow.xgboost
        mlflow.xgboost.log_model(model, artifact_path)

    def log_artifact(self, file_path: str):
        import mlflow
        mlflow.log_artifact(file_path)