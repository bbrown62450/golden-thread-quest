"""Tests for reconcile.py, against the made-up Jira and the fixture. No network. Every item here is made up."""
import contextlib
import io
import itertools
import json
import os
import random
import re
import shutil
import sys
import tempfile
import unittest
import urllib.parse
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, SKILL)
import fake_jira    # noqa: E402
import reconcile    # noqa: E402

MADE_UP = "-".join(["made", "up", "value", "used", "only", "in", "tests"])      # stands where an API token would be
NOW = fake_jira.NOW
PRIVATE_WORDS = ("Made-up private title", "Example Ltd", "example.invalid", "made-up.person", "Made-up title that is never asked for")


def named(number, key, kind, status, when):
    """What Jira answers for one item, with any status name at all."""
    body = fake_jira.shaped(number, key, kind, "To Do", when)
    body["fields"]["status"]["name"] = status
    return body


def copy_item(number, key, status="To Do", held=None, kind="Story", updated="2026-11-17T08:00:00Z"):
    return {"id": str(number), "copied_at": fake_jira.COPIED, "as_copied": {"key": key, "issuetype": kind, "status": status, "updated": updated}, "as_held": {"issuetype": kind, "status": held or status}}


class Case(unittest.TestCase):
    def setUp(self):
        self.folder = os.path.realpath(tempfile.mkdtemp(prefix="gtq-reconcile-test-"))
        self.out = os.path.join(self.folder, "out")
        os.makedirs(self.out)
        self.copy_path = os.path.join(self.folder, "copy.json")
        self.save_copy(fake_jira.local_copy())

    def tearDown(self):
        shutil.rmtree(self.folder, ignore_errors=True)

    # ---------------------------------------------------------- helpers

    def save_copy(self, copy, path=None):
        with open(path or self.copy_path, "w", encoding="utf-8") as f:
            json.dump(copy, f)

    def main(self, *argv):
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed), contextlib.redirect_stderr(printed):
            try:
                code = reconcile.main(list(argv))
            except SystemExit as stop:
                code = stop.code
        return code, printed.getvalue()

    def report(self, as_of=NOW, extra=(), name="report", faults=None):
        argv = ["report", "--source", "fake", "--copy", self.copy_path, "--out-dir", self.out, "--name", name, "--as-of", as_of] + list(extra)
        if faults is None:
            return self.main(*argv)
        real = fake_jira.FakeJira
        with mock.patch.object(fake_jira, "FakeJira", lambda: real(faults)):
            return self.main(*argv)

    def text(self, ending=".md", name="report"):
        with open(os.path.join(self.out, name + ending), encoding="utf-8") as f:
            return f.read()

    def files(self):
        state = {}
        for name in sorted(os.listdir(self.out)):
            path = os.path.join(self.out, name)
            with open(path, "rb") as f:
                state[name] = (f.read(), os.stat(path).st_mtime_ns, os.stat(path).st_ino)
        return state

    def entries(self, faults=None, copy=None, as_of=NOW):
        """What the tool makes of the fixture: {number: entry}, with the failure of the list if any."""
        conn = reconcile.Connection(fake_jira.FakeJira(faults).get, "jira.example.test")
        entries, failure, self.list_line, self.listed = reconcile.reconcile(copy or fake_jira.local_copy(), conn, as_of)
        self.conn = conn
        return {e["id"]: e for e in entries}, failure, entries

    def sections(self):
        """The report's exception sections: {state: text}."""
        report = self.text()
        body = report[report.index("## 3. "):report.index("## 4. ")]
        out = {}
        for part in body.split("\n### ")[1:]:
            title, _, rest = part.partition("\n")
            out[title.split(":")[0].lower()] = rest
        return out

    def expected(self):
        """The state the FIXTURE says each item should be given. Written beside the made-up Jira, not taken from the tool."""
        want = {row[0]: row[6] for row in fake_jira.ROWS}
        want.update({only[0]: "not yet copied" for only in fake_jira.ONLY_IN_JIRA})
        return want


class EveryItemInExactlyOneState(Case):
    def test_each_item_of_the_fixture_is_given_the_state_the_fixture_says(self):
        got, failure, entries = self.entries()
        self.assertIsNone(failure)
        self.assertEqual({number: e["state"] for number, e in got.items()}, self.expected())
        self.assertEqual(len(entries), 18)

    def test_no_item_is_in_two_states_or_in_none(self):
        _, _, entries = self.entries()
        numbers = [e["id"] for e in entries]
        self.assertEqual(len(numbers), len(set(numbers)))
        self.assertEqual(set(numbers), set(self.expected()))
        self.assertTrue(all(e["state"] in reconcile.STATE_NAMES for e in entries))

    def test_every_combination_of_what_jira_and_the_copy_can_say_gets_the_state_the_order_gives(self):
        """Worked out here from the order of the states, for each combination, and compared with the tool."""
        same = {"key": "DEMO-1", "issuetype": "Story", "status": "To Do", "updated": "2026-11-17T08:00:00Z", "names_checksum": "0" * 16}
        jira_says = {"failed": ("failed", "server error (5xx)"), "gone": ("gone", None), "moved away": ("gone", "moved"), "same": ("item", same),
                     "another status": ("item", dict(same, status="Done", updated="2026-11-19T08:00:00Z")), "another key only": ("item", dict(same, key="DEMO-77")),
                     "another type only": ("item", dict(same, issuetype="Bug")), "a later time only": ("item", dict(same, updated="2026-11-19T08:00:00Z"))}
        locally = {"nothing": {}, "the status": {"status": "In Review"}, "the type": {"issuetype": "Bug"}, "both": {"status": "In Review", "issuetype": "Bug"}}
        seen = set()
        for (what, answer), (which, change) in itertools.product(jira_says.items(), locally.items()):
            item = copy_item(1, "DEMO-1")
            item["as_held"].update(change)
            jira_changed = answer[0] == "item" and what != "same"
            fits = []                       # every state whose own condition holds, whatever else holds
            if answer[0] == "failed":
                fits.append("failed to fetch")
            if answer[0] == "gone":
                fits.append("missing from Jira")
            if jira_changed and change:
                fits.append("conflicted")
            if answer[0] == "item" and change and not jira_changed:
                fits.append("changed locally only")
            if jira_changed:
                fits.append("stale")
            want = next((name for name in reconcile.STATE_NAMES if name in fits), "synchronized")
            got = reconcile.classify(item, answer[0], answer[1], NOW)
            self.assertEqual(got["state"], want, (what, which))
            self.assertEqual(bool(got["also"]), bool(change) and answer[0] != "item" or (jira_changed and bool(change)), (what, which))
            seen.add(want)
        self.assertEqual(seen, set(reconcile.STATE_NAMES) - {"not yet copied"})

    def test_a_thousand_made_up_projects_each_add_up_and_each_item_has_the_state_worked_out_here(self):
        chooser = random.Random(20261120)
        failing = (429, 500, 403, "garbled", "timeout")
        for trial in range(1000):
            count = chooser.randint(0, 12)
            held = {str(100 + n): chooser.choice([None, None, "Done"]) for n in range(count)}
            copy = {"format": reconcile.COPY_FORMAT, "project": "DEMO", "source": "fake", "site_fingerprint": None,
                    "items": [copy_item(int(n), "DEMO-%s" % n, "To Do", held[n]) for n in held]}
            answers = {n: chooser.choice(["same", "changed", 404, 429, 500, 403, "garbled", "timeout"]) for n in held}
            extra = [str(900 + n) for n in range(chooser.randint(0, 4))]

            def get(path, params=None):
                if path == reconcile.SEARCH_PATH:
                    there = sorted([n for n, a in answers.items() if a != 404] + extra, key=int)
                    return 200, {}, {"issues": [{"id": n, "key": "DEMO-%s" % n, "fields": {}} for n in there], "isLast": True}
                number = path.rsplit("/", 1)[1]
                answer = answers[number]
                if answer == "timeout":
                    raise TimeoutError()
                if answer == "garbled":
                    return 200, {}, {"nonsense": True}
                if isinstance(answer, int):
                    return answer, {}, {}
                return 200, {}, fake_jira.shaped(number, "DEMO-%s" % number, "Story", "To Do" if answer == "same" else "Done", "2026-11-17T08:00:00Z" if answer == "same" else "2026-11-19T08:00:00Z")
            want = {n: "not yet copied" for n in extra}
            for n, answer in answers.items():           # the state, worked out here and not by the tool
                want[n] = ("failed to fetch" if answer in failing else "missing from Jira" if answer == 404 else
                           ("conflicted" if held[n] else "stale") if answer == "changed" else ("changed locally only" if held[n] else "synchronized"))
            entries, failure, _, listed = reconcile.reconcile(copy, reconcile.Connection(get, "x"), NOW)
            self.assertEqual({e["id"]: e["state"] for e in entries}, want, trial)
            self.assertEqual(len(entries), len(want), trial)
            counts, total, problems = reconcile.own_check(entries, copy, listed)
            self.assertEqual(problems, [], trial)
            self.assertEqual(total, count + len(extra), trial)
            self.assertEqual(counts, {name: sum(1 for state in want.values() if state == name) for name in reconcile.STATE_NAMES}, trial)

    def test_names_that_differ_only_in_what_cleaning_removes_are_not_called_the_same(self):
        """Two names that clean to one: `QA:Review` and `QA/Review`, and two that differ after the 40th character."""
        long_a, long_b = "A" * 40 + " one", "A" * 40 + " two"
        for was, now in (("QA:Review", "QA/Review"), (long_a, long_b)):
            self.assertEqual(reconcile.clean(was), reconcile.clean(now), "the cleaned names are the same")
            item = copy_item(1, "DEMO-1", reconcile.clean(was))
            item["as_copied"]["names_checksum"] = reconcile.names_checksum("Story", was)
            answer = lambda path, params=None, name=now: (200, {}, named("1", "DEMO-1", "Story", name, "2026-11-17T08:00:00Z"))     # noqa: E731
            kind, value = reconcile.ask_item(reconcile.Connection(answer, "x"), "1", "DEMO")
            entry = reconcile.classify(item, kind, value, NOW)
            self.assertEqual(entry["state"], "stale", (was, now))
            self.assertIn("in a way the cleaned names here do not show", entry["reason"])
            unchanged = lambda path, params=None, name=was: (200, {}, named("1", "DEMO-1", "Story", name, "2026-11-17T08:00:00Z"))   # noqa: E731
            kind, value = reconcile.ask_item(reconcile.Connection(unchanged, "x"), "1", "DEMO")
            self.assertEqual(reconcile.classify(item, kind, value, NOW)["state"], "synchronized")
        self.assertNotEqual(reconcile.names_checksum("Story", "QA:Review"), reconcile.names_checksum("Story", "QA/Review"))
        self.assertNotEqual(reconcile.names_checksum("Story", "a"), reconcile.names_checksum("Bug", "a"))
        self.assertEqual(reconcile.names_checksum("Story", "To Do"), fake_jira.names_checksum("Story", "To Do"), "written twice, once by the tool and once by the made-up Jira")

    def test_a_copy_with_no_checksum_of_names_is_compared_by_cleaned_names_and_the_report_says_so(self):
        copy = fake_jira.local_copy()
        for item in copy["items"][:4]:
            del item["as_copied"]["names_checksum"]
        self.save_copy(copy)
        code, text = self.report()
        self.assertEqual(code, 0, text)
        self.assertIn("**4 of the 16 items of this copy carry no checksum of their names as Jira wrote them,**", self.text())
        self.assertIn("would not be seen", self.text())
        self.save_copy(fake_jira.local_copy())
        self.report(name="whole")
        self.assertIn("Each item of this copy carries a checksum of its type and status names as Jira wrote them", self.text(".md", "whole"))
        self.assertNotIn("carry no checksum", self.text(".md", "whole"))


