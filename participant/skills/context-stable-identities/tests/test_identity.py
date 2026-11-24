"""Tests for the context-stable-identities skill. Each applies the made-up batches in participant/context/identity/batches to a map in a scratch folder."""
import copy
import json
import os
import re
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import identity      # noqa: E402

BATCHES = os.path.join(identity.FOLDER, "batches")
STORY, CARD, ISSUE = "jira:40003", "trello:6ae851100000000000000a02", "github:I_kwFIX0302"


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def card(short):
    """The identity of the made-up Trello card with this short link."""
    return "trello:" + [one["record"]["id"] for one in batch(1)["records"] if one["record"].get("shortLink") == short][0]


def batch(number):
    return json.loads(read(os.path.join(BATCHES, "batch-%d.json" % number)))


class Base(unittest.TestCase):
    def setUp(self):
        self.state = identity.load(tempfile.gettempdir() + "/no-such-map-folder")
        self.said = []

    def apply(self, data):
        self.said = []
        return identity.sync(self.state, data, self.said.append)

    def upto(self, last):
        for number in range(1, last + 1):
            self.apply(batch(number))

    def one(self, system, record, name="extra"):
        return self.apply({"batch": name, "records": [{"system": system, "record": record}]})


class Deriving(unittest.TestCase):
    """Criteria 1, 2 and 7."""

    def test_an_identity_is_the_system_a_colon_and_the_identifier(self):
        self.assertEqual(identity.derive("jira", "40003"), "jira:40003")
        self.assertEqual(identity.derive("trello", "6ae851100000000000000a02"), "trello:6ae851100000000000000a02")
        self.assertEqual(identity.derive("github", "I_kwFIX0302"), "github:I_kwFIX0302")

    def test_the_identifier_is_used_character_for_character(self):
        self.assertNotEqual(identity.derive("github", "I_kwFIXab05"), identity.derive("github", "I_kwFIXAB05"))
        self.assertEqual(identity.derive("jira", "0040003"), "jira:0040003")

    def test_a_whole_number_is_written_as_its_digits_and_that_is_the_only_conversion(self):
        self.assertEqual(identity.derive("jira", 40003), identity.derive("jira", "40003"))
        for bad in (40003.0, 40003.5, True, None, ["40003"], {"id": 1}, -5):
            with self.assertRaises(identity.Refused, msg=repr(bad)):
                identity.derive("jira", bad)

    def test_an_identifier_that_is_not_clean_is_refused_not_repaired(self):
        for bad in ("", " 40003", "40003 ", "40 003", "jira:40003", "a\tb", "a\nb", "x" * 201, "café"):
            with self.assertRaises(identity.Refused, msg=repr(bad)):
                identity.derive("jira", bad)
        self.assertEqual(identity.derive("jira", "x" * 200), "jira:" + "x" * 200)

    def test_an_unknown_system_is_refused(self):
        for bad in ("asana", "Jira", "JIRA", "", None):
            with self.assertRaises(identity.Refused):
                identity.derive(bad, "1")

    def test_the_field_used_is_the_one_the_rules_name_and_no_other(self):
        self.assertEqual([identity.SYSTEMS[s]["identifier"][0] for s in ("jira", "trello", "github")], ["id", "id", "node_id"])
        base = Base()
        base.setUp()
        record = {"node_id": "I_kwONE", "id": 1, "number": 5, "title": "T", "created_at": "2026-10-02T10:00:00Z", "repository": {"id": 1, "full_name": "a/b"}}
        base.one("github", record, "one")
        changed = dict(record, id=999, number=77, title="Other", repository={"id": 2, "full_name": "c/d"}, html_url="https://github.com/c/d/issues/77")
        base.one("github", changed, "two")
        self.assertEqual(list(base.state["items"]), ["github:I_kwONE"])

    def test_the_rules_document_is_what_the_code_writes_and_can_be_followed_by_hand(self):
        text = identity.rules_document()
        self.assertEqual(read(os.path.join(identity.FOLDER, "rules.md")), text)
        for phrase in ("SYSTEM:IDENTIFIER", "character for character", "One conversion is allowed", "Do not repair it", "Do not compare titles", "## 5. When a source reuses an identifier",
                       "## 8. Deriving an identity by hand"):
            self.assertIn(phrase, text)
        for system in identity.SYSTEMS:
            for field, why in identity.SYSTEMS[system]["refused"]:
                self.assertIn("| `%s` | %s |" % (field, why), text)


