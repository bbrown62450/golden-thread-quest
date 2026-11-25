#!/usr/bin/env python3
"""Adds one comment to one Jira story: preview first, then a person confirms.

    comment.py preview --source live|fake --change CHANGE.json --allowlist FILE --state DIR
    comment.py confirm --source live|fake --change CHANGE.json --allowlist FILE --state DIR \
                       --fingerprint CODE --confirmed-by NAME
    comment.py check   --source live|fake --change CHANGE.json --state DIR --fingerprint CODE

A change file names one story, the file that holds the comment's text, and who may see the comment:

    {"story": "SAND-1", "text_file": "comment.txt", "visibility": "everyone"}
    {"story": "SAND-1", "text_file": "comment.txt", "visibility": {"role": "Administrators"}}

"everyone" means everyone who can see the story: no restriction is put on the comment. A role is the name of one of
the project's roles. Nothing else is supported. There is no option that widens this.

The text file is read as plain text, in the folder of the change file. It is sent as plain text: one paragraph to a
line, with no formatting, no links and no mentions. An @name in it is text and mentions nobody.

    The text is refused if it is empty, longer than 2000 characters or 40 lines, has an empty line, a line that
    begins or ends with a space, a tab, or a character that cannot be seen.
    The text is refused if part of it looks like a secret: a key, a token, a password written out. See SECRETS below.
    The text is NOT refused for looking private. Email addresses, telephone numbers, web addresses, @names and
    words such as "confidential" are pointed out in the preview, for the person confirming to judge.

preview   reads Jira and writes nothing. It has no way to send a write.
          It shows the Jira site, the project, the story, the exact text with its visibility beside it, where the
          text came from, the permission check and the duplicate check, and a fingerprint. It saves that preview in
          the state folder. If this identity has already put a comment with the same text and the same visibility
          on the story, no fingerprint is issued: there is nothing to add.

confirm   adds the comment of one preview, named by its fingerprint, and only if all of this holds at that moment:
            a fingerprint and the confirming person's name are given;
            the saved preview is unaltered, unused and at most 15 minutes old;
            the change file and the text file still ask for exactly what the preview showed;
            the project is on the sandbox allowlist, for this Jira site;
            Jira still says this identity may comment on the story;
            the story's comments, read again just before the write, still hold no such comment by this identity.
          After the write the comment is read back by its identifier and compared with the text previewed.

check     reads the story back after a write and looks for the comment: the same text, the expected author, the
          visibility the preview showed. It writes nothing.

The allowlist is a JSON file listing projects by Jira's project id together with a fingerprint of the site's
address, because project ids repeat from site to site.

What this cannot do. Jira's request to add a comment has no "only if there is no such comment yet" condition. Between
the last read and the write there is a moment in which a second run could add the same comment. The duplicate check
before the write, and the check after it, report that case. And this workflow cannot list who can see a story: it
shows the visibility of the comment and the story's security level, and says so.

A write is sent once and never retried.

--pretend-minutes-later N is for tests: it moves "now" forward by N minutes.
--log FILE saves the output with the site's address replaced by a marker.
--result FILE saves the result record of a write as Markdown, the same way.

Nothing in the story, or in the comments already on it, is printed or acted on. Other comments are compared with
the text and counted.

For a live run the connection comes from the environment variables JIRA_BASE_URL, JIRA_EMAIL and JIRA_API_TOKEN. None
is stored. The output is searched for the token, the email address and their encoded form before it is shown. The
site's address is shown on screen, so that the person confirming can see where the write would go, and is removed
from anything saved. The account's identifier and name are never printed.

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
import urllib.error
import urllib.parse
import urllib.request

LIMIT_MINUTES = 15
MAX_CHARACTERS = 2000
MAX_LINES = 40
MAX_COMMENT_PAGES = 50
REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,60}")
ROLE = re.compile(r"[A-Za-z0-9][A-Za-z0-9 _-]{0,59}")
FILE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,80}")
TIME_FORMAT = "%Y-%m-%d %H:%M:%S UTC"
SITE_MARK = "[site address removed]"
UNSEEN = re.compile("[\\x00-\\x09\\x0b-\\x1f\\x7f-\\xa0\\u00ad\\u034f\\u061c\\u115f\\u1160\\u200b-\\u200f\\u2028\\u2029\\u202a-\\u202e\\u2060-\\u2069\\u2800\\u3164\\ufeff\\U000e0000-\\U000e007f]")

# SECRETS. A comment whose text matches one of these is refused. They are patterns, so they miss secrets of other
# shapes and can refuse text that is not a secret. The person confirming still has to read the text.
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
# POINTED OUT, and not refused. Each is something a person should look at before making a comment public.
PRIVATE = (
    ("an email address", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z0-9.-]+")),
    ("a web address", re.compile(r"(?i)\b(?:https?://|www\.)\S+")),
    ("what may be a telephone number", re.compile(r"(?<![0-9])\+?[0-9][0-9 ().-]{7,}[0-9](?![0-9])")),
    ("an @name, which is sent as text and mentions nobody", re.compile(r"(?<![A-Za-z0-9._%+-])@[A-Za-z0-9_.-]+")),
    ("a word that marks something as private", re.compile(r"(?i)\b(?:confidential|private|internal only|do not share|not for customers?|under nda)\b")),
)

LINES = []


class Refused(Exception):
    """Nothing was written. The message is the reason."""


class NotWritten(Refused):
    """A write was sent, and reading Jira afterwards shows that nothing was written."""


class NeedsLooking(Exception):
    """A write was sent. The message says what is and is not known."""


def say(text=""):
    LINES.append(text)


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

    def post_comment(self, issue_id, text, visibility):
        if self._post is None:
            raise Refused("this command has no way to write")
        if not ident(issue_id):
            raise Refused("a write names the story by its issue id")
        body = {"body": document_of(text)}
        if visibility["kind"] == "role":
            body["visibility"] = {"type": "role", "value": visibility["name"]}
        path = "/rest/api/3/issue/%s/comment" % issue_id
        self.sent.append(("POST", path))
        try:
            return self._post(path, None, body)
        except (OSError, TimeoutError) as err:
            raise NeedsLooking("the write was sent and no answer came back (%s). It is NOT KNOWN whether Jira added "
                               "the comment. It was not sent again" % type(getattr(err, "reason", err)).__name__)


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
        if not re.fullmatch(r"/rest/api/3/issue/[0-9]{1,20}/comment", path):
            raise Refused("the only write this workflow sends is one comment on one story")
        return send("POST", path, params, body)

    return Connection(get, post if may_write else None, host), [token, email, encoded]


def site_fingerprint(host):
    return hashlib.sha256(host.lower().encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------- the text of a comment


def document_of(text):
    """The text as the document Jira takes: one paragraph to a line, text only, with no marks."""
    return {"type": "doc", "version": 1,
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": line}]} for line in text.split("\n")]}


def text_of(document):
    """A Jira document back as plain text, and the things in it that are not plain text.
    Returns (text, [what is not plain]). A document that is not one gives (None, [...])."""
    if not isinstance(document, dict) or document.get("type") != "doc" or not isinstance(document.get("content"), list):
        return None, ["it is not a document"]
    lines, odd = [], []
    for block in document["content"]:
        if not isinstance(block, dict) or block.get("type") != "paragraph":
            odd.append("a block of type %s" % json.dumps(str((block or {}).get("type") if isinstance(block, dict) else block)[:30]))
            continue
        parts = []
        for node in block.get("content") or []:
            if isinstance(node, dict) and node.get("type") == "text" and isinstance(node.get("text"), str):
                parts.append(node["text"])
                if node.get("marks"):
                    odd.append("formatting on a piece of text")
            elif isinstance(node, dict) and node.get("type") == "hardBreak":
                parts.append("\n")
            else:
                odd.append("a piece of type %s" % json.dumps(str((node or {}).get("type") if isinstance(node, dict) else node)[:30]))
        lines.append("".join(parts))
    return "\n".join(lines), odd


def check_text(text):
    """Refuses a text this workflow will not send. Returns what to point out to the person confirming."""
    if not text:
        raise Refused("the text file is empty")
    if len(text) > MAX_CHARACTERS:
        raise Refused("the text is %d characters long and the limit is %d" % (len(text), MAX_CHARACTERS))
    lines = text.split("\n")
    if len(lines) > MAX_LINES:
        raise Refused("the text has %d lines and the limit is %d" % (len(lines), MAX_LINES))
    for number, line in enumerate(lines, 1):
        if not line.strip():
            raise Refused("line %d of the text is empty. Each line is sent as a paragraph, and empty ones are not supported" % number)
        if line != line.strip():
            raise Refused("line %d of the text begins or ends with a space" % number)
        if UNSEEN.search(line):
            raise Refused("line %d of the text has a tab or a character that cannot be seen" % number)
    for what, pattern in SECRETS:
        if pattern.search(text):
            line = next((n for n, each in enumerate(lines, 1) if pattern.search(each)), 0)
            raise Refused("the text looks as if it holds %s%s. A comment cannot be unsent, so this workflow does not "
                          "send it. The matching text is not shown here" % (what, ", on line %d" % line if line else ""))
    return ["line %d: %s" % (number, what) for number, line in enumerate(lines, 1) for what, pattern in PRIVATE if pattern.search(line)]


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
    """The story, the text and the visibility wanted, checked. Returns a dict."""
    change = read_json(path, "change file")
    if not isinstance(change, dict) or set(change) != {"story", "text_file", "visibility"}:
        raise Refused("the change file must have exactly 'story', 'text_file' and 'visibility'")
    ref, name, visibility = change["story"], change["text_file"], change["visibility"]
    if not isinstance(ref, str) or not REF.fullmatch(ref):
        raise Refused("the story is given by its id or its key: letters, digits and dashes only")
    if not isinstance(name, str) or not FILE_NAME.fullmatch(name):
        raise Refused("text_file is the name of a file beside the change file: letters, digits, dots and dashes only")
    if visibility == "everyone":
        wanted = {"kind": "everyone"}
    elif isinstance(visibility, dict) and set(visibility) == {"role"} and isinstance(visibility["role"], str) and ROLE.fullmatch(visibility["role"]):
        wanted = {"kind": "role", "name": visibility["role"]}
    else:
        raise Refused("visibility must be \"everyone\", or {\"role\": \"the name of a project role\"}. Nothing else is supported")
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(path)), name), "rb") as f:
            raw = f.read(MAX_CHARACTERS * 8 + 1)
    except FileNotFoundError:
        raise Refused("there is no text file named %s beside the change file" % name)
    except OSError:
        raise Refused("the text file %s could not be read" % name)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise Refused("the text file is not UTF-8 text")
    text = text.replace("\r\n", "\n")
    text = text[:-1] if text.endswith("\n") else text   # the one line ending a text file ends with is not part of the comment
    return {"ref": ref, "source": name, "source_sha": hashlib.sha256(raw).hexdigest(), "text": text, "visibility": wanted,
            "pointed_out": check_text(text)}


# ---------------------------------------------------------------- reading Jira


def ident(value):
    return isinstance(value, str) and value.isascii() and value.isdigit() and len(value) <= 20


def read_issue(conn, ref):
    status, _, issue = conn.get("/rest/api/3/issue/%s" % ref)
    if status == 401:
        raise Refused("Jira rejected the credentials (401). Check JIRA_EMAIL and JIRA_API_TOKEN")
    if status == 404:
        raise Refused("Jira answered 404 for the story. It does not exist, or this identity is not permitted "
                      "to see it. Jira gives one answer for both")
    fields = issue.get("fields") if isinstance(issue, dict) else None
    project = fields.get("project") if isinstance(fields, dict) else None
    ok = (status == 200 and isinstance(project, dict) and ident(issue.get("id")) and ident(project.get("id"))
          and isinstance(issue.get("key"), str) and REF.fullmatch(issue["key"])
          and isinstance(project.get("key"), str) and REF.fullmatch(project["key"]))
    if not ok:
        raise Refused("Jira's answer for the story could not be used (status %d)" % status)
    return issue


def security_of(issue):
    """The name of the story's security level, or None. A level limits who can see the story, and so the comment."""
    if "security" not in issue["fields"]:
        return "?"
    level = issue["fields"]["security"]
    if level is None:
        return None
    if not isinstance(level, dict) or not isinstance(level.get("name"), str):
        raise Refused("Jira's security level for the story could not be read, so who can see it is not known")
    return level["name"][:60]


