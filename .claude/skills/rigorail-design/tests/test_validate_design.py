from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "validate_design.py"
spec = importlib.util.spec_from_file_location("rigorail_design_validator", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)


REVIEW = """# Technical Design Review

STATUS: READY

## PRODUCT_CONTRADICTIONS

None.

## PRODUCT_INVENTIONS

None.

## PRODUCT_BLOCKERS

None.

## UNRESOLVED_TECHNICAL_DECISIONS

None.

## UNVERIFIED_FRAMEWORK_FACTS

None.

## TECHNICAL_INTEGRITY_GAPS

None.

## RESOLVED_TECHNICAL_DECISIONS

None.
"""

DECISIONS = """# Decision Ledger

## Sources
- **S-001** [SOURCE_FACT] — source — authority

## Decisions
- **D-001** [NEW_HUMAN_DECISION] [risk:high] [status:decided] — topic — decision — evidence: user

## Decision History
"""

OPEN_TECHNICAL_DECISION_LINE = (
    "\n- **D-002** [OPEN_TECHNICAL_DECISION] [risk:medium] [status:open] — session storage\n"
)

FINDING_TEMPLATE = """- [{severity}] {identifier} — {summary}
  - Evidence: {evidence}
  - Authoritative inputs: {inputs}
  - Required action: {action}
"""


def finding(
    identifier,
    severity="HIGH",
    summary="summary",
    evidence="plan.md line 12",
    inputs="not stated in spec.md or decisions.md",
    action="human product decision required",
):
    return FINDING_TEMPLATE.format(
        severity=severity,
        identifier=identifier,
        summary=summary,
        evidence=evidence,
        inputs=inputs,
        action=action,
    )


def with_section(review, section, body):
    marker = f"## {section}\n\nNone.\n"
    assert marker in review
    return review.replace(marker, f"## {section}\n\n{body}\n")


