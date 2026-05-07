import yaml
from pathlib import Path

from src.training.pipeline import TrainingPipeline


CONFIG_PATH = Path("configs/config.yaml")


def load_config():

    with open(CONFIG_PATH) as f:

        config = yaml.safe_load(f)

    return config


if __name__ == "__main__":

    config = load_config()

    pipeline = TrainingPipeline(config)

    pipeline.run()
