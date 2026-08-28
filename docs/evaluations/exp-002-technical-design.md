# EXP-002 — Technical Design / Planning

**Status:** completed
**Rigorail design skill:** v0.1
**Tested Spec Kit baseline:** 1.0.1
**Date:** 2026-08-27

## Goal

Evaluate lightweight mechanisms for transforming an approved product specification into an implementation-ready technical design without silently inventing or changing product behavior.

The experiment focused on seven questions:

1. Can the planner preserve the approved product contract while concretizing architecture, data models, contracts, and workflows?
2. Can the workflow distinguish unresolved product semantics from legitimate technical decisions?
3. Can the planner resolve the technical decisions required for implementation without escalating unnecessary questions to the human?
4. Can the design prefer appropriate framework-native primitives without creating unnecessary custom abstractions or framework adoption?
5. Can a fresh-context reviewer detect silent product invention introduced during technical concretization?
6. Can deterministic tooling verify decision accounting and design-readiness structure without pretending to verify semantics?
7. Does the resulting workflow reduce human attention to true product-semantic decisions?

## Mechanisms evaluated

The experiment compared selected planning and review mechanisms from:

- a minimal generic LLM technical-planning baseline;
- GitHub Spec Kit `/speckit.plan`, tested with Spec Kit 1.0.1;
- fresh-context, read-only technical-design review;
- an initial Rigorail design skill built from the observed strengths and failure modes;
- deterministic design-readiness validation;
- a fresh end-to-end smoke test of the resulting workflow.

The goal was not to adopt Spec Kit wholesale.

No third planning framework was added because the first two runs exposed the main decision-boundary failure clearly enough that another expensive framework comparison did not have demonstrated marginal value.

## Main findings

### 1. Technical completeness can be purchased by product invention

Spec Kit produced stronger planning artifacts than the generic baseline in areas such as:

- technical research;
- explicit decision rationale;
- data modeling;
- interface contracts;
- implementation structure;
- quickstart / acceptance mapping.

However, some of that additional concreteness came from silently resolving product semantics that were not authorized by the approved specification.

Observed examples included unsupported required fields and other concrete product behavior introduced while making the plan more implementation-ready.

The key result is:

> More concrete does not necessarily mean more correct.

A design workflow therefore needs a product-semantic preservation review after technical concretization, not only before planning.

### 2. The product / technical boundary is about semantic commitment, not mere observability

The experiment initially used observable behavior as the main heuristic for distinguishing product decisions from technical decisions.

The E2E smoke test and two independent adversarial reviews showed that observability alone is too broad.

Implementations necessarily exhibit incidental observable behavior such as:

- ordering;
- opaque identifier representation;
- framework-standard transport conventions;
- implementation-local defaults.

These do not automatically require human product authority.

A choice requires product authority when alternatives materially change a product-semantic commitment, such as:

- an explicit approved requirement;
- business meaning or user rights;
- permissions, ownership, isolation, security, privacy, or visibility;
- lifecycle or economically meaningful outcomes;
- a stable/public interface guarantee;
- behavior consumers are expected to rely on;
- an acceptance outcome that must remain stable.

Incidental behavior may remain implementation-defined, but the planner must not promote it into an approved product guarantee or acceptance criterion without grounding.

### 3. PRODUCT_INVENTION and PRODUCT_BLOCKER require different routing

The experiment confirmed that unsupported planner behavior should not automatically become a human question.

`PRODUCT_INVENTION` applies when the planner introduces an unsupported product-semantic guarantee that is not required for implementation.

Routing:

```text
PRODUCT_INVENTION
→ planner
```

The planner removes the unsupported guarantee without asking the human to invent a replacement rule.

`PRODUCT_BLOCKER` applies when correct implementation genuinely requires an authoritative product-semantic commitment and the approved contract does not determine one unique required meaning.

This includes:

- missing product semantics;
- materially conflicting approved product rules.

