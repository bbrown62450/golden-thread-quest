#!/usr/bin/env python3
"""Read-only delta synchronization of the issues of one GitHub repository.

See SKILL.md in this folder for what it does and the rules it follows.

    sync.py --source fake [--fake-step N] [--fake-fail-issue N]     read the made-up GitHub in fake_github.py
    sync.py --source live --repo OWNER/NAME --out FOLDER            read one repository on GitHub
    sync.py ... --full                                              read every issue again, ignoring the cursor
    sync.py ... --verify                                            compare the local copy with a full read. Writes nothing
    sync.py --status [--out FOLDER]                                 say where the cursor is. Contacts nothing

It only ever sends GET requests. There is no code here that creates, comments
on, labels, closes or reopens anything in GitHub.

Exit codes: 0 synchronized, or verified the same; 1 stopped, nothing written; 2 incomplete (rate-limited),
nothing written; 3 --verify found the local copy and GitHub differ.
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
PER_PAGE = 100             # the most GitHub returns for one request
MARGIN_SECONDS = 300       # how far behind the cursor each delta asks from
STALE_HOURS = 24
MAX_WAITS = 3              # waits for one request before giving up
MAX_WAIT_SECONDS = 15      # the longest single wait
DEFAULT_WAIT_SECONDS = 10
MAX_REDIRECTS = 3
NODE_ID = re.compile(r"^[A-Za-z0-9_=-]{1,120}$")
REPO_NAME = re.compile(r"^[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}$")
STAMP = "%Y-%m-%dT%H:%M:%SZ"
# What is kept of an issue, and what the digest is taken over. Nothing else in GitHub's answer is kept.
KEPT = ("number", "title", "state", "state_reason", "author", "assignees", "labels", "milestone", "created_at",
        "updated_at", "closed_at")
CURSOR_SOURCE = "GitHub's own clock, from the Date header of the first answer of the last successful sync"
PULL_REQUEST_RULE = "an item is a pull request when it carries a `pull_request` key, and only then"


class Stop(Exception):
    """The run cannot go on. The message says why, in plain words."""


class RateLimited(Exception):
    """GitHub kept answering with a rate limit after every allowed wait."""


def say(text):
    print("github-delta: " + text, flush=True)


def shown_path(path):
    """A path as it is printed: from the folder the skill was run in, so a home folder's name is not shown."""
    try:
        relative = os.path.relpath(path)
    except ValueError:
        return os.path.basename(path)
    return os.path.basename(path) if relative.startswith("..") else relative


def plural(count, word, many=None):
    return "%d %s" % (count, word if count == 1 else many or word + "s")


# ---------------------------------------------------------------- talking to GitHub


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None            # a redirect comes back as an answer, and the Client decides whether to follow it


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
    request.add_header("User-Agent", "github-delta-sync-skill")
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


def lowered(headers):
    return {str(name).lower(): str(value) for name, value in (headers or {}).items()}


class Client:
    """Every request the skill makes goes through here. It can only read."""

    def __init__(self, get, sleep=time.sleep, clock=time.time):
        self._get, self._sleep, self._clock = get, sleep, clock
        self.waits = []        # seconds waited for rate limits, in order
        self.count = 0         # requests answered
        self.redirects = 0     # redirects followed
        self.scopes = None     # what GitHub says the token may do, when it says

    def _wait_for(self, headers):
        if headers.get("retry-after", "").isdigit():
            return int(headers["retry-after"])
        if headers.get("x-ratelimit-reset", "").isdigit():
            return max(1, int(headers["x-ratelimit-reset"]) - int(self._clock()) + 1)
        return DEFAULT_WAIT_SECONDS

    def _once(self, path, params):
        waited = 0
        while True:
            status, headers, body = self._get(path, params)
            self.count += 1
            head = lowered(headers)
            if "x-oauth-scopes" in head:
                self.scopes = head["x-oauth-scopes"]
            limited = status == 429 or (status == 403 and (head.get("x-ratelimit-remaining") == "0" or "retry-after" in head))
            if not limited:
                return status, head, body
            seconds = self._wait_for(head)
            if seconds > MAX_WAIT_SECONDS or waited == MAX_WAITS:
                say("rate limited by GitHub, and %s" % ("it asks for a %d second wait when the limit is %d"
                    % (seconds, MAX_WAIT_SECONDS) if seconds > MAX_WAIT_SECONDS else "still limited after %d waits" % MAX_WAITS))
                raise RateLimited()
            waited += 1
            say("rate limited by GitHub. Wait %d of %d: %d seconds" % (waited, MAX_WAITS, seconds))
            self._sleep(seconds)
            self.waits.append(seconds)

    def get(self, path, params=None):
        """Returns (status, headers with lower-case names, body). Follows GitHub's own redirects, and no others."""
        params, hops = dict(params or {}), 0
        while True:
            status, head, body = self._once(path, params)
            if status == 401:
                raise Stop("GitHub rejected the token (401). Check GITHUB_TOKEN. A token also stops working when it expires")
            if status not in (301, 302, 307, 308):
                return status, head, body
            where = urllib.parse.urlsplit(head.get("location", ""))
            if where.scheme != "https" or where.netloc != API_HOST or hops == MAX_REDIRECTS:
                raise Stop("GitHub redirected %s to somewhere the skill does not follow" % path)
            path, params, hops = where.path, dict(urllib.parse.parse_qsl(where.query)), hops + 1
            self.redirects += 1


