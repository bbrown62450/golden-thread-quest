#!/usr/bin/env python3
"""Preview a new GitHub issue: check it against the repository's conventions and show exactly what would be sent.

See SKILL.md in this folder for what it does and the rules it follows.

    preview.py --source fake|live --draft DRAFT.md --index INDEX.md --allowlist FILE
               [--despite-duplicate OWNER/NAME#N] [--payload-out FILE] [--state FOLDER] [--fake-store FILE]

It only ever sends GET requests. There is no code here that creates, edits, labels or closes anything. It builds
the payload a later write would send, shows it, and stops.

Exit codes: 0 the preview is READY; 1 NOT READY, refused or stopped; 2 rate-limited.
"""
import argparse
import base64
import datetime
import email.utils
import hashlib
import importlib.util
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
API_HOST = "api.github.com"
PER_PAGE = 100
MAX_WAITS, MAX_WAIT_SECONDS, DEFAULT_WAIT_SECONDS = 3, 15, 10
LIMIT_MINUTES = 15
DRAFT_FORMAT = "github-issue-draft/1"
PREVIEW_FORMAT = "github-issue-preview/1"
STAMP = "%Y-%m-%dT%H:%M:%SZ"
REPO_NAME = re.compile(r"^[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}$")
TEMPLATE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,80}\.md$")
LOGIN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")
ISSUE_NAME = re.compile(r"^([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)#(\d+)$")
CITATION = re.compile(r'^- ([a-z]+): (\S+) lines? (\d+)(?:-(\d+))?: "(.*)"$')
TEMPLATE_FOLDER = ".github/ISSUE_TEMPLATE"
OPTIONAL = re.compile(r"\(optional\)\s*$", re.I)
CITED = ("title", "body", "labels", "assignees", "milestone")


class Stop(Exception):
    """The run cannot go on."""


class RateLimited(Exception):
    pass


def say(text=""):
    print(("github-preview: " + text) if text else "github-preview:", flush=True)


def q(value):
    return json.dumps(value, ensure_ascii=False)


def plural(count, word, many=None):
    return "%d %s" % (count, word if count == 1 else many or word + "s")


def shown_path(path):
    try:
        relative = os.path.relpath(path)
    except ValueError:
        return os.path.basename(path)
    return os.path.basename(path) if relative.startswith("..") else relative


