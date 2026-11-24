#!/usr/bin/env python3
"""Writes the made-up batches of source records into participant/context/identity/batches/.

    python3 participant/skills/context-stable-identities/make_batches.py

Nothing here is real. Each batch stands for one sync: the records three made-up systems sent that day. Running this
again writes the same files.

    batch-1  the first sync: 20 items. 7 from Jira, 7 from Trello, 6 from GitHub
    batch-2  every item again, in another order, after people RENAMED and MOVED some of them at the source
    batch-3  a COLLISION: two different GitHub records with one node ID. And one Jira record delivered twice
    batch-4  a REUSED IDENTIFIER: Jira sends id 40007 for an issue created on another day. And two records with no creation time
    batch-5  the source CHANGES an identifier and says so. And six records whose identifier is not usable
"""
import copy
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import identity      # noqa: E402

OUT = os.path.join(identity.FOLDER, "batches")
DEMO = {"id": "50000", "key": "DEMO", "name": "Made-up project DEMO"}
OPS = {"id": "51000", "key": "OPS", "name": "Made-up project OPS"}
BOARD, OTHER = "6740000000000000000000b1", "6740000000000000000000b2"


def card_id(day, hour, number):
    """A made-up Trello card id. Like a real one, its first 8 characters are its creation time."""
    moment = datetime.datetime(2026, 11, day, hour, 0, 0, tzinfo=datetime.timezone.utc)
    return "%08x%014x%02d" % (int(moment.timestamp()), 0xa, number)


def jira(issue, number, summary, day, project=DEMO):
    return {"system": "jira", "record": {"id": issue, "key": "%s-%d" % (project["key"], number), "self": "https://jira.example.invalid/rest/api/3/issue/%s" % issue,
                                          "fields": {"summary": summary, "project": project, "created": "2026-11-%02dT09:00:00.000+0000" % day}}}


def trello(number, short, name, day, list_id, pos, board=BOARD, id_short=None):
    return {"system": "trello", "record": {"id": card_id(day, 9, number), "idShort": id_short or number, "shortLink": short, "name": name, "idBoard": board, "idList": list_id, "pos": pos}}


def github(node, number, title, day, repo=("acme-fixture/platform", 101)):
    return {"system": "github", "record": {"node_id": node, "id": 9000000 + number, "number": number, "title": title, "created_at": "2026-10-%02dT10:00:00Z" % day,
                                            "repository": {"id": repo[1], "full_name": repo[0]}, "html_url": "https://github.com/%s/issues/%d" % (repo[0], number)}}


FIRST = [
    jira("40001", 1, "Set up the intake form", 2), jira("40002", 2, "Validate email addresses on intake", 2), jira("40003", 3, "Export intake records as CSV", 3),
    jira("40004", 4, "Fix export", 3), jira("40005", 5, "Schedule the Friday export", 4), jira("40006", 6, "Fix export", 5), jira("40007", 7, "Tidy the export folder", 6),
    trello(1, "fixT0001", "Add dark mode", 2, "6740000000000000000000d1", 16384), trello(2, "fixT0002", "Export report as PDF", 2, "6740000000000000000000d2", 16384),
    trello(3, "fixT0003", "Write onboarding guide", 3, "6740000000000000000000d1", 32768), trello(4, "fixT0004", "Search by title", 3, "6740000000000000000000d1", 49152),
    trello(5, "fixT0005", "Fix export", 4, "6740000000000000000000d2", 32768), trello(6, "fixT0006", "Set up project board", 5, "6740000000000000000000d3", 16384),
    trello(7, "fixT0007", "Remove old banner", 6, "6740000000000000000000d3", 32768),
    github("I_kwFIX0301", 1, "Export times out on large accounts", 2), github("I_kwFIX0302", 2, "Add retry to the webhook sender", 3),
    github("I_kwFIX0303", 3, "Drop the legacy importer", 4), github("I_kwFIX0304", 4, "Fix export", 5),
    github("I_kwFIXab05", 5, "Rate-limit the public API", 6), github("I_kwFIXAB05", 6, "Document the rate limits", 7),
]


