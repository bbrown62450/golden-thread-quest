#!/usr/bin/env python3
"""Creates one subtask under one existing Jira story: preview first, then a person confirms.

    subtask.py preview --source live|fake --change CHANGE.json --allowlist FILE --state DIR
    subtask.py confirm --source live|fake --change CHANGE.json --allowlist FILE --state DIR \
                       --fingerprint CODE --confirmed-by NAME
    subtask.py check   --source live|fake --state DIR --fingerprint CODE

A change file names the parent and gives the subtask's title:

    {"parent": "SAND-1", "summary": "Write the export query"}

THE PARENT IS CHOSEN BY ITS IDENTIFIER, never by its title. "parent" is the story's key or its issue id. The preview
asks Jira for that one issue and shows its key, its issue id, its type, its status and its title. The fingerprint is
tied to the issue id, which does not change when a story is moved or renamed. A confirmation reads the parent by that
id, and is refused if the reference in the change file now leads to another issue. There is no search by title
anywhere in this file.

Refused before any preview is shown:
    a parent Jira does not return (it does not exist, or this identity may not see it: Jira gives one answer);
    a parent that is itself a subtask;
    a parent that is closed: its status is in Jira's "done" category. Reopen it in Jira first. There is no override;
    a parent in a project that is not on the sandbox allowlist.

What is sent, and nothing else: the project, the parent, the project's subtask issue type and the title. No
description, assignee or estimate.

    The title is one line of at most 200 characters. It is refused if it is empty, begins or ends with a space, has
    a tab or a character that cannot be seen, or looks as if it holds a secret. See SECRETS below.
    It is NOT refused for looking private. Email addresses, telephone numbers, web addresses, @names and words such
    as "confidential" are pointed out in the preview, for the person confirming to judge.

preview   reads Jira and writes nothing. It has no way to send a write.
          If the parent already has a subtask with the same title (capitals and spacing aside), whoever made it,
          no fingerprint is issued: there is nothing to add.

confirm   creates the subtask of one preview, named by its fingerprint, and only if all of this holds at that moment:
            a fingerprint and the confirming person's name are given;
            the saved preview is unaltered, unused and at most 15 minutes old;
            the change file still asks for exactly what the preview showed;
            the project is on the sandbox allowlist, for this Jira site;
            the parent is still not a subtask and not closed, and Jira still says this identity may create issues;
            the parent's subtasks, read again just before the write, still hold none with this title.
          After the write the new subtask is read back by its issue id, and its parent is compared with the
          parent intended.

check     reads the subtask back after a write and compares its parent with the parent intended. It writes nothing.

The allowlist is a JSON file listing projects by Jira's project id together with a fingerprint of the site's
address, because project ids repeat from site to site.

What this cannot do. Jira's request to create an issue has no "only if there is none like it" condition. Between the
last read and the write there is a moment in which a second run could create the same subtask. The duplicate check
before the write, and the count after it, report that case. Only the answers 400, 401, 403 and 404, with the
parent's subtasks read back unchanged, are reported as "nothing was written". Any other failed answer ends with
"A PERSON NEEDS TO LOOK", because Jira may still be creating the subtask. The duplicate check sees the subtasks this identity can
see. It compares titles under ONE parent: the same title under another story is not a duplicate.

A write is sent once and never retried.

--pretend-minutes-later N is for tests: it moves "now" forward by N minutes.
--log FILE saves the output with the site's address replaced by a marker, and the parent's title left out.
--result FILE saves the result record of a write as Markdown, the same way.

Nothing in the parent's title, or in the titles of its subtasks, is acted on. The parent's title is shown on screen,
marked as other people's text, so that a person can see which story this is. It is not saved.

For a live run the connection comes from the environment variables JIRA_BASE_URL, JIRA_EMAIL and JIRA_API_TOKEN. None
is stored. The output is searched for the token, the email address and their encoded form before it is shown.

Exit codes: 0 done; 1 refused or not found, nothing written; 2 a write was sent and its result needs a person to look.
"""
import argparse
import base64
import datetime
import hashlib
import http.client
import json
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

LIMIT_MINUTES = 15
MAX_SUMMARY = 200
REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,60}")
TIME_FORMAT = "%Y-%m-%d %H:%M:%S UTC"
SITE_MARK = "[site address removed]"
ISSUE_FIELDS = "summary,status,issuetype,project,parent,subtasks,updated"
REFUSALS = (400, 401, 403, 404)   # answers that mean Jira did not take the write. Any other failure is not taken to mean that
UNSEEN = re.compile("[\\x00-\\x09\\x0b-\\x1f\\x7f-\\xa0\\u00ad\\u034f\\u061c\\u115f\\u1160\\u200b-\\u200f\\u2028\\u2029\\u202a-\\u202e\\u2060-\\u2069\\u2800\\u3164\\ufeff\\U000e0000-\\U000e007f]")


# SECRETS. A title that matches one of these is refused. They are patterns, so they miss secrets of other
# shapes and can refuse text that is not a secret. The person confirming still has to read the title.
SECRETS = (
    ("an AWS access key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("a private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY")),
    ("a GitHub token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})")),
    ("a Slack token", re.compile(r"\bx(?:ox[abeprs]|app)-[A-Za-z0-9-]{10,}")),
    ("an Atlassian API token", re.compile(r"\bATATT3[A-Za-z0-9_=-]{20,}")),
    ("a JSON web token", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}")),
    ("a web address with a password in it", re.compile(r"://[^/\s:@]+:[^/\s@]+@")),
    ("a password, key or token written out", re.compile(
        r"(?i)(?:pass ?word|passwd|passphrase|pwd|secret|api[ _-]?key|token)[a-z_]{0,12}\s*[:=]\s*\S{4,}"
        r"|\b(?:pass ?word|passwd|passphrase|pwd|pw)\b(?: for(?: \S+){1,4})? is:?\s+\S{4,}")),
    ("a long run of letters and digits, as a key is", re.compile(r"(?<![A-Za-z0-9+/_-])(?=[A-Za-z0-9+/_-]*[0-9])(?=[A-Za-z0-9+/_-]*[A-Za-z])[A-Za-z0-9+/_-]{32,}")),
)


