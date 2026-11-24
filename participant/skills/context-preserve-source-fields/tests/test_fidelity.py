"""Tests for the context-preserve-source-fields skill. They use the made-up records in participant/context/fidelity. Nothing is written there."""
import json
import os
import re
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import fidelity      # noqa: E402

CARD, STORY, ISSUE = "trello 62c0000000000000000000a1", "jira 10042", "github I_kwFIX0201"


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class Base(unittest.TestCase):
    def setUp(self):
        self.sources = read(os.path.join(fidelity.FOLDER, "source-records.md"))
        self.status_map = fidelity.status_map_of(self.sources)
        self.records = {heading: (system, block) for heading, system, block in fidelity.source_records(self.sources)}

    def normalized(self, version=fidelity.LATEST, sources=None):
        sources = self.sources if sources is None else sources
        return fidelity.render([fidelity.normalize_one(h, s, b, fidelity.status_map_of(sources), version) for h, s, b in fidelity.source_records(sources)], version)

    def check(self, normalized, sources=None):
        said = []
        code = fidelity.check(self.sources if sources is None else sources, normalized, said.append)
        return code, said

    def one(self, heading, version=fidelity.LATEST):
        system, block = self.records[heading]
        return fidelity.normalize_one(heading, system, block, self.status_map, version)

    def broken(self, old, new, expected, count=1):
        text = self.normalized()
        self.assertEqual(text.count(old), count, old)
        code, said = self.check(text.replace(old, new))
        self.assertNotEqual(code, 0)
        self.assertTrue(any(expected in line for line in said), "expected %r in %r" % (expected, [line for line in said if "RESULT" not in line and "PRESERVED IN" not in line]))
        return said


class TheFilesAsHandedIn(Base):
    def test_the_normalized_file_is_what_the_code_writes_from_the_sources(self):
        self.assertEqual(read(os.path.join(fidelity.FOLDER, "normalized.md")), self.normalized())

    def test_the_rationale_is_what_the_code_writes(self):
        self.assertEqual(read(os.path.join(fidelity.FOLDER, "mapping-rationale.md")), fidelity.rationale_document())

    def test_three_systems_two_records_each_and_each_system_has_fields_the_others_lack(self):
        systems = [system for system, _ in self.records.values()]
        self.assertEqual(sorted(systems), ["github", "github", "jira", "jira", "trello", "trello"])
        names = {system: set(path for h, (s, b) in self.records.items() if s == system for path, raw in fidelity.fields_of(s, b) if raw is not None) for system in fidelity.SYSTEMS}
        for system in fidelity.SYSTEMS:
            others = set().union(*(names[other] for other in fidelity.SYSTEMS if other != system))
            self.assertGreaterEqual(len(names[system] - others), 8, system)


class Canonical(Base):
    """Criterion 1."""

    def test_every_record_has_the_same_canonical_names(self):
        wanted = [name for name, _, _ in fidelity.CANONICAL]
        for heading in self.records:
            self.assertEqual(list(self.one(heading)["canonical"]), wanted, heading)

    def test_the_canonical_values(self):
        story, card, issue = self.one(STORY)["canonical"], self.one(CARD)["canonical"], self.one(ISSUE)["canonical"]
        self.assertEqual((story["identity"], story["title"], story["status"], story["assignee_count"], story["labels"], story["due_at"], story["source_updated_at"]),
                         ("jira:10042", "Fix the café export", "in_progress", 1, ["export", "q4-2026"], "2026-12-01T00:00:00Z", "2026-11-17T09:30:00Z"))
        self.assertEqual((card["identity"], card["title"], card["status"], card["assignee_count"], card["labels"], card["due_at"]),
                         ("trello:62c0000000000000000000a1", "Export report as PDF  ", "in_progress", 2, ["feature", ""], "2026-12-04T17:00:00Z"))
        self.assertEqual((issue["identity"], issue["status"], issue["assignee_count"], issue["labels"], issue["due_at"], issue["reference"]),
                         ("github:I_kwFIX0201", "open", 1, ["backend"], None, 12))
        self.assertEqual([self.one(h)["canonical"]["status"] for h in ("jira 10043", "trello 62c0000000000000000000a2", "github I_kwFIX0202")], ["dropped"] * 3)

    def test_a_status_is_one_of_four_values(self):
        for heading in self.records:
            self.assertIn(self.one(heading)["canonical"]["status"], fidelity.STATUSES)


