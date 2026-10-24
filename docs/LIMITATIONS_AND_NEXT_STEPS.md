# Limitations and next steps

This document is current-state documentation. Every limitation is backed by code, a test
or a measured artifact. All data in this project is **synthetic**.

## A. Limitations

### The demand model is observational

The model is trained on historical price/demand pairs produced by the synthetic generator.
It has never seen a controlled price experiment. It therefore learns the associations
present in that data, including the generator's own demand equation
(`src/data/generator.py`), not a causal response that would transfer to a real market.

### A revenue-maximizing price is not a causal pricing policy

`argmax_price E[units | price]` is not a valid causal policy on real data. In real data,
prices are set in response to demand, competitors and inventory, so the estimated price
response can be confounded. The optimizer maximizes the model's conditional expectation; it
does not estimate what would happen under an intervention. The README states this, and
`tests/test_readme_limitations.py` keeps the statement in place.

### All data and metrics are synthetic

`scripts/regenerate_data.py` generates every row with `src/data/generator.py`. The seed-42
metrics (R² 0.4193, MAPE 0.3509) describe how well the model learns that generator. They are
not evidence of real-world accuracy.

### The served price range is far outside the training distribution

The generator draws base prices from 200,000 to 5,000,000; the generated file spans roughly
240,000 to 5,930,000. The API's default price range is 30.0 to 120.0
(`configs/config.yaml`), and the README example uses 70 to 110. The model therefore
extrapolates on every default request. The ratio and log features soften this, but the
absolute price features are outside their training range.

### The model's explanatory power is modest

On the seed-42 synthetic validation split the model reaches R² 0.4193 and MAPE 0.3509
(`reports/training_metrics.json`, generated). Across seeds 1–10 the README records R²
0.447 ± 0.029, so the result varies materially with the data draw.

### Rate limiting is in memory and per worker

`RateLimitMiddleware` keeps a per-client-IP sliding window in process memory
(`src/api/middleware.py`). Limits are not shared across workers and reset on restart. With
`API_WORKERS > 1`, each worker enforces its own limit.

### No authentication, authorization or TLS

The API is unauthenticated and serves plain HTTP. CORS is enabled by default with
`CORS_ORIGINS` defaulting to `*` (`src/api/server.py`). Do not expose it to an untrusted
network.

### The model artifact is a version-tied pickle

`models/demand_model.pkl` is a joblib-serialized `XGBRegressor`. Loading an artifact
produced by a different XGBoost version can warn or fail. Retrain after upgrading the
dependency stack.

### The MLflow registry is optional and requires explicit promotion

With no promoted `production` alias (or `stage=Production` tag), the engine serves the
local pickle. Promotion is a manual step (`scripts/promote_model.py`). The fallback is
logged at ERROR and visible as `checks.model.source == "local"`, but it is still a
fallback, not a guarantee that the newest model is served.

### There is no drift monitoring and no automated retraining

Drift detection and performance monitoring were removed. Retraining is manual, and nothing
compares live traffic with the training distribution.

### There is no experiment or A/B capability

The demo returns a recommendation. It cannot split traffic, measure incremental revenue or
attribute an outcome to a price change.

### Hyperparameter tuning is not covered by the test suite

`scripts/train_with_tuning.py` imports MLflow eagerly and requires a reachable tracking
server. No test runs it; it is only reachable in the import graph. The plain training path
is the tested one.

## B. Open observations

These are proven facts that were noticed but not changed in the P2 batch.

1. **Transitive dependencies are unpinned, and a default change already broke an image
   once.** `requirements.txt` pins direct dependencies only. `Dockerfile.mlflow` pins
   `mlflow`, `protobuf` and `psycopg2-binary`, but SQLAlchemy arrives transitively. SQLAlchemy
   2.1 changed bare `postgresql://` to resolve to psycopg 3, which broke the MLflow
   container until the URI named `+psycopg2` (commit `0aeb1be`). Any future default change
   in a transitive package can do the same.