# POINTED OUT, and not refused. Each is something a person should look at before creating an issue others will see.
PRIVATE = (
    ("an email address", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z0-9.-]+")),
    ("a web address", re.compile(r"(?i)\b(?:https?://|www\.)\S+")),
    ("what may be a telephone number", re.compile(r"(?<![0-9])\+?[0-9][0-9 ().-]{7,}[0-9](?![0-9])")),
    ("an @name, which is sent as text and mentions nobody", re.compile(r"(?<![A-Za-z0-9._%+-])@[A-Za-z0-9_.-]+")),
    ("a word that marks something as private", re.compile(r"(?i)\b(?:confidential|private|internal only|do not share|not for customers?|under nda)\b")),
)


LINES = []   # each is (what is shown on screen, what is saved)


class Refused(Exception):
    """Nothing was written. The message is the reason."""


class NotWritten(Refused):
    """A write was sent, and reading Jira afterwards shows that nothing was written."""


class NeedsLooking(Exception):
    """A write was sent. The message says what is and is not known."""


def say(text="", saved=None):
    LINES.append((text, text if saved is None else saved))


def quoted(text, limit=60):
    """Other people's text, made safe to show: quoted, cut short, with unseen characters replaced."""
    return json.dumps(UNSEEN.sub("?", str(text))[:limit], ensure_ascii=False)


# ---------------------------------------------------------------- the connection


class Connection:
    """Every request goes through here and is written down. A preview and a check are given no way to write."""

    def __init__(self, get, post, host):
        self._get, self._post, self.host = get, post, host
        self.sent = []

    def get(self, path, params=None):
        self.sent.append(("GET", path))
        try:
            return self._get(path, params)
        except (OSError, TimeoutError) as err:
            reason = "could not reach Jira (%s)" % type(getattr(err, "reason", err)).__name__
            if any(method == "POST" for method, _ in self.sent):
                raise NeedsLooking("after the write was sent, a read failed: %s" % reason)
            raise Refused(reason)

    def post_subtask(self, project_id, parent_id, type_id, summary):
        if self._post is None:
            raise Refused("this command has no way to write")
        if not (ident(project_id) and ident(parent_id) and ident(type_id)):
            raise Refused("a write names the project, the parent and the issue type by their ids")
        body = {"fields": {"project": {"id": project_id}, "parent": {"id": parent_id}, "issuetype": {"id": type_id}, "summary": summary}}
        self.sent.append(("POST", WRITE_PATH))
        try:
            return self._post(WRITE_PATH, None, body)
        except (OSError, TimeoutError) as err:
            raise NeedsLooking("the write was sent and no answer came back (%s). It is NOT KNOWN whether Jira created "
                               "the subtask. It was not sent again" % type(getattr(err, "reason", err)).__name__)


WRITE_PATH = "/rest/api/3/issue"

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def make_live(may_write):
    base = os.environ.get("JIRA_BASE_URL", "").rstrip("/")
    email, token = os.environ.get("JIRA_EMAIL", ""), os.environ.get("JIRA_API_TOKEN", "")
    for name, value in (("JIRA_BASE_URL", base), ("JIRA_EMAIL", email), ("JIRA_API_TOKEN", token)):
        if not value:
            raise Refused("the environment variable %s is not set" % name)
    if not base.startswith("https://"):
        raise Refused("JIRA_BASE_URL must start with https://")
    parsed_base = urllib.parse.urlparse(base)
    host = parsed_base.hostname or ""
    if not host or base != "https://" + host:
        raise Refused("JIRA_BASE_URL must be https:// and the site's name, with no port, path or sign-in in it")
    encoded = base64.b64encode(("%s:%s" % (email, token)).encode("utf-8")).decode("ascii")
    opener = urllib.request.build_opener(NoRedirect)

    def send(method, path, params, body):
        url = base + path + ("?" + urllib.parse.urlencode(params) if params else "")
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = urllib.request.Request(url, data=data, method=method)
        request.add_header("Authorization", "Basic " + encoded)
        request.add_header("Accept", "application/json")
        if data is not None:
            request.add_header("Content-Type", "application/json")
        try:
            with opener.open(request, timeout=30) as response:
                status, headers, raw = response.status, dict(response.headers), response.read()
        except urllib.error.HTTPError as err:
            status, headers, raw = err.code, dict(err.headers), err.read()
        except http.client.HTTPException as err:
            raise OSError(type(err).__name__)
        try:
            parsed = json.loads(raw.decode("utf-8")) if raw.strip() else {}
        except ValueError:
            parsed = {}
        return status, headers, parsed if isinstance(parsed, dict) else {}

    def get(path, params=None):
        return send("GET", path, params, None)

    def post(path, params, body):
        fields = body.get("fields") if isinstance(body, dict) else None
        if path != WRITE_PATH or params or set(body) != {"fields"} or not isinstance(fields, dict) or set(fields) != {"project", "parent", "issuetype", "summary"}:
            raise Refused("the only write this workflow sends is one new subtask: a project, a parent, an issue type and a title")
        return send("POST", path, params, body)

    return Connection(get, post if may_write else None, host), [token, email, encoded]


def site_fingerprint(host):
    return hashlib.sha256(host.lower().encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------- the title of the subtask


def check_summary(text):
    """Refuses a title this workflow will not send. Returns what to point out to the person confirming."""
    if not isinstance(text, str) or not text:
        raise Refused("the summary, which is the subtask's title, is empty")
    if "\n" in text or "\r" in text:
        raise Refused("the summary must be one line")
    if len(text) > MAX_SUMMARY:
        raise Refused("the summary is %d characters long and the limit is %d" % (len(text), MAX_SUMMARY))
    if text != text.strip():
        raise Refused("the summary begins or ends with a space")
    if UNSEEN.search(text):
        raise Refused("the summary has a tab or a character that cannot be seen")
    for what, pattern in SECRETS:
        if pattern.search(text):
            raise Refused("the summary looks as if it holds %s. A created issue cannot be unsent, so this workflow "
                          "does not send it. The matching text is not shown here" % what)
    return [what for what, pattern in PRIVATE if pattern.search(text)]


def same_title(a, b):
    """Two titles are the same if they differ only in capitals, in spacing, or in how the same letters are encoded."""
    plain = lambda text: " ".join(unicodedata.normalize("NFKC", text).split()).casefold()  # noqa: E731
    return isinstance(a, str) and isinstance(b, str) and plain(a) == plain(b)


# ---------------------------------------------------------------- reading the local files

def no_repeats(pairs):
    names = [name for name, _ in pairs]
    for name in names:
        if names.count(name) > 1:
            raise Refused("the file gives the name %s twice in one place" % json.dumps(name)[:60])
    return dict(pairs)


def read_json(path, what):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f, object_pairs_hook=no_repeats)
    except FileNotFoundError:
        raise Refused("there is no %s at the path given" % what)
    except (ValueError, UnicodeDecodeError):
        raise Refused("the %s is not JSON" % what)


