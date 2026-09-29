# LOG.md — Running session log

Append a new entry at the **top** of the entries section (newest first) at the end of every
session. Do not edit past entries; supersede them with a new one.

## Template

```
## <date> — <one-line summary>
Done:
- ...
Left open / blocked:
- ...
Next session should start with:
- ...
```

---

## 2026-09-29 — R1 done; branch-divergence incident (stale branch base) found and resolved

Done:
- **R1 implemented and verified.** Replaced `scipy.optimize.minimize(method='L-BFGS-B')` in `src/pricing/bayesian_optimizer.py` with a vectorized dense price grid + local refinement (first pass targets 0.02 spacing, min 901 points, so it lands in the global basin; later passes zoom in). Batched `model.predict` with a row-by-row fallback for non-vectorized predict doubles. Removed the unused `method` parameter; no gradient call remains. **Code commit `b21e45a`** (see the incident below for why this hash and not the earlier `a325fbd`).
- **Re-verified against *this* revision's criteria** — revenue ≥ 0.99 × a test-time ≥ 901-point reference grid; `optimization_success` True; price within bounds; bound-aware interiority; contract; constraints — **all pass** (see the ROADMAP R1 evidence table). Observed: `(30,80)`/`(70,110)`/`(30,120)` → **77.3725** (ratios 1.00051/1.00051/1.00094 vs the 901-pt max); `(10,200)` → **200.0** and `(100,120)` → **120.0**, where the true optimum is genuinely the upper bound. `optimize_with_constraints(cost=60, min_margin_pct=0.15)` → price 77.3725, margin 0.2245. `pytest tests/ --ignore=tests/test_api.py -q` → **17 passed**. API (mlflow stubbed): `POST /v1/optimize-price` bayesian → 200, `optimal_price=77.3725`.
- **Incident — stale branch base.** The R1 branch was cut from `f4b0921`, but `main` was **amended** (`f4b0921` → `616a6df`) in the previous session (see the "R1 task-file fixes … `--amend`" entry below). Because an amend rewrites the commit, `616a6df` and `f4b0921` are **siblings** (both children of `c32841f`), and `616a6df` was never an ancestor of the branch. The branch therefore carried the **pre-revision** `.agents/` docs: D1/D2/D15 read as `proposed` (D2 un-merged), and R1's old price-equality criteria. Working from those, this session re-discovered the "strictly interior vs. 901-pt argmax" contradiction for `(10,200)`/`(100,120)` that the revision had **already** fixed (revenue-ratio + bound-aware rule), amended the stale ROADMAP copy, and produced a stale docs commit `0c21805`. The optimizer code itself was fine — only the bookkeeping baseline was stale.
- **Resolution:** reset the branch to the code commit `a325fbd`, then `git rebase --onto 616a6df f4b0921`, which replayed **only** the optimizer change onto `main` (new hash `b21e45a`) and **dropped `0c21805` entirely**. Re-read `main`'s actual `tasks/R1-real-optimizer.md` and ROADMAP R1 and re-ran every check against those exact criteria (not the stale-branch numbers). Then one clean docs commit against `main`'s current content (this entry + ROADMAP R1 `done` + STATE.md updates). `main` fast-forwarded to include the code and docs commits.
- Scope confirmed: `b21e45a` touches only `src/pricing/bayesian_optimizer.py`; the `"bayesian"` label and the `engine.py`/`schemas.py` dispatch are untouched, so R6/D2's `grid_search`/HTTP-422 work is entirely open and unimplemented.

Left open / blocked:
- R6/D2 (rename to `grid_search`, reject `"bayesian"` with 422) not started; R2 (grid `KeyError`), R3 (mlflow import), R8 (pytest collection) remain `todo`. A plain `pytest tests/` still aborts collection on `tests/test_api.py` (mlflow).
- No permanent regression test was added — that is ROADMAP **R7** (separate item; R1 must not create `tests/test_optimizer_real.py`).

