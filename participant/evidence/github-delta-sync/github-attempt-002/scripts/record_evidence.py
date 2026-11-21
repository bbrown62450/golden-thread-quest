#!/usr/bin/env python3
"""Records logs/delta-run.txt, logs/failed-sync-run.txt and logs/analysis-intact.txt for the github-delta-sync quest.

Each block between dashed lines is what a command printed. Every command is
started as a person would start it. Nothing here contacts GitHub: every run is
against the made-up GitHub in participant/skills/github-delta-sync/fake_github.py,
and the repository, its issues, comments and logins are invented.

The three logs are one story in one folder, participant/context/github/delta/:
a first sync, a delta, a delta that fails partway, the recovery, a last delta,
and a full read. The runs write issues.md and state.json there, and
participant/context/github/sync-state.md. This script removes those first,
because they are generated. It never writes, moves or removes anything in the
notes folder there. Runs that need a wrong clock, no margin or an empty folder
write to a temporary folder, shown as COPY.

This script checks for itself. It works out from the made-up GitHub which
issues changed, reads the cursor from the memory file, and takes the SHA-256
of the notes and of the generated files, rather than taking the sync's word.

Run from anywhere:  python3 scripts/record_evidence.py
Exit code 0 if every check came out as expected, 1 if not.
"""
import contextlib
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ATTEMPT = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(ATTEMPT, "..", "..", "..", ".."))
SKILL = "participant/skills/github-delta-sync"
SYNC = SKILL + "/sync.py"
OUT = "participant/context/github/delta"
ISSUES, MEMORY, NOTES, STATE_DOC = OUT + "/issues.md", OUT + "/state.json", OUT + "/notes", "participant/context/github/sync-state.md"

sys.path.insert(0, os.path.join(ROOT, SKILL))
import fake_github  # noqa: E402
import sync  # noqa: E402
from fake_github import CLOCK, FakeGitHub, node  # noqa: E402


