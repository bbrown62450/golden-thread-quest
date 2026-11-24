"""Tests for story.py. They contact nothing and write only to a scratch folder.

    python3 -m unittest discover -s participant/skills/ba-write-story/tests -v
"""
import copy
import os
import shutil
import subprocess
import sys
import tempfile
import types
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import story        # noqa: E402
import story_001    # noqa: E402

NAMES = ("SOURCE", "WORK_ITEM", "OWNER", "OUT_OF_SCOPE", "STORY", "IN_SCOPE", "GLOSSARY", "CRITERIA", "DEPENDENCIES", "QUESTIONS", "DEFINITION_OF_DONE", "TAKEN_AS_GIVEN", "TEST_SETUP", "NOT_USED")
T = story.TRANSCRIPTS
RECORD, PROVENANCE, DECISIONS, ITEMS = (story.read(os.path.join(T, "sample-meeting" + ext)) for ext in (".md", ".provenance.yaml", ".decisions.md", ".work-items.md"))


def built(change=None):
    """The story file build writes, after an optional change to a copy of the content."""
    content = types.SimpleNamespace(**{name: copy.deepcopy(getattr(story_001, name)) for name in NAMES})
    if change:
        change(content)
    return story.render(content, story.read_record(RECORD), RECORD)


def problems(text=None, record=None, provenance=None):
    return story.check(built() if text is None else text, record or RECORD, provenance or PROVENANCE, DECISIONS, ITEMS)[0]


def edited(old, new):
    text = built()
    assert old in text, old
    return problems(text.replace(old, new, 1))


def has(got, words):
    return any(words in p for p in got)


def criterion(content, name):
    return next(c for c in content.CRITERIA if c["id"] == name)


class Sound(unittest.TestCase):
    def test_the_story_as_written_passes(self):
        self.assertEqual(problems(), [])

    def test_the_handed_in_files_are_what_the_code_writes(self):
        self.assertEqual(story.read(os.path.join(story.STORIES, "story-001.md")), built())
        self.assertEqual(story.read(os.path.join(story.STORIES, "story-standard.md")), story.standard_text())

    def test_what_is_read_back_is_what_was_written(self):
        facts = story.check(built(), RECORD, PROVENANCE, DECISIONS, ITEMS)[1]
        self.assertEqual([c["id"] for c in facts["criteria"]], [c["id"] for c in story_001.CRITERIA])
        self.assertEqual([c["basis"] for c in facts["criteria"]], [c["basis"] for c in story_001.CRITERIA])
        self.assertEqual(facts["defined"], [g[0] for g in story_001.GLOSSARY])
        self.assertEqual((facts["in"], facts["out"], facts["deps"]), (len(story_001.IN_SCOPE), len(story_001.OUT_OF_SCOPE), len(story_001.DEPENDENCIES)))


class Sections(unittest.TestCase):
    def test_every_required_section_is_there_in_order(self):
        text = built()
        places = [text.index("\n## %s\n" % title) for title in story.SECTIONS]
        self.assertEqual(places, sorted(places))

    def test_each_missing_section_is_reported(self):
        text = built()
        for title in story.SECTIONS:
            start = text.index("\n## %s\n" % title)
            end = text.find("\n## ", start + 1)
            got = problems(text[:start] + (text[end:] if end != -1 else "\n"))
            self.assertIn("The story has no section \"%s\"." % title, got, title)

    def test_an_empty_section_is_reported(self):
        text = built()
        start, end = text.index("\n## In scope\n"), text.index("\n## Words this story defines\n")
        self.assertIn("The section \"In scope\" is empty.", problems(text[:start] + "\n## In scope\n" + text[end:]))

    def test_sections_out_of_order_are_reported(self):
        text = built()
        a, b, c = text.index("\n## Out of scope\n"), text.index("\n## In scope\n"), text.index("\n## Words this story defines\n")
        self.assertIn("The story's sections are not in the order the standard gives.", problems(text[:a] + text[b:c] + text[a:b] + text[c:]))

    def test_out_of_scope_comes_before_in_scope(self):
        text = built()
        self.assertLess(text.index("\n## Out of scope\n"), text.index("\n## In scope\n"))


