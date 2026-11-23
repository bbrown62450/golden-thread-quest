#!/usr/bin/env python3
"""A made-up GitHub for the github-update-metadata skill and its tests. It accepts writes.

Nothing here contacts GitHub. The repositories, people, labels and issues are
invented. It answers the requests the skill sends to api.github.com, with
answers shaped like GitHub's, and it remembers what was written.

Because a preview and its confirmation are two separate commands, the made-up
GitHub keeps everything in one JSON file, the store. Used as a command, this
file stands in for the world outside the skill:

    fake_github.py STORE new                       make a fresh store
    fake_github.py STORE show                      print issue 7's labels, assignees and milestone, and the writes received
    fake_github.py STORE someone-else FIELD=VALUE  another person changes issue 7 on GitHub, as a maintainer would
    fake_github.py STORE advance MINUTES           time passes on GitHub's clock
    fake_github.py STORE token-read-only           the token loses its permission to write

What is in a fresh store:

    acme-fixture/sandbox      the sandbox. Issue 7 is an issue. Number 9 is a pull request
    acme-fixture/production   a repository that exists and must never be written to

It behaves like GitHub in two ways that matter here. Adding a label that does not exist CREATES that label. And
changing an issue with PATCH and a `labels` list REPLACES every label on it.
"""
import copy
import datetime
import email.utils
import json
import os
import re
import sys
import urllib.parse

API = "https://api.github.com"
REPO, OTHER = "acme-fixture/sandbox", "acme-fixture/production"
ISSUE, PULL = 7, 9
START = "2026-11-23T09:00:00Z"
STAMP = "%Y-%m-%dT%H:%M:%SZ"
MAX_PER_PAGE = 100
WRITES = ("POST", "PATCH", "PUT", "DELETE")


def fresh():
    def repo(rid):
        return {"id": rid, "private": True, "archived": False,
                "permissions": {"admin": False, "maintain": False, "push": True, "triage": True, "pull": True},
                "labels": [{"id": 7001, "name": "bug", "color": "d73a4a", "description": "Something is not working"},
                           {"id": 7002, "name": "needs triage", "color": "fbca04", "description": None},
                           {"id": 7003, "name": "in progress", "color": "0e8a16", "description": None},
                           {"id": 7004, "name": "urgent", "color": "b60205", "description": None},
                           {"id": 7005, "name": "Docs", "color": "0075ca", "description": None}],
                "milestones": [{"number": 1, "title": "Sprint 12", "state": "open"}, {"number": 2, "title": "Sprint 11", "state": "closed"},
                               {"number": 3, "title": "Sprint 13", "state": "open"}],
                "assignable": ["robin-fixture", "kit-fixture", "sam-fixture"],
                "issues": {str(ISSUE): {"node_id": "I_kwFX%d%04d" % (rid, ISSUE), "title": "Made-up issue: export drops a column", "state": "open",
                                        "labels": ["bug", "needs triage"], "assignees": ["robin-fixture"], "milestone": 1, "pull": False},
                           str(PULL): {"node_id": "PR_kwFX%d%04d" % (rid, PULL), "title": "Made-up change", "state": "open",
                                       "labels": [], "assignees": [], "milestone": None, "pull": True}},
                "events": {str(ISSUE): [{"id": 9001, "event": "labeled", "label": "bug", "actor": "sam-fixture", "created_at": "2026-11-20T10:00:00Z"}]}}
    return {"now": START, "me": {"login": "robin-fixture", "id": 9001}, "token_may_write": True, "scopes": None, "next_id": 9100,
            "repos": {REPO: repo(401), OTHER: repo(402)}, "calls": []}


def load(path):
    with open(path, encoding="utf-8") as f:
        return FakeGitHub(json.load(f), path)


