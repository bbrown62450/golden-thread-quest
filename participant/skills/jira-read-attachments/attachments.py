#!/usr/bin/env python3
"""Records what is attached to a Jira story WITHOUT FETCHING ANY OF IT, and fetches one attachment only when a person
names it, after checks. IT ONLY READS JIRA.

    attachments.py sync     --source live|fake --issue KEY --out-dir DIR --name NAME [--state DIR] [--log FILE]
    attachments.py download --source fake --issue KEY --id ID --downloads DIR --state DIR [--log FILE]
    attachments.py limits

A SYNC DOWNLOADS NOTHING. It asks Jira for the story's list of attachments and writes two files in DIR:

    NAME.json    for each attachment: Jira's identifier, its name, the type and size Jira states, who attached it
                 (as "me", "someone else" or "unknown"), and when
    NAME.md      the same as an index, to be read

There is no code in `sync` that asks for a file's contents. The output counts the requests it made, by kind.

A DOWNLOAD HAPPENS ONLY WHEN A PERSON NAMES ONE ATTACHMENT BY ITS IDENTIFIER, with --id. There is no "all", no
pattern and no list. One command fetches at most one file.

A DOWNLOAD FROM A REAL JIRA IS REFUSED. This tool has never fetched a real attachment. A real Jira does not hand
over a file itself: it sends the asker on to another server, and code that follows it there and writes what comes
back has not been tried against one. `download --source live` is refused before anything is asked. `sync` against a
real Jira is not affected: it never fetches a file.

THE NAME, THE TYPE AND THE SIZE ARE CLAIMS FROM A STRANGER. Before one byte is saved, in this order:

    1. the name     refused if it has a path in it (/ or \\), a "..", a character that cannot be seen, or nothing left
    2. the type     the LAST extension of the name must be on the allowed list, and the type Jira states must be one
                    that goes with that extension. `limits` prints the list. Anything not on it is refused:
                    archives, programs, scripts, office documents, web pages, and names with no extension
    3. the size     the size Jira states must be within the limit
    ... only then is the file asked for ...
    4. the bytes    are counted as they arrive. If they pass the limit the fetch is stopped and nothing is kept.
                    If their number is not the size Jira stated, refused
    5. how they begin  the first bytes must be what the extension says: a PNG begins as a PNG does, and so on. THIS
                    LOOKS AT THE BEGINNING ONLY. A picture or a PDF can begin rightly and carry anything after.
                    Text must be text all through: readable as UTF-8, with no zero byte, and not beginning as an
                    archive, a program or another kind of file begins
    6. a scan       for a short list of known patterns (below)

A REFUSAL SAYS WHICH CHECK AND WHY, AND KEEPS NOTHING. The bytes are held in memory until every check has passed.
Nothing is written to the downloads folder for a refused file.

THE FILE NAME FROM JIRA IS NEVER USED AS A PATH. The name the file is saved under is built by this tool:

    <Jira's identifier>-<letters, digits and dashes taken from the name, at most 40>.<the allowed extension>

So it cannot hold a slash, a dot-dot, a space or a second extension, and two attachments cannot be saved over each
other: the identifier is in the name. A file already there is not written over.

A DOWNLOADED FILE IS SAVED OUTSIDE SOURCE CONTROL. --downloads must be a folder that is in no repository this tool
can find (Git, Mercurial, Subversion and a few others, looked for in every folder above it), or a folder that Git
says it ignores AS A FOLDER. A folder whose contents are ignored by a pattern is not enough: another pattern could
take one file back. Git is asked with its own settings from the environment set aside. Anywhere else is refused. The file is saved readable
and writable by its owner only, and never marked as a program. THIS TOOL NEVER OPENS OR RUNS WHAT IT SAVES.

EVERY ATTEMPT THAT REACHES A DOWNLOADS FOLDER THIS TOOL ACCEPTS IS WRITTEN TO A LOG there, `download-log.jsonl`, one
line each: the time, the story, the attachment's identifier, whether it was saved or refused and why, and for a
saved file its name on disk, its size and its SHA-256 checksum. THE LOG IS OPENED BEFORE ANYTHING IS ASKED OF JIRA.
If it cannot be opened, nothing is fetched. If its line cannot be written after a file was saved, the file is taken
away again: there is no saved file without a line. Three refusals come before there is a log to write to, and are
not in it: a downloads folder that is refused, a download from a real Jira, and a log that cannot be opened.

THE SCAN IS A SHORT LIST OF PATTERNS. IT IS NOT ANTIVIRUS, and a file that passes it is not thereby safe:
    the test string antivirus makers publish; a program or a zip archive inside an allowed type; a private key; in a
    PDF, a script, something set to run or to send, or another file inside; in text, a line that starts a script, a
    script tag, a frame or a `javascript:` address; in a CSV, a cell that begins as a formula begins.
It is known to miss things: other kinds of archive after a picture, a PDF written to hide its own marks in ways
this does not undo, a web page saved as text. It also refuses some harmless files.

PEOPLE ARE NOT KEPT. No name, email address or account identifier is written. Who attached a file is worked out by
comparing two account identifiers, which are then dropped.

AN ATTACHMENT'S NAME IS OTHER PEOPLE'S TEXT, and can be private in itself. It is kept in the index, with characters
that cannot be seen replaced. A sync never prints it. The name a file is saved under does carry up to 40 letters and
digits taken from it, and that saved name is printed and logged. A live sync writes only inside a folder named
`local-data`, which this repository does not hand in.

REQUESTS. Every one is a GET. Against a real Jira only two are ever built: the story with its list of attachments,
and "which account am I". The two that concern one attachment are asked of the made-up Jira only.

--state DIR is for the made-up Jira (--source fake): the folder that holds it.
--log FILE saves the output with the site's address replaced by a marker.

For a live sync the connection comes from the environment variables JIRA_BASE_URL, JIRA_EMAIL and JIRA_API_TOKEN. None
is stored. The output is searched for the token, the email address and their encoded form before it is shown.

Exit codes: 0 done (a sync wrote the index; a download saved the file and logged it); 1 REFUSED before the checks, or
something could not be read or written: nothing is saved, and if the downloads folder was accepted and its log
opened there is a line in the log; 2 a download REFUSED BY A CHECK: nothing saved, and a line in the log.
"""
import argparse
import base64
import csv
import datetime
import hashlib
import http.client
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request

