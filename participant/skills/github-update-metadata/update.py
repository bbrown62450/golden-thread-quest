#!/usr/bin/env python3
"""Change the labels, assignees or milestone of one GitHub issue, after a preview and a person's confirmation.

See SKILL.md in this folder for what it does and the rules it follows.

    update.py preview --source fake|live --repo OWNER/NAME --issue N --change FIELD=VALUE [--change ...]
                      --allowlist FILE --state FOLDER [--fake-store FILE]
    update.py confirm (the same arguments) --fingerprint F --confirmed-by NAME [--results FOLDER]

FIELD is one of: label.add, label.remove, assignee.add, assignee.remove, milestone.set, milestone.clear (=yes).

`preview` only reads. It has no way to write. `confirm` writes, and only what the preview with that fingerprint
showed, and only if the issue's labels, assignees and milestone are still what the preview showed.

Exit codes: 0 preview ready, nothing to change, or update done; 1 refused or stopped, nothing written;
2 rate-limited before any write, nothing written; 3 something was written and needs a person to look.
"""
import argparse
import datetime
import email.utils
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API_HOST = "api.github.com"
PER_PAGE = 100
LIMIT_MINUTES = 15         # how long a preview may be confirmed for, by GitHub's clock
MAX_CHANGES = 10
MAX_ASSIGNEES = 10         # GitHub's own limit for one issue
MAX_WAITS = 3
MAX_WAIT_SECONDS = 15
DEFAULT_WAIT_SECONDS = 10
PREVIEW_FORMAT = "github-update-preview/1"
STAMP = "%Y-%m-%dT%H:%M:%SZ"
NODE_ID = re.compile(r"^[A-Za-z0-9_=-]{1,120}$")
REPO_NAME = re.compile(r"^[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}$")
FINGERPRINT = re.compile(r"^[0-9a-f]{32}$")
LOGIN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")
EMAIL_SHAPED = re.compile(r"[^\s@]+@[^\s@]+\.[^\s@]+")
PULL_REQUEST_RULE = "an item is a pull request when it carries a `pull_request` key, and only then"

# The only things this workflow may change, and how each is asked for.
SUPPORTED = ("label.add", "label.remove", "assignee.add", "assignee.remove", "milestone.set", "milestone.clear")
# Things a person might ask for that it refuses, each with the reason.
NOT_SUPPORTED = {
    "title": "the title is content, not metadata. This workflow does not change what an issue says",
    "body": "the body is content, not metadata. This workflow does not change what an issue says",
    "state": "closing or reopening an issue is a decision, not metadata. A person does that on GitHub",
    "locked": "locking a conversation is a moderation decision. A person does that on GitHub",
    "type": "the issue type is set by the organization's own rules. This workflow does not change it",
    "label.set": "replacing the whole list of labels is how a label that someone else added gets removed. Ask for label.add and label.remove, one label at a time",
    "label.create": "this workflow does not create labels. A label must already exist in the repository",
    "assignee.set": "replacing the whole list of assignees could remove someone another person assigned. Ask for assignee.add and assignee.remove",
    "milestone.create": "this workflow does not create milestones. A milestone must already exist and be open",
    "project": "project fields live in GitHub Projects, outside the repository. Changing them needs a wider token than this workflow is given, so it does not change them",
}
EVENTS_OF_INTEREST = ("labeled", "unlabeled", "assigned", "unassigned", "milestoned", "demilestoned")


class Stop(Exception):
    """The run cannot go on. Nothing was written."""


class Refused(Exception):
    """The workflow will not do this. Nothing was written."""


class RateLimited(Exception):
    """GitHub kept answering with a rate limit after every allowed wait."""


def say(text=""):
    print(("github-update: " + text) if text else "github-update:", flush=True)


def q(value):
    """A value from GitHub or from the command line, as it is printed: as JSON, so that it cannot break a line."""
    return json.dumps(value, ensure_ascii=False)


def plural(count, word, many=None):
    return "%d %s" % (count, word if count == 1 else many or word + "s")


def shown_path(path):
    try:
        relative = os.path.relpath(path)
    except ValueError:
        return os.path.basename(path)
    return os.path.basename(path) if relative.startswith("..") else relative