class RenameAndMove(Base):
    """Criteria 2, 3 and 4."""

    def test_twenty_records_across_three_systems_get_twenty_identities(self):
        self.upto(1)
        systems = [item["system"] for item in self.state["items"].values()]
        self.assertEqual((len(systems), systems.count("jira"), systems.count("trello"), systems.count("github")), (20, 7, 7, 6))

    def test_after_renames_and_moves_every_identity_is_the_same(self):
        self.upto(1)
        before = sorted(self.state["items"])
        self.upto_two = self.apply(batch(2))
        self.assertEqual(sorted(self.state["items"]), before)
        self.assertEqual(self.upto_two, 0)

    def test_the_renamed_and_moved_items_were_updated_in_place(self):
        self.upto(2)
        for one, title, reference in ((STORY, "Export intake records as CSV, weekly", "OPS-17"), (CARD, "Export report as PDF and CSV", "fixT0002"),
                                      (ISSUE, "Add retry and backoff to the webhook sender", 41)):
            item = self.state["items"][one]
            self.assertEqual((item["now"]["title"], item["now"]["reference"]), (title, reference))
            changes = [entry["change"] for entry in item["history"]]
            self.assertIn("renamed", changes)
            self.assertIn("moved", changes)
        self.assertEqual(self.state["items"][STORY]["now"]["container"], "Made-up project OPS")

    def test_a_title_swapped_between_two_items_moves_no_identity(self):
        self.upto(1)
        first, other = self.state["items"][STORY]["birth_mark"], self.state["items"]["jira:40005"]["birth_mark"]
        self.upto_two = self.apply(batch(2))
        self.assertEqual(self.state["items"]["jira:40005"]["now"]["title"], "Export intake records as CSV")
        self.assertEqual((self.state["items"][STORY]["birth_mark"], self.state["items"]["jira:40005"]["birth_mark"]), (first, other))

    def test_items_with_the_same_title_are_separate_items(self):
        self.upto(1)
        same = [one for one, item in self.state["items"].items() if item["now"]["title"] == "Fix export"]
        self.assertEqual(sorted(same), ["github:I_kwFIX0304", "jira:40004", "jira:40006", card("fixT0005")])

    def test_the_order_of_the_records_and_the_batch_s_name_change_nothing(self):
        data = batch(1)
        self.apply(data)
        forward = copy.deepcopy(self.state["items"])
        other = Base()
        other.setUp()
        other.apply({"batch": "another-name", "records": list(reversed(data["records"]))})
        for one in forward:
            forward[one]["first_batch"] = forward[one]["last_batch"] = other.state["items"][one]["first_batch"]
        self.assertEqual(other.state["items"], forward)

    def test_a_card_moved_within_its_board_and_dragged_keeps_its_identity_and_records_no_change(self):
        self.upto(2)
        self.assertEqual(self.state["items"][card("fixT0004")]["history"], [])

    def test_a_re_sync_of_unchanged_records_changes_nothing(self):
        self.upto(2)
        before = copy.deepcopy(self.state["items"])
        again = batch(2)
        again["batch"] = "batch-2-again"
        self.assertEqual(self.apply(again), 0)
        for item in before.values():
            item["last_batch"] = "batch-2-again"
        self.assertEqual(self.state["items"], before)


class Collision(Base):
    """Criterion 5."""

    def test_two_different_records_with_one_identity_are_reported_and_neither_is_written(self):
        self.upto(2)
        reported = self.apply(batch(3))
        self.assertEqual(reported, 1)
        self.assertNotIn("github:I_kwFIX0306", self.state["items"])
        self.assertTrue(any("COLLISION: 2 different records" in line and "Neither is written" in line for line in self.said))
        self.assertEqual(self.state["collisions"][0]["seen_as"], ["Rotate the signing key", "Archive the old dashboards"])

    def test_a_collision_on_an_identity_already_held_leaves_the_held_item_as_it_was(self):
        self.upto(2)
        before = copy.deepcopy(self.state["items"][ISSUE])
        clash = {"batch": "clash", "records": [
            {"system": "github", "record": {"node_id": "I_kwFIX0302", "number": 1, "title": "One claimant", "created_at": "2026-10-03T10:00:00Z", "repository": {"id": 1, "full_name": "a/b"}}},
            {"system": "github", "record": {"node_id": "I_kwFIX0302", "number": 2, "title": "Another claimant", "created_at": "2026-10-03T10:00:00Z", "repository": {"id": 1, "full_name": "a/b"}}}]}
        self.assertEqual(self.apply(clash), 1)
        self.assertEqual(self.state["items"][ISSUE], before)
        self.assertTrue(any("The item already held under that identity is left as it was" in line for line in self.said))

    def test_the_same_record_delivered_twice_is_applied_once_and_is_not_a_collision(self):
        self.upto(2)
        self.apply(batch(3))
        self.assertTrue(any("jira:40002 was delivered 2 times" in line for line in self.said))
        self.assertEqual(len(self.state["collisions"]), 1)

    def test_records_that_differ_only_in_a_field_that_is_not_shown_still_collide(self):
        a = {"node_id": "I_kwC", "number": 1, "title": "Same", "created_at": "2026-10-03T10:00:00Z", "repository": {"id": 1, "full_name": "a/b"}, "locked": False}
        self.assertEqual(self.apply({"batch": "c", "records": [{"system": "github", "record": a}, {"system": "github", "record": dict(a, locked=True)}]}), 1)
        self.assertEqual(self.state["items"], {})


