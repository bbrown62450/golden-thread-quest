#!/usr/bin/env python3
"""The runs against the REAL Jira sandbox, in order, for the quest jira-link-work. A PERSON runs this, in their own
terminal, with JIRA_BASE_URL, JIRA_EMAIL and JIRA_API_TOKEN set there. The AI assistant does not run it.

    python3 live_run.py

It creates ONE link in the sandbox project, after you type the fingerprint of the preview you have read:

    SCRUM-1 blocks SCRUM-25

Only step 6 can write to Jira, and only after you type the fingerprint.

    1   preview with an allowlist that lists no project        refused
    2   preview                                                shown to you on screen. Read the sentence aloud
        ... you type the fingerprint, or press Return to stop with nothing written ...
    3   confirm with no fingerprint                            refused
    4   confirm a copy of the request, turned round            refused. The real request file is not touched
    5   confirm with the test clock 16 minutes on              refused
    6   CONFIRM                                                the link is created, and read back from both items
    7   check                                                  read back from both items again
    8   preview again                                          nothing to create
    9   confirm again with the used fingerprint                refused
    10  preview the same link said from the other item         already there, nothing to create
    11  preview the OPPOSITE link                              refused: a conflict
    12  preview a "duplicates" link                            refused: a type this workflow does not create

Steps 3, 4, 5 and 9 are run with the command that CAN write, and are expected to be refused before anything is sent.
If step 3, 5 or 9 were not refused, it would send the write you approved, once. If step 4 were not refused, it would
send the OPPOSITE link. It is refused because the turned-round file is not the file the preview showed, and that
refusal is one of the tested ones.

A step passes only if it ends with the status expected AND its output holds the words expected.

Each step's output is saved under logs/ as live-NN-*.txt with the site's address and the items' titles removed. The
state folder is local-data/jira-link-work/state, which Git ignores. If a step does not end as expected, the sequence
stops.

--rehearse runs the same sequence against the fake Jira in a temporary folder, saving nothing in the repository.
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
SKILL = os.path.join(PARTICIPANT, "skills", "jira-link-work")
TOOL = os.path.join(SKILL, "link_work.py")
CONTEXT = os.path.join(PARTICIPANT, "context", "jira")
PERSON = "the participant"


class Sequence:
    def __init__(self, rehearse):
        self.rehearse, self.number = rehearse, 0
        real = os.path.join(CONTEXT, "links")
        if rehearse:
            self.temp = tempfile.mkdtemp(prefix="gtq-rehearsal-")
            self.source, self.state, self.logs = "fake", os.path.join(self.temp, "state"), os.path.join(self.temp, "logs")
            self.requests = os.path.join(self.temp, "links")
            os.makedirs(self.requests)
            for name in ("link-request.json", "same-link-other-side.json", "opposite-link.json", "refused-type.json"):      # the real requests, with the fake's items
                with open(os.path.join(real, name), encoding="utf-8") as f:
                    text = f.read().replace("SCRUM-25", "SAND-2").replace("SCRUM-1", "SAND-1")
                with open(os.path.join(self.requests, name), "w", encoding="utf-8") as f:
                    f.write(text)
            self.allowlist = os.path.join(SKILL, "fixtures", "fake-allowlist.json")
            self.result = os.path.join(self.temp, "result.md")
        else:
            self.source, self.state, self.logs = "live", os.path.join(REPO, "local-data", "jira-link-work", "state"), os.path.join(ATTEMPT, "logs")
            self.requests, self.allowlist = real, os.path.join(CONTEXT, "update", "sandbox-allowlist.json")
            self.result = os.path.join(CONTEXT, "results", "link-work.md")
        self.request = os.path.join(self.requests, "link-request.json")
        self.empty = os.path.join(real, "empty-allowlist.json")

    def step(self, name, what, command, *extra, expect, words, show=False, request=None, allowlist=None):
        """Runs one command, saves its output, and stops the sequence if it did not end as expected."""
        self.number += 1
        log = os.path.join(self.logs, "live-%02d-%s.txt" % (self.number, name))
        args = [sys.executable, TOOL, command, "--source", self.source, "--state", self.state, "--log", log]
        if command != "check":
            args += ["--request", request or self.request, "--allowlist", allowlist or self.allowlist]
        done = subprocess.run(args + list(extra), capture_output=True, text=True)
        print("\n--- step %d: %s" % (self.number, what))
        if show:
            print(done.stdout)
        else:
            telling = [line.strip() for line in done.stdout.split("\n") if line.startswith(("REFUSED", "NOTHING TO CREATE", "A PERSON NEEDS", "FOUND", "NOT AS ASKED", "STOPPED"))]
            print("    " + (telling[0][:300] if telling else "(no line beginning REFUSED, NOTHING TO CREATE or FOUND)"))
        print("    exit status %d. Saved as logs/%s" % (done.returncode, os.path.basename(log)))
        if done.returncode != expect or words not in done.stdout:
            print("\nSTOPPED: this step was expected to end with status %d and to say: %s" % (expect, words))
            print("It ended with status %d%s. Nothing more is run." % (done.returncode, "" if words in done.stdout else ", and did not say that"))
            print("DO NOT DELETE ANYTHING, and do not run this again. Tell the assistant which step stopped.")
            sys.exit(1)
        return done.stdout

    def main(self):
        if os.path.exists(os.path.join(self.state, "written")) and os.listdir(os.path.join(self.state, "written")):
            print("STOPPED: an earlier run of this sequence already began writing. Nothing was run. DO NOT DELETE ANYTHING. Tell the assistant.")
            return 1
        self.step("refused-allowlist", "preview with an allowlist that lists no project. Expected: refused", "preview", expect=1, words="is not on the sandbox allowlist", allowlist=self.empty)
        text = self.step("preview", "the preview. READ IT, and read the sentence aloud", "preview", expect=0, words="IN WORDS:", show=True)
        found = re.findall(r"(?m)^Fingerprint of this preview: ([0-9a-f]{12})$", text)       # a line of its own, the last one: never text inside a title
        if not found:
            print("\nSTOPPED: the preview issued no fingerprint, so there is nothing to confirm. Nothing was written. Tell the assistant what it says.")
            return 1
        print("\n" + "=" * 78)
        print("The next steps include ONE REAL WRITE: the link said in words above, between the two items shown above.")
        print("If the preview is right, type its fingerprint and press Return. To stop with nothing written, just press Return.")
        try:
            typed = input("Fingerprint: ").strip().lower()
        except EOFError:
            typed = ""
        if typed != found[-1]:
            print("\nSTOPPED: %s. Nothing was written." % ("nothing was typed" if not typed else "what was typed is not this preview's fingerprint"))
            return 1
        code, who = typed, ["--confirmed-by", PERSON]
        self.step("refused-missing", "confirm with no fingerprint. Expected: refused", "confirm", *who, expect=1, words="no confirmation was given")
        with open(self.request, encoding="utf-8") as f:
            asked = json.load(f)["links"][0]
        turned = tempfile.mkdtemp(prefix="gtq-turned-")      # a copy with the same file name, in a folder of its own. The real request is not touched
        try:
            with open(os.path.join(turned, os.path.basename(self.request)), "w", encoding="utf-8") as f:
                json.dump({"links": [{"from": asked["to"], "phrase": asked["phrase"], "to": asked["from"]}]}, f)
            self.step("refused-differs", "confirm a copy of the request, turned round. Expected: refused", "confirm", "--fingerprint", code, *who, expect=1,
                      words="the change is not the one that was previewed", request=os.path.join(turned, os.path.basename(self.request)))
        finally:
            shutil.rmtree(turned, ignore_errors=True)
        self.step("refused-stale", "confirm with the test clock 16 minutes on. Expected: refused", "confirm", "--fingerprint", code, *who, "--pretend-minutes-later", "16", expect=1, words="this preview is too old")
        self.step("confirmation", "THE REAL WRITE. Expected: the link is created and read back from both items", "confirm", "--fingerprint", code, *who, "--result", self.result,
                  expect=0, words="ALL DONE: 1 link written, 0 already there.", show=True)
        self.step("check", "check: read the link back from both items again. Expected: found", "check", "--fingerprint", code, expect=0, words="FOUND: every link is there", show=True)
        self.step("rerun-preview", "preview again. Expected: nothing to create", "preview", expect=0, words="NOTHING TO CREATE")
        self.step("rerun-confirm", "confirm again with the used fingerprint. Expected: refused", "confirm", "--fingerprint", code, *who, expect=1, words="has been used")
        self.step("same-link-other-side", "preview the same link said from the other item. Expected: already there", "preview", expect=0, words="NOTHING TO CREATE", request=os.path.join(self.requests, "same-link-other-side.json"))
        self.step("refused-opposite", "preview the OPPOSITE link. Expected: refused, a conflict", "preview", expect=1, words="THE OPPOSITE LINK ALREADY EXISTS", request=os.path.join(self.requests, "opposite-link.json"))
        self.step("refused-type", "preview a 'duplicates' link. Expected: refused, a type this workflow does not create", "preview", expect=1, words="which this workflow does not create", request=os.path.join(self.requests, "refused-type.json"))
        print("\nONE THING ONLY YOU CAN CHECK. Open the first item of the link in Jira, in your browser, and look at its linked items.")
        print("Tell the assistant the words Jira shows there, above the other item: \"blocks\" or \"is blocked by\".")
        print("\nDONE. One link was created, once. Every step ended as expected.")
        return 0


if __name__ == "__main__":
    sequence = Sequence("--rehearse" in sys.argv)
    try:
        sys.exit(sequence.main())
    finally:
        if sequence.rehearse:
            shutil.rmtree(sequence.temp, ignore_errors=True)
