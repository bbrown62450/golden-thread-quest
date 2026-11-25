#!/usr/bin/env python3
"""Compares two snapshots of one sprint and reports the change of scope. It reads and writes local files only.

    python3 participant/skills/scrum-scope-change/scope.py compare --snapshots FILE [--start NAME] [--later NAME] --out FILE
    python3 participant/skills/scrum-scope-change/scope.py check   --snapshots FILE [--start NAME] [--later NAME] --report FILE

    --snapshots  a file holding the snapshots, in the form participant/skills/scrum-scope-change/make_snapshots.py writes
    --start      the name of the snapshot taken at sprint start. Default: start
    --later      the name of the one to compare with it. Default: later. Give "start" to compare the start with itself
    --out        the report to write

ITEMS ARE MATCHED BY IDENTIFIER AND BY NOTHING ELSE. A title is never compared to find an item.

WHAT COUNTS. Three fields are the commitment: `estimate`, `scope` and `acceptance`. A difference in one of them is
MATERIAL, once a little formatting is set aside. Three fields are not: `title`, `description` and `assignee`. A
difference in one of those is NOISE. The rules are in SKILL.md, beside this file.

The program cannot tell a criterion that was reworded from one whose meaning changed. Both are reported as material,
with both versions, and the report says a person should read them. When it is unsure it reports, and does not stay
silent: very little is set aside as formatting, so some changes that are only formatting are reported as material.

The report names its snapshots by the checksum of the file and not by its path, and the computer's clock is never
read. So the same file gives the same bytes, wherever it is and whenever it is run.

`check` reads a finished report back and compares it with the snapshots. It reads them with this program's own code,
so a fault in that reading is invisible to it.
Exit code 0: done, or no problem found. 1: nothing could be compared, or problems, each printed. 2: the file could not
be read. It imports nothing that can reach a network.
"""
import argparse
import hashlib
import os
import re
import sys
import unicodedata
from decimal import Decimal

ID = re.compile(r"^[A-Z][A-Z0-9]*-[0-9]+$")
ID_AT_START = re.compile(r"^[A-Z][A-Z0-9]*-[0-9]+")
NUMBER = re.compile(r"^[0-9]{1,9}(\.[0-9]{1,3})?$")
PLAIN = ("title", "description", "assignee", "estimate", "changed_by")
LISTS = ("scope", "acceptance")
NOISE = ("title", "description", "assignee")
HEADER = ("sprint_start", "sprint_end", "capacity_points", "product_owner")
UNPRINTABLE = re.compile("[\\x00-\\x1f\\x7f-\\x9f\\u00ad\\u061c\\u200b-\\u200f\\u2028\\u2029\\u202a-\\u202e\\u2066-\\u2069\\ufeff]")
QUOTES = re.compile("[\\u00ab\\u00bb\\u2018-\\u201f\\u2032\\u2033\\u2039\\u203a\\u02ba\\u275d\\u275e\\u301d-\\u301f\\uff02\\uff07]")
DASHES = re.compile("[\\u2010-\\u2015\\u2212]")
BULLET = re.compile("^[-*+\\u2022]\\s+")
NUMBERED = re.compile(r"^([0-9]{1,4})[.)]\s+")
DOUBLE_QUOTES = re.compile("[\u00ab\u00bb\u201c-\u201f\uff02]")
SINGLE_QUOTES = re.compile("[\u2018-\u201b\u2039\u203a\uff07]")
INVISIBLE = re.compile("[\u00ad\u200b-\u200f\u202a-\u202e\u2066-\u2069\ufeff]")
WHY = {"estimate": "the estimate is the size of the commitment",
       "scope": "the scope list is what is to be built",
       "acceptance": "the acceptance criteria are what done means"}
SAID = {"title": "A title is a name for the item. The identifier is the same, so it is the same item.",
        "description": "A description is not read for scope. If it asks for work that the scope list does not, a person has to see that here.",
        "assignee": "Who does the work is not what was committed to.",
        "estimate": "The same number, written differently."}
LIMIT = 400


def read_bytes(path):
    with open(path, "rb") as f:
        return f.read()


def write(path, text):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def safe(text):
    """Other people's text made fit to print inside double quotes on one line. It is never read for meaning."""
    out = QUOTES.sub("'", UNPRINTABLE.sub(" ", str(text)))
    for bad, good in (("`", "'"), ('"', "'"), ("|", "/"), ("<", "(less than)"), (">", "(more than)"), ("[", "("), ("]", ")"), ("*", "(star)"), ("#", "(hash)")):
        out = out.replace(bad, good)
    return out if len(out) <= LIMIT else out[:LIMIT - 3] + "..."


def pair(was, now):
    """Two versions, each quoted. Says so when the quotations cannot show how they differ."""
    a, b = safe(was), safe(now)
    return "\"%s\" at start, \"%s\" later.%s" % (a, b, " The two differ beyond what is printed here: they are cut at %d characters, or differ in a character that cannot be shown." % LIMIT if a == b else "")


def plain(entry):
    """A list entry with a little formatting set aside: capitals, runs of spaces, the kind of quote mark or dash,
    characters that cannot be seen, and one full stop, comma or semicolon at the very end. Everything else is kept."""
    text = " ".join(unicodedata.normalize("NFC", entry).split())
    text = DASHES.sub("-", SINGLE_QUOTES.sub("'", DOUBLE_QUOTES.sub('"', INVISIBLE.sub("", text))))
    if text[-1:] in (".", ";", ",") and text[-2:-1] not in (".", ";", ","):
        text = text[:-1].rstrip()
    return text.casefold()


