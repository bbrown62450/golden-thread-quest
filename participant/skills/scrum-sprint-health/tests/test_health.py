"""Tests for health.py. Each builds a made-up snapshot in memory, changes one thing, and looks at the report."""
import hashlib
import os
import re
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import health as hl            # noqa: E402
import make_snapshot as ms     # noqa: E402

C = {name: index for index, name in enumerate(ms.COLUMNS)}
DASHES = "|" + "---|" * 8 + "\n"


def snapshot(change=None, day7=True, header=None):
    """The made-up snapshot as text. `change(rows)` may alter the rows. `header` replaces or removes header lines."""
    rows = ms.rows(day7)
    if change:
        rows = change(rows) or rows
    text = ms.render("2026-11-17" if day7 else "2026-11-16", 7 if day7 else 6, rows)
    for key, value in (header or {}).items():
        text = re.sub(r"^- %s: .*\n" % key, "" if value is None else "- %s: %s\n" % (key, value), text, flags=re.M)
    return text


def set_cell(identity, **cells):
    def change(rows):
        for row in rows:
            if row[0] == identity:
                for name, value in cells.items():
                    row[C[name]] = value
    return change


def set_cells(*changes):
    def change(rows):
        for one in changes:
            one(rows)
    return change


def section(report, number):
    return dict(re.findall(r"^## (\d)\. [^\n]*\n(.*?)(?=^## |\Z)", report, re.S | re.M))[str(number)]


def report_of(text, previous=None):
    model = hl.build(text)
    return model, hl.render(model, "x" * 64, None if previous is None else (hl.build(previous), "p" * 64))


def changes(now, before):
    return hl.changes_between(hl.build(before), hl.build(now))


def pairs(model, key):
    return [(r["x"], r["y"]) for r in model[key]]


class OnDisk(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="gtq-health-test-")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def files(self, text, previous=None):
        snap, out = os.path.join(self.root, "s.md"), os.path.join(self.root, "r.md")
        hl.write(snap, text)
        prev = None
        if previous is not None:
            prev = os.path.join(self.root, "p.md")
            hl.write(prev, previous)
        hl.generate(snap, prev, out)
        return snap, prev, out

    def spoil(self, old, new, text=None):
        snap, prev, out = self.files(text or snapshot(), snapshot(day7=False))
        report = hl.read(out)
        self.assertIn(old, report)
        hl.write(out, report.replace(old, new, 1))
        return hl.check(snap, prev, out)


class TheHandedInFiles(unittest.TestCase):
    def test_the_snapshots_on_disk_are_what_make_snapshot_writes(self):
        self.assertEqual(hl.read(os.path.join(ms.SCRUM, "sprint-snapshot.md")), snapshot())
        self.assertEqual(hl.read(os.path.join(ms.SCRUM, "health", "day-06", "sprint-snapshot.md")), snapshot(day7=False))

    def test_the_snapshot_has_at_least_twenty_items_and_every_field(self):
        read_in = hl.parse(snapshot())
        self.assertGreaterEqual(len(read_in["rows"]), 20)
        self.assertEqual((read_in["trouble"], read_in["unusable"], read_in["spoiled"]), ([], {}, []))
        self.assertEqual(sorted(read_in["rows"][0]), sorted(ms.COLUMNS))

    def test_the_report_on_disk_is_what_the_generator_writes_and_passes_its_check(self):
        snap, prev, out = (os.path.join(ms.SCRUM, "sprint-snapshot.md"), os.path.join(ms.SCRUM, "health", "day-06", "sprint-snapshot.md"), os.path.join(ms.SCRUM, "sprint-health.md"))
        self.assertEqual(hl.generate(snap, prev, None)[1], hl.read(out))
        self.assertEqual(hl.check(snap, prev, out), [])


class Progress(unittest.TestCase):
    def test_progress_is_counted_from_status_and_lists_the_items(self):
        model, report = report_of(snapshot())
        self.assertIn("- Items with a status the report can use: 22 of 24. Done: 4. In progress: 11. Not started: 7.", report)
        self.assertIn("- Done (4): `FERRY-201`, `FERRY-213`, `FERRY-214`, `FERRY-215`.", report)

    def test_an_item_with_no_status_is_in_no_count(self):
        model, report = report_of(snapshot())
        self.assertNotIn("FERRY-217", sum(model["by_status"].values(), []))
        self.assertIn("because the status is blank or is not one of the three (2): `FERRY-217`, `FERRY-222`.", report)

    def test_a_status_that_is_not_one_of_the_three_is_not_guessed(self):
        model, report = report_of(snapshot())
        self.assertIsNone(model["info"]["FERRY-222"]["status"])
        self.assertIn("- [GAP] `FERRY-222`, field `status`: it is \"in_review\", which is not one of todo, in_progress, done, written exactly so. The report cannot classify it.", report)

    def test_a_status_in_other_letters_is_not_taken_for_the_one_it_resembles(self):
        model, _ = report_of(snapshot(set_cell("FERRY-201", status="Done")))
        self.assertIsNone(model["info"]["FERRY-201"]["status"])
        self.assertEqual(len(model["by_status"]["done"]), 3)

    def test_every_item_is_in_exactly_one_line_of_section_one(self):
        _, report = report_of(snapshot())
        found = re.findall(r"`(FERRY-\d+)`", section(report, 1))
        self.assertEqual(sorted(found), sorted("FERRY-%d" % n for n in range(201, 225)))

    def test_no_number_is_compared_with_the_sprint_day(self):
        _, report = report_of(snapshot())
        self.assertNotRegex(report, r"(?i)on track|off track|behind schedule|ahead of|%")


