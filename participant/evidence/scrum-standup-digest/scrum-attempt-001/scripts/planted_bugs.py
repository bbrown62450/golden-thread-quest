#!/usr/bin/env python3
"""Records logs/planted-bugs.txt for the scrum-standup-digest quest.

Puts one bug at a time into participant/skills/scrum-standup-digest/digest.py,
runs every test, notes which tests fail, and takes the bug out again. At the
end it checks that the file is the same as when it started, byte for byte.

It changes digest.py while it runs. Do not run the skill at the same time.

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
SKILL = os.path.join(ROOT, "participant", "skills", "scrum-standup-digest")
TARGET = os.path.join(SKILL, "digest.py")

# (what the bug is, the text to replace, what to replace it with)
BUGS = [
    ('A. The stale limit is not applied (criterion 5)',
     '        elif entry["age"] > STALE_AFTER_HOURS * 3600:',
     '        elif False:'),
    ('B. A record at exactly the limit is called stale',
     '        elif entry["age"] > STALE_AFTER_HOURS * 3600:',
     '        elif entry["age"] >= STALE_AFTER_HOURS * 3600:'),
    ("C. A record retrieved after the digest's time is treated as fresh",
     '        elif entry["age"] < 0:',
     '        elif False:'),
    ('D. A record with no readable retrieval time is treated as fresh',
     '        if at is None:\n            stale[identity] = "its record gives no retrieval time',
     '        if False:\n            stale[identity] = "its record gives no retrieval time'),
    ('E. A status the source does not state is asserted (criterion 6)',
     '    stated = {i: items[i] for i in fresh if items[i]["c"]["status_basis"] == "stated"}',
     '    stated = {i: items[i] for i in fresh}'),
    ('F. A title that says blocked makes an item blocked (criterion 7)',
     '        if c["blocked"] == "yes":\n            basis',
     '        if c["blocked"] == "yes" or "blocked" in c["title"].lower():\n            basis'),
    ("G. A person's explicit note is not counted (criterion 7)",
     '    for kind, other in notes.get(identity, []):\n        found.append',
     '    for kind, other in []:\n        found.append'),
    ('H. Aging starts a day late (criterion 8)',
     '        if days >= AGING_AFTER_DAYS:\n            aging.append',
     '        if days > AGING_AFTER_DAYS:\n            aging.append'),
    ("I. Aging is counted to the digest's time and not to retrieval (criterion 8)",
     'days = int((time_of(stated[identity]["p"]["retrieved_at"]) - changed).total_seconds() // 86400)',
     'days = int((now - changed).total_seconds() // 86400)'),
    ('J. An item not started can be aging (criterion 8)',
     '        if c["status"] != "in_progress":\n            continue\n        changed',
     '        if False:\n            continue\n        changed'),
    ('K. A removed item is not reported (criterion 9)',
     '        for identity in sorted(set(before) - now_ids):',
     '        for identity in []:'),
    ('L. An added item is not reported (criterion 9)',
     '        for identity in sorted(now_ids - set(before)):',
     '        for identity in []:'),
    ('M. A status change is reported even when one side was not asserted',
     '            if identity in stated and was.get("asserted"):',
     '            if True:'),
    ("N. The computer's clock is read (criterion 10)",
     '    now = time_of(as_of)\n    data = load(context)\n    items, notes',
     '    now = datetime.datetime.utcnow()\n    data = load(context)\n    items, notes'),
    ('O. Names on the redaction list are not taken out',
     '    for name in sorted(names, key=len, reverse=True):\n        out = re.sub',
     '    for name in []:\n        out = re.sub'),
    ('P. Email addresses are not taken out',
     're.compile(r"[\\w.+-]+@[\\w-]+(?:\\.[\\w-]+)+")), ("[customer number]"',
     're.compile(r"NOTHING-MATCHES-THIS")), ("[customer number]"'),
    ('Q. An item a run retrieved with no record is dropped silently (criterion 6)',
     '        if identity not in items and file_name(identity) not in unreadable and not any(g["what"] == identity for g in gaps):',
     '        if False:'),
    ('R. A record that cannot be read is dropped silently (criterion 6)',
     '            trouble.append(("MISSING", "items/%s" % name, "the record file cannot be read',
     '            (lambda *a: None)(("MISSING", "items/%s" % name, "the record file cannot be read'),
    ('S. A blocker with no record is not reported as missing (criterion 6)',
     '                    gap("MISSING", other, "`%s` is recorded as blocked by it, and there is no local record of it"',
     '                    (lambda *a: None)("MISSING", other, "`%s` is recorded as blocked by it, and there is no local record of it"'),
    ('T. The scoped digest holds every item',
     '    in_scope = lambda i: scope == "all" or items[i]["c"].get("assigned_to_me") == "yes"',
     '    in_scope = lambda i: True'),
    ('U. Items with nothing recorded about being blocked are not in the gap report',
     '    if unknown_blocked:',
     '    if False:'),
    ('V. A system with no fresh run is not reported',
     '        if not any(r["fresh"] for r in done_runs):',
     '        if False:'),
    ('W. The check lets a stale record be stated as current',
     '                if identity in stale and (tag != "LAST KNOWN" or number != "9"):',
     '                if False:'),
    ('X. The check lets a wrong retrieval time through (criterion 3)',
     '                if p.get("retrieved_at") != retrieved:',
     '                if False:'),
    ('Y. The check lets an item be shown as blocked with no record of it',
     '        if shown and not recorded:',
     '        if False:'),
    ('Z. The check lets a listed name through',
     '        if re.search(r"(?<!\\w)%s(?!\\w)" % re.escape(name), quiet, re.I):',
     '        if False:'),
    ('AA. The check lets a line with no citation through (criterion 2)',
     '            if not cited and not exempt:',
     '            if False:'),
    ('AB. No previous digest gives an empty list of changes and no gap',
     '    elif previous is None:\n        gap("UNSUPPORTED", "changes since the previous digest", "no previous',
     '    elif False:\n        gap("UNSUPPORTED", "changes since the previous digest", "no previous'),
    ('AC. A recorded blocking link is not reported (criterion 7)',
     '            if kind == "blocks":\n                blocking_facts.append',
     '            if False:\n                blocking_facts.append'),
    ('AD. One blocker done and one not is called every blocker done',
     '        if blockers and not not_done and not unseen:',
     '        if blockers and done:'),
    ('AE. The check lets a cited item with no record through',
     '                if identity not in items:\n                    say("Section %s cites %s, of which',
     '                if False:\n                    say("Section %s cites %s, of which'),
    ("AF. A removed item's absence is not put in the gap report",
     '            gap("UNSUPPORTED", identity, "it has gone from this digest\'s context',
     '            (lambda *a: None)("UNSUPPORTED", identity, "it has gone from this digest\'s context'),
    ('AG. A fresh-looking record whose run is not listed is asserted',
     '        elif run not in completed:',
     '        elif False:'),
    ('AH. A record that disagrees with its run about the time is asserted',
     '        elif completed[run]["retrieved_at"] != retrieved:',
     '        elif False:'),
    ('AI. Two files for one item: the later one is used',
     '        if identity in seen:',
     '        if False:'),
    ('AJ. A note whose heading names no item is used or dropped silently',
     '            trouble.append(("UNSUPPORTED", "notes/%s" % name, "the note\'s heading',
     '            (lambda *a: None)(("UNSUPPORTED", "notes/%s" % name, "the note\'s heading'),
    ('AK. Prose in a note is not reported',
     '        if len(bullets) > len(links):',
     '        if False:'),
    ('AL. A previous digest of another scope is compared with',
     '    if previous is not None and previous.get("scope") != scope:',
     '    if False:'),
    ('AM. A quote mark in a title is printed as it is',
     '(("`", "\'"), (\'"\', "\'"), ("|", "/")',
     '(("`", "\'"), ("|", "/")'),
    ('AN. A line break in a title is printed as it is',
     '    out = re.sub(r"[\\x00-\\x1f\\x7f\\u2028\\u2029]", " ", out)',
     '    out = out'),
    ('AO. A listed name is taken out of the middle of a word',
     '        out = re.sub(r"(?<!\\w)%s(?!\\w)" % re.escape(name), "[name]", out, flags=re.I)',
     '        out = re.sub(re.escape(name), "[name]", out, flags=re.I)'),
    ('AP. The previous state may be the file this run writes',
     '        if os.path.abspath(previous_path) == os.path.abspath(os.path.join(out, "digest-state.json")):',
     '        if False:'),
    ('AQ. The check lets a wrong status word through',
     '                if c and (c["status_basis"] != "stated" or not STATUS_WORDS[c["status"]].lower().startswith(word.split(",")[0])):',
     '                if False:'),
    ('AR. The check lets a fresh item be left out',
     '        if identity not in stale and "`%s`, retrieved" % identity not in sections.get("2", "") + sections.get("5", "") + sections.get("8", ""):',
     '        if False:'),
    ('AS. The check lets a wrong number of aging days through',
     '                if not days or real is None or int(days.group(1)) != real or real < AGING_AFTER_DAYS or c["status"] != "in_progress":',
     '                if False:'),
    ('AT. The check lets gap entries be taken out',
     '    if not said or int(said.group(1)) != entries:',
     '    if False:'),
    ('AU. A link saved with a record is ignored when the blocked field says no',
     '            if c["blocked"] != "yes" or where.startswith("a person"):',
     '            if where.startswith("a person"):'),
    ("AV. A blocker outside the digest's scope is cited as if it were inside",
     '            elif not in_scope(other):',
     '            elif False:'),
]

def run_tests():
    done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=SKILL,
                          capture_output=True, text=True)
    failed = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\w+) \((?:test_digest\.)?(\w+)", done.stderr, re.M)))
    return done.stderr.strip().splitlines()[-1], ["%s.%s" % (group, name) for name, group in failed]


def main():
    with open(TARGET, encoding="utf-8") as f:
        good = f.read()
    out = ["Do the tests notice a broken digest generator? scrum-standup-digest, attempt scrum-attempt-001",
           "Recorded by scripts/planted_bugs.py.", "",
           "Each bug below was put into participant/skills/scrum-standup-digest/digest.py, every test was run, and the",
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
    out += ["After the last bug was taken out: digest.py is %s it was at the start. %s"
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