class UserAndValue(unittest.TestCase):
    def test_the_user_and_the_value_are_named_and_cited(self):
        text = built()
        self.assertIn("- User: A customer who does not have an account.", text)
        self.assertIn("- Value: They can buy without making one.", text)
        self.assertIn("- Source for the user: Priya Natarajan, Product owner, in U-0002", text)
        self.assertIn("- Source for the value: Priya Natarajan, Product owner, in U-0002", text)

    def test_a_user_who_is_only_a_user_is_reported(self):
        self.assertIn("The story does not name the user.", edited("- User: A customer who does not have an account.", "- User: A user."))

    def test_a_vague_value_is_reported(self):
        got = edited("- Value: They can buy without making one.", "- Value: They get a better and faster checkout.")
        self.assertTrue(has(got, "The story's value uses a word nobody can check: faster, better."), got)

    def test_a_value_with_no_source_is_reported(self):
        def change(content):
            content.STORY["value"] = (content.STORY["value"][0], [])
        self.assertIn("The story's value cites no line of the meeting.", problems(built(change)))

    def test_the_story_says_what_the_meeting_did_not_say_about_the_value(self):
        self.assertIn("- Not said: The meeting said what the customer can then do. It did not say why that matters to the business", built())


class Scope(unittest.TestCase):
    def test_both_lists_have_entries(self):
        facts = story.check(built(), RECORD, PROVENANCE, DECISIONS, ITEMS)[1]
        self.assertGreater(facts["in"], 0)
        self.assertGreater(facts["out"], 0)

    def test_an_out_of_scope_list_with_nothing_in_it_is_reported(self):
        def change(content):
            content.OUT_OF_SCOPE = []
        self.assertIn("\"Out of scope\" lists nothing.", problems(built(change)))

    def test_an_in_scope_list_with_nothing_in_it_is_reported(self):
        def change(content):
            content.IN_SCOPE = []
        self.assertTrue(has(problems(built(change)), "\"In scope\" lists nothing."))

    def test_an_out_of_scope_entry_with_no_reason_is_reported(self):
        got = edited("   - Why it is out: It was asked about and parked. Nobody said one should be built.\n", "")
        self.assertIn("Out-of-scope entry 2 does not say why it is out.", got)

    def test_an_out_of_scope_entry_that_went_nowhere_known_is_reported(self):
        got = edited("   - Where it went: W-03\n", "   - Where it went: W-33\n")
        self.assertIn("Out-of-scope entry 3 says it went to W-33, which is in neither the work-items file nor the decisions file.", got)

    def test_an_out_of_scope_entry_that_does_not_say_where_it_went_is_reported(self):
        got = edited("   - Where it went: W-03\n", "")
        self.assertIn("Out-of-scope entry 3 does not say where it went.", got)

    def test_every_place_an_out_of_scope_entry_went_exists(self):
        known = story.item_ids(DECISIONS) | story.item_ids(ITEMS)
        for item in story_001.OUT_OF_SCOPE:
            for ref in item["where"] or []:
                self.assertIn(ref, known)


class Criteria(unittest.TestCase):
    def test_the_criteria_are_numbered_in_order_with_none_missing(self):
        facts = story.check(built(), RECORD, PROVENANCE, DECISIONS, ITEMS)[1]
        self.assertEqual([c["id"] for c in facts["criteria"]], ["AC-%02d" % n for n in range(1, len(story_001.CRITERIA) + 1)])

    def test_a_gap_in_the_numbering_is_reported(self):
        self.assertTrue(has(edited("### AC-05 · SAID", "### AC-15 · SAID"), "are not numbered AC-01, AC-02 and so on"))

    def test_a_criterion_with_no_number_is_reported(self):
        self.assertTrue(has(edited("### AC-05 · SAID", "### Payment · SAID"), "are not numbered AC-01, AC-02 and so on"))

    def test_two_criteria_with_one_number_are_reported(self):
        self.assertTrue(has(edited("### AC-05 · SAID", "### AC-04 · SAID"), "are not numbered AC-01, AC-02 and so on"))

    def test_no_criteria_at_all_is_reported(self):
        def change(content):
            content.CRITERIA = []
            content.QUESTIONS = [(q, text, [], origin) for q, text, _, origin in content.QUESTIONS]
        self.assertTrue(has(problems(built(change)), "The story has no acceptance criteria that could be read."))

    def test_every_criterion_has_one_given_one_when_and_one_then(self):
        for c in story.check(built(), RECORD, PROVENANCE, DECISIONS, ITEMS)[1]["criteria"]:
            self.assertEqual((len(c["given"]), len(c["when"]), len(c["then"])), (1, 1, 1), c["id"])

    def test_a_criterion_with_no_then_is_reported(self):
        got = edited("- Then: the order is not placed.\n", "")
        self.assertIn("AC-03 has 0 \"Then\" lines. A criterion has exactly one.", got)

    def test_a_criterion_with_two_thens_is_reported(self):
        got = edited("- Then: the order is not placed.\n", "- Then: the order is not placed.\n- Then: a message is shown.\n")
        self.assertIn("AC-03 has 2 \"Then\" lines. A criterion has exactly one.", got)

    def test_a_then_of_two_sentences_is_reported(self):
        got = edited("- Then: the order is not placed.", "- Then: the order is not placed. The basket is emptied.")
        self.assertIn("AC-03: its \"Then\" is not one sentence.", got)


