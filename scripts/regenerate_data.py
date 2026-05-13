#!/usr/bin/env python3
"""Regenerate synthetic data and rebuild features"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.generator import EcommerceDataGenerator
from src.features.feature_builder import FeatureBuilder
from src.utils.logger import get_logger
import yaml

logger = get_logger(__name__)

def main():
    logger.info("=" * 60)
    logger.info("Regenerating Synthetic Data with Stronger Price Signals")
    logger.info("=" * 60)
    
    # Generate new data
    logger.info("Step 1: Generating synthetic sales data...")
    gen = EcommerceDataGenerator(n_products=100, days=365)
    df = gen.generate_sales()
    gen.save(df)
    
    logger.info(f"Generated {len(df)} sales records")
    logger.info(f"Price range: ${df['our_price'].min():.0f} - ${df['our_price'].max():.0f}")
    logger.info(f"Units sold range: {df['units_sold'].min():.0f} - {df['units_sold'].max():.0f}")
    
    # Build features
    logger.info("\nStep 2: Building features...")
    with open("configs/config.yaml") as f:
        config = yaml.safe_load(f)
    
    builder = FeatureBuilder(config)
    raw_df = builder.load_raw()
    feature_df = builder.build_features(raw_df)
    builder.save_features(feature_df)
    
    logger.info(f"Built {len(feature_df)} training samples")
    logger.info(f"Features: {len([c for c in feature_df.columns if c not in ['product_id', 'date', 'y_units_sold']])}")
    
    logger.info("\n" + "=" * 60)
    logger.info("Data regeneration complete!")
    logger.info("=" * 60)
    logger.info("\nNext steps:")
    logger.info("  1. Run training: python3 scripts/train_with_tuning.py")
    logger.info("  2. Check improved metrics in reports/training_metrics.json")

if __name__ == "__main__":
    main()
