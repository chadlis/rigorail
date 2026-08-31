---
name: rigorail-spec
description: Produce, review, and freeze a product specification from raw product context while preserving provenance, surfacing implementation-changing ambiguities, and forbidding reviewers from silently inventing or resolving product rules. Use when drafting a feature spec, clarifying requirements, auditing a spec against its sources, or deciding whether a spec is ready for technical design.
---

# Rigorail Spec

Build a product contract that is grounded, addressable, explicit about
uncertainty, and cheap for a human to review.

The goal is not to maximize prose. The goal is to reach a contract where:

1. every firm product statement is grounded in a source or a human decision;
2. every firm product statement has a stable, unique identifier;
3. every material ambiguity is either decided by a human or explicitly open;
4. reviewers expose semantic problems but never silently resolve them;
5. deterministic checks verify the mechanical parts of the contract.

## Scope boundary

This skill owns exactly one transition:

```text
informal authoritative source
→ clarified product contract
→ explicit product decisions
→ semantic review
→ frozen desired product state
```

It stops there. Backlog management, issue-tracker synchronization, change
planning, technical design, implementation, CI orchestration, delivery state,
and test-to-requirement coverage are downstream concerns and must never be
added here.

## Outputs

One product has one Rigorail contract, and it lives in `docs/`:

```text
docs/
├── source.md             # the authoritative informal input, verbatim
├── product-spec.md       # the desired product state, addressable
├── decisions.md          # append-only decision ledger
└── discovery-review.md   # grounding/ambiguity/readiness review
```

The validator accepts a directory argument, but the canonical project contract
lives in `docs/`. Do not create one contract per feature: a feature is a slice
of the same `docs/product-spec.md`, addressed by its `§` ids, not a document of
its own.

Use the templates bundled with this skill. Do not create extra planning
documents during this workflow.

### `source.md`

Preserve the human's original product input **verbatim**. It is provenance, not
a generated specification.

- never rewrite the input into a cleaner brief;
- never mix a generated interpretation into a source block;
- append further authoritative material as a new block rather than editing an
  existing one;
- a large or binary source may be referenced by path instead of pasted.

The validator never parses `source.md`. Nothing written there can create a
source, a decision, or a product statement: those exist only in `decisions.md`
and `product-spec.md`.

## Product statement identifiers

Every firm product statement in `product-spec.md` carries a Product ID.

```text
PRODUCT_ID := \d+\.\d+ | C\d+
```

```text
§n.m  product behavior / product obligation
§Cn   product constraint
```

Behaviors live under numbered level-2 sections whose number is the major part
of every id inside them. Constraints live under `## §C Constraints`.

```markdown
## §1 Notes

- **§1.1** — A user can create a note. <!-- provenance: S-001 -->
- **§1.2** — A user can edit a note. <!-- provenance: S-001 -->

## §C Constraints

- **§C1** — Customer data is hosted within the European Union. <!-- provenance: S-002 -->
```

Ids must be unique across behaviors, constraints, and withdrawn statements.

The form above is the only accepted one: a list item, the id in bold, a real em
dash, and a non-empty body. The validator rejects every near-miss rather than
skipping it, so a statement can never fall out of the contract by being written
slightly wrong.

### One `§` is one product obligation

Each id must correspond to exactly one independently deliverable, independently
testable product obligation. Downstream delivery tracking uses these ids as
accounting units, so a bundled statement cannot be tracked.

Bad:

```text
§1.1 — A user can create, edit, delete, and share a note.
```

Better:

```text
§1.1 — A user can create a note.
§1.2 — A user can edit a note.
§1.3 — A user can delete a note.
§1.4 — A user can share a note.
```

Atomicity is semantic, not syntactic. Do not mechanically split every sentence
containing "and". This is one obligation and should stay one:

```text
§1.1 — A user can create a note with a title and body.
```

The validator emits a warning for statements that enumerate several actions. A
warning is a prompt to look, never a proof that a statement is or is not
atomic.

### Behavior or constraint?

- **Behavior** — something the product must allow, reject, show, or preserve,
  triggered by an actor or an event.
- **Constraint** — a property the product must satisfy *continuously*, whose
  violation would matter to a user, customer, audit, contract, or authoritative
  product commitment.