class Reuse(Base):
    """Criterion 6."""

    def test_a_different_birth_mark_is_reported_as_reuse_and_nothing_is_overwritten(self):
        self.upto(3)
        before = copy.deepcopy(self.state["items"]["jira:40007"])
        self.assertEqual(self.apply(batch(4)), 1)
        self.assertEqual(self.state["items"]["jira:40007"], before)
        self.assertEqual(before["now"]["title"], "Tidy the export folder")
        held = self.state["held_aside"][0]
        self.assertEqual((held["identity"], held["held_birth_mark"], held["newcomer_birth_mark"], held["newcomer"]["title"]),
                         ("jira:40007", "2026-11-06T09:00:00Z", "2026-11-20T09:00:00Z", "Rotate the signing key"))
        self.assertTrue(any("REUSED IDENTIFIER: jira:40007" in line for line in self.said))

    def test_the_same_birth_mark_with_everything_else_changed_is_the_same_item(self):
        self.upto(1)
        record = batch(1)["records"][6]["record"]
        changed = dict(record, key="ZZZ-999", fields=dict(record["fields"], summary="Nothing like the old title", project={"id": "9", "key": "ZZZ", "name": "Elsewhere"}))
        self.assertEqual(self.one("jira", changed), 0)
        self.assertEqual(self.state["items"]["jira:40007"]["now"]["title"], "Nothing like the old title")
        self.assertEqual(self.state["held_aside"], [])

    def test_the_same_title_with_a_different_birth_mark_is_still_reuse(self):
        self.upto(1)
        record = batch(1)["records"][6]["record"]
        same_title = dict(record, fields=dict(record["fields"], created="2026-11-25T09:00:00.000+0000"))
        self.assertEqual(self.one("jira", same_title), 1)
        self.assertEqual(len(self.state["held_aside"]), 1)

    def test_the_same_moment_written_in_another_time_zone_is_the_same_birth_mark(self):
        self.upto(1)
        record = batch(1)["records"][6]["record"]
        self.assertEqual(self.one("jira", dict(record, fields=dict(record["fields"], created="2026-11-06T04:00:00.000-0500"))), 0)

    def test_with_no_creation_time_reuse_cannot_be_checked_and_the_run_says_so(self):
        self.upto(3)
        self.apply(batch(4))
        self.assertTrue(any("github:I_kwFIX0301 could not be checked for reuse" in line for line in self.said))
        self.assertTrue(any("NEW: github:I_kwFIX0307. Its record gives no creation time" in line for line in self.said))
        self.assertIsNone(self.state["items"]["github:I_kwFIX0307"]["birth_mark"])

    def test_a_trello_card_s_birth_mark_comes_from_its_id_so_reuse_of_a_card_id_cannot_be_seen(self):
        self.upto(1)
        card = batch(1)["records"][8]["record"]
        self.assertEqual(identity.birth_mark("trello", card), "2026-11-02T09:00:00Z")
        self.assertEqual(self.one("trello", dict(card, name="A wholly different card", idBoard="x", shortLink="other")), 0)
        self.assertEqual(self.state["held_aside"], [])


