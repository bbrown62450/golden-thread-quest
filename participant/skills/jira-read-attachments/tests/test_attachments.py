"""Tests for attachments.py, against the made-up Jira. No network. Every attachment, file and person here is made up."""
import contextlib
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import urllib.parse
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, SKILL)
import attachments    # noqa: E402
import fake_jira      # noqa: E402

MADE_UP = "-".join(["made", "up", "value", "used", "only", "in", "tests"])      # stands where an API token would be
JPG = b"\xff\xd8\xff\xe0" + b"made-up picture bytes" * 3
# The first line of a private key, with nothing after it. Built from pieces, so that this file does not itself hold one.
KEY_MARK = b"-----BEGIN RSA " + b"PRIVATE " + b"KEY-----"


class Case(unittest.TestCase):
    def setUp(self):
        self.folder = os.path.realpath(tempfile.mkdtemp(prefix="gtq-attachments-test-"))
        self.out, self.downloads, self.state = (os.path.join(self.folder, name) for name in ("out", "downloads", "jira"))
        for path in (self.out, self.downloads, self.state):
            os.makedirs(path)
        self.fake_path = os.path.join(self.state, "fake-jira.json")
        fake_jira.FakeJira(fake_jira.fresh()).save(self.fake_path)

    def tearDown(self):
        shutil.rmtree(self.folder, ignore_errors=True)

    # ---------------------------------------------------------- helpers

    def main(self, *argv):
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed), contextlib.redirect_stderr(printed):
            try:
                code = attachments.main(list(argv))
            except SystemExit as stop:
                code = stop.code
        return code, printed.getvalue()

    def sync(self, extra=(), name="index"):
        return self.main("sync", "--source", "fake", "--issue", "DEMO-7", "--out-dir", self.out, "--name", name, "--state", self.state, *extra)

    def download(self, number, extra=(), downloads=None):
        return self.main("download", "--source", "fake", "--issue", "DEMO-7", "--id", number, "--downloads", downloads or self.downloads, "--state", self.state, *extra)

    @contextlib.contextmanager
    def jira(self):
        fake = fake_jira.FakeJira.open(self.fake_path)
        yield fake
        fake.save(self.fake_path)

    def asked(self):
        with open(self.fake_path, encoding="utf-8") as f:
            return json.load(f)["asked"]

    def index(self, name="index"):
        with open(os.path.join(self.out, name + ".json"), encoding="utf-8") as f:
            return json.load(f)

    def page(self, name="index"):
        with open(os.path.join(self.out, name + ".md"), encoding="utf-8") as f:
            return f.read()

    def files(self, folder=None):
        return sorted(os.listdir(folder or self.downloads))

    def log(self):
        path = os.path.join(self.downloads, attachments.LOG_NAME)
        if not os.path.exists(path):
            return []
        with open(path, encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    def add(self, name, kind="text/plain", size=None, content=b"made-up text\n", number="41900", author="acct-ana"):
        """Attaches one more made-up file, whose bytes this test supplies."""
        with self.jira() as jira:
            jira.data["attachments"].append({"id": number, "filename": name, "mimeType": kind, "size": len(content) if size is None else size,
                                             "author": author, "created": "2026-11-08T09:00:00.000+0000"})
        real = fake_jira.content_of
        return mock.patch.object(fake_jira, "content_of", lambda ident: content if ident == number else real(ident))


class ASyncRecordsEveryAttachment(Case):
    def test_the_index_has_each_attachments_identifier_name_type_size_author_and_date(self):
        code, text = self.sync()
        self.assertEqual(code, 0, text)
        made = {a["id"]: a for a in fake_jira.fresh()["attachments"]}
        got = {a["id"]: a for a in self.index()["attachments"]}
        self.assertEqual(sorted(got), sorted(made))
        self.assertEqual(len(got), 16)
        for number, a in made.items():
            self.assertEqual((got[number]["name"], got[number]["stated_type"], got[number]["stated_size"]), (a["filename"], a["mimeType"], a["size"]))
            self.assertEqual(got[number]["attached_by"], "me" if a["author"] == "acct-ben" else "someone else")
            self.assertRegex(got[number]["attached"], r"^2026-11-0[2-7]T[0-9:]{8}Z$")
        self.assertEqual(got["41002"]["attached"], "2026-11-03T13:40:00Z", "Jira's time, with its own offset, is turned into UTC")

    def test_the_page_has_a_row_for_each_with_all_six(self):
        self.sync()
        rows = [line for line in self.page().split("\n") if re.match(r"\| 4[0-9]{4} \|", line)]
        self.assertEqual(len(rows), 16)
        self.assertIn("| 41001 | `release-notes.txt` | `text/plain` | 57 bytes | someone else | 2026-11-02T09:15:00Z | could be asked for", self.page())
        self.assertIn("| 41002 | `export.csv` | `text/csv` | 45 bytes | me | 2026-11-03T13:40:00Z |", self.page())
        self.assertIn("**No file was downloaded to make this.**", self.page())

    def test_no_person_is_kept_or_printed(self):
        _, text = self.sync()
        everything = json.dumps(self.index()) + self.page() + text
        for private in ("acct-", "Made-up Person", "example.invalid", "displayName", "accountId"):
            self.assertNotIn(private, everything)

    def test_an_author_jira_does_not_name_is_unknown(self):
        with self.jira() as jira:
            jira.data["attachments"][0]["author"] = None
        _, text = self.sync()
        self.assertEqual(self.index()["attachments"][0]["attached_by"], "unknown")
        self.assertIn("unknown: 1", text)

    def test_names_are_in_the_index_and_are_not_printed(self):
        _, text = self.sync()
        for name in ("release-notes", "authorized_keys", "backup.zip", "Quarterly"):
            self.assertNotIn(name, text)
        self.assertIn("../../.ssh/authorized_keys.txt", json.dumps(self.index()))

    def test_what_the_first_three_checks_would_say_is_in_the_index(self):
        self.sync()
        verdict = {a["id"]: a["if_asked_for"] for a in self.index()["attachments"]}
        self.assertTrue(verdict["41001"].startswith("could be asked for"))
        self.assertTrue(verdict["41004"].startswith("would be refused by the type"))
        self.assertTrue(verdict["41005"].startswith("would be refused by the size"))
        self.assertTrue(verdict["41006"].startswith("would be refused by the name"))
        self.assertTrue(verdict["41010"].startswith("would be refused by the type"))
        self.assertTrue(verdict["41009"].startswith("could be asked for"), "what is wrong with this one is inside the file, which a sync never sees")

    def test_a_story_with_no_attachments_is_an_answer(self):
        with self.jira() as jira:
            jira.data["attachments"] = []
        code, text = self.sync()
        self.assertEqual(code, 0, text)
        self.assertIn("ATTACHMENTS LISTED BY JIRA: 0.", text)
        self.assertIn("The story has no attachments.", self.page())

    def test_a_second_sync_of_unchanged_data_writes_nothing(self):
        self.sync()
        def state():
            out = {}
            for n in self.files(self.out):
                with open(os.path.join(self.out, n), "rb") as f:
                    out[n] = (f.read(), os.stat(os.path.join(self.out, n)).st_mtime_ns)
            return out
        before = state()
        code, text = self.sync()
        self.assertEqual(state(), before)
        self.assertIn("RESULT: INDEX UNCHANGED", text)

    def test_a_name_cannot_break_the_page_and_unseen_characters_are_replaced(self):
        with self.add("x`|y\n## Attachments | z\u202etxt.exe.txt"):
            self.sync()
        rows = [line for line in self.page().split("\n") if line.startswith("| 41900 |")]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].count("|"), 8)
        self.assertEqual(sum(1 for line in self.page().split("\n") if line.startswith("#")), 1)
        added = [a for a in self.index()["attachments"] if a["id"] == "41900"][0]
        self.assertEqual(added["name"], "x`|y?## Attachments | z?txt.exe.txt")
        self.assertTrue(added["name_cut_or_changed"])
        self.assertIn("(changed or cut here)", rows[0])


