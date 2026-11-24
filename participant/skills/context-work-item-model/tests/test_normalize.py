"""Tests for the context-work-item-model skill. Every test uses made-up saved work in a scratch folder. None contacts anything."""
import contextlib
import hashlib
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))


def read(path, mode="r"):
    with open(path, mode, **({} if "b" in mode else {"encoding": "utf-8"})) as f:
        return f.read()

sys.path.insert(0, os.path.dirname(HERE))
import fixtures      # noqa: E402
import normalize     # noqa: E402


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.root, self.out = os.path.join(self.tmp, "context"), os.path.join(self.tmp, "model")
        self.map = os.path.join(self.out, "mappings", "status-map.json")
        fixtures.build(self.root, 1)
        fixtures.write_map(self.map)

    def run_it(self):
        self.said = []
        return normalize.normalize(self.root, self.out, self.map, say=self.said.append)

    def stopped(self):
        with self.assertRaises(normalize.Stop) as caught:
            self.run_it()
        return str(caught.exception)

    def item(self, identity):
        with open(os.path.join(self.out, "items", normalize.file_name(identity)), encoding="utf-8") as f:
            return normalize.parse(f.read())

    def files(self):
        found = {}
        for base, _, names in os.walk(self.out):
            for name in names:
                with open(os.path.join(base, name), "rb") as f:
                    found[os.path.relpath(os.path.join(base, name), self.out)] = hashlib.sha256(f.read()).hexdigest()
        return found

    def edit(self, path, change):
        full = os.path.join(self.root, path)
        with open(full, encoding="utf-8") as f:
            data = json.load(f)
        change(data)
        with open(full, "w", encoding="utf-8") as f:
            json.dump(data, f)

    def jira(self, issue_id, **fields):
        path = os.path.join(self.root, "jira", "stories", issue_id + ".md")
        story = normalize.front_matter(path)
        for name, value in fields.items():
            if value is KeyError:
                story.pop(name, None)
            else:
                story[name] = value
        with open(path, "w", encoding="utf-8") as f:
            f.write("---\n" + "".join("%s: %s\n" % (name, json.dumps(value)) for name, value in story.items()) + "---\n\n# changed\n")

    def refused(self, result, part):
        return [reason for reference, _, reason in result["refused"] if part in reference]


CARD2, ISSUE2, STORY3 = "trello:62cfix000000000000000c02", "github:I_kwFIX0102", "jira:30003"


