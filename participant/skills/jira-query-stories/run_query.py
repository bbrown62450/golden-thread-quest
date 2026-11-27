#!/usr/bin/env python3
"""Runs one saved query against Jira, fetches EVERY page, and says whether what it saved is all of it. IT ONLY READS.

    run_query.py list --config QUERIES.yaml
    run_query.py run  --config QUERIES.yaml --query NAME --project KEY --source live|fake --out RESULT.json
                      [--set NAME=VALUE ...] [--log FILE] [--fixture FILE] [--fault NAME=N]

THE QUERIES ARE NOT IN THIS FILE. They are in the configuration file, each with a name and a purpose. Changing a
query, adding one, or changing the page size means editing that file and nothing here.

WHAT A RUN DOES, IN ORDER
    1. Asks Jira how many items the query matches.                      "the total Jira stated"
    2. Asks for the items a page at a time, until Jira says a page is the last.
    3. Asks Jira for the count again.
    4. Compares. The result file is written ONLY IF ALL OF THESE HOLD:
         every page was answered and readable;
         the last page said it was the last, and gave no marker for a further page;
         no item came twice;
         every item belongs to the project asked for;
         the number of items equals the count Jira stated, before and after.
       Otherwise the run is INCOMPLETE: no result file is written, and the exit code is 2.

HOW IT KNOWS PAGINATION ENDED. Not by a short page, and not by an empty one: Jira may send fewer items than were
asked for on any page. It ended when a page carries no marker for the next page and does not say `isLast: false`.
That alone is Jira's word for it. The count is the second, independent check on that word.

NOTHING THAT LOOKS LIKE A RESULT IS LEFT BY AN INCOMPLETE RUN. Pages are gathered in memory. The result is written
to a temporary file beside the place it is going and moved there in one step, only at the end. If an OLDER result is
already at that place it is left as it was, and the output says it is older and is not this run's.

WHAT IS SAVED FOR EACH ITEM, and nothing else: key, id, the type's name, the status's name and category, and the
last-updated time in UTC. Titles, descriptions, comments and people are not asked for.

THE QUERY THAT IS SENT is built here, so that a saved query cannot reach outside the project named on the command line:

    project = "KEY" AND (THE SAVED FILTER) ORDER BY key ASC

A saved filter is refused if its brackets or quotes do not pair up, or if it has ORDER BY in it. --project must be
one of the configuration's `allowed_projects`.

PARAMETERS. A saved filter may have a blank, written {name}, declared under `parameters` with a kind. The only
kind is `date`. A value is given with --set name=2026-11-01, is checked to be a real date, and is put in quoted.
No other text can be put into a query from the command line.

REQUESTS. Two kinds, each built in one place:
    GET  /rest/api/3/search/jql                    the pages
    POST /rest/api/3/search/approximate-count      the count. Jira takes this question as a POST. It changes nothing
There is no code path that builds any other request. What the output says about the requests is read back from each
request as it was built. Jira calls its count approximate: a mismatch can be Jira's doing, and is still reported.

--fixture and --fault are for the made-up Jira (--source fake) and are refused against a real one.
--log FILE saves the output with the site's address replaced by a marker.

For a live run the connection comes from the environment variables JIRA_BASE_URL, JIRA_EMAIL and JIRA_API_TOKEN. None
is stored. The output is searched for the token, the email address and their encoded form before it is shown.

Exit codes: 0 complete, and the result was written (a query that matches nothing is complete, with zero items);
1 refused before anything was asked of Jira, or a credential was found in the output; 2 INCOMPLETE, no result written.
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

FORMAT = "jira-query-stories/1"
CONFIG_FORMAT = "jira-saved-queries/1"
REF = re.compile(r"([A-Za-z][A-Za-z0-9_]{0,30})-[0-9]{1,9}")
PROJECT = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,30}")
NAME = re.compile(r"[a-z][a-z0-9-]{0,40}")
BLANK = re.compile(r"\{([^{}]*)\}")
SITE_MARK = "[site address removed]"
FIELDS = "issuetype,status,updated"            # no summary: titles are not asked for
SEARCH_PATH = "/rest/api/3/search/jql"
COUNT_PATH = "/rest/api/3/search/approximate-count"
MAX_PAGES = 500
KINDS = ("date",)
SAFE = re.compile(r"[^A-Za-z0-9 ._/()'-]")
UNSEEN = re.compile("[\\x00-\\x1f\\x7f-\\xa0\\u00ad\\u034f\\u061c\\u115f\\u1160\\u200b-\\u200f\\u2028\\u2029\\u202a-\\u202e\\u2060-\\u2069\\u2800\\u3164\\ufeff\\U000e0000-\\U000e007f]")

LINES = []


class Refused(Exception):
    """Nothing was asked of Jira. The message is the reason."""


class Incomplete(Exception):
    """Jira was asked, and what came back is not known to be all of it. The message is the reason. `arrived` is how
    many items and pages had been answered in full by then, when the failure was among the pages."""

    def __init__(self, reason, arrived=None):
        Exception.__init__(self, reason)
        self.arrived = arrived


def say(text=""):
    LINES.append(text)


def word(value, limit=40):
    """A name the site's administrators chose (a status, a type): cut short, unseen characters out."""
    return SAFE.sub("?", UNSEEN.sub("?", value))[:limit].strip() or None if isinstance(value, str) and value.strip() else None


