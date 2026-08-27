# Ambiguity Review Protocol

Purpose: find missing product decisions that permit materially different valid implementations.

This is not a grounding review. Do not spend time re-proving sourced rules.

## Fresh-context requirement

Prefer a reviewer that did not draft the spec. Give it:

- authoritative sources;
- `spec.md`;
- `decisions.md`.

Do not provide previous reviewers' recommendations or hidden expected answers.

## Taxonomy

Search in this order:

1. actor permissions and visibility;
2. cardinality and composition;
3. ownership and reassignment;
4. lifecycle/state transitions;
5. publication/moderation distinctions;
6. pricing/payment semantics;
7. routing/fan-out/isolation;
8. destructive actions and reversal;
9. edits to already-active/published objects;
10. failure/retry/partial-success behavior;
11. scope boundaries with meaningful implementation cost.

## Required-flow and materiality gates

Report a blocking ambiguity only if **both** are true:

1. the choice is necessary to implement an in-scope behavior required by the authoritative sources or an authorized decision; and
2. two competent implementers could make different choices, both compatible with the current sources, and the difference would materially affect product behavior, data model, API contract, routing, permissions, money, lifecycle, or required implementation scope.

Do **not** report a blocking ambiguity merely because an optional capability could exist. Source silence about cancellation, post-launch editing, later repricing, channel administration, or another additive feature normally means that capability is not required by this spec unless the sourced flow necessarily reaches that decision point.

Do not combine separate dimensions in one question. Example: `quantity > 1` and `multiple distinct products` are separate cardinality questions.

## Question format

```text
Question: <neutral wording>
Why it matters: <implementation-changing consequence>
Options: <neutral alternatives, if useful>
Deferral allowed: yes
```

Do not recommend an answer unless the human asks.

## Reviewer rule

Never infer the answer from:

- the simplest implementation;
- a single success scenario;
- common industry practice;
- framework defaults;
- an architectural preference.

If a high-impact answer is not authorized, return it as a **candidate product decision** to the orchestrator. The reviewer is read-only and must not edit `decisions.md` or `spec.md`. Only create `OPEN_PRODUCT_DECISION` after the human explicitly defers the question.

Return at most five findings, highest risk first. Low-impact optional-capability observations may be omitted.
