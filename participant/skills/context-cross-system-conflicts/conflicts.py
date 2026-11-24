#!/usr/bin/env python3
"""Reports where systems disagree about the same work. It reports. It never resolves, and it never picks a winner.

    conflicts.py report [--records FILE] [--out FILE] [--previous FILE] [--state FILE]

It reads one Markdown file of linked records and writes a report. That is all it does. It has no code that changes a
record, in a file or in any system, and it opens the records file for reading only. It contacts nothing. It uses no
clock: every time in the report comes from the records, so the same input gives the same report on any day.

WHAT IS COMPARED
  Two records are compared only if a LINK says they are the same work. A link is a row in the records file's table of
  links, stated by a person, naming each record by its stable identity. A matching title is never a link.
  For each linked pair, four fields are compared, because all three systems can state them: status, title, whether
  anyone is assigned, and the due date.

THE FOUR ANSWERS for a pair of values
  agree            the two values are the same
  not comparable   they differ, and one system has no way to say what the other says (GitHub has no "in progress", and
                   no due date). A system saying the nearest thing it can is not disagreeing
  lag              they differ, and ALL of: both records say when they last changed; the gap between those two times is
                   more than nothing and at most LAG_HOURS; and, for status, the record that changed LATER is the one
                   that is FURTHER ALONG. The other side has probably not caught up yet
  conflict         they differ, and it is not one of the above

  "Lag" does not mean the later value is right. Neither value is changed, hidden or preferred under any of the four.

--previous FILE is the state file an earlier run wrote. With it, each conflict says whether it was there before.

Exit codes: 0 the report was written. 1 the command could not run, and nothing was written.
"""
import argparse
import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
FOLDER = os.path.join(REPO, "participant", "context", "conflicts")
SYSTEMS = ("jira", "trello", "github")
STATUSES = ("open", "in_progress", "done", "dropped")
LAG_HOURS = 24
FIELDS = ("status", "assigned", "due", "title")
# How far along a status is. done and dropped are both the end of the road, and they are not the same end.
ALONG = {"open": 0, "in_progress": 1, "done": 2, "dropped": 2}
# What a system has no way to say. The value it gives when it cannot say more is the nearest one it has.
CANNOT_SAY = {
    "github": {"status": {"in_progress": "open"}, "due": True},
}
WHY_CANNOT = {
    ("github", "status"): "GitHub has open and closed, and nothing between. An issue someone is working on is still \"open\"",
    ("github", "due"): "a GitHub issue has no due date",
}


class Stop(Exception):
    pass


def moment(value):
    """A time from a record as a moment, or None if it has none or it cannot be read."""
    if not isinstance(value, str):
        return None
    try:
        text = re.sub(r"([+-]\d\d)(\d\d)$", r"\1:\2", re.sub(r"Z$", "+00:00", value))
        when = datetime.datetime.fromisoformat(text)
        return when.astimezone(datetime.timezone.utc) if when.tzinfo else None
    except ValueError:
        return None


def show_gap(seconds):
    hours, rest = divmod(int(seconds), 3600)
    minutes, secs = divmod(rest, 60)
    parts = ["%d hour%s" % (hours, "" if hours == 1 else "s")] if hours else []
    parts += ["%d minute%s" % (minutes, "" if minutes == 1 else "s")] if minutes else []
    parts += ["%d second%s" % (secs, "" if secs == 1 else "s")] if secs or not parts else []
    return ", ".join(parts)


# ------------------------------------------------------------------ reading the records file

def read_records(text):
    """The records, the links and what depends on what, from the Markdown file. Nothing is changed or filled in."""
    records = {}
    for identity, block in re.findall(r"^### (\S+)[ \t]*\n(?:(?!### )[^\n]*\n)*?```json\n(.*?)\n```", text, re.M | re.S):
        try:
            record = json.loads(block)
        except ValueError:
            raise Stop("the record %s is not JSON" % identity)
        if record.get("identity") != identity:
            raise Stop("the record under the heading %s gives its identity as %s" % (identity, json.dumps(record.get("identity"))))
        if identity in records:
            raise Stop("the record %s is in the file twice" % identity)
        if record.get("system") not in SYSTEMS or not identity.startswith(record["system"] + ":"):
            raise Stop("the record %s does not belong to one of %s" % (identity, ", ".join(SYSTEMS)))
        if record.get("status") not in STATUSES:
            raise Stop("the record %s has the status %s, which is not one of %s" % (identity, json.dumps(record.get("status")), ", ".join(STATUSES)))
        records[identity] = record
    links = []
    table = re.search(r"^## Links\n(.*?)(?=^## )", text, re.M | re.S)
    for row in re.findall(r"^\| (W-\d+) \| ([^|]*) \| ([^|]*) \| ([^|]*) \| ([^|]*) \|$", table.group(1) if table else "", re.M):
        members = [cell.strip().strip("`") for cell in row[1:4] if cell.strip() not in ("", "none")]
        links.append({"work": row[0], "members": members, "stated": row[4].strip()})
    depends = {}
    table = re.search(r"^## What depends on what\n(.*?)(?=^## )", text, re.M | re.S)
    for work, needs in re.findall(r"^\| (W-\d+) \| ([^|]*) \|$", table.group(1) if table else "", re.M):
        depends[work] = [one.strip() for one in needs.split(",") if one.strip().startswith("W-")]
    if not records:
        raise Stop("the records file holds no records")
    return records, links, depends