Routing:

```text
PRODUCT_BLOCKER
→ human
```

This distinction is central to minimizing human attention.

### 4. Technical choices need explicit ownership and deterministic accounting

Open technical decisions are legitimate inputs to technical planning.

The planner is expected to resolve them when they preserve approved product semantics.

Every declared `OPEN_TECHNICAL_DECISION` must be accounted for exactly once as either:

```text
RESOLVED_TECHNICAL_DECISION
XOR
UNRESOLVED_TECHNICAL_DECISION
```

This accounting is enforced deterministically.

The reviewer does not need to infer whether a declared technical decision disappeared silently.

### 5. Missing technical choice and insufficient mechanism are different failures

The experiment refined the boundary between:

- `UNRESOLVED_TECHNICAL_DECISION`; and
- `TECHNICAL_INTEGRITY_GAP`.

Use:

```text
no mechanism chosen
→ UNRESOLVED_TECHNICAL_DECISION

mechanism chosen, but it does not guarantee a required invariant
→ TECHNICAL_INTEGRITY_GAP
```

Likewise:

```text
design explicitly specifies behavior contrary to approved product semantics
→ PRODUCT_CONTRADICTION

design claims to preserve the product invariant, but its mechanism does not enforce it
→ TECHNICAL_INTEGRITY_GAP
```

This keeps ownership clear without adding more categories.

### 6. High-severity integrity gaps must cover invariant-breaking failures

Only HIGH technical-integrity gaps block design freeze.

The experiment therefore tightened the meaning of HIGH.

A `TECHNICAL_INTEGRITY_GAP` is HIGH when, unresolved, it can plausibly:

- violate an approved product invariant;
- violate authorization, isolation, privacy, visibility, or security semantics;
- corrupt durable state or durable correctness;
- cause economically meaningful duplication, loss, or inconsistent outcomes;
- cause materially incorrect partial failure;
- require non-local architectural redesign if discovered during implementation.

This prevents false READY caused by under-classifying a security or correctness failure as a non-blocking technical detail.

### 7. Framework assumptions need explicit verification treatment

Technical plans frequently depend on framework or platform behavior.

Rigorail distinguishes:

```text
VERIFIED_FRAMEWORK_FACT
NEEDS_FRAMEWORK_VERIFICATION
```

and review findings may use:

```text
UNVERIFIED_FRAMEWORK_FACT
```

An unverified framework premise may remain non-blocking only when:

- falsification before ship exercises the actual relevant framework/platform/version behavior;
- the check deterministically fails before ship if the premise is false;
- recovery is local;
- correction does not require changed product semantics, changed security/privacy guarantees, or non-local redesign.

A load-bearing assumption cannot remain merely a non-blocking framework note when falsity would invalidate the architecture or a required invariant.

### 8. Fresh-context review is useful but not semantic proof

A fresh-context reviewer added value by avoiding direct inheritance of the planner's conversational rationale.

The reviewer receives:

- authoritative product inputs;
- technical context;
- frozen generated design artifacts.

It does not receive planning history or prior review conclusions.

This reduces rationalization inheritance, but repeated reviews showed that semantic finding discovery remains incomplete and non-deterministic.

Therefore:

```text
fresh-context review
≠ semantic proof
```

The workflow should not add multiple reviewers or voting without evidence that the additional cost produces meaningful marginal value.

### 9. Product silence must not become a hidden product rule

The E2E smoke test exposed two related failures:

```text
product silent on empty-string validity
→ planner silently accepted empty strings
```

and later:

```text
product silent on maximum length
→ planner guaranteed unbounded acceptance
```

The resulting rules are:

- absence of a product constraint does not authorize a restrictive default;
- absence of a product constraint does not authorize a permissive or unbounded product guarantee;
- implementation-defined incidental behavior may exist without becoming product semantics;
- human escalation is required only when an authoritative product-semantic commitment is genuinely necessary.

