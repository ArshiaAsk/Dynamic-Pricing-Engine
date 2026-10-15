"""DECISIONS D30 / ROADMAP R25: the synthetic data generator is seeded.

``EcommerceDataGenerator(seed=...)`` must be deterministic: the same seed
produces identical frames, and different seeds produce different frames (so the
seed is not silently ignored). A small ``n_products``/``days`` keeps the whole
file to about a second.
"""
import pandas as pd

from src.data.generator import EcommerceDataGenerator

N_PRODUCTS = 4
DAYS = 10


def _frame(seed):
    gen = EcommerceDataGenerator(n_products=N_PRODUCTS, days=DAYS, seed=seed)
    return gen.generate_sales()


def test_same_seed_is_deterministic():
    """Same seed twice -> identical frames (``pd.testing.assert_frame_equal``)."""
    pd.testing.assert_frame_equal(_frame(42), _frame(42))


def test_different_seeds_differ():
    """Different seeds -> frames differ."""
    assert not _frame(42).equals(_frame(7))
