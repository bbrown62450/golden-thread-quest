"""Tests for hierarchy.py, against the made-up Jira. No network. Every item here is made up."""
import argparse
import contextlib
import io
import json
import os
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
import hierarchy    # noqa: E402

MADE_UP = "-".join(["made", "up", "value", "used", "only", "in", "tests"])      # stands where an API token would be


def item(number, key, kind="Story", parent=None, level=0, estimate=None, parent_key=None):
    return {"id": str(number), "key": key, "type": kind, "level": level, "subtask": level == -1, "parent_id": None if parent is None else str(parent),
            "parent_key": parent_key, "estimate_seconds": estimate}


class Case(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix="gtq-hierarchy-test-")
        self.out = os.path.join(self.folder, "out")
        self.state = os.path.join(self.folder, "jira")
        os.makedirs(self.out)
        os.makedirs(self.state)
        self.fake_path = os.path.join(self.state, "fake-jira.json")
        fake_jira.FakeJira(fake_jira.fresh()).save(self.fake_path)

    def tearDown(self):
        shutil.rmtree(self.folder, ignore_errors=True)

    # ---------------------------------------------------------- helpers

    def main(self, *argv):
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed), contextlib.redirect_stderr(printed):
            try:
                code = hierarchy.main(list(argv))
            except SystemExit as stop:
                code = stop.code
        return code, printed.getvalue()

    def build(self, extra=(), name="tree"):
        return self.main("build", "--source", "fake", "--project", "DEMO", "--out-dir", self.out, "--name", name, "--state", self.state, *extra)

    @contextlib.contextmanager
    def jira(self):
        fake = fake_jira.FakeJira.open(self.fake_path)
        yield fake
        fake.save(self.fake_path)

    def faults(self, **faults):
        with self.jira() as jira:
            jira.data["faults"] = faults
            jira.data["asked"] = 0

    def records(self, name="tree"):
        with open(os.path.join(self.out, name + ".json"), encoding="utf-8") as f:
            return json.load(f)

    def page(self, name="tree"):
        with open(os.path.join(self.out, name + ".md"), encoding="utf-8") as f:
            return f.read()

    def by_key(self):
        return {i["key"]: i for i in self.records()["items"]}

    def files(self):
        state = {}
        for name in sorted(os.listdir(self.out)):
            path = os.path.join(self.out, name)
            with open(path, "rb") as f:
                state[name] = (f.read(), os.stat(path).st_mtime_ns, os.stat(path).st_ino)
        return state

    def tree_of(self, items):
        return hierarchy.build_tree(items)

    def save_records(self, items, links=(), name="hand.json"):
        path = os.path.join(self.folder, name)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"format": hierarchy.FORMAT, "project": "DEMO", "source": "fake", "site_fingerprint": None, "items": items, "links": list(links)}, f)
        return path

    def refused_and_nothing_written(self, code, text, before=None):
        self.assertEqual(code, 1, text)
        self.assertIn("REFUSED", text)
        self.assertNotIn("RESULT:", text)
        self.assertEqual(self.files(), before if before is not None else {})


class TypeAndParentByIdentifier(Case):
    def test_each_item_has_its_type_and_its_parents_number_as_jira_gave_them(self):
        code, text = self.build()
        self.assertEqual(code, 0, text)
        fresh = {i["key"]: i for i in fake_jira.fresh()["issues"]}
        got = self.by_key()
        self.assertEqual(sorted(got), sorted(fresh))
        for key, made in fresh.items():
            self.assertEqual(got[key]["id"], made["id"])
            self.assertEqual(got[key]["type"], made["type"])
            self.assertEqual(got[key]["parent_id"], made["parent"]["id"] if made["parent"] else None)
            self.assertEqual(got[key]["parent_key"], made["parent"]["key"] if made["parent"] else None)

    def test_the_index_has_a_row_for_every_item_with_identifier_type_and_parent_identifier(self):
        self.build()
        index = self.page()[self.page().index("## Index"):self.page().index("## The tree")]
        rows = [line.split(" | ") for line in index.split("\n") if line.startswith("| 3")]
        self.assertEqual(len(rows), 11)
        fresh = {i["id"]: i for i in fake_jira.fresh()["issues"]}
        for row in rows:           # every row, against the made-up Jira, not two of them
            made = fresh[row[0].strip("| ")]
            self.assertEqual((row[1], row[2], row[3]), (made["key"], "`%s`" % made["type"], made["parent"]["id"] if made["parent"] else "none"))
        self.assertIn("| 30007 | DEMO-7 | `Subtask` | 30002 | DEMO-2 | yes | 2 h | nothing beneath |", self.page())
        self.assertIn("| 30001 | DEMO-1 | `Epic` | none | none | no parent | no estimate | 25 h (2 of the 8 without an estimate) |", self.page())

    def test_all_four_kinds_are_there_and_a_missing_one_is_named(self):
        _, text = self.build()
        self.assertIn("Of epic, story, task and subtask: all four are here.", text)
        with self.jira() as jira:
            jira.data["issues"] = [i for i in jira.data["issues"] if i["type"] not in ("Epic", "Task")]
            jira.data["links"] = []
            for issue in jira.data["issues"]:
                if issue["parent"] and issue["parent"]["key"] in ("DEMO-1", "DEMO-4"):
                    issue["parent"] = None
        _, text = self.build(name="fewer")
        self.assertIn("here are story, subtask; NOT here: epic, task", text)

    def test_the_four_kinds_are_known_by_jiras_mark_or_by_name(self):
        kinds = hierarchy.kinds_present([item(1, "D-1", "Initiative", level=1), item(2, "D-2", "story"), item(3, "D-3", "TASK"), item(4, "D-4", "Sub-task", level=None)])
        self.assertEqual(kinds, ["epic", "story", "task", "subtask"])
        self.assertEqual(hierarchy.kinds_present([item(1, "D-1", "Bug"), item(2, "D-2", "Unterauftrag", level=-1)]), ["subtask"])

    def test_no_title_is_asked_for_or_kept(self):
        code, text = self.build()
        with self.jira() as jira:
            asked = jira.data["fields_asked"]
        self.assertTrue(asked)
        for fields in asked:
            self.assertEqual(sorted(fields), ["issuelinks", "issuetype", "parent", "timeoriginalestimate"])
        everything = json.dumps(self.records()) + self.page() + text
        self.assertNotIn("Made-up title", everything)
        self.assertNotIn("summary", json.dumps(self.records()))


class BuiltFromIdentifiers(Case):
    def test_the_tree_does_not_look_at_keys_or_at_the_parents_key(self):
        self.build()
        items = self.records()["items"]
        tree = self.tree_of(items)
        scrambled = [dict(i, key="X-%d" % (900 - n), parent_key="WRONG-1") for n, i in enumerate(items)]
        again = self.tree_of(scrambled)
        self.assertEqual((tree["children"], tree["roots"], tree["unresolved"], tree["total"]), (again["children"], again["roots"], again["unresolved"], again["total"]))

    def test_the_children_of_each_item_are_those_whose_parent_number_is_its_number(self):
        self.build()
        tree = self.tree_of(self.records()["items"])
        self.assertEqual(tree["children"]["30001"], ["30002", "30003", "30004"])
        self.assertEqual(tree["children"]["30002"], ["30006", "30007"])
        self.assertEqual(tree["roots"], ["30001", "30005", "30011"])

    def test_an_item_given_a_new_key_keeps_its_children(self):
        self.build()
        with self.jira() as jira:
            jira.rekey("DEMO-2", "DEMO-200")
        code, text = self.build()
        self.assertEqual(code, 0, text)
        self.assertIn("NEW KEY: the item with the number 30002 had the key DEMO-2 and now has DEMO-200. It is the same item.", text)
        self.assertIn("1 with a new key, 0 new, 0 no longer returned", text)
        tree = self.tree_of(self.records()["items"])
        self.assertEqual(tree["children"]["30002"], ["30006", "30007"])
        self.assertEqual(self.by_key()["DEMO-6"]["parent_key"], "DEMO-200")

    def test_two_items_with_the_same_type_and_estimate_are_two_items(self):
        tree = self.tree_of([item(1, "D-1", "Epic", level=1), item(2, "D-2", parent=1, estimate=3600), item(3, "D-3", parent=1, estimate=3600)])
        self.assertEqual(tree["children"]["1"], ["2", "3"])
        self.assertEqual(tree["total"]["1"], (7200, 1, 3))


