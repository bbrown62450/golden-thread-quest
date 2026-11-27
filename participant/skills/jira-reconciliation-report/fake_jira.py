#!/usr/bin/env python3
"""A made-up Jira, and a made-up local copy to go with it, for tests and records. Together they are THE FIXTURE: a
project, DEMO, in which every state a reconciliation report can give is met at least once, and several items fit
two states at once.

    fake_jira.py fixture --copy COPY.json --describe FIXTURE.md

writes the local copy as the report tool reads it, and a page that says, item by item, what the local copy holds,
what this made-up Jira answers, and so which state the item should be given and why.

The made-up Jira answers the two requests `reconcile.py` makes, in the shape the real Jira Cloud gives them:

    GET /rest/api/3/issue/{number}?fields=issuetype,status,updated     one item, or a refusal
    GET /rest/api/3/search/jql?jql=..&fields=..&maxResults=..&nextPageToken=..      the project's items, in pages

IT IS A MODEL, AND IT CAN BE WRONG ABOUT THE REAL JIRA. What the real Jira does is shown by the one real run.

IT IS THE SAME EVERY TIME. Nothing in it changes, and the report is asked "as of" a clock that is given, NOW below.
Its refusals carry made-up private-looking text (a title, an email address) in their bodies, so that a test can show
the report repeats none of it.

`faults` can make it misbehave further:  {"listing": STATUS}  answers the list of the project with that status;
{"listing": "unreachable"}  does not answer it at all;  {"all": STATUS}  answers every item with that status.
"""
import argparse
import copy
import json
import os
import re
import sys

SITE = "https://jira.example.test"
PROJECT = "DEMO"
NOW = "2026-11-20T12:00:00Z"                 # the clock the fixture's report is asked as of
COPIED = "2026-11-18T09:00:00Z"              # when every item of the local copy was copied
SEARCH_PATH = "/rest/api/3/search/jql"
PRIVATE = {"errorMessages": ["Made-up private title: the customer export for Example Ltd"], "reporter": "made-up.person@example.invalid"}

# number, key, type, status when copied, then: what Jira has now, what the local copy has now, and the state expected.
#   jira: ("same",) | ("changed", new status, when) | ("gone",) | ("refuses", status) | ("unreachable",) | ("garbled",) | ("rekeyed", new key, when)
#   held: None if the local copy is as it was copied, or the status a person changed it to locally
ROWS = [
    ("30001", "DEMO-1", "Story", "To Do", ("same",), None, "synchronized", "Jira has what the copy has."),
    ("30002", "DEMO-2", "Task", "In Progress", ("same",), None, "synchronized", "Jira has what the copy has."),
    ("30003", "DEMO-3", "Bug", "Done", ("same",), None, "synchronized", "Jira has what the copy has."),
    ("30004", "DEMO-4", "Story", "To Do", ("gone",), None, "missing from Jira", "Jira answers 404 for it."),
    ("30005", "DEMO-5", "Story", "In Progress", ("gone",), "Done", "missing from Jira", "Jira answers 404, AND the copy was changed locally. It fits two; missing ranks higher."),
    ("30006", "DEMO-6", "Story", "To Do", ("changed", "In Progress", "2026-11-20T09:00:00Z"), None, "stale", "Jira changed it 3 hours before the report. Within the limit of 24 hours."),
    ("30007", "DEMO-7", "Task", "To Do", ("changed", "Done", "2026-11-18T10:00:00Z"), None, "stale", "Jira changed it 2 days 2 hours before the report. Over the limit."),
    ("30008", "DEMO-8", "Story", "To Do", ("changed", "In Progress", "2026-11-20T07:00:00Z"), "In Review", "conflicted", "Changed in Jira AND locally. It also fits stale; conflicted ranks higher."),
    ("30009", "DEMO-9", "Bug", "In Progress", ("changed", "Done", "2026-11-18T12:00:00Z"), "To Do", "conflicted", "Changed on both sides, and behind by 2 days: over the limit as well."),
    ("30010", "DEMO-10", "Story", "To Do", ("refuses", 429), None, "failed to fetch", "Jira answers 429: too many requests."),
    ("30011", "DEMO-11", "Task", "To Do", ("refuses", 500), "Done", "failed to fetch", "Jira answers 500, AND the copy was changed locally. Failed ranks highest: nothing is known."),
    ("30012", "DEMO-12", "Story", "In Progress", ("refuses", 403), None, "failed to fetch", "Jira answers 403: not permitted."),
    ("30013", "DEMO-13", "Story", "To Do", ("same",), "In Progress", "changed locally only", "The copy was changed locally. Jira has not changed."),
    ("30014", "DEMO-14", "Task", "Done", ("garbled",), None, "failed to fetch", "Jira answers 200 with something that is not an item."),
    ("30017", "DEMO-17", "Story", "To Do", ("unreachable",), None, "failed to fetch", "The request gets no answer at all."),
    ("30018", "DEMO-18", "Story", "To Do", ("rekeyed", "DEMO-180", "2026-11-19T15:00:00Z"), None, "stale", "Jira now calls it DEMO-180. Same number. Changed 21 hours before: within the limit."),
]
ONLY_IN_JIRA = [("30015", "DEMO-15", "Story", "To Do", "2026-11-19T08:00:00Z"), ("30016", "DEMO-16", "Bug", "To Do", "2026-11-20T10:00:00Z")]
CATEGORY = {"To Do": "new", "In Progress": "indeterminate", "In Review": "indeterminate", "Done": "done"}
JIRA_TIME = "2026-11-17T08:00:00.000+0000"    # Jira's last-changed time for every item when it was copied


