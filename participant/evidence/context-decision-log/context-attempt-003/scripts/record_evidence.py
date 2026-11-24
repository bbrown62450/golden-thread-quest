#!/usr/bin/env python3
"""Records logs/log-check.txt for the quest context-decision-log. It contacts nothing.

    python3 participant/evidence/context-decision-log/context-attempt-003/scripts/record_evidence.py

Part 1 checks the handed-in log, participant/context/decisions/log.md, and changes nothing. Parts 2 to 4 work on a copy of
it in a scratch folder, SCRATCH, which is deleted at the end: a status change is made there, and the log is broken there
in one way at a time, to show what the check reports.
"""
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "participant", "skills", "context-decision-log"))
import decisions      # noqa: E402

REAL = os.path.join(REPO, "participant", "context", "decisions")
LOGS = os.path.join(HERE, "..", "logs")
NEW = """
### E-015 · decision

- status: decision
- date: 2026-10-02
- title: A failed export is tried three times, then the on-call engineer is alerted
- source: design document DOC-9, section 1
- kind: technical
- approver: tech lead
- approved_in: decision record DR-9, comment 1
- approval_words: "Approved as written in DOC-9 section 1."
- affects: WX-20
- promotes: E-012
- answers: E-011

**Decision.** A failed export is tried again up to three times, ten minutes apart, and then the on-call engineer is alerted.
"""


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class Log:
    def __init__(self):
        self.lines = ["The check of the decision log. context-decision-log, attempt context-attempt-003",
                      "Recorded by scripts/record_evidence.py. No request was sent anywhere. The log's project, documents, work items and roles are all made up."]
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

    def command(self, log_path, name, shown):
        said = []
        code = decisions.main([name, "--log", log_path], say=said.append)
        self.out("$ python3 participant/skills/context-decision-log/decisions.py %s%s" % (name, shown), "-" * 78, *said, "-" * 78, "exit code: %d" % code)
        return code, said


