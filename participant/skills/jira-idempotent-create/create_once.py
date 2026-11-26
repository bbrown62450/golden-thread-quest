#!/usr/bin/env python3
"""Creates one Jira task from one draft, and is built so that running it again, or interrupting it anywhere, does not
create a second one. That holds on one computer, with the draft's record kept, the label left on the task, and
Jira's search no more than a minute and a half behind. Outside that it can fail; see "What this cannot do".

    create_once.py preview --source live|fake --draft DRAFT.json --allowlist FILE --state DIR
    create_once.py confirm --source live|fake --draft DRAFT.json --allowlist FILE --state DIR \
                           --fingerprint CODE --confirmed-by NAME
    create_once.py resolve --source live|fake --draft DRAFT.json --state DIR
    create_once.py check   --source live|fake --draft DRAFT.json --state DIR

A draft names the project and gives the title:    {"project": "SAND", "summary": "Tidy the export folder"}

THE KEY. The first time a draft is previewed, a key is made for it: "gtq-key-" and 16 random characters. It is saved
in DIR/intents/, in a record named after the draft, BEFORE anything is asked of Jira. Every later run reads it from
there. It is not worked out from the title, so correcting the title does not change it. The key is sent to Jira as
a LABEL, inside the request that creates the task, so the task never exists without it. A label is the one place
on a Jira issue that can be searched for exactly.

THE RECORD of a draft is always in one of five states:

    new        nothing has been sent, or Jira refused what was sent and created nothing
    sending    written just BEFORE the request to create is sent. If a later run finds this state, an earlier run
               ended without saying what happened. The outcome is NOT KNOWN
    uncertain  the request was sent and no usable answer came back. The outcome is NOT KNOWN
    released   NOT KNOWN was looked into: Jira was searched for the key and returned nothing twice, each time 60
               seconds or more after the request ended and the two 30 seconds or more apart. A new preview is allowed
    linked     the task exists and its issue id and key are recorded here. Nothing will be created again

preview   reads Jira and writes nothing to it. It has no way to send a write.
          linked: says so, reads the task back, and issues no fingerprint.
          sending or uncertain: REFUSED. Run resolve first.
          Otherwise it searches Jira for the key. Found: no fingerprint, run resolve. Not found: a preview, with a
          fingerprint a person can confirm.

confirm   creates the task of one preview, named by its fingerprint, and only if all of this holds at that moment:
            a fingerprint and the confirming person's name are given;
            the saved preview is unaltered, unused and at most 15 minutes old;
            the draft still asks for exactly what the preview showed;
            the project is on the sandbox allowlist, for this Jira site;
            Jira still says this identity may create issues in the project;
            Jira, searched again just before the write, returns no issue carrying the key.
          The write is sent once and never sent again by the same run.
            Jira answers with the new issue: recorded at once (linked), then read back.
            Jira answers 400, 401, 403 or 404, and a search for the key finds nothing: nothing was written (new).
            Anything else, no answer included: NOT KNOWN (uncertain). It says so and stops.

resolve   the rerun after an interruption. It searches Jira for the key and never creates anything.
            exactly one issue carries the key, in the project the write was sent to: it is recorded (linked);
            none: said to be "not found YET" until two searches have found nothing, each 60 seconds or more after
            the request ended and the two 30 seconds or more apart. An empty answer counts only if Jira also says
            this identity can see the project and a search there returns something. Then the record is released,
            and creating needs a NEW preview and a NEW confirmation from a person. It will carry the SAME key, so if
            the first task shows up later, two issues carry one key and `check` says so. "Not found" by a search is
            not proof: Jira's search can be behind;
            more than one, or one in another project: stops. A PERSON NEEDS TO LOOK. Nothing is recorded;
            THE SEARCH ITSELF FAILS (no answer, an error, an answer that cannot be read or is cut short): stops.
            Nothing is created, the record is left as it was, and it says how to look by hand.

check     reads a linked task back by its issue id, says whether it still carries the key and whether its title
          has been changed since, and searches for the key. It writes nothing.

What this cannot do.
    Jira's request to create an issue has no "only if there is none with this label" condition. Between the last
    search and the write there is a moment in which another run could create the same task. On THIS computer one
    run at a time may confirm a draft: a claim file, made with "create only if absent", is held for the length of
    the run. Nothing stops a run on another computer with a copy of the state folder.
    The draft's record is found by the draft's FILE NAME, in the state folder given. Rename the draft, or give
    another state folder, and it is a new draft with a new key.
    A confirmation is a fingerprint and a name given on the command line. Against a real Jira the command must
    also be started from a terminal. That keeps out a program with no terminal. It does not prove who typed.
    The waits are measured by this computer's clock. A clock moved forward shortens them.
    Jira's search can be behind what Jira holds. A search made just after a create may not show it. How far behind
    is not known to this workflow. Sixty seconds is a choice, not a measurement.
    If the local record is lost after the task was created, the key is lost with it, and a new preview makes a new
    key. The preview's title check is then the only thing that points the earlier task out, and it only points.
    Anyone who can edit the task can remove the label. The task is then not found by its key.

--interrupt-at POINT is for tests: confirm ends at that point as if it had been killed, and records nothing after it.
    before-send   the record says "sending" and the request has not gone
    after-send    Jira has answered and nothing has been recorded
    after-record  the task is recorded, and has not been read back
--pretend-minutes-later N (confirm) moves "now" forward for tests. It can only make a preview older, so only refuse.
--pretend-seconds-later N (resolve) does the same, and is REFUSED against a real Jira: it would shorten the wait.
--log FILE saves the output with the site's address replaced by a marker.
--result FILE saves the result record as Markdown, the same way.

For a live run the connection comes from the environment variables JIRA_BASE_URL, JIRA_EMAIL and JIRA_API_TOKEN. None
is stored. The output is searched for the token, the email address and their encoded form before it is shown.

Exit codes: 0 done; 1 refused or not yet, nothing written by this run; 2 a person needs to look;
            3 stopped on purpose by --interrupt-at.
"""
import argparse
import base64
import datetime
import hashlib
import http.client
import json
import os
import re
import secrets as random_source
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

LIMIT_MINUTES = 15
WAIT_SECONDS = 60      # how long after a request ended an empty search starts to count
GAP_SECONDS = 30       # how far apart the two empty searches that count must be
TIMEOUT_SECONDS = 30   # how long a request waits for Jira's answer
CLAIM_MINUTES = 10     # how long a run may hold a draft before another run may take over
MAX_SUMMARY = 200
TYPE_NAME = "Task"
KEY_PREFIX = "gtq-key-"
KEY = re.compile(r"gtq-key-[0-9a-f]{16}")
REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,60}")
TIME_FORMAT = "%Y-%m-%d %H:%M:%S UTC"
SITE_MARK = "[site address removed]"
ISSUE_FIELDS = "summary,labels,issuetype,project,created"
WRITE_PATH = "/rest/api/3/issue"
SEARCH_PATH = "/rest/api/3/search/jql"
REFUSALS = (400, 401, 403, 404)   # answers that mean Jira did not take the write. Any other failure is not taken to mean that
POINTS = ("before-send", "after-send", "after-record")
UNSEEN = re.compile("[\\x00-\\x09\\x0b-\\x1f\\x7f-\\xa0\\u00ad\\u034f\\u061c\\u115f\\u1160\\u200b-\\u200f\\u2028\\u2029\\u202a-\\u202e\\u2060-\\u2069\\u2800\\u3164\\ufeff\\U000e0000-\\U000e007f]")

