# Principles

1. Human attention is the scarce resource.
2. Deterministic verification beats advisory prose.
3. Requirements and implementation must be independently reviewable.
4. Agents must provide evidence rather than claims.
5. Human review is selected by risk, not by diff size.
6. Diff size measures review cost, not risk.
7. Independent review should avoid inheriting implementation rationale unless
   that context is required to judge correctness.
8. Add mechanisms only when justified by observed failures, established failure
   modes, or high-consequence risks.
9. Every non-trivial pipeline layer must justify its marginal value.
10. Remove or downgrade mechanisms whose marginal value stays low relative to
    their cost, except for safeguards against rare high-consequence failures.
11. Prefer native framework primitives over custom abstractions.
12. CI should not require an LLM by default.
