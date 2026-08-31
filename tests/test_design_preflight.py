import json
import os
import stat
import textwrap

import pytest

from rigorail import design_preflight as p
from rigorail import speckit_setup as s

# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------


def make_feature(root, slug="team-invites", artifacts=("product-spec.md", "decisions.md")):
    feature = root / "specs" / slug
    feature.mkdir(parents=True)
    for name in artifacts:
        (feature / name).write_text(f"# {name}\n", encoding="utf-8")
    return feature


def make_script(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/usr/bin/env bash\n" + textwrap.dedent(body), encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def make_speckit_workspace(root, version=s.SPECKIT_VERSION):
    (root / ".specify").mkdir(parents=True, exist_ok=True)
    (root / ".specify" / "integration.json").write_text(json.dumps({"version": version}))
    make_script(root / p.SETUP_PLAN, 'echo "{}"\n')
    skill = root / ".claude" / "skills" / "speckit-plan"
    skill.mkdir(parents=True, exist_ok=True)
    (skill / "SKILL.md").write_text("# speckit-plan\n", encoding="utf-8")


# --------------------------------------------------------------------------
# Feature-directory handling
# --------------------------------------------------------------------------


def test_relative_feature_directory_resolves_without_shell_state(tmp_path):
    feature = make_feature(tmp_path)
    assert p.resolve_feature_dir(tmp_path, "specs/team-invites") == feature.resolve()


def test_absolute_feature_directory_resolves(tmp_path):
    feature = make_feature(tmp_path)
    assert p.resolve_feature_dir(tmp_path, str(feature)) == feature.resolve()


def test_missing_feature_directory_fails(tmp_path):
    with pytest.raises(p.PreflightError, match="does not exist"):
        p.resolve_feature_dir(tmp_path, "specs/absent")


def test_feature_directory_without_contract_fails(tmp_path):
    make_feature(tmp_path, artifacts=("product-spec.md",))
    with pytest.raises(p.PreflightError, match="decisions.md"):
        p.resolve_feature_dir(tmp_path, "specs/team-invites")


def test_feature_directory_outside_the_repository_fails(tmp_path):
    outside = tmp_path / "outside"
    root = tmp_path / "repo"
    root.mkdir()
    make_feature(outside)
    with pytest.raises(p.PreflightError, match="outside the repository root"):
        p.resolve_feature_dir(root, str(outside / "specs" / "team-invites"))


# --------------------------------------------------------------------------
# Frozen-specification gate
# --------------------------------------------------------------------------


def install_spec_validator(root, exit_code):
    validator = root / p.SPEC_VALIDATOR
    validator.parent.mkdir(parents=True, exist_ok=True)
    validator.write_text(
        f'import sys\nprint("open product decisions: 1")\nsys.exit({exit_code})\n',
        encoding="utf-8",
    )
    return validator


def test_frozen_spec_accepts_validator_exit_zero(tmp_path):
    feature = make_feature(tmp_path)
    install_spec_validator(tmp_path, 0)
    p.verify_frozen_spec(tmp_path, feature)


@pytest.mark.parametrize("exit_code", [1, 2])
def test_frozen_spec_rejects_nonzero_validator_exit(tmp_path, exit_code):
    feature = make_feature(tmp_path)
    install_spec_validator(tmp_path, exit_code)
    with pytest.raises(p.PreflightError) as excinfo:
        p.verify_frozen_spec(tmp_path, feature)
    assert f"exited {exit_code}" in str(excinfo.value)
    assert "open product decisions: 1" in str(excinfo.value)


def test_frozen_spec_fails_when_the_validator_is_absent(tmp_path):
    feature = make_feature(tmp_path)
    with pytest.raises(p.PreflightError, match="cannot be verified"):
        p.verify_frozen_spec(tmp_path, feature)


# --------------------------------------------------------------------------
# Spec Kit preflight
# --------------------------------------------------------------------------


def test_valid_speckit_workspace_is_left_unchanged(tmp_path, monkeypatch):
    make_speckit_workspace(tmp_path)

    def fail(*args, **kwargs):
        raise AssertionError("a valid workspace must not invoke the specify CLI")

    monkeypatch.setattr(p.speckit_setup, "resolve_cli", fail)
    monkeypatch.setattr(p.speckit_setup, "run_init", fail)
    assert p.ensure_speckit(tmp_path) == "verified"


def test_missing_speckit_workspace_is_regenerated(tmp_path, monkeypatch):
    calls = []

    def fake_run_init(root, specify):
        calls.append(specify)
        make_speckit_workspace(root)

    monkeypatch.setattr(p.speckit_setup, "resolve_cli", lambda: "/fake/specify")
    monkeypatch.setattr(p.speckit_setup, "run_init", fake_run_init)
    assert p.ensure_speckit(tmp_path) == "repaired"
    assert calls == ["/fake/specify"]


def test_speckit_preflight_is_idempotent(tmp_path, monkeypatch):
    calls = []

    def fake_run_init(root, specify):
        calls.append(specify)
        make_speckit_workspace(root)

    monkeypatch.setattr(p.speckit_setup, "resolve_cli", lambda: "/fake/specify")
    monkeypatch.setattr(p.speckit_setup, "run_init", fake_run_init)
    assert p.ensure_speckit(tmp_path) == "repaired"
    assert p.ensure_speckit(tmp_path) == "verified"
    assert len(calls) == 1


def test_stale_speckit_workspace_fails_clearly(tmp_path, monkeypatch):
    make_speckit_workspace(tmp_path, version="9.9.9")
    monkeypatch.setattr(p.speckit_setup, "resolve_cli", lambda: "/fake/specify")
    with pytest.raises(p.PreflightError, match="records Spec Kit 9.9.9"):
        p.ensure_speckit(tmp_path)


def test_extra_speckit_skill_is_pruned_rather_than_rescaffolded(tmp_path, monkeypatch):
    make_speckit_workspace(tmp_path)
    extra = tmp_path / ".claude" / "skills" / "speckit-implement"
    extra.mkdir(parents=True)
    (extra / "SKILL.md").write_text("# speckit-implement\n", encoding="utf-8")

    def fail(*args, **kwargs):
        raise AssertionError("pruning must need neither the CLI nor rescaffolding")

    monkeypatch.setattr(p.speckit_setup, "run_init", fail)
    monkeypatch.setattr(p.speckit_setup, "resolve_cli", fail)
    assert p.ensure_speckit(tmp_path) == "repaired"
    assert not extra.exists()


# --------------------------------------------------------------------------
# Command-scoped feature-directory pinning
# --------------------------------------------------------------------------


def install_setup_plan(root, body):
    return make_script(root / p.SETUP_PLAN, body)


def test_feature_directory_is_passed_command_scoped(tmp_path, monkeypatch):
    feature = make_feature(tmp_path)
    install_setup_plan(
        tmp_path,
        """
        printf '{"SPECS_DIR":"%s"}\\n' "$SPECIFY_FEATURE_DIRECTORY"
        """,
    )
    monkeypatch.delenv("SPECIFY_FEATURE_DIRECTORY", raising=False)
    assert p.pin_feature_directory(tmp_path, feature.resolve()) == feature.resolve()
    # No persistent shell state was created for the user.
    assert "SPECIFY_FEATURE_DIRECTORY" not in os.environ


def test_pinning_rejects_a_mismatched_resolution(tmp_path):
    feature = make_feature(tmp_path)
    make_feature(tmp_path, slug="other")
    install_setup_plan(tmp_path, 'echo \'{"SPECS_DIR":"specs/other"}\'\n')
    with pytest.raises(p.PreflightError, match="not the intended"):
        p.pin_feature_directory(tmp_path, feature.resolve())


def test_pinning_reports_a_failing_setup_script(tmp_path):
    feature = make_feature(tmp_path)
    install_setup_plan(tmp_path, 'echo "boom" >&2\nexit 3\n')
    with pytest.raises(p.PreflightError) as excinfo:
        p.pin_feature_directory(tmp_path, feature.resolve())
    assert "exited 3" in str(excinfo.value)
    assert "boom" in str(excinfo.value)


def test_pinning_requires_the_speckit_script(tmp_path):
    feature = make_feature(tmp_path)
    with pytest.raises(p.PreflightError, match="workspace is incomplete"):
        p.pin_feature_directory(tmp_path, feature.resolve())


def test_pinning_ignores_diagnostic_lines_before_the_json(tmp_path):
    feature = make_feature(tmp_path)
    install_setup_plan(
        tmp_path,
        """
        echo "Copied plan template"
        printf '{"SPECS_DIR":"%s"}\\n' "$SPECIFY_FEATURE_DIRECTORY"
        """,
    )
    assert p.pin_feature_directory(tmp_path, feature.resolve()) == feature.resolve()


# --------------------------------------------------------------------------
# Repository-fact discovery
# --------------------------------------------------------------------------


def test_no_facts_are_invented_in_an_empty_repository(tmp_path):
    assert p.repository_facts(tmp_path) == []


def test_python_version_file_is_a_fact(tmp_path):
    (tmp_path / ".python-version").write_text("3.13\n", encoding="utf-8")
    assert p.Fact("Python 3.13", ".python-version") in p.repository_facts(tmp_path)


def test_requires_python_is_a_fact(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x"\nrequires-python = ">=3.12"\n', encoding="utf-8"
    )
    facts = p.repository_facts(tmp_path)
    assert (
        p.Fact("Python runtime constraint >=3.12", "pyproject.toml [project] requires-python")
        in facts
    )


def test_lockfile_evidences_the_package_manager(tmp_path):
    (tmp_path / "uv.lock").write_text("", encoding="utf-8")
    assert p.Fact("Package manager: uv", "uv.lock") in p.repository_facts(tmp_path)


def test_test_and_lint_tooling_are_facts(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\ntestpaths = ["tests"]\n\n'
        '[dependency-groups]\ndev = ["ruff>=0.14"]\n',
        encoding="utf-8",
    )
    statements = {fact.statement for fact in p.repository_facts(tmp_path)}
    assert "Test framework: pytest" in statements
    assert "Lint and format: Ruff" in statements


def test_ci_workflows_are_facts(tmp_path):
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yaml").write_text("name: CI\n", encoding="utf-8")
    (workflows / "notes.txt").write_text("ignored\n", encoding="utf-8")
    facts = p.repository_facts(tmp_path)
    assert [fact.evidence for fact in facts] == [".github/workflows/ci.yaml"]


def test_malformed_pyproject_yields_no_fabricated_facts(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project\nname =", encoding="utf-8")
    assert p.repository_facts(tmp_path) == []


def test_unrelated_tooling_is_not_reported_as_a_fact(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x"\ndependencies = ["requests"]\n', encoding="utf-8"
    )
    statements = {fact.statement for fact in p.repository_facts(tmp_path)}
    assert "Test framework: pytest" not in statements
    assert "Lint and format: Ruff" not in statements


# --------------------------------------------------------------------------
# technical-context.md bootstrapping
# --------------------------------------------------------------------------


def test_skeleton_separates_repository_facts_from_human_constraints(tmp_path):
    text = p.technical_context_skeleton([p.Fact("Python 3.13", ".python-version")])
    assert "## Repository facts" in text
    assert "## Human design constraints" in text
    assert "## Unresolved constraints" in text
    assert "- Python 3.13 <!-- REPO_FACT: .python-version -->" in text
    assert "- None provided." in text


def test_skeleton_states_when_nothing_was_discoverable(tmp_path):
    text = p.technical_context_skeleton([])
    assert "- None discoverable from repository evidence." in text


def test_missing_technical_context_is_created(tmp_path):
    feature = make_feature(tmp_path)
    (tmp_path / ".python-version").write_text("3.13\n", encoding="utf-8")
    assert p.ensure_technical_context(tmp_path, feature) == "created"
    text = (feature / p.TECHNICAL_CONTEXT_FILENAME).read_text(encoding="utf-8")
    assert "<!-- REPO_FACT: .python-version -->" in text


def test_existing_technical_context_is_never_rewritten(tmp_path):
    feature = make_feature(tmp_path)
    original = "# Technical Context\n\n- hand written constraint\n"
    (feature / p.TECHNICAL_CONTEXT_FILENAME).write_text(original, encoding="utf-8")
    assert p.ensure_technical_context(tmp_path, feature) == "existing"
    assert (feature / p.TECHNICAL_CONTEXT_FILENAME).read_text(encoding="utf-8") == original


# --------------------------------------------------------------------------
# End to end
# --------------------------------------------------------------------------


def test_preflight_reports_every_step(tmp_path, monkeypatch):
    feature = make_feature(tmp_path)
    install_spec_validator(tmp_path, 0)
    make_speckit_workspace(tmp_path)
    install_setup_plan(
        tmp_path,
        """
        printf '{"SPECS_DIR":"%s"}\\n' "$SPECIFY_FEATURE_DIRECTORY"
        """,
    )
    monkeypatch.setattr(p.speckit_setup, "resolve_cli", lambda: "/fake/specify")

    report = p.preflight(tmp_path, "specs/team-invites")
    joined = "\n".join(report)
    assert "feature directory: specs/team-invites" in joined
    assert "frozen specification: verified" in joined
    assert "spec kit workspace: verified" in joined
    assert "technical context: created" in joined
    assert "pinned to specs/team-invites" in joined
    assert (feature / p.TECHNICAL_CONTEXT_FILENAME).is_file()


def test_preflight_stops_before_touching_the_feature_when_the_spec_is_not_frozen(tmp_path):
    feature = make_feature(tmp_path)
    install_spec_validator(tmp_path, 2)
    make_speckit_workspace(tmp_path)
    with pytest.raises(p.PreflightError, match="is not frozen"):
        p.preflight(tmp_path, "specs/team-invites")
    assert not (feature / p.TECHNICAL_CONTEXT_FILENAME).exists()