class TheCountsAddUp(Case):
    def test_the_report_gives_the_count_of_each_state_and_a_total_of_the_items_considered(self):
        code, text = self.report()
        self.assertEqual(code, 0, text)
        want = {}
        for state in self.expected().values():
            want[state] = want.get(state, 0) + 1
        report = self.text()
        for place, name in enumerate(reconcile.STATE_NAMES, 1):
            self.assertIn("| %d | %s | **%d** |" % (place, name, want[name]), report)
        self.assertIn("| | **All** | **18** | |", report)
        self.assertIn("- Items considered: **18**. That is 16 the local copy holds, and 2 more that Jira lists and the copy does not hold.", report)
        self.assertIn("5 + 2 + 2 + 1 + 3 + 2 + 3 = **18**", report)
        self.assertIn("**CHECK: 18 = 18. PASSED.**", report)
        self.assertIn("CHECK: 18 = 18. PASSED.", text)

    def test_the_check_is_the_first_section_of_the_report(self):
        self.report()
        headings = [line for line in self.text().split("\n") if line.startswith("## ")]
        self.assertEqual(headings[0], "## 1. The check that comes first")
        self.assertLess(self.text().index("CHECK: 18 = 18"), self.text().index("## 2. "))

    def test_the_tools_own_check_finds_an_item_in_two_states_in_none_or_in_no_real_state(self):
        copy = fake_jira.local_copy()
        _, _, entries = self.entries()
        extra = self.listed
        self.assertEqual(len(extra), 16, "the numbers Jira's list gave, and not the tool's own entries")
        self.assertEqual(reconcile.own_check(entries, copy, extra)[2], [])
        twice = entries + [dict(entries[0], state="stale")]
        self.assertTrue(any("given 2 states" in p for p in reconcile.own_check(twice, copy, extra)[2]))
        self.assertTrue(any("given no state" in p for p in reconcile.own_check(entries[1:], copy, extra)[2]))
        odd = [dict(entries[0], state="fine")] + entries[1:]
        problems = reconcile.own_check(odd, copy, extra)[2]
        self.assertTrue(any("not one of the states" in p for p in problems))
        self.assertTrue(any("add up to 17 and 18" in p for p in problems))

    def test_the_check_is_not_only_the_tool_agreeing_with_itself(self):
        """Faults that leave every item with one real state, and the counts adding up."""
        copy = fake_jira.local_copy()
        _, _, entries = self.entries()
        dropped = [e for e in entries if e["state"] != "not yet copied"]
        problems = reconcile.own_check(dropped, copy, self.listed)[2]
        self.assertTrue(any("2 item(s) considered were given no state" in p for p in problems), "items Jira lists and the tool lost")
        all_in_sync = [dict(e, state="synchronized") for e in entries]
        problems = reconcile.own_check(all_in_sync, copy, self.listed)[2]
        self.assertEqual(sum("does not agree with what was found for it" in p for p in problems), 15, "every item that is not in sync")
        for number, wrong in (("30006", "conflicted"), ("30003", "stale"), ("30010", "missing from Jira"), ("30004", "failed to fetch"), ("30001", "not yet copied"), ("30015", "synchronized")):
            swapped = [dict(e, state=wrong) if e["id"] == number else e for e in entries]
            problems = reconcile.own_check(swapped, copy, self.listed)[2]
            self.assertEqual(problems, ["the item %s was given the state `%s`, which does not agree with what was found for it" % (number, wrong)])
        self.assertEqual(set(reconcile.MUST_BE), set(reconcile.STATE_NAMES))
        self.assertEqual(reconcile.own_check(dropped, copy, None)[2], [], "with no list, the copy's items are all there is to count")

    def test_if_the_check_fails_no_report_is_written(self):
        real = reconcile.classify

        def dropping(item, kind, value, as_of):          # a fault in the tool: one item is given a state that does not exist
            entry = real(item, kind, value, as_of)
            return dict(entry, state="lost") if item["id"] == "30002" else entry
        with mock.patch.object(reconcile, "classify", dropping):
            code, text = self.report()
        self.assertEqual(code, 3, text)
        self.assertIn("CHECK FAILED", text)
        self.assertIn("RESULT: NO REPORT.", text)
        self.assertEqual(os.listdir(self.out), [])

    def test_the_scenario_items_jira_has_that_were_never_copied_are_counted(self):
        """A report that walked only the local copy would say 16 of 16."""
        got, _, entries = self.entries()
        self.assertEqual([e["id"] for e in entries if e["state"] == "not yet copied"], ["30015", "30016"])
        self.assertEqual(len(entries), len(fake_jira.local_copy()["items"]) + 2)
        self.report()
        self.assertIn("### Not yet copied: 2", self.text())