class ASyncDownloadsNothing(Case):
    def test_no_request_for_a_files_contents_or_for_one_attachment_is_made(self):
        with mock.patch.object(fake_jira.FakeJira, "content", side_effect=AssertionError("a file was asked for")):
            code, text = self.sync()
        self.assertEqual(code, 0, text)
        self.assertEqual(self.asked(), {"content": 0, "details": 0, "issue": 1, "myself": 1})
        self.assertIn("Requests that ask for a file's contents: 0.", text)
        self.assertIn("NO FILE WAS DOWNLOADED.", text)
        self.assertNotIn("/content/", text)

    def test_the_only_files_written_are_the_index_and_its_page(self):
        self.sync()
        self.assertEqual(self.files(self.out), ["index.json", "index.md"])
        self.assertEqual(self.files(), [])
        self.assertEqual(sorted(os.listdir(self.folder)), ["downloads", "jira", "out"])

    def test_the_sync_command_has_no_code_that_asks_for_contents(self):
        with open(os.path.join(SKILL, "attachments.py"), encoding="utf-8") as f:
            source = f.read()
        body = source[source.index("def cmd_sync("):source.index("def say_requests(")]
        self.assertNotIn(".content(", body)
        self.assertNotIn("/attachment/", body)

    def test_what_cannot_be_read_is_refused_and_nothing_is_written(self):
        spoilers = {
            "no list of attachments": lambda body: body["fields"].pop("attachment"),
            "a list that is a word": lambda body: body["fields"].update(attachment="none"),
            "an attachment with no identifier": lambda body: body["fields"]["attachment"][0].pop("id"),
            "an identifier that is not a number": lambda body: body["fields"]["attachment"][0].update(id="../x"),
            "an attachment with no name": lambda body: body["fields"]["attachment"][0].pop("filename"),
            "a date that cannot be read": lambda body: body["fields"]["attachment"][0].update(created="last week"),
            "the same attachment twice": lambda body: body["fields"]["attachment"].append(body["fields"]["attachment"][0]),
            "another story's key": lambda body: body.update(key="OTHER-1"),
        }
        real = fake_jira.FakeJira.get
        for what, spoil in spoilers.items():
            def get(fake, path, params=None, spoil=spoil):
                status, headers, body = real(fake, path, params)
                if "/issue/" in path:
                    spoil(body)
                return status, headers, body
            with self.subTest(what), mock.patch.object(fake_jira.FakeJira, "get", get):
                code, text = self.sync()
                self.assertEqual(code, 1, text)
                self.assertEqual(self.files(self.out), [])
        for status in (401, 404, 500):
            with self.subTest(status), mock.patch.object(fake_jira.FakeJira, "get", lambda fake, path, params=None, status=status: (status, {}, {})):
                self.assertEqual(self.sync()[0], 1)
        with mock.patch.object(fake_jira.FakeJira, "get", side_effect=OSError("made up")):
            code, text = self.sync()
        self.assertEqual(code, 1)
        self.assertIn("could not be reached", text)

    def test_a_size_jira_does_not_state_is_not_stated_and_not_zero(self):
        with self.jira() as jira:
            jira.data["attachments"][0]["size"] = None
        self.sync()
        self.assertIsNone(self.index()["attachments"][0]["stated_size"])
        self.assertIn("| 41001 | `release-notes.txt` | `text/plain` | not stated |", self.page())
        self.assertTrue(self.index()["attachments"][0]["if_asked_for"].startswith("would be refused by the size"))


class ADownloadNeedsOneAttachmentNamed(Case):
    def test_without_an_identifier_there_is_no_download(self):
        code, text = self.main("download", "--source", "fake", "--issue", "DEMO-7", "--downloads", self.downloads, "--state", self.state)
        self.assertEqual(code, 2)
        self.assertIn("--id", text)
        self.assertEqual(self.files(), [])
        self.assertEqual(self.asked()["content"], 0)

    def test_there_is_no_way_to_ask_for_more_than_one(self):
        for many in ("all", "*", "41001,41002", "41001 41002", "4100?", "", "041001", "41001/../41002", "-1"):
            with self.subTest(many):
                code, text = self.download(many)
                self.assertNotEqual(code, 0, text)
                self.assertEqual([n for n in self.files() if n != attachments.LOG_NAME], [])
        self.assertEqual(self.asked()["content"], 0)

    def test_an_identifier_that_is_not_one_of_the_storys_is_refused_and_logged(self):
        code, text = self.download("99999")
        self.assertEqual(code, 1, text)
        self.assertIn("has no attachment with the identifier 99999", text)
        self.assertEqual(self.files(), [attachments.LOG_NAME])
        self.assertEqual((self.log()[0]["attachment"], self.log()[0]["outcome"]), ("99999", "refused"))
        self.assertEqual(self.asked()["content"], 0)

    def test_one_command_fetches_at_most_one_file(self):
        self.download("41001")
        self.assertEqual(self.asked()["content"], 1)
        self.assertEqual(len([n for n in self.files() if n != attachments.LOG_NAME]), 1)


class AnAllowedDownload(Case):
    def test_the_file_is_saved_with_the_bytes_jira_sent_under_a_name_the_tool_built(self):
        code, text = self.download("41001")
        self.assertEqual(code, 0, text)
        self.assertEqual(self.files(), ["41001-release-notes.txt", attachments.LOG_NAME])
        with open(os.path.join(self.downloads, "41001-release-notes.txt"), "rb") as f:
            self.assertEqual(f.read(), fake_jira.content_of("41001"))
        self.assertIn("SAVED as 41001-release-notes.txt", text)
        self.assertIn("RESULT: SAVED. One file, after six checks, and its line is in the log.", text)
        for step in ("1. THE NAME", "2. THE TYPE", "3. THE SIZE", "4. THE BYTES", "5. HOW THE BYTES BEGIN", "6. THE SCAN"):
            self.assertIn(step, text)
        self.assertEqual(text.count("passed:"), 6, "each of the six checks says it passed")

    def test_each_honest_kind_can_be_saved(self):
        for number, saved in (("41002", "41002-export.csv"), ("41003", "41003-diagram.png"), ("41012", "41012-quarterly-report-final-v2.pdf")):
            code, text = self.download(number)
            self.assertEqual(code, 0, text)
            self.assertIn(saved, self.files())
        with self.add("photo of a made-up thing.JPEG", "image/jpeg", content=JPG), self.add("config.json", "application/json", content=b'{"made": "up"}\n', number="41901"), \
                self.add("NOTES.MD", "text/markdown", content=b"# made up\n", number="41902"):
            self.assertEqual(self.download("41900")[0], 0)
            self.assertEqual(self.download("41901")[0], 0)
            self.assertEqual(self.download("41902")[0], 0)
        self.assertIn("41900-photo-of-a-made-up-thing.jpg", self.files())
        self.assertIn("41902-notes.md", self.files())

    def test_the_saved_file_is_private_and_not_a_program_and_no_temporary_file_is_left(self):
        self.download("41001")
        mode = os.stat(os.path.join(self.downloads, "41001-release-notes.txt")).st_mode & 0o777
        self.assertEqual(mode, 0o600)
        self.assertEqual([n for n in self.files() if n.startswith(".")], [])

    def test_the_download_is_in_the_log_with_identifier_time_name_size_and_checksum(self):
        _, text = self.download("41001")
        entry = self.log()[0]
        self.assertEqual((entry["attachment"], entry["story"], entry["outcome"], entry["saved_as"], entry["bytes"]), ("41001", "DEMO-7", "saved", "41001-release-notes.txt", 57))
        self.assertEqual(entry["sha256"], hashlib.sha256(fake_jira.content_of("41001")).hexdigest())
        self.assertRegex(entry["time"], r"^20[0-9]{2}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")
        self.assertIn(entry["sha256"], text)
        self.assertIn(json.dumps(entry, sort_keys=True), text)

    def test_a_file_already_saved_is_not_written_over(self):
        self.download("41001")
        path = os.path.join(self.downloads, "41001-release-notes.txt")
        with open(path, "wb") as f:
            f.write(b"changed since it was saved")
        code, text = self.download("41001")
        self.assertEqual(code, 2, text)
        self.assertIn("It is not written over", text)
        with open(path, "rb") as f:
            self.assertEqual(f.read(), b"changed since it was saved")
        self.assertEqual([e["outcome"] for e in self.log()], ["saved", "refused"])

    def test_a_save_that_fails_at_the_last_moment_is_logged_and_leaves_nothing(self):
        with mock.patch.object(attachments.os, "link", side_effect=OSError("made up")):
            code, text = self.download("41001")
        self.assertEqual(code, 1, text)
        self.assertIn("the file could not be written", text)
        self.assertEqual(self.files(), [attachments.LOG_NAME], "a temporary file was left, or there is no log")
        self.assertEqual((self.log()[0]["outcome"], self.log()[0]["saved_as"]), ("refused", None))

    def test_the_tool_never_opens_or_runs_what_it_saved(self):
        opened = []
        real_open = open

        def watching(path, *a, **k):
            if str(path).endswith("41001-release-notes.txt"):
                opened.append(path)
            return real_open(path, *a, **k)
        with mock.patch("builtins.open", watching), mock.patch.object(attachments.subprocess, "run", side_effect=lambda *a, **k: opened.append(("run", a)) or subprocess.CompletedProcess(a, 0)), \
                mock.patch.object(os, "system", side_effect=AssertionError("ran something")):
            code, _ = self.download("41001")
        self.assertEqual(code, 0)
        self.assertEqual(opened, [], "the saved file is written through a temporary name and is not opened afterwards")


