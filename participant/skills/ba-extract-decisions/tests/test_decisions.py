"""Tests for decisions.py. They contact nothing and write only to a scratch folder.

    python3 -m unittest discover -s participant/skills/ba-extract-decisions/tests -v
"""
import copy
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import decisions   # noqa: E402
import sorting     # noqa: E402

SAMPLE, NOTIF = "sample-meeting", "notifications-meeting"


def source(name):
    return decisions.read(os.path.join(decisions.FOLDER, name + ".md")), decisions.read(os.path.join(decisions.FOLDER, name + ".provenance.yaml"))


def built(name, change=None):
    """The decisions file build writes, after an optional change to a copy of the sorting."""
    record_text, _ = source(name)
    meeting = copy.deepcopy(sorting.SORTED[name])
    if change:
        change({i["id"]: i for i in meeting["items"]}, meeting)
    return decisions.render(name, decisions.read_record(record_text), meeting, record_text)


def problems(name, text=None, record_text=None, provenance_text=None, same_file=False):
    record, provenance = source(name)
    return decisions.check(built(name) if text is None else text, record_text or record, provenance_text or provenance, same_file)[0]


def edited(name, old, new):
    text = built(name)
    assert old in text, old
    return problems(name, text.replace(old, new, 1))


def has(got, words):
    return any(words in p for p in got)


class Sound(unittest.TestCase):
    def test_both_meetings_as_sorted_pass(self):
        self.assertEqual(problems(SAMPLE), [])
        self.assertEqual(problems(NOTIF), [])

    def test_the_handed_in_files_are_what_the_code_writes(self):
        for name in (SAMPLE, NOTIF):
            self.assertEqual(decisions.read(os.path.join(decisions.FOLDER, name + ".decisions.md")), built(name), name)
        self.assertEqual(decisions.read(decisions.RULES), decisions.rules_text())

    def test_the_record_is_read_as_it_is_written(self):
        record = decisions.read_record(source(SAMPLE)[0])
        self.assertEqual(record["id"], "tr-2026-10-21-checkout-refinement")
        self.assertEqual(len(record["lines"]), 24)
        self.assertEqual(record["lines"]["U-0006"], {"speaker": "Priya Natarajan", "words": "That's fine.", "uncertain": False})
        self.assertTrue(record["lines"]["U-0011"]["uncertain"] and record["lines"]["U-0013"]["uncertain"])
        self.assertEqual(record["roles"]["Dana Whitfield"], "Tester")

    def test_an_utterance_on_two_lines_is_read_whole(self):
        record = decisions.read_record(source(SAMPLE)[0])
        self.assertEqual(record["lines"]["U-0019"]["words"],
                         "Back to the story. Acceptance criteria: a guest can pay with a card, gets an email receipt, and is offered account linking once, after the order is placed.")

    def test_the_counts_of_each_meeting(self):
        for name, expected in ((SAMPLE, [7, 0, 0, 3, 1]), (NOTIF, [6, 1, 3, 2, 1])):
            facts = decisions.check(built(name), *source(name))[1]
            self.assertEqual(list(facts["counts"].values()), expected, name)

    def test_every_line_of_each_record_is_cited_or_listed(self):
        for name in (SAMPLE, NOTIF):
            facts = decisions.check(built(name), *source(name))[1]
            self.assertEqual(sorted(facts["cited"] | set(facts["listed"])), sorted(facts["record"]["lines"]), name)
            self.assertEqual(facts["cited"] & set(facts["listed"]), set())


