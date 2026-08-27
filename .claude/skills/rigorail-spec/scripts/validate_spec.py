#!/usr/bin/env python3
"""Deterministic validator for Rigorail product-spec artifacts.

Strict mode is a freeze gate. Use --allow-open while drafting to allow explicitly
open product decisions while still enforcing provenance and artifact structure.

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

REQUIRED_SPEC_SECTIONS = (
    "Goal",
    "Non-goals",
    "Actors",
    "User Flows",
    "Functional Requirements",
    "Acceptance Examples",
    "Key Entities",
    "Constraints",
    "Open Decisions",
    "Success Criteria",
)

REQUIRED_REVIEW_SECTIONS = (
    "Blockers",
    "Unsupported Firm Rules",
    "High-impact Ambiguities",
    "Consistency Findings",
    "Open Product Decisions",
    "Open Technical Decisions",
    "Deterministic Validation",
)

ALLOWED_DECISION_TYPES = {
    "PREVIOUS_HUMAN_DECISION",
    "NEW_HUMAN_DECISION",
    "INFERENCE",
    "TECHNICAL_DECISION",
    "OPEN_PRODUCT_DECISION",
    "OPEN_TECHNICAL_DECISION",
}

FIRM_DECISION_TYPES = {
    "PREVIOUS_HUMAN_DECISION",
    "NEW_HUMAN_DECISION",
}

SOURCE_RE = re.compile(r"^- \*\*(S-\d{3,})\*\* \[SOURCE_FACT\]", re.MULTILINE)
DECISION_RE = re.compile(
    r"^- \*\*(D-\d{3,})\*\* \[([A-Z_]+)\](?: \[[^\]]+\])*\s+—",
    re.MULTILINE,
)
RULE_RE = re.compile(
    r"^- \*\*((?:FR|SC)-[A-Za-z0-9.-]+)\*\*:\s*(.+)$",
    re.MULTILINE,
)
PROVENANCE_RE = re.compile(r"<!--\s*provenance:\s*((?:S|D)-\d{3,})\s*-->")
STATUS_RE = re.compile(r"^STATUS:\s*(READY|BLOCKED)\s*$", re.MULTILINE)
OPEN_PRODUCT_SECTION_RE = re.compile(
    r"^## Open Decisions\s*$.*?^### Product\s*$(.*?)(?=^### Technical\s*$|^## |\Z)",
    re.MULTILINE | re.DOTALL,
)
BLOCKERS_SECTION_RE = re.compile(
    r"^## Blockers\s*$(.*?)(?=^## |\Z)",
    re.MULTILINE | re.DOTALL,
)


@dataclass
class Result:
    feature_dir: str
    errors: list[str]
    warnings: list[str]
    open_product_decisions: list[str]
    open_technical_decisions: list[str]
    rule_count: int
    status: str | None

    @property
    def structurally_valid(self) -> bool:
        return not self.errors


def _read(path: Path, errors: list[str]) -> str:
    if not path.exists():
        errors.append(f"missing required artifact: {path.name}")
        return ""
    return path.read_text(encoding="utf-8")


def _headings(text: str) -> set[str]:
    return {match.group(1).strip() for match in re.finditer(r"^##\s+(.+?)\s*$", text, re.MULTILINE)}


def validate(feature_dir: Path) -> Result:
    errors: list[str] = []
    warnings: list[str] = []

    spec = _read(feature_dir / "spec.md", errors)
    decisions = _read(feature_dir / "decisions.md", errors)
    review = _read(feature_dir / "review.md", errors)

    if spec:
        missing = [s for s in REQUIRED_SPEC_SECTIONS if s not in _headings(spec)]
        for section in missing:
            errors.append(f"spec.md missing section: ## {section}")

    if review:
        missing = [s for s in REQUIRED_REVIEW_SECTIONS if s not in _headings(review)]
        for section in missing:
            errors.append(f"review.md missing section: ## {section}")

    sources = set(SOURCE_RE.findall(decisions)) if decisions else set()
    decision_pairs = DECISION_RE.findall(decisions) if decisions else []
    decision_types = dict(decision_pairs)

    for decision_id, decision_type in decision_pairs:
        if decision_type not in ALLOWED_DECISION_TYPES:
            errors.append(f"{decision_id} uses unknown decision type: {decision_type}")

    open_product = sorted(
        decision_id
        for decision_id, decision_type in decision_pairs
        if decision_type == "OPEN_PRODUCT_DECISION"
    )
    open_technical = sorted(
        decision_id
        for decision_id, decision_type in decision_pairs
        if decision_type == "OPEN_TECHNICAL_DECISION"
    )

    rules = RULE_RE.findall(spec) if spec else []
    for rule_id, body in rules:
        provenance = PROVENANCE_RE.findall(body)
        if len(provenance) != 1:
            errors.append(
                f"{rule_id} must have exactly one hidden provenance marker; found {len(provenance)}"
            )
            continue

        ref = provenance[0]
        if ref.startswith("S-"):
            if ref not in sources:
                errors.append(f"{rule_id} references unknown source {ref}")
            continue

        if ref not in decision_types:
            errors.append(f"{rule_id} references unknown decision {ref}")
            continue

        dtype = decision_types[ref]
        if dtype not in FIRM_DECISION_TYPES:
            errors.append(f"{rule_id} is a firm rule but {ref} has non-authorizing type {dtype}")

    if spec and open_product:
        match = OPEN_PRODUCT_SECTION_RE.search(spec)
        product_open_text = match.group(1) if match else ""
        for decision_id in open_product:
            if decision_id not in product_open_text:
                errors.append(
                    f"open product decision {decision_id} is "
                    "not listed under spec.md > Open Decisions > Product"
                )

    status = None
    if review:
        status_match = STATUS_RE.search(review)
        if not status_match:
            errors.append(
                "review.md must contain exactly one STATUS: READY or STATUS: BLOCKED line"
            )
        else:
            status = status_match.group(1)

    if status == "READY" and open_product:
        errors.append("review.md says READY while OPEN_PRODUCT_DECISION entries still exist")

    if status == "BLOCKED" and open_product:
        blockers_match = BLOCKERS_SECTION_RE.search(review)
        blockers_text = blockers_match.group(1) if blockers_match else ""
        for decision_id in open_product:
            if decision_id not in blockers_text:
                errors.append(
                    f"review.md says BLOCKED but Blockers does not list open product "
                    f"decision {decision_id}"
                )

    # A few deterministic hygiene checks. These are warnings because semantic
    # interpretation still belongs to the reviewer/human gate.
    if spec:
        for token in ("[NEEDS CLARIFICATION]", "<TBD>", "TODO PRODUCT DECISION"):
            if token in spec:
                warnings.append(f"spec.md contains unresolved marker: {token}")

        # Numeric thresholds in SCs are legitimate only when provenance exists;
        # provenance validity is already enforced above. Surface them for human
        # attention because invented precision was an observed failure mode.
        for rule_id, body in rules:
            has_numeric_threshold = rule_id.startswith("SC-") and re.search(
                r"\b\d+(?:\.\d+)?\s*"
                r"(?:%|ms|s|sec|seconds?|minutes?|mins?|hours?|days?)\b",
                body,
                re.I,
            )
            if has_numeric_threshold:
                warnings.append(
                    f"{rule_id} contains a numeric threshold; confirm its cited "
                    "provenance authorizes the number"
                )

    return Result(
        feature_dir=str(feature_dir),
        errors=errors,
        warnings=warnings,
        open_product_decisions=open_product,
        open_technical_decisions=open_technical,
        rule_count=len(rules),
        status=status,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("feature_dir", type=Path)
    parser.add_argument(
        "--allow-open",
        action="store_true",
        help="allow OPEN_PRODUCT_DECISION entries while drafting",
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
        )
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"Rigorail spec validation: {args.feature_dir}")
        print(f"rules: {result.rule_count}")
        print(f"review status: {result.status or 'MISSING'}")
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
