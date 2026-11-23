#!/usr/bin/env python3
"""Create one previewed GitHub issue after a person confirms, and tie the local file to it.

See SKILL.md in this folder for what it does and the rules it follows.

    create.py preview   --source fake|live --draft DRAFT.md --index INDEX.md --allowlist FILE --state FOLDER [--link FILE]
    create.py confirm   (the same) --fingerprint F --confirmed-by NAME [--results FOLDER]
    create.py verify    --source fake|live --draft DRAFT.md --allowlist FILE [--link FILE]
    create.py reconcile --source fake|live --draft DRAFT.md --allowlist FILE [--link FILE] [--number N] [--results FOLDER]

`preview`, `verify` and `reconcile` only read GitHub. `confirm` makes one write: it sends the exact bytes the
preview saved, and nothing it built itself. It never sends a create twice, and it never guesses whether one
arrived.

Exit codes: 0 ready, done, verified or reconciled; 1 refused or stopped, nothing was sent; 2 rate-limited, nothing
was sent; 3 a person must look: the outcome is unknown, or the issue is not what the preview showed.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
LINK_FORMAT = "github-issue-link/1"
FINGERPRINT = re.compile(r"^[0-9a-f]{32}$")
EMAIL_SHAPED = re.compile(r"[^\s@]+@[^\s@]+\.[^\s@]+")
CREATE_PATH = re.compile(r"^/repos/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/issues$")
SETTLE_SECONDS = 60        # how long after a lost answer before "GitHub lists no such issue" is believed
MARGIN_SECONDS = 300       # how far before the send time reconcile looks
COMPARED = ("title", "body", "labels", "assignees", "milestone")


def _load(folder, name, alias):
    path = os.path.join(HERE, "..", folder, name)
    spec = importlib.util.spec_from_file_location(alias, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pv = _load("github-create-issue-preview", "preview.py", "preview_skill_used_by_create")
Stop, RateLimited, q, plural, shown_path = pv.Stop, pv.RateLimited, pv.q, pv.plural, pv.shown_path


class Refused(Exception):
    """The workflow will not do this. Nothing was sent."""


class OutcomeUnknown(Exception):
    """The create was sent and no usable answer came back. The issue may or may not exist."""


def say(text=""):
    print(("github-create: " + text) if text else "github-create:", flush=True)


# ---------------------------------------------------------------- talking to GitHub


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def live_create(method, path, params=None, body=None):
    """The sender used by `confirm` on GitHub. It sends GET, and one kind of write: POST of bytes to a repository's issues."""
    if method == "GET":
        return pv.live_send(method, path, params, body)
    if method != "POST" or not CREATE_PATH.match(path) or not isinstance(body, bytes) or params:
        raise RuntimeError("this workflow may send only GET, and POST to a repository's issues")
    request = urllib.request.Request("https://%s%s" % (pv.API_HOST, path), data=body, method="POST")
    request.add_header("Authorization", "Bearer %s" % os.environ.get("GITHUB_TOKEN"))
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("X-GitHub-Api-Version", "2022-11-28")
    request.add_header("User-Agent", "github-create-issue-skill")
    request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.build_opener(_NoRedirect).open(request, timeout=30) as response:
            return response.status, dict(response.headers), json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        text = err.read().decode("utf-8", "replace")
        try:
            answer = json.loads(text) if text.strip() else None
        except ValueError:
            answer = {"message": text[:200]}
        return err.code, dict(err.headers), answer
    # Anything else (a timeout, a dropped connection, an answer that is not JSON) is left to rise: the caller
    # treats it as an unknown outcome, because the request may have arrived.