# ---------------------------------------------------------------- talking to GitHub


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def make_live(may_write):
    """The function that sends requests to api.github.com. Made for `preview`, it refuses to send anything but GET."""
    def send(method, path, params=None, body=None):
        if method != "GET" and not (may_write and method in ("POST", "PATCH", "DELETE")):
            raise RuntimeError("this command may not send %s" % method)
        url = "https://%s%s" % (API_HOST, path)
        if params:
            url += "?" + urllib.parse.urlencode(params)
        data = None if body is None else json.dumps(body).encode("utf-8")
        request = urllib.request.Request(url, data=data, method=method)
        request.add_header("Authorization", "Bearer %s" % os.environ.get("GITHUB_TOKEN"))
        request.add_header("Accept", "application/vnd.github+json")
        request.add_header("X-GitHub-Api-Version", "2022-11-28")
        request.add_header("User-Agent", "github-update-metadata-skill")
        if data is not None:
            request.add_header("Content-Type", "application/json")
        try:
            with urllib.request.build_opener(_NoRedirect).open(request, timeout=20) as response:
                text = response.read().decode("utf-8")
                return response.status, dict(response.headers), json.loads(text) if text.strip() else None
        except urllib.error.HTTPError as err:
            text = err.read().decode("utf-8", "replace")
            try:
                answer = json.loads(text) if text.strip() else None
            except ValueError:
                answer = {"message": text[:200]}
            return err.code, dict(err.headers), answer
        except (urllib.error.URLError, OSError) as err:
            raise Stop("could not reach GitHub: %s" % getattr(err, "reason", err))
        except ValueError:
            raise Stop("GitHub's answer to %s was not JSON" % path)
    return send


def lowered(headers):
    return {str(name).lower(): str(value) for name, value in (headers or {}).items()}


class Connection:
    """Every request goes through here. It can read. It can write only after `allow_writes` names one issue."""

    def __init__(self, send, sleep=time.sleep, clock=time.time):
        self._send, self._sleep, self._clock = send, sleep, clock
        self.asked = []            # (method, path) of every request answered, in order
        self.waits = []
        self.scopes = None
        self._writable = None      # the one issue path that may be written to

    def allow_writes(self, repo, number):
        self._writable = "/repos/%s/issues/%d" % (repo, number)

    def _once(self, method, path, params, body):
        waited = 0
        while True:
            status, headers, answer = self._send(method, path, params, body)
            self.asked.append((method, path))
            head = lowered(headers)
            if "x-oauth-scopes" in head:
                self.scopes = head["x-oauth-scopes"]
            limited = status == 429 or (status == 403 and (head.get("x-ratelimit-remaining") == "0" or "retry-after" in head))
            if not limited:
                return status, head, answer
            seconds = int(head["retry-after"]) if head.get("retry-after", "").isdigit() else (
                max(1, int(head["x-ratelimit-reset"]) - int(self._clock()) + 1) if head.get("x-ratelimit-reset", "").isdigit() else DEFAULT_WAIT_SECONDS)
            if seconds > MAX_WAIT_SECONDS or waited == MAX_WAITS:
                raise RateLimited()
            waited += 1
            say("rate limited by GitHub. Wait %d of %d: %d seconds" % (waited, MAX_WAITS, seconds))
            self._sleep(seconds)
            self.waits.append(seconds)

    def get(self, path, params=None):
        status, head, answer = self._once("GET", path, dict(params or {}), None)
        if status == 401:
            raise Stop("GitHub rejected the token (401). Check GITHUB_TOKEN. A token also stops working when it expires")
        if status in (301, 302, 307, 308):
            raise Stop("GitHub redirected %s. The repository was renamed or moved, and this workflow does not follow it" % path)
        return status, head, answer

    def write(self, method, path, body=None):
        """One write. Only POST, PATCH or DELETE, and only on the one issue that was allowed."""
        if self._writable is None:
            raise Refused("this command cannot write")
        if method not in ("POST", "PATCH", "DELETE") or not (path == self._writable or path.startswith(self._writable + "/")):
            raise Refused("a write outside the one issue of the preview was about to be sent, and was not")
        return self._once(method, path, None, body)

    def writes(self):
        return [(method, path) for method, path in self.asked if method != "GET"]


def github_time(head):
    """GitHub's own clock, from the Date header of one of its answers. This machine's clock is never used."""
    try:
        when = email.utils.parsedate_to_datetime(head["date"])
    except (KeyError, TypeError, ValueError):
        raise Stop("GitHub's answer carried no usable Date header, so its clock cannot be read")
    if when.tzinfo is None:
        when = when.replace(tzinfo=datetime.timezone.utc)
    return when.astimezone(datetime.timezone.utc).strftime(STAMP)


def minutes_between(earlier, later):
    parse = lambda stamp: datetime.datetime.strptime(stamp, STAMP)
    return (parse(later) - parse(earlier)).total_seconds() / 60.0


def read_all(conn, path, params, what):
    rows, seen, page = [], set(), 1
    while True:
        status, head, answer = conn.get(path, dict(params, per_page=PER_PAGE, page=page))
        if status != 200 or not isinstance(answer, list) or any(not isinstance(row, dict) for row in answer):
            raise Stop("GitHub did not return %s (status %d)" % (what, status))
        fresh = [row for row in answer if json.dumps(row, sort_keys=True) not in seen]
        rows += fresh
        seen.update(json.dumps(row, sort_keys=True) for row in fresh)
        if not any('rel="next"' in part for part in head.get("link", "").split(",")):
            return rows
        if not fresh:
            raise Stop("GitHub kept returning the same of %s, so the list cannot be trusted" % what)
        page += 1