These rules were discovered and retested on the same synthetic smoke fixture, so the mechanism is considered principled but not independently validated for generalization. A first held-out exercise of these rules is recorded below; it is one data point, not generalization evidence.

## Resulting Rigorail workflow

The experiment produced the first `rigorail-design` skill.

Its intended workflow is:

```text
approved / frozen specification
        ↓
Spec Kit version + availability preflight
        ↓
technical-design planning
        ↓
freeze generated design artifacts
        ↓
fresh-context read-only design review
        ↓
route findings by ownership
        ↓
human semantic gate only for PRODUCT_BLOCKER
        ↓
deterministic readiness validation
        ↓
design freeze
```

The authoritative inputs are:

```text
spec.md
decisions.md
technical-context.md
```

The authority order is:

```text
approved product semantics
        ↓
technical constraints
        ↓
planner technical judgment
```

Typical generated planning artifacts include:

```text
plan.md
research.md
data-model.md
contracts/
quickstart.md
```

Rigorail adds:

```text
design-review.md
```

## Rigorail Design v0.1

v0.1 includes:

- explicit product / technical authority boundaries;
- semantic-commitment rather than mere-observability routing;
- distinct handling of product contradictions, inventions, and blockers;
- explicit routing by finding ownership;
- fresh-context, read-only design review;
- frozen plan artifacts before review;
- deterministic accounting of declared open technical decisions;
- explicit resolved-technical-decision ledger;
- framework-fact verification states;
- technical-integrity review for failure, retry, concurrency, isolation, and partial-failure risks;
- deterministic status derivation;
- deterministic validator exit codes;
- safeguards preventing the validator or tests from being modified during an active design run;
- READY defined as implementation-ready under the Rigorail gate, not semantic proof.

The design validator checks structure and accounting only.

It intentionally does not claim to determine:

- whether a finding is semantically classified correctly;
- whether evidence is true;
- whether architecture is good;
- whether a hidden product invention exists in prose;
- whether a framework claim is factually correct.

## Spec Kit packaging and reproducibility

The tested Spec Kit baseline is:

```text
1.0.1
```

`specify-cli==1.0.1` is pinned as a project development dependency.

Rigorail does not vendor Spec Kit planning prompts or generated workspace files.

A deterministic setup mechanism regenerates the Spec Kit workspace from the assets bundled with the pinned dependency and exposes only the planning capability required by Rigorail:

```text
speckit-plan
```

The generated `.specify/` workspace and generated Spec Kit Claude-facing skills remain local rather than being committed. Regeneration was verified byte-identical to the previously generated workspace apart from install timestamps, and the Claude integration installs ten skills of which nine are pruned.

The setup is intended to be:

- deterministic;
- idempotent;
- version-checked;
- offline after dependency installation;
- free of LLM logic.

CI remains LLM-free.

## Evaluation result

**Verdict:** keep and freeze as v0.1; validate generalization on new features

The resulting architecture is more aligned with Rigorail's goals than adopting Spec Kit planning unchanged.

The strongest observed properties were:

- strong technical planning from Spec Kit without adopting the full Spec Kit workflow;
- explicit product / technical decision ownership;
- routing product invention back to the planner instead of turning every invention into a human question;
- human escalation only for genuine product-semantic blockers;
- deterministic decision accounting;
- fresh-context review after technical concretization;
- deterministic design-freeze gating;
- reproducible Spec Kit version/setup.

The E2E smoke test exercised both major routing paths:

```text
true missing product semantics
→ PRODUCT_BLOCKER
→ human

unsupported planner-created product guarantee
→ PRODUCT_INVENTION
→ planner
```

and reached:

```text
STATUS: READY
validator exit 0
```

after the appropriate corrections.

## Held-out validation