class Writer(pv.Connection):
    """The preview skill's read-only connection, with one thing added: creating an issue, once, in one repository."""

    def __init__(self, send, **more):
        super().__init__(send, **more)
        self._repo, self.sent = None, 0

    def allow(self, repo):
        self._repo = repo

    def create(self, data):
        if self._repo is None or self.sent or not isinstance(data, bytes):
            raise Refused("a second create, or a create that was not allowed, was about to be sent, and was not")
        self.sent += 1
        path = "/repos/%s/issues" % self._repo
        try:
            status, headers, answer = self._send("POST", path, None, data)
        except Exception as problem:            # a timeout or a broken connection: the request may have arrived
            self.asked.append(("POST", path))
            raise OutcomeUnknown(type(problem).__name__)
        self.asked.append(("POST", path))
        return status, {str(name).lower(): str(value) for name, value in (headers or {}).items()}, answer


def connection(args, writer=False):
    """The connection for this command. Only `confirm` gets one that can create."""
    kind = Writer if writer else pv.Connection
    if getattr(args, "fake", None) is not None:          # a made-up GitHub handed in by a test or a recording
        return kind(args.fake.send, sleep=lambda seconds: None)
    if args.source == "fake":
        if not args.fake_store:
            raise Stop("--source fake needs --fake-store, the made-up GitHub's file")
        fake = _load("github-create-issue", "fake_github.py", "made_up_github_for_create").load(args.fake_store)
        return kind(fake.send)
    if args.fake_store:
        raise Stop("--fake-store only goes with --source fake")
    root = os.path.realpath(os.path.join(HERE, "..", "..", ".."))
    for path, what in ((args.draft, "--draft"), (args.state, "--state"), (args.results, "--results"), (link_path(args), "--link")):
        if path and os.path.commonpath([root, os.path.realpath(path)]) == root:
            raise Stop("a live run keeps its files outside this repository, because they name a real account. Give %s a path outside it" % what)
    if not os.environ.get("GITHUB_TOKEN"):
        raise Stop("the environment variable GITHUB_TOKEN is not set")
    return kind(live_create if writer else pv.live_send)


# ---------------------------------------------------------------- the local link file


def link_path(args):
    return args.link or os.path.join(os.path.dirname(os.path.abspath(args.draft)), "linked.md")


def read_link(path):
    """The local link file's fields, or None when there is none. A file that cannot be read stops everything."""
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        return None
    except (OSError, UnicodeDecodeError):
        raise Stop("the local link file %s cannot be read, so it is not known whether this draft was already created" % shown_path(path))
    try:
        front = dict((line.split(": ", 1)[0], json.loads(line.split(": ", 1)[1])) for line in text[4:text.index("\n---\n", 3)].split("\n"))
        payload = json.loads(re.search(r"\n## The payload that was sent\n\n```json\n(.*?)\n```\n", text, re.S).group(1))
    except (ValueError, IndexError, AttributeError):
        raise Stop("the local link file %s is not one this workflow wrote, so it is not known whether this draft was already created" % shown_path(path))
    if front.get("format") != LINK_FORMAT or front.get("status") not in ("creating", "unknown", "linked", "not-created"):
        raise Stop("the local link file %s is not in the format %s" % (shown_path(path), LINK_FORMAT))
    return dict(front, payload=payload)


ORDER = ("format", "status", "draft", "draft_sha256", "repository", "repository_id", "fingerprint", "payload_sha256", "confirmed_by", "account",
         "sent_at", "number", "node_id", "id", "html_url", "created_at", "linked_by", "compared_at", "compared")
STATUS_WORDS = {
    "creating": "The request to create this issue was about to be sent. If this file still says so, the outcome is NOT KNOWN: run `reconcile`.",
    "unknown": "The request was sent and no usable answer came back. The issue MAY exist on GitHub. Nothing more is sent until `reconcile` has settled it.",
    "linked": "This draft is the GitHub issue named below. It is matched to it by its node ID, not by its number alone.",
    "not-created": "The request was refused, or `reconcile` found no such issue. No issue exists for this draft. A new preview is allowed.",
}


