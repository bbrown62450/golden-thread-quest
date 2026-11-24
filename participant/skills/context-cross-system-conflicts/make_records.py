#!/usr/bin/env python3
"""Writes the made-up linked records: participant/context/conflicts/records.md and earlier-records.md.

    python3 participant/skills/context-cross-system-conflicts/make_records.py

Nothing here is real. Each record is one work item in one of three made-up systems, in the shape the earlier quests'
normalizing left it: a stable identity, canonical fields, and beside them what the source itself wrote, untouched.
`earlier-records.md` is the same work a week before, used to show which conflicts were already there.
Running this again writes the same files.
"""
import copy
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
FOLDER = os.path.abspath(os.path.join(HERE, "..", "..", "context", "conflicts"))
LISTS = {"open": "Backlog", "in_progress": "Doing", "done": "Done", "dropped": "archived"}


def jira(number, title, status, sent, updated, assignees=1, due=None):
    return {"identity": "jira:%d" % number, "system": "jira", "title": title, "status": status, "assignee_count": assignees, "due_at": due + "T00:00:00Z" if due else None,
            "updated_at": updated, "as_sent": {"status": sent, "assigned": "assignee: account 5b10fixture%04d" % number if assignees else "assignee: null", "due": "duedate: %s" % due if due else "duedate: null"}}


def trello(number, title, status, updated, assignees=1, due=None, list_name=None):
    card = "%08x%014x%02d" % (0x6ae85110 + number * 3600, 0xa, number)
    return {"identity": "trello:%s" % card, "system": "trello", "title": title, "status": status, "assignee_count": assignees, "due_at": due + "T17:00:00Z" if due else None,
            "updated_at": updated, "as_sent": {"status": "in the list \"%s\"%s" % (list_name or LISTS[status], ", archived" if status == "dropped" else ""),
                                              "assigned": "idMembers: %d" % assignees, "due": "due: %sT17:00:00.000Z" % due if due else "due: null"}}


def github(number, title, status, updated, assignees=1):
    state = {"open": "state open", "done": "state closed, state_reason completed", "dropped": "state closed, state_reason not_planned"}[status]
    return {"identity": "github:I_kwFIX04%02d" % number, "system": "github", "title": title, "status": status, "assignee_count": assignees, "due_at": None, "updated_at": updated,
            "as_sent": {"status": state, "assigned": "assignees: %d" % assignees, "due": "an issue has no due date"}}