# A title that matches one of these is refused. They are patterns: they miss secrets of other shapes.
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
# Pointed out, and not refused.
PRIVATE = (
    ("an email address", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z0-9.-]+")),
    ("a web address", re.compile(r"(?i)\b(?:https?://|www\.)\S+")),
    ("what may be a telephone number", re.compile(r"(?<![0-9])\+?[0-9][0-9 ().-]{7,}[0-9](?![0-9])")),
    ("an @name, which is sent as text and mentions nobody", re.compile(r"(?<![A-Za-z0-9._%+-])@[A-Za-z0-9_.-]+")),
    ("a word that marks something as private", re.compile(r"(?i)\b(?:confidential|private|internal only|do not share|not for customers?|under nda)\b")),
)

LINES = []      # each is (what is shown on screen, what is saved)
PENDING = {}    # the result record, written by main() only after the output has been searched for credentials


class Refused(Exception):
    """Nothing was written by this run. The message is the reason."""


class NotWritten(Refused):
    """A write was sent, and Jira's answer and a search afterwards show that nothing was written."""


class NeedsLooking(Exception):
    """A person needs to look. The message says what is and is not known."""


class SearchFailed(Exception):
    """A search did not give an answer that can be relied on. The message says how."""


class Interrupted(Exception):
    """The test switch --interrupt-at ended the run here."""


def say(text="", saved=None):
    """One line of output. `saved` is what is kept in a saved log, where that differs from what is shown on screen."""
    LINES.append((text, text if saved is None else saved))


def quoted(text, limit=60):
    return json.dumps(UNSEEN.sub("?", str(text))[:limit], ensure_ascii=False)


def plural(count, word):
    return "%d %s%s" % (count, word, "" if count == 1 else "s")


# ---------------------------------------------------------------- the connection


class Connection:
    """Every request goes through here and is written down. Only `confirm` is given a way to write."""

    def __init__(self, get, post, host):
        self._get, self._post, self.host = get, post, host
        self.sent = []

    def posted(self):
        return any(method == "POST" for method, _ in self.sent)

    def get(self, path, params=None):
        self.sent.append(("GET", path))
        return self._get(path, params)

    def post_issue(self, project_id, type_id, summary, key):
        if self._post is None:
            raise Refused("this command has no way to write")
        if not (ident(project_id) and ident(type_id) and KEY.fullmatch(key)):
            raise Refused("a write names the project and the issue type by their ids, and carries the key")
        body = {"fields": {"project": {"id": project_id}, "issuetype": {"id": type_id}, "summary": summary, "labels": [key]}}
        self.sent.append(("POST", WRITE_PATH))
        return self._post(WRITE_PATH, None, body)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def make_live(may_write, opener=None):
    base = os.environ.get("JIRA_BASE_URL", "").rstrip("/")
    email, token = os.environ.get("JIRA_EMAIL", ""), os.environ.get("JIRA_API_TOKEN", "")
    for name, value in (("JIRA_BASE_URL", base), ("JIRA_EMAIL", email), ("JIRA_API_TOKEN", token)):
        if not value:
            raise Refused("the environment variable %s is not set" % name)
    host = urllib.parse.urlparse(base).hostname or ""
    if not host or base != "https://" + host:
        raise Refused("JIRA_BASE_URL must be https:// and the site's name, with no port, path or sign-in in it")
    encoded = base64.b64encode(("%s:%s" % (email, token)).encode("utf-8")).decode("ascii")
    opener = opener or urllib.request.build_opener(NoRedirect)

    def send(method, path, params, body):
        url = base + path + ("?" + urllib.parse.urlencode(params) if params else "")
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = urllib.request.Request(url, data=data, method=method)
        request.add_header("Authorization", "Basic " + encoded)
        request.add_header("Accept", "application/json")
        if data is not None:
            request.add_header("Content-Type", "application/json")
        try:
            with opener.open(request, timeout=TIMEOUT_SECONDS) as response:
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
        labels = fields.get("labels") if isinstance(fields, dict) else None
        if (path != WRITE_PATH or params or set(body) != {"fields"} or set(fields) != {"project", "issuetype", "summary", "labels"}
                or not isinstance(labels, list) or len(labels) != 1 or not isinstance(labels[0], str) or not KEY.fullmatch(labels[0])):
            raise Refused("the only write this workflow sends is one new task: a project, an issue type, a title and the key as its one label")
        return send("POST", path, params, body)

    return Connection(get, post if may_write else None, host), [token, email, encoded]


def site_fingerprint(host):
    return hashlib.sha256(host.lower().encode("utf-8")).hexdigest()[:16]


def unreachable(err):
    return "could not reach Jira (%s)" % type(getattr(err, "reason", err)).__name__


def read(conn, path, params=None):
    """A read that is not a search. If Jira cannot be reached, nothing is assumed."""
    try:
        return conn.get(path, params)
    except (OSError, TimeoutError) as err:
        if conn.posted():
            raise NeedsLooking("after the write was sent, a read failed: %s" % unreachable(err))
        raise Refused(unreachable(err))


# ---------------------------------------------------------------- local files


def ident(value):
    return isinstance(value, str) and value.isascii() and value.isdigit() and len(value) <= 20


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0, tzinfo=None)


def stamp(moment):
    return moment.strftime(TIME_FORMAT)


def parse(text):
    return datetime.datetime.strptime(text, TIME_FORMAT)


def canonical(data):
    return json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def save_json(path, data):
    """Written whole or not at all: to a second file, pushed to the disk, then renamed over the first."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = "%s.%d.tmp" % (path, os.getpid())      # a name of this run's own, so that two runs never share one
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    try:                                           # and the folder, so that the new name survives a loss of power
        folder = os.open(os.path.dirname(path), os.O_RDONLY)
        os.fsync(folder)
        os.close(folder)
    except OSError:
        pass


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
        if not (isinstance(site, str) and re.fullmatch(r"[0-9a-f]{16}", site) and ident(project)):
            raise Refused("an entry in the sandbox allowlist is not a site fingerprint and a project id")
        allowed.add((site, project))
    with open(path, "rb") as f:
        sha = hashlib.sha256(f.read()).hexdigest()
    return allowed, "the file %s, sha256 %s, which lists %s" % (os.path.basename(path), sha[:16], plural(len(allowed), "project"))


def check_summary(text):
    """Refuses a title this workflow will not send. Returns what to point out to the person confirming."""
    if not isinstance(text, str) or not text:
        raise Refused("the summary, which is the task's title, is empty")
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


def read_draft(path):
    name = os.path.basename(path)
    if not name.endswith(".json") or not REF.fullmatch(name[:-5]):
        raise Refused("a draft is a file whose name is letters, digits and dashes, ending in .json. Its record is kept under that name")
    draft = read_json(path, "draft")
    if not isinstance(draft, dict) or set(draft) != {"project", "summary"}:
        raise Refused("the draft must have exactly 'project' and 'summary'")
    if not isinstance(draft["project"], str) or not REF.fullmatch(draft["project"]):
        raise Refused("the project is given by its key or its project id: letters, digits and dashes only")
    pointed_out = check_summary(draft["summary"])
    with open(path, "rb") as f:
        sha = hashlib.sha256(f.read()).hexdigest()
    folder = hashlib.sha256(os.path.dirname(os.path.realpath(path)).encode("utf-8")).hexdigest()[:16]
    return {"name": name[:-5], "project": draft["project"], "summary": draft["summary"], "source": name, "source_sha": sha, "folder": folder, "pointed_out": pointed_out}


def same_title(a, b):
    plain = lambda text: " ".join(unicodedata.normalize("NFKC", text).split()).casefold()  # noqa: E731
    return isinstance(a, str) and isinstance(b, str) and plain(a) == plain(b)


def sha_of(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------- the record of one draft


def record_path(state, name):
    return os.path.join(state, "intents", name + ".json")


def load_record(state, draft, make):
    """The draft's record. With `make`, a draft that has none is given one, with a new key, saved before anything else."""
    path = record_path(state, draft["name"])
    if not os.path.exists(path):
        if not make:
            raise Refused("this draft has no record in the state folder: it has never been previewed, so nothing was ever sent for it")
        record = {"key": KEY_PREFIX + random_source.token_hex(8), "draft": draft["source"], "folder": draft["folder"], "made_at": stamp(now_utc()),
                  "status": "new", "attempts": [], "not_found": [], "issue": None}
        save_json(path, record)
        return path, record, True
    try:
        with open(path, encoding="utf-8") as f:
            record = json.load(f)
        ok = (KEY.fullmatch(record["key"]) and record["status"] in ("new", "sending", "uncertain", "released", "linked")
              and isinstance(record["attempts"], list) and isinstance(record["not_found"], list)
              and (record["status"] != "linked" or (ident(record["issue"]["id"]) and REF.fullmatch(record["issue"]["key"]))))
    except (ValueError, KeyError, TypeError):
        ok = False
    if not ok:
        raise Refused("the record of this draft in the state folder cannot be read. It holds the key, so nothing is done "
                      "without it. A person looks at the file and at Jira")
    if record.get("folder") != draft["folder"]:
        raise Refused("the record named %s in this state folder belongs to a draft file in another folder. Two drafts with one "
                      "file name cannot share a state folder: give this one another name" % draft["name"])
    return path, record, False