def value_of(record, field):
    if field == "status":
        return record.get("status")
    if field == "assigned":
        count = record.get("assignee_count")
        return None if count is None else ("someone" if count > 0 else "nobody")
    if field == "due":
        due = record.get("due_at")
        return due[:10] if isinstance(due, str) else None
    return record.get("title")


def as_sent(record, field):
    """What the source itself wrote for this field, untouched. Shown beside the canonical value."""
    sent = record.get("as_sent") or {}
    return sent.get(field)


def cannot_say(record, field, other_value):
    """Why this record's system could not have said what the other record says, or None if it could."""
    limits = CANNOT_SAY.get(record["system"], {}).get(field)
    if limits is True:
        return WHY_CANNOT[(record["system"], field)] if value_of(record, field) is None else None
    if isinstance(limits, dict) and limits.get(other_value) == value_of(record, field):
        return WHY_CANNOT[(record["system"], field)]
    return None


def compare(first, second, field):
    """One pair of records on one field: (class, why, what a person would need to find out)."""
    a, b = value_of(first, field), value_of(second, field)
    name = lambda record: record["system"]
    if a == b:
        return "agree", "both say %s" % json.dumps(a), None
    if field == "title":
        return "different", "the two systems name the work differently", None
    for one, other, other_value in ((first, second, b), (second, first, a)):
        reason = cannot_say(one, field, other_value)
        if reason:
            return "not comparable", "%s. So %s saying %s is not a disagreement with %s saying %s" % (
                reason, name(one), json.dumps(value_of(one, field)), name(other), json.dumps(other_value)), None
    if a is None or b is None:
        silent = first if a is None else second
        return "conflict", "%s gives no value for this field and %s gives %s. A value against no value is a difference, and no rule here explains it" % (
            name(silent), name(second if a is None else first), json.dumps(b if a is None else a)), "whether %s was meant to have one" % name(silent)
    when_a, when_b = moment(first.get("updated_at")), moment(second.get("updated_at"))
    if when_a is None or when_b is None:
        silent = first if when_a is None else second
        return "conflict", "%s does not say when it last changed, so it cannot be told whether one side is merely behind" % name(silent), "when %s's record last changed" % name(silent)
    gap = abs((when_a - when_b).total_seconds())
    if gap == 0:
        return "conflict", "both records were last changed at the same moment and still differ, so neither is behind the other", "which of the two was meant, and who made each change"
    newer, older = (first, second) if when_a > when_b else (second, first)
    if field == "status" and ALONG[value_of(newer, field)] == ALONG[value_of(older, field)]:
        return "conflict", "%s says %s and %s says %s. Those are two different ends, and a delay does not turn one into the other" % (
            name(first), json.dumps(a), name(second), json.dumps(b)), "whether the work was finished or abandoned, and who decided"
    if field == "status" and ALONG[value_of(newer, field)] < ALONG[value_of(older, field)]:
        return "conflict", "%s changed LATER, by %s, and it is the one that is LESS far along (%s against %s). A delay cannot explain that: someone set %s back, or disagreed" % (
            name(newer), show_gap(gap), json.dumps(value_of(newer, field)), json.dumps(value_of(older, field)), name(newer)), \
            "who changed %s at %s, after %s had said %s, and why" % (name(newer), newer["updated_at"], name(older), json.dumps(value_of(older, field)))
    if gap > LAG_HOURS * 3600:
        return "conflict", "the two records last changed %s apart, which is more than the %d hours allowed for one side to catch up" % (show_gap(gap), LAG_HOURS), \
            "why %s has not changed since %s while %s has, and who keeps each of the two up to date" % (name(older), older["updated_at"], name(newer))
    extra = ", and it is the one further along" if field == "status" else ""
    return "lag", "%s changed %s after %s%s. That is within %d hours, so %s may simply not have caught up" % (name(newer), show_gap(gap), name(older), extra, LAG_HOURS, name(older)), None


