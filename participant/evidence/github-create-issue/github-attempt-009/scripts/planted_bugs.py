#!/usr/bin/env python3
"""Records logs/planted-bugs.txt for the github-create-issue quest.

Puts one bug at a time into participant/skills/github-create-issue/create.py,
runs every test, notes which tests fail, and takes the bug out again. At the
end it checks that the file is the same as when it started, byte for byte.

It changes create.py while it runs. Do not run the skill at the same time.

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
SKILL = os.path.join(ROOT, "participant", "skills", "github-create-issue")
TARGET = os.path.join(SKILL, "create.py")

# (what the bug is, the text to replace, what to replace it with)
BUGS = [
    ("A. The write builds its own bytes from the payload instead of sending the preview's (criterion 1)",
     '    data = pv.payload_bytes(record["payload"])', '    data = json.dumps(record["payload"]).encode("utf-8")'),
    ("B. The saved payload's bytes are not checked against the checksum the preview recorded (criterion 1)",
     '    if hashlib.sha256(data).hexdigest() != record["payload_sha256"]:', '    if False:'),
    ("C. The issue is read back and the comparison is not used (criterion 1)",
     'compared="same" if all(row[3] for row in rows) else "different")', 'compared="same")'),
    ("D. Only the title and the body are compared (criterion 1)",
     'COMPARED = ("title", "body", "labels", "assignees", "milestone")', 'COMPARED = ("title", "body")'),
    ("E. The comparison forgives white space and kinds of value (criterion 1)",
     'type(sent[field]) is type(back[field]) and sent[field] == back[field])', 'str(sent[field]).strip() == str(back[field]).strip())'),
    ("F. The number GitHub returned is not written down until after the issue is read back (criterion 2)",
     '    try:\n        write_link(path, link)\n    except OSError as problem:', '    try:\n        pass\n    except OSError as problem:'),
    ("G. Nothing is written locally before the create is sent, so a crash leaves no trace: the quest's scenario (criteria 2 and 9)",
     '    write_link(link_path(args), link)                     # the intent', '    pass                     # the intent'),
    ("H. The local link is matched to the issue by number only (criterion 3)",
     '    if issue["node_id"] != link["node_id"]:', '    if False:'),
    ("I. A local link file that cannot be read is taken to mean the draft has no issue (criteria 3 and 9)",
     '        raise Stop("the local link file %s is not one this workflow wrote, so it is not known whether this draft was already created" % shown_path(path))', '        return None'),
    ("J. The preview does not look at the local link (criteria 4 and 9)",
     'def cmd_preview(args):\n    refuse_if_linked(link_path(args))', 'def cmd_preview(args):'),
    ("K. A second create can be sent on one connection (criterion 4)",
     '        if self._repo is None or self.sent or not isinstance(data, bytes):', '        if self._repo is None or not isinstance(data, bytes):'),
    ("L. A create can be sent without a repository being allowed (criteria 4 and 6)",
     '        if self._repo is None or self.sent or not isinstance(data, bytes):', '        if self.sent or not isinstance(data, bytes):'),
    ("M. The confirmation does not check the allowlist (criterion 6)",
     '    try:\n        count = pv.check_allowlist(args.allowlist, repo)\n    except Stop as why:\n        raise Refused(str(why))\n    refuse_if_linked(link_path(args))',
     '    count = 1\n    refuse_if_linked(link_path(args))'),
    ("N. A confirmation with no name is accepted (criterion 7)",
     '    if not args.fingerprint or not args.confirmed_by:', '    if not args.fingerprint:'),
    ("O. An email address is accepted as the confirmer's name (criterion 7)",
     ' or EMAIL_SHAPED.search(name):', ':'),
    ("P. A draft changed after the preview is created all the same (criterion 7)",
     '    if record["draft_digest"] != draft["digest"]:', '    if False:'),
    ("Q. A saved preview that was altered is accepted (criterion 7)",
     '    if hashlib.sha256(json.dumps(body, sort_keys=True).encode("utf-8")).hexdigest()[:32] != mark or record.get("fingerprint") != mark:', '    if False:'),
    ("R. The time limit is not checked (criterion 7)",
     '    if age > record["limit_minutes"] or age < -1:', '    if False:'),
    ("S. A preview exactly at the limit is refused (criterion 7)",
     '    if age > record["limit_minutes"] or age < -1:', '    if age >= record["limit_minutes"] or age < -1:'),
    ("T. A preview that was used can be confirmed again (criteria 7 and 9)",
     '    if saved.get("status") != "ready":', '    if False:'),
    ("U. Another account than the one of the preview is accepted (criterion 7)",
     '    if account.get("login") != record["account"] or about.get("id") != record["repository_id"] or about.get("full_name") != repo:', '    if False:'),
    ("V. A label deleted after the preview is not noticed, and GitHub would create it again (criterion 7)",
     '    gone = [one for one in record["payload"].get("labels", []) if one not in labels]', '    gone = []'),
    ("W. The same title filed by someone else after the preview is not noticed (criterion 9)",
     '    if twins:', '    if False:'),
    ("X. The result record does not name who confirmed (criterion 8)",
     '"- confirmed by: %s, as typed with the fingerprint in the command that wrote. The workflow cannot check who typed it" % q(link["confirmed_by"]),', '"- confirmed by: someone",'),
    ("Y. A draft that is already an issue can be created again (criterion 9)",
     '    if link is None or link["status"] == "not-created":\n        return link', '    if True:\n        return link'),
    ("Z. A lost answer is recorded as \"not created\", so the next run creates a second issue (criterion 9)",
     '        write_link(link_path(args), dict(link, status="unknown"))\n        say("     NO ANSWER CAME BACK', '        write_link(link_path(args), dict(link, status="not-created"))\n        say("     NO ANSWER CAME BACK'),
    ("AA. A lost answer is answered by sending the create again (criterion 9)",
     '            raise OutcomeUnknown(type(problem).__name__)', '            status, headers, answer = self._send("POST", path, None, data)'),
    ("AB. A refusal by GitHub is recorded as an unknown outcome",
     '        if 400 <= status < 500:', '        if False:'),
    ("AC. Reconcile believes at once that no issue was created (criterion 9)",
     '        if waited < SETTLE_SECONDS:', '        if False:'),
    ("AD. Reconcile takes any issue with the same title for the one that was sent (criterion 9)",
     ' and row.get("body") == link["payload"]["body"]', ''),
    ("AE. Reconcile links the first of several matching issues without asking (criterion 9)",
     '    if len(found) > 1:', '    if False:'),
]


def run_tests():
    done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=SKILL,
                          capture_output=True, text=True)
    failed = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\w+) \((?:test_create\.)?(\w+)", done.stderr, re.M)))
    return done.stderr.strip().splitlines()[-1], ["%s.%s" % (group, name) for name, group in failed]


def main():
    with open(TARGET, encoding="utf-8") as f:
        good = f.read()
    out = ["Do the tests notice a broken workflow? github-create-issue, attempt github-attempt-009",
           "Recorded by scripts/planted_bugs.py.", "",
           "Each bug below was put into participant/skills/github-create-issue/create.py, every test was run, and the",
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
    out += ["After the last bug was taken out: create.py is %s it was at the start. %s"
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