def write_link(path, link, rows=None):
    """Write the whole local link file, or nothing. `rows` is the read-back comparison, when there is one."""
    payload = link["payload"]
    lines = ["---"] + ["%s: %s" % (key, json.dumps(link.get(key), ensure_ascii=True)) for key in ORDER] + ["---", "",
             "# Local link: %s" % link["draft"], "",
             "Written by the github-create-issue skill. It ties one local draft to one GitHub issue. Every value above is JSON.", "",
             "**Status: %s.** %s" % (link["status"], STATUS_WORDS[link["status"]]), ""]
    if link.get("number"):
        lines += ["- repository: %s, id %s" % (q(link["repository"]), link["repository_id"]), "- issue number: %d" % link["number"],
                  "- node ID, the identifier this file is matched by: `%s`" % link["node_id"], "- GitHub's id: %s" % link["id"],
                  "- created at: %s, by GitHub's clock" % link["created_at"], "- how it was linked: %s" % link["linked_by"], ""]
    lines += ["## Read back and compared", ""]
    if rows is None:
        lines += ["Not done yet.", ""]
    else:
        lines += ["After the issue was created it was read back from GitHub, at %s, and compared with the payload of the preview, field" % link["compared_at"],
                  "by field. Result: **%s**." % ("every field is the same" if link["compared"] == "same" else "NOT THE SAME"), "",
                  "| Field | In the previewed payload | Read back from GitHub | Same? |", "|---|---|---|---|"]
        lines += ["| `%s` | %s | %s | %s |" % (field, pv.q(sent).replace("|", "\\|") if field != "body" else "%d characters, SHA-256 `%s`" % (len(sent or ""), sha_text(sent)),
                                             pv.q(back).replace("|", "\\|") if field != "body" else "%d characters, SHA-256 `%s`" % (len(back or ""), sha_text(back)),
                                             "yes" if same else "**NO**") for field, sent, back, same in rows]
        lines.append("")
    lines += ["## The payload that was sent", "", "```json", json.dumps(payload, indent=1, sort_keys=True, ensure_ascii=True), "```", "",
              "The bytes sent were these fields in the preview's fixed order. Their SHA-256 is `%s`." % link["payload_sha256"], ""]
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    os.replace(path + ".tmp", path)


def sha_text(text):
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:16]


def refuse_if_linked(path):
    """The rerun guard: a draft that already has an issue, or may have one, is never created again."""
    link = read_link(path)
    if link is None or link["status"] == "not-created":
        return link
    if link["status"] == "linked":
        raise Refused("this draft is ALREADY the GitHub issue number %d of %s (node ID %s), created at %s. It is not created again. "
                      "`verify` reads it back and compares it" % (link["number"], link["repository"], link["node_id"], link["created_at"]))
    raise Refused("a create for this draft was sent at %s and its OUTCOME IS NOT KNOWN. The issue may exist on GitHub. Nothing more is sent "
                  "until `reconcile` has settled it" % link["sent_at"])


# ---------------------------------------------------------------- reading back and comparing


def read_issue(conn, repo, number):
    status, _, answer = conn.get("/repos/%s/issues/%d" % (repo, number))
    if status != 200 or not isinstance(answer, dict) or answer.get("number") != number or not isinstance(answer.get("node_id"), str):
        raise Stop("GitHub did not return issue %d (status %d)" % (number, status))
    if "pull_request" in answer or not str(answer.get("repository_url", "")).endswith("/repos/" + repo):
        raise Stop("number %d is not an issue of this repository any more" % number)
    return answer


def compare(payload, issue):
    """The created issue against the previewed payload, field by field: [(field, sent, read back, same?)]."""
    back = {"title": issue.get("title"), "body": issue.get("body"),
            "labels": sorted(row.get("name") if isinstance(row, dict) else row for row in issue.get("labels") or []),
            "assignees": sorted(row.get("login") for row in issue.get("assignees") or [] if isinstance(row, dict)),
            "milestone": issue["milestone"].get("number") if isinstance(issue.get("milestone"), dict) else None}
    sent = {"title": payload["title"], "body": payload["body"], "labels": sorted(payload.get("labels", [])),
            "assignees": sorted(payload.get("assignees", [])), "milestone": payload.get("milestone")}
    return [(field, sent[field], back[field], type(sent[field]) is type(back[field]) and sent[field] == back[field]) for field in COMPARED]


