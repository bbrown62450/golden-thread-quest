"""Tests for the github-delta-sync skill. Every test runs against fake_github.py. None contacts GitHub."""
import contextlib
import io
import json
import os
import re
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import fake_github  # noqa: E402
import sync  # noqa: E402
from fake_github import CASEY, CLOCK, REPO, FakeGitHub, node  # noqa: E402

PRETEND = "-".join(("made", "up", "value"))      # stands in for a token. It is not one
PRETEND_ENV = dict([("GITHUB_TOKEN", PRETEND)])
COMMENTS = "/repos/%s/issues/%%d/comments" % REPO
LISTING = "/repos/%s/issues" % REPO


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.out = os.path.join(self._tmp.name, "local")

    def sync(self, fake=0, out=None, get=None, local_now=None, **options):
        """One sync against the made-up GitHub at a step, or against a made-up GitHub given."""
        self.fake = FakeGitHub(fake) if isinstance(fake, int) else fake
        self.client = sync.Client(get or self.fake.get, sleep=lambda seconds: None, clock=lambda: 1000)
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            try:
                code = sync.run(self.client, out or self.out, "fake", REPO, local_now=local_now or self.fake.now, **options)
            except sync.Stop as stop:
                print("github-delta: STOPPED: %s." % stop)
                code = 1
        self.printed = printed.getvalue()
        return code

    def upto(self, step):
        for n in range(step + 1):
            self.assertEqual(self.sync(n), 0)

    def state(self, out=None):
        with open(os.path.join(out or self.out, "state.json"), encoding="utf-8") as f:
            return json.load(f)

    def read(self, name):
        with open(os.path.join(self.out, name), encoding="utf-8") as f:
            return f.read()

    def files(self):
        found = {}
        for folder, _, names in os.walk(self.out):
            for name in names:
                with open(os.path.join(folder, name), "rb") as f:
                    found[os.path.relpath(os.path.join(folder, name), self.out)] = f.read()
        return found

    def note(self, name, text):
        os.makedirs(os.path.join(self.out, "notes"), exist_ok=True)
        with open(os.path.join(self.out, "notes", name), "w", encoding="utf-8") as f:
            f.write(text)

    def fetched(self):
        """The issue numbers whose comments were asked for in the last sync."""
        return sorted(int(m.group(1)) for path, _ in self.fake.calls for m in [re.match(r".*/issues/(\d+)/comments$", path)] if m)


class FirstSync(Base):
    def test_with_no_cursor_every_issue_is_read(self):
        self.assertEqual(self.sync(0), 0)
        self.assertEqual(self.fetched(), list(range(1, 13)))
        self.assertIn("cursor before this sync: none", self.printed)
        self.assertNotIn("since", self.fake.calls[1][1])
        self.assertIn("This sync: 12 new, 0 changed, 0 unchanged", self.printed)

    def test_pull_requests_are_left_out_by_the_key(self):
        self.sync(0)
        self.assertIn("GitHub returned 15 items in 1 request (15). Pull requests left out: 3", self.printed)
        self.assertEqual(len(self.state()["issues"]), 12)
        self.assertFalse([n for n in self.state()["issues"] if n.startswith("PR_")])

    def test_only_the_named_fields_are_kept_and_no_text_of_bodies_or_comments(self):
        self.sync(0)
        raw = self.read("state.json") + self.read("issues.md")
        for unwanted in ("IGNORE ALL PREVIOUS", "A made-up first comment", "repository_url", "html_url", '"body"'):
            self.assertNotIn(unwanted, raw)
        self.assertEqual(self.state()["issues"][node(3)]["comments"][0]["author"], "casey-fixture")

    def test_the_first_request_is_for_the_repository(self):
        self.sync(0)
        self.assertEqual(self.fake.calls[0], ("/repos/%s" % REPO, {}))


