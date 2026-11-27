#!/usr/bin/env python3
"""Reads the items of one Jira project and keeps the SHAPE of the work: which item is under which. IT ONLY READS JIRA.

    hierarchy.py build --source live|fake --project KEY --out-dir DIR --name NAME [--state DIR] [--log FILE]
    hierarchy.py tree  --records FILE

`build` reads the project and writes two files in DIR, and no others (with --source fake the made-up Jira also saves
its own file, in its own folder):

    NAME.json    the records: for each item its identifier, key, type, and its PARENT'S IDENTIFIER
    NAME.md      the same as an index, and the tree built from it, laid out to be read

`tree` contacts nothing. It builds the tree again from a records file and prints it with its checksum.

AN ITEM IS KNOWN BY JIRA'S INTERNAL NUMBER, NOT BY ITS KEY AND NEVER BY ITS TITLE. The key (DEMO-7) changes when an
item is moved to another project. The number (30007) does not. Each record holds the parent's number. The tree is
built from the numbers alone. Keys are kept beside them for reading. Titles are not asked for and not kept.

A MOVED ITEM. Because the tree is built fresh from each item's own parent number, an item that was moved in Jira is
under its new parent and nowhere else. It cannot be in two places: a record has one parent number. `build` also
compares with the records already on disk, by number, and prints what moved: "was under X, is under Y". An item
whose key changed and whose number did not is printed as the same item under a new key.

A PARENT THAT WAS NOT RETRIEVED. Jira names an item's parent even when that parent is in another project or is not
visible to the account. Such an item is KEPT, with the parent's number, and is listed as an UNRESOLVED LINK. It is
not dropped and is not shown as an item with no parent. In the tree it stands under a line that names the parent
that is missing. This tool does not go and fetch the parent: it reads one project.

A LOOP OR AN ITEM THAT IS ITS OWN PARENT REJECTS THE WHOLE BUILD. Nothing is written, and every item in the loop is
named. So does one number or one key held by two items. A tree with a loop cut out of it would look like a whole tree.
If records from an earlier build are on disk they are left as they were, and the output says they are older.

THE SAME INPUT GIVES THE SAME FILES, BYTE FOR BYTE. Items are ordered by number, children by number, and no time is
written into either file. The output prints a checksum of the tree, so two builds can be compared by eye.

NOTHING IS WRITTEN UNLESS THE WHOLE PROJECT WAS READ, TWICE, AND THE TWO READINGS AGREE. The items come in pages. If
someone moves an item while the pages are read, one reading can miss it. The project is read a second time and the
two are compared, item by item and parent by parent. If they differ the build is REFUSED and says to run it again.
Jira is also asked how many items the project has, before the readings and after. If that number is not the number
of items read, the build is REFUSED: an item left out would turn its children into unresolved links without a word.

ESTIMATES. Each item's own original estimate (Jira's standard field) is kept, in seconds. The tree shows each item's
own and the total of everything beneath it. An item with no estimate is "no estimate", not zero, and each total says
how many items in it had none. Items under a parent that was not retrieved are totalled apart and are added to no
retrieved parent. The total is this tool's own sum. If a team already writes the sum of the children into the parent
by hand, this would count it twice, and cannot know.

LINKS THAT ARE NOT PARENT LINKS ("blocks", "relates to") are listed in their own section, by number, each once.
They are never used to build the tree.

PEOPLE AND TITLES ARE NOT KEPT. Type names and link names are other people's text: each is cut to 40 characters and
every character that is not a letter or digit, or one of a few marks, is replaced by a question mark.

REQUESTS. Two kinds, each built in one place:
    GET  /rest/api/3/search/jql                    the pages of items
    POST /rest/api/3/search/approximate-count      the count. Jira takes this question as a POST. It changes nothing
There is no code path that builds any other request. What the output says about the requests is read back from each
request as it was built.

--state DIR is for the made-up Jira (--source fake): the folder that holds it.
--log FILE saves the output with the site's address replaced by a marker.

For a live build the connection comes from the environment variables JIRA_BASE_URL, JIRA_EMAIL and JIRA_API_TOKEN. None
is stored. The output is searched for the token, the email address and their encoded form before it is shown.

Exit codes: 0 the tree was built (and written, by `build`); 1 REFUSED: something could not be read, and nothing was
written; 2 REJECTED: the items do not make a tree (a loop, a self-parent, a number or key used twice), nothing written.
"""
import argparse
import base64
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

FORMAT = "jira-hierarchy/1"
REF = re.compile(r"([A-Za-z][A-Za-z0-9_]{0,30})-[0-9]{1,9}")
PROJECT = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,30}")
NAME = re.compile(r"[a-z][a-z0-9-]{0,60}")
SITE_MARK = "[site address removed]"
SEARCH_PATH = "/rest/api/3/search/jql"
COUNT_PATH = "/rest/api/3/search/approximate-count"
FIELDS = "issuetype,parent,timeoriginalestimate,issuelinks"            # no summary: titles are not asked for
PAGE = 100
MAX_PAGES = 200
UNSEEN = re.compile("[\\x00-\\x1f\\x7f-\\xa0\\u00ad\\u034f\\u061c\\u115f\\u1160\\u200b-\\u200f\\u2028\\u2029\\u202a-\\u202e\\u2060-\\u2069\\u2800\\u3164\\ufeff\\ud800-\\udfff\\U000e0000-\\U000e007f]")
KEPT_MARKS = " _()'-"            # no dot, slash or colon: a name must not come out looking like an address
PAGE_HEADING = "# Hierarchy · project "
LOG_STARTS = ("Project:", "REFUSED:", "REJECTED:", "Records:", "STOPPED:")
FOUR = ("epic", "story", "task", "subtask")

