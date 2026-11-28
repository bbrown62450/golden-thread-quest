#!/usr/bin/env python3
"""Makes the records for the quest jira-transition-status, against the MADE-UP Jira. No real Jira is contacted.

    logs/invalid-transition.txt   moves that are refused before any preview, and the status read back after an approved one
    logs/preview.txt              the workflow stopping at a preview, with the made-up Jira unchanged
    logs/confirmation.txt         four refusals, then the approved run
    logs/rerun.txt                the approved workflow run again
    participant/context/jira/transition/rules.md      the moves read from the made-up workflow for five sample items

Each command is run as a person would run it, from the `participant` folder, and its output is copied in whole. The
state folder is a temporary one outside the repository; in the records it is written $STATE.

TWO KINDS OF CHECK, and each says which it is. A check that says "the made-up Jira's own state file" was made by
this script opening that file and reading: each item's status and resolution, its history entries, the writes (POSTs)
the made-up Jira received and the reads (GETs) it received. "Nothing written" means that file, leaving out its list
of reads, is exactly what it was. A check that says "the tool says" or "the output" looks only at what the tool
printed, and shows that the words are there, not that they are true.

Run from anywhere:  python3 scripts/record_evidence.py        Exit code 0 if every check passed, 1 if not.
"""
import hashlib
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
SKILL = "skills/jira-transition-status"
TOOL, FAKE = SKILL + "/transition.py", SKILL + "/fake_jira.py"
FIX = SKILL + "/fixtures"
ALLOW = FIX + "/fake-allowlist.json"
RULES = "context/jira/transition/rules.md"
BAR = "-" * 78
STATUS = {"10000": "To Do", "10001": "In Progress", "10002": "In Review", "10003": "Done", "10004": "Closed"}


