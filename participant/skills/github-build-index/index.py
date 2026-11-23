#!/usr/bin/env python3
"""Build an index of the local GitHub issue records. Reads local files only. Contacts nothing.

See SKILL.md in this folder for what it does and the rules it follows.

    index.py build  [--records FOLDER] [--out FILE]          write the index from the records
    index.py check  [--records FOLDER] [--out FILE]          is the index still what the records give? Writes nothing
    index.py lookup KIND [VALUE | --none | --gap | --list]   look issues up FROM THE INDEX. KIND: repository, label, milestone, assignee
    index.py find TEXT [--records FOLDER]                    search the titles and text of the RECORDS

The records are the source of truth. The index is generated from them, whole, every time. It is never merged
with what was there, and it holds no date, so the same records always give the same bytes.

Exit codes: 0 built clean, up to date, or found; 1 stopped, or nothing found; 3 built with something a person
should look at (a gap, a file that could not be indexed, an issue in two files), or the index is stale or was edited.
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.parse

RECORD_FORMAT = "github-issue-markdown/1"
INDEX_FORMAT = "github-issue-index/1"
REPO_NAME = re.compile(r"^[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}$")
PLAIN_KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._:/-]{0,99}$")
KINDS = {"repository": "By repository", "label": "By label", "milestone": "By milestone", "assignee": "By assignee"}
NONE_GROUP = {"label": "(no label)", "milestone": "(no milestone)", "assignee": "(nobody assigned)"}
GAP_GROUP = "(GAP: this field could not be read from the record)"
# The link at the end of a table row. Every "[" in someone else's text is written with a backslash before it, so a
# "[" straight after a cell's opening "| " can only be the link this skill wrote.
ROW_END = re.compile(r"\| \[((?:[^\]\\]|\\.)*)\]\(([^)]*)\) \| ([0-9a-f]{12}) \|$")
ITEM = re.compile(r"^- \[((?:[^\]\\]|\\.)*)\]\(([^)]*)\) \(([^)]*)\) (.*)$")
BLOCK = re.compile(r"<!-- gtq:begin (\S+) ([0-9a-f]{16}) -->\n(.*?)\n<!-- gtq:end \1 \2 -->\n", re.S)


class Gap:
    """A field that should be in a record and is missing, or holds something that cannot be read."""

    def __init__(self, why):
        self.why = why


class Unreadable(Exception):
    """A file that is not a record at all. The message says why."""


class Stop(Exception):
    pass


def say(text):
    print("github-index: " + text, flush=True)


def plural(count, word, many=None):
    return "%d %s" % (count, word if count == 1 else many or word + "s")


def shown_path(path):
    try:
        relative = os.path.relpath(path)
    except ValueError:
        return os.path.basename(path)
    return os.path.basename(path) if relative.startswith("..") else relative


def cell(text):
    """Someone else's text, made safe to sit in a table cell, a list item or a link."""
    text = "".join(char if char >= " " and char != "\x7f" else " " for char in str(text))
    for old, new in (("\\", "\\\\"), ("|", "\\|"), ("`", "\\`"), ("[", "\\["), ("]", "\\]"), ("<", "&lt;"), (">", "&gt;"),
                     ("*", "\\*"), ("_", "\\_"), ("#", "\\#")):
        text = text.replace(old, new)
    return text.strip() or "(empty)"


def key_text(name):
    """A label, milestone, login or repository as it is written in a lookup heading: plain if it is plain, else as JSON."""
    return name if PLAIN_KEY.match(name) else json.dumps(name, ensure_ascii=False)


def key_from(text):
    """The reverse of key_text. Returns None for text that is neither."""
    if text.startswith('"'):
        try:
            return json.loads(text)
        except ValueError:
            return None
    return text


# ---------------------------------------------------------------- reading the records


