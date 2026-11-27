#!/usr/bin/env python3
"""A made-up Jira for tests and records. It holds ONE made-up project, DEMO, in a JSON file, and answers the one request
`hierarchy.py` makes, in the shape the real Jira Cloud gives it:

    POST /rest/api/3/search/approximate-count    body {"jql": ..}    answers {"count": N}
    GET /rest/api/3/search/jql?jql=..&fields=..&maxResults=..&nextPageToken=..
        {"issues": [{"id", "key", "fields": {"issuetype": {"name", "hierarchyLevel", "subtask"},
                                             "parent": {"id", "key", "fields": {"summary", ..}},      only if it has one
                                             "timeoriginalestimate": seconds or null,
                                             "issuelinks": [{"id", "type": {"name", "inward", "outward"},
                                                             "outwardIssue" or "inwardIssue": {"id", "key", "fields": {"summary"}}}]}}],
         "nextPageToken": "..", "isLast": false}          and on the last page "isLast": true with no token

IT IS A MODEL, AND IT CAN BE WRONG ABOUT THE REAL JIRA. What the real Jira does is shown by the one real run.
It reads one query only: project = "DEMO" ORDER BY key ASC. It answers 400 for anything else.

THE MADE-UP PROJECT has an epic, three stories, two tasks, four subtasks and a bug. One story's parent is an epic in
ANOTHER project, which a read of DEMO does not retrieve. Titles are in it so that a test can show none is kept.

IT CAN BE CHANGED, the way people change a project in Jira. The hierarchy tool has no way to do any of this: it
sends GET and nothing else. These are this file's own commands, on its own file:

    fake_jira.py new    --state DIR                          a fresh made-up project
    fake_jira.py move   --state DIR --key KEY --under KEY    give an item another parent
    fake_jira.py rekey  --state DIR --key KEY --to KEY       give an item another key, as a move between projects does
    fake_jira.py break  --state DIR --how self|loop          make an item its own parent, or make two items each
                                                             other's parent. A real Jira is not supposed to allow either

IT CAN BE MADE TO MISBEHAVE. `faults` is a dictionary kept in the file. N counts pages asked for, from 1.
    fail_page: N        the Nth page is answered with status 500
    repeat_on_page: N   the Nth page starts one item early
    early_last: N       the Nth page says it is the last, and it is not
    always_early: true  every reading stops after its first page, saying it is the last: the same wrong answer twice
    no_count: true      the count request is answered 404
    change_after: N     after the Nth page is answered, an item gets another parent, as if someone moved it meanwhile
"""
import argparse
import copy
import json
import os
import re
import sys

SITE = "https://jira.example.test"
SEARCH_PATH = "/rest/api/3/search/jql"
COUNT_PATH = "/rest/api/3/search/approximate-count"
LEVELS = {"Epic": 1, "Story": 0, "Task": 0, "Bug": 0, "Subtask": -1}


def fresh():
    rows = [  # key, id, type, parent key, estimate in hours
        ("DEMO-1", "30001", "Epic", None, None),
        ("DEMO-2", "30002", "Story", "DEMO-1", 8),
        ("DEMO-3", "30003", "Story", "DEMO-1", 5),
        ("DEMO-4", "30004", "Task", "DEMO-1", 3),
        ("DEMO-5", "30005", "Task", None, 2),
        ("DEMO-6", "30006", "Subtask", "DEMO-2", 3),
        ("DEMO-7", "30007", "Subtask", "DEMO-2", 2),
        ("DEMO-8", "30008", "Subtask", "DEMO-3", 4),
        ("DEMO-9", "30009", "Subtask", "DEMO-4", None),
        ("DEMO-10", "30010", "Story", "OTHER-3", 6),
        ("DEMO-11", "30011", "Bug", None, 1),
    ]
    ids = {key: ident for key, ident, _, _, _ in rows}
    ids["OTHER-3"] = "40003"
    issues = [{"key": key, "id": ident, "type": kind, "parent": {"id": ids[parent], "key": parent} if parent else None,
               "estimate": hours * 3600 if hours is not None else None, "summary": "Made-up title of %s, which is never kept" % key} for key, ident, kind, parent, hours in rows]
    links = [{"id": "50001", "name": "Blocks", "outward": "blocks", "inward": "is blocked by", "from": "DEMO-3", "to": "DEMO-5"},
             {"id": "50002", "name": "Relates", "outward": "relates to", "inward": "relates to", "from": "DEMO-2", "to": "DEMO-11"},
             {"id": "50003", "name": "Blocks", "outward": "blocks", "inward": "is blocked by", "from": "DEMO-8", "to": "OTHER-9"}]
    return {"project": "DEMO", "issues": issues, "links": links, "other": {"OTHER-3": "40003", "OTHER-9": "40009"}, "faults": {}, "asked": 0}


