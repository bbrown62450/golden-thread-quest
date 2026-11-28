#!/usr/bin/env python3
"""Moves one Jira item to another status, after asking Jira which moves its workflow allows, a preview, and a
confirmation by a person. Then reads the status back.

    transition.py rules   --source live|fake --issue KEY [--issue KEY ..] [--out RULES.md]
    transition.py preview --source live|fake --request REQUEST.json --allowlist FILE --state DIR
    transition.py confirm --source live|fake --request REQUEST.json --allowlist FILE --state DIR \
                          --fingerprint CODE --confirmed-by NAME
    transition.py check   --source live|fake --state DIR --fingerprint CODE

A REQUEST names one item and the status it should have:

    {"issue": "SAND-1", "to": "In Progress"}

"to" is the status's name as the Jira site writes it, matched exactly. Nobody writes a transition's number: the
workflow asks Jira which moves are open for this item from the status it has NOW, and looks for the one that leads to
the status named. Jira calls a move a "transition".

WHAT IT WILL NOT DO, each refused BEFORE any preview, with no fingerprint:
  - a move Jira does not offer for this item now. The moves Jira does offer are named in the refusal;
  - a move that asks for a REQUIRED field. This workflow sends the move and nothing else, so it cannot fill one in;
  - a move to a status Jira counts as done while a subtask of the item is not done. There is no override;
  - the same, if any subtask's status cannot be read: "could not check" is not "none open";
  - a status that two of the offered moves lead to, because the request would not say which is meant;
  - an item in a project that is not on the sandbox allowlist, or one this identity may not move.
An item that already has the status asked for is reported, and nothing is offered for confirmation.

rules     reads Jira and writes nothing to it. For each item given, it lists every move Jira offers from the item's
          present status, whether this workflow supports it and why not, the fields it asks for, and what else it
          touches. JIRA LISTS ONLY THE MOVES OPEN TO THIS IDENTITY FROM THE PRESENT STATUS. A move a condition hides is
          not listed, and Jira does not say why.

preview   reads Jira and writes nothing. It has no way to send a write. It shows the site, the project, the item, the
          status it has, the move and the status it would have, what is and is not sent, the subtasks, the
          resolution, the permission check and the duplicate check.

confirm   makes the move of one preview, named by its fingerprint, and only if all of this holds at that moment:
            a fingerprint and the confirming person's name are given;
            the saved preview is unaltered, unused and at most 15 minutes old;
            the request, worked out again against Jira, is exactly what the preview showed;
            the item, read again just before the write, still has the status the preview showed.
          If the item ALREADY has the status asked for, nothing is sent, and the run says so.
          If it has any other status, the run is refused: someone moved it, and the preview no longer describes it.
          The move is sent once. Then the item is read back: its status must be the one intended. For a move into a
          done status the resolution is read too, and an EMPTY RESOLUTION is reported as something a person must
          look at; so is a resolution still set after a move out of a done status.
          If Jira accepts the write and the item does not show it yet, it is read again, up to three times, two
          seconds apart. The write is never sent again.

check     reads the status of a confirmed preview's item back. It writes nothing.

What this cannot do. Jira's request to move an item has no "only if its status is still X" condition. Between the
last read and the write there is a moment in which someone else could move the item. A move is open only from
certain statuses, so Jira would usually refuse; where the workflow offers the same move from the new status too, it
would go through. The read-back afterwards, and the item's history, would show it.
Whether Jira will set a resolution cannot be known before the move. It is read afterwards.
Status and move names are the site's own text, set by whoever administers it. They are shown and saved, because they
are what is being confirmed. They are held to 60 characters with no unseen characters.

--pretend-minutes-later N (confirm) is for tests: it moves "now" forward. It can only make a preview older.
--log FILE saves the output with the site's address replaced by a marker and the item's title left out.
--result FILE saves the result record as Markdown, the same way.

Nothing in an item's title is acted on. It is shown on screen, marked as other people's text. It is not saved.

For a live run the connection comes from the environment variables JIRA_BASE_URL, JIRA_EMAIL and JIRA_API_TOKEN. None
is stored. The output is searched for the token, the email address and their encoded form before it is shown.

Exit codes: 0 done; 1 refused or not found, nothing written by this run; 2 a person needs to look.
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
import time
import urllib.error
import urllib.parse
import urllib.request

LIMIT_MINUTES = 15
CLAIM_MINUTES = 10
TIMEOUT_SECONDS = 30
MAX_RULES = 5
REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,60}")
FIELD = re.compile(r"[A-Za-z0-9_.-]{1,60}")
TIME_FORMAT = "%Y-%m-%d %H:%M:%S UTC"
SITE_MARK = "[site address removed]"
ISSUE_FIELDS = "summary,project,status,resolution,subtasks,issuetype,updated"
WRITE_PATH = re.compile(r"/rest/api/3/issue/[0-9]{1,20}/transitions")
REFUSALS = (400, 401, 403, 404, 409)   # answers that mean Jira did not take the write. Any other failure is not taken to mean that
UNSEEN = re.compile("[\\x00-\\x1f\\x7f-\\xa0\\u00ad\\u034f\\u061c\\u115f\\u1160\\u2000-\\u200f\\u2028\\u2029\\u202a-\\u202e\\u205f-\\u2069\\u2800\\u3000\\u3164\\ufeff\\ud800-\\udfff\\U000e0000-\\U000e007f]")
MARKUP = re.compile(r"[|`<>\[\]]")       # characters that mean something to a Markdown page. Shown as a question mark
RULES_HEADING = "# Transition rules"

READ_AGAIN = 3       # how many times the item is read after a write that Jira accepted, if it does not show the move yet
PAUSE_SECONDS = 2

LINES = []      # each is (what is shown on screen, what is saved)
PENDING = {}    # files written by main() only after the output has been searched for credentials


class Refused(Exception):
    """Nothing was written by this run. The message is the reason."""


class NotWritten(Refused):
    """A write was sent, and Jira's answer and a read afterwards show that nothing was written."""


class NeedsLooking(Exception):
    """A person needs to look. The message says what is and is not known."""


def pause():
    time.sleep(PAUSE_SECONDS)


def say(text="", saved=None):
    LINES.append((text, text if saved is None else saved))


def quoted(text, limit=60):
    return json.dumps(MARKUP.sub("?", UNSEEN.sub("?", str(text)))[:limit], ensure_ascii=False)


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
        try:
            return self._get(path, params)
        except (OSError, TimeoutError) as err:
            reason = "could not reach Jira (%s)" % type(getattr(err, "reason", err)).__name__
            if self.posted():
                raise NeedsLooking("after a write was sent, a read failed: %s" % reason)
            raise Refused(reason)

    def post_move(self, issue_id, move_id):
        """One move of one item. The body is the move's id and nothing else: no field, no comment."""
        if self._post is None:
            raise Refused("this command has no way to write")
        if not (ident(issue_id) and ident(move_id)):
            raise Refused("a write names the item and the move by their ids")
        path = "/rest/api/3/issue/%s/transitions" % issue_id
        self.sent.append(("POST", path))
        return self._post(path, None, {"transition": {"id": move_id}})


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
            err.close()
        except http.client.HTTPException as err:
            raise OSError(type(err).__name__)
        try:
            parsed = json.loads(raw.decode("utf-8")) if raw.strip() else {}
        except (ValueError, RecursionError):
            parsed = {}
        return status, headers, parsed if isinstance(parsed, dict) else {}

    def get(path, params=None):
        return send("GET", path, params, None)

    def post(path, params, body):
        ok = (WRITE_PATH.fullmatch(path) is not None and not params and isinstance(body, dict) and set(body) == {"transition"}
              and isinstance(body["transition"], dict) and set(body["transition"]) == {"id"} and ident(body["transition"]["id"]))
        if not ok:
            raise Refused("the only write this workflow sends is one move of one item: the move's id, and nothing else")
        return send("POST", path, params, body)

    return Connection(get, post if may_write else None, host), [token, email, encoded]