def record_files(folder):
    """Every .md file directly in the folder, by name. Sub-folders and hidden files are not records."""
    if not os.path.isdir(folder):
        raise Stop("there is no records folder %s" % shown_path(folder))
    return sorted(name for name in os.listdir(folder)
                  if name.endswith(".md") and not name.startswith(".") and os.path.isfile(os.path.join(folder, name)))


def read_record(folder, name):
    """One record file. Returns its fields, with a Gap in place of any that is missing or cannot be read."""
    with open(os.path.join(folder, name), "rb") as f:
        raw = f.read()
    record = {"file": name, "digest": hashlib.sha256(raw).hexdigest()}
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise Unreadable("it is not UTF-8 text", record)
    if not text.startswith("---\n") or "\n---\n" not in text[3:]:
        raise Unreadable("it has no front matter, so it is not an issue record", record)
    front, damaged = {}, set()
    for line in text[4:text.index("\n---\n", 3)].split("\n"):
        key, colon, value = line.partition(": ")
        try:
            front[key] = json.loads(value) if colon else None
            if not colon:
                damaged.add(key)
        except ValueError:
            damaged.add(key)
    if "format" in damaged or front.get("format") != RECORD_FORMAT:
        raise Unreadable("it is not in the format %s" % RECORD_FORMAT, record)

    def field(key, good, what):
        if key in damaged:
            return Gap("the line is there and cannot be read")
        if key not in front:
            return Gap("the line is missing")
        return front[key] if good(front[key]) else Gap("it does not hold %s" % what)
    words = lambda value: isinstance(value, list) and all(isinstance(one, str) for one in value)
    record.update(
        repository=field("repository", lambda v: isinstance(v, str) and bool(REPO_NAME.match(v)), "a repository name"),
        number=field("number", lambda v: isinstance(v, int) and not isinstance(v, bool) and v > 0, "an issue number"),
        title=field("title", lambda v: isinstance(v, str), "text"),
        state=field("state", lambda v: isinstance(v, str) and bool(v), "a state"),
        labels=field("labels", words, "a list of label names"),
        assignees=field("assignees", words, "a list of logins"),
        milestone=field("milestone", lambda v: v is None or isinstance(v, str), "a milestone title or null"))
    record["body"] = body_of(text, field("body_sha256", lambda v: v is None or (isinstance(v, str) and len(v) == 64), "a checksum or null"))
    record["text"] = text
    return record


def body_of(text, digest):
    """The body, cut back out and checked against its recorded checksum. None when GitHub sent no body."""
    if isinstance(digest, Gap) or digest is None:
        return digest
    for name, tag, body in blocks(text):
        if name == "body":
            if tag == digest[:16] and hashlib.sha256(body.encode("utf-8")).hexdigest() == digest:
                return body
            break
    return Gap("the text in the file does not match its recorded checksum")


def blocks(text):
    """Every block of someone else's text in a record: (name, tag, text). Read in order, so a block inside a block is not taken for one."""
    return [(found.group(1), found.group(2), found.group(3)) for found in BLOCK.finditer(text.partition("\n## Content from GitHub\n")[2])]


def read_all(folder):
    """Every file in the folder, each exactly once: as a record, or as one that could not be indexed."""
    records, unreadable = [], []
    for name in record_files(folder):
        try:
            records.append(read_record(folder, name))
        except Unreadable as why:
            unreadable.append(dict(why.args[1], why=why.args[0]))
    known = lambda value: not isinstance(value, Gap)
    records.sort(key=lambda r: (not known(r["repository"]), r["repository"].casefold() if known(r["repository"]) else "",
                                not known(r["number"]), r["number"] if known(r["number"]) else 0, r["file"]))
    return records, unreadable


def fingerprint(records, unreadable):
    pairs = sorted((one["file"], one["digest"]) for one in records + unreadable)
    return hashlib.sha256(json.dumps(pairs).encode("utf-8")).hexdigest()


FIELDS = ("repository", "number", "title", "state", "labels", "milestone", "assignees", "body")


def gaps_of(record):
    return [(key, record[key].why) for key in FIELDS if isinstance(record[key], Gap)]