def claim_draft(state, name):
    """Only one run at a time may confirm a draft. The claim is a file made with 'create only if absent'."""
    path = os.path.join(state, "claims", name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    for _ in range(2):
        try:
            handle = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(handle, stamp(now_utc()).encode("ascii"))
            os.close(handle)
            return path
        except FileExistsError:
            try:
                with open(path, encoding="ascii") as f:
                    since = parse(f.read().strip())
            except (OSError, ValueError):
                since = now_utc()
            if now_utc() - since <= datetime.timedelta(minutes=CLAIM_MINUTES):
                raise Refused("another run is confirming this draft at this moment (it began at %s). If no run is, that run was "
                              "killed: wait until %d minutes after that time and try again. The draft's record will say what it sent"
                              % (stamp(since), CLAIM_MINUTES))
            try:
                os.remove(path)        # an abandoned claim. Whoever makes the file next has it
            except OSError:
                pass
    raise Refused("another run took this draft at the same moment")


# ---------------------------------------------------------------- reading Jira


def read_project(conn, ref):
    status, _, body = read(conn, "/rest/api/3/project/%s" % ref)
    if status == 401:
        raise Refused("Jira rejected the credentials (401). Check JIRA_EMAIL and JIRA_API_TOKEN")
    if status == 404:
        raise Refused("Jira answered 404 for the project. It does not exist, or this identity is not permitted to see it")
    types = body.get("issueTypes") if status == 200 else None
    if not (isinstance(types, list) and ident(body.get("id")) and isinstance(body.get("key"), str) and REF.fullmatch(body["key"])):
        raise Refused("Jira's answer for the project could not be used (status %d)" % status)
    found = [t for t in types if isinstance(t, dict) and t.get("name") == TYPE_NAME and t.get("subtask") is False and ident(t.get("id"))]
    if len(found) != 1:
        raise Refused("the project has %d issue types named %s that are not subtasks. This workflow needs exactly one" % (len(found), TYPE_NAME))
    return {"id": body["id"], "key": body["key"], "type_id": found[0]["id"]}


def read_permissions(conn, project_id):
    names = ("BROWSE_PROJECTS", "CREATE_ISSUES")
    status, _, body = read(conn, "/rest/api/3/mypermissions", {"projectId": project_id, "permissions": ",".join(names)})
    found = body.get("permissions") if status == 200 else None
    if not isinstance(found, dict):
        raise Refused("Jira did not answer the permission check (status %d), so nothing is assumed" % status)
    return {name: (found.get(name) or {}).get("havePermission") is True for name in names}


def search(conn, jql, fields, limit=50):
    """Issues Jira returns for a search. Raises SearchFailed unless the answer is whole and readable."""
    try:
        status, _, body = conn.get(SEARCH_PATH, {"jql": jql, "fields": fields, "maxResults": limit})
    except (OSError, TimeoutError) as err:
        raise SearchFailed("no answer came back (%s)" % type(getattr(err, "reason", err)).__name__)
    if status != 200:
        raise SearchFailed("Jira answered %d" % status)
    issues = body.get("issues") if isinstance(body, dict) else None
    if not isinstance(issues, list) or any(not isinstance(i, dict) or not ident(i.get("id")) or not isinstance(i.get("fields"), dict) for i in issues):
        raise SearchFailed("Jira's answer was not a list of issues")
    if body.get("nextPageToken") or body.get("isLast") is False or len(issues) >= limit:
        raise SearchFailed("Jira's answer was cut short: there are more results than it gave")
    return issues


def shown_key(issue):
    """An issue's key as Jira gave it, if it has the shape of a key. Otherwise a question mark: it is other people's text."""
    key = issue.get("key")
    return key if isinstance(key, str) and REF.fullmatch(key) else "?"


def can_be_seen(conn, project_id):
    """Before an EMPTY search is believed: this identity can still see the project, and a search there returns something.
    An identity that has lost its access gets empty answers too, and those say nothing about what exists."""
    try:
        status, _, body = conn.get("/rest/api/3/mypermissions", {"projectId": project_id, "permissions": "BROWSE_PROJECTS"})
    except (OSError, TimeoutError) as err:
        raise SearchFailed("the permission check got no answer (%s)" % type(getattr(err, "reason", err)).__name__)
    found = body.get("permissions") if status == 200 and isinstance(body, dict) else None
    if not isinstance(found, dict) or (found.get("BROWSE_PROJECTS") or {}).get("havePermission") is not True:
        raise SearchFailed("an empty answer cannot be believed: Jira does not now say that this identity may see project id %s (status %d)" % (project_id, status))
    try:
        status, _, body = conn.get(SEARCH_PATH, {"jql": "project = %s ORDER BY created DESC" % project_id, "fields": "created", "maxResults": 1})
    except (OSError, TimeoutError) as err:
        raise SearchFailed("the search of the project got no answer (%s)" % type(getattr(err, "reason", err)).__name__)
    issues = body.get("issues") if status == 200 and isinstance(body, dict) else None
    if not isinstance(issues, list) or not issues:
        raise SearchFailed("an empty answer cannot be believed: a search of project id %s for any issue at all returned nothing (status %d)" % (project_id, status))


def find_by_key(conn, key):
    """Every issue carrying the key, anywhere this identity can see: [{"id", "key", "project_id"}]."""
    if not KEY.fullmatch(key):
        raise SearchFailed("the key is not a key")
    found = []
    for issue in search(conn, 'labels = "%s"' % key, "labels,project"):
        labels, project = issue["fields"].get("labels"), issue["fields"].get("project")
        if not isinstance(labels, list) or key not in labels or not isinstance(project, dict) or not ident(project.get("id")):
            raise SearchFailed("Jira returned an issue that does not show the key among its labels")
        found.append({"id": issue["id"], "key": shown_key(issue), "project_id": project["id"]})
    return found


def find_by_title(conn, project_id, summary):
    """Issues in the project with this title, capitals and spacing aside: a list, or None if it could not be checked."""
    words = re.findall(r"[A-Za-z0-9]+", summary)
    if not words:
        return None
    try:
        issues = search(conn, 'project = %s AND summary ~ "%s"' % (project_id, " ".join(words)), "summary")
    except SearchFailed:
        return None
    return [{"id": i["id"], "key": shown_key(i)} for i in issues if same_title(i["fields"].get("summary"), summary)]


def newest_in(conn, project_id):
    """The issue id of the newest issue in the project, or "none". One issue is asked for, so more existing is expected."""
    try:
        status, _, body = conn.get(SEARCH_PATH, {"jql": "project = %s ORDER BY created DESC" % project_id, "fields": "created", "maxResults": 1})
    except (OSError, TimeoutError) as err:
        raise Refused(unreachable(err))
    issues = body.get("issues") if status == 200 and isinstance(body, dict) else None
    if not isinstance(issues, list) or any(not isinstance(i, dict) or not ident(i.get("id")) for i in issues):
        raise Refused("the project's newest issue could not be read (status %d), so no snapshot can be taken" % status)
    return issues[0]["id"] if issues else "none"


def snapshot(conn, project_id, key, summary):
    """One short code for what Jira shows where this creation would land: the project's newest issue, the issues
    carrying the key, and the issues with this title."""
    try:
        keyed = find_by_key(conn, key)
    except SearchFailed as failure:
        raise Refused("THE SEARCH FOR THE KEY FAILED (%s). The duplicate check cannot be made, so no preview is issued" % failure)
    titled = find_by_title(conn, project_id, summary)
    text = canonical({"newest": newest_in(conn, project_id), "keyed": [i["id"] for i in keyed], "titled": None if titled is None else [i["id"] for i in titled]})
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16], keyed, titled


