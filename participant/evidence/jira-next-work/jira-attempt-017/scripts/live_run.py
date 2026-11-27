#!/usr/bin/env python3
"""The run against the REAL Jira sandbox for the quest jira-next-work. A PERSON runs this, in their own terminal, with
JIRA_BASE_URL, JIRA_EMAIL and JIRA_API_TOKEN set there. The AI assistant does not run it.

    python3 live_run.py

IT ONLY READS JIRA. There is nothing to confirm and no fingerprint, because nothing is written to Jira.

    1  copy every item of the project SCRUM into local records     reads only. No titles and no people are copied
    2  rank the records                                            contacts nothing
    3  rank them again, with the same clock value                  must give the same recommendation, byte for byte
    4  copy again, into a temporary file that is then deleted      to compare Jira's listing with the first one.
                                                                   The records that were ranked are NOT written over

The clock value for the ranking is taken ONCE, here, from this computer's clock, and handed to both rankings with
--now. `rank.py` itself never reads a clock.

It writes, inside participant/:
    context/jira/next-work/records-sandbox.json           the local records
    context/jira/next-work/recommendation-sandbox.md      the recommendation
    evidence/.../logs/live-NN-*.txt                       what each step printed, with the site's address removed
    evidence/.../logs/live-05-snapshots.txt               the four snapshots of Jira, and whether they are the same

A step passes only if it ends with the status expected AND says the words expected. Otherwise the sequence stops.
"""
import datetime
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ATTEMPT = os.path.dirname(HERE)
PARTICIPANT = os.path.abspath(os.path.join(ATTEMPT, "..", "..", ".."))
SKILL = os.path.join(PARTICIPANT, "skills", "jira-next-work")
CONTEXT = os.path.join(PARTICIPANT, "context", "jira", "next-work")
LOGS = os.path.join(ATTEMPT, "logs")
RECORDS = os.path.join(CONTEXT, "records-sandbox.json")
PROJECT = "SCRUM"


def step(number, name, what, args, words, save_output=True):
    log = os.path.join(LOGS, "live-%02d-%s.txt" % (number, name))
    done = subprocess.run([sys.executable] + args + (["--log", log] if not save_output else []), capture_output=True, text=True)
    print("\n--- step %d: %s" % (number, what))
    print(done.stdout)
    if done.returncode not in (0, 1, 2) or (done.stderr.strip() and not done.stdout.strip()):
        print("    THE PROGRAM FAILED and printed no result. Its last words: %s" % (done.stderr.strip().split("\n")[-1][:200] if done.stderr.strip() else "none"))
    if save_output:                      # rank.py prints no site address and has no --log of its own
        os.makedirs(LOGS, exist_ok=True)
        with open(log, "w", encoding="utf-8") as f:
            f.write(done.stdout)
    print("    exit status %d. Saved as logs/%s" % (done.returncode, os.path.basename(log)))
    if done.returncode != 0 or words not in done.stdout:
        print("\nSTOPPED: this step was expected to end with status 0 and to say: %s" % words)
        print("Nothing was changed in Jira: these commands can only read. Tell the assistant which step stopped.")
        sys.exit(1)
    return done.stdout


def main():
    copy = [os.path.join(SKILL, "sync.py"), "copy", "--source", "live", "--project", PROJECT, "--out", RECORDS]
    first = step(1, "copy", "copy every item of %s into local records. Reads only" % PROJECT, copy, "Every one was a GET with no body", save_output=False)
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rank = [os.path.join(SKILL, "rank.py"), "rank", "--records", RECORDS, "--now", now, "--also-rule", "due-first", "--out", os.path.join(CONTEXT, "recommendation-sandbox.md")]
    one = step(2, "rank", "rank the records, with the clock value %s. Contacts nothing" % now, rank, "sha256 of the recommendation:")
    two = step(3, "rank-again", "rank them again with the same clock value. Expected: the same, byte for byte", rank, "sha256 of the recommendation:")
    if one != two:
        print("\nSTOPPED: the two rankings did not print the same thing. Tell the assistant.")
        return 1
    scratch = tempfile.mkdtemp(prefix="gtq-copy-again-")
    try:
        second = [os.path.join(SKILL, "sync.py"), "copy", "--source", "live", "--project", PROJECT, "--out", os.path.join(scratch, "records.json")]
        again = step(4, "copy-again", "copy again into a temporary file, to compare Jira's listing. Reads only", second, "Every one was a GET with no body", save_output=False)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    codes = [re.findall(r"Snapshot of Jira (?:before|after) the copy:\s+([0-9a-f]{16})", text) for text in (first, again)]
    same = len(codes[0]) == 2 and len(codes[1]) == 2 and len(set(codes[0] + codes[1])) == 1
    lines = ["The four snapshots of Jira, before and after each of the two copies: %s" % ", ".join(codes[0] + codes[1]),
             "They are all the same: the four listings of the project agree, from the first read to the last." if same else
             "THEY ARE NOT ALL THE SAME. These commands only read, so someone else changed an item meanwhile, or Jira's search was behind.",
             "A snapshot is of every item's key and last-updated time, as a search lists them. It is not proof that nothing changed: a search can be behind.",
             "The records that were ranked are the ones from the first copy. The second copy went to a temporary file and was deleted."]
    with open(os.path.join(LOGS, "live-05-snapshots.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n" + "\n".join(lines))
    if not same:
        print("\nSTOPPED: the snapshots differ. Nothing was changed by these commands. Tell the assistant.")
        return 1
    print("\nDONE. Jira was only read. The two rankings were identical.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