def names_checksum(kind, status):
    """The same short checksum of a type name and a status name that the report tool takes, written here by itself."""
    import hashlib
    return hashlib.sha256(json.dumps([kind, status], ensure_ascii=True).encode("utf-8")).hexdigest()[:16]


def as_jira_time(utc):
    return utc.replace("Z", ".000+0000")


def local_copy():
    """The local copy, in the form `reconcile.py` reads: each item as it was copied, and as it is held now."""
    items = []
    for number, key, kind, status, _, held, _, _ in ROWS:
        copied = {"key": key, "issuetype": kind, "status": status, "updated": "2026-11-17T08:00:00Z", "names_checksum": names_checksum(kind, status)}
        items.append({"id": number, "copied_at": COPIED, "as_copied": copied, "as_held": {"issuetype": kind, "status": held or status}})
    return {"format": "jira-reconcile-copy/1", "project": PROJECT, "source": "fake", "site_fingerprint": None, "items": items}


class FakeJira:
    def __init__(self, faults=None):
        self.faults = dict(faults or {})
        self.asked = []

    def now(self, number):
        """(status, body) as this Jira answers for one item now."""
        row = [r for r in ROWS if r[0] == number]
        if not row:
            only = [o for o in ONLY_IN_JIRA if o[0] == number]
            if only:
                _, key, kind, status, when = only[0]
                return 200, shaped(number, key, kind, status, when)
            return 404, copy.deepcopy(PRIVATE)
        number, key, kind, status, jira, _, _, _ = row[0]
        how = jira[0]
        if how == "gone":
            return 404, copy.deepcopy(PRIVATE)
        if how == "refuses":
            return jira[1], copy.deepcopy(PRIVATE)
        if how == "garbled":
            return 200, {"id": number, "summary": PRIVATE["errorMessages"][0]}
        if how == "changed":
            return 200, shaped(number, key, kind, jira[1], jira[2])
        if how == "rekeyed":
            return 200, shaped(number, jira[1], kind, status, jira[2])
        return 200, shaped(number, key, kind, status, "2026-11-17T08:00:00Z")

    def get(self, path, params=None):
        params = params or {}
        self.asked.append((path, dict(params)))
        if path == SEARCH_PATH:
            fault = self.faults.get("listing")
            if fault == "unreachable":
                raise OSError("made-up network failure")
            if fault:
                return fault, {}, copy.deepcopy(PRIVATE)
            if not re.fullmatch(r'project = "%s" ORDER BY key ASC' % PROJECT, params.get("jql", ""), re.I):
                return 400, {}, {}
            there = []
            for number, _, _, _, jira, _, _, _ in ROWS:
                if jira[0] != "gone":          # an item Jira refuses or garbles when asked for alone is still in its list
                    there.append(number)
            there += [o[0] for o in ONLY_IN_JIRA]
            there.sort(key=int)
            size, start = max(1, min(int(params.get("maxResults", 50)), 100)), int(params.get("nextPageToken") or 0)
            body = {"issues": [{"id": n, "key": self.key_now(n), "fields": {}} for n in there[start:start + size]]}
            if start + size < len(there):
                body.update(nextPageToken=str(start + size), isLast=False)
            else:
                body["isLast"] = True
            return 200, {}, body
        found = re.fullmatch(r"/rest/api/3/issue/([0-9]+)", path)
        if not found:
            return 404, {}, {}
        if self.faults.get("all"):
            return self.faults["all"], {}, copy.deepcopy(PRIVATE)
        row = [r for r in ROWS if r[0] == found.group(1)]
        if row and row[0][4][0] == "unreachable":
            raise TimeoutError("made-up timeout")
        status, body = self.now(found.group(1))
        return status, {}, body

    def key_now(self, number):
        for n, key, _, _, jira, _, _, _ in ROWS:
            if n == number:
                return jira[1] if jira[0] == "rekeyed" else key
        return [o[1] for o in ONLY_IN_JIRA if o[0] == number][0]