def load_allowlist(path):
    data = read_json(path, "sandbox allowlist")
    entries = data.get("sandbox_projects") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        raise Refused("the sandbox allowlist must hold a list named sandbox_projects")
    allowed = set()
    for entry in entries:
        site, project = (entry or {}).get("site_fingerprint"), (entry or {}).get("project_id")
        if not (isinstance(site, str) and re.fullmatch(r"[0-9a-f]{16}", site)
                and isinstance(project, str) and project.isascii() and project.isdigit()):
            raise Refused("an entry in the sandbox allowlist is not a site fingerprint and a project id")
        allowed.add((site, project))
    return allowed


def read_change(path):
    """The parent and the title wanted, checked. Returns a dict."""
    change = read_json(path, "change file")
    if not isinstance(change, dict) or set(change) != {"parent", "summary"}:
        raise Refused("the change file must have exactly 'parent' and 'summary'")
    ref, summary = change["parent"], change["summary"]
    if not isinstance(ref, str) or not REF.fullmatch(ref):
        raise Refused("the parent is given by its key or its issue id: letters, digits and dashes only. A title is not accepted")
    pointed_out = check_summary(summary)
    with open(path, "rb") as f:
        sha = hashlib.sha256(f.read()).hexdigest()
    return {"ref": ref, "summary": summary, "source": os.path.basename(path), "source_sha": sha, "pointed_out": pointed_out}


# ---------------------------------------------------------------- reading Jira

def ident(value):
    return isinstance(value, str) and value.isascii() and value.isdigit() and len(value) <= 20


def read_issue(conn, ref, what="the parent"):
    status, _, issue = conn.get("/rest/api/3/issue/%s" % ref, {"fields": ISSUE_FIELDS})
    if status == 401:
        raise Refused("Jira rejected the credentials (401). Check JIRA_EMAIL and JIRA_API_TOKEN")
    if status == 404:
        raise Refused("Jira answered 404 for %s. It does not exist, or this identity is not permitted to see it. "
                      "Jira gives one answer for both" % what)
    fields = issue.get("fields") if isinstance(issue, dict) else None
    project = fields.get("project") if isinstance(fields, dict) else None
    kind = fields.get("issuetype") if isinstance(fields, dict) else None
    ok = (status == 200 and isinstance(project, dict) and isinstance(kind, dict) and ident(issue.get("id")) and ident(project.get("id"))
          and isinstance(issue.get("key"), str) and REF.fullmatch(issue["key"])
          and isinstance(project.get("key"), str) and REF.fullmatch(project["key"])
          and ident(kind.get("id")) and isinstance(kind.get("subtask"), bool))
    if not ok:
        raise Refused("Jira's answer for %s could not be used (status %d)" % (what, status))
    return issue


def status_of(issue):
    """(the status's name, its category: "new", "indeterminate" or "done"). Refuses if Jira did not give the category."""
    status = issue["fields"].get("status")
    category = (status.get("statusCategory") or {}).get("key") if isinstance(status, dict) else None
    if not isinstance(category, str) or not re.fullmatch(r"[a-z_]{1,30}", category):
        raise Refused("Jira did not say which category the parent's status is in, so it is not known whether the parent is closed")
    return str(status.get("name", "?")), category


def parent_checks(issue):
    """Criterion 2, and the closed parent. Each refusal is made before any preview is shown."""
    where = "%s (issue id %s)" % (issue["key"], issue["id"])
    if issue["fields"]["issuetype"]["subtask"]:
        raise Refused("the parent named, %s, is itself a subtask: its issue type is %s. A subtask cannot be the parent of "
                      "a subtask. Name the story" % (where, quoted(issue["fields"]["issuetype"].get("name", "?"))))
    name, category = status_of(issue)
    if category == "done":
        raise Refused("the parent named, %s, is closed: its status is %s, which is in Jira's \"done\" category. This workflow "
                      "does not add work to a closed story. If the work is real, reopen the story in Jira first, and "
                      "preview again" % (where, quoted(name)))


def read_permissions(conn, issue_id):
    names = ("BROWSE_PROJECTS", "CREATE_ISSUES")
    status, _, body = conn.get("/rest/api/3/mypermissions", {"issueId": issue_id, "permissions": ",".join(names)})
    found = body.get("permissions") if status == 200 else None
    if not isinstance(found, dict):
        raise Refused("Jira did not answer the permission check (status %d), so nothing is assumed" % status)
    return {name: (found.get(name) or {}).get("havePermission") is True for name in names}


def read_subtask_type(conn, project_id):
    """The project's one subtask issue type. Refuses if it has none, or more than one."""
    status, _, body = conn.get("/rest/api/3/project/%s" % project_id)
    types = body.get("issueTypes") if status == 200 else None
    if not isinstance(types, list):
        raise Refused("Jira did not list the project's issue types (status %d), so the subtask type is not known" % status)
    found = [t for t in types if isinstance(t, dict) and t.get("subtask") is True and ident(t.get("id"))]
    if not found:
        raise Refused("the project has no subtask issue type, so a subtask cannot be created in it")
    if len(found) > 1:
        raise Refused("the project has %d subtask issue types (%s). This workflow does not choose between them"
                      % (len(found), ", ".join(quoted(t.get("name", "?"), 40) for t in found)))
    return {"id": found[0]["id"], "name": str(found[0].get("name", "?"))[:60]}


def children_of(issue):
    """The parent's subtasks as Jira lists them: [{"id", "key", "summary"}]. Refuses if Jira gave no list."""
    listed = issue["fields"].get("subtasks")
    if not isinstance(listed, list):
        raise Refused("Jira did not list the parent's subtasks, so the duplicate check cannot be made")
    children = []
    for child in listed:
        if not isinstance(child, dict) or not ident(child.get("id")):
            raise Refused("Jira's list of the parent's subtasks could not be read, so the duplicate check cannot be made")
        summary = (child.get("fields") or {}).get("summary")
        children.append({"id": child["id"], "key": str(child.get("key", "?"))[:60], "summary": summary if isinstance(summary, str) else ""})
    return children