class AParentThatWasNotRetrieved(Case):
    def test_the_item_is_kept_and_listed_as_an_unresolved_link(self):
        code, text = self.build()
        self.assertEqual(self.by_key()["DEMO-10"]["parent_id"], "40003")
        tree = self.tree_of(self.records()["items"])
        self.assertEqual(tree["unresolved"], {"40003": ["30010"]})
        self.assertNotIn("30010", tree["roots"])
        self.assertIn("UNRESOLVED LINKS: 1.", text)
        self.assertIn("DEMO-10 [30010] names the parent number 40003 (OTHER-3), which is not among the items read. The item is kept", text)
        page = self.page()
        self.assertIn("| 30010 | DEMO-10 | `Story` | 40003 | OTHER-3 | **NO: unresolved link** |", page)
        section = page[page.index("## Unresolved links"):page.index("## Links that are not parent links")]
        self.assertIn("| 30010 | DEMO-10 | `Story` | 40003 | OTHER-3 |", section)
        self.assertIn("PARENT NOT RETRIEVED: number 40003 (Jira names it OTHER-3)", page)

    def test_it_is_not_shown_as_an_item_with_no_parent(self):
        self.build()
        lines = hierarchy.tree_lines(self.records()["items"], self.tree_of(self.records()["items"]))
        at = [n for n, line in enumerate(lines) if "DEMO-10" in line][0]
        self.assertTrue(lines[at].startswith("  DEMO-10"), "it is set in under the line that names the missing parent")
        self.assertTrue(lines[at - 1].startswith("PARENT NOT RETRIEVED"))

    def test_when_a_parent_stops_being_returned_its_children_are_kept_as_unresolved(self):
        self.build()
        with self.jira() as jira:
            jira.data["issues"] = [i for i in jira.data["issues"] if i["key"] != "DEMO-1"]
        code, text = self.build()
        self.assertEqual(code, 0, text)
        self.assertEqual(len(self.records()["items"]), 10)
        self.assertIn("UNRESOLVED LINKS: 4.", text)
        self.assertIn("NO LONGER RETURNED BY JIRA, and so not in this build: DEMO-1 [30001].", text)
        tree = self.tree_of(self.records()["items"])
        self.assertEqual(tree["unresolved"]["30001"], ["30002", "30003", "30004"])
        self.assertEqual(tree["children"]["30002"], ["30006", "30007"], "what is under them stays under them")

    def test_none_says_none(self):
        with self.jira() as jira:
            jira.find("DEMO-10")["parent"] = None
        _, text = self.build()
        self.assertIn("UNRESOLVED LINKS: 0.", text)
        self.assertIn("None. Every parent named is among the items read.", self.page())


class AMovedItem(Case):
    def move(self):
        self.build()
        self.before = self.tree_of(self.records()["items"])
        with self.jira() as jira:
            jira.move("DEMO-7", "DEMO-3")
        return self.build()

    def test_it_is_under_its_new_parent_and_not_under_the_old(self):
        code, text = self.move()
        self.assertEqual(code, 0, text)
        tree = self.tree_of(self.records()["items"])
        self.assertEqual(tree["children"]["30002"], ["30006"])
        self.assertEqual(tree["children"]["30003"], ["30007", "30008"])
        self.assertEqual(self.by_key()["DEMO-7"]["parent_id"], "30003")
        lines = hierarchy.tree_lines(self.records()["items"], tree)
        self.assertEqual(sum(1 for line in lines if "DEMO-7 " in line), 1, "it is in the tree once")
        self.assertEqual(self.page().count("| 30007 | DEMO-7 |"), 1)

    def test_it_is_matched_by_its_number_and_the_move_is_printed(self):
        _, text = self.move()
        self.assertIn("COMPARED WITH THE RECORDS ON DISK, by number: 1 moved, 0 with a new key, 0 new, 0 no longer returned, 0 of another type.", text)
        self.assertIn("MOVED: DEMO-7 [30007] was under DEMO-2 [30002], and is now under DEMO-3 [30003].", text)

    def test_its_estimate_is_counted_once_the_scenario(self):
        self.move()
        after = self.tree_of(self.records()["items"])
        self.assertEqual(self.before["total"]["30002"][0] - after["total"]["30002"][0], 2 * 3600)
        self.assertEqual(after["total"]["30003"][0] - self.before["total"]["30003"][0], 2 * 3600)
        self.assertEqual(after["total"]["30001"][0], self.before["total"]["30001"][0], "the epic's total is what it was: nothing is counted twice")

    def test_moved_and_given_a_new_key_at_once_is_still_the_same_item(self):
        self.build()
        with self.jira() as jira:
            jira.move("DEMO-7", "DEMO-3")
            jira.rekey("DEMO-7", "DEMO-70")
        _, text = self.build()
        self.assertIn("MOVED: DEMO-70 [30007] was under DEMO-2 [30002], and is now under DEMO-3 [30003].", text)
        self.assertIn("NEW KEY: the item with the number 30007 had the key DEMO-7 and now has DEMO-70.", text)
        self.assertIn("0 new, 0 no longer returned", text)

    def test_moved_to_no_parent_and_moved_under_a_parent_not_retrieved(self):
        self.build()
        with self.jira() as jira:
            jira.find("DEMO-7")["parent"] = None
            jira.find("DEMO-8")["parent"] = {"id": "40003", "key": "OTHER-3"}
        _, text = self.build()
        self.assertIn("MOVED: DEMO-7 [30007] was under DEMO-2 [30002], and is now under no parent.", text)
        self.assertIn("MOVED: DEMO-8 [30008] was under DEMO-3 [30003], and is now under OTHER-3 [40003].", text)
        self.assertEqual(self.tree_of(self.records()["items"])["unresolved"]["40003"], ["30008", "30010"])

    def test_a_new_item_an_item_gone_and_a_change_of_type_are_printed(self):
        self.build()
        with self.jira() as jira:
            jira.data["issues"] = [i for i in jira.data["issues"] if i["key"] != "DEMO-11"]
            jira.data["links"] = [link for link in jira.data["links"] if "DEMO-11" not in (link["from"], link["to"])]
            jira.data["issues"].append({"key": "DEMO-12", "id": "30012", "type": "Task", "parent": None, "estimate": None, "summary": "Made-up title"})
            jira.find("DEMO-5")["type"] = "Story"
        _, text = self.build()
        self.assertIn("NEW: DEMO-12 [30012].", text)
        self.assertIn("NO LONGER RETURNED BY JIRA, and so not in this build: DEMO-11 [30011].", text)
        self.assertIn("TYPE: DEMO-5 [30005] was a Task and is now a Story.", text)


class ALoopOrASelfParentIsRejected(Case):
    def rejected(self, code, text, before):
        self.assertEqual(code, 2, text)
        self.assertIn("REJECTED: these items do not make a tree.", text)
        self.assertIn("Nothing was written.", text)
        self.assertNotIn("RESULT:", text)
        self.assertEqual(self.files(), before)

    def test_an_item_that_is_its_own_parent(self):
        with self.jira() as jira:
            jira.break_it("self")
        code, text = self.build()
        self.rejected(code, text, {})
        self.assertIn("DEMO-5 [30005] is its own parent.", text)

    def test_a_loop_of_three_names_every_item_in_it(self):
        with self.jira() as jira:
            jira.break_it("loop")
        code, text = self.build()
        self.rejected(code, text, {})
        self.assertIn("a loop: DEMO-1 [30001], which is under DEMO-6 [30006], which is under DEMO-2 [30002], which is under DEMO-1 [30001].", text)
        self.assertEqual(text.count("a loop:"), 1, "the loop is named once, though it is met from every item in and under it")

    def test_an_older_build_is_left_as_it_was_and_called_older(self):
        self.build()
        before = self.files()
        with self.jira() as jira:
            jira.break_it("loop")
        code, text = self.build()
        self.rejected(code, text, before)
        self.assertIn("THEY ARE NOT THIS BUILD'S", text)

    def test_loops_of_every_size_and_two_at_once(self):
        with self.assertRaises(hierarchy.Rejected) as caught:
            self.tree_of([item(1, "D-1", parent=2), item(2, "D-2", parent=1), item(3, "D-3", parent=4), item(4, "D-4", parent=5), item(5, "D-5", parent=3),
                          item(6, "D-6", parent=1), item(7, "D-7", parent=7), item(8, "D-8")])
        reasons = caught.exception.reasons
        self.assertEqual(reasons, ["D-7 [7] is its own parent",
                                   "a loop: D-1 [1], which is under D-2 [2], which is under D-1 [1]",
                                   "a loop: D-3 [3], which is under D-4 [4], which is under D-5 [5], which is under D-3 [3]"])

    def test_a_loop_met_from_outside_it_is_written_the_same_way_starting_at_its_lowest_number(self):
        with self.assertRaises(hierarchy.Rejected) as caught:
            self.tree_of([item(1, "D-1", parent=5), item(3, "D-3", parent=4), item(4, "D-4", parent=5), item(5, "D-5", parent=3)])
        self.assertEqual(caught.exception.reasons, ["a loop: D-3 [3], which is under D-4 [4], which is under D-5 [5], which is under D-3 [3]"])

    def test_a_long_chain_with_no_loop_is_a_tree(self):
        chain = [item(1, "D-1")] + [item(n, "D-%d" % n, parent=n - 1) for n in range(2, 60)]
        tree = self.tree_of(chain)
        self.assertEqual(tree["total"]["1"][2], 59)

    def test_a_number_or_a_key_held_by_two_items(self):
        for items, said in (([item(1, "D-1"), item(1, "D-2")], "the number 1 is held by 2 items"), ([item(1, "D-1"), item(2, "D-1")], "the key D-1 is held by 2 items")):
            with self.assertRaises(hierarchy.Rejected) as caught:
                self.tree_of(items)
            self.assertIn(said, caught.exception.reasons)

    def test_the_tree_command_rejects_them_too_from_a_records_file(self):
        for items, said in (([item(1, "D-1", parent=1)], "is its own parent"), ([item(1, "D-1", parent=2), item(2, "D-2", parent=1)], "a loop:")):
            code, text = self.main("tree", "--records", self.save_records(items))
            self.assertEqual(code, 2, text)
            self.assertIn(said, text)
            self.assertNotIn("RESULT:", text)


