#!/usr/bin/env python3
"""Turns one REAL run of the github-read-assigned skill into local context the digest can be built from.

    python3 participant/skills/scrum-standup-digest/from_sync.py REAL_FOLDER OUT_FOLDER

    REAL_FOLDER   where the participant's real sync wrote its assigned.json. It is outside the repository.
    OUT_FOLDER    where to write the context, such as participant/context/scrum/real/2026-11-25

It contacts nothing. It does three things, in order.

1. MASKS the real sync, and writes the masked copy to OUT_FOLDER/source/github/assigned/assigned.json.
       every login                                      ->  [owner], or [user 2], [user 3] ... for anyone else
       the owner's numeric user id                      ->  "[user id]"
       each issue's and pull request's node ID          ->  I_masked_ and 12 characters, or PR_masked_ and 12
       the repository's numeric id, each issue's id,
       each comment's id and each event's id            ->  a word in square brackets
       the text of each body and each comment           ->  "[not copied]"   (the count of comments is kept)
   The issue numbers, titles, labels, states, times and links are as GitHub sent them.
   A masked node ID is the first 12 characters of the SHA-256 of a secret and the real node ID. The secret is a file
   beside REAL_FOLDER, outside the repository, made the first time this runs. So the same real item has the same masked
   identity on every day, which is what lets one day be compared with the next, and nobody without the secret can work
   back from the masked identity to the real one. It stops if a real value is still in what it would write.

2. NORMALIZES the masked copy with the approved skill, participant/skills/context-work-item-model/normalize.py, which
   writes the canonical records to OUT_FOLDER/items/. This file does not write a record itself.

3. Writes OUT_FOLDER/sync-runs.md from the sync's own account of itself: its time, and the identities it retrieved.
   And a redaction.md that lists no names and says why. No notes folder is written: nobody wrote a note for these days.

Only the participant can run this again on the real files, because only their computer has them. Anyone can check its
output: `digest.py generate` on OUT_FOLDER reproduces the digest.
"""
import hashlib
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
NORMALIZE = os.path.join(REPO, "participant", "skills", "context-work-item-model", "normalize.py")
STATUS_MAP = os.path.join(REPO, "participant", "context", "model", "mappings", "status-map.json")


def secret_of(real_folder):
    path = os.path.join(os.path.dirname(os.path.abspath(real_folder)), "mask-secret.txt")
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(os.urandom(32).hex() + "\n")
    with open(path, encoding="utf-8") as f:
        return f.read().strip()