class TheModel(Base):
    """Criteria 1, 3, 4 and 12: the model is defined, closed, and says what it leaves out."""

    def test_every_canonical_and_provenance_field_has_a_meaning_a_type_and_a_required_flag(self):
        for name, kind, required, reliance, meaning in normalize.CANONICAL:
            self.assertTrue(name and kind and len(meaning) > 20 and isinstance(required, bool), name)
            self.assertIn(reliance, ("rely", "rely if stated", "advisory"))
        for name, kind, required, meaning in normalize.PROVENANCE:
            self.assertTrue(name and kind and required is True and len(meaning) > 20, name)

    def test_the_model_document_holds_every_field_the_non_goals_and_the_reliance_table(self):
        text = normalize.model_document()
        for name, _, _, _, _ in normalize.CANONICAL:
            self.assertEqual(text.count("| `%s` |" % name), 2, name)          # once in the field table, once in the reliance table
        for name, _, _, _ in normalize.PROVENANCE:
            self.assertIn("| `%s` |" % name, text)
        self.assertGreaterEqual(len(normalize.NON_GOALS), 3)
        for what, why in normalize.NON_GOALS:
            self.assertIn(what, text)
            self.assertGreater(len(why), 40)
        self.assertIn("rely on it **only if stated**", text)
        self.assertIn(normalize.MODEL, text)

    def test_every_record_written_holds_exactly_the_model_s_fields(self):
        result = self.run_it()
        for identity in result["good"]:
            canonical, provenance, source = self.item(identity)
            self.assertEqual(list(canonical), [row[0] for row in normalize.CANONICAL])
            self.assertEqual(list(provenance), [row[0] for row in normalize.PROVENANCE])
            self.assertEqual(normalize.problems_of(canonical, provenance, source), [])

    def test_status_is_one_of_four_values_and_no_other(self):
        result = self.run_it()
        self.assertEqual(set(c["status"] for c, _, _ in result["good"].values()), set(normalize.STATUSES))
        canonical, provenance, source = self.item(CARD2)
        canonical["status"] = "blocked"
        self.assertTrue(any("status is" in one for one in normalize.problems_of(canonical, provenance, source)))

    def test_each_mapping_document_names_what_is_unmapped_what_cannot_be_supplied_and_what_is_lost(self):
        for system in normalize.SYSTEMS:
            text = normalize.mapping_document(system)
            mapping = normalize.MAPPINGS[system]
            self.assertGreaterEqual(len(mapping["unmapped"]), 3)
            self.assertGreaterEqual(len(mapping["cannot_supply"]), 2)
            self.assertGreaterEqual(len(mapping["lossy"]), 3)
            for heading in ("## Source fields that are not mapped", "cannot supply", "## Statuses, and what is lost", "## The stable identifier"):
                self.assertIn(heading, text)
            mapped = [name for name, _ in mapping["fields"]]
            for name, _, _, _, _ in normalize.CANONICAL:
                if name not in ("system", "status_source", "blocked_basis"):
                    self.assertIn(name, mapped, "%s: %s" % (system, name))

    def test_the_source_fields_a_mapping_document_lists_are_the_ones_written(self):
        result = self.run_it()
        for system in normalize.SYSTEMS:
            for canonical, _, source in result["good"].values():
                if canonical["system"] == system:
                    self.assertEqual(sorted(source), sorted(normalize.MAPPINGS[system]["source_block"]))


