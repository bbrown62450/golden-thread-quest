"""Tests for comment.py, against the fake Jira. No network. Each test gets its own fake and its own folder."""
import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, SKILL)
import comment as cm      # noqa: E402
import fake_jira as fj    # noqa: E402

HOST = "fixture-site.example.invalid"
TEXT = "Checked against the made-up onboarding checklist on 25 November.\nNo change to the story is needed. This is a test comment."
ME, OTHER = fj.ME, fj.OTHER


def made_up_settings(base):
    """The three settings a live run reads, with invented values. Nothing here is a real address or credential."""
    return dict(zip(("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN"), (base, "made-up@example.invalid", "made-up-value")))


class Case(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="gtq-comment-test-")
        self.state = os.path.join(self.root, "state")
        self.fake = fj.FakeJira()
        self.write_text(TEXT + "\n")
        self.write_change({"story": "SAND-1", "text_file": "comment.txt", "visibility": "everyone"})
        self.allowlist = os.path.join(self.root, "allowlist.json")
        self.write_allowlist([("738169e667642f09", "20001"), ("738169e667642f09", "20003")])

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def write_text(self, text, name="comment.txt"):
        with open(os.path.join(self.root, name), "w", encoding="utf-8", newline="") as f:
            f.write(text)

    def write_change(self, change, name="change.json"):
        with open(os.path.join(self.root, name), "w", encoding="utf-8") as f:
            json.dump(change, f)

    def write_allowlist(self, pairs):
        with open(self.allowlist, "w", encoding="utf-8") as f:
            json.dump({"sandbox_projects": [{"site_fingerprint": s, "project_id": p} for s, p in pairs]}, f)

    def go(self, command, may_write=None, host=HOST, **more):
        args = argparse.Namespace(command=command, change=os.path.join(self.root, more.pop("change", "change.json")), allowlist=self.allowlist,
                                  state=self.state, fingerprint=None, confirmed_by=None, result=None, pretend_minutes_later=0, log=None)
        for key, value in more.items():
            setattr(args, key, value)
        post = self.fake.post if (command == "confirm" if may_write is None else may_write) else None
        conn = cm.Connection(self.fake.get, post, host)
        del cm.LINES[:]
        code = cm.run(args, conn)
        return code, "\n".join(cm.LINES), conn

    def preview(self, **more):
        return self.go("preview", **more)

    def fingerprint(self, **more):
        code, out, _ = self.preview(**more)
        self.assertEqual(code, 0, out)
        return re.search(r"^Fingerprint of this preview: ([0-9a-f]{12})$", out, re.M).group(1)

    def confirm(self, fp, by="the participant", **more):
        return self.go("confirm", fingerprint=fp, confirmed_by=by, **more)

    def comments(self, issue="30001"):
        return self.fake.state["comments"][issue]

    def mine(self, issue="30001"):
        return [c for c in self.comments(issue) if c["author"]["accountId"] == ME]

    def posts(self):
        return [r for r in self.fake.requests if r[0] == "POST"]

    def refused(self, result, *parts):
        code, out, _ = result
        self.assertEqual(code, 1, out)
        self.assertIn("REFUSED:", out)
        self.assertIn("Nothing has been written.", out)
        for part in parts:
            self.assertIn(part, out)
        return out


