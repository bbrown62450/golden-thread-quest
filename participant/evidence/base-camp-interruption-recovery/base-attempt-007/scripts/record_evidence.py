#!/usr/bin/env python3
"""Records logs/interrupted.txt, logs/resumed.txt and logs/three-points.txt for the quest base-camp-interruption-recovery.

It runs scripts/workflow.py as a person would, in temporary folders, and writes down what it printed and what it left.

HOW A RUN IS STOPPED HERE. Two ways, both a kill that cannot be caught (SIGKILL), and both of the workflow's own
process and no other:

  from outside   this script starts the workflow with a setting that makes it wait at a named point, reads its output
                 until it says it is waiting, and kills it. That is the run recorded in interrupted.txt.
  from inside    the workflow is started with a setting that makes it kill itself at a named point. Used for the
                 sweep in three-points.txt, where the exact point matters.

WORK, CLEAN and so on stand for temporary folders, which are deleted at the end. The number at the end of a temporary
file's name is the process id of the run that made it.

Run from anywhere:  python3 scripts/record_evidence.py
Exit code 0 if every check came out as expected, 1 if not.
"""
import hashlib
import os
import shutil
import signal
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ATTEMPT = os.path.dirname(HERE)
WORKFLOW = os.path.join(HERE, "workflow.py")
ITEMS = os.path.join(HERE, "sample", "items.json")
IDS = ["W-%02d" % n for n in range(1, 11)]
HEAD = ("Recorded by scripts/record_evidence.py. Each block between dashed lines is what a command printed. Where lines were\n"
        "left out of a block, the record says so beside it. The work items are made up. Nothing here is from a real system.")


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