class FakeJira:
    def __init__(self, data):
        self.data = data

    @classmethod
    def open(cls, path):
        with open(path, encoding="utf-8") as f:
            return cls(json.load(f))

    def save(self, path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=1)
            f.write("\n")

    def find(self, key):
        return [i for i in self.data["issues"] if i["key"] == key][0]

    # ------------------------------------------------ what people do in Jira. The hierarchy tool cannot call these

    def move(self, key, under):
        target = self.find(under)
        self.find(key)["parent"] = {"id": target["id"], "key": target["key"]}

    def rekey(self, key, new):
        self.find(key)["key"] = new
        for issue in self.data["issues"]:
            if issue["parent"] and issue["parent"]["key"] == key:
                issue["parent"]["key"] = new
        for link in self.data["links"]:
            link["from"], link["to"] = (new if link["from"] == key else link["from"]), (new if link["to"] == key else link["to"])

    def break_it(self, how):
        if how == "self":
            issue = self.find("DEMO-5")
            issue["parent"] = {"id": issue["id"], "key": issue["key"]}
        else:
            self.move("DEMO-1", "DEMO-6")          # the epic under a subtask of a story under that epic: a loop of three

    # ------------------------------------------------ what Jira answers

    def shaped(self, issue, fields):
        by_key = {i["key"]: i["id"] for i in self.data["issues"]}
        by_key.update(self.data["other"])
        out = {}
        if "issuetype" in fields:
            out["issuetype"] = {"name": issue["type"], "hierarchyLevel": LEVELS.get(issue["type"], 0), "subtask": issue["type"] == "Subtask"}
        if "parent" in fields and issue["parent"]:
            out["parent"] = {"id": issue["parent"]["id"], "key": issue["parent"]["key"], "fields": {"summary": "Made-up title of the parent, which is never kept", "issuetype": {"name": "Made-up"}}}
        if "timeoriginalestimate" in fields:
            out["timeoriginalestimate"] = issue["estimate"]
        if "issuelinks" in fields:
            out["issuelinks"] = []
            for link in self.data["links"]:
                kind = {"name": link["name"], "inward": link["inward"], "outward": link["outward"]}
                if link["from"] == issue["key"]:
                    out["issuelinks"].append({"id": link["id"], "type": kind, "outwardIssue": {"id": by_key[link["to"]], "key": link["to"], "fields": {"summary": "Made-up title of a linked item"}}})
                if link["to"] == issue["key"]:
                    out["issuelinks"].append({"id": link["id"], "type": kind, "inwardIssue": {"id": by_key[link["from"]], "key": link["from"], "fields": {"summary": "Made-up title of a linked item"}}})
        if "summary" in fields:
            out["summary"] = issue["summary"]
        return {"id": issue["id"], "key": issue["key"], "fields": out}

    def post(self, path, body):
        if path != COUNT_PATH or not isinstance(body, dict) or set(body) != {"jql"} or self.data["faults"].get("no_count"):
            return 404, {}, {}
        if not re.fullmatch(r'project = "%s" ORDER BY key ASC' % self.data["project"], body["jql"], re.I):
            return 400, {}, {}
        return 200, {}, {"count": len(self.data["issues"])}

    def get(self, path, params=None):
        params = params or {}
        if path != SEARCH_PATH:
            return 404, {}, {}
        if not re.fullmatch(r'project = "%s" ORDER BY key ASC' % self.data["project"], params.get("jql", ""), re.I):
            return 400, {}, {"errorMessages": ["the made-up Jira could not read the query"]}
        self.data["asked"] += 1
        n, faults = self.data["asked"], self.data["faults"]
        if faults.get("fail_page") == n:
            return 500, {}, {}
        found = sorted(self.data["issues"], key=lambda i: (i["key"].split("-")[0], int(i["key"].split("-")[1])))
        fields = [name for name in str(params.get("fields", "")).split(",") if name]
        self.data.setdefault("fields_asked", []).append(fields)
        size = max(1, min(int(params.get("maxResults", 50)), 100))
        start = int(params.get("nextPageToken") or 0)
        first = start - 1 if faults.get("repeat_on_page") == n and start > 0 else start
        body = {"issues": [self.shaped(issue, fields) for issue in found[first:first + size]]}
        if start + size < len(found) and faults.get("early_last") != n and not faults.get("always_early"):
            body.update(nextPageToken=str(start + size), isLast=False)
        else:
            body["isLast"] = True
        if faults.get("change_after") == n:
            self.move("DEMO-7", "DEMO-3")
        return 200, {}, copy.deepcopy(body)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Change the made-up Jira's one made-up project. Not a way to change a real Jira.")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("new", "move", "rekey", "break"):
        sub = commands.add_parser(name)
        sub.add_argument("--state", required=True)
        if name in ("move", "rekey"):
            sub.add_argument("--key", required=True)
        if name == "move":
            sub.add_argument("--under", required=True)
        if name == "rekey":
            sub.add_argument("--to", required=True)
        if name == "break":
            sub.add_argument("--how", choices=("self", "loop"), required=True)
    args = parser.parse_args(argv)
    path = os.path.join(args.state, "fake-jira.json")
    if args.command == "new":
        os.makedirs(args.state, exist_ok=True)
        fake = FakeJira(fresh())
        print("The made-up Jira has a fresh made-up project, DEMO, with %d items." % len(fake.data["issues"]))
    else:
        fake = FakeJira.open(path)
        if args.command == "move":
            fake.move(args.key, args.under)
            print("In the made-up Jira: %s was moved under %s." % (args.key, args.under))
        elif args.command == "rekey":
            fake.rekey(args.key, args.to)
            print("In the made-up Jira: %s now has the key %s. Its internal number is the same." % (args.key, args.to))
        else:
            fake.break_it(args.how)
            print("In the made-up Jira: %s" % ("DEMO-5 was made its own parent." if args.how == "self" else "DEMO-1 was put under DEMO-6, which is under DEMO-2, which is under DEMO-1: a loop."))
    fake.save(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
