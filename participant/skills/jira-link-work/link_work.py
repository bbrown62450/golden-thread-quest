#!/usr/bin/env python3
"""Links Jira issues, after a preview that says each link in words and a confirmation by a person.

    link_work.py preview --source live|fake --request REQUEST.json --allowlist FILE --state DIR
    link_work.py confirm --source live|fake --request REQUEST.json --allowlist FILE --state DIR \
                         --fingerprint CODE --confirmed-by NAME
    link_work.py check   --source live|fake --state DIR --fingerprint CODE

A REQUEST IS WRITTEN AS SENTENCES, one to five of them:

    {"links": [{"from": "SAND-1", "phrase": "blocks", "to": "SAND-2"}]}        read: SAND-1 blocks SAND-2

"phrase" must be a phrase the Jira site itself uses for one of its link types, such as "blocks" or "is blocked by".
The workflow reads the site's link types and finds the phrase there. Nobody writes Jira's slot names. "SAND-2 is
blocked by SAND-1" is the same link as "SAND-1 blocks SAND-2", and is treated as the same.

WHICH LINKS IT WILL CREATE. Only the link types named Blocks and Relates. A phrase belonging to any other type is
refused: "duplicates" tells people to stop work on an item, and on some sites closes it; "clones" records a history
that did not happen; and what a site's own extra types set off cannot be known from here.

DIRECTION. Every link has a source and a target: "source <outward phrase> target", as in "SAND-1 blocks SAND-2". The
other item shows the same link with the type's inward phrase: "SAND-2 is blocked by SAND-1". For a type whose two
phrases are the same, as "relates to" is, there is no direction and either order is the same link.

    What Jira is sent has two slots, `inwardIssue` and `outwardIssue`. THIS WORKFLOW PUTS THE SOURCE IN `inwardIssue`
    AND THE TARGET IN `outwardIssue`. Those names read the other way round to many people, and that mapping is the
    one thing here that a test against a fake Jira cannot prove. So after every write the link is read back FROM
    BOTH ITEMS, and what each item shows is put into words and compared with the sentence in the request. A link
    that reads backwards ends the run with "A PERSON NEEDS TO LOOK", the link's id, and the words that it IS
    in Jira and must be removed by hand.
    WHAT THE READ-BACK PROVES, AND WHAT IT DOES NOT. It proves that the write and the reads agree with each other.
    Both rest on one more belief: that when an item lists a link with `outwardIssue`, that item is the source. If
    THAT were wrong, every check here would say "yes" about a backwards link. Only a person looking at the item in
    Jira's own screen settles it.

preview   reads Jira and writes nothing. It has no way to send a write. For each link it says the sentence, the same
          link from the other item, exactly what would be sent, the permission check and the duplicate check.
          Refused, with no fingerprint, if any link in the request:
            names an item Jira does not return, or the same item twice;
            has an item in a project that is not on the sandbox allowlist. BOTH items must be;
            uses a phrase that is not one of the site's, or belongs to a type this workflow does not create;
            already exists THE OTHER WAY ROUND (a conflict), or is asked for twice in one request;
            would close a circle: for a link with a direction, existing links of the same type are followed from the
            target, and if they lead back to the source the link is refused. At most 50 items are read; a chain
            longer than that is refused, because the check could not be finished.
          A link that is already there, the same type and the same way round, is reported and NOT created again.
          If every link is already there, no fingerprint is issued.

confirm   creates the links of one preview, named by its fingerprint, and only if all of this holds at that moment:
            a fingerprint and the confirming person's name are given;
            the saved preview is unaltered, unused and at most 15 minutes old;
            the request still asks for exactly what the preview showed, link for link;
            every item is on the sandbox allowlist, and Jira still says this identity may link issues there;
            both items of each link, read again just before its write, still show no such link and no opposite one.
          Each link is sent once, and read back from both items before the next is sent. If one fails, the run stops
          there and says which links were written and which were not. Nothing is undone. A new preview then finds
          the links that were made and offers only the rest.
          If Jira accepts a write and the items do not list the link yet, they are read again, up to three times,
          two seconds apart. The write is never sent again.

check     reads the links of a confirmed preview back from both items. It writes nothing.

What this cannot do. Jira's request to create a link has no "only if there is none like it" condition that this
workflow relies on. Between the last read and the write there is a moment in which another run could create the
same link. One run at a time may confirm a request file, in one state folder, on this computer; nothing stops a run
on another computer, with another state folder, or with the same link in a request of another name. If two links
appear, the count after the write reports a double. A real Jira may instead ignore the second write and still
answer that it succeeded: the workflow then finds the one link and cannot tell which run made it.
A link type's name and its two phrases are the site's own text, set by whoever administers the site. They are shown
and saved, because they are the sentence. They are held to 60 characters with no unseen characters. A link is found by reading the two items, which shows only the links this
identity may see. The circle check follows links of ONE type: "A blocks B" and "B relates to A" is not a circle.

--pretend-minutes-later N (confirm) is for tests: it moves "now" forward. It can only make a preview older.
--log FILE saves the output with the site's address replaced by a marker and the items' titles left out.
--result FILE saves the result record as Markdown, the same way.

Nothing in an item's title is acted on. Titles are shown on screen, marked as other people's text, so that a person
can see which items these are. They are not saved.

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
MAX_LINKS = 5
MAX_FOLLOWED = 50
ALLOWED_TYPES = ("Blocks", "Relates")      # by the type's name on the site. Any other type is refused
REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,60}")
PHRASE = re.compile(r"[a-z][a-z ]{0,38}[a-z]")
TIME_FORMAT = "%Y-%m-%d %H:%M:%S UTC"
SITE_MARK = "[site address removed]"
ISSUE_FIELDS = "summary,project,issuelinks,updated"
WRITE_PATH = "/rest/api/3/issueLink"
REFUSALS = (400, 401, 403, 404)   # answers that mean Jira did not take the write. Any other failure is not taken to mean that
UNSEEN = re.compile("[\\x00-\\x09\\x0b-\\x1f\\x7f-\\xa0\\u00ad\\u034f\\u061c\\u115f\\u1160\\u200b-\\u200f\\u2028\\u2029\\u202a-\\u202e\\u2060-\\u2069\\u2800\\u3164\\ufeff\\U000e0000-\\U000e007f]")

READ_AGAIN = 3       # how many times the two items are read after a write that Jira accepted, if the link is not listed yet
PAUSE_SECONDS = 2

LINES = []      # each is (what is shown on screen, what is saved)
PENDING = {}    # the result record, written by main() only after the output has been searched for credentials


class Refused(Exception):
    """Nothing was written by this run. The message is the reason."""


class NotWritten(Refused):
    """A write was sent, and Jira's answer and a read afterwards show that nothing was written."""