class EveryExceptionIsExplained(Case):
    def test_each_item_not_in_sync_has_a_reason_a_next_action_and_a_line_in_the_log(self):
        self.report()
        sections = self.sections()
        want = self.expected()
        for number, state in want.items():
            if state == "synchronized":
                continue
            block = [b for b in sections[state.lower()].split("\n- **")[0:] if "[%s]" % number in b.split("\n")[0]]
            self.assertEqual(len(block), 1, "%s is listed %d times under %s" % (number, len(block), state))
            self.assertRegex(block[0], r"  - Reason: .{20,}")
            self.assertRegex(block[0], r"  - Next: .{20,}")
            self.assertRegex(block[0], r"  - Log: line L[0-9]{3} of `report.log.md`\.")
        listed = sum(section.count("\n  - Reason: ") for section in sections.values())
        self.assertEqual(listed, 15)
        self.assertNotIn("synchronized", sections)

    def test_a_stale_item_names_its_age_and_the_limit_and_which_side_it_is_on(self):
        self.report()
        stale = self.sections()["stale"]
        self.assertIn("**DEMO-6** [30006]\n  - Reason: Jira changed it at 2026-11-20T09:00:00Z: its status is now `In Progress`, and was `To Do` when copied. The copy has not been changed locally.\n"
                      "  - Error class: none. Jira answered; this is not a failure to fetch.\n  - Age: **3 hours**. Limit: **24 hours**. Within the limit.\n  - Next: The next sync should pick it up.", stale)
        self.assertIn("  - Age: **2 days 2 hours**. Limit: **24 hours**. **Over the limit**.\n  - Next: Sync it now, and find out why the last sync missed it.", stale)
        self.assertEqual(stale.count("  - Age: "), 3)
        self.assertEqual(stale.count("Limit: **24 hours**"), 3)

    def test_the_age_is_from_jiras_change_to_the_time_the_report_is_as_of(self):
        got, _, _ = self.entries(as_of="2026-11-21T09:00:00Z")
        self.assertEqual((got["30006"]["age_seconds"], got["30006"]["over_limit"]), (24 * 3600, False), "exactly at the limit is not over it")
        got, _, _ = self.entries(as_of="2026-11-21T09:00:01Z")
        self.assertEqual((got["30006"]["age_seconds"], got["30006"]["over_limit"]), (24 * 3600 + 1, True))
        got, _, _ = self.entries(as_of="2026-11-20T08:00:00Z")
        self.assertEqual(got["30006"]["state"], "stale", "a change Jira dates after the report's clock is still a change")
        self.assertEqual(reconcile.span(got["30006"]["age_seconds"]), "no time (Jira dates the change after this report's clock)")

    def test_a_failed_item_names_its_error_class_from_a_fixed_list(self):
        got, _, _ = self.entries()
        classes = {number: e["error_class"] for number, e in got.items() if e["state"] == "failed to fetch"}
        self.assertEqual(classes, {"30010": "rate limited (429)", "30011": "server error (5xx)", "30012": "forbidden (403)", "30014": "unreadable answer", "30017": "timed out"})
        self.assertTrue(set(classes.values()) <= set(reconcile.NEXT_FOR_FAILURE))
        self.assertTrue(all(e["error_class"] is None for e in got.values() if e["state"] != "failed to fetch"))
        self.report()
        self.assertEqual(self.sections()["failed to fetch"].count("  - Error class: **"), 5)
        blocks = {b.split("]")[0].split("[")[1]: b for section in self.sections().values() for b in section.split("\n- **") if "[" in b.split("\n")[0]}
        self.assertEqual(len(blocks), 15)
        for number, block in blocks.items():        # the class is on the item's own lines, and is the fixture's
            if number in classes:
                self.assertIn("  - Error class: **%s**." % classes[number], block)
                self.assertIn("  - Reason: Jira could not be read for this item: %s." % classes[number], block)
            else:
                self.assertIn("  - Error class: none. Jira answered; this is not a failure to fetch.", block)
                self.assertNotIn("Error class: **", block)

    def test_nothing_jira_said_in_refusing_is_in_the_report_the_log_the_history_or_the_output(self):
        code, text = self.report()
        everything = text + self.text() + self.text(".log.md") + self.text(".history.json")
        for word in PRIVATE_WORDS:
            self.assertNotIn(word, everything)
        self.assertTrue(any(word in json.dumps(fake_jira.FakeJira().get("/rest/api/3/issue/30010")[2]) for word in PRIVATE_WORDS), "the made-up Jira does send it")

    def test_every_class_of_failure(self):
        cases = {403: "forbidden (403)", 429: "rate limited (429)", 500: "server error (5xx)", 503: "server error (5xx)", 599: "server error (5xx)", 302: "unexpected status", 418: "unexpected status", 400: "unexpected status"}
        for status, want in cases.items():
            got, _, _ = self.entries(faults={"all": status})
            self.assertEqual(set(e["error_class"] for e in got.values() if e["state"] == "failed to fetch"), {want}, status)
            self.assertEqual(sum(1 for e in got.values() if e["state"] == "failed to fetch"), 16, "every item the copy holds failed")
        for problem, want in ((OSError("made up"), "network error"), (TimeoutError(), "timed out"), (OSError("the read operation timed out"), "timed out")):
            conn = reconcile.Connection(mock.Mock(side_effect=problem), "x")
            self.assertEqual(reconcile.ask_item(conn, "1", "DEMO"), ("failed", want))

    def test_answers_that_are_not_an_item_are_failures_and_not_guesses(self):
        good = fake_jira.shaped("1", "DEMO-1", "Story", "To Do", "2026-11-17T08:00:00Z")
        spoiled = {"another number": dict(good, id="2"), "no key": {k: v for k, v in good.items() if k != "key"}, "no fields": {"id": "1", "key": "DEMO-1"},
                   "no status": dict(good, fields=dict(good["fields"], status=None)), "a time that cannot be read": dict(good, fields=dict(good["fields"], updated="yesterday")),
                   "a list": [], "nothing": {}}
        for what, body in spoiled.items():
            conn = reconcile.Connection(lambda path, params=None, body=body: (200, {}, body), "x")
            self.assertEqual(reconcile.ask_item(conn, "1", "DEMO"), ("failed", "unreadable answer"), what)

    def test_a_reader_can_tell_what_to_do_next_for_each_kind_of_exception(self):
        got, _, _ = self.entries()
        nexts = {state: set(e["next"] for e in got.values() if e["state"] == state) for state in reconcile.STATE_NAMES}
        self.assertIn("Do not delete the copy on the strength of this report.", " ".join(nexts["missing from Jira"]))
        self.assertIn("Do not sync over either.", " ".join(nexts["conflicted"]))
        self.assertIn("A sync would overwrite it.", " ".join(nexts["changed locally only"]))
        self.assertIn("Copy it with the next sync.", " ".join(nexts["not yet copied"]))
        self.assertEqual(len(nexts["stale"]), 2, "one action for within the limit and another for over it")
        self.assertEqual(len(nexts["failed to fetch"]), 5, "a different action for each class of failure in the fixture")
        self.assertEqual(nexts["synchronized"], {"None."})
        for state, actions in nexts.items():
            self.assertTrue(all(len(a) > 3 for a in actions), state)