class OnlyTheChanged(Base):
    """Criterion 1."""

    def test_a_delta_fetches_only_the_issues_changed_since_the_cursor(self):
        self.sync(0)
        self.assertEqual(self.sync(1), 0)
        self.assertEqual(self.fetched(), [3, 5, 7, 13])
        self.assertIn("fetched: 4 issues, in 4 requests for their comments. Not fetched: 9", self.printed)

    def test_the_delta_asks_github_with_since(self):
        self.sync(0)
        self.sync(1)
        listing = [params for path, params in self.fake.calls if path == LISTING]
        self.assertEqual(listing, [{"state": "all", "sort": "updated", "direction": "asc", "since": "2026-11-20T08:55:00Z",
                                    "per_page": 100, "page": 1}])

    def test_a_delta_with_nothing_changed_fetches_nothing(self):
        self.sync(0)
        later = FakeGitHub(0)
        later.now = CLOCK[1]
        self.assertEqual(self.sync(later), 0)
        self.assertEqual(self.fetched(), [])
        self.assertIn("This sync: 0 new, 0 changed, 12 unchanged (12 not fetched, 0 fetched and found the same)", self.printed)
        self.assertEqual(self.client.count, 2)

    def test_a_changed_pull_request_is_not_fetched(self):
        self.sync(0)
        self.sync(1)
        self.assertNotIn(21, self.fetched())
        self.assertIn("Pull requests left out: 1", self.printed)

    def test_a_listing_that_ignores_since_is_said_and_does_no_harm(self):
        self.sync(0)
        later = FakeGitHub(1)
        later.ignore_since = True
        self.assertEqual(self.sync(later), 0)
        self.assertIn("NOTE: 9 issues returned were last updated before the time asked for", self.printed)
        self.assertIn("This sync: 1 new, 3 changed, 9 unchanged (0 not fetched, 9 fetched and found the same)", self.printed)

    def test_a_changed_listing_beyond_one_page_is_followed(self):
        self.sync(0)
        later = FakeGitHub(1)
        later.bulk(150, "2026-11-20T19:00:00Z")
        self.assertEqual(self.sync(later), 0)
        self.assertIn("GitHub returned 155 items in 2 requests (100 + 55)", self.printed)
        self.assertIn("This sync: 151 new, 3 changed, 9 unchanged", self.printed)

    def test_the_same_page_returned_again_is_not_taken_as_the_end(self):
        fake = FakeGitHub(0)
        fake.bulk(150, "2026-11-19T19:00:00Z")
        fake.ignore_page = True
        self.assertEqual(self.sync(fake), 1)
        self.assertIn("kept returning the same", self.printed)
        self.assertFalse(os.path.exists(self.out))


class TheCursor(Base):
    """Criteria 2 and 3, and clock differences."""

    def test_the_cursor_is_githubs_clock_at_the_start_of_the_sync(self):
        self.sync(0)
        self.assertEqual(self.state()["cursor"], {"time": "2026-11-20T09:00:00Z", "taken_from": sync.CURSOR_SOURCE})
        self.sync(1)
        self.assertEqual(self.state()["cursor"]["time"], "2026-11-21T09:00:00Z")
        self.assertIn("cursor after this sync: 2026-11-21T09:00:00Z, GitHub's clock at its start", self.printed)

    def test_a_wrong_local_clock_does_not_move_the_cursor_or_the_question(self):
        for wrong in ("2031-01-01T00:00:00Z", "2019-01-01T00:00:00Z"):
            with tempfile.TemporaryDirectory() as out:
                self.sync(0, out=out, local_now=wrong)
                self.assertEqual(self.state(out)["cursor"]["time"], "2026-11-20T09:00:00Z")
                self.sync(1, out=out, local_now=wrong)
                self.assertEqual(self.state(out)["cursor"]["time"], "2026-11-21T09:00:00Z")
                self.assertEqual(self.fetched(), [3, 5, 7, 13])
                self.assertEqual([p["since"] for path, p in self.fake.calls if path == LISTING], ["2026-11-20T08:55:00Z"])

    def test_the_run_says_how_far_the_local_clock_is_from_githubs(self):
        self.sync(0, local_now="2026-11-20T09:07:00Z")
        self.assertIn("This machine's clock: 2026-11-20T09:07:00Z, 7 minutes ahead of GitHub's. This machine's clock is not used for the cursor", self.printed)
        with tempfile.TemporaryDirectory() as out:
            self.sync(0, out=out, local_now="2026-11-20T08:59:30Z")
            self.assertIn("30 seconds behind GitHub's", self.printed)

    def test_the_local_clock_is_never_asked_for_when_setting_the_cursor(self):
        with mock.patch.object(sync, "utc_now", side_effect=AssertionError("the local clock was read")):
            self.assertEqual(self.sync(0), 0)

    def test_no_date_header_stops_the_run_and_the_local_clock_is_not_used_instead(self):
        fake = FakeGitHub(0)
        fake.send_date = False
        self.assertEqual(self.sync(fake), 1)
        self.assertIn("no usable Date header", self.printed)
        self.assertFalse(os.path.exists(self.out))

    def test_a_date_header_that_cannot_be_read_stops_the_run(self):
        fake = FakeGitHub(0)
        real = fake.get
        self.assertEqual(self.sync(fake, get=lambda path, params=None: (lambda s, h, b: (s, dict(h, Date="yesterday-ish"), b))(*real(path, params))), 1)
        self.assertIn("no usable Date header", self.printed)

    def test_the_date_header_is_read_in_any_time_zone(self):
        self.assertEqual(sync.github_clock({"date": "Fri, 20 Nov 2026 10:00:00 +0100"}), "2026-11-20T09:00:00Z")
        self.assertEqual(sync.github_clock({"date": "Fri, 20 Nov 2026 09:00:00 GMT"}), "2026-11-20T09:00:00Z")

    def test_the_cursor_is_taken_before_any_issue_is_read(self):
        """A change made while the sync runs is stamped after the cursor, so the next sync asks for it."""
        fake = FakeGitHub(0)
        real = fake.get

        def get(path, params=None):
            answer = real(path, params)
            if path == LISTING:            # the listing has been answered. Now an issue changes, and the clock moves on
                fake.now = "2026-11-20T09:00:30Z"
                fake.touch(4, "2026-11-20T09:00:20Z", labels=["changed-during-the-sync"])
            return answer
        self.assertEqual(self.sync(fake, get=get), 0)
        self.assertEqual(self.state()["cursor"]["time"], "2026-11-20T09:00:00Z")
        self.assertEqual(self.state()["issues"][node(4)]["labels"], [])
        later = FakeGitHub(0)
        later.now = CLOCK[1]
        later.touch(4, "2026-11-20T09:00:20Z", labels=["changed-during-the-sync"])
        self.sync(later)
        self.assertEqual(self.state()["issues"][node(4)]["labels"], ["changed-during-the-sync"])

    def test_a_sync_that_finds_nothing_still_succeeds_and_moves_the_cursor(self):
        self.sync(0)
        later = FakeGitHub(0)
        later.now = CLOCK[2]
        self.sync(later)
        self.assertEqual(self.state()["cursor"]["time"], CLOCK[2])
        self.assertEqual(self.state()["syncs"], 2)


