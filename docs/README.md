# Documentation

This directory describes the Dynamic Pricing Engine: a demo that trains an XGBoost
demand model on **synthetic** e-commerce data and serves a revenue-maximizing price
through a FastAPI API and a Streamlit UI.

## Start here

1. [ARCHITECTURE.md](ARCHITECTURE.md) — what the system is, how a request flows, and
   which tests guard each part.
2. [OPERATIONS.md](OPERATIONS.md) — how to build, run, test and troubleshoot it.
3. [LIMITATIONS_AND_NEXT_STEPS.md](LIMITATIONS_AND_NEXT_STEPS.md) — what it does not do,
   open observations, and the parked Phase 3 plan.

## Index

| File | Purpose | Audience |
|---|---|---|
| [README.md](README.md) | This index and reading order. | Everyone |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Current-state design: pipeline, serving path, configuration, containers, CI, testing, repository layout. | Engineers and reviewers |
| [OPERATIONS.md](OPERATIONS.md) | Current-state runbook: prerequisites, commands, API examples, environment variables, logs, troubleshooting. | Anyone running the demo |
| [LIMITATIONS_AND_NEXT_STEPS.md](LIMITATIONS_AND_NEXT_STEPS.md) | Current-state limits and open observations, plus the parked Phase 3 review plan. | Reviewers and planners |
| [DECISIONS.md](DECISIONS.md) | Historical architecture decision log D1–D31. | Engineers |
| [ENGINEERING_CONVENTIONS.md](ENGINEERING_CONVENTIONS.md) | Repository rules 1–36 and the historical rebuild process. | Contributors |
| [REBUILD_HISTORY.md](REBUILD_HISTORY.md) | Historical record of the audit, the rebuild R1–R35, incidents, and P2 closure. | Reviewers |
| [archive/AUDIT_ORIGINAL.md](archive/AUDIT_ORIGINAL.md) | The original technical audit, preserved byte-for-byte. | Historians |

## Current state versus history

- **Current state:** `ARCHITECTURE.md`, `OPERATIONS.md` and
  `LIMITATIONS_AND_NEXT_STEPS.md`. Every statement is backed by code, a test, a script
  or the CI workflow in this repository.
- **Historical records:** `DECISIONS.md` and `REBUILD_HISTORY.md` describe decisions and
  events from earlier phases. They may mention files that were deleted or states that no
  longer exist; those mentions are history, not current instructions.
- **Historical archive:** `docs/archive/` is frozen. Its contents are preserved exactly
  as they were and are not maintained.

All data in this project is synthetic. Every metric describes how well the model learns
the synthetic generator, not real-world accuracy.
