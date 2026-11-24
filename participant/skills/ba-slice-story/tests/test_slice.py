"""Tests for slice.py. They use the documents as built from reporting_module.py, held in memory, and spoil one thing
at a time. No file is written."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import reporting_module as data  # noqa: E402
import slice as sl  # noqa: E402

ORIGINAL = sl.render_original(data)
SLICES = sl.render_slices(data, ORIGINAL)
REJECTED = sl.render_rejected(data)


def swap(text, old, new, count=1):
    assert text.count(old) >= 1, "the text to replace is not there: %r" % old
    return text.replace(old, new, count)


def resum(slices, original):
    """Puts the original's present checksum into the slices, so that a change to the original is the only thing tested."""
    import re
    return re.sub(r"original_sha256: `[0-9a-f]{64}`", "original_sha256: `%s`" % sl.sha(original), slices)


def crit(cid):
    return next(text for c, _, text, _ in data.CRITERIA if c == cid)


def row(cid):
    return "  - %s: %s\n" % (cid, crit(cid))


def deps(n, to):
    """The Depends on line of slice n, with what follows it so that it is found once, and the same with `to` in its place."""
    s = data.SLICES[n - 1]
    was = ", ".join("Slice %d" % d for d in s["depends"]) or "none"
    tail = "\n- Relies on: %s" % s["relies"]
    return "- Depends on: %s%s" % (was, tail), ("- Depends on: %s%s" % (to, tail)) if to is not None else tail[1:]


def set_needs(cid, to):
    import re
    out, n = re.subn(r"(### %s [^\n]*\n\n- Criterion: [^\n]*\n- Needs: )[^\n]*" % cid, lambda m: m.group(1) + to, ORIGINAL)
    assert n == 1
    return out


class Base(unittest.TestCase):
    def problems(self, original=ORIGINAL, slices=SLICES):
        return sl.check(original, slices)[0]

    def reported(self, wanted, original=ORIGINAL, slices=SLICES):
        got = self.problems(original, slices)
        self.assertTrue(any(wanted in p for p in got), "wanted a problem containing %r, got %r" % (wanted, got))

    def not_reported(self, unwanted, original=ORIGINAL, slices=SLICES):
        got = self.problems(original, slices)
        self.assertFalse(any(unwanted in p for p in got), got)


class TheHandedInFiles(Base):
    def test_the_built_documents_pass(self):
        self.assertEqual(self.problems(), [])

    def test_the_files_on_disk_are_what_the_tables_give(self):
        self.assertEqual(sl.read(sl.ORIGINAL), ORIGINAL)
        self.assertEqual(sl.read(sl.SLICES), SLICES)
        self.assertEqual(sl.read(sl.REJECTED), REJECTED)

    def test_the_facts_are_those_of_the_story(self):
        facts = sl.check(ORIGINAL, SLICES)[1]
        self.assertEqual(len(facts["criteria"]), 20)
        self.assertEqual(len(facts["slices"]), 7)
        self.assertEqual(facts["once"], 20)
        self.assertTrue(facts["first_alone"])
        self.assertEqual(facts["where"]["OC-20"], 2)

    def test_every_slice_criterion_is_an_original_criterion_word_for_word(self):
        text_of = {cid: text for cid, _, text, _ in data.CRITERIA}
        for s in sl.parse_slices(SLICES)["slices"]:
            for cid, said in s["criteria"]:
                self.assertEqual(said, text_of[cid])


class TheOriginalStory(Base):
    def test_a_missing_section_is_reported(self):
        self.reported("has no section \"Why it is too large", original=swap(ORIGINAL, "## Why it is too large for one iteration\n\n" + data.TOO_LARGE, ""))

    def test_a_missing_value_is_reported(self):
        self.reported("does not state its value", original=swap(ORIGINAL, "- Value: " + data.STORY["Value"] + "\n", ""))

    def test_no_criteria_is_reported(self):
        self.reported("has no acceptance criteria", original=ORIGINAL.split("## Acceptance criteria")[0] + "## Acceptance criteria\n\nNone yet.\n")

    def test_criteria_out_of_order_are_reported(self):
        self.reported("not numbered OC-01, OC-02", original=swap(ORIGINAL, "### OC-07 ·", "### OC-27 ·"))

    def test_a_need_that_is_not_a_criterion_is_reported(self):
        self.reported("OC-02 needs OC-41, which is not a criterion", original=set_needs("OC-02", "OC-41"))

    def test_a_criterion_that_needs_itself_is_reported(self):
        self.reported("OC-02 needs itself", original=set_needs("OC-02", "OC-02"))

    def test_a_criterion_with_no_needs_line_is_reported(self):
        self.reported("OC-01 does not say what it needs", original=swap(ORIGINAL, "- Needs: none\n", ""))

    def test_needs_that_go_round_in_a_circle_are_reported(self):
        self.reported("go round in a circle", original=set_needs("OC-01", "OC-03"))

    def test_a_criterion_with_no_text_is_reported(self):
        self.reported("OC-01 has no criterion", original=swap(ORIGINAL, "- Criterion: " + data.CRITERIA[0][2] + "\n", ""))


