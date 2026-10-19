"""Static checks for the GitHub Actions workflow (ROADMAP R27 / DECISIONS D18).

No network and no Docker: the workflow, the scripts it calls and the Dockerfile
are read from disk. PyYAML implements YAML 1.1, which parses the bare ``on:``
key as the boolean ``True``; the helper below accepts either form.
"""
import fnmatch
import re
import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
DOCKERFILE = REPO_ROOT / "Dockerfile"

# Scripts the workflow depends on, directly or through scripts/ci_check.sh.
CI_SCRIPTS = (
    "scripts/ci_check.sh",
    "scripts/check_coverage.py",
    "scripts/docker_smoke.sh",
    "scripts/verify_readme.sh",
)


@pytest.fixture(scope="module")
def workflow_text():
    assert WORKFLOW.is_file(), f"missing workflow: {WORKFLOW}"
    return WORKFLOW.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def workflow(workflow_text):
    return yaml.safe_load(workflow_text)


def _triggers(workflow):
    """The ``on:`` mapping, tolerating PyYAML's YAML-1.1 ``True`` key."""
    return workflow.get("on", workflow.get(True))


def _run_text(workflow):
    return "\n".join(
        step["run"]
        for job in workflow["jobs"].values()
        for step in job["steps"]
        if "run" in step
    )


def test_workflow_parses_and_runs_on_push_and_pr_for_main(workflow):
    triggers = _triggers(workflow)
    assert isinstance(triggers, dict)
    assert {"push", "pull_request"} <= set(triggers)
    for trigger in ("push", "pull_request"):
        assert "main" in triggers[trigger]["branches"]


def test_test_and_docker_jobs_with_the_documented_bounds(workflow):
    jobs = workflow["jobs"]
    assert {"test", "docker"} <= set(jobs)
    assert jobs["docker"]["needs"] == "test"
    assert jobs["test"]["timeout-minutes"] == 20
    assert jobs["docker"]["timeout-minutes"] == 30


def test_python_version_matches_the_dockerfile_base(workflow):
    steps = workflow["jobs"]["test"]["steps"]
    versions = [
        step["with"]["python-version"]
        for step in steps
        if "python-version" in step.get("with", {})
    ]
    assert versions == ["3.12"]

    first_from = next(
        line for line in DOCKERFILE.read_text(encoding="utf-8").splitlines()
        if line.strip().upper().startswith("FROM ")
    )
    match = re.search(r"python:(\d+\.\d+)", first_from)
    assert match, f"no python:<version> base in {first_from!r}"
    assert match.group(1) == versions[0]


def test_steps_call_the_repo_scripts(workflow):
    run_text = _run_text(workflow)
    assert "scripts/ci_check.sh" in run_text
    assert "scripts/docker_smoke.sh" in run_text


def test_no_error_suppression(workflow_text):
    assert "continue-on-error" not in workflow_text
    assert "|| true" not in workflow_text


def test_permissions_are_read_only(workflow):
    assert workflow["permissions"] == {"contents": "read"}


def test_ci_scripts_exist_are_executable_and_parse(workflow):
    run_text = _run_text(workflow)
    referenced = set(re.findall(r"scripts/[\w./-]+\.(?:sh|py)", run_text))
    assert {"scripts/ci_check.sh", "scripts/docker_smoke.sh"} <= referenced

    for relative in CI_SCRIPTS:
        path = REPO_ROOT / relative
        assert path.is_file(), f"missing {relative}"
        assert path.stat().st_mode & 0o111, f"{relative} is not executable"
        if relative.endswith(".sh"):
            result = subprocess.run(
                ["bash", "-n", str(path)], capture_output=True, text=True
            )
            assert result.returncode == 0, f"{relative}: {result.stderr}"


def _ignore_patterns(path):
    """Yield `(negated, pattern, directory_only)` from an ignore file.

    Simplified gitignore parsing: blank lines and `#` comments are skipped,
    a leading `/` anchors the pattern to the repository root, a trailing `/`
    marks a directory-only pattern, and a leading `!` re-includes. Escapes and
    character classes beyond `fnmatch` are not modelled.
    """
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        negated = line.startswith("!")
        if negated:
            line = line[1:].strip()
            if not line:
                continue
        directory_only = line.endswith("/")
        line = line.strip("/")
        if line:
            yield negated, line, directory_only


def _pattern_matches(pattern, candidate):
    """Match one normalised pattern against a repo-relative path.

    A pattern containing a slash is anchored at the root; a pattern without one
    matches a single path component at any depth (gitignore's `*.yml` rule).
    """
    if "/" in pattern:
        return fnmatch.fnmatchcase(candidate, pattern)
    return fnmatch.fnmatchcase(candidate.rsplit("/", 1)[-1], pattern)


def _is_gitignored(relative_path, gitignore):
    """Return whether `relative_path` is ignored by `gitignore`.

    This is a deliberate simplification of gitignore semantics, not a full git
    implementation. The path and each of its parent directories are tested
    against every pattern, and the last matching pattern wins (so a later `!`
    re-inclusion cancels an earlier match). Negations are honoured only when
    they match the path itself; git's rule that a file inside an ignored
    directory cannot be re-included is not modelled, because the only question
    here is whether this one tracked workflow path is ignored.

    The test must not shell out to `git`: `scripts/verify_readme.sh` runs the
    suite in a `git archive HEAD` export that has no `.git` directory, so a
    `git check-ignore` subprocess fails there with exit 128. Parsing the ignore
    file in pure Python mirrors the approach already used for
    `.dockerignore` in `tests/test_repo_hygiene.py`.
    """
    candidates = []
    parts = relative_path.split("/")
    for index in range(len(parts), 0, -1):
        candidates.append("/".join(parts[:index]))
    directories = candidates[1:]

    ignored = False
    for negated, pattern, directory_only in _ignore_patterns(gitignore):
        pool = directories if directory_only else candidates
        if any(_pattern_matches(pattern, candidate) for candidate in pool):
            ignored = not negated
    return ignored


def test_workflow_file_is_not_gitignored():
    """A workflow under an ignored path would never reach GitHub.

    Reads `.gitignore` directly instead of running `git check-ignore`: CI's
    archive checkout (`scripts/verify_readme.sh`) has no `.git` directory.
    The matcher is intentionally simplified; see `_is_gitignored`.
    """
    relative = WORKFLOW.relative_to(REPO_ROOT).as_posix()
    assert not _is_gitignored(relative, REPO_ROOT / ".gitignore"), (
        f"{relative} is ignored by .gitignore"
    )


def test_docker_smoke_script_checks_nonroot_health_and_mlflow():
    """D31: the docker job verifies the hardened runtime, not just HTTP 200."""
    script = (REPO_ROOT / "scripts" / "docker_smoke.sh").read_text(encoding="utf-8")
    for needle in ("id -u", "State.Health.Status", ":5000/health", "docker compose down"):
        assert needle in script, f"scripts/docker_smoke.sh is missing {needle!r}"
    result = subprocess.run(
        ["bash", "-n", str(REPO_ROOT / "scripts" / "docker_smoke.sh")],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
