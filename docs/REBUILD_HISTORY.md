# Rebuild history

This document is a historical record. It describes the audit that started the rebuild,
the method used, the 35 roadmap items and their final status, the incidents that shaped the
work, and the closure of phase P2. It may mention files that no longer exist; those
mentions describe the state at the time.

Current-state documentation is in [ARCHITECTURE.md](ARCHITECTURE.md),
[OPERATIONS.md](OPERATIONS.md) and [LIMITATIONS_AND_NEXT_STEPS.md](LIMITATIONS_AND_NEXT_STEPS.md).

## 1. Why: the original audit

The starting point was a technical audit preserved byte-for-byte in
[archive/AUDIT_ORIGINAL.md](archive/AUDIT_ORIGINAL.md). It compared the README's claims with
the code. The key findings:

| Claim | Reality found by the audit | Final state |
|---|---|---|
| XGBoost demand forecasting, ~49% R² | A real `XGBRegressor`, but trained on synthetic data; the "0.49" was a rounded, stale number. | Real model; seed-42 R² 0.4193, stated with MAPE and the seed spread. |
| "Time-series validation" | A random `train_test_split(..., shuffle=True)`, not a temporal split. | Chronological split with whole-day boundaries (D6, R12). |
| Bayesian optimization | No Bayesian library; `scipy.optimize.minimize(method="L-BFGS-B")` on a piecewise-constant tree objective. | Deleted; one dense grid search named `grid_search` (D1/D2, R1/R6). |
| Grid search | Crashed with a `KeyError` because it built 22 of the required columns. | One serving feature builder; complete 30-column frame (D4, R2/R4). |
| Business constraints | Margin and inventory code existed but ran on the broken optimizer. | Margin floor and inventory cap on the live path, tested. |
| Data drift detection | `ModelMonitor` was never imported or called. | Removed (D13, R15). |
| Log rotation | A plain `FileHandler`; rotation was a README `find` command. | Real size/daily rotation from env (R20). |
| Prometheus | `prometheus-client` was declared but never imported. | Removed; `/v1/metrics` is custom JSON. |
| Nginx reverse proxy | Compose mounted `./nginx/nginx.conf`, which did not exist. | Service removed (D17, R24). |
| AWS EC2 deployment and rollback | `deploy.sh` and `pre_deploy_check.sh` did not exist. | Claims removed (D19, R28). |
| CI/CD | No `.github/` directory or workflow. | Two-job GitHub Actions workflow (D18, R27). |
| SQLite database, backup and retention | `data.db` was an orphan; the API never touched it. | Ingestion chain and scripts deleted (D9, R22/R29). |
| Streamlit UI | Read `predicted_demand` while the API returned `expected_demand`; the Advanced tab shipped a fake response. | Contract test and real schema (D20, R10/R11). |
| Tests | 17 tests passed, but some tested dead classes and some asserted the bug. | Offline suite of 134 tests with an import-graph guard. |
| Docker | Images were real; the prod compose referenced missing nginx config and shipped no model. | One hardened image that builds its own model (D31, R25). |
| MLflow | Tracking was real; registry loading fell back silently; promotion used deprecated stage APIs. | Optional lazy registry, loud fallback, alias-based promotion (D7/D8, R5). |

The audit's conclusion was that the project was a learning prototype with a fake core and
aspirational documentation. The rebuild's guiding rule became: **make the headline
capability true before advertising it.**

## 2. Method

1. **Audit first.** Read source, trace imports and run the code; treat docs and comments as
   hypotheses. The result was a claim-by-claim state file with `CONFIRMED`, `PARTIAL`,
   `FAKE-OR-DEAD` and `NOT-FOUND` statuses.
2. **Plan in dependency order.** The findings became 35 roadmap items in three priority
   groups: P0 (core is fake or blocks everything), P1 (honesty, correctness, operability),
   P2 (polish and CI).
3. **One item at a time, one commit per item.** No branches, no amends, explicit-path
   staging.
4. **Test first where possible.** A regression test was shown to fail on the pre-fix code
   and pass after the fix. Acceptance criteria were commands or tests, never titles.
