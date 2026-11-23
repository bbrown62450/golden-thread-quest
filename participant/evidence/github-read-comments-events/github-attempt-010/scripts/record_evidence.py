#!/usr/bin/env python3
"""Records logs/sync-twice.txt and logs/notes-intact.txt for the github-read-comments-events quest.

It also has the sync write participant/context/github/comments-sample.md and
participant/context/github/event-rules.md.

Each block between dashed lines is what a command printed. Every command is
started as a person would start it. Nothing here contacts GitHub: every run is
against the made-up GitHub in participant/skills/github-read-comments-events/fake_github.py,
and the repository, its people, its issue and its comments are invented.

Before the first sync this script removes what the last recording left: the
sync's memory and the sample file. It does not touch the notes file, except to
create it if it is not there.

This script checks for itself. It counts the comments and events in the file
with its own patterns, asks the made-up GitHub directly what it holds at each
step, and takes its own SHA-256 of the notes file, rather than taking the
sync's word.

Run from anywhere:  python3 scripts/record_evidence.py
Exit code 0 if every check came out as expected, 1 if not.
"""
import hashlib
import os
import re
import shlex
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ATTEMPT = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(ATTEMPT, "..", "..", "..", ".."))
SKILL = "participant/skills/github-read-comments-events"
SYNC = SKILL + "/sync.py"
OUT = "participant/context/github/comments-events"
SAMPLE = "participant/context/github/comments-sample.md"
RULES = "participant/context/github/event-rules.md"
NOTES = OUT + "/notes/my-notes.md"
NOTES_TEXT = "# My notes on issue 61\n\nMade-up notes, written by hand. The sync must never change this file.\n\n- ask finance which months are affected\n"

sys.path.insert(0, os.path.join(ROOT, SKILL))
import fake_github  # noqa: E402
import sync  # noqa: E402
from fake_github import ISSUE, FakeGitHub  # noqa: E402

C2, C3, C5 = "IC_kwFX6102", "IC_kwFX6103", "IC_kwFX6105"