class VagueWords(unittest.TestCase):
    def test_no_criterion_uses_an_undefined_vague_word(self):
        defined = [g[0] for g in story_001.GLOSSARY]
        for c in story_001.CRITERIA:
            self.assertEqual(story.vague_in(" ".join((c["given"], c["when"], c["then"])), defined), [], c["id"])

    def test_each_of_the_quests_three_words_is_reported(self):
        for word in ("fast", "easy", "intuitive"):
            got = edited("- Then: the order is not placed.", "- Then: the order is not placed and the page is %s." % word)
            self.assertIn("AC-03 uses the word \"%s\", which the story does not define. A tester cannot check it." % word, got)

    def test_a_word_is_matched_whole_and_in_any_case(self):
        self.assertEqual(story.vague_in("The breakfast order is steadfast", []), [])
        self.assertEqual(story.vague_in("It is Fast.", []), ["fast"])
        self.assertEqual(story.vague_in("a user-friendly page", []), ["user-friendly"])

    def test_words_the_product_shows_in_quotes_are_not_counted(self):
        self.assertEqual(story.vague_in("the message \"Enter a valid email address\" is shown", []), [])

    def test_valid_is_allowed_only_because_the_story_defines_it(self):
        self.assertIn("valid", [g[0] for g in story_001.GLOSSARY])

        def change(content):
            content.GLOSSARY = [g for g in content.GLOSSARY if g[0] != "valid"]
        self.assertTrue(has(problems(built(change)), "AC-10 uses the word \"valid\", which the story does not define. A tester cannot check it."))

    def test_should_and_soon_are_on_the_list(self):
        self.assertEqual(story.vague_in("the receipt should arrive soon", []), ["soon", "should"])

    def test_every_amount_of_time_in_a_criterion_is_a_number(self):
        waits = {g[0]: g[1] for g in story_001.GLOSSARY}
        self.assertIn("5 minutes", waits["receipt wait"])
        self.assertIn("10 seconds", waits["not placed"])