def in_utc(value):
    """Jira's time, such as 2026-11-20T10:00:00.000+0100, as 2026-11-20T09:00:00Z. None if it is not one."""
    if not isinstance(value, str):
        return None
    for shape in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            moment = datetime.datetime.strptime(value, shape)
        except ValueError:
            continue
        return moment.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return None


# ---------------------------------------------------------------- the configuration


def scalar(text, where):
    """The value after `key:`. Plain, or in single or double quotes. No escapes: a backslash in double quotes is refused."""
    text = text.strip()
    if text[:1] == "'":
        if len(text) < 2 or text[-1] != "'" or "'" in text[1:-1].replace("''", ""):
            raise Refused("%s: a value in single quotes must end with one, and a quote inside it is written twice" % where)
        return text[1:-1].replace("''", "'")
    if text[:1] == '"':
        if len(text) < 2 or text[-1] != '"' or '"' in text[1:-1] or "\\" in text:
            raise Refused('%s: a value in double quotes must end with one and have no " or \\ inside. Use single quotes' % where)
        return text[1:-1]
    if not text or text[0] in "[{&*!|>%@`#,-?:" or " #" in text or ": " in text or text.endswith(":"):
        raise Refused("%s: put this value in quotes" % where)
    return text


def load_config(path):
    """The saved queries. Reads a small, strict part of YAML, and refuses anything else with the line it is on:

        format: jira-saved-queries/1
        page_size: 10
        allowed_projects:
          - DEMO
        queries:
          - name: open-stories
            purpose: 'What it is for'
            filter: 'issuetype = Story'
            parameters:
              since: date
    """
    try:
        with open(path, encoding="utf-8") as f:
            raw = f.read()
    except (OSError, UnicodeDecodeError):
        raise Refused("the configuration file could not be read")
    if "\t" in raw:
        raise Refused("the configuration file has a tab in it. Indent with spaces")
    top, queries, projects, section, current, in_parameters = {}, [], [], None, None, False
    for number, line in enumerate(raw.split("\n"), 1):
        where = "line %d of the configuration" % number
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        body = line.strip()
        if indent == 0:
            key, colon, rest = body.partition(":")
            if not colon or key in top or key in ("allowed_projects", "queries") and (section == key or key in top):
                raise Refused("%s: expected `key: value`, once" % where)
            in_parameters, current = False, None
            if key in ("allowed_projects", "queries"):
                if rest.strip() or key in top:
                    raise Refused("%s: `%s:` is followed by a list on the lines below it" % (where, key))
                top[key], section = True, key
            elif key in ("format", "page_size"):
                top[key], section = scalar(rest, where), None
            else:
                raise Refused("%s: `%s` is not a setting this tool knows" % (where, key))
        elif section == "allowed_projects" and indent == 2 and body.startswith("- "):
            projects.append(scalar(body[2:], where))
        elif section == "queries" and indent == 2 and body.startswith("- "):
            current, in_parameters = {"parameters": {}, "line": number}, False
            queries.append(current)
            key, colon, rest = body[2:].partition(":")
            if key != "name" or not colon:
                raise Refused("%s: each query starts with `- name:`" % where)
            current["name"] = scalar(rest, where)
        elif section == "queries" and current is not None and indent == 4:
            key, colon, rest = body.partition(":")
            if not colon or key in current and key != "parameters" or key == "parameters" and in_parameters:
                raise Refused("%s: expected `key: value`, once for each query" % where)
            if key == "parameters":
                if rest.strip():
                    raise Refused("%s: `parameters:` is followed by its names on the lines below it" % where)
                in_parameters = True
            elif key in ("purpose", "filter"):
                current[key], in_parameters = scalar(rest, where), False
            else:
                raise Refused("%s: `%s` is not a setting of a query" % (where, key))
        elif section == "queries" and current is not None and in_parameters and indent == 6:
            key, colon, rest = body.partition(":")
            if not colon or key in current["parameters"]:
                raise Refused("%s: expected `name: kind`, once" % where)
            current["parameters"][key] = scalar(rest, where)
        else:
            raise Refused("%s: this line is not where the tool expects anything" % where)
    if top.get("format") != CONFIG_FORMAT:
        raise Refused("the configuration's first setting must be `format: %s`" % CONFIG_FORMAT)
    size = top.get("page_size", "")
    if not (size.isascii() and size.isdigit() and 1 <= int(size) <= 100):
        raise Refused("`page_size` must be a whole number from 1 to 100")
    if not projects or any(not PROJECT.fullmatch(p) for p in projects):
        raise Refused("`allowed_projects` must list at least one project key")
    if not queries:
        raise Refused("the configuration has no queries")
    for query in queries:
        where = "the query that starts on line %d" % query["line"]
        if not NAME.fullmatch(query.get("name", "")):
            raise Refused("%s: a name is lower-case letters, digits and dashes, starting with a letter" % where)
        if sum(1 for q in queries if q.get("name") == query["name"]) > 1:
            raise Refused("%s: the name `%s` is used twice" % (where, query["name"]))
        if len(query.get("purpose", "").strip()) < 10 or UNSEEN.search(query["purpose"]):
            raise Refused("%s: it needs a `purpose`, in words, saying what the query is for" % where)
        check_filter(query.get("filter", ""), query["parameters"], where)
    return {"page_size": int(size), "projects": [p.upper() for p in projects], "queries": queries}