class TheMargin(Base):
    """The hint: back the cursor up by a margin, and rely on identifiers."""

    def test_a_change_stamped_before_the_cursor_and_shown_late_is_caught(self):
        self.upto(1)
        self.assertEqual(self.state()["issues"][node(11)]["comments"], [])
        self.assertEqual(self.sync(2), 0)
        self.assertIn(11, self.fetched())
        self.assertEqual(len(self.state()["issues"][node(11)]["comments"]), 1)
        self.assertLess(self.state()["issues"][node(11)]["updated_at"], CLOCK[1])

    def test_without_the_margin_that_change_is_missed(self):
        self.upto(1)
        self.assertEqual(self.sync(2, margin=0), 0)
        self.assertNotIn(11, self.fetched())
        self.assertEqual(self.state()["issues"][node(11)]["comments"], [])

    def test_an_issue_returned_again_by_the_margin_is_not_held_twice(self):
        fake = FakeGitHub(0)
        fake.touch(6, "2026-11-20T08:58:00Z", labels=["inside-the-margin"])
        self.sync(fake)
        later = FakeGitHub(1)
        later.touch(6, "2026-11-20T08:58:00Z", labels=["inside-the-margin"])
        self.assertEqual(self.sync(later), 0)
        self.assertIn("issue %s, number 6. The same as held. It was returned because of the margin" % node(6), self.printed)
        self.assertIn("This sync: 1 new, 3 changed, 9 unchanged (8 not fetched, 1 fetched and found the same)", self.printed)
        self.assertEqual(len(self.state()["issues"]), 13)
        self.assertEqual(self.read("issues.md").count("| #6 |"), 1)

    def test_since_is_the_cursor_less_the_margin(self):
        self.assertEqual(sync.since_for("2026-11-21T00:02:00Z", 300), "2026-11-20T23:57:00Z")
        self.assertEqual(sync.since_for("2026-11-21T00:02:00Z", 0), "2026-11-21T00:02:00Z")