def good_repo(name):
    return bool(isinstance(name, str) and REPO_NAME.match(name) and not set(name.split("/")) & {".", ".."})


def read_account(conn):
    status, _, answer = conn.get("/user")
    if status != 200 or not isinstance(answer, dict) or not isinstance(answer.get("login"), str):
        raise Stop("GitHub did not say who the connection acts as (status %d)" % status)
    return answer["login"]


def read_repo(conn, repo):
    status, _, answer = conn.get("/repos/%s" % repo)
    if status in (403, 404):
        raise Stop("GitHub does not show the repository to this connection (status %d)" % status)
    if status != 200 or not isinstance(answer, dict) or not isinstance(answer.get("id"), int):
        raise Stop("GitHub did not return the repository (status %d)" % status)
    if answer.get("full_name") != repo:
        raise Stop("GitHub knows the repository under another name than the one given. Give the name exactly as GitHub writes it")
    return answer


def read_issue(conn, repo, number):
    """The issue as it is now. Returns (snapshot, facts about it, GitHub's clock)."""
    status, head, answer = conn.get("/repos/%s/issues/%d" % (repo, number))
    if status in (403, 404, 410):
        raise Stop("GitHub does not show issue %d to this connection (status %d)" % (number, status))
    if status != 200 or not isinstance(answer, dict):
        raise Stop("GitHub did not return the issue (status %d)" % status)
    if answer.get("number") != number or not isinstance(answer.get("node_id"), str) or not NODE_ID.match(answer["node_id"]):
        raise Stop("GitHub's answer is not the issue that was asked for")
    if not str(answer.get("repository_url", "")).endswith("/repos/" + repo):
        raise Stop("GitHub answered from another repository. The issue was transferred")
    if "pull_request" in answer:
        raise Refused("number %d is a pull request. This workflow changes issues only. The rule: %s" % (number, PULL_REQUEST_RULE))
    labels = [row["name"] if isinstance(row, dict) else str(row) for row in answer.get("labels") or []]
    people = [row["login"] for row in answer.get("assignees") or [] if isinstance(row, dict) and isinstance(row.get("login"), str)]
    milestone = answer.get("milestone")
    snapshot = {"labels": sorted(labels, key=str.casefold), "assignees": sorted(people, key=str.casefold),
                "milestone": {"number": milestone["number"], "title": milestone["title"]} if isinstance(milestone, dict) else None}
    label_ids = {row["name"]: row.get("id") for row in answer.get("labels") or [] if isinstance(row, dict)}
    return snapshot, {"node_id": answer["node_id"], "state": str(answer.get("state")), "label_ids": label_ids}, github_time(head)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------- what was asked for


def parse_changes(texts):
    """The changes as typed. Returns (the supported ones as [field, value] pairs, the refused ones as (text, reason))."""
    asked, refused = [], []
    for text in texts or []:
        field, equals, value = text.partition("=")
        field, value = field.strip(), value.strip()
        if field not in SUPPORTED:
            reason = NOT_SUPPORTED.get(field) or (NOT_SUPPORTED["project"] if field.split(".")[0] in ("project", "projects") else None)
            refused.append((text, "NOT SUPPORTED: %s" % (reason or "it is not a field this workflow knows. It changes only: %s" % ", ".join(SUPPORTED))))
        elif not equals or not value or len(value) > 100 or any(ord(char) < 32 for char in value):
            refused.append((text, "the value must be short plain text on one line"))
        elif field == "milestone.clear" and value != "yes":
            refused.append((text, "to clear the milestone, write milestone.clear=yes"))
        elif field.startswith("assignee.") and not LOGIN.match(value):
            refused.append((text, "that is not the shape of a GitHub login"))
        elif [field, value] in asked:
            refused.append((text, "the same change was asked for twice"))
        else:
            asked.append([field, value])
    if len(asked) > MAX_CHANGES:
        refused.append(("(all of them)", "at most %d changes go in one preview" % MAX_CHANGES))
    return sorted(asked), refused