def same_issue(records):
    """Groups of files that hold the same repository and number."""
    groups = {}
    for one in records:
        if not isinstance(one["repository"], Gap) and not isinstance(one["number"], Gap):
            groups.setdefault((one["repository"], one["number"]), []).append(one["file"])
    return {key: files for key, files in groups.items() if len(files) > 1}


# ---------------------------------------------------------------- the index


def name_of(record):
    if isinstance(record["repository"], Gap) or isinstance(record["number"], Gap):
        return "file %s" % cell(record["file"])
    return "%s#%d" % (record["repository"], record["number"])


def link(text, record, records_rel):
    return "[%s](%s)" % (text, urllib.parse.quote("%s/%s" % (records_rel, record["file"])))


def grouped(records, kind):
    """The records under each value of one field. A record with a gap in that field goes under GAP, never nowhere."""
    groups = {}
    for one in records:
        value = one[{"repository": "repository", "label": "labels", "milestone": "milestone", "assignee": "assignees"}[kind]]
        if isinstance(value, Gap):
            keys = [GAP_GROUP]
        elif kind in ("repository", "milestone"):
            keys = [NONE_GROUP[kind] if value is None else key_text(value)]
        else:
            keys = sorted(set(key_text(name) for name in value)) or [NONE_GROUP[kind]]
        for key in keys:
            groups.setdefault(key, []).append(one)
    special = lambda key: (key == GAP_GROUP, key in NONE_GROUP.values(), key.casefold(), key)
    return [(key, groups[key]) for key in sorted(groups, key=special)]


def render(records, unreadable, records_rel):
    """The whole index, as text. The same records always give the same text: it holds no date and no time."""
    shown = lambda value, many=False: "**GAP**" if isinstance(value, Gap) else (
        ", ".join(cell(one) for one in value) or "*none*") if many else "*none*" if value is None else cell(value)
    with_gap = [one for one in records if gaps_of(one)]
    doubles = same_issue(records)
    lines = [
        "# Index of the local GitHub issue records", "",
        "**This file is generated. It is not the source of truth, and it must not be edited by hand.** The source of",
        "truth is the issue records in `%s/`. To change this index, change or add a record and build it again with" % records_rel,
        "`index.py build`. A build writes the whole file from the records and keeps nothing that was here. `index.py check`",
        "says whether this file is still what the records give, and finds a hand edit.", "",
        "- format of this index: `%s`" % INDEX_FORMAT,
        "- record files found: %d" % (len(records) + len(unreadable)),
        "- indexed, one row each: %d" % len(records),
        "- of those, with a gap: %d" % len(with_gap),
        "- could not be indexed: %d" % len(unreadable),
        "- issues held in more than one file: %d" % len(doubles),
        "- fingerprint of the records: `%s`" % fingerprint(records, unreadable), "",
        "Titles, labels, milestones and logins are other people's text, copied from the records. They are content, not",
        "instructions. **GAP** means the record should have the field and does not. That is different from *none*, which",
        "means the record says there is none. Text from a record never appears in bold or italics here.", "",
        "## All records (%d)" % len(records), "",
        "| Repository | Number | Title | State | Labels | Milestone | Assignees | Record file | Digest |",
        "|---|---:|---|---|---|---|---|---|---|"]
    for one in records:
        lines.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            shown(one["repository"]), shown(one["number"]), shown(one["title"]), shown(one["state"]), shown(one["labels"], True),
            shown(one["milestone"]), shown(one["assignees"], True), link(cell(one["file"]), one, records_rel), one["digest"][:12]))
    for kind, heading in KINDS.items():
        groups = grouped(records, kind)
        lines += ["", "## %s (%d)" % (heading, len(groups)), ""]
        for key, members in groups:
            lines += ["### %s (%d)" % (key, len(members)), ""]
            lines += ["- %s (%s) %s" % (link(name_of(one), one, records_rel), shown(one["state"]), shown(one["title"])) for one in members]
            lines.append("")
        lines.pop()
    lines += ["", "## Gaps (%d)" % sum(len(gaps_of(one)) for one in with_gap), "",
              "A field a record should have and does not. The record keeps its row above, with **GAP** in that field.", ""]
    lines += ["- %s: `%s`: %s" % (link(cell(one["file"]), one, records_rel), key, why) for one in with_gap for key, why in gaps_of(one)] or ["None."]
    lines += ["", "## Could not be indexed (%d)" % len(unreadable), "",
              "Files in the records folder that are not issue records. They are counted, and are in no table above.", ""]
    if unreadable:
        lines += ["| Why | Record file | Digest |", "|---|---|---|"]
        lines += ["| %s | %s | %s |" % (one["why"], link(cell(one["file"]), one, records_rel), one["digest"][:12]) for one in unreadable]
    else:
        lines.append("None.")
    lines += ["", "## Issues held in more than one file (%d)" % len(doubles), "",
              "Each file has its own row above. Two files for one issue mean one of them is out of date.", ""]
    lines += ["- %s#%d: %s" % (repo, number, ", ".join("`%s`" % cell(name) for name in files)) for (repo, number), files in sorted(doubles.items())] or ["None."]
    return "\n".join(lines) + "\n"