def has_next(head):
    """GitHub says there is a further page with a Link header that has rel="next"."""
    return any('rel="next"' in part for part in head.get("link", "").split(","))


def read_pages(client, path, params, what, key):
    """Criterion 4: ask for the next page until GitHub reports no further page. Returns (rows, size of each page)."""
    rows, sizes, seen, page = [], [], set(), 1
    while True:
        status, head, body = client.get(path, dict(params, per_page=PER_PAGE, page=page))
        if status != 200 or not isinstance(body, list) or any(not isinstance(row, dict) for row in body):
            raise Stop("GitHub did not return %s (status %d). A part may be missing, so nothing is saved" % (what, status))
        if len(body) > PER_PAGE:
            raise Stop("GitHub returned more of %s than were asked for, so paging cannot be trusted" % what)
        fresh = [row for row in body if key(row) not in seen]
        sizes.append(len(body))
        rows += fresh
        seen.update(key(row) for row in fresh)
        if not has_next(head):
            return rows, sizes
        if not fresh:
            # GitHub says there is more, and gave nothing new. Asking for the next page is not working, so
            # there may be rows that were never reached. This is not treated as the end.
            raise Stop("GitHub kept returning the same of %s, so the skill cannot tell whether it has them all" % what)
        page += 1


# ---------------------------------------------------------------- the person's notes


def notes_checksums(out_dir):
    """SHA-256 of every notes file. The files are opened for reading only. Nothing in this skill writes there."""
    folder, sums = os.path.join(out_dir, "notes"), {}
    if os.path.isdir(folder):
        for name in sorted(os.listdir(folder)):
            path = os.path.join(folder, name)
            if os.path.isfile(path):
                with open(path, "rb") as f:
                    sums[name] = hashlib.sha256(f.read()).hexdigest()
    return sums


def write_text(path, text, out_dir):
    """Write the whole file or nothing. Refuses anything in the notes folder (criterion 6)."""
    notes = os.path.realpath(os.path.join(out_dir, "notes"))
    if os.path.commonpath([notes, os.path.realpath(path)]) == notes:
        raise Stop("the sync does not write in the notes folder")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


# ---------------------------------------------------------------- times


UTC = datetime.timezone.utc


def parse(stamp):
    return datetime.datetime.strptime(stamp, STAMP).replace(tzinfo=UTC)


def utc_now():
    return datetime.datetime.now(UTC).strftime(STAMP)


def github_clock(head):
    """GitHub's own time, from the Date header of one of its answers.

    The cursor is taken from this and from nothing else. If the header is missing or cannot be read the run
    stops: this machine's clock is never used in its place.
    """
    try:
        when = email.utils.parsedate_to_datetime(head["date"])
    except (KeyError, TypeError, ValueError):
        raise Stop("GitHub's answer carried no usable Date header, so its clock cannot be read. This machine's "
                   "clock is never used in its place")
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    return when.astimezone(UTC).strftime(STAMP)


def since_for(cursor_time, margin):
    """The time a delta asks from: the cursor, backed up by the margin."""
    return (parse(cursor_time) - datetime.timedelta(seconds=margin)).strftime(STAMP)


