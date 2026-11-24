"""Tests for the context-cross-system-conflicts skill. They use the made-up records in participant/context/conflicts and records built here. Nothing is written there."""
import copy
import hashlib
import json
import os
import random
import re
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import conflicts      # noqa: E402

FOLDER = conflicts.FOLDER


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def rec(system, status, updated, assignees=1, due=None, title="The same title", number=1):
    return {"identity": "%s:x%d" % (system, number), "system": system, "title": title, "status": status, "assignee_count": assignees, "due_at": due, "updated_at": updated, "as_sent": {}}


class Base(unittest.TestCase):
    def setUp(self):
        self.text = read(os.path.join(FOLDER, "records.md"))
        self.records, self.links, self.depends = conflicts.read_records(self.text)
        self.previous = json.loads(read(os.path.join(FOLDER, "previous-run.json")))

    def found(self, records=None, links=None, previous=False):
        return conflicts.analyse(self.records if records is None else records, self.links if links is None else links, self.depends, self.previous if previous else None)

    def classes(self, work, field="status"):
        return [pair["class"] for one in self.found()["works"] if one["work"] == work for pair in one["pairs"] if pair["field"] == field]


class ThePair(unittest.TestCase):
    """Criterion 3, and the lag rule itself."""

    def kind(self, first, second, field="status"):
        return conflicts.compare(first, second, field)[0]

    def test_equal_values_agree_whatever_the_times(self):
        self.assertEqual(self.kind(rec("jira", "done", None), rec("trello", "done", "2026-11-01T00:00:00Z")), "agree")

    def test_later_and_further_along_within_the_allowance_is_lag(self):
        self.assertEqual(self.kind(rec("jira", "done", "2026-11-18T10:00:00Z"), rec("trello", "in_progress", "2026-11-18T08:00:00Z")), "lag")
        self.assertEqual(self.kind(rec("trello", "in_progress", "2026-11-18T08:00:00Z"), rec("jira", "done", "2026-11-18T10:00:00Z")), "lag")

    def test_the_allowance_is_24_hours_between_the_two_records_and_the_edge_is_inside(self):
        base = rec("jira", "in_progress", "2026-11-19T09:00:00Z")
        self.assertEqual(self.kind(base, rec("trello", "done", "2026-11-20T09:00:00Z")), "lag")
        self.assertEqual(self.kind(base, rec("trello", "done", "2026-11-20T09:00:01Z")), "conflict")
        self.assertEqual(self.kind(base, rec("trello", "done", "2026-11-19T09:00:01Z")), "lag")
        self.assertEqual(conflicts.LAG_HOURS, 24)

    def test_later_and_less_far_along_is_a_conflict_however_close(self):
        kind, why, find = conflicts.compare(rec("jira", "done", "2026-11-17T09:00:00Z"), rec("trello", "in_progress", "2026-11-17T09:05:00Z"), "status")
        self.assertEqual(kind, "conflict")
        self.assertIn("LESS far along", why)
        self.assertIn("who changed trello", find)

    def test_the_same_moment_is_a_conflict(self):
        self.assertEqual(self.kind(rec("trello", "done", "2026-11-15T12:00:00Z"), rec("jira", "open", "2026-11-15T12:00:00Z")), "conflict")
        self.assertEqual(self.kind(rec("trello", "done", "2026-11-15T12:00:00Z"), rec("jira", "open", "2026-11-15T07:00:00-05:00")), "conflict")

    def test_done_against_dropped_is_always_a_conflict(self):
        for gap in ("2026-11-16T10:30:00Z", "2026-11-16T10:00:01Z", "2026-12-16T10:00:00Z"):
            self.assertEqual(self.kind(rec("jira", "done", "2026-11-16T10:00:00Z"), rec("github", "dropped", gap)), "conflict")

    def test_no_update_time_on_either_side_is_a_conflict_and_says_what_is_missing(self):
        kind, why, find = conflicts.compare(rec("jira", "in_progress", None), rec("trello", "done", "2026-11-14T16:00:00Z"), "status")
        self.assertEqual((kind, find), ("conflict", "when jira's record last changed"))
        self.assertEqual(self.kind(rec("jira", "in_progress", "not a time"), rec("trello", "done", "2026-11-14T16:00:00Z")), "conflict")
        self.assertEqual(self.kind(rec("jira", "in_progress", "2026-11-14T16:00:00"), rec("trello", "done", "2026-11-14T16:00:00Z")), "conflict")

    def test_github_saying_open_where_another_says_in_progress_is_not_comparable(self):
        for other in ("jira", "trello"):
            kind, why, _ = conflicts.compare(rec(other, "in_progress", "2026-11-12T11:00:00Z"), rec("github", "open", "2026-10-01T09:00:00Z"), "status")
            self.assertEqual(kind, "not comparable")
            self.assertIn("nothing between", why)

    def test_github_open_against_done_is_comparable_and_judged_by_the_rule(self):
        self.assertEqual(self.kind(rec("jira", "done", "2026-11-19T16:00:00Z"), rec("github", "open", "2026-11-19T10:00:00Z")), "lag")
        self.assertEqual(self.kind(rec("jira", "done", "2026-11-10T09:00:00Z"), rec("github", "open", "2026-11-04T10:00:00Z")), "conflict")
        self.assertEqual(self.kind(rec("jira", "in_progress", "2026-11-10T09:00:00Z"), rec("github", "done", "2026-11-10T10:00:00Z")), "lag")

    def test_jira_and_trello_can_both_say_in_progress_so_open_against_it_is_compared(self):
        self.assertEqual(self.kind(rec("jira", "in_progress", "2026-11-10T09:00:00Z"), rec("trello", "open", "2026-11-01T10:00:00Z")), "conflict")

    def test_a_due_date_on_github_is_not_comparable_and_between_the_others_is_compared_by_the_day(self):
        j = rec("jira", "open", "2026-11-10T09:00:00Z", due="2026-12-01T00:00:00Z")
        self.assertEqual(self.kind(j, rec("github", "open", "2026-11-09T09:00:00Z"), "due"), "not comparable")
        self.assertEqual(self.kind(j, rec("trello", "open", "2026-11-13T09:00:00Z", due="2026-12-01T17:00:00Z"), "due"), "agree")
        self.assertEqual(self.kind(j, rec("trello", "open", "2026-11-13T09:00:00Z", due="2026-12-04T17:00:00Z"), "due"), "conflict")
        self.assertEqual(self.kind(j, rec("trello", "open", "2026-11-10T10:00:00Z", due="2026-12-04T17:00:00Z"), "due"), "lag")
        self.assertEqual(self.kind(j, rec("trello", "open", "2026-11-10T10:00:00Z"), "due"), "conflict")

    def test_assigned_compares_whether_anyone_is_and_not_how_many(self):
        a = rec("jira", "open", "2026-11-20T10:00:00Z", assignees=1)
        self.assertEqual(self.kind(a, rec("trello", "open", "2026-11-01T08:30:00Z", assignees=3), "assigned"), "agree")
        self.assertEqual(self.kind(a, rec("trello", "open", "2026-11-20T08:30:00Z", assignees=0), "assigned"), "lag")
        self.assertEqual(self.kind(a, rec("trello", "open", "2026-11-10T08:30:00Z", assignees=0), "assigned"), "conflict")

    def test_a_title_that_differs_is_different_and_never_a_conflict(self):
        for updated in ("2026-11-01T00:00:00Z", None):
            self.assertEqual(self.kind(rec("jira", "open", updated, title="A"), rec("trello", "open", "2026-12-01T00:00:00Z", title="B"), "title"), "different")

    def test_the_answer_does_not_depend_on_which_record_comes_first(self):
        samples = [rec(s, st, u, number=n) for n, (s, st, u) in enumerate([("jira", "done", "2026-11-18T10:00:00Z"), ("trello", "in_progress", "2026-11-18T08:00:00Z"), ("github", "open", "2026-11-10T00:00:00Z"),
                                                                          ("github", "dropped", "2026-11-18T10:30:00Z"), ("trello", "open", None), ("jira", "in_progress", "2026-11-17T10:00:00Z")])]
        for a in samples:
            for b in samples:
                if a["system"] != b["system"]:
                    self.assertEqual(self.kind(a, b), self.kind(b, a), "%s %s" % (a["identity"], b["identity"]))