def canonical(data):
    return json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def snapshot(issue):
    """One short code for what Jira returned of the parent: its last-updated time, project, type and status, and the
    id and title of every subtask."""
    fields = issue["fields"]
    text = canonical({"id": issue["id"], "key": issue["key"], "updated": fields.get("updated"), "project": fields["project"].get("id"),
                      "type": fields["issuetype"].get("id"), "status": (fields.get("status") or {}).get("id"),
                      "subtasks": [[c["id"], c["summary"]] for c in children_of(issue)]})
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------- what the change is

def allowlist_note(path, allowed):
    with open(path, "rb") as f:
        sha = hashlib.sha256(f.read()).hexdigest()
    return "the file %s, sha256 %s, which lists %d project%s" % (os.path.basename(path), sha[:16], len(allowed), "" if len(allowed) == 1 else "s")


def check_allowlist(site, allowed, issue, allowlist_path):
    """Criterion 6: the parent's project must be on the allowlist, for this site."""
    project = issue["fields"]["project"]
    if (site, project["id"]) not in allowed:
        raise Refused("project %s (project id %s) on the Jira site with fingerprint %s is not on the sandbox "
                      "allowlist (%s). This workflow writes only to projects listed there"
                      % (project["key"], project["id"], site, os.path.basename(allowlist_path)))


def build_proposal(site, allowed, allowlist_path, issue, permissions, subtype, change):
    """The one place that decides what a change means. The preview shows its result; confirm compares with it."""
    check_allowlist(site, allowed, issue, allowlist_path)
    parent_checks(issue)
    if not permissions["BROWSE_PROJECTS"] or not permissions["CREATE_ISSUES"]:
        raise Refused("Jira says this identity may not create issues in this project (CREATE_ISSUES: %s)"
                      % ("yes" if permissions["CREATE_ISSUES"] else "no"))
    project = issue["fields"]["project"]
    children = children_of(issue)
    name, category = status_of(issue)
    return {"site": site, "ref": change["ref"], "parent_id": issue["id"], "parent_key": issue["key"],
            "parent_type": str(issue["fields"]["issuetype"].get("name", "?"))[:60], "parent_status": name[:60], "parent_category": category,
            "project_id": project["id"], "project_key": project["key"], "subtask_type": subtype,
            "summary": change["summary"], "summary_sha": hashlib.sha256(change["summary"].encode("utf-8")).hexdigest(),
            "source": change["source"], "source_sha": change["source_sha"],
            "allowlist": allowlist_note(allowlist_path, allowed), "permissions": permissions, "children": len(children),
            "same": [{"id": c["id"], "key": c["key"]} for c in children if same_title(c["summary"], change["summary"])]}


def fingerprint_of(proposal, made_at):
    return hashlib.sha256(canonical({"proposal": proposal, "made_at": made_at}).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------- showing


def head(conn, proposal):
    say("Jira site:  https://%s  (site fingerprint %s)" % (conn.host, proposal["site"]))
    say("Project:    %s (project id %s). On the sandbox allowlist: yes." % (proposal["project_key"], proposal["project_id"]))
    say("            The allowlist is %s." % proposal["allowlist"])
    say("Parent:     %s (issue id %s). The issue id is what identifies it, and what the fingerprint is tied to." % (proposal["parent_key"], proposal["parent_id"]))


def requests_line(conn):
    kinds = sorted(set(method for method, _ in conn.sent))
    say("Requests sent to Jira: %d. %s" % (len(conn.sent), "Every one was a GET, which reads and cannot change anything."
                                           if kinds == ["GET"] else "Kinds: %s." % ", ".join(kinds)))
    for method, path in conn.sent:
        say("  %s %s" % (method, path))


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0, tzinfo=None)


def save_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write("\n")
    os.replace(tmp, path)


# ---------------------------------------------------------------- preview


