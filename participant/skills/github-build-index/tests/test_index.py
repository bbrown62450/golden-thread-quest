"""Tests for the github-build-index skill. They read and write local files in a scratch folder. Nothing is contacted."""
import contextlib
import io
import os
import re
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, SKILL)
import index  # noqa: E402
import make_records  # noqa: E402

T, W = "acme-fixture/tracker", "acme-fixture/website"
# What the eleven made-up records hold, written out here by hand, apart from the generator.
EXPECTED = {
    (T, 12): ("open", ["bug"], "Sprint 12: exports", ["robin-fixture"]),
    (T, 13): ("closed", ["docs"], "Sprint 12: exports", ["sam-fixture"]),
    (T, 17): ("open", ["bug", "enhancement"], "Sprint 13", ["robin-fixture", "kit-fixture"]),
    (T, 21): ("open", [], None, []),
    (T, 30): ("open", ["enhancement"], None, ["kit-fixture"]),
    (W, 3): ("closed", ["bug"], "Launch", ["sam-fixture"]),
    (W, 4): ("open", ["enhancement", "good first issue"], "Launch", ["kit-fixture"]),
    (W, 5): ("open", ["bug", "good first issue"], "Launch", []),
    (W, 8): ("open", ["docs"], None, ["robin-fixture"]),
    (W, 9): ("open", [], "Sprint 13", ["sam-fixture", "robin-fixture"]),
    (W, 11): ("closed", ["docs"], "Launch", ["kit-fixture"]),
}


def file_of(repo, number):
    return "%s__issue-%d.md" % (repo.replace("/", "__"), number)


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = self._tmp.name
        self.records, self.out = os.path.join(self.dir, "issues"), os.path.join(self.dir, "index.md")
        for made in make_records.all_records():
            make_records.write(self.records, made)

    def run_it(self, *argv):
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            code = index.main(list(argv) + ["--records", self.records, "--out", self.out])
        return code, printed.getvalue()

    def build(self):
        return self.run_it("build")

    def text(self):
        with open(self.out, encoding="utf-8") as f:
            return f.read()

    def path(self, repo=T, number=12):
        return os.path.join(self.records, file_of(repo, number))

    def edit(self, old, new, repo=T, number=12, count=1):
        with open(self.path(repo, number), encoding="utf-8") as f:
            text = f.read()
        self.assertEqual(text.count(old), count, old)
        with open(self.path(repo, number), "w", encoding="utf-8") as f:
            f.write(text.replace(old, new))

    def put(self, name, text):
        with open(os.path.join(self.records, name), "wb") as f:
            f.write(text if isinstance(text, bytes) else text.encode("utf-8"))

    def table(self):
        lines = self.text().split("\n")
        start = lines.index("|---|---:|---|---|---|---|---|---|---|")
        return [line for line in lines[start + 1:lines.index("", start)]]

    def found(self, *argv):
        """The repository#number of every line a lookup or a search printed."""
        code, printed = self.run_it(*argv)
        return code, sorted(re.findall(r"^github-index:   (\S+#\d+)", printed, re.M)), printed


