# Architecture

This document describes what currently exists in the repository. Per
[docs/principles.md](principles.md) (principle 8), nothing here is
speculative: every area listed below is real and in use.

## `src/rigorail/`

Reusable deterministic logic, implemented in Python and covered by tests.

## `tests/`

Tests for `src/rigorail/`.

## Project and tooling files

`pyproject.toml`, `uv.lock`, `.python-version`, `.gitignore`, and
`.editorconfig` configure the Python package, dependency locking, and
formatting/linting via `uv` and Ruff.

## `docs/`

- [principles.md](principles.md) — the principles this project is judged
  against.
- [architecture.md](architecture.md) — this file.
- [sources.md](sources.md) — provenance recording for any mechanism copied,
  adapted, or inspired by an external source.

## Future top-level concepts

Ideas like skills, agents, hooks, profiles, templates, and other
integrations are not part of the repository yet. Per principles 8–10, each
must be introduced only in response to a concrete experiment or an observed
need — not added speculatively ahead of that evidence.