class ThePreview(Case):
    def test_it_shows_the_site_the_project_and_the_story(self):
        _, out, _ = self.preview()
        self.assertIn("Jira site:  https://fixture-site.example.invalid  (site fingerprint 738169e667642f09)", out)
        self.assertIn("Project:    SAND (project id 20001). Kind of project, as Jira gives it: software.", out)
        self.assertRegex(out, r"On the sandbox allowlist: yes\. The allowlist is the file allowlist\.json, sha256 [0-9a-f]{16}, which lists 2 projects\.")
        self.assertIn("Story:      SAND-1 (issue id 30001).", out)
        self.assertIn("It would appear under the Jira account the API token belongs to", out)

    def test_it_shows_the_exact_text_line_for_line(self):
        _, out, _ = self.preview()
        shown = [line[6:] for line in out.split("\n") if line.startswith("    | ")]
        self.assertEqual("\n".join(shown), TEXT)
        self.assertIn("122 characters, 2 lines", out)

    def test_the_visibility_is_on_the_line_under_the_text(self):
        _, out, _ = self.preview()
        lines = out.split("\n")
        last = max(i for i, line in enumerate(lines) if line.startswith("    | "))
        self.assertTrue(lines[last + 1].startswith("  WHO CAN SEE IT: EVERYONE who can see the story SAND-1. No restriction is put on the comment."), lines[last + 1])
        self.assertIn("This workflow cannot list who that is, and cannot tell whether the project is open to customers", lines[last + 2])

    def test_it_says_where_the_text_came_from_with_the_files_checksum(self):
        _, out, _ = self.preview()
        with open(os.path.join(self.root, "comment.txt"), "rb") as f:
            sha = hashlib.sha256(f.read()).hexdigest()
        self.assertIn("Where the text came from: the file comment.txt beside the change file, sha256 %s." % sha, out)

    def test_it_writes_nothing_and_sends_only_reads(self):
        before = json.dumps(self.fake.state, sort_keys=True)
        _, out, conn = self.preview()
        self.assertEqual(json.dumps(self.fake.state, sort_keys=True), before)
        self.assertEqual(set(method for method, _ in conn.sent), {"GET"})
        self.assertEqual(self.posts(), [])
        self.assertIn("Every one was a GET, which reads and cannot change anything.", out)
        self.assertIn("PREVIEW. Nothing has been written.", out)

    def test_a_preview_has_no_way_to_write(self):
        _, _, conn = self.preview()
        with self.assertRaises(cm.Refused):
            conn.post_comment("30001", TEXT, {"kind": "everyone"})
        self.assertEqual(self.posts(), [])

    def test_the_two_snapshots_are_given_and_are_the_same(self):
        _, out, _ = self.preview()
        codes = re.findall(r"^Snapshot of the story and its comments as Jira returned them, (?:before|after) the preview:\s+([0-9a-f]{16})$", out, re.M)
        self.assertEqual(len(codes), 2)
        self.assertEqual(codes[0], codes[1])
        self.assertIn("The two are the same. Jira is unchanged, as far as two reads of the story and its comments can show.", out)

    def test_a_story_that_changes_during_the_preview_stops_it(self):
        calls = {"n": 0}
        real = self.fake.get

        def get(path, params=None):
            calls["n"] += 1
            if calls["n"] == 5:
                self.fake.other_comment("SAND-1", "Slipped in while the preview was being made.")
            return real(path, params)
        self.fake.get = get
        self.refused(self.preview(), "changed in Jira while the preview was being made")

    def test_it_records_the_permission_check(self):
        _, out, _ = self.preview()
        self.assertIn("  may see the story        (BROWSE_PROJECTS): yes", out)
        self.assertIn("  may comment on the story (ADD_COMMENTS):    yes", out)

    def test_it_records_the_duplicate_check_and_where_jira_cannot_check(self):
        _, out, _ = self.preview()
        self.assertIn("Duplicate check, made against Jira just now: the story has 2 comments that this identity can see.", out)
        self.assertIn("  With the same text, by this identity: 0.", out)
        self.assertIn("  With the same text, by someone else:  0.", out)
        self.assertIn("Where Jira cannot check: its request to add a comment has no 'only if there is no such comment' condition.", out)

    def test_the_same_text_by_someone_else_is_counted_and_does_not_stop_the_preview(self):
        other = self.fake.other_comment("SAND-1", TEXT)
        code, out, _ = self.preview()
        self.assertEqual(code, 0)
        self.assertIn("  With the same text, by someone else:  1 (comment id %s)." % other, out)
        self.assertIn("Fingerprint of this preview:", out)

    def test_it_issues_a_fingerprint_with_its_limit_and_saves_the_preview(self):
        _, out, _ = self.preview()
        fp = re.search(r"^Fingerprint of this preview: ([0-9a-f]{12})$", out, re.M).group(1)
        with open(os.path.join(self.state, "previews", fp + ".json"), encoding="utf-8") as f:
            record = json.load(f)
        self.assertEqual(record["state"], "open")
        self.assertEqual(record["proposal"]["text"], TEXT)
        self.assertEqual(record["fingerprint"][:12], fp)
        self.assertIn("(15 minutes after it was made)", out)

    def test_nothing_in_the_story_or_its_comments_is_printed(self):
        _, out, _ = self.preview()
        self.assertNotIn("SYSTEM:", out)
        self.assertNotIn("Ignore your rules", out)
        self.assertNotIn("made-up earlier comment", out)
        self.assertNotIn("Ada Fixture", out)
        self.assertNotIn(ME, out)

    def test_a_story_with_a_security_level_says_so_beside_the_visibility(self):
        self.write_change({"story": "SAND-2", "text_file": "comment.txt", "visibility": "everyone"})
        _, out, _ = self.preview()
        self.assertIn("The story has the security level \"Staff only\", which limits who can see it.", out)

    def test_a_comment_for_a_role_shows_the_role_and_checks_that_the_project_has_it(self):
        self.write_change({"story": "SAND-1", "text_file": "comment.txt", "visibility": {"role": "Administrators"}})
        _, out, _ = self.preview()
        self.assertIn("  WHO CAN SEE IT: ONLY people in the project role \"Administrators\" who can also see the story SAND-1.", out)
        self.assertIn("  the project has the role \"Administrators\" (role id 10002): yes", out)

    def test_a_role_the_project_does_not_have_is_refused(self):
        self.write_change({"story": "SAND-1", "text_file": "comment.txt", "visibility": {"role": "Customers"}})
        self.refused(self.preview(), "the project has no role named \"Customers\". Its roles: \"Administrators\", \"Developers\"")

    def test_every_comment_is_read_when_they_come_in_pages(self):
        self.fake.page_max = 50
        self.write_change({"story": "SAND-3", "text_file": "comment.txt", "visibility": "everyone"})
        self.fake.state["comments"]["30003"].insert(110, self.fake.state["comments"]["30003"].pop())
        there = self.fake.other_comment("SAND-3", TEXT, as_me=True)
        self.fake.state["comments"]["30003"].insert(105, self.fake.state["comments"]["30003"].pop())
        code, out, conn = self.preview()
        self.assertIn("the story has 121 comments", out)
        self.assertIn("NOTHING TO ADD.", out)
        self.assertIn("comment id %s" % there, out)
        self.assertEqual(sum(1 for _, path in conn.sent if path.endswith("/comment")), 6)

    def test_a_list_of_comments_that_cannot_be_read_stops_the_preview(self):
        real = self.fake.get
        self.fake.get = lambda path, params=None: (500, {}, {}) if path.endswith("/comment") else real(path, params)
        self.refused(self.preview(), "Jira did not list the story's comments (status 500), so the duplicate check cannot be made")