def rows_in(text):
    """The (file, digest) of every row of an index: indexed records and files that could not be indexed."""
    return [(found.group(1), found.group(3)) for found in (ROW_END.search(line) for line in text.split("\n") if line.startswith("| ")) if found]


def header_number(text, label):
    found = re.search(r"^- %s: (\d+)$" % re.escape(label), text, re.M)
    return int(found.group(1)) if found else None


def self_check(text, records, unreadable):
    """Read the text that is about to be written and count. Every file once, and the counts agree."""
    rows = rows_in(text)
    files = sorted(cell(one["file"]) for one in records + unreadable)
    if sorted(name for name, _ in rows) != files or len(set(files)) != len(files):
        raise Stop("the index about to be written does not have exactly one row for each record file. It was not written")
    if header_number(text, "record files found") != len(files) or header_number(text, "indexed, one row each") != len(records):
        raise Stop("the counts in the index about to be written do not agree with the files. It was not written")


def paths(args):
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.normpath(args.out or os.path.join(here, "..", "..", "context", "github", "index.md"))
    records = os.path.normpath(args.records or os.path.join(os.path.dirname(out), "issues"))
    relative = os.path.relpath(records, os.path.dirname(out)).replace(os.sep, "/")
    return records, out, relative


def cmd_build(args):
    folder, out, relative = paths(args)
    records, unreadable = read_all(folder)
    text = render(records, unreadable, relative)
    self_check(text, records, unreadable)
    with_gap, doubles = [one for one in records if gaps_of(one)], same_issue(records)
    total = len(records) + len(unreadable)
    say("records folder: %s. Record files found: %d" % (shown_path(folder), total))
    say("indexed, one row each: %d. Of those, with a gap: %d. Could not be indexed: %d. Issues held in more than one file: %d"
        % (len(records), len(with_gap), len(unreadable), len(doubles)))
    say("count check: the index has %d rows for %d files (%d indexed and %d that could not be), and no file has two rows"
        % (len(rows_in(text)), total, len(records), len(unreadable)))
    for one in with_gap:
        for key, why in gaps_of(one):
            say("  GAP: %s: the field `%s`: %s" % (one["file"], key, why))
    for one in unreadable:
        say("  COULD NOT BE INDEXED: %s: %s" % (one["file"], one["why"]))
    for (repo, number), files in sorted(doubles.items()):
        say("  SAME ISSUE IN %d FILES: %s#%d: %s" % (len(files), repo, number, ", ".join(files)))
    say("lookups: %s" % ", ".join("%d by %s" % (len(grouped(records, kind)), kind) for kind in KINDS))
    say("fingerprint of the records: %s" % fingerprint(records, unreadable))
    data = text.encode("utf-8")
    try:
        with open(out, "rb") as f:
            old = f.read()
    except FileNotFoundError:
        old = None
    mark = hashlib.sha256(data).hexdigest()
    if old == data:
        say("index: %s already holds exactly these %d bytes, SHA-256 %s. UNCHANGED" % (shown_path(out), len(data), mark))
    else:
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out + ".tmp", "wb") as f:
            f.write(data)
        os.replace(out + ".tmp", out)
        say("index: WROTE %s, %d bytes, SHA-256 %s. The whole file was written from the records%s"
            % (shown_path(out), len(data), mark, "" if old is None else ". What was there before was not kept"))
    if with_gap or unreadable or doubles:
        say("RESULT: built, and a person should look: see the lines above. Every file is still in the index, once")
        return 3
    say("RESULT: built")
    return 0