def show_compare(rows):
    for field, sent, back, same in rows:
        if field == "body":
            say("     %-10s %s: previewed %d characters, read back %d characters" % (field, "the same, character for character" if same else "DIFFERENT",
                                                                               len(sent or ""), len(back or "")))
        else:
            say("     %-10s %s: previewed %s, read back %s" % (field, "the same" if same else "DIFFERENT", q(sent), q(back)))


def append_result(args, link, rows, how):
    path = os.path.join(args.results, "create-issue.md")
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        text = "\n".join(["# Result records: issues created", "",
                          "Written by the github-create-issue skill. One section for each issue it created or linked, the newest last. Every value",
                          "that came from GitHub or from the command line is written as JSON.", ""])
    lines = ["", "## Issue %d of %s" % (link["number"], link["repository"]), "",
             "- outcome: %s" % ("CREATED, and the same as the preview" if link["compared"] == "same" else "CREATED, and NOT the same as the preview"),
             "- how it was recorded: %s" % how,
             "- repository: %s, id %s" % (q(link["repository"]), link["repository_id"]),
             "- issue number: %d" % link["number"],
             "- identifier of what was created: node ID `%s`, GitHub's id %s" % (link["node_id"], link["id"]),
             "- created at: %s, by GitHub's clock" % link["created_at"],
             "- confirmed by: %s, as typed with the fingerprint in the command that wrote. The workflow cannot check who typed it" % q(link["confirmed_by"]),
             "- the connection acted as login: %s" % q(link["account"]),
             "- preview fingerprint: %s" % link["fingerprint"],
             "- SHA-256 of the payload's bytes: %s" % link["payload_sha256"],
             "- local draft: %s. Local link: %s" % (link["draft"], os.path.basename(link_path(args))), "",
             "| Field | In the previewed payload | Read back from GitHub | Same? |", "|---|---|---|---|"]
    lines += ["| `%s` | %s | %s | %s |" % (field, "%d characters" % len(sent or "") if field == "body" else q(sent).replace("|", "\\|"),
                                         "%d characters" % len(back or "") if field == "body" else q(back).replace("|", "\\|"), "yes" if same else "**NO**")
              for field, sent, back, same in rows]
    os.makedirs(args.results, exist_ok=True)
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        f.write(text.rstrip("\n") + "\n" + "\n".join(lines) + "\n")
    os.replace(path + ".tmp", path)
    return path


def finish(args, conn, link, issue, how):
    """An issue exists for this draft: record it, read it back, compare, and write the result record."""
    link.update(status="linked", number=issue["number"], node_id=issue["node_id"], id=issue.get("id"), html_url=issue.get("html_url"),
                created_at=issue.get("created_at"), linked_by=how)
    path = link_path(args)
    try:
        write_link(path, link)
    except OSError as problem:
        say("THE ISSUE EXISTS AND COULD NOT BE RECORDED (%s). WRITE THIS DOWN: issue number %d, node ID %s, in %s"
            % (type(problem).__name__, issue["number"], issue["node_id"], link["repository"]))
        say("The local link file still says the outcome is unknown, so nothing will be created again. Fix the cause and run `reconcile`")
        return 3
    say("%s RECORDED. Issue number %d, node ID %s, was written to %s before anything else was done" % ("7." if how.startswith("created") else "3.", issue["number"], issue["node_id"], shown_path(path)))
    back = read_issue(conn, link["repository"], issue["number"])
    if back["node_id"] != issue["node_id"]:
        raise Stop("issue %d read back with another node ID than the one GitHub returned" % issue["number"])
    rows = compare(link["payload"], back)
    link.update(compared_at=conn.now, compared="same" if all(row[3] for row in rows) else "different")
    write_link(path, link, rows)
    say("%s READ BACK AND COMPARED. The issue was read back from GitHub by its number, matched by its node ID, and compared with the previewed payload:" % ("8." if how.startswith("created") else "4."))
    show_compare(rows)
    result = append_result(args, link, rows, how)
    say("%s RESULT RECORD. Written to %s. The local link is %s" % ("9." if how.startswith("created") else "5.", shown_path(result), shown_path(path)))
    if link["compared"] == "same":
        say("RESULT: DONE. Issue %d was created, recorded, read back, and is the same as the preview field for field" % issue["number"])
        return 0
    say("RESULT: NEEDS LOOKING. Issue %d exists and is recorded, and it is NOT what the preview showed: %s. Nothing was changed to fix it. "
        "Look at the issue on GitHub" % (issue["number"], ", ".join(row[0] for row in rows if not row[3])))
    return 3