def read_myself(conn):
    status, _, body = conn.get("/rest/api/3/myself")
    if status == 401:
        raise Refused("Jira rejected the credentials (401). Check JIRA_EMAIL and JIRA_API_TOKEN")
    if status != 200 or not isinstance(body.get("accountId"), str):
        raise Refused("Jira did not say which identity this is (status %d)" % status)
    return body["accountId"]


def read_permissions(conn, issue_id):
    names = ("BROWSE_PROJECTS", "ADD_COMMENTS")
    status, _, body = conn.get("/rest/api/3/mypermissions", {"issueId": issue_id, "permissions": ",".join(names)})
    found = body.get("permissions") if status == 200 else None
    if not isinstance(found, dict):
        raise Refused("Jira did not answer the permission check (status %d), so nothing is assumed" % status)
    return {name: (found.get(name) or {}).get("havePermission") is True for name in names}


def read_role(conn, project_id, name):
    """The identifier of a project role, by its name. Refuses if the project has no role of that name."""
    status, _, body = conn.get("/rest/api/3/project/%s/role" % project_id)
    if status != 200 or not body:
        raise Refused("Jira did not list the project's roles (status %d), so the visibility cannot be checked" % status)
    link = body.get(name)
    found = re.search(r"/role/([0-9]{1,20})$", link) if isinstance(link, str) else None
    if not found:
        raise Refused("the project has no role named %s. Its roles: %s" % (json.dumps(name), ", ".join(json.dumps(str(k)[:60]) for k in sorted(body)) or "none"))
    return found.group(1)