# ------------------------------------------------------------------ the report

def analyse(records, links, depends, previous=None):
    """Everything the report says, as data. Sorted, so that the order of the input changes nothing."""
    problems, seen_in = [], {}
    for link in links:
        for identity in link["members"]:
            seen_in.setdefault(identity, []).append(link["work"])
    twice = sorted(identity for identity, works in seen_in.items() if len(works) > 1)
    works = []
    for link in sorted(links, key=lambda one: one["work"]):
        missing = [identity for identity in link["members"] if identity not in records]
        shared = [identity for identity in link["members"] if identity in twice]
        systems = [identity.split(":")[0] for identity in link["members"]]
        if missing:
            problems.append((link["work"], "its link names %s, and there is no such record here. It is not compared" % ", ".join(missing)))
        elif shared:
            problems.append((link["work"], "its link names %s, which another link names too (%s). One record cannot be two pieces of work. Neither link is compared"
                             % (", ".join(shared), ", ".join(sorted(set(w for i in shared for w in seen_in[i]) - {link["work"]})))))
        elif len(set(systems)) != len(systems):
            problems.append((link["work"], "its link names two records from the same system. This report compares across systems. It is not compared"))
        elif len(link["members"]) < 2:
            problems.append((link["work"], "its link names one record only, so there is nothing to compare it with"))
        else:
            members = sorted((records[identity] for identity in link["members"]), key=lambda record: SYSTEMS.index(record["system"]))
            pairs = []
            for field in FIELDS:
                for at, first in enumerate(members):
                    for second in members[at + 1:]:
                        kind, why, to_find = compare(first, second, field)
                        pairs.append({"field": field, "a": first["identity"], "b": second["identity"], "class": kind, "why": why, "find_out": to_find})
            works.append({"work": link["work"], "members": [record["identity"] for record in members], "stated": link["stated"], "pairs": pairs})
    linked = set(identity for work in works for identity in work["members"])
    unlinked = sorted(identity for identity in records if identity not in linked)

    def downstream(work, seen=None):
        seen = set() if seen is None else seen
        for other, needs in depends.items():
            if work in needs and other not in seen:
                seen.add(other)
                downstream(other, seen)
        return seen
    affected = {work["work"]: sorted(downstream(work["work"])) for work in works}
    before = set(tuple(one) for one in (previous or {}).get("conflicts", []))
    conflicts = []
    for work in works:
        for pair in work["pairs"]:
            if pair["class"] == "conflict":
                key = (work["work"], pair["field"], pair["a"], pair["b"], json.dumps(value_of(records[pair["a"]], pair["field"])), json.dumps(value_of(records[pair["b"]], pair["field"])))
                conflicts.append(dict(pair, work=work["work"], key=key, affects=affected[work["work"]],
                                      seen_before=None if previous is None else key in before))
    conflicts.sort(key=lambda one: (-len(one["affects"]), one["work"], FIELDS.index(one["field"]), one["a"], one["b"]))
    hints = {}
    for identity in unlinked:
        hints.setdefault(records[identity].get("title"), []).append(identity)
    same_title = sorted((title, sorted(found)) for title, found in hints.items() if title and len(set(one.split(":")[0] for one in found)) > 1)
    return {"works": works, "conflicts": conflicts, "unlinked": unlinked, "problems": sorted(problems), "same_title": same_title, "affected": affected}


def cell(value):
    return "none" if value is None else ("`%s`" % json.dumps(value, ensure_ascii=False)).replace("|", "\\|")


