# Discovery Review: <Feature Name>

STATUS: BLOCKED
GATE: PENDING

## Blockers

- <None only when STATUS is READY; otherwise list every freeze blocker, including each open product D-###>

## Unsupported Firm Rules

- <None, or statement whose provenance does not authorize it>

## High-impact Ambiguities

- <None, or materially different valid product behaviors still possible>

## Unresolved Assumptions

- <Required to be explicit. Either "None identified." or the assumptions that remain unresolved. Never invent one to fill this section.>

## Consistency Findings

- <None, or contradictions/invalid references>

## Open Product Decisions

- <None, or D-### list>

## Open Technical Decisions

- <None, or D-### list>

## Human Semantic Gate

`GATE:` above is `APPROVED` only after a human confirmed that this contract is
the product they intend to build. The validator records that the gate happened;
it never performs it.

- Reviewed by: <human>
- Date: <YYYY-MM-DD>
- Confirmed: semantic correctness, material open decisions, no inference promoted without a decision, constraints

## Deterministic Validation

- Command: `python .claude/skills/rigorail-spec/scripts/validate_spec.py docs`
- Result: <PASS/FAIL>