class Log:
    def __init__(self, title, folders):
        self.lines, self.problems, self.count, self.folders = [title, HEAD, ""], [], 0, folders

    def out(self, *lines):
        self.lines += list(lines) if lines else [""]

    def part(self, text):
        self.lines += ["", "=" * 78, text]

    def check(self, label, ok):
        self.count += 1
        self.lines.append("  %-4s %s" % ("ok" if ok else "FAIL", label))
        if not ok:
            self.problems.append(label)

    def tidy(self, text):
        for name, path in self.folders.items():
            text = text.replace(path, name)
        return text.replace(HERE, "scripts")

    def shown(self, args, env_note=""):
        return "$ %spython3 scripts/workflow.py %s" % (env_note, " ".join(self.tidy(a) for a in args))

    def block(self, command, text, ending):
        self.lines += [command, "-" * 78, self.tidy(text.rstrip("\n")), "-" * 78, ending]

    def run(self, *args, stop_at=None):
        """Runs the workflow to its end, or to the point where it kills itself. Returns (exit code, output)."""
        env = {k: v for k, v in os.environ.items() if not k.startswith("GTQ_")}
        if stop_at:
            env["GTQ_STOP_AT"] = stop_at
        done = subprocess.run([sys.executable, WORKFLOW] + list(args), capture_output=True, text=True, env=env)
        ending = "exit code: %d" % done.returncode if done.returncode >= 0 else "NO EXIT CODE: the process was killed by signal %d (SIGKILL), sent by itself at the point named" % -done.returncode
        self.block(self.shown(args, "GTQ_STOP_AT=%s " % stop_at if stop_at else ""), done.stdout + done.stderr, ending)
        return done.returncode, done.stdout + done.stderr

    def run_and_kill(self, *args, pause_at):
        """Starts the workflow, waits until it says it is waiting at `pause_at`, and kills it from here."""
        env = {k: v for k, v in os.environ.items() if not k.startswith("GTQ_")}
        env["GTQ_PAUSE_AT"] = pause_at
        child = subprocess.Popen([sys.executable, WORKFLOW] + list(args), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
        lines = []
        for line in child.stdout:
            lines.append(line)
            if line.startswith("PAUSED AT"):
                break
        os.kill(child.pid, signal.SIGKILL)   # the workflow this script started, and nothing else
        rest = child.stdout.read()
        child.stdout.close()
        code = child.wait()
        self.block(self.shown(args, "GTQ_PAUSE_AT=%s " % pause_at), "".join(lines) + rest,
                   "NO EXIT CODE: the process was killed by signal %d (SIGKILL), sent by this script to process %d, the workflow it had started" % (-code, child.pid))
        return code, "".join(lines) + rest

    def listing(self, out, whole, old=None):
        """Lists every file in a run's folder, and says of each whether it is under a final name and whether it is whole.
        `whole` is {name: checksum} from an uninterrupted run. Returns (finals that are not whole, temporary files)."""
        bad, temporary = [], []
        self.out("Every file in %s:" % self.tidy(out))
        for folder, _, names in sorted(os.walk(out)):
            for name in sorted(names):
                path = os.path.join(folder, name)
                rel = os.path.relpath(path, out)
                size = os.path.getsize(path)
                if ".tmp-" in name:
                    final = os.path.join(os.path.dirname(rel), name[1:].split(".tmp-")[0])
                    full = os.path.getsize(os.path.join(whole["__folder__"], final)) if final in whole else 0
                    temporary.append(rel)
                    note = "TEMPORARY. Not under a final name: its name begins with a dot and ends in .tmp-<process id>. %s" % (
                        "It is PART of a file: %d of the %d bytes of %s." % (size, full, final) if size < full else
                        "It holds all %d bytes of %s (same checksum), and was not renamed." % (full, final) if final in whole and sha(path) == whole[final] else
                        "IT IS NOT PART OR ALL OF %s." % final)
                elif rel in whole:
                    same = sha(path) == whole[rel]
                    older = old and rel in old and sha(path) == old[rel]
                    note = ("final name. WHOLE: its checksum is that of the same file from an uninterrupted run." if same else
                            "final name. WHOLE, AND THE OLDER VERSION: its checksum is that of the file that was there before the run that stopped." if older else
                            "final name. NOT WHOLE: its checksum is not that of an uninterrupted run.")
                    if not same and not older:
                        bad.append(rel)
                elif rel == "progress.jsonl":
                    with open(path, "rb") as f:
                        raw = f.read()
                    tail = raw.split(b"\n")[-1]
                    note = "the progress record. %d whole lines%s. It is the one file written in place: see the notes." % (
                        raw.count(b"\n"), ", and then %d bytes of a line that was cut short" % len(tail) if tail else "")
                elif rel == "lock":
                    note = "the lock file. It names the process that last held the lock."
                else:
                    note = "NOT EXPECTED HERE."
                    bad.append(rel)
                self.out("  %-28s %5d bytes  %s" % (rel, size, note))
        return bad, temporary

    def save(self, name):
        self.lines += ["", "RESULT: %s" % ("%d OF %d CHECKS FAILED." % (len(self.problems), self.count) if self.problems else "ALL CHECKS PASSED. %d checks." % self.count)]
        os.makedirs(os.path.join(ATTEMPT, "logs"), exist_ok=True)
        with open(os.path.join(ATTEMPT, "logs", name), "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(self.lines) + "\n")
        print("%s: %s" % (name, self.lines[-1]))
        for label in self.problems:
            print("  FAILED: " + label)
        return not self.problems


def results(out):
    names = ["index.md"] + sorted(os.path.join("cards", n) for n in os.listdir(os.path.join(out, "cards")) if ".tmp-" not in n)
    found = {name: sha(os.path.join(out, name)) for name in names if os.path.exists(os.path.join(out, name))}
    found["__folder__"] = out
    return found


def record_lines(out):
    with open(os.path.join(out, "progress.jsonl"), encoding="utf-8", errors="replace") as f:
        return f.read().split("\n")


def stamps(out):
    """For each card and the index: the file's own number on the disk (its inode), and when it was last changed. A file
    that is written again arrives by a rename, so it is a new file with a new number."""
    names = [os.path.join("cards", n) for n in os.listdir(os.path.join(out, "cards")) if ".tmp-" not in n] + (["index.md"] if os.path.exists(os.path.join(out, "index.md")) else [])
    return {n: (os.stat(os.path.join(out, n)).st_ino, os.stat(os.path.join(out, n)).st_mtime_ns) for n in names}


def temporaries(out):
    return sorted(os.path.relpath(os.path.join(folder, name), out) for folder, _, names in os.walk(out) for name in names if ".tmp-" in name)


def tree(out):
    """The checksum of every file in a folder but the lock file, whose text names whichever process last took the lock."""
    return {os.path.relpath(os.path.join(folder, name), out): sha(os.path.join(folder, name)) for folder, _, names in os.walk(out) for name in names if name != "lock"}


def main():
    root = tempfile.mkdtemp(prefix="gtq-recovery-")
    work, clean = os.path.join(root, "work"), os.path.join(root, "clean")
    folders = {"WORK": work, "CLEAN": clean}
    ok = True
    try:
        # ------------------------------------------------------------ interrupted.txt
        log = Log("A run stopped partway. base-camp-interruption-recovery, attempt base-attempt-007", folders)
        log.part("FIRST, for comparison: a run that is never interrupted, in another folder")
        code, text = log.run("run", "--items", ITEMS, "--out", clean)
        whole = results(clean)
        log.check("the uninterrupted run finished, and wrote ten cards and an index", code == 0 and len(whole) == 12 and "Written in this run: 11" in text)

        log.part("THE RUN THAT IS STOPPED",
                 )
        log.out("The workflow is started on the same ten items, in a fresh folder. It is told to wait when it is halfway through",
                "writing the sixth card, W-06. This script reads its output until it says it is waiting, and then kills it with SIGKILL.",
                "SIGKILL cannot be caught: no clean-up code runs. Only the workflow's own process is killed.")
        log.out()
        code, text = log.run_and_kill("run", "--items", ITEMS, "--out", work, pause_at="W-06:mid-write")
        log.check("the process was killed by SIGKILL and did not end by itself", code == -signal.SIGKILL)
        log.check("its output is whole up to the kill: five cards written and recorded, then the wait, and no word of finishing",
                  all("  %s  written" % i in text for i in IDS[:5]) and "W-06  written" not in text and "FINISHED" not in text and "PAUSED AT W-06:mid-write" in text)

        log.part("WHAT IT LEFT BEHIND")
        bad, temporary = log.listing(work, whole)
        finals = sorted(n for n in os.listdir(os.path.join(work, "cards")) if ".tmp-" not in n)
        log.out()
        log.check("criterion 2: no partial or temporary file is under the final name of a card or of the index. The %d cards under final names are each whole, and nothing unexpected is in the folder" % len(finals), not bad and len(finals) == 5)
        log.check("criterion 1, as far as this run shows it: the card that was being written, W-06, is not under its final name at all. (A file that was already there, being replaced, is in three-points.txt, point 6.)", "W-06.md" not in finals and not os.path.exists(os.path.join(work, "index.md")))
        log.check("what was half-written is in one temporary file, whose name cannot be taken for a card's: %s" % ", ".join(temporary),
                  len(temporary) == 1 and os.path.basename(temporary[0]).startswith(".W-06.md.tmp-") and 0 < os.path.getsize(os.path.join(work, temporary[0])) < os.path.getsize(os.path.join(clean, "cards", "W-06.md")))
        log.out()
        log.out("The progress record, WORK/progress.jsonl, as the stopped run left it. Each line ends with a check of its own text:")
        lines = record_lines(work)
        log.out(*["  " + line for line in lines if line])
        done = [i for i in IDS if any('"item-done"' in line and '"id": "%s"' % i in line for line in lines)]
        log.check("criterion 3: progress was recorded as each item finished, not at the end: after the kill the record has a line for each of %s, and none for W-06. "
                  "(This shows each line had left the program before the kill. It does not show the line was on the disk itself: a kill is not a power cut. See the notes.)" % ", ".join(done), done == IDS[:5])
        log.check("the record has a run-started line and no run-finished line", any('"run-started"' in line for line in lines) and not any('"run-finished"' in line for line in lines))
        for item in done:
            line = next(line for line in lines if '"id": "%s"' % item in line)
            if sha(os.path.join(work, "cards", item + ".md")) not in line:
                done = None
                break
        log.check("each of those lines holds the checksum of the card that is on disk", done is not None)

        log.part("CAN A PERSON TELL? The status command, which changes nothing")
        code, text = log.run("status", "--out", work)
        log.check("criterion 6: it says the run was interrupted, how far it got, what was left, and how to recover",
                  code == 0 and text.startswith("INTERRUPTED:") and "Recorded as done: 5 (W-01, W-02, W-03, W-04, W-05)." in text
                  and "Temporary files left in the folder: 1 cards/.W-06.md.tmp-" in text and "Do not delete the progress record." in text)
        ok = log.save("interrupted.txt") and ok

        # ------------------------------------------------------------ resumed.txt
        log = Log("The same run, resumed. base-camp-interruption-recovery, attempt base-attempt-007", folders)
        log.out("WORK is the folder the stopped run left, exactly as interrupted.txt shows it. Nothing in it was deleted or edited:",
                "the progress record is the one the stopped run wrote. The command is the same command, given again.")
        before = stamps(work)
        record_before = open(os.path.join(work, "progress.jsonl"), "rb").read()
        log.part("THE RESUMED RUN")
        code, text = log.run("run", "--items", ITEMS, "--out", work)
        log.check("it finished", code == 0 and "FINISHED." in text)
        log.check("criterion 6: it says it is resuming an interrupted run, and where that run had got to",
                  "RESUMING AN INTERRUPTED RUN." in text and "It was interrupted after 5 of 10 items were recorded as done. The last whole line recorded: item-done W-05" in text)
        log.check("criterion 6: it says what the stopped run left behind and what was done with it", "LEFT BY THE RUN THAT STOPPED: temporary file cards/.W-06.md.tmp-" in text and "Removed." in text)
        log.check("criterion 4: it skipped the five items that were finished: W-01 to W-05", all("  %s  skipped" % i in text for i in IDS[:5]) and not any("  %s  written" % i in text for i in IDS[:5]))
        log.check("criterion 4: it completed the rest: W-06 to W-10, and the index", all("  %s  written" % i in text for i in IDS[5:]) and "  index  built" in text
                  and "FINISHED. Skipped as already done: 5 (W-01, W-02, W-03, W-04, W-05). Written in this run: 6 (W-06, W-07, W-08, W-09, W-10, index)." in text)
        after = stamps(work)
        log.check("criterion 4: the five finished cards were not written again: each is the same file on the disk (the same inode), last changed when it was before the resume",
                  all(after["cards/%s.md" % i] == before["cards/%s.md" % i] for i in IDS[:5]))
        log.check("and the five cards the resume wrote are new files", all("cards/%s.md" % i not in before for i in IDS[5:]) and len(after) == 11)
        log.check("the progress record was added to and not replaced: it still begins with every byte the stopped run wrote", open(os.path.join(work, "progress.jsonl"), "rb").read().startswith(record_before))

        log.part("THE RESULT, AGAINST AN UNINTERRUPTED RUN'S (criterion 5)")
        log.out("CLEAN is the folder of the run that was never interrupted. sha256 of each file, in both:", "")
        mine, same = results(work), True
        for name in sorted(n for n in whole if n != "__folder__"):
            match = mine.get(name) == whole[name]
            same = same and match
            log.out("  %-14s %s" % (name, "same" if match else "DIFFERENT"), "      resumed       %s" % (mine.get(name) or "MISSING"), "      uninterrupted %s" % whole[name])
        combined = lambda found: hashlib.sha256("".join("%s %s\n" % (n, found[n]) for n in sorted(found) if n != "__folder__").encode()).hexdigest()   # noqa: E731
        log.out("", "  one checksum over all eleven names and checksums:", "    resumed       %s" % combined(mine), "    uninterrupted %s" % combined(whole), "")
        log.check("criterion 5: every card and the index are, byte for byte, those of the uninterrupted run", same and len(mine) == len(whole) == 12 and combined(mine) == combined(whole))
        bad, temporary = log.listing(work, whole)
        log.out()
        log.check("no temporary file is left, and every file under a final name is whole", not bad and not temporary)
        log.out("", "WHAT THIS COMPARISON CAN AND CANNOT SHOW. The same item always gives the same card, so equal checksums show that no file is",
                "missing, cut short or mixed. They cannot show that no work was repeated: a card written twice is the same card. That is",
                "shown above, by the skipped cards being the same files as before.",
                "", "The progress records are NOT the same, and are not meant to be. The resumed run's keeps the history:")
        lines = [line for line in record_lines(work) if line]
        log.out(*["  " + line[:120] + ("..." if len(line) > 120 else "") for line in lines])
        names = [line.split('"event": "')[1].split('"')[0] + (":" + line.split('"id": "')[1].split('"')[0] if '"id": "' in line else "") for line in lines]
        log.check("criterion 6: the record shows one start, W-01 to W-05, one resume, W-06 to W-10, the index and the finish, with each item recorded once",
                  names == ["run-started"] + ["item-done:" + i for i in IDS[:5]] + ["run-resumed"] + ["item-done:" + i for i in IDS[5:]] + ["index-done", "run-finished"])

        log.part("AFTERWARDS")
        code, text = log.run("status", "--out", work)
        log.check("the status now says finished, and that the run was resumed once", text.startswith("FINISHED:") and "Times this run was resumed: 1." in text)
        log.out("", "The same command a third time:")
        before, files_before = stamps(work), tree(work)
        code, text = log.run("run", "--items", ITEMS, "--out", work)
        log.check("run again, it finds the run finished, checks each file, and writes no card, no index and no line of the record: each is the same file with the same bytes. (It does take the lock, and writes its process id in the lock file.)",
                  code == 0 and "ALREADY FINISHED." in text and "Written in this run: 0." in text and stamps(work) == before and tree(work) == files_before)
        ok = log.save("resumed.txt") and ok

        # ------------------------------------------------------------ three-points.txt
        log = Log("Stopped at each point, and with two runs at once. base-camp-interruption-recovery, attempt base-attempt-007", folders)
        log.out("The stretch goals. Each run below is in a fresh folder. The workflow kills itself with SIGKILL at the point named.",
                "THE BLOCKS IN THIS RECORD ARE SHORTENED: of a stopped run only the last two lines are kept, after '...', and of a resumed",
                "run the lines saying an item was skipped are left out. The tests make these stops, and others in the record's own",
                "lines, for the first card, a middle card, the last card and the index: see logs/tests.txt.")
        trials = (("W-04:mid-write", "half of the card is in the temporary file", "the temporary file holds part of W-04"),
                  ("W-04:before-rename", "the whole card is in the temporary file, which is not renamed", "the temporary file holds all of W-04, and is still not a card"),
                  ("W-04:after-rename", "the card is under its final name, and its progress line is not written", "W-04 is under its final name, whole, with no record"),
                  ("W-04:mid-record", "half of the card's progress line is written", "the last line of the record is cut short"),
                  ("index:mid-write", "every card is done, and half of the index is in a temporary file", "all ten cards are recorded, and there is no index"))
        for number, (point, what, left) in enumerate(trials, 1):
            out = os.path.join(root, "point-%d" % number)
            folders["POINT-%d" % number] = out
            log.part("POINT %d. Stopped at %s: %s" % (number, point, what))
            code, text = log.run("run", "--items", ITEMS, "--out", out, stop_at=point)
            log.lines[-3] = "\n".join(["  ..."] + log.lines[-3].split("\n")[-2:])
            bad, temporary = log.listing(out, whole)
            lines = record_lines(out)
            log.check("killed at that point, and what it left is as expected: %s" % left, code == -signal.SIGKILL and {
                1: len(temporary) == 1 and os.path.basename(temporary[0]).startswith(".W-04.md.tmp-") and 0 < os.path.getsize(os.path.join(out, temporary[0])) < os.path.getsize(os.path.join(clean, "cards", "W-04.md")) and "W-04.md" not in os.listdir(os.path.join(out, "cards")),
                2: len(temporary) == 1 and sha(os.path.join(out, temporary[0])) == whole["cards/W-04.md"] and "W-04.md" not in os.listdir(os.path.join(out, "cards")),
                3: not temporary and os.path.exists(os.path.join(out, "cards", "W-04.md")) and not any('"id": "W-04"' in line for line in lines),
                4: not temporary and lines[-1] != "" and '"id": "W-04"' in lines[-1],
                5: temporary == [next(iter(temporary), "")] and temporary[0].startswith(".index.md.tmp-") and sum('"item-done"' in line for line in lines) == 10 and not os.path.exists(os.path.join(out, "index.md"))}[number])
            log.check("criteria 1 and 2: every card, and the index if it is there, is whole, and nothing unexpected is in the folder", not bad)
            log.out("", "Resumed:")
            code, text = log.run("run", "--items", ITEMS, "--out", out)
            keep = [line for line in text.split("\n") if not line.startswith("  W-") or "skipped" not in line]
            log.lines[-3] = log.tidy("\n".join(keep).rstrip("\n"))
            log.out("(lines saying an item was skipped are left out of the block above)")
            mine = results(out)
            log.check("the resumed run finished, said it was resuming, left no temporary file, and its eleven files equal the uninterrupted run's",
                      code == 0 and "RESUMING AN INTERRUPTED RUN." in text and all(mine.get(n) == whole[n] for n in whole if n != "__folder__") and len(mine) == 12 and not temporaries(out))

        # -------- point 6: a file that was already there
        out = os.path.join(root, "point-6")
        folders["POINT-6"] = out
        log.part("POINT 6. A file that is already there, being replaced: the previous whole file stays until the new whole file takes its place (criterion 1)")
        log.out("A run is finished in a fresh folder. Then the card W-04 is replaced, by this script, with an older version: a whole file",
                "with other text. That makes the next run write W-04 again, over a file that exists. That run is stopped halfway through.", "")
        subprocess.run([sys.executable, WORKFLOW, "run", "--items", ITEMS, "--out", out], capture_output=True, text=True)
        older = b"# W-04: Show the last sign-in time\n\nAn older, whole version of this card, put here by scripts/record_evidence.py.\n"
        with open(os.path.join(out, "cards", "W-04.md"), "wb") as f:
            f.write(older)
        old = {"cards/W-04.md": hashlib.sha256(older).hexdigest(), "index.md": whole["index.md"]}
        for label, point in (("halfway through writing the new W-04", "W-04:mid-write"), ("again, when the new W-04 is whole in its temporary file and not yet renamed", "W-04:before-rename")):
            log.out("Stopped %s:" % label)
            code, text = log.run("run", "--items", ITEMS, "--out", out, stop_at=point)
            log.lines[-3] = "\n".join(line for line in log.lines[-3].split("\n") if "skipped" not in line)
            log.out("(lines saying an item was skipped are left out of the block above)")
            bad, temporary = log.listing(out, whole, old)
            with open(os.path.join(out, "cards", "W-04.md"), "rb") as f:
                still = f.read() == older
            log.check("criterion 1: stopped %s, the name W-04.md still holds the previous whole file, byte for byte, and not part of the new one" % label, code == -signal.SIGKILL and still and not bad and len(temporary) == 1)
            log.out()
        code, text = log.run("status", "--out", out)
        log.check("the status calls this interrupted, though the run had once finished: the record has a run-reopened line after its run-finished line", text.startswith("INTERRUPTED:") and "Times it was reopened after finishing: 1." in text)
        log.out("", "Resumed:")
        code, text = log.run("run", "--items", ITEMS, "--out", out)
        log.lines[-3] = log.tidy("\n".join(line for line in text.split("\n") if "skipped" not in line).rstrip("\n"))
        log.out("(lines saying an item was skipped are left out of the block above)")
        mine = results(out)
        log.check("criterion 1: after the resume the name holds the new whole file, and all eleven files equal the uninterrupted run's", code == 0 and all(mine.get(n) == whole[n] for n in whole if n != "__folder__") and not temporaries(out))

        out = os.path.join(root, "locked")
        folders["LOCKED"] = out
        log.part("TWO RUNS AT ONCE. The lock")
        log.out("A run is started and made to wait while writing its third card:", "")
        env = {k: v for k, v in os.environ.items() if not k.startswith("GTQ_")}
        env["GTQ_PAUSE_AT"] = "W-03:mid-write"
        first = subprocess.Popen([sys.executable, WORKFLOW, "run", "--items", ITEMS, "--out", out], stdout=subprocess.PIPE, text=True, env=env)
        said = []
        for line in first.stdout:
            said.append(line)
            if line.startswith("PAUSED AT"):
                break
        log.block(log.shown(["run", "--items", ITEMS, "--out", out], "GTQ_PAUSE_AT=W-03:mid-write "), "".join(said), "(still running, as process %d, and waiting)" % first.pid)
        log.out("", "While it waits, a second run is started in the same folder:")
        before = tree(out)
        code, text = log.run("run", "--items", ITEMS, "--out", out)
        log.check("stretch goal: the second run is refused while the first holds the lock, and every file in the folder but the lock file has the bytes it had", code == 1 and "REFUSED: another run is working in this folder now" in text and tree(out) == before)
        code, text = log.run("status", "--out", out)
        log.check("the status says a run is working there now", "A RUN IS WORKING IN THIS FOLDER NOW" in text)
        os.kill(first.pid, signal.SIGKILL)   # the first run, which this script started
        first.stdout.close()
        killed = first.wait()
        log.out("", "The first run is then killed with SIGKILL by this script (process %d, signal %d). It could not release the lock itself." % (first.pid, -killed), "The same command again:")
        code, text = log.run("run", "--items", ITEMS, "--out", out)
        log.lines[-3] = log.tidy("\n".join(line for line in text.split("\n") if "skipped" not in line).rstrip("\n"))
        log.out("(lines saying an item was skipped are left out of the block above)")
        mine = results(out)
        log.check("stretch goal: a killed run leaves no lock behind: the next run is not refused, resumes, and gives the uninterrupted run's files",
                  code == 0 and "RESUMING AN INTERRUPTED RUN." in text and all(mine.get(n) == whole[n] for n in whole if n != "__folder__") and len(mine) == 12)
        ok = log.save("three-points.txt") and ok
    finally:
        shutil.rmtree(root, ignore_errors=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