FORMAT = "jira-attachments/1"
REF = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,30}-[0-9]{1,9}")
NAME = re.compile(r"[a-z][a-z0-9-]{0,60}")
SITE_MARK = "[site address removed]"
PAGE_HEADING = "# Attachments · "
LOG_STARTS = ("Story:", "REFUSED", "STOPPED:", "Download asked for:", "The limits")
LOG_NAME = "download-log.jsonl"
OTHER_REPOSITORIES = (".hg", ".svn", ".jj", ".bzr", ".fslckout", "_FOSSIL_", "CVS")
MAX_PIECES = 20000
SIZE_LIMIT = 5 * 1024 * 1024
CHUNK = 65536
UNSEEN = re.compile("[\\x00-\\x1f\\x7f-\\xa0\\u00ad\\u034f\\u061c\\u115f\\u1160\\u200b-\\u200f\\u2028\\u2029\\u202a-\\u202e\\u2060-\\u2069\\u2800\\u3164\\ufeff\\ud800-\\udfff\\U000e0000-\\U000e007f]")

# ---------------------------------------------------------------- the limits
# extension: (the types Jira may state for it, how its first bytes are judged). Anything not here is refused.
ALLOWED = {
    "txt": (("text/plain",), "text"),
    "md": (("text/plain", "text/markdown"), "text"),
    "log": (("text/plain",), "text"),
    "csv": (("text/csv", "text/plain"), "text"),
    "json": (("application/json",), "json"),
    "png": (("image/png",), b"\x89PNG\r\n\x1a\n"),
    "jpg": (("image/jpeg",), b"\xff\xd8\xff"),
    "jpeg": (("image/jpeg",), b"\xff\xd8\xff"),
    "pdf": (("application/pdf",), b"%PDF-"),
}
# How other kinds of file begin. Text that begins like one of these is not text.
OTHER_KINDS = [(b"PK\x03\x04", "an archive (zip, or an office document)"), (b"MZ", "a Windows program"), (b"\x7fELF", "a Linux program"),
               (b"\xcf\xfa\xed\xfe", "a Mac program"), (b"\xfe\xed\xfa", "a Mac program"), (b"\xca\xfe\xba\xbe", "a program"),
               (b"%PDF-", "a PDF"), (b"\x89PNG", "a PNG picture"), (b"\xff\xd8\xff", "a JPEG picture"), (b"GIF8", "a GIF picture"),
               (b"Rar!", "an archive (rar)"), (b"7z\xbc\xaf", "an archive (7z)"), (b"\x1f\x8b", "a compressed file (gzip)"), (b"BZh", "a compressed file (bzip2)")]
TEST_STRING_HALVES = (b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$", b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*")

LINES = []


class Refused(Exception):
    """Something could not be read, or a place could not be used. The message is the reason."""


class Check(Exception):
    """One of the checks on an attachment refused it. `which` names the check; the message is the reason."""

    def __init__(self, which, reason):
        Exception.__init__(self, reason)
        self.which = which


def say(text=""):
    LINES.append(text)


def plain(text, limit):
    """Other people's text, with characters that cannot be seen replaced, cut to a length."""
    return UNSEEN.sub("?", text)[:limit] if isinstance(text, str) else None


def shown(text, limit=80):
    return "".join("?" if UNSEEN.match(ch) else ch for ch in str(text))[:limit]


def ident(value):
    return isinstance(value, str) and re.fullmatch(r"0|[1-9][0-9]{0,19}", value) is not None


def in_utc(value):
    if not isinstance(value, str):
        return None
    for shape in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.datetime.strptime(value, shape).astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except (ValueError, OverflowError):
            continue
    return None


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def size_text(count):
    return "%d bytes" % count if count < 1024 else "%.1f KB" % (count / 1024.0) if count < 1024 * 1024 else "%.1f MB" % (count / 1048576.0)


def file_sum(path):
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except FileNotFoundError:
        return None


def same_file(a, b):
    try:
        if os.path.exists(a) and os.path.exists(b):
            return os.path.samefile(a, b)
    except OSError:
        pass
    return os.path.realpath(a).casefold() == os.path.realpath(b).casefold()


def listing(folder):
    """Every file in a folder and below it, as sorted paths from the folder, with sizes."""
    out = []
    for root, _, names in os.walk(folder):
        for name in names:
            path = os.path.join(root, name)
            out.append((os.path.relpath(path, folder), os.lstat(path).st_size))
    return sorted(out)


# ---------------------------------------------------------------- the checks on one attachment


def check_name(name):
    """Refuses a name that is hostile. Returns the extension, in small letters."""
    if not isinstance(name, str) or not name.strip():
        raise Check("the name", "the attachment has no name")
    if "/" in name or "\\" in name:
        raise Check("the name", "the name has a path in it (a slash). A name is not a place")
    if ".." in name:
        raise Check("the name", "the name has `..` in it, which is how a path climbs out of a folder")
    if UNSEEN.search(name):
        raise Check("the name", "the name has a character in it that cannot be seen, which can make one name look like another")
    if name != name.strip() or name.endswith("."):
        raise Check("the name", "the name begins or ends with a space or ends with a dot, which some systems silently drop")
    if len(name) > 255:
        raise Check("the name", "the name is longer than a file name may be")
    if "." not in name.strip("."):
        raise Check("the type", "the name has no extension, so its type cannot be told")
    extension = name.rsplit(".", 1)[1]
    if not re.fullmatch(r"[A-Za-z0-9]{1,10}", extension):
        raise Check("the type", "the name's extension is not plain letters and digits, so it is on no list")
    return extension.lower()