def render(records, found, previous_named):
    by_class = lambda kind: [(work, pair) for work in found["works"] for pair in work["pairs"] if pair["class"] == kind]
    row = lambda identity, field: "| %s | `%s` | %s | %s | %s |" % (records[identity]["system"], identity, cell(value_of(records[identity], field)),
                                                                   cell(as_sent(records[identity], field)), records[identity].get("updated_at") or "**not stated**")
    lines = [
        "# Conflict report: where the systems disagree about the same work", "",
        "Written by `participant/skills/context-cross-system-conflicts/conflicts.py report` from `records.md`. Do not edit this file: the next run replaces it.",
        "**Every record is made up.**", "",
        "**This report resolves nothing.** It shows what each system says and when it last said it. It does not say which system is right, it changes no record, and it",
        "gives no single \"true\" state for any piece of work. Where two systems differ, both values are shown, side by side, as each system wrote them.", "",
        "## How to read it", "",
        "Two records are compared only when a **link** in `records.md` says they are the same work. A link is stated by a person and names each record by its stable",
        "identity. A matching title is never a link. Four fields are compared: status, whether anyone is assigned, the due date, and the title.", "",
        "Each pair of values gets one of these answers:", "",
        "| Answer | When |", "|---|---|",
        "| **agree** | The two values are the same |",
        "| **not comparable** | They differ, and one system has no way to say what the other says. GitHub has no \"in progress\" and no due date |",
        "| **lag** | They differ, and all of: both records say when they last changed; those two times are more than nothing and at most **%d hours** apart; and, for status, the record that changed **later** is the one **further along** |" % LAG_HOURS,
        "| **conflict** | They differ, and it is none of the above |", "",
        "The %d hours are measured **between the two records' own times**, not from today. So this report does not change as days pass." % LAG_HOURS,
        "\"Further along\" means: open, then in progress, then done or dropped. Done and dropped are two different ends, so one against the other is always a conflict.", "",
        "**\"Lag\" does not mean the later value is the true one.** It means the pattern fits a delay. Both values are still shown.", "",
        "## Summary", "",
        "- pieces of work compared: %d" % len(found["works"]),
        "- conflicts: %d, in %d pieces of work" % (len(found["conflicts"]), len(set(one["work"] for one in found["conflicts"]))),
        "- differences judged to be lag: %d" % len(by_class("lag")),
        "- differences that are not comparable: %d" % len(by_class("not comparable")),
        "- records with no counterpart: %d" % len(found["unlinked"]),
        "- links that could not be used: %d" % len(found["problems"]), "",
        "## Conflicts", "",
        "Ordered by how many other pieces of work depend on the one in conflict, most first. The order says how much is waiting on an answer. It does not say which",
        "conflict is more likely to matter, and it says nothing about which side is right.", ""]
    if not found["conflicts"]:
        lines += ["None.", ""]
    for number, one in enumerate(found["conflicts"], 1):
        lines += ["### %d. %s: %s" % (number, one["work"], one["field"]), "",
                  "| System | Record | Says | As the source wrote it | Last changed |", "|---|---|---|---|---|", row(one["a"], one["field"]), row(one["b"], one["field"]), "",
                  "- **Why it is a conflict:** %s." % one["why"],
                  "- **To settle it, a person would need to find out:** %s." % one["find_out"],
                  "- **Other work that depends on this:** %s" % (", ".join(one["affects"]) if one["affects"] else "none recorded")]
        if previous_named:
            lines.append("- **Seen before:** %s" % ("yes. The same two values were in conflict in the previous run, %s" % previous_named if one["seen_before"]
                                                   else "no. This is new since the previous run, %s" % previous_named))
        lines.append("")
    lines += ["## Differences judged to be lag", "", "These differ, and the pattern fits one side not having caught up yet. Neither value is treated as the true one.", ""]
    if by_class("lag"):
        lines += ["| Work | Field | System | Says | As the source wrote it | Last changed | Why it is lag, not conflict |", "|---|---|---|---|---|---|---|"]
        for work, pair in by_class("lag"):
            for at, identity in enumerate((pair["a"], pair["b"])):
                record = records[identity]
                lines.append("| %s | %s | %s | %s | %s | %s | %s |" % (work["work"] if at == 0 else "", pair["field"] if at == 0 else "", record["system"], cell(value_of(record, pair["field"])),
                                                                      cell(as_sent(record, pair["field"])), record.get("updated_at"), pair["why"] + "." if at == 0 else ""))
    else:
        lines.append("None.")
    lines += ["", "## Differences that are not comparable", "", "One system cannot say what the other says. These are not disagreements.", ""]
    if by_class("not comparable"):
        lines += ["| Work | Field | First | Second | Why |", "|---|---|---|---|---|"]
        lines += ["| %s | %s | %s: %s | %s: %s | %s. |" % (work["work"], pair["field"], records[pair["a"]]["system"], cell(value_of(records[pair["a"]], pair["field"])),
                                                           records[pair["b"]]["system"], cell(value_of(records[pair["b"]], pair["field"])), pair["why"]) for work, pair in by_class("not comparable")]
    else:
        lines.append("None.")
    lines += ["", "## Titles that differ", "", "Linked records that name the same work differently. This is ordinary, and is not a conflict of state.", ""]
    if by_class("different"):
        lines += ["| Work | First | Second |", "|---|---|---|"]
        lines += ["| %s | %s: %s | %s: %s |" % (work["work"], records[pair["a"]]["system"], cell(records[pair["a"]]["title"]), records[pair["b"]]["system"], cell(records[pair["b"]]["title"]))
                  for work, pair in by_class("different")]
    else:
        lines.append("None.")
    lines += ["", "## Unlinked records", "", "A record that no usable link ties to a record in another system. It is not compared with anything, and it is **not a conflict**: there is nothing for it to",
              "disagree with. It may be work that lives in one system only, or work nobody has linked yet.", ""]
    if found["unlinked"]:
        lines += ["| Record | System | Title | Status | Last changed |", "|---|---|---|---|---|"]
        lines += ["| `%s` | %s | %s | %s | %s |" % (identity, records[identity]["system"], cell(records[identity].get("title")), cell(records[identity]["status"]), records[identity].get("updated_at") or "not stated")
                  for identity in found["unlinked"]]
    else:
        lines.append("None.")
    lines += ["", "### Links that could not be used", ""]
    lines += ["- %s: %s." % problem for problem in found["problems"]] or ["None."]
    lines += ["", "### Same title, not linked", "", "Unlinked records in different systems that happen to have the same title. **This is a hint for a person, not a link.** They were not compared. If they are the",
              "same work, a person can add a link to `records.md`.", ""]
    lines += ["- %s: %s" % (cell(title), ", ".join("`%s`" % one for one in found)) for title, found in found["same_title"]] or ["None."]
    lines += ["", "## Every comparison made", "", "So that a reader can see why each pair was or was not called a conflict.", "",
              "| Work | Field | First | Second | Answer | Why |", "|---|---|---|---|---|---|"]
    for work in found["works"]:
        for pair in work["pairs"]:
            lines.append("| %s | %s | %s: %s | %s: %s | %s | %s |" % (work["work"], pair["field"], records[pair["a"]]["system"], cell(value_of(records[pair["a"]], pair["field"])),
                                                                     records[pair["b"]]["system"], cell(value_of(records[pair["b"]], pair["field"])),
                                                                     "**conflict**" if pair["class"] == "conflict" else pair["class"], pair["why"].replace("|", "\\|")))
    lines += ["", "## The links used", "", "| Work | Records | Stated by |", "|---|---|---|"]
    lines += ["| %s | %s | %s |" % (work["work"], ", ".join("`%s`" % one for one in work["members"]), work["stated"]) for work in found["works"]]
    return "\n".join(lines) + "\n"


