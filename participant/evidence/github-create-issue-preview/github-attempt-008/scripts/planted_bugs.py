#!/usr/bin/env python3
"""Records logs/planted-bugs.txt for the github-create-issue-preview quest.

Puts one bug at a time into participant/skills/github-create-issue-preview/preview.py,
runs every test, notes which tests fail, and takes the bug out again. At the
end it checks that the file is the same as when it started, byte for byte.

It changes preview.py while it runs. Do not run the skill at the same time.

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
SKILL = os.path.join(ROOT, "participant", "skills", "github-create-issue-preview")
TARGET = os.path.join(SKILL, "preview.py")

# (what the bug is, the text to replace, what to replace it with)
BUGS = [
    ("A. A required section that is empty is accepted (criteria 1 and 3)",
     '        elif not bare(written[name]) or bare(written[name]) == bare(placeholder):', '        elif False:'),
    ("B. A section holding only the template's placeholder counts as filled in (criterion 3)",
     '        elif not bare(written[name]) or bare(written[name]) == bare(placeholder):', '        elif not bare(written[name]):'),
    ("C. A required section that is missing is accepted (criteria 1 and 3)",
     'problems.append("the required template section %s is missing from the draft" % q(name))', 'pass'),
    ("D. Every section of the template is treated as optional (criterion 1)",
     '[(name, not OPTIONAL.search(name), text) for name, text in sections]', '[(name, False, text) for name, text in sections]'),
    ("E. A section marked optional is treated as required (criterion 1)",
     '[(name, not OPTIONAL.search(name), text) for name, text in sections]', '[(name, True, text) for name, text in sections]'),
    ("F. Sections in another order than the template's are accepted (criterion 1)",
     '    if [name for name in have if name in wanted] != [name for name in wanted if name in have]:', '    if False:'),
    ("G. A section the template does not have is accepted (criterion 1)",
     '        if name not in wanted:', '        if False:'),
    ("H. A heading inside a code block is taken for a section (criterion 1)",
     '        elif fence is None:\n            yield number, line', '        else:\n            yield number, line'),
    ("I. A label the repository does not have is put in the payload (criteria 2 and 3)",
     '        row = have.get(name.casefold())', '        row = have.get(name.casefold()) or {"name": name, "id": None}'),
    ("J. A label is sent as the draft writes it, not as the repository does (criterion 2)",
     '            labels.append(row["name"])', '            labels.append(name)'),
    ("K. The label the template gives is not required of the draft (criterion 1)",
     '        if name.casefold() not in [one.casefold() for one in draft["labels"]]:', '        if False:'),
    ("L. A login that cannot be assigned is accepted (criterion 2)",
     '        if status == 204:', '        if status in (204, 404):'),
    ("M. A closed milestone is accepted (criterion 2)",
     '        elif found[0].get("state") != "open":', '        elif False:'),
    ("N. The milestone is sent as its title, which GitHub does not take (criterion 5)",
     '        payload["milestone"] = found["milestone"]["number"]', '        payload["milestone"] = found["milestone"]["title"]'),
    ("O. A citation is not checked against the words on the lines it names (criterion 7)",
     '        if there is None or not words.strip() or " ".join(words.split()) not in there:', '        if False:'),
    ("P. A citation may point outside the draft's folder (criterion 7)",
     '        if os.path.isabs(where) or os.path.commonpath([base, path]) != base:', '        if False:'),
    ("Q. A field with no citation is accepted (criterion 7)",
     '        if field not in cited:', '        if False:'),
    ("R. A likely duplicate does not stop the preview (criterion 4)",
     '    stopping = [name for name in close if name not in despite]', '    stopping = []'),
    ("S. An override naming any issue at all is accepted (criterion 4)",
     '        if name not in close:', '        if False:'),
    ("T. A person's override is not recorded in the preview (criterion 4)",
     '    overridden = [name for name in close if name in despite]', '    overridden = []'),
    ("U. Labels set by an account that may not triage are not flagged, though GitHub would drop them (criterion 4)",
     '        if extras and not any(may.get(key) for key in ("triage", "push", "maintain", "admin")):', '        if False:'),
    ("V. An archived repository is still READY (criterion 4)",
     '    if about.get("archived"):', '    if False:'),
    ("W. The payload holds only the start of the body: a summary, not the payload (criterion 5)",
     '    payload = {"title": draft["title"], "body": draft["body"]}', '    payload = {"title": draft["title"], "body": draft["body"][:200]}'),
    ("X. The body is tidied on its way into the payload (criterion 5)",
     '    payload = {"title": draft["title"], "body": draft["body"]}', '    payload = {"title": draft["title"], "body": " ".join(draft["body"].split())}'),
    ("Y. The payload's bytes depend on the order its fields are held in, so a saved payload gives other bytes (criterion 5)",
     '    ordered = [(key, payload[key]) for key in PAYLOAD_FIELDS if key in payload]', '    ordered = list(payload.items())'),
    ("Z. A field this workflow does not know is sent (criterion 5)",
     '    if set(payload) - set(PAYLOAD_FIELDS):', '    if False:'),
    ("AA. A payload is shown for a draft that was refused (criterion 3)",
     '    if problems:\n        say("7. THE EXACT PAYLOAD. Not shown', '    if False:\n        say("7. THE EXACT PAYLOAD. Not shown'),
    ("AB. A repository that changes during the preview is still READY (criterion 6)",
     '    if not same:', '    if False:'),
    ("AC. The sandbox allowlist is not checked (criterion 6)",
     '    count = check_allowlist(args.allowlist, repo)', '    count = 1'),
]


def run_tests():
    done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=SKILL,
                          capture_output=True, text=True)
    failed = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\w+) \((?:test_preview\.)?(\w+)", done.stderr, re.M)))
    return done.stderr.strip().splitlines()[-1], ["%s.%s" % (group, name) for name, group in failed]


def main():
    with open(TARGET, encoding="utf-8") as f:
        good = f.read()
    out = ["Do the tests notice a broken preview? github-create-issue-preview, attempt github-attempt-008",
           "Recorded by scripts/planted_bugs.py.", "",
           "Each bug below was put into participant/skills/github-create-issue-preview/preview.py, every test was run, and the",
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
    out += ["After the last bug was taken out: preview.py is %s it was at the start. %s"
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
