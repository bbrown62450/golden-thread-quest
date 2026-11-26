#!/usr/bin/env python3
"""The runs against the REAL Jira sandbox, in order, for the quest jira-idempotent-create. A PERSON runs this, in
their own terminal, with JIRA_BASE_URL, JIRA_EMAIL and JIRA_API_TOKEN set there. The AI assistant does not run it.

    python3 live_run.py            the main sequence. It creates ONE task in the sandbox project, after you type the
                                   fingerprint of the preview you have read
    python3 live_run.py after-edit after you have changed the task's title in Jira by hand: checks it is still found

What the main sequence does. Only step 6 can write to Jira, and only after you type the fingerprint.

    1  preview with an allowlist that lists no project      refused
    2  preview                                              shown to you on screen. Read it
       ... you type the fingerprint, or press Return to stop with nothing written ...
    3  confirm with no fingerprint                          refused
    4  confirm after the draft's title was changed          refused. The draft is then put back, byte for byte
    5  confirm with the test clock 16 minutes on            refused
    6  CONFIRM, stopped on purpose just after Jira answers  if Jira answers 201 the task exists, and nothing is recorded locally
    7  preview again                                        refused: the outcome is not known
    8  resolve, up to three times in the first half minute  finds the task by its key and records it
    9  preview, confirm, resolve and check, all again       nothing is created

Steps 3, 4, 5 and the second confirm in step 9 are run with the command that CAN write, and are expected to be
refused before anything is sent. If one were not refused, it would send the write you approved, once.
Step 8 never waits long enough for the workflow to give up looking: if the task is not found in half a minute, the
sequence stops and nothing is released.

Each step's output is saved under logs/ as live-NN-*.txt with the site's address removed. The state folder is
local-data/jira-idempotent-create/state, which Git ignores. If a step does not end as expected, the sequence stops.

--rehearse runs the same sequence against the fake Jira in a temporary folder, saving nothing in the repository.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ATTEMPT = os.path.dirname(HERE)
PARTICIPANT = os.path.abspath(os.path.join(ATTEMPT, "..", "..", ".."))
REPO = os.path.dirname(PARTICIPANT)
SKILL = os.path.join(PARTICIPANT, "skills", "jira-idempotent-create")
TOOL = os.path.join(SKILL, "create_once.py")
CONTEXT = os.path.join(PARTICIPANT, "context", "jira")
PERSON = "the participant"
WAIT = 15


class Sequence:
    def __init__(self, rehearse):
        self.rehearse, self.number = rehearse, 0
        if rehearse:
            self.temp = tempfile.mkdtemp(prefix="gtq-rehearsal-")
            self.source, self.state, self.logs = "fake", os.path.join(self.temp, "state"), os.path.join(self.temp, "logs")
            self.draft = os.path.join(SKILL, "fixtures", "export-archive.json")
            self.draft = shutil.copy(self.draft, self.temp)
            self.project = "SAND"
            self.allowlist = os.path.join(SKILL, "fixtures", "fake-allowlist.json")
            self.result = os.path.join(self.temp, "result.md")
        else:
            self.source, self.state, self.logs = "live", os.path.join(REPO, "local-data", "jira-idempotent-create", "state"), os.path.join(ATTEMPT, "logs")
            self.draft = os.path.join(CONTEXT, "idempotent", "created-once.json")
            self.project = "SCRUM"
            self.allowlist = os.path.join(CONTEXT, "update", "sandbox-allowlist.json")
            self.result = os.path.join(CONTEXT, "results", "idempotent-create.md")
        self.empty = os.path.join(CONTEXT, "idempotent", "empty-allowlist.json")

    def step(self, name, what, command, *extra, expect, show=False, draft=None, allowlist=None):
        """Runs one command, saves its output, and stops the sequence if it did not end as expected."""
        self.number += 1
        log = os.path.join(self.logs, "live-%02d-%s.txt" % (self.number, name))
        args = [sys.executable, TOOL, command, "--source", self.source, "--draft", draft or self.draft, "--state", self.state, "--log", log]
        if command in ("preview", "confirm"):
            args += ["--allowlist", allowlist or self.allowlist]
        done = subprocess.run(args + list(extra), capture_output=True, text=True)
        print("\n--- step %d: %s" % (self.number, what))
        if show:
            print(done.stdout)
        else:
            tail = [line for line in done.stdout.strip().split("\n") if line.strip()][-2:]
            print("    " + "\n    ".join(tail))
        print("    exit status %d. Saved as logs/%s" % (done.returncode, os.path.basename(log)))
        if done.returncode not in (expect if isinstance(expect, tuple) else (expect,)):
            print("\nSTOPPED: this step was expected to end with status %s. Nothing more is run." % (expect,))
            print("DO NOT DELETE ANYTHING, and do not run this again. Tell the assistant which step stopped.")
            sys.exit(1)
        return done.returncode, done.stdout

    def earlier_run(self):
        """What an earlier run of this sequence left, read from the draft's record: None, or words to stop with."""
        path = os.path.join(self.state, "intents", os.path.basename(self.draft))
        if not os.path.exists(path):
            return None
        try:
            with open(path, encoding="utf-8") as f:
                record = json.load(f)
            status, sent = record["status"], len(record["attempts"])
        except (ValueError, KeyError, TypeError):
            return "the draft's record from an earlier run cannot be read. DO NOT DELETE IT: it holds the key."
        if status == "new" and sent == 0:
            return None                      # an earlier run stopped before anything was sent. The same key is used again
        if status == "linked":
            return "the task was already created and recorded by an earlier run (%s). There is nothing to do." % record["issue"]["key"]
        return ("an earlier run sent a request and the record says '%s'. DO NOT DELETE ANYTHING and do not start again.\n"
                "The next step is `resolve`, which only searches. Tell the assistant." % status)

    def main(self):
        words = self.earlier_run()
        if words:
            print("STOPPED: " + words + " Nothing was run.")
            return 1
        self.step("refused-allowlist", "preview with an allowlist that lists no project. Expected: refused", "preview", expect=1, allowlist=self.empty)
        _, text = self.step("preview", "the preview. READ IT", "preview", expect=0, show=True)
        found = re.search(r"Fingerprint of this preview: ([0-9a-f]{12})", text)
        if not found:
            print("\nSTOPPED: the preview issued no fingerprint. Nothing was written. Tell the assistant what it says.")
            return 1
        print("\n" + "=" * 78)
        print("The next steps include ONE REAL WRITE: a new task in the project shown above, with the title shown above.")
        print("If the preview is right, type its fingerprint and press Return. To stop with nothing written, just press Return.")
        try:
            typed = input("Fingerprint: ").strip().lower()
        except EOFError:
            typed = ""
        if typed != found.group(1):
            print("\nSTOPPED: %s. Nothing was written." % ("nothing was typed" if not typed else "what was typed is not this preview's fingerprint"))
            return 1
        code = typed
        who = ["--confirmed-by", PERSON]
        self.step("refused-missing", "confirm with no fingerprint. Expected: refused", "confirm", *who, expect=1)
        with open(self.draft, "rb") as f:
            original = f.read()
        try:
            with open(self.draft, "w", encoding="utf-8") as f:
                json.dump({"project": self.project, "summary": json.loads(original.decode("utf-8"))["summary"] + " (changed after the preview)"}, f)
            self.step("refused-differs", "confirm after the draft's title was changed. Expected: refused", "confirm", "--fingerprint", code, *who, expect=1)
        finally:
            with open(self.draft, "wb") as f:
                f.write(original)
        self.step("refused-stale", "confirm with the test clock 16 minutes on. Expected: refused", "confirm", "--fingerprint", code, *who, "--pretend-minutes-later", "16", expect=1)
        _, text = self.step("confirm-interrupted", "THE REAL WRITE, stopped on purpose just after Jira answers. Expected: status 3", "confirm", "--fingerprint", code, *who,
                            "--interrupt-at", "after-send", expect=3, show=True)
        if "Jira answered 201." not in text:
            print("\nSTOPPED: Jira did not answer 201 to the write, so it is not known that the task was created. Nothing more is run.")
            print("DO NOT DELETE ANYTHING, and do not run this again. Tell the assistant what the line 'Jira answered' says.")
            return 1
        self.step("rerun-refused", "preview again, as a rerun would. Expected: refused, outcome not known", "preview", expect=1)
        for attempt in range(1, 4):
            status, text = self.step("resolve-%d" % attempt, "resolve: search Jira for the key. Expected: found (0), or not found yet (1)", "resolve", "--result", self.result, expect=(0, 1), show=True)
            if status == 0 or attempt == 3:
                break
            print("    Waiting %d seconds before searching again..." % WAIT)
            time.sleep(0 if self.rehearse else WAIT)
        if status != 0 or "FOUND BY ITS KEY" not in text:
            print("\nSTOPPED: the task was not found by its key in the first half minute. Nothing was created by these searches, and")
            print("the record has not been released. DO NOT DELETE ANYTHING. Tell the assistant: the next step is `resolve` again, later.")
            return 1
        self.step("rerun-preview", "preview again. Expected: nothing to create", "preview", expect=0)
        self.step("rerun-confirm", "confirm again with the used fingerprint. Expected: refused", "confirm", "--fingerprint", code, *who, expect=1)
        self.step("rerun-resolve", "resolve again. Expected: already recorded", "resolve", expect=0)
        self.step("check", "check the recorded task. Expected: there, and found by its key", "check", expect=0, show=True)
        print("\nDONE. One task was created, once. Every step ended as expected.")
        return 0

    def after_edit(self):
        self.number = 20
        self.step("check-after-edit", "check the task after its title was changed by hand. Expected: still found by its key", "check", expect=0, show=True)
        self.step("preview-after-edit", "preview again. Expected: nothing to create", "preview", expect=0)
        return 0


if __name__ == "__main__":
    sequence = Sequence("--rehearse" in sys.argv)
    try:
        sys.exit(sequence.after_edit() if "after-edit" in sys.argv else sequence.main())
    finally:
        if sequence.rehearse:
            shutil.rmtree(sequence.temp, ignore_errors=True)