LINES = []


class Refused(Exception):
    """Something could not be read, or a place could not be written. Nothing was written. The message is the reason."""


class WriteFailed(Refused):
    """A write failed. The message says what state the files are in."""


class Rejected(Exception):
    """The items were read and do not make a tree. Nothing was written. `reasons` is a list of sentences."""

    def __init__(self, reasons):
        Exception.__init__(self, "; ".join(reasons))
        self.reasons = reasons


def say(text=""):
    LINES.append(text)


def clean(value, limit=40):
    if not isinstance(value, str) or not value.strip():
        return None
    return "".join(ch if (ch.isalnum() or ch in KEPT_MARKS) and not UNSEEN.match(ch) else "?" for ch in value)[:limit].strip() or None


def shown(text, limit=80):
    return "".join("?" if UNSEEN.match(ch) else ch for ch in str(text))[:limit]


def ident(value):
    """Jira's internal number, as text, written the one way a number is written: no sign, no leading zero."""
    return isinstance(value, str) and re.fullmatch(r"0|[1-9][0-9]{0,19}", value) is not None


def file_sum(path):
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except FileNotFoundError:
        return None


def same_file(a, b):
    """Whether two paths are one file: by the disk's own answer if both exist, and by the paths, compared without
    regard to capitals, if not."""
    try:
        if os.path.exists(a) and os.path.exists(b):
            return os.path.samefile(a, b)
    except OSError:
        pass
    return os.path.realpath(a).casefold() == os.path.realpath(b).casefold()


def hours(seconds):
    return "no estimate" if seconds is None else ("%.2f" % (seconds / 3600.0)).rstrip("0").rstrip(".") + " h"


def total_text(seconds, missing, count):
    """A total over `count` items, `missing` of which have no estimate. A total of nothing is not shown as 0 h."""
    if count == 0:
        return "no items"
    if missing == count:
        return "no estimate on any of the %d" % count
    return hours(seconds) + ("" if not missing else " (%d of the %d without an estimate)" % (missing, count))


# ---------------------------------------------------------------- the connection: GET only, one path


class Connection:
    """Every request goes through `get` or `count` and is written down. There is no other method."""

    def __init__(self, get, post, host):
        self._get, self._post, self.host = get, post, host
        self.sent = []

    def _ask(self, built_as, call, path, argument):
        try:
            answer = call(path, argument)
        except (OSError, TimeoutError) as err:
            self.sent.append(("?", path))
            raise Refused("Jira could not be reached (%s)" % type(getattr(err, "reason", err)).__name__)
        # A live answer carries, as its 4th part, the method of the request as it was built.
        self.sent.append((answer[3] if len(answer) == 4 else built_as + " (the made-up Jira)", path))
        return answer[0], answer[2]

    def get(self, params):
        return self._ask("GET", self._get, SEARCH_PATH, params)

    def count(self, jql):
        return self._ask("POST", self._post, COUNT_PATH, {"jql": jql})

    def only_the_two_reads(self):
        return all((method.split(" ")[0], path) in (("GET", SEARCH_PATH), ("POST", COUNT_PATH)) for method, path in self.sent)


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

    def get(path, params):
        if path != SEARCH_PATH:
            raise Refused("this tool sends GET to one path only, the search")
        return send(urllib.request.Request(base + path + "?" + urllib.parse.urlencode(params), method="GET"))

    def post(path, body):
        if path != COUNT_PATH or set(body) != {"jql"}:
            raise Refused("this tool sends POST to one path only, the count, with the query and nothing else")
        request = urllib.request.Request(base + path, data=json.dumps(body).encode("utf-8"), method="POST")
        request.add_header("Content-Type", "application/json")
        return send(request)

    def send(request):
        request.add_header("Authorization", "Basic " + encoded)
        request.add_header("Accept", "application/json")
        try:
            with opener.open(request, timeout=30) as response:
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
        return status, headers, parsed, request.get_method()

    return Connection(get, post, host), [token, email, encoded]


