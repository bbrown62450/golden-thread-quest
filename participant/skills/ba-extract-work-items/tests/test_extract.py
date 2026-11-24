"""Tests for extract.py. They contact nothing and write only to a scratch folder.

    python3 -m unittest discover -s participant/skills/ba-extract-work-items/tests -v
"""
import copy
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import extract   # noqa: E402
import items     # noqa: E402

SAMPLE, NOTIF = "sample-meeting", "notifications-meeting"


def source(name):
    return tuple(extract.read(os.path.join(extract.FOLDER, name + ext)) for ext in (".md", ".provenance.yaml", ".decisions.md"))


def built(name, change=None):
    """The work-items file build writes, after an optional change to a copy of the items."""
    extracted = copy.deepcopy(items.EXTRACTED[name])
    if change:
        change({i["id"]: i for i in extracted["items"]}, extracted)
    record_text = source(name)[0]
    return extract.render(name, extract.read_record(record_text), extracted, record_text)


def problems(name, text=None, record=None, provenance=None, decisions=None, same_file=False):
    r, p, d = source(name)
    return extract.check(built(name) if text is None else text, record or r, provenance or p, decisions or d, same_file)[0]


def edited(name, old, new):
    text = built(name)
    assert old in text, old
    return problems(name, text.replace(old, new, 1))


def has(got, words):
    return any(words in p for p in got)


def facts(name):
    return extract.check(built(name), *source(name))[1]


class Sound(unittest.TestCase):
    def test_both_meetings_as_extracted_pass(self):
        self.assertEqual(problems(SAMPLE), [])
        self.assertEqual(problems(NOTIF), [])

    def test_the_handed_in_files_are_what_the_code_writes(self):
        for name in (SAMPLE, NOTIF):
            self.assertEqual(extract.read(os.path.join(extract.FOLDER, name + ".work-items.md")), built(name), name)
        self.assertEqual(extract.read(extract.RULES), extract.rules_text())

    def test_every_line_of_each_record_is_cited_or_listed(self):
        for name in (SAMPLE, NOTIF):
            f = facts(name)
            self.assertEqual(sorted(f["cited"] | set(f["listed"])), sorted(f["record"]["lines"]), name)
            self.assertEqual(f["cited"] & set(f["listed"]), set())

    def test_every_item_has_a_title_and_one_sentence_of_intent(self):
        for name in (SAMPLE, NOTIF):
            for item in facts(name)["items"]:
                self.assertTrue(item["title"] and item["intent"].endswith("."), item["id"])
                self.assertEqual(item["intent"].count(". "), 0, item["id"])


