"""Tests for the context-decision-log skill. Each starts from the made-up log in participant/context/decisions, copied to a scratch folder."""
import json
import os
import re
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import decisions      # noqa: E402

REAL = os.path.join(decisions.REPO, "participant", "context", "decisions")
NEW = """
### E-015 · decision

- status: decision
- date: 2026-10-02
- title: A failed export is tried three times, then the on-call engineer is alerted
- source: design document DOC-9, section 1
- kind: technical
- approver: tech lead
- approved_in: decision record DR-9, comment 1
- approval_words: "Approved as written in DOC-9 section 1."
- affects: WX-20
- promotes: E-012
- answers: E-011

**Decision.** A failed export is tried again up to three times, ten minutes apart, and then the on-call engineer is alerted.
"""


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        for name in ("log.md", "ledger.json"):
            shutil.copy(os.path.join(REAL, name), self.tmp)
        self.log = os.path.join(self.tmp, "log.md")
        self.good = read(self.log)

    def put(self, text):
        with open(self.log, "w", encoding="utf-8") as f:
            f.write(text)

    def run_it(self, command, *more):
        self.said = []
        return decisions.main([command, "--log", self.log, *more], say=self.said.append)

    def messages(self, text=None, refresh=True, ledger=None):
        """What the check says is wrong with the log, after its generated part is brought up to date (unless refresh is False)."""
        text = self.good if text is None else text
        if refresh:
            text = text[:text.index(decisions.BEGIN)] + decisions.view_block(decisions.parse(text)) + text[text.index(decisions.END) + len(decisions.END):]
        return ["%s: %s" % one for one in decisions.check(text, ledger)[0]]

    def change(self, old, new, count=1):
        self.assertEqual(self.good.count(old), count, old)
        return self.good.replace(old, new)

    def broken(self, old, new, expected, entry=None):
        found = self.messages(self.change(old, new))
        hits = [one for one in found if expected in one and (entry is None or one.startswith(entry + ":"))]
        self.assertTrue(hits, "expected %r in %r" % (expected, found))
        return found


class TheLogAsWritten(Base):
    def test_the_handed_in_log_keeps_every_rule_and_is_sealed(self):
        self.assertEqual(self.run_it("check"), 0)
        self.assertIn("the log keeps every rule", self.said[-1])
        self.assertEqual(self.messages(refresh=False, ledger=json.loads(read(os.path.join(self.tmp, "ledger.json")))), [])

    def test_it_has_at_least_ten_entries_across_the_three_statuses(self):
        entries = decisions.parse(self.good)
        counts = {status: sum(1 for entry in entries if entry["fields"]["status"] == status) for status in decisions.STATUSES}
        self.assertGreaterEqual(len(entries), 10)
        self.assertTrue(all(count >= 2 for count in counts.values()), counts)

    def test_the_rules_document_is_what_the_code_writes(self):
        self.assertEqual(read(os.path.join(REAL, "rules.md")), decisions.rules_document())


class OneStatus(Base):
    """Criterion 1."""

    def test_a_status_outside_the_three(self):
        self.broken("### E-008 · proposal\n\n- status: proposal", "### E-008 · agreed\n\n- status: agreed", "exactly one of decision, proposal, question", "E-008")

    def test_a_heading_and_a_field_that_disagree(self):
        self.broken("### E-008 · proposal", "### E-008 · decision", "An entry has one status", "E-008")

    def test_two_statuses_in_one_entry(self):
        self.broken("- status: proposal\n- date: 2026-09-18", "- status: proposal\n- status: decision\n- date: 2026-09-18", "status is given more than once", "E-008")

    def test_an_entry_with_no_status(self):
        self.broken("- status: proposal\n- date: 2026-09-18", "- date: 2026-09-18", "exactly one of", "E-008")

    def test_the_statement_says_what_it_is(self):
        self.broken("**Proposal, not decided.** Two customers", "Two customers", "the statement must begin with", "E-008")
        self.broken("**Proposal, not decided.** Two customers", "**Decision.** Two customers", "the statement must begin with", "E-008")
        self.broken("**Question, not answered.** A queue worker", "**Decision.** A queue worker", "the statement must begin with", "E-011")