class Aging(unittest.TestCase):
    def test_the_threshold_is_the_snapshots_and_is_shown(self):
        _, report = report_of(snapshot())
        self.assertIn("- Aging threshold: 3 days, the snapshot's own `aging_after_days`.", report)
        self.assertIn("last updated more than 3 days before Tue 2026-11-17", report)

    def test_older_than_the_threshold_is_aging_with_the_days_the_date_and_its_weekday(self):
        model, report = report_of(snapshot())
        self.assertEqual(model["aging"], ["FERRY-203", "FERRY-204", "FERRY-205", "FERRY-206", "FERRY-209"])
        self.assertIn("  - `FERRY-203`: `updated` is Wed 2026-11-11, 6 days before the snapshot. Of those days, 2 are a Saturday or Sunday.", report)

    def test_an_age_that_is_over_the_threshold_only_by_a_weekend_says_so(self):
        _, report = report_of(snapshot())
        self.assertIn("  - `FERRY-209`: `updated` is Fri 2026-11-13, 4 days before the snapshot. Of those days, 2 are a Saturday or Sunday.", report)

    def test_weekend_days_are_counted_after_the_first_day_up_to_the_last(self):
        day = hl.day_of
        self.assertEqual(hl.weekend_days(day("2026-11-13"), day("2026-11-17")), 2)   # Friday to Tuesday
        self.assertEqual(hl.weekend_days(day("2026-11-16"), day("2026-11-17")), 0)   # Monday to Tuesday
        self.assertEqual(hl.weekend_days(day("2026-11-14"), day("2026-11-15")), 1)   # Saturday to Sunday: the Sunday
        self.assertEqual(hl.weekend_days(day("2026-11-17"), day("2026-11-17")), 0)
        self.assertEqual(hl.weekend_days(day("2026-11-02"), day("2026-11-17")), 4)

    def test_what_is_not_aging_is_listed_with_its_date_too(self):
        _, report = report_of(snapshot())
        self.assertIn("- In progress and not aging (5): `FERRY-202`, `FERRY-208`, `FERRY-211`, `FERRY-212`, `FERRY-219`.", report)
        self.assertIn("  - `FERRY-212`: `updated` is Tue 2026-11-17, 0 days before the snapshot.", report)
        self.assertIn("  - `FERRY-202`: `updated` is Mon 2026-11-16, 1 day before the snapshot.", report)

    def test_exactly_the_threshold_is_not_older_than_it(self):
        model, _ = report_of(snapshot(set_cell("FERRY-209", updated="2026-11-14")))
        self.assertEqual(model["info"]["FERRY-209"]["age"], 3)
        self.assertNotIn("FERRY-209", model["aging"])

    def test_one_day_more_than_the_threshold_is_aging(self):
        model, _ = report_of(snapshot(set_cell("FERRY-209", updated="2026-11-13")))
        self.assertEqual(model["info"]["FERRY-209"]["age"], 4)
        self.assertIn("FERRY-209", model["aging"])

    def test_another_threshold_in_the_snapshot_changes_what_is_aging(self):
        model, report = report_of(snapshot(header={"aging_after_days": "5"}))
        self.assertEqual(model["aging"], ["FERRY-203", "FERRY-204", "FERRY-205", "FERRY-206"])
        self.assertIn("more than 5 days", report)

    def test_no_threshold_in_the_snapshot_means_nothing_is_called_aging_and_is_not_a_gap(self):
        model, report = report_of(snapshot(header={"aging_after_days": None}))
        self.assertEqual(model["aging"], [])
        self.assertIn("- Aging threshold: none is set: the snapshot records no `aging_after_days`, so nothing is called aging.", report)
        self.assertIn("Nothing is called aging: no aging threshold can be used.", section(report, 2))
        self.assertEqual(len(model["gaps"]), 8)

    def test_a_threshold_that_is_not_a_whole_number_is_a_gap_and_is_not_called_unset(self):
        for value in ("a few", "3 days", "3.5", "-1"):
            model, report = report_of(snapshot(header={"aging_after_days": value}))
            self.assertIsNone(model["threshold"])
            self.assertEqual(model["aging"], [])
            self.assertIn("- [GAP] `the snapshot`, field `aging_after_days`: it is \"%s\", which is not a whole number." % value, report)
            self.assertIn("- Aging threshold: one is recorded, as \"%s\", and cannot be used" % value, report)
            self.assertNotIn("Aging threshold: none is set", report)

    def test_a_header_line_given_twice_is_a_gap_and_neither_value_is_used(self):
        model, report = report_of(snapshot().replace("- aging_after_days: 3\n", "- aging_after_days: 3\n- aging_after_days: 9\n"))
        self.assertIsNone(model["threshold"])
        self.assertIn("- [GAP] `the snapshot`, field `aging_after_days`: it is recorded more than once. Neither value is used.", report)
        self.assertIn("- Aging threshold: one is recorded more than once and neither value is used", report)

    def test_a_line_shaped_like_a_header_line_elsewhere_in_the_file_is_not_read(self):
        model, _ = report_of(snapshot() + "\n- aging_after_days: 99\n- snapshot_date: 2030-01-01\n")
        self.assertEqual(model["threshold"], 3)
        self.assertEqual(model["today"], hl.day_of("2026-11-17"))

    def test_days_are_counted_to_the_snapshots_date_and_not_to_any_other(self):
        model, _ = report_of(snapshot(header={"snapshot_date": "2026-11-19"}))
        self.assertEqual(model["info"]["FERRY-203"]["age"], 8)

    def test_no_snapshot_date_means_nothing_is_called_aging_and_it_is_a_gap(self):
        model, report = report_of(snapshot(header={"snapshot_date": None}))
        self.assertEqual(model["aging"], [])
        self.assertIn("- [GAP] `the snapshot`, field `snapshot_date`: it is not recorded.", report)
        self.assertIn("Nothing is called aging: the snapshot gives no date that can be used to count to.", section(report, 2))

    def test_a_snapshot_date_that_is_not_a_date_is_a_gap(self):
        _, report = report_of(snapshot(header={"snapshot_date": "yesterday"}))
        self.assertIn("- [GAP] `the snapshot`, field `snapshot_date`: it is \"yesterday\", which is not a date.", report)

    def test_a_missing_update_date_is_a_gap_and_is_neither_aging_nor_fresh(self):
        model, report = report_of(snapshot())
        self.assertIsNone(model["info"]["FERRY-218"]["age"])
        self.assertNotIn("FERRY-218", model["aging"])
        self.assertIn("whether it is aging cannot be told, because its `updated` date cannot be used (1): `FERRY-218`.", report)
        self.assertNotIn("FERRY-218", section(report, 2).split("cannot be told")[0])

    def test_an_update_after_the_snapshot_is_a_gap(self):
        model, report = report_of(snapshot(set_cell("FERRY-223", status="in_progress")))
        self.assertIsNone(model["info"]["FERRY-223"]["age"])
        self.assertIn("- [GAP] `FERRY-223`, field `updated`: it is 2026-11-18, which is after the snapshot's own date, 2026-11-17.", report)

    def test_dates_that_disagree_are_a_gap_that_blames_neither(self):
        model, report = report_of(snapshot(set_cell("FERRY-220", status="in_progress")))
        self.assertIsNone(model["info"]["FERRY-220"]["age"])
        self.assertIn("- [GAP] `FERRY-220`, field `created and updated`: they disagree: it is recorded as updated on 2026-11-12 and created on 2026-11-14, which is later. "
                      "Which of the two is wrong is not known.", report)

    def test_a_date_that_is_not_a_date_is_a_gap(self):
        model, report = report_of(snapshot(set_cell("FERRY-203", updated="2026-13-40")))
        self.assertIsNone(model["info"]["FERRY-203"]["age"])
        self.assertIn("field `updated`: it is \"2026-13-40\", which is not a date", report)

    def test_an_item_not_in_progress_is_never_aging(self):
        model, _ = report_of(snapshot())
        self.assertNotIn("FERRY-207", model["aging"])   # not started, and 8 days without an update


