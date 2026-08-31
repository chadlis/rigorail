---
name: rigorail-design
description: Turn an approved product specification into an implementation-ready technical design by running Spec Kit `/speckit.plan` as the planner, then reviewing the generated design for product contradictions, product inventions, product blockers, unresolved technical decisions, unverified framework facts, and technical integrity gaps. Use when a frozen spec must become a plan, when auditing a technical design against its product contract, or when deciding whether a design is ready for implementation.
---

# Rigorail Design

Rigorail is a thin control layer around an external planner. It does not plan.
It decides when planning is allowed to start, and whether the produced design
may be trusted as a product contract implementation.

This is an optional stage. `rigorail-spec` ends at the frozen whole-product
contract in `docs/`; what happens between that contract and shipped code is
downstream of Rigorail. Use this skill when a piece of work genuinely needs an
explicit Rigorail technical-design phase, or for experiments. It is not a
mandatory step before every feature, and it does not turn the product contract
into a per-feature document: it plans against the same `docs/` contract,
addressing the `§` ids it implements.

The failure this skill exists to catch:

> While concretizing a spec into schemas, routes, states, and contracts, a
> planner can silently turn missing product behavior into a concrete product
> rule.

The boundary rule is:

A choice requires product authority when different alternatives materially
change a **product-semantic commitment**, including at least:

- an explicit approved product requirement;
- business meaning or user rights;
- permissions, ownership, isolation, security, privacy, or visibility;
- lifecycle or economically meaningful outcomes;
- data-retention semantics, when retention itself matters to the approved
  product meaning;
- a public or stable interface guarantee;
- behavior consumers are expected to be able to rely on;
- an acceptance outcome that must remain stable.

**Mere observability is not sufficient.** An implementation always exhibits
observable incidental behavior — ordering, opaque identifier representation,
framework-standard status codes, internal timeout values, equivalent transport
conventions, implementation-local defaults. Such behavior may legitimately
remain implementation-defined or planner-chosen when it creates none of the
commitments above. Rigorail must not turn that choice into a finding, and must
not route it to the human.

An implementation-defined choice MUST NOT, however, be promoted into an approved
product guarantee, a product acceptance criterion, or a stable consumer contract
unless it is grounded in the approved product contract.

Where a product-semantic commitment is not grounded in the approved contract:

- if the planner introduced an unsupported commitment that can be removed
  without preventing implementation, it is a `PRODUCT_INVENTION`;
- if correct implementation genuinely requires an authoritative product-semantic
  commitment and the approved contract does not determine one unique required
  meaning, it is a `PRODUCT_BLOCKER`.

## Prerequisites

Spec Kit must be installed in the project so that `/speckit.plan` is available.
Rigorail does not fork Spec Kit, copy its templates, or reimplement its planner.

**Tested Spec Kit baseline: `1.0.1`.** That is the only version this skill has
been exercised against (EXP-002). The repository pins `specify-cli==1.0.1` as a
dev dependency; this skill does not install or upgrade Spec Kit itself, and it
refuses to pretend that an unknown version is equivalent.

### Preflight

Every precondition a program can decide is decided by one deterministic,
idempotent command. Run it once, before Phase 0, and report its output in the
completion response. Do not perform its steps by hand, and do not ask the user
to perform them:

```bash
uv run python -m rigorail.design_preflight docs
```

It establishes, in order:

1. the feature directory named by the argument exists and holds
   `product-spec.md` and `decisions.md`;
2. **the specification is frozen** — it runs the `rigorail-spec` validator
   strictly and requires exit `0`, so approval is a verified exit code rather
   than a claim. Exit `1` (malformed or ungrounded artifacts) and exit `2` (an
   open `PRODUCT` decision remains) each mean the contract is not approved for
   technical design;
3. the pinned Spec Kit workspace is present and valid, scaffolding it through
   `rigorail.speckit_setup` only when it is missing or incomplete, and refusing
   to reconcile a workspace that records a different version;
4. `technical-context.md` exists, creating the skeleton described below when it
   does not, and never rewriting one that does;
5. Spec Kit resolves the intended feature directory, by invoking Spec Kit's own
   `setup-plan.sh` with a command-scoped `SPECIFY_FEATURE_DIRECTORY`.