5. **Record evidence.** Each item carries the command, test name or commit that proves it.
6. **Flag, do not silently fix.** Out-of-scope findings were written down for a later item.

## 3. Outcome: R1–R35

All 35 items reached `done` against their written acceptance criteria. Priorities were
P0 = 8, P1 = 20, P2 = 7.

| ID | Title | Priority | Final status | Evidence pointer |
|---|---|---|---|---|
| R1 | Replace the non-functional "Bayesian" optimizer with a real search | P0 | done | `tests/test_optimizer_real.py::test_grid_optimizer_reaches_reference_optimum`; commit `b21e45a` |
| R2 | Fix grid search to build the complete feature frame | P0 | done | `tests/test_optimizer_real.py::test_grid_optimizer_builds_complete_feature_frame` |
| R3 | Make `mlflow` import lazy/optional | P0 | done | Lazy import in `src/pricing/engine.py`; `tests/test_mlflow_registry.py` |
| R6 | One canonical method name `grid_search`; reject `bayesian` | P0 | done | `tests/test_api.py::test_grid_search_and_alias_accepted`, `test_legacy_bayesian_method_rejected` |
| R7 | Real-model optimizer regression test | P0 | done | Reference-ratio tests in `tests/test_optimizer_real.py` |
| R8 | Default `pytest tests/` collects and passes | P0 | done | `pytest tests -q` |
| R9 | API contract and grid-path integration test | P0 | done | `tests/test_api.py::test_grid_path_reaches_reference_optimum` |
| R10 | Fix the Streamlit/API response contract | P0 | done | `tests/test_streamlit_contract.py` |
| R4 | One serving feature builder shared by all paths | P1 | done | `tests/test_serving_features.py::test_serving_builder_covers_committed_columns_in_order` |
| R5 | Correct and loud MLflow registry resolution | P1 | done | `tests/test_mlflow_registry.py`; `scripts/promote_model.py` |
| R11 | Remove the hardcoded fake Advanced-tab response | P1 | done | `tests/test_streamlit_contract.py::test_app_contains_no_fabricated_response_keys` |
| R12 | Honest temporal split and `product_id` handling | P1 | done | `tests/test_training_data.py::test_split_is_chronological`, `test_product_id_is_not_a_model_feature` |
| R13 | Health check validates the served model type | P1 | done | `tests/test_health_model_type.py` |
| R14 | Convert smoke tests into a collectable pytest module | P1 | done | `tests/smoke_tests.py` (8 tests; skip when offline) |
| R15 | Drift detection: wire it or delete it | P1 | done | Drift modules removed; `tests/test_import_graph.py` |
| R16 | Stop leaking internal error strings | P1 | done | `tests/test_api.py::test_optimizer_failure_returns_generic_error` |
| R17 | Fix the `PredictionLogger` shutdown crash | P1 | done | `tests/test_prediction_logger.py` |
| R18 | Config: every YAML key is read, or removed | P1 | done | `tests/test_config.py::test_every_yaml_key_is_read_by_code` |
| R19 | Env: every variable is read, or removed | P1 | done | `tests/test_env.py` |
| R20 | Log rotation: implement it or delete the claim | P1 | done | `tests/test_log_rotation.py` |
| R21 | `requirements.txt` correctness | P1 | done | `tests/test_requirements_pinned.py` |
| R22 | Dead code: delete or wire, file by file | P1 | done | `tests/test_import_graph.py`; deletion commits `c4b9fb1`, `3b51851`, `87fdf8a` |
| R23 | README truth pass | P1 | done | `tests/test_readme_truth.py`; `scripts/verify_readme.sh`; commit `f26dee3` |
| R24 | nginx: add a real config or remove the service | P1 | done | `docker-compose.yml` has no nginx; `tests/test_compose_files.py` |
| R25 | Docker build/compose works from a clean checkout | P1 | done | Model built in `Dockerfile`; `tests/test_dockerfile_model_build.py`; CI docker job |
| R26 | Bounded startup in `start.sh` | P1 | done | `scripts/verify_readme.sh` bounded health wait; `tests/test_verify_readme_script.py` |
| R34 | `PricingRequest.product_id` accepted but unused | P1 | done | `tests/test_product_id_contract.py` |
| R35 | Collapse to a single `config.yaml` | P1 | done | `tests/test_config.py::test_exactly_one_config_file`; R35 compose fixture |
| R27 | CI workflow (or remove CI claims) | P2 | done | `.github/workflows/ci.yml`; `tests/test_ci_workflow.py`; commits `3723295`, `2f890a0` |
| R28 | Deployment scripts, or remove the claims | P2 | done | AWS/deploy claims removed; `tests/test_readme_truth.py`; commit `5aa5d58` |
| R29 | SQLite: use it or remove it | P2 | done | SQLite chain deleted; `tests/test_import_graph.py`; commit `87fdf8a` |
| R30 | Raise coverage on the pricing/serving path | P2 | done | `scripts/check_coverage.py`; CI per-file 80% gate |
| R31 | Every documentation link resolves | P2 | done | `tests/test_readme_links.py` |
| R32 | Document the causal-inference limitation | P2 | done | `tests/test_readme_limitations.py` |
| R33 | Decide tracking for the agent records | P2 | done | Records were un-ignored and committed; later moved to `docs/` at P2 closure |