class NeedsLooking(Exception):
    """A person needs to look. The message says what is and is not known."""


class Backwards(NeedsLooking):
    """A link now exists in Jira the wrong way round."""


def pause():
    time.sleep(PAUSE_SECONDS)


def say(text="", saved=None):
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
        try:
            return self._get(path, params)
        except (OSError, TimeoutError) as err:
            reason = "could not reach Jira (%s)" % type(getattr(err, "reason", err)).__name__
            if self.posted():
                raise NeedsLooking("after a write was sent, a read failed: %s" % reason)
            raise Refused(reason)

    def post_link(self, type_id, source_id, target_id):
        """One new link: "source <outward phrase> target". The source goes in Jira's `inwardIssue`, the target in `outwardIssue`."""
        if self._post is None:
            raise Refused("this command has no way to write")
        if not (ident(type_id) and ident(source_id) and ident(target_id)) or source_id == target_id:
            raise Refused("a write names the link type and two different items by their ids")
        body = {"type": {"id": type_id}, "inwardIssue": {"id": source_id}, "outwardIssue": {"id": target_id}}
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
        ok = (path == WRITE_PATH and not params and isinstance(body, dict) and set(body) == {"type", "inwardIssue", "outwardIssue"}
              and all(isinstance(body[name], dict) and set(body[name]) == {"id"} and ident(body[name]["id"]) for name in body))
        if not ok:
            raise Refused("the only write this workflow sends is one new link: a link type and two items, each by its id")
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
    try:
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


def read_request(path):
    name = os.path.basename(path)
    if not name.endswith(".json") or not REF.fullmatch(name[:-5]):
        raise Refused("a request is a file whose name is letters, digits and dashes, ending in .json")
    data = read_json(path, "request")
    links = data.get("links") if isinstance(data, dict) and set(data) == {"links"} else None
    if not isinstance(links, list) or not 1 <= len(links) <= MAX_LINKS:
        raise Refused("the request must have exactly 'links': a list of 1 to %d links" % MAX_LINKS)
    wanted = []
    for number, link in enumerate(links, 1):
        if not isinstance(link, dict) or set(link) != {"from", "phrase", "to"}:
            raise Refused("link %d must have exactly 'from', 'phrase' and 'to'" % number)
        for end in ("from", "to"):
            if not isinstance(link[end], str) or not REF.fullmatch(link[end]):
                raise Refused("link %d: '%s' is an item's key or issue id: letters, digits and dashes only. A title is not accepted" % (number, end))
        if not isinstance(link["phrase"], str) or not PHRASE.fullmatch(link["phrase"]):
            raise Refused("link %d: the phrase is a few plain words in small letters, such as \"blocks\" or \"is blocked by\"" % number)
        wanted.append({"from": link["from"], "phrase": link["phrase"], "to": link["to"]})
    with open(path, "rb") as f:
        sha = hashlib.sha256(f.read()).hexdigest()
    return {"name": name[:-5], "links": wanted, "source": name, "source_sha": sha}


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
                since = now_utc()
            if now_utc() - since <= datetime.timedelta(minutes=CLAIM_MINUTES):
                raise Refused("another run is confirming this request at this moment (its claim was last renewed at %s). If no run is, that "
                              "run was killed: wait until %d minutes after that time, then preview again" % (stamp(since), CLAIM_MINUTES))
            try:
                os.remove(path)
            except OSError:
                pass
    raise Refused("another run took this request at the same moment")


def holds(claim):
    """True if the claim file is still this run's own."""
    path, mark = claim
    try:
        with open(path, encoding="ascii") as f:
            return f.read().split("|")[-1].strip() == mark
    except OSError:
        return False


def renew(claim):
    """Before each write: the claim must still be this run's, and its time is brought up to date."""
    if not holds(claim):
        raise Refused("this run's claim on the request has been taken by another run, so it sends nothing more")
    with open(claim[0], "w", encoding="ascii") as f:
        f.write("%s|%s" % (stamp(now_utc()), claim[1]))


def release(claim):
    if holds(claim):            # never another run's
        try:
            os.remove(claim[0])
        except OSError:
            pass


# ---------------------------------------------------------------- reading Jira


def read_types(conn):
    """The site's link types: [{"id", "name", "inward", "outward"}]. Their names and phrases are the site's own text."""
    status, _, body = conn.get("/rest/api/3/issueLinkType")
    if status == 401:
        raise Refused("Jira rejected the credentials (401). Check JIRA_EMAIL and JIRA_API_TOKEN")
    listed = body.get("issueLinkTypes") if status == 200 and isinstance(body, dict) else None
    if not isinstance(listed, list) or not listed:
        raise Refused("Jira did not list its link types (status %d). Issue linking may be turned off on this site" % status)
    types = []
    for entry in listed:
        ok = isinstance(entry, dict) and ident(entry.get("id")) and all(isinstance(entry.get(k), str) and entry[k] and len(entry[k]) <= 60 and not UNSEEN.search(entry[k]) for k in ("name", "inward", "outward"))
        if not ok:
            raise Refused("Jira's list of link types could not be read")
        types.append({"id": entry["id"], "name": entry["name"], "inward": entry["inward"], "outward": entry["outward"]})
    return types