def cmd_preview(args, conn):
    change = read_change(args.change)
    allowed = load_allowlist(args.allowlist)
    site = site_fingerprint(conn.host)
    issue = read_issue(conn, change["ref"])          # a parent Jira does not return is refused here
    check_allowlist(site, allowed, issue, args.allowlist)
    parent_checks(issue)                             # a parent that is a subtask, or closed, is refused here
    permissions = read_permissions(conn, issue["id"])
    subtype = read_subtask_type(conn, issue["fields"]["project"]["id"])
    before = snapshot(issue)
    proposal = build_proposal(site, allowed, args.allowlist, issue, permissions, subtype, change)
    after = snapshot(read_issue(conn, issue["id"]))
    if after != before:
        raise Refused("the parent or its subtasks changed in Jira while the preview was being made. Preview again")
    there = proposal["same"]
    title = issue["fields"].get("summary")
    title = UNSEEN.sub("?", title)[:120] if isinstance(title, str) else "(Jira gave no title)"

    say("NOTHING TO ADD. Nothing has been written." if there else "PREVIEW. Nothing has been written.")
    say("")
    head(conn, proposal)
    say("            It was found by the reference in the change file, %s, and by nothing else. Not by its title." % json.dumps(proposal["ref"]))
    say("            Its type: %s. Not a subtask: ok. Whether it is a story is for you to judge from that name." % quoted(proposal["parent_type"]))
    say("            Its status: %s, in Jira's category \"%s\". Not closed: ok." % (quoted(proposal["parent_status"]), proposal["parent_category"]))
    say("            Its title, between the bars, for you to check that this is the story you mean. It is other")
    say("            people's text: shown, and not acted on. Two stories can have one title. On one site, a key or an id is one issue.")
    say("    | %s" % title, "    | [the parent's title was shown on screen and is not saved: %d characters]" % len(title))
    say("")
    say("%s: one new issue, a subtask of %s." % ("The change asked for" if there else "The change that would be made", proposal["parent_key"]))
    say("  Sent to Jira, and nothing else:")
    say("    project     project id %s (%s)" % (proposal["project_id"], proposal["project_key"]))
    say("    parent      issue id %s (%s)" % (proposal["parent_id"], proposal["parent_key"]))
    say("    issue type  %s (issue type id %s), the project's one subtask type" % (quoted(proposal["subtask_type"]["name"]), proposal["subtask_type"]["id"]))
    say("    summary     the title, exactly as it would be sent, between the bars. %d character%s:" % (len(proposal["summary"]), "" if len(proposal["summary"]) == 1 else "s"))
    say("    | %s" % proposal["summary"])
    say("  No description, assignee, estimate or other field is sent. Jira fills in its own defaults. Its reporter would")
    say("  be the Jira account the API token belongs to, and not the name given with the confirmation.")
    say("  Where the title came from: the change file %s, sha256 %s. Who or what put it there is not" % (proposal["source"], proposal["source_sha"][:16]))
    say("  known to this workflow. It did not take the title from Jira.")
    say("  A created issue cannot be unsent. It can be deleted afterwards, by hand, and emails already sent stay sent.")
    say("")
    if change["pointed_out"]:
        say("LOOK AT THESE BEFORE CONFIRMING. They are not refused. Each may be something private. The title holds:")
        for line in change["pointed_out"]:
            say("  %s" % line)
    else:
        say("Looked for in the title and not found: email addresses, web addresses, telephone numbers, @names, and")
        say("  words that mark something as private. That is a search for patterns. It is not a judgement that the")
        say("  title is fit to be seen. The person confirming reads the title.")
    say("Looked for in the title and not found: %d patterns that look like a secret. A title that matched one would" % len(SECRETS))
    say("  have been refused.")
    say("")
    say("Permission check, asked of Jira for this parent and this identity:")
    say("  may see the project           (BROWSE_PROJECTS): %s" % ("yes" if permissions["BROWSE_PROJECTS"] else "no"))
    say("  may create issues in it       (CREATE_ISSUES):   %s" % ("yes" if permissions["CREATE_ISSUES"] else "no"))
    say("Duplicate check, made against Jira just now: the parent has %d subtask%s that this identity can see. The title"
        % (proposal["children"], "" if proposal["children"] == 1 else "s"))
    say("  of each was compared with the title above, capitals and spacing aside, whoever made it.")
    say("  With the same title, under this parent: %d%s." % (len(there), "".join(" (%s, issue id %s)" % (c["key"], c["id"]) for c in there)))
    say("  Subtasks of OTHER stories are not looked at: the same title under another parent is not a duplicate.")
    say("Where Jira cannot check: its request to create an issue has no 'only if there is none like it' condition.")
    say("  The confirmation reads the parent's subtasks again just before writing and stops if one has this title by then.")
    say("")
    say("Snapshot of the parent and its subtasks as Jira returned them, before the preview: %s" % before)
    say("Snapshot of the parent and its subtasks as Jira returned them, after the preview:  %s" % after)
    say("The two are the same. Jira is unchanged, as far as two reads of the parent can show. A snapshot is of the")
    say("  parent's last-updated time, project, type and status, and of the id and title of every subtask it lists.")
    requests_line(conn)
    say("")
    if there:
        say("The parent already has a subtask with this title: %s." % ", ".join("%s (issue id %s)" % (c["key"], c["id"]) for c in there))
        say("No fingerprint is issued, because there is nothing to confirm, and nothing was sent.")
        return 0

    made = now_utc()
    made_at = made.strftime(TIME_FORMAT)
    expires_at = (made + datetime.timedelta(minutes=LIMIT_MINUTES)).strftime(TIME_FORMAT)
    fingerprint = fingerprint_of(proposal, made_at)
    code = fingerprint[:12]
    folder = os.path.join(args.state, "previews")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, code + ".json")
    if os.path.exists(path):
        raise Refused("a preview with this fingerprint was made a moment ago. Wait a second and preview again")
    save_json(path, {"fingerprint": fingerprint, "made_at": made_at, "expires_at": expires_at, "proposal": proposal, "state": "open"})
    say("Fingerprint of this preview: %s" % code)
    say("Made:    %s" % made_at)
    say("Expires: %s (%d minutes after it was made)" % (expires_at, LIMIT_MINUTES))
    say("")
    say("Nothing has been written. To create this subtask, a person who has read this preview confirms it by its")
    say("fingerprint.")
    return 0


# ---------------------------------------------------------------- confirm

def read_preview_record(state, code):
    path = os.path.join(state, "previews", code + ".json")
    try:
        with open(path, encoding="utf-8") as f:
            record = json.load(f)
        made = datetime.datetime.strptime(record["made_at"], TIME_FORMAT)
        genuine = fingerprint_of(record["proposal"], record["made_at"])
        status = record["state"]
    except FileNotFoundError:
        raise Refused("there is no preview with the fingerprint %s. Make a preview, read it, and confirm that one" % code)
    except (ValueError, KeyError, TypeError):
        raise Refused("the saved preview %s cannot be read, so it cannot be confirmed" % code)
    if genuine != record.get("fingerprint") or genuine[:12] != code:
        raise Refused("the saved preview %s has been altered since it was made, so it cannot be confirmed" % code)
    return path, record, made, status


def compare(shown_before, now):
    """How the change worked out now differs from the preview: (what differs in the request, what moved in Jira)."""
    differs, moved = [], []
    if shown_before["parent_id"] != now["parent_id"]:
        differs.append("it names a different parent")
    if shown_before["summary"] != now["summary"]:
        differs.append("the title is not the title the preview showed")
    if shown_before["source"] != now["source"] or shown_before["source_sha"] != now["source_sha"]:
        differs.append("the change file is not the file the preview showed")
    if shown_before["allowlist"] != now["allowlist"]:
        differs.append("the allowlist file is not the one the preview used")
    if shown_before["project_id"] != now["project_id"]:
        moved.append("the parent is now in a different project (project id %s)" % now["project_id"])
    if shown_before["subtask_type"]["id"] != now["subtask_type"]["id"]:
        moved.append("the project's subtask issue type is now a different one")
    if now["same"]:
        moved.append("the parent has been given a subtask with this title since the preview (%s)"
                     % ", ".join("%s, issue id %s" % (c["key"], c["id"]) for c in now["same"]))
    return differs, moved


def jira_said(body):
    """What Jira's refusal said, as other people's text: quoted, cut short, with unseen characters taken out."""
    messages = body.get("errorMessages") if isinstance(body, dict) else None
    texts = [m for m in messages if isinstance(m, str)] if isinstance(messages, list) else []
    errors = body.get("errors") if isinstance(body, dict) else None
    texts += ["%s: %s" % (k, v) for k, v in sorted(errors.items()) if isinstance(k, str) and isinstance(v, str)] if isinstance(errors, dict) else []
    return " Jira's own words, which are not this workflow's: %s." % json.dumps(UNSEEN.sub(" ", " / ".join(texts))[:200]) if texts else ""