class CitedLinesExist(unittest.TestCase):
    def test_a_decision_citing_a_line_that_does_not_exist(self):
        got = edited(SAMPLE, "in U-0004: ", "in U-0044: ")
        self.assertIn("U-0044 is cited by D-02 and is not in the source record.", got)

    def test_a_line_number_past_the_end_of_the_record(self):
        got = edited(SAMPLE, "in U-0006: ", "in U-0025: ")
        self.assertIn("U-0025 is cited by D-03 and is not in the source record.", got)

    def test_an_identifier_written_in_a_note_is_checked_too(self):
        got = edited(SAMPLE, "under O-02.", "under O-02, see U-0099.")
        self.assertIn("U-0099 is cited by the file and is not in the source record.", got)

    def test_an_identifier_with_five_digits(self):
        got = edited(SAMPLE, "in U-0004: ", "in U-00004: ")
        self.assertTrue(has(got, "U-00004 is cited by D-02 and is not in the source record."), got)

    def test_a_citation_into_another_transcript(self):
        got = edited(SAMPLE, "under O-02.", "under O-02, see tr-2026-11-04-notification-settings#U-0003.")
        self.assertIn("A line is cited from tr-2026-11-04-notification-settings, which is not this record.", got)

    def test_a_line_removed_from_the_record_is_reported_where_it_is_cited(self):
        record, provenance = source(SAMPLE)
        start, end = record.index('<a id="U-0014">'), record.index('<a id="U-0015">')
        got = decisions.check(built(SAMPLE), record[:start] + record[end:], provenance)[0]
        self.assertIn("U-0014 is cited by D-06 and is not in the source record.", got)

    def test_a_decision_with_no_citation_at_all(self):
        def change(by_id, meeting):
            by_id["D-01"]["ruled"] = []
            meeting["unsorted"]["U-0002"] = "left out"
        got = problems(SAMPLE, built(SAMPLE, change))
        self.assertIn("D-01 cites no line of the source record.", got)

    def test_words_that_are_not_the_records(self):
        got = edited(SAMPLE, "\"Yes, email is required. Phone is optional.\"", "\"Yes, email and phone are required.\"")
        self.assertIn("D-02 quotes U-0004 in words that are not the record's.", got)

    def test_one_word_dropped_from_a_quotation(self):
        got = edited(NOTIF, "\"Sure, I guess. Fine by me.\"", "\"Sure. Fine by me.\"")
        self.assertIn("D-05 quotes U-0017 in words that are not the record's.", got)

    def test_a_line_given_to_the_wrong_speaker(self):
        got = edited(SAMPLE, "Agreed by: Priya Natarajan, Product owner, in U-0006", "Agreed by: Marcus Oyelaran, Developer, in U-0006")
        self.assertTrue(has(got, "D-03 gives U-0006 to \"Marcus Oyelaran, Developer\". The record gives it to \"Priya Natarajan, Product owner\"."), got)

    def test_a_right_speaker_with_the_wrong_role(self):
        got = edited(SAMPLE, "Ruled by: Priya Natarajan, Product owner, in U-0004", "Ruled by: Priya Natarajan, Tester, in U-0004")
        self.assertTrue(has(got, "D-02 gives U-0004 to"), got)