class TheText(Case):
    def refuse_text(self, text, *parts):
        self.write_text(text)
        out = self.refused(self.preview(), *parts)
        self.assertEqual(self.fake.requests, [], "a text that is refused is refused before Jira is asked anything")
        return out

    def test_an_empty_text_is_refused(self):
        self.refuse_text("", "the text file is empty")
        self.refuse_text("\n", "the text file is empty")

    def test_a_text_that_is_too_long_is_refused(self):
        self.refuse_text("word " * 500, "characters long and the limit is 2000")
        self.refuse_text("\n".join("line" for _ in range(41)), "the text has 41 lines and the limit is 40")

    def test_an_empty_line_a_space_at_an_end_a_tab_and_an_unseen_character_are_refused(self):
        self.refuse_text("One.\n\nTwo.", "line 2 of the text is empty")
        self.refuse_text("One. \nTwo.", "line 1 of the text begins or ends with a space")
        self.refuse_text("One.\n Two.", "line 2 of the text begins or ends with a space")
        self.refuse_text("One\tand two.", "line 1 of the text has a tab or a character that cannot be seen")
        self.refuse_text("One" + chr(0x200b) + "and two.", "line 1 of the text has a tab or a character that cannot be seen")
        self.refuse_text("One" + chr(0x202e) + "and two.", "cannot be seen")

    def test_the_line_ending_at_the_end_of_the_file_is_not_part_of_the_comment_and_other_endings_are_read(self):
        self.write_text("One.\r\nTwo.\r\n")
        fp = self.fingerprint()
        self.confirm(fp)
        self.assertEqual(cm.text_of(self.mine()[0]["body"])[0], "One.\nTwo.")

    def test_a_file_that_is_not_text_is_refused(self):
        with open(os.path.join(self.root, "comment.txt"), "wb") as f:
            f.write(b"\xff\xfe\x00")
        self.refused(self.preview(), "the text file is not UTF-8 text")

    def test_a_text_that_looks_as_if_it_holds_a_secret_is_refused_and_the_secret_is_not_shown(self):
        made_up = {
            "an AWS access key": "AK" + "IA" + "Q7" * 8,
            "a private key": "-----BEGIN RSA " + "PRIVATE KEY-----",
            "a GitHub token": "gh" + "p_" + "a1B2" * 9,
            "a Slack token": "xo" + "xb-" + "1234567890-abcdefghij",
            "an Atlassian API token": "ATA" + "TT3" + "xFfGF0" * 5,
            "a JSON web token": "ey" + "J" + "hbGciOiJIUzI1" + "." + "eyJzdWIiOiIxMjM0" + "." + "SflKxwRJSMeKKF2Q",
            "a password, key or token written out": "the pass" + "word is " + "hunter2hunter2",
            "a web address with a password in it": "https://deploy" + ":" + "s3cr3t" + "@" + "host.example.invalid/x",
            "a long run of letters and digits, as a key is": "9f8e7d6c5b4a" + "39281706f5e4d3c2b1a0" + "ffee",
        }
        self.assertEqual(sorted(made_up), sorted(what for what, _ in cm.SECRETS))
        for what, sample in made_up.items():
            out = self.refuse_text("The value to use: %s\nThank you." % sample, "the text looks as if it holds %s, on line 1" % what, "The matching text is not shown here")
            self.assertNotIn(sample, out, what)

    def test_ordinary_text_is_not_taken_for_a_secret(self):
        for text in ("The token count is fine and the password reset page works.", "See build 20261125 and commit abc1234.",
                     "Supercalifragilisticexpialidocious is a long word with no digits in it at all."):
            self.assertEqual(cm.check_text(text), [], text)

    def test_what_may_be_private_is_pointed_out_and_not_refused(self):
        self.write_text("Ask sam.example@example.invalid or ring 020 7946 0000.\nSee https://example.invalid/page and tell @harbour-team.\nThis part is confidential.")
        code, out, _ = self.preview()
        self.assertEqual(code, 0)
        self.assertIn("LOOK AT THESE BEFORE CONFIRMING. They are not refused.", out)
        for line in ("  line 1: an email address", "  line 1: what may be a telephone number", "  line 2: a web address",
                     "  line 2: an @name, which is sent as text and mentions nobody", "  line 3: a word that marks something as private"):
            self.assertIn(line, out)
        self.assertIn("Fingerprint of this preview:", out)

    def test_a_text_with_nothing_to_point_out_says_what_was_looked_for_and_that_it_is_not_a_judgement(self):
        _, out, _ = self.preview()
        self.assertNotIn("LOOK AT THESE", out)
        self.assertIn("It is not a judgement that the", out)

    def test_an_at_name_is_sent_as_text_and_mentions_nobody(self):
        self.write_text("Thanks @harbour-team for the review.")
        self.confirm(self.fingerprint())
        body = self.mine()[0]["body"]
        self.assertEqual([node["type"] for block in body["content"] for node in block["content"]], ["text"])


class TheChangeFile(Case):
    def test_it_must_have_exactly_its_three_names(self):
        self.write_change({"story": "SAND-1", "text_file": "comment.txt"})
        self.refused(self.preview(), "the change file must have exactly 'story', 'text_file' and 'visibility'")
        self.write_change({"story": "SAND-1", "text_file": "comment.txt", "visibility": "everyone", "notify": False})
        self.refused(self.preview(), "the change file must have exactly")

    def test_the_text_file_is_a_plain_name_beside_the_change_file(self):
        for name in ("../comment.txt", "sub/comment.txt", "/etc/hosts", ".hidden"):
            self.write_change({"story": "SAND-1", "text_file": name, "visibility": "everyone"})
            self.refused(self.preview(), "text_file is the name of a file beside the change file")
        self.write_change({"story": "SAND-1", "text_file": "missing.txt", "visibility": "everyone"})
        self.refused(self.preview(), "there is no text file named missing.txt beside the change file")

    def test_only_everyone_or_one_role_is_a_visibility(self):
        for bad in ("public", {"group": "jira-users"}, {"role": ""}, {"role": "A", "group": "B"}, None, ["everyone"]):
            self.write_change({"story": "SAND-1", "text_file": "comment.txt", "visibility": bad})
            self.refused(self.preview(), "visibility must be \"everyone\", or {\"role\": \"the name of a project role\"}")

    def test_a_story_is_named_by_letters_digits_and_dashes(self):
        for bad in ("SAND-1/comment", "SAND 1", "", "SAND-1?expand=x"):
            self.write_change({"story": bad, "text_file": "comment.txt", "visibility": "everyone"})
            self.refused(self.preview(), "the story is given by its id or its key")

    def test_a_name_given_twice_in_the_change_file_is_refused(self):
        with open(os.path.join(self.root, "change.json"), "w", encoding="utf-8") as f:
            f.write('{"story": "SAND-1", "story": "PROD-9", "text_file": "comment.txt", "visibility": "everyone"}')
        self.refused(self.preview(), "gives the name \"story\" twice")

    def test_a_story_that_is_not_there_is_refused(self):
        self.write_change({"story": "SAND-99", "text_file": "comment.txt", "visibility": "everyone"})
        self.refused(self.preview(), "Jira answered 404 for the story")


class TheAllowlist(Case):
    def test_a_project_that_is_not_listed_is_refused_at_the_preview_before_anything_else_is_asked(self):
        self.write_change({"story": "PROD-9", "text_file": "comment.txt", "visibility": "everyone"})
        code, out, conn = self.preview()
        self.refused((code, out, conn), "project PROD (project id 20002) on the Jira site with fingerprint 738169e667642f09 is not on the sandbox allowlist (allowlist.json)")
        self.assertEqual(conn.sent, [("GET", "/rest/api/3/issue/PROD-9")])

    def test_a_project_taken_off_the_list_after_the_preview_is_refused_at_the_confirmation(self):
        fp = self.fingerprint()
        self.write_allowlist([("738169e667642f09", "20003")])
        self.refused(self.confirm(fp), "is not on the sandbox allowlist")
        self.assertEqual(self.posts(), [])
        self.assertEqual(self.mine(), [])

    def test_the_same_project_id_on_another_site_is_not_the_listed_project(self):
        self.refused(self.preview(host="another-site.example.invalid"), "is not on the sandbox allowlist")

    def test_a_story_moved_to_another_project_after_the_preview_is_refused(self):
        fp = self.fingerprint()
        self.fake.state["issues"]["30001"]["fields"]["project"].update(id="20002", key="PROD")
        self.refused(self.confirm(fp), "is not on the sandbox allowlist")
        self.assertEqual(self.posts(), [])

    def test_an_allowlist_that_is_not_one_is_refused(self):
        with open(self.allowlist, "w", encoding="utf-8") as f:
            f.write('{"sandbox_projects": [{"site_fingerprint": "*", "project_id": "20001"}]}')
        self.refused(self.preview(), "an entry in the sandbox allowlist is not a site fingerprint and a project id")
        os.remove(self.allowlist)
        self.refused(self.preview(), "there is no sandbox allowlist at the path given")

    def test_a_confirmation_against_another_site_is_refused(self):
        fp = self.fingerprint()
        self.refused(self.confirm(fp, host="another-site.example.invalid"), "this is not the Jira site the preview was made against")


