#!/usr/bin/env python3
"""Makes the masked copy of a REAL run of the approved github-read-assigned skill, so that it can be kept in this repository.

    mask_real_github.py FOLDER      FOLDER is where the participant's real sync wrote, outside this repository

It reads FOLDER/assigned.json and writes participant/context/github/assigned-live-masked/assigned.json. It contacts nothing.
What it changes, and nothing else:

    the owner's login, wherever it appears           ->  [owner]
    the owner's numeric user id                      ->  "[user id]"
    each issue's node ID                             ->  [issue node id 1], [issue node id 2] ... in the order of the issue numbers
    each pull request's node ID                      ->  [pull request node id 1] ...
    the repository's numeric id                      ->  "[repository id]"
    each issue's numeric id, and each event's id     ->  "[issue id]", id:[event id]
    the text of each body and each comment           ->  "[not copied]"   (the count of comments is kept)

The issue numbers, titles, labels, states, times and links are as GitHub sent them. The titles are made-up work the
participant typed into their own sandbox repository. It stops if a masked value is still in what it would write.

Only the participant can run this again, because only their computer has the real files.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
OUT = os.path.join(REPO, "participant", "context", "github", "assigned-live-masked")
NOTE = """# A masked copy of a real sync

`assigned.json` here is a masked copy of what the approved `github-read-assigned` skill saved when the participant ran it
against their own private sandbox repository. The original is kept outside this repository.

Replaced, and shown in square brackets: the owner's login and user id, every node ID, the repository's id, each issue's and
event's numeric id, and the text of each body and comment. Nothing else was changed. The issue numbers, titles, labels,
states, times and links are as GitHub sent them. The titles are made-up work the participant typed.

Made by `participant/evidence/context-canonical-work-item/context-attempt-002/scripts/mask_real_github.py`.
The made-up GitHub's version of this file is `../assigned/assigned.json`.
"""


def main(argv):
    if len(argv) != 1:
        print(__doc__)
        return 1
    with open(os.path.join(argv[0], "assigned.json"), encoding="utf-8") as f:
        data = json.load(f)
    if data.get("source") != "live":
        print("mask_real_github: that folder does not hold a real sync. Nothing was written.")
        return 1
    login, user_id = data["identity"]["login"], data["identity"]["id"]
    real = {login, str(user_id)}
    nodes = {}
    for issue in sorted(data["issues"].values(), key=lambda one: one["number"]):
        nodes[issue["node_id"]] = "[issue node id %d]" % (len(nodes) + 1)
    pulls = {}
    issues = {}
    for node, issue in data["issues"].items():
        real.update([node, str(issue["id"]), str(issue["repo_id"])])
        issue = dict(issue, node_id=nodes[node], id="[issue id]", repo_id="[repository id]", body="[not copied]" if issue.get("body") else "")
        issue["comments"] = [dict(comment, body="[not copied]", id="[comment id]") for comment in issue.get("comments") or []]
        for event in issue.get("events") or []:
            detail = event.get("detail") or {}
            if detail.get("node_id"):
                real.add(detail["node_id"])
                detail["node_id"] = pulls.setdefault(detail["node_id"], "[pull request node id %d]" % (len(pulls) + 1))
            for found in re.findall(r"\d{6,}", event.get("key", "")):
                real.add(found)
            event["key"] = re.sub(r"id:\d+", "id:[event id]", event.get("key", ""))
            if event["key"].startswith("cross-referenced:"):
                event["key"] = "cross-referenced:%s:%s" % (detail.get("node_id"), event.get("created_at"))
        issues[nodes[node]] = issue
    repos = {"[repository id]": dict(repo, id="[repository id]") for repo in data.get("repos", {}).values()}
    masked = dict(data, identity={"id": "[user id]", "login": login}, issues=issues, repos=repos)
    text = json.dumps(masked, indent=1, sort_keys=True).replace(login, "[owner]") + "\n"
    left = sorted(value for value in real if value in text)
    if left or re.search(r"\b(I|PR|IC)_kw[A-Za-z0-9]", text):
        print("mask_real_github: a value that should be masked is still there. Nothing was written.")
        return 1
    os.makedirs(OUT, exist_ok=True)
    for name, content in (("assigned.json", text), ("README.md", NOTE)):
        with open(os.path.join(OUT, name), "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
    print("mask_real_github: wrote the masked copy of %d real issues. Values masked: %d" % (len(issues), len(real)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
