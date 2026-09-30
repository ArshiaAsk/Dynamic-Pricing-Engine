# CONVENTIONS.md — Rules for all future work

**Scope:** every human or agent contributing to this repo. These rules exist because the
patterns below were found in this codebase and each one cost real credibility.

**Reference commits:** Ground truth verified against commit `c32841f` (see `.agents/STATE.md`). This planning revision sits on top of the working tree at the current commit (see `git log -1`); no new commit was created for these `.agents/` edits.

**Enforcement status (added 2026-09-28):** every rule ends with a status tag:
- **`enforced`** — checked today. Either an automated test/script exists, or the rule is a
  review/process rule enforced by code review and the `AGENTS.md` workflow (tagged
  `enforced (code review)` / `enforced (process)`).
- **`target (after Rxx)`** — depends on a roadmap item that is not yet `done`; it is not
  checked today.

If you cannot check a rule, it is not a rule. New rules are appended at the end so existing
"(R#)/rule N" cross-references stay valid.

---

## Failure patterns observed (recap by category)

- **Tests that mock away the behavior under test** — `tests/test_optimizer.py:18` uses a smooth linear model, so it passes while the real XGBoost model breaks the optimizer. `tests/test_integration.py` tests `IntegratedPricingOptimizer`, which is not on the running path. `tests/test_data_drift.py` asserts the bug (`pvalue < 0.01`). `tests/smoke_tests.py` collects 0 tests. A plain `pytest tests/` aborts collection on an `mlflow` import.
- **Silent fallbacks / swallowed exceptions** — `src/pricing/engine.py:91-94` catches bare `Exception`, logs a WARNING, and silently loads a local pickle; `src/pricing/integrated_optimizer.py:87-89` returns `1e10` on any error; `src/api/router.py:108` leaks `str(e)` to clients.
- **Dead code** — `revenue.py`, `optimize.py`, `metrics_tracker.py`, `model_monitor.py`, `data/{ingest,pipeline_runner,validation}.py`, `utils/config.py`, `features/feature_pipeline.py`, `integrated_optimizer.py`, `transformer.py`, `model_loader.py`, and `engine.compare_methods` are never reached by the API or training path.
- **Config/env defined but never wired** — the entire `monitoring:` block, `training.test_size`/`random_state`/`cv_folds`, `pricing.price_steps`/`default_method`, and the `api:`/`logging:` blocks in dev/prod YAML are never read; ~24 `.env` vars are decorative.
- **Misleading labels** — L-BFGS-B called "Bayesian optimization"; a random split called "time-series validation"; `prometheus-client` declared but never imported; "log rotation" is a plain `FileHandler`.
- **Docs written ahead of code** — README links five files that do not exist, shows a curl to `/optimize-price` (404), documents `python src/training/train.py` (fails), and rounds R² 0.468 up to "0.49" while omitting MAPE 0.40.
- **Duplicated source of truth** — a nested clone of the whole repo was previously committed (now absent; do not reintroduce); `data.db` is an orphan never read or written by code.
- **Contract drift & fabricated UI data** — `app.py` reads `predicted_demand` while the API returns `expected_demand`, sends `grid_search` which the engine rejects, and shows a hardcoded fake response in the Advanced tab.
- **Unbounded ops** — `start.sh:23-25` waits forever for health with no retry cap; `docker-compose.prod.yml` mounts a non-existent `nginx/`.

---

## Rules

### Dead code
1. Every module, class, and function under `src/` must be reachable from a real entry point (`src.api.server` or a `scripts/` training entry) or be deleted in the same PR. "Reachable only from tests" is dead — either wire it into production or delete it with its tests. (R22) — `target (after R22)`
2. Do not add a file to `src/` without at least one import from the running path. Keep the import-graph test green; if it flags an orphan, delete or wire the orphan before merging. — `target (after R22)`
3. Delete code outright — no `# removed` comments, `_unused` renames, or stray renamed `.pyc` files. Git history is the archive. — `enforced (code review)`
4. If a function is defined but never called (e.g. `load_production_model`, `compare_methods`, `EnvConfig.get_env`), either call it from production code or delete it; an unused import of it is not "usage". — `target (after R22)`

### Config & env hygiene
5. Every key in `configs/*.yaml` must be read by `src/` code, or be deleted. The config test must fail on any unread key. (R18) — `target (after R18)`
6. Every variable in `.env` must be read by code that actually runs (or by a shell script that is actually invoked); `.env.example` must list exactly the read set. Remove decorative vars. (R19) — `target (after R19)`
7. Never hardcode a value that also exists as config (`test_size`, `random_state`, `cv_folds`, `price_steps`, etc.). Read it from config, and if the key is removed, remove the hardcoded twin too. — `target (after R18, R19)`
8. Pick one configuration mechanism per concern: runtime toggles come from env vars *or* YAML, never both with a third unread copy. If a section exists in both, delete one. — `target (after R18)`

### Exception handling & fallbacks
9. Never catch bare `Exception` and continue into a fallback that changes behavior. Catch a specific exception, log at ERROR, and record the degraded state (e.g. `checks.model.source == "local"` exposed by `/v1/health`). (R5) — `target (after R5)`
10. Every fallback must be observable and asserted by a test. A "use the local model instead" path may not be silent, and a broken registry must never look like success. — `target (after R5)`
11. Never return raw exception text to a client. 500 responses carry a generic message plus `request_id`; the exception is logged server-side. A test asserts no response body contains `KeyError`, `Traceback`, or `not in index`. (R16) — `target (after R16)`
12. Objective/loss functions must not return a magic penalty (e.g. `1e10`) to hide failures. Let the error surface; if a penalty is unavoidable, log and count every occurrence. — `target (after R1)`
13. Do not perform I/O in `__del__`. Use `atexit` or context managers for flushing. (R17) — `target (after R17)`