def mask(data, secret):
    """The masked copy of one saved sync, as text, and the set of real values that were masked."""
    login, user_id = data["identity"]["login"], data["identity"]["id"]
    real = {login, str(user_id)}
    token = lambda prefix, node: "%s_masked_%s" % (prefix, hashlib.sha256((secret + node).encode("utf-8")).hexdigest()[:12])  # noqa: E731
    people = {login: "[owner]"}

    def person(name):
        if isinstance(name, str) and name:
            real.add(name)
            return people.setdefault(name, "[user %d]" % (len(people) + 1))
        return name

    issues = {}
    for node, issue in data["issues"].items():
        real.update([node, str(issue["id"]), str(issue["repo_id"])])
        masked = dict(issue, node_id=token("I", node), id="[issue id]", repo_id="[repository id]", body="[not copied]" if issue.get("body") else "",
                      author=person(issue.get("author")), assignees=[person(one) for one in issue.get("assignees") or []])
        masked["comments"] = [dict(comment, body="[not copied]", id="[comment id]", **({"author": person(comment["author"])} if "author" in comment else {})) for comment in issue.get("comments") or []]
        events = []
        for event in issue.get("events") or []:
            event = dict(event, detail=dict(event.get("detail") or {}))
            if "actor" in event:
                event["actor"] = person(event["actor"])
            for key, value in list(event["detail"].items()):
                if key == "node_id" and isinstance(value, str) and value:
                    real.add(value)
                    event["detail"][key] = token("PR", value)
                elif key in ("actor", "assignee", "assigner", "author", "user", "login", "requested_reviewer"):
                    event["detail"][key] = person(value)
            for found in re.findall(r"\d{6,}", event.get("key", "")):
                real.add(found)
            event["key"] = re.sub(r"id:\d+", "id:[event id]", event.get("key", ""))
            if event["key"].startswith("cross-referenced:"):
                event["key"] = "cross-referenced:%s:%s" % (event["detail"].get("node_id"), event.get("created_at"))
            events.append(event)
        masked["events"] = events
        issues[masked["node_id"]] = masked
    repos = {"[repository id]": dict(repo, id="[repository id]") for repo in data.get("repos", {}).values()}
    text = json.dumps(dict(data, identity={"id": "[user id]", "login": "[owner]"}, issues=issues, repos=repos), indent=1, sort_keys=True)
    for name, word in sorted(people.items(), key=lambda pair: -len(pair[0])):
        text = text.replace(name, word)
    return text + "\n", real


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 1
    real_folder, out = argv
    with open(os.path.join(real_folder, "assigned.json"), encoding="utf-8") as f:
        data = json.load(f)
    if data.get("source") != "live":
        print("from_sync: that folder does not hold a real sync. Nothing was written.")
        return 1
    text, real = mask(data, secret_of(real_folder))
    left = sorted(value for value in real if value in text)
    if left or re.search(r"\b(I|PR|IC|U|R)_kw[A-Za-z0-9]", text):
        print("from_sync: %d real values that should be masked are still there. Nothing was written." % (len(left) or 1))
        return 1
    source = os.path.join(out, "source", "github", "assigned")
    os.makedirs(source, exist_ok=True)
    with open(os.path.join(source, "assigned.json"), "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    done = subprocess.run([sys.executable, NORMALIZE, "--root", os.path.join(out, "source"), "--out", out, "--map", STATUS_MAP], capture_output=True, text=True)
    if done.returncode != 0:
        print("from_sync: the canonical model skill stopped: %s" % (done.stdout + done.stderr).strip()[-400:])
        return 1
    masked = json.loads(text)
    at = masked["last_successful_sync"]
    identities = ["github:%s" % node for node, issue in sorted(masked["issues"].items(), key=lambda pair: pair[1]["number"])]
    files = {
        "sync-runs.md": ["# Synchronization runs: local context of %s" % at[:10], "",
                         "From a REAL run of `participant/skills/github-read-assigned/sync.py --source live`, made by the participant with their own",
                         "read-only token. Written by `participant/skills/scrum-standup-digest/from_sync.py` from that run's own saved account of itself.",
                         "Node IDs are masked. The run's scope, in its own words: %s." % masked.get("scope"), "",
                         "## github-read-assigned:%s" % at, "", "- system: github", "- retrieved_at: %s" % at, "- result: completed", "- items: %s" % (", ".join(identities) or "none"),
                         "- scope: %s. Pull requests the sync left out, because a pull request is not a work item: %s" % (masked.get("scope"), masked.get("pulls_left_out")), ""],
        "redaction.md": ["# Names to take out of anything meant for sharing", "",
                         "None are listed. Logins were already replaced when the real sync was masked, and the titles are of made-up work the participant typed",
                         "into their own sandbox repository. The digest still takes out anything with the shape of an email address, a customer number or a telephone number.", ""],
        "README.md": ["# Real local context of %s, masked" % at[:10], "",
                      "Built by `participant/skills/scrum-standup-digest/from_sync.py` from a real GitHub sync the participant ran. **The real output is not in this",
                      "repository.** What is here:", "",
                      "- `source/github/assigned/assigned.json`: the masked copy of what the sync saved. Logins, the user id, node IDs and other numeric ids are replaced,",
                      "  and the text of bodies and comments is not copied. Issue numbers, titles, labels, states and times are as GitHub sent them.",
                      "- `items/`: canonical work-item records, written from that masked copy by the approved skill `participant/skills/context-work-item-model/normalize.py`.",
                      "- `sync-runs.md`: the run, its time and the identities it retrieved.", "- `report.md`: the canonical model skill's own report of what it did.",
                      "- No `notes/` folder: nobody wrote a note for this day.", "",
                      "An identity such as `github:I_masked_...` stands for a real GitHub node ID. The same real item has the same masked identity on every day.", ""],
    }
    for name, lines in files.items():
        with open(os.path.join(out, name), "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines))
    print("from_sync: masked %d real values, and wrote the context of %d real issues retrieved at %s." % (len(real), len(identities), at))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
