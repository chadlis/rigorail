import json

import pytest

from rigorail import speckit_setup as s


def make_workspace(root, version=s.SPECKIT_VERSION, skills=("speckit-plan",)):
    specify = root / ".specify"
    (specify / "scripts" / "bash").mkdir(parents=True)
    (specify / "scripts" / "bash" / "setup-plan.sh").write_text("#!/usr/bin/env bash\n")
    (specify / "integration.json").write_text(json.dumps({"version": version}))
    for name in skills:
        skill = root / ".claude" / "skills" / name
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(f"# {name}\n")
    return root


def test_cli_version_parses_reported_version(monkeypatch):
    monkeypatch.setattr(
        s.subprocess,
        "run",
        lambda *a, **k: type("R", (), {"returncode": 0, "stdout": "specify 1.0.1\n", "stderr": ""}),
    )
    assert s.cli_version("specify") == "1.0.1"


def test_cli_version_rejects_unrecognised_output(monkeypatch):
    monkeypatch.setattr(
        s.subprocess,
        "run",
        lambda *a, **k: type("R", (), {"returncode": 0, "stdout": "unexpected\n", "stderr": ""}),
    )
    with pytest.raises(s.SetupError, match="Unrecognised"):
        s.cli_version("specify")


def test_workspace_version_absent(tmp_path):
    assert s.workspace_version(tmp_path) is None


def test_workspace_version_read(tmp_path):
    make_workspace(tmp_path)
    assert s.workspace_version(tmp_path) == s.SPECKIT_VERSION


def test_workspace_version_malformed(tmp_path):
    (tmp_path / ".specify").mkdir()
    (tmp_path / ".specify" / "integration.json").write_text("{not json")
    with pytest.raises(s.SetupError, match="malformed"):
        s.workspace_version(tmp_path)


def test_needs_init_when_workspace_absent(tmp_path):
    assert s.needs_init(tmp_path) is True


def test_needs_init_when_plan_skill_missing(tmp_path):
    make_workspace(tmp_path, skills=())
    assert s.needs_init(tmp_path) is True


def test_needs_init_false_when_complete(tmp_path):
    make_workspace(tmp_path)
    assert s.needs_init(tmp_path) is False


def test_needs_init_rejects_version_mismatch(tmp_path):
    make_workspace(tmp_path, version="9.9.9")
    with pytest.raises(s.SetupError, match="records Spec Kit 9.9.9"):
        s.needs_init(tmp_path)


def test_prune_removes_only_disallowed_speckit_skills(tmp_path):
    make_workspace(
        tmp_path,
        skills=("speckit-plan", "speckit-tasks", "speckit-implement", "rigorail-design"),
    )
    assert s.prune_skills(tmp_path) == ["speckit-implement", "speckit-tasks"]
    assert s.installed_speckit_skills(tmp_path) == ["speckit-plan"]
    assert (tmp_path / ".claude" / "skills" / "rigorail-design").is_dir()


def test_prune_is_idempotent(tmp_path):
    make_workspace(tmp_path, skills=("speckit-plan", "speckit-tasks"))
    s.prune_skills(tmp_path)
    assert s.prune_skills(tmp_path) == []


def test_verify_passes_on_pruned_workspace(tmp_path):
    make_workspace(tmp_path)
    s.verify(tmp_path)


def test_verify_rejects_extra_speckit_skill(tmp_path):
    make_workspace(tmp_path, skills=("speckit-plan", "speckit-tasks"))
    with pytest.raises(s.SetupError, match="beyond the allowlist"):
        s.verify(tmp_path)


def test_verify_rejects_missing_plan_skill(tmp_path):
    make_workspace(tmp_path, skills=())
    with pytest.raises(s.SetupError, match="no planner"):
        s.verify(tmp_path)


def test_repository_root_rejects_unrelated_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(s.SetupError, match="not the Rigorail repository root"):
        s.repository_root()