class Approval(Base):
    """Criterion 2, and the difference between approval and agreement."""

    def test_a_decision_with_no_approver_no_place_or_no_words(self):
        self.broken("- approver: security lead\n", "", "a decision must have approver", "E-013")
        self.broken("- approved_in: decision record DR-7, comment 1\n", "", "a decision must have approved_in", "E-013")
        self.broken('- approval_words: "Approved: no email address in any export file. User ids only."\n', "", "a decision must have approval_words", "E-013")
        self.broken("- kind: security\n- approver: security lead", "- approver: security lead", "a decision must have kind", "E-013")

    def test_agreement_in_conversation_is_not_approval(self):
        for words in ("Sounds good.", "No objections from me.", "Makes sense, fine by me.", "+1", "Agreed.", "OK", "Looks good to everyone."):
            found = self.broken('- approval_words: "Approved: no email address in any export file. User ids only."', '- approval_words: "%s"' % words,
                                "agreement, not approval", "E-013")
            self.assertEqual(len(found), 1, words)

    def test_words_that_only_contain_an_approval_word_inside_another_word_do_not_count(self):
        self.broken('"Approved: no email address in any export file. User ids only."', '"Unapproved so far, but looks good."', "agreement, not approval", "E-013")

    def test_explicit_words_of_approval_or_of_declining_count(self):
        for words in ("Approved.", "I approve this.", "Go ahead with this as written.", "I sign this off.", "Declined."):
            self.assertEqual(self.messages(self.change('"Approved: no email address in any export file. User ids only."', '"%s"' % words)), [], words)

    def test_a_report_of_approval_with_no_quoted_words(self):
        self.broken('- approval_words: "Approved: no email address in any export file. User ids only."', "- approval_words: the security lead said it was fine",
                    "inside double quotes", "E-013")

    def test_the_approver_must_be_the_role_for_that_kind(self):
        self.broken("- kind: security\n- approver: security lead", "- kind: security\n- approver: tech lead", "a security decision is approved by the security lead", "E-013")
        self.broken("- kind: security\n- approver: security lead", "- kind: budget\n- approver: security lead", "the kind is", "E-013")

    def test_the_place_of_approval_needs_a_reference(self):
        self.broken("- approved_in: decision record DR-7, comment 1", "- approved_in: the Tuesday meeting", "approved_in names no reference", "E-013")


class ProposalIsNotADecision(Base):
    """Criterion 3."""

    def test_a_proposal_may_not_carry_approval_fields(self):
        for line in ("- approver: tech lead", "- approved_in: decision record DR-4", '- approval_words: "Approved."'):
            self.broken("- raised_by: support lead\n", "- raised_by: support lead\n%s\n" % line, "a proposal may not have the field", "E-008")

    def test_a_question_may_not_carry_approval_fields(self):
        self.broken("- raised_by: security lead\n", "- raised_by: security lead\n- approver: security lead\n", "a question may not have the field", "E-006")

    def test_a_proposal_worded_as_settled(self):
        for wording in ("We will offer the export in both formats.", "It was agreed to offer both formats.", "The team decided on both formats.", "Final: both formats.",
                        "Both formats, confirmed.", "Approved by everyone on the call."):
            self.broken("Offer the export in both formats, chosen in the account's settings.", wording, "worded as if it were settled", "E-008")

    def test_a_proposal_s_title_worded_as_settled(self):
        self.broken("- title: Offer the export as an Excel file as well as CSV", "- title: Decided: Excel as well as CSV", "worded as if it were settled", "E-008")

    def test_a_proposal_may_quote_someone_else_s_wrong_wording_to_report_it(self):
        self.assertIn('The ticket WX-31 quotes it as "the decision"', self.good)
        self.assertEqual(self.messages(), [])

    def test_an_open_proposal_is_never_in_the_list_of_current_decisions(self):
        block = decisions.view_block(decisions.parse(self.good))
        current = block.split("## What is NOT decided")[0]
        for entry in ("E-003", "E-005", "E-008", "E-012", "E-001", "E-006", "E-011"):
            self.assertNotIn("| %s |" % entry, current)
        self.assertIn("| E-005 | 2026-09-15 | PROPOSAL, not decided |", block)

    def test_a_proposal_treated_as_decided_elsewhere_is_reported_and_stays_a_proposal(self):
        self.run_it("check")
        self.assertTrue(any("WARNING: E-005 is a proposal that something else treats as decided" in line and "WX-31, WX-32, WX-33" in line for line in self.said))
        self.assertEqual(decisions.states(decisions.parse(self.good))["E-005"], ("open", None))