def read_comments(conn, issue_id):
    """Every comment on the story, oldest first. Refuses if the whole list could not be read."""
    comments, start = [], 0
    for _ in range(MAX_COMMENT_PAGES):
        status, _, body = conn.get("/rest/api/3/issue/%s/comment" % issue_id, {"startAt": start, "maxResults": 100})
        page, total = (body.get("comments"), body.get("total")) if status == 200 else (None, None)
        if not isinstance(page, list) or not isinstance(total, int):
            raise Refused("Jira did not list the story's comments (status %d), so the duplicate check cannot be made" % status)
        comments += [c for c in page if isinstance(c, dict)]
        start += len(page)
        if start >= total or not page:
            return comments
    raise Refused("the story has more than %d comments, which is more than this workflow reads, so the duplicate "
                  "check cannot be made" % (MAX_COMMENT_PAGES * 100))


def visibility_of(comment):
    """A comment's visibility, in the form this workflow compares."""
    seen = comment.get("visibility")
    if seen is None:
        return {"kind": "everyone"}
    if isinstance(seen, dict) and seen.get("type") == "role" and isinstance(seen.get("value"), str):
        return {"kind": "role", "name": seen["value"]}
    return {"kind": "other"}


def same_visibility(a, b):
    return a["kind"] == b["kind"] and a.get("name") == b.get("name")


