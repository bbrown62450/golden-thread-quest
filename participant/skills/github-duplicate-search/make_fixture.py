#!/usr/bin/env python3
"""Writes the made-up fixture for the duplicate search: issue records, their index, and three proposed issues.

    make_fixture.py [FOLDER]      default: participant/context/github/duplicates

It writes FOLDER/records/ (nine made-up issue records), FOLDER/fixture.md (the index of those records) and
FOLDER/proposals/ (three drafts of issues somebody is about to file). Contacts nothing.

The records are written by the github-read-issue skill's code, and the index is built by the github-build-index
skill's generator, both loaded from their folders and neither changed. So the fixture is a real index of real
records in those skills' formats. Every repository, person, label and issue here is invented.

What the fixture holds, for the proposed issue "Out of memory when saving the March orders":

    tracker 101   the TRUE DUPLICATE, under a different title: "Export crashes on files over 2 GB"
    tracker 102   a NEAR DUPLICATE: the same export, the same files, but it is slow, it does not crash
    tracker 106   the same error, fixed and closed a version ago
    tracker 105, 107, 104 and website 7, 8   ordinary issues in the background

And for the proposed issue "Login page is blank":

    tracker 103   the SAME TITLE, UNRELATED: a sign-in screen that stays blank, where the proposal is about a
                  page of a printed handbook
"""
import contextlib
import importlib.util
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TRACKER, WEBSITE = "acme-fixture/tracker", "acme-fixture/website"
SOURCE = "the made-up GitHub (fake_github.py)"


def load(folder, name, alias):
    spec = importlib.util.spec_from_file_location(alias, os.path.join(HERE, "..", folder, name))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


reader = load("github-read-issue", "read_issue.py", "reader_for_the_duplicate_fixture")
world = load("github-read-issue", "fake_github.py", "made_up_github_for_the_duplicate_fixture")
indexer = load("github-build-index", "index.py", "indexer_for_the_duplicate_fixture")
ROBIN, SAM, KIT = world.ROBIN, world.SAM, world.KIT

LABELS = {"bug": 1, "export": 11, "performance": 12, "auth": 13, "docs": 4, "enhancement": 5, "import": 14, "search": 15}


def made(repo, number, title, body, marks, state="open", why=None, assigned=(), author=SAM, replies=()):
    more = {"labels": [world.label(LABELS[name], name, "ededed", None) for name in marks],
            "assignees": [world.person(*one) for one in assigned], "assignee": world.person(*assigned[0]) if assigned else None,
            "state": state, "state_reason": why, "closed_at": "2026-10-02T09:00:00Z" if state == "closed" else None,
            "closed_by": world.person(*ROBIN) if state == "closed" else None}
    if repo == WEBSITE:
        more["node_id"] = "I_kwFW%04d" % number
    issue = world.issue(repo, number, title, body, author=author, comments=len(replies), **more)
    comments = [world.comment(repo, number, 6700 + number * 10 + index, text, who, "2026-11-18T1%d:00:00Z" % index) for index, (who, text) in enumerate(replies)]
    return repo, issue, comments


