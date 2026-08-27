---
name: rigorail-spec
description: Produce, review, and freeze a product specification from raw product context while preserving provenance, surfacing implementation-changing ambiguities, and forbidding reviewers from silently inventing or resolving product rules. Use when drafting a feature spec, clarifying requirements, auditing a spec against its sources, or deciding whether a spec is ready for technical design.
---

# Rigorail Spec

Build a product contract that is grounded, explicit about uncertainty, and cheap for a human to review.

The goal is not to maximize prose. The goal is to reach a spec where:

1. every firm product rule is grounded in a source or human decision;
2. every material ambiguity is either decided by a human or explicitly open;
3. reviewers expose semantic problems but never silently resolve them;
4. deterministic checks verify the mechanical parts of the contract.

## Outputs

For a feature `<slug>`, maintain exactly these primary artifacts:

```text
specs/<slug>/
├── spec.md
├── decisions.md
└── review.md
```

Use the templates bundled with this skill. Do not create extra planning documents during this workflow.

## Provenance types

Use these exact types in `decisions.md`:

- `SOURCE_FACT`: directly supported by an explicit source.
- `PREVIOUS_HUMAN_DECISION`: product behavior previously decided by a human and recovered from trusted project context.
- `NEW_HUMAN_DECISION`: product behavior decided by the human during this workflow.
- `INFERENCE`: plausible interpretation not yet authorized as a product rule.
- `TECHNICAL_DECISION`: implementation/design choice; not a product requirement unless it changes externally observable behavior and a human promotes it.
- `OPEN_PRODUCT_DECISION`: materially different product behaviors remain possible; blocks spec freeze.
- `OPEN_TECHNICAL_DECISION`: implementation choice intentionally deferred to technical design; does not block product-spec freeze unless it changes product behavior.

### Firm-rule provenance rule

Every `FR-*` and `SC-*` line in `spec.md` MUST end with a hidden provenance marker:

```html
<!-- provenance: S-001 -->
```

or:

```html
<!-- provenance: D-003 -->
```

`S-*` identifiers refer to source entries in `decisions.md`.
`D-*` identifiers refer to decision entries in `decisions.md`.

A firm requirement or success criterion may be grounded only by:

- `SOURCE_FACT` via an `S-*` source; or
- `PREVIOUS_HUMAN_DECISION`; or
- `NEW_HUMAN_DECISION`.

Never ground a firm rule with `INFERENCE`, `TECHNICAL_DECISION`, `OPEN_PRODUCT_DECISION`, or `OPEN_TECHNICAL_DECISION`.

## Workflow

Execute the following phases in order. Do not skip directly to planning.

### Phase 0 — Establish source boundary

1. Identify the product sources the user explicitly wants treated as authoritative.
2. Record each source in `decisions.md` as `S-###`.
3. Distinguish authoritative product sources from optional technical context.
4. Do not treat framework defaults, prior generated specs, or your own recommendations as product facts unless the user explicitly authorizes them.

If the source boundary is genuinely unclear and it changes what may be treated as authoritative, ask one concise question.

### Phase 1 — Discover only high-value decisions

Scan the source for implementation-changing ambiguity before drafting firm semantics.

Prioritize:

1. actor permissions;
2. cardinalities and ownership;
3. lifecycle/state transitions;
4. pricing/payment semantics;
5. destructive/reversal behavior;
6. routing and isolation;
7. failure/retry behavior;
8. scope boundaries that add or remove a meaningful feature.

A question is worth human attention when:

> Two competent implementers could choose materially different product behavior and both choices remain compatible with the current authoritative information.

Do not ask about:

- implementation details the technical-design phase can choose safely;
- naming preferences;
- low-impact defaults;
- best-practice choices that do not materially change product behavior.

Before asking, apply both gates:

1. **Required-flow gate** — the missing choice must be necessary to implement an in-scope behavior required by an authoritative source or already-authorized decision.
2. **Materiality gate** — different answers must materially change product behavior, data model, API contract, routing, permissions, money, lifecycle, or implementation scope.

