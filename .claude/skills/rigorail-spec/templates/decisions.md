# Decision Ledger: <Feature Name>

## Sources

Use one line per authoritative source. Keep the identifier stable.

- **S-001** [SOURCE_FACT] — <source name/path/message> — <what authority it has>

## Decisions

Use exactly one primary type per decision entry. Do not create a D-entry for a fact already directly represented by an authoritative S-source; cite S directly from the spec.

- **D-001** [NEW_HUMAN_DECISION] [risk:high] [status:decided] — <topic> — <decision> — evidence: <source/question/answer>
- **D-002** [OPEN_PRODUCT_DECISION] [risk:high] [status:open] — <topic> — <material alternatives that remain possible>
- **D-003** [OPEN_TECHNICAL_DECISION] [risk:medium] [status:open] — <topic> — <why safe to defer to technical design>
- **D-004** [INFERENCE] [risk:low] [status:unconfirmed] — <topic> — <plausible inference, not allowed to ground a firm product rule>

## Decision History

Append only material changes to an existing decision.

- <YYYY-MM-DD> — <D-###> — <old state> → <new state> — <reason/human confirmation>
