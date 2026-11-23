"""Tests for the github-duplicate-search skill. They work on a made-up fixture in a scratch folder. Nothing is contacted."""
import contextlib
import io
import json
import os
import re
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, SKILL)
import make_fixture  # noqa: E402
import search  # noqa: E402

T, W = make_fixture.TRACKER, make_fixture.WEBSITE
MEMORY, LOGIN, DARK = "proposed-out-of-memory.md", "proposed-login-page.md", "proposed-dark-mode.md"


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = self._tmp.name
        make_fixture.write_all(self.dir)
        self.index, self.records = os.path.join(self.dir, "fixture.md"), os.path.join(self.dir, "records")

    def proposal(self, name):
        return os.path.join(self.dir, "proposals", name)

    def go(self, name, *flags):
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            code = search.main([self.proposal(name) if not os.path.isabs(name) else name, "--index", self.index] + list(flags))
        return code, printed.getvalue()

    def write_proposal(self, title, body, repo=T, labels=("bug", "export"), name="mine.md"):
        with open(self.proposal(name), "w", encoding="utf-8") as f:
            f.write(make_fixture.proposal_text(title, repo, list(labels), body))
        return name

    def rebuild(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return make_fixture.indexer.main(["build", "--records", self.records, "--out", self.index])

    def add(self, *args, **more):
        """Add one made-up issue to the fixture and build its index again."""
        repo, issue, comments = make_fixture.made(*args, **more)
        with open(os.path.join(self.records, "%s__issue-%d.md" % (repo.replace("/", "__"), issue["number"])), "wb") as f:
            f.write(make_fixture.reader.render(make_fixture.SOURCE, repo, issue, comments).encode("utf-8"))
        self.rebuild()

    def candidates(self, printed):
        return re.findall(r"CANDIDATE \d+: (\S+#\d+)", printed)

    def block(self, printed, issue):
        """The lines the search printed for one candidate."""
        lines = printed.splitlines()
        start = next(number for number, line in enumerate(lines) if "CANDIDATE" in line and issue + " " in line)
        return "\n".join(lines[start:start + 8])

    def report(self, name, *flags):
        path = os.path.join(self.dir, "report.md")
        self.go(name, "--report", path, *flags)
        with open(path, encoding="utf-8") as f:
            return f.read()


def pair(body, other, **more):
    """compare() for two made-up texts."""
    proposal = {"title": more.get("title", "One title"), "repository": more.get("repo", T), "labels": more.get("labels", ["export"]), "text": body}
    issue = {"title": more.get("other_title", "Another heading"), "repository": more.get("other_repo", T), "labels": more.get("other_labels", ["export"]),
             "state": "open", "text": other}
    return search.compare(proposal, issue)


class Signals(Base):
    """Criterion 1: the search uses at least three signals beyond the title."""

    def test_there_are_five_signals_beyond_the_title_and_three_are_needed(self):
        self.assertEqual([name for name, _, _ in search.SIGNALS], ["error", "named", "wording", "labels", "repository"])
        self.assertNotIn("title", [name for name, _, _ in search.SIGNALS])
        self.assertEqual(search.NEEDED, 3)

    def test_the_title_is_worth_least_and_never_counts_toward_a_candidate(self):
        self.assertEqual(search.TITLE_POINTS, min(points for _, _, points in search.SIGNALS))
        found = pair("x", "y", title="Login page is blank", other_title="Login page is blank", other_labels=["export"])
        self.assertEqual([found[name][0] for name in ("title", "labels", "repository")], ["match"] * 3)
        self.assertEqual(search.weigh(found), (2, 4, None))

    def test_error_text(self):
        self.assertEqual(pair("it said MemoryError: no room", "a MemoryError in the night")["error"][0], "match")
        self.assertEqual(pair("code E-EXPORT-413 again", "see E-EXPORT-413")["error"], ("match", "both quote: e-export-413"))
        self.assertEqual(pair("a ValueError", "a MemoryError")["error"][0], "no")
        self.assertEqual(pair("it is slow", "a MemoryError")["error"][0], "not comparable")
        self.assertEqual(pair("an error happened", "the error was bad")["error"][0], "not comparable")

    def test_named_things_need_two_in_common(self):
        self.assertEqual(pair("`export.py` on `a.csv`", "run export.py with a.csv")["named"][0], "match")
        self.assertEqual(pair("`export.py` on `a.csv`", "see export.py and b.csv")["named"][0], "no")
        self.assertEqual(pair("use --chunk-size in v2.3.1", "v2.3.1 and --chunk-size")["named"][0], "match")
        self.assertEqual(pair("nothing named", "see export.py and b.csv")["named"][0], "not comparable")

    def test_an_error_name_is_not_counted_again_as_a_named_thing(self):
        self.assertEqual(search.named_in("`MemoryError` in `export.py`"), {"export.py"})

    def test_body_wording_needs_enough_words_and_a_large_enough_share(self):
        text = "the nightly export of the orders file loads the whole file into memory before writing anything"
        self.assertEqual(pair(text, text + " and stops")["wording"][0], "match")
        self.assertEqual(pair(text, "the footer shows the wrong year on every page of the site")["wording"][0], "no")
        self.assertEqual(pair("export orders", "export orders")["wording"][0], "no")
        self.assertEqual(pair("", text)["wording"][0], "not comparable")

    def test_meaningful_words_drop_common_words_and_endings(self):
        self.assertEqual(search.words_in("The exports were loading files"), {"export", "load", "file"})
        self.assertEqual(search.words_in("anything writes crashes and the process"), {"anything", "write", "crash", "process"})

    def test_a_label_that_only_says_what_kind_of_issue_it_is_is_not_a_signal(self):
        self.assertEqual(pair("x", "y", labels=["bug"], other_labels=["bug"])["labels"][0], "not comparable")
        self.assertEqual(pair("x", "y", labels=["bug", "export"], other_labels=["bug", "auth"])["labels"][0], "no")
        self.assertEqual(pair("x", "y", labels=["Export"], other_labels=["bug", "export"])["labels"][0], "match")
        self.assertEqual(pair("x", "y", labels=[], other_labels=["export"])["labels"][0], "not comparable")

    def test_repository(self):
        self.assertEqual(pair("x", "y")["repository"][0], "match")
        self.assertEqual(pair("x", "y", other_repo=W)["repository"][0], "no")
        self.assertEqual(pair("x", "y", repo=None)["repository"][0], "not comparable")

    def test_not_comparable_is_neither_a_match_nor_points(self):
        found = pair("it is slow", "a MemoryError", labels=["bug"], other_labels=["bug"], repo=None)
        self.assertEqual(search.weigh(found), (0, 0, None))


class EachMatchExplained(Base):
    """Criterion 2: each match lists the signals and a confidence."""

    def test_every_candidate_shows_all_six_signals_a_score_and_a_confidence(self):
        _, printed = self.go(MEMORY)
        for issue in self.candidates(printed):
            block = self.block(printed, issue)
            for label in ("Error text", "Named things", "Body wording", "Labels", "Repository", "Title"):
                self.assertIn("    " + label, block)
            self.assertRegex(block, r"confidence (high|medium|low), \d+ points\. Signals beyond the title that matched: \d of 5")

    def test_each_signal_says_what_was_found(self):
        _, printed = self.go(MEMORY)
        block = self.block(printed, "acme-fixture/tracker#101")
        self.assertIn("Error text    MATCH           both quote: memoryerror", block)
        self.assertIn("Named things  MATCH           both name: export.py, orders-march.csv, v2.3.1", block)
        self.assertIn("Labels        MATCH           both have: export", block)
        self.assertIn("Title         no              the titles are different", block)

    def test_the_scale_has_three_steps_and_no_gaps(self):
        self.assertEqual(search.SCALE, (("high", 11, 14), ("medium", 9, 10), ("low", 6, 8)))
        self.assertEqual(search.MOST, 14)
        covered = sorted(points for _, low, high in search.SCALE for points in range(low, high + 1))
        self.assertEqual(covered, list(range(6, 15)))

    def test_the_least_a_candidate_can_score_is_the_bottom_of_the_scale(self):
        weakest = sorted(points for _, _, points in search.SIGNALS)[:search.NEEDED]
        self.assertEqual(sum(weakest), search.SCALE[-1][1])

    def test_confidence_follows_the_points(self):
        def found(*matched):
            return {name: ("match" if name in matched else "no", "") for name in ("error", "named", "wording", "labels", "repository", "title")}
        self.assertEqual(search.weigh(found("wording", "labels", "repository")), (3, 6, "low"))
        self.assertEqual(search.weigh(found("named", "wording", "labels")), (3, 8, "low"))
        self.assertEqual(search.weigh(found("error", "named", "labels")), (3, 9, "medium"))
        self.assertEqual(search.weigh(found("error", "named", "wording")), (3, 10, "medium"))
        self.assertEqual(search.weigh(found("error", "named", "wording", "repository")), (4, 11, "high"))
        self.assertEqual(search.weigh(found("error", "named", "wording", "labels", "repository", "title")), (5, 14, "high"))
        self.assertEqual(search.weigh(found("error", "named", "title")), (2, 8, None))

    def test_the_run_states_the_scale(self):
        _, printed = self.go(MEMORY)
        self.assertIn("a candidate needs 3 of the 5 signals beyond the title. Confidence: high is 11 to 14 points; medium is 9 to 10 points; low is 6 to 8 points, of 14", printed)

    def test_the_report_holds_a_table_of_signals_for_each_candidate(self):
        text = self.report(MEMORY)
        self.assertEqual(text.count("| Signal | Points | Result | What was found |"), 3)
        self.assertIn("### 1. acme-fixture/tracker#101: high confidence, 13 of 14 points. Recommendation: close-as-duplicate", text)
        self.assertIn("| Error text | 4 | MATCH | both quote: memoryerror |", text)
        self.assertIn("| Title | 0 | no | the titles are different |", text)
        self.assertIn("- signals beyond the title that matched: 5 of 5", text)
        self.assertIn("**Confidence**, on a scale of three: high is 11 to 14 points; medium is 9 to 10 points; low is 6 to 8 points, of 14.", text)

    def test_candidates_are_listed_strongest_first(self):
        _, printed = self.go(MEMORY)
        self.assertEqual(self.candidates(printed), ["acme-fixture/tracker#101", "acme-fixture/tracker#106", "acme-fixture/tracker#102"])
        self.assertEqual(re.findall(r"confidence (\w+), (\d+) points", printed), [("high", "13"), ("medium", "10"), ("low", "6")])


class SameTitleUnrelated(Base):
    """Criterion 3: a same-title unrelated issue is not reported as a duplicate."""

    def test_the_issue_with_the_same_title_is_not_a_candidate(self):
        code, printed = self.go(LOGIN)
        self.assertEqual(code, 0)
        self.assertEqual(self.candidates(printed), [])
        self.assertIn("RESULT: NONE.", printed)

    def test_it_is_shown_as_looked_at_with_the_reason(self):
        _, printed = self.go(LOGIN)
        self.assertIn('NOT A CANDIDATE: acme-fixture/tracker#103 "Login page is blank": 0 of the 3 signals needed (nothing beyond the title). '
                      "The title matched: the titles are the same. A title alone makes nothing a duplicate", printed)

    def test_the_report_says_so_too(self):
        text = self.report(LOGIN)
        self.assertIn("- candidates: 0", text)
        self.assertIn("- **recommendation: proceed**. No likely duplicate was found", text)
        looked = text.split("## Looked at, and not candidates")[1]
        self.assertIn('acme-fixture/tracker#103 "Login page is blank" (open): 0 of the 3 needed.', looked)
        self.assertIn("**The title matched (the titles are the same), and a title alone makes nothing a duplicate**", looked)

    def test_the_same_title_with_two_more_signals_is_still_not_a_candidate(self):
        name = self.write_proposal("Login page is blank", "The printed handbook has an empty page.", repo=T, labels=["auth"])
        _, printed = self.go(name)
        self.assertEqual(self.candidates(printed), [])
        self.assertIn('#103 "Login page is blank": 2 of the 3 signals needed (Labels, Repository). The title matched', printed)

    def test_the_same_title_does_get_reported_when_three_other_signals_agree(self):
        name = self.write_proposal("Login page is blank", "After a password reset the sign-in screen stays white. The console shows `E-AUTH-500` from `session.js` in `v2.3.1`.",
                                   repo=T, labels=["auth"])
        _, printed = self.go(name)
        self.assertEqual(self.candidates(printed)[0], "acme-fixture/tracker#103")
        self.assertIn("Title         MATCH           the titles are the same", printed)


class DifferentTitleDuplicate(Base):
    """Criterion 4: a true duplicate with a different title is found."""

    def test_the_duplicate_is_the_first_candidate_at_high_confidence(self):
        code, printed = self.go(MEMORY)
        self.assertEqual(code, 0)
        self.assertIn('CANDIDATE 1: acme-fixture/tracker#101 "Export crashes on files over 2 GB", open', printed)
        self.assertIn("confidence high, 13 points. Signals beyond the title that matched: 5 of 5", printed)

    def test_its_title_did_not_match(self):
        _, printed = self.go(MEMORY)
        self.assertIn("Title         no ", self.block(printed, "acme-fixture/tracker#101"))
        self.assertEqual(search.words_in("Out of memory when saving the March orders") & search.words_in("Export crashes on files over 2 GB"), set())

    def test_it_is_found_with_no_labels_and_no_repository_on_the_proposal(self):
        with open(self.proposal(MEMORY), encoding="utf-8") as f:
            body = f.read().split("\n---\n", 1)[1]
        name = self.write_proposal("Out of memory when saving the March orders", body, repo=None, labels=[])
        _, printed = self.go(name)
        self.assertEqual(self.candidates(printed), ["acme-fixture/tracker#101"])
        self.assertIn("confidence medium, 10 points. Signals beyond the title that matched: 3 of 5", printed)
        self.assertIn("Repository    not comparable", printed)

    def test_a_comment_on_the_existing_issue_counts_as_its_text(self):
        self.add(T, 110, "Something else entirely", "A short body.", ["export"],
                 replies=[(make_fixture.KIT, "I get `MemoryError` from `export.py` on `orders-march.csv` with `v2.3.1`.")])
        _, printed = self.go(MEMORY)
        self.assertIn("acme-fixture/tracker#110", self.candidates(printed))

    def test_the_near_duplicate_is_found_at_a_lower_confidence_and_is_not_called_the_same(self):
        _, printed = self.go(MEMORY)
        block = self.block(printed, "acme-fixture/tracker#102")
        self.assertIn("confidence low, 6 points", block)
        self.assertIn("Recommendation: link (the confidence is low, not high)", block)
        self.assertIn("Error text    not comparable  one of the two quotes no error", block)


class NoMatch(Base):
    """Criterion 5: a proposal with no match reports none."""

    def test_no_match_says_none_plainly(self):
        code, printed = self.go(DARK)
        self.assertEqual(code, 0)
        self.assertEqual(self.candidates(printed), [])
        self.assertIn("RESULT: NONE. No likely duplicate was found. Recommendation: proceed. A person decides", printed)

    def test_the_nearest_issue_is_not_offered_as_a_candidate_just_for_being_nearest(self):
        _, printed = self.go(DARK)
        self.assertIsNone(re.search(r"CANDIDATE \d", printed))
        self.assertIn("NOT A CANDIDATE: acme-fixture/website#7", printed)
        self.assertIn("issues that matched on nothing at all: 7", printed)

    def test_the_report_for_no_match(self):
        text = self.report(DARK)
        self.assertIn("## Candidates (0)\n\nNone. No existing issue matched on 3 signals beyond the title.", text)
        self.assertIn("- **recommendation: proceed**", text)

    def test_an_empty_index_reports_none(self):
        for name in os.listdir(self.records):
            os.remove(os.path.join(self.records, name))
        self.rebuild()
        code, printed = self.go(MEMORY)
        self.assertEqual(code, 0)
        self.assertIn("RESULT: NONE.", printed)


class Recommendation(Base):
    """Criterion 6: the recommendation is link, close-as-duplicate or proceed, and a person decides."""

    def test_only_the_three_recommendations_are_ever_given(self):
        seen = set()
        for name in (MEMORY, LOGIN, DARK):
            _, printed = self.go(name)
            seen |= set(re.findall(r"Recommendation: ([a-z-]+)", printed))
        self.assertEqual(seen, {"close-as-duplicate", "link", "proceed"})

    def rule(self, confidence, state="open", repo=T):
        return search.recommend({"repository": T}, {"repository": repo, "state": state}, confidence)[0]

    def test_close_as_duplicate_needs_high_confidence_an_open_issue_and_the_same_repository(self):
        self.assertEqual(self.rule("high"), "close-as-duplicate")
        self.assertEqual(self.rule("medium"), "link")
        self.assertEqual(self.rule("low"), "link")
        self.assertEqual(self.rule("high", state="closed"), "link")
        self.assertEqual(self.rule("high", repo=W), "link")
        self.assertEqual(search.recommend({"repository": None}, {"repository": T, "state": "open"}, "high")[0], "link")

    def test_a_closed_issue_with_the_same_error_is_linked_and_the_reason_is_given(self):
        _, printed = self.go(MEMORY)
        self.assertIn("Recommendation: link (the existing issue is closed, so if this is the same problem it has come back)", self.block(printed, "acme-fixture/tracker#106"))

    def test_the_overall_recommendation_is_the_strongest_candidate_s(self):
        _, printed = self.go(MEMORY)
        self.assertIn("RESULT: 3 likely duplicates. Strongest: acme-fixture/tracker#101, high confidence. Recommendation: close-as-duplicate. A person decides", printed)
        self.assertIn("- **recommendation: close-as-duplicate** of acme-fixture/tracker#101", self.report(MEMORY))

    def test_every_result_says_a_person_decides_and_the_report_says_nothing_was_done(self):
        for name in (MEMORY, LOGIN, DARK):
            self.assertIn("A person decides", self.go(name)[1].splitlines()[-1])
        self.assertIn("**This report is generated. It recommends, and a person decides.** Nothing was created, linked or closed.", self.report(MEMORY))

    def test_the_skill_has_no_way_to_act_on_its_recommendation(self):
        with open(os.path.join(SKILL, "search.py"), encoding="utf-8") as f:
            code = f.read()
        for word in ("urllib.request", "socket", "http.client", "subprocess", "os.system", "os.remove", "shutil", "api.github.com", "GITHUB_TOKEN"):
            self.assertNotIn(word, code)


class IndexUnchanged(Base):
    """Criterion 7: the search does not change the index."""

    def state(self):
        found = {}
        for folder, _, names in os.walk(self.dir):
            for name in names:
                path = os.path.join(folder, name)
                if "report" not in name:
                    with open(path, "rb") as f:
                        found[path] = (f.read(), os.stat(path).st_mtime_ns)
        return found

    def test_the_index_and_every_record_are_byte_for_byte_and_untouched_after_each_search(self):
        before = self.state()
        for name in (MEMORY, LOGIN, DARK):
            _, printed = self.go(name)
            self.assertIn("have the same SHA-256 after the search as before it: yes", printed)
        self.report(MEMORY)
        self.assertEqual(self.state(), before)

    def test_the_only_file_the_skill_opens_for_writing_is_the_report(self):
        with open(os.path.join(SKILL, "search.py"), encoding="utf-8") as f:
            code = f.read()
        self.assertEqual(re.findall(r'open\(([^)]*), "w', code), ['args.report + ".tmp"'])
        self.assertNotIn('"wb"', code)
        self.assertNotIn('"a"', code)

    def test_the_report_cannot_be_written_over_the_index_or_a_record(self):
        before = self.state()
        for target in (self.index, os.path.join(self.records, "acme-fixture__tracker__issue-101.md")):
            code, printed = self.go(MEMORY, "--report", target)
            self.assertEqual(code, 1)
            self.assertIn("would be written over the index or a record", printed)
        self.assertEqual({path: data for path, (data, _) in self.state().items()}, {path: data for path, (data, _) in before.items()})

    def test_a_stale_index_is_not_searched(self):
        repo, issue, comments = make_fixture.made(T, 120, "A new issue the index does not know", "Body.", ["export"])
        with open(os.path.join(self.records, "acme-fixture__tracker__issue-120.md"), "wb") as f:
            f.write(make_fixture.reader.render(make_fixture.SOURCE, repo, issue, comments).encode("utf-8"))
        code, printed = self.go(MEMORY)
        self.assertEqual(code, 1)
        self.assertIn("the index is NOT what its records give now", printed)
        self.assertIn("Nothing was searched and nothing was written.", printed)
        self.assertNotIn("RESULT", printed)

    def test_an_index_edited_by_hand_is_not_searched(self):
        with open(self.index, encoding="utf-8") as f:
            text = f.read()
        with open(self.index, "w", encoding="utf-8") as f:
            f.write("\n".join(line for line in text.split("\n") if "| 101 |" not in line))
        code, printed = self.go(MEMORY)
        self.assertEqual(code, 1)
        self.assertIn("stale, or it was edited by hand", printed)

    def test_a_file_that_is_not_an_index_is_refused(self):
        with open(self.index, "w") as f:
            f.write("# my notes\n")
        self.assertIn("is not an index written by the github-build-index skill", self.go(MEMORY)[1])
        os.remove(self.index)
        self.assertIn("there is no readable index", self.go(MEMORY)[1])

    def test_the_same_search_gives_the_same_report(self):
        first = self.report(MEMORY)
        self.assertEqual(self.report(MEMORY), first)
        self.assertIsNone(re.search(r"\b20\d\d-\d\d-\d\d|\d\d:\d\d:\d\d", first.replace("2147483648", "")))


class TheProposal(Base):
    def test_a_proposal_needs_a_front_matter_and_a_title(self):
        for text in ("no front matter", "---\ntitle: \"\"\n---\nbody", "---\nrepository: \"a/b\"\n---\nbody", "---\ntitle: not json\n---\nbody",
                     "---\ntitle: \"x\"\nlabels: \"bug\"\n---\nbody", "---\ntitle: \"x\"\nrepository: 7\n---\nbody"):
            with open(self.proposal("bad.md"), "w") as f:
                f.write(text)
            code, printed = self.go("bad.md")
            self.assertEqual(code, 1, text)
            self.assertIn("STOPPED", printed)
        self.assertEqual(self.go("missing.md")[0], 1)

    def test_a_proposal_with_only_a_title_matches_nothing(self):
        name = self.write_proposal("Export crashes on files over 2 GB", "", repo=None, labels=[])
        code, printed = self.go(name)
        self.assertEqual(code, 0)
        self.assertEqual(self.candidates(printed), [])
        self.assertIn('#101 "Export crashes on files over 2 GB": 0 of the 3 signals needed (nothing beyond the title). The title matched', printed)


class OtherPeoplesText(Base):
    def test_a_title_in_a_record_cannot_break_the_report(self):
        self.add(T, 130, "x |\n## Candidates (9)\n### 1. evil: high confidence | y", "\n".join([
            "I ran `export.py` on `orders-march.csv` with `v2.3.1` and got `MemoryError`.",
            "The whole orders file is loaded into memory before anything is written, and the job was killed after a few minutes."]), ["export"])
        text = self.report(MEMORY)
        self.assertEqual(len([line for line in text.split("\n") if line.startswith("## ")]), 4)
        self.assertEqual(len([line for line in text.split("\n") if line.startswith("### ")]), 4)
        self.assertIn('"x \\|\\\\n\\#\\# Candidates (9)', text)

    def test_what_was_found_is_written_safely(self):
        odd = "See `a|b.csv` and `[link](http://example.invalid).py` for the export."
        self.add(T, 131, "Odd names", odd, ["export"])
        name = self.write_proposal("Something with odd names", odd)
        self.assertIn("acme-fixture/tracker#131", self.candidates(self.go(name)[1]))
        text = self.report(name)
        self.assertIn("| Named things | 3 | MATCH | both name: \\[link\\](http://example.invalid).py, a\\|b.csv, b.csv |", text)
        self.assertIsNone(re.search(r"(?<!\\)\]\(http", text))
        rows = [line for line in text.split("\n") if line.startswith("| Named things | 3 | MATCH |")]
        self.assertEqual([len(re.findall(r"(?<!\\)\|", row)) for row in rows], [5] * len(rows))

    def test_a_record_with_a_gap_is_not_compared_and_is_counted(self):
        path = os.path.join(self.records, "acme-fixture__tracker__issue-101.md")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        with open(path, "w", encoding="utf-8") as f:
            f.write(text.replace('state: "open"\n', ""))
        self.assertEqual(self.rebuild(), 3)
        code, printed = self.go(MEMORY)
        self.assertEqual(code, 0)
        self.assertNotIn("acme-fixture/tracker#101", self.candidates(printed))
        self.assertIn("Records that could not be compared: 1", printed)
        self.assertIn("- records the search could not compare, because a field is a gap: 1", self.report(MEMORY))


class Weights(Base):
    def test_equal_weights_change_the_confidence_of_three_strong_signals(self):
        with open(self.proposal(MEMORY), encoding="utf-8") as f:
            body = f.read().split("\n---\n", 1)[1]
        name = self.write_proposal("Out of memory when saving the March orders", body, repo=None, labels=[])
        self.assertIn("confidence medium, 10 points", self.go(name)[1])
        _, printed = self.go(name, "--equal-weights")
        self.assertIn("confidence low, 3 points", printed)
        self.assertIn("with equal weights every signal counts 1: high is all 5 signals beyond the title, medium is 4, low is 3", printed)

    def test_equal_weights_do_not_change_which_issues_are_candidates(self):
        self.assertEqual(self.candidates(self.go(MEMORY)[1]), self.candidates(self.go(MEMORY, "--equal-weights")[1]))
        self.assertEqual(self.candidates(self.go(LOGIN, "--equal-weights")[1]), [])

    def test_the_report_shows_each_signal_s_points(self):
        text = self.report(MEMORY)
        for line in ("| Error text | 4 |", "| Named things | 3 |", "| Body wording | 3 |", "| Labels | 2 |", "| Repository | 1 |", "| Title | 1 |"):
            self.assertIn(line, text.split("## Candidates")[0])


class TheFixture(Base):
    def test_the_fixture_is_an_index_the_generator_calls_up_to_date(self):
        with contextlib.redirect_stdout(io.StringIO()) as printed:
            code = make_fixture.indexer.main(["check", "--records", self.records, "--out", self.index])
        self.assertEqual(code, 0)
        self.assertIn("UP TO DATE", printed.getvalue())

    def test_it_holds_the_three_kinds_of_issue_the_quest_asks_for(self):
        with open(self.index, encoding="utf-8") as f:
            text = f.read()
        for row in ("| acme-fixture/tracker | 101 | Export crashes on files over 2 GB | open |", "| acme-fixture/tracker | 102 | Export is slow on large files | open |",
                    "| acme-fixture/tracker | 103 | Login page is blank | open |"):
            self.assertIn(row, text)
        with open(self.proposal(LOGIN), encoding="utf-8") as f:
            self.assertEqual(json.loads(f.read().split("\n")[1].split(": ", 1)[1]), "Login page is blank")


if __name__ == "__main__":
    unittest.main()
