from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "validate_spec.py"
spec = importlib.util.spec_from_file_location("rigorail_spec_validator", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)


SPEC = """# Feature

**Status:** Draft

## Goal
x
## Non-goals
x
## Actors
x
## User Flows
x
## Functional Requirements
- **FR-001**: The system MUST do x. <!-- provenance: S-001 -->
## Acceptance Examples
x
## Key Entities
x
## Constraints
x
## Open Decisions
### Product
None
### Technical
None
## Success Criteria
- **SC-001**: 100% of x succeeds. <!-- provenance: D-001 -->
"""

DECISIONS = """# Decision Ledger

## Sources
- **S-001** [SOURCE_FACT] — source — authority

## Decisions
- **D-001** [NEW_HUMAN_DECISION] [risk:high] [status:decided] — target — 100pct — evidence: user

## Decision History
"""

REVIEW = """# Spec Review

STATUS: READY

## Blockers
None
## Unsupported Firm Rules
None
## High-impact Ambiguities
None
## Consistency Findings
None
## Open Product Decisions
None
## Open Technical Decisions
None
## Deterministic Validation
PASS
"""

OPEN_PRODUCT_DECISION_LINE = (
    "\n- **D-002** [OPEN_PRODUCT_DECISION] [risk:high] [status:open] — cart\n"
)
OPEN_TECHNICAL_DECISION_LINE = (
    "\n- **D-002** [OPEN_TECHNICAL_DECISION] [risk:medium] [status:open] — auth\n"
)


class ValidatorTests(unittest.TestCase):
    def make_feature(self, spec_text=SPEC, decisions_text=DECISIONS, review_text=REVIEW):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        (root / "spec.md").write_text(spec_text, encoding="utf-8")
        (root / "decisions.md").write_text(decisions_text, encoding="utf-8")
        (root / "review.md").write_text(review_text, encoding="utf-8")
        self.addCleanup(tmp.cleanup)
        return root

    def test_valid_contract(self):
        result = module.validate(self.make_feature())
        self.assertEqual([], result.errors)
        self.assertEqual(2, result.rule_count)

    def test_missing_provenance_fails(self):
        text = SPEC.replace(" <!-- provenance: S-001 -->", "")
        result = module.validate(self.make_feature(spec_text=text))
        self.assertTrue(any("FR-001" in e and "provenance" in e for e in result.errors))

    def test_unknown_reference_fails(self):
        text = SPEC.replace("S-001", "S-999")
        result = module.validate(self.make_feature(spec_text=text))
        self.assertTrue(any("unknown source S-999" in e for e in result.errors))

    def test_inference_cannot_ground_firm_rule(self):
        decisions = DECISIONS.replace("NEW_HUMAN_DECISION", "INFERENCE")
        result = module.validate(self.make_feature(decisions_text=decisions))
        self.assertTrue(any("non-authorizing type INFERENCE" in e for e in result.errors))

    def test_open_product_decision_listed_in_spec_passes_draft(self):
        decisions = DECISIONS + OPEN_PRODUCT_DECISION_LINE
        spec_text = SPEC.replace("### Product\nNone", "### Product\n- D-002 — cart")
        review_text = REVIEW.replace("STATUS: READY", "STATUS: BLOCKED").replace(
            "## Blockers\nNone", "## Blockers\n- D-002 — cart"
        )
        result = module.validate(
            self.make_feature(
                spec_text=spec_text,
                decisions_text=decisions,
                review_text=review_text,
            )
        )
        self.assertEqual([], result.errors)
        self.assertEqual(["D-002"], result.open_product_decisions)

    def test_open_product_decision_missing_from_spec_fails(self):
        decisions = DECISIONS + OPEN_PRODUCT_DECISION_LINE
        review_text = REVIEW.replace("STATUS: READY", "STATUS: BLOCKED").replace(
            "## Blockers\nNone", "## Blockers\n- D-002 — cart"
        )
        result = module.validate(
            self.make_feature(decisions_text=decisions, review_text=review_text)
        )
        self.assertTrue(any("D-002" in e and "not listed" in e for e in result.errors))

    def test_open_product_decision_blocks_ready_status(self):
        decisions = DECISIONS + OPEN_PRODUCT_DECISION_LINE
        spec_text = SPEC.replace("### Product\nNone", "### Product\n- D-002 — cart")
        result = module.validate(self.make_feature(spec_text=spec_text, decisions_text=decisions))
        self.assertTrue(any("says READY" in e for e in result.errors))

    def test_blocked_review_must_name_open_product_blocker(self):
        decisions = DECISIONS + OPEN_PRODUCT_DECISION_LINE
        spec_text = SPEC.replace("### Product\nNone", "### Product\n- D-002 — cart")
        review_text = REVIEW.replace("STATUS: READY", "STATUS: BLOCKED")
        result = module.validate(
            self.make_feature(
                spec_text=spec_text,
                decisions_text=decisions,
                review_text=review_text,
            )
        )
        self.assertTrue(any("Blockers does not list" in e and "D-002" in e for e in result.errors))

    def test_open_technical_decision_does_not_block_ready(self):
        decisions = DECISIONS + OPEN_TECHNICAL_DECISION_LINE
        result = module.validate(self.make_feature(decisions_text=decisions))
        self.assertEqual([], result.errors)
        self.assertEqual(["D-002"], result.open_technical_decisions)


if __name__ == "__main__":
    unittest.main()