class Record:
    def __init__(self, name, title):
        self.name, self.checks, self.failed = name, 0, []
        self.state = os.path.join(tempfile.mkdtemp(prefix="gtq-transition-record-"), "state")
        os.makedirs(self.state)
        self.lines = [title, "jira-transition-status, attempt jira-attempt-023. Recorded by scripts/record_evidence.py.",
                      "Against the made-up Jira (skills/jira-transition-status/fake_jira.py). Every item is made up. No real Jira was contacted.",
                      "Commands are run from the `participant` folder. $STATE is a temporary folder outside the repository.", ""]

    def say(self, text=""):
        self.lines.append(text)

    def part(self, title):
        self.say("")
        self.say("=" * 78)
        self.say(title)

    def run(self, tool, arguments, show=True):
        done = subprocess.run([sys.executable, "-B", tool] + arguments, cwd=PARTICIPANT, capture_output=True, text=True, timeout=120)
        output = (done.stdout + done.stderr).replace(self.state, "$STATE").replace(os.path.dirname(self.state), "$TEMP")
        if show:
            self.say("$ python3 %s %s" % (tool, " ".join(a if " " not in a else '"%s"' % a for a in arguments).replace(self.state, "$STATE").replace(os.path.dirname(self.state), "$TEMP")))
            self.say(BAR)
            self.lines += output.rstrip("\n").split("\n")
            self.say(BAR)
            self.say("exit code: %d" % done.returncode)
        return done.returncode, output

    def tool(self, command, *arguments):
        extra = [] if command == "rules" else ["--state", self.state]
        return self.run(TOOL, [command, "--source", "fake"] + extra + list(arguments))

    def fake(self, *arguments):
        return self.run(FAKE, list(arguments) + ["--state", self.state])

    def held(self):
        """The made-up Jira's own state file, read by this script: (sha256 of the file, {key: (status, resolution, history entries)}, POSTs received)."""
        path = os.path.join(self.state, "fake-jira.json")
        if not os.path.exists(path):
            self.run(FAKE, ["show", "--state", self.state], show=False)
        with open(path, "rb") as f:
            raw = f.read()
        state = json.loads(raw.decode("utf-8"))
        self.gets = state.pop("gets")                # the reads it received. Left out of the comparison: a read changes nothing
        self.history = {i["key"]: [entry["id"] for entry in i["history"]] for i in state["issues"]}
        kept = json.dumps(state, sort_keys=True).encode("utf-8")
        return hashlib.sha256(kept).hexdigest(), {i["key"]: (STATUS[i["status"]], i["resolution"], len(i["history"])) for i in state["issues"]}, state["posts"]

    def saved_previews(self):
        folder = os.path.join(self.state, "previews")
        return sorted(os.listdir(folder)) if os.path.isdir(folder) else []

    def check(self, passed, what):
        self.checks += 1
        self.say("  %s %s" % ("ok  " if passed else "FAIL", what))
        if not passed:
            self.failed.append(what)

    def unchanged(self, before, what):
        after = self.held()
        self.say("  The made-up Jira's own state file (without its list of reads), sha256 before %s, after %s. POSTs it has received: %d." % (before[0][:16], after[0][:16], len(after[2])))
        self.check(after[0] == before[0], "NOTHING WRITTEN: %s, the made-up Jira's own state file holds exactly what it held" % what)

    def close(self):
        self.say("")
        self.say("RESULT: ALL CHECKS PASSED. %d checks." % self.checks if not self.failed else "RESULT: %d OF %d CHECKS FAILED: %s" % (len(self.failed), self.checks, "; ".join(self.failed)))
        with open(os.path.join(ATTEMPT, "logs", self.name), "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(self.lines) + "\n")
        print("%s: %s" % (self.name, self.lines[-1]))
        shutil.rmtree(os.path.dirname(self.state), ignore_errors=True)
        return not self.failed


def fingerprint_in(output):
    found = re.search(r"^Fingerprint of this preview: ([0-9a-f]{12})$", output, re.M)
    return found.group(1) if found else None


def request(name):
    return ["--request", "%s/%s.json" % (FIX, name), "--allowlist", ALLOW]


def refused_before_preview(r, name, words, why):
    before, previews = r.held(), r.saved_previews()
    code, out = r.tool("preview", *request(name))
    r.check(code == 1 and "REFUSED: " in out and words in out, "exit code 1, and the reason is given: %s" % why)
    r.check("PREVIEW." not in out and fingerprint_in(out) is None and r.saved_previews() == previews,
            "REFUSED BEFORE THE PREVIEW (criterion 2): no preview was shown, no fingerprint issued, and no preview file saved, so there is nothing that could be confirmed")
    r.unchanged(before, "after the refusal")


def invalid_transition():
    r = Record("invalid-transition.txt", "Moves that are refused before any preview, and the status read back after an approved move")
    r.part("0. What the made-up Jira holds at the start")
    r.fake("show")
    r.part("1. A MOVE THE WORKFLOW DOES NOT ALLOW: SAND-1 is To Do, and the request asks for Done. The made-up workflow has no such move.")
    refused_before_preview(r, "skip-to-done", "THE WORKFLOW DOES NOT ALLOW THIS MOVE.", "Jira offers no move from To Do to Done, and the moves it does offer are named")
    r.part("2. A MOVE THE WORKFLOW ALLOWS AND THIS TOOL REFUSES: closing SAND-2, which has an open subtask (SAND-4)")
    refused_before_preview(r, "close-with-open-subtask", "it leads to a done status while 1 subtask is not done (SAND-4)", "a subtask is not done, and it is named")
    r.say("")
    r.say("Would the made-up Jira itself have accepted that move? In a second, throwaway copy of it, the move is made directly, without the tool:")
    other = os.path.join(os.path.dirname(r.state), "throwaway")
    code, out = r.run(FAKE, ["move", "--issue", "SAND-2", "--transition", "31", "--state", other])
    r.check(code == 0 and "Someone else moved SAND-2" in out, "yes: the made-up Jira's workflow accepts closing SAND-2 with its subtask open. Only the tool stood in the way. (This is the quest's scenario.)")
    r.part("3. Closing SAND-8, one of whose subtasks has a status that cannot be read")
    refused_before_preview(r, "close-unreadable-subtask", '"Could not check" is not "none open"', "the subtask's status could not be read")
    r.part("4. A move with a required field: SAND-5 to Closed, which asks for a resolution")
    refused_before_preview(r, "close-needs-resolution", "it asks for 1 required field (resolution)", "the move has a required field, which is named")
    r.part("5. AN APPROVED MOVE, AND THE STATUS READ BACK: SAND-1 from To Do to In Progress")
    code, out = r.tool("preview", *request("start-work"))
    fingerprint = fingerprint_in(out)
    r.check(code == 0 and fingerprint is not None, "the preview was made, with a fingerprint")
    code, out = r.tool("confirm", *request("start-work"), "--fingerprint", fingerprint or "none", "--confirmed-by", "the participant")
    _, items, posts = r.held()
    r.say("  The made-up Jira's own state file, read by this script: SAND-1 has the status %s, %d history entr%s. POSTs received: %d." % (items["SAND-1"][0], items["SAND-1"][2], "y" if items["SAND-1"][2] == 1 else "ies", len(posts)))
    r.check(code == 0 and 'the status of SAND-1 is "In Progress" (status id 10001). Intended: "In Progress" (status id 10001): yes' in out,
            "THE STATUS READ BACK MATCHES THE INTENDED ONE (criterion 3): the tool read SAND-1 back after the write and says In Progress, as intended")
    r.check(items["SAND-1"][0] == "In Progress" and len(posts) == 1, "and the made-up Jira's own state file agrees: SAND-1 is In Progress, after one POST")
    r.part("6. The status read back again, by the command that only reads")
    code, out = r.tool("check", "--fingerprint", fingerprint or "none")
    r.check(code == 0 and "FOUND: the item has the status intended." in out and len(r.held()[2]) == 1, "the check command finds the status intended, and sent no write")
    r.part("7. THE REST OF THE QUEST'S SCENARIO: closing an item, and reading the resolution back")
    r.say("7a. SAND-5, whose one subtask is done. The made-up workflow sets a resolution when an item is approved.")
    code, out = r.tool("preview", *request("close-all-subtasks-done"))
    code, out = r.tool("confirm", *request("close-all-subtasks-done"), "--fingerprint", fingerprint_in(out) or "none", "--confirmed-by", "the participant")
    _, items, posts = r.held()
    r.check(code == 0 and items["SAND-5"][:2] == ("Done", "Done") and 'the resolution is set: "Done": yes' in out,
            "exit code 0. The made-up Jira's own state file: SAND-5 is Done with the resolution Done; and the tool says it read the resolution back as set")
    r.say("")
    r.say("7b. SAND-7, whose workflow sets NO resolution when it is approved. The move is legal, and it leaves the item done with no resolution.")
    code, out = r.tool("preview", *request("close-bare-workflow"))
    code, out = r.tool("confirm", *request("close-bare-workflow"), "--fingerprint", fingerprint_in(out) or "none", "--confirmed-by", "the participant")
    _, items, posts = r.held()
    r.check(items["SAND-7"][:2] == ("Done", None), "the made-up Jira's own state file: SAND-7 is Done and its resolution is empty")
    r.check(code == 2 and "THE RESOLUTION IS EMPTY" in out and "A PERSON NEEDS TO LOOK:" in out and "THE ITEM IS IN A DONE STATUS WITH NO RESOLUTION." in out and "ALL DONE" not in out,
            "exit code 2, not 0: the tool read the resolution back, found none, said so in capitals, and did not say ALL DONE. The move itself cannot be known to do this before it is made")
    r.say("")
    r.say("WHAT THIS DOES NOT SHOW. A real Jira. The made-up workflow is a model: the real one is read in the real run.")
    return r.close()


def preview():
    r = Record("preview.txt", "The workflow stopping at a preview, with nothing written")
    r.part("0. What the made-up Jira holds before the preview")
    r.fake("show")
    before = r.held()
    r.part("1. THE PREVIEW: SAND-1 from To Do to In Progress")
    code, out = r.tool("preview", *request("start-work"))
    r.check(code == 0 and "PREVIEW. Nothing has been written." in out, "exit code 0, and it stops at a preview")
    r.check("Jira site:  https://fixture-site.example.invalid  (site fingerprint 738169e667642f09)" in out and "Project:    SAND (project id 20001). On the sandbox allowlist: yes." in out,
            "THE PREVIEW SHOWS THE SITE AND THE PROJECT (criterion 4)")
    r.check('Status now:    "To Do" (status id 10000' in out and 'Status after:  "In Progress" (status id 10001' in out and "transition id 11, for issue id 30001" in out,
            "AND THE EXACT CHANGE (criterion 4): the status now, the status after, and exactly what would be sent")
    r.held()
    asked = r.gets.count("/rest/api/3/issue/30001/transitions")
    r.say("  The made-up Jira's own list of the reads it received holds the request for SAND-1's moves %d times, and the permission request %d times." % (asked, r.gets.count("/rest/api/3/mypermissions")))
    r.check(asked == 2 and "By the move:   \"Start progress\" (Jira's transition id 11)" in out,
            "THE MOVE WAS READ FROM THE WORKFLOW (criterion 1): the made-up Jira's own state file shows it was asked for this item's moves, once for each of the preview's two looks; and the move the preview names, id 11, is the one the made-up workflow has from To Do")
    r.check("Permission check, asked of Jira for this item and this identity (may see it / may move it): yes / yes" in out and r.gets.count("/rest/api/3/mypermissions") == 2,
            "THE PERMISSION CHECK IS RECORDED (criterion 5): the output gives its result, and the made-up Jira's own state file shows it was asked. Here it can only read yes / yes: a no is a refusal, shown in part 3")
    r.check("Duplicate check, made against Jira just now: the item's status is \"To Do\", which is not the status asked for." in out and "Where Jira cannot check:" in out,
            "THE DUPLICATE CHECK IS RECORDED, with a statement of where Jira cannot check (criterion 5)")
    r.check(fingerprint_in(out) is not None and "Expires: " in out and "(15 minutes after it was made)" in out, "the preview has a fingerprint and a stated time limit (criterion 7)")
    r.check("Every one was a GET, which reads and cannot change anything." in out and "POST" not in out, "every request the preview sent was a GET")
    r.part("2. What the made-up Jira holds after the preview")
    r.fake("show")
    r.unchanged(before, "after the preview (criterion 4)")
    snapshots = re.findall(r"^Snapshot of the item, as Jira returned it, (?:before|after) the preview: +([0-9a-f]{16})$", out, re.M)
    r.check(len(snapshots) == 2 and snapshots[0] == snapshots[1], "the tool says its own before-and-after snapshots of the item are the same: %s. (It would refuse otherwise; the check that Jira is unchanged is the one above, on the state file)" % " and ".join(snapshots))
    r.part("3. THE PERMISSION CHECK, WHEN THE ANSWER IS NO. The made-up Jira is told that this identity may not move items")
    r.fake("set", "--no-permission")
    before = r.held()
    code, out = r.tool("preview", *request("start-work"))
    r.check(code == 1 and "Jira says this identity may not move SAND-1 (TRANSITION_ISSUES: no)" in out and fingerprint_in(out) is None, "exit code 1 and no fingerprint: Jira says this identity may not move the item (criterion 5)")
    r.unchanged(before, "after the refusal")
    return r.close()


def confirmation():
    r = Record("confirmation.txt", "Four refusals with nothing written, then the approved run")
    r.part("0. A preview is made and read")
    code, out = r.tool("preview", *request("start-work"))
    fingerprint = fingerprint_in(out) or "none"
    before = r.held()
    r.say("  Each of the four refusals below is made with the command that CAN write. If one were not refused, it would send a write.")

    r.part("1. REFUSED: A MISSING CONFIRMATION. The confirm command with no fingerprint")
    code, out = r.tool("confirm", *request("start-work"), "--confirmed-by", "the participant")
    r.check(code == 1 and "REFUSED: no confirmation was given." in out, "exit code 1: no confirmation was given (criterion 7)")
    r.unchanged(before, "after the refusal")

    r.part("2. REFUSED: A CHANGE THAT DIFFERS FROM THE PREVIEW. A request file of the same name that asks for another item to be moved")
    changed = os.path.join(os.path.dirname(r.state), "changed")
    os.makedirs(changed)
    with open(os.path.join(changed, "start-work.json"), "w", encoding="utf-8") as f:
        json.dump({"issue": "SAND-9", "to": "In Progress"}, f)
    r.say("  $TEMP/changed/start-work.json holds: %s" % json.dumps({"issue": "SAND-9", "to": "In Progress"}))
    code, out = r.tool("confirm", "--request", os.path.join(changed, "start-work.json"), "--allowlist", ALLOW, "--fingerprint", fingerprint, "--confirmed-by", "the participant")
    r.check(code == 1 and "the change is not the one that was previewed" in out, "exit code 1: the change is not the one that was previewed (criterion 7)")
    r.unchanged(before, "after the refusal")
    r.check(r.held()[1]["SAND-9"][0] == "To Do", "and SAND-9, which the changed request named, is still To Do")

    r.part("3. REFUSED: A PREVIEW OLDER THAN THE TIME LIMIT. The test clock is moved 16 minutes on; the limit is 15")
    code, out = r.tool("confirm", *request("start-work"), "--fingerprint", fingerprint, "--confirmed-by", "the participant", "--pretend-minutes-later", "16")
    r.check(code == 1 and "this preview is too old. It was made 16 minutes ago and the limit is 15" in out, "exit code 1: the preview is too old (criterion 7)")
    r.unchanged(before, "after the refusal")

    r.say("  The limit is tested here with the tool's own test clock, which can only make a preview older. No record waits 15 real minutes.")

    r.part("3b. REFUSED: A FINGERPRINT THAT IS NOT THIS PREVIEW'S, and a saved preview that was altered")
    wrong = "0123456789ab" if fingerprint != "0123456789ab" else "ba9876543210"
    code, out = r.tool("confirm", *request("start-work"), "--fingerprint", wrong, "--confirmed-by", "the participant")
    r.check(code == 1 and "there is no preview with the fingerprint %s" % wrong in out, "exit code 1: a well-formed fingerprint that belongs to no preview is refused")
    r.unchanged(before, "after the refusal")
    saved_path = os.path.join(r.state, "previews", fingerprint + ".json")
    with open(saved_path, encoding="utf-8") as f:
        original = f.read()
    altered = json.loads(original)
    altered["proposal"]["to"] = {"id": "10003", "name": "Done", "category": "done"}
    with open(saved_path, "w", encoding="utf-8") as f:
        json.dump(altered, f)
    r.say("  This script now edits the saved preview %s, so that it says the status after is Done, and confirms it with its own fingerprint:" % fingerprint)
    code, out = r.tool("confirm", *request("start-work"), "--fingerprint", fingerprint, "--confirmed-by", "the participant")
    r.check(code == 1 and "has been altered since it was made" in out, "exit code 1: what the saved preview holds no longer matches its fingerprint (criterion 7)")
    r.unchanged(before, "after the refusal")
    with open(saved_path, "w", encoding="utf-8") as f:
        f.write(original)
    r.say("  The saved preview is put back as it was.")

    r.part("4. REFUSED: A PROJECT THAT IS NOT ON THE SANDBOX ALLOWLIST")
    r.say("4a. A preview for PROD-1, in a project the allowlist does not list:")
    code, out = r.tool("preview", *request("other-project"))
    r.check(code == 1 and "is not on the sandbox allowlist" in out and fingerprint_in(out) is None, "exit code 1 and no fingerprint: the project is not on the allowlist (criterion 6)")
    r.say("4b. The approved preview, confirmed with an allowlist that lists no project:")
    empty = os.path.join(os.path.dirname(r.state), "empty-allowlist.json")
    with open(empty, "w", encoding="utf-8") as f:
        json.dump({"sandbox_projects": []}, f)
    code, out = r.tool("confirm", "--request", FIX + "/start-work.json", "--allowlist", empty, "--fingerprint", fingerprint, "--confirmed-by", "the participant")
    r.check(code == 1 and "is not on the sandbox allowlist" in out, "exit code 1: with no project listed, the confirmation is refused too (criterion 6)")
    r.unchanged(before, "after both refusals")
    r.check(len(r.held()[2]) == 0, "after all the refusals above the made-up Jira's own state file shows it has received no POST at all")

    r.part("5. THE APPROVED RUN: the confirmation names the preview's fingerprint, and the write happens in the same run")
    result = os.path.join(os.path.dirname(r.state), "result.md")
    code, out = r.tool("confirm", *request("start-work"), "--fingerprint", fingerprint, "--confirmed-by", "the participant", "--result", result)
    _, items, posts = r.held()
    r.check(code == 0 and "CONFIRMATION for preview %s, given by: the participant" % fingerprint in out,
            "the approved run was given the fingerprint %s, that of the preview in part 0, and its output names it. That the fingerprint MATTERS is shown by parts 1, 2, 3 and 3b, where without it, or with another, or with an altered preview, nothing was written" % fingerprint)
    r.check(len(before[2]) == 0 and len(posts) == 1,
            "GIVEN IN THE SAME SESSION AS THE WRITE (criterion 7): the made-up Jira's own state file shows no POST before this one command and one POST after it. The confirmation was an argument of that command")
    r.check(posts == [{"path": "/rest/api/3/issue/30001/transitions", "body": {"transition": {"id": "11"}}}],
            "the made-up Jira received exactly one POST, and its body is the move's id and nothing else: %s" % json.dumps(posts[0]["body"] if posts else None))
    r.check(items["SAND-1"] == ("In Progress", None, 1) and all(items[key][2] == 0 for key in items if key != "SAND-1"),
            "the made-up Jira's own state file: SAND-1 is In Progress with one history entry, and no other item has any")
    r.check('Intended: "In Progress" (status id 10001): yes' in out, "the status read back matches the intended one (criterion 3)")
    with open(result, encoding="utf-8") as f:
        record = f.read()
    r.say("")
    r.say("The result record the run saved (this one is of the made-up Jira; the one handed in is of the real run):")
    r.lines += ["  | " + line for line in record.rstrip("\n").split("\n")]
    entry = r.history["SAND-1"][0] if len(r.history["SAND-1"]) == 1 else "none"
    r.say("  The made-up Jira's own state file: SAND-1's one history entry has the id %s." % entry)
    r.check(all(word in record for word in ("- Issue key: SAND-1", "- Identifier of what was changed: Jira history entry %s\n" % entry, "- Target project: SAND (project id 20001)", "- Confirmed by: the participant, at "))
            and re.search(r"^- Written at: 20[0-9]{2}-[0-9]{2}-[0-9]{2} [0-9:]{8} UTC$", record, re.M) is not None,
            "THE RESULT RECORD (criterion 8) holds the issue key, the project, a time, the name given with the confirmation, and as the identifier of what was changed the id of the history entry the made-up Jira itself made: %s" % entry)
    return r.close()


def rerun():
    r = Record("rerun.txt", "The approved workflow run a second time")
    r.part("0. The approved run, once")
    code, out = r.tool("preview", *request("start-work"))
    first = fingerprint_in(out) or "none"
    time.sleep(1.1)                 # so that the second preview is made at another second and has another fingerprint
    r.say("")
    r.say("A second preview of the same request is made before the first is confirmed, as a person who asked twice might:")
    code, out = r.tool("preview", *request("start-work"))
    second = fingerprint_in(out) or "none"
    r.check(first != second and "none" not in (first, second), "two previews, two fingerprints: %s and %s" % (first, second))
    code, out = r.tool("confirm", *request("start-work"), "--fingerprint", first, "--confirmed-by", "the participant")
    after_first = r.held()
    r.check(code == 0 and after_first[1]["SAND-1"] == ("In Progress", None, 1) and len(after_first[2]) == 1, "the first is confirmed: SAND-1 is In Progress, one history entry, one POST")

    r.part("1. THE SAME CONFIRMATION AGAIN, with the fingerprint that was used")
    code, out = r.tool("confirm", *request("start-work"), "--fingerprint", first, "--confirmed-by", "the participant")
    r.check(code == 1 and "has been used (recorded as 'written'). A fingerprint is used once" in out, "exit code 1: a fingerprint is used once")
    r.unchanged(after_first, "after the refusal")

    r.part("2. THE WHOLE WORKFLOW AGAIN: a new preview of the same request")
    code, out = r.tool("preview", *request("start-work"))
    r.check(code == 0 and 'SAND-1 ALREADY HAS THE STATUS "In Progress"' in out and fingerprint_in(out) is None, "the preview finds the item already has the status, and issues no fingerprint: there is nothing to confirm")
    r.unchanged(after_first, "after the second preview")

    r.part("3. THE OTHER PREVIEW, made before the move and still within its time limit, is confirmed now")
    r.say("This is the case a used-fingerprint rule does not cover: a valid, unused confirmation for a move that has already been made.")
    code, out = r.tool("confirm", *request("start-work"), "--fingerprint", second, "--confirmed-by", "the participant")
    r.check(code == 0 and "ALREADY DONE. Nothing was sent." in out and "POST" not in out, "exit code 0: the tool read the item first, found the status already there, and sent nothing")
    now = r.held()
    r.check(now[1] == after_first[1] and len(now[2]) == 1, "NO REPEATED CHANGE (criterion 9): the made-up Jira's own state file still shows one history entry on SAND-1 and one POST in all")
    code, out = r.tool("confirm", *request("start-work"), "--fingerprint", second, "--confirmed-by", "the participant")
    r.check(code == 1 and "has been used" in out, "and that second fingerprint is now used up as well")

    r.part("4. A CONFLICTING CHANGE: someone else moves the item after a preview, and the preview is then confirmed")
    code, out = r.tool("preview", "--request", FIX + "/close-all-subtasks-done.json", "--allowlist", ALLOW)
    third = fingerprint_in(out) or "none"
    r.fake("move", "--issue", "SAND-5", "--transition", "32")
    before = r.held()
    code, out = r.tool("confirm", "--request", FIX + "/close-all-subtasks-done.json", "--allowlist", ALLOW, "--fingerprint", third, "--confirmed-by", "the participant")
    r.check(code == 1 and "THE ITEM HAS BEEN MOVED SINCE THE PREVIEW." in out, "exit code 1: the item no longer has the status the preview showed")
    r.unchanged(before, "after the refusal")
    r.part("5. What the made-up Jira holds at the end")
    r.fake("show")
    r.check(len(r.held()[2]) == 1, "in the whole of this record the made-up Jira received one POST: the approved move")
    r.say("")
    r.say("THE LIMIT (criterion 9). Jira's request to move an item has no 'only if its status is still this' condition. Between the tool's last")
    r.say("read and its write there is a moment in which someone else could move the item. In the made-up workflow a move is open from one")
    r.say("status only, so the made-up Jira would refuse it then. A real workflow may offer the same move from every status; there Jira would")
    r.say("not refuse, and only the tool's own look before the write stands in the way. A person would notice in the output, which reads the")
    r.say("status back and looks for one new history entry, and in the item's history in Jira. That is this script's statement, not something it tested.")
    r.say("One run at a time may confirm a request in one state folder on one computer. Nothing stops a run on another computer.")
    return r.close()


def rules():
    r = Record("rules-run.txt", "The moves read from the made-up workflow for five sample items")
    r.part("The rules page is written from what the made-up Jira answers. Five items, in four statuses.")
    path = os.path.join(PARTICIPANT, RULES)
    if os.path.exists(path):
        os.unlink(path)
    code, out = r.tool("rules", "--issue", "SAND-1", "--issue", "SAND-4", "--issue", "SAND-2", "--issue", "SAND-5", "--issue", "SAND-3", "--out", RULES)
    with open(path, encoding="utf-8") as f:
        page = f.read()
    sys.path.insert(0, os.path.join(PARTICIPANT, SKILL))
    import fake_jira
    rows = re.findall(r'^\| "([^"]+)" \(([0-9]+)\) \| "([^"]+)" \| "([^"]+)" ', page, re.M)
    r.say("  Rows in the page's tables: %d. Moves in the made-up workflow that start at the four statuses read: %d." % (len(rows), 1 + 2 + 3 + 3 + 1))
    listed = {"SAND-1": "10000", "SAND-4": "10001", "SAND-2": "10002", "SAND-5": "10002", "SAND-3": "10003"}
    want = sorted((move[0], move_id, STATUS[move[1]], STATUS[move[2]]) for status in listed.values() for move_id, move in fake_jira.MOVES.items() if move[1] == status)
    r.check(code == 0 and sorted(rows) == want, "THE MOVES WERE READ FROM THE WORKFLOW (criterion 1): the page lists, for each item, every move the made-up workflow has from that item's status, and no other. Compared with the workflow by this script")
    verdicts = {}
    for section in page.split("\n## ")[1:]:
        for move_id, verdict in re.findall(r'^\| "[^"]+" \(([0-9]+)\) \|(?:[^|]*\|){4} (yes|\*\*no\*\*)', section, re.M):
            verdicts[(section.split(",")[0], move_id)] = verdict == "yes"
    refused = sorted(key for key, supported in verdicts.items() if not supported)
    r.check(len(verdicts) == 10 and refused == [("SAND-2", "31"), ("SAND-2", "33"), ("SAND-5", "33")],
            "of the ten, seven are supported and three are not: closing SAND-2 (an open subtask) and the move with a required field, on each of the two items it is offered for")
    r.check("`resolution`" in page and "`assignee`" in page and "1 subtask is not done (SAND-4)" in page, "required and optional fields are named, and the open subtask is named")
    r.check("fixture-site.example.invalid" not in page and "POST" not in out, "the page holds no site address, and no write was sent")
    return r.close()


def main():
    good = [rules(), invalid_transition(), preview(), confirmation(), rerun()]
    return 0 if all(good) else 1


if __name__ == "__main__":
    sys.exit(main())
