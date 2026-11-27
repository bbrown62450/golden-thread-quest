#!/usr/bin/env python3
"""Keeps a local copy of one Jira story's comments and of the changes in its history that matter, and brings the copy
up to date each time it is run, without ever adding anything twice. IT ONLY READS JIRA.

    sync_comments.py sync  --source live|fake --issue KEY --out-dir DIR --name NAME [--state DIR] [--log FILE]
    sync_comments.py rules [--write FILE]

A sync writes two files in DIR, and no others:

    NAME.json    the copy itself. Every comment is under the identifier Jira gave it
    NAME.md      the same, laid out to be read. It is written from NAME.json every time and is never read back

and it never writes, moves or opens for writing a third:

    NAME.notes.md    the person's own notes. Its checksum is taken before and after and both are printed

COMMENTS ARE MATCHED BY JIRA'S IDENTIFIER AND BY NOTHING ELSE. Never by their text, their author or their time.

    A comment Jira lists that the copy does not have     is ADDED, once
    A comment whose words differ from the copy's         is UPDATED IN PLACE: the text is replaced, and a note is put
                                                         under it saying when Jira says it was edited, when this
                                                         sync noticed, how long lay between, a short checksum of
                                                         the text it replaced, and whether the edit was by the
                                                         comment's author or by someone else
    A comment the copy has that Jira no longer lists     is first asked for by its own identifier. Only if Jira
                                                         answers 404 is it MARKED, and it is KEPT, with its last
                                                         text. It is never taken out. The mark says "not returned by Jira any more": this
                                                         tool cannot tell a deleted comment from one that has been
                                                         hidden from the account it reads with
    Everything else                                      is left exactly as it is

If nothing changed in Jira, nothing is written: the two files are byte for byte what they were.

NOTHING IS CHANGED UNLESS EVERYTHING WAS READ. The story, every page of its comments and every page of its history
are read first. If any request fails, if Jira's own count of the comments does not match what arrived, or if a
comment comes twice, the sync is REFUSED and the copy is left as it was. Otherwise a failed page would look like
deleted comments.

THE HISTORY. Jira records every change to a story, most of them of no use to a reader. The rules below say which
kinds are kept ("material"), which are left out ("noise"), and what is kept of each. `rules` prints them, and
`rules --write` writes the rules document from the same lists this tool applies. A kind of change on neither list is
not kept and not hidden: the sync counts it and names it as UNLISTED.
Each change kept is under Jira's identifier for the history entry and the place of the change inside it, so it too
is added once.

PEOPLE ARE NOT KEPT. No name, email address or account identifier is written. Whether an edit was by the comment's
author is worked out by comparing two account identifiers, which are then dropped. A change of assignee is kept as
"assigned", "reassigned" or "unassigned". A mention inside a comment is kept as "[a person]".

THE TEXT OF A COMMENT IS OTHER PEOPLE'S TEXT. It is kept, because a copy of the comments is what this is for. It is
never printed by this tool. In NAME.md it is put inside a fence it cannot close, with unseen characters replaced.
Titles and descriptions are not kept: a change to one is kept as the fact that it changed.

A LIVE SYNC WRITES ONLY INSIDE A FOLDER NAMED `local-data`, which this repository does not hand in, because real
comments can hold private discussion.

Every request is a GET, built in one place: the story, a page of its comments, one comment by its identifier, or a
page of its history. There is no code path that builds any other. What the output says about
the requests is read back from each request as it was built.

--state DIR is for the made-up Jira (--source fake): the folder that holds it. --pretend-now TIME, also for the
made-up Jira only, sets the clock that "noticed" times are taken from.
--log FILE saves the output with the site's address replaced by a marker.

For a live sync the connection comes from the environment variables JIRA_BASE_URL, JIRA_EMAIL and JIRA_API_TOKEN. None
is stored. The output is searched for the token, the email address and their encoded form before it is shown.

Exit codes: 0 the copy is up to date (whether or not anything had to change); 1 REFUSED, and the copy is as it was;
also 1 if a write failed partway (the output says which file is behind), or if the notes file changed while the sync
ran, which this tool does not do and reports.
"""
import argparse
import base64
import datetime
import hashlib
import http.client
import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request

FORMAT = "jira-comments-history/1"
REF = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,30}-[0-9]{1,9}")
NAME = re.compile(r"[a-z][a-z0-9-]{0,60}")
SITE_MARK = "[site address removed]"
PAGE = 100
MAX_PAGES = 100
TEXT_LIMIT = 8000
UNSEEN = re.compile("[\\x00-\\x08\\x0b-\\x1f\\x7f-\\xa0\\u00ad\\u034f\\u061c\\u115f\\u1160\\u200b-\\u200f\\u2028\\u2029\\u202a-\\u202e\\u2060-\\u2069\\u2800\\u3164\\ufeff\\U000e0000-\\U000e007f]")
KEPT_MARKS = " ._/()'-"

# ---------------------------------------------------------------- the rules for the history
# Each kind of change is known by the name Jira gives the field, compared without regard to capitals. `keeps` says what
# is kept of it. A field the site's administrators added (Jira marks it "custom") is never material, whatever it is
# called: its values are free text, and a custom field named "Status" is not the story's status.
MATERIAL = [
    ("status", "names", "Where the work stands. The old and the new status are kept."),
    ("assignee", "person", "Who has the work. Kept as assigned, reassigned or unassigned. No person is kept."),
    ("priority", "names", "How urgent it is. The old and the new priority are kept."),
    ("duedate", "dates", "When it is due. The old and the new date are kept."),
    ("issuetype", "names", "What kind of work it is. The old and the new type are kept."),
    ("summary", "fact", "The title. Kept as the fact that it changed. The old and new titles are not kept."),
    ("description", "fact", "The description. Kept as the fact that it changed. The texts are not kept."),
    ("link", "links", "What the work depends on: a link to another item was added or removed. The other item's key is kept, if Jira gives one."),
    ("parent", "keys", "The story was moved under another parent. The keys are kept, if Jira gives keys."),
    ("issueparentassociation", "fact", "Jira's other name for a move under another parent. Kept as the fact that it changed."),
]
NOISE = [
    ("rank", "The order of cards on a board. It changes every time someone drags a card. Urgency is kept from the priority field instead."),
    ("labels", "Tags. Useful for finding things, and they do not change what the work is, who has it, or when."),
    ("sprint", "Which sprint the card sits in. Planning moves it back and forth. The due date is what is kept for \"when\"."),
    ("attachment", "A file was added or removed. The file is not copied, and its name can be private."),
    ("watchers", "Who is following the story."),
    ("timespent", "Time logged."),
    ("timeestimate", "The remaining estimate."),
    ("timeoriginalestimate", "The original estimate."),
    ("worklogid", "A work-log entry."),
    ("resolution", "Set and cleared by the workflow when the status changes. The status change is what is kept."),
    ("resolutiondate", "The same."),
    ("comment", "Comments are kept in their own right, by identifier, not from the history."),
    ("remoteissuelink", "A link to something outside Jira, such as a web page."),
]
MATERIAL_NAMES = [name for name, _, _ in MATERIAL]
NOISE_NAMES = [name for name, _ in NOISE]

