#!/usr/bin/env python3
"""Checks a GitHub connection before anything trusts it. Read-only.

See SKILL.md in this folder for what it does and the rules it follows.

    verify.py --source fake [--fake-case CASE] --expect OWNER/NAME [--expect OWNER/NAME ...]
    verify.py --source live --expect OWNER/NAME [--expect OWNER/NAME ...]

It says who the connection acts as, what GitHub reports it may do, which
repositories it can reach, and whether each repository it is EXPECTED to reach
can in fact be read. It writes no file. Everything it prints is held back until
the end and scanned for the credential first.

It only ever sends GET requests. There is no code here that creates, changes
or deletes anything in GitHub, and it does not try a write to find out whether
one would be allowed.

Exit codes: 0 every expected repository can be read; 1 the check could not be made; 3 an expected
repository cannot be read, or the output had to be redacted.
"""
import argparse
import datetime
import email.utils
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

API_HOST = "api.github.com"
PER_PAGE = 100
MAX_LIST_PAGES = 10
REPO_NAME = re.compile(r"^[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}$")
# Anything shaped like a GitHub token. The scan of the output looks for this, and for the token's own value.
TOKEN_SHAPED = re.compile(r"(gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})")
# The reads tried on each expected repository: (word, the end of the address, whether the check needs it).
READS = (("repository", "", True), ("issues", "/issues", True), ("pull requests", "/pulls", False), ("files", "/contents", False))
SAME_ANSWER = ("GitHub gives this same answer for a repository that does not exist and for one this connection "
               "may not see, so the two cannot be told apart from here")


class Stop(Exception):
    """The check cannot be made. The message says why, in plain words."""


class Report:
    """Everything the check says. Nothing is printed until it has been scanned (criterion 6)."""

    def __init__(self):
        self.lines = []

    def say(self, text=""):
        self.lines.append("github-verify: " + text if text else "")

    def finish(self, token):
        """Scan every line for the credential, then print. Returns True when nothing had to be redacted."""
        found = 0
        for index, line in enumerate(self.lines):
            clean = line.replace(token, "[REDACTED]") if token else line
            clean = TOKEN_SHAPED.sub("[REDACTED]", clean)
            if clean != line:
                self.lines[index], found = clean, found + 1
        self.say("7. SCAN OF THIS OUTPUT. %d lines were scanned before any was printed, for %sanything shaped like a "
                 "GitHub token. %s" % (len(self.lines), "the token's own value and for " if token else "",
                                       "Nothing was found" if not found else
                                       "FOUND in %d line%s, and replaced with [REDACTED]. Treat the token as exposed and revoke it"
                                       % (found, "" if found == 1 else "s")))
        print("\n".join(self.lines), flush=True)
        return not found


def plural(count, word, many=None):
    return "%d %s" % (count, word if count == 1 else many or word + "s")


def good_repo(name):
    return bool(isinstance(name, str) and REPO_NAME.match(name) and not set(name.split("/")) & {".", ".."})


# ---------------------------------------------------------------- talking to GitHub


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None            # a redirect comes back as an answer. The check reports it and does not follow it


def live_get(path, params=None):
    """One GET to api.github.com. Returns (status, headers, body).

    The token comes from the environment and goes in a request header. It is
    never part of an address, and it is never printed, returned or written.
    """
    url = "https://%s%s" % (API_HOST, path)
    if params:
        url += "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, method="GET")
    request.add_header("Authorization", "Bearer %s" % os.environ.get("GITHUB_TOKEN"))
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("X-GitHub-Api-Version", "2022-11-28")
    request.add_header("User-Agent", "github-verify-connection-skill")
    try:
        with urllib.request.build_opener(_NoRedirect).open(request, timeout=20) as response:
            return response.status, dict(response.headers), json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        text = err.read().decode("utf-8", "replace")
        try:
            body = json.loads(text)
        except ValueError:
            body = {"message": text[:200]}
        return err.code, dict(err.headers), body
    except (urllib.error.URLError, OSError) as err:
        raise Stop("could not reach GitHub: %s" % getattr(err, "reason", err))
    except ValueError:
        raise Stop("GitHub's answer to %s was not JSON" % path)


class Client:
    """Every request the check makes goes through here, and is written down. It can only read."""

    def __init__(self, get):
        self._get = get
        self.made = []         # every request, as "GET <path>"

    def get(self, path, params=None):
        status, headers, body = self._get(path, dict(params or {}))
        self.made.append("GET %s" % path)
        head = {str(name).lower(): str(value) for name, value in (headers or {}).items()}
        if status == 401:
            raise Stop("GitHub rejected the token (401). It may be mistyped, revoked or expired. Nothing can be said "
                       "about what it reaches")
        if status == 429 or (status == 403 and (head.get("x-ratelimit-remaining") == "0" or "retry-after" in head)):
            raise Stop("GitHub is rate-limiting this connection, so the check could not be finished. Run it again later")
        return status, head, body


# ---------------------------------------------------------------- the parts of the check