class Coverage(Base):
    def test_a_criterion_in_no_slice_is_reported(self):
        spoiled = swap(swap(SLICES, "- Covers: OC-13\n", "- Covers: \n"), "  - OC-13: " + data.CRITERIA[12][2] + "\n", "")
        self.reported("OC-13 is covered by no slice", slices=spoiled)

    def test_a_criterion_in_two_slices_is_reported(self):
        row = "  - OC-13: " + data.CRITERIA[12][2] + "\n"
        spoiled = swap(swap(SLICES, "- Covers: OC-06\n", "- Covers: OC-06, OC-13\n"), "  - OC-06: " + data.CRITERIA[5][2] + "\n", "  - OC-06: " + data.CRITERIA[5][2] + "\n" + row)
        self.reported("OC-13 is covered by more than one slice: 3, 5", slices=spoiled)

    def test_a_criterion_listed_twice_in_one_slice_is_reported(self):
        self.reported("Slice 3 lists OC-13 twice", slices=swap(SLICES, "- Covers: OC-13\n", "- Covers: OC-13, OC-13\n"))

    def test_a_slice_that_covers_an_unknown_criterion_is_reported(self):
        self.reported("Slice 3 covers OC-31, which is not a criterion", slices=swap(SLICES, "- Covers: OC-13\n", "- Covers: OC-13, OC-31\n"))

    def test_a_slice_that_covers_nothing_is_reported(self):
        self.reported("Slice 3 covers nothing", slices=swap(SLICES, "- Covers: OC-13\n", "- Covers: \n"))

    def test_the_covers_line_and_the_criteria_written_out_must_agree(self):
        self.reported("Slice 2 says it covers OC-05, OC-20, and the criteria written out under it are OC-05", slices=swap(SLICES, row("OC-20"), ""))

    def test_the_counts_at_the_head_must_be_the_counts(self):
        self.reported("The counts at the head", slices=swap(SLICES, "Slices: 7.", "Slices: 8."))

    def test_the_counts_are_recomputed_and_not_read(self):
        spoiled = swap(swap(SLICES, "- Covers: OC-13\n", "- Covers: \n"), "  - OC-13: " + data.CRITERIA[12][2] + "\n", "")
        self.reported("and 19 are covered by exactly one slice", slices=spoiled)

    def test_a_criterion_covered_twice_is_not_counted_as_covered_once(self):
        self.reported("and 19 are covered by exactly one slice", slices=swap(SLICES, "- Covers: OC-06\n", "- Covers: OC-06, OC-13\n"))

    def test_the_coverage_table_must_be_what_the_slices_say(self):
        self.reported("The coverage table in the slices is not what the slices themselves say", slices=swap(SLICES, "| OC-20 | 2 |", "| OC-20 | 3 |"))

    def test_a_missing_row_of_the_coverage_table_is_reported(self):
        self.reported("The coverage table", slices=swap(SLICES, "| OC-20 | 2 |\n", ""))