class ProposalsAreNotDecisions(unittest.TestCase):
    def test_a_proposal_moved_under_decisions_is_reported(self):
        text = built(NOTIF)
        start, end = text.index("### P-01"), text.index("### P-02")
        moved = text[:start] + text[end:]
        moved = moved.replace("## Proposals that did not become decisions", text[start:end] + "## Proposals that did not become decisions")
        self.assertIn("P-01 is under \"decision\", where it does not belong.", problems(NOTIF, moved))

    def test_a_proposal_relabelled_as_an_agreed_decision_has_nobody_who_accepted(self):
        def change(by_id, meeting):
            p = by_id["P-01"]
            p.update(id="D-08", kind="decision", basis="agreed", proposed=p["put"], accepted=[])
        got = problems(NOTIF, built(NOTIF, change))
        self.assertIn("D-08 is listed as a decision, and no line is cited in which anyone accepted it. It is a proposal.", got)

    def test_the_proposers_own_agreed_is_not_acceptance(self):
        def change(by_id, meeting):
            p = by_id["P-01"]
            p.update(id="D-08", kind="decision", basis="agreed", proposed=["U-0006"], accepted=["U-0008"])
        got = problems(NOTIF, built(NOTIF, change))
        self.assertIn("D-08 is \"agreed\" only by Tomas Example, who proposed it. A proposer's own agreement is not acceptance.", got)

    def test_agreement_from_an_uncertain_speaker_is_not_acceptance(self):
        def change(by_id, meeting):
            p = by_id["P-02"]
            p.update(id="D-08", kind="decision", basis="agreed", proposed=["U-0024"], accepted=["U-0025"])
        got = problems(NOTIF, built(NOTIF, change))
        self.assertIn("D-08 is \"agreed\" in U-0025 by a speaker whose identity is uncertain. Nobody can be named as having agreed.", got)

    def test_acceptance_before_the_proposal(self):
        def change(by_id, meeting):
            by_id["D-05"].update(proposed=["U-0016"], accepted=["U-0015"])
        self.assertIn("D-05 is \"agreed\" in a line that comes before the line that proposed it.", problems(NOTIF, built(NOTIF, change)))

    def test_a_ruling_outside_the_speakers_role_is_a_proposal(self):
        def change(by_id, meeting):
            p = by_id["O-02"]
            p.update(id="D-08", kind="decision", basis="ruled", area="build", ruled=["U-0014"])
        got = problems(NOTIF, built(NOTIF, change))
        self.assertIn("D-08 is \"ruled\" by a Product owner on a question of build, which that role does not own. It is a proposal.", got)

    def test_a_ruling_by_an_uncertain_speaker(self):
        def change(by_id, meeting):
            by_id["D-06"].update(basis="ruled", area="product", ruled=["U-0013"])
        got = problems(SAMPLE, built(SAMPLE, change))
        self.assertIn("D-06 is \"ruled\" in U-0013 by a speaker with no role that owns any kind of question.", got)

    def test_a_ruling_inside_the_speakers_role_passes(self):
        def change(by_id, meeting):
            by_id["O-01"].update(id="D-08", kind="decision", basis="ruled", area="build", ruled=["U-0018"])
        got = problems(NOTIF, built(NOTIF, change))
        self.assertFalse(has(got, "D-08"), got)

    def test_a_proposal_with_an_agreed_by_line(self):
        got = edited(NOTIF, "- Then: Noor Example, Product owner, in U-0033", "- Agreed by: Noor Example, Product owner, in U-0033")
        self.assertIn("P-03 is not a decision and has an \"Agreed by\" or \"Ruled by\" line.", got)

    def test_a_proposal_must_say_why(self):
        got = edited(NOTIF, "- Why it is not a decision: Only the person who proposed it said it was agreed.", "- Remark: Only the person who proposed it said it was agreed.")
        self.assertIn("P-01 does not say why it is not a decision, or where it was left.", got)


class WhoAgreed(unittest.TestCase):
    def test_every_decision_names_who_agreed_or_says_it_was_not_stated(self):
        for name in (SAMPLE, NOTIF):
            for item in decisions.check(built(name), *source(name))[1]["decisions"]:
                agreed = [c for c in item["cites"] if c["label"] == "Agreed by"]
                self.assertTrue(bool(agreed) != item["not_stated"], item["id"])

    def test_a_ruled_decision_without_the_words_agreement_was_not_stated(self):
        got = edited(SAMPLE, "in U-0004: \"Yes, email is required. Phone is optional.\"\n- Agreed by: agreement was not stated. No later line objects.\n", "in U-0004: \"Yes, email is required. Phone is optional.\"\n")
        self.assertIn("D-02 is a ruled decision and does not state that agreement was not stated.", got)

    def test_a_decision_that_says_both(self):
        got = edited(SAMPLE, "- Note: The acceptance is two words.", "- Agreed by: agreement was not stated. No later line objects.\n- Note: The acceptance is two words.")
        self.assertIn("D-03 names who agreed and also says agreement was not stated.", got)

    def test_a_ruled_decision_that_also_names_an_agreer(self):
        got = edited(SAMPLE, "- In answer to: Marcus Oyelaran, Developer, in U-0003", "- Agreed by: Marcus Oyelaran, Developer, in U-0003")
        self.assertIn("D-02 is \"ruled\" and also names somebody as agreeing. It is one or the other.", got)

    def test_a_decision_that_is_neither_agreed_nor_ruled(self):
        got = edited(SAMPLE, "### D-02 · ruled · in force", "### D-02 · settled · in force")
        self.assertIn("D-02 does not say whether it was agreed or ruled.", got)

    def test_an_agreed_decision_with_no_proposing_line(self):
        got = edited(SAMPLE, "- Proposed by: Dana Whitfield, Tester, in U-0005", "- Said by: Dana Whitfield, Tester, in U-0005")
        self.assertIn("D-03 is an agreed decision and cites no line that proposed it.", got)