class Preserved(Base):
    """Criteria 2 and 3."""

    def test_every_source_field_is_preserved_or_given_back_by_a_canonical_field(self):
        for heading, (system, block) in self.records.items():
            record = self.one(heading)
            fields = [path for path, raw in fidelity.fields_of(system, block) if raw is not None]
            covered = [path for path, _ in record["preserved"]] + list(record["rebuilt_from_canonical"])
            self.assertEqual(sorted(covered), sorted(fields), heading)

    def test_a_preserved_value_is_the_source_s_own_characters(self):
        for heading, (system, block) in self.records.items():
            raw = dict(fidelity.fields_of(system, block))
            for path, kept in self.one(heading)["preserved"]:
                self.assertEqual(kept, raw[path], "%s %s" % (heading, path))
                self.assertIn("%s: %s" % (json.dumps(path.split(".")[-1]), kept), block)

    def test_the_awkward_values_arrive_untouched(self):
        text = self.normalized()
        for line in ("fields.customfield_10016: 3.0", "pos: 1e3", "pos: 65535.5", 'fields.summary: "Fix the caf\\u00e9 export"', 'fields.description: ""', "fields.assignee: null",
                     'idChecklists: ["65f0000000000000000000c2", "65f0000000000000000000c1"]', 'body: "Not worth it. \\ud83d\\udeab"', "fields.timetracking: {}",
                     'fields.description: "The weekly export fails for any team with zero rows.\\n\\nSee the runbook.  "'):
            self.assertIn("\n%s\n" % line, text, line)

    def test_the_scenario_s_custom_field_is_preserved_whole(self):
        kept = dict(self.one(CARD)["preserved"])["customFieldItems"]
        self.assertIn("High: 3 enterprise accounts are waiting", kept)
        self.assertIn('{"number": "3.0"}', kept)

    def test_a_translated_field_is_preserved_as_well_as_mapped(self):
        kept = dict(self.one(STORY)["preserved"])
        self.assertIn('"name": "In Review"', kept["fields.status"])
        self.assertEqual(kept["fields.duedate"], '"2026-12-01"')
        self.assertEqual(dict(self.one(CARD)["preserved"])["due"], '"2026-12-04T17:00:00.000Z"')

    def test_a_copied_field_is_not_stored_twice_unless_copying_would_lose_a_character(self):
        self.assertNotIn("fields.summary", dict(self.one("jira 10043")["preserved"]))
        self.assertEqual(self.one("jira 10043")["rebuilt_from_canonical"]["fields.summary"], "title")
        self.assertIn("fields.summary", dict(self.one(STORY)["preserved"]))            # sent with an escape: the canonical value would not write back the same
        self.assertNotIn("fields.summary", self.one(STORY)["rebuilt_from_canonical"])
        self.assertEqual(self.one(ISSUE)["rebuilt_from_canonical"]["updated_at"], "source_updated_at")
        self.assertIn("fields.updated", dict(self.one(STORY)["preserved"]))

    def test_an_empty_string_null_and_a_missing_field_stay_three_different_things(self):
        second = dict(self.one("jira 10043")["preserved"])
        self.assertEqual((second["fields.description"], second["fields.assignee"]), ('""', "null"))
        self.assertNotIn("fields.parent", second)
        self.assertNotIn("fields.parent", self.one("jira 10043")["field_order"])

    def test_a_field_the_mapping_has_never_heard_of_is_preserved_and_reported(self):
        sources = self.sources.replace('  "pos": 65535.5,\n', '  "pos": 65535.5,\n  "customerTier": "gold",\n')
        text = self.normalized(sources=sources)
        self.assertIn('\ncustomerTier: "gold"\n', text)
        code, said = self.check(text, sources)
        self.assertEqual(code, 0)
        self.assertTrue(any("NOTE: the field trello customerTier is not in the mapping's list" in line for line in said))


