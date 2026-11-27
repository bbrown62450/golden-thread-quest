"""Tests for run_query.py, against the made-up Jira. No network. Every item and site here is made up."""
import argparse
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, SKILL)
import fake_jira    # noqa: E402
import run_query    # noqa: E402

CONFIG = os.path.abspath(os.path.join(SKILL, "..", "..", "context", "jira", "queries.yaml"))
FIXTURE = os.path.join(SKILL, "fixtures", "demo.json")
MADE_UP = "-".join(["made", "up", "value", "used", "only", "in", "tests"])      # stands where an API token would be
GOOD = """format: jira-saved-queries/1
page_size: 10
allowed_projects:
  - DEMO
queries:
  - name: all-stories
    purpose: 'Every story in the project.'
    filter: 'issuetype = Story'
"""


class Case(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix="gtq-query-test-")
        self.results = os.path.join(self.folder, "results")
        os.makedirs(self.results)
        self.out = os.path.join(self.results, "result.json")

    def tearDown(self):
        shutil.rmtree(self.folder, ignore_errors=True)

    # ---------------------------------------------------------- helpers

    def main(self, *argv):
        """The tool as the command line runs it. Returns (exit code, what it printed)."""
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed), contextlib.redirect_stderr(printed):
            try:
                code = run_query.main(list(argv))
            except SystemExit as stop:
                code = stop.code
        return code, printed.getvalue()

    def run_query(self, query="all-stories", faults=(), config=CONFIG, project="DEMO", extra=()):
        argv = ["run", "--config", config, "--query", query, "--project", project, "--source", "fake", "--fixture", FIXTURE, "--out", self.out]
        for fault in faults:
            argv += ["--fault", fault]
        return self.main(*(argv + list(extra)))

    def direct(self, fake, query="all-stories", config=CONFIG, project="DEMO"):
        """The tool against a made-up Jira the test holds, so the test can see and change what it is asked."""
        del run_query.LINES[:]
        conn = run_query.Connection(fake.get, fake.post, "jira.example.test")
        args = argparse.Namespace(query=query, project=project, out=self.out, set=None)
        code = run_query.cmd_run(args, run_query.load_config(config), conn, live=False)
        return code, "\n".join(run_query.LINES), conn

    def fake(self, **faults):
        return fake_jira.FakeJira.open(FIXTURE, faults)

    def config(self, text):
        path = os.path.join(self.folder, "queries.yaml")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path

    def result(self):
        with open(self.out, encoding="utf-8") as f:
            return json.load(f)

    def stories(self):
        with open(FIXTURE, encoding="utf-8") as f:
            return [i["key"] for i in json.load(f)["issues"] if i["issuetype"] == "Story"]

    def assert_nothing_left(self, text):
        """An incomplete run: exit code aside, no file of any kind is in the results folder, and the words say so."""
        self.assertEqual(os.listdir(self.results), [], "something was left in the results folder")
        self.assertIn("RESULT: INCOMPLETE", text)
        self.assertNotIn("RESULT: COMPLETE", text)
        self.assertIn("Items saved locally: 0", text)
        self.assertIn("No result file was written", text)