## 4. Timeline

| Date | Milestone | Commit |
|---|---|---|
| 2026-06-07 | Last pre-audit commit; the audit's reference baseline. | `c32841f` |
| 2026-09-27/28 | Audit completed; state, roadmap, decisions and conventions written; P0 scoped. | planning commits |
| 2026-09-29 | R1: L-BFGS-B replaced by a derivative-free dense grid search. | `b21e45a` |
| 2026-09-30 | R5/R6/R7/R9/R10: real-model tests, one method name, API contract. | several commits |
| 2026-10-07 | R15/D13: drift detection removed. | several commits |
| 2026-10-13 | R35 single config; R26 bounded startup; D27 pin policy. | `5a8f887`, `7cdbf56` |
| 2026-10-15 | D30: seeded generator and config-driven size. | `1abfc1b` |
| 2026-10-15 | D30/R25: data and model built inside the image. | `51c5c38` |
| 2026-10-16 | R23: `scripts/verify_readme.sh` runs the quickstart end to end. | `5e17dbc` |
| 2026-10-17 | D18/R27: GitHub Actions workflow and local CI scripts. | `3723295` |
| 2026-10-19 | D31: hardened main image, pinned MLflow image, compose hardening, docker smoke. | `1d45e8e`, `39fc31e`, `06f62f3`, `1b09d21`, `4496ca7` |
| 2026-10-19 | R27: README documents CI with a status badge. | `2f890a0` |
| 2026-10-20 | CI docker job found the MLflow driver bug; fixed by naming psycopg2. | `0aeb1be` |
| 2026-10-20 | Final agent-record update before the documentation move. | `1827883` |
| 2026-10-22 | P2 closure: docs moved to `docs/`, agent workflow files removed. | see the final commits of this batch |

## 5. Incidents and lessons

### A branch cut from an amended commit

The R1 branch was cut from `f4b0921`, but `main` had been amended to `616a6df` in the
previous session. The two commits were siblings, not parent and child. The branch carried
the pre-revision planning docs, so the session re-discovered a contradiction that had
already been fixed and produced a stale documentation commit.

**Lesson:** never amend a commit that a branch is based on; verify ancestry before starting
work. The rebuild kept to a single branch and stopped amending.

### R35 broke the production compose file and no test noticed

R35's edit corrupted the `environment:` indentation in the production compose file, making
it invalid YAML. Nothing parsed that file, so the suite stayed green. The fix was a compose
validator plus a fixture holding the exact broken file, and a test proving the validator
rejects it.

**Lesson:** a file that no test parses is not covered, even if it is "just configuration".

### Hardcoded reference values broke on retrain

Early optimizer tests compared against literal revenue figures. R12 retrained the model and
invalidated them. The tests now compute the reference optimum at test time from the loaded
artifact and the requested bounds (convention 34).