class RoundTrip(Base):
    """Criteria 4, 5 and 6."""

    def test_every_record_rebuilds_to_the_original_character_for_character(self):
        records = {record["source_record"]: record for record in fidelity.normalized_records(self.normalized())}
        for heading, (system, block) in self.records.items():
            rebuilt, missing = fidelity.rebuild(system, records[heading])
            self.assertEqual((rebuilt, missing), (block, []), heading)
        code, said = self.check(self.normalized())
        self.assertEqual(code, 0)
        self.assertEqual(len([line for line in said if "identical to the original, character for character" in line]), 6)

    def test_the_rebuild_uses_only_the_normalized_file(self):
        text = self.normalized()
        for heading, (system, block) in self.records.items():
            record = [one for one in fidelity.normalized_records(text) if one["source_record"] == heading][0]
            self.assertEqual(fidelity.rebuild(system, record)[0], block)

    def test_a_dropped_preserved_field_is_reported_by_name(self):
        line = [one for one in self.normalized().split("\n") if one.startswith("customFieldItems: [{")][0]
        said = self.broken(line + "\n", "", "MISSING FIELD: customFieldItems is in the source record and cannot be rebuilt")
        self.assertEqual(len([one for one in said if "NOT IDENTICAL" in one]), 1)

    def test_a_dropped_field_of_each_kind_is_reported(self):
        self.broken('fields.status: {"id": "10003"', 'xfields.status: {"id": "10003"', "MISSING FIELD: fields.status")
        self.broken('"key": "reference", ', "", "MISSING FIELD: key", count=2)
        self.broken('\nreference: "DEMO-42"\n', "\n", "MISSING FIELD: key")

    def test_a_reformatted_value_is_reported(self):
        self.broken("fields.customfield_10016: 3.0", "fields.customfield_10016: 3", "CHANGED FIELD: fields.customfield_10016 was preserved as 3 and the source sent 3.0")
        self.broken("pos: 1e3", "pos: 1000.0", "CHANGED FIELD: pos")
        self.broken('fields.summary: "Fix the caf\\u00e9 export"', 'fields.summary: "Fix the café export"', "CHANGED FIELD: fields.summary")
        self.broken('"2026-11-17T09:30:00.000+0000"', '"2026-11-17T09:30:00Z"', "CHANGED FIELD: fields.updated")
        self.broken('See the runbook.  "', 'See the runbook."', "CHANGED FIELD: fields.description")
        self.broken('"key": "indeterminate", "name": "In Progress"}}', '"key":"indeterminate","name":"In Progress"}}', "CHANGED FIELD: fields.status")

    def test_a_reordered_list_or_a_summarised_value_is_reported(self):
        self.broken('idChecklists: ["65f0000000000000000000c2", "65f0000000000000000000c1"]', 'idChecklists: ["65f0000000000000000000c1", "65f0000000000000000000c2"]', "CHANGED FIELD: idChecklists")
        self.broken('{"text": "High: 3 enterprise accounts are waiting"}', '{"text": "High"}', "CHANGED FIELD: customFieldItems")
        self.broken('fields.description: ""', "fields.description: null", "CHANGED FIELD: fields.description")

    def test_a_changed_canonical_value_that_a_field_is_rebuilt_from_is_reported(self):
        self.broken('title: "Export report as PDF  "', 'title: "Export report as PDF"', "CHANGED FIELD: name is rebuilt from the canonical field title")
        self.broken('labels: ["export", "q4-2026"]', 'labels: ["q4-2026", "export"]', "CHANGED FIELD: fields.labels is rebuilt from the canonical field labels")

    def test_a_changed_field_order_and_an_extra_field_are_reported(self):
        self.broken('field_order: ["id", "key", "self", ', 'field_order: ["key", "id", "self", ', "ORDER: the fields are all there", count=2)
        self.broken("pos: 1e3\n", 'pos: 1e3\ninvented: "x"\n', "EXTRA FIELD: invented is preserved and not in the source record")

    def test_a_missing_or_an_extra_record_is_reported(self):
        text = self.normalized()
        cut = text[:text.index("## github:I_kwFIX0202")]
        code, said = self.check(cut)
        self.assertTrue(code and any("github I_kwFIX0202: NOT IDENTICAL" in line for line in said) and any("MISSING RECORD" in line for line in said))
        fewer = self.sources[:self.sources.index("### github I_kwFIX0202")]
        code, said = self.check(text, fewer)
        self.assertTrue(code and any("a normalized record with no source record" in line for line in said))

    def test_a_changed_source_record_is_reported_too(self):
        code, said = self.check(self.normalized(), self.sources.replace('"pos": 65535.5', '"pos": 65535.50'))
        self.assertTrue(code and any("CHANGED FIELD: pos was preserved as 65535.5 and the source sent 65535.50" in line for line in said))

    def test_a_check_with_nothing_to_check_does_not_pass(self):
        code, said = self.check("# no records here either\n", "# nothing here\n")
        self.assertNotEqual(code, 0)
        self.assertIn("There is nothing to check", said[-1])


