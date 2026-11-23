#!/usr/bin/env python3
"""A made-up GitHub for the github-create-issue-preview skill and its tests.

Nothing here contacts GitHub. The repositories, people, labels, milestones and
templates are invented. It answers the read requests the preview sends to
api.github.com, with answers shaped like GitHub's.

It keeps everything in one JSON file, the store, so that a recording can open
the file before and after a preview and see that nothing in it changed.

    fake_github.py STORE new      make a fresh store
    fake_github.py STORE show     print what the tracker repository holds, and every request received that was not a GET

What is in a fresh store:

    acme-fixture/tracker      the sandbox. It has an issue template, bug_report.md, six labels, three milestones
    acme-fixture/production   a repository that exists and is not on the sandbox allowlist

It refuses every request that is not a GET, with status 403, and remembers that it was asked.
"""
import base64
import copy
import datetime
import email.utils
import json
import os
import re
import sys
import urllib.parse

API = "https://api.github.com"
REPO, OTHER = "acme-fixture/tracker", "acme-fixture/production"
START = "2026-11-24T09:00:00Z"
STAMP = "%Y-%m-%dT%H:%M:%SZ"
MAX_PER_PAGE = 100
TEMPLATE_FOLDER = ".github/ISSUE_TEMPLATE"

BUG_TEMPLATE = "\n".join([
    "---", "name: Bug report", "about: Something does not work as it should", "title: ''", "labels: bug", "assignees: ''", "---", "",
    "### What happened", "", "<!-- Say what you saw. Quote any error text exactly. -->", "",
    "### Steps to reproduce", "", "1.", "",
    "### What you expected", "", "<!-- Say what should have happened. -->", "",
    "### Environment (optional)", "", "<!-- Version, file names, anything else that helps. -->", ""])


def fresh():
    def repo(rid):
        return {"id": rid, "private": True, "archived": False, "has_issues": True,
                "permissions": {"admin": False, "maintain": False, "push": True, "triage": True, "pull": True},
                "labels": [{"id": 7001, "name": "bug"}, {"id": 7011, "name": "export"}, {"id": 7012, "name": "performance"},
                           {"id": 7013, "name": "auth"}, {"id": 7004, "name": "docs"}, {"id": 7005, "name": "enhancement"}],
                "milestones": [{"number": 1, "title": "Sprint 12", "state": "closed"}, {"number": 3, "title": "Sprint 13", "state": "open"},
                               {"number": 4, "title": "Sprint 14", "state": "open"}],
                "assignable": ["robin-fixture", "kit-fixture", "sam-fixture"],
                "templates": {"bug_report.md": BUG_TEMPLATE},
                "newest_issue": 107}
    return {"now": START, "me": {"login": "robin-fixture", "id": 9001}, "scopes": None, "repos": {REPO: repo(401), OTHER: repo(402)}, "calls": []}


def load(path):
    with open(path, encoding="utf-8") as f:
        return FakeGitHub(json.load(f), path)