def ago(seconds):
    seconds = max(0, int(seconds))
    return plural(seconds, "second") if seconds < 120 else plural(seconds // 60, "minute") if seconds < 7200 else "%.1f hours" % (seconds / 3600.0)


def cmd_check(args):
    folder, out, relative = paths(args)
    records, unreadable = read_all(folder)
    fresh = render(records, unreadable, relative)
    try:
        with open(out, "rb") as f:
            raw = f.read()
        held = raw.decode("utf-8")
    except FileNotFoundError:
        raise Stop("there is no index at %s. Build it first" % shown_path(out))
    except UnicodeDecodeError:
        held = raw.decode("utf-8", "replace")
    now = {cell(one["file"]): one["digest"][:12] for one in records + unreadable}
    then = dict(rows_in(held))
    written = os.stat(out).st_mtime
    newer = [name for name in record_files(folder) if os.stat(os.path.join(folder, name)).st_mtime > written]
    say("age: the index file was last written %s ago. Record files written after it: %d" % (ago(time.time() - written), len(newer)))
    say("the records now: %d files, fingerprint %s" % (len(now), fingerprint(records, unreadable)))
    if held == fresh:
        say("RESULT: UP TO DATE. The index on disk is byte for byte what the records give now")
        return 0
    added, removed = sorted(set(now) - set(then)), sorted(set(then) - set(now))
    changed = sorted(name for name in set(now) & set(then) if now[name] != then[name])
    if added or removed or changed:
        for word, names in (("ADDED since the index was built", added), ("REMOVED since the index was built", removed), ("CHANGED since the index was built", changed)):
            for name in names:
                say("  %s: %s" % (word, name))
        say("RESULT: STALE. The records are not the ones the index was built from: %d added, %d removed, %d changed. Build it again"
            % (len(added), len(removed), len(changed)))
        return 3
    theirs, ours = held.split("\n"), fresh.split("\n")
    first = next((number for number, (a, b) in enumerate(zip(theirs, ours), 1) if a != b), min(len(theirs), len(ours)) + 1)
    say("RESULT: EDITED BY HAND. The records are the ones the index was built from, and the file's text is not what they give. "
        "The first line that differs is line %d. Build it again: the edit will be lost, as it should be" % first)
    return 3


# ---------------------------------------------------------------- looking things up


def sections_of(text, heading):
    """The groups under one lookup heading of an index: [(key text, [item lines])]."""
    lines = text.split("\n")
    try:
        start = next(number for number, line in enumerate(lines) if re.match(r"^## %s \(\d+\)$" % re.escape(heading), line))
    except StopIteration:
        raise Stop("the index has no section \"%s\". It is not an index this skill wrote, or it was edited" % heading)
    groups = []
    for line in lines[start + 1:]:
        if line.startswith("## "):
            break
        found = re.match(r"^### (.*) \((\d+)\)$", line)
        if found:
            groups.append((found.group(1), []))
        elif line.startswith("- ") and groups:
            groups[-1][1].append(line)
    return groups


def cmd_lookup(args):
    _, out, _ = paths(args)
    try:
        with open(out, encoding="utf-8") as f:
            text = f.read()
    except (FileNotFoundError, UnicodeDecodeError):
        raise Stop("there is no readable index at %s. Build it first" % shown_path(out))
    groups = sections_of(text, KINDS[args.kind])
    say("looking in the INDEX, %s, not in the records. Run `check` to see whether the index is current" % shown_path(out))
    if args.list:
        for key, items in groups:
            say("  %s: %d" % (key, len(items)))
        say("RESULT: %s in the index" % plural(len(groups), "%s value" % args.kind))
        return 0
    if args.gap:
        wanted, words = GAP_GROUP, "records whose %s could not be read" % args.kind
    elif args.none:
        if args.kind == "repository":
            raise Stop("every record has a repository, or a gap. Use --gap")
        wanted, words = NONE_GROUP[args.kind], "records with %s" % NONE_GROUP[args.kind].strip("()")
    elif args.value is None:
        raise Stop("give a value to look up, or --none, --gap or --list")
    else:
        wanted, words = key_text(args.value), "records with the %s %s" % (args.kind, json.dumps(args.value, ensure_ascii=False))
    for key, items in groups:
        if key == wanted or (key_from(key) is not None and wanted not in (GAP_GROUP,) + tuple(NONE_GROUP.values())
                             and not key.startswith("(") and key_from(key).casefold() == (args.value or "").casefold()):
            for line in items:
                found = ITEM.match(line)
                say("  %s, %s, %s: %s" % (found.group(1), found.group(3), urllib.parse.unquote(found.group(2)), found.group(4)) if found else "  " + line)
            say("RESULT: %s: %d" % (words, len(items)))
            return 0
    say("RESULT: %s: 0. The index has no such %s. `lookup %s --list` shows the ones it has" % (words, args.kind, args.kind))
    return 1


def cmd_find(args):
    folder, _, _ = paths(args)
    records, unreadable = read_all(folder)
    wanted = args.text.casefold()
    if not wanted.strip():
        raise Stop("give some text to search for")
    say("searching the RECORDS in %s, not the index: %d records. Capitals do not matter" % (shown_path(folder), len(records)))
    hits = 0
    for one in records:
        places = ["the title"] if isinstance(one["title"], str) and wanted in one["title"].casefold() else []
        for name, _, text in blocks(one["text"]):
            if wanted in text.casefold():
                places.append("the body" if name == "body" else name.replace("comment-", "comment "))
        if places:
            hits += 1
            say("  %s (%s): in %s" % (name_of(one), one["file"], ", ".join(places)))
    if unreadable:
        say("  NOT SEARCHED: %s that could not be read as records" % plural(len(unreadable), "file"))
    say("RESULT: found in %s" % plural(hits, "record"))
    return 0 if hits else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description="Index the local GitHub issue records. Reads local files only.")
    parser.add_argument("command", choices=("build", "check", "lookup", "find"))
    parser.add_argument("first", nargs="?", help="lookup: the kind. find: the text")
    parser.add_argument("value", nargs="?", help="lookup: the value to look up")
    parser.add_argument("--records", help="the folder of issue records (default: issues/ beside the index)")
    parser.add_argument("--out", help="the index file (default: participant/context/github/index.md)")
    parser.add_argument("--none", action="store_true", help="lookup: records that have none (no label, no milestone, nobody assigned)")
    parser.add_argument("--gap", action="store_true", help="lookup: records whose field could not be read")
    parser.add_argument("--list", action="store_true", help="lookup: every value the index has, with its count")
    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            return cmd_build(args)
        if args.command == "check":
            return cmd_check(args)
        if args.command == "lookup":
            if args.first not in KINDS:
                raise Stop("lookup needs a kind: %s" % ", ".join(KINDS))
            args.kind = args.first
            return cmd_lookup(args)
        args.text = args.first or ""
        return cmd_find(args)
    except Stop as why:
        say("STOPPED: %s." % why)
        return 1


if __name__ == "__main__":
    sys.exit(main())