Constraints legitimately cover hosting and geography, supported platforms,
file/interchange formats, regulatory or contractual commitments, and externally
observable compatibility requirements.

An implementation preference is not a product constraint:

```text
§C3 — Use PostgreSQL.          # wrong: a technical choice
§C4 — Use a repository pattern. # wrong: a technical choice
```

unless the human established it as an externally binding product commitment,
which is unusual.

### Semantic stability of ids

A Product ID names an obligation, not a sentence.

**Editorial change — same id.** Wording changes, the obligation does not:

```text
§1.3 — Users can remove their own notes.
→ §1.3 — A user can delete a note they own.
```

Only when the two are explicitly judged semantically equivalent.

**Product-semantic change — new id, and explicit withdrawal of the old one.**
Required observable behavior changes:

```text
§1.3 — A user can delete a note.
→ desired: a deleted note can be restored for 30 days
```

Do not rewrite `§1.3` in place and let downstream references keep pointing at
it. Write the new obligation under a new id, record the change as a `PRODUCT`
`HUMAN` decision naming the old id, and list the old id under `## Withdrawn` in
`product-spec.md`. A withdrawn id keeps existing references resolvable and is
never reused for different behavior.

This skill only authors ids under this rule. Tracking whether downstream
artifacts are still fresh is not its job.

### Ids do not replace provenance

Adding a `§` id makes a statement **addressable**. It does not make it
**grounded**. The two checks are independent, and both are required: every firm
statement still carries a provenance marker naming the source or the decision
that authorized it. An id on an invented rule is an invented rule with an id.

## The decision ledger

`decisions.md` is append-only and carries two independent axes plus a state:

```text
layer:      PRODUCT | TECHNICAL
provenance: SOURCE | HUMAN | INFERRED
status:     decided | open | unconfirmed
```

```text
- **D-###** [YYYY-MM-DD] [LAYER] [PROVENANCE] [status:<state>] [risk:<level>] — <scope> — <decision> — <rationale> — reversible:<Y|N>
```

```text
- **D-001** [2026-09-02] [PRODUCT] [HUMAN] [status:decided] [risk:high] — §1.4 — Deletion is permanent in V1 — Keep V1 simple — reversible:Y
- **D-002** [2026-09-02] [PRODUCT] [SOURCE] [status:decided] [risk:high] — §C1 — Customer data remains in the EU — Stated in S-001 — reversible:N
- **D-003** [2026-09-02] [TECHNICAL] [INFERRED] [status:unconfirmed] [risk:low] — foundation — Use framework-native validation — Lower custom complexity — reversible:Y
```

`<scope>` is a Product ID when the decision governs a specific statement, or a
short word such as `foundation` when it does not. Every `§` reference in the
ledger must resolve to a statement that exists.

Sources are separate and stable:

```text
- **S-001** — source.md block S-001 — verbatim product input from the human
```

### Grounding rules

Only these may ground a firm `§` statement:

- an `S-###` source; or
- a `PRODUCT` decision with `status:decided` and `SOURCE` or `HUMAN`
  provenance.

Never ground a firm statement with `INFERRED` provenance, a `TECHNICAL`
decision, or an entry with `status:open` or `status:unconfirmed`.

`INFERRED` does **not** mean an agent's inference has become authoritative. An
inference is a candidate. It becomes firm only when a human decides it at the
semantic gate, which produces a `HUMAN` `status:decided` entry. The validator
rejects an `INFERRED` entry marked `status:decided` for exactly this reason.

`SOURCE` provenance means an authoritative source says so, and the entry must
cite at least one `S-###`, each of which must be declared under
`decisions.md > Sources`. A citation of a source that does not exist is
rejected: otherwise "stated in S-999" would ground a rule that nothing states.
Prefer citing the source directly from the spec over manufacturing a `D-###`
for a fact a source already states.

An open `PRODUCT` decision blocks the freeze. An open `TECHNICAL` decision does
not, unless it changes externally observable product behavior.

Two further typing rules:

- an example demonstrates that the example can occur; it does not authorize
  global lifecycle, cardinality, provisioning, or mutability semantics;
- never infer a feature lifecycle from the existence of an example object such
  as `Store A`.

