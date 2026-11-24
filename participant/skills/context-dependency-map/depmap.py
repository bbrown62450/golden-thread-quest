#!/usr/bin/env python3
"""Dependency index for work items and decisions. Local files only. It contacts nothing and changes no record.

    python3 participant/skills/context-dependency-map/depmap.py build [--data FILE] [--out FILE]
    python3 participant/skills/context-dependency-map/depmap.py slip IDENTITY DAYS [--data FILE]

build  reads the records in data.md and writes index.md: what each item waits on, what waits on each item,
       every problem found, the five items blocking the most, and the longest chain.
       Exit code 0: built, nothing to report. 1: built, and problems are reported. 2: not built.
slip   prints what moves if one item finishes DAYS later than planned.

A dependency is read from three fields only: blocked_by, blocks and needs_decision. No title, description,
label, parent or related field is ever read for one.
"""
import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FOLDER = os.path.abspath(os.path.join(HERE, "..", "..", "context", "dependencies"))

LINK_FIELDS = ("blocked_by", "blocks", "needs_decision")     # the only fields a dependency comes from
SEEN_NOT_COUNTED = ("parent", "related")                     # recorded, shown, never counted
IDENTITY = re.compile(r"^(jira|trello|github|decision):[A-Za-z0-9_\-=+/.]+$")
FINISHED = {"work": ("done",), "decision": ("decided",)}
GONE = {"work": ("dropped",), "decision": ("superseded",)}
UNDECIDED = ("proposal", "question")
TOP = 5


class DataError(Exception):
    pass


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------- reading

def read_records(text):
    """The records of data.md: a '### identity' heading followed by one fenced json block."""
    records = {}
    for heading, body in re.findall(r"^### (\S+)\n+```json\n(.*?)\n```", text, re.M | re.S):
        try:
            record = json.loads(body)
        except ValueError as error:
            raise DataError("The record under %s is not valid JSON: %s" % (heading, error))
        if not isinstance(record, dict) or record.get("identity") != heading:
            raise DataError("The record under %s does not carry that identity." % heading)
        if not IDENTITY.match(heading):
            raise DataError("%s is not an identity these rules cover." % heading)
        if heading in records:
            raise DataError("Two records have the identity %s. Which one a link means cannot be told." % heading)
        if record.get("kind") not in FINISHED:
            raise DataError("%s has no kind, or a kind that is neither work nor decision." % heading)
        records[heading] = record
    if not records:
        raise DataError("No records could be read.")
    return records


def day(value):
    try:
        return datetime.date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------- the model

def state_of(identity, records):
    """finished, gone, undecided, waiting or missing."""
    record = records.get(identity)
    if record is None:
        return "missing"
    status = record.get("status")
    if status in FINISHED[record["kind"]]:
        return "finished"
    if status in GONE[record["kind"]]:
        return "gone"
    if record["kind"] == "decision" and status in UNDECIDED:
        return "undecided"
    return "waiting"