**A non-zero exit stops the workflow.** Report the command and its output. Do
not substitute another planning framework, do not hand-write a plan in its
place, do not scaffold Spec Kit by other means, and do not proceed on a Spec Kit
version the preflight could not reconcile with the tested baseline. Never
silently treat an unknown or different version as equivalent to it.

`uv run python -m rigorail.speckit_setup` still works and remains useful for
manual maintenance and debugging. It is not part of the normal workflow.

## Inputs and authority order

The workflow requires at minimum:

```text
product-spec.md
decisions.md
technical-context.md
```

Authority order, highest first:

1. decided product behavior in `product-spec.md` and `decisions.md`;
2. technical constraints in `technical-context.md`;
3. planner technical judgment.

A lower level never overrides a higher one. Planner judgment is authoritative
only where the two levels above are silent *and* the choice is technical.

`product-spec.md` and `decisions.md` come from `rigorail-spec`.
`technical-context.md` does not: no workflow produces it. The preflight creates
it when it is absent and leaves an existing one untouched. It records the
constraints that outrank planner judgment — and nothing else. Keep decided
product behavior out of it: product authority lives at level 1, and a product
rule smuggled in here would carry the wrong authority.

The generated skeleton keeps the authority boundary visible:

```md
# Technical Context

## Repository facts

- Python 3.13 <!-- REPO_FACT: .python-version -->
- Package manager: uv <!-- REPO_FACT: uv.lock -->

## Human design constraints

- None provided.

## Unresolved constraints

- None recorded.
```

Only `Repository facts` is populated automatically, only from direct file
evidence, and each line cites the file it was read from. Business behavior is
never inferred from repository structure, and a plausible convention is not
turned into a constraint.

`Human design constraints` is written by a human. Each line there is a
constraint, not a suggestion — the stack and runtime, what is authoritative for
durable state, what is out of scope at the technical boundary, the trust
boundary, invariants the implementation must enforce and where, framework and
abstraction preferences, testing and CI constraints, explicit non-requirements.
Never populate it yourself. `- None provided.` means nobody imposed a
constraint, which leaves the choice to the planner — the intended outcome for a
genuinely technical decision. It is not authorization to invent one.

`Unresolved constraints` holds a constraint that design genuinely requires and
nobody has established. Escalate one to the human only when it is actually
required for a materially different technical design; otherwise it is a
technical choice and belongs to the planner.

## Outputs

Work in the directory that already holds the frozen contract, so the design
sits beside it:

```text
docs/
├── product-spec.md         # input, unchanged
├── decisions.md            # input; product decisions originate from the human
├── technical-context.md    # input, unchanged
├── <Spec Kit plan artifacts>
└── design-review.md        # produced by this skill
```

Spec Kit owns the plan artifacts. Rigorail owns only `design-review.md`.

A Spec Kit design is a DRAFT until the Rigorail review passes.

## Workflow

```text
approved specification
→ specification readiness check
→ /speckit.plan
→ freeze generated design artifacts
→ fresh-context technical-design review
→ deterministic validation and routing
→ bounded automatic repair, or the human semantic gate
→ design freeze
```

### Phase 0 — Preconditions

The preflight above establishes every precondition deterministically. Do not
re-derive them by reading the files, and do not ask the user to confirm them:

- the Spec Kit workspace is the pinned, verified one;
- the specification is frozen — `validate_spec.py` exited `0`, which also means
  no open `PRODUCT` decision remains in `decisions.md`;
- `technical-context.md` exists.

Open technical decisions are allowed and expected: they are exactly what the
planner is authorized to resolve.

If the preflight did not exit `0`, readiness is not established. Require the
expected artifacts or state. Never infer approval, and never approve the spec on
the human's behalf.

### Phase 1 — Planning

Before invoking `/speckit.plan`, give the planner all three authoritative
inputs — `product-spec.md`, `decisions.md`, and `technical-context.md` — and
require it
to read all three and follow the authority order documented above. The feature
spec alone is not sufficient: `decisions.md` carries the decided product
behavior and the open technical decisions the planner is authorized to resolve,
and `technical-context.md` carries the constraints that outrank planner
judgment.