def shown_visibility(visibility, key, security):
    if visibility["kind"] == "everyone":
        text = "EVERYONE who can see the story %s. No restriction is put on the comment." % key
    elif visibility["kind"] == "role":
        text = "ONLY people in the project role %s who can also see the story %s." % (json.dumps(visibility["name"]), key)
    else:
        text = "a restriction this workflow does not know."
    return text + (" Jira did not say whether the story has a security level." if security == "?"
                   else " The story has the security level %s, which limits who can see it." % json.dumps(security) if security
                   else " The story has no security level.")


def canonical(data):
    return json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def snapshot(issue, comments):
    """One short code for what Jira returned of the story's last update, project and security level, and of every comment.
    Fields that move when a person only looks at the story, such as when it was last viewed, are left out."""
    fields = issue["fields"]
    text = canonical({"id": issue["id"], "key": issue["key"], "updated": fields.get("updated"), "project": fields["project"].get("id"),
                      "security": fields.get("security"), "comments": comments})
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------- what the change is


def allowlist_note(path, allowed):
    with open(path, "rb") as f:
        sha = hashlib.sha256(f.read()).hexdigest()
    return "the file %s, sha256 %s, which lists %d project%s" % (os.path.basename(path), sha[:16], len(allowed), "" if len(allowed) == 1 else "s")


def check_allowlist(site, allowed, issue, allowlist_path):
    project = issue["fields"]["project"]
    if (site, project["id"]) not in allowed:
        raise Refused("project %s (project id %s) on the Jira site with fingerprint %s is not on the sandbox "
                      "allowlist (%s). This workflow writes only to projects listed there"
                      % (project["key"], project["id"], site, os.path.basename(allowlist_path)))


def build_proposal(conn, site, allowed, allowlist_path, issue, permissions, comments, me, change):
    """The one place that decides what a change means. The preview shows its result; confirm compares with it."""
    check_allowlist(site, allowed, issue, allowlist_path)
    if not permissions["BROWSE_PROJECTS"] or not permissions["ADD_COMMENTS"]:
        raise Refused("Jira says this identity may not comment on this story (ADD_COMMENTS: %s)"
                      % ("yes" if permissions["ADD_COMMENTS"] else "no"))
    project = issue["fields"]["project"]
    kind = project.get("projectTypeKey")
    kind = kind if isinstance(kind, str) and re.fullmatch(r"[a-z_]{1,30}", kind) else "not given"
    if kind == "service_desk" and change["visibility"]["kind"] == "everyone":
        raise Refused("this is a service project, where a comment with no restriction can be seen by customers. This "
                      "workflow does not send one there")
    visibility = dict(change["visibility"])
    if visibility["kind"] == "role":
        visibility["id"] = read_role(conn, project["id"], visibility["name"])
    same = [c for c in comments if text_of(c.get("body"))[0] == change["text"] and ident(c.get("id"))]
    mine = [c for c in same if (c.get("author") or {}).get("accountId") == me]
    return {"site": site, "ref": change["ref"], "issue_id": issue["id"], "key": issue["key"], "project_id": project["id"],
            "project_key": project["key"], "text": change["text"], "text_sha": hashlib.sha256(change["text"].encode("utf-8")).hexdigest(),
            "source": change["source"], "source_sha": change["source_sha"], "visibility": visibility,
            "security": security_of(issue), "project_type": kind, "allowlist": allowlist_note(allowlist_path, allowed),
            "permissions": permissions, "comments": len(comments),
            "same_mine": [{"id": c["id"], "visibility": visibility_of(c)} for c in mine],
            "same_others": [c["id"] for c in same if c not in mine]}


def already_there(proposal):
    """The identifiers of comments by this identity with the same text and the same visibility."""
    return [c["id"] for c in proposal["same_mine"] if same_visibility(c["visibility"], proposal["visibility"])]