# ---------------------------------------------------------------- the commands


def cmd_preview(args):
    refuse_if_linked(link_path(args))
    return pv.run(args, connection(args))


def load_preview(state, mark):
    if not FINGERPRINT.match(mark or ""):
        raise Refused("that is not the shape of a preview fingerprint")
    path = os.path.join(state, mark + ".json")
    try:
        with open(path, encoding="utf-8") as f:
            saved = json.load(f)
        record = dict(saved["record"])
    except (OSError, ValueError, KeyError, TypeError):
        raise Refused("there is no preview with the fingerprint %s. Run `preview` first" % mark)
    body = {key: value for key, value in record.items() if key != "fingerprint"}
    if hashlib.sha256(json.dumps(body, sort_keys=True).encode("utf-8")).hexdigest()[:32] != mark or record.get("fingerprint") != mark:
        raise Refused("the saved preview does not match its fingerprint. It was altered after it was made")
    return path, saved, record


def cmd_confirm(args):
    say("CONFIRM the creation of one previewed issue")
    if not args.fingerprint or not args.confirmed_by:
        raise Refused("NO CONFIRMATION was given. A write needs --fingerprint, from the preview, and --confirmed-by, the name of the person confirming")
    name = args.confirmed_by.strip()
    if not name or len(name) > 60 or any(ord(char) < 32 for char in name) or EMAIL_SHAPED.search(name):
        raise Refused("--confirmed-by must be a short plain name, and not an email address")
    draft = pv.read_draft(args.draft)
    repo = draft["repository"]
    try:
        count = pv.check_allowlist(args.allowlist, repo)
    except Stop as why:
        raise Refused(str(why))
    refuse_if_linked(link_path(args))
    path, saved, record = load_preview(args.state, args.fingerprint)
    if record["repository"] != repo or record["source"] != args.source:
        raise Refused("THE CHANGE DIFFERS FROM THE PREVIEW: the preview with this fingerprint is for another repository or source")
    if record["draft_digest"] != draft["digest"]:
        raise Refused("THE CHANGE DIFFERS FROM THE PREVIEW: the draft was changed after the preview was made. Its SHA-256 then was %s and is now %s. "
                      "A confirmation covers exactly what its preview showed. Make a new preview" % (record["draft_digest"][:16], draft["digest"][:16]))
    data = pv.payload_bytes(record["payload"])
    if hashlib.sha256(data).hexdigest() != record["payload_sha256"]:
        raise Refused("the saved payload does not give the bytes the preview showed. It was altered after the preview was made")
    if saved.get("status") != "ready":
        raise Refused("this preview was ALREADY USED, at %s by GitHub's clock, confirmed by %s. A preview can be confirmed once" % (saved.get("used_at"), q(saved.get("confirmed_by"))))
    say("1. CONFIRMATION. Given by %s, for the preview with fingerprint %s, in this same command" % (q(name), args.fingerprint))
    say("     The name is recorded as it was typed. This workflow cannot check who typed it")
    say("2. ALLOWLIST. The repository %s is on the sandbox allowlist, which names %s" % (q(repo), plural(count, "repository", "repositories")))
    say("3. THE DRAFT is the draft of the preview: its SHA-256 is the same, %s. The saved payload gives the bytes the preview showed: %d bytes, SHA-256 %s"
        % (draft["digest"][:16], len(data), record["payload_sha256"]))

    conn = connection(args, writer=True)
    status, _, account = conn.get("/user")
    status_repo, _, about = conn.get("/repos/%s" % repo)
    if status != 200 or status_repo != 200 or not isinstance(account, dict) or not isinstance(about, dict):
        raise Stop("GitHub did not return the account or the repository (status %d and %d)" % (status, status_repo))
    if account.get("login") != record["account"] or about.get("id") != record["repository_id"] or about.get("full_name") != repo:
        raise Refused("the account or the repository is not the one of the preview. Make a new preview")
    age = (pv.datetime.datetime.strptime(conn.now, pv.STAMP) - pv.datetime.datetime.strptime(record["created"], pv.STAMP)).total_seconds() / 60.0
    if age > record["limit_minutes"] or age < -1:
        raise Refused("THE PREVIEW HAS EXPIRED. It was made at %s and it is now %s by GitHub's clock: %s, and the limit is %d. Make a new preview"
                      % (record["created"], conn.now, plural(round(age), "minute"), record["limit_minutes"]))
    say("4. AGE. The preview was made at %s and it is now %s by GitHub's clock: %s. The limit is %d" % (record["created"], conn.now, plural(round(age), "minute"), record["limit_minutes"]))
    labels = {str(row.get("name")) for row in pv.read_all(conn, "/repos/%s/labels" % repo, {}, "the repository's labels")}
    gone = [one for one in record["payload"].get("labels", []) if one not in labels]
    milestones = pv.read_all(conn, "/repos/%s/milestones" % repo, {"state": "open"}, "the repository's milestones")
    if gone or ("milestone" in record["payload"] and record["payload"]["milestone"] not in [row.get("number") for row in milestones]):
        raise Refused("the repository changed after the preview: %s. Make a new preview" % ("the label %s is gone" % q(gone[0]) if gone else "the milestone is gone or closed"))
    recent = pv.read_all(conn, "/repos/%s/issues" % repo, {"state": "all", "since": record["created"]}, "the repository's recent issues")
    twins = [row.get("number") for row in recent if "pull_request" not in row and row.get("title") == record["payload"]["title"]
             and str(row.get("created_at", "")) >= record["created"]]
    if twins:
        raise Refused("an issue with exactly this title was created in the repository AFTER the preview: number %s. Creating another would make a "
                      "duplicate. Look at it, then make a new preview" % ", ".join(str(one) for one in twins))
    say("5. STILL TRUE. The labels and milestone of the payload still exist, and no issue with this title was created since the preview")

    link = {"format": LINK_FORMAT, "status": "creating", "draft": os.path.basename(args.draft), "draft_sha256": draft["digest"], "repository": repo,
            "repository_id": record["repository_id"], "fingerprint": args.fingerprint, "payload_sha256": record["payload_sha256"], "confirmed_by": name,
            "account": record["account"], "sent_at": conn.now, "payload": record["payload"]}
    write_link(link_path(args), link)                     # the intent is on disk before anything is sent
    saved.update(status="used", used_at=conn.now, confirmed_by=name)
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        json.dump(saved, f, indent=1, sort_keys=True)
    os.replace(path + ".tmp", path)                       # and the preview is spent
    conn.allow(repo)
    say("6. WRITING. The local link %s now says a create is about to be sent. Then one request: POST /repos/%s/issues, the %d bytes of the preview"
        % (shown_path(link_path(args)), repo, len(data)))
    try:
        status, _, issue = conn.create(data)
    except OutcomeUnknown as problem:
        write_link(link_path(args), dict(link, status="unknown"))
        say("     NO ANSWER CAME BACK (%s). The request was sent and may have arrived" % problem)
        say("RESULT: OUTCOME UNKNOWN. The issue MAY exist on GitHub. It was NOT sent again, and it will not be: the local link says the outcome is "
            "unknown, and every run refuses until `reconcile` has looked on GitHub and settled it")
        return 3
    if status != 201 or not isinstance(issue, dict) or not isinstance(issue.get("number"), int) or not isinstance(issue.get("node_id"), str):
        if 400 <= status < 500:
            write_link(link_path(args), dict(link, status="not-created"))
            say("     -> status %d. GITHUB REFUSED THE CREATE. A refusal of this kind means no issue was made" % status)
            say("RESULT: NOT DONE. No issue was created. The local link says so, and the preview is spent: make a new one once the cause is fixed")
            return 1
        write_link(link_path(args), dict(link, status="unknown"))
        say("     -> status %d, with no issue in the answer. GitHub may have created it all the same" % status)
        say("RESULT: OUTCOME UNKNOWN. The issue MAY exist on GitHub. It was NOT sent again. Run `reconcile`")
        return 3
    say("     -> status 201. GitHub created issue number %d, node ID %s" % (issue["number"], issue["node_id"]))
    code = finish(args, conn, link, issue, "created by this workflow, and recorded from GitHub's answer")
    say("     Requests made by this command: %d. Writes: %d, the one create" % (len(conn.asked), conn.sent))
    return code