The planner's target is already pinned. Spec Kit resolves it from
`SPECIFY_FEATURE_DIRECTORY`, otherwise from `.specify/feature.json` — never from
the current git branch. `feature.json` is machine-local and not committed, so a
fresh clone may point at nothing or at a stale feature. The preflight handled
this: it passed the feature directory to Spec Kit's own `setup-plan.sh` as a
command-scoped `SPECIFY_FEATURE_DIRECTORY`, which persists the value to
`feature.json`, and it then verified that Spec Kit resolved the intended
directory. Never ask the user to export anything.

`/speckit.plan` runs `.specify/scripts/bash/setup-plan.sh --json` again, which
prints the resolved `SPECS_DIR`. Compare that printed value against the intended
feature directory. If they differ, **stop** and rerun the preflight before
planning: a mismatch silently writes a complete design into the wrong feature,
and the review that follows would then read a different feature's product
contract.

Run `/speckit.plan`.

The planner may:

- resolve technical decisions;
- perform framework research;
- produce plan/research/data-model/contracts/quickstart artifacts;
- choose architecture, modules, workflows, schemas, routes, transactions,
  storage patterns, and framework primitives.

The planner must not silently decide missing product behavior. Where a product
question blocks concretization, it must be left visible for the review rather
than answered.

Where practical the plan should mark framework premises as:

```text
VERIFIED_FRAMEWORK_FACT
NEEDS_FRAMEWORK_VERIFICATION
```

### Phase 2 — Freeze the generated artifacts

Treat the generated design artifacts as frozen inputs to the review. Do not edit
them while reviewing. If they change, the review must be rerun.

### Phase 3 — Fresh-context review

Perform a conceptually fresh-context, READ-ONLY review. Use a subagent when the
environment supports one; do not give it the planning rationale.

Inputs: `product-spec.md`, `decisions.md`, `technical-context.md`, and the
generated
design artifacts.

The reviewer writes `design-review.md` and nothing else. It MUST NOT edit the
plan, the spec, `decisions.md`, this skill, the validator, or the tests. It must
not repair a product finding — describing the problem is the whole job.

#### Categories

```text
PRODUCT_CONTRADICTIONS   design directly contradicts decided product behavior
PRODUCT_INVENTIONS       design imposes a new product-semantic commitment
                         without product authority; if removing it shows the
                         commitment is genuinely required, reclassify as a
                         PRODUCT_BLOCKER
PRODUCT_BLOCKERS         correct implementation genuinely requires an
                         authoritative product-semantic commitment and the
                         approved contract does not determine one unique
                         required meaning — either because the semantics are
                         missing, or because approved product rules conflict
                         materially and no unique implementable meaning exists
UNRESOLVED_TECHNICAL_DECISIONS
                         a technical decision the planner was authorized to make
                         is still undecided
UNVERIFIED_FRAMEWORK_FACTS
                         a framework property is used as an important premise
                         without sufficient verification
TECHNICAL_INTEGRITY_GAPS the product behavior is understood but the proposed
                         mechanism is insufficiently robust
```

An `UNVERIFIED_FRAMEWORK_FACT` matters most when the assumption affects product
invariants, transactions, authorization, retries/idempotency, or data integrity.

A `TECHNICAL_INTEGRITY_GAP` is generic, e.g. a missing idempotency boundary, a
retry that can duplicate an operation, a partial failure with no recovery path,
authorization enforced only in UI code, a documented cardinality invariant with
no structural enforcement, or an ambiguous transaction boundary spanning durable
writes and external calls.

#### Precedence between adjacent categories

Three categories describe adjacent failure modes. Classify by what the design
already commits to:

- **`PRODUCT_CONTRADICTION`** — the design specifies or intends behavior that
  contradicts an approved product-semantic commitment. *Product says only owners
  may delete; the design explicitly permits any authenticated user to delete.*
- **`UNRESOLVED_TECHNICAL_DECISION`** — a required technical choice has not been
  made; the planner selected no mechanism. *Retry/idempotency strategy is still
  TODO.*
- **`TECHNICAL_INTEGRITY_GAP`** — a mechanism has been selected or claimed, but
  it does not actually guarantee a required invariant. *The design says
  owner-only access is guaranteed, but authorization exists only in UI code and
  is not enforced server-side.*

