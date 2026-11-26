#!/usr/bin/env python3
"""A small workflow that can be stopped at any moment and resumed. For the quest base-camp-interruption-recovery.

    workflow.py run    --items ITEMS.json --out DIR      start, or resume if DIR holds a run that did not finish
    workflow.py status --out DIR                         say whether the run in DIR finished, and what it left

What it does. It reads a list of made-up work items. For each it writes one card, DIR/cards/<id>.md. When every card
is written it builds DIR/index.md FROM THE CARD FILES, so a card that was wrong would make the index wrong.

HOW A CARD OR THE INDEX IS WRITTEN (write_whole). Never under its final name. The content goes to a temporary name
in the same folder (".<name>.tmp-<process id>"), is pushed to the disk, and is then renamed to the final name. A
rename within one folder is one step: at every moment the final name holds the old whole file, or the new whole file,
or nothing. The folder is then pushed to the disk too, so that the rename itself is kept.

WHERE PROGRESS IS RECORDED. DIR/progress.jsonl. One line is added, and pushed to the disk, as each thing finishes:

    run-started    a fingerprint of the items and the number of the card format, so that a resume with another
                   input, or by a version that writes cards differently, is refused
    item-done      the item, and the checksum and length of the card that was written for it
    index-done     the checksum of the index
    run-finished
    run-resumed    added by a run that found the record of a run that did not finish
    run-reopened   added by a run that found a finished run with a card or the index missing or changed
    cut-short-line-closed   added by a resume, after a line or lines at the end that an interruption cut short

THE RECORD IS THE ONE FILE THAT IS WRITTEN IN PLACE. It is added to, not renamed into place, so an interruption can
leave its last line cut short. That is why each line ends with a short check of its own text, and why a line that
fails the check is never believed. The record is only ever added to. It is never rewritten and never deleted.

RESUMING. A run is finished when the last line of its record is "run-finished". A run that finds a record that is
not finished is resuming. It says so. Then:

    lines at the end that are cut short, or fail their check    ignored, and said. They are closed off. Their items are done again
    a record with no whole line in it at all                    the run stopped while writing its first line. It is begun again, and said
    a bad line with good lines after it that do not close it    REFUSED. The record is damaged. A person looks
    temporary files left by the run that stopped                 listed, and removed. Never used
    an item recorded as done, whose card is there and has the
      checksum recorded                                          SKIPPED
    an item recorded as done, whose card is missing or differs   written again, and said
    a card that is there with no record of it                    written again, and said. It is whole, since only a
                                                                 rename can put it there, but nothing says what input
                                                                 it was made from
    the items are not the items the run started with             REFUSED
    cards in the folder and no progress record at all            REFUSED. The record was lost or deleted. It does not start over

Only one run at a time may work in DIR. A run holds a lock on DIR/lock for as long as it lives. The system lets go
of that lock when the process ends, however it ends, so a run that was killed leaves no lock behind.

STOPPING IT ON PURPOSE, for tests. Two settings in the environment, read only by this file:

    GTQ_STOP_AT=<where>     at that point the process kills itself with SIGKILL, which cannot be caught: no clean-up
                            code runs, in this file or in Python.
    GTQ_PAUSE_AT=<where>    at that point it prints "PAUSED AT <where>" and waits, so that another process can kill it.

<where> is "<id>:<point>" for a card or "index:<point>" for the index, and <point> is one of
    mid-write      half the content is in the temporary file
    before-rename  the whole content is in the temporary file, which has not been renamed
    after-rename   the file is under its final name, and its progress line is not written
    mid-record     half of its progress line is written
Or <where> is one of these, for the lines of the record that are not about a card:
    start:created  the record file has just been created and is empty
    start:mid-record, resume:mid-record, reopen:mid-record, finish:mid-record, close:mid-record
                   half of the run-started, run-resumed, run-reopened, run-finished or closing line is written

WHAT THIS DOES NOT SHOW. A killed process is not a power cut. What the process had handed to the system before it
died is still written out. This file asks the disk to keep each file, each folder it changes and each progress line
(F_FULLFSYNC on macOS, and plain fsync where that is refused or missing, without saying which), which is what a power
cut would test, and nothing here cuts the power.

Exit codes: 0 finished, or already finished. 1 refused. 3 stopped by an error from the system, such as a full disk:
run it again when the cause is gone. A killed run has no exit code of its own: the system reports the signal.
"""
import argparse
import fcntl
import hashlib
import json
import os
import signal
import sys
import time

