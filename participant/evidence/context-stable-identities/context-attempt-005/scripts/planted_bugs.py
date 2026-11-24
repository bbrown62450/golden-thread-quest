#!/usr/bin/env python3
"""Records logs/planted-bugs.txt for the context-stable-identities quest.

Puts one bug at a time into participant/skills/context-stable-identities/identity.py,
runs every test, notes which tests fail, and takes the bug out again. At the
end it checks that the file is the same as when it started, byte for byte.

It changes identity.py while it runs. Do not run the skill at the same time.

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
SKILL = os.path.join(ROOT, "participant", "skills", "context-stable-identities")
TARGET = os.path.join(SKILL, "identity.py")

# (what the bug is, the text to replace, what to replace it with)
BUGS = [
    ("A. The Jira identity is built from the key, DEMO-3, which changes when a story moves project. This is the quest's scenario (criteria 2 and 4)",
     '"identifier": ("id", "Jira\'s issue id.', '"identifier": ("key", "Jira\'s issue id.'),
    ("B. The GitHub identity is built from the issue's number, which changes on a transfer (criteria 2 and 4)",
     '"identifier": ("node_id", "GitHub\'s global node ID.', '"identifier": ("number", "GitHub\'s global node ID.'),
    ("C. The Trello identity is built from the card's name (criteria 2 and 3)",
     '"identifier": ("id", "Trello\'s card id. Trello gives', '"identifier": ("name", "Trello\'s card id. Trello gives'),
    ("D. The identifier is put in lower case, so two GitHub items become one (criterion 1)",
     '    return "%s:%s" % (system, identifier)\n\n\ndef dig', '    return "%s:%s" % (system, identifier.lower())\n\n\ndef dig'),
    ("E. A space around an identifier is trimmed, where the rule is to refuse (criterion 7)",
     '    if identifier == "":\n        raise Refused("the identifier is empty")', '    identifier = identifier.strip()\n    if identifier == "":\n        raise Refused("the identifier is empty")'),
    ("F. A decimal is rounded to a whole number, where the rule is to refuse (criterion 7)",
     "    if isinstance(identifier, int):\n        if identifier < 0:", "    if isinstance(identifier, float):\n        identifier = int(identifier)\n    if isinstance(identifier, int):\n        if identifier < 0:"),
    ("G. A whole number is not written as its digits, so 40001 and \"40001\" are two items (criterion 7)",
     "        identifier = str(identifier)                       # the one conversion allowed: a whole number is written as its digits", "        identifier = \"n\" + str(identifier)"),
    ("H. An unknown system is given an identity anyway (criterion 1)",
     '    if system not in SYSTEMS:\n        raise Refused("the system is %s', '    if system is None:\n        raise Refused("the system is %s'),
    ("I. A collision is not noticed: the last record in the batch wins (criterion 5)",
     "        if len(group) > 1:\n            if all(entry[2] == source for entry in group):", "        if len(group) > 1 and False:\n            if all(entry[2] == source for entry in group):"),
    ("J. A collision is reported, and the first record is written all the same (criterion 5)",
     "                reported += 1\n                continue\n        mark = birth_mark(system, source)", "                reported += 1\n        mark = birth_mark(system, source)"),
    ("K. Two records that differ are taken for one record delivered twice (criterion 5)",
     "            if all(entry[2] == source for entry in group):", "            if all(seen(entry[1], entry[2])[\"title\"] == seen(system, source)[\"title\"] or True for entry in group):"),
    ("L. A reused identifier is not noticed: the newcomer overwrites the item held (criterion 6)",
     '        if item["birth_mark"] and mark and item["birth_mark"] != mark:', '        if False:'),
    ("M. A reused identifier is reported, and the newcomer overwrites the item held all the same (criterion 6)",
     "                \"The item held is left as it was, and the newcomer is held aside for a person to decide\" % (identity, item[\"birth_mark\"], name, mark))\n            reported += 1\n            continue",
     "                \"The item held is left as it was, and the newcomer is held aside for a person to decide\" % (identity, item[\"birth_mark\"], name, mark))\n            reported += 1"),
    ("N. Reuse is decided by comparing titles, not birth marks (criterion 2)",
     '        if item["birth_mark"] and mark and item["birth_mark"] != mark:', '        if item["now"]["title"] != now["title"]:'),
    ("O. A birth mark is compared as text, so one moment written in two time zones looks like two (criterion 6)",
     '        return moment.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if moment.tzinfo else None', '        return value if moment.tzinfo else None'),
    ("P. An alias is made whenever the title matches an item already held, without the source saying so (stretch goal, criterion 2)",
     "        if previous is not None:", "        if previous is None:\n            twin = [one for one, held in state[\"items\"].items() if held[\"system\"] == system and held[\"now\"][\"title\"] == now[\"title\"] and one != identity]\n            previous = twin[0].split(\":\", 1)[1] if twin and identity not in state[\"items\"] else None\n        if previous is not None:"),
    ("Q. A change of title is not recorded, so the map cannot say an item was renamed (criterion 3)",
     '        for what, word in (("title", "renamed"), ("container", "moved"), ("reference", "its reference changed")):', '        for what, word in (("container", "moved"), ("reference", "its reference changed")):'),
    ("R. The same batch can be applied twice",
     '    if name in state["batches"]:\n        raise Stop(', '    if False:\n        raise Stop('),
    ("S. An import merges into a map that already exists",
     '            if os.path.exists(os.path.join(args.folder, "state.json")):\n                raise Stop(', '            if False:\n                raise Stop('),
    ("T. A refused record is given an identity from its title, to be helpful (criterion 2)",
     "            reported += 1\n            continue\n        derived.append(", "            reported += 1\n            if system in SYSTEMS and isinstance(source, dict):\n                derived.append((\"%s:%s\" % (system, shown), system, source, None))\n            continue\n        derived.append("),
]


def run_tests():
    done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=SKILL,
                          capture_output=True, text=True)
    failed = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\w+) \((?:test_identity\.)?(\w+)", done.stderr, re.M)))
    return done.stderr.strip().splitlines()[-1], ["%s.%s" % (group, name) for name, group in failed]


def main():
    with open(TARGET, encoding="utf-8") as f:
        good = f.read()
    out = ["Do the tests notice a broken identity rule? context-stable-identities, attempt context-attempt-005",
           "Recorded by scripts/planted_bugs.py.", "",
           "Each bug below was put into participant/skills/context-stable-identities/identity.py, every test was run, and the",
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
    out += ["After the last bug was taken out: identity.py is %s it was at the start. %s"
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
