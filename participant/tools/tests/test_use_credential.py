"""Tests for participant/tools/use_credential.py. Every credential here is made up, and is put together when the test
runs, so that no file holds anything shaped like one."""
import base64
import os
import subprocess
import sys
import tempfile
import unittest
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, TOOLS)
import use_credential as uc   # noqa: E402

FAKE = "ghp_" + ("example" * 6)[:36]                 # shaped like a GitHub token, and plainly not one
HEX_KEY = ("example".encode("ascii").hex() * 4)[:32]   # 32 hex characters, the shape of a Trello API key


def run(*args, value=FAKE, extra_env=None):
    env = {k: v for k, v in os.environ.items() if k != uc.VARIABLE}
    if value is not None:
        env[uc.VARIABLE] = value
    env.update(extra_env or {})
    done = subprocess.run([sys.executable, os.path.join(TOOLS, "use_credential.py")] + list(args), capture_output=True, text=True, env=env)
    return done.returncode, done.stdout, done.stderr


def every_form(value):
    return [value, urllib.parse.quote(value, safe=""), base64.b64encode(value.encode()).decode(),
            base64.b64encode(("%s:%s" % (uc.ACCOUNT, value)).encode()).decode(), base64.urlsafe_b64encode(value.encode()).decode()]


class TheCredentialIsNeverPrinted(unittest.TestCase):
    """Criteria 2 and 3."""

    def clean(self, *texts):
        for text in texts:
            for form in every_form(FAKE) + every_form(FAKE + "-out-of-date"):
                self.assertNotIn(form, text)
            self.assertNotIn("exampleexample", text)

    def test_ordinary_use(self):
        code, out, err = run("call")
        self.assertEqual((code, err), (0, ""))
        self.assertIn("Its value: [REDACTED] (40 characters)", out)
        self.assertIn("accepted the credential", out)
        self.clean(out)

    def test_a_debugging_print_of_the_request_and_its_headers(self):
        code, out, err = run("call", "--verbose")
        self.assertEqual(code, 0)
        self.assertIn("Authorization: Bearer [REDACTED]", out)
        self.assertIn("access_" + "token=[REDACTED]", out)
        self.assertIn("Basic [REDACTED]", out)
        self.clean(out, err)

    def test_an_error_from_the_service_that_repeats_the_credential(self):
        code, out, err = run("call", "--rejected")
        self.assertEqual(code, 1)
        self.assertIn("THE SERVICE REFUSED (status 401)", err)
        self.assertIn("'Bearer [REDACTED]'", err)
        self.clean(out, err)

    def test_a_crash_whose_message_holds_the_credential(self):
        code, out, err = run("call", "--crash")
        self.assertEqual(code, 3)
        self.assertIn("RuntimeError: could not read the reply to the request made with Bearer [REDACTED]", err)
        self.assertIn("Traceback", err)
        self.clean(out, err)

    def test_the_service_really_does_repeat_it_so_the_mask_is_doing_the_work(self):
        status, body = uc.MadeUpService(FAKE).get("/items", {"Authorization": "Bearer wrong-value"})
        self.assertEqual(status, 401)
        self.assertIn("wrong-value", body["error"])

    def test_masking_covers_each_form_the_value_takes(self):
        uc.SECRETS[:] = uc.forms_of(FAKE)
        try:
            for form in every_form(FAKE):
                self.assertNotIn(form, uc.masked("before %s after" % form))
                self.assertEqual(uc.masked("before %s after" % form), "before [REDACTED] after")
            self.assertEqual(uc.masked("nothing secret here"), "nothing secret here")
        finally:
            del uc.SECRETS[:]

    def test_a_value_with_characters_a_web_address_changes(self):
        value = "example/with+odd=chars&more-1234"
        code, out, err = run("call", "--verbose", value=value)
        self.assertEqual(code, 0, out + err)
        for form in every_form(value) + [urllib.parse.quote_plus(value)]:
            self.assertNotIn(form, out)

    def test_each_base64_form_is_masked_when_the_two_base64_alphabets_differ(self):
        """For most values the ordinary and the URL-safe base64 are the same text, and one hides a gap in the other."""
        def differs(raw):
            return base64.b64encode(raw) != base64.urlsafe_b64encode(raw)
        value = next(v for v in ("example-%04d-made-up-value-~~??" % n for n in range(10000))
                     if differs(v.encode()) and differs(("%s:%s" % (uc.ACCOUNT, v)).encode()))
        uc.SECRETS[:] = uc.forms_of(value)
        try:
            for form in every_form(value) + [base64.urlsafe_b64encode(("%s:%s" % (uc.ACCOUNT, value)).encode()).decode()]:
                self.assertEqual(uc.masked("x %s y" % form), "x [REDACTED] y")
        finally:
            del uc.SECRETS[:]

    def test_percent_escapes_written_in_small_letters_are_masked_too(self):
        value = "example/with+odd=chars&more-1234"
        small = urllib.parse.quote(value, safe="").lower()
        self.assertNotEqual(small, urllib.parse.quote(value, safe=""))
        uc.SECRETS[:] = uc.forms_of(value)
        try:
            self.assertEqual(uc.masked("x %s y" % small), "x [REDACTED] y")
        finally:
            del uc.SECRETS[:]


