#!/usr/bin/env python3
"""Writes participant/context/next-work/inputs.md: made-up work items and decisions to be ranked.

    python3 participant/skills/context-next-work/make_inputs.py

Every record is invented. The project, a school meals ordering app, does not exist. It contacts nothing.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "..", "context", "next-work", "inputs.md")

CLOCK = "2026-12-01T09:00:00Z"
FRESH, OLD = "2026-12-01T07:00:00Z", "2026-11-24T08:00:00Z"


def work(identity, title, status="open", retrieved_at=FRESH, **fields):
    record = {"identity": identity, "kind": "work", "title": title, "status": status}
    record.update(fields)
    if retrieved_at is not None:
        record["retrieved_at"] = retrieved_at
    return record


def decision(identity, title, status, retrieved_at=FRESH):
    return {"identity": identity, "kind": "decision", "title": title, "status": status, "retrieved_at": retrieved_at}


T1, T2 = "trello:7b2e000000000000000e0001", "trello:7b2e000000000000000e0002"
G1 = "github:I_kwFIXnw00001"

RECORDS = [
    work("jira:61001", "Allergen labels on the menu", priority="high", due="2026-12-03", created="2026-11-10", votes=4, blocks=["jira:61005", "jira:61009"]),
    work("jira:61002", "Parents can cancel an order", priority="high", due="2026-12-03", created="2026-11-12", votes=2),
    work("jira:61003", "Receipt email", priority="high", due="2026-12-10", created="2026-11-14", votes=0),
    # First on its recorded fields, and its copy is a week old.
    work("jira:61004", "Weekly menu import", retrieved_at=OLD, priority="high", due="2026-12-02", created="2026-11-08", votes=1),
    # Waits on jira:61001. The run "after a dependency was completed" completes that one.
    work("jira:61005", "Allergen filter", priority="medium", due="2026-12-08", created="2026-11-16", votes=3, blocked_by=["jira:61001"]),
    # Level on priority, due date, waiters and created date: the identity decides.
    work("jira:61006", "Kitchen printout", priority="medium", due="2026-12-05", created="2026-11-15", votes=1),
    work("jira:61007", "Export orders to CSV", priority="medium", due="2026-12-05", created="2026-11-15", votes=6),
    # Low priority, due tomorrow.
    work("jira:61008", "Low balance reminder", priority="low", due="2026-12-02", created="2026-11-18", votes=5),
    # Blocked, and its priority was never recorded.
    work("jira:61009", "Allergen report for the kitchen", due="2026-12-09", created="2026-11-17", votes=0, blocked_by=["jira:61001"]),
    # Waits on a decision that is still a question.
    work("jira:61010", "Pay by voucher", priority="high", due="2026-12-04", created="2026-11-11", votes=8, needs_decision=["decision:E-301"]),
    # Open, and somebody has it.
    work("jira:61011", "Term dates in the calendar", priority="medium", due="2026-12-06", created="2026-11-13", votes=2, assigned_to="Developer B"),
    work("jira:61012", "Design tokens", status="in_progress", priority="medium", due="2026-12-12", created="2026-11-05", votes=0, assigned_to="Designer A", blocks=[G1]),
    work("jira:61013", "Remove the old login page", status="done", priority="low", created="2026-10-20", votes=0),
    # Names a blocker that has no record.
    work("jira:61014", "Sibling discount", priority="medium", due="2026-12-07", created="2026-11-19", votes=7, blocked_by=["jira:61099"]),
    # A due date that is not a date.
    work("jira:61015", "Menu photo upload", priority="medium", due="soon", created="2026-11-20", votes=1),
    # No record of when it was retrieved.
    work("jira:61016", "Translate the order page", retrieved_at=None, priority="medium", due="2026-12-05", created="2026-11-18", votes=0),
    # Blocked by an item whose own copy is old.
    work("jira:61017", "Refund flow", priority="medium", due="2026-12-06", created="2026-11-21", votes=9, blocked_by=["jira:61018"]),
    work("jira:61018", "Payment provider contract check", retrieved_at="2026-11-20T10:00:00Z", priority="high", due="2026-12-04", created="2026-11-09", votes=0),
    # Waits on a decision that has been made.
    work("jira:61019", "Free school meals flag", priority="medium", due="2026-12-09", created="2026-11-22", votes=2, needs_decision=["decision:E-302"]),
    # The scenario's item: the most votes, blocked, and a copy a week old.
    work(G1, "Dark mode", retrieved_at=OLD, priority="low", due="2026-12-20", created="2026-10-01", votes=57, blocked_by=["jira:61012"]),
    # High priority and no due date.
    work(T1, "Order cut-off time setting", priority="high", created="2026-11-23", votes=1),
    # Neither priority nor due date.
    work(T2, "Tidy up the help page", created="2026-11-01", votes=0),
    decision("decision:E-301", "Are vouchers accepted for part of an order?", "question"),
    decision("decision:E-302", "Free school meals are shown to kitchen staff only", "decided"),
]


def text():
    out = ["# Inputs: work to be ranked, the school meals ordering app", "",
           "Written by `participant/skills/context-next-work/make_inputs.py`, at the participant's direction, for the quest",
           "`context-next-work`.", "",
           "**Everything here is made up.** The project, a school meals ordering app, does not exist. No identifier belongs to a",
           "real item, and the people are roles.", "",
           "- clock: `%s`" % CLOCK, "",
           "The clock value is part of the input. The ranking reads it from the line above, or from `--now`, and never from the",
           "computer's clock. `retrieved_at` is when the local copy of a record was fetched.", "",
           "## What is in here on purpose", "",
           "| Record | What it shows |", "|---|---|",
           "| `%s` | The most votes of any item. Blocked, and its copy is 7 days old |" % G1,
           "| `jira:61005`, `jira:61009` | Blocked by `jira:61001`. One of them has no priority recorded |",
           "| `jira:61010` | Blocked by a decision that is still a question |",
           "| `jira:61014` | Blocked by an item that has no record |",
           "| `jira:61017` | Blocked by an item whose own copy is old |",
           "| `jira:61004`, `jira:61018` | Not blocked, with a copy older than 24 hours |",
           "| `jira:61016` | No `retrieved_at` at all |",
           "| `jira:61015` | A due date that is not a date |",
           "| `%s` | High priority and no due date |" % T1,
           "| `%s` | Neither a priority nor a due date |" % T2,
           "| `jira:61006`, `jira:61007` | Level on every criterion but the last |",
           "| `jira:61008` | Low priority, due the day after the clock value |",
           "| `jira:61011`, `jira:61012`, `jira:61013` | Taken, in progress, done |", "",
           "## The records", ""]
    for record in RECORDS:
        out += ["### %s" % record["identity"], "", "```json", json.dumps(record, indent=2, ensure_ascii=False), "```", ""]
    return "\n".join(out)


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(text())
    print("Wrote inputs.md: %d records." % len(RECORDS))


if __name__ == "__main__":
    main()
