"""Static checks for the GitHub Actions workflow (ROADMAP R27 / DECISIONS D18).

No network and no Docker: the workflow, the scripts it calls and the Dockerfile
are read from disk. PyYAML implements YAML 1.1, which parses the bare ``on:``
key as the boolean ``True``; the helper below accepts either form.
"""
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


def test_workflow_file_is_not_gitignored():
    """A workflow under an ignored path would never reach GitHub."""
    result = subprocess.run(
        ["git", "check-ignore", "-q", str(WORKFLOW)],
        cwd=REPO_ROOT,
        capture_output=True,
    )
    assert result.returncode == 1, (
        f"{WORKFLOW} is ignored by git (check-ignore exit {result.returncode})"
    )
