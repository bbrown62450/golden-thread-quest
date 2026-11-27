#!/usr/bin/env python3
"""Compares a local copy of a Jira project with Jira as it is now, and accounts for EVERY item: each is given exactly
one state, the states add up to the total, and each item that is not simply in sync says why and what to do next.
IT ONLY READS JIRA, and it changes nothing in the local copy.

    reconcile.py report --source live|fake --copy COPY.json --out-dir DIR --name NAME [--as-of TIME] [--log FILE]
    reconcile.py adopt  --from RESULT.json --out COPY.json
    reconcile.py states

`report` writes three files in DIR, and no others:

    NAME.md             the report
    NAME.log.md         every request that was made, one numbered line each. The report cites these lines
    NAME.history.json   the counts of the runs so far, for the trend. One entry for each distinct input

WHAT IS CONSIDERED. Every item on either side: each item the local copy holds, and each item Jira lists for the
project that the copy does not hold. A report that walked only the local copy could say "118 of 118" and never see
twelve items that were never copied.

THE STATES. `states` prints them. An item is given the FIRST of these that fits, and no other:

    1. failed to fetch        Jira could not be asked about it, or did not answer with an item. Nothing else can be
                              said about it, so this comes before everything
    2. missing from Jira      Jira answered that it is not there (404)
    3. conflicted             Jira has changed it since it was copied, AND the copy was changed locally
    4. changed locally only   the copy was changed locally, and Jira has not changed
    5. stale                  Jira has changed it since it was copied, and the copy has not been changed locally
    6. not yet copied         Jira lists it and the local copy does not hold it
    7. synchronized           none of the above: Jira has what the copy has

So "synchronized" is never a default. It is what is left when six things have been ruled out. An item that also
fits a later state than its own says so on its line ("also: ..."), and the report counts those.

The quest this was built for names five states. Two were added, 4 and 6, because without them an item could be in no
state at all, and the total would not be the number of items. The report says so itself.

NAMES ARE COMPARED AS JIRA WROTE THEM. A status or type name is other people's text, so what is KEPT of it is a
cleaned form: cut to 40 characters, with marks replaced by a question mark. Two different names can clean to the
same thing ("QA/Review" and "QA:Review"). So the copy also keeps a short checksum of the two names as Jira wrote
them, and that is what is compared. A copy made without the checksum (one adopted from another tool's result) is
compared by cleaned names, and the report says for how many items that is so, and what it could miss.

THE CHECK COMES FIRST. Before anything is written, the tool takes the numbers in the local copy and the numbers in
Jira's list, each straight from where it was read, and requires that every one of them was given exactly one state,
that no other item was, and that the counts add up. It also states the rule a second time, as what must be true of
an item in each state, and requires each item's state to agree with what was found for it. If any of that fails the
report is NOT written (exit code 3). The first section of the report is that check.
It is a check of the tool against itself. It cannot tell whether Jira's answers were right.

STALE. Age is how long the copy has been behind: from the time Jira says it changed the item to the time the report
is as of. The limit is 24 hours. Every item that is behind is listed, whatever its age, and its line says which
side of the limit it is on.

A FAILED ITEM NAMES ITS ERROR CLASS AND NOTHING JIRA SAID. A refusal from Jira can carry a title, a person's name or
an address. The report has a fixed list of classes ("rate limited (429)", "server error (5xx)", "timed out", ...)
and prints the class. The body of a refusal is never read into the report or the log.

IF JIRA'S LIST OF THE PROJECT CANNOT BE READ, items that Jira has and the copy lacks cannot be counted. The report is
still written for the items the copy holds, its first section says INCOMPLETE and why, and the exit code is 2.

THE SAME INPUT GIVES THE SAME REPORT. The input is the local copy, what Jira answered, the time the report is as of,
and the history of earlier runs, which the trend is drawn from. Items are in order of their numbers. With --as-of
the time is given; without it, it is the clock, and the age of a stale item will differ between two runs by the
time between them. The trend adds a run to the history only if that same input is not already in it, shows runs in
order of their times, and keeps the last 50.

THE THREE FILES ARE WRITTEN ONE AFTER ANOTHER, the report last. If a write fails partway the output says which were
written. The report and the fetch log each carry the same run mark, so a report beside a log of another run can be
told.

PEOPLE AND TITLES ARE NOT KEPT OR ASKED FOR. Status and type names are other people's text: each is cut to 40
characters and characters that are not letters, digits or a few marks are replaced by a question mark.

REQUESTS. Every one is a GET: one for each item the copy holds, by its number, and the pages of the project's list.
There is no code path that builds any other. What the output says about the requests is read back from each
request as it was built.

`adopt` contacts nothing. It turns a result file written by the saved-query tool (jira-query-stories) into a local
copy this tool can read, with each item marked as copied at the time that result was taken.

--as-of TIME sets the time the report is as of, such as 2026-11-20T12:00:00Z. It is needed with --source fake.
--log FILE saves the output with the site's address replaced by a marker.

For a live run the connection comes from the environment variables JIRA_BASE_URL, JIRA_EMAIL and JIRA_API_TOKEN. None
is stored. The output is searched for the token, the email address and their encoded form before it is shown.

Exit codes: 0 the report was written and accounts for every item; 1 REFUSED, or a write failed partway (the output
says which files were written, if any); 2 written, and INCOMPLETE because Jira's list could not be read; 3 the
report's own check failed, nothing written.
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
import tempfile
import urllib.error
import urllib.parse
import urllib.request

COPY_FORMAT = "jira-reconcile-copy/1"
HISTORY_FORMAT = "jira-reconcile-history/1"
REF = re.compile(r"([A-Za-z][A-Za-z0-9_]{0,30})-[0-9]{1,9}")
PROJECT = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,30}")
NAME = re.compile(r"[a-z][a-z0-9-]{0,60}")
STAMP = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z")
SITE_MARK = "[site address removed]"
SEARCH_PATH = "/rest/api/3/search/jql"
FIELDS = "issuetype,status,updated"            # no summary: titles are not asked for
PAGE = 100
MAX_PAGES = 200
MAX_ITEMS = 5000
STALE_LIMIT_HOURS = 24
REPORT_HEADING = "# Reconciliation report · project "
LOG_HEADING = "# Fetch log · project "
LOG_STARTS = (re.compile(rb"Project: [A-Z][A-Z0-9_]{0,30}\nCompared: the local copy given with --copy"), re.compile(rb"REFUSED: "), re.compile(rb"STOPPED: a credential was found"))
HISTORY_KEEPS = 50
# What must be true of an item for it to be in each state: the rule stated a second time, for the check that comes
# first. (what Jira answered, whether Jira changed it, whether it was changed locally). None means "either".
MUST_BE = {
    "failed to fetch": ("failed", None, None),
    "missing from Jira": ("gone", None, None),
    "conflicted": ("item", True, True),
    "changed locally only": ("item", False, True),
    "stale": ("item", True, False),
    "synchronized": ("item", False, False),
    "not yet copied": ("listed only", None, None),
}
UNSEEN = re.compile("[\\x00-\\x1f\\x7f-\\xa0\\u00ad\\u034f\\u061c\\u115f\\u1160\\u200b-\\u200f\\u2028\\u2029\\u202a-\\u202e\\u2060-\\u2069\\u2800\\u3164\\ufeff\\ud800-\\udfff\\U000e0000-\\U000e007f]")
KEPT_MARKS = " _()'-"

# The states, in the order they are tried. (name, what it means, whether it is an exception)
STATES = [
    ("failed to fetch", "Jira could not be asked about it, or did not answer with an item. Nothing else can be said about it.", True),
    ("missing from Jira", "Jira answered that it is not there.", True),
    ("conflicted", "Jira has changed it since it was copied, and the copy was changed locally.", True),
    ("changed locally only", "The copy was changed locally. Jira has not changed.", True),
    ("stale", "Jira has changed it since it was copied. The copy has not been changed locally.", True),
    ("not yet copied", "Jira lists it. The local copy does not hold it.", True),
    ("synchronized", "None of the above: Jira has what the copy has.", False),
]
STATE_NAMES = [name for name, _, _ in STATES]
# The classes of failure. A failed item is given one of these. Nothing Jira says in a refusal is used.
NEXT_FOR_FAILURE = {
    "forbidden (403)": "Ask whether this account should still be able to see the item. Nothing is known about it until it can.",
    "rate limited (429)": "Run the report again later. Nothing is known about the item until then.",
    "server error (5xx)": "Run the report again later. If it fails the same way, look at the item in Jira.",
    "timed out": "Run the report again. If it times out again, look at the connection before the item.",
    "network error": "Run the report again. If it fails again, look at the connection before the item.",
    "unreadable answer": "Jira answered, and not with an item this tool can read. Look at the item in Jira, and report it if it persists.",
    "unexpected status": "Run the report again. If the status is the same, look at the item in Jira.",
}

LINES = []


class Refused(Exception):
    """Nothing was written. The message is the reason."""


def say(text=""):
    LINES.append(text)


def clean(value, limit=40):
    if not isinstance(value, str) or not value.strip():
        return None
    return "".join(ch if (ch.isalnum() or ch in KEPT_MARKS) and not UNSEEN.match(ch) else "?" for ch in value)[:limit].strip() or None


def shown(text, limit=80):
    return "".join("?" if UNSEEN.match(ch) else ch for ch in str(text))[:limit]


def ident(value):
    return isinstance(value, str) and re.fullmatch(r"0|[1-9][0-9]{0,19}", value) is not None


def in_utc(value):
    if not isinstance(value, str):
        return None
    for shape in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.datetime.strptime(value, shape).astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except (ValueError, OverflowError):
            continue
    return None


def real_stamp(value):
    """Whether a text is a time written as 2026-11-20T12:00:00Z, and a time that exists."""
    if not isinstance(value, str) or not STAMP.fullmatch(value):
        return False
    try:
        datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return False
    return True


def seconds_between(earlier, later):
    shape = "%Y-%m-%dT%H:%M:%SZ"
    return int((datetime.datetime.strptime(later, shape) - datetime.datetime.strptime(earlier, shape)).total_seconds())


def span(seconds):
    if seconds < 0:
        return "no time (Jira dates the change after this report's clock)"
    days, rest = divmod(seconds, 86400)
    hours, rest = divmod(rest, 3600)
    minutes = rest // 60
    parts = [("%d day%s" % (days, "" if days == 1 else "s")) if days else "", ("%d hour%s" % (hours, "" if hours == 1 else "s")) if hours else "",
             ("%d minute%s" % (minutes, "" if minutes == 1 else "s")) if minutes else ""]
    return " ".join(p for p in parts if p) or "under a minute"


def names_checksum(kind, status):
    """A short checksum of a type name and a status name AS JIRA WROTE THEM, so that two names that clean to the same
    thing are still told apart."""
    return hashlib.sha256(json.dumps([kind, status], ensure_ascii=True).encode("utf-8")).hexdigest()[:16]


def file_label(path):
    """A file's name, made safe to put in the report: letters, digits, dot, dash and underscore."""
    return re.sub(r"[^A-Za-z0-9._-]", "?", os.path.basename(path))[:80]


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"))


