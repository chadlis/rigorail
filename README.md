# Rigorail

Rigorail is an experimental, reusable framework for disciplined agentic
software development.

## The problem it addresses

If you ask an agent to build something from a short description, it will fill
the gaps by itself. It has no choice, because a short description is never
complete enough to implement. The problem is that it fills them silently. Once
a gap is filled, it looks the same as a requirement you actually asked for.

Here is a real example from this repository's own tests. The approved
specification said that a note title must contain at least one character. It
said nothing about a maximum length. The planner wrote this into the design:

> No maximum length is imposed on the title or the body.

It also added a test that required a title of 100,000 characters to be accepted.

Nobody decided this. It is not even a bad guess. It is a rule that no person
approved, now stored in the contract as if someone had. The opposite guess,
"titles are limited to 200 characters", would have been just as wrong. Six
months later, the only sign that a machine invented this rule is a test that
protects it.

Rigorail answers this in two ways. Every firm rule must say where it came from.
Every real gap stays visible as a gap, instead of being filled in silence.

## Core principle

> Human attention is the scarce resource. Anything machine-verifiable should
> be verified deterministically. LLMs should be used only where judgment is
> required.

This creates a split. Some questions have an answer a program can compute: is
every rule attributed? is this document well formed? Those are checked by
scripts, which give the same answer every time. Other questions need judgment:
is this the right product? does this mechanism really guarantee what it claims?
Those go to a language model, or to you. Neither side does the other's work.

## Status

**Experimental.** The specification stage below is the one that is finished and
meant to be used. Everything downstream of the frozen contract is not built
here yet. It is **not currently ready for external use**.

## Where Rigorail starts and stops

```text
informal product source
→ /rigorail-spec
→ docs/
   ├── source.md
   ├── product-spec.md
   ├── decisions.md
   └── discovery-review.md
→ frozen desired product state
→ (downstream: backlog slicing, per-change planning, implementation)
```

`docs/` holds **one contract for the whole product**, not one per feature. Its
`§` ids are what a feature is addressed by later: a piece of work delivers
`§1.2` and `§C1`, it does not get a specification of its own. Everything past
the frozen contract — how work is sliced, tracked, planned per change, and
implemented — is downstream of Rigorail Spec and is not built in this
repository.

You run Rigorail as skills in Claude Code:

- **`/rigorail-spec`** turns raw product context into a frozen product contract.
  This is the entry point, and it is where the default workflow ends.
- **`/rigorail-design`** turns a frozen contract into a reviewed technical
  design. It remains available for experiments and for work that genuinely
  needs an explicit Rigorail design phase. It is **not** a mandatory stage
  before every downstream feature.

Neither of them writes the feature.

