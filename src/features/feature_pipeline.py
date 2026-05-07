# src/pipelines/feature_pipeline.py
from src.utils.config import load_config
from src.features.feature_builder import FeatureBuilder
from src.utils.logger import get_logger

logger = get_logger(__name__)

def run_feature_pipeline():
    logger.info("Starting feature pipeline...")
    config = load_config("configs/config.yaml")
    fb = FeatureBuilder(config)

    raw_df = fb.load_raw(filename=config["features"].get("raw_filename", "ecommerce_sales.csv"))
    feat_df = fb.build_features(raw_df)
    fb.save_features(feat_df, filename=config["features"].get("feature_filename", "training_features.parquet"))
    logger.info("Feature pipeline completed successfully.")

if __name__ == "__main__":
    run_feature_pipeline()
