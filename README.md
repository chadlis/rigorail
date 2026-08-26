# Rigorail

Rigorail is an experimental, reusable framework for disciplined agentic
software development.

## Core principle

> Human attention is the scarce resource. Anything machine-verifiable should
> be verified deterministically. LLMs should be used only where judgment is
> required.

## Status

**Experimental.** This repository is a bootstrap — a clean foundation for
future experiments. It is **not currently ready for external use**.

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