class Log:
    def __init__(self, title):
        self.lines, self.problems = [title], []
        self.out("Recorded by scripts/record_evidence.py. No request was sent to GitHub. The repository, people, issue and comments are made up.")

    def out(self, text=""):
        self.lines.append(text)

    def part(self, text):
        self.lines += ["", "=" * 78, text]

    def check(self, label, ok):
        self.lines.append("  %-4s %s" % ("ok" if ok else "FAIL", label))
        if not ok:
            self.problems.append(label)

    def run(self, *args):
        done = subprocess.run([sys.executable, SYNC] + list(args), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        self.out("$ python3 " + " ".join(shlex.quote(part) for part in [SYNC] + list(args)))
        self.lines += ["-" * 78, done.stdout.rstrip("\n"), "-" * 78, "exit code: %s" % done.returncode]
        return done.returncode, done.stdout

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


def data(path):
    with open(path, "rb") as f:
        return f.read()


def digest(path):
    return hashlib.sha256(data(path)).hexdigest()


def keys_in(text):
    """The comments and the events in the sample file, by their keys, found with this script's own patterns."""
    return re.findall(r"^### Comment `([^`]+)`$", text, re.M), re.findall(r"^\| `([^`]+)` \| (\S+) \|", text, re.M)


def main():
    os.chdir(ROOT)
    for path in (os.path.join(OUT, "state.json"), SAMPLE):
        if os.path.exists(path):
            os.remove(path)
    os.makedirs(os.path.dirname(NOTES), exist_ok=True)
    if not os.path.exists(NOTES):
        with open(NOTES, "w", encoding="utf-8") as f:
            f.write(NOTES_TEXT)
    subprocess.run([sys.executable, SYNC, "--write-rules", RULES], stdout=subprocess.PIPE, check=True)

    log, notes = Log("Syncing an issue's comments and events. github-read-comments-events, attempt github-attempt-010"), Log(
        "The notes file before and after the syncs. github-read-comments-events, attempt github-attempt-010")
    step1, step2 = FakeGitHub(1), FakeGitHub(2)
    log.out("Before part 1 this script removed the sync's memory and %s, left by the last recording." % SAMPLE)
    log.out("Asked directly, the made-up GitHub holds for issue %d: %d comments and %d timeline entries of its own, of which %d are of a kind the rules call noise."
            % (ISSUE, len(step1.comments[ISSUE]), len(step1.events[ISSUE]), sum(one["event"] in sync.NOISE for one in step1.events[ISSUE])))

    notes.part("PART 1. The notes file before any sync")
    notes.out("The file is %s. It stands for a person's own notes, kept beside the synced copy." % NOTES)
    before, stamp = digest(NOTES), os.stat(NOTES).st_mtime_ns
    notes.out("SHA-256, worked out by this script: %s" % before)
    notes.out("Size: %d bytes." % len(data(NOTES)))
    notes.check("the notes file is there and holds what a person wrote", data(NOTES).decode("utf-8") == NOTES_TEXT)
    common = ["--source", "fake", "--out", OUT, "--markdown", SAMPLE]

    def after_sync(number, text):
        notes.part("PART %d. After sync %d" % (number + 1, number))
        now = digest(NOTES)
        notes.out("SHA-256, worked out by this script: %s" % now)
        line = next((one for one in text.splitlines() if "notes/my-notes.md" in one), "")
        notes.out("What the sync itself printed: " + line.split("github-comments: ", 1)[-1].strip())
        notes.check("the checksum is the same as before any sync", now == before)
        notes.check("the sync's own before and after checksums are that same value, and it says \"same\"", line.count(before) == 2 and line.rstrip().endswith("same"))
        notes.check("the file was not written at all: its last-written time has not moved", os.stat(NOTES).st_mtime_ns == stamp)

    log.part("PART 1. The first sync")
    code, text = log.run(*common)
    first = data(SAMPLE).decode("utf-8")
    comments, events = keys_in(first)
    log.check("exit code 0, and the sync wrote the file", code == 0 and "file: WROTE " in text)
    log.check("the file holds the 4 comments of the made-up GitHub, each under its own node ID (criterion 1)",
              sorted(comments) == sorted(one["node_id"] for one in step1.comments[ISSUE]) and len(comments) == 4)
    log.check("the file holds 10 events, each under GitHub's id for it (criterion 1)", len(events) == 10 and len({key for key, _ in events}) == 10)
    after_sync(1, text)

    log.part("PART 2. The second sync. Nothing has changed on the made-up GitHub (criterion 2)")
    stamp_sample = os.stat(SAMPLE).st_mtime_ns
    code, text = log.run(*common)
    second = data(SAMPLE).decode("utf-8")
    log.check("exit code 0, and the sync says: 0 new, 0 edited, 4 unchanged, 0 found deleted, and 0 new events",
              code == 0 and "This sync: 0 new, 0 edited, 4 unchanged, 0 found deleted. Held now: 4" in text and "events: 0 new this sync. Held now: 10" in text)
    log.check("nothing is duplicated: this script counted 4 comments and 10 events in the file again, and no key twice",
              keys_in(second) == (comments, events) and len(set(comments)) == 4)
    log.check("the file is byte for byte what the first sync wrote, and was not even written again", second == first and os.stat(SAMPLE).st_mtime_ns == stamp_sample and "UNCHANGED" in text)
    log.check("each comment's text is in the file once: this script counted", all(second.count(one["body"]) == 1 for one in step1.comments[ISSUE]))
    after_sync(2, text)

    log.part("PART 3. On the made-up GitHub, a day later: one comment EDITED, one ADDED, one DELETED")
    log.out("Asked directly, the made-up GitHub at step 2 holds %d comments for issue %d. Compared with step 1:" % (len(step2.comments[ISSUE]), ISSUE))
    log.out("  %s was edited: its text and its last-changed time are different" % C2)
    log.out("  %s is new" % C5)
    log.out("  %s is gone: the made-up GitHub no longer lists it, and answers 404 when asked for it by id" % C3)
    held2 = {one["node_id"]: one for one in step2.comments[ISSUE]}
    log.check("that is what the made-up GitHub holds: this script looked", C3 not in held2 and C5 in held2 and held2[C2]["body"] == fake_github.SECOND_EDITED
              and step2.get("/repos/%s/issues/comments/6103" % fake_github.REPO)[0] == 404)
    code, text = log.run(*common, "--fake-step", "2")
    third = data(SAMPLE).decode("utf-8")
    comments3, events3 = keys_in(third)
    log.check("exit code 0, and the sync says: 1 new, 1 edited, 2 unchanged, 1 found deleted", code == 0 and "This sync: 1 new, 1 edited, 2 unchanged, 1 found deleted. Held now: 5" in text)
    log.check("the EDIT was applied in place: the comment %s is in the file once, under the same key, with its new text (criterion 3)" % C2,
              comments3.count(C2) == 1 and third.count("I can reproduce it, on two machines.") == 1)
    log.check("its earlier text is kept under it, as \"Earlier version 1\", and not as another comment",
              ("#### Earlier version 1 of `%s`" % C2) in third and third.index("I can reproduce it, on two machines.") < third.index("#### Earlier version 1 of `%s`" % C2)
              and third.count("I can reproduce it.\n") == 1)
    log.check("the NEW comment %s was added once (criterion 4)" % C5, comments3.count(C5) == 1 and third.count(fake_github.FIFTH) == 1)
    log.check("the DELETED comment %s is still in the file, FLAGGED as deleted, with its last text. It was not removed (criterion 7)" % C3,
              comments3.count(C3) == 1 and "**DELETED on GitHub.** Found missing by the sync at 2026-11-25T09:30:00Z" in third and fake_github.THIRD in third)
    log.check("the sync asked the made-up GitHub for that one comment by its id before flagging it, and says so",
              "GitHub answered 404 when asked for this comment by its id" in text and "requests made: 4, every one a GET" in text)
    log.check("the file holds 5 comments, one more than before, and no key twice", sorted(comments3) == sorted(comments + [C5]) and len(set(comments3)) == 5)
    log.check("the two comments nobody touched are word for word what they were", all(one["body"] in third for one in step1.comments[ISSUE] if one["node_id"] not in (C2, C3)))
    after_sync(3, text)

    log.part("PART 4. One more sync, with nothing changed since part 3")
    code, text = log.run(*common, "--fake-step", "2")
    log.check("exit code 0: 0 new, 0 edited, 0 found deleted. The deleted comment is not flagged a second time",
              code == 0 and "This sync: 0 new, 0 edited, 4 unchanged, 0 found deleted. Held now: 5" in text)
    log.check("the file is byte for byte what part 3 wrote", data(SAMPLE).decode("utf-8") == third and "UNCHANGED" in text)
    after_sync(4, text)

    log.part("PART 5. Only the events the rules call material are recorded (criterion 5)")
    log.out("The rules are in %s. This script read the made-up GitHub's timeline for itself and sorted its entries by those rules:" % RULES)
    kinds = [one["event"] for one in step2.events[ISSUE]]
    material = sorted(kind for kind in kinds if kind in sync.MATERIAL)
    noise = sorted(kind for kind in kinds if kind in sync.NOISE)
    unknown = sorted(kind for kind in kinds if kind not in sync.MATERIAL and kind not in sync.NOISE)
    log.out("  material (%d): %s" % (len(material), ", ".join(material)))
    log.out("  noise (%d): %s" % (len(noise), ", ".join(noise)))
    log.out("  of a kind the rules do not name (%d): %s" % (len(unknown), ", ".join(unknown)))
    recorded = sorted(kind.replace("\\_", "_") for _, kind in events3)
    log.check("the file's events are exactly the %d material ones and the %d the rules do not name" % (len(material), len(unknown)), recorded == sorted(material + unknown))
    log.check("not one of the %d noise entries is in the file: no subscribed, unsubscribed, mentioned, pinned or referenced" % len(noise),
              not any(kind in recorded for kind in set(noise)) and len(noise) == 6)
    log.check("the comments are not recorded a second time as events of the kind \"commented\"", "commented" not in recorded)
    log.check("the kind the rules do not name is kept and marked UNCLASSIFIED, not dropped and not passed off as material",
              "| `EV_kwFX4011` | x\\_fixture\\_sparkled | UNCLASSIFIED |" in third)
    log.check("the sync counted the noise in its output, by kind, so that it is not silently lost",
              "Noise, not recorded: 6 (mentioned 1, pinned 1, referenced 1, subscribed 2, unsubscribed 1)" in text)

    notes.part("PART 6. The sync cannot be told to write in the notes folder")
    notes.out("The sync is pointed at the notes file as the place to write its own Markdown.")
    done = subprocess.run([sys.executable, SYNC, "--source", "fake", "--out", OUT, "--markdown", NOTES, "--fake-step", "2"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    notes.out("$ python3 %s --source fake --out %s --markdown %s --fake-step 2" % (SYNC, OUT, NOTES))
    notes.lines += ["-" * 78, done.stdout.rstrip("\n"), "-" * 78, "exit code: %s" % done.returncode]
    notes.check("exit code 1: it stops, saying it does not write in the notes folder", done.returncode == 1 and "the sync does not write in the notes folder" in done.stdout)
    notes.check("the notes file still has the checksum it had before any sync", digest(NOTES) == before and os.stat(NOTES).st_mtime_ns == stamp)

    notes.part("PART 7. In all")
    notes.check("across 4 syncs and one refused write, the notes file is byte for byte what it was (criterion 6)", data(NOTES).decode("utf-8") == NOTES_TEXT)
    notes.check("the notes folder holds that one file and nothing the sync put there", os.listdir(os.path.dirname(NOTES)) == ["my-notes.md"])
    ok = log.save("sync-twice.txt")
    return 0 if notes.save("notes-intact.txt") and ok else 1


if __name__ == "__main__":
    sys.exit(main())