class ThePermissionCheck(Case):
    def test_a_story_this_identity_may_not_comment_on_is_refused_though_its_project_is_listed(self):
        self.write_change({"story": "RO-1", "text_file": "comment.txt", "visibility": "everyone"})
        self.refused(self.preview(), "Jira says this identity may not comment on this story (ADD_COMMENTS: no)")

    def test_a_permission_taken_away_after_the_preview_is_refused_at_the_confirmation(self):
        fp = self.fingerprint()
        self.fake.state["may_comment"]["20001"] = False
        self.refused(self.confirm(fp), "may not comment on this story")
        self.assertEqual(self.posts(), [])

    def test_no_answer_to_the_permission_check_is_not_taken_as_yes(self):
        real = self.fake.get
        self.fake.get = lambda path, params=None: (500, {}, {}) if path.endswith("/mypermissions") else real(path, params)
        self.refused(self.preview(), "Jira did not answer the permission check (status 500), so nothing is assumed")


class TheConfirmation(Case):
    def test_a_confirmed_preview_adds_the_comment_once_with_the_exact_text(self):
        fp = self.fingerprint()
        code, out, conn = self.confirm(fp)
        self.assertEqual(code, 0, out)
        self.assertEqual(len(self.mine()), 1)
        self.assertEqual(self.mine()[0]["body"], cm.document_of(TEXT))
        self.assertEqual(len(self.posts()), 1)
        self.assertNotIn("visibility", self.mine()[0])
        self.assertIn("CONFIRMATION for preview %s, given by: the participant" % fp, out)
        self.assertIn("WRITTEN to Jira: one comment on story SAND-1. Jira answered 201 and gave it the comment id %s." % self.mine()[0]["id"], out)
        self.assertIn("The confirmation and the write happened in this one run of the command.", out)

    def test_the_comment_is_read_back_and_compared_with_the_preview(self):
        _, out, _ = self.confirm(self.fingerprint())
        self.assertIn("the text read back is the text previewed, character for character (122 characters, sha256 %s): yes" % hashlib.sha256(TEXT.encode()).hexdigest()[:16], out)
        self.assertIn("  its author is this identity: yes", out)
        self.assertIn("  its visibility is the one previewed: everyone who can see the story: yes", out)
        self.assertIn("  comments on the story with this text and this visibility by this identity, counted after the write: 1", out)

    def test_the_result_record_holds_what_the_quest_asks_for(self):
        fp = self.fingerprint()
        result = os.path.join(self.root, "out", "result.md")
        _, out, _ = self.confirm(fp, result=result)
        with open(result, encoding="utf-8") as f:
            text = f.read()
        comment_id = self.mine()[0]["id"]
        for part in ("- Issue key: SAND-1", "- Issue id: 30001", "- Identifier of what was created: Jira comment id %s, on that issue" % comment_id,
                     "- Target project: SAND (project id 20001), on the sandbox allowlist", "- Visibility: everyone who can see the story; no restriction on the comment",
                     "- Confirmed by: the participant, at ", "- Written at: ", "- Preview: fingerprint %s, made " % fp, "- To reverse: delete comment %s" % comment_id):
            self.assertIn(part, text)
        self.assertNotIn(HOST, text)
        self.assertIn("[site address removed]", text)

    def test_without_a_fingerprint_or_without_a_name_nothing_is_written(self):
        fp = self.fingerprint()
        self.refused(self.confirm(None), "no confirmation was given. A confirmation names the fingerprint")
        self.refused(self.confirm(""), "no confirmation was given")
        self.refused(self.confirm(fp, by=None), "no confirmation was given. A confirmation gives the name of the person confirming")
        self.refused(self.confirm(fp, by="   "), "no confirmation was given")
        self.assertEqual(self.posts(), [])

    def test_a_name_that_is_an_email_address_is_refused(self):
        self.refused(self.confirm(self.fingerprint(), by="someone@example.invalid"), "must be short plain text, and not an email address")

    def test_a_fingerprint_that_was_never_issued_is_refused(self):
        self.fingerprint()
        self.refused(self.confirm("0123456789ab"), "there is no preview with the fingerprint 0123456789ab")
        self.refused(self.confirm("yes"), "a fingerprint is 12 characters")
        self.assertEqual(self.posts(), [])

    def test_a_text_changed_after_the_preview_is_refused(self):
        fp = self.fingerprint()
        self.write_text(TEXT.replace("No change", "A change") + "\n")
        self.refused(self.confirm(fp), "the change is not the one that was previewed: the text is not the text the preview showed")
        self.assertEqual(self.posts(), [])
        self.assertEqual(self.mine(), [])

    def test_a_visibility_or_a_story_changed_after_the_preview_is_refused(self):
        fp = self.fingerprint()
        self.write_change({"story": "SAND-1", "text_file": "comment.txt", "visibility": {"role": "Developers"}})
        self.refused(self.confirm(fp), "the visibility asked for is not the one the preview showed")
        self.write_change({"story": "SAND-2", "text_file": "comment.txt", "visibility": "everyone"})
        self.refused(self.confirm(fp), "it names a different story")
        self.write_text(TEXT + "\n", "other.txt")
        self.write_change({"story": "SAND-1", "text_file": "other.txt", "visibility": "everyone"})
        self.refused(self.confirm(fp), "the text comes from a different file")
        self.assertEqual(self.posts(), [])

    def test_a_preview_is_good_for_fifteen_minutes_and_no_longer(self):
        fp = self.fingerprint()
        out = self.refused(self.confirm(fp, pretend_minutes_later=16), "this preview is too old. It was made 16 minutes ago and the limit is 15")
        self.assertIn("TEST CLOCK: pretending it is 16 minutes later than it is.", out)
        self.assertEqual(self.posts(), [])
        code, out, _ = self.confirm(fp, pretend_minutes_later=14)
        self.assertEqual(code, 0, out)

    def test_a_preview_dated_in_the_future_is_refused(self):
        fp = self.fingerprint()
        path = os.path.join(self.state, "previews", fp + ".json")
        with open(path, encoding="utf-8") as f:
            record = json.load(f)
        record["made_at"] = "2099-01-01 00:00:00 UTC"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(record, f)
        self.refused(self.confirm(fp), "has been altered since it was made")

    def test_a_saved_preview_that_was_altered_is_refused(self):
        fp = self.fingerprint()
        path = os.path.join(self.state, "previews", fp + ".json")
        with open(path, encoding="utf-8") as f:
            record = json.load(f)
        record["proposal"]["text"] = "Something else entirely."
        with open(path, "w", encoding="utf-8") as f:
            json.dump(record, f)
        self.refused(self.confirm(fp), "the saved preview %s has been altered since it was made" % fp)
        self.assertEqual(self.posts(), [])

    def test_a_fingerprint_is_used_once(self):
        fp = self.fingerprint()
        self.confirm(fp)
        self.refused(self.confirm(fp), "the preview %s has already been confirmed and written. A fingerprint is used once" % fp)
        self.assertEqual(len(self.posts()), 1)
        self.assertEqual(len(self.mine()), 1)

    def test_the_same_comment_put_there_by_this_identity_since_the_preview_stops_the_write(self):
        fp = self.fingerprint()
        there = self.fake.other_comment("SAND-1", TEXT, as_me=True)
        self.refused(self.confirm(fp), "this identity has put this comment on the story since the preview (comment id %s)" % there)
        self.assertEqual(self.posts(), [])
        self.assertEqual(len(self.mine()), 1)

    def test_another_persons_comment_since_the_preview_does_not_stop_the_write(self):
        fp = self.fingerprint()
        self.fake.other_comment("SAND-1", "A made-up reply from someone else.")
        code, out, _ = self.confirm(fp)
        self.assertEqual(code, 0, out)
        self.assertIn("the story's 3 comments, read just before the write", out)

    def test_a_security_level_put_on_the_story_since_the_preview_stops_the_write(self):
        fp = self.fingerprint()
        self.fake.state["issues"]["30001"]["fields"]["security"] = {"id": "10100", "name": "Staff only"}
        self.refused(self.confirm(fp), "the story's security level changed, so who can see it changed")
        self.assertEqual(self.posts(), [])

    def test_a_comment_for_a_role_is_sent_with_that_restriction_and_read_back_with_it(self):
        self.write_change({"story": "SAND-1", "text_file": "comment.txt", "visibility": {"role": "Administrators"}})
        code, out, _ = self.confirm(self.fingerprint())
        self.assertEqual(code, 0, out)
        self.assertEqual(self.mine()[0]["visibility"], {"type": "role", "value": "Administrators", "identifier": "10002"})
        self.assertIn("  its visibility is the one previewed: the role \"Administrators\": yes", out)

    def test_the_same_text_for_everyone_does_not_count_as_the_comment_for_a_role(self):
        self.fake.other_comment("SAND-1", TEXT, as_me=True)
        self.write_change({"story": "SAND-1", "text_file": "comment.txt", "visibility": {"role": "Administrators"}})
        code, out, _ = self.preview()
        self.assertIn("PREVIEW. Nothing has been written.", out)
        self.assertIn("  With the same text, by this identity: 1 (comment id", out)