def plan(asked, old, repo_labels, milestones, assignable):
    """Work out, change by change, what would happen. Returns (rows, the snapshot the issue would have afterwards)."""
    new = {"labels": list(old["labels"]), "assignees": list(old["assignees"]), "milestone": old["milestone"]}
    rows = []

    def row(field, value, status, why=""):
        rows.append({"field": field, "value": value, "status": status, "why": why})

    def among(names, name):
        return next((have for have in names if have.casefold() == name.casefold()), None)
    for field, value in asked:
        kind, action = field.split(".")
        opposite = "%s.%s" % (kind, {"add": "remove", "remove": "add", "set": "clear", "clear": "set"}[action])
        if any(other == opposite and (kind == "milestone" or theirs.casefold() == value.casefold()) for other, theirs in asked):
            row(field, value, "refused", "the same request also asks for the opposite (%s)" % opposite)
        elif kind == "label":
            known = among(repo_labels, value)
            if known is None:
                row(field, value, "refused", "the repository has no label of that name. This workflow does not create labels, and GitHub would create one without saying")
            elif action == "add" and among(old["labels"], known):
                row(field, known, "already", "the issue already has this label")
            elif action == "remove" and not among(old["labels"], known):
                row(field, known, "already", "the issue does not have this label")
            else:
                row(field, known, "change")
                new["labels"] = [have for have in new["labels"] if have != known] + ([known] if action == "add" else [])
        elif kind == "assignee":
            held = among(old["assignees"], value)
            if action == "remove":
                if held is None:
                    row(field, value, "already", "this person is not assigned to the issue")
                else:
                    row(field, held, "change")
                    new["assignees"].remove(held)
            elif held:
                row(field, held, "already", "this person is already assigned to the issue")
            elif not assignable(value):
                row(field, value, "refused", "GitHub says this login cannot be assigned to issues in this repository")
            elif len(new["assignees"]) >= MAX_ASSIGNEES:
                row(field, value, "refused", "an issue can have at most %d assignees" % MAX_ASSIGNEES)
            else:
                row(field, value, "change")
                new["assignees"].append(value)
        elif action == "clear":
            if old["milestone"] is None:
                row(field, value, "already", "the issue has no milestone")
            else:
                row(field, value, "change")
                new["milestone"] = None
        else:
            found = [one for one in milestones if one.get("title") == value]
            if len(found) != 1:
                row(field, value, "refused", "the repository has %s milestone with exactly that title" % ("no" if not found else "more than one"))
            elif found[0].get("state") != "open":
                row(field, value, "refused", "that milestone is closed")
            elif old["milestone"] and old["milestone"]["number"] == found[0]["number"]:
                row(field, value, "already", "the issue is already in this milestone")
            else:
                row(field, value, "change")
                new["milestone"] = {"number": found[0]["number"], "title": found[0]["title"]}
    new["labels"].sort(key=str.casefold)
    new["assignees"].sort(key=str.casefold)
    return rows, new


def requests_for(repo, number, rows, new):
    """The exact requests a confirmation sends. One label or one person at a time, never a whole list."""
    base, out = "/repos/%s/issues/%d" % (repo, number), []
    for one in rows:
        if one["status"] != "change":
            continue
        if one["field"] == "label.add":
            out.append({"method": "POST", "path": base + "/labels", "body": {"labels": [one["value"]]}})
        elif one["field"] == "label.remove":
            out.append({"method": "DELETE", "path": base + "/labels/" + urllib.parse.quote(one["value"], safe=""), "body": None})
        elif one["field"] == "assignee.add":
            out.append({"method": "POST", "path": base + "/assignees", "body": {"assignees": [one["value"]]}})
        elif one["field"] == "assignee.remove":
            out.append({"method": "DELETE", "path": base + "/assignees", "body": {"assignees": [one["value"]]}})
        else:
            out.append({"method": "PATCH", "path": base, "body": {"milestone": new["milestone"]["number"] if new["milestone"] else None}})
    return out


def reversal(rows, old):
    """The changes that would put the old values back."""
    back = []
    for one in rows:
        if one["status"] != "change":
            continue
        kind, action = one["field"].split(".")
        if kind == "milestone":
            back.append("milestone.set=%s" % old["milestone"]["title"] if old["milestone"] else "milestone.clear=yes")
        else:
            back.append("%s.%s=%s" % (kind, "remove" if action == "add" else "add", one["value"]))
    return back


# ---------------------------------------------------------------- the allowlist and the saved preview


def check_allowlist(path, repo):
    """Before any request: is this repository one the workflow may write to? Returns how many are on the list."""
    try:
        with open(path, encoding="utf-8") as f:
            names = json.load(f)["sandbox_repositories"]
    except (OSError, ValueError, KeyError, TypeError):
        raise Refused("the sandbox allowlist could not be read, so no repository is allowed")
    if not isinstance(names, list) or repo not in names:
        raise Refused("the repository %s is NOT ON THE SANDBOX ALLOWLIST. This workflow writes only to the repositories named in %s. "
                      "No request was sent to GitHub" % (q(repo), shown_path(path)))
    return len(names)


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, sort_keys=True)
    os.replace(tmp, path)


def fingerprint_of(record):
    return digest(record)[:32]


def differences(old, new):
    """In words: what differs between two snapshots, field by field. Empty when they are the same."""
    found = []
    for field in ("labels", "assignees"):
        added = [name for name in new[field] if name not in old[field]]
        removed = [name for name in old[field] if name not in new[field]]
        if added or removed:
            found.append((field, ", ".join((["added " + q(name) for name in added]) + ["removed " + q(name) for name in removed])))
    if old["milestone"] != new["milestone"]:
        found.append(("milestone", "%s became %s" % (milestone_words(old["milestone"]), milestone_words(new["milestone"]))))
    return found


def milestone_words(milestone):
    return "none" if milestone is None else "%s (number %d)" % (q(milestone["title"]), milestone["number"])


