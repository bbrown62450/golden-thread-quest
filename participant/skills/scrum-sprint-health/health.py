#!/usr/bin/env python3
"""Generates a sprint health report from one sprint snapshot. It reads and writes local files only.

    python3 participant/skills/scrum-sprint-health/health.py generate --snapshot FILE [--previous FILE] --out FILE
    python3 participant/skills/scrum-sprint-health/health.py check    --snapshot FILE [--previous FILE] --report FILE

    --snapshot   a sprint snapshot, in the form participant/skills/scrum-sprint-health/make_snapshot.py writes
    --previous   an earlier snapshot of the same sprint, to report what changed. Optional
    --out        the report to write

EVERY NUMBER COMES FROM A FIELD OF THE SNAPSHOT, AND SO DO BOTH THRESHOLDS AND THE DATE.
  The day everything is counted to is the snapshot's own `snapshot_date`. The computer's clock is never read. The report
  names its snapshot by checksum and not by path. So the same snapshot gives the same bytes, wherever the file is and
  whenever it is run. The aging threshold is the snapshot's `aging_after_days`, and the limit on work in progress is its
  `wip_limit_per_person`. This program has no threshold of its own.

`check` reads a finished report back and compares it with the snapshot. It reads the snapshot with the generator's own
code, so a fault in that reading is invisible to it, and most of what it compares cannot differ on a report the
generator has just written. Its use is on a report that was edited, or kept while the snapshot moved on.
Exit code 0: no problem found. 1: problems, each printed.

THE RULES ARE IN SKILL.md, beside this file. It imports nothing that can reach a network.
"""
import argparse
import datetime
import hashlib
import os
import re
import sys

COLUMNS = ["id", "title", "status", "assignee", "created", "updated", "blocked_by", "depends_on"]
STATUSES = ("todo", "in_progress", "done")
WORDS = {"todo": "not started", "in_progress": "in progress", "done": "done"}   # the snapshot's own meanings of its three statuses
HEADER = ("snapshot_date", "sprint_start", "sprint_end", "sprint_day", "wip_limit_per_person", "aging_after_days")
ID = re.compile(r"^[A-Z][A-Z0-9]*-\d+$")
DATE = re.compile(r"^\d{4}-\d\d-\d\d$")
# Written where a name belongs, and not a name. Each is a gap. `unassigned` is the one word that means nobody is recorded.
NOT_A_NAME = ("none", "tbd", "n/a", "na", "-", "?", "tba", "nobody", "unknown")
JUDGING = ("overloaded", "behind", "slow", "lazy", "struggling", "underperform", "at fault", "should take", "needs to", "bottleneck", "too much", "too many")
UNPRINTABLE = re.compile("[\\x00-\\x1f\\x7f-\\x9f\\u061c\\u200b-\\u200f\\u2028\\u2029\\u202a-\\u202e\\u2066-\\u2069\\ufeff]")
QUOTES = re.compile("[\\u00ab\\u00bb\\u2018-\\u201f\\u2039\\u203a\\u301d-\\u301f\\uff02\\uff07]")   # marks a reader could take for the end of a quotation


def read_bytes(path):
    with open(path, "rb") as f:
        return f.read()


def read(path):
    return read_bytes(path).decode("utf-8")


def write(path, text):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def day_of(text):
    """A date, or None if the text is not one. 2026-13-40 is not one."""
    if not isinstance(text, str) or not DATE.match(text):
        return None
    try:
        return datetime.datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def dated(day):
    """A date with its day of the week, so that a weekend can be seen."""
    return "%s %s" % (("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")[day.weekday()], day.isoformat())


def weekend_days(first, last):
    """How many of the days after `first`, up to and including `last`, are a Saturday or a Sunday."""
    return sum(1 for n in range(1, (last - first).days + 1) if (first + datetime.timedelta(days=n)).weekday() >= 5)


def safe(text):
    """Other people's text made fit to print inside double quotes on one line. It is never read for meaning."""
    out = QUOTES.sub("'", UNPRINTABLE.sub(" ", str(text)))
    for bad, good in (("`", "'"), ('"', "'"), ("|", "/"), ("<", "("), (">", ")"), ("[", "("), ("]", ")"), ("*", ""), ("#", "")):
        out = out.replace(bad, good)
    return out if len(out) <= 70 else out[:67] + "..."