class AnItemThatFitsTwoStates(Case):
    def test_it_is_given_the_earlier_state_and_says_what_else_it_fits(self):
        got, _, _ = self.entries()
        self.assertEqual((got["30005"]["state"], got["30005"]["also"]), ("missing from Jira", ["changed locally (status `In Progress` to `Done`). That change has nowhere to go"]))
        self.assertEqual(got["30008"]["state"], "conflicted")
        self.assertEqual(got["30008"]["also"], ["stale: behind by 5 hours; the limit is 24 hours: within the limit"])
        self.assertEqual(got["30009"]["also"], ["stale: behind by 2 days; the limit is 24 hours: OVER THE LIMIT"])
        self.assertEqual((got["30011"]["state"], got["30011"]["also"]), ("failed to fetch", ["changed locally (status `To Do` to `Done`). Whether Jira changed too is not known"]))
        self.assertEqual(sum(1 for e in got.values() if e["also"]), 4)

    def test_the_report_counts_them_and_shows_each(self):
        self.report()
        self.assertIn("4 items also fit a later state than the one given.", self.text())
        self.assertEqual(self.text().count("  - Also: "), 4)

    def test_a_failed_fetch_is_never_called_anything_else_whatever_the_copy_holds(self):
        for held in (None, "Done"):
            entry = reconcile.classify(copy_item(1, "DEMO-1", "To Do", held), "failed", "timed out", NOW)
            self.assertEqual(entry["state"], "failed to fetch")
        got, _, _ = self.entries(faults={"all": 500})
        self.assertFalse(any(e["state"] == "synchronized" for e in got.values()))

    def test_synchronized_is_only_what_is_left(self):
        got, _, _ = self.entries()
        for number, e in got.items():
            if e["state"] == "synchronized":
                row = [r for r in fake_jira.ROWS if r[0] == number][0]
                self.assertEqual((row[4], row[5]), (("same",), None))

    def test_a_new_key_or_another_project_is_said(self):
        got, _, _ = self.entries()
        self.assertIn("its key is now DEMO-180", got["30018"]["reason"])
        conn = reconcile.Connection(lambda path, params=None: (200, {}, fake_jira.shaped("1", "OTHER-9", "Story", "To Do", "2026-11-17T08:00:00Z")), "x")
        self.assertEqual(reconcile.ask_item(conn, "1", "DEMO"), ("gone", "moved"))
        moved = reconcile.classify(copy_item(1, "DEMO-1"), "gone", "moved", NOW)
        plain = reconcile.classify(copy_item(1, "DEMO-1"), "gone", None, NOW)
        self.assertEqual(moved["state"], "missing from Jira")
        self.assertIn("in another project", moved["reason"])
        self.assertIn("It was moved to another project.", moved["next"])
        self.assertNotIn("OTHER", json.dumps(moved), "the other project's key is not this report's to print")
        self.assertEqual(plain["reason"], "Jira answers that it is not there.")
        self.assertIn("deleted, moved to another project, or hidden", plain["next"])


class TheSameInputGivesTheSameReport(Case):
    def test_twice_gives_the_same_three_files_and_the_second_time_writes_none(self):
        self.report()
        before = self.files()
        self.assertEqual(sorted(before), ["report.history.json", "report.log.md", "report.md"])
        code, text = self.report()
        self.assertEqual(code, 0)
        self.assertEqual(self.files(), before)
        self.assertEqual(text.count("not written: byte for byte the same"), 3)
        self.assertIn("RESULT: REPORT UNCHANGED: the same input gave the same report.", text)

    def test_the_order_of_the_items_in_the_copy_does_not_matter(self):
        self.report(name="one")
        copy = fake_jira.local_copy()
        copy["items"] = list(reversed(copy["items"]))
        self.save_copy(copy)
        self.report(name="two")
        self.assertEqual(self.text(".md", "one"), self.text(".md", "two").replace("two.log.md", "one.log.md"))

    def test_the_time_the_report_is_as_of_is_part_of_the_input(self):
        self.report()
        first = self.text()
        self.report(as_of="2026-11-21T12:00:00Z")
        self.assertNotEqual(self.text(), first)
        self.assertIn("  - Age: **1 day 3 hours**. Limit: **24 hours**. **Over the limit**.", self.text())

    def test_a_made_up_run_needs_the_time_and_a_time_must_be_a_time(self):
        code, text = self.main("report", "--source", "fake", "--copy", self.copy_path, "--out-dir", self.out, "--name", "report")
        self.assertEqual(code, 1)
        self.assertIn("needs --as-of", text)
        for bad in ("now", "2026-11-20", "2026-13-40T99:00:00Z", "2026-11-20T12:00:00+0100"):
            self.assertEqual(self.report(as_of=bad)[0], 1, bad)
        self.assertEqual(os.listdir(self.out), [])


class TheTrend(Case):
    def test_a_run_is_added_once_for_each_distinct_input_and_the_last_five_are_shown(self):
        for day in range(20, 27):
            self.report(as_of="2026-11-%dT12:00:00Z" % day)
            self.report(as_of="2026-11-%dT12:00:00Z" % day)
        history = json.loads(self.text(".history.json"))
        self.assertEqual(len(history["runs"]), 7)
        report = self.text()
        trend = report[report.index("## 5. "):report.index("## 6. ")]
        rows = [line for line in trend.split("\n") if line.startswith("| 2026-")]
        self.assertEqual([row.split(" | ")[0].strip("| ") for row in rows], ["2026-11-%dT12:00:00Z" % day for day in range(22, 27)])
        self.assertIn("## 5. The trend: the last 5 runs", report)
        self.assertTrue(all(row.endswith("| 18 | yes |") for row in rows), rows)
        self.assertEqual([run["as_of"] for run in history["runs"]], ["2026-11-%dT12:00:00Z" % day for day in range(20, 27)])

    def test_the_trend_is_in_order_of_time_whatever_order_the_reports_were_run_in_and_the_history_is_capped(self):
        for day in (25, 21, 23):
            self.report(as_of="2026-11-%dT12:00:00Z" % day)
        rows = [line.split(" | ")[0].strip("| ") for line in self.text().split("\n") if line.startswith("| 2026-")]
        self.assertEqual(rows, ["2026-11-21T12:00:00Z", "2026-11-23T12:00:00Z", "2026-11-25T12:00:00Z"])
        with mock.patch.object(reconcile, "HISTORY_KEEPS", 2):
            self.report(as_of="2026-11-26T12:00:00Z")
        self.assertEqual([run["as_of"] for run in json.loads(self.text(".history.json"))["runs"]], ["2026-11-25T12:00:00Z", "2026-11-26T12:00:00Z"])

    def test_two_inputs_with_the_same_counts_are_two_runs(self):
        self.report()
        copy = fake_jira.local_copy()
        copy["items"][0]["copied_at"] = "2026-11-18T08:00:00Z"          # another input; every state is as it was
        self.save_copy(copy)
        code, text = self.report()
        self.assertEqual(code, 0, text)
        runs = json.loads(self.text(".history.json"))["runs"]
        self.assertEqual(len(runs), 2)
        self.assertEqual(runs[0]["counts"], runs[1]["counts"])
        self.assertNotEqual(runs[0]["input"], runs[1]["input"])
        self.assertIn("This input was added.", text)

    def test_the_report_and_the_log_of_one_run_carry_one_mark(self):
        code, text = self.report()
        mark = re.search(r"Run mark: `([0-9a-f]{16})`", self.text()).group(1)
        self.assertIn("Run mark: `%s`." % mark, self.text(".log.md"))
        self.assertIn("Run mark: %s." % mark, text)
        self.assertEqual(json.loads(self.text(".history.json"))["runs"][-1]["input"], mark)
        self.report(as_of="2026-11-21T12:00:00Z")
        self.assertNotIn(mark, self.text() + self.text(".log.md"))

    def test_the_first_report_shows_itself(self):
        self.report()
        self.assertIn("## 5. The trend: the last 1 run\n", self.text())
        self.assertIn("| 2026-11-20T12:00:00Z | 5 | 2 | 2 | 1 | 3 | 2 | 3 | 18 |", self.text())

    def test_a_history_that_is_not_the_tools_is_left_alone(self):
        path = os.path.join(self.out, "report.history.json")
        for text in ("{", '{\n "format": "jira-reconcile-history/1", "runs": "none"}', '{\n "format": "jira-reconcile-history/1",\n "runs": [{"input": "x", "as_of": "y", "counts": {}, "total": 1}]}', "[]"):
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            code, out = self.report()
            self.assertEqual(code, 1, out)
            self.assertTrue("is not one this tool wrote" in out or "could not be read" in out, out)
            self.assertNotIn("did not foresee", out)
            with open(path, encoding="utf-8") as f:
                self.assertEqual(f.read(), text)
            self.assertEqual(os.listdir(self.out), ["report.history.json"])