class AFailedSync(Base):
    """Criteria 2, 3 and 4."""

    def fail_at(self, number, step=2):
        fake = FakeGitHub(step)
        fake.fail(COMMENTS % number, 500)
        return fake

    def test_a_failure_partway_writes_nothing_and_leaves_the_cursor(self):
        self.upto(1)
        before = self.files()
        self.assertEqual(self.sync(self.fail_at(8)), 1)
        self.assertGreater(len(self.fetched()), 3)                 # it had fetched several issues before it failed
        self.assertEqual(self.files(), before)
        self.assertEqual(self.state()["cursor"]["time"], CLOCK[1])
        self.assertIn("so nothing is saved", self.printed)

    def test_the_next_sync_recovers_every_issue_the_failed_one_missed(self):
        self.upto(1)
        self.sync(self.fail_at(8))
        self.assertEqual(self.sync(2), 0)
        self.assertEqual(self.fetched(), [2, 4, 6, 8, 9, 10, 11])
        self.assertEqual([p["since"] for path, p in self.fake.calls if path == LISTING], ["2026-11-21T08:55:00Z"])
        self.assertIn("This sync: 0 new, 7 changed, 6 unchanged", self.printed)

    def test_after_recovery_the_local_state_is_what_it_would_have_been_with_no_failure(self):
        self.upto(1)
        self.sync(self.fail_at(8))
        self.sync(2)
        recovered = sync.digest(self.state()["issues"])
        with tempfile.TemporaryDirectory() as clean:
            for step in (0, 1, 2):
                self.sync(step, out=clean)
            self.assertEqual(sync.digest(self.state(clean)["issues"]), recovered)

    def test_a_failure_of_the_listing_or_the_repository_leaves_everything_too(self):
        self.upto(1)
        before = self.files()
        for prefix in (LISTING, "/repos/%s" % REPO):
            fake = FakeGitHub(2)
            fake.fail(prefix, 502)
            self.assertEqual(self.sync(fake), 1)
            self.assertEqual(self.files(), before)

    def test_a_failure_on_the_last_issue_leaves_everything_too(self):
        self.upto(1)
        before = self.files()
        self.assertEqual(self.sync(self.fail_at(10)), 1)
        self.assertEqual(self.files(), before)

    def test_two_failures_in_a_row_then_a_recovery(self):
        self.upto(1)
        self.sync(self.fail_at(4))
        self.sync(self.fail_at(9))
        self.assertEqual(self.state()["cursor"]["time"], CLOCK[1])
        self.assertEqual(self.sync(2), 0)
        self.assertEqual(self.fetched(), [2, 4, 6, 8, 9, 10, 11])

    def test_the_cursor_is_written_after_the_issues(self):
        self.upto(0)
        order = []
        real = sync.write_text
        with mock.patch.object(sync, "write_text", lambda path, text, out: (order.append(os.path.basename(path)), real(path, text, out))):
            self.sync(1)
        self.assertEqual(order, ["issues.md", "state.json", "sync-state.md"])

    def test_a_crash_while_writing_the_issues_leaves_the_cursor(self):
        self.upto(0)

        def broken(path, text, out):
            raise OSError("made-up disk failure")
        with mock.patch.object(sync, "write_text", broken), self.assertRaises(OSError):
            self.sync(1)
        self.assertEqual(self.state()["cursor"]["time"], CLOCK[0])
        self.assertEqual(self.sync(1), 0)
        self.assertEqual(self.fetched(), [3, 5, 7, 13])

    def test_a_rate_limit_that_does_not_clear_writes_nothing(self):
        self.upto(1)
        before = self.files()
        fake = FakeGitHub(2)
        fake.fail(COMMENTS % 6, 429, times=9, headers={"Retry-After": "1"})
        self.assertEqual(self.sync(fake), 2)
        self.assertIn("INCOMPLETE: GitHub rate-limited this run. Nothing was written", self.printed)
        self.assertEqual(self.files(), before)

    def test_a_rate_limit_that_clears_is_waited_for(self):
        self.upto(1)
        fake = FakeGitHub(2)
        fake.fail(COMMENTS % 6, 403, times=1, headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1004"})
        self.assertEqual(self.sync(fake), 0)
        self.assertEqual(self.client.waits, [5])


class Counts(Base):
    """Criterion 5."""

    def test_the_run_reports_new_changed_and_unchanged(self):
        self.sync(0)
        self.sync(1)
        self.assertIn("issues in the repository: 13. This sync: 1 new, 3 changed, 9 unchanged (9 not fetched, 0 fetched and found the same), "
                      "0 no longer in the repository", self.printed)

    def test_each_fetched_issue_is_said_to_be_new_or_changed_with_what_changed(self):
        self.sync(0)
        self.sync(1)
        self.assertIn("fetched: issue %s, number 13. NEW" % node(13), self.printed)
        self.assertIn("fetched: issue %s, number 5. CHANGED (state, state_reason, updated_at, closed_at)" % node(5), self.printed)
        self.assertIn("fetched: issue %s, number 3. CHANGED (updated_at, comments)" % node(3), self.printed)

    def test_the_counts_add_up_to_the_issues_held(self):
        self.upto(2)
        found = re.search(r"issues in the repository: (\d+)\. This sync: (\d+) new, (\d+) changed, (\d+) unchanged", self.printed)
        held, new, changed, unchanged = map(int, found.groups())
        self.assertEqual((held, new + changed + unchanged), (13, 13))

    def test_the_state_file_holds_the_counts_of_the_last_sync(self):
        self.sync(0)
        self.sync(1)
        self.assertEqual({k: self.state()["last"][k] for k in ("new", "changed", "unchanged", "fetched", "held")},
                         {"new": 1, "changed": 3, "unchanged": 9, "fetched": 4, "held": 13})

    def test_the_screen_output_holds_no_title(self):
        self.upto(2)
        for text in ("Tracker task", "Report", "IGNORE"):
            self.assertNotIn(text, self.printed)


class Notes(Base):
    """Criterion 6."""

    def setUp(self):
        super().setUp()
        self.note(node(3) + ".md", "A made-up analysis of issue 3.\n")
        self.note(node(12) + ".md", "A made-up analysis with no newline at the end")
        self.start = sync.notes_checksums(self.out)

    def test_notes_are_byte_identical_after_every_kind_of_sync(self):
        self.upto(1)
        fake = FakeGitHub(2)
        fake.fail(COMMENTS % 8, 500)
        for run in (lambda: self.sync(fake), lambda: self.sync(2), lambda: self.sync(3), lambda: self.sync(3, verify=True),
                    lambda: self.sync(3, full=True)):
            run()
            self.assertEqual(sync.notes_checksums(self.out), self.start)
        self.assertNotIn("DIFFERENT  ", self.printed.replace("DIFFERENT: issue", ""))

    def test_each_sync_prints_the_checksums_before_and_after(self):
        self.sync(0)
        self.assertEqual(self.printed.count("  same"), 2)
        self.assertIn("notes/%s.md  before %s  after %s  same" % (node(3), self.start[node(3) + ".md"], self.start[node(3) + ".md"]), self.printed)

    def test_the_one_writing_function_refuses_the_notes_folder(self):
        with self.assertRaises(sync.Stop):
            sync.write_text(os.path.join(self.out, "notes", "x.md"), "x", self.out)
        with self.assertRaises(sync.Stop):
            sync.write_text(os.path.join(self.out, "a", "..", "notes", "deep", "x.md"), "x", self.out)

    def test_note_text_is_copied_nowhere(self):
        self.upto(1)
        self.assertFalse([name for name, data in self.files().items() if not name.startswith("notes") and b"made-up analysis" in data])

    def test_the_issues_file_shows_which_issues_have_notes_even_when_gone(self):
        self.upto(3)
        self.sync(3, full=True)
        text = self.read("issues.md")
        self.assertIn("`notes/%s.md` |" % node(3), [l for l in text.splitlines() if l.startswith("| #3 |")][0])
        self.assertIn("`notes/%s.md` |" % node(12), [l for l in text.splitlines() if l.startswith("| #12 |")][0])


class FullAndDeltas(Base):
    """Criterion 7, and the second stretch goal."""

    def full_into_empty(self, step):
        with tempfile.TemporaryDirectory() as fresh:
            self.assertEqual(self.sync(step, out=fresh), 0)
            return sync.digest(self.state(fresh)["issues"])

    def test_a_full_read_into_an_empty_folder_gives_the_digest_the_deltas_reached(self):
        for step in (0, 1, 2):
            self.assertEqual(self.sync(step), 0)
            self.assertEqual(sync.digest(self.state()["issues"]), self.full_into_empty(step))

    def test_the_digest_is_printed_by_every_sync(self):
        self.upto(2)
        self.assertIn("local state digest: %s (13 issues in the repository" % sync.digest(self.state()["issues"]), self.printed)

    def test_a_full_read_in_place_changes_nothing_when_the_deltas_were_right(self):
        self.upto(2)
        before = sync.digest(self.state()["issues"])
        self.assertEqual(self.sync(2, full=True), 0)
        self.assertEqual(self.fetched(), list(range(1, 14)))
        self.assertIn("This sync: 0 new, 0 changed, 13 unchanged (0 not fetched, 13 fetched and found the same)", self.printed)
        self.assertEqual(sync.digest(self.state()["issues"]), before)

    def test_the_digest_does_not_depend_on_when_or_how_often_it_was_synced(self):
        self.upto(2)
        state = self.state()
        again = json.loads(json.dumps(state))
        for record in again["issues"].values():
            record.update(first_seen="x", last_fetched="y")
        self.assertEqual(sync.digest(again["issues"]), sync.digest(state["issues"]))

    def test_the_digest_changes_when_a_field_or_a_comment_does(self):
        self.upto(2)
        state = self.state()
        base = sync.digest(state["issues"])
        for change in (lambda r: r.update(title="x"), lambda r: r.update(labels=[]), lambda r: r["comments"].append({"id": 1})):
            again = json.loads(json.dumps(state))
            change(again["issues"][node(2)])
            self.assertNotEqual(sync.digest(again["issues"]), base)

    def test_verify_says_the_same_and_writes_nothing(self):
        self.upto(2)
        before = self.files()
        self.assertEqual(self.sync(2, verify=True), 0)
        self.assertIn("the local copy and a full read are THE SAME", self.printed)
        self.assertEqual(self.files(), before)

    def test_verify_finds_a_change_a_delta_has_not_fetched_yet(self):
        self.upto(1)
        self.assertEqual(self.sync(2, verify=True), 3)
        self.assertIn("DIFFERENT: issue %s is held with different fields or comments" % node(8), self.printed)
        self.assertEqual(self.state()["cursor"]["time"], CLOCK[1])

    def test_verify_finds_a_missed_change_when_the_margin_is_taken_away(self):
        self.upto(1)
        self.sync(2, margin=0)
        self.assertEqual(self.sync(2, verify=True), 3)
        self.assertEqual(re.findall(r"DIFFERENT: issue (\S+)", self.printed), [node(11)])

    def test_verify_finds_an_issue_not_held(self):
        self.upto(0)
        self.assertEqual(self.sync(1, verify=True), 3)
        self.assertIn("DIFFERENT: issue %s is returned by GitHub and not held locally" % node(13), self.printed)


class Gone(Base):
    """The first stretch goal."""

    def setUp(self):
        super().setUp()
        self.upto(3)

    def test_a_delta_does_not_see_a_deleted_or_transferred_issue(self):
        self.assertEqual(self.fetched(), [9])
        self.assertEqual({r["status"] for r in self.state()["issues"].values()}, {"present"})

    def test_an_edited_comment_is_held_with_its_new_time(self):
        self.assertEqual([c["updated_at"] for c in self.state()["issues"][node(9)]["comments"]], ["2026-11-22T10:00:00Z"])
        fresh = FakeGitHub(3)
        fresh.item(9)["updated_at"] = "2026-11-21T14:00:00Z"       # as if the edit had not moved the issue's own time
        fresh.item(9)["comments"][0]["updated_at"] = "2026-11-25T10:00:00Z"
        self.assertEqual(self.sync(fresh, verify=True), 3)
        self.assertIn("DIFFERENT: issue %s is held with different fields or comments" % node(9), self.printed)

    def test_verify_says_the_local_copy_differs(self):
        self.assertEqual(self.sync(3, verify=True), 3)
        self.assertEqual(re.findall(r"DIFFERENT: issue (\S+) is held locally and not returned by GitHub", self.printed), [node(1), node(12)])

    def test_a_full_read_flags_them_with_why_and_deletes_nothing(self):
        self.assertEqual(self.sync(3, full=True), 0)
        issues = self.state()["issues"]
        self.assertEqual(len(issues), 13)
        self.assertEqual((issues[node(12)]["status"], issues[node(12)]["reason"], issues[node(12)]["state"]), ("gone", "deleted", "closed"))
        self.assertEqual((issues[node(1)]["status"], issues[node(1)]["reason"]), ("gone", "transferred"))
        self.assertIn("acme-fixture/archive#77", issues[node(1)]["detail"])
        self.assertIn("FLAGGED, not deleted: issue %s, number 12, is no longer in the repository: deleted. Last known state: closed (not_planned)"
                      % node(12), self.printed)
        text = self.read("issues.md")
        self.assertIn("## No longer in the repository (2)", text)
        self.assertIn("| #1 | Tracker task 1 | open | **transferred**:", text)

    def test_after_the_full_read_the_local_copy_and_github_agree(self):
        self.sync(3, full=True)
        self.assertEqual(self.sync(3, verify=True), 0)
        with tempfile.TemporaryDirectory() as fresh:
            self.sync(3, out=fresh)
            self.assertEqual(sync.digest(self.state(fresh)["issues"]), sync.digest(self.state()["issues"]))

    def test_they_stay_flagged_and_are_not_flagged_again(self):
        self.sync(3, full=True)
        self.assertEqual(self.sync(3, full=True), 0)
        self.assertNotIn("FLAGGED", self.printed)
        self.assertEqual(self.state()["issues"][node(12)]["since"], CLOCK[3])

    def test_an_unknown_answer_about_a_missing_issue_stops_the_run(self):
        before = self.files()
        fake = FakeGitHub(3)
        fake.fail("/repos/%s/issues/12" % REPO, 500, times=9)
        self.assertEqual(self.sync(fake, full=True), 1)
        self.assertIn("did not say what became of", self.printed)
        self.assertEqual(self.files(), before)

    def test_an_issue_still_there_that_the_full_read_missed_stops_the_run(self):
        fake = FakeGitHub(3)
        real = fake.get

        def get(path, params=None):
            status, headers, body = real(path, params)
            return status, headers, [row for row in body if row["number"] != 4] if path == LISTING else body
        self.assertEqual(self.sync(fake, get=get, full=True), 1)
        self.assertIn("still in the repository and the full read did not return it", self.printed)


class TheStateDocument(Base):
    def test_it_records_the_cursor_and_how_it_advances(self):
        self.upto(1)
        text = self.read("sync-state.md")
        for part in ("| Cursor | 2026-11-21T09:00:00Z |", "| The cursor is | GitHub's own clock, from the Date header of the first answer of the last successful sync |",
                     "| That sync was | a delta |", "| It asked for | issues updated at or after 2026-11-20T08:55:00Z: the cursor less a margin of 300 seconds |",
                     "| It fetched | 4 issues of the 13 held |", "| It found | 1 new, 3 changed, 9 unchanged, 0 no longer in the repository |",
                     "| Successful syncs so far | 2 |", "If any request fails, the run stops. No file is written.",
                     "This machine's clock is never used for the cursor"):
            self.assertIn(part, text)
        self.assertIn("| Digest of the local state | `%s` |" % sync.digest(self.state()["issues"]), text)

    def test_beside_the_default_folder_it_is_one_level_up(self):
        self.assertEqual(sync.state_doc_path(os.path.join("participant", "context", "github", "delta")),
                         os.path.join("participant", "context", "github", "sync-state.md"))
        self.assertEqual(sync.state_doc_path(self.out), os.path.join(self.out, "sync-state.md"))

    def test_a_failed_sync_does_not_rewrite_it(self):
        self.upto(1)
        before = self.read("sync-state.md")
        fake = FakeGitHub(2)
        fake.fail(COMMENTS % 8, 500)
        self.sync(fake)
        self.assertEqual(self.read("sync-state.md"), before)

    def test_staleness_is_said_and_flagged_past_the_limit(self):
        self.sync(0)
        later = FakeGitHub(0)
        later.now = CLOCK[2]
        self.sync(later)
        self.assertIn("48.0 hours before now (2026-11-22T09:00:00Z by this machine's clock). STALE: that is more than 24 hours", self.printed)


class Guards(Base):
    def test_one_folder_holds_one_repository_and_one_source(self):
        self.sync(0)
        with self.assertRaises(sync.Stop) as stop:
            sync.load_state(self.out, "fake", REPO, {"id": 999, "private": True})
        self.assertIn("another repository's issues", str(stop.exception))
        with self.assertRaises(sync.Stop) as stop:
            sync.load_state(self.out, "live", REPO, {"id": fake_github.REPO_ID, "private": True})
        self.assertIn("One folder holds one source", str(stop.exception))

    def test_a_repository_that_is_not_shown_stops_the_run(self):
        fake = FakeGitHub(0)
        fake.fail("/repos/%s" % REPO, 404)
        self.assertEqual(self.sync(fake), 1)
        self.assertIn("does not show the repository", self.printed)

    def test_a_rejected_token_stops_the_run(self):
        fake = FakeGitHub(0)
        fake.fail("/repos/%s" % REPO, 401)
        self.assertEqual(self.sync(fake), 1)
        self.assertIn("rejected the token", self.printed)

    def test_an_unusable_node_id_stops_the_run(self):
        fake = FakeGitHub(0)
        real = fake.get

        def get(path, params=None):
            status, headers, body = real(path, params)
            if path == LISTING:
                body[0]["node_id"] = "../outside"
            return status, headers, body
        self.assertEqual(self.sync(fake, get=get), 1)
        self.assertIn("no usable node ID", self.printed)

    def test_a_title_cannot_break_the_table(self):
        self.sync(0)
        self.assertIn("| #8 | Report \\| breaks (the)(https://example.invalid) 'table' | open |", self.read("issues.md"))


class OnlyReads(Base):
    def source(self):
        with open(os.path.join(os.path.dirname(HERE), "sync.py"), encoding="utf-8") as f:
            return f.read()

    def test_the_skill_has_no_way_to_send_anything_but_a_get(self):
        source = self.source()
        self.assertEqual(re.findall(r'method="(\w+)"', source), ["GET"])
        for word in ("POST", "PATCH", "PUT", "DELETE", "data="):
            self.assertNotIn(word, source)

    def test_the_token_goes_in_a_header_and_never_in_the_address(self):
        seen = {}

        class Response:
            status, headers = 200, {"Date": "Fri, 20 Nov 2026 09:00:00 GMT"}
            def read(self):
                return b"{}"
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False

        class Opener:
            def open(self, request, timeout=None):
                seen["request"] = request
                return Response()
        with mock.patch.dict(os.environ, PRETEND_ENV), mock.patch.object(sync.urllib.request, "build_opener", lambda *h: Opener()):
            answer = sync.live_get(LISTING, {"since": "2026-11-20T08:55:00Z"})
        request = seen["request"]
        self.assertEqual(request.full_url, "https://api.github.com/repos/acme-fixture/tracker/issues?since=2026-11-20T08%3A55%3A00Z")
        self.assertEqual((request.get_method(), request.get_header("Authorization"), request.data), ("GET", "Bearer " + PRETEND, None))
        self.assertNotIn(PRETEND, repr(answer))

    def test_the_token_is_not_printed_or_written(self):
        with mock.patch.dict(os.environ, PRETEND_ENV):
            self.sync(0)
        self.assertNotIn(PRETEND, self.printed)
        self.assertFalse([name for name, data in self.files().items() if PRETEND.encode() in data])

    def test_a_redirect_to_anywhere_but_githubs_api_is_refused(self):
        for where in ("https://example.invalid/repos/a/b/issues/1", "http://api.github.com/user", ""):
            answers = [(301, {"Location": where}, {}), (200, {}, {"followed": True})]
            client = sync.Client(lambda path, params: answers.pop(0))
            with self.assertRaises(sync.Stop):
                client.get("/user")
            self.assertEqual(client.count, 1)

    def test_every_request_is_counted_and_said(self):
        self.sync(0)
        self.sync(1)
        self.assertEqual(self.client.count, len(self.fake.calls))
        self.assertIn("requests made: 6, every one a GET (1 repository, 1 listing, 4 comments, 0 look-ups)", self.printed)


class CommandLine(Base):
    def main(self, *args):
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            code = sync.main(list(args))
        self.printed = printed.getvalue()
        return code

    def test_fake_runs_from_the_command_line(self):
        self.assertEqual(self.main("--source", "fake", "--out", self.out), 0)
        self.assertEqual(self.main("--source", "fake", "--fake-step", "1", "--out", self.out), 0)
        self.assertIn("This sync: 1 new, 3 changed, 9 unchanged", self.printed)

    def test_a_forced_failure_says_the_cursor_is_where_it_was(self):
        self.main("--source", "fake", "--out", self.out)
        self.assertEqual(self.main("--source", "fake", "--fake-step", "1", "--fake-fail-issue", "7", "--out", self.out), 1)
        self.assertIn("Nothing was written. The cursor is where it was: 2026-11-20T09:00:00Z.", self.printed)

    def test_a_failure_of_the_first_sync_says_there_is_no_cursor(self):
        self.assertEqual(self.main("--source", "fake", "--fake-fail-issue", "7", "--out", self.out), 1)
        self.assertIn("Nothing was written. There is no cursor yet.", self.printed)

    def test_status_contacts_nothing_and_writes_nothing(self):
        self.assertEqual(self.main("--status", "--out", self.out), 1)
        self.main("--source", "fake", "--out", self.out)
        before = self.files()
        self.assertEqual(self.main("--status", "--out", self.out), 0)
        self.assertIn("cursor: 2026-11-20T09:00:00Z. It is GitHub's own clock", self.printed)
        self.assertIn("nothing was contacted and nothing was written", self.printed)
        self.assertEqual(self.files(), before)

    def test_a_live_run_needs_a_repository_a_folder_and_a_token(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(self.main("--source", "live"), 1)
            self.assertIn("needs --repo", self.printed)
            self.assertEqual(self.main("--source", "live", "--repo", "a/b"), 1)
            self.assertIn("needs --out", self.printed)
            self.assertEqual(self.main("--source", "live", "--repo", "a/b", "--out", self.out), 1)
            self.assertIn("GITHUB_TOKEN is not set", self.printed)
        for bad in ("../x", "a/b/c", "a"):
            self.assertEqual(self.main("--source", "live", "--repo", bad, "--out", self.out), 1)
            self.assertIn("needs --repo", self.printed)

    def test_arguments_that_do_not_go_together(self):
        self.assertEqual(self.main("--source", "fake", "--full", "--verify", "--out", self.out), 1)
        self.assertEqual(self.main("--source", "live", "--fake-step", "1", "--repo", "a/b", "--out", self.out), 1)
        self.assertEqual(self.main("--out", self.out), 1)

    def test_a_memory_file_that_cannot_be_read_stops_the_run(self):
        os.makedirs(self.out)
        with open(os.path.join(self.out, "state.json"), "w") as f:
            f.write("{not json")
        self.assertEqual(self.main("--source", "fake", "--out", self.out), 1)
        self.assertIn("cannot be read as this skill's memory", self.printed)
        self.assertIn("the cursor is not known", self.printed)


if __name__ == "__main__":
    unittest.main()