def parse(text):
    """A snapshot into its header, its rows and what could not be read. A blank cell is None: the field is not recorded."""
    text = text.replace("\r\n", "\n")
    parts = re.split(r"^## ", text, flags=re.M)
    headed = [(p.split("\n", 1)[0].strip(), p.split("\n", 1)[1] if "\n" in p else "") for p in parts[1:]]
    header, rows, trouble, unusable, spoiled = {}, [], [], {}, []
    out = {"header": header, "rows": rows, "trouble": trouble, "front": parts[0], "unusable": unusable, "spoiled": spoiled}
    sprint = [body for heading, body in headed if heading == "The sprint"]
    if len(sprint) != 1:
        trouble.append(("the snapshot", "The sprint", "it has %d sections headed The sprint, and one is needed. No header line is read" % len(sprint)))
        for name in HEADER:
            unusable[name] = "it cannot be read, because the snapshot has %d sections headed The sprint" % len(sprint)
    else:
        for name, value in re.findall(r"^[ \t]*[-*][ \t]*(\w+)[ \t]*:[ \t]*(.*)$", sprint[0], re.M):
            name = name.lower()
            if name not in HEADER:
                continue
            if name in header or name in unusable:
                if name not in unusable:
                    trouble.append(("the snapshot", name, "it is recorded more than once. Neither value is used"))
                unusable[name] = "one is recorded more than once and neither value is used"
                header.pop(name, None)
            else:
                header[name] = value.strip()
    tables = [body for heading, body in headed if heading == "Items"]
    if len(tables) != 1:
        trouble.append(("the snapshot", "Items", "it has %d sections headed Items, and one is needed. No item is read" % len(tables)))
        return out
    lines = [l for l in tables[0].split("\n") if l.strip()]
    stray = [l for l in lines if not (l.strip().startswith("|") and l.strip().endswith("|"))]
    lines = [l.strip() for l in lines if l not in stray]
    for line in stray:
        trouble.append(("the table of items", "a line", "a line in the Items section is not a row of the table: \"%s\"" % safe(line.strip())))
    cells_of = lambda line: [c.strip() for c in line[1:-1].split("|")]  # noqa: E731
    if not lines or cells_of(lines[0]) != COLUMNS:
        trouble.append(("the table of items", "the columns", "there is no table, or its columns are not %s. No item is read" % ", ".join(COLUMNS)))
        return out
    if len(lines) < 2 or not re.match(r"^\|(\s*:?-+:?\s*\|)+$", lines[1]):
        trouble.append(("the table of items", "the second line", "it is not the line of dashes that follows a table's headings. No item is read"))
        return out
    for number, line in enumerate(lines[2:], 1):
        cells = cells_of(line)
        if len(cells) != len(COLUMNS):
            trouble.append(("row %d of the table" % number, "the row", "it has %d cells and the table has %d columns. Its first cell is \"%s\"" % (len(cells), len(COLUMNS), safe(cells[0]))))
            if ID.match(cells[0]):
                spoiled.append(cells[0])
            continue
        row = {name: (cell if cell else None) for name, cell in zip(COLUMNS, cells)}
        if not row["id"] or not ID.match(row["id"]):
            trouble.append(("row %d of the table" % number, "id", "it has no identifier that can be read"))
            continue
        rows.append(row)
    return out


def ids_of(cell):
    """A blocked_by or depends_on cell: None if not recorded, [] for `none`, a list of ids, or the word "unreadable"."""
    if cell is None:
        return None
    if cell.lower() == "none":
        return []
    parts = [p.strip() for p in cell.split(",")]
    return list(dict.fromkeys(parts)) if all(ID.match(p) for p in parts) else "unreadable"


def loops_of(waits, order):
    """The groups of items that wait on each other, directly or round a longer loop. Each group is sorted."""
    index, low, stack, on, found, counter = {}, {}, [], set(), [], [0]

    def visit(v):
        index[v] = low[v] = counter[0]
        counter[0] += 1
        stack.append(v)
        on.add(v)
        for w in sorted(waits.get(v, {})):
            if w not in index:
                visit(w)
                low[v] = min(low[v], low[w])
            elif w in on:
                low[v] = min(low[v], index[w])
        if low[v] == index[v]:
            group = []
            while True:
                w = stack.pop()
                on.discard(w)
                group.append(w)
                if w == v:
                    break
            if len(group) > 1:
                found.append(sorted(group))
    for v in order:
        if v not in index:
            visit(v)
    return sorted(found)