LINES = []


class Refused(Exception):
    """The copy is as it was. The message is the reason."""


class WriteFailed(Refused):
    """A write failed partway. The message says what state the files are in."""


def say(text=""):
    LINES.append(text)


def clean(value, limit=60):
    """A name the site's administrators chose (a status, a priority, a field): cut short; characters that are not a
    letter or digit of some script, or one of a few marks, replaced by a question mark. None if there is nothing."""
    if not isinstance(value, str) or not value.strip():
        return None
    return "".join(ch if (ch.isalnum() or ch in KEPT_MARKS) and not UNSEEN.match(ch) else "?" for ch in value)[:limit].strip() or None


def plain(text):
    """Other people's text, with unseen characters and halves of characters replaced, so it can be stored and written."""
    return re.sub("[\ud800-\udfff]", "?", UNSEEN.sub("?", text))


def same_file(a, b):
    """Whether two paths are one file: by the disk's own answer if both exist (so another spelling in capitals, a link
    or a second name is seen), and by the paths, compared without regard to capitals, if not."""
    try:
        if os.path.exists(a) and os.path.exists(b):
            return os.path.samefile(a, b)
    except OSError:
        pass
    return os.path.realpath(a).casefold() == os.path.realpath(b).casefold()


def may_write(path, own=()):
    """Refuses a place this tool must not write a file of its OWN choosing to: anything named like a notes file, a link,
    a file with a second name, or one of the paths in `own`."""
    if os.path.basename(path).casefold().endswith(".notes.md"):
        raise Refused("that place is named like a notes file. This tool never writes one")
    if os.path.islink(path) or (os.path.isfile(path) and os.stat(path).st_nlink > 1):
        raise Refused("that place is a link, or a file with a second name. This tool writes only a plain file")
    if any(same_file(path, other) for other in own):
        raise Refused("that place is one of the sync's own files, or the notes")


def shown(text, limit=80):
    return "".join("?" if UNSEEN.match(ch) or ch == "\n" else ch for ch in str(text))[:limit]


def in_utc(value):
    """Jira's time, such as 2026-11-20T10:00:00.000+0100, as 2026-11-20T09:00:00Z. None if it is not one."""
    if not isinstance(value, str):
        return None
    for shape in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.datetime.strptime(value, shape).astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except (ValueError, OverflowError):
            continue
    return None


def seconds_between(earlier, later):
    shape = "%Y-%m-%dT%H:%M:%SZ"
    return int((datetime.datetime.strptime(later, shape) - datetime.datetime.strptime(earlier, shape)).total_seconds())


def span(seconds):
    """How long, in words: "2 days 4 hours". A change that Jira dates after the sync's own clock is said to be that."""
    if seconds < 0:
        return "dated after this sync's clock"
    days, rest = divmod(seconds, 86400)
    hours, rest = divmod(rest, 3600)
    minutes = rest // 60
    parts = [("%d day%s" % (days, "" if days == 1 else "s")) if days else "", ("%d hour%s" % (hours, "" if hours == 1 else "s")) if hours else "",
             ("%d minute%s" % (minutes, "" if minutes == 1 else "s")) if minutes and not days else ""]
    return " ".join(p for p in parts if p) or "under a minute"


