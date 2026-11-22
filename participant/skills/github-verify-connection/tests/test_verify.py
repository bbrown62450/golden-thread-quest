"""Tests for the github-verify-connection skill. Every test runs against fake_github.py. None contacts GitHub."""
import contextlib
import io
import os
import re
import sys
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import fake_github  # noqa: E402
import verify  # noqa: E402
from fake_github import EMPTY, NOWHERE, PAYROLL, TRACKER, FakeGitHub  # noqa: E402

PRETEND = "github" + "_pat_" + "Z9" * 20         # shaped like a token, and stands in for one. It is not one
PRETEND_ENV = dict([("GITHUB_TOKEN", PRETEND)])
PLAIN = "-".join(("plain", "stand", "in", "value"))      # a made-up value with no token shape


class Base(unittest.TestCase):
    def check(self, *expect, case="fine-grained", fake=None, token=None):
        """Run the check against a made-up GitHub. Returns the exit code. The output is in self.out."""
        self.fake = fake or FakeGitHub(case)
        self.client = verify.Client(self.fake.get)
        report, code = verify.Report(), 1
        try:
            code = verify.run(self.client, report, list(expect or [TRACKER]))
        except verify.Stop as stop:
            report.say("STOPPED: %s." % stop)
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            clean = report.finish(token)
        self.out = printed.getvalue()
        return code if clean else 3

    def line(self, start):
        return next((row for row in self.out.splitlines() if start in row), "")


class Who(Base):
    """Criterion 1."""

    def test_the_identity_is_asked_from_github(self):
        self.assertEqual(self.check(), 0)
        self.assertEqual(self.fake.calls[0][0], "/user")
        self.assertIn("1. WHO. The connection acts as login robin-fixture, user id 9001", self.out)

    def test_no_login_is_written_in_the_skill_or_taken_as_an_argument(self):
        with open(os.path.join(os.path.dirname(HERE), "verify.py"), encoding="utf-8") as f:
            source = f.read()
        self.assertNotIn("robin-fixture", source)
        self.assertNotIn("--login", source)
        self.assertNotIn("--user", source)

    def test_another_identity_is_reported_as_that_identity(self):
        fake = FakeGitHub()
        fake.leak = "someone-else-fixture"
        self.check(fake=fake)
        self.assertIn("acts as login someone-else-fixture", self.out)

    def test_a_rejected_token_stops_the_check_and_is_not_called_fine(self):
        self.assertEqual(self.check(case="rejected"), 1)
        self.assertIn("STOPPED: GitHub rejected the token (401)", self.out)
        self.assertNotIn("REACHABLE", self.out)
        self.assertNotIn("every expected repository can be read", self.out)

    def test_an_answer_with_no_login_stops_the_check(self):
        fake = FakeGitHub()
        fake.fail("/user", 500)
        self.assertEqual(self.check(fake=fake), 1)
        self.assertIn("did not say who the connection acts as (status 500)", self.out)


class Scopes(Base):
    """Criterion 2, and the scopes broader than needed of criterion 7."""

    def test_classic_scopes_are_reported_one_by_one(self):
        self.assertEqual(self.check(case="classic-wide"), 0)
        self.assertIn("The scopes GitHub reports for this connection are: delete_repo, read:org, repo, workflow", self.out)
        self.assertIn("scope read:org: read-only", self.out)
        for scope in ("delete_repo", "repo", "workflow"):
            self.assertIn("scope %s: ALLOWS MORE THAN READING" % scope, self.out)

    def test_scopes_broader_than_needed_are_counted_in_the_result(self):
        self.check(case="classic-wide")
        self.assertIn("RESULT: every expected repository can be read. 3 scopes are broader than reading needs", self.out)

    def test_a_fine_grained_token_is_said_to_report_no_scopes(self):
        self.check()
        self.assertIn("GitHub reports no scopes for this token, as it does for a fine-grained token", self.out)
        self.assertIn("Whether it may write is NOT tested", self.out)
        self.assertNotIn("broader than reading needs", self.out)

    def test_an_empty_scope_list_is_reported_as_none(self):
        fake = FakeGitHub("classic-wide")
        fake.scopes = ""
        self.check(fake=fake)
        self.assertIn("The scopes GitHub reports for this connection are: none", self.out)

    def test_which_scopes_are_read_only(self):
        self.assertTrue(verify.read_only_scope("read:org") and verify.read_only_scope("repo:status"))
        for scope in ("repo", "public_repo", "write:org", "admin:org", "delete_repo", "workflow", "gist", "user"):
            self.assertFalse(verify.read_only_scope(scope))

    def test_the_expiry_is_reported_with_the_days_left_by_githubs_clock(self):
        self.check()
        self.assertIn("the token expires: 2026-11-27 09:00:00 UTC, 7.0 days from now by GitHub's clock", self.out)

    def test_an_expiry_that_has_passed_or_is_absent_is_said(self):
        fake = FakeGitHub()
        fake.expires = "2026-11-19 09:00:00 UTC"
        self.check(fake=fake)
        self.assertIn("already past", self.out)
        self.check(case="classic-wide")
        self.assertIn("GitHub reports no expiry date for it", self.out)