def build(snapshot_text):
    """Works everything out for one snapshot. Returns the model the report is written from."""
    read_in = parse(snapshot_text)
    header, rows, trouble, front, unusable = (read_in[k] for k in ("header", "rows", "trouble", "front", "unusable"))
    spoiled = set(read_in["spoiled"])
    gaps = []

    def gap(what, field, reason, left_out):
        gaps.append({"what": what, "field": field, "reason": reason, "left_out": left_out})

    for what, field, reason in trouble:
        gap(what, field, reason, "everything that depends on it" if what == "the snapshot" else "everything that row or line would have held")
    today = day_of(header.get("snapshot_date"))
    if today is None and "snapshot_date" not in unusable:
        said = header.get("snapshot_date")
        gap("the snapshot", "snapshot_date", "it is not recorded" if said is None else "it is \"%s\", which is not a date" % safe(said), "aging, which needs a day to count to")

    def whole(name, what):
        value = header.get(name)
        if name in unusable:
            return None, unusable[name] + " (a gap, in section 6)"
        if value is None:
            return None, "none is set: the snapshot records no `%s`" % name
        if not re.match(r"^\d+$", value):
            gap("the snapshot", name, "it is \"%s\", which is not a whole number" % safe(value), what)
            return None, "one is recorded, as \"%s\", and cannot be used, because it is not a whole number (a gap, in section 6)" % safe(value)
        return int(value), None
    limit, no_limit = whole("wip_limit_per_person", "comparing any count of work in progress with a limit")
    threshold, no_threshold = whole("aging_after_days", "aging")

    seen, items = {}, {}
    for row in rows:
        seen[row["id"]] = seen.get(row["id"], 0) + 1
    for row in rows:
        if seen[row["id"]] > 1:
            if not any(g["what"] == row["id"] and g["field"] == "id" for g in gaps):
                gap(row["id"], "id", "%d rows have this identifier. None of them is used" % seen[row["id"]], "everything")
            spoiled.add(row["id"])
            continue
        items[row["id"]] = row

    info = {}
    for identity, row in items.items():
        one = {"id": identity, "title": row["title"] or "", "status": None, "raw_status": row["status"], "assignee": None, "assigned": None, "age": None, "updated": row["updated"],
               "updated_day": None, "blocked_by": None, "depends_on": None, "unknown": {"blocked_by": [], "depends_on": []}}
        if row["status"] is None:
            gap(identity, "status", "it is blank", "progress, aging, work in progress and dependency risk")
        elif row["status"] not in STATUSES:
            gap(identity, "status", "it is \"%s\", which is not one of %s, written exactly so. The report cannot classify it" % (safe(row["status"]), ", ".join(STATUSES)), "progress, aging, work in progress and dependency risk")
        else:
            one["status"] = row["status"]
        if row["assignee"] is None:
            gap(identity, "assignee", "it is blank. That is not the same as being recorded as unassigned", "work in progress for each person")
        elif row["assignee"].lower() == "unassigned":
            one["assigned"] = False
        elif row["assignee"].lower() in NOT_A_NAME:
            gap(identity, "assignee", "it is \"%s\", which is neither a name nor the word unassigned" % safe(row["assignee"]), "work in progress for each person")
        else:
            one["assigned"], one["assignee"] = True, row["assignee"]
        created, updated = day_of(row["created"]), day_of(row["updated"])
        if row["created"] is None:
            gap(identity, "created", "it is blank", "nothing: no number here is counted from it")
        elif created is None:
            gap(identity, "created", "it is \"%s\", which is not a date" % safe(row["created"]), "nothing: no number here is counted from it")
        if created is not None and today is not None and created > today:
            gap(identity, "created", "it is %s, which is after the snapshot's own date, %s" % (row["created"], header.get("snapshot_date")), "nothing: no number here is counted from it")
        if row["updated"] is None:
            gap(identity, "updated", "it is blank", "aging: how long it has gone without an update is not known")
        elif updated is None:
            gap(identity, "updated", "it is \"%s\", which is not a date" % safe(row["updated"]), "aging")
        elif today is not None and updated > today:
            gap(identity, "updated", "it is %s, which is after the snapshot's own date, %s" % (row["updated"], header.get("snapshot_date")), "aging")
        elif created is not None and created > updated:
            gap(identity, "created and updated", "they disagree: it is recorded as updated on %s and created on %s, which is later. Which of the two is wrong is not known" % (row["updated"], row["created"]), "aging")
        elif today is not None:
            one["age"], one["updated_day"] = (today - updated).days, updated
        for field in ("blocked_by", "depends_on"):
            found = ids_of(row[field])
            unsaid = "blocked items and dependency risk" if field == "blocked_by" else "dependency risk"
            if found is None:
                gap(identity, field, "it is blank. That is not the same as none", unsaid)
            elif found == "unreadable":
                gap(identity, field, "it is \"%s\", which is neither none nor a list of identifiers" % safe(row[field]), unsaid)
            elif identity in found:
                gap(identity, field, "it names the item itself", unsaid)
            else:
                known = []
                for other in found:
                    if other not in items:
                        gap(identity, field, "it names %s, %s" % (other, "whose row cannot be used" if other in spoiled else "which is not in the snapshot"), "dependency risk, as far as %s goes: whether %s is done cannot be told" % (other, other))
                        one["unknown"][field].append(other)
                    else:
                        known.append(other)
                one[field] = known
        info[identity] = one

    order = sorted(info)
    by_status = {s: [i for i in order if info[i]["status"] == s] for s in STATUSES}
    can_age = threshold is not None and today is not None
    is_aging = lambda i: can_age and info[i]["status"] == "in_progress" and info[i]["age"] is not None and info[i]["age"] > threshold  # noqa: E731
    aging = [i for i in order if is_aging(i)]
    has_blocker = lambda i: info[i]["blocked_by"] is not None and bool(info[i]["blocked_by"] or info[i]["unknown"]["blocked_by"])  # noqa: E731
    blocked = [(i, info[i]["blocked_by"] + info[i]["unknown"]["blocked_by"]) for i in order if has_blocker(i) and info[i]["status"] in ("todo", "in_progress")]
    blocked_unknown = [i for i in order if has_blocker(i) and info[i]["status"] is None]
    blocked_done = [i for i in order if has_blocker(i) and info[i]["status"] == "done"]

    people = {}
    for i in by_status["in_progress"]:
        if info[i]["assigned"]:
            people.setdefault(info[i]["assignee"], []).append(i)
    nobody = [i for i in by_status["in_progress"] if info[i]["assigned"] is False]
    unknown_who = [i for i in by_status["in_progress"] if info[i]["assigned"] is None]
    no_status_named = [(i, info[i]["assignee"]) for i in order if info[i]["status"] is None and info[i]["assigned"]]

    # Dependency risk. X waits on Y when Y is in X's blocked_by or depends_on, neither is done, and both statuses can be used.
    waits, not_assessed = {}, []
    for x in order:
        if info[x]["status"] == "done":
            continue
        for field in ("blocked_by", "depends_on"):
            if info[x]["status"] is None:
                if info[x][field] or info[x]["unknown"][field]:
                    not_assessed.append("`%s` names %s in its `%s`, and its own status cannot be used" % (x, ", ".join("`%s`" % y for y in (info[x][field] or []) + info[x]["unknown"][field]), field))
                continue
            if info[x][field] is None:
                not_assessed.append("`%s`: its `%s` cannot be used" % (x, field))
            for y in info[x]["unknown"][field]:
                not_assessed.append("`%s` names `%s` in its `%s`, and %s" % (x, y, field, "the row of `%s` cannot be used" % y if y in spoiled else "`%s` is not in the snapshot" % y))
            for y in info[x][field] or []:
                if info[y]["status"] is None:
                    not_assessed.append("`%s` names `%s` in its `%s`, and the status of `%s` cannot be used" % (x, y, field, y))
                elif info[y]["status"] != "done":
                    waits.setdefault(x, {}).setdefault(y, []).append(field)

    def own_links_unsure(y):
        """Whether one of y's own links could not be assessed, so that whether y is itself waiting cannot be told."""
        return any(info[y][f] is None or info[y]["unknown"][f] or any(info[z]["status"] is None for z in info[y][f]) for f in ("blocked_by", "depends_on"))
    loops = loops_of(waits, order)
    in_loop = {i for group in loops for i in group}
    risks, plain, undecided = [], [], []
    for x in order:
        for y in sorted(waits.get(x, {})):
            why, unknown = [], []
            if info[y]["status"] == "todo":
                why.append("D1: `%s` is not started (its `status` is `todo`)" % y)
            if info[y]["assigned"] is False:
                why.append("D2: nobody is recorded as assigned to `%s` (its `assignee` is `unassigned`)" % y)
            elif info[y]["assigned"] is None:
                unknown.append("D2 cannot be told: the `assignee` of `%s` cannot be used" % y)
            if is_aging(y):
                why.append("D3: `%s` is in progress and its `updated` is %s, %d days before the snapshot, more than the %d the snapshot sets" % (y, info[y]["updated"], info[y]["age"], threshold))
            elif info[y]["status"] == "in_progress" and (not can_age or info[y]["age"] is None):
                unknown.append("D3 cannot be told: %s" % ("the `updated` of `%s` cannot be used" % y if can_age else "no aging threshold or no date can be used"))
            if waits.get(y):
                why.append("D4: `%s` is itself waiting, on %s (in its `%s`)" % (y, ", ".join("`%s`" % z for z in sorted(waits[y])), "` and `".join(sorted({f for z in waits[y] for f in waits[y][z]}))))
            elif own_links_unsure(y):
                unknown.append("D4 cannot be told: one of the links of `%s` itself could not be assessed" % y)
            (risks if why else undecided if unknown else plain).append({"x": x, "y": y, "fields": waits[x][y], "why": why, "unknown": unknown})

    def chains_from(x, path):
        out = []
        for y in sorted(waits.get(x, {})):
            if y in path or y in in_loop:
                continue
            out += chains_from(y, path + [y]) or [path + [y]]
        return out
    starts = [x for x in order if x not in in_loop and not any(x in waits.get(w, {}) for w in waits if w not in in_loop)]
    chains = sorted({tuple(c) for x in starts for c in chains_from(x, [x]) if len(c) >= 3})
    fan_in = {}
    for x in waits:
        for y in waits[x]:
            fan_in.setdefault(y, set()).add(x)
    waited_on = sorted(fan_in)
    fan_in = {y: sorted(xs) for y, xs in sorted(fan_in.items()) if len(xs) >= 2}
    said = lambda n, name: str(n) if n is not None else "not usable" if name in header or name in unusable else "not set"  # noqa: E731
    return {"header": header, "front": front, "info": info, "order": order, "gaps": gaps, "by_status": by_status, "aging": aging, "blocked": blocked, "blocked_done": blocked_done,
            "blocked_unknown": blocked_unknown, "spoiled": spoiled, "unusable": unusable, "threshold_said": said(threshold, "aging_after_days"), "limit_said": said(limit, "wip_limit_per_person"),
            "people": people, "nobody": nobody, "unknown_who": unknown_who, "no_status_named": no_status_named, "risks": risks, "plain": plain, "undecided": undecided,
            "not_assessed": not_assessed, "chains": chains, "loops": loops, "fan_in": fan_in, "waited_on": waited_on, "limit": limit, "no_limit": no_limit,
            "threshold": threshold, "no_threshold": no_threshold, "today": today, "can_age": can_age, "waits": waits}


