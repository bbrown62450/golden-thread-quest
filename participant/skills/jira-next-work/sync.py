#!/usr/bin/env python3
"""Copies the items of one Jira project into a local records file, for `rank.py` to rank. IT ONLY READS JIRA.

    sync.py copy --source live|fake --project KEY --out RECORDS.json                 copy every item of the project
    sync.py copy --source live|fake --project KEY --out RECORDS.json --refresh KEY [KEY ...]
                                                                                     copy only these again, and keep the rest

THERE IS NO WAY TO WRITE TO JIRA IN THIS FILE. Every request is made by one function, and that function sends GET
and nothing else. There is no code path that builds a POST, PUT or DELETE. What the output says about the requests
is read back from each request as it was built: its method, and whether it carried a body.

What is copied for each item, and nothing else:

    key, id            Jira's own identifiers
    issuetype          the type's name
    status             its name, and the category Jira puts it in: "new", "indeterminate" or "done"
    priority           its name, or nothing if Jira has none for the item
    assignee           NOT the person. One of three words: "me", "someone else", "nobody". "me" is the account the
                       API token belongs to. The account id is compared and then dropped
    duedate            as Jira sent it: a date
    created, updated   Jira's times, rewritten in UTC, so that the site's own time zone is not kept
    links              for each link: the link type's name, the phrase as this item shows it ("is blocked by",
                       "blocks", "relates to"), whether this item is the link's source or its target, the other
                       item's key and id, and the other item's status as Jira showed it inside this item
    copied_at          when THIS copy of THIS item was taken, by this computer's clock, in UTC

NOT COPIED: titles, descriptions, comments, people's names, email addresses, account ids. Jira is not asked for an
item's own title. Its answers still carry two things that are dropped as they are read: the person who has each
item, of whom only the one word above is kept, and the titles of LINKED items, which Jira puts inside every link.

NAMES CHOSEN BY THE SITE'S ADMINISTRATORS (of statuses, priorities, issue types, link types) are other people's text
and end up in a Markdown file. Each is cut to 40 characters, and every character that is not a letter, a digit, a
space or one of . _ / ( ) ' - is replaced by a question mark.

The site's link types are copied too, so that the ranking can say which one it takes to mean "blocks".

The site's priorities are copied too, in the order Jira lists them, because that order is what "higher priority"
means on that site.

A SNAPSHOT is taken before and after the copy: every item's key and last-updated time, read again and reduced to one
short code. The two are compared. If they differ, someone changed an item while it was being copied; the copy is
still saved, and the output says so. The copy itself cannot be the cause: it sends only reads.

--refresh copies the named items again, one request each, and leaves the others as they were, with their older
`copied_at`. An item Jira no longer returns is taken out of the records, and the output says so. So is an item
Jira now returns under another key or in another project. The output then lists what it can see has drifted: items
whose last-updated time in Jira is no longer the one in their kept copy, items in Jira with no record, and records
with no item in Jira.

WHAT A SNAPSHOT CAN AND CANNOT SHOW. It is two listings of the project, by search. Jira's search can be behind what
Jira holds, so two equal snapshots show that the two listings agree, not that nothing changed. They do not cover an
item in another project that one of these is linked to.

--pretend-now TIME is for tests, and is refused against a real Jira: it sets the clock `copied_at` is taken from.
--log FILE saves the output with the site's address replaced by a marker.

For a live run the connection comes from the environment variables JIRA_BASE_URL, JIRA_EMAIL and JIRA_API_TOKEN. None
is stored. The output is searched for the token, the email address and their encoded form before it is shown.

Exit codes: 0 the records were written; 1 refused and nothing written, or a credential was found in the output, in
which case the output is withheld and the records file, which holds no credential field, has been written.
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

FORMAT = "jira-next-work/1"
REF = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,30}-[0-9]{1,9}")
PROJECT = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,30}")
SITE_MARK = "[site address removed]"
FIELDS = "status,priority,assignee,duedate,created,updated,issuelinks,issuetype"       # no summary: titles are not asked for
SEARCH_PATH = "/rest/api/3/search/jql"
PAGE = 100
MAX_ITEMS = 2000
UNSEEN = re.compile("[\\x00-\\x1f\\x7f-\\xa0\\u00ad\\u034f\\u061c\\u115f\\u1160\\u200b-\\u200f\\u2028\\u2029\\u202a-\\u202e\\u2060-\\u2069\\u2800\\u3164\\ufeff\\U000e0000-\\U000e007f]")
CATEGORIES = ("new", "indeterminate", "done", "undefined")       # "undefined" is Jira's own word for a status with no category
SAFE = re.compile(r"[^A-Za-z0-9 ._/()'-]")

LINES = []


class Refused(Exception):
    """Nothing was written. The message is the reason."""


def say(text=""):
    LINES.append(text)


def ident(value):
    return isinstance(value, str) and value.isascii() and value.isdigit() and len(value) <= 20


def word(value, limit=40):
    """A name the site's administrators chose (a status, a priority, a type, a link phrase): cut short, unseen characters out."""
    return SAFE.sub("?", UNSEEN.sub("?", value))[:limit].strip() or None if isinstance(value, str) and value.strip() else None


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0, tzinfo=None)