def show_values(title, snapshot):
    say("     %-10s labels     %s" % (title, q(snapshot["labels"])))
    say("     %-10s assignees  %s" % ("", q(snapshot["assignees"])))
    say("     %-10s milestone  %s" % ("", milestone_words(snapshot["milestone"])))


# ---------------------------------------------------------------- preview


def gather(conn, args, asked):
    """Everything the preview and the confirmation both need to read. Only GET requests."""
    account = read_account(conn)
    repo = read_repo(conn, args.repo)
    old, facts, now = read_issue(conn, args.repo, args.issue)
    repo_labels = [row["name"] for row in read_all(conn, "/repos/%s/labels" % args.repo, {}, "the repository's labels") if isinstance(row.get("name"), str)]
    milestones = read_all(conn, "/repos/%s/milestones" % args.repo, {"state": "all"}, "the repository's milestones")

    def assignable(login):
        status, _, _ = conn.get("/repos/%s/assignees/%s" % (args.repo, urllib.parse.quote(login, safe="")))
        if status not in (204, 404):
            raise Stop("GitHub did not say whether %s can be assigned (status %d)" % (q(login), status))
        return status == 204
    rows, new = plan(asked, old, repo_labels, milestones, assignable)
    return {"account": account, "repo": repo, "old": old, "new": new, "facts": facts, "now": now, "rows": rows}


def cmd_preview(args, conn):
    say("PREVIEW of a change to an issue's metadata. This command only reads. It has no way to write")
    asked, refused = parse_changes(args.change)
    count = check_allowlist(args.allowlist, args.repo)
    found = gather(conn, args, asked)
    repo, old, new, rows = found["repo"], found["old"], found["new"], found["rows"]
    say("1. WHERE. Repository %s, id %d, %s. Issue %d, node ID %s, state %s. The connection acts as login %s"
        % (q(args.repo), repo["id"], "private" if repo.get("private") else "PUBLIC", args.issue, found["facts"]["node_id"], found["facts"]["state"], q(found["account"])))
    say("2. ALLOWLIST. The repository is on the sandbox allowlist %s, which names %s" % (shown_path(args.allowlist), plural(count, "repository", "repositories")))
    say("3. WHAT WAS ASKED, change by change:")
    for text, reason in refused:
        say("     %s: REFUSED. %s" % (q(text), reason))
    words = {"change": "WILL CHANGE", "already": "ALREADY SO, nothing is sent for it", "refused": "REFUSED"}
    for one in rows:
        say("     %s=%s: %s%s" % (one["field"], q(one["value"]), words[one["status"]], ". " + one["why"] if one["why"] else ""))
    say("4. OLD AND NEW VALUES of every field this workflow can change:")
    show_values("old:", old)
    show_values("new:", new)
    for field, what in differences(old, new):
        say("     difference: %s: %s" % (field, what))
    if new == old:
        say("     difference: none. Nothing would change")
    requests = requests_for(args.repo, args.issue, rows, new)
    say("5. EXACT REQUESTS a confirmation would send, in this order: %d" % len(requests))
    for one in requests:
        say("     %s %s%s" % (one["method"], one["path"], " " + json.dumps(one["body"]) if one["body"] is not None else ""))
    may = repo.get("permissions") if isinstance(repo.get("permissions"), dict) else None
    allowed = bool(may and (may.get("push") or may.get("triage") or may.get("maintain") or may.get("admin")))
    say("6. PERMISSION CHECK. %s" % (
        "GitHub did not say what the account may do in this repository" if may is None else
        "GitHub says the ACCOUNT %s change issues here (%s)" % ("may" if allowed else "MAY NOT", ", ".join("%s: %s" % (key, "yes" if may[key] else "no") for key in sorted(may)))))
    say("     %s" % ("The token's scopes, as GitHub reports them: %s" % q(conn.scopes) if conn.scopes is not None else
                     "GitHub reports no scopes for this token, as for a fine-grained token, and does not say what the TOKEN may do. "
                     "That is known only when a write is tried: a token that may not write is refused by GitHub with status 403, and nothing changes"))
    if repo.get("archived"):
        say("     The repository is ARCHIVED. GitHub accepts no changes to it")
    already = [one for one in rows if one["status"] == "already"]
    say("7. DUPLICATE CHECK. Each change was compared with the issue as it is now. Already so, and not sent: %d. "
        "GitHub does not refuse a repeated change of this kind itself: it accepts it and changes nothing" % len(already))
    again, _, _ = read_issue(conn, args.repo, args.issue)
    say("8. NOTHING WAS WRITTEN. The issue was read again at the end. Its labels, assignees and milestone before: %s. After: %s. %s"
        % (digest(old)[:16], digest(again)[:16], "The same" if again == old else "DIFFERENT: someone changed the issue during this preview"))
    say("     Requests made by this command: %d, every one a GET" % len(conn.asked))
    bad = len(refused) + sum(one["status"] == "refused" for one in rows)
    if bad or not allowed or repo.get("archived") or again != old:
        say("RESULT: NOT READY. %s. No fingerprint is given, so there is nothing to confirm" % (
            "%s refused" % plural(bad, "change was", "changes were") if bad else "the account may not change issues here" if not allowed
            else "the repository is archived" if repo.get("archived") else "the issue changed while it was being previewed"))
        return 1
    if not requests:
        say("RESULT: NOTHING TO CHANGE. The issue already has every value that was asked for. No fingerprint is given, so there is nothing to confirm")
        return 0
    record = {"format": PREVIEW_FORMAT, "source": args.source, "repository": args.repo, "repository_id": repo["id"], "issue": args.issue,
              "node_id": found["facts"]["node_id"], "account": found["account"], "asked": asked, "old": old, "new": new,
              "changes": [[one["field"], one["value"]] for one in rows if one["status"] == "change"], "requests": requests,
              "created": found["now"], "limit_minutes": LIMIT_MINUTES}
    mark = fingerprint_of(record)
    save_json(os.path.join(args.state, mark + ".json"), {"record": record, "status": "ready"})
    say("9. FINGERPRINT of this preview: %s. It covers the repository, the issue, the old values, the new values and the exact requests" % mark)
    say("     Made at %s by GitHub's clock. It can be confirmed once, for %d minutes" % (found["now"], LIMIT_MINUTES))
    say("     To confirm: run the same command with `confirm` in place of `preview`, and add --fingerprint %s --confirmed-by YOUR-NAME" % mark)
    say("RESULT: READY. Nothing has been written")
    return 0