def check_claims(name, stated_type, stated_size):
    """Checks 1 to 3: what Jira says about the attachment, before any of it is fetched. Returns the extension."""
    extension = check_type(check_name(name), stated_type)
    check_size(stated_size)
    return extension


def check_type(extension, stated_type):
    if extension not in ALLOWED:
        raise Check("the type", "the name ends in an extension that is not on the allowed list. Allowed: %s" % ", ".join(sorted(ALLOWED)))
    stated = stated_type.split(";")[0].strip().casefold() if isinstance(stated_type, str) else ""
    if stated not in ALLOWED[extension][0]:
        raise Check("the type", "Jira states a type that does not go with the name's extension (.%s goes with %s)" % (extension, " or ".join(ALLOWED[extension][0])))
    return extension


def check_size(stated_size):
    if type(stated_size) is not int or stated_size < 0:
        raise Check("the size", "Jira does not state a size that is a whole number of bytes")
    if stated_size > SIZE_LIMIT:
        raise Check("the size", "Jira states a size of %s, and the limit is %s" % (size_text(stated_size), size_text(SIZE_LIMIT)))


def check_bytes(extension, data):
    """Check 5: the bytes are what the extension says."""
    how = ALLOWED[extension][1]
    if isinstance(how, bytes):
        if not data.startswith(how):
            raise Check("what the bytes are", "the file does not begin the way a .%s file begins%s" % (extension, begins_as(data)))
        return
    if b"\x00" in data:
        raise Check("what the bytes are", "the file is named as text and has a zero byte in it, which text does not%s" % begins_as(data))
    for start, what in OTHER_KINDS:
        if data.startswith(start):
            raise Check("what the bytes are", "the file is named as text and begins the way %s begins" % what)
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise Check("what the bytes are", "the file is named as text and is not readable as text (UTF-8)")
    if how == "json":
        try:
            json.loads(text)
        except (ValueError, RecursionError):
            raise Check("what the bytes are", "the file is named .json and is not JSON")


def begins_as(data):
    for start, what in OTHER_KINDS:
        if data.startswith(start):
            return ". It begins the way %s begins" % what
    return ""


def scan(extension, data):
    """Check 6: a short list of known patterns. NOT antivirus."""
    if TEST_STRING_HALVES[0] + TEST_STRING_HALVES[1] in data:
        raise Check("the scan", "the file holds the test string that antivirus makers publish")
    if b"This program cannot be run in DOS mode" in data or b"\x7fELF" in data:
        raise Check("the scan", "the file has a program inside it")
    if b"PK\x03\x04" in data:
        raise Check("the scan", "the file has an archive inside it")
    if re.search(rb"-----BEGIN [A-Z ]*PRIVATE KEY( BLOCK)?-----|PuTTY-User-Key-File", data):
        raise Check("the scan", "the file holds a private key")
    if extension == "pdf":
        # A PDF may write any letter of a name as # and two hex digits. Those are undone before the marks are looked for.
        undone = re.sub(rb"#([0-9A-Fa-f]{2})", lambda m: bytes([int(m.group(1), 16)]), data)
        for mark, what in ((b"/JavaScript", "a script"), (b"/JS", "a script"), (b"/OpenAction", "something set to run when it is opened"), (b"/AA", "something set to run by itself"),
                           (b"/Launch", "an instruction to start a program"), (b"/EmbeddedFile", "another file inside it"), (b"/SubmitForm", "an instruction to send what is typed into it"),
                           (b"/GoToR", "an instruction to open another file"), (b"/RichMedia", "media that plays by itself"), (b"/XFA", "a form that can run scripts")):
            if re.search(re.escape(mark) + rb"(?![A-Za-z])", undone):
                raise Check("the scan", "the PDF has %s in it" % what)
    elif ALLOWED[extension][1] in ("text", "json"):
        text = data.decode("utf-8", "replace")
        if text.lstrip("\ufeff \t\r\n").startswith("#!"):
            raise Check("the scan", "the file's first line starts a script")
        if re.search(r"<\s*script\b", text, re.I):
            raise Check("the scan", "the file has a script tag in it")
        if re.search(r"<\s*iframe\b|javascript\s*:", text, re.I):
            raise Check("the scan", "the file has a frame or a `javascript:` address in it")
        if extension == "csv":
            # A cell is looked at whatever separates the cells (comma, semicolon or tab), with spaces and quotes taken
            # off its front. It is refused if it then begins with = + - or @, in either width, unless it is a plain number.
            for cell in re.split(r"[,;\t\r\n]", text):
                bare = cell.strip(" \"'\u00a0")
                if bare[:1] in ("=", "+", "-", "@", "\uff1d", "\uff0b", "\uff0d", "\uff20") and not re.fullmatch(r"[+-]?[0-9]+([.,][0-9]+)?%?", bare):
                    raise Check("the scan", "the CSV has a cell that begins the way a formula begins")


def saved_name(number, name, extension):
    """The name the file is saved under. Built here. Jira's name gives it some letters and nothing else."""
    stem = name.rsplit(".", 1)[0].casefold()
    slug = re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", stem)).strip("-")[:40].strip("-")
    return "%s-%s.%s" % (number, slug or "attachment", "jpg" if extension == "jpeg" else extension)


# ---------------------------------------------------------------- the connection: GET only


