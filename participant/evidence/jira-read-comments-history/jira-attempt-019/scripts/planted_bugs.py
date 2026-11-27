#!/usr/bin/env python3
"""Plants one bug at a time in a COPY of participant/skills/jira-read-comments-history/sync_comments.py and runs the tests against
the copy. Records logs/planted-bugs.txt. The real tool is never changed: the copy is in a temporary folder.

A bug that is CAUGHT made at least one test fail. A bug that is MISSED left every test passing: the tests would not
notice that mistake. Some mistakes are deliberately not planted, because a second check in the tool catches what the
first lets through, so no test can tell them apart from the outside. They are listed at the end of the record.

Run from anywhere:  python3 scripts/planted_bugs.py        Exit code 0 if every bug was caught, 1 if not.
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ATTEMPT = os.path.dirname(HERE)
PARTICIPANT = os.path.abspath(os.path.join(ATTEMPT, "..", "..", ".."))
REPO = os.path.dirname(PARTICIPANT)
SKILL = os.path.join(PARTICIPANT, "skills", "jira-read-comments-history")
CONFIG = os.path.join(PARTICIPANT, "context", "jira", "history-rules.md")
LIMIT = 120

BUGS = [
    # matched by identifier, added once
    ("a comment is not looked up by its identifier, so every sync adds every comment again: the quest's scenario", "        have = by_id.get(fresh[\"id\"])", "        have = None"),
    ("a material change is added again on every sync", "        if change[\"id\"] not in known:", "        if True:"),
    ("the files are written even when nothing changed", "        if before[0] != hashlib.sha256(copy_text.encode(\"utf-8\")).hexdigest():", "        if True:"),
    # an edit
    ("an edited comment keeps its old text", "            have.update(text=fresh[\"text\"], text_cut=fresh[\"text_cut\"], not_all_text=fresh[\"not_all_text\"], body_checksum=fresh[\"body_checksum\"], updated=fresh[\"updated\"])",
     "            have.update(body_checksum=fresh[\"body_checksum\"], updated=fresh[\"updated\"])"),
    ("the checksum noted for an edit is of the new text, not the text replaced", "\"replaced_text_checksum\": checksum(have[\"text\"])", "\"replaced_text_checksum\": checksum(fresh[\"text\"])"),
    ("every edit is said to be by the author", "{\"noticed\": now, \"jira_says_edited\": fresh[\"updated\"], \"by\": fresh[\"edited_by\"],", "{\"noticed\": now, \"jira_says_edited\": fresh[\"updated\"], \"by\": \"its author\","),
    ("author and someone else are the wrong way round", "\"its author\" if author == editor else \"someone else\"", "\"its author\" if author != editor else \"someone else\""),
    ("the time until an edit was noticed is counted from when the comment was written", "\"seconds_until_noticed\": seconds_between(fresh[\"updated\"], now)})", "\"seconds_until_noticed\": seconds_between(fresh[\"created\"], now)})"),
    ("a comment already edited when first copied does not say so", "\"edited_before_first_sync\": {\"by\": fresh[\"edited_by\"], \"jira_says_edited\": fresh[\"updated\"]} if fresh[\"updated\"] != fresh[\"created\"] else None}", "\"edited_before_first_sync\": None}"),
    ("a new edit time with the same body is called an edit", "        if have[\"text\"] != fresh[\"text\"]:", "        if have[\"text\"] != fresh[\"text\"] or have[\"updated\"] != fresh[\"updated\"]:"),
    # a deletion
    ("a comment Jira no longer lists is taken out of the copy, silently", "    known = set(h[\"id\"] for h in copy[\"history\"])", "    copy[\"comments\"] = [c for c in copy[\"comments\"] if c[\"id\"] in listed]\n    known = set(h[\"id\"] for h in copy[\"history\"])"),
    ("a comment Jira no longer lists is not marked", "            if have.get(\"in_jira\", True):\n                have[\"in_jira\"] = False", "            if False:\n                have[\"in_jira\"] = False"),
    ("a marked comment is marked again by every later sync", "            if have.get(\"in_jira\", True):\n                have[\"in_jira\"] = False", "            if True:\n                have[\"in_jira\"] = False"),
    ("a marked comment loses its text", "                have[\"not_returned_since\"] = now", "                have[\"not_returned_since\"] = now\n                have[\"text\"] = \"\""),
    ("a marked comment is left off the page", "    for c in copy[\"comments\"]:\n        out.append(\"### Comment %s\" % c[\"id\"])", "    for c in [c for c in copy[\"comments\"] if c.get(\"in_jira\", True)]:\n        out.append(\"### Comment %s\" % c[\"id\"])"),
    ("a marked comment that Jira returns again stays marked", "        if not have.get(\"in_jira\", True):\n            have[\"in_jira\"] = True", "        if False:\n            have[\"in_jira\"] = True"),
    # nothing changes unless everything was read
    ("a page that fails is taken for the end of the list, so the comments after it look deleted", "            raise Refused(\"Jira did not list the story's %s (status %d)\" % (what, status))", "            return entries"),
    ("fewer arriving than Jira's own count is accepted", "            if len(entries) != total or total != first_total:", "            if False:"),
    ("an entry that comes twice is accepted", "            if entry[\"id\"] in seen:", "            if False:"),
    ("an answer with a status other than 200 is read as a list", "(body.get(list_name), body.get(\"total\")) if status == 200 and isinstance(body, dict) else (None, None)", "(body.get(list_name), body.get(\"total\")) if isinstance(body, dict) else (None, None)"),
    ("a total of `true` is taken for a number", "not isinstance(total, int) or isinstance(total, bool) or total < 0:", "not isinstance(total, int) or total < 0:"),
    ("a story that has been moved or renamed is read as the one asked for", "    if body[\"key\"].upper() != key.upper():", "    if False:"),
    ("a copy of another story, or from another Jira, is brought up to date with this one", "    elif (copy[\"story\"].get(\"id\"), copy.get(\"source\"), copy.get(\"site_fingerprint\")) != (story[\"id\"], source, site):", "    elif False:"),
    ("a copy that is not one this tool wrote is used anyway", "    if not good:", "    if False:"),
    # the history
    ("noise is kept as if it were material", "            elif name in NOISE_NAMES:\n                noise[name] = noise.get(name, 0) + 1",
     "            elif name in NOISE_NAMES:\n                material.append({\"id\": \"%s:%d\" % (entry[\"id\"], place), \"at\": at, \"kind\": name, \"from\": \"\", \"to\": clean(item.get(\"toString\")) or \"\"})"),
    ("rank is not on the noise list", "NOISE_NAMES = [name for name, _ in NOISE]", "NOISE_NAMES = [name for name, _ in NOISE if name != \"rank\"]"),
    ("a field on neither list is dropped without a word", "                unlisted[label] = unlisted.get(label, 0) + 1", "                pass"),
    ("the names of assignees are kept", "    (\"assignee\", \"person\",", "    (\"assignee\", \"names\","),
    ("old and new titles are kept", "    (\"summary\", \"fact\",", "    (\"summary\", \"names\","),
    ("the whole sentence of a link is kept, not only the other item's key", "        added, removed = key_of(item, \"to\"), key_of(item, \"from\")", "        added, removed = new, old"),
    ("the time until a change was noticed is not worked out", "seconds_until_noticed=seconds_between(change[\"at\"], now)))", "seconds_until_noticed=0))"),
    ("names chosen by the site's administrators are kept as they come", "    return \"\".join(ch if (ch.isalnum() or ch in KEPT_MARKS) and not UNSEEN.match(ch) else \"?\" for ch in value)[:limit].strip() or None", "    return value[:limit].strip() or None"),
    # the notes
    ("the sync adds a line to the notes", "    after = (file_sum(copy_path), file_sum(page_path))", "    open(notes_path, \"a\").write(\"synced\\n\") if os.path.exists(notes_path) else None\n    after = (file_sum(copy_path), file_sum(page_path))"),
    ("the sync opens the notes for writing and writes nothing", "    after = (file_sum(copy_path), file_sum(page_path))", "    open(notes_path, \"a\").close() if os.path.exists(notes_path) else None\n    after = (file_sum(copy_path), file_sum(page_path))"),
    ("the sync makes a notes file where there was none", "    after = (file_sum(copy_path), file_sum(page_path))", "    open(notes_path, \"a\").close()\n    after = (file_sum(copy_path), file_sum(page_path))"),
    ("a changed notes file is still called unchanged", "\"UNCHANGED. This tool never writes it\" if notes_before == notes_after else", "\"UNCHANGED. This tool never writes it\" if True else"),
    ("a refusal is saved over the notes when --log names them: the bug the tests found in the first version", "                log_to = None           # and", "                pass           # and"),
    ("--log may name the notes or one of the two files", "                    may_write(log_to, own)", "                    pass"),
    ("a copy or page that is a link, or has a second name, is written through", "        if os.path.islink(path) or os.path.isdir(path) or (os.path.exists(path) and os.stat(path).st_nlink > 1):", "        if os.path.isdir(path):"),
    # other people's text, and people
    ("a comment's fence is three tildes whatever the comment holds", "    return \"~\" * (longest + 1)", "    return \"~~~\""),
    ("unseen characters in a comment are kept", "        text = plain(text_of(body, 0, lost).strip(\"\\n\"))", "        text = text_of(body, 0, lost).strip(\"\\n\")"),
    ("the name in a mention is kept", "        return \"[a person]\"", "        return str(node.get(\"attrs\", {}).get(\"text\", \"\"))"),
    ("the output prints a comment's text", "    say(\"  unchanged:                      %d\" % len(done[\"unchanged\"]))", "    say(\"  unchanged:                      %d %s\" % (len(done[\"unchanged\"]), copy[\"comments\"][0][\"text\"]))"),
    ("a long comment is cut without saying so", "\"text\": text[:TEXT_LIMIT], \"text_cut\": cut,", "\"text\": text[:TEXT_LIMIT], \"text_cut\": False,"),
    # the files
    ("a page that was changed or lost is not put right", "        if before[1] != hashlib.sha256(page_text.encode(\"utf-8\")).hexdigest():", "        if wrote:"),
    ("a write that fails halfway leaves its temporary file", "            os.unlink(temporary)", "            pass"),
    ("a write that fails is reported as an ordinary refusal, with the copy said to be as it was", "        raise WriteFailed(\"a file could not be written", "        raise Refused(\"a file could not be written"),
    ("something unforeseen is a crash", "    except Exception as surprise:", "    except KeyboardInterrupt as surprise:"),
    # only reads, and nothing private
    ("a live sync may write anywhere", "    if live and \"local-data\" not in folder.split(os.sep):", "    if False:"),
    ("the connection will send a GET anywhere", "        if not re.fullmatch(r\"/rest/api/3/issue/[A-Za-z0-9_-]+(/comment(/[0-9]{1,20})?|/changelog)?\", path):", "        if False:"),
    ("any request is reported as a plain GET", "        return all(method.split(\" \")[0] == \"GET\" and \"BODY\" not in method for method, _ in self.sent)", "        return True"),
    ("the made-up Jira's switches are accepted for a real Jira", "                if args.state or args.pretend_now:", "                if False:"),
    ("the output is not searched for the credentials", "    if any(secret and secret in text for secret in secrets):", "    if False:"),
    ("only the token is searched for", "    return Connection(get, host), [token, email, encoded]", "    return Connection(get, host), [token]"),
    ("the site's address is left in the saved output", "        kept = kept.replace(\"https://\" + host, SITE_MARK).replace(host, SITE_MARK) if host else kept", "        kept = kept"),
    ("a real server's refusal is not read for its status", "            status, headers, raw = err.code, dict(err.headers), err.read()\n            err.close()", "            raise"),
    # found by the independent readers, or shown by them to be mistakes the first tests would not notice
    ("a place is compared with the notes by its spelling, so the same file in other capitals is written: found by both readers", "    if any(same_file(path, other) for other in own):", "    if any(os.path.realpath(path) == os.path.realpath(other) for other in own):"),
    ("a file of the tool's own may be written to a place named like a notes file", "    if os.path.basename(path).casefold().endswith(\".notes.md\"):\n        raise Refused(\"that place is named like a notes file. This tool never writes one\")", "    if False:\n        raise Refused(\"that place is named like a notes file. This tool never writes one\")"),
    ("the rules may be written over a file that is not a rules document", "                if not f.read(200).startswith(text.split(\"\\n\")[0]):", "                if False:"),
    ("a comment missing from the list is marked without asking Jira for it: one still there can fall between two pages", "            if status == 200:\n                raise Refused(\"Jira's list of comments left out", "            if False:\n                raise Refused(\"Jira's list of comments left out"),
    ("a comment is marked when Jira would not say whether it is gone", "            if status != 404:", "            if False:"),
    ("a field the site added is material if it has a material field's name", "            rule = None if custom else next((rule for rule in MATERIAL if rule[0] == name), None)", "            rule = next((rule for rule in MATERIAL if rule[0] == name), None)"),
    ("a field's name is compared with its capitals", "            name = item[\"field\"].strip().casefold()", "            name = item[\"field\"].strip()"),
    ("a key is picked out of a sentence", "        if isinstance(value, str) and REF.fullmatch(value.strip()):", "        if isinstance(value, str) and REF.search(value.strip()):"),
    ("two statuses of the same name are kept with nothing said", "if before == after else \"\")", "if False else \"\")"),
    ("the line about an edit before the first copy gives the comment's latest edit time", "c[\"edited_before_first_sync\"][\"by\"], c[\"edited_before_first_sync\"][\"jira_says_edited\"]))", "c[\"edited_before_first_sync\"][\"by\"], c[\"updated\"]))"),
    ("a comment that is not all plain text does not say so", "\"not_all_text\": sorted(set(lost)),", "\"not_all_text\": [],"),
    ("one comment whose body cannot be read stops the whole sync", "        text, lost = \"[this comment's body is not in a form this tool reads]\", [\"the whole body\"]", "        raise Refused(\"a comment's body could not be read\")"),
    ("half a character in a comment stops the sync", "    return re.sub(\"[\\ud800-\\udfff]\", \"?\", UNSEEN.sub(\"?\", text))", "    return UNSEEN.sub(\"?\", text)"),
    ("a body that changes with the same words is called an edit", "        if have[\"text\"] != fresh[\"text\"]:", "        if have[\"body_checksum\"] != fresh[\"body_checksum\"]:"),
    ("a comment's lines are not set in, so one can start like a heading of the page", "[\"    \" + line for line in c[\"text\"].split(\"\\n\")]", "c[\"text\"].split(\"\\n\")"),
    ("an editor Jira does not name is taken for the author", "    by = \"unknown\" if not (isinstance(author, str) and author and isinstance(editor, str) and editor) else \"its author\" if author == editor", "    by = \"its author\" if author == editor"),
    ("Jira's count changing while the list is read is accepted", "            if len(entries) != total or total != first_total:", "            if len(entries) != total:"),
    ("more pages than the tool reads gives a shorter list, not a refusal", "    raise Refused(\"the story has more than %d %s, which is more than this tool reads\" % (MAX_PAGES * PAGE, what))", "    return entries"),
    ("a history entry without a time is skipped", "        if at is None or not isinstance(items, list):\n            raise Refused(", "        if at is None or not isinstance(items, list):\n            continue\n            raise Refused("),
    ("Jira's times are labelled UTC without being turned into UTC", "datetime.datetime.strptime(value, shape).astimezone(datetime.timezone.utc).strftime(", "datetime.datetime.strptime(value, shape).strftime("),
    ("redirects are followed", "    opener = opener or urllib.request.build_opener(NoRedirect)", "    opener = opener or urllib.request.build_opener()"),
    ("an address with a path or a port, or without https, is accepted", "    if not host or base.lower() != \"https://\" + host:", "    if not host:"),
    ("the method reported is the word GET, not the request's own", "        return status, headers, parsed, request.get_method(), request.data is not None", "        return status, headers, parsed, \"GET\", False"),
    ("the name of an unlisted field is printed as it comes", "                label = clean(item[\"field\"], 40) or \"a field with no name\"", "                label = item[\"field\"]"),
]

NOT_PLANTED = [
    "The rules document written from some other text than the lists: a test compares the file, byte for byte, with what the tool writes.",
    "The check on --log for a link or a second name, taken out: the disk's own answer to \"are these one file\" still refuses it.",
    "The disk's own answer taken out: the check for a link or a second name still refuses it.",
    "The last guard, inside the function that writes a file, taken out: the checks before it still refuse a notes file's name.",
    "The check of `rules --write` for a notes file's name, taken out: the notes file is then refused as not being a rules document.",
    "In each, a second check refuses what the first lets through, so no test can tell from the outside which one did.",
]


def run_tests(folder):
    try:
        done = subprocess.run([sys.executable, "-B", "-m", "unittest", "tests.test_sync_comments"], cwd=folder, capture_output=True, text=True, timeout=LIMIT)
    except subprocess.TimeoutExpired:
        return False, "stopped after %d seconds" % LIMIT
    last = (done.stderr.strip().split("\n") or [""])[-1]
    failed = sorted(set(line.split(" ")[1] for line in done.stderr.split("\n") if line.startswith(("FAIL: ", "ERROR: "))))
    return done.returncode == 0, "%s%s" % (last, (": " + ", ".join(failed[:2]) + (" ..." if len(failed) > 2 else "")) if failed else "")


def git_state():
    return subprocess.run(["git", "-C", REPO, "status", "--porcelain", "--untracked-files=all"], capture_output=True, text=True).stdout


def main():
    before = git_state()
    with open(os.path.join(SKILL, "sync_comments.py"), encoding="utf-8") as f:
        source = f.read()
    lines = ["Planted bugs in a copy of participant/skills/jira-read-comments-history/sync_comments.py. jira-read-comments-history, attempt jira-attempt-019",
             "Recorded by scripts/planted_bugs.py. One bug at a time is planted in a copy of the tool, in a temporary folder, and the tests are run",
             "against the copy. CAUGHT means at least one test failed. The real tool is not changed.", ""]
    temp = tempfile.mkdtemp(prefix="gtq-planted-")
    missed, problems = [], []
    try:
        work = os.path.join(temp, "participant", "skills", "jira-read-comments-history")
        shutil.copytree(SKILL, work, ignore=shutil.ignore_patterns("__pycache__"))
        os.makedirs(os.path.join(temp, "participant", "context", "jira"))
        shutil.copy(CONFIG, os.path.join(temp, "participant", "context", "jira"))
        copy = os.path.join(work, "sync_comments.py")
        passed, said = run_tests(work)
        lines.append("First, with no bug planted, the tests against the copy: %s" % said)
        if not passed:
            lines.append("THE TESTS DO NOT PASS WITHOUT A BUG, so nothing below would mean anything. Stopped.")
            problems.append("the tests fail with no bug planted")
        else:
            lines.append("")
            for number, (what, old, new) in enumerate(BUGS, 1):
                if source.count(old) != 1 or old == new:
                    lines.append("%2d. NOT PLANTED  %s: the text to change was found %d times, not once" % (number, what, source.count(old)))
                    problems.append("bug %d could not be planted" % number)
                    continue
                with open(copy, "w", encoding="utf-8") as f:
                    f.write(source.replace(old, new))
                passed, said = run_tests(work)
                lines.append("%2d. %-7s %s" % (number, "MISSED" if passed else "CAUGHT", what))
                lines.append("            %s" % said)
                if passed:
                    missed.append(what)
            with open(copy, "w", encoding="utf-8") as f:
                f.write(source)
            passed, said = run_tests(work)
            lines += ["", "Last, with the copy put back as it was: %s" % said]
            if not passed:
                problems.append("the tests fail after the copy was put back")
    finally:
        shutil.rmtree(temp, ignore_errors=True)
    with open(os.path.join(SKILL, "sync_comments.py"), encoding="utf-8") as f:
        same = f.read() == source
    unchanged = git_state() == before
    lines.append("The real tool is byte for byte what it was before: %s" % ("yes" if same else "NO"))
    lines.append("Git reports the same state of the whole repository as before the run: %s" % ("yes" if unchanged else "NO"))
    if not same or not unchanged:
        problems.append("something in the repository changed")
    lines += ["", "NOT PLANTED, AND WHY"] + ["  " + line for line in NOT_PLANTED]
    planted = len(BUGS) - sum(1 for p in problems if "could not be planted" in p)
    result = "RESULT: %d OF %d PLANTED BUGS CAUGHT." % (planted - len(missed), len(BUGS)) + ("" if not missed and not problems else " NOT ALL: " + "; ".join(missed + problems))
    lines += ["", result]
    with open(os.path.join(ATTEMPT, "logs", "planted-bugs.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print(result)
    for line in lines:
        if "MISSED" in line or "NOT PLANTED " in line:
            print(line)
    return 0 if not missed and not problems else 1


if __name__ == "__main__":
    sys.exit(main())