class Reachable(Base):
    """Criterion 3."""

    def test_the_repositories_are_listed_by_full_name(self):
        self.check()
        self.assertIn("3. REPOSITORIES GITHUB LISTS FOR THIS CONNECTION: 3", self.out)
        self.assertIn("     acme-fixture/empty-start, private.", self.out)
        self.assertIn("     acme-fixture/tracker, private.", self.out)
        self.assertIn("     robin-fixture/notes, public.", self.out)
        self.assertNotIn("     acme-fixture/payroll,", self.out)

    def test_a_public_repository_is_listed_and_readable_without_being_granted_and_the_run_says_so(self):
        self.assertEqual(self.check(fake_github.NOTES_REPO), 0)
        self.assertNotIn(fake_github.NOTES_REPO, self.fake.granted)
        self.assertIn("robin-fixture/notes: REACHABLE", self.out)
        self.assertIn("note: 1 of these is public. A public repository is listed, and can be read, whatever the token was given. "
                      "Being listed here does not show that the token was granted it", self.out)
        fake = FakeGitHub()
        fake.repos[fake_github.NOTES_REPO]["private"] = True
        self.check(fake=fake)
        self.assertNotIn("of these", self.out)

    def test_a_wider_token_lists_more(self):
        self.check(case="classic-wide")
        self.assertIn("LISTS FOR THIS CONNECTION: 4", self.out)
        self.assertIn("     robin-fixture/notes, public.", self.out)
        self.assertIn("     acme-fixture/payroll, private. GitHub says the ACCOUNT may: read", self.out)

    def test_what_the_account_may_do_is_not_passed_off_as_what_the_token_may_do(self):
        self.check()
        self.assertIn("GitHub says the ACCOUNT may: read, write", self.out)
        self.assertIn("GitHub does not say here whether this TOKEN may write", self.out)

    def test_a_list_that_cannot_be_read_is_not_reported_as_empty(self):
        fake = FakeGitHub()
        fake.list_status = 403
        self.assertEqual(self.check(fake=fake), 0)
        self.assertIn("THE LIST COULD NOT BE READ (status 403). This is not the same as an empty list", self.out)
        self.assertNotIn("its list is empty", self.out)

    def test_a_list_that_is_truly_empty_says_so(self):
        fake = FakeGitHub()
        fake.granted = set()
        fake.repos[fake_github.NOTES_REPO]["private"] = True
        self.check(fake=fake)
        self.assertIn("LISTS FOR THIS CONNECTION: 0", self.out)
        self.assertIn("none. GitHub answered, and its list is empty", self.out)

    def test_a_long_list_is_followed_page_by_page(self):
        fake = FakeGitHub("classic-wide")
        for n in range(150):
            fake.repos["acme-fixture/bulk-%03d" % n] = {"id": 1000 + n, "private": True, "issues": 0, "pulls": 0, "files": 0, "push": False}
        fake.granted = set(fake.repos)
        self.check(fake=fake)
        self.assertIn("LISTS FOR THIS CONNECTION: 154", self.out)
        self.assertEqual([p["page"] for path, p in fake.calls if path == "/user/repos"], [1, 2])