def load_search():
    """The github-duplicate-search skill, loaded from its folder and not changed."""
    path = os.path.join(HERE, "..", "github-duplicate-search", "search.py")
    if not os.path.isfile(path):
        raise Stop("the github-duplicate-search skill is not beside this one, and the preview runs it")
    spec = importlib.util.spec_from_file_location("duplicate_search_for_the_preview", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------- talking to GitHub: reading only


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def live_send(method, path, params=None, body=None):
    """One GET to api.github.com. Any other method is refused here, before anything is sent."""
    if method != "GET" or body is not None:
        raise RuntimeError("the preview may only send GET")
    url = "https://%s%s" % (API_HOST, path)
    if params:
        url += "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, method="GET")
    request.add_header("Authorization", "Bearer %s" % os.environ.get("GITHUB_TOKEN"))
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("X-GitHub-Api-Version", "2022-11-28")
    request.add_header("User-Agent", "github-create-issue-preview-skill")
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


class Connection:
    """Every request goes through here. It has one method, get. There is no way to write."""

    def __init__(self, send, sleep=time.sleep, clock=time.time):
        self._send, self._sleep, self._clock = send, sleep, clock
        self.asked, self.waits, self.scopes, self.now = [], [], None, None

    def get(self, path, params=None):
        waited = 0
        while True:
            status, headers, answer = self._send("GET", path, dict(params or {}), None)
            self.asked.append(("GET", path))
            head = {str(name).lower(): str(value) for name, value in (headers or {}).items()}
            if "x-oauth-scopes" in head:
                self.scopes = head["x-oauth-scopes"]
            try:
                when = email.utils.parsedate_to_datetime(head["date"])
                self.now = (when if when.tzinfo else when.replace(tzinfo=datetime.timezone.utc)).astimezone(datetime.timezone.utc).strftime(STAMP)
            except (KeyError, TypeError, ValueError):
                pass
            limited = status == 429 or (status == 403 and (head.get("x-ratelimit-remaining") == "0" or "retry-after" in head))
            if not limited:
                break
            seconds = int(head["retry-after"]) if head.get("retry-after", "").isdigit() else (
                max(1, int(head["x-ratelimit-reset"]) - int(self._clock()) + 1) if head.get("x-ratelimit-reset", "").isdigit() else DEFAULT_WAIT_SECONDS)
            if seconds > MAX_WAIT_SECONDS or waited == MAX_WAITS:
                raise RateLimited()
            waited += 1
            say("rate limited by GitHub. Wait %d of %d: %d seconds" % (waited, MAX_WAITS, seconds))
            self._sleep(seconds)
            self.waits.append(seconds)
        if status == 401:
            raise Stop("GitHub rejected the token (401). Check GITHUB_TOKEN. A token also stops working when it expires")
        if status in (301, 302, 307, 308):
            raise Stop("GitHub redirected %s. The repository was renamed or moved, and the preview does not follow it" % path)
        return status, head, answer


def read_all(conn, path, params, what):
    rows, page = [], 1
    while True:
        status, head, answer = conn.get(path, dict(params, per_page=PER_PAGE, page=page))
        if status != 200 or not isinstance(answer, list) or any(not isinstance(row, dict) for row in answer):
            raise Stop("GitHub did not return %s (status %d)" % (what, status))
        rows += answer
        if not any('rel="next"' in part for part in head.get("link", "").split(",")):
            return rows
        if not answer or page > 50:
            raise Stop("GitHub's pages of %s do not end, so the list cannot be trusted" % what)
        page += 1


# ---------------------------------------------------------------- the draft


def outside_fences(lines):
    """Yields (number, line) for the lines that are not inside a fenced code block."""
    fence = None
    for number, line in enumerate(lines):
        mark = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        if mark and fence is None:
            fence = mark.group(1)[0]
        elif mark and mark.group(1)[0] == fence:
            fence = None
        elif fence is None:
            yield number, line


def sections_of(lines):
    """The level-3 sections of some Markdown: [(name, text under it)], and whatever comes before the first one."""
    starts = [(number, line[4:].strip()) for number, line in outside_fences(lines) if line.startswith("### ")]
    before = "\n".join(lines[:starts[0][0]] if starts else lines)
    found = [(name, "\n".join(lines[number + 1:(starts[position + 1][0] if position + 1 < len(starts) else len(lines))]))
             for position, (number, name) in enumerate(starts)]
    return found, before


def read_draft(path):
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except (OSError, UnicodeDecodeError):
        raise Stop("the draft %s cannot be read" % shown_path(path))
    if not text.startswith("---\n") or "\n---\n" not in text[3:]:
        raise Stop("the draft has no front matter")
    end = text.index("\n---\n", 3)
    front = {}
    for line in text[4:end].split("\n"):
        key, colon, value = line.partition(": ")
        try:
            front[key] = json.loads(value) if colon else None
        except ValueError:
            raise Stop("the draft's line \"%s\" cannot be read. Every value is written as JSON" % key[:40])
    strings = lambda value: isinstance(value, list) and all(isinstance(one, str) and one.strip() for one in value)
    if front.get("format") != DRAFT_FORMAT:
        raise Stop("the draft is not in the format %s" % DRAFT_FORMAT)
    if not isinstance(front.get("repository"), str) or not REPO_NAME.match(front["repository"]):
        raise Stop("the draft needs a repository, as owner/name")
    if not isinstance(front.get("template"), str) or not TEMPLATE_NAME.match(front["template"]):
        raise Stop("the draft needs a template: the name of a .md file in the repository's %s folder" % TEMPLATE_FOLDER)
    if not isinstance(front.get("title"), str) or not front["title"].strip() or "\n" in front["title"] or len(front["title"]) > 256:
        raise Stop("the draft needs a title, on one line, of at most 256 characters")
    if not strings(front.get("labels", [])) or not strings(front.get("assignees", [])):
        raise Stop("the draft's labels and assignees must be lists of names")
    if front.get("milestone") is not None and not isinstance(front["milestone"], str):
        raise Stop("the draft's milestone must be a title, or null")
    lines = text[end + 5:].split("\n")
    marks = {line: number for number, line in outside_fences(lines) if line in ("## Body", "## Sources")}
    if "## Body" not in marks or "## Sources" not in marks or marks["## Sources"] < marks["## Body"]:
        raise Stop("the draft needs a \"## Body\" heading and, after it, a \"## Sources\" heading")
    body_lines = lines[marks["## Body"] + 1:marks["## Sources"]]
    sections, before = sections_of(body_lines)
    first = next((number for number, line in outside_fences(body_lines) if line.startswith("### ")), len(body_lines))
    return {"path": path, "repository": front["repository"], "template": front["template"], "title": front["title"],
            "labels": front.get("labels", []), "assignees": front.get("assignees", []), "milestone": front.get("milestone"),
            "sections": sections, "before": before.strip(), "body": "\n".join(body_lines[first:]).strip("\n"),
            "sources": [line for line in lines[marks["## Sources"] + 1:] if line.strip()], "digest": hashlib.sha256(text.encode("utf-8")).hexdigest()}


def bare(text):
    """A section's text with HTML comments and all white space taken out: what is left is what somebody wrote."""
    return "".join(re.sub(r"<!--.*?-->", "", text, flags=re.S).split())


# ---------------------------------------------------------------- the checks. Each returns (lines to show, problems)


def read_template(conn, repo, name):
    """The repository's own template, read from the repository. Returns {labels, sections: [(name, required, placeholder)]}."""
    status, _, answer = conn.get("/repos/%s/contents/%s/%s" % (repo, TEMPLATE_FOLDER, urllib.parse.quote(name)))
    if status == 404:
        status_list, _, listing = conn.get("/repos/%s/contents/%s" % (repo, TEMPLATE_FOLDER))
        have = sorted(row.get("name") for row in listing if isinstance(row, dict)) if status_list == 200 and isinstance(listing, list) else []
        raise Stop("the repository has no issue template named %s. %s" % (q(name), "It has: %s" % ", ".join(q(one) for one in have) if have else
                   "It has no %s folder that this connection can read" % TEMPLATE_FOLDER))
    if status != 200 or not isinstance(answer, dict) or answer.get("encoding") != "base64" or not isinstance(answer.get("content"), str):
        raise Stop("GitHub did not return the template (status %d). Reading it needs permission to read the repository's files" % status)
    try:
        text = base64.b64decode(answer["content"]).decode("utf-8").replace("\r\n", "\n")
    except (ValueError, UnicodeDecodeError):
        raise Stop("the template is not text that can be read")
    labels, body = [], text
    if text.startswith("---\n") and "\n---\n" in text[3:]:
        end = text.index("\n---\n", 3)
        front, body = text[4:end].split("\n"), text[end + 5:]
        for number, line in enumerate(front):
            if line.startswith("labels:"):
                value = line[len("labels:"):].strip()
                if value.startswith("["):
                    try:
                        labels = [str(one) for one in json.loads(value.replace("'", '"'))]
                    except ValueError:
                        raise Stop("the template's labels line cannot be read")
                elif value:
                    labels = [part.strip().strip("'\"") for part in value.split(",")]
                else:
                    labels = [after.strip()[2:].strip().strip("'\"") for after in front[number + 1:] if after.strip().startswith("- ")]
    sections, _ = sections_of(body.split("\n"))
    if not sections:
        raise Stop("the template has no level-3 headings (### ...), so it has no sections this workflow can read")
    return {"labels": [one for one in labels if one], "sections": [(name, not OPTIONAL.search(name), text) for name, text in sections]}


def check_template(draft, template):
    """Criteria 1 and 3: the draft's sections are the template's, in its order, and no required one is empty."""
    lines, problems = [], []
    wanted, have = [name for name, _, _ in template["sections"]], [name for name, _ in draft["sections"]]
    written = dict(draft["sections"])
    for name, required, placeholder in template["sections"]:
        kind = "required" if required else "optional"
        if name not in written:
            lines.append("%s (%s): MISSING from the draft" % (q(name), kind))
            if required:
                problems.append("the required template section %s is missing from the draft" % q(name))
        elif not bare(written[name]) or bare(written[name]) == bare(placeholder):
            lines.append("%s (%s): EMPTY. It holds nothing but the template's own placeholder or blank lines" % (q(name), kind))
            if required:
                problems.append("the required template section %s is empty" % q(name))
        else:
            lines.append("%s (%s): filled in, %s" % (q(name), kind, plural(len(written[name].strip().split("\n")), "line")))
    for name in have:
        if name not in wanted:
            problems.append("the draft has a section %s that the template does not have" % q(name))
    if len(set(have)) != len(have):
        problems.append("the draft has the same section twice")
    if [name for name in have if name in wanted] != [name for name in wanted if name in have]:
        problems.append("the draft's sections are not in the template's order")
    if draft["before"]:
        problems.append("the draft's body has text before its first section, which the template does not have")
    return lines, problems


def check_sources(draft):
    """Criterion 7: every citation names a file beside the draft and words that really are on the lines it names."""
    lines, problems, cited = [], [], set()
    base = os.path.dirname(os.path.realpath(draft["path"]))
    for line in draft["sources"]:
        found = CITATION.match(line)
        if not found or found.group(1) not in CITED:
            problems.append("a line under Sources is not a citation this workflow can read: %s" % q(line[:80]))
            continue
        field, where, first, last, words = found.group(1), found.group(2), int(found.group(3)), int(found.group(4) or found.group(3)), found.group(5)
        path = os.path.realpath(os.path.join(base, where))
        if os.path.isabs(where) or os.path.commonpath([base, path]) != base:
            problems.append("the citation for %s points outside the draft's folder" % field)
            continue
        try:
            with open(path, encoding="utf-8") as f:
                source = f.read().split("\n")
        except (OSError, UnicodeDecodeError):
            problems.append("the citation for %s names a file that cannot be read: %s" % (field, where))
            continue
        there = " ".join(" ".join(source[first - 1:last]).split()) if 1 <= first <= last <= len(source) else None
        if there is None or not words.strip() or " ".join(words.split()) not in there:
            problems.append("the citation for %s is NOT TRUE: the words quoted are not on %s %s of %s"
                            % (field, "line" if first == last else "lines", first if first == last else "%d-%d" % (first, last), where))
            continue
        cited.add(field)
        lines.append("%s: %s, %s. The words quoted are there" % (field, where, "line %d" % first if first == last else "lines %d-%d" % (first, last)))
    needed = ["title", "body"] + [field for field in ("labels", "assignees", "milestone") if draft[field]]
    for field in needed:
        if field not in cited:
            problems.append("the draft gives no source for its %s" % field)
    return lines, problems


def check_existing(conn, draft, template):
    """Criterion 2: every label, assignee and the milestone is one the repository has. Returns (lines, problems, what was found)."""
    lines, problems, repo = [], [], draft["repository"]
    have = {row["name"].casefold(): row for row in read_all(conn, "/repos/%s/labels" % repo, {}, "the repository's labels") if isinstance(row.get("name"), str)}
    labels = []
    for name in draft["labels"]:
        row = have.get(name.casefold())
        if row is None:
            lines.append("label %s: DOES NOT EXIST in the repository" % q(name))
            problems.append("the label %s does not exist in the repository. The preview does not invent labels, and GitHub would create one without saying" % q(name))
        elif row["name"] in labels:
            problems.append("the label %s is in the draft twice" % q(name))
        else:
            labels.append(row["name"])
            lines.append("label %s: exists, id %s" % (q(row["name"]), row.get("id")))
    for name in template["labels"]:
        if name.casefold() not in [one.casefold() for one in draft["labels"]]:
            problems.append("the template gives issues of this kind the label %s, and the draft does not have it" % q(name))
    people = []
    for login in draft["assignees"]:
        if not LOGIN.match(login) or login.casefold() in [one.casefold() for one in people]:
            problems.append("the assignee %s is not the shape of a login, or is in the draft twice" % q(login))
            continue
        status, _, _ = conn.get("/repos/%s/assignees/%s" % (repo, urllib.parse.quote(login, safe="")))
        if status == 204:
            people.append(login)
            lines.append("assignee %s: can be assigned in this repository" % q(login))
        elif status == 404:
            lines.append("assignee %s: CANNOT BE ASSIGNED in this repository" % q(login))
            problems.append("GitHub says %s cannot be assigned to issues in this repository" % q(login))
        else:
            raise Stop("GitHub did not say whether %s can be assigned (status %d)" % (q(login), status))
    milestone = None
    milestones = read_all(conn, "/repos/%s/milestones" % repo, {"state": "all"}, "the repository's milestones")
    if draft["milestone"] is None:
        lines.append("milestone: none asked for")
    else:
        found = [row for row in milestones if row.get("title") == draft["milestone"]]
        if len(found) != 1:
            lines.append("milestone %s: %s" % (q(draft["milestone"]), "DOES NOT EXIST in the repository" if not found else "MORE THAN ONE has that title"))
            problems.append("the repository has %s milestone with exactly the title %s" % ("no" if not found else "more than one", q(draft["milestone"])))
        elif found[0].get("state") != "open":
            lines.append("milestone %s: exists and is CLOSED" % q(draft["milestone"]))
            problems.append("the milestone %s is closed" % q(draft["milestone"]))
        else:
            milestone = {"number": found[0]["number"], "title": found[0]["title"]}
            lines.append("milestone %s: exists, is open, number %d" % (q(milestone["title"]), milestone["number"]))
    lines.append("the repository has %s and %s to choose from" % (plural(len(have), "label"), plural(len(milestones), "milestone")))
    return lines, problems, {"labels": labels, "assignees": people, "milestone": milestone}


def check_duplicates(draft, index_path, despite):
    """Criterion 4: the duplicate search of the local index, and what its result does to the preview."""
    search = load_search()
    try:
        index = search.read_index(search.load_indexer(), index_path)
    except search.Stop as why:
        raise Stop("the duplicate search could not run: %s" % why)
    index["path"] = index_path
    proposal = {"title": draft["title"], "repository": draft["repository"], "labels": draft["labels"], "text": draft["body"]}
    candidates, looked, nothing, skipped = search.search(proposal, index)
    lines = ["searched the local index %s: %s. %d matched on nothing, %d matched on fewer than %d signals beyond the title and are not candidates"
             % (shown_path(index_path), plural(len(index["issues"]), "issue"), nothing, len(looked), search.NEEDED)]
    problems, close = [], []
    for row in candidates:
        name = search.name_of(row)
        matched = [label for key, label, _ in search.SIGNALS if row["found"][key][0] == "match"]
        lines.append("candidate %s %s, %s: %s confidence, %d of %d points (%s). The search recommends: %s"
                     % (name, q(row["title"]), row["state"], row["confidence"], row["points"], search.MOST, ", ".join(matched), row["recommendation"]))
        if row["recommendation"] == "close-as-duplicate":
            close.append(name)
    for name in despite:
        if name not in close:
            problems.append("--despite-duplicate names %s, which the search did not report as a likely duplicate to close against" % name)
    stopping = [name for name in close if name not in despite]
    for name in stopping:
        problems.append("the duplicate search reports %s as a LIKELY DUPLICATE at high confidence, open and in the same repository. To go on anyway, "
                        "a person runs the preview again with --despite-duplicate %s" % (name, name))
    overridden = [name for name in close if name in despite]
    for name in overridden:
        lines.append("OVERRIDDEN BY A PERSON: the preview was told to go on despite %s. That is recorded in the preview" % name)
    linked = [search.name_of(row) for row in candidates if row["recommendation"] == "link"]
    if linked:
        lines.append("to LINK: the new issue should point to %s. The preview does not add that to the issue's text: a person does" % ", ".join(linked))
    result = "close-as-duplicate" if close else "link" if linked else "proceed"
    lines.append("duplicate result: %s%s" % (result, ". No likely duplicate was found" if result == "proceed" else ""))
    return lines, problems, {"result": result, "candidates": [search.name_of(row) for row in candidates], "overridden": overridden,
                              "index_fingerprint": index["fingerprint"]}


def check_permission(conn, about, draft):
    """Criterion 4: what GitHub says the account may do here, and what GitHub does not say."""
    may = about.get("permissions") if isinstance(about.get("permissions"), dict) else None
    lines, problems = [], []
    if may is None:
        lines.append("GitHub did not say what the account may do in this repository")
        problems.append("GitHub did not say what the account may do in this repository")
    else:
        lines.append("GitHub says the ACCOUNT may: %s" % ", ".join("%s: %s" % (key, "yes" if may[key] else "no") for key in sorted(may)))
        if not may.get("pull"):
            problems.append("GitHub says the account may not read this repository, so it could not open an issue in it")
        extras = [field for field in ("labels", "assignees", "milestone") if draft[field]]
        if extras and not any(may.get(key) for key in ("triage", "push", "maintain", "admin")):
            problems.append("the draft sets %s, and GitHub says the account may not triage here. GitHub would create the issue and DROP them without saying" % ", ".join(extras))
    if about.get("archived"):
        problems.append("the repository is archived, and GitHub accepts no new issues in it")
    if about.get("has_issues") is False:
        problems.append("issues are turned off in this repository")
    lines.append("issues are %s in this repository, and it is %s" % ("turned OFF" if about.get("has_issues") is False else "turned on", "ARCHIVED" if about.get("archived") else "not archived"))
    lines.append("The token's scopes, as GitHub reports them: %s" % q(conn.scopes) if conn.scopes is not None else
                 "GitHub reports no scopes for this token, as for a fine-grained token, and does not say what the TOKEN may do. Whether it may "
                 "create an issue is known only when the write is tried. The preview does not try it")
    return lines, problems


# ---------------------------------------------------------------- the payload: built once, here


def build_payload(draft, found):
    """The body of the one request a later write would send. This is the only place it is built."""
    payload = {"title": draft["title"], "body": draft["body"]}
    if found["labels"]:
        payload["labels"] = list(found["labels"])
    if found["assignees"]:
        payload["assignees"] = list(found["assignees"])
    if found["milestone"]:
        payload["milestone"] = found["milestone"]["number"]
    return payload


PAYLOAD_FIELDS = ("title", "body", "labels", "assignees", "milestone")


def payload_bytes(payload):
    """The exact bytes of the payload: what is shown, what is fingerprinted, and what a write would send.

    The fields are written in one fixed order, whatever order the payload holds them in, so that a payload saved
    to a file and read back gives the same bytes. A field this workflow does not know is refused, not sent.
    """
    if set(payload) - set(PAYLOAD_FIELDS):
        raise Stop("the payload holds a field this workflow does not send")
    ordered = [(key, payload[key]) for key in PAYLOAD_FIELDS if key in payload]
    return json.dumps(dict(ordered), ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def fenced(text):
    fence = "`" * max(3, max((len(run) for run in re.findall(r"`+", text)), default=0) + 1)
    return "%s\n%s\n%s" % (fence, text, fence)


def render_payload(record):
    """payload.md: the exact payload, field by field, and as bytes."""
    payload, found = record["payload"], record["found"]
    data = payload_bytes(payload)
    rows = [("title", q(payload["title"]), "text"), ("body", "shown in full below, %d characters" % len(payload["body"]), "text"),
            ("labels", q(payload["labels"]) if "labels" in payload else "not sent: the draft has none", "a list of the names of labels that exist"),
            ("assignees", q(payload["assignees"]) if "assignees" in payload else "not sent: the draft has none", "a list of logins that can be assigned"),
            ("milestone", "%d, which is the number of %s" % (payload["milestone"], q(found["milestone"]["title"])) if "milestone" in payload else "not sent: the draft has none", "the milestone's number, not its title")]
    lines = ["# The exact payload of the new issue", "",
             "**This file is generated by the preview. Nothing was sent.** It shows the one request a later write would send, field by",
             "field and then as the exact bytes. The payload is built once, by the preview, and saved under the fingerprint below. A",
             "write sends those saved bytes and builds nothing of its own.", "",
             "- repository: %s, id %d" % (q(record["repository"]), record["repository_id"]),
             "- request: `%s %s`" % (record["request"]["method"], record["request"]["path"]),
             "- preview fingerprint: `%s`" % record["fingerprint"],
             "- SHA-256 of the payload's bytes: `%s`" % hashlib.sha256(data).hexdigest(),
             "- length of the payload: %d bytes" % len(data),
             "- draft it was built from: SHA-256 `%s`" % record["draft_digest"], "",
             "## Field by field", "", "| Field | Value | What GitHub takes it as |", "|---|---|---|"]
    lines += ["| `%s` | %s | %s |" % (name, value.replace("|", "\\|"), kind) for name, value, kind in rows]
    lines += ["", "No other field is sent. The issue's number, its author and its dates are set by GitHub.", "",
              "## The body, in full", "", "Between the fences is the body exactly as it would be sent.", "", fenced(payload["body"]), "",
              "## The exact bytes", "", "The whole payload as it would be sent, as one line of JSON.", "", fenced(data.decode("utf-8")), ""]
    return "\n".join(lines)


def snapshot(conn, repo):
    """What the repository holds that a write would change: its newest issue number, its labels, its milestones."""
    status, _, newest = conn.get("/repos/%s/issues" % repo, {"state": "all", "sort": "created", "direction": "desc", "per_page": 1})
    if status != 200 or not isinstance(newest, list):
        raise Stop("GitHub did not return the repository's issues (status %d)" % status)
    labels = sorted(str(row.get("name")) for row in read_all(conn, "/repos/%s/labels" % repo, {}, "the repository's labels"))
    milestones = sorted((row.get("number"), str(row.get("title")), str(row.get("state"))) for row in read_all(conn, "/repos/%s/milestones" % repo, {"state": "all"}, "the repository's milestones"))
    return {"newest_issue": newest[0].get("number") if newest else None, "labels": labels, "milestones": milestones}


# ---------------------------------------------------------------- the preview


def check_allowlist(path, repo):
    try:
        with open(path, encoding="utf-8") as f:
            names = json.load(f)["sandbox_repositories"]
    except (OSError, ValueError, KeyError, TypeError):
        raise Stop("the sandbox allowlist could not be read, so no repository is allowed")
    if not isinstance(names, list) or repo not in names:
        raise Stop("the repository %s is NOT ON THE SANDBOX ALLOWLIST %s. No request was sent to GitHub" % (q(repo), shown_path(path)))
    return len(names)


def preview(args, conn):
    say("PREVIEW of a new issue. This command only reads. It has no way to write")
    draft = read_draft(args.draft)
    repo = draft["repository"]
    count = check_allowlist(args.allowlist, repo)
    despite = []
    for name in args.despite_duplicate or []:
        if not ISSUE_NAME.match(name):
            raise Stop("--despite-duplicate takes an issue as OWNER/NAME#NUMBER")
        despite.append(name)
    status, _, account = conn.get("/user")
    if status != 200 or not isinstance(account, dict) or not isinstance(account.get("login"), str):
        raise Stop("GitHub did not say who the connection acts as (status %d)" % status)
    status, _, about = conn.get("/repos/%s" % repo)
    if status != 200 or not isinstance(about, dict) or not isinstance(about.get("id"), int) or about.get("full_name") != repo:
        raise Stop("GitHub does not show the repository %s to this connection under that name (status %d)" % (q(repo), status))
    before = snapshot(conn, repo)
    say("1. WHERE. Repository %s, id %d, %s. On the sandbox allowlist %s, which names %s. The connection acts as login %s"
        % (q(repo), about["id"], "private" if about.get("private") else "PUBLIC", shown_path(args.allowlist), plural(count, "repository", "repositories"), q(account["login"])))
    say("     Draft: %s, title %s" % (shown_path(args.draft), q(draft["title"])))
    problems = []

    template = read_template(conn, repo, draft["template"])
    lines, found_problems = check_template(draft, template)
    say("2. TEMPLATE. The repository's own template %s was read from the repository. It has %s. Every section is required unless its heading ends \"(optional)\""
        % (q(draft["template"]), plural(len(template["sections"]), "section")))
    for line in lines:
        say("     section " + line)
    say("     the template gives issues of this kind the label(s): %s" % (", ".join(q(one) for one in template["labels"]) or "none"))
    problems += found_problems

    lines, found_problems, found = check_existing(conn, draft, template)
    say("3. LABELS, ASSIGNEES, MILESTONE. Each one was looked up in the repository:")
    for line in lines:
        say("     " + line)
    problems += found_problems

    lines, found_problems = check_sources(draft)
    say("4. SOURCES. %s checked against the file and lines each one names:" % plural(len(draft["sources"]), "citation"))
    for line in lines:
        say("     " + line)
    problems += found_problems

    lines, found_problems, duplicate = check_duplicates(draft, args.index, despite)
    say("5. DUPLICATE CHECK.")
    for line in lines:
        say("     " + line)
    problems += found_problems

    lines, found_problems = check_permission(conn, about, draft)
    say("6. PERMISSION CHECK.")
    for line in lines:
        say("     " + line)
    problems += found_problems

    record = None
    if problems:
        say("7. THE EXACT PAYLOAD. Not shown: the draft cannot be sent as it is, so there is no payload to show")
    else:
        payload = build_payload(draft, found)
        data = payload_bytes(payload)
        record = {"format": PREVIEW_FORMAT, "source": args.source, "repository": repo, "repository_id": about["id"], "account": account["login"],
                  "draft_digest": draft["digest"], "template": draft["template"], "found": found, "duplicate": duplicate,
                  "request": {"method": "POST", "path": "/repos/%s/issues" % repo}, "payload": payload,
                  "payload_sha256": hashlib.sha256(data).hexdigest(), "created": conn.now, "limit_minutes": LIMIT_MINUTES}
        record["fingerprint"] = hashlib.sha256(json.dumps(record, sort_keys=True).encode("utf-8")).hexdigest()[:32]
        say("7. THE EXACT PAYLOAD a later write would send. It is built once, here, and saved. A write sends these bytes and builds nothing of its own:")
        say("     POST /repos/%s/issues" % repo)
        say("     title      %s" % q(payload["title"]))
        say("     body       %d characters, %s. First line: %s" % (len(payload["body"]), plural(payload["body"].count("\n") + 1, "line"), q(payload["body"].split("\n")[0])))
        say("     labels     %s" % (q(payload["labels"]) if "labels" in payload else "not sent"))
        say("     assignees  %s" % (q(payload["assignees"]) if "assignees" in payload else "not sent"))
        say("     milestone  %s" % ("%d (%s)" % (payload["milestone"], q(found["milestone"]["title"])) if "milestone" in payload else "not sent"))
        say("     the exact bytes, %d of them, SHA-256 %s:" % (len(data), record["payload_sha256"]))
        say("     " + data.decode("utf-8"))

    after = snapshot(conn, repo)
    same = before == after
    say("8. NOTHING WAS WRITTEN. The repository was read at the start and again at the end. Newest issue number: %s then %s. Labels: %d then %d. "
        "Milestones: %d then %d. %s" % (before["newest_issue"], after["newest_issue"], len(before["labels"]), len(after["labels"]),
                                         len(before["milestones"]), len(after["milestones"]), "The same" if same else "DIFFERENT: someone changed the repository during the preview"))
    say("     Requests made by this command: %d, every one a GET" % len(conn.asked))
    if not same:
        problems.append("the repository changed while it was being previewed")
        record = None
    if problems:
        say("RESULT: NOT READY. %s:" % plural(len(problems), "reason"))
        for number, problem in enumerate(problems, 1):
            say("  %d. %s" % (number, problem))
        say("No fingerprint is given and no payload was saved, so there is nothing a write could send")
        return 1
    if args.state:
        os.makedirs(args.state, exist_ok=True)
        path = os.path.join(args.state, record["fingerprint"] + ".json")
        with open(path + ".tmp", "w", encoding="utf-8") as f:
            json.dump({"record": record, "status": "ready"}, f, indent=1, sort_keys=True)
        os.replace(path + ".tmp", path)
    if args.payload_out:
        os.makedirs(os.path.dirname(os.path.abspath(args.payload_out)), exist_ok=True)
        with open(args.payload_out + ".tmp", "w", encoding="utf-8") as f:
            f.write(render_payload(record))
        os.replace(args.payload_out + ".tmp", args.payload_out)
        say("     The payload was written, field by field, to %s" % shown_path(args.payload_out))
    say("9. FINGERPRINT of this preview: %s. It covers the repository, the draft, the checks and the exact payload%s"
        % (record["fingerprint"], ". Saved for a later write, good for %d minutes from %s by GitHub's clock" % (LIMIT_MINUTES, conn.now) if args.state else ""))
    say("RESULT: READY. Nothing has been written")
    return 0


def run(args, conn):
    """The preview, with every way it can stop turned into a line and an exit code."""
    try:
        return preview(args, conn)
    except Stop as why:
        say("STOPPED: %s." % why)
        say("Nothing was written. Requests made by this command: %d%s" % (len(conn.asked), ", every one a GET" if conn.asked else ""))
        return 1
    except RateLimited:
        say("INCOMPLETE: GitHub rate-limited this run. Nothing was written. Run it again later.")
        return 2


def main(argv=None):
    root = os.path.realpath(os.path.join(HERE, "..", "..", ".."))
    parser = argparse.ArgumentParser(description="Preview a new GitHub issue. Reads only.")
    parser.add_argument("--source", choices=("live", "fake"), required=True)
    parser.add_argument("--draft", required=True)
    parser.add_argument("--index", required=True, help="the local index of issue records, for the duplicate search")
    parser.add_argument("--allowlist", required=True, help="a JSON file naming the sandbox repositories")
    parser.add_argument("--despite-duplicate", action="append", metavar="OWNER/NAME#N", help="a person's decision to go on despite this likely duplicate")
    parser.add_argument("--payload-out", help="write the payload, field by field, to this file")
    parser.add_argument("--state", help="a folder to save a READY preview in, for a later write")
    parser.add_argument("--fake-store", help="with --source fake: the made-up GitHub's file")
    args = parser.parse_args(argv)
    try:
        if args.source == "fake":
            sys.path.insert(0, HERE)
            import fake_github
            fake = fake_github.load(args.fake_store) if args.fake_store else fake_github.FakeGitHub()
            return run(args, Connection(fake.send))
        if args.fake_store:
            raise Stop("--fake-store only goes with --source fake")
        for path, what in ((args.draft, "--draft"), (args.payload_out, "--payload-out"), (args.state, "--state")):
            if path and os.path.commonpath([root, os.path.realpath(path)]) == root:
                raise Stop("a live run keeps its files outside this repository, because they name a real account. Give %s a path outside it" % what)
        if not os.environ.get("GITHUB_TOKEN"):
            raise Stop("the environment variable GITHUB_TOKEN is not set")
        return run(args, Connection(live_send))
    except Stop as why:
        say("STOPPED: %s." % why)
        say("Nothing was written.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