class Separate(unittest.TestCase):
    def test_open_items_and_proposals_are_under_their_own_headings(self):
        text = built(NOTIF)
        order = [text.index("## " + title) for _, _, title in decisions.SECTIONS] + [text.index("## Lines not sorted")]
        self.assertEqual(order, sorted(order))
        self.assertLess(text.index("## Open discussion and undecided items"), text.index("### O-01"))
        self.assertLess(text.index("### O-01"), text.index("## Not decisions"))

    def test_an_open_item_moved_under_decisions_is_reported(self):
        text = built(SAMPLE)
        start, end = text.index("### O-01"), text.index("### O-02")
        moved = (text[:start] + text[end:]).replace("## Proposals that did not become decisions", text[start:end] + "## Proposals that did not become decisions")
        self.assertIn("O-01 is under \"decision\", where it does not belong.", problems(SAMPLE, moved))

    def test_a_decision_moved_under_open_is_reported(self):
        text = built(SAMPLE)
        start, end = text.index("### D-07"), text.index("## Proposals that did not become decisions")
        moved = (text[:start] + text[end:]).replace("## Not decisions", text[start:end] + "## Not decisions")
        self.assertIn("D-07 is under \"open\", where it does not belong.", problems(SAMPLE, moved))

    def test_the_record_changed_after_ingestion_is_reported(self):
        record, provenance = source(SAMPLE)
        got = decisions.check(built(SAMPLE), record.replace("Phone is optional.", "Phone is required."), provenance)[0]
        self.assertIn("The source record has been changed since it was ingested: its SHA-256 is not the one in its provenance file.", got)
        self.assertIn("D-02 quotes U-0004 in words that are not the record's.", got)

    def test_one_space_added_to_the_record_is_reported(self):
        record, provenance = source(SAMPLE)
        got = decisions.check(built(SAMPLE), record + " ", provenance)[0]
        self.assertTrue(has(got, "has been changed since it was ingested"), got)

    def test_decisions_written_into_the_record_are_reported(self):
        record, provenance = source(SAMPLE)
        got = decisions.check(built(SAMPLE), record + "\n### D-01 · ruled · in force\n", provenance)[0]
        self.assertIn("The source record holds decision items. Analysis does not belong in the record.", got)

    def test_the_record_copied_into_the_decisions_file_is_reported(self):
        record, _ = source(SAMPLE)
        got = problems(SAMPLE, built(SAMPLE) + record[record.index('<a id="U-0001">'):record.index('<a id="U-0002">')])
        self.assertIn("The decisions file holds utterance headings, as if the record had been copied into it.", got)

    def test_one_file_for_both_is_reported(self):
        self.assertIn("The decisions file and the source record are the same file.", problems(SAMPLE, same_file=True))

    def test_a_decisions_file_made_from_another_version_of_the_record(self):
        got = edited(SAMPLE, "- source_sha256: `449f", "- source_sha256: `0000")
        self.assertIn("The decisions file was not made from the source record as it is now: the SHA-256 it states is not the record's.", got)

    def test_a_decisions_file_checked_against_the_other_meeting(self):
        got = decisions.check(built(SAMPLE), *source(NOTIF))[0]
        self.assertTrue(has(got, "does not name the source record's transcript ID, tr-2026-11-04-notification-settings"), got)
        self.assertTrue(has(got, "in words that are not the record's"), got)

    def test_a_provenance_file_without_the_records_hash(self):
        record, provenance = source(SAMPLE)
        got = decisions.check(built(SAMPLE), record, provenance.replace("record_sha256:", "record_hash:"))[0]
        self.assertTrue(has(got, "does not give the record's SHA-256"), got)

    def test_build_never_writes_to_the_record(self):
        scratch = tempfile.mkdtemp(prefix="gtq-decisions-")
        self.addCleanup(shutil.rmtree, scratch, True)
        for ext in (".md", ".provenance.yaml"):
            shutil.copy(os.path.join(decisions.FOLDER, SAMPLE + ext), scratch)
        before = decisions.read(os.path.join(scratch, SAMPLE + ".md"))
        said = []
        self.assertEqual(decisions.main(["build", SAMPLE, "--folder", scratch], say=said.append), 0)
        self.assertEqual(decisions.read(os.path.join(scratch, SAMPLE + ".md")), before)
        self.assertEqual(sorted(os.listdir(scratch)), [SAMPLE + ".decisions.md", SAMPLE + ".md", SAMPLE + ".provenance.yaml"])
        self.assertEqual(decisions.main(["check", SAMPLE, "--folder", scratch], say=said.append), 0)