def read_back(conn, subtask_id, proposal):
    """Reads the new subtask by its issue id and compares it with what was previewed.
    Returns (the parent id read back or None, a list of (what, ok))."""
    status, _, issue = conn.get("/rest/api/3/issue/%s" % subtask_id, {"fields": ISSUE_FIELDS})
    fields = issue.get("fields") if status == 200 and isinstance(issue, dict) else None
    if not isinstance(fields, dict):
        return None, [("Jira returned the subtask when asked for it by its issue id (status %d)" % status, False)]
    parent = fields.get("parent") if isinstance(fields.get("parent"), dict) else {}
    parent_id = parent.get("id") if ident(parent.get("id")) else None
    kind = fields.get("issuetype") if isinstance(fields.get("issuetype"), dict) else {}
    project = fields.get("project") if isinstance(fields.get("project"), dict) else {}
    summary = fields.get("summary")
    checks = [("its parent, read back, is issue id %s. The parent intended is issue id %s (%s). They are the same"
               % (parent_id or "NOT GIVEN", proposal["parent_id"], proposal["parent_key"]), parent_id == proposal["parent_id"]),
              ("its issue type, read back, is a subtask type (issue type id %s)" % (kind.get("id") if ident(kind.get("id")) else "?"), kind.get("subtask") is True),
              ("its title, read back, is the title previewed, character for character (%d characters, sha256 %s)"
               % (len(summary) if isinstance(summary, str) else 0, hashlib.sha256((summary if isinstance(summary, str) else "").encode("utf-8")).hexdigest()[:16]),
               summary == proposal["summary"]),
              ("its project, read back, is project id %s, the parent's" % (project.get("id") if ident(project.get("id")) else "?"), project.get("id") == proposal["project_id"])]
    return parent_id, checks


def seen_from_parent(conn, subtask_id, proposal):
    """The parent read again: (whether its own list of subtasks holds the new one, the ids of every subtask with this title)."""
    children = children_of(read_issue(conn, proposal["parent_id"]))
    listed = any(c["id"] == subtask_id for c in children)
    twins = sorted(set([c["id"] for c in children if same_title(c["summary"], proposal["summary"])] + [subtask_id]))
    return listed, twins, len(children)