def site_fingerprint(host):
    return hashlib.sha256(host.lower().encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------- reading Jira


def one_item(raw, project):
    """What is kept of one item, and its links. Refuses an item that cannot be read: a guess here would be a wrong tree."""
    fields = raw.get("fields") if isinstance(raw, dict) else None
    key, number = (raw.get("key"), raw.get("id")) if isinstance(raw, dict) else (None, None)
    found = REF.fullmatch(key) if isinstance(key, str) else None
    if not found or not ident(number) or not isinstance(fields, dict):
        raise Refused("Jira sent an item that could not be read")
    if found.group(1).upper() != project:
        raise Refused("Jira sent an item of another project (%s) in answer to a search of %s" % (found.group(1).upper(), project))
    kind = fields.get("issuetype") if isinstance(fields.get("issuetype"), dict) else {}
    name = clean(kind.get("name"))
    if name is None:
        raise Refused("Jira sent the item %s without its type" % key.upper())
    level = kind.get("hierarchyLevel")
    level = level if isinstance(level, int) and not isinstance(level, bool) and -5 <= level <= 20 else None
    parent = fields.get("parent")
    parent_id = parent_key = None
    if parent is not None:
        if not isinstance(parent, dict) or not ident(parent.get("id")):
            raise Refused("Jira sent the item %s with a parent that has no number that can be used. It is not guessed at" % key.upper())
        parent_id = parent["id"]
        parent_key = parent["key"].upper() if isinstance(parent.get("key"), str) and REF.fullmatch(parent["key"]) else None
    estimate = fields.get("timeoriginalestimate")
    if estimate is not None and (type(estimate) is not int or estimate < 0 or estimate > 10 ** 9):
        raise Refused("Jira sent the item %s with an estimate that is not a number of seconds" % key.upper())
    links = []
    for link in fields.get("issuelinks") or []:
        if not isinstance(link, dict) or not ident(link.get("id")) or not isinstance(link.get("type"), dict):
            raise Refused("Jira sent the item %s with a link that could not be read" % key.upper())
        outward = "outwardIssue" in link
        if outward and "inwardIssue" in link:
            raise Refused("Jira sent the item %s with a link that names two other items" % key.upper())
        other = link.get("outwardIssue" if outward else "inwardIssue")
        if not isinstance(other, dict) or not ident(other.get("id")):
            raise Refused("Jira sent the item %s with a link that names no other item" % key.upper())
        other_key = other["key"].upper() if isinstance(other.get("key"), str) and REF.fullmatch(other["key"]) else None
        mine, theirs = (number, key.upper()), (other["id"], other_key)
        source, target = (mine, theirs) if outward else (theirs, mine)
        links.append({"id": link["id"], "type": clean(link["type"].get("name")) or "a link with no name", "phrase": clean(link["type"].get("outward")) or "is linked to",
                      "from_id": source[0], "from_key": source[1], "to_id": target[0], "to_key": target[1]})
    return {"id": number, "key": key.upper(), "type": name, "level": level, "subtask": kind.get("subtask") is True,
            "parent_id": parent_id, "parent_key": parent_key, "estimate_seconds": estimate}, links


def read_once(conn, project):
    """Every item of the project, page by page. Refuses unless every page is readable, no item comes twice, and the
    last page says it is the last."""
    items, links, seen, marker, pages = [], {}, set(), None, 0
    while True:
        params = {"jql": 'project = "%s" ORDER BY key ASC' % project, "fields": FIELDS, "maxResults": PAGE}
        if marker:
            params["nextPageToken"] = marker
        status, body = conn.get(params)
        if status == 401:
            raise Refused("Jira rejected the credentials (401). Check JIRA_EMAIL and JIRA_API_TOKEN")
        page = body.get("issues") if status == 200 and isinstance(body, dict) else None
        if not isinstance(page, list):
            raise Refused("Jira did not answer with a page of items (status %d)" % status)
        following = body.get("nextPageToken")
        if following is not None and (not isinstance(following, str) or not following):
            raise Refused("Jira's marker for the next page could not be used")
        if (not page and following) or (following and following == marker):
            raise Refused("Jira sent an empty page and said there was more, or gave back the marker it was asked with")
        for raw in page:
            item, its_links = one_item(raw, project)
            marks = {"number " + item["id"], "key " + item["key"]}
            if marks & seen:
                raise Refused("the item %s came twice in the pages, so another may have been pushed out of them" % item["key"])
            seen |= marks
            items.append(item)
            for link in its_links:
                if links.setdefault(link["id"], link) != link:
                    raise Refused("Jira described the link %s differently at its two ends, so it is not known what it joins" % link["id"])
        pages += 1
        if not following:
            if body.get("isLast", True) is not True:
                raise Refused("Jira did not say the last page was the last, and gave no way to ask for another")
            return items, [links[i] for i in sorted(links, key=int)], pages
        if pages >= MAX_PAGES:
            raise Refused("the project has more than %d pages of items, which is more than this tool reads" % MAX_PAGES)
        marker = following


def ask_count(conn, project):
    status, body = conn.count('project = "%s" ORDER BY key ASC' % project)
    if status == 401:
        raise Refused("Jira rejected the credentials (401). Check JIRA_EMAIL and JIRA_API_TOKEN")
    count = body.get("count") if status == 200 and isinstance(body, dict) else None
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        raise Refused("Jira did not say how many items the project has (status %d), so what was read cannot be checked against it" % status)
    return count


def read_project(conn, project):
    """The project, read twice, with Jira's own count taken before and after. Refuses unless the two readings agree,
    item by item and parent by parent, and both counts are the number of items read."""
    before = ask_count(conn, project)
    first, links, pages = read_once(conn, project)
    second, links_again, _ = read_once(conn, project)
    after = ask_count(conn, project)
    if sorted(json.dumps(i, sort_keys=True) for i in first) != sorted(json.dumps(i, sort_keys=True) for i in second) or links != links_again:
        raise Refused("the project was read twice and the two readings differ: something was changed in Jira while it was being read. Run it again")
    if not before == after == len(first):
        raise Refused("Jira says the project has %d items (%d when asked again) and %d were read. An item left out would turn its children into unresolved links" % (before, after, len(first)))
    return sorted(first, key=lambda i: int(i["id"])), links, pages


# ---------------------------------------------------------------- the tree


def check_shape(items):
    """Raises Rejected unless the items can make a tree: no number or key twice, no item its own parent, no loop."""
    reasons = []
    for what, field in (("number", "id"), ("key", "key")):
        held = {}
        for i in items:
            held[i[field]] = held.get(i[field], 0) + 1
        for value in sorted(v for v, n in held.items() if n > 1):
            reasons.append("the %s %s is held by %d items" % (what, value, held[value]))
    by_id = {i["id"]: i for i in items}
    name = lambda number: "%s [%s]" % (by_id[number]["key"], number)       # noqa: E731
    for item in items:
        if item["parent_id"] == item["id"]:
            reasons.append("%s is its own parent" % name(item["id"]))
    loops, settled = set(), set()            # settled: numbers already followed to the top, or into a loop already found
    for item in items:
        path, on_path, at = [], set(), item["id"]
        while at in by_id and at not in on_path and at not in settled:
            path.append(at)
            on_path.add(at)
            at = by_id[at]["parent_id"]
        settled |= on_path
        if at in on_path and len(path[path.index(at):]) > 1:
            loop = path[path.index(at):]
            start = loop.index(min(loop, key=int))          # the same loop, found from any of its items, is written the same way
            loops.add(tuple(loop[start:] + loop[:start]))
    for loop in sorted(loops):
        reasons.append("a loop: %s, which is under %s" % (", which is under ".join(name(number) for number in loop), name(loop[0])))
    if reasons:
        raise Rejected(reasons)


def build_tree(items):
    """The tree, from numbers alone. Returns a dictionary:
        children     {number: [numbers of its children, in order]}
        roots        numbers of items with no parent, in order
        unresolved   {missing parent's number: [numbers of the items that name it, in order]}
        total        {number: (seconds of the item and all beneath it, how many of those have no estimate, how many items)}
    """
    check_shape(items)
    by_id = {i["id"]: i for i in items}
    children, roots, unresolved = {i["id"]: [] for i in items}, [], {}
    for item in sorted(items, key=lambda i: int(i["id"])):
        if item["parent_id"] is None:
            roots.append(item["id"])
        elif item["parent_id"] in by_id:
            children[item["parent_id"]].append(item["id"])
        else:
            unresolved.setdefault(item["parent_id"], []).append(item["id"])
    # Each item's total is its own and its children's. Worked from the bottom up without one function calling itself, so
    # that a chain of any length is a tree like any other.
    order, stack = [], roots + [n for group in unresolved.values() for n in group]
    while stack:
        number = stack.pop()
        order.append(number)
        stack.extend(children[number])
    total = {}
    for number in reversed(order):
        seconds, missing, count = by_id[number]["estimate_seconds"] or 0, 1 if by_id[number]["estimate_seconds"] is None else 0, 1
        for child in children[number]:
            s, m, c = total[child]
            seconds, missing, count = seconds + s, missing + m, count + c
        total[number] = (seconds, missing, count)
    return {"children": children, "roots": roots, "unresolved": unresolved, "total": total}


def tree_lines(items, tree):
    """The tree as lines of text. The same items give the same lines."""
    by_id = {i["id"]: i for i in items}
    out = []

    def line(top, start):
        stack = [(top, start)]
        while stack:
            number, depth = stack.pop()
            item = by_id[number]
            seconds, missing, count = tree["total"][number]
            beneath = "" if count == 1 else "; with all %d beneath: %s" % (count - 1, total_text(seconds, missing, count))
            out.append("%s%s [%s] %s. Own estimate: %s%s" % ("  " * depth, item["key"], number, item["type"], hours(item["estimate_seconds"]), beneath))
            stack.extend((child, depth + 1) for child in reversed(tree["children"][number]))
    for number in tree["roots"]:
        line(number, 0)
    for parent in sorted(tree["unresolved"], key=int):
        named = sorted(set(by_id[n]["parent_key"] or "no key given" for n in tree["unresolved"][parent]))
        out.append("PARENT NOT RETRIEVED: number %s (Jira names it %s). It is not in what was read. Under it:" % (parent, ", ".join(named)))
        for number in tree["unresolved"][parent]:
            line(number, 1)
    return out


def tree_checksum(lines):
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()[:16]


def odd_shapes(items):
    """Shapes Jira does not usually allow: a child whose level is not below its parent's, and a subtask for which Jira
    names no parent. Reported, not rejected: they are what Jira sent."""
    by_id = {i["id"]: i for i in items}
    out = []
    for item in items:
        if item["parent_id"] is None and (item["subtask"] or item["level"] == -1):
            out.append("%s [%s] is a %s, and Jira names no parent for it. It is shown with no parent because none was given, not because it is known to have none" % (item["key"], item["id"], item["type"]))
        parent = by_id.get(item["parent_id"])
        if parent and item["level"] is not None and parent["level"] is not None and item["level"] >= parent["level"]:
            out.append("%s [%s], a %s, is under %s [%s], a %s" % (item["key"], item["id"], item["type"], parent["key"], parent["id"], parent["type"]))
    return out


def kinds_present(items):
    """Which of epic, story, task and subtask are among the items. An epic and a subtask are known by Jira's own mark
    for them where it gives one, and by the type's name otherwise. A story and a task are known by name."""
    present = set()
    for item in items:
        name = item["type"].casefold()
        marked = item["level"] is not None           # where Jira gives its own mark, the mark decides, not the name
        if item["level"] == 1 or (not marked and name == "epic"):
            present.add("epic")
        elif item["subtask"] or item["level"] == -1 or (not marked and name in ("subtask", "sub-task")):
            present.add("subtask")
        elif name in ("story", "task"):
            present.add(name)
    return [kind for kind in FOUR if kind in present]


def render(records, tree, lines):
    items = records["items"]
    by_id = {i["id"]: i for i in items}
    out = [PAGE_HEADING + records["project"], "",
           "**Written by a tool. Do not edit this file: the next build writes it again from `%s`.**" % records["files"]["records"], "",
           "Source: %s." % ("the made-up Jira; every item here is made up" if records["source"] == "fake" else "a real Jira, site fingerprint %s" % records["site_fingerprint"]),
           "An item is known by Jira's internal number. Its parent is recorded by the parent's number. The key is beside each for reading.",
           "No title and no person is kept.", "",
           "## Index", "",
           "| Identifier | Key | Type | Parent identifier | Parent key | Parent retrieved | Own estimate | With all beneath |", "|---|---|---|---|---|---|---|---|"]
    for item in items:
        seconds, missing, count = tree["total"][item["id"]]
        beneath = total_text(seconds, missing, count) if count > 1 else "nothing beneath"
        out.append("| %s | %s | `%s` | %s | %s | %s | %s | %s |" % (
            item["id"], item["key"], item["type"], item["parent_id"] or "none", item["parent_key"] or ("none" if item["parent_id"] is None else "no key given"),
            "no parent" if item["parent_id"] is None else "yes" if item["parent_id"] in by_id else "**NO: unresolved link**", hours(item["estimate_seconds"]), beneath))
    counts = {}
    for item in items:
        counts[item["type"]] = counts.get(item["type"], 0) + 1
    out += ["", "%d items: %s." % (len(items), ", ".join("%d %s" % (counts[name], name) for name in sorted(counts))), "",
            "## The tree", "", "Built from the identifiers in the index, and from nothing else. Checksum of the tree: `%s`." % tree_checksum(lines), "", "~~~text"] + lines + ["~~~", "",
            "## Unresolved links", ""]
    if not tree["unresolved"]:
        out += ["None. Every parent named is among the items read.", ""]
    else:
        out += ["Jira names a parent for each of these, and that parent is not among the items read: it is in another project, or the account",
                "that reads cannot see it. The item is kept, under its parent's identifier. It is not an item without a parent.", "",
                "| Identifier | Key | Type | Parent identifier, not retrieved | Parent key, as Jira names it |", "|---|---|---|---|---|"]
        for parent in sorted(tree["unresolved"], key=int):
            for number in tree["unresolved"][parent]:
                item = by_id[number]
                out.append("| %s | %s | `%s` | %s | %s |" % (number, item["key"], item["type"], parent, item["parent_key"] or "no key given"))
        out.append("")
    odd = odd_shapes(items)
    if odd:
        out += ["## Shapes Jira does not usually allow", "", "Kept as Jira gave them, and pointed out:", ""] + ["- %s" % line for line in odd] + [""]
    out += ["## Links that are not parent links", "", "Listed by identifier, each once. **They are not used to build the tree.**", ""]
    if not records["links"]:
        out += ["None.", ""]
    else:
        out += ["| Link | From | | To | To retrieved |", "|---|---|---|---|---|"]
        for link in records["links"]:
            out.append("| %s | %s [%s] | `%s` | %s [%s] | %s |" % (link["id"], link["from_key"] or "no key given", link["from_id"], link["phrase"], link["to_key"] or "no key given", link["to_id"],
                                                               "yes" if link["to_id"] in by_id and link["from_id"] in by_id else "one end is outside what was read"))
        out.append("")
    return "\n".join(out)


def good_item(i):
    """Whether a record of an item is one this tool would have written: every field there, and of the shape it writes."""
    return (isinstance(i, dict) and set(i) == {"id", "key", "type", "level", "subtask", "parent_id", "parent_key", "estimate_seconds"}
            and ident(i["id"]) and isinstance(i["key"], str) and REF.fullmatch(i["key"]) is not None and i["key"] == i["key"].upper()
            and isinstance(i["type"], str) and clean(i["type"]) == i["type"]
            and (i["level"] is None or (type(i["level"]) is int and -5 <= i["level"] <= 20)) and type(i["subtask"]) is bool
            and (i["parent_id"] is None or ident(i["parent_id"]))
            and (i["parent_key"] is None or (isinstance(i["parent_key"], str) and REF.fullmatch(i["parent_key"]) is not None and i["parent_id"] is not None))
            and (i["estimate_seconds"] is None or (type(i["estimate_seconds"]) is int and 0 <= i["estimate_seconds"] <= 10 ** 9)))


def good_link(link):
    return (isinstance(link, dict) and set(link) == {"id", "type", "phrase", "from_id", "from_key", "to_id", "to_key"} and ident(link["id"]) and ident(link["from_id"]) and ident(link["to_id"])
            and all(isinstance(link[k], str) and clean(link[k]) == link[k] for k in ("type", "phrase"))
            and all(link[k] is None or (isinstance(link[k], str) and REF.fullmatch(link[k]) is not None) for k in ("from_key", "to_key")))


def load_records(path, must_exist=False):
    if os.path.lexists(path) and (not os.path.isfile(path) or os.path.getsize(path) > 50 * 1024 * 1024):
        raise Refused("the records file is not a plain file, or is far larger than any this tool writes")
    try:
        with open(path, encoding="utf-8") as f:
            raw = f.read()
    except FileNotFoundError:
        if must_exist:
            raise Refused("there is no records file at that place")
        return None
    except (OSError, UnicodeDecodeError):
        raise Refused("the records file could not be read")
    try:
        records = json.loads(raw)
    except ValueError:
        records = None
    good = (isinstance(records, dict) and records.get("format") == FORMAT and isinstance(records.get("items"), list) and isinstance(records.get("links"), list)
            and isinstance(records.get("project"), str) and PROJECT.fullmatch(records["project"]) is not None
            and all(good_item(i) for i in records["items"]) and all(good_link(link) for link in records["links"]))
    if not good:
        raise Refused("the records file is not one this tool wrote, or has been changed into something it cannot read. It is left as it is")
    return records


def write_file(path, text):
    handle, temporary = tempfile.mkstemp(prefix=".hierarchy-", suffix=".tmp", dir=os.path.dirname(path))
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


def places(out_dir, name):
    if not NAME.fullmatch(name):
        raise Refused("--name is lower-case letters, digits and dashes, starting with a letter")
    folder = os.path.realpath(out_dir)
    if not os.path.isdir(folder):
        raise Refused("--out-dir is not a folder that exists")
    records_path, page_path = os.path.join(folder, name + ".json"), os.path.join(folder, name + ".md")
    for path in (records_path, page_path):
        if os.path.islink(path) or os.path.isdir(path) or (os.path.exists(path) and os.stat(path).st_nlink > 1):
            raise Refused("%s in the folder is a link, a folder, or a file with a second name. This tool writes only a plain file of its own" % os.path.basename(path))
    if os.path.exists(page_path) and not os.path.exists(records_path):       # with records beside it, the pair is this tool's
        with open(page_path, "rb") as f:
            if not f.read(len(PAGE_HEADING.encode("utf-8"))) == PAGE_HEADING.encode("utf-8"):
                raise Refused("a file named %s is already in the folder and it is not a page this tool wrote. It is left as it is. Use another --name" % shown(os.path.basename(page_path)))
    return records_path, page_path


def what_changed(old, items):
    """Compared by number with the records already on disk: (moved, rekeyed, new, gone, retyped), each a list of sentences."""
    before, now = {i["id"]: i for i in old["items"]}, {i["id"]: i for i in items}
    name = lambda i: "%s [%s]" % (i["key"], i["id"])       # noqa: E731
    parent = lambda i: "no parent" if i["parent_id"] is None else "%s [%s]" % (i["parent_key"] or "no key given", i["parent_id"])       # noqa: E731
    moved = ["%s was under %s, and is now under %s" % (name(now[n]), parent(before[n]), parent(now[n])) for n in sorted(now, key=int) if n in before and before[n]["parent_id"] != now[n]["parent_id"]]
    rekeyed = ["the item with the number %s had the key %s and now has %s. It is the same item" % (n, before[n]["key"], now[n]["key"]) for n in sorted(now, key=int) if n in before and before[n]["key"] != now[n]["key"]]
    new = [name(now[n]) for n in sorted(now, key=int) if n not in before]
    gone = [name(before[n]) for n in sorted(before, key=int) if n not in now]
    retyped = ["%s was a %s and is now a %s" % (name(now[n]), before[n]["type"], now[n]["type"]) for n in sorted(now, key=int) if n in before and before[n]["type"] != now[n]["type"]]
    return moved, rekeyed, new, gone, retyped


# ---------------------------------------------------------------- the commands


def say_tree(items, links, tree, lines):
    by_id = {i["id"]: i for i in items}
    counts = {}
    for item in items:
        counts[item["type"]] = counts.get(item["type"], 0) + 1
    say("ITEMS: %d. By type: %s." % (len(items), ", ".join("%d %s" % (counts[name], name) for name in sorted(counts)) or "none"))
    present = kinds_present(items)
    say("Of epic, story, task and subtask: %s." % ("all four are here" if len(present) == 4 else "here are %s; NOT here: %s" % (", ".join(present) or "none", ", ".join(k for k in FOUR if k not in present))))
    if len(present) < 4:
        say("  (An epic and a subtask are known by Jira's own mark for them. A story and a task are known by those two English names.)")
    say("Each item's parent is recorded by the parent's number. Jira names a parent for %d, and names none for %d." % (
        sum(1 for i in items if i["parent_id"] is not None), sum(1 for i in items if i["parent_id"] is None)))
    say("")
    unresolved = [(parent, number) for parent in sorted(tree["unresolved"], key=int) for number in tree["unresolved"][parent]]
    say("UNRESOLVED LINKS: %d." % len(unresolved))
    for parent, number in unresolved:
        say("  %s [%s] names the parent number %s (%s), which is not among the items read. The item is kept, under that number." % (
            by_id[number]["key"], number, parent, by_id[number]["parent_key"] or "no key given"))
    odd = odd_shapes(items)
    if odd:
        say("")
        say("SHAPES JIRA DOES NOT USUALLY ALLOW, kept as given: %d." % len(odd))
        for line in odd:
            say("  %s" % line)
    say("")
    say("THE TREE, built from the numbers alone:")
    for line in lines:
        say("  " + line)
    group = lambda numbers: tuple(sum(tree["total"][n][k] for n in numbers) for k in (0, 1, 2))       # noqa: E731
    in_tree, apart = group(tree["roots"]), group([n for g in tree["unresolved"].values() for n in g])
    say("Estimates, added up by this tool. Under retrieved parents or under none: %s. Under parents not retrieved, added to no one: %s." % (total_text(*in_tree), total_text(*apart)))
    say("Checksum of the tree: %s" % tree_checksum(lines))
    say("")
    say("LINKS THAT ARE NOT PARENT LINKS: %d. Not used to build the tree." % len(links))
    for link in links:
        say("  %s [%s] %s %s [%s]" % (link["from_key"] or "no key given", link["from_id"], link["phrase"], link["to_key"] or "no key given", link["to_id"]))


def say_rejected(rejection, older=None):
    say("REJECTED: these items do not make a tree.")
    for reason in rejection.reasons:
        say("  %s." % reason)
    say("Nothing was written. A tree with the loop cut out of it would look like a whole tree.")
    if older:
        say(older)
    return 2


def cmd_tree(args):
    records = load_records(args.records, must_exist=True)
    say("Records: the file given with --records, %s. Project %s. Nothing is contacted." % (shown(os.path.basename(args.records)), shown(records["project"], 40)))
    say("")
    try:
        tree = build_tree(records["items"])
    except Rejected as rejection:
        return say_rejected(rejection)
    lines = tree_lines(records["items"], tree)
    say_tree(records["items"], records["links"], tree, lines)
    say("")
    say("RESULT: THE TREE WAS BUILT from the records. Nothing was written.")
    return 0


def cmd_build(args, conn, live, secrets=()):
    project = args.project.upper()
    if not PROJECT.fullmatch(args.project):
        raise Refused("--project is a project's key, such as DEMO")
    records_path, page_path = places(args.out_dir, args.name)
    before = (file_sum(records_path), file_sum(page_path))
    old = load_records(records_path)
    source, site = ("live", site_fingerprint(conn.host)) if live else ("fake", None)
    if old is not None and (old.get("project"), old.get("source"), old.get("site_fingerprint")) != (project, source, site):
        raise Refused("the records on disk are of another project, or were made from another Jira. They are left as they are. Use another --name")

    items, links, pages = read_project(conn, project)
    say("Project: %s" % project)
    say("Read from: %s" % ("a real Jira, site fingerprint %s" % site if live else "the made-up Jira. No real Jira was contacted"))
    say("The project was read twice, %d page%s each time, and the two readings agree. Jira's own count, before and after: %d. Items read: %d." % (
        pages, "" if pages == 1 else "s", len(items), len(items)))
    say("")
    older = None if old is None else "The records already on disk are from an earlier build. They were left as they were. THEY ARE NOT THIS BUILD'S."
    try:
        tree = build_tree(items)
    except Rejected as rejection:
        code = say_rejected(rejection, older)
        say_requests(conn)
        return code
    lines = tree_lines(items, tree)
    say_tree(items, links, tree, lines)
    say("")
    if old is None:
        say("COMPARED WITH THE RECORDS ON DISK: there were none. This is the first build.")
    else:
        moved, rekeyed, new, gone, retyped = what_changed(old, items)
        say("COMPARED WITH THE RECORDS ON DISK, by number: %d moved, %d with a new key, %d new, %d no longer returned, %d of another type." % (len(moved), len(rekeyed), len(new), len(gone), len(retyped)))
        for label, group in (("MOVED", moved), ("NEW KEY", rekeyed), ("TYPE", retyped)):
            for sentence in group:
                say("  %s: %s." % (label, sentence))
        if new:
            say("  NEW: %s." % ", ".join(new))
        if gone:
            say("  NO LONGER RETURNED BY JIRA, and so not in this build: %s. Deleted, moved to another project, or hidden from the account." % ", ".join(gone))
    records = {"format": FORMAT, "project": project, "source": source, "site_fingerprint": site, "items": items, "links": links,
               "files": {"records": args.name + ".json", "page": args.name + ".md"}}
    records_text = json.dumps(records, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    page_text = render(records, tree, lines)
    if any(secret and secret in "\n".join(LINES) + records_text + page_text for secret in secrets):
        raise Refused("a credential was found in what would be shown or saved")
    wrote = []
    try:
        if before[0] != hashlib.sha256(records_text.encode("utf-8")).hexdigest():
            write_file(records_path, records_text)
            wrote.append(os.path.basename(records_path))
        if before[1] != hashlib.sha256(page_text.encode("utf-8")).hexdigest():
            write_file(page_path, page_text)
            wrote.append(os.path.basename(page_path))
    except OSError:
        raise WriteFailed("a file could not be written%s. Run the build again: the page is written from the records every time" % (
            ". Nothing was written" if not wrote else ". The records were written and the page was not, so the page is behind the records"))
    after = (file_sum(records_path), file_sum(page_path))
    say("")
    say("FILES, in the folder given with --out-dir.")
    for label, path, a, b in (("the records", records_path, before[0], after[0]), ("the page", page_path, before[1], after[1])):
        say("  %-12s %-24s before %s   after %s   %s" % (label, shown(os.path.basename(path)), (a or "not there")[:16], (b or "not there")[:16],
                                                         "WRITTEN" if os.path.basename(path) in wrote else "not written: byte for byte the same"))
    say("")
    say("RESULT: BUILT. %d items, %d unresolved link%s, tree checksum %s. %s" % (
        len(items), sum(len(g) for g in tree["unresolved"].values()), "" if sum(len(g) for g in tree["unresolved"].values()) == 1 else "s", tree_checksum(lines),
        "The files are the same as before: nothing was written." if not wrote else "Written."))
    say_requests(conn)
    return 0


def say_requests(conn):
    say("")
    if conn.only_the_two_reads():
        say("Requests sent to Jira: %d. Each was one of the two this tool can build, and neither changes anything in Jira:" % len(conn.sent))
    else:
        say("Requests sent to Jira: %d. NOT EVERY ONE COULD BE READ BACK AS ONE OF THE TWO THIS TOOL BUILDS (a request that got no answer shows as ?):" % len(conn.sent))
    for method, path in sorted(set(conn.sent)):
        say("  %s %s  x%d" % (method, path, conn.sent.count((method, path))))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Keep the parent and child links of a Jira project, and build the tree. Reads only.")
    commands = parser.add_subparsers(dest="command", required=True)
    sub = commands.add_parser("tree")
    sub.add_argument("--records", required=True)
    sub = commands.add_parser("build")
    sub.add_argument("--source", choices=("live", "fake"), required=True)
    sub.add_argument("--project", required=True)
    sub.add_argument("--out-dir", required=True)
    sub.add_argument("--name", required=True, help="the files are NAME.json and NAME.md")
    sub.add_argument("--state", help="with --source fake: the folder that holds the made-up Jira")
    sub.add_argument("--log", help="also save the output here, with the site's address removed")
    args = parser.parse_args(argv)
    del LINES[:]
    secrets, conn, code, log_to = [], None, 0, getattr(args, "log", None)
    try:
        if args.command == "tree":
            code = cmd_tree(args)
        else:
            if log_to:
                own = [os.path.join(args.out_dir, args.name + ending) for ending in (".json", ".md")]
                if os.path.islink(log_to) or (os.path.isfile(log_to) and os.stat(log_to).st_nlink > 1) or any(same_file(log_to, path) for path in own):
                    log_to = None           # and the refusal below is NOT saved there: that would be the very write refused
                    raise Refused("--log names one of the build's own files, or a link, or a file with a second name")
                if os.path.lexists(log_to):
                    already = b""
                    if os.path.isfile(log_to):
                        with open(log_to, "rb") as f:
                            already = f.read(40)
                    if not already.startswith(tuple(start.encode("utf-8") for start in LOG_STARTS)):
                        log_to = None
                        raise Refused("--log names something that is already there and is not an output of this tool. It is left as it is")
            if args.source == "fake":
                if not args.state:
                    raise Refused("--source fake needs --state, the folder that holds the made-up Jira")
                import fake_jira
                fake = fake_jira.FakeJira.open(os.path.join(args.state, "fake-jira.json"))
                conn = Connection(fake.get, fake.post, urllib.parse.urlparse(fake_jira.SITE).hostname)
                try:
                    code = cmd_build(args, conn, False)
                finally:
                    fake.save(os.path.join(args.state, "fake-jira.json"))
            else:
                if args.state:
                    raise Refused("--state is for the made-up Jira only")
                conn, secrets = make_live()
                code = cmd_build(args, conn, True, secrets)
    except WriteFailed as failure:
        del LINES[:]
        say("REFUSED: %s." % failure)
        say("Nothing was changed in Jira: this tool can only read.")
        code = 1
    except Refused as refusal:
        del LINES[:]
        say("REFUSED: %s." % refusal)
        say("Nothing was written by this run. Nothing was changed in Jira: this tool can only read.")
        code = 1
    except Exception as surprise:           # anything unforeseen
        del LINES[:]
        say("REFUSED: the tool stopped on something it did not foresee (%s)." % type(surprise).__name__)
        say("Nothing was changed in Jira: this tool can only read.%s" % (" Check the two files before trusting them." if args.command == "build" else " This command writes nothing."))
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
            os.makedirs(os.path.dirname(os.path.abspath(log_to)), exist_ok=True)
            with open(log_to, "w", encoding="utf-8") as f:
                f.write(kept + "\n")
        except OSError:
            print("\nTHE OUTPUT ABOVE COULD NOT BE SAVED where --log said. What it says stands.")
    return code


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    sys.exit(main())