class TheSameAcrossTwoRuns(Case):
    def test_a_second_build_writes_nothing_and_the_files_are_byte_for_byte_the_same(self):
        _, first = self.build()
        before = self.files()
        code, second = self.build()
        self.assertEqual(self.files(), before)
        self.assertIn("The files are the same as before: nothing was written.", second)
        self.assertEqual(second.count("not written: byte for byte the same"), 2)
        checksum = [line for line in first.split("\n") if line.startswith("Checksum of the tree")]
        self.assertEqual(checksum, [line for line in second.split("\n") if line.startswith("Checksum of the tree")])
        self.assertEqual(len(checksum), 1)

    def test_the_order_jira_sends_the_items_in_does_not_matter(self):
        self.build(name="one")
        for size in (2, 3, 100):
            with mock.patch.object(hierarchy, "PAGE", size):
                self.build(name="one")
        real = fake_jira.FakeJira.get

        def backwards(fake, path, params=None):
            status, headers, body = real(fake, path, params)
            body["issues"] = list(reversed(body["issues"]))
            for issue in body["issues"]:
                issue["fields"]["issuelinks"] = list(reversed(issue["fields"].get("issuelinks", [])))
            return status, headers, body
        with mock.patch.object(fake_jira.FakeJira, "get", backwards):
            self.build(name="two")
        for ending in (".json", ".md"):
            with open(os.path.join(self.out, "one" + ending), encoding="utf-8") as a, open(os.path.join(self.out, "two" + ending), encoding="utf-8") as b:
                self.assertEqual(a.read().replace("one.", "X."), b.read().replace("two.", "X."))

    def test_the_tree_command_gives_the_same_output_twice_and_the_builds_checksum(self):
        _, built = self.build()
        path = os.path.join(self.out, "tree.json")
        first, second = self.main("tree", "--records", path), self.main("tree", "--records", path)
        self.assertEqual(first, second)
        self.assertEqual(first[0], 0)
        self.assertEqual([line for line in first[1].split("\n") if line.startswith("Checksum of the tree")], [line for line in built.split("\n") if line.startswith("Checksum of the tree")])
        self.assertEqual(sorted(os.listdir(self.out)), ["tree.json", "tree.md"])

    def test_no_time_is_written_into_either_file(self):
        self.build()
        self.assertNotRegex(json.dumps(self.records()) + self.page(), r"20[0-9]{2}-[0-9]{2}-[0-9]{2}")

    def test_the_page_is_put_right_from_the_records_if_it_was_changed(self):
        self.build()
        good = self.page()
        with open(os.path.join(self.out, "tree.md"), "w", encoding="utf-8") as f:
            f.write("scribbled over")
        self.build()
        self.assertEqual(self.page(), good)


class NothingIsWrittenUnlessTheWholeProjectWasRead(Case):
    def test_pages_are_all_read(self):
        with mock.patch.object(hierarchy, "PAGE", 3):
            code, text = self.build()
        self.assertEqual(code, 0, text)
        self.assertEqual(len(self.records()["items"]), 11)
        self.assertIn("read twice, 4 pages each time", text)
        self.assertIn("/rest/api/3/search/jql  x8", text)

    def test_a_page_that_fails_in_either_reading(self):
        self.build()
        before = self.files()
        for n in (1, 2, 4, 5, 8):
            with self.subTest(n):
                self.faults(fail_page=n)
                with mock.patch.object(hierarchy, "PAGE", 3):
                    code, text = self.build()
                self.refused_and_nothing_written(code, text, before)

    def test_an_item_that_comes_twice(self):
        self.faults(repeat_on_page=2)
        with mock.patch.object(hierarchy, "PAGE", 3):
            code, text = self.build()
        self.refused_and_nothing_written(code, text)
        self.assertIn("came twice", text)

    def test_one_reading_that_stops_early(self):
        self.faults(early_last=1)
        with mock.patch.object(hierarchy, "PAGE", 3):
            code, text = self.build()
        self.refused_and_nothing_written(code, text)
        self.assertIn("the two readings differ", text)

    def test_both_readings_stopping_early_the_same_way_is_caught_by_jiras_count(self):
        """Three items read twice, the same three. Their children would all be unresolved links, and nothing would say why."""
        self.faults(always_early=True)
        with mock.patch.object(hierarchy, "PAGE", 3):
            code, text = self.build()
        self.refused_and_nothing_written(code, text)
        self.assertIn("Jira says the project has 11 items (11 when asked again) and 3 were read", text)

    def test_an_item_moved_between_the_two_readings(self):
        self.faults(change_after=1)
        code, text = self.build()
        self.refused_and_nothing_written(code, text)
        self.assertIn("something was changed in Jira while it was being read", text)

    def test_no_count_or_a_count_that_is_not_a_number(self):
        self.faults(no_count=True)
        code, text = self.build()
        self.refused_and_nothing_written(code, text)
        for bad in (True, "11", -1, None, 11.0):
            with self.subTest(repr(bad)), mock.patch.object(fake_jira.FakeJira, "post", lambda fake, path, body, bad=bad: (200, {}, {"count": bad})):
                code, text = self.build()
                self.refused_and_nothing_written(code, text)

    def test_a_count_that_differs_before_or_after(self):
        for answers in ([10, 11], [11, 12], [12, 12]):
            with self.subTest(answers), mock.patch.object(fake_jira.FakeJira, "post", lambda fake, path, body, answers=list(answers): (200, {}, {"count": answers.pop(0)})):
                code, text = self.build()
                self.refused_and_nothing_written(code, text)

    def test_a_status_that_is_not_200_whatever_its_body(self):
        real = fake_jira.FakeJira.get
        with mock.patch.object(fake_jira.FakeJira, "get", lambda fake, path, params=None: (503,) + real(fake, path, params)[1:]):
            code, text = self.build()
        self.refused_and_nothing_written(code, text)
        real_post = fake_jira.FakeJira.post
        with mock.patch.object(fake_jira.FakeJira, "post", lambda fake, path, body: (500,) + real_post(fake, path, body)[1:]):
            code, text = self.build()
        self.refused_and_nothing_written(code, text)

    def test_jira_that_cannot_be_reached(self):
        with mock.patch.object(fake_jira.FakeJira, "get", side_effect=OSError("made up")):
            code, text = self.build()
        self.refused_and_nothing_written(code, text)
        self.assertIn("could not be reached", text)

    def test_items_that_cannot_be_read_are_not_guessed_at(self):
        real = fake_jira.FakeJira.get
        spoilers = {
            "a parent with no number": lambda i: i["fields"].update(parent={"key": "DEMO-1"}),
            "a parent that is a word": lambda i: i["fields"].update(parent="DEMO-1"),
            "a parent whose number is not digits": lambda i: i["fields"].update(parent={"id": "abc", "key": "DEMO-1"}),
            "no type": lambda i: i["fields"].pop("issuetype"),
            "an estimate in words": lambda i: i["fields"].update(timeoriginalestimate="two days"),
            "an estimate below zero": lambda i: i["fields"].update(timeoriginalestimate=-5),
            "an estimate of true": lambda i: i["fields"].update(timeoriginalestimate=True),
            "a number that is not digits": lambda i: i.update(id="x1"),
            "a key of another project": lambda i: i.update(key="OTHER-7"),
            "no fields": lambda i: i.pop("fields"),
            "a link with no other item": lambda i: i["fields"].update(issuelinks=[{"id": "1", "type": {"name": "Blocks"}}]),
            "a link with no number": lambda i: i["fields"].update(issuelinks=[{"type": {"name": "Blocks"}, "outwardIssue": {"id": "1"}}]),
        }
        for what, spoil in spoilers.items():
            with self.subTest(what):
                def get(fake, path, params=None, spoil=spoil):
                    status, headers, body = real(fake, path, params)
                    spoil(body["issues"][1])
                    return status, headers, body
                with mock.patch.object(fake_jira.FakeJira, "get", get):
                    code, text = self.build()
                self.refused_and_nothing_written(code, text)

    def test_an_item_of_another_project_with_no_links_and_no_children(self):
        real = fake_jira.FakeJira.get

        def get(fake, path, params=None):
            status, headers, body = real(fake, path, params)
            for issue in body["issues"]:
                if issue["key"] == "DEMO-9":
                    issue["key"] = "OTHER-77"
            return status, headers, body
        with mock.patch.object(fake_jira.FakeJira, "get", get):
            code, text = self.build()
        self.refused_and_nothing_written(code, text)
        self.assertIn("an item of another project (OTHER)", text)

    def test_answers_that_are_not_pages(self):
        for what, body in (("a list", []), ("no issues", {"isLast": True}), ("a marker that is a number", {"issues": [], "nextPageToken": 7}),
                           ("an empty page that says there is more", {"issues": [], "nextPageToken": "x", "isLast": False}), ("isLast that is a word", {"issues": [], "isLast": "false"})):
            with self.subTest(what), mock.patch.object(fake_jira.FakeJira, "get", lambda fake, path, params=None, body=body: (200, {}, body)):
                code, text = self.build()
                self.refused_and_nothing_written(code, text)

    def test_a_last_page_that_does_not_say_it_is_the_last_with_every_item_there(self):
        """Every item arrives and the count agrees. Jira still has not said the pages ended."""
        real = fake_jira.FakeJira.get
        for value in ("false", "no", 0, False):
            def get(fake, path, params=None, value=value):
                status, headers, body = real(fake, path, params)
                body["isLast"] = value
                return status, headers, body
            with self.subTest(repr(value)), mock.patch.object(fake_jira.FakeJira, "get", get):
                code, text = self.build()
                self.refused_and_nothing_written(code, text)
                self.assertIn("did not say the last page was the last", text)

    def test_the_same_marker_given_back_and_too_many_pages(self):
        real = fake_jira.FakeJira.get

        def looping(fake, path, params=None):
            status, headers, body = real(fake, path, params)
            if params.get("nextPageToken"):
                body.update(nextPageToken=params["nextPageToken"], isLast=False)
            return status, headers, body
        with mock.patch.object(fake_jira.FakeJira, "get", looping), mock.patch.object(hierarchy, "PAGE", 3):
            code, text = self.build()
        self.refused_and_nothing_written(code, text)
        with mock.patch.object(hierarchy, "PAGE", 2), mock.patch.object(hierarchy, "MAX_PAGES", 3):
            code, text = self.build()
        self.refused_and_nothing_written(code, text)
        self.assertIn("more than this tool reads", text)