class Expected(Base):
    """Criterion 4: inaccessible and empty must not look the same."""

    def test_a_reachable_repository_is_reported_with_what_was_read(self):
        self.assertEqual(self.check(TRACKER), 0)
        self.assertIn("acme-fixture/tracker: REACHABLE. Reads allowed: repository (id 301, private); issues (12); pull requests (3); files (4)", self.out)

    def test_an_empty_repository_is_reachable_with_nothing_in_it(self):
        self.assertEqual(self.check(EMPTY), 0)
        self.assertIn("acme-fixture/empty-start: REACHABLE. Reads allowed: repository (id 302, private); issues (0); pull requests (0); "
                      "files (none: GitHub says the repository is empty)", self.out)

    def test_a_repository_outside_the_token_is_inaccessible_not_empty(self):
        self.assertEqual(self.check(PAYROLL), 3)
        row = self.line("acme-fixture/payroll:")
        self.assertIn("INACCESSIBLE (status 404). Nothing in it could be read. This is NOT an empty repository", row)
        self.assertNotIn("REACHABLE", row)
        self.assertNotIn("(0)", row)

    def test_empty_and_inaccessible_are_different_lines_with_different_words(self):
        self.assertEqual(self.check(EMPTY, PAYROLL), 3)
        empty, denied = self.line("acme-fixture/empty-start:"), self.line("acme-fixture/payroll:")
        self.assertIn("REACHABLE", empty)
        self.assertIn("issues (0)", empty)
        self.assertIn("INACCESSIBLE", denied)
        self.assertNotIn("issues", denied)

    def test_a_repository_that_does_not_exist_gets_the_same_honest_answer(self):
        self.assertEqual(self.check(NOWHERE), 3)
        self.assertIn("acme-fixture/nowhere: INACCESSIBLE (status 404)", self.out)
        self.assertIn("the two cannot be told apart from here", self.out)

    def test_the_other_reads_are_not_tried_on_an_inaccessible_repository(self):
        self.check(PAYROLL)
        self.assertEqual([path for path, _ in self.fake.calls if PAYROLL in path], ["/repos/%s" % PAYROLL])

    def test_access_lost_since_last_week_fails_the_check(self):
        self.assertEqual(self.check(TRACKER, EMPTY), 0)
        self.assertEqual(self.check(TRACKER, EMPTY, case="lost-access"), 3)
        self.assertIn("acme-fixture/tracker: INACCESSIBLE (status 404)", self.out)
        self.assertIn("acme-fixture/empty-start: REACHABLE", self.out)
        self.assertIn("RESULT: 1 expected repository CANNOT be read: acme-fixture/tracker", self.out)

    def test_a_refused_read_of_issues_is_not_reported_as_no_issues(self):
        self.assertEqual(self.check(TRACKER, case="issues-refused"), 3)
        self.assertIn("issues: REFUSED (status 403). The check needs this read", self.out)
        self.assertIn("This is not the same as having no issues", self.out)
        self.assertNotIn("issues (0)", self.out)

    def test_a_refused_read_the_check_does_not_need_is_only_reported(self):
        fake = FakeGitHub()
        fake.refused = {(TRACKER, "contents"), (TRACKER, "pulls")}
        self.assertEqual(self.check(TRACKER, fake=fake), 0)
        self.assertIn("files: REFUSED (status 403). Not needed by the check, so this is only reported", self.out)
        self.assertIn("pull requests: REFUSED (status 403)", self.out)

    def test_a_renamed_repository_is_reported_as_moved_and_not_followed(self):
        self.assertEqual(self.check(TRACKER, case="renamed"), 3)
        self.assertIn("acme-fixture/tracker: MOVED (status 301)", self.out)
        self.assertEqual(len(self.fake.calls), 3)

    def test_a_server_error_on_a_repository_is_inaccessible_with_its_status(self):
        fake = FakeGitHub()
        fake.fail("/repos/%s" % TRACKER, 502)
        self.assertEqual(self.check(TRACKER, fake=fake), 3)
        row = self.line("acme-fixture/tracker:")
        self.assertIn("INACCESSIBLE (status 502)", row)
        self.assertNotIn("cannot be told apart", row)

    def test_pull_requests_are_not_counted_as_issues(self):
        self.check(TRACKER)
        self.assertIn("issues (12); pull requests (3)", self.out)

    def test_more_than_one_page_of_issues_is_said_not_counted_short(self):
        fake = FakeGitHub()
        fake.bulk(TRACKER, 250)
        self.check(TRACKER, fake=fake)
        self.assertIn("issues (100 on the first page, and there are more)", self.out)

    def test_a_repository_read_by_name_and_missing_from_the_list_is_noted(self):
        fake = FakeGitHub()
        real = fake._answer
        fake._answer = lambda path, params: (200, {}, []) if path == "/user/repos" else real(path, params)
        self.assertEqual(self.check(TRACKER, fake=fake), 0)
        self.assertIn("it can be read by name, and GitHub's list in part 3 does not include it", self.out)

    def test_the_safe_read_is_reported_or_said_not_to_have_been_made(self):
        self.check(TRACKER)
        self.assertIn("5. ONE SAFE READ. The issues of acme-fixture/tracker were asked for and GitHub returned 12. Only the count was used", self.out)
        self.check(PAYROLL)
        self.assertIn("5. ONE SAFE READ. NOT MADE: no expected repository could be read", self.out)

    def test_no_title_is_printed(self):
        self.check(TRACKER, EMPTY)
        self.assertNotIn("Made-up issue", self.out)
        self.assertNotIn("file-0.md", self.out)