class TheConfiguration(Case):
    def test_the_real_file_has_a_name_and_a_purpose_for_every_query(self):
        config = run_query.load_config(CONFIG)
        self.assertGreaterEqual(len(config["queries"]), 4)
        for query in config["queries"]:
            self.assertRegex(query["name"], r"^[a-z][a-z0-9-]*$")
            self.assertGreater(len(query["purpose"].split()), 5)
            self.assertTrue(query["filter"])
        code, text = self.main("list", "--config", CONFIG)
        self.assertEqual(code, 0)
        for query in config["queries"]:
            self.assertIn(query["name"], text)
            self.assertIn(query["purpose"], text)

    def test_the_real_file_reads_the_same_with_a_full_yaml_reader(self):
        """This tool reads a small part of YAML by itself. If a full reader is to hand, the two must agree."""
        try:
            import yaml
        except ImportError:
            self.skipTest("PyYAML is not installed for this Python. Run with the project's own Python to make this comparison")
        with open(CONFIG, encoding="utf-8") as f:
            full = yaml.safe_load(f)
        mine = run_query.load_config(CONFIG)
        self.assertEqual(full["page_size"], mine["page_size"])
        self.assertEqual([p.upper() for p in full["allowed_projects"]], mine["projects"])
        self.assertEqual([(q["name"], q["purpose"], q["filter"], q.get("parameters", {})) for q in full["queries"]],
                         [(q["name"], q["purpose"], q["filter"], q["parameters"]) for q in mine["queries"]])

    def test_a_good_small_file_is_read(self):
        self.assertEqual(run_query.load_config(self.config(GOOD))["queries"][0]["filter"], "issuetype = Story")

    def test_what_is_wrong_in_a_file_is_refused(self):
        wrong = {
            "a tab": GOOD.replace("  - DEMO", "\t- DEMO"),
            "an unknown setting": GOOD + "extra: 1\n",
            "an unknown setting of a query": GOOD + "    order: 'key'\n",
            "the same name twice": GOOD + GOOD.split("queries:\n")[1],
            "no purpose": GOOD.replace("    purpose: 'Every story in the project.'\n", ""),
            "a purpose of one word": GOOD.replace("Every story in the project.", "Stories"),
            "no filter": GOOD.replace("    filter: 'issuetype = Story'\n", ""),
            "ORDER BY in the filter": GOOD.replace("issuetype = Story", "issuetype = Story ORDER BY created"),
            "a bracket that closes the project's": GOOD.replace("issuetype = Story", "issuetype = Story) OR (project = OTHER"),
            "an open bracket": GOOD.replace("issuetype = Story", "(issuetype = Story"),
            "an open quote": GOOD.replace("issuetype = Story", 'status = "To Do'),
            "a blank that is not declared": GOOD.replace("issuetype = Story", "updated >= {since}"),
            "a parameter that is not used": GOOD + "    parameters:\n      since: date\n",
            "a parameter of an unknown kind": GOOD.replace("issuetype = Story", "updated >= {since}") + "    parameters:\n      since: text\n",
            "a blank inside quotes": GOOD.replace("issuetype = Story", 'updated >= "{since}"') + "    parameters:\n      since: date\n",
            "a blank used twice": GOOD.replace("issuetype = Story", "updated >= {since} AND created >= {since}") + "    parameters:\n      since: date\n",
            "a page size of 0": GOOD.replace("page_size: 10", "page_size: 0"),
            "a page size of 101": GOOD.replace("page_size: 10", "page_size: 101"),
            "a page size in words": GOOD.replace("page_size: 10", "page_size: ten"),
            "no page size": GOOD.replace("page_size: 10\n", ""),
            "no allowed projects": GOOD.replace("allowed_projects:\n  - DEMO\n", ""),
            "another format": GOOD.replace("jira-saved-queries/1", "jira-saved-queries/2"),
            "a backslash in double quotes": GOOD.replace("'issuetype = Story'", '"status = \\"Done\\""'),
            "a setting twice": GOOD.replace("page_size: 10", "page_size: 10\npage_size: 50"),
            "a filter twice in one query": GOOD + "    filter: 'issuetype = Bug'\n",
            "a value that YAML would not read as text": GOOD.replace("'issuetype = Story'", "[issuetype = Story]"),
            "no queries": GOOD.split("queries:")[0] + "queries:\n",
            "an unseen character in a filter": GOOD.replace("issuetype = Story", "issuetype = Story​"),
        }
        for what, text in wrong.items():
            with self.subTest(what):
                self.assertNotEqual(text, GOOD)
                with self.assertRaises(run_query.Refused):
                    run_query.load_config(self.config(text))

    def test_what_the_readers_found_wrong_in_the_reading_of_a_file_is_refused(self):
        slash = chr(92)
        escape = "'labels = " + '"a' + slash + '"b") OR (project = OTHER) OR (labels = "c' + slash + '"d"' + "'"
        wrong = {
            "a backslash that hides a quote, to get out of the project (found by both readers)": GOOD.replace("'issuetype = Story'", escape),
            "any backslash in a filter": GOOD.replace("issuetype = Story", "labels = a" + slash + "b"),
            "parameters twice in one query": GOOD.replace("issuetype = Story", "updated >= {since} AND created >= {from}")
            + "    parameters:\n      since: date\n    parameters:\n      from: date\n",
            "a page size with a leading zero": GOOD.replace("page_size: 10", "page_size: 010"),
            "no space after a colon": GOOD.replace("page_size: 10", "page_size:10"),
            "a project YAML would read as false": GOOD.replace("  - DEMO", "  - NO"),
            "a name YAML would read as nothing": GOOD.replace("name: all-stories", "name: null"),
            "a document mark at the top": "---\n" + GOOD,
            "a byte-order mark at the top": "\ufeff" + GOOD,
            "a comment after a quoted value": GOOD.replace("'issuetype = Story'", "'issuetype = Story'  # stories"),
        }
        for what, text in wrong.items():
            with self.subTest(what):
                self.assertNotEqual(text, GOOD)
                with self.assertRaises(run_query.Refused):
                    run_query.load_config(self.config(text))

    def test_the_words_of_a_refusal_do_not_carry_unseen_characters_from_the_file(self):
        with self.assertRaises(run_query.Refused) as caught:
            run_query.load_config(self.config(GOOD + "bad\x1b[2Jkey: 1\n"))
        self.assertNotIn("\x1b", str(caught.exception))

    def test_a_file_that_is_not_there_is_refused_and_jira_is_not_asked(self):
        code, text = self.run_query(config=os.path.join(self.folder, "missing.yaml"))
        self.assertEqual(code, 1)
        self.assertIn("Nothing was asked of Jira", text)


class ChangingAQueryNeedsNoCodeChange(Case):
    def test_an_edited_filter_changes_what_is_asked_and_what_comes_back(self):
        with open(os.path.join(SKILL, "run_query.py"), "rb") as f:
            code_before = f.read()
        path = self.config(GOOD)
        code, first = self.run_query(config=path)
        self.assertEqual(code, 0)
        self.assertEqual(self.result()["saved"], 28)
        self.config(GOOD.replace("issuetype = Story", "issuetype = Bug"))
        code, second = self.run_query(config=path)
        self.assertEqual(code, 0)
        self.assertIn('(issuetype = Bug)', second)
        self.assertEqual(self.result()["saved"], 4)
        self.assertEqual(set(i["issuetype"] for i in self.result()["items"]), {"Bug"})
        with open(os.path.join(SKILL, "run_query.py"), "rb") as f:
            self.assertEqual(f.read(), code_before)

    def test_a_query_added_to_the_file_can_be_run(self):
        path = self.config(GOOD + "  - name: tasks-to-do\n    purpose: 'Tasks nobody has started yet.'\n    filter: 'issuetype = Task AND status = \"To Do\"'\n")
        code, text = self.run_query(query="tasks-to-do", config=path)
        self.assertEqual(code, 0, text)
        self.assertTrue(all(i["issuetype"] == "Task" and i["status"] == "To Do" for i in self.result()["items"]))
        self.assertGreater(self.result()["saved"], 0)

    def test_the_page_size_is_a_setting(self):
        for size, pages in ((10, 3), (5, 6), (28, 1), (100, 1), (1, 28)):
            with self.subTest(size):
                code, _ = self.run_query(config=self.config(GOOD.replace("page_size: 10", "page_size: %d" % size)))
                self.assertEqual(code, 0)
                self.assertEqual((self.result()["pages"], self.result()["saved"]), (pages, 28))

    def test_no_query_text_is_in_the_code(self):
        with open(os.path.join(SKILL, "run_query.py"), encoding="utf-8") as f:
            code = f.read().split('"""', 2)[2]
        for filter_text in [q["filter"] for q in run_query.load_config(CONFIG)["queries"]]:
            self.assertNotIn(filter_text, code)
        self.assertNotIn("issuetype =", code)