class TheFetchLog(Case):
    def test_each_exception_cites_the_line_of_the_request_that_put_it_in_its_state(self):
        self.report()
        log = {int(line.split("**L")[1][:3]): line for line in self.text(".log.md").split("\n") if line.startswith("- **L")}
        self.assertEqual(sorted(log), list(range(1, 18)))
        got, _, _ = self.entries()
        for number, e in got.items():
            line = log[e["log_line"]]
            if e["state"] == "not yet copied":
                self.assertIn("/rest/api/3/search/jql", line)
            else:
                self.assertIn("/rest/api/3/issue/%s`" % number, line)
        self.assertIn("status 429", log[got["30010"]["log_line"]])
        self.assertIn("timed out", log[got["30017"]["log_line"]])
        self.assertIn("status 404", log[got["30004"]["log_line"]])

    def test_the_log_holds_no_answer_only_what_was_asked_and_the_class_of_what_came_back(self):
        self.report()
        for line in self.text(".log.md").split("\n"):
            if line.startswith("- **L"):
                self.assertRegex(line, r"^- \*\*L[0-9]{3}\*\* GET `/rest/api/3/(issue/[0-9]+|search/jql)` — (status [0-9]{3}|timed out|network error)$")


class WhenTheListCannotBeRead(Case):
    def test_the_report_is_written_says_incomplete_and_counts_only_what_the_copy_holds(self):
        for fault, klass in ((500, "server error (5xx)"), (429, "rate limited (429)"), ("unreachable", "network error")):
            code, text = self.report(faults={"listing": fault}, name="r%s" % fault)
            self.assertEqual(code, 2, text)
            self.assertIn("INCOMPLETE: Jira's list of the project could not be read (%s). Items Jira has and the copy lacks are NOT counted." % klass, text)
            self.assertIn("RESULT: REPORT WRITTEN, AND INCOMPLETE. 16 items considered", text)
            report = self.text(".md", "r%s" % fault)
            self.assertIn("**INCOMPLETE.** Jira's list of the project could not be read (%s; line L017 of `r%s.log.md`)." % (klass, fault), report)
            self.assertIn("- Items considered: **16**. That is 16 the local copy holds.", report)
            self.assertNotIn("### Not yet copied", report)
            self.assertLess(report.index("**INCOMPLETE.**"), report.index("## 2. "))
            self.assertIn("| 6 | not yet copied | **NOT KNOWN** |", report)
            self.assertIn("| | **All** | **16** (the local copy only) | |", report)
            self.assertIn("  6. not yet copied         NOT KNOWN", text)
            self.assertIn("- Jira's list of the project: could not be read.", report)
            trend = [line for line in report.split("\n") if line.startswith("| 2026-")]
            self.assertEqual(len(trend), 1)
            self.assertTrue(trend[0].endswith("| not known | 3 | 16 | **NO**: Jira's list could not be read |"), trend[0])
            self.assertTrue(json.loads(self.text(".history.json", "r%s" % fault))["runs"][0]["incomplete"])
        code, text = self.report(name="whole")
        self.assertIn("- Jira's list of the project: **16 items**, line L017 of `whole.log.md`.", self.text(".md", "whole"))
        self.assertIn("  Jira's list of the project: 16 items.", text)

    def test_with_nothing_in_the_copy_and_no_list_the_report_says_nothing_was_considered(self):
        self.save_copy(dict(fake_jira.local_copy(), items=[]))
        code, text = self.report(faults={"listing": 500})
        self.assertEqual(code, 2, text)
        self.assertIn("None: no items were considered.", self.text())
        self.assertIn("- Items considered: **0**.", self.text())

    def test_a_list_that_cannot_be_trusted_is_a_list_that_could_not_be_read(self):
        page = {"issues": [{"id": "1", "key": "DEMO-1", "fields": {}}], "isLast": True}
        spoiled = {"an item twice": dict(page, issues=page["issues"] * 2), "an item of another project": dict(page, issues=[{"id": "1", "key": "OTHER-1", "fields": {}}]),
                   "an item with no number": dict(page, issues=[{"key": "DEMO-1"}]), "no word that it is the last page": {"issues": page["issues"], "isLast": False},
                   "an empty page that says there is more": {"issues": [], "nextPageToken": "x", "isLast": False}, "not a page": {"values": []}, "a marker that is a number": dict(page, nextPageToken=5)}
        for what, body in spoiled.items():
            conn = reconcile.Connection(lambda path, params=None, body=body: (200, {}, body), "x")
            self.assertEqual(reconcile.list_project(conn, "DEMO"), (None, "unreadable answer"), what)

    def test_the_list_comes_in_pages_and_every_page_is_read(self):
        with mock.patch.object(reconcile, "PAGE", 4):
            got, failure, _ = self.entries()
        self.assertIsNone(failure)
        self.assertEqual(sum(1 for e in got.values() if e["state"] == "not yet copied"), 2)
        self.assertEqual(sum(1 for _, path, _ in self.conn.sent if path == reconcile.SEARCH_PATH), 4)
        with mock.patch.object(reconcile, "PAGE", 4), mock.patch.object(reconcile, "MAX_PAGES", 2):
            _, failure, _ = self.entries()
        self.assertEqual(failure, "unreadable answer")

    def test_rejected_credentials_refuse_the_whole_run(self):
        code, text = self.report(faults={"all": 401})
        self.assertEqual(code, 1, text)
        self.assertIn("rejected the credentials (401)", text)
        self.assertEqual(os.listdir(self.out), [])
        code, text = self.report(faults={"listing": 401})
        self.assertEqual(code, 1, text)
        self.assertIn("rejected the credentials (401)", text)
        self.assertEqual(os.listdir(self.out), [])


class OtherPeoplesText(Case):
    def test_a_status_or_type_with_markup_is_cleaned_before_it_reaches_the_report(self):
        real = fake_jira.FakeJira.now

        def now(fake, number):
            status, body = real(fake, number)
            if number == "30006":
                body["fields"]["status"]["name"] = "Done | <b>x</b>‮\n## 9. Forged\n- **DEMO-1** [30001]"
            return status, body
        with mock.patch.object(fake_jira.FakeJira, "now", now):
            code, text = self.report()
        self.assertEqual(code, 0, text)
        report = self.text()
        self.assertEqual([line for line in report.split("\n") if line.startswith("## ")][-1], "## 6. What this report cannot tell")
        self.assertEqual(report.count("- **DEMO-1** [30001]"), 0, "a synchronized item is not listed as an exception, and a forged line did not get in")
        self.assertNotIn("<b>", report + text)
        self.assertNotIn("‮", report + text)

    def test_no_title_is_asked_for(self):
        fake = fake_jira.FakeJira()
        reconcile.reconcile(fake_jira.local_copy(), reconcile.Connection(fake.get, "x"), NOW)
        asked = [params.get("fields") for path, params in fake.asked]
        self.assertEqual(set(asked), {"issuetype,status,updated", "issuetype"})
        self.assertEqual(len(asked), 17, "every request the made-up Jira received was looked at")
        self.assertIn("summary", json.dumps(fake.get("/rest/api/3/issue/30001")[2]), "the made-up Jira does hold a title to give")