class Connection:
    """Every request goes through `get` and is written down. `content` exists only where the made-up Jira is behind it."""

    def __init__(self, get, host, content=None):
        self._get, self.host, self._content = get, host, content
        self.sent = []

    def get(self, path, params=None):
        try:
            answer = self._get(path, params)
        except (OSError, TimeoutError) as err:
            self.sent.append(("?", path))
            raise Refused("Jira could not be reached (%s)" % type(getattr(err, "reason", err)).__name__)
        self.sent.append((answer[3] + (" WITH A BODY" if answer[4] else "") if len(answer) == 5 else "GET (the made-up Jira)", path))
        return answer[0], answer[2]

    def content(self, number):
        if self._content is None:
            raise Refused("this connection has no way to ask for a file's contents")
        self.sent.append(("GET (the made-up Jira)", "/rest/api/3/attachment/content/%s" % number))
        return self._content(number)

    def only_gets(self):
        return all(method.split(" ")[0] == "GET" and "BODY" not in method for method, _ in self.sent)

    def asked_for_contents(self):
        return sum(1 for _, path in self.sent if "/content/" in path)


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
        # The story, and "which account am I". Nothing about one attachment, and never a file's contents.
        if not (path == "/rest/api/3/myself" or re.fullmatch(r"/rest/api/3/issue/[A-Za-z0-9_-]+", path)):
            raise Refused("against a real Jira this tool asks for a story's list of attachments and for its own account, and nothing else")
        request = urllib.request.Request(base + path + ("?" + urllib.parse.urlencode(params) if params else ""), method="GET")
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

    return Connection(get, host), [token, email, encoded]          # no `content`: there is no way to ask a real Jira for a file