class Estimates(Case):
    def test_each_item_shows_its_own_and_the_total_of_all_beneath(self):
        self.build()
        total = self.tree_of(self.records()["items"])["total"]
        self.assertEqual(total["30001"], (25 * 3600, 2, 8))
        self.assertEqual(total["30002"], (13 * 3600, 0, 3))
        self.assertEqual(total["30004"], (3 * 3600, 1, 2))
        self.assertEqual(total["30009"], (0, 1, 1))
        self.assertIn("DEMO-1 [30001] Epic. Own estimate: no estimate; with all 7 beneath: 25 h (2 of the 8 without an estimate)", self.page())

    def test_no_estimate_is_not_zero(self):
        self.assertEqual((hierarchy.hours(None), hierarchy.hours(0), hierarchy.hours(1800), hierarchy.hours(5400)), ("no estimate", "0 h", "0.5 h", "1.5 h"))
        with self.jira() as jira:
            jira.find("DEMO-9")["estimate"] = 0
        self.build()
        self.assertIn("| 30009 | DEMO-9 | `Subtask` | 30004 | DEMO-4 | yes | 0 h | nothing beneath |", self.page())
        self.assertEqual(self.tree_of(self.records()["items"])["total"]["30004"], (3 * 3600, 0, 2))

    def test_a_total_of_nothing_is_not_shown_as_zero_hours(self):
        """Found on the real project: no item had an estimate, and the first version printed 0 h for each total."""
        with self.jira() as jira:
            for issue in jira.data["issues"]:
                issue["estimate"] = None
        _, text = self.build()
        self.assertNotIn("0 h", text + self.page())
        self.assertIn("with all 7 beneath: no estimate on any of the 8", text)
        self.assertIn("Under retrieved parents or under none: no estimate on any of the 10. Under parents not retrieved, added to no one: no estimate on any of the 1.", text)
        self.assertEqual(hierarchy.total_text(0, 2, 2), "no estimate on any of the 2")
        self.assertEqual(hierarchy.total_text(0, 1, 2), "0 h (1 of the 2 without an estimate)")

    def test_what_is_under_a_parent_not_retrieved_is_totalled_apart(self):
        _, text = self.build()
        self.assertIn("Under retrieved parents or under none: 28 h (2 of the 10 without an estimate). Under parents not retrieved, added to no one: 6 h.", text)
        with self.jira() as jira:           # a reader's find: one group with no estimates at all was printed as 0 h
            jira.find("DEMO-10")["estimate"] = None
        _, text = self.build()
        self.assertIn("Under parents not retrieved, added to no one: no estimate on any of the 1.", text)
        with self.jira() as jira:
            jira.find("DEMO-10")["parent"] = None
        _, text = self.build()
        self.assertIn("Under parents not retrieved, added to no one: no items.", text)


class LinksThatAreNotParentLinks(Case):
    def test_each_link_is_listed_once_though_jira_gives_it_at_both_ends(self):
        _, text = self.build()
        links = self.records()["links"]
        self.assertEqual([(l["id"], l["from_id"], l["phrase"], l["to_id"]) for l in links], [("50001", "30003", "blocks", "30005"), ("50002", "30002", "relates to", "30011"), ("50003", "30008", "blocks", "40009")])
        self.assertIn("LINKS THAT ARE NOT PARENT LINKS: 3. Not used to build the tree.", text)
        self.assertIn("| 50001 | DEMO-3 [30003] | `blocks` | DEMO-5 [30005] | yes |", self.page())
        self.assertIn("| 50003 | DEMO-8 [30008] | `blocks` | OTHER-9 [40009] | one end is outside what was read |", self.page())

    def test_the_direction_is_the_same_whichever_end_it_is_read_from(self):
        ends = fake_jira.FakeJira(fake_jira.fresh())
        _, from_source = hierarchy.one_item(ends.shaped(ends.find("DEMO-3"), hierarchy.FIELDS.split(",")), "DEMO")
        _, from_target = hierarchy.one_item(ends.shaped(ends.find("DEMO-5"), hierarchy.FIELDS.split(",")), "DEMO")
        self.assertEqual(from_source, from_target)
        self.assertEqual((from_source[0]["from_key"], from_source[0]["to_key"]), ("DEMO-3", "DEMO-5"))

    def test_a_link_does_not_change_the_tree(self):
        _, before = self.build()
        with self.jira() as jira:
            jira.data["links"].append({"id": "50009", "name": "Blocks", "outward": "blocks", "inward": "is blocked by", "from": "DEMO-9", "to": "DEMO-1"})
        _, after = self.build()
        line = lambda text: [l for l in text.split("\n") if l.startswith("Checksum of the tree")]       # noqa: E731
        self.assertEqual(line(before), line(after))
        self.assertEqual(len(self.records()["links"]), 4)
        self.assertEqual(self.by_key()["DEMO-9"]["parent_id"], "30004")


