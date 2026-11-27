#!/usr/bin/env python3
"""Asks the operating system one question about each file named: may the program that runs this open it for writing?

    zone_probe.py FILE [FILE ...]

IT WRITES NOTHING. For each file it opens the file for reading and writing at once, and closes it again without
writing a byte. An open like that changes nothing in the file: not its contents, not its length, and not the time it
was last changed. It only succeeds if the program is allowed to write there. The file's checksum and last-changed
time are taken before and after and compared, and the result is printed.

It is for testing a sandbox around the shell. A rule that reads the text of a shell command cannot see what a
program does once it is running. This IS a running program, started by the shell, trying to open a file for writing.
If the sandbox holds, the operating system refuses the open.

It never creates a file: a file that is not there is reported as not there. So it cannot leave anything behind,
whether the sandbox works or not.

For each file one line:
    REFUSED BY THE OPERATING SYSTEM    the open was refused with "operation not permitted", which is what a sandbox gives
    NOT WRITABLE BY ITS OWN SETTINGS   the open was refused because the file itself is marked read-only, or belongs to
                                       someone else. That says nothing about a sandbox, and is not counted as refused
    OPENED FOR WRITING                 the open succeeded: this program MAY write there. Nothing was written
    NOT THERE                          no such file, or it cannot be read

Exit code: 0 if every file was refused by the operating system, 1 if any was opened or was only read-only, 2 if any
was not there.
"""
import errno
import hashlib
import os
import sys


def state(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest(), os.stat(path).st_mtime_ns, os.stat(path).st_size


def probe(path):
    """One of "refused", "opened", "missing", and whether the file is byte for byte and time for time as it was."""
    if not os.path.isfile(path):
        return "missing", True
    try:
        before = state(path)
    except OSError:
        return "missing", True
    try:
        with open(path, "r+b"):
            pass                       # opened for reading and writing, and closed. Nothing is written
        result = "opened"
    except PermissionError as refusal:
        # "Operation not permitted" is what a sandbox answers. "Permission denied" is the file's own read-only mark.
        result = "refused" if refusal.errno == errno.EPERM else "readonly"
    return result, state(path) == before


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    words = {"refused": "REFUSED BY THE OPERATING SYSTEM", "readonly": "NOT WRITABLE BY ITS OWN SETTINGS", "opened": "OPENED FOR WRITING", "missing": "NOT THERE"}
    results = []
    for path in argv:
        result, untouched = probe(path)
        results.append(result)
        print("%-32s %s%s" % (words[result], path, "" if result == "missing" else "   (the file is unchanged: %s)" % ("yes" if untouched else "NO")))
    print("%d refused, %d opened for writing, %d read-only by their own settings, %d not there. This program wrote nothing."
          % (results.count("refused"), results.count("opened"), results.count("readonly"), results.count("missing")))
    return 2 if "missing" in results else 1 if "opened" in results or "readonly" in results else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
