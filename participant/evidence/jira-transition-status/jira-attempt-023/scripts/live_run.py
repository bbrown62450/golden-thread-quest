#!/usr/bin/env python3
"""The runs against the REAL Jira sandbox, in order, for the quest jira-transition-status. A PERSON runs this, in
their own terminal, with JIRA_BASE_URL, JIRA_EMAIL and JIRA_API_TOKEN set there. The AI assistant does not run it.

    python3 live_run.py

It moves ONE item in the sandbox project to another status, after you type the fingerprint of the preview you have
read. The item and the status are in participant/context/jira/transition/move-request.json.

Only the step called CONFIRM can write to Jira, and only after you type the fingerprint.

    preview with an allowlist that lists no project        refused
    preview a move to a status Jira offers no move to      refused, before any preview
    preview closing an item that has an open subtask       refused, before any preview (only if close-parent.json is there)
    preview                                                shown to you on screen. Read it
        ... you type the fingerprint, or press Return to stop with nothing written ...
    confirm with no fingerprint                            refused
    confirm a changed copy of the request                  refused. The real request file is not touched
    confirm with the test clock 16 minutes on              refused
    CONFIRM                                                the item is moved, and its status is read back
    check                                                  the status is read back again
    preview again                                          nothing to do, and no fingerprint
    confirm again with the used fingerprint                refused
    rules                                                  the moves Jira offers for the item from its new status

WHAT THE SECOND STEP SHOWS, AND WHAT IT DOES NOT. It asks for a status Jira offers no move to from where the item
is. In a workflow where every status can be reached from every other, there is no move between two real statuses
that the workflow forbids, so the status asked for is one the workflow does not have. The refusal is the same code:
the status is not among those Jira offers.

The three confirm steps before CONFIRM, and the one after it, are run with the command that CAN write, and are
expected to be refused before anything is sent. If one of them, other than the changed copy, were not refused, it
would send the move you approved, once. The changed copy in step 5
asks for the same item to be given a status that does not exist, so that if it were not refused for being another
file, Jira would still have no such move to make.

A step passes only if it ends with the status expected AND its output holds the words expected.

Each step's output is saved under logs/ as live-NN-*.txt with the site's address and the item's title removed. The
state folder is local-data/jira-transition-status/state, which Git ignores. If a step does not end as expected, the
sequence stops. If you take more than 15 minutes to read the preview, CONFIRM is refused as too old and nothing is
written: tell the assistant, and the sequence is run again from the start.

The saved outputs do not hold the site's address, by this project's rule for evidence. They hold a short fingerprint
of its name. The address is shown to you on screen in the preview.

--rehearse runs the same sequence against the made-up Jira in a temporary folder, saving nothing in the repository.
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
REPO = os.path.dirname(PARTICIPANT)
SKILL = os.path.join(PARTICIPANT, "skills", "jira-transition-status")
TOOL = os.path.join(SKILL, "transition.py")
CONTEXT = os.path.join(PARTICIPANT, "context", "jira")
PERSON = "the participant"
TELLING = ("REFUSED", "NOTHING TO DO", "ALREADY DONE", "A PERSON NEEDS", "FOUND", "NOT AS INTENDED", "STOPPED", "ALL DONE")


class Sequence:
    def __init__(self, rehearse):
        self.rehearse, self.number = rehearse, 0
        real = os.path.join(CONTEXT, "transition")
        if rehearse:
            self.temp = tempfile.mkdtemp(prefix="gtq-rehearsal-")
            self.source, self.state, self.logs = "fake", os.path.join(self.temp, "state"), os.path.join(self.temp, "logs")
            self.requests = os.path.join(self.temp, "transition")
            os.makedirs(self.requests)
            os.makedirs(self.logs)
            for name, item in (("move-request.json", "SAND-1"), ("not-a-move.json", "SAND-1"), ("close-parent.json", "SAND-2")):       # the real requests, with the made-up Jira's items
                if not os.path.exists(os.path.join(real, name)):
                    continue
                with open(os.path.join(real, name), encoding="utf-8") as f:
                    asked = json.load(f)
                with open(os.path.join(self.requests, name), "w", encoding="utf-8") as f:
                    json.dump({"issue": item, "to": asked["to"]}, f)
            self.allowlist = os.path.join(SKILL, "fixtures", "fake-allowlist.json")
            self.result, self.rules_after = os.path.join(self.temp, "result.md"), os.path.join(self.temp, "rules-after.md")
        else:
            self.source, self.state, self.logs = "live", os.path.join(REPO, "local-data", "jira-transition-status", "state"), os.path.join(ATTEMPT, "logs")
            self.requests, self.allowlist = real, os.path.join(CONTEXT, "update", "sandbox-allowlist.json")
            self.result, self.rules_after = os.path.join(CONTEXT, "results", "transition-status.md"), os.path.join(real, "rules-sandbox-after.md")
        self.request = os.path.join(self.requests, "move-request.json")
        self.empty = os.path.join(real, "empty-allowlist.json")
        with open(self.request, encoding="utf-8") as f:
            self.asked = json.load(f)

    def step(self, name, what, command, *extra, expect, words, show=False, request=None, allowlist=None, first=False, absent=None):
        """Runs one command, saves its output, and stops the sequence if it did not end as expected."""
        self.number += 1
        log = os.path.join(self.logs, "live-%02d-%s.txt" % (self.number, name))
        args = [sys.executable, "-B", TOOL, command, "--source", self.source, "--log", log]
        if command != "rules":
            args += ["--state", self.state]
        if command in ("preview", "confirm"):
            args += ["--request", request or self.request, "--allowlist", allowlist or self.allowlist]
        done = subprocess.run(args + list(extra), capture_output=True, text=True, stdin=None)
        print("\n--- step %d: %s" % (self.number, what))
        if show:
            print(done.stdout)
        else:
            telling = [line.strip() for line in done.stdout.split("\n") if line.startswith(TELLING)]
            print("    " + (telling[0][:300] if telling else "(no line beginning REFUSED, NOTHING TO DO or FOUND)"))
        print("    exit status %d. Saved as logs/%s" % (done.returncode, os.path.basename(log)))
        said = done.stdout.startswith(words) if first else any(line.strip().startswith(words) for line in done.stdout.split("\n"))      # at the start of a line: never inside a title
        if absent and any(line.startswith(absent) for line in done.stdout.split("\n")):
            said = False
        if done.returncode != expect or not said:
            print("\nSTOPPED: this step was expected to end with status %d and to say: %s" % (expect, words))
            print("It ended with status %d%s. Nothing more is run." % (done.returncode, "" if said else ", and did not say that (or said something it should not)"))
            print("DO NOT DELETE ANYTHING, and do not run this again. Tell the assistant which step stopped.")
            sys.exit(1)
        return done.stdout

    def shown_key(self):
        return "SAND-1" if self.rehearse else self.asked["issue"]

    def main(self):
        if os.path.exists(os.path.join(self.state, "written")) and os.listdir(os.path.join(self.state, "written")):
            print("STOPPED: an earlier run of this sequence already began writing. Nothing was run. DO NOT DELETE ANYTHING. Tell the assistant.")
            return 1
        os.makedirs(self.state, exist_ok=True)
        self.step("refused-allowlist", "preview with an allowlist that lists no project. Expected: refused", "preview", expect=1, words="REFUSED: %s is in project" % self.shown_key(), allowlist=self.empty)
        self.step("refused-not-allowed", "preview a move to a status the workflow has no move to. Expected: refused before any preview", "preview", expect=1,
                  words="REFUSED: THE WORKFLOW DOES NOT ALLOW THIS MOVE.", request=os.path.join(self.requests, "not-a-move.json"))
        if os.path.exists(os.path.join(self.requests, "close-parent.json")):
            self.step("refused-open-subtask", "preview closing an item that has an open subtask. Expected: refused before any preview", "preview", expect=1,
                      words="REFUSED: THIS WORKFLOW DOES NOT MAKE THIS MOVE.", request=os.path.join(self.requests, "close-parent.json"))
        text = self.step("preview", "the preview. READ IT: the item, the status now, the status after", "preview", expect=0, words="PREVIEW. Nothing has been written.", show=True, first=True)
        found = re.findall(r"(?m)^Fingerprint of this preview: ([0-9a-f]{12})$", text)       # a line of its own, the last one: never text inside a title
        if not found:
            print("\nSTOPPED: the preview issued no fingerprint, so there is nothing to confirm. Nothing was written. Tell the assistant what it says.")
            return 1
        print("\n" + "=" * 78)
        print("The next steps include ONE REAL WRITE: the item shown above is moved to the status shown above.")
        print("If the preview is right, type its fingerprint and press Return. To stop with nothing written, just press Return.")
        try:
            typed = input("Fingerprint: ").strip().lower()
        except EOFError:
            typed = ""
        if typed != found[-1]:
            print("\nSTOPPED: %s. Nothing was written." % ("nothing was typed" if not typed else "what was typed is not this preview's fingerprint"))
            return 1
        code, who = typed, ["--confirmed-by", PERSON]
        self.step("refused-missing", "confirm with no fingerprint. Expected: refused", "confirm", *who, expect=1, words="REFUSED: no confirmation was given")
        changed = tempfile.mkdtemp(prefix="gtq-changed-")      # a copy with the same file name, in a folder of its own. The real request is not touched
        try:
            with open(os.path.join(changed, os.path.basename(self.request)), "w", encoding="utf-8") as f:
                json.dump({"issue": self.asked["issue"], "to": "A status that does not exist"}, f)
            self.step("refused-differs", "confirm a changed copy of the request. Expected: refused", "confirm", "--fingerprint", code, *who, expect=1,
                      words="REFUSED: the change is not the one that was previewed", request=os.path.join(changed, os.path.basename(self.request)))
        finally:
            shutil.rmtree(changed, ignore_errors=True)
        self.step("refused-stale", "confirm with the test clock 16 minutes on. Expected: refused", "confirm", "--fingerprint", code, *who, "--pretend-minutes-later", "16", expect=1, words="REFUSED: this preview is too old")
        self.step("confirmation", "THE REAL WRITE. Expected: the item is moved and its status is read back", "confirm", "--fingerprint", code, *who, "--result", self.result,
                  expect=0, words="ALL DONE: %s was moved from" % self.shown_key(), show=True)
        try:
            with open(self.result, encoding="utf-8") as f:
                kept = f.read().startswith("# Result record: one Jira item moved to another status")
        except OSError:
            kept = False
        if not kept:
            print("\nSTOPPED: the move was made, and the result record was not saved where it should be. DO NOT DELETE ANYTHING. Tell the assistant.")
            return 1
        self.step("check", "check: read the status back again. Expected: found", "check", "--fingerprint", code, expect=0, words="FOUND: the item has the status intended.", show=True)
        self.step("rerun-preview", "preview again. Expected: nothing to do", "preview", expect=0, words="NOTHING TO DO. Nothing has been written.", first=True, absent="Fingerprint of this preview:")
        self.step("rerun-confirm", "confirm again with the used fingerprint. Expected: refused", "confirm", "--fingerprint", code, *who, expect=1, words="REFUSED: the preview %s has been used" % code)
        self.step("rules-after", "the moves Jira offers for the item from its new status. Reads only", "rules", "--issue", self.shown_key(), "--out", self.rules_after, expect=0, words="TRANSITION RULES.", first=True)
        print("\nDONE. One item was moved, once. Every step ended as expected.")
        return 0


if __name__ == "__main__":
    sequence = Sequence("--rehearse" in sys.argv)
    try:
        sys.exit(sequence.main())
    finally:
        if sequence.rehearse:
            shutil.rmtree(sequence.temp, ignore_errors=True)
