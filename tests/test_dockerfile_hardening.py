"""D31: the main image is hardened — builder stage, non-root user, HEALTHCHECK.

Pure file parsing: no Docker and no git, so the checks run in any checkout
(CONVENTIONS rule 36). The CI ``docker`` job verifies the built image.
"""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = REPO_ROOT / "Dockerfile"


def _instructions() -> list[str]:
    """Dockerfile instructions with line continuations joined."""
    instructions: list[str] = []
    buffer = ""
    for line in DOCKERFILE.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        continued = stripped.endswith("\\")
        part = stripped[:-1].strip() if continued else stripped
        buffer = f"{buffer} {part}".strip() if buffer else part
        if not continued:
            instructions.append(buffer)
            buffer = ""
    if buffer:
        instructions.append(buffer)
    return instructions


def _stages() -> list[list[str]]:
    stages: list[list[str]] = []
    for instruction in _instructions():
        if instruction.upper().startswith("FROM "):
            stages.append([instruction])
        elif stages:
            stages[-1].append(instruction)
    return stages


def _is_source_copy(instruction: str) -> bool:
    """True for ``COPY . .`` and flag variants such as ``COPY --chown=a:a . .``."""
    parts = instruction.split()
    if not parts or parts[0].upper() != "COPY":
        return False
    args = [part for part in parts[1:] if not part.startswith("--")]
    return args == [".", "."]


def test_at_least_two_stages_and_final_is_not_the_builder():
    stages = _stages()
    assert len(stages) >= 2, f"expected a builder and a final stage, got {len(stages)}"
    final_from = stages[-1][0].upper()
    assert " AS BUILDER" not in final_from, f"final stage is the builder: {final_from}"


def test_non_root_user_after_sources_before_cmd():
    final = _stages()[-1]
    user_indexes = [
        i for i, instruction in enumerate(final)
        if instruction.upper().startswith("USER ")
    ]
    assert user_indexes, "final stage has no USER instruction"
    user_index = user_indexes[-1]
    user = final[user_index].split(None, 1)[1].strip().lower()
    assert user not in {"root", "0", "root:root", "0:0"}, f"USER is root: {user}"

    copy_index = next(
        (i for i, instruction in enumerate(final) if _is_source_copy(instruction)),
        None,
    )
    assert copy_index is not None, "final stage has no COPY of the sources"
    assert copy_index < user_index, "USER appears before the sources are copied"

    cmd_index = next(
        (i for i, instruction in enumerate(final)
         if instruction.upper().startswith("CMD ")),
        None,
    )
    assert cmd_index is not None, "final stage has no CMD"
    assert user_index < cmd_index, "USER appears after the final CMD"


def test_healthcheck_targets_the_health_endpoint():
    healthchecks = [
        instruction for instruction in _stages()[-1]
        if instruction.upper().startswith("HEALTHCHECK ")
    ]
    assert healthchecks, "final stage has no HEALTHCHECK instruction"
    assert any("/v1/health" in instruction for instruction in healthchecks), (
        f"HEALTHCHECK does not target /v1/health: {healthchecks}"
    )


def test_final_stage_does_not_pip_install():
    offenders = [
        instruction for instruction in _stages()[-1]
        if instruction.upper().startswith("RUN ")
        and "pip install" in instruction.lower()
    ]
    assert offenders == [], f"final stage installs dependencies: {offenders}"


def test_data_and_model_build_run_after_sources_are_copied():
    final = _stages()[-1]
    copy_index = next(
        (i for i, instruction in enumerate(final) if _is_source_copy(instruction)),
        None,
    )
    assert copy_index is not None, "final stage has no COPY of the sources"
    after = "\n".join(
        instruction for instruction in final[copy_index + 1:]
        if instruction.upper().startswith("RUN ")
    )
    assert "scripts/regenerate_data.py" in after, (
        f"no RUN after the source COPY mentions scripts/regenerate_data.py: {after}"
    )
    assert "src.training.train" in after, (
        f"no RUN after the source COPY mentions src.training.train: {after}"
    )