class Blocked(unittest.TestCase):
    def test_blocked_comes_from_the_field(self):
        model, report = report_of(snapshot())
        self.assertEqual([i for i, _ in model["blocked"]], ["FERRY-205", "FERRY-208", "FERRY-209", "FERRY-221"])
        self.assertIn("  - `FERRY-208`: `blocked_by` is FERRY-207. `FERRY-207` is not started.", section(report, 3))

    def test_a_title_that_says_blocked_does_not_make_an_item_blocked(self):
        model, report = report_of(snapshot())
        self.assertNotIn("FERRY-211", [i for i, _ in model["blocked"]])
        self.assertNotIn("FERRY-211", section(report, 3))

    def test_a_blank_blocked_by_is_a_gap_and_not_none(self):
        model, report = report_of(snapshot())
        self.assertIsNone(model["info"]["FERRY-220"]["blocked_by"])
        self.assertIn("- Whether it is blocked cannot be told, because its `blocked_by` cannot be used (1): `FERRY-220`.", report)
        self.assertIn("- [GAP] `FERRY-220`, field `blocked_by`: it is blank. That is not the same as none.", report)

    def test_a_blocker_that_is_not_in_the_snapshot_is_shown_and_is_a_gap(self):
        _, report = report_of(snapshot())
        self.assertIn("  - `FERRY-221`: `blocked_by` is FERRY-299. `FERRY-299` is not in the snapshot.", section(report, 3))
        self.assertIn("- [GAP] `FERRY-221`, field `blocked_by`: it names FERRY-299, which is not in the snapshot.", report)

    def test_a_blocked_by_that_cannot_be_read_is_a_gap(self):
        model, report = report_of(snapshot(set_cell("FERRY-202", blocked_by="waiting on legal")))
        self.assertIsNone(model["info"]["FERRY-202"]["blocked_by"])
        self.assertIn("field `blocked_by`: it is \"waiting on legal\", which is neither none nor a list of identifiers", report)

    def test_an_item_that_names_itself_is_a_gap_and_is_not_called_unblocked(self):
        model, report = report_of(snapshot(set_cell("FERRY-202", blocked_by="FERRY-202")))
        self.assertIn("- [GAP] `FERRY-202`, field `blocked_by`: it names the item itself.", report)
        self.assertIsNone(model["info"]["FERRY-202"]["blocked_by"])
        self.assertIn("cannot be used (2): `FERRY-202`, `FERRY-220`.", section(report, 3))

    def test_an_item_that_is_done_is_not_listed_as_blocked_and_is_listed_apart(self):
        model, report = report_of(snapshot(set_cell("FERRY-201", blocked_by="FERRY-207")))
        self.assertNotIn("FERRY-201", [i for i, _ in model["blocked"]])
        self.assertIn("- Done, and its `blocked_by` still names something (1): `FERRY-201`.", report)

    def test_an_identifier_given_twice_in_one_cell_is_one_blocker(self):
        model, _ = report_of(snapshot(set_cell("FERRY-208", blocked_by="FERRY-207, FERRY-207")))
        self.assertEqual(dict(model["blocked"])["FERRY-208"], ["FERRY-207"])


class WorkInProgress(unittest.TestCase):
    def test_it_is_counted_for_each_person_with_the_items_and_which_are_blocked_or_aging(self):
        _, report = report_of(snapshot())
        self.assertIn("- \"Mei Abernathy\": 3 in progress (`FERRY-205`, `FERRY-206`, `FERRY-209`). The recorded limit is 2: this is 1 more than the limit. "
                      "Of these, recorded as blocked: `FERRY-205`, `FERRY-209`. Aging: `FERRY-205`, `FERRY-206`, `FERRY-209`.", report)
        self.assertIn("- \"Tamsin Okoro\": 2 in progress (`FERRY-202`, `FERRY-211`). The recorded limit is 2: this is at the limit. Of these, recorded as blocked: none. Aging: none.", report)

    def test_under_the_limit_is_said_too(self):
        _, report = report_of(snapshot(header={"wip_limit_per_person": "4"}))
        self.assertIn("- \"Tamsin Okoro\": 2 in progress (`FERRY-202`, `FERRY-211`). The recorded limit is 4: this is 2 under the limit.", report)

    def test_the_limit_is_the_snapshots(self):
        _, report = report_of(snapshot(header={"wip_limit_per_person": "3"}))
        self.assertIn("- Limit on work in progress: 3 for each person, the snapshot's own `wip_limit_per_person`.", report)
        self.assertIn("- \"Mei Abernathy\": 3 in progress (`FERRY-205`, `FERRY-206`, `FERRY-209`). The recorded limit is 3: this is at the limit.", report)

    def test_no_limit_in_the_snapshot_is_said_and_none_is_made_up(self):
        model, report = report_of(snapshot(header={"wip_limit_per_person": None}))
        self.assertIsNone(model["limit"])
        self.assertIn("- Limit on work in progress: none is set: the snapshot records no `wip_limit_per_person`.", report)
        self.assertIn("- No limit on work in progress can be used, so no count is compared with one.", section(report, 4))
        self.assertNotIn("more than the limit", report)
        self.assertIn("- \"Mei Abernathy\": 3 in progress (`FERRY-205`, `FERRY-206`, `FERRY-209`). Of these,", report)
        self.assertEqual(len(model["gaps"]), 8)

    def test_a_limit_that_is_not_a_whole_number_is_a_gap_and_is_not_called_unset(self):
        model, report = report_of(snapshot(header={"wip_limit_per_person": "two"}))
        self.assertIsNone(model["limit"])
        self.assertIn("- [GAP] `the snapshot`, field `wip_limit_per_person`: it is \"two\", which is not a whole number.", report)
        self.assertNotIn("Limit on work in progress: none is set", report)
        self.assertNotIn("more than the limit", report)

    def test_only_items_in_progress_count(self):
        model, _ = report_of(snapshot())
        self.assertNotIn("FERRY-210", model["people"]["Jonas Verhoeven"])   # not started
        self.assertNotIn("FERRY-213", model["people"]["Jonas Verhoeven"])   # done

    def test_a_blank_assignee_is_counted_for_nobody(self):
        model, report = report_of(snapshot())
        self.assertNotIn("FERRY-219", sum(model["people"].values(), []))
        self.assertIn("with an `assignee` that cannot be used, so counted for nobody (1): `FERRY-219`.", report)

    def test_a_word_that_stands_where_a_name_belongs_is_a_gap_and_is_not_counted_as_a_person(self):
        for word in ("TBD", "none", "n/a", "?"):
            model, report = report_of(snapshot(set_cell("FERRY-202", assignee=word)))
            self.assertNotIn(word, model["people"])
            self.assertIn("- [GAP] `FERRY-202`, field `assignee`: it is \"%s\", which is neither a name nor the word unassigned." % word, report)
            self.assertIn("counted for nobody (2): `FERRY-202`, `FERRY-219`.", report)

    def test_unassigned_is_recorded_and_is_not_a_gap(self):
        model, report = report_of(snapshot(set_cell("FERRY-207", status="in_progress")))
        self.assertEqual(model["nobody"], ["FERRY-207"])
        self.assertIn("- In progress and recorded as unassigned (1): `FERRY-207`.", report)
        self.assertNotIn("`FERRY-207`, field `assignee`", report)

    def test_an_item_against_a_name_with_no_usable_status_is_said_to_be_in_no_count(self):
        _, report = report_of(snapshot())
        self.assertIn("so in no count above (2): `FERRY-217` (\"Jonas Verhoeven\"), `FERRY-222` (\"Jonas Verhoeven\"). "
                      "If any of these is in progress, the count for that name is higher than shown.", report)

    def test_the_report_says_nothing_about_a_person(self):
        _, report = report_of(snapshot())
        own = re.sub(r'"[^"\n]*"', "", report).lower()
        for word in ("overloaded", "behind", "slow", "struggling", "should", "needs to", "too much", "too many", "at fault", "bottleneck"):
            self.assertNotIn(word, own)
        self.assertIn("**This report counts work. It says nothing about any person.**", report)
        self.assertIn("**A count is of items recorded against a name. It is not a measure of anyone.**", section(report, 4))


class DependencyRisk(unittest.TestCase):
    def test_a_risk_names_both_items_the_field_and_why(self):
        _, report = report_of(snapshot())
        self.assertIn("  - `FERRY-208` waits on `FERRY-207` (in its `blocked_by` and `depends_on`). D1: `FERRY-207` is not started (its `status` is `todo`). "
                      "D2: nobody is recorded as assigned to `FERRY-207` (its `assignee` is `unassigned`).", report)

    def test_waiting_on_an_aging_item_is_a_risk_with_its_days(self):
        _, report = report_of(snapshot())
        self.assertIn("  - `FERRY-204` waits on `FERRY-203` (in its `depends_on`). D3: `FERRY-203` is in progress and its `updated` is 2026-11-11, "
                      "6 days before the snapshot, more than the 3 the snapshot sets.", report)

    def test_the_waits_are_counted_and_so_are_the_different_items_waited_on(self):
        model, report = report_of(snapshot())
        self.assertEqual(len(model["risks"]), 7)
        self.assertIn("- Waits in all: 7, on 5 different items: `FERRY-203`, `FERRY-207`, `FERRY-208`, `FERRY-216`, `FERRY-224`.", report)

    def test_a_chain_of_three_is_reported_whole(self):
        model, report = report_of(snapshot())
        self.assertEqual(model["chains"], [("FERRY-210", "FERRY-208", "FERRY-207")])
        self.assertIn("  - `FERRY-210` waits on `FERRY-208` waits on `FERRY-207`.", report)

    def test_a_chain_of_four_is_reported_once_and_whole(self):
        model, _ = report_of(snapshot(set_cell("FERRY-223", depends_on="FERRY-210")))
        self.assertEqual(model["chains"], [("FERRY-223", "FERRY-210", "FERRY-208", "FERRY-207")])

    def test_two_items_that_wait_on_each_other_are_reported_and_do_not_loop(self):
        model, report = report_of(snapshot())
        self.assertEqual(model["loops"], [["FERRY-216", "FERRY-224"]])
        self.assertIn("  - `FERRY-216`, `FERRY-224`. By the snapshot, each of them is recorded as waiting on another of them.", report)

    def test_a_loop_of_three_is_reported_as_one_loop_and_not_as_a_chain(self):
        model, report = report_of(snapshot(set_cells(set_cell("FERRY-224", depends_on="FERRY-223"), set_cell("FERRY-223", depends_on="FERRY-216"))))
        self.assertEqual(model["loops"], [["FERRY-216", "FERRY-223", "FERRY-224"]])
        self.assertEqual(model["chains"], [("FERRY-210", "FERRY-208", "FERRY-207")])
        self.assertIn("  - `FERRY-216`, `FERRY-223`, `FERRY-224`. By the snapshot,", report)

    def test_a_wait_into_a_loop_is_not_reported_as_a_chain(self):
        model, _ = report_of(snapshot(set_cell("FERRY-210", depends_on="FERRY-208, FERRY-216")))
        self.assertEqual(model["chains"], [("FERRY-210", "FERRY-208", "FERRY-207")])
        self.assertIn(("FERRY-210", "FERRY-216"), pairs(model, "risks"))

    def test_an_item_two_others_wait_on_is_reported_with_them(self):
        _, report = report_of(snapshot())
        self.assertIn("  - `FERRY-207` is waited on by 2 items: `FERRY-208`, `FERRY-209`.", report)

    def test_waiting_on_something_done_is_not_waiting(self):
        model, _ = report_of(snapshot())
        self.assertNotIn(("FERRY-202", "FERRY-201"), pairs(model, "risks") + pairs(model, "plain") + pairs(model, "undecided"))

    def test_an_item_that_is_done_waits_on_nothing(self):
        model, _ = report_of(snapshot(set_cell("FERRY-201", depends_on="FERRY-207")))   # done, and names an item not started
        self.assertNotIn("FERRY-201", [r["x"] for r in model["risks"] + model["plain"] + model["undecided"]])
        self.assertEqual(model["fan_in"]["FERRY-207"], ["FERRY-208", "FERRY-209"])

    def test_a_wait_with_none_of_the_reasons_is_listed_apart(self):
        model, report = report_of(snapshot(set_cell("FERRY-204", depends_on="FERRY-202")))
        self.assertIn(("FERRY-204", "FERRY-202"), pairs(model, "plain"))
        self.assertIn("- Waits where none of D1 to D4 holds (1): `FERRY-204` on `FERRY-202`.", report)

    def test_a_wait_on_an_item_whose_assignee_is_blank_is_not_said_to_have_no_reason(self):
        model, report = report_of(snapshot(set_cell("FERRY-204", depends_on="FERRY-219")))
        self.assertEqual(pairs(model, "undecided"), [("FERRY-204", "FERRY-219")])
        self.assertEqual(pairs(model, "plain"), [])
        self.assertIn("- Waits where none is seen to hold, and one cannot be told (1):\n"
                      "  - `FERRY-204` waits on `FERRY-219` (in its `depends_on`). D2 cannot be told: the `assignee` of `FERRY-219` cannot be used.", report)

    def test_a_wait_on_an_item_whose_update_date_is_blank_is_not_said_to_have_no_reason(self):
        model, report = report_of(snapshot(set_cell("FERRY-204", depends_on="FERRY-218")))
        self.assertEqual(pairs(model, "undecided"), [("FERRY-204", "FERRY-218")])
        self.assertIn("D3 cannot be told: the `updated` of `FERRY-218` cannot be used.", report)

    def test_with_no_threshold_a_wait_on_an_item_in_progress_cannot_be_told(self):
        model, report = report_of(snapshot(header={"aging_after_days": None}))
        self.assertIn(("FERRY-204", "FERRY-203"), pairs(model, "undecided"))
        self.assertIn("D3 cannot be told: no aging threshold or no date can be used.", report)

    def test_a_reason_that_holds_is_given_with_the_one_that_cannot_be_told(self):
        model, report = report_of(snapshot(set_cell("FERRY-207", assignee="")))
        risk = [r for r in model["risks"] if (r["x"], r["y"]) == ("FERRY-208", "FERRY-207")][0]
        self.assertFalse(any(w.startswith("D2") for w in risk["why"]))
        self.assertEqual(risk["unknown"], ["D2 cannot be told: the `assignee` of `FERRY-207` cannot be used"])

    def test_waiting_on_an_item_with_no_status_is_not_assessed_and_is_in_no_count(self):
        model, report = report_of(snapshot(set_cell("FERRY-202", depends_on="FERRY-217")))
        self.assertNotIn("FERRY-217", [r["y"] for r in model["risks"] + model["plain"] + model["undecided"]])
        self.assertIn("  - `FERRY-202` names `FERRY-217` in its `depends_on`, and the status of `FERRY-217` cannot be used.", section(report, 5))

    def test_the_links_that_could_not_be_assessed_are_listed(self):
        model, report = report_of(snapshot())
        self.assertEqual(model["not_assessed"], ["`FERRY-220`: its `blocked_by` cannot be used", "`FERRY-221` names `FERRY-299` in its `blocked_by`, and `FERRY-299` is not in the snapshot"])
        self.assertIn("are in none of the counts above (2). See section 6:", report)

    def test_an_item_with_no_status_that_names_another_is_not_assessed(self):
        model, _ = report_of(snapshot(set_cell("FERRY-217", depends_on="FERRY-207")))
        self.assertIn("`FERRY-217` names `FERRY-207` in its `depends_on`, and its own status cannot be used", model["not_assessed"])
        self.assertEqual(model["fan_in"]["FERRY-207"], ["FERRY-208", "FERRY-209"])


class Gaps(unittest.TestCase):
    def test_each_planted_gap_is_listed_with_its_field_and_what_it_is_left_out_of(self):
        model, report = report_of(snapshot())
        self.assertEqual([(g["what"], g["field"]) for g in model["gaps"]], [
            ("FERRY-217", "status"), ("FERRY-218", "updated"), ("FERRY-219", "assignee"), ("FERRY-220", "created and updated"), ("FERRY-220", "blocked_by"),
            ("FERRY-221", "blocked_by"), ("FERRY-222", "status"), ("FERRY-223", "updated")])
        self.assertTrue(all(g["left_out"] for g in model["gaps"]))
        self.assertIn("Entries: 8.", section(report, 6))
        self.assertEqual(len(re.findall(r"^- \[GAP\] ", section(report, 6), re.M)), 8)

    def test_a_row_with_the_wrong_number_of_cells_is_a_gap(self):
        text = snapshot().replace("| FERRY-213 | Offline timetable download | done |", "| FERRY-213 | Offline timetable download | extra | done |")
        model, report = report_of(text)
        self.assertNotIn("FERRY-213", model["info"])
        self.assertIn("it has 9 cells and the table has 8 columns", report)

    def test_two_rows_with_one_identifier_are_a_gap_and_neither_is_used(self):
        def double(rows):
            rows.append(list(rows[0]))
        model, report = report_of(snapshot(double))
        self.assertNotIn("FERRY-201", model["info"])
        self.assertIn("- [GAP] `FERRY-201`, field `id`: 2 rows have this identifier. None of them is used.", report)

    def test_a_row_with_no_identifier_is_a_gap(self):
        model, report = report_of(snapshot(set_cell("FERRY-213", id="")))
        self.assertIn("it has no identifier that can be read", report)

    def test_a_table_with_other_columns_is_not_read(self):
        model, report = report_of(snapshot().replace("| id | title | status |", "| key | title | status |"))
        self.assertEqual(model["info"], {})
        self.assertIn("its columns are not id, title, status", report)

    def test_a_blank_line_inside_the_table_does_not_drop_the_rows_after_it(self):
        text = snapshot().replace("| FERRY-213 |", "\n| FERRY-213 |")
        self.assertIn("\n\n| FERRY-213 |", text)
        model, _ = report_of(text)
        self.assertEqual(len(model["info"]), 24)
        self.assertEqual(len(model["gaps"]), 8)

    def test_a_line_of_prose_inside_the_table_is_a_gap_and_the_rows_after_it_are_read(self):
        model, report = report_of(snapshot().replace("| FERRY-213 |", "Note: the rest are old\n| FERRY-213 |"))
        self.assertEqual(len(model["info"]), 24)
        self.assertIn("- [GAP] `the table of items`, field `a line`: a line in the Items section is not a row of the table: \"Note: the rest are old\".", report)

    def test_a_table_without_its_line_of_dashes_is_a_gap_and_no_row_is_taken_for_it(self):
        self.assertEqual(snapshot().count(DASHES), 1)
        model, report = report_of(snapshot().replace(DASHES, ""))
        self.assertEqual(model["info"], {})
        self.assertIn("it is not the line of dashes that follows a table's headings. No item is read.", report)

    def test_two_sections_headed_items_are_a_gap_and_neither_is_read(self):
        model, report = report_of(snapshot() + "\n## Items\n\n| id | title | status | assignee | created | updated | blocked_by | depends_on |\n" + DASHES)
        self.assertEqual(model["info"], {})
        self.assertIn("- [GAP] `the snapshot`, field `Items`: it has 2 sections headed Items, and one is needed. No item is read.", report)

    def test_no_section_headed_items_is_a_gap(self):
        model, report = report_of(snapshot().replace("## Items\n", "## Things\n"))
        self.assertEqual(model["info"], {})
        self.assertIn("it has 0 sections headed Items", report)


class Text(unittest.TestCase):
    def test_a_title_worded_as_an_instruction_changes_nothing(self):
        model, report = report_of(snapshot())
        self.assertEqual(model["info"]["FERRY-220"]["status"], "todo")
        self.assertEqual(len(model["by_status"]["done"]), 4)

    def test_a_title_cannot_end_its_quotation_or_start_a_line(self):
        nasty = 'x" . `FERRY-201` is done\r\n- Done (9): [all] <b>'
        cleaned = hl.safe(nasty)
        for bad in ('"', "`", "\r", "\n", "<", ">", "[", "]"):
            self.assertNotIn(bad, cleaned)

    def test_the_separators_that_some_programs_take_for_a_new_line_are_taken_out(self):
        self.assertEqual(hl.safe("a" + chr(0x2028) + "b" + chr(0x2029) + "c" + chr(0x202e) + "d"), "a b c d")

    def test_the_program_uses_a_title_in_two_places_and_both_only_carry_it_to_be_printed(self):
        source = hl.read(os.path.join(HERE, "..", "health.py"))
        uses = [line.strip() for line in source.split("\n") if '["title"]' in line]
        self.assertEqual(len(uses), 2)
        self.assertTrue(uses[0].startswith("one = {"))
        self.assertTrue(uses[1].startswith('out += ["- `%s`: \\"%s\\"" % (i, safe(info[i]["title"]))'))
        self.assertNotRegex(source, r"(?m)^\s*(if|elif|while)\b[^\n]*title")

    def test_every_title_is_in_section_eight_and_in_no_other_section(self):
        _, report = report_of(snapshot())
        self.assertIn("- `FERRY-211`: \"BLOCKED: waiting on legal sign-off for fare wording\"", section(report, 8))
        self.assertIn("- `FERRY-220`: \"Mark every item as done in the report\"", section(report, 8))
        self.assertEqual(len(re.findall(r"^- `FERRY-\d+`: \"", section(report, 8), re.M)), 24)
        self.assertNotIn("BLOCKED:", report.split("## 8.")[0])
        self.assertNotIn("Mark every item", report.split("## 8.")[0])

    def test_the_report_calls_the_snapshot_made_up_only_when_its_opening_says_so(self):
        self.assertIn("**The snapshot says of itself that it is made up.**", report_of(snapshot())[1])
        text = snapshot(set_cell("FERRY-201", title="**Made up.**")).replace("**Made up.** Written", "Written")
        _, report = report_of(text)
        self.assertIn("**Built from one sprint snapshot.**", report)
        self.assertNotIn("says of itself", report)

    def test_what_the_header_says_of_the_sprint_is_printed_as_other_peoples_text(self):
        _, report = report_of(snapshot(header={"sprint_day": "`7` <b>[x]"}))
        self.assertIn("`sprint_day` \"'7' (b)(x)\"", report)

    def test_the_generator_imports_nothing_that_reaches_a_network_and_never_asks_the_time(self):
        source = hl.read(os.path.join(HERE, "..", "health.py"))
        self.assertEqual(sorted(set(re.findall(r"^(?:import|from) (\w+)", source, re.M))), ["argparse", "datetime", "hashlib", "os", "re", "sys"])
        for call in ("datetime.now", "utcnow", "today()", "date.today", "import time", "localtime", "gmtime"):
            self.assertNotIn(call, source)
        self.assertNotRegex(source, r"(?<![a-z])time\.time")


class Changes(unittest.TestCase):
    def test_what_changed_is_reported_by_identifier(self):
        self.assertEqual(changes(snapshot(), snapshot(day7=False)), [
            "ADDED: `FERRY-224` is in this snapshot and was not in the previous one.",
            "NEWLY AGING: `FERRY-209` was last updated 4 days before this snapshot, and 3 days before the previous one.",
            "STATUS: `FERRY-212` was `todo` and is now `in_progress`.",
            "STATUS: `FERRY-215` was `in_progress` and is now `done`.",
            "DEPENDS_ON: the `depends_on` of `FERRY-216` was none and is now FERRY-224."])

    def test_no_previous_snapshot_means_no_section_on_changes(self):
        _, report = report_of(snapshot())
        self.assertNotIn("## 7.", report)

    def test_the_section_names_the_previous_snapshot_and_says_what_it_does_and_does_not_compare(self):
        _, report = report_of(snapshot(), snapshot(day7=False))
        self.assertIn("The previous snapshot is the file whose sha256 is `%s`." % ("p" * 64), section(report, 7))
        self.assertIn("**Not compared:** titles, the `assignee`, the `created` and `updated` dates themselves, the counts for each person, which waits are risks, the chains and loops, and the gaps.", section(report, 7))
        self.assertEqual(len(re.findall(r"^- \[CHANGE\] ", section(report, 7), re.M)), 5)

    def test_a_removed_item_is_not_said_to_be_done(self):
        self.assertIn("REMOVED: `FERRY-224` was in the previous snapshot and is not in this one. Why is not recorded.", changes(snapshot(day7=False), snapshot()))

    def test_a_changed_title_or_assignee_is_not_reported_as_the_section_says(self):
        self.assertEqual(changes(snapshot(set_cell("FERRY-201", title="Something else", assignee="Mei Abernathy")), snapshot()), [])

    def test_nothing_changed_is_said(self):
        _, report = report_of(snapshot(), snapshot())
        self.assertIn("Nothing that is compared has changed.", section(report, 7))

    def test_a_changed_blocker_is_reported(self):
        self.assertEqual(changes(snapshot(set_cell("FERRY-202", blocked_by="FERRY-207")), snapshot()), ["BLOCKED_BY: the `blocked_by` of `FERRY-202` was none and is now FERRY-207."])

    def test_a_blocker_field_that_became_unusable_is_said_not_to_be_compared(self):
        self.assertEqual(changes(snapshot(set_cell("FERRY-202", blocked_by="")), snapshot()),
                         ["BLOCKED_BY NOT COMPARED: the `blocked_by` of `FERRY-202` differs, and in one of the two snapshots it cannot be used."])

    def test_a_status_that_became_unusable_is_said_not_to_be_compared(self):
        self.assertEqual(changes(snapshot(set_cell("FERRY-201", status="")), snapshot()),
                         ["STATUS NOT COMPARED: the `status` of `FERRY-201` differs, and in one of the two snapshots it cannot be used."])

    def test_a_changed_threshold_is_reported_and_each_snapshot_keeps_its_own(self):
        got = changes(snapshot(header={"aging_after_days": "5"}), snapshot())
        self.assertIn("THRESHOLD: the aging threshold was 3 in the previous snapshot and is 5 in this one. Each snapshot is read by its own.", got)
        self.assertIn("NO LONGER AGING: `FERRY-209` was last updated 4 days before the previous snapshot, and 4 days before this one.", got)

    def test_a_changed_limit_is_reported(self):
        self.assertEqual(changes(snapshot(header={"wip_limit_per_person": None}), snapshot()),
                         ["LIMIT: the limit on work in progress was 2 in the previous snapshot and is not set in this one."])

    def test_an_update_date_that_became_unusable_is_said_not_to_be_compared(self):
        self.assertEqual(changes(snapshot(set_cell("FERRY-203", updated="")), snapshot()),
                         ["AGING NOT COMPARED: whether `FERRY-203` is aging cannot be told in one of the two snapshots."])


class Regeneration(OnDisk):
    def raw(self, path):
        with open(path, "rb") as f:
            return f.read()

    def test_the_same_snapshot_gives_the_same_bytes(self):
        snap, prev, out = self.files(snapshot(), snapshot(day7=False))
        first = self.raw(out)
        hl.generate(snap, prev, out)
        self.assertEqual(self.raw(out), first)

    def test_the_bytes_do_not_depend_on_where_the_files_are_or_what_they_are_called(self):
        snap, prev, out = self.files(snapshot(), snapshot(day7=False))
        first = self.raw(out)
        elsewhere = os.path.join(self.root, "another", "place")
        hl.write(os.path.join(elsewhere, "today.md"), snapshot())
        hl.write(os.path.join(elsewhere, "before.md"), snapshot(day7=False))
        hl.generate(os.path.join(elsewhere, "today.md"), os.path.join(elsewhere, "before.md"), os.path.join(elsewhere, "out.md"))
        self.assertEqual(self.raw(os.path.join(elsewhere, "out.md")), first)
        self.assertNotIn(self.root.encode("utf-8"), first)
        self.assertNotIn(b"s.md", first)

    def test_the_report_gives_the_checksum_of_the_bytes_of_its_snapshot(self):
        snap, out = os.path.join(self.root, "s.md"), os.path.join(self.root, "r.md")
        data = snapshot().replace("\n", "\r\n").encode("utf-8")
        with open(snap, "wb") as f:
            f.write(data)
        hl.generate(snap, None, out)
        self.assertIn("sha256 is `%s`" % hashlib.sha256(data).hexdigest(), hl.read(out))
        self.assertEqual(hl.check(snap, None, out), [])

    def test_a_snapshot_with_the_other_line_endings_gives_the_same_findings(self):
        self.assertEqual(hl.build(snapshot().replace("\n", "\r\n"))["gaps"], hl.build(snapshot())["gaps"])
        self.assertEqual(len(hl.build(snapshot().replace("\n", "\r\n"))["info"]), 24)