def check_filter(text, parameters, where):
    if not text.strip() or UNSEEN.search(text):
        raise Refused("%s: it needs a `filter`, on one line, with no unseen characters" % where)
    depth, quote = 0, None
    for ch in text:
        if quote:
            quote = None if ch == quote else quote
        elif ch in "\"'":
            quote = ch
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth < 0:
                raise Refused("%s: the filter closes a bracket it did not open, which would let it out of the project" % where)
    if depth or quote:
        raise Refused("%s: the filter's brackets or quotes do not pair up" % where)
    if re.search(r"\border\s+by\b", text, re.I):
        raise Refused("%s: the filter must not have ORDER BY. The tool orders by key, so that pages do not shift" % where)
    for name, kind in parameters.items():
        if not NAME.fullmatch(name) or kind not in KINDS:
            raise Refused("%s: a parameter is `name: kind`, and the only kind is %s" % (where, ", ".join(KINDS)))
    used = BLANK.findall(text)
    if "{" in BLANK.sub("", text) or "}" in BLANK.sub("", text) or sorted(set(used)) != sorted(parameters) or len(used) != len(set(used)):
        raise Refused("%s: every {blank} in the filter must be declared under `parameters`, every parameter used, each once" % where)
    for name in used:                               # a blank inside quotes would have its value quoted twice
        if re.search(r"[\"']\s*\{%s\}|\{%s\}\s*[\"']" % (name, name), text):
            raise Refused("%s: write {%s} without quotes round it. The tool puts the quotes in" % (where, name))


