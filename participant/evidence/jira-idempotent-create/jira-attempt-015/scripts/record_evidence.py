#!/usr/bin/env python3
"""Records the runs against the FAKE Jira for the quest jira-idempotent-create:

    logs/preview.txt          the workflow stopping at a preview
    logs/confirmation.txt     the approved run, and four refusals
    logs/interrupted-run.txt  a creation interrupted after Jira accepted it, and the rerun that finds it; then the
                              other ways a run can end without an answer, and what happens when the search fails
    logs/rerun.txt            the approved workflow run a second time
    logs/manual-edit.txt      the key after a person edits the task by hand

NOTHING HERE TOUCHES A REAL JIRA. The fake Jira is a file in a temporary folder, deleted at the end. Every project,
issue, person and title is made up. The runs against the real sandbox are in the logs whose names begin "live-".

In the records, TEMP stands for the temporary folder and SKILL for participant/skills/jira-idempotent-create.
Each command line is shown shortened: every command was also given --source fake and a state folder. The draft and
the allowlist are shown by file name. The draft is a copy of the skill's fixture, made in the temporary folder.

Run from anywhere:  python3 scripts/record_evidence.py        Exit code 0 if every check came out as expected.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ATTEMPT = os.path.dirname(HERE)
PARTICIPANT = os.path.abspath(os.path.join(ATTEMPT, "..", "..", ".."))
SKILL = os.path.join(PARTICIPANT, "skills", "jira-idempotent-create")
TOOL = os.path.join(SKILL, "create_once.py")
FAKE = os.path.join(SKILL, "fake_jira.py")
DRAFT = os.path.join(SKILL, "fixtures", "export-archive.json")
ALLOWLIST = os.path.join(SKILL, "fixtures", "fake-allowlist.json")
PERSON = "A made-up person"
HEAD = ("Recorded by scripts/record_evidence.py against the FAKE Jira: a file on this computer, with made-up projects and issues.\n"
        "Each block between dashed lines is what a command printed. No real Jira was contacted to make this record.")


class Log:
    def __init__(self, title, temp):
        self.lines, self.problems, self.count, self.temp = [title, HEAD, ""], [], 0, temp

    def out(self, *lines):
        self.lines += list(lines) if lines else [""]

    def part(self, text):
        self.lines += ["", "=" * 78, text]

    def check(self, label, ok):
        self.count += 1
        self.lines.append("  %-4s %s" % ("ok" if ok else "FAIL", label))
        if not ok:
            self.problems.append(label)

    def tidy(self, text):
        for path, name in ((os.path.realpath(self.temp), "TEMP"), (self.temp, "TEMP"), (SKILL, "SKILL")):
            text = text.replace(path, name)
        return text

    def run(self, shown, args):
        done = subprocess.run([sys.executable] + args, capture_output=True, text=True, cwd=SKILL)
        said = self.tidy((done.stdout + done.stderr).rstrip("\n"))
        self.lines += ["$ " + shown, "-" * 78, said, "-" * 78, "exit status: %d" % done.returncode]
        return done.returncode, said

    def save(self, name):
        self.lines += ["", "RESULT: %s" % ("%d OF %d CHECKS FAILED." % (len(self.problems), self.count) if self.problems else "ALL CHECKS PASSED. %d checks." % self.count)]
        os.makedirs(os.path.join(ATTEMPT, "logs"), exist_ok=True)
        with open(os.path.join(ATTEMPT, "logs", name), "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(self.lines) + "\n")
        print("%s: %s" % (name, self.lines[-1]))
        for label in self.problems:
            print("  FAILED: " + label)
        return not self.problems


class Jira:
    """One fake Jira in one state folder, and the commands run against it."""

    def __init__(self, log, temp, name):
        self.log, self.state, self.draft = log, os.path.join(temp, name), os.path.join(temp, "drafts", "export-archive.json")
        if not os.path.exists(self.draft):
            os.makedirs(os.path.dirname(self.draft))
            shutil.copy(DRAFT, self.draft)

    def cmd(self, command, *extra, allowlist=ALLOWLIST, draft=None):
        args = [TOOL, command, "--source", "fake", "--draft", draft or self.draft, "--state", self.state]
        shown = "create_once.py %s --draft %s" % (command, os.path.basename(draft or self.draft))
        if command in ("preview", "confirm"):
            args += ["--allowlist", allowlist]
            shown += " --allowlist %s" % os.path.basename(allowlist)
        return self.log.run(shown + "".join(" " + ('"%s"' % e if " " in e else self.log.tidy(e)) for e in extra), args + list(extra))

    def confirm(self, fingerprint, *extra, **kw):
        return self.cmd("confirm", "--fingerprint", fingerprint, "--confirmed-by", PERSON, *extra, **kw)

    def fake(self, *args):
        return self.log.run("fake_jira.py %s" % " ".join('"%s"' % a if " " in a else a for a in args), [FAKE, args[0], "--state", self.state] + list(args[1:]))

    def issues(self):
        path = os.path.join(self.state, "fake-jira.json")
        if not os.path.exists(path):
            return 3, 0
        with open(path, encoding="utf-8") as f:
            issues = json.load(f)["issues"].values()
        return len(issues), sum(1 for issue in issues if any(label.startswith("gtq-key-") for label in issue["labels"]))

    def record(self):
        with open(os.path.join(self.state, "intents", os.path.basename(self.draft)), encoding="utf-8") as f:
            return json.load(f)


def fingerprint_in(text):
    found = re.search(r"Fingerprint of this preview: ([0-9a-f]{12})", text)
    return found.group(1) if found else ""


def requests_of(text):
    """The requests a run says it sent, in order: ["GET /rest/...", ...]."""
    return [line.strip() for line in text.split("\n") if line.startswith(("  GET /rest", "  POST /rest"))]


def all_get(text):
    return "Every one was a GET" in text and "POST" not in text


def main():
    temp = tempfile.mkdtemp(prefix="gtq-once-")
    ok = True
    try:
        # ------------------------------------------------------------ preview.txt
        log = Log("The workflow stopping at a preview. jira-idempotent-create, attempt jira-attempt-015", temp)
        jira = Jira(log, temp, "state-preview")
        log.part("THE PREVIEW")
        code, said = jira.cmd("preview")
        key = jira.record()["key"]
        log.check("criterion 4: the preview shows the Jira site, the project and the exact changes", code == 0 and "Jira site:  https://" in said and "SAND (project id 20001)" in said
                  and "| Archive the October export files" in said and "issue type  Task" in said)
        log.check("criterion 1: the draft's key, as saved in its local record, is shown in the preview as the one label that would be sent",
                  bool(re.fullmatch(r"gtq-key-[0-9a-f]{16}", key)) and "labels      one label, the key: " + key in said)
        log.check("criterion 5: the permission check is recorded: may this identity create issues here", "(CREATE_ISSUES):   yes" in said)
        log.check("criterion 5: the duplicate check is recorded, by the key and by the title, and where Jira cannot check is stated",
                  "Duplicate check 1, by the key" in said and "Found: 0." in said and "Duplicate check 2, by the title" in said and "Where Jira cannot check" in said)
        log.check("criterion 7: the preview has a fingerprint, and says when it expires", bool(fingerprint_in(said)) and "Expires:" in said and "15 minutes after it was made" in said)
        log.check("criterion 4: nothing was written: every request was a GET, and the before and after snapshots are the same", all_get(said) and "The two are the same" in said)
        log.out("", "The fake Jira, looked at directly after the preview:")
        code, said = jira.fake("show")
        log.check("the fake Jira still holds the 3 issues it began with, and none carries a key", jira.issues() == (3, 0))
        ok = log.save("preview.txt") and ok

        # ------------------------------------------------------------ confirmation.txt
        log = Log("The approved run, and four refusals. jira-idempotent-create, attempt jira-attempt-015", temp)
        jira = Jira(log, temp, "state-confirm")
        log.part("FOUR REFUSALS, each with nothing written. A preview is made first.")
        code, said = jira.cmd("preview")
        first = fingerprint_in(said)

        log.out("", "1. A MISSING CONFIRMATION: no fingerprint is given.")
        code, said = jira.cmd("confirm", "--confirmed-by", PERSON)
        log.check("criterion 7: refused when the confirmation is missing, and nothing written", code == 1 and "no confirmation was given" in said and jira.issues() == (3, 0))

        log.out("", "2. A CHANGE THAT DIFFERS FROM THE PREVIEW: the draft's title is changed after the preview, and the fingerprint of the",
                "   preview is used. (The script rewrites the draft, runs the command, and puts the draft back byte for byte.)")
        with open(jira.draft, "rb") as f:
            original = f.read()
        with open(jira.draft, "w", encoding="utf-8") as f:
            json.dump({"project": "SAND", "summary": "Archive the October export files and delete the originals"}, f)
        try:
            code, said = jira.confirm(first)
        finally:
            with open(jira.draft, "wb") as f:
                f.write(original)
        log.check("criterion 7: refused when the change differs from the preview, and nothing written", code == 1 and "the change is not the one that was previewed" in said
                  and "the title is not the title the preview showed" in said and jira.issues() == (3, 0))

        log.out("", "3. A PREVIEW OLDER THAN THE LIMIT: the test clock is moved 16 minutes on. The limit is 15.")
        code, said = jira.confirm(first, "--pretend-minutes-later", "16")
        log.check("criterion 7: refused when the preview is older than the stated limit, and nothing written", code == 1 and "this preview is too old" in said and "the limit is 15" in said and jira.issues() == (3, 0))

        log.out("", "4. A PROJECT THAT IS NOT ON THE SANDBOX ALLOWLIST: a draft that names PROD, where the identity MAY create issues.")
        prod = os.path.join(temp, "to-production.json")
        with open(prod, "w", encoding="utf-8") as f:
            json.dump({"project": "PROD", "summary": "A made-up task for production"}, f)
        code, said = jira.cmd("preview", draft=prod)
        log.check("criterion 6: refused for a project not on the allowlist, before any preview, and nothing written", code == 1 and "is not on the sandbox allowlist" in said and not fingerprint_in(said) and jira.issues() == (3, 0))
        log.out("   And the same draft as before, with an allowlist that lists no project:")
        empty = os.path.join(temp, "empty-allowlist.json")
        with open(empty, "w", encoding="utf-8") as f:
            json.dump({"sandbox_projects": []}, f)
        code, said = jira.confirm(first, allowlist=empty)
        log.check("criterion 6: the confirmation is refused too when the project is not on the allowlist it is given", code == 1 and "is not on the sandbox allowlist (empty-allowlist.json)" in said and jira.issues() == (3, 0))

        log.part("THE APPROVED RUN. The first preview is still open and unused, and is confirmed by its fingerprint.")
        result = os.path.join(temp, "result.md")
        code, said = jira.confirm(first, "--result", result)
        record = jira.record()
        log.check("criterion 7: the confirmation names the preview's fingerprint and the person, and the write happens in the same run",
                  code == 0 and "CONFIRMATION for preview %s, given by: %s" % (first, PERSON) in said and "The confirmation and the write happened in this one run" in said)
        sent = requests_of(said)
        write = sent.index("POST /rest/api/3/issue") if "POST /rest/api/3/issue" in sent else -1
        log.check("criteria 2, 5 and 6: the order of its requests shows the run read the project, asked the permission question and searched for the key BEFORE the one write",
                  write > 0 and sent.count("POST /rest/api/3/issue") == 1 and all(wanted in sent[:write] for wanted in ("GET /rest/api/3/project/SAND", "GET /rest/api/3/mypermissions", "GET /rest/api/3/search/jql")))
        log.out("  (That the allowlist and the search each STOP a write is shown by the refusals above and in logs/interrupted-run.txt, and by the tests.)")
        log.check("criterion 1: one task was created, and it carries the key as a label on the Jira item", "WRITTEN to Jira: one task, SAND-3 (issue id 30004)" in said
                  and "it carries the label %s: yes" % record["key"] in said and jira.issues() == (4, 1))
        log.check("criterion 8: the result record holds the issue key, the identifier of what was created, the project, the timestamp and the confirmer",
                  all(w in said for w in ("Issue key: SAND-3", "Jira issue id 30004, carrying the label", "Target project: SAND (project id 20001)", "Created, by Jira's own clock:", "Confirmed by: " + PERSON)))
        with open(result, encoding="utf-8") as f:
            log.check("the result record saved as Markdown has the site's address taken out", "fixture-site" not in f.read())
        ok = log.save("confirmation.txt") and ok

        # ------------------------------------------------------------ rerun.txt  (uses the same fake Jira as the approved run)
        rerun = Log("The approved workflow, run a second time. jira-idempotent-create, attempt jira-attempt-015", temp)
        jira.log = rerun
        rerun.out("This continues from the approved run in logs/confirmation.txt, against the same fake Jira: SAND-3 exists and is recorded.")
        rerun.part("1. PREVIEW AGAIN")
        code, said = jira.cmd("preview")
        rerun.check("criterion 9: the preview says there is nothing to create, names the task, and issues no fingerprint", code == 0 and "NOTHING TO CREATE" in said and "SAND-3 (issue id 30004)" in said and not fingerprint_in(said) and all_get(said))
        rerun.part("2. CONFIRM AGAIN, with the fingerprint that was used")
        code, said = jira.confirm(first)
        rerun.check("criterion 9: the confirmation is refused: the task already exists", code == 1 and "already exists: SAND-3" in said)
        rerun.part("3. RESOLVE AGAIN")
        code, said = jira.cmd("resolve")
        rerun.check("criterion 3: resolve finds the task already recorded, and creates nothing", code == 0 and "ALREADY RECORDED: SAND-3" in said and all_get(said))
        rerun.part("4. THE FAKE JIRA, looked at directly")
        jira.fake("show")
        rerun.check("criterion 9: no duplicate: the fake Jira holds 4 issues, as after the approved run, and one carries a key", jira.issues() == (4, 1))
        ok = rerun.save("rerun.txt") and ok

        # ------------------------------------------------------------ manual-edit.txt (same fake Jira)
        edit = Log("The key after a person edits the task by hand. jira-idempotent-create, attempt jira-attempt-015", temp)
        jira.log = edit
        edit.out("Stretch goal. This continues against the same fake Jira: SAND-3 exists and is recorded.")
        edit.part("1. A PERSON CHANGES THE TITLE AND ADDS A LABEL OF THEIR OWN")
        jira.fake("edit", "--issue", "SAND-3", "--summary", "Archive the export files (retitled by hand)", "--add-label", "team-label")
        code, said = jira.cmd("check")
        edit.check("stretch goal: after the edit the task still carries the key, and a search for the key finds it and no other",
                   code == 0 and "it carries the label %s: yes" % record["key"] in said and "this one, and no other" in said and "It has been changed in Jira since" in said)
        code, said = jira.cmd("preview")
        edit.check("and the workflow still creates nothing for this draft", "NOTHING TO CREATE" in said and jira.issues() == (4, 1))
        edit.part("2. THE LIMIT: A PERSON REMOVES THE KEY'S LABEL")
        jira.fake("edit", "--issue", "SAND-3", "--remove-label", record["key"])
        code, said = jira.cmd("check")
        edit.check("THE LIMIT, shown: with the label removed the task is no longer found by its key, and check says so plainly", code == 1 and "NO. The label has been removed" in said)
        code, said = jira.cmd("preview")
        edit.check("the task is still known by the issue id in the local record, so nothing is created", "NOTHING TO CREATE" in said and jira.issues() == (4, 0))
        ok = edit.save("manual-edit.txt") and ok

        # ------------------------------------------------------------ interrupted-run.txt
        log = Log("A creation interrupted, and the rerun. jira-idempotent-create, attempt jira-attempt-015", temp)
        log.out("The interruption is made by the test switch --interrupt-at, which ends the run at a named point as if it had been",
                "killed: nothing after that point is done or recorded. The lost answers in parts 4 and 5 are made by the fake Jira.")

        log.part("1. INTERRUPTED AFTER JIRA ACCEPTED IT, BEFORE THE RESULT WAS RECORDED")
        jira = Jira(log, temp, "state-after-send")
        code, said = jira.cmd("preview")
        code, said = jira.confirm(fingerprint_in(said), "--interrupt-at", "after-send")
        log.check("the run ended after Jira answered 201: exit status 3, and the record says 'sending' with no issue recorded",
                  code == 3 and "The request was sent, and Jira answered 201." in said and jira.record()["status"] == "sending" and jira.record()["issue"] is None)
        jira.fake("show")
        log.check("Jira did create the task: the fake Jira holds 4 issues, and one carries the key", jira.issues() == (4, 1))
        log.out("", "A second run of the workflow, begun as if nothing had happened:")
        code, said = jira.cmd("preview")
        log.check("criterion 2: the rerun does not preview or create: it sees an unknown outcome and says to resolve it", code == 1 and "ITS OUTCOME IS NOT KNOWN" in said and not fingerprint_in(said))
        code, said = jira.cmd("resolve")
        log.check("criterion 2: the first request resolve sends is the search for the key, and it sends no write", requests_of(said)[:1] == ["GET /rest/api/3/search/jql"] and all_get(said))
        log.check("criterion 3: the task found by the key is recorded locally, and nothing is created", code == 0 and "FOUND BY ITS KEY: SAND-3 (issue id 30004)" in said
                  and "NOTHING WAS CREATED by this run" in said and jira.record()["status"] == "linked" and jira.record()["issue"]["id"] == "30004")
        log.check("criterion 8: the result record names the task, the project, the times and the person who confirmed the run that was interrupted",
                  "Issue key: SAND-3" in said and "Confirmed by: " + PERSON in said and "found by its key by `resolve`" in said)
        code, said = jira.cmd("preview")
        log.check("criterion 9: run again, there is nothing to create, and the fake Jira still holds 4 issues with one key", "NOTHING TO CREATE" in said and jira.issues() == (4, 1))

        log.part("2. INTERRUPTED BEFORE THE REQUEST WENT (stretch goal: a second point)")
        jira = Jira(log, temp, "state-before-send")
        code, said = jira.cmd("preview")
        code, said = jira.confirm(fingerprint_in(said), "--interrupt-at", "before-send")
        log.check("the run ended before sending: the record says 'sending', and the fake Jira holds no new issue", code == 3 and jira.record()["status"] == "sending" and jira.issues() == (3, 0))
        code, said = jira.cmd("resolve")
        log.check("an empty search straight away is NOT taken to mean the task does not exist: 'not found yet', nothing created, and it does not count towards the two",
                  code == 1 and "NOT FOUND YET" in said and "count so far: 0" in said and jira.record()["status"] == "sending")
        log.out("", "The rule: two empty searches, each 60 seconds or more after the request ended, and 30 seconds or more apart. The run was",
                "killed, so when the request ended is not known: it is taken to have lasted the 30 seconds a request may wait. The test",
                "clock is moved on 91 seconds, then 122. Against a real Jira the test clock is refused, and the wait is waited.")
        code, said = jira.cmd("resolve", "--pretend-seconds-later", "91")
        log.check("one empty search that counts is not enough: still 'not found yet', the record still says 'sending'", code == 1 and "count so far: 1" in said and jira.record()["status"] == "sending")
        code, said = jira.cmd("resolve", "--pretend-seconds-later", "122")
        log.check("after a second empty search that counts, 31 seconds after the first, the record is released. It says this is not proof, and creates nothing",
                  code == 0 and "NOT FOUND, at " in said and "THAT IS NOT PROOF" in said and jira.record()["status"] == "released" and jira.issues() == (3, 0))
        code, said = jira.cmd("preview")
        second = fingerprint_in(said)
        log.check("creating now needs a NEW preview, which says it is attempt 2, and a new confirmation by a person", bool(second) and "this is attempt 2" in said)
        code, said = jira.confirm(second)
        log.check("confirmed, the task is created once: the fake Jira holds 4 issues and one key", code == 0 and jira.issues() == (4, 1) and jira.record()["status"] == "linked")

        log.part("3. INTERRUPTED AFTER THE TASK WAS RECORDED, BEFORE IT WAS READ BACK (stretch goal: a third point)")
        jira = Jira(log, temp, "state-after-record")
        code, said = jira.cmd("preview")
        code, said = jira.confirm(fingerprint_in(said), "--interrupt-at", "after-record")
        log.check("the run ended after recording: the record already says 'linked'", code == 3 and jira.record()["status"] == "linked")
        code, said = jira.cmd("resolve")
        log.check("the rerun finds it recorded, reads it back, and creates nothing: 4 issues, one key", code == 0 and "ALREADY RECORDED: SAND-3" in said and jira.issues() == (4, 1))

        log.part("4. NO ANSWER CAME BACK, and Jira had created the task. Then the search is behind.")
        jira = Jira(log, temp, "state-lost-answer")
        code, said = jira.cmd("preview")
        fingerprint = fingerprint_in(said)
        jira.fake("set", "--fail-post", "applied-timeout")
        code, said = jira.confirm(fingerprint)
        log.check("a timeout is treated as an unknown outcome, not as a failure: exit status 2, 'not known', and it says not to confirm again",
                  code == 2 and "IT IS NOT KNOWN whether Jira created the task" in said and "DO NOT CONFIRM AGAIN" in said and jira.record()["status"] == "uncertain")
        jira.fake("show")
        log.check("the write was sent once and not sent again by the same run: the fake Jira created ONE issue for it, 4 in all and one key. A second send would have made two", jira.issues() == (4, 1))
        jira.fake("set", "--search-lag", "1")
        code, said = jira.cmd("resolve")
        log.check("with Jira's search behind, resolve says 'not found yet' and creates nothing. The task exists and is not duplicated", code == 1 and "NOT FOUND YET" in said and jira.issues() == (4, 1))
        code, said = jira.cmd("resolve")
        log.check("searched again, the task is found by its key and recorded", code == 0 and "FOUND BY ITS KEY" in said and jira.record()["status"] == "linked" and jira.issues() == (4, 1))

        log.part("5. THE SEARCH ITSELF FAILS")
        jira = Jira(log, temp, "state-search-fails")
        code, said = jira.cmd("preview")
        code, said = jira.confirm(fingerprint_in(said), "--interrupt-at", "after-send")
        with open(os.path.join(jira.state, "intents", "export-archive.json"), "rb") as f:
            before = f.read()
        for failure, words in (("500", "Jira answered 500"), ("timeout", "no answer came back"), ("partial", "cut short")):
            jira.fake("set", "--fail-search", failure)
            code, said = jira.cmd("resolve")
            with open(os.path.join(jira.state, "intents", "export-archive.json"), "rb") as f:
                same = f.read() == before
            log.check("the search fails (%s): resolve stops with exit status 2, creates nothing, leaves the record exactly as it was, and says how to look by hand"
                      % words, code == 2 and "THE SEARCH FOR THE KEY FAILED" in said and words in said and "NOT KNOWN" in said and "To look by hand" in said and same and jira.issues() == (4, 1))
        code, said = jira.cmd("resolve")
        log.check("when the search works again, the task is found and recorded. Nothing was created meanwhile", code == 0 and "FOUND BY ITS KEY" in said and jira.issues() == (4, 1))

        log.part("6. MORE THAN ONE ISSUE CARRIES THE KEY")
        jira = Jira(log, temp, "state-two")
        code, said = jira.cmd("preview")
        code, said = jira.confirm(fingerprint_in(said), "--interrupt-at", "after-send")
        jira.fake("other-issue", "--project", "SAND", "--summary", "A copy made some other way", "--label", jira.record()["key"])
        code, said = jira.cmd("resolve")
        log.check("resolve stops, lists both, and records neither: a person decides", code == 2 and "MORE THAN ONE ISSUE CARRIES THE KEY" in said and jira.record()["status"] == "sending")
        ok = log.save("interrupted-run.txt") and ok
    finally:
        shutil.rmtree(temp, ignore_errors=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
