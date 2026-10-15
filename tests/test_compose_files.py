"""Validate the repo's docker-compose files, including an R35 regression fixture.

Why this exists (R25 follow-up): R35 (commit 5a8f887) corrupted the
``environment:`` indentation in ``docker-compose.prod.yml`` so the file stopped
being valid YAML, and no test caught it. Convention 18 requires the regression
check to demonstrably fail on the pre-fix version, so
``tests/fixtures/invalid_compose_r35.yml.txt`` holds the exact broken file and
``test_invalid_fixture_is_reported`` asserts the validator flags it.
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml
REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
INVALID_FIXTURE = FIXTURES_DIR / "invalid_compose_r35.yml.txt"


def validate_compose(path) -> list[str]:
    """Return a list of problems with ``path``; an empty list means valid."""
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"{path}: cannot read file: {exc}"]

    try:
        doc = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        return [f"{path}: YAML parse error: {exc}"]

    problems: list[str] = []

    if not isinstance(doc, dict):
        return [f"{path}: top level is not a mapping"]

    services = doc.get("services")
    if not isinstance(services, dict) or not services:
        return [f"{path}: 'services' is missing or not a non-empty mapping"]

    for name, service in services.items():
        if not isinstance(service, dict):
            problems.append(f"{path}: service '{name}' is not a mapping")
            continue

        if "image" not in service and "build" not in service:
            problems.append(
                f"{path}: service '{name}' has neither 'image' nor 'build'"
            )

        build = service.get("build")
        if build is None:
            continue

        if isinstance(build, str):
            context, dockerfile = build, None
        elif isinstance(build, dict):
            context = build.get("context", ".")
            dockerfile = build.get("dockerfile")
        else:
            problems.append(f"{path}: service '{name}' has an invalid 'build' value")
            continue

        context_dir = (path.parent / context).resolve()
        if not context_dir.is_dir():
            problems.append(
                f"{path}: service '{name}' build context '{context}' does not exist"
            )
        elif dockerfile:
            if not (context_dir / dockerfile).is_file():
                problems.append(
                    f"{path}: service '{name}' dockerfile '{dockerfile}' "
                    f"not found in build context '{context}'"
                )

    return problems


DISCOVERED_COMPOSE_FILES = sorted(REPO_ROOT.glob("docker-compose*.yml"))


def test_at_least_one_compose_file_discovered():
    assert DISCOVERED_COMPOSE_FILES, (
        f"no docker-compose*.yml found in {REPO_ROOT}"
    )


@pytest.mark.parametrize(
    "compose_file",
    DISCOVERED_COMPOSE_FILES,
    ids=[p.name for p in DISCOVERED_COMPOSE_FILES],
)
def test_compose_file_is_valid(compose_file):
    problems = validate_compose(compose_file)
    assert problems == [], f"{compose_file.name} has problems: {problems}"


def test_invalid_fixture_is_reported():
    problems = validate_compose(INVALID_FIXTURE)
    assert problems, "expected the R35 pre-fix fixture to be rejected"
    assert any("parse error" in p.lower() for p in problems), (
        f"expected a parse-error problem, got: {problems}"
    )


@pytest.mark.parametrize(
    "compose_file",
    DISCOVERED_COMPOSE_FILES,
    ids=[p.name for p in DISCOVERED_COMPOSE_FILES],
)
def test_docker_compose_config_accepts_file(compose_file):
    if shutil.which("docker") is None:
        pytest.skip("docker CLI not available")
    result = subprocess.run(
        ["docker", "compose", "-f", str(compose_file), "config", "-q"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, (
        f"`docker compose config -q` failed for {compose_file.name} "
        f"(rc={result.returncode}): {result.stderr}"
    )


def test_compose_mlflow_service_pin_matches_requirements():
    """D27 point 7: the mlflow service pins the same mlflow== as requirements.txt."""
    compose = yaml.safe_load(
        (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    )
    command = compose["services"]["mlflow"]["command"]
    compose_match = re.search(r"mlflow==([^\s\"'&]+)", command)
    assert compose_match, f"mlflow service command does not pin mlflow==X: {command!r}"

    req_text = (REPO_ROOT / "requirements.txt").read_text(encoding="utf-8")
    req_match = re.search(r"^mlflow==([^\s#]+)", req_text, re.MULTILINE)
    assert req_match, "requirements.txt has no mlflow== pin"

    assert compose_match.group(1) == req_match.group(1), (
        f"compose mlflow=={compose_match.group(1)} "
        f"!= requirements mlflow=={req_match.group(1)}"
    )