class ARefusedDownload(Case):
    CASES = [  # attachment, the check that refuses it, words in the reason, whether the file's contents may have been asked for
        ("41004", "the type", "not on the allowed list", False),
        ("41005", "the size", "Jira states a size of 9.0 MB, and the limit is 5.0 MB", False),
        ("41006", "the name", "the name has a path in it", False),
        ("41010", "the type", "not on the allowed list", False),
        ("41007", "what the bytes are", "begins the way an archive", True),
        ("41008", "the size", "more arrived than the 200 bytes Jira stated", True),
        ("41009", "the scan", "the PDF has", True),
        ("41011", "the scan", "the test string that antivirus makers publish", True),
        ("41013", "what the bytes are", "does not begin the way a .jpg file begins. It begins the way a PNG picture begins", True),
        ("41014", "what the bytes are", "is named .json and is not JSON", True),
        ("41015", "the size", "40 bytes arrived and Jira stated 500", True),
    ]

    def test_each_is_refused_with_the_check_and_the_reason_and_nothing_is_saved(self):
        for number, check, words, _ in self.CASES:
            with self.subTest(number):
                code, text = self.download(number)
                self.assertEqual(code, 2, text)
                self.assertIn("REFUSED by %s: " % check, text)
                self.assertIn(words, text)
                self.assertIn("RESULT: NOT SAVED.", text)
                self.assertNotIn("SAVED as", text)
                self.assertEqual(self.files(), [attachments.LOG_NAME], "something besides the log is in the downloads folder")
                entry = self.log()[-1]
                self.assertEqual((entry["attachment"], entry["outcome"], entry["check"], entry["saved_as"], entry["sha256"]), (number, "refused", check, None, None))
                self.assertIn(words.split(".")[0][:30], entry["reason"])

    def test_what_jira_says_is_checked_before_the_file_is_asked_for(self):
        for number, _, _, fetched in self.CASES:
            fake_jira.FakeJira(fake_jira.fresh()).save(self.fake_path)
            self.download(number)
            self.assertEqual(self.asked()["content"], 1 if fetched else 0, "attachment %s" % number)

    def test_a_file_that_runs_past_the_limit_is_stopped_and_not_read_to_its_end(self):
        taken = []
        real = fake_jira.FakeJira.content

        def content(fake, ident):
            status, pieces = real(fake, ident)

            def counting():
                for piece in pieces:
                    taken.append(len(piece))
                    yield piece
            return status, counting()
        with mock.patch.object(fake_jira.FakeJira, "content", content):
            code, _ = self.download("41008")
        self.assertEqual(code, 2)
        self.assertEqual(len(taken), 1, "it stopped at the first piece that ran past the 200 bytes Jira stated")
        self.assertLess(sum(taken), len(fake_jira.content_of("41008")))

    def test_a_file_exactly_at_the_limit_passes_and_one_byte_more_does_not(self):
        with self.add("big.txt", content=b"a" * attachments.SIZE_LIMIT):
            self.assertEqual(self.download("41900")[0], 0)
        with self.add("big2.txt", content=b"a" * (attachments.SIZE_LIMIT + 1), number="41901"):
            code, text = self.download("41901")
        self.assertEqual(code, 2)
        self.assertIn("REFUSED by the size", text)
        self.assertEqual(self.asked()["content"], 1, "one byte over, by Jira's own statement: refused without asking for it")
        with self.add("big3.txt", size=attachments.SIZE_LIMIT, content=b"a" * (attachments.SIZE_LIMIT + 70000), number="41902"):
            code, text = self.download("41902")
        self.assertEqual(code, 2)
        self.assertIn("more arrived than the limit of 5.0 MB", text)

    def test_the_type_jira_states_must_go_with_the_extension(self):
        for name, kind in (("a.txt", "application/zip"), ("a.png", "text/plain"), ("a.pdf", "image/png"), ("a.txt", ""), ("a.txt", None), ("a.csv", "application/vnd.ms-excel")):
            with self.subTest(name + " " + str(kind)), self.add(name, kind):
                code, text = self.download("41900")
                self.assertEqual(code, 2, text)
                self.assertIn("REFUSED by the type", text)
                self.assertEqual(self.asked()["content"], 0)
            fake_jira.FakeJira(fake_jira.fresh()).save(self.fake_path)

    def test_types_that_are_never_allowed(self):
        for name in ("a.zip", "a.exe", "a.sh", "a.js", "a.html", "a.svg", "a.docx", "a.xlsm", "a.dmg", "a.jar", "a.tar.gz", "a.py", "a.bat", "a.lnk", "a.TXT.EXE", "noextension", ".txt", "a."):
            with self.assertRaises(attachments.Check, msg=name) as caught:
                attachments.check_claims(name, "text/plain", 10)
            self.assertIn(caught.exception.which, ("the type", "the name"), name)

    def test_a_size_that_is_not_a_whole_number_of_bytes(self):
        for size in (None, "10", 10.5, True, -1):
            with self.assertRaises(attachments.Check) as caught:
                attachments.check_claims("a.txt", "text/plain", size)
            self.assertEqual(caught.exception.which, "the size")

    def test_jira_not_sending_the_file_or_not_describing_it(self):
        with mock.patch.object(fake_jira.FakeJira, "content", lambda fake, ident: (500, iter(()))):
            code, text = self.download("41001")
        self.assertEqual(code, 1, text)
        self.assertEqual(self.files(), [attachments.LOG_NAME])
        real = fake_jira.FakeJira.get
        with mock.patch.object(fake_jira.FakeJira, "get", lambda fake, path, params=None: (404, {}, {}) if "/attachment/" in path else real(fake, path, params)):
            code, text = self.download("41001")
        self.assertEqual(code, 1, text)
        self.assertEqual(self.asked()["content"], 0)
        with mock.patch.object(fake_jira.FakeJira, "get", lambda fake, path, params=None: (200, {}, dict(real(fake, path, params)[2], id="41002")) if "/attachment/" in path else real(fake, path, params)):
            code, text = self.download("41001")
        self.assertEqual(code, 1, text)