class Reversed(unittest.TestCase):
    def test_the_reversed_decision_is_kept_marked_and_not_counted_in_force(self):
        text = built(NOTIF)
        self.assertIn("### D-01 · agreed · REVERSED later in the meeting", text)
        self.assertIn("- Reversed by: Noor Example, Product owner, in U-0022: \"Then I take that back.", text)
        self.assertIn("- Prompted by: Ines Example, Tester, in U-0021: ", text)
        self.assertIn("- Replaced by: D-06", text)
        self.assertIn("| Decisions in force | 6 |", text)
        self.assertIn("| Decisions reversed later in the meeting | 1 |", text)

    def test_marked_reversed_with_no_reversing_line(self):
        got = edited(NOTIF, "### D-02 · ruled · in force", "### D-02 · ruled · REVERSED later in the meeting")
        self.assertIn("D-02 is marked reversed and cites no line that reversed it.", got)

    def test_a_reversing_line_on_a_decision_still_marked_in_force(self):
        got = edited(NOTIF, "### D-01 · agreed · REVERSED later in the meeting", "### D-01 · agreed · in force")
        self.assertIn("D-01 cites a line that reversed it and is not marked reversed.", got)

    def test_reversed_by_a_line_before_the_decision_was_made(self):
        def change(by_id, meeting):
            by_id["D-01"]["reversed"]["by"] = ["U-0001"]
            meeting["unsorted"].pop("U-0001")
        got = problems(NOTIF, built(NOTIF, change))
        self.assertIn("D-01 is \"reversed\" by a line that comes before the decision was made.", got)

    def test_reversed_with_no_replacement_named(self):
        got = edited(NOTIF, "- Replaced by: D-06\n", "")
        self.assertIn("D-01 is marked reversed and does not name a decision in force that replaced it.", got)

    def test_replaced_by_something_that_is_not_a_decision(self):
        got = edited(NOTIF, "- Replaced by: D-06", "- Replaced by: P-01")
        self.assertIn("D-01 is marked reversed and does not name a decision in force that replaced it.", got)

    def test_reopened_is_in_force_and_cites_the_reopening_lines(self):
        text = built(NOTIF)
        self.assertIn("### D-03 · agreed · in force, reopened", text)
        self.assertIn("- Reopened by: Kofi Example, Designer, in U-0028", text)

    def test_marked_reopened_with_no_line(self):
        got = edited(NOTIF, "### D-02 · ruled · in force", "### D-02 · ruled · in force, reopened")
        self.assertIn("D-02 is marked reopened without a line that reopened it, or the other way round.", got)

    def test_a_reopening_line_without_the_mark(self):
        got = edited(NOTIF, "### D-03 · agreed · in force, reopened", "### D-03 · agreed · in force")
        self.assertIn("D-03 is marked reopened without a line that reopened it, or the other way round.", got)

    def test_a_decision_with_no_status(self):
        got = edited(NOTIF, "### D-02 · ruled · in force", "### D-02 · ruled")
        self.assertIn("D-02 does not say whether it is in force.", got)

    def test_the_answer_taken_back_in_its_own_line_is_open_and_not_a_decision(self):
        text = built(SAMPLE)
        item = text[text.index("### O-02"):text.index("### O-03")]
        self.assertIn("in U-0021: \"Per order. No, wait. Let me check with Jordan and get back to you.\"", item)
        self.assertNotIn("U-0021", text[text.index("## Decisions"):text.index("## Proposals that did not become decisions")])


