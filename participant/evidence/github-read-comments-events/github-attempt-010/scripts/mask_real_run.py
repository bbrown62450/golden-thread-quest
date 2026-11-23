#!/usr/bin/env python3
"""Makes the masked copies of the REAL run: what the four syncs printed, and the comments file they wrote.

    mask_real_run.py FOLDER RUN1 RUN2 RUN3 RUN4

FOLDER is the scratch folder of the real run, outside this repository. RUN1 to RUN4 are the saved outputs of the four
syncs. It contacts nothing. It writes two files:

    logs/live-runs.txt                                             what the four syncs printed
    participant/context/github/comments-sample-real-masked.md      the comments file after the fourth sync

and changes nothing in them but these values:

    the owner's login                              ->  [owner]
    each GitHub node ID                            ->  [issue node id], [comment node id 1], [event node id 1] ...
    each GitHub numeric id of a comment            ->  [comment id 1] ...
    the scratch folder's path                      ->  SCRATCH

The same real value always gets the same masked name, in both files, so a reader can still follow one comment from sync to
sync. It stops if a masked value is still in what it would write.

Only the participant can run this again, because only their computer has the real files.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
LOG = os.path.join(HERE, "..", "logs", "live-runs.txt")
COPY = os.path.join(ROOT, "participant", "context", "github", "comments-sample-real-masked.md")
KINDS = {"I": "issue node id", "IC": "comment node id", "PR": "pull request node id"}
NODE = re.compile(r"\b([A-Z]{1,3})(\\?_)([A-Za-z0-9]*kw|lA)([A-Za-z0-9_-]{6,})")
NOTE = ("**This is a masked copy.** The file was written by the real syncs of issue 1 of the participant's private sandbox repository. The\n"
        "original is kept outside this repository. The owner's login, every GitHub node ID and every GitHub numeric id of a comment are\n"
        "replaced, and shown in square brackets. Nothing else was changed, so the checksums in the marker lines are those of the real\n"
        "text. Every comment in it is made-up text the participant typed for this quest. The made-up GitHub's version of this file is\n"
        "`comments-sample.md`, beside it.\n")


def main(argv):
    if len(argv) != 5:
        print(__doc__)
        return 1
    folder = argv[0].rstrip("/")
    with open(os.path.join(folder, "comments.md"), encoding="utf-8") as f:
        copy = f.read()
    runs = []
    for path in argv[1:]:
        with open(path, encoding="utf-8") as f:
            runs.append(f.read())
    owner = re.search(r'^- repository: "([^/"]+)/', copy, re.M).group(1)
    names, real = {}, set([owner])

    def node(found):
        key = found.group(0).replace("\\", "")
        kind = KINDS.get(found.group(1), "event node id")
        if key not in names:
            count = 1 + sum(1 for shown in names.values() if shown.startswith("[" + kind))
            names[key] = "[%s]" % kind if kind == "issue node id" else "[%s %d]" % (kind, count)
            real.add(key)
        return names[key]

    def mask(text):
        text = NODE.sub(node, text)
        for match in re.findall(r"GitHub(?:'s)? id:? (\d{6,})", text):       # in the order they come, so the numbers follow the comments
            if match not in names:
                names[match] = "[comment id %d]" % (1 + sum(1 for shown in names.values() if shown.startswith("[comment id")))
                real.add(match)
        for value in sorted((v for v in names if v.isdigit()), key=len, reverse=True):
            text = text.replace(value, names[value])
        return text.replace(folder, "SCRATCH").replace("/private" + folder, "SCRATCH").replace(owner, "[owner]")

    copy = mask(copy)
    head, rest = copy.split("\n", 1)
    copy = head + "\n\n" + NOTE + rest
    steps = ["Sync 1. The first sync of the real issue",
             "Sync 2. Nothing had changed on GitHub (criterion 2)",
             "Sync 3. Before it, the participant by hand, on GitHub's web page: EDITED one comment, ADDED one, DELETED one (criteria 3, 4 and 7)",
             "Sync 4. Nothing had changed since sync 3 (criterion 2)"]
    command = "$ python3 participant/skills/github-read-comments-events/sync.py --source live --repo [owner]/gtq-sandbox --issue 1 --out SCRATCH"
    log = ["The real syncs. github-read-comments-events, attempt github-attempt-010",
           "A masked copy of what four syncs printed in the participant's own terminal, made by scripts/mask_real_run.py.",
           "The issue is issue 1 of the participant's private sandbox repository. Every request was a GET. The edit, the new comment and the",
           "deletion before sync 3 were made by the participant by hand. The skill changed nothing on GitHub.",
           "Masked: the owner's login, every node ID, every numeric id of a comment, and the scratch folder. Nothing else was changed.", ""]
    for title, text in zip(steps, runs):
        log += ["=" * 78, title, command, "-" * 78, mask(text).rstrip("\n"), ""]
    log = "\n".join(log) + "\n"
    for text in (copy, log):
        left = [value for value in real if value in text]
        if left or re.search(r"\b(IC|I|PR|AE|LE)\\?_[A-Za-z0-9]", text):
            print("mask_real_run: a value that should be masked is still there. Nothing was written.")
            return 1
    for path, text in ((LOG, log), (COPY, copy)):
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
    print("mask_real_run: wrote logs/live-runs.txt and comments-sample-real-masked.md. Values masked: %d" % len(real))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