def changes_between(before, now):
    """What differs between two snapshots, by identifier. Only the kinds of change listed in the report are compared."""
    lines = []
    say = lines.append
    if before["today"] and now["today"] and before["today"] > now["today"]:
        say("ORDER: the snapshot given as previous is dated %s, which is after this one's date, %s." % (before["today"].isoformat(), now["today"].isoformat()))
    if before["threshold_said"] != now["threshold_said"]:
        say("THRESHOLD: the aging threshold was %s in the previous snapshot and is %s in this one. Each snapshot is read by its own." % (before["threshold_said"], now["threshold_said"]))
    if before["limit_said"] != now["limit_said"]:
        say("LIMIT: the limit on work in progress was %s in the previous snapshot and is %s in this one." % (before["limit_said"], now["limit_said"]))
    was_info, info = before["info"], now["info"]
    for i in sorted(set(info) - set(was_info)):
        say("ROW NOT USABLE BEFORE: `%s` is in this snapshot, and its row in the previous one cannot be used." % i if i in before["spoiled"] else "ADDED: `%s` is in this snapshot and was not in the previous one." % i)
    for i in sorted(set(was_info) - set(info)):
        say("ROW NOT USABLE NOW: `%s` was in the previous snapshot, and its row in this one cannot be used." % i if i in now["spoiled"] else "REMOVED: `%s` was in the previous snapshot and is not in this one. Why is not recorded." % i)
    for i in sorted(set(info) & set(was_info)):
        was, cur = was_info[i], info[i]
        if was["status"] and cur["status"]:
            if was["status"] != cur["status"]:
                say("STATUS: `%s` was `%s` and is now `%s`." % (i, was["status"], cur["status"]))
        elif was["raw_status"] != cur["raw_status"]:
            say("STATUS NOT COMPARED: the `status` of `%s` differs, and in one of the two snapshots it cannot be used." % i)
        if cur["status"] == "in_progress" and was["status"] == "in_progress":
            if was["age"] is None or cur["age"] is None or not before["can_age"] or not now["can_age"]:
                if (was["age"] is None) != (cur["age"] is None) or before["can_age"] != now["can_age"]:
                    say("AGING NOT COMPARED: whether `%s` is aging cannot be told in one of the two snapshots." % i)
            elif i in now["aging"] and i not in before["aging"]:
                say("NEWLY AGING: `%s` was last updated %d days before this snapshot, and %d days before the previous one." % (i, cur["age"], was["age"]))
            elif i in before["aging"] and i not in now["aging"]:
                say("NO LONGER AGING: `%s` was last updated %d days before the previous snapshot, and %d days before this one." % (i, was["age"], cur["age"]))
        for field in ("blocked_by", "depends_on"):
            a = None if was[field] is None else sorted(was[field] + was["unknown"][field])
            b = None if cur[field] is None else sorted(cur[field] + cur["unknown"][field])
            if a is None or b is None:
                if a != b:
                    say("%s NOT COMPARED: the `%s` of `%s` differs, and in one of the two snapshots it cannot be used." % (field.upper(), field, i))
            elif a != b:
                say("%s: the `%s` of `%s` was %s and is now %s." % (field.upper(), field, i, ", ".join(a) or "none", ", ".join(b) or "none"))
    return lines


