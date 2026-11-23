#!/usr/bin/env python3
"""Records the four logs of the github-update-metadata quest, and writes two of its files.

    logs/preview.txt        the workflow stopping at a preview
    logs/confirmation.txt   the approved run, and four refusals
    logs/stale-run.txt      an update refused because a field changed on GitHub after the preview
    logs/rerun.txt          the approved workflow run a second time
    participant/context/github/update/supported-fields.md     the supported fields, with two runs in it
    participant/context/github/results/update-metadata.md     the result record of the approved run

Each block between dashed lines is what a command printed. Every command is
started as a person would start it. Nothing here contacts GitHub: every run is
against the made-up GitHub in participant/skills/github-update-metadata/fake_github.py,
which keeps its repositories in one file so that a preview and its confirmation
can be two separate commands. That file and the saved previews are in a scratch
folder that is thrown away, shown here as SCRATCH.

This script checks for itself. After each command it opens the made-up
GitHub's file and looks at what the repository holds and at every request it
received, rather than taking the workflow's word.

Run from anywhere:  python3 scripts/record_evidence.py
Exit code 0 if every check came out as expected, 1 if not.
"""
import contextlib
import io
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ATTEMPT = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(ATTEMPT, "..", "..", "..", ".."))
SKILL = "participant/skills/github-update-metadata"
UPDATE, FAKE = SKILL + "/update.py", SKILL + "/fake_github.py"
ALLOWLIST = "participant/context/github/update/sandbox-allowlist.json"
SUPPORTED_DOC = "participant/context/github/update/supported-fields.md"
RESULT = "participant/context/github/results/update-metadata.md"

sys.path.insert(0, os.path.join(ROOT, SKILL))
import fake_github  # noqa: E402
import update  # noqa: E402
from fake_github import ISSUE, OTHER, REPO  # noqa: E402

CHANGES = ["label.add=in progress", "label.remove=needs triage", "label.add=bug", "milestone.set=Sprint 13"]
NAME = "the participant"