def build_jql(query, project, given):
    """The query as sent. `given` is {name: value} from --set."""
    filled = query["filter"]
    if sorted(given) != sorted(query["parameters"]):
        raise Refused("the query `%s` takes %s, and --set gave %s" % (
            query["name"], ", ".join(sorted(query["parameters"])) or "no parameters", ", ".join(sorted(given)) or "none"))
    for name, value in given.items():
        try:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                raise ValueError
            datetime.date(int(value[:4]), int(value[5:7]), int(value[8:]))
        except ValueError:
            raise Refused("the value for `%s` must be a real date written as 2026-11-01" % name)
        filled = filled.replace("{%s}" % name, '"%s"' % value)
    return 'project = "%s" AND (%s) ORDER BY key ASC' % (project, filled)


# ---------------------------------------------------------------- the connection: two requests, both reads


class Connection:
    """Every request goes through `pages` or `count` and is written down. There is no other method."""

    def __init__(self, get, post, host):
        self._get, self._post, self.host = get, post, host
        self.sent = []

    def _ask(self, built_as, call, path, argument):
        try:
            answer = call(path, argument)
        except (OSError, TimeoutError) as err:
            self.sent.append(("?", path, None))
            raise Incomplete("Jira could not be reached (%s)" % type(getattr(err, "reason", err)).__name__)
        # A live answer carries, as its 4th part, the method of the request as it was built.
        self.sent.append((answer[3] if len(answer) == 4 else built_as + " (the made-up Jira)", path, None))
        return answer[0], answer[2]

    def pages(self, params):
        return self._ask("GET", self._get, SEARCH_PATH, params)

    def count(self, jql):
        return self._ask("POST", self._post, COUNT_PATH, {"jql": jql})

    def only_the_two_reads(self):
        return all((method.split(" ")[0], path) in (("GET", SEARCH_PATH), ("POST", COUNT_PATH)) for method, path, _ in self.sent)


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

    def send(request):
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
        return status, headers, parsed, request.get_method()

    def get(path, params):
        if path != SEARCH_PATH:
            raise Refused("this tool sends GET to one path only")
        return send(urllib.request.Request(base + path + "?" + urllib.parse.urlencode(params), method="GET"))

    def post(path, body):
        if path != COUNT_PATH or set(body) != {"jql"}:
            raise Refused("this tool sends POST to one path only, the count, with the query and nothing else")
        request = urllib.request.Request(base + path, data=json.dumps(body).encode("utf-8"), method="POST")
        request.add_header("Content-Type", "application/json")
        return send(request)

    return Connection(get, post, host), [token, email, encoded]