def analyse(records):
    """Everything the index says, as plain data. Nothing here depends on the order of the input."""
    links, unreadable = {}, []                     # links: (waiter, target) -> set of (field, written on)
    for identity in sorted(records):
        record = records[identity]
        for field in LINK_FIELDS:
            if field not in record:
                continue
            value = record[field]
            if not isinstance(value, list):
                unreadable.append((identity, field, json.dumps(value), "the field is not a list"))
                continue
            for named in value:
                if not isinstance(named, str) or not IDENTITY.match(named):
                    unreadable.append((identity, field, json.dumps(named), "it is not an identity, so nothing is guessed from it"))
                    continue
                pair = (named, identity) if field == "blocks" else (identity, named)
                links.setdefault(pair, set()).add((field, identity))
    nodes = sorted(set(records) | {n for pair in links for n in pair})
    state = {n: state_of(n, records) for n in nodes}
    waits_on = {n: sorted(t for (w, t) in links if w == n) for n in nodes}
    waited_by = {n: sorted(w for (w, t) in links if t == n) for n in nodes}

    def open_link(waiter, target):
        """The waiter is still held up by the target."""
        return state[target] != "finished"

    def active(n):
        return state[n] in ("waiting", "undecided")

    # Cycles: Tarjan's strongly connected components, over every recorded link.
    index, low, on_stack, stack, components, counter = {}, {}, set(), [], [], [0]

    def visit(n):
        index[n] = low[n] = counter[0]
        counter[0] += 1
        stack.append(n)
        on_stack.add(n)
        for t in waits_on[n]:
            if t not in index:
                visit(t)
                low[n] = min(low[n], low[t])
            elif t in on_stack:
                low[n] = min(low[n], index[t])
        if low[n] == index[n]:
            members = []
            while True:
                m = stack.pop()
                on_stack.discard(m)
                members.append(m)
                if m == n:
                    break
            components.append(sorted(members))
    for n in nodes:
        if n not in index:
            visit(n)
    cycles = sorted(c for c in components if len(c) > 1)
    self_links = sorted(n for n in nodes if (n, n) in links)
    in_cycle = {n for c in cycles for n in c} | set(self_links)

    def walk(members):
        """One shortest way round, starting from the first member."""
        start, inside = members[0], set(members)
        paths = [[start]]
        while paths:
            path = paths.pop(0)
            for t in waits_on[path[-1]]:
                if t == start:
                    return path + [start]
                if t in inside and t not in path:
                    paths.append(path + [t])
        return members + [start]

    # What each item blocks: everything still to do that cannot finish until it is done.
    def blocked_by(n):
        found, queue = set(), [n]
        while queue:
            current = queue.pop()
            for w in waited_by[current]:
                if w not in found and w != n and active(w) and open_link(w, current):
                    found.add(w)
                    queue.append(w)
        return sorted(found)
    blocked = {n: blocked_by(n) for n in nodes if state[n] != "finished"}
    direct = {n: sorted(w for w in waited_by[n] if w != n and active(w)) for n in blocked}
    ranked = sorted((n for n in blocked if blocked[n]), key=lambda n: (-len(blocked[n]), -len(direct[n]), n))
    top = ranked[:TOP]
    level = [n for n in ranked[TOP:] if top and len(blocked[n]) == len(blocked[top[-1]])]

    # The longest chain of waiting that does not pass through a cycle.
    memo = {}

    def chain(n):
        if n not in memo:
            best = [n]
            for t in waits_on[n]:
                if t not in in_cycle and open_link(n, t) and state[t] != "gone":
                    candidate = [n] + chain(t)
                    if len(candidate) > len(best) or (len(candidate) == len(best) and candidate < best):
                        best = candidate
            memo[n] = best
        return memo[n]
    chains = [chain(n) for n in nodes if n not in in_cycle and active(n)]
    longest = sorted(chains, key=lambda c: (-len(c), c))[0] if chains else []

    # Problems, each named.
    problems = {"cycles": [(c, walk(c)) for c in cycles], "self": self_links,
                "missing": [(n, waited_by[n]) for n in nodes if state[n] == "missing"],
                "unreadable": sorted(unreadable),
                "gone": sorted((w, t) for (w, t) in links if state[t] == "gone" and active(w)),
                "undecided": sorted((w, t) for (w, t) in links if state[t] == "undecided" and active(w)),
                "wrong_kind": sorted((w, t) for (w, t), sources in links.items()
                                     if any(f == "needs_decision" for f, _ in sources) and t in records and records[t]["kind"] != "decision"),
                "finished_early": sorted((w, t) for (w, t) in links if state[w] == "finished" and state[t] != "finished"),
                "too_early": []}
    for (w, t) in sorted(links):
        if active(w) and open_link(w, t) and w in records and t in records and w != t:
            start, finish = day(records[w].get("planned_start")), day(records[t].get("planned_finish"))
            if start and finish and start <= finish:
                problems["too_early"].append((w, t, start.isoformat(), finish.isoformat()))
    one_sided = sorted((w, t, sorted(sources)[0]) for (w, t), sources in links.items()
                       if len(sources) == 1 and next(iter(sources))[0] != "needs_decision" and w in records and t in records and w != t)
    not_counted = sorted((n, field, json.dumps(records[n][field])) for n in records for field in SEEN_NOT_COUNTED if records[n].get(field))
    return {"records": records, "nodes": nodes, "links": links, "state": state, "waits_on": waits_on, "waited_by": waited_by,
            "cycles": cycles, "in_cycle": in_cycle, "blocked": blocked, "direct": direct, "top": top, "level": level,
            "longest": longest, "problems": problems, "one_sided": one_sided, "not_counted": not_counted}