class PromotionKeepsHistory(Base):
    """Criterion 4."""

    def test_promoting_adds_an_entry_and_leaves_the_proposal_as_it_was(self):
        before = {entry["id"]: entry["text"] for entry in decisions.parse(self.good)}
        self.put(self.good + NEW)
        self.assertEqual(self.run_it("view"), 0)
        self.assertEqual(self.run_it("seal"), 0)
        self.assertIn("sealed 1 new entry: E-015", self.said[-1])
        self.assertEqual(self.run_it("check"), 0)
        after = {entry["id"]: entry["text"] for entry in decisions.parse(read(self.log))}
        self.assertEqual(len(after), len(before) + 1)
        for entry_id, text in before.items():
            self.assertEqual(after[entry_id], text, entry_id)
        state = decisions.states(decisions.parse(read(self.log)))
        self.assertEqual((state["E-012"], state["E-011"], state["E-015"]), (("approved", "E-015"), ("answered", "E-015"), ("current", None)))
        self.assertIn("| E-015 | 2026-10-02 |", read(self.log).split("## What is NOT decided")[0])

    def test_the_earlier_entries_checksums_in_the_ledger_do_not_change(self):
        before = json.loads(read(os.path.join(self.tmp, "ledger.json")))["entries"]
        self.put(self.good + NEW)
        self.run_it("view")
        self.run_it("seal")
        after = json.loads(read(os.path.join(self.tmp, "ledger.json")))["entries"]
        self.assertEqual({key: after[key] for key in before}, before)
        self.assertEqual(len(after), len(before) + 1)

    def test_editing_a_proposal_into_a_decision_in_place_is_caught(self):
        edited = self.change("### E-012 · proposal\n\n- status: proposal", "### E-012 · decision\n\n- status: decision")
        found = self.messages(edited, ledger=json.loads(read(os.path.join(self.tmp, "ledger.json"))))
        self.assertTrue(any(one.startswith("E-012: the entry was changed after it was sealed") for one in found), found)

    def test_any_edit_to_a_sealed_entry_is_caught_even_one_that_keeps_every_other_rule(self):
        edited = self.change("Try a failed export again up to three times", "Try a failed export again up to five times")
        self.assertEqual(self.messages(edited, ledger=json.loads(read(os.path.join(self.tmp, "ledger.json")))),
                         ["E-012: the entry was changed after it was sealed. An entry is never edited: write a new entry that points at it"])

    def test_a_removed_entry_is_caught(self):
        cut = self.good[:self.good.index("### E-014")]
        found = self.messages(cut, ledger=json.loads(read(os.path.join(self.tmp, "ledger.json"))))
        self.assertIn("E-014: the entry was sealed and is no longer in the log. An entry is never removed", found)

    def test_an_entry_not_yet_sealed_is_reported_and_seal_never_reseals(self):
        self.put(self.good + NEW)
        self.run_it("view")
        self.assertEqual(self.run_it("check"), 2)
        self.assertTrue(any("E-015: the entry is not sealed yet" in line for line in self.said))
        self.put(read(self.log).replace("up to three times, ten minutes apart, and then", "up to nine times, and then"))
        ledger_before = read(os.path.join(self.tmp, "ledger.json"))
        self.put(read(self.log).replace("Each account's export is sent on Friday at 06:00 UTC.", "Each account's export is sent on Sunday."))
        self.run_it("seal")
        after = json.loads(read(os.path.join(self.tmp, "ledger.json")))["entries"]
        self.assertEqual(after["E-004"], json.loads(ledger_before)["entries"]["E-004"])
        self.assertEqual(self.run_it("check"), 2)
        self.assertTrue(any("E-004: the entry was changed after it was sealed" in line for line in self.said))

    def test_a_proposal_is_approved_or_declined_once(self):
        again = NEW.replace("- promotes: E-012\n- answers: E-011\n", "- rejects: E-003\n")
        self.assertTrue(any("E-003 was already approved or declined by E-004" in one for one in self.messages(self.good + again)))

    def test_promotes_must_point_at_an_earlier_proposal(self):
        self.assertTrue(any("promotes points at E-002, which is a decision" in one for one in self.messages(self.good + NEW.replace("promotes: E-012", "promotes: E-002"))))
        self.assertTrue(any("promotes points at E-099, which is not an earlier entry" in one for one in self.messages(self.good + NEW.replace("promotes: E-012", "promotes: E-099"))))
        self.assertTrue(any("promotes points at E-015, which is not an earlier entry" in one for one in self.messages(self.good + NEW.replace("promotes: E-012", "promotes: E-015"))))