class NothingAdded(Base):
    def test_a_criterion_worded_differently_is_reported(self):
        self.reported("Slice 2 words OC-05 differently", slices=swap(SLICES, row("OC-05"), row("OC-05").replace("both included.", "both included, and is remembered.")))

    def test_one_changed_character_is_reported(self):
        self.reported("Slice 2 words OC-20 differently", slices=swap(SLICES, row("OC-20"), row("OC-20").replace("within 5 seconds", "within 6 seconds")))

    def test_a_criterion_that_is_not_from_the_original_is_reported(self):
        self.reported("Slice 3 has a criterion that is not from the original story", slices=swap(SLICES, "  - OC-13: ", "  - The file opens in a spreadsheet program.\n  - OC-13: "))

    def test_a_new_numbered_criterion_is_reported(self):
        self.reported("Slice 3 covers OC-21, which is not a criterion", slices=swap(swap(SLICES, "- Covers: OC-13\n", "- Covers: OC-13, OC-21\n"), "  - OC-13: ", "  - OC-21: The file opens in a spreadsheet program.\n  - OC-13: "))

    def test_slices_cut_from_another_version_of_the_original_are_reported(self):
        self.reported("cut from a different version of the original", original=swap(ORIGINAL, "within 5 seconds", "within 9 seconds"))

    def test_a_change_to_the_original_shows_as_a_difference_of_wording_too(self):
        changed = swap(ORIGINAL, "within 5 seconds", "within 9 seconds")
        self.reported("Slice 2 words OC-20 differently", original=changed, slices=resum(SLICES, changed))


class Order(Base):
    def test_a_slice_that_depends_on_a_later_slice_is_reported(self):
        self.reported("Slice 2 depends on Slice 5, which does not come before it", slices=swap(SLICES, *deps(2, "Slice 5")))

    def test_a_slice_that_depends_on_itself_is_reported(self):
        self.reported("Slice 2 depends on Slice 2, which does not come before it", slices=swap(SLICES, *deps(2, "Slice 2")))

    def test_a_slice_that_depends_on_a_slice_that_does_not_exist_is_reported(self):
        self.reported("Slice 2 depends on Slice 14, which does not exist", slices=swap(SLICES, *deps(2, "Slice 14")))

    def test_a_need_in_a_later_slice_is_reported_whatever_the_slice_says(self):
        changed = set_needs("OC-05", "OC-03, OC-14")
        self.reported("Slice 2 covers OC-05, which needs OC-14. That is in Slice 6, which comes after it", original=changed, slices=resum(SLICES, changed))

    def test_a_need_in_an_earlier_slice_that_is_not_declared_is_reported(self):
        self.reported("Slice 7 covers OC-19, which needs OC-13 in Slice 3, and Slice 7 does not say that it depends on Slice 3", slices=swap(SLICES, *deps(7, "Slice 6")))

    def test_a_dependency_reached_through_another_slice_counts(self):
        # Slice 6 says Slice 2 and Slice 5. It does not name Slice 1, and reaches it through them.
        self.not_reported("Slice 6 does not say that it depends on")

    def test_a_slice_must_name_a_needed_slice_or_one_that_leads_to_it(self):
        # Slice 7 without Slice 6 still has Slice 3, which leads to Slice 1 and not to Slice 6.
        self.reported("Slice 7 covers OC-18, which needs OC-15 in Slice 6, and Slice 7 does not say that it depends on Slice 6", slices=swap(SLICES, *deps(7, "Slice 3")))

    def test_a_dependency_is_followed_through_another_slice(self):
        # Slice 6 names Slices 2 and 5. Make one of its criteria need something in Slice 1: they lead there.
        changed = set_needs("OC-15", "OC-14, OC-03")
        self.not_reported("Slice 6 does not say that it depends on", original=changed, slices=resum(SLICES, changed))
        self.assertIn(1, sl.check(changed, resum(SLICES, changed))[1]["derived"][6])

    def test_a_missing_depends_line_is_reported(self):
        self.reported("Slice 2 does not say which slices it depends on", slices=swap(SLICES, *deps(2, None)))

    def test_slices_out_of_order_are_reported(self):
        self.reported("The slices are not numbered 1, 2, 3", slices=swap(SLICES, "## Slice 4: ", "## Slice 14: "))


class TheFirstSlice(Base):
    def test_a_first_slice_that_depends_on_another_is_reported(self):
        self.reported("Slice 1 depends on another slice", slices=swap(SLICES, *deps(1, "Slice 2")))

    def test_a_first_slice_that_relies_on_a_later_slice_is_reported(self):
        self.reported("Slice 1 relies on a later slice", slices=swap(SLICES, "It relies on no other slice.", "It also relies on Slice 3."))

    def test_a_first_slice_whose_criterion_needs_a_later_one_is_not_alone(self):
        changed = set_needs("OC-04", "OC-03, OC-05")
        facts = sl.check(changed, resum(SLICES, changed))[1]
        self.assertFalse(facts["first_alone"])

    def test_no_slices_at_all_is_reported(self):
        self.reported("There are no slices", slices=SLICES.split("## Slice 1:")[0])


