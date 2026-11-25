"""Tests for from_sync.py: the masking of a real sync. They use an invented sync, shaped like a real one. No real value is here."""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import digest as dg       # noqa: E402
import from_sync as fs    # noqa: E402

LOGIN, OTHER = "invented-owner-login", "invented-other-login"


def pretend(sync_at="2026-11-25T16:00:00Z", extra_issue=False):
    """An invented sync in the shape github-read-assigned saves. Its ids are made up and are of the real kinds."""
    def issue(number, node, title, state="open"):
        return {"assignees": [LOGIN], "author": LOGIN, "body": "A body that must not be copied, written by %s." % LOGIN, "closed_at": None, "created_at": "2026-11-20T10:00:00Z",
                "comments": [{"author": OTHER, "body": "A comment that must not be copied.", "id": 987654321, "created_at": "2026-11-21T10:00:00Z"}],
                "events": [{"actor": OTHER, "created_at": "2026-11-21T11:00:00Z", "detail": {"node_id": "PR_kwInvented0001", "actor": OTHER}, "event": "cross-referenced", "key": "cross-referenced:id:123456789"}],
                "first_seen": sync_at, "full_name": "%s/pretend-repo" % LOGIN, "id": 4000000000 + number, "labels": ["bug"], "last_synced": sync_at, "milestone": None,
                "node_id": node, "number": number, "previously": [], "private": True, "repo_id": 777000111, "state": state, "state_history": [], "state_reason": None,
                "status": "assigned", "title": title, "updated_at": "2026-11-22T10:00:00Z"}
    issues = {"I_kwInvented0001": issue(1, "I_kwInvented0001", "An invented task"), "I_kwInvented0002": issue(2, "I_kwInvented0002", "Another invented task", "closed")}
    if extra_issue:
        issues["I_kwInvented0003"] = issue(3, "I_kwInvented0003", "A third invented task")
    return {"identity": {"id": 55501234, "login": LOGIN}, "issues": issues, "last_successful_sync": sync_at, "pulls_left_out": 0, "schema": 1, "source": "live",
            "repos": {"777000111": {"full_name": "%s/pretend-repo" % LOGIN, "id": 777000111, "last_successful_sync": sync_at, "previously": [], "private": True, "pulls_left_out": 0, "seen_at": sync_at, "unreadable": None}},
            "scope": "RESTRICTED with --only-repos to 1 repository. This is not every repository"}


class Masking(unittest.TestCase):
    def test_no_real_value_is_left(self):
        text, real = fs.mask(pretend(), "a secret")
        for value in real | {LOGIN, OTHER, "55501234", "777000111", "987654321", "123456789"}:
            self.assertNotIn(value, text)
        self.assertNotRegex(text, r"\b(I|PR)_kw")

    def test_bodies_and_comments_are_not_copied_and_their_count_is_kept(self):
        masked = json.loads(fs.mask(pretend(), "a secret")[0])
        for issue in masked["issues"].values():
            self.assertEqual(issue["body"], "[not copied]")
            self.assertEqual([c["body"] for c in issue["comments"]], ["[not copied]"])

    def test_the_owner_and_another_person_are_told_apart_and_neither_is_named(self):
        masked = json.loads(fs.mask(pretend(), "a secret")[0])
        issue = list(masked["issues"].values())[0]
        self.assertEqual(issue["author"], "[owner]")
        self.assertEqual(issue["comments"][0]["author"], "[user 2]")
        self.assertEqual(issue["events"][0]["actor"], "[user 2]")
        self.assertEqual(masked["identity"], {"id": "[user id]", "login": "[owner]"})

    def test_titles_numbers_labels_states_and_times_are_kept(self):
        masked = json.loads(fs.mask(pretend(), "a secret")[0])
        got = sorted((i["number"], i["title"], i["state"], i["labels"], i["updated_at"]) for i in masked["issues"].values())
        self.assertEqual(got, [(1, "An invented task", "open", ["bug"], "2026-11-22T10:00:00Z"), (2, "Another invented task", "closed", ["bug"], "2026-11-22T10:00:00Z")])

    def test_the_same_item_has_the_same_masked_identity_on_another_day(self):
        monday = json.loads(fs.mask(pretend("2026-11-24T16:00:00Z"), "a secret")[0])
        tuesday = json.loads(fs.mask(pretend("2026-11-25T16:00:00Z", extra_issue=True), "a secret")[0])
        self.assertTrue(set(monday["issues"]) < set(tuesday["issues"]))
        self.assertEqual(len(set(tuesday["issues"]) - set(monday["issues"])), 1)

    def test_a_masked_identity_depends_on_the_secret(self):
        self.assertNotEqual(set(json.loads(fs.mask(pretend(), "one secret")[0])["issues"]), set(json.loads(fs.mask(pretend(), "another secret")[0])["issues"]))

    def test_a_masked_identity_is_one_the_digest_accepts(self):
        for node in json.loads(fs.mask(pretend(), "a secret")[0])["issues"]:
            self.assertRegex(node, r"^I_masked_[0-9a-f]{12}$")
            self.assertTrue(dg.IDENTITY.match("github:" + node))