class TheReport(Base):
    """Criteria 1, 2, 5 and 7, on the made-up records."""

    def test_each_case_in_the_records_gets_the_answer_it_was_built_to_get(self):
        self.assertEqual(self.classes("W-01"), ["agree"] * 3)
        self.assertEqual(self.classes("W-02"), ["conflict", "conflict", "not comparable"])
        self.assertEqual(self.classes("W-03"), ["lag", "agree", "lag"])
        for work, wanted in (("W-04", "conflict"), ("W-05", "not comparable"), ("W-06", "conflict"), ("W-07", "conflict"), ("W-08", "conflict"), ("W-09", "lag"), ("W-10", "lag"), ("W-11", "conflict")):
            self.assertEqual(self.classes(work), [wanted], work)
        self.assertEqual((self.classes("W-12", "due"), self.classes("W-13", "assigned")), (["conflict", "not comparable", "not comparable"], ["lag"]))

    def test_records_are_compared_by_identity_through_the_links_and_only_through_them(self):
        found = self.found()
        self.assertEqual(len(found["works"]), 13)
        for work in found["works"]:
            for pair in work["pairs"]:
                self.assertIn(pair["a"], work["members"])
                self.assertIn(pair["b"], work["members"])
                self.assertNotEqual(pair["a"].split(":")[0], pair["b"].split(":")[0])
        self.assertEqual(sum(len(work["pairs"]) for work in found["works"]), (4 * 3 + 9) * 4)        # four pieces of work in three systems, nine in two, four fields each

    def test_every_conflict_shows_both_values_both_systems_and_both_times(self):
        text = conflicts.render(self.records, self.found(previous=True), self.previous["run"])
        blocks = text.split("## Differences judged to be lag")[0].split("\n### ")[1:]
        self.assertEqual(len(blocks), 8)
        for block in blocks:
            rows = [line for line in block.split("\n") if line.startswith("| ") and not line.startswith("| System") and not line.startswith("|---")]
            self.assertEqual(len(rows), 2, block[:60])
            self.assertEqual(len(set(row.split(" | ")[0] for row in rows)), 2)
            for row in rows:
                self.assertRegex(row, r"\| `\"[^`]+\"` \| `\".*\"` \| (\d{4}-\d\d-\d\dT[\d:]+Z|\*\*not stated\*\*) \|$")
            for phrase in ("**Why it is a conflict:**", "**To settle it, a person would need to find out:**", "**Seen before:**"):
                self.assertIn(phrase, block)

    def test_a_record_with_no_counterpart_is_unlinked_and_is_not_a_conflict(self):
        found = self.found()
        self.assertIn("jira:41050", found["unlinked"])
        self.assertEqual(len(found["unlinked"]), 7)
        self.assertFalse([one for one in found["conflicts"] if one["a"] in found["unlinked"] or one["b"] in found["unlinked"]])
        text = conflicts.render(self.records, found, None)
        self.assertIn("| `jira:41050` | jira |", text.split("## Unlinked records")[1])
        self.assertNotIn("jira:41050", text.split("## Unlinked records")[0])

    def test_the_same_title_never_links_two_records_and_is_only_a_hint(self):
        found = self.found()
        self.assertEqual(found["same_title"], [("Fix export", ["github:I_kwFIX0450", [one for one in found["unlinked"] if one.startswith("trello:") and self.records[one]["title"] == "Fix export"][0]])])
        self.assertFalse([work for work in found["works"] if "github:I_kwFIX0450" in work["members"]])

    def test_a_link_that_cannot_be_used_is_reported_and_its_records_are_left_unlinked(self):
        found = self.found()
        problems = dict(found["problems"])
        self.assertIn("there is no such record here", problems["W-14"])
        self.assertIn("another link names too (W-16)", problems["W-15"])
        self.assertIn("another link names too (W-15)", problems["W-16"])
        for identity in ("jira:41014", "jira:41015", "jira:41016"):
            self.assertIn(identity, found["unlinked"])

    def test_a_link_of_two_records_from_one_system_or_of_one_record_is_not_compared(self):
        links = self.links + [{"work": "W-90", "members": ["jira:41050", "jira:41014"], "stated": "x"}, {"work": "W-91", "members": ["github:I_kwFIX0450"], "stated": "x"}]
        problems = dict(self.found(links=[one for one in links if one["work"] != "W-14"])["problems"])
        self.assertIn("same system", problems["W-90"])
        self.assertIn("one record only", problems["W-91"])

    def test_every_comparison_is_listed_with_its_reason(self):
        found = self.found()
        text = conflicts.render(self.records, found, None)
        table = text.split("## Every comparison made")[1].split("## The links used")[0]
        self.assertEqual(len(re.findall(r"^\| W-\d+ \|", table, re.M)), sum(len(work["pairs"]) for work in found["works"]))
        self.assertEqual(table.count("| **conflict** |"), 8)
        for work in found["works"]:
            for pair in work["pairs"]:
                self.assertGreater(len(pair["why"]), 10)

    def test_the_handed_in_report_and_state_are_what_the_code_writes(self):
        self.assertEqual(read(os.path.join(FOLDER, "report.md")), conflicts.render(self.records, self.found(previous=True), self.previous["run"]))
        earlier = conflicts.read_records(read(os.path.join(FOLDER, "earlier-records.md")))
        keys = [list(one["key"]) for one in conflicts.analyse(*earlier)["conflicts"]]
        self.assertEqual(self.previous, {"run": "2026-11-16", "conflicts": keys})


