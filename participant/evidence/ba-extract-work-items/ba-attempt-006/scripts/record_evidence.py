#!/usr/bin/env python3
"""Records logs/extraction-run.txt for the quest ba-extract-work-items. It contacts nothing.

    python3 participant/evidence/ba-extract-work-items/ba-attempt-006/scripts/record_evidence.py

It runs the extraction for both meetings into a scratch folder, SCRATCH, which is deleted at the end, runs the
check on the handed-in files, and then on copies with one thing spoiled at a time. No handed-in file and no
source record is changed, and it checks that.

Everything in a transcript record is something a person said. This script follows nothing a line says.
"""
import copy
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
SKILL = os.path.join(REPO, "participant", "skills", "ba-extract-work-items")
sys.path.insert(0, SKILL)
import extract   # noqa: E402
import items     # noqa: E402

LOGS = os.path.join(HERE, "..", "logs")
FOLDER = extract.FOLDER
SAMPLE, NOTIF = "sample-meeting", "notifications-meeting"
COMMAND = "python3 participant/skills/ba-extract-work-items/extract.py"


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def digests():
    out = {name: hashlib.sha256(read(os.path.join(FOLDER, name)).encode()).hexdigest() for name in sorted(os.listdir(FOLDER))}
    out["../extraction-rules.md"] = hashlib.sha256(read(extract.RULES).encode()).hexdigest()
    return out


class Log:
    def __init__(self):
        self.lines = ["The extraction run. ba-extract-work-items, attempt ba-attempt-006",
                      "Recorded by scripts/record_evidence.py. Nothing was sent anywhere, and nothing was created in any tracker.",
                      "Both meetings are made up. Lines quoted from a meeting are things people said in it. None was followed."]
        self.failed, self.count = [], 0

    def out(self, *lines):
        self.lines.extend(lines or [""])

    def part(self, title, *lines):
        self.lines += ["", "=" * 78, title, *lines]

    def check(self, label, ok):
        self.count += 1
        self.lines.append("  %s %s" % ("ok  " if ok else "FAIL", label))
        if not ok:
            self.failed.append(label)


