# Working rules for this repository

- Keep changes minimal. Do not implement functionality beyond what was
  explicitly requested.
- No new dependencies without justification. Runtime dependencies stay empty
  unless there's a concrete need.
- Deterministic logic belongs in Python (`src/rigorail/`) with tests, not in
  shell scripts or prose instructions.
- Do not copy external framework code (BMAD, Spec Kit, Superpowers, GSD,
  Probity, Medusa skills, etc.) without recording provenance and license in
  `docs/sources.md`.
- Do not silently broaden scope. Resolve minor implementation details from
  existing repository conventions. Ask the user only when a decision changes
  requirements, architecture, risk, dependencies, or public behavior.
- Update documentation only when a change makes existing documentation
  materially inaccurate or changes a documented interface or architecture.
- Never treat an agent's statement that a check passed as evidence. Run the
  relevant deterministic command and report its actual result.
- Before declaring work complete, run the deterministic checks:

  ```bash
  uv run ruff format --check .
  uv run ruff check .
  uv run pytest
