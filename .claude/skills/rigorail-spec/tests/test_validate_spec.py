from __future__ import annotations

import contextlib
import importlib.util
import io
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


SOURCE = """# Authoritative Product Source

## S-001 — product draft pasted by the human

> A user can create a note. A user can delete a note. Customer data stays in
> the European Union.
"""

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
## §1 Notes
- **§1.1** — A user can create a note. <!-- provenance: S-001 -->
- **§1.2** — A user can delete a note. <!-- provenance: D-001 -->
## §C Constraints
- **§C1** — Customer data is hosted within the European Union. <!-- provenance: S-001 -->
## Acceptance Examples
x
## Key Entities
x
## Open Decisions
### Product
None
### Technical
None
"""

DECISIONS = """# Decision Ledger

## Sources
- **S-001** — source.md block S-001 — verbatim product input

## Decisions
- **D-001** [2026-09-02] [PRODUCT] [HUMAN] [status:decided] [risk:high] — §1.2 — \
Deletion is permanent in V1 — Keep V1 simple — reversible:Y

## Decision History
"""

REVIEW = """# Discovery Review

STATUS: READY
GATE: APPROVED

## Blockers
None
## Unsupported Firm Rules
None
## High-impact Ambiguities
None
## Unresolved Assumptions
None identified.
## Consistency Findings
None
## Open Product Decisions
None
## Open Technical Decisions
None
## Human Semantic Gate
Reviewed and approved by the human on 2026-09-02.
## Deterministic Validation
PASS
"""

OPEN_PRODUCT_LINE = (
    "\n- **D-002** [2026-09-02] [PRODUCT] [HUMAN] [status:open] [risk:high] — cart — "
    "one cart per user or many — deferred by the human — reversible:Y\n"
)
OPEN_TECHNICAL_LINE = (
    "\n- **D-002** [2026-09-02] [TECHNICAL] [HUMAN] [status:open] [risk:medium] — auth — "
    "session mechanism deferred — not product visible — reversible:Y\n"
)


def errors_matching(result, *needles):
    return [e for e in result.errors if all(n in e for n in needles)]


class ValidatorTestCase(unittest.TestCase):
    def make_feature(
        self,
        spec_text=SPEC,
        decisions_text=DECISIONS,
        review_text=REVIEW,
        source_text=SOURCE,
        omit=(),
    ):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        artifacts = {
            "source.md": source_text,
            "product-spec.md": spec_text,
            "decisions.md": decisions_text,
            "discovery-review.md": review_text,
        }
        for name, text in artifacts.items():
            if name not in omit:
                (root / name).write_text(text, encoding="utf-8")
        self.addCleanup(tmp.cleanup)
        return root


class ContractTests(ValidatorTestCase):
    def test_valid_contract(self):
        result = module.validate(self.make_feature())
        self.assertEqual([], result.errors)
        self.assertEqual([], result.warnings)
        self.assertEqual(3, result.statement_count)
        self.assertEqual(["1.1", "1.2"], result.behavior_ids)
        self.assertEqual(["C1"], result.constraint_ids)
        self.assertEqual("READY", result.status)
        self.assertEqual("APPROVED", result.gate)

    def test_missing_required_artifact_fails(self):
        result = module.validate(self.make_feature(omit=("discovery-review.md",)))
        self.assertTrue(errors_matching(result, "missing required artifact", "discovery-review.md"))

    def test_missing_spec_section_fails(self):
        text = SPEC.replace("## Key Entities", "## Entities")
        result = module.validate(self.make_feature(spec_text=text))
        self.assertTrue(errors_matching(result, "missing section", "Key Entities"))

    def test_missing_review_section_fails(self):
        text = REVIEW.replace("## Consistency Findings", "## Consistency")
        result = module.validate(self.make_feature(review_text=text))
        self.assertTrue(errors_matching(result, "missing section", "Consistency Findings"))

    def test_spec_without_behavior_section_fails(self):
        text = SPEC.replace("## §1 Notes", "## Behaviors")
        result = module.validate(self.make_feature(spec_text=text))
        self.assertTrue(errors_matching(result, "no behavior section"))


class ProductIdTests(ValidatorTestCase):
    def test_multi_digit_behavior_id_is_valid(self):
        text = SPEC.replace(
            "## §1 Notes\n- **§1.1** — A user can create a note. <!-- provenance: S-001 -->",
            "## §12 Notes\n- **§12.4** — A user can create a note. <!-- provenance: S-001 -->",
        ).replace("- **§1.2** — A user can delete a note. <!-- provenance: D-001 -->", "")
        decisions = DECISIONS.replace("§1.2", "§12.4")
        result = module.validate(self.make_feature(spec_text=text, decisions_text=decisions))
        self.assertEqual([], result.errors)
        self.assertEqual(["12.4"], result.behavior_ids)

    def test_multi_digit_constraint_id_is_valid(self):
        text = SPEC.replace("**§C1**", "**§C20**")
        result = module.validate(self.make_feature(spec_text=text))
        self.assertEqual([], result.errors)
        self.assertEqual(["C20"], result.constraint_ids)

    def test_malformed_ids_are_rejected(self):
        for bad in ("1", "1.1.1", "c1", "C", "C1a", "1.a"):
            with self.subTest(bad=bad):
                text = SPEC.replace(
                    "- **§1.1** — A user can create a note. <!-- provenance: S-001 -->",
                    f"- **§{bad}** — A user can create a note. <!-- provenance: S-001 -->",
                )
                result = module.validate(self.make_feature(spec_text=text))
                self.assertTrue(
                    errors_matching(result, "malformed product statement id", f"§{bad}"),
                    result.errors,
                )

    def test_duplicate_behavior_id_fails(self):
        text = SPEC.replace(
            "- **§1.2** — A user can delete a note. <!-- provenance: D-001 -->",
            "- **§1.1** — A user can delete a note. <!-- provenance: D-001 -->",
        )
        result = module.validate(self.make_feature(spec_text=text))
        self.assertTrue(errors_matching(result, "duplicate product statement id", "§1.1"))

    def test_duplicate_constraint_id_fails(self):
        text = SPEC.replace(
            "## Acceptance Examples",
            "- **§C1** — Data export is provided in CSV format. <!-- provenance: S-001 -->\n"
            "## Acceptance Examples",
        )
        result = module.validate(self.make_feature(spec_text=text))
        self.assertTrue(errors_matching(result, "duplicate product statement id", "§C1"))

    def test_duplicate_behavior_section_number_fails(self):
        text = SPEC.replace("## §C Constraints", "## §1 More notes\n## §C Constraints")
        result = module.validate(self.make_feature(spec_text=text))
        self.assertTrue(errors_matching(result, "duplicate behavior section number", "§1"))

    def test_canonical_behavior_and_constraint_statements_parse(self):
        result = module.validate(self.make_feature())
        self.assertEqual([], result.errors)
        self.assertEqual(["1.1", "1.2"], result.behavior_ids)
        self.assertEqual(["C1"], result.constraint_ids)

    def test_non_canonical_statement_lines_are_rejected_not_ignored(self):
        cases = {
            "bare": "§1.2 — A user can delete a note.",
            "unbolded list item": "- §1.2 — A user can delete a note.",
            "colon separator": "- **§1.2**: A user can delete a note.",
            "missing separator": "- **§1.2** A user can delete a note.",
            "hyphen separator": "- **§1.2** - A user can delete a note.",
            "empty body": "- **§1.2** —",
            "indented bare": "  - §1.2 — A user can delete a note.",
        }
        for label, line in cases.items():
            with self.subTest(case=label):
                text = SPEC.replace(
                    "- **§1.2** — A user can delete a note. <!-- provenance: D-001 -->",
                    line,
                )
                result = module.validate(self.make_feature(spec_text=text))
                self.assertTrue(
                    errors_matching(result, "canonical form"),
                    f"{label} produced no canonical-form error: {result.errors}",
                )

    def test_statement_body_holding_only_provenance_fails(self):
        text = SPEC.replace(
            "- **§1.2** — A user can delete a note. <!-- provenance: D-001 -->",
            "- **§1.2** — <!-- provenance: D-001 -->",
        )
        result = module.validate(self.make_feature(spec_text=text))
        self.assertTrue(errors_matching(result, "§1.2", "empty statement body"))

    def test_prose_mentioning_a_statement_is_not_flagged(self):
        text = SPEC.replace("## Goal\nx", "## Goal\nThe contract starts at §1.1 and grows.")
        result = module.validate(self.make_feature(spec_text=text))
        self.assertEqual([], result.errors)

    def test_behavior_id_must_match_its_section(self):
        text = SPEC.replace(
            "- **§1.2** — A user can delete a note. <!-- provenance: D-001 -->",
            "- **§2.1** — A user can delete a note. <!-- provenance: D-001 -->",
        ).replace("§1.2", "§2.1")
        result = module.validate(self.make_feature(spec_text=text))
        self.assertTrue(errors_matching(result, "§2.1", "does not belong to behavior section"))

    def test_constraint_id_in_behavior_section_fails(self):
        text = SPEC.replace(
            "- **§1.2** — A user can delete a note. <!-- provenance: D-001 -->",
            "- **§C9** — A user can delete a note. <!-- provenance: D-001 -->",
        ).replace("— §1.2 —", "— §C9 —")
        result = module.validate(self.make_feature(spec_text=text))
        self.assertTrue(errors_matching(result, "§C9", "behavior section"))

    def test_statement_outside_a_statement_section_fails(self):
        text = SPEC.replace(
            "## Key Entities\nx",
            "## Key Entities\n- **§3.1** — A user can share a note. <!-- provenance: S-001 -->",
        )
        result = module.validate(self.make_feature(spec_text=text))
        self.assertTrue(errors_matching(result, "§3.1", "neither a behavior section"))


class AtomicityTests(ValidatorTestCase):
    def test_multi_obligation_statement_warns(self):
        text = SPEC.replace(
            "- **§1.1** — A user can create a note. <!-- provenance: S-001 -->",
            "- **§1.1** — A user can create, edit, delete, and share a note. "
            "<!-- provenance: S-001 -->",
        )
        result = module.validate(self.make_feature(spec_text=text))
        self.assertEqual([], result.errors)
        warnings = [w for w in result.warnings if "§1.1" in w]
        self.assertEqual(1, len(warnings))
        self.assertIn("may describe more than one product obligation", warnings[0])

    def test_atomicity_warning_does_not_claim_proof(self):
        text = SPEC.replace(
            "- **§1.1** — A user can create a note. <!-- provenance: S-001 -->",
            "- **§1.1** — A user can create, edit, delete, and share a note. "
            "<!-- provenance: S-001 -->",
        )
        result = module.validate(self.make_feature(spec_text=text))
        warning = next(w for w in result.warnings if "§1.1" in w)
        self.assertIn("atomicity is semantic and is not verified by this check", warning)

    def test_coherent_statement_is_not_flagged(self):
        text = SPEC.replace(
            "- **§1.1** — A user can create a note. <!-- provenance: S-001 -->",
            "- **§1.1** — A user can create a note with a title and body. "
            "<!-- provenance: S-001 -->",
        )
        result = module.validate(self.make_feature(spec_text=text))
        self.assertEqual([], result.errors)
        self.assertEqual([], result.warnings)


class SourceArtifactTests(ValidatorTestCase):
    def test_missing_source_fails(self):
        result = module.validate(self.make_feature(omit=("source.md",)))
        self.assertTrue(errors_matching(result, "missing required artifact", "source.md"))

    def test_empty_source_fails(self):
        result = module.validate(self.make_feature(source_text="   \n"))
        self.assertTrue(errors_matching(result, "source.md is empty"))

    def test_source_content_is_not_parsed_as_ledger_or_spec(self):
        source = SOURCE + (
            "\n- **S-999** — invented source — invented authority\n"
            "- **D-999** [2026-09-02] [PRODUCT] [HUMAN] [status:decided] — x — y — z — "
            "reversible:Y\n"
            "- **§9.9** — An invented obligation. <!-- provenance: S-999 -->\n"
        )
        text = SPEC.replace("provenance: S-001 -->", "provenance: S-999 -->")
        result = module.validate(self.make_feature(spec_text=text, source_text=source))
        self.assertTrue(errors_matching(result, "unknown source S-999"))
        self.assertNotIn("9.9", result.behavior_ids)


class DecisionLedgerTests(ValidatorTestCase):
    def test_unknown_layer_fails(self):
        decisions = DECISIONS.replace("[PRODUCT] [HUMAN]", "[BUSINESS] [HUMAN]")
        result = module.validate(self.make_feature(decisions_text=decisions))
        self.assertTrue(errors_matching(result, "D-001", "unknown layer: BUSINESS"))

    def test_unknown_provenance_fails(self):
        decisions = DECISIONS.replace("[PRODUCT] [HUMAN]", "[PRODUCT] [GUESSED]")
        result = module.validate(self.make_feature(decisions_text=decisions))
        self.assertTrue(errors_matching(result, "D-001", "unknown provenance: GUESSED"))

    def test_layer_and_provenance_axes_are_not_interchangeable(self):
        decisions = DECISIONS.replace("[PRODUCT] [HUMAN]", "[HUMAN] [PRODUCT]")
        result = module.validate(self.make_feature(decisions_text=decisions))
        self.assertTrue(errors_matching(result, "unknown layer: HUMAN"))
        self.assertTrue(errors_matching(result, "unknown provenance: PRODUCT"))

    def test_unknown_status_fails(self):
        decisions = DECISIONS.replace("[status:decided]", "[status:maybe]")
        result = module.validate(self.make_feature(decisions_text=decisions))
        self.assertTrue(errors_matching(result, "unknown status: maybe"))

    def test_inference_cannot_be_marked_decided(self):
        decisions = DECISIONS.replace("[HUMAN] [status:decided]", "[INFERRED] [status:decided]")
        result = module.validate(self.make_feature(decisions_text=decisions))
        self.assertTrue(errors_matching(result, "D-001", "INFERRED with status:decided"))

    def test_inference_cannot_ground_firm_statement(self):
        decisions = DECISIONS.replace("[HUMAN] [status:decided]", "[INFERRED] [status:unconfirmed]")
        result = module.validate(self.make_feature(decisions_text=decisions))
        self.assertTrue(errors_matching(result, "§1.2", "status:unconfirmed"))

    def test_technical_decision_cannot_ground_firm_statement(self):
        decisions = DECISIONS.replace("[PRODUCT] [HUMAN]", "[TECHNICAL] [HUMAN]")
        result = module.validate(self.make_feature(decisions_text=decisions))
        self.assertTrue(errors_matching(result, "§1.2", "is a TECHNICAL decision"))

    def test_open_decision_cannot_ground_firm_statement(self):
        decisions = DECISIONS.replace("[status:decided]", "[status:open]")
        result = module.validate(self.make_feature(decisions_text=decisions))
        self.assertTrue(errors_matching(result, "§1.2", "status:open"))

    def test_source_provenance_must_cite_a_source(self):
        decisions = DECISIONS.replace("[PRODUCT] [HUMAN]", "[PRODUCT] [SOURCE]")
        result = module.validate(self.make_feature(decisions_text=decisions))
        self.assertTrue(errors_matching(result, "D-001", "cites no S-### source"))

    def test_source_provenance_with_citation_grounds_firm_statement(self):
        decisions = DECISIONS.replace("[PRODUCT] [HUMAN]", "[PRODUCT] [SOURCE]").replace(
            "Keep V1 simple", "Stated in S-001"
        )
        result = module.validate(self.make_feature(decisions_text=decisions))
        self.assertEqual([], result.errors)

    def test_source_provenance_citing_unknown_source_fails(self):
        decisions = DECISIONS.replace("[PRODUCT] [HUMAN]", "[PRODUCT] [SOURCE]").replace(
            "Keep V1 simple", "Stated in S-999"
        )
        result = module.validate(self.make_feature(decisions_text=decisions))
        self.assertTrue(
            errors_matching(result, "D-001", "references unknown source S-999"), result.errors
        )

    def test_source_provenance_citing_several_sources_requires_all_to_exist(self):
        declared = DECISIONS.replace(
            "- **S-001** — source.md block S-001 — verbatim product input",
            "- **S-001** — source.md block S-001 — verbatim product input\n"
            "- **S-002** — source.md block S-002 — follow-up message",
        )
        both = declared.replace("[PRODUCT] [HUMAN]", "[PRODUCT] [SOURCE]").replace(
            "Keep V1 simple", "Stated in S-001, S-002"
        )
        self.assertEqual([], module.validate(self.make_feature(decisions_text=both)).errors)

        one_missing = declared.replace("[PRODUCT] [HUMAN]", "[PRODUCT] [SOURCE]").replace(
            "Keep V1 simple", "Stated in S-001, S-003"
        )
        result = module.validate(self.make_feature(decisions_text=one_missing))
        self.assertTrue(errors_matching(result, "unknown source S-003"))
        self.assertFalse(errors_matching(result, "unknown source S-001"))

    def test_source_declared_only_in_source_md_does_not_ground_a_decision(self):
        source = SOURCE + "\n- **S-042** — invented — invented authority\n"
        decisions = DECISIONS.replace("[PRODUCT] [HUMAN]", "[PRODUCT] [SOURCE]").replace(
            "Keep V1 simple", "Stated in S-042"
        )
        result = module.validate(self.make_feature(decisions_text=decisions, source_text=source))
        self.assertTrue(errors_matching(result, "references unknown source S-042"))

    def test_malformed_decision_line_is_rejected_not_ignored(self):
        decisions = DECISIONS.replace("[2026-09-02] ", "")
        result = module.validate(self.make_feature(decisions_text=decisions))
        self.assertTrue(errors_matching(result, "malformed decision entry"))

    def test_malformed_source_line_is_rejected_not_ignored(self):
        decisions = DECISIONS.replace("- **S-001** — source.md", "- **S-001** source.md")
        result = module.validate(self.make_feature(decisions_text=decisions))
        self.assertTrue(errors_matching(result, "malformed source entry"))

    def test_duplicate_decision_id_fails(self):
        decisions = DECISIONS + (
            "- **D-001** [2026-09-02] [PRODUCT] [HUMAN] [status:decided] [risk:low] — "
            "cart — other — other — reversible:Y\n"
        )
        result = module.validate(self.make_feature(decisions_text=decisions))
        self.assertTrue(errors_matching(result, "duplicate decision id", "D-001"))


class ProvenanceTests(ValidatorTestCase):
    def test_missing_provenance_fails(self):
        text = SPEC.replace(" <!-- provenance: S-001 -->", "", 1)
        result = module.validate(self.make_feature(spec_text=text))
        self.assertTrue(errors_matching(result, "§1.1", "provenance marker"))

    def test_unknown_source_reference_fails(self):
        text = SPEC.replace("provenance: S-001 -->", "provenance: S-777 -->", 1)
        result = module.validate(self.make_feature(spec_text=text))
        self.assertTrue(errors_matching(result, "§1.1", "unknown source S-777"))

    def test_unknown_decision_reference_fails(self):
        text = SPEC.replace("provenance: D-001 -->", "provenance: D-777 -->")
        result = module.validate(self.make_feature(spec_text=text))
        self.assertTrue(errors_matching(result, "§1.2", "unknown decision D-777"))


class ReferenceTests(ValidatorTestCase):
    def test_decision_referencing_unknown_statement_fails(self):
        decisions = DECISIONS.replace("— §1.2 —", "— §4.9 —")
        result = module.validate(self.make_feature(decisions_text=decisions))
        self.assertTrue(errors_matching(result, "decisions.md", "unknown product statement §4.9"))

    def test_decision_referencing_constraint_passes(self):
        decisions = DECISIONS.replace("— §1.2 —", "— §C1 —")
        text = SPEC.replace("provenance: D-001 -->", "provenance: S-001 -->")
        result = module.validate(self.make_feature(spec_text=text, decisions_text=decisions))
        self.assertEqual([], result.errors)

    def test_malformed_reference_in_decisions_fails(self):
        decisions = DECISIONS.replace("— §1.2 —", "— §1 —")
        result = module.validate(self.make_feature(decisions_text=decisions))
        self.assertTrue(errors_matching(result, "decisions.md", "malformed product id reference"))

    def test_malformed_reference_in_review_fails(self):
        review = REVIEW.replace("## Consistency Findings\nNone", "## Consistency Findings\n- §C")
        result = module.validate(self.make_feature(review_text=review))
        self.assertTrue(
            errors_matching(result, "discovery-review.md", "malformed product id reference")
        )


class WithdrawalTests(ValidatorTestCase):
    def test_withdrawn_statement_needs_no_provenance_and_stays_referenceable(self):
        text = SPEC + "\n## Withdrawn\n- **§1.9** — withdrawn 2026-09-03 — see D-001\n"
        decisions = DECISIONS.replace("— §1.2 —", "— §1.2, §1.9 —")
        result = module.validate(self.make_feature(spec_text=text, decisions_text=decisions))
        self.assertEqual([], result.errors)
        self.assertEqual(["1.9"], result.withdrawn_ids)
        self.assertNotIn("1.9", result.behavior_ids)

    def test_withdrawn_id_cannot_be_reused(self):
        text = SPEC + "\n## Withdrawn\n- **§1.1** — withdrawn 2026-09-03 — see D-001\n"
        result = module.validate(self.make_feature(spec_text=text))
        self.assertTrue(errors_matching(result, "duplicate product statement id", "§1.1"))


class GateAndAssumptionTests(ValidatorTestCase):
    def test_ready_requires_approved_gate(self):
        review = REVIEW.replace("GATE: APPROVED", "GATE: PENDING")
        result = module.validate(self.make_feature(review_text=review))
        self.assertTrue(errors_matching(result, "READY but the human semantic gate is PENDING"))

    def test_exactly_one_status_and_gate_pass(self):
        result = module.validate(self.make_feature())
        self.assertEqual([], result.errors)
        self.assertEqual("READY", result.status)
        self.assertEqual("APPROVED", result.gate)

    def test_missing_status_line_fails(self):
        review = REVIEW.replace("STATUS: READY\n", "")
        result = module.validate(self.make_feature(review_text=review))
        self.assertTrue(errors_matching(result, "exactly one STATUS", "found 0"))

    def test_duplicate_status_lines_fail(self):
        review = REVIEW.replace(
            "## Deterministic Validation", "STATUS: BLOCKED\n\n## Deterministic Validation"
        )
        result = module.validate(self.make_feature(review_text=review))
        self.assertTrue(errors_matching(result, "exactly one STATUS", "found 2"))

    def test_missing_gate_line_fails(self):
        review = REVIEW.replace("GATE: APPROVED\n", "")
        result = module.validate(self.make_feature(review_text=review))
        self.assertTrue(errors_matching(result, "exactly one GATE", "found 0"))

    def test_duplicate_gate_lines_fail(self):
        review = REVIEW.replace(
            "## Deterministic Validation", "GATE: REJECTED\n\n## Deterministic Validation"
        )
        result = module.validate(self.make_feature(review_text=review))
        self.assertTrue(errors_matching(result, "exactly one GATE", "found 2"))

    def test_blocked_status_may_keep_a_pending_gate(self):
        review = REVIEW.replace("STATUS: READY", "STATUS: BLOCKED").replace(
            "GATE: APPROVED", "GATE: PENDING"
        )
        result = module.validate(self.make_feature(review_text=review))
        self.assertEqual([], result.errors)

    def test_empty_unresolved_assumptions_section_fails(self):
        review = REVIEW.replace(
            "## Unresolved Assumptions\nNone identified.", "## Unresolved Assumptions\n"
        )
        result = module.validate(self.make_feature(review_text=review))
        self.assertTrue(errors_matching(result, "Unresolved Assumptions must state the outcome"))

    def test_no_unresolved_assumptions_is_a_valid_explicit_state(self):
        result = module.validate(self.make_feature())
        self.assertEqual([], result.errors)


class OpenDecisionTests(ValidatorTestCase):
    def test_open_product_decision_listed_in_spec_passes_draft(self):
        decisions = DECISIONS + OPEN_PRODUCT_LINE
        spec_text = SPEC.replace("### Product\nNone", "### Product\n- D-002 — cart")
        review_text = (
            REVIEW.replace("STATUS: READY", "STATUS: BLOCKED")
            .replace("GATE: APPROVED", "GATE: PENDING")
            .replace("## Blockers\nNone", "## Blockers\n- D-002 — cart")
        )
        result = module.validate(
            self.make_feature(
                spec_text=spec_text, decisions_text=decisions, review_text=review_text
            )
        )
        self.assertEqual([], result.errors)
        self.assertEqual(["D-002"], result.open_product_decisions)

    def test_open_product_decision_missing_from_spec_fails(self):
        decisions = DECISIONS + OPEN_PRODUCT_LINE
        review_text = (
            REVIEW.replace("STATUS: READY", "STATUS: BLOCKED")
            .replace("GATE: APPROVED", "GATE: PENDING")
            .replace("## Blockers\nNone", "## Blockers\n- D-002 — cart")
        )
        result = module.validate(
            self.make_feature(decisions_text=decisions, review_text=review_text)
        )
        self.assertTrue(errors_matching(result, "D-002", "not listed"))

    def test_open_product_decision_blocks_ready_status(self):
        decisions = DECISIONS + OPEN_PRODUCT_LINE
        spec_text = SPEC.replace("### Product\nNone", "### Product\n- D-002 — cart")
        result = module.validate(self.make_feature(spec_text=spec_text, decisions_text=decisions))
        self.assertTrue(errors_matching(result, "says READY while open PRODUCT decisions"))

    def test_blocked_review_must_name_open_product_blocker(self):
        decisions = DECISIONS + OPEN_PRODUCT_LINE
        spec_text = SPEC.replace("### Product\nNone", "### Product\n- D-002 — cart")
        review_text = REVIEW.replace("STATUS: READY", "STATUS: BLOCKED").replace(
            "GATE: APPROVED", "GATE: PENDING"
        )
        result = module.validate(
            self.make_feature(
                spec_text=spec_text, decisions_text=decisions, review_text=review_text
            )
        )
        self.assertTrue(errors_matching(result, "Blockers does not list", "D-002"))

    def test_open_technical_decision_does_not_block_ready(self):
        decisions = DECISIONS + OPEN_TECHNICAL_LINE
        result = module.validate(self.make_feature(decisions_text=decisions))
        self.assertEqual([], result.errors)
        self.assertEqual(["D-002"], result.open_technical_decisions)


class WarningTests(ValidatorTestCase):
    def test_numeric_threshold_warns_without_blocking(self):
        text = SPEC.replace(
            "- **§1.1** — A user can create a note. <!-- provenance: S-001 -->",
            "- **§1.1** — A note is exported within 5 seconds. <!-- provenance: S-001 -->",
        )
        result = module.validate(self.make_feature(spec_text=text))
        self.assertEqual([], result.errors)
        self.assertTrue(any("numeric threshold" in w for w in result.warnings))

    def test_unresolved_marker_warns(self):
        text = SPEC.replace("## Goal\nx", "## Goal\n<TBD>")
        result = module.validate(self.make_feature(spec_text=text))
        self.assertTrue(any("<TBD>" in w for w in result.warnings))


class ExitCodeTests(ValidatorTestCase):
    def run_main(self, root, *args):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = module.main([str(root), *args])
        return code, buffer.getvalue()

    def test_valid_contract_exits_zero(self):
        code, _ = self.run_main(self.make_feature())
        self.assertEqual(0, code)

    def test_structural_failure_exits_one(self):
        root = self.make_feature(spec_text=SPEC.replace(" <!-- provenance: S-001 -->", "", 1))
        code, output = self.run_main(root)
        self.assertEqual(1, code)
        self.assertIn("ERROR:", output)

    def test_open_product_decision_exits_two_and_allow_open_exits_zero(self):
        decisions = DECISIONS + OPEN_PRODUCT_LINE
        spec_text = SPEC.replace("### Product\nNone", "### Product\n- D-002 — cart")
        review_text = (
            REVIEW.replace("STATUS: READY", "STATUS: BLOCKED")
            .replace("GATE: APPROVED", "GATE: PENDING")
            .replace("## Blockers\nNone", "## Blockers\n- D-002 — cart")
        )
        root = self.make_feature(
            spec_text=spec_text, decisions_text=decisions, review_text=review_text
        )
        self.assertEqual(2, self.run_main(root)[0])
        self.assertEqual(0, self.run_main(root, "--allow-open")[0])


if __name__ == "__main__":
    unittest.main()
