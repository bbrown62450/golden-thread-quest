"""Tests for rank.py. They contact nothing and write only to a scratch folder.

    python3 -m unittest discover -s participant/skills/context-next-work/tests -v
"""
import copy
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import make_inputs   # noqa: E402
import rank          # noqa: E402

NOW = "2026-12-01T09:00:00Z"
HOURS = {"work-item-status": 24, "decision": 2160}
FRESH = "2026-12-01T07:00:00Z"


def w(number, **fields):
    record = {"identity": "jira:%d" % number, "kind": "work", "title": "Item %d" % number, "status": "open",
              "priority": "medium", "due": "2026-12-10", "created": "2026-11-01", "retrieved_at": FRESH}
    record.update(fields)
    return {k: v for k, v in record.items() if v is not None}


def d(number, status):
    return {"identity": "decision:E-%d" % number, "kind": "decision", "title": "Decision %d" % number, "status": status, "retrieved_at": FRESH}


def run(*records, rule="priority-first", now=NOW):
    return rank.analyse({r["identity"]: r for r in records}, now, HOURS, rule)


def order(found):
    return [i["identity"] for i in found["ranked"]]


def J(number):
    return "jira:%d" % number


def as_text(records, clock=NOW):
    head = "- clock: `%s`\n\n" % clock if clock else ""
    return head + "\n".join("### %s\n\n```json\n%s\n```\n" % (r["identity"], json.dumps(r, indent=2)) for r in records)


HANDED_IN, CLOCK = rank.read_inputs(make_inputs.text())
REAL_HOURS = rank.limits(rank.read(rank.POLICY))


def handed_in(rule="priority-first", change=None):
    records = copy.deepcopy(HANDED_IN)
    if change:
        change(records)
    return rank.analyse(records, CLOCK, REAL_HOURS, rule)


class Criteria(unittest.TestCase):
    def test_priority_decides_first(self):
        found = run(w(1, priority="low", due="2026-12-02"), w(2, priority="high", due="2026-12-30"), w(3, priority="medium"))
        self.assertEqual(order(found), [J(2), J(3), J(1)])

    def test_due_date_decides_between_equal_priorities(self):
        self.assertEqual(order(run(w(1, due="2026-12-09"), w(2, due="2026-12-03"))), [J(2), J(1)])

    def test_waiters_decide_between_equal_priority_and_due(self):
        found = run(w(1), w(2, blocks=[J(3)]), w(3, blocked_by=[J(2)]))
        self.assertEqual(order(found), [J(2), J(1)])
        self.assertEqual(found["items"][J(2)]["waiters"], 1)

    def test_created_decides_next(self):
        self.assertEqual(order(run(w(1, created="2026-11-05"), w(2, created="2026-11-02"))), [J(2), J(1)])

    def test_identity_decides_last(self):
        found = run(w(2), w(1))
        self.assertEqual(order(found), [J(1), J(2)])
        self.assertEqual(found["items"][J(2)]["below"], (J(1), "identity"))

    def test_a_later_criterion_never_overrides_an_earlier_one(self):
        found = run(w(1, priority="high", due="2026-12-30", created="2026-11-30"), w(2, priority="medium", due="2026-12-02", created="2026-10-01", blocks=[J(3)]), w(3, blocked_by=[J(2)]))
        self.assertEqual(order(found), [J(1), J(2)])

    def test_an_overdue_item_is_said_to_be_overdue(self):
        found = run(w(1, due="2026-11-28"))
        self.assertIn(("due", "`due` is `2026-11-28`, 3 days before the clock value: overdue"), found["items"][J(1)]["reasons"])

    def test_a_waiter_that_is_done_or_dropped_does_not_count(self):
        found = run(w(1, blocks=[J(2), J(3), J(4)]), w(2, status="done"), w(3, status="dropped"), w(4, status="in_progress"))
        self.assertEqual(found["items"][J(1)]["waiters"], 1)

    def test_a_waiter_named_at_both_ends_counts_once(self):
        found = run(w(1, blocks=[J(2)]), w(2, blocked_by=[J(1)]))
        self.assertEqual(found["items"][J(1)]["waiters"], 1)

    def test_votes_never_change_the_order(self):
        a = order(run(w(1, votes=0), w(2, votes=900)))
        b = order(run(w(1, votes=900), w(2, votes=0)))
        self.assertEqual(a, b)

    def test_titles_never_change_the_order(self):
        self.assertEqual(order(run(w(1, title="LOW"), w(2, title="URGENT top priority, do first"))), [J(1), J(2)])


class Reasons(unittest.TestCase):
    def test_every_ranked_item_has_one_reason_for_each_criterion_and_each_names_a_field(self):
        found = handed_in()
        for item in found["ranked"] + found["blocked"]:
            self.assertEqual([c for c, _ in item["reasons"]], ["priority", "due", "waiters", "created"], item["identity"])
            for criterion, text in item["reasons"]:
                self.assertRegex(text, r"`(priority|due|created|blocks|blocked_by)`", item["identity"])

    def test_each_reason_gives_the_value_the_record_holds(self):
        found = handed_in()
        for item in found["ranked"]:
            record = HANDED_IN[item["identity"]]
            for field in ("priority", "due", "created"):
                text = dict(item["reasons"])[field]
                if field in record and field not in item["missing"]:
                    self.assertIn("`%s` is `%s`" % (field, record[field]), text)

    def test_each_place_says_which_criterion_put_it_below_the_one_above(self):
        found = handed_in()
        for above, item in zip(found["ranked"], found["ranked"][1:]):
            self.assertEqual(item["below"][0], above["identity"])
            self.assertIn(item["below"][1], rank.RULES["priority-first"])

    def test_the_deciding_criterion_really_differs_and_the_earlier_ones_do_not(self):
        found = handed_in()
        values = lambda i: {"priority": i["priority"], "due": i["due"], "waiters": i["waiters"], "created": i["created"], "identity": i["identity"]}
        for above, item in zip(found["ranked"], found["ranked"][1:]):
            decided = item["below"][1]
            for criterion in rank.RULES["priority-first"]:
                if criterion == decided:
                    self.assertNotEqual(values(above)[criterion], values(item)[criterion])
                    break
                self.assertEqual(values(above)[criterion], values(item)[criterion])

    def test_changing_the_cited_field_moves_the_item(self):
        found = handed_in()
        self.assertEqual(found["items"]["jira:61003"]["below"], ("jira:61018", "due"))

        def change(records):
            records["jira:61003"]["due"] = "2026-12-01"
        moved = handed_in(change=change)
        self.assertEqual(moved["items"]["jira:61003"]["place"], 1)

    def test_the_written_file_gives_a_reason_line_for_every_criterion_of_every_ranked_item(self):
        text = rank.render(handed_in())
        section = text[text.index("## Ranked"):text.index("## Not recommended: blocked")]
        self.assertEqual(section.count("\n### "), 13)
        for criterion in ("priority", "due", "waiters", "created"):
            self.assertEqual(section.count("\n- Reason, %s: " % criterion), 13)

    def test_why_an_item_is_not_first_is_stated(self):
        text = rank.render(handed_in())
        self.assertIn("- Why it is not first: due decides against `jira:61004`.", text)
        self.assertIn("- It is first because no other ranked item comes before it on priority, then due, then waiters, then created.", text)


class Blocked(unittest.TestCase):
    def test_a_blocked_item_is_not_ranked_and_its_blocker_is_named(self):
        found = run(w(1, priority="high", blocked_by=[J(2)]), w(2, priority="low"))
        self.assertEqual(order(found), [J(2)])
        self.assertEqual([b["identity"] for b in found["blocked"][0]["blockers"]], [J(2)])

    def test_a_blocker_recorded_only_on_the_other_record(self):
        found = run(w(1), w(2, blocks=[J(1)]))
        self.assertEqual(found["items"][J(1)]["list"], "blocked")
        self.assertEqual(found["items"][J(1)]["blockers"][0]["sources"], ["`blocks` on `jira:2`"])

    def test_a_done_blocker_does_not_block(self):
        self.assertEqual(run(w(1, blocked_by=[J(2)]), w(2, status="done"))["items"][J(1)]["list"], "ranked")

    def test_a_dropped_blocker_still_blocks(self):
        self.assertEqual(run(w(1, blocked_by=[J(2)]), w(2, status="dropped"))["items"][J(1)]["list"], "blocked")

    def test_a_blocker_with_no_record_blocks_and_is_named(self):
        found = run(w(1, blocked_by=[J(9)]))
        self.assertEqual(found["items"][J(1)]["list"], "blocked")
        self.assertIn("has no record", found["items"][J(1)]["blockers"][0]["state"])

    def test_an_undecided_decision_blocks_and_a_decided_one_does_not(self):
        found = run(w(1, needs_decision=["decision:E-1"]), w(2, needs_decision=["decision:E-2"]), d(1, "question"), d(2, "decided"))
        self.assertEqual((found["items"][J(1)]["list"], found["items"][J(2)]["list"]), ("blocked", "ranked"))

    def test_two_blockers_are_both_named(self):
        found = run(w(1, blocked_by=[J(2), J(3)]), w(2), w(3))
        self.assertEqual([b["identity"] for b in found["items"][J(1)]["blockers"]], [J(2), J(3)])

    def test_a_stale_blocker_is_said_to_be_stale(self):
        found = run(w(1, blocked_by=[J(2)]), w(2, retrieved_at="2026-11-20T09:00:00Z"))
        self.assertIn("so this item may no longer be blocked", found["items"][J(1)]["blockers"][0]["state"])

    def test_a_link_that_is_not_an_identity_is_warned_about_and_not_guessed(self):
        found = run(w(1, blocked_by=["2"]), w(2))
        item = found["items"][J(1)]
        self.assertEqual(item["list"], "ranked")
        self.assertTrue(any("is not an identity" in warning for warning in item["warnings"]))
        self.assertEqual(item["confidence"], "medium")

    def test_the_six_handed_in_blocked_items_and_their_blockers(self):
        found = handed_in()
        self.assertEqual({i["identity"]: [b["identity"] for b in i["blockers"]] for i in found["blocked"]},
                         {"jira:61005": ["jira:61001"], "jira:61009": ["jira:61001"], "jira:61010": ["decision:E-301"], "jira:61014": ["jira:61099"],
                          "jira:61017": ["jira:61018"], "github:I_kwFIXnw00001": ["jira:61012"]})

    def test_no_blocked_item_has_a_place_and_the_file_names_each_blocker(self):
        found = handed_in()
        text = rank.render(found)
        for item in found["blocked"]:
            self.assertNotIn("place", item)
            self.assertIn("- BLOCKED BY `%s`" % item["blockers"][0]["identity"], text)


class NotOffered(unittest.TestCase):
    def test_assigned_in_progress_done_and_dropped_are_not_offered_with_the_field_cited(self):
        found = run(w(1, assigned_to="Developer B"), w(2, status="in_progress"), w(3, status="done"), w(4, status="dropped"), w(5))
        self.assertEqual(order(found), [J(5)])
        self.assertEqual([i["why"] for i in found["not_offered"]], ["`assigned_to` is `Developer B`", "`status` is `in_progress`", "`status` is `done`", "`status` is `dropped`"])

    def test_no_status_is_not_offered(self):
        self.assertEqual(run(w(1, status=None))["not_offered"][0]["why"], "`status` is not recorded")

    def test_a_decision_is_never_ranked(self):
        self.assertEqual(run(d(1, "question"), w(1))["items"].keys(), {J(1)})


class Stale(unittest.TestCase):
    def test_exactly_at_the_limit_is_fresh_and_one_second_over_is_stale(self):
        found = run(w(1, retrieved_at="2026-11-30T09:00:00Z"), w(2, retrieved_at="2026-11-30T08:59:59Z"))
        self.assertEqual((found["items"][J(1)]["stale"], found["items"][J(2)]["stale"]), (False, True))

    def test_no_retrieved_at_an_unreadable_one_and_a_future_one_are_stale(self):
        found = run(w(1, retrieved_at=None), w(2, retrieved_at="yesterday"), w(3, retrieved_at="2026-12-02T09:00:00Z"), w(4, retrieved_at="2026-12-01"))
        self.assertTrue(all(found["items"][J(n)]["stale"] for n in (1, 2, 3, 4)))

    def test_a_stale_item_keeps_its_place_and_carries_a_warning(self):
        found = run(w(1, priority="high", retrieved_at="2026-11-24T09:00:00Z"), w(2))
        self.assertEqual(order(found), [J(1), J(2)])
        self.assertTrue(found["items"][J(1)]["warnings"][0].startswith("STALE CONTEXT: `retrieved_at` is `2026-11-24T09:00:00Z`, 7 days before the clock value."))

    def test_start_here_is_the_first_fresh_item(self):
        found = run(w(1, priority="high", retrieved_at="2026-11-24T09:00:00Z"), w(2), w(3, priority="low"))
        self.assertEqual(found["pick"]["identity"], J(2))

    def test_with_nothing_fresh_nothing_is_recommended(self):
        found = run(w(1, retrieved_at="2026-11-24T09:00:00Z"))
        self.assertIsNone(found["pick"])
        self.assertIn("**Nothing can be recommended.**", rank.render(found))

    def test_the_three_handed_in_stale_ranked_items_each_carry_the_warning_in_the_file(self):
        found = handed_in()
        self.assertEqual([i["identity"] for i in found["ranked"] if i["stale"]], ["jira:61004", "jira:61018", "jira:61016"])
        text = rank.render(found)
        self.assertEqual(text[text.index("## Ranked"):text.index("## Not recommended")].count("- WARNING: STALE CONTEXT:"), 3)

    def test_the_handed_in_pick_is_second_place_and_the_stale_first_place_is_named(self):
        found = handed_in()
        self.assertEqual((found["ranked"][0]["identity"], found["pick"]["identity"]), ("jira:61004", "jira:61001"))
        text = rank.render(found)
        start = text[text.index("## Start here"):text.index("## Ranked")]
        self.assertIn("It is not first on the recorded fields.", start)
        self.assertIn("- `jira:61004` \"Weekly menu import\", place 1. STALE CONTEXT:", start)

    def test_the_limit_comes_from_the_freshness_policy(self):
        self.assertEqual(REAL_HOURS["work-item-status"], 24)
        self.assertEqual(rank.limits("| `work-item-status` | 2 days | x |\n| `decision` | 90 days | y |")["work-item-status"], 48)
        with self.assertRaises(rank.InputError):
            rank.limits("no table here")

    def test_a_stale_blocked_item_carries_the_warning_too(self):
        text = rank.render(handed_in())
        dark = text[text.index("### `github:I_kwFIXnw00001`"):text.index("### `jira:61009`")]
        self.assertIn("- WARNING: STALE CONTEXT:", dark)


class Missing(unittest.TestCase):
    def test_a_missing_priority_goes_after_every_priority_and_is_reported(self):
        found = run(w(1, priority=None, due="2026-12-01"), w(2, priority="low", due="2026-12-30"))
        self.assertEqual(order(found), [J(2), J(1)])
        self.assertIn(("priority", "`priority` is not recorded. It is placed after every item that has one"), found["items"][J(1)]["reasons"])

    def test_a_missing_due_date_goes_after_every_due_date_of_the_same_priority(self):
        self.assertEqual(order(run(w(1, due=None), w(2, due="2027-06-01"))), [J(2), J(1)])

    def test_an_unreadable_value_is_missing_and_is_quoted(self):
        found = run(w(1, due="soon", priority="urgent!!"))
        reasons = dict(found["items"][J(1)]["reasons"])
        self.assertIn("`due` is `\"soon\"`, which is not a date", reasons["due"])
        self.assertIn("`priority` is `\"urgent!!\"`, which is not high, medium or low", reasons["priority"])

    def test_a_date_that_does_not_exist_is_missing(self):
        self.assertEqual(run(w(1, due="2026-02-30"))["items"][J(1)]["missing"], ["due"])

    def test_nothing_is_filled_in(self):
        records = {J(1): w(1, priority=None, due=None)}
        before = copy.deepcopy(records)
        found = rank.analyse(records, NOW, HOURS)
        self.assertEqual(records, before)
        self.assertNotIn("medium", rank.render(found).split("## To disagree")[0].replace("confidence medium", "").replace("Confidence: medium", ""))

    def test_confidence_falls_one_step_for_each_missing_field_and_for_a_stale_copy(self):
        found = run(w(1), w(2, due=None), w(3, due=None, priority=None), w(4, due=None, priority=None, created=None), w(5, retrieved_at=None), w(6, retrieved_at=None, due=None))
        self.assertEqual([found["items"][J(n)]["confidence"] for n in range(1, 7)], ["high", "medium", "low", "low", "medium", "low"])

    def test_confidence_does_not_change_the_place(self):
        found = run(w(1, priority="high", due=None, created=None), w(2, priority="medium"))
        self.assertEqual(order(found), [J(1), J(2)])
        self.assertEqual(found["items"][J(1)]["confidence"], "low")

    def test_the_handed_in_items_with_missing_data(self):
        found = handed_in()
        self.assertEqual({i["identity"]: i["missing"] for i in found["items"].values() if i["missing"]},
                         {"jira:61009": ["priority"], "jira:61015": ["due"], "trello:7b2e000000000000000e0001": ["due"], "trello:7b2e000000000000000e0002": ["priority", "due"],
                          "jira:61013": ["due"]})
        self.assertEqual(found["items"]["trello:7b2e000000000000000e0002"]["confidence"], "low")


class SameEveryRun(unittest.TestCase):
    def test_two_runs_give_the_same_text(self):
        self.assertEqual(rank.render(handed_in()), rank.render(handed_in()))

    def test_the_order_of_the_records_does_not_matter(self):
        expected = rank.render(handed_in())
        for seed in range(5):
            records = [copy.deepcopy(r) for r in make_inputs.RECORDS]
            random.Random(seed).shuffle(records)
            got = rank.analyse(rank.read_inputs(as_text(records, CLOCK))[0], CLOCK, REAL_HOURS)
            self.assertEqual(rank.render(got), expected, seed)

    def test_the_computers_clock_is_not_read(self):
        source = rank.read(os.path.join(os.path.dirname(HERE), "rank.py"))
        for call in ("datetime.now", "utcnow", "date.today", "time.time", "import time"):
            self.assertNotIn(call, source.split('"""', 2)[2], call)

    def test_separate_processes_with_different_hash_seeds_write_the_same_file(self):
        code = ("import sys; sys.path.insert(0, %r); import rank, make_inputs; r, c = rank.read_inputs(make_inputs.text()); "
                "sys.stdout.write(rank.render(rank.analyse(r, c, rank.limits(rank.read(rank.POLICY)))))" % os.path.dirname(HERE))
        outputs = set()
        for seed in ("0", "1", "2"):
            done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=dict(os.environ, PYTHONHASHSEED=seed))
            self.assertEqual(done.returncode, 0, done.stderr)
            outputs.add(done.stdout)
        self.assertEqual(outputs, {rank.render(handed_in())})

    def test_a_different_clock_value_is_a_different_input(self):
        later = rank.analyse(copy.deepcopy(HANDED_IN), "2026-12-03T09:00:00Z", REAL_HOURS)
        self.assertIsNone(later["pick"])

    def test_the_handed_in_files_are_what_the_code_writes(self):
        self.assertEqual(rank.read(os.path.join(rank.FOLDER, "inputs.md")), make_inputs.text())
        self.assertEqual(rank.read(os.path.join(rank.FOLDER, "recommendation.md")), rank.render(handed_in()))
        self.assertEqual(rank.read(os.path.join(rank.FOLDER, "rules.md")), rank.rules_text(REAL_HOURS))

    def test_the_handed_in_order(self):
        self.assertEqual(order(handed_in()), ["jira:61004", "jira:61001", "jira:61002", "jira:61018", "jira:61003", "trello:7b2e000000000000000e0001", "jira:61006", "jira:61007",
                                              "jira:61016", "jira:61019", "jira:61015", "jira:61008", "trello:7b2e000000000000000e0002"])


class AfterADependencyIsCompleted(unittest.TestCase):
    def change(self, records):
        records["jira:61001"]["status"] = "done"

    def test_what_waited_on_it_enters_the_ranking_and_it_leaves(self):
        before, after = handed_in(), handed_in(change=self.change)
        self.assertEqual(after["items"]["jira:61001"]["list"], "not offered")
        self.assertEqual((after["items"]["jira:61005"]["place"], after["items"]["jira:61009"]["place"]), (9, 13))
        self.assertEqual(after["pick"]["identity"], "jira:61002")
        self.assertEqual(len(before["blocked"]) - len(after["blocked"]), 2)

    def test_the_change_is_explained_by_the_field_that_changed(self):
        lines = rank.changes(handed_in(), handed_in(change=self.change))
        self.assertEqual(lines[0], "Fields that differ between the two inputs: `status` of `jira:61001`: \"open\" -> \"done\"")
        text = "\n".join(lines)
        self.assertIn("jira:61005                       blocked      -> place 9      because it was blocked by jira:61001, and that is finished in the second input.", text)
        self.assertIn("jira:61001                       place 2      -> not offered  because in the second input its `status` is `done`.", text)
        self.assertIn("Start here: jira:61001 -> jira:61002.", text)

    def test_an_item_that_only_shifted_says_what_moved_above_it(self):
        text = "\n".join(rank.changes(handed_in(), handed_in(change=self.change)))
        self.assertIn("jira:61002                       place 3      -> place 2      because its own fields are unchanged. Above it, jira:61001 left the ranking.", text)

    def test_no_change_in_the_inputs_gives_no_change(self):
        self.assertEqual(rank.changes(handed_in(), handed_in()), ["Fields that differ between the two inputs: none"])


class AnotherRule(unittest.TestCase):
    def test_due_first_puts_the_low_priority_item_due_tomorrow_near_the_top(self):
        found = handed_in("due-first")
        self.assertEqual(order(found)[:3], ["jira:61004", "jira:61008", "jira:61001"])
        self.assertEqual(found["pick"]["identity"], "jira:61008")
        self.assertEqual(handed_in()["items"]["jira:61008"]["place"], 12)

    def test_the_two_rules_use_the_same_criteria_in_another_order(self):
        self.assertEqual(sorted(rank.RULES["due-first"]), sorted(rank.RULES["priority-first"]))
        self.assertEqual(sorted(order(handed_in("due-first"))), sorted(order(handed_in())))

    def test_an_unknown_rule_is_refused(self):
        with self.assertRaises(rank.InputError):
            run(w(1), rule="most-votes")


class Command(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.mkdtemp(prefix="gtq-rank-")
        self.addCleanup(shutil.rmtree, self.scratch, True)
        self.inputs = os.path.join(self.scratch, "inputs.md")

    def write(self, text):
        with open(self.inputs, "w", encoding="utf-8") as f:
            f.write(text)

    def run_main(self, *argv):
        said = []
        return rank.main(["rank", "--inputs", self.inputs] + list(argv), say=said.append), said

    def test_a_run_writes_the_recommendation_and_leaves_the_inputs_alone(self):
        self.write(make_inputs.text())
        code, said = self.run_main()
        self.assertEqual(code, 0)
        self.assertEqual(rank.read(self.inputs), make_inputs.text())
        self.assertEqual(sorted(os.listdir(self.scratch)), ["inputs.md", "recommendation.md"])
        self.assertIn("Start here: jira:61001, place 2", said)
        self.assertEqual(said[-1], "Wrote recommendation.md. Nothing was started, assigned or changed.")

    def test_no_clock_value_is_refused_and_nothing_is_written(self):
        self.write(as_text([w(1)], clock=None))
        code, said = self.run_main()
        self.assertEqual(code, 2)
        self.assertIn("No clock value was given. The computer's clock is not read.", said[-1])
        self.assertEqual(os.listdir(self.scratch), ["inputs.md"])

    def test_now_overrides_the_clock_in_the_inputs(self):
        self.write(as_text([w(1)]))
        code, said = self.run_main("--now", "2026-12-05T09:00:00Z")
        self.assertEqual(code, 0)
        self.assertIn("Clock value: 2026-12-05T09:00:00Z.", said[0])
        self.assertIn("STALE", said[1])

    def test_a_clock_value_that_is_not_a_time_is_refused(self):
        self.write(as_text([w(1)]))
        self.assertEqual(self.run_main("--now", "today")[0], 2)

    def test_two_records_with_one_identity_are_refused(self):
        self.write(as_text([w(1), w(1)]))
        code, said = self.run_main()
        self.assertEqual(code, 2)
        self.assertIn("Two records have the identity jira:1", said[-1])

    def test_no_records_is_refused(self):
        self.write("- clock: `%s`\n" % NOW)
        self.assertEqual(self.run_main()[0], 2)

    def test_writing_over_the_inputs_is_refused(self):
        self.write(as_text([w(1)]))
        code, said = self.run_main("--out", self.inputs)
        self.assertEqual(code, 2)
        self.assertEqual(rank.read(self.inputs), as_text([w(1)]))

    def test_a_missing_freshness_policy_is_refused(self):
        self.write(as_text([w(1)]))
        code, said = self.run_main("--policy", os.path.join(self.scratch, "none.md"))
        self.assertEqual(code, 2)
        self.assertIn("freshness policy could not be read", said[-1])

    def test_the_rule_can_be_chosen(self):
        self.write(make_inputs.text())
        code, said = self.run_main("--rule", "due-first")
        self.assertIn("Start here: jira:61008, place 2", said)

    def test_no_command_explains_itself(self):
        self.assertEqual(rank.main([], say=lambda line: None), 2)


if __name__ == "__main__":
    unittest.main()