def fingerprint_of(proposal, made_at):
    return hashlib.sha256(canonical({"proposal": proposal, "made_at": made_at}).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------- showing


def head(conn, proposal):
    say("Jira site:  https://%s  (site fingerprint %s)" % (conn.host, proposal["site"]))
    say("Project:    %s (project id %s). Kind of project, as Jira gives it: %s." % (proposal["project_key"], proposal["project_id"], proposal["project_type"]))
    say("            On the sandbox allowlist: yes. The allowlist is %s." % proposal["allowlist"])
    say("Story:      %s (issue id %s). The id is what identifies it. Its title is other people's text and is not" % (proposal["key"], proposal["issue_id"]))
    say("            shown: check the key against the story you mean, in Jira.")


def show_text(text):
    for line in text.split("\n"):
        say("    | %s" % line)


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
    issue = read_issue(conn, change["ref"])
    check_allowlist(site, allowed, issue, args.allowlist)
    me = read_myself(conn)
    permissions = read_permissions(conn, issue["id"])
    comments = read_comments(conn, issue["id"])
    before = snapshot(issue, comments)
    proposal = build_proposal(conn, site, allowed, args.allowlist, issue, permissions, comments, me, change)
    after = snapshot(read_issue(conn, issue["id"]), read_comments(conn, issue["id"]))
    if after != before:
        raise Refused("the story or its comments changed in Jira while the preview was being made. Preview again")
    there = already_there(proposal)

    say("NOTHING TO ADD. Nothing has been written." if there else "PREVIEW. Nothing has been written.")
    say("")
    head(conn, proposal)
    say("")
    say("%s: one comment on %s." % ("The comment asked for" if there else "The change that would be made", proposal["key"]))
    say("  It would appear under the Jira account the API token belongs to, called this identity below. Not under the")
    say("  name given with the confirmation.")
    say("  Text, exactly as it would be sent, between the bars. %d character%s, %d line%s:"
        % (len(proposal["text"]), "" if len(proposal["text"]) == 1 else "s", proposal["text"].count("\n") + 1, "" if "\n" not in proposal["text"] else "s"))
    show_text(proposal["text"])
    say("  WHO CAN SEE IT: %s" % shown_visibility(proposal["visibility"], proposal["key"], proposal["security"]))
    say("    This workflow cannot list who that is, and cannot tell whether the project is open to customers or to the")
    say("    public. Jira may also email the story's watchers the whole text.")
    say("  Where the text came from: the file %s beside the change file, sha256 %s." % (proposal["source"], proposal["source_sha"]))
    say("    Who or what put the text in that file is not known to this workflow. It did not write the file and did not")
    say("    take the text from Jira.")
    say("  It is sent as plain text: no formatting, no links, no mentions. Nothing else on the story would be sent.")
    say("  A comment cannot be unsent. It can be deleted afterwards, by hand, and emails already sent stay sent.")
    say("")
    if change["pointed_out"]:
        say("LOOK AT THESE BEFORE CONFIRMING. They are not refused. Each may be something private:")
        for line in change["pointed_out"]:
            say("  %s" % line)
    else:
        say("Looked for in the text and not found: email addresses, web addresses, telephone numbers, @names, and")
        say("  words that mark something as private. That is a search for patterns. It is not a judgement that the")
        say("  text is fit to be seen. The person confirming reads the text.")
    say("Looked for in the text and not found: %d patterns that look like a secret. A text that matched one would" % len(SECRETS))
    say("  have been refused.")
    say("")
    say("Permission check, asked of Jira for this story and this identity:")
    say("  may see the story        (BROWSE_PROJECTS): %s" % ("yes" if permissions["BROWSE_PROJECTS"] else "no"))
    say("  may comment on the story (ADD_COMMENTS):    %s" % ("yes" if permissions["ADD_COMMENTS"] else "no"))
    if proposal["visibility"]["kind"] == "role":
        say("  the project has the role %s (role id %s): yes" % (json.dumps(proposal["visibility"]["name"]), proposal["visibility"]["id"]))
    say("Duplicate check, made against Jira just now: the story has %d comment%s that this identity can see. Each was"
        % (proposal["comments"], "" if proposal["comments"] == 1 else "s"))
    say("  compared with the text. A comment restricted to others would not be among them.")
    say("  With the same text, by this identity: %d%s." % (len(proposal["same_mine"]), "".join(
        " (comment id %s, seen by %s)" % (c["id"], "everyone who can see the story" if c["visibility"]["kind"] == "everyone" else "the role %s" % json.dumps(c["visibility"].get("name", "?")))
        for c in proposal["same_mine"])))
    say("  With the same text, by someone else:  %d%s." % (len(proposal["same_others"]), " (comment id %s)" % ", ".join(proposal["same_others"]) if proposal["same_others"] else ""))
    say("Where Jira cannot check: its request to add a comment has no 'only if there is no such comment' condition.")
    say("  The confirmation reads the comments again just before writing and stops if this comment is there by then.")
    say("")
    say("Snapshot of the story and its comments as Jira returned them, before the preview: %s" % before)
    say("Snapshot of the story and its comments as Jira returned them, after the preview:  %s" % after)
    say("The two are the same. Jira is unchanged, as far as two reads of the story and its comments can show. A snapshot")
    say("  is of the story's last-updated time, project and security level, and of every comment this identity can see.")
    requests_line(conn)
    say("")
    if there:
        say("This identity has already put this comment on the story, with this visibility: comment id %s." % ", ".join(there))
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
    say("Nothing has been written. To add this comment, a person who has read this preview confirms it by its")
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
    if shown_before["issue_id"] != now["issue_id"]:
        differs.append("it names a different story")
    if shown_before["text"] != now["text"] or shown_before["source_sha"] != now["source_sha"]:
        differs.append("the text is not the text the preview showed")
    if shown_before["source"] != now["source"]:
        differs.append("the text comes from a different file")
    if not same_visibility(shown_before["visibility"], now["visibility"]):
        differs.append("the visibility asked for is not the one the preview showed")
    elif shown_before["visibility"].get("id") != now["visibility"].get("id"):
        moved.append("the project role of that name is now a different role")
    if shown_before["project_id"] != now["project_id"]:
        moved.append("the story is now in a different project (project id %s)" % now["project_id"])
    if shown_before["project_type"] != now["project_type"]:
        moved.append("the kind of project changed")
    if shown_before["allowlist"] != now["allowlist"]:
        differs.append("the allowlist file is not the one the preview used")
    if shown_before["security"] != now["security"]:
        moved.append("the story's security level changed, so who can see it changed")
    if already_there(now):
        moved.append("this identity has put this comment on the story since the preview (comment id %s)" % ", ".join(already_there(now)))
    return differs, moved


def twins_of(comments, proposal, me):
    """The identifiers of the comments with this text and this visibility by this identity: the duplicate check's own rule."""
    return [c.get("id") for c in comments if text_of(c.get("body"))[0] == proposal["text"] and (c.get("author") or {}).get("accountId") == me
            and same_visibility(visibility_of(c), proposal["visibility"])]


def jira_said(body):
    """What Jira's refusal said, as other people's text: quoted, cut short, with unseen characters taken out."""
    messages = body.get("errorMessages") if isinstance(body, dict) else None
    texts = [m for m in messages if isinstance(m, str)] if isinstance(messages, list) else []
    return " Jira's own words, which are not this workflow's: %s." % json.dumps(UNSEEN.sub(" ", " / ".join(texts))[:200]) if texts else ""


def read_back(conn, issue_id, comment_id, proposal, me):
    """Reads one comment by its identifier and compares it with what was previewed. Returns a list of (what, ok)."""
    status, _, comment = conn.get("/rest/api/3/issue/%s/comment/%s" % (issue_id, comment_id))
    if status != 200 or not isinstance(comment, dict):
        return None, [("Jira returned the comment when asked for it by its identifier (status %d)" % status, False)]
    text, odd = text_of(comment.get("body"))
    seen = visibility_of(comment)
    checks = [("the text read back is the text previewed, character for character (%d characters, sha256 %s)"
               % (len(text or ""), hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:16]), text == proposal["text"]),
              ("it is plain text, with nothing added: %s" % (", ".join(sorted(set(odd))) if odd else "no formatting, links or mentions"), not odd),
              ("its author is this identity", (comment.get("author") or {}).get("accountId") == me),
              ("its visibility is the one previewed: %s" % ("everyone who can see the story" if seen["kind"] == "everyone" else
                                                           "the role %s" % json.dumps(seen["name"]) if seen["kind"] == "role" else "a restriction this workflow does not know"),
               same_visibility(seen, proposal["visibility"]))]
    return text, checks


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
                      "used again. Read the story's comments, then make a new preview" % (code, status))

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
        raise Refused("the change is not the one that was previewed: it names a different story. Make a new "
                      "preview and read it")
    allowed = load_allowlist(args.allowlist)
    site = site_fingerprint(conn.host)
    if site != before["site"]:
        raise Refused("this is not the Jira site the preview was made against. Make a new preview and read it")
    issue_id = before["issue_id"]
    me = read_myself(conn)
    permissions = read_permissions(conn, issue_id)
    issue = read_issue(conn, issue_id)
    comments = read_comments(conn, issue_id)  # the last read before the write
    proposal = build_proposal(conn, site, allowed, args.allowlist, issue, permissions, comments, me, change)
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
    say("  the change file and the text file ask for exactly what the preview showed: ok")
    say("  the project is on the sandbox allowlist for this site: ok")
    say("  Jira says this identity may comment on the story: ok")
    say("  the story's %d comments, read just before the write, hold no such comment by this identity: ok" % len(comments))
    say("")

    if now_utc() + datetime.timedelta(minutes=args.pretend_minutes_later or 0) - made > datetime.timedelta(minutes=LIMIT_MINUTES):
        raise Refused("this preview passed its limit of %d minutes while the checks were being made. Make a new preview and read it" % LIMIT_MINUTES)
    try:
        os.makedirs(os.path.join(args.state, "sending"), exist_ok=True)
        os.close(os.open(os.path.join(args.state, "sending", code), os.O_CREAT | os.O_EXCL | os.O_WRONLY))
    except FileExistsError:
        raise Refused("another run is confirming the preview %s at this moment, or one began and did not finish. It cannot be "
                      "used again. Read the story's comments, then make a new preview" % code)
    record["state"] = "sending"
    save_json(record_path, record)
    try:
        status, _, body = conn.post_comment(issue_id, proposal["text"], proposal["visibility"])
    except NeedsLooking:
        record["state"] = "sent, answer not received"
        save_json(record_path, record)
        raise
    written_at = now_utc().strftime(TIME_FORMAT)
    comment_id = body.get("id") if isinstance(body, dict) else None
    if status not in (200, 201) or not ident(comment_id):
        record["state"] = "sent, Jira answered %d" % status
        save_json(record_path, record)
        after = read_comments(conn, issue_id)
        new = [c for c in after if text_of(c.get("body"))[0] == proposal["text"] and (c.get("author") or {}).get("accountId") == me]
        if status >= 400 and not new and len(after) == len(comments):
            raise NotWritten("Jira answered %d to the write.%s Read back afterwards, the story has the %d comments it had "
                             "before and none is this one, so nothing was written. The preview cannot be used again" % (status, jira_said(body), len(comments)))
        raise NeedsLooking("Jira answered %d to the write and gave no usable comment identifier. Read back afterwards, the "
                           "story has %d comments where it had %d, and %d with this text by this identity"
                           % (status, len(after), len(comments), len(new)))

    confirmed_at = confirmed.strftime(TIME_FORMAT)
    result = {"fingerprint": record["fingerprint"], "issue_key": proposal["key"], "issue_id": issue_id, "comment_id": comment_id,
              "project_key": proposal["project_key"], "project_id": proposal["project_id"], "site_fingerprint": site,
              "confirmed_by": name, "confirmed_at": confirmed_at, "written_at": written_at, "preview_made_at": record["made_at"],
              "text": proposal["text"], "text_sha": proposal["text_sha"], "source": proposal["source"], "source_sha": proposal["source_sha"],
              "visibility": proposal["visibility"], "security": proposal["security"], "read_back": None}
    os.makedirs(os.path.join(args.state, "written"), exist_ok=True)
    save_json(os.path.join(args.state, "written", code + ".json"), result)   # kept at once, so that the comment's identifier is not lost
    record["state"] = "written"
    save_json(record_path, record)
    say("WRITTEN to Jira: one comment on story %s. Jira answered %d and gave it the comment id %s." % (proposal["key"], status, comment_id))
    say("The confirmation and the write happened in this one run of the command.")
    say("")
    say("Read back from Jira after the write, by that comment id:")
    _, checks = read_back(conn, issue_id, comment_id, proposal, me)
    for what, ok in checks:
        say("  %s: %s" % (what, "yes" if ok else "NO"))
    after = read_comments(conn, issue_id)
    twins = twins_of(after, proposal, me)
    say("  comments on the story with this text and this visibility by this identity, counted after the write: %d%s"
        % (len(twins), "" if len(twins) == 1 else ". MORE THAN ONE: comment ids %s" % ", ".join(str(t) for t in twins)))

    result["read_back"] = [[what, ok] for what, ok in checks]
    save_json(os.path.join(args.state, "written", code + ".json"), result)

    say("")
    say("RESULT RECORD")
    for line in result_lines(result):
        say("  " + line)
    if args.result:
        text = "\n".join(["# Result record: one comment added to one Jira story", ""] + ["- " + line for line in result_lines(result)]) + "\n"
        os.makedirs(os.path.dirname(os.path.abspath(args.result)), exist_ok=True)
        with open(args.result, "w", encoding="utf-8") as f:
            f.write(text.replace(conn.host, SITE_MARK))
        say("")
        say("The result record was also saved as Markdown where --result said.")
    if not all(ok for _, ok in checks):
        raise NeedsLooking("Jira accepted the write, and the comment does not read back as previewed")
    if len(twins) != 1:
        raise NeedsLooking("the comment was added, and the story now has %d comments with this text by this identity" % len(twins))
    return 0


