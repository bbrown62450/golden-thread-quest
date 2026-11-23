#!/usr/bin/env python3
"""A made-up GitHub for the github-create-issue skill and its tests. It can create issues.

Nothing here contacts GitHub. It is the made-up GitHub of the github-create-issue-preview skill, loaded from
that skill's folder and not changed, with three things added: it accepts the one write this skill makes
(creating an issue), it can be asked for an issue by number, and it can be told to misbehave.

It keeps everything in one JSON file, the store, because a preview and its confirmation are two commands.

    fake_github.py STORE new                      make a fresh store
    fake_github.py STORE show                     print the issues created so far and every write received
    fake_github.py STORE mode MODE                how the next create goes. One of:
                                                    ok              the issue is created and GitHub says so
                                                    lost-answer     the issue IS created, and the answer never arrives
                                                    never-arrived   the request never reaches GitHub
                                                    refused         GitHub answers 403 and creates nothing
                                                    drop-labels     the issue is created WITHOUT its labels, as GitHub does
                                                                    when the account may not triage
    fake_github.py STORE advance MINUTES          time passes on GitHub's clock
    fake_github.py STORE someone-else TITLE       another person files an issue with this title

Like GitHub, it creates an issue every time it is asked. It does not notice that it was asked twice.
"""
import copy
import datetime
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("made_up_github_of_the_preview", os.path.join(HERE, "..", "github-create-issue-preview", "fake_github.py"))
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)

REPO, OTHER, STAMP, API = base.REPO, base.OTHER, base.STAMP, base.API
MODES = ("ok", "lost-answer", "never-arrived", "refused", "drop-labels")


def fresh():
    store = base.fresh()
    store.update(mode="ok", next_id=5000108)
    for repo in store["repos"].values():
        repo["issues"] = {}
    return store


def load(path):
    with open(path, encoding="utf-8") as f:
        return FakeGitHub(json.load(f), path)