class EndToEnd(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="gtq-from-sync-test-")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def build(self, day, **kw):
        real = os.path.join(self.root, "real-" + day)
        os.makedirs(real)
        with open(os.path.join(real, "assigned.json"), "w", encoding="utf-8") as f:
            json.dump(pretend(day + "T16:00:00Z", **kw), f)
        out = os.path.join(self.root, "context-" + day)
        with contextlib.redirect_stdout(io.StringIO()):   # it prints a line that says "real". Here the sync is invented
            self.assertEqual(fs.main([real, out]), 0)
        return out

    def test_a_sync_becomes_context_the_digest_reads_and_marks_as_live(self):
        out = self.build("2026-11-25")
        model, written = dg.generate(out, "2026-11-25T17:00:00Z", "none", os.path.join(self.root, "o"))
        self.assertEqual(len(model["fresh"]), 2)
        self.assertTrue(all(e["p"]["sync_source"] == "live" for e in model["items"].values()))
        self.assertIn("**Built from context that a real synchronization run wrote.**", written["standup-digest.md"])
        self.assertEqual(dg.check(out, "2026-11-25T17:00:00Z", os.path.join(self.root, "o")), [])
        self.assertNotIn(LOGIN, "".join(written.values()))

    def test_an_item_new_on_the_second_day_is_reported_as_added(self):
        first = self.build("2026-11-24")
        dg.generate(first, "2026-11-24T17:00:00Z", "none", os.path.join(self.root, "o1"))
        second = self.build("2026-11-25", extra_issue=True)
        model, _ = dg.generate(second, "2026-11-25T17:00:00Z", os.path.join(self.root, "o1", "digest-state.json"), os.path.join(self.root, "o2"))
        self.assertEqual([kind for kind, _, _ in model["changes"]], ["ADDED"])

    def test_a_folder_that_is_not_a_real_sync_is_refused(self):
        real = os.path.join(self.root, "not-real")
        os.makedirs(real)
        with open(os.path.join(real, "assigned.json"), "w", encoding="utf-8") as f:
            json.dump(dict(pretend(), source="fake"), f)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(fs.main([real, os.path.join(self.root, "never")]), 1)
        self.assertFalse(os.path.exists(os.path.join(self.root, "never")))

    def test_the_secret_is_kept_beside_the_real_folder_and_not_in_the_context(self):
        out = self.build("2026-11-25")
        self.assertTrue(os.path.exists(os.path.join(self.root, "mask-secret.txt")))
        held = dg.read(os.path.join(self.root, "mask-secret.txt")).strip()
        for folder, _, files in os.walk(out):
            for name in files:
                with open(os.path.join(folder, name), encoding="utf-8") as f:
                    self.assertNotIn(held, f.read())


if __name__ == "__main__":
    unittest.main()
