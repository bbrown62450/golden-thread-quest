#!/usr/bin/env python3
"""Writes participant/context/dependencies/data.md: made-up work items and decisions for the dependency index.

    python3 participant/skills/context-dependency-map/make_data.py

Every record is invented. The project, a ferry timetable app, does not exist. It contacts nothing.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "..", "context", "dependencies", "data.md")


def work(identity, title, status, start=None, finish=None, **more):
    record = {"identity": identity, "kind": "work", "title": title, "status": status}
    if start:
        record["planned_start"], record["planned_finish"] = start, finish
    record.update(more)
    return record


def decision(identity, title, status, **more):
    record = {"identity": identity, "kind": "decision", "title": title, "status": status}
    record.update(more)
    return record


T1, T2, T3 = "trello:6a1f000000000000000d0001", "trello:6a1f000000000000000d0002", "trello:6a1f000000000000000d0003"
G1, G2, G3 = "github:I_kwFIXdep0001", "github:I_kwFIXdep0002", "github:I_kwFIXdep0003"

RECORDS = [
    # The long chain: schema, import, search, page, mobile, release notes.
    work("jira:52001", "Timetable schema", "in_progress", "2026-11-30", "2026-12-04", blocks=["jira:52002", "jira:52005"]),
    work("jira:52002", "Import operator timetables", "open", "2026-12-07", "2026-12-11", blocked_by=["jira:52001"], blocks=["jira:52003"]),
    work("jira:52003", "Search API", "open", "2026-12-14", "2026-12-18", blocked_by=["jira:52002"], blocks=["jira:52004"]),
    work("jira:52004", "Search page", "open", "2026-12-21", "2026-12-24", blocked_by=["jira:52003"], needs_decision=["decision:E-201"]),
    work(G1, "Mobile search screen", "open", "2026-12-28", "2027-01-08", blocked_by=["jira:52004"]),
    work(T1, "Release notes for search", "open", "2027-01-11", "2027-01-12", blocked_by=[G1, "jira:52009"]),
    work("jira:52005", "Fares page", "open", "2026-12-07", "2026-12-16", blocked_by=["jira:52001"], blocks=["jira:52006"]),
    work("jira:52006", "Fare calculator", "open", "2026-12-17", "2026-12-23", blocked_by=["jira:52005", "jira:52005"]),
    # A link written on the blocker only.
    work("jira:52007", "Operator logo licence check", "open", "2026-12-07", "2026-12-08", blocks=["jira:52008"]),
    work("jira:52008", "Operator logos on results", "open", "2026-12-07", "2026-12-09"),
    work("jira:52009", "Translate search screens", "open", "2026-12-28", "2027-01-06"),
    # The scenario: two stories wait on each other, and both are planned to start on the same Monday.
    work("jira:52010", "Saved journeys", "open", "2026-12-07", "2026-12-11", blocked_by=["jira:52011"]),
    work("jira:52011", "Account sign-in", "open", "2026-12-07", "2026-12-15", blocked_by=["jira:52010"]),
    work("jira:52012", "Journey alerts", "open", "2026-12-14", "2026-12-18", blocked_by=["jira:52010"]),
    # The scenario: a story waits on a decision that was never recorded.
    work("jira:52013", "Show live delays", "open", "2026-12-07", "2026-12-14", needs_decision=["decision:E-209"]),
    work("jira:52026", "Delay notifications", "open", "2026-12-15", "2026-12-18", blocked_by=["jira:52013"]),
    work("jira:52027", "Delay history chart", "open", "2026-12-15", "2026-12-17", needs_decision=["decision:E-209"]),
    # A cycle that passes through a decision.
    work("jira:52014", "Offline timetables", "open", "2026-12-14", "2026-12-22", needs_decision=["decision:E-203"]),
    work("jira:52015", "Spike: how large is a full timetable download?", "open", "2026-12-07", "2026-12-08", blocked_by=["jira:52014"]),
    # Waiting on a proposal.
    work("jira:52016", "Ticket purchase", "open", "2026-12-07", "2026-12-18", needs_decision=["decision:E-202"]),
    work("jira:52017", "Purchase receipts", "open", "2026-12-21", "2026-12-23", blocked_by=["jira:52016"]),
    # A target that is done, and one that was dropped.
    work("jira:52018", "Accessibility pass on search", "open", "2026-12-28", "2026-12-30", blocked_by=["jira:52019"]),
    work("jira:52019", "Colour contrast fixes", "done", "2026-11-23", "2026-11-27"),
    work("jira:52020", "Port map layer", "open", "2026-12-14", "2026-12-18", blocked_by=["jira:52021"]),
    work("jira:52021", "Licence the port map data", "dropped"),
    # Finished while what it waited on is not.
    work("jira:52022", "Search analytics events", "done", "2026-11-23", "2026-11-25", blocked_by=["jira:52003"]),
    # Links that point nowhere or cannot be read.
    work(T2, "Print timetable poster", "open", "2026-12-07", "2026-12-09", blocked_by=["jira:52999"]),
    work(T3, "Tidy the backlog board", "open", blocked_by=[T3]),
    work(G3, "Cache timetable responses", "open", "2026-12-14", "2026-12-16", blocked_by=["52001"]),
    # needs_decision that names a work item.
    work("jira:52025", "Import monitoring", "open", "2026-12-14", "2026-12-15", needs_decision=["jira:52002"]),
    # A superseded decision.
    work(G2, "Sign in with a ferry operator account", "open", "2026-12-14", "2026-12-18", needs_decision=["decision:E-204"]),
    # Wording, parents and relations. None of these is a dependency, and none is recorded as one.
    work("jira:52023", "Timetable PDF export, once the search API (jira:52003) is done", "open", "2026-12-07", "2026-12-10",
         description="Depends on jira:52003 and cannot start before the import, jira:52002, is finished.", labels=["search"]),
    work("jira:52024", "Schema documentation", "open", "2026-12-07", "2026-12-08", parent="jira:52001", related=["jira:52004"], labels=["search"]),
    work("jira:52028", "Epic: search", "open", parent=None, related=["jira:52003", "jira:52004", G1]),
    # Decisions.
    decision("decision:E-201", "Search results are ordered by departure time", "decided"),
    decision("decision:E-202", "Take card payments through a payment provider's hosted page", "proposal"),
    decision("decision:E-203", "How much timetable data may be kept on a phone?", "question", blocked_by=["jira:52015"]),
    decision("decision:E-204", "Sign-in is through operator accounts", "superseded", superseded_by="decision:E-205"),
    decision("decision:E-205", "Sign-in is by email link only", "decided"),
]

FIELDS = [
    ("`blocked_by`", "yes", "This record waits on each one named."),
    ("`blocks`", "yes", "Each one named waits on this record. The same link as `blocked_by`, written from the other end."),
    ("`needs_decision`", "yes", "This record waits on each decision named."),
    ("`parent`", "no", "Grouping. A child does not wait on its parent, and a parent is not said to wait on its children."),
    ("`related`", "no", "Somebody thought two items had to do with each other. It says nothing about order."),
    ("`superseded_by`", "no", "The decision that replaced this one."),
    ("`title`, `description`, `labels`", "no", "Words. A title that says \"once the search API is done\" records nothing."),
]


def text():
    out = ["# Dependency data: the ferry timetable app", "",
           "Written by `participant/skills/context-dependency-map/make_data.py`, at the participant's direction, for the quest",
           "`context-dependency-map`.", "",
           "**Everything here is made up.** The project, a ferry timetable app, does not exist. No identifier belongs to a real",
           "item. Records that hold text which reads like an instruction or a dependency are sample data, put there on purpose.", "",
           "## Identities", "",
           "A work item's identity is `system:identifier`, in the form fixed by `participant/context/identity/rules.md`. A decision's",
           "identity is `decision:` and its entry number, such as `decision:E-201`. A decision is a record like any other.", "",
           "## The fields, and which of them record a dependency", "",
           "| Field | Counted as a dependency | What it means |", "|---|---|---|"]
    out += ["| %s | %s | %s |" % row for row in FIELDS]
    out += ["", "A work item's `status` is `open`, `in_progress`, `done` or `dropped`. A decision's is `decided`, `proposal`, `question` or",
            "`superseded`. Dates are planned dates, as calendar days.", "",
            "## Every recorded link, and the field it comes from", "",
            "| Written on | Field | Names |", "|---|---|---|"]
    for record in RECORDS:
        for field in ("blocked_by", "blocks", "needs_decision"):
            for target in record.get(field, []):
                out.append("| `%s` | `%s` | `%s` |" % (record["identity"], field, target))
    out += ["", "Put there on purpose: two cycles, one of them through a decision; a work item and a decision that are named and have",
            "no record; an item that names itself; a link with no system in it; a link written twice; and links written on one end only.", "",
            "## The records", ""]
    for record in RECORDS:
        out += ["### %s" % record["identity"], "", "```json", json.dumps(record, indent=2, ensure_ascii=False), "```", ""]
    return "\n".join(out)


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(text())
    print("Wrote data.md: %d records." % len(RECORDS))


if __name__ == "__main__":
    main()