class FakeGitHub(base.FakeGitHub):
    def __init__(self, store=None, path=None):
        super().__init__(store if store is not None else fresh(), path)

    def writes(self):
        return [call for call in self.calls if call[0] != "GET"]

    def created(self, repo=REPO):
        return self.store["repos"][repo]["issues"]

    def advance(self, minutes):
        when = datetime.datetime.strptime(self.store["now"], STAMP) + datetime.timedelta(minutes=minutes)
        self.store["now"] = when.strftime(STAMP)

    def someone_else(self, title, repo=REPO, login="sam-fixture"):
        return self._create(repo, {"title": title, "body": "Filed by somebody else."}, login)

    def _create(self, repo, payload, login, drop_labels=False):
        about = self.store["repos"][repo]
        number = about["newest_issue"] + 1
        about["newest_issue"] = number
        milestone = next((row for row in about["milestones"] if row["number"] == payload.get("milestone")), None)
        known = {row["name"].lower(): row for row in about["labels"]}
        labels = []
        for name in ([] if drop_labels else payload.get("labels", [])):
            if name.lower() not in known:               # GitHub creates a label that does not exist
                known[name.lower()] = {"id": self.store["next_id"], "name": name}
                about["labels"].append(known[name.lower()])
                self.store["next_id"] += 1
            labels.append(known[name.lower()]["name"])
        issue = {"number": number, "id": self.store["next_id"], "node_id": "I_kwFX%d%04d" % (about["id"], number), "title": payload.get("title"),
                 "body": payload.get("body"), "state": "open", "labels": labels,
                 "assignees": [] if drop_labels else [one for one in payload.get("assignees", []) if one.lower() in [who.lower() for who in about["assignable"]]],
                 "milestone": None if drop_labels or not milestone else {"number": milestone["number"], "title": milestone["title"]},
                 "user": login, "created_at": self.store["now"]}
        self.store["next_id"] += 1
        about["issues"][str(number)] = issue
        return issue

    def _issue_json(self, repo, issue):
        return {"number": issue["number"], "id": issue["id"], "node_id": issue["node_id"], "title": issue["title"], "body": issue["body"], "state": issue["state"],
                "html_url": "https://github.com/%s/issues/%d" % (repo, issue["number"]), "repository_url": "%s/repos/%s" % (API, repo),
                "labels": [{"id": 7000, "name": name} for name in issue["labels"]], "assignees": [{"login": login, "id": 9000} for login in issue["assignees"]],
                "milestone": issue["milestone"], "user": {"login": issue["user"], "id": 9001}, "created_at": issue["created_at"], "updated_at": issue["created_at"]}

    def send(self, method, path, params=None, body=None):
        found = re.match(r"^/repos/([^/]+/[^/]+)/issues$", path)
        if method != "POST" or not found or found.group(1) not in self.store["repos"]:
            return super().send(method, path, params, body)
        if self.before:
            self.before(method, path)
        self.calls.append([method, path])
        headers = self._date()
        repo, mode = found.group(1), self.store["mode"]
        if mode == "never-arrived":
            self.save()
            raise TimeoutError("made-up: the request never reached GitHub")
        about = self.store["repos"][repo]
        if mode == "refused" or about["archived"]:
            self.save()
            return 403, headers, {"message": "Resource not accessible by personal access token"}
        try:
            payload = json.loads(body.decode("utf-8") if isinstance(body, bytes) else json.dumps(body))
        except ValueError:
            self.save()
            return 400, headers, {"message": "Problems parsing JSON"}
        if not isinstance(payload.get("title"), str) or not payload["title"].strip() or set(payload) - {"title", "body", "labels", "assignees", "milestone"}:
            self.save()
            return 422, headers, {"message": "Validation Failed"}
        if payload.get("milestone") is not None and payload["milestone"] not in [row["number"] for row in about["milestones"]]:
            self.save()
            return 422, headers, {"message": "Validation Failed"}
        issue = self._create(repo, payload, self.store["me"]["login"], drop_labels=mode == "drop-labels")
        self.store.setdefault("received", []).append(body.decode("utf-8") if isinstance(body, bytes) else json.dumps(body))
        self.save()
        if mode == "lost-answer":
            raise TimeoutError("made-up: the issue was created, and the answer was lost on the way back")
        return 201, headers, self._issue_json(repo, issue)

    def _date(self):
        import email.utils
        return {"Date": email.utils.format_datetime(datetime.datetime.strptime(self.store["now"], STAMP).replace(tzinfo=datetime.timezone.utc), usegmt=True)}

    def _answer(self, path, params):
        found = re.match(r"^/repos/([^/]+/[^/]+)/issues(?:/(\d+))?$", path)
        if not found or found.group(1) not in self.store["repos"]:
            return super()._answer(path, params)
        repo, about = found.group(1), self.store["repos"][found.group(1)]
        if found.group(2):
            issue = about["issues"].get(found.group(2))
            return (200, {}, self._issue_json(repo, issue)) if issue else (404, {}, {"message": "Not Found"})
        rows = [self._issue_json(repo, issue) for issue in sorted(about["issues"].values(), key=lambda one: -one["number"])]
        older = about["newest_issue"] - len(about["issues"])
        rows += [{"number": number, "node_id": "I_kwFX%04d" % number, "title": "Made-up older issue %d" % number, "body": None, "user": {"login": "sam-fixture"},
                  "created_at": "2026-11-01T00:00:00Z", "state": "open"} for number in range(older, 0, -1)]
        if params.get("creator"):
            rows = [row for row in rows if row["user"]["login"].lower() == params["creator"].lower()]
        if params.get("since"):
            rows = [row for row in rows if row["created_at"] >= params["since"]]
        return self._paged(path, params, rows)


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
    if command == "mode" and rest and rest[0] in MODES:
        fake.store["mode"] = rest[0]
        print("made-up GitHub: the next create will go: %s" % rest[0])
    elif command == "advance":
        fake.advance(int(rest[0]))
        print("made-up GitHub: %d minutes passed. GitHub's clock now says %s" % (int(rest[0]), fake.store["now"]))
    elif command == "someone-else":
        issue = fake.someone_else(rest[0])
        print("made-up GitHub: another person, sam-fixture, filed issue %d with the title %s" % (issue["number"], json.dumps(rest[0])))
    elif command == "show":
        issues = fake.created()
        print("made-up GitHub: %s: newest issue number %d. Issues created since the store was made: %d" % (REPO, fake.repo()["newest_issue"], len(issues)))
        for number in sorted(issues, key=int):
            one = issues[number]
            print("made-up GitHub:   issue %s, node ID %s, by %s: %s, labels %s, assignees %s, milestone %s"
                  % (number, one["node_id"], one["user"], json.dumps(one["title"]), json.dumps(one["labels"]), json.dumps(one["assignees"]),
                     json.dumps(one["milestone"]["title"]) if one["milestone"] else "none"))
        print("made-up GitHub: writes received so far, to any repository: %d" % len(fake.writes()))
    else:
        print(__doc__)
        return 1
    fake.save()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