class WhatEachSliceStates(Base):
    def test_a_slice_with_no_value_is_reported(self):
        self.reported("Slice 3 does not state the value", slices=swap(SLICES, "- Value on its own: " + data.SLICES[2]["value"], "- Value on its own: More dates."))

    def test_a_slice_that_does_not_say_what_a_user_would_notice_is_reported(self):
        self.reported("Slice 3 does not say what a user would notice", slices=swap(SLICES, "- A user would notice: " + data.SLICES[2]["notice"] + "\n", ""))

    def test_a_slice_that_does_not_say_what_it_relies_on_is_reported(self):
        self.reported("Slice 3 does not say what it relies on", slices=swap(SLICES, "- Relies on: " + data.SLICES[2]["relies"] + "\n", ""))

    def test_a_slice_that_does_not_say_what_holds_without_the_later_ones_is_reported(self):
        self.reported("Slice 3 does not say what holds if it is released without", slices=swap(SLICES, "- If released without the later slices: " + data.SLICES[2]["alone"] + "\n", ""))

    def test_a_slice_that_does_not_justify_its_place_is_reported(self):
        self.reported("Slice 3 does not say why it is where it is", slices=swap(SLICES, "- Why it is here in the order: " + data.SLICES[2]["why"] + "\n", ""))

    def test_a_slice_named_for_a_layer_is_reported(self):
        self.reported("Slice 3 is named for a technical layer", slices=swap(SLICES, "## Slice 3: " + data.SLICES[2]["title"], "## Slice 3: The export endpoint"))

    def test_a_layer_word_in_the_value_is_reported(self):
        self.reported("it uses the word \"database\"", slices=swap(SLICES, "- Value on its own: " + data.SLICES[4]["value"], "- Value on its own: The database can be asked which orders had one product in them."))

    def test_a_layer_word_inside_another_word_is_not_reported(self):
        self.assertEqual(sl.layer_words("A rapid remodelling of the capital"), [])


class TheRejectedSlicing(unittest.TestCase):
    def test_nothing_holds_until_the_third_layer(self):
        rows = sl.judge_layers(ORIGINAL, REJECTED)["layers"]
        self.assertEqual([len(r["holding"]) for r in rows], [0, 0, 18, 20])

    def test_no_criterion_belongs_to_one_layer(self):
        got = sl.judge_layers(ORIGINAL, REJECTED)
        self.assertEqual(got["in_one_layer"], [])
        self.assertEqual(got["missing"], [])
        self.assertTrue(all(not r["alone"] for r in got["layers"]))

    def test_a_criterion_left_out_of_the_table_is_noticed(self):
        got = sl.judge_layers(ORIGINAL, swap(REJECTED, "| OC-20 | L1, L2, L3 |\n", ""))
        self.assertEqual(got["missing"], ["OC-20"])

    def test_the_count_follows_the_table(self):
        rows = sl.judge_layers(ORIGINAL, swap(REJECTED, "| OC-01 | L1, L2, L3 |", "| OC-01 | L1 |"))["layers"]
        self.assertEqual([len(r["holding"]) for r in rows], [1, 1, 18, 20])
        self.assertEqual(rows[0]["alone"], ["OC-01"])


class TheRejectedSlicingByArea(unittest.TestCase):
    def test_the_areas_are_read_from_the_headings_of_the_original(self):
        got = sl.judge_areas(ORIGINAL)
        self.assertEqual([a["area"] for a in got["areas"]], ["The page", "The list", "The figures", "The export", "Saved reports", "The weekly email", "Speed"])
        self.assertEqual(sum(len(a["criteria"]) for a in got["areas"]), 20)

    def test_it_passes_every_count_the_check_can_make(self):
        got = sl.judge_areas(ORIGINAL)
        self.assertEqual(got["once"], 20)
        self.assertEqual(got["later"], [])
        self.assertEqual(got["first"], ["OC-01", "OC-02"])

    def test_a_need_in_a_later_area_would_be_counted(self):
        self.assertEqual(sl.judge_areas(set_needs("OC-02", "OC-01, OC-13"))["later"], [("OC-02", "OC-13")])


if __name__ == "__main__":
    unittest.main()