def render(model, snapshot_sha, previous=None):
    info, header = model["info"], model["header"]
    listed = lambda ids: ", ".join("`%s`" % i for i in ids) or "none"  # noqa: E731
    classified = sum(len(v) for v in model["by_status"].values())
    no_status = [i for i in model["order"] if info[i]["status"] is None]
    threshold, limit, today = model["threshold"], model["limit"], model["today"]
    shown = lambda key: "\"%s\"" % safe(header[key]) if header.get(key) else "not usable (see section 6)" if key in model["unusable"] else "not recorded"  # noqa: E731
    no_date = "a snapshot with no date that can be used"
    out = ["# Sprint health report, for %s" % ("the snapshot of " + today.isoformat() if today else no_date), "",
           "**The snapshot says of itself that it is made up.**" if "**Made up.**" in model["front"] else "**Built from one sprint snapshot.**",
           "Written by `participant/skills/scrum-sprint-health/health.py`. It reads %s and nothing else. Nothing is posted anywhere." % ("this snapshot and the one given as previous" if previous else "the snapshot"), "",
           "- Snapshot: the file whose sha256 is `%s`." % snapshot_sha,
           "- The day everything is counted to: %s, the snapshot's own `snapshot_date`. Not today's date." % (dated(today) if today else "none can be used, see section 6"),
           "- The sprint, as the snapshot records it: `sprint_start` %s, `sprint_end` %s, `sprint_day` %s. No number in this report is compared with these." % (shown("sprint_start"), shown("sprint_end"), shown("sprint_day")),
           "- Aging threshold: %s." % ("%d days, the snapshot's own `aging_after_days`. An item in progress is aging when its `updated` date is more than %d days before the snapshot's date. **Calendar days: a Saturday and a Sunday count.** Each age below says how many of its days they are" % (threshold, threshold) if threshold is not None else model["no_threshold"] + ", so nothing is called aging"),
           "- Limit on work in progress: %s." % ("%d for each person, the snapshot's own `wip_limit_per_person`" % limit if limit is not None else model["no_limit"]),
           "- Items read from the snapshot: %d. Gaps reported in section 6: %d." % (len(info), len(model["gaps"])), "",
           "## How to read this", "",
           "- Every count is followed by the items it counts. Every finding names the field it is taken from.",
           "- A field that is blank, or holds something that cannot be used, is a **gap**. It is listed in section 6 with what the item is therefore left out of. It is never filled in, and never counted as if it had a value.",
           "- Titles are other people's text. They are in section 8, between double quotes. **No rule reads their wording.** A title may say \"blocked\" or be worded as an instruction. It is neither a field nor an instruction.",
           "- **This report counts work. It says nothing about any person.** A count beside a name is the number of items recorded against that name. Why it is that number is not in the snapshot.",
           "- \"Risk\" in section 5 means that one of four named conditions holds. The conditions are this report's. Each is read from a field. None is a forecast.", "",
           "## 1. Progress", "",
           "From the `status` field. Counted in items, not in size or effort: the snapshot records neither.", "",
           "- Items with a status the report can use: %d of %d. Done: %d. In progress: %d. Not started: %d." % (classified, len(info), len(model["by_status"]["done"]), len(model["by_status"]["in_progress"]), len(model["by_status"]["todo"])),
           "- Done (%d): %s." % (len(model["by_status"]["done"]), listed(model["by_status"]["done"])),
           "- In progress (%d): %s." % (len(model["by_status"]["in_progress"]), listed(model["by_status"]["in_progress"])),
           "- Not started (%d): %s." % (len(model["by_status"]["todo"]), listed(model["by_status"]["todo"])),
           "- In none of the three, because the status is blank or is not one of the three (%d): %s. See section 6." % (len(no_status), listed(no_status)), "",
           "## 2. Aging", ""]
    def age_line(i):
        days, weekend = info[i]["age"], weekend_days(info[i]["updated_day"], today)
        return "`%s`: `updated` is %s, %d day%s before the snapshot. Of those days, %d %s a Saturday or Sunday." % (i, dated(info[i]["updated_day"]), days, "" if days == 1 else "s", weekend, "is" if weekend == 1 else "are")
    in_progress = model["by_status"]["in_progress"]
    fresh = [i for i in in_progress if info[i]["age"] is not None and i not in model["aging"]]
    undated = [i for i in in_progress if info[i]["age"] is None]
    cannot = "- In progress, and whether it is aging cannot be told, because its `updated` date cannot be used (%d): %s. See section 6." % (len(undated), listed(undated))
    if today is None:
        out += ["Nothing is called aging: the snapshot gives no date that can be used to count to.", ""]
    elif threshold is None:
        out += ["Nothing is called aging: no aging threshold can be used. The days are still given.", "",
                "- In progress, with an `updated` date that can be used (%d): %s." % (len(fresh), listed(fresh))]
        out += ["  - " + age_line(i) for i in fresh] + [cannot.replace("whether it is aging cannot be told", "with no days to give"), ""]
    else:
        out += ["From the `status` and `updated` fields. In progress, and last updated more than %d days before %s." % (threshold, dated(today)), "",
                "- Aging (%d): %s." % (len(model["aging"]), listed(model["aging"]))]
        out += ["  - " + age_line(i) for i in model["aging"]]
        out += ["- In progress and not aging (%d): %s." % (len(fresh), listed(fresh))]
        out += ["  - " + age_line(i) for i in fresh] + [cannot, ""]
    out += ["## 3. Blocked", "",
            "From the `blocked_by` field, and from nothing else.", "",
            "- Recorded as blocked, and not done (%d): %s." % (len(model["blocked"]), listed([i for i, _ in model["blocked"]]))]
    for i, blockers in model["blocked"]:
        out.append("  - `%s`: `blocked_by` is %s. %s" % (i, ", ".join(blockers), " ".join(
            ("The row of `%s` cannot be used." % b if b in model["spoiled"] else "`%s` is not in the snapshot." % b) if b not in info else "`%s` is %s." % (b, WORDS[info[b]["status"]]) if info[b]["status"] else "The status of `%s` cannot be used." % b for b in blockers)))
    not_recorded = [i for i in model["order"] if info[i]["blocked_by"] is None]
    out += ["- Done, and its `blocked_by` still names something (%d): %s." % (len(model["blocked_done"]), listed(model["blocked_done"])),
            "- Its status cannot be used, and its `blocked_by` names something (%d): %s. See section 6." % (len(model["blocked_unknown"]), listed(model["blocked_unknown"])),
            "- Whether it is blocked cannot be told, because its `blocked_by` cannot be used (%d): %s. See section 6." % (len(not_recorded), listed(not_recorded)), "",
            "## 4. Work in progress, for each person", "",
            "From the `status` and `assignee` fields. An item counts when its `status` is `in_progress`.",
            "**A count is of items recorded against a name. It is not a measure of anyone.** Two spellings of one name are counted as two names.", ""]
    for person in sorted(model["people"]):
        mine = model["people"][person]
        over = "" if limit is None else " The recorded limit is %d: %s." % (limit, "this is %d more than the limit" % (len(mine) - limit) if len(mine) > limit else "this is at the limit" if len(mine) == limit else "this is %d under the limit" % (limit - len(mine)))
        both = [i for i in mine if i in dict(model["blocked"])]
        old = [i for i in mine if i in model["aging"]]
        unsure = [i for i in mine if info[i]["blocked_by"] is None or info[i]["age"] is None or not model["can_age"]]
        out.append("- \"%s\": %d in progress (%s).%s Of these, recorded as blocked: %s. Aging: %s. One or the other cannot be told for: %s." % (safe(person), len(mine), listed(mine), over, listed(both), listed(old), listed(unsure)))
    if not model["people"]:
        out.append("- No item in progress has a name recorded against it.")
    out += ["- In progress and recorded as unassigned (%d): %s." % (len(model["nobody"]), listed(model["nobody"])),
            "- In progress, with an `assignee` that cannot be used, so counted for nobody (%d): %s. See section 6." % (len(model["unknown_who"]), listed(model["unknown_who"])),
            "- Recorded against a name, with a status that cannot be used, so in no count above (%d): %s. If any of these is in progress, the count for that name is higher than shown."
            % (len(model["no_status_named"]), ", ".join("`%s` (\"%s\")" % (i, safe(who)) for i, who in model["no_status_named"]) or "none")]
    if limit is None:
        out.append("- No limit on work in progress can be used, so no count is compared with one.")
    total = len(model["risks"]) + len(model["plain"]) + len(model["undecided"])
    out += ["", "## 5. Dependency risk", "",
            "From the `blocked_by` and `depends_on` fields, with the `status`, `assignee` and `updated` of the item waited on.",
            "An item **waits on** another when the other is in its `blocked_by` or `depends_on`, and neither is done. The two fields are counted alike here, and each line says which it was.",
            "A wait is called a risk when one of these holds: D1 the item waited on is not started. D2 nobody is recorded as assigned to it. D3 it is aging. D4 it is itself waiting on something.", "",
            "- Waits in all: %d, on %d different items: %s. One item that is waited on by several makes several waits." % (total, len(model["waited_on"]), listed(model["waited_on"])),
            "- Waits that are a risk (%d):%s" % (len(model["risks"]), "" if model["risks"] else " none.")]
    for r in model["risks"]:
        out.append("  - `%s` waits on `%s` (in its `%s`). %s.%s" % (r["x"], r["y"], "` and `".join(r["fields"]), ". ".join(r["why"]), "".join(" %s." % u for u in r["unknown"])))
    out += ["- Waits where none of D1 to D4 holds (%d): %s." % (len(model["plain"]), ", ".join("`%s` on `%s`" % (r["x"], r["y"]) for r in model["plain"]) or "none"),
            "- Waits where none is seen to hold, and one cannot be told (%d):%s" % (len(model["undecided"]), "" if model["undecided"] else " none.")]
    out += ["  - `%s` waits on `%s` (in its `%s`). %s." % (r["x"], r["y"], "` and `".join(r["fields"]), ". ".join(r["unknown"])) for r in model["undecided"]]
    out += ["- Links that could not be assessed at all, and are in none of the counts above (%d). See section 6%s" % (len(model["not_assessed"]), ":" if model["not_assessed"] else ".")]
    out += ["  - %s." % line for line in model["not_assessed"]]
    out += ["- Chains of three items or more (%d):%s" % (len(model["chains"]), "" if model["chains"] else " none.")]
    out += ["  - %s. By the snapshot, each but the last is recorded as waiting on the one after it." % " waits on ".join("`%s`" % i for i in chain) for chain in model["chains"]]
    out += ["- Items that wait on each other, directly or round a loop (%d):%s" % (len(model["loops"]), "" if model["loops"] else " none.")]
    out += ["  - %s. By the snapshot, each of them is recorded as waiting on another of them." % listed(group) for group in model["loops"]]
    out += ["- Items that two or more others wait on (%d):%s" % (len(model["fan_in"]), "" if model["fan_in"] else " none.")]
    out += ["  - `%s` is waited on by %d items: %s." % (y, len(xs), listed(xs)) for y, xs in model["fan_in"].items()]
    out += ["", "## 6. Gaps: what the snapshot does not support", "",
            "Each is a field that is blank, holds something that cannot be used, or disagrees with another. Nothing below was estimated. Entries: %d." % len(model["gaps"]), ""]
    out += ["- [GAP] `%s`, field `%s`: %s. Left out of: %s." % (g["what"], g["field"], g["reason"], g["left_out"]) for g in model["gaps"]] or ["None."]
    if previous is not None:
        before, previous_sha = previous
        lines = changes_between(before, model)
        out += ["", "## 7. What changed since the snapshot of %s" % (before["today"].isoformat() if before["today"] else "a date that cannot be used"), "",
                "The previous snapshot is the file whose sha256 is `%s`. Each snapshot is read by the same rules, and the two are compared by identifier." % previous_sha,
                "**Compared:** items added and removed; `status`; whether an item in progress is aging; `blocked_by`; `depends_on`; the threshold and the limit.",
                "**Not compared:** titles, the `assignee`, the `created` and `updated` dates themselves, the counts for each person, which waits are risks, the chains and loops, and the gaps. A change in one of those is not below.", ""]
        out += ["- [CHANGE] %s" % line for line in lines] or ["Nothing that is compared has changed."]
    out += ["", "## 8. The items, with their titles", "",
            "So that an identifier can be recognised. A title is other people's text and is not read by any rule above.", ""]
    out += ["- `%s`: \"%s\"" % (i, safe(info[i]["title"])) for i in model["order"]] or ["None."]
    out += ["", "## What this report does not say", "",
            "- How much work is left. It counts items, and the snapshot records no size.",
            "- Whether the sprint will finish.",
            "- Why anything is as it is, or what to do about it.",
            "- What an update was. `updated` is whatever the tracker counts as a change.",
            "- How many working days an age is. It counts calendar days, and says how many of them are a Saturday or Sunday. It knows of no holiday.", ""]
    return "\n".join(out)