class OtherPeoplesText(Case):
    def test_a_type_name_with_markup_or_a_table_bar_is_cleaned(self):
        with self.jira() as jira:
            jira.find("DEMO-11")["type"] = "Bug | <b>x</b>‮\n## The tree"
        code, text = self.build()
        self.assertEqual(code, 0, text)
        self.assertEqual(self.by_key()["DEMO-11"]["type"], "Bug ? ?b?x??b????? The tree")
        self.assertEqual(sum(1 for line in self.page().split("\n") if line.startswith("## The tree")), 1)
        row = self.page().split("\n")[[n for n, l in enumerate(self.page().split("\n")) if l.startswith("| 30011")][0]]
        self.assertEqual(row.count("|"), 9)
        self.assertEqual(row.count("`"), 2)

    def test_a_subtask_for_which_jira_names_no_parent_is_pointed_out(self):
        """Found on the real project: a subtask came with no parent. It may have one that Jira did not send."""
        with self.jira() as jira:
            jira.find("DEMO-9")["parent"] = None
        code, text = self.build()
        self.assertEqual(code, 0, text)
        self.assertIn("DEMO-9 [30009] is a Subtask, and Jira names no parent for it.", text)
        self.assertIn("DEMO-9 [30009] is a Subtask, and Jira names no parent for it.", self.page())
        self.assertNotIn("DEMO-5 [30005] is a", text, "a task with no parent is ordinary")

    def test_a_parent_link_jira_does_not_usually_allow_is_kept_and_pointed_out(self):
        with self.jira() as jira:
            jira.move("DEMO-3", "DEMO-2")
        code, text = self.build()
        self.assertEqual(code, 0, text)
        self.assertIn("SHAPES JIRA DOES NOT USUALLY ALLOW, kept as given: 1.", text)
        self.assertIn("DEMO-3 [30003], a Story, is under DEMO-2 [30002], a Story", text)
        self.assertIn("## Shapes Jira does not usually allow", self.page())
        self.assertEqual(self.tree_of(self.records()["items"])["children"]["30002"], ["30003", "30006", "30007"])


class TheFilesOnDisk(Case):
    def test_records_changed_into_something_else_are_left_alone(self):
        self.build()
        path = os.path.join(self.out, "tree.json")
        good = self.records()
        for what, text in (("not JSON", "{"), ("another format", json.dumps(dict(good, format="x"))), ("an item with no number", json.dumps(dict(good, items=[{"key": "D-1", "type": "Story"}]))),
                           ("an empty file", "")):
            with self.subTest(what):
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text)
                code, out = self.build()
                self.assertEqual(code, 1, out)
                with open(path, encoding="utf-8") as f:
                    self.assertEqual(f.read(), text)
                code, out = self.main("tree", "--records", path)
                self.assertEqual(code, 1, out)

    def test_records_of_another_project_or_another_jira_are_not_written_over(self):
        self.build()
        path = os.path.join(self.out, "tree.json")
        for field, value in (("project", "OTHER"), ("source", "live"), ("site_fingerprint", "0123456789abcdef")):
            with self.subTest(field):
                changed = dict(self.records(), **{field: value})
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(changed, f)
                before = self.files()
                code, text = self.build()
                self.refused_and_nothing_written(code, text, before)
                with mock.patch.object(fake_jira.FakeJira, "get", side_effect=AssertionError("Jira was asked")):
                    self.build()
                os.unlink(path)
                self.build()

    def test_the_log_cannot_be_one_of_the_two_files_under_any_spelling_or_name(self):
        self.build()
        before = self.files()
        second_name = os.path.join(self.folder, "innocent.txt")
        os.link(os.path.join(self.out, "tree.md"), second_name)
        link = os.path.join(self.folder, "link.txt")
        os.symlink(os.path.join(self.out, "tree.json"), link)
        for log in (os.path.join(self.out, "tree.json"), os.path.join(self.out, "TREE.MD"), os.path.join(self.out, ".", "tree.md"), second_name, link):
            with self.subTest(log):
                code, text = self.build(extra=["--log", log])
                self.assertEqual(code, 1, text)
                self.assertIn("--log names one of the build's own files", text)
        os.unlink(second_name)
        self.assertEqual({k: v[0] for k, v in self.files().items()}, {k: v[0] for k, v in before.items()})

    def test_names_and_folders_that_are_not_allowed(self):
        for name in ("Tree", "../x", "a b", "", "x.json"):
            with self.subTest(name):
                code, text = self.build(name=name)
                self.assertEqual(code, 1, text)
        code, _ = self.main("build", "--source", "fake", "--project", "DEMO", "--out-dir", os.path.join(self.folder, "missing"), "--name", "tree", "--state", self.state)
        self.assertEqual(code, 1)
        code, _ = self.main("build", "--source", "fake", "--project", 'DEMO" OR project = "OTHER', "--out-dir", self.out, "--name", "tree", "--state", self.state)
        self.assertEqual(code, 1)
        self.assertEqual(os.listdir(self.out), [])

    def test_a_records_file_that_is_a_link_or_has_a_second_name_is_not_written_through(self):
        """The files linked to are ones this tool wrote, kept elsewhere, so that only the check for a link can refuse."""
        self.build(name="kept")
        elsewhere = os.path.join(self.folder, "elsewhere")
        os.makedirs(elsewhere)
        for ending in (".json", ".md"):
            os.rename(os.path.join(self.out, "kept" + ending), os.path.join(elsewhere, "kept" + ending))
        with self.jira() as jira:
            jira.move("DEMO-7", "DEMO-3")
        kept = {}
        for ending in (".json", ".md"):
            with open(os.path.join(elsewhere, "kept" + ending), "rb") as f:
                kept[ending] = f.read()
        os.symlink(os.path.join(elsewhere, "kept.json"), os.path.join(self.out, "tree.json"))
        code, text = self.build()
        self.assertEqual(code, 1, text)
        self.assertIn("is a link, a folder, or a file with a second name", text)
        os.unlink(os.path.join(self.out, "tree.json"))
        os.link(os.path.join(elsewhere, "kept.md"), os.path.join(self.out, "tree.md"))
        code, text = self.build()
        self.assertEqual(code, 1, text)
        self.assertIn("is a link, a folder, or a file with a second name", text)
        for ending in (".json", ".md"):
            with open(os.path.join(elsewhere, "kept" + ending), "rb") as f:
                self.assertEqual(f.read(), kept[ending])

    def test_a_write_that_fails_leaves_no_temporary_file_and_does_not_say_built(self):
        with mock.patch.object(hierarchy.os, "replace", side_effect=OSError("made up")):
            code, text = self.build()
        self.assertEqual(code, 1)
        self.assertNotIn("RESULT:", text)
        self.assertEqual(os.listdir(self.out), [])

    def test_something_unforeseen_is_a_refusal_and_not_a_crash(self):
        with mock.patch.object(hierarchy, "read_project", side_effect=RuntimeError("unforeseen")):
            code, text = self.build()
        self.assertEqual(code, 1)
        self.assertIn("did not foresee (RuntimeError)", text)

    def test_the_tree_command_with_no_file(self):
        code, text = self.main("tree", "--records", os.path.join(self.folder, "missing.json"))
        self.assertEqual(code, 1)
        self.assertIn("no records file", text)


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

    def __init__(self, fake, fail=None):
        self.fake, self.requests, self.fail = fake, [], fail

    def open(self, request, timeout=None):
        import urllib.error
        self.requests.append(request)
        if self.fail and len(self.requests) == self.fail[0]:
            raise urllib.error.HTTPError(request.full_url, self.fail[1], "made up", {}, io.BytesIO(b"{}"))
        url = urllib.parse.urlparse(request.full_url)
        if request.data is None:
            _, _, body = self.fake.get(url.path, dict(urllib.parse.parse_qsl(url.query)))
        else:
            _, _, body = self.fake.post(url.path, json.loads(request.data.decode("utf-8")))
        return Response(body)