Because the smoke fixture became a tuning set during rule discovery, the frozen workflow was exercised once on a new feature that had never been used for tuning, starting from a one-paragraph product draft. No rule was changed as a result of this run; it was validation, not tuning.

Specification stage:

- the grounding review caught an unsupported cardinality claim in the drafted spec — a phrase in the source generalized into an entity rule — which was removed rather than decided in either direction;
- the fresh-context ambiguity reviewer independently surfaced a question that had been deliberately withheld from the discovery batch, and ranked it a blocker;
- three findings were decided by the human; two lower-risk findings remained non-blocking review notes rather than being promoted into open product decisions;
- strict validation reached `STATUS: READY`, exit `0`, with zero open product decisions and one open technical decision.

Design stage, two review rounds:

```text
round 1 → 2 HIGH TECHNICAL_INTEGRITY_GAPS → NEEDS_TECHNICAL_WORK → exit 2
round 2 → 1 HIGH TECHNICAL_INTEGRITY_GAP  → NEEDS_TECHNICAL_WORK → exit 2
```

- one round-1 gap was a partial-failure path the planner had deliberately left unresolved rather than deciding silently;
- the other was a load-bearing framework premise that the four-part test moved out of `UNVERIFIED_FRAMEWORK_FACTS` into a blocking gap, because no pre-ship check exercised the real behavior;
- the round-2 gap had not been planted: the design specified a data store that its own `technical-context.md` placed behind an external boundary, invalidating a claimed transactional atomicity;
- across both rounds no incidental choice was escalated to the human. Normalization, transport status codes, identifier type, list ordering, absence of an expiry, and a single-column ownership representation were all correctly left with the planner.

The loop was stopped after round 2 by choice; the design did not reach READY on this feature. Both fixtures were disposable and are not committed.

What this run supports: the routing and severity rules behaved as specified on a feature they were not tuned against, and the review found a real defect its author had not anticipated. What it does not support: any claim of general reliability. It is one feature.

## Known limitations

v0.1 is not considered semantically complete or proven to generalize.

Observed or retained limitations include:

- fresh-context semantic review is probabilistic and does not reliably rediscover every non-blocking finding;
- product / technical classification still requires LLM judgment;
- framework-fact load-bearing classification remains reviewer judgment;
- the deterministic validator does not verify evidence truth or inspect the semantic correctness of the generated plan;
- the Personal Notes E2E fixture became a tuning set during rule discovery and must not be used as evidence of future generalization;
- held-out validation covers one feature and one design loop that was stopped before freeze, so it is a single data point;
- the generic baseline and Spec Kit run differ in planner structure and available mechanisms, so causal attribution to a single Spec Kit feature is limited;
- an unsatisfiable, false, or ambiguous `technical-context.md` constraint does not yet have a dedicated finding category. In the held-out run an ambiguous constraint — stating that a dependency existed at the application boundary without stating whether that boundary is local or remote — propagated into a HIGH design gap. The gate caught the consequence, but the root cause was an unvalidated input;
- `technical-context.md` has no producing workflow and no deterministic validation; v0.1 adds only a documented skeleton;
- only Spec Kit 1.0.1 has been exercised as the planning baseline;
- each design round costs a full fresh-context review; convergence across rounds was observed but not measured;
- the implementation / coding stage has not yet been experimentally frozen to the same degree as specification and technical design.

These limitations are inputs to future experiments rather than reasons to add more process to v0.1.

## Decision

Keep `/speckit.plan` as the technical-planning mechanism behind the Rigorail control layer.

Do not adopt the full Spec Kit workflow as the default Rigorail development process.

Keep `rigorail-design` as a thin semantic-boundary, review, routing, and deterministic-gating layer.

Freeze the current design workflow as `rigorail-design-v0.1` after repository checks pass.

Do not continue tuning the design skill on the Commerce benchmark or Personal Notes smoke fixture.

The next experimental stage should evaluate implementation from a frozen specification and technical design on a new real or held-out feature.