def site_fingerprint(host):
    return hashlib.sha256(host.lower().encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------- asking Jira


def ask_count(conn, jql, when):
    status, body = conn.count(jql)
    if status == 400:
        raise Incomplete("Jira could not read the query (status 400). Check the filter in the configuration")
    if status == 401:
        raise Incomplete("Jira rejected the credentials (401). Check JIRA_EMAIL and JIRA_API_TOKEN")
    count = body.get("count") if status == 200 and isinstance(body, dict) else None
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        raise Incomplete("Jira did not state a total %s the pages (status %d), so there is nothing to compare the saved items with" % (when, status))
    return count


def one_item(raw, project):
    """What is kept of one item, or a reason it cannot be used."""
    fields = raw.get("fields") if isinstance(raw, dict) else None
    key, ident = (raw.get("key"), raw.get("id")) if isinstance(raw, dict) else (None, None)
    found = REF.fullmatch(key) if isinstance(key, str) else None
    if not found or not (isinstance(ident, str) and ident.isascii() and ident.isdigit() and len(ident) <= 20) or not isinstance(fields, dict):
        return None, "an item that could not be read"
    if found.group(1).upper() != project:
        return None, "an item of another project"
    status = fields.get("status") if isinstance(fields.get("status"), dict) else {}
    category = status.get("statusCategory", {}).get("key") if isinstance(status.get("statusCategory"), dict) else None
    kind = fields.get("issuetype", {}).get("name") if isinstance(fields.get("issuetype"), dict) else None
    return {"key": key.upper(), "id": ident, "issuetype": word(kind), "status": word(status.get("name")),
            "status_category": category if category in ("new", "indeterminate", "done", "undefined") else None,
            "updated": in_utc(fields.get("updated"))}, None


def fetch_pages(conn, jql, project, size):
    """Every item, page by page. Raises Incomplete, saying how far it got, unless Jira's last page says it is the last."""
    items, seen, token, page_sizes = [], set(), None, []

    def stop(reason):
        got = "%d page%s and %d item%s had arrived" % (len(page_sizes), "" if len(page_sizes) == 1 else "s", len(items), "" if len(items) == 1 else "s")
        return Incomplete("page %d: %s. Before it, %s. They are not saved" % (len(page_sizes) + 1, reason, got), (len(items), len(page_sizes)))

    while True:
        params = {"jql": jql, "fields": FIELDS, "maxResults": size}
        if token:
            params["nextPageToken"] = token
        try:
            status, body = conn.pages(params)
        except Incomplete as failure:
            raise stop(str(failure))
        if status == 400:
            raise stop("Jira could not read the query (status 400). Check the filter in the configuration")
        page = body.get("issues") if status == 200 and isinstance(body, dict) else None
        if not isinstance(page, list):
            raise stop("Jira did not answer with a page of items (status %d)" % status)
        following = body.get("nextPageToken")
        if following is not None and (not isinstance(following, str) or not following):
            raise stop("Jira's marker for the next page could not be used")
        if not page and following:
            raise stop("Jira sent an empty page and said there was more")
        if following and following == token:
            raise stop("Jira gave back the same marker it was asked with, so the next page would be this one again")
        for raw in page:
            item, problem = one_item(raw, project)
            if problem:
                raise stop("Jira sent %s" % problem)
            if item["id"] in seen:
                raise stop("the item %s came a second time, so another item may have been pushed out of the pages" % item["key"])
            seen.add(item["id"])
            items.append(item)
        page_sizes.append(len(page))
        say("  Page %d: %d item%s. %s" % (len(page_sizes), len(page), "" if len(page) == 1 else "s",
                                       "Jira gave a marker for a further page." if following else "Jira gave no marker for a further page."))
        if not following:
            if body.get("isLast") is False:
                raise Incomplete("page %d: Jira said there was more and gave no way to ask for it. %d items had arrived. They are not saved" % (len(page_sizes), len(items)), (len(items), len(page_sizes)))
            return items, page_sizes
        if len(page_sizes) >= MAX_PAGES:
            raise Incomplete("stopped after %d pages, which is this tool's limit. %d items had arrived. They are not saved" % (MAX_PAGES, len(items)), (len(items), len(page_sizes)))
        token = following


def older_result(path):
    """A sentence about a result file already at `path`, or None."""
    if not os.path.lexists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            old = json.load(f)
        taken = old.get("taken_at") if isinstance(old, dict) and old.get("format") == FORMAT else None
    except (OSError, ValueError):
        taken = None
    return "A file is already at the place given with --out%s. It was left as it was. IT IS NOT THIS RUN'S RESULT." % (
        ", from a run at %s" % taken if isinstance(taken, str) and re.fullmatch(r"[0-9TZ:-]{20}", taken) else "")


def write_result(path, result):
    folder = os.path.dirname(os.path.abspath(path))
    os.makedirs(folder, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=".query-result-", suffix=".tmp", dir=folder)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=1, sort_keys=True)
            f.write("\n")
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------- the commands