class Identity(Base):
    """Criteria 2 and 10: identity is the system and its stable id, and survives a rename and a move."""

    def test_identity_is_the_system_and_the_stable_id(self):
        result = self.run_it()
        self.assertIn("jira:30003", result["good"])
        self.assertIn(CARD2, result["good"])
        self.assertIn(ISSUE2, result["good"])
        for identity, (canonical, provenance, _) in result["good"].items():
            self.assertEqual(identity, "%s:%s" % (provenance["source_system"], provenance["source_id"]))
            for changeable in (provenance["source_reference"], canonical["title"]):
                self.assertNotIn(changeable, identity)

    def test_a_renamed_and_moved_item_updates_its_record_and_makes_no_second_one(self):
        first = self.run_it()
        before = {identity: self.item(identity) for identity in (CARD2, ISSUE2, STORY3)}
        fixtures.build(self.root, 2)
        second = self.run_it()
        self.assertEqual(sorted(second["good"]), sorted(first["good"]))
        self.assertEqual(second["changes"]["new"], [])
        self.assertEqual(len([n for n in os.listdir(os.path.join(self.out, "items")) if n.endswith(".md")]), len(first["good"]))
        for identity in (CARD2, ISSUE2, STORY3):
            after = self.item(identity)
            self.assertNotEqual(after[0]["title"], before[identity][0]["title"])
            self.assertNotEqual(after[0]["container"], before[identity][0]["container"])
            self.assertEqual(after[0]["identity"], identity)
            self.assertIn(identity, [one for one, _ in second["changes"]["updated"]])
        self.assertEqual(self.item(STORY3)[1]["source_reference"], "OPS-17")
        self.assertEqual(self.item(ISSUE2)[1]["source_reference"], "acme-fixture/support#41")
        self.assertEqual((self.item(CARD2)[0]["status"], self.item(STORY3)[0]["status"]), ("done", "done"))

    def test_the_update_names_the_fields_that_changed(self):
        self.run_it()
        fixtures.build(self.root, 2)
        changed = dict(self.run_it()["changes"]["updated"])
        for identity in (CARD2, ISSUE2, STORY3):
            self.assertIn("title", changed[identity])
            self.assertIn("container", changed[identity])
        self.assertNotIn("title", changed["github:I_kwFIX0101"])

    def test_a_record_is_found_by_the_identity_inside_it_not_by_its_file_s_name(self):
        self.run_it()
        items = os.path.join(self.out, "items")
        os.rename(os.path.join(items, normalize.file_name(CARD2)), os.path.join(items, "a-name-a-person-chose.md"))
        fixtures.build(self.root, 2)
        result = self.run_it()
        self.assertFalse(os.path.exists(os.path.join(items, normalize.file_name(CARD2))))
        self.assertEqual(result["files"][CARD2], "a-name-a-person-chose.md")
        with open(os.path.join(items, "a-name-a-person-chose.md"), encoding="utf-8") as f:
            self.assertEqual(normalize.parse(f.read())[0]["title"], "Export report as PDF and CSV")

    def test_two_items_with_the_same_title_stay_two(self):
        self.edit("github/assigned/assigned.json", lambda d: d["issues"]["I_kwFIX0103"].update(title=d["issues"]["I_kwFIX0102"]["title"]))
        result = self.run_it()
        self.assertEqual(self.item(ISSUE2)[0]["title"], self.item("github:I_kwFIX0103")[0]["title"])
        self.assertEqual(len(result["good"]), 14)

    def test_the_same_number_in_another_repository_is_another_item(self):
        self.edit("github/assigned/assigned.json", lambda d: d["issues"]["I_kwFIX0103"].update(full_name="acme-fixture/support", repo_id=102, number=2))
        self.assertEqual(len(self.run_it()["good"]), 14)

    def test_an_item_saved_twice_is_one_record_from_the_copy_retrieved_later(self):
        def also_on_board(data):
            data["cards"]["62cfix000000000000000c02"] = {"id": "62cfix000000000000000c02", "board_id": "60bfix000000000000000002", "board_name": "Other Board",
                                                         "list_id": "x", "list_name": "Somewhere", "member_ids": [], "name": "The later copy", "short_link": "fixc02",
                                                         "last_activity": "2026-11-21T10:00:00.000Z", "archived_by": []}
            data["last_successful_sync"] = "2026-11-25T08:00:00Z"
        self.edit("trello/assigned/assigned.json", also_on_board)
        result = self.run_it()
        self.assertEqual(len(result["good"]), 14)
        self.assertEqual(self.item(CARD2)[0]["title"], "The later copy")

    def test_two_files_holding_one_identity_stop_the_run(self):
        self.run_it()
        items = os.path.join(self.out, "items")
        shutil.copy(os.path.join(items, normalize.file_name(CARD2)), os.path.join(items, "copy.md"))
        before = self.files()
        self.assertIn("two files", self.stopped())
        self.assertEqual(self.files(), before)