def site_fingerprint(host):
    return hashlib.sha256(host.lower().encode("utf-8")).hexdigest()[:16]


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


def sha_of(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def save_json(path, data):
    """Written whole or not at all: to a file of this run's own, pushed to the disk, then renamed over the first."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = "%s.%d.tmp" % (path, os.getpid())
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


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
    except (OSError, ValueError, UnicodeDecodeError, RecursionError):
        raise Refused("the %s is not JSON that can be read" % what)


def load_allowlist(path):
    data = read_json(path, "sandbox allowlist")
    entries = data.get("sandbox_projects") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        raise Refused("the sandbox allowlist must hold a list named sandbox_projects")
    allowed = set()
    for entry in entries:
        site, project = (entry.get("site_fingerprint"), entry.get("project_id")) if isinstance(entry, dict) else (None, None)
        if not (isinstance(site, str) and re.fullmatch(r"[0-9a-f]{16}", site) and ident(project)):
            raise Refused("an entry in the sandbox allowlist is not a site fingerprint and a project id")
        allowed.add((site, project))
    with open(path, "rb") as f:
        sha = hashlib.sha256(f.read()).hexdigest()
    return allowed, "the file %s, sha256 %s, which lists %s" % (os.path.basename(path), sha[:16], plural(len(allowed), "project"))


def plain_name(value):
    return isinstance(value, str) and 1 <= len(value) <= 60 and value == value.strip() and not UNSEEN.search(value)


def read_request(path):
    name = os.path.basename(path)
    if not name.endswith(".json") or not REF.fullmatch(name[:-5]):
        raise Refused("a request is a file whose name is letters, digits and dashes, ending in .json")
    data = read_json(path, "request")
    if not isinstance(data, dict) or set(data) != {"issue", "to"}:
        raise Refused("the request must have exactly 'issue' and 'to'")
    if not isinstance(data["issue"], str) or not REF.fullmatch(data["issue"]):
        raise Refused("'issue' is the item's key or issue id: letters, digits and dashes only. A title is not accepted")
    if not plain_name(data["to"]):
        raise Refused("'to' is the name of a status as the Jira site writes it: 1 to 60 characters, none of them unseen")
    with open(path, "rb") as f:
        sha = hashlib.sha256(f.read()).hexdigest()
    return {"name": name[:-5], "issue": data["issue"], "to": data["to"], "source": name, "source_sha": sha}


def claim_request(state, name):
    """Only one run at a time may confirm a request. The claim is a file made with 'create only if absent', holding the
    time and a mark of this run's own. Returns (path, mark)."""
    path, mark = os.path.join(state, "claims", name), random_source.token_hex(8)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    for _ in range(2):
        try:
            handle = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(handle, ("%s|%s" % (stamp(now_utc()), mark)).encode("ascii"))
            os.close(handle)
            return path, mark
        except FileExistsError:
            try:
                with open(path, encoding="ascii") as f:
                    since = parse(f.read().split("|")[0].strip())
            except (OSError, ValueError):
                since = None
            if since is None or since > now_utc():
                raise Refused("there is a claim on this request that cannot be read, or is dated in the future. If no run is confirming it, remove the file "
                              "%s from the claims folder of the state folder by hand, and preview again" % json.dumps(name))
            if now_utc() - since <= datetime.timedelta(minutes=CLAIM_MINUTES):
                raise Refused("another run is confirming this request at this moment (its claim was made at %s). If no run is, that "
                              "run was killed: wait until %d minutes after that time, then preview again" % (stamp(since), CLAIM_MINUTES))
            try:
                os.remove(path)
            except OSError:
                pass
    raise Refused("another run took this request at the same moment")


def holds(claim):
    """True if the claim file is still this run's own."""
    try:
        with open(claim[0], encoding="ascii") as f:
            return f.read().split("|")[-1].strip() == claim[1]
    except OSError:
        return False


def release(claim):
    if holds(claim):            # never another run's
        try:
            os.remove(claim[0])
        except OSError:
            pass


# ---------------------------------------------------------------- reading Jira


def status_of(raw):
    """A status as Jira gives it: {"id", "name", "category"}, or None if it cannot be read."""
    category = raw.get("statusCategory") if isinstance(raw, dict) else None
    key = category.get("key") if isinstance(category, dict) else None
    if not (isinstance(raw, dict) and ident(raw.get("id")) and plain_name(raw.get("name")) and isinstance(key, str) and re.fullmatch(r"[a-z]{1,20}", key)):
        return None
    return {"id": raw["id"], "name": raw["name"], "category": key}


def read_item(conn, ref, what):
    status, _, issue = conn.get("/rest/api/3/issue/%s" % ref, {"fields": ISSUE_FIELDS})
    if status == 401:
        raise Refused("Jira rejected the credentials (401). Check JIRA_EMAIL and JIRA_API_TOKEN")
    if status == 404:
        raise Refused("Jira answered 404 for %s. It does not exist, or this identity is not permitted to see it. Jira gives one answer for both" % what)
    fields = issue.get("fields") if status == 200 and isinstance(issue, dict) else None
    project = fields.get("project") if isinstance(fields, dict) else None
    now = status_of(fields.get("status")) if isinstance(fields, dict) else None
    listed = fields.get("subtasks") if isinstance(fields, dict) else None
    ok = (isinstance(project, dict) and now is not None and ident(issue.get("id")) and ident(project.get("id"))
          and isinstance(issue.get("key"), str) and REF.fullmatch(issue["key"]) and isinstance(project.get("key"), str) and REF.fullmatch(project["key"]))
    if not ok:
        raise Refused("Jira's answer for %s could not be used (status %d)" % (what, status))
    resolution = fields.get("resolution")
    if resolution is not None and not (isinstance(resolution, dict) and isinstance(resolution.get("name"), str) and resolution["name"].strip()):
        raise Refused("Jira's answer for %s gives a resolution that could not be read" % what)
    subtasks = []
    for child in listed if isinstance(listed, list) else []:
        child_status = status_of((child.get("fields") or {}).get("status")) if isinstance(child, dict) and isinstance(child.get("fields"), dict) else None
        key = child.get("key") if isinstance(child, dict) and isinstance(child.get("key"), str) and REF.fullmatch(child["key"]) else "?"
        subtasks.append({"key": key, "status": child_status})        # a status of None: it could not be read
    title = fields.get("summary")
    kind = fields.get("issuetype", {}).get("name") if isinstance(fields.get("issuetype"), dict) else None
    return {"type": kind if plain_name(kind) else "not given", "id": issue["id"], "key": issue["key"], "project_id": project["id"], "project_key": project["key"], "status": now,
            "resolution": UNSEEN.sub("?", resolution["name"])[:60] if resolution else None, "subtasks": subtasks, "subtasks_listed": isinstance(listed, list),
            "updated": str(fields.get("updated", ""))[:40], "title": " ".join(UNSEEN.sub("?", title).split())[:100] if isinstance(title, str) else "(Jira gave no title)"}


def read_moves(conn, issue_id, what):
    """The moves Jira offers for the item from the status it has now. Each: {"id", "name", "to", "required", "optional"}."""
    status, _, body = conn.get("/rest/api/3/issue/%s/transitions" % issue_id, {"expand": "transitions.fields"})
    listed = body.get("transitions") if status == 200 and isinstance(body, dict) else None
    if not isinstance(listed, list):
        raise Refused("Jira did not list the moves open for %s (status %d), so none is assumed" % (what, status))
    moves = []
    for raw in listed:
        to = status_of(raw.get("to")) if isinstance(raw, dict) else None
        told = isinstance(raw, dict) and "fields" in raw          # Jira was asked to say which fields each move asks for
        fields = raw.get("fields", {}) if isinstance(raw, dict) else None
        if not (isinstance(raw, dict) and ident(raw.get("id")) and plain_name(raw.get("name")) and to is not None and isinstance(fields, dict)
                and all(isinstance(name, str) and FIELD.fullmatch(name) and isinstance(field, dict) and isinstance(field.get("required"), bool) for name, field in fields.items())):
            raise Refused("Jira's list of the moves open for %s could not be read, so none is assumed" % what)
        if raw.get("isAvailable") is False:
            continue
        moves.append({"id": raw["id"], "name": raw["name"], "to": to, "fields_told": told, "required": sorted(n for n, f in fields.items() if f["required"]), "optional": sorted(n for n, f in fields.items() if not f["required"])})
    if len(set(move["id"] for move in moves)) != len(moves):
        raise Refused("Jira's list of the moves open for %s names one move twice, so none is assumed" % what)
    return moves


def read_permissions(conn, issue_id):
    names = ("BROWSE_PROJECTS", "TRANSITION_ISSUES")
    status, _, body = conn.get("/rest/api/3/mypermissions", {"issueId": issue_id, "permissions": ",".join(names)})
    found = body.get("permissions") if status == 200 and isinstance(body, dict) else None
    if not isinstance(found, dict):
        raise Refused("Jira did not answer the permission check (status %d), so nothing is assumed" % status)
    return {name: isinstance(found.get(name), dict) and found[name].get("havePermission") is True for name in names}


def read_history(conn, issue_id):
    """The last entries of the item's history: (how many Jira says there are, [{"id", "moves": [(from id, to id)]}])."""
    path = "/rest/api/3/issue/%s/changelog" % issue_id
    status, _, body = conn.get(path, {"startAt": 0, "maxResults": 100})
    total = body.get("total") if status == 200 and isinstance(body, dict) else None
    if type(total) is int and total > 100:
        status, _, body = conn.get(path, {"startAt": total - 100, "maxResults": 100})
    values = body.get("values") if status == 200 and isinstance(body, dict) else None
    if type(total) is not int or not isinstance(values, list):
        return None, []
    entries = []
    for raw in values:
        if not (isinstance(raw, dict) and ident(raw.get("id")) and isinstance(raw.get("items"), list)):
            return None, []
        moves = [(item.get("from"), item.get("to")) for item in raw["items"] if isinstance(item, dict) and item.get("field") == "status"]
        entries.append({"id": raw["id"], "moves": moves})
    return total, entries


# ---------------------------------------------------------------- what a move is, and which are supported


def open_subtasks(item):
    """(keys of subtasks not in a done status, how many have a status that could not be read)."""
    return ([s["key"] for s in item["subtasks"] if s["status"] is not None and s["status"]["category"] != "done"], sum(1 for s in item["subtasks"] if s["status"] is None))


def judge(item, move):
    """Whether this workflow will make a move Jira offers: (True, None) or (False, the reason)."""
    if not move.get("fields_told", True):
        return False, "Jira did not say which fields this move asks for, so it cannot be told whether one is required. Nothing is assumed"
    if move["required"]:
        return False, "it asks for %s (%s) and this workflow sends the move and nothing else. Make this move in Jira, where the form can be seen" % (
            plural(len(move["required"]), "required field"), ", ".join(move["required"]))
    if move["to"]["category"] == "done":
        still_open, unread = open_subtasks(item)
        if not item["subtasks_listed"] or unread:
            return False, "it leads to a done status, and the status of %s could not be read. \"Could not check\" is not \"none open\"" % (
                plural(unread, "subtask") if item["subtasks_listed"] else "the subtasks")
        if still_open:
            return False, "it leads to a done status while %s not done (%s). Finish the subtasks first. There is no override" % (
                "%d subtasks are" % len(still_open) if len(still_open) != 1 else "1 subtask is", ", ".join(still_open))
    return True, None


def touches(item, move):
    """What else a move touches besides the status, in words."""
    said = []
    if move["to"]["category"] == "done":
        said.append("It leads to a done status: reports will count the item as finished. Jira may set a resolution; whether it does is not known before the move, and is read back after it")
    elif item["status"]["category"] == "done":
        said.append("It leads out of a done status: reports will count the item as open again. Jira may clear the resolution; that is read back after the move")
    else:
        said.append("Neither status is a done status, so the resolution should stay as it is%s. It is read back after the move" % (" (empty)" if not item["resolution"] else ""))
    still_open, unread = open_subtasks(item)
    said.append("Subtasks: %d, of which %d not done%s. A move of the parent does not move them" % (len(item["subtasks"]), len(still_open), " and %d unreadable" % unread if unread else ""))
    return said


def build_proposal(conn, request, allowlist_path):
    """The one place that decides what a request means. The preview shows its result; confirm compares with it.
    Returns (proposal, the item as read)."""
    allowed, note = load_allowlist(allowlist_path)
    site = site_fingerprint(conn.host)
    item = read_item(conn, request["issue"], "the item %s" % quoted(request["issue"]))
    if (site, item["project_id"]) not in allowed:
        raise Refused("%s is in project %s (project id %s), which on the Jira site with fingerprint %s is not on the sandbox allowlist (%s). "
                      "This workflow writes only to a project listed there" % (item["key"], item["project_key"], item["project_id"], site, os.path.basename(allowlist_path)))
    permissions = read_permissions(conn, item["id"])
    if not all(permissions.values()):
        raise Refused("Jira says this identity may not move %s (TRANSITION_ISSUES: %s)" % (item["key"], "yes" if permissions["TRANSITION_ISSUES"] else "no"))
    moves = read_moves(conn, item["id"], item["key"])
    still_open, unread = open_subtasks(item)
    history_total, _ = read_history(conn, item["id"])
    if history_total is None:
        raise Refused("Jira did not give the history of %s, so the entry a move makes there could not be told from an older one. Nothing is assumed" % item["key"])
    proposal = {"site": site, "request": request["name"], "source": request["source"], "source_sha": request["source_sha"], "allowlist": note,
                "issue": {"id": item["id"], "key": item["key"], "project_id": item["project_id"], "project_key": item["project_key"]},
                "from": item["status"], "wanted": request["to"], "resolution_before": item["resolution"], "permissions": permissions,
                "subtasks": {"total": len(item["subtasks"]), "open": still_open, "unread": unread},
                "seen": {"updated": item["updated"], "history_entries": history_total},        # so that a confirmation can tell that the item changed and came back
                "offered": [{"id": m["id"], "name": m["name"], "to": m["to"]["name"]} for m in moves]}
    if item["status"]["name"] == request["to"]:
        proposal.update(action="nothing", move=None, to=item["status"], not_sent=[])
        return proposal, item
    leading = [move for move in moves if move["to"]["name"] == request["to"]]
    if not leading:
        offered = ", ".join("%s (by the move %s)" % (quoted(m["to"]["name"]), quoted(m["name"])) for m in moves) or "none"
        raise Refused("THE WORKFLOW DOES NOT ALLOW THIS MOVE. %s has the status %s, and Jira offers no move from there to %s for this identity. "
                      "From %s Jira offers: %s. A status name is matched exactly. Nothing was previewed"
                      % (item["key"], quoted(item["status"]["name"]), quoted(request["to"]), quoted(item["status"]["name"]), offered))
    if len(leading) > 1:
        raise Refused("Jira offers %d moves from %s to %s (%s), so the request does not say which is meant. Make this move in Jira"
                      % (len(leading), quoted(item["status"]["name"]), quoted(request["to"]), ", ".join(quoted(m["name"]) for m in leading)))
    move = leading[0]
    supported, why_not = judge(item, move)
    if not supported:
        raise Refused("THIS WORKFLOW DOES NOT MAKE THIS MOVE. Jira offers the move %s from %s to %s for %s, and %s. Nothing was previewed"
                      % (quoted(move["name"]), quoted(item["status"]["name"]), quoted(move["to"]["name"]), item["key"], why_not))
    proposal.update(action="move", move={"id": move["id"], "name": move["name"]}, to=move["to"], not_sent=move["optional"])
    return proposal, item


def snapshot(item, history_total):
    """One short code for what Jira returned of the item: its last-changed time, status, resolution, subtasks and the
    number of entries in its history."""
    text = canonical([item["id"], item["updated"], item["status"]["id"], item["resolution"], [[s["key"], s["status"]["id"] if s["status"] else None] for s in item["subtasks"]], history_total])
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def fingerprint_of(proposal, made_at):
    return sha_of(canonical({"proposal": proposal, "made_at": made_at}))


def requests_line(conn):
    kinds = sorted(set(method for method, _ in conn.sent))
    say("Requests sent to Jira: %d. %s" % (len(conn.sent), "Every one was a GET, which reads and cannot change anything."
                                           if kinds == ["GET"] else "Kinds: %s." % ", ".join(kinds)))
    for method, path in conn.sent:
        say("  %s %s" % (method, path))


def head(conn, proposal):
    issue = proposal["issue"]
    say("Jira site:  https://%s  (site fingerprint %s)" % (conn.host, proposal["site"]))
    say("Project:    %s (project id %s). On the sandbox allowlist: yes." % (issue["project_key"], issue["project_id"]))
    say("            The allowlist is %s." % proposal["allowlist"])
    say("Item:       %s (issue id %s)." % (issue["key"], issue["id"]))


# ---------------------------------------------------------------- rules


def cmd_rules(args, conn):
    if not 1 <= len(args.issue) <= MAX_RULES or any(not REF.fullmatch(ref) for ref in args.issue) or len(set(args.issue)) != len(args.issue):
        raise Refused("give 1 to %d different items, each by its key or issue id" % MAX_RULES)
    out = [RULES_HEADING, "",
           "**Written by a tool** (`participant/skills/jira-transition-status/transition.py rules`). Read from %s, site fingerprint %s. Nothing was written to Jira."
           % ("a real Jira" if args.source == "live" else "the made-up Jira (every item here is made up)", site_fingerprint(conn.host)), "",
           "A move is what Jira calls a transition. **In the tables for each item below, the move, its id, the two statuses and the fields were read from %s for the item named,** at the status"
           % ("Jira's workflow" if args.source == "live" else "the made-up Jira's workflow"),
           "the item had when it was read. None of those is assumed. The two sections before those tables, and the last column of each table, are **this tool's own statements**, the same on every run.", "",
           "## What Jira does and does not tell (this tool's statements, not read on this run)", "",
           "- Jira lists the moves open **to this identity, from the item's present status**. To see the moves from another status, an item in that status must be read.",
           "- **Conditions.** A move that a workflow condition hides from this identity is not listed at all, and Jira does not say why. So the condition for every move below is the same:",
           "  Jira offered it. A move that is not listed is refused by this workflow, whatever the reason Jira left it out.",
           "- **Required fields.** Jira says which fields a move's form asks for, and which are required. That is read, and shown for each move.",
           "- **A required field is only seen if it is on the move's form.** A workflow can also reject a move with a rule of its own (a validator). Jira does not list those. Such a move is",
           "  previewed, and Jira refuses it at the write. The tool then reads the item and reports that nothing was written.",
           "- **Resolution.** Jira does not say whether a move will set or clear the resolution. It is read back after the move.",
           "- **\"Done\" means the status's category is `done`,** as Jira gives it. The status's name is not looked at.",
           "- **Subtasks are the ones Jira lists on the item for this identity.** One that Jira does not list is not seen. Stories under an epic are not subtasks, and are not looked at.", "",
           "## What this workflow supports (this tool's rules)", "",
           "It sends the move and nothing else: no field, no comment. So, for a move Jira offers:", "",
           "| The move | Supported | Why |", "|---|---|---|",
           "| has no required field, and does not lead to a done status | yes | |",
           "| has a **required field** | **no** | The workflow cannot fill it in. Make the move in Jira, where the form can be seen |",
           "| has optional fields only | yes | They are listed in the preview as not sent |",
           "| leads to a **done** status, and every subtask is done or there are none | yes | The resolution is read back, and an empty one is reported for a person to look at |",
           "| leads to a **done** status while a **subtask is not done** | **no** | Refused before the preview. No override. Finish the subtasks first |",
           "| leads to a **done** status and a subtask's status **cannot be read** | **no** | \"Could not check\" is not \"none open\" |",
           "| is one of two offered moves to the same status | **no** | The request names a status, and would not say which move is meant |", ""]
    say("TRANSITION RULES. Nothing is written to Jira by this command.")
    say("")
    say("Jira site:  https://%s  (site fingerprint %s)" % (conn.host, site_fingerprint(conn.host)))
    for ref in args.issue:
        item = read_item(conn, ref, "the item %s" % quoted(ref))
        moves = read_moves(conn, item["id"], item["key"])
        still_open, unread = open_subtasks(item)
        say("")
        say("%s (issue id %s), in project %s. Status now: %s (category %s). Resolution: %s. Subtasks: %d, not done: %d%s."
            % (item["key"], item["id"], item["project_key"], quoted(item["status"]["name"]), item["status"]["category"], quoted(item["resolution"]) if item["resolution"] else "none",
               len(item["subtasks"]), len(still_open), ", unreadable: %d" % unread if unread else ""))
        out += ["## %s, read at the status %s" % (item["key"], quoted(item["status"]["name"])), "",
                "Issue id %s, project %s, type %s. Status category `%s`. Resolution: %s. Subtasks: %d, of which %d not done%s." % (
                    item["id"], item["project_key"], quoted(item["type"]), item["status"]["category"], quoted(item["resolution"]) if item["resolution"] else "none", len(item["subtasks"]), len(still_open),
                    " and %d whose status could not be read" % unread if unread else ""), ""]
        if not moves:
            say("  Jira offers no move from this status for this identity.")
            out += ["Jira offers **no move** from this status for this identity.", ""]
            continue
        out += ["| Move (Jira's id) | From | To (category) | Required fields | Optional fields | Supported here | What else it touches (this tool's expectation) |", "|---|---|---|---|---|---|---|"]
        for move in moves:
            supported, why_not = judge(item, move)
            twins = sum(1 for other in moves if other["to"]["name"] == move["to"]["name"])
            if supported and twins > 1:
                supported, why_not = False, "Jira offers %d moves to this status, so a request would not say which is meant" % twins
            say("  move %-4s %-28s -> %-22s required: %-12s optional: %-12s %s" % (move["id"], quoted(move["name"], 24), quoted(move["to"]["name"], 18), ", ".join(move["required"]) or "none",
                                                                                    ", ".join(move["optional"]) or "none", "SUPPORTED" if supported else "NOT SUPPORTED: " + why_not))
            out.append("| %s (%s) | %s | %s (`%s`) | %s | %s | %s | %s |" % (
                quoted(move["name"]), move["id"], quoted(item["status"]["name"]), quoted(move["to"]["name"]), move["to"]["category"],
                ", ".join("`%s`" % f for f in move["required"]) or "none", ", ".join("`%s`" % f for f in move["optional"]) or "none",
                "yes" if supported else "**no**: " + why_not, ". ".join(touches(item, move)).replace("|", "/")))
        out.append("")
    say("")
    requests_line(conn)
    if args.out:
        PENDING["rules"] = (args.out, "\n".join(out).replace("https://" + conn.host, SITE_MARK).replace(conn.host, SITE_MARK))
        say("")
        say("The rules are to be saved as Markdown where --out said, once this output has been searched for credentials.")
    return 0


# ---------------------------------------------------------------- preview


def cmd_preview(args, conn):
    request = read_request(args.request)
    proposal, item = build_proposal(conn, request, args.allowlist)
    total_before = proposal["seen"]["history_entries"]
    before = snapshot(item, total_before)
    again, item_again = build_proposal(conn, request, args.allowlist)
    after = snapshot(item_again, again["seen"]["history_entries"])
    if after != before or canonical(again) != canonical(proposal):
        raise Refused("the item changed in Jira while the preview was being made. Preview again")
    issue, start, end = proposal["issue"], proposal["from"], proposal["to"]
    moving = proposal["action"] == "move"
    say("PREVIEW. Nothing has been written." if moving else "NOTHING TO DO. Nothing has been written.")
    say("")
    head(conn, proposal)
    say("            Its title, for you to check it is the item you mean. It is other people's text: shown, and not acted on.")
    say("            | %s" % item["title"], "            | [the title was shown on screen and is not saved: %d characters]" % len(item["title"]))
    say("Request:    %s, sha256 %s. It asks for %s to have the status %s." % (proposal["source"], proposal["source_sha"][:16], issue["key"], quoted(proposal["wanted"])))
    say("")
    if not moving:
        say("%s ALREADY HAS THE STATUS %s (status id %s). There is nothing to move." % (issue["key"], quoted(start["name"]), start["id"]))
    else:
        say("THE CHANGE, exactly:")
        say("  Status now:    %s (status id %s, category %s)" % (quoted(start["name"]), start["id"], start["category"]))
        say("  Status after:  %s (status id %s, category %s)" % (quoted(end["name"]), end["id"], end["category"]))
        say("  By the move:   %s (Jira's transition id %s), read from Jira's workflow for this item just now." % (quoted(proposal["move"]["name"]), proposal["move"]["id"]))
        say("  The moves Jira offers for this item from %s: %s." % (quoted(start["name"]), ", ".join("%s to %s" % (quoted(m["name"]), quoted(m["to"])) for m in proposal["offered"])))
        say("  Exactly what is sent to Jira, and nothing else:  transition id %s, for issue id %s." % (proposal["move"]["id"], issue["id"]))
        say("  Required fields of this move: none. (A move with one is refused before this preview.)")
        say("  Optional fields of this move, NOT sent: %s." % (", ".join(proposal["not_sent"]) or "none"))
        say("")
        say("WHAT ELSE IT TOUCHES:")
        for line in touches(item, {"to": end}):
            say("  %s." % line)
        say("  Resolution now: %s." % (quoted(proposal["resolution_before"]) if proposal["resolution_before"] else "none"))
    say("")
    say("Permission check, asked of Jira for this item and this identity (may see it / may move it): %s / %s"
        % ("yes" if proposal["permissions"]["BROWSE_PROJECTS"] else "no", "yes" if proposal["permissions"]["TRANSITION_ISSUES"] else "no"))
    say("Duplicate check, made against Jira just now: the item's status is %s, which is %s the status asked for. Its history has %s."
        % (quoted(start["name"]), "ALREADY" if not moving else "not", "%d entr%s" % (total_before, "y" if total_before == 1 else "ies")))
    say("Where Jira cannot check: its request to move an item has no 'only if the status is still this' condition. The")
    say("  confirmation reads the item again just before writing, sends nothing if it already has the status asked for,")
    say("  and stops if it has any other status than the one shown here.")
    say("")
    say("Snapshot of the item, as Jira returned it, before the preview: %s" % before)
    say("Snapshot of the item, as Jira returned it, after the preview:  %s" % after)
    say("The two are the same. Jira is unchanged, as far as two reads can show. A snapshot is of the item's last-changed")
    say("  time, status, resolution, subtasks' statuses and the number of entries in its history.")
    requests_line(conn)
    say("")
    if not moving:
        say("No fingerprint is issued, because there is nothing to confirm, and nothing was sent.")
        return 0
    made = now_utc()
    made_at, expires_at = stamp(made), stamp(made + datetime.timedelta(minutes=LIMIT_MINUTES))
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
    say("Nothing has been written. To make this move, a person who has read this preview confirms it by its fingerprint.")
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
    except (OSError, ValueError, KeyError, TypeError):
        raise Refused("the saved preview %s cannot be read, so it cannot be confirmed" % code)
    if genuine != saved.get("fingerprint") or genuine[:12] != code:
        raise Refused("the saved preview %s has been altered since it was made, so it cannot be confirmed" % code)
    if not (isinstance(status, str) and good_record(saved["proposal"]) and saved["proposal"].get("action") == "move"):
        raise Refused("the saved preview %s does not hold what a preview holds, so it cannot be confirmed" % code)
    return path, saved, made, status


def good_record(record):
    """Whether a saved preview's proposal, or a saved write, names its item, statuses and move in the shapes this tool
    writes. A record is read from a file, and a file can be edited."""
    try:
        issue, start, end, move = record["issue"], record["from"], record["to"], record["move"]
        return (ident(issue["id"]) and ident(issue["project_id"]) and all(isinstance(issue[k], str) and REF.fullmatch(issue[k]) for k in ("key", "project_key"))
                and all(ident(status["id"]) and plain_name(status["name"]) and re.fullmatch(r"[a-z]{1,20}", status["category"]) for status in (start, end))
                and ident(move["id"]) and plain_name(move["name"]))
    except (KeyError, TypeError):
        return False


def differences(before, now):
    """How the request worked out now differs from the preview: a list of words, empty if it is the same."""
    if before["source_sha"] != now["source_sha"] or before["source"] != now["source"]:
        return ["the request is not the file the preview showed"]
    if before["allowlist"] != now["allowlist"]:
        return ["the allowlist file is not the one the preview used"]
    said = []
    if before["issue"] != now["issue"]:
        said.append("the reference now leads to another item, or the item has moved to another project or been given another key")
    if before["from"] != now["from"]:
        said.append("the item's status is %s now, and was %s when previewed" % (quoted(now["from"]["name"]), quoted(before["from"]["name"])))
    if (before["move"], before["to"], before["not_sent"]) != (now["move"], now["to"], now["not_sent"]):
        said.append("the move Jira offers to that status is not the one the preview showed")
    if before["subtasks"] != now["subtasks"] or before["resolution_before"] != now["resolution_before"]:
        said.append("what the preview showed of the subtasks or the resolution is no longer so")
    if not said and before.get("seen") != now.get("seen"):
        said.append("the item has been changed in Jira since the preview (its last-changed time or the number of entries in its history is not what the preview saw), even if its status is the same")
    if not said and canonical(before) != canonical(now):
        said.append("what Jira returns for this request is not what the preview showed")
    return said


def cmd_confirm(args, conn):
    code = (args.fingerprint or "").strip().lower()
    if not code:
        raise Refused("no confirmation was given. A confirmation names the fingerprint of the preview it approves, and there is no way to write without one")
    if len(code) != 12 or any(ch not in "0123456789abcdef" for ch in code):
        raise Refused("a fingerprint is 12 characters, each 0 to 9 or a to f")
    name = (args.confirmed_by or "").strip()
    if not name:
        raise Refused("no confirmation was given. A confirmation gives the name of the person confirming")
    if len(name) > 60 or "@" in name or UNSEEN.search(name):
        raise Refused("the confirming person's name must be short plain text, and not an email address")
    request = read_request(args.request)
    claim = claim_request(args.state, request["name"])
    try:
        return confirm_claimed(args, conn, request, code, name, claim)
    finally:
        release(claim)


def confirm_claimed(args, conn, request, code, name, claim):
    preview_file, saved, made, status = read_preview_record(args.state, code)      # read AFTER the claim
    if status != "open":
        raise Refused("the preview %s has been used (recorded as '%s'). A fingerprint is used once. Preview again: if the item "
                      "already has the status asked for, the preview says so and offers nothing" % (code, status))
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
    if site_fingerprint(conn.host) != before["site"]:
        raise Refused("this is not the Jira site the preview was made against. Make a new preview and read it")
    if before.get("request") != request["name"]:
        raise Refused("the preview %s was made for another request file. Make a new preview and read it" % code)
    if (before["source"], before["source_sha"]) != (request["source"], request["source_sha"]):
        raise Refused("the change is not the one that was previewed: the request is not the file the preview showed. Make a new preview and read it")
    issue, start, end, move = before["issue"], before["from"], before["to"], before["move"]

    # The first look: where the item is now decides which of three things this run is.
    item = read_item(conn, issue["id"], issue["key"])
    if item["status"]["id"] == end["id"] and item["status"]["id"] != start["id"]:
        saved["state"] = "not needed: the item already had the status"
        save_json(preview_file, saved)
        say("ALREADY DONE. Nothing was sent.")
        say("")
        head(conn, before)
        say("")
        say("%s already has the status %s (status id %s), which is the status preview %s asked for. No move was sent, and no" % (issue["key"], quoted(end["name"]), end["id"], code))
        say("result record was written by this run. The preview is marked as used and cannot be confirmed again.")
        say("")
        requests_line(conn)
        return 0
    if item["status"]["id"] != start["id"]:
        raise Refused("THE ITEM HAS BEEN MOVED SINCE THE PREVIEW. %s has the status %s now. The preview showed %s, to be moved to %s. Someone or "
                      "something moved it, and the preview no longer describes it. Make a new preview and read it"
                      % (issue["key"], quoted(item["status"]["name"]), quoted(start["name"]), quoted(end["name"])))
    proposal, item = build_proposal(conn, request, args.allowlist)
    differs = differences(before, proposal)
    if differs:
        raise Refused("the change is not the one that was previewed: %s. Make a new preview and read it" % "; ".join(differs))
    total_before, entries_before = read_history(conn, issue["id"])
    if total_before is None:
        raise Refused("Jira did not give the history of %s just before the write, so the entry the move makes could not be told from an older one. Nothing was sent" % issue["key"])
    known = set(entry["id"] for entry in entries_before)
    newest = max([int(entry["id"]) for entry in entries_before] or [0])

    say("CONFIRMATION for preview %s, given by: %s (the name given with the confirmation)." % (code, name))
    say("")
    head(conn, proposal)
    say("Move:       %s (transition id %s): from %s to %s." % (quoted(move["name"]), move["id"], quoted(start["name"]), quoted(end["name"])))
    say("")
    say("Checked in this run, before writing:")
    say("  the preview is %s old, and the limit is %d: ok" % (plural(int(age.total_seconds() // 60), "minute"), LIMIT_MINUTES))
    say("  what the saved preview holds still matches its fingerprint, and it is marked as not used: ok")
    say("  the request, worked out again against Jira, is exactly what the preview showed: ok")
    say("  the item is in a project on the sandbox allowlist for this site: ok")
    say("  Jira says this identity may move the item: ok")
    say("  the item still has the status the preview showed, %s: ok" % quoted(start["name"]))
    say("")

    result = {"fingerprint": saved["fingerprint"], "confirmed_by": name, "confirmed_at": stamp(confirmed), "preview_made_at": saved["made_at"],
              "site_fingerprint": proposal["site"], "source": proposal["source"], "source_sha": proposal["source_sha"], "issue": issue, "from": start, "to": end, "move": move,
              "status": "sending", "history_entry": None, "written_at": None, "read_back": None, "resolution_before": proposal["resolution_before"], "resolution_after": None}
    written_file = os.path.join(args.state, "written", code + ".json")
    if not holds(claim):
        raise Refused("this run's claim on the request has been taken by another run, so it sends nothing")
    saved["state"] = "writing"
    save_json(preview_file, saved)
    save_json(written_file, result)        # written down BEFORE the request goes
    say("The confirmation and the write happen in this one run of the command.")
    say("")

    answered, body = None, {}
    try:
        answered, _, body = conn.post_move(issue["id"], move["id"])
    except (OSError, TimeoutError) as err:
        say("The write was sent and NO ANSWER came back (%s). It was not sent again. Reading the item to see:" % type(getattr(err, "reason", err)).__name__)
    accepted = answered in (200, 204)
    item = read_item(conn, issue["id"], issue["key"])
    for _ in range(READ_AGAIN):
        if not accepted or item["status"]["id"] != start["id"]:
            break
        say("Jira accepted the write and the item does not show the move yet. Reading it again in %d seconds. The write is not sent again." % PAUSE_SECONDS)
        pause()
        item = read_item(conn, issue["id"], issue["key"])
    moved, unmoved = item["status"]["id"] == end["id"], item["status"]["id"] == start["id"]

    def stop(status):
        result["status"] = status
        save_json(written_file, result)

    if answered is not None and not accepted:
        if answered in REFUSALS and unmoved:
            stop("Jira refused it (%d) and nothing was written" % answered)
            raise NotWritten("Jira answered %d to the write, and read back afterwards %s still has the status %s, so it was not moved. What Jira said in "
                             "refusing is not repeated here" % (answered, issue["key"], quoted(start["name"])))
        stop("sent, and Jira answered %d" % answered)
        raise NeedsLooking("Jira answered %d to the write. Read back afterwards, %s has the status %s. IT IS NOT KNOWN whether this run moved it. "
                           "Look at the item's history in Jira" % (answered, issue["key"], quoted(item["status"]["name"])))
    if not moved:
        stop("sent, and read back as %s" % item["status"]["name"])
        raise NeedsLooking("the write was sent%s, and read back afterwards %s has the status %s. The status intended was %s. %s"
                           % (" and Jira accepted it (%d)" % answered if accepted else " and no answer came", issue["key"], quoted(item["status"]["name"]), quoted(end["name"]),
                              "IT IS NOT KNOWN whether the move will still arrive. Preview again in a minute" if unmoved else "Something else moved it, or the workflow moved it on. Look at the item's history in Jira"))
    def new_entries():
        _, entries_after = read_history(conn, issue["id"])
        return [entry for entry in entries_after if entry["id"] not in known and int(entry["id"]) > newest and (start["id"], end["id"]) in entry["moves"]]
    new = new_entries()
    for _ in range(READ_AGAIN):
        if new:
            break
        say("The item shows the new status and its history does not show the entry for it yet. Reading the history again in %d seconds." % PAUSE_SECONDS)
        pause()
        new = new_entries()
    result.update({"status": "written", "written_at": stamp(now_utc()), "resolution_after": item["resolution"], "history_entry": new[0]["id"] if len(new) == 1 else None})
    save_json(written_file, result)        # kept at once
    say("WRITTEN to Jira.%s" % (" Jira answered %d." % answered if accepted else " No answer came to the write; the move was found by reading the item."))
    say("")
    say("Read back from Jira after the write:")
    checks = [("the status of %s is %s (status id %s). Intended: %s (status id %s)" % (issue["key"], quoted(item["status"]["name"]), item["status"]["id"], quoted(end["name"]), end["id"]), moved)]
    if new:
        checks.append(("the item's history has one new entry that records the status going from %s to %s%s"
                       % (quoted(start["name"]), quoted(end["name"]), ": entry id %s" % new[0]["id"] if len(new) == 1 else " (found: %d)" % len(new)), len(new) == 1))
    if end["category"] == "done":
        checks.append(("the status is a done status, and the resolution is set: %s" % (quoted(item["resolution"]) if item["resolution"] else "NO. THE RESOLUTION IS EMPTY"), bool(item["resolution"])))
    elif start["category"] == "done":
        checks.append(("the status is not a done status, and the resolution is empty%s" % ("" if not item["resolution"] else ": NO. A RESOLUTION IS STILL SET: %s" % quoted(item["resolution"])), not item["resolution"]))
    else:
        same = item["resolution"] == proposal["resolution_before"]
        checks.append(("neither status is a done status, and the resolution is as it was (%s)%s" % (quoted(proposal["resolution_before"]) if proposal["resolution_before"] else "none",
                                                                                                    "" if same else ": NO. IT IS NOW %s" % (quoted(item["resolution"]) if item["resolution"] else "none")), same))
    for what, ok in checks:
        say("  %s: %s" % (what, "yes" if ok else "NO"))
    if not new:
        say("  The item's history did not show an entry for this move in %d reads. The status read back above is what stands as the record of the change." % (READ_AGAIN + 1))
    still_open, unread = open_subtasks(item)
    say("  Subtasks after the move: %d, of which %d not done%s." % (len(item["subtasks"]), len(still_open), " and %d unreadable" % unread if unread else ""))
    result["read_back"] = [[what, ok] for what, ok in checks]
    save_json(written_file, result)
    saved["state"] = "written"
    save_json(preview_file, saved)
    finish(args, conn, result)
    say("")
    requests_line(conn)
    if not all(ok for _, ok in checks):
        problem = ("THE ITEM IS IN A DONE STATUS WITH NO RESOLUTION. Reports that count resolved work will not agree with its status. Set a resolution in Jira, or move it back"
                   if end["category"] == "done" and not item["resolution"] and checks[0][1] and checks[1][1] else "the move was written, and it does not read back as intended. See the lines marked NO")
        raise NeedsLooking("%s was moved to %s, and: %s" % (issue["key"], quoted(end["name"]), problem))
    say("")
    say("ALL DONE: %s was moved from %s to %s, and reads back as intended." % (issue["key"], quoted(start["name"]), quoted(end["name"])))
    return 0


def result_lines(result):
    issue, back = result["issue"], result["read_back"]
    return ["Issue key: %s" % issue["key"],
            "Issue id: %s (this identifies the item; a key can change)" % issue["id"],
            "Target project: %s (project id %s), on the sandbox allowlist" % (issue["project_key"], issue["project_id"]),
            "Jira site: %s, site fingerprint %s" % (SITE_MARK, result["site_fingerprint"]),
            "Request: %s (file sha256 %s)" % (result["source"], result["source_sha"]),
            "What was changed: the status, from %s (status id %s) to %s (status id %s)" % (quoted(result["from"]["name"]), result["from"]["id"], quoted(result["to"]["name"]), result["to"]["id"]),
            "By the move: %s (Jira's transition id %s). Nothing else was sent" % (quoted(result["move"]["name"]), result["move"]["id"]),
            "Identifier of what was changed: %s" % ("Jira history entry %s" % result["history_entry"] if result["history_entry"] else "no single new history entry was found; the read-back value below stands in for it"),
            "Read back from Jira after the write: %s" % ("; ".join("%s: %s" % (what, "yes" if ok else "NO") for what, ok in back) if back else "not read back by this run"),
            "Resolution: before %s; after %s" % (quoted(result["resolution_before"]) if result["resolution_before"] else "none", quoted(result["resolution_after"]) if result["resolution_after"] else "none"),
            "Status of this record: %s" % result["status"],
            "Written at: %s" % (result["written_at"] or "not written by this run"),
            "Confirmed by: %s, at %s" % (result["confirmed_by"], result["confirmed_at"]),
            "Preview: fingerprint %s, made %s" % (result["fingerprint"][:12], result["preview_made_at"]),
            "To reverse: make a new preview that asks for the status %s. It will be made only if the workflow offers a move back" % quoted(result["from"]["name"])]


def finish(args, conn, result):
    lines = result_lines(result)
    say("")
    say("RESULT RECORD")
    for line in lines:
        say("  " + line)
    if getattr(args, "result", None):
        text = "\n".join(["# Result record: one Jira item moved to another status", ""] + ["- " + line for line in lines]) + "\n"
        PENDING["result"] = (args.result, text.replace(conn.host, SITE_MARK))
        say("")
        say("The result record is to be saved as Markdown where --result said, once this output has been searched for credentials.")


OWN_FILES = {      # how each kind of file this tool saves begins. A file that is there and begins otherwise is not written over
    "log": re.compile(rb"(TRANSITION RULES\. |PREVIEW\. Nothing has been written\.|NOTHING TO DO\. Nothing has been written\.|CONFIRMATION for preview [0-9a-f]{12}, given by: |ALREADY DONE\. Nothing was sent\.|"
                      rb"STATUS CHECK for the write of preview |TEST CLOCK: pretending it is |\nREFUSED: |\nA PERSON NEEDS TO LOOK: )"),
    "result": re.compile(rb"# Result record: one Jira item moved to another status\n"),
    "rules": re.compile(rb"# Transition rules\n"),
}


def same_file(a, b):
    try:
        if os.path.exists(a) and os.path.exists(b):
            return os.path.samefile(a, b)
    except OSError:
        pass
    return os.path.realpath(a).casefold() == os.path.realpath(b).casefold()


def check_places(args):
    """Before anything is asked of Jira: every place this run was told to save a file is one it may write. A place is
    refused if its folder is not there, if it is a link, a folder or a file with a second name, if it is inside the
    state folder, if it is the request or the allowlist, if two of them are one file, or if a file is already there
    that does not begin as this tool's own file of that kind begins."""
    places = [(kind, getattr(args, option, None), "--" + option) for kind, option in (("log", "log"), ("result", "result"), ("rules", "out")) if getattr(args, option, None)]
    inputs = [path for path in (getattr(args, "request", None), getattr(args, "allowlist", None)) if path]
    state = os.path.realpath(args.state) if getattr(args, "state", None) else None
    for number, (kind, path, option) in enumerate(places):
        full = os.path.realpath(path)
        problem = None
        if not os.path.isdir(os.path.dirname(os.path.abspath(path))):
            problem = "its folder is not there"
        elif os.path.islink(path) or os.path.isdir(path) or (os.path.exists(path) and (not os.path.isfile(path) or os.stat(path).st_nlink > 1)):
            problem = "it is a link, a folder, or a file with a second name"
        elif state and (full == state or full.startswith(state + os.sep)):
            problem = "it is inside the state folder"
        elif any(same_file(path, other) for other in inputs) or any(same_file(path, other) for _, other, _ in places[:number]):
            problem = "it is the request, the allowlist, or another file this run saves"
        elif os.path.exists(path):
            with open(path, "rb") as f:
                if not OWN_FILES[kind].match(f.read(200)):
                    problem = "a file is already there, and it does not begin as this tool's own file of that kind begins"
        if problem:
            raise Refused("%s names a place this tool will not write: %s. Nothing was asked of Jira" % (option, problem))


def write_whole(path, text):
    tmp = "%s.%d.tmp" % (path, os.getpid())
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    os.replace(tmp, path)


def write_pending():
    """Saves the result record or the rules. Called only after the output has been searched for credentials."""
    for which in list(PENDING):
        path, text = PENDING.pop(which)
        write_whole(path, text)


def show(text):
    """Prints, and does not fail if the terminal cannot show a character or has gone away. What was sent to Jira has
    been sent by now; the output must not be lost to a terminal's limits."""
    try:
        print(text)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "ascii"
        print(text.encode(encoding, "backslashreplace").decode(encoding, "replace"))
    except (BrokenPipeError, ValueError):
        pass


# ---------------------------------------------------------------- check


def cmd_check(args, conn):
    code = (args.fingerprint or "").strip().lower()
    if len(code) != 12 or any(ch not in "0123456789abcdef" for ch in code):
        raise Refused("a fingerprint is 12 characters, each 0 to 9 or a to f")
    try:
        with open(os.path.join(args.state, "written", code + ".json"), encoding="utf-8") as f:
            result = json.load(f)
        issue, end, site, entry = result["issue"], result["to"], result["site_fingerprint"], result["history_entry"]
        wanted = (result["from"]["id"], end["id"])
        if not good_record(result) or not (entry is None or ident(entry)) or not isinstance(site, str):
            raise ValueError("not a record of a write")
    except FileNotFoundError:
        raise Refused("there is no record of a write for the fingerprint %s" % code)
    except (OSError, ValueError, KeyError, TypeError):
        raise Refused("the record of the write %s cannot be read" % code)
    if site_fingerprint(conn.host) != site:
        raise Refused("this is not the Jira site the move was written to")
    say("STATUS CHECK for the write of preview %s. Nothing is written by this command." % code)
    say("")
    say("Jira site:  https://%s  (site fingerprint %s)" % (conn.host, site))
    item = read_item(conn, issue["id"], issue["key"])
    _, entries = read_history(conn, issue["id"])
    good = item["status"]["id"] == end["id"]
    say("Item:       %s (issue id %s)." % (item["key"], item["id"]))
    say("")
    say("  the status of %s is %s (status id %s). Intended: %s (status id %s): %s" % (item["key"], quoted(item["status"]["name"]), item["status"]["id"], quoted(end["name"]), end["id"], "yes" if good else "NO"))
    if entry:
        there = any(e["id"] == entry and wanted in e["moves"] for e in entries)
        say("  history entry %s is in the item's history and records that move: %s" % (entry, "yes" if there else "NO"))
        good = good and there
    say("  Resolution now: %s." % (quoted(item["resolution"]) if item["resolution"] else "none"))
    say("")
    requests_line(conn)
    say("")
    say("FOUND: the item has the status intended." if good else "NOT AS INTENDED: see the lines marked NO above. The item may have been moved since.")
    return 0 if good else 1


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
            return {"rules": cmd_rules, "preview": cmd_preview, "confirm": cmd_confirm, "check": cmd_check}[args.command](args, conn)
        except NotWritten as refusal:
            say("")
            say("REFUSED: %s." % refusal)
            return 1
        except Refused as refusal:
            if conn.posted():
                raise NeedsLooking("a write was sent, and a step after it could not be done: %s" % refusal)
            PENDING.clear()
            return refused(refusal)
        except NeedsLooking:
            raise
        except KeyboardInterrupt:
            if conn.posted():
                raise NeedsLooking("a write was sent, and the run was then interrupted. The item may have been moved")
            PENDING.clear()
            return refused("the run was interrupted before anything was sent")
        except Exception as failure:  # nothing may hide what was already sent
            if conn.posted():
                raise NeedsLooking("a write was sent, and the program then failed (%s). The item may have been moved" % type(failure).__name__)
            PENDING.clear()
            return refused("the program failed before anything was sent (%s)" % type(failure).__name__)
    except NeedsLooking as problem:
        say("")
        say("A PERSON NEEDS TO LOOK: %s." % problem)
        if args.command == "confirm":
            say("Do not confirm again with this fingerprint. Preview again: it reads the item and says what status it has.")
        return 2


def person_present(stream):
    """True if the run was started from a terminal. It keeps out a program that has none. It does not prove who typed."""
    try:
        return bool(stream.isatty())
    except (AttributeError, ValueError):
        return False


def main(argv=None):
    parser = argparse.ArgumentParser(description="Ask Jira which moves are allowed, preview one, confirm it, and read the status back.")
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("rules", "preview", "confirm", "check"):
        sub = commands.add_parser(command)
        sub.add_argument("--source", choices=("live", "fake"), required=True)
        sub.add_argument("--state", required=command != "rules", help="the folder where previews and write records are kept")
        sub.add_argument("--log", help="also save the output here, with the site's address and the item's title removed")
        if command == "rules":
            sub.add_argument("--issue", action="append", required=True, help="an item to read the moves of. May be given up to %d times" % MAX_RULES)
            sub.add_argument("--out", help="save the rules here, as Markdown")
        if command in ("preview", "confirm"):
            sub.add_argument("--request", required=True, help="the request file")
            sub.add_argument("--allowlist", required=True, help="the sandbox allowlist")
        if command in ("confirm", "check"):
            sub.add_argument("--fingerprint")
        if command == "confirm":
            sub.add_argument("--confirmed-by")
            sub.add_argument("--result", help="save the result record here, as Markdown")
            sub.add_argument("--pretend-minutes-later", type=whole_number, default=0, metavar="N", help="tests only")
    args = parser.parse_args(argv)
    del LINES[:]
    PENDING.clear()
    writes = args.command == "confirm"       # the one command that is given a way to write, whatever the source
    secrets, conn, fake, fake_path = [], None, None, os.path.join(args.state, "fake-jira.json") if args.state else None
    try:
        check_places(args)
        if args.source == "fake":
            import fake_jira
            fake = fake_jira.FakeJira.open(fake_path) if fake_path else fake_jira.FakeJira()
            conn = Connection(fake.get, fake.post if writes else None, urllib.parse.urlparse(fake_jira.SITE).hostname)
        else:
            if writes and not person_present(sys.stdin):
                raise Refused("a real write is confirmed by a person at a terminal, and this run was not started from one")
            conn, secrets = make_live(writes)
        code = run(args, conn)
    except Refused as refusal:
        PENDING.clear()
        if "names a place this tool will not write" in str(refusal):
            args.log = None                 # the refusal is not saved where the run was refused for
        code = refused(refusal)
    if fake is not None and fake_path:
        fake.save(fake_path)
    text = "\n".join(shown for shown, _ in LINES)
    kept = "\n".join(saved for _, saved in LINES)
    if any(secret and secret in text + "".join(pending[1] for pending in PENDING.values()) for secret in secrets):
        wrote = bool(conn) and conn.posted()
        show("STOPPED: a credential was found in the output, so the output was not shown or saved.%s"
             % (" A WRITE WAS SENT TO JIRA in this run. Preview again before doing anything else: it says what status the item has." if wrote else ""))
        return 2 if wrote else 1
    notes = []
    try:
        write_pending()
    except OSError:
        notes.append("\nA FILE COULD NOT BE SAVED where --result or --out said. What the output above says stands.")
    if secrets:
        notes.append("\nThe output above was searched for the API token, the account's email address and their encoded\nform: none found.")
    if args.log:                # saved BEFORE it is shown, so that a terminal that fails does not lose it
        host = conn.host if conn else ""
        kept = "\n".join([kept] + notes)
        kept = kept.replace("https://" + host, SITE_MARK).replace(host, SITE_MARK) if host else kept
        try:
            write_whole(args.log, kept + "\n")
        except OSError:
            notes.append("\nTHE OUTPUT ABOVE COULD NOT BE SAVED where --log said. What it says stands.")
    show("\n".join([text] + notes))
    return code


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    sys.exit(main())