class Superseded(Base):
    """Criterion 5."""

    def test_a_superseded_decision_is_linked_to_its_replacement_both_ways_in_the_view(self):
        state = decisions.states(decisions.parse(self.good))
        self.assertEqual((state["E-004"], state["E-007"]), (("superseded", "E-014"), ("superseded", "E-009")))
        block = decisions.view_block(decisions.parse(self.good))
        self.assertIn("| E-004 | 2026-09-10 | decision | SUPERSEDED by E-014 |", block)
        self.assertIn("- supersedes: E-004", self.good)

    def test_without_the_link_the_old_decision_would_still_be_current(self):
        unlinked = self.change("- supersedes: E-004\n", "")
        block = decisions.view_block(decisions.parse(unlinked))
        current = block.split("## What is NOT decided")[0]
        self.assertIn("| E-004 |", current)
        self.assertIn("| E-014 |", current)

    def test_supersedes_must_point_at_an_earlier_decision(self):
        self.broken("- supersedes: E-004", "- supersedes: E-003", "supersedes points at E-003, which is a proposal", "E-014")
        self.broken("- supersedes: E-004", "- supersedes: E-020", "which is not an earlier entry", "E-014")

    def test_a_decision_is_superseded_once(self):
        self.broken("- supersedes: E-004", "- supersedes: E-007", "E-007 was already superseded by E-009", "E-014")

    def test_a_proposal_cannot_supersede_a_decision(self):
        self.broken("- raised_by: tech lead\n- kind: technical\n- support: In the thread", "- raised_by: tech lead\n- kind: technical\n- supersedes: E-009\n- support: In the thread",
                    "a proposal may not have the field supersedes", "E-012")


class Sources(Base):
    """Criterion 6."""

    def test_every_entry_has_a_source_with_a_reference(self):
        for entry in decisions.parse(self.good):
            self.assertRegex(entry["fields"]["source"], decisions.REFERENCE_SHAPE)

    def test_an_entry_with_no_source_or_a_vague_one(self):
        self.broken("- source: ticket WX-20, comment 2\n", "", "a question must have source", "E-011")
        self.broken("- source: ticket WX-20, comment 2", "- source: somebody mentioned it", "source names no reference", "E-011")
        self.broken("- source: decision record DR-1\n", "", "a decision must have source", "E-002")


