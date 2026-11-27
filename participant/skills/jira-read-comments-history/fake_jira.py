#!/usr/bin/env python3
"""A made-up Jira for tests and records. It holds ONE made-up story, DEMO-7, with made-up comments and a made-up
change history, in a JSON file, and answers the three requests `sync_comments.py` makes, in the shape the real Jira
Cloud gives them:

    GET /rest/api/3/issue/{key}?fields=issuetype
    GET /rest/api/3/issue/{key}/comment?startAt=..&maxResults=..     {"startAt", "maxResults", "total", "comments": [..]}
    GET /rest/api/3/issue/{key}/comment/{id}                         one comment, or 404 if it is not there
    GET /rest/api/3/issue/{key}/changelog?startAt=..&maxResults=..   {"startAt", "maxResults", "total", "isLast", "values": [..]}

IT IS A MODEL, AND IT CAN BE WRONG ABOUT THE REAL JIRA. What the real Jira does is shown by the one real run.

IT CAN BE CHANGED, the way people change a story in Jira, so that the next sync has something to find. The sync tool
has no way to do any of this: it sends GET and nothing else. These are this file's own commands, on its own file:

    fake_jira.py new    --state DIR                            a fresh made-up story
    fake_jira.py edit   --state DIR --id ID --text TEXT [--by author|other] --at TIME
    fake_jira.py add    --state DIR --text TEXT --at TIME
    fake_jira.py delete --state DIR --id ID
    fake_jira.py change --state DIR --field FIELD --from X --to Y --at TIME      one entry in the change history

IT CAN BE MADE TO MISBEHAVE. `faults` is a dictionary, kept in the file:
    fail_comments_page: N     the Nth page of comments asked for is answered with status 500
    fail_history_page: N      the same, for the change history
    short_total: K            the comments' `total` is K more than the comments it will ever send
    repeat_comment: true      the second page of comments starts one comment early

Every person here is an account id that is made up: "acct-ana", "acct-ben", "acct-cho".
"""
import argparse
import copy
import json
import os
import re
import sys

SITE = "https://jira.example.test"
KEY, IDENT = "DEMO-7", "20007"