class TheNameIsNeverUsedAsAPath(Case):
    HOSTILE = ["../../.ssh/authorized_keys.txt", "/etc/passwd.txt", "..\\..\\windows\\win.txt", "a/b.txt", "a\\b.txt", "x..txt", "..txt", "x\x00.txt", "x\n.txt", "x\u202etxt.exe.txt",
               "x\u200b.txt", " x.txt", "x.txt ", "x.txt.", "", "   ", "~/x.txt/", "C:\\x.txt", "file:///x.txt"]

    def test_hostile_names_are_refused_by_the_name_check(self):
        for name in self.HOSTILE:
            with self.assertRaises(attachments.Check, msg=repr(name)) as caught:
                attachments.check_claims(name, "text/plain", 10)
            self.assertIn(caught.exception.which, ("the name", "the type"), repr(name))

    def test_a_hostile_name_from_jira_writes_nothing_anywhere(self):
        for n, name in enumerate(self.HOSTILE[:8]):
            with self.subTest(repr(name)), self.add(name, number=str(41900 + n)):
                code, text = self.download(str(41900 + n))
                self.assertEqual(code, 2, text)
        self.assertEqual(self.files(), [attachments.LOG_NAME])
        self.assertEqual(sorted(os.listdir(self.folder)), ["downloads", "jira", "out"])
        self.assertFalse(os.path.exists(os.path.join(os.path.dirname(self.folder), ".ssh")))

    def test_whatever_the_name_the_saved_name_is_one_plain_name_the_tool_built(self):
        awkward = ["Quarterly Report (final) v2!.PDF", "CON.txt", "résumé façade.txt", "名前.txt", "a" * 300 + ".txt", "---.txt", "....txt", "UPPER lower.TXT", "a.b.c.d.txt", "-rf.txt", "$(rm -rf).txt",
                   "`whoami`.txt", "a;b&c|d.txt", "%2e%2e%2f.txt", "x.pdf.txt", "nul.txt", ".hidden.txt"] + self.HOSTILE
        for name in awkward:
            for extension in ("txt", "pdf", "jpeg"):
                saved = attachments.saved_name("41001", name, extension)
                self.assertRegex(saved, r"^41001-[a-z0-9]+(-[a-z0-9]+)*\.(txt|pdf|jpg)$", repr(name))
                self.assertEqual(os.path.basename(saved), saved)
                self.assertLessEqual(len(saved), 60)
                self.assertEqual(os.path.dirname(os.path.join(self.downloads, saved)), self.downloads)
        self.assertEqual(attachments.saved_name("7", "résumé façade.txt", "txt"), "7-r-sum-fa-ade.txt")
        self.assertEqual(attachments.saved_name("7", "名前.txt", "txt"), "7-attachment.txt")

    def test_two_attachments_with_the_same_name_do_not_share_a_file(self):
        with self.add("release-notes.txt", content=b"another made-up file\n"):
            self.download("41001")
            self.download("41900")
        self.assertEqual([n for n in self.files() if n.endswith(".txt")], ["41001-release-notes.txt", "41900-release-notes.txt"])

    def test_the_download_code_never_joins_jiras_name_to_a_folder(self):
        with open(os.path.join(SKILL, "attachments.py"), encoding="utf-8") as f:
            source = f.read()
        body = source[source.index("def cmd_download("):source.index("def main(")]
        self.assertEqual(body.count("os.path.join(downloads, saved_name("), 1)
        self.assertNotIn("os.path.join(downloads, name", body)
        self.assertNotIn("open(name", body)


class OutsideSourceControl(Case):
    def repo(self):
        root = os.path.join(self.folder, "repo")
        os.makedirs(os.path.join(root, "tracked"))
        os.makedirs(os.path.join(root, "ignored-data"))
        subprocess.run(["git", "init", "-q", root], check=True, capture_output=True)
        with open(os.path.join(root, ".gitignore"), "w", encoding="utf-8") as f:
            f.write("/ignored-data/\n")
        return root

    def test_a_folder_git_would_commit_from_is_refused_before_jira_is_asked(self):
        root = self.repo()
        for inside in (os.path.join(root, "tracked"), root):
            code, text = self.download("41001", downloads=inside)
            self.assertEqual(code, 1, text)
            self.assertTrue("Git does not ignore that folder as a folder" in text or "is the top of a Git repository" in text, text)
            self.assertEqual([n for n in os.listdir(inside) if n not in (".git", ".gitignore", "tracked", "ignored-data")], [])
        self.assertEqual(self.asked(), {"content": 0, "details": 0, "issue": 0, "myself": 0})

    def test_a_folder_git_ignores_and_a_folder_in_no_repository_are_allowed_and_said_to_be_that(self):
        root = self.repo()
        code, text = self.download("41001", downloads=os.path.join(root, "ignored-data"))
        self.assertEqual(code, 0, text)
        self.assertIn("Git says it ignores that folder whole", text)
        code, text = self.download("41001")
        self.assertEqual(code, 0, text)
        self.assertIn("no repository was found in it or in any folder above it", text)

    def test_when_git_cannot_be_asked_a_folder_inside_a_repository_is_refused(self):
        root = self.repo()
        with mock.patch.object(attachments.subprocess, "run", side_effect=OSError("no git")):
            code, text = self.download("41001", downloads=os.path.join(root, "ignored-data"))
        self.assertEqual(code, 1, text)
        self.assertIn("could not be asked", text)

    def test_a_downloads_folder_that_is_not_there_is_not_made(self):
        missing = os.path.join(self.folder, "missing")
        self.assertEqual(self.download("41001", downloads=missing)[0], 1)
        self.assertFalse(os.path.exists(missing))


class TheChecksOnTheBytes(Case):
    def test_text_must_be_text(self):
        for what, data in (("a zero byte", b"abc\x00def"), ("a program's beginning", b"MZ\x90made up"), ("a linux program's", b"\x7fELFmade up"), ("an archive's", b"PK\x03\x04made up"),
                           ("a PDF's", b"%PDF-1.4 made up"), ("gzip's", b"\x1f\x8bmade up"), ("not UTF-8", b"\xff\xfe\x00m\x00a".replace(b"\x00", b"\x81"))):
            with self.subTest(what), self.assertRaises(attachments.Check):
                attachments.check_bytes("txt", data)
        attachments.check_bytes("txt", "made-up text, with an é and a 名\n".encode("utf-8"))
        attachments.check_bytes("csv", b"a,b\n1,2\n")
        attachments.check_bytes("json", b'{"a": [1, 2]}')
        attachments.check_bytes("jpg", JPG)
        with self.assertRaises(attachments.Check):
            attachments.check_bytes("png", JPG)
        with self.assertRaises(attachments.Check):
            attachments.check_bytes("pdf", b"not a pdf")

    def test_the_scan_finds_each_of_its_patterns(self):
        pdf = fake_jira.PDF
        found = [("pdf", pdf.replace(b"/Pages 2 0 R", b"/Pages 2 0 R /OpenAction 3 0 R"), "set to run when it is opened"), ("pdf", pdf + b"<< /S /JavaScript >>", "a script"),
                 ("pdf", pdf + b"<< /JS (x) >>", "a script"), ("pdf", pdf + b"<< /S /Launch /F (x) >>", "start a program"), ("pdf", pdf + b"<< /Type /EmbeddedFile >>", "another file inside"),
                 ("txt", b"notes\n" + KEY_MARK + b"\nmade up\n", "a private key"), ("txt", b"#!/bin/sh\necho made up\n", "starts a script"),
                 ("md", b"hello <script>alert(1)</script>", "a script tag"), ("md", b"hello <  SCRIPT src=x>", "a script tag"),
                 ("csv", b"name,value\nx,=cmd|' /C calc'!A0\n", "begins the way a formula begins"), ("csv", b"name,value\nx,@SUM(1)\n", "begins the way a formula begins"), ("csv", b'name,value\nx," +cmd"\n', "begins the way a formula begins"),
                 ("csv", b"name,value\nx,-cmd\n", "begins the way a formula begins"), ("txt", b"text then PK\x03\x04 later", "an archive inside"),
                 ("png", fake_jira.PNG + b"MZ.. This program cannot be run in DOS mode", "a program inside"), ("txt", b"x" + fake_jira.TEST_STRING, "test string")]
        for extension, data, words in found:
            with self.subTest(words + " in ." + extension), self.assertRaises(attachments.Check) as caught:
                attachments.scan(extension, data)
            self.assertEqual(caught.exception.which, "the scan")
            self.assertIn(words, str(caught.exception))

    def test_the_scan_passes_what_is_ordinary(self):
        attachments.scan("pdf", fake_jira.PDF + b"<< /JSON /AAA /Launcher >>")
        attachments.scan("csv", b"name,value\nx,-5\ny,+3.2\nz,a=b\nw,-12%\nv,\"1,5\"\n")
        attachments.scan("txt", b"a line about scripts: use #! at the top\nand BEGIN PRIVATE things\n")
        attachments.scan("json", b'{"script": "no tag here"}')
        attachments.scan("png", fake_jira.PNG)

    def test_the_output_says_the_scan_is_not_antivirus(self):
        _, text = self.download("41001")
        self.assertIn("Not antivirus", text)
        self.assertIn("That does not make the file safe", text)
        _, limits = self.main("limits")
        self.assertIn("NOT antivirus", limits)


