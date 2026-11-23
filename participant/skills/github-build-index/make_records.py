#!/usr/bin/env python3
"""Writes the made-up issue records that the index is built from. Contacts nothing.

    make_records.py [FOLDER]        write the eleven made-up records (default: participant/context/github/issues)
    make_records.py FOLDER --one    write one more made-up record, website issue 14, as a sync would add one

The records are written by the github-read-issue skill's own code, so they are
real records in its format (github-issue-markdown/1), not look-alikes. That
skill and its made-up GitHub are loaded from their folder and are not changed.
Every repository, person, label, milestone and issue here is invented.

The twelfth record in the default folder, issue-sample.md, was written by the
github-read-issue quest and is left as it is.
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
READER = os.path.join(HERE, "..", "github-read-issue")
TRACKER, WEBSITE = "acme-fixture/tracker", "acme-fixture/website"
SOURCE = "the made-up GitHub (fake_github.py)"


def _load(name, alias):
    spec = importlib.util.spec_from_file_location(alias, os.path.join(READER, name))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


reader = _load("read_issue.py", "reader_of_issues")
world = _load("fake_github.py", "made_up_github_of_the_reader")
ROBIN, SAM, KIT = world.ROBIN, world.SAM, world.KIT

LABELS = {"bug": (1, "d73a4a", "Something is not working"), "docs": (4, "0075ca", "Words, not code"),
          "enhancement": (5, "a2eeef", "New feature or request"), "good first issue": (6, "7057ff", "Good for newcomers")}


def labels(*names):
    return [world.label(LABELS[name][0], name, LABELS[name][1], LABELS[name][2]) for name in names]


def milestone(number, title):
    return dict(world.milestone(), number=number, title=title, id=8000 + number, node_id="MI_kwFX%d" % (8000 + number))


def people(*who):
    return [world.person(*one) for one in who]


def record(repo, number, title, body, state="open", marks=(), assigned=(), sprint=None, author=SAM, why=None, replies=()):
    """One made-up issue as GitHub would return it, and its comments."""
    more = {"labels": labels(*marks), "assignees": people(*assigned), "assignee": people(*assigned)[0] if assigned else None,
            "milestone": milestone(*sprint) if sprint else None, "state": state, "state_reason": why,
            "closed_at": "2026-11-19T16:00:00Z" if state == "closed" else None,
            "closed_by": world.person(*ROBIN) if state == "closed" else None}
    if repo == WEBSITE:
        more["node_id"] = "I_kwFW%04d" % number
    issue = world.issue(repo, number, title, body, author=author, comments=len(replies), **more)
    comments = [world.comment(repo, number, 6500 + number * 10 + index, text, who, "2026-11-18T1%d:00:00Z" % index)
                for index, (who, text) in enumerate(replies)]
    return repo, issue, comments


EXPORTS, SPRINT_13, LAUNCH, WEB_SPRINT = (3, "Sprint 12: exports"), (4, "Sprint 13"), (1, "Launch"), (2, "Sprint 13")


def all_records():
    return [
        record(TRACKER, 12, "Import fails on an empty file", "Steps:\n\n1. Make an empty file.\n2. Import it.\n\nIt stops with a made-up error.",
               marks=["bug"], assigned=[ROBIN], sprint=EXPORTS, replies=[(KIT, "Seen here too, with a file of one line.")]),
        record(TRACKER, 13, "Document the export format", "The made-up export has no page in the handbook yet.",
               state="closed", why="completed", marks=["docs"], assigned=[SAM], sprint=EXPORTS),
        record(TRACKER, 17, "Rename the | pipe | option", "The option `--pipe` reads like a shell pipe.\n\n- [ ] pick a name\n- [ ] keep the old one working",
               marks=["bug", "enhancement"], assigned=[ROBIN, KIT], sprint=SPRINT_13),
        record(TRACKER, 21, "Nobody owns this yet", "A made-up issue with no label, no milestone and nobody assigned."),
        record(TRACKER, 30, "Title with `backticks`, [brackets] and <b>tags</b>", "A made-up issue whose title could break a table.",
               marks=["enhancement"], assigned=[KIT], author=ROBIN),
        record(WEBSITE, 3, "Broken link on the pricing page", "The made-up link to the price list goes nowhere.",
               state="closed", why="not_planned", marks=["bug"], assigned=[SAM], sprint=LAUNCH),
        record(WEBSITE, 4, "Add a search box", "Visitors cannot search the made-up site.", marks=["enhancement", "good first issue"], assigned=[KIT], sprint=LAUNCH),
        record(WEBSITE, 5, "Fix the footer year", "The footer still shows last year.", marks=["bug", "good first issue"], sprint=LAUNCH, author=KIT),
        record(WEBSITE, 8, "# Not a heading", "A made-up issue whose title starts like a Markdown heading.", marks=["docs"], assigned=[ROBIN]),
        record(WEBSITE, 9, "Translate the home page", None, assigned=[SAM, ROBIN], sprint=WEB_SPRINT),
        record(WEBSITE, 11, "Ünïcödé title — with a long dash", "A made-up issue with a title that is not plain ASCII.",
               state="closed", why="completed", marks=["docs"], assigned=[KIT], sprint=LAUNCH),
    ]


def one_more():
    return record(WEBSITE, 14, "Add a footer link to the handbook", "Asked for by a made-up visitor.", marks=["enhancement"], assigned=[ROBIN], sprint=LAUNCH)


def write(folder, made):
    """Write one record with the reader's own code, and check it by reading it back. Returns the file's name."""
    repo, issue, comments = made
    text = reader.render(SOURCE, repo, issue, comments)
    if reader.lost(text, issue, comments):
        raise SystemExit("make_records: the reader's own check failed for issue %d" % issue["number"])
    name = "%s__issue-%d.md" % (repo.replace("/", "__"), issue["number"])
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, name), "wb") as f:
        f.write(text.encode("utf-8"))
    return name


def main(argv):
    folder = argv[0] if argv and not argv[0].startswith("--") else os.path.join(HERE, "..", "..", "context", "github", "issues")
    made = [one_more()] if "--one" in argv else all_records()
    names = [write(folder, one) for one in made]
    print("make_records: wrote %d made-up issue record(s): %s" % (len(names), ", ".join(names)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
