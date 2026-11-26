#!/usr/bin/env python3
"""Records logs/planted-bugs.txt for the jira-create-subtask quest.

Puts one bug at a time into participant/skills/jira-create-subtask/subtask.py,
runs every test, notes which tests fail, and takes the bug out again. At the
end it checks that the file is the same as when it started, byte for byte.

It changes subtask.py while it runs. Do not run the skill at the same time.

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
SKILL = os.path.join(ROOT, "participant", "skills", "jira-create-subtask")
TARGET = os.path.join(SKILL, "subtask.py")

# (what the bug is, the text to replace, what to replace it with)
BUGS = [
    ('A. A preview can write (criterion 4)',
     '        if self._post is None:\n            raise Refused("this command has no way to write")\n',
     ''),
    ('B. The live preview is handed the write function (criterion 4)',
     'return Connection(get, post if may_write else None, host), [token, email, encoded]',
     'return Connection(get, post, host), [token, email, encoded]'),
    ('C. The fake preview is handed the write function (criterion 4)',
     'conn = Connection(fake.get, fake.post if args.command == "confirm" else None, host)',
     'conn = Connection(fake.get, fake.post, host)'),
    ('D. A live connection will send any write (criterion 4)',
     '        if path != WRITE_PATH or params or set(body) != {"fields"} or not isinstance(fields, dict) or set(fields) != {"project", "parent", "issuetype", "summary"}:',
     '        if False:'),
    ('E. A parent that is a subtask is accepted (criterion 2)',
     '    if issue["fields"]["issuetype"]["subtask"]:',
     '    if False:'),
    ('F. A closed parent is accepted (the closed-parent rule)',
     '    if category == "done":',
     '    if False:'),
    ('G. A status with no category is taken as open (the closed-parent rule)',
     '    if not isinstance(category, str) or not re.fullmatch(r"[a-z_]{1,30}", category):',
     '    if False:'),
    ('H. A parent Jira does not return is not refused as missing (criterion 2)',
     '    if status == 404:\n        raise Refused("Jira answered 404 for %s.',
     '    if False:\n        raise Refused("Jira answered 404 for %s.'),
    ('I. The parent may be given as any text, a title included (criterion 1)',
     '    if not isinstance(ref, str) or not REF.fullmatch(ref):\n        raise Refused("the parent is given by its key',
     '    if False:\n        raise Refused("the parent is given by its key'),
    ('J. The parent checks are not made again at the confirmation (criterion 2)',
     '    check_allowlist(site, allowed, issue, allowlist_path)\n    parent_checks(issue)\n    if not permissions',
     '    check_allowlist(site, allowed, issue, allowlist_path)\n    if not permissions'),
    ('K. The write names the parent by the reference in the change file, not the pinned id (criterion 1)',
     '    parent_id = before["parent_id"]\n    if change["ref"] != parent_id and read_issue(conn, change["ref"])["id"] != parent_id:',
     '    parent_id = read_issue(conn, change["ref"])["id"]\n    if False:'),
    ('L. A reference that now leads to another issue is not noticed (criterion 1)',
     '    if change["ref"] != parent_id and read_issue(conn, change["ref"])["id"] != parent_id:',
     '    if False:'),
    ('M. The subtask is sent with the project as its parent id (criterion 3)',
     'conn.post_subtask(proposal["project_id"], parent_id, proposal["subtask_type"]["id"], proposal["summary"])',
     'conn.post_subtask(proposal["project_id"], proposal["project_id"], proposal["subtask_type"]["id"], proposal["summary"])'),
    ('N. The parent read back is not compared with the parent intended (criterion 3)',
     '% (parent_id or "NOT GIVEN", proposal["parent_id"], proposal["parent_key"]), parent_id == proposal["parent_id"]),',
     '% (parent_id or "NOT GIVEN", proposal["parent_id"], proposal["parent_key"]), True),'),
    ('O. The read-back takes the intended parent as the parent read (criterion 3)',
     '    parent_id = parent.get("id") if ident(parent.get("id")) else None\n',
     '    parent_id = proposal["parent_id"]\n'),
    ('P. The type read back is not checked (criterion 3)',
     'kind.get("subtask") is True),',
     'True),'),
    ('Q. The title read back is not compared (criterion 3)',
     '               summary == proposal["summary"]),',
     '               True),'),
    ('R. A failed read-back still ends as done (criterion 3)',
     '    if not all(ok for _, ok in checks):\n        raise NeedsLooking("Jira accepted the write, and the subtask does not read back as previewed")\n',
     ''),
    ('S. The check command does not fail on a wrong parent (criterion 3)',
     '    ok = all(good for _, good in checks) and len(twins) == 1\n    say("")\n    say("FOUND',
     '    ok = True\n    say("")\n    say("FOUND'),
    ('T. The check does not compare the write record with the preview (criterion 3)',
     'previewed.get("parent_id") == result["parent_id"]))',
     'True))'),
    ('U. The allowlist is not checked (criterion 6)',
     '    if (site, project["id"]) not in allowed:',
     '    if False:'),
    ('V. The allowlist is checked by project id alone, on any site (criterion 6)',
     '    if (site, project["id"]) not in allowed:',
     '    if project["id"] not in [p for _, p in allowed]:'),
    ('W. The allowlist is not checked again at the confirmation (criterion 6)',
     '    check_allowlist(site, allowed, issue, allowlist_path)\n    parent_checks(issue)\n    if not permissions',
     '    parent_checks(issue)\n    if not permissions'),
    ('X. Another allowlist file at the confirmation is accepted (criterion 6)',
     '    if shown_before["allowlist"] != now["allowlist"]:',
     '    if False:'),
    ('Y. The permission check is not applied (criterion 5)',
     '    if not permissions["BROWSE_PROJECTS"] or not permissions["CREATE_ISSUES"]:',
     '    if False:'),
    ('Z. No answer to the permission check is taken as yes (criterion 5)',
     '    if not isinstance(found, dict):\n        raise Refused("Jira did not answer the permission check',
     '    if not isinstance(found, dict):\n        return {name: True for name in names}\n    if False:\n        raise Refused("Jira did not answer the permission check'),
    ('AA. The duplicate check finds nothing (criteria 5 and 9)',
     '            "same": [{"id": c["id"], "key": c["key"]} for c in children if same_title(c["summary"], change["summary"])]}',
     '            "same": []}'),
    ('AB. Titles are compared exactly, so capitals make a title new (criterion 9)',
     'return isinstance(a, str) and isinstance(b, str) and plain(a) == plain(b)',
     'return isinstance(a, str) and isinstance(b, str) and a == b'),
    ('AB2. The same letters encoded another way make a title new (criterion 9)',
     'unicodedata.normalize("NFKC", text)',
     'text'),
    ('AC. A duplicate found at the preview still gets a fingerprint (criterion 9)',
     '        say("No fingerprint is issued, because there is nothing to confirm, and nothing was sent.")\n        return 0\n',
     '        say("No fingerprint is issued, because there is nothing to confirm, and nothing was sent.")\n'),
    ('AD. A duplicate that appears after the preview is not noticed (criterion 9)',
     '    if now["same"]:\n        moved.append(',
     '    if False:\n        moved.append('),
    ('AE. Two subtasks with the title after the write go unreported (criterion 9)',
     '    if len(twins) != 1:\n        raise NeedsLooking("the subtask was created, and the parent now has %d subtasks with this title" % len(twins))\n',
     ''),
    ('AF. A list of subtasks Jira does not give is taken as empty (criterion 5)',
     '    if not isinstance(listed, list):\n        raise Refused("Jira did not list the parent\'s subtasks, so the duplicate check cannot be made")',
     '    if not isinstance(listed, list):\n        return []'),
    ('AG. A confirmation with no fingerprint is accepted (criterion 7)',
     '    if not code:\n        raise Refused("no confirmation was given. A confirmation names',
     '    if not code:\n        code = sorted(os.listdir(os.path.join(args.state, "previews")))[0][:12]\n    if False:\n        raise Refused("no confirmation was given. A confirmation names'),
    ('AH. A confirmation with no name is accepted (criterion 7)',
     '    if not name:\n        raise Refused("no confirmation was given. A confirmation gives',
     '    if False:\n        raise Refused("no confirmation was given. A confirmation gives'),
    ('AI. A preview never expires (criterion 7)',
     '    if age > datetime.timedelta(minutes=LIMIT_MINUTES):',
     '    if False:'),
    ('AJ. A preview is good for an hour (criterion 7)',
     'LIMIT_MINUTES = 15',
     'LIMIT_MINUTES = 60'),
    ('AK. A title changed after the preview is sent (criterion 7)',
     '    if shown_before["summary"] != now["summary"]:',
     '    if False:'),
    ('AL. A parent changed after the preview is accepted (criterion 7)',
     '    if change["ref"] != before["ref"]:\n        raise Refused("the change is not the one that was previewed: it names a different parent.',
     '    if False:\n        raise Refused("the change is not the one that was previewed: it names a different parent.'),
    ('AM. Another change file is accepted (criterion 7)',
     '    if shown_before["source"] != now["source"] or shown_before["source_sha"] != now["source_sha"]:',
     '    if False:'),
    ('AN. An altered saved preview is accepted (criterion 7)',
     '    if genuine != record.get("fingerprint") or genuine[:12] != code:',
     '    if False:'),
    ('AO. A fingerprint can be used twice (criterion 7)',
     '    if status == "written":\n        raise Refused(',
     '    if False:\n        raise Refused('),
    ('AP. A preview whose write went unanswered can be used again (criterion 9)',
     '    if status != "open":\n        raise Refused(',
     '    if False:\n        raise Refused('),
    ('AQ. Two runs can confirm one preview at once (criterion 9)',
     '    except FileExistsError:\n        raise Refused("another run is confirming',
     '    except FileExistsError:\n        pass\n    if False:\n        raise Refused("another run is confirming'),
    ('AR. A preview dated in the future is accepted (criterion 7)',
     '    if age < datetime.timedelta(0):',
     '    if False:'),
    ('AS. A confirmation against another site is accepted (criterion 4)',
     '    if site != before["site"]:',
     '    if False:'),
    ('AT. The fingerprint does not depend on the proposal (criterion 7)',
     'return hashlib.sha256(canonical({"proposal": proposal, "made_at": made_at}).encode("utf-8")).hexdigest()',
     'return hashlib.sha256(canonical({"made_at": made_at}).encode("utf-8")).hexdigest()'),
    ('AU. A change in Jira during the preview is not noticed (criterion 4)',
     '    if after != before:\n        raise Refused("the parent or its subtasks changed',
     '    if False:\n        raise Refused("the parent or its subtasks changed'),
    ('AV. The snapshot leaves out the subtasks (criterion 4)',
     '                      "subtasks": [[c["id"], c["summary"]] for c in children_of(issue)]})',
     '                      "subtasks": []})'),
    ('AW. The result record leaves out the confirmer (criterion 8)',
     '            "Confirmed by: %s, at %s" % (result["confirmed_by"], result["confirmed_at"]),\n',
     ''),
    ('AX. The result record leaves out the identifier of what was created (criterion 8)',
     '            "Identifier of what was created: Jira issue id %s" % result["subtask_id"],\n',
     ''),
    ('AY. A refusal by Jira is reported as not written without reading back (after a write)',
     '        if status in REFUSALS and not new and len(after) == proposal["children"]:',
     '        if status in REFUSALS:'),
    ('AY2. Any failed answer with nothing created yet is reported as not written (after a write)',
     '        if status in REFUSALS and not new and len(after) == proposal["children"]:',
     '        if status >= 400 and not new and len(after) == proposal["children"]:'),
    ('AY3. A credential found after a write does not say a write was sent (after a write)',
     ' A WRITE WAS SENT TO JIRA in this run.',
     ''),
    ('AY4. A log that cannot be saved changes the result of the run (after a write)',
     '        except OSError:\n            print("\\nTHE OUTPUT ABOVE COULD NOT BE SAVED',
     '        except ZeroDivisionError:\n            print("\\nTHE OUTPUT ABOVE COULD NOT BE SAVED'),
    ('AZ. No answer to the write is reported as refused (after a write)',
     '            raise NeedsLooking("the write was sent and no answer came back (%s). It is NOT KNOWN whether Jira created "\n                               "the subtask. It was not sent again" % type(getattr(err, "reason", err)).__name__)',
     '            raise Refused("no answer")'),
    ('BA. A failure after the write is reported as nothing written (after a write)',
     '            if posted():\n                raise NeedsLooking("the write was sent, and the program then failed',
     '            if False:\n                raise NeedsLooking("the write was sent, and the program then failed'),
    ('BB. A failed read after the write is reported as nothing written (after a write)',
     '            if any(method == "POST" for method, _ in self.sent):\n                raise NeedsLooking("after the write was sent, a read failed: %s" % reason)\n',
     ''),
    ('BC. The new issue\'s id is not saved until the read-back is done (after a write)',
     '    save_json(os.path.join(args.state, "written", code + ".json"), result)   # kept at once, so that the new issue\'s id is not lost\n    record["state"] = "written"\n',
     ''),
    ('BD. A title that looks like a secret is sent (the title)',
     '    for what, pattern in SECRETS:\n        if pattern.search(text):\n            raise Refused("the summary looks',
     '    for what, pattern in SECRETS:\n        if False:\n            raise Refused("the summary looks'),
    ('BE. A title with an unseen character is sent (the title)',
     '    if UNSEEN.search(text):\n        raise Refused("the summary has a tab',
     '    if False:\n        raise Refused("the summary has a tab'),
    ('BF. A title of any length is sent (the title)',
     '    if len(text) > MAX_SUMMARY:',
     '    if False:'),
    ('BG. Private-looking things are not pointed out (the title)',
     '    return [what for what, pattern in PRIVATE if pattern.search(text)]',
     '    return []'),
    ('BH. The parent\'s title is saved with the output (privacy)',
     '    say("    | %s" % title, "    | [the parent\'s title was shown on screen and is not saved: %d characters]" % len(title))',
     '    say("    | %s" % title)'),
    ('BI. Unseen characters in the parent\'s title are shown as they came (privacy)',
     '    title = UNSEEN.sub("?", title)[:120] if isinstance(title, str) else "(Jira gave no title)"',
     '    title = title[:120] if isinstance(title, str) else "(Jira gave no title)"'),
    ('BJ. Output holding a credential is shown (credentials)',
     '    if any(secret and secret in text for secret in secrets):',
     '    if False:'),
    ('BK. The site address is saved in the log (privacy)',
     '        kept = kept.replace("https://" + host, SITE_MARK).replace(host, SITE_MARK) if host else kept',
     '        pass'),
    ('BL. An address with a port is accepted for a live run (credentials)',
     '    if not host or base != "https://" + host:',
     '    if not host:'),
    ('BM. A project with two subtask types gets the first (criterion 4)',
     '    if len(found) > 1:',
     '    if False:'),
    ('BN. A name given twice in the change file takes the last (the change file)',
     '        if names.count(name) > 1:',
     '        if False:'),
    ('BO. An extra field in the change file is ignored (the change file)',
     '    if not isinstance(change, dict) or set(change) != {"parent", "summary"}:',
     '    if not isinstance(change, dict) or not {"parent", "summary"} <= set(change):'),
]

def run_tests():
    done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=SKILL,
                          capture_output=True, text=True)
    failed = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\w+) \((?:test_subtask\.)?(\w+)", done.stderr, re.M)))
    return done.stderr.strip().splitlines()[-1], ["%s.%s" % (group, name) for name, group in failed]


def main():
    with open(TARGET, encoding="utf-8") as f:
        good = f.read()
    out = ["Do the tests notice a broken subtask workflow? jira-create-subtask, attempt jira-attempt-014",
           "Recorded by scripts/planted_bugs.py.", "",
           "Each bug below was put into participant/skills/jira-create-subtask/subtask.py, every test was run, and the",
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
    out += ["After the last bug was taken out: subtask.py is %s it was at the start. %s"
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