class NoWinner(Base):
    """Criterion 4."""

    def test_the_run_changes_no_file_but_the_report_and_cannot_write_over_the_records(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        for name in ("records.md", "previous-run.json"):
            shutil.copy(os.path.join(FOLDER, name), tmp)
        digest = lambda: {name: hashlib.sha256(read(os.path.join(tmp, name)).encode()).hexdigest() for name in sorted(os.listdir(tmp)) if name != "report.md"}
        before = digest()
        run = lambda *more: conflicts.main(["report", "--records", os.path.join(tmp, "records.md"), "--previous", os.path.join(tmp, "previous-run.json")] + list(more), say=lambda line: None)
        self.assertEqual(run("--out", os.path.join(tmp, "report.md")), 0)
        self.assertEqual(digest(), before)
        self.assertEqual(run("--out", os.path.join(tmp, "records.md")), 1)
        self.assertEqual(digest(), before)

    def test_analysing_does_not_alter_the_records_in_memory_either(self):
        before = copy.deepcopy(self.records)
        self.found(previous=True)
        self.assertEqual(self.records, before)

    def test_the_report_names_no_winner_and_gives_no_single_resolved_state(self):
        text = conflicts.render(self.records, self.found(previous=True), self.previous["run"])
        body = text.split("## Summary")[1]
        for word in ("winner", "correct value", "should be", "is right", "is wrong", "trust ", "stale", "authoritative", "resolved", "true state", "probably"):
            self.assertNotIn(word, body.lower().replace("which side is right", "").replace("it does not say", ""), word)
        found = self.found()
        for work in found["works"]:
            self.assertEqual(sorted(work), ["members", "pairs", "stated", "work"])
        for one in found["conflicts"]:
            self.assertFalse(set(one) & {"winner", "resolved", "value", "true"})

    def test_a_lag_still_shows_both_values_and_both_times(self):
        text = conflicts.render(self.records, self.found(), None).split("## Differences judged to be lag")[1].split("## Differences that are not comparable")[0]
        self.assertEqual(len(re.findall(r"^\| ", text, re.M)), 1 + 5 * 2)
        self.assertIn('| W-09 | status | jira | `"done"` |', text)
        self.assertIn('|  |  | github | `"open"` | `"state open"` | 2026-11-19T10:00:00Z |', text)

    def test_the_skill_has_no_code_that_reaches_a_network_or_runs_a_command(self):
        code = read(os.path.join(os.path.dirname(HERE), "conflicts.py"))
        self.assertEqual(set(re.findall(r"^(?:import|from) ([A-Za-z_.]+)", code, re.M)), {"argparse", "datetime", "json", "os", "re", "sys"})
        self.assertEqual(len(re.findall(r"open\(", code)), 2)


class SameInputSameReport(Base):
    """Criterion 6."""

    def report(self, records=None, links=None):
        return conflicts.render(self.records if records is None else records, self.found(records, links, previous=True), self.previous["run"])

    def test_two_runs_give_the_same_report(self):
        self.assertEqual(self.report(), self.report())

    def test_the_order_of_the_records_and_of_the_links_changes_nothing(self):
        wanted = self.report()
        for seed in range(5):
            order = list(self.records)
            random.Random(seed).shuffle(order)
            links = list(self.links)
            random.Random(seed + 100).shuffle(links)
            links = [dict(link, members=list(reversed(link["members"]))) for link in links]
            self.assertEqual(self.report({identity: self.records[identity] for identity in order}, links), wanted, seed)

    def test_no_clock_is_read(self):
        code = read(os.path.join(os.path.dirname(HERE), "conflicts.py"))
        for call in (".now(", ".today(", "utcnow", "getmtime", "import time"):
            self.assertNotIn(call, code)
        self.assertIsNone(re.search(r"\btime\.time\(", code))

    def test_a_changed_input_changes_the_report(self):
        records = copy.deepcopy(self.records)
        records["jira:41001"]["status"] = "open"
        self.assertNotEqual(self.report(records), self.report())


class Stretch(Base):
    def test_conflicts_are_ordered_by_how_much_other_work_depends_on_them(self):
        found = self.found()
        counts = [len(one["affects"]) for one in found["conflicts"]]
        self.assertEqual(counts, sorted(counts, reverse=True))
        self.assertEqual(found["affected"]["W-02"], ["W-04", "W-06", "W-09"])
        self.assertEqual((found["conflicts"][0]["work"], found["affected"]["W-06"], found["affected"]["W-08"]), ("W-02", ["W-09"], ["W-11"]))

    def test_a_conflict_already_in_the_previous_run_is_marked_and_a_new_one_is_not(self):
        seen = {(one["work"], one["field"]): one["seen_before"] for one in self.found(previous=True)["conflicts"]}
        self.assertEqual(seen[("W-04", "status")], False)
        self.assertEqual(seen[("W-11", "status")], False)
        for key in (("W-02", "status"), ("W-06", "status"), ("W-07", "status"), ("W-08", "status"), ("W-12", "due")):
            self.assertEqual(seen[key], True, key)
        self.assertTrue(all(one["seen_before"] is None for one in self.found()["conflicts"]))

    def test_the_same_pair_in_conflict_with_other_values_is_a_new_conflict(self):
        records = copy.deepcopy(self.records)
        records["jira:41006"]["status"] = "open"
        records["jira:41006"]["updated_at"] = "2026-11-16T10:30:00Z"
        found = conflicts.analyse(records, self.links, self.depends, self.previous)
        self.assertEqual([one["seen_before"] for one in found["conflicts"] if one["work"] == "W-06"], [False])


class Input(Base):
    def test_a_broken_records_file_stops_the_run_and_writes_nothing(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        for change, wanted in ((lambda t: t.replace('"status": "done"', '"status": "finished"', 1), "not one of"), (lambda t: t.replace('"identity": "jira:41001"', '"identity": "jira:41999"'), "gives its identity as"),
                               (lambda t: "# nothing\n", "holds no records"), (lambda t: t.replace('"system": "jira"', '"system": "asana"', 1), "does not belong")):
            with open(os.path.join(tmp, "records.md"), "w", encoding="utf-8") as f:
                f.write(change(self.text))
            said = []
            self.assertEqual(conflicts.main(["report", "--records", os.path.join(tmp, "records.md"), "--out", os.path.join(tmp, "report.md")], say=said.append), 1)
            self.assertIn(wanted, said[-1])
            self.assertFalse(os.path.exists(os.path.join(tmp, "report.md")))


if __name__ == "__main__":
    unittest.main()