class OnlyReads(Base):
    """Criterion 5."""

    def test_the_skill_has_no_way_to_send_anything_but_a_get(self):
        with open(os.path.join(os.path.dirname(HERE), "verify.py"), encoding="utf-8") as f:
            source = f.read()
        self.assertEqual(re.findall(r'method="(\w+)"', source), ["GET"])
        for word in ("POST", "PATCH", "PUT", "DELETE"):
            self.assertIsNone(re.search(r"\b%s\b" % word, source), word)      # as a word: "OUTPUT" holds "PUT"
        self.assertNotIn("data=", source)

    def test_every_request_is_listed_and_the_list_matches_what_was_received(self):
        self.check(TRACKER, PAYROLL)
        listed = [row.split(":", 1)[1].strip() for row in self.out.splitlines() if row.startswith("github-verify:      GET ")]
        self.assertEqual(listed, ["GET %s" % path for path, _ in self.fake.calls])
        self.assertIn("6. ONLY READS. 7 requests were made, and every one was a GET", self.out)

    def test_the_check_writes_no_file(self):
        with open(os.path.join(os.path.dirname(HERE), "verify.py"), encoding="utf-8") as f:
            source = f.read()
        self.assertNotIn("open(", source.replace(".open(request", ""))
        self.assertNotIn("os.makedirs", source)

    def test_a_live_request_does_not_follow_redirects(self):
        self.assertIsNone(verify._NoRedirect().redirect_request(None, None, 301, "", {}, "https://example.invalid/"))