def type_for(types, phrase, number):
    """The link type a phrase belongs to, and whether the phrase is its outward or its inward one."""
    found = [(t, side) for t in types for side in ("outward", "inward") if t[side] == phrase]
    kinds = sorted(set(t["id"] for t, _ in found))
    if not kinds:
        offered = sorted(set(quoted(t[side]) for t in types if t["name"] in ALLOWED_TYPES for side in ("outward", "inward")))
        raise Refused("link %d: %s is not a phrase this Jira site uses for a link type. For the types this workflow creates, the site's "
                      "phrases are: %s. A phrase is matched exactly" % (number, quoted(phrase), ", ".join(offered) or "none"))
    if len(kinds) > 1:
        raise Refused("link %d: on this site the phrase %s belongs to %d link types, so it does not say which link is meant" % (number, quoted(phrase), len(kinds)))
    kind = found[0][0]
    if kind["name"] not in ALLOWED_TYPES:
        raise Refused("link %d: %s is a phrase of the link type %s, which this workflow does not create. It creates links of the "
                      "types %s only. Make this link by hand in Jira if it is right" % (number, quoted(phrase), quoted(kind["name"]), " and ".join(ALLOWED_TYPES)))
    symmetric = kind["inward"] == kind["outward"]
    return kind, symmetric, ("outward" if symmetric else found[0][1])


class Reader:
    """Reads items and remembers them for the length of one look at Jira, so that one item is one read."""

    def __init__(self, conn):
        self.conn, self.by_id, self.by_ref = conn, {}, {}

    def read(self, ref, what):
        if ref in self.by_ref:
            return self.by_ref[ref]
        status, _, issue = self.conn.get("/rest/api/3/issue/%s" % ref, {"fields": ISSUE_FIELDS})
        if status == 401:
            raise Refused("Jira rejected the credentials (401). Check JIRA_EMAIL and JIRA_API_TOKEN")
        if status == 404:
            raise Refused("Jira answered 404 for %s. It does not exist, or this identity is not permitted to see it. Jira gives one answer for both" % what)
        fields = issue.get("fields") if status == 200 and isinstance(issue, dict) else None
        project = fields.get("project") if isinstance(fields, dict) else None
        listed = fields.get("issuelinks") if isinstance(fields, dict) else None
        ok = (isinstance(project, dict) and isinstance(listed, list) and ident(issue.get("id")) and ident(project.get("id"))
              and isinstance(issue.get("key"), str) and REF.fullmatch(issue["key"]) and isinstance(project.get("key"), str) and REF.fullmatch(project["key"]))
        if not ok:
            raise Refused("Jira's answer for %s could not be used (status %d)" % (what, status))
        links = []
        for entry in listed:
            kind = entry.get("type") if isinstance(entry, dict) else None
            out, inn = (entry.get("outwardIssue"), entry.get("inwardIssue")) if isinstance(entry, dict) else (None, None)
            other = out if isinstance(out, dict) else inn
            if not (isinstance(kind, dict) and ident(kind.get("id")) and ident(entry.get("id")) and isinstance(other, dict) and ident(other.get("id"))
                    and (out is None) != (inn is None)):
                raise Refused("Jira's list of the links of %s could not be read, so the duplicate check cannot be made" % what)
            key = other.get("key") if isinstance(other.get("key"), str) and REF.fullmatch(other["key"]) else "?"
            # Seen from this item: `outwardIssue` means "this item <outward phrase> that one", so this item is the source.
            links.append({"id": entry["id"], "type_id": kind["id"], "source": issue["id"] if out is not None else other["id"],
                          "target": other["id"] if out is not None else issue["id"], "other_id": other["id"], "other_key": key})
        title = fields.get("summary")
        item = {"id": issue["id"], "key": issue["key"], "project_id": project["id"], "project_key": project["key"], "updated": str(fields.get("updated", ""))[:40],
                "title": UNSEEN.sub("?", title)[:120] if isinstance(title, str) else "(Jira gave no title)", "links": links}
        self.by_ref[ref] = self.by_ref[item["id"]] = self.by_ref[item["key"]] = self.by_id[item["id"]] = item
        return item


def read_permissions(conn, issue_id):
    names = ("BROWSE_PROJECTS", "LINK_ISSUES")
    status, _, body = conn.get("/rest/api/3/mypermissions", {"issueId": issue_id, "permissions": ",".join(names)})
    found = body.get("permissions") if status == 200 and isinstance(body, dict) else None
    if not isinstance(found, dict):
        raise Refused("Jira did not answer the permission check (status %d), so nothing is assumed" % status)
    return {name: (found.get(name) or {}).get("havePermission") is True for name in names}


# ---------------------------------------------------------------- what a link is


def same_link(link, want):
    """A link an item lists is the link wanted: the same type, the same way round. A type with no direction: either way."""
    if link["type_id"] != want["type"]["id"]:
        return False
    there, asked = (link["source"], link["target"]), (want["source"]["id"], want["target"]["id"])
    return there == asked or (want["symmetric"] and there == asked[::-1])


def opposite_link(link, want):
    return not want["symmetric"] and link["type_id"] == want["type"]["id"] and (link["source"], link["target"]) == (want["target"]["id"], want["source"]["id"])


def in_words(item, link, kind, keys):
    """What an item shows for one of its links, as a sentence: "SAND-1 blocks SAND-2" or "SAND-2 is blocked by SAND-1"."""
    phrase = kind["outward"] if link["source"] == item["id"] else kind["inward"]
    other = link["target"] if link["source"] == item["id"] else link["source"]
    return "%s %s %s" % (item["key"], phrase, keys.get(other, link["other_key"]))


def leads_back(reader, want, planned):
    """True if links of the same type, followed from the target, lead back to the source. Raises if it cannot finish."""
    start, goal, type_id = want["target"]["id"], want["source"]["id"], want["type"]["id"]
    seen, queue = {start}, [start]
    while queue:
        node = queue.pop(0)
        if len(seen) > MAX_FOLLOWED:
            raise Refused("link %d: following %s links from %s reaches more than %d items, so the check for a circle could not be finished. "
                          "Nothing is assumed" % (want["n"], quoted(want["type"]["outward"]), want["target"]["key"], MAX_FOLLOWED))
        item = reader.read(node, "an item further along the chain from %s" % want["target"]["key"])
        onward = [link["target"] for link in item["links"] if link["type_id"] == type_id and link["source"] == node]
        onward += [target for kind, source, target in planned if kind == type_id and source == node]
        for following in onward:
            if following == goal:
                return True
            if following not in seen:
                seen.add(following)
                queue.append(following)
    want["followed"] = len(seen)
    return False