class FakeGitHub:
    def __init__(self, store=None, path=None):
        self.store = store if store is not None else fresh()
        self.path = path
        self.before = None                  # called with (method, path) before each answer. Tests use it for "meanwhile"
        self._failures = []

    def save(self):
        if self.path:
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.store, f, indent=1, sort_keys=True)
            os.replace(tmp, self.path)

    # ------------------------------------------------------------ what tests and the recording script look at

    @property
    def calls(self):
        return self.store["calls"]

    def writes(self):
        return [call for call in self.calls if call[0] in WRITES]

    def issue(self, number=ISSUE, repo=REPO):
        return self.store["repos"][repo]["issues"][str(number)]

    def snapshot(self, number=ISSUE, repo=REPO):
        """The whole repository, as it is now, for a before-and-after comparison."""
        return copy.deepcopy(self.store["repos"][repo])

    def advance(self, minutes):
        when = datetime.datetime.strptime(self.store["now"], STAMP) + datetime.timedelta(minutes=minutes)
        self.store["now"] = when.strftime(STAMP)

    def fail(self, method, path_prefix, status, times=1, headers=None):
        self._failures.append({"method": method, "prefix": path_prefix, "status": status, "times": times, "headers": headers or {}})

    def someone_else(self, change, number=ISSUE, repo=REPO, actor="sam-fixture"):
        """Another person changes the issue on GitHub. Not a request from the skill, so it is not in `calls`."""
        field, _, value = change.partition("=")
        issue = self.issue(number, repo)
        if field == "label.add" and value not in issue["labels"]:
            issue["labels"].append(value)
            self._event(repo, number, "labeled", actor, label=value)
        elif field == "label.remove" and value in issue["labels"]:
            issue["labels"].remove(value)
            self._event(repo, number, "unlabeled", actor, label=value)
        elif field == "assignee.add" and value not in issue["assignees"]:
            issue["assignees"].append(value)
            self._event(repo, number, "assigned", actor, assignee=value)
        elif field == "assignee.remove" and value in issue["assignees"]:
            issue["assignees"].remove(value)
            self._event(repo, number, "unassigned", actor, assignee=value)
        elif field == "milestone.set":
            issue["milestone"] = int(value)
            self._event(repo, number, "milestoned", actor)
        elif field == "milestone.clear":
            issue["milestone"] = None
            self._event(repo, number, "demilestoned", actor)
        elif field == "comment":
            self._event(repo, number, "commented", actor)
        else:
            raise ValueError(change)

    # ------------------------------------------------------------ answering

    def send(self, method, path, params=None, body=None):
        params = dict(params or {})
        if self.before:
            self.before(method, path)
        self.calls.append([method, path, copy.deepcopy(body)])
        headers = {"Date": email.utils.format_datetime(datetime.datetime.strptime(self.store["now"], STAMP).replace(tzinfo=datetime.timezone.utc), usegmt=True)}
        if self.store["scopes"] is not None:
            headers["X-OAuth-Scopes"] = self.store["scopes"]
        for rule in self._failures:
            if rule["method"] == method and path.startswith(rule["prefix"]) and rule["times"] > 0:
                rule["times"] -= 1
                return rule["status"], dict(headers, **rule["headers"]), {"message": "made-up failure"}
        status, more, answer = self._answer(method, path, params, body)
        self.save()
        return status, dict(headers, **more), copy.deepcopy(answer)

    def _event(self, repo, number, name, actor, **more):
        row = dict({"id": self.store["next_id"], "event": name, "actor": actor, "created_at": self.store["now"]}, **more)
        self.store["next_id"] += 1
        self.store["repos"][repo]["events"].setdefault(str(number), []).append(row)

    def _label(self, repo, name):
        return next((row for row in self.store["repos"][repo]["labels"] if row["name"].lower() == name.lower()), None)

    def _person(self, login):
        return {"login": login, "id": 9000 + sum(map(ord, login)) % 900, "type": "User"}

    def _issue_json(self, repo, number):
        issue, about = self.issue(number, repo), self.store["repos"][repo]
        milestone = next((row for row in about["milestones"] if row["number"] == issue["milestone"]), None)
        answer = {"number": number, "node_id": issue["node_id"], "title": issue["title"], "state": issue["state"],
                  "repository_url": "%s/repos/%s" % (API, repo),
                  "labels": [dict(self._label(repo, name), node_id="LA_kwFX%d" % self._label(repo, name)["id"]) for name in issue["labels"]],
                  "assignees": [self._person(login) for login in issue["assignees"]],
                  "milestone": dict(milestone, id=8000 + milestone["number"]) if milestone else None}
        if issue["pull"]:
            answer["pull_request"] = {"url": "%s/repos/%s/pulls/%d" % (API, repo, number)}
        return answer

    def _paged(self, path, params, rows):
        per_page = min(int(params.get("per_page", 30)), MAX_PER_PAGE)
        page = int(params.get("page", 1))
        start, headers = (page - 1) * per_page, {}
        if start + per_page < len(rows):
            query = urllib.parse.urlencode(dict(params, per_page=per_page, page=page + 1))
            headers["Link"] = '<%s%s?%s>; rel="next"' % (API, path, query)
        return 200, headers, rows[start:start + per_page]

    def _answer(self, method, path, params, body):
        if (method, path) == ("GET", "/user"):
            return 200, {}, dict(self.store["me"], type="User")
        found = re.match(r"^/repos/([^/]+/[^/]+)(/.*)?$", path)
        if not found or found.group(1) not in self.store["repos"]:
            return 404, {}, {"message": "Not Found"}
        repo, rest = found.group(1), found.group(2) or ""
        about = self.store["repos"][repo]
        if method in WRITES and (not self.store["token_may_write"] or about["archived"]):
            return 403, {}, {"message": "Resource not accessible by personal access token"}
        if method == "GET" and rest == "":
            return 200, {}, {"id": about["id"], "node_id": "R_kwFX%d" % about["id"], "full_name": repo, "private": about["private"],
                             "archived": about["archived"], "permissions": about["permissions"]}
        if method == "GET" and rest == "/labels":
            return self._paged(path, params, about["labels"])
        if method == "GET" and rest == "/milestones":
            wanted = params.get("state", "open")
            return self._paged(path, params, [row for row in about["milestones"] if wanted == "all" or row["state"] == wanted])
        if method == "GET" and rest.startswith("/assignees/"):
            login = urllib.parse.unquote(rest[len("/assignees/"):])
            return (204, {}, None) if login.lower() in [name.lower() for name in about["assignable"]] else (404, {}, {"message": "Not Found"})
        found = re.match(r"^/issues/(\d+)(/.*)?$", rest)
        if not found or found.group(1) not in about["issues"]:
            return 404, {}, {"message": "Not Found"}
        number, part = int(found.group(1)), found.group(2) or ""
        issue = about["issues"][str(number)]
        actor = self.store["me"]["login"]
        if method == "GET" and part == "":
            return 200, {}, self._issue_json(repo, number)
        if method == "GET" and part == "/events":
            return self._paged(path, params, [{"id": row["id"], "event": row["event"], "created_at": row["created_at"], "actor": self._person(row["actor"])}
                                             for row in about["events"].get(str(number), [])])
        if method == "POST" and part == "/labels":
            for name in (body or {}).get("labels", []):
                if not self._label(repo, name):         # GitHub creates a label that does not exist
                    about["labels"].append({"id": self.store["next_id"], "name": name, "color": "ededed", "description": None})
                    self.store["next_id"] += 1
                name = self._label(repo, name)["name"]
                if name not in issue["labels"]:
                    issue["labels"].append(name)
                    self._event(repo, number, "labeled", actor, label=name)
            return 200, {}, self._issue_json(repo, number)["labels"]
        if method == "DELETE" and part.startswith("/labels/"):
            name = urllib.parse.unquote(part[len("/labels/"):])
            held = next((have for have in issue["labels"] if have.lower() == name.lower()), None)
            if held is None:
                return 404, {}, {"message": "Label does not exist"}
            issue["labels"].remove(held)
            self._event(repo, number, "unlabeled", actor, label=held)
            return 200, {}, self._issue_json(repo, number)["labels"]
        if method in ("POST", "DELETE") and part == "/assignees":
            for login in (body or {}).get("assignees", []):
                known = next((name for name in about["assignable"] if name.lower() == login.lower()), None)
                if method == "POST" and known and known not in issue["assignees"]:
                    issue["assignees"].append(known)
                    self._event(repo, number, "assigned", actor, assignee=known)
                if method == "DELETE" and known in issue["assignees"]:
                    issue["assignees"].remove(known)
                    self._event(repo, number, "unassigned", actor, assignee=known)
            return (201 if method == "POST" else 200), {}, self._issue_json(repo, number)
        if method == "PATCH" and part == "":
            body = body or {}
            if "milestone" in body:
                if body["milestone"] is not None and body["milestone"] not in [row["number"] for row in about["milestones"]]:
                    return 422, {}, {"message": "Validation Failed"}
                if issue["milestone"] != body["milestone"]:
                    issue["milestone"] = body["milestone"]
                    self._event(repo, number, "milestoned" if body["milestone"] is not None else "demilestoned", actor)
            if "labels" in body:                          # as on GitHub: this REPLACES every label
                issue["labels"] = list(body["labels"])
            for key in ("title", "state", "body"):
                if key in body:
                    issue[key] = body[key]
            return 200, {}, self._issue_json(repo, number)
        return 404, {}, {"message": "Not Found"}


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    path, command, rest = argv[0], argv[1], argv[2:]
    if command == "new":
        FakeGitHub(fresh(), path).save()
        print("made-up GitHub: a fresh store was made")
        return 0
    fake = load(path)
    if command == "someone-else":
        fake.someone_else(rest[0])
        print("made-up GitHub: another person, sam-fixture, changed issue %d on GitHub: %s" % (ISSUE, rest[0]))
    elif command == "advance":
        fake.advance(int(rest[0]))
        print("made-up GitHub: %d minutes passed. GitHub's clock now says %s" % (int(rest[0]), fake.store["now"]))
    elif command == "token-read-only":
        fake.store["token_may_write"] = False
        print("made-up GitHub: the token may no longer write")
    elif command == "show":
        issue = fake.issue()
        print("made-up GitHub: issue %d of %s: labels %s, assignees %s, milestone %s"
              % (ISSUE, REPO, json.dumps(issue["labels"]), json.dumps(issue["assignees"]), json.dumps(issue["milestone"])))
        print("made-up GitHub: writes received so far, to any repository: %d" % len(fake.writes()))
        for method, where, body in fake.writes():
            print("made-up GitHub:   %s %s %s" % (method, where, json.dumps(body) if body is not None else ""))
    else:
        print(__doc__)
        return 1
    fake.save()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
