#!/usr/bin/env python3
"""Records the runs against the FAKE Jira for the quest jira-link-work:

    logs/link-check.txt     the relationship in words; an identical link detected; both items read back; how direction was tested
    logs/preview.txt        the workflow stopping at a preview
    logs/confirmation.txt   the approved run, and four refusals
    logs/rerun.txt          the approved workflow run a second time
    logs/stretch.txt        a link that would close a circle, and several links in one confirmed batch

NOTHING HERE TOUCHES A REAL JIRA. The fake Jira is a file in a temporary folder, deleted at the end. Every project,
issue, person and title is made up. The runs against the real sandbox are in the logs whose names begin "live-".

In the records, TEMP stands for the temporary folder. Each command line is shown shortened: every command was also
given --source fake and a state folder. The request and the allowlist are shown by file name, and each request's
sentences are written out above the command that uses it.

Run from anywhere:  python3 scripts/record_evidence.py        Exit code 0 if every check came out as expected.
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
SKILL = os.path.join(PARTICIPANT, "skills", "jira-link-work")
TOOL = os.path.join(SKILL, "link_work.py")
FAKE = os.path.join(SKILL, "fake_jira.py")
ALLOWLIST = os.path.join(SKILL, "fixtures", "fake-allowlist.json")
PERSON = "A made-up person"
HEAD = ("Recorded by scripts/record_evidence.py against the FAKE Jira: a file on this computer, with made-up projects and issues.\n"
        "Each block between dashed lines is what a command printed. No real Jira was contacted to make this record.\n"
        "The fake Jira begins with one link: SAND-3 blocks SAND-4 (link id 40001).")


class Log:
    def __init__(self, title, temp):
        self.lines, self.problems, self.count, self.temp = [title, HEAD, ""], [], 0, temp

    def out(self, *lines):
        self.lines += list(lines) if lines else [""]

    def part(self, text):
        self.lines += ["", "=" * 78, text]

    def check(self, label, ok):
        self.count += 1
        self.lines.append("  %-4s %s" % ("ok" if ok else "FAIL", label))
        if not ok:
            self.problems.append(label)

    def tidy(self, text):
        for path, name in ((os.path.realpath(self.temp), "TEMP"), (self.temp, "TEMP"), (SKILL, "SKILL")):
            text = text.replace(path, name)
        return text

    def run(self, shown, args):
        done = subprocess.run([sys.executable] + args, capture_output=True, text=True, cwd=SKILL)
        said = self.tidy((done.stdout + done.stderr).rstrip("\n"))
        self.lines += ["$ " + shown, "-" * 78, said, "-" * 78, "exit status: %d" % done.returncode]
        return done.returncode, said

    def save(self, name):
        self.lines += ["", "RESULT: %s" % ("%d OF %d CHECKS FAILED." % (len(self.problems), self.count) if self.problems else "ALL CHECKS PASSED. %d checks." % self.count)]
        os.makedirs(os.path.join(ATTEMPT, "logs"), exist_ok=True)
        with open(os.path.join(ATTEMPT, "logs", name), "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(self.lines) + "\n")
        print("%s: %s" % (name, self.lines[-1]))
        for label in self.problems:
            print("  FAILED: " + label)
        return not self.problems


class Jira:
    """One fake Jira in one state folder, and the commands run against it."""

    def __init__(self, log, temp, name):
        self.log, self.temp, self.state = log, temp, os.path.join(temp, name)
        self.request = os.path.join(temp, name + "-requests", "links.json")
        os.makedirs(os.path.dirname(self.request))

    def ask(self, *links, say=True):
        with open(self.request, "w", encoding="utf-8") as f:
            json.dump({"links": [{"from": a, "phrase": phrase, "to": b} for a, phrase, b in links]}, f)
        if say:
            self.log.out("", "The request file links.json now says: %s." % "; ".join("%s %s %s" % link for link in links))

    def cmd(self, command, *extra, allowlist=ALLOWLIST):
        args, shown = [TOOL, command, "--source", "fake", "--state", self.state], "link_work.py %s" % command
        if command != "check":
            args += ["--request", self.request, "--allowlist", allowlist]
            shown += " --request links.json --allowlist %s" % os.path.basename(allowlist)
        return self.log.run(shown + "".join(" " + ('"%s"' % e if " " in e else self.log.tidy(e)) for e in extra), args + list(extra))

    def confirm(self, fingerprint, *extra, **kw):
        return self.cmd("confirm", "--fingerprint", fingerprint, "--confirmed-by", PERSON, *extra, **kw)

    def fake(self, *args):
        return self.log.run("fake_jira.py %s" % " ".join(args), [FAKE, args[0], "--state", self.state] + list(args[1:]))

    def links(self):
        path = os.path.join(self.state, "fake-jira.json")
        if not os.path.exists(path):
            return ["SAND-3 blocks SAND-4"]
        with open(path, encoding="utf-8") as f:
            state = json.load(f)
        words = {"10000": "blocks", "10001": "clones", "10002": "duplicates", "10003": "relates to"}
        return ["%s %s %s" % (state["issues"][l["source"]]["key"], words[l["type_id"]], state["issues"][l["target"]]["key"])
                for l in sorted(state["links"].values(), key=lambda item: int(item["id"]))]


def fingerprint_in(text):
    found = re.search(r"Fingerprint of this preview: ([0-9a-f]{12})", text)
    return found.group(1) if found else ""


def requests_of(text):
    return [line.strip() for line in text.split("\n") if line.startswith(("  GET /rest", "  POST /rest"))]


def all_get(text):
    return "Every one was a GET" in text and "POST" not in text


def main():
    temp = tempfile.mkdtemp(prefix="gtq-link-")
    ok = True
    try:
        # ------------------------------------------------------------ preview.txt
        log = Log("The workflow stopping at a preview. jira-link-work, attempt jira-attempt-016", temp)
        jira = Jira(log, temp, "state-preview")
        jira.ask(("SAND-1", "blocks", "SAND-2"))
        log.part("THE PREVIEW")
        code, said = jira.cmd("preview")
        log.check("criterion 1: the preview states the relationship and its direction in words, from both items",
                  code == 0 and "IN WORDS:                        SAND-1 blocks SAND-2." in said and "The same link, from the other item: SAND-2 is blocked by SAND-1." in said)
        log.check("criterion 4: it shows the Jira site, the project and the exact changes: the link type and which item goes in which of Jira's two slots",
                  "Jira site:  https://" in said and "SAND (project id 20001)" in said and "type          link type id 10000" in said
                  and 'inwardIssue   issue id 30001 (SAND-1), the item that "blocks"' in said and 'outwardIssue  issue id 30002 (SAND-2), the item that "is blocked by"' in said)
        log.check("criterion 5: the permission check is recorded for each item: may see it, may link issues", "SAND-1: yes / yes" in said and "SAND-2: yes / yes" in said)
        log.check("criterion 5: the duplicate check is recorded: this same link, the opposite link, and where Jira cannot check",
                  "the same type and the same way round: 0." in said and "The opposite link, which would be a conflict: 0." in said and "Where Jira cannot check" in said)
        log.check("criterion 7: the preview has a fingerprint, and says when it expires", bool(fingerprint_in(said)) and "15 minutes after it was made" in said)
        log.check("criterion 4: nothing was written: every request was a GET, and the before and after snapshots are the same", all_get(said) and "The two are the same" in said)
        log.out("", "This record is made from what the command printed to the SCREEN, so the two made-up titles are in it above. The same",
                "preview again, this time also saved with --log, and the saved file looked at:")
        kept = os.path.join(temp, "saved-preview.txt")
        jira.cmd("preview", "--log", kept)
        with open(kept, encoding="utf-8") as f:
            saved = f.read()
        log.out("Lines of the saved file that hold a title or the site:", *["    " + line.strip() for line in saved.split("\n") if line.strip().startswith("|") or line.startswith("Jira site:")])
        log.check("in a saved log the items' titles are left out and the site's address is replaced by a marker",
                  "Collect the export requirements" not in saved and "Write the export query" not in saved and saved.count("the title was shown on screen and is not saved") == 2
                  and "fixture-site" not in saved and "[site address removed]" in saved)
        log.out("", "The fake Jira, looked at directly after the preview:")
        jira.fake("show")
        log.check("the fake Jira still holds only the one link it began with", jira.links() == ["SAND-3 blocks SAND-4"])
        ok = log.save("preview.txt") and ok

        # ------------------------------------------------------------ confirmation.txt
        log = Log("The approved run, and four refusals. jira-link-work, attempt jira-attempt-016", temp)
        jira = Jira(log, temp, "state-confirm")
        jira.ask(("SAND-1", "blocks", "SAND-2"))
        log.part("FOUR REFUSALS, each with nothing written. A preview is made first.")
        code, said = jira.cmd("preview")
        first = fingerprint_in(said)
        unchanged = lambda: jira.links() == ["SAND-3 blocks SAND-4"]   # noqa: E731

        log.out("", "1. A MISSING CONFIRMATION: no fingerprint is given.")
        code, said = jira.cmd("confirm", "--confirmed-by", PERSON)
        log.check("criterion 7: refused when the confirmation is missing, and nothing written", code == 1 and "no confirmation was given" in said and unchanged())

        log.out("", "2. A CHANGE THAT DIFFERS FROM THE PREVIEW: after the preview the request is turned round, and the preview's fingerprint",
                "   is used. (The script rewrites the request, runs the command, and puts the request back byte for byte.)")
        with open(jira.request, "rb") as f:
            original = f.read()
        jira.ask(("SAND-2", "blocks", "SAND-1"))
        try:
            code, said = jira.confirm(first)
        finally:
            with open(jira.request, "wb") as f:
                f.write(original)
        log.check("criterion 7: refused when the change differs from the preview, and nothing written", code == 1 and "the change is not the one that was previewed" in said and unchanged())

        log.out("", "3. A PREVIEW OLDER THAN THE LIMIT: the test clock is moved 16 minutes on. The limit is 15.")
        code, said = jira.confirm(first, "--pretend-minutes-later", "16")
        log.check("criterion 7: refused when the preview is older than the stated limit, and nothing written", code == 1 and "this preview is too old" in said and "the limit is 15" in said and unchanged())

        log.out("", "4. A PROJECT THAT IS NOT ON THE SANDBOX ALLOWLIST: one end of the link is PROD-9, where the identity MAY link issues.")
        jira.ask(("SAND-1", "blocks", "PROD-9"))
        code, said = jira.cmd("preview")
        log.check("criterion 6: refused when either item is in a project not on the allowlist, before any preview, and nothing written",
                  code == 1 and "PROD-9 is in project PROD (project id 20002)" in said and "is not on the sandbox allowlist" in said and not fingerprint_in(said) and unchanged())
        with open(jira.request, "wb") as f:
            f.write(original)
        log.out("   The request is put back to: SAND-1 blocks SAND-2. And the confirmation, with an allowlist that lists no project:")
        empty = os.path.join(temp, "empty-allowlist.json")
        with open(empty, "w", encoding="utf-8") as f:
            json.dump({"sandbox_projects": []}, f)
        code, said = jira.confirm(first, allowlist=empty)
        log.check("criterion 6: the confirmation is refused too when the project is not on the allowlist it is given", code == 1 and "is not on the sandbox allowlist (empty-allowlist.json)" in said and unchanged())

        log.part("THE APPROVED RUN. The first preview is still open and unused, and is confirmed by its fingerprint.")
        result = os.path.join(temp, "result.md")
        code, said = jira.confirm(first, "--result", result)
        log.check("criterion 7: the confirmation names the preview's fingerprint and the person, and the write happens in the same run",
                  code == 0 and "CONFIRMATION for preview %s, given by: %s" % (first, PERSON) in said and "The confirmation and the writes happen in this one run" in said)
        sent = requests_of(said)
        write = sent.index("POST /rest/api/3/issueLink") if "POST /rest/api/3/issueLink" in sent else -1
        log.check("criteria 2, 5 and 6: the order of its requests shows the run read both items and asked the permission question BEFORE the one write, and read both items after it",
                  write > 0 and sent.count("POST /rest/api/3/issueLink") == 1 and sent[write - 2:write] == ["GET /rest/api/3/issue/30001", "GET /rest/api/3/issue/30002"]
                  and "GET /rest/api/3/mypermissions" in sent[:write] and sent[write + 1:write + 3] == ["GET /rest/api/3/issue/30001", "GET /rest/api/3/issue/30002"])
        log.check("criterion 3: one link was created, and the fake Jira holds it the right way round", "WRITTEN to Jira: link id 40002" in said and jira.links() == ["SAND-3 blocks SAND-4", "SAND-1 blocks SAND-2"])
        log.check("criterion 8: the result record holds the issue keys, the identifier of the link created, the project, the timestamp and the confirmer",
                  all(w in said for w in ("Link 1. Issue keys: SAND-1 and SAND-2", "Identifier of what was created: Jira issue link id 40002", "Target project: SAND (project id 20001)", "Link 1. Written at: 20", "Confirmed by: " + PERSON)))
        with open(result, encoding="utf-8") as f:
            log.check("the result record saved as Markdown has the site's address taken out", "fixture-site" not in f.read())
        ok = log.save("confirmation.txt") and ok

        # ------------------------------------------------------------ rerun.txt (the same fake Jira)
        rerun = Log("The approved workflow, run a second time. jira-link-work, attempt jira-attempt-016", temp)
        jira.log = rerun
        rerun.out("This continues from the approved run in logs/confirmation.txt, against the same fake Jira: SAND-1 blocks SAND-2 exists (link id 40002).")
        rerun.part("1. PREVIEW AGAIN, the same request")
        code, said = jira.cmd("preview")
        rerun.check("criteria 2 and 9: the preview finds the link already there, says it is not created again, and issues no fingerprint",
                    code == 0 and "NOTHING TO CREATE" in said and "ALREADY THERE. It is not created again" in said and "(link id 40002)" in said and not fingerprint_in(said) and all_get(said))
        rerun.part("2. CONFIRM AGAIN, with the fingerprint that was used")
        code, said = jira.confirm(first)
        rerun.check("criterion 9: the confirmation is refused: a fingerprint is used once", code == 1 and "has been used" in said)
        rerun.part("3. CHECK the links of the approved run")
        code, said = jira.cmd("check", "--fingerprint", first)
        rerun.check("criterion 3: read again from both items, the link is there with the right type and direction, and there is one of it",
                    code == 0 and "counted on each: 1 and 1" in said and "FOUND: every link is there" in said and all_get(said))
        rerun.part("4. THE FAKE JIRA, looked at directly")
        jira.fake("show")
        rerun.check("criterion 9: no duplicate: the fake Jira holds the same two links as after the approved run", jira.links() == ["SAND-3 blocks SAND-4", "SAND-1 blocks SAND-2"])
        ok = rerun.save("rerun.txt") and ok

        # ------------------------------------------------------------ link-check.txt
        log = Log("The link in words, an identical link detected, and both items read back. jira-link-work, attempt jira-attempt-016", temp)
        jira = Jira(log, temp, "state-link-check")
        log.part("1. THE PREVIEW STATES THE RELATIONSHIP AND ITS DIRECTION IN WORDS")
        jira.ask(("SAND-2", "is blocked by", "SAND-1"))
        log.out("This request is written from the blocked item's side, on purpose.")
        code, said = jira.cmd("preview")
        fingerprint = fingerprint_in(said)
        log.check("criterion 1: the preview says the sentence as asked, and the same link from the other item",
                  "IN WORDS:                        SAND-2 is blocked by SAND-1." in said and "The same link, from the other item: SAND-1 blocks SAND-2." in said)
        log.check("criterion 1: it works out that SAND-1 is the item that blocks, though the request names SAND-2 first",
                  'inwardIssue   issue id 30001 (SAND-1), the item that "blocks"' in said and 'outwardIssue  issue id 30002 (SAND-2), the item that "is blocked by"' in said)

        log.part("2. THE LINK IS CREATED, AND READ BACK FROM BOTH ITEMS")
        code, said = jira.confirm(fingerprint)
        log.check("criterion 3: read from SAND-1, the link says: SAND-1 blocks SAND-2", code == 0 and "read from SAND-1: it lists link id 40002 as: SAND-1 blocks SAND-2. Wanted: SAND-1 blocks SAND-2. Type \"Blocks\": yes" in said)
        log.check("criterion 3: read from SAND-2, the same link says: SAND-2 is blocked by SAND-1", "read from SAND-2: it lists link id 40002 as: SAND-2 is blocked by SAND-1. Wanted: SAND-2 is blocked by SAND-1. Type \"Blocks\": yes" in said)
        log.check("criterion 3: read by its own id, the link has the two items in the slots they were sent in", "as sent: yes" in said)
        log.out("", "The fake Jira, looked at directly:")
        jira.fake("show")
        log.check("the fake Jira holds it as: SAND-1 blocks SAND-2", jira.links()[-1] == "SAND-1 blocks SAND-2")

        log.part("3. AN EXISTING IDENTICAL LINK IS DETECTED AND NOT CREATED AGAIN")
        jira.ask(("SAND-1", "blocks", "SAND-2"))
        log.out("The same link, asked for this time from the other item's side.")
        code, said = jira.cmd("preview")
        log.check("criterion 2: the link is recognised as the one already there, though the request is worded the other way, and nothing is created",
                  code == 0 and "ALREADY THERE. It is not created again" in said and "the same type and the same way round: 1 (link id 40002)" in said and not fingerprint_in(said) and all_get(said))
        jira.ask(("SAND-3", "blocks", "SAND-4"))
        log.out("And the link the fake Jira began with, which this workflow did not make.")
        code, said = jira.cmd("preview")
        log.check("criterion 2: a link made by someone else is detected the same way", "ALREADY THERE" in said and "(link id 40001)" in said and not fingerprint_in(said))
        jira.ask(("SAND-2", "blocks", "SAND-1"))
        log.out("And the OPPOSITE of the link just made.")
        code, said = jira.cmd("preview")
        log.check("the opposite link is not taken for the same link: it is refused as a conflict, and nothing is created",
                  code == 1 and "THE OPPOSITE LINK ALREADY EXISTS (link id 40002): SAND-1 blocks SAND-2. The request says: SAND-2 blocks SAND-1" in said and not fingerprint_in(said))
        jira.fake("show")
        log.check("after those three previews the fake Jira still holds the two links it held before them", jira.links() == ["SAND-3 blocks SAND-4", "SAND-1 blocks SAND-2"])

        log.part("4. WOULD A WRONG DIRECTION BE NOTICED? A JIRA THAT STORES THE LINK THE OTHER WAY ROUND")
        log.out("Parts 1 to 3 show that the workflow and the fake Jira AGREE about direction. They cannot show that either is right about",
                "a real Jira: the fake was written with the same belief about Jira's two slots as the workflow. So here a NEW fake Jira,",
                "holding only its first link again, is told to store the next link the other way round from what the workflow expects,",
                "as a real Jira would if the workflow had the slots wrong. This tests that a mismatch is noticed. It does not test which",
                "way round is right.")
        jira = Jira(log, temp, "state-backwards")
        jira.ask(("SAND-1", "blocks", "SAND-2"))
        code, said = jira.cmd("preview")
        fingerprint = fingerprint_in(said)
        jira.fake("set", "--reverse-next")
        code, said = jira.confirm(fingerprint)
        log.check("the workflow notices from the read-back: it ends with 'a person needs to look', says the link reads backwards, and names the link id to remove",
                  code == 2 and "THE LINK READS BACKWARDS, AND IT IS IN JIRA NOW. Asked for: SAND-1 blocks SAND-2. What Jira now holds is link id 40002: SAND-2 blocks SAND-1" in said)
        log.check("it says the wrong-way link IS in Jira, tells the person to remove it by hand, and does not advise previewing again",
                  "AND IT IS IN JIRA NOW" in said and "1. Remove link id 40002 by hand in Jira" in said and "2. Do not run this workflow again" in said and "Preview again" not in said and "WRITTEN to Jira" not in said)
        jira.fake("show")
        log.check("the fake Jira does hold the wrong-way link: SAND-2 blocks SAND-1", jira.links() == ["SAND-3 blocks SAND-4", "SAND-2 blocks SAND-1"])
        log.out("", "WHAT NONE OF THIS SHOWS. Whether the workflow has the slots right for a REAL Jira. The real run (logs/live-*) shows that a",
                "real Jira's answers agree with the workflow's reading of them. The last step is a person's: to look at the item in Jira's",
                "own screen and see which way the link reads there. PROOF.md says what was seen.")
        ok = log.save("link-check.txt") and ok

        # ------------------------------------------------------------ stretch.txt
        log = Log("A circle refused, and several links in one confirmed batch. jira-link-work, attempt jira-attempt-016", temp)
        jira = Jira(log, temp, "state-stretch")
        log.part("1. A LINK THAT WOULD CLOSE A CIRCLE (stretch goal)")
        jira.fake("other-link", "--source", "SAND-4", "--type", "Blocks", "--target", "SAND-5")
        log.out("The fake Jira now holds: SAND-3 blocks SAND-4, and SAND-4 blocks SAND-5.")
        jira.ask(("SAND-5", "blocks", "SAND-3"))
        code, said = jira.cmd("preview")
        log.check("stretch goal: the link is refused: followed from SAND-3, the existing links lead back to SAND-5. No fingerprint, nothing written",
                  code == 1 and 'THIS LINK WOULD CLOSE A CIRCLE. Followed from SAND-3, existing "blocks" links lead back to SAND-5' in said and not fingerprint_in(said) and len(jira.links()) == 2)
        jira.ask(("SAND-1", "blocks", "SAND-2"), ("SAND-2", "blocks", "SAND-6"), ("SAND-6", "blocks", "SAND-1"))
        code, said = jira.cmd("preview")
        log.check("a circle made only by the links of one request is refused too, at the link that would close it", code == 1 and "link 3: THIS LINK WOULD CLOSE A CIRCLE" in said and len(jira.links()) == 2)
        jira.fake("other-link", "--source", "SAND-5", "--type", "Relates", "--target", "SAND-2")
        log.out("The fake Jira now also holds: SAND-5 relates to SAND-2.")
        jira.ask(("SAND-2", "blocks", "SAND-3"))
        code, said = jira.cmd("preview")
        log.check("THE LIMIT, shown: the check follows links of ONE type. SAND-2 blocks SAND-3 blocks SAND-4 blocks SAND-5, and SAND-5 relates to SAND-2: "
                  "that is not counted as a circle, and the link is offered", code == 0 and bool(fingerprint_in(said)) and "Items reached, SAND-3 included: 3. None is SAND-2." in said)

        log.part("2. SEVERAL LINKS IN ONE CONFIRMED BATCH (stretch goal)")
        jira.ask(("SAND-3", "blocks", "SAND-4"), ("SAND-1", "blocks", "SAND-2"), ("SAND-2", "relates to", "SAND-6"))
        code, said = jira.cmd("preview")
        fingerprint = fingerprint_in(said)
        log.check("stretch goal: three links, one preview, one fingerprint. Each is said in words. One is already there",
                  code == 0 and said.count("Fingerprint of this preview") == 1 and "It asks for 3 links. To create: 2. Already there: 1." in said
                  and all("IN WORDS:                        %s." % words in said for words in ("SAND-3 blocks SAND-4", "SAND-1 blocks SAND-2", "SAND-2 relates to SAND-6")))
        code, said = jira.confirm(fingerprint)
        sent = requests_of(said)
        log.check("one confirmation creates the two that were missing, and does not send the one that was there", code == 0 and "ALREADY THERE (link id 40001). Not sent." in said
                  and "ALL DONE: 2 links written, 1 already there." in said and sent.count("POST /rest/api/3/issueLink") == 2)
        writes = [n for n, line in enumerate(sent) if line.startswith("POST")]
        between = sent[writes[0] + 1:writes[1]] if len(writes) == 2 else []
        log.check("the first new link is read back, from both of its items and by its own id, before the second is sent",
                  between[:2] == ["GET /rest/api/3/issue/30001", "GET /rest/api/3/issue/30002"] and len(between) > 2 and between[2].startswith("GET /rest/api/3/issueLink/"))
        jira.fake("show")
        log.check("the fake Jira holds each of the three once", sorted(jira.links()).count("SAND-1 blocks SAND-2") == 1 and sorted(jira.links()).count("SAND-2 relates to SAND-6") == 1 and jira.links().count("SAND-3 blocks SAND-4") == 1)

        log.part("3. A BATCH THAT STOPS PARTWAY: JIRA REFUSES THE SECOND WRITE")
        jira = Jira(log, temp, "state-partway")
        jira.ask(("SAND-1", "blocks", "SAND-2"), ("SAND-2", "relates to", "SAND-6"))
        code, said = jira.cmd("preview")
        fingerprint = fingerprint_in(said)
        jira.fake("set", "--fail-post", "400", "--after", "1")
        code, said = jira.confirm(fingerprint)
        log.check("the run stops at the link Jira refused, and says which link was written and that none is left unsent. Nothing is undone",
                  code == 1 and "link 2 (SAND-2 relates to SAND-6): Jira answered 400 to the write" in said and "Written in this run before it stopped: link 1 (link id 40002). Not sent: none" in said
                  and jira.links() == ["SAND-3 blocks SAND-4", "SAND-1 blocks SAND-2"])
        code, said = jira.cmd("preview")
        log.check("a new preview finds the link that was made and offers only the one that was not", "To create: 1. Already there: 1." in said and bool(fingerprint_in(said)))

        log.part("4. A BATCH OVERTAKEN BEFORE IT IS CONFIRMED")
        jira = Jira(log, temp, "state-overtaken")
        jira.ask(("SAND-1", "blocks", "SAND-2"), ("SAND-2", "relates to", "SAND-6"))
        code, said = jira.cmd("preview")
        fingerprint = fingerprint_in(said)
        log.out("Someone else makes the second link while the batch is waiting to be confirmed... and the confirmation is given.")
        jira.fake("other-link", "--source", "SAND-6", "--type", "Relates", "--target", "SAND-2")
        code, said = jira.confirm(fingerprint)
        log.check("the confirmation is refused whole, before anything is sent: what was previewed is no longer what would happen", code == 1 and "link 2: it was to be created when previewed, and is already there now" in said and len(jira.links()) == 2)
        code, said = jira.cmd("preview")
        log.check("a new preview offers only the link that is still missing", "To create: 1. Already there: 1." in said and bool(fingerprint_in(said)))
        ok = log.save("stretch.txt") and ok
    finally:
        shutil.rmtree(temp, ignore_errors=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