def main():
    log = Log()
    text = read(os.path.join(REAL, "log.md"))
    ledger = json.loads(read(os.path.join(REAL, "ledger.json")))
    entries = decisions.parse(text)
    state = decisions.states(entries)
    by = lambda status: [entry for entry in entries if entry["fields"].get("status") == status]

    log.part("PART 1. The handed-in log is checked. participant/context/decisions/log.md")
    code, said = log.command(os.path.join(REAL, "log.md"), "check", "")
    log.check("the check passes: exit code 0, and it says the log keeps every rule", code == 0 and said[-1].endswith("the log keeps every rule"))
    log.check("the log has %d entries, at least ten, in all three statuses: %d decisions, %d proposals, %d questions" % (len(entries), len(by("decision")), len(by("proposal")), len(by("question"))),
              len(entries) >= 10 and all(len(by(status)) >= 2 for status in decisions.STATUSES))
    log.check("every entry has exactly one status, the same in its heading and its field, and its statement opens by saying what it is (criterion 1)",
              all(entry["heading_status"] == entry["fields"]["status"] in decisions.STATUSES and not entry["repeated"]
                  and entry["statement"].startswith(decisions.OPENING[entry["fields"]["status"]]) for entry in entries))
    log.out("Every decision, with who approved it, where, and in what words:")
    for entry in by("decision"):
        fields = entry["fields"]
        log.out("  %s  %-9s approved by the %-13s in %s" % (entry["id"], fields["kind"], fields["approver"], fields["approved_in"]), "        words: %s" % fields["approval_words"],
                "        source: %s" % fields["source"])
    log.check("every one of the %d decisions has an approver, the place it was approved, the approver's quoted words, and a source (criteria 2 and 6)" % len(by("decision")),
              all(all(entry["fields"].get(name) for name in ("approver", "approved_in", "approval_words", "source", "kind", "date")) for entry in by("decision")))
    log.check("every approver is the role the rules allow for that kind of decision", all(entry["fields"]["approver"] == decisions.KINDS[entry["fields"]["kind"]][0] for entry in by("decision")))
    log.check("every decision's quoted words are words of approval or of declining, and none is only agreement",
              all(any(word in entry["fields"]["approval_words"].lower() for word in decisions.APPROVAL_WORDS) for entry in by("decision")))
    log.check("every one of the %d entries cites a source with a reference a reader can look up (criterion 6)" % len(entries),
              all(decisions.REFERENCE_SHAPE.search(entry["fields"].get("source", "")) for entry in entries))
    loose = [entry["id"] for entry in by("proposal") + by("question") if any(entry["fields"].get(name) for name in ("approver", "approved_in", "approval_words"))]
    log.check("no proposal and no question carries an approver, a place of approval or approval words (criterion 3)", not loose)
    block = text[text.index(decisions.BEGIN):text.index(decisions.END)]
    current = block.split("## What is NOT decided")[0]
    listed = re.findall(r"^\| (E-\d{3}) \|", current, re.M)
    log.out("The list of current decisions at the top of the log holds: %s" % ", ".join(listed))
    log.check("that list holds only decisions, and no proposal or question is in it (criterion 3)", all(entry_id in [entry["id"] for entry in by("decision")] for entry_id in listed))
    log.check("it holds exactly the decisions that are not superseded: 5 of the 7 (criterion 7)",
              listed == [entry["id"] for entry in by("decision") if state[entry["id"]][0] == "current"] and len(listed) == 5)
    log.check("it is at the top of the file, before the first entry, so a reader does not need the history to find it (criterion 7)",
              text.index("## What is decided now") < text.index("### E-001"))
    log.check("it is exactly what the entries say: the part on the page is byte for byte what the script writes from them", block + decisions.END == decisions.view_block(entries))
    superseded = [(entry["id"], state[entry["id"]][1]) for entry in by("decision") if state[entry["id"]][0] == "superseded"]
    log.out("Superseded decisions and what replaced them: %s" % ", ".join("%s by %s" % pair for pair in superseded))
    log.check("each superseded decision is linked to its replacement: the newer entry names it in `supersedes`, and the index shows the older one as SUPERSEDED by the newer (criterion 5)",
              len(superseded) == 2 and all("| %s |" % old in block and "SUPERSEDED by %s" % new in block and "- supersedes: %s" % old in next(e for e in entries if e["id"] == new)["text"]
                                           for old, new in superseded))
    log.check("the proposal E-005, which a ticket quotes as \"the decision\" and three stories were built on, is still a proposal, and the check warns about it (criterion 3)",
              state["E-005"] == ("open", None) and any("WARNING: E-005" in line and "WX-31, WX-32, WX-33" in line for line in said))
    log.check("the ledger holds a checksum for each of the %d entries, and each entry's text matches its checksum: none was edited since it was sealed" % len(entries),
              sorted(ledger["entries"]) == [entry["id"] for entry in entries]
              and all(hashlib.sha256(entry["text"].encode("utf-8")).hexdigest() == ledger["entries"][entry["id"]] for entry in entries))
    log.check("the rules document is exactly what the checking code writes, so the rules and the check cannot disagree", read(os.path.join(REAL, "rules.md")) == decisions.rules_document())

    scratch = tempfile.mkdtemp(prefix="gtq-decisions-")
    try:
        log.part("PART 2. A status change, in the handed-in log: the proposal E-003 became the decision E-004, and E-004 was later superseded by E-014 (criteria 4 and 5)",
                 "The three entries as they stand in the log, with the checksum the ledger holds for each:")
        for entry_id in ("E-003", "E-004", "E-014"):
            entry = next(one for one in entries if one["id"] == entry_id)
            log.out("  %s  %s  now: %s%s" % (entry_id, entry["fields"]["status"], state[entry_id][0], " by %s" % state[entry_id][1] if state[entry_id][1] else ""),
                    "        title: %s" % entry["fields"]["title"], "        ledger SHA-256: %s" % ledger["entries"][entry_id])
        proposal = next(one for one in entries if one["id"] == "E-003")
        log.check("the proposal E-003 is still in the log as a proposal, with its own text: no approver, and its statement still opens \"Proposal, not decided.\"",
                  proposal["fields"]["status"] == "proposal" and "approver" not in proposal["fields"] and proposal["statement"].startswith("**Proposal, not decided.**"))
        log.check("the decision E-004 is a separate, later entry that names it: `promotes: E-003`", next(one for one in entries if one["id"] == "E-004")["fields"].get("promotes") == "E-003")
        log.check("the superseded decision E-004 is still in the log with its own text, and still says Friday", "on Friday at 06:00 UTC" in next(one for one in entries if one["id"] == "E-004")["statement"])
        log.check("what became of each is not written into the old entry. It is in the index: E-003 approved by E-004, E-004 SUPERSEDED by E-014",
                  "| E-003 | 2026-09-08 | proposal | approved, by E-004 |" in block and "| E-004 | 2026-09-10 | decision | SUPERSEDED by E-014 |" in block
                  and "E-004" not in proposal["text"] and "E-014" not in next(one for one in entries if one["id"] == "E-004")["text"])

        log.part("PART 3. A status change made now, on a copy of the log in SCRATCH: the open proposal E-012 is approved (criterion 4)",
                 "A new entry, E-015, is added at the end of the copy. It is a decision by the tech lead that names `promotes: E-012` and `answers: E-011`. Nothing else is touched.")
        for name in ("log.md", "ledger.json"):
            shutil.copy(os.path.join(REAL, name), scratch)
        copy = os.path.join(scratch, "log.md")
        before = {entry["id"]: hashlib.sha256(entry["text"].encode("utf-8")).hexdigest() for entry in entries}
        with open(copy, "a", encoding="utf-8") as f:
            f.write(NEW)
        code, said = log.command(copy, "check", " --log SCRATCH/log.md")
        log.check("before the view is rewritten and the entry sealed, the check fails, and says exactly those two things", code == 2 and len([line for line in said if "RULE BROKEN" in line]) == 2
                  and any("is not what the entries say" in line for line in said) and any("E-015: the entry is not sealed yet" in line for line in said))
        log.command(copy, "view", " --log SCRATCH/log.md")
        log.command(copy, "seal", " --log SCRATCH/log.md")
        code, said = log.command(copy, "check", " --log SCRATCH/log.md")
        after_entries = decisions.parse(read(copy))
        after = {entry["id"]: hashlib.sha256(entry["text"].encode("utf-8")).hexdigest() for entry in after_entries}
        after_state = decisions.states(after_entries)
        log.out("SHA-256 of the proposal E-012 before the change: %s" % before["E-012"], "SHA-256 of the proposal E-012 after the change:  %s" % after["E-012"])
        log.check("the check passes again", code == 0)
        log.check("an entry was added: 15 entries where there were 14", len(after_entries) == 15 and len(entries) == 14)
        log.check("the earlier entry was kept: the proposal E-012 is byte for byte what it was, and so is every one of the other 13", all(after[entry_id] == digest for entry_id, digest in before.items()))
        log.check("the ledger's 14 earlier checksums are unchanged, and one was added for E-015",
                  {key: value for key, value in json.loads(read(os.path.join(scratch, "ledger.json")))["entries"].items() if key != "E-015"} == ledger["entries"])
        log.check("the proposal now shows as approved by E-015, the question E-011 as answered by E-015, and E-015 is in the list of current decisions",
                  after_state["E-012"] == ("approved", "E-015") and after_state["E-011"] == ("answered", "E-015")
                  and "| E-015 |" in read(copy).split("## What is NOT decided")[0])
        log.check("the handed-in log was not touched by any of this", read(os.path.join(REAL, "log.md")) == text and json.loads(read(os.path.join(REAL, "ledger.json"))) == ledger)

        log.part("PART 4. Can the check fail? The log is broken in one way at a time, on a copy, and checked",
                 "Each case changes the handed-in log's text in one place, brings the view up to date so that only the planted fault is at issue, and checks it against the real ledger",
                 "where the case is about editing. \"Reported\" is every rule the check says is broken.")
        cases = [
            ("a decision with no approver (criterion 2)", "- approver: security lead\n", "", "a decision must have approver", False),
            ("a decision with no place of approval (criterion 2)", "- approved_in: decision record DR-7, comment 1\n", "", "a decision must have approved_in", False),
            ("a decision with no source (criterion 6)", "- source: security review DOC-11, finding 2\n", "", "a decision must have source", False),
            ("a proposal with no source (criterion 6)", "- source: customer call notes CN-2026-09-18, item 2\n- raised_by: support lead", "- raised_by: support lead", "a proposal must have source", False),
            ("a decision whose approval is \"sounds good\" in a meeting", '"Approved: no email address in any export file. User ids only."', '"Sounds good to me."', "agreement, not approval", False),
            ("a decision whose approval is that nobody objected", '"Approved: no email address in any export file. User ids only."', '"No objections were raised."', "agreement, not approval", False),
            ("a decision approved by a role that may not approve that kind", "- kind: security\n- approver: security lead", "- kind: security\n- approver: tech lead", "approved by the security lead", False),
            ("a decision whose approval is reported, not quoted", '- approval_words: "Approved: no email address in any export file. User ids only."',
             "- approval_words: the security lead said it was fine", "inside double quotes", False),
            ("a proposal given an approver, as if it were decided (criterion 3)", "- raised_by: support lead\n", "- raised_by: support lead\n- approver: product owner\n", "a proposal may not have the field approver", False),
            ("a proposal labelled as a decision in its heading (criterion 1)", "### E-008 · proposal", "### E-008 · decision", "An entry has one status", False),
            ("a proposal worded \"we will\" (criterion 3, the scenario)", "Offer the export in both formats, chosen in the account's settings.", "We will offer the export in both formats.", "worded as if it were settled", False),
            ("a proposal whose statement opens \"Decision.\" (criterion 3)", "**Proposal, not decided.** Two customers", "**Decision.** Two customers", "the statement must begin with", False),
            ("an entry with two statuses (criterion 1)", "- status: proposal\n- date: 2026-09-18", "- status: proposal\n- status: decision\n- date: 2026-09-18", "given more than once", False),
            ("a proposal edited in place into a decision, where a new entry was called for (criterion 4)", "### E-012 · proposal\n\n- status: proposal", "### E-012 · decision\n\n- status: decision",
             "E-012: the entry was changed after it was sealed", True),
            ("an old entry quietly reworded, keeping every other rule (criterion 4)", "Try a failed export again up to three times", "Try a failed export again up to five times",
             "E-012: the entry was changed after it was sealed", True),
            ("a superseded decision edited to match its replacement", "Each account's export is sent on Friday at 06:00 UTC.", "Each account's export is sent on Monday at 06:00 UTC.",
             "E-004: the entry was changed after it was sealed", True),
            ("a decision that supersedes a proposal (criterion 5)", "- supersedes: E-004", "- supersedes: E-003", "supersedes points at E-003, which is a proposal", False),
            ("a decision that supersedes one already superseded (criterion 5)", "- supersedes: E-004", "- supersedes: E-007", "E-007 was already superseded by E-009", False),
        ]
        for title, old, new, expected, with_ledger in cases:
            if text.count(old) != 1:
                log.check("%s: the case could be set up" % title, False)
                continue
            changed = text.replace(old, new)
            changed = changed[:changed.index(decisions.BEGIN)] + decisions.view_block(decisions.parse(changed)) + changed[changed.index(decisions.END) + len(decisions.END):]
            found = ["%s: %s" % one for one in decisions.check(changed, ledger if with_ledger else None)[0]]
            log.out("  CASE: %s" % title, *["    reported: %s" % one for one in found] or ["    reported: NOTHING"])
            log.check("%s: reported" % title, any(expected in one for one in found))
        removed = text[:text.index("### E-014")]
        removed = removed[:removed.index(decisions.BEGIN)] + decisions.view_block(decisions.parse(removed)) + removed[removed.index(decisions.END) + len(decisions.END):]
        found = ["%s: %s" % one for one in decisions.check(removed, ledger)[0]]
        log.out("  CASE: the newest entry is removed from the log", *["    reported: %s" % one for one in found])
        log.check("an entry removed from the log: reported", any("E-014: the entry was sealed and is no longer in the log" in one for one in found))
        stale = text.replace("| E-014 | 2026-09-30 | The export is sent every Monday at 06:00 UTC | product |", "| E-005 | 2026-09-15 | Keep each export file in the shared bucket for 90 days | security |")
        found = ["%s: %s" % one for one in decisions.check(stale, ledger)[0]]
        log.out("  CASE: the list of current decisions is edited by hand, to put the proposal E-005 in it (criteria 3 and 7)", *["    reported: %s" % one for one in found])
        log.check("a proposal written into the list of current decisions by hand: reported", any("is not what the entries say" in one for one in found))
        unlinked = text.replace("- supersedes: E-004\n", "")
        current_then = decisions.view_block(decisions.parse(unlinked)).split("## What is NOT decided")[0]
        log.out("  CASE: the newer decision E-014 is written without its `supersedes` link (criterion 5)",
                "    the list of current decisions would then hold both the Friday decision E-004 and the Monday decision E-014: %s" % ("yes" if "| E-004 |" in current_then and "| E-014 |" in current_then else "no"))
        log.check("without the link, two decisions that contradict each other would both be current. The link is what removes the older one, and the check cannot know one is missing",
                  "| E-004 |" in current_then and "| E-014 |" in current_then)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    log.lines += ["", "RESULT: %s" % ("%d OF %d CHECKS FAILED." % (len(log.failed), log.count) if log.failed else "ALL CHECKS PASSED. %d checks." % log.count)]
    os.makedirs(LOGS, exist_ok=True)
    with open(os.path.join(LOGS, "log-check.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(log.lines) + "\n")
    print("log-check.txt: %s" % log.lines[-1])
    for label in log.failed:
        print("  FAILED: %s" % label)
    return 1 if log.failed else 0


if __name__ == "__main__":
    sys.exit(main())
