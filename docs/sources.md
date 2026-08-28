# Sources and provenance

Whenever a mechanism is copied, adapted, or materially inspired by an external
source, record:

- **Source/project**
- **Source type**: repository, documentation, paper, issue, article, etc.
- **URL**
- **Exact file or section**, when applicable
- **Revision/commit**, when applicable
- **Accessed date**
- **License / SPDX identifier**, when applicable
- **Relationship**: `copied`, `adapted`, or `inspired`
- **Local implementation**: where the resulting mechanism lives in Rigorail

Provenance must remain traceable regardless of repository visibility.

## Entries

### GitHub Spec Kit

- **Source/project**: Spec Kit (`github/spec-kit`)
- **Source type**: repository / slash-command toolkit
- **URL**: https://github.com/github/spec-kit
- **Exact file or section**: the `/speckit.plan` command
- **Revision/commit**: `1.0.1`, the tested baseline. Pinned exactly as the
  `specify-cli==1.0.1` dev dependency in `pyproject.toml` and locked in
  `uv.lock` with the distribution hashes, so a fresh clone resolves the same
  artifact. The same version is reported by `.specify/init-options.json`
  (`speckit_version`) and `.specify/integration.json` (`version`) in the
  generated workspace.
- **How it is obtained**: from PyPI, via the pinned dev dependency. Rigorail
  neither vendors nor redistributes Spec Kit. `specify init` scaffolds
  `.specify/` and the Claude-facing `speckit-*` skills from assets bundled
  inside that wheel, without network access, so those files are regenerated
  rather than committed — both paths are gitignored.
- **Accessed date**: 2026-08-27
- **License / SPDX identifier**: MIT (`specify_cli-1.0.1.dist-info/licenses/LICENSE`;
  https://github.com/github/spec-kit/blob/main/LICENSE). No Spec Kit code,
  template, or prompt text is copied, adapted, or redistributed in this
  repository; the package is consumed as an installed dependency.
- **Relationship**: external dependency. `rigorail-design` invokes
  `/speckit.plan` as the planning mechanism and reviews its output. Only that
  one Spec Kit skill is exposed to Claude; the others the Claude integration
  installs are pruned by the setup command below.
- **Local implementation**: `.claude/skills/rigorail-design/` (the reviewer),
  `src/rigorail/speckit_setup.py` (the deterministic setup/pruning command, run
  as `uv run python -m rigorail.speckit_setup`), and
  `src/rigorail/design_preflight.py`, which reuses that setup and invokes Spec
  Kit's own `.specify/scripts/bash/setup-plan.sh` with a command-scoped
  `SPECIFY_FEATURE_DIRECTORY` to select the feature. Spec Kit's documented
  interfaces are called; none of its code or prompt text is copied.