A stage ends with a **freeze**. A frozen document is one that passed its review
and its automatic checks. Nothing becomes read-only. The freeze is a state you
confirm by running a script, and you can confirm it again at any time. There is
more detail in [What "frozen" means](#what-frozen-means) at the end of this
file.

## Worked example

This example takes a one-paragraph draft and turns it into a reviewed technical
design. The feature is team invitations.

There is nothing to set up first. Rigorail does not plan by itself: it runs
[GitHub Spec Kit](https://github.com/github/spec-kit) as its planner and reviews
what the planner produced. Installing the pinned version of Spec Kit, pointing
it at the right feature, and running the checks are all things the skills do for
you. [Running the machinery yourself](#running-the-machinery-yourself) shows the
commands underneath, for when something goes wrong.

### 1. From a draft to a frozen product spec

Run `/rigorail-spec` with whatever you have: a paragraph, a ticket, a meeting
transcript.

> A team owner can invite people to their team by email address. Invited people
> get access once they accept.

The skill first decides which material is authoritative. Then it asks you at
most three questions. It only asks when two competent developers could build
materially different products from the same input. For the draft above, it
asked what happens when the invited email already belongs to a member, whether
you can invite an address that has no account yet, and who is allowed to accept
an invitation. It does not answer these for you. It never asks about naming,
status codes, or table layout, because those belong to the design stage.

It produces four files:

```text
docs/
├── source.md             # your words, kept verbatim
├── product-spec.md       # the product contract
├── decisions.md          # where every rule came from
└── discovery-review.md   # what the reviews found
```

The validator accepts a directory argument, but the canonical project contract
lives in `docs/`, and there is one of them for the whole product. As the
product grows, later runs extend the same four files — new `§` ids, new ledger
entries — rather than starting a second contract somewhere else.

#### `source.md`, the input

Your original text, unedited. The skill never tidies it into a cleaner brief,
never mixes its own interpretation into it, and never reads product rules out
of it by itself. It exists so that "the source says so" can be checked against
something that a machine did not write.

#### `product-spec.md`, the contract

Every firm statement carries a **Product ID**, so other files can address it.
`§n.m` is a behavior: something the product must do. `§Cn` is a constraint: a
property the product must satisfy continuously.

```md
## §1 Invitations

- **§1.1** — A team owner can invite a person to their team by email address. <!-- provenance: S-001 -->
- **§1.2** — An invited person has no access to the team before they accept. <!-- provenance: S-001 -->

## §C Constraints

- **§C1** — An invitation is addressed by email address. <!-- provenance: S-001 -->
```

One `§` is **one product obligation**. "A user can create, edit, delete, and
share a note" is four obligations wearing one id, and an id that covers four
things cannot be tracked, delivered, or tested as one. Atomicity is a judgment,
not a word count: "a user can create a note with a title and body" is one
obligation and stays one.

Ids are **semantically stable**. Rewording an obligation keeps its id. Changing
what the product must do gets a new id, and the old one is listed under
`## Withdrawn` rather than quietly reused, so nothing that referred to `§1.3`
ends up pointing at a different promise than the one it was written against.

The HTML comment at the end of each line is a **provenance marker**. It does
not appear when the Markdown is displayed. It names what authorized the
statement, here the source `S-001`. Every firm statement must have one.

An id and a provenance marker answer two different questions, and both are
required. The id makes a statement **addressable**. The marker makes it
**grounded**. An id on an invented rule is an invented rule with an id.

#### `decisions.md`, the ledger

Markers point to entries in this file. Identifiers that start with `S-` are
sources. Identifiers that start with `D-` are decisions.

```md
- **S-001** — source.md block S-001 — the product draft, verbatim

- **D-001** [2026-09-02] [PRODUCT] [HUMAN] [status:decided] [risk:high] — §1.2 —
  a person who accepts becomes a team member who can use the team's resources,
  and cannot manage the team or invite others — decided by the human on the
  access question — reversible:Y

- **D-004** [2026-09-02] [TECHNICAL] [HUMAN] [status:open] [risk:low] — delivery —
  how an invitation reaches the invited address — deferred to technical design —
  reversible:Y
```

Each entry carries two independent tags and a state:

| Axis | Values | What it says |
|---|---|---|
| layer | `PRODUCT`, `TECHNICAL` | whether this is a promise to a user or an implementation choice |
| provenance | `SOURCE`, `HUMAN`, `INFERRED` | who or what established it |
| status | `decided`, `open`, `unconfirmed` | whether it is settled |

Only two combinations can justify a firm statement: an `S-###` source, or a
`PRODUCT` decision that is `decided` and whose provenance is `SOURCE` or
`HUMAN`. A `SOURCE` entry must cite the source it rests on.

`INFERRED` is the important one. A guess can be recorded, but it cannot be
marked `decided` — the checks reject that outright. It becomes a rule only when
a person decides it, which produces a `HUMAN` entry. This is what would have
stopped the invented length rule.

`status:open` does the other half of the work. A question you have not answered
stays visible as a question. An open **product** question keeps the contract
unfrozen: the checks fail, and the design stage refuses to start and tells you
why. This is deliberate, because building without an answer means somebody will
guess it. An open **technical** question blocks nothing, because the design
stage is exactly where it gets answered.

#### `discovery-review.md`, and the gate

The review records what grounding and ambiguity review found, whether any
**unresolved assumptions** remain — "None identified." is a valid answer, an
empty section is not — and whether you approved the contract:

```text
STATUS: READY
GATE: APPROVED
```

`GATE:` is the human semantic gate. It answers one question that no script can:
does this describe the product you intend to build? A contract is not frozen
because its syntax passed. The checks below record that the gate happened; they
never perform it.

#### Checking the contract

Before it reports anything, the skill checks the contract with a script instead
of asking you to read it. No model is used. It is a normal Python program that
passes or fails, so it gives the same answer every time and CI can run it.

It checks only what a program can check: that the four files exist and
`source.md` is not empty, that the required sections are present, that Product
IDs parse and are unique and sit in a matching section, that every firm
statement has one marker pointing at an entry allowed to justify it, that
ledger entries use valid tags and that an inference is not marked decided, and
that `§` references resolve. It warns — never blocks — when a statement
enumerates several actions, or carries a number that looks invented.

It cannot tell you whether the contract describes the right product, and it
cannot prove a statement is atomic. The reviews, the gate, and your own
judgment do that.

| Exit | Meaning |
|---|---|
| `0` | passed |
| `1` | something is missing or malformed: a section, an id, a marker, a reference |
| `2` | structurally fine, but a question you left open is still open |

Exit code `2` is the one to understand. When you answer a question with "leave
open", the skill records an open `PRODUCT` decision. This blocks the freeze on
purpose, which is the reason for recording it.

The skill cannot talk its way past a failure. `SPEC FROZEN` is reported only
after the strict check actually exited `0`, so the run ends like this:

```text
✓ product contract artifacts produced
✓ grounding/provenance review passed
✓ ambiguity review passed
✓ human semantic gate approved
✓ deterministic validator passed
SPEC FROZEN
```

That is where this stage stops. `/rigorail-spec` owns the road from an informal
source to a frozen desired product state, and nothing after it: backlog
tracking, change planning, implementation, and repository-wide delivery
invariants are downstream concerns. None of them exist in this repository yet,
and none of them belong in the specification skill.

### 2. Optional: from a frozen contract to a reviewed technical design

This stage is not part of the default lifecycle. Rigorail Spec ends at the
frozen contract; how that contract becomes shipped work is downstream and lives
outside this repository. `/rigorail-design` remains available for experiments,
and for work that genuinely needs an explicit Rigorail design phase before
anyone writes code. Skip this section if you only wanted the contract.

Run the design skill with the directory holding the contract:

```text
/rigorail-design docs
```

That is the whole command. Before planning starts, one deterministic preflight
confirms the specification really is frozen, installs the pinned Spec Kit if it
is missing, points Spec Kit at that directory, and creates
`docs/technical-context.md` if you have not written one.

That last file holds the technical constraints that outrank the planner's
judgment: the stack, what stores the data, what the implementation can assume
already exists, the rules it must enforce, the testing and CI constraints.
Nobody can invent those for you, and the generated file does not pretend to. It
separates what was read off the repository from what a person decided:

```md
## Repository facts

- Python 3.13 <!-- REPO_FACT: .python-version -->
- Package manager: uv <!-- REPO_FACT: uv.lock -->

## Human design constraints

- None provided.

## Unresolved constraints

- None recorded.
```

Only the first section is filled in automatically, and only from a file that
directly evidences each line. `None provided.` is not a gap to be filled by
guessing: it means nobody imposed a constraint, so the choice belongs to the
planner. Write your constraints into the second section whenever you have them,
and the preflight will leave your file alone from then on.

The planner produces `plan.md`, `research.md`, `data-model.md`, `contracts/`,
and `quickstart.md`. Those files are then frozen and given to a **fresh-context
reviewer**. This is a second agent that reads the spec and the finished design,
but never reads the reasoning the planner used. This matters, because a
reviewer who followed the argument usually finds it convincing. A reviewer that
starts with no history gives you a real second opinion.

The reviewer writes `design-review.md`. It sorts what it finds into six kinds:

| Finding | Meaning |
|---|---|
| `PRODUCT_CONTRADICTION` | the design does something the spec forbids |
| `PRODUCT_INVENTION` | the design added a product rule nobody approved |
| `PRODUCT_BLOCKER` | the work cannot continue without a decision nobody made |
| `UNRESOLVED_TECHNICAL_DECISION` | a choice the planner had to make is still open |
| `UNVERIFIED_FRAMEWORK_FACT` | the design depends on framework behavior nobody checked |
| `TECHNICAL_INTEGRITY_GAP` | the chosen mechanism does not guarantee what it claims |

Only one of them needs your attention:

```text
PRODUCT_CONTRADICTION ─┐
PRODUCT_INVENTION ─────┤
UNRESOLVED_TECHNICAL_DECISION ─┼─→ back to the planner
HIGH TECHNICAL_INTEGRITY_GAP ──┘
PRODUCT_BLOCKER ───────────────→ to you
```

The invented length rule from the top of this file is a `PRODUCT_INVENTION`. It
goes back to the planner, which deletes it. It does not come to you, because
asking you to choose a maximum would mean inventing the same rule by hand. The
skill does that round trip itself, at most twice, and then stops rather than
looping. Only a `PRODUCT_BLOCKER` reaches you, and only when the work cannot
continue without a meaning that the contract does not contain. You decide it,
the skill records it in `decisions.md`, and planning runs again.

Which of those happens is decided by the same kind of script as before, not by
the reviewer's own reading of its review. It verifies that the review is well
formed, that its status matches its findings (you cannot write `READY` while a
blocker is still open), and that every technical decision the spec postponed was
either resolved or reported as still open. Then it prints where the run goes
next. It does not judge whether the design is good.

| Exit | Meaning |
|---|---|
| `0` | READY |
| `1` | malformed, or claiming a status its findings do not support |
| `2` | well formed, and correctly reporting that work remains |

A run that reaches the end looks like this:

```text
✓ frozen specification verified
✓ technical context resolved
✓ Spec Kit environment ready
✓ planning completed
✓ independent design review completed
✓ allowed findings repaired (1 of 2 rounds)
✓ deterministic validator passed
DESIGN FROZEN
```

A run that needs you looks like this, and nothing else is asked of you:

```text
DESIGN BLOCKED

PRODUCT_BLOCKER:
The approved product contract does not define whether expired invitations may
still be accepted.

Why this requires a human:
Two materially different product behaviors are possible and neither is
authorized by the current specification.

Decision required:
...
```

### 3. Implement

When `design-review.md` says `READY` and the validator exits `0`, build the
feature.

## Running the machinery yourself

Nothing above is hidden: the skills run ordinary commands you can run too. Reach
for these when a run fails and you want to see why, or when you are maintaining
the repository rather than using it.

Everything the design workflow needs before planning, in one idempotent command.
The design skill runs this itself; running it again changes nothing:

```bash
uv run python -m rigorail.design_preflight docs
```

It checks the spec is frozen, prepares Spec Kit, creates `technical-context.md`
if it is absent, and pins the directory Spec Kit will plan in. It never
rewrites a `technical-context.md` you wrote.

Install or repair the pinned Spec Kit workspace on its own:

```bash
uv run python -m rigorail.speckit_setup
```

Run either validator by hand:

```bash
uv run python .claude/skills/rigorail-spec/scripts/validate_spec.py docs
uv run python .claude/skills/rigorail-design/scripts/validate_design.py docs
```

While you are still drafting a spec and expect an open product decision, add
`--allow-open`. It means "I know about this one, check everything else". It is a
drafting aid and never establishes a freeze:

```bash
uv run python .claude/skills/rigorail-spec/scripts/validate_spec.py --allow-open docs
```

Spec Kit resolves its target feature from `SPECIFY_FEATURE_DIRECTORY`, and
otherwise from `.specify/feature.json`. The preflight sets the first for the one
command it runs, which makes Spec Kit persist the second, so you never need to
export anything. If you are driving Spec Kit directly, you still can:

```bash
SPECIFY_FEATURE_DIRECTORY=docs .specify/scripts/bash/setup-plan.sh --json
```

## What "frozen" means

A product contract is frozen when `discovery-review.md` says `READY`, its gate
says `APPROVED`, and its validator exits `0`. A design is frozen when
`design-review.md` says `READY` and its validator exits `0`.

There is no lock file, and no file becomes read-only. Freezing is a statement
you can check again at any time by running one command. This also means that
editing a frozen file silently unfreezes it, and that the command is how you
find out.

`READY` means the design is ready to implement under this gate. It does not
mean that the design is proven correct, that no defects remain, or that every
framework assumption was verified.

## Learn more

- [docs/principles.md](docs/principles.md): the principles this project is
  judged against.
- [docs/architecture.md](docs/architecture.md): how the repository is
  organized.
- [docs/evaluations/](docs/evaluations/): what was tried at each stage, what
  was found, and what was kept.
- The skills are readable on their own:
  `.claude/skills/rigorail-spec/SKILL.md` and
  `.claude/skills/rigorail-design/SKILL.md`.