class WhenTheWriteGoesWrong(Case):
    def test_a_refusal_from_jira_is_reported_as_nothing_written_and_the_preview_is_spent(self):
        fp = self.fingerprint()
        self.fake.fail_post = 400
        out = self.refused(self.confirm(fp), "Jira answered 400 to the write. Read back afterwards, the story has the 2 comments it had before and none is this one, so nothing was written")
        self.assertEqual(self.mine(), [])
        self.fake.fail_post = None
        self.refused(self.confirm(fp), "was confirmed before and a write was sent (recorded as 'sent, Jira answered 400')")
        self.assertEqual(len(self.posts()), 1)
        self.assertTrue(out)

    def test_no_answer_to_the_write_is_not_known_and_the_write_is_not_sent_again(self):
        fp = self.fingerprint()
        self.fake.fail_post = "timeout"
        code, out, _ = self.confirm(fp)
        self.assertEqual(code, 2, out)
        self.assertIn("A PERSON NEEDS TO LOOK: the write was sent and no answer came back (TimeoutError). It is NOT KNOWN whether Jira added the comment. It was not sent again.", out)
        self.assertEqual(len(self.posts()), 1)
        self.fake.fail_post = None
        self.refused(self.confirm(fp), "recorded as 'sent, answer not received'")
        self.assertEqual(len(self.posts()), 1)

    def test_a_comment_that_was_added_though_no_answer_came_is_found_by_the_next_preview(self):
        fp = self.fingerprint()
        self.fake.fail_post = "applied-timeout"
        code, _, _ = self.confirm(fp)
        self.assertEqual(code, 2)
        self.fake.fail_post = None
        code, out, _ = self.preview()
        self.assertIn("NOTHING TO ADD.", out)
        self.assertIn("comment id %s" % self.mine()[0]["id"], out)
        self.assertNotIn("Fingerprint of this preview", out)
        self.assertEqual(len(self.mine()), 1)

    def test_a_text_that_jira_changed_is_reported_for_a_person_to_look_at(self):
        fp = self.fingerprint()

        def trim(doc):
            doc["content"][0]["content"][0]["text"] = doc["content"][0]["content"][0]["text"].replace("made-up ", "")
            return doc
        self.fake.alter = trim
        code, out, _ = self.confirm(fp)
        self.assertEqual(code, 2, out)
        self.assertIn("the text read back is the text previewed, character for character (114 characters", out)
        self.assertIn("): NO", out)
        self.assertIn("A PERSON NEEDS TO LOOK: Jira accepted the write, and the comment does not read back as previewed.", out)

    def test_formatting_or_a_mention_that_jira_added_is_reported(self):
        fp = self.fingerprint()

        def mark(doc):
            doc["content"][0]["content"][0]["marks"] = [{"type": "strong"}]
            doc["content"][1]["content"].append({"type": "mention", "attrs": {"id": OTHER}})
            return doc
        self.fake.alter = mark
        code, out, _ = self.confirm(fp)
        self.assertEqual(code, 2, out)
        self.assertIn("it is plain text, with nothing added: a piece of type \"mention\", formatting on a piece of text: NO", out)

    def test_a_comment_that_comes_back_under_another_author_is_reported(self):
        fp = self.fingerprint()
        real = self.fake.post

        def post(path, params=None, body=None):
            answer = real(path, params, body)
            self.comments()[-1]["author"] = fj.person(OTHER, "Bo Sample")
            return answer
        self.fake.post = post
        code, out, _ = self.confirm(fp)
        self.assertEqual(code, 2, out)
        self.assertIn("  its author is this identity: NO", out)

    def test_a_second_copy_that_appeared_in_the_last_moment_is_reported(self):
        fp = self.fingerprint()
        self.fake.before_post = lambda fake: fake.other_comment("SAND-1", TEXT, as_me=True)
        code, out, _ = self.confirm(fp)
        self.assertEqual(code, 2, out)
        self.assertIn("counted after the write: 2. MORE THAN ONE: comment ids", out)
        self.assertIn("the story now has 2 comments with this text by this identity", out)

    def test_jira_not_reachable_before_the_write_is_a_refusal(self):
        def down(path, params=None):
            raise TimeoutError("no answer")
        self.fake.get = down
        self.refused(self.preview(), "could not reach Jira (TimeoutError)")