def read(path):
    try:
        with open(path, encoding="utf-8") as f:          # read only
            return f.read()
    except OSError as error:
        raise Stop("%s could not be read: %s" % (os.path.basename(path), error.strerror))


def write(path, text, records_path):
    if os.path.abspath(path) == os.path.abspath(records_path):
        raise Stop("refused to write over the records file")
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path + ".tmp", "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    os.replace(path + ".tmp", path)


def main(argv=None, say=print):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("command", choices=("report",))
    parser.add_argument("--records", default=os.path.join(FOLDER, "records.md"))
    parser.add_argument("--out", default=os.path.join(FOLDER, "report.md"))
    parser.add_argument("--previous")
    parser.add_argument("--state")
    args = parser.parse_args(argv)
    try:
        records, links, depends = read_records(read(args.records))
        previous = None
        if args.previous:
            try:
                previous = json.loads(read(args.previous))
            except ValueError:
                raise Stop("the previous run's state file is not JSON")
        found = analyse(records, links, depends, previous)
        write(args.out, render(records, found, (previous or {}).get("run")), args.records)
        if args.state:
            name = re.search(r"^Run: (.+)$", read(args.records), re.M)
            write(args.state, json.dumps({"run": name.group(1).strip() if name else "unnamed", "conflicts": [list(one["key"]) for one in found["conflicts"]]}, indent=1) + "\n", args.records)
        count = lambda kind: sum(1 for work in found["works"] for pair in work["pairs"] if pair["class"] == kind)
        say("conflicts: read %d records and %d links. Compared %d pieces of work, field by field" % (len(records), len(links), len(found["works"])))
        say("conflicts: %d conflicts, %d lag, %d not comparable, %d agree, %d titles that differ" % (len(found["conflicts"]), count("lag"), count("not comparable"), count("agree"), count("different")))
        say("conflicts: %d unlinked records, %d links that could not be used" % (len(found["unlinked"]), len(found["problems"])))
        if previous is not None:
            say("conflicts: against the previous run, %s: %d of the conflicts were already there, %d are new"
                % (previous.get("run"), sum(1 for one in found["conflicts"] if one["seen_before"]), sum(1 for one in found["conflicts"] if not one["seen_before"])))
        say("conflicts: wrote the report. No record was changed, and no value was chosen over another")
        return 0
    except Stop as error:
        say("conflicts: STOPPED: %s" % error)
        return 1


if __name__ == "__main__":
    sys.exit(main())
