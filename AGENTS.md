# AGENTS.md — start here

Entrypoint for any AI agent working in this repo. Keep this file short; the linked files
are the source of truth, not this one.

**Reference commits:** Ground truth verified against commit `c32841f` (see `.agents/STATE.md`). This planning revision sits on top of the working tree at the current commit (see `git log -1`); no new commit was created for these `.agents/` edits.

## Before doing anything else in a session, read in this exact order

1. **`.agents/STATE.md`** — the only trusted description of what currently works. Do not trust
   `README.md`, `docs/`, or code comments over it.
2. **`.agents/ROADMAP.md`** — pick or confirm the task in progress. Mark it `in-progress` before starting.
3. **`.agents/LOG.md`** — read the latest (top) entry for what the previous session left open.
4. **`.agents/CONVENTIONS.md`** — read before writing or modifying any code. These rules are enforceable.

`.agents/DECISIONS.md` is the architecture decision log; a `proposed` decision must not be
implemented until it is marked `accepted`.

## At the end of every session

- Append a new entry to `.agents/LOG.md` (use the template at the top of that file).
- Update the relevant item's status in `.agents/ROADMAP.md` (only to `done` after its acceptance criteria are verified).
- Update `.agents/STATE.md` if any claim's status changed — especially fake/partial → confirmed, or confirmed → broken.

## Git workflow for `.agents/` edits

Planning-only edits to `.agents/*.md` and `AGENTS.md` within an active planning phase (before any
ROADMAP item is `in-progress`) may be amended into the existing planning commit to keep git history
to one clean snapshot; `.agents/LOG.md` remains the authoritative chronological record of
session-by-session history regardless of git commit boundaries. Code changes are never amended
into an existing commit — each code change gets its own commit(s).

## Hard rules

- **`README.md` is user-facing marketing copy. It is never a source of technical truth for an agent.** Verify claims against source and runtime.
- Do not start a `proposed` decision in `.agents/DECISIONS.md`.
- Do not mark work done based on a description; verify the acceptance criterion.