def result_lines(result):
    visibility = result["visibility"]
    return ["Issue key: %s" % result["issue_key"],
            "Issue id: %s (this identifies the story; a key can change)" % result["issue_id"],
            "Identifier of what was created: Jira comment id %s, on that issue" % result["comment_id"],
            "Target project: %s (project id %s), on the sandbox allowlist" % (result["project_key"], result["project_id"]),
            "Jira site: %s, site fingerprint %s" % (SITE_MARK, result["site_fingerprint"]),
            "Visibility: %s" % ("everyone who can see the story; no restriction on the comment" if visibility["kind"] == "everyone"
                                else "only the project role %s (role id %s)" % (json.dumps(visibility["name"]), visibility.get("id"))),
            "Story's security level when written: %s" % ("Jira did not say" if result["security"] == "?" else json.dumps(result["security"]) if result["security"] else "none"),
            "Text: %d characters, sha256 %s, from the file %s (file sha256 %s)" % (len(result["text"]), result["text_sha"], result["source"], result["source_sha"]),
            "Read back after the write: %s" % ("as previewed: same text, plain, by this identity, same visibility"
                                               if result["read_back"] and all(ok for _, ok in result["read_back"]) else "NOT as previewed, or not read back. See the run's output"),
            "Written at: %s" % result["written_at"],
            "Confirmed by: %s, at %s" % (result["confirmed_by"], result["confirmed_at"]),
            "Preview: fingerprint %s, made %s" % (result["fingerprint"][:12], result["preview_made_at"]),
            "To reverse: delete comment %s on the story in Jira, by hand. This workflow does not delete. Emails Jira "
            "sent about the comment cannot be taken back" % result["comment_id"]]