def build_proposal(conn, request, allowlist_path):
    """The one place that decides what a request means. The preview shows its result; confirm compares with it.
    Returns (proposal, the items read, by id)."""
    allowed, note = load_allowlist(allowlist_path)
    site = site_fingerprint(conn.host)
    types = read_types(conn)
    reader = Reader(conn)
    permissions, wants, planned = {}, [], []
    for number, link in enumerate(request["links"], 1):
        kind, symmetric, side = type_for(types, link["phrase"], number)
        start, end = reader.read(link["from"], "the item %s" % quoted(link["from"])), reader.read(link["to"], "the item %s" % quoted(link["to"]))
        if start["id"] == end["id"]:
            raise Refused("link %d names one item twice (%s, issue id %s). An item is not linked to itself" % (number, start["key"], start["id"]))
        for item in (start, end):
            if (site, item["project_id"]) not in allowed:
                raise Refused("link %d: %s is in project %s (project id %s), which on the Jira site with fingerprint %s is not on the sandbox allowlist "
                              "(%s). A link changes both items, so both must be in a project listed there"
                              % (number, item["key"], item["project_key"], item["project_id"], site, os.path.basename(allowlist_path)))
            if item["id"] not in permissions:
                permissions[item["id"]] = read_permissions(conn, item["id"])
            if not all(permissions[item["id"]].values()):
                raise Refused("link %d: Jira says this identity may not link issues for %s (LINK_ISSUES: %s)" % (number, item["key"], "yes" if permissions[item["id"]]["LINK_ISSUES"] else "no"))
        source, target = (start, end) if side == "outward" else (end, start)
        brief = lambda item: {"id": item["id"], "key": item["key"], "project_id": item["project_id"], "project_key": item["project_key"]}  # noqa: E731
        want = {"n": number, "from": link["from"], "phrase": link["phrase"], "to": link["to"], "type": kind, "symmetric": symmetric,
                "source": brief(source), "target": brief(target),
                "sentence": "%s %s %s" % (start["key"], link["phrase"], end["key"]),
                "other_side": "%s %s %s" % (end["key"], kind["inward"] if side == "outward" else kind["outward"], start["key"])}
        for earlier in wants:
            if earlier["type"]["id"] == kind["id"] and {earlier["source"]["id"], earlier["target"]["id"]} == {source["id"], target["id"]}:
                raise Refused("link %d is link %d again, or its opposite. A request asks for each link once" % (number, earlier["n"]))
        on_source = sorted(l["id"] for l in source["links"] if same_link(l, want))
        on_target = sorted(l["id"] for l in target["links"] if same_link(l, want))
        if on_source != on_target:
            raise Refused("link %d: %s and %s do not list the same links between them, so it cannot be told whether this link exists. "
                          "This identity may not be able to see one of them fully" % (number, source["key"], target["key"]))
        against = sorted(set(l["id"] for item in (source, target) for l in item["links"] if opposite_link(l, want)))
        if against:
            raise Refused("link %d: THE OPPOSITE LINK ALREADY EXISTS (link id %s): %s. The request says: %s. Both cannot be meant. "
                          "Nothing is created. A person decides which way round is right, and removes the wrong one by hand"
                          % (number, ", ".join(against), "%s %s %s" % (target["key"], kind["outward"], source["key"]), want["sentence"]))
        want["existing"] = on_source
        want["action"] = "exists" if on_source else "create"
        want["listed"] = {source["id"]: len(source["links"]), target["id"]: len(target["links"])}
        if not symmetric and not on_source:
            if leads_back(reader, want, planned):
                raise Refused("link %d: THIS LINK WOULD CLOSE A CIRCLE. Followed from %s, existing %s links lead back to %s. With this link, "
                              "each item in the circle would wait for the next, for ever. Nothing is created"
                              % (number, target["key"], quoted(kind["outward"]), source["key"]))
        if want["action"] == "create":
            planned.append((kind["id"], source["id"], target["id"]))
        wants.append(want)
    proposal = {"site": site, "request": request["name"], "source": request["source"], "source_sha": request["source_sha"], "allowlist": note, "links": wants,
                "permissions": {issue_id: permissions[issue_id] for issue_id in sorted(permissions)}}
    return proposal, reader.by_id


def snapshot(items, proposal):
    """One short code for what Jira returned of the items the request names: each one's last-updated time and its links."""
    named = sorted(set(end["id"] for want in proposal["links"] for end in (want["source"], want["target"])))
    text = canonical([[i, items[i]["updated"], sorted([l["id"], l["type_id"], l["source"], l["target"]] for l in items[i]["links"])] for i in named])
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
    say("Jira site:  https://%s  (site fingerprint %s)" % (conn.host, proposal["site"]))
    projects = sorted(set((end["project_key"], end["project_id"]) for want in proposal["links"] for end in (want["source"], want["target"])))
    say("Project%s   %s. On the sandbox allowlist: yes." % ("s:" if len(projects) > 1 else ": ", ", ".join("%s (project id %s)" % p for p in projects)))
    say("            The allowlist is %s." % proposal["allowlist"])


# ---------------------------------------------------------------- preview


