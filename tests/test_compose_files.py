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
from urllib.parse import urlsplit

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



def _main_compose():
    return yaml.safe_load(
        (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    )


def _volume_mounts(service):
    return [str(volume) for volume in service.get("volumes", [])]


def test_pricing_api_restarts_unless_stopped():
    service = _main_compose()["services"]["pricing-api"]
    assert service.get("restart") == "unless-stopped"


def test_no_obsolete_top_level_version_key():
    assert "version" not in _main_compose(), (
        "the top-level 'version' key is obsolete and prints a warning"
    )


def test_configs_mount_is_read_only():
    mounts = _volume_mounts(_main_compose()["services"]["pricing-api"])
    configs = [mount for mount in mounts if mount.split(":")[1:2] == ["/app/configs"]]
    assert configs, f"pricing-api has no /app/configs mount: {mounts}"
    assert all(mount.endswith(":ro") for mount in configs), configs


def test_logs_use_a_declared_named_volume():
    doc = _main_compose()
    mounts = _volume_mounts(doc["services"]["pricing-api"])
    logs = [mount for mount in mounts if mount.split(":")[1:2] == ["/app/logs"]]
    assert logs, f"pricing-api has no /app/logs mount: {mounts}"
    for mount in logs:
        source = mount.split(":")[0]
        assert not source.startswith((".", "/")), (
            f"/app/logs must be a named volume, not a host bind: {mount}"
        )
        assert source in doc.get("volumes", {}), (
            f"named volume {source!r} is not declared under top-level volumes"
        )


def test_no_data_bind_mount_at_serve_time():
    """STEP 0a: the serving path neither reads nor writes data/."""
    mounts = _volume_mounts(_main_compose()["services"]["pricing-api"])
    data = [mount for mount in mounts if mount.split(":")[1:2] == ["/app/data"]]
    assert data == [], f"unexpected /app/data mount: {data}"


MLFLOW_DOCKERFILE = REPO_ROOT / "Dockerfile.mlflow"


def _pinned_version(text, package):
    match = re.search(rf"\b{re.escape(package)}==([^\s\\\"'&]+)", text)
    return match.group(1) if match else None


def test_mlflow_image_pins_match_requirements():
    """D31/D27: the pinned mlflow image matches requirements.txt."""
    image_text = MLFLOW_DOCKERFILE.read_text(encoding="utf-8")
    req_text = (REPO_ROOT / "requirements.txt").read_text(encoding="utf-8")

    for package in ("mlflow", "protobuf"):
        image_pin = _pinned_version(image_text, package)
        req_pin = _pinned_version(req_text, package)
        assert image_pin, f"{MLFLOW_DOCKERFILE.name} does not pin {package}==X"
        assert req_pin, f"requirements.txt has no {package}== pin"
        assert image_pin == req_pin, (
            f"image {package}=={image_pin} != requirements {package}=={req_pin}"
        )

    assert _pinned_version(image_text, "psycopg2-binary") == "2.9.13"


def test_mlflow_service_uses_the_pinned_image_not_pip_at_start():
    service = _main_compose()["services"]["mlflow"]
    build = service.get("build")
    assert isinstance(build, dict), f"mlflow service has no build mapping: {build!r}"
    assert build.get("dockerfile") == "Dockerfile.mlflow", build
    command = service.get("command", "")
    assert "pip install" not in command, (
        f"mlflow service still installs at start: {command!r}"
    )


def test_mlflow_image_runs_non_root_and_has_a_healthcheck():
    text = MLFLOW_DOCKERFILE.read_text(encoding="utf-8")
    users = [
        line.split(None, 1)[1].strip().lower()
        for line in text.splitlines()
        if line.strip().upper().startswith("USER ")
    ]
    assert users, "Dockerfile.mlflow has no USER instruction"
    assert users[-1] not in {"root", "0", "root:root", "0:0"}, users
    healthchecks = [
        line for line in text.splitlines()
        if line.strip().upper().startswith("HEALTHCHECK ")
    ]
    assert healthchecks, "Dockerfile.mlflow has no HEALTHCHECK"
    assert ":5000/health" in text, "HEALTHCHECK does not probe :5000/health"


def _compose_backend_store_uris(service):
    """Every backend-store URI the compose service supplies, if any."""
    uris = []

    command = service.get("command")
    if isinstance(command, str):
        uris.extend(
            match.strip("\"'")
            for match in re.findall(r"--backend-store-uri[=\s]+(\S+)", command)
        )
    elif isinstance(command, list):
        for index, token in enumerate(command):
            if token == "--backend-store-uri" and index + 1 < len(command):
                uris.append(command[index + 1])

    environment = service.get("environment", {})
    if isinstance(environment, dict):
        items = environment.items()
    else:
        items = [
            entry.split("=", 1) for entry in environment if "=" in str(entry)
        ]
    for key, value in items:
        if key in {"MLFLOW_BACKEND_STORE_URI", "BACKEND_STORE_URI"}:
            uris.append(str(value))

    return uris


def test_mlflow_backend_store_uri_names_the_psycopg2_driver():
    """SQLAlchemy 2.1 resolves ``postgresql://`` to the psycopg (v3) dialect.

    The CI docker job (2026-10-19) crashed the mlflow-server container with
    ``ModuleNotFoundError: No module named 'psycopg'`` from
    ``sqlalchemy/dialects/postgresql/psycopg.py`` while creating the engine for
    ``postgresql://...``. The image installs psycopg2, so the URI must name that
    driver explicitly (``postgresql+psycopg2://``).
    """
    text = MLFLOW_DOCKERFILE.read_text(encoding="utf-8")
    match = re.search(r'"--backend-store-uri",\s*"([^"]+)"', text)
    assert match, "Dockerfile.mlflow CMD has no --backend-store-uri value"

    uri = match.group(1)
    scheme = urlsplit(uri).scheme
    assert scheme == "postgresql+psycopg2", (
        f"backend-store-uri scheme is {scheme!r}, not 'postgresql+psycopg2': {uri}"
    )

    psycopg2_pin = _pinned_version(text, "psycopg2-binary")
    assert psycopg2_pin, "Dockerfile.mlflow does not pin psycopg2-binary==X"
    assert re.fullmatch(r"\d+(\.\d+)+", psycopg2_pin), (
        f"psycopg2-binary pin is not an exact version: {psycopg2_pin!r}"
    )

    compose_uris = _compose_backend_store_uris(_main_compose()["services"]["mlflow"])
    for compose_uri in compose_uris:
        assert urlsplit(compose_uri).scheme == "postgresql+psycopg2", (
            f"compose backend-store-uri does not name the driver: {compose_uri}"
        )
