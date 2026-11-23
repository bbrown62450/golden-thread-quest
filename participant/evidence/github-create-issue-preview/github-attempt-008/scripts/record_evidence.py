#!/usr/bin/env python3
"""Records logs/preview-run.txt and logs/convention-refusal.txt for the github-create-issue-preview quest.

It also has the preview write participant/context/github/new-issue/payload.md.

Each block between dashed lines is what a command printed. Every command is
started as a person would start it. Nothing here contacts GitHub: every run is
against the made-up GitHub in participant/skills/github-create-issue-preview/fake_github.py,
which keeps its repositories in one file so that this script can open that file
before and after a preview. That file and the saved previews are in a scratch
folder that is thrown away, shown here as SCRATCH.

This script checks for itself. It reads the draft with its own few lines of
code and builds what the payload should be, takes its own SHA-256 of the bytes
the preview printed, and compares what the made-up GitHub holds before and
after, rather than taking the preview's word.

Run from anywhere:  python3 scripts/record_evidence.py
Exit code 0 if every check came out as expected, 1 if not.
"""
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ATTEMPT = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(ATTEMPT, "..", "..", "..", ".."))
SKILL = "participant/skills/github-create-issue-preview"
PREVIEW, FAKE = SKILL + "/preview.py", SKILL + "/fake_github.py"
FOLDER = "participant/context/github/new-issue"
DRAFT, PAYLOAD, ALLOWLIST = FOLDER + "/draft.md", FOLDER + "/payload.md", FOLDER + "/sandbox-allowlist.json"
INDEX = "participant/context/github/duplicates/fixture.md"
REPO = "acme-fixture/tracker"