`decisions.md` is written by this phase for `PRODUCT` decisions. The
`TECHNICAL` layer exists so later phases can share the same ledger. Do not
start doing technical design because the ledger can hold technical entries.

## Workflow

Execute the following phases in order. Do not skip directly to drafting.

### Phase 0 — Establish the source boundary

1. Write the human's authoritative product input into `source.md`, verbatim.
2. Record each source in `decisions.md` as `S-###`, pointing at its block in
   `source.md` or at the file that holds it.
3. Distinguish authoritative product sources from optional technical context.
4. Do not treat framework defaults, prior generated specs, or your own
   recommendations as product facts unless the user explicitly authorizes them.

If the source boundary is genuinely unclear and it changes what may be treated
as authoritative, ask one concise question.

### Phase 1 — Discover only high-value decisions

Scan the source for implementation-changing ambiguity before drafting firm
semantics.

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

> Two competent implementers could choose materially different product behavior
> and both choices remain compatible with the current authoritative
> information.

Good questions look like: is deletion permanent or reversible? Can a workspace
have multiple administrators? Is an empty title allowed? What does a user
observe when payment fails?

Do not escalate ordinary technical choices: table layout, framework primitives,
internal module boundaries, ORM choice, endpoint structure, cache strategy, or
implementation sequencing. If a technical choice would materially alter the
product contract, surface the **product consequence** rather than asking the
human to pick an implementation.

Before asking, apply both gates:

1. **Required-flow gate** — the missing choice must be necessary to implement
   an in-scope behavior required by an authoritative source or an
   already-authorized decision.
2. **Materiality gate** — different answers must materially change product
   behavior, data model, API contract, routing, permissions, money, lifecycle,
   or implementation scope.

Silence about an optional capability is not automatically an ambiguity. If the
source requires order placement but says nothing about cancellation, do not
create a blocking cancellation decision merely because cancellation could
exist. Omission means the capability is not required unless the sourced flow
cannot be implemented without choosing its behavior.

To reduce human turns, you MAY batch up to three independent high-impact
questions. Never batch dependent questions or combine multiple decision
dimensions into one question. For each question:

- state the ambiguity neutrally;
- explain in one or two sentences why it changes required implementation;
- give neutral options only when useful;
- always allow `leave open`;
- do not recommend an answer unless the human explicitly asks.

Record answers immediately in `decisions.md`.

If the user explicitly defers a product decision, record it as `[PRODUCT] …
[status:open]`. Never infer a replacement rule.

### Phase 2 — Draft the compact contract

Draft `product-spec.md` from the sources and decided product semantics.

Keep it compact. This is a product contract, not a PRD. Prefer statements and
examples over narrative.

Required sections:

```text
# <Feature>
## Goal
## Non-goals
## Actors
## User Flows
## §1 <Behavior group>          (one or more numbered behavior sections)
## §C Constraints
## Acceptance Examples
## Key Entities
## Open Decisions
## Withdrawn                    (optional)
```

Cover, where relevant: actors, behaviors, constraints, important state
transitions, externally observable failure behavior, product-level invariants,
resolved product decisions, and remaining open product decisions.

Rules:

- give every firm behavior and constraint a Product ID and a provenance marker;
- do not invent priorities; if prioritization is useful but not sourced, record
  it as an inference or ask the human;
- do not invent numeric targets to make a statement look measurable;
- do not convert a best practice into `MUST` without provenance;
- do not introduce lifecycle steps merely because they seem conventional;
- keep implementation/framework choices out of the contract unless the human
  supplied them as explicit constraints;
- keep open product and open technical decisions visibly separate.

Avoid statements such as "the application should be intuitive", "the system
should be scalable", or "use best practices", unless they can be converted into
a grounded, verifiable obligation or constraint. Do not create fake precision
merely to obtain testability.

### Phase 3 — Grounding review

Perform a source/provenance review before ambiguity review. The reviewer is
read-only: it may write findings to `discovery-review.md`, but MUST NOT edit
`product-spec.md`, `decisions.md`, `source.md`, validator code, templates, or
tests.

Read `references/grounding-review.md` and follow it.

For every firm statement, ask:

> Where did this rule come from?

Classify unsupported statements instead of repairing them.

