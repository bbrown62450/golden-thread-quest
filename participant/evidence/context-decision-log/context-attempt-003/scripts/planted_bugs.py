#!/usr/bin/env python3
"""Records logs/planted-bugs.txt for the context-decision-log quest.

Puts one bug at a time into participant/skills/context-decision-log/decisions.py,
runs every test, notes which tests fail, and takes the bug out again. At the
end it checks that the file is the same as when it started, byte for byte.

It changes decisions.py while it runs. Do not run the skill at the same time.

Run from anywhere:  python3 scripts/planted_bugs.py
Exit code 0 if every bug was caught and the file was restored, 1 if not.
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ATTEMPT = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(ATTEMPT, "..", "..", "..", ".."))
SKILL = os.path.join(ROOT, "participant", "skills", "context-decision-log")
TARGET = os.path.join(SKILL, "decisions.py")

# (what the bug is, the text to replace, what to replace it with)
BUGS = [
    ("A. A decision does not need an approver (criterion 2)",
     '"approver": (("decision",), ("decision",), "The role that approved.', '"approver": (("decision",), (), "The role that approved.'),
    ("B. A decision does not need the place it was approved (criterion 2)",
     '"approved_in": (("decision",), ("decision",), "Where the approval is recorded', '"approved_in": (("decision",), (), "Where the approval is recorded'),
    ("C. \"Sounds good\" and \"no objections\" count as approval (the quest's hint)",
     'APPROVAL_WORDS = ("approved",', 'APPROVAL_WORDS = ("sounds good", "no objection", "makes sense", "fine by me", "looks good", "agreed", "ok", "+1", "approved",'),
    ("D. Any quoted words count as approval",
     "                elif not any(re.search(r\"(?<![a-z])%s(?![a-z])\" % re.escape(word), plain) for word in APPROVAL_WORDS):", "                elif False:"),
    ("E. An approval word inside another word counts: \"unapproved\" is read as approved",
     'any(re.search(r"(?<![a-z])%s(?![a-z])" % re.escape(word), plain) for word in APPROVAL_WORDS)', 'any(word in plain for word in APPROVAL_WORDS)'),
    ("F. A reported approval, with no quoted words, is accepted",
     "                if not quoted:\n", "                if False:\n"),
    ("G. Any role may approve any kind of decision",
     'elif kind and fields.get("approver") and fields["approver"] != KINDS[kind][0]:', 'elif False:'),
    ("H. A proposal may carry an approver (criterion 3)",
     '            if name in fields and status not in allowed:', '            if name in fields and status not in allowed and name != "approver":'),
    ("I. A proposal worded \"we will\" or \"decided\" is not noticed (criterion 3)",
     "        if status != \"decision\":\n            shown", "        if status == \"nothing\":\n            shown"),
    ("J. A statement need not say what it is (criteria 1 and 3)",
     '        if not entry["statement"].startswith(OPENING[status] + " "):', '        if False:'),
    ("K. The heading and the status field may disagree (criterion 1)",
     '        if entry["heading_status"] != status:', '        if False:'),
    ("L. A field given twice is not noticed, so an entry can have two statuses (criterion 1)",
     "            elif name in entry[\"fields\"]:\n                entry[\"repeated\"].append(name)", "            elif False:\n                pass"),
    ("M. An open proposal is listed among the current decisions (criteria 3 and 7)",
     '    current = [entry for entry in decisions if state[entry["id"]][0] == "current"]\n    field',
     '    current = [entry for entry in good if entry["fields"]["status"] != "question" and state[entry["id"]][0] in ("current", "open")]\n    field'),
    ("N. A superseded decision stays in the list of current decisions (criteria 5 and 7)",
     '(("promotes", "approved"), ("rejects", "declined"), ("supersedes", "superseded"), ("answers", "answered")):\n            target = entry["fields"].get(name)',
     '(("promotes", "approved"), ("rejects", "declined"), ("answers", "answered")):\n            target = entry["fields"].get(name)'),
    ("O. A proposal that only offers an answer closes the question",
     '            if name == "answers" and entry["fields"].get("status") != "decision":', '            if False:'),
    ("P. A view that is stale or edited by hand is not noticed (criterion 7)",
     "    elif text[text.index(BEGIN):text.index(END) + len(END)] != wanted:", "    elif False:"),
    ("Q. An entry edited after it was sealed is not noticed (criterion 4)",
     '            elif sealed[entry["id"]] != digest:', '            elif False:'),
    ("R. An entry removed from the log is not noticed (criterion 4)",
     "        for gone in sorted(set(sealed) - set(by_id)):", "        for gone in []:"),
    ("S. Sealing again replaces the checksum of an entry already sealed, so an edit can be sealed over (criterion 4)",
     'if not entry["malformed"] and entry["id"] not in sealed:               # an entry already sealed is never sealed again', 'if not entry["malformed"]:'),
    ("T. supersedes may point at a proposal (criterion 5)",
     '"promotes": "proposal", "rejects": "proposal", "supersedes": "decision", "answers": "question"}[name]', '"promotes": "proposal", "rejects": "proposal", "supersedes": by_id[target]["fields"].get("status"), "answers": "question"}[name]'),
    ("U. A decision can be superseded twice, leaving two replacements (criterion 5)",
     '            if (group, target) in taken:', '            if (group, target) in taken and group != "supersede":'),
    ("V. A source need not name anything a reader can look up (criterion 6)",
     '        for name in ("source", "approved_in"):', '        for name in ():'),
    ("W. An entry need not have a source (criterion 6)",
     '"source": (STATUSES, STATUSES, "Where the entry comes from', '"source": (STATUSES, (), "Where the entry comes from'),
    ("X. A reference may point at a later entry, or at itself",
     '            elif target not in by_id or target == here:', '            elif False:'),
    ("Y. The check quietly rewrites the view, so a check changes the log",
     '            return 2 if report(text, load_ledger(args.log), say) else 0', '            write(args.log, text[:text.index(BEGIN)] + view_block(parse(text)) + text[text.index(END) + len(END):])\n            return 2 if report(read(args.log), load_ledger(args.log), say) else 0'),
    ("Z. A current decision with no work item is not reported (stretch goal)",
     '    idle = [entry for entry in current if not ids_in(entry["fields"].get("affects", ""))]', '    idle = []'),
]


def run_tests():
    done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=SKILL,
                          capture_output=True, text=True)
    failed = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\w+) \((?:test_decisions\.)?(\w+)", done.stderr, re.M)))
    return done.stderr.strip().splitlines()[-1], ["%s.%s" % (group, name) for name, group in failed]


def main():
    with open(TARGET, encoding="utf-8") as f:
        good = f.read()
    out = ["Do the tests notice a broken check? context-decision-log, attempt context-attempt-003",
           "Recorded by scripts/planted_bugs.py.", "",
           "Each bug below was put into participant/skills/context-decision-log/decisions.py, every test was run, and the",
           "bug was taken out again. Only local files are used.", ""]
    last, failed = run_tests()
    out += ["Before any bug: %s" % last, ""]
    clean, missed = (not failed and last.startswith("OK")), []
    try:
        for title, old, new in BUGS:
            out += ["PLANTED BUG %s" % title]
            if good.count(old) != 1:
                out += ["  COULD NOT BE PLANTED: the text to replace was not found once", ""]
                missed.append(title)
                continue
            with open(TARGET, "w", encoding="utf-8") as f:
                f.write(good.replace(old, new))
            last, failed = run_tests()
            with open(TARGET, "w", encoding="utf-8") as f:
                f.write(good)
            out += ["  unittest result: %s" % last, "  tests that failed (%d):" % len(failed)]
            out += ["    " + test for test in failed] or ["    NONE. THIS BUG WAS NOT CAUGHT."]
            out += [""]
            if not failed:
                missed.append(title)
    finally:
        with open(TARGET, "w", encoding="utf-8") as f:
            f.write(good)
    with open(TARGET, encoding="utf-8") as f:
        restored = f.read() == good
    last, failed = run_tests()
    out += ["After the last bug was taken out: decisions.py is %s it was at the start. %s"
            % ("byte for byte what" if restored else "NOT what", last), ""]
    ok = clean and restored and not missed and not failed
    out += ["RESULT: %s" % ("all %d planted bugs were caught by at least one test, and the file was restored."
                            % len(BUGS) if ok else "NOT ALL AS EXPECTED: %s" % ("; ".join(missed) or "see above"))]
    os.makedirs(os.path.join(ATTEMPT, "logs"), exist_ok=True)
    with open(os.path.join(ATTEMPT, "logs", "planted-bugs.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print(out[-1])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