def problem_count(found):
    return sum(len(v) for v in found["problems"].values())


def schedule(found, slipped=None, days=0):
    """Earliest start and finish of each dated work item. None for one that cannot be dated."""
    records, state, memo = found["records"], found["state"], {}
    undatable = set(found["in_cycle"])

    def dates(n):
        if n in memo:
            return memo[n]
        memo[n] = None
        record = records.get(n, {})
        start, finish = day(record.get("planned_start")), day(record.get("planned_finish"))
        if n in undatable or not start or not finish:
            return None
        for t in found["waits_on"][n]:
            if state[t] == "finished" or t == n:
                continue
            if t in found["in_cycle"] or (t in records and day(records[t].get("planned_start")) and dates(t) is None):
                return None                                    # it waits, directly or not, on a cycle
            got = dates(t)
            if got and got[1] >= start:
                finish = finish + (got[1] + datetime.timedelta(days=1) - start)
                start = got[1] + datetime.timedelta(days=1)
        if n == slipped:
            finish = finish + datetime.timedelta(days=days)
        memo[n] = (start, finish)
        return memo[n]
    return {n: dates(n) for n in found["nodes"]}


def slip(found, identity, days):
    """What moves if identity finishes days later. Rows of (item, start before, start after, days pushed)."""
    before, after = schedule(found), schedule(found, identity, days)
    rows = []
    for n in found["blocked"].get(identity, []):
        if before[n] is None or after[n] is None:
            rows.append((n, None, None, None))
        else:
            rows.append((n, before[n][0].isoformat(), after[n][0].isoformat(), (after[n][0] - before[n][0]).days))
    return rows


# ---------------------------------------------------------------- writing

STATE_WORDS = {"finished": "satisfied", "waiting": "waiting", "undecided": "NOT DECIDED", "missing": "NOT FOUND", "gone": "DROPPED OR SUPERSEDED"}


