"""Training-support loading and serving validation (DECISIONS D32).

``models/training_support.json`` is written by training from the train split
(see ``src/training/support.py``). Serving:

* loads it at startup and fails loudly when it is missing or invalid;
* rejects a request whose competitor price or price bounds lie outside the
  observed support, with field-level errors;
* derives the default price bounds and the history-feature defaults from it.

No numeric support value is hardcoded here: every bound comes from the file.
"""
import json
from pathlib import Path
from typing import Dict, List, Tuple

# Lag and rolling unit features whose serving default is the training median.
HISTORY_FEATURES = (
    "lag_units_sold_1",
    "lag_units_sold_7",
    "lag_units_sold_14",
    "roll_mean_units_7",
    "roll_mean_units_14",
    "roll_mean_units_28",
    "roll_std_units_7",
    "roll_std_units_14",
    "roll_std_units_28",
)

# Relative tolerance for boundary comparisons: a value exactly on a support
# limit is accepted; anything further outside is rejected.
REL_TOL = 1e-9

ERROR_TYPE = "outside_training_support"


class TrainingSupportError(ValueError):
    """The training-support artifact is missing or invalid."""


def _check_stats(name: str, stats) -> None:
    if not isinstance(stats, dict) or not {"min", "max", "median"} <= set(stats):
        raise TrainingSupportError(
            f"Training support entry {name!r} must carry min, max and median"
        )
    if not stats["min"] <= stats["median"] <= stats["max"]:
        raise TrainingSupportError(
            f"Training support entry {name!r} has min > median > max: {stats}"
        )


def load_training_support(path) -> Dict:
    """Load and validate the training-support artifact.

    Raises:
        TrainingSupportError: the file is missing, unreadable, not JSON, or does
            not describe a train-split support with the required entries.
    """
    path = Path(path)
    try:
        data = json.loads(path.read_text())
    except FileNotFoundError:
        raise TrainingSupportError(
            f"Training support artifact not found: {path}"
        ) from None
    except (OSError, json.JSONDecodeError) as exc:
        raise TrainingSupportError(
            f"Cannot read training support {path}: {exc}"
        ) from None

    if data.get("split") != "train":
        raise TrainingSupportError(
            f"Training support {path} must be computed from the 'train' split; "
            f"got {data.get('split')!r}"
        )
    if not isinstance(data.get("n_rows"), int) or data["n_rows"] <= 0:
        raise TrainingSupportError(f"Training support {path} has no positive n_rows")

    features = data.get("features")
    if not isinstance(features, dict) or not features:
        raise TrainingSupportError(f"Training support {path} has no features map")

    for name, stats in features.items():
        _check_stats(name, stats)
    for name in ("price", "competitor_price", "price_ratio"):
        if name not in data:
            raise TrainingSupportError(f"Training support {path} is missing {name!r}")
        _check_stats(name, data[name])
    missing = [name for name in HISTORY_FEATURES if name not in features]
    if missing:
        raise TrainingSupportError(
            f"Training support {path} misses history features: {missing}"
        )
    return data


def history_defaults(support: Dict) -> Dict[str, float]:
    """Training medians for the lag and rolling unit features."""
    return {
        name: float(support["features"][name]["median"])
        for name in HISTORY_FEATURES
    }


def default_price_bounds(competitor_price: float, support: Dict) -> Tuple[float, float]:
    """Default price bounds: the observed price_ratio support around the competitor."""
    ratio = support["price_ratio"]
    return (
        float(ratio["min"]) * competitor_price,
        float(ratio["max"]) * competitor_price,
    )


def _below(value: float, bound: float) -> bool:
    return value < bound - REL_TOL * max(1.0, abs(bound))


def _above(value: float, bound: float) -> bool:
    return value > bound + REL_TOL * max(1.0, abs(bound))


def validate_price_support(
    competitor_price: float,
    price_min: float,
    price_max: float,
    support: Dict,
) -> List[Dict]:
    """Return field-level errors for a request outside the training support.

    Empty list means the request is inside the support. The price bounds must
    lie in ``[ratio_min * competitor_price, ratio_max * competitor_price]``,
    using the stored values exactly (relative tolerance ``REL_TOL``).
    """
    errors = []
    competitor = support["competitor_price"]
    if _below(competitor_price, competitor["min"]) or _above(
        competitor_price, competitor["max"]
    ):
        errors.append({
            "field": "competitor_price",
            "message": (
                f"competitor_price {competitor_price} is outside the training "
                f"support [{competitor['min']}, {competitor['max']}]"
            ),
            "type": ERROR_TYPE,
        })

    ratio = support["price_ratio"]
    lower = float(ratio["min"]) * competitor_price
    upper = float(ratio["max"]) * competitor_price
    for field, value in (("price_min", price_min), ("price_max", price_max)):
        if _below(value, lower) or _above(value, upper):
            errors.append({
                "field": field,
                "message": (
                    f"{field} {value} is outside the training support "
                    f"[{lower}, {upper}] (price_ratio support "
                    f"[{ratio['min']}, {ratio['max']}] x competitor_price "
                    f"{competitor_price})"
                ),
                "type": ERROR_TYPE,
            })

    if not errors and price_min >= price_max:
        errors.append({
            "field": "price_max",
            "message": "price_max must be greater than price_min",
            "type": ERROR_TYPE,
        })
    return errors
