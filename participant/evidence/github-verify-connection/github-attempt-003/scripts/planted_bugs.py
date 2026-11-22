#!/usr/bin/env python3
"""Records logs/planted-bugs.txt for the github-verify-connection quest.

Puts one bug at a time into participant/skills/github-verify-connection/verify.py,
runs every test, notes which tests fail, and takes the bug out again. At the
end it checks that the file is the same as when it started, byte for byte.

It changes verify.py while it runs. Do not run the check at the same time.

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
SKILL = os.path.join(ROOT, "participant", "skills", "github-verify-connection")
TARGET = os.path.join(SKILL, "verify.py")

# (what the bug is, the text to replace, what to replace it with)
BUGS = [
    ("A. The login is written into the check instead of read from the connection (criterion 1)",
     '% (body["login"], body["id"]))', '% ("robin-fixture", 9001))'),
    ("B. A rejected token is not recognised (criterion 1)",
     '        if status == 401:', '        if status == 4010:'),
    ("C. The scopes GitHub reports are not reported (criterion 2)",
     '    if "x-oauth-scopes" in head:', '    if False:'),
    ("D. Every scope is called read-only (criteria 2 and 7)",
     '    return scope.startswith("read:") or scope in', '    return True or scope in'),
    ("E. The scope `repo`, which allows writing, is called read-only (criterion 7)",
     'scope in ("repo:status", "public_repo:status")', 'scope in ("repo", "repo:status", "public_repo:status")'),
    ("F. The token's expiry date is not reported (criterion 2)",
     '    if expires:', '    if False:'),
    ("G. What the account may do is passed off as what the token may do (criterion 2)",
     '    if any(may.get("push") or may.get("admin") for _, _, may in names):', '    if False:'),
    ("H. A list of repositories that could not be read is reported as an empty list (criteria 3 and 4)",
     '        if status != 200 or not isinstance(body, list):', '        if False:'),
    ("I. The list of repositories stops after the first page (criterion 3)",
     "        if 'rel=\"next\"' not in head.get(\"link\", \"\") or page == MAX_LIST_PAGES:", '        if True:'),
    ("J. A refused read is reported as a read that found nothing: the scenario (criterion 4)",
     '            results.append((word, needed, "refused", status))', '            results.append((word, needed, "ok", "0"))'),
    ("K. A refused read of issues does not count against the repository (criterion 4)",
     '("issues", "/issues", True)', '("issues", "/issues", False)'),
    ("L. An expected repository that cannot be read does not fail the check (criterion 4)",
     '    return 3 if failed else 0', '    return 0'),
    ("M. A repository GitHub says is empty is not told from one whose files are refused (criterion 4)",
     '        elif word == "files" and status == 404 and "empty" in', '        elif False and "empty" in'),
    ("N. A renamed repository is reported as readable (criterion 4)",
     '            results.append((word, needed, "moved", status))', '            results.append((word, needed, "ok", "moved"))'),
    ("O. A server error is described as a repository that may not exist (criterion 4)",
     'if detail == 404 else ""', 'if True else ""'),
    ("P. Pull requests are counted as issues (criterion 4)",
     ' and not (word == "issues" and "pull_request" in row)', ''),
    ("Q. A count cut off at the first page is given as the whole count (criterion 4)",
     "            more = 'rel=\"next\"' in head.get(\"link\", \"\")\n            results.append", '            more = False\n            results.append'),
    ("R. The check may be run with no expected repository (criterion 4)",
     '        if not args.expect:', '        if False:'),
    ("S. The request is not a GET (criterion 5)",
     'method="GET"', 'method="POST"'),
    ("T. A request is made and left out of the list of requests (criterion 5)",
     '        self.made.append("GET %s" % path)', '        if path != "/user":\n            self.made.append("GET %s" % path)'),
    ("U. The token is put in the address (criterion 6)",
     '    url = "https://%s%s" % (API_HOST, path)',
     '    url = "https://%s%s?access_token=%s" % (API_HOST, path, os.environ.get("GITHUB_TOKEN"))'),
    ("V. Lines are printed as they are made, before the scan (criterion 6)",
     '        self.lines.append("github-verify: " + text if text else "")',
     '        self.lines.append("github-verify: " + text if text else "")\n        print(self.lines[-1])'),
    ("W. The output is not scanned for the token's own value (criterion 6)",
     '            clean = line.replace(token, "[REDACTED]") if token else line', '            clean = line'),
    ("X. The output is not scanned for anything shaped like a token (criterion 6)",
     '            clean = TOKEN_SHAPED.sub("[REDACTED]", clean)', '            clean = clean'),
    ("Y. A credential found in the output does not fail the check (criterion 6)",
     '    return code if report.finish(token) else 3', '    report.finish(token)\n    return code'),
    ("Z. A rate limit is not recognised, and is reported as lost access",
     '        if status == 429 or (', '        if status == 4290 or ('),
]


def run_tests():
    done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=SKILL,
                          capture_output=True, text=True)
    failed = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\w+) \((?:test_verify\.)?(\w+)", done.stderr, re.M)))
    return done.stderr.strip().splitlines()[-1], ["%s.%s" % (group, name) for name, group in failed]


def main():
    with open(TARGET, encoding="utf-8") as f:
        good = f.read()
    out = ["Do the tests notice a broken check? github-verify-connection, attempt github-attempt-003",
           "Recorded by scripts/planted_bugs.py.", "",
           "Each bug below was put into participant/skills/github-verify-connection/verify.py, every test was run, and the",
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
    out += ["After the last bug was taken out: verify.py is %s it was at the start. %s"
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