### Test realism
14. Any test that validates **optimizer behavior, a pricing decision, or a model prediction** must run against the working-tree `models/demand_model.pkl` (gitignored, regenerated by the training pipeline) + the tracked `models/features.json` at least once per test file — not only against mocks. Schema and middleware tests are exempt. (R7) — `target (after R7)`
15. A test must assert the specified behavior, not the current bug. Do not assert that drift exists, that a call raises, or that a bound is returned unless that is the documented contract. — `target (after R7, R15)`
16. Tests must target the code path that actually serves or trains. If a class is not on the running path, its tests are dead too — delete them or wire the class in. — `target (after R22)`
17. Every test file must be collected by a plain `pytest tests/` run. Put test logic in module-level `test_*` functions/classes, not in helper classes; if a test needs a live server, mark it and skip when unreachable — never let collection error. (R14) — `target (after R14, R8)`
18. A regression test for a bug must be shown to fail on the pre-fix code and pass after. Add it in the same PR as the fix. (R7) — `target (after R7)`
19. Optional/lazy imports of heavy dependencies (e.g. `mlflow`) in **production code are required** — serving and tests must start when the dependency is unavailable. What is forbidden is *hiding* a broken dependency **in tests** via `--ignore`, config overrides, or conditional test imports; fix the root cause instead. (R3, R8) — `target (after R3, R8)`

### Docs vs code sync
20. Every command in `README.md` must be executed by `scripts/verify_readme.sh` (run in CI). If it does not run on a clean checkout, it cannot be in the README. (R23) — `target (after R23)`
21. Every relative link in `README.md`/`docs/` must resolve to an existing file. Do not link planned documents. (R31) — `target (after R31)`
22. Numbers in docs must be copied from the generated artifact, not from memory, and R² must be stated together with MAPE. Re-generate artifacts before updating any number. — `target (after R23, R12)`
23. A feature may be described in docs only if `.agents/STATE.md` marks it `CONFIRMED`, or `PARTIAL` with the caveat stated verbatim. Remove the claim or fix the code — there is no third state. (R23) — `target (after R23)`
24. Name things what they are. If it uses `scipy` L-BFGS-B, do not call it "Bayesian"; if the split is random, do not call it "time-series validation"; if `prometheus-client` is not imported, do not claim Prometheus. — `enforced (R1/R6: the served method is `grid_search`; `"bayesian"` is rejected with 422)`
25. No hardcoded fake responses or hand-written "example" payloads presented as live data. Examples must be labeled as examples and generated from the schema, not invented. (R11) — `enforced (R11: tests/test_streamlit_contract.py asserts app.py contains no confidence_interval / optimization_metadata / example_response)`

### Single source of truth
26. There is exactly one canonical repo root. Never commit a vendored or nested clone of `src/` or the whole project; deploy mirrors must be produced in CI or referenced as a submodule, never checked in. — `enforced (code review)`
27. Do not commit a second copy of any artifact or state (`mlruns/`, `data.db`, a duplicate config that is never read). If a file is orphaned — never read or written by code — delete it or wire it in the same PR. (R29) — `target (after R29)`
28. `.agents/STATE.md` is the single source of truth for what works. Update it in the same PR that changes any claim, and re-verify its `Last verified` commit line. — `enforced (process: AGENTS.md)`

### Contracts
29. Any consumer of the API must be validated against the response schema in a test: `set(keys read by the consumer) ⊆ set(PricingResponse.model_fields)`. Field renames update the consumer and the test in the same PR. (R10) — `enforced (R10: tests/test_streamlit_contract.py parses app.py and asserts UI-read keys ⊆ PricingResponse.model_fields)`
30. Enum-like inputs (e.g. `optimization_method`) must have a single normalization point and a test for every accepted value; unknown values return 4xx, never 500. (R6) — `enforced (R6: `Literal["grid_search","grid"]`; `tests/test_api.py` asserts 200 for both accepted values and 422 for `"bayesian"`/unknown)`

### Ops & dependencies
31. Startup/wait loops must have a bounded timeout and exit non-zero on failure. Never write `until curl ...; do sleep; done` with no cap. (R26) — `target (after R26)`
32. Declared dependencies must be imported, and imported dependencies must be declared. `pip check` and a grep-based unused-dependency check must pass before merging. (R21) — `target (after R21)`

### Owner-supplied files
33. Files supplied by the owner (audits, inputs, data, reference documents) must never be deleted or overwritten without explicit owner approval. When one is superseded, archive it under `.agents/archive/` and link the archive path from the record that supersedes it, rather than removing it. — `enforced (process: AGENTS.md/LOG)`

### Model-derived reference values
34. Tests must not hardcode reference values that derive from a model artifact (argmax prices, revenue figures, metrics). Compute them at test time from the loaded artifact and the given inputs, so the test stays valid across retrains. (R7, R12) — `target (after R7)`

---

Last updated: 2026-09-30, against commit 43d9a04 (see `.agents/STATE.md`; rule 14 wording corrected to "working-tree (gitignored)" for the model pickle).