def checksum(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def file_sum(path):
    """The sha256 of a file, or None if there is no file there."""
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except FileNotFoundError:
        return None


# ---------------------------------------------------------------- the connection: GET only


class Connection:
    """Every request goes through `get` and is written down. There is no other method."""

    def __init__(self, get, host):
        self._get, self.host = get, host
        self.sent = []

    def get(self, path, params=None):
        try:
            answer = self._get(path, params)
        except (OSError, TimeoutError) as err:
            self.sent.append(("?", path))
            raise Refused("Jira could not be reached (%s)" % type(getattr(err, "reason", err)).__name__)
        # A live answer carries, as its 4th and 5th parts, the method of the request as built and whether it had a body.
        method = answer[3] + (" WITH A BODY" if answer[4] else "") if len(answer) == 5 else "GET (the made-up Jira)"
        self.sent.append((method, path))
        return answer[0], answer[2]

    def only_gets(self):
        return all(method.split(" ")[0] == "GET" and "BODY" not in method for method, _ in self.sent)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def make_live(opener=None):
    base = os.environ.get("JIRA_BASE_URL", "").rstrip("/")
    email, token = os.environ.get("JIRA_EMAIL", ""), os.environ.get("JIRA_API_TOKEN", "")
    for name, value in (("JIRA_BASE_URL", base), ("JIRA_EMAIL", email), ("JIRA_API_TOKEN", token)):
        if not value:
            raise Refused("the environment variable %s is not set" % name)
    host = urllib.parse.urlparse(base).hostname or ""
    if not host or base.lower() != "https://" + host:
        raise Refused("JIRA_BASE_URL must be https:// and the site's name, with no port, path or sign-in in it")
    base = "https://" + host
    encoded = base64.b64encode(("%s:%s" % (email, token)).encode("utf-8")).decode("ascii")
    opener = opener or urllib.request.build_opener(NoRedirect)

    def get(path, params=None):
        if not re.fullmatch(r"/rest/api/3/issue/[A-Za-z0-9_-]+(/comment(/[0-9]{1,20})?|/changelog)?", path):
            raise Refused("this tool reads a story, its comments and its history, and asks for nothing else")
        url = base + path + ("?" + urllib.parse.urlencode(params) if params else "")
        request = urllib.request.Request(url, method="GET")          # GET, and only GET. No body is ever attached
        request.add_header("Authorization", "Basic " + encoded)
        request.add_header("Accept", "application/json")
        try:
            with opener.open(request, timeout=30) as response:
                status, headers, raw = response.status, dict(response.headers), response.read()
        except urllib.error.HTTPError as err:
            status, headers, raw = err.code, dict(err.headers), err.read()
            err.close()
        except http.client.HTTPException as err:
            raise OSError(type(err).__name__)
        try:
            parsed = json.loads(raw.decode("utf-8")) if raw.strip() else {}
        except (ValueError, RecursionError):
            parsed = {}
        return status, headers, parsed, request.get_method(), request.data is not None

    return Connection(get, host), [token, email, encoded]


def site_fingerprint(host):
    return hashlib.sha256(host.lower().encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------- reading Jira


def ident(value):
    return isinstance(value, str) and value.isascii() and value.isdigit() and 0 < len(value) <= 20


def read_story(conn, key):
    status, body = conn.get("/rest/api/3/issue/%s" % key, {"fields": "issuetype"})
    if status == 401:
        raise Refused("Jira rejected the credentials (401). Check JIRA_EMAIL and JIRA_API_TOKEN")
    if status == 404:
        raise Refused("Jira answered 404 for the story. It does not exist, or this account is not permitted to see it")
    if not (status == 200 and isinstance(body, dict) and ident(body.get("id")) and isinstance(body.get("key"), str) and REF.fullmatch(body["key"])):
        raise Refused("Jira's answer for the story could not be used (status %d)" % status)
    if body["key"].upper() != key.upper():
        raise Refused("Jira answered with the story %s. The story asked for has been moved or renamed. Ask for it by the key it has now" % body["key"].upper())
    return {"key": body["key"].upper(), "id": body["id"]}


def read_all(conn, path, list_name, what):
    """Every entry of a list Jira gives in pages with startAt and total. Refuses unless the whole list arrived:
    each page readable, no entry twice, and as many entries as Jira's own total says, on the first page and the last."""
    entries, seen, first_total = [], set(), None
    for _ in range(MAX_PAGES):
        status, body = conn.get(path, {"startAt": len(entries), "maxResults": PAGE})
        page, total = (body.get(list_name), body.get("total")) if status == 200 and isinstance(body, dict) else (None, None)
        if not isinstance(page, list) or not isinstance(total, int) or isinstance(total, bool) or total < 0:
            raise Refused("Jira did not list the story's %s (status %d)" % (what, status))
        first_total = total if first_total is None else first_total
        for entry in page:
            if not isinstance(entry, dict) or not ident(entry.get("id")):
                raise Refused("Jira sent one of the story's %s without an identifier that can be used" % what)
            if entry["id"] in seen:
                raise Refused("Jira sent one of the story's %s twice (identifier %s), so another may be missing" % (what, entry["id"]))
            seen.add(entry["id"])
            entries.append(entry)
        if len(entries) >= total or not page:
            if len(entries) != total or total != first_total:
                raise Refused("Jira said the story has %d %s and %d arrived%s" % (
                    total, what, len(entries), "" if total == first_total else ", and its own count changed from %d while they were read" % first_total))
            return entries
    raise Refused("the story has more than %d %s, which is more than this tool reads" % (MAX_PAGES * PAGE, what))


def text_of(node, depth=0, lost=None):
    """The plain text of a Jira document, whatever is in it. A mention becomes "[a person]". A status badge or an emoji
    becomes the words it shows. Anything else that carries no text of its own (a date, a card, an image) becomes its
    kind in square brackets, and is added to `lost`, a list, so that the copy can say it is not the whole comment."""
    lost = lost if lost is not None else []
    if not isinstance(node, dict):
        return ""
    if depth > 40:
        lost.append("something nested too deep to read")
        return "[...]"
    kind = node.get("type")
    if kind == "text":
        return node.get("text") if isinstance(node.get("text"), str) else ""
    if kind == "mention":
        return "[a person]"
    if kind == "hardBreak":
        return "\n"
    attrs = node.get("attrs") if isinstance(node.get("attrs"), dict) else {}
    if kind in ("status", "emoji") and isinstance(attrs.get("text"), str) and attrs["text"]:
        return attrs["text"]
    inner = node.get("content")
    if not isinstance(inner, list):
        if kind in ("doc", "paragraph"):
            return ""
        lost.append(clean(kind, 20) or "something")
        return "[%s]" % (clean(kind, 20) or "something")
    joined = "".join(text_of(child, depth + 1, lost) for child in inner)
    return joined + ("\n" if kind in ("paragraph", "heading", "listItem", "codeBlock", "blockquote", "tableRow") else "")


def one_comment(raw):
    """What is kept of a comment as Jira sends it, and who edited it. People are compared and dropped here."""
    created, updated = in_utc(raw.get("created")), in_utc(raw.get("updated"))
    body = raw.get("body")
    if created is None or updated is None:
        raise Refused("Jira sent the comment %s without a time that can be read" % raw["id"])
    lost = []
    if isinstance(body, dict):
        text = plain(text_of(body, 0, lost).strip("\n"))
    else:           # one comment this tool cannot read must not stop every other comment being kept
        text, lost = "[this comment's body is not in a form this tool reads]", ["the whole body"]
    cut = len(text) > TEXT_LIMIT
    author = raw.get("author", {}).get("accountId") if isinstance(raw.get("author"), dict) else None
    editor = raw.get("updateAuthor", {}).get("accountId") if isinstance(raw.get("updateAuthor"), dict) else None
    by = "unknown" if not (isinstance(author, str) and author and isinstance(editor, str) and editor) else "its author" if author == editor else "someone else"
    return {"id": raw["id"], "created": created, "updated": updated, "text": text[:TEXT_LIMIT], "text_cut": cut, "not_all_text": sorted(set(lost)),
            "body_checksum": checksum(json.dumps(body, sort_keys=True, ensure_ascii=True)), "edited_by": by}


def key_of(item, side):
    """The other item's key, if Jira gives exactly a key on this side of the change. Nothing is picked out of a sentence."""
    for name in (side, side + "String"):
        value = item.get(name)
        if isinstance(value, str) and REF.fullmatch(value.strip()):
            return value.strip().upper()
    return None


def kept_of(keeps, item):
    """What is kept of one change in the history, as two short texts: (from, to)."""
    old, new = item.get("fromString"), item.get("toString")
    if keeps == "names":
        before, after = clean(old) or "nothing", clean(new) or "nothing"
        return before, after + (" (the same name: Jira recorded a change between two that are called this)" if before == after else "")
    if keeps == "dates":
        date = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
        return (old[:10] if isinstance(old, str) and date.fullmatch(old[:10]) else "no date"), (new[:10] if isinstance(new, str) and date.fullmatch(new[:10]) else "no date")
    if keeps == "person":
        had, has = bool(isinstance(old, str) and old.strip()), bool(isinstance(new, str) and new.strip())
        return "", "reassigned" if had and has else "assigned" if has else "unassigned" if had else "changed"
    if keeps == "links":
        added, removed = key_of(item, "to"), key_of(item, "from")
        has_new, had_old = bool(isinstance(new, str) and new.strip()), bool(isinstance(old, str) and old.strip())
        return "", ("link added: %s" % added) if added else ("link removed: %s" % removed) if removed else "a link added" if has_new and not had_old else "a link removed" if had_old and not has_new else "a link changed"
    if keeps == "keys":
        return key_of(item, "from") or "no key given", key_of(item, "to") or "no key given"
    return "", "changed"


def read_history(entries):
    """(the material changes, {noise field: how many}, {unlisted field: how many})."""
    material, noise, unlisted = [], {}, {}
    for entry in entries:
        at = in_utc(entry.get("created"))
        items = entry.get("items")
        if at is None or not isinstance(items, list):
            raise Refused("Jira sent the history entry %s without a time or a list of changes that can be read" % entry["id"])
        for place, item in enumerate(items):
            if not isinstance(item, dict) or not isinstance(item.get("field"), str):
                raise Refused("Jira sent the history entry %s with a change that names no field" % entry["id"])
            name = item["field"].strip().casefold()
            custom = item.get("fieldtype") == "custom" or str(item.get("fieldId") or "").casefold().startswith("customfield_")
            rule = None if custom else next((rule for rule in MATERIAL if rule[0] == name), None)
            if rule:
                old, new = kept_of(rule[1], item)
                material.append({"id": "%s:%d" % (entry["id"], place), "at": at, "kind": name, "from": old, "to": new})
            elif name in NOISE_NAMES:
                noise[name] = noise.get(name, 0) + 1
            else:
                label = clean(item["field"], 40) or "a field with no name"
                unlisted[label] = unlisted.get(label, 0) + 1
    return material, noise, unlisted


# ---------------------------------------------------------------- the copy


def load_copy(path):
    """The copy as it is on disk, or None if there is none yet."""
    try:
        with open(path, encoding="utf-8") as f:
            raw = f.read()
    except FileNotFoundError:
        return None
    except (OSError, UnicodeDecodeError):
        raise Refused("the copy on disk could not be read")
    try:
        copy = json.loads(raw)
    except ValueError:
        copy = None
    good = (isinstance(copy, dict) and copy.get("format") == FORMAT and isinstance(copy.get("comments"), list) and isinstance(copy.get("history"), list)
            and isinstance(copy.get("story"), dict) and all(isinstance(c, dict) and ident(c.get("id")) for c in copy["comments"])
            and all(isinstance(h, dict) and isinstance(h.get("id"), str) for h in copy["history"])
            and len(set(c["id"] for c in copy["comments"])) == len(copy["comments"]) and len(set(h["id"] for h in copy["history"])) == len(copy["history"]))
    if not good:
        raise Refused("the copy on disk is not one this tool wrote, or has been changed by hand. It is left as it is. Move it away to start a new copy")
    return copy


def bring_up_to_date(copy, story, source, site, comments, material, now):
    """Changes `copy` in place to match what Jira sent. Returns what it did, as lists of identifiers."""
    done = {"added": [], "edited": [], "retimed": [], "marked": [], "returned": [], "unchanged": [], "still_marked": [], "history_added": []}
    by_id = {c["id"]: c for c in copy["comments"]}
    for fresh in comments:
        have = by_id.get(fresh["id"])
        if have is None:
            entry = {"id": fresh["id"], "created": fresh["created"], "updated": fresh["updated"], "text": fresh["text"], "text_cut": fresh["text_cut"],
                     "not_all_text": fresh["not_all_text"], "body_checksum": fresh["body_checksum"], "first_synced": now, "in_jira": True, "edits": [], "other_changes": [],
                     "edited_before_first_sync": {"by": fresh["edited_by"], "jira_says_edited": fresh["updated"]} if fresh["updated"] != fresh["created"] else None}
            copy["comments"].append(entry)
            done["added"].append(fresh["id"])
            continue
        if not have.get("in_jira", True):
            have["in_jira"] = True
            have.setdefault("returns", []).append(now)
            done["returned"].append(fresh["id"])
        if have["text"] != fresh["text"]:
            have.setdefault("edits", []).append({"noticed": now, "jira_says_edited": fresh["updated"], "by": fresh["edited_by"],
                                                 "replaced_text_checksum": checksum(have["text"]), "seconds_until_noticed": seconds_between(fresh["updated"], now)})
            have.update(text=fresh["text"], text_cut=fresh["text_cut"], not_all_text=fresh["not_all_text"], body_checksum=fresh["body_checksum"], updated=fresh["updated"])
            done["edited"].append(fresh["id"])
        elif have["body_checksum"] != fresh["body_checksum"] or have["updated"] != fresh["updated"]:
            # The words this copy keeps are the same. Something else about the comment changed in Jira: its formatting, a
            # link's target, who a mention points at, or only its edit time. That is noted, and is not called an edit.
            have.setdefault("other_changes", []).append({"noticed": now, "jira_says_edited": fresh["updated"]})
            have.update(body_checksum=fresh["body_checksum"], updated=fresh["updated"])
            done["retimed"].append(fresh["id"])
        elif fresh["id"] not in done["returned"]:
            done["unchanged"].append(fresh["id"])
    listed = set(c["id"] for c in comments)
    for have in copy["comments"]:
        if have["id"] not in listed:
            if have.get("in_jira", True):
                have["in_jira"] = False
                have["not_returned_since"] = now
                done["marked"].append(have["id"])
            else:
                done["still_marked"].append(have["id"])
    known = set(h["id"] for h in copy["history"])
    for change in material:
        if change["id"] not in known:
            copy["history"].append(dict(change, noticed=now, seconds_until_noticed=seconds_between(change["at"], now)))
            done["history_added"].append(change["id"])
    copy["comments"].sort(key=lambda c: (c["created"], int(c["id"])))
    copy["history"].sort(key=lambda h: (h["at"], [int(part) for part in h["id"].split(":")]))
    return done


def fence_for(text):
    longest = max([len(run) for run in re.findall(r"~+", text)] + [2])
    return "~" * (longest + 1)


def render(copy, notes_name):
    """The copy, laid out to be read. Written from the copy every time."""
    out = ["# Comments and material changes · %s" % copy["story"]["key"], "",
           "**Written by a tool. Do not edit this file: the next sync writes it again from `%s`.**" % copy["files"]["copy"],
           "Your own notes go in `%s`, which the tool never writes." % notes_name, "",
           "Source: %s. Every comment is under the identifier Jira gave it. Times are UTC." % (
               "the made-up Jira; every comment and change here is made up" if copy["source"] == "fake" else "a real Jira, site fingerprint %s" % copy["site_fingerprint"]),
           "No person is named: see the rules for what is kept.", "", "## Comments", ""]
    if not copy["comments"]:
        out += ["The story has no comments in this copy.", ""]
    for c in copy["comments"]:
        out.append("### Comment %s" % c["id"])
        out.append("")
        if not c.get("in_jira", True):
            out.append("**NOT RETURNED BY JIRA ANY MORE. First found missing by the sync of %s.** It was deleted, or hidden from the account" % c["not_returned_since"])
            out.append("that reads. The text below is the last this copy had. It is kept, and is not taken out by a later sync.")
            out.append("")
        out.append("- Written: %s. First copied: %s." % (c["created"], c["first_synced"]))
        if c.get("edited_before_first_sync"):
            out.append("- Already edited in Jira when first copied, by %s. Jira's edit time then: %s. The earlier text was never in this copy." % (
                c["edited_before_first_sync"]["by"], c["edited_before_first_sync"]["jira_says_edited"]))
        for edit in c.get("edits", []):
            out.append("- **Edited in Jira** at %s, by %s. Noticed by the sync of %s, %s later. The text below replaced the text with checksum `%s`." % (
                edit["jira_says_edited"], edit["by"], edit["noticed"], span(edit["seconds_until_noticed"]), edit["replaced_text_checksum"]))
        for other in c.get("other_changes", []):
            out.append("- Changed in Jira at %s with the same words: its formatting, a link, a mention, or only its edit time. Noticed by the sync of %s. Not an edit of the text." % (
                other["jira_says_edited"], other["noticed"]))
        if c.get("not_all_text"):
            out.append("- **Not the whole comment.** It holds things that are not plain text, shown below by kind in square brackets: %s." % ", ".join(c["not_all_text"]))
        for back in c.get("returns", []):
            out.append("- Returned by Jira again as of the sync of %s." % back)
        if c.get("text_cut"):
            out.append("- The text was longer than %d characters and was cut." % TEXT_LIMIT)
        fence = fence_for(c["text"])
        # Every line of the comment is set in by four spaces, so that no line of it starts the way a line of this page does.
        out += ["", fence + "text"] + ["    " + line for line in c["text"].split("\n")] + [fence, ""]
    out += ["## Material changes", ""]
    if not copy["history"]:
        out += ["No material change is in this copy.", ""]
    else:
        out += ["| When | What | From | To | Noticed | Time until noticed | Identifier |", "|---|---|---|---|---|---|---|"]
        for h in copy["history"]:
            out.append("| %s | %s | %s | %s | %s | %s | %s |" % (h["at"], h["kind"], h["from"] or "", h["to"], h["noticed"], span(h["seconds_until_noticed"]), h["id"]))
        out.append("")
    out += ["Only the kinds of change listed as material in the rules are here. What is left out, and why, is in the rules.", ""]
    return "\n".join(out)


def write_file(path, text):
    if os.path.basename(path).casefold().endswith(".notes.md"):
        raise Refused("this tool never writes a file named like a notes file")
    folder = os.path.dirname(path)
    handle, temporary = tempfile.mkstemp(prefix=".sync-", suffix=".tmp", dir=folder)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def places(out_dir, name, live):
    """The three paths, checked. Refuses a place where a write could land on the notes or outside the folder."""
    if not NAME.fullmatch(name):
        raise Refused("--name is lower-case letters, digits and dashes, starting with a letter")
    folder = os.path.realpath(out_dir)
    if not os.path.isdir(folder):
        raise Refused("--out-dir is not a folder that exists")
    if live and "local-data" not in folder.split(os.sep):
        raise Refused("a live sync writes only inside a folder named `local-data`, which is not handed in, because real comments can be private")
    copy_path, page_path, notes_path = (os.path.join(folder, name + ending) for ending in (".json", ".md", ".notes.md"))
    for path in (copy_path, page_path):
        if os.path.islink(path) or os.path.isdir(path) or (os.path.exists(path) and os.stat(path).st_nlink > 1):
            raise Refused("%s in the folder is a link, a folder, or a file with a second name. This tool writes only a plain file of its own" % os.path.basename(path))
    return copy_path, page_path, notes_path


# ---------------------------------------------------------------- the commands


def rules_text():
    out = ["# Which changes in a story's history are kept", "",
           "**Written by a tool** (`participant/skills/jira-read-comments-history/sync_comments.py rules --write`), from the same lists the sync applies.",
           "To change a rule, change the list in the tool and write this file again.", "",
           "## The rule in one sentence", "",
           "**A change is material if it changes what the work is, where it stands, who has it, how urgent it is, when it is due, or what it depends on.**",
           "Everything else in the history is noise for a reader.", "",
           "- A field is known by the name Jira gives it, compared without regard to capitals: `Link` and `link` are the same field.",
           "- **A field the site's administrators added is never material, whatever it is called.** Jira marks such a field \"custom\". Its values are",
           "  free text, and a custom field someone named \"Status\" is not the story's status. It is reported as unlisted.", "",
           "## Material: kept", "", "| Jira's name for the field | Why | What is kept |", "|---|---|---|"]
    for name, keeps, why in MATERIAL:
        first, _, rest = why.partition(". ")
        out.append("| `%s` | %s. | %s |" % (name, first.rstrip("."), rest))
    out += ["", "For each change kept: when Jira says it happened, when a sync first noticed it, the time between the two, and Jira's identifier",
            "for the history entry with the place of the change inside it. That identifier is what stops a change being added twice.", "",
            "## Noise: left out", "", "| Jira's name for the field | Why it is left out |", "|---|---|"]
    for name, why in NOISE:
        out.append("| `%s` | %s |" % (name, why))
    out += ["", "A sync counts what it left out, by field, and prints the counts. It keeps nothing of them.", "",
            "## A field on neither list", "",
            "It is **not kept**, and it is **not hidden**: the sync prints it as UNLISTED, with its name and how many times it appeared.",
            "That is the prompt to decide which list it belongs on. This page does not rule on a story-point estimate, a fix version, a component,",
            "a reporter or a flag: by the sentence at the top a fix version or a component could well be material, and none of them is kept today.",
            "The name printed is the field's name, as the site's administrators chose it.", "",
            "## Three things this page does not hide", "",
            "- **Two statuses with the same name.** Jira can record a change from one status to another of the same name. It is kept, and says so.",
            "- **A story moved to another project** gets a new key. A sync asked for it by its old key is refused, and says the story has moved.",
            "- **Rank on some teams is the priority.** Where the order of the backlog is how urgency is shown, leaving rank out loses that. Here urgency is",
            "  taken from the priority field. A team that works the other way should move `rank` to the first list.", "",
            "## People, and other people's words", "",
            "- **No person is kept**: no name, email address or account identifier. A change of assignee is kept as assigned, reassigned or unassigned",
            "  (or as \"changed\", if Jira gives neither an old nor a new assignee).",
            "- **Whether a comment was edited by its author or by someone else** is kept, as those words, or as \"unknown\" if Jira does not say who.",
            "  Two account identifiers are compared and dropped.",
            "- **A link or a parent is kept by the other item's key only when Jira gives exactly a key.** Nothing is picked out of a sentence. Otherwise",
            "  it is kept as \"a link added\", \"a link removed\", \"a link changed\" or \"no key given\".",
            "- **A title or description is not kept.** Its change is kept as the fact that it changed.",
            "- **A comment's text is kept**, because a copy of the comments is what this is for. A mention in it is kept as \"[a person]\".",
            "- **Not always the whole comment.** Unseen characters are replaced by a question mark. Text over %d characters is cut. A date, a card or" % TEXT_LIMIT,
            "  an image is kept as its kind in square brackets. In each case the page says so under the comment.", "",
            "## Comments: what a sync does", "",
            "| What Jira shows | What the copy does |", "|---|---|",
            "| A comment the copy does not have | Added, once, under Jira's identifier |",
            "| A comment whose words differ from the copy's | The text is replaced in place. A note under it gives Jira's edit time, when it was noticed, the time between, a checksum of the text replaced, and whether its author or someone else edited it |",
            "| A comment with the same words, changed in some other way (formatting, a link's target, only its edit time) | The text is left. A note under it says so. It is not called an edit |",
            "| A comment the copy has and Jira no longer lists | It is asked for by its own identifier. If Jira answers 404 it is marked \"not returned by Jira any more\", with the sync that first found it missing. **Its last text is kept, and it is never taken out** |",
            "| A marked comment that Jira lists again | The mark is taken off, and a note says when it came back |",
            "| Nothing new | Nothing is written. The files are byte for byte what they were |", "",
            "- **Comments are matched by identifier only.** Two comments with the same words are two comments.",
            "- **Deleted text is retained.** That is a choice: the mark is only useful if it shows what went. It also means this copy holds words someone chose to remove.",
            "- **\"Not returned\" is not always \"deleted\".** A comment hidden from the account that reads looks the same from here.",
            "- **Only the latest text of an edited comment is kept,** with a checksum of what it replaced. Two edits between two syncs are seen as one.",
            "- **A sync changes nothing unless it read everything.** A page that fails must not look like deleted comments.",
            "- **The notes file is never written.** `NAME.notes.md` belongs to the person. The sync prints its checksum before and after. The tool",
            "  refuses to write any file of its own to a place named like a notes file, or to a place that is the notes file under another spelling or name.", ""]
    return "\n".join(out)


def cmd_rules(args):
    text = rules_text()
    if args.write:
        target = os.path.abspath(args.write)
        may_write(target)
        if os.path.exists(target):
            with open(target, encoding="utf-8", errors="replace") as f:
                if not f.read(200).startswith(text.split("\n")[0]):
                    raise Refused("a file is already at that place and it is not a rules document this tool wrote. It is left as it is")
        os.makedirs(os.path.dirname(target), exist_ok=True)
        write_file(target, text)
        say("The rules were written to the file given with --write: %s (%d material kinds, %d noise kinds)." % (shown(os.path.basename(args.write)), len(MATERIAL), len(NOISE)))
    else:
        say(text)
    return 0


def cmd_sync(args, conn, live, now):
    if not REF.fullmatch(args.issue):
        raise Refused("--issue is a story's key, such as DEMO-7")
    copy_path, page_path, notes_path = places(args.out_dir, args.name, live)
    notes_before = file_sum(notes_path)
    before = (file_sum(copy_path), file_sum(page_path))
    copy = load_copy(copy_path)
    source, site = ("live", site_fingerprint(conn.host)) if live else ("fake", None)

    # Everything is read before anything is changed.
    story = read_story(conn, args.issue)
    comments = [one_comment(raw) for raw in read_all(conn, "/rest/api/3/issue/%s/comment" % story["key"], "comments", "comments")]
    material, noise, unlisted = read_history(read_all(conn, "/rest/api/3/issue/%s/changelog" % story["key"], "values", "history entries"))

    # A comment the copy has and the list does not is asked for by its own identifier before it is marked. The list
    # comes in pages: if a comment is deleted and another added while the pages are read, one that is still there can
    # fall between two pages. Only Jira saying 404 for that very comment marks it.
    listed = set(c["id"] for c in comments)
    for have in (copy["comments"] if copy else []):
        if have["id"] not in listed and have.get("in_jira", True):
            status, _ = conn.get("/rest/api/3/issue/%s/comment/%s" % (story["key"], have["id"]))
            if status == 200:
                raise Refused("Jira's list of comments left out the comment %s, and Jira says it is still there. The list changed while it was being read. Run the sync again" % have["id"])
            if status != 404:
                raise Refused("the comment %s is not in Jira's list, and Jira would not say whether it is gone (status %d)" % (have["id"], status))

    first = copy is None
    if first:
        copy = {"format": FORMAT, "story": story, "source": source, "site_fingerprint": site, "comments": [], "history": [],
                "files": {"copy": args.name + ".json", "page": args.name + ".md"}}
    elif (copy["story"].get("id"), copy.get("source"), copy.get("site_fingerprint")) != (story["id"], source, site):
        raise Refused("the copy on disk is of another story, or was made from another Jira. It is left as it is. Use another --name")
    copy["story"] = story
    done = bring_up_to_date(copy, story, source, site, comments, material, now)

    copy_text = json.dumps(copy, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    page_text = render(copy, args.name + ".notes.md")
    wrote = []
    try:
        if before[0] != hashlib.sha256(copy_text.encode("utf-8")).hexdigest():
            write_file(copy_path, copy_text)
            wrote.append(os.path.basename(copy_path))
        if before[1] != hashlib.sha256(page_text.encode("utf-8")).hexdigest():
            write_file(page_path, page_text)
            wrote.append(os.path.basename(page_path))
    except OSError:
        raise WriteFailed("a file could not be written%s. Run the sync again: the page is written from the copy every time" % (
            "" if not wrote else ". The copy was written and the page was not, so the page is behind the copy"))
    after = (file_sum(copy_path), file_sum(page_path))
    notes_after = file_sum(notes_path)

    say("Story: %s" % story["key"])
    say("Read from: %s" % ("a real Jira, site fingerprint %s" % site if live else "the made-up Jira. No real Jira was contacted"))
    say("This sync's clock: %s" % now)
    say("%s" % ("FIRST SYNC: there was no copy yet." if first else "A copy was already there. It was brought up to date."))
    say("")
    say("COMMENTS. Jira lists %d. Matched by Jira's identifier, and by nothing else." % len(comments))
    say("  added:                          %d%s" % (len(done["added"]), ids(done["added"])))
    say("  edited in Jira, updated in place: %d%s" % (len(done["edited"]), ids(done["edited"])))
    for ident_ in done["edited"]:
        edit = [c for c in copy["comments"] if c["id"] == ident_][0]["edits"][-1]
        say("      %s: edited by %s at %s, noticed %s later. The text was replaced; the old text's checksum is kept: %s" % (
            ident_, edit["by"], edit["jira_says_edited"], span(edit["seconds_until_noticed"]), edit["replaced_text_checksum"]))
    say("  unchanged:                      %d" % len(done["unchanged"]))
    if done["retimed"]:
        say("  same words, changed in Jira in some other way: %d%s" % (len(done["retimed"]), ids(done["retimed"])))
    say("  NOT RETURNED BY JIRA ANY MORE, marked now and kept: %d%s" % (len(done["marked"]), ids(done["marked"])))
    if done["marked"]:
        say("      Each was asked for by its own identifier, and Jira answered 404. Deleted in Jira, or hidden from the account")
        say("      that reads: this tool cannot tell which. The last text is kept.")
    if done["still_marked"]:
        say("  marked by an earlier sync, still kept: %d%s" % (len(done["still_marked"]), ids(done["still_marked"])))
    if done["returned"]:
        say("  marked earlier and returned by Jira again: %d%s" % (len(done["returned"]), ids(done["returned"])))
    say("  comments in the copy now:       %d (%d of them marked as not returned)" % (len(copy["comments"]), sum(1 for c in copy["comments"] if not c.get("in_jira", True))))
    say("")
    say("HISTORY. Jira lists %d changes in the story's history." % (len(material) + sum(noise.values()) + sum(unlisted.values())))
    say("  material, by the rules:         %d, of which new to the copy: %d%s" % (len(material), len(done["history_added"]), ids(done["history_added"])))
    for change in copy["history"]:
        if change["id"] in done["history_added"]:
            say("      %s  %s: %s%s. Noticed %s later." % (change["at"], change["kind"], (change["from"] + " -> ") if change["from"] else "", change["to"], span(change["seconds_until_noticed"])))
    say("  noise, left out:                %d%s" % (sum(noise.values()), (" (%s)" % ", ".join("%s x%d" % pair for pair in sorted(noise.items()))) if noise else ""))
    say("  UNLISTED, on neither list, not kept: %d%s" % (sum(unlisted.values()), (" (%s)" % ", ".join("%s x%d" % pair for pair in sorted(unlisted.items()))) if unlisted else ""))
    say("  material changes in the copy now: %d" % len(copy["history"]))
    say("")
    say("FILES, in the folder given with --out-dir.")
    for label, path, a, b in (("the copy", copy_path, before[0], after[0]), ("the page", page_path, before[1], after[1])):
        say("  %-9s %-28s before %s   after %s   %s" % (label, shown(os.path.basename(path)), (a or "not there")[:16], (b or "not there")[:16],
                                                         "WRITTEN" if os.path.basename(path) in wrote else "not written: byte for byte the same"))
    say("  the notes %-28s before %s   after %s   %s" % (shown(os.path.basename(notes_path)), notes_before or "not there", notes_after or "not there",
                                                         "UNCHANGED. This tool never writes it" if notes_before == notes_after else "IT CHANGED DURING THE SYNC"))
    say("")
    nothing = not wrote
    say("RESULT: %s" % ("NOTHING TO DO. Jira shows nothing the copy does not have, and nothing was written." if nothing else
                        "UP TO DATE. %d added, %d edited in place, %d marked as not returned, %d material change%s added." % (
                            len(done["added"]), len(done["edited"]), len(done["marked"]), len(done["history_added"]), "" if len(done["history_added"]) == 1 else "s")))
    say("")
    if conn.only_gets():
        say("Requests sent to Jira: %d. Every one was a GET with no body, which reads and cannot change anything." % len(conn.sent))
    else:
        say("Requests sent to Jira: %d. NOT EVERY ONE COULD BE READ BACK AS A PLAIN GET:" % len(conn.sent))
    shapes = {}
    for method, path in conn.sent:
        shape = method + " " + re.sub(r"/issue/[^/]+", "/issue/{key}", path)
        shapes[shape] = shapes.get(shape, 0) + 1
    for shape in sorted(shapes):
        say("  %s  x%d" % (shape, shapes[shape]))
    return 0 if notes_before == notes_after else 1


def ids(identifiers):
    return ("  [%s]" % ", ".join(identifiers[:12]) + (" ..." if len(identifiers) > 12 else "")) if identifiers else ""


def main(argv=None):
    parser = argparse.ArgumentParser(description="Keep a local copy of a Jira story's comments and material history. Reads only.")
    commands = parser.add_subparsers(dest="command", required=True)
    sub = commands.add_parser("rules")
    sub.add_argument("--write", metavar="FILE")
    sub = commands.add_parser("sync")
    sub.add_argument("--source", choices=("live", "fake"), required=True)
    sub.add_argument("--issue", required=True)
    sub.add_argument("--out-dir", required=True)
    sub.add_argument("--name", required=True, help="the files are NAME.json and NAME.md; the notes are NAME.notes.md")
    sub.add_argument("--state", help="with --source fake: the folder that holds the made-up Jira")
    sub.add_argument("--pretend-now", metavar="TIME", help="with --source fake only: this sync's clock, as 2026-11-08T12:00:00Z")
    sub.add_argument("--log", help="also save the output here, with the site's address removed")
    args = parser.parse_args(argv)
    del LINES[:]
    secrets, conn, code, log_to, notes_at_start = [], None, 0, getattr(args, "log", None), None
    try:
        if args.command == "rules":
            code = cmd_rules(args)
        else:
            own = [os.path.join(args.out_dir, args.name + ending) for ending in (".json", ".md", ".notes.md")]
            notes_at_start = file_sum(own[2])
            if log_to:
                try:
                    may_write(log_to, own)
                except Refused as no:
                    log_to = None           # and the refusal below is NOT saved there: that would be the very write refused
                    raise Refused("--log: %s" % no)
            now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            if args.source == "fake":
                if not args.state:
                    raise Refused("--source fake needs --state, the folder that holds the made-up Jira")
                if args.pretend_now:
                    if in_utc(args.pretend_now.replace("Z", "+0000")) != args.pretend_now:
                        raise Refused("--pretend-now is a time such as 2026-11-08T12:00:00Z")
                    now = args.pretend_now
                import fake_jira
                fake = fake_jira.FakeJira.open(os.path.join(args.state, "fake-jira.json"))
                conn = Connection(fake.get, urllib.parse.urlparse(fake_jira.SITE).hostname)
                try:
                    code = cmd_sync(args, conn, False, now)
                finally:
                    fake.save(os.path.join(args.state, "fake-jira.json"))
            else:
                if args.state or args.pretend_now:
                    raise Refused("--state and --pretend-now are for the made-up Jira only")
                conn, secrets = make_live()
                code = cmd_sync(args, conn, True, now)
    except WriteFailed as failure:
        del LINES[:]
        say("NOT FINISHED: %s." % failure)
        say("Nothing was changed in Jira: this tool can only read.")
        code = 1
    except Refused as refusal:
        del LINES[:]
        say("REFUSED: %s." % refusal)
        say("The copy on disk is as it was before this sync. Nothing was changed in Jira: this tool can only read.")
        code = 1
    except Exception as surprise:           # anything unforeseen
        del LINES[:]
        say("REFUSED: the tool stopped on something it did not foresee (%s)." % type(surprise).__name__)
        say("Nothing was changed in Jira: this tool can only read. Check the two files' checksums before trusting the copy.")
        code = 1
    text = "\n".join(LINES)
    if any(secret and secret in text for secret in secrets):
        print("STOPPED: a credential was found in the output, so the output was not shown or saved.")
        return 1
    print(text)
    kept = text
    if secrets:
        note = "\nThe output above was searched for the API token, the account's email address and their encoded\nform: none found."
        print(note)
        kept += "\n" + note
    if log_to:
        host = conn.host if conn else ""
        kept = kept.replace("https://" + host, SITE_MARK).replace(host, SITE_MARK) if host else kept
        try:
            os.makedirs(os.path.dirname(os.path.abspath(log_to)), exist_ok=True)
            with open(log_to, "w", encoding="utf-8") as f:
                f.write(kept + "\n")
        except OSError:
            print("\nTHE OUTPUT ABOVE COULD NOT BE SAVED where --log said. What it says stands.")
    if args.command == "sync" and "own" in locals() and file_sum(own[2]) != notes_at_start:
        print("\nTHE NOTES FILE IS NOT WHAT IT WAS WHEN THIS COMMAND STARTED. This tool does not write it. Look at it before anything else.")
        return 1
    return code


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    sys.exit(main())