class Basis(unittest.TestCase):
    def test_every_criterion_is_said_or_assumed_and_carries_what_that_needs(self):
        for c in story.check(built(), RECORD, PROVENANCE, DECISIONS, ITEMS)[1]["criteria"]:
            if c["basis"] == "SAID":
                self.assertTrue(c["cites"] and not c["confirm"] and not c["question"], c["id"])
            else:
                self.assertEqual(c["basis"], "ASSUMED")
                self.assertTrue(c["confirm"] and c["question"] and not c["cites"], c["id"])

    def test_a_said_criterion_with_no_citation_is_reported(self):
        def change(content):
            criterion(content, "AC-07")["lines"] = []
            content.NOT_USED.update({"U-0009": "x", "U-0010": "x"})
            content.IN_SCOPE = [e for e in content.IN_SCOPE if "AC-07" not in e[2]]
        self.assertIn("AC-07 is marked SAID and cites no line of the meeting.", problems(built(change)))

    def test_an_assumption_relabelled_as_said_is_reported(self):
        got = edited("### AC-09 · ASSUMED", "### AC-09 · SAID")
        self.assertIn("AC-09 is marked SAID and cites no line of the meeting.", got)
        self.assertIn("AC-09 is marked SAID and is also written as an assumption. It is one or the other.", got)

    def test_an_assumption_given_a_source_line_is_reported(self):
        got = edited("- ASSUMPTION, to be confirmed by: the product owner.\n- Answers the open question: Q-01.",
                     "- Source: Priya Natarajan, Product owner, in U-0004: \"Yes, email is required. Phone is optional.\"\n- ASSUMPTION, to be confirmed by: the product owner.\n- Answers the open question: Q-01.")
        self.assertIn("AC-09 is marked ASSUMED and cites a line of the meeting as its source. It is one or the other.", got)

    def test_an_assumption_with_nobody_to_confirm_it_is_reported(self):
        got = edited("- ASSUMPTION, to be confirmed by: the product owner.\n- Answers the open question: Q-01.", "- Answers the open question: Q-01.")
        self.assertIn("AC-09 is marked ASSUMED and does not say who is to confirm it.", got)

    def test_an_assumption_with_no_question_is_reported(self):
        got = edited("- Answers the open question: Q-01.\n", "")
        self.assertIn("AC-09 is marked ASSUMED and does not name the open question it answers.", got)

    def test_an_assumption_answering_a_question_that_is_not_listed_is_reported(self):
        got = edited("- Answers the open question: Q-01.", "- Answers the open question: Q-41.")
        self.assertIn("AC-09 answers Q-41, which is not in the list of open questions.", got)

    def test_a_question_that_does_not_list_the_criterion_back_is_reported(self):
        got = edited("- Answers the open question: Q-01.", "- Answers the open question: Q-02.")
        self.assertIn("AC-09 answers Q-02, and Q-02 does not list AC-09 among the criteria that depend on it.", got)

    def test_a_criterion_with_no_basis_is_reported(self):
        self.assertIn("AC-05 does not say whether it is SAID or ASSUMED.", edited("### AC-05 · SAID", "### AC-05 · AGREED"))

    def test_the_count_at_the_head_is_the_count_of_the_criteria(self):
        said = sum(1 for c in story_001.CRITERIA if c["basis"] == "SAID")
        self.assertIn("Acceptance criteria: %d. SAID by the meeting: %d. ASSUMED by the writer: %d." % (len(story_001.CRITERIA), said, len(story_001.CRITERIA) - said), built())

    def test_a_wrong_count_at_the_head_is_reported(self):
        got = edited("SAID by the meeting: ", "SAID by the meeting: 1")
        self.assertTrue(has(got, "The count at the head of the story is not the count of its criteria"), got)


class Dependencies(unittest.TestCase):
    def test_none_is_accepted(self):
        def change(content):
            content.DEPENDENCIES = []
        text = built(change).replace("## Dependencies\n\n", "## Dependencies\n\nNone.\n")
        self.assertFalse(has(problems(text), "Dependencies"))

    def test_neither_a_list_nor_none_is_reported(self):
        def change(content):
            content.DEPENDENCIES = []
        text = built(change).replace("## Dependencies\n\n", "## Dependencies\n\nTo be worked out.\n")
        self.assertIn("\"Dependencies\" neither lists one nor says None.", problems(text))

    def test_a_dependency_with_no_basis_is_reported(self):
        got = edited("It did not say how. ASSUMED.", "It did not say how.")
        self.assertTrue(has(got, "A dependency does not say whether it is SAID or ASSUMED"), got)