class ACompleteRun(Case):
    def test_three_pages_every_item_once_and_both_numbers_stated(self):
        code, text = self.run_query()
        self.assertEqual(code, 0, text)
        result = self.result()
        self.assertEqual([i["key"] for i in result["items"]], self.stories())
        self.assertEqual((result["pages"], result["saved"], result["total_jira_stated"], result["complete"]), (3, 28, 28, True))
        self.assertIn("Total Jira stated:  28", text)
        self.assertIn("Items saved locally: 28", text)
        self.assertIn("Pages answered:     3", text)
        self.assertIn("RESULT: COMPLETE", text)
        self.assertEqual(os.listdir(self.results), ["result.json"], "a temporary file was left behind")

    def test_each_page_is_asked_for_with_the_marker_the_page_before_gave(self):
        fake, asked = self.fake(), []
        real = fake.get

        def get(path, params=None):
            answer = real(path, params)
            asked.append((params.get("nextPageToken"), answer[2].get("nextPageToken")))
            return answer
        fake.get = get
        code, _, _ = self.direct(fake)
        self.assertEqual(code, 0)
        self.assertEqual(asked[0][0], None)
        self.assertEqual([a[0] for a in asked[1:]], [a[1] for a in asked[:-1]])
        self.assertEqual(asked[-1][1], None)

    def test_it_does_not_stop_at_a_short_page(self):
        """Jira may send fewer than were asked for on any page. Only Jira's word ends the pages."""
        fake = self.fake()
        real = fake.get
        fake.get = lambda path, params=None: real(path, dict(params, maxResults=3))
        code, text, _ = self.direct(fake)
        self.assertEqual(code, 0, text)
        self.assertEqual((self.result()["pages"], self.result()["saved"]), (10, 28))

    def test_a_query_that_matches_nothing_reports_zero_and_is_not_an_error(self):
        code, text = self.run_query(query="stories-with-no-such-label")
        self.assertEqual(code, 0, text)
        self.assertEqual((self.result()["saved"], self.result()["total_jira_stated"], self.result()["items"]), (0, 0, []))
        self.assertIn("Total Jira stated:  0", text)
        self.assertIn("Items saved locally: 0", text)
        self.assertIn("RESULT: COMPLETE. The query matches nothing", text)
        self.assertNotIn("REFUSED", text)
        self.assertNotIn("INCOMPLETE", text)

    def test_every_saved_query_runs_against_the_made_up_project(self):
        for query in run_query.load_config(CONFIG)["queries"]:
            with self.subTest(query["name"]):
                extra = ["--set", "since=2026-11-15"] if query["parameters"] else []
                code, text = self.run_query(query=query["name"], extra=extra)
                self.assertEqual(code, 0, text)

    def test_titles_are_never_asked_for_or_saved(self):
        fake = self.fake()
        code, text, _ = self.direct(fake)
        self.assertEqual(code, 0)
        self.assertTrue(fake.fields_asked)
        for fields in fake.fields_asked:
            self.assertEqual(sorted(fields), ["issuetype", "status", "updated"])
        with open(self.out, encoding="utf-8") as f:
            saved = f.read()
        self.assertNotIn("Made-up item", saved + text)
        self.assertEqual(sorted(self.result()["items"][0]), ["id", "issuetype", "key", "status", "status_category", "updated"])

    def test_times_are_saved_in_utc_and_names_are_cleaned(self):
        self.assertEqual(run_query.in_utc("2026-11-20T10:00:00.000+0100"), "2026-11-20T09:00:00Z")
        self.assertIsNone(run_query.in_utc("yesterday"))
        fake = self.fake()
        fake.issues[0]["status"] = "To Do<script>‮"
        fake.issues[0]["issuetype"] = "Story"
        code, _, _ = self.direct(fake, query="all-items")
        self.assertEqual(code, 0)
        self.assertEqual(self.result()["items"][0]["status"], "To Do?script??")

    def test_a_complete_run_replaces_an_older_result(self):
        self.run_query(query="stories-with-no-such-label")
        self.assertEqual(self.result()["saved"], 0)
        self.run_query()
        self.assertEqual(self.result()["saved"], 28)