def checksum(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def file_sum(path):
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except FileNotFoundError:
        return None


def same_file(a, b):
    try:
        if os.path.exists(a) and os.path.exists(b):
            return os.path.samefile(a, b)
    except OSError:
        pass
    return os.path.realpath(a).casefold() == os.path.realpath(b).casefold()


# ---------------------------------------------------------------- the connection: GET only


class Connection:
    """Every request goes through `get` and is written down, with the class of what came back. There is no other method."""

    def __init__(self, get, host):
        self._get, self.host = get, host
        self.sent = []          # (method as built, the path with numbers left in, what came back)

    def get(self, path, params=None):
        """(status or None, body). None means no answer came: the third thing returned says which kind."""
        try:
            answer = self._get(path, params)
        except TimeoutError:
            self.sent.append(("GET (no answer)", path, "timed out"))
            return None, {}, "timed out"
        except OSError as err:
            timed = "timed out" in str(getattr(err, "reason", err)).lower()
            self.sent.append(("GET (no answer)", path, "timed out" if timed else "network error"))
            return None, {}, "timed out" if timed else "network error"
        method = answer[3] + (" WITH A BODY" if answer[4] else "") if len(answer) == 5 else "GET (the made-up Jira)"
        self.sent.append((method, path, "status %d" % answer[0]))
        return answer[0], answer[2], None

    def only_gets(self):
        return all(method.split(" ")[0] == "GET" and "BODY" not in method for method, _, _ in self.sent)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def make_live(opener=None):
    base = os.environ.get("JIRA_BASE_URL", "").rstrip("/")
    email, token = os.environ.get("JIRA_EMAIL", ""), os.environ.get("JIRA_API_TOKEN", "")
    for name, value in (("JIRA_BASE_URL", base), ("JIRA_EMAIL", email), ("JIRA_API_TOKEN", token)):
        if not value:
            raise Refused("the environment variable %s is not set" % name)
    host = urllib.parse.urlparse(base).hostname or ""
    if not host or base.lower() != "https://" + host:
        raise Refused("JIRA_BASE_URL must be https:// and the site's name, with no port, path or sign-in in it")
    base = "https://" + host
    encoded = base64.b64encode(("%s:%s" % (email, token)).encode("utf-8")).decode("ascii")
    opener = opener or urllib.request.build_opener(NoRedirect)

    def get(path, params=None):
        if not (path == SEARCH_PATH or re.fullmatch(r"/rest/api/3/issue/[0-9]{1,20}", path)):
            raise Refused("this tool asks for one item by its number, and for the project's list, and nothing else")
        request = urllib.request.Request(base + path + ("?" + urllib.parse.urlencode(params) if params else ""), method="GET")       # GET, and only GET. No body
        request.add_header("Authorization", "Basic " + encoded)
        request.add_header("Accept", "application/json")
        try:
            with opener.open(request, timeout=30) as response:
                status, headers, raw = response.status, dict(response.headers), response.read()
        except urllib.error.HTTPError as err:
            status, headers, raw = err.code, dict(err.headers), b""          # the body of a refusal is not read at all
            err.close()
        except http.client.HTTPException as err:
            raise OSError(type(err).__name__)
        try:
            parsed = json.loads(raw.decode("utf-8")) if raw.strip() else {}
        except (ValueError, RecursionError):
            parsed = {}
        return status, headers, parsed, request.get_method(), request.data is not None

    return Connection(get, host), [token, email, encoded]


def site_fingerprint(host):
    return hashlib.sha256(host.lower().encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------- the local copy


def good_copy_item(i):
    return (isinstance(i, dict) and set(i) == {"id", "copied_at", "as_copied", "as_held"} and ident(i["id"]) and real_stamp(i["copied_at"])
            and isinstance(i["as_copied"], dict) and set(i["as_copied"]) - {"names_checksum"} == {"key", "issuetype", "status", "updated"}
            and ("names_checksum" not in i["as_copied"] or (isinstance(i["as_copied"]["names_checksum"], str) and re.fullmatch(r"[0-9a-f]{16}", i["as_copied"]["names_checksum"]) is not None))
            and isinstance(i["as_copied"]["key"], str) and REF.fullmatch(i["as_copied"]["key"]) is not None and i["as_copied"]["key"] == i["as_copied"]["key"].upper()
            and all(isinstance(i["as_copied"][k], str) and clean(i["as_copied"][k]) == i["as_copied"][k] for k in ("issuetype", "status")) and real_stamp(i["as_copied"]["updated"])
            and isinstance(i["as_held"], dict) and set(i["as_held"]) == {"issuetype", "status"}
            and all(isinstance(i["as_held"][k], str) and clean(i["as_held"][k]) == i["as_held"][k] for k in ("issuetype", "status")))


def load_copy(path):
    if not os.path.isfile(path) or os.path.getsize(path) > 50 * 1024 * 1024:
        raise Refused("--copy is not a plain file that is there")
    try:
        with open(path, encoding="utf-8") as f:
            copy = json.load(f)
    except (OSError, ValueError, UnicodeDecodeError):
        raise Refused("the local copy could not be read")
    return check_copy(copy)


def check_copy(copy):
    """Refuses a copy that is not in the form this tool reads. Used for a copy that is read, and for one about to be written."""
    good = (isinstance(copy, dict) and set(copy) == {"format", "project", "source", "site_fingerprint", "items"} and copy.get("format") == COPY_FORMAT
            and isinstance(copy.get("project"), str) and PROJECT.fullmatch(copy["project"]) is not None
            and ((copy.get("source") == "fake" and copy["site_fingerprint"] is None) or (copy.get("source") == "live" and isinstance(copy["site_fingerprint"], str) and re.fullmatch(r"[0-9a-f]{16}", copy["site_fingerprint"])))
            and isinstance(copy.get("items"), list) and len(copy["items"]) <= MAX_ITEMS and all(good_copy_item(i) for i in copy["items"]))
    if not good:
        raise Refused("the local copy is not in the form this tool reads (%s), or holds something it should not. It is not used" % COPY_FORMAT)
    numbers = [i["id"] for i in copy["items"]]
    keys = [i["as_copied"]["key"] for i in copy["items"]]
    if len(set(numbers)) != len(numbers) or len(set(keys)) != len(keys):
        raise Refused("the local copy holds one number or one key twice, so its items cannot be counted")
    if any(REF.fullmatch(k).group(1) != copy["project"].upper() for k in keys):
        raise Refused("the local copy holds an item of another project than the one it says it is of")
    return copy


# ---------------------------------------------------------------- asking Jira


def failure_class(status, problem):
    """The class of a failure, from a fixed list. Nothing Jira said is used."""
    if problem:
        return problem
    if status == 403:
        return "forbidden (403)"
    if status == 429:
        return "rate limited (429)"
    if isinstance(status, int) and 500 <= status <= 599:
        return "server error (5xx)"
    return "unexpected status"


def ask_item(conn, number, project):
    """What Jira has for one item now. Returns (kind, value): ("item", {...}), ("gone", None) or ("failed", class). The
    number of the line in the fetch log is the length of conn.sent after the call."""
    status, body, problem = conn.get("/rest/api/3/issue/%s" % number, {"fields": FIELDS})
    if status == 401:
        raise Refused("Jira rejected the credentials (401). Check JIRA_EMAIL and JIRA_API_TOKEN")
    if status == 404:
        return "gone", None
    if status != 200:
        return "failed", failure_class(status, problem)
    fields = body.get("fields") if isinstance(body, dict) else None
    key = body.get("key") if isinstance(body, dict) else None
    found = REF.fullmatch(key) if isinstance(key, str) else None
    kind = fields.get("issuetype", {}).get("name") if isinstance(fields, dict) and isinstance(fields.get("issuetype"), dict) else None
    state = fields.get("status", {}).get("name") if isinstance(fields, dict) and isinstance(fields.get("status"), dict) else None
    updated = in_utc(fields.get("updated")) if isinstance(fields, dict) else None
    if not found or body.get("id") != number or clean(kind) is None or clean(state) is None or updated is None:
        return "failed", "unreadable answer"
    if found.group(1).upper() != project:
        return "gone", "moved"
    return "item", {"key": key.upper(), "issuetype": clean(kind), "status": clean(state), "updated": updated, "names_checksum": names_checksum(kind, state)}


def list_project(conn, project):
    """The numbers and keys of every item Jira lists for the project: ({number: key}, None), or (None, class of failure)."""
    listed, marker, pages = {}, None, 0
    while True:
        params = {"jql": 'project = "%s" ORDER BY key ASC' % project, "fields": "issuetype", "maxResults": PAGE}
        if marker:
            params["nextPageToken"] = marker
        status, body, problem = conn.get(SEARCH_PATH, params)
        if status == 401:
            raise Refused("Jira rejected the credentials (401). Check JIRA_EMAIL and JIRA_API_TOKEN")
        if status != 200:
            return None, failure_class(status, problem)
        page = body.get("issues") if isinstance(body, dict) else None
        following = body.get("nextPageToken") if isinstance(body, dict) else None
        if not isinstance(page, list) or (following is not None and (not isinstance(following, str) or not following)) or (not page and following) or (following and following == marker):
            return None, "unreadable answer"
        for raw in page:
            key = raw.get("key") if isinstance(raw, dict) else None
            found = REF.fullmatch(key) if isinstance(key, str) else None
            if not found or not ident(raw.get("id")) or raw["id"] in listed or found.group(1).upper() != project:
                return None, "unreadable answer"
            listed[raw["id"]] = key.upper()
        pages += 1
        if not following:
            return (listed, None) if body.get("isLast", True) is True else (None, "unreadable answer")
        if pages >= MAX_PAGES or len(listed) > MAX_ITEMS:
            return None, "unreadable answer"
        marker = following


# ---------------------------------------------------------------- giving each item its one state


def classify(item, kind, value, as_of):
    """The one state of an item the local copy holds, with its reason, what else it fits, and what to do next.
    The states are tried in their order, and the first that fits is the item's state."""
    copied, held = item["as_copied"], item["as_held"]
    locally_changed = (held["issuetype"], held["status"]) != (copied["issuetype"], copied["status"])
    local_note = " and ".join(part for part in (
        "status `%s` to `%s`" % (copied["status"], held["status"]) if held["status"] != copied["status"] else "",
        "type `%s` to `%s`" % (copied["issuetype"], held["issuetype"]) if held["issuetype"] != copied["issuetype"] else "") if part)
    out = {"id": item["id"], "key": copied["key"], "error_class": None, "age_seconds": None, "over_limit": None, "also": [],
           "found": {"answer": kind, "jira_changed": None, "locally_changed": locally_changed}}
    if kind == "failed":                                                                        # 1
        out.update(state="failed to fetch", error_class=value, reason="Jira could not be read for this item: %s." % value,
                   next=NEXT_FOR_FAILURE.get(value, NEXT_FOR_FAILURE["unexpected status"]))
        if locally_changed:
            out["also"].append("changed locally (%s). Whether Jira changed too is not known" % local_note)
        return out
    if kind == "gone":                                                                          # 2
        if value == "moved":
            out.update(state="missing from Jira", reason="Jira has it under this number, in another project. It is no longer in this one.",
                       next="It was moved to another project. Decide whether the local copy should follow it or be let go. Do not delete the copy on the strength of this report.")
        else:
            out.update(state="missing from Jira", reason="Jira answers that it is not there.",
                       next="It was deleted, moved to another project, or hidden from this account. Find out which before removing the local copy. Do not delete the copy on the strength of this report.")
        if locally_changed:
            out["also"].append("changed locally (%s). That change has nowhere to go" % local_note)
        return out
    jira_changed = (value["key"], value["issuetype"], value["status"], value["updated"]) != (copied["key"], copied["issuetype"], copied["status"], copied["updated"])
    renamed = "names_checksum" in copied and copied["names_checksum"] != value["names_checksum"]
    jira_changed = jira_changed or renamed
    out["found"]["jira_changed"] = jira_changed
    what = []
    if value["key"] != copied["key"]:
        what.append("its key is now %s" % value["key"])
    if value["issuetype"] != copied["issuetype"]:
        what.append("its type is now `%s`" % value["issuetype"])
    if value["status"] != copied["status"]:
        what.append("its status is now `%s`, and was `%s` when copied" % (value["status"], copied["status"]))
    if renamed and not what:
        what.append("the name of its status or type is not what it was when copied, in a way the cleaned names here do not show")
    behind = seconds_between(value["updated"], as_of)
    over = behind > STALE_LIMIT_HOURS * 3600
    lag = "behind by %s; the limit is %d hours: %s" % (span(behind), STALE_LIMIT_HOURS, "OVER THE LIMIT" if over else "within the limit")
    changed_text = "Jira changed it at %s%s" % (value["updated"], (": " + "; ".join(what)) if what else ", in something this copy does not hold")
    if jira_changed and locally_changed:                                                        # 3
        out.update(state="conflicted", reason="%s. And the copy was changed locally (%s)." % (changed_text, local_note), age_seconds=behind, over_limit=over,
                   next="Both sides changed. Compare the two versions and decide which stands, with the conflict tool (jira-detect-conflicts). Do not sync over either.")
        out["also"].append("stale: %s" % lag)
        return out
    if locally_changed:                                                                         # 4
        out.update(state="changed locally only", reason="The copy was changed locally (%s). Jira has not changed since it was copied." % local_note,
                   next="Review the local change. Send it to Jira with a write tool that previews first, or discard it. A sync would overwrite it.")
        return out
    if jira_changed:                                                                            # 5
        out.update(state="stale", reason="%s. The copy has not been changed locally." % changed_text, age_seconds=behind, over_limit=over,
                   next="Sync it now, and find out why the last sync missed it." if over else "The next sync should pick it up. No action unless it is still here on the next report.")
        return out
    out.update(state="synchronized", reason="Jira has what the copy has.", next="None.")        # 7
    return out


def reconcile(copy, conn, as_of):
    """Every item considered, each with exactly one state. Returns (entries, why the list failed or None, the line of
    the fetch log where the list was last asked for, the numbers Jira's list gave or None)."""
    project = copy["project"].upper()
    entries = []
    for item in sorted(copy["items"], key=lambda i: int(i["id"])):
        kind, value = ask_item(conn, item["id"], project)
        entry = classify(item, kind, value, as_of)
        entry["log_line"] = len(conn.sent)
        entries.append(entry)
    listed, list_failure = list_project(conn, project)
    list_line = len(conn.sent)
    if listed is not None:
        held = set(i["id"] for i in copy["items"])
        for number in sorted(set(listed) - held, key=int):                                      # 6
            entries.append({"id": number, "key": listed[number], "state": "not yet copied", "error_class": None, "age_seconds": None, "over_limit": None, "also": [],
                            "found": {"answer": "listed only", "jira_changed": None, "locally_changed": None},
                            "reason": "Jira lists it for the project. The local copy does not hold it.", "log_line": list_line,
                            "next": "Copy it with the next sync. If it is not meant to be copied, say so in the sync's own rules, so that it is left out on purpose."})
    entries.sort(key=lambda e: int(e["id"]))
    return entries, list_failure, list_line, (None if listed is None else sorted(listed, key=int))


def own_check(entries, copy, listed):
    """The check that comes first. `listed` is the numbers Jira's list gave, straight from the list, or None if the list
    could not be read. Every number in the copy or the list must have exactly one state; nothing else may; the counts
    must add up; and each item's state must agree with what was found for it, by the rule as MUST_BE states it.
    Returns (counts, total, problems). The report is written only if there are no problems."""
    problems = []
    numbers = [e["id"] for e in entries]
    counts = {name: sum(1 for e in entries if e["state"] == name) for name in STATE_NAMES}
    for number in sorted(set(numbers), key=int):
        if numbers.count(number) != 1:
            problems.append("the item %s was given %d states" % (number, numbers.count(number)))
    for entry in entries:
        if entry["state"] not in STATE_NAMES:
            problems.append("the item %s was given a state that is not one of the states" % entry["id"])
    considered = set(i["id"] for i in copy["items"]) | set(listed or [])
    if set(numbers) != considered:
        problems.append("%d item(s) considered were given no state, or an item was given a state that was not considered" % len(considered ^ set(numbers)))
    held = set(i["id"] for i in copy["items"])
    for entry in entries:
        wanted, found = MUST_BE.get(entry["state"]), entry.get("found") or {}
        agrees = wanted is not None and found.get("answer") == wanted[0] and all(want is None or have is want for want, have in ((wanted[1], found.get("jira_changed")), (wanted[2], found.get("locally_changed"))))
        if not agrees or (entry["state"] == "not yet copied") != (entry["id"] not in held):
            problems.append("the item %s was given the state `%s`, which does not agree with what was found for it" % (entry["id"], shown(entry["state"], 30)))
    total = len(considered)
    if sum(counts.values()) != total:
        problems.append("the counts of the states add up to %d and %d items were considered" % (sum(counts.values()), total))
    return counts, total, problems


# ---------------------------------------------------------------- the three files


def fetch_log(project, conn, mark):
    out = [LOG_HEADING + project, "", "Run mark: `%s`. The report made by the same run carries the same mark." % mark, "",
           "Every request this run made, in order. The report cites these lines by their numbers.",
           "A line gives what was asked for and the class of what came back. Nothing Jira said in a refusal is here.", ""]
    for number, (method, path, came) in enumerate(conn.sent, 1):
        out.append("- **L%03d** %s `%s` — %s" % (number, method.split(" ")[0], path, came))
    return "\n".join(out) + "\n"


def render(copy, entries, counts, total, list_failure, as_of, source, site, trend, files, listed_count, mark, list_line):
    project = copy["project"].upper()
    local, extra = len(copy["items"]), counts["not yet copied"]
    by_cleaned = sum(1 for i in copy["items"] if "names_checksum" not in i["as_copied"])
    out = [REPORT_HEADING + project, "",
           "**Written by a tool. Do not edit this file.** As of %s. Source: %s." % (as_of, "the made-up Jira; every item here is made up" if source == "fake" else "a real Jira, site fingerprint %s" % site),
           "Local copy: `%s` (%d items). No title and no person is in this report. Run mark: `%s`; the fetch log beside this report carries the same." % (files["copy"], local, mark), "",
           "## 1. The check that comes first", ""]
    if list_failure:
        out += ["**INCOMPLETE.** Jira's list of the project could not be read (%s; line L%03d of `%s`). So items that Jira has and the local copy does not hold" % (list_failure, list_line, files["log"]),
                "**could not be counted**. The total below is of the items the local copy holds only, and \"not yet copied\" is NOT KNOWN. Run the report again.", ""]
    out += ["- Items considered: **%d**. That is %d the local copy holds%s." % (total, local, "" if list_failure else ", and %d more that Jira lists and the copy does not hold" % extra),
            "- Jira's list of the project: %s." % ("could not be read" if list_failure else "**%d items**, line L%03d of `%s`" % (listed_count, list_line, files["log"])),
            "- Items given a state: **%d**. Each has exactly one." % sum(counts.values()),
            "- The counts of the states: %s = **%d**." % (" + ".join(str(counts[name]) for name in STATE_NAMES), sum(counts.values())),
            "- **CHECK: %d = %d. PASSED.** Every number in the copy%s was given one state and no other, and each state agrees with what was found for the item." % (
                sum(counts.values()), total, "" if list_failure else " and in Jira's list"),
            "  This check is made before the report is written. If it failed there would be no report. It checks the tool against itself, not Jira's answers.", "",
            "## 2. The count of each state", "",
            "An item is given the first state in this order that fits it, and no other.", "",
            "| | State | Items | What it means |", "|---|---|---|---|"]
    for place, (name, meaning, _) in enumerate(STATES, 1):
        shown_count = "NOT KNOWN" if list_failure and name == "not yet copied" else "%d" % counts[name]
        out.append("| %d | %s | **%s** | %s |" % (place, name, shown_count, meaning))
    out += ["| | **All** | **%d**%s | |" % (total, " (the local copy only)" if list_failure else ""), "",
            "**Seven states, where the quest this was built for names five.** `changed locally only` and `not yet copied` were added. Without the first, a copy edited locally",
            "while Jira stood still would be in no state. Without the second, an item Jira has and the copy lacks would not be counted at all.", ""]
    also = [e for e in entries if e["also"]]
    out += ["%d item%s also fit%s a later state than the one given. Each says so on its line below." % (len(also), "" if len(also) == 1 else "s", "s" if len(also) == 1 else ""), "",
            "## 3. Every item that is not simply in sync", ""]
    exceptions = [e for e in entries if e["state"] != "synchronized"]
    if not exceptions:
        out += ["None." if total else "None: no items were considered.", ""]
    for name, _, is_exception in STATES:
        group = [e for e in entries if e["state"] == name]
        if not is_exception or not group:
            continue
        out += ["### %s: %d" % (name[0].upper() + name[1:], len(group)), ""]
        for e in group:
            out.append("- **%s** [%s]" % (e["key"], e["id"]))
            out.append("  - Reason: %s" % e["reason"])
            if e["error_class"]:
                out.append("  - Error class: **%s**. What Jira said in refusing is not repeated here." % e["error_class"])
            else:
                out.append("  - Error class: none. Jira answered; this is not a failure to fetch.")
            if name == "stale":
                out.append("  - Age: **%s**. Limit: **%d hours**. %s." % (span(e["age_seconds"]), STALE_LIMIT_HOURS, "**Over the limit**" if e["over_limit"] else "Within the limit"))
            for other in e["also"]:
                out.append("  - Also: %s." % other)
            out.append("  - Next: %s" % e["next"])
            out.append("  - Log: line L%03d of `%s`." % (e["log_line"], files["log"]))
        out.append("")
    in_sync = [e for e in entries if e["state"] == "synchronized"]
    out += ["## 4. Synchronized: %d" % len(in_sync), "",
            ("Jira was asked about each of these, one request each, and has what the copy has: " + ", ".join("%s [%s]" % (e["key"], e["id"]) for e in in_sync) + ".") if in_sync else "None.", "",
            "## 5. The trend: the last %d run%s" % (len(trend), "" if len(trend) == 1 else "s"), "",
            "One line for each distinct input, in order of the time each is as of. Running the report again on the same input adds nothing.", "",
            "| As of | " + " | ".join(name for name in STATE_NAMES) + " | All | Complete |", "|---|" + "---|" * (len(STATE_NAMES) + 2)]
    for run in trend:
        cells = ["not known" if run.get("incomplete") and name == "not yet copied" else str(run["counts"][name]) for name in STATE_NAMES]
        out.append("| %s | %s | %d | %s |" % (run["as_of"], " | ".join(cells), run["total"], "**NO**: Jira's list could not be read" if run.get("incomplete") else "yes"))
    out += ["", "## 6. What this report cannot tell", "",
            "- **Deleted, moved or hidden** look the same from here when Jira answers that an item is not there.",
            "- **\"Changed locally\"** is judged from the type and status the copy holds against those it held when copied. A change to anything else is not seen.",
            "- **\"Jira changed it\"** is judged from the key, the type, the status and the last-changed time. Jira may have changed something this copy does not hold.",
            "- **Names.** %s" % ("Each item of this copy carries a checksum of its type and status names as Jira wrote them, and that is what was compared." if not by_cleaned else
                               "**%d of the %d items of this copy carry no checksum of their names as Jira wrote them,** so those were compared by cleaned names: cut to 40 characters, "
                               "marks replaced by a question mark. For them, a name changed only in its marks, or beyond its 40th character, with no change to the item's last-changed time, would not be seen." % (by_cleaned, local)),
            "- **An item hidden from this account and not in the local copy** is in no list, and is not counted.",
            "- **Two items can show the same key,** if an item was removed and its key is now another item's. They are told apart by their numbers.",
            "- **Nothing changed here.** The report reads Jira and reads the copy. It syncs nothing and settles nothing.", ""]
    return "\n".join(out)


def write_file(path, text):
    handle, temporary = tempfile.mkstemp(prefix=".reconcile-", suffix=".tmp", dir=os.path.dirname(path))
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        os.chmod(temporary, 0o644)
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def places(out_dir, name, copy_path):
    """The three paths, checked: each is absent or is a file this tool wrote, and none is the local copy."""
    if not NAME.fullmatch(name):
        raise Refused("--name is lower-case letters, digits and dashes, starting with a letter")
    folder = os.path.realpath(out_dir)
    if not os.path.isdir(folder):
        raise Refused("--out-dir is not a folder that exists")
    paths = {"report": os.path.join(folder, name + ".md"), "log": os.path.join(folder, name + ".log.md"), "history": os.path.join(folder, name + ".history.json")}
    starts = {"report": REPORT_HEADING, "log": LOG_HEADING, "history": '{\n "format": "%s"' % HISTORY_FORMAT}
    for which, path in paths.items():
        if same_file(path, copy_path):
            raise Refused("one of the report's files would be the local copy itself. Use another --name or --out-dir")
        if os.path.islink(path) or os.path.isdir(path) or (os.path.exists(path) and os.stat(path).st_nlink > 1):
            raise Refused("%s in the folder is a link, a folder, or a file with a second name. This tool writes only a plain file of its own" % os.path.basename(path))
        if os.path.exists(path):
            with open(path, "rb") as f:
                if f.read(len(starts[which].encode("utf-8"))) != starts[which].encode("utf-8"):
                    raise Refused("a file named %s is already in the folder and it is not one this tool wrote. It is left as it is. Use another --name" % shown(os.path.basename(path)))
    return paths


def load_history(path):
    try:
        with open(path, encoding="utf-8") as f:
            history = json.load(f)
    except FileNotFoundError:
        return {"format": HISTORY_FORMAT, "runs": []}
    except (OSError, ValueError, UnicodeDecodeError):
        raise Refused("the history beside the report could not be read. It is left as it is. Use another --name, or move it away")
    good = (isinstance(history, dict) and history.get("format") == HISTORY_FORMAT and isinstance(history.get("runs"), list)
            and all(isinstance(r, dict) and set(r) >= {"input", "as_of", "counts", "total"} and real_stamp(r["as_of"]) and isinstance(r["input"], str) and re.fullmatch(r"[0-9a-f]{16}", r["input"])
                    and isinstance(r["counts"], dict) and set(r["counts"]) == set(STATE_NAMES) and all(type(v) is int and v >= 0 for v in r["counts"].values())
                    and type(r["total"]) is int for r in history["runs"]))
    if not good:
        raise Refused("the history beside the report is not one this tool wrote. It is left as it is. Use another --name, or move it away")
    return history


# ---------------------------------------------------------------- the commands


def cmd_states():
    say("The states, in the order they are tried. An item is given the first that fits, and no other.")
    say("")
    for place, (name, meaning, is_exception) in enumerate(STATES, 1):
        say("  %d. %-22s %s%s" % (place, name, meaning, "" if is_exception else "  (not an exception)"))
    say("")
    say("A stale item gives its age, which is how long the copy has been behind Jira, and the limit, which is %d hours." % STALE_LIMIT_HOURS)
    say("A failed item gives one of these classes, and nothing Jira said: %s." % "; ".join(sorted(NEXT_FOR_FAILURE)))
    return 0


def cmd_adopt(args):
    if not os.path.isfile(args.source_file) or os.path.getsize(args.source_file) > 50 * 1024 * 1024:
        raise Refused("--from is not a plain file that is there")
    try:
        with open(args.source_file, encoding="utf-8") as f:
            result = json.load(f)
    except (OSError, ValueError, UnicodeDecodeError):
        raise Refused("the result file could not be read")
    if not (isinstance(result, dict) and result.get("format") == "jira-query-stories/1" and result.get("complete") is True and isinstance(result.get("items"), list)
            and real_stamp(result.get("taken_at")) and isinstance(result.get("project"), str) and PROJECT.fullmatch(result["project"]) and result.get("source") in ("fake", "live")):
        raise Refused("--from is not a complete result written by the saved-query tool (jira-query-stories)")
    items, recleaned = [], 0
    for raw in result["items"]:
        if not (isinstance(raw, dict) and ident(raw.get("id")) and isinstance(raw.get("key"), str) and REF.fullmatch(raw["key"]) and clean(raw.get("issuetype")) and clean(raw.get("status"))
                and real_stamp(raw.get("updated"))):
            raise Refused("the result file holds an item this tool cannot take. Nothing was written")
        kind, status = clean(raw["issuetype"]), clean(raw["status"])
        recleaned += (kind, status) != (raw["issuetype"], raw["status"])
        items.append({"id": raw["id"], "copied_at": result["taken_at"], "as_copied": {"key": raw["key"].upper(), "issuetype": kind, "status": status, "updated": raw["updated"]},
                      "as_held": {"issuetype": kind, "status": status}})
    copy = {"format": COPY_FORMAT, "project": result["project"].upper(), "source": result["source"], "site_fingerprint": result.get("site_fingerprint"), "items": items}
    try:
        check_copy(copy)                    # what is written must be something `report` will read
    except Refused as no:
        raise Refused("the result cannot be made into a local copy this tool reads: %s. Nothing was written" % no)
    out = os.path.abspath(args.out)
    if os.path.lexists(out):
        raise Refused("something is already at the place given with --out. It is not written over")
    if not os.path.isdir(os.path.dirname(out)):
        raise Refused("the folder for --out is not there")
    write_file(out, json.dumps(copy, indent=1, sort_keys=True) + "\n")
    say("Adopted %d items of project %s from a result taken at %s, as a local copy this tool can read: %s." % (len(items), copy["project"], result["taken_at"], file_label(out)))
    say("Each is marked as copied at that time, and as NOT changed locally: the result says nothing about local changes.")
    say("The result holds cleaned names only, so these items carry no checksum of their names as Jira wrote them, and are compared by cleaned names.%s" % (
        " %d item(s) had a name cleaned further here." % recleaned if recleaned else ""))
    say("Nothing was contacted.")
    return 0


def cmd_report(args, conn, live, as_of, secrets=()):
    copy = load_copy(args.copy)
    source, site = ("live", site_fingerprint(conn.host)) if live else ("fake", None)
    if (copy["source"], copy["site_fingerprint"]) != (source, site):
        raise Refused("the local copy was made from another Jira than the one being asked (a made-up one against a real one, or another site). They are not compared")
    if any(i["copied_at"] > as_of for i in copy["items"]):
        raise Refused("the report is asked as of a time before the copy was taken. A copy cannot be judged as of a time it did not exist")
    paths = places(args.out_dir, args.name, args.copy)
    history = load_history(paths["history"])
    before = {which: file_sum(path) for which, path in paths.items()}

    entries, list_failure, list_line, listed = reconcile(copy, conn, as_of)
    counts, total, problems = own_check(entries, copy, listed)
    not_in_sync = sum(1 for e in entries if e["state"] != "synchronized")

    project = copy["project"].upper()
    say("Project: %s" % project)
    say("Compared: the local copy given with --copy (%d items) with %s." % (len(copy["items"]), "a real Jira, site fingerprint %s" % site if live else "the made-up Jira. No real Jira was contacted"))
    say("As of: %s. A stale item's limit: %d hours." % (as_of, STALE_LIMIT_HOURS))
    say("")
    say("THE CHECK THAT COMES FIRST")
    say("  Jira's list of the project: %s." % ("COULD NOT BE READ (%s)" % list_failure if list_failure else "%d items" % len(listed)))
    say("  Items considered: %d (%d in the local copy%s)." % (total, len(copy["items"]), "" if list_failure else ", %d more in Jira only" % counts["not yet copied"]))
    say("  The counts of the states: %s = %d." % (" + ".join(str(counts[name]) for name in STATE_NAMES), sum(counts.values())))
    if problems:
        say("  CHECK FAILED:")
        for problem in problems:
            say("    %s." % problem)
        say("")
        say("RESULT: NO REPORT. Its own check failed, so nothing was written. This is a fault in the tool, not in the data.")
        return 3
    say("  CHECK: %d = %d. PASSED. Every number in the copy%s has one state and no other, and each state agrees with what was found." % (sum(counts.values()), total, "" if list_failure else " and in Jira's list"))
    if list_failure:
        say("  INCOMPLETE: Jira's list of the project could not be read (%s). Items Jira has and the copy lacks are NOT counted." % list_failure)
    say("")
    say("THE COUNT OF EACH STATE")
    for place, (name, _, _) in enumerate(STATES, 1):
        say("  %d. %-22s %s" % (place, name, "NOT KNOWN" if list_failure and name == "not yet copied" else counts[name]))
    say("     %-22s %d%s" % ("ALL", total, "   (the local copy only)" if list_failure else ""))
    say("")
    say("EVERY ITEM THAT IS NOT SIMPLY IN SYNC: %d" % not_in_sync)
    for e in entries:
        if e["state"] == "synchronized":
            continue
        extra_text = (" Error class: %s." % e["error_class"] if e["error_class"] else "") + \
            (" Age %s, limit %d hours, %s." % (span(e["age_seconds"]), STALE_LIMIT_HOURS, "OVER" if e["over_limit"] else "within") if e["state"] == "stale" else "")
        say("  %-9s [%s]  %s.%s%s  (log L%03d)" % (e["key"], e["id"], e["state"].upper(), extra_text, " ALSO: " + "; ".join(e["also"]) + "." if e["also"] else "", e["log_line"]))
    if not_in_sync:
        say("  The reason and the next action for each are in the report.")

    kept = [dict(e, found=None) for e in entries]
    in_order = dict(copy, items=sorted(copy["items"], key=lambda i: int(i["id"])))       # the order of the items in the file is not part of the input
    snapshot = canonical({"copy": in_order, "as_of": as_of, "entries": kept, "list_failure": list_failure, "listed": listed})
    mark = checksum(snapshot)
    this_run = {"input": mark, "as_of": as_of, "counts": counts, "total": total, "incomplete": bool(list_failure)}
    added = not any(run["input"] == mark for run in history["runs"])
    if added:
        history["runs"].append(this_run)
    history["runs"] = sorted(history["runs"], key=lambda run: (run["as_of"], run["input"]))[-HISTORY_KEEPS:]
    history_text = json.dumps(history, indent=1, sort_keys=True) + "\n"
    files = {"copy": file_label(args.copy), "log": os.path.basename(paths["log"])}
    texts = {"report": render(copy, entries, counts, total, list_failure, as_of, source, site, history["runs"][-5:], files, None if listed is None else len(listed), mark, list_line),
             "log": fetch_log(project, conn, mark), "history": history_text}
    if any(secret and secret in "\n".join(LINES) + "".join(texts.values()) for secret in secrets):
        raise Refused("a credential was found in what would be shown or saved")
    wrote = []
    try:
        for which in ("history", "log", "report"):
            if before[which] != hashlib.sha256(texts[which].encode("utf-8")).hexdigest():
                write_file(paths[which], texts[which])
                wrote.append(os.path.basename(paths[which]))
    except OSError:
        raise Refused("a file could not be written. %s. Run the report again: until then the files in the folder may not belong to one run, and their run marks will differ" % (
            "Nothing was written" if not wrote else "Written before it failed: %s" % ", ".join(wrote)))
    say("")
    say("FILES, in the folder given with --out-dir. Run mark: %s." % mark)
    for which, label in (("report", "the report"), ("log", "the fetch log"), ("history", "the history")):
        say("  %-13s %-28s before %s   after %s   %s" % (label, shown(os.path.basename(paths[which])), (before[which] or "not there")[:16], file_sum(paths[which])[:16],
                                                         "WRITTEN" if os.path.basename(paths[which]) in wrote else "not written: byte for byte the same"))
    say("  Runs in the history: %d. This input %s." % (len(history["runs"]), "was added" if added else "was already there"))
    say("")
    say("RESULT: %s %d items considered, %d not simply in sync." % ("REPORT WRITTEN, AND INCOMPLETE." if list_failure else "REPORT WRITTEN." if wrote else "REPORT UNCHANGED: the same input gave the same report.",
                                                              total, not_in_sync))
    say("")
    if conn.only_gets():
        say("Requests sent to Jira: %d. Every one was a GET with no body, which reads and cannot change anything." % len(conn.sent))
    else:
        say("Requests sent to Jira: %d. NOT EVERY ONE COULD BE READ BACK AS A PLAIN GET." % len(conn.sent))
    shapes = {}
    for method, path, _ in conn.sent:
        shape = method.split(" (")[0] + " " + re.sub(r"/issue/[0-9]+", "/issue/{number}", path)
        shapes[shape] = shapes.get(shape, 0) + 1
    for shape in sorted(shapes):
        say("  %s  x%d" % (shape, shapes[shape]))
    return 2 if list_failure else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Account for every item of a local copy against Jira. Reads only.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("states")
    sub = commands.add_parser("adopt")
    sub.add_argument("--from", dest="source_file", required=True)
    sub.add_argument("--out", required=True)
    sub = commands.add_parser("report")
    sub.add_argument("--source", choices=("live", "fake"), required=True)
    sub.add_argument("--copy", required=True)
    sub.add_argument("--out-dir", required=True)
    sub.add_argument("--name", required=True, help="the files are NAME.md, NAME.log.md and NAME.history.json")
    sub.add_argument("--as-of", metavar="TIME", help="the time the report is as of, as 2026-11-20T12:00:00Z")
    sub.add_argument("--log", help="also save the output here, with the site's address removed")
    args = parser.parse_args(argv)
    del LINES[:]
    secrets, conn, code, log_to = [], None, 0, getattr(args, "log", None)
    try:
        if args.command == "states":
            code = cmd_states()
        elif args.command == "adopt":
            code = cmd_adopt(args)
        else:
            if log_to:
                own = [os.path.join(args.out_dir, args.name + ending) for ending in (".md", ".log.md", ".history.json")] + [args.copy]
                already = b""
                if os.path.isfile(log_to) and not os.path.islink(log_to):
                    with open(log_to, "rb") as f:
                        already = f.read(120)
                if (os.path.islink(log_to) or (os.path.isfile(log_to) and os.stat(log_to).st_nlink > 1) or any(same_file(log_to, path) for path in own)
                        or (os.path.lexists(log_to) and not any(start.match(already) for start in LOG_STARTS)) or not os.path.isdir(os.path.dirname(os.path.abspath(log_to)))):
                    log_to = None           # and the refusal below is NOT saved there: that would be the very write refused
                    raise Refused("--log names one of this tool's own files, the local copy, a link, a place in a folder that is not there, "
                                  "or something already there that does not begin as an output of this tool begins")
            if args.as_of is not None and not real_stamp(args.as_of):
                raise Refused("--as-of is a time such as 2026-11-20T12:00:00Z")
            if args.source == "fake":
                if args.as_of is None:
                    raise Refused("--source fake needs --as-of, so that the report is the same every time")
                import fake_jira
                conn = Connection(fake_jira.FakeJira().get, urllib.parse.urlparse(fake_jira.SITE).hostname)
                code = cmd_report(args, conn, False, args.as_of)
            else:
                conn, secrets = make_live()
                code = cmd_report(args, conn, True, args.as_of or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), secrets)
    except Refused as refusal:
        del LINES[:]
        say("REFUSED: %s." % refusal)
        say("Nothing was changed in Jira: this tool can only read.")
        code = 1
    except Exception as surprise:           # anything unforeseen
        del LINES[:]
        say("REFUSED: the tool stopped on something it did not foresee (%s)." % type(surprise).__name__)
        say("Nothing was changed in Jira: this tool can only read.")
        code = 1
    text = "\n".join(LINES)
    if any(secret and secret in text for secret in secrets):
        print("STOPPED: a credential was found in the output, so the output was not shown or saved.")
        return 1
    print(text)
    kept = text
    if secrets:
        note = "\nThe output above was searched for the API token, the account's email address and their encoded\nform: none found."
        print(note)
        kept += "\n" + note
    if log_to:
        host = conn.host if conn else ""
        kept = kept.replace("https://" + host, SITE_MARK).replace(host, SITE_MARK) if host else kept
        try:
            with open(log_to, "w", encoding="utf-8") as f:
                f.write(kept + "\n")
        except OSError:
            print("\nTHE OUTPUT ABOVE COULD NOT BE SAVED where --log said. What it says stands.")
    return code


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    sys.exit(main())