class Source(unittest.TestCase):
    def test_every_cited_identifier_exists(self):
        facts = story.check(built(), RECORD, PROVENANCE, DECISIONS, ITEMS)[1]
        self.assertTrue(facts["cites"])
        self.assertTrue(all(c["u"] in facts["record"]["lines"] for c in facts["cites"]))

    def test_an_identifier_that_does_not_exist_is_reported(self):
        got = edited("in U-0019: ", "in U-0091: ")
        self.assertIn("U-0091 is cited and is not in the source record.", got)

    def test_an_identifier_written_in_plain_text_is_checked_too(self):
        got = edited("- Not said: The meeting said", "- Not said: See U-0077. The meeting said")
        self.assertIn("U-0077 is cited and is not in the source record.", got)

    def test_a_citation_into_another_transcript_is_reported(self):
        got = edited("- Not said: The meeting said", "- Not said: See tr-2026-11-04-notification-settings#U-0003. The meeting said")
        self.assertIn("A line is cited from tr-2026-11-04-notification-settings, which is not this record.", got)

    def test_words_that_are_not_the_records_are_reported(self):
        got = edited("\"Yes, email is required. Phone is optional.\"", "\"Yes, email and phone are required.\"")
        self.assertIn("U-0004 is quoted in words that are not the record's.", got)

    def test_a_line_given_to_the_wrong_speaker_is_reported(self):
        got = edited("- Source: Priya Natarajan, Product owner, in U-0019", "- Source: Marcus Oyelaran, Developer, in U-0019")
        self.assertTrue(has(got, "U-0019 is given to \"Marcus Oyelaran, Developer\". The record gives it to \"Priya Natarajan, Product owner\"."), got)

    def test_a_line_removed_from_the_record_is_reported(self):
        cut = RECORD[:RECORD.index('<a id="U-0019">')] + RECORD[RECORD.index('<a id="U-0020">'):]
        self.assertIn("U-0019 is cited and is not in the source record.", problems(record=cut))

    def test_the_record_changed_after_ingestion_is_reported(self):
        self.assertIn("The source record has been changed since it was ingested: its SHA-256 is not the one in its provenance file.", problems(record=RECORD + " "))

    def test_the_source_section_lists_exactly_the_lines_cited(self):
        facts = story.check(built(), RECORD, PROVENANCE, DECISIONS, ITEMS)[1]
        used = sorted({c["u"] for c in facts["cites"]})
        self.assertIn("The story cites %d of its lines: %s." % (len(used), ", ".join(used)), built())

    def test_a_source_section_that_leaves_a_line_out_is_reported(self):
        got = edited(", U-0014, U-0019", ", U-0019")
        self.assertTrue(has(got, "The \"Source\" section does not list exactly the lines the story cites"), got)

    def test_a_work_item_that_does_not_exist_is_reported(self):
        self.assertIn("The story does not name a work item that is in the work-items file.", edited("- work_item: W-01 of", "- work_item: W-91 of"))

    def test_every_line_of_the_record_is_cited_or_listed_as_not_used(self):
        facts = story.check(built(), RECORD, PROVENANCE, DECISIONS, ITEMS)[1]
        cited = {c["u"] for c in facts["cites"]}
        self.assertEqual(sorted(cited | set(facts["not_used"])), sorted(facts["record"]["lines"]))
        self.assertEqual(cited & set(facts["not_used"]), set())

    def test_a_line_neither_cited_nor_listed_is_reported(self):
        got = edited("- U-0015 · Dana Whitfield: gives a contact number for carriers about test orders. Nothing in this story uses it.\n", "")
        self.assertIn("U-0015 is in the source record, and the story neither cites it nor lists it as not used.", got)

    def test_a_line_both_cited_and_listed_is_reported(self):
        got = edited("- U-0015 · Dana Whitfield:", "- U-0014 · Priya Natarajan: x.\n- U-0015 · Dana Whitfield:")
        self.assertIn("U-0014 is cited by the story and also listed as not used.", got)

    def test_the_rule_that_was_missing_from_the_first_version_is_a_criterion(self):
        c = criterion(story_001, "AC-07")
        self.assertEqual((c["basis"], c["lines"]), ("SAID", ["U-0009", "U-0010"]))
        self.assertIn("that order is not in the list", c["then"])

    def test_build_never_writes_to_the_record(self):
        scratch = tempfile.mkdtemp(prefix="gtq-story-")
        self.addCleanup(shutil.rmtree, scratch, True)
        before = story.read(os.path.join(T, "sample-meeting.md"))
        said = []
        self.assertEqual(story.main(["build", "--stories", scratch], say=said.append), 0)
        self.assertEqual(story.read(os.path.join(T, "sample-meeting.md")), before)
        self.assertEqual(os.listdir(scratch), ["story-001.md"])
        self.assertEqual(story.main(["check", "--stories", scratch], say=said.append), 0)


