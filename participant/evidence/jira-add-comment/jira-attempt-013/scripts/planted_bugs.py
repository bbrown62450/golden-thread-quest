#!/usr/bin/env python3
"""Records logs/planted-bugs.txt for the jira-add-comment quest.

Puts one bug at a time into participant/skills/jira-add-comment/comment.py,
runs every test, notes which tests fail, and takes the bug out again. At the
end it checks that the file is the same as when it started, byte for byte.

It changes comment.py while it runs. Do not run the skill at the same time.

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
SKILL = os.path.join(ROOT, "participant", "skills", "jira-add-comment")
TARGET = os.path.join(SKILL, "comment.py")

# (what the bug is, the text to replace, what to replace it with)
BUGS = [
    ('A. A preview can write (criterion 3)',
     '        if self._post is None:\n            raise Refused("this command has no way to write")\n',
     ''),
    ('B. The live preview is handed the write function (criterion 3)',
     'return Connection(get, post if may_write else None, host), [token, email, encoded]',
     'return Connection(get, post, host), [token, email, encoded]'),
    ('C. The allowlist is not checked (criterion 5)',
     '    if (site, project["id"]) not in allowed:',
     '    if False:'),
    ('D. The allowlist is checked by project id alone, on any site (criterion 5)',
     '    if (site, project["id"]) not in allowed:',
     '    if project["id"] not in [p for _, p in allowed]:'),
    ('E. The allowlist is not checked again at the confirmation (criterion 5)',
     '    """The one place that decides what a change means. The preview shows its result; confirm compares with it."""\n    check_allowlist(site, allowed, issue, allowlist_path)\n',
     '    """The one place that decides what a change means. The preview shows its result; confirm compares with it."""\n'),
    ('F. The permission check is not applied (criterion 4)',
     '    if not permissions["BROWSE_PROJECTS"] or not permissions["ADD_COMMENTS"]:',
     '    if False:'),
    ('G. No answer to the permission check is taken as yes (criterion 4)',
     '    if not isinstance(found, dict):\n        raise Refused("Jira did not answer the permission check',
     '    if not isinstance(found, dict):\n        return {name: True for name in names}\n    if False:\n        raise Refused("Jira did not answer the permission check'),
    ('H. A confirmation with no fingerprint is accepted (criterion 6)',
     '    if not code:\n        raise Refused("no confirmation was given. A confirmation names',
     '    if not code:\n        code = sorted(os.listdir(os.path.join(args.state, "previews")))[0][:12]\n    if False:\n        raise Refused("no confirmation was given. A confirmation names'),
    ('I. A confirmation with no name is accepted (criterion 6)',
     '    if not name:\n        raise Refused("no confirmation was given. A confirmation gives',
     '    if False:\n        raise Refused("no confirmation was given. A confirmation gives'),
    ('J. A preview never expires (criterion 6)',
     '    if age > datetime.timedelta(minutes=LIMIT_MINUTES):',
     '    if False:'),
    ('K. A preview is good for an hour (criterion 6)',
     'LIMIT_MINUTES = 15',
     'LIMIT_MINUTES = 60'),
    ('L. A text changed after the preview is sent (criterion 6)',
     '    if shown_before["text"] != now["text"] or shown_before["source_sha"] != now["source_sha"]:',
     '    if False:'),
    ('M. A visibility changed after the preview is sent (criterion 6)',
     '    if not same_visibility(shown_before["visibility"], now["visibility"]):',
     '    if False:'),
    ('N. A story changed in the change file after the preview is sent (criterion 6)',
     '    if change["ref"] != before["ref"]:',
     '    if False:'),
    ('O. A saved preview that was altered is accepted (criterion 6)',
     '    if genuine != record.get("fingerprint") or genuine[:12] != code:',
     '    if False:'),
    ('P. A fingerprint can be used twice (criterion 8)',
     '    if status == "written":',
     '    if False:'),
    ('Q. A preview whose write was sent and failed can be used again',
     '    if status != "open":',
     '    if False:'),
    ('R. The duplicate check is not made at the preview (criterion 8)',
     '    there = already_there(proposal)\n',
     '    there = []\n'),
    ('S. The duplicate check is not made again at the confirmation (criterion 8)',
     '    if already_there(now):',
     '    if False:'),
    ('T. The duplicate check counts a comment by anyone as this one',
     '    mine = [c for c in same if (c.get("author") or {}).get("accountId") == me]',
     '    mine = same'),
    ('U. The duplicate check ignores visibility',
     '    return [c["id"] for c in proposal["same_mine"] if same_visibility(c["visibility"], proposal["visibility"])]',
     '    return [c["id"] for c in proposal["same_mine"]]'),
    ('V. Only the first page of comments is read',
     '        if start >= total or not page:\n            return comments',
     '        return comments'),
    ('W. A list of comments that cannot be read is taken as empty',
     '        if not isinstance(page, list) or not isinstance(total, int):\n            raise Refused(',
     '        if not isinstance(page, list) or not isinstance(total, int):\n            return []\n        if False:\n            raise Refused('),
    ('X. The text sent is not the text previewed (criterion 2)',
     '        body = {"body": document_of(text)}',
     '        body = {"body": document_of(text + " ")}'),
    ('Y. The comment is not compared with the preview when read back (criterion 2)',
     'hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:16]), text == proposal["text"]),',
     'hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:16]), True),'),
    ('Z. Formatting or a mention that Jira added is not noticed',
     '(", ".join(sorted(set(odd))) if odd else "no formatting, links or mentions"), not odd),',
     '(", ".join(sorted(set(odd))) if odd else "no formatting, links or mentions"), True),'),
    ('AA. The author of the comment read back is not checked',
     '("its author is this identity", (comment.get("author") or {}).get("accountId") == me),',
     '("its author is this identity", True),'),
    ('AB. The visibility of the comment read back is not checked',
     '               same_visibility(seen, proposal["visibility"]))]',
     '               True)]'),
    ('AC. A role restriction is asked for and not sent',
     '        if visibility["kind"] == "role":\n            body["visibility"]',
     '        if False:\n            body["visibility"]'),
    ('AD. The visibility is not shown under the text (criterion 1)',
     '    say("  WHO CAN SEE IT: %s" % shown_visibility(proposal["visibility"], proposal["key"], proposal["security"]))\n    say("    This workflow cannot list',
     '    say("    This workflow cannot list'),
    ("AE. The story's security level is not shown",
     'else " The story has the security level %s, which limits who can see it." % json.dumps(security) if security',
     'else " The story has no security level." if security'),
    ('AF. A security level put on the story after the preview is not noticed',
     '    if shown_before["security"] != now["security"]:',
     '    if False:'),
    ('AG. Where the text came from is not shown (criterion 1)',
     '    say("  Where the text came from: the file %s beside the change file, sha256 %s." % (proposal["source"], proposal["source_sha"]))\n',
     ''),
    ('AH. A text that looks like a secret is sent (stretch goal)',
     '    for what, pattern in SECRETS:\n        if pattern.search(text):',
     '    for what, pattern in SECRETS:\n        if False:'),
    ('AI. The secret that was matched is printed in the refusal',
     '"send it. The matching text is not shown here" % (what, ", on line %d" % line if line else ""))',
     '"send it. The matching text is not shown here: %s" % (what, ", on line %d" % line if line else "", pattern.search(text).group(0)))'),
    ('AJ. What may be private is not pointed out',
     '    return ["line %d: %s" % (number, what) for number, line in enumerate(lines, 1) for what, pattern in PRIVATE if pattern.search(line)]',
     '    return []'),
    ('AK. An empty line in the text is sent',
     '        if not line.strip():',
     '        if False:'),
    ('AL. A character that cannot be seen is sent',
     '        if UNSEEN.search(line):',
     '        if False:'),
    ('AM. The text file may be anywhere on the computer',
     '    if not isinstance(name, str) or not FILE_NAME.fullmatch(name):',
     '    if not isinstance(name, str):'),
    ('AN. Any visibility is accepted as everyone',
     '        raise Refused("visibility must be \\"everyone\\", or {\\"role\\": \\"the name of a project role\\"}. Nothing else is supported")',
     '        wanted = {"kind": "everyone"}'),
    ('AO. A role the project does not have is sent',
     '    if not found:\n        raise Refused("the project has no role named',
     '    if not found:\n        return "0"\n    if False:\n        raise Refused("the project has no role named'),
    ('AP. The write is sent again when no answer comes',
     '            raise NeedsLooking("the write was sent and no answer came back (%s). It is NOT KNOWN whether Jira added "',
     '            self._post(path, None, body)\n            raise NeedsLooking("the write was sent and no answer came back (%s). It is NOT KNOWN whether Jira added "'),
    ('AQ. A refusal from Jira is reported as written',
     '    if status not in (200, 201) or not ident(comment_id):',
     '    if False:'),
    ('AR. A second copy made in the last moment is not reported',
     '    if len(twins) != 1:\n        raise NeedsLooking("the comment was added',
     '    if False:\n        raise NeedsLooking("the comment was added'),
    ('AS. A comment that does not read back as previewed is reported as done',
     '    if not all(ok for _, ok in checks):\n        raise NeedsLooking(',
     '    if False:\n        raise NeedsLooking('),
    ('AT. The story changing during the preview is not noticed',
     '    if after != before:\n        raise Refused("the story or its comments changed',
     '    if False:\n        raise Refused("the story or its comments changed'),
    ("AU. The result record leaves out the comment's identifier (criterion 7)",
     '            "Identifier of what was created: Jira comment id %s, on that issue" % result["comment_id"],\n',
     ''),
    ('AV. The result record leaves out who confirmed (criterion 7)',
     '            "Confirmed by: %s, at %s" % (result["confirmed_by"], result["confirmed_at"]),\n',
     ''),
    ("AW. The site's address is left in a saved log",
     '        saved = text.replace("https://" + host, SITE_MARK).replace(host, SITE_MARK) if host else text',
     '        saved = text'),
    ("AX. The site's address is left in the result record",
     '            f.write(text.replace(conn.host, SITE_MARK))',
     '            f.write(text.replace("[site address removed]", "https://" + conn.host))'),
    ('AY. The check passes a comment whose text was changed',
     '    ok = all(good for _, good in checks) and len(twins) == 1 and now_level == result["security"]',
     '    ok = True'),
    ('AZ. The check can write',
     'conn = Connection(fake.get, fake.post if args.command == "confirm" else None, host)',
     'conn = Connection(fake.get, fake.post, host)'),
    ('BA. A confirmation against another Jira site is accepted',
     '    if site != before["site"]:',
     '    if False:'),
    ('BB. Text from a comment already on the story is printed',
     '    say("  With the same text, by someone else:  %d%s." % (len(proposal["same_others"]),',
     '    say("  Others: %s" % [text_of(c.get("body"))[0] for c in comments])\n    say("  With the same text, by someone else:  %d%s." % (len(proposal["same_others"]),'),
    ('BC. A read that fails after the write is reported as nothing written',
     '            if posted():\n                raise NeedsLooking("the write was sent, and a step after it could not be done',
     '            if False:\n                raise NeedsLooking("the write was sent, and a step after it could not be done'),
    ('BD. A failure of the program after the write hides that it was sent',
     '            if posted():\n                raise NeedsLooking("the write was sent, and the program then failed',
     '            if False:\n                raise NeedsLooking("the write was sent, and the program then failed'),
    ("BE. The comment's identifier is not kept until everything after the write has worked",
     '    save_json(os.path.join(args.state, "written", code + ".json"), result)   # kept at once, so that the comment\'s identifier is not lost\n',
     ''),
    ('BF. Two runs confirming one preview at once both write',
     '    except FileExistsError:\n        raise Refused("another run',
     '    except FileExistsError:\n        pass\n    if False:\n        raise Refused("another run'),
    ('BG. The count after the write ignores visibility',
     '            and same_visibility(visibility_of(c), proposal["visibility"])]',
     '            ]'),
    ('BH. A role is sent with its number as well as its name',
     '            body["visibility"] = {"type": "role", "value": visibility["name"]}',
     '            body["visibility"] = {"type": "role", "value": visibility["name"], "identifier": visibility["id"]}'),
    ('BI. A story for which Jira gives no security field is said to have no level',
     '    if "security" not in issue["fields"]:\n        return "?"',
     '    if "security" not in issue["fields"]:\n        return None'),
    ('BJ. An unrestricted comment is sent to a service project',
     '    if kind == "service_desk" and change["visibility"]["kind"] == "everyone":',
     '    if False:'),
    ('BK. Another allowlist file at the confirmation is accepted',
     '    if shown_before["allowlist"] != now["allowlist"]:',
     '    if False:'),
    ("BL. The site's address may carry a port or a path",
     '    if not host or base != "https://" + host:',
     '    if not host:'),
    ('BM. Looking at the story in a browser during a preview stops it',
     '"security": fields.get("security"), "comments": comments})',
     '"security": fields.get("security"), "fields": fields, "comments": comments})'),
    ('BN. The check prints unseen characters that Jira returns',
     '    show_text(UNSEEN.sub("?", text) if text is not None else "(could not be read)")',
     '    show_text(text if text is not None else "(could not be read)")'),
    ("BO. Jira's own words in a refusal are printed as they come",
     'json.dumps(UNSEEN.sub(" ", " / ".join(texts))[:200])',
     '\'"%s"\' % " / ".join(texts)'),
    ('BP. The preview does not say which allowlist file was used',
     '    say("            On the sandbox allowlist: yes. The allowlist is %s." % proposal["allowlist"])\n',
     ''),
    ('BQ. The preview does not say under whose account the comment appears',
     '    say("  It would appear under the Jira account the API token belongs to, called this identity below. Not under the")\n',
     ''),
]

def run_tests():
    done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=SKILL,
                          capture_output=True, text=True)
    failed = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\w+) \((?:test_comment\.)?(\w+)", done.stderr, re.M)))
    return done.stderr.strip().splitlines()[-1], ["%s.%s" % (group, name) for name, group in failed]


def main():
    with open(TARGET, encoding="utf-8") as f:
        good = f.read()
    out = ["Do the tests notice a broken comment workflow? jira-add-comment, attempt jira-attempt-013",
           "Recorded by scripts/planted_bugs.py.", "",
           "Each bug below was put into participant/skills/jira-add-comment/comment.py, every test was run, and the",
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
    out += ["After the last bug was taken out: comment.py is %s it was at the start. %s"
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