def read_item(conn, issue_id):
    """An issue read by its id: {"labels", "summary", "project_id", "type_id", "created"}, or None if Jira answers 404."""
    status, _, issue = read(conn, "/rest/api/3/issue/%s" % issue_id, {"fields": ISSUE_FIELDS})
    if status == 404:
        return None
    fields = issue.get("fields") if status == 200 and isinstance(issue, dict) else None
    project = fields.get("project") if isinstance(fields, dict) else None
    kind = fields.get("issuetype") if isinstance(fields, dict) else None
    if not (isinstance(project, dict) and isinstance(kind, dict) and isinstance(fields.get("labels"), list) and issue.get("id") == issue_id):
        raise NeedsLooking("Jira's answer for issue id %s could not be used (status %d)" % (issue_id, status))
    return {"labels": fields["labels"], "summary": fields.get("summary"), "project_id": project.get("id"), "type_id": kind.get("id"),
            "created": str(fields.get("created", "?"))[:40] if re.fullmatch(r"[0-9T:.+-]{10,40}", str(fields.get("created", ""))) else "?", "key": shown_key(issue)}


# ---------------------------------------------------------------- what the creation is


def build_proposal(conn, draft, record, allowlist_path):
    """The one place that decides what a creation means. The preview shows its result; confirm compares with it."""
    allowed, note = load_allowlist(allowlist_path)
    site = site_fingerprint(conn.host)
    project = read_project(conn, draft["project"])
    if (site, project["id"]) not in allowed:
        raise Refused("project %s (project id %s) on the Jira site with fingerprint %s is not on the sandbox allowlist (%s). "
                      "This workflow writes only to projects listed there" % (project["key"], project["id"], site, os.path.basename(allowlist_path)))
    permissions = read_permissions(conn, project["id"])
    if not permissions["BROWSE_PROJECTS"] or not permissions["CREATE_ISSUES"]:
        raise Refused("Jira says this identity may not create issues in this project (CREATE_ISSUES: %s)" % ("yes" if permissions["CREATE_ISSUES"] else "no"))
    return {"site": site, "project_id": project["id"], "project_key": project["key"], "type_id": project["type_id"],
            "summary": draft["summary"], "summary_sha": sha_of(draft["summary"]), "source": draft["source"], "source_sha": draft["source_sha"],
            "allowlist": note, "permissions": permissions, "key": record["key"], "attempt": len(record["attempts"]) + 1}


def fingerprint_of(proposal, made_at):
    return sha_of(canonical({"proposal": proposal, "made_at": made_at}))


def head(conn, proposal):
    say("Jira site:  https://%s  (site fingerprint %s)" % (conn.host, proposal["site"]))
    say("Project:    %s (project id %s). On the sandbox allowlist: yes." % (proposal["project_key"], proposal["project_id"]))
    say("            The allowlist is %s." % proposal["allowlist"])
    say("Key:        %s  (the draft's key, read from its record in the state folder)" % proposal["key"])


def requests_line(conn):
    kinds = sorted(set(method for method, _ in conn.sent))
    say("Requests sent to Jira: %d. %s" % (len(conn.sent), "Every one was a GET, which reads and cannot change anything."
                                           if kinds == ["GET"] else "Kinds: %s." % ", ".join(kinds)))
    for method, path in conn.sent:
        say("  %s %s" % (method, path))


def listed(items):
    return ", ".join("%s (issue id %s)" % (i["key"], i["id"]) for i in items)


def by_hand(key):
    say("To look by hand: in Jira, open the issue search and search for    labels = \"%s\"" % key)


# ---------------------------------------------------------------- check a linked task


def check_link(conn, record):
    """Reads a linked task back. Returns (lines to say, whether it is there as recorded, how the key search went).
    The last is "yes" (this one and no other), "none", "many", or "failed"."""
    issue, key, last = record["issue"], record["key"], record["attempts"][-1]
    item = read_item(conn, issue["id"])
    if item is None:
        return ["Jira answered 404 for issue id %s. It has been deleted, or this identity can no longer see it." % issue["id"],
                "NOTHING IS CREATED IN ITS PLACE. Whether to create it again is for a person to decide."], False, "none"
    lines = ["Read back from Jira just now, by its issue id %s:" % issue["id"],
             "  it exists, and its key is %s: yes" % item["key"],
             "  it carries the label %s: %s" % (key, "yes" if key in item["labels"] else "NO. The label has been removed. It is still the task this record names, by its issue id"),
             "  it is in project id %s, where it was sent: %s" % (last["project_id"], "yes" if item["project_id"] == last["project_id"] else "NO, it is now in project id %s" % item["project_id"]),
             "  its title is the title that was sent, character for character: %s" % ("yes" if isinstance(item["summary"], str) and sha_of(item["summary"]) == last["summary_sha"]
                                                                                    else "no. It has been changed in Jira since. That does not affect the key")]
    ok = key in item["labels"] and item["project_id"] == last["project_id"]
    try:
        found = find_by_key(conn, key)
    except SearchFailed as failure:
        lines.append("  a search of Jira for the key COULD NOT BE MADE (%s). The read by issue id above stands by itself" % failure)
        return lines, ok, "failed"
    if [i["id"] for i in found] == [issue["id"]]:
        lines.append("  a search of Jira for the key returns 1 issue: this one, and no other")
        return lines, ok, "yes"
    if not found:
        lines.append("  a search of Jira for the key returns 0 issues. IT IS NOT FOUND BY ITS KEY just now: Jira's search is behind, or the label is gone")
        return lines, ok, "none"
    lines.append("  a search of Jira for the key returns %s. NOT THIS ONE ALONE: %s" % (plural(len(found), "issue"), listed(found)))
    return lines, False, "many"


# ---------------------------------------------------------------- preview


def refuse_if_unknown(record):
    if record["status"] in ("sending", "uncertain"):
        last = record["attempts"][-1]
        raise Refused("a request to create this draft's task was sent at %s and ITS OUTCOME IS NOT KNOWN (the record says '%s'). "
                      "It may exist in Jira. Nothing is previewed or created until that is looked into. Run `resolve` for this draft"
                      % (last["sent_at"], record["status"]))