def main():
    log = Log()
    scratch = tempfile.mkdtemp(prefix="gtq-items-")
    src = {n: tuple(read(os.path.join(FOLDER, n + ext)) for ext in (".md", ".provenance.yaml", ".decisions.md")) for n in (SAMPLE, NOTIF)}
    good = {n: read(os.path.join(FOLDER, n + ".work-items.md")) for n in (SAMPLE, NOTIF)}
    facts = {n: extract.check(good[n], *src[n])[1] for n in (SAMPLE, NOTIF)}
    before = digests()

    def trial(label, name, old, new, expect, record=None, same_file=False, text=None):
        base = good[name] if text is None else text
        found = old in base
        got = extract.check(base.replace(old, new, 1), record or src[name][0], src[name][1], src[name][2], same_file)[0]
        log.out("Spoiled: %s" % label, *["    PROBLEM: " + p for p in got] or ["    no problem reported"])
        log.check("reported: \"%s\"" % expect, found and any(expect in p for p in got))

    def rebuilt(name, change):
        extracted = copy.deepcopy(items.EXTRACTED[name])
        change({i["id"]: i for i in extracted["items"]}, extracted)
        return extract.render(name, extract.read_record(src[name][0]), extracted, src[name][0])

    try:
        log.part("PART 1. Running the extraction, and the check (the record the quest asks for)")
        for name in (SAMPLE, NOTIF):
            for ext in (".md", ".provenance.yaml", ".decisions.md"):
                shutil.copy(os.path.join(FOLDER, name + ext), scratch)
        for name in (SAMPLE, NOTIF):
            said = []
            code = extract.main(["build", name, "--folder", scratch], say=said.append)
            log.out("", "$ %s build %s --folder SCRATCH" % (COMMAND, name), *said, "exit code: %d" % code)
            log.check("%s: the extraction ran, and what it wrote in SCRATCH is byte for byte the handed-in %s.work-items.md" % (name, name),
                      code == 0 and read(os.path.join(scratch, name + ".work-items.md")) == good[name])
            said = []
            code = extract.main(["check", name], say=said.append)
            log.out("", "$ %s check %s" % (COMMAND, name), "-" * 78, *said, "-" * 78, "exit code: %d" % code)
            log.check("%s: the check passed with exit code 0 and reported no problem" % name, code == 0 and said[-1].startswith("CHECK PASSED.") and extract.check(good[name], *src[name])[0] == [])
        log.check("neither run changed any file in participant/context/transcripts, or the rules file", digests() == before)
        log.check("extraction-rules.md is byte for byte what the rules command writes", read(extract.RULES) == extract.rules_text())

        log.part("PART 2. Criteria 1 and 7: every item cites a line that exists, no item lacks a citation, and each can be traced")
        for name in (SAMPLE, NOTIF):
            f = facts[name]
            cites = [(i["id"], c) for i in f["items"] + f["refused"] for c in i["cites"]]
            log.out("%s: %d items, %d refusals, %d citations to %d different lines of the record's %d." % (
                name, len(f["items"]), len(f["refused"]), len(cites), len({c["u"] for _, c in cites}), len(f["record"]["lines"])))
            log.check("%s: every item cites at least one line, and at least one of its lines is a mention of the work itself: %s" % (name, ", ".join("%s %d" % (i["id"], len(i["cites"])) for i in f["items"])),
                      all(i["cites"] and any(c["label"].startswith("Mention ") for c in i["cites"]) for i in f["items"]))
            log.check("%s: every cited identifier is in the record, and so is every identifier written anywhere else in the file" % name,
                      all(c["u"] in f["record"]["lines"] for _, c in cites) and set(re.findall(r"\bU-\d+\b", good[name])) <= set(f["record"]["lines"]))
            log.check("%s: every quotation is the record's own words for that line, with the speaker and role the record gives: %d of %d" % (
                name, sum(1 for _, c in cites if c["words"] == f["record"]["lines"][c["u"]]["words"] and c["speaker"] == extract.who(f["record"], c["u"])), len(cites)),
                all(c["words"] == f["record"]["lines"][c["u"]]["words"] and c["speaker"] == extract.who(f["record"], c["u"]) for _, c in cites))
            log.check("%s: every line of the record is cited by an item or a refusal, or listed with why it gave no item, and none is both" % name,
                      f["cited"] | set(f["listed"]) == set(f["record"]["lines"]) and not f["cited"] & set(f["listed"]))
        trial("an item cites U-0041, and the record ends at U-0024", SAMPLE, "in U-0014: ", "in U-0041: ", "U-0041 is cited by W-03 and is not in the source record.")
        trial("an identifier that does not exist, written in a note", SAMPLE, "which is W-02.", "which is W-02, see U-0099.", "U-0099 is cited by the file and is not in the source record.")
        trial("a line cited from the other meeting's transcript", SAMPLE, "which is W-02.", "which is W-02, see tr-2026-11-04-notification-settings#U-0003.", "A line is cited from tr-2026-11-04-notification-settings, which is not this record.")
        record = src[SAMPLE][0]
        trial("line U-0014 deleted from a copy of the record", SAMPLE, "", "", "U-0014 is cited by W-03 and is not in the source record.", record=record[:record.index('<a id="U-0014">')] + record[record.index('<a id="U-0015">'):])

        def no_citation(by_id, extracted):
            by_id["W-04"]["mentions"] = []
            extracted["no_item"].update({"U-0005": "x", "U-0006": "x"})
        trial("an item with every citation taken away", SAMPLE, "", "", "W-04 cites no line of the source record. An item with no citation has no source.", text=rebuilt(SAMPLE, no_citation))
        trial("one word changed in a quotation", SAMPLE, "\"Yes, email is required. Phone is optional.\"", "\"Yes, email and phone are required.\"", "W-01 quotes U-0004 in words that are not the record's.")
        trial("a line given to another speaker", SAMPLE, "Mention 1: Priya Natarajan, Product owner, in U-0002", "Mention 1: Dana Whitfield, Tester, in U-0002", "W-01 gives U-0002 to \"Dana Whitfield, Tester\"")

        log.part("PART 3. Criterion 3: an item lists what the meeting did not say")
        log.out("Six things are asked of every item: %s. For each, the item cites a line or says NOT SAID." % ", ".join(label.lower() for _, label, _ in extract.ASKED), "")
        every = [(n, i) for n in (SAMPLE, NOTIF) for i in facts[n]["items"]]
        for name, item in every:
            log.out("  %-22s %s  said: %-22s not said: %s" % (name, item["id"], ", ".join(l.lower() for l, s in item["answers"].items() if s.startswith("said")) or "nothing",
                                                              ", ".join(l.lower() for l, s in item["answers"].items() if s.startswith("NOT"))))
        log.check("all %d items answer all six" % len(every), all(len(i["answers"]) == 6 for _, i in every))
        log.check("every item lists at least one thing the meeting did not say. The most any item has said is %d of 6" % max(i["stated_count"] for _, i in every),
                  all(any(s.startswith("NOT SAID") for s in i["answers"].values()) for _, i in every))
        log.check("wherever an item says something was said, it cites the line that says it, and nowhere does it cite a line for something it calls not said",
                  all(bool([c for c in i["cites"] if c["label"] == "Answers %s" % label.lower()]) == state.startswith("said") for _, i in every for label, state in i["answers"].items()))
        blanks = sum(1 for _, i in every for s in i["answers"].values() if s.startswith("NOT"))
        log.out("", "Across the %d items, %d of %d answers are NOT SAID. No owner is recorded unless a person took the work on in words: %d of %d items have one." % (
            len(every), blanks, 6 * len(every), sum(1 for _, i in every if i["answers"]["Owner"].startswith("said")), len(every)))
        trial("an owner written in with no line behind it", SAMPLE, "- Owner: NOT SAID.", "- Owner: said. The developer.", "W-01 says the meeting stated its owner and cites no line that does. That is a gap filled in.")
        trial("one of the six left out", SAMPLE, "- Due: NOT SAID.\n", "", "W-01 does not say whether the meeting stated its due.")

        log.part("PART 4. Criterion 4: two mentions of the same work produce one item with both citations")
        for name in (SAMPLE, NOTIF):
            for item in facts[name]["items"]:
                groups = {}
                for c in item["cites"]:
                    if c["label"].startswith("Mention "):
                        groups.setdefault(c["label"], []).append(c["u"])
                if len(groups) > 1:
                    log.out("  %-22s %s  %s: %s" % (name, item["id"], item["title"], "; ".join("%s in %s" % (label.lower(), ", ".join(us)) for label, us in sorted(groups.items()))))
        log.check("%d items are merged from more than one mention: %d in the first meeting and %d in the second. Each cites every mention" % (
            facts[SAMPLE]["merged"] + facts[NOTIF]["merged"], facts[SAMPLE]["merged"], facts[NOTIF]["merged"]), facts[SAMPLE]["merged"] == 2 and facts[NOTIF]["merged"] == 3)
        text = good[SAMPLE]
        log.check("W-01 of the first meeting, guest checkout, is stated at U-0002 and again as acceptance criteria at U-0019. It is one item, and cites both",
                  "### W-01 · decided · merged from 2 mentions" in text and "- Mention 1: Priya Natarajan, Product owner, in U-0002" in text and "- Mention 2: Priya Natarajan, Product owner, in U-0019" in text)
        log.check("no two items in either file have the same title, and no item appears twice", all(len({i["title"] for i in facts[n]["items"]}) == len(facts[n]["items"]) for n in facts))
        shared = {}
        for item in facts[SAMPLE]["items"] + [dict(i, id="n" + i["id"]) for i in facts[NOTIF]["items"]]:
            for c in item["cites"]:
                if c["label"].startswith("Mention "):
                    shared.setdefault((item["id"][0] == "n", c["u"]), set()).add(item["id"].lstrip("n"))
        both = sorted((u, sorted(owners)) for (_, u), owners in shared.items() if len(owners) > 1)
        log.out("Lines that are a mention in two items, each named in the first item's note as holding two pieces of work: %s" % "; ".join("%s in %s" % (u, " and ".join(o)) for u, o in both))
        log.check("there are 2 such lines, and no other line is a mention in more than one item", len(both) == 2)

        def duplicate(by_id, extracted):
            by_id["W-04"]["mentions"] = [["U-0013", "U-0014"]]
            extracted["no_item"].update({"U-0005": "x", "U-0006": "x"})
        trial("a second item made from the lines of W-03, as if the same work were written up twice", SAMPLE, "", "", "U-0014 is cited as a mention by W-03 and W-04. One piece of work is one item.", text=rebuilt(SAMPLE, duplicate))
        trial("a merged item's heading left saying 2 mentions after one was removed", SAMPLE,
              "- Mention 2: Priya Natarajan, Product owner, in U-0019: \"Back to the story. Acceptance criteria: a guest can pay with a card, gets an email receipt, and is offered account linking once, after the order is placed.\"\n- Supports", "- Supports",
              "W-01 says \"merged from 2 mentions\" in its heading and cites 1.")

        log.part("PART 5. Criterion 2: no item contains scope that no cited utterance supports")
        log.out("What a program can check, and does:", "")
        log.check("every item rests on a named item of the decisions file, of the kind its mark says, and cites at least one of the lines that item cites",
                  all(i["rests_on"] and all(ref in facts[n]["decisions"] and facts[n]["decisions"][ref][1] & {c["u"] for c in i["cites"]} for ref in i["rests_on"]) for n in facts for i in facts[n]["items"]))
        marks = {}
        for name in facts:
            for item in facts[name]["items"]:
                marks.setdefault(item["tags"][0], []).append("%s %s" % ("first" if name == SAMPLE else "second", item["id"]))
        for mark, ids in marks.items():
            log.out("  %-22s %d: %s" % (mark, len(ids), ", ".join(ids)))
        log.check("no item marked decided, in whole, in part or reopened, rests on a proposal, an open item or a reversed decision",
                  all(ref.startswith("D-") and "REVERSED" not in facts[n]["decisions"][ref][0] for n in facts for i in facts[n]["items"] if i["tags"][0].lower().startswith("decided") for ref in i["rests_on"]))
        log.check("a heading never reads more settled than the item: the one item with parts not settled says DECIDED IN PART, and the one resting on a reopened decision says REOPENED",
                  marks.get("DECIDED IN PART") == ["first W-02"] and marks.get("decided, REOPENED") == ["second W-04"])
        log.check("the 3 proposed items and the 1 open item say so in their headings, in capitals, and again in a note", len(marks.get("PROPOSED, NOT DECIDED", [])) == 3 and len(marks.get("OPEN, NOT SETTLED", [])) == 1
                  and good[NOTIF].count("- Note: NOT DECIDED.") == 3 and "- Note: NOT SETTLED." in good[NOTIF])
        trial("the unaccepted proposal \"drop text messages\" marked as decided", NOTIF, "### W-06 · PROPOSED, NOT DECIDED · merged from 2 mentions", "### W-06 · decided · merged from 2 mentions",
              "W-06 is marked \"decided\" and rests on P-01, which is not that kind of item.")
        trial("an item made to rest on the decision the meeting reversed", NOTIF, "- Rests on: D-06 of `notifications-meeting.decisions.md`\n- Mention 1: Noor Example", "- Rests on: D-01 of `notifications-meeting.decisions.md`\n- Mention 1: Noor Example",
              "W-01 rests on D-01, a decision that was reversed later in the meeting.")
        trial("the item with two parts not settled given a plain \"decided\" heading", SAMPLE, "### W-02 · DECIDED IN PART · merged from 3 mentions", "### W-02 · decided · merged from 3 mentions",
              "W-02 is marked \"decided\" and has a part listed as not settled. A heading must not read more settled than the item is.")
        trial("the item resting on a reopened decision given a plain \"decided\" heading", NOTIF, "### W-04 · decided, REOPENED · 1 mention", "### W-04 · decided · 1 mention",
              "W-04 is marked \"decided\", and D-03 was reopened later in the meeting. The heading has to say so.")
        trial("an item made to rest on a decision none of whose lines it cites", SAMPLE, "- Rests on: D-06 of", "- Rests on: D-03 of", "W-03 rests on D-03 and cites none of the lines that D-03 cites.")
        log.out("", "What was refused, each with the lines that could tempt:")
        for name in (SAMPLE, NOTIF):
            for r in facts[name]["refused"]:
                said_text = re.search(r"^\*\*It would have said:\*\* (.+)$", r["body"], re.M).group(1)
                log.out("  %-22s %s  %-78s %s" % (name, r["id"], said_text, ", ".join(c["u"] for c in r["cites"])))
        log.check("%d things were not made into items. Each cites the lines and says why" % sum(len(facts[n]["refused"]) for n in facts), all(r["cites"] and r["why"] for n in facts for r in facts[n]["refused"]))
        log.check("no item is made from a line the decisions file lists as reading like an instruction: U-0016 of the first meeting and U-0030 of the second are cited only by refusals",
                  not any(c["u"] in ("U-0016",) for i in facts[SAMPLE]["items"] for c in i["cites"]) and not any(c["u"] == "U-0030" for i in facts[NOTIF]["items"] for c in i["cites"])
                  and any(c["u"] == "U-0016" for r in facts[SAMPLE]["refused"] for c in r["cites"]) and any(c["u"] == "U-0030" for r in facts[NOTIF]["refused"] for c in r["cites"]))

        def from_instruction(by_id, extracted):
            by_id["W-04"]["mentions"] = [["U-0016"]]
            extracted["refused"] = [r for r in extracted["refused"] if r["id"] != "R-03"]
            extracted["no_item"].update({"U-0005": "x", "U-0006": "x", "U-0017": "x", "U-0018": "x"})
        trial("an item made from the line addressed to an AI assistant", SAMPLE, "", "", "W-04 is made from U-0016, which the decisions file lists as a line that reads like an instruction.", text=rebuilt(SAMPLE, from_instruction))
        added = good[SAMPLE].replace("**Intent:** The phone number goes on the shipping label only, for the carrier, and is not used for marketing.",
                                     "**Intent:** The phone number goes on the shipping label only, for the carrier, is deleted after thirty days and is not used for marketing.")
        got = extract.check(added, *src[SAMPLE])[0]
        log.out("", "What the check does NOT catch. A clause that no line supports, \"is deleted after thirty days\", was added to the intent of W-03.",
                "The check reports: %s" % ("; ".join(got) or "no problem."),
                "The check sees an item that cites real lines. It cannot read the intent and the lines and tell that one says more than the",
                "other. Whether an item adds scope is a judgment, and logs/blind-read.txt records what three independent readers found.")
        log.check("that limit is real and is recorded here, not hidden: the check passes the invented clause", got == [] and added != good[SAMPLE])

        log.part("PART 6. Criterion 5: items are stored apart from the source record, which is not edited")
        for name in (SAMPLE, NOTIF):
            stated = re.search(r"^record_sha256: (\S+)$", src[name][1], re.M).group(1)
            now = extract.sha(src[name][0])
            log.out("%s.md" % name, "  SHA-256 now:                          %s" % now, "  SHA-256 its provenance file recorded: %s" % stated)
            log.check("%s.md is byte for byte the record the ingest skill wrote, and %s.work-items.md is another file that states that SHA-256 as its source" % (name, name),
                      now == stated and ("- source_sha256: `%s`" % now) in good[name])
        done = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", "participant/context/transcripts", "participant/context/decision-rules.md", "participant/skills/ba-ingest-transcript", "participant/skills/ba-extract-decisions"], cwd=REPO)
        untracked = subprocess.run(["git", "status", "--porcelain", "--", "participant/context/transcripts"], cwd=REPO, capture_output=True, text=True).stdout.split()
        log.check("git reports no change to any approved file under participant/context/transcripts, to the decision rules, or to the two earlier skills. The only new files there are the two work-items files",
                  done.returncode == 0 and sorted(p for p in untracked if p.endswith(".md")) == ["participant/context/transcripts/notifications-meeting.work-items.md", "participant/context/transcripts/sample-meeting.work-items.md"])
        log.check("the build in SCRATCH wrote one new file for each meeting and left the record, the provenance file and the decisions file as they were",
                  sorted(os.listdir(scratch)) == sorted(n + ext for n in (SAMPLE, NOTIF) for ext in (".md", ".provenance.yaml", ".decisions.md", ".work-items.md"))
                  and all(read(os.path.join(scratch, n + ext)) == src[n][k] for n in (SAMPLE, NOTIF) for k, ext in enumerate((".md", ".provenance.yaml", ".decisions.md"))))
        trial("one space added to the end of a copy of the record", SAMPLE, "", "", "The source record has been changed since it was ingested", record=record + " ")
        trial("an item written into a copy of the record", SAMPLE, "", "", "The source record holds work items. They do not belong in the record.", record=record + "\n### W-01 · decided · 1 mention\n")
        trial("one file given as both the record and the work-items file", SAMPLE, "", "", "The work-items file and the source record are the same file.", same_file=True)

        log.part("PART 7. Criterion 6: nothing is written to an external tracker")
        probe = ("import sys, tempfile, shutil, os; sys.path.insert(0, %r); import extract; d = tempfile.mkdtemp()\n"
                 "for n in ('sample-meeting', 'notifications-meeting'):\n"
                 "    for e in ('.md', '.provenance.yaml', '.decisions.md'): shutil.copy(os.path.join(extract.FOLDER, n + e), d)\n"
                 "    extract.main(['build', n, '--folder', d], say=lambda l: None); extract.main(['check', n, '--folder', d], say=lambda l: None)\n"
                 "shutil.rmtree(d)\n"
                 "print(sorted(m for m in sys.modules if m.split('.')[0] in ('socket', 'ssl', 'http', 'urllib', 'smtplib', 'ftplib', 'subprocess')))" % SKILL)
        done = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True)
        log.out(*(["The probe itself failed: " + done.stderr.strip().splitlines()[-1]] if done.returncode else []))
        log.out("Modules for connecting, mailing or running another program that Python had loaded after a build and a check of both meetings: %s" % done.stdout.strip())
        log.check("none was loaded, so nothing could have been sent to a tracker or anywhere else", done.stdout.strip() == "[]")
        log.check("each file says at its top that nothing was created in any tracker, and the build says so when it runs", all("**Nothing here was created\nin any tracker**" in good[n] for n in good))
        log.check("no work-items file holds a web address or an email address", not any(mark in good[n] for n in good for mark in ("http:", "https:", "@")))

        log.part("PART 8. Stretch goals: items ranked by how much the meeting specified, and items from one speaker flagged")
        for name in (SAMPLE, NOTIF):
            table = good[name][good[name].index("| Item | Title |"):good[name].index("\nItems: ")]
            rows = [row for row in table.splitlines()[2:] if row.startswith("| W-")]
            log.out(name, *["  " + row for row in rows])
            counts = [int(row.split("|")[4]) for row in rows]
            log.check("%s: the table lists all %d items, most said first: %s" % (name, len(rows), ", ".join(str(c) for c in counts)), counts == sorted(counts, reverse=True) and len(rows) == len(facts[name]["items"]))
        flagged = [(n, i["id"]) for n in facts for i in facts[n]["items"] if i["one_speaker"]]
        log.check("%d items are flagged as resting on one speaker only: %s. For each, every cited line is that speaker's, and no other item's lines are all one speaker's" % (len(flagged), ", ".join("%s %s" % ("first" if n == SAMPLE else "second", i) for n, i in flagged)),
                  all(i["one_speaker"] == (len({facts[n]["record"]["lines"][c["u"]]["speaker"] for c in i["cites"]}) == 1) for n in facts for i in facts[n]["items"]) and len(flagged) >= 2)
        trial("the one-speaker flag removed from an item that needs it", SAMPLE, "- ONE SPEAKER: every line cited is Marcus Oyelaran's. Nobody else in the meeting is on record about it.\n", "", "W-06 cites one speaker only and is not flagged.")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    log.check("at the end, every file in participant/context/transcripts and the rules file are what they were at the start", digests() == before)
    log.lines += ["", "RESULT: %s" % ("%d OF %d CHECKS FAILED." % (len(log.failed), log.count) if log.failed else "ALL CHECKS PASSED. %d checks." % log.count)]
    os.makedirs(LOGS, exist_ok=True)
    with open(os.path.join(LOGS, "extraction-run.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(log.lines) + "\n")
    print("extraction-run.txt: %s" % log.lines[-1])
    for label in log.failed:
        print("  FAILED: %s" % label)
    return 1 if log.failed else 0


if __name__ == "__main__":
    sys.exit(main())