class LeaningOnDefinedWords(unittest.TestCase):
    def test_each_said_criterion_names_the_assumed_words_it_uses(self):
        glossary = [(g[0], g[2]) for g in story_001.GLOSSARY]
        for c in story.check(built(), RECORD, PROVENANCE, DECISIONS, ITEMS)[1]["criteria"]:
            if c["basis"] == "SAID":
                words = story.assumed_words(" ".join(c["given"] + c["when"] + c["then"]), glossary)
                self.assertEqual([w.strip() for w in c["leans"].split(",")], words or ["none"], c["id"])

    def test_not_placed_is_not_also_counted_as_placed(self):
        glossary = [("placed", "assumed"), ("not placed", "assumed"), ("receipt", "assumed"), ("receipt wait", "assumed")]
        self.assertEqual(story.assumed_words("the order is not placed", glossary), ["not placed"])
        self.assertEqual(story.assumed_words("once the receipt wait has passed, a receipt is there", glossary), ["receipt", "receipt wait"])

    def test_a_word_left_off_that_list_is_reported(self):
        got = edited("These words in it are defined by the writer: guest, placed, complete the checkout, pay with, accepted test card.", "These words in it are defined by the writer: guest, complete the checkout, pay with, accepted test card.")
        self.assertTrue(has(got, "AC-01 says the writer defined \"guest, complete the checkout, pay with, accepted test card\" in it. By the story's own list of words it is: guest, placed, complete the checkout, pay with, accepted test card."), got)

    def test_a_said_criterion_without_that_line_is_reported(self):
        got = edited("- The requirement is the meeting's. These words in it are defined by the writer: guest, placed, complete the checkout, pay with, accepted test card.\n", "")
        self.assertIn("AC-01 is marked SAID and does not say which of its words the writer defined.", got)

    def test_the_head_counts_how_many_said_criteria_lean_on_a_defined_word(self):
        self.assertIn("Of the 8 SAID, 8 use a word whose meaning the writer had to define.", built())
        got = edited("Of the 8 SAID, 8 use", "Of the 8 SAID, 2 use")
        self.assertIn("The head of the story does not say that 8 of its 8 SAID criteria use a word the writer defined.", got)

    def test_a_word_marked_said_in_the_list_is_not_counted_as_assumed(self):
        self.assertEqual(story.assumed_words("a guest is placed", [("guest", "said"), ("placed", "assumed")]), ["placed"])


class InScopeIsTested(unittest.TestCase):
    def test_every_in_scope_entry_names_criteria_that_exist(self):
        ids = [c["id"] for c in story_001.CRITERIA]
        for text, lines, tested in story_001.IN_SCOPE:
            self.assertTrue(tested and lines, text)
            for ac in tested:
                self.assertIn(ac, ids)

    def test_an_entry_that_names_no_criterion_is_reported(self):
        got = edited("   - Tested by: AC-07\n", "")
        self.assertIn("In-scope entry 5 does not say which criteria test it.", got)

    def test_an_entry_tested_by_a_criterion_that_does_not_exist_is_reported(self):
        got = edited("   - Tested by: AC-07\n", "   - Tested by: AC-70\n")
        self.assertIn("In-scope entry 5 says it is tested by AC-70, which is not a criterion of this story.", got)

    def test_an_assumed_criterion_listed_as_if_it_were_the_meetings_is_reported(self):
        got = edited("   - Tested by: AC-03\n   - And, on the writer's assumptions, by: AC-09, AC-10, AC-11\n", "   - Tested by: AC-03, AC-09\n   - And, on the writer's assumptions, by: AC-10, AC-11\n")
        self.assertTrue(has(got, "In-scope entry 2 lists AC-09 on the wrong line."), got)

    def test_every_in_scope_entry_is_tested_by_at_least_one_said_criterion(self):
        basis = {c["id"]: c["basis"] for c in story_001.CRITERIA}
        for text, _, tested in story_001.IN_SCOPE:
            self.assertTrue(any(basis[ac] == "SAID" for ac in tested), text)

    def test_the_removed_acceptance_criterion_is_named_at_the_head_of_the_story(self):
        head = built().split("## The story")[0]
        self.assertIn("**One of the product owner's three acceptance criteria, the linking offer, is not in this story.**", head)

    def test_every_criterion_tests_some_in_scope_entry(self):
        tested = {ac for _, _, acs in story_001.IN_SCOPE for ac in acs}
        self.assertEqual(sorted(tested), [c["id"] for c in story_001.CRITERIA])

    def test_no_test_data_is_reported(self):
        def change(content):
            content.TEST_SETUP = []
        self.assertTrue(has(problems(built(change)), "\"Test set-up\" gives no data."))