# ---------------------------------------------------------------- confirm


def load_preview(state, mark):
    if not FINGERPRINT.match(mark or ""):
        raise Refused("that is not the shape of a preview fingerprint")
    path = os.path.join(state, mark + ".json")
    try:
        with open(path, encoding="utf-8") as f:
            saved = json.load(f)
        record, status = saved["record"], saved["status"]
    except (OSError, ValueError, KeyError, TypeError):
        raise Refused("there is no preview with the fingerprint %s. Run `preview` first" % mark)
    if fingerprint_of(record) != mark or record.get("format") != PREVIEW_FORMAT:
        raise Refused("the saved preview does not match its fingerprint. It was altered after it was made")
    return path, saved, record, status


def cmd_confirm(args, conn):
    say("CONFIRM a change to an issue's metadata")
    if not args.fingerprint or not args.confirmed_by:
        raise Refused("NO CONFIRMATION was given. A write needs --fingerprint, from the preview, and --confirmed-by, the name of the person confirming")
    name = args.confirmed_by.strip()
    if not name or len(name) > 60 or any(ord(char) < 32 for char in name) or EMAIL_SHAPED.search(name):
        raise Refused("--confirmed-by must be a short plain name, and not an email address")
    count = check_allowlist(args.allowlist, args.repo)
    path, saved, record, status = load_preview(args.state, args.fingerprint)
    if (record["repository"], record["issue"], record["source"]) != (args.repo, args.issue, args.source):
        raise Refused("THE CHANGE DIFFERS FROM THE PREVIEW: the preview with this fingerprint is for another repository, issue or source")
    asked, refused = parse_changes(args.change)
    if refused or asked != record["asked"]:
        only_now = [pair for pair in asked if pair not in record["asked"]] + [[text, ""] for text, _ in refused]
        only_then = [pair for pair in record["asked"] if pair not in asked]
        raise Refused("THE CHANGE DIFFERS FROM THE PREVIEW. Asked for now and not in the preview: %s. In the preview and not asked for now: %s. "
                      "A confirmation covers exactly what its preview showed. Make a new preview"
                      % (q(["=".join(pair).rstrip("=") for pair in only_now]), q(["=".join(pair) for pair in only_then])))
    if status != "ready":
        raise Refused("this preview was ALREADY USED, at %s by GitHub's clock, confirmed by %s. A preview can be confirmed once. "
                      "To change something more, make a new preview" % (saved.get("used_at"), q(saved.get("confirmed_by"))))
    say("1. CONFIRMATION. Given by %s, for the preview with fingerprint %s, in this same command" % (q(name), args.fingerprint))
    say("     The name is recorded as it was typed. This workflow cannot check who typed it")
    say("2. ALLOWLIST. The repository %s is on the sandbox allowlist, which names %s" % (q(args.repo), plural(count, "repository", "repositories")))
    say("3. THE CHANGE asked for now is the change of the preview: %s" % q(["=".join(pair) for pair in asked]))

    account = read_account(conn)
    repo = read_repo(conn, args.repo)
    now_values, facts, now = read_issue(conn, args.repo, args.issue)
    if account != record["account"] or repo["id"] != record["repository_id"] or facts["node_id"] != record["node_id"]:
        raise Refused("the account, the repository or the issue is not the one of the preview. Make a new preview")
    age = minutes_between(record["created"], now)
    if age > record["limit_minutes"] or age < -1:
        raise Refused("THE PREVIEW HAS EXPIRED. It was made at %s and it is now %s by GitHub's clock: %d minutes, and the limit is %d. Make a new preview"
                      % (record["created"], now, round(age), record["limit_minutes"]))
    say("4. AGE. The preview was made at %s and it is now %s by GitHub's clock: %s. The limit is %d" % (record["created"], now, plural(round(age), "minute"), record["limit_minutes"]))
    moved = differences(record["old"], now_values)
    if moved:
        say("5. HAS ANYTHING MOVED? YES. The issue's metadata on GitHub is no longer what the preview showed:")
        show_values("preview:", record["old"])
        show_values("now:", now_values)
        for field, what in moved:
            say("     MOVED since the preview: %s: %s" % (field, what))
        raise Refused("STALE: a field changed on GitHub after the preview. The person confirmed a picture that is out of date, so the update is not made. "
                      "Make a new preview, which will show the issue as it is now")
    say("5. HAS ANYTHING MOVED? No. Labels, assignees and milestone were read again just now and are what the preview showed (%s)" % digest(now_values)[:16])
    events_before = {row.get("id") for row in read_all(conn, "/repos/%s/issues/%d/events" % (args.repo, args.issue), {}, "the issue's events")}

    saved.update(status="used", used_at=now, confirmed_by=name)
    save_json(path, saved)                      # the preview is spent before the first write, so it can never be used twice
    conn.allow_writes(args.repo, args.issue)
    say("6. WRITING. %s, as shown in the preview:" % plural(len(record["requests"]), "request"))
    sent, failed = [], None
    for one in record["requests"]:
        status_code, _, _ = conn.write(one["method"], one["path"], one["body"])
        ok = status_code in (200, 201)
        sent.append(dict(one, status=status_code))
        say("     %s %s%s -> status %d%s" % (one["method"], one["path"], " " + json.dumps(one["body"]) if one["body"] is not None else "",
                                           status_code, "" if ok else ". GITHUB REFUSED THIS. No further request is sent"))
        if not ok:
            failed = status_code
            break
    after, facts_after, written_at = read_issue(conn, args.repo, args.issue)
    events = [row for row in read_all(conn, "/repos/%s/issues/%d/events" % (args.repo, args.issue), {}, "the issue's events")
              if row.get("id") not in events_before and row.get("event") in EVENTS_OF_INTEREST]
    as_promised = after == record["new"]
    untouched = after == record["old"]
    say("7. READ BACK. The issue was read again after the writes:")
    show_values("now:", after)
    say("     %s" % ("This is exactly what the preview promised" if as_promised else
                     "This is what the issue held before. NOTHING WAS CHANGED" if untouched else
                     "THIS IS NOT what the preview promised: %s" % "; ".join("%s: %s" % pair for pair in differences(record["new"], after))))
    outcome = "DONE" if as_promised and failed is None else "NOT DONE, NOTHING CHANGED" if untouched else "NEEDS LOOKING"
    ids = {name_: facts_after["label_ids"].get(name_) for name_ in after["labels"] if name_ not in record["old"]["labels"]}
    say("8. IDENTIFIERS. Events GitHub recorded for this update: %s. Labels added, with their ids: %s"
        % (", ".join("%s %s" % (row.get("event"), row.get("id")) for row in events) or "none listed yet", q(ids) if ids else "none"))
    results = os.path.join(args.results, "update-metadata.md")
    append_result(results, args, record, name, outcome, sent, after, events, ids, written_at)
    say("9. RESULT RECORD. Written to %s" % shown_path(results))
    say("     Requests made by this command: %d. Writes: %d, all to issue %d of the repository of the preview"
        % (len(conn.asked), len(conn.writes()), args.issue))
    if outcome == "DONE":
        say("RESULT: DONE. The update of the preview was made, and the issue was read back and matches")
        return 0
    if outcome == "NEEDS LOOKING":
        say("RESULT: NEEDS LOOKING. Something was written, and the issue is not what the preview promised. Someone may have changed it in the "
            "moment between the check and the write, or GitHub refused part of the update. Look at the issue on GitHub. The result record says what was sent")
        return 3
    say("RESULT: NOT DONE. GitHub refused the write (status %s) and the issue is as it was. The preview is spent: make a new one once the cause is fixed" % failed)
    return 1


