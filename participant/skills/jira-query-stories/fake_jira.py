#!/usr/bin/env python3
"""A made-up Jira for tests and records. It holds made-up items in memory and answers the two requests `run_query.py`
makes, in the shape the real Jira Cloud gives them:

    POST /rest/api/3/search/approximate-count     body {"jql": ..}          answers {"count": N}
    GET  /rest/api/3/search/jql?jql=..&fields=..&maxResults=..&nextPageToken=..
                                                  answers {"issues": [..], "nextPageToken": "..", "isLast": false}
                                                  and on the last page {"issues": [..], "isLast": true}, with no token

IT IS A MODEL, AND IT CAN BE WRONG ABOUT THE REAL JIRA. Twice in earlier quests a model like this one was. What the
real Jira does is shown by the one real run, not by this file.

IT UNDERSTANDS A SMALL PART OF JQL, and answers 400 for anything else, as Jira does for a query it cannot read:

    project = "KEY" AND (CLAUSE AND CLAUSE ...) ORDER BY key ASC

    CLAUSE is one of   issuetype = X    issuetype != X    status = X    status != X
                       statusCategory = X    statusCategory != X    labels = X
                       updated >= "YYYY-MM-DD"    updated <= "YYYY-MM-DD"    created >= "YYYY-MM-DD"

IT CAN BE MADE TO MISBEHAVE, one fault at a time, so that the tool's handling of each can be shown. `faults` is a
dictionary. N counts pages of one run from 1.

    fail_page: N          the Nth page is answered with status 500
    unreachable_page: N   the Nth page is not answered at all
    early_last: N         the Nth page says it is the last, and it is not. This is the quest's scenario
    drop_on_page: N       the Nth page leaves out its first item and says nothing
    repeat_on_page: N     the Nth page starts one item early: one item comes twice and another never comes. The
                          NUMBER of items received is then right, and the items are wrong
    empty_more: N         the Nth page is empty and says there is more
    token_loop: N         the Nth page gives back the page marker it was asked with
    other_project: N      the Nth page's first item belongs to another project
    no_count: true        the count request is answered 404
    count_moves: K        the second count is K more than the first, as if items were added during the run

A fixture is a JSON file: {"project": "DEMO", "issues": [{"key", "id", "issuetype", "status", "category", "labels",
"created", "updated", "summary"}, ..]}. The summary is there so that a test can show the tool never asks for it.
"""
import copy
import json
import re

SITE = "https://jira.example.test"
COUNT_PATH = "/rest/api/3/search/approximate-count"
SEARCH_PATH = "/rest/api/3/search/jql"
WHOLE = re.compile(r'project = "([A-Za-z][A-Za-z0-9_]*)" AND \((.*)\) ORDER BY key ASC', re.S)
CLAUSE = re.compile(r'(issuetype|status|statusCategory|labels|updated|created) (=|!=|>=|<=) (?:"([^"]*)"|([A-Za-z0-9_-]+))')
CATEGORY_NAMES = {"new": "To Do", "indeterminate": "In Progress", "done": "Done"}


class BadQuery(Exception):
    pass


def matches(issue, clause):
    found = CLAUSE.fullmatch(clause.strip())
    if not found:
        raise BadQuery(clause)
    field, op, quoted, bare = found.groups()
    value = quoted if quoted is not None else bare
    if field in ("updated", "created"):
        if op not in (">=", "<=") or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise BadQuery(clause)
        day = issue[field][:10]
        return day >= value if op == ">=" else day <= value
    if op not in ("=", "!="):
        raise BadQuery(clause)
    if field == "labels":
        if op != "=":
            raise BadQuery(clause)
        return value.lower() in [label.lower() for label in issue.get("labels", [])]
    have = {"issuetype": issue["issuetype"], "status": issue["status"], "statusCategory": CATEGORY_NAMES[issue["category"]]}[field]
    return (have.lower() == value.lower()) == (op == "=")


class FakeJira:
    def __init__(self, project, issues, faults=None):
        self.project, self.issues, self.faults = project, issues, dict(faults or {})
        self.pages_asked = 0
        self.counts_asked = 0
        self.fields_asked = []

    @classmethod
    def open(cls, path, faults=None):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return cls(data["project"], data["issues"], faults)

    def found(self, jql):
        whole = WHOLE.fullmatch(jql or "")
        if not whole:
            raise BadQuery(jql)
        if whole.group(1).upper() != self.project:
            return []
        clauses = whole.group(2).split(" AND ")
        return sorted((i for i in self.issues if all(matches(i, c) for c in clauses)), key=lambda i: int(i["key"].split("-")[1]))

    def shaped(self, issue, fields):
        out = {}
        for name in fields:
            if name == "issuetype":
                out[name] = {"name": issue["issuetype"]}
            elif name == "status":
                out[name] = {"name": issue["status"], "statusCategory": {"key": issue["category"]}}
            elif name in ("updated", "created", "summary", "labels"):
                out[name] = copy.deepcopy(issue.get(name))
        return {"id": issue["id"], "key": issue["key"], "fields": out}

    def post(self, path, body):
        if path != COUNT_PATH or not isinstance(body, dict) or set(body) != {"jql"}:
            return 404, {}, {}
        self.counts_asked += 1
        if self.faults.get("no_count"):
            return 404, {}, {}
        try:
            count = len(self.found(body["jql"]))
        except BadQuery:
            return 400, {}, {"errorMessages": ["the made-up Jira could not read the query"]}
        if self.counts_asked > 1:
            count += int(self.faults.get("count_moves", 0))
        return 200, {}, {"count": count}

    def get(self, path, params=None):
        params = params or {}
        if path != SEARCH_PATH:
            return 404, {}, {}
        self.pages_asked += 1
        n = self.pages_asked
        if self.faults.get("unreachable_page") == n:
            raise OSError("made-up network failure")
        if self.faults.get("fail_page") == n:
            return 500, {}, {}
        try:
            found = self.found(params.get("jql"))
        except BadQuery:
            return 400, {}, {"errorMessages": ["the made-up Jira could not read the query"]}
        fields = [name for name in str(params.get("fields", "")).split(",") if name]
        self.fields_asked.append(fields)
        size = max(1, min(int(params.get("maxResults", 50)), 100))
        asked = params.get("nextPageToken")
        start = int(asked or 0)
        first = start
        if self.faults.get("repeat_on_page") == n and start > 0:
            first = start - 1
        page = found[first:first + size]
        if self.faults.get("drop_on_page") == n:
            page = page[1:]
        if self.faults.get("empty_more") == n:
            return 200, {}, {"issues": [], "nextPageToken": str(start + size), "isLast": False}
        issues = [self.shaped(issue, fields) for issue in page]
        if self.faults.get("other_project") == n and issues:
            issues[0]["key"] = "OTHER-" + issues[0]["key"].split("-")[1]
        body = {"issues": issues}
        if self.faults.get("token_loop") == n and asked:
            body.update(nextPageToken=asked, isLast=False)
        elif start + size < len(found) and self.faults.get("early_last") != n:
            body.update(nextPageToken=str(start + size), isLast=False)
        else:
            body["isLast"] = True
        return 200, {}, body