class CitedLinesExist(unittest.TestCase):
    def test_every_item_cites_at_least_one_line_that_exists(self):
        for name in (SAMPLE, NOTIF):
            f = facts(name)
            for item in f["items"]:
                self.assertTrue(item["cites"], item["id"])
                self.assertTrue(all(c["u"] in f["record"]["lines"] for c in item["cites"]), item["id"])

    def test_an_item_citing_a_line_that_does_not_exist(self):
        got = edited(SAMPLE, "in U-0014: ", "in U-0041: ")
        self.assertIn("U-0041 is cited by W-03 and is not in the source record.", got)

    def test_an_identifier_written_in_a_note_is_checked_too(self):
        got = edited(SAMPLE, "which is W-02.", "which is W-02, see U-0099.")
        self.assertIn("U-0099 is cited by the file and is not in the source record.", got)

    def test_a_citation_into_another_transcript(self):
        got = edited(SAMPLE, "which is W-02.", "which is W-02, see tr-2026-11-04-notification-settings#U-0003.")
        self.assertIn("A line is cited from tr-2026-11-04-notification-settings, which is not this record.", got)

    def test_an_item_with_no_citation_at_all(self):
        def change(by_id, extracted):
            by_id["W-04"]["mentions"] = []
            extracted["no_item"].update({"U-0005": "x", "U-0006": "x"})
        got = problems(SAMPLE, built(SAMPLE, change))
        self.assertIn("W-04 cites no line of the source record. An item with no citation has no source.", got)

    def test_an_item_whose_only_citations_are_not_mentions(self):
        def change(by_id, extracted):
            by_id["W-06"]["mentions"] = []
        got = problems(SAMPLE, built(SAMPLE, change))
        self.assertIn("W-06 cites lines and none of them is a mention of the work itself.", got)

    def test_a_line_removed_from_the_record_is_reported_where_it_is_cited(self):
        record, provenance, decisions = source(SAMPLE)
        cut = record[:record.index('<a id="U-0014">')] + record[record.index('<a id="U-0015">'):]
        got = extract.check(built(SAMPLE), cut, provenance, decisions)[0]
        self.assertIn("U-0014 is cited by W-03 and is not in the source record.", got)

    def test_words_that_are_not_the_records(self):
        got = edited(SAMPLE, "\"Yes, email is required. Phone is optional.\"", "\"Yes, email and phone are required.\"")
        self.assertIn("W-01 quotes U-0004 in words that are not the record's.", got)

    def test_a_line_given_to_the_wrong_speaker(self):
        got = edited(SAMPLE, "Mention 1: Priya Natarajan, Product owner, in U-0002", "Mention 1: Dana Whitfield, Tester, in U-0002")
        self.assertTrue(has(got, "W-01 gives U-0002 to \"Dana Whitfield, Tester\". The record gives it to \"Priya Natarajan, Product owner\"."), got)


class WhatTheMeetingDidNotSay(unittest.TestCase):
    def test_every_item_answers_all_six_and_each_answer_is_cited_or_not_said(self):
        for name in (SAMPLE, NOTIF):
            for item in facts(name)["items"]:
                self.assertEqual(sorted(item["answers"]), sorted(label for _, label, _ in extract.ASKED), item["id"])
                for label, state in item["answers"].items():
                    answering = [c for c in item["cites"] if c["label"] == "Answers %s" % label.lower()]
                    self.assertEqual(bool(answering), state.startswith("said"), (item["id"], label))

    def test_every_item_has_at_least_one_thing_not_said(self):
        for name in (SAMPLE, NOTIF):
            for item in facts(name)["items"]:
                self.assertTrue(any(s.startswith("NOT SAID") for s in item["answers"].values()), item["id"])

    def test_an_owner_filled_in_with_no_line_is_reported(self):
        got = edited(SAMPLE, "- Owner: NOT SAID.", "- Owner: said. The developer.")
        self.assertIn("W-01 says the meeting stated its owner and cites no line that does. That is a gap filled in.", got)
        self.assertTrue(has(got, "W-01 says 1 of 6 were said, and its own lines give 2."))

    def test_one_of_the_six_left_out_is_reported(self):
        got = edited(SAMPLE, "- Due: NOT SAID.\n", "")
        self.assertIn("W-01 does not say whether the meeting stated its due.", got)

    def test_not_said_beside_a_line_that_answers_is_reported(self):
        got = edited(SAMPLE, "- Done: said. Stated as acceptance criteria: a guest can pay with a card and gets an email receipt.", "- Done: NOT SAID.")
        self.assertIn("W-01 says its done was not said and cites a line as answering it.", got)

    def test_the_count_said_is_the_count_of_answers(self):
        for name in (SAMPLE, NOTIF):
            for item in facts(name)["items"]:
                self.assertEqual(item["stated_count"], sum(1 for s in item["answers"].values() if s.startswith("said")), item["id"])

    def test_a_wrong_count_is_reported(self):
        got = edited(SAMPLE, "- Said, of 6: 1.", "- Said, of 6: 5.")
        self.assertIn("W-01 says 5 of 6 were said, and its own lines give 1.", got)

    def test_nothing_in_the_items_table_is_said_without_lines(self):
        for name in (SAMPLE, NOTIF):
            for item in items.EXTRACTED[name]["items"]:
                for key, answer in item["said"].items():
                    self.assertTrue(answer is None or (answer[0] and answer[1]), (item["id"], key))