def render(found):
    records, state, links = found["records"], found["state"], found["links"]

    def name(n):
        return "`%s` %s" % (n, "\"%s\"" % records[n]["title"].replace("|", "/") if n in records else "(no record)")

    def source(pair):
        return "; ".join("`%s` on `%s`" % s for s in sorted(links[pair]))

    def plural(n, word):
        return "%d %s%s" % (n, word, "" if n == 1 else "s")

    p = found["problems"]
    out = ["# Dependency index", "",
           "Written by `participant/skills/context-dependency-map/depmap.py build` from `data.md`. Do not edit it: build it again.",
           "The data is made up.", "",
           "A link is read from three fields only: `blocked_by`, `blocks` and `needs_decision`. A decision is an item like any",
           "other. Nothing is read from a title, a description, a label, a parent or a `related` field.", "",
           "## Summary", "",
           "- Records: %d (%d work items, %d decisions). Named in a link and not found: %d." % (
               len(records), sum(1 for r in records.values() if r["kind"] == "work"), sum(1 for r in records.values() if r["kind"] == "decision"), len(p["missing"])),
           "- Links: %d. Still holding something up: %d." % (len(links), sum(1 for (w, t) in links if state[t] != "finished")),
           "- Problems reported below: %d." % problem_count(found), "",
           "## Problems", ""]

    def section(title, rows, none="None."):
        out.extend(["### %s" % title, ""] + (rows or [none]) + [""])
    section("Cycles: items that wait on each other", [
        "- **CYCLE of %d:** %s. One way round: %s." % (len(members), ", ".join(name(m) for m in members), " waits on ".join("`%s`" % m for m in way))
        for members, way in p["cycles"]])
    section("An item that waits on itself", ["- **SELF:** %s names itself (%s)." % (name(n), source((n, n))) for n in p["self"]])
    section("Links to something that has no record", [
        "- **NOT FOUND:** `%s` has no record. Named by: %s." % (n, "; ".join("%s (%s)" % (name(w), source((w, n))) for w in waiters))
        for n, waiters in p["missing"]])
    section("Links that could not be read", [
        "- **UNREADABLE:** `%s` on %s holds %s: %s." % (field, name(n), "`%s`" % value, why) for n, field, value, why in p["unreadable"]])
    section("Waiting on a decision that has not been made", [
        "- **NOT DECIDED:** %s waits on %s, which is a %s." % (name(w), name(t), records[t]["status"]) for w, t in p["undecided"]])
    section("Waiting on something dropped or superseded", [
        "- **WILL NEVER FINISH:** %s waits on %s, which is %s%s." % (
            name(w), name(t), records[t]["status"], " by `%s`" % records[t]["superseded_by"] if records[t].get("superseded_by") else "") for w, t in p["gone"]])
    section("`needs_decision` that names something other than a decision", [
        "- **NOT A DECISION:** %s names %s in `needs_decision`. The link is kept." % (name(w), name(t)) for w, t in p["wrong_kind"]])
    section("Finished while what it waited on is not", ["- **OUT OF ORDER:** %s is finished, and %s is not." % (name(w), name(t)) for w, t in p["finished_early"]])
    section("Planned to start before what it waits on is planned to finish", [
        "- **TOO EARLY:** %s is planned to start on %s. It waits on %s, planned to finish on %s." % (name(w), start, name(t), finish)
        for w, t, start, finish in p["too_early"]])

    out += ["## The %d items blocking the most" % TOP, "",
            "An item blocks every item still to do that cannot finish until it is done: those waiting on it, those waiting on",
            "them, and so on. An item that is done blocks nothing. Equal totals are ordered by the direct count, then by identity.", "",
            "| Place | Item | Blocks in all | Of those, directly | Note |", "|---|---|---|---|---|"]
    for place, n in enumerate(found["top"], 1):
        note = [word for word, yes in (("in a cycle", n in found["in_cycle"]), ("NOT FOUND", state[n] == "missing"),
                                       ("NOT DECIDED", state[n] == "undecided"), ("dropped or superseded", state[n] == "gone")) if yes]
        out.append("| %d | %s | %d | %d | %s |" % (place, name(n), len(found["blocked"][n]), len(found["direct"][n]), ", ".join(note) or "-"))
    if found["level"]:
        out += ["", "%s the same total as fifth place and %s not listed: %s." % (
            plural(len(found["level"]), "more item") + (" has" if len(found["level"]) == 1 else " have"),
            "is" if len(found["level"]) == 1 else "are", ", ".join("`%s`" % n for n in found["level"]))]

    out += ["", "## The longest chain", "",
            "The longest run of items still to do in which each waits on the next. Chains through a cycle are left out, since a",
            "cycle has no end.", ""]
    out += ["%s, each waiting on the next:" % plural(len(found["longest"]), "item"), ""] if found["longest"] else ["None."]
    out += ["%d. %s" % (i, name(n)) for i, n in enumerate(found["longest"], 1)]

    if found["top"]:
        first = found["top"][0]
        rows = slip(found, first, 5)
        out += ["", "## If one item slips", "",
                "If %s finishes 5 days later than planned, this is what happens to everything it blocks. Dates are calendar" % name(first),
                "days. An item moves only as far as it must. `depmap.py slip IDENTITY DAYS` does the same for any item.", "",
                "| Item | Earliest start now | Earliest start after the slip | Pushed by |", "|---|---|---|---|"]
        out += ["| %s | %s | %s | %s |" % (name(n), a or "cannot be dated", b or "cannot be dated", "-" if d is None else plural(d, "day")) for n, a, b, d in rows]

    def index(title, intro, table, wording):
        out.extend(["", "## %s" % title, "", intro, ""])
        for n in found["nodes"]:
            others = table[n]
            out.append("### %s" % name(n))
            out.append("")
            if state[n] == "missing":
                out.append("**NOT FOUND: nothing in the data has this identity.**")
            elif n in records:
                out.append("Status: %s." % records[n]["status"])
            out.extend(["- %s %s. %s. From %s." % (wording, name(o), STATE_WORDS[state[o if table is found["waits_on"] else n]],
                                                 source((n, o) if table is found["waits_on"] else (o, n))) for o in others] or ["- Nothing."])
            out.append("")
        out.pop()
    index("Forward index: what each item waits on",
          "For each item, everything it waits on, whether that still holds it up, and the field the link was read from.", found["waits_on"], "Waits on")
    index("Reverse index: what waits on each item",
          "For each item, everything waiting on it. This is the answer to \"who is waiting on me?\".", found["waited_by"], "Waited on by")

    out += ["", "## Links written at one end only", "",
            "Not a fault in themselves. Each is a link that somebody looking only at the other record would not see.", ""]
    out += ["- %s waits on %s. Written only as `%s` on `%s`." % (name(w), name(t), s[0], s[1]) for w, t, s in found["one_sided"]] or ["None."]
    out += ["", "## Seen and not counted", "",
            "Fields that name another item and do not record a dependency. They are listed so that a reader can see they were",
            "noticed. No link was made from any of them.", ""]
    out += ["- `%s` on %s: `%s`" % (field, name(n), value) for n, field, value in found["not_counted"]] or ["None."]
    return "\n".join(out) + "\n"


