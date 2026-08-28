#!/usr/bin/env python3
"""Deterministic validator for Rigorail technical-design artifacts.

This validator checks only machine-checkable properties of `design-review.md`
and its accounting against the `OPEN_TECHNICAL_DECISION` entries declared in
`decisions.md`.

It deliberately does NOT judge whether a technical choice is good, whether prose
contains a product invention, or whether a framework claim is factually true.
Those remain LLM-review or documentation-verification responsibilities.

It also derives the next action from the findings, so the repair loop is routed
by a program rather than by the reviewer's own reading of its review, and is
bounded by a fixed number of automatic repair rounds.

Usage:
    python .claude/skills/rigorail-design/scripts/validate_design.py <design-directory>
    python .claude/skills/rigorail-design/scripts/validate_design.py --iteration 2 <dir>

Exit codes:
  0 = design-review.md is well formed and STATUS is READY
  1 = missing, malformed, or gate-violating artifacts
  2 = well formed, but the design is not READY yet
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

REVIEW_FILENAME = "design-review.md"
DECISIONS_FILENAME = "decisions.md"

STATUSES = ("READY", "NEEDS_PRODUCT_DECISION", "NEEDS_TECHNICAL_WORK")

# The six primary finding categories, in required document order.
FINDING_SECTIONS = (
    "PRODUCT_CONTRADICTIONS",
    "PRODUCT_INVENTIONS",
    "PRODUCT_BLOCKERS",
    "UNRESOLVED_TECHNICAL_DECISIONS",
    "UNVERIFIED_FRAMEWORK_FACTS",
    "TECHNICAL_INTEGRITY_GAPS",
)

# The only section whose findings require a human product decision.
BLOCKER_SECTION = "PRODUCT_BLOCKERS"

# Sections whose findings go back to the planner rather than to the human.
PLANNER_REWORK_SECTIONS = (
    "PRODUCT_CONTRADICTIONS",
    "PRODUCT_INVENTIONS",
    "UNRESOLVED_TECHNICAL_DECISIONS",
)

# Accounting ledger for open technical decisions the planner did resolve.
RESOLVED_SECTION = "RESOLVED_TECHNICAL_DECISIONS"

REQUIRED_SECTIONS = FINDING_SECTIONS + (RESOLVED_SECTION,)

REQUIRED_FINDING_FIELDS = ("evidence", "required action")

# Automatic repair/replan rounds allowed before the workflow must stop and
# report. Raise or lower this single number to change the bound.
MAX_REPAIR_ITERATIONS = 2

# Next action, derived from the findings. Only HUMAN_PRODUCT_DECISION costs
# human attention; every other blocking finding goes back to the planner.
ROUTE_FREEZE = "FREEZE"
ROUTE_HUMAN = "HUMAN_PRODUCT_DECISION"
ROUTE_REPLAN = "REPLAN"
ROUTE_REPAIR_LIMIT = "REPAIR_LIMIT_REACHED"
ROUTE_INVALID = "INVALID_ARTIFACTS"

STATUS_RE = re.compile(r"^STATUS:\s*(\S.*?)\s*$", re.MULTILINE)
SECTION_RE = re.compile(r"^##\s+([A-Z_]+)\s*$", re.MULTILINE)
FINDING_RE = re.compile(r"^-\s+\[(HIGH|MEDIUM|LOW)\]\s+(\S+)\s+—\s*(\S.*)$")
SEVERITY_TAG_RE = re.compile(r"^-\s+\[([A-Za-z_]+)\]")
FIELD_RE = re.compile(r"^\s{2,}-\s+([A-Za-z][A-Za-z /]*):\s*(\S.*)$")
LEDGER_RE = re.compile(r"^-\s+(D-\d{3,})\s+—\s*(\S.*)$")
NONE_RE = re.compile(r"^None\.?$", re.IGNORECASE)
DECISION_RE = re.compile(r"^- \*\*(D-\d{3,})\*\* \[([A-Z_]+)\]", re.MULTILINE)


@dataclass
class Finding:
    section: str
    severity: str
    identifier: str
    text: str
    fields: dict[str, str] = field(default_factory=dict)


@dataclass
class Result:
    design_dir: str
    errors: list[str]
    status: str | None
    findings: list[Finding]
    resolved_technical_decisions: list[str]
    open_technical_decisions: list[str]
    blocking: list[Finding] = field(default_factory=list)

    @property
    def ready(self) -> bool:
        return not self.errors and self.status == "READY"


def _split_sections(text: str, errors: list[str]) -> dict[str, str]:
    sections: dict[str, str] = {}
    matches = list(SECTION_RE.finditer(text))
    for index, match in enumerate(matches):
        name = match.group(1)
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        if name in sections:
            errors.append(f"{REVIEW_FILENAME} declares section ## {name} more than once")
            continue
        sections[name] = text[match.end() : end]
    return sections


def _parse_findings(section: str, body: str, errors: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    declared_none = False
    # The field a wrapped continuation line would belong to, and its indent.
    open_field: str | None = None
    field_indent = 0

    for raw_line in body.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue

        if not line.startswith((" ", "-")) and NONE_RE.match(line.strip()):
            declared_none = True
            continue

        match = FINDING_RE.match(line)
        if match:
            findings.append(Finding(section, match.group(1), match.group(2), match.group(3)))
            open_field = None
            continue

        field_match = FIELD_RE.match(line)
        if field_match and findings:
            open_field = field_match.group(1).strip().lower()
            field_indent = len(line) - len(line.lstrip())
            findings[-1].fields[open_field] = field_match.group(2)
            continue

        # A field value wrapped onto the next line: indented more deeply than its
        # field, and not itself a bullet, field or finding.
        indent = len(line) - len(line.lstrip())
        if findings and open_field and indent > field_indent and not line.lstrip().startswith("-"):
            findings[-1].fields[open_field] += " " + line.strip()
            continue

        severity_match = SEVERITY_TAG_RE.match(line)
        if severity_match and severity_match.group(1).upper() not in ("HIGH", "MEDIUM", "LOW"):
            errors.append(
                f"{section} finding has unknown severity {severity_match.group(1)!r}; "
                "expected HIGH, MEDIUM or LOW"
            )
            continue

        errors.append(f"{section} contains an unparseable line: {line.strip()!r}")

    if declared_none and findings:
        errors.append(f"{section} declares None but also lists findings")
    if not declared_none and not findings:
        errors.append(f"{section} must list at least one finding or the single word None")

    for finding in findings:
        for required in REQUIRED_FINDING_FIELDS:
            if required not in finding.fields:
                errors.append(
                    f"{section} finding {finding.identifier} is missing a "
                    f"'{required.capitalize()}:' field"
                )

    return findings


def _parse_resolved(body: str, errors: list[str]) -> list[str]:
    resolved: list[str] = []
    declared_none = False

    for raw_line in body.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue

        if not line.startswith((" ", "-")) and NONE_RE.match(line.strip()):
            declared_none = True
            continue

        match = LEDGER_RE.match(line)
        if match:
            resolved.append(match.group(1))
            continue

        errors.append(f"{RESOLVED_SECTION} contains an unparseable line: {line.strip()!r}")

    if declared_none and resolved:
        errors.append(f"{RESOLVED_SECTION} declares None but also lists decisions")
    if not declared_none and not resolved:
        errors.append(f"{RESOLVED_SECTION} must list at least one decision or the single word None")

    return resolved


def validate(design_dir: Path) -> Result:
    errors: list[str] = []
    status: str | None = None
    findings: list[Finding] = []
    resolved: list[str] = []
    open_technical: list[str] = []

    review_path = design_dir / REVIEW_FILENAME
    decisions_path = design_dir / DECISIONS_FILENAME

    if not review_path.is_file():
        errors.append(f"missing required artifact: {review_path}")
    else:
        review = review_path.read_text(encoding="utf-8")

        status_matches = STATUS_RE.findall(review)
        if len(status_matches) != 1:
            errors.append(
                f"{REVIEW_FILENAME} must contain exactly one STATUS line; "
                f"found {len(status_matches)}"
            )
        elif status_matches[0] not in STATUSES:
            errors.append(
                f"{REVIEW_FILENAME} has unrecognized STATUS: {status_matches[0]!r}; "
                f"expected one of {', '.join(STATUSES)}"
            )
        else:
            status = status_matches[0]

        sections = _split_sections(review, errors)
        for name in REQUIRED_SECTIONS:
            if name not in sections:
                errors.append(f"{REVIEW_FILENAME} missing section: ## {name}")

        for name in FINDING_SECTIONS:
            if name in sections:
                findings.extend(_parse_findings(name, sections[name], errors))

        if RESOLVED_SECTION in sections:
            resolved = _parse_resolved(sections[RESOLVED_SECTION], errors)

    unresolved = [f.identifier for f in findings if f.section == "UNRESOLVED_TECHNICAL_DECISIONS"]
    for section, identifiers in (
        (RESOLVED_SECTION, resolved),
        ("UNRESOLVED_TECHNICAL_DECISIONS", unresolved),
    ):
        for identifier in sorted({i for i in identifiers if identifiers.count(i) > 1}):
            errors.append(f"{section} lists {identifier} more than once")

    if not decisions_path.is_file():
        errors.append(f"missing required artifact: {decisions_path}")
    else:
        decisions = decisions_path.read_text(encoding="utf-8")
        entries = DECISION_RE.findall(decisions)
        open_product = sorted(i for i, t in entries if t == "OPEN_PRODUCT_DECISION")
        open_technical = sorted(i for i, t in entries if t == "OPEN_TECHNICAL_DECISION")

        for decision_id in open_product:
            errors.append(
                f"{DECISIONS_FILENAME} still declares OPEN_PRODUCT_DECISION {decision_id}; "
                "the specification is not approved for technical design"
            )

        if review_path.is_file():
            unresolved_ids = set(unresolved)
            resolved_ids = set(resolved)
            for decision_id in sorted(resolved_ids - set(open_technical)):
                errors.append(
                    f"{RESOLVED_SECTION} lists {decision_id}, which {DECISIONS_FILENAME} does "
                    "not declare as an OPEN_TECHNICAL_DECISION"
                )
            for decision_id in open_technical:
                in_resolved = decision_id in resolved_ids
                in_unresolved = decision_id in unresolved_ids
                if in_resolved and in_unresolved:
                    errors.append(
                        f"OPEN_TECHNICAL_DECISION {decision_id} is listed both as resolved "
                        "and as unresolved"
                    )
                elif not in_resolved and not in_unresolved:
                    errors.append(
                        f"OPEN_TECHNICAL_DECISION {decision_id} from {DECISIONS_FILENAME} is "
                        f"accounted for neither under {RESOLVED_SECTION} nor under "
                        "UNRESOLVED_TECHNICAL_DECISIONS"
                    )

    # STATUS is fully derived from the findings; no other value is valid.
    blocking = [f for f in findings if f.section == BLOCKER_SECTION]
    required_status = "NEEDS_PRODUCT_DECISION"
    if not blocking:
        blocking = [
            f
            for f in findings
            if f.section in PLANNER_REWORK_SECTIONS
            or (f.section == "TECHNICAL_INTEGRITY_GAPS" and f.severity == "HIGH")
        ]
        required_status = "NEEDS_TECHNICAL_WORK" if blocking else "READY"

    if status is not None and status != required_status:
        if blocking:
            listed = ", ".join(f"{f.section}:{f.identifier}" for f in blocking)
            errors.append(
                f"STATUS: {status} is not allowed while unresolved findings remain "
                f"({listed}); expected STATUS: {required_status}"
            )
        else:
            errors.append(
                f"STATUS: {status} is not allowed when no blocking finding remains; "
                "expected STATUS: READY"
            )

    return Result(
        design_dir=str(design_dir),
        errors=errors,
        status=status,
        findings=findings,
        resolved_technical_decisions=resolved,
        open_technical_decisions=open_technical,
        blocking=blocking,
    )


def route(result: Result, iteration: int = 0, limit: int = MAX_REPAIR_ITERATIONS) -> str:
    """Return the next action for ``result`` after ``iteration`` repair rounds.

    ``iteration`` counts repair/replan rounds already performed. Only a
    `PRODUCT_BLOCKER` reaches the human; everything else the planner is
    authorized to fix goes back to the planner until the bound is reached, and
    reaching the bound can never produce ``FREEZE``.
    """
    if result.errors:
        return ROUTE_INVALID
    if any(finding.section == BLOCKER_SECTION for finding in result.blocking):
        return ROUTE_HUMAN
    if result.blocking:
        return ROUTE_REPLAN if iteration < limit else ROUTE_REPAIR_LIMIT
    return ROUTE_FREEZE if result.ready else ROUTE_INVALID


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("design_dir", type=Path)
    parser.add_argument(
        "--iteration",
        type=int,
        default=0,
        help=(
            "automatic repair rounds already performed; at "
            f"{MAX_REPAIR_ITERATIONS} the route becomes {ROUTE_REPAIR_LIMIT}"
        ),
    )
    args = parser.parse_args(argv)

    result = validate(args.design_dir)

    print(f"Rigorail design validation: {result.design_dir}")
    print(f"review status: {result.status or 'MISSING'}")
    print(f"findings: {len(result.findings)}")
    print(f"open technical decisions declared: {len(result.open_technical_decisions)}")
    print(f"route: {route(result, args.iteration)}")
    for finding in result.blocking:
        print(f"BLOCKING: {finding.section} {finding.identifier} — {finding.text}")
    for error in result.errors:
        print(f"ERROR: {error}")

    if result.errors:
        return 1
    if result.status != "READY":
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
