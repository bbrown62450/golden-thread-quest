#!/usr/bin/env python3
"""Records logs/planted-bugs.txt for the github-update-metadata quest.

Puts one bug at a time into participant/skills/github-update-metadata/update.py,
runs every test, notes which tests fail, and takes the bug out again. At the
end it checks that the file is the same as when it started, byte for byte.

It changes update.py while it runs. Do not run the skill at the same time.

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
SKILL = os.path.join(ROOT, "participant", "skills", "github-update-metadata")
TARGET = os.path.join(SKILL, "update.py")

# (what the bug is, the text to replace, what to replace it with)
BUGS = [
    ("A. The preview shows the new values in place of the old ones (criterion 1)",
     '    show_values("old:", old)', '    show_values("old:", new)'),
    ("B. A value from GitHub is printed as it is, so it can break a line of the preview (criterion 1)",
     '    return json.dumps(value, ensure_ascii=False)', '    return str(value)'),
    ("C. A field that is not supported is let through (criterion 2)",
     '        if field not in SUPPORTED:', '        if False:'),
    ("D. A label the repository does not have is added, and GitHub creates it (criterion 2)",
     '            known = among(repo_labels, value)', '            known = among(repo_labels, value) or value'),
    ("E. A login that cannot be assigned is accepted (criterion 2)",
     '            elif not assignable(value):', '            elif False:'),
    ("F. A closed milestone is accepted (criterion 2)",
     '            elif found[0].get("state") != "open":', '            elif False:'),
    ("G. A request for a thing and its opposite is accepted (criterion 2)",
     '        if any(other == opposite and', '        if False and any(other == opposite and'),
    ("H. A pull request is accepted (criterion 2)",
     '    if "pull_request" in answer:', '    if False:'),
    ("I. The same change asked for twice is accepted (criterion 2)",
     '        elif [field, value] in asked:', '        elif False:'),
    ("J. More than ten changes are accepted (criterion 2)",
     '    if len(asked) > MAX_CHANGES:', '    if False:'),
    ("K. A label is matched only when its capitals match (criterion 2)",
     'if have.casefold() == name.casefold()), None)', 'if have == name), None)'),
    ("L. The check for a field that moved is skipped (criterion 3)",
     '    if moved:', '    if False:'),
    ("M. Only the labels are checked for having moved (criterion 3)",
     '    moved = differences(record["old"], now_values)', '    moved = [pair for pair in differences(record["old"], now_values) if pair[0] == "labels"]'),
    ("N. The issue is compared with itself, not with the old values of the preview (criterion 3)",
     '    moved = differences(record["old"], now_values)', '    moved = differences(now_values, now_values)'),
    ("O. The quest's scenario: a label is added by sending the whole list of labels (criterion 3)",
     'out.append({"method": "POST", "path": base + "/labels", "body": {"labels": [one["value"]]}})',
     'out.append({"method": "PATCH", "path": base, "body": {"labels": new["labels"]}})'),
    ("P. The milestone request carries the whole list of labels as well (criterion 3)",
     '"body": {"milestone": new["milestone"]["number"] if new["milestone"] else None}})',
     '"body": {"milestone": new["milestone"]["number"] if new["milestone"] else None, "labels": new["labels"]}})'),
    ("Q. The read-back is not compared with what the preview promised (criterion 3)",
     '    as_promised = after == record["new"]', '    as_promised = True'),
    ("R. A connection can write without one issue being allowed (criterion 4)",
     '        if self._writable is None:', '        if False:'),
    ("S. A write outside the one issue of the preview is sent (criteria 4 and 6)",
     '        if method not in ("POST", "PATCH", "DELETE") or not (path == self._writable or path.startswith(self._writable + "/")):', '        if False:'),
    ("T. An issue that changes while it is previewed is still READY (criterion 4)",
     '    if bad or not allowed or repo.get("archived") or again != old:', '    if bad or not allowed or repo.get("archived"):'),
    ("U. A preview with nothing to change still gives a fingerprint (criteria 4 and 9)",
     '    if not requests:', '    if False:'),
    ("V. An account that may only read is still READY (criterion 5)",
     '    allowed = bool(may and (may.get("push") or may.get("triage") or may.get("maintain") or may.get("admin")))', '    allowed = True'),
    ("W. An archived repository is still READY (criterion 5)",
     '    if bad or not allowed or repo.get("archived") or again != old:', '    if bad or not allowed or again != old:'),
    ("X. A change that is already so is sent anyway (criteria 5 and 9)",
     '            elif action == "add" and among(old["labels"], known):', '            elif False:'),
    ("Y. The preview does not check the allowlist (criterion 6)",
     '    asked, refused = parse_changes(args.change)\n    count = check_allowlist(args.allowlist, args.repo)', '    asked, refused = parse_changes(args.change)\n    count = 1'),
    ("Z. The confirmation does not check the allowlist (criterion 6)",
     '    count = check_allowlist(args.allowlist, args.repo)\n    path, saved, record, status', '    count = 1\n    path, saved, record, status'),
    ("AA. An allowlist that cannot be read allows every repository (criterion 6)",
     '        raise Refused("the sandbox allowlist could not be read, so no repository is allowed")', '        return 0'),
    ("AB. An allowlist that is not a list is searched as text (criterion 6)",
     '    if not isinstance(names, list) or repo not in names:', '    if not isinstance(names, (list, str)) or repo not in names:'),
    ("AC. A repository GitHub knows under another name is accepted (criterion 6)",
     '    if answer.get("full_name") != repo:', '    if False:'),
    ("AD. A redirect is not recognised as a repository that moved (criterion 6)",
     '        if status in (301, 302, 307, 308):', '        if False:'),
    ("AE. A confirmation with no name is accepted (criterion 7)",
     '    if not args.fingerprint or not args.confirmed_by:', '    if not args.fingerprint:'),
    ("AF. An email address is accepted as the confirmer's name (criterion 7)",
     ' or EMAIL_SHAPED.search(name):', ':'),
    ("AG. A change that differs from the preview is accepted (criterion 7)",
     '    if refused or asked != record["asked"]:', '    if refused:'),
    ("AH. A preview for another issue is accepted (criterion 7)",
     '    if (record["repository"], record["issue"], record["source"]) != (args.repo, args.issue, args.source):', '    if False:'),
    ("AI. A saved preview that was altered is accepted (criterion 7)",
     '    if fingerprint_of(record) != mark or record.get("format") != PREVIEW_FORMAT:', '    if record.get("format") != PREVIEW_FORMAT:'),
    ("AJ. A fingerprint of any shape is used as a file name (criterion 7)",
     '    if not FINGERPRINT.match(mark or ""):', '    if False:'),
    ("AK. The time limit is not checked (criterion 7)",
     '    if age > record["limit_minutes"] or age < -1:', '    if False:'),
    ("AL. A preview exactly at the limit is refused (criterion 7)",
     '    if age > record["limit_minutes"] or age < -1:', '    if age >= record["limit_minutes"] or age < -1:'),
    ("AM. Another account, or an issue that was recreated, is accepted (criterion 7)",
     '    if account != record["account"] or repo["id"] != record["repository_id"] or facts["node_id"] != record["node_id"]:', '    if False:'),
    ("AN. The result record does not name who confirmed (criterion 8)",
     '"- confirmed by: %s, as typed with the fingerprint in the command that wrote. The workflow cannot check who typed it" % q(name),', '"- confirmed by: someone",'),
    ("AO. Events that were there before the update are claimed as its identifiers (criterion 8)",
     '              if row.get("id") not in events_before and row.get("event") in EVENTS_OF_INTEREST]', '              if row.get("event") in EVENTS_OF_INTEREST]'),
    ("AP. The changes given for putting the old values back do not reverse anything (criterion 8)",
     '(kind, "remove" if action == "add" else "add", one["value"]))', '(kind, action, one["value"]))'),
    ("AQ. A preview that was used can be confirmed again (criterion 9)",
     '    if status != "ready":', '    if False:'),
    ("AR. The preview is not marked as used (criterion 9)",
     '    save_json(path, saved)                      # the preview', '    pass                      # the preview'),
    ("AS. After GitHub refuses a write, the rest are sent anyway",
     '            failed = status_code\n            break', '            failed = status_code'),
    ("AT. A write GitHub refused is not reported as refused",
     '        ok = status_code in (200, 201)', '        ok = True'),
]


def run_tests():
    done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=SKILL,
                          capture_output=True, text=True)
    failed = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\w+) \((?:test_update\.)?(\w+)", done.stderr, re.M)))
    return done.stderr.strip().splitlines()[-1], ["%s.%s" % (group, name) for name, group in failed]


def main():
    with open(TARGET, encoding="utf-8") as f:
        good = f.read()
    out = ["Do the tests notice a broken skill? github-update-metadata, attempt github-attempt-005",
           "Recorded by scripts/planted_bugs.py.", "",
           "Each bug below was put into participant/skills/github-update-metadata/update.py, every test was run, and the",
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
    out += ["After the last bug was taken out: update.py is %s it was at the start. %s"
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