class AnIncompleteRun(Case):
    def test_each_way_the_pages_can_go_wrong_leaves_nothing_that_looks_like_a_result(self):
        faults = ["fail_page=1", "fail_page=2", "fail_page=3", "unreachable_page=1", "unreachable_page=2", "unreachable_page=3",
                  "early_last=1", "early_last=2", "drop_on_page=1", "drop_on_page=3", "repeat_on_page=2", "repeat_on_page=3",
                  "empty_more=1", "empty_more=2", "token_loop=2", "other_project=1", "other_project=3", "no_count", "count_moves=1", "count_moves=-1"]
        for fault in faults:
            with self.subTest(fault):
                code, text = self.run_query(faults=[fault])
                self.assertEqual(code, 2, text)
                self.assert_nothing_left(text)

    def test_a_page_that_fails_partway_reports_the_shortfall(self):
        code, text = self.run_query(faults=["fail_page=3"])
        self.assertEqual(code, 2)
        self.assertIn("Total Jira stated:  28", text)
        self.assertIn("Items received:     20", text)
        self.assertIn("NOT SAVED", text)
        self.assertIn("Pages answered:     2", text)
        self.assertIn("page 3: Jira did not answer with a page of items (status 500)", text)
        self.assertIn("SHORTFALL: Jira stated 28 and 20 arrived. 8 did not.", text)
        self.assert_nothing_left(text)

    def test_the_scenario_a_first_page_that_says_it_is_the_last(self):
        """Fifty reported, one hundred and twenty there. Here: ten arrive and Jira's page says that is all. 28 are there."""
        code, text = self.run_query(faults=["early_last=1"])
        self.assertEqual(code, 2)
        self.assertIn("MISMATCH: Jira stated 28 and 10 arrived, 18 short", text)
        self.assertIn("SHORTFALL: Jira stated 28 and 10 arrived. 18 did not.", text)
        self.assert_nothing_left(text)

    def test_an_item_left_out_of_a_page_is_a_mismatch(self):
        code, text = self.run_query(faults=["drop_on_page=2"])
        self.assertEqual(code, 2)
        self.assertIn("MISMATCH: Jira stated 28 and 27 arrived, 1 short", text)

    def test_the_right_number_of_wrong_items_is_caught(self):
        """One item twice and another missing: 28 arrive and Jira states 28. The count alone would pass this."""
        fake = self.fake(repeat_on_page=2)
        raw, token = [], None
        while True:      # what a tool that only counted would have collected
            _, _, body = fake.get(fake_jira.SEARCH_PATH, dict({"jql": 'project = "DEMO" AND (issuetype = Story) ORDER BY key ASC', "fields": "status", "maxResults": 10},
                                                              **({"nextPageToken": token} if token else {})))
            raw += [i["key"] for i in body["issues"]]
            token = body.get("nextPageToken")
            if not token:
                break
        self.assertEqual(len(raw), 28, "the fault is meant to give the right NUMBER")
        self.assertEqual(len(set(raw)), 27)
        code, text = self.run_query(faults=["repeat_on_page=2"])
        self.assertEqual(code, 2)
        self.assertIn("came a second time", text)
        self.assert_nothing_left(text)

    def test_a_count_that_moves_during_the_run_is_said_to_be_that(self):
        code, text = self.run_query(faults=["count_moves=2"])
        self.assertEqual(code, 2)
        self.assertIn("changed while the pages were being read, from 28 to 30", text)
        self.assertNotIn("MISMATCH", text)

    def test_no_total_from_jira_means_no_result(self):
        code, text = self.run_query(faults=["no_count"])
        self.assertEqual(code, 2)
        self.assertIn("Total Jira stated:  not stated", text)
        for bad in (True, "28", -1, 28.0, None):
            with self.subTest(repr(bad)):
                fake = self.fake()
                fake.post = lambda path, body, bad=bad: (200, {}, {"count": bad})
                code, text, _ = self.direct(fake)
                self.assertEqual(code, 2)
                self.assert_nothing_left(text)

    def test_jira_saying_there_is_more_with_no_marker_is_not_an_end(self):
        fake = self.fake()
        real = fake.get

        def get(path, params=None):
            status, headers, body = real(path, params)
            if "nextPageToken" in body:
                del body["nextPageToken"]            # isLast: false stays
            return status, headers, body
        fake.get = get
        code, text, _ = self.direct(fake)
        self.assertEqual(code, 2)
        self.assertIn("did not say this was the last page, and gave no way to ask for another", text)
        self.assert_nothing_left(text)

    def test_answers_that_are_not_pages_are_not_pages(self):
        for what, body in (("a list", []), ("no issues", {"isLast": True}), ("issues that is not a list", {"issues": "none", "isLast": True}),
                           ("an item with no key", {"issues": [{"id": "1", "fields": {}}], "isLast": True}),
                           ("an item with no fields", {"issues": [{"id": "1", "key": "DEMO-1"}], "isLast": True}),
                           ("a marker that is a number", {"issues": [{"id": "1", "key": "DEMO-1", "fields": {}}], "nextPageToken": 7})):
            with self.subTest(what):
                fake = self.fake()
                fake.get = lambda path, params=None, body=body: (200, {}, body)
                code, text, _ = self.direct(fake)
                self.assertEqual(code, 2, text)
                self.assert_nothing_left(text)

    def test_there_is_a_limit_to_the_pages(self):
        with mock.patch.object(run_query, "MAX_PAGES", 2):
            code, text = self.run_query()
        self.assertEqual(code, 2)
        self.assertIn("stopped after 2 pages", text)
        self.assert_nothing_left(text)

    def test_an_older_result_is_left_as_it_was_and_called_older(self):
        self.run_query()
        with open(self.out, "rb") as f:
            older = f.read()
        code, text = self.run_query(faults=["fail_page=2"])
        self.assertEqual(code, 2)
        with open(self.out, "rb") as f:
            self.assertEqual(f.read(), older)
        self.assertEqual(os.listdir(self.results), ["result.json"])
        self.assertIn("IT IS NOT THIS RUN'S RESULT", text)
        self.assertIn("RESULT: INCOMPLETE", text)
        self.assertNotIn("RESULT: COMPLETE", text)

    def test_a_result_that_cannot_be_written_is_not_called_complete(self):
        with mock.patch.object(run_query, "write_result", side_effect=OSError("disk full")):
            code, text = self.run_query()
        self.assertEqual(code, 2)
        self.assert_nothing_left(text)

    def test_a_write_that_fails_halfway_leaves_no_temporary_file(self):
        with mock.patch.object(run_query.os, "replace", side_effect=OSError("no")):
            code, text = self.run_query()
        self.assertEqual(code, 2)
        self.assert_nothing_left(text)


