#!/usr/bin/env python3
"""Records logs/preview.txt, confirmation.txt, comment-check.txt and rerun.txt for the quest jira-add-comment.

Each record has two parts.

  PART A is the participant's own run against their real Jira sandbox. This script does not make that run and
  cannot: it has no credentials and contacts nothing. The participant ran the commands in their own terminal, and
  the workflow saved what it printed, with the site's address removed, in logs/ under names starting live-. This
  script copies those files in unchanged. Where one is not there yet, PART A says so.

  PART B is recorded here, against participant/skills/jira-add-comment/fake_jira.py, a made-up Jira. No network is
  used. Each run is the real command, started as a person would start it, and what it printed is written down. It
  shows the refusals and the cases that would be unsafe or impossible to stage on a real site.

The fake Jira keeps its state in a temporary folder, shown as STATE. The change file and the text file are copied
to another, shown as WORK, so that a run can change the text after a preview. Both are deleted at the end.

Run from anywhere:  python3 scripts/record_evidence.py
Exit code 0 if every check came out as expected, 1 if not.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ATTEMPT = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(ATTEMPT, "..", "..", "..", ".."))
SKILL = "participant/skills/jira-add-comment"
FIX = os.path.join(ROOT, SKILL, "fixtures")
ALLOW = SKILL + "/fixtures/fake-allowlist.json"
HEAD = ("Recorded by scripts/record_evidence.py. Each block between dashed lines is what a command printed.\n"
        "STATE and WORK stand for temporary folders.")
FAKE_NOTE = ("The Jira in this part is fake_jira.py, a made-up one. No real Jira was read or written, so nothing in it is\n"
             "redacted: the site, the projects, the stories and the people are invented.")
TEXT_FIRST = "Checked against the made-up onboarding checklist on 25 November."


class Log:
    def __init__(self, title, state, work):
        self.lines, self.problems, self.state, self.work, self.count = [title, HEAD, ""], [], state, work, 0

    def out(self, text=""):
        self.lines.append(text)

    def part(self, text):
        self.lines += ["", "=" * 78, text]

    def check(self, label, ok):
        self.count += 1
        self.lines.append("  %-4s %s" % ("ok" if ok else "FAIL", label))
        if not ok:
            self.problems.append(label)

    def tidy(self, text):
        return text.replace(self.state, "STATE").replace(self.work, "WORK")

    def command(self, script, *args):
        real = [a.replace("STATE", self.state).replace("WORK", self.work) for a in args]
        self.out("$ python3 %s/%s %s" % (SKILL, script, " ".join('"%s"' % a if " " in a else a for a in args)))
        done = subprocess.run([sys.executable, os.path.join(ROOT, SKILL, script)] + real, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=ROOT)
        text = self.tidy(done.stdout.rstrip("\n"))
        self.lines += ["-" * 78, text, "-" * 78, "exit code: %d" % done.returncode]
        return done.returncode, text

    def live(self, title, *names):
        """Copies the participant's saved live logs in, unchanged. Returns the text of those that are there."""
        self.part("PART A. The real sandbox: %s" % title)
        self.out("These are the files the workflow saved, with the site's address removed, when the participant ran it in their own")
        self.out("terminal with their own credentials. This script copies them in unchanged. It cannot establish by reading them who")
        self.out("ran what, or that a person read a preview before confirming it. The saved files hold no command line and no exit")
        self.out("code, so the commands are given in PROOF.md and not here. Each check below is of the saved text and no more.")
        found = []
        for name in names:
            path = os.path.join(ATTEMPT, "logs", name)
            self.out("")
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    text = f.read().rstrip("\n")
                self.lines += ["logs/%s:" % name, "-" * 78, text, "-" * 78]
                found.append(text)
            else:
                self.out("logs/%s: NOT THERE YET. This run has not been made, or its output was not saved." % name)
                found.append(None)
        return found

    def save(self, name):
        self.lines += ["", "RESULT: %s" % ("%d OF %d CHECKS FAILED." % (len(self.problems), self.count) if self.problems else "ALL CHECKS PASSED. %d checks." % self.count)]
        os.makedirs(os.path.join(ATTEMPT, "logs"), exist_ok=True)
        with open(os.path.join(ATTEMPT, "logs", name), "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(self.lines) + "\n")
        print("%s: %s" % (name, self.lines[-1]))
        for label in self.problems:
            print("  FAILED: " + label)
        return not self.problems


def fresh():
    state, work = tempfile.mkdtemp(prefix="gtq-comment-state-"), tempfile.mkdtemp(prefix="gtq-comment-work-")
    for name in os.listdir(FIX):
        shutil.copy(os.path.join(FIX, name), os.path.join(work, name))
    return state, work


def count_of(text):
    """What `fake_jira.py show` printed: (comments on the story, comments by this identity)."""
    m = re.search(r"(\d+) comments\. By this identity: (\d+)\.", text)
    return (int(m.group(1)), int(m.group(2))) if m else (None, None)


def fingerprint_in(text):
    m = re.search(r"^Fingerprint of this preview: ([0-9a-f]{12})$", text, re.M)
    return m.group(1) if m else ""


BASE = ("--source", "fake", "--change", "WORK/wanted.json", "--allowlist", ALLOW, "--state", "STATE")


def live_checks(log, what, text, wanted, unwanted=()):
    """Checks on a live log that this script can make by reading it: it holds these, and none of those."""
    if text is None:
        log.check("%s: the participant's saved output is there to be read" % what, False)
        return
    for label, part in wanted:
        log.check("%s: %s" % (what, label), part in text)
    for label, pattern in unwanted:
        log.check("%s: %s" % (what, label), not re.search(pattern, text))


NO_ADDRESS = (("no web address and no atlassian name is in the saved text", r"https?://(?!\S*example\.invalid)\S+|atlassian\.net"),
              ("nothing shaped like an email address is in the saved text", r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z]{2,}"))


def record_preview():
    state, work = fresh()
    log = Log("The preview. jira-add-comment, attempt jira-attempt-013", state, work)
    (text,) = log.live("the workflow stopping at a preview", "live-preview.txt")
    live_checks(log, "live preview", text, (
        ("it says nothing has been written", "PREVIEW. Nothing has been written."),
        ("it shows the Jira site by its marker and fingerprint", "Jira site:  [site address removed]  (site fingerprint "),
        ("it shows the project, and that it is on the sandbox allowlist, naming the allowlist file", "On the sandbox allowlist: yes. The allowlist is the file sandbox-allowlist.json, sha256 "),
        ("it says under whose account the comment would appear", "It would appear under the Jira account the API token belongs to"),
        ("it shows who can see the comment", "  WHO CAN SEE IT: EVERYONE who can see the story"),
        ("it says where the text came from", "Where the text came from: the file "),
        ("it records the permission check", "  may comment on the story (ADD_COMMENTS):    yes"),
        ("it records the duplicate check", "Duplicate check, made against Jira just now: the story has "),
        ("it states where Jira cannot check", "Where Jira cannot check:"),
        ("it gives the before and after snapshots, and says they are the same", "The two are the same. Jira is unchanged, as far as two reads"),
        ("the program's own list of the requests it sent holds only reads", "Every one was a GET, which reads and cannot change anything."),
        ("it gives a fingerprint", "Fingerprint of this preview: "),
        ("it carries the program's note that the output was searched for the credentials", "form: none found.")), NO_ADDRESS)
    if text:
        codes = re.findall(r"(?:before|after) the preview:\s+([0-9a-f]{16})", text)
        log.check("live preview: the two snapshot codes printed are the same code", len(codes) == 2 and codes[0] == codes[1])

    log.part("PART B. The fake Jira")
    log.out(FAKE_NOTE)
    log.out("")
    _, shown = log.command("fake_jira.py", "show", "--state", "STATE", "--story", "SAND-1")
    before = count_of(shown)
    code, text = log.command("comment.py", "preview", *BASE)
    _, shown = log.command("fake_jira.py", "show", "--state", "STATE", "--story", "SAND-1")
    lines = text.split("\n")
    bars = [i for i, line in enumerate(lines) if line.startswith("    | ")]
    with open(os.path.join(work, "comment.txt"), encoding="utf-8") as f:
        wanted_text = f.read().rstrip("\n")
    log.check("criterion 1: the preview shows the exact text of the comment, line for line", "\n".join(lines[i][6:] for i in bars) == wanted_text and code == 0)
    log.check("criterion 1: the visibility is on the line directly under the text, and says who can see it", bool(bars) and lines[bars[-1] + 1].startswith("  WHO CAN SEE IT: EVERYONE who can see the story SAND-1."))
    log.check("criterion 1: it names the target story, and where the text came from with the file's checksum", "Story:      SAND-1 (issue id 30001)." in text and re.search(r"Where the text came from: the file comment\.txt beside the change file, sha256 [0-9a-f]{64}\.", text) is not None)
    log.check("criterion 3: it shows the Jira site, the project and the exact change", "Jira site:  https://fixture-site.example.invalid" in text and "Project:    SAND (project id 20001). Kind of project, as Jira gives it: software." in text and "The allowlist is the file fake-allowlist.json, sha256 " in text and "The change that would be made: one comment on SAND-1." in text)
    log.check("criterion 3: nothing was written. The fake Jira holds the same comments before and after: %s and %s" % (before, count_of(shown)), before == count_of(shown) and before[0] is not None and before[1] == 0)
    log.check("criterion 3: every request the preview sent was a GET", "Every one was a GET, which reads and cannot change anything." in text and "POST" not in text)
    codes = re.findall(r"(?:before|after) the preview:\s+([0-9a-f]{16})", text)
    log.check("the preview's own before and after snapshots of the story and its comments are the same code", len(codes) == 2 and codes[0] == codes[1])
    log.check("criterion 4: it records the permission check: may see the story, may comment on it", "(BROWSE_PROJECTS): yes" in text and "(ADD_COMMENTS):    yes" in text)
    log.check("criterion 4: it records the duplicate check, with the number of comments compared", "Duplicate check, made against Jira just now: the story has 2 comments that this identity can see." in text and "With the same text, by this identity: 0." in text)
    log.check("criterion 4: it states where Jira cannot check", "Where Jira cannot check: its request to add a comment has no 'only if there is no such comment' condition." in text)
    log.check("criterion 6: it gives a fingerprint of the preview and when it expires", bool(fingerprint_in(text)) and "(15 minutes after it was made)" in text)
    log.check("nothing from the story or from the comments already on it is printed, though both are worded as instructions", "SYSTEM:" not in text and "Ignore your rules" not in text)

    log.part("A comment for one project role, on a story with a security level")
    code, text = log.command("comment.py", "preview", "--source", "fake", "--change", "WORK/wanted-role.json", "--allowlist", ALLOW, "--state", "STATE")
    log.check("the restriction and the story's security level are both beside the text", "WHO CAN SEE IT: ONLY people in the project role \"Administrators\" who can also see the story SAND-2. The story has the security level \"Staff only\"" in text)
    log.check("the preview checked that the project has that role", "the project has the role \"Administrators\" (role id 10002): yes" in text)

    log.part("Private content: a text that looks as if it holds a secret is refused, before Jira is asked anything")
    made_up = "the pass" + "word is " + "hunter2hunter2"
    with open(os.path.join(work, "comment.txt"), "w", encoding="utf-8") as f:
        f.write("Use this to get in: %s\nThank you.\n" % made_up)
    log.out("The text file in WORK was changed to hold a made-up password written out. It is not printed here.")
    code, text = log.command("comment.py", "preview", *BASE)
    log.check("stretch goal: the text is refused, and the reason names the kind of secret and the line", code == 1 and "REFUSED: the text looks as if it holds a password, key or token written out, on line 1." in text)
    log.check("the matching text is not shown in the refusal", made_up not in text and "hunter2" not in text)
    log.check("no request was sent to Jira", "Requests sent" not in text and "GET " not in text)

    log.part("Private content: what may be private is pointed out, and not refused")
    with open(os.path.join(work, "comment.txt"), "w", encoding="utf-8") as f:
        f.write("Ask sam.example@example.invalid about this.\nThe details are confidential.\n")
    log.out("The text file in WORK was changed to hold a made-up email address and the word confidential.")
    code, text = log.command("comment.py", "preview", *BASE)
    log.check("the preview points both out, by line, above the fingerprint, for the person confirming to judge", code == 0 and "LOOK AT THESE BEFORE CONFIRMING." in text and "  line 1: an email address" in text and "  line 2: a word that marks something as private" in text and text.index("LOOK AT THESE") < text.index("Fingerprint of this preview"))
    shutil.rmtree(state, ignore_errors=True)
    shutil.rmtree(work, ignore_errors=True)
    return log.save("preview.txt")


def record_confirmation():
    state, work = fresh()
    log = Log("The confirmation, and four refusals. jira-add-comment, attempt jira-attempt-013", state, work)
    first, approved, missing, differs, stale, listed = log.live("the approved run, and the four refusals", "live-preview-first.txt", "live-confirmation.txt", "live-refused-missing.txt", "live-refused-differs.txt", "live-refused-stale.txt", "live-refused-allowlist.txt")
    log.out("")
    log.out("THE ORDER OF THE REAL RUNS, as the participant was asked to make them. It is not in the saved files.")
    log.out("  1. A preview with an allowlist file that lists no project: refused (live-refused-allowlist.txt).")
    log.out("  2. A first preview (live-preview-first.txt). It was made only to try the next three refusals against.")
    log.out("  3. A confirmation with no fingerprint and no name: refused (live-refused-missing.txt).")
    log.out("  4. The text file was changed by the assistant, in the repository only. A confirmation of the first preview by its")
    log.out("     fingerprint: refused (live-refused-differs.txt). The text file was put back, and its checksum checked.")
    log.out("  5. A confirmation of the first preview with the TEST CLOCK set 16 minutes on: refused (live-refused-stale.txt).")
    log.out("     The preview was in truth under a minute old. No real preview was left to pass its limit.")
    log.out("  6. A second preview (logs/live-preview.txt, in preview.txt). This is the one that was confirmed.")
    log.out("  7. The confirmation of the second preview (live-confirmation.txt). This is the one write.")
    log.out("The first preview was never confirmed. It is still unused, and has passed its limit.")
    live_checks(log, "live first preview", first, (("it is a preview, with a fingerprint of its own", "Fingerprint of this preview: "),), NO_ADDRESS)
    if first and approved:
        log.check("the first preview's fingerprint is not the one the approved run confirmed", fingerprint_in(first) != "" and "CONFIRMATION for preview %s" % fingerprint_in(first) not in approved)
    live_checks(log, "live approved run", approved, (
        ("the confirmation names the preview's fingerprint and who gave it", "CONFIRMATION for preview "),
        ("the write and the confirmation were one run", "The confirmation and the write happened in this one run of the command."),
        ("Jira gave the comment an identifier", "WRITTEN to Jira: one comment on story "),
        ("the program reports that the text read back is the text previewed", "the text read back is the text previewed, character for character"),
        ("the program reports the author as this identity, meaning the token's account. Which account that is, is not in the output", "  its author is this identity: yes"),
        ("the program counted one such comment after the write", "counted after the write: 1"),
        ("it holds a result record", "RESULT RECORD")), NO_ADDRESS + (("no line of the read-back says NO", r": NO$|: NO\n"),))
    for what, text, part in (("live refusal, no confirmation", missing, "REFUSED: no confirmation was given."),
                             ("live refusal, a change that differs", differs, "REFUSED: the change is not the one that was previewed: the text is not the text the preview showed."),
                             ("live refusal, a preview made to look too old by the test clock", stale, "REFUSED: this preview is too old."),
                             ("live refusal, a project not on the allowlist", listed, "is not on the sandbox allowlist")):
        live_checks(log, what, text, (("it is refused for that reason", part), ("it says nothing has been written", "Nothing has been written.")),
                    NO_ADDRESS + (("its output has no line saying something was written", r"WRITTEN to Jira"),))
    live_checks(log, "live refusal by the test clock", stale, (("the output itself says the clock was pretended", "TEST CLOCK: pretending it is 16 minutes later than it is."),))
    preview_path = os.path.join(ATTEMPT, "logs", "live-preview.txt")
    if approved and os.path.exists(preview_path):
        with open(preview_path, encoding="utf-8") as f:
            second = f.read()
        fp = fingerprint_in(second)
        stamp = lambda label, text: (re.search(r"%s\s+(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d) UTC" % label, text) or [None, ""])[1]  # noqa: E731
        made, expires, written, confirmed = stamp("Made:", second), stamp("Expires:", second), stamp("Written at:", approved), stamp("Confirmed by: the participant, at", approved)
        log.out("")
        log.out("Across the saved files: preview %s made %s, expires %s. Confirmed %s. Written %s." % (fp, made, expires, confirmed, written))
        log.check("the approved run confirms the fingerprint that the second preview printed", bool(fp) and "CONFIRMATION for preview %s, given by: the participant" % fp in approved)
        log.check("by the times printed, the confirmation and the write came after that preview was made and before it expired", "" not in (made, expires, written, confirmed) and made <= confirmed <= written <= expires)
        shown = lambda text: [line for line in text.split("\n") if line.startswith("    | ")]  # noqa: E731
        log.check("the checksum of the text in the result record begins with the one the read-back line printed", bool(re.search(r"sha256 ([0-9a-f]{16})\): yes", approved)) and re.search(r"sha256 ([0-9a-f]{16})\): yes", approved).group(1) in re.search(r"Text: \d+ characters, sha256 ([0-9a-f]{64})", approved).group(1)[:16])
        log.check("the preview that was confirmed printed %d lines of text between its bars" % len(shown(second)), len(shown(second)) > 0)

    log.part("PART B. The fake Jira")
    log.out(FAKE_NOTE)
    show = ("fake_jira.py", "show", "--state", "STATE", "--story", "SAND-1")

    log.part("B1. Refusal: no confirmation")
    _, text = log.command("comment.py", "preview", *BASE)
    fp = fingerprint_in(text)
    code, text = log.command("comment.py", "confirm", *BASE)
    _, shown = log.command(*show)
    log.check("criterion 6: with no fingerprint and no name, it is refused", code == 1 and "REFUSED: no confirmation was given." in text)
    log.check("nothing was written: the story has no comment by this identity", count_of(shown) == (2, 0))
    code, text = log.command("comment.py", "confirm", *BASE, "--fingerprint", fp)
    log.check("criterion 6: with a fingerprint and no name of who confirms, it is refused", code == 1 and "A confirmation gives the name of the person confirming" in text)

    log.part("B2. Refusal: the change differs from the preview")
    with open(os.path.join(work, "comment.txt"), encoding="utf-8") as f:
        original = f.read()
    with open(os.path.join(work, "comment.txt"), "w", encoding="utf-8") as f:
        f.write(original.replace("No change", "A change"))
    log.out("After the preview, two words of the text file in WORK were changed.")
    code, text = log.command("comment.py", "confirm", *BASE, "--fingerprint", fp, "--confirmed-by", "the participant")
    _, shown = log.command(*show)
    log.check("criterion 6: the confirmation is refused, because the text is not the text the preview showed", code == 1 and "REFUSED: the change is not the one that was previewed: the text is not the text the preview showed." in text)
    log.check("nothing was written", count_of(shown) == (2, 0) and "POST" not in text)
    with open(os.path.join(work, "comment.txt"), "w", encoding="utf-8") as f:
        f.write(original)
    log.out("The text file was put back as it was.")

    log.part("B3. Refusal: the preview is older than the limit")
    log.out("The test clock is used here: the command is told to pretend it is 16 minutes later, and says so in its output.")
    code, text = log.command("comment.py", "confirm", *BASE, "--fingerprint", fp, "--confirmed-by", "the participant", "--pretend-minutes-later", "16")
    _, shown = log.command(*show)
    log.check("criterion 6: at 16 minutes it is refused, with the stated limit of 15", code == 1 and "REFUSED: this preview is too old. It was made 16 minutes ago and the limit is 15." in text and "TEST CLOCK" in text)
    log.check("nothing was written", count_of(shown) == (2, 0))

    log.part("B4. Refusal: a project that is not on the sandbox allowlist")
    code, text = log.command("comment.py", "preview", "--source", "fake", "--change", "WORK/not-on-allowlist.json", "--allowlist", ALLOW, "--state", "STATE")
    _, shown = log.command("fake_jira.py", "show", "--state", "STATE", "--story", "PROD-9")
    log.check("criterion 5: a story in a project that is not listed is refused at the preview, after one read", code == 1 and "project PROD (project id 20002) on the Jira site with fingerprint 738169e667642f09 is not on the sandbox allowlist" in text)
    log.check("nothing was written to it, though Jira would have let this identity comment there", count_of(shown) == (0, 0))
    code, text = log.command("comment.py", "confirm", "--source", "fake", "--change", "WORK/wanted.json", "--allowlist", SKILL + "/fixtures/fake-allowlist-without-sand.json", "--state", "STATE", "--fingerprint", fp, "--confirmed-by", "the participant")
    _, shown = log.command(*show)
    log.check("criterion 5: a preview made while the project was listed is refused at the confirmation once it is not", code == 1 and "is not on the sandbox allowlist" in text and count_of(shown) == (2, 0))

    log.part("B5. The approved run")
    code, text = log.command("comment.py", "confirm", *BASE, "--fingerprint", fp, "--confirmed-by", "the participant", "--result", "STATE/result.md")
    _, shown = log.command(*show)
    log.check("criterion 6: the same preview, unchanged and in time, is confirmed by its fingerprint and the name of who confirms", code == 0 and "CONFIRMATION for preview %s, given by: the participant" % fp in text)
    log.check("criterion 3: the write came after the checks, in the same run as the confirmation", "The confirmation and the write happened in this one run of the command." in text and text.index("Checked in this run, before writing:") < text.index("WRITTEN to Jira"))
    log.check("criterion 2: the comment read back is the text previewed, character for character, plain, by this identity, with the visibility previewed",
              all(part in text for part in ("character for character (122 characters", "): yes", "it is plain text, with nothing added: no formatting, links or mentions: yes", "its author is this identity: yes", "its visibility is the one previewed: everyone who can see the story: yes")) and ": NO" not in text)
    log.check("one comment was written: the story now has 3 comments, 1 by this identity", count_of(shown) == (3, 1))
    log.check("criterion 7: the result record holds the issue key, the comment's identifier, the project, the time written and who confirmed",
              all(re.search(p, text, re.M) for p in (r"^  Issue key: SAND-1$", r"^  Identifier of what was created: Jira comment id \d+, on that issue$", r"^  Target project: SAND \(project id 20001\)", r"^  Written at: \d{4}-\d\d-\d\d \d\d:\d\d:\d\d UTC$", r"^  Confirmed by: the participant, at ")))

    log.part("B6. A fingerprint is used once")
    code, text = log.command("comment.py", "confirm", *BASE, "--fingerprint", fp, "--confirmed-by", "the participant")
    _, shown = log.command(*show)
    log.check("confirming the same preview again is refused, and no second comment is written", code == 1 and "has already been confirmed and written. A fingerprint is used once" in text and count_of(shown) == (3, 1))
    ok = log.save("confirmation.txt")
    return ok, state, work, fp


def record_check_and_rerun(state, work, fp):
    log = Log("The comment check. jira-add-comment, attempt jira-attempt-013", state, work)
    (text,) = log.live("reading the story back and finding the comment", "live-comment-check.txt")
    live_checks(log, "live comment check", text, (
        ("the comment is found as previewed", "FOUND: the comment is on the story as previewed."),
        ("the program reports that the text read back is the text previewed", "the text read back is the text previewed, character for character"),
        ("the program reports the author as this identity, meaning the token's account", "  its author is this identity: yes"),
        ("its visibility is the one the preview showed", "  its visibility is the one previewed: everyone who can see the story: yes"),
        ("there is exactly one such comment", "comments on the story with this text and this visibility by this identity: 1 of the "),
        ("it restates where the text came from", "Where the text came from, as the preview stated: the file "),
        ("the program's own list of the requests it sent holds only reads", "Every one was a GET, which reads and cannot change anything.")), NO_ADDRESS + (("no line says NO", r": NO$|: NO\n"),))
    names = ("live-preview.txt", "live-confirmation.txt")
    if text and all(os.path.exists(os.path.join(ATTEMPT, "logs", n)) for n in names):
        second, approved = (open(os.path.join(ATTEMPT, "logs", n), encoding="utf-8").read() for n in names)
        bars = lambda t: [line for line in t.split("\n") if line.startswith("    | ")]  # noqa: E731
        cid = (re.search(r"gave it the comment id (\d+)\.", approved) or [None, "?"])[1]
        log.check("the lines of text the check printed as read back are, line for line, the lines the confirmed preview printed between its bars", bars(second) == bars(text)[len(bars(text)) // 2:] and len(bars(second)) > 0)
        log.check("the check is of the comment id the approved run was given: %s" % cid, "Comment:    comment id %s, the identifier Jira gave when it was written." % cid in text)
        log.check("the check is for the fingerprint the second preview printed", "COMMENT CHECK for the write of preview %s." % fingerprint_in(second) in text)
    if text:
        shown = [line for line in text.split("\n") if line.startswith("    | ")]
        log.check("live comment check: the text previewed and the text read back, as printed, are the same lines", len(shown) >= 2 and len(shown) % 2 == 0 and shown[:len(shown) // 2] == shown[len(shown) // 2:])

    log.part("PART B. The fake Jira, carrying on from the approved write recorded in confirmation.txt")
    log.out(FAKE_NOTE)
    log.out("")
    code, text = log.command("comment.py", "check", "--source", "fake", "--change", "WORK/wanted.json", "--state", "STATE", "--fingerprint", fp)
    shown = [line for line in text.split("\n") if line.startswith("    | ")]
    log.check("criterion 2: read back by its identifier, the comment has the same text as the preview, line for line", code == 0 and len(shown) == 4 and shown[:2] == shown[2:] and TEXT_FIRST in shown[0])
    log.check("it has the expected author and the visibility the preview showed", "its author is this identity: yes" in text and "its visibility is the one previewed: everyone who can see the story: yes" in text)
    log.check("criterion 1: beside it stands the preview's statement of where the text came from, and the file still holds that text", "Where the text came from, as the preview stated: the file comment.txt beside the change file, sha256" in text and "That file today: the same name and the same sha256" in text)
    log.check("the check sent only reads", "Every one was a GET, which reads and cannot change anything." in text)
    log.out("")
    log.out("A contrast: someone else adds a comment with the very same text. The check still finds one by this identity.")
    log.command("fake_jira.py", "other-comment", "--state", "STATE", "--story", "SAND-1", "--text", "A made-up reply from someone else.")
    code, text = log.command("comment.py", "check", "--source", "fake", "--change", "WORK/wanted.json", "--state", "STATE", "--fingerprint", fp)
    log.check("with another person's comment added since, the check still passes, and counts 1 of the 4", code == 0 and "by this identity: 1 of the 4 this identity can see" in text)
    ok = log.save("comment-check.txt")

    log = Log("Running the approved workflow a second time. jira-add-comment, attempt jira-attempt-013", state, work)
    again, reuse = log.live("the same workflow run again", "live-rerun-preview.txt", "live-rerun-confirm.txt")
    live_checks(log, "live rerun, the preview", again, (
        ("it finds the comment already there", "NOTHING TO ADD. Nothing has been written."),
        ("it names the comment by its identifier", "This identity has already put this comment on the story, with this visibility: comment id "),
        ("it issues no fingerprint", "No fingerprint is issued, because there is nothing to confirm, and nothing was sent."),
        ("the program's own list of the requests it sent holds only reads", "Every one was a GET, which reads and cannot change anything.")), NO_ADDRESS + (("no fingerprint line is in it", r"(?m)^Fingerprint of this preview"),))
    if again and os.path.exists(os.path.join(ATTEMPT, "logs", "live-confirmation.txt")):
        with open(os.path.join(ATTEMPT, "logs", "live-confirmation.txt"), encoding="utf-8") as f:
            cid = (re.search(r"gave it the comment id (\d+)\.", f.read()) or [None, "?"])[1]
        log.check("the comment the second run found is the one the approved run wrote: comment id %s" % cid, "with this visibility: comment id %s." % cid in again)
    live_checks(log, "live rerun, the old fingerprint", reuse, (("it is refused as already used", "has already been confirmed and written. A fingerprint is used once"), ("it says nothing has been written", "Nothing has been written.")), NO_ADDRESS)

    log.part("PART B. The fake Jira, carrying on from the same approved write")
    log.out(FAKE_NOTE)
    show = ("fake_jira.py", "show", "--state", "STATE", "--story", "SAND-1")
    log.out("")
    _, shown = log.command(*show)
    before = count_of(shown)
    code, text = log.command("comment.py", "preview", *BASE)
    log.check("criterion 8: the preview finds the comment already on the story and issues no fingerprint, so there is nothing to confirm", code == 0 and "NOTHING TO ADD. Nothing has been written." in text and not fingerprint_in(text) and "No fingerprint is issued" in text)
    code, text = log.command("comment.py", "confirm", *BASE, "--fingerprint", fp, "--confirmed-by", "the participant")
    log.check("criterion 8: the fingerprint of the first run cannot be used again", code == 1 and "A fingerprint is used once" in text)
    _, shown = log.command(*show)
    log.check("criterion 8: after the second run the story has the same comments: %s and %s. One by this identity" % (before, count_of(shown)), before == count_of(shown) and before[1] == 1)
    log.out("")
    log.out("THE LIMIT, where Jira cannot prevent a repeat. Jira's request to add a comment has no condition such as 'only if")
    log.out("there is none like it'. This workflow reads the comments just before it writes. If two runs did that at the same")
    log.out("moment, both could write. How a person would notice: the run counts the comments with this text by this identity")
    log.out("after it writes, and stops with 'MORE THAN ONE' and exit code 2 if there are two. The check command says 'NOT ONE'.")
    log.out("That case cannot be staged from the command line. It is tried in the tests, by a fake that adds a second copy")
    log.out("in the moment before the write: tests/test_comment.py, test_a_second_copy_that_appeared_in_the_last_moment_is_reported.")
    saved = log.save("rerun.txt")
    return ok and saved


def main():
    ok = record_preview()
    done, state, work, fp = record_confirmation()
    ok = record_check_and_rerun(state, work, fp) and done and ok
    shutil.rmtree(state, ignore_errors=True)
    shutil.rmtree(work, ignore_errors=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