class TheLocalCopy(Case):
    def test_a_copy_that_is_not_in_the_form_the_tool_reads_is_not_used(self):
        good = fake_jira.local_copy()
        first = good["items"][0]
        bad = {
            "another format": dict(good, format="x"),
            "an item with no number": dict(good, items=[{k: v for k, v in first.items() if k != "id"}]),
            "a number with a leading zero": dict(good, items=[dict(first, id="030001")]),
            "a key with a line break": dict(good, items=[dict(first, as_copied=dict(first["as_copied"], key="DEMO-1\nRESULT: forged"))]),
            "a status with markup": dict(good, items=[dict(first, as_held=dict(first["as_held"], status="<b>Done</b>"))]),
            "a time that is not one": dict(good, items=[dict(first, copied_at="yesterday")]),
            "a field this tool does not read": dict(good, items=[dict(first, title="Made-up title")]),
            "one number twice": dict(good, items=[first, dict(good["items"][1], id=first["id"])]),
            "one key twice": dict(good, items=[first, dict(good["items"][1], as_copied=dict(good["items"][1]["as_copied"], key="DEMO-1"))]),
            "an item of another project": dict(good, items=[dict(first, as_copied=dict(first["as_copied"], key="OTHER-1"))]),
            "a project that is not a key": dict(good, project='DEMO" OR project = "OTHER'),
            "no word of which Jira it came from": {k: v for k, v in good.items() if k != "site_fingerprint"},
            "a made-up copy that names a site": dict(good, site_fingerprint="0123456789abcdef"),
            "a real copy that names no site": dict(good, source="live"),
            "a checksum of names that is not one": dict(good, items=[dict(first, as_copied=dict(first["as_copied"], names_checksum="<b>"))]),
            "a word more at the top": dict(good, note="RESULT: forged"),
        }
        for what, copy in bad.items():
            self.save_copy(copy)
            with mock.patch.object(fake_jira.FakeJira, "get", side_effect=AssertionError("Jira was asked")):
                code, text = self.report()
            self.assertEqual(code, 1, what)
            self.assertIn("REFUSED: the local copy ", text, "%s: refused, and for being what it is, not because something later broke" % what)
            self.assertNotIn("did not foresee", text, what)
            self.assertNotIn("forged", text)
            self.assertEqual(os.listdir(self.out), [], what)
        code, _ = self.main("report", "--source", "fake", "--copy", os.path.join(self.folder, "missing.json"), "--out-dir", self.out, "--name", "report", "--as-of", NOW)
        self.assertEqual(code, 1)

    def test_an_empty_copy_is_an_answer(self):
        self.save_copy(dict(fake_jira.local_copy(), items=[]))
        code, text = self.report()
        self.assertEqual(code, 0, text)
        self.assertIn("Items considered: 16 (0 in the local copy, 16 more in Jira only).", text)
        self.assertIn("  6. not yet copied         16", text)

    def test_the_copys_file_name_is_made_safe_before_it_is_in_the_report(self):
        odd = os.path.join(self.folder, "co`py|<b> x.json")
        self.save_copy(fake_jira.local_copy(), odd)
        code, text = self.main("report", "--source", "fake", "--copy", odd, "--out-dir", self.out, "--name", "report", "--as-of", NOW)
        self.assertEqual(code, 0, text)
        self.assertIn("Local copy: `co?py??b??x.json` (16 items).", self.text())
        self.assertNotIn("<b>", self.text() + text)

    def test_a_report_as_of_a_time_before_the_copy_was_taken_is_refused(self):
        code, text = self.report(as_of="2026-11-18T08:59:59Z")
        self.assertEqual(code, 1, text)
        self.assertIn("as of a time before the copy was taken", text)
        self.assertEqual(os.listdir(self.out), [])
        self.assertEqual(self.report(as_of=fake_jira.COPIED)[0], 0, "the moment it was copied is not before it")

    def test_the_report_does_not_change_the_copy(self):
        with open(self.copy_path, "rb") as f:
            before = (f.read(), os.stat(self.copy_path).st_mtime_ns)
        self.report()
        with open(self.copy_path, "rb") as f:
            self.assertEqual((f.read(), os.stat(self.copy_path).st_mtime_ns), before)


class TheFilesOnDisk(Case):
    def test_a_file_of_the_same_name_that_is_someone_elses_is_refused(self):
        for name in ("report.md", "report.log.md", "report.history.json"):
            path = os.path.join(self.out, name)
            with open(path, "w", encoding="utf-8") as f:
                f.write("# Someone's own notes\n")
            code, text = self.report()
            self.assertEqual(code, 1, text)
            with open(path, encoding="utf-8") as f:
                self.assertEqual(f.read(), "# Someone's own notes\n")
            self.assertEqual(os.listdir(self.out), [name])
            os.unlink(path)

    def test_links_second_names_and_the_copy_itself_are_not_written(self):
        elsewhere = os.path.join(self.folder, "elsewhere.md")
        with open(elsewhere, "w", encoding="utf-8") as f:
            f.write(reconcile.REPORT_HEADING + "DEMO\nkept elsewhere\n")
        os.symlink(elsewhere, os.path.join(self.out, "report.md"))
        self.assertEqual(self.report()[0], 1)
        os.unlink(os.path.join(self.out, "report.md"))
        os.link(elsewhere, os.path.join(self.out, "report.md"))
        self.assertEqual(self.report()[0], 1)
        with open(elsewhere, encoding="utf-8") as f:
            self.assertIn("kept elsewhere", f.read())
        os.unlink(os.path.join(self.out, "report.md"))
        shutil.copy(self.copy_path, os.path.join(self.out, "copy.history.json"))
        code, text = self.main("report", "--source", "fake", "--copy", os.path.join(self.out, "copy.history.json"), "--out-dir", self.out, "--name", "copy", "--as-of", NOW)
        self.assertEqual(code, 1, text)
        self.assertIn("would be the local copy itself", text)

    def test_the_log_option_cannot_name_the_tools_files_the_copy_or_a_strangers_file(self):
        self.report()
        before = self.files()
        theirs = os.path.join(self.folder, "notes.txt")
        with open(theirs, "w", encoding="utf-8") as f:
            f.write("mine\n")
        for log in (os.path.join(self.out, "report.md"), os.path.join(self.out, "REPORT.LOG.MD"), os.path.join(self.out, "report.history.json"), self.copy_path, theirs):
            code, text = self.report(extra=["--log", log])
            self.assertEqual(code, 1, log)
        self.assertEqual({k: v[0] for k, v in self.files().items()}, {k: v[0] for k, v in before.items()})
        with open(theirs, encoding="utf-8") as f:
            self.assertEqual(f.read(), "mine\n")
        log = os.path.join(self.folder, "log.txt")
        self.assertEqual(self.report(extra=["--log", log])[0], 0)
        self.assertEqual(self.report(extra=["--log", log])[0], 0)
        nowhere = os.path.join(self.folder, "no", "such", "folder", "log.txt")
        code, text = self.report(extra=["--log", nowhere])
        self.assertEqual(code, 1)
        self.assertIn("a place in a folder that is not there", text)
        self.assertFalse(os.path.exists(os.path.join(self.folder, "no")), "no folder is made for a log")
        for looks_alike in ("Project: my own notes\n", "REFUSED\n", "Project: DEMO\nmine\n"):
            with open(theirs, "w", encoding="utf-8") as f:
                f.write(looks_alike)
            self.assertEqual(self.report(extra=["--log", theirs])[0], 1, looks_alike)
            with open(theirs, encoding="utf-8") as f:
                self.assertEqual(f.read(), looks_alike)
        self.assertEqual(self.report(as_of="yesterday", extra=["--log", log])[0], 1)
        with open(log, encoding="utf-8") as f:
            self.assertTrue(f.read().startswith("REFUSED: --as-of"))
        self.assertEqual(self.report(extra=["--log", log])[0], 0, "a refusal this tool saved is the tool's own, and may be written over")

    def test_a_write_that_fails_part_way_says_which_files_were_written(self):
        real, calls = os.replace, []

        def second_fails(a, b):
            calls.append(b)
            if len(calls) == 2:
                raise OSError("made up")
            return real(a, b)
        with mock.patch.object(reconcile.os, "replace", second_fails):
            code, text = self.report()
        self.assertEqual(code, 1)
        self.assertIn("a file could not be written. Written before it failed: report.history.json.", text)
        self.assertIn("their run marks will differ", text)
        self.assertNotIn("RESULT:", text)
        self.assertEqual(os.listdir(self.out), ["report.history.json"])
        with mock.patch.object(reconcile.os, "replace", side_effect=OSError("made up")):
            code, text = self.report(name="other")
        self.assertIn("a file could not be written. Nothing was written.", text)

    def test_names_and_folders_that_are_not_allowed_and_a_write_that_fails(self):
        for name in ("Report", "../x", "a b", ""):
            self.assertEqual(self.report(name=name)[0], 1)
        self.assertEqual(self.main("report", "--source", "fake", "--copy", self.copy_path, "--out-dir", os.path.join(self.folder, "missing"), "--name", "report", "--as-of", NOW)[0], 1)
        with mock.patch.object(reconcile.os, "replace", side_effect=OSError("made up")):
            code, text = self.report()
        self.assertEqual(code, 1)
        self.assertNotIn("RESULT:", text)
        self.assertEqual(os.listdir(self.out), [])

    def test_something_unforeseen_is_a_refusal_and_not_a_crash(self):
        with mock.patch.object(reconcile, "reconcile", side_effect=RuntimeError("unforeseen")):
            code, text = self.report()
        self.assertEqual(code, 1)
        self.assertIn("did not foresee (RuntimeError)", text)

    def test_times_and_spans(self):
        self.assertEqual(reconcile.in_utc("2026-11-20T14:00:00.000+0200"), "2026-11-20T12:00:00Z")
        self.assertEqual(reconcile.in_utc("2026-11-20T07:30:00-0430"), "2026-11-20T12:00:00Z")
        self.assertEqual(reconcile.in_utc("2026-11-20T12:00:00.123+0000"), "2026-11-20T12:00:00Z")
        self.assertIsNone(reconcile.in_utc("2026-11-20T12:00:00"))
        self.assertIsNone(reconcile.in_utc(5))
        spans = {0: "under a minute", 59: "under a minute", 60: "1 minute", 3600: "1 hour", 3660: "1 hour 1 minute", 86400: "1 day", 2 * 86400 + 300: "2 days 5 minutes",
                 86400 + 2 * 3600 + 3 * 60: "1 day 2 hours 3 minutes", 24 * 3600 + 1: "1 day"}
        for seconds, want in spans.items():
            self.assertEqual(reconcile.span(seconds), want, seconds)

    def test_what_is_printed_lists_every_exception_and_the_synchronized_are_listed_in_the_report(self):
        code, text = self.report()
        for line in ("  DEMO-6    [30006]  STALE. Age 3 hours, limit 24 hours, within.  (log L006)", "  DEMO-10   [30010]  FAILED TO FETCH. Error class: rate limited (429).  (log L010)",
                     "  DEMO-15   [30015]  NOT YET COPIED.  (log L017)", "EVERY ITEM THAT IS NOT SIMPLY IN SYNC: 15", "  The reason and the next action for each are in the report."):
            self.assertIn(line, text)
        self.assertEqual(sum(1 for line in text.split("\n") if re.match(r"  DEMO-[0-9]+ +\[[0-9]+\]  [A-Z ]+\.", line)), 15)
        self.assertEqual(text.count(" STALE. Age "), 3)
        in_sync = sorted(number for number, state in self.expected().items() if state == "synchronized")
        self.assertIn("## 4. Synchronized: 3\n\nJira was asked about each of these, one request each, and has what the copy has: %s.\n" % ", ".join(
            "DEMO-%d [%s]" % (int(number) - 30000, number) for number in in_sync), self.text())

    def test_the_report_says_it_has_seven_states_where_the_quest_names_five(self):
        self.report()
        self.assertIn("**Seven states, where the quest this was built for names five.** `changed locally only` and `not yet copied` were added.", self.text())
        self.assertIn("The quest names five states", fake_jira.describe())
        for heading, count in re.findall(r"^### ([A-Za-z ]+): ([0-9]+)$", self.text(), re.M):
            self.assertEqual(self.sections()[heading.lower()].count("\n  - Reason: ") + self.sections()[heading.lower()].startswith("  - Reason: "), int(count), heading)

    def test_the_states_command_prints_the_states_in_their_order(self):
        code, text = self.main("states")
        self.assertEqual(code, 0)
        positions = [text.index("%d. %s" % (place, name)) for place, name in enumerate(reconcile.STATE_NAMES, 1)]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(reconcile.STATE_NAMES, ["failed to fetch", "missing from Jira", "conflicted", "changed locally only", "stale", "not yet copied", "synchronized"])
        self.assertIn("24 hours", text)