Silence about an optional capability is not automatically an ambiguity. For example, if the source requires order placement but says nothing about cancellation, do not create a blocking cancellation decision merely because a cancellation feature could exist. Omission means the capability is not required by this spec unless the sourced flow cannot be implemented without choosing its behavior.

To reduce human turns, you MAY batch up to three independent high-impact questions. Never batch dependent questions or combine multiple decision dimensions into one question. For each question:

- state the ambiguity neutrally;
- explain in one or two sentences why it changes required implementation;
- give neutral options only when useful;
- always allow `leave open`;
- do not recommend an answer unless the human explicitly asks for a recommendation.

Record answers immediately in `decisions.md`.

If the user explicitly defers a product decision, record `OPEN_PRODUCT_DECISION`. Never infer a replacement rule.

### Phase 2 — Draft the compact spec

Draft `spec.md` from the sources and decided product semantics.

Keep it compact. Prefer requirements and examples over narrative.

Required sections:

```text
# <Feature>
## Goal
## Non-goals
## Actors
## User Flows
## Functional Requirements
## Acceptance Examples
## Key Entities
## Constraints
## Open Decisions
## Success Criteria
```

Rules:

- Do not invent priorities. If prioritization is useful but not sourced, record it as an inference or ask the human.
- Do not invent numeric targets to make success criteria measurable.
- Do not convert a best practice into `MUST` without provenance.
- Do not introduce lifecycle steps merely because they seem conventional.
- Keep implementation/framework choices out of the product spec unless they are explicit constraints supplied by the user.
- Keep product-open and technical-open decisions visibly separate.

### Phase 3 — Grounding review

Perform a source/provenance review before ambiguity review. The reviewer is read-only: it may write findings to `review.md`, but MUST NOT edit `spec.md`, `decisions.md`, validator code, templates, or tests.

Read `references/grounding-review.md` and follow it.

For every firm requirement and success criterion, ask:

> Where did this rule come from?

Classify unsupported statements instead of repairing them.

A grounding reviewer MAY:

- identify an unsupported rule;
- cite the conflicting or missing evidence;
- classify the risk;
- propose the product question that would authorize it.

A grounding reviewer MUST NOT:

- silently delete or rewrite product semantics to make the spec pass;
- infer a new rule from a single example;
- promote an `INFERENCE` into a firm requirement;
- choose among materially different valid behaviors.

Write findings to `review.md`.

### Phase 4 — Ambiguity review

Use a fresh-context reviewer when the environment supports subagents. Give it the authoritative sources, `spec.md`, and `decisions.md`, but not the drafting rationale or previous reviewer conclusions.

Read `references/ambiguity-review.md` and follow it.

The ambiguity reviewer looks for missing decisions, not unsupported inventions.

Keep the distinction strict:

```text
GROUNDING: did we invent something?
AMBIGUITY: did we fail to decide something?
```

The fresh-context reviewer is read-only. It reports candidate ambiguities; it MUST NOT mutate `spec.md`, `decisions.md`, scripts, templates, or tests.

A candidate ambiguity becomes an `OPEN_PRODUCT_DECISION` only after the human explicitly chooses to leave that material question open. Do not create blocking product decisions on the human's behalf. Low-value or optional-capability findings remain review notes and do not block freeze.

### Phase 5 — Human semantic gate

Present only the smallest high-risk surface that needs human attention:

1. blockers;
2. unsupported firm rules;
3. high-impact ambiguities;
4. product decisions that need confirmation;
5. technical questions intentionally deferred.

Do not ask the human to reread the full spec unless needed.

For each product blocker the human may:

- decide it now;
- remove the unsupported behavior;
- explicitly leave it open.

Update `decisions.md` first, then update `spec.md`.

### Phase 6 — Readiness and deterministic validation

Read `references/readiness.md`.

Treat the validator as an immutable black box during a spec run. Run it; do not inspect or modify its implementation or tests during this workflow. If it appears buggy, record `TOOLING_BUG` in `review.md`, report the failing command/output, and stop the deterministic gate. Fix tooling outside the run, then rerun the experiment.

