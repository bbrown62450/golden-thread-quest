#!/usr/bin/env python3
"""Runs the sync against the made-up Jira, in order, and records what it printed. Makes two records in logs/:

    sync-twice.txt     a first sync; a second from unchanged data; then, after a comment was edited, one added and one
                       deleted in the made-up Jira, a third; then a fourth from unchanged data again
    notes-intact.txt   the checksum of the local notes file before and after every one of those syncs

It also leaves the result where the quest asks for it: participant/context/jira/comments-sample.md, with the copy it
is written from beside it, comments-sample.json. Both are deleted at the start, so that the first sync is a first sync.
The notes file, comments-sample.notes.md, is NOT made, changed or deleted by this script. If it is not there the
script stops.

Each command is run as a person would run it, from the `participant` folder, and its output is copied in whole.
The made-up Jira lives in a temporary folder, shown as JIRA, deleted afterwards. NO REAL JIRA IS CONTACTED.
The clock of each sync is given, so that the record comes out the same every time.

Every check reads the output or the files. A record ends with RESULT: ALL CHECKS PASSED, or says which did not.

Run from anywhere:  python3 scripts/record_syncs.py        Exit code 0 if every check passed, 1 if not.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ATTEMPT = os.path.dirname(HERE)
PARTICIPANT = os.path.abspath(os.path.join(ATTEMPT, "..", "..", ".."))
TOOL = "skills/jira-read-comments-history/sync_comments.py"
FAKE = "skills/jira-read-comments-history/fake_jira.py"
OUT = "context/jira"
NAME = "comments-sample"
BAR = "-" * 78
TIMES = ["2026-11-07T09:00:00Z", "2026-11-07T10:00:00Z", "2026-11-08T12:00:00Z", "2026-11-09T12:00:00Z"]


def path_of(ending):
    return os.path.join(PARTICIPANT, OUT, NAME + ending)


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


class Record:
    def __init__(self, name, title, temp):
        self.name, self.temp, self.checks, self.failed = name, temp, 0, []
        self.lines = [title, "jira-read-comments-history, attempt jira-attempt-019. Recorded by scripts/record_syncs.py.",
                      "Read from the made-up Jira (skills/jira-read-comments-history/fake_jira.py): one made-up story with made-up comments. No real Jira was contacted.",
                      "Commands are run from the `participant` folder. JIRA is a temporary folder that holds the made-up Jira, deleted afterwards.", ""]

    def say(self, text=""):
        self.lines.append(text)

    def run(self, tool, arguments, show=True):
        real = [sys.executable, "-B", tool] + [a.replace("JIRA", self.temp) for a in arguments]
        done = subprocess.run(real, cwd=PARTICIPANT, capture_output=True, text=True, timeout=120)
        output = (done.stdout + done.stderr).replace(self.temp, "JIRA")
        if show:
            self.say("$ python3 %s %s" % (tool, " ".join('"%s"' % a if " " in a else a for a in arguments)))
            self.say(BAR)
            self.lines += output.rstrip("\n").split("\n")
            self.say(BAR)
            self.say("exit code: %d" % done.returncode)
        return done.returncode, output

    def check(self, passed, what):
        self.checks += 1
        self.say("  %s %s" % ("ok  " if passed else "FAIL", what))
        if not passed:
            self.failed.append(what)

    def close(self):
        self.say("")
        self.say("RESULT: ALL CHECKS PASSED. %d checks." % self.checks if not self.failed else "RESULT: %d OF %d CHECKS FAILED: %s" % (len(self.failed), self.checks, "; ".join(self.failed)))
        with open(os.path.join(ATTEMPT, "logs", self.name), "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(self.lines) + "\n")
        print("%s: %s" % (self.name, self.lines[-1]))
        return not self.failed


def copy_now():
    with open(path_of(".json"), encoding="utf-8") as f:
        return json.load(f)


def page_now():
    with open(path_of(".md"), encoding="utf-8") as f:
        return f.read()


def made_up_texts():
    """The made-up Jira's comments as it starts out, read from the made-up Jira's own file: {identifier: text}."""
    sys.path.insert(0, os.path.join(PARTICIPANT, os.path.dirname(FAKE)))
    import fake_jira
    return {c["id"]: c["text"] for c in fake_jira.fresh()["comments"]}


def material_names_in_the_rules():
    """The names in the first table of the rules document, the one headed Material."""
    with open(os.path.join(PARTICIPANT, OUT, "history-rules.md"), encoding="utf-8") as f:
        text = f.read()
    table = text[text.index("## Material: kept"):text.index("## Noise: left out")]
    return [line.split("`")[1] for line in table.split("\n") if line.startswith("| `")]


def headings(page):
    return [line for line in page.split("\n") if line.startswith("### Comment ")]


def section(page, ident):
    start = page.index("### Comment %s" % ident)
    following = page.find("\n### Comment ", start + 1)
    return page[start:following if following != -1 else page.index("\n## Material changes")]


def main():
    if not os.path.isfile(path_of(".notes.md")):
        print("There is no notes file at %s/%s.notes.md. This script does not make one. Stopped." % (OUT, NAME))
        return 1
    temp = tempfile.mkdtemp(prefix="gtq-comments-record-")
    r = Record("sync-twice.txt", "Syncing a story's comments and material history: twice from unchanged data, then after an edit, an addition and a deletion", temp)
    n = Record("notes-intact.txt", "The local notes file, before and after every sync", temp)
    sync = ["sync", "--source", "fake", "--issue", "DEMO-7", "--out-dir", OUT, "--name", NAME, "--state", "JIRA"]
    notes = path_of(".notes.md")
    notes_start = (sha(notes), os.stat(notes).st_mtime_ns, os.stat(notes).st_size)
    n.say("The notes file is %s/%s.notes.md. It is the participant's. Neither the sync nor this script writes it." % (OUT, NAME))
    n.say("This script takes its sha256 itself, with Python's hashlib, before anything and after each sync. The sync prints the same")
    n.say("checksum on its own line, before and after; those lines are quoted too, so the two can be compared.")
    n.say("")
    n.say("Before any sync:   sha256 %s   %d bytes" % (notes_start[0], notes_start[2]))
    try:
        for ending in (".json", ".md"):
            if os.path.exists(path_of(ending)):
                os.unlink(path_of(ending))
        r.say("=" * 78)
        r.say("0. A FRESH MADE-UP STORY. The two files a sync writes were deleted first, so the first sync below is a first sync.")
        r.run(FAKE, ["new", "--state", "JIRA"])

        counted = []

        def one_sync(part, title, when):
            counted.append(when)
            number = len(counted)
            r.say("")
            r.say("=" * 78)
            r.say("%d. %s" % (part, title))
            code, out = r.run(TOOL, sync + ["--pretend-now", when])
            now = (sha(notes), os.stat(notes).st_mtime_ns, os.stat(notes).st_size)
            line = [l for l in out.split("\n") if l.strip().startswith("the notes")]
            n.say("")
            n.say("After sync %d:      sha256 %s   %d bytes" % (number, now[0], now[2]))
            n.say("  the sync's own line: %s" % (line[0].strip() if line else "NOT FOUND"))
            n.check(now == notes_start, "after sync %d the notes file has the same checksum, the same size and the same last-written time as before any sync" % number)
            n.check(len(line) == 1 and line[0].count(notes_start[0]) == 2 and "UNCHANGED" in line[0], "the sync's own line gives that same checksum twice, before and after, and says UNCHANGED")
            return code, out

        code, out = one_sync(1, "THE FIRST SYNC", TIMES[0])
        first = {e: sha(path_of(e)) for e in (".json", ".md")}
        r.check(code == 0 and "FIRST SYNC" in out, "exit code 0, and the output says it is a first sync")
        r.check({c["id"]: c["text"] for c in copy_now()["comments"]} == made_up_texts() and len(copy_now()["comments"]) == 5,
                "the copy holds five comments, and under each Jira identifier is the text the made-up Jira has for that identifier (criterion 1)")
        r.check(headings(page_now()) == ["### Comment %d" % i for i in range(31001, 31006)], "the page has one heading for each of the five identifiers, and no other comment heading")
        kinds = [h["kind"] for h in copy_now()["history"]]
        listed = material_names_in_the_rules()
        r.check(len(kinds) == 7 and len(listed) >= 5 and all(kind in listed for kind in kinds),
                "seven changes are kept from the history, of the kinds: %s. Every one is a name in the Material table of history-rules.md, which this script reads (criterion 5)" % ", ".join(kinds))
        r.check("noise, left out:                6" in out and "UNLISTED, on neither list, not kept: 1 (Story Points x1)" in out, "the output counts six changes left out as noise and names one field on neither list")
        r.check(not any(word in json.dumps(copy_now()) + page_now() for word in ("Ranked", "quarter-end", "Sprint", "made-up.png", "Story Points", "Example", "acct-", "old title", "new title")),
                "nothing of the noise, no person and no title is in the copy or the page: nine words from the made-up Jira were looked for")

        code, out = one_sync(2, "THE SECOND SYNC, FROM UNCHANGED DATA", TIMES[1])
        second = {e: sha(path_of(e)) for e in (".json", ".md")}
        r.check(code == 0 and "RESULT: NOTHING TO DO" in out, "the output says there was nothing to do")
        r.check(first == second, "the copy and the page have the same sha256 as after the first sync, taken by this script (criterion 2)")
        r.check(len(headings(page_now())) == 5 and len(set(headings(page_now()))) == 5 and len(copy_now()["comments"]) == 5,
                "counted directly as well, though it follows from the checksums: still five comments, each once")
        r.check(len(copy_now()["history"]) == 7 and len(set(h["id"] for h in copy_now()["history"])) == 7, "and still seven material changes, each once")

        r.say("")
        r.say("=" * 78)
        r.say("3. THE STORY CHANGES IN THE MADE-UP JIRA. These are the made-up Jira's own commands. The sync tool has no such commands.")
        old_text = [c for c in copy_now()["comments"] if c["id"] == "31002"][0]["text"]
        deleted_text = [c for c in copy_now()["comments"] if c["id"] == "31004"][0]["text"]
        r.run(FAKE, ["edit", "--state", "JIRA", "--id", "31002", "--text", "Made-up comment, corrected: archived orders are in a separate table. It is about two days, not one.", "--by", "other", "--at", "2026-11-08T08:00:00.000+0000"])
        r.run(FAKE, ["add", "--state", "JIRA", "--text", "Made-up comment: two days is still fine.", "--at", "2026-11-08T09:30:00.000+0000"])
        r.run(FAKE, ["delete", "--state", "JIRA", "--id", "31004"])
        r.run(FAKE, ["change", "--state", "JIRA", "--field", "status", "--from", "In Progress", "--to", "In Review", "--at", "2026-11-08T10:00:00.000+0000"])
        r.run(FAKE, ["change", "--state", "JIRA", "--field", "Rank", "--from", "", "--to", "Ranked higher", "--at", "2026-11-08T10:05:00.000+0000"])

        code, out = one_sync(4, "THE THIRD SYNC, AFTER THOSE CHANGES", TIMES[2])
        copy, page = copy_now(), page_now()
        by_id = {c["id"]: c for c in copy["comments"]}
        r.check(code == 0 and "RESULT: UP TO DATE. 1 added, 1 edited in place, 1 marked as not returned, 1 material change added." in out, "the output reports one added, one edited in place, one marked, one material change")
        id_list = [c["id"] for c in copy["comments"]]
        r.check(headings(page).count("### Comment 31002") == 1 and id_list.count("31002") == 1 and by_id["31002"]["first_synced"] == TIMES[0],
                "EDITED IN PLACE (criterion 3): comment 31002 is in the copy once and on the page once, and is still the entry first copied by sync 1, not a new one")
        r.check(by_id["31002"]["text"].startswith("Made-up comment, corrected") and old_text not in json.dumps(copy) + page, "its text is the new text, and the old text is nowhere in the copy or the page")
        edit = by_id["31002"]["edits"][0] if by_id["31002"]["edits"] else {}
        r.check(len(by_id["31002"]["edits"]) == 1 and edit.get("by") == "someone else" and edit.get("replaced_text_checksum") == hashlib.sha256(old_text.encode("utf-8")).hexdigest()[:16]
                and edit.get("seconds_until_noticed") == 4 * 3600
                and "**Edited in Jira** at 2026-11-08T08:00:00Z, by someone else. Noticed by the sync of %s, 4 hours later." % TIMES[2] in section(page, "31002"),
                "the change is noted, in the copy and under the comment on the page: edited by someone else, noticed 4 hours later, with a checksum that this script confirms is the old text's")
        r.check(headings(page).count("### Comment 31006") == 1 and id_list.count("31006") == 1 and by_id.get("31006", {}).get("first_synced") == TIMES[2]
                and by_id.get("31006", {}).get("text") == "Made-up comment: two days is still fine.",
                "ADDED ONCE (criterion 4): the new comment 31006 is in the copy once and on the page once, with the text that was added")
        gone = by_id.get("31004", {})
        r.check(gone.get("in_jira") is False and gone.get("text") == deleted_text and "NOT RETURNED BY JIRA ANY MORE" in section(page, "31004") and deleted_text in section(page, "31004"),
                "FLAGGED, NOT REMOVED (criterion 7): comment 31004 is still in the copy and on the page, marked, with its last text")
        r.check(page.count("NOT RETURNED BY JIRA ANY MORE") == 1 and all(c["in_jira"] for c in copy["comments"] if c["id"] != "31004"), "no other comment is marked")
        r.check(len(copy["comments"]) == 6 and len(set(headings(page))) == 6 and len(headings(page)) == 6, "six comments in all, each once")
        r.check([h["kind"] for h in copy["history"]].count("status") == 2 and len(copy["history"]) == 8 and "Ranked" not in json.dumps(copy) + page,
                "the status change was kept and the rank change was not (criterion 5)")
        r.say("")
        r.say("What the page now shows for the edited comment and the deleted one. All of it is made up.")
        r.say(BAR)
        r.lines += (section(page, "31002").rstrip("\n") + "\n\n" + section(page, "31004").rstrip("\n")).split("\n")
        r.say(BAR)

        third = {e: sha(path_of(e)) for e in (".json", ".md")}
        code, out = one_sync(5, "A FOURTH SYNC, FROM UNCHANGED DATA AGAIN", TIMES[3])
        r.check(code == 0 and "RESULT: NOTHING TO DO" in out and third == {e: sha(path_of(e)) for e in (".json", ".md")}, "nothing to do, and both files have the same sha256 as after the third sync")
        r.check([c for c in copy_now()["comments"] if c["id"] == "31004"][0].get("not_returned_since") == TIMES[2] and "marked by an earlier sync, still kept: 1" in out,
                "the deleted comment is still there, still marked with the sync that first found it gone, and was not marked again")
        r.say("")
        r.say("WHAT THIS DOES NOT SHOW. That a real Jira reports an edit or a deletion this way. No change was made in a real Jira.")
    finally:
        shutil.rmtree(temp, ignore_errors=True)
    end = (sha(notes), os.stat(notes).st_mtime_ns, os.stat(notes).st_size)
    n.say("")
    n.say("After every sync:  sha256 %s   %d bytes" % (end[0], end[2]))
    n.check(end == notes_start, "at the end the notes file has the checksum, size and last-written time it had at the start (criterion 6)")
    everything = os.listdir(os.path.join(PARTICIPANT, OUT))
    n.check(sorted(name for name in everything if name.startswith(NAME)) == [NAME + ".json", NAME + ".md", NAME + ".notes.md"],
            "the folder holds three files of this name: the copy, the page and the notes")
    n.check(not any(name.startswith(".sync-") for name in everything), "and no temporary file of the tool's (their names begin .sync-) is left in the folder")
    n.say("")
    n.say("WHAT THIS DOES NOT SHOW. That nothing else on the computer could change the notes. It shows that four syncs by this tool did not.")
    n.say("That the tool never OPENS the notes for writing is a test, which watches every open.")
    ok = [r.close(), n.close()]
    return 0 if all(ok) else 1


if __name__ == "__main__":
    sys.exit(main())