def cmd_preview(args, conn):
    draft = read_draft(args.draft)
    _, record, is_new = load_record(args.state, draft, make=True)
    key = record["key"]
    refuse_if_unknown(record)
    if record["status"] == "linked":
        lines, ok, _ = check_link(conn, record)
        say("NOTHING TO CREATE. Nothing has been written.")
        say("")
        say("This draft's task already exists: %s (issue id %s), recorded here at %s." % (record["issue"]["key"], record["issue"]["id"], record["issue"]["recorded_at"]))
        say("Key: %s" % key)
        for line in lines:
            say(line)
        requests_line(conn)
        say("")
        say("No fingerprint is issued, because there is nothing to confirm, and nothing was sent.")
        return 0 if ok else 1

    proposal = build_proposal(conn, draft, record, args.allowlist)
    before, keyed, titled = snapshot(conn, proposal["project_id"], key, draft["summary"])
    after, keyed_again, _ = snapshot(conn, proposal["project_id"], key, draft["summary"])
    if after != before:
        raise Refused("what Jira shows changed while the preview was being made. Preview again")
    say("NOTHING TO CREATE. Nothing has been written." if keyed else "PREVIEW. Nothing has been written.")
    say("")
    head(conn, proposal)
    say("            %s" % ("It was made just now, for this draft, and saved before anything was asked of Jira." if is_new else "It was made at %s and has not changed." % record["made_at"]))
    if record["attempts"]:
        last = record["attempts"][-1]
        say("Earlier:    this is attempt %d. A request was sent at %s. What became of it: %s." % (proposal["attempt"], last["sent_at"], last["outcome"]))
    say("")
    say("%s: one new issue." % ("The change asked for" if keyed else "The change that would be made"))
    say("  Sent to Jira, and nothing else:")
    say("    project     project id %s (%s)" % (proposal["project_id"], proposal["project_key"]))
    say("    issue type  %s (issue type id %s)" % (TYPE_NAME, proposal["type_id"]))
    say("    labels      one label, the key: %s" % key)
    say("    summary     the title, exactly as it would be sent, between the bars. %s:" % plural(len(draft["summary"]), "character"))
    say("    | %s" % draft["summary"])
    say("  No description, assignee or other field is sent. Jira fills in its own defaults. Its reporter would be the")
    say("  Jira account the API token belongs to, and not the name given with the confirmation.")
    say("  Where the title came from: the draft %s, sha256 %s." % (draft["source"], draft["source_sha"][:16]))
    say("  A created issue cannot be unsent. It can be deleted afterwards, by hand.")
    say("")
    if draft["pointed_out"]:
        say("LOOK AT THESE BEFORE CONFIRMING. They are not refused. Each may be something private. The title holds:")
        for line in draft["pointed_out"]:
            say("  %s" % line)
    else:
        say("Looked for in the title and not found: email addresses, web addresses, telephone numbers, @names, words")
        say("  that mark something as private, and %d patterns that look like a secret. That is a search for patterns." % len(SECRETS))
        say("  The person confirming reads the title.")
    say("")
    say("Permission check, asked of Jira for this project and this identity:")
    say("  may see the project      (BROWSE_PROJECTS): %s" % ("yes" if proposal["permissions"]["BROWSE_PROJECTS"] else "no"))
    say("  may create issues in it  (CREATE_ISSUES):   %s" % ("yes" if proposal["permissions"]["CREATE_ISSUES"] else "no"))
    say("Duplicate check 1, by the key: Jira was searched for issues carrying the label %s, in every project this" % key)
    say("  identity can see. Found: %d%s." % (len(keyed), " (%s)" % listed(keyed) if keyed else ""))
    if titled is None:
        say("Duplicate check 2, by the title: NOT MADE. Jira would not run the search, or the title has no plain words to search for.")
    else:
        say("Duplicate check 2, by the title: issues in %s with this title, capitals and spacing aside: %d%s."
            % (proposal["project_key"], len(titled), " (%s)" % listed(titled) if titled else ""))
        if titled and not keyed:
            say("  LOOK AT %s BEFORE CONFIRMING. %s the same title and not this draft's key. If one of them is this"
                % ("IT" if len(titled) == 1 else "THEM", "It has" if len(titled) == 1 else "They have"))
            say("  work, made some other way, do not confirm.")
    say("Where Jira cannot check: its request to create an issue has no 'only if there is none with this label'")
    say("  condition, and its search can be behind what it holds. The confirmation searches for the key again just")
    say("  before writing. After a write whose outcome is not known, nothing is created without a search and a person.")
    say("")
    say("Snapshot before the preview: %s" % before)
    say("Snapshot after the preview:  %s" % after)
    say("The two are the same. Jira is unchanged, as far as these reads can show. A snapshot is of the newest issue in")
    say("  the project, the issues carrying the key, and the issues with this title.")
    requests_line(conn)
    say("")
    if keyed:
        say("An issue already carries this draft's key: %s." % listed(keyed))
        say("No fingerprint is issued, because there is nothing to create. Run `resolve` to record it here.")
        return 0
    made = now_utc()
    made_at, expires_at = stamp(made), stamp(made + datetime.timedelta(minutes=LIMIT_MINUTES))
    proposal["titled"] = None if titled is None else sorted(i["id"] for i in titled)
    fingerprint = fingerprint_of(proposal, made_at)
    code = fingerprint[:12]
    path = os.path.join(args.state, "previews", code + ".json")
    if os.path.exists(path):
        raise Refused("a preview with this fingerprint was made a moment ago. Wait a second and preview again")
    save_json(path, {"fingerprint": fingerprint, "made_at": made_at, "expires_at": expires_at, "proposal": proposal, "state": "open"})
    say("Fingerprint of this preview: %s" % code)
    say("Made:    %s" % made_at)
    say("Expires: %s (%d minutes after it was made)" % (expires_at, LIMIT_MINUTES))
    say("")
    say("Nothing has been written. To create this task, a person who has read this preview confirms it by its fingerprint.")
    return 0


# ---------------------------------------------------------------- confirm


def read_preview_record(state, code):
    path = os.path.join(state, "previews", code + ".json")
    try:
        with open(path, encoding="utf-8") as f:
            saved = json.load(f)
        made = parse(saved["made_at"])
        genuine = fingerprint_of(saved["proposal"], saved["made_at"])
        status = saved["state"]
    except FileNotFoundError:
        raise Refused("there is no preview with the fingerprint %s. Make a preview, read it, and confirm that one" % code)
    except (ValueError, KeyError, TypeError):
        raise Refused("the saved preview %s cannot be read, so it cannot be confirmed" % code)
    if genuine != saved.get("fingerprint") or genuine[:12] != code:
        raise Refused("the saved preview %s has been altered since it was made, so it cannot be confirmed" % code)
    return path, saved, made, status


def jira_said(body):
    """What Jira's refusal said: other people's text, cut short, with unseen characters taken out. Shown, and not saved."""
    messages = body.get("errorMessages") if isinstance(body, dict) else None
    texts = [m for m in messages if isinstance(m, str)] if isinstance(messages, list) else []
    errors = body.get("errors") if isinstance(body, dict) else None
    texts += ["%s: %s" % (k, v) for k, v in sorted(errors.items()) if isinstance(k, str) and isinstance(v, str)] if isinstance(errors, dict) else []
    return UNSEEN.sub(" ", " / ".join(texts))[:200]


def interrupt(args, point):
    if getattr(args, "interrupt_at", None) == point:
        raise Interrupted(point)