**Lesson:** if a value derives from an artifact, compute it; never freeze it.

### The bound-aware acceptance criterion

A tree model's revenue curve is piecewise with plateaus, so a price-equality assertion is
both fragile and wrong. R1 compares **revenue** against a 901-point reference and requires
that an interior reference argmax is not answered on a bound. R2 also recorded that a
50-step grid on `(30,120)` can reach only ~0.971 of the reference maximum, which is why the
grid spacing is now adaptive.

**Lesson:** assert the property the system promises, in the units the model actually has.

### The unseeded generator

The generator used the global NumPy RNG. Two clean clones produced different models
(R² 0.4328 vs 0.4708), and the documented 50-product dataset could not be reproduced with
the documented command (the script built 100 products). D30 seeded the generator, moved the
size and seed into `configs/config.yaml`, and built data and model inside the image.

The retrain moved R² from 0.4750 to 0.4193 (Δ −0.0557) and MAPE from 0.3458 to 0.3509. A
seed sweep (seeds 1–10 plus 42) showed R² 0.40602–0.50037 (mean 0.44650, population standard
deviation 0.02919) and MAPE 0.34671–0.37953 (mean 0.36080). The shift was therefore within
the seed-to-seed spread; the old 0.475 was one lucky draw.

**Lesson:** report a multi-seed mean and a reference seed, never a single unqualified number.

### Virtual-environment drift

The working environment had plain `xgboost` and an `nvidia-nccl-cu13` wheel instead of
`xgboost-cpu`, so it did not match `requirements.txt`. It was rebuilt from the pinned file
on 2026-10-16.

**Lesson:** the environment is part of the build; rebuild it from the pinned file.

### Tests that depended on `.git`

`test_workflow_file_is_not_gitignored` ran `git check-ignore`. It passed locally but failed
in CI's `git archive HEAD` checkout, which has no `.git` directory (exit 128). It was
rewritten to parse `.gitignore` in pure Python (convention 36).

**Lesson:** tests must not depend on how the repository was checked out.

### The psycopg driver bug found by the CI docker job

The first complete CI docker run passed the main image checks and failed at the MLflow
health step. The container restart-looped with
`ModuleNotFoundError: No module named 'psycopg'`: SQLAlchemy 2.1 resolves a bare
`postgresql://` URI to the psycopg 3 dialect, while the image installs psycopg2. Naming the
driver (`postgresql+psycopg2://`) fixed it without changing versions.

**Lesson:** transitive dependency behaviour is part of the image contract; a local static
check cannot replace a real start. This is why the docker job exists.

### Reproducing a clean clone

A fresh clone had no `.dockerignore`, no `.env`, no `mlflow.db` and no model. The baseline
suite produced 54 passed, 33 skipped and 11 errors (all missing model). After data and
training it produced 96 passed, 2 skipped. This drove the CI "build data and model first"
step and the zero-skip gate.

**Lesson:** "works on my machine" includes the untracked state; test the clone.

## 6. P2 closure

P2 covered R27–R33 plus the D31 container work. The user reported that, after commits
`0aeb1be` and `1827883`, both GitHub Actions jobs in `.github/workflows/ci.yml` — `test`
and `docker` — were green, including the `mlflow-server` health check that had exposed the
psycopg bug. That user-reported evidence is the acceptance record for R27 and the D31
container work.

**P2 closed on 2026-10-22.** The final local verification was a fresh
`bash scripts/ci_check.sh` run with the project virtual environment: 138 tests passed, 0
skipped, exit 0; combined coverage 97% (378/389 statements), with every file under
`src/pricing` and `src/api` at or above 80%. The closure batch moved the project
documentation into `docs/` and removed the agent workflow files.

## 7. Recovering the raw agent logs

The original agent records are preserved in the annotated tag `agents-archive`, which
points at the last commit before the directory was removed. Recover any file with:

```bash
git show agents-archive:.agents/LOG.md
git show agents-archive:.agents/STATE.md
```

The tag `p2-complete` marks the closure commit. Neither tag is pushed by this batch.
