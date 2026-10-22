# Engineering conventions

These are the rules for anyone changing this repository. They exist because each pattern
below was found in the codebase during the audit and cost real credibility. The numbers are
preserved: code comments and tests cite "convention 34", "rule 36" and so on.

The enforcement tag says how the rule is checked today:

- **enforced (test/script)** — an automated check exists.
- **enforced (review)** — checked in code review.
- **enforced (process)** — a workflow rule, not a test.

## Rules

### Dead code

1. Every module, class and function under `src/` must be reachable from a real entry point
   (`src.api.server` or a `scripts/` entry) or be deleted in the same change. "Reachable
   only from tests" is dead. — **enforced (test/script)** by `tests/test_import_graph.py`.
2. Do not add a file to `src/` without at least one import from the running path. Keep the
   import-graph test green; if it flags an orphan, delete or wire the orphan before merging.
   — **enforced (test/script)**.
3. Delete code outright — no `# removed` comments, `_unused` renames or stray renamed
   `.pyc` files. Git history is the archive. — **enforced (review)**.
4. If a function is defined but never called, either call it from production code or delete
   it; an unused import of it is not "usage". — **enforced (review)**.

### Config and environment hygiene

5. Every key in `configs/*.yaml` must be read by `src/` or `scripts/` code, or be
   deleted. The config test fails on any unread key. — **enforced (test/script)** by
   `tests/test_config.py`.
6. Every variable in `.env` must be read by code that actually runs (or by a script that is
   actually invoked); `.env.example` must list exactly the read set. Remove decorative
   variables. — **enforced (test/script)** by `tests/test_env.py`.
7. Never hardcode a value that also exists as config. Read it from config, and if the key is
   removed, remove the hardcoded twin too. — **enforced (review)**.
8. Pick one configuration mechanism per concern: runtime toggles come from environment
   variables, structural settings from `configs/config.yaml`. Do not keep a third unread
   copy. — **enforced (review)**; the single-file rule is checked by `tests/test_config.py`.

### Exception handling and fallbacks

9. Never catch a bare `Exception` and continue into a fallback that changes behaviour. Catch
   a specific exception, log at ERROR, and record the degraded state (for example
   `checks.model.source == "local"` on `/v1/health`). — **enforced (test/script)** by
   `tests/test_mlflow_registry.py`.
10. Every fallback must be observable and asserted by a test. A broken registry must never
    look like success. — **enforced (test/script)**.
11. Never return raw exception text to a client. 500 responses carry a generic message plus
    `request_id`; the exception is logged server-side. A test asserts that no response body
    contains `KeyError`, `Traceback` or `not in index`. — **enforced (test/script)** by
    `tests/test_api.py`.
12. Objective or loss functions must not return a magic penalty to hide failures. Let the
    error surface; if a penalty is unavoidable, log and count every occurrence. — **enforced
    (review)**.
13. Do not perform I/O in `__del__`. Use `atexit` or context managers for flushing. —
    **enforced (test/script)** by `tests/test_prediction_logger.py`.

### Test realism

14. Any test that validates optimizer behaviour, a pricing decision or a model prediction
    must run against the working-tree `models/demand_model.pkl` and the tracked
    `models/features.json` at least once per test file — not only against mocks. Schema and
    middleware tests are exempt. — **enforced (test/script)** by `tests/test_optimizer_real.py`
    and `tests/test_api.py`.
15. A test must assert the specified behaviour, not the current bug. Do not assert that drift
    exists, that a call raises, or that a bound is returned unless that is the documented
    contract. — **enforced (review)**.
16. Tests must target the code path that actually serves or trains. If a class is not on the
    running path, its tests are dead too — delete them or wire the class in. — **enforced
    (test/script)** by the import graph.
17. Every test file must be collected by a plain `pytest tests` run. Put test logic in
    module-level `test_*` functions or classes; if a test needs a live server, skip when it
    is unreachable — never let collection error. — **enforced (test/script)**.
18. A regression test for a bug must be shown to fail on the pre-fix code and pass after. Add
    it in the same change as the fix. — **enforced (process)**.
19. Optional or lazy imports of heavy dependencies in production code are required: serving
    and tests must start when the dependency is unavailable. What is forbidden is hiding a
    broken dependency in tests via `--ignore`, config overrides or conditional imports; fix
    the root cause. — **enforced (review)**.

### Documentation versus code

20. Every command in the README's local quickstart must be executed by
    `scripts/verify_readme.sh` (run in CI). Docker, Streamlit and load-test commands are
    documented separately and are not part of that script. If a quickstart command does
    not run on a clean checkout, it cannot be in the README. — **enforced (test/script)**
    by `tests/test_verify_readme_script.py` and the CI test job.
21. Every relative link in `README.md` and `docs/` must resolve to an existing file. Do not
    link planned documents. — **enforced (test/script)** by `tests/test_readme_links.py` and
    `tests/test_docs.py`.