class CurrentView(Base):
    """Criterion 7."""

    def test_the_view_lists_exactly_the_decisions_not_superseded(self):
        current = decisions.view_block(decisions.parse(self.good)).split("## What is NOT decided")[0]
        self.assertEqual(re.findall(r"^\| (E-\d{3}) \|", current, re.M), ["E-002", "E-009", "E-010", "E-013", "E-014"])

    def test_the_view_comes_before_the_first_entry(self):
        self.assertLess(self.good.index("## What is decided now"), self.good.index("### E-001"))

    def test_a_view_edited_by_hand_or_gone_stale_is_caught(self):
        by_hand = self.change("| E-014 | 2026-09-30 | The export is sent every Monday at 06:00 UTC | product |", "| E-014 | 2026-09-30 | The export is sent every Tuesday | product |")
        self.assertIn("log: the view of current decisions at the top is not what the entries say. It is stale or was edited by hand. Run: decisions.py view", self.messages(by_hand, refresh=False))
        self.assertTrue(any("is not what the entries say" in one for one in self.messages(self.good + NEW, refresh=False)))
        added = self.change("| E-002 | 2026-09-03 | The weekly export goes", "| E-005 | 2026-09-15 | Keep each export file for 90 days | security | tech lead | DOC-4 | WX-31 |\n| E-002 | 2026-09-03 | The weekly export goes")
        self.assertTrue(any("is not what the entries say" in one for one in self.messages(added, refresh=False)))

    def test_view_rewrites_only_the_generated_part_and_twice_changes_nothing(self):
        self.put(self.good + NEW)
        self.run_it("view")
        once = read(self.log)
        self.assertEqual(once[:once.index(decisions.BEGIN)], self.good[:self.good.index(decisions.BEGIN)])
        self.assertEqual(once[once.index(decisions.END):], (self.good + NEW)[self.good.index(decisions.END):])
        self.run_it("view")
        self.assertEqual(read(self.log), once)
        self.assertIn("Nothing was written", self.said[-1])

    def test_a_missing_generated_part_is_caught(self):
        gone = self.good[:self.good.index(decisions.BEGIN)] + self.good[self.good.index(decisions.END) + len(decisions.END):]
        self.assertIn(("log", "the generated part, between its two marker lines, is missing. Run: decisions.py view"), decisions.check(gone)[0])


class OrderAndShape(Base):
    def test_ids_in_order_with_no_gaps_and_dates_never_backwards(self):
        self.broken("### E-014 · decision", "### E-016 · decision", "this one should be E-014", "E-016")
        self.broken("- date: 2026-09-30", "- date: 2026-09-02", "its date is before the date of the entry above it", "E-014")
        self.broken("- date: 2026-09-30", "- date: 30 September", "the date is not a day", "E-014")

    def test_a_field_the_rules_do_not_define_and_a_question_with_no_question_mark(self):
        self.broken("- raised_by: support lead\n", "- raised_by: support lead\n- decided_by: everyone\n", "the field decided_by is not one the rules define", "E-008")
        self.broken("- title: Who receives the weekly export?", "- title: Who receives the weekly export", "ends with a question mark", "E-001")

    def test_a_work_item_that_is_not_an_identifier(self):
        self.broken("- affects: WX-21", "- affects: the Excel work", "which is not a work item's identifier", "E-008")


class Stretch(Base):
    def test_decisions_name_the_work_items_they_affect_and_those_with_none_are_reported(self):
        block = decisions.view_block(decisions.parse(self.good))
        self.assertIn("| WX-12, WX-13 |", block)
        idle = block.split("## Current decisions with no work item")[1].split("## What became")[0]
        self.assertEqual(re.findall(r"^- (E-\d{3}):", idle, re.M), ["E-010", "E-013"])

    def test_a_superseded_decision_with_no_work_item_is_not_reported(self):
        text = self.change("- affects: WX-14\n", "")
        idle = decisions.view_block(decisions.parse(text)).split("## Current decisions with no work item")[1].split("## What became")[0]
        self.assertNotIn("E-007", idle)


class TheSkillItself(Base):
    def test_it_adds_no_entry_and_approves_nothing(self):
        code = read(os.path.join(os.path.dirname(HERE), "decisions.py"))
        self.assertEqual(set(re.findall(r"^(?:import|from) ([A-Za-z_.]+)", code, re.M)), {"argparse", "datetime", "hashlib", "json", "os", "re", "sys"})
        for command in ("check", "view", "seal"):
            before = decisions.parse(read(self.log))
            self.run_it(command)
            after = decisions.parse(read(self.log))
            self.assertEqual([entry["text"] for entry in after], [entry["text"] for entry in before], command)

    def test_check_changes_no_file(self):
        self.put(self.change("- approver: security lead\n", ""))
        before = {name: read(os.path.join(self.tmp, name)) for name in sorted(os.listdir(self.tmp))}
        self.assertEqual(self.run_it("check"), 2)
        self.assertEqual({name: read(os.path.join(self.tmp, name)) for name in sorted(os.listdir(self.tmp))}, before)

    def test_a_log_that_cannot_be_read_stops_with_a_message(self):
        self.assertEqual(decisions.main(["check", "--log", os.path.join(self.tmp, "none.md")], say=lambda line: None), 1)


if __name__ == "__main__":
    unittest.main()