class Merged(unittest.TestCase):
    def test_the_merged_items_cite_every_mention(self):
        text = built(SAMPLE)
        item = text[text.index("### W-01"):text.index("### W-02")]
        self.assertIn("### W-01 · decided · merged from 2 mentions", item)
        self.assertIn("- Mention 1: Priya Natarajan, Product owner, in U-0002", item)
        self.assertIn("- Mention 2: Priya Natarajan, Product owner, in U-0019", item)

    def test_three_mentions_are_one_item(self):
        text = built(SAMPLE)
        self.assertIn("### W-02 · DECIDED IN PART · merged from 3 mentions", text)
        self.assertEqual(text[text.index("### W-02"):text.index("### W-03")].count("\n- Mention 3: "), 1)

    def test_a_heading_that_claims_more_mentions_than_are_cited(self):
        got = edited(SAMPLE, "### W-03 · decided · 1 mention", "### W-03 · decided · merged from 2 mentions")
        self.assertIn("W-03 says \"merged from 2 mentions\" in its heading and cites 1.", got)

    def test_a_merged_item_that_lost_a_mention(self):
        got = edited(SAMPLE, "- Mention 2: Priya Natarajan, Product owner, in U-0019: \"Back to the story. Acceptance criteria: a guest can pay with a card, gets an email receipt, and is offered account linking once, after the order is placed.\"\n- Supports", "- Supports")
        self.assertTrue(has(got, "W-01 says \"merged from 2 mentions\" in its heading and cites 1."), got)

    def test_the_same_line_as_a_mention_of_two_items_is_reported(self):
        def change(by_id, extracted):
            by_id["W-04"]["mentions"] = [["U-0013", "U-0014"]]
            extracted["no_item"].update({"U-0005": "x", "U-0006": "x"})
        got = problems(SAMPLE, built(SAMPLE, change))
        self.assertTrue(has(got, "U-0014 is cited as a mention by W-03 and W-04. One piece of work is one item."), got)

    def test_a_line_shared_on_purpose_must_be_named_in_the_first_items_note(self):
        self.assertEqual(problems(SAMPLE), [])
        got = edited(SAMPLE, "- Note: The same line, U-0019, also states", "- Note: The same line also states")
        self.assertTrue(has(got, "U-0019 is cited as a mention by W-01 and W-02."), got)

    def test_an_intent_of_two_sentences_is_reported(self):
        got = edited(SAMPLE, "**Intent:** The phone number goes on the shipping label only, for the carrier, and is not used for marketing.",
                     "**Intent:** A customer's phone number is put on the shipping label. It is also sent to the carrier by text.")
        self.assertIn("W-03 states its intent in more than one sentence, or not as a sentence.", got)

    def test_two_items_with_one_title_are_reported(self):
        def change(by_id, extracted):
            by_id["W-04"]["title"] = by_id["W-03"]["title"]
        self.assertTrue(has(problems(SAMPLE, built(SAMPLE, change)), "Two items have the title"))

    def test_the_same_item_twice(self):
        text = built(SAMPLE)
        start, end = text.index("### W-06"), text.index("## Not created")
        got = problems(SAMPLE, text[:end] + text[start:end] + text[end:])
        self.assertIn("W-06 appears more than once.", got)

    def test_the_counts_in_each_file(self):
        self.assertIn("Items: 6. Merged from more than one mention: 2. Not created, for lack of support: 3.", built(SAMPLE))
        self.assertEqual(problems(SAMPLE, built(SAMPLE).replace("Items: 6. Merged", "Items: 7. Merged")), ["The counts in the file are not the counts of what is in it: 6 items, 2 merged, 3 not created."])