class TheLimitsCommand(Case):
    def test_it_prints_the_size_and_every_allowed_type_from_the_lists_the_checks_use(self):
        code, text = self.main("limits")
        self.assertEqual(code, 0)
        self.assertIn("at most 5.0 MB", text)
        for extension, (types, _) in attachments.ALLOWED.items():
            self.assertIn("  .%-5s" % extension, text)
            for kind in types:
                self.assertIn(kind, text)
        self.assertEqual(sorted(attachments.ALLOWED), ["csv", "jpeg", "jpg", "json", "log", "md", "pdf", "png", "txt"])
        self.assertEqual(attachments.SIZE_LIMIT, 5 * 1024 * 1024)


class TheLog(Case):
    def test_every_attempt_adds_one_line_and_none_is_taken_away(self):
        for number in ("41001", "41004", "41006", "41001", "99999"):
            self.download(number)
        entries = self.log()
        self.assertEqual([(e["attachment"], e["outcome"]) for e in entries], [("41001", "saved"), ("41004", "refused"), ("41006", "refused"), ("41001", "refused"), ("99999", "refused")])
        self.assertTrue(all(set(e) == {"time", "story", "attachment", "outcome", "check", "reason", "saved_as", "bytes", "sha256", "stated_type", "stated_size"} for e in entries))

    def test_the_log_does_not_hold_jiras_name_for_the_file(self):
        self.download("41006")
        with open(os.path.join(self.downloads, attachments.LOG_NAME), encoding="utf-8") as f:
            self.assertNotIn("authorized_keys", f.read())

    def test_a_log_that_is_a_link_is_not_written_through(self):
        elsewhere = os.path.join(self.folder, "elsewhere.txt")
        with open(elsewhere, "w", encoding="utf-8") as f:
            f.write("not the tool's\n")
        os.symlink(elsewhere, os.path.join(self.downloads, attachments.LOG_NAME))
        code, text = self.download("41001")
        self.assertEqual(code, 1, text)
        with open(elsewhere, encoding="utf-8") as f:
            self.assertEqual(f.read(), "not the tool's\n")


class TheFilesOnDisk(Case):
    def test_an_index_that_is_not_the_tools_is_left_alone(self):
        path = os.path.join(self.out, "index.json")
        for text in ("{", json.dumps({"format": "x"}), ""):
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            code, out = self.sync()
            self.assertEqual(code, 1, out)
            with open(path, encoding="utf-8") as f:
                self.assertEqual(f.read(), text)

    def test_a_page_name_that_is_someone_elses_file_is_refused(self):
        with open(os.path.join(self.out, "readme.md"), "w", encoding="utf-8") as f:
            f.write("# Someone's own notes\n")
        code, text = self.sync(name="readme")
        self.assertEqual(code, 1, text)
        with open(os.path.join(self.out, "readme.md"), encoding="utf-8") as f:
            self.assertEqual(f.read(), "# Someone's own notes\n")

    def test_the_log_option_cannot_name_the_tools_own_files_or_a_strangers(self):
        self.sync()
        theirs = os.path.join(self.folder, "notes.txt")
        with open(theirs, "w", encoding="utf-8") as f:
            f.write("mine\n")
        for log in (os.path.join(self.out, "index.json"), os.path.join(self.out, "INDEX.MD"), theirs):
            code, text = self.sync(extra=["--log", log])
            self.assertEqual(code, 1, text)
        for log in (os.path.join(self.downloads, attachments.LOG_NAME), os.path.join(self.downloads, "x.txt"), theirs):
            code, text = self.download("41001", extra=["--log", log])
            self.assertEqual(code, 1, text)
        self.assertEqual(self.files(), [])
        with open(theirs, encoding="utf-8") as f:
            self.assertEqual(f.read(), "mine\n")
        log = os.path.join(self.folder, "log.txt")
        self.assertEqual(self.sync(extra=["--log", log])[0], 0)
        self.assertEqual(self.download("41001", extra=["--log", log])[0], 0)

    def test_names_and_folders_that_are_not_allowed(self):
        for name in ("Index", "../x", "a b", ""):
            self.assertEqual(self.sync(name=name)[0], 1)
        self.assertEqual(self.main("sync", "--source", "fake", "--issue", "DEMO-7/attachment", "--out-dir", self.out, "--name", "index", "--state", self.state)[0], 1)
        self.assertEqual(self.files(self.out), [])

    def test_something_unforeseen_is_a_refusal_and_not_a_crash(self):
        with mock.patch.object(attachments, "read_story", side_effect=RuntimeError("unforeseen")):
            code, text = self.sync()
        self.assertEqual(code, 1)
        self.assertIn("did not foresee (RuntimeError)", text)


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
        self.fake, self.requests, self.fail, self.waits = fake, [], fail, []

    def open(self, request, timeout=None):
        import urllib.error
        self.requests.append(request)
        self.waits.append(timeout)
        if self.fail and len(self.requests) == self.fail[0]:
            raise urllib.error.HTTPError(request.full_url, self.fail[1], "made up", {}, io.BytesIO(b"{}"))
        url = urllib.parse.urlparse(request.full_url)
        _, _, body = self.fake.get(url.path, dict(urllib.parse.parse_qsl(url.query)))
        return Response(body)