def stamp(moment):
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------- the connection: reads only


class Connection:
    """Every request goes through `get` and is written down. There is no other method."""

    def __init__(self, get, host):
        self._get, self.host = get, host
        self.sent = []

    def get(self, path, params=None):
        try:
            answer = self._get(path, params)
        except (OSError, TimeoutError) as err:
            self.sent.append(("?", path, None))
            raise Refused("could not reach Jira (%s)" % type(getattr(err, "reason", err)).__name__)
        # A live answer carries, as its 4th and 5th parts, the method of the request as it was built and whether it had a body.
        method, body = (answer[3], answer[4]) if len(answer) == 5 else ("GET (the fake Jira has no other)", False)
        self.sent.append((method, path, body))
        return answer[0], answer[1], answer[2]

    def only_read(self):
        return all(method.startswith("GET") and body is False for method, _, body in self.sent)


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
    if not host or base != "https://" + host:
        raise Refused("JIRA_BASE_URL must be https:// and the site's name, with no port, path or sign-in in it")
    encoded = base64.b64encode(("%s:%s" % (email, token)).encode("utf-8")).decode("ascii")
    opener = opener or urllib.request.build_opener(NoRedirect)

    def get(path, params=None):
        url = base + path + ("?" + urllib.parse.urlencode(params) if params else "")
        request = urllib.request.Request(url, method="GET")          # GET, and only GET. No body is ever attached
        request.add_header("Authorization", "Basic " + encoded)
        request.add_header("Accept", "application/json")
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
        return status, headers, parsed, request.get_method(), request.data is not None

    return Connection(get, host), [token, email, encoded]