class FakeGitHub:
    def __init__(self, store=None, path=None):
        self.store = store if store is not None else fresh()
        self.path = path
        self.before = None                  # called with (method, path) before each answer
        self._failures = []

    def save(self):
        if self.path:
            with open(self.path + ".tmp", "w", encoding="utf-8") as f:
                json.dump(self.store, f, indent=1, sort_keys=True)
            os.replace(self.path + ".tmp", self.path)

    @property
    def calls(self):
        return self.store["calls"]

    def not_gets(self):
        return [call for call in self.calls if call[0] != "GET"]

    def repo(self, name=REPO):
        return self.store["repos"][name]

    def snapshot(self):
        return copy.deepcopy(self.store["repos"])

    def fail(self, path_prefix, status, times=1, headers=None):
        self._failures.append({"prefix": path_prefix, "status": status, "times": times, "headers": headers or {}})

    def send(self, method, path, params=None, body=None):
        params = dict(params or {})
        if self.before:
            self.before(method, path)
        self.calls.append([method, path])
        headers = {"Date": email.utils.format_datetime(datetime.datetime.strptime(self.store["now"], STAMP).replace(tzinfo=datetime.timezone.utc), usegmt=True)}
        if self.store["scopes"] is not None:
            headers["X-OAuth-Scopes"] = self.store["scopes"]
        for rule in self._failures:
            if path.startswith(rule["prefix"]) and rule["times"] > 0:
                rule["times"] -= 1
                self.save()
                return rule["status"], dict(headers, **rule["headers"]), {"message": "made-up failure"}
        status, more, answer = (403, {}, {"message": "this made-up GitHub accepts only GET"}) if method != "GET" else self._answer(path, params)
        self.save()
        return status, dict(headers, **more), copy.deepcopy(answer)

    def _paged(self, path, params, rows):
        per_page = min(int(params.get("per_page", 30)), MAX_PER_PAGE)
        page = int(params.get("page", 1))
        start, headers = (page - 1) * per_page, {}
        if start + per_page < len(rows):
            headers["Link"] = '<%s%s?%s>; rel="next"' % (API, path, urllib.parse.urlencode(dict(params, per_page=per_page, page=page + 1)))
        return 200, headers, rows[start:start + per_page]

    def _answer(self, path, params):
        if path == "/user":
            return 200, {}, dict(self.store["me"], type="User")
        found = re.match(r"^/repos/([^/]+/[^/]+)(/.*)?$", path)
        if not found or found.group(1) not in self.store["repos"]:
            return 404, {}, {"message": "Not Found"}
        name, rest = found.group(1), found.group(2) or ""
        about = self.store["repos"][name]
        if rest == "":
            return 200, {}, {"id": about["id"], "full_name": name, "private": about["private"], "archived": about["archived"],
                             "has_issues": about["has_issues"], "permissions": about["permissions"]}
        if rest == "/labels":
            return self._paged(path, params, [dict(row, color="ededed", description=None) for row in about["labels"]])
        if rest == "/milestones":
            wanted = params.get("state", "open")
            return self._paged(path, params, [row for row in about["milestones"] if wanted == "all" or row["state"] == wanted])
        if rest == "/issues":
            newest = about["newest_issue"]
            return self._paged(path, params, [{"number": number, "node_id": "I_kwFX%04d" % number} for number in range(newest, 0, -1)] if newest else [])
        if rest.startswith("/assignees/"):
            login = urllib.parse.unquote(rest[len("/assignees/"):])
            return (204, {}, None) if login.lower() in [one.lower() for one in about["assignable"]] else (404, {}, {"message": "Not Found"})
        if rest == "/contents/" + TEMPLATE_FOLDER:
            if not about["templates"]:
                return 404, {}, {"message": "Not Found"}
            return 200, {}, [{"name": one, "path": "%s/%s" % (TEMPLATE_FOLDER, one), "type": "file"} for one in sorted(about["templates"])]
        if rest.startswith("/contents/%s/" % TEMPLATE_FOLDER):
            one = urllib.parse.unquote(rest.rsplit("/", 1)[1])
            if one not in about["templates"]:
                return 404, {}, {"message": "Not Found"}
            encoded = base64.encodebytes(about["templates"][one].encode("utf-8")).decode("ascii")      # with line breaks, as GitHub sends it
            return 200, {}, {"name": one, "path": "%s/%s" % (TEMPLATE_FOLDER, one), "type": "file", "encoding": "base64", "content": encoded}
        return 404, {}, {"message": "Not Found"}


def main(argv):
    if len(argv) < 2 or argv[1] not in ("new", "show"):
        print(__doc__)
        return 1
    if argv[1] == "new":
        FakeGitHub(fresh(), argv[0]).save()
        print("made-up GitHub: a fresh store was made")
        return 0
    fake = load(argv[0])
    about = fake.repo()
    print("made-up GitHub: %s: newest issue number %d, %d labels, %d milestones, %d template(s)"
          % (REPO, about["newest_issue"], len(about["labels"]), len(about["milestones"]), len(about["templates"])))
    print("made-up GitHub: requests received so far: %d. Of those, not a GET: %d" % (len(fake.calls), len(fake.not_gets())))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