class Stretch(unittest.TestCase):
    def test_the_definition_of_done_is_a_checklist_apart_from_the_criteria(self):
        text = built()
        done = text[text.index("\n## Definition of done\n"):text.index("\n## Source\n")]
        self.assertEqual(done.count("\n- [ ] "), len(story_001.DEFINITION_OF_DONE))
        self.assertNotIn("### AC-", done)

    def test_a_criterion_put_in_the_definition_of_done_is_reported(self):
        got = edited("- [ ] Every acceptance criterion above passes on staging.", "### AC-13 · SAID\n\n- [ ] Every acceptance criterion above passes on staging.")
        self.assertIn("The definition of done and the acceptance criteria are mixed together.", got)

    def test_no_checklist_is_reported(self):
        def change(content):
            content.DEFINITION_OF_DONE = []
        self.assertTrue(has(problems(built(change)), "\"Definition of done\" has no checklist."))

    def test_every_assumption_is_tied_to_an_open_question_and_back(self):
        questions = {q: acs for q, _, acs, _ in story_001.QUESTIONS}
        for c in story_001.CRITERIA:
            if c["basis"] == "ASSUMED":
                self.assertIn(c["id"], questions[c["question"]])

    def test_questions_from_the_decisions_file_name_open_items_that_exist(self):
        known = story.item_ids(DECISIONS)
        origins = [origin for _, _, _, origin in story_001.QUESTIONS if origin]
        self.assertTrue(origins)
        for origin in origins:
            self.assertIn(origin, known)
            self.assertTrue(origin.startswith("O-"))

    def test_a_question_naming_a_criterion_that_does_not_exist_is_reported(self):
        got = edited("| AC-09 |", "| AC-77 |")
        self.assertTrue(has(got, "names AC-77, which is not a criterion of this story."), got)


class Standard(unittest.TestCase):
    def test_the_standard_says_what_makes_a_criterion_testable_and_lists_the_words(self):
        text = story.standard_text()
        self.assertIn("## 3. What makes a criterion testable", text)
        for word in ("fast", "easy", "intuitive"):
            self.assertIn(word, text[text.index("## 4."):text.index("## 5.")])
        for title in story.SECTIONS:
            self.assertIn("| %s |" % title, text)

    def test_the_standard_quotes_no_long_line_of_the_meeting(self):
        text = story.standard_text()
        for line in story.read_record(RECORD)["lines"].values():
            if len(line["words"]) > 30:
                self.assertNotIn(line["words"], text)


class Command(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.mkdtemp(prefix="gtq-story-")
        self.addCleanup(shutil.rmtree, self.scratch, True)

    def run_main(self, *argv):
        said = []
        return story.main(list(argv) + ["--stories", self.scratch], say=said.append), said

    def test_check_passes_with_exit_code_0(self):
        self.run_main("build")
        code, said = self.run_main("check")
        self.assertEqual(code, 0)
        self.assertTrue(said[-1].startswith("CHECK PASSED."))

    def test_check_fails_with_exit_code_1_and_names_the_problem(self):
        self.run_main("build")
        path = os.path.join(self.scratch, "story-001.md")
        text = story.read(path).replace("in U-0019: ", "in U-0091: ")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        code, said = self.run_main("check")
        self.assertEqual(code, 1)
        self.assertIn("PROBLEM: U-0091 is cited and is not in the source record.", said)
        self.assertTrue(said[-1].startswith("CHECK FAILED."))

    def test_check_with_no_story_does_not_pass(self):
        self.assertEqual(self.run_main("check")[0], 1)

    def test_an_empty_story_does_not_pass(self):
        with open(os.path.join(self.scratch, "story-001.md"), "w", encoding="utf-8") as f:
            f.write("# Story\n")
        code, said = self.run_main("check")
        self.assertEqual(code, 1)
        self.assertTrue(any("The story has no section \"Acceptance criteria\"." in line for line in said))

    def test_no_command_explains_itself(self):
        self.assertEqual(story.main([], say=lambda line: None), 2)

    def test_no_module_for_connecting_is_loaded(self):
        code = ("import sys, tempfile, shutil; sys.path.insert(0, %r); import story; d = tempfile.mkdtemp()\n"
                "story.main(['build', '--stories', d], say=lambda l: None); story.main(['check', '--stories', d], say=lambda l: None); shutil.rmtree(d)\n"
                "print(sorted(m for m in sys.modules if m.split('.')[0] in ('socket', 'ssl', 'http', 'urllib', 'smtplib', 'ftplib', 'subprocess')))" % os.path.dirname(HERE))
        done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
        self.assertEqual((done.returncode, done.stdout.strip()), (0, "[]"), done.stderr)


if __name__ == "__main__":
    unittest.main()