class ARealJira(Case):
    ENV = {"JIRA_BASE_URL": "https://real.example.invalid", "JIRA_EMAIL": "someone@example.invalid", "JIRA_API_TOKEN": MADE_UP}

    def setUp(self):
        Case.setUp(self)
        self.private = os.path.join(self.folder, "local-data", "jira")
        os.makedirs(self.private)

    def run_live(self, command="sync", env=None, out_dir=None, extra=(), fail=None, spoil=None):
        fake = fake_jira.FakeJira.open(self.fake_path)
        if spoil:
            spoil(fake)
        self.opener, self.handlers = Opener(fake, fail), []

        def build(*handlers):
            self.handlers.append(handlers)
            return self.opener
        argv = ["sync", "--source", "live", "--issue", "DEMO-7", "--out-dir", out_dir or self.private, "--name", "real"] if command == "sync" else \
            ["download", "--source", "live", "--issue", "DEMO-7", "--id", "41001", "--downloads", self.downloads]
        with mock.patch.dict(os.environ, env or self.ENV), mock.patch.object(attachments.urllib.request, "build_opener", build), \
                mock.patch.object(fake_jira.FakeJira, "content", side_effect=AssertionError("a file was asked for")):
            return self.main(*(argv + list(extra)))

    def test_a_download_from_a_real_jira_is_refused_before_anything_is_asked(self):
        code, text = self.run_live("download")
        self.assertEqual(code, 1, text)
        self.assertIn("a download from a real Jira is not something this tool does", text)
        self.assertEqual(self.opener.requests, [])
        self.assertEqual(self.handlers, [], "no connection was even made")
        self.assertEqual(self.files(), [])

    def test_a_real_connection_has_no_way_to_ask_for_a_file_or_for_one_attachment(self):
        with mock.patch.dict(os.environ, self.ENV):
            conn, _ = attachments.make_live(Opener(fake_jira.FakeJira.open(self.fake_path)))
        with self.assertRaises(attachments.Refused):
            conn.content("41001")
        for path in ("/rest/api/3/attachment/41001", "/rest/api/3/attachment/content/41001", "/rest/api/3/issue/DEMO-7/attachments", "/rest/api/3/search/jql", "/rest/api/3/issue/DEMO-7/../../x"):
            with self.assertRaises(attachments.Refused, msg=path):
                conn._get(path)
        with open(os.path.join(SKILL, "attachments.py"), encoding="utf-8") as f:
            source = f.read()
        live = source[source.index("def make_live("):source.index("def site_fingerprint(")]
        self.assertNotIn("content", live.replace("no `content`", "").replace("a file's contents", "").replace("Content", ""))

    def test_a_live_sync_sends_two_gets_follows_no_redirect_and_fetches_no_file(self):
        code, text = self.run_live()
        self.assertEqual(code, 0, text)
        self.assertEqual(sorted((r.get_method(), r.data, urllib.parse.urlparse(r.full_url).path) for r in self.opener.requests),
                         [("GET", None, "/rest/api/3/issue/DEMO-7"), ("GET", None, "/rest/api/3/myself")])
        self.assertEqual(self.opener.waits, [30, 30])
        self.assertEqual(self.handlers, [(attachments.NoRedirect,)])
        self.assertIsNone(attachments.NoRedirect().redirect_request(None, None, 302, "Found", {}, "https://elsewhere.example.invalid/"))
        for request in self.opener.requests:
            self.assertTrue(request.get_header("Authorization").startswith("Basic "))
            self.assertTrue(request.full_url.startswith("https://real.example.invalid/"))
        self.assertIn("Every one was a GET with no body", text)
        self.assertIn("NO FILE WAS DOWNLOADED.", text)
        self.assertEqual(sorted(os.listdir(self.private)), ["real.json", "real.md"])

    def test_a_live_sync_writes_only_inside_local_data(self):
        code, text = self.run_live(out_dir=self.out)
        self.assertEqual(code, 1)
        self.assertIn("local-data", text)
        self.assertEqual(self.opener.requests, [])
        self.assertEqual(self.files(self.out), [])

    def test_no_credential_site_address_name_or_person_is_in_the_output_or_the_log(self):
        import base64
        log = os.path.join(self.folder, "log.txt")
        code, text = self.run_live(extra=["--log", log])
        with open(log, encoding="utf-8") as f:
            saved = f.read()
        encoded = base64.b64encode(("someone@example.invalid:" + MADE_UP).encode()).decode()
        for secret in (MADE_UP, "someone@example.invalid", encoded, "real.example.invalid", "release-notes", "authorized_keys", "acct-", "Made-up Person"):
            self.assertNotIn(secret, text + saved)
        self.assertIn(attachments.site_fingerprint("real.example.invalid"), text)
        with mock.patch.dict(os.environ, self.ENV):
            _, secrets = attachments.make_live(Opener(None))
        self.assertEqual(sorted(secrets), sorted([MADE_UP, "someone@example.invalid", encoded]))

    def test_a_token_that_would_reach_a_file_stops_the_sync_before_anything_is_written(self):
        def spoil(fake):
            fake.data["attachments"][0]["filename"] = MADE_UP + ".txt"
        code, text = self.run_live(spoil=spoil)
        self.assertEqual(code, 1)
        self.assertNotIn(MADE_UP, text)
        self.assertEqual(os.listdir(self.private), [])

    def test_a_credential_in_any_output_stops_the_output(self):
        with mock.patch.dict(os.environ, self.ENV), mock.patch.object(attachments, "make_live", return_value=(attachments.Connection(None, "x"), [MADE_UP])), \
                mock.patch.object(attachments, "cmd_sync", side_effect=lambda *a, **k: attachments.say("leaked " + MADE_UP) or 0):
            code, text = self.main("sync", "--source", "live", "--issue", "DEMO-7", "--out-dir", self.private, "--name", "real")
        self.assertEqual(code, 1)
        self.assertNotIn(MADE_UP, text)
        self.assertIn("STOPPED", text)

    def test_the_saved_output_has_the_sites_address_taken_out(self):
        log = os.path.join(self.folder, "log.txt")
        with mock.patch.dict(os.environ, self.ENV), mock.patch.object(attachments, "make_live", return_value=(attachments.Connection(None, "real.example.invalid"), [])), \
                mock.patch.object(attachments, "cmd_sync", side_effect=lambda *a, **k: attachments.say("Story: see https://real.example.invalid/browse and real.example.invalid") or 0):
            self.main("sync", "--source", "live", "--issue", "DEMO-7", "--out-dir", self.private, "--name", "real", "--log", log)
        with open(log, encoding="utf-8") as f:
            saved = f.read()
        self.assertNotIn("real.example.invalid", saved)
        self.assertEqual(saved.count(attachments.SITE_MARK), 2)

    def test_the_method_reported_is_the_one_the_request_was_built_with(self):
        class Lying(attachments.urllib.request.Request):
            def get_method(self):
                return "POST"
        with mock.patch.object(attachments.urllib.request, "Request", Lying):
            code, text = self.run_live()
        self.assertIn("NOT EVERY ONE COULD BE READ BACK AS A PLAIN GET", text)

    def test_a_base_address_that_is_not_https_and_the_sites_name_only(self):
        for base in ("http://real.example.invalid", "https://real.example.invalid:8443", "https://real.example.invalid/jira", "https://user@real.example.invalid"):
            code, text = self.run_live(env=dict(self.ENV, JIRA_BASE_URL=base))
            self.assertEqual(code, 1, text)
            self.assertEqual(self.opener.requests, [])
        self.assertEqual(self.run_live(env=dict(self.ENV, JIRA_BASE_URL="https://Real.Example.invalid/"))[0], 0)

    def test_a_real_servers_refusals_write_nothing(self):
        for status in (401, 403, 404, 429, 500, 302):
            for on in (1, 2):
                code, text = self.run_live(fail=(on, status))
                self.assertEqual(code, 1, text)
                self.assertEqual(os.listdir(self.private), [])
        self.assertIn("rejected the credentials (401)", self.run_live(fail=(1, 401))[1])

    def test_the_made_up_jiras_folder_is_refused_for_a_real_one_and_no_variables_means_no_request(self):
        code, text = self.run_live(extra=["--state", self.state])
        self.assertEqual(code, 1)
        self.assertIn("for the made-up Jira only", text)
        with mock.patch.dict(os.environ, {}, clear=True):
            code, text = self.main("sync", "--source", "live", "--issue", "DEMO-7", "--out-dir", self.private, "--name", "real")
        self.assertEqual(code, 1)
        self.assertIn("JIRA_BASE_URL is not set", text)


class TheMadeUpJiraItself(Case):
    def test_its_files_are_what_its_description_says(self):
        made = {a["id"]: a for a in fake_jira.fresh()["attachments"]}
        self.assertEqual(made["41001"]["size"], len(fake_jira.content_of("41001")))
        self.assertGreater(len(fake_jira.content_of("41008")), attachments.SIZE_LIMIT)
        self.assertEqual(made["41008"]["size"], 200)
        self.assertTrue(fake_jira.content_of("41007").startswith(b"PK\x03\x04"))
        self.assertTrue(fake_jira.content_of("41012").startswith(b"%PDF-"))

    def test_the_tool_does_not_change_it(self):
        with open(self.fake_path, encoding="utf-8") as f:
            before = json.load(f)["attachments"]
        self.sync()
        self.download("41001")
        with open(self.fake_path, encoding="utf-8") as f:
            self.assertEqual(json.load(f)["attachments"], before)


