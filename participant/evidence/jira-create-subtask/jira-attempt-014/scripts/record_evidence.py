#!/usr/bin/env python3
"""Records logs/preview.txt, confirmation.txt, parent-check.txt and rerun.txt for the quest jira-create-subtask.

Each record has two parts.

  PART A is the participant's own run against their real Jira sandbox. This script does not make that run and
  cannot: it has no credentials and contacts nothing. The participant ran the commands in their own terminal, and
  the workflow saved what it printed, with the site's address and the parent's title removed, in logs/ under names
  starting live-. This script copies those files in unchanged. Where one is not there yet, PART A says so.

  PART B is recorded here, against participant/skills/jira-create-subtask/fake_jira.py, a made-up Jira. No network
  is used. Each run is the real command, started as a person would start it, and what it printed is written down.
  It shows the refusals and the cases that would be unsafe or impossible to stage on a real site.

The fake Jira keeps its state in a temporary folder, shown as STATE. The change files are written to another, shown
as WORK. Both are deleted at the end.

Run from anywhere:  python3 scripts/record_evidence.py
Exit code 0 if every check came out as expected, 1 if not.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ATTEMPT = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(ATTEMPT, "..", "..", "..", ".."))
SKILL = "participant/skills/jira-create-subtask"
ALLOW = SKILL + "/fixtures/fake-allowlist.json"
HEAD = ("Recorded by scripts/record_evidence.py. Each block between dashed lines is what a command printed.\n"
        "STATE and WORK stand for temporary folders. WORK holds the change files.")
FAKE_NOTE = ("The Jira in this part is fake_jira.py, a made-up one. No real Jira was read or written, so nothing in it is\n"
             "redacted: the site, the projects and the stories are invented.")
TITLE = "Add a column for the export date"


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
    state, work = tempfile.mkdtemp(prefix="gtq-subtask-state-"), tempfile.mkdtemp(prefix="gtq-subtask-work-")
    changes = {"wanted": ("SAND-1", TITLE), "missing": ("SAND-999", TITLE), "subtask-parent": ("SAND-4", TITLE), "closed": ("SAND-3", TITLE),
               "by-title": ("Export the monthly report", TITLE), "twin": ("SAND-2", TITLE), "production": ("PROD-9", TITLE)}
    for name, (parent, summary) in changes.items():
        with open(os.path.join(work, name + ".json"), "w", encoding="utf-8") as f:
            json.dump({"parent": parent, "summary": summary}, f, indent=2)
            f.write("\n")
    return state, work


def held(text):
    """What `fake_jira.py show` printed: (subtasks of the issue, issues in all)."""
    m = re.search(r"(\d+) subtasks?(?:: [^.]*)?\. Issues in all: (\d+)\.", text)
    return (int(m.group(1)), int(m.group(2))) if m else (None, None)


def fingerprint_in(text):
    m = re.search(r"^Fingerprint of this preview: ([0-9a-f]{12})$", text or "", re.M)
    return m.group(1) if m else ""


def found(pattern, text):
    m = re.search(pattern, text or "", re.M)
    return m.group(1) if m else None


def base(change="wanted"):
    return ("--source", "fake", "--change", "WORK/%s.json" % change, "--allowlist", ALLOW, "--state", "STATE")


NO_ADDRESS = (("no web address and no atlassian name is in the saved text", r"https?://(?!\S*example\.invalid)\S+|atlassian\.net"),
              ("nothing shaped like an email address is in the saved text", r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z]{2,}"),
              ("no account identifier is in the saved text: nothing named accountId, and no run of exactly 24 hex characters", r"accountId|(?<![0-9a-f])[0-9a-f]{24}(?![0-9a-f])|\b[0-9]{6}:[0-9a-f-]{36}"))


def live_checks(log, what, text, wanted, unwanted=NO_ADDRESS):
    """Checks on a live log that this script can make by reading it: it holds these, and none of those."""
    if text is None:
        log.check("%s: the participant's saved output is there to be read" % what, False)
        return
    for label, part in wanted:
        log.check("%s: %s" % (what, label), bool(part.search(text)) if hasattr(part, "search") else part in text)
    for label, pattern in unwanted:
        log.check("%s: %s" % (what, label), not re.search(pattern, text))


def refusal(log, what, text, reason):
    live_checks(log, what, text, (("it is refused for that reason", reason),
                                  ("the line after the refusal says nothing has been written", re.compile(r"^REFUSED: .*\nNothing has been written\.$", re.M))))
    if text is not None:
        log.check("%s: it has no line saying something was written to Jira, and no fingerprint" % what, "WRITTEN to Jira" not in text and "Fingerprint of this preview" not in text)


def show(log, issue="SAND-1"):
    return held(log.command("fake_jira.py", "show", "--state", "STATE", "--issue", issue)[1])


# ---------------------------------------------------------------- preview.txt


def record_preview():
    state, work = fresh()
    log = Log("The preview. jira-create-subtask, attempt jira-attempt-014", state, work)
    (text,) = log.live("the workflow stopping at a preview", "live-preview.txt")
    live_checks(log, "live preview", text, (
        ("it says it is a preview and that nothing has been written", "PREVIEW. Nothing has been written."),
        ("it shows the Jira site as a marker and a fingerprint", "Jira site:  [site address removed]  (site fingerprint "),
        ("it shows the project by key and id, and that it is on the allowlist", re.compile(r"^Project:    \S+ \(project id \d+\)\. On the sandbox allowlist: yes\.", re.M)),
        ("it shows the parent with its key and its issue id", re.compile(r"^Parent:     \S+ \(issue id \d+\)\.", re.M)),
        ("it says the parent was found by the reference and not by its title", "and by nothing else. Not by its title."),
        ("it says the parent is not a subtask", "Not a subtask: ok."),
        ("it says the parent is not closed", "Not closed: ok."),
        ("the parent's title is left out of what was saved", "[the parent's title was shown on screen and is not saved:"),
        ("it lists what would be sent as four fields: a project, a parent, an issue type and a summary", re.compile(r"Sent to Jira, and nothing else:\n    project     project id \d+ .*\n    parent      issue id \d+ .*\n    issue type  .*\n    summary     .*\n    \| .+\n  No description", re.M)),
        ("it records the permission check", "(CREATE_ISSUES):   yes"),
        ("it records the duplicate check", "With the same title, under this parent: 0."),
        ("it states where Jira cannot check", "Where Jira cannot check:"),
        ("the program reports that every request was a read", "Every one was a GET, which reads and cannot change anything."),
        ("it has a fingerprint of 12 characters, and an expiry", re.compile(r"^Fingerprint of this preview: [0-9a-f]{12}\nMade:    .* UTC\nExpires: .* UTC \(15 minutes after it was made\)$", re.M)),
        ("it carries the program's note that the output was searched for the credentials", "form: none found.")))
    if text:
        codes = re.findall(r"(?:before|after) the preview:\s+([0-9a-f]{16})", text)
        log.check("live preview: the two snapshot codes printed are the same code", len(codes) == 2 and codes[0] == codes[1])
        log.check("live preview: no line of it says something was written to Jira", "WRITTEN to Jira" not in text)
        listed = re.findall(r"^  (GET|POST|PUT|DELETE|PATCH) /", text, re.M)
        said = found(r"^Requests sent to Jira: (\d+)\.", text)
        log.check("live preview: it says it sent %s requests, it lists %d, and each listed is a GET" % (said, len(listed)), said == str(len(listed)) and len(listed) > 0 and set(listed) == {"GET"})

    log.part("PART B. The same preview against the made-up Jira")
    log.out(FAKE_NOTE)
    log.out("")
    log.out("What the made-up Jira holds for SAND-1 before the preview:")
    before = show(log)
    log.out("")
    code, out = log.command("subtask.py", "preview", *base(), "--log", "STATE/preview-saved.txt")
    fp = fingerprint_in(out)
    log.out("")
    log.out("What the made-up Jira holds for SAND-1 after the preview:")
    after = show(log)
    log.check("criterion 4: the preview shows the site, the project and the exact changes", code == 0 and all(part in out for part in (
        "Jira site:  https://fixture-site.example.invalid", "Project:    SAND (project id 20001)", "parent      issue id 30001 (SAND-1)", "    | " + TITLE)))
    log.check("criterion 4: nothing was written: the made-up Jira holds %s subtask of SAND-1 and %s issues, before and after" % before, before == after == (1, 7))
    log.check("criterion 5: the permission check and the duplicate check are in the preview, with what Jira cannot check",
              "(CREATE_ISSUES):   yes" in out and "With the same title, under this parent: 0." in out and "Where Jira cannot check" in out)
    log.check("criterion 7: the preview has a fingerprint of 12 characters and says when it expires", len(fp) == 12 and "15 minutes after it was made" in out)
    log.check("criterion 1: the preview says how the parent was found, and gives its issue id", 'the reference in the change file, "SAND-1", and by nothing else' in out and "Parent:     SAND-1 (issue id 30001)" in out)
    with open(os.path.join(state, "preview-saved.txt"), encoding="utf-8") as f:
        saved = f.read()
    log.check("what --log saved has a marker where the site was, and not the parent's title", "fixture-site" not in saved and "[site address removed]" in saved and "Export the monthly report" not in saved)
    log.out("")
    log.out("A preview of a subtask the parent already has. Someone else creates it first:")
    log.command("fake_jira.py", "other-subtask", "--state", "STATE", "--parent", "SAND-1", "--summary", TITLE.upper())
    code, out = log.command("subtask.py", "preview", *base())
    log.check("criterion 5: a subtask with this title already under the parent, in other capitals, gives no fingerprint", code == 0 and "NOTHING TO ADD" in out and not fingerprint_in(out))
    shutil.rmtree(state, ignore_errors=True)
    shutil.rmtree(work, ignore_errors=True)
    return log.save("preview.txt")


# ---------------------------------------------------------------- confirmation.txt


def record_confirmation():
    state, work = fresh()
    log = Log("The confirmation, and the refusals. jira-create-subtask, attempt jira-attempt-014", state, work)
    first, approved, missing, differs, stale, listed = log.live(
        "the approved run, and the four refusals", "live-preview-first.txt", "live-confirmation.txt", "live-refused-missing.txt",
        "live-refused-differs.txt", "live-refused-stale.txt", "live-refused-allowlist.txt")
    log.out("")
    log.out("The order of the real runs, as the participant was asked to make them:")
    log.out("  1. A preview naming a parent that does not exist: refused (live-refused-missing-parent.txt, in parent-check.txt).")
    log.out("  2. A preview with an allowlist file that lists no project: refused (live-refused-allowlist.txt).")
    log.out("  3. A first preview (live-preview-first.txt). It was made only to try the next three refusals against.")
    log.out("  4. A confirmation with no fingerprint and no name: refused (live-refused-missing.txt).")
    log.out("  5. A confirmation of the first preview's fingerprint with a change file whose title had been altered:")
    log.out("     refused (live-refused-differs.txt).")
    log.out("  6. A confirmation of the first preview with the TEST CLOCK set 16 minutes on: refused (live-refused-stale.txt).")
    log.out("     The preview was not 16 minutes old. The program was told to act as if it were.")
    log.out("  7. A second preview (live-preview.txt, in preview.txt). This is the one that was confirmed.")
    log.out("  8. The confirmation of the second preview (live-confirmation.txt). This is the one write.")
    log.out("  9. The parent check, the second run, and a preview naming the new subtask as a parent (in parent-check.txt")
    log.out("     and rerun.txt).")
    log.out("")
    live_checks(log, "live first preview", first, (("it is a preview, with a fingerprint of its own", "Fingerprint of this preview: "),))
    live_checks(log, "live approved run", approved, (
        ("the confirmation names a fingerprint and gives a name for who gave it", re.compile(r"^CONFIRMATION for preview [0-9a-f]{12}, given by: \S", re.M)),
        ("the program reports that the confirmation and the write happened in one run", "The confirmation and the write happened in this one run of the command."),
        ("it reports one subtask written", "WRITTEN to Jira: one subtask, "),
        ("the parent read back is reported as the parent intended", "They are the same: yes"),
        ("it holds a result record", "RESULT RECORD"),
        ("the result record names who confirmed", "Confirmed by: ")))
    refusal(log, "live refusal, no confirmation", missing, "REFUSED: no confirmation was given.")
    refusal(log, "live refusal, a change that differs", differs, "REFUSED: the change is not the one that was previewed: the title is not the title the preview showed")
    refusal(log, "live refusal, a preview made to look too old by the test clock", stale, "REFUSED: this preview is too old.")
    refusal(log, "live refusal, a project not on the allowlist", listed, "is not on the sandbox allowlist")
    live_checks(log, "live refusal by the test clock", stale, (("the output itself says the clock was pretended", "TEST CLOCK: pretending it is 16 minutes later than it is."),), ())
    preview_path = os.path.join(ATTEMPT, "logs", "live-preview.txt")
    preview = open(preview_path, encoding="utf-8").read() if os.path.exists(preview_path) else None
    if approved and preview:
        fp_live = fingerprint_in(preview)
        log.check("live: the fingerprint confirmed (%s) is the fingerprint of the saved preview" % fp_live, bool(fp_live) and "CONFIRMATION for preview %s," % fp_live in approved)
        log.check("live: it is not the fingerprint of the first preview, which was only refused against", bool(first) and fingerprint_in(first) not in ("", fp_live))
        parent = found(r"^Parent:     (\S+ \(issue id \d+\))", preview)
        log.check("live: the parent in the confirmation is the parent in the preview: %s" % parent, bool(parent) and "Parent:     %s" % parent in approved)
        title = found(r"^    summary .*\n    \| (.*)$", preview)
        made, expires, written = found(r"^Made:    (.*)$", preview), found(r"^Expires: (.*)$", preview), found(r"Written at: (.*)$", approved)
        log.check("live: the write (%s) is after the preview was made (%s) and before it expired (%s)" % (written, made, expires), bool(made and written and expires) and made[:23] <= written[:23] <= expires[:23])
        log.check("live: the title's checksum in the result record is the checksum of the title the preview showed",
                  bool(title) and "sha256 %s" % hashlib.sha256(title.encode("utf-8")).hexdigest() in approved)
        result_path = os.path.join(ROOT, "participant", "context", "jira", "results", "create-subtask.md")
        if os.path.exists(result_path):
            with open(result_path, encoding="utf-8") as f:
                record = [line[2:] for line in f.read().splitlines() if line.startswith("- ")]
            block = [line[2:] for line in approved.split("RESULT RECORD\n")[-1].splitlines() if line.startswith("  ")]
            log.check("criterion 8: participant/context/jira/results/create-subtask.md holds the %d lines of the result record the run printed. (Both were written by that one run, so this shows the file was not changed since, and no more.)" % len(record), len(record) >= 10 and record == block[:len(record)])
            for label, start in (("the issue key", "Issue key: "), ("the identifier of what was created", "Identifier of what was created: Jira issue id "),
                                 ("the target project", "Target project: "), ("the timestamp", "Written at: "), ("the confirmer", "Confirmed by: ")):
                log.check("criterion 8: the result record holds %s" % label, any(line.startswith(start) and len(line) > len(start) for line in record))
            log.check("criterion 8: the result record holds no site address", not any(re.search(NO_ADDRESS[0][1], line) for line in record))
        else:
            log.check("criterion 8: participant/context/jira/results/create-subtask.md is there", False)
    else:
        log.check("live: the approved run and its preview are both there to be compared", False)

    log.part("PART B. The approved run and the refusals against the made-up Jira")
    log.out(FAKE_NOTE)
    log.out("")
    log.out("B1. A preview, then five confirmations and one preview that must be refused. What the made-up Jira holds first:")
    start = show(log)
    _, out = log.command("subtask.py", "preview", *base())
    fp = fingerprint_in(out)
    log.out("")
    log.out("No confirmation at all:")
    code, out = log.command("subtask.py", "confirm", *base())
    log.check("criterion 7: a missing confirmation is refused", code == 1 and "REFUSED: no confirmation was given." in out)
    log.out("")
    log.out("A fingerprint with no name:")
    code, out = log.command("subtask.py", "confirm", *base(), "--fingerprint", fp)
    log.check("criterion 7: a fingerprint with nobody's name is refused", code == 1 and "the name of the person confirming" in out)
    log.out("")
    log.out("The title in the change file is altered after the preview, and the old fingerprint is confirmed:")
    with open(os.path.join(work, "wanted.json"), "w", encoding="utf-8") as f:
        json.dump({"parent": "SAND-1", "summary": TITLE + " and the time"}, f)
    code, out = log.command("subtask.py", "confirm", *base(), "--fingerprint", fp, "--confirmed-by", "the participant")
    log.check("criterion 7: a change that differs from the preview is refused", code == 1 and "the title is not the title the preview showed" in out)
    with open(os.path.join(work, "wanted.json"), "w", encoding="utf-8") as f:
        json.dump({"parent": "SAND-1", "summary": TITLE}, f, indent=2)
        f.write("\n")
    log.out("")
    log.out("The parent in the change file is changed to SAND-2, the story with the same title, and the old fingerprint is confirmed:")
    code, out = log.command("subtask.py", "confirm", "--source", "fake", "--change", "WORK/twin.json", "--allowlist", ALLOW, "--state", "STATE", "--fingerprint", fp, "--confirmed-by", "the participant")
    log.check("criterion 7: the same title aimed at the other story with that title is refused", code == 1 and "it names a different parent" in out)
    log.out("")
    log.out("The preview is 16 minutes old, by the test clock:")
    code, out = log.command("subtask.py", "confirm", *base(), "--fingerprint", fp, "--confirmed-by", "the participant", "--pretend-minutes-later", "16")
    log.check("criterion 7: a preview older than the stated 15 minutes is refused", code == 1 and "this preview is too old" in out and "TEST CLOCK" in out)
    log.out("")
    log.out("A parent in a project that is not on the allowlist:")
    code, out = log.command("subtask.py", "preview", *base("production"))
    log.check("criterion 6: a project not on the sandbox allowlist is refused, at the preview", code == 1 and "project PROD (project id 20002)" in out and "is not on the sandbox allowlist" in out)
    log.out("")
    log.out("What the made-up Jira holds after those six refusals:")
    log.check("after the six refusals the made-up Jira holds what it held: %s subtask of SAND-1 and %s issues" % start, show(log) == start == (1, 7))

    log.out("")
    log.out("B2. The approved run. The same preview is still open and unaltered, and is now confirmed:")
    code, out = log.command("subtask.py", "confirm", *base(), "--fingerprint", fp, "--confirmed-by", "the participant", "--result", "STATE/result.md")
    log.check("criterion 4: with the fingerprint and a name, one subtask is written", code == 0 and "WRITTEN to Jira: one subtask, SAND-6 (issue id 30008), under parent SAND-1." in out)
    log.check("criterion 7: the confirmation names the fingerprint of the preview", "CONFIRMATION for preview %s, given by: the participant" % fp in out)
    log.check("criterion 3: the parent read back is the parent intended", "its parent, read back, is issue id 30001. The parent intended is issue id 30001 (SAND-1). They are the same: yes" in out)
    log.check("criterion 8: the result record holds the key, the identifier, the project, the time and the confirmer",
              all(part in out for part in ("Issue key: SAND-6", "Jira issue id 30008", "Target project: SAND (project id 20001)", "Written at: ", "Confirmed by: the participant, at ")))
    log.out("")
    log.check("the made-up Jira now holds one more subtask of SAND-1 and one more issue", show(log) == (2, 8))
    log.check("the other story with the same title, SAND-2, still has no subtask", show(log, "SAND-2")[0] == 0)
    log.out("")
    log.out("The same fingerprint again:")
    code, out = log.command("subtask.py", "confirm", *base(), "--fingerprint", fp, "--confirmed-by", "the participant")
    log.check("criterion 7: a fingerprint is used once", code == 1 and "A fingerprint is used once" in out)
    return log.save("confirmation.txt"), state, work, fp


# ---------------------------------------------------------------- parent-check.txt and rerun.txt


def record_check_and_rerun(state, work, fp):
    log = Log("The parent check. jira-create-subtask, attempt jira-attempt-014", state, work)
    text, gone, child = log.live("reading the subtask back, and the two refused parents", "live-parent-check.txt", "live-refused-missing-parent.txt", "live-refused-subtask-parent.txt")
    live_checks(log, "live parent check", text, (
        ("it says it writes nothing", "Nothing is written by this command."),
        ("the parent read back is reported as the parent intended", re.compile(r"^  its parent, read back, is issue id (\d+)\. The parent intended is issue id \1 .*They are the same: yes$", re.M)),
        ("the parent's own list holds the subtask", re.compile(r"subtasks holds issue id \d+: yes$", re.M)),
        ("there is one subtask with this title under the parent", "subtasks of this parent with this title: 1"),
        ("the program reports that every request was a read", "Every one was a GET, which reads and cannot change anything."),
        ("it ends as found", "FOUND: the subtask is under the parent intended.")))
    refusal(log, "live refusal, a parent that does not exist", gone, "REFUSED: Jira answered 404 for the parent.")
    refusal(log, "live refusal, a parent that is itself a subtask", child, "is itself a subtask")
    paths = {name: os.path.join(ATTEMPT, "logs", name) for name in ("live-preview.txt", "live-confirmation.txt")}
    if text and all(os.path.exists(path) for path in paths.values()):
        preview, approved = (open(paths[name], encoding="utf-8").read() for name in ("live-preview.txt", "live-confirmation.txt"))
        intended = found(r"^Parent:     \S+ \(issue id (\d+)\)", preview)
        read = found(r"^Parent read back from the subtask just now: issue id (\d+)\.", text)
        log.check("criterion 3: the parent id read back in the check (%s) is the issue id the PREVIEW gave for the parent (%s), compared here as printed" % (read, intended), bool(read) and read == intended)
        made = found(r"^WRITTEN to Jira: one subtask, (\S+ \(issue id \d+\))", approved)
        log.check("live: the subtask checked is the subtask the confirmation reported written: %s" % made, bool(made) and "Subtask:    %s" % made in text)
        log.check("live: the check is of the fingerprint that was confirmed", "PARENT CHECK for the write of preview %s." % fingerprint_in(preview) in text)
        if child:
            key = made.split(" ")[0] if made else "?"
            log.check("live: the parent refused as a subtask is the subtask this workflow created, %s" % key, bool(made) and "the parent named, %s," % made in child)
    else:
        log.check("live: the parent check, the preview and the confirmation are all there to be compared", False)

    log.part("PART B. The parent check and the refused parents against the made-up Jira")
    log.out(FAKE_NOTE)
    log.out("The made-up Jira is the one confirmation.txt left: SAND-6 was created under SAND-1 by preview %s." % fp)
    log.out("")
    code, out = log.command("subtask.py", "check", "--source", "fake", "--state", "STATE", "--fingerprint", fp)
    log.check("criterion 3: the subtask is read back and its parent is the parent intended", code == 0 and "Parent read back from the subtask just now: issue id 30001." in out and "They are the same: yes" in out)
    log.check("the check sent only reads", "Every one was a GET" in out)
    before = show(log)
    for label, change, reason, criterion in (
            ("A parent that does not exist, SAND-999:", "missing", "REFUSED: Jira answered 404 for the parent.", "criterion 2: a missing parent is refused before the preview"),
            ("A parent that is itself a subtask, SAND-4:", "subtask-parent", "the parent named, SAND-4 (issue id 30004), is itself a subtask", "criterion 2: a parent that is itself a subtask is refused before the preview"),
            ("A parent that is closed, SAND-3:", "closed", "the parent named, SAND-3 (issue id 30003), is closed", "the closed-parent rule: a closed parent is refused before the preview"),
            ("A title given in place of a reference:", "by-title", "A title is not accepted", "criterion 1: a parent given by its title is refused")):
        log.out("")
        log.out(label)
        code, out = log.command("subtask.py", "preview", *base(change))
        log.check(criterion, code == 1 and reason in out and "PREVIEW" not in out and not fingerprint_in(out) and "Nothing has been written." in out)
    log.check("no preview was saved for any of the four: the state folder holds the one preview it held", len(os.listdir(os.path.join(state, "previews"))) == 1)
    log.out("")
    log.check("after the four refusals the made-up Jira holds what it held", show(log) == before == (2, 8))
    log.out("")
    log.out("The two stories with one title. SAND-2 has the title SAND-1 has. A preview naming SAND-2 shows SAND-2's id:")
    code, out = log.command("subtask.py", "preview", *base("twin"))
    log.check("criterion 1: the story with the same title is a different parent, shown by its own key and id", code == 0 and "Parent:     SAND-2 (issue id 30002)" in out and "With the same title, under this parent: 0." in out)
    ok = log.save("parent-check.txt")

    log = Log("The second run. jira-create-subtask, attempt jira-attempt-014", state, work)
    again, reuse = log.live("the same workflow run again", "live-rerun-preview.txt", "live-rerun-confirm.txt")
    live_checks(log, "live rerun, the preview", again, (
        ("it finds nothing to add", "NOTHING TO ADD. Nothing has been written."),
        ("it names the subtask that is already there", "The parent already has a subtask with this title: "),
        ("it issues no fingerprint", "No fingerprint is issued, because there is nothing to confirm, and nothing was sent.")))
    if again:
        log.check("live rerun: the preview has no fingerprint line", not fingerprint_in(again))
    if again and os.path.exists(paths["live-confirmation.txt"]):
        approved = open(paths["live-confirmation.txt"], encoding="utf-8").read()
        made = found(r"^WRITTEN to Jira: one subtask, (\S+) \(issue id (?:\d+)\)", approved)
        made_id = found(r"^WRITTEN to Jira: one subtask, \S+ \(issue id (\d+)\)", approved)
        log.check("live rerun: the subtask it found already there is the one the first run created: %s" % made, bool(made) and "with this title: %s (issue id %s)." % (made, made_id) in again)
        log.check("live rerun: the duplicate check counts one subtask with this title", "With the same title, under this parent: 1 (" in again)
    else:
        log.check("live rerun: the second preview and the confirmation are both there to be compared", False)
    refusal(log, "live rerun, the old fingerprint", reuse, "has already been confirmed and written. A fingerprint is used once")

    log.part("PART B. The second run against the made-up Jira")
    log.out(FAKE_NOTE)
    before = show(log)
    log.out("")
    log.out("The whole workflow again, with the same change file:")
    code, out = log.command("subtask.py", "preview", *base())
    log.check("criterion 9: the second preview finds the subtask there and issues no fingerprint", code == 0 and "NOTHING TO ADD" in out and "SAND-6 (issue id 30008)" in out and not fingerprint_in(out))
    code, out = log.command("subtask.py", "confirm", *base(), "--fingerprint", fp, "--confirmed-by", "the participant")
    log.check("criterion 9: the old fingerprint cannot be confirmed again", code == 1 and "A fingerprint is used once" in out)
    log.out("")
    log.check("criterion 9: the made-up Jira holds what it held before the second run: %s subtasks of SAND-1, %s issues" % before, show(log) == before == (2, 8))
    log.out("")
    log.out("THE LIMIT, stated. Jira's request to create an issue has no 'only if there is none like it' condition. Two runs")
    log.out("at the same moment, each with its own preview, could both create the subtask. Each run counts the subtasks with")
    log.out("this title after it writes, and ends with 'MORE THAN ONE' and exit code 2 if there are two. That case is in the")
    log.out("tests (test_the_same_subtask_created_by_someone_at_the_last_moment_is_reported), and cannot be staged from the")
    log.out("command line. A person would notice it by that message, or by two subtasks with one title under the story.")
    return log.save("rerun.txt") and ok


def main():
    ok = record_preview()
    done, state, work, fp = record_confirmation()
    ok = record_check_and_rerun(state, work, fp) and done and ok
    shutil.rmtree(state, ignore_errors=True)
    shutil.rmtree(work, ignore_errors=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