RECORD = "progress.jsonl"
FORMAT = 1   # the number of the card format. Change it when card_of or index_of changes what it writes
POINTS = ("mid-write", "before-rename", "after-rename", "mid-record")


class Refused(Exception):
    """The run does not go on. The message is the reason."""


def say(text=""):
    print(text, flush=True)   # every line leaves at once, so a killed run's output is whole up to the kill


def sha(data):
    return hashlib.sha256(data).hexdigest()


def stop_here(where):
    """The test hooks. In ordinary use neither setting is there and this does nothing."""
    if os.environ.get("GTQ_STOP_AT") == where:
        sys.stdout.flush()
        os.kill(os.getpid(), signal.SIGKILL)
    if os.environ.get("GTQ_PAUSE_AT") == where:
        say("PAUSED AT %s" % where)
        time.sleep(60)


def to_disk(fd):
    """Ask that what was written is on the disk itself, not only handed to the system."""
    if hasattr(fcntl, "F_FULLFSYNC"):
        try:
            fcntl.fcntl(fd, fcntl.F_FULLFSYNC)
            return
        except OSError:
            pass
    os.fsync(fd)


def folder_to_disk(folder):
    fd = os.open(folder, os.O_RDONLY)
    try:
        to_disk(fd)
    finally:
        os.close(fd)


def write_whole(path, data, where):
    """Puts `data` under `path` so that the name never holds part of it. `where` names the stop points for tests."""
    folder, name = os.path.split(path)
    temporary = os.path.join(folder, ".%s.tmp-%d" % (name, os.getpid()))
    half = len(data) // 2
    with open(temporary, "wb") as f:
        f.write(data[:half])
        f.flush()
        stop_here(where + ":mid-write")
        f.write(data[half:])
        f.flush()
        to_disk(f.fileno())
    stop_here(where + ":before-rename")
    os.replace(temporary, path)          # the one step in which the file becomes real
    folder_to_disk(folder)
    stop_here(where + ":after-rename")


# ---------------------------------------------------------------- the progress record


def write_all(fd, data):
    """os.write may write less than it was given. This goes on until all of it is written, or raises."""
    while data:
        count = os.write(fd, data)
        if count <= 0:
            raise OSError("the system wrote nothing")
        data = data[count:]


def line_of(event):
    text = json.dumps(event, sort_keys=True, ensure_ascii=False)
    return "%s\t%s\n" % (text, sha(text.encode("utf-8"))[:16])


def parse(line):
    """The event a line of the record holds, or None if the line is cut short or fails its own check."""
    try:
        text, check = line.decode("utf-8").rsplit("\t", 1)
        event = json.loads(text) if check == sha(text.encode("utf-8"))[:16] else None
    except (ValueError, UnicodeDecodeError):
        return None
    return event if isinstance(event, dict) else None


