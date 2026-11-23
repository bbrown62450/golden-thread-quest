#!/usr/bin/env python3
"""Records logs/planted-bugs.txt for the github-read-issue quest.

Puts one bug at a time into participant/skills/github-read-issue/read_issue.py,
runs every test, notes which tests fail, and takes the bug out again. At the
end it checks that the file is the same as when it started, byte for byte.

It changes read_issue.py while it runs. Do not run the skill at the same time.

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
SKILL = os.path.join(ROOT, "participant", "skills", "github-read-issue")
TARGET = os.path.join(SKILL, "read_issue.py")

# (what the bug is, the text to replace, what to replace it with)
BUGS = [
    ("A. A field the format does not know is dropped (criteria 1 and 4)",
     '    preserved = {key: value for key, value in slim.items() if key not in KNOWN_KEYS}', '    preserved = {}'),
    ("B. An unknown field on a comment is dropped (criteria 1 and 4)",
     'for key, value in row.items() if key != "body"},', 'for key, value in row.items() if key != "body" and key in KNOWN_COMMENT_KEYS},'),
    ("C. Labels are kept by name only, and their colour and description are lost (criterion 1)",
     'if key in KNOWN_KEYS and key not in in_front}', 'if key in KNOWN_KEYS and key not in in_front and key != "labels"}'),
    ("D. The read-back check before writing is skipped, so a lost field would go unnoticed (criterion 1)",
     '    if missing:\n        raise Stop("reading the file back', '    if False:\n        raise Stop("reading the file back'),
    ("E. The read-back check takes false and 0 for the same value (criterion 1)",
     '    return [] if type(raw) is type(kept) and raw == kept else [path]', '    return [] if raw == kept else [path]'),
    ("F. The quest's scenario: the body is flattened, so its task list, table and code block run together (criterion 2)",
     '    body = slim.get("body")', '    body = slim.get("body") and " ".join(slim["body"].split())'),
    ("G. Spaces at the end of each line of the body are tidied away (criterion 2)",
     '    body = slim.get("body")', '    body = slim.get("body") and "\\n".join(line.rstrip() for line in slim["body"].split("\\n"))'),
    ("H. Blank lines at the start and end of a text are trimmed (criterion 2)",
     '    return "%s\\n%s\\n%s\\n" % (begin, text, end)', '    return "%s\\n%s\\n%s\\n" % (begin, text.strip(), end)'),
    ("I. Windows line endings are turned into plain ones when the file is written (criterion 2)",
     '        f.write(data)', '        f.write(data.replace(b"\\r\\n", b"\\n"))'),
    ("J. No body is stored as an empty body (criteria 1 and 2)",
     '    body = slim.get("body")', '    body = slim.get("body") or ""'),
    ("K. A pull request is saved as if it were an issue (criterion 3)",
     '    if "pull_request" in issue:', '    if False:'),
    ("L. An issue that was transferred is not recognised as moved (criterion 3)",
     '    if client.redirects or repo_in_url(issue.get("repository_url")) != repo:', '    if False:'),
    ("M. An answer with no usable node identifier is accepted (criterion 3)",
     '    if not isinstance(issue.get("node_id"), str) or not NODE_ID.match(issue["node_id"]):', '    if False:'),
    ("N. A file holding another issue, with another node identifier, is overwritten (criterion 3)",
     ', ("node_id", "of another issue: the node ID differs")):', '):'),
    ("O. A file from another source is overwritten (criterion 3)",
     '(("source", "from another source"), ', '('),
    ("P. A file the skill did not write is overwritten",
     '    old = read_bytes(path)\n    if old is not None:', '    old = read_bytes(path)\n    if False:'),
    ("Q. A deleted issue is not told apart from other failures (criterion 3)",
     '    if status == 410:', '    if status == 4100:'),
    ("R. A second retrieval always writes the file again (criterion 5)",
     '    if old == data:', '    if False:'),
    ("S. The time of retrieval is put in the file, so no two runs give the same bytes (criterion 5)",
     '    lines = ["---"] + ', '    lines = ["---", "retrieved_at: %d" % time.time_ns()] + '),
    ("T. Fields are written in the order GitHub happens to send them (criterion 5)",
     'indent=2, sort_keys=True', 'indent=2, sort_keys=False'),
    ("U. The report of what changed names every part, whatever changed (criterion 5)",
     '    return [words for words, key in names if old[key] != new[key]]', '    return [words for words, key in names]'),
    ("V. The title is written into the front matter as it is, so a title can add lines to it (criterion 6)",
     '(key, one_json(front[key])) for key in FRONT_ORDER]', '(key, front[key] if key == "title" else one_json(front[key])) for key in FRONT_ORDER]'),
    ("W. The markers do not depend on the text, so a line in the body can pass for the end marker (criterion 6)",
     '    tag = sha(text)[:16]', '    tag = "0" * 16'),
    ("X. A text that holds its own end marker is stored anyway, and would be cut short (criterion 6)",
     '    if end in text:', '    if False:'),
    ("Y. A comment's text is looked for from the top of the file, so an earlier comment can pass for a later one (criterion 6)",
     'found, position = _unblock(text, "comment-%d" % index, entry["body_sha256"], position)',
     'found, _ = _unblock(text, "comment-%d" % index, entry["body_sha256"], 0)'),
    ("Z. A file changed by hand after it was written passes the check (criterion 6)",
     '    if sha(found) != digest:', '    if False:'),
    ("AA. A person's whole record is kept in the file (criterion 7)",
     'isinstance(value.get("login"), str) and any(k in value for k in ("id", "node_id", "avatar_url"))', 'False'),
    ("AB. A person's record is not reduced, though the check knows it should be (criterion 7)",
     '    if is_person(value):\n        left.setdefault', '    if False:\n        left.setdefault'),
    ("AC. API addresses are kept in the file",
     '    return (key == "url" or key.endswith("_url")) and isinstance(value, str) and value.startswith(API_PREFIX)', '    return False'),
    ("AD. The token's own value in an issue's text does not stop the run (criterion 7)",
     '    if token and token in text:', '    if False:'),
    ("AE. Text shaped like a credential or an email address is not counted (criterion 7)",
     '    return len(TOKEN_SHAPED.findall(text)), len(EMAIL_SHAPED.findall(text))', '    return 0, 0'),
    ("AF. A file with such text is reported as saved, with no warning in the result (criterion 7)",
     '    if tokens or emails:', '    if False:'),
    ("AG. The run prints the issue's title (criterion 7)",
     '% (number, issue["node_id"], plural(len(comments), "comment")', '% (number, issue["title"], plural(len(comments), "comment")'),
    ("AH. A field name is printed whatever it holds (criterion 6)",
     '    plain = [name for name in names if FIELD_NAME.match(name)]', '    plain = list(names)'),
    ("AI. Only the first page of comments is read (criterion 1)",
     '        if not has_next(head):\n            return rows, page', '        if True:\n            return rows, page'),
    ("AJ. A page that repeats itself is taken for the end of the comments (criterion 1)",
     '        if not fresh:\n            raise Stop(', '        if not fresh:\n            return rows, page\n            raise Stop('),
    ("AK. Comments that could not be read are saved as no comments (criterion 1)",
     '            raise Stop("GitHub did not return %s (status %d). A part may be missing, so nothing is saved" % (what, status))', '            return rows, page'),
    ("AL. A count of comments that differs from what was read is not mentioned",
     '    if isinstance(issue.get("comments"), int) and issue["comments"] != len(comments):', '    if False:'),
    ("AM. A rejected token is not recognised",
     '            if status == 401:', '            if status == 4010:'),
    ("AN. A rate limit is not recognised",
     '            limited = status == 429 or (', '            limited = status == 4290 or ('),
    ("AO. A redirect to another host is followed, taking the token's request with it (criterion 7)",
     '            if where.scheme != "https" or where.netloc != API_HOST or hops == MAX_REDIRECTS:', '            if hops == MAX_REDIRECTS:'),
    ("AP. A file name that is not a plain .md name is accepted",
     '    if not FILE_NAME.match(name):', '    if False:'),
]


def run_tests():
    done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=SKILL,
                          capture_output=True, text=True)
    failed = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\w+) \((?:test_read_issue\.)?(\w+)", done.stderr, re.M)))
    return done.stderr.strip().splitlines()[-1], ["%s.%s" % (group, name) for name, group in failed]


def main():
    with open(TARGET, encoding="utf-8") as f:
        good = f.read()
    out = ["Do the tests notice a broken skill? github-read-issue, attempt github-attempt-004",
           "Recorded by scripts/planted_bugs.py.", "",
           "Each bug below was put into participant/skills/github-read-issue/read_issue.py, every test was run, and the",
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
    out += ["After the last bug was taken out: read_issue.py is %s it was at the start. %s"
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