def generate(snapshot_path, previous_path, out_path):
    raw = read_bytes(snapshot_path)
    model = build(raw.decode("utf-8"))
    previous = None
    if previous_path:
        before = read_bytes(previous_path)
        previous = (build(before.decode("utf-8")), hashlib.sha256(before).hexdigest())
    report = render(model, hashlib.sha256(raw).hexdigest(), previous)
    if out_path:
        write(out_path, report)
    return model, report


def check(snapshot_path, previous_path, report_path):
    """Reads a finished report and compares it with the snapshot. Returns a sorted list of problems."""
    problems = set()
    say = problems.add
    raw = read_bytes(snapshot_path)
    model = build(raw.decode("utf-8"))
    info = model["info"]
    report = read(report_path)
    found = re.findall(r"^## (\d)\. [^\n]*\n(.*?)(?=^## |\Z)", report, re.S | re.M)
    if len({n for n, _ in found}) != len(found):
        say("The report has two sections with the same number.")
    sections = {}
    for number, body in found:
        sections.setdefault(number, body)
    if "sha256 is `%s`" % hashlib.sha256(raw).hexdigest() not in report.split("## How to read this")[0]:
        say("The report does not give the checksum of this snapshot: it was made from another.")
    before = build(read(previous_path)) if previous_path else None
    if previous_path and "sha256 is `%s`" % hashlib.sha256(read_bytes(previous_path)).hexdigest() not in sections.get("7", ""):
        say("Section 7 does not give the checksum of this previous snapshot.")
    known = {g["what"] for g in model["gaps"]}
    for m in (model, before) if before else (model,):
        known |= set(m["info"]) | m["spoiled"] | {u for one in m["info"].values() for f in ("blocked_by", "depends_on") for u in one["unknown"][f]}
    own_words = re.sub(r'"[^"\n]*"', "", report)
    for identity in sorted(set(re.findall(r"\b([A-Z][A-Z0-9]*-\d+)\b", own_words))):
        if identity not in known:
            say("The report names %s, which is not in the snapshot." % identity)
    for line in report.split("\n"):
        got = re.match(r"^- ([A-Z][^:(]*?) \((\d+)\):(.*)$", line) or re.match(r"^- (\"[^\"]*\"): (\d+) in progress \(([^)]*)\)", line)
        if got and not got.group(1).startswith(("Waits", "Chains", "Links", "Items that")):
            named = re.findall(r"`([A-Z][A-Z0-9]*-\d+)`", got.group(3).split(". See section")[0].split(". If any")[0])
            if len(named) != int(got.group(2)):
                say("A line gives the number %s and lists %d items: %s" % (got.group(2), len(named), line[:70]))

    def line_ids(section, start):
        lines = [l for l in sections.get(section, "").split("\n") if l.startswith(start)]
        return sorted(re.findall(r"`([A-Z][A-Z0-9]*-\d+)`", lines[0].split(". See section")[0])) if len(lines) == 1 else None
    for status, start in (("done", "- Done ("), ("in_progress", "- In progress ("), ("todo", "- Not started (")):
        if line_ids("1", start) != sorted(model["by_status"][status]):
            say("Section 1 does not list as %s exactly the items whose status is %s." % (status, status))
    seen = sorted(i for start in ("- Done (", "- In progress (", "- Not started (", "- In none of the three") for i in (line_ids("1", start) or []))
    if seen != sorted(info):
        say("Section 1 does not account for every item of the snapshot exactly once.")
    totals = re.search(r"can use: (\d+) of (\d+)\. Done: (\d+)\. In progress: (\d+)\. Not started: (\d+)\.", sections.get("1", ""))
    real = [sum(len(v) for v in model["by_status"].values()), len(info)] + [len(model["by_status"][s]) for s in ("done", "in_progress", "todo")]
    if not totals or [int(n) for n in totals.groups()] != real:
        say("The first line of section 1 does not give the counts of the snapshot.")
    if model["can_age"]:
        fresh = sorted(i for i in model["by_status"]["in_progress"] if info[i]["age"] is not None and i not in model["aging"])
        if line_ids("2", "- Aging (") != sorted(model["aging"]) or line_ids("2", "- In progress and not aging (") != fresh:
            say("Section 2 does not list as aging, and as not aging, exactly the items in progress on each side of the threshold.")
        for identity, when, days in re.findall(r"^  - `([A-Z0-9-]+)`: `updated` is \w+ (\S+), (\d+) days? before", sections.get("2", ""), re.M):
            if identity not in info or info[identity]["age"] is None or int(days) != info[identity]["age"] or info[identity]["updated"] != when:
                say("Section 2 gives %s an update date or a number of days that is not the snapshot's." % identity)
        if "- Aging threshold: %d days," % model["threshold"] not in report.split("## How to read this")[0] or "more than %d days before" % model["threshold"] not in sections.get("2", ""):
            say("The report does not show the aging threshold the snapshot sets.")
    elif "Nothing is called aging" not in sections.get("2", ""):
        say("No aging threshold or no date can be used, and the report still calls something aging.")
    if line_ids("3", "- Recorded as blocked, and not done (") != sorted(i for i, _ in model["blocked"]):
        say("Section 3 does not list as blocked exactly the items whose blocked_by names an item.")
    for identity, said in re.findall(r"^  - `([A-Z0-9-]+)`: `blocked_by` is ([^.]*)\.", sections.get("3", ""), re.M):
        real = dict(model["blocked"]).get(identity)
        if real is None or said != ", ".join(real):
            say("Section 3 gives %s blockers that are not the ones in its blocked_by." % identity)
    counted = {}
    for m in re.finditer(r"^- \"([^\"]*)\": (\d+) in progress \(([^)]*)\)\.(.*)$", sections.get("4", ""), re.M):
        counted[m.group(1)] = sorted(re.findall(r"`([A-Z0-9-]+)`", m.group(3)))
        if model["limit"] is not None:
            n = int(m.group(2))
            want = "this is %d more than the limit" % (n - model["limit"]) if n > model["limit"] else "this is at the limit" if n == model["limit"] else "this is %d under the limit" % (model["limit"] - n)
            if "The recorded limit is %d: %s." % (model["limit"], want) not in m.group(4):
                say("Section 4 does not set the count for \"%s\" beside the limit correctly." % m.group(1))
    if counted != {safe(p): sorted(v) for p, v in model["people"].items()}:
        say("Section 4 does not count, for each person, exactly the items in progress recorded against them.")
    if model["limit"] is None and "so no count is compared with one" not in sections.get("4", ""):
        say("No limit on work in progress can be used, and the report does not say so.")
    risky = sections.get("5", "").split("- Waits where none of D1")[0]
    pairs = sorted(re.findall(r"^  - `([A-Z0-9-]+)` waits on `([A-Z0-9-]+)` \(in its", risky, re.M))
    if pairs != sorted((r["x"], r["y"]) for r in model["risks"]):
        say("Section 5 does not list as risks exactly the waits that one of D1 to D4 holds for.")
    total = len(model["risks"]) + len(model["plain"]) + len(model["undecided"])
    if "- Waits in all: %d, on %d different items:" % (total, len(model["waited_on"])) not in sections.get("5", "") or "- Waits that are a risk (%d):" % len(model["risks"]) not in sections.get("5", ""):
        say("Section 5 does not give the number of waits, of items waited on, or of risks that the snapshot gives.")
    for line in [l for l in risky.split("\n") if l.startswith("  - `") and "(in its" in l]:
        if not re.search(r"\bD[1-4]: ", line):
            say("A dependency risk does not say why it is one: %s" % line[:60])
    entries = len(re.findall(r"^- \[GAP\] ", sections.get("6", ""), re.M))
    said = re.search(r"Entries: (\d+)\.", sections.get("6", ""))
    if entries != len(model["gaps"]) or not said or int(said.group(1)) != entries:
        say("Section 6 does not hold one entry for each gap in the snapshot, or its count is not the number of entries.")
    for g in model["gaps"]:
        if "- [GAP] `%s`, field `%s`:" % (g["what"], g["field"]) not in sections.get("6", ""):
            say("The gap in %s, field %s, is not in section 6." % (g["what"], g["field"]))
    for word in JUDGING:
        if re.search(r"(?<![a-z])%s" % re.escape(word), own_words.lower()):
            say("The report uses the word \"%s\". It is to count work and say nothing about a person." % word)
    return sorted(problems)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate or check a sprint health report from one snapshot.")
    parser.add_argument("command", choices=["generate", "check"])
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--previous")
    parser.add_argument("--out")
    parser.add_argument("--report")
    args = parser.parse_args(argv)
    if args.command == "generate":
        if not args.out:
            parser.error("generate needs --out")
        model, report = generate(args.snapshot, args.previous, args.out)
        print("wrote %s  sha256 %s" % (os.path.basename(args.out), hashlib.sha256(read_bytes(args.out)).hexdigest()))
        print("Items: %d. Done: %d. In progress: %d. Not started: %d. Aging: %d. Blocked: %d. Risks: %d. Gaps: %d." % (
            len(model["info"]), len(model["by_status"]["done"]), len(model["by_status"]["in_progress"]), len(model["by_status"]["todo"]), len(model["aging"]),
            len(model["blocked"]), len(model["risks"]), len(model["gaps"])))
        return 0
    if not args.report:
        parser.error("check needs --report")
    problems = check(args.snapshot, args.previous, args.report)
    for problem in problems:
        print("PROBLEM: %s" % problem)
    print("CHECK FAILED. %d problems." % len(problems) if problems else "CHECK PASSED. None of the things this check looks for was found. What it looks for is in SKILL.md.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
