"""Deterministic Spec Kit workspace setup for the ``rigorail-design`` workflow.

Rigorail does not vendor Spec Kit. The workspace under ``.specify/`` and the
Claude-facing ``speckit-*`` skills are scaffolded from assets bundled inside the
pinned ``specify-cli`` dev dependency, so a fresh clone reproduces exactly the
files that version ships, without network access.

Rigorail exposes only ``/speckit-plan`` to Claude. Every other Spec Kit skill
the Claude integration installs is pruned here.

Run from the repository root::

    uv run python -m rigorail.speckit_setup

The command is idempotent: on an already-correct workspace it verifies and
changes nothing. It never repairs unexpected state silently -- it fails.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

SPECKIT_VERSION = "1.0.1"
"""The only Spec Kit version ``rigorail-design`` has been exercised against."""

SKILL_PREFIX = "speckit-"
ALLOWED_SKILLS = frozenset({"speckit-plan"})

INIT_ARGS = (
    "init",
    "--here",
    "--force",
    "--non-interactive",
    "--integration",
    "claude",
    "--script",
    "sh",
    "--ignore-agent-tools",
)


class SetupError(RuntimeError):
    """Unexpected toolchain or workspace state. Never repaired silently."""


def cli_version(specify: str) -> str:
    """Return the version reported by the ``specify`` executable."""
    result = subprocess.run([specify, "--version"], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise SetupError(
            f"`{specify} --version` failed with exit code {result.returncode}:\n"
            f"{result.stderr.strip()}"
        )
    reported = result.stdout.strip()
    parts = reported.split()
    if len(parts) != 2 or parts[0] != "specify":
        raise SetupError(f"Unrecognised `specify --version` output: {reported!r}")
    return parts[1]


def resolve_cli() -> str:
    """Locate ``specify`` and confirm it is exactly the pinned version."""
    specify = shutil.which("specify")
    if specify is None:
        raise SetupError(
            "`specify` is not on PATH. Run this inside the project environment: "
            "`uv run python -m rigorail.speckit_setup`."
        )
    version = cli_version(specify)
    if version != SPECKIT_VERSION:
        raise SetupError(
            f"specify-cli {version} is on PATH, but this repository pins "
            f"{SPECKIT_VERSION}. Run `uv sync --dev`."
        )
    return specify


def repository_root() -> Path:
    """Return the current directory, confirmed to be the Rigorail repository root."""
    root = Path.cwd()
    for marker in (Path("pyproject.toml"), Path(".claude/skills/rigorail-design")):
        if not (root / marker).exists():
            raise SetupError(
                f"{root} is not the Rigorail repository root (missing {marker}). "
                "Run this command from the repository root."
            )
    return root


def workspace_version(root: Path) -> str | None:
    """Return the Spec Kit version recorded in the workspace, or ``None`` if absent."""
    integration = root / ".specify" / "integration.json"
    if not integration.is_file():
        return None
    try:
        return json.loads(integration.read_text(encoding="utf-8"))["version"]
    except (OSError, json.JSONDecodeError, KeyError) as exc:
        raise SetupError(f"{integration} is unreadable or malformed: {exc}") from exc


def skill_dir(root: Path, name: str) -> Path:
    return root / ".claude" / "skills" / name


def installed_speckit_skills(root: Path) -> list[str]:
    """Return the Spec Kit Claude skills currently present, sorted."""
    skills = root / ".claude" / "skills"
    if not skills.is_dir():
        return []
    return sorted(
        entry.name
        for entry in skills.iterdir()
        if entry.is_dir() and entry.name.startswith(SKILL_PREFIX)
    )


def needs_init(root: Path) -> bool:
    """Whether the workspace must be scaffolded from the pinned CLI."""
    recorded = workspace_version(root)
    if recorded is None:
        return True
    if recorded != SPECKIT_VERSION:
        raise SetupError(
            f"{root / '.specify' / 'integration.json'} records Spec Kit {recorded}, but "
            f"this repository pins {SPECKIT_VERSION}. Delete `.specify/` and the "
            f"`{SKILL_PREFIX}*` skills to rescaffold, or correct the pin."
        )
    if not (root / ".specify" / "scripts" / "bash" / "setup-plan.sh").is_file():
        return True
    return not (skill_dir(root, "speckit-plan") / "SKILL.md").is_file()


def run_init(root: Path, specify: str) -> None:
    """Scaffold the Spec Kit workspace and the Claude integration in ``root``."""
    result = subprocess.run(
        [specify, *INIT_ARGS], cwd=root, capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise SetupError(
            f"`specify {' '.join(INIT_ARGS)}` failed with exit code {result.returncode}:\n"
            f"{result.stdout.strip()}\n{result.stderr.strip()}"
        )


def prune_skills(root: Path) -> list[str]:
    """Remove every Spec Kit Claude skill that is not on the allowlist."""
    removed = []
    for name in installed_speckit_skills(root):
        if name in ALLOWED_SKILLS:
            continue
        shutil.rmtree(skill_dir(root, name))
        removed.append(name)
    return removed


def verify(root: Path) -> None:
    """Fail loudly unless the workspace is exactly what ``rigorail-design`` needs."""
    recorded = workspace_version(root)
    if recorded != SPECKIT_VERSION:
        raise SetupError(
            f"Spec Kit workspace reports version {recorded!r}, expected {SPECKIT_VERSION!r}."
        )
    setup_plan = root / ".specify" / "scripts" / "bash" / "setup-plan.sh"
    if not setup_plan.is_file():
        raise SetupError(f"Missing {setup_plan}; the Spec Kit workspace is incomplete.")
    plan_skill = skill_dir(root, "speckit-plan") / "SKILL.md"
    if not plan_skill.is_file():
        raise SetupError(f"Missing {plan_skill}; rigorail-design has no planner to invoke.")
    unexpected = [n for n in installed_speckit_skills(root) if n not in ALLOWED_SKILLS]
    if unexpected:
        raise SetupError(
            "Spec Kit skills exposed to Claude beyond the allowlist: " + ", ".join(unexpected)
        )


def setup(root: Path, specify: str) -> list[str]:
    """Scaffold if needed, prune to the allowlist, then verify. Returns pruned skills."""
    if needs_init(root):
        run_init(root, specify)
    removed = prune_skills(root)
    verify(root)
    return removed


def main() -> int:
    try:
        root = repository_root()
        removed = setup(root, resolve_cli())
    except SetupError as exc:
        print(f"speckit-setup: {exc}", file=sys.stderr)
        return 1
    print(f"speckit-setup: Spec Kit {SPECKIT_VERSION} workspace ready in {root}")
    if removed:
        print(f"speckit-setup: pruned {', '.join(removed)}")
    print(f"speckit-setup: exposed to Claude: {', '.join(sorted(ALLOWED_SKILLS))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