def now():
    """(work, what it is, the records, the note on who stated the link)."""
    return [
        ("W-01", "All three agree.", [jira(41001, "Set up the intake form", "done", "status Done, category done", "2026-11-03T10:12:00Z"),
                                      trello(1, "Set up the intake form", "done", "2026-11-03T10:30:00Z"), github(1, "Set up the intake form", "done", "2026-11-03T10:20:00Z")]),
        ("W-02", "The quest's scenario: the tracker says done, the board says in review, and the issue is still open. Days apart.",
         [jira(41002, "Export intake records as CSV", "done", "status Done, category done", "2026-11-10T09:00:00Z"),
          trello(2, "CSV export", "in_progress", "2026-11-05T14:00:00Z", list_name="In Review"), github(2, "Export intake records as CSV", "open", "2026-11-04T10:00:00Z")]),
        ("W-03", "The tracker and the issue were closed two hours after the card last moved.",
         [jira(41003, "Validate email addresses on intake", "done", "status Done, category done", "2026-11-18T10:00:00Z"),
          trello(3, "Validate email addresses on intake", "in_progress", "2026-11-18T08:00:00Z"), github(3, "Validate email addresses on intake", "done", "2026-11-18T10:05:00Z")]),
        ("W-04", "The tracker was closed in the morning. In the afternoon the card was moved back to Doing.",
         [jira(41004, "Schedule the Friday export", "done", "status Done, category done", "2026-11-17T09:00:00Z"), trello(4, "Schedule the Friday export", "in_progress", "2026-11-17T15:00:00Z")]),
        ("W-05", "The tracker says in progress. GitHub can only say open.",
         [jira(41005, "Tidy the export folder", "in_progress", "status In Progress, category indeterminate", "2026-11-12T11:00:00Z"), github(5, "Tidy the export folder", "open", "2026-11-11T09:00:00Z")]),
        ("W-06", "The tracker says done. The issue was closed as not planned, half an hour later.",
         [jira(41006, "Drop the legacy importer", "done", "status Done, category done", "2026-11-16T10:00:00Z"), github(6, "Drop the legacy importer", "dropped", "2026-11-16T10:30:00Z")]),
        ("W-07", "The card and the issue were last changed at the same second, and differ.",
         [trello(7, "Rate-limit the public API", "done", "2026-11-15T12:00:00Z"), github(7, "Rate-limit the public API", "open", "2026-11-15T12:00:00Z")]),
        ("W-08", "The tracker's record does not say when it last changed.",
         [jira(41008, "Document the rate limits", "in_progress", "status In Progress, category indeterminate", None), trello(8, "Document the rate limits", "done", "2026-11-14T16:00:00Z")]),
        ("W-09", "The tracker was closed six hours after the issue last changed. The issue is still open.",
         [jira(41009, "Add retry to the webhook sender", "done", "status Done, category done", "2026-11-19T16:00:00Z"), github(9, "Add retry to the webhook sender", "open", "2026-11-19T10:00:00Z")]),
        ("W-10", "The card was moved to Done exactly 24 hours after the tracker last changed.",
         [jira(41010, "Add a status page", "in_progress", "status In Progress, category indeterminate", "2026-11-19T09:00:00Z"), trello(10, "Add a status page", "done", "2026-11-20T09:00:00Z")]),
        ("W-11", "The card was moved to Done 24 hours and one second after the tracker last changed.",
         [jira(41011, "Archive the old dashboards", "in_progress", "status In Progress, category indeterminate", "2026-11-19T09:00:00Z"), trello(11, "Archive the old dashboards", "done", "2026-11-20T09:00:01Z")]),
        ("W-12", "The statuses agree as far as each system can say. The due dates do not, three days apart, and the three titles differ.",
         [jira(41012, "Rotate the signing key", "in_progress", "status In Progress, category indeterminate", "2026-11-10T09:00:00Z", due="2026-12-01"),
          trello(12, "Key rotation", "in_progress", "2026-11-13T09:00:00Z", due="2026-12-04"), github(12, "Rotate signing key (security)", "open", "2026-11-09T09:00:00Z")]),
        ("W-13", "The tracker gained an assignee ninety minutes after the card last changed. The card has none.",
         [jira(41013, "Write the onboarding guide", "open", "status To Do, category new", "2026-11-20T10:00:00Z"), trello(13, "Write the onboarding guide", "open", "2026-11-20T08:30:00Z", assignees=0)]),
    ]


LOOSE = [jira(41050, "Translate the help pages", "open", "status To Do, category new", "2026-11-08T09:00:00Z"),
         trello(50, "Fix export", "in_progress", "2026-11-09T09:00:00Z"), github(50, "Fix export", "open", "2026-11-12T09:00:00Z"),
         jira(41014, "Add dark mode", "open", "status To Do, category new", "2026-11-07T09:00:00Z"),
         jira(41015, "Search by title", "in_progress", "status In Progress, category indeterminate", "2026-11-06T09:00:00Z"),
         jira(41016, "Remove the old banner", "done", "status Done, category done", "2026-11-06T10:00:00Z"), trello(15, "Search and banner", "in_progress", "2026-11-06T11:00:00Z")]
BAD_LINKS = [("W-14", ["jira:41014", "github:I_kwFIX0499"]), ("W-15", ["jira:41015", LOOSE[6]["identity"]]), ("W-16", ["jira:41016", LOOSE[6]["identity"]])]
DEPENDS = {"W-04": ["W-02"], "W-06": ["W-02"], "W-09": ["W-06"], "W-11": ["W-08"]}