def main(argv=None, say=print):
    argv = sys.argv[1:] if argv is None else argv

    def option(flag, default):
        return argv[argv.index(flag) + 1] if flag in argv else default
    data = option("--data", os.path.join(FOLDER, "data.md"))
    if argv[:1] not in (["build"], ["slip"]):
        say(__doc__.strip())
        return 2
    try:
        found = analyse(read_records(read(data)))
    except (OSError, DataError) as error:
        say("NOT BUILT. %s" % (error if isinstance(error, DataError) else "The data file could not be read."))
        return 2
    if argv[0] == "slip":
        if len(argv) < 3 or argv[1] not in found["records"] or not re.fullmatch(r"\d+", argv[2]):
            say("slip needs the identity of a record and a whole number of days.")
            return 2
        rows = slip(found, argv[1], int(argv[2]))
        say("If %s finishes %s days later than planned:" % (argv[1], argv[2]))
        for n, before, after, pushed in rows:
            say("  %-34s %s" % (n, "cannot be dated" if pushed is None else "earliest start %s -> %s, pushed %d day%s" % (before, after, pushed, "" if pushed == 1 else "s")))
        if not rows:
            say("  Nothing still to do waits on it.")
        return 0
    out = option("--out", os.path.join(os.path.dirname(os.path.abspath(data)), "index.md"))
    if os.path.abspath(out) == os.path.abspath(data):
        say("NOT BUILT. Refused to write the index over the data file.")
        return 2
    with open(out, "w", encoding="utf-8") as f:
        f.write(render(found))
    p = found["problems"]
    say("Read %d records and %d links." % (len(found["records"]), len(found["links"])))
    for members, way in p["cycles"]:
        say("CYCLE: %s" % " waits on ".join(way))
    for n in p["self"]:
        say("SELF: %s waits on itself" % n)
    for n, waiters in p["missing"]:
        say("NOT FOUND: %s, named by %s" % (n, ", ".join(waiters)))
    for n, field, value, why in p["unreadable"]:
        say("UNREADABLE: %s on %s holds %s" % (field, n, value))
    for key, word in (("undecided", "NOT DECIDED"), ("gone", "WILL NEVER FINISH"), ("wrong_kind", "NOT A DECISION"), ("finished_early", "OUT OF ORDER")):
        for w, t in p[key]:
            say("%s: %s waits on %s" % (word, w, t))
    for w, t, start, finish in p["too_early"]:
        say("TOO EARLY: %s starts %s, and waits on %s, which finishes %s" % (w, start, t, finish))
    say("Blocking the most: %s" % (", ".join("%s (%d)" % (n, len(found["blocked"][n])) for n in found["top"]) or "nothing"))
    say("Longest chain: %d items: %s" % (len(found["longest"]), " <- ".join(reversed(found["longest"]))))
    count = problem_count(found)
    say("Wrote index.md. %s" % ("PROBLEMS REPORTED: %d." % count if count else "Nothing to report."))
    return 1 if count else 0


if __name__ == "__main__":
    sys.exit(main())