def linked_or_stop(args):
    link = read_link(link_path(args))
    if link is None:
        raise Stop("there is no local link file %s, so this draft has no issue" % shown_path(link_path(args)))
    try:
        pv.check_allowlist(args.allowlist, link["repository"])
    except Stop as why:
        raise Refused(str(why))
    return link


def cmd_verify(args):
    say("VERIFY that the linked issue is still what the preview showed. This command only reads")
    link = linked_or_stop(args)
    if link["status"] != "linked":
        raise Stop("the local link's status is %s, not linked. %s" % (q(link["status"]), STATUS_WORDS[link["status"]]))
    conn = connection(args)
    issue = read_issue(conn, link["repository"], link["number"])
    say("1. THE LOCAL LINK says: issue number %d of %s, node ID %s" % (link["number"], q(link["repository"]), link["node_id"]))
    if issue["node_id"] != link["node_id"]:
        say("2. MATCHED BY IDENTIFIER? NO. Number %d on GitHub now has the node ID %s. It is NOT the issue this file was linked to" % (link["number"], issue["node_id"]))
        say("RESULT: NOT THE SAME ISSUE. Nothing was changed. A person must look")
        return 3
    say("2. MATCHED BY IDENTIFIER. GitHub's issue number %d has the same node ID as the local link" % link["number"])
    rows = compare(link["payload"], issue)
    say("3. COMPARED with the payload of the preview, field by field:")
    show_compare(rows)
    say("     Requests made by this command: %d, every one a GET. Nothing was written, on GitHub or locally" % len(conn.asked))
    if all(row[3] for row in rows):
        say("RESULT: THE SAME. The issue on GitHub is the previewed payload, field for field")
        return 0
    say("RESULT: DIFFERENT in %s. The issue was changed on GitHub after it was created, or was never what the preview showed. Nothing was changed to fix it"
        % ", ".join(row[0] for row in rows if not row[3]))
    return 3