A grounding reviewer MAY identify an unsupported rule, cite the conflicting or
missing evidence, classify the risk, and propose the product question that
would authorize it.

A grounding reviewer MUST NOT silently delete or rewrite product semantics to
make the contract pass, infer a new rule from a single example, promote an
inference into a firm statement, or choose among materially different valid
behaviors.

Write findings to `discovery-review.md`.

### Phase 4 — Ambiguity review

Use a fresh-context reviewer when the environment supports subagents. Give it
the authoritative sources, `product-spec.md`, and `decisions.md`, but not the
drafting rationale or previous reviewer conclusions.

Read `references/ambiguity-review.md` and follow it.

The ambiguity reviewer looks for missing decisions, not unsupported inventions.

Keep the distinction strict:

```text
GROUNDING: did we invent something?
AMBIGUITY: did we fail to decide something?
```

The fresh-context reviewer is read-only. It reports candidate ambiguities; it
MUST NOT mutate `product-spec.md`, `decisions.md`, `source.md`, scripts,
templates, or tests.

A candidate ambiguity becomes an open `PRODUCT` decision only after the human
explicitly chooses to leave that material question open. Do not create blocking
product decisions on the human's behalf. Low-value or optional-capability
findings remain review notes and do not block the freeze.

Record the outcome in `discovery-review.md > Unresolved Assumptions`. That
section must state the outcome explicitly — either the assumptions that remain,
or that none were identified. Never invent an assumption to fill it, and never
leave it blank.

### Phase 5 — Human semantic gate

The gate answers one question:

> Does this specification represent the product the human intends to build?

Present only the smallest high-risk surface that needs human attention:

1. blockers;
2. unsupported firm statements;
3. high-impact ambiguities;
4. product decisions that need confirmation;
5. technical questions intentionally deferred.

Do not ask the human to reread the full contract unless needed.

The gate is specifically responsible for confirming semantic correctness,
resolving material open product decisions, ensuring no inference has become an
unsupported rule, confirming constraints, and approving the contract.

For each product blocker the human may decide it now, remove the unsupported
behavior, or explicitly leave it open.

Update `decisions.md` first, then `product-spec.md`. Record the outcome in
`discovery-review.md` as `GATE: APPROVED`, `GATE: PENDING`, or
`GATE: REJECTED`, with who reviewed it and when.

The deterministic validator records that this gate happened. It never performs
it: a contract is not frozen merely because its syntax passes.

### Phase 6 — Readiness and deterministic validation

Read `references/readiness.md`.

Treat the validator as an immutable black box during a spec run. Run it; do not
inspect or modify its implementation or tests during this workflow. If it
appears buggy, record `TOOLING_BUG` in `discovery-review.md`, report the
failing command/output, and stop the deterministic gate. Fix tooling outside
the run, then rerun the experiment.

Set `discovery-review.md` status to either:

```text
STATUS: READY
```

or:

```text
STATUS: BLOCKED
```

Always run the strict validator yourself before reporting any readiness. Never
ask the user to run it, and never treat this step as optional:

```bash
python .claude/skills/rigorail-spec/scripts/validate_spec.py docs
```

Its exit code decides:

- `0` — structurally valid with no open product decision; readiness is allowed;
- `1` — structural or provenance failure; the contract is not ready;
- `2` — structurally valid, but an open `PRODUCT` decision still blocks the
  freeze.

A failing validator is never overridden by review prose. Do not set
`STATUS: READY`, and do not claim the contract is frozen, unless the strict
validator actually exited `0`. When it does not, surface its output — the
`ERROR:` lines name what to fix — rather than only its exit code.

During drafting, if intentionally open product decisions remain, use:

```bash
python .claude/skills/rigorail-spec/scripts/validate_spec.py --allow-open docs
```

`--allow-open` is a drafting aid. It never establishes freeze: only the strict
run does.

### Phase 7 — Freeze

Freeze the contract only when all are true:

- every firm `§` statement has a unique id and valid provenance;
- no firm statement is grounded by an inference, a technical decision, or an
  open/unconfirmed entry;