Next session should start with:
- R2 and R3 (P0), then R7 (real-model regression test locking in R1 + R2). **Workflow hazard to avoid:** always branch from the current `main`, and prefer a merge over an amend once a branch exists — the `--amend` here rewrote the shared base and orphaned the R1 branch.

---

## 2026-09-29 — R1 task-file fixes + git-workflow note; `.agents/`+`AGENTS.md` folded into the planning commit via `--amend`

Done:
- **`.agents/tasks/R1-real-optimizer.md`:**
  - (a) Replaced the stale Out-of-scope example "(e.g. D2 must be `accepted` first)" — D2 is now
    `accepted`, so the example was wrong — with the current state: only D1/D2/D15 are `accepted`,
    **every other entry is still `proposed` and must not be implemented**. Named **D6**
    (chronological train/validation split) and **D5** (dropping `product_id`) as the currently-
    `proposed` decisions that are tempting but out of scope for R1, and stated that even D1/D2 do
    not license touching feature engineering or training code in R1.
  - (b) Added an **"Interim only"** note near "Relevant files": fixing `bayesian_optimizer.py` in
    place is interim — per accepted D1, once R6 locks `"bayesian"` as rejected (HTTP 422) the
    module becomes unreachable from the API and must be retired/merged by a later task (R4/R22);
    **R1 must not delete, rename, or merge the file**, only fix the algorithm inside it.
  - (c) Added a "Reference commits" note using a *relative* self-reference (`git log -1`) while
    keeping `c32841f` as the literal ground-truth citation.
- **Relative self-reference (no hardcoded self-HEAD):** reworded the top "Reference commits" note
  in `AGENTS.md`, `.agents/ROADMAP.md`, `.agents/DECISIONS.md`, and `.agents/CONVENTIONS.md` so it
  no longer hardcodes HEAD `f4b0921` as *the current* commit; it now reads "the current commit
  (see `git log -1`)". `c32841f` remains the literal, unchanging ground-truth citation. Rationale:
  these files are about to be folded into an amended commit, which would immediately stale a
  hardcoded self-referencing SHA. Past (non-top) LOG entries were left untouched.
- **New workflow note (Part 2a):** added a "## Git workflow for `.agents/` edits" section to
  `AGENTS.md`: planning-only edits to `.agents/*.md` + `AGENTS.md` within an active planning phase
  (before any ROADMAP item is `in-progress`) may be amended into the existing planning commit to
  keep one clean snapshot; `.agents/LOG.md` stays the authoritative chronological record regardless
  of commit boundaries; code changes are never amended — each gets its own commit(s).