def records():
    return [
        made(TRACKER, 101, "Export crashes on files over 2 GB", "\n".join([
            "The nightly export stops part way when the orders file is large.", "",
            "Steps:", "", "1. Take the made-up file `orders-march.csv`, which is about 2.4 GB.", "2. Run `export.py` from `v2.3.1`.", "",
            "It fails after a few minutes with:", "", "```", "MemoryError: cannot allocate 2147483648 bytes", "error code E-EXPORT-413", "```", "",
            "Smaller files export without trouble. The whole file seems to be loaded into memory before anything is written."]),
             ["bug", "export"], assigned=[ROBIN],
             replies=[(KIT, "Same here. Memory climbs until the process is killed. The March orders file is the only one this large.")]),
        made(TRACKER, 102, "Export is slow on large files", "\n".join([
            "The export of `orders-march.csv` with `export.py` in `v2.3.1` takes over forty minutes.", "",
            "It does finish, and the output is right. It is only slow. Setting `--chunk-size` higher helps a little.", "",
            "Most of the time goes on writing one row at a time."]),
             ["performance", "export"], assigned=[KIT]),
        made(TRACKER, 103, "Login page is blank", "\n".join([
            "After a password reset, the sign-in screen of the tracker stays white.", "",
            "The browser console shows `E-AUTH-500` from `session.js`. Reloading does not help. Signing in from a private window works.", "",
            "Seen in `v2.3.1` on two machines."]),
             ["bug", "auth"], assigned=[SAM]),
        made(TRACKER, 104, "Import fails on an empty file", "\n".join([
            "Importing a made-up file with no rows stops with:", "", "```", "ValueError: empty file", "```", "",
            "`import.py` should say the file is empty and carry on with the next one."]),
             ["bug", "import"], assigned=[ROBIN]),
        made(TRACKER, 105, "Document the export format", "\n".join([
            "The columns that `export.py` writes are not described anywhere in the handbook.", "", "A short page with one line for each column would do."]),
             ["docs"], assigned=[SAM]),
        made(TRACKER, 106, "MemoryError in the nightly export", "\n".join([
            "The nightly export of the orders file stopped last night with a MemoryError.", "",
            "```", "MemoryError: cannot allocate 1073741824 bytes", "```", "",
            "The whole orders file is loaded into memory before the export writes anything. Fixed by reading it in pieces, in `v2.2.0`."]),
             ["bug", "export"], state="closed", why="completed", assigned=[ROBIN]),
        made(TRACKER, 107, "Rename the --chunk-size option", "The option `--chunk-size` counts rows, not bytes. The name should say so.", ["enhancement", "export"], author=KIT),
        made(WEBSITE, 7, "Search box returns nothing", "Searching the made-up site for any word shows an empty list. The search index was last built in the spring.",
             ["bug", "search"], assigned=[KIT]),
        made(WEBSITE, 8, "Footer year is wrong", "The footer still shows last year.", ["bug"]),
    ]


PROPOSALS = {
    "proposed-out-of-memory.md": ("Out of memory when saving the March orders", TRACKER, ["bug", "export"], "\n".join([
        "Saving the March orders ran out of memory this morning and the job was killed.", "",
        "I ran `export.py` on `orders-march.csv` with `v2.3.1`. After a few minutes it stopped:", "",
        "```", "MemoryError: cannot allocate 2147483648 bytes", "```", "",
        "The orders file is large this month. It looks as if the whole file is loaded into memory before anything is written."])),
    "proposed-login-page.md": ("Login page is blank", WEBSITE, ["docs"], "\n".join([
        "In the printed handbook, the page that explains how to log in comes out empty.", "",
        "The PDF has the heading and then nothing. The page before it and the page after it print as they should.", "",
        "It is page 14 of the made-up handbook, the autumn edition."])),
    "proposed-dark-mode.md": ("Add a dark mode to the settings screen", WEBSITE, ["enhancement"], "\n".join([
        "Several made-up visitors asked for a dark colour scheme.", "", "A switch on the settings screen that remembers the choice would be enough."])),
}


def proposal_text(title, repo, labels, body):
    import json
    return "---\ntitle: %s\nrepository: %s\nlabels: %s\n---\n%s\n" % (json.dumps(title), json.dumps(repo), json.dumps(labels), body)


def write_all(folder):
    """Write the records, build their index with the build-index generator, and write the proposals."""
    folder = os.path.normpath(folder)
    names = []
    for repo, issue, comments in records():
        text = reader.render(SOURCE, repo, issue, comments)
        if reader.lost(text, issue, comments):
            raise SystemExit("make_fixture: the reader's own check failed for issue %d" % issue["number"])
        name = "%s__issue-%d.md" % (repo.replace("/", "__"), issue["number"])
        os.makedirs(os.path.join(folder, "records"), exist_ok=True)
        with open(os.path.join(folder, "records", name), "wb") as f:
            f.write(text.encode("utf-8"))
        names.append(name)
    with contextlib.redirect_stdout(io.StringIO()) as printed:
        code = indexer.main(["build", "--records", os.path.join(folder, "records"), "--out", os.path.join(folder, "fixture.md")])
    if code != 0:
        raise SystemExit("make_fixture: the index generator did not build a clean index:\n" + printed.getvalue())
    os.makedirs(os.path.join(folder, "proposals"), exist_ok=True)
    for name, parts in PROPOSALS.items():
        with open(os.path.join(folder, "proposals", name), "w", encoding="utf-8") as f:
            f.write(proposal_text(*parts))
    return names


def main(argv):
    folder = argv[0] if argv else os.path.join(HERE, "..", "..", "context", "github", "duplicates")
    names = write_all(folder)
    print("make_fixture: wrote %d made-up issue records, their index fixture.md, and %d proposed issues" % (len(names), len(PROPOSALS)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