class HowSettled(unittest.TestCase):
    def test_every_item_rests_on_an_item_of_the_decisions_file_of_the_right_kind(self):
        for name in (SAMPLE, NOTIF):
            f = facts(name)
            for item in f["items"]:
                self.assertTrue(item["rests_on"], item["id"])
                for ref in item["rests_on"]:
                    self.assertIn(ref, f["decisions"], item["id"])

    def test_a_proposal_cannot_be_marked_decided(self):
        got = edited(NOTIF, "### W-06 · PROPOSED, NOT DECIDED · merged from 2 mentions", "### W-06 · decided · merged from 2 mentions")
        self.assertIn("W-06 is marked \"decided\" and rests on P-01, which is not that kind of item.", got)

    def test_an_open_matter_cannot_be_marked_decided(self):
        got = edited(NOTIF, "### W-11 · OPEN, NOT SETTLED · merged from 2 mentions", "### W-11 · decided · merged from 2 mentions")
        self.assertTrue(has(got, "W-11 is marked \"decided\" and rests on O-01"), got)

    def test_an_item_resting_on_a_reversed_decision_is_reported(self):
        got = edited(NOTIF, "- Rests on: D-06 of `notifications-meeting.decisions.md`\n- Mention 1: Noor Example", "- Rests on: D-01 of `notifications-meeting.decisions.md`\n- Mention 1: Noor Example")
        self.assertIn("W-01 rests on D-01, a decision that was reversed later in the meeting.", got)

    def test_resting_on_something_that_is_not_in_the_decisions_file(self):
        got = edited(SAMPLE, "- Rests on: D-06 of", "- Rests on: D-66 of")
        self.assertIn("W-03 rests on D-66, which is not in the decisions file.", got)

    def test_resting_on_a_decision_whose_lines_the_item_does_not_cite(self):
        got = edited(SAMPLE, "- Rests on: D-06 of", "- Rests on: D-03 of")
        self.assertIn("W-03 rests on D-03 and cites none of the lines that D-03 cites.", got)

    def test_a_plain_decided_heading_on_an_item_with_a_part_not_settled_is_reported(self):
        got = edited(SAMPLE, "### W-02 · DECIDED IN PART · merged from 3 mentions", "### W-02 · decided · merged from 3 mentions")
        self.assertIn("W-02 is marked \"decided\" and has a part listed as not settled. A heading must not read more settled than the item is.", got)

    def test_decided_in_part_with_nothing_listed_as_not_settled_is_reported(self):
        got = edited(SAMPLE, "### W-03 · decided · 1 mention", "### W-03 · DECIDED IN PART · 1 mention")
        self.assertIn("W-03 is marked \"DECIDED IN PART\" and has no part listed as not settled. A heading must not read more settled than the item is.", got)

    def test_a_plain_decided_heading_on_a_reopened_decision_is_reported(self):
        got = edited(NOTIF, "### W-04 · decided, REOPENED · 1 mention", "### W-04 · decided · 1 mention")
        self.assertIn("W-04 is marked \"decided\", and D-03 was reopened later in the meeting. The heading has to say so.", got)

    def test_reopened_on_a_decision_that_was_not_reopened_is_reported(self):
        got = edited(NOTIF, "### W-02 · decided · 1 mention", "### W-02 · decided, REOPENED · 1 mention")
        self.assertIn("W-02 is marked \"decided, REOPENED\", and D-02 was not reopened later in the meeting. The heading has to say so.", got)

    def test_a_remark_nobody_ruled_on_is_refused_and_kept_out_of_the_decided_item(self):
        text = built(NOTIF)
        self.assertIn("**It would have said:** Make the unsubscribe link work for a member who is signed out.", text)
        item = text[text.index("### W-03"):text.index("### W-04")]
        self.assertIn("**Intent:** Every email has an unsubscribe link, with no exceptions.", item)
        self.assertNotIn("U-0021", item)

    def test_an_item_with_no_mark(self):
        got = edited(SAMPLE, "### W-03 · decided · 1 mention", "### W-03 · agreed · 1 mention")
        self.assertIn("W-03 does not say how settled it is.", got)

    def test_the_proposed_and_open_items_say_so_in_capitals(self):
        text = built(NOTIF)
        for item_id in ("W-06", "W-07", "W-08"):
            self.assertIn("### %s · PROPOSED, NOT DECIDED" % item_id, text)
        self.assertIn("### W-11 · OPEN, NOT SETTLED", text)
        self.assertEqual(text.count("- Note: NOT DECIDED."), 3)