class ValidatorTests(unittest.TestCase):
    def make_design(self, review_text=REVIEW, decisions_text=DECISIONS, write_review=True):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        if write_review:
            (root / "design-review.md").write_text(review_text, encoding="utf-8")
        (root / "decisions.md").write_text(decisions_text, encoding="utf-8")
        self.addCleanup(tmp.cleanup)
        return root

    def test_valid_ready_review_passes(self):
        design_dir = self.make_design()
        result = module.validate(design_dir)
        self.assertEqual([], result.errors)
        self.assertEqual("READY", result.status)
        self.assertTrue(result.ready)
        self.assertEqual(0, module.main([str(design_dir)]))

    def test_product_blocker_with_ready_fails(self):
        review = with_section(REVIEW, "PRODUCT_BLOCKERS", finding("B-001"))
        design_dir = self.make_design(review_text=review)
        result = module.validate(design_dir)
        self.assertTrue(any("PRODUCT_BLOCKERS:B-001" in e for e in result.errors))
        self.assertTrue(any("NEEDS_PRODUCT_DECISION" in e for e in result.errors))
        self.assertEqual(1, module.main([str(design_dir)]))

    def test_product_invention_with_ready_fails(self):
        review = with_section(REVIEW, "PRODUCT_INVENTIONS", finding("I-001"))
        result = module.validate(self.make_design(review_text=review))
        self.assertTrue(any("PRODUCT_INVENTIONS:I-001" in e for e in result.errors))

    def test_product_invention_routes_to_the_planner_not_the_human(self):
        review = with_section(REVIEW, "PRODUCT_INVENTIONS", finding("I-001")).replace(
            "STATUS: READY", "STATUS: NEEDS_TECHNICAL_WORK"
        )
        result = module.validate(self.make_design(review_text=review))
        self.assertEqual([], result.errors)
        self.assertEqual("NEEDS_TECHNICAL_WORK", result.status)
        self.assertFalse(result.ready)

    def test_product_contradiction_with_ready_fails(self):
        review = with_section(REVIEW, "PRODUCT_CONTRADICTIONS", finding("C-001"))
        result = module.validate(self.make_design(review_text=review))
        self.assertTrue(any("PRODUCT_CONTRADICTIONS:C-001" in e for e in result.errors))

    def test_product_contradiction_routes_to_the_planner_not_the_human(self):
        review = with_section(REVIEW, "PRODUCT_CONTRADICTIONS", finding("C-001")).replace(
            "STATUS: READY", "STATUS: NEEDS_TECHNICAL_WORK"
        )
        result = module.validate(self.make_design(review_text=review))
        self.assertEqual([], result.errors)
        self.assertEqual("NEEDS_TECHNICAL_WORK", result.status)

    def test_product_blocker_still_requires_the_human_status(self):
        review = with_section(REVIEW, "PRODUCT_BLOCKERS", finding("B-001")).replace(
            "STATUS: READY", "STATUS: NEEDS_TECHNICAL_WORK"
        )
        result = module.validate(self.make_design(review_text=review))
        self.assertTrue(any("expected STATUS: NEEDS_PRODUCT_DECISION" in e for e in result.errors))

    def test_blocker_outranks_contradiction_in_status_derivation(self):
        review = with_section(REVIEW, "PRODUCT_CONTRADICTIONS", finding("C-001"))
        review = with_section(review, "PRODUCT_BLOCKERS", finding("B-001")).replace(
            "STATUS: READY", "STATUS: NEEDS_PRODUCT_DECISION"
        )
        result = module.validate(self.make_design(review_text=review))
        self.assertEqual([], result.errors)
        self.assertEqual("NEEDS_PRODUCT_DECISION", result.status)

    def test_unresolved_technical_decision_with_ready_fails(self):
        review = with_section(REVIEW, "UNRESOLVED_TECHNICAL_DECISIONS", finding("D-002"))
        result = module.validate(
            self.make_design(
                review_text=review,
                decisions_text=DECISIONS + OPEN_TECHNICAL_DECISION_LINE,
            )
        )
        self.assertTrue(any("UNRESOLVED_TECHNICAL_DECISIONS:D-002" in e for e in result.errors))
        self.assertTrue(any("NEEDS_TECHNICAL_WORK" in e for e in result.errors))

    def test_high_technical_integrity_gap_with_ready_fails(self):
        review = with_section(REVIEW, "TECHNICAL_INTEGRITY_GAPS", finding("T-001", severity="HIGH"))
        result = module.validate(self.make_design(review_text=review))
        self.assertTrue(any("TECHNICAL_INTEGRITY_GAPS:T-001" in e for e in result.errors))

    def test_medium_technical_integrity_gap_does_not_block_ready(self):
        review = with_section(
            REVIEW, "TECHNICAL_INTEGRITY_GAPS", finding("T-002", severity="MEDIUM")
        )
        result = module.validate(self.make_design(review_text=review))
        self.assertEqual([], result.errors)
        self.assertTrue(result.ready)

    def test_medium_framework_fact_may_coexist_with_ready(self):
        review = with_section(
            REVIEW,
            "UNVERIFIED_FRAMEWORK_FACTS",
            finding(
                "F-001",
                severity="MEDIUM",
                summary="assumes the framework enforces the constraint",
                action="verify before implementation",
            ),
        )
        design_dir = self.make_design(review_text=review)
        result = module.validate(design_dir)
        self.assertEqual([], result.errors)
        self.assertTrue(result.ready)
        self.assertEqual(0, module.main([str(design_dir)]))

    def test_needs_product_decision_without_blocker_fails(self):
        review = REVIEW.replace("STATUS: READY", "STATUS: NEEDS_PRODUCT_DECISION")
        design_dir = self.make_design(review_text=review)
        result = module.validate(design_dir)
        self.assertTrue(
            any(
                "STATUS: NEEDS_PRODUCT_DECISION is not allowed when no blocking finding remains"
                in e
                and "expected STATUS: READY" in e
                for e in result.errors
            )
        )
        self.assertEqual(1, module.main([str(design_dir)]))

    def test_needs_technical_work_without_blocking_finding_fails(self):
        review = REVIEW.replace("STATUS: READY", "STATUS: NEEDS_TECHNICAL_WORK")
        design_dir = self.make_design(review_text=review)
        result = module.validate(design_dir)
        self.assertTrue(
            any(
                "STATUS: NEEDS_TECHNICAL_WORK is not allowed when no blocking finding remains" in e
                and "expected STATUS: READY" in e
                for e in result.errors
            )
        )
        self.assertEqual(1, module.main([str(design_dir)]))

    def test_ready_is_required_when_nothing_blocks(self):
        design_dir = self.make_design()
        result = module.validate(design_dir)
        self.assertEqual([], result.errors)
        self.assertEqual("READY", result.status)
        self.assertEqual(0, module.main([str(design_dir)]))

    def test_finding_without_required_fields_fails(self):
        review = with_section(
            REVIEW, "UNVERIFIED_FRAMEWORK_FACTS", "- [MEDIUM] F-001 — no supporting fields"
        )
        result = module.validate(self.make_design(review_text=review))
        self.assertTrue(any("missing a 'Evidence:' field" in e for e in result.errors))
        self.assertTrue(any("missing a 'Required action:' field" in e for e in result.errors))

    def test_wrapped_field_continuation_is_accepted(self):
        wrapped = (
            "- [MEDIUM] F-001 — plan assumes the framework enforces uniqueness\n"
            '  - Evidence: data-model.md, "link table" section\n'
            "  - Authoritative inputs: spec.md SC-004 requires the invariant; no source proves\n"
            "    the framework enforces it\n"
            "  - Classification: INFERENCE\n"
            "  - Required action: verify before implementation; add an explicit constraint if\n"
            "    the framework does not enforce it"
        )
        review = with_section(REVIEW, "UNVERIFIED_FRAMEWORK_FACTS", wrapped)
        design_dir = self.make_design(review_text=review)
        result = module.validate(design_dir)
        self.assertEqual([], result.errors)
        self.assertTrue(result.ready)
        self.assertEqual(
            "spec.md SC-004 requires the invariant; no source proves the framework enforces it",
            result.findings[0].fields["authoritative inputs"],
        )
        self.assertEqual(0, module.main([str(design_dir)]))

    def test_indented_line_without_a_preceding_field_fails(self):
        stray = (
            "- [MEDIUM] F-001 — summary\n"
            "    stray continuation with no field\n"
            "  - Evidence: plan.md\n"
            "  - Required action: verify"
        )
        review = with_section(REVIEW, "UNVERIFIED_FRAMEWORK_FACTS", stray)
        result = module.validate(self.make_design(review_text=review))
        self.assertTrue(
            any(
                "unparseable line" in e and "stray continuation with no field" in e
                for e in result.errors
            )
        )

    def test_malformed_status_fails(self):
        review = REVIEW.replace("STATUS: READY", "STATUS: MOSTLY_READY")
        design_dir = self.make_design(review_text=review)
        result = module.validate(design_dir)
        self.assertTrue(any("unrecognized STATUS" in e for e in result.errors))
        self.assertIsNone(result.status)
        self.assertEqual(1, module.main([str(design_dir)]))

    def test_missing_status_fails(self):
        review = REVIEW.replace("STATUS: READY\n", "")
        result = module.validate(self.make_design(review_text=review))
        self.assertTrue(any("exactly one STATUS line" in e for e in result.errors))

    def test_missing_review_fails(self):
        design_dir = self.make_design(write_review=False)
        result = module.validate(design_dir)
        self.assertTrue(any("missing required artifact" in e for e in result.errors))
        self.assertEqual(1, module.main([str(design_dir)]))

    def test_missing_section_fails(self):
        review = REVIEW.replace("## PRODUCT_INVENTIONS\n\nNone.\n", "")
        result = module.validate(self.make_design(review_text=review))
        self.assertTrue(any("missing section: ## PRODUCT_INVENTIONS" in e for e in result.errors))

    def test_empty_section_fails(self):
        review = REVIEW.replace("## PRODUCT_BLOCKERS\n\nNone.\n", "## PRODUCT_BLOCKERS\n\n")
        result = module.validate(self.make_design(review_text=review))
        self.assertTrue(
            any("at least one finding or the single word None" in e for e in result.errors)
        )

    def test_missing_decisions_fails(self):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        (root / "design-review.md").write_text(REVIEW, encoding="utf-8")
        self.addCleanup(tmp.cleanup)
        result = module.validate(root)
        self.assertTrue(any("decisions.md" in e and "missing" in e for e in result.errors))

    def test_unaccounted_open_technical_decision_fails(self):
        result = module.validate(
            self.make_design(decisions_text=DECISIONS + OPEN_TECHNICAL_DECISION_LINE)
        )
        self.assertTrue(any("D-002" in e and "accounted for neither" in e for e in result.errors))

    def test_open_technical_decision_accounted_as_resolved_passes(self):
        review = with_section(
            REVIEW,
            "RESOLVED_TECHNICAL_DECISIONS",
            "- D-002 — resolved in plan.md > Technical Decisions",
        )
        design_dir = self.make_design(
            review_text=review, decisions_text=DECISIONS + OPEN_TECHNICAL_DECISION_LINE
        )
        result = module.validate(design_dir)
        self.assertEqual([], result.errors)
        self.assertEqual(["D-002"], result.resolved_technical_decisions)
        self.assertEqual(0, module.main([str(design_dir)]))

    def test_open_technical_decision_accounted_as_unresolved_is_valid_but_not_ready(self):
        review = with_section(
            REVIEW, "UNRESOLVED_TECHNICAL_DECISIONS", finding("D-002", action="planner must decide")
        ).replace("STATUS: READY", "STATUS: NEEDS_TECHNICAL_WORK")
        design_dir = self.make_design(
            review_text=review, decisions_text=DECISIONS + OPEN_TECHNICAL_DECISION_LINE
        )
        result = module.validate(design_dir)
        self.assertEqual([], result.errors)
        self.assertEqual("NEEDS_TECHNICAL_WORK", result.status)
        self.assertFalse(result.ready)
        self.assertEqual(2, module.main([str(design_dir)]))

    def test_decision_listed_as_both_resolved_and_unresolved_fails(self):
        review = with_section(REVIEW, "UNRESOLVED_TECHNICAL_DECISIONS", finding("D-002")).replace(
            "STATUS: READY", "STATUS: NEEDS_TECHNICAL_WORK"
        )
        review = with_section(review, "RESOLVED_TECHNICAL_DECISIONS", "- D-002 — resolved")
        result = module.validate(
            self.make_design(
                review_text=review, decisions_text=DECISIONS + OPEN_TECHNICAL_DECISION_LINE
            )
        )
        self.assertTrue(any("both as resolved" in e for e in result.errors))

    def test_duplicate_resolved_decision_fails(self):
        review = with_section(
            REVIEW,
            "RESOLVED_TECHNICAL_DECISIONS",
            "- D-002 — resolved in plan.md\n- D-002 — resolved in data-model.md",
        )
        result = module.validate(
            self.make_design(
                review_text=review, decisions_text=DECISIONS + OPEN_TECHNICAL_DECISION_LINE
            )
        )
        self.assertTrue(
            any(
                "RESOLVED_TECHNICAL_DECISIONS lists D-002 more than once" in e
                for e in result.errors
            )
        )

    def test_duplicate_unresolved_decision_fails(self):
        review = with_section(
            REVIEW,
            "UNRESOLVED_TECHNICAL_DECISIONS",
            finding("D-002") + finding("D-002", summary="again"),
        ).replace("STATUS: READY", "STATUS: NEEDS_TECHNICAL_WORK")
        result = module.validate(
            self.make_design(
                review_text=review, decisions_text=DECISIONS + OPEN_TECHNICAL_DECISION_LINE
            )
        )
        self.assertTrue(
            any(
                "UNRESOLVED_TECHNICAL_DECISIONS lists D-002 more than once" in e
                for e in result.errors
            )
        )

    def test_resolved_decision_not_declared_open_fails(self):
        review = with_section(
            REVIEW, "RESOLVED_TECHNICAL_DECISIONS", "- D-009 — resolved in plan.md"
        )
        result = module.validate(self.make_design(review_text=review))
        self.assertTrue(any("D-009" in e and "does not declare" in e for e in result.errors))

    def test_route_is_freeze_when_nothing_blocks(self):
        result = module.validate(self.make_design())
        self.assertEqual(module.ROUTE_FREEZE, module.route(result))

    def test_product_blocker_routes_to_the_human(self):
        review = with_section(REVIEW, "PRODUCT_BLOCKERS", finding("B-001")).replace(
            "STATUS: READY", "STATUS: NEEDS_PRODUCT_DECISION"
        )
        result = module.validate(self.make_design(review_text=review))
        self.assertEqual([], result.errors)
        self.assertEqual(module.ROUTE_HUMAN, module.route(result))

    def test_product_blocker_reaches_the_human_regardless_of_iteration(self):
        review = with_section(REVIEW, "PRODUCT_BLOCKERS", finding("B-001")).replace(
            "STATUS: READY", "STATUS: NEEDS_PRODUCT_DECISION"
        )
        result = module.validate(self.make_design(review_text=review))
        for iteration in range(module.MAX_REPAIR_ITERATIONS + 2):
            self.assertEqual(module.ROUTE_HUMAN, module.route(result, iteration=iteration))

    def test_planner_owned_findings_route_back_to_planning(self):
        for section, identifier in (
            ("PRODUCT_CONTRADICTIONS", "C-001"),
            ("PRODUCT_INVENTIONS", "I-001"),
            ("TECHNICAL_INTEGRITY_GAPS", "T-001"),
        ):
            with self.subTest(section=section):
                review = with_section(REVIEW, section, finding(identifier)).replace(
                    "STATUS: READY", "STATUS: NEEDS_TECHNICAL_WORK"
                )
                result = module.validate(self.make_design(review_text=review))
                self.assertEqual([], result.errors)
                self.assertEqual(module.ROUTE_REPLAN, module.route(result))

    def test_unresolved_technical_decision_routes_back_to_planning(self):
        review = with_section(REVIEW, "UNRESOLVED_TECHNICAL_DECISIONS", finding("D-002")).replace(
            "STATUS: READY", "STATUS: NEEDS_TECHNICAL_WORK"
        )
        result = module.validate(
            self.make_design(
                review_text=review, decisions_text=DECISIONS + OPEN_TECHNICAL_DECISION_LINE
            )
        )
        self.assertEqual([], result.errors)
        self.assertEqual(module.ROUTE_REPLAN, module.route(result))

    def test_medium_integrity_gap_does_not_route_back_to_planning(self):
        review = with_section(
            REVIEW, "TECHNICAL_INTEGRITY_GAPS", finding("T-002", severity="MEDIUM")
        )
        result = module.validate(self.make_design(review_text=review))
        self.assertEqual(module.ROUTE_FREEZE, module.route(result))

    def test_repair_loop_is_bounded(self):
        review = with_section(REVIEW, "PRODUCT_INVENTIONS", finding("I-001")).replace(
            "STATUS: READY", "STATUS: NEEDS_TECHNICAL_WORK"
        )
        result = module.validate(self.make_design(review_text=review))
        limit = module.MAX_REPAIR_ITERATIONS
        self.assertEqual(module.ROUTE_REPLAN, module.route(result, iteration=limit - 1))
        self.assertEqual(module.ROUTE_REPAIR_LIMIT, module.route(result, iteration=limit))
        self.assertEqual(module.ROUTE_REPAIR_LIMIT, module.route(result, iteration=limit + 1))

    def test_repair_limit_can_never_freeze_or_exit_zero(self):
        review = with_section(REVIEW, "PRODUCT_INVENTIONS", finding("I-001")).replace(
            "STATUS: READY", "STATUS: NEEDS_TECHNICAL_WORK"
        )
        design_dir = self.make_design(review_text=review)
        result = module.validate(design_dir)
        self.assertNotEqual(
            module.ROUTE_FREEZE, module.route(result, iteration=module.MAX_REPAIR_ITERATIONS)
        )
        self.assertEqual(
            2, module.main([str(design_dir), "--iteration", str(module.MAX_REPAIR_ITERATIONS)])
        )

    def test_iteration_argument_does_not_change_exit_codes(self):
        design_dir = self.make_design()
        self.assertEqual(0, module.main([str(design_dir), "--iteration", "9"]))

    def test_malformed_artifacts_route_to_invalid(self):
        review = REVIEW.replace("STATUS: READY", "STATUS: MOSTLY_READY")
        result = module.validate(self.make_design(review_text=review))
        self.assertEqual(module.ROUTE_INVALID, module.route(result))

    def test_open_product_decision_blocks_design(self):
        decisions = DECISIONS + (
            "\n- **D-003** [OPEN_PRODUCT_DECISION] [risk:high] [status:open] — refunds\n"
        )
        result = module.validate(self.make_design(decisions_text=decisions))
        self.assertTrue(any("D-003" in e and "not approved" in e for e in result.errors))


if __name__ == "__main__":
    unittest.main()
