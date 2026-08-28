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

**Experimental.** Two stages of the pipeline below exist. The rest is not built
yet. It is **not currently ready for external use**.

## Intended pipeline

```text
product discovery
→ business spec
→ human spec review
→ technical design
→ human design review
→ implementation
→ deterministic gates
→ independent review
→ targeted human code review
→ deterministic CI
→ measurement
```

Each stage is intended to keep human attention focused on judgment calls,
while machine-verifiable checks are enforced deterministically rather than
through advisory prose.

Two stages exist today. You run them as skills in Claude Code:

- **`/rigorail-spec`** turns raw product context into a frozen product contract.
- **`/rigorail-design`** turns that contract into a reviewed technical design.

Neither of them writes the feature. They decide what to build and how, then
stop.

Each stage ends with a **freeze**. A frozen document is one that passed its
review and its automatic checks, so the next stage is allowed to start from it.
Nothing becomes read-only. The freeze is a state you confirm by running a
script, and you can confirm it again at any time. There is more detail in
[What "frozen" means](#what-frozen-means) at the end of this file.

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

It produces three files:

```text
specs/team-invites/
├── spec.md         # the product contract
├── decisions.md    # where every rule came from
└── review.md       # what the reviews found
```

#### `spec.md`, the contract

Requirements are numbered so that other files can refer to them. `FR` means
**functional requirement**: something the system must do. `SC` means **success
criterion**: a visible result that shows the feature works.

```md
- **FR-001**: A team owner MUST be able to invite a person to their team by email address. <!-- provenance: S-001 -->
- **FR-002**: An invited person MUST NOT have access to the team before they accept. <!-- provenance: S-001 -->
- **SC-001**: A team owner can invite a person by email address, and that person has no access until they accept. <!-- provenance: S-001 -->
```

The HTML comment at the end of each line is a **provenance marker**. It does
not appear when the Markdown is displayed. It names what authorized the rule,
here the source `S-001`. Every `FR-*` and `SC-*` line must have one. This is
the rule that makes invented requirements visible: if a rule has nothing to
refer to, it cannot be written as if someone had approved it.

#### `decisions.md`, the ledger

Markers point to entries in this file. Identifiers that start with `S-` are
sources. Identifiers that start with `D-` are decisions.

```md
- **S-001** [SOURCE_FACT] — raw product draft: "A team owner can invite people
  to their team by email address. Invited people get access once they accept."

- **D-001** [NEW_HUMAN_DECISION] [risk:high] [status:decided] — access granted on
  acceptance — a person who accepts becomes a team member who can use the team's
  resources, and cannot manage the team or invite others

- **D-004** [OPEN_TECHNICAL_DECISION] [risk:low] [status:open] — how an
  invitation reaches the invited address is deferred to technical design
```

The tag in brackets is the **provenance type**. It decides whether the entry is
allowed to justify a firm rule.

| Type | Meaning | Can justify a rule? |
|---|---|---|
| `SOURCE_FACT` | stated in your source material | yes |
| `PREVIOUS_HUMAN_DECISION` | you decided this earlier | yes |
| `NEW_HUMAN_DECISION` | you decided this during the run | yes |
| `INFERENCE` | plausible, but nobody approved it | no |
| `TECHNICAL_DECISION` | an implementation choice, not a product rule | no |
| `OPEN_PRODUCT_DECISION` | a product question left unanswered on purpose | no, and the spec cannot be frozen |
| `OPEN_TECHNICAL_DECISION` | postponed to the design stage | no, but the spec can still be frozen |

The three rows marked "yes" are the core of the method. A guess can be stored
as an `INFERENCE`, but it can never become a `MUST` until a person turns it
into a decision. This is what would have stopped the invented length rule.

The two `OPEN_*` types do the other half of the work. A question you have not
answered stays visible as a question.

The two types differ in what happens next. An open **product** question keeps
the spec unfrozen: the checks fail, and the design stage refuses to start on it
and tells you why. This is deliberate, because building without an answer means
somebody will guess it. An open **technical** question blocks nothing, because
the design stage is exactly where it gets answered.

#### Checking the spec

Before it reports anything, the skill checks the spec with a script instead of
asking you to read it. No model is used. It is a normal Python program that
passes or fails, so it gives the same answer every time and CI can run it.

It checks only what a program can check: that `spec.md` has the required
sections, that every `FR-*` and `SC-*` has a marker, and that each marker
points to an entry that is allowed to justify a rule. It cannot tell you
whether the spec describes the right product. The reviews and your own judgment
do that.

| Exit | Meaning |
|---|---|
| `0` | passed |
| `1` | something is missing or malformed: a section, a marker, a reference |
| `2` | structurally fine, but a question you left open is still open |

Exit code `2` is the one to understand. When you answer a question with "leave
open", the skill records an `OPEN_PRODUCT_DECISION`. This blocks the freeze on
purpose, which is the reason for recording it.

The skill cannot talk its way past a failure. `SPEC FROZEN` is reported only
after the strict check actually exited `0`, so the run ends like this:

```text
✓ specification artifacts produced
✓ grounding/provenance review passed
✓ ambiguity review passed
✓ deterministic validator passed
SPEC FROZEN
```

### 2. From a frozen spec to a reviewed technical design

Run the design skill with the feature directory:

```text
/rigorail-design specs/team-invites
```

That is the whole command. Before planning starts, one deterministic preflight
confirms the specification really is frozen, installs the pinned Spec Kit if it
is missing, points Spec Kit at this feature, and creates
`specs/team-invites/technical-context.md` if you have not written one.

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
uv run python -m rigorail.design_preflight specs/team-invites
```

It checks the spec is frozen, prepares Spec Kit, creates `technical-context.md`
if it is absent, and pins the feature directory. It never rewrites a
`technical-context.md` you wrote.

Install or repair the pinned Spec Kit workspace on its own:

```bash
uv run python -m rigorail.speckit_setup
```

Run either validator by hand:

```bash
uv run python .claude/skills/rigorail-spec/scripts/validate_spec.py specs/team-invites
uv run python .claude/skills/rigorail-design/scripts/validate_design.py specs/team-invites
```

While you are still drafting a spec and expect an open product decision, add
`--allow-open`. It means "I know about this one, check everything else". It is a
drafting aid and never establishes a freeze:

```bash
uv run python .claude/skills/rigorail-spec/scripts/validate_spec.py --allow-open specs/team-invites
```

Spec Kit resolves its target feature from `SPECIFY_FEATURE_DIRECTORY`, and
otherwise from `.specify/feature.json`. The preflight sets the first for the one
command it runs, which makes Spec Kit persist the second, so you never need to
export anything. If you are driving Spec Kit directly, you still can:

```bash
SPECIFY_FEATURE_DIRECTORY=specs/team-invites .specify/scripts/bash/setup-plan.sh --json
```

## What "frozen" means

A spec is frozen when `review.md` says `READY` and its validator exits `0`. A
design is frozen when `design-review.md` says `READY` and its validator exits
`0`.

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