Set `review.md` status to either:

```text
STATUS: READY
```

or:

```text
STATUS: BLOCKED
```

Run:

```bash
python .claude/skills/rigorail-spec/scripts/validate_spec.py specs/<slug>
```

During drafting, if intentionally open product decisions remain, use:

```bash
python .claude/skills/rigorail-spec/scripts/validate_spec.py --allow-open specs/<slug>
```

Do not claim the spec is frozen if the strict validator fails.

### Phase 7 — Freeze

Freeze the spec only when all are true:

- every firm `FR-*` and `SC-*` has valid provenance;
- no firm rule is grounded by inference or technical/open decisions;
- no unresolved high-impact product ambiguity remains;
- no grounding blocker remains;
- the spec is internally consistent enough to implement;
- strict deterministic validation passes;
- the human approves the semantic gate when a human decision was required.

A frozen product spec may still contain `OPEN_TECHNICAL_DECISION` entries if they do not alter product behavior.


## Provenance typing discipline

Use the smallest authoritative type that actually matches the evidence.

- If a claim is directly stated in an authoritative `S-*` source, cite that source directly from the spec. Do not manufacture a `PREVIOUS_HUMAN_DECISION` entry for it.
- Use `PREVIOUS_HUMAN_DECISION` only for a recoverable, explicit human choice made before this workflow.
- Use `NEW_HUMAN_DECISION` only for an explicit human answer in this workflow.
- An example demonstrates that the example can occur; it does not authorize global lifecycle, cardinality, provisioning, or mutability semantics.
- Never infer a feature lifecycle from the existence of an example object such as `Store A`.

## Product vs technical boundary

A choice is technical only when all viable options preserve the same externally observable product contract and scope.

If choosing differently would add/remove a user-visible capability, actor permission, business state, lifecycle transition, routing behavior, or admin operation, it is a product/scope question. Apply the required-flow gate before asking it; optional capabilities omitted by the source are normally simply not required, not blockers.

## Scope-minimality rule

The product spec defines what must exist for the sourced MVP. It does not need to decide every capability a future system could have.

Do not turn source silence into:

- an invented `MUST NOT`;
- an invented assumption;
- an `OPEN_PRODUCT_DECISION`; or
- an `OPEN_TECHNICAL_DECISION`

unless the choice is necessary to implement a required sourced behavior. If useful, mention an optional omitted capability as a non-blocking review note, but do not promote it into the contract.

## Reviewer non-resolution rule

This rule is absolute:

> A reviewer may identify, classify, and evidence an unresolved product decision. It must not resolve that decision by inferring a new business rule. Any finding admitting multiple materially different valid product behaviors requires a human decision before spec freeze.

Automatic fixes are allowed only for mechanical issues that do not change product semantics, such as broken references, duplicated identifiers, or formatting.

## Human-attention policy

Human attention is the scarce resource.

Prefer:

- deterministic validation for mechanically checkable properties;
- LLM judgment only for semantic grounding and ambiguity;
- fresh-context review for independent semantic checks;
- short blocker summaries rather than long review essays.

Stop asking clarification questions when the expected implementation-risk reduction is lower than the human attention cost. Defer purely technical choices to technical design.

## Token and tool discipline

During a normal run:

- read `SKILL.md`, the three templates, the authoritative product sources, and only the reference file needed for the current review phase;
- do not inspect `scripts/` or `tests/`; execute the validator as a black box;
- run at most one fresh-context ambiguity review pass;
- return at most five candidate ambiguity findings, ranked by risk;
- ask at most three independent high-value questions in one batch;
- do not rerun semantic reviewers after every answer; update the ledger/spec directly, then perform readiness once.

## Completion response

When the workflow finishes, report only:

- artifact paths;
- `READY` or `BLOCKED`;
- number of open product decisions;
- number of open technical decisions;
- number of unsupported/blocking findings;
- deterministic validator result;
- the next action.

Do not move into technical design unless the user asks.