- no unresolved high-impact product ambiguity remains;
- no grounding blocker remains;
- unresolved assumptions are stated explicitly, even when there are none;
- the contract is internally consistent enough to implement;
- strict deterministic validation was run in this workflow and exited `0`;
- the human approved the semantic gate.

A frozen contract may still contain open `TECHNICAL` decisions if they do not
alter product behavior.

The frozen contract is the end of this skill's responsibility. What happens to
those `§` ids afterwards — planning, tracking, implementation — is not decided
here.

## What the deterministic validator does and does not check

It checks: the four artifacts exist and `source.md` is non-empty; required
sections are present; every product statement uses the canonical form
`- **§<id>** — <body>`, with a well-formed unique id, a real em dash, and a
non-empty body, in a section matching its id; every firm statement has exactly
one provenance marker resolving to an authorizing source or decision; ledger
entries use valid layer, provenance, and status values; an inference is not
marked decided; a `SOURCE` entry cites at least one declared source and no
undeclared one; `§` references in the ledger and the review resolve; open
product decisions are mirrored in the contract and in the review's blockers;
`discovery-review.md` carries exactly one `STATUS:` line and exactly one
`GATE:` line, and they are consistent with the open decisions.

It fails closed on anything that visibly tries to be a product statement. A
line such as `- §1.1 — …`, `- **§1.1**: …`, or `- **§1.1** —` is an error, not
a line the parser skips, because a statement that silently disappears is
measured by nobody.

It does **not** check that a statement is semantically grounded, that a
statement is atomic, that the contract describes the right product, or anything
about downstream delivery. It emits warnings for suspicious enumerations and
invented-looking numeric precision; a warning is a prompt for human attention,
not a verdict.

## Product vs technical boundary

A choice is technical only when all viable options preserve the same externally
observable product contract and scope.

If choosing differently would add or remove a user-visible capability, an actor
permission, a business state, a lifecycle transition, routing behavior, or an
admin operation, it is a product/scope question. Apply the required-flow gate
before asking it; optional capabilities omitted by the source are normally
simply not required, not blockers.

## Scope-minimality rule

The contract defines what must exist for the sourced MVP. It does not need to
decide every capability a future system could have.

Do not turn source silence into an invented `MUST NOT`, an invented assumption,
or an open decision of either layer, unless the choice is necessary to
implement a required sourced behavior. If useful, mention an optional omitted
capability as a non-blocking review note, but do not promote it into the
contract.

## Reviewer non-resolution rule

This rule is absolute:

> A reviewer may identify, classify, and evidence an unresolved product
> decision. It must not resolve that decision by inferring a new business rule.
> Any finding admitting multiple materially different valid product behaviors
> requires a human decision before freeze.

Automatic fixes are allowed only for mechanical issues that do not change
product semantics, such as broken references, duplicated identifiers, or
formatting.

## Human-attention policy

Human attention is the scarce resource.

Prefer:

- deterministic validation for mechanically checkable properties;
- LLM judgment only for semantic grounding and ambiguity;
- fresh-context review for independent semantic checks;
- short blocker summaries rather than long review essays.

Stop asking clarification questions when the expected implementation-risk
reduction is lower than the human attention cost. Defer purely technical
choices to technical design.

## Token and tool discipline

During a normal run:

- read `SKILL.md`, the four templates, the authoritative product sources, and
  only the reference file needed for the current review phase;
- do not inspect `scripts/` or `tests/`; execute the validator as a black box;
- run at most one fresh-context ambiguity review pass;
- return at most five candidate ambiguity findings, ranked by risk;
- ask at most three independent high-value questions in one batch;
- do not rerun semantic reviewers after every answer; update the ledger and the
  contract directly, then perform readiness once.

## Completion response

Report the outcome, not the choreography. On success:

```text
✓ product contract artifacts produced
✓ grounding/provenance review passed
✓ ambiguity review passed
✓ human semantic gate approved
✓ deterministic validator passed
SPEC FROZEN
```

Then report only:

- artifact paths;
- `READY` or `BLOCKED`;
- number of behaviors and constraints;
- number of open product decisions;
- number of open technical decisions;
- number of unsupported/blocking findings;
- the deterministic validator command and its exit code;
- the next action.

Show individual commands and their output only when a step failed, or when the
user asks for them.

Do not move into technical design unless the user asks.