# ---------------------------------------------------------------- check


def cmd_check(args, conn):
    code = (args.fingerprint or "").strip().lower()
    if len(code) != 12 or any(ch not in "0123456789abcdef" for ch in code):
        raise Refused("a fingerprint is 12 characters, each 0 to 9 or a to f")
    try:
        with open(os.path.join(args.state, "written", code + ".json"), encoding="utf-8") as f:
            result = json.load(f)
        proposal = {"text": result["text"], "visibility": result["visibility"]}
        issue_id, comment_id = result["issue_id"], result["comment_id"]
    except FileNotFoundError:
        raise Refused("there is no record of a write for the fingerprint %s" % code)
    except (ValueError, KeyError, TypeError):
        raise Refused("the record of the write %s cannot be read" % code)
    if site_fingerprint(conn.host) != result["site_fingerprint"]:
        raise Refused("this is not the Jira site the comment was written to")
    change = read_change(args.change)
    me = read_myself(conn)
    issue = read_issue(conn, issue_id)
    text, checks = read_back(conn, issue_id, comment_id, proposal, me)
    comments = read_comments(conn, issue_id)
    twins = twins_of(comments, proposal, me)

    say("COMMENT CHECK for the write of preview %s. Nothing is written by this command." % code)
    say("")
    say("Jira site:  https://%s  (site fingerprint %s)" % (conn.host, result["site_fingerprint"]))
    say("Story:      %s (issue id %s), in project %s (project id %s)." % (issue["key"], issue_id, issue["fields"]["project"]["key"], issue["fields"]["project"]["id"]))
    say("Comment:    comment id %s, the identifier Jira gave when it was written." % comment_id)
    say("")
    say("The text the preview showed, between the bars:")
    show_text(result["text"])
    say("The text read back from Jira now, between the bars:")
    show_text(UNSEEN.sub("?", text) if text is not None else "(could not be read)")
    say("  (A character that cannot be seen, in what Jira returned, is shown as a question mark.)" if text and UNSEEN.search(text) else "")
    say("")
    for what, ok in checks:
        say("  %s: %s" % (what, "yes" if ok else "NO"))
    say("  WHO CAN SEE IT, as the preview showed: %s" % shown_visibility(result["visibility"], result["issue_key"], result["security"]))
    now_level = security_of(issue)
    say("  the story's security level is what it was when the comment was written (%s): %s"
        % ("Jira did not say" if now_level == "?" else json.dumps(now_level) if now_level else "none", "yes" if now_level == result["security"] else "NO"))
    say("  comments on the story with this text and this visibility by this identity: %d of the %d this identity can see%s"
        % (len(twins), len(comments), "" if len(twins) == 1 else ". NOT ONE: comment ids %s" % (", ".join(str(t) for t in twins) or "none")))
    say("")
    say("Where the text came from, as the preview stated: the file %s beside the change file, sha256 %s." % (result["source"], result["source_sha"]))
    same_file = change["source"] == result["source"] and change["source_sha"] == result["source_sha"]
    say("  That file today: %s" % ("the same name and the same sha256, so it still holds the text that was sent." if same_file
                                   else "NOT the same. It has been changed since, or the change file names another."))
    say("  Who or what put the text in that file is not known to this workflow. It did not write the file and did not")
    say("  take the text from Jira.")
    say("")
    requests_line(conn)
    ok = all(good for _, good in checks) and len(twins) == 1 and now_level == result["security"]
    say("")
    say("FOUND: the comment is on the story as previewed." if ok else "NOT AS PREVIEWED: see the lines marked NO above.")
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
                raise NeedsLooking("the write was sent, and a step after it could not be done: %s. The comment may be on the story" % refusal)
            return refused(refusal)
        except NeedsLooking:
            raise
        except Exception as failure:  # nothing may hide what was already sent
            if posted():
                raise NeedsLooking("the write was sent, and the program then failed (%s). The comment may be on the story" % type(failure).__name__)
            return refused("the program failed before anything was sent (%s)" % type(failure).__name__)
    except NeedsLooking as problem:
        say("")
        say("A PERSON NEEDS TO LOOK: %s." % problem)
        say("Do not run this again before reading the story's comments in Jira.")
        return 2