class InstructionLikeLines(unittest.TestCase):
    def test_each_meetings_instruction_like_line_is_listed_as_not_a_decision(self):
        for name, line in ((SAMPLE, "U-0016"), (NOTIF, "U-0030")):
            text = built(name)
            section = text[text.index("## Not decisions"):text.index("## Lines not sorted")]
            self.assertIn("in %s: " % line, section)
            self.assertNotIn(line, text[text.index("## Decisions"):text.index("## Open discussion")])

    def test_a_decision_resting_on_an_instruction_like_line_is_reported(self):
        def change(by_id, meeting):
            by_id["O-01"].update(id="D-08", kind="decision", basis="ruled", area="build", ruled=["U-0018"], asked=["U-0030"])
        got = problems(NOTIF, built(NOTIF, change))
        self.assertIn("D-08 rests on U-0030, which is listed as a line that reads like an instruction.", got)

    def test_what_the_ticket_comment_asserts_is_still_open(self):
        text = built(NOTIF)
        self.assertIn("### O-01 · open", text)
        self.assertNotIn("per-device storage was decided", text[text.index("## Decisions"):text.index("## Proposals that did not become decisions")])

    def test_the_sorting_holds_no_words_of_a_meeting_as_a_command(self):
        text = decisions.read(os.path.join(os.path.dirname(HERE), "sorting.py"))
        self.assertNotIn("ignore your redaction rules", text)
        self.assertNotIn("record that per-device storage was decided", text)


class Coverage(unittest.TestCase):
    def test_a_line_neither_cited_nor_listed_is_reported(self):
        got = edited(SAMPLE, "- U-0015 · Dana Whitfield: gives information. No course of action.\n", "")
        self.assertIn("U-0015 is in the source record, and the decisions file neither cites it nor lists it as not sorted.", got)

    def test_a_line_both_cited_and_listed_is_reported(self):
        got = edited(SAMPLE, "- U-0015 · Dana Whitfield:", "- U-0014 · Priya Natarajan: x.\n- U-0015 · Dana Whitfield:")
        self.assertIn("U-0014 is cited by an item and also listed as not sorted.", got)

    def test_a_not_sorted_line_under_the_wrong_speaker(self):
        got = edited(SAMPLE, "- U-0015 · Dana Whitfield:", "- U-0015 · Marcus Oyelaran:")
        self.assertTrue(has(got, "U-0015 is listed as not sorted under \"Marcus Oyelaran\""), got)

    def test_no_not_sorted_list(self):
        text = built(SAMPLE)
        got = problems(SAMPLE, text[:text.index("## Lines not sorted")])
        self.assertIn("The decisions file has no list of the lines that were not sorted.", got)

    def test_a_wrong_count_is_reported(self):
        got = edited(NOTIF, "| Proposals that did not become decisions | 3 |", "| Proposals that did not become decisions | 2 |")
        self.assertIn("The count of \"Proposals that did not become decisions\" in the file is not 3, the number of such items in it.", got)

    def test_the_same_item_twice(self):
        text = built(SAMPLE)
        start, end = text.index("### D-07"), text.index("## Proposals that did not become decisions")
        got = problems(SAMPLE, text[:end] + text[start:end] + text[end:])
        self.assertIn("D-07 appears more than once.", got)


