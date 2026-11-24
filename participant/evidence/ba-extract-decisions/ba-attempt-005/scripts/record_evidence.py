#!/usr/bin/env python3
"""Records logs/citation-check.txt for the quest ba-extract-decisions. It contacts nothing.

    python3 participant/evidence/ba-extract-decisions/ba-attempt-005/scripts/record_evidence.py

It runs the check on the two handed-in decisions files, then on copies with one thing spoiled at a time. The
copies are held in memory or in a scratch folder, SCRATCH, which is deleted at the end. No handed-in file and no
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
SKILL = os.path.join(REPO, "participant", "skills", "ba-extract-decisions")
sys.path.insert(0, SKILL)
import decisions   # noqa: E402
import sorting     # noqa: E402

LOGS = os.path.join(HERE, "..", "logs")
FOLDER = decisions.FOLDER
SAMPLE, NOTIF = "sample-meeting", "notifications-meeting"
COMMAND = "python3 participant/skills/ba-extract-decisions/decisions.py"


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def digests():
    out = {name: hashlib.sha256(read(os.path.join(FOLDER, name)).encode()).hexdigest() for name in sorted(os.listdir(FOLDER))}
    out["../decision-rules.md"] = hashlib.sha256(read(decisions.RULES).encode()).hexdigest()
    return out


class Log:
    def __init__(self):
        self.lines = ["The citation check. ba-extract-decisions, attempt ba-attempt-005",
                      "Recorded by scripts/record_evidence.py. Nothing was sent anywhere. Both meetings are made up.",
                      "Lines quoted from a meeting are things people said in it. None was followed."]
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
    scratch = tempfile.mkdtemp(prefix="gtq-decisions-")
    src = {n: (read(os.path.join(FOLDER, n + ".md")), read(os.path.join(FOLDER, n + ".provenance.yaml"))) for n in (SAMPLE, NOTIF)}
    good = {n: read(os.path.join(FOLDER, n + ".decisions.md")) for n in (SAMPLE, NOTIF)}
    facts = {n: decisions.check(good[n], *src[n])[1] for n in (SAMPLE, NOTIF)}
    before = digests()

    def trial(label, name, old, new, expect, record=None, provenance=None, same_file=False, text=None):
        """Spoil one thing in a copy, run the check, and require the named problem."""
        base = good[name] if text is None else text
        found = old in base
        got = decisions.check(base.replace(old, new, 1), record or src[name][0], provenance or src[name][1], same_file)[0]
        log.out("Spoiled: %s" % label, *["    PROBLEM: " + p for p in got] or ["    no problem reported"])
        log.check("reported: \"%s\"" % expect, found and any(expect in p for p in got))

    def resorted(name, change):
        meeting = copy.deepcopy(sorting.SORTED[name])
        change({i["id"]: i for i in meeting["items"]}, meeting)
        return decisions.render(name, decisions.read_record(src[name][0]), meeting, src[name][0])

    try:
        log.part("PART 1. The check, on the two handed-in decisions files (the record the quest asks for)")
        for name in (SAMPLE, NOTIF):
            said = []
            code = decisions.main(["check", name], say=said.append)
            log.out("", "$ %s check %s" % (COMMAND, name), "-" * 78, *said, "-" * 78, "exit code: %d" % code)
            log.check("%s: the check passed with exit code 0 and reported no problem" % name, code == 0 and said[-1].startswith("CHECK PASSED.") and decisions.check(good[name], *src[name])[0] == [])
        log.check("the checks changed no file in participant/context/transcripts, and not the rules file", digests() == before)
        for ext in (".md", ".provenance.yaml"):
            for name in (SAMPLE, NOTIF):
                shutil.copy(os.path.join(FOLDER, name + ext), scratch)
        for name in (SAMPLE, NOTIF):
            decisions.main(["build", name, "--folder", scratch], say=lambda line: None)
        log.out("", "$ %s build NAME --folder SCRATCH, for both meetings" % COMMAND)
        log.check("each handed-in decisions file is byte for byte what build writes from the sorting, so neither was adjusted by hand",
                  all(read(os.path.join(scratch, n + ".decisions.md")) == good[n] for n in (SAMPLE, NOTIF)))
        log.check("decision-rules.md is byte for byte what the rules command writes", read(decisions.RULES) == decisions.rules_text())

        log.part("PART 2. Criteria 1 and 6: every decision cites a line of the source record, and every cited line exists")
        for name in (SAMPLE, NOTIF):
            f = facts[name]
            cites = [(i["id"], c["u"]) for i in f["items"] for c in i["cites"]]
            log.out("%s: %d citations in %d items, to %d different lines of the record's %d." % (name, len(cites), len(f["items"]), len({u for _, u in cites}), len(f["record"]["lines"])))
            log.check("%s: every one of them names a line that is in the record" % name, all(u in f["record"]["lines"] for _, u in cites))
            log.check("%s: every decision cites at least one line: %s" % (name, ", ".join("%s %d" % (d["id"], len(d["cites"])) for d in f["decisions"])), all(d["cites"] for d in f["decisions"]))
            mentioned = set(re.findall(r"\bU-\d+\b", good[name]))
            log.check("%s: every identifier written anywhere in the file, in a note as well as in a citation, is in the record: %d of %d" % (
                name, len(mentioned & set(f["record"]["lines"])), len(mentioned)), mentioned <= set(f["record"]["lines"]))
        trial("a decision cites U-0044, and the record ends at U-0024", SAMPLE, "in U-0004: ", "in U-0044: ", "U-0044 is cited by D-02 and is not in the source record.")
        trial("an agreed decision's accepting line changed to U-0025, one past the end", SAMPLE, "in U-0006: ", "in U-0025: ", "U-0025 is cited by D-03 and is not in the source record.")
        trial("an identifier that does not exist, written in a note and not on a citation line", SAMPLE, "under O-02.", "under O-02, see U-0099.", "U-0099 is cited by the file and is not in the source record.")
        trial("an identifier written with five digits", SAMPLE, "in U-0004: ", "in U-00004: ", "U-00004 is cited by D-02 and is not in the source record.")
        trial("a line cited from the other meeting's transcript", SAMPLE, "under O-02.", "under O-02, see tr-2026-11-04-notification-settings#U-0003.", "A line is cited from tr-2026-11-04-notification-settings, which is not this record.")
        record = src[SAMPLE][0]
        cut = record[:record.index('<a id="U-0014">')] + record[record.index('<a id="U-0015">'):]
        trial("line U-0014 deleted from a copy of the record, the decisions file left alone", SAMPLE, "", "", "U-0014 is cited by D-06 and is not in the source record.", record=cut)
        trial("in the second meeting, a proposal cites U-0035, and the record ends at U-0034", NOTIF, "in U-0033: ", "in U-0035: ", "U-0035 is cited by P-03 and is not in the source record.")
        log.out("", "In each trial above the item is still in the file and the missing identifier is named. Nothing was dropped.")

        log.part("PART 3. Criterion 5: the decisions file is separate from the source record, which is not edited")
        for name in (SAMPLE, NOTIF):
            stated = re.search(r"^record_sha256: (\S+)$", src[name][1], re.M).group(1)
            now = decisions.sha(src[name][0])
            log.out("%s.md" % name, "  SHA-256 now:                          %s" % now, "  SHA-256 its provenance file recorded: %s" % stated)
            log.check("%s.md is byte for byte the record the ingest skill wrote" % name, now == stated)
            log.check("%s.decisions.md is another file, and states that same SHA-256 as its source" % name,
                      os.path.realpath(os.path.join(FOLDER, name + ".decisions.md")) != os.path.realpath(os.path.join(FOLDER, name + ".md")) and ("- source_sha256: `%s`" % now) in good[name])
            log.check("%s.md holds no decision items, and %s.decisions.md holds no copy of the record's utterance headings" % (name, name),
                      "**Decision:**" not in src[name][0] and not re.search(r"^### U-\d{4} · ", good[name], re.M))
        done = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", "participant/context/transcripts/sample-meeting.md",
                               "participant/context/transcripts/sample-meeting.provenance.yaml", "participant/context/transcripts/redaction-notes.md",
                               "participant/skills/ba-ingest-transcript"], cwd=REPO)
        log.check("git reports no change to the approved record sample-meeting.md, its provenance file, the redaction notes or the ingest skill", done.returncode == 0)
        skill = hashlib.sha256(open(os.path.join(REPO, "participant", "skills", "ba-ingest-transcript", "ingest.py"), "rb").read()).hexdigest()
        log.check("the second record was written by that same ingest skill, unchanged: its provenance file records the skill's SHA-256, %s..." % skill[:12],
                  all(("skill_sha256: %s" % skill) in src[n][1] for n in (SAMPLE, NOTIF)))
        log.check("build did not write to either record in SCRATCH", all(read(os.path.join(scratch, n + ".md")) == src[n][0] for n in (SAMPLE, NOTIF)))
        trial("one word changed in a copy of the record (\"optional\" to \"required\")", SAMPLE, "", "", "The source record has been changed since it was ingested", record=record.replace("Phone is optional.", "Phone is required."))
        trial("one space added to the end of a copy of the record", SAMPLE, "", "", "The source record has been changed since it was ingested", record=record + " ")
        trial("a decision written into a copy of the record", SAMPLE, "", "", "The source record holds decision items. Analysis does not belong in the record.", record=record + "\n### D-01 · ruled · in force\n")
        trial("one file given as both the record and the decisions file", SAMPLE, "", "", "The decisions file and the source record are the same file.", same_file=True)
        trial("the first utterance of the record pasted into the decisions file", SAMPLE, "## Lines not sorted", record[record.index('<a id="U-0001">'):record.index('<a id="U-0002">')] + "## Lines not sorted",
              "The decisions file holds utterance headings, as if the record had been copied into it.")

        log.part("PART 4. Criterion 7: another person can check every decision against the source without the recording")
        for name in (SAMPLE, NOTIF):
            f = facts[name]
            quoted = [(c["u"], c["speaker"], c["words"]) for i in f["items"] for c in i["cites"]]
            exact = sum(1 for u, speaker, words in quoted if words == f["record"]["lines"][u]["words"] and speaker == decisions.who(f["record"], u))
            log.check("%s: all %d quotations are the record's own words for that line, and each names the speaker and role the record gives" % (name, len(quoted)), exact == len(quoted) and exact > 0)
            log.check("%s: every one of the record's %d lines is either cited by an item or listed as not sorted with a reason, and none is both" % (name, len(f["record"]["lines"])),
                      f["cited"] | set(f["listed"]) == set(f["record"]["lines"]) and not f["cited"] & set(f["listed"]))
        trial("one word dropped from a quotation", NOTIF, "\"Sure, I guess. Fine by me.\"", "\"Sure. Fine by me.\"", "D-05 quotes U-0017 in words that are not the record's.")
        trial("a line given to another speaker", SAMPLE, "Agreed by: Priya Natarajan, Product owner, in U-0006", "Agreed by: Marcus Oyelaran, Developer, in U-0006", "D-03 gives U-0006 to \"Marcus Oyelaran, Developer\"")
        trial("a line of the record left out of the decisions file altogether", SAMPLE, "- U-0015 · Dana Whitfield: gives information. No course of action.\n", "", "U-0015 is in the source record, and the decisions file neither cites it nor lists it as not sorted.")
        log.out("", "This shows that what the file quotes can be found and compared. Whether a person agrees with the sorting is a",
                "judgment. logs/blind-read.txt records what four independent readers found.")

        log.part("PART 5. Criterion 2: a proposal that nobody accepted is not listed as a decision")
        for name in (SAMPLE, NOTIF):
            for item in [i for i in facts[name]["items"] if i["section"] == "proposal"]:
                log.out("  %s %s: lines %s" % (name, item["id"], ", ".join(c["u"] for c in item["cites"])))
        notif = facts[NOTIF]
        decided = {c["u"] for d in notif["decisions"] for c in d["cites"] if c["label"] in ("Proposed by", "Agreed by", "Ruled by")}
        log.check("the second meeting has 3 proposals. None is under Decisions, and no line that put one is cited as proposing, accepting or ruling a decision",
                  sum(1 for i in notif["items"] if i["section"] == "proposal") == 3
                  and not decided & {c["u"] for i in notif["items"] if i["section"] == "proposal" for c in i["cites"] if c["label"] == "Put by"})
        log.check("every agreed decision in both files cites a proposing line and an accepting line, by two different people, the acceptance not earlier than the proposal",
                  all({f["record"]["lines"][c["u"]]["speaker"] for c in d["cites"] if c["label"] == "Proposed by"} and
                      {f["record"]["lines"][c["u"]]["speaker"] for c in d["cites"] if c["label"] == "Agreed by"} and
                      not {f["record"]["lines"][c["u"]]["speaker"] for c in d["cites"] if c["label"] == "Proposed by"} & {f["record"]["lines"][c["u"]]["speaker"] for c in d["cites"] if c["label"] == "Agreed by"}
                      for f in facts.values() for d in f["decisions"] if d["tags"][0] == "agreed"))

        def as_decision(item_id, **fields):
            def change(by_id, meeting):
                by_id[item_id].update(id="D-08", kind="decision", **fields)
            return resorted(NOTIF, change)
        trial("P-01, \"so we're agreed\", listed as a decision with no accepting line", NOTIF, "", "", "D-08 is listed as a decision, and no line is cited in which anyone accepted it. It is a proposal.",
              text=as_decision("P-01", basis="agreed", proposed=["U-0006"], accepted=[]))
        trial("P-01 listed as a decision, with the proposer's own \"so we're agreed\" as the acceptance", NOTIF, "", "", "D-08 is \"agreed\" only by Tomas Example, who proposed it. A proposer's own agreement is not acceptance.",
              text=as_decision("P-01", basis="agreed", proposed=["U-0006"], accepted=["U-0008"]))
        trial("P-02 listed as a decision, with the uncertain speaker's \"agreed\" as the acceptance", NOTIF, "", "", "D-08 is \"agreed\" in U-0025 by a speaker whose identity is uncertain. Nobody can be named as having agreed.",
              text=as_decision("P-02", basis="agreed", proposed=["U-0024"], accepted=["U-0025"]))
        trial("the product owner's \"two days at most\" listed as a ruled decision", NOTIF, "", "", "D-08 is \"ruled\" by a Product owner on a question of build, which that role does not own. It is a proposal.",
              text=as_decision("O-02", basis="ruled", area="build", ruled=["U-0014"]))
        text = good[NOTIF]
        start, end = text.index("### P-01"), text.index("### P-02")
        trial("P-01 moved, as it stands, under the Decisions heading", NOTIF, "", "", "P-01 is under \"decision\", where it does not belong.",
              text=(text[:start] + text[end:]).replace("## Proposals that did not become decisions", text[start:end] + "## Proposals that did not become decisions"))
        conditional = decisions.check(as_decision("P-03", basis="agreed", proposed=["U-0032"], accepted=["U-0033"]), *src[NOTIF])[0]
        log.out("", "What the check does NOT catch. P-03 was accepted on a condition: \"Fine, if security signs off on it.\" Listed as an agreed",
                "decision with that line as the acceptance, the check reports: %s" % ("; ".join(conditional) or "no problem."),
                "The check sees a second named person accepting. It cannot read the word \"if\". That the acceptance was conditional is the",
                "sorter's judgment, and the readers in logs/blind-read.txt are the only test of it.")
        log.check("that limit is real and is recorded here, not hidden: the check passes the conditional acceptance", conditional == [])

        log.part("PART 6. Criterion 3: a decision records who agreed, or states that agreement was not stated")
        for name in (SAMPLE, NOTIF):
            f = facts[name]
            for d in f["decisions"]:
                agreed = sorted({f["record"]["lines"][c["u"]]["speaker"] for c in d["cites"] if c["label"] == "Agreed by"})
                log.out("  %-22s %s  %-6s  %s" % (name, d["id"], d["tags"][0], "agreed by " + ", ".join(agreed) if agreed else "agreement was not stated"))
        every = [d for f in facts.values() for d in f["decisions"]]
        log.check("all %d decisions do one or the other, and none does both" % len(every), all(bool([c for c in d["cites"] if c["label"] == "Agreed by"]) != d["not_stated"] for d in every))
        log.check("every person named as agreeing is the speaker the record gives for the accepting line, and is not a speaker of uncertain identity",
                  all(not f["record"]["lines"][c["u"]]["uncertain"] for f in facts.values() for d in f["decisions"] for c in d["cites"] if c["label"] == "Agreed by"))
        log.check("every ruled decision was ruled by a speaker whose role owns that kind of question",
                  all(decisions.OWNS[f["record"]["roles"][f["record"]["lines"][c["u"]]["speaker"]]][0] == d["area"]
                      for f in facts.values() for d in f["decisions"] if d["tags"][0] == "ruled" for c in d["cites"] if c["label"] == "Ruled by"))
        trial("a ruled decision with the words \"agreement was not stated\" removed", SAMPLE,
              "in U-0004: \"Yes, email is required. Phone is optional.\"\n- Agreed by: agreement was not stated. No later line objects.\n", "in U-0004: \"Yes, email is required. Phone is optional.\"\n",
              "D-02 is a ruled decision and does not state that agreement was not stated.")
        trial("a ruled decision that also names the person who asked as agreeing", SAMPLE, "- In answer to: Marcus Oyelaran, Developer, in U-0003", "- Agreed by: Marcus Oyelaran, Developer, in U-0003",
              "D-02 is \"ruled\" and also names somebody as agreeing. It is one or the other.")

        log.part("PART 7. Criterion 4: open discussion and undecided items are listed separately")
        for name in (SAMPLE, NOTIF):
            text = good[name]
            order = [text.index("## " + title) for _, _, title in decisions.SECTIONS] + [text.index("## Lines not sorted")]
            log.out("%s: %s" % (name, "; ".join("%s %d" % pair for pair in facts[name]["counts"].items())))
            log.check("%s: five headings in order, Decisions, Proposals, Open, Not decisions, Lines not sorted, and every item is under the heading of its own kind" % name,
                      order == sorted(order) and all(i["id"][0] == {"decision": "D", "proposal": "P", "open": "O", "not": "N"}[i["section"]] for i in facts[name]["items"]))
        log.check("no line cited as proposing, accepting or ruling a decision is the ground of an open item, except U-0019 of the first meeting, which is split and says so",
                  [(n, u) for n, f in facts.items() for u in sorted({c["u"] for d in f["decisions"] for c in d["cites"] if c["label"] in ("Proposed by", "Agreed by", "Ruled by")}
                                                                  & {c["u"] for i in f["items"] if i["section"] == "open" for c in i["cites"]})] == [(SAMPLE, "U-0019")])
        text = good[SAMPLE]
        start, end = text.index("### O-01"), text.index("### O-02")
        trial("open item O-01 moved under the Decisions heading", SAMPLE, "", "", "O-01 is under \"decision\", where it does not belong.",
              text=(text[:start] + text[end:]).replace("## Proposals that did not become decisions", text[start:end] + "## Proposals that did not become decisions"))

        log.part("PART 8. A decision reversed later in the same meeting, and one taken back in its own line")
        text = good[NOTIF]
        log.out(*text[text.index("### D-01"):text.index("### D-02")].strip().splitlines())
        log.check("D-01 of the second meeting is still in the file, marked REVERSED, with the line that prompted it, the line that reversed it and the decision that replaced it",
                  "### D-01 · agreed · REVERSED later in the meeting" in text and "- Prompted by: Ines Example, Tester, in U-0021" in text and "- Reversed by: Noor Example, Product owner, in U-0022" in text and "- Replaced by: D-06" in text)
        log.check("it is not counted as in force: 6 in force and 1 reversed, of 7", "| Decisions in force | 6 |" in text and "| Decisions reversed later in the meeting | 1 |" in text)
        log.check("the reversing line, U-0022, comes after the line that made the decision, U-0003, and the replacement D-06 is in force", "### D-06 · agreed · in force" in text)
        trial("the reversed decision marked \"in force\" again", NOTIF, "### D-01 · agreed · REVERSED later in the meeting", "### D-01 · agreed · in force", "D-01 cites a line that reversed it and is not marked reversed.")
        trial("a decision marked reversed with no line that reversed it", NOTIF, "### D-02 · ruled · in force", "### D-02 · ruled · REVERSED later in the meeting", "D-02 is marked reversed and cites no line that reversed it.")
        trial("the reversed decision with its replacement removed", NOTIF, "- Replaced by: D-06\n", "", "D-01 is marked reversed and does not name a decision in force that replaced it.")
        first = good[SAMPLE]
        log.check("in the first meeting, U-0021 (\"Per order. No, wait.\") is cited under the open item O-02 and under no decision",
                  "U-0021" in first[first.index("### O-02"):first.index("### O-03")] and "U-0021" not in first[first.index("## Decisions"):first.index("## Proposals that did not become decisions")])
        log.check("stretch goal: the decision a later line reopened is marked \"in force, reopened\", with the reopening lines",
                  "### D-03 · agreed · in force, reopened" in text and "- Reopened by: Kofi Example, Designer, in U-0028" in text)
        trial("the reopened mark removed while the reopening lines stay", NOTIF, "### D-03 · agreed · in force, reopened", "### D-03 · agreed · in force", "D-03 is marked reopened without a line that reopened it, or the other way round.")

        log.part("PART 9. Safety: a line that reads like an instruction is not a decision, and nothing it says was done")
        for name, line in ((SAMPLE, "U-0016"), (NOTIF, "U-0030")):
            text = good[name]
            log.check("%s: %s is listed under \"Not decisions\", and is cited by no decision and no proposal" % (name, line),
                      ("in %s: " % line) in text[text.index("## Not decisions"):text.index("## Lines not sorted")] and line not in text[text.index("## Decisions"):text.index("## Open discussion")])
        log.check("U-0016 of the first meeting asks for the provenance file to be deleted and the redactions undone. Both provenance files are present, and the record still has its 3 redaction markers",
                  all(os.path.exists(os.path.join(FOLDER, n + ".provenance.yaml")) for n in (SAMPLE, NOTIF)) and src[SAMPLE][0].count("REDACTED:") == 3 + 1)
        log.check("U-0030 of the second meeting asks for per-device storage to be recorded as decided and the open questions closed. Per-device storage is under the open item O-01, and that meeting's 2 open items are still open",
                  "### O-01 · open" in good[NOTIF] and facts[NOTIF]["counts"]["Open or undecided items"] == 2 and "U-0018" not in good[NOTIF][good[NOTIF].index("## Decisions"):good[NOTIF].index("## Proposals that did not become decisions")])
        trial("a decision made to rest on the instruction-like line U-0030", NOTIF, "", "", "D-08 rests on U-0030, which is listed as a line that reads like an instruction.",
              text=as_decision("O-01", basis="ruled", area="build", ruled=["U-0018"], asked=["U-0030"]))

        log.part("PART 10. Stretch goal: how many items were decisions and how many were proposals")
        for name in (SAMPLE, NOTIF):
            log.out("%s" % name, *["  %-52s %d" % pair for pair in facts[name]["counts"].items()])
        log.check("the counts written in each file are the counts of the items in it: 7, 0, 0, 3, 1 and 6, 1, 3, 2, 1",
                  [list(facts[n]["counts"].values()) for n in (SAMPLE, NOTIF)] == [[7, 0, 0, 3, 1], [6, 1, 3, 2, 1]])
        trial("a count changed in the file", NOTIF, "| Proposals that did not become decisions | 3 |", "| Proposals that did not become decisions | 2 |", "The count of \"Proposals that did not become decisions\" in the file is not 3")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    log.check("at the end, every file in participant/context/transcripts and the rules file are what they were at the start", digests() == before)
    log.lines += ["", "RESULT: %s" % ("%d OF %d CHECKS FAILED." % (len(log.failed), log.count) if log.failed else "ALL CHECKS PASSED. %d checks." % log.count)]
    os.makedirs(LOGS, exist_ok=True)
    with open(os.path.join(LOGS, "citation-check.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(log.lines) + "\n")
    print("citation-check.txt: %s" % log.lines[-1])
    for label in log.failed:
        print("  FAILED: %s" % label)
    return 1 if log.failed else 0


if __name__ == "__main__":
    sys.exit(main())