def cmd_preview(args, conn):
    request = read_request(args.request)
    proposal, items = build_proposal(conn, request, args.allowlist)
    before = snapshot(items, proposal)
    again, items_again = build_proposal(conn, request, args.allowlist)
    after = snapshot(items_again, again)
    if after != before or canonical(again) != canonical(proposal):
        raise Refused("the items or their links changed in Jira while the preview was being made. Preview again")
    wants = proposal["links"]
    to_create = [want for want in wants if want["action"] == "create"]
    say("PREVIEW. Nothing has been written." if to_create else "NOTHING TO CREATE. Nothing has been written.")
    say("")
    head(conn, proposal)
    say("Request:    %s, sha256 %s. It asks for %s. To create: %d. Already there: %d."
        % (proposal["source"], proposal["source_sha"][:16], plural(len(wants), "link"), len(to_create), len(wants) - len(to_create)))
    for want in wants:
        kind, source, target = want["type"], want["source"], want["target"]
        say("")
        say("LINK %d of %d.  %s" % (want["n"], len(wants), "TO CREATE" if want["action"] == "create" else "ALREADY THERE. It is not created again"))
        say("  IN WORDS:                        %s." % want["sentence"])
        say("  The same link, from the other item: %s." % want["other_side"])
        if kind["outward"] == "blocks" and not want["symmetric"]:
            say("  That is: %s comes first, and %s waits for it." % (source["key"], target["key"]))
        say("  READ IT ALOUD. If the sentence is backwards, so is the link. The sentence is what you are confirming.")
        if want["symmetric"]:
            say("  This link type has one phrase for both items, so it has no direction: either order is the same link.")
        say("  Link type:  %s (link type id %s). On this site its phrases are %s and %s." % (quoted(kind["name"]), kind["id"], quoted(kind["outward"]), quoted(kind["inward"])))
        say("  The items, each found by the reference in the request and by nothing else. The issue id is what the fingerprint is tied to:")
        for end in ((source, target) if want["sentence"].startswith(source["key"] + " ") else (target, source)):       # in the order the sentence names them
            say("    %s (issue id %s), in project %s (project id %s). Its title, for you to check it is the item you mean. It is other" % (end["key"], end["id"], end["project_key"], end["project_id"]))
            say("    people's text: shown, and not acted on.")
            say("    | %s" % items[end["id"]]["title"], "    | [the title was shown on screen and is not saved: %d characters]" % len(items[end["id"]]["title"]))
        if want["action"] == "create":
            say("  For the record, exactly what is sent to Jira, and nothing else:")
            say("    type          link type id %s (%s)" % (kind["id"], quoted(kind["name"])))
            say("    inwardIssue   issue id %s (%s), the item that %s" % (source["id"], source["key"], quoted(kind["outward"])))
            say("    outwardIssue  issue id %s (%s), the item that %s" % (target["id"], target["key"], quoted(kind["inward"])))
            say("    DO NOT JUDGE THE LINK BY THESE TWO SLOT NAMES. They are Jira's, and they read the wrong way round to many people,")
            say("    people who know Jira included. Judge the sentence. The workflow filled the slots in from it, and after the write")
            say("    it reads the link back from BOTH items and compares what each shows with the sentence.")
        say("  Permission check, asked of Jira for each item and this identity (may see it / may link issues):")
        for end in (source, target):
            have = proposal["permissions"][end["id"]]
            say("    %s: %s / %s" % (end["key"], "yes" if have["BROWSE_PROJECTS"] else "no", "yes" if have["LINK_ISSUES"] else "no"))
        say("  Duplicate check, made against Jira just now: %s lists %s and %s lists %s that this identity can see."
            % (source["key"], plural(want["listed"][source["id"]], "link"), target["key"], plural(want["listed"][target["id"]], "link")))
        say("    This same link, the same type and the same way round: %d%s." % (len(want["existing"]), " (link id %s)" % ", ".join(want["existing"]) if want["existing"] else ""))
        if not want["symmetric"]:
            say("    The opposite link, which would be a conflict: 0.")
            if want["action"] == "create":
                say("    Circle check: %s links were followed onward from %s. Items reached, %s included: %d. None is %s."
                    % (quoted(kind["outward"]), target["key"], target["key"], want["followed"], source["key"]))
    say("")
    say("Where Jira cannot check: this workflow relies on no 'only if there is none like it' condition in Jira's request to")
    say("  create a link. The confirmation reads both items of each link again just before writing it, and stops if the link,")
    say("  or its opposite, is there by then.")
    say("")
    say("Snapshot of the items named, as Jira returned them, before the preview: %s" % before)
    say("Snapshot of the items named, as Jira returned them, after the preview:  %s" % after)
    say("The two are the same. Jira is unchanged, as far as two reads of each item can show. A snapshot is of each item's")
    say("  last-updated time and of every link it lists.")
    requests_line(conn)
    say("")
    if not to_create:
        say("Every link asked for is already there. No fingerprint is issued, because there is nothing to confirm, and nothing was sent.")
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
    say("Nothing has been written. To create %s, a person who has read this preview confirms it by its fingerprint."
        % ("this link" if len(to_create) == 1 else "these %d links" % len(to_create)))
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
    messages = body.get("errorMessages") if isinstance(body, dict) else None
    texts = [m for m in messages if isinstance(m, str)] if isinstance(messages, list) else []
    return UNSEEN.sub(" ", " / ".join(texts))[:200]


def differences(before, now):
    """How the request worked out now differs from the preview: a list of words, empty if it is the same."""
    if before["source_sha"] != now["source_sha"] or before["source"] != now["source"]:
        return ["the request is not the file the preview showed"]
    if before["allowlist"] != now["allowlist"]:
        return ["the allowlist file is not the one the preview used"]
    said = []
    for old, new in zip(before["links"], now["links"]):
        if (old["type"]["id"], old["source"]["id"], old["target"]["id"]) != (new["type"]["id"], new["source"]["id"], new["target"]["id"]):
            said.append("link %d is no longer the same link: a reference now leads to another item, or the site's phrases have changed" % old["n"])
        elif old["type"] != new["type"]:
            said.append("link %d: the site's words for this link type have changed since the preview" % old["n"])
        elif old["action"] != new["action"] or old["existing"] != new["existing"]:
            said.append("link %d: it was %s when previewed, and is %s now (link id %s)" % (old["n"], "to be created" if old["action"] == "create" else "already there",
                                                                                         "already there" if new["action"] == "exists" else "not there", ", ".join(new["existing"]) or "none"))
        elif old["source"] != new["source"] or old["target"] != new["target"]:
            said.append("link %d: an item has moved to another project or been given another key since the preview" % old["n"])
    return said


def look(conn, want, known):
    """Both items of one link, read afresh. Returns (source item, target item, ids of this same link that are new on
    each side, ids of an OPPOSITE link that are new)."""
    reader = Reader(conn)
    source, target = reader.read(want["source"]["id"], want["source"]["key"]), reader.read(want["target"]["id"], want["target"]["key"])
    new = [sorted(l["id"] for l in item["links"] if same_link(l, want) and l["id"] not in known) for item in (source, target)]
    backwards = sorted(set(l["id"] for item in (source, target) for l in item["links"] if opposite_link(l, want) and l["id"] not in known))
    return source, target, new, backwards