def cmd_confirm(args, conn):
    code = (args.fingerprint or "").strip().lower()
    if not code:
        raise Refused("no confirmation was given. A confirmation names the fingerprint of the preview it "
                      "approves, and there is no way to write without one")
    if len(code) != 12 or any(ch not in "0123456789abcdef" for ch in code):
        raise Refused("a fingerprint is 12 characters, each 0 to 9 or a to f")
    name = (args.confirmed_by or "").strip()
    if not name:
        raise Refused("no confirmation was given. A confirmation gives the name of the person confirming")
    if len(name) > 60 or "@" in name or any(ord(ch) < 32 or ord(ch) == 127 for ch in name):
        raise Refused("the confirming person's name must be short plain text, and not an email address")

    record_path, record, made, status = read_preview_record(args.state, code)
    if status == "written":
        raise Refused("the preview %s has already been confirmed and written. A fingerprint is used once" % code)
    if status != "open":
        raise Refused("the preview %s was confirmed before and a write was sent (recorded as '%s'). It cannot be "
                      "used again. Read the parent's subtasks in Jira, then make a new preview" % (code, status))

    confirmed = now_utc()
    now = confirmed
    if args.pretend_minutes_later:
        say("TEST CLOCK: pretending it is %d minutes later than it is." % args.pretend_minutes_later)
        now += datetime.timedelta(minutes=args.pretend_minutes_later)
    age = now - made
    if age < datetime.timedelta(0):
        raise Refused("the preview %s is dated later than the clock says it is now" % code)
    if age > datetime.timedelta(minutes=LIMIT_MINUTES):
        raise Refused("this preview is too old. It was made %d minutes ago and the limit is %d. Make a new "
                      "preview and read it" % (age.total_seconds() // 60, LIMIT_MINUTES))

    before = record["proposal"]
    change = read_change(args.change)
    if change["ref"] != before["ref"]:
        raise Refused("the change is not the one that was previewed: it names a different parent. Make a new "
                      "preview and read it")
    allowed = load_allowlist(args.allowlist)
    site = site_fingerprint(conn.host)
    if site != before["site"]:
        raise Refused("this is not the Jira site the preview was made against. Make a new preview and read it")
    parent_id = before["parent_id"]
    if change["ref"] != parent_id and read_issue(conn, change["ref"])["id"] != parent_id:
        raise Refused("the reference %s now leads to a different issue than the one the preview showed (issue id %s). "
                      "Make a new preview and read it" % (json.dumps(change["ref"]), parent_id))
    permissions = read_permissions(conn, parent_id)
    subtype = read_subtask_type(conn, before["project_id"])
    issue = read_issue(conn, parent_id)               # the last read before the write, by the issue id
    proposal = build_proposal(site, allowed, args.allowlist, issue, permissions, subtype, change)
    differs, moved = compare(before, proposal)
    if differs:
        raise Refused("the change is not the one that was previewed: %s. Make a new preview and read it" % "; ".join(differs))
    if moved:
        raise Refused("something changed in Jira after the preview was made: %s. Make a new preview and read it" % "; ".join(moved))

    say("CONFIRMATION for preview %s, given by: %s (the name given with the confirmation)." % (code, name))
    say("")
    head(conn, proposal)
    say("")
    say("Checked in this run, before writing:")
    say("  the preview is %d minute%s old, and the limit is %d: ok"
        % (age.total_seconds() // 60, "" if age.total_seconds() // 60 == 1 else "s", LIMIT_MINUTES))
    say("  the saved preview is unaltered and has not been used: ok")
    say("  the change file asks for exactly what the preview showed: ok")
    say("  the reference in the change file still leads to issue id %s: ok" % parent_id)
    say("  the project is on the sandbox allowlist for this site: ok")
    say("  the parent is not a subtask and is not closed: ok")
    say("  Jira says this identity may create issues in the project: ok")
    say("  the parent's %d subtask%s, read just before the write, hold none with this title: ok" % (proposal["children"], "" if proposal["children"] == 1 else "s"))
    say("")

    if now_utc() + datetime.timedelta(minutes=args.pretend_minutes_later or 0) - made > datetime.timedelta(minutes=LIMIT_MINUTES):
        raise Refused("this preview passed its limit of %d minutes while the checks were being made. Make a new preview and read it" % LIMIT_MINUTES)
    try:
        os.makedirs(os.path.join(args.state, "sending"), exist_ok=True)
        os.close(os.open(os.path.join(args.state, "sending", code), os.O_CREAT | os.O_EXCL | os.O_WRONLY))
    except FileExistsError:
        raise Refused("another run is confirming the preview %s at this moment, or one began and did not finish. It cannot be "
                      "used again. Read the parent's subtasks in Jira, then make a new preview" % code)
    record["state"] = "sending"
    save_json(record_path, record)
    try:
        status, _, body = conn.post_subtask(proposal["project_id"], parent_id, proposal["subtask_type"]["id"], proposal["summary"])
    except NeedsLooking:
        record["state"] = "sent, answer not received"
        save_json(record_path, record)
        raise
    written_at = now_utc().strftime(TIME_FORMAT)
    subtask_id = body.get("id") if isinstance(body, dict) else None
    subtask_key = body.get("key") if isinstance(body, dict) else None
    if status not in (200, 201) or not ident(subtask_id) or not (isinstance(subtask_key, str) and REF.fullmatch(subtask_key)):
        record["state"] = "sent, Jira answered %d" % status
        save_json(record_path, record)
        after = children_of(read_issue(conn, parent_id))
        new = [c for c in after if same_title(c["summary"], proposal["summary"])]
        if status in REFUSALS and not new and len(after) == proposal["children"]:
            raise NotWritten("Jira answered %d to the write.%s Read back afterwards, the parent has the %d subtasks it had "
                             "before and none has this title, so nothing was written. The preview cannot be used again"
                             % (status, jira_said(body), proposal["children"]))
        raise NeedsLooking("Jira answered %d to the write and gave no usable issue id. Read back just afterwards, the parent has "
                           "%d subtasks where it had %d, and %d with this title%s. If there is none, Jira may still be creating it: look "
                           "again in a minute" % (status, len(after), proposal["children"], len(new),
                                                  "".join(" (%s, issue id %s)" % (c["key"], c["id"]) for c in new)))

    confirmed_at = confirmed.strftime(TIME_FORMAT)
    result = {"fingerprint": record["fingerprint"], "parent_key": proposal["parent_key"], "parent_id": parent_id,
              "subtask_key": subtask_key, "subtask_id": subtask_id, "parent_read_back": None,
              "project_key": proposal["project_key"], "project_id": proposal["project_id"], "site_fingerprint": site,
              "subtask_type": proposal["subtask_type"], "confirmed_by": name, "confirmed_at": confirmed_at, "written_at": written_at,
              "preview_made_at": record["made_at"], "summary": proposal["summary"], "summary_sha": proposal["summary_sha"],
              "source": proposal["source"], "source_sha": proposal["source_sha"], "read_back": None}
    say("WRITTEN to Jira: one subtask, %s (issue id %s), under parent %s. Jira answered %d." % (subtask_key, subtask_id, proposal["parent_key"], status))
    os.makedirs(os.path.join(args.state, "written"), exist_ok=True)
    save_json(os.path.join(args.state, "written", code + ".json"), result)   # kept at once, so that the new issue's id is not lost
    record["state"] = "written"
    save_json(record_path, record)
    say("The confirmation and the write happened in this one run of the command.")
    say("")
    say("Read back from Jira after the write, by that issue id:")
    parent_read, checks = read_back(conn, subtask_id, proposal)
    listed, twins, count = seen_from_parent(conn, subtask_id, proposal)
    checks.append(("the parent's own list of its %d subtasks, read again, holds issue id %s" % (count, subtask_id), listed))
    for what, ok in checks:
        say("  %s: %s" % (what, "yes" if ok else "NO"))
    say("  subtasks of this parent with this title, counted after the write: %d%s"
        % (len(twins), "" if len(twins) == 1 else ". MORE THAN ONE: issue ids %s" % ", ".join(twins)))

    result["parent_read_back"] = parent_read
    result["read_back"] = [[what, ok] for what, ok in checks]
    save_json(os.path.join(args.state, "written", code + ".json"), result)

    say("")
    say("RESULT RECORD")
    for line in result_lines(result):
        say("  " + line)
    if args.result:
        text = "\n".join(["# Result record: one subtask created under one Jira story", ""] + ["- " + line for line in result_lines(result)]) + "\n"
        os.makedirs(os.path.dirname(os.path.abspath(args.result)), exist_ok=True)
        with open(args.result, "w", encoding="utf-8") as f:
            f.write(text.replace(conn.host, SITE_MARK))
        say("")
        say("The result record was also saved as Markdown where --result said.")
    if not all(ok for _, ok in checks):
        raise NeedsLooking("Jira accepted the write, and the subtask does not read back as previewed")
    if len(twins) != 1:
        raise NeedsLooking("the subtask was created, and the parent now has %d subtasks with this title" % len(twins))
    return 0


def result_lines(result):
    return ["Issue key: %s, the subtask that was created" % result["subtask_key"],
            "Identifier of what was created: Jira issue id %s" % result["subtask_id"],
            "Parent intended: %s, issue id %s (the id identifies it; a key can change)" % (result["parent_key"], result["parent_id"]),
            "Parent read back from the subtask after the write: issue id %s%s" % (result["parent_read_back"] or "NOT READ", ", the same" if result["parent_read_back"] == result["parent_id"] else ". NOT THE SAME"),
            "Target project: %s (project id %s), on the sandbox allowlist" % (result["project_key"], result["project_id"]),
            "Jira site: %s, site fingerprint %s" % (SITE_MARK, result["site_fingerprint"]),
            "Issue type: %s (issue type id %s)" % (quoted(result["subtask_type"]["name"]), result["subtask_type"]["id"]),
            "Title: %d characters, sha256 %s, from the change file %s (file sha256 %s)" % (len(result["summary"]), result["summary_sha"], result["source"], result["source_sha"]),
            "Read back after the write: %s" % ("as previewed: same parent, a subtask, same title, same project, and listed by the parent"
                                               if result["read_back"] and all(ok for _, ok in result["read_back"]) else "NOT as previewed, or not read back. See the run's output"),
            "Written at: %s" % result["written_at"],
            "Confirmed by: %s, at %s" % (result["confirmed_by"], result["confirmed_at"]),
            "Preview: fingerprint %s, made %s" % (result["fingerprint"][:12], result["preview_made_at"]),
            "To reverse: delete %s in Jira, by hand. This workflow does not delete. Emails Jira sent about it cannot "
            "be taken back" % result["subtask_key"]]


# ---------------------------------------------------------------- check


def cmd_check(args, conn):
    code = (args.fingerprint or "").strip().lower()
    if len(code) != 12 or any(ch not in "0123456789abcdef" for ch in code):
        raise Refused("a fingerprint is 12 characters, each 0 to 9 or a to f")
    try:
        with open(os.path.join(args.state, "written", code + ".json"), encoding="utf-8") as f:
            result = json.load(f)
        with open(os.path.join(args.state, "previews", code + ".json"), encoding="utf-8") as f:
            previewed = json.load(f)["proposal"]
        proposal = {"parent_id": result["parent_id"], "parent_key": result["parent_key"], "summary": result["summary"], "project_id": result["project_id"]}
        subtask_id = result["subtask_id"]
    except FileNotFoundError:
        raise Refused("there is no record of a write for the fingerprint %s" % code)
    except (ValueError, KeyError, TypeError):
        raise Refused("the record of the write %s cannot be read" % code)
    if site_fingerprint(conn.host) != result["site_fingerprint"]:
        raise Refused("this is not the Jira site the subtask was written to")
    parent_read, checks = read_back(conn, subtask_id, proposal)
    listed, twins, count = seen_from_parent(conn, subtask_id, proposal)
    checks.append(("the parent's own list of its %d subtasks holds issue id %s" % (count, subtask_id), listed))
    checks.append(("the parent the write recorded is the parent the preview showed (issue id %s)" % previewed.get("parent_id"), previewed.get("parent_id") == result["parent_id"]))

    say("PARENT CHECK for the write of preview %s. Nothing is written by this command." % code)
    say("")
    say("Jira site:  https://%s  (site fingerprint %s)" % (conn.host, result["site_fingerprint"]))
    say("Subtask:    %s (issue id %s), the identifiers Jira gave when it was created." % (result["subtask_key"], subtask_id))
    say("Parent intended, as the preview showed it: %s (issue id %s)." % (result["parent_key"], result["parent_id"]))
    say("Parent read back from the subtask just now: issue id %s." % (parent_read or "NOT GIVEN"))
    say("")
    for what, ok in checks:
        say("  %s: %s" % (what, "yes" if ok else "NO"))
    say("  subtasks of this parent with this title: %d%s" % (len(twins), "" if len(twins) == 1 else ". NOT ONE: issue ids %s" % ", ".join(twins)))
    say("")
    requests_line(conn)
    ok = all(good for _, good in checks) and len(twins) == 1
    say("")
    say("FOUND: the subtask is under the parent intended." if ok else "NOT AS PREVIEWED: see the lines marked NO above.")
    return 0 if ok else 1


# ---------------------------------------------------------------- running

def minutes_forward(text):
    if not text.isascii() or not text.isdigit() or len(text) > 6:
        raise argparse.ArgumentTypeError("must be a whole number of minutes, 0 or more")
    return int(text)


def refused(refusal):
    say("")
    say("REFUSED: %s." % refusal)
    say("Nothing has been written.")
    return 1


def run(args, conn):
    """One command, start to finish. Returns the exit code; what it said is in LINES."""
    posted = lambda: any(method == "POST" for method, _ in conn.sent)  # noqa: E731
    try:
        try:
            return {"confirm": cmd_confirm, "preview": cmd_preview, "check": cmd_check}[args.command](args, conn)
        except NotWritten as refusal:
            return refused(refusal)
        except Refused as refusal:
            if posted():
                raise NeedsLooking("the write was sent, and a step after it could not be done: %s. The subtask may have been created" % refusal)
            return refused(refusal)
        except NeedsLooking:
            raise
        except Exception as failure:  # nothing may hide what was already sent
            if posted():
                raise NeedsLooking("the write was sent, and the program then failed (%s). The subtask may have been created" % type(failure).__name__)
            return refused("the program failed before anything was sent (%s)" % type(failure).__name__)
    except NeedsLooking as problem:
        say("")
        say("A PERSON NEEDS TO LOOK: %s." % problem)
        say("Do not run this again before reading the parent's subtasks in Jira.")
        return 2


def main(argv=None):
    parser = argparse.ArgumentParser(description="Preview, then confirm, one subtask under one Jira story. Then check its parent.")
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("preview", "confirm", "check"):
        sub = commands.add_parser(command)
        sub.add_argument("--source", choices=("live", "fake"), required=True)
        sub.add_argument("--state", required=True, help="the folder where previews and write records are kept")
        sub.add_argument("--log", help="also save the output here, with the site's address and the parent's title removed")
        if command != "check":
            sub.add_argument("--change", required=True, help="the change file")
            sub.add_argument("--allowlist", required=True, help="the sandbox allowlist")
        if command != "preview":
            sub.add_argument("--fingerprint")
        if command == "confirm":
            sub.add_argument("--confirmed-by")
            sub.add_argument("--result", help="save the result record of a write here, as Markdown")
            sub.add_argument("--pretend-minutes-later", type=minutes_forward, default=0, metavar="N",
                             help="tests only: move 'now' forward by N minutes")
    args = parser.parse_args(argv)
    del LINES[:]
    secrets, conn, fake, fake_path = [], None, None, os.path.join(args.state, "fake-jira.json")
    try:
        if args.source == "fake":
            import fake_jira
            fake = fake_jira.FakeJira.open(fake_path)
            host = urllib.parse.urlparse(fake_jira.SITE).hostname
            conn = Connection(fake.get, fake.post if args.command == "confirm" else None, host)
        else:
            conn, secrets = make_live(args.command == "confirm")
        code = run(args, conn)
    except Refused as refusal:
        code = refused(refusal)
    if fake is not None:
        fake.save(fake_path)
    text = "\n".join(shown for shown, _ in LINES)
    kept = "\n".join(saved for _, saved in LINES)
    if any(secret and secret in text for secret in secrets):
        wrote = bool(conn) and any(method == "POST" for method, _ in conn.sent)
        print("STOPPED: a credential was found in the output, so the output was not shown or saved.%s"
              % (" A WRITE WAS SENT TO JIRA in this run. Read the parent's subtasks in Jira before doing anything else." if wrote else ""))
        return 2 if wrote else 1
    print(text)
    if secrets:
        note = ("\nThe output above was searched for the API token, the account's email address and their encoded\n"
                "form: none found.")
        print(note)
        kept += "\n" + note
    if args.log:
        host = conn.host if conn else ""
        kept = kept.replace("https://" + host, SITE_MARK).replace(host, SITE_MARK) if host else kept
        try:
            os.makedirs(os.path.dirname(os.path.abspath(args.log)), exist_ok=True)
            with open(args.log, "w", encoding="utf-8") as f:
                f.write(kept + "\n")
        except OSError:
            print("\nTHE OUTPUT ABOVE COULD NOT BE SAVED where --log said. What it says stands.")
    return code


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    sys.exit(main())