class Log:
    def __init__(self, title):
        self.lines, self.problems, self.copy = [title], [], None
        self.out("Recorded by scripts/record_evidence.py. No request was sent to GitHub. The repository, its issues, comments and logins are made up.")

    def out(self, text=""):
        self.lines.append(text)

    def part(self, text):
        self.lines += ["", "=" * 78, text]

    def check(self, label, ok):
        self.lines.append("  %-4s %s" % ("ok" if ok else "FAIL", label))
        if not ok:
            self.problems.append(label)

    def tidy(self, text):
        return text.replace(self.copy, "COPY") if self.copy else text

    def block(self, title, code, text):
        self.out(self.tidy(title))
        self.lines += ["-" * 78, self.tidy(text.rstrip("\n")), "-" * 78, "exit code: %s" % code]

    def command(self, *args, script=SYNC):
        done = subprocess.run([sys.executable, script] + list(args), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        self.block("$ python3 %s" % " ".join([script] + list(args)), done.returncode, done.stdout)
        return done.returncode, done.stdout

    def in_process(self, what, fake, out_dir, **options):
        """A sync started inside this script, for a made-up GitHub that the command line cannot make."""
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            try:
                code = sync.run(sync.Client(fake.get, sleep=lambda s: None), out_dir, "fake", fake_github.REPO,
                                **dict({"local_now": fake.now}, **options))
            except sync.Stop as stop:
                print("github-delta: STOPPED: %s.\ngithub-delta: Nothing was written. %s" % (stop, sync.cursor_line(out_dir)))
                code = 1
        self.block("(inside this script) %s" % what, code, printed.getvalue())
        return code, printed.getvalue()

    def save(self, name):
        count = sum(1 for line in self.lines if re.match(r"  (ok  |FAIL) ", line))
        self.out()
        self.out("RESULT: %s" % ("ALL CHECKS PASSED. %d checks." % count if not self.problems else "%d OF %d CHECKS FAILED." % (len(self.problems), count)))
        os.makedirs(os.path.join(ATTEMPT, "logs"), exist_ok=True)
        with open(os.path.join(ATTEMPT, "logs", name), "w", encoding="utf-8") as f:
            f.write("\n".join(self.lines) + "\n")
        print("%s: %s" % (name, self.lines[-1]))
        for problem in self.problems:
            print("  FAILED: " + problem)
        return not self.problems


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def notes_now():
    return {name: sha(os.path.join(NOTES, name)) for name in sorted(os.listdir(NOTES))}


def generated_now():
    return {name: sha(name) for name in (ISSUES, MEMORY, STATE_DOC)}


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def memory(folder=OUT):
    return json.loads(read(os.path.join(folder, "state.json")))


def cursor():
    return memory()["cursor"]["time"]


def fetched_in(text):
    """The issue numbers a sync says it fetched."""
    return sorted(int(n) for n in re.findall(r"fetched: issue \S+, number (\d+)\.", text))


def changed_since(step, since):
    """Worked out by this script from the made-up GitHub: the issues updated at or after a time."""
    return sorted(i["number"] for i in FakeGitHub(step).issues() if i["updated_at"] >= since)


def digest_in(text):
    return re.search(r"local state digest: ([0-9a-f]{64})", text).group(1)


def delta_run(log):
    log.part("PART 1. The first sync. There is no cursor, so every issue is read")
    code, text = log.command("--source", "fake")
    log.check("exit code 0", code == 0)
    log.check("all 12 issues were fetched, and the 3 pull requests were left out",
              fetched_in(text) == list(range(1, 13)) and "Pull requests left out: 3" in text)
    log.check("the cursor in the memory file is the made-up GitHub's clock at the start of the sync: %s" % CLOCK[0], cursor() == CLOCK[0])

    log.part("PART 2. A delta sync, a day later, after 4 issues and 1 pull request changed (criteria 1 and 5)")
    since = sync.since_for(CLOCK[0], sync.MARGIN_SECONDS)
    expected = changed_since(1, since)
    log.out("Worked out by this script from the made-up GitHub: the issues updated at or after %s are numbers %s."
            % (since, ", ".join(str(n) for n in expected)))
    code, text = log.command("--source", "fake", "--fake-step", "1")
    state = memory()
    log.check("exit code 0", code == 0)
    log.check("criterion 1: the issues fetched are exactly the ones this script worked out: %s" % expected,
              fetched_in(text) == expected == [3, 5, 7, 13])
    log.check("criterion 1: 4 fetched, 9 not fetched, and 6 requests in all", "fetched: 4 issues, in 4 requests for their comments. Not fetched: 9" in text
              and "requests made: 6, every one a GET (1 repository, 1 listing, 4 comments, 0 look-ups)" in text)
    log.check("criterion 5: the run reports 1 new, 3 changed, 9 unchanged", "This sync: 1 new, 3 changed, 9 unchanged (9 not fetched, 0 fetched and found the same)" in text)
    log.check("the counts add up to the 13 issues held", len(state["issues"]) == 13 == 1 + 3 + 9)
    log.check("the pull request that changed was not fetched", "Pull requests left out: 1" in text and 21 not in fetched_in(text))
    log.check("criterion 2: the cursor moved to GitHub's clock at the start of this sync: %s" % CLOCK[1], cursor() == CLOCK[1])
    log.check("the 9 issues not fetched are as the first sync left them",
              all(state["issues"][node(n)]["last_fetched"] == CLOCK[0] for n in range(1, 13) if n not in expected))

    log.part("PART 3. The same delta again, with nothing changed since")
    code, text = log.command("--source", "fake", "--fake-step", "1")
    log.check("exit code 0, nothing fetched, 2 requests", code == 0 and fetched_in(text) == [] and "requests made: 2," in text)
    log.check("criterion 5: 0 new, 0 changed, 13 unchanged", "This sync: 0 new, 0 changed, 13 unchanged (13 not fetched" in text)

    log.part("PART 4. Clock differences: the same two syncs on a machine whose clock is wrong")
    for wrong, word in (("2026-11-20T09:07:00Z", "7 minutes fast"), ("2026-11-18T09:00:00Z", "2 days slow")):
        with tempfile.TemporaryDirectory() as copy:
            log.copy = copy
            log.in_process("the first sync, with this machine's clock %s" % word, FakeGitHub(0), copy, local_now=wrong)
            later = FakeGitHub(1)
            code, text = log.in_process("the delta, with this machine's clock still %s" % word, later, copy,
                                        local_now=wrong.replace("-20T", "-21T").replace("-18T", "-19T"))
            asked = [p["since"] for path, p in later.calls if "since" in p]
            log.check("clock %s: the cursor is still GitHub's time, %s, and the delta asked from %s" % (word, CLOCK[1], since),
                      memory(copy)["cursor"]["time"] == CLOCK[1] and asked == [since])
            log.check("clock %s: the same 4 issues were fetched, and the local state has the same digest as part 2" % word,
                      fetched_in(text) == expected and sync.digest(memory(copy)["issues"]) == sync.digest(state["issues"]))
        log.copy = None

    log.part("PART 5. Clock differences: GitHub answers with no Date header")
    with tempfile.TemporaryDirectory() as copy:
        log.copy = copy
        fake = FakeGitHub(0)
        fake.send_date = False
        code, text = log.in_process("a first sync against a made-up GitHub that sends no Date header", fake, copy)
        log.check("exit code 1: the run stops, and does not use this machine's clock in its place", code == 1 and "no usable Date header" in text)
        log.check("nothing was written", os.listdir(copy) == [])
    log.copy = None
    return log.save("delta-run.txt")


def failed_run(log):
    log.out("This follows delta-run.txt, in the same folder. The cursor is %s." % cursor())
    since = sync.since_for(CLOCK[1], sync.MARGIN_SECONDS)
    expected = changed_since(2, since)
    log.out("The made-up GitHub is now at step 2. Worked out by this script: the issues updated at or after %s are numbers %s."
            % (since, ", ".join(str(n) for n in expected)))
    log.out("Issue 11 is among them because of the margin: its change is stamped 2026-11-21T08:58:00Z, two minutes before the cursor,")
    log.out("and the sync that set the cursor was not shown it.")
    before, cursor_before = generated_now(), cursor()

    log.part("PART 1. A delta that fails partway: GitHub fails when asked for the comments of issue 8 (criteria 2 and 3)")
    code, text = log.command("--source", "fake", "--fake-step", "2", "--fake-fail-issue", "8")
    log.check("exit code 1", code == 1)
    log.check("the run had listed all 7 changed issues before it failed", "Issues: 7" in text)
    log.check("criterion 3: the cursor in the memory file is where it was: %s" % cursor_before, cursor() == cursor_before == CLOCK[1])
    log.check("the run says so", "Nothing was written. The cursor is where it was: %s." % cursor_before in text)
    log.check("criterion 2: every generated file is byte for byte as it was, by SHA-256 taken by this script", generated_now() == before)

    log.part("PART 2. Where the cursor is, asked without contacting anything")
    code, text = log.command("--status")
    log.check("the status gives the same cursor", code == 0 and "cursor: %s." % cursor_before in text)

    log.part("PART 3. The next sync recovers what the failed one missed (criterion 4)")
    code, text = log.command("--source", "fake", "--fake-step", "2")
    state = memory()
    log.check("exit code 0", code == 0)
    log.check("it asked from the same time as the failed one: %s" % since, "asking for issues updated at or after %s" % since in text)
    log.check("criterion 4: all 7 issues were fetched, the ones before the failure and the ones after it: %s" % expected,
              fetched_in(text) == expected == [2, 4, 6, 8, 9, 10, 11])
    log.check("criterion 5: 0 new, 7 changed, 6 unchanged", "This sync: 0 new, 7 changed, 6 unchanged" in text)
    log.check("criterion 2: only now did the cursor move, to %s" % CLOCK[2], cursor() == CLOCK[2])
    log.check("issue 11's late change, found by the margin, is held", len(state["issues"][node(11)]["comments"]) == 1)
    with tempfile.TemporaryDirectory() as copy:
        for step in (0, 1, 2):
            with contextlib.redirect_stdout(io.StringIO()):
                sync.run(sync.Client(FakeGitHub(step).get), copy, "fake", fake_github.REPO, local_now=CLOCK[step])
        clean = sync.digest(memory(copy)["issues"])
    log.out("  digest after the failure and the recovery:        %s" % sync.digest(state["issues"]))
    log.out("  digest of three syncs with no failure, made here: %s" % clean)
    log.check("the local state is what it would have been had nothing failed", clean == sync.digest(state["issues"]) == digest_in(text))

    log.part("PART 4. The same step with no margin, in a copy: the late change is missed, and --verify says so")
    with tempfile.TemporaryDirectory() as copy:
        log.copy = copy
        for step in (0, 1):
            with contextlib.redirect_stdout(io.StringIO()):
                sync.run(sync.Client(FakeGitHub(step).get), copy, "fake", fake_github.REPO, local_now=CLOCK[step])
        code, text = log.in_process("the delta at step 2 with a margin of 0 seconds", FakeGitHub(2), copy, margin=0)
        log.check("without the margin, issue 11 is not fetched", code == 0 and 11 not in fetched_in(text) and len(fetched_in(text)) == 6)
        code, text = log.in_process("--verify, in the same copy", FakeGitHub(2), copy, verify=True)
        log.check("--verify exits 3 and names issue 11 as different", code == 3 and re.findall(r"DIFFERENT: issue (\S+)", text) == [node(11)])
    log.copy = None
    return log.save("failed-sync-run.txt")


def analysis_intact(log, notes_start, notes_between):
    log.out("This follows failed-sync-run.txt, in the same folder.")
    log.out("")
    log.out("SHA-256 of each notes file, taken by this script BEFORE the first sync of delta-run.txt:")
    for name, value in notes_start.items():
        log.out("  notes/%s  %s" % (name, value))
    log.part("PART 1. The notes after each sync so far (criterion 6)")
    for what, sums in notes_between:
        log.check("after %s: every notes file has the SHA-256 it started with" % what, sums == notes_start)

    log.part("PART 2. A full read into an empty folder, compared with the accumulated deltas (criterion 7)")
    log.out("The folder holds a first sync, two deltas, a failed delta and its recovery. The made-up GitHub is at step 2.")
    deltas = sync.digest(memory()["issues"])
    with tempfile.TemporaryDirectory() as copy:
        log.copy = copy
        code, text = log.command("--source", "fake", "--fake-step", "2", "--out", copy)
        full = sync.digest(memory(copy)["issues"])
        log.out("  digest of the accumulated deltas, computed by this script: %s" % deltas)
        log.out("  digest of the full read, computed by this script:          %s" % full)
        log.check("criterion 7: the two digests are the same", code == 0 and deltas == full == digest_in(text))
        ours, theirs = memory()["issues"], memory(copy)["issues"]
        log.check("field by field and comment by comment, the 13 issues are the same in both",
                  set(ours) == set(theirs) and len(ours) == 13 and all(sync.kept(ours[n]) == sync.kept(theirs[n]) for n in ours))
    log.copy = None
    code, text = log.command("--source", "fake", "--fake-step", "2", "--verify")
    log.check("--verify, in the delta folder itself: THE SAME, exit code 0", code == 0 and "are THE SAME" in text)
    log.check("criterion 6: the notes are unchanged", notes_now() == notes_start)

    log.part("PART 3. A day later: one issue edited, one deleted, one transferred. A delta, then --verify")
    code, text = log.command("--source", "fake", "--fake-step", "3")
    log.check("the delta fetched the one edited issue, number 9, and cannot see the other two", code == 0 and fetched_in(text) == [9])
    before = generated_now()
    code, text = log.command("--source", "fake", "--fake-step", "3", "--verify")
    log.check("--verify exits 3: the local copy and a full read differ, by issues 1 and 12",
              code == 3 and re.findall(r"DIFFERENT: issue (\S+) is held locally", text) == [node(1), node(12)])
    log.check("--verify wrote nothing and did not move the cursor", generated_now() == before and cursor() == CLOCK[3])

    log.part("PART 4. A full read in place finds out why, and flags them. Nothing is deleted locally")
    code, text = log.command("--source", "fake", "--fake-step", "3", "--full")
    state = memory()
    log.check("exit code 0", code == 0)
    log.check("issue 12 is flagged as deleted and issue 1 as transferred, each with its last known state",
              (state["issues"][node(12)]["reason"], state["issues"][node(12)]["state"]) == ("deleted", "closed")
              and (state["issues"][node(1)]["reason"], state["issues"][node(1)]["state"]) == ("transferred", "open"))
    log.check("all 13 issues are still held", len(state["issues"]) == 13)
    with tempfile.TemporaryDirectory() as copy:
        log.copy = copy
        code, text = log.command("--source", "fake", "--fake-step", "3", "--out", copy)
        log.out("  digest of the delta folder, computed by this script: %s" % sync.digest(state["issues"]))
        log.out("  digest of a full read into an empty folder:          %s" % sync.digest(memory(copy)["issues"]))
        log.check("criterion 7: the delta folder and a full read into an empty folder have the same digest again",
                  sync.digest(state["issues"]) == sync.digest(memory(copy)["issues"]))
    log.copy = None

    log.part("PART 5. The notes after everything (criterion 6)")
    end = notes_now()
    for name in sorted(set(notes_start) | set(end)):
        log.out("  notes/%s  before %s  after %s" % (name, notes_start.get(name, "absent"), end.get(name, "absent")))
    log.check("every notes file is byte for byte as it was before the first sync, after 9 runs in this folder, one of them failed", end == notes_start)
    log.check("that includes the notes of the deleted issue and of the transferred one",
              {node(12) + ".md", node(1) + ".md"} <= set(end))
    listing = read(ISSUES)
    log.check("the issues file still points to both of those notes",
              all("`notes/%s.md`" % node(n) in next(l for l in listing.splitlines() if l.startswith("| #%d |" % n)) for n in (1, 12)))
    log.check("no note text is in any generated file", not any("Made-up analysis" in read(name) for name in generated_now()))
    return log.save("analysis-intact.txt")


def main():
    os.chdir(ROOT)
    for name in (ISSUES, MEMORY, STATE_DOC):
        if os.path.exists(name):
            os.remove(name)
    notes_start = notes_now()
    between = []
    ok = delta_run(Log("A delta sync that fetches only changed issues. github-delta-sync, attempt github-attempt-002"))
    between.append(("the first sync and the two deltas of delta-run.txt", notes_now()))
    ok = failed_run(Log("A sync that fails partway, and the recovery. github-delta-sync, attempt github-attempt-002")) and ok
    between.append(("the failed delta and the recovery of failed-sync-run.txt", notes_now()))
    ok = analysis_intact(Log("Local analysis unchanged, and a full read compared with the deltas. github-delta-sync, attempt github-attempt-002"),
                         notes_start, between) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
