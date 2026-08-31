#!/usr/bin/env python3
"""Deterministic validator for Rigorail product-contract artifacts.

Strict mode is a freeze gate. Use --allow-open while drafting to allow explicitly
open product decisions while still enforcing provenance and artifact structure.

This validator checks addressability, references, and structure. It cannot check
whether a product statement is semantically grounded, whether it describes one
obligation, or whether it describes the right product. Those remain the job of
the grounding review, the ambiguity review, and the human semantic gate.

Exit codes:
  0 = valid for requested mode
  1 = structural/provenance validation failure
  2 = structurally valid but strict freeze is blocked by open product decisions
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

SOURCE_FILENAME = "source.md"
SPEC_FILENAME = "product-spec.md"
DECISIONS_FILENAME = "decisions.md"
REVIEW_FILENAME = "discovery-review.md"

CONSTRAINT_SECTION = "§C Constraints"
WITHDRAWN_SECTION = "Withdrawn"

REQUIRED_SPEC_SECTIONS = (
    "Goal",
    "Non-goals",
    "Actors",
    "User Flows",
    CONSTRAINT_SECTION,
    "Acceptance Examples",
    "Key Entities",
    "Open Decisions",
)

REQUIRED_REVIEW_SECTIONS = (
    "Blockers",
    "Unsupported Firm Rules",
    "High-impact Ambiguities",
    "Unresolved Assumptions",
    "Consistency Findings",
    "Open Product Decisions",
    "Open Technical Decisions",
    "Human Semantic Gate",
    "Deterministic Validation",
)

ALLOWED_LAYERS = {"PRODUCT", "TECHNICAL"}
ALLOWED_PROVENANCE = {"SOURCE", "HUMAN", "INFERRED"}
ALLOWED_STATUSES = {"decided", "open", "unconfirmed"}

#: Provenance values that may authorize a firm product statement. ``INFERRED`` is
#: deliberately absent: an inference becomes authoritative only by passing through
#: the human semantic gate, which turns it into a ``HUMAN`` decision.
AUTHORIZING_PROVENANCE = {"SOURCE", "HUMAN"}

# PRODUCT_ID := \d+\.\d+ | C\d+
PRODUCT_ID_RE = re.compile(r"^(?:\d+\.\d+|C\d+)$")
BEHAVIOR_ID_RE = re.compile(r"^(\d+)\.\d+$")
BEHAVIOR_SECTION_RE = re.compile(r"^§(\d+)(?:\s|$)")

SECTION_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)

#: The canonical product statement: `- **§<id>** — <non-empty body>`. The em
#: dash separator and the body are both required.
STATEMENT_RE = re.compile(r"^- \*\*§([^*]*)\*\*\s+—\s+(\S.*)$")

#: Any line that visibly tries to be a product statement. A line matching this
#: but not the canonical form is an error, never a line the parser skips: a
#: statement that silently disappears is exactly the failure mode this
#: validator exists to prevent.
STATEMENT_LIKE_RE = re.compile(r"^\s*(?:-\s+)?\*{0,2}§")
REFERENCE_RE = re.compile(r"§([A-Za-z0-9]+(?:\.[A-Za-z0-9]+)*)")

SOURCE_PREFIX_RE = re.compile(r"^- \*\*S-")
SOURCE_RE = re.compile(r"^- \*\*(S-\d{3,})\*\*\s+—\s+\S")
DECISION_PREFIX_RE = re.compile(r"^- \*\*D-")
DECISION_RE = re.compile(
    r"^- \*\*(D-\d{3,})\*\* "
    r"\[(\d{4}-\d{2}-\d{2})\] "
    r"\[([A-Za-z_]+)\] "
    r"\[([A-Za-z_]+)\] "
    r"\[status:([A-Za-z_]+)\]"
    r"(?: \[risk:([A-Za-z_]+)\])?"
    r"\s+—\s+(\S.*)$"
)

SOURCE_CITATION_RE = re.compile(r"\bS-\d{3,}\b")
PROVENANCE_RE = re.compile(r"<!--\s*provenance:\s*((?:S|D)-\d{3,})\s*-->")
STATUS_RE = re.compile(r"^STATUS:\s*(READY|BLOCKED)\s*$", re.MULTILINE)
GATE_RE = re.compile(r"^GATE:\s*(APPROVED|PENDING|REJECTED)\s*$", re.MULTILINE)

#: An enumeration of three or more comma-separated items closed by "and"/"or".
#: This is a heuristic for a statement that bundles several obligations. It is
#: never proof: atomicity is semantic, so a hit is only ever a warning.
MULTI_OBLIGATION_RE = re.compile(r"\w+\s*,\s*[^,]+,\s*(?:and|or)\s+\w", re.I)

NUMERIC_THRESHOLD_RE = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:%|ms|s|sec|seconds?|minutes?|mins?|hours?|days?)\b",
    re.I,
)

UNRESOLVED_MARKERS = ("[NEEDS CLARIFICATION]", "<TBD>", "TODO PRODUCT DECISION")


@dataclass
class Statement:
    """One addressable product statement in ``product-spec.md``."""

    id: str
    body: str
    section: str
    withdrawn: bool


@dataclass
class Decision:
    """One ledger entry in ``decisions.md``."""

    id: str
    date: str
    layer: str
    provenance: str
    status: str
    risk: str | None
    body: str


@dataclass
class Result:
    feature_dir: str
    errors: list[str]
    warnings: list[str]
    open_product_decisions: list[str]
    open_technical_decisions: list[str]
    behavior_ids: list[str]
    constraint_ids: list[str]
    withdrawn_ids: list[str]
    status: str | None
    gate: str | None
    statement_count: int

    @property
    def structurally_valid(self) -> bool:
        return not self.errors


def _read(path: Path, errors: list[str]) -> str:
    if not path.exists():
        errors.append(f"missing required artifact: {path.name}")
        return ""
    return path.read_text(encoding="utf-8")


def _headings(text: str) -> set[str]:
    return {match.group(1).strip() for match in SECTION_RE.finditer(text)}


def _sections(text: str) -> list[tuple[str, str]]:
    """Split ``text`` into ``(heading, body)`` pairs for every level-2 heading."""
    matches = list(SECTION_RE.finditer(text))
    sections: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections.append((match.group(1).strip(), text[match.end() : end]))
    return sections


def _section_body(text: str, heading: str) -> str:
    for name, body in _sections(text):
        if name == heading:
            return body
    return ""


def _parse_statements(spec: str, errors: list[str]) -> list[Statement]:
    """Parse every product statement, rejecting malformed and misplaced ones."""
    statements: list[Statement] = []
    seen_behavior_sections: dict[str, str] = {}

    for heading, body in _sections(spec):
        section_match = BEHAVIOR_SECTION_RE.match(heading)
        if section_match:
            major = section_match.group(1)
            if major in seen_behavior_sections:
                errors.append(
                    f"duplicate behavior section number §{major}: "
                    f"'{seen_behavior_sections[major]}' and '{heading}'"
                )
            else:
                seen_behavior_sections[major] = heading

        for line in body.splitlines():
            line = line.rstrip()
            if not STATEMENT_LIKE_RE.match(line):
                continue

            match = STATEMENT_RE.match(line)
            if not match:
                errors.append(
                    "product statement must use the canonical form "
                    f"`- **§<id>** — <statement>`; found: {line.strip()[:60]}"
                )
                continue

            statement_id = match.group(1).strip()
            rest = match.group(2)

            if not PRODUCT_ID_RE.match(statement_id):
                errors.append(
                    f"malformed product statement id: §{statement_id} "
                    "(expected §<n>.<m> for a behavior or §C<n> for a constraint)"
                )
                continue

            if not PROVENANCE_RE.sub("", rest).strip():
                errors.append(f"§{statement_id} has an empty statement body")
                continue

            if heading == WITHDRAWN_SECTION:
                statements.append(Statement(statement_id, rest, heading, withdrawn=True))
                continue

            if section_match:
                expected = section_match.group(1)
                behavior_match = BEHAVIOR_ID_RE.match(statement_id)
                if not behavior_match:
                    errors.append(
                        f"§{statement_id} is a constraint id but appears in behavior "
                        f"section '## {heading}'"
                    )
                    continue
                if behavior_match.group(1) != expected:
                    errors.append(
                        f"§{statement_id} does not belong to behavior section "
                        f"'## {heading}'; expected §{expected}.<m>"
                    )
                    continue
            elif heading == CONSTRAINT_SECTION:
                if not statement_id.startswith("C"):
                    errors.append(
                        f"§{statement_id} is a behavior id but appears in '## {CONSTRAINT_SECTION}'"
                    )
                    continue
            else:
                errors.append(
                    f"§{statement_id} appears in '## {heading}', which is neither a "
                    f"behavior section, '## {CONSTRAINT_SECTION}', nor '## {WITHDRAWN_SECTION}'"
                )
                continue

            statements.append(Statement(statement_id, rest, heading, withdrawn=False))

    seen: set[str] = set()
    for statement in statements:
        if statement.id in seen:
            errors.append(f"duplicate product statement id: §{statement.id}")
        seen.add(statement.id)

    return statements


def _parse_decisions(decisions: str, errors: list[str]) -> tuple[set[str], list[Decision]]:
    """Parse the ledger. Malformed ``S-``/``D-`` lines fail rather than vanish."""
    sources: set[str] = set()
    entries: list[Decision] = []

    for line in decisions.splitlines():
        line = line.rstrip()

        if SOURCE_PREFIX_RE.match(line):
            match = SOURCE_RE.match(line)
            if not match:
                errors.append(
                    f"malformed source entry (expected `- **S-###** — <locator> — "
                    f"<authority>`): {line[:80]}"
                )
                continue
            if match.group(1) in sources:
                errors.append(f"duplicate source id: {match.group(1)}")
            sources.add(match.group(1))
            continue

        if DECISION_PREFIX_RE.match(line):
            match = DECISION_RE.match(line)
            if not match:
                errors.append(
                    f"malformed decision entry (expected `- **D-###** [YYYY-MM-DD] "
                    f"[LAYER] [PROVENANCE] [status:<state>] [risk:<level>] — …`): {line[:80]}"
                )
                continue
            entry = Decision(
                id=match.group(1),
                date=match.group(2),
                layer=match.group(3),
                provenance=match.group(4),
                status=match.group(5),
                risk=match.group(6),
                body=match.group(7),
            )
            if any(entry.id == existing.id for existing in entries):
                errors.append(f"duplicate decision id: {entry.id}")
            entries.append(entry)

    for entry in entries:
        if entry.layer not in ALLOWED_LAYERS:
            errors.append(f"{entry.id} uses unknown layer: {entry.layer}")
        if entry.provenance not in ALLOWED_PROVENANCE:
            errors.append(f"{entry.id} uses unknown provenance: {entry.provenance}")
        if entry.status not in ALLOWED_STATUSES:
            errors.append(f"{entry.id} uses unknown status: {entry.status}")

        # An inference is a candidate, not an authority. Promoting one is a human
        # act that produces a HUMAN decision; it never happens by relabelling.
        if entry.provenance == "INFERRED" and entry.status == "decided":
            errors.append(
                f"{entry.id} is INFERRED with status:decided; an inference becomes firm "
                "only as a HUMAN decision through the semantic gate"
            )

        # SOURCE provenance means "an authoritative source says so". The cited
        # source must exist, or SOURCE becomes a channel for unattributed rules
        # that only has to look grounded.
        if entry.provenance == "SOURCE":
            cited = SOURCE_CITATION_RE.findall(entry.body)
            if not cited:
                errors.append(f"{entry.id} claims SOURCE provenance but cites no S-### source")
            for reference in sorted(set(cited)):
                if reference not in sources:
                    errors.append(
                        f"{entry.id} claims SOURCE provenance but references "
                        f"unknown source {reference}"
                    )

    return sources, entries


def _check_references(text: str, filename: str, known: set[str], errors: list[str]) -> None:
    """Every ``§`` reference in ``text`` must be a well-formed, existing id."""
    for match in REFERENCE_RE.finditer(text):
        token = match.group(1)
        if not PRODUCT_ID_RE.match(token):
            errors.append(f"{filename} contains a malformed product id reference: §{token}")
        elif token not in known:
            errors.append(f"{filename} references unknown product statement §{token}")


def validate(feature_dir: Path) -> Result:
    errors: list[str] = []
    warnings: list[str] = []

    # source.md is authoritative provenance, never a parsed input. Nothing written
    # inside it can create a source, a decision, or a product statement.
    source = _read(feature_dir / SOURCE_FILENAME, errors)
    spec = _read(feature_dir / SPEC_FILENAME, errors)
    decisions = _read(feature_dir / DECISIONS_FILENAME, errors)
    review = _read(feature_dir / REVIEW_FILENAME, errors)

    if (feature_dir / SOURCE_FILENAME).exists() and not source.strip():
        errors.append(f"{SOURCE_FILENAME} is empty; it must preserve the authoritative input")

    if spec:
        headings = _headings(spec)
        for section in REQUIRED_SPEC_SECTIONS:
            if section not in headings:
                errors.append(f"{SPEC_FILENAME} missing section: ## {section}")
        if not any(BEHAVIOR_SECTION_RE.match(heading) for heading in headings):
            errors.append(f"{SPEC_FILENAME} has no behavior section (## §<n> <title>)")

    if review:
        headings = _headings(review)
        for section in REQUIRED_REVIEW_SECTIONS:
            if section not in headings:
                errors.append(f"{REVIEW_FILENAME} missing section: ## {section}")

    statements = _parse_statements(spec, errors) if spec else []
    sources, entries = _parse_decisions(decisions, errors) if decisions else (set(), [])
    by_id = {entry.id: entry for entry in entries}

    open_product = sorted(
        entry.id for entry in entries if entry.layer == "PRODUCT" and entry.status == "open"
    )
    open_technical = sorted(
        entry.id for entry in entries if entry.layer == "TECHNICAL" and entry.status == "open"
    )

    firm = [statement for statement in statements if not statement.withdrawn]

    for statement in firm:
        provenance = PROVENANCE_RE.findall(statement.body)
        if len(provenance) != 1:
            errors.append(
                f"§{statement.id} must have exactly one hidden provenance marker; "
                f"found {len(provenance)}"
            )
            continue

        ref = provenance[0]
        if ref.startswith("S-"):
            if ref not in sources:
                errors.append(f"§{statement.id} references unknown source {ref}")
            continue

        entry = by_id.get(ref)
        if entry is None:
            errors.append(f"§{statement.id} references unknown decision {ref}")
            continue
        if entry.layer != "PRODUCT":
            errors.append(
                f"§{statement.id} is a firm product statement but {ref} is a {entry.layer} decision"
            )
        elif entry.status != "decided":
            errors.append(
                f"§{statement.id} is a firm product statement but {ref} has status:{entry.status}"
            )
        elif entry.provenance not in AUTHORIZING_PROVENANCE:
            errors.append(
                f"§{statement.id} is a firm product statement but {ref} has "
                f"non-authorizing provenance {entry.provenance}"
            )

    known_ids = {statement.id for statement in statements}
    if decisions:
        _check_references(decisions, DECISIONS_FILENAME, known_ids, errors)
    if review:
        _check_references(review, REVIEW_FILENAME, known_ids, errors)

    if spec and open_product:
        product_open_text = _open_product_subsection(spec)
        for decision_id in open_product:
            if decision_id not in product_open_text:
                errors.append(
                    f"open product decision {decision_id} is not listed under "
                    f"{SPEC_FILENAME} > Open Decisions > Product"
                )

    status = None
    gate = None
    if review:
        status_matches = STATUS_RE.findall(review)
        if len(status_matches) != 1:
            errors.append(
                f"{REVIEW_FILENAME} must contain exactly one STATUS: READY or "
                f"STATUS: BLOCKED line; found {len(status_matches)}"
            )
        else:
            status = status_matches[0]

        gate_matches = GATE_RE.findall(review)
        if len(gate_matches) != 1:
            errors.append(
                f"{REVIEW_FILENAME} must contain exactly one GATE: APPROVED, "
                f"GATE: PENDING, or GATE: REJECTED line; found {len(gate_matches)}"
            )
        else:
            gate = gate_matches[0]

        assumptions = _section_body(review, "Unresolved Assumptions").strip()
        if not assumptions:
            errors.append(
                f"{REVIEW_FILENAME} > Unresolved Assumptions must state the outcome "
                "explicitly, including when none remain"
            )

    if status == "READY" and open_product:
        errors.append(f"{REVIEW_FILENAME} says READY while open PRODUCT decisions still exist")

    # The validator records that the gate happened. It never performs it.
    if status == "READY" and gate is not None and gate != "APPROVED":
        errors.append(f"{REVIEW_FILENAME} says READY but the human semantic gate is {gate}")

    if status == "BLOCKED" and open_product:
        blockers_text = _section_body(review, "Blockers")
        for decision_id in open_product:
            if decision_id not in blockers_text:
                errors.append(
                    f"{REVIEW_FILENAME} says BLOCKED but Blockers does not list open "
                    f"product decision {decision_id}"
                )

    if spec:
        for token in UNRESOLVED_MARKERS:
            if token in spec:
                warnings.append(f"{SPEC_FILENAME} contains unresolved marker: {token}")

        for statement in firm:
            body = PROVENANCE_RE.sub("", statement.body).strip()

            # Heuristic only. Whether a statement carries one obligation is a
            # semantic question this validator does not and cannot decide.
            if MULTI_OBLIGATION_RE.search(body):
                warnings.append(
                    f"§{statement.id} enumerates several actions and may describe more "
                    "than one product obligation; atomicity is semantic and is not "
                    "verified by this check"
                )

            # Invented precision was an observed failure mode: a number added to
            # make a statement look measurable. Provenance validity is enforced
            # above; this only asks a human to confirm the number itself.
            if NUMERIC_THRESHOLD_RE.search(body):
                warnings.append(
                    f"§{statement.id} contains a numeric threshold; confirm its cited "
                    "provenance authorizes the number"
                )

    return Result(
        feature_dir=str(feature_dir),
        errors=errors,
        warnings=warnings,
        open_product_decisions=open_product,
        open_technical_decisions=open_technical,
        behavior_ids=[s.id for s in firm if BEHAVIOR_ID_RE.match(s.id)],
        constraint_ids=[s.id for s in firm if s.id.startswith("C")],
        withdrawn_ids=[s.id for s in statements if s.withdrawn],
        status=status,
        gate=gate,
        statement_count=len(firm),
    )


def _open_product_subsection(spec: str) -> str:
    """Fallback for the ``### Product`` subsection under ``## Open Decisions``."""
    match = re.search(
        r"^## Open Decisions\s*$.*?^### Product\s*$(.*?)(?=^### |^## |\Z)",
        spec,
        re.MULTILINE | re.DOTALL,
    )
    return match.group(1) if match else ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("feature_dir", type=Path)
    parser.add_argument(
        "--allow-open",
        action="store_true",
        help="allow open PRODUCT decisions while drafting",
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args(argv)

    result = validate(args.feature_dir)

    if args.json:
        payload = asdict(result)
        payload["structurally_valid"] = result.structurally_valid
        payload["freeze_ready"] = (
            result.structurally_valid
            and not result.open_product_decisions
            and result.status == "READY"
            and result.gate == "APPROVED"
        )
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"Rigorail product-contract validation: {args.feature_dir}")
        print(f"behaviors: {len(result.behavior_ids)}")
        print(f"constraints: {len(result.constraint_ids)}")
        print(f"withdrawn: {len(result.withdrawn_ids)}")
        print(f"review status: {result.status or 'MISSING'}")
        print(f"human semantic gate: {result.gate or 'MISSING'}")
        print(f"open product decisions: {len(result.open_product_decisions)}")
        print(f"open technical decisions: {len(result.open_technical_decisions)}")
        for warning in result.warnings:
            print(f"WARN: {warning}")
        for error in result.errors:
            print(f"ERROR: {error}")

    if result.errors:
        return 1
    if result.open_product_decisions and not args.allow_open:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