def who(client, report):
    """Criterion 1: ask GitHub who the token belongs to. No login is given to the check."""
    status, head, body = client.get("/user")
    if status != 200 or not isinstance(body, dict) or not isinstance(body.get("login"), str) or not isinstance(body.get("id"), int):
        raise Stop("GitHub did not say who the connection acts as (status %d)" % status)
    report.say('1. WHO. The connection acts as login %s, user id %d. GitHub was asked "who am I?". No login was typed in '
               "or given to the check" % (body["login"], body["id"]))
    return head


def read_only_scope(scope):
    return scope.startswith("read:") or scope in ("repo:status", "public_repo:status")


def what_it_may_do(head, report):
    """Criterion 2: the scopes or permissions GitHub reports. Returns the scopes that allow more than reading."""
    wide = []
    if "x-oauth-scopes" in head:
        scopes = sorted(scope.strip() for scope in head["x-oauth-scopes"].split(",") if scope.strip())
        report.say("2. WHAT IT MAY DO. The scopes GitHub reports for this connection are: %s" % (", ".join(scopes) or "none"))
        for scope in scopes:
            if read_only_scope(scope):
                report.say("     scope %s: read-only" % scope)
            else:
                wide.append(scope)
                report.say("     scope %s: ALLOWS MORE THAN READING. Broader than this check, or any read-only sync, needs" % scope)
        if wide:
            report.say("     %s broader than reading needs. A fine-grained token with read-only permissions on chosen "
                       "repositories would be narrower" % plural(len(wide), "scope is", "scopes are"))
    else:
        report.say("2. WHAT IT MAY DO. GitHub reports no scopes for this token, as it does for a fine-grained token. "
                   "GitHub does not tell a fine-grained token its own permissions. What it may READ is tried in part 4. "
                   "Whether it may write is NOT tested, because that would mean trying a write")
    expires = head.get("github-authentication-token-expiration")
    if expires:
        left = ""
        try:
            end = datetime.datetime.strptime(expires.replace(" UTC", ""), "%Y-%m-%d %H:%M:%S").replace(tzinfo=datetime.timezone.utc)
            days = (end - email.utils.parsedate_to_datetime(head["date"])).total_seconds() / 86400
            left = ", %s from now by GitHub's clock" % ("%.1f days" % days if days >= 0 else "already past")
        except (KeyError, TypeError, ValueError):
            pass
        report.say("     the token expires: %s%s. After that every request is rejected" % (expires, left))
    else:
        report.say("     the token expires: GitHub reports no expiry date for it")
    return wide


def reachable(client, report):
    """Criterion 3: the repositories GitHub lists for this connection, by full name. Returns the names, or None."""
    names, page = [], 1
    while True:
        status, head, body = client.get("/user/repos", {"per_page": PER_PAGE, "page": page})
        if status != 200 or not isinstance(body, list):
            report.say("3. REPOSITORIES GITHUB LISTS FOR THIS CONNECTION. THE LIST COULD NOT BE READ (status %d). This is "
                       "not the same as an empty list: nothing is known about what it lists" % status)
            return None
        rows = [row for row in body if isinstance(row, dict) and good_repo(row.get("full_name"))]
        names += [(row["full_name"], bool(row.get("private")), row.get("permissions") if isinstance(row.get("permissions"), dict) else {})
                  for row in rows]
        if 'rel="next"' not in head.get("link", "") or page == MAX_LIST_PAGES:
            more = 'rel="next"' in head.get("link", "")
            break
        page += 1
    report.say("3. REPOSITORIES GITHUB LISTS FOR THIS CONNECTION: %d%s" % (
        len(names), ". THERE ARE MORE: the check stops listing after %d" % len(names) if more else ""))
    for name, private, may in sorted(names):
        words = [word for word, key in (("read", "pull"), ("write", "push"), ("administer", "admin")) if may.get(key)]
        report.say("     %s, %s. GitHub says the ACCOUNT may: %s" % (name, "private" if private else "public", ", ".join(words) or "not stated"))
    if not names:
        report.say("     none. GitHub answered, and its list is empty")
    public = sum(not private for _, private, _ in names)
    if public:
        report.say("     note: %d of these %s public. A public repository is listed, and can be read, whatever the token was "
                   "given. Being listed here does not show that the token was granted it" % (public, "is" if public == 1 else "are"))
    if any(may.get("push") or may.get("admin") for _, _, may in names):
        report.say("     note: that is what the account may do. GitHub does not say here whether this TOKEN may write")
    return [name for name, _, _ in names]


def try_reads(client, name):
    """The reads tried on one expected repository. Returns a list of (word, needed, outcome, detail)."""
    results = []
    for word, end, needed in READS:
        params = {"per_page": PER_PAGE, "state": "all"} if word in ("issues", "pull requests") else {}
        status, head, body = client.get("/repos/%s%s" % (name, end), params)
        if status in (301, 302, 307, 308):
            results.append((word, needed, "moved", status))
        elif word == "files" and status == 404 and "empty" in str((body or {}).get("message", "")).lower():
            results.append((word, needed, "ok", "none: GitHub says the repository is empty"))
        elif status != 200:
            results.append((word, needed, "refused", status))
        elif word == "repository":
            results.append((word, needed, "ok", "id %s, %s" % (body.get("id"), "private" if body.get("private") else "public")))
        else:
            rows = [row for row in body if isinstance(row, dict) and not (word == "issues" and "pull_request" in row)] if isinstance(body, list) else []
            more = 'rel="next"' in head.get("link", "")
            results.append((word, needed, "ok", "%d%s" % (len(rows), " on the first page, and there are more" if more else "")))
        if results[0][2] != "ok":
            break              # the repository itself cannot be read, so the other reads are not tried
    return results