def site_fingerprint(host):
    return hashlib.sha256(host.lower().encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------- reading Jira


def read_me(conn):
    status, body = conn.get("/rest/api/3/myself")
    if status == 401:
        raise Refused("Jira rejected the credentials (401). Check JIRA_EMAIL and JIRA_API_TOKEN")
    account = body.get("accountId") if status == 200 and isinstance(body, dict) else None
    if not isinstance(account, str) or not account:
        raise Refused("Jira did not say which account is reading (status %d), so \"me\" cannot be told from \"someone else\"" % status)
    return account


def one_attachment(raw, me, live=False):
    """What is kept of one attachment as Jira describes it. People are compared and dropped here."""
    if not isinstance(raw, dict) or not ident(raw.get("id")):
        raise Refused("Jira sent an attachment without an identifier that can be used")
    created = in_utc(raw.get("created"))
    name = raw.get("filename")
    if created is None or not isinstance(name, str) or not name:
        raise Refused("Jira sent the attachment %s without a name or a date that can be read" % raw["id"])
    size = raw.get("size")
    author = raw.get("author", {}).get("accountId") if isinstance(raw.get("author"), dict) else None
    try:
        check_claims(name, raw.get("mimeType"), size)
        verdict = ("could not be asked for: this tool does not download from a real Jira. Its name, stated type and stated size would pass the first three checks" if live else
                   "could be asked for: its name, stated type and stated size pass the first three checks")
    except Check as no:
        verdict = "would be refused by %s: %s" % (no.which, no)
    return {"id": raw["id"], "name": plain(name, 200), "name_cut_or_changed": plain(name, 200) != name,
            "stated_type": plain(raw.get("mimeType"), 80) or "none stated", "stated_size": size if type(size) is int and size >= 0 else None,
            "attached_by": "unknown" if not (isinstance(author, str) and author) else "me" if author == me else "someone else",
            "attached": created, "if_asked_for": verdict}


def read_story(conn, key):
    status, body = conn.get("/rest/api/3/issue/%s" % key, {"fields": "attachment"})
    if status == 401:
        raise Refused("Jira rejected the credentials (401). Check JIRA_EMAIL and JIRA_API_TOKEN")
    if status == 404:
        raise Refused("Jira answered 404 for the story. It does not exist, or this account is not permitted to see it")
    fields = body.get("fields") if status == 200 and isinstance(body, dict) else None
    if not (isinstance(fields, dict) and ident(body.get("id")) and isinstance(body.get("key"), str) and REF.fullmatch(body["key"])):
        raise Refused("Jira's answer for the story could not be used (status %d)" % status)
    if body["key"].upper() != key.upper():
        raise Refused("Jira answered with the story %s. The story asked for has been moved or renamed" % body["key"].upper())
    listed = fields.get("attachment")
    if not isinstance(listed, list):
        raise Refused("Jira's answer for the story has no list of attachments in it. An empty list would be an answer; no list is not")
    return {"key": body["key"].upper(), "id": body["id"]}, listed


# ---------------------------------------------------------------- the index


def render(index):
    out = [PAGE_HEADING + index["story"]["key"], "",
           "**Written by a tool. Do not edit this file: the next sync writes it again from `%s`.**" % index["files"]["index"], "",
           "Source: %s." % ("the made-up Jira; every attachment here is made up" if index["source"] == "fake" else "a real Jira, site fingerprint %s" % index["site_fingerprint"]),
           "**No file was downloaded to make this.** It is what Jira says is attached. The name, the type and the size are Jira's statements, not facts about the files.",
           "No person is named: who attached each is \"me\" (the account that reads), \"someone else\" or \"unknown\". Dates are UTC.", ""]
    if not index["attachments"]:
        return "\n".join(out + ["The story has no attachments.", ""])
    out += ["| Identifier | Name, as Jira gives it | Stated type | Stated size | Attached by | Attached | If a person asked for it |", "|---|---|---|---|---|---|---|"]
    for a in index["attachments"]:
        name = "`%s`" % a["name"].replace("`", "'").replace("|", "¦") + (" (changed or cut here)" if a["name_cut_or_changed"] else "")
        out.append("| %s | %s | `%s` | %s | %s | %s | %s |" % (
            a["id"], name, a["stated_type"].replace("`", "'").replace("|", "¦"), "not stated" if a["stated_size"] is None else size_text(a["stated_size"]),
            a["attached_by"], a["attached"], a["if_asked_for"].replace("|", "¦")))
    out += ["", "%d attachment%s. The last column is what the first three checks would say. The other three need the file itself and are made only if a person asks for it." % (
        len(index["attachments"]), "" if len(index["attachments"]) == 1 else "s"), ""]
    return "\n".join(out)


def good_index(index):
    keys = {"id", "name", "name_cut_or_changed", "stated_type", "stated_size", "attached_by", "attached", "if_asked_for"}
    return (isinstance(index, dict) and index.get("format") == FORMAT and isinstance(index.get("story"), dict) and isinstance(index.get("attachments"), list)
            and all(isinstance(a, dict) and set(a) == keys and ident(a["id"]) for a in index["attachments"]))


def load_index(path):
    if os.path.lexists(path) and (not os.path.isfile(path) or os.path.getsize(path) > 20 * 1024 * 1024):
        raise Refused("the index on disk is not a plain file")
    try:
        with open(path, encoding="utf-8") as f:
            raw = f.read()
    except FileNotFoundError:
        return None
    except (OSError, UnicodeDecodeError):
        raise Refused("the index on disk could not be read")
    try:
        index = json.loads(raw)
    except ValueError:
        index = None
    if not good_index(index):
        raise Refused("the index on disk is not one this tool wrote. It is left as it is. Use another --name")
    return index


def write_file(path, text, private=False):
    """Writes a whole file or none of it. A private file (a download) is never written over one that is there: it is
    given its name by linking, which fails if the name is taken, however lately it was taken."""
    handle, temporary = tempfile.mkstemp(prefix=".attachments-", suffix=".tmp", dir=os.path.dirname(path))
    try:
        with os.fdopen(handle, "wb") as f:
            f.write(text if isinstance(text, bytes) else text.encode("utf-8"))
        os.chmod(temporary, 0o600 if private else 0o644)
        if private:
            os.link(temporary, path)
            os.unlink(temporary)
        else:
            os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def places(out_dir, name, live):
    if not NAME.fullmatch(name):
        raise Refused("--name is lower-case letters, digits and dashes, starting with a letter")
    folder = os.path.realpath(out_dir)
    if not os.path.isdir(folder):
        raise Refused("--out-dir is not a folder that exists")
    if live and "local-data" not in folder.split(os.sep):
        raise Refused("a live sync writes only inside a folder named `local-data`, which is not handed in, because the names of real attachments can be private")
    index_path, page_path = os.path.join(folder, name + ".json"), os.path.join(folder, name + ".md")
    for path in (index_path, page_path):
        if os.path.islink(path) or os.path.isdir(path) or (os.path.exists(path) and os.stat(path).st_nlink > 1):
            raise Refused("%s in the folder is a link, a folder, or a file with a second name. This tool writes only a plain file of its own" % os.path.basename(path))
    if os.path.exists(page_path) and not os.path.exists(index_path):
        with open(page_path, "rb") as f:
            if f.read(len(PAGE_HEADING.encode("utf-8"))) != PAGE_HEADING.encode("utf-8"):
                raise Refused("a file named %s is already in the folder and it is not a page this tool wrote. It is left as it is" % shown(os.path.basename(page_path)))
    return index_path, page_path


# ---------------------------------------------------------------- the downloads folder


def outside_source_control(folder):
    """Returns a sentence saying why the folder is outside source control, or raises Refused. `folder` is a real path."""
    at, git_at = folder, None
    while True:
        for mark in OTHER_REPOSITORIES:
            if os.path.lexists(os.path.join(at, mark)):
                raise Refused("--downloads is inside a repository of a kind this tool cannot ask (%s was found above it), so it cannot be shown to be outside source control" % mark)
        if git_at is None and os.path.lexists(os.path.join(at, ".git")):
            git_at = at
        parent = os.path.dirname(at)
        if parent == at:
            break
        at = parent
    if git_at is None:
        return "no repository was found in it or in any folder above it"
    if folder == git_at:
        raise Refused("--downloads is the top of a Git repository")
    # Git is asked about the FOLDER ITSELF. When a folder is ignored as a folder, Git does not look inside it, and no
    # other pattern can take a file in it back. Git's own settings from the environment are set aside, so that the
    # question is about this repository as it stands on disk.
    clean = {k: v for k, v in os.environ.items() if not k.upper().startswith("GIT_")}
    try:
        asked = subprocess.run(["git", "-C", git_at, "check-ignore", "-q", "--", folder], capture_output=True, timeout=20, env=clean)
    except (OSError, subprocess.SubprocessError):
        raise Refused("--downloads is inside a Git repository, and Git could not be asked whether it ignores that folder")
    if asked.returncode != 0:
        raise Refused("--downloads is inside a Git repository and Git does not ignore that folder as a folder, so a file saved there could be committed. "
                      "Choose a folder outside the repository, or one Git ignores whole")
    return "it is inside a Git repository, and Git says it ignores that folder whole"


def open_log(downloads):
    """Opens the download log for adding to, and returns the handle. Done BEFORE anything is asked of Jira, so that
    nothing is fetched which could not then be logged."""
    path = os.path.join(downloads, LOG_NAME)
    if os.path.islink(path) or (os.path.lexists(path) and (not os.path.isfile(path) or os.stat(path).st_nlink > 1)):
        raise Refused("the download log in that folder is a link, or is not a plain file of this tool's. Nothing was asked of Jira")
    try:
        return os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
    except OSError:
        raise Refused("the download log in that folder could not be opened for adding to. Nothing was asked of Jira")


def log_line(handle, entry):
    line = json.dumps(entry, sort_keys=True, ensure_ascii=True) + "\n"
    os.write(handle, line.encode("utf-8"))
    os.fsync(handle)
    return line.rstrip("\n")


# ---------------------------------------------------------------- the commands


def cmd_limits():
    say("The limits this tool applies before it saves an attachment.")
    say("")
    say("SIZE: at most %s, by what Jira states and again by counting the bytes as they arrive." % size_text(SIZE_LIMIT))
    say("")
    say("TYPE: only these. The last extension of the name, the type Jira states, and how the file's own bytes begin must all agree.")
    for extension in sorted(ALLOWED):
        types, how = ALLOWED[extension]
        say("  .%-5s Jira may state %-28s the bytes must %s" % (extension, " or ".join(types) + ";", "begin as that kind of file begins" if isinstance(how, bytes) else
                                                           "be JSON, readable as UTF-8 text" if how == "json" else "be text: readable as UTF-8, no zero byte, not beginning as another kind of file"))
    say("  Anything else is refused: archives, programs, scripts, office documents, web pages, SVG pictures, and a name with no extension.")
    say("")
    say("NAME: refused if it has a slash, a `..`, a character that cannot be seen, or a space or dot at its end. It is never used as a path.")
    say("")
    say("THE SCAN, a short list of patterns and NOT antivirus: the published antivirus test string; a program or archive inside the file; in a PDF, a script")
    say("or something set to run; in text, a private key, a script's first line or a script tag; in a CSV, a cell a spreadsheet would run as a formula.")
    return 0


def cmd_sync(args, conn, live, secrets=()):
    if not REF.fullmatch(args.issue):
        raise Refused("--issue is a story's key, such as DEMO-7")
    index_path, page_path = places(args.out_dir, args.name, live)
    folder = os.path.dirname(index_path)
    before = (file_sum(index_path), file_sum(page_path))
    files_before = listing(folder)
    old = load_index(index_path)
    source, site = ("live", site_fingerprint(conn.host)) if live else ("fake", None)
    if old is not None and (old["story"].get("key"), old.get("source"), old.get("site_fingerprint")) != (args.issue.upper(), source, site):
        raise Refused("the index on disk is of another story, or was made from another Jira. It is left as it is. Use another --name")

    me = read_me(conn)
    story, listed = read_story(conn, args.issue)
    attachments = [one_attachment(raw, me, live) for raw in listed]
    numbers = [a["id"] for a in attachments]
    if len(set(numbers)) != len(numbers):
        raise Refused("Jira listed one attachment twice, so the list cannot be trusted to be whole")
    attachments.sort(key=lambda a: int(a["id"]))
    index = {"format": FORMAT, "story": story, "source": source, "site_fingerprint": site, "attachments": attachments,
             "files": {"index": args.name + ".json", "page": args.name + ".md"}}
    index_text = json.dumps(index, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    page_text = render(index)

    say("Story: %s" % story["key"])
    say("Read from: %s" % ("a real Jira, site fingerprint %s" % site if live else "the made-up Jira. No real Jira was contacted"))
    say("")
    say("ATTACHMENTS LISTED BY JIRA: %d. For each, the index now holds its identifier, name, stated type, stated size, who attached it and when." % len(attachments))
    by_me = {word: sum(1 for a in attachments if a["attached_by"] == word) for word in ("me", "someone else", "unknown")}
    say("  attached by me: %d; by someone else: %d; unknown: %d" % (by_me["me"], by_me["someone else"], by_me["unknown"]))
    could = sum(1 for a in attachments if a["if_asked_for"].startswith("could be asked for"))
    say("  by name, stated type and stated size alone: %d could be asked for, %d would be refused. NONE WAS ASKED FOR." % (could, len(attachments) - could))
    for a in attachments:
        say("    %s  %-12s %-22s %-13s %s" % (a["id"], "not stated" if a["stated_size"] is None else size_text(a["stated_size"]), a["stated_type"][:22], a["attached_by"], a["if_asked_for"].split(":")[0]))
    say("  Names are in the index and are not printed here: a name is other people's text.")
    if any(secret and secret in "\n".join(LINES) + index_text + page_text for secret in secrets):
        raise Refused("a credential was found in what would be shown or saved")
    wrote = []
    try:
        if before[0] != hashlib.sha256(index_text.encode("utf-8")).hexdigest():
            write_file(index_path, index_text)
            wrote.append(os.path.basename(index_path))
        if before[1] != hashlib.sha256(page_text.encode("utf-8")).hexdigest():
            write_file(page_path, page_text)
            wrote.append(os.path.basename(page_path))
    except OSError:
        raise Refused("a file could not be written%s" % ("" if not wrote else ". The index was written and the page was not: run the sync again"))
    files_after = listing(folder)
    new_files = sorted(set(n for n, _ in files_after) - set(n for n, _ in files_before))
    say("")
    say("NO FILE WAS DOWNLOADED.")
    say("  Requests that ask for a file's contents: %d. This command has no code that makes one." % conn.asked_for_contents())
    say("  Files in the folder given with --out-dir, before: %d. After: %d. New: %s." % (len(files_before), len(files_after), ", ".join(shown(n) for n in new_files) or "none"))
    say("  The only files this command writes are the index and its page: %s." % (", ".join(wrote) + " written" if wrote else "both were already as they should be, and neither was written"))
    say("")
    say("RESULT: INDEX %s. %d attachment%s recorded. No attachment was fetched." % ("WRITTEN" if wrote else "UNCHANGED", len(attachments), "" if len(attachments) == 1 else "s"))
    say_requests(conn)
    return 0


def say_requests(conn):
    say("")
    if conn.only_gets():
        say("Requests sent to Jira: %d. Every one was a GET with no body, which reads and cannot change anything." % len(conn.sent))
    else:
        say("Requests sent to Jira: %d. NOT EVERY ONE COULD BE READ BACK AS A PLAIN GET:" % len(conn.sent))
    shapes = {}
    for method, path in conn.sent:
        shape = method + " " + re.sub(r"/content/[0-9]+", "/content/{id}", re.sub(r"/attachment/[0-9]+", "/attachment/{id}", re.sub(r"/issue/[^/]+", "/issue/{key}", path)))
        shapes[shape] = shapes.get(shape, 0) + 1
    for shape in sorted(shapes):
        say("  %s  x%d" % (shape, shapes[shape]))


def cmd_download(args, conn):
    if not REF.fullmatch(args.issue):
        raise Refused("--issue is a story's key, such as DEMO-7")
    downloads = os.path.realpath(args.downloads)
    if not os.path.isdir(downloads):
        raise Refused("--downloads is not a folder that exists")
    why_outside = outside_source_control(downloads)
    log = open_log(downloads)                       # before anything is asked of Jira
    try:
        return download_one(args, conn, downloads, why_outside, log)
    finally:
        os.close(log)


def download_one(args, conn, downloads, why_outside, log):
    before = listing(downloads)
    say("Download asked for: attachment %s of %s. One attachment, named by its identifier." % (shown(args.id, 30), args.issue.upper()))
    say("Asked of: the made-up Jira. No real Jira was contacted. Every file it serves is made up.")
    say("The downloads folder is outside source control: %s." % why_outside)
    say("The download log was opened before anything was asked of Jira.")
    say("")
    entry = {"time": now_utc(), "story": args.issue.upper(), "attachment": plain(args.id, 30), "outcome": "refused", "check": None, "reason": None,
             "saved_as": None, "bytes": None, "sha256": None, "stated_type": None, "stated_size": None}
    code, target, saved = 2, None, False
    try:
        if not ident(args.id):
            raise Refused("--id is ONE attachment's identifier, a number, as the index gives it. There is no way to ask for more than one")
        story, listed = read_story(conn, args.issue)
        if args.id not in [raw.get("id") for raw in listed if isinstance(raw, dict)]:
            raise Refused("the story %s has no attachment with the identifier %s" % (story["key"], args.id))
        status, raw = conn.get("/rest/api/3/attachment/%s" % args.id)
        if status != 200 or not isinstance(raw, dict) or raw.get("id") != args.id or not isinstance(raw.get("filename"), str):
            raise Refused("Jira did not describe the attachment %s (status %d)" % (args.id, status))
        name, stated_type, stated_size = raw["filename"], raw.get("mimeType"), raw.get("size")
        entry.update(stated_type=plain(stated_type, 80), stated_size=stated_size if type(stated_size) is int else None)
        say("1. THE NAME. Looked at, never used as a path.")
        extension = check_name(name)
        say("     passed: no path, no `..`, nothing that cannot be seen.")
        say("2. THE TYPE. The name's last extension is .%s, and Jira states %s." % (shown(extension, 12), shown(stated_type, 60)))
        check_type(extension, stated_type)
        say("     passed: the extension is on the allowed list, and the stated type goes with it.")
        say("3. THE SIZE. Jira states %s. The limit is %s." % ("%d bytes" % stated_size if type(stated_size) is int else "nothing usable", size_text(SIZE_LIMIT)))
        check_size(stated_size)
        say("     passed: the stated size is within the limit.")
        target = os.path.join(downloads, saved_name(args.id, name, extension))
        if os.path.lexists(target):
            raise Check("the place", "a file is already saved under that name (%s). It is not written over" % os.path.basename(target))
        say("4. THE BYTES, counted as they arrive.")
        status, pieces = conn.content(args.id)
        if status != 200:
            raise Refused("Jira did not send the file (status %d)" % status)
        held, count, taken = [], 0, 0
        for piece in pieces:
            taken += 1
            if not isinstance(piece, (bytes, bytearray)) or taken > MAX_PIECES:
                raise Check("the size", "the file did not arrive as a file does: in too many pieces, or in pieces that are not bytes. The fetch was stopped and nothing was kept")
            count += len(piece)
            if count > SIZE_LIMIT or count > stated_size:
                raise Check("the size", "more arrived than %s. The fetch was stopped and nothing was kept" % (
                    "the limit of %s, though Jira stated %d bytes" % (size_text(SIZE_LIMIT), stated_size) if count > SIZE_LIMIT else "the %d bytes Jira stated" % stated_size))
            held.append(bytes(piece))
        data = b"".join(held)
        if len(data) != stated_size:
            raise Check("the size", "%d bytes arrived and Jira stated %d. The file is not what was described" % (len(data), stated_size))
        say("     passed: %d bytes arrived, which is what Jira stated." % len(data))
        say("5. HOW THE BYTES BEGIN.")
        check_bytes(extension, data)
        say("     passed: %s" % ("the file is text all through: readable as UTF-8, no zero byte, and not beginning as another kind of file does." if ALLOWED[extension][1] == "text" else
                                "the file is JSON." if ALLOWED[extension][1] == "json" else
                                "the file BEGINS the way a .%s file begins. Only its beginning was looked at: what follows is not examined by this check." % extension))
        say("6. THE SCAN, a short list of known patterns. Not antivirus.")
        try:
            scan(extension, data)
        except (csv.Error, ValueError, RecursionError):
            raise Check("the scan", "the file could not be read well enough to be scanned")
        say("     passed: none of the patterns was found. That does not make the file safe.")
        try:
            write_file(target, data, private=True)
        except FileExistsError:
            raise Check("the place", "a file appeared under that name while this one was being fetched. It is not written over")
        except OSError:
            raise Refused("every check passed and the file could not be written to the downloads folder")
        saved = True
        entry.update(outcome="saved", saved_as=os.path.basename(target), bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
        code = 0
    except Check as no:
        entry.update(check=no.which, reason=str(no))
        say("     REFUSED BY THIS CHECK.")
        say("")
        say("REFUSED by %s: %s." % (no.which, no))
        say("Nothing was saved. The checks after this one were not made.")
    except Refused as no:
        entry.update(check="before the checks", reason=str(no))
        say("")
        say("REFUSED: %s." % no)
        say("Nothing was saved.")
        code = 1
    except Exception as surprise:           # anything unforeseen is still an attempt, and is still logged
        entry.update(check="something unforeseen", reason=type(surprise).__name__)
        say("")
        say("REFUSED: the tool stopped on something it did not foresee (%s)." % type(surprise).__name__)
        say("Nothing was saved.")
        code = 1
    # The line is written now. If a file was saved and its line cannot be written, the file is taken away again.
    try:
        written = log_line(log, entry)
    except OSError:
        if saved:
            try:
                os.unlink(target)
            except OSError:
                raise Refused("the file %s was saved and its line could not be written to the log, and the file could not then be taken away. LOOK AT THE DOWNLOADS FOLDER" % os.path.basename(target))
        raise Refused("the line for this attempt could not be written to the download log%s" % (". The file that had been saved was taken away again, so that no file is there without a line" if saved else ""))
    if saved:
        say("")
        say("SAVED as %s, in the folder given with --downloads. That name was built by this tool: the identifier, letters and digits taken from Jira's name, and the allowed extension." % os.path.basename(target))
        say("  %d bytes. SHA-256 %s." % (entry["bytes"], entry["sha256"]))
        say("  Readable and writable by its owner only, and not marked as a program. THIS TOOL DID NOT OPEN OR RUN IT, AND NEVER DOES.")
    say("")
    say("THE LOG. One line was added to %s in the downloads folder:" % LOG_NAME)
    say("  %s" % written)
    after = listing(downloads)
    say("")
    say("FILES IN THE DOWNLOADS FOLDER. Before: %d. After: %d." % (len(before), len(after)))
    for name, size in after:
        say("  %-60s %10d bytes%s" % (shown(name, 60), size, "   NEW" if name not in [n for n, _ in before] else ""))
    say("")
    say("RESULT: %s" % ("SAVED. One file, after six checks, and its line is in the log." if code == 0 else "NOT SAVED. Refused, and the reason is above and in the log."))
    say_requests(conn)
    return code


def main(argv=None):
    parser = argparse.ArgumentParser(description="Record a Jira story's attachments without fetching them. Fetch one only when named. Reads only.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("limits")
    sub = commands.add_parser("sync")
    sub.add_argument("--source", choices=("live", "fake"), required=True)
    sub.add_argument("--issue", required=True)
    sub.add_argument("--out-dir", required=True)
    sub.add_argument("--name", required=True, help="the files are NAME.json and NAME.md")
    sub.add_argument("--state", help="with --source fake: the folder that holds the made-up Jira")
    sub.add_argument("--log", help="also save the output here, with the site's address removed")
    sub = commands.add_parser("download")
    sub.add_argument("--source", choices=("live", "fake"), required=True)
    sub.add_argument("--issue", required=True)
    sub.add_argument("--id", required=True, help="ONE attachment's identifier")
    sub.add_argument("--downloads", required=True, help="a folder outside source control")
    sub.add_argument("--state", help="the folder that holds the made-up Jira")
    sub.add_argument("--log", help="also save the output here")
    args = parser.parse_args(argv)
    del LINES[:]
    secrets, conn, code, log_to = [], None, 0, getattr(args, "log", None)
    try:
        if args.command == "limits":
            code = cmd_limits()
        else:
            own = [os.path.join(args.out_dir, args.name + ending) for ending in (".json", ".md")] if args.command == "sync" else [os.path.join(args.downloads, LOG_NAME)]
            if log_to:
                inside = args.command == "download" and os.path.realpath(os.path.dirname(os.path.abspath(log_to))).casefold().startswith(os.path.realpath(args.downloads).casefold())
                already = b""
                if os.path.isfile(log_to) and not os.path.islink(log_to):
                    with open(log_to, "rb") as f:
                        already = f.read(40)
                if (os.path.islink(log_to) or (os.path.isfile(log_to) and os.stat(log_to).st_nlink > 1) or any(same_file(log_to, path) for path in own) or inside
                        or (os.path.lexists(log_to) and not already.startswith(tuple(start.encode("utf-8") for start in LOG_STARTS)))):
                    log_to = None           # and the refusal below is NOT saved there: that would be the very write refused
                    raise Refused("--log names one of this tool's own files, a place in the downloads folder, a link, or something already there that is not an output of this tool")
            if args.command == "download" and args.source == "live":
                raise Refused("a download from a real Jira is not something this tool does. It has never fetched a real attachment, and the way a real Jira hands one over "
                              "has not been tried. Nothing was asked of Jira")
            if args.source == "fake":
                if not args.state:
                    raise Refused("--source fake needs --state, the folder that holds the made-up Jira")
                import fake_jira
                fake = fake_jira.FakeJira.open(os.path.join(args.state, "fake-jira.json"))
                conn = Connection(fake.get, urllib.parse.urlparse(fake_jira.SITE).hostname, fake.content)
                try:
                    code = cmd_sync(args, conn, False) if args.command == "sync" else cmd_download(args, conn)
                finally:
                    fake.save(os.path.join(args.state, "fake-jira.json"))
            else:
                if args.state:
                    raise Refused("--state is for the made-up Jira only")
                conn, secrets = make_live()
                code = cmd_sync(args, conn, True, secrets)
    except Refused as refusal:
        del LINES[:]
        say("REFUSED: %s." % refusal)
        say("Nothing was changed in Jira: this tool can only read.")
        code = 1
    except Exception as surprise:           # anything unforeseen
        del LINES[:]
        say("REFUSED: the tool stopped on something it did not foresee (%s)." % type(surprise).__name__)
        say("Nothing was changed in Jira: this tool can only read. Look at the folder before trusting what is in it.")
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
    return code


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    sys.exit(main())