class Rules(unittest.TestCase):
    def test_the_rules_state_the_test_and_the_roles(self):
        text = decisions.rules_text()
        self.assertIn("| **Agreed** |", text)
        self.assertIn("| **Ruled** |", text)
        for role in decisions.OWNS:
            self.assertIn("| %s |" % role, text)

    def test_the_rules_give_at_least_two_borderline_lines_each_quoted_from_a_record(self):
        text = decisions.rules_text()
        section = text[text.index("## 6. Borderline"):text.index("## 7.")]
        self.assertEqual(section.count("Classified as **"), 6)
        for name in (SAMPLE, NOTIF):
            record = decisions.read_record(source(name)[0])
            for line in [l for l in section.splitlines() if l.startswith("**`%s#" % record["id"])]:
                number = line.split("#")[1][:6]
                self.assertIn("> %s" % record["lines"][number]["words"], section)

    def test_the_borderline_lines_are_the_ones_the_notes_are_about(self):
        text = decisions.rules_text()
        for line in ("tr-2026-10-21-checkout-refinement#U-0002", "tr-2026-11-04-notification-settings#U-0029",
                     "tr-2026-10-21-checkout-refinement#U-0006", "tr-2026-10-21-checkout-refinement#U-0021",
                     "tr-2026-11-04-notification-settings#U-0008", "tr-2026-11-04-notification-settings#U-0017"):
            self.assertIn("**`%s`**" % line, text)


class Command(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.mkdtemp(prefix="gtq-decisions-")
        self.addCleanup(shutil.rmtree, self.scratch, True)
        for ext in (".md", ".provenance.yaml"):
            shutil.copy(os.path.join(decisions.FOLDER, NOTIF + ext), self.scratch)

    def run_main(self, *argv):
        said = []
        return decisions.main(list(argv) + ["--folder", self.scratch], say=said.append), said

    def test_check_passes_with_exit_code_0(self):
        self.run_main("build", NOTIF)
        code, said = self.run_main("check", NOTIF)
        self.assertEqual(code, 0)
        self.assertTrue(said[-1].startswith("CHECK PASSED."))

    def test_check_fails_with_exit_code_1_and_names_the_identifier(self):
        self.run_main("build", NOTIF)
        path = os.path.join(self.scratch, NOTIF + ".decisions.md")
        text = decisions.read(path).replace("in U-0005: ", "in U-0055: ")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        code, said = self.run_main("check", NOTIF)
        self.assertEqual(code, 1)
        self.assertIn("PROBLEM: U-0055 is cited by D-02 and is not in the source record.", said)
        self.assertTrue(said[-1].startswith("CHECK FAILED."))

    def test_check_without_a_decisions_file_does_not_pass(self):
        self.assertEqual(self.run_main("check", NOTIF)[0], 1)

    def test_a_meeting_with_no_record_is_not_done(self):
        self.assertEqual(self.run_main("check", "no-such-meeting")[0], 2)

    def test_build_for_a_meeting_with_no_sorting(self):
        for ext in (".md", ".provenance.yaml"):
            shutil.copy(os.path.join(self.scratch, NOTIF + ext), os.path.join(self.scratch, "other" + ext))
        code, said = self.run_main("build", "other")
        self.assertEqual(code, 2)
        self.assertFalse(os.path.exists(os.path.join(self.scratch, "other.decisions.md")))

    def test_an_empty_decisions_file_does_not_pass(self):
        with open(os.path.join(self.scratch, NOTIF + ".decisions.md"), "w", encoding="utf-8") as f:
            f.write("# Decisions\n")
        code, said = self.run_main("check", NOTIF)
        self.assertEqual(code, 1)
        self.assertTrue(any("neither cites it nor lists it" in line for line in said))

    def test_no_command_explains_itself(self):
        self.assertEqual(decisions.main([], say=lambda line: None), 2)


if __name__ == "__main__":
    unittest.main()
