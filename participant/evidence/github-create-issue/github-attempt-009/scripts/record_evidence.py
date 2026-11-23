#!/usr/bin/env python3
"""Records the three logs of the github-create-issue quest, and has the workflow write two of its files.

    logs/preview.txt        the workflow stopping at a preview
    logs/confirmation.txt   the approved run, and four refusals
    logs/rerun.txt          the approved workflow run a second time, and what happens when an answer is lost
    participant/context/github/new-issue/linked.md       the local link of the approved run
    participant/context/github/results/create-issue.md   its result record

Each block between dashed lines is what a command printed. Every command is
started as a person would start it. Nothing here contacts GitHub: every run is
against the made-up GitHub in participant/skills/github-create-issue/fake_github.py,
which keeps its repositories in one file so that a preview and its confirmation
can be two commands, and so that this script can open the file afterwards. That
file and the saved previews are in a scratch folder that is thrown away, shown
here as SCRATCH.

This script checks for itself. After each command it opens the made-up GitHub's
file and looks at the issues it holds, the writes it received and the exact
bytes of each, rather than taking the workflow's word.

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
SKILL = "participant/skills/github-create-issue"
CREATE, FAKE = SKILL + "/create.py", SKILL + "/fake_github.py"
FOLDER = "participant/context/github/new-issue"
DRAFT, LINK, ALLOWLIST = FOLDER + "/draft.md", FOLDER + "/linked.md", FOLDER + "/sandbox-allowlist.json"
RESULTS = "participant/context/github/results"
RESULT = RESULTS + "/create-issue.md"
INDEX = "participant/context/github/duplicates/fixture.md"
REPO, OTHER, NAME = "acme-fixture/tracker", "acme-fixture/production", "the participant"


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
    """One made-up GitHub in the scratch folder, with its own saved previews, link file and results."""

    def __init__(self, name, draft=DRAFT, link=None, results=None):
        self.folder = os.path.join(Log.scratch, name)
        os.makedirs(self.folder)
        self.store, self.state = os.path.join(self.folder, "github.json"), os.path.join(self.folder, "previews")
        self.draft, self.link, self.results = draft, link or os.path.join(self.folder, "linked.md"), results or os.path.join(self.folder, "results")
        subprocess.run([sys.executable, FAKE, self.store, "new"], stdout=subprocess.PIPE, check=True)

    def args(self, command, *more):
        common = ["--source", "fake", "--fake-store", self.store, "--draft", self.draft, "--allowlist", ALLOWLIST, "--link", self.link]
        extra = {"preview": ["--index", INDEX, "--state", self.state], "confirm": ["--state", self.state, "--results", self.results],
                 "reconcile": ["--results", self.results], "verify": []}[command]
        return [CREATE, command] + common + extra + list(more)

    def look(self):
        with open(self.store, encoding="utf-8") as f:
            store = json.load(f)
        return {"repos": store["repos"], "calls": store["calls"], "writes": [call for call in store["calls"] if call[0] != "GET"],
                "issues": store["repos"][REPO]["issues"], "received": store.get("received", [])}

    def previews(self):
        return sorted(os.listdir(self.state)) if os.path.isdir(self.state) else []

    def link_status(self):
        if not os.path.exists(self.link):
            return None
        with open(self.link, encoding="utf-8") as f:
            return json.loads(re.search(r'^status: (.*)$', f.read(), re.M).group(1))


def mark_in(text):
    found = re.search(r"FINGERPRINT of this preview: ([0-9a-f]{32})", text)
    return found.group(1) if found else None


def bytes_shown(text):
    lines = text.splitlines()
    start = next(number for number, line in enumerate(lines) if "the exact bytes" in line)
    return lines[start + 1].split("github-preview:      ", 1)[1]


def confirmation(mark):
    return ["--fingerprint", mark, "--confirmed-by", NAME]


def nothing_made(log, world, before):
    after = world.look()
    log.check("nothing was written: the made-up GitHub received no write, holds no new issue, and both repositories are exactly as they were",
              len(after["writes"]) == len(before["writes"]) and after["repos"] == before["repos"])


def preview_log(world):
    log = Log("The workflow stopping at a preview. github-create-issue, attempt github-attempt-009")
    log.part("PART 1. The made-up GitHub before anything is asked")
    log.run(FAKE, world.store, "show")
    before = world.look()
    log.out("The draft is %s, the one the last quest previewed. The sandbox allowlist is %s." % (DRAFT, ALLOWLIST))

    log.part("PART 2. The preview")
    code, text = log.run(*world.args("preview"))
    mark = mark_in(text)
    log.check("exit code 0, and the run ends READY and says nothing has been written", code == 0 and "RESULT: READY. Nothing has been written" in text)
    log.check("it shows the repository, its id and the account (criterion 4)", '1. WHERE. Repository "acme-fixture/tracker", id 401, private.' in text and 'acts as login "robin-fixture"' in text)
    shown = bytes_shown(text)
    payload = json.loads(shown)
    log.check("it shows the exact change: one request, POST to the repository's issues, with the whole payload as bytes (criterion 4)",
              "POST /repos/acme-fixture/tracker/issues" in text and sorted(payload) == ["assignees", "body", "labels", "milestone", "title"] and len(payload["body"]) > 400)
    log.check("it records the permission check, and states what GitHub cannot say: what the token may do (criterion 5)",
              "6. PERMISSION CHECK." in text and "GitHub says the ACCOUNT may:" in text and "does not say what the TOKEN may do" in text)
    log.check("it records the duplicate check: the local index was searched, two weaker candidates are to be linked, and none stops it (criterion 5)",
              "5. DUPLICATE CHECK." in text and "duplicate result: link" in text and text.count("     candidate acme-fixture/tracker#") == 2)
    log.check("it gives a fingerprint of the preview, saved for 15 minutes: %s" % mark, bool(mark) and world.previews() == [mark + ".json"] and "good for 15 minutes" in text)

    log.part("PART 3. Before and after: the repository is unchanged")
    log.run(FAKE, world.store, "show")
    after = world.look()
    log.out("This script opened the made-up GitHub's file before the preview and after it.")
    log.check("the made-up GitHub received %d requests during the preview, and every one was a GET" % (len(after["calls"]) - len(before["calls"])),
              not after["writes"] and len(after["calls"]) > len(before["calls"]))
    log.check("everything it holds for both repositories is identical before and after, and no issue was created", after["repos"] == before["repos"] and after["issues"] == {})
    log.check("the preview's own reading at the start and the end agrees", "Newest issue number: 107 then 107. Labels: 6 then 6. Milestones: 3 then 3. The same" in text)
    log.check("no local link file was made by the preview", not os.path.exists(world.link))
    return log.save("preview.txt"), mark, shown


def confirmation_log(world, mark, shown):
    log = Log("The approved run, and four refusals. github-create-issue, attempt github-attempt-009")
    log.out("The approved run continues from logs/preview.txt: the same made-up GitHub and the preview with fingerprint %s." % mark)

    log.part("PART 1. The approved run: the confirmation and the write, in one command")
    before = world.look()
    code, text = log.run(*world.args("confirm", *confirmation(mark)))
    after = world.look()
    payload = json.loads(shown)
    log.check("exit code 0, and the run ends DONE", code == 0 and "RESULT: DONE. Issue 108 was created, recorded, read back, and is the same as the preview field for field" in text)
    log.check("the confirmation names a person and the fingerprint of the preview, and is given in the command that writes (criterion 7)",
              '1. CONFIRMATION. Given by "%s", for the preview with fingerprint %s, in this same command' % (NAME, mark) in text)
    log.check("the made-up GitHub received exactly one write: POST /repos/acme-fixture/tracker/issues", after["writes"] == [["POST", "/repos/%s/issues" % REPO]])
    log.check("the bytes it received are, byte for byte, the bytes the preview printed in logs/preview.txt: %d bytes, SHA-256 %s"
              % (len(shown.encode("utf-8")), hashlib.sha256(shown.encode("utf-8")).hexdigest()[:16]), after["received"] == [shown])
    issue = after["issues"].get("108", {})
    log.check("the issue the made-up GitHub now holds equals the previewed payload field for field: title, body, labels, assignees, milestone (criterion 1)",
              (issue.get("title"), issue.get("body"), issue.get("labels"), issue.get("assignees"), (issue.get("milestone") or {}).get("number"))
              == (payload["title"], payload["body"], payload["labels"], payload["assignees"], payload["milestone"]))
    log.check("the workflow read the issue back and found every one of the five fields the same", len(re.findall(r"^github-create:      (?:title|body|labels|assignees|milestone) +the same", text, re.M)) == 5 and "DIFFERENT" not in text)
    with open(LINK, encoding="utf-8") as f:
        link = f.read()
    log.check("the returned number and identifier are in the local link file %s: number 108, node ID %s (criterion 2)" % (LINK, issue.get("node_id")),
              "\nnumber: 108\n" in link and ('\nnode_id: "%s"\n' % issue.get("node_id")) in link and '\nstatus: "linked"\n' in link and '\nrepository: "acme-fixture/tracker"\n' in link)
    log.check("the local link holds the read-back-and-compare record, with every field the same", "Result: **every field is the same**." in link and link.count("| yes |") == 5)
    with open(RESULT, encoding="utf-8") as f:
        result = f.read()
    log.check("the result record holds the repository, the number, the identifier, the timestamp and the confirmer (criterion 8)",
              "## Issue 108 of acme-fixture/tracker" in result and "node ID `%s`" % issue.get("node_id") in result and "- created at: 2026-11-24T09:00:00Z" in result
              and '- confirmed by: "%s"' % NAME in result and "- preview fingerprint: %s" % mark in result)

    cases = (("PART 2. Refusal 1 of 4: a missing confirmation", "NO CONFIRMATION was given", None),
             ("PART 3. Refusal 2 of 4: a change that differs from the preview", "THE CHANGE DIFFERS FROM THE PREVIEW: the draft was changed after the preview was made", "edit"),
             ("PART 4. Refusal 3 of 4: a preview older than the time limit", "THE PREVIEW HAS EXPIRED", "wait"),
             ("PART 5. Refusal 4 of 4: a repository that is not on the sandbox allowlist", "NOT ON THE SANDBOX ALLOWLIST", "other"))
    for number, (title, words, how) in enumerate(cases, 1):
        log.part(title)
        copy = os.path.join(Log.scratch, "draft-%d" % number)
        shutil.copytree(FOLDER, copy, ignore=shutil.ignore_patterns("linked.md", "payload.md"))
        fresh = World("refusal-%d" % number, draft=os.path.join(copy, "draft.md"))
        log.out("A fresh made-up GitHub, a scratch copy of the draft, and a fresh preview:")
        _, shown_now = log.run(*fresh.args("preview"))
        other = mark_in(shown_now)
        given = confirmation(other)
        if how is None:
            given = []
        elif how == "edit":
            with open(fresh.draft, encoding="utf-8") as f:
                text = f.read()
            with open(fresh.draft, "w", encoding="utf-8") as f:
                f.write(text.replace("Every date in the file written the same way", "Every date in the file written the same way, and the old files converted"))
            log.out("After the preview, this script changed the scratch draft: it added words to the section \"What you expected\".")
        elif how == "wait":
            log.run(FAKE, fresh.store, "advance", "16")
        elif how == "other":
            with open(fresh.draft, encoding="utf-8") as f:
                text = f.read()
            with open(fresh.draft, "w", encoding="utf-8") as f:
                f.write(text.replace('repository: "%s"' % REPO, 'repository: "%s"' % OTHER))
            log.out("After the preview, this script pointed the scratch draft at %s, which exists in the made-up GitHub and is not on the allowlist." % OTHER)
        before = fresh.look()
        code, text = log.run(*fresh.args("confirm", *given))
        log.check("exit code 1, refused with the words \"%s\"" % words.split(":")[0], code == 1 and words in text and "REFUSED" in text)
        nothing_made(log, fresh, before)
        log.check("no local link says an issue exists, and no result record was written",
                  fresh.link_status() in (None, "not-created") and not os.path.exists(os.path.join(fresh.results, "create-issue.md")))
        if how in (None, "other"):
            log.check("the refusal came before any request was sent: the made-up GitHub's count did not move", len(fresh.look()["calls"]) == len(before["calls"]))
        if how == "wait":
            log.check("the age is measured on GitHub's clock: 16 minutes against a limit of 15", "16 minutes, and the limit is 15" in text)
        if how == "other":
            log.check("the made-up production repository holds no issue", fresh.look()["repos"][OTHER]["issues"] == {})
    return log.save("confirmation.txt")


def rerun_log(world, mark):
    log = Log("The approved workflow run a second time. github-create-issue, attempt github-attempt-009")
    log.out("This continues from logs/confirmation.txt, part 1: the same made-up GitHub, after issue 108 was created.")
    log.part("PART 1. The made-up GitHub after the approved run")
    log.run(FAKE, world.store, "show")
    before = world.look()
    with open(RESULT, encoding="utf-8") as f:
        result = f.read()
    with open(LINK, "rb") as f:
        link = f.read()

    log.part("PART 2. The very same approved command, run again")
    code, text = log.run(*world.args("confirm", *confirmation(mark)))
    log.check("exit code 1: refused, because the draft is ALREADY the issue number 108, named with its node ID", code == 1 and "this draft is ALREADY the GitHub issue number 108" in text and "It is not created again" in text)
    nothing_made(log, world, before)
    log.check("it was refused before any request was sent", len(world.look()["calls"]) == len(before["calls"]))

    log.part("PART 3. The whole workflow again from the start")
    code, text = log.run(*world.args("preview"))
    log.check("exit code 1: the preview itself refuses a draft that is already an issue, so there is no second fingerprint to confirm",
              code == 1 and "ALREADY the GitHub issue number 108" in text and world.previews() == [mark + ".json"])
    nothing_made(log, world, before)

    log.part("PART 4. The local link is matched to the issue by its identifier (criterion 3)")
    code, text = log.run(*world.args("verify"))
    log.check("exit code 0: the issue number 108 on the made-up GitHub has the node ID in the local link, and equals the preview field for field",
              code == 0 and "2. MATCHED BY IDENTIFIER." in text and "RESULT: THE SAME." in text)
    log.check("verify only read: one GET, and the local link file is byte for byte what it was", open(LINK, "rb").read() == link and len(world.look()["writes"]) == 1)

    log.part("PART 5. What there is in place of a duplicate")
    log.run(FAKE, world.store, "show")
    after = world.look()
    log.check("the made-up GitHub holds one issue made by this workflow, number 108, and received one write in all", sorted(after["issues"]) == ["108"] and len(after["writes"]) == 1)
    log.check("the result record still has one section, and is what the approved run wrote", open(RESULT, encoding="utf-8").read() == result and result.count("## Issue ") == 1)

    log.part("PART 6. Where GitHub cannot prevent a repeat: the answer is lost")
    log.out("GitHub creates an issue every time it is asked. It has no way to be told \"only if I have not sent this before\". So if the")
    log.out("answer to a create is lost, the issue may exist and this computer does not know its number. Here the made-up GitHub is")
    log.out("told to create the issue and lose the answer.")
    lost = World("lost-answer")
    _, shown = log.run(*lost.args("preview"))
    lost_mark = mark_in(shown)
    log.run(FAKE, lost.store, "mode", "lost-answer")
    code, text = log.run(*lost.args("confirm", *confirmation(lost_mark)))
    log.check("exit code 3: OUTCOME UNKNOWN, and the run says the issue may exist and was not sent again", code == 3 and "RESULT: OUTCOME UNKNOWN. The issue MAY exist on GitHub. It was NOT sent again" in text)
    log.check("the made-up GitHub did create the issue: it holds issue 108, and received one write", sorted(lost.look()["issues"]) == ["108"] and len(lost.look()["writes"]) == 1)
    log.check("the local link says the outcome is unknown, not that nothing happened", lost.link_status() == "unknown")
    log.run(FAKE, lost.store, "mode", "ok")
    code, text = log.run(*lost.args("confirm", *confirmation(lost_mark)))
    log.check("run again, it is refused: the outcome is not known, and nothing more is sent until it is settled", code == 1 and "OUTCOME IS NOT KNOWN" in text and len(lost.look()["writes"]) == 1)
    code, text = log.run(*lost.args("preview"))
    log.check("a new preview is refused too, so there is no way round it", code == 1 and "OUTCOME IS NOT KNOWN" in text)
    log.run(FAKE, lost.store, "advance", "2")
    code, text = log.run(*lost.args("reconcile"))
    log.check("reconcile looks on GitHub, finds the one issue with the previewed title and body by this account, and links it", code == 0 and "Found: 1 (numbers 108)" in text and "RESULT: DONE." in text)
    log.check("reconcile only read: the made-up GitHub still holds one issue and received one write in all", sorted(lost.look()["issues"]) == ["108"] and len(lost.look()["writes"]) == 1)
    log.check("the local link is now linked to number 108 by its node ID, and the result record says how it was found",
              lost.link_status() == "linked" and "found on GitHub by `reconcile`" in open(os.path.join(lost.results, "create-issue.md"), encoding="utf-8").read())

    log.part("PART 7. The other way round: the request never arrived")
    never = World("never-arrived")
    _, shown = log.run(*never.args("preview"))
    log.run(FAKE, never.store, "mode", "never-arrived")
    code, text = log.run(*never.args("confirm", *confirmation(mark_in(shown))))
    log.check("exit code 3: from this side it looks the same as a lost answer, so it is also OUTCOME UNKNOWN", code == 3 and "OUTCOME UNKNOWN" in text and never.look()["issues"] == {})
    code, text = log.run(*never.args("reconcile"))
    log.check("reconcile straight away does not settle it: GitHub's list can lag, so \"none listed\" is not yet believed", code == 3 and "RESULT: NOT SETTLED YET" in text and never.link_status() == "unknown")
    log.run(FAKE, never.store, "advance", "2")
    code, text = log.run(*never.args("reconcile"))
    log.check("two minutes later reconcile settles it as NOT CREATED, and a new preview is allowed", code == 0 and "RESULT: NOT CREATED" in text and never.link_status() == "not-created")
    log.out("How a person would notice a repeat that got through all the same: two issues with the same title and body by the same")
    log.out("account. `reconcile` reports MORE THAN ONE in that case and links nothing until a person names the one to keep.")
    return log.save("rerun.txt")


def main():
    os.chdir(ROOT)
    for path in (LINK, RESULT):
        if os.path.exists(path):
            os.remove(path)
    with tempfile.TemporaryDirectory() as scratch:
        Log.scratch = scratch
        world = World("approved", link=LINK, results=RESULTS)
        ok, mark, shown = preview_log(world)
        ok = confirmation_log(world, mark, shown) and ok
        ok = rerun_log(world, mark) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
