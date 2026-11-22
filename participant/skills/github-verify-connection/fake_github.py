"""A made-up GitHub for the github-verify-connection skill and its tests.

Nothing here contacts GitHub. The account, its repositories and their contents
are invented. It answers the read requests the skill sends to api.github.com,
with answers shaped like GitHub's.

The made-up account can see four repositories. What a connection can reach
depends on the made-up token it uses, chosen with `case`:

    fine-grained    a token limited to tracker and empty-start. GitHub reports no scopes for it.
                    Like any token it can also see the account's one public repository, notes
    lost-access     the same token a week later, after tracker was taken out of it
    issues-refused  the same token, after its permission to read issues was taken away
    classic-wide    an older kind of token that reaches everything, with scopes wider than reading needs
    renamed         the fine-grained token, after tracker was renamed
    rejected        a token GitHub no longer accepts
"""
import re
import urllib.parse

API = "https://api.github.com"
ME = {"login": "robin-fixture", "id": 9001}
TRACKER, EMPTY = "acme-fixture/tracker", "acme-fixture/empty-start"
PAYROLL, NOTES_REPO = "acme-fixture/payroll", "robin-fixture/notes"
NOWHERE = "acme-fixture/nowhere"            # there is no such repository
RENAMED_TO = "acme-fixture/issue-tracker"
CASES = ("fine-grained", "lost-access", "issues-refused", "classic-wide", "renamed", "rejected")
NOW = "Fri, 20 Nov 2026 09:00:00 GMT"
MAX_PER_PAGE = 100


class FakeGitHub:
    def __init__(self, case="fine-grained"):
        if case not in CASES:
            raise ValueError(case)
        self.case = case
        self.calls = []                     # every request received, as (path, params)
        self.repos = {
            TRACKER: {"id": 301, "private": True, "issues": 12, "pulls": 3, "files": 4, "push": True},
            EMPTY: {"id": 302, "private": True, "issues": 0, "pulls": 0, "files": 0, "push": True},
            PAYROLL: {"id": 303, "private": True, "issues": 5, "pulls": 1, "files": 9, "push": False},
            NOTES_REPO: {"id": 304, "private": False, "issues": 2, "pulls": 0, "files": 3, "push": True},
        }
        self.granted = {TRACKER, EMPTY}
        self.scopes = None                  # the X-OAuth-Scopes header, sent only for a classic token
        self.expires = "2026-11-27 09:00:00 UTC"
        self.refused = set()                # (repository, part) pairs GitHub answers 403 for
        self.list_status = 200
        self.leak = None                    # text put into an answer, to test the scan of the output
        self._failures = []
        if case == "lost-access":
            self.granted = {EMPTY}
        elif case == "issues-refused":
            self.refused = {(TRACKER, "issues"), (EMPTY, "issues")}
        elif case == "classic-wide":
            self.granted, self.scopes, self.expires = set(self.repos), "delete_repo, read:org, repo, workflow", None
        elif case == "renamed":
            self.repos[RENAMED_TO] = self.repos.pop(TRACKER)
            self.granted = {RENAMED_TO, EMPTY}

    def visible(self):
        """What a token can see: the repositories it was given, and every public one, whatever it was given."""
        return set(self.granted) | {name for name, repo in self.repos.items() if not repo["private"]}

    def fail(self, path_prefix, status, times=1):
        self._failures.append({"prefix": path_prefix, "status": status, "times": times})

    def bulk(self, name, issues):
        self.repos[name]["issues"] = issues

    def get(self, path, params=None):
        params = dict(params or {})
        self.calls.append((path, params))
        status, headers, body = None, {}, None
        for rule in self._failures:
            if path.startswith(rule["prefix"]) and rule["times"] > 0:
                rule["times"] -= 1
                status, body = rule["status"], {"message": "made-up failure"}
                break
        if status is None:
            if self.case == "rejected":
                status, body = 401, {"message": "Bad credentials"}
            else:
                status, headers, body = self._answer(path, params)
        headers = dict(headers, Date=NOW)
        if self.case != "rejected":
            if self.scopes is not None:
                headers["X-OAuth-Scopes"] = self.scopes
            if self.expires:
                headers["GitHub-Authentication-Token-Expiration"] = self.expires
        return status, headers, body

    def _repo_json(self, name):
        repo = self.repos[name]
        return {"id": repo["id"], "node_id": "R_kwFX%d" % repo["id"], "full_name": name, "private": repo["private"],
                "permissions": {"admin": False, "push": repo["push"], "pull": True}}

    def _paged(self, path, params, rows):
        per_page = min(int(params.get("per_page", 30)), MAX_PER_PAGE)
        page = int(params.get("page", 1))
        start, headers = (page - 1) * per_page, {}
        if start + per_page < len(rows):
            query = urllib.parse.urlencode(dict(params, per_page=per_page, page=page + 1))
            headers["Link"] = '<%s%s?%s>; rel="next"' % (API, path, query)
        return 200, headers, rows[start:start + per_page]

    def _answer(self, path, params):
        if path == "/user":
            return 200, {}, {"login": self.leak or ME["login"], "id": ME["id"], "type": "User"}
        if path == "/user/repos":
            if self.list_status != 200:
                return self.list_status, {}, {"message": "made-up refusal"}
            return self._paged(path, params, [self._repo_json(name) for name in sorted(self.visible())])
        found = re.match(r"^/repos/([^/]+/[^/]+)(?:/(issues|pulls|contents))?$", path)
        if not found:
            return 404, {}, {"message": "Not Found"}
        name, part = found.group(1), found.group(2)
        if self.case == "renamed" and name == TRACKER:
            return 301, {"Location": "%s/repositories/301%s" % (API, "/" + part if part else "")}, {"message": "Moved Permanently"}
        if name not in self.visible():
            return 404, {}, {"message": "Not Found"}       # GitHub does not say which of the two it is
        if (name, part) in self.refused:
            return 403, {}, {"message": "Resource not accessible by personal access token"}
        repo = self.repos[name]
        if part is None:
            return 200, {}, self._repo_json(name)
        if part == "issues":
            rows = [{"number": n, "node_id": "I_kwFX%d%04d" % (repo["id"], n), "title": "Made-up issue %d" % n} for n in range(1, repo["issues"] + 1)]
            rows += [{"number": 500 + n, "node_id": "PR_kwFX%d%04d" % (repo["id"], n), "title": "Made-up change %d" % n,
                      "pull_request": {"url": "%s/repos/%s/pulls/%d" % (API, name, 500 + n)}} for n in range(repo["pulls"])]
            return self._paged(path, params, rows)
        if part == "pulls":
            return self._paged(path, params, [{"number": 500 + n, "node_id": "PR_kwFX%d%04d" % (repo["id"], n)} for n in range(repo["pulls"])])
        if repo["files"] == 0:
            return 404, {}, {"message": "This repository is empty."}
        return 200, {}, [{"name": "file-%d.md" % n, "type": "file"} for n in range(repo["files"])]