class WhatIsRefusedBeforeJiraIsAsked(Case):
    def refused(self, fake_calls=0, **kwargs):
        with mock.patch.object(fake_jira.FakeJira, "get", side_effect=AssertionError("Jira was asked")), \
                mock.patch.object(fake_jira.FakeJira, "post", side_effect=AssertionError("Jira was asked")):
            code, text = self.run_query(**kwargs)
        self.assertEqual(code, 1, text)
        self.assertIn("REFUSED", text)
        self.assertIn("Nothing was asked of Jira", text)
        self.assertEqual(os.listdir(self.results), [])
        return text

    def test_a_project_that_is_not_allowed(self):
        self.refused(project="OTHER")
        self.refused(project='DEMO" OR project = "OTHER')

    def test_a_query_that_is_not_in_the_file(self):
        self.refused(query="everything")

    def test_a_date_that_is_not_a_date(self):
        for value in ("2026-02-30", "yesterday", "2026-11-1", '2026-11-01" OR project = "OTHER', "2026-11-01 ", "", "٢٠٢٦-١١-٠١"):
            with self.subTest(value):
                self.refused(query="stories-updated-since", extra=["--set", "since=" + value])

    def test_a_parameter_missing_extra_or_given_twice(self):
        self.refused(query="stories-updated-since")
        self.refused(query="all-stories", extra=["--set", "since=2026-11-01"])
        self.refused(query="stories-updated-since", extra=["--set", "since=2026-11-01", "--set", "until=2026-11-02"])
        self.refused(query="stories-updated-since", extra=["--set", "since=2026-11-01", "--set", "since=2026-11-02"])
        self.refused(query="stories-updated-since", extra=["--set", "since"])

    def test_a_good_date_is_put_in_quoted(self):
        code, text = self.run_query(query="stories-updated-since", extra=["--set", "since=2026-11-15"])
        self.assertEqual(code, 0, text)
        self.assertIn('The query as sent: project = "DEMO" AND (issuetype = Story AND updated >= "2026-11-15") ORDER BY key ASC', text)
        self.assertEqual(self.result()["saved"], 10)
        self.assertTrue(all(i["updated"] >= "2026-11-15" for i in self.result()["items"]))

    def test_the_query_sent_always_keeps_to_the_project(self):
        config = run_query.load_config(CONFIG)
        for query in config["queries"]:
            given = {name: "2026-11-01" for name in query["parameters"]}
            jql = run_query.build_jql(query, "DEMO", given)
            self.assertTrue(jql.startswith('project = "DEMO" AND (') and jql.endswith(") ORDER BY key ASC"), jql)

    def test_the_made_up_jiras_switches_are_refused_for_a_real_one(self):
        base = ["run", "--config", CONFIG, "--query", "all-stories", "--project", "DEMO", "--source", "live", "--out", self.out]
        with mock.patch.dict(os.environ, TheRequestsOfALiveRun.ENV), \
                mock.patch.object(run_query, "make_live", side_effect=AssertionError("a connection was made")):
            for extra in (["--fixture", FIXTURE], ["--fault", "fail_page=1"]):
                code, text = self.main(*(base + extra))
                self.assertEqual(code, 1)
                self.assertIn("for the made-up Jira only", text)

    def test_a_live_run_without_the_environment_variables_is_refused(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            code, text = self.main("run", "--config", CONFIG, "--query", "all-stories", "--project", "DEMO", "--source", "live", "--out", self.out)
        self.assertEqual(code, 1)
        self.assertIn("JIRA_BASE_URL is not set", text)


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
    """Stands where the network would be for a live connection. It answers from the made-up Jira and keeps each request."""

    def __init__(self, fake):
        self.fake, self.requests = fake, []

    def open(self, request, timeout=None):
        import urllib.parse
        self.requests.append(request)
        url = urllib.parse.urlparse(request.full_url)
        if request.get_method() == "GET":
            _, _, body = self.fake.get(url.path, dict(urllib.parse.parse_qsl(url.query)))
        else:
            _, _, body = self.fake.post(url.path, json.loads(request.data.decode("utf-8")))
        return Response(body)


class TheRequestsOfALiveRun(Case):
    ENV = {"JIRA_BASE_URL": "https://real.example.invalid", "JIRA_EMAIL": "someone@example.invalid", "JIRA_API_TOKEN": MADE_UP}

    def live(self, opener):
        del run_query.LINES[:]
        with mock.patch.dict(os.environ, self.ENV):
            conn, secrets = run_query.make_live(opener)
        args = argparse.Namespace(query="all-stories", project="DEMO", out=self.out, set=None)
        code = run_query.cmd_run(args, run_query.load_config(CONFIG), conn, live=True)
        return code, "\n".join(run_query.LINES), conn, secrets

    def test_only_the_two_requests_are_built_and_each_is_read_back(self):
        opener = Opener(self.fake())
        code, text, conn, secrets = self.live(opener)
        self.assertEqual(code, 0, text)
        self.assertEqual(sorted(set((r.get_method(), r.full_url.split("?")[0]) for r in opener.requests)),
                         [("GET", "https://real.example.invalid/rest/api/3/search/jql"), ("POST", "https://real.example.invalid/rest/api/3/search/approximate-count")])
        self.assertEqual(len(opener.requests), 5)
        for request in opener.requests:
            if request.get_method() == "POST":
                self.assertEqual(sorted(json.loads(request.data.decode("utf-8"))), ["jql"])
            else:
                self.assertIsNone(request.data)
        self.assertEqual(sorted(set(m for m, _, _ in conn.sent)), ["GET", "POST"])
        self.assertIn("Each was one of the two this tool can build", text)
        for secret in secrets:
            self.assertNotIn(secret, text)
        self.assertNotIn("real.example.invalid", text)
        self.assertEqual(self.result()["source"], "live")

    def test_the_connection_refuses_to_build_anything_else(self):
        with mock.patch.dict(os.environ, self.ENV):
            conn, _ = run_query.make_live(Opener(self.fake()))
        with self.assertRaises(run_query.Refused):
            conn._get("/rest/api/3/issue/DEMO-1", {})
        with self.assertRaises(run_query.Refused):
            conn._post("/rest/api/3/issue", {"jql": "x"})
        with self.assertRaises(run_query.Refused):
            conn._post(run_query.COUNT_PATH, {"jql": "x", "fields": {}})
        self.assertFalse(hasattr(conn, "put") or hasattr(conn, "delete") or hasattr(conn, "post") or hasattr(conn, "get"))

    def test_a_request_that_is_not_one_of_the_two_is_not_called_one(self):
        conn = run_query.Connection(None, None, "x")
        conn.sent = [("GET", run_query.SEARCH_PATH, None), ("POST", run_query.COUNT_PATH, None)]
        self.assertTrue(conn.only_the_two_reads())
        for other in (("POST", run_query.SEARCH_PATH, None), ("GET", run_query.COUNT_PATH, None), ("DELETE", run_query.SEARCH_PATH, None), ("?", run_query.SEARCH_PATH, None)):
            conn.sent = [other]
            self.assertFalse(conn.only_the_two_reads(), other)

    def test_a_base_address_with_a_path_or_without_https_is_refused(self):
        for base in ("http://real.example.invalid", "https://real.example.invalid/jira", "https://user@real.example.invalid", "https://real.example.invalid:8443"):
            with self.subTest(base), mock.patch.dict(os.environ, dict(self.ENV, JIRA_BASE_URL=base)):
                with self.assertRaises(run_query.Refused):
                    run_query.make_live(Opener(self.fake()))

    def test_a_credential_in_the_output_stops_the_output(self):
        with mock.patch.dict(os.environ, self.ENV), mock.patch.object(run_query, "make_live", return_value=(run_query.Connection(None, None, "x"), [MADE_UP])), \
                mock.patch.object(run_query, "cmd_run", side_effect=lambda *a, **k: run_query.say("leaked " + MADE_UP) or 0):
            code, text = self.main("run", "--config", CONFIG, "--query", "all-stories", "--project", "DEMO", "--source", "live", "--out", self.out)
        self.assertEqual(code, 1)
        self.assertNotIn(MADE_UP, text)
        self.assertIn("STOPPED", text)

    def test_the_saved_output_has_the_sites_address_taken_out(self):
        log = os.path.join(self.folder, "log.txt")
        with mock.patch.dict(os.environ, self.ENV), mock.patch.object(run_query, "make_live", return_value=(run_query.Connection(None, None, "real.example.invalid"), [])), \
                mock.patch.object(run_query, "cmd_run", side_effect=lambda *a, **k: run_query.say("see https://real.example.invalid/browse and real.example.invalid") or 0):
            self.main("run", "--config", CONFIG, "--query", "all-stories", "--project", "DEMO", "--source", "live", "--out", self.out, "--log", log)
        with open(log, encoding="utf-8") as f:
            saved = f.read()
        self.assertNotIn("real.example.invalid", saved)
        self.assertEqual(saved.count(run_query.SITE_MARK), 2)


class TheMadeUpJiraItself(Case):
    """The made-up Jira is a model. These check the model does what its own description says, and no more than that."""

    def test_it_answers_400_for_a_query_it_cannot_read(self):
        fake = self.fake()
        self.assertEqual(fake.post(fake_jira.COUNT_PATH, {"jql": "assignee = currentUser()"})[0], 400)
        self.assertEqual(fake.get(fake_jira.SEARCH_PATH, {"jql": 'project = "DEMO" AND (reporter = me) ORDER BY key ASC'})[0], 400)

    def test_a_query_it_cannot_read_gives_no_result(self):
        path = self.config(GOOD.replace("issuetype = Story", "assignee = currentUser()"))
        code, text = self.run_query(config=path)
        self.assertEqual(code, 2)
        self.assertIn("could not read the query (status 400)", text)
        self.assert_nothing_left(text)

    def test_another_project_has_no_items(self):
        fake = self.fake()
        self.assertEqual(fake.post(fake_jira.COUNT_PATH, {"jql": 'project = "OTHER" AND (issuetype = Story) ORDER BY key ASC'})[2], {"count": 0})

    def test_the_fixture_is_what_the_tests_assume(self):
        with open(FIXTURE, encoding="utf-8") as f:
            issues = json.load(f)["issues"]
        self.assertEqual(len(issues), 40)
        self.assertEqual(len(set(i["id"] for i in issues)), 40)
        self.assertEqual(len(self.stories()), 28)


class WhatTheReadersFound(Case):
    """Each of these is something an independent reader found in the first version, or showed the tests would miss."""

    def scripted(self, pages, counts):
        """A made-up Jira that gives these page bodies in order and these counts in order, whatever it is asked."""
        fake = self.fake()
        pages, counts = list(pages), list(counts)
        fake.get = lambda path, params=None: (200, {}, pages.pop(0))
        fake.post = lambda path, body: (200, {}, {"count": counts.pop(0)})
        return fake

    def item(self, n, key=None, **fields):
        base = {"issuetype": {"name": "Story"}, "status": {"name": "To Do", "statusCategory": {"key": "new"}}, "updated": "2026-11-20T10:00:00.000+0000"}
        base.update(fields)
        return {"id": str(100 + n), "key": key or "DEMO-%d" % n, "fields": base}

    def test_more_arriving_than_jira_stated_is_a_mismatch_too(self):
        fake = self.fake()
        fake.post = lambda path, body: (200, {}, {"count": 27})
        code, text, _ = self.direct(fake)
        self.assertEqual(code, 2)
        self.assertIn("MISMATCH: Jira stated 27 and 28 arrived, 1 over", text)
        self.assertNotIn("SHORTFALL", text)
        self.assert_nothing_left(text)

    def test_a_failure_on_a_query_that_matches_nothing_is_not_zero(self):
        """Zero stated and zero arrived looks like a complete, empty answer. A page that failed must not pass for one."""
        for fault in ("fail_page=1", "unreachable_page=1", "empty_more=1"):
            with self.subTest(fault):
                code, text = self.run_query(query="stories-with-no-such-label", faults=[fault])
                self.assertEqual(code, 2, text)
                self.assert_nothing_left(text)

    def test_a_count_of_true_is_not_one(self):
        fake = self.scripted([{"issues": [self.item(1)], "isLast": True}], [True, True])
        code, text, _ = self.direct(fake)
        self.assertEqual(code, 2, text)
        self.assert_nothing_left(text)

    def test_an_empty_page_that_says_there_is_more_fails_even_when_nothing_is_skipped(self):
        fake = self.scripted([{"issues": [self.item(1)], "nextPageToken": "a", "isLast": False}, {"issues": [], "nextPageToken": "b", "isLast": False},
                              {"issues": [self.item(2)], "isLast": True}], [2, 2])
        code, text, _ = self.direct(fake)
        self.assertEqual(code, 2, text)
        self.assertIn("empty page", text)

    def test_the_same_marker_given_back_fails_even_when_the_items_differ(self):
        fake = self.scripted([{"issues": [self.item(1)], "nextPageToken": "a", "isLast": False}, {"issues": [self.item(2)], "nextPageToken": "a", "isLast": False},
                              {"issues": [self.item(3)], "isLast": True}], [3, 3])
        code, text, _ = self.direct(fake)
        self.assertEqual(code, 2, text)
        self.assertIn("same marker", text)

    def test_a_status_that_is_not_200_is_not_a_page_or_a_count_whatever_its_body(self):
        fake = self.fake()
        real = fake.get
        fake.get = lambda path, params=None: (500,) + real(path, params)[1:]
        code, text, _ = self.direct(fake)
        self.assertEqual(code, 2)
        self.assert_nothing_left(text)
        fake = self.fake()
        real_post = fake.post
        fake.post = lambda path, body: (503,) + real_post(path, body)[1:]
        code, text, _ = self.direct(fake)
        self.assertEqual(code, 2)
        self.assertIn("did not state a total", text)

    def test_a_failure_in_the_middle_of_a_page_counts_only_the_pages_before_it(self):
        pages = [{"issues": [self.item(1), self.item(2), self.item(3)], "nextPageToken": "a", "isLast": False},
                 {"issues": [self.item(4), self.item(5), {"id": "x", "key": "DEMO-6", "fields": {}}], "isLast": True}]
        code, text, _ = self.direct(self.scripted(pages, [10, 10]))
        self.assertEqual(code, 2)
        self.assertIn("Before it, 1 page and 3 items had arrived", text)
        self.assertIn("Items received:     3", text)
        self.assertIn("SHORTFALL: Jira stated 10 and 3 arrived. 7 did not.", text)

    def test_a_moved_count_is_not_also_called_a_shortfall(self):
        code, text, _ = self.direct(self.scripted([{"issues": [self.item(n) for n in range(1, 5)], "isLast": True}], [5, 4]))
        self.assertEqual(code, 2)
        self.assertIn("changed while the pages were being read, from 5 to 4", text)
        self.assertNotIn("SHORTFALL", text)

    def test_two_items_with_one_key_are_one_item_twice(self):
        pages = [{"issues": [self.item(1), self.item(2, key="demo-1")], "isLast": True}]
        code, text, _ = self.direct(self.scripted(pages, [2, 2]))
        self.assertEqual(code, 2)
        self.assertIn("came a second time", text)
        self.assert_nothing_left(text)

    def test_an_item_missing_what_was_asked_for_is_not_saved_as_blanks(self):
        for what, item in (("no fields at all", {"id": "101", "key": "DEMO-1", "fields": {}}),
                           ("a time that cannot be read", self.item(1, updated="last Tuesday")),
                           ("a time out of range", self.item(1, updated="0001-01-01T00:00:00.000+1400")),
                           ("no status name", self.item(1, status={"statusCategory": {"key": "new"}})),
                           ("an id that is not a number", dict(self.item(1), id="ten")),
                           ("an id that is a number and not text", dict(self.item(1), id=101))):
            with self.subTest(what):
                code, text, _ = self.direct(self.scripted([{"issues": [item], "isLast": True}], [1, 1]))
                self.assertEqual(code, 2, text)
                self.assert_nothing_left(text)

    def test_names_in_other_scripts_are_kept_and_changed_names_are_counted(self):
        pages = [{"issues": [self.item(1, status={"name": "Terminé & livré: QA", "statusCategory": {"key": "done"}}, issuetype={"name": "故事"}), self.item(2)], "isLast": True}]
        code, text, _ = self.direct(self.scripted(pages, [2, 2]))
        self.assertEqual(code, 0, text)
        first = self.result()["items"][0]
        self.assertEqual((first["issuetype"], first["status"]), ("故事", "Terminé ? livré? QA"))
        self.assertNotIn("cleaned", first)
        self.assertIn("In 1 of them a status or type name had characters replaced", text)

    def test_is_last_must_be_true_or_absent_when_there_is_no_marker(self):
        for value in ("false", 0, None, "true", False):
            with self.subTest(repr(value)):
                code, text, _ = self.direct(self.scripted([{"issues": [self.item(1)], "isLast": value}], [1, 1]))
                self.assertEqual(code, 2, text)
        code, text, _ = self.direct(self.scripted([{"issues": [self.item(1)]}], [1, 1]))
        self.assertEqual(code, 0, text)

    def test_complete_says_what_it_does_not_mean(self):
        """One item leaves the query and another joins: the counts agree and the set is wrong. No check here can see it."""
        code, text = self.run_query()
        self.assertEqual(code, 0)
        self.assertIn("It does not mean nothing changed in Jira during the run", text)

    def test_the_log_and_the_result_cannot_be_the_same_file(self):
        for faults in ([], ["fail_page=2"]):
            with self.subTest(faults):
                code, text = self.run_query(faults=faults, extra=["--log", self.out])
                self.assertEqual(code, 1, text)
                self.assertIn("--log and --out name the same file", text)
                self.assertEqual(os.listdir(self.results), [])
        code, text = self.run_query(extra=["--log", os.path.join(self.results, ".", "result.json")])
        self.assertEqual(code, 1)

    def test_a_file_name_with_a_line_break_cannot_forge_a_result_line(self):
        self.out = os.path.join(self.results, "x\nRESULT: INCOMPLETE. forged.json")
        code, text = self.run_query()
        self.assertEqual(code, 0)
        self.assertEqual(sum(1 for line in text.split("\n") if line.startswith("RESULT:")), 1)

    def test_something_unforeseen_is_incomplete_and_not_a_crash(self):
        with mock.patch.object(run_query, "fetch_pages", side_effect=RuntimeError("unforeseen")):
            code, text = self.run_query()
        self.assertEqual(code, 2)
        self.assertIn("did not foresee (RuntimeError)", text)
        self.assertEqual(os.listdir(self.results), [])


class Failing:
    """Stands where the network would be, and answers as a real server does when it refuses: by raising."""

    def __init__(self, fake, status, on, body=b"{}"):
        self.inner, self.status, self.on, self.body, self.seen = Opener(fake), status, on, body, 0
        self.requests = self.inner.requests

    def open(self, request, timeout=None):
        import urllib.error
        self.seen += 1
        if self.seen == self.on:
            self.requests.append(request)
            raise urllib.error.HTTPError(request.full_url, self.status, "made up", {}, io.BytesIO(self.body))
        return self.inner.open(request, timeout)


class ALiveRunThatGoesWrong(TheRequestsOfALiveRun):
    def test_a_real_servers_refusals_are_incomplete_runs_and_not_crashes(self):
        for status in (401, 403, 404, 429, 500, 502, 302):
            for on in (1, 2, 3, 4, 5):          # the count before, each of three pages, the count after
                with self.subTest(status=status, on=on):
                    code, text, conn, _ = self.live(Failing(self.fake(), status, on))
                    self.assertEqual(code, 2, text)
                    self.assert_nothing_left(text)
                    self.assertTrue(conn.only_the_two_reads())

    def test_rejected_credentials_are_named(self):
        code, text, _, _ = self.live(Failing(self.fake(), 401, 1))
        self.assertIn("rejected the credentials (401)", text)

    def test_an_answer_that_is_not_json_is_not_a_page(self):
        class NotJson(Opener):
            def open(self, request, timeout=None):
                response = Opener.open(self, request, timeout)
                if request.get_method() == "GET":
                    response._body = b"<html>Sign in</html>"
                return response
        code, text, _, _ = self.live(NotJson(self.fake()))
        self.assertEqual(code, 2)
        self.assert_nothing_left(text)

    def test_a_connection_that_drops_is_an_incomplete_run(self):
        class Dropping(Opener):
            def open(self, request, timeout=None):
                if len(self.requests) == 2:
                    self.requests.append(request)
                    raise TimeoutError("made up")
                return Opener.open(self, request, timeout)
        code, text, _, _ = self.live(Dropping(self.fake()))
        self.assertEqual(code, 2)
        self.assertIn("could not be reached", text)
        self.assert_nothing_left(text)

    def test_every_request_carries_the_sign_in_and_all_three_forms_are_searched_for(self):
        import base64
        opener = Opener(self.fake())
        _, _, _, secrets = self.live(opener)
        encoded = base64.b64encode(("%s:%s" % (self.ENV["JIRA_EMAIL"], self.ENV["JIRA_API_TOKEN"])).encode()).decode()
        self.assertEqual(sorted(secrets), sorted([self.ENV["JIRA_API_TOKEN"], self.ENV["JIRA_EMAIL"], encoded]))
        for request in opener.requests:
            self.assertEqual(request.get_header("Authorization"), "Basic " + encoded)

    def test_a_redirect_is_not_followed(self):
        import urllib.request
        captured = {}
        real_build = urllib.request.build_opener

        def build(*handlers):
            captured["handlers"] = handlers
            return real_build(*handlers)
        with mock.patch.dict(os.environ, self.ENV), mock.patch.object(run_query.urllib.request, "build_opener", side_effect=build):
            run_query.make_live()
        self.assertEqual(len(captured["handlers"]), 1)
        handler = captured["handlers"][0]()
        self.assertIsNone(handler.redirect_request(None, None, 302, "Found", {}, "https://elsewhere.example.invalid/"))

    def test_a_base_address_in_capitals_is_the_same_site(self):
        opener = Opener(self.fake())
        with mock.patch.dict(os.environ, dict(self.ENV, JIRA_BASE_URL="https://Real.Example.invalid")):
            conn, _ = run_query.make_live(opener)
        conn.count("x")
        self.assertTrue(opener.requests[0].full_url.startswith("https://real.example.invalid/"))

    def test_a_query_that_names_the_runners_own_email_writes_no_result(self):
        """The email is one of the things searched for. The result must not be written before that search."""
        del run_query.LINES[:]
        path = self.config(GOOD.replace("issuetype = Story", 'issuetype = Story AND labels = "%s"' % self.ENV["JIRA_EMAIL"]))
        fake = self.fake()
        fake.post = lambda p, body: (200, {}, {"count": 0})
        fake.get = lambda p, params=None: (200, {}, {"issues": [], "isLast": True})
        with mock.patch.dict(os.environ, self.ENV):
            conn, secrets = run_query.make_live(Opener(fake))
        args = argparse.Namespace(query="all-stories", project="DEMO", out=self.out, set=None, log=None)
        code = run_query.cmd_run(args, run_query.load_config(path), conn, live=True, secrets=secrets)
        self.assertEqual(code, 2)
        self.assertEqual(os.listdir(self.results), [])


if __name__ == "__main__":
    unittest.main()