def read_back(conn, want, link_id, source, target):
    """What each item shows for the link, in words, compared with the request's sentence. Returns [(what, ok)]."""
    kind, keys = want["type"], {source["id"]: source["key"], target["id"]: target["key"]}
    expected = {source["id"]: "%s %s %s" % (source["key"], kind["outward"], target["key"]), target["id"]: "%s %s %s" % (target["key"], kind["inward"], source["key"])}
    checks = []
    for item in (source, target):
        held = [l for l in item["links"] if l["id"] == link_id]
        shown = in_words(item, held[0], kind, keys) if held else "NOT LISTED"
        right = bool(held) and held[0]["type_id"] == kind["id"] and (shown == expected[item["id"]] or (want["symmetric"] and shown == "%s %s %s" % (item["key"], kind["outward"], keys[target["id"] if item is source else source["id"]])))
        checks.append(("read from %s: it lists link id %s as: %s. Wanted: %s. Type %s" % (item["key"], link_id, shown, expected[item["id"]], quoted(kind["name"])), right))
    status, _, body = conn.get("/rest/api/3/issueLink/%s" % link_id)
    ends = [(body.get(slot) or {}).get("id") for slot in ("inwardIssue", "outwardIssue")] if status == 200 and isinstance(body, dict) else [None, None]
    wanted = [source["id"], target["id"]]
    checks.append(("the link read by its own id: Jira's `inwardIssue` is issue id %s and `outwardIssue` is issue id %s, as sent" % (ends[0] or "?", ends[1] or "?"),
                   ends == wanted or (want["symmetric"] and ends == wanted[::-1])))
    same = [sorted(l["id"] for l in item["links"] if same_link(l, want)) for item in (source, target)]
    checks.append(("links between these two items of this type and this way round, counted on each: %d and %d. One is wanted" % (len(same[0]), len(same[1])), len(same[0]) == 1 and len(same[1]) == 1))
    return checks


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
    request = read_request(args.request)
    claim = claim_request(args.state, request["name"])
    try:
        return confirm_claimed(args, conn, request, code, name, claim)
    finally:
        release(claim)