- **Git history:** the uncommitted `.agents/` + `AGENTS.md` changes in this working tree are being
  folded into the existing planning commit via `git commit --amend` rather than added as a new
  commit, per the workflow note above. **Pre-amend commit: `f4b0921`** ("docs(agents): track
  .agents source-of-truth docs + AGENTS.md entrypoint"). The post-amend hash is deliberately not
  recorded here (it is unknowable before the amend and would be a stale self-reference); read it
  from `git rev-parse HEAD`. The untracked `.agents/archive/audit_Dynamic-Pricing-Engine.md`
  (archived 2026-09-28 per CONVENTIONS rule 33) is also being brought into the commit by
  `git add .agents`, so the tree is left fully clean.
- No code under `src/`, `scripts/`, `tests/`, `app.py`, or configs was changed. No roadmap item was
  started (R1 remains `todo`).

Left open / blocked:
- R1 is still `todo`; implementation was intentionally not started (this session was documentation
  + git hygiene only).
- Every decision except D1, D2, D15 (`accepted`) and D3, D14, D22, D23 (`superseded`) is still
  `proposed` and awaits the owner.
- `mlflow` is still unimportable in the local venv (protobuf conflict); R3/R8 remain blocked on that.

Next session should start with:
- Begin the P0 unblockers R1 (task file at `.agents/tasks/R1-real-optimizer.md`), R2, R3. Mark each
  `in-progress` before starting. R7 must be re-run after R12.

---

## 2026-09-29 — Owner finalized D1/D2 accepted; legacy "bayesian" locked to HTTP 422; reference-commit clarification (no commit)

Done:
- **DECISIONS.md:** D1 and D2 both moved `proposed` → `accepted` at the owner's direction. D2's open owner choice on the legacy `"bayesian"` method is removed and locked: `"bayesian"` (and any unrecognized value) is **REJECTED** with HTTP 422, not a deprecated alias. D2's Consequences now state that `src/api/schemas.py`'s enum/validator accepts only `"grid_search"` and its alias `"grid"`, and that `"bayesian"` / any other value is invalid input rather than silently normalized. D3's superseded note was updated to drop the "open owner choice" phrasing. Header refreshed: **D1, D2, D15 `accepted`; D3, D14, D22, D23 `superseded`; all other entries remain `proposed`.**
- **ROADMAP.md:** R6's acceptance criteria now describe only the accepted branch — `"grid"` and `"grid_search"` → HTTP 200; `"bayesian"` and any other unknown value → HTTP 422 (Pydantic/enum validation error, not 500, not a deprecation-warning alias). R6's title was updated and the two-branch / either-or "OPEN OWNER DECISION" note removed. R9's contract-test description was updated to assert 200 for `grid`/`grid_search` and 422 for `"bayesian"`. No roadmap item status changed (all still `todo` except R33 `done`).
- **Reference-commit clarification (no new commit):** added one consistently-phrased note near the top of `ROADMAP.md`, `DECISIONS.md`, `CONVENTIONS.md`, `AGENTS.md`, and this entry: ground truth is verified against commit `c32841f` (see `.agents/STATE.md`), while this planning revision sits on top of the working tree at HEAD `f4b0921` and was **not** committed. Existing "verified against `c32841f`" lines were left unchanged; `STATE.md` was not touched (it was not re-verified).
- No code under `src/`, `scripts/`, `tests/`, `app.py`, or configs was changed. No roadmap item was started or marked `done`. **No `git add` / `git commit` was run** — all `.agents/` edits remain uncommitted working-tree changes.

Left open / blocked:
- D1, D2, and D15 are now `accepted` and therefore unblocked for implementation, but implementation was intentionally not started in this pass (a separate step).
- Every other decision (D4–D13, D16–D21, D24, D25) is still `proposed` and awaits the owner.
- `mlflow` is still unimportable in the local venv (protobuf conflict); R3/R8 remain blocked on that.

Next session should start with:
- Begin the P0 unblockers R1, R2, R3 (task file at `.agents/tasks/R1-real-optimizer.md`), now that D1/D2 are `accepted`. Mark each `in-progress` before starting. R7 must be re-run after R12.

---

## 2026-09-28 — Revised planning docs: runtime reference grids, single-optimizer decision, enforcement tags

Done:
- **ROADMAP.md:** rewrote R1's acceptance criteria to drop the "strictly interior" price rule and all hardcoded numbers (e.g. 77.30). R1 is now revenue-based: for bounds `(30,80)`, `(70,110)`, `(10,200)`, `(100,120)`, `(30,120)` the returned `expected_revenue` must be ≥ 0.99 × the maximum over a ≥ 901-point reference grid **computed at test time with the same model and bounds**; `optimization_success` True; price within bounds; no bound-hugging where the reference argmax is strictly interior. Applied the same "reference at test time, no hardcoded numbers" principle to R2, R7, R9. Made R7 model-agnostic and noted it must be **re-run after R12** (which retrains the artifact). Re-prioritized: **P0 = R1,R2,R3,R6,R7,R8,R9,R10 (8)**; **P1 = R4,R5,R11–R26 (18)**; **P2 = R27–R33 (7)**; updated the execution-order section. Updated R6/R9/R10 for the single method name (`grid_search`, alias `grid`) and wrote both branches of the legacy-`"bayesian"` open owner decision (HTTP 422 reject vs deprecated alias). All statuses remain `todo`; R33 stays `done`.
- **DECISIONS.md:** merged D2+D3 into one decision — single canonical optimizer = vectorized dense price-grid search named `grid_search` (alias `grid`) — and marked D3 `superseded` by D2. Rewrote D1 to match (one optimizer module, one strategy; delete `integrated_optimizer.py` and `transformer.py`). Marked D14 `superseded` (covered by CONVENTIONS rule 26) and D22/D23 `superseded` (folded into ROADMAP R23/R32). D16 now names `python:3.12-slim` (the interpreter actually tested) and states the current Dockerfiles pin 3.10 and must be bumped. No entry deleted; D15 stays `accepted`; header refreshed.
- **CONVENTIONS.md:** resolved the rule 19 ↔ R3 contradiction (optional/lazy heavy-dep imports in production code are *required*; what is forbidden is hiding a broken dependency in tests via `--ignore`, config overrides, or conditional test imports). Narrowed rule 14 to optimizer/pricing/model-prediction tests (schema/middleware exempt). Added an enforcement status tag to every rule (`enforced` or `target (after Rxx)`). Appended two rules: **33** (owner-supplied files must never be deleted/overwritten without explicit approval — archive under `.agents/archive/`) and **34** (tests must not hardcode model-derived reference values; compute them at test time). Numbering 1–32 preserved.
- **Archived the superseded audit** per new rule 33: moved `/tmp/audit_Dynamic-Pricing-Engine.md.bak` → `.agents/archive/audit_Dynamic-Pricing-Engine.md` (30,266 bytes, MD5 `660b46ed041c1e81486ab11e6cb7476d`). It was present, so no re-supply was needed.
- **Consistency:** updated `.agents/tasks/R1-real-optimizer.md` to match the new R1 criteria; checked `AGENTS.md` (it lists no priorities/counts/file lists, so no change was needed); normalized every "Last updated" line to `2026-09-28, against commit c32841f (see .agents/STATE.md)`; grepped `.agents/*.md` for stale R/D/rule/priority-count references. `STATE.md` was **not** touched (nothing was re-verified).
- No code under `src/`, `scripts/`, `tests/`, `app.py`, or configs was changed. No roadmap item was started.

Left open / blocked:
- **OPEN OWNER DECISIONS:** (1) legacy `"bayesian"` handling — reject with HTTP 422 (recommended) or accept as a deprecated alias (see DECISIONS D2, ROADMAP R6/R9); (2) accept or override the merged D2, the revised D1, and the remaining `proposed` entries.
- R7 must be re-run after R12 (the model artifact is retrained there).
- The historical priority counts in the 2026-09-27 entry below ("14 P0 / 12 P1 / 7 P2") are left as-is: that entry records that session's state and past log entries are not edited.
- `mlflow` is still unimportable in the local venv (protobuf conflict); R3/R8 remain blocked on that.
- `.agents/archive/audit_Dynamic-Pricing-Engine.md` is a read-only archive — do not edit it (rule 33).

Next session should start with:
- Owner to pick the legacy-`"bayesian"` option and accept/override D1/D2, then start the P0 unblockers R1, R2, R3 (task file at `.agents/tasks/R1-real-optimizer.md`). Mark each `in-progress` before starting.

---

## 2026-09-28 — Deleted the superseded audit, corrected STATE.md, and put `.agents/` under git

Done:
- Compared `audit_Dynamic-Pricing-Engine.md` with `.agents/STATE.md`. STATE.md supersedes it: it is more complete and already corrects the audit's two known errors (the "nested clone" and the non-existent `docs/ARCHITECTURE.md`). Backed the audit up to `/tmp/audit_Dynamic-Pricing-Engine.md.bak` and **deleted** it as redundant (two sources of truth violate CONVENTIONS rule 27).
- Fixed errors in `.agents/STATE.md`: (a) the prediction logs were described as "committed" but are untracked (`logs/` is gitignored) — corrected in §1 and §5.1; (b) `reports/feature_importance.csv:31` → `:30` for `product_id` (importance 0.01195); (c) §6 retitled now that the audit is gone; (d) the `.gitignore` bullet updated to the new tracked state; (e) `Last verified` → 2026-09-28.
- `.gitignore`: removed the `.agents` ignore so the directory can be tracked. Note for the record: the owner's edit had actually **added** `.agents` to `.gitignore` (replacing the `docs/` ignore), i.e. the directory was still ignored despite the intent to un-ignore it.
- Committed `.agents/` (`STATE.md`, `ROADMAP.md`, `CONVENTIONS.md`, `DECISIONS.md`, `LOG.md`, `tasks/R1-real-optimizer.md`) and the root `AGENTS.md`.
- Bookkeeping: ROADMAP **R33 → done** (evidence recorded); DECISIONS **D15 → accepted** at the owner's direction; "Last updated" lines refreshed. (Also recording the prior session's unlogged output: `.agents/tasks/R1-real-optimizer.md` was created; no code was written.)