class Rationale(Base):
    """Criterion 7."""

    def test_every_field_in_the_source_records_is_in_the_list_of_fields_considered_with_a_reason(self):
        for heading, (system, block) in self.records.items():
            listed = {path: reason for path, _, _, reason, _ in fidelity.CONSIDERED[system]}
            for path, raw in fidelity.fields_of(system, block):
                if raw is not None:
                    self.assertGreater(len(listed.get(path, "")), 25, "%s %s" % (heading, path))

    def test_every_listed_field_has_one_of_three_outcomes_and_a_canonical_field_only_if_mapped(self):
        names = [name for name, _, _ in fidelity.CANONICAL]
        for system in fidelity.SYSTEMS:
            paths = [row[0] for row in fidelity.CONSIDERED[system]]
            self.assertEqual(len(paths), len(set(paths)))
            for path, outcome, canonical, _, _ in fidelity.CONSIDERED[system]:
                self.assertIn(outcome, ("copied", "translated", "preserved"))
                self.assertEqual(canonical is None, outcome == "preserved", path)
                if canonical:
                    self.assertIn(canonical, names)

    def test_the_document_lists_every_field_and_says_how_a_field_is_decided(self):
        text = fidelity.rationale_document()
        for system in fidelity.SYSTEMS:
            for path, _, _, reason, _ in fidelity.CONSIDERED[system]:
                self.assertIn("| `%s` |" % path, text)
                self.assertIn(reason, text)
        for phrase in ("preserve first, promote later", "More than one system has it", "## The mapping's versions"):
            self.assertIn(phrase, text)


class Stretch(Base):
    def test_preserved_fields_that_more_than_one_system_has_are_reported(self):
        code, said = self.check(self.normalized())
        shared = [line for line in said if "PRESERVED IN MORE THAN ONE SYSTEM" in line]
        self.assertTrue(any("description: jira `fields.description`, trello `desc`, github `body`" in line for line in shared))
        self.assertTrue(any("created: jira `fields.created`, github `created_at`" in line for line in shared))
        self.assertFalse(any("customFieldItems" in line for line in shared))
        self.assertFalse(any("estimate" in line for line in shared))                  # only Jira has one here

    def test_both_versions_of_the_mapping_rebuild_the_same_originals(self):
        first, second = self.normalized(1), self.normalized(2)
        self.assertNotEqual(first, second)
        self.assertNotIn("\ndue_at:", first)
        self.assertIn('\ndue_at: "2026-12-01T00:00:00Z"\n', second)
        self.assertEqual(self.check(first)[0], 0)
        self.assertEqual(self.check(second)[0], 0)
        strip = lambda text: re.findall(r"### Preserved source fields.*?```text\n(.*?)```", text, re.S)
        self.assertEqual(strip(first), strip(second))


class CommandLine(Base):
    def test_normalize_check_and_a_stop(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        out = os.path.join(tmp, "normalized.md")
        said = []
        self.assertEqual(fidelity.main(["normalize", "--out", out], say=said.append), 0)
        self.assertEqual(read(out), self.normalized())
        self.assertEqual(fidelity.main(["check", "--normalized", out], say=said.append), 0)
        with open(out, "w", encoding="utf-8") as f:
            f.write(self.normalized().replace("pos: 1e3", "pos: 1000"))
        self.assertEqual(fidelity.main(["check", "--normalized", out], say=said.append), 2)
        self.assertEqual(fidelity.main(["check", "--normalized", os.path.join(tmp, "none.md")], say=said.append), 1)

    def test_the_skill_reaches_no_network_and_check_writes_nothing(self):
        code = read(os.path.join(os.path.dirname(HERE), "fidelity.py"))
        self.assertEqual(set(re.findall(r"^(?:import|from) ([A-Za-z_.]+)", code, re.M)), {"argparse", "datetime", "json", "os", "re", "sys"})
        before = {name: read(os.path.join(fidelity.FOLDER, name)) for name in sorted(os.listdir(fidelity.FOLDER))}
        fidelity.main(["check"], say=lambda line: None)
        self.assertEqual({name: read(os.path.join(fidelity.FOLDER, name)) for name in sorted(os.listdir(fidelity.FOLDER))}, before)


if __name__ == "__main__":
    unittest.main()
