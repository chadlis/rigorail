# Architecture

This document describes what currently exists in the repository. Per
[docs/principles.md](principles.md) (principle 8), nothing here is
speculative: every area listed below is real and in use.

## `src/rigorail/`

Reusable deterministic logic, implemented in Python and covered by tests:

- `speckit_setup.py` — prepares the Spec Kit workspace described below.
- `design_preflight.py` — every precondition `rigorail-design` needs before
  planning that a program can decide: the feature directory resolves, the
  specification passes the `rigorail-spec` validator, the Spec Kit workspace is
  the pinned one, `technical-context.md` exists, and Spec Kit resolves the
  intended feature. It reuses `speckit_setup.py` rather than duplicating it, and
  configures Spec Kit through a command-scoped `SPECIFY_FEATURE_DIRECTORY` so no
  exported shell state is required from the user.

## `tests/`

Tests for `src/rigorail/`.

## `.claude/skills/`

Two Rigorail skills, each pairing an LLM-judgment workflow with deterministic
Python tooling that is run rather than trusted:

- `rigorail-spec/` — produce, review, and freeze a product contract:
  `source.md` (the informal input, verbatim), `product-spec.md` (addressable
  `§n.m` behaviors and `§Cn` constraints), `decisions.md` (an append-only
  ledger carrying layer, provenance, and status), and `discovery-review.md`
  (grounding, ambiguity, unresolved assumptions, and the human semantic
  gate). One product has one such contract, and `docs/` is where it lives; the
  validator takes a directory argument, but per-feature contracts are not the
  intended usage. Its `scripts/validate_spec.py` checks addressability,
  provenance, references, and structure, and fails closed on anything that
  visibly tries to be a product statement; it does not judge semantics. The
  skill stops at the frozen contract: backlog, delivery, and implementation
  state are outside it.
- `rigorail-design/` — turn a frozen specification into an implementation-ready
  technical design, and review that design against its product contract. It is
  available for experiments and for work that needs an explicit Rigorail design
  phase; it is not a mandatory stage between the frozen contract and downstream
  delivery. Its `scripts/validate_design.py` validator and `tests/` are
  deterministic and carry their own test suite. The validator also derives the next action from
  the review's findings — freeze, replan, or ask the human — and bounds the
  automatic repair loop, so routing is decided by a program rather than by the
  reviewer's reading of its own review.

Each skill runs its deterministic validator itself and respects its exit code.
Neither may report a frozen or `READY` state on prose alone.

## Spec Kit integration

`rigorail-design` does not plan. It invokes GitHub Spec Kit's `/speckit.plan`
as the external planner and reviews the result.

Spec Kit is pinned as the `specify-cli==1.0.1` dev dependency and is not
vendored. `uv run python -m rigorail.speckit_setup` scaffolds `.specify/` and
the Claude-facing Spec Kit skills offline from assets bundled in that pinned
wheel, then prunes them to the single skill Rigorail uses, `speckit-plan`. Both
generated paths are gitignored because they are reproducible from the pin.
`design_preflight.py` invokes that setup on the normal path, so the explicit
command remains available for maintenance rather than being a step the user must
remember.

Provenance is recorded in [sources.md](sources.md).

## Project and tooling files

`pyproject.toml`, `uv.lock`, `.python-version`, `.gitignore`, and
`.editorconfig` configure the Python package, dependency locking, and
formatting/linting via `uv` and Ruff.

`.github/workflows/ci.yaml` runs formatting, linting, and every test suite.
CI is deterministic and requires no LLM.

## `docs/`

- [principles.md](principles.md) — the principles this project is judged
  against.
- [architecture.md](architecture.md) — this file.
- [sources.md](sources.md) — provenance recording for any mechanism copied,
  adapted, or inspired by an external source.
- [evaluations/](evaluations/) — one record per experiment: what was evaluated,
  what was found, and what was kept.

## Future top-level concepts

Skills and an external planner integration now exist, each introduced in
response to a concrete experiment (EXP-001, EXP-002) rather than ahead of the
evidence. Ideas like agents, hooks, and profiles are still not part of the
repository. Per principles 8–10, each must be introduced only in response to a
concrete experiment or an observed need — not added speculatively ahead of that
evidence.