class AliasAndRefusal(Base):
    def test_an_alias_is_made_when_the_source_names_the_previous_identifier(self):
        self.upto(4)
        old = copy.deepcopy(self.state["items"]["github:I_kwFIX0303"])
        self.apply(batch(5))
        self.assertNotIn("github:I_kwFIX0303", self.state["items"])
        new = self.state["items"]["github:I_kwFIX0399"]
        self.assertEqual((new["birth_mark"], new["first_batch"]), (old["birth_mark"], old["first_batch"]))
        self.assertEqual(identity.resolve(self.state, "github:I_kwFIX0303"), "github:I_kwFIX0399")
        self.assertEqual(identity.resolve(self.state, "github:I_kwFIX0399"), "github:I_kwFIX0399")
        self.assertEqual(len(self.state["items"]), 21)

    def test_no_alias_is_made_from_a_matching_title(self):
        self.upto(1)
        record = {"node_id": "I_kwNEW", "number": 3, "title": "Drop the legacy importer", "created_at": "2026-10-04T10:00:00Z", "repository": {"id": 101, "full_name": "acme-fixture/platform"}}
        self.one("github", record)
        self.assertEqual(self.state["aliases"], {})
        self.assertIn("github:I_kwFIX0303", self.state["items"])
        self.assertIn("github:I_kwNEW", self.state["items"])

    def test_six_records_with_no_usable_identifier_are_refused_and_get_no_identity(self):
        self.upto(4)
        self.assertEqual(self.apply(batch(5)), 6)
        self.assertEqual(len(self.state["refused"]), 6)
        for one in self.state["items"]:
            self.assertNotRegex(one, r"40042|40009|6744:bad|asana|^jira:$")

    def test_a_jira_id_sent_as_a_number_is_the_item_already_held(self):
        self.upto(4)
        self.apply(batch(5))
        self.assertEqual(len([one for one in self.state["items"] if one.startswith("jira:40001")]), 1)
        self.assertEqual(self.state["items"]["jira:40001"]["last_batch"], "batch-5")


class TheMapAndTheFiles(Base):
    def test_the_handed_in_map_and_state_are_what_the_five_batches_give(self):
        self.upto(5)
        self.assertEqual(json.loads(read(os.path.join(identity.FOLDER, "state.json"))), self.state)
        self.assertEqual(read(os.path.join(identity.FOLDER, "map.md")), identity.map_document(self.state))

    def test_the_map_lists_every_item_and_what_was_reported(self):
        self.upto(5)
        text = identity.map_document(self.state)
        for one in self.state["items"]:
            self.assertIn("| `%s` |" % one, text)
        for phrase in ("| `jira:40003` | batch-2 | renamed |", "| `jira:40003` | batch-2 | moved |", "| `github:I_kwFIX0303` | `github:I_kwFIX0399` |", "| `jira:40007` | batch-4 | 2026-11-06T09:00:00Z |",
                       "| `github:I_kwFIX0306` | batch-3 | 2 |"):
            self.assertIn(phrase, text)

    def test_a_batch_cannot_be_applied_twice_and_a_broken_batch_stops_with_nothing_written(self):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)
        run = lambda *args: identity.main(list(args) + ["--folder", folder], say=lambda line: None)
        self.assertEqual(run("sync", "--batch", os.path.join(BATCHES, "batch-1.json")), 0)
        before = read(os.path.join(folder, "state.json"))
        self.assertEqual(run("sync", "--batch", os.path.join(BATCHES, "batch-1.json")), 1)
        bad = os.path.join(folder, "bad.json")
        with open(bad, "w") as f:
            f.write("{not json")
        self.assertEqual(run("sync", "--batch", bad), 1)
        self.assertEqual(read(os.path.join(folder, "state.json")), before)

    def test_an_export_and_an_import_give_the_same_identities(self):
        folder, other = tempfile.mkdtemp(), tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)
        self.addCleanup(shutil.rmtree, other)
        quiet = lambda line: None
        for number in (1, 2):
            identity.main(["sync", "--batch", os.path.join(BATCHES, "batch-%d.json" % number), "--folder", folder], say=quiet)
        self.assertEqual(identity.main(["export", "--out", os.path.join(folder, "export.json"), "--folder", folder], say=quiet), 0)
        self.assertEqual(identity.main(["import", "--from", os.path.join(folder, "export.json"), "--folder", other], say=quiet), 0)
        self.assertEqual(read(os.path.join(other, "state.json")), read(os.path.join(folder, "state.json")))
        self.assertEqual(identity.main(["import", "--from", os.path.join(folder, "export.json"), "--folder", other], say=quiet), 1)
        for number in (3, 4, 5):
            for target in (folder, other):
                identity.main(["sync", "--batch", os.path.join(BATCHES, "batch-%d.json" % number), "--folder", target], say=quiet)
        self.assertEqual(read(os.path.join(other, "state.json")), read(os.path.join(folder, "state.json")))

    def test_the_skill_reaches_no_network(self):
        code = read(os.path.join(os.path.dirname(HERE), "identity.py"))
        self.assertEqual(set(re.findall(r"^(?:import|from) ([A-Za-z_.]+)", code, re.M)), {"argparse", "datetime", "json", "os", "re", "sys"})


if __name__ == "__main__":
    unittest.main()