class WhereTheCredentialComesFrom(unittest.TestCase):
    """Criterion 1."""

    def test_not_set_is_refused(self):
        code, out, _ = run("call", value=None)
        self.assertEqual(code, 1)
        self.assertIn("REFUSED: the environment variable GTQ_DEMO_TOKEN is not set", out)

    def test_there_is_no_way_to_give_it_on_the_command_line_or_from_a_file(self):
        for extra in (["--token", FAKE], ["--token-file", "x"], ["--password", "x"], [FAKE]):
            code, out, err = run("call", *extra, value=None)
            self.assertEqual(code, 2, extra)
            self.assertIn("REFUSED: the command line was not understood", err)

    def test_a_credential_typed_on_the_command_line_by_mistake_is_not_repeated(self):
        """Python's usual complaint quotes what was typed. No mask could know that value, so nothing typed is repeated."""
        for extra in (["call", "--token", FAKE], ["call", FAKE], [FAKE], ["scan"], ["call", "--token=" + FAKE], []):
            for value in (None, FAKE):
                code, out, err = run(*extra, value=value)
                self.assertEqual(code, 2, extra)
                self.assertNotIn("exampleexample", out + err, extra)
                self.assertNotIn("unrecognized", out + err)
                self.assertNotIn("usage:", out + err)

    def test_a_value_that_is_not_proper_text_is_still_masked(self):
        value = "example-" + "\udcff\udcfe" + "-not-proper-text-0123"
        uc.SECRETS[:] = []
        try:
            uc.remember(value)
            self.assertEqual(uc.masked("x %s y" % value), "x [REDACTED] y")
        finally:
            del uc.SECRETS[:]

    def test_used_from_another_program_a_failure_is_still_masked_and_does_not_escape(self):
        """main() reports its own failures. The mask does not depend on the file being run as a script."""
        import contextlib
        import io
        out, err = io.StringIO(), io.StringIO()
        before = os.environ.get(uc.VARIABLE)
        os.environ.update({uc.VARIABLE: FAKE})
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = uc.main(["call", "--crash"])
        finally:
            os.environ.pop(uc.VARIABLE)
            if before is not None:
                os.environ.update({uc.VARIABLE: before})
            del uc.SECRETS[:]
        self.assertEqual(code, 3)
        self.assertIn("Bearer [REDACTED]", err.getvalue())
        self.assertNotIn("exampleexample", out.getvalue() + err.getvalue())

    def test_a_short_value_is_refused_in_words_that_are_not_masked(self):
        """A short value is not written down for masking: holes punched in ordinary text would give it away."""
        code, out, err = run("call", value="REFUSED")
        self.assertEqual(code, 1)
        self.assertIn("REFUSED: the value of GTQ_DEMO_TOKEN is shorter than 20 characters", out)
        self.assertNotIn("[REDACTED]", out + err)

    def test_a_value_that_is_not_plainly_made_up_is_refused_and_not_shown(self):
        value = "a-real-looking-value-0123456789"
        code, out, err = run("call", "--verbose", value=value)
        self.assertEqual(code, 1)
        self.assertIn('does not contain the word "example"', out)
        self.assertNotIn(value, out + err)
        self.assertNotIn("accepted", out)

    def test_a_short_value_is_refused(self):
        self.assertEqual(run("call", value="example-short")[0], 1)

    def test_the_tool_reads_no_file_and_writes_none(self):
        with open(os.path.join(TOOLS, "use_credential.py"), encoding="utf-8") as f:
            source = f.read()
        self.assertEqual(source.count("open("), 1)                 # the one in `scan`, which reads the files it is asked to scan
        self.assertNotIn('"w"', source)
        self.assertNotIn("os.environ[", source)                     # it never sets the variable either