class TheLiveCommandAsAPersonRunsIt(Case):
    """Through main(), with the network replaced where urllib builds its opener: the path a real run takes."""
    ENV = {"JIRA_BASE_URL": "https://real.example.invalid", "JIRA_EMAIL": "someone@example.invalid", "JIRA_API_TOKEN": MADE_UP}

    def run_live(self, env=None, extra=(), spoil=None, fail=None):
        fake = fake_jira.FakeJira.open(self.fake_path)
        if spoil:
            spoil(fake)
        self.opener, self.handlers = Opener(fake, fail), []

        def build(*handlers):
            self.handlers.append(handlers)
            return self.opener
        with mock.patch.dict(os.environ, env or self.ENV), mock.patch.object(hierarchy.urllib.request, "build_opener", build):
            return self.main("build", "--source", "live", "--project", "DEMO", "--out-dir", self.out, "--name", "real", *extra)

    def test_only_the_two_reads_are_sent_and_redirects_are_not_followed(self):
        code, text = self.run_live()
        self.assertEqual(code, 0, text)
        self.assertEqual(sorted(set((r.get_method(), urllib.parse.urlparse(r.full_url).path) for r in self.opener.requests)),
                         [("GET", "/rest/api/3/search/jql"), ("POST", "/rest/api/3/search/approximate-count")])
        self.assertEqual(len(self.opener.requests), 4)
        for request in self.opener.requests:
            self.assertTrue(request.get_header("Authorization").startswith("Basic "))
            self.assertTrue(request.full_url.startswith("https://real.example.invalid/"))
            if request.get_method() == "POST":
                self.assertEqual(sorted(json.loads(request.data.decode("utf-8"))), ["jql"])
            else:
                self.assertIsNone(request.data)
        self.assertEqual(self.handlers, [(hierarchy.NoRedirect,)])
        self.assertIsNone(hierarchy.NoRedirect().redirect_request(None, None, 302, "Found", {}, "https://elsewhere.example.invalid/"))
        self.assertIn("Each was one of the two this tool can build", text)
        self.assertEqual(self.records("real")["source"], "live")

    def test_no_credential_or_site_address_is_in_the_output_the_log_or_the_files(self):
        log = os.path.join(self.folder, "log.txt")
        code, text = self.run_live(extra=["--log", log])
        with open(log, encoding="utf-8") as f:
            everything = text + f.read() + json.dumps(self.records("real")) + self.page("real")
        import base64
        encoded = base64.b64encode(("someone@example.invalid:" + MADE_UP).encode()).decode()
        for secret in (MADE_UP, "someone@example.invalid", encoded, "real.example.invalid"):
            self.assertNotIn(secret, everything)
        self.assertIn(hierarchy.site_fingerprint("real.example.invalid"), everything)
        with mock.patch.dict(os.environ, self.ENV):
            _, secrets = hierarchy.make_live(Opener(None))
        self.assertEqual(sorted(secrets), sorted([MADE_UP, "someone@example.invalid", encoded]))

    def test_the_saved_output_has_the_sites_address_taken_out(self):
        log = os.path.join(self.folder, "log.txt")
        with mock.patch.dict(os.environ, self.ENV), mock.patch.object(hierarchy, "make_live", return_value=(hierarchy.Connection(None, None, "real.example.invalid"), [])), \
                mock.patch.object(hierarchy, "cmd_build", side_effect=lambda *a, **k: hierarchy.say("see https://real.example.invalid/browse and real.example.invalid") or 0):
            self.main("build", "--source", "live", "--project", "DEMO", "--out-dir", self.out, "--name", "real", "--log", log)
        with open(log, encoding="utf-8") as f:
            saved = f.read()
        self.assertNotIn("real.example.invalid", saved)
        self.assertEqual(saved.count(hierarchy.SITE_MARK), 2)

    def test_a_credential_in_any_output_stops_the_output_whatever_put_it_there(self):
        with mock.patch.dict(os.environ, self.ENV), mock.patch.object(hierarchy, "make_live", return_value=(hierarchy.Connection(None, None, "x"), [MADE_UP])), \
                mock.patch.object(hierarchy, "cmd_build", side_effect=lambda *a, **k: hierarchy.say("leaked " + MADE_UP) or 0):
            code, text = self.main("build", "--source", "live", "--project", "DEMO", "--out-dir", self.out, "--name", "real")
        self.assertEqual(code, 1)
        self.assertNotIn(MADE_UP, text)
        self.assertIn("STOPPED", text)

    def test_a_token_that_reaches_the_output_stops_the_output(self):
        def spoil(fake):
            fake.find("DEMO-11")["type"] = MADE_UP
        code, text = self.run_live(spoil=spoil)
        self.assertEqual(code, 1)
        self.assertIn("a credential was found", text)
        self.assertNotIn(MADE_UP, text)
        self.assertEqual(os.listdir(self.out), [], "a reader's find: the files were written before the search for credentials")

    def test_the_method_reported_is_the_one_the_request_was_built_with(self):
        class Lying(hierarchy.urllib.request.Request):
            def get_method(self):
                return "DELETE"
        with mock.patch.object(hierarchy.urllib.request, "Request", Lying):
            code, text = self.run_live()
        self.assertIn("NOT EVERY ONE COULD BE READ BACK", text)
        self.assertNotIn("Each was one of the two this tool can build", text)

    def test_the_connection_builds_nothing_else(self):
        with mock.patch.dict(os.environ, self.ENV):
            conn, _ = hierarchy.make_live(Opener(None))
        with self.assertRaises(hierarchy.Refused):
            conn._get("/rest/api/3/issue/DEMO-1", {})
        with self.assertRaises(hierarchy.Refused):
            conn._post("/rest/api/3/issue", {"jql": "x"})
        with self.assertRaises(hierarchy.Refused):
            conn._post(hierarchy.COUNT_PATH, {"jql": "x", "fields": {}})
        for sent in ([("POST", hierarchy.SEARCH_PATH)], [("GET", hierarchy.COUNT_PATH)], [("DELETE", hierarchy.SEARCH_PATH)], [("?", hierarchy.SEARCH_PATH)]):
            conn.sent = sent
            self.assertFalse(conn.only_the_two_reads(), sent)

    def test_a_base_address_that_is_not_https_and_the_sites_name_only(self):
        for base in ("http://real.example.invalid", "https://real.example.invalid:8443", "https://real.example.invalid/jira", "https://user@real.example.invalid"):
            with self.subTest(base):
                code, text = self.run_live(env=dict(self.ENV, JIRA_BASE_URL=base))
                self.assertEqual(code, 1, text)
                self.assertEqual(self.opener.requests, [])
        code, text = self.run_live(env=dict(self.ENV, JIRA_BASE_URL="https://Real.Example.invalid/"))
        self.assertEqual(code, 0, text)

    def test_a_real_servers_refusals_write_nothing(self):
        for status in (401, 403, 404, 429, 500, 302):
            for on in (1, 2, 3, 4):
                with self.subTest(status=status, on=on):
                    code, text = self.run_live(fail=(on, status))
                    self.assertEqual(code, 1, text)
                    self.assertEqual(os.listdir(self.out), [])
        _, text = self.run_live(fail=(1, 401))
        self.assertIn("rejected the credentials (401)", text)

    def test_the_made_up_jiras_folder_is_refused_for_a_real_one_and_no_variables_means_no_request(self):
        code, text = self.run_live(extra=["--state", self.state])
        self.assertEqual(code, 1)
        self.assertIn("for the made-up Jira only", text)
        self.assertEqual(self.opener.requests, [])
        with mock.patch.dict(os.environ, {}, clear=True):
            code, text = self.main("build", "--source", "live", "--project", "DEMO", "--out-dir", self.out, "--name", "real")
        self.assertEqual(code, 1)
        self.assertIn("JIRA_BASE_URL is not set", text)


class TheMadeUpJiraItself(Case):
    def test_the_hierarchy_tool_cannot_change_it(self):
        with open(self.fake_path, encoding="utf-8") as f:
            before = json.load(f)
        self.build()
        with open(self.fake_path, encoding="utf-8") as f:
            after = json.load(f)
        self.assertEqual((before["issues"], before["links"]), (after["issues"], after["links"]))

    def test_its_own_commands_change_it(self):
        self.build()
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            fake_jira.main(["move", "--state", self.state, "--key", "DEMO-7", "--under", "DEMO-3"])
            fake_jira.main(["rekey", "--state", self.state, "--key", "DEMO-5", "--to", "DEMO-50"])
        _, text = self.build()
        self.assertIn("1 moved, 1 with a new key", text)
        with contextlib.redirect_stdout(printed):
            fake_jira.main(["break", "--state", self.state, "--how", "loop"])
        self.assertEqual(self.build()[0], 2)


def nesting(lines):
    """{number: [numbers set in directly under it]}, read back from the printed tree by its indentation alone."""
    told, stack = {}, []
    for line in lines:
        if line.startswith("PARENT NOT RETRIEVED"):
            stack = [(-1, line.split("number ")[1].split(" ")[0])]
            continue
        depth, number = (len(line) - len(line.lstrip(" "))) // 2, line.split("[")[1].split("]")[0]
        if stack and stack[0][0] == -1 and depth == 0:
            stack = []
        stack = [s for s in stack if s[0] < depth]
        if stack:
            told.setdefault(stack[-1][1], []).append(number)
        stack.append((depth, number))
    return told


