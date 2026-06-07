import mlflow
from mlflow.tracking import MlflowClient

MODEL_NAME = "demand_forecasting_model"


def promote_to_stage(stage: str):
    mlflow.set_tracking_uri("http://localhost:5000")

    client = MlflowClient()

    latest_versions = client.get_latest_versions(
        MODEL_NAME,
        stages=["None"]
    )

    if not latest_versions:
        print("No new model versions found")
        return
    
    version = latest_versions[0].version

    print(f"Promoting model version {version} to {stage}")

    client.transition_model_version_stage(
        name=MODEL_NAME,
        version=version,
        stage=stage
    )

    print("Promotion completed")



if __name__ == "__main__":
    promote_to_stage("Staging")