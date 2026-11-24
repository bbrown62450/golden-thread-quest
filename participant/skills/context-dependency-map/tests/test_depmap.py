"""Tests for depmap.py. They contact nothing and write only to a scratch folder.

    python3 -m unittest discover -s participant/skills/context-dependency-map/tests -v
"""
import json
import os
import random
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import depmap      # noqa: E402
import make_data   # noqa: E402


def w(number, status="open", **more):
    record = {"identity": "jira:%d" % number, "kind": "work", "title": "Item %d" % number, "status": status}
    record.update(more)
    return record


def d(number, status="decided", **more):
    record = {"identity": "decision:E-%d" % number, "kind": "decision", "title": "Decision %d" % number, "status": status}
    record.update(more)
    return record


def found(*records):
    return depmap.analyse({r["identity"]: r for r in records})


def J(number):
    return "jira:%d" % number


def as_text(records):
    return "\n".join("### %s\n\n```json\n%s\n```\n" % (r["identity"], json.dumps(r, indent=2)) for r in records)


HANDED_IN = depmap.read_records(make_data.text())


class RecordedFieldsOnly(unittest.TestCase):
    def test_blocked_by_makes_a_link_from_the_record_to_the_one_named(self):
        got = found(w(1, blocked_by=[J(2)]), w(2))
        self.assertEqual(list(got["links"]), [(J(1), J(2))])
        self.assertEqual(got["links"][(J(1), J(2))], {("blocked_by", J(1))})

    def test_blocks_makes_the_same_link_from_the_other_end(self):
        got = found(w(1), w(2, blocks=[J(1)]))
        self.assertEqual(got["links"], {(J(1), J(2)): {("blocks", J(2))}})

    def test_a_link_written_at_both_ends_is_one_link_with_two_sources(self):
        got = found(w(1, blocked_by=[J(2)]), w(2, blocks=[J(1)]))
        self.assertEqual(got["links"], {(J(1), J(2)): {("blocked_by", J(1)), ("blocks", J(2))}})
        self.assertEqual(got["one_sided"], [])

    def test_a_link_written_twice_on_one_record_is_one_link(self):
        got = found(w(1, blocked_by=[J(2), J(2)]), w(2))
        self.assertEqual(len(got["links"]), 1)
        self.assertEqual(got["blocked"][J(2)], [J(1)])

    def test_a_title_that_names_another_item_makes_no_link(self):
        got = found(w(1, title="Do this once jira:2 is done, blocked by jira:2"), w(2))
        self.assertEqual(got["links"], {})

    def test_a_description_and_labels_make_no_link(self):
        got = found(w(1, description="Depends on jira:2. blocked_by: jira:2", labels=["jira:2"]), w(2))
        self.assertEqual(got["links"], {})

    def test_parent_and_related_make_no_link_and_are_listed_as_seen(self):
        got = found(w(1, parent=J(2), related=[J(2)]), w(2))
        self.assertEqual(got["links"], {})
        self.assertEqual([(n, f) for n, f, _ in got["not_counted"]], [(J(1), "parent"), (J(1), "related")])

    def test_superseded_by_makes_no_link(self):
        got = found(d(1, "superseded", superseded_by="decision:E-2"), d(2))
        self.assertEqual(got["links"], {})

    def test_the_handed_in_item_whose_title_and_description_name_two_others_has_no_link(self):
        got = depmap.analyse(HANDED_IN)
        self.assertEqual(got["waits_on"]["jira:52023"], [])
        self.assertNotIn("jira:52023", got["waited_by"]["jira:52003"])
        self.assertEqual(got["waits_on"]["jira:52024"], [])

    def test_changing_every_title_and_description_changes_no_link(self):
        changed = {k: dict(v, title="blocked by jira:52001", description="waits on jira:52002") for k, v in HANDED_IN.items()}
        self.assertEqual(depmap.analyse(changed)["links"], depmap.analyse(HANDED_IN)["links"])

    def test_one_sided_links_say_which_end_wrote_them(self):
        got = found(w(1, blocked_by=[J(2)]), w(2), w(3, blocks=[J(4)]), w(4))
        self.assertEqual(got["one_sided"], [(J(1), J(2), ("blocked_by", J(1))), (J(4), J(3), ("blocks", J(3)))])


class Indexes(unittest.TestCase):
    def setUp(self):
        self.got = found(w(1, blocked_by=[J(2), J(3)]), w(2, blocked_by=[J(3)]), w(3), w(4))

    def test_forward(self):
        self.assertEqual(self.got["waits_on"], {J(1): [J(2), J(3)], J(2): [J(3)], J(3): [], J(4): []})

    def test_reverse_is_the_forward_index_turned_round(self):
        self.assertEqual(self.got["waited_by"], {J(1): [], J(2): [J(1)], J(3): [J(1), J(2)], J(4): []})

    def test_in_the_handed_in_data_each_index_holds_every_link_exactly_once(self):
        got = depmap.analyse(HANDED_IN)
        forward = sorted((a, b) for a in got["waits_on"] for b in got["waits_on"][a])
        reverse = sorted((a, b) for b in got["waited_by"] for a in got["waited_by"][b])
        self.assertEqual(forward, sorted(got["links"]))
        self.assertEqual(reverse, sorted(got["links"]))
        self.assertEqual(len(forward), 28)

    def test_both_indexes_are_in_the_written_file_with_every_item(self):
        text = depmap.render(depmap.analyse(HANDED_IN))
        forward = text[text.index("## Forward index"):text.index("## Reverse index")]
        reverse = text[text.index("## Reverse index"):text.index("## Links written at one end only")]
        for part in (forward, reverse):
            self.assertEqual(part.count("\n### "), 41)
        self.assertIn("- Waits on `jira:52001` \"Timetable schema\". waiting. From `blocked_by` on `jira:52002`; `blocks` on `jira:52001`.", forward)
        self.assertIn("- Waited on by `jira:52002` \"Import operator timetables\". waiting. From `blocked_by` on `jira:52002`; `blocks` on `jira:52001`.", reverse)


class Cycles(unittest.TestCase):
    def test_two_items_that_wait_on_each_other(self):
        got = found(w(1, blocked_by=[J(2)]), w(2, blocked_by=[J(1)]), w(3))
        self.assertEqual(got["cycles"], [[J(1), J(2)]])
        self.assertEqual(got["problems"]["cycles"][0][1], [J(1), J(2), J(1)])

    def test_a_cycle_of_three_with_its_members_and_one_way_round(self):
        got = found(w(1, blocked_by=[J(3)]), w(2, blocked_by=[J(1)]), w(3, blocked_by=[J(2)]))
        self.assertEqual(got["problems"]["cycles"], [([J(1), J(2), J(3)], [J(1), J(3), J(2), J(1)])])

    def test_a_cycle_closed_by_a_blocks_field(self):
        got = found(w(1, blocked_by=[J(2)]), w(2), w(1 + 2, blocks=[J(2)], blocked_by=[J(1)]))
        self.assertEqual(got["cycles"], [[J(1), J(2), J(3)]])

    def test_a_cycle_through_a_decision(self):
        got = found(w(1, needs_decision=["decision:E-1"]), d(1, "question", blocked_by=[J(1)]))
        self.assertEqual(got["cycles"], [["decision:E-1", J(1)]])

    def test_a_chain_is_not_a_cycle(self):
        got = found(w(1, blocked_by=[J(2)]), w(2, blocked_by=[J(3)]), w(3))
        self.assertEqual(got["cycles"], [])

    def test_two_ways_to_the_same_item_are_not_a_cycle(self):
        got = found(w(1, blocked_by=[J(2), J(3)]), w(2, blocked_by=[J(4)]), w(3, blocked_by=[J(4)]), w(4))
        self.assertEqual(got["cycles"], [])

    def test_two_separate_cycles_are_reported_separately(self):
        got = found(w(1, blocked_by=[J(2)]), w(2, blocked_by=[J(1)]), w(3, blocked_by=[J(4)]), w(4, blocked_by=[J(3)]))
        self.assertEqual(got["cycles"], [[J(1), J(2)], [J(3), J(4)]])

    def test_two_cycles_that_share_an_item_are_one_group(self):
        got = found(w(1, blocked_by=[J(2)]), w(2, blocked_by=[J(1), J(3)]), w(3, blocked_by=[J(2)]))
        self.assertEqual(got["cycles"], [[J(1), J(2), J(3)]])

    def test_an_item_that_waits_on_a_cycle_is_not_in_it(self):
        got = found(w(1, blocked_by=[J(2)]), w(2, blocked_by=[J(1)]), w(3, blocked_by=[J(1)]))
        self.assertEqual(got["cycles"], [[J(1), J(2)]])
        self.assertNotIn(J(3), got["in_cycle"])

    def test_an_item_that_names_itself_is_reported_as_itself_not_as_a_cycle(self):
        got = found(w(1, blocked_by=[J(1)]))
        self.assertEqual((got["cycles"], got["problems"]["self"]), ([], [J(1)]))

    def test_a_cycle_among_finished_items_is_still_reported(self):
        got = found(w(1, "done", blocked_by=[J(2)]), w(2, "done", blocked_by=[J(1)]))
        self.assertEqual(got["cycles"], [[J(1), J(2)]])

    def test_a_long_cycle_is_found(self):
        got = found(*[w(n, blocked_by=[J(n % 60 + 1)]) for n in range(1, 61)])
        self.assertEqual(len(got["cycles"][0]), 60)

    def test_the_two_handed_in_cycles(self):
        got = depmap.analyse(HANDED_IN)
        self.assertEqual(got["cycles"], [["decision:E-203", "jira:52014", "jira:52015"], ["jira:52010", "jira:52011"]])


class Missing(unittest.TestCase):
    def test_a_missing_target_is_kept_and_named_with_who_names_it(self):
        got = found(w(1, blocked_by=[J(9)]), w(2, blocked_by=[J(9)]))
        self.assertEqual(got["problems"]["missing"], [(J(9), [J(1), J(2)])])
        self.assertEqual(got["waits_on"][J(1)], [J(9)])
        self.assertEqual(got["waited_by"][J(9)], [J(1), J(2)])

    def test_a_missing_decision_is_reported_the_same_way(self):
        got = found(w(1, needs_decision=["decision:E-9"]))
        self.assertEqual(got["problems"]["missing"], [("decision:E-9", [J(1)])])

    def test_a_missing_item_named_by_blocks(self):
        got = found(w(1, blocks=[J(9)]))
        self.assertEqual(got["problems"]["missing"], [(J(9), [])])
        self.assertEqual(got["waits_on"][J(9)], [J(1)])

    def test_a_missing_target_blocks_and_can_be_ranked(self):
        got = found(w(1, blocked_by=[J(9)]), w(2, blocked_by=[J(1)]))
        self.assertEqual(got["blocked"][J(9)], [J(1), J(2)])
        self.assertEqual(got["top"][0], J(9))

    def test_a_link_that_is_not_an_identity_is_reported_and_not_guessed(self):
        got = found(w(1, blocked_by=["2", 2, None, "jira 2", "Jira:2"]), w(2))
        self.assertEqual(got["links"], {})
        self.assertEqual([value for _, _, value, _ in got["problems"]["unreadable"]], ['"2"', '"Jira:2"', '"jira 2"', "2", "null"])

    def test_a_field_that_is_not_a_list_is_reported(self):
        got = found(w(1, blocked_by=J(2)), w(2))
        self.assertEqual(got["links"], {})
        self.assertEqual(got["problems"]["unreadable"][0][:3], (J(1), "blocked_by", '"jira:2"'))

    def test_the_written_index_names_both_missing_items(self):
        text = depmap.render(depmap.analyse(HANDED_IN))
        self.assertIn("**NOT FOUND:** `decision:E-209` has no record. Named by: `jira:52013`", text)
        self.assertIn("**NOT FOUND:** `jira:52999` has no record. Named by: `trello:6a1f000000000000000d0002`", text)
        self.assertIn("### `jira:52999` (no record)\n\n**NOT FOUND: nothing in the data has this identity.**", text)


class Decisions(unittest.TestCase):
    def test_a_decision_is_a_node_like_a_work_item(self):
        got = found(w(1, needs_decision=["decision:E-1"]), d(1, "proposal"))
        self.assertEqual(got["waits_on"][J(1)], ["decision:E-1"])
        self.assertEqual(got["waited_by"]["decision:E-1"], [J(1)])
        self.assertEqual(got["blocked"]["decision:E-1"], [J(1)])

    def test_blocked_by_may_name_a_decision_and_gives_the_same_link(self):
        a = found(w(1, needs_decision=["decision:E-1"]), d(1, "question"))
        b = found(w(1, blocked_by=["decision:E-1"]), d(1, "question"))
        self.assertEqual(list(a["links"]), list(b["links"]))
        self.assertEqual(a["blocked"], b["blocked"])

    def test_a_decided_decision_holds_nothing_up(self):
        got = found(w(1, needs_decision=["decision:E-1"]), d(1, "decided"))
        self.assertNotIn("decision:E-1", got["blocked"])
        self.assertEqual(got["problems"]["undecided"], [])

    def test_a_proposal_and_a_question_are_not_decided(self):
        got = found(w(1, needs_decision=["decision:E-1", "decision:E-2"]), d(1, "proposal"), d(2, "question"))
        self.assertEqual(got["problems"]["undecided"], [(J(1), "decision:E-1"), (J(1), "decision:E-2")])

    def test_a_superseded_decision_will_never_be_made(self):
        got = found(w(1, needs_decision=["decision:E-1"]), d(1, "superseded", superseded_by="decision:E-2"), d(2))
        self.assertEqual(got["problems"]["gone"], [(J(1), "decision:E-1")])

    def test_a_decision_can_wait_on_work(self):
        got = found(d(1, "question", blocked_by=[J(1)]), w(1))
        self.assertEqual(got["blocked"][J(1)], ["decision:E-1"])

    def test_needs_decision_naming_a_work_item_is_reported_and_kept(self):
        got = found(w(1, needs_decision=[J(2)]), w(2))
        self.assertEqual(got["problems"]["wrong_kind"], [(J(1), J(2))])
        self.assertEqual(got["waits_on"][J(1)], [J(2)])


class Blocking(unittest.TestCase):
    def test_everything_down_the_chain_is_counted_and_the_direct_count_is_beside_it(self):
        got = found(w(1), w(2, blocked_by=[J(1)]), w(3, blocked_by=[J(2)]), w(4, blocked_by=[J(2)]))
        self.assertEqual(got["blocked"][J(1)], [J(2), J(3), J(4)])
        self.assertEqual(got["direct"][J(1)], [J(2)])

    def test_an_item_reached_two_ways_is_counted_once(self):
        got = found(w(1), w(2, blocked_by=[J(1)]), w(3, blocked_by=[J(1)]), w(4, blocked_by=[J(2), J(3)]))
        self.assertEqual(got["blocked"][J(1)], [J(2), J(3), J(4)])

    def test_a_done_item_blocks_nothing(self):
        got = found(w(1, "done"), w(2, blocked_by=[J(1)]))
        self.assertNotIn(J(1), got["blocked"])
        self.assertEqual(got["top"], [])

    def test_a_done_item_in_the_middle_ends_the_chain(self):
        got = found(w(1), w(2, "done", blocked_by=[J(1)]), w(3, blocked_by=[J(2)]))
        self.assertEqual(got["blocked"][J(1)], [])

    def test_a_dropped_waiter_is_not_counted(self):
        got = found(w(1), w(2, "dropped", blocked_by=[J(1)]))
        self.assertEqual(got["blocked"][J(1)], [])

    def test_in_a_cycle_each_item_blocks_the_others_and_never_itself(self):
        got = found(w(1, blocked_by=[J(2)]), w(2, blocked_by=[J(1)]), w(3, blocked_by=[J(1)]))
        self.assertEqual(got["blocked"][J(1)], [J(2), J(3)])
        self.assertEqual(got["blocked"][J(2)], [J(1), J(3)])

    def test_only_five_are_listed_and_the_ones_level_with_fifth_are_named(self):
        records = [w(n) for n in range(1, 8)] + [w(10 + n, blocked_by=[J(n)]) for n in range(1, 8)]
        got = found(*records)
        self.assertEqual(got["top"], [J(1), J(2), J(3), J(4), J(5)])
        self.assertEqual(got["level"], [J(6), J(7)])

    def test_equal_totals_go_by_direct_count_then_identity(self):
        got = found(w(1), w(2, blocked_by=[J(1)]), w(3, blocked_by=[J(2)]), w(5), w(6, blocked_by=[J(5)]), w(7, blocked_by=[J(5)]))
        self.assertEqual(got["top"], [J(5), J(1), J(2)])

    def test_the_handed_in_top_five_and_their_counts(self):
        got = depmap.analyse(HANDED_IN)
        self.assertEqual([(n, len(got["blocked"][n]), len(got["direct"][n])) for n in got["top"]],
                         [("jira:52001", 8, 2), ("jira:52002", 5, 2), ("decision:E-209", 3, 2), ("jira:52003", 3, 1), ("jira:52010", 2, 2)])
        self.assertEqual(len(got["level"]), 6)

    def test_the_count_for_the_first_place_checked_by_another_method(self):
        got = depmap.analyse(HANDED_IN)
        reach, grew = {"jira:52001"}, True
        while grew:
            grew = False
            for (waiter, target) in got["links"]:
                if target in reach and waiter not in reach and got["state"][waiter] in ("waiting", "undecided"):
                    reach.add(waiter)
                    grew = True
        self.assertEqual(sorted(reach - {"jira:52001"}), got["blocked"]["jira:52001"])


class Chain(unittest.TestCase):
    def test_the_longest_chain_from_the_waiter_down(self):
        got = found(w(1), w(2, blocked_by=[J(1)]), w(3, blocked_by=[J(2)]), w(4, blocked_by=[J(1)]))
        self.assertEqual(got["longest"], [J(3), J(2), J(1)])

    def test_the_longer_of_two_branches_is_taken(self):
        got = found(w(1, blocked_by=[J(2), J(4)]), w(2, blocked_by=[J(3)]), w(3), w(4))
        self.assertEqual(got["longest"], [J(1), J(2), J(3)])

    def test_a_done_item_ends_a_chain(self):
        got = found(w(1, "done"), w(2, blocked_by=[J(1)]), w(3, blocked_by=[J(2)]))
        self.assertEqual(got["longest"], [J(3), J(2)])

    def test_a_cycle_is_left_out_and_does_not_hang(self):
        got = found(w(1, blocked_by=[J(2)]), w(2, blocked_by=[J(1)]), w(3, blocked_by=[J(1)]), w(4), w(5, blocked_by=[J(4)]))
        self.assertEqual(got["longest"], [J(5), J(4)])

    def test_the_handed_in_chain_has_six_items_across_three_systems(self):
        got = depmap.analyse(HANDED_IN)
        self.assertEqual(got["longest"], ["trello:6a1f000000000000000d0001", "github:I_kwFIXdep0001", "jira:52004", "jira:52003", "jira:52002", "jira:52001"])


class Slip(unittest.TestCase):
    def records(self):
        return (w(1, planned_start="2026-12-01", planned_finish="2026-12-03"),
                w(2, blocked_by=[J(1)], planned_start="2026-12-04", planned_finish="2026-12-05"),
                w(3, blocked_by=[J(2)], planned_start="2026-12-10", planned_finish="2026-12-11"))

    def test_a_dependent_with_no_slack_moves_by_the_whole_slip(self):
        self.assertEqual(depmap.slip(found(*self.records()), J(1), 2)[0], (J(2), "2026-12-04", "2026-12-06", 2))

    def test_slack_absorbs_a_slip(self):
        self.assertEqual(depmap.slip(found(*self.records()), J(1), 2)[1], (J(3), "2026-12-10", "2026-12-10", 0))

    def test_a_slip_larger_than_the_slack_passes_on_what_is_left(self):
        self.assertEqual(depmap.slip(found(*self.records()), J(1), 7)[1], (J(3), "2026-12-10", "2026-12-13", 3))

    def test_no_slip_moves_nothing(self):
        self.assertEqual([row[3] for row in depmap.slip(found(*self.records()), J(1), 0)], [0, 0])

    def test_an_item_that_waits_on_a_cycle_cannot_be_dated(self):
        got = found(w(1, blocked_by=[J(2)], planned_start="2026-12-01", planned_finish="2026-12-02"),
                    w(2, blocked_by=[J(1)], planned_start="2026-12-01", planned_finish="2026-12-02"),
                    w(3, blocked_by=[J(1)], planned_start="2026-12-05", planned_finish="2026-12-06"))
        self.assertEqual(depmap.slip(got, J(1), 3), [(J(2), None, None, None), (J(3), None, None, None)])

    def test_an_item_nothing_waits_on_moves_nothing(self):
        self.assertEqual(depmap.slip(found(*self.records()), J(3), 5), [])

    def test_too_early_is_reported_when_the_plan_starts_before_the_prerequisite_ends(self):
        got = found(w(1, planned_start="2026-12-07", planned_finish="2026-12-09"), w(2, blocked_by=[J(1)], planned_start="2026-12-09", planned_finish="2026-12-10"),
                    w(3, blocked_by=[J(1)], planned_start="2026-12-10", planned_finish="2026-12-11"))
        self.assertEqual(got["problems"]["too_early"], [(J(2), J(1), "2026-12-09", "2026-12-09")])

    def test_the_handed_in_slip_of_five_days(self):
        rows = {n: pushed for n, _, _, pushed in depmap.slip(depmap.analyse(HANDED_IN), "jira:52001", 5)}
        self.assertEqual(rows, {"github:I_kwFIXdep0001": 0, "jira:52002": 3, "jira:52003": 1, "jira:52004": 0, "jira:52005": 3,
                                "jira:52006": 3, "jira:52025": 1, "trello:6a1f000000000000000d0001": 0})


class OtherProblems(unittest.TestCase):
    def test_waiting_on_a_dropped_item(self):
        self.assertEqual(found(w(1, blocked_by=[J(2)]), w(2, "dropped"))["problems"]["gone"], [(J(1), J(2))])

    def test_finished_before_what_it_waited_on(self):
        self.assertEqual(found(w(1, "done", blocked_by=[J(2)]), w(2))["problems"]["finished_early"], [(J(1), J(2))])

    def test_a_satisfied_link_is_no_problem(self):
        got = found(w(1, blocked_by=[J(2)]), w(2, "done"))
        self.assertEqual(depmap.problem_count(got), 0)

    def test_the_handed_in_data_has_sixteen_problems(self):
        got = depmap.analyse(HANDED_IN)
        self.assertEqual({k: len(v) for k, v in got["problems"].items()},
                         {"cycles": 2, "self": 1, "missing": 2, "unreadable": 1, "gone": 2, "undecided": 2, "wrong_kind": 1, "finished_early": 1, "too_early": 4})


class SameEveryRun(unittest.TestCase):
    def test_two_runs_give_the_same_text(self):
        self.assertEqual(depmap.render(depmap.analyse(HANDED_IN)), depmap.render(depmap.analyse(HANDED_IN)))

    def test_the_order_of_the_records_and_of_each_list_does_not_matter(self):
        expected = depmap.render(depmap.analyse(HANDED_IN))
        for seed in range(5):
            rng = random.Random(seed)
            records = [dict(r) for r in make_data.RECORDS]
            rng.shuffle(records)
            for r in records:
                for field in depmap.LINK_FIELDS:
                    if isinstance(r.get(field), list):
                        r[field] = rng.sample(r[field], len(r[field]))
            self.assertEqual(depmap.render(depmap.analyse(depmap.read_records(as_text(records)))), expected, seed)

    def test_separate_python_processes_with_different_hash_seeds_write_the_same_index(self):
        import subprocess
        code = ("import sys; sys.path.insert(0, %r); import depmap, make_data; "
                "sys.stdout.write(depmap.render(depmap.analyse(depmap.read_records(make_data.text()))))" % os.path.dirname(HERE))
        outputs = set()
        for seed in ("0", "1", "2", "3", "77"):
            done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=dict(os.environ, PYTHONHASHSEED=seed))
            self.assertEqual(done.returncode, 0, done.stderr)
            outputs.add(done.stdout)
        self.assertEqual(len(outputs), 1)
        self.assertEqual(outputs.pop(), depmap.render(depmap.analyse(HANDED_IN)))

    def test_the_index_holds_no_date_or_time_of_the_run(self):
        import datetime
        text = depmap.render(depmap.analyse(HANDED_IN))
        today = datetime.date.today()
        self.assertNotIn(today.isoformat(), text)
        self.assertNotIn("Generated on", text)

    def test_the_handed_in_files_are_what_the_code_writes(self):
        self.assertEqual(depmap.read(os.path.join(depmap.FOLDER, "data.md")), make_data.text())
        self.assertEqual(depmap.read(os.path.join(depmap.FOLDER, "index.md")), depmap.render(depmap.analyse(HANDED_IN)))