#### `TECHNICAL_INTEGRITY_GAP` severity

A `TECHNICAL_INTEGRITY_GAP` must be `HIGH` when, left unresolved, it can
plausibly:

- violate an approved product invariant;
- violate authorization, isolation, privacy, visibility, or security semantics;
- corrupt durable state or durable correctness;
- cause economically meaningful duplication, loss, or inconsistent outcomes;
- cause unrecoverable or materially incorrect partial failure;
- require non-local architectural redesign if discovered during implementation.

Unenforced authorization is therefore never `MEDIUM`. Lower severities remain
available for genuinely non-blocking technical issues.

#### Review discipline

- Do not require implementation detail that is unnecessary to begin
  implementation.
- Do not turn architectural preference into a finding.
- Do not penalize custom code merely because it is custom. A custom mechanism is
  a finding only when an appropriate native framework primitive exists and the
  custom mechanism adds unjustified complexity or risk.
- Absence of a product constraint authorizes neither a restrictive default nor a
  permissive or unbounded guarantee. In particular, absence of a stated maximum
  does not mean arbitrarily large values are guaranteed to be accepted. When the
  planner turns product silence into an explicit product guarantee that can
  simply be removed without preventing implementation, classify it as a
  `PRODUCT_INVENTION`; "no maximum length is imposed" and "a 100k-character title
  must be accepted" are such guarantees. Removing a guarantee does not mean
  pretending the runtime has no behavior: the runtime still does something, and
  that incidental behavior may remain implementation-defined so long as it is not
  elevated into approved product semantics.
- That an implementation must choose *some* observable behavior does not by
  itself make the choice a `PRODUCT_BLOCKER`. Use `PRODUCT_BLOCKER` only when
  correct implementation genuinely requires an authoritative product-semantic
  commitment and the approved contract does not determine one unique required
  meaning — whether because the semantics are missing, or because approved
  product rules conflict materially. Worked cases:
  - `400` vs `422` where the distinction carries no approved or stable semantic
    meaning — the planner may choose; not a blocker;
  - newest-first vs another incidental list order where no ordering contract
    exists — the planner may choose an implementation-defined order, but must not
    promote it into a product acceptance guarantee;
  - unauthorized-resource disclosure semantics — a product decision, because the
    alternatives change security, privacy, or visibility meaning;
  - retry behavior that can charge a customer twice — a blocker when the approved
    business contract does not determine the acceptable outcome.
- Do not escalate a missing bound to the human merely because none is stated.
- Report the smallest set of findings that actually changes what happens next.

### Phase 4 — Deterministic validation and routing

Treat the validator as an immutable black box during a design run. Run it; do
not inspect or edit `scripts/` or `tests/`. If it appears buggy, stop the
deterministic gate and report `TOOLING_BUG` in the completion response with the
failing command and its output. Do not mutate `design-review.md` or the
validator during the run — `TOOLING_BUG` is not part of the review schema. Fix
tooling outside the run, then rerun.

```bash
python .claude/skills/rigorail-design/scripts/validate_design.py --iteration <n> docs
```

`<n>` is the number of automatic repair rounds already performed in this run,
starting at `0`.

Exit codes: `0` design is READY, `1` missing/malformed/gate-violating artifacts,
`2` well formed but not READY yet.

**The validator must actually be run, and its exit code decides.** Never report
`READY`, never freeze, and never claim a gate passed because the review prose
looks correct. A failing validator is never overridden — surface its output so
the failure can be diagnosed.

The validator also prints one `route:` line, derived from the findings rather
than from prose, and lists the blocking findings under `BLOCKING:`:

```text
FREEZE                  nothing blocks → Phase 6
REPLAN                  back to the planner → Phase 1, then Phases 2–4 again
HUMAN_PRODUCT_DECISION  stop and ask the human → Phase 5
REPAIR_LIMIT_REACHED    stop and report; readiness was not reached
INVALID_ARTIFACTS       design-review.md is malformed, or claims a status its
                        findings do not support; fix the review, never the gate
```

The validator checks only machine-checkable properties. It does not judge
whether a technical choice is good, whether prose hides a product invention, or
whether a framework claim is true.

### Phase 5 — Repair, and the human semantic gate