def site_fingerprint(host):
    return hashlib.sha256(host.lower().encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------- reading Jira


def read_me(conn):
    status, _, body = conn.get("/rest/api/3/myself")
    if status == 401:
        raise Refused("Jira rejected the credentials (401). Check JIRA_EMAIL and JIRA_API_TOKEN")
    account = body.get("accountId") if status == 200 and isinstance(body, dict) else None
    if not isinstance(account, str) or not account:
        raise Refused("Jira did not say which account the API token belongs to (status %d), so \"me\" cannot be told from \"someone else\"" % status)
    return account


def read_priorities(conn):
    """The site's priorities, by name, in the order Jira lists them: highest first."""
    status, _, body = conn.get("/rest/api/3/priority")
    names = [word(entry.get("name")) for entry in body if isinstance(entry, dict)] if status == 200 and isinstance(body, list) else None
    if not names or None in names or len(set(names)) != len(names):
        raise Refused("Jira did not list its priorities (status %d), so the order of priorities is not known" % status)
    return names


def read_project(conn, key):
    status, _, body = conn.get("/rest/api/3/project/%s" % key)
    if status == 404:
        raise Refused("Jira answered 404 for the project. It does not exist, or this identity is not permitted to see it")
    if not (status == 200 and isinstance(body, dict) and ident(body.get("id")) and isinstance(body.get("key"), str) and PROJECT.fullmatch(body["key"])):
        raise Refused("Jira's answer for the project could not be used (status %d)" % status)
    return {"id": body["id"], "key": body["key"]}


def search_all(conn, jql, fields):
    """Every issue a search returns, page by page. Refuses unless every page is readable and the last says it is the last."""
    issues, token = [], None
    while True:
        params = {"jql": jql, "fields": fields, "maxResults": PAGE}
        if token:
            params["nextPageToken"] = token
        status, _, body = conn.get(SEARCH_PATH, params)
        page = body.get("issues") if status == 200 and isinstance(body, dict) else None
        if isinstance(page, list) and not page and body.get("nextPageToken"):
            raise Refused("Jira answered a search with an empty page and said there was more, so the copy would not be whole")
        if not isinstance(page, list) or any(not isinstance(i, dict) or not ident(i.get("id")) or not isinstance(i.get("fields"), dict) for i in page):
            raise Refused("Jira's answer to a search could not be used (status %d), so the copy would not be whole" % status)
        issues += page
        token = body.get("nextPageToken")
        if not token:
            if body.get("isLast") is False:
                raise Refused("Jira's answer to a search said there was more and gave no way to ask for it, so the copy would not be whole")
            return issues
        if not isinstance(token, str) or len(issues) > MAX_ITEMS:
            raise Refused("the search returned more than %d items, or a page marker that could not be used. Nothing is copied" % MAX_ITEMS)


def snapshot(conn, project_id):
    """One short code for every item's key and last-updated time, and the listing itself: {key: updated, in UTC}."""
    seen = sorted((str(i.get("key")), str(i["fields"].get("updated"))) for i in search_all(conn, "project = %s ORDER BY key ASC" % project_id, "updated"))
    return hashlib.sha256(json.dumps(seen).encode("utf-8")).hexdigest()[:16], {key: in_utc(updated) for key, updated in seen}


def in_utc(value):
    """One of Jira's times, rewritten in UTC to the second, or None if it cannot be read."""
    for shape in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.datetime.strptime(value, shape).astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except (TypeError, ValueError):
            pass
    return None


def read_link_types(conn):
    """The site's link types: [{"name", "inward", "outward"}], by name."""
    status, _, body = conn.get("/rest/api/3/issueLinkType")
    listed = body.get("issueLinkTypes") if status == 200 and isinstance(body, dict) else None
    if not isinstance(listed, list):
        raise Refused("Jira did not list its link types (status %d), so it is not known which link means \"blocks\"" % status)
    kinds = [{"name": word(k.get("name")), "inward": word(k.get("inward")), "outward": word(k.get("outward"))} for k in listed if isinstance(k, dict)]
    if any(None in k.values() for k in kinds):
        raise Refused("Jira's list of link types could not be read")
    return sorted(kinds, key=lambda k: k["name"])


def read_one(conn, key):
    """One item by its key, as Jira returns it now. None if Jira answers 404."""
    status, _, issue = conn.get("/rest/api/3/issue/%s" % key, {"fields": FIELDS})
    if status == 404:
        return None
    if not (status == 200 and isinstance(issue, dict) and ident(issue.get("id")) and isinstance(issue.get("fields"), dict)):
        raise Refused("Jira's answer for %s could not be used (status %d)" % (key, status))
    return issue


def status_of(node):
    category = (node.get("statusCategory") or {}).get("key") if isinstance(node, dict) else None
    if category not in CATEGORIES or not word(node.get("name")):
        return None
    return {"name": word(node["name"]), "category": category}


def record_of(issue, me, copied_at):
    """One item as it is kept. Returns (record, what could not be read)."""
    fields, gaps = issue["fields"], []
    key = issue.get("key")
    if not isinstance(key, str) or not REF.fullmatch(key):
        raise Refused("Jira returned an item whose key could not be used")
    status = status_of(fields.get("status"))
    if status is None:
        raise Refused("Jira did not give a usable status for %s, so it is not known whether it is open" % key)
    priority = fields.get("priority")
    assignee = fields.get("assignee")
    if assignee is None:
        who = "nobody"
    elif isinstance(assignee, dict) and isinstance(assignee.get("accountId"), str):
        who = "me" if assignee["accountId"] == me else "someone else"
    else:
        raise Refused("Jira's answer about who has %s could not be read" % key)
    listed = fields.get("issuelinks")
    if not isinstance(listed, list):
        raise Refused("Jira did not list the links of %s, so it is not known whether it is blocked" % key)
    links = []
    for entry in listed:
        kind = entry.get("type") if isinstance(entry, dict) else None
        out, inn = (entry.get("outwardIssue"), entry.get("inwardIssue")) if isinstance(entry, dict) else (None, None)
        other = out if isinstance(out, dict) else inn
        if not (isinstance(kind, dict) and word(kind.get("name")) and isinstance(other, dict) and ident(other.get("id")) and (out is None) != (inn is None)
                and isinstance(other.get("key"), str) and REF.fullmatch(other["key"])):
            raise Refused("a link of %s could not be read, so it is not known whether it is blocked" % key)
        # Seen from this item: `outwardIssue` means "this item <outward phrase> that one", so this item is the link's source.
        end = "source" if out is not None else "target"
        phrase = word(kind.get("outward") if out is not None else kind.get("inward"))
        other_status = status_of((other.get("fields") or {}).get("status"))
        if other_status is None:
            gaps.append("the status of %s, as shown inside %s" % (other["key"], key))
        links.append({"type": word(kind["name"]), "says": phrase or "?", "this_item_is": end, "other": other["key"], "other_id": other["id"], "other_status": other_status})
    due = fields.get("duedate")
    if due is not None and not (isinstance(due, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", due)):
        gaps.append("the due date of %s" % key)
        due = None
    stamps = {name: in_utc(fields.get(name)) for name in ("created", "updated")}
    kind = fields.get("issuetype")
    return {"key": key, "id": issue["id"], "issuetype": word(kind.get("name")) if isinstance(kind, dict) else None, "status": status,
            "priority": word(priority.get("name")) if isinstance(priority, dict) else None, "assignee": who, "duedate": due,
            "created": stamps["created"], "updated": stamps["updated"], "links": links, "copied_at": copied_at}, gaps


def save_json(path, data):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = "%s.%d.tmp" % (path, os.getpid())
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False, sort_keys=True)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def key_order(key):
    project, number = key.rsplit("-", 1)
    return project, int(number)


# ---------------------------------------------------------------- copy


def cmd_copy(args, conn, clock):
    if not PROJECT.fullmatch(args.project):
        raise Refused("the project is given by its key: letters and digits")
    refresh = args.refresh or []
    if any(not REF.fullmatch(key) for key in refresh) or len(set(refresh)) != len(refresh) or len(refresh) > 50:
        raise Refused("--refresh takes up to 50 item keys, such as ABC-12, each once")
    kept = None
    if refresh:
        try:
            with open(args.out, encoding="utf-8") as f:
                kept = json.load(f)
            ok = kept["format"] == FORMAT and isinstance(kept["items"], list)
        except (OSError, ValueError, KeyError, TypeError):
            ok = False
        if not ok:
            raise Refused("--refresh needs a records file already at --out, and there is none that can be read")

    me = read_me(conn)
    priorities = read_priorities(conn)
    link_types = read_link_types(conn)
    project = read_project(conn, args.project)
    site = site_fingerprint(conn.host)
    if kept and (kept.get("site_fingerprint"), (kept.get("project") or {}).get("id")) != (site, project["id"]):
        raise Refused("the records file at --out is of another site or another project")
    before, listed_before = snapshot(conn, project["id"])
    count_before = len(listed_before)
    gone, moved = [], []
    if refresh:
        if any(key.rsplit("-", 1)[0] != project["key"] for key in refresh):
            raise Refused("an item named in --refresh is not in project %s" % project["key"])
        found = []
        for key in sorted(refresh, key=key_order):
            issue = read_one(conn, key)                 # one request each: a search would refuse the whole list for one deleted key
            if issue is None:
                gone.append(key)
            elif issue.get("key") != key:               # Jira answers a request for an old key with the item under its new one
                moved.append((key, str(issue.get("key"))[:60]))
            else:
                found.append(issue)
    else:
        found = search_all(conn, "project = %s ORDER BY key ASC" % project["id"], FIELDS)
    copied_at = stamp(clock())
    records, gaps = [], []
    for issue in found:
        record, missing = record_of(issue, me, copied_at)
        if record["key"].rsplit("-", 1)[0] != project["key"]:
            raise Refused("Jira returned %s, which is not in project %s" % (record["key"], project["key"]))
        records.append(record)
        gaps += missing
    after, listed_after = snapshot(conn, project["id"])
    count_after = len(listed_after)

    if refresh:
        dropped = set(gone) | set(old for old, _ in moved)
        fresh_ids = set(r["id"] for r in records)
        records += [item for item in kept["items"] if item["key"] not in dropped and item["id"] not in fresh_ids]      # matched by Jira's id, which a key change does not alter
    elif len(records) != count_before:
        raise Refused("the project listed %d items and the copy holds %d, so the copy is not whole. Nothing is written" % (count_before, len(records)))
    records.sort(key=lambda r: key_order(r["key"]))
    data = {"format": FORMAT, "site_fingerprint": site, "project": project, "priorities": priorities, "link_types": link_types, "items": records,
            "note": "Copied by sync.py. No titles, descriptions or people. `assignee` is one of: me, someone else, nobody."}
    save_json(args.out, data)

    say("COPIED from Jira into local records. Jira was only read.")
    say("")
    say("Jira site:  https://%s  (site fingerprint %s)" % (conn.host, site))
    say("Project:    %s (project id %s)" % (project["key"], project["id"]))
    say("Copied at:  %s, by this computer's clock%s" % (copied_at, " (a made-up time, set by --pretend-now)" if args.pretend_now else ""))
    if refresh:
        say("Refreshed:  %s named, %d copied again: %s" % (len(refresh), len(found), ", ".join(sorted((i["key"] for i in found), key=key_order)) or "none"))
        if gone:
            say("            NO LONGER RETURNED BY JIRA, and taken out of the records: %s" % ", ".join(gone))
        for old, new in moved:
            say("            MOVED: Jira now returns %s as %s. It is taken out of the records. If it is still in this project, copy the whole project again" % (old, new))
        have = {r["key"]: r["updated"] for r in records}
        drifted = sorted((k for k in have if k in listed_after and listed_after[k] != have[k]), key=key_order)
        unknown = sorted((k for k in listed_after if k not in have), key=key_order)
        vanished = sorted((k for k in have if k not in listed_after), key=key_order)
        say("            CHANGED IN JIRA SINCE THEIR COPY, and not copied again: %s" % (", ".join(drifted) or "none that the listing shows"))
        if unknown or vanished:
            say("            IN JIRA WITH NO RECORD HERE: %s. RECORDS WITH NO ITEM IN JIRA'S LISTING: %s" % (", ".join(unknown) or "none", ", ".join(vanished) or "none"))
        older = sorted(set(r["copied_at"] for r in records if r["copied_at"] != copied_at))
        say("            The other %d items keep the copy they had, taken at: %s" % (len(records) - len(found), ", ".join(older) or "none"))
    say("Items in the records now: %d" % len(records))
    counts = {c: sum(1 for r in records if r["status"]["category"] == c) for c in CATEGORIES}
    say("  by Jira's status category: new %d, indeterminate %d, done %d" % (counts["new"], counts["indeterminate"], counts["done"]))
    say("  who has them: me %d, someone else %d, nobody %d" % tuple(sum(1 for r in records if r["assignee"] == w) for w in ("me", "someone else", "nobody")))
    say("  with no priority: %d. With no due date: %d. With links: %d" % (sum(1 for r in records if r["priority"] is None), sum(1 for r in records if r["duedate"] is None), sum(1 for r in records if r["links"])))
    say("The site's priorities, in the order Jira lists them, which is taken to be highest first: %s" % ", ".join(priorities))
    say("The site's link types: %s" % "; ".join("%s (%s / %s)" % (k["name"], k["outward"], k["inward"]) for k in link_types))
    if gaps:
        say("COULD NOT BE READ, and recorded as missing: %s" % "; ".join(gaps[:10]))
    say("NOT copied: titles, descriptions, comments, people's names, account ids. Who has an item is kept as one of three words.")
    say("")
    say("Snapshot of Jira before the copy: %s (%d items)" % (before, count_before))
    say("Snapshot of Jira after the copy:  %s (%d items)" % (after, count_after))
    if before == after:
        say("The two are the same: the two listings of the project agree, so no change to an item shows between them.")
    else:
        say("THE TWO DIFFER: someone changed an item of the project while it was being copied. This copy sends only reads, so it was")
        say("not this copy. The records may mix older and newer states. Copy again.")
    say("A snapshot is of every item's key and last-updated time, as a search lists them. A search can be behind.")
    if conn.only_read():
        say("Requests sent to Jira: %d. Every one was a GET with no body, which reads and cannot change anything." % len(conn.sent))
        say("  (%s)" % ("That is read back from each request as it was built, not assumed." if any(not m.endswith(")") for m, _, _ in conn.sent)
                         else "This is the fake Jira, which can only be read. For a real Jira the line above is read back from each request as built."))
    else:
        say("Requests sent to Jira: %d. NOT EVERY ONE WAS A PLAIN GET: %s" % (len(conn.sent), ", ".join(sorted(set("%s%s" % (m, " with a body" if b else "") for m, _, b in conn.sent)))))
    for path in sorted(set(path if "/issue/" not in path else "/rest/api/3/issue/{key}" for _, path, _ in conn.sent)):
        say("  GET %s  x%d" % (path, sum(1 for _, p, _ in conn.sent if (p if "/issue/" not in p else "/rest/api/3/issue/{key}") == path)))
    say("")
    say("Records written to the file given with --out: %s" % os.path.basename(args.out))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Copy a Jira project's items into local records. Reads only.")
    commands = parser.add_subparsers(dest="command", required=True)
    sub = commands.add_parser("copy")
    sub.add_argument("--source", choices=("live", "fake"), required=True)
    sub.add_argument("--project", required=True)
    sub.add_argument("--out", required=True, help="the records file to write")
    sub.add_argument("--refresh", nargs="+", metavar="KEY", help="copy only these items again, and keep the rest")
    sub.add_argument("--state", help="with --source fake: the folder that holds the fake Jira")
    sub.add_argument("--pretend-now", metavar="TIME", help="tests only, fake Jira only: the clock value for copied_at, as 2026-12-01T08:00:00Z")
    sub.add_argument("--log", help="also save the output here, with the site's address removed")
    args = parser.parse_args(argv)
    del LINES[:]
    secrets, conn, code = [], None, 0
    try:
        clock = now_utc
        if args.pretend_now:
            if args.source != "fake":
                raise Refused("--pretend-now is for the fake Jira only. A real copy is stamped with the real time")
            try:
                fixed = datetime.datetime.strptime(args.pretend_now, "%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                raise Refused("--pretend-now is a time such as 2026-12-01T08:00:00Z")
            clock = lambda: fixed  # noqa: E731
        if args.source == "fake":
            if not args.state:
                raise Refused("--source fake needs --state, the folder that holds the fake Jira")
            import fake_jira
            fake = fake_jira.FakeJira.open(os.path.join(args.state, "fake-jira.json"))
            conn = Connection(fake.get, urllib.parse.urlparse(fake_jira.SITE).hostname)
            code = cmd_copy(args, conn, clock)
            fake.save(os.path.join(args.state, "fake-jira.json"))
        else:
            conn, secrets = make_live()
            code = cmd_copy(args, conn, clock)
    except Refused as refusal:
        say("")
        say("REFUSED: %s." % refusal)
        say("No records were written. Nothing was changed in Jira: this command can only read.")
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