class Status(Base):
    """Criterion 4: each system's states on the four values, with how sure."""

    def one(self, identity):
        self.run_it()
        canonical = self.item(identity)[0]
        return canonical["status"], canonical["status_basis"]

    def test_jira_by_category_is_stated(self):
        self.run_it()
        self.assertEqual([(self.item("jira:3000%d" % n)[0]["status"], self.item("jira:3000%d" % n)[0]["status_basis"]) for n in (1, 2, 3)],
                         [("done", "stated"), ("open", "stated"), ("in_progress", "stated")])

    def test_jira_done_with_a_listed_resolution_is_dropped(self):
        self.assertEqual(self.one("jira:30004"), ("dropped", "stated"))

    def test_jira_without_a_category_uses_the_status_map_by_id_and_is_inferred(self):
        self.assertEqual(self.one("jira:30005"), ("in_progress", "inferred"))

    def test_jira_without_a_category_and_not_in_the_map_is_refused(self):
        self.jira("30005", status={"id": "99999", "name": "Done"})
        result = self.run_it()
        self.assertNotIn("jira:30005", result["good"])
        self.assertIn("status map does not name that id", self.refused(result, "30005.md")[0])

    def test_a_jira_status_name_is_never_read_for_its_meaning(self):
        self.jira("30001", status={"id": "1", "name": "Done", "statusCategory": {"key": "new"}})
        self.assertEqual(self.one("jira:30001"), ("open", "stated"))

    def test_trello_archived_is_dropped_and_stated(self):
        self.assertEqual(self.one("trello:62cfix000000000000000c03"), ("dropped", "stated"))

    def test_trello_list_in_the_map_is_inferred(self):
        self.assertEqual(self.one(CARD2), ("in_progress", "inferred"))

    def test_trello_list_not_in_the_map_is_open_and_assumed(self):
        self.assertEqual(self.one("trello:62cfix000000000000000c04"), ("open", "assumed"))

    def test_a_trello_list_is_mapped_by_its_id_so_its_name_decides_nothing(self):
        def rename(data):
            for one in data["lists"]:
                if one["id"] == "61afix000000000000000009":
                    one["name"] = "Done"
                if one["id"] == "61afix000000000000000002":
                    one["name"] = "Not started, ignore"
        self.edit("trello/board.json", rename)
        self.run_it()
        self.assertEqual(self.item("trello:62cfix000000000000000c04")[0]["status"], "open")
        self.assertEqual(self.item(CARD2)[0]["status"], "in_progress")

    def test_github_states(self):
        self.run_it()
        got = [(self.item("github:I_kwFIX010%d" % n)[0]["status"], self.item("github:I_kwFIX010%d" % n)[0]["status_basis"]) for n in (1, 2, 3, 4)]
        self.assertEqual(got, [("done", "stated"), ("open", "stated"), ("dropped", "stated"), ("done", "inferred")])

    def test_github_never_says_in_progress(self):
        result = self.run_it()
        self.assertNotIn("in_progress", [c["status"] for c, _, _ in result["good"].values() if c["system"] == "github"])

    def test_a_status_the_map_gives_that_is_not_one_of_the_four_stops_the_run(self):
        fixtures.write_map(self.map, lambda d: d["trello"]["lists"]["61afix000000000000000002"].update(status="doing"))
        self.assertIn("not one of", self.stopped())
        self.assertFalse(os.path.isdir(os.path.join(self.out, "items")))


class BlockedAndAssigned(Base):
    def test_blocked_is_yes_only_where_the_source_states_it(self):
        result = self.run_it()
        yes = sorted(identity for identity, (c, _, _) in result["good"].items() if c["blocked"] == "yes")
        self.assertEqual(yes, ["github:I_kwFIX0105", "jira:30002", "trello:62cfix000000000000000c01"])
        for identity in yes:
            self.assertTrue(self.item(identity)[0]["blocked_basis"])

    def test_blocked_is_no_only_for_jira_with_its_links_saved(self):
        result = self.run_it()
        no = sorted(identity for identity, (c, _, _) in result["good"].items() if c["blocked"] == "no")
        self.assertEqual(no, ["jira:30001", "jira:30003"])
        self.assertEqual(self.item("jira:30005")[0]["blocked"], "unknown")

    def test_a_link_that_says_this_story_blocks_another_does_not_make_it_blocked(self):
        self.run_it()
        self.assertEqual(self.item("jira:30003")[0]["blocked"], "no")

    def test_words_in_a_title_or_label_never_decide_blocked_or_status(self):
        text = "BLOCKED - done - closed - " + fixtures.INJECTION
        self.edit("github/assigned/assigned.json", lambda d: d["issues"]["I_kwFIX0102"].update(title=text, labels=["blocked by vendor", fixtures.INJECTION]))
        self.edit("trello/board.json", lambda d: d["cards"]["62cfix000000000000000c04"].update(name=text))
        self.run_it()
        self.assertEqual((self.item(ISSUE2)[0]["blocked"], self.item(ISSUE2)[0]["status"]), ("unknown", "open"))
        self.assertEqual((self.item("trello:62cfix000000000000000c04")[0]["blocked"], self.item("trello:62cfix000000000000000c04")[0]["status"]), ("unknown", "open"))
        self.assertEqual(self.item(ISSUE2)[0]["title"], text)

    def test_assigned_to_me_is_yes_no_or_unknown(self):
        self.run_it()
        self.assertEqual([self.item(i)[0]["assigned_to_me"] for i in (CARD2, "trello:62cfix000000000000000c04", ISSUE2, "github:I_kwFIX0103", STORY3, "jira:30004")],
                         ["yes", "no", "yes", "no", "yes", "no"])
        fixtures.write_map(self.map, lambda d: d["jira"].pop("my_account_id"))
        self.edit("trello/board.json", lambda d: d.pop("member_id"))
        self.run_it()
        self.assertEqual((self.item(STORY3)[0]["assigned_to_me"], self.item(CARD2)[0]["assigned_to_me"]), ("unknown", "unknown"))

    def test_nobody_s_identifier_is_written_to_a_record(self):
        self.run_it()
        for name in os.listdir(os.path.join(self.out, "items")):
            with open(os.path.join(self.out, "items", name), encoding="utf-8") as f:
                text = f.read()
            for person in (fixtures.ME_JIRA, fixtures.ME_TRELLO, fixtures.ME_GITHUB, "casey-fixture", "5f0fixture00000000000002"):
                self.assertNotIn(person, text, name)