class Adopting(Case):
    def result(self, **changes):
        items = [{"id": "10000", "key": "SCRUM-1", "issuetype": "Task", "status": "To Do", "status_category": "new", "updated": "2026-11-27T00:56:59Z"},
                 {"id": "10001", "key": "SCRUM-2", "issuetype": "Story", "status": "In Progress", "status_category": "indeterminate", "updated": "2026-11-10T20:02:32Z"}]
        result = {"format": "jira-query-stories/1", "complete": True, "project": "SCRUM", "source": "live", "site_fingerprint": "0123456789abcdef", "taken_at": "2026-11-27T19:00:22Z", "items": items}
        result.update(changes)
        path = os.path.join(self.folder, "result.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(result, f)
        return path

    def test_a_saved_query_result_becomes_a_copy_the_tool_reads(self):
        out = os.path.join(self.folder, "adopted.json")
        code, text = self.main("adopt", "--from", self.result(), "--out", out)
        self.assertEqual(code, 0, text)
        copy = reconcile.load_copy(out)
        self.assertEqual((copy["project"], copy["source"], copy["site_fingerprint"], len(copy["items"])), ("SCRUM", "live", "0123456789abcdef", 2))
        self.assertEqual(copy["items"][0], {"id": "10000", "copied_at": "2026-11-27T19:00:22Z", "as_copied": {"key": "SCRUM-1", "issuetype": "Task", "status": "To Do", "updated": "2026-11-27T00:56:59Z"},
                                            "as_held": {"issuetype": "Task", "status": "To Do"}})
        self.assertEqual(self.main("adopt", "--from", self.result(), "--out", out)[0], 1, "it is not written over")

    def test_what_is_not_a_complete_result_is_not_adopted(self):
        out = os.path.join(self.folder, "adopted.json")
        for changes in ({"complete": False}, {"format": "x"}, {"taken_at": "yesterday"}, {"items": [{"id": "1"}]}, {"project": "A B"}):
            self.assertEqual(self.main("adopt", "--from", self.result(**changes), "--out", out)[0], 1, changes)
            self.assertFalse(os.path.exists(out))
        self.assertEqual(self.main("adopt", "--from", os.path.join(self.folder, "missing.json"), "--out", out)[0], 1)

    def test_nothing_is_adopted_that_the_report_would_then_refuse(self):
        out = os.path.join(self.folder, "adopted.json")
        with open(self.result(), encoding="utf-8") as f:
            items = json.load(f)["items"]
        bad = {"one number twice": {"items": [items[0], dict(items[1], id="10000")]}, "one key twice": {"items": [items[0], dict(items[1], key="SCRUM-1")]},
               "an item of another project": {"items": [items[0], dict(items[1], key="OTHER-2")]}, "a real result that names no site": {"site_fingerprint": None},
               "a made-up result that names a site": {"source": "fake"}, "a site that is not a fingerprint": {"site_fingerprint": "https://real.example.invalid"}}
        for what, changes in bad.items():
            code, text = self.main("adopt", "--from", self.result(**changes), "--out", out)
            self.assertEqual(code, 1, what)
            self.assertIn("REFUSED: the result cannot be made into a local copy this tool reads", text, what)
            self.assertIn("Nothing was written", text, what)
            self.assertNotIn("did not foresee", text, what)
            self.assertFalse(os.path.exists(out), what)

    def test_names_with_marks_are_cleaned_and_adopting_says_what_it_cannot_know(self):
        out = os.path.join(self.folder, "adopted.json")
        with open(self.result(), encoding="utf-8") as f:
            items = json.load(f)["items"]
        code, text = self.main("adopt", "--from", self.result(items=[dict(items[0], status="QA/Review"), items[1]]), "--out", out)
        self.assertEqual(code, 0, text)
        copy = reconcile.load_copy(out)
        self.assertEqual(copy["items"][0]["as_copied"]["status"], "QA?Review")
        self.assertEqual(copy["items"][0]["as_held"]["status"], "QA?Review", "adopted as not changed locally")
        self.assertIn("1 item(s) had a name cleaned further here.", text)
        self.assertIn("as NOT changed locally", text)
        self.assertIn("carry no checksum of their names as Jira wrote them, and are compared by cleaned names", text)
        self.assertTrue(all("names_checksum" not in item["as_copied"] for item in copy["items"]))


class Response:
    def __init__(self, body):
        self.status, self.headers, self._body = 200, {}, json.dumps(body).encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class Opener:
    """Stands where the network would be. It answers from the made-up Jira and keeps each request."""

    def __init__(self, fake):
        self.fake, self.requests, self.waits = fake, [], []

    def open(self, request, timeout=None):
        import urllib.error
        self.requests.append(request)
        self.waits.append(timeout)
        url = urllib.parse.urlparse(request.full_url)
        status, _, body = self.fake.get(url.path, dict(urllib.parse.parse_qsl(url.query)))
        if status != 200:
            raise urllib.error.HTTPError(request.full_url, status, "made up", {}, io.BytesIO(json.dumps(body).encode("utf-8")))
        return Response(body)


class ARealJira(Case):
    ENV = {"JIRA_BASE_URL": "https://real.example.invalid", "JIRA_EMAIL": "someone@example.invalid", "JIRA_API_TOKEN": MADE_UP}

    def setUp(self):
        Case.setUp(self)
        self.save_copy(dict(fake_jira.local_copy(), source="live", site_fingerprint=reconcile.site_fingerprint("real.example.invalid")))

    def run_live(self, env=None, extra=(), faults=None):
        self.opener, self.handlers = Opener(fake_jira.FakeJira(faults)), []

        def build(*handlers):
            self.handlers.append(handlers)
            return self.opener
        with mock.patch.dict(os.environ, env or self.ENV), mock.patch.object(reconcile.urllib.request, "build_opener", build):
            return self.main("report", "--source", "live", "--copy", self.copy_path, "--out-dir", self.out, "--name", "real", "--as-of", NOW, *extra)

    def test_a_live_report_gives_the_same_states_and_sends_only_gets(self):
        code, text = self.run_live()
        self.assertEqual(code, 0, text)
        self.assertIn("5 + 2 + 2 + 1 + 3 + 2 + 3 = 18", text)
        self.assertEqual(sorted(set((r.get_method(), r.data, re.sub(r"[0-9]+$", "N", urllib.parse.urlparse(r.full_url).path)) for r in self.opener.requests)),
                         [("GET", None, "/rest/api/3/issue/N"), ("GET", None, "/rest/api/3/search/jql")])
        self.assertEqual(set(self.opener.waits), {30})
        self.assertEqual(self.handlers, [(reconcile.NoRedirect,)])
        self.assertIsNone(reconcile.NoRedirect().redirect_request(None, None, 302, "Found", {}, "https://elsewhere.example.invalid/"))
        for request in self.opener.requests:
            self.assertTrue(request.get_header("Authorization").startswith("Basic "))
            self.assertTrue(request.full_url.startswith("https://real.example.invalid/"))
            self.assertNotIn("summary", request.full_url)
        self.assertIn("Every one was a GET with no body", text)

    def test_a_real_servers_refusal_is_read_for_its_status_and_not_for_what_it_says(self):
        code, text = self.run_live()
        everything = text + self.text(".md", "real") + self.text(".log.md", "real")
        self.assertIn("rate limited (429)", everything)
        self.assertIn("forbidden (403)", everything)
        for word in PRIVATE_WORDS:
            self.assertNotIn(word, everything)

    def test_no_credential_or_site_address_is_in_the_output_the_log_or_the_files(self):
        import base64
        log = os.path.join(self.folder, "log.txt")
        code, text = self.run_live(extra=["--log", log])
        with open(log, encoding="utf-8") as f:
            everything = text + f.read() + self.text(".md", "real") + self.text(".log.md", "real") + self.text(".history.json", "real")
        encoded = base64.b64encode(("someone@example.invalid:" + MADE_UP).encode()).decode()
        for secret in (MADE_UP, "someone@example.invalid", encoded, "real.example.invalid"):
            self.assertNotIn(secret, everything)
        with mock.patch.dict(os.environ, self.ENV):
            _, secrets = reconcile.make_live(Opener(None))
        self.assertEqual(sorted(secrets), sorted([MADE_UP, "someone@example.invalid", encoded]))

    def test_a_token_that_would_reach_a_file_stops_the_run_before_anything_is_written(self):
        real = fake_jira.FakeJira.now

        def now(fake, number):
            status, body = real(fake, number)
            if number == "30006":
                body["fields"]["status"]["name"] = MADE_UP
            return status, body
        with mock.patch.object(fake_jira.FakeJira, "now", now):
            code, text = self.run_live()
        self.assertEqual(code, 1)
        self.assertNotIn(MADE_UP, text)
        self.assertEqual(os.listdir(self.out), [])

    def test_a_credential_in_any_output_stops_the_output_and_the_sites_address_is_taken_out_of_a_saved_one(self):
        with mock.patch.dict(os.environ, self.ENV), mock.patch.object(reconcile, "make_live", return_value=(reconcile.Connection(None, "x"), [MADE_UP])), \
                mock.patch.object(reconcile, "cmd_report", side_effect=lambda *a, **k: reconcile.say("leaked " + MADE_UP) or 0):
            code, text = self.main("report", "--source", "live", "--copy", self.copy_path, "--out-dir", self.out, "--name", "real")
        self.assertEqual(code, 1)
        self.assertNotIn(MADE_UP, text)
        self.assertIn("STOPPED", text)
        log = os.path.join(self.folder, "log.txt")
        with mock.patch.dict(os.environ, self.ENV), mock.patch.object(reconcile, "make_live", return_value=(reconcile.Connection(None, "real.example.invalid"), [])), \
                mock.patch.object(reconcile, "cmd_report", side_effect=lambda *a, **k: reconcile.say("Project: see https://real.example.invalid/x and real.example.invalid") or 0):
            self.main("report", "--source", "live", "--copy", self.copy_path, "--out-dir", self.out, "--name", "real", "--log", log)
        with open(log, encoding="utf-8") as f:
            saved = f.read()
        self.assertNotIn("real.example.invalid", saved)
        self.assertEqual(saved.count(reconcile.SITE_MARK), 2)

    def test_the_connection_builds_nothing_else_and_reports_the_method_it_built(self):
        with mock.patch.dict(os.environ, self.ENV):
            conn, _ = reconcile.make_live(Opener(None))
        for path in ("/rest/api/3/issue/DEMO-1", "/rest/api/3/issue/1/comment", "/rest/api/3/myself", "/rest/api/3/issue/1/../../x", "/rest/api/3/attachment/content/1"):
            with self.assertRaises(reconcile.Refused, msg=path):
                conn._get(path)
        self.assertFalse(hasattr(conn, "post") or hasattr(conn, "put") or hasattr(conn, "delete"))
        for sent in ([("POST", "/x", "status 200")], [("GET WITH A BODY", "/x", "status 200")], [("DELETE", "/x", "status 200")]):
            conn.sent = sent
            self.assertFalse(conn.only_gets())

        class Lying(reconcile.urllib.request.Request):
            def get_method(self):
                return "POST"
        with mock.patch.object(reconcile.urllib.request, "Request", Lying):
            code, text = self.run_live()
        self.assertIn("NOT EVERY ONE COULD BE READ BACK AS A PLAIN GET", text)

    def test_a_copy_from_another_jira_is_not_compared(self):
        self.save_copy(fake_jira.local_copy())
        code, text = self.run_live()
        self.assertEqual(code, 1, text)
        self.assertIn("made from another Jira", text)
        self.assertEqual(self.opener.requests, [])
        self.save_copy(dict(fake_jira.local_copy(), source="live", site_fingerprint="0123456789abcdef"))
        self.assertEqual(self.run_live()[0], 1)

    def test_a_base_address_that_is_not_https_and_the_sites_name_only_and_no_variables(self):
        for base in ("http://real.example.invalid", "https://real.example.invalid:8443", "https://real.example.invalid/jira", "https://user@real.example.invalid"):
            code, text = self.run_live(env=dict(self.ENV, JIRA_BASE_URL=base))
            self.assertEqual(code, 1, text)
            self.assertEqual(self.opener.requests, [])
        with mock.patch.dict(os.environ, {}, clear=True):
            code, text = self.main("report", "--source", "live", "--copy", self.copy_path, "--out-dir", self.out, "--name", "real")
        self.assertEqual(code, 1)
        self.assertIn("JIRA_BASE_URL is not set", text)


class TheFixtureItself(Case):
    def test_the_page_and_the_copy_on_disk_are_what_the_made_up_jira_writes(self):
        folder = os.path.abspath(os.path.join(SKILL, "..", "..", "context", "jira", "reconciliation"))
        with open(os.path.join(folder, "fixture.md"), encoding="utf-8") as f:
            self.assertEqual(f.read(), fake_jira.describe())
        with open(os.path.join(folder, "fixture-copy.json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f), fake_jira.local_copy())

    def test_it_has_every_state_and_items_that_fit_two(self):
        states = set(self.expected().values())
        self.assertEqual(states, set(reconcile.STATE_NAMES))
        for needed in ("synchronized", "missing from Jira", "stale", "conflicted", "failed to fetch"):
            self.assertIn(needed, states)
        self.assertIn("## Items that fit two states", fake_jira.describe())


if __name__ == "__main__":
    unittest.main()
