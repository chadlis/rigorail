"""Deterministic preflight for the ``rigorail-design`` workflow.

Everything the design workflow needs before planning may start, and that a
program can decide, happens here rather than in the user's shell:

1. resolve the requested feature directory and confirm it holds the product
   contract artifacts;
2. run the ``rigorail-spec`` validator, so "the specification is frozen" is a
   verified exit code rather than a claim;
3. verify -- and, when missing or stale, scaffold -- the pinned Spec Kit
   workspace, reusing :mod:`rigorail.speckit_setup`;
4. create ``technical-context.md`` when it is absent, recording only facts the
   repository actually evidences and leaving human constraints empty;
5. pin the Spec Kit feature directory by invoking Spec Kit's own
   ``setup-plan.sh`` with a command-scoped ``SPECIFY_FEATURE_DIRECTORY``, then
   confirm the directory Spec Kit resolved is the intended one.

Run from the repository root::

    uv run python -m rigorail.design_preflight specs/<slug>

The command is idempotent and never repairs unexpected state silently: it
fails, prints why, and exits ``1``.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

from rigorail import speckit_setup

TECHNICAL_CONTEXT_FILENAME = "technical-context.md"
"""Level-2 authority: technical constraints that outrank planner judgment."""

REQUIRED_CONTRACT_ARTIFACTS = ("spec.md", "decisions.md")

SPEC_VALIDATOR = Path(".claude/skills/rigorail-spec/scripts/validate_spec.py")
SETUP_PLAN = Path(".specify/scripts/bash/setup-plan.sh")

LOCKFILE_PACKAGE_MANAGERS = (
    ("uv.lock", "uv"),
    ("poetry.lock", "Poetry"),
    ("pdm.lock", "PDM"),
    ("Pipfile.lock", "Pipenv"),
    ("pnpm-lock.yaml", "pnpm"),
    ("yarn.lock", "Yarn"),
    ("package-lock.json", "npm"),
    ("Cargo.lock", "Cargo"),
    ("go.sum", "Go modules"),
)


class PreflightError(RuntimeError):
    """A precondition for design planning that a program could not establish."""


@dataclass(frozen=True)
class Fact:
    """A repository property, and the file that evidences it."""

    statement: str
    evidence: str


# --------------------------------------------------------------------------
# Feature directory
# --------------------------------------------------------------------------


def resolve_feature_dir(root: Path, requested: str | Path) -> Path:
    """Resolve ``requested`` against ``root`` and confirm it holds the contract.

    Accepts the argument the user typed -- ``specs/team-invites`` or an absolute
    path -- so no exported shell state is required to name the feature.
    """
    candidate = Path(requested)
    if not candidate.is_absolute():
        candidate = root / candidate
    feature_dir = candidate.resolve()

    try:
        feature_dir.relative_to(root.resolve())
    except ValueError as exc:
        raise PreflightError(f"{feature_dir} is outside the repository root {root}.") from exc

    if not feature_dir.is_dir():
        raise PreflightError(f"Feature directory {feature_dir} does not exist.")

    missing = [name for name in REQUIRED_CONTRACT_ARTIFACTS if not (feature_dir / name).is_file()]
    if missing:
        raise PreflightError(
            f"{feature_dir} is missing {', '.join(missing)}; it does not hold a product "
            "contract produced by rigorail-spec."
        )
    return feature_dir


# --------------------------------------------------------------------------
# Frozen specification
# --------------------------------------------------------------------------


def verify_frozen_spec(root: Path, feature_dir: Path) -> None:
    """Run the ``rigorail-spec`` validator strictly; anything but ``0`` fails.

    Exit ``1`` means malformed or ungrounded artifacts, exit ``2`` means an
    ``OPEN_PRODUCT_DECISION`` is still open. Neither is an approved contract, so
    neither may start technical design.
    """
    validator = root / SPEC_VALIDATOR
    if not validator.is_file():
        raise PreflightError(f"Missing {validator}; the specification gate cannot be verified.")

    result = subprocess.run(
        [sys.executable, str(validator), str(feature_dir)],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise PreflightError(
            f"The specification in {feature_dir} is not frozen: "
            f"`validate_spec.py` exited {result.returncode}.\n"
            f"{result.stdout.strip()}\n{result.stderr.strip()}".rstrip()
        )


# --------------------------------------------------------------------------
# Spec Kit workspace
# --------------------------------------------------------------------------


def ensure_speckit(root: Path) -> str:
    """Verify the pinned Spec Kit workspace, scaffolding it only if needed.

    Returns ``"verified"`` when the workspace was already correct and nothing
    changed, or ``"repaired"`` when it had to be scaffolded or pruned back to the
    allowlist. A workspace recording a version other than the pin is not
    repaired silently. The ``specify`` CLI is required only when scaffolding is.
    """
    try:
        speckit_setup.verify(root)
        return "verified"
    except speckit_setup.SetupError:
        pass

    try:
        specify = speckit_setup.resolve_cli() if speckit_setup.needs_init(root) else ""
        speckit_setup.setup(root, specify)
    except speckit_setup.SetupError as exc:
        raise PreflightError(f"Spec Kit workspace setup failed: {exc}") from exc
    return "repaired"


def pin_feature_directory(root: Path, feature_dir: Path) -> Path:
    """Point Spec Kit at ``feature_dir`` and confirm it resolved that directory.

    ``SPECIFY_FEATURE_DIRECTORY`` is scoped to this one command rather than
    exported by the user. Spec Kit persists the value to ``.specify/feature.json``
    itself, which is how the planner invoked afterwards resolves the same
    feature without any shell state.
    """
    script = root / SETUP_PLAN
    if not script.is_file():
        raise PreflightError(f"Missing {script}; the Spec Kit workspace is incomplete.")

    feature_dir = feature_dir.resolve()
    relative = feature_dir.relative_to(root.resolve())
    env = {**os.environ, "SPECIFY_FEATURE_DIRECTORY": str(relative)}
    result = subprocess.run(
        ["bash", str(script), "--json"],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise PreflightError(
            f"`SPECIFY_FEATURE_DIRECTORY={relative} {script} --json` exited "
            f"{result.returncode}:\n{result.stdout.strip()}\n{result.stderr.strip()}".rstrip()
        )

    lines = [line for line in result.stdout.splitlines() if line.strip()]
    if not lines:
        raise PreflightError(f"{script} --json produced no output.")
    try:
        payload = json.loads(lines[-1])
        resolved = Path(payload["SPECS_DIR"])
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise PreflightError(f"Could not read SPECS_DIR from {script} --json: {exc}") from exc

    if not resolved.is_absolute():
        resolved = root / resolved
    if resolved.resolve() != feature_dir:
        raise PreflightError(
            f"Spec Kit resolved {resolved}, not the intended {feature_dir}. Planning would "
            "write a design into the wrong feature."
        )
    return feature_dir


# --------------------------------------------------------------------------
# Technical context
# --------------------------------------------------------------------------


def _pyproject(root: Path) -> dict:
    path = root / "pyproject.toml"
    if not path.is_file():
        return {}
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        # Unreadable evidence is not evidence. Discover nothing rather than guess.
        return {}


def _declared_requirements(data: dict) -> list[str]:
    project = data.get("project") or {}
    declared: list[str] = list(project.get("dependencies") or [])
    for group in (project.get("optional-dependencies") or {}).values():
        declared.extend(group or [])
    for group in (data.get("dependency-groups") or {}).values():
        declared.extend(group or [])
    return [item for item in declared if isinstance(item, str)]


def _declares(data: dict, distribution: str) -> bool:
    pattern = re.compile(rf"^{re.escape(distribution)}\b", re.IGNORECASE)
    return any(pattern.match(item.strip()) for item in _declared_requirements(data))


def repository_facts(root: Path) -> list[Fact]:
    """Return repository properties supported by direct file evidence.

    This is deliberately not a repository-understanding system. A property that
    needs interpretation to establish is left undiscovered, because an invented
    constraint outranks planner judgment and would do more damage than silence.
    """
    facts: list[Fact] = []

    python_version = root / ".python-version"
    if python_version.is_file():
        pinned = next(
            (
                line.strip()
                for line in python_version.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ),
            "",
        )
        if pinned:
            facts.append(Fact(f"Python {pinned}", ".python-version"))

    data = _pyproject(root)
    requires_python = (data.get("project") or {}).get("requires-python")
    if isinstance(requires_python, str) and requires_python.strip():
        facts.append(
            Fact(
                f"Python runtime constraint {requires_python.strip()}",
                "pyproject.toml [project] requires-python",
            )
        )

    for filename, manager in LOCKFILE_PACKAGE_MANAGERS:
        if (root / filename).is_file():
            facts.append(Fact(f"Package manager: {manager}", filename))

    tools = data.get("tool") or {}
    if "pytest" in tools or _declares(data, "pytest"):
        facts.append(Fact("Test framework: pytest", "pyproject.toml"))
    if "ruff" in tools or _declares(data, "ruff"):
        facts.append(Fact("Lint and format: Ruff", "pyproject.toml"))

    workflows = root / ".github" / "workflows"
    if workflows.is_dir():
        for workflow in sorted(
            path
            for path in workflows.iterdir()
            if path.is_file() and path.suffix in (".yml", ".yaml")
        ):
            relative = workflow.relative_to(root).as_posix()
            facts.append(Fact(f"Continuous integration is defined in {relative}", relative))

    return facts


def technical_context_skeleton(facts: list[Fact]) -> str:
    """Render the minimal `technical-context.md` skeleton for ``facts``."""
    lines = [
        "# Technical Context",
        "",
        "Constraints that outrank planner judgment. Decided product behavior belongs in",
        "`spec.md` and `decisions.md`, never here.",
        "",
        "## Repository facts",
        "",
        "Discovered from repository evidence by `rigorail.design_preflight`. Each line",
        "cites the file it was read from.",
        "",
    ]
    if facts:
        lines.extend(f"- {fact.statement} <!-- REPO_FACT: {fact.evidence} -->" for fact in facts)
    else:
        lines.append("- None discoverable from repository evidence.")
    lines.extend(
        [
            "",
            "## Human design constraints",
            "",
            "Written by a human. Never populated by inference: an empty list means nobody",
            "imposed a constraint, which leaves the choice to the planner.",
            "",
            "- None provided.",
            "",
            "## Unresolved constraints",
            "",
            "Constraints that design genuinely requires but nobody has established. Record",
            "one here rather than guessing it.",
            "",
            "- None recorded.",
            "",
        ]
    )
    return "\n".join(lines)


def ensure_technical_context(root: Path, feature_dir: Path) -> str:
    """Create the skeleton when absent. An existing file is never rewritten."""
    path = feature_dir / TECHNICAL_CONTEXT_FILENAME
    if path.exists():
        return "existing"
    path.write_text(technical_context_skeleton(repository_facts(root)), encoding="utf-8")
    return "created"


# --------------------------------------------------------------------------
# Command
# --------------------------------------------------------------------------


def preflight(root: Path, requested: str) -> list[str]:
    """Run every deterministic precondition. Returns the report lines."""
    feature_dir = resolve_feature_dir(root, requested)
    relative = feature_dir.relative_to(root.resolve()).as_posix()

    verify_frozen_spec(root, feature_dir)
    workspace = ensure_speckit(root)
    context = ensure_technical_context(root, feature_dir)
    pin_feature_directory(root, feature_dir)

    return [
        f"feature directory: {relative}",
        "frozen specification: verified (validate_spec.py exit 0)",
        f"spec kit workspace: {workspace} ({speckit_setup.SPECKIT_VERSION})",
        f"technical context: {context}",
        f"spec kit feature directory: pinned to {relative}",
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("feature_dir", help="feature directory, e.g. specs/team-invites")
    args = parser.parse_args(argv)

    try:
        root = speckit_setup.repository_root()
        report = preflight(root, args.feature_dir)
    except (PreflightError, speckit_setup.SetupError) as exc:
        print(f"design-preflight: {exc}", file=sys.stderr)
        return 1

    for line in report:
        print(f"design-preflight: {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