class TheRerun(Case):
    def test_previewing_again_after_the_write_finds_the_comment_and_issues_no_fingerprint(self):
        self.confirm(self.fingerprint())
        code, out, conn = self.preview()
        self.assertEqual(code, 0)
        self.assertIn("NOTHING TO ADD. Nothing has been written.", out)
        self.assertIn("This identity has already put this comment on the story, with this visibility: comment id %s." % self.mine()[0]["id"], out)
        self.assertIn("No fingerprint is issued, because there is nothing to confirm, and nothing was sent.", out)
        self.assertNotIn("Fingerprint of this preview", out)
        self.assertEqual(len(os.listdir(os.path.join(self.state, "previews"))), 1)
        self.assertEqual(len(self.mine()), 1)
        self.assertEqual(len(self.posts()), 1)

    def test_the_whole_workflow_run_three_times_leaves_one_comment(self):
        self.confirm(self.fingerprint())
        for _ in range(2):
            code, out, _ = self.preview()
            self.assertNotIn("Fingerprint of this preview", out)
        self.assertEqual(len(self.mine()), 1)
        self.assertEqual(len(self.comments()), 3)


class TheCheck(Case):
    def written(self):
        fp = self.fingerprint()
        self.confirm(fp)
        return fp

    def test_it_finds_the_comment_with_the_same_text_author_and_visibility(self):
        fp = self.written()
        code, out, conn = self.go("check", fingerprint=fp)
        self.assertEqual(code, 0, out)
        self.assertIn("FOUND: the comment is on the story as previewed.", out)
        self.assertIn("  its author is this identity: yes", out)
        self.assertIn("  its visibility is the one previewed: everyone who can see the story: yes", out)
        self.assertIn("  comments on the story with this text and this visibility by this identity: 1 of the 3 this identity can see", out)
        self.assertIn("Where the text came from, as the preview stated: the file comment.txt beside the change file", out)
        self.assertIn("That file today: the same name and the same sha256", out)
        self.assertEqual(out.count("    | Checked against the made-up onboarding checklist on 25 November."), 2)
        self.assertEqual(set(method for method, _ in conn.sent), {"GET"})

    def test_it_has_no_way_to_write(self):
        fp = self.written()
        _, _, conn = self.go("check", fingerprint=fp)
        with self.assertRaises(cm.Refused):
            conn.post_comment("30001", TEXT, {"kind": "everyone"})

    def test_a_comment_that_was_deleted_is_not_found(self):
        fp = self.written()
        self.fake.state["comments"]["30001"] = [c for c in self.comments() if c["author"]["accountId"] != ME]
        code, out, _ = self.go("check", fingerprint=fp)
        self.assertEqual(code, 1)
        self.assertIn("NOT AS PREVIEWED", out)
        self.assertIn("Jira returned the comment when asked for it by its identifier (status 404): NO", out)

    def test_a_comment_edited_in_jira_since_is_reported(self):
        fp = self.written()
        self.mine()[0]["body"]["content"][1]["content"][0]["text"] = "Something else."
        code, out, _ = self.go("check", fingerprint=fp)
        self.assertEqual(code, 1)
        self.assertIn("    | Something else.", out)
        self.assertIn("): NO", out)

    def test_a_comment_restricted_in_jira_since_is_reported(self):
        fp = self.written()
        self.mine()[0]["visibility"] = {"type": "role", "value": "Developers", "identifier": "10001"}
        code, out, _ = self.go("check", fingerprint=fp)
        self.assertEqual(code, 1)
        self.assertIn("  its visibility is the one previewed: the role \"Developers\": NO", out)

    def test_a_text_file_changed_since_is_said(self):
        fp = self.written()
        self.write_text("Other words.\n")
        _, out, _ = self.go("check", fingerprint=fp)
        self.assertIn("That file today: NOT the same.", out)

    def test_a_fingerprint_with_no_write_is_refused(self):
        fp = self.fingerprint()
        self.refused(self.go("check", fingerprint=fp), "there is no record of a write for the fingerprint %s" % fp)