def append_result(path, args, record, name, outcome, sent, after, events, ids, written_at):
    head = ["# Result records: metadata updates", "",
            "Written by the github-update-metadata skill. One section for each confirmed update, the newest last. Every value",
            "that came from GitHub or from the command line is written as JSON.", ""]
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        text = "\n".join(head)
    back = reversal([{"field": field, "value": value, "status": "change"} for field, value in record["changes"]], record["old"])
    lines = ["", "## Update %s" % args.fingerprint, "",
             "- outcome: %s" % outcome,
             "- repository: %s, id %d" % (q(record["repository"]), record["repository_id"]),
             "- issue: number %d, node ID %s" % (record["issue"], record["node_id"]),
             "- source: %s" % ("the made-up GitHub (fake_github.py)" if record["source"] == "fake" else "GitHub"),
             "- confirmed by: %s, as typed with the fingerprint in the command that wrote. The workflow cannot check who typed it" % q(name),
             "- the connection acted as login: %s" % q(record["account"]),
             "- preview fingerprint: %s, made at %s by GitHub's clock" % (args.fingerprint, record["created"]),
             "- written at: %s by GitHub's clock" % written_at, "",
             "| field | old value | new value promised by the preview | value read back after the write |", "|---|---|---|---|"]
    for field in ("labels", "assignees"):
        lines.append("| %s | `%s` | `%s` | `%s` |" % (field, q(record["old"][field]), q(record["new"][field]), q(after[field])))
    lines.append("| milestone | `%s` | `%s` | `%s` |" % tuple(q(value) for value in (record["old"]["milestone"], record["new"]["milestone"], after["milestone"])))
    lines += ["", "Requests sent, in order:", ""]
    lines += ["- `%s %s%s` -> status %d" % (one["method"], one["path"], " " + json.dumps(one["body"]) if one["body"] is not None else "", one["status"]) for one in sent]
    lines += ["", "Identifiers of what was changed:", ""]
    lines += ["- event %s: `%s`, at %s" % (row.get("id"), row.get("event"), row.get("created_at")) for row in events] or ["- GitHub listed no event for this update when it was read back"]
    lines += ["- label %s: id %s" % (q(label), number) for label, number in sorted(ids.items())]
    lines += ["", "To put the old values back, preview and confirm these changes:", ""]
    lines += ["- `--change %s`" % q(change) for change in back]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text.rstrip("\n") + "\n" + "\n".join(lines) + "\n")
    os.replace(tmp, path)