class Refused(unittest.TestCase):
    def test_each_refusal_cites_lines_and_says_why(self):
        for name in (SAMPLE, NOTIF):
            for r in facts(name)["refused"]:
                self.assertTrue(r["cites"] and r["why"], r["id"])

    def test_no_item_is_made_from_a_line_that_reads_like_an_instruction(self):
        for name, line in ((SAMPLE, "U-0016"), (NOTIF, "U-0030")):
            f = facts(name)
            self.assertFalse(any(c["u"] == line for i in f["items"] for c in i["cites"]), name)
            self.assertTrue(any(c["u"] == line for r in f["refused"] for c in r["cites"]), name)

    def test_an_item_made_from_an_instruction_like_line_is_reported(self):
        def change(by_id, extracted):
            by_id["W-04"]["mentions"] = [["U-0016"]]
            extracted["refused"] = [r for r in extracted["refused"] if r["id"] != "R-03"]
            extracted["no_item"].update({"U-0005": "x", "U-0006": "x", "U-0017": "x", "U-0018": "x"})
        got = problems(SAMPLE, built(SAMPLE, change))
        self.assertIn("W-04 is made from U-0016, which the decisions file lists as a line that reads like an instruction.", got)

    def test_the_reversed_placement_is_refused_and_kept_as_history(self):
        text = built(NOTIF)
        self.assertIn("**It would have said:** Put notification settings on the profile page.", text)
        item = text[text.index("### W-01"):text.index("### W-02")]
        self.assertIn("- History, first agreed for the profile page, and reversed: Kofi Example, Designer, in U-0002", item)
        self.assertNotIn("profile page", item.split("**Intent:**")[1].split("\n")[0])

    def test_the_time_out_is_refused_and_recorded_as_not_settled(self):
        text = built(SAMPLE)
        self.assertIn("**It would have said:** Add a time-out to the offer to link an order.", text)
        self.assertIn("- Not settled: Whether the offer times out if the customer never answers (O-01).", text)
        self.assertNotIn("time", text[text.index("### W-02"):].split("**Intent:**")[1].split("\n")[0])

    def test_a_refusal_with_no_reason_is_reported(self):
        got = edited(SAMPLE, "- Why no item: A question was asked and parked.", "- Remark: A question was asked and parked.")
        self.assertIn("R-01 does not say why no item was made.", got)

    def test_a_line_neither_cited_nor_listed_is_reported(self):
        got = edited(SAMPLE, "- U-0015 · Dana Whitfield: gives a contact number for test orders. No work is stated.\n", "")
        self.assertIn("U-0015 is in the source record, and the work-items file neither cites it nor lists it as giving no item.", got)

    def test_a_line_both_cited_and_listed_is_reported(self):
        got = edited(SAMPLE, "- U-0015 · Dana Whitfield:", "- U-0014 · Priya Natarajan: x.\n- U-0015 · Dana Whitfield:")
        self.assertIn("U-0014 is cited by an item and also listed as giving no item.", got)