class Command(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.mkdtemp(prefix="gtq-depmap-")
        self.addCleanup(shutil.rmtree, self.scratch, True)
        self.data = os.path.join(self.scratch, "data.md")

    def write(self, text):
        with open(self.data, "w", encoding="utf-8") as f:
            f.write(text)

    def run_main(self, *argv):
        said = []
        return depmap.main(list(argv), say=said.append), said

    def test_build_reports_by_name_and_ends_with_exit_code_1(self):
        self.write(make_data.text())
        code, said = self.run_main("build", "--data", self.data)
        self.assertEqual(code, 1)
        self.assertIn("CYCLE: jira:52010 waits on jira:52011 waits on jira:52010", said)
        self.assertIn("NOT FOUND: decision:E-209, named by jira:52013, jira:52027", said)
        self.assertIn("NOT FOUND: jira:52999, named by trello:6a1f000000000000000d0002", said)
        self.assertEqual(said[-1], "Wrote index.md. PROBLEMS REPORTED: 16.")
        self.assertTrue(os.path.exists(os.path.join(self.scratch, "index.md")))

    def test_clean_data_ends_with_exit_code_0(self):
        self.write(as_text([w(1, blocked_by=[J(2)]), w(2)]))
        code, said = self.run_main("build", "--data", self.data)
        self.assertEqual((code, said[-1]), (0, "Wrote index.md. Nothing to report."))

    def test_build_leaves_the_data_file_alone(self):
        self.write(make_data.text())
        self.run_main("build", "--data", self.data)
        self.assertEqual(depmap.read(self.data), make_data.text())

    def test_build_refuses_to_write_over_the_data(self):
        self.write(make_data.text())
        code, said = self.run_main("build", "--data", self.data, "--out", self.data)
        self.assertEqual(code, 2)
        self.assertEqual(depmap.read(self.data), make_data.text())

    def test_no_data_file(self):
        self.assertEqual(self.run_main("build", "--data", self.data)[0], 2)

    def test_no_records(self):
        self.write("# Nothing here\n")
        code, said = self.run_main("build", "--data", self.data)
        self.assertEqual((code, said[-1]), (2, "NOT BUILT. No records could be read."))

    def test_two_records_with_one_identity_are_refused(self):
        self.write(as_text([w(1), w(1)]))
        code, said = self.run_main("build", "--data", self.data)
        self.assertEqual(code, 2)
        self.assertIn("Two records have the identity jira:1", said[-1])

    def test_a_record_that_is_not_json_is_refused_by_name(self):
        self.write("### jira:1\n\n```json\n{not json}\n```\n")
        code, said = self.run_main("build", "--data", self.data)
        self.assertEqual(code, 2)
        self.assertIn("jira:1", said[-1])

    def test_a_heading_that_differs_from_the_record_is_refused(self):
        self.write(as_text([w(1)]).replace("### jira:1", "### jira:2"))
        self.assertEqual(self.run_main("build", "--data", self.data)[0], 2)

    def test_slip_prints_what_moves(self):
        self.write(make_data.text())
        code, said = self.run_main("slip", "jira:52001", "5", "--data", self.data)
        self.assertEqual(code, 0)
        self.assertTrue(any("jira:52002" in line and "pushed 3 days" in line for line in said))

    def test_slip_needs_a_record_and_a_number(self):
        self.write(make_data.text())
        self.assertEqual(self.run_main("slip", "jira:1", "5", "--data", self.data)[0], 2)
        self.assertEqual(self.run_main("slip", "jira:52001", "soon", "--data", self.data)[0], 2)

    def test_no_command_explains_itself(self):
        self.assertEqual(self.run_main()[0], 2)


if __name__ == "__main__":
    unittest.main()
