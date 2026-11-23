#!/usr/bin/env python3
"""Makes the masked copies of the local link and the result record of the REAL run.

    mask_real_records.py FOLDER      FOLDER is the scratch folder of the real run, outside this repository

It reads FOLDER/linked.md and FOLDER/results/create-issue.md, which the participant's real `confirm` wrote, and
writes masked copies to the two paths the quest names. It contacts nothing. It changes nothing but these values:

    the owner's login                    ->  [owner]
    the issue's node ID                  ->  [node id]
    the repository's id                  ->  [repository id]
    GitHub's numeric id of the issue     ->  [issue id]
    the name typed with --confirmed-by   ->  the participant

and it adds one paragraph under each file's heading saying that the file is a masked copy. Everything else,
including the issue number, the times, the fingerprint, the checksums and the comparison, is as the real run
wrote it. It stops if any of the masked values is still in what it would write.

Only the participant can run this again, because only their computer has the real files.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
LINK = os.path.join(ROOT, "participant", "context", "github", "new-issue", "linked.md")
RESULT = os.path.join(ROOT, "participant", "context", "github", "results", "create-issue.md")
NOTE = ("**This is a masked copy.** The file was written by the real run on the participant's private sandbox repository, when the participant confirmed\n"
        "the creation of issue 4. The original is kept outside this repository. Five values are replaced and shown in square brackets, or as\n"
        "\"the participant\": the owner's login, the issue's node ID, the repository's id, GitHub's numeric id of the issue, and the name typed as\n"
        "confirmer. Nothing else was changed. The made-up run's version of this file is kept beside it under a name that says so.\n")


def main(argv):
    if len(argv) != 1:
        print(__doc__)
        return 1
    with open(os.path.join(argv[0], "linked.md"), encoding="utf-8") as f:
        link = f.read()
    with open(os.path.join(argv[0], "results", "create-issue.md"), encoding="utf-8") as f:
        result = f.read()
    front = dict((line.split(": ", 1)[0], json.loads(line.split(": ", 1)[1])) for line in link[4:link.index("\n---\n", 3)].split("\n"))
    owner, name = front["repository"].split("/")[0], front["confirmed_by"]
    secret = {owner: "[owner]", front["node_id"]: "[node id]", str(front["repository_id"]): "[repository id]", str(front["id"]): "[issue id]"}

    def mask(text):
        text = text.replace("repository_id: %d" % front["repository_id"], 'repository_id: "[repository id]"').replace("\nid: %d" % front["id"], '\nid: "[issue id]"')
        for real, shown in secret.items():
            text = text.replace(real, shown)
        return re.sub(r'(confirmed_by: |confirmed by: )%s' % re.escape(json.dumps(name)), r'\1"the participant"', text)
    link, result = mask(link), mask(result)
    link = link.replace("\n# Local link: draft.md\n", "\n# Local link: draft.md\n\n" + NOTE, 1)
    result = result.replace("\n# Result records: issues created\n", "\n# Result records: issues created\n\n" + NOTE, 1) if result.startswith("\n") else \
        result.replace("# Result records: issues created\n", "# Result records: issues created\n\n" + NOTE, 1)
    for text in (link, result):
        if any(real in text for real in secret) or json.dumps(name) in text or NOTE not in text:
            print("mask_real_records: a value that should be masked is still there, or the note is missing. Nothing was written.")
            return 1
    for path, text in ((LINK, link), (RESULT, result)):
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
    print("mask_real_records: wrote the masked local link and the masked result record of the real run, issue %d" % front["number"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