class Log:
    scratch = None

    def __init__(self, title):
        self.lines, self.problems = [title], []
        self.out("Recorded by scripts/record_evidence.py. No request was sent to GitHub. The repository, people, labels, milestones and issues are made up.")

    def tidy(self, text):
        return text.replace(os.path.realpath(Log.scratch), "SCRATCH").replace(Log.scratch, "SCRATCH") if Log.scratch else text

    def out(self, text=""):
        self.lines.append(self.tidy(text))

    def part(self, text):
        self.lines += ["", "=" * 78, text]

    def check(self, label, ok):
        self.lines.append("  %-4s %s" % ("ok" if ok else "FAIL", label))
        if not ok:
            self.problems.append(label)

    def run(self, script, *args):
        done = subprocess.run([sys.executable, script] + list(args), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        self.out("$ python3 " + " ".join(shlex.quote(part) for part in [script] + list(args)))
        self.lines += ["-" * 78, self.tidy(done.stdout.rstrip("\n")), "-" * 78, "exit code: %s" % done.returncode]
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


class World:
    """One made-up GitHub in the scratch folder."""

    def __init__(self, name):
        self.folder = os.path.join(Log.scratch, name)
        os.makedirs(self.folder)
        self.store, self.state = os.path.join(self.folder, "github.json"), os.path.join(self.folder, "previews")
        subprocess.run([sys.executable, FAKE, self.store, "new"], stdout=subprocess.PIPE, check=True)

    def args(self, draft, *more):
        return ["--source", "fake", "--fake-store", self.store, "--draft", draft, "--index", INDEX, "--allowlist", ALLOWLIST, "--state", self.state] + list(more)

    def look(self):
        with open(self.store, encoding="utf-8") as f:
            store = json.load(f)
        return {"repos": store["repos"], "calls": store["calls"], "not_gets": [call for call in store["calls"] if call[0] != "GET"]}

    def saved(self):
        return sorted(os.listdir(self.state)) if os.path.isdir(self.state) else []


def own_draft(path):
    """The draft's front matter and body, read by this script's own code."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    head, rest = text[4:].split("\n---\n", 1)
    front = dict((line.split(": ", 1)[0], json.loads(line.split(": ", 1)[1])) for line in head.split("\n"))
    body = rest.split("\n## Body\n", 1)[1].split("\n## Sources\n", 1)[0]
    return front, body[body.index("### "):].strip("\n")


def bytes_shown(text):
    lines = text.splitlines()
    start = next(number for number, line in enumerate(lines) if "the exact bytes" in line)
    return lines[start + 1].split("github-preview:      ", 1)[1], re.search(r"SHA-256 ([0-9a-f]{64}):", lines[start]).group(1)


def unchanged(log, world, before, words="nothing was written: the made-up GitHub received no request but GETs, and holds exactly what it held before"):
    after = world.look()
    log.check(words, not after["not_gets"] and after["repos"] == before["repos"] and len(after["calls"]) > len(before["calls"]))


def preview_log():
    log = Log("The preview of a new issue. github-create-issue-preview, attempt github-attempt-008")
    if os.path.exists(PAYLOAD):
        os.remove(PAYLOAD)
    world = World("preview")
    log.part("PART 1. The made-up GitHub, and the draft")
    log.run(FAKE, world.store, "show")
    before = world.look()
    front, body = own_draft(DRAFT)
    log.out("The draft is %s. Read by this script: title %s, labels %s, assignees %s, milestone %s, template %s."
            % (DRAFT, json.dumps(front["title"]), json.dumps(front["labels"]), json.dumps(front["assignees"]), json.dumps(front["milestone"]), json.dumps(front["template"])))
    log.out("The duplicate search uses the index of the last quest, %s." % INDEX)

    log.part("PART 2. The preview")
    code, text = log.run(PREVIEW, *world.args(DRAFT, "--payload-out", PAYLOAD))
    log.check("exit code 0, and the run ends READY and says nothing has been written", code == 0 and "RESULT: READY. Nothing has been written" in text)
    log.check("the template was read from the repository, and all 3 required sections and the optional one are filled in (criterion 1)",
              "was read from the repository. It has 4 sections" in text and text.count("): filled in,") == 4 and "EMPTY" not in text and "MISSING" not in text)
    log.check("both labels, the assignee and the milestone were looked up and exist (criterion 2)",
              'label "bug": exists' in text and 'label "export": exists' in text and 'assignee "robin-fixture": can be assigned' in text and 'milestone "Sprint 13": exists, is open, number 3' in text)
    log.check("this script found them in the made-up GitHub's own file too", {"bug", "export"} <= {row["name"] for row in before["repos"][REPO]["labels"]}
              and "robin-fixture" in before["repos"][REPO]["assignable"] and {"number": 3, "title": "Sprint 13", "state": "open"} in before["repos"][REPO]["milestones"])
    log.check("the 6 source citations were each checked against the file and lines they name (criterion 7)",
              "4. SOURCES. 6 citations checked" in text and text.count("The words quoted are there") == 6)
    with open(os.path.join(FOLDER, "sources", "notes.md"), encoding="utf-8") as f:
        notes = f.read().split("\n")
    log.check("this script read line 7 of sources/notes.md itself, and the words cited for the title are on it", "The export writes dates in two different formats in the same file." == notes[6])
    log.check("the duplicate result appears in the preview: two weaker candidates, to link, and the result \"link\" (criterion 4)",
              "5. DUPLICATE CHECK." in text and text.count("     candidate acme-fixture/tracker#") == 2 and "duplicate result: link" in text and "close-as-duplicate" not in text)
    log.check("the permission check appears in the preview, with what GitHub does not say (criterion 4)",
              "6. PERMISSION CHECK." in text and "GitHub says the ACCOUNT may: admin: no, maintain: no, pull: yes, push: yes, triage: yes" in text and "does not say what the TOKEN may do" in text)

    log.part("PART 3. The exact payload (criterion 5)")
    shown, mark = bytes_shown(text)
    expected = {"title": front["title"], "body": body, "labels": front["labels"], "assignees": front["assignees"], "milestone": 3}
    log.out("This script built what the payload should be from the draft file with its own code: the title, the body between the")
    log.out("\"## Body\" and \"## Sources\" headings, the labels, the assignees, and the number of the milestone \"Sprint 13\", which is 3.")
    log.check("the bytes the preview printed are JSON, and hold exactly those five fields with exactly those values", json.loads(shown) == expected)
    log.check("it is the whole payload and not a summary: the body in it is all %d characters of the draft's body" % len(body), json.loads(shown)["body"] == body and len(body) > 400)
    log.check("the SHA-256 the preview printed is the SHA-256 of those bytes, worked out by this script: %s" % mark, hashlib.sha256(shown.encode("utf-8")).hexdigest() == mark)
    saved = world.saved()
    with open(os.path.join(world.state, saved[0]), encoding="utf-8") as f:
        record = json.load(f)["record"]
    log.check("the preview saved one record, under its fingerprint, and the payload in it is the same payload", len(saved) == 1 and saved[0] == record["fingerprint"] + ".json"
              and record["payload"] == expected and record["payload_sha256"] == mark and "FINGERPRINT of this preview: %s" % record["fingerprint"] in text)
    with open(PAYLOAD, encoding="utf-8") as f:
        payload_file = f.read()
    log.check("%s shows the repository, the request, each field, the body in full and the same bytes" % PAYLOAD,
              '- repository: "acme-fixture/tracker", id 401' in payload_file and "- request: `POST /repos/acme-fixture/tracker/issues`" in payload_file
              and shown in payload_file and body in payload_file and mark in payload_file and payload_file.count("| `") == 5)

    log.part("PART 4. The repository is unchanged (criterion 6)")
    log.run(FAKE, world.store, "show")
    after = world.look()
    log.out("This script opened the made-up GitHub's file before the preview and after it.")
    log.check("the made-up GitHub received %d requests during the preview, and every one was a GET" % (len(after["calls"]) - len(before["calls"])),
              not after["not_gets"] and len(after["calls"]) > len(before["calls"]))
    log.check("the number the preview printed is the number the made-up GitHub counted", "Requests made by this command: %d, every one a GET" % (len(after["calls"]) - len(before["calls"])) in text)
    log.check("everything the made-up GitHub holds for both repositories is identical before and after: issues, labels, milestones, templates", after["repos"] == before["repos"])
    log.check("the preview's own reading at the start and the end agrees: newest issue 107 then 107, 6 labels, 3 milestones",
              "Newest issue number: 107 then 107. Labels: 6 then 6. Milestones: 3 then 3. The same" in text)

    log.part("PART 5. A likely duplicate stops the preview, until a person says to go on")
    other = World("duplicate")
    before = other.look()
    code, text = log.run(PREVIEW, *other.args(FOLDER + "/draft-out-of-memory.md"))
    log.check("exit code 1: NOT READY, because the duplicate search reports tracker 101 at high confidence, open and in the same repository",
              code == 1 and "reports acme-fixture/tracker#101 as a LIKELY DUPLICATE at high confidence" in text and "RESULT: NOT READY. 1 reason:" in text)
    log.check("no fingerprint, no payload and no saved preview", "FINGERPRINT" not in text and "Not shown" in text and other.saved() == [])
    unchanged(log, other, before)
    code, text = log.run(PREVIEW, *other.args(FOLDER + "/draft-out-of-memory.md", "--despite-duplicate", "acme-fixture/tracker#101"))
    log.check("with a person's decision to go on, the preview is READY, and the decision is shown in it",
              code == 0 and "OVERRIDDEN BY A PERSON: the preview was told to go on despite acme-fixture/tracker#101" in text and "RESULT: READY" in text)
    with open(os.path.join(other.state, other.saved()[0]), encoding="utf-8") as f:
        record = json.load(f)["record"]
    log.check("the saved preview records the override, and the search's result, which is still close-as-duplicate",
              record["duplicate"]["overridden"] == ["acme-fixture/tracker#101"] and record["duplicate"]["result"] == "close-as-duplicate")
    return log.save("preview-run.txt")


def refusal_log():
    log = Log("Previews refused for breaking the repository's conventions. github-create-issue-preview, attempt github-attempt-008")
    cases = (
        ("PART 1. A required template section is empty", FOLDER + "/draft-empty-section.md",
         "In this draft the section \"Steps to reproduce\" holds only \"1.\", which is the template's own placeholder.",
         'the required template section "Steps to reproduce" is empty', 'section "Steps to reproduce" (required): EMPTY'),
        ("PART 2. A label does not exist", FOLDER + "/draft-unknown-label.md",
         "In this draft the labels are bug, export and data-quality. The repository has no label data-quality.",
         'the label "data-quality" does not exist in the repository. The preview does not invent labels', 'label "data-quality": DOES NOT EXIST in the repository'))
    for number, (title, draft, about, reason, line) in enumerate(cases, 1):
        log.part(title)
        log.out(about)
        world = World("refusal-%d" % number)
        before = world.look()
        code, text = log.run(PREVIEW, *world.args(draft))
        log.check("exit code 1, and the run ends NOT READY with 1 reason", code == 1 and "RESULT: NOT READY. 1 reason:" in text)
        log.check("the reason is given: %s" % reason.split(". ")[0], ("  1. " + reason) in text and line in text)
        log.check("no payload is shown, no fingerprint is given and no preview was saved, so there is nothing a write could send",
                  "7. THE EXACT PAYLOAD. Not shown" in text and "FINGERPRINT" not in text and world.saved() == [] and "nothing a write could send" in text)
        unchanged(log, world, before)
        if number == 2:
            log.check("the label was not created: the made-up repository still has its 6 labels", len(world.look()["repos"][REPO]["labels"]) == 6)
        if number == 1:
            log.check("the optional section, also left empty in this draft, is reported and is not a reason", 'section "Environment (optional)" (optional): EMPTY' in text)

    log.part("PART 3. A source citation that is not true")
    world = World("refusal-3")
    copy = os.path.join(world.folder, "new-issue")
    shutil.copytree(FOLDER, copy)
    with open(os.path.join(copy, "draft.md"), encoding="utf-8") as f:
        original = f.read()
    with open(os.path.join(copy, "draft.md"), "w", encoding="utf-8") as f:
        f.write(original.replace('line 12: "It should go in Sprint 13."', 'line 12: "It should go in Sprint 14."').replace('milestone: "Sprint 13"', 'milestone: "Sprint 14"'))
    log.out("In a scratch copy of the draft the milestone is changed to Sprint 14, and so is its citation. The notes still say Sprint 13.")
    before = world.look()
    code, text = log.run(PREVIEW, *world.args(os.path.join(copy, "draft.md")))
    log.check("exit code 1: the milestone exists, but the citation for it is NOT TRUE, and that is the reason",
              code == 1 and 'milestone "Sprint 14": exists, is open, number 4' in text and "the citation for milestone is NOT TRUE: the words quoted are not on line 12 of sources/notes.md" in text)
    unchanged(log, world, before)

    log.part("PART 4. A repository that is not on the sandbox allowlist")
    log.out("In the scratch copy the draft is put back as it was, and its repository is changed to acme-fixture/production, which exists")
    log.out("in the made-up GitHub and is not on the allowlist.")
    with open(os.path.join(copy, "draft.md"), "w", encoding="utf-8") as f:
        f.write(original.replace('repository: "acme-fixture/tracker"', 'repository: "acme-fixture/production"'))
    before = world.look()
    code, text = log.run(PREVIEW, *world.args(os.path.join(copy, "draft.md")))
    log.check("exit code 1: refused, and not one request of any kind was sent for it", code == 1 and "NOT ON THE SANDBOX ALLOWLIST" in text
              and len(world.look()["calls"]) == len(before["calls"]) and "Requests made by this command: 0" in text)
    return log.save("convention-refusal.txt")


def main():
    os.chdir(ROOT)
    with tempfile.TemporaryDirectory() as scratch:
        Log.scratch = scratch
        ok = preview_log()
        ok = refusal_log() and ok
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