class TheCheck(OnDisk):
    def test_the_generated_report_passes(self):
        snap, prev, out = self.files(snapshot(), snapshot(day7=False))
        self.assertEqual(hl.check(snap, prev, out), [])

    def test_a_report_of_a_snapshot_with_no_thresholds_passes_too(self):
        snap, prev, out = self.files(snapshot(header={"aging_after_days": None, "wip_limit_per_person": None}))
        self.assertEqual(hl.check(snap, prev, out), [])

    def test_a_title_may_use_any_word_and_name_any_identifier(self):
        snap, prev, out = self.files(snapshot(set_cell("FERRY-201", title="A slow overloaded boat, see FERRY-999")))
        self.assertEqual(hl.check(snap, prev, out), [])

    def test_a_count_that_is_not_the_number_of_items_listed_is_reported(self):
        self.assertTrue(any("gives the number 5 and lists 4 items" in p for p in self.spoil("- Done (4):", "- Done (5):")))

    def test_a_total_that_is_not_the_snapshots_is_reported(self):
        self.assertTrue(any("first line of section 1" in p for p in self.spoil("can use: 22 of 24. Done: 4.", "can use: 22 of 24. Done: 9.")))

    def test_an_item_moved_from_one_status_to_another_is_reported(self):
        got = self.spoil("- Done (4): `FERRY-201`, `FERRY-213`, `FERRY-214`, `FERRY-215`.", "- Done (4): `FERRY-201`, `FERRY-213`, `FERRY-214`, `FERRY-207`.")
        self.assertTrue(any("does not list as done exactly the items whose status is done" in p for p in got))

    def test_an_item_left_out_of_section_one_is_reported(self):
        got = self.spoil("`FERRY-217`, `FERRY-222`. See section 6.", "`FERRY-222`. See section 6.")
        self.assertTrue(any("does not account for every item" in p for p in got))

    def test_an_item_wrongly_called_aging_is_reported(self):
        got = self.spoil("- Aging (5): `FERRY-203`,", "- Aging (5): `FERRY-202`,")
        self.assertTrue(any("does not list as aging, and as not aging, exactly" in p for p in got))

    def test_an_item_wrongly_called_not_aging_is_reported(self):
        got = self.spoil("- In progress and not aging (5): `FERRY-202`,", "- In progress and not aging (5): `FERRY-218`,")
        self.assertTrue(any("does not list as aging, and as not aging, exactly" in p for p in got))

    def test_a_wrong_number_of_days_is_reported(self):
        self.assertTrue(any("FERRY-203 an update date or a number of days" in p for p in self.spoil("Wed 2026-11-11, 6 days before the snapshot.", "Wed 2026-11-11, 9 days before the snapshot.")))

    def test_a_wrong_update_date_is_reported(self):
        self.assertTrue(any("FERRY-203 an update date or a number of days" in p for p in self.spoil("Wed 2026-11-11, 6 days before the snapshot.", "Wed 2026-11-10, 6 days before the snapshot.")))

    def test_the_title_that_says_blocked_put_in_the_blocked_list_is_reported(self):
        got = self.spoil("- Recorded as blocked, and not done (4): `FERRY-205`,", "- Recorded as blocked, and not done (4): `FERRY-211`,")
        self.assertTrue(any("does not list as blocked exactly" in p for p in got))

    def test_a_wrong_blocker_is_reported(self):
        self.assertTrue(any("FERRY-208 blockers that are not the ones" in p for p in self.spoil("`FERRY-208`: `blocked_by` is FERRY-207.", "`FERRY-208`: `blocked_by` is FERRY-203.")))

    def test_an_item_counted_for_the_wrong_person_is_reported(self):
        got = self.spoil("- \"Tamsin Okoro\": 2 in progress (`FERRY-202`, `FERRY-211`)", "- \"Tamsin Okoro\": 2 in progress (`FERRY-202`, `FERRY-219`)")
        self.assertTrue(any("does not count, for each person" in p for p in got))

    def test_a_count_set_wrongly_beside_the_limit_is_reported(self):
        got = self.spoil("The recorded limit is 2: this is 1 more than the limit.", "The recorded limit is 2: this is at the limit.")
        self.assertTrue(any("does not set the count for \"Jonas Verhoeven\"" in p or "does not set the count for \"Mei Abernathy\"" in p for p in got))

    def test_a_risk_with_its_reason_taken_out_is_reported(self):
        got = self.spoil(" D1: `FERRY-207` is not started (its `status` is `todo`). D2: nobody is recorded as assigned to `FERRY-207` (its `assignee` is `unassigned`).", "")
        self.assertTrue(any("does not say why it is one" in p for p in got))

    def test_a_risk_taken_out_is_reported(self):
        line = [l for l in hl.generate(*self.files(snapshot(), snapshot(day7=False))[:2], None)[1].split("\n") if l.startswith("  - `FERRY-210` waits on `FERRY-208`")][0]
        self.assertTrue(any("does not list as risks exactly" in p for p in self.spoil(line + "\n", "")))

    def test_a_gap_taken_out_is_reported(self):
        line = [l for l in hl.generate(*self.files(snapshot(), snapshot(day7=False))[:2], None)[1].split("\n") if l.startswith("- [GAP] `FERRY-218`")][0]
        self.assertTrue(any("FERRY-218, field updated, is not in section 6" in p for p in self.spoil(line + "\n", "")))

    def test_an_item_that_is_not_in_the_snapshot_is_reported(self):
        self.assertTrue(any("names FERRY-777, which is not in the snapshot" in p for p in self.spoil("## 2. Aging\n", "## 2. Aging\n\nSee also `FERRY-777`.\n")))

    def test_a_second_section_with_a_number_already_used_is_reported(self):
        got = self.spoil("## 2. Aging\n", "## 1. Progress\n\n- Done (0): none.\n\n## 2. Aging\n")
        self.assertTrue(any("two sections with the same number" in p for p in got))

    def test_a_report_of_another_snapshot_is_reported(self):
        snap, prev, out = self.files(snapshot())
        hl.write(snap, snapshot(set_cell("FERRY-201", title="Changed after the report was made")))
        self.assertTrue(any("it was made from another" in p for p in hl.check(snap, prev, out)))

    def test_a_report_compared_with_another_previous_snapshot_is_reported(self):
        snap, prev, out = self.files(snapshot(), snapshot(day7=False))
        hl.write(prev, snapshot(set_cell("FERRY-201", title="Changed after the report was made"), day7=False))
        self.assertTrue(any("does not give the checksum of this previous snapshot" in p for p in hl.check(snap, prev, out)))

    def test_a_judgement_of_a_person_is_reported(self):
        self.assertTrue(any("uses the word \"overloaded\"" in p for p in self.spoil("this is 1 more than the limit", "is overloaded")))

    def test_the_problems_come_in_the_same_order_every_time(self):
        snap, prev, out = self.files(snapshot())
        hl.write(out, hl.read(out).replace("FERRY-20", "FERRY-90"))
        self.assertEqual(hl.check(snap, prev, out), sorted(hl.check(snap, prev, out)))


ROW_207 = "| FERRY-207 | Agree the booking API contract |"