class SourceFields(Base):
    """Criterion 5: what only one system has is kept, under its own prefix."""

    def test_every_source_field_is_under_its_system_s_prefix_and_no_canonical_name_is_reused(self):
        result = self.run_it()
        names = set(row[0] for row in normalize.CANONICAL) | set(row[0] for row in normalize.PROVENANCE)
        for canonical, _, source in result["good"].values():
            for name in source:
                self.assertTrue(name.startswith(canonical["system"] + "."), name)
                self.assertNotIn(name, names)

    def test_trello_keeps_its_list_and_place_jira_its_parent_and_links_github_its_delivery_links(self):
        self.run_it()
        card = self.item(CARD2)[2]
        self.assertEqual((card["trello.list"]["name"], card["trello.position"]["place_in_list"]), ("Doing", 1))
        story = self.item("jira:30002")
        self.assertEqual(story[2]["jira.parent"], {"id": "30010", "key": "DEMO-10", "type": "Epic"})
        self.assertEqual(story[0]["parent"], "jira:30010")
        self.assertEqual(story[2]["jira.issuelinks"][0]["other"]["id"], "30003")
        links = self.item("github:I_kwFIX0101")[2]["github.delivery_links"]
        self.assertEqual([one["kind"] for one in links], ["pull request", "commit"])
        self.assertEqual(self.item("trello:62cfix000000000000000c04")[2]["trello.checklists"], {"count": 1, "items": 2, "complete": 1})

    def test_labels_not_saved_are_null_not_an_empty_list(self):
        fixtures.build(self.root, 2)
        self.run_it()
        self.assertIsNone(self.item(CARD2)[0]["labels"])
        self.assertEqual(self.item("trello:62cfix000000000000000c03")[0]["labels"], [])