class Log:
    scratch = None

    def __init__(self, title):
        self.lines, self.problems = [title], []
        self.out("Recorded by scripts/record_evidence.py. No request was sent to GitHub. The repositories, people, labels and issues are made up.")

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

    def run(self, argv):
        done = subprocess.run([sys.executable] + argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        self.out("$ python3 " + " ".join(shlex.quote(part) for part in argv))
        self.lines += ["-" * 78, self.tidy(done.stdout.rstrip("\n")), "-" * 78, "exit code: %s" % done.returncode]
        return done.returncode, done.stdout

    def world(self, world, *command):
        return self.run([FAKE, world.store] + list(command))

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
    """One made-up GitHub in the scratch folder, with its own folder for saved previews."""

    def __init__(self, name):
        self.folder = os.path.join(Log.scratch, name)
        os.makedirs(self.folder)
        self.store, self.state = os.path.join(self.folder, "github.json"), os.path.join(self.folder, "previews")
        self.results = os.path.join(self.folder, "results")
        with contextlib.redirect_stdout(io.StringIO()):
            fake_github.main([self.store, "new"])

    def argv(self, command, changes, repo=REPO, results=None, more=()):
        argv = [UPDATE, command, "--source", "fake", "--fake-store", self.store, "--repo", repo, "--issue", str(ISSUE)]
        for change in changes:
            argv += ["--change", change]
        argv += ["--allowlist", ALLOWLIST, "--state", self.state]
        return argv + (["--results", results or self.results] if command == "confirm" else []) + list(more)

    def look(self):
        """What the made-up GitHub holds now, read from its file by this script."""
        with open(self.store, encoding="utf-8") as f:
            store = json.load(f)
        calls = store["calls"]
        return {"repos": store["repos"], "calls": calls, "writes": [call for call in calls if call[0] != "GET"],
                "issue": store["repos"][REPO]["issues"][str(ISSUE)]}

    def previews(self):
        return sorted(os.listdir(self.state)) if os.path.isdir(self.state) else []


def mark_in(text):
    found = re.search(r"FINGERPRINT of this preview: ([0-9a-f]{32})", text)
    return found.group(1) if found else None


def confirmation(mark, name=NAME):
    return ["--fingerprint", mark, "--confirmed-by", name]


def requests_in(text, heading):
    """The request lines under one numbered heading of the workflow's output."""
    lines, found, inside = text.splitlines(), [], False
    for line in lines:
        body = line.split("github-update: ", 1)[-1]
        if body.startswith(heading):
            inside = True
        elif inside and re.match(r"     (POST|PATCH|DELETE|PUT) /", body):
            found.append(body.strip().split(" -> ")[0])
        elif inside and re.match(r"\d+\. |RESULT", body):
            break
    return found


def as_lines(calls):
    return ["%s %s%s" % (method, path, " " + json.dumps(body) if body is not None else "") for method, path, body in calls]


def unchanged(log, world, before, what="nothing was written: the made-up GitHub received no write, and both repositories are exactly as they were"):
    after = world.look()
    log.check(what, len(after["writes"]) == len(before["writes"]) and after["repos"] == before["repos"])


# ---------------------------------------------------------------- logs/preview.txt


def preview_log(world):
    log = Log("The workflow stopping at a preview. github-update-metadata, attempt github-attempt-005")
    log.part("PART 1. The made-up GitHub before anything is asked")
    log.world(world, "show")
    before = world.look()
    log.out("The sandbox allowlist is %s. It names: %s." % (ALLOWLIST, ", ".join(allowlist())))

    log.part("PART 2. The preview")
    log.out("Four changes are asked for. One of them, adding the label \"bug\", is already so.")
    code, text = log.run(world.argv("preview", CHANGES))
    mark = mark_in(text)
    after = world.look()
    log.check("exit code 0, and the run ends READY and says nothing has been written", code == 0 and "RESULT: READY. Nothing has been written" in text)
    log.check("it shows the repository, its id, the issue and the account (criterion 4)",
              '1. WHERE. Repository "%s", id 401, private. Issue %d,' % (REPO, ISSUE) in text and 'acts as login "robin-fixture"' in text)
    log.check("it shows the old and the new value of labels, assignees and milestone (criterion 1)",
              'old:       labels     ["bug", "needs triage"]' in text and 'new:       labels     ["bug", "in progress"]' in text
              and text.count('assignees  ["robin-fixture"]') == 2 and 'milestone  "Sprint 12" (number 1)' in text and 'milestone  "Sprint 13" (number 3)' in text)
    log.check("the old values it shows are what the made-up GitHub holds: this script read them from its file",
              sorted(before["issue"]["labels"]) == ["bug", "needs triage"] and before["issue"]["assignees"] == ["robin-fixture"] and before["issue"]["milestone"] == 1)
    wanted = ['POST /repos/%s/issues/%d/labels {"labels": ["in progress"]}' % (REPO, ISSUE), "DELETE /repos/%s/issues/%d/labels/needs%%20triage" % (REPO, ISSUE),
              'PATCH /repos/%s/issues/%d {"milestone": 3}' % (REPO, ISSUE)]
    log.check("it shows the exact changes as the 3 requests a confirmation would send (criterion 4)", requests_in(text, "5. EXACT REQUESTS") == wanted)
    log.check("it records the permission check, and states what GitHub cannot say: what the token may do (criterion 5)",
              "6. PERMISSION CHECK. GitHub says the ACCOUNT may change issues here" in text and "does not say what the TOKEN may do" in text)
    log.check("it records the duplicate check: 1 change is already so and is not sent, and it states that GitHub would not refuse a repeat (criterion 5)",
              'label.add="bug": ALREADY SO' in text and "Already so, and not sent: 1." in text and "GitHub does not refuse a repeated change of this kind itself" in text)
    log.check("it gives a fingerprint of the preview: %s" % mark, bool(mark) and world.previews() == [mark + ".json"])
    log.check("it says how long the fingerprint is good for: 15 minutes, once", "It can be confirmed once, for 15 minutes" in text)

    log.part("PART 3. Before and after: the repository is unchanged")
    log.world(world, "show")
    log.out("This script opened the made-up GitHub's file before the preview and after it.")
    log.check("the made-up GitHub received %d requests during the preview, and every one was a GET" % (len(after["calls"]) - len(before["calls"])),
              len(after["calls"]) > len(before["calls"]) and all(call[0] == "GET" for call in after["calls"]))
    log.check("the number the preview printed is the number the made-up GitHub counted", "Requests made by this command: %d, every one a GET" % (len(after["calls"]) - len(before["calls"])) in text)
    unchanged(log, world, before, "everything the made-up GitHub holds for both repositories (issues, labels, milestones, events) is identical before and after")
    log.check("the preview's own before-and-after reading of the issue agrees", bool(re.search(r"before: (\w{16})\. After: \1\. The same", text)))
    return log.save("preview.txt"), mark, text


# ---------------------------------------------------------------- logs/confirmation.txt


def confirmation_log(world, mark, preview_text):
    log = Log("The approved run, and four refusals. github-update-metadata, attempt github-attempt-005")
    log.out("The approved run continues from logs/preview.txt: the same made-up GitHub and the preview with fingerprint %s." % mark)
    result = os.path.join(ROOT, RESULT)
    if os.path.exists(result):
        os.remove(result)

    log.part("PART 1. The approved run: the confirmation and the write, in one command")
    before = world.look()
    code, text = log.run(world.argv("confirm", CHANGES, results=os.path.dirname(RESULT), more=confirmation(mark)))
    after = world.look()
    log.check("exit code 0, and the run ends DONE", code == 0 and "RESULT: DONE" in text)
    log.check("the confirmation names a person and the fingerprint of the preview, and is given in the command that writes (criterion 7)",
              '1. CONFIRMATION. Given by "%s", for the preview with fingerprint %s, in this same command' % (NAME, mark) in text)
    log.check("the run checked that nothing had moved before it wrote (criterion 3)", "5. HAS ANYTHING MOVED? No." in text)
    sent = as_lines(after["writes"][len(before["writes"]):])
    log.check("the writes the made-up GitHub received are exactly the %d requests the preview showed, in the same order" % len(sent),
              sent == requests_in(preview_text, "5. EXACT REQUESTS") and len(sent) == 3)
    log.check("every write went to issue %d of %s, and none to any other place" % (ISSUE, REPO),
              all(call[1].startswith("/repos/%s/issues/%d" % (REPO, ISSUE)) for call in after["writes"]))
    log.check("the issue now holds what the preview promised: labels bug and in progress, milestone number 3, the same assignee",
              sorted(after["issue"]["labels"]) == ["bug", "in progress"] and after["issue"]["milestone"] == 3 and after["issue"]["assignees"] == ["robin-fixture"])
    log.check("no label was sent as part of a whole list: each request carries one label", all(len((call[2] or {}).get("labels", [0])) == 1 for call in after["writes"]))
    log.check("the result record was written: %s" % RESULT, os.path.exists(result) and ("## Update " + mark) in open(result, encoding="utf-8").read())

    refusals = (
        ("PART 2. Refusal 1 of 4: a missing confirmation", [], CHANGES, REPO, "NO CONFIRMATION was given", 0),
        ("PART 3. Refusal 2 of 4: a change that differs from the preview", None, CHANGES + ["label.remove=bug"], REPO, "THE CHANGE DIFFERS FROM THE PREVIEW", 0),
        ("PART 4. Refusal 3 of 4: a preview older than the time limit", None, CHANGES, REPO, "THE PREVIEW HAS EXPIRED", 16),
        ("PART 5. Refusal 4 of 4: a repository that is not on the sandbox allowlist", None, CHANGES, OTHER, "NOT ON THE SANDBOX ALLOWLIST", 0))
    for number, (title, given, changes, repo, words, minutes) in enumerate(refusals, 1):
        log.part(title)
        fresh = World("refusal-%d" % number)
        log.out("A fresh made-up GitHub, and a fresh preview of the same four changes:")
        _, shown = log.run(fresh.argv("preview", CHANGES))
        other = mark_in(shown)
        if minutes:
            log.world(fresh, "advance", str(minutes))
        if repo == OTHER:
            log.out("The made-up GitHub also has %s, which exists and is not on the allowlist. The confirmation is pointed at it:" % OTHER)
        before = fresh.look()
        code, text = log.run(fresh.argv("confirm", changes, repo=repo, more=confirmation(other) if given is None else given))
        log.check("exit code 1, refused with the words \"%s\", and the run says nothing was written" % words, code == 1 and words in text and "Nothing was written." in text)
        unchanged(log, fresh, before)
        if repo == OTHER:
            log.check("not one request of any kind was sent to GitHub for it: the made-up GitHub's count did not move", len(fresh.look()["calls"]) == len(before["calls"])
                      and "No request was sent to GitHub" in text)
        if minutes:
            log.check("the age is measured on GitHub's clock: 16 minutes against a limit of 15", "16 minutes, and the limit is 15" in text)
        if "DIFFERS" in words:
            log.check("the refusal names the change that was not in the preview", 'Asked for now and not in the preview: ["label.remove=bug"]' in text)
        if given == []:
            log.check("the refusal comes before any request is sent", len(fresh.look()["calls"]) == len(before["calls"]))
        log.check("no result record was written", not os.path.exists(os.path.join(fresh.results, "update-metadata.md")))
    return log.save("confirmation.txt")


# ---------------------------------------------------------------- logs/rerun.txt


def rerun_log(world, mark):
    log = Log("The approved workflow run a second time. github-update-metadata, attempt github-attempt-005")
    log.out("This continues from logs/confirmation.txt, part 1: the same made-up GitHub, after the approved update was made.")
    result = os.path.join(ROOT, RESULT)
    log.part("PART 1. The made-up GitHub after the approved run")
    log.world(world, "show")
    before = world.look()
    events = len(before["repos"][REPO]["events"][str(ISSUE)])
    record = open(result, encoding="utf-8").read()

    log.part("PART 2. The very same approved command, run again")
    code, text = log.run(world.argv("confirm", CHANGES, results=os.path.dirname(RESULT), more=confirmation(mark)))
    log.check("exit code 1: the preview was ALREADY USED, and the run says when and by whom", code == 1 and "this preview was ALREADY USED, at " in text and 'confirmed by "%s"' % NAME in text)
    unchanged(log, world, before)
    log.check("it was refused before any request was sent", len(world.look()["calls"]) == len(before["calls"]))

    log.part("PART 3. The whole workflow again from the start: a new preview of the same changes")
    code, text = log.run(world.argv("preview", CHANGES))
    log.check("exit code 0, and the run ends NOTHING TO CHANGE: every value asked for is already there", code == 0 and "RESULT: NOTHING TO CHANGE" in text)
    log.check("each of the 4 changes is reported ALREADY SO, and 0 requests would be sent", text.count("ALREADY SO") == 4 and "in this order: 0" in text)
    log.check("no fingerprint is given, so there is nothing that could be confirmed: the only saved preview is the used one", mark_in(text) is None and world.previews() == [mark + ".json"])
    unchanged(log, world, before)

    log.part("PART 4. What a repeat would have looked like, and what there is instead")
    after = world.look()
    log.world(world, "show")
    log.check("the made-up GitHub received 3 writes in all, the ones of the approved run, and none since", len(after["writes"]) == 3)
    log.check("the issue has %d events, as it had after the approved run: no second \"labeled\" or \"milestoned\" event" % events,
              len(after["repos"][REPO]["events"][str(ISSUE)]) == events)
    log.check("the issue has the label \"in progress\" once, and the labels and milestone the approved run left",
              after["issue"]["labels"].count("in progress") == 1 and after["issue"] == before["issue"])
    log.check("the result record still has one section, and is byte for byte what the approved run wrote", open(result, encoding="utf-8").read() == record and record.count("## Update ") == 1)
    log.out("Where GitHub cannot prevent a repeat: GitHub accepts the same label, assignee or milestone a second time and changes")
    log.out("nothing, so a repeated request would do no harm. It is still never sent, because the preview compares first.")
    return log.save("rerun.txt")


# ---------------------------------------------------------------- logs/stale-run.txt


def stale_log():
    log = Log("An update refused because a field changed on GitHub after the preview. github-update-metadata, attempt github-attempt-005")
    world = World("stale")
    swap = ["label.add=in progress", "label.remove=needs triage"]

    log.part("PART 1. The preview")
    _, shown = log.run(world.argv("preview", swap))
    mark = mark_in(shown)
    log.check("the preview is READY, with fingerprint %s" % mark, bool(mark))

    log.part("PART 2. Meanwhile, on GitHub, a maintainer adds a label. This is the quest's scenario")
    log.world(world, "someone-else", "label.add=urgent")
    before = world.look()
    log.check("the issue on the made-up GitHub now has three labels: bug, needs triage, urgent", before["issue"]["labels"] == ["bug", "needs triage", "urgent"])

    log.part("PART 3. The person confirms the preview they were shown")
    code, text = log.run(world.argv("confirm", swap, more=confirmation(mark)))
    log.check("exit code 1, refused as STALE, and the run says nothing was written",
              code == 1 and "REFUSED: STALE: a field changed on GitHub after the preview" in text and "Nothing was written." in text)
    log.check("it shows the values of the preview beside the values now, and names what moved: the label \"urgent\" was added",
              'preview:   labels     ["bug", "needs triage"]' in text and 'now:       labels     ["bug", "needs triage", "urgent"]' in text
              and 'MOVED since the preview: labels: added "urgent"' in text)
    unchanged(log, world, before)
    log.check("the maintainer's label is still on the issue", "urgent" in world.look()["issue"]["labels"])
    log.check("every request of the refused run was a GET", "every one a GET" in text and all(call[0] == "GET" for call in world.look()["calls"]))

    log.part("PART 4. A new preview shows the issue as it is now, and can be confirmed")
    _, shown = log.run(world.argv("preview", swap))
    again = mark_in(shown)
    log.check("the new preview has another fingerprint, and its old values include \"urgent\"", bool(again) and again != mark and 'old:       labels     ["bug", "needs triage", "urgent"]' in shown)
    code, text = log.run(world.argv("confirm", swap, more=confirmation(again)))
    log.check("exit code 0, DONE", code == 0 and "RESULT: DONE" in text)
    log.check("the issue has the label that was asked for and the maintainer's label, and has lost only the one it was asked to lose",
              sorted(world.look()["issue"]["labels"]) == ["bug", "in progress", "urgent"])

    log.part("PART 5. A field the update does not touch also stops it")
    other = World("stale-milestone")
    _, shown = log.run(other.argv("preview", swap))
    log.world(other, "someone-else", "milestone.clear")
    before = other.look()
    code, text = log.run(other.argv("confirm", swap, more=confirmation(mark_in(shown))))
    log.check("exit code 1, STALE: the milestone moved, though only labels were being changed", code == 1 and "STALE" in text
              and 'MOVED since the preview: milestone: "Sprint 12" (number 1) became none' in text)
    unchanged(log, other, before)

    log.part("PART 6. A new comment is not metadata, and does not stop the update")
    third = World("stale-comment")
    _, shown = log.run(third.argv("preview", swap))
    log.world(third, "someone-else", "comment")
    code, text = log.run(third.argv("confirm", swap, more=confirmation(mark_in(shown))))
    log.check("exit code 0, DONE: labels, assignees and milestone had not moved", code == 0 and "HAS ANYTHING MOVED? No." in text)

    log.part("PART 7. The gap that remains: a change in the moment between the check and the write")
    log.out("The check and the write are separate requests. GitHub offers no way to make them one for these fields. Here the")
    log.out("made-up GitHub is told to let a maintainer add \"urgent\" after the check has passed and just before the first write.")
    log.out("This cannot be arranged from the command line, so the workflow is started inside this script.")
    fake = fake_github.FakeGitHub()
    folder = os.path.join(Log.scratch, "race")
    args = lambda command, **more: type("Args", (), dict(dict(command=command, source="fake", repo=REPO, issue=ISSUE, change=swap, allowlist=ALLOWLIST,
                                                             state=os.path.join(folder, "previews"), results=os.path.join(folder, "results"), fingerprint=None, confirmed_by=None), **more))()
    printed = io.StringIO()
    with contextlib.redirect_stdout(printed):
        update.run(args("preview"), update.Connection(fake.send))
    race_mark = mark_in(printed.getvalue())

    def meanwhile(method, path):
        if method == "POST" and fake.before:
            fake.before = None
            fake.someone_else("label.add=urgent")
    fake.before = meanwhile
    printed = io.StringIO()
    with contextlib.redirect_stdout(printed):
        code = update.run(args("confirm", fingerprint=race_mark, confirmed_by=NAME), update.Connection(fake.send))
    log.out("(inside this script) the confirmation, with a maintainer's change arriving between the check and the write")
    log.lines += ["-" * 78, log.tidy(printed.getvalue().rstrip("\n")), "-" * 78, "exit code: %s" % code]
    text = printed.getvalue()
    log.check("the check passed, because at that moment nothing had moved", "5. HAS ANYTHING MOVED? No." in text)
    log.check("the maintainer's label was NOT removed: labels are added and removed one at a time, never sent as a whole list",
              sorted(fake.issue()["labels"]) == ["bug", "in progress", "urgent"])
    log.check("exit code 3, NEEDS LOOKING: the read-back found a label the preview did not promise, and the run says which",
              code == 3 and "RESULT: NEEDS LOOKING" in text and 'THIS IS NOT what the preview promised: labels: added "urgent"' in text)
    return log.save("stale-run.txt")


# ---------------------------------------------------------------- the supported-fields file


def allowlist():
    with open(os.path.join(ROOT, ALLOWLIST), encoding="utf-8") as f:
        return json.load(f)["sandbox_repositories"]


def supported_doc(preview_text):
    """Writes supported-fields.md: what may be changed, what is refused, and two runs."""
    world = World("unsupported")
    asked = ["title=A new title", "state=closed", "project.status=Done", "label.set=in progress", "label.add=brand new", "milestone.set=Sprint 11", "label.add=urgent"]
    done = subprocess.run([sys.executable] + world.argv("preview", asked), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    text = done.stdout.replace(os.path.realpath(Log.scratch), "SCRATCH").replace(Log.scratch, "SCRATCH")
    look = world.look()
    ok = (done.returncode == 1 and "RESULT: NOT READY. 6 changes were refused" in text and mark_in(text) is None and not look["writes"]
          and world.previews() == [] and len(look["repos"][REPO]["labels"]) == 5)
    command = "python3 " + " ".join(shlex.quote(part) for part in world.argv("preview", asked)).replace(Log.scratch, "SCRATCH")
    lines = [
        "# Supported fields: what the metadata update may change",
        "",
        "Written by an AI assistant (Claude) at the participant's direction, for the quest `github-update-metadata`. The",
        "two runs at the end are put in by `scripts/record_evidence.py`, against the made-up GitHub. The workflow is",
        "`participant/skills/github-update-metadata/update.py`.",
        "",
        "## What it may change",
        "",
        "Three fields of one issue, in six ways. Nothing else.",
        "",
        "| Asked for as | What it does | Allowed values | Sent to GitHub as |",
        "|---|---|---|---|",
        "| `label.add=NAME` | adds one label | a label that already exists in the repository. Capitals do not matter | `POST .../issues/N/labels` with that one label |",
        "| `label.remove=NAME` | removes one label | a label that exists in the repository | `DELETE .../issues/N/labels/NAME` |",
        "| `assignee.add=LOGIN` | assigns one person | a login GitHub says can be assigned in this repository. At most %d on one issue | `POST .../issues/N/assignees` with that one login |" % update.MAX_ASSIGNEES,
        "| `assignee.remove=LOGIN` | unassigns one person | a login that is assigned | `DELETE .../issues/N/assignees` with that one login |",
        "| `milestone.set=TITLE` | puts the issue in a milestone | the exact title of one open milestone of the repository | `PATCH .../issues/N` with only the milestone's number |",
        "| `milestone.clear=yes` | takes the issue out of its milestone | only `yes` | `PATCH .../issues/N` with only `milestone: null` |",
        "",
        "Limits: at most %d changes in one preview. One issue per preview. Issues only, not pull requests. Only a" % update.MAX_CHANGES,
        "repository named in the sandbox allowlist, `%s`." % ALLOWLIST,
        "",
        "A change that is already so (adding a label the issue has) is reported and is not sent.",
        "",
        "## Why labels and assignees are added and removed one at a time",
        "",
        "GitHub can also replace the whole list of labels in one request. That is how a label a maintainer added that",
        "morning gets removed by a workflow working from an older copy. This workflow never sends a whole list. A label",
        "it was not asked about is not in any request it sends, so it cannot be removed by it.",
        "",
        "## What it refuses",
        "",
        "| Asked for as | Refused because |",
        "|---|---|"]
    names = {"project": "`project.ANYTHING`, `projects.ANYTHING`"}
    lines += ["| %s | %s |" % (names.get(field, "`%s`" % field), reason) for field, reason in update.NOT_SUPPORTED.items()]
    lines += [
        "| anything else | it is not a field this workflow knows |",
        "",
        "It also refuses, with the reason shown in the preview:",
        "",
        "- a label the repository does not have. GitHub would create it without saying, so the workflow checks first;",
        "- a login GitHub says cannot be assigned in the repository;",
        "- a milestone that is closed, that does not exist, or whose title two milestones share;",
        "- a request that asks for a thing and its opposite, or for the same thing twice;",
        "- a value that is empty, longer than 100 characters or not on one line;",
        "- a pull request, an archived repository, and an account GitHub says may not change issues there.",
        "",
        "One refused change stops the whole preview. No fingerprint is given, so nothing can be confirmed.",
        "",
        "**Project fields** are refused on purpose. They live in GitHub Projects, outside the repository, and are changed",
        "through a different interface with a wider token. The assistant believes a token limited to one repository",
        "cannot reach them, and did not check that against GitHub's documentation.",
        "",
        "## Run 1: unsupported changes refused",
        "",
        "Seven changes are asked for. Six are refused: the title, the state, a project field, replacing the whole label",
        "list, a label that does not exist, and a closed milestone. The seventh is supported and would be allowed alone.",
        "",
        "    $ " + command,
        ""]
    lines += ["    " + line for line in text.rstrip("\n").split("\n")] + ["", "    exit code: %d" % done.returncode, ""]
    lines += [
        "Checked by the recording script, from the made-up GitHub's own file: the made-up GitHub received no write, no",
        "preview was saved, and the repository still has its 5 labels, so \"brand new\" was not created. Result: %s." % ("as expected" if ok else "NOT AS EXPECTED"),
        "",
        "## Run 2: the preview showing old and new values",
        "",
        "This is the preview of `logs/preview.txt`, part 2. Section 4 shows the old and new value of every field the",
        "workflow can change, including the one that stays the same.",
        ""]
    lines += ["    " + line for line in preview_text.replace(os.path.realpath(Log.scratch), "SCRATCH").replace(Log.scratch, "SCRATCH").rstrip("\n").split("\n")] + [""]
    with open(os.path.join(ROOT, SUPPORTED_DOC), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("supported-fields.md: written. Run 1 came out %s." % ("as expected" if ok else "NOT AS EXPECTED"))
    return ok


def main():
    os.chdir(ROOT)
    with tempfile.TemporaryDirectory() as scratch:
        Log.scratch = scratch
        world = World("approved")
        ok, mark, preview_text = preview_log(world)
        ok = confirmation_log(world, mark, preview_text) and ok
        ok = rerun_log(world, mark) and ok
        ok = stale_log() and ok
        ok = supported_doc(preview_text) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