def cmd_reconcile(args):
    say("RECONCILE a create whose outcome is not known. This command only reads GitHub")
    link = linked_or_stop(args)
    if link["status"] not in ("creating", "unknown"):
        raise Stop("there is nothing to reconcile: the local link's status is %s" % q(link["status"]))
    conn = connection(args)
    status, _, account = conn.get("/user")
    if status != 200 or not isinstance(account, dict) or account.get("login") != link["account"]:
        raise Stop("the connection does not act as the account that sent the create")
    stamp = lambda text: pv.datetime.datetime.strptime(text, pv.STAMP)
    since = (stamp(link["sent_at"]) - pv.datetime.timedelta(seconds=MARGIN_SECONDS)).strftime(pv.STAMP)
    rows = pv.read_all(conn, "/repos/%s/issues" % link["repository"], {"state": "all", "creator": link["account"], "since": since}, "the account's recent issues")
    found = [row for row in rows if "pull_request" not in row and row.get("title") == link["payload"]["title"] and row.get("body") == link["payload"]["body"]
             and str(row.get("created_at", "")) >= since and isinstance(row.get("node_id"), str)]
    say("1. THE LOCAL LINK says a create was sent at %s by GitHub's clock, and its outcome is not known" % link["sent_at"])
    say("2. LOOKED ON GITHUB for issues made by %s since %s with exactly the previewed title and body. Found: %d%s"
        % (q(link["account"]), since, len(found), " (numbers %s)" % ", ".join(str(row["number"]) for row in found) if found else ""))
    if args.number:
        found = [row for row in found if row["number"] == args.number]
        if not found:
            raise Refused("issue %d is not one of the issues that match this create" % args.number)
    if len(found) > 1:
        say("RESULT: MORE THAN ONE. %d issues match, so the create was sent more than once, or someone filed the same text. Nothing was linked. "
            "A person closes the extra ones on GitHub, then runs `reconcile --number N` to link the one to keep" % len(found))
        return 3
    if not found:
        waited = (stamp(conn.now) - stamp(link["sent_at"])).total_seconds()
        if waited < SETTLE_SECONDS:
            say("RESULT: NOT SETTLED YET. No such issue is listed, and the create was sent only %d seconds ago. GitHub's list can lag. "
                "Nothing was changed. Run `reconcile` again in a minute" % waited)
            return 3
        write_link(link_path(args), dict(link, status="not-created"))
        say("RESULT: NOT CREATED. GitHub lists no such issue, %d seconds after the create was sent. The local link now says so, and a new preview is allowed"
            % waited)
        return 0
    return finish(args, conn, link, found[0], "found on GitHub by `reconcile`, by its title, body, author and time, after the create's answer was lost")