class Separate(unittest.TestCase):
    def test_the_record_changed_after_ingestion_is_reported(self):
        record, provenance, decisions = source(SAMPLE)
        got = extract.check(built(SAMPLE), record + " ", provenance, decisions)[0]
        self.assertIn("The source record has been changed since it was ingested: its SHA-256 is not the one in its provenance file.", got)

    def test_items_written_into_the_record_are_reported(self):
        record, provenance, decisions = source(SAMPLE)
        got = extract.check(built(SAMPLE), record + "\n### W-01 · decided · 1 mention\n", provenance, decisions)[0]
        self.assertIn("The source record holds work items. They do not belong in the record.", got)

    def test_the_record_copied_into_the_items_file_is_reported(self):
        record = source(SAMPLE)[0]
        got = problems(SAMPLE, built(SAMPLE) + record[record.index('<a id="U-0001">'):record.index('<a id="U-0002">')])
        self.assertIn("The work-items file holds utterance headings, as if the record had been copied into it.", got)

    def test_one_file_for_both_is_reported(self):
        self.assertIn("The work-items file and the source record are the same file.", problems(SAMPLE, same_file=True))

    def test_a_file_made_from_another_version_of_the_record(self):
        got = edited(SAMPLE, "- source_sha256: `449f", "- source_sha256: `0000")
        self.assertIn("The work-items file was not made from the source record as it is now: the SHA-256 it states is not the record's.", got)

    def test_a_file_checked_against_the_other_meeting(self):
        got = extract.check(built(SAMPLE), *source(NOTIF))[0]
        self.assertTrue(has(got, "does not name the source record's transcript ID, tr-2026-11-04-notification-settings"), got)

    def test_build_writes_one_file_and_never_the_record_or_the_decisions(self):
        scratch = tempfile.mkdtemp(prefix="gtq-items-")
        self.addCleanup(shutil.rmtree, scratch, True)
        for ext in (".md", ".provenance.yaml", ".decisions.md"):
            shutil.copy(os.path.join(extract.FOLDER, SAMPLE + ext), scratch)
        before = {n: extract.read(os.path.join(scratch, n)) for n in os.listdir(scratch)}
        said = []
        self.assertEqual(extract.main(["build", SAMPLE, "--folder", scratch], say=said.append), 0)
        self.assertEqual({n: extract.read(os.path.join(scratch, n)) for n in before}, before)
        self.assertEqual(sorted(set(os.listdir(scratch)) - set(before)), [SAMPLE + ".work-items.md"])
        self.assertEqual(said[-1], "The source record was not changed. Nothing was sent to any tracker.")


class NothingIsSent(unittest.TestCase):
    def test_no_module_for_connecting_is_loaded_by_a_build_and_a_check(self):
        code = ("import sys, tempfile, shutil, os; sys.path.insert(0, %r); import extract; d = tempfile.mkdtemp()\n"
                "for e in ('.md', '.provenance.yaml', '.decisions.md'): shutil.copy(os.path.join(extract.FOLDER, 'sample-meeting' + e), d)\n"
                "extract.main(['build', 'sample-meeting', '--folder', d], say=lambda l: None); extract.main(['check', 'sample-meeting', '--folder', d], say=lambda l: None); shutil.rmtree(d)\n"
                "print(sorted(m for m in sys.modules if m.split('.')[0] in ('socket', 'ssl', 'http', 'urllib', 'smtplib', 'ftplib', 'subprocess')))" % os.path.dirname(HERE))
        done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
        self.assertEqual((done.returncode, done.stdout.strip()), (0, "[]"), done.stderr)

    def test_the_file_says_nothing_was_created_in_a_tracker(self):
        self.assertIn("**Nothing here was created\nin any tracker**", built(SAMPLE))


class Stretch(unittest.TestCase):
    def test_the_table_ranks_items_by_how_much_was_said(self):
        text = built(SAMPLE)
        table = text[text.index("| Item | Title |"):text.index("Items: 6.")]
        counts = [int(row.split("|")[4]) for row in table.splitlines()[2:] if row.startswith("| W-")]
        self.assertEqual(counts, sorted(counts, reverse=True))
        self.assertEqual(len(counts), 6)

    def test_an_item_whose_lines_are_all_one_speakers_is_flagged(self):
        text = built(SAMPLE)
        self.assertIn("- ONE SPEAKER: every line cited is Marcus Oyelaran's.", text[text.index("### W-06"):text.index("## Not created")])
        self.assertIn("| W-06 | Size it, once that is settled | follow-up | 2 | 1 | YES: Marcus Oyelaran |", text)

    def test_the_flag_is_on_every_one_speaker_item_and_on_no_other(self):
        for name in (SAMPLE, NOTIF):
            f = facts(name)
            for item in f["items"]:
                speakers = {f["record"]["lines"][c["u"]]["speaker"] for c in item["cites"]}
                self.assertEqual(item["one_speaker"], len(speakers) == 1, item["id"])

    def test_a_missing_flag_is_reported(self):
        got = edited(SAMPLE, "- ONE SPEAKER: every line cited is Marcus Oyelaran's. Nobody else in the meeting is on record about it.\n", "")
        self.assertIn("W-06 cites one speaker only and is not flagged.", got)

    def test_a_wrong_flag_is_reported(self):
        got = edited(SAMPLE, "- Said, of 6: 0.", "- Said, of 6: 0.\n- ONE SPEAKER: every line cited is Priya Natarajan's.")
        self.assertTrue(has(got, "is flagged as one speaker's and cites more than one"), got)