def doc(text):
    return {"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [{"type": "text", "text": line}]} for line in text.split("\n")]}


def item(field, field_id, old, new):
    """One change in the history, as Jira gives it. A field the site added is marked custom. A link carries the other
    item's key in `from` or `to`, beside the sentence in `fromString` or `toString`."""
    out = {"field": field, "fieldId": field_id, "fieldtype": "custom" if field_id.startswith("customfield_") else "jira", "fromString": old, "toString": new}
    if field == "Link":
        key = re.search(r"[A-Z]+-[0-9]+$", new or old or "")
        out.update({"from": key.group(0) if key and old else None, "to": key.group(0) if key and new else None})
        out.pop("fieldId")
    return out


def fresh():
    comments = [
        ("31001", "acct-ana", "2026-11-02T09:15:00.000+0000", "Made-up comment: the export should include archived orders too."),
        ("31002", "acct-ben", "2026-11-03T14:40:00.000+0000", "Made-up comment: archived orders are in a separate table. I can add them, it is about a day."),
        ("31003", "acct-ana", "2026-11-04T08:05:00.000+0000", "Made-up comment: a day is fine. Please keep the column order the same."),
        ("31004", "acct-cho", "2026-11-05T16:20:00.000+0000", "Made-up comment: reminder that the finance review is on the 20th."),
        ("31005", "acct-ben", "2026-11-06T11:00:00.000+0000", "Made-up comment: first version is on the test site."),
    ]
    history = [
        ("41001", "2026-11-01T10:00:00.000+0000", [("status", "status", "To Do", "In Progress")]),
        ("41002", "2026-11-01T10:05:00.000+0000", [("Rank", "customfield_10019", "", "Ranked higher")]),
        ("41003", "2026-11-02T09:00:00.000+0000", [("assignee", "assignee", "Ana Example", "Ben Example"), ("labels", "labels", "", "quarter-end")]),
        ("41004", "2026-11-03T12:00:00.000+0000", [("priority", "priority", "Medium", "High")]),
        ("41005", "2026-11-03T12:30:00.000+0000", [("Rank", "customfield_10019", "", "Ranked lower"), ("Sprint", "customfield_10020", "", "Made-up Sprint 4")]),
        ("41006", "2026-11-04T15:00:00.000+0000", [("duedate", "duedate", "2026-11-18", "2026-11-25")]),
        ("41007", "2026-11-05T09:30:00.000+0000", [("summary", "summary", "Made-up old title", "Made-up new title"), ("Attachment", "attachment", "", "made-up.png")]),
        ("41008", "2026-11-05T17:00:00.000+0000", [("Link", "issuelinks", "", "This issue blocks DEMO-9")]),
        ("41009", "2026-11-06T08:00:00.000+0000", [("Story Points", "customfield_10016", "3", "5")]),
        ("41010", "2026-11-06T12:00:00.000+0000", [("timespent", "timespent", "", "3600"), ("description", "description", "Made-up old description", "Made-up new description")]),
    ]
    return {"key": KEY, "id": IDENT, "next_comment": 31006, "next_history": 41011, "faults": {}, "asked": {"comments": 0, "history": 0},
            "comments": [{"id": i, "author": a, "updateAuthor": a, "created": t, "updated": t, "text": text} for i, a, t, text in comments],
            "history": [{"id": i, "created": t, "items": [item(f, fid, x, y) for f, fid, x, y in items]} for i, t, items in history]}


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

    # ------------------------------------------------ what people do in Jira. The sync tool cannot call these

    def edit(self, ident, text, at, by="author"):
        comment = [c for c in self.data["comments"] if c["id"] == ident][0]
        comment.update(text=text, updated=at, updateAuthor=comment["author"] if by == "author" else "acct-cho" if comment["author"] != "acct-cho" else "acct-ana")

    def add(self, text, at, author="acct-ana"):
        ident = str(self.data["next_comment"])
        self.data["next_comment"] += 1
        self.data["comments"].append({"id": ident, "author": author, "updateAuthor": author, "created": at, "updated": at, "text": text})
        return ident

    def delete(self, ident):
        before = len(self.data["comments"])
        self.data["comments"] = [c for c in self.data["comments"] if c["id"] != ident]
        if len(self.data["comments"]) == before:
            raise KeyError(ident)

    def change(self, field, old, new, at, field_id=None):
        ident = str(self.data["next_history"])
        self.data["next_history"] += 1
        self.data["history"].append({"id": ident, "created": at, "items": [item(field, field_id or field, old, new)]})
        return ident

    # ------------------------------------------------ what Jira answers

    def get(self, path, params=None):
        params = params or {}
        one = re.fullmatch(r"/rest/api/3/issue/([^/]+)/comment/([0-9]+)", path)
        if one and one.group(1).upper() in (self.data["key"], self.data["id"]):
            there = [c for c in self.data["comments"] if c["id"] == one.group(2)]
            return (200, {}, {"id": there[0]["id"]}) if there else (404, {}, {"errorMessages": ["Can not find a comment for the id."]})
        found = re.fullmatch(r"/rest/api/3/issue/([^/]+)(/comment|/changelog)?", path)
        if not found or found.group(1).upper() not in (self.data["key"], self.data["id"]):
            return 404, {}, {"errorMessages": ["Issue does not exist or you do not have permission to see it."]}
        if not found.group(2):
            return 200, {}, {"id": self.data["id"], "key": self.data["key"], "fields": {"issuetype": {"name": "Story"}}}
        start, size = int(params.get("startAt", 0)), max(1, min(int(params.get("maxResults", 50)), 100))
        faults = self.data["faults"]
        if found.group(2) == "/comment":
            self.data["asked"]["comments"] += 1
            if faults.get("fail_comments_page") == self.data["asked"]["comments"]:
                return 500, {}, {}
            first = start - 1 if faults.get("repeat_comment") and start > 0 else start
            page = [{"id": c["id"], "author": {"accountId": c["author"], "displayName": "Made-up Person"},
                     "updateAuthor": {"accountId": c["updateAuthor"], "displayName": "Made-up Person"},
                     "body": doc(c["text"]), "created": c["created"], "updated": c["updated"]} for c in self.data["comments"][first:first + size]]
            return 200, {}, {"startAt": start, "maxResults": size, "total": len(self.data["comments"]) + int(faults.get("short_total", 0)), "comments": page}
        self.data["asked"]["history"] += 1
        if faults.get("fail_history_page") == self.data["asked"]["history"]:
            return 500, {}, {}
        page = [{"id": h["id"], "author": {"accountId": "acct-ana", "displayName": "Made-up Person"}, "created": h["created"], "items": copy.deepcopy(h["items"])}
                for h in self.data["history"][start:start + size]]
        return 200, {}, {"startAt": start, "maxResults": size, "total": len(self.data["history"]), "isLast": start + size >= len(self.data["history"]), "values": page}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Change the made-up Jira's one made-up story. Not a way to change a real Jira.")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("new", "edit", "add", "delete", "change"):
        sub = commands.add_parser(name)
        sub.add_argument("--state", required=True)
        if name in ("edit", "delete"):
            sub.add_argument("--id", required=True)
        if name in ("edit", "add"):
            sub.add_argument("--text", required=True)
        if name == "edit":
            sub.add_argument("--by", choices=("author", "other"), default="author")
        if name == "change":
            sub.add_argument("--field", required=True)
            sub.add_argument("--from", dest="old", required=True)
            sub.add_argument("--to", dest="new", required=True)
        if name in ("edit", "add", "change"):
            sub.add_argument("--at", required=True, help="when it happened in the made-up Jira, as 2026-11-08T10:00:00.000+0000")
    args = parser.parse_args(argv)
    path = os.path.join(args.state, "fake-jira.json")
    if args.command == "new":
        os.makedirs(args.state, exist_ok=True)
        fake = FakeJira(fresh())
        print("The made-up Jira has a fresh made-up story, %s, with %d comments and %d entries in its change history." % (KEY, len(fake.data["comments"]), len(fake.data["history"])))
    else:
        fake = FakeJira.open(path)
        if args.command == "edit":
            fake.edit(args.id, args.text, args.at, args.by)
            print("In the made-up Jira: comment %s was edited by %s." % (args.id, "its author" if args.by == "author" else "someone else"))
        elif args.command == "add":
            print("In the made-up Jira: comment %s was added." % fake.add(args.text, args.at))
        elif args.command == "delete":
            fake.delete(args.id)
            print("In the made-up Jira: comment %s was deleted." % args.id)
        else:
            print("In the made-up Jira: history entry %s, %s changed." % (fake.change(args.field, args.old, args.new, args.at), args.field))
    fake.save(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