def second():
    records = copy.deepcopy(FIRST)
    by = {entry["record"].get("node_id") or entry["record"]["id"]: entry["record"] for entry in records}
    story = by["40003"]                                   # the scenario: renamed, and moved to another project, so its key changes
    story["fields"]["summary"], story["fields"]["project"], story["key"] = "Export intake records as CSV, weekly", OPS, "OPS-17"
    by["40005"]["fields"]["summary"] = "Export intake records as CSV"            # another story takes the title the first one just gave up
    card = by[card_id(2, 9, 2)]                           # renamed, moved to another board, dragged to the top, renumbered by the new board
    card["name"], card["idBoard"], card["idList"], card["pos"], card["idShort"] = "Export report as PDF and CSV", OTHER, "6740000000000000000000e1", 1024, 31
    by[card_id(3, 9, 4)].update(idList="6740000000000000000000d3", pos=8192)     # moved to another list on the same board, and dragged
    issue = by["I_kwFIX0302"]                             # renamed, and transferred to another repository, so its number changes
    issue["title"], issue["number"], issue["repository"], issue["html_url"] = ("Add retry and backoff to the webhook sender", 41, {"id": 102, "full_name": "acme-fixture/support"},
                                                                               "https://github.com/acme-fixture/support/issues/41")
    return [records[index] for index in (13, 2, 19, 7, 0, 15, 9, 4, 17, 11, 6, 1, 14, 8, 3, 18, 10, 5, 16, 12)]      # and the source sends them in another order


def batches():
    collide_a = github("I_kwFIX0306", 7, "Rotate the signing key", 20)
    collide_b = github("I_kwFIX0306", 8, "Archive the old dashboards", 21)
    no_birth_old = github("I_kwFIX0301", 1, "Export times out on large accounts", 2)
    del no_birth_old["record"]["created_at"]
    no_birth_new = github("I_kwFIX0307", 9, "Add a status page", 22)
    del no_birth_new["record"]["created_at"]
    renamed_id = github("I_kwFIX0399", 3, "Drop the legacy importer", 4)
    renamed_id["record"]["previous_identifier"] = "I_kwFIX0303"
    as_number = jira("40001", 1, "Set up the intake form", 2)
    as_number["record"]["id"] = 40001
    bad = [jira("", 90, "A story with an empty id", 7), jira("40042", 91, "A story whose id was sent as a decimal", 7), jira(" 40009", 92, "A story whose id has a space in front", 7),
           trello(8, "fixT0008", "A card whose id holds a colon", 7, "6740000000000000000000d1", 1), github("x", 93, "An issue with no node ID", 8),
           {"system": "asana", "record": {"gid": "1200000000000001", "name": "A task from a system the rules do not know"}}]
    bad[1]["record"]["id"] = 40042.5
    bad[3]["record"]["id"] = "6744:bad"
    del bad[4]["record"]["node_id"]
    return [
        ("batch-1", "2026-11-10T08:00:00Z", "The first sync.", FIRST),
        ("batch-2", "2026-11-17T08:00:00Z", "A week later. People have renamed and moved items at the source, and the source sends the records in another order.", second()),
        ("batch-3", "2026-11-18T08:00:00Z", "A faulty delivery: two different GitHub records carry one node ID, and one Jira record arrives twice.",
         [collide_a, collide_b, jira("40002", 2, "Validate email addresses on intake", 2), jira("40002", 2, "Validate email addresses on intake", 2), FIRST[7]]),
        ("batch-4", "2026-11-20T08:00:00Z", "Jira sends id 40007 for an issue created on another day: the identifier has been reused. Two GitHub records have no creation time.",
         [jira("40007", 7, "Rotate the signing key", 20), no_birth_old, no_birth_new]),
        ("batch-5", "2026-11-21T08:00:00Z", "GitHub replaces a node ID and says which one it replaces. A Jira id arrives as a number. Six records have no usable identifier.", [renamed_id, as_number] + bad),
    ]


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for name, when, about, records in batches():
        with open(os.path.join(OUT, name + ".json"), "w", encoding="utf-8", newline="\n") as f:
            json.dump({"batch": name, "synced_at": when, "about": about, "records": records}, f, indent=1)
            f.write("\n")
    print("make_batches: wrote %d made-up batches" % len(batches()))