def confirm_claimed(args, conn, request, code, name, claim):
    preview_file, saved, made, status = read_preview_record(args.state, code)      # read AFTER the claim
    if status != "open":
        raise Refused("the preview %s has been used: writing began for it (recorded as '%s'). A fingerprint is used once. "
                      "Preview again: links that were made will be found, and not made again" % (code, status))
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
    proposal, _ = build_proposal(conn, request, args.allowlist)
    differs = differences(before, proposal)
    if differs:
        raise Refused("the change is not the one that was previewed: %s. Make a new preview and read it" % "; ".join(differs))
    to_create = [want for want in proposal["links"] if want["action"] == "create"]

    say("CONFIRMATION for preview %s, given by: %s (the name given with the confirmation)." % (code, name))
    say("")
    head(conn, proposal)
    say("")
    say("Checked in this run, before writing:")
    say("  the preview is %s old, and the limit is %d: ok" % (plural(int(age.total_seconds() // 60), "minute"), LIMIT_MINUTES))
    say("  what the saved preview holds still matches its fingerprint, and it is marked as not used: ok")
    say("  the request asks for exactly what the preview showed, link for link: ok")
    say("  every item is in a project on the sandbox allowlist for this site: ok")
    say("  Jira says this identity may link issues for every item: ok")
    say("  no link asked for has appeared since the preview, the same way round or the opposite: ok")
    say("")

    result = {"fingerprint": saved["fingerprint"], "confirmed_by": name, "confirmed_at": stamp(confirmed), "preview_made_at": saved["made_at"],
              "site_fingerprint": proposal["site"], "source": proposal["source"], "source_sha": proposal["source_sha"], "links": []}
    for want in proposal["links"]:
        result["links"].append({"n": want["n"], "sentence": want["sentence"], "other_side": want["other_side"], "type": want["type"], "symmetric": want["symmetric"],
                                "source": want["source"], "target": want["target"], "status": "not sent" if want["action"] == "create" else "already there",
                                "link_id": want["existing"][0] if want["existing"] else None, "written_at": None, "read_back": None})
    written_file = os.path.join(args.state, "written", code + ".json")
    saved["state"] = "writing"
    save_json(preview_file, saved)
    save_json(written_file, result)
    say("The confirmation and the writes happen in this one run of the command.")

    for want, entry in zip(proposal["links"], result["links"]):
        say("")
        if want["action"] == "exists":
            say("LINK %d of %d: %s. ALREADY THERE (link id %s). Not sent." % (want["n"], len(proposal["links"]), want["sentence"], ", ".join(want["existing"])))
            continue
        # The last read before this write: both items, by their issue ids.
        source, target, new, backwards = look(conn, want, set())
        if new[0] or new[1] or backwards:
            stop_batch(written_file, result, entry, "not sent")
            raise Refused("link %d (%s): just before its write, the link or its opposite was found there (link id %s). It is not sent%s"
                          % (want["n"], want["sentence"], ", ".join(new[0] or new[1] or backwards), written_so_far(result)))
        if (source["project_id"], target["project_id"]) != (want["source"]["project_id"], want["target"]["project_id"]):
            stop_batch(written_file, result, entry, "not sent")
            raise Refused("link %d (%s): just before its write, an item was found to have moved to another project. It is not sent%s"
                          % (want["n"], want["sentence"], written_so_far(result)))
        renew(claim)
        known = set(l["id"] for item in (source, target) for l in item["links"])
        entry["status"] = "sending"
        save_json(written_file, result)        # written down BEFORE the request goes
        say("LINK %d of %d: %s." % (want["n"], len(proposal["links"]), want["sentence"]))
        answered = None
        try:
            answered, _, body = conn.post_link(want["type"]["id"], want["source"]["id"], want["target"]["id"])
        except (OSError, TimeoutError) as err:
            say("  The write was sent and NO ANSWER came back (%s). It was not sent again. Reading both items to see:" % type(getattr(err, "reason", err)).__name__)
        source, target, new, backwards = look(conn, want, known)
        for _ in range(READ_AGAIN):
            if answered not in (200, 201) or new[0] or new[1] or backwards:
                break
            say("  Jira accepted the write and the items do not list the link yet. Reading them again in %d seconds. The write is not sent again." % PAUSE_SECONDS)
            pause()
            source, target, new, backwards = look(conn, want, known)
        if backwards and (answered is None or answered in (200, 201)):
            entry["link_id"] = backwards[0]
            stop_batch(written_file, result, entry, "A LINK THE WRONG WAY ROUND IS IN JIRA: link id %s" % ", ".join(backwards))
            raise Backwards("link %d: THE LINK READS BACKWARDS, AND IT IS IN JIRA NOW. Asked for: %s. What Jira now holds is link id %s: %s %s %s.\n"
                            "  1. Remove link id %s by hand in Jira: open either item, find the link, and delete it.\n"
                            "  2. Do not run this workflow again. It put the two items in Jira's slots the wrong way round, and it has to be "
                            "corrected by whoever maintains it before it is used.\n"
                            "  Links this run made the RIGHT way round before it stopped: %s. Links not sent: %s"
                            % (want["n"], want["sentence"], ", ".join(backwards), target["key"], want["type"]["outward"], source["key"], ", ".join(backwards),
                               ", ".join("link %d (link id %s)" % (e["n"], e["link_id"]) for e in result["links"] if e["status"] == "written") or "none",
                               ", ".join("link %d" % e["n"] for e in result["links"] if e["status"] == "not sent") or "none"))
        if answered is not None and answered not in (200, 201):
            words = jira_said(body)
            if words:
                say("  Jira's own words, which are not this workflow's: %s" % json.dumps(words), "  Jira's own words were shown on screen and are not saved: %d characters." % len(words))
            if answered in REFUSALS and not new[0] and not new[1]:
                stop_batch(written_file, result, entry, "Jira refused it (%d) and nothing was written" % answered)
                raise NotWritten("link %d (%s): Jira answered %d to the write, and read back afterwards neither item shows the link, so it was not "
                                 "written%s%s" % (want["n"], want["sentence"], answered,
                                                  ". A new link the OPPOSITE way round is there (link id %s). Jira refused this write, so it is someone else's" % ", ".join(backwards) if backwards else "",
                                                  written_so_far(result)))
            stop_batch(written_file, result, entry, "sent, and Jira answered %d" % answered)
            raise NeedsLooking("link %d (%s): Jira answered %d to the write. Read back afterwards, the items show %d and %d new links of this kind%s. "
                               "IT IS NOT KNOWN whether it was written. Preview again in a minute: a link that exists will be found%s"
                               % (want["n"], want["sentence"], answered, len(new[0]), len(new[1]),
                                  ", and a new link the OPPOSITE way round (link id %s), which may be someone else's" % ", ".join(backwards) if backwards else "", written_so_far(result)))
        if len(new[0]) != 1 or new[0] != new[1]:
            stop_batch(written_file, result, entry, "sent, and read back as %d and %d new links" % (len(new[0]), len(new[1])))
            raise NeedsLooking("link %d (%s): the write was sent%s, and read back afterwards the two items show %d and %d new links of this kind where one "
                               "on each was wanted%s. Preview again in a minute: a link that exists will be found%s"
                               % (want["n"], want["sentence"], " and Jira answered %d" % answered if answered else " and no answer came", len(new[0]), len(new[1]),
                                  " (link ids %s)" % ", ".join(sorted(set(new[0] + new[1]))) if new[0] or new[1] else "", written_so_far(result)))
        link_id = new[0][0]
        entry.update({"status": "written", "link_id": link_id, "written_at": stamp(now_utc())})
        save_json(written_file, result)        # kept at once, so that the new link's id is not lost
        say("  WRITTEN to Jira: link id %s.%s" % (link_id, " Jira answered %d." % answered if answered else " No answer came to the write; the link was found by reading both items."))
        say("  (It is the one new link of this kind on both items. Jira's answer to a write does not name the link, so this is found by reading.)")
        say("  Read back from Jira after the write:")
        checks = read_back(conn, want, link_id, source, target)
        for what, ok in checks:
            say("    %s: %s" % (what, "yes" if ok else "NO"))
        entry["read_back"] = [[what, ok] for what, ok in checks]
        save_json(written_file, result)
        if not all(ok for _, ok in checks):
            raise NeedsLooking("link %d (%s) was written as link id %s, and it does not read back as asked. See the lines marked NO%s"
                               % (want["n"], want["sentence"], link_id, written_so_far(result)))

    saved["state"] = "written"
    save_json(preview_file, saved)
    say("")
    say("ALL DONE: %s written, %d already there." % (plural(len(to_create), "link"), len(proposal["links"]) - len(to_create)))
    finish(args, conn, result)
    say("")
    requests_line(conn)
    return 0


def stop_batch(path, result, entry, status):
    entry["status"] = status
    save_json(path, result)


def written_so_far(result):
    done = ["link %d (link id %s)" % (e["n"], e["link_id"]) for e in result["links"] if e["status"] == "written"]
    left = ["link %d" % e["n"] for e in result["links"] if e["status"] == "not sent"]
    return ". Written in this run before it stopped: %s. Not sent: %s" % (", ".join(done) or "none", ", ".join(left) or "none")


def result_lines(result):
    lines = ["Jira site: %s, site fingerprint %s" % (SITE_MARK, result["site_fingerprint"]),
             "Request: %s (file sha256 %s)" % (result["source"], result["source_sha"]),
             "Confirmed by: %s, at %s" % (result["confirmed_by"], result["confirmed_at"]),
             "Preview: fingerprint %s, made %s" % (result["fingerprint"][:12], result["preview_made_at"])]
    for entry in result["links"]:
        source, target = entry["source"], entry["target"]
        lines += ["Link %d. Issue keys: %s and %s" % (entry["n"], source["key"], target["key"]),
                  "Link %d. In words: %s. From the other item: %s" % (entry["n"], entry["sentence"], entry["other_side"]),
                  "Link %d. Identifier of what was created: Jira issue link id %s. Status: %s" % (entry["n"], entry["link_id"] or "none", entry["status"]),
                  "Link %d. Link type: %s (link type id %s)" % (entry["n"], quoted(entry["type"]["name"]), entry["type"]["id"]),
                  "Link %d. Items by issue id: %s is %s, %s is %s" % (entry["n"], source["key"], source["id"], target["key"], target["id"]),
                  "Link %d. Target project%s: %s, on the sandbox allowlist" % (entry["n"], "" if source["project_id"] == target["project_id"] else "s",
                                                                              " and ".join(sorted(set("%s (project id %s)" % (e["project_key"], e["project_id"]) for e in (source, target))))),
                  "Link %d. Written at: %s" % (entry["n"], entry["written_at"] or "not written by this run"),
                  "Link %d. Read back from both items after the write: %s" % (entry["n"], "as asked: the right type and the right way round on each" if entry["read_back"] and all(ok for _, ok in entry["read_back"])
                                                                               else ("not read back by this run" if not entry["read_back"] else "NOT as asked. See the run's output")),
                  "Link %d. To reverse: remove link id %s in Jira, by hand. This workflow does not remove links" % (entry["n"], entry["link_id"] or "none")]
    return lines


def finish(args, conn, result):
    lines = result_lines(result)
    say("")
    say("RESULT RECORD")
    for line in lines:
        say("  " + line)
    if getattr(args, "result", None):
        text = "\n".join(["# Result record: links created between Jira items", ""] + ["- " + line for line in lines]) + "\n"
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


# ---------------------------------------------------------------- check


def cmd_check(args, conn):
    code = (args.fingerprint or "").strip().lower()
    if len(code) != 12 or any(ch not in "0123456789abcdef" for ch in code):
        raise Refused("a fingerprint is 12 characters, each 0 to 9 or a to f")
    try:
        with open(os.path.join(args.state, "written", code + ".json"), encoding="utf-8") as f:
            result = json.load(f)
        entries = [(e, {"n": e["n"], "type": e["type"], "symmetric": e["symmetric"], "source": e["source"], "target": e["target"], "sentence": e["sentence"]}) for e in result["links"]]
        site = result["site_fingerprint"]
    except FileNotFoundError:
        raise Refused("there is no record of a write for the fingerprint %s" % code)
    except (ValueError, KeyError, TypeError):
        raise Refused("the record of the write %s cannot be read" % code)
    if site_fingerprint(conn.host) != site:
        raise Refused("this is not the Jira site the links were written to")
    say("LINK CHECK for the write of preview %s. Nothing is written by this command." % code)
    say("")
    say("Jira site:  https://%s  (site fingerprint %s)" % (conn.host, site))
    good = True
    for entry, want in entries:
        say("")
        say("LINK %d: %s. From the other item: %s." % (entry["n"], entry["sentence"], entry["other_side"]))
        if not entry["link_id"]:
            say("  No link id is recorded for it (%s), so there is nothing to read back." % entry["status"])
            good = False
            continue
        source, target, _, backwards = look(conn, want, set())
        for what, ok in read_back(conn, want, entry["link_id"], source, target):
            say("  %s: %s" % (what, "yes" if ok else "NO"))
            good = good and ok
        if backwards:
            say("  A LINK THE OPPOSITE WAY ROUND is also there: link id %s." % ", ".join(backwards))
            good = False
    say("")
    requests_line(conn)
    say("")
    say("FOUND: every link is there, with the right type and the right way round, on both items." if good else "NOT AS ASKED: see the lines marked NO above.")
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
            return {"preview": cmd_preview, "confirm": cmd_confirm, "check": cmd_check}[args.command](args, conn)
        except NotWritten as refusal:
            say("")
            say("REFUSED: %s." % refusal)
            return 1
        except Refused as refusal:
            if conn.posted():
                raise NeedsLooking("a write was sent, and a step after it could not be done: %s" % refusal)
            return refused(refusal)
        except NeedsLooking:
            raise
        except Exception as failure:  # nothing may hide what was already sent
            if conn.posted():
                raise NeedsLooking("a write was sent, and the program then failed (%s). A link may have been created" % type(failure).__name__)
            return refused("the program failed before anything was sent (%s)" % type(failure).__name__)
    except Backwards as problem:
        say("")
        say("A PERSON NEEDS TO LOOK: %s." % problem)
        return 2
    except NeedsLooking as problem:
        say("")
        say("A PERSON NEEDS TO LOOK: %s." % problem)
        if args.command == "confirm":
            say("Do not confirm again with this fingerprint. Preview again: it reads both items and finds what is there.")
        return 2


def person_present(stream):
    """True if the run was started from a terminal. It keeps out a program that has none. It does not prove who typed."""
    try:
        return bool(stream.isatty())
    except (AttributeError, ValueError):
        return False


def main(argv=None):
    parser = argparse.ArgumentParser(description="Preview, then confirm, links between Jira items. Then check them from both items.")
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("preview", "confirm", "check"):
        sub = commands.add_parser(command)
        sub.add_argument("--source", choices=("live", "fake"), required=True)
        sub.add_argument("--state", required=True, help="the folder where previews and write records are kept")
        sub.add_argument("--log", help="also save the output here, with the site's address and the items' titles removed")
        if command != "check":
            sub.add_argument("--request", required=True, help="the request file")
            sub.add_argument("--allowlist", required=True, help="the sandbox allowlist")
        if command != "preview":
            sub.add_argument("--fingerprint")
        if command == "confirm":
            sub.add_argument("--confirmed-by")
            sub.add_argument("--result", help="save the result record here, as Markdown")
            sub.add_argument("--pretend-minutes-later", type=whole_number, default=0, metavar="N", help="tests only")
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
              % (" A WRITE WAS SENT TO JIRA in this run. Preview again before doing anything else: it finds what is there." if wrote else ""))
        return 2 if wrote else 1
    print(text)
    try:
        write_pending()
    except OSError:
        print("\nTHE RESULT RECORD COULD NOT BE SAVED where --result said. What the output above says stands.")
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