def earlier():
    """The same work five days before. W-02, W-06, W-07, W-08 and W-12 were already as they are. The rest had not yet diverged."""
    works = copy.deepcopy(now())
    by = {work: records for work, _, records in works}
    def set_to(record, status, updated, sent=None):
        record["status"], record["updated_at"] = status, updated
        record["as_sent"]["status"] = sent or record["as_sent"]["status"]
    set_to(by["W-03"][0], "in_progress", "2026-11-12T10:00:00Z", "status In Progress, category indeterminate")
    set_to(by["W-03"][2], "open", "2026-11-12T10:05:00Z", "state open")
    set_to(by["W-03"][1], "in_progress", "2026-11-12T08:00:00Z")
    set_to(by["W-04"][0], "in_progress", "2026-11-12T09:00:00Z", "status In Progress, category indeterminate")
    set_to(by["W-04"][1], "in_progress", "2026-11-12T09:30:00Z")
    set_to(by["W-09"][0], "in_progress", "2026-11-12T16:00:00Z", "status In Progress, category indeterminate")
    set_to(by["W-09"][1], "open", "2026-11-12T10:00:00Z")
    for work in ("W-10", "W-11"):
        by[work][0]["updated_at"] = "2026-11-13T09:00:00Z"
        set_to(by[work][1], "in_progress", "2026-11-13T09:05:00Z", "in the list \"Doing\"")
    by["W-13"][0]["assignee_count"], by["W-13"][0]["updated_at"] = 0, "2026-11-12T10:00:00Z"
    by["W-13"][0]["as_sent"]["assigned"] = "assignee: null"
    by["W-13"][1]["updated_at"] = "2026-11-12T08:30:00Z"
    return works


def document(works, run, about):
    lines = ["# Linked records across three systems", "",
             "Written by an AI assistant (Claude) at the participant's direction, for the quest `context-cross-system-conflicts`, with",
             "`participant/skills/context-cross-system-conflicts/make_records.py`.", "", "Run: %s" % run, "",
             "**Every record here is made up.** %s" % about, "",
             "Each record is one work item in one system: its stable identity, the fields the systems share in a common form, and under `as_sent` what the source itself",
             "wrote for each, untouched. `status` is one of open, in_progress, done, dropped. `updated_at` is when the source says the record last changed.", "",
             "## Links", "",
             "Which records are the same piece of work. **A link is stated by a person**, and names each record by its stable identity. Nothing here was worked out from a title.", "",
             "| Work | Jira | Trello | GitHub | Stated by |", "|---|---|---|---|---|"]
    for work, _, records in works:
        cells = {record["system"]: "`%s`" % record["identity"] for record in records}
        lines.append("| %s | %s | %s | %s | the delivery lead, in the planning sheet PS-7, row %s |" % (work, cells.get("jira", "none"), cells.get("trello", "none"), cells.get("github", "none"), work[2:]))
    for work, members in BAD_LINKS:
        cells = {member.split(":")[0]: "`%s`" % member for member in members}
        lines.append("| %s | %s | %s | %s | the delivery lead, in the planning sheet PS-7, row %s |" % (work, cells.get("jira", "none"), cells.get("trello", "none"), cells.get("github", "none"), work[2:]))
    lines += ["", "Three of these links are faulty on purpose: W-14 names a GitHub issue that is not in this file, and W-15 and W-16 both name the same Trello card.", "",
              "## What depends on what", "", "Which pieces of work cannot proceed until another is finished. Used only to order the report.", "", "| Work | Depends on |", "|---|---|"]
    lines += ["| %s | %s |" % (work, ", ".join(needs)) for work, needs in sorted(DEPENDS.items())]
    lines += ["", "## The records", ""]
    for work, about_work, records in works:
        lines += ["#### %s" % work, "", about_work, ""]
        for record in records:
            lines += ["### %s" % record["identity"], "", "```json", json.dumps(record, indent=1, ensure_ascii=False), "```", ""]
    lines += ["#### Not linked to anything usable", "", "A story with no counterpart, a card and an issue that share a title and no link, and the records the three faulty links name.", ""]
    for record in LOOSE:
        lines += ["### %s" % record["identity"], "", "```json", json.dumps(record, indent=1, ensure_ascii=False), "```", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    os.makedirs(FOLDER, exist_ok=True)
    for name, works, run, about in (("records.md", now(), "2026-11-21", "They are three made-up systems' records of the same made-up work, as they stood on 21 November."),
                                    ("earlier-records.md", earlier(), "2026-11-16", "They are the same made-up work five days before `records.md`, as it stood at the end of 16 November.")):
        with open(os.path.join(FOLDER, name), "w", encoding="utf-8", newline="\n") as f:
            f.write(document(works, run, about))
    print("make_records: wrote records.md and earlier-records.md")