class Rules(unittest.TestCase):
    def test_the_rules_say_how_an_item_is_recognized_how_one_is_told_from_two_and_what_is_left_out(self):
        text = extract.rules_text()
        for heading in ("## 1. How an item is recognized", "## 3. One item or two", "## 5. What is left out", "## 4. What the meeting did not say"):
            self.assertIn(heading, text)
        for _, label, _ in extract.ASKED:
            self.assertIn("| %s |" % label, text)

    def test_the_rules_quote_no_line_of_either_meeting(self):
        text = extract.rules_text()
        for name in (SAMPLE, NOTIF):
            for line in extract.read_record(source(name)[0])["lines"].values():
                if len(line["words"]) > 25:
                    self.assertNotIn(line["words"], text)


class Command(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.mkdtemp(prefix="gtq-items-")
        self.addCleanup(shutil.rmtree, self.scratch, True)
        for ext in (".md", ".provenance.yaml", ".decisions.md"):
            shutil.copy(os.path.join(extract.FOLDER, NOTIF + ext), self.scratch)

    def run_main(self, *argv):
        said = []
        return extract.main(list(argv) + ["--folder", self.scratch], say=said.append), said

    def test_build_then_check_passes_with_exit_code_0(self):
        self.assertEqual(self.run_main("build", NOTIF)[0], 0)
        code, said = self.run_main("check", NOTIF)
        self.assertEqual(code, 0)
        self.assertIn("Items with no citation: 0.", said)
        self.assertTrue(said[-1].startswith("CHECK PASSED."))

    def test_check_fails_with_exit_code_1_and_names_the_identifier(self):
        self.run_main("build", NOTIF)
        path = os.path.join(self.scratch, NOTIF + ".work-items.md")
        text = extract.read(path).replace("in U-0005: ", "in U-0055: ")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        code, said = self.run_main("check", NOTIF)
        self.assertEqual(code, 1)
        self.assertIn("PROBLEM: U-0055 is cited by W-02 and is not in the source record.", said)

    def test_check_without_a_work_items_file_does_not_pass(self):
        self.assertEqual(self.run_main("check", NOTIF)[0], 1)

    def test_an_empty_work_items_file_does_not_pass(self):
        with open(os.path.join(self.scratch, NOTIF + ".work-items.md"), "w", encoding="utf-8") as f:
            f.write("# Candidate work items\n")
        code, said = self.run_main("check", NOTIF)
        self.assertEqual(code, 1)
        self.assertTrue(any("has no items that could be read" in line for line in said))

    def test_a_meeting_with_no_decisions_file_is_not_done(self):
        os.remove(os.path.join(self.scratch, NOTIF + ".decisions.md"))
        self.assertEqual(self.run_main("build", NOTIF)[0], 2)

    def test_a_meeting_with_no_items_in_the_table_is_not_done(self):
        for ext in (".md", ".provenance.yaml", ".decisions.md"):
            shutil.copy(os.path.join(self.scratch, NOTIF + ext), os.path.join(self.scratch, "other" + ext))
        self.assertEqual(self.run_main("build", "other")[0], 2)

    def test_no_command_explains_itself(self):
        self.assertEqual(extract.main([], say=lambda line: None), 2)


if __name__ == "__main__":
    unittest.main()