def expected(client, report, names, listed):
    """Criterion 4: each repository the connection is expected to reach, read by name. Returns the ones that fail."""
    report.say("4. REPOSITORIES THIS CONNECTION IS EXPECTED TO REACH: %d. Each is asked for by name" % len(names))
    failed, first_read = [], None
    for name in names:
        results = try_reads(client, name)
        word, _, outcome, detail = results[0]
        if outcome == "moved":
            failed.append(name)
            report.say("     %s: MOVED (status %s). GitHub redirects this name, so the repository was renamed or transferred. "
                       "The check does not follow it. Not counted as readable" % (name, detail))
            continue
        if outcome == "refused":
            failed.append(name)
            report.say("     %s: INACCESSIBLE (status %s). Nothing in it could be read. This is NOT an empty repository%s"
                       % (name, detail, ". " + SAME_ANSWER if detail == 404 else ""))
            continue
        ok = ["%s (%s)" % (word, detail) for word, _, outcome, detail in results if outcome == "ok"]
        refused = [(word, needed, detail) for word, needed, outcome, detail in results if outcome != "ok"]
        report.say("     %s: REACHABLE. Reads allowed: %s" % (name, "; ".join(ok)))
        for word, needed, status in refused:
            report.say("       %s: REFUSED (status %s). %s" % (word, status, "The check needs this read, so the repository "
                       "is counted as NOT readable. This is not the same as having no %s" % word if needed else
                       "Not needed by the check, so this is only reported"))
        if any(needed for _, needed, _ in refused):
            failed.append(name)
        elif first_read is None:
            first_read = (name, dict((word, detail) for word, _, _, detail in results)["issues"])
        if listed is not None and name not in listed:
            report.say("       note: it can be read by name, and GitHub's list in part 3 does not include it")
    return failed, first_read


def run(client, report, expect):
    head = who(client, report)
    wide = what_it_may_do(head, report)
    listed = reachable(client, report)
    failed, first_read = expected(client, report, expect, listed)
    if first_read:
        report.say("5. ONE SAFE READ. The issues of %s were asked for and GitHub returned %s. Only the count was used. "
                   "No title or text was kept or printed" % first_read)
    else:
        report.say("5. ONE SAFE READ. NOT MADE: no expected repository could be read")
    kinds = sorted({line.split()[0] for line in client.made})
    report.say("6. ONLY READS. %d requests were made, and every one was a %s. No write was tried, not even to see "
               "whether it would be refused:" % (len(client.made), " or ".join(kinds)))
    for line in client.made:
        report.say("     " + line)
    report.say("RESULT: %s%s" % (
        "every expected repository can be read" if not failed else
        "%s CANNOT be read: %s" % (plural(len(failed), "expected repository", "expected repositories"), ", ".join(failed)),
        ". %s broader than reading needs" % plural(len(wide), "scope is", "scopes are") if wide else ""))
    return 3 if failed else 0


def main(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(description="Check a GitHub connection: who, what it may do, what it can reach. Read-only.")
    parser.add_argument("--source", choices=("live", "fake"), required=True)
    parser.add_argument("--expect", action="append", default=[], metavar="OWNER/NAME",
                        help="a repository the connection is expected to reach. Give it once for each repository")
    parser.add_argument("--fake-case", default="fine-grained", help="with --source fake: which made-up token to use")
    args = parser.parse_args(argv)
    report, token, code = Report(), None, 1
    try:
        if not args.expect:
            raise Stop("give at least one --expect OWNER/NAME: a repository this connection should be able to read. "
                       "Without one, a lost permission could not be told from nothing being there")
        if any(not good_repo(name) for name in args.expect):
            raise Stop("--expect takes a repository as owner/name")
        if args.source == "fake":
            sys.path.insert(0, here)
            import fake_github
            if args.fake_case not in fake_github.CASES:
                raise Stop("--fake-case is one of: %s" % ", ".join(fake_github.CASES))
            report.say("source: a made-up GitHub, fake_github.py, with the made-up token \"%s\". No request leaves this machine" % args.fake_case)
            client = Client(fake_github.FakeGitHub(args.fake_case).get)
        else:
            token = os.environ.get("GITHUB_TOKEN")
            if not token:
                raise Stop("the environment variable GITHUB_TOKEN is not set")
            report.say("source: GitHub, with the token in the environment variable GITHUB_TOKEN")
            client = Client(live_get)
        code = run(client, report, args.expect)
    except Stop as stop:
        report.say("STOPPED: %s." % stop)
        report.say("RESULT: the check could not be made. That is not the same as the connection being fine")
    return code if report.finish(token) else 3


if __name__ == "__main__":
    sys.exit(main())