def run(args):
    try:
        return {"preview": cmd_preview, "confirm": cmd_confirm, "verify": cmd_verify, "reconcile": cmd_reconcile}[args.command](args)
    except Refused as why:
        say("REFUSED: %s." % why)
    except Stop as why:
        say("STOPPED: %s." % why)
    except RateLimited:
        say("INCOMPLETE: GitHub rate-limited this run before anything was sent. Run it again later.")
        return 2
    say("Nothing was sent to GitHub by this command that could change anything.")
    return 1


def main(argv=None):
    parser = argparse.ArgumentParser(description="Create one previewed GitHub issue after a person confirms, and tie the local file to it.")
    parser.add_argument("command", choices=("preview", "confirm", "verify", "reconcile"))
    parser.add_argument("--source", choices=("live", "fake"), required=True)
    parser.add_argument("--draft", required=True)
    parser.add_argument("--allowlist", required=True)
    parser.add_argument("--index", help="preview: the local index of issue records, for the duplicate search")
    parser.add_argument("--state", help="the folder where a READY preview is kept until it is confirmed")
    parser.add_argument("--link", help="the local link file (default: linked.md beside the draft)")
    parser.add_argument("--results", help="the folder for the result record")
    parser.add_argument("--fingerprint", help="confirm: the fingerprint the preview printed")
    parser.add_argument("--confirmed-by", help="confirm: the name of the person confirming")
    parser.add_argument("--despite-duplicate", action="append", metavar="OWNER/NAME#N", help="preview: a person's decision to go on despite this likely duplicate")
    parser.add_argument("--payload-out", help="preview: write the payload, field by field, to this file")
    parser.add_argument("--number", type=int, help="reconcile: the one issue to link, when several match")
    parser.add_argument("--fake-store", help="with --source fake: the made-up GitHub's file")
    args = parser.parse_args(argv)
    if args.source == "fake":
        args.results = args.results or os.path.join(HERE, "..", "..", "context", "github", "results")
    elif args.command in ("confirm", "reconcile") and not args.results:
        say("REFUSED: a live %s needs --results, a folder outside this repository for the result record." % args.command)
        return 1
    if args.command in ("preview", "confirm") and not args.state:
        say("REFUSED: %s needs --state, the folder where the preview is kept." % args.command)
        return 1
    if args.command == "preview" and not args.index:
        say("REFUSED: preview needs --index, the local index for the duplicate search.")
        return 1
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