def cmd_list(config):
    say("Saved queries in the configuration: %d. Page size: %d. Projects allowed: %s." % (len(config["queries"]), config["page_size"], ", ".join(config["projects"])))
    for query in config["queries"]:
        say("")
        say("  %s" % query["name"])
        say("      purpose:    %s" % query["purpose"])
        say("      filter:     %s" % query["filter"])
        if query["parameters"]:
            say("      parameters: %s" % ", ".join("%s (a %s)" % pair for pair in sorted(query["parameters"].items())))
    return 0


def cmd_run(args, config, conn, live):
    query = next((q for q in config["queries"] if q["name"] == args.query), None)
    if query is None:
        raise Refused("the configuration has no query named `%s`. It has: %s" % (args.query if NAME.fullmatch(args.query) else "that", ", ".join(q["name"] for q in config["queries"])))
    project = args.project.upper()
    if not PROJECT.fullmatch(args.project) or project not in config["projects"]:
        raise Refused("--project must be one of the configuration's allowed_projects: %s" % ", ".join(config["projects"]))
    given = {}
    for pair in args.set or []:
        name, equals, value = pair.partition("=")
        if not equals or name in given:
            raise Refused("--set takes name=value, once for each name")
        given[name] = value
    jql = build_jql(query, project, given)
    size = config["page_size"]
    say("Query: %s" % query["name"])
    say("Purpose: %s" % query["purpose"])
    say("Asked of: %s" % ("a real Jira, site fingerprint %s" % site_fingerprint(conn.host) if live else "the made-up Jira. No real Jira was contacted"))
    say("The query as sent: %s" % jql)
    say("Page size asked for: %d" % size)
    say("")
    before = after = None
    items, page_sizes, failure, arrived = [], [], None, (0, 0)
    try:
        before = ask_count(conn, jql, "before")
        say("Jira's count before the pages: %d" % before)
        items, page_sizes = fetch_pages(conn, jql, project, size)
        arrived = (len(items), len(page_sizes))
        after = ask_count(conn, jql, "after")
        say("Jira's count after the pages:  %d" % after)
        if before != after:
            raise Incomplete("Jira's own count changed while the pages were being read, from %d to %d: items were added, removed or changed "
                             "during the run. %d items arrived. Which count they belong to cannot be told. Run it again" % (before, after, len(items)))
        if len(items) != before:
            raise Incomplete("MISMATCH: Jira stated %d and %d arrived, %d %s. Every page was answered and the last said it was the last, "
                             "so the pages do not explain it" % (before, len(items), abs(before - len(items)), "short" if len(items) < before else "over"))
    except Incomplete as problem:
        failure, arrived = str(problem), problem.arrived or arrived
    say("")
    say("Total Jira stated:  %s" % (before if before is not None else "not stated"))
    say("Items received:     %d%s" % (arrived[0], "" if failure is None else "   (in pages that were answered in full. NOT SAVED)"))
    say("Pages answered:     %d" % arrived[1])
    if failure is None:
        result = {"format": FORMAT, "complete": True, "query": query["name"], "purpose": query["purpose"], "query_as_sent": jql,
                  "parameters": given, "project": project, "source": "live" if live else "fake",
                  "site_fingerprint": site_fingerprint(conn.host) if live else None, "page_size": size, "pages": len(page_sizes),
                  "total_jira_stated": before, "saved": len(items), "taken_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                  "items": items}
        try:
            write_result(args.out, result)
        except OSError:
            failure = "the result file could not be written where --out said"
    if failure is None:
        say("Items saved locally: %d, in the file given with --out: %s" % (len(items), os.path.basename(args.out)))
        say("")
        if before == 0:
            say("RESULT: COMPLETE. The query matches nothing: Jira stated 0 and 0 items were saved. That is an answer, not an error.")
        else:
            say("RESULT: COMPLETE. Jira stated %d, %d were saved, in %d page%s, and the last page said it was the last." % (
                before, len(items), len(page_sizes), "" if len(page_sizes) == 1 else "s"))
        code = 0
    else:
        say("Items saved locally: 0")
        say("")
        say("RESULT: INCOMPLETE. %s." % failure)
        say("No result file was written by this run, so nothing of it can be taken for a whole result.")
        if before is not None and arrived[0] < before:
            say("SHORTFALL: Jira stated %d and %d arrived. %d did not." % (before, arrived[0], before - arrived[0]))
        older = older_result(args.out)
        if older:
            say(older)
        code = 2
    say("")
    if conn.only_the_two_reads():
        say("Requests sent to Jira: %d. Each was one of the two this tool can build, and neither changes anything in Jira:" % len(conn.sent))
    else:
        say("Requests sent to Jira: %d. NOT EVERY ONE COULD BE READ BACK AS ONE OF THE TWO THIS TOOL BUILDS (a request that never got an answer is shown as ?):" % len(conn.sent))
    for method, path in sorted(set((m, p) for m, p, _ in conn.sent)):
        say("  %s %s  x%d" % (method, path, sum(1 for m, p, _ in conn.sent if (m, p) == (method, path))))
    return code


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run a saved Jira query, every page of it, and say whether the result is whole. Reads only.")
    commands = parser.add_subparsers(dest="command", required=True)
    sub = commands.add_parser("list")
    sub.add_argument("--config", required=True)
    sub = commands.add_parser("run")
    sub.add_argument("--config", required=True)
    sub.add_argument("--query", required=True)
    sub.add_argument("--project", required=True)
    sub.add_argument("--source", choices=("live", "fake"), required=True)
    sub.add_argument("--out", required=True, help="the result file to write, if the run is complete")
    sub.add_argument("--set", action="append", metavar="NAME=VALUE", help="a value for a parameter of the query")
    sub.add_argument("--fixture", help="with --source fake: the made-up Jira's items")
    sub.add_argument("--fault", action="append", metavar="NAME=N", help="with --source fake: make the made-up Jira misbehave")
    sub.add_argument("--log", help="also save the output here, with the site's address removed")
    args = parser.parse_args(argv)
    del LINES[:]
    secrets, conn, code = [], None, 0
    try:
        config = load_config(args.config)
        if args.command == "list":
            code = cmd_list(config)
        elif args.source == "fake":
            if not args.fixture:
                raise Refused("--source fake needs --fixture, the made-up Jira's items")
            import fake_jira
            faults = {}
            for pair in args.fault or []:
                name, _, value = pair.partition("=")
                faults[name] = True if value in ("", "true") else int(value) if value.lstrip("-").isdigit() else value
            fake = fake_jira.FakeJira.open(args.fixture, faults)
            conn = Connection(fake.get, fake.post, urllib.parse.urlparse(fake_jira.SITE).hostname)
            code = cmd_run(args, config, conn, live=False)
        else:
            if args.fixture or args.fault:
                raise Refused("--fixture and --fault are for the made-up Jira only")
            conn, secrets = make_live()
            code = cmd_run(args, config, conn, live=True)
    except Refused as refusal:
        say("")
        say("REFUSED: %s." % refusal)
        say("Nothing was asked of Jira and no result was written.")
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
    if getattr(args, "log", None):
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