2. **The `__main__` block of `src/api/server.py` is uncovered.** The measured coverage is
   89% for that file, with lines 97–102 missing; the block is only exercised when the module
   is run as a script. The README records 98% for the whole `src/api` package.
3. **The pickle is tied to the installed XGBoost version.** This is a consequence of joblib
   serialization, not a bug, but it makes the artifact non-portable across upgrades.
4. **The engine is constructed at import time.** `src/api/router.py` opens the config and
   builds `PricingEngine` when the module is imported. A missing model or feature contract
   therefore raises during import, before any request; a fresh clone must build the
   artifacts first.
5. **The served price range versus the training range is a modelling gap, not only a
   documentation one.** It is listed under limitations above because it affects every
   default request.
6. **The rate limiter keys on the client IP.** Behind a proxy or load balancer, all clients
   may share one bucket unless the proxy forwards a trustworthy client address.

## C. Parked Phase 3 plan

This plan was parked at the end of P2 and is **not started**. It is written as a spec so it
can be picked up without re-deriving the intent.

### C.1 Machine learning

1. **Compute the noise ceiling of the synthetic generator.** Use the generator's noise-free
   expected demand as an oracle and report oracle R² and MAPE. This puts the model's R²
   0.4193 and MAPE 0.3509 in context: a model cannot beat the noise the generator injects.
2. **Add baselines.** Compare XGBoost with (a) a mean-per-product baseline and (b) a
   log-log elasticity regression. Report the same metrics on the same split.
3. **Try a monotonic constraint on price.** XGBoost supports monotone constraints; measure
   how often predicted demand rises with price before and after the constraint.
4. **Evaluate decisions, not only predictions.** Compute regret against the generator's true
   optimum and uplift against the historical price. A model with a modest R² can still make
   useful decisions, or fail to; this measures which.
5. **Run a feature-group ablation.** Remove calendar, price, lag and rolling groups in turn
   and report the metric change.
6. **Report multiple seeds.** Use the seeds-1–10 protocol already used for the README, with
   mean and spread, and keep seed 42 as the reference run.
7. **Check training/serving skew.** Compare the feature frame built by
   `src/features/feature_builder.py` with the one built by `src/pricing/features.py` for the
   same request, and assert equality where the serving path has the inputs.

### C.2 Product

1. **Define the user and the decision.** Name who receives the recommendation (for example,
   a category manager) and what decision it changes (the list price for the next period).
2. **Define the success metric.** Revenue uplift versus a baseline policy, measured on a
   holdout or an experiment, not on the training distribution.
3. **Define guardrails.** A maximum price change per period, a minimum margin, and an
   inventory cap. The optimizer already supports a margin floor and an inventory cap; a
   price-change guardrail does not exist yet.
4. **Explain a recommendation.** Show the input features, the candidate revenue curve and
   the binding constraint (margin, inventory or bounds). The UI currently shows the result,
   not the reasoning.
5. **Write an experiment plan.** Unit of randomization, sample size, duration, primary and
   guardrail metrics, and the analysis method.
6. **Optionally replace synthetic data with a public retail dataset that has real price
   variation.** Check the licence before use, and re-run the audit's honesty checks on the
   new data.

### C.3 Stop rule

Stop the phase if any of these is true:

- the oracle noise ceiling shows the model is already at the generator's noise floor, so
  further modelling cannot improve the synthetic result;
- the decision-level evaluation shows no positive uplift over the historical price on a
  held-out period;
- the product success metric cannot be defined without an experiment that the demo cannot
  run;
- a public dataset cannot be used under an acceptable licence.

In those cases, record the negative result and keep the demo's claims at their current
level rather than adding a new capability.

## D. Phase 3 diagnostics

Phase 3 diagnostics have **not been run**. No oracle R², regret, uplift or ablation results
exist in this repository. The plan above is the specification for running them.