class WhatTheReadersFound(Case):
    """Each of these is something an independent reader found in the first version, or showed the tests would miss."""

    def saved_files(self, folder=None):
        return [n for n in self.files(folder) if n != attachments.LOG_NAME]

    def git(self, *patterns):
        root = os.path.join(self.folder, "repo")
        os.makedirs(root, exist_ok=True)
        if not os.path.exists(os.path.join(root, ".git")):
            subprocess.run(["git", "init", "-q", root], check=True, capture_output=True)
        with open(os.path.join(root, ".gitignore"), "w", encoding="utf-8") as f:
            f.write("\n".join(patterns) + "\n")
        return root

    # ------------------------------------------------ no saved file without a line in the log

    def test_a_log_that_cannot_be_added_to_stops_the_download_before_jira_is_asked(self):
        log = os.path.join(self.downloads, attachments.LOG_NAME)
        elsewhere = os.path.join(self.folder, "elsewhere.txt")
        with open(elsewhere, "w", encoding="utf-8") as f:
            f.write("not the tool's\n")

        def as_link():
            os.symlink(elsewhere, log)

        def as_folder():
            os.makedirs(log)

        def as_pipe():
            os.mkfifo(log)

        def as_second_name():
            os.link(elsewhere, log)

        def as_read_only():
            with open(log, "w", encoding="utf-8") as f:
                f.write("")
            os.chmod(log, 0o400)
        for make in (as_link, as_folder, as_pipe, as_second_name, as_read_only):
            with self.subTest(make.__name__):
                make()
                code, text = self.download("41001")
                self.assertEqual(code, 1, text)
                self.assertIn("Nothing was asked of Jira", text)
                self.assertEqual(self.saved_files(), [], "a file was saved with no line in the log")
                self.assertEqual(self.asked(), {"content": 0, "details": 0, "issue": 0, "myself": 0})
                if os.path.isdir(log) and not os.path.islink(log):
                    os.rmdir(log)
                else:
                    os.chmod(log, 0o600) if not os.path.islink(log) and os.path.isfile(log) else None
                    os.unlink(log)
        with open(elsewhere, encoding="utf-8") as f:
            self.assertEqual(f.read(), "not the tool's\n")

    def test_a_line_that_cannot_be_written_after_the_save_takes_the_file_away_again(self):
        with mock.patch.object(attachments, "log_line", side_effect=OSError("made up: the disk is full")):
            code, text = self.download("41001")
        self.assertEqual(code, 1, text)
        self.assertEqual(self.saved_files(), [], "a file is there without a line in the log")
        self.assertIn("The file that had been saved was taken away again", text)
        self.assertNotIn("SAVED", text)

    def test_every_refusal_once_the_folder_is_accepted_is_in_the_log(self):
        with self.add("bad.csv", "text/csv", content=b"a,b\r1,2\rmade up with bare returns\r"), self.add("wide.csv", "text/csv", content=b"a," + b"x" * 140000 + b"\n", number="41901"):
            for number in ("41900", "41901", "all", "41001,41002"):
                self.download(number)
        with mock.patch.object(fake_jira.FakeJira, "content", lambda fake, ident: (200, iter(["not bytes"]))):
            self.download("41001")
        with mock.patch.object(attachments, "check_bytes", side_effect=RuntimeError("unforeseen")):
            code, text = self.download("41002")
        self.assertEqual(code, 1)
        self.assertIn("did not foresee (RuntimeError)", text)
        entries = self.log()
        self.assertEqual(len(entries), 6, "an attempt left no line")
        self.assertTrue(all(e["outcome"] == "refused" or e["attachment"] in ("41900", "41901") for e in entries))
        self.assertEqual([e["attachment"] for e in entries][2:4], ["all", "41001,41002"])
        self.assertEqual(entries[-1]["check"], "something unforeseen")
        self.assertEqual(self.saved_files(), [f for f in ("41900-bad.csv", "41901-wide.csv") if f in self.saved_files()])

    def test_the_time_in_the_log_is_the_time_of_the_attempt(self):
        import datetime
        before = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0, tzinfo=None)
        self.download("41001")
        at = datetime.datetime.strptime(self.log()[0]["time"], "%Y-%m-%dT%H:%M:%SZ")
        self.assertLessEqual(abs((at - before).total_seconds()), 5)

    def test_nothing_of_a_refused_file_touches_the_disk_even_for_a_moment(self):
        with mock.patch.object(attachments, "write_file", side_effect=AssertionError("something was written for a refused file")), \
                mock.patch.object(attachments.tempfile, "mkstemp", side_effect=AssertionError("a temporary file was made")):
            for number, _, _, _ in ARefusedDownload.CASES:
                code, text = self.download(number)
                self.assertEqual(code, 2, text)

    # ------------------------------------------------ outside source control

    def test_a_folder_whose_contents_are_ignored_by_a_pattern_is_not_enough(self):
        cases = {"only the name once asked about": ("dl/probe",), "its contents, with text files taken back": ("dl/*", "!dl/*.txt"), "one kind of file": ("dl/*.pdf",)}
        for what, patterns in cases.items():
            with self.subTest(what):
                root = self.git(*patterns)
                target = os.path.join(root, "dl")
                os.makedirs(target, exist_ok=True)
                code, text = self.download("41001", downloads=target)
                self.assertEqual(code, 1, text)
                self.assertIn("does not ignore that folder as a folder", text)
                self.assertEqual(os.listdir(target), [])
        root = self.git("/dl/")
        code, text = self.download("41001", downloads=os.path.join(root, "dl"))
        self.assertEqual(code, 0, text)
        staged = subprocess.run(["git", "-C", root, "add", "-A", "--dry-run"], capture_output=True, text=True).stdout
        self.assertNotIn("41001", staged, "Git itself would have picked the saved file up")

    def test_gits_settings_in_the_environment_do_not_change_the_answer(self):
        root = self.git("# nothing ignored")
        tracked = os.path.join(root, "tracked")
        os.makedirs(tracked)
        other = os.path.join(self.folder, "other")
        subprocess.run(["git", "init", "-q", other], check=True, capture_output=True)
        with open(os.path.join(other, ".git", "info", "exclude"), "w", encoding="utf-8") as f:
            f.write("*\n")
        everything = os.path.join(self.folder, "ignore-everything")
        with open(everything, "w", encoding="utf-8") as f:
            f.write("*\n")
        for env in ({"GIT_DIR": os.path.join(other, ".git"), "GIT_WORK_TREE": root}, {"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_" + "KEY_0": ".".join(["core", "excludesFile"]), "GIT_CONFIG_VALUE_0": everything}):
            with self.subTest(sorted(env)[0]), mock.patch.dict(os.environ, env):
                code, text = self.download("41001", downloads=tracked)
                self.assertEqual(code, 1, text)
                self.assertEqual(os.listdir(tracked), [])

    def test_a_repository_of_another_kind_a_deep_folder_and_a_link_into_a_repository(self):
        for mark in (".hg", ".svn", ".jj"):
            top = os.path.join(self.folder, "other-" + mark.strip("."))
            target = os.path.join(top, "a", "b")
            os.makedirs(target)
            os.makedirs(os.path.join(top, mark))
            code, text = self.download("41001", downloads=target)
            self.assertEqual(code, 1, text)
            self.assertIn("a repository of a kind this tool cannot ask", text)
            self.assertEqual(os.listdir(target), [])
        root = self.git("# nothing ignored")
        deep = os.path.join(root, "a", "b", "c", "d")
        os.makedirs(deep)
        self.assertEqual(self.download("41001", downloads=deep)[0], 1)
        link = os.path.join(self.folder, "looks-outside")
        os.symlink(deep, link)
        code, text = self.download("41001", downloads=link)
        self.assertEqual(code, 1, text)
        self.assertEqual(os.listdir(deep), [])

    # ------------------------------------------------ the place a file is saved

    def test_a_link_or_a_file_that_appears_under_the_saved_name_is_never_written_over(self):
        elsewhere = os.path.join(self.folder, "elsewhere.txt")
        with open(elsewhere, "w", encoding="utf-8") as f:
            f.write("not the tool's\n")
        target = os.path.join(self.downloads, "41001-release-notes.txt")
        os.symlink(os.path.join(self.folder, "nowhere"), target)          # a link that leads nowhere: it is still something there
        code, text = self.download("41001")
        self.assertEqual(code, 2, text)
        self.assertTrue(os.path.islink(target))
        self.assertFalse(os.path.exists(os.path.join(self.folder, "nowhere")))
        os.unlink(target)
        real = fake_jira.FakeJira.content

        def content(fake, ident):                                             # the name is taken while the file is being fetched
            status, pieces = real(fake, ident)
            os.symlink(elsewhere, target)
            return status, pieces
        with mock.patch.object(fake_jira.FakeJira, "content", content):
            code, text = self.download("41001")
        self.assertEqual(code, 2, text)
        self.assertIn("appeared under that name", text)
        with open(elsewhere, encoding="utf-8") as f:
            self.assertEqual(f.read(), "not the tool's\n")

    def test_a_name_that_points_at_a_folder_that_really_is_there_writes_nothing_in_it(self):
        code, text = self.download("41016")
        self.assertEqual(code, 2, text)
        self.assertIn("REFUSED by the name", text)
        self.assertEqual(sorted(os.listdir(self.state)), ["fake-jira.json"])
        self.assertEqual(sorted(os.listdir(os.path.join(self.folder, "jira"))), ["fake-jira.json"])
        with mock.patch.object(attachments, "check_name", side_effect=lambda name: name.rsplit(".", 1)[1]):      # even with the name check gone
            code, text = self.download("41016")
        self.assertEqual(self.saved_files(), ["41016-jira-planted.txt"])
        self.assertEqual(sorted(os.listdir(self.state)), ["fake-jira.json"])

    def test_an_extension_must_be_plain_letters_and_a_name_has_a_longest_length(self):
        for name in ("data.cſv", "x.jſon", "a.tхt", "a.tx-t", "a.txt "):
            with self.assertRaises(attachments.Check, msg=repr(name)):
                attachments.check_claims(name, "text/plain", 10)
        with self.assertRaises(attachments.Check) as caught:
            attachments.check_claims("a" * 252 + ".txt", "text/plain", 10)
        self.assertEqual(caught.exception.which, "the name")
        self.assertEqual(attachments.check_claims("a" * 251 + ".txt", "text/plain", 10), "txt")

    def test_the_type_jira_states_may_carry_capitals_or_a_character_set(self):
        for stated in ("Text/Plain", "text/plain; charset=utf-8", " text/plain "):
            self.assertEqual(attachments.check_claims("a.txt", stated, 10), "txt")

    # ------------------------------------------------ the bytes

    def test_a_file_that_arrives_in_too_many_pieces_or_empty_ones_is_stopped(self):
        with mock.patch.object(attachments, "MAX_PIECES", 50), mock.patch.object(fake_jira.FakeJira, "content", lambda fake, ident: (200, (b"" for _ in range(10 ** 9)))):
            code, text = self.download("41001")
        self.assertEqual(code, 2, text)
        self.assertIn("in too many pieces", text)
        self.assertEqual(self.saved_files(), [])

    def test_the_output_says_only_the_beginning_of_a_picture_or_pdf_was_looked_at(self):
        _, text = self.download("41003")
        self.assertIn("the file BEGINS the way a .png file begins. Only its beginning was looked at", text)
        self.assertNotIn("they are what a", text)
        _, text = self.download("41001")
        self.assertIn("the file is text all through", text)

    def test_what_the_scan_missed_in_its_first_version(self):
        pdf = fake_jira.PDF
        far = b"x" * 100000
        found = [("pdf", pdf + b"<< /Open#41ction 3 0 R >>"), ("pdf", pdf + b"<< /S /J#61vaScript >>"), ("pdf", pdf + b"<< /J#53 (x) >>"), ("pdf", pdf + b"<< /S /SubmitForm >>"),
                 ("pdf", pdf + b"<< /S /GoToR >>"), ("pdf", pdf + b"<< /RichMedia 1 0 R >>"), ("pdf", pdf + b"<< /XFA 1 0 R >>"),
                 ("pdf", pdf + b"\n" + KEY_MARK + b"\nmade up\n"), ("png", fake_jira.PNG + far + b"\x7fELF made up"), ("jpg", JPG + far + b"PK\x03\x04 made up"),
                 ("txt", KEY_MARK.replace(b"RSA", b"PGP").replace(b"KEY-", b"KEY BLOCK-") + b"\nmade up\n"), ("txt", b"PuTTY-User-Key-File-3: made up\n"), ("txt", b"\xef\xbb\xbf\n  #!/bin/sh\n"),
                 ("md", b'made up <iframe src="x">'), ("md", b"[x](JavaScript : alert(1))"), ("txt", far + fake_jira.TEST_STRING),
                 ("csv", b"a,b\nx,+1+cmd|' /C calc'!A0\n"), ("csv", b"a,b\nx,-2+3+cmd|'x'!A0\n"), ("csv", b"a;b\nx;=HYPERLINK(1)\n"), ("csv", b"a\tb\nx\t=cmd|x\n"),
                 ("csv", "a,b\nx,＝1+1\n".encode("utf-8")), ("csv", b'a,b\nx, "=1+1"\n'), ("csv", b"a,b\rx,@SUM(1)\r")]
        for extension, data in found:
            with self.subTest(extension + " " + repr(data[-30:])), self.assertRaises(attachments.Check) as caught:
                attachments.scan(extension, data)
            self.assertEqual(caught.exception.which, "the scan")

    def test_a_zero_byte_far_into_a_text_file_is_found(self):
        with self.assertRaises(attachments.Check):
            attachments.check_bytes("txt", b"made up " * 20000 + b"\x00" + b"more")

    # ------------------------------------------------ a sync

    def test_a_sync_does_not_reach_a_files_bytes_by_any_road(self):
        with mock.patch.object(fake_jira, "content_of", side_effect=AssertionError("a file's bytes were made")), \
                mock.patch.object(attachments.urllib.request, "urlopen", side_effect=AssertionError("an address was opened")):
            code, text = self.sync()
        self.assertEqual(code, 0, text)
        with open(self.fake_path, encoding="utf-8") as f:
            self.assertEqual(json.load(f)["contents_asked_for"], [])
        self.assertNotIn("/rest/api/3/attachment/content", json.dumps(self.index()) + self.page(), "the address Jira gives for the contents is not kept")

    def test_every_attachment_of_a_story_with_many_is_recorded(self):
        with self.jira() as jira:
            for n in range(40):
                jira.data["attachments"].append({"id": str(42000 + n), "filename": "made-up-%d.txt" % n, "mimeType": "text/plain", "size": 5, "author": "acct-ana", "created": "2026-11-08T09:00:00.000+0000"})
        code, text = self.sync()
        self.assertEqual(len(self.index()["attachments"]), 56)
        self.assertIn("ATTACHMENTS LISTED BY JIRA: 56.", text)
        self.assertEqual(len([line for line in self.page().split("\n") if re.match(r"\| 4[0-9]{4} \|", line)]), 56)

    def test_a_dangling_link_in_the_folder_does_not_stop_a_sync(self):
        os.symlink(os.path.join(self.folder, "nowhere"), os.path.join(self.out, "stray"))
        self.assertEqual(self.sync()[0], 0)

    def test_the_one_named_and_only_that_one_is_what_jira_was_asked_for(self):
        self.download("41003")
        with open(self.fake_path, encoding="utf-8") as f:
            self.assertEqual(json.load(f)["contents_asked_for"], ["41003"])

    def test_the_saved_file_is_not_opened_by_any_road_after_it_is_saved(self):
        touched = []
        target = os.path.join(self.downloads, "41001-release-notes.txt")
        real = {"open": open, "os_open": os.open, "popen": subprocess.Popen}

        def is_target(path):
            return isinstance(path, (str, bytes, os.PathLike)) and os.fsdecode(path) == target

        def watch_open(path, *a, **k):
            if is_target(path):
                touched.append("open")
            return real["open"](path, *a, **k)

        def watch_os_open(path, *a, **k):
            if is_target(path):
                touched.append("os.open")
            return real["os_open"](path, *a, **k)

        def watch_popen(command, *a, **k):
            if any(target in str(part) for part in (command if isinstance(command, (list, tuple)) else [command])):
                touched.append("started a program with it")
            return real["popen"](command, *a, **k)
        import io as io_module
        with mock.patch("builtins.open", watch_open), mock.patch.object(io_module, "open", watch_open), mock.patch.object(os, "open", watch_os_open), \
                mock.patch.object(subprocess, "Popen", watch_popen), mock.patch.object(os, "system", side_effect=AssertionError("ran something")), \
                mock.patch.object(os, "startfile", side_effect=AssertionError("opened something"), create=True):
            code, _ = self.download("41001")
        self.assertEqual(code, 0)
        self.assertEqual(touched, [])
        self.assertTrue(os.path.exists(target))


class WhatTheReadersFoundAboutARealJira(ARealJira):
    def test_a_live_index_does_not_say_an_attachment_could_be_asked_for(self):
        code, text = self.run_live()
        self.assertEqual(code, 0, text)
        with open(os.path.join(self.private, "real.json"), encoding="utf-8") as f:
            verdicts = [a["if_asked_for"] for a in json.load(f)["attachments"]]
        self.assertFalse(any(v.startswith("could be asked for") for v in verdicts))
        self.assertTrue(verdicts[0].startswith("could not be asked for: this tool does not download from a real Jira"))
        self.assertIn("0 could be asked for", text)

    def test_a_live_sync_asks_for_the_attachment_field_and_nothing_more(self):
        self.run_live()
        queries = [urllib.parse.urlparse(r.full_url).query for r in self.opener.requests]
        self.assertEqual(sorted(queries), ["", "fields=attachment"])


if __name__ == "__main__":
    unittest.main()