Left open / blocked:
- Every roadmap item except R33 is still `todo`; decisions D1–D14 and D16–D25 are still `proposed`.
- `mlflow` is still unimportable in the local venv (protobuf conflict); R3/R8 remain blocked on that.

Next session should start with:
- Accept or override the remaining `.agents/DECISIONS.md` entries, then start the P0 unblockers: R1 (task file at `.agents/tasks/R1-real-optimizer.md`), R2 (grid fix), R3 (lazy/optional mlflow import). Mark each `in-progress` before starting.

---

## 2026-09-27 — Source-code audit completed; `.agents/` planning docs created (no code changed)

Done:
- Audited the whole repo against actual source and runtime (not README/docs) and wrote `.agents/STATE.md`: a claim-by-claim verification table, the real training/serving flows, a dead-code inventory, unread config/env values, and known-broken behavior. Core finding: the headline "Bayesian optimizer" is `scipy` L-BFGS-B on a tree model and returns a bound/midpoint; the grid optimizer crashes with a `KeyError`.
- Wrote `.agents/ROADMAP.md`: 33 discrete items (14 P0 / 12 P1 / 7 P2), all `todo`, each with priority, files, testable acceptance criteria, and dependencies.
- Wrote `.agents/CONVENTIONS.md`: 32 enforceable rules derived from the observed failure patterns (dead code, config/env hygiene, exception handling, test realism, docs-vs-code sync, single source of truth, contracts, ops).
- Wrote `.agents/DECISIONS.md`: 25 ADR-lite entries (D1–D25), all `proposed`, covering the optimizer consolidation, nested-repo policy, SQLite removal, and MLflow-optional posture, plus 21 more.
- Wrote this `.agents/LOG.md` and the root `AGENTS.md` entrypoint.
- No code changes were made. No roadmap item has been started.

Left open / blocked:
- All 33 roadmap items are `todo`; all 25 decisions are `proposed` and await the owner's accept/override. No implementation may begin on a proposed decision.
- `.agents/` is currently gitignored by `.gitignore:86` (see DECISIONS D15); the four planning files are untracked.
- Environment caveat: `mlflow` cannot be imported in the local venv (protobuf conflict), so `python -m src.api.server`, `scripts/train_with_tuning.py`, and `pytest tests/` (collection) fail until ROADMAP R3/R8 are done.
- Note for the record: during the audit, one probe accidentally ran the training pipeline in the repo root and overwrote the untracked `models/demand_model.pkl` and `reports/*`; they were restored from a pre-run copy (MD5 verified) and `reports/training_metrics.json` is back to `R2=0.4682`. Git state was unaffected.

Next session should start with:
- Have the owner accept or override the entries in `.agents/DECISIONS.md` (at minimum D1, D7, D9, D14).
- Then start the P0 unblockers in `.agents/ROADMAP.md`: R1 (real optimizer), R2 (grid fix), R3 (lazy/optional mlflow import). Mark each `in-progress` before starting.