def shaped(number, key, kind, status, when):
    return {"id": number, "key": key, "fields": {"issuetype": {"name": kind}, "status": {"name": status, "statusCategory": {"key": CATEGORY[status]}}, "updated": as_jira_time(when),
                                                 "summary": "Made-up title that is never asked for"}}


def describe():
    out = ["# Reconciliation fixture · made-up project %s" % PROJECT, "",
           "**Written by a tool** (`participant/skills/jira-reconciliation-report/fake_jira.py fixture`). Every item, time and refusal here is made up.", "",
           "**The quest names five states: synchronized, missing from Jira, stale, conflicted and failed to fetch. This fixture has seven.** Two were added,",
           "`changed locally only` and `not yet copied`, because an item in either position fits none of the five, and \"every item in exactly one state\" would then be false.", "",
           "Two things make the fixture: a **local copy** of the project (`fixture-copy.json`, beside this page), and a **made-up Jira** that answers when asked",
           "about each item. This page sets them side by side and says which state each item should be given. The report is made by another tool, which does",
           "not read this page.", "",
           "- Every item of the local copy was copied at **%s**. Jira's last-changed time for each was then 2026-11-17T08:00:00Z." % COPIED,
           "- The report is asked as of **%s**. An item that Jira has changed and the copy has not is stale; the limit is 24 hours." % NOW,
           "- %d items are in the local copy. %d more are in the made-up Jira only. **%d items are considered in all.**" % (len(ROWS), len(ONLY_IN_JIRA), len(ROWS) + len(ONLY_IN_JIRA)), "",
           "## Item by item", "",
           "| Identifier | Key | Type | Status when copied | The local copy now | What the made-up Jira answers now | State it should be given | Why |", "|---|---|---|---|---|---|---|---|"]
    said = {"same": "the same as when copied", "gone": "404: not there", "garbled": "200, with something that is not an item", "unreachable": "nothing: the request times out"}
    for number, key, kind, status, jira, held, state, why in ROWS:
        answer = said.get(jira[0]) or ("status %d" % jira[1] if jira[0] == "refuses" else "status now `%s`, changed %s" % (jira[1], jira[2]) if jira[0] == "changed" else "key now %s, changed %s" % (jira[1], jira[2]))
        out.append("| %s | %s | %s | `%s` | %s | %s | **%s** | %s |" % (number, key, kind, status, "as copied" if held is None else "**changed locally** to `%s`" % held, answer, state, why))
    for number, key, kind, status, when in ONLY_IN_JIRA:
        out.append("| %s | %s | %s | not copied | not in the local copy | status `%s`, last changed %s | **not yet copied** | Jira lists it. The local copy does not hold it. |" % (number, key, kind, status, when))
    counts = {}
    for row in ROWS:
        counts[row[6]] = counts.get(row[6], 0) + 1
    counts["not yet copied"] = len(ONLY_IN_JIRA)
    order = ["failed to fetch", "missing from Jira", "conflicted", "changed locally only", "stale", "not yet copied", "synchronized"]
    out += ["", "## What the report should count", "", "| State | Items |", "|---|---|"] + ["| %s | %d |" % (state, counts.get(state, 0)) for state in order]
    out += ["| **All** | **%d** |" % sum(counts.values()), "",
            "## Items that fit two states", "",
            "- **DEMO-5**: missing from Jira, and changed locally. Missing ranks higher.",
            "- **DEMO-8** and **DEMO-9**: changed on both sides, which is conflicted. Jira having changed also makes them stale. Conflicted ranks higher.",
            "- **DEMO-11**: its fetch failed, and it was changed locally. Failed ranks highest: nothing can be said about what Jira has.", "",
            "## What the refusals carry", "",
            "When this made-up Jira refuses a request, its answer holds a made-up title and a made-up email address, as a real refusal can.",
            "The report must name the kind of failure and repeat none of that text.", ""]
    return "\n".join(out)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Write the made-up local copy and the page that describes the fixture.")
    commands = parser.add_subparsers(dest="command", required=True)
    sub = commands.add_parser("fixture")
    sub.add_argument("--copy", required=True)
    sub.add_argument("--describe", required=True)
    args = parser.parse_args(argv)
    for path, text in ((args.copy, json.dumps(local_copy(), indent=1, sort_keys=True) + "\n"), (args.describe, describe())):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    print("The fixture was written: a local copy of %d made-up items, and the page that describes it. %d more items are in the made-up Jira only." % (len(ROWS), len(ONLY_IN_JIRA)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