def number(text):
    return Decimal(text) if isinstance(text, str) and NUMBER.match(text) else None


def points(value):
    text = format(Decimal(value).normalize(), "f")
    return "0" if text in ("-0", "") else text


def signed(value):
    return ("+" if value > 0 else "-" if value < 0 else "") + points(abs(value))


def entries_of(lines):
    """The entries of a list: the bullet goes from each, and the numbering goes only when there are two entries or more and it runs 1, 2, 3 down the list."""
    out = [BULLET.sub("", line.strip()) for line in lines]
    numbers = [NUMBERED.match(entry) for entry in out]
    if len(out) > 1 and all(numbers) and [int(m.group(1)) for m in numbers] == list(range(1, len(out) + 1)):
        out = [NUMBERED.sub("", entry) for entry in out]
    return out


def parse(text):
    """The file into its header, its snapshots and what could not be read."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    file_trouble, header, doubled_header = [], {}, set()
    parts = re.split(r"^## ", text, flags=re.M)
    headed = [(p.split("\n", 1)[0].strip(), p.split("\n", 1)[1] if "\n" in p else "") for p in parts[1:]]
    sprint = [body for heading, body in headed if heading == "The sprint"]
    if len(sprint) > 1:
        file_trouble.append(("the file", "The sprint", "it has %d sections headed The sprint. No header line is read" % len(sprint)))
    for name, value in re.findall(r"^[ \t]*[-*][ \t]*(\w+)[ \t]*:[ \t]*(.*)$", sprint[0] if len(sprint) == 1 else "", re.M):
        name = name.lower()
        if name not in HEADER:
            continue
        if name in header or name in doubled_header:
            if name not in doubled_header:
                file_trouble.append(("the file", name, "it is recorded more than once in the header. Neither value is used"))
            doubled_header.add(name)
            header.pop(name, None)
        else:
            header[name] = value.strip()
    snapshots, names_twice, orphans, cut_off, last_snapshot = {}, set(), set(), set(), None
    for heading, body in headed:
        if not heading.startswith("Snapshot: ") or not heading[len("Snapshot: "):].strip():
            if re.match(r"(?i)^snapshot\b", heading):
                file_trouble.append(("the file", "a heading", "\"%s\" looks like a snapshot's heading and is not one: it must read \"Snapshot: \" and a name. What is under it is not read" % safe(heading)))
            elif heading != "The sprint" and last_snapshot and not re.search(r"^### ", body, re.M) and re.search(r"^(?:[ \t]+\S|- \w+:)", body, re.M):
                file_trouble.append(("the file", "a heading", "the heading \"%s\" follows snapshot \"%s\" and has lines under it that read like part of an item. They are not read" % (safe(heading), safe(last_snapshot))))
                cut_off.add(last_snapshot)
            elif heading != "The sprint" and re.search(r"^### ", body, re.M):
                file_trouble.append(("the file", "a heading", "items are written under \"%s\", which is not a snapshot. They are not read, and are in neither snapshot" % safe(heading)))
                orphans.update(m.group(0) for m in (ID_AT_START.match(line[4:].strip()) for line in body.split("\n") if line.startswith("### ")) if m)
            last_snapshot = None if heading == "The sprint" else last_snapshot
            continue
        name = heading[len("Snapshot: "):].strip()
        last_snapshot = name
        if name in snapshots or name in names_twice:
            names_twice.add(name)
            snapshots.pop(name, None)
            continue
        trouble = []
        blocks = re.split(r"^### ", body, flags=re.M)
        taken = re.findall(r"^- taken:[ \t]*(.*)$", blocks[0], re.M)
        if len(taken) > 1:
            trouble.append(("snapshot \"%s\"" % safe(name), "taken", "it is given more than once. Neither is used"))
        for line in blocks[0].split("\n"):
            if line.strip() and not re.match(r"^- taken:", line):
                trouble.append(("snapshot \"%s\"" % safe(name), "a line", "a line before its first item is not read: \"%s\"" % safe(line.strip())))
        items, seen, spoiled, unnamed = {}, {}, set(), 0
        for block in blocks[1:]:
            lines = block.split("\n")
            identity = lines[0].strip()
            if not ID.match(identity):
                inside = ID_AT_START.match(identity)
                if inside:
                    spoiled.add(inside.group(0))
                else:
                    unnamed += 1
                trouble.append(("snapshot \"%s\"" % safe(name), "an item's heading", "\"%s\" is not an identifier and nothing else. The item under it is not read" % safe(identity)))
                continue
            seen[identity] = seen.get(identity, 0) + 1
            one = {"id": identity, "unread": [], "repeated": [], "raw": {}, "block": [line.rstrip() for line in lines[1:] if line.strip()]}
            current = None
            for line in lines[1:]:
                if not line.strip():
                    continue
                field = re.match(r"^- (\w+):(?:[ \t]+(.*))?$", line)
                if field and field.group(1) in PLAIN + LISTS:
                    key, value = field.group(1), (field.group(2) or "").strip()
                    if key in one:
                        one["repeated"].append(key)
                    if key in LISTS:
                        current = key
                        one["raw"][key] = []
                        one[key] = [] if not value else None
                    else:
                        current = None
                        one[key] = value
                elif current and one.get(current) is not None and line[:1] in (" ", "\t"):
                    one["raw"][current].append(line)
                else:
                    current = None
                    one["unread"].append(line.strip())
            for key in LISTS:
                if one.get(key) is not None:
                    one[key] = entries_of(one["raw"][key])
            items[identity] = one
        for identity in sorted(i for i, count in seen.items() if count > 1):
            trouble.append(("snapshot \"%s\"" % safe(name), identity, "%d items have this identifier. None of them is used" % seen[identity]))
            del items[identity]
            spoiled.add(identity)
        snapshots[name] = {"taken": taken[0].strip() if len(taken) == 1 and taken[0].strip() else None, "items": items, "spoiled": spoiled, "unnamed": unnamed, "trouble": trouble}
    return {"header": header, "doubled_header": doubled_header, "snapshots": snapshots, "names_twice": names_twice, "orphans": orphans, "cut_off": cut_off, "trouble": file_trouble, "front": parts[0]}


def multiset(entries):
    out = {}
    for entry in entries:
        out[plain(entry)] = out.get(plain(entry), 0) + 1
    return out


def beyond(mine, theirs):
    """The entries of `mine` that `theirs` does not have, counting an entry given twice as two."""
    left, out = dict(multiset(theirs)), []
    for entry in mine:
        if left.get(plain(entry), 0) > 0:
            left[plain(entry)] -= 1
        else:
            out.append(entry)
    return out


def build(text, start_name="start", later_name="later"):
    """Works the comparison out. Returns the model the report is written from."""
    read_in = parse(text)
    gaps = []

    def gap(what, field, reason, effect):
        gaps.append({"what": what, "field": field, "reason": reason, "effect": effect})

    for what, field, reason in read_in["trouble"]:
        gap(what, field, reason, "whatever it would have held is in no list and no figure")
    missing = []
    for name in dict.fromkeys((start_name, later_name)):
        if name in read_in["names_twice"]:
            gap("the file", "a snapshot's name", "there are two snapshots named \"%s\". Neither is used" % safe(name), "nothing can be compared")
            missing.append(name)
        elif name not in read_in["snapshots"]:
            gap("the file", "a snapshot's name", "there is no snapshot named \"%s\"" % safe(name), "nothing can be compared")
            missing.append(name)
    empty = {"taken": None, "items": {}, "spoiled": set(), "unnamed": 0, "trouble": []}
    start, later = read_in["snapshots"].get(start_name, empty), read_in["snapshots"].get(later_name, empty)
    comparable = not missing
    same_one = later_name == start_name

    def usable(side, name):
        """The items of one snapshot, each with its estimate as a number or None, its two lists or None, and whether a line of it went unread."""
        for what, field, reason in side["trouble"]:
            gap(what, field, reason, "whatever it would have held is in no list and no figure")
        out = {}
        for identity, one in side["items"].items():
            for line in one["unread"]:
                gap(identity, "a line", "in the %s snapshot a line of it is not read: \"%s\"" % (name, safe(line)), "the item is not called unchanged or noise, since what the line held is not known")
            for key in dict.fromkeys(one["repeated"]):
                gap(identity, key, "in the %s snapshot it is given more than once. The last is used" % name, "the item is not called unchanged or noise")
            estimate = number(one.get("estimate"))
            if estimate is None:
                said = one.get("estimate")
                gap(identity, "estimate", "in the %s snapshot %s" % (name, "it is not given" if said is None else "it is blank" if said == "" else "it is \"%s\", which is not a number this program takes" % safe(said)),
                    "the item is in no figure of section 1 or of section 8")
            for key in LISTS:
                if one.get(key) is None:
                    gap(identity, key, "in the %s snapshot it is %s" % (name, "not given" if key not in one else "written on the field's own line, and not as entries on the lines under it"), "whether it differs cannot be told")
                elif not one[key]:
                    gap(identity, key, "in the %s snapshot it has no entries" % name, "it is compared as an empty list. If the other snapshot's is empty too, whether it differs cannot be told")
            out[identity] = dict(one, number=estimate, doubt=bool(one["unread"] or one["repeated"]))
        if name in read_in["cut_off"] and out:
            last = list(side["items"])[-1]
            out[last]["doubt"] = True
        return out

    a = usable(start, start_name) if comparable else {}
    b = a if same_one else (usable(later, later_name) if comparable else {})
    spoiled = set(start["spoiled"]) | set(later["spoiled"]) | read_in["orphans"]
    for identity in sorted(i for i in (set(a) ^ set(b)) if i in spoiled):
        gap(identity, "the item", "it can be used in one snapshot and not in the other, where its heading is given twice, cannot be read, or is under a heading that is not a snapshot", "it is not reported as added or as removed, and is in no figure")
    added = sorted(i for i in b if i not in a and i not in spoiled)
    removed = sorted(i for i in a if i not in b and i not in spoiled)
    material, noise, undecided, unchanged = [], [], [], []
    for identity in sorted(set(a) & set(b)):
        was, now = a[identity], b[identity]
        differs, also, untold = [], [], []
        if was["block"] == now["block"] and was["doubt"] == now["doubt"]:   # the same lines, letter for letter: nothing differs, whatever could not be read
            unchanged.append({"id": identity, "differs": [], "also": [], "untold": [], "changed_by": now.get("changed_by") or None})
            continue
        if was["number"] is None or now["number"] is None:
            untold.append("estimate")
        elif was["number"] != now["number"]:
            differs.append({"field": "estimate", "was": was["number"], "now": now["number"]})
        elif was.get("estimate") != now.get("estimate"):
            also.append({"field": "estimate", "was": was.get("estimate"), "now": now.get("estimate")})
        for key in LISTS:
            if was.get(key) is None or now.get(key) is None or (not was[key] and not now[key]):
                untold.append(key)
            elif multiset(was[key]) != multiset(now[key]):
                differs.append({"field": key, "gone": beyond(was[key], now[key]), "came": beyond(now[key], was[key])})
            elif was["raw"][key] != now["raw"][key]:
                also.append({"field": key, "was": [line.strip() for line in was["raw"][key]], "now": [line.strip() for line in now["raw"][key]]})
        for key in NOISE:
            if (was.get(key) or "") != (now.get(key) or ""):
                also.append({"field": key, "was": was.get(key) or "", "now": now.get(key) or ""})
        if was["doubt"] or now["doubt"]:
            untold.append("a line that was not read, or a field given twice")
        entry = {"id": identity, "differs": differs, "also": also, "untold": untold, "changed_by": now.get("changed_by") or None}
        (material if differs else undecided if untold else noise if also else unchanged).append(entry)

    # An item is in the figures only if its estimate can be used wherever the item is. So the parts always add up.
    out_of_figures = sorted(i for i in set(a) | set(b) if (i in a and (a[i]["number"] is None or a[i]["doubt"])) or (i in b and (b[i]["number"] is None or b[i]["doubt"])) or (i in spoiled and (i in a) != (i in b)))
    counted = lambda side: {i: one for i, one in side.items() if i not in out_of_figures}  # noqa: E731
    start_total = sum((one["number"] for one in counted(a).values()), Decimal(0))
    later_total = sum((one["number"] for one in counted(b).values()), Decimal(0))
    added_sum = sum((b[i]["number"] for i in added if i not in out_of_figures), Decimal(0))
    removed_sum = sum((a[i]["number"] for i in removed if i not in out_of_figures), Decimal(0))
    reest = [(m["id"], d["was"], d["now"]) for m in material for d in m["differs"] if d["field"] == "estimate" and m["id"] not in out_of_figures]
    reest_sum = sum((now - was for _, was, now in reest), Decimal(0))
    adds_up = start_total + added_sum - removed_sum + reest_sum == later_total
    capacity = number(read_in["header"].get("capacity_points"))
    if "capacity_points" in read_in["header"] and capacity is None:
        gap("the file", "capacity_points", "it is \"%s\", which is not a number this program takes" % safe(read_in["header"]["capacity_points"]), "nothing is said of capacity")
    return {"read": read_in, "gaps": gaps, "a": a, "b": b, "start": start, "later": later, "start_name": start_name, "later_name": later_name,
            "added": added, "removed": removed, "material": material, "noise": noise, "undecided": undecided, "unchanged": unchanged,
            "start_total": start_total, "later_total": later_total, "added_sum": added_sum, "removed_sum": removed_sum, "reest": reest, "reest_sum": reest_sum,
            "adds_up": adds_up, "out_of_figures": out_of_figures, "counted_start": len(counted(a)), "counted_later": len(counted(b)),
            "capacity": capacity, "owner": read_in["header"].get("product_owner") or None, "owner_twice": "product_owner" in read_in["doubled_header"],
            "comparable": comparable, "unnamed": (start["unnamed"], later["unnamed"]),
            "nothing": comparable and not (added or removed or material or noise or undecided)}


def render(model, sha):
    a, b = model["a"], model["b"]
    listed = lambda ids: ", ".join("`%s`" % i for i in ids) or "none"  # noqa: E731
    quoted = lambda entries: ", ".join("\"%s\"" % safe(e) for e in entries) or "none"  # noqa: E731
    est = lambda side, i: ("%s points" % points(side[i]["number"])) if side[i]["number"] is not None else "an estimate that cannot be used"  # noqa: E731
    taken = lambda side: "taken \"%s\"" % safe(side["taken"]) if side["taken"] else "with no day recorded"  # noqa: E731
    items = lambda n: "%d item%s" % (n, "" if n == 1 else "s")  # noqa: E731
    net = model["later_total"] - model["start_total"]
    moved = model["added_sum"] + model["removed_sum"] + sum((abs(now - was) for _, was, now in model["reest"]), Decimal(0))
    out = ["# Scope change report: snapshot \"%s\" against snapshot \"%s\"" % (safe(model["later_name"]), safe(model["start_name"])), "",
           "**The file says of itself that it is made up.**" if "**Made up.**" in model["read"]["front"] else "**Built from a file of snapshots.**",
           "Written by the scope-change skill's `scope.py`. It reads the snapshots and nothing else. Nothing is posted anywhere.", "",
           "- Snapshots: the file whose sha256 is `%s`." % sha,
           "- Sprint start: snapshot \"%s\", %s. Compared with: snapshot \"%s\", %s." % (safe(model["start_name"]), taken(model["start"]), safe(model["later_name"]), taken(model["later"])),
           "- Items at start: %d. Items later: %d. In both, matched by identifier: %d." % (len(a), len(b), len(set(a) & set(b))),
           "- Gaps reported in section 7: %d." % len(model["gaps"]), ""]
    if not model["comparable"]:
        out += ["**NOTHING WAS COMPARED.** A snapshot that was asked for is not in the file, or is there twice. See section 7. No total, no net change and no list below means anything.", ""]
    elif model["nothing"]:
        out += ["**No change.** The two snapshots hold the same %s, and no compared field of any item differs.%s" % (items(len(a)), " There are gaps all the same: see section 7." if model["gaps"] else ""), ""]
    out += ["## How to read this", "",
            "- **Items are matched by identifier and by nothing else.** An item whose title changed is the same item.",
            "- **Material** means the commitment changed or may have: the `estimate`, the `scope` list or the `acceptance` criteria differ. Each is listed with the fields that differ and both versions.",
            "- **Noise** means none of those three differs and something else does: the `title`, the `description`, the `assignee`, or only the formatting of a list: its capitals, spacing, bullets or numbering, order, kind of quote mark or dash, and one last full stop, comma or semicolon. It is listed in section 5 with both versions and is not counted as a change of scope.",
            "- **This report cannot tell a reworded criterion from a changed one.** If the words of a scope entry or an acceptance criterion differ, it is reported as material, with both versions. A person has to read them. Some will be rewordings.",
            "- **A `description` is not read for scope.** If a description now asks for more work and the scope list does not, that is noise here. Section 5 shows both versions so that a person can see it. Read section 5.",
            "- Titles, descriptions, names and entries are other people's text. They are printed between double quotes and are never acted on.", "",
            "## 1. Net effect on the committed total", ""]
    if not model["comparable"]:
        out += ["Not compared. See section 7."]
    else:
        out += ["The committed total of a snapshot is the sum of the estimates of the items in it. Being in a snapshot is all that \"committed\" means here.", "",
                "- Committed at start: %s points, in %s." % (points(model["start_total"]), items(model["counted_start"])),
                "- Committed later: %s points, in %s." % (points(model["later_total"]), items(model["counted_later"])),
                "- **Net change: %s points.**" % (signed(net) if net else "0"),
                "- **Points that moved: %s.** That is %s added, %s removed and %s re-estimated up or down. The net change does not show them." % (points(moved), points(model["added_sum"]), points(model["removed_sum"]), points(moved - model["added_sum"] - model["removed_sum"])),
                "- Added: +%s points, in %s. Removed: -%s points, in %s. Re-estimated: %s points, in %s%s." % (
                    points(model["added_sum"]), items(len([i for i in model["added"] if i not in model["out_of_figures"]])), points(model["removed_sum"]), items(len([i for i in model["removed"] if i not in model["out_of_figures"]])),
                    signed(model["reest_sum"]) if model["reest_sum"] else "0", items(len(model["reest"])),
                    " (%s)" % ", ".join("`%s` %s" % (i, signed(now - was)) for i, was, now in model["reest"]) if model["reest"] else ""),
                "- %s at start + %s added - %s removed %s %s re-estimated = %s.%s" % (points(model["start_total"]), points(model["added_sum"]), points(model["removed_sum"]), "-" if model["reest_sum"] < 0 else "+", points(abs(model["reest_sum"])),
                                                                                   points(model["start_total"] + model["added_sum"] - model["removed_sum"] + model["reest_sum"]), "" if model["adds_up"] else " THIS IS NOT THE LATER TOTAL. The program is at fault.")]
        if model["out_of_figures"]:
            out.append("- **NOT COMPLETE.** These items are in no figure above, at start or later, because an estimate, a line or a heading of theirs cannot be used: %s. See section 7." % listed(model["out_of_figures"]))
        if sum(model["unnamed"]):
            out.append("- **NOT COMPLETE.** %d item heading%s could not be read, so an item counted above as added or as removed may be one of those. See section 7." % (sum(model["unnamed"]), "" if sum(model["unnamed"]) == 1 else "s"))
    caveat = lambda n, where: [] if not n else ["%d item heading%s in the %s snapshot could not be read. An item listed here may be one of those under another heading." % (n, "" if n == 1 else "s", where), ""]  # noqa: E731
    out += ["", "## 2. Added (%d)" % len(model["added"]), "", "In the later snapshot only.", ""] + caveat(model["unnamed"][0], "start")
    out += ["- `%s`: %s. \"%s\"" % (i, est(b, i), safe(b[i].get("title") or "")) for i in model["added"]] or ["None."]
    out += ["", "## 3. Removed (%d)" % len(model["removed"]), "", "In the start snapshot only. Who removed an item, and why, is in neither snapshot.", ""] + caveat(model["unnamed"][1], "later")
    out += ["- `%s`: %s. \"%s\"" % (i, est(a, i), safe(a[i].get("title") or "")) for i in model["removed"]] or ["None."]

    def also_lines(entry):
        lines = []
        for x in entry["also"]:
            if x["field"] in LISTS:
                lines.append("  - `%s`: the same entries, once formatting and order are set aside. At start: %s. Later: %s." % (x["field"], quoted(x["was"]), quoted(x["now"])))
            else:
                lines.append("  - `%s`: %s %s" % (x["field"], pair(x["was"], x["now"]), SAID[x["field"]]))
        return lines
    out += ["", "## 4. Materially changed (%d)" % len(model["material"]), "", "In both snapshots, and the `estimate`, the `scope` list or the `acceptance` criteria differ.", ""]
    for m in model["material"]:
        out.append("- `%s`: fields that differ: %s." % (m["id"], ", ".join("`%s`" % d["field"] for d in m["differs"])))
        for d in m["differs"]:
            if d["field"] == "estimate":
                out.append("  - `estimate`: %s at start, %s later. %s points. It counts because %s." % (points(d["was"]), points(d["now"]), signed(d["now"] - d["was"]), WHY["estimate"]))
            else:
                both = bool(d["gone"]) and bool(d["came"])
                out.append("  - `%s`: at start only: %s. Later only: %s. It counts because %s.%s%s" % (d["field"], quoted(d["gone"]), quoted(d["came"]), WHY[d["field"]],
                           " Entries went and entries came, so this may be a rewording or a change of meaning. This report cannot tell which. A person should read both." if both else "",
                           " The two differ beyond what is printed here: they are cut at %d characters, or differ in a character that cannot be shown." % LIMIT if both and quoted(d["gone"]) == quoted(d["came"]) else ""))
        if m["untold"]:
            out.append("  - Cannot be told: %s. See section 7." % ", ".join(m["untold"]))
        if m["also"]:
            out.append("  - Also differs, and is not counted:")
            out += ["  " + line for line in also_lines(m)]
    if not model["material"]:
        out.append("None.")
    out += ["", "## 5. Noise: differs, and not counted as a change of scope (%d)" % len(model["noise"]), "",
            "In both snapshots. The `estimate` is the same number, the `scope` list and the `acceptance` criteria hold the same entries once formatting and order are set aside, and something else differs.",
            "**That is a statement about three fields. It is not a statement that no work was added.** Read the versions below.", ""]
    for n in model["noise"]:
        out.append("- `%s`: fields that differ: %s." % (n["id"], ", ".join("`%s`" % x["field"] for x in n["also"])))
        out += also_lines(n)
    if not model["noise"]:
        out.append("None.")
    out += ["", "## 6. Unchanged (%d)" % len(model["unchanged"]), "", "No compared field differs. `changed_by` is not a compared field.", "", "- %s." % listed([u["id"] for u in model["unchanged"]]),
            "", "## 7. Gaps: what the snapshots do not support", "",
            "Each is something that is missing or cannot be used. Nothing below was guessed or filled in. Entries: %d." % len(model["gaps"]), ""]
    out += ["- [GAP] `%s`, `%s`: %s. Effect: %s." % (g["what"], g["field"], g["reason"], g["effect"]) for g in model["gaps"]] or ["None."]
    out += ["", "- In both snapshots, with nothing material seen to differ and something that cannot be compared (%d): %s. Neither material, nor noise, nor unchanged." % (len(model["undecided"]), listed([u["id"] for u in model["undecided"]]))]
    for u in model["undecided"]:
        if u["also"]:
            out.append("  - `%s` also differs in what is not counted:" % u["id"])
            out += ["  " + line for line in also_lines(u)]
    out += ["", "## 8. Capacity not yet committed", ""]
    if not model["comparable"]:
        out += ["Not compared. See section 7."]
    elif model["capacity"] is None:
        out += ["The file records no `capacity_points` that can be used, so nothing is said of capacity."]
    else:
        cap = model["capacity"]
        out += ["From `capacity_points`, which the file records as %s. This is that figure less the committed total. **It takes no account of work done or of days gone.**" % points(cap), "",
                "- Uncommitted at start: %s points. Uncommitted later: %s points." % (points(cap - model["start_total"]), points(cap - model["later_total"]))]
        out += ["- `%s` added: %s." % (i, "%s points of uncommitted capacity" % signed(-b[i]["number"]) if i not in model["out_of_figures"] else "it is in no figure") for i in model["added"]]
        out += ["- `%s` removed: %s." % (i, "%s points of uncommitted capacity" % signed(a[i]["number"]) if i not in model["out_of_figures"] else "it is in no figure") for i in model["removed"]]
        out += ["- `%s` re-estimated: %s points of uncommitted capacity." % (i, signed(was - now)) for i, was, now in model["reest"]]
        if model["out_of_figures"]:
            out.append("- NOT COMPLETE, for the items named in section 1.")
    out += ["", "## 9. What `changed_by` records for each change", "",
            "`changed_by`, in the later snapshot, is whoever last changed the item. That may not be whoever made the change listed here: an item that was re-estimated and then given to another person records one name.",
            "It is set beside the file's `product_owner`, letter for letter. Two spellings of one name are two texts.",
            "**This section says what is recorded. It does not say whether a change was agreed, and it is not a finding about anyone.**", ""]
    if not model["comparable"]:
        out.append("Not compared. See section 7.")
    elif not model["owner"]:
        out.append("- The file records `product_owner` more than once, so neither is used and no change is set beside one." if model["owner_twice"] else "- The file records no `product_owner`, so no change is set beside one.")
    else:
        changed = sorted([(i, "added", b[i].get("changed_by") or None) for i in model["added"]] + [(m["id"], "materially changed", m["changed_by"]) for m in model["material"]])
        same = [(i, kind) for i, kind, who in changed if who == model["owner"]]
        other = [(i, kind, who) for i, kind, who in changed if who and who != model["owner"]]
        unsaid = [(i, kind) for i, kind, who in changed if not who]
        out += ["- `product_owner`: \"%s\"." % safe(model["owner"]),
                "- `changed_by` is the same text as `product_owner` (%d): %s." % (len(same), ", ".join("`%s` (%s)" % x for x in same) or "none"),
                "- `changed_by` is other text (%d):%s" % (len(other), "" if other else " none.")]
        out += ["  - `%s` (%s): \"%s\"." % (i, kind, safe(who)) for i, kind, who in other]
        out += ["- Added or materially changed, with no `changed_by` (%d): %s." % (len(unsaid), ", ".join("`%s` (%s)" % x for x in unsaid) or "none"),
                "- Removed (%d): %s. Who removed an item is in neither snapshot." % (len(model["removed"]), listed(model["removed"]))]
    out += ["", "## What this report does not say", "",
            "- Why anything changed, who agreed to it, or whether it should have been made.",
            "- Whether a material change of wording changed the meaning. It shows both versions.",
            "- Whether a description hides new scope. It shows both versions.",
            "- What happened between the two snapshots and was undone again.",
            "- How much work is done. It compares what is in the sprint, not what is finished.",
            "- Anything about how a person is working.", ""]
    return "\n".join(out)


def compare(path, start_name, later_name, out_path):
    raw = read_bytes(path)
    model = build(raw.decode("utf-8"), start_name, later_name)
    report = render(model, hashlib.sha256(raw).hexdigest())
    if out_path:
        write(out_path, report)
    return model, report


def check(path, start_name, later_name, report_path):
    """Reads a finished report and compares it with the snapshots. Returns a sorted list of problems."""
    problems = set()
    say = problems.add
    raw = read_bytes(path)
    model = build(raw.decode("utf-8"), start_name, later_name)
    report = read_bytes(report_path).decode("utf-8")
    top = report.split("## How to read this")[0]
    found = re.findall(r"^## (\d)\. [^\n]*\n(.*?)(?=^## |\Z)", report, re.S | re.M)
    if len({n for n, _ in found}) != len(found):
        say("The report has two sections with the same number.")
    sections = {}
    for number_, body in found:
        sections.setdefault(number_, body)
    if "sha256 is `%s`" % hashlib.sha256(raw).hexdigest() not in top:
        say("The report does not give the checksum of this file: it was made from another.")
    heads = dict(re.findall(r"^## (\d)\. [^\n(]*\((\d+)\)", report, re.M))
    ids_in = lambda n: re.findall(r"^- `([A-Z][A-Z0-9]*-[0-9]+)`", sections.get(n, ""), re.M)  # noqa: E731
    wanted = {"2": model["added"], "3": model["removed"], "4": [m["id"] for m in model["material"]], "5": [n["id"] for n in model["noise"]]}
    names = {"2": "added", "3": "removed", "4": "materially changed", "5": "noise"}
    for n, ids in wanted.items():
        if ids_in(n) != ids:
            say("Section %s does not list as %s exactly the items the snapshots give." % (n, names[n]))
        if heads.get(n) != str(len(ids_in(n))):
            say("The heading of section %s does not give the number of items listed under it." % n)
        stray = [l for l in sections.get(n, "").split("\n") if re.match(r"^[-*+] ", l) and not re.match(r"^- `[A-Z][A-Z0-9]*-[0-9]+`: ", l)]
        if stray:
            say("Section %s has a line that begins like an item and is not one: %s" % (n, stray[0][:50]))
    for n, side, ids in (("2", model["b"], model["added"]), ("3", model["a"], model["removed"])):
        for i in ids:
            said = "%s points" % points(side[i]["number"]) if side[i]["number"] is not None else "an estimate that cannot be used"
            if "- `%s`: %s. \"%s\"" % (i, said, safe(side[i].get("title") or "")) not in sections.get(n, "").split("\n"):
                say("Section %s does not give for %s its estimate and its title as the snapshot has them." % (n, i))
    unchanged = re.findall(r"`([A-Z][A-Z0-9]*-[0-9]+)`", sections.get("6", "").replace("`changed_by`", ""))
    if unchanged != [u["id"] for u in model["unchanged"]] or heads.get("6") != str(len(unchanged)):
        say("Section 6 does not list as unchanged exactly the items no compared field of which differs, with their number.")
    told = re.search(r"^- In both snapshots, with nothing material seen to differ and something that cannot be compared \((\d+)\): ([^\n]*)\. Neither", sections.get("7", ""), re.M)
    undecided = re.findall(r"`([A-Z][A-Z0-9]*-[0-9]+)`", told.group(2)) if told else None
    if undecided != [u["id"] for u in model["undecided"]] or int(told.group(1)) != len(undecided):
        say("Section 7 does not list exactly the items that are neither material, nor noise, nor unchanged, with their number.")
    in_one_only = [i for i in (set(model["a"]) ^ set(model["b"])) if i not in model["added"] and i not in model["removed"]]
    placed = ids_in("2") + ids_in("3") + ids_in("4") + ids_in("5") + unchanged + (undecided or []) + in_one_only
    if sorted(placed) != sorted(set(model["a"]) | set(model["b"])):
        say("The report does not put every item of the two snapshots in exactly one of its lists.")
    for m in model["material"]:
        block = re.search(r"^- `%s`: fields that differ: ([^\n]*)\.\n((?:  [^\n]*\n)*)" % re.escape(m["id"]), sections.get("4", ""), re.M)
        if not block or re.findall(r"`(\w+)`", block.group(1)) != [d["field"] for d in m["differs"]]:
            say("Section 4 does not give for %s exactly the fields that differ." % m["id"])
        for d in m["differs"]:
            if d["field"] == "estimate" and (not block or block.group(2).count("  - `estimate`:") != 1 or "  - `estimate`: %s at start, %s later. %s points." % (points(d["was"]), points(d["now"]), signed(d["now"] - d["was"])) not in block.group(2)):
                say("Section 4 does not give for %s the two estimates and their difference." % m["id"])
    if not model["comparable"] and sections.get("1", "").strip() != "Not compared. See section 7.":
        say("Nothing was compared, and section 1 says something other than that.")
    if model["comparable"]:
        net = model["later_total"] - model["start_total"]
        lines = [l.strip() for l in report.split("\n")]
        if ("**NOT COMPLETE.**" in sections.get("1", "")) != bool(model["out_of_figures"] or sum(model["unnamed"])):
            say("Section 1 is marked NOT COMPLETE when every item is in its figures, or is not marked when one is not.")
        for start, want in (("committed at start:", "- Committed at start: %s points, in " % points(model["start_total"])),
                            ("committed later:", "- Committed later: %s points, in " % points(model["later_total"])),
                            ("net change:", "- **Net change: %s points.**" % (signed(net) if net else "0"))):
            got = [l for l in lines if re.search(r"(?<![a-z])" + re.escape(start), l.lower())]
            if len(got) != 1 or not got[0].startswith(want):
                say("Section 1 does not say, once: %s" % want.strip())
    entries = len(re.findall(r"^- \[GAP\] ", sections.get("7", ""), re.M))
    said = re.search(r"Entries: (\d+)\.", sections.get("7", ""))
    if entries != len(model["gaps"]) or not said or int(said.group(1)) != entries or "- Gaps reported in section 7: %d." % entries not in top:
        say("Section 7 does not hold one entry for each gap, or a count of them is not the number of entries.")
    if len(re.findall(r"(?i)\bno change\.", report)) != (1 if model["nothing"] else 0) or ("**No change.**" in top) != model["nothing"]:
        say("The report says \"No change\" when something differs, or does not say it when nothing does.")
    if ("**NOTHING WAS COMPARED.**" in top) != (not model["comparable"]):
        say("The report does not say, at its top, that nothing was compared, or says it when something was.")
    known = set(model["a"]) | set(model["b"]) | {g["what"] for g in model["gaps"]} | {g["field"] for g in model["gaps"]}
    for identity in sorted(set(re.findall(r"(?<![A-Za-z0-9-])([A-Z][A-Z0-9]*-[0-9]+)(?![A-Za-z0-9-])", re.sub(r'"[^"\n]*"', "", report)))):
        if identity not in known:
            say("The report names %s, which is in neither snapshot." % identity)
    return sorted(problems)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Compare two snapshots of a sprint, or check a finished report.")
    parser.add_argument("command", choices=["compare", "check"])
    parser.add_argument("--snapshots", required=True)
    parser.add_argument("--start", default="start")
    parser.add_argument("--later", default="later")
    parser.add_argument("--out")
    parser.add_argument("--report")
    args = parser.parse_args(argv)
    try:
        if args.command == "compare":
            if not args.out:
                parser.error("compare needs --out")
            model, _ = compare(args.snapshots, args.start, args.later, args.out)
        else:
            if not args.report:
                parser.error("check needs --report")
            problems = check(args.snapshots, args.start, args.later, args.report)
    except (OSError, UnicodeDecodeError) as error:
        print("COULD NOT READ OR WRITE A FILE: %s. No report was written, or none that can be relied on." % type(error).__name__)
        return 2
    if args.command == "check":
        for problem in problems:
            print("PROBLEM: %s" % problem)
        print("CHECK FAILED. %d problems." % len(problems) if problems else "CHECK PASSED. None of the things this check looks for was found. What it looks for is in SKILL.md.")
        return 1 if problems else 0
    print("wrote %s  sha256 %s" % (os.path.basename(args.out), hashlib.sha256(read_bytes(args.out)).hexdigest()))
    if not model["comparable"]:
        print("NOTHING WAS COMPARED. A snapshot that was asked for is not in the file, or is there twice. Gaps: %d." % len(model["gaps"]))
        return 1
    net = model["later_total"] - model["start_total"]
    print("Compared snapshot \"%s\" with snapshot \"%s\". Matched by identifier." % (args.later, args.start))
    print("Committed at start: %s. Later: %s. Net change: %s." % (points(model["start_total"]), points(model["later_total"]), signed(net) if net else "0"))
    print("Added (%d): %s" % (len(model["added"]), ", ".join(model["added"]) or "none"))
    print("Removed (%d): %s" % (len(model["removed"]), ", ".join(model["removed"]) or "none"))
    print("Materially changed (%d): %s" % (len(model["material"]), ", ".join("%s [%s]" % (m["id"], ", ".join(d["field"] for d in m["differs"])) for m in model["material"]) or "none"))
    print("Differed only in noise, and left out of the change of scope (%d): %s" % (len(model["noise"]), ", ".join("%s [%s]" % (n["id"], ", ".join(x["field"] for x in n["also"])) for n in model["noise"]) or "none"))
    print("Unchanged (%d): %s" % (len(model["unchanged"]), ", ".join(u["id"] for u in model["unchanged"]) or "none"))
    print("Cannot be told (%d): %s" % (len(model["undecided"]), ", ".join(u["id"] for u in model["undecided"]) or "none"))
    print("Gaps: %d.%s" % (len(model["gaps"]), " Not in any figure: %s." % ", ".join(model["out_of_figures"]) if model["out_of_figures"] else ""))
    if model["nothing"]:
        print("NO CHANGE.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