class Generated(Base):
    """Criterion 1: the index is generated, never hand-edited."""

    def test_a_hand_edit_is_found_by_the_check(self):
        self.build()
        with open(self.out, "a", encoding="utf-8") as f:
            f.write("\nA note somebody added by hand.\n")
        code, printed = self.run_it("check")
        self.assertEqual(code, 3)
        self.assertIn("RESULT: EDITED BY HAND", printed)
        self.assertNotIn("STALE", printed)

    def test_the_check_says_which_line_was_edited(self):
        self.build()
        lines = self.text().split("\n")
        row = next(number for number, line in enumerate(lines) if "| 12 |" in line)
        lines[row] = lines[row].replace("| open |", "| closed |")
        with open(self.out, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        code, printed = self.run_it("check")
        self.assertEqual(code, 3)
        self.assertIn("The first line that differs is line %d." % (row + 1), printed)

    def test_a_hand_edit_to_the_fingerprint_line_is_still_a_hand_edit(self):
        self.build()
        text = self.text()
        mark = re.search(r"fingerprint of the records: `(\w+)`", text).group(1)
        with open(self.out, "w", encoding="utf-8") as f:
            f.write(text.replace(mark, "0" * 64))
        self.assertIn("RESULT: EDITED BY HAND", self.run_it("check")[1])

    def test_a_build_keeps_nothing_of_a_hand_edit(self):
        self.build()
        clean = self.text()
        with open(self.out, "w", encoding="utf-8") as f:
            f.write(clean.replace("| open |", "| closed |") + "\n## A section added by hand\n")
        code, printed = self.build()
        self.assertEqual(code, 0)
        self.assertIn("What was there before was not kept", printed)
        self.assertEqual(self.text(), clean)
        self.assertEqual(self.run_it("check")[0], 0)

    def test_a_build_writes_over_a_file_that_was_never_an_index(self):
        with open(self.out, "w") as f:
            f.write("my own notes\n")
        self.build()
        self.assertNotIn("my own notes", self.text())

    def test_no_half_written_file_is_left(self):
        self.build()
        self.assertEqual(sorted(os.listdir(self.dir)), ["index.md", "issues"])

    def test_the_records_are_never_written_to(self):
        before = {name: os.stat(os.path.join(self.records, name)).st_mtime_ns for name in os.listdir(self.records)}
        for argv in (("build",), ("check",), ("lookup", "label", "bug"), ("find", "footer")):
            self.run_it(*argv)
        self.assertEqual({name: os.stat(os.path.join(self.records, name)).st_mtime_ns for name in os.listdir(self.records)}, before)
        with open(os.path.join(SKILL, "index.py"), encoding="utf-8") as f:
            code = f.read()
        self.assertEqual(code.count('"wb"'), 1)
        self.assertNotIn('"w"', code)
        for word in ("urllib.request", "socket", "subprocess", "os.system", "os.remove", "shutil"):
            self.assertNotIn(word, code)


class EveryRecordOnce(Base):
    """Criterion 2: every local record appears once."""

    def test_the_table_has_one_row_for_each_file_and_no_file_twice(self):
        self.build()
        files = sorted(os.listdir(self.records))
        linked = sorted(re.search(r"\]\(issues/([^)]*)\) \| \w{12} \|$", row).group(1) for row in self.table())
        self.assertEqual(linked, files)
        self.assertEqual(len(set(linked)), 11)

    def test_each_row_holds_what_the_record_holds(self):
        self.build()
        rows = {}
        for row in self.table():
            cells = [part.strip() for part in row.strip("|").split(" | ")]
            rows[(cells[0], int(cells[1]))] = (cells[3], cells[4], cells[5], cells[6])
        self.assertEqual(sorted(rows), sorted(EXPECTED))
        for key, (state, labels, milestone, people) in EXPECTED.items():
            self.assertEqual(rows[key], (state, ", ".join(labels) or "*none*", milestone or "*none*", ", ".join(people) or "*none*"), key)

    def test_the_build_counts_and_says_so(self):
        code, printed = self.build()
        self.assertEqual(code, 0)
        self.assertIn("Record files found: 11", printed)
        self.assertIn("count check: the index has 11 rows for 11 files (11 indexed and 0 that could not be), and no file has two rows", printed)
        self.assertIn("- record files found: 11\n- indexed, one row each: 11\n", self.text())

    def test_a_file_that_is_not_a_record_is_counted_and_not_dropped(self):
        self.put("notes.md", "# my notes\n")
        code, printed = self.build()
        self.assertEqual(code, 3)
        self.assertIn("COULD NOT BE INDEXED: notes.md: it has no front matter", printed)
        self.assertIn("the index has 12 rows for 12 files (11 indexed and 1 that could not be)", printed)
        text = self.text()
        self.assertIn("- record files found: 12\n- indexed, one row each: 11\n- of those, with a gap: 0\n- could not be indexed: 1\n", text)
        self.assertEqual(len(self.table()), 11)
        self.assertIn("| it has no front matter, so it is not an issue record | [notes.md](issues/notes.md) |", text)

    def test_every_kind_of_file_that_is_not_a_record_gets_its_reason(self):
        with open(self.path(), encoding="utf-8") as f:
            good = f.read()
        self.put("a.md", b"\xff\xfe not text")
        self.put("b.md", "")
        self.put("c.md", good.replace('format: "github-issue-markdown/1"', 'format: "something-else/9"'))
        self.put("d.md", "---\nnever closed\n")
        self.put("e.md", good.replace('format: "github-issue-markdown/1"\n', ""))
        code, printed = self.build()
        self.assertEqual(code, 3)
        for name, why in (("a.md", "not UTF-8"), ("b.md", "no front matter"), ("c.md", "not in the format"), ("d.md", "no front matter"), ("e.md", "not in the format")):
            self.assertIn("COULD NOT BE INDEXED: %s: it" % name, printed)
            self.assertIn(why, [line for line in printed.splitlines() if name in line][0])
        self.assertIn("16 rows for 16 files (11 indexed and 5 that could not be)", printed)

    def test_one_issue_in_two_files_keeps_both_rows_and_is_flagged(self):
        shutil.copy(self.path(), os.path.join(self.records, "an-older-copy.md"))
        code, printed = self.build()
        self.assertEqual(code, 3)
        self.assertIn("SAME ISSUE IN 2 FILES: acme-fixture/tracker#12: acme-fixture__tracker__issue-12.md, an-older-copy.md", printed)
        self.assertEqual(len(self.table()), 12)
        self.assertIn("- issues held in more than one file: 1", self.text())
        self.assertIn("- acme-fixture/tracker#12: `acme-fixture\\_\\_tracker\\_\\_issue-12.md`, `an-older-copy.md`", self.text())

    def test_folders_hidden_files_and_other_kinds_of_file_are_not_records(self):
        os.makedirs(os.path.join(self.records, "notes"))
        self.put(os.path.join("notes", "inside.md"), "x")
        self.put(".hidden.md", "x")
        self.put("readme.txt", "x")
        code, printed = self.build()
        self.assertEqual(code, 0)
        self.assertIn("Record files found: 11", printed)

    def test_an_index_that_would_miss_a_row_is_not_written(self):
        real = index.render
        index.render = lambda *args: "\n".join(line for line in real(*args).split("\n") if "| 21 |" not in line)
        self.addCleanup(setattr, index, "render", real)
        code, printed = self.build()
        self.assertEqual(code, 1)
        self.assertIn("does not have exactly one row for each record file. It was not written", printed)
        self.assertFalse(os.path.exists(self.out))

    def test_an_index_whose_counts_are_wrong_is_not_written(self):
        real = index.render
        index.render = lambda *args: real(*args).replace("- record files found: 11", "- record files found: 10")
        self.addCleanup(setattr, index, "render", real)
        self.assertEqual(self.build()[0], 1)
        self.assertFalse(os.path.exists(self.out))

    def test_an_empty_folder_gives_an_empty_index_and_a_missing_one_stops(self):
        shutil.rmtree(self.records)
        self.assertIn("there is no records folder", self.build()[1])
        os.makedirs(self.records)
        code, printed = self.build()
        self.assertEqual(code, 0)
        self.assertIn("the index has 0 rows for 0 files", printed)


class Lookups(Base):
    """Criterion 3: lookup by repository, label, milestone and assignee works from the index."""

    def expect(self, test):
        return sorted("%s#%d" % key for key, value in EXPECTED.items() if test(key, *value))

    def test_by_repository(self):
        self.build()
        for repo in (T, W):
            code, got, _ = self.found("lookup", "repository", repo)
            self.assertEqual((code, got), (0, self.expect(lambda key, *rest: key[0] == repo)))

    def test_by_label(self):
        self.build()
        for name in ("bug", "docs", "enhancement", "good first issue"):
            code, got, printed = self.found("lookup", "label", name)
            self.assertEqual((code, got), (0, self.expect(lambda key, state, labels, *rest: name in labels)), name)
            self.assertIn('RESULT: records with the label "%s": %d' % (name, len(got)), printed)

    def test_by_milestone(self):
        self.build()
        for title in ("Sprint 12: exports", "Sprint 13", "Launch"):
            code, got, _ = self.found("lookup", "milestone", title)
            self.assertEqual((code, got), (0, self.expect(lambda key, state, labels, milestone, people: milestone == title)), title)

    def test_by_assignee(self):
        self.build()
        for login in ("robin-fixture", "sam-fixture", "kit-fixture"):
            code, got, _ = self.found("lookup", "assignee", login)
            self.assertEqual((code, got), (0, self.expect(lambda key, state, labels, milestone, people: login in people)), login)

    def test_the_ones_that_have_none(self):
        self.build()
        self.assertEqual(self.found("lookup", "label", "--none")[1], self.expect(lambda key, state, labels, *rest: not labels))
        self.assertEqual(self.found("lookup", "milestone", "--none")[1], self.expect(lambda key, state, labels, milestone, people: milestone is None))
        self.assertEqual(self.found("lookup", "assignee", "--none")[1], self.expect(lambda key, state, labels, milestone, people: not people))

    def test_every_record_is_under_exactly_one_repository_and_one_milestone(self):
        self.build()
        for kind in ("repository", "milestone"):
            _, printed = self.run_it("lookup", kind, "--list")
            self.assertEqual(sum(int(count) for count in re.findall(r"^github-index:   .*: (\d+)$", printed, re.M)), 11, kind)

    def test_capitals_do_not_matter(self):
        self.build()
        self.assertEqual(self.found("lookup", "label", "BUG")[1], self.found("lookup", "label", "bug")[1])
        self.assertEqual(len(self.found("lookup", "assignee", "Robin-Fixture")[1]), 4)

    def test_a_value_the_index_does_not_have_finds_nothing_and_says_so(self):
        self.build()
        code, got, printed = self.found("lookup", "label", "wontfix")
        self.assertEqual((code, got), (1, []))
        self.assertIn("The index has no such label", printed)

    def test_the_list_shows_every_value_with_its_count(self):
        self.build()
        _, printed = self.run_it("lookup", "label", "--list")
        for line in ("  bug: 4", "  docs: 3", "  enhancement: 3", "  good first issue: 2", "  (no label): 2"):
            self.assertIn("github-index: " + line + "\n", printed)
        self.assertIn("RESULT: 5 label values in the index", printed)

    def test_the_lookup_reads_the_index_and_not_the_records(self):
        self.build()
        shutil.rmtree(self.records)
        code, got, printed = self.found("lookup", "label", "docs")
        self.assertEqual((code, len(got)), (0, 3))
        self.assertIn("looking in the INDEX", printed)

    def test_a_label_with_odd_characters_can_be_looked_up_and_one_named_like_a_special_group_is_kept_apart(self):
        self.edit('labels: ["bug"]', 'labels: ["needs: triage [export] | `urgent`", "(no label)", "bug"]')
        self.build()
        self.assertEqual(self.found("lookup", "label", "needs: triage [export] | `urgent`")[1], ["acme-fixture/tracker#12"])
        self.assertEqual(self.found("lookup", "label", "(no label)")[1], ["acme-fixture/tracker#12"])
        self.assertEqual(len(self.found("lookup", "label", "--none")[1]), 2)

    def test_a_lookup_needs_an_index_a_kind_and_a_value(self):
        self.assertIn("Build it first", self.run_it("lookup", "label", "bug")[1])
        self.build()
        self.assertEqual(self.run_it("lookup", "colour", "red")[0], 1)
        self.assertEqual(self.run_it("lookup", "label")[0], 1)
        self.assertEqual(self.run_it("lookup", "repository", "--none")[0], 1)


class Gaps(Base):
    """Criterion 4: a record with a missing field is listed as a gap."""

    def test_a_missing_milestone_line_is_a_gap_and_the_record_keeps_its_row(self):
        self.edit('milestone: "Sprint 12: exports"\n', "")
        code, printed = self.build()
        self.assertEqual(code, 3)
        self.assertIn("GAP: acme-fixture__tracker__issue-12.md: the field `milestone`: the line is missing", printed)
        row = next(line for line in self.table() if "| 12 |" in line)
        self.assertIn("| bug | **GAP** | robin-fixture |", row)
        self.assertEqual(len(self.table()), 11)
        text = self.text()
        self.assertIn("- of those, with a gap: 1", text)
        self.assertIn("## Gaps (1)", text)
        self.assertIn("- [acme-fixture\\_\\_tracker\\_\\_issue-12.md](issues/acme-fixture__tracker__issue-12.md): `milestone`: the line is missing", text)

    def test_no_milestone_is_not_a_gap(self):
        code, _ = self.build()
        self.assertEqual(code, 0)
        self.assertIn("## Gaps (0)\n\nA field a record should have", self.text())
        self.assertIn("| enhancement | *none* | kit-fixture |", self.text())
        self.assertNotIn("**GAP**", "\n".join(self.table()))

    def test_a_record_with_a_gap_is_looked_up_under_gap_and_not_under_none(self):
        self.edit('milestone: "Sprint 12: exports"\n', "")
        self.build()
        self.assertEqual(self.found("lookup", "milestone", "--gap")[1], ["acme-fixture/tracker#12"])
        self.assertNotIn("acme-fixture/tracker#12", self.found("lookup", "milestone", "--none")[1])
        self.assertNotIn("acme-fixture/tracker#12", self.found("lookup", "milestone", "Sprint 12: exports")[1])
        self.assertIn("acme-fixture/tracker#12", self.found("lookup", "label", "bug")[1])
        self.assertIn("acme-fixture/tracker#12", self.found("lookup", "assignee", "robin-fixture")[1])

    def test_a_line_that_cannot_be_read_is_a_gap(self):
        self.edit('labels: ["bug"]', 'labels: ["bug"')
        _, printed = self.build()
        self.assertIn("the field `labels`: the line is there and cannot be read", printed)
        self.assertEqual(self.found("lookup", "label", "--gap")[1], ["acme-fixture/tracker#12"])

    def test_a_field_of_the_wrong_kind_is_a_gap(self):
        for old, new, field in (('labels: ["bug"]', 'labels: "bug"', "labels"), ('assignees: ["robin-fixture"]', "assignees: [7]", "assignees"),
                                ('state: "open"', "state: null", "state"), ('milestone: "Sprint 12: exports"', "milestone: 3", "milestone"),
                                ('title: "Import fails on an empty file"', "title: null", "title")):
            self.setUp()
            self.edit(old, new)
            code, printed = self.build()
            self.assertEqual(code, 3, field)
            self.assertIn("the field `%s`: it does not hold" % field, printed)

    def test_a_record_without_its_number_or_repository_still_has_a_row(self):
        self.edit("number: 12\n", "")
        self.edit('repository: "acme-fixture/website"', 'repository: "not a repository"', repo=W, number=3)
        code, printed = self.build()
        self.assertEqual(code, 3)
        table = self.table()
        self.assertEqual(len(table), 11)
        self.assertTrue(table[-1].startswith("| **GAP** | 3 |"), table[-1])
        self.assertIn("| acme-fixture/tracker | **GAP** | Import fails on an empty file |", "\n".join(table))
        self.assertIn("## Gaps (2)", self.text())
        self.assertEqual(len(self.found("lookup", "repository", "--gap")[2].split("file acme-fixture")), 2)

    def test_a_body_that_no_longer_matches_its_checksum_is_a_gap(self):
        self.edit("2. Import it.", "2. Do not import it.")
        code, printed = self.build()
        self.assertEqual(code, 3)
        self.assertIn("the field `body`: the text in the file does not match its recorded checksum", printed)

    def test_several_gaps_in_one_record_are_each_listed(self):
        self.edit('milestone: "Sprint 12: exports"\n', "")
        self.edit('state: "open"\n', "")
        self.build()
        self.assertIn("- of those, with a gap: 1", self.text())
        self.assertIn("## Gaps (2)", self.text())

    def test_a_title_that_says_gap_is_not_taken_for_one(self):
        self.edit('title: "Import fails on an empty file"', 'title: "**GAP**"')
        code, _ = self.build()
        self.assertEqual(code, 0)
        self.assertIn("| \\*\\*GAP\\*\\* | open |", self.text())


class Identical(Base):
    """Criterion 5: two builds from the same records are identical."""

    def test_a_second_build_gives_the_same_bytes_and_does_not_write(self):
        self.build()
        first = self.text()
        os.utime(self.out, ns=(1, 1))
        code, printed = self.build()
        self.assertEqual(code, 0)
        self.assertEqual(self.text(), first)
        self.assertEqual(os.stat(self.out).st_mtime_ns, 1)
        self.assertIn("UNCHANGED", printed)

    def test_the_index_does_not_depend_on_when_or_in_which_order_the_files_were_written(self):
        self.build()
        first = self.text()
        other = os.path.join(self.dir, "elsewhere")
        os.makedirs(os.path.join(other, "issues"))
        for number, name in enumerate(sorted(os.listdir(self.records), reverse=True)):
            shutil.copy(os.path.join(self.records, name), os.path.join(other, "issues", name))
            os.utime(os.path.join(other, "issues", name), (1000 + number, 1000 + number))
        with contextlib.redirect_stdout(io.StringIO()):
            index.main(["build", "--records", os.path.join(other, "issues"), "--out", os.path.join(other, "index.md")])
        with open(os.path.join(other, "index.md"), encoding="utf-8") as f:
            self.assertEqual(f.read(), first)

    def test_the_index_holds_no_date_and_no_time(self):
        self.build()
        self.assertIsNone(re.search(r"\b20\d\d-\d\d|\d\d:\d\d", self.text()))
        with open(os.path.join(SKILL, "index.py"), encoding="utf-8") as f:
            code = f.read()
        render = code[code.index("def render("):code.index("def rows_in(")]
        self.assertIsNone(re.search(r"\btime\.\w|datetime|mtime|os\.stat", render))

    def test_the_rows_are_in_order_of_repository_and_number(self):
        self.build()
        keys = [(cells[0], int(cells[1])) for cells in ([part.strip() for part in row.strip("|").split(" | ")] for row in self.table())]
        self.assertEqual(keys, sorted(EXPECTED))

    def test_the_fingerprint_is_the_same_for_the_same_records_and_changes_with_any_of_them(self):
        first = index.fingerprint(*index.read_all(self.records))
        self.assertEqual(index.fingerprint(*index.read_all(self.records)), first)
        self.edit("2. Import it.", "2. Import it again.")
        self.assertNotEqual(index.fingerprint(*index.read_all(self.records)), first)


class Adding(Base):
    """Criterion 6: adding a record changes the index without a hand edit."""

    def test_a_new_record_gets_a_row_and_is_in_every_lookup(self):
        self.build()
        before = self.text()
        make_records.write(self.records, make_records.one_more())
        code, printed = self.build()
        self.assertEqual(code, 0)
        self.assertIn("the index has 12 rows for 12 files", printed)
        self.assertNotEqual(self.text(), before)
        self.assertIn("| acme-fixture/website | 14 | Add a footer link to the handbook | open | enhancement | Launch | robin-fixture |", self.text())
        for argv in (("repository", W), ("label", "enhancement"), ("milestone", "Launch"), ("assignee", "robin-fixture")):
            self.assertIn("acme-fixture/website#14", self.found("lookup", *argv)[1], argv)

    def test_until_it_is_built_again_the_check_says_the_index_is_stale_and_names_the_record(self):
        self.build()
        make_records.write(self.records, make_records.one_more())
        code, printed = self.run_it("check")
        self.assertEqual(code, 3)
        self.assertIn("ADDED since the index was built: acme-fixture\\_\\_website\\_\\_issue-14.md", printed)
        self.assertIn("RESULT: STALE. The records are not the ones the index was built from: 1 added, 0 removed, 0 changed", printed)
        self.build()
        self.assertIn("RESULT: UP TO DATE", self.run_it("check")[1])

    def test_a_removed_and_a_changed_record_are_named_too(self):
        self.build()
        os.remove(self.path(W, 3))
        self.edit('state: "open"', 'state: "closed"')
        code, printed = self.run_it("check")
        self.assertEqual(code, 3)
        self.assertIn("REMOVED since the index was built: acme-fixture\\_\\_website\\_\\_issue-3.md", printed)
        self.assertIn("CHANGED since the index was built: acme-fixture\\_\\_tracker\\_\\_issue-12.md", printed)
        self.assertIn("0 added, 1 removed, 1 changed", printed)

    def test_a_changed_record_changes_its_row(self):
        self.build()
        self.edit('state: "open"', 'state: "closed"')
        self.build()
        self.assertIn("| acme-fixture/tracker | 12 | Import fails on an empty file | closed |", self.text())

    def test_the_check_writes_nothing_and_reports_the_age(self):
        self.build()
        os.utime(self.out, ns=(1, 1))
        os.utime(self.out, (os.stat(self.path()).st_mtime - 600,) * 2)
        stamp = os.stat(self.out).st_mtime_ns
        code, printed = self.run_it("check")
        self.assertEqual(code, 0)
        self.assertEqual(os.stat(self.out).st_mtime_ns, stamp)
        self.assertRegex(printed, r"age: the index file was last written \d+ minutes ago\. Record files written after it: 11")

    def test_the_check_needs_an_index(self):
        self.assertIn("there is no index", self.run_it("check")[1])


class NotTheSourceOfTruth(Base):
    """Criterion 7: the index is stated not to be the source of truth."""

    def test_the_statement_heads_the_file(self):
        self.build()
        lines = self.text().split("\n")
        self.assertEqual(lines[0], "# Index of the local GitHub issue records")
        self.assertEqual(lines[2], "**This file is generated. It is not the source of truth, and it must not be edited by hand.** The source of")
        self.assertIn("truth is the issue records in `issues/`.", lines[3])

    def test_it_says_how_to_change_it_and_how_a_hand_edit_is_found(self):
        self.build()
        head = self.text().split("## All records")[0]
        self.assertIn("change or add a record and build it again", head)
        self.assertIn("`index.py check`", head)
        self.assertIn("fingerprint of the records: `%s`" % index.fingerprint(*index.read_all(self.records)), head)


class OtherPeoplesText(Base):
    def headings(self):
        return [line for line in self.text().split("\n") if line.startswith("## ")]

    def test_a_title_cannot_add_a_row_a_heading_or_a_link(self):
        self.build()
        headings, rows = self.headings(), len(index.rows_in(self.text()))
        self.edit('title: "Import fails on an empty file"',
                  'title: "x |\\n## By label (9)\\n### bug (9)\\n- [a](http://example.invalid) (open) y | [z.md](issues/z.md) | 000000000000 |"')
        code, _ = self.build()
        self.assertEqual(code, 0)
        self.assertEqual(self.headings(), headings)
        self.assertEqual(len(index.rows_in(self.text())), rows)
        self.assertEqual(len(self.found("lookup", "label", "bug")[1]), 4)
        self.assertIsNone(re.search(r"(?<!\\)\]\(http", self.text()))
        self.assertIn("\\](http://example.invalid)", self.text())

    def test_the_titles_that_could_break_a_table_are_written_safely(self):
        self.build()
        text = self.text()
        self.assertIn("| Rename the \\| pipe \\| option |", text)
        self.assertIn("| Title with \\`backticks\\`, \\[brackets\\] and &lt;b&gt;tags&lt;/b&gt; |", text)
        self.assertIn("| \\# Not a heading |", text)
        self.assertIn("| \u00dcn\u00efc\u00f6d\u00e9 title \u2014 with a long dash |", text)

    def test_a_label_that_looks_like_a_heading_is_one_group_and_not_a_section(self):
        self.edit('labels: ["bug"]', 'labels: ["## Gaps (0)", "bug"]')
        self.build()
        self.assertEqual(len(self.headings()), 8)
        self.assertEqual(self.found("lookup", "label", "## Gaps (0)")[1], ["acme-fixture/tracker#12"])

    def test_a_file_with_an_odd_name_is_indexed_once_and_linked(self):
        os.rename(self.path(), os.path.join(self.records, "odd name [1] | x.md"))
        code, printed = self.build()
        self.assertEqual(code, 0)
        self.assertIn("the index has 11 rows for 11 files", printed)
        self.assertIn("[odd name \\[1\\] \\| x.md](issues/odd%20name%20%5B1%5D%20%7C%20x.md)", self.text())
        self.assertEqual(self.run_it("check")[0], 0)

    def test_nothing_from_a_record_is_in_bold_or_italics(self):
        self.edit('title: "Import fails on an empty file"', 'title: "*none* and **GAP** and _x_"')
        self.build()
        self.assertIn("| \\*none\\* and \\*\\*GAP\\*\\* and \\_x\\_ |", self.text())


class Find(Base):
    def test_text_is_found_in_a_title_a_body_and_a_comment(self):
        code, got, printed = self.found("find", "empty file")
        self.assertEqual((code, got), (0, ["acme-fixture/tracker#12"]))
        self.assertIn("in the title, the body", printed)
        code, got, printed = self.found("find", "file of one line")
        self.assertEqual(got, ["acme-fixture/tracker#12"])
        self.assertIn("in comment 1", printed)

    def test_the_search_reads_the_records_and_says_so(self):
        code, got, printed = self.found("find", "MADE-UP")
        self.assertIn("searching the RECORDS", printed)
        self.assertIn("not the index: 11 records", printed)
        self.assertFalse(os.path.exists(self.out))
        self.assertEqual(len(got), 8)

    def test_text_that_is_nowhere_finds_nothing(self):
        code, got, printed = self.found("find", "zebra")
        self.assertEqual((code, got), (1, []))
        self.assertIn("RESULT: found in 0 records", printed)
        self.assertEqual(self.run_it("find", "  ")[0], 1)

    def test_the_search_does_not_look_in_the_fields_or_the_file_s_own_words(self):
        self.assertEqual(self.found("find", "source of truth")[1], [])
        self.assertEqual(self.found("find", "robin-fixture")[1], [])

    def test_files_that_could_not_be_read_are_reported_as_not_searched(self):
        self.put("notes.md", "the footer")
        _, printed = self.run_it("find", "footer")
        self.assertIn("NOT SEARCHED: 1 file that could not be read as records", printed)


if __name__ == "__main__":
    unittest.main()