# ---------------------------------------------------------------- the command line


def run(args, conn):
    try:
        if not good_repo(args.repo):
            raise Refused("give --repo, the repository as owner/name")
        if not args.issue or args.issue < 1:
            raise Refused("give --issue, the issue's number")
        return cmd_preview(args, conn) if args.command == "preview" else cmd_confirm(args, conn)
    except Refused as why:
        say("REFUSED: %s." % why)
    except Stop as why:
        say("STOPPED: %s." % why)
    except RateLimited:
        if conn.writes():
            say("INCOMPLETE: GitHub rate-limited this run after a write was sent. Look at the issue on GitHub, then make a new preview.")
            return 3
        say("INCOMPLETE: GitHub rate-limited this run. Nothing was written. Run it again later.")
        return 2
    wrote = len(conn.writes())
    say("%s Requests made by this command: %d%s" % (
        "Nothing was written." if not wrote else "WRITES WERE SENT BEFORE THIS: %d. Look at the issue on GitHub." % wrote,
        len(conn.asked), ", every one a GET" if conn.asked and not wrote else ""))
    return 3 if wrote else 1


def main(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.realpath(os.path.join(here, "..", "..", ".."))
    parser = argparse.ArgumentParser(description="Change labels, assignees or milestone of one issue, after a preview and a confirmation.")
    parser.add_argument("command", choices=("preview", "confirm"))
    parser.add_argument("--source", choices=("live", "fake"), required=True)
    parser.add_argument("--repo")
    parser.add_argument("--issue", type=int)
    parser.add_argument("--change", action="append", metavar="FIELD=VALUE")
    parser.add_argument("--allowlist", required=True, help="a JSON file naming the sandbox repositories")
    parser.add_argument("--state", required=True, help="a folder where a preview is kept until it is confirmed")
    parser.add_argument("--results", help="confirm: the folder for the result record")
    parser.add_argument("--fingerprint", help="confirm: the fingerprint the preview printed")
    parser.add_argument("--confirmed-by", help="confirm: the name of the person confirming")
    parser.add_argument("--fake-store", help="with --source fake: the made-up GitHub's file")
    args = parser.parse_args(argv)
    args.results = args.results or os.path.join(here, "..", "..", "context", "github", "results")
    if args.source == "fake":
        if not args.fake_store:
            say("REFUSED: --source fake needs --fake-store, the made-up GitHub's file.")
            return 1
        sys.path.insert(0, here)
        import fake_github
        return run(args, Connection(fake_github.load(args.fake_store).send))
    for folder, what in ((args.state, "--state"), (args.results, "--results")):
        if os.path.commonpath([root, os.path.realpath(folder)]) == root:
            say("REFUSED: a live run keeps its files outside this repository. Give %s a folder outside it." % what)
            return 1
    if args.fake_store:
        say("REFUSED: --fake-store only goes with --source fake.")
        return 1
    if not os.environ.get("GITHUB_TOKEN"):
        say("REFUSED: the environment variable GITHUB_TOKEN is not set.")
        return 1
    return run(args, Connection(make_live(may_write=args.command == "confirm")))


if __name__ == "__main__":
    sys.exit(main())