def record(out, event, where=None):
    """Adds one line to the progress record and pushes it to the disk before returning."""
    data = line_of(event).encode("utf-8")
    path = os.path.join(out, RECORD)
    created = not os.path.exists(path)
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        if created:
            folder_to_disk(out)              # so that the record's own name is kept
            if where:
                stop_here(where + ":created")
        if where and os.environ.get("GTQ_STOP_AT") == where + ":mid-record":
            write_all(fd, data[:len(data) // 2])
            to_disk(fd)
        if where:
            stop_here(where + ":mid-record")
        write_all(fd, data)
        to_disk(fd)
    finally:
        os.close(fd)


def read_record(out):
    """Returns (events, note, ends_clean).
    events      the whole lines of the record, in order, without the closing lines. None if there is no record file.
    note        what is wrong with the end of the record, if an interruption cut it short. Otherwise None.
    ends_clean  False if something must be closed off before another line is added.
    Refuses a record with a bad line that later good lines do not close off: an interruption cannot leave that."""
    path = os.path.join(out, RECORD)
    if not os.path.exists(path):
        return None, None, True
    with open(path, "rb") as f:
        raw = f.read()
    lines = raw.split(b"\n")
    ends_with_newline = lines[-1] == b""
    lines = lines[:-1] if ends_with_newline else lines
    events, bad = [], []          # bad: the numbers of the bad lines met since the last good one
    for number, line in enumerate(lines, 1):
        event = parse(line)
        if event is None:
            bad.append(number)
            continue
        if bad:
            if event.get("event") != "cut-short-line-closed":
                raise Refused("line %d of the progress record is damaged, and the lines after it do not close it off. An interruption "
                              "cannot do that. The record is left as it is for a person to look at" % bad[0])
            bad = []
        if event.get("event") != "cut-short-line-closed":
            events.append(event)
    if bad:
        size = sum(len(lines[n - 1]) for n in bad)
        what = "line %d, the last, is" % bad[0] if len(bad) == 1 else "lines %d to %d, the last, are" % (bad[0], bad[-1])
        return events, "%s cut short or fail%s the check (%d bytes). Ignored: what was being recorded is done again" % (what, "s" if len(bad) == 1 else "", size), False
    return events, None, ends_with_newline or not lines     # a whole last line that only lacks its line end is believed


def repair_tail(out):
    """Closes off the end of a record that an interruption cut short, so that the next line added does not run into
    it. Nothing is removed: the cut-short text stays in the record. Safe to do again if it is itself interrupted."""
    path = os.path.join(out, RECORD)
    with open(path, "rb") as f:
        raw = f.read()
    lines = raw.split(b"\n")
    number = len(lines) - (1 if raw.endswith(b"\n") else 0)
    last_is_whole = number > 0 and parse(lines[number - 1]) is not None
    data = b"" if raw.endswith(b"\n") or not raw else b"\n"
    if not last_is_whole and raw:
        data += line_of({"event": "cut-short-line-closed", "line": number}).encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_APPEND)
    try:
        if os.environ.get("GTQ_STOP_AT") == "close:mid-record":
            write_all(fd, data[:len(data) // 2])
            to_disk(fd)
        stop_here("close:mid-record")
        write_all(fd, data)
        to_disk(fd)
    finally:
        os.close(fd)


# ---------------------------------------------------------------- the work


def read_items(path):
    try:
        with open(path, "rb") as f:
            raw = f.read()
        items = json.loads(raw.decode("utf-8"))["items"]
    except FileNotFoundError:
        raise Refused("there is no items file at the path given")
    except (ValueError, KeyError, TypeError, UnicodeDecodeError):
        raise Refused("the items file is not JSON with a list named items")
    if not isinstance(items, list) or not items:
        raise Refused("the items file lists no item")
    seen = set()
    for item in items:
        ok = (isinstance(item, dict) and isinstance(item.get("id"), str) and item["id"].isascii() and item["id"].replace("-", "").isalnum()
              and isinstance(item.get("title"), str) and "\n" not in item["title"] and isinstance(item.get("points"), int) and 0 <= item["points"] <= 100
              and isinstance(item.get("owner_role"), str))
        if not ok or item["id"].lower() in seen:      # ids that differ only in capitals would be one file on some disks
            raise Refused("an item has no usable id, title, points and owner_role, or two items share an id, capitals aside")
        seen.add(item["id"].lower())
    # The fingerprint is of what the items say, not of how the file is laid out, so tidying the file is not "another input".
    return items, sha(json.dumps(items, sort_keys=True, ensure_ascii=False).encode("utf-8"))


def card_of(item):
    """The card for one item, as bytes. The same item always gives the same bytes."""
    lines = ["# %s: %s" % (item["id"], item["title"]), "", "- Points: %d" % item["points"], "- Owner: the %s" % item["owner_role"], "",
             "## Checklist", ""]
    lines += ["- [ ] Step %d of %d for %s" % (n, 12 + item["points"], item["id"]) for n in range(1, 13 + item["points"])]
    lines += ["", "End of card %s." % item["id"], ""]
    return "\n".join(lines).encode("utf-8")


def index_of(out, items):
    """The index, built from the card files as they are on disk. A card that was cut short would show here."""
    lines = ["# Index of cards", "", "| Card | Title | Lines | sha256 of the card file |", "|---|---|---|---|"]
    for item in items:
        with open(os.path.join(out, "cards", item["id"] + ".md"), "rb") as f:
            data = f.read()
        title = data.split(b"\n", 1)[0].decode("utf-8")[2:]
        lines.append("| %s | %s | %d | %s |" % (item["id"], title.split(": ", 1)[-1], data.count(b"\n"), sha(data)))
    lines += ["", "%d cards." % len(items), ""]
    return "\n".join(lines).encode("utf-8")


def temporary_files(out):
    found = []
    for folder in (out, os.path.join(out, "cards")):
        if os.path.isdir(folder):
            found += [os.path.join(folder, name) for name in sorted(os.listdir(folder)) if ".tmp-" in name]
    return found


def file_state(path, wanted_sha):
    """"same" if the file is there with that checksum, "missing", or "differs"."""
    if not os.path.exists(path):
        return "missing"
    with open(path, "rb") as f:
        return "same" if sha(f.read()) == wanted_sha else "differs"


def take_lock(out):
    fd = os.open(os.path.join(out, "lock"), os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(fd)
        raise Refused("another run is working in this folder now: it holds the lock. Two runs at once would write over each other. "
                      "This run wrote no card, no index and no line of the progress record")
    except OSError as err:
        os.close(fd)
        raise Refused("the lock could not be taken (%s). This folder may be on a disk that does not support it. Nothing was written" % type(err).__name__)
    os.ftruncate(fd, 0)
    write_all(fd, ("last held by process %d\n" % os.getpid()).encode("ascii"))
    return fd   # kept open for the life of the process. The system releases it when the process ends, however it ends


def cmd_run(args):
    items, items_sha = read_items(args.items)
    out = args.out
    fresh = not os.path.isdir(os.path.join(out, "cards"))
    os.makedirs(os.path.join(out, "cards"), exist_ok=True)
    if fresh:
        folder_to_disk(out)
        folder_to_disk(os.path.dirname(os.path.abspath(out)))
    lock = take_lock(out)
    events, torn, ends_clean = read_record(out)
    done, index_done, finished = {}, None, False
    start = {"event": "run-started", "items": len(items), "items_fingerprint": items_sha, "card_format": FORMAT}
    if events is None:
        there = sorted(n for n in os.listdir(os.path.join(out, "cards")) if ".tmp-" not in n)
        if there or os.path.exists(os.path.join(out, "index.md")):
            raise Refused("there are %d cards in this folder and no progress record. The record was lost or deleted. This workflow does "
                          "not start over on top of files it has no record of. Use an empty folder, or put the record back" % len(there))
        say("STARTING. No progress record is in the folder, so this is a new run of %d items." % len(items))
        record(out, start, "start")
    elif not events:
        say("RESUMING AN INTERRUPTED RUN. The progress record is there and has no whole line in it: the run stopped while writing its first line.")
        if torn:
            say("  THE PROGRESS RECORD: %s." % torn)
        repair_tail(out)
        record(out, start, "start")
        record(out, {"event": "run-resumed", "number": 1, "items_recorded_done": 0}, "resume")
    else:
        started = events[0] if events[0].get("event") == "run-started" else None
        if started is None:
            raise Refused("the progress record does not begin with a run-started line. It is left as it is for a person to look at")
        if started.get("card_format") != FORMAT:
            raise Refused("this run was started by a version of the workflow that writes cards in another format (%s, and this is %s). Resuming "
                          "would mix the two. Use another folder. The progress record is left as it is" % (started.get("card_format"), FORMAT))
        if started.get("items_fingerprint") != items_sha:
            raise Refused("the items are not the items this run started with (the fingerprint differs). A run is resumed with the "
                          "input it began with. For another input, use another folder. The progress record is left as it is")
        for event in events:
            if event.get("event") == "item-done":
                done[event["id"]] = event
            elif event.get("event") == "index-done":
                index_done = event
        finished = events[-1].get("event") == "run-finished"      # finished means: nothing was recorded after the finish
        resumes = sum(1 for e in events if e.get("event") == "run-resumed")
        if finished:
            say("ALREADY FINISHED. The last line of the progress record is run-finished. Each file is checked against the record.")
        else:
            last = events[-1]
            say("RESUMING AN INTERRUPTED RUN. The progress record does not end with a run-finished line.")
            say("  It was interrupted %s." % ("before any item was recorded" if not done else
                                              "after the index was recorded and before the run was marked finished" if last.get("event") == "index-done" else
                                              "after %d of %d items were recorded as done. The last whole line recorded: %s%s"
                                              % (len(done), len(items), last.get("event"), " " + last["id"] if "id" in last else "")))
            say("  This is resume number %d of this run." % (resumes + 1))
        if torn:
            say("  THE PROGRESS RECORD: %s." % torn)
        if not ends_clean:
            repair_tail(out)
        if not finished:
            record(out, {"event": "run-resumed", "number": resumes + 1, "items_recorded_done": len(done)}, "resume")
        left = temporary_files(out)
        for path in left:
            say("  LEFT BY THE RUN THAT STOPPED: temporary file %s, %d bytes. Removed. It was never under a final name and is not used."
                % (os.path.relpath(path, out), os.path.getsize(path)))
            os.remove(path)
        if not left and not finished:
            say("  No temporary file was left behind.")

    def about_to_write():
        """A finished run that needs something written again is no longer finished, and the record says so first."""
        nonlocal finished
        if finished:
            record(out, {"event": "run-reopened", "why": "a file recorded as done is missing or is not the file recorded"}, "reopen")
            finished = False

    reopened = finished
    skipped, written = [], []
    for item in items:
        path = os.path.join(out, "cards", item["id"] + ".md")
        before = done.get(item["id"])
        if before:
            state = file_state(path, before["sha256"])
            if state == "same":
                say("  %s  skipped: recorded as done, and its card is there with the checksum recorded" % item["id"])
                skipped.append(item["id"])
                continue
            say("  %s  RECORDED AS DONE, and its card %s. Written again." % (item["id"], "is missing" if state == "missing" else "is not the file that was recorded"))
        elif os.path.exists(path) and events is not None:
            say("  %s  a card is under its final name with no whole record of it: the run stopped after the rename and before its record was complete. Written again." % item["id"])
        about_to_write()
        data = card_of(item)
        write_whole(path, data, item["id"])
        record(out, {"event": "item-done", "id": item["id"], "sha256": sha(data), "bytes": len(data)}, item["id"])
        say("  %s  written (%d bytes), and recorded" % (item["id"], len(data)))
        written.append(item["id"])

    index_path = os.path.join(out, "index.md")
    data = index_of(out, items)
    if index_done and not written and file_state(index_path, index_done["sha256"]) == "same" and sha(data) == index_done["sha256"]:
        say("  index  skipped: recorded as done, it is there with the checksum recorded, and the cards give the same index")
    else:
        if index_done:
            say("  index  recorded as done, and %s. Built again." % ("cards were written again since" if written else "it is missing or is not the file that was recorded"))
        about_to_write()
        write_whole(index_path, data, "index")
        record(out, {"event": "index-done", "sha256": sha(data), "bytes": len(data)}, "index")
        say("  index  built from the %d card files (%d bytes), and recorded" % (len(items), len(data)))
        written.append("index")
    if not finished:
        record(out, {"event": "run-finished", "items": len(items)}, "finish")
    if reopened and written:
        say("  THE RUN HAD FINISHED, and was reopened: the record now holds a run-reopened line and a second run-finished line.")
    say("")
    say("FINISHED. Skipped as already done: %d%s. Written in this run: %d%s."
        % (len(skipped), " (%s)" % ", ".join(skipped) if skipped else "", len(written), " (%s)" % ", ".join(written) if written else ""))
    os.close(lock)
    return 0


def cmd_status(args):
    out = args.out
    events, torn, _ = read_record(out)
    if events is None:
        say("NO RUN: there is no progress record in this folder.")
        return 0
    if os.path.exists(os.path.join(out, "lock")):
        fd = os.open(os.path.join(out, "lock"), os.O_RDONLY)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(fd, fcntl.LOCK_UN)
        except OSError:
            say("A RUN IS WORKING IN THIS FOLDER NOW: it holds the lock. What follows is how far it has got, and may be out of date at once.")
        finally:
            os.close(fd)
    done = [e["id"] for e in events if e.get("event") == "item-done"]
    started = events[0] if events and events[0].get("event") == "run-started" else {}
    finished = bool(events) and events[-1].get("event") == "run-finished"
    resumes = sum(1 for e in events if e.get("event") == "run-resumed")
    say("FINISHED: the last line of the progress record is run-finished." if finished else
        "INTERRUPTED: the progress record does not end with a run-finished line. A run stopped partway.")
    say("  Items in the run: %s. Recorded as done: %d%s." % (started.get("items", "?"), len(set(done)), " (%s)" % ", ".join(sorted(set(done))) if done else ""))
    say("  Index recorded as done: %s. Times this run was resumed: %d. Times it was reopened after finishing: %d."
        % ("yes" if any(e.get("event") == "index-done" for e in events) else "no", resumes, sum(1 for e in events if e.get("event") == "run-reopened")))
    if torn:
        say("  The progress record: %s." % torn)
    left = temporary_files(out)
    say("  Temporary files left in the folder: %d%s." % (len(left), "".join(" %s (%d bytes)" % (os.path.relpath(p, out), os.path.getsize(p)) for p in left)))
    unrecorded = sorted(name[:-3] for name in os.listdir(os.path.join(out, "cards")) if name.endswith(".md") and name[:-3] not in done) if os.path.isdir(os.path.join(out, "cards")) else []
    if unrecorded:
        say("  Cards under a final name with no record of them: %s. Each got there by a rename, so each is a whole file. A resume writes "
            "again those that are in the items file." % ", ".join(unrecorded))
    if not finished:
        say("  To recover: run the same `run` command again, with the same items file and this folder. Do not delete the progress record.")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="A workflow that can be stopped at any moment and resumed.")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run")
    run.add_argument("--items", required=True)
    run.add_argument("--out", required=True)
    status = commands.add_parser("status")
    status.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    try:
        return cmd_run(args) if args.command == "run" else cmd_status(args)
    except Refused as refusal:
        say("")
        say("REFUSED: %s." % refusal)
        return 1
    except OSError as error:
        say("")
        say("STOPPED BY AN ERROR FROM THE SYSTEM: %s. This run did not finish. What it had recorded is kept. Run the same command "
            "again when the cause is gone: it will resume." % type(error).__name__)
        return 3


if __name__ == "__main__":
    sys.exit(main())