def cmd_confirm(args, conn):
    code = (args.fingerprint or "").strip().lower()
    if not code:
        raise Refused("no confirmation was given. A confirmation names the fingerprint of the preview it approves, and there is no way to write without one")
    if len(code) != 12 or any(ch not in "0123456789abcdef" for ch in code):
        raise Refused("a fingerprint is 12 characters, each 0 to 9 or a to f")
    name = (args.confirmed_by or "").strip()
    if not name:
        raise Refused("no confirmation was given. A confirmation gives the name of the person confirming")
    if len(name) > 60 or "@" in name or any(ord(ch) < 32 or ord(ch) == 127 for ch in name):
        raise Refused("the confirming person's name must be short plain text, and not an email address")

    draft = read_draft(args.draft)
    claim = claim_draft(args.state, draft["name"])      # from here to the end of this run, no other run may confirm this draft
    try:
        return confirm_claimed(args, conn, draft, code, name)
    finally:
        try:
            os.remove(claim)
        except OSError:
            pass


def confirm_claimed(args, conn, draft, code, name):
    record_file, record, _ = load_record(args.state, draft, make=False)     # read AFTER the claim, so it is what stands now
    refuse_if_unknown(record)
    if record["status"] == "linked":
        raise Refused("this draft's task already exists: %s (issue id %s). It is not created again" % (record["issue"]["key"], record["issue"]["id"]))
    preview_file, saved, made, status = read_preview_record(args.state, code)
    if status != "open":
        raise Refused("the preview %s has been used: a write was sent for it (recorded as '%s'). A fingerprint is used once" % (code, status))
    confirmed = now_utc()
    now = confirmed + datetime.timedelta(minutes=args.pretend_minutes_later or 0)
    if args.pretend_minutes_later:
        say("TEST CLOCK: pretending it is %d minutes later than it is." % args.pretend_minutes_later)
    age = now - made
    if age < datetime.timedelta(0):
        raise Refused("the preview %s is dated later than the clock says it is now" % code)
    if age > datetime.timedelta(minutes=LIMIT_MINUTES):
        raise Refused("this preview is too old. It was made %d minutes ago and the limit is %d. Make a new preview and read it" % (age.total_seconds() // 60, LIMIT_MINUTES))

    before = saved["proposal"]
    if before["key"] != record["key"] or before["attempt"] != len(record["attempts"]) + 1:
        raise Refused("the preview %s is not for this draft as its record now stands. Make a new preview and read it" % code)
    if site_fingerprint(conn.host) != before["site"]:
        raise Refused("this is not the Jira site the preview was made against. Make a new preview and read it")
    proposal = build_proposal(conn, draft, record, args.allowlist)
    differs = [what for what, field in (("the title is not the title the preview showed", "summary"), ("the draft is not the file the preview showed", "source_sha"),
                                        ("the allowlist file is not the one the preview used", "allowlist")) if before[field] != proposal[field]]
    if differs:
        raise Refused("the change is not the one that was previewed: %s. Make a new preview and read it" % "; ".join(differs))
    moved = [what for what, field in (("the draft now names a different project", "project_id"), ("the project's %s issue type is now a different one" % TYPE_NAME, "type_id")) if before[field] != proposal[field]]
    try:
        keyed = find_by_key(conn, record["key"])     # the last search before the write
    except SearchFailed as failure:
        raise Refused("THE SEARCH FOR THE KEY FAILED just before the write (%s). Whether the task already exists cannot be told, so nothing is sent" % failure)
    if keyed:
        moved.append("an issue now carries this draft's key (%s). Run `resolve` to record it" % listed(keyed))
    titled = find_by_title(conn, proposal["project_id"], draft["summary"])
    if (None if titled is None else sorted(i["id"] for i in titled)) != before["titled"]:
        moved.append("the issues in the project with this title are not the ones the preview showed")
    if moved:
        raise Refused("something changed in Jira after the preview was made: %s. Make a new preview and read it" % "; ".join(moved))

    say("CONFIRMATION for preview %s, given by: %s (the name given with the confirmation)." % (code, name))
    say("")
    head(conn, proposal)
    say("")
    say("Checked in this run, before writing:")
    say("  the preview is %s old, and the limit is %d: ok" % (plural(int(age.total_seconds() // 60), "minute"), LIMIT_MINUTES))
    say("  the saved preview is unaltered and has not been used: ok")
    say("  the draft asks for exactly what the preview showed: ok")
    say("  the draft's record shows no earlier request whose outcome is unknown: ok")
    say("  the project is on the sandbox allowlist for this site: ok")
    say("  Jira says this identity may create issues in the project: ok")
    say("  Jira, searched just before the write, returns no issue carrying the key: ok")
    say("")

    # Written down BEFORE the request goes: from here until an answer is recorded, the outcome is not known.
    sent_at = stamp(now_utc())
    attempt = {"fingerprint": saved["fingerprint"], "sent_at": sent_at, "outcome": "sent, and no answer recorded", "confirmed_by": name,
               "confirmed_at": stamp(confirmed), "preview_made_at": saved["made_at"], "site": proposal["site"], "project_id": proposal["project_id"],
               "project_key": proposal["project_key"], "type_id": proposal["type_id"], "summary_sha": proposal["summary_sha"],
               "summary_len": len(draft["summary"]), "source": draft["source"], "source_sha": draft["source_sha"]}
    record["attempts"].append(attempt)
    record["status"], record["not_found"] = "sending", []
    save_json(record_file, record)
    saved["state"] = "sending"
    save_json(preview_file, saved)
    say("Written to the draft's record before sending: status 'sending', at %s." % sent_at)
    interrupt(args, "before-send")
    try:
        status, _, body = conn.post_issue(proposal["project_id"], proposal["type_id"], draft["summary"], record["key"])
    except (OSError, TimeoutError) as err:
        attempt["outcome"], attempt["ended_at"] = "sent, and no answer came back", stamp(now_utc())
        record["status"] = "uncertain"
        save_json(record_file, record)
        raise NeedsLooking("the write was sent and no answer came back (%s). IT IS NOT KNOWN whether Jira created the task. "
                           "It was not sent again" % type(getattr(err, "reason", err)).__name__)
    say("The request was sent, and Jira answered %d." % status)
    interrupt(args, "after-send")
    attempt["ended_at"] = stamp(now_utc())
    issue_id, issue_key = (body.get("id"), body.get("key")) if isinstance(body, dict) else (None, None)
    if status not in (200, 201) or not ident(issue_id) or not (isinstance(issue_key, str) and REF.fullmatch(issue_key)):
        try:
            found = find_by_key(conn, record["key"])
        except SearchFailed:
            found = None
        if status in REFUSALS and found == []:
            attempt["outcome"] = "Jira refused it (%d) and created nothing" % status
            record["status"] = "new"
            save_json(record_file, record)
            words = jira_said(body)
            if words:
                say("Jira's own words, which are not this workflow's: %s" % json.dumps(words), "Jira's own words were shown on screen and are not saved: %d characters." % len(words))
            raise NotWritten("Jira answered %d to the write. That answer is Jira's own refusal, and a search for the key just afterwards "
                             "finds nothing either. The preview cannot be used again" % status)
        attempt["outcome"] = "sent, and Jira answered %d without a usable issue id" % status
        record["status"] = "uncertain"
        save_json(record_file, record)
        raise NeedsLooking("Jira answered %d to the write and gave no usable issue id. A search for the key just afterwards %s. "
                           "IT IS NOT KNOWN whether the task was created" % (status, "could not be made" if found is None else "finds %s" % plural(len(found), "issue")))

    recorded_at = stamp(now_utc())
    attempt["outcome"] = "Jira answered %d and created %s" % (status, issue_key)
    record["issue"] = {"id": issue_id, "key": issue_key, "recorded_at": recorded_at, "how": "created by the run that was confirmed, and answered by Jira"}
    record["status"] = "linked"
    save_json(record_file, record)       # kept at once, so that the new issue's id is not lost
    saved["state"] = "written"
    save_json(preview_file, saved)
    say("WRITTEN to Jira: one task, %s (issue id %s), carrying the key. Jira answered %d." % (issue_key, issue_id, status))
    say("Recorded in the draft's record at once: status 'linked'.")
    say("The confirmation and the write happened in this one run of the command.")
    interrupt(args, "after-record")
    say("")
    lines, ok, by_key = check_link(conn, record)
    for line in lines:
        say(line)
    if by_key == "none":
        say("  That search was made a moment after the create. The task is recorded by its issue id. Run `check` later.")
    finish(args, conn, record)
    say("")
    requests_line(conn)
    if not ok or by_key == "many":
        raise NeedsLooking("Jira accepted the write, and the task does not read back as recorded. See the lines above")
    return 0


def result_lines(record, created):
    issue, last = record["issue"], record["attempts"][-1]
    return ["Issue key: %s" % issue["key"],
            "Identifier of what was created: Jira issue id %s, carrying the label %s" % (issue["id"], record["key"]),
            "Target project: %s (project id %s), on the sandbox allowlist" % (last["project_key"], last["project_id"]),
            "Jira site: %s, site fingerprint %s" % (SITE_MARK, last["site"]),
            "Issue type: %s (issue type id %s)" % (TYPE_NAME, last["type_id"]),
            "Title: %d characters, sha256 %s, from the draft %s (file sha256 %s)" % (last["summary_len"], last["summary_sha"], last["source"], last["source_sha"]),
            "The request to create it was sent at: %s. Attempt %d for this draft" % (last["sent_at"], len(record["attempts"])),
            "Created, by Jira's own clock: %s" % created,
            "Recorded locally at: %s. How: %s" % (issue["recorded_at"], issue["how"]),
            "Confirmed by: %s, at %s" % (last["confirmed_by"], last["confirmed_at"]),
            "Preview: fingerprint %s, made %s" % (last["fingerprint"][:12], last["preview_made_at"]),
            "To reverse: delete %s in Jira, by hand. This workflow does not delete" % issue["key"]]


def finish(args, conn, record):
    item = read_item(conn, record["issue"]["id"])
    lines = result_lines(record, item["created"] if item else "not read")
    say("")
    say("RESULT RECORD")
    for line in lines:
        say("  " + line)
    if getattr(args, "result", None):
        text = "\n".join(["# Result record: one Jira task, created at most once", ""] + ["- " + line for line in lines]) + "\n"
        PENDING["result"] = (args.result, text.replace(conn.host, SITE_MARK))
        say("")
        say("The result record is also saved as Markdown where --result said.")


def write_pending():
    """Saves the result record. Called only after the output has been searched for credentials."""
    if "result" in PENDING:
        path, text = PENDING.pop("result")
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)


# ---------------------------------------------------------------- resolve and check


def cmd_resolve(args, conn):
    draft = read_draft(args.draft)
    if args.pretend_seconds_later and args.source != "fake":
        raise Refused("--pretend-seconds-later is for the fake Jira only. Against a real Jira the wait is really waited")
    record_file, record, _ = load_record(args.state, draft, make=False)
    key = record["key"]
    say("RESOLVE for the draft %s. This command searches and records. It has no way to create anything." % draft["source"])
    say("")
    say("Key:    %s" % key)
    say("Record: status '%s'%s." % (record["status"], ", %s sent" % plural(len(record["attempts"]), "request") if record["attempts"] else ", and nothing was ever sent"))
    if record["status"] == "linked":
        say("")
        say("ALREADY RECORDED: %s (issue id %s), at %s. Nothing to resolve, and nothing is created." % (record["issue"]["key"], record["issue"]["id"], record["issue"]["recorded_at"]))
        lines, ok, _ = check_link(conn, record)
        for line in lines:
            say(line)
        requests_line(conn)
        return 0 if ok else 1
    last = record["attempts"][-1] if record["attempts"] else None
    if last and site_fingerprint(conn.host) != last["site"]:
        raise Refused("this is not the Jira site the request was sent to")
    if last:
        say("        The last request was sent at %s. What is recorded of it: %s." % (last["sent_at"], last["outcome"]))
    say("")
    try:
        found = find_by_key(conn, key)
        if not found and last:
            can_be_seen(conn, last["project_id"])
    except SearchFailed as failure:
        say("THE SEARCH FOR THE KEY FAILED: %s." % failure)
        say("Whether the task exists is NOT KNOWN. Nothing is created and nothing is recorded: the record stays '%s'." % record["status"])
        say("Run `resolve` again later. If it keeps failing, a person looks in Jira.")
        by_hand(key)
        requests_line(conn)
        raise NeedsLooking("the search failed, so this run cannot say whether the task exists")
    say("Jira was searched for issues carrying the label %s, in every project this identity can see. Found: %d." % (key, len(found)))

    if len(found) > 1:
        say("MORE THAN ONE ISSUE CARRIES THE KEY: %s." % listed(found))
        say("Nothing is recorded, because this workflow cannot say which one is the task. Nothing is created.")
        requests_line(conn)
        raise NeedsLooking("%d issues carry this draft's key. A person decides which to keep, and removes the others by hand" % len(found))
    if len(found) == 1:
        one = found[0]
        if not last:
            requests_line(conn)
            raise NeedsLooking("%s carries this draft's key, and the record shows that nothing was ever sent for this draft. Nothing is recorded" % listed(found))
        if one["project_id"] != last["project_id"]:
            requests_line(conn)
            raise NeedsLooking("%s carries the key and is in project id %s, not project id %s where the request was sent. Nothing is recorded" % (listed(found), one["project_id"], last["project_id"]))
        item = read_item(conn, one["id"])
        if item is None or key not in item["labels"] or item["type_id"] != last["type_id"]:
            requests_line(conn)
            raise NeedsLooking("%s carries the key in the search, and read by its issue id it is not a %s carrying the key. Nothing is recorded" % (listed(found), TYPE_NAME))
        was = record["status"]
        last["outcome"] += ". Found afterwards by its key: %s" % one["key"]
        record["issue"] = {"id": one["id"], "key": one["key"], "recorded_at": stamp(now_utc()),
                           "how": "found by its key by `resolve`, after a run that ended without recording it (the record said '%s')" % was}
        record["status"] = "linked"
        save_json(record_file, record)
        say("FOUND BY ITS KEY: %s (issue id %s), in project id %s, where the request was sent." % (one["key"], one["id"], one["project_id"]))
        say("It is the one issue that carries the key, and it is a %s. It is taken to be the task the earlier run asked for." % TYPE_NAME)
        say("It is now recorded in the draft's record: status 'linked'. NOTHING WAS CREATED by this run.")
        say("")
        lines, ok, _ = check_link(conn, record)
        for line in lines:
            say(line)
        finish(args, conn, record)
        say("")
        requests_line(conn)
        return 0 if ok else 1

    if record["status"] in ("new", "released"):
        say("Nothing carries the key, and the record shows no request whose outcome is unknown. Nothing to resolve.")
        requests_line(conn)
        return 0
    now = now_utc() + datetime.timedelta(seconds=args.pretend_seconds_later or 0)
    if args.pretend_seconds_later:
        say("TEST CLOCK: pretending it is %d seconds later than it is." % args.pretend_seconds_later)
    # The request ended when its answer came, or failed to. If the run was killed, that moment was not recorded: the
    # request is then taken to have been alive for as long as a request is allowed to wait.
    ended = parse(last["ended_at"]) if last.get("ended_at") else parse(last["sent_at"]) + datetime.timedelta(seconds=TIMEOUT_SECONDS)
    counts_from = ended + datetime.timedelta(seconds=WAIT_SECONDS)
    if any(parse(earlier) > now for earlier in record["not_found"] + [last["sent_at"]]):
        raise Refused("this computer's clock is earlier than a time in the draft's record, so the wait cannot be measured. Put the clock right")
    record["not_found"].append(stamp(now))
    counted = [moment for moment in record["not_found"] if parse(moment) >= counts_from]
    if len(counted) >= 2 and parse(counted[-1]) - parse(counted[0]) >= datetime.timedelta(seconds=GAP_SECONDS):
        record["status"] = "released"
        last["outcome"] += ". Searched for by its key and not found, at %s and again at %s" % (counted[0], counted[-1])
        save_json(record_file, record)
        say("NOT FOUND, at %s and again at %s. Both searches were %d seconds or more after the request ended (%s)," % (counted[0], counted[-1], WAIT_SECONDS, stamp(ended)))
        say("and %d seconds or more apart. Jira says this identity can see the project, and a search there does return issues." % GAP_SECONDS)
        say("As far as Jira's search shows, the task was not created. THAT IS NOT PROOF: a search can be behind, and can")
        say("only show what this identity may see.")
        by_hand(key)
        say("The record is now 'released'. NOTHING WAS CREATED by this run, and nothing will be created by running it again.")
        say("To create the task, make a new preview. A person reads it and confirms it. It will carry the same key.")
        requests_line(conn)
        return 0
    save_json(record_file, record)
    again = max(counts_from, parse(counted[0]) + datetime.timedelta(seconds=GAP_SECONDS)) if counted else counts_from
    say("NOT FOUND YET, at %s. Jira's search can be behind a create, so this is not taken to mean the task does not exist." % stamp(now))
    say("Nothing is created. The record stays '%s'; the time of this empty search is noted in it." % record["status"])
    say("It takes two empty searches, each %d seconds or more after the request ended (%s) and %d seconds or more" % (WAIT_SECONDS, stamp(ended), GAP_SECONDS))
    say("apart, before a new preview is allowed. Empty searches that count so far: %d. Run `resolve` again at or after %s." % (len(counted), stamp(max(again, now))))
    requests_line(conn)
    return 1


def cmd_check(args, conn):
    draft = read_draft(args.draft)
    _, record, _ = load_record(args.state, draft, make=False)
    if record["status"] != "linked":
        raise Refused("this draft has no recorded task to check: its record says '%s'" % record["status"])
    say("CHECK of the task recorded for the draft %s. Nothing is written by this command." % draft["source"])
    say("")
    say("Recorded: %s (issue id %s), at %s. Key: %s" % (record["issue"]["key"], record["issue"]["id"], record["issue"]["recorded_at"], record["key"]))
    lines, ok, by_key = check_link(conn, record)
    for line in lines:
        say(line)
    requests_line(conn)
    say("")
    if ok and by_key == "yes":
        say("AS RECORDED: the task is there, and is found by its key.")
        return 0
    say("THE TASK IS THERE, AND IT WAS NOT FOUND BY ITS KEY in this run: see the last line above." if ok else "NOT AS RECORDED: see the lines above.")
    return 1


# ---------------------------------------------------------------- running


def whole_number(text):
    if not text.isascii() or not text.isdigit() or len(text) > 6:
        raise argparse.ArgumentTypeError("must be a whole number, 0 or more")
    return int(text)


def refused(refusal):
    say("")
    say("REFUSED: %s." % refusal)
    say("Nothing has been written.")
    return 1


def run(args, conn):
    """One command, start to finish. Returns the exit code; what it said is in LINES."""
    try:
        try:
            return {"preview": cmd_preview, "confirm": cmd_confirm, "resolve": cmd_resolve, "check": cmd_check}[args.command](args, conn)
        except NotWritten as refusal:
            return refused(refusal)
        except Refused as refusal:
            if conn.posted():
                raise NeedsLooking("the write was sent, and a step after it could not be done: %s. The task may have been created" % refusal)
            return refused(refusal)
        except (NeedsLooking, Interrupted):
            raise
        except Exception as failure:  # nothing may hide what was already sent
            if conn.posted():
                raise NeedsLooking("the write was sent, and the program then failed (%s). The task may have been created" % type(failure).__name__)
            return refused("the program failed before anything was sent (%s)" % type(failure).__name__)
    except NeedsLooking as problem:
        say("")
        say("A PERSON NEEDS TO LOOK: %s." % problem)
        if args.command == "confirm":
            say("DO NOT CONFIRM AGAIN. Run `resolve` for this draft: it searches Jira for the key and creates nothing.")
        return 2
    except Interrupted as point:
        say("")
        say("STOPPED ON PURPOSE by the test switch --interrupt-at %s. The run ended here as if it had been killed." % point)
        say("Nothing after this point was done, and nothing after this point was recorded.")
        return 3


def person_present(stream):
    """True if the run was started from a terminal. It keeps out a program that has none. It does not prove who typed."""
    try:
        return bool(stream.isatty())
    except (AttributeError, ValueError):
        return False


def main(argv=None):
    parser = argparse.ArgumentParser(description="Create one Jira task from one draft, at most once: preview, confirm, resolve, check.")
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("preview", "confirm", "resolve", "check"):
        sub = commands.add_parser(command)
        sub.add_argument("--source", choices=("live", "fake"), required=True)
        sub.add_argument("--draft", required=True, help="the draft file")
        sub.add_argument("--state", required=True, help="the folder where the draft's record and previews are kept")
        sub.add_argument("--log", help="also save the output here, with the site's address removed")
        if command in ("preview", "confirm"):
            sub.add_argument("--allowlist", required=True, help="the sandbox allowlist")
        if command == "confirm":
            sub.add_argument("--fingerprint")
            sub.add_argument("--confirmed-by")
            sub.add_argument("--pretend-minutes-later", type=whole_number, default=0, metavar="N", help="tests only")
            sub.add_argument("--interrupt-at", choices=POINTS, help="tests only: end the run at this point")
        if command in ("confirm", "resolve"):
            sub.add_argument("--result", help="save the result record here, as Markdown")
        if command == "resolve":
            sub.add_argument("--pretend-seconds-later", type=whole_number, default=0, metavar="N", help="tests only")
    args = parser.parse_args(argv)
    del LINES[:]
    PENDING.clear()
    writes = args.command == "confirm"       # the one command that is given a way to write, whatever the source
    secrets, conn, fake, fake_path = [], None, None, os.path.join(args.state, "fake-jira.json")
    try:
        if args.source == "fake":
            import fake_jira
            fake = fake_jira.FakeJira.open(fake_path)
            conn = Connection(fake.get, fake.post if writes else None, urllib.parse.urlparse(fake_jira.SITE).hostname)
        else:
            if writes and not person_present(sys.stdin):
                raise Refused("a real write is confirmed by a person at a terminal, and this run was not started from one")
            conn, secrets = make_live(writes)
        code = run(args, conn)
    except Refused as refusal:
        code = refused(refusal)
    if fake is not None:
        fake.save(fake_path)
    text = "\n".join(shown for shown, _ in LINES)
    kept = "\n".join(saved for _, saved in LINES)
    if any(secret and secret in text + PENDING.get("result", ("", ""))[1] for secret in secrets):
        wrote = bool(conn) and conn.posted()
        print("STOPPED: a credential was found in the output, so the output was not shown or saved.%s"
              % (" A WRITE WAS SENT TO JIRA in this run. Run `resolve` for this draft before doing anything else." if wrote else ""))
        return 2 if wrote else 1
    print(text)
    write_pending()
    if secrets:
        note = "\nThe output above was searched for the API token, the account's email address and their encoded\nform: none found."
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