class TheFirstRead(Case):
    """One test for each fault the reader of the first version found."""

    def test_a_read_that_fails_after_the_write_is_not_reported_as_nothing_written(self):
        fp = self.fingerprint()
        self.fake.fail_get_after_post = 503
        code, out, _ = self.confirm(fp)
        self.assertEqual(code, 2, out)
        self.assertIn("WRITTEN to Jira: one comment on story SAND-1.", out)
        self.assertIn("A PERSON NEEDS TO LOOK: the write was sent, and a step after it could not be done:", out)
        self.assertIn("The comment may be on the story.", out)
        self.assertNotIn("Nothing has been written.", out)
        self.assertEqual(len(self.mine()), 1)

    def test_the_comments_identifier_is_kept_at_once_so_that_the_check_can_be_made_later(self):
        fp = self.fingerprint()
        self.fake.fail_get_after_post = 503
        self.confirm(fp)
        with open(os.path.join(self.state, "written", fp + ".json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f)["comment_id"], self.mine()[0]["id"])
        self.fake.fail_get_after_post = None
        self.fake.requests = []
        code, out, _ = self.go("check", fingerprint=fp)
        self.assertEqual(code, 0, out)
        self.refused(self.confirm(fp), "has already been confirmed and written")

    def test_a_failure_of_the_program_after_the_write_still_shows_what_was_sent(self):
        fp = self.fingerprint()
        self.fake.fail_get_after_post = "broken"
        code, out, _ = self.confirm(fp)
        self.assertEqual(code, 2, out)
        self.assertIn("WRITTEN to Jira: one comment on story SAND-1.", out)
        self.assertIn("A PERSON NEEDS TO LOOK: the write was sent, and the program then failed (ValueError). The comment may be on the story.", out)

    def test_a_failure_of_the_program_before_any_write_is_a_refusal(self):
        def broken(path, params=None):
            raise ValueError("not an answer")
        self.fake.get = broken
        self.refused(self.preview(), "the program failed before anything was sent (ValueError)")

    def test_two_runs_confirming_one_preview_at_once_do_not_both_write(self):
        fp = self.fingerprint()
        os.makedirs(os.path.join(self.state, "sending"))
        open(os.path.join(self.state, "sending", fp), "w").close()
        self.refused(self.confirm(fp), "another run is confirming the preview %s at this moment, or one began and did not finish" % fp)
        self.assertEqual(self.posts(), [])

    def test_a_comment_for_a_role_is_counted_apart_from_the_same_text_for_everyone(self):
        self.fake.other_comment("SAND-1", TEXT, as_me=True)
        self.write_change({"story": "SAND-1", "text_file": "comment.txt", "visibility": {"role": "Administrators"}})
        fp = self.fingerprint()
        code, out, _ = self.confirm(fp)
        self.assertEqual(code, 0, out)
        self.assertIn("counted after the write: 1", out)
        code, out, _ = self.go("check", fingerprint=fp)
        self.assertEqual(code, 0, out)

    def test_a_role_is_sent_by_its_name_and_nothing_else(self):
        sent, real = [], self.fake.post

        def post(path, params=None, body=None):
            sent.append(body)
            return real(path, params, body)
        self.fake.post = post
        self.write_change({"story": "SAND-1", "text_file": "comment.txt", "visibility": {"role": "Administrators"}})
        self.confirm(self.fingerprint())
        self.assertEqual(sent[0]["visibility"], {"type": "role", "value": "Administrators"})
        self.assertEqual(set(sent[0]), {"body", "visibility"})

    def test_a_story_for_which_jira_gives_no_security_field_is_not_said_to_have_no_level(self):
        del self.fake.state["issues"]["30001"]["fields"]["security"]
        _, out, _ = self.preview()
        self.assertIn("Jira did not say whether the story has a security level.", out)
        self.assertNotIn("The story has no security level.", out)

    def test_an_unrestricted_comment_is_not_sent_to_a_service_project(self):
        self.fake.state["issues"]["30001"]["fields"]["project"]["projectTypeKey"] = "service_desk"
        self.refused(self.preview(), "this is a service project, where a comment with no restriction can be seen by customers")
        self.write_change({"story": "SAND-1", "text_file": "comment.txt", "visibility": {"role": "Administrators"}})
        code, out, _ = self.preview()
        self.assertEqual(code, 0, out)
        self.assertIn("Kind of project, as Jira gives it: service_desk.", out)

    def test_a_project_that_became_a_service_project_after_the_preview_is_refused(self):
        fp = self.fingerprint()
        self.fake.state["issues"]["30001"]["fields"]["project"]["projectTypeKey"] = "service_desk"
        self.refused(self.confirm(fp), "this is a service project")
        self.assertEqual(self.posts(), [])

    def test_another_allowlist_file_at_the_confirmation_is_refused_though_it_lists_the_project(self):
        fp = self.fingerprint()
        self.write_allowlist([("738169e667642f09", "20001"), ("738169e667642f09", "20002"), ("738169e667642f09", "20003")])
        self.refused(self.confirm(fp), "the allowlist file is not the one the preview used")
        self.assertEqual(self.posts(), [])

    def test_the_sites_address_must_be_its_name_and_nothing_more(self):
        for base in ("https://nowhere.example.invalid:8443", "https://nowhere.example.invalid/jira", "https://someone@nowhere.example.invalid"):
            os.environ.update(made_up_settings(base))
            try:
                with self.assertRaisesRegex(cm.Refused, "with no port, path or sign-in in it"):
                    cm.make_live(False)
            finally:
                for name in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN"):
                    del os.environ[name]

    def test_looking_at_the_story_in_a_browser_during_a_preview_does_not_stop_it(self):
        calls = {"n": 0}
        real = self.fake.get

        def get(path, params=None):
            calls["n"] += 1
            if calls["n"] == 5:
                self.fake.state["issues"]["30001"]["fields"]["lastViewed"] = "2026-11-25T12:30:00.000+0000"
            return real(path, params)
        self.fake.get = get
        code, out, _ = self.preview()
        self.assertEqual(code, 0, out)
        self.assertIn("Fingerprint of this preview", out)

    def test_more_shapes_of_secret_are_refused(self):
        samples = ["DB_PASS" + "WORD=" + "hunter2x", "client_sec" + "ret: " + "abcd1234", "access_to" + "ken=" + "abcd", "the pass" + "word for the wiki is " + "opensesame",
                   "pass" + "phrase: " + "correct horse", "AS" + "IA" + "Q7" * 8, "-----BEGIN PGP " + "PRIVATE KEY BLOCK-----", "xa" + "pp-" + "1-A0123456789-abc"]
        for sample in samples:
            self.write_text("Here it is: %s" % sample)
            code, out, _ = self.preview()
            self.assertEqual(code, 1, sample)
            self.assertIn("the text looks as if it holds", out)
            self.assertEqual(self.fake.requests, [])

    def test_more_characters_that_cannot_be_seen_are_refused(self):
        for character in (chr(0xe0041), chr(0x3164), chr(0xa0), chr(0x2800), chr(0x115f)):
            self.write_text("One" + character + "two.")
            self.refused(self.preview(), "a character that cannot be seen")

    def test_the_check_does_not_print_unseen_characters_that_jira_returns(self):
        fp = self.fingerprint()
        self.confirm(fp)
        self.mine()[0]["body"]["content"][1]["content"][0]["text"] = "Red " + chr(27) + "[31m text" + chr(0x202e)
        _, out, _ = self.go("check", fingerprint=fp)
        self.assertNotIn(chr(27), out)
        self.assertNotIn(chr(0x202e), out)
        self.assertIn("    | Red ?[31m text?", out)

    def test_what_jira_said_in_refusing_is_shown_as_its_own_words(self):
        fp = self.fingerprint()
        self.fake.post = lambda path, params=None, body=None: (self.fake.requests.append(("POST", path)) or (400, {}, {"errorMessages": ["You do not have permission to comment" + chr(27) + "[0m"]}))
        out = self.refused(self.confirm(fp), "Jira answered 400 to the write. Jira's own words, which are not this workflow's: \"You do not have permission to comment [0m\".")
        self.assertNotIn(chr(27), out)

    def test_the_preview_says_whose_name_the_comment_goes_under_and_that_the_storys_title_is_not_shown(self):
        _, out, _ = self.preview()
        self.assertIn("It would appear under the Jira account the API token belongs to, called this identity below. Not under the", out)
        self.assertIn("Its title is other people's text and is not", out)
        self.assertIn("Who or what put the text in that file is not known to this workflow.", out)
        self.assertIn("cannot tell whether the project is open to customers or to the", out)


class TheDocument(unittest.TestCase):
    def test_text_goes_to_a_document_and_back_unchanged(self):
        for text in ("One line.", "Two\nlines.", "Signs & marks <b> *stars* [link](x) {code} h1. | \\ \" '", "Words   with   wide   spaces."):
            self.assertEqual(cm.text_of(cm.document_of(text)), (text, []))

    def test_only_text_is_sent(self):
        doc = cm.document_of("See [this|http://example.invalid] and @someone and h1. heading")
        self.assertEqual({node["type"] for block in doc["content"] for node in block["content"]}, {"text"})
        self.assertTrue(all(set(node) == {"type", "text"} for block in doc["content"] for node in block["content"]))

    def test_what_is_not_plain_text_is_named(self):
        doc = {"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "a", "marks": [{"type": "em"}]}, {"type": "hardBreak"}, {"type": "emoji", "attrs": {}}]},
                                                       {"type": "codeBlock", "content": []}]}
        text, odd = cm.text_of(doc)
        self.assertEqual(text, "a\n")
        self.assertEqual(odd, ["formatting on a piece of text", "a piece of type \"emoji\"", "a block of type \"codeBlock\""])
        self.assertEqual(cm.text_of("a string")[0], None)


class TheProgram(Case):
    def test_it_imports_nothing_that_starts_a_program_and_reads_no_clock_but_for_the_age_of_a_preview(self):
        with open(os.path.join(SKILL, "comment.py"), encoding="utf-8") as f:
            source = f.read()
        self.assertEqual(sorted(set(re.findall(r"^import ([\w.]+)$", source, re.M))),
                         ["argparse", "base64", "datetime", "hashlib", "http.client", "json", "os", "re", "sys", "urllib.error", "urllib.parse", "urllib.request"])
        self.assertNotRegex(source, r"^from \w+ import|subprocess|os\.system|os\.popen|__import__|eval\(|exec\(")
        self.assertEqual(source.count("datetime.datetime.now("), 1)

    def test_the_only_write_it_can_send_is_one_comment_on_one_story(self):
        with open(os.path.join(SKILL, "comment.py"), encoding="utf-8") as f:
            source = f.read()
        self.assertEqual(re.findall(r'send\("(\w+)"', source), ["GET", "POST"])
        self.assertNotRegex(source, r'"(PUT|DELETE|PATCH)"')
        os.environ.update(made_up_settings("https://nowhere.example.invalid"))
        try:
            conn, _ = cm.make_live(True)
            for path in ("/rest/api/3/issue/30001", "/rest/api/3/issue/SAND-1/comment", "/rest/api/3/issue/30001/comment/50001", "/rest/api/3/project/20001/role"):
                with self.assertRaises(cm.Refused):
                    conn._post(path, None, {})
            self.assertIsNone(cm.make_live(False)[0]._post)
        finally:
            for name in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN"):
                del os.environ[name]

    def test_a_live_run_without_its_three_settings_or_without_https_is_refused(self):
        for name in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN"):
            os.environ.pop(name, None)
        with self.assertRaises(cm.Refused):
            cm.make_live(False)
        os.environ.update(made_up_settings("http://nowhere.example.invalid"))
        try:
            with self.assertRaisesRegex(cm.Refused, "must start with https://"):
                cm.make_live(False)
        finally:
            for name in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN"):
                del os.environ[name]

    def test_from_the_command_line_only_the_confirmation_is_given_a_way_to_write(self):
        given, real = [], cm.Connection

        def watched(get, post, host):
            given.append(post is not None)
            return real(get, post, host)
        common = ["--source", "fake", "--change", os.path.join(self.root, "change.json"), "--state", self.state]
        saved, cm.Connection = sys.stdout, watched
        sys.stdout = open(os.devnull, "w")
        try:
            cm.main(["preview"] + common + ["--allowlist", self.allowlist])
            fp = os.listdir(os.path.join(self.state, "previews"))[0][:12]
            cm.main(["confirm"] + common + ["--allowlist", self.allowlist, "--fingerprint", fp, "--confirmed-by", "the participant"])
            cm.main(["check"] + common + ["--fingerprint", fp])
        finally:
            sys.stdout.close()
            sys.stdout, cm.Connection = saved, real
        self.assertEqual(given, [False, True, False])

    def test_a_saved_log_has_the_sites_address_taken_out(self):
        log = os.path.join(self.root, "logs", "preview.txt")
        argv = ["preview", "--source", "fake", "--change", os.path.join(self.root, "change.json"), "--allowlist", self.allowlist, "--state", self.state, "--log", log]
        saved = sys.stdout
        sys.stdout = open(os.devnull, "w")
        try:
            self.assertEqual(cm.main(argv), 0)
        finally:
            sys.stdout.close()
            sys.stdout = saved
        with open(log, encoding="utf-8") as f:
            text = f.read()
        self.assertNotIn(HOST, text)
        self.assertIn("Jira site:  [site address removed]  (site fingerprint 738169e667642f09)", text)


if __name__ == "__main__":
    unittest.main()