def apart(earlier, later):
    seconds = int((parse(later) - parse(earlier)).total_seconds())
    if abs(seconds) < 120:
        return plural(abs(seconds), "second")
    if abs(seconds) < 2 * 3600:
        return plural(abs(seconds) // 60, "minute")
    return "%.1f hours" % (abs(seconds) / 3600)


def clock_difference(local_now, github_now):
    seconds = int((parse(local_now) - parse(github_now)).total_seconds())
    if seconds == 0:
        return "the same as GitHub's"
    return "%s %s GitHub's" % (apart(github_now, local_now), "ahead of" if seconds > 0 else "behind")


def staleness(state, local_now, stale_hours):
    cursor = state["cursor"]["time"]
    hours = (parse(local_now) - parse(cursor)).total_seconds() / 3600
    text = "the last successful sync started at %s by GitHub's clock, %s before now (%s by this machine's clock)" % (
        cursor, apart(cursor, local_now), local_now)
    return text + (". STALE: that is more than %d hours" % stale_hours if hours > stale_hours else "")


# ---------------------------------------------------------------- reading


def login_of(person):
    return person["login"] if isinstance(person, dict) and isinstance(person.get("login"), str) else "(nobody)"


def good_repo(name):
    return bool(isinstance(name, str) and REPO_NAME.match(name) and not set(name.split("/")) & {".", ".."})


def repo_in_url(url):
    name = "/".join(str(url or "").partition("/repos/")[2].split("/")[:2])
    return name if good_repo(name) else None


def read_repo(client, repo):
    """The repository, and GitHub's clock at the start of the sync. This is the first request of every run."""
    status, head, body = client.get("/repos/%s" % repo)
    if status in (403, 404):
        raise Stop("GitHub does not show the repository to this connection (status %d). Check its name and the token's access" % status)
    if status != 200 or not isinstance(body, dict) or not isinstance(body.get("id"), int):
        raise Stop("GitHub did not return the repository (status %d)" % status)
    return {"id": body["id"], "private": bool(body.get("private"))}, github_clock(head)


def as_fields(row):
    """The fields kept of one issue. Nothing else in GitHub's answer is kept: no body, no comment text."""
    if not isinstance(row.get("node_id"), str) or not NODE_ID.match(row["node_id"]):
        raise Stop("GitHub returned an item with no usable node ID")
    if not isinstance(row.get("number"), int) or isinstance(row.get("number"), bool):
        raise Stop("GitHub returned item %s without a usable number" % row["node_id"])
    milestone = row.get("milestone") if isinstance(row.get("milestone"), dict) else None
    return {"node_id": row["node_id"], "number": row["number"], "title": str(row.get("title") or ""),
            "state": str(row.get("state") or "unknown"), "state_reason": row.get("state_reason"),
            "author": login_of(row.get("user")),
            "assignees": sorted(login_of(person) for person in row.get("assignees") or []),
            "labels": sorted(str(label.get("name")) if isinstance(label, dict) else str(label) for label in row.get("labels") or []),
            "milestone": str(milestone.get("title")) if milestone else None,
            "created_at": row.get("created_at"), "updated_at": row.get("updated_at"), "closed_at": row.get("closed_at")}


def read_issues(client, repo, since):
    """Criterion 1: with `since`, GitHub returns only the issues updated at or after that time."""
    params = {"state": "all", "sort": "updated", "direction": "asc"}
    if since:
        params["since"] = since
    rows, sizes = read_pages(client, "/repos/%s/issues" % repo, params, "the repository's issues", key=lambda row: row.get("node_id"))
    issues = [as_fields(row) for row in rows if "pull_request" not in row]
    return issues, len(rows) - len(issues), sizes


def read_comments(client, repo, issue):
    """The comments of one issue: who, when, and when last edited. Their text is not kept."""
    rows, sizes = read_pages(client, "/repos/%s/issues/%d/comments" % (repo, issue["number"]), {},
                             "the comments of issue %s" % issue["node_id"], key=lambda row: row.get("id"))
    if any(not isinstance(row.get("id"), int) for row in rows):
        raise Stop("GitHub returned a comment with no id")
    comments = [{"id": row["id"], "author": login_of(row.get("user")), "created_at": row.get("created_at"),
                 "updated_at": row.get("updated_at")} for row in rows]
    return sorted(comments, key=lambda c: c["id"]), len(sizes)


def why_gone(client, repo, old):
    """First stretch goal: look up a held issue that a full read no longer returns."""
    status, _, body = client.get("/repos/%s/issues/%d" % (repo, old["number"]))
    if status == 410:
        return {"reason": "deleted", "detail": "GitHub says the issue was deleted"}
    if status == 404:
        return {"reason": "not found", "detail": "GitHub answers 404 for it"}
    if status != 200 or not isinstance(body, dict):
        raise Stop("GitHub did not say what became of issue %s (status %d), so nothing is saved" % (old["node_id"], status))
    now_in, now = repo_in_url(body.get("repository_url")), as_fields(body)
    if now_in != repo or now["node_id"] != old["node_id"]:
        return {"reason": "transferred", "detail": "GitHub redirects its old address to %s#%d, node ID %s"
                                                   % (now_in or "another repository", now["number"], now["node_id"]),
                "shown": "now node ID %s" % now["node_id"]}
    if "pull_request" in body:
        return {"reason": "now a pull request", "detail": "GitHub now marks this item as a pull request"}
    raise Stop("issue %s is still in the repository and the full read did not return it. The read was not "
               "complete, so nothing is saved" % old["node_id"])


# ---------------------------------------------------------------- memory: state.json


def state_doc_path(out_dir):
    """The state description. Beside the default folder it is participant/context/github/sync-state.md."""
    if os.path.basename(os.path.normpath(out_dir)) == "delta" and os.path.basename(os.path.dirname(os.path.normpath(out_dir))) == "github":
        return os.path.join(os.path.dirname(os.path.normpath(out_dir)), "sync-state.md")
    return os.path.join(out_dir, "sync-state.md")


def read_state(out_dir):
    path = os.path.join(out_dir, "state.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            state = json.load(f)
        assert state["schema"] == 1 and isinstance(state["issues"], dict)
        assert state["cursor"] is None or parse(state["cursor"]["time"])
    except (ValueError, KeyError, TypeError, AssertionError):
        raise Stop("%s cannot be read as this skill's memory. Move it aside to start again" % shown_path(path))
    return state


def load_state(out_dir, source, repo, info):
    state = read_state(out_dir)
    if state is None:
        return {"schema": 1, "source": source, "repo": repo, "repo_id": info["id"], "private": info["private"],
                "cursor": None, "issues": {}, "syncs": 0}
    if state.get("source") != source:
        raise Stop("%s holds issues from a %s run, and this is a %s run. One folder holds one source. Use another --out"
                   % (shown_path(out_dir), state.get("source"), source))
    if state.get("repo_id") != info["id"]:
        raise Stop("%s holds another repository's issues. One folder holds one repository. Use another --out" % shown_path(out_dir))
    state["repo"] = repo          # a repository can be renamed. Its id cannot
    return state


def kept(record):
    return {"node_id": record["node_id"], "comments": record["comments"], **{field: record[field] for field in KEPT}}


def digest(issues):
    """A SHA-256 of what is held about the issues in the repository, and nothing about when it was synced.

    Two local copies with the same digest hold the same repository (criterion 7).
    """
    present = sorted((kept(r) for r in issues.values() if r["status"] == "present"), key=lambda r: r["node_id"])
    return hashlib.sha256(json.dumps(present, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def merge(state, fetched, gone, started):
    """Fold what was fetched into what is held, matching on the node ID, so nothing is ever held twice."""
    held, found = state["issues"], {"new": [], "changed": [], "same": [], "back": [], "gone": []}
    for node, record in fetched.items():
        old = held.get(node)
        if old is None:
            found["new"].append(node)
        elif old["status"] != "present":
            found["back"].append(node)
        elif kept(old) != kept(record):
            what = [field for field in KEPT if old[field] != record[field]] + (["comments"] if old["comments"] != record["comments"] else [])
            found["changed"].append((node, what))
        else:
            found["same"].append(node)
        held[node] = dict(record, status="present", first_seen=old["first_seen"] if old else started, last_fetched=started)
    for node, why in gone.items():
        held[node].update(status="gone", since=started, **why)
        found["gone"].append(node)
    return found


# ---------------------------------------------------------------- what is written


def one_line(text):
    """Text on one line, with nothing that could start Markdown structure. Titles are other people's writing."""
    return " ".join(str(text).split()).replace("|", "\\|").replace("[", "(").replace("]", ")").replace("`", "'") or "(empty)"


def state_words(record):
    return record["state"] + (" (%s)" % one_line(record["state_reason"]) if record["state_reason"] else "")


def render_issues(state, notes):
    records = sorted(state["issues"].values(), key=lambda r: r["number"])
    note = lambda r: "`notes/%s.md`" % r["node_id"] if r["node_id"] + ".md" in notes else ""
    head = ["| Issue | Title | State | Updated | Labels | Comments | Node ID | Last fetched | Your notes |", "|---|---|---|---|---|---|---|---|---|"]
    row = lambda r: "| #%d | %s | %s | %s | %s | %d | `%s` | %s | %s |" % (
        r["number"], one_line(r["title"]), state_words(r), r["updated_at"] or "not given",
        ", ".join(one_line(name) for name in r["labels"]), len(r["comments"]), r["node_id"], r["last_fetched"], note(r))
    out = ["# Issues of the repository", "",
           "Generated by the github-delta-sync skill from %s. Do not edit this file: the next sync replaces it."
           % ("a made-up GitHub, `fake_github.py`. The repository, its issues and its logins are invented" if state["source"] == "fake" else "GitHub"),
           "Your own notes on an issue go in `notes/<node ID>.md`, which the sync never writes to.", "",
           "| | |", "|---|---|",
           "| Repository | `%s`, repository id `%d` |" % (state["repo"], state["repo_id"]),
           "| Cursor | %s |" % state["cursor"]["time"],
           "| Digest of the local state | `%s` |" % digest(state["issues"])]
    for title, group in (("Open", [r for r in records if r["status"] == "present" and r["state"] == "open"]),
                         ("Closed", [r for r in records if r["status"] == "present" and r["state"] != "open"])):
        out += ["", "## %s (%d)" % (title, len(group)), ""] + (head + [row(r) for r in group] if group else ["none"])
    gone = [r for r in records if r["status"] != "present"]
    out += ["", "## No longer in the repository (%d)" % len(gone), ""]
    if gone:
        out += ["Held from an earlier sync, and no longer returned by a full read. Nothing here has been deleted locally.",
                "Each row is the issue as it was when last fetched.", "",
                "| Issue | Title | Last known state | Why | Noticed at the sync of | Node ID | Your notes |", "|---|---|---|---|---|---|---|"]
        out += ["| #%d | %s | %s | **%s**: %s | %s | `%s` | %s |" % (r["number"], one_line(r["title"]), state_words(r), r["reason"],
                                                                 one_line(r["detail"]), r["since"], r["node_id"], note(r)) for r in gone]
    else:
        out += ["none"]
    return "\n".join(out) + "\n"


def render_state_doc(state, out_dir, local_now, stale_hours):
    last, cursor = state["last"], state["cursor"]
    fake = state["source"] == "fake"
    return "\n".join([
        "# Sync state: issues of one GitHub repository", "",
        "Generated by the github-delta-sync skill from `%s`, which is where the cursor is kept. Do not edit this file:"
        % shown_path(os.path.join(out_dir, "state.json")).replace(os.sep, "/"),
        "it is rewritten after every successful sync.", "",
        "## The last successful point", "",
        "| | |", "|---|---|",
        "| Repository | `%s`, repository id `%d`%s |" % (state["repo"], state["repo_id"], ", a made-up repository" if fake else ""),
        "| Cursor | %s |" % cursor["time"],
        "| The cursor is | %s |" % cursor["taken_from"],
        "| That sync was | %s |" % last["kind"],
        "| It asked for | %s |" % last["asked"],
        "| It fetched | %s of the %d held |" % (plural(last["fetched"], "issue"), last["held"]),
        "| It found | %d new, %d changed, %d unchanged, %d no longer in the repository |" % (last["new"], last["changed"], last["unchanged"], last["gone"]),
        "| Successful syncs so far | %d |" % state["syncs"],
        "| Digest of the local state | `%s` |" % digest(state["issues"]),
        "| How stale, when this file was written | %s |" % staleness(state, local_now, stale_hours),
        "", "## What the cursor is", "",
        "The cursor is a time on GitHub's own clock. Every answer GitHub gives carries a Date header. The sync reads",
        "it from its first answer, before it reads any issue, and that time becomes the cursor if the whole sync",
        "succeeds. This machine's clock is never used for the cursor, so a wrong clock here cannot move it.",
        "", "## How a delta uses it", "",
        "A delta asks GitHub for the issues updated at or after the cursor less a margin of %d seconds, and fetches" % MARGIN_SECONDS,
        "the comments of those issues and no others. The margin is there because GitHub's servers do not all learn",
        "of a change at the same instant: a change can be stamped a little before the cursor and still not have been",
        "shown to the sync that set it. An issue returned a second time because of the margin is matched to the one",
        "already held by its node ID, so nothing is held twice.",
        "", "## How it advances", "",
        "1. The sync notes GitHub's clock, asks for the changed issues and fetches their comments. All of it is held",
        "   in memory. Nothing is written yet.",
        "2. If any request fails, the run stops. No file is written. The cursor, the issues and this file are exactly",
        "   as the last successful sync left them.",
        "3. Only when every changed issue has been fetched are the files written: `issues.md`, then `state.json`,",
        "   which holds the cursor, and last this file. The new cursor is the time noted in step 1.",
        "",
        "So the next sync after a failed one asks from the same cursor again, and fetches every issue the failed one",
        "would have. A change made while a sync is running is stamped after the time noted in step 1, so the next",
        "sync asks for it.",
        "", "## What a delta cannot see", "",
        "An issue that was deleted, or transferred to another repository, is not returned as changed. `--verify`",
        "compares the local copy with a full read and says when they differ, and `--full` finds out why and flags",
        "the issue. Neither removes anything locally."]) + "\n"


# ---------------------------------------------------------------- the run


def run(client, out_dir, source, repo, full=False, verify=False, margin=MARGIN_SECONDS, local_now=None, stale_hours=STALE_HOURS):
    local_now = local_now or utc_now()
    notes_before = notes_checksums(out_dir)
    # Everything is read first. Nothing is written until every request has been answered.
    try:
        info, started = read_repo(client, repo)
        state = load_state(out_dir, source, repo, info)
        cursor = state["cursor"]
        say("repository id %d, %s" % (info["id"], "private" if info["private"] else "public"))
        say("GitHub's clock at the start of this sync: %s, from the Date header of its first answer. This machine's clock: "
            "%s, %s. This machine's clock is not used for the cursor" % (started, local_now, clock_difference(local_now, started)))
        if cursor:
            say("cursor before this sync: %s" % cursor["time"])
            say("how stale: %s" % staleness(state, local_now, stale_hours))
        else:
            say("cursor before this sync: none. This is the first sync, so every issue is read")
        whole = full or verify or cursor is None
        since = None if whole else since_for(cursor["time"], margin)
        if since:
            asked = "issues updated at or after %s: the cursor less a margin of %d seconds" % (since, margin)
        else:
            asked = "every issue in the repository" + (", ignoring the cursor (%s)" % ("--verify" if verify else "--full") if cursor else "")
        say("asking for %s" % asked)
        issues, pulls, sizes = read_issues(client, repo, since)
        say("GitHub returned %s in %s (%s). Pull requests left out: %d (%s). Issues: %d"
            % (plural(len(issues) + pulls, "item"), plural(len(sizes), "request"), " + ".join(str(size) for size in sizes),
               pulls, PULL_REQUEST_RULE, len(issues)))
        early = [i for i in issues if since and (i["updated_at"] or "") < since]
        if early:
            say("NOTE: %s returned were last updated before the time asked for. They are fetched all the same" % plural(len(early), "issue"))
        fetched, comment_requests = {}, 0
        for issue in issues:
            comments, requests = read_comments(client, repo, issue)
            fetched[issue["node_id"]] = dict(issue, comments=comments)
            comment_requests += requests
        missing = sorted(node for node, old in state["issues"].items() if whole and old["status"] == "present" and node not in fetched)
        gone = {} if verify else {node: why_gone(client, repo, state["issues"][node]) for node in missing}
    except RateLimited:
        say("INCOMPLETE: GitHub rate-limited this run. Nothing was written. Run it again later.")
        return 2

    if verify:
        theirs = {node: dict(record, status="present") for node, record in fetched.items()}
        ours = {node: r for node, r in state["issues"].items() if r["status"] == "present"}
        differ = sorted(node for node in set(ours) & set(theirs) if kept(ours[node]) != kept(theirs[node]))
        say("VERIFY: digest of the local copy:  %s (%s)" % (digest(state["issues"]), plural(len(ours), "issue")))
        say("VERIFY: digest of a full read now: %s (%s)" % (digest(theirs), plural(len(theirs), "issue")))
        for word, nodes in (("held locally and not returned by GitHub", missing), ("returned by GitHub and not held locally", sorted(set(theirs) - set(ours))),
                            ("held with different fields or comments", differ)):
            for node in nodes:
                say("  DIFFERENT: issue %s is %s" % (node, word))
        same = digest(state["issues"]) == digest(theirs)
        say("VERIFY: %s" % ("the local copy and a full read are THE SAME" if same else
                            "the local copy and a full read DIFFER. Run a sync, or --full to find issues that were deleted or transferred"))
        say("requests made: %d, every one a GET. Nothing was written, and the cursor was not moved" % client.count)
        return 0 if same else 3

    held_before = sum(r["status"] == "present" for r in state["issues"].values())
    found = merge(state, fetched, gone, started)
    not_fetched = held_before - len(found["changed"]) - len(found["same"]) - len(gone)
    kind = "the first sync, a read of every issue" if cursor is None else ("a full read of every issue, with --full" if full else "a delta")
    for node in found["new"]:
        say("  fetched: issue %s, number %d. NEW" % (node, fetched[node]["number"]))
    for node, what in found["changed"]:
        say("  fetched: issue %s, number %d. CHANGED (%s)" % (node, fetched[node]["number"], ", ".join(what)))
    for node in found["back"]:
        say("  fetched: issue %s, number %d. In the repository again" % (node, fetched[node]["number"]))
    if since:
        for node in found["same"]:
            say("  fetched: issue %s, number %d. The same as held. It was returned because of the margin" % (node, fetched[node]["number"]))
    for node in found["gone"]:
        record = state["issues"][node]
        say("  FLAGGED, not deleted: issue %s, number %d, is no longer in the repository: %s%s. Last known state: %s"
            % (node, record["number"], record["reason"], ", " + record["shown"] if record.get("shown") else "", state_words(record)))
    present = sum(r["status"] == "present" for r in state["issues"].values())
    say("fetched: %s, in %s for their comments. Not fetched: %d"
        % (plural(len(fetched), "issue"), plural(comment_requests, "request"), not_fetched))
    say("issues in the repository: %d. This sync: %d new, %d changed, %d unchanged (%d not fetched, %d fetched and found the same), "
        "%d no longer in the repository" % (present, len(found["new"]) + len(found["back"]), len(found["changed"]),
                                           not_fetched + len(found["same"]), not_fetched, len(found["same"]), len(gone)))
    state.update(cursor={"time": started, "taken_from": CURSOR_SOURCE}, syncs=state["syncs"] + 1,
                 last={"kind": kind, "asked": asked, "fetched": len(fetched), "held": present, "new": len(found["new"]) + len(found["back"]),
                       "changed": len(found["changed"]), "unchanged": not_fetched + len(found["same"]), "gone": len(gone)})
    write_text(os.path.join(out_dir, "issues.md"), render_issues(state, notes_before), out_dir)
    write_text(os.path.join(out_dir, "state.json"), json.dumps(state, indent=1, ensure_ascii=False, sort_keys=True) + "\n", out_dir)  # the cursor
    write_text(state_doc_path(out_dir), render_state_doc(state, out_dir, local_now, stale_hours), out_dir)
    say("cursor after this sync: %s, GitHub's clock at its start" % started)
    say("local state digest: %s (%s in the repository; %d more kept that are no longer in it)"
        % (digest(state["issues"]), plural(present, "issue"), len(state["issues"]) - present))
    notes_after = notes_checksums(out_dir)
    say("notes: %s, opened for reading only. SHA-256 before and after this sync:" % plural(len(notes_before), "file"))
    for name in sorted(set(notes_before) | set(notes_after)):
        say("  notes/%s  before %s  after %s  %s" % (name, notes_before.get(name, "absent"), notes_after.get(name, "absent"),
                                                    "same" if notes_before.get(name) == notes_after.get(name) else "DIFFERENT"))
    if client.waits:
        say("this run waited %d time(s) for GitHub's rate limit" % len(client.waits))
    say("requests made: %d, every one a GET (1 repository, %d listing, %d comments, %d look-ups)"
        % (client.count, len(sizes), comment_requests, client.count - 1 - len(sizes) - comment_requests))
    say("written: issues.md, state.json and %s" % shown_path(state_doc_path(out_dir)).replace(os.sep, "/"))
    return 0 if notes_before == notes_after else 1


def cursor_line(out_dir):
    try:
        state = read_state(out_dir)
    except Stop:
        return "The memory file cannot be read, so the cursor is not known."
    if state is None or not state["cursor"]:
        return "There is no cursor yet."
    return "The cursor is where it was: %s." % state["cursor"]["time"]


def status(out_dir, local_now=None, stale_hours=STALE_HOURS):
    state = read_state(out_dir)
    if state is None or not state["cursor"]:
        say("no successful sync has been recorded in %s. There is no cursor" % shown_path(out_dir))
        return 1
    say("repository id %d, from a %s run" % (state["repo_id"], state["source"]))
    say("cursor: %s. It is %s" % (state["cursor"]["time"], state["cursor"]["taken_from"]))
    say("how stale: %s" % staleness(state, local_now or utc_now(), stale_hours))
    say("local state digest: %s" % digest(state["issues"]))
    say("nothing was contacted and nothing was written")
    return 0


def main(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    default_out = os.path.join(here, "..", "..", "context", "github", "delta")
    parser = argparse.ArgumentParser(description="Delta synchronization of one GitHub repository's issues. Read-only.")
    parser.add_argument("--source", choices=("live", "fake"))
    parser.add_argument("--repo", help="with --source live: the repository, as owner/name")
    parser.add_argument("--out", help="folder to write into (default: participant/context/github/delta)")
    parser.add_argument("--full", action="store_true", help="read every issue again, ignoring the cursor")
    parser.add_argument("--verify", action="store_true", help="compare the local copy with a full read. Writes nothing")
    parser.add_argument("--status", action="store_true", help="say where the cursor is and how stale. Contacts nothing")
    parser.add_argument("--stale-hours", type=int, default=STALE_HOURS)
    parser.add_argument("--fake-step", type=int, default=0, choices=(0, 1, 2, 3), help="with --source fake: the made-up repository at this step")
    parser.add_argument("--fake-fail-issue", type=int, help="with --source fake: GitHub fails when asked for this issue's comments")
    args = parser.parse_args(argv)
    out = os.path.normpath(args.out or default_out)
    try:
        if args.status:
            return status(out, stale_hours=args.stale_hours)
        if not args.source:
            raise Stop("give --source fake or --source live, or --status")
        if args.full and args.verify:
            raise Stop("--full and --verify do not go together")
        if args.source == "fake":
            sys.path.insert(0, here)
            import fake_github
            fake = fake_github.FakeGitHub(args.fake_step)
            if args.fake_fail_issue:
                fake.fail("/repos/%s/issues/%d/comments" % (fake_github.REPO, args.fake_fail_issue), 500)
            return run(Client(fake.get), out, "fake", fake_github.REPO, full=args.full, verify=args.verify,
                       local_now=fake.now, stale_hours=args.stale_hours)
        if args.fake_step or args.fake_fail_issue:
            raise Stop("--fake-step and --fake-fail-issue only go with --source fake")
        if not good_repo(args.repo):
            raise Stop("a live run needs --repo, the repository as owner/name")
        if not args.out:
            raise Stop("a live run needs --out, a folder outside this repository, because real issues can be private")
        if not os.environ.get("GITHUB_TOKEN"):
            raise Stop("the environment variable GITHUB_TOKEN is not set")
        return run(Client(live_get), out, "live", args.repo, full=args.full, verify=args.verify, stale_hours=args.stale_hours)
    except Stop as stop:
        say("STOPPED: %s." % stop)
        say("Nothing was written. %s" % cursor_line(out))
        return 1


if __name__ == "__main__":
    sys.exit(main())