class Credential(Base):
    """Criterion 6."""

    def live(self):
        seen = {}

        class Response:
            status, headers = 200, {}
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
        with mock.patch.dict(os.environ, PRETEND_ENV), mock.patch.object(verify.urllib.request, "build_opener", lambda *h: Opener()):
            answer = verify.live_get("/user/repos", {"page": 2})
        return seen["request"], answer

    def test_the_token_goes_in_a_header_and_never_in_the_address(self):
        request, answer = self.live()
        self.assertEqual(request.full_url, "https://api.github.com/user/repos?page=2")
        self.assertEqual((request.get_method(), request.get_header("Authorization"), request.data), ("GET", "Bearer " + PRETEND, None))
        self.assertNotIn(PRETEND, repr(answer))

    def test_the_output_says_it_was_scanned_and_found_nothing(self):
        self.assertEqual(self.check(token=PRETEND), 0)
        self.assertIn("7. SCAN OF THIS OUTPUT.", self.out)
        self.assertIn("for the token's own value and for anything shaped like a GitHub token. Nothing was found", self.out)
        self.assertNotIn(PRETEND, self.out)

    def test_the_token_echoed_back_by_github_is_redacted_before_printing(self):
        fake = FakeGitHub()
        fake.leak = PLAIN
        self.assertEqual(self.check(fake=fake, token=PLAIN), 3)
        self.assertNotIn(PLAIN, self.out)
        self.assertIn("acts as login [REDACTED]", self.out)
        self.assertIn("FOUND in 1 line, and replaced with [REDACTED]. Treat the token as exposed and revoke it", self.out)

    def test_anything_shaped_like_a_token_is_redacted_even_when_it_is_not_this_token(self):
        for shaped in ("ghp_" + "a1B2" * 9, "github_pat_" + "11ABC_" * 6, "gho_" + "x" * 36):
            fake = FakeGitHub()
            fake.leak = shaped
            self.assertEqual(self.check(fake=fake), 3)
            self.assertNotIn(shaped, self.out)
            self.assertIn("[REDACTED]", self.out)

    def test_nothing_is_printed_before_the_scan(self):
        report, printed = verify.Report(), io.StringIO()
        with contextlib.redirect_stdout(printed):
            verify.run(verify.Client(FakeGitHub().get), report, [TRACKER])
            self.assertEqual(printed.getvalue(), "")
            report.finish(None)
        self.assertIn("1. WHO.", printed.getvalue())

    def test_ordinary_words_are_not_redacted(self):
        self.check(TRACKER, EMPTY, PAYROLL)
        self.assertNotIn("[REDACTED]", self.out)


class CommandLine(Base):
    def main(self, *args):
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            code = verify.main(list(args))
        self.out = printed.getvalue()
        return code

    def test_a_fake_run_from_the_command_line(self):
        self.assertEqual(self.main("--source", "fake", "--expect", TRACKER, "--expect", EMPTY), 0)
        self.assertIn('source: a made-up GitHub, fake_github.py, with the made-up token "fine-grained"', self.out)
        self.assertEqual(self.main("--source", "fake", "--fake-case", "lost-access", "--expect", TRACKER), 3)

    def test_at_least_one_expected_repository_is_required(self):
        self.assertEqual(self.main("--source", "fake"), 1)
        self.assertIn("give at least one --expect", self.out)
        self.assertIn("RESULT: the check could not be made. That is not the same as the connection being fine", self.out)

    def test_bad_names_and_cases_are_refused(self):
        for bad in ("tracker", "a/b/c", "../x", "a/b?x=1"):
            self.assertEqual(self.main("--source", "fake", "--expect", bad), 1)
            self.assertIn("owner/name", self.out)
        self.assertEqual(self.main("--source", "fake", "--fake-case", "nope", "--expect", TRACKER), 1)

    def test_a_live_run_needs_the_token_and_says_so_without_contacting_anything(self):
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(verify, "live_get", side_effect=AssertionError("contacted")):
            self.assertEqual(self.main("--source", "live", "--expect", TRACKER), 1)
        self.assertIn("GITHUB_TOKEN is not set", self.out)

    def test_a_live_run_scans_for_the_tokens_own_value(self):
        fake = FakeGitHub()
        fake.leak = PLAIN
        with mock.patch.dict(os.environ, dict([("GITHUB_TOKEN", fake.leak)])), mock.patch.object(verify, "live_get", fake.get):
            self.assertEqual(self.main("--source", "live", "--expect", TRACKER), 3)
        self.assertNotIn(PLAIN, self.out)

    def test_a_rate_limit_stops_the_check(self):
        fake = FakeGitHub()
        real = fake.get
        with mock.patch.dict(os.environ, PRETEND_ENV), \
                mock.patch.object(verify, "live_get", lambda path, params: (429, {}, {}) if path != "/user" else real(path, params)):
            self.assertEqual(self.main("--source", "live", "--expect", TRACKER), 1)
        self.assertIn("rate-limiting this connection", self.out)


if __name__ == "__main__":
    unittest.main()