22. Numbers in docs must be copied from the generated artifact, not from memory, and R² must
    be stated together with MAPE. Regenerate artifacts before updating a number. — **enforced
    (review)**.
23. A feature may be described in current-state docs only if the code, a test, a script or
    the CI workflow backs the description. Remove the claim or fix the code — there is no
    third state. — **enforced (review)**; path-level claims are checked by
    `tests/test_docs.py`.
24. Name things what they are. If it uses a gradient method, do not call it "Bayesian"; if
    the split is random, do not call it "time-series validation"; if `prometheus-client` is
    not imported, do not claim Prometheus. — **enforced (test/script)** by
    `tests/test_api.py` (the served method is `grid_search`; `"bayesian"` is rejected with
    422).
25. No hardcoded fake responses or hand-written "example" payloads presented as live data.
    Examples must be labelled as examples and generated from the schema, not invented. —
    **enforced (test/script)** by `tests/test_streamlit_contract.py`.

### Single source of truth

26. There is exactly one canonical repository root. Never commit a vendored or nested clone
    of `src/` or the whole project; deploy mirrors must be produced in CI or referenced as a
    submodule, never checked in. — **enforced (review)**.
27. Do not commit a second copy of any artifact or state (`mlruns/`, `data.db`, a duplicate
    config that is never read). If a file is orphaned — never read or written by code —
    delete it or wire it in the same change. — **enforced (test/script)** by
    `tests/test_repo_hygiene.py`.
28. `docs/ARCHITECTURE.md`, `docs/OPERATIONS.md` and
    `docs/LIMITATIONS_AND_NEXT_STEPS.md` are the current-state description of what works.
    Update them in the same change that alters a claim, and re-verify every statement against
    code, a test, a script or the CI workflow. — **enforced (process)**.

### Contracts

29. Any consumer of the API must be validated against the response schema in a test:
    `set(keys read by the consumer) ⊆ set(PricingResponse.model_fields)`. Field renames
    update the consumer and the test in the same change. — **enforced (test/script)** by
    `tests/test_streamlit_contract.py`.
30. Enum-like inputs (for example `optimization_method`) must have a single normalization
    point and a test for every accepted value; unknown values return 4xx, never 500. —
    **enforced (test/script)** by `tests/test_api.py`.

### Operations and dependencies

31. Startup and wait loops must have a bounded timeout and exit non-zero on failure. Never
    write an unbounded `until curl ...; do sleep; done` loop. — **enforced (test/script)**
    by `scripts/verify_readme.sh`, `scripts/docker_smoke.sh` and
    `tests/test_verify_readme_script.py`.
32. Declared dependencies must be imported, and imported dependencies must be declared.
    `pip check` and a grep-based unused-dependency check must pass before merging. —
    **enforced (test/script)** by `tests/test_requirements_pinned.py` and the import graph.

### Owner-supplied files

33. Files supplied by the owner (audits, inputs, data, reference documents) must never be
    deleted or overwritten without explicit owner approval. When one is superseded, archive
    it under `docs/archive/` and link the archive path from the record that supersedes it,
    rather than removing it. — **enforced (process)**.

### Model-derived reference values

34. Tests must not hardcode reference values that derive from a model artifact (argmax
    prices, revenue figures, metrics). Compute them at test time from the loaded artifact and
    the given inputs, so the test stays valid across retrains. — **enforced (test/script)**
    by `tests/test_optimizer_real.py` and `tests/test_api.py`.

### Commit hygiene

35. Every commit must leave the full test suite green. A config key and the code that reads
    it go in the same commit; a transient red commit hurts `git bisect`. — **enforced
    (process)**.
36. Scripts and tests must not depend on how the repository was checked out: no `git`
    subprocess calls and no `.git` directory in tests; read tracked files directly. Verify
    CI scripts at the committed HEAD, never before committing the files they test. —
    **enforced (test/script)** by `tests/test_ci_workflow.py`.

## How the rebuild was run (historical)

The rebuild that produced this repository followed five rules. They are recorded here
because they explain the shape of the history, not because they constrain future work.

1. **Single branch `main`.** No task branches. Work was committed directly to `main`.
2. **One commit per task.** Each roadmap item or documentation batch got its own commit;
   commits were never combined.
3. **Evidence before "done".** An item moved to done only after the stated command, test or
   assertion was run and its output recorded. A title was never evidence.
4. **Flag instead of fix.** When a problem was outside the current task's scope, it was
   written down and left for a later item rather than silently repaired.
5. **One docs commit per batch.** Documentation updates for a batch were committed
   separately from the code, with explicit paths only.

The detailed record of the rebuild — the audit findings, the 35 roadmap items, the
incidents and the P2 closure — is in [REBUILD_HISTORY.md](REBUILD_HISTORY.md).