The design cannot be `READY` while any of `PRODUCT_CONTRADICTIONS`,
`PRODUCT_INVENTIONS`, or `PRODUCT_BLOCKERS` is non-empty. Where each one goes
differs, and only one of them costs human attention:

- `PRODUCT_CONTRADICTION` → **back to the planner.** The product behavior is
  already decided; the planner contradicted it. The planner corrects the design.
  Do not ask the human to decide the same product question again.
- `PRODUCT_INVENTION` → **back to the planner**, to remove the unsupported
  commitment. If removing it reveals that correct implementation genuinely
  requires an authoritative product-semantic commitment the approved contract
  does not determine, the reviewer reclassifies that issue as a
  `PRODUCT_BLOCKER`; it is not an invention any more.
- `UNRESOLVED_TECHNICAL_DECISION` → **back to the planner.** The planner is
  authorized to decide it.
- HIGH `TECHNICAL_INTEGRITY_GAP` → **back to the planner.** The product behavior
  is understood; the mechanism is not sufficient.
- `UNVERIFIED_FRAMEWORK_FACT` → **neither.** It never blocks the gate. Verify it
  where practical — the framework's own documentation, or exercising the actual
  behavior — and otherwise leave it reported under the four-part test below.
- `PRODUCT_BLOCKER` → **the human.** This is the only category that requires a
  human product decision.

#### Automatic repair

On `REPLAN`, repair without involving the user: hand the findings back to the
planner (Phase 1), then rerun Phases 2–4 with `--iteration` incremented. Do not
report intermediate rounds as questions, and do not ask the user to schedule
them.

`MAX_REPAIR_ITERATIONS` in the validator bounds this at **2** automatic rounds.
It is a single constant; change it there if the bound is ever wrong.

On `REPAIR_LIMIT_REACHED`, **stop**. Report the unresolved findings and the
rounds spent. Do not freeze, and do not report `READY`: the validator still
exits `2`, and no further prose changes that.

#### The human semantic gate

For a `PRODUCT_BLOCKER` only:

1. present the blockers to the human, shortest form first: the missing
   product-semantic commitment, why it requires a human, and the decision
   required;
2. the human decides;
3. record the decision in the product artifact (`decisions.md`, and `product-spec.md`
   when the decided behavior belongs in the contract);
4. rerun the preflight, planning, and review.

Never resolve a `PRODUCT_BLOCKER` yourself. Never escalate anything else to the
human: contradictions, inventions, unresolved technical decisions, and integrity
gaps all go back to the planner. In particular, do not ask the human to approve
a `PRODUCT_INVENTION` retroactively — the repair is to remove the unsupported
commitment, and asking would invent the same rule by hand.

### Phase 6 — Design freeze

Freeze the design only when all are true:

- `design-review.md` has `STATUS: READY`;
- no product contradiction, invention, or blocker remains;
- every open `TECHNICAL` decision in `decisions.md` is accounted for;
- no HIGH `TECHNICAL_INTEGRITY_GAP` remains;
- deterministic validation exits `0` and its route is `FREEZE`;
- the human approved the semantic gate when one was required.

## `design-review.md` format

The format is strict so that the deterministic validator can parse it. Section
names are uppercase and appear in this order. Each section lists findings or the
single word `None`.

```md
# Technical Design Review

STATUS: READY

## PRODUCT_CONTRADICTIONS

None.

## PRODUCT_INVENTIONS

None.

## PRODUCT_BLOCKERS

None.

## UNRESOLVED_TECHNICAL_DECISIONS

None.

## UNVERIFIED_FRAMEWORK_FACTS

- [MEDIUM] F-001 — plan assumes the framework enforces uniqueness on the link table
  - Evidence: data-model.md, "link table" section
  - Authoritative inputs: product-spec.md §4.1 requires the invariant; no source proves
    the framework enforces it
  - Classification: INFERENCE
  - Required action: verify before implementation; add an explicit constraint if
    the framework does not enforce it

## TECHNICAL_INTEGRITY_GAPS

None.

## RESOLVED_TECHNICAL_DECISIONS

None.
```

`STATUS` is one of:

```text
READY | NEEDS_PRODUCT_DECISION | NEEDS_TECHNICAL_WORK
```

Every finding line is:

```text
- [HIGH|MEDIUM|LOW] <id> — <one-line claim>
```

followed by indented fields. `Evidence:` and `Required action:` are mandatory;
add `Authoritative inputs:` and a `Classification:` of
`SOURCE FACT` / `HUMAN DECISION` / `INFERENCE` wherever they apply.

`RESOLVED_TECHNICAL_DECISIONS` is an accounting ledger, not a finding category.
List each open `TECHNICAL` decision from `decisions.md` that the planner did
decide:

```md
- D-011 — resolved in plan.md > Technical Decisions
```

Every open `TECHNICAL` decision declared in `decisions.md` must appear exactly
once, either there or as a finding under `UNRESOLVED_TECHNICAL_DECISIONS` — not
twice in one section, and not once in each. Only decisions `decisions.md`
declares as open `TECHNICAL` may be listed as resolved.

### Status selection

- any `PRODUCT_BLOCKER` → `NEEDS_PRODUCT_DECISION`;
- otherwise any product contradiction or invention, unresolved technical
  decision, or HIGH technical integrity gap → `NEEDS_TECHNICAL_WORK`;
- otherwise `READY`.

`STATUS` is fully derived from the findings. No other value is valid, and the
validator rejects it — including `NEEDS_TECHNICAL_WORK` with nothing blocking.
If more planner work is genuinely required, state the concrete finding that
justifies it; wanting more work is not a status.

`READY` means implementation-ready under the Rigorail design gate. It does not
mean semantic proof, exhaustive absence of defects, or verified truth of every
framework premise.

### Unverified framework facts and READY

A non-blocking `UNVERIFIED_FRAMEWORK_FACT` may coexist with `STATUS: READY` only
when all of these hold:

1. falsification before ship exercises the actual relevant
   framework/platform/version behavior, rather than a mock or a test that simply
   encodes the same assumption;
2. that check deterministically fails before ship if the premise is false;
3. recovery is local;
4. correcting the premise does not require changing approved product semantics,
   security or privacy guarantees, or non-local architecture.

If falsity could require architectural redesign, data migration, security
redesign, or changed product semantics, it must be represented through an
appropriate blocking finding rather than remaining only an
`UNVERIFIED_FRAMEWORK_FACT`.

`UNVERIFIED_FRAMEWORK_FACTS` therefore never block deterministically, at any
severity. When an unverified assumption is genuinely load-bearing — the design
collapses or a product invariant breaks if it is false — do not file it only as
a framework fact. File it as a `TECHNICAL_INTEGRITY_GAP` with the severity it
deserves, or as an `UNRESOLVED_TECHNICAL_DECISION`, so the gate can see it.

## Human-attention policy

Human attention is the scarce resource.

- deterministic validation for mechanically checkable properties;
- LLM judgment only for the product/technical boundary;
- fresh-context review so the reviewer does not inherit planning rationale;
- escalate product semantics only, and in the shortest form that supports a
  decision;
- run every deterministic step yourself. The user is not the scheduler between
  the preflight, the planner, the reviewer, and the validator.

## Completion response

Report the outcome, not the choreography. On success:

```text
✓ frozen specification verified
✓ technical context resolved
✓ Spec Kit environment ready
✓ planning completed
✓ independent design review completed
✓ allowed findings repaired (<n> of 2 rounds)
✓ deterministic validator passed
DESIGN FROZEN
```

Then report only:

- artifact paths;
- the feature directory the planner resolved, and that it matched the intended
  one;
- the Spec Kit version used, and whether it matched the tested baseline;
- `STATUS`;
- counts per finding category;
- the deterministic validator command, its exit code, and its route;
- `TOOLING_BUG` with the failing command and output, if the validator itself
  appeared broken;
- the next action.

When the run stops, lead with why and what is required:

```text
DESIGN BLOCKED

PRODUCT_BLOCKER:
<the missing product-semantic commitment>

Why this requires a human:
<why the approved contract determines no unique required meaning>

Decision required:
<the decision, shortest form first>
```

`REPAIR_LIMIT_REACHED` reports the same way, listing the unresolved findings and
the rounds spent instead of a decision request.

Show individual commands and their output only when a step failed, or when the
user asks for them.

Do not start implementation unless the user asks.