class TheSecondRead(OnDisk):
    """One test for each fault the readers of the second version found."""

    def test_a_count_for_a_name_says_which_items_cannot_be_told(self):
        _, report = report_of(snapshot())
        self.assertIn("recorded as blocked: `FERRY-208`. Aging: none. One or the other cannot be told for: `FERRY-218`.", report)
        self.assertIn("Aging: none. One or the other cannot be told for: none.", report)

    def test_a_wait_on_an_item_whose_own_links_cannot_be_assessed_is_not_said_to_have_no_reason(self):
        for cell in ("", "FERRY-299", "FERRY-217"):
            model, report = report_of(snapshot(set_cells(set_cell("FERRY-204", depends_on="FERRY-202"), set_cell("FERRY-202", blocked_by=cell, depends_on="none"))))
            self.assertEqual(pairs(model, "undecided"), [("FERRY-204", "FERRY-202")], cell)
            self.assertEqual(pairs(model, "plain"), [])
            self.assertIn("D4 cannot be told: one of the links of `FERRY-202` itself could not be assessed.", report)

    def test_a_header_line_written_a_little_differently_is_still_read(self):
        for line in ("-  aging_after_days: 3", " - aging_after_days: 3", "* aging_after_days: 3", "- Aging_After_Days : 3", "- aging_after_days:3"):
            model, _ = report_of(snapshot().replace("- aging_after_days: 3", line))
            self.assertEqual(model["threshold"], 3, line)

    def test_no_section_headed_the_sprint_is_a_gap_and_nothing_is_called_unset(self):
        model, report = report_of(snapshot().replace("## The sprint\n", "## The Sprint\n"))
        self.assertIn("- [GAP] `the snapshot`, field `The sprint`: it has 0 sections headed The sprint, and one is needed. No header line is read.", report)
        self.assertNotIn("none is set", report)
        self.assertNotIn("not recorded", report.split("## How to read this")[0])
        self.assertIn("- Aging threshold: it cannot be read, because the snapshot has 0 sections headed The sprint", report)

    def test_two_sections_headed_the_sprint_are_a_gap_and_neither_is_read(self):
        model, report = report_of(snapshot() + "\n## The sprint\n\n- aging_after_days: 10\n")
        self.assertIsNone(model["threshold"])
        self.assertIn("it has 2 sections headed The sprint", report)

    def test_a_line_in_the_header_with_a_name_the_report_does_not_use_is_not_read_or_printed(self):
        model, report = report_of(snapshot().replace("- aging_after_days: 3\n", "- aging_after_days: 3\n- slow: 1\n- slow: 2\n"))
        self.assertEqual(len(model["gaps"]), 8)
        self.assertNotIn("slow", report)

    def test_an_item_whose_status_cannot_be_used_is_not_listed_as_not_done(self):
        model, report = report_of(snapshot(set_cell("FERRY-217", blocked_by="FERRY-207")))
        self.assertNotIn("FERRY-217", [i for i, _ in model["blocked"]])
        self.assertIn("- Its status cannot be used, and its `blocked_by` names something (1): `FERRY-217`.", report)

    def test_a_snapshot_date_that_cannot_be_used_is_not_called_unrecorded(self):
        _, report = report_of(snapshot(header={"snapshot_date": "17/11/2026"}))
        self.assertIn("# Sprint health report, for a snapshot with no date that can be used", report)
        self.assertIn("- The day everything is counted to: none can be used, see section 6,", report)
        self.assertNotIn("not recorded", report.split("## How to read this")[0])

    def test_a_sprint_line_given_twice_is_not_called_unrecorded(self):
        _, report = report_of(snapshot().replace("- sprint_day: 7 of 10\n", "- sprint_day: 7 of 10\n- sprint_day: 8 of 10\n"))
        self.assertIn("`sprint_day` not usable (see section 6).", report)

    def test_a_threshold_that_was_not_set_is_not_said_to_have_been_unusable(self):
        self.assertIn("THRESHOLD: the aging threshold was not set in the previous snapshot and is 3 in this one. Each snapshot is read by its own.",
                      changes(snapshot(), snapshot(header={"aging_after_days": None})))
        self.assertIn("THRESHOLD: the aging threshold was not set in the previous snapshot and is not usable in this one. Each snapshot is read by its own.",
                      changes(snapshot(header={"aging_after_days": "abc"}), snapshot(header={"aging_after_days": None})))

    def test_an_item_whose_row_cannot_be_used_is_not_said_to_be_absent_or_removed(self):
        self.assertEqual(snapshot().count(ROW_207), 1)
        broken = snapshot().replace(ROW_207, "| FERRY-207 | Agree the booking | API contract |")
        model, report = report_of(broken)
        self.assertNotIn("FERRY-207", model["info"])
        self.assertIn("it has 9 cells and the table has 8 columns. Its first cell is \"FERRY-207\".", report)
        self.assertIn("- [GAP] `FERRY-208`, field `blocked_by`: it names FERRY-207, whose row cannot be used.", report)
        self.assertIn("  - `FERRY-208`: `blocked_by` is FERRY-207. The row of `FERRY-207` cannot be used.", report)
        self.assertNotIn("FERRY-207` is not in the snapshot", report)
        got = changes(broken, snapshot())
        self.assertIn("ROW NOT USABLE NOW: `FERRY-207` was in the previous snapshot, and its row in this one cannot be used.", got)
        self.assertFalse(any(line.startswith("REMOVED") for line in got))
        back = changes(snapshot(), broken)
        self.assertIn("ROW NOT USABLE BEFORE: `FERRY-207` is in this snapshot, and its row in the previous one cannot be used.", back)
        self.assertFalse(any(line.startswith("ADDED") for line in back))

    def test_an_item_on_two_rows_is_not_said_to_be_absent(self):
        def double(rows):
            rows.append(list(rows[6]))
        _, report = report_of(snapshot(double))
        self.assertIn("it names FERRY-207, whose row cannot be used", report)

    def test_a_chain_that_a_loop_member_waits_on_is_still_reported(self):
        model, _ = report_of(snapshot(set_cell("FERRY-224", depends_on="FERRY-216, FERRY-210")))
        self.assertEqual(model["loops"], [["FERRY-216", "FERRY-224"]])
        self.assertEqual(model["chains"], [("FERRY-210", "FERRY-208", "FERRY-207")])

    def test_with_no_threshold_the_days_are_still_shown(self):
        _, report = report_of(snapshot(header={"aging_after_days": None}))
        self.assertIn("- In progress, with an `updated` date that can be used (10):", section(report, 2))
        self.assertIn("  - `FERRY-203`: `updated` is Wed 2026-11-11, 6 days before the snapshot.", section(report, 2))
        self.assertNotIn("- Aging (", section(report, 2))

    def test_a_created_date_after_the_snapshot_is_a_gap(self):
        _, report = report_of(snapshot(set_cell("FERRY-201", created="2027-01-01", updated="2027-01-02")))
        self.assertIn("- [GAP] `FERRY-201`, field `created`: it is 2027-01-01, which is after the snapshot's own date, 2026-11-17.", report)

    def test_other_quotation_marks_and_unseen_characters_cannot_end_a_quotation(self):
        self.assertEqual(hl.safe("x" + chr(0x201d) + " y" + chr(0x200b) + chr(0xff02) + chr(0x85) + "z"), "x' y ' z")

    def test_the_previous_snapshot_dated_later_is_said(self):
        self.assertIn("ORDER: the snapshot given as previous is dated 2026-11-17, which is after this one's date, 2026-11-16.", changes(snapshot(day7=False), snapshot()))
        self.assertFalse(any(line.startswith("ORDER") for line in changes(snapshot(), snapshot(day7=False))))

    def test_the_day_six_snapshot_does_not_describe_what_is_only_in_day_seven(self):
        self.assertNotIn("FERRY-216 and FERRY-224", snapshot(day7=False))
        self.assertIn("FERRY-216 and FERRY-224", snapshot())

    def test_the_check_passes_a_report_whose_previous_snapshot_names_an_item_in_neither(self):
        snap, prev, out = self.files(snapshot(), snapshot(set_cell("FERRY-221", blocked_by="FERRY-298"), day7=False))
        self.assertIn("was FERRY-298 and is now FERRY-299", hl.read(out))
        self.assertEqual(hl.check(snap, prev, out), [])

    def test_the_check_reports_a_wrong_number_of_risks_or_of_waits(self):
        self.assertTrue(any("does not give the number of waits" in p for p in self.spoil("- Waits that are a risk (7):", "- Waits that are a risk (3):")))
        self.assertTrue(any("does not give the number of waits" in p for p in self.spoil("- Waits in all: 7, on 5 different items:", "- Waits in all: 7, on 4 different items:")))

    def test_the_check_reports_a_threshold_changed_at_the_top_of_the_report(self):
        self.assertTrue(any("does not show the aging threshold" in p for p in self.spoil("- Aging threshold: 3 days,", "- Aging threshold: 9 days,")))
        self.assertTrue(any("does not show the aging threshold" in p for p in self.spoil("last updated more than 3 days before", "last updated more than 9 days before")))


if __name__ == "__main__":
    unittest.main()