class TheSecondPattern(unittest.TestCase):
    """The stretch goal: one more shape, beside the program's scanner."""

    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix="gtq-secrets-test-")

    def tearDown(self):
        for name in os.listdir(self.folder):
            os.remove(os.path.join(self.folder, name))
        os.rmdir(self.folder)

    def scan(self, text):
        path = os.path.join(self.folder, "file.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        code, out, _ = run("scan", path, value=None)
        return code, out

    def test_a_bare_key_on_a_line_that_says_trello_is_found_and_not_shown(self):
        code, out = self.scan("notes\nOur Trello key is %s for the sandbox board\n" % HEX_KEY)
        self.assertEqual(code, 1)
        self.assertIn("file.txt:2:19: [trello-api-key]", out)
        self.assertNotIn(HEX_KEY, out)
        self.assertIn("1 finding", out)

    def test_a_key_as_the_value_of_a_field_named_key_is_found(self):
        for line in ('{"key": "%s"}' % HEX_KEY, "apiKey: %s" % HEX_KEY, "api_key = '%s'" % HEX_KEY):
            self.assertEqual(self.scan(line + "\n")[0], 1, line)

    def test_the_programs_scanner_does_not_find_the_first_two_of_those(self):
        """Why the second pattern is worth having. If the program's scanner learns this shape, this test will say so."""
        sys.path.insert(0, os.path.abspath(os.path.join(TOOLS, "..", "..")))
        try:
            from quest_app.secret_patterns import scan_text
        except Exception:      # the program's code needs a newer Python than the system's
            self.skipTest("the program's scanner needs the project's own Python: run these tests with .venv/bin/python to make this comparison")
        self.assertEqual(scan_text("Our Trello key is %s for the sandbox board" % HEX_KEY), [])
        self.assertEqual(scan_text('{"key": "%s"}' % HEX_KEY), [])

    def test_32_hex_characters_with_nothing_to_say_what_they_are_are_not_reported(self):
        self.assertEqual(self.scan("checksum %s\n" % HEX_KEY)[0], 0)

    def test_a_longer_run_or_one_with_capitals_is_not_a_trello_key(self):
        self.assertEqual(self.scan("trello %s\n" % (HEX_KEY + "ab"))[0], 0)
        self.assertEqual(self.scan("trello %s\n" % HEX_KEY.upper())[0], 0)

    def test_a_clean_file_passes(self):
        code, out = self.scan("Nothing here.\n")
        self.assertEqual(code, 0)
        self.assertIn("0 findings", out)

    def test_a_key_given_as_an_option_is_found(self):
        for line in ("tool --key %s" % HEX_KEY, "tool --api-key=%s" % HEX_KEY, "TRELLO_API_KEY=%s" % HEX_KEY):
            self.assertEqual(self.scan(line + "\n")[0], 1, line)

    def test_a_folder_is_looked_into(self):
        """The program's scanner, given a folder, scans nothing and passes. This one must not."""
        self.scan("Our Trello key is %s\n" % HEX_KEY)
        code, out, _ = run("scan", self.folder, value=None)
        self.assertEqual(code, 1)
        self.assertIn("1 file scanned, 1 finding", out)

    def test_a_scan_that_looked_at_no_file_is_not_a_pass(self):
        code, out, _ = run("scan", self.folder, value=None)      # the folder is empty
        self.assertEqual(code, 1)
        self.assertIn("NOTHING WAS SCANNED", out)

    def test_a_file_that_is_not_text_is_skipped_and_not_counted_as_scanned(self):
        with open(os.path.join(self.folder, "picture.bin"), "wb") as f:
            f.write(b"\x00\x01trello " + HEX_KEY.encode("ascii"))
        with open(os.path.join(self.folder, "notes.txt"), "w", encoding="utf-8") as f:
            f.write("nothing\n")
        code, out, _ = run("scan", self.folder, value=None)
        self.assertEqual(code, 0)
        self.assertIn("1 file scanned, 0 findings", out)

    def test_a_file_that_cannot_be_read_is_not_passed_as_clean(self):
        code, out, _ = run("scan", os.path.join(self.folder, "not-there.txt"), value=None)
        self.assertEqual(code, 1)
        self.assertIn("could not be read", out)


if __name__ == "__main__":
    unittest.main()