class WhatTheReadersFound(Case):
    """Each of these is something an independent reader found in the first version, or showed the tests would miss."""

    # ------------------------------------------------ the printed tree, and what it is built from

    def test_the_printed_tree_sets_each_item_in_under_its_parent(self):
        """The tests looked at the tree as the tool holds it. A tree printed flat would have passed them all."""
        self.build()
        items = self.records()["items"]
        tree = self.tree_of(items)
        told = nesting(hierarchy.tree_lines(items, tree))
        want = {parent: kids for parent, kids in tree["children"].items() if kids}
        want.update(tree["unresolved"])
        self.assertEqual(told, want)
        self.assertEqual(len(told), 5)

    def test_the_printed_tree_is_the_same_when_every_key_is_another_key(self):
        """Criterion 2, on what is printed: the nesting, read by the numbers, does not move when the keys do."""
        self.build()
        items = self.records()["items"]
        scrambled = [dict(i, key="ZZ-%d" % (500 - n), parent_key=None if i["parent_id"] is None else "QQ-1") for n, i in enumerate(items)]
        self.assertEqual(nesting(hierarchy.tree_lines(items, self.tree_of(items))), nesting(hierarchy.tree_lines(scrambled, self.tree_of(scrambled))))

    def test_children_are_in_the_order_of_their_numbers_not_of_their_text(self):
        tree = self.tree_of([item(1, "D-1"), item(100, "D-2", parent=1), item(9, "D-3", parent=1), item(10, "D-4", parent=1)])
        self.assertEqual(tree["children"]["1"], ["9", "10", "100"])
        code, text = self.main("tree", "--records", self.save_records([item(1, "D-1"), item(100, "D-2", parent=1), item(9, "D-3", parent=1), item(10, "D-4", parent=1)]))
        self.assertEqual(code, 0, text)
        text = text[text.index("THE TREE"):]          # the tool was right; the first version of this test read an earlier part of the output
        self.assertLess(text.index("D-3 [9]"), text.index("D-4 [10]"))
        self.assertLess(text.index("D-4 [10]"), text.index("D-2 [100]"))

    def test_a_new_key_on_a_parent_is_not_a_move_of_its_children(self):
        self.build()
        with self.jira() as jira:
            jira.rekey("DEMO-2", "DEMO-200")
        _, text = self.build()
        self.assertIn("by number: 0 moved, 1 with a new key", text)
        self.assertNotIn("MOVED:", text)

    def test_after_a_move_the_printed_tree_has_the_item_under_the_new_parent_only(self):
        self.build()
        with self.jira() as jira:
            jira.move("DEMO-7", "DEMO-3")
            jira.rekey("DEMO-7", "DEMO-70")
        self.build()
        told = nesting(hierarchy.tree_lines(self.records()["items"], self.tree_of(self.records()["items"])))
        self.assertEqual((told["30002"], told["30003"]), (["30006"], ["30007", "30008"]))

    def test_a_chain_far_deeper_than_any_real_project_is_still_a_tree(self):
        chain = [item(1, "D-1", estimate=3600)] + [item(n, "D-%d" % n, parent=n - 1, estimate=3600) for n in range(2, 3001)]
        tree = self.tree_of(chain)
        self.assertEqual(tree["total"]["1"], (3000 * 3600, 0, 3000))
        code, text = self.main("tree", "--records", self.save_records(chain))
        self.assertEqual(code, 0, text[:300])
        self.assertIn("RESULT: THE TREE WAS BUILT", text)

    def test_many_items_are_checked_in_a_time_that_does_not_square(self):
        import time
        items = [item(1, "D-1")] + [item(n, "D-%d" % n, parent=max(1, n // 2)) for n in range(2, 20001)]
        start = time.time()
        self.tree_of(items)
        self.assertLess(time.time() - start, 2.0)

    # ------------------------------------------------ numbers written another way

    def test_a_number_with_a_leading_zero_is_not_another_number_and_is_refused(self):
        real = fake_jira.FakeJira.get
        for spoil in (lambda i: i.update(id="030002"), lambda i: i["fields"].update(parent={"id": "030001", "key": "DEMO-1"})):
            def get(fake, path, params=None, spoil=spoil):
                status, headers, body = real(fake, path, params)
                spoil(body["issues"][1])
                return status, headers, body
            with mock.patch.object(fake_jira.FakeJira, "get", get):
                code, text = self.build()
            self.refused_and_nothing_written(code, text)
        for items in ([item(7, "D-7")] + [dict(item(8, "D-8"), parent_id="07")], [dict(item(7, "D-7"), id="07")], [dict(item(7, "D-7"), parent_id=7)], [dict(item(7, "D-7"), id="７")]):
            code, text = self.main("tree", "--records", self.save_records(items))
            self.assertEqual(code, 1, text)

    def test_hours_are_written_as_plain_numbers_however_large(self):
        self.assertEqual([hierarchy.hours(s) for s in (360001800, 10 ** 9, 36, 3600 * 1000000)], ["100000.5 h", "277777.78 h", "0.01 h", "1000000 h"])

    # ------------------------------------------------ a records file that is not what the tool writes

    def test_records_with_text_that_could_forge_a_line_are_refused_by_tree_and_by_build(self):
        good = [item(1, "D-1", "Epic", level=1), item(2, "D-2", parent=1, parent_key="D-1")]
        bad = {
            "a key with a line break and a forged result": [dict(good[0], key="D-1\nRESULT: BUILT. 99 items\x1b[2J"), good[1]],
            "a key in small letters": [dict(good[0], key="d-1"), good[1]],
            "a type with a table bar and a fence": [dict(good[0], type="T|x\n~~~"), good[1]],
            "a parent key that is not a key": [good[0], dict(good[1], parent_key="someone@example.invalid")],
            "a parent key that is a list": [good[0], dict(good[1], parent_key=["D-1"])],
            "a parent key with no parent number": [dict(good[0], parent_key="D-9"), good[1]],
            "no estimate field": [{k: v for k, v in good[0].items() if k != "estimate_seconds"}, good[1]],
            "an estimate below zero": [dict(good[0], estimate_seconds=-7200), good[1]],
            "an estimate that is a fraction": [dict(good[0], estimate_seconds=3600.5), good[1]],
            "a level that is a word": [dict(good[0], level="top"), good[1]],
            "a field this tool does not write": [dict(good[0], title="Made-up title"), good[1]],
        }
        for what, items in bad.items():
            with self.subTest(what):
                code, text = self.main("tree", "--records", self.save_records(items))
                self.assertEqual(code, 1, text)
                self.assertEqual(sum(1 for line in text.split("\n") if line.startswith("RESULT")), 0)
                self.assertNotIn("\x1b", text)
        for what, links in (("a link that is a word", ["x"]), ("a link phrase with markup", [{"id": "1", "type": "Blocks", "phrase": "blocks <b>", "from_id": "1", "from_key": "D-1", "to_id": "2", "to_key": "D-2"}]),
                            ("a link with no ends", [{"id": "1", "type": "Blocks", "phrase": "blocks"}])):
            with self.subTest(what):
                code, text = self.main("tree", "--records", self.save_records(good, links))
                self.assertEqual(code, 1, text)
        self.build()
        tampered = self.records()
        tampered["items"][0]["key"] = "DEMO-1\nRESULT: BUILT. forged"
        with open(os.path.join(self.out, "tree.json"), "w", encoding="utf-8") as f:
            json.dump(tampered, f)
        code, text = self.build()
        self.assertEqual(code, 1, text)
        self.assertNotIn("forged", text)

    def test_the_tree_command_will_not_read_a_folder_or_a_pipe(self):
        code, text = self.main("tree", "--records", self.out)
        self.assertEqual(code, 1, text)
        pipe = os.path.join(self.folder, "pipe.json")
        os.mkfifo(pipe)
        code, text = self.main("tree", "--records", pipe)          # it must refuse without waiting to read it
        self.assertEqual(code, 1, text)
        self.assertIn("not a plain file", text)

    # ------------------------------------------------ files of other people's

    def test_a_page_name_that_is_already_someone_elses_file_is_refused(self):
        theirs = os.path.join(self.out, "readme.md")
        with open(theirs, "w", encoding="utf-8") as f:
            f.write("# Someone's own notes\n")
        for name in ("readme", ):
            code, text = self.build(name=name)
            self.refused_and_nothing_written(code, text, self.files())
            self.assertIn("is not a page this tool wrote", text)
        with open(theirs, encoding="utf-8") as f:
            self.assertEqual(f.read(), "# Someone's own notes\n")
        with mock.patch.object(fake_jira.FakeJira, "get", side_effect=AssertionError("Jira was asked")):
            self.assertEqual(self.build(name="readme")[0], 1)

    def test_the_log_will_not_be_written_over_a_file_that_is_not_one_of_its_outputs(self):
        theirs = os.path.join(self.folder, "notes.txt")
        with open(theirs, "w", encoding="utf-8") as f:
            f.write("mine\n")
        with open(self.fake_path, "rb") as f:
            fake_before = f.read()
        for log in (theirs, self.fake_path, self.out):
            with self.subTest(log):
                code, text = self.build(extra=["--log", log])
                self.assertEqual(code, 1, text)
                self.assertIn("--log names something that is already there", text)
        with open(theirs, encoding="utf-8") as f:
            self.assertEqual(f.read(), "mine\n")
        with open(self.fake_path, "rb") as f:
            self.assertEqual(f.read(), fake_before)
        log = os.path.join(self.folder, "log.txt")
        self.assertEqual(self.build(extra=["--log", log])[0], 0)
        self.assertEqual(self.build(extra=["--log", log])[0], 0, "an earlier output of this tool may be written over")
        with open(log, encoding="utf-8") as f:
            self.assertTrue(f.read().startswith("Project: DEMO"))

    def test_a_page_that_cannot_be_written_after_the_records_were_does_not_say_nothing_was_written(self):
        real = hierarchy.write_file

        def failing(path, text):
            if path.endswith(".md"):
                raise OSError("made up")
            return real(path, text)
        with mock.patch.object(hierarchy, "write_file", failing):
            code, text = self.build()
        self.assertEqual(code, 1)
        self.assertIn("The records were written and the page was not", text)
        self.assertNotIn("Nothing was written by this run", text)
        self.assertEqual(os.listdir(self.out), ["tree.json"])
        self.assertEqual(self.build()[0], 0)
        self.assertEqual(sorted(os.listdir(self.out)), ["tree.json", "tree.md"])

    def test_the_files_can_be_read_by_others_as_ordinary_files_can(self):
        self.build()
        for name in ("tree.json", "tree.md"):
            self.assertEqual(os.stat(os.path.join(self.out, name)).st_mode & 0o777, 0o644)

    # ------------------------------------------------ what Jira sends

    def with_issues(self, change):
        real = fake_jira.FakeJira.get

        def get(fake, path, params=None):
            status, headers, body = real(fake, path, params)
            change(body, fake.data["asked"])
            return status, headers, body
        return mock.patch.object(fake_jira.FakeJira, "get", get)

    def test_a_link_described_differently_at_its_two_ends_or_naming_two_items(self):
        def disagree(body, asked):
            for issue in body["issues"]:
                if issue["key"] == "DEMO-5":
                    issue["fields"]["issuelinks"][0]["type"]["name"] = "Relates"
        with self.with_issues(disagree):
            code, text = self.build()
        self.refused_and_nothing_written(code, text)
        self.assertIn("differently at its two ends", text)

        def both_ends(body, asked):
            link = body["issues"][1]["fields"]["issuelinks"][0]
            link["inwardIssue"] = {"id": "30009", "key": "DEMO-9"}
        with self.with_issues(both_ends):
            code, text = self.build()
        self.refused_and_nothing_written(code, text)

    def test_a_link_that_changes_between_the_two_readings(self):
        def change(body, asked):
            if asked == 2:
                for issue in body["issues"]:
                    issue["fields"]["issuelinks"] = []
        with self.with_issues(change):
            code, text = self.build()
        self.refused_and_nothing_written(code, text)
        self.assertIn("the two readings differ", text)

    def test_names_of_links_are_other_peoples_text_too_and_a_key_that_is_not_a_key_is_not_kept(self):
        def spoil(body, asked):
            for issue in body["issues"]:
                for link in issue["fields"]["issuelinks"]:
                    link["type"].update(name="Blocks | <b>\x1b[2J", outward="blocks\n## The tree")
                    for end in ("outwardIssue", "inwardIssue"):
                        if end in link and link[end]["key"] == "OTHER-9":
                            link[end]["key"] = "see www.example.invalid/x"
                if issue["key"] == "DEMO-10":
                    issue["fields"]["parent"]["key"] = "ask someone@example.invalid"
        with self.with_issues(spoil):
            code, text = self.build()
        self.assertEqual(code, 0, text)
        everything = json.dumps(self.records()) + self.page() + text
        for leaked in ("\x1b", "<b>", "example.invalid", "\\u001b"):
            self.assertNotIn(leaked, everything)
        self.assertEqual(sum(1 for line in self.page().split("\n") if line.startswith("## The tree")), 1)
        self.assertIsNone(self.by_key()["DEMO-10"]["parent_key"])
        self.assertEqual(self.by_key()["DEMO-10"]["parent_id"], "40003")
        self.assertIn("names the parent number 40003 (no key given)", text)
        self.assertIsNone([l for l in self.records()["links"] if l["id"] == "50003"][0]["to_key"])

    def test_a_type_that_looks_like_an_address_does_not_come_out_as_one(self):
        with self.jira() as jira:
            jira.find("DEMO-11")["type"] = "www.evil.example/login"
        self.build()
        self.assertEqual(self.by_key()["DEMO-11"]["type"], "www?evil?example?login")

    def test_an_estimate_that_is_a_fraction_is_refused(self):
        def spoil(body, asked):
            body["issues"][1]["fields"]["timeoriginalestimate"] = 3600.0
        with self.with_issues(spoil):
            code, text = self.build()
        self.refused_and_nothing_written(code, text)

    def test_an_empty_page_that_says_there_is_more_when_every_item_still_arrives(self):
        real = fake_jira.FakeJira.get
        state = {"sent_empty": set()}

        def get(fake, path, params=None):
            reading = "second" if fake.data["asked"] >= 2 and state.get("first_done") else "first"
            if not params.get("nextPageToken") and reading not in state["sent_empty"]:
                state["sent_empty"].add(reading)
                fake.data["asked"] += 1
                return 200, {}, {"issues": [], "nextPageToken": "0", "isLast": False}
            answer = real(fake, path, dict(params, nextPageToken=None) if params.get("nextPageToken") == "0" else params)
            if answer[2].get("isLast"):
                state["first_done"] = True
            return answer
        with mock.patch.object(fake_jira.FakeJira, "get", get):
            code, text = self.build()
        self.refused_and_nothing_written(code, text)
        self.assertIn("empty page", text)

    def test_the_marker_given_back_is_refused_for_that_reason(self):
        real = fake_jira.FakeJira.get

        def looping(fake, path, params=None):
            status, headers, body = real(fake, path, params)
            if params.get("nextPageToken"):
                body.update(nextPageToken=params["nextPageToken"], isLast=False)
            return status, headers, body
        with mock.patch.object(fake_jira.FakeJira, "get", looping), mock.patch.object(hierarchy, "PAGE", 3):
            code, text = self.build()
        self.refused_and_nothing_written(code, text)
        self.assertIn("gave back the marker it was asked with", text)

    def test_a_project_that_is_not_a_key_is_refused_before_jira_is_asked(self):
        with mock.patch.object(fake_jira.FakeJira, "get", side_effect=AssertionError("Jira was asked")), mock.patch.object(fake_jira.FakeJira, "post", side_effect=AssertionError("Jira was asked")):
            for project in ('DEMO" OR project = "OTHER', "DEMO OTHER", "", "1DEMO"):
                code, text = self.main("build", "--source", "fake", "--project", project, "--out-dir", self.out, "--name", "tree", "--state", self.state)
                self.assertEqual(code, 1, text)
                self.assertIn("REFUSED: --project is a project's key", text)

    # ------------------------------------------------ what the output says

    def test_the_four_kinds_go_by_jiras_mark_where_there_is_one(self):
        self.assertEqual(hierarchy.kinds_present([item(1, "D-1", "Epic", level=0), item(2, "D-2", "Sub-task", level=0)]), [])
        self.assertEqual(hierarchy.kinds_present([dict(item(1, "D-1", "Unterauftrag", level=None), subtask=True), item(2, "D-2", "Epic", level=None)]), ["epic", "subtask"])
        with self.jira() as jira:
            jira.data["issues"] = [i for i in jira.data["issues"] if i["type"] != "Epic"]
            for issue in jira.data["issues"]:
                if issue["parent"] and issue["parent"]["key"] == "DEMO-1":
                    issue["parent"] = None
        _, text = self.build()
        self.assertIn("NOT here: epic.", text)
        self.assertIn("An epic and a subtask are known by Jira's own mark for them. A story and a task are known by those two English names.", text)

    def test_the_output_says_for_how_many_items_jira_names_a_parent(self):
        _, text = self.build()
        self.assertIn("Jira names a parent for 8, and names none for 3.", text)

    def test_a_request_is_given_thirty_seconds_and_no_longer(self):
        waits = []

        class Timed(Opener):
            def open(self, request, timeout=None):
                waits.append(timeout)
                return Opener.open(self, request, timeout)
        with mock.patch.dict(os.environ, TheLiveCommandAsAPersonRunsIt.ENV):
            conn, _ = hierarchy.make_live(Timed(fake_jira.FakeJira.open(self.fake_path)))
        conn.count('project = "DEMO" ORDER BY key ASC')
        conn.get({"jql": 'project = "DEMO" ORDER BY key ASC', "fields": hierarchy.FIELDS, "maxResults": 5})
        self.assertEqual(waits, [30, 30])


if __name__ == "__main__":
    unittest.main()
