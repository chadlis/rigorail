# EXP-001 — Specification Pipeline

**Status:** completed
**Rigorail spec skill:** v0.1
**Date:** 2026-08-27

## Goal

Evaluate lightweight mechanisms for turning raw product context into an implementation-ready specification while minimizing human review cost and preventing silent product decisions.

The experiment focused on three questions:

1. Can the workflow surface implementation-changing ambiguities?
2. Can it distinguish sourced requirements from inferred behavior?
3. Can unresolved product decisions remain explicit instead of being silently resolved by the model?

## Mechanisms evaluated

The experiment compared selected mechanisms from:

- a minimal generic LLM baseline;
- BMAD Product Brief / PRD / compact specification workflows;
- GitHub Spec Kit specification and clarification workflows;
- an initial Rigorail specification skill built from the observed strengths and failure modes.

The goal was not to adopt any framework wholesale.

## Main findings

### 1. Testable does not mean grounded

Multiple workflows produced requirements that were internally consistent and easy to test but were not actually authorized by the source material.

A specification workflow therefore needs a separate grounding/provenance check, not only consistency and testability checks.

### 2. Ambiguity review is valuable when it is read-only

A dedicated fresh-context ambiguity review consistently added value.

The useful behavior is:

- identify a materially different product interpretation;
- explain why it matters;
- ask the human if necessary;
- allow the decision to remain explicitly open.

The reviewer must not silently choose a product rule in order to make the specification complete.

### 3. Open decisions should be first-class artifacts

Unresolved product decisions should remain visible and block specification freeze when they materially affect implementation.

Technical decisions may be deferred to technical design when they do not alter required product behavior.

### 4. Provenance must be explicit

Firm requirements should be traceable to either:

- authoritative source material; or
- an explicit human decision.

An inference must not silently become a normative product requirement.

### 5. Human attention should be spent on semantic risk

The highest-value questions concern areas such as:

- cardinality and routing;
- state/lifecycle transitions;
- actor permissions;
- pricing and payment semantics;
- ownership and isolation;
- destructive or reversal behavior.

Low-impact implementation details should normally be deferred to technical design.

## Resulting Rigorail workflow

The experiment produced the first `rigorail-spec` skill.

Its intended workflow is:

```text
authoritative product context
        ↓
targeted discovery
        ↓
compact specification
        ↓
grounding / provenance review
        ↓
fresh-context ambiguity review
        ↓
human semantic gate
        ↓
deterministic readiness validation
        ↓
specification freeze
```

The primary artifacts are:

```text
spec.md
decisions.md
review.md
```

## Rigorail Spec v0.1

v0.1 includes:

- explicit source boundaries;
- provenance references for normative requirements;
- separate product and technical open decisions;
- fresh-context ambiguity review;
- explicit human deferral;
- deterministic validation before freeze;
- blocking of unresolved material product decisions;
- regression protection for the validator;
- safeguards preventing the skill from modifying its own validator or tests during a specification run.

## Evaluation result

**Verdict:** experimental / keep and refine

The overall architecture is promising and was more aligned with Rigorail's goals than adopting the evaluated frameworks unchanged.

The strongest observed properties were:

- compact output;
- explicit unresolved decisions;
- fresh-context ambiguity discovery;
- deterministic freeze gating;
- separation of product and technical decisions.

## Known limitations

v0.1 is not considered fully reliable yet.

Observed limitations include:

- provenance classification can still be too permissive for plausible inferences;
- a human answer may be recorded as a new decision even when the source already contained the answer;
- ambiguity discovery is incomplete;
- some questions may concern implementation sequencing rather than materially different product behavior.

These limitations are inputs to the next revision rather than reasons to add more process around the specification.

## Decision

Keep the Rigorail specification skill and continue iterating on it.

Do not adopt the full BMAD or Spec Kit workflow as the default Rigorail specification process.

The next experiment will evaluate the boundary between an approved product specification and technical design/planning.