def main(argv=None):
    parser = argparse.ArgumentParser(description="Preview, then confirm, one comment on one Jira story. Then check it.")
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("preview", "confirm", "check"):
        sub = commands.add_parser(command)
        sub.add_argument("--source", choices=("live", "fake"), required=True)
        sub.add_argument("--change", required=True, help="the change file")
        sub.add_argument("--state", required=True, help="the folder where previews and write records are kept")
        sub.add_argument("--log", help="also save the output here, with the site's address removed")
        if command != "check":
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
    text = "\n".join(LINES)
    if any(secret and secret in text for secret in secrets):
        print("STOPPED: a credential was found in the output, so the output was not shown or saved.")
        return 2 if conn and any(method == "POST" for method, _ in conn.sent) else 1
    print(text)
    if secrets:
        note = ("\nThe output above was searched for the API token, the account's email address and their encoded\n"
                "form: none found.")
        print(note)
        text += "\n" + note
    if args.log:
        host = conn.host if conn else ""
        saved = text.replace("https://" + host, SITE_MARK).replace(host, SITE_MARK) if host else text
        os.makedirs(os.path.dirname(os.path.abspath(args.log)), exist_ok=True)
        with open(args.log, "w", encoding="utf-8") as f:
            f.write(saved + "\n")
    return code


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    sys.exit(main())
