# EXP-001 — Specification pipeline

## Hypothesis

A structured discovery and clarification process may surface important implicit
decisions and reduce late requirement changes compared with directly asking an
LLM to turn raw notes into a specification.

## Test case

The experiment will use a real early-stage commerce MVP.

Raw inputs, generated artifacts, company information, and product-specific
details remain private and are not stored in Rigorail.

## Baseline

Raw notes → generic LLM prompt → specification.

The baseline prompt must be saved in the private experiment lab and reused
unchanged for the baseline run.

## Candidate mechanisms

Evaluate independently, not as a package:

1. BMAD product discovery / product brief
2. BMAD PRD
3. BMAD compact specification
4. Spec Kit clarification
5. Spec Kit requirements checklist

Do not assume every stage is useful or that they must be used together.

## Evaluation

For each mechanism record:

- human time consumed
- questions asked
- REQUIRED questions
- USEFUL questions
- NOISE questions
- previously implicit decisions surfaced
- useful decisions surfaced per 10 human minutes
- unjustified assumptions detected
- substantive output lines
- substantive output lines requiring human review
- notable failure modes


Question classification:

REQUIRED:
implementation or product behavior would remain materially ambiguous without
an answer.

USEFUL:
the answer materially improves the specification, but implementation could
reasonably begin without it.

NOISE:
the question does not justify the human attention it consumes.

## Downstream measurement

When implementation later occurs, record:

- requirement changes discovered after design started
- requirement changes discovered after implementation started
- misunderstandings traceable to the specification
- post-merge fixes traceable to missing or ambiguous requirements

## Decision rule

Evaluate marginal value, not document quality or polish.

A mechanism should survive only when it provides useful information not already
provided by cheaper preceding steps at an acceptable human-attention cost.

Possible decisions:

KEEP
MODIFY
REMOVE

## Status

NOT STARTED