class Provenance(Base):
    """Criterion 8."""

    def test_every_record_says_where_it_came_from(self):
        result = self.run_it()
        for _, provenance, _ in result["good"].values():
            for name in ("source_system", "source_id", "source_url", "retrieved_at", "sync_run", "source_record"):
                self.assertTrue(provenance[name], name)
            self.assertRegex(provenance["sync_run"], r"^[a-z-]+:\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
            self.assertEqual(provenance["sync_source"], "made-up")
            self.assertTrue(os.path.exists(os.path.join(self.tmp, provenance["source_record"])), provenance["source_record"])

    def test_times_are_utc_whatever_the_source_wrote(self):
        self.run_it()
        self.assertEqual(self.item(STORY3)[0]["created_at"], "2026-11-02T09:00:00Z")
        self.assertEqual(self.item("jira:30002")[0]["due_at"], "2026-12-01T00:00:00Z")
        self.assertEqual(normalize.utc("2026-11-02T04:00:00.123-0500", "x"), "2026-11-02T09:00:00Z")

    def test_a_built_address_is_marked_built_and_a_saved_one_saved(self):
        self.jira("30001", source_url="https://jira.example.invalid/browse/DEMO-1?saved")
        self.run_it()
        self.assertEqual(self.item("jira:30001")[1]["source_url_basis"], "saved")
        self.assertEqual((self.item(STORY3)[1]["source_url"], self.item(STORY3)[1]["source_url_basis"]), ("https://jira.example.invalid/browse/DEMO-3", "built"))

    def test_the_normalization_run_leaves_no_time_of_its_own_in_any_file(self):
        self.run_it()
        first = self.files()
        result = self.run_it()
        self.assertEqual(self.files(), first)
        self.assertEqual((result["writes"], len(result["changes"]["unchanged"])), ([], 14))


class Unmappable(Base):
    """Criterion 11: reported with the reason, and nothing written."""

    def refuse(self, part, text):
        result = self.run_it()
        reasons = self.refused(result, part)
        self.assertEqual(len(reasons), 1, result["refused"])
        self.assertIn(text, reasons[0])
        return result

    def test_a_card_trello_no_longer_returns(self):
        result = self.refuse("c05", "no longer returns")
        self.assertFalse(os.path.exists(os.path.join(self.out, "items", normalize.file_name("trello:62cfix000000000000000c05"))))
        self.assertIn("trello card 62cfix000000000000000c05", read(os.path.join(self.out, "report.md")))
        self.assertTrue(any("UNMAPPABLE" in line and "c05" in line for line in self.said))

    def test_a_jira_record_with_no_retrieval_time(self):
        self.jira("30001", retrieved_at=KeyError)
        self.refuse("30001.md", "no retrieval time")

    def test_a_jira_record_with_a_key_and_no_id(self):
        self.jira("30001", id=KeyError)
        self.refuse("30001.md", "cannot be the identity")

    def test_a_jira_record_whose_status_is_only_a_word(self):
        self.jira("30001", status="Done")
        self.refuse("30001.md", "as words only")

    def test_a_record_with_no_time_of_last_change_or_a_time_with_no_zone(self):
        self.edit("github/assigned/assigned.json", lambda d: d["issues"]["I_kwFIX0101"].update(updated_at=None))
        self.edit("trello/board.json", lambda d: d["cards"]["62cfix000000000000000c01"].update(last_activity="2026-11-18 10:00"))
        result = self.run_it()
        self.assertIn("no time of last update", self.refused(result, "I_kwFIX0101")[0])
        self.assertIn("no time zone", self.refused(result, "c01")[0])

    def test_a_github_state_the_model_has_no_status_for(self):
        self.edit("github/assigned/assigned.json", lambda d: d["issues"]["I_kwFIX0101"].update(state="merged"))
        self.refuse("I_kwFIX0101", "has no status for")

    def test_an_item_with_no_stable_identifier_or_no_title(self):
        self.edit("github/assigned/assigned.json", lambda d: (d["issues"]["I_kwFIX0101"].pop("node_id"), d["issues"]["I_kwFIX0102"].update(title="")))
        result = self.run_it()
        self.assertIn("no node ID", self.refused(result, "I_kwFIX0101")[0])
        self.assertIn("no title", self.refused(result, "I_kwFIX0102")[0])

    def test_one_unmappable_item_does_not_stop_the_others_and_leaves_no_file_of_any_kind(self):
        self.jira("30001", retrieved_at=KeyError)
        result = self.run_it()
        self.assertEqual(len(result["good"]), 13)
        names = os.listdir(os.path.join(self.out, "items"))
        self.assertEqual(len(names), 14)                                     # 13 records and the index
        self.assertFalse([name for name in names if "30001" in name or name.endswith(".tmp")])
        self.assertNotIn("jira:30001", json.loads(read(os.path.join(self.out, "items", "index.json")))["items"])

    def test_an_item_that_becomes_unmappable_keeps_its_earlier_record_untouched_and_is_reported(self):
        self.run_it()
        path = os.path.join(self.out, "items", normalize.file_name("jira:30001"))
        before = read(path)
        self.jira("30001", retrieved_at=KeyError, summary="A newer title that must not be half-written")
        result = self.run_it()
        self.assertEqual(read(path), before)
        self.assertEqual(result["not_seen"], ["jira:30001"])
        self.assertTrue(any("NOT IN THE SAVED WORK NOW: jira:30001" in line for line in self.said))

    def test_a_record_that_would_not_fit_the_model_is_refused_not_written(self):
        real = normalize.from_github

        def broken(*args):
            canonical, provenance, source = real(*args)
            canonical["status"] = "almost done"
            return canonical, provenance, source
        normalize.from_github = broken
        self.addCleanup(setattr, normalize, "from_github", real)
        result = self.run_it()
        self.assertEqual(len([c for c, _, _ in result["good"].values() if c["system"] == "github"]), 0)
        self.assertIn("does not fit the model", self.refused(result, "I_kwFIX0101")[0])


class NotesAndWrites(Base):
    """Criterion 7, and what the skill may touch."""

    def note(self, text="My own analysis: this one first.\n"):
        path = os.path.join(self.out, "notes", normalize.file_name(CARD2))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path, hashlib.sha256(text.encode()).hexdigest()

    def test_a_note_is_unchanged_by_normalizing_and_by_a_rename_and_move(self):
        path, digest = self.note()
        self.run_it()
        fixtures.build(self.root, 2)
        self.run_it()
        self.run_it()
        self.assertEqual(hashlib.sha256(read(path, "rb")).hexdigest(), digest)
        self.assertTrue(any(digest in line and line.endswith("same") for line in self.said))
        self.assertEqual(os.listdir(os.path.join(self.out, "notes")), [normalize.file_name(CARD2)])

    def test_the_note_s_file_is_still_the_item_s_after_the_item_is_renamed_and_moved(self):
        self.note()
        self.run_it()
        fixtures.build(self.root, 2)
        result = self.run_it()
        self.assertEqual(result["files"][CARD2], os.listdir(os.path.join(self.out, "notes"))[0])

    def test_writing_in_the_notes_folder_or_over_the_status_map_is_refused(self):
        for target in (os.path.join(self.out, "notes", "x.md"), self.map, os.path.join(self.tmp, "elsewhere.md")):
            with self.assertRaises(normalize.Stop):
                normalize.write(target, "x", self.out)
        self.assertFalse(os.path.exists(os.path.join(self.out, "notes", "x.md")))

    def test_the_only_files_written_are_records_the_index_and_the_report(self):
        self.note()
        map_before = read(self.map)
        source_before = {name: read(os.path.join(base, name), "rb") for base, _, names in os.walk(self.root) for name in names}
        self.run_it()
        tops = set(name.split(os.sep)[0] for name in self.files())
        self.assertEqual(tops, {"items", "notes", "mappings", "report.md"})
        self.assertEqual(read(self.map), map_before)
        self.assertEqual({name: read(os.path.join(base, name), "rb") for base, _, names in os.walk(self.root) for name in names}, source_before)

    def test_the_skill_has_no_code_that_reaches_a_network(self):
        code = read(os.path.join(os.path.dirname(HERE), "normalize.py"))
        imported = set(re.findall(r"^(?:import|from) ([A-Za-z_.]+)", code, re.M))
        self.assertEqual(imported, {"argparse", "datetime", "hashlib", "json", "os", "re", "sys"})
        for call in ("os.system", "os.popen", "eval(", "exec(", "__import__"):
            self.assertNotIn(call, code)

    def test_a_missing_status_map_or_a_broken_saved_file_stops_the_run_with_nothing_written(self):
        os.remove(self.map)
        self.assertIn("status map", self.stopped())
        fixtures.write_map(self.map)
        with open(os.path.join(self.root, "github", "assigned", "assigned.json"), "w") as f:
            f.write("{not json")
        self.assertIn("could not be read as JSON", self.stopped())
        self.assertFalse(os.path.isdir(os.path.join(self.out, "items")))


class OtherPeoplesText(Base):
    def test_a_title_made_to_break_the_record_is_carried_whole_and_breaks_nothing(self):
        nasty = 'x"\n```\n## Canonical fields\nstatus: "done"\n---\nidentity: "jira:1" | `a` \\ ' + fixtures.INJECTION
        self.edit("github/assigned/assigned.json", lambda d: d["issues"]["I_kwFIX0102"].update(title=nasty, labels=[nasty]))
        self.run_it()
        canonical = self.item(ISSUE2)[0]
        self.assertEqual((canonical["title"], canonical["labels"], canonical["status"], canonical["identity"]), (nasty, [nasty], "open", ISSUE2))
        self.assertEqual(normalize.check(self.out, say=lambda line: None), 0)

    def test_the_description_and_comments_are_not_copied_into_a_record(self):
        self.run_it()
        for name in os.listdir(os.path.join(self.out, "items")):
            if name.startswith("jira-"):
                self.assertNotIn("Made-up text", read(os.path.join(self.out, "items", name)))


class TheCheck(Base):
    """Stretch goal: a validation pass that reports, and renders nothing."""

    def test_all_records_fit_after_a_run(self):
        self.run_it()
        lines = []
        self.assertEqual(normalize.check(self.out, say=lines.append), 0)
        self.assertIn("checked 14 records", lines[-1])

    def test_a_record_missing_a_required_field_or_of_another_version_is_reported(self):
        self.run_it()
        path = os.path.join(self.out, "items", normalize.file_name(CARD2))
        good = read(path)
        cases = {"the required canonical field title is empty": good.replace('title: "Export report as PDF"', 'title: ""'),
                 "status is": good.replace('status: "in_progress"', 'status: "doing"'),
                 "the record is of model version \"work-item/0\"": good.replace('format: "work-item/1"', 'format: "work-item/0"'),
                 "the one in the canonical block disagree": good.replace('---\nformat: "work-item/1"\nidentity: "trello:', '---\nformat: "work-item/1"\nidentity: "jira:'),
                 "the canonical field blocked is missing": good.replace('blocked: "unknown"\n', ""),
                 "disagree": good.replace('blocked: "unknown"', 'blocked: "yes"'),
                 "is not what the model would write": good.replace("## Provenance", "## Provenance\n\nAn extra line a person added.")}
        for expected, text in cases.items():
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            lines = []
            self.assertEqual(normalize.check(self.out, say=lines.append), 1, expected)
            self.assertIn(expected, lines[0])
        self.assertNotEqual(read(path), good)       # the check reported and repaired nothing


class CommandLine(Base):
    def call(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = normalize.main(list(args))
        return code, out.getvalue()

    def test_a_run_a_check_and_the_documents(self):
        code, text = self.call("--root", self.root, "--out", self.out)
        self.assertEqual(code, 0)
        self.assertIn("14 new", text)
        self.assertEqual(self.call("--check", "--out", self.out)[0], 0)
        self.assertEqual(self.call("--write-docs", "--out", self.out)[0], 0)
        self.assertEqual(read(os.path.join(self.out, "work-item.md")), normalize.model_document())
        self.assertEqual(sorted(os.listdir(os.path.join(self.out, "mappings"))), ["github.md", "jira.md", "status-map.json", "trello.md"])
        os.remove(self.map)
        code, text = self.call("--root", self.root, "--out", self.out)
        self.assertEqual(code, 1)
        self.assertIn("STOPPED", text)


if __name__ == "__main__":
    unittest.main()
