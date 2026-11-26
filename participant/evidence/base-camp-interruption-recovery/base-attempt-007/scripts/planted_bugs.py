#!/usr/bin/env python3
"""Records logs/planted-bugs.txt for the quest base-camp-interruption-recovery.

Puts one bug at a time into scripts/workflow.py, runs every test, notes which tests fail, and takes the bug out
again. At the end it checks that the file is the same as when it started, byte for byte.

It changes workflow.py while it runs. Do not run the workflow or the tests at the same time.

Run from anywhere:  python3 scripts/planted_bugs.py
Exit code 0 if every bug was caught and the file was restored, 1 if not.
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ATTEMPT = os.path.dirname(HERE)
TARGET = os.path.join(HERE, "workflow.py")

# (what the bug is, the text to replace, what to replace it with)
BUGS = [
    ('A. A file is written straight under its final name (criteria 1 and 2)',
     '    temporary = os.path.join(folder, ".%s.tmp-%d" % (name, os.getpid()))',
     '    temporary = path'),
    ('B. The temporary file is renamed before its second half is written (criterion 2)',
     '        stop_here(where + ":mid-write")\n        f.write(data[half:])',
     '        os.replace(temporary, path)\n        temporary = path\n        stop_here(where + ":mid-write")\n        f.write(data[half:])'),
    ('C. The temporary file is made in another folder (criterion 1: a rename across folders is not one step)',
     '    temporary = os.path.join(folder, ".%s.tmp-%d" % (name, os.getpid()))',
     '    temporary = os.path.join(os.path.dirname(folder), ".%s.tmp-%d" % (name, os.getpid()))'),
    ('D. Progress is recorded before the file is in place (criterion 3)',
     '        write_whole(path, data, item["id"])\n        record(out, {"event": "item-done", "id": item["id"], "sha256": sha(data), "bytes": len(data)}, item["id"])',
     '        record(out, {"event": "item-done", "id": item["id"], "sha256": sha(data), "bytes": len(data)})\n        write_whole(path, data, item["id"])'),
    ('E. An item is said to be recorded, and no line is written for it (criterion 3)',
     '        record(out, {"event": "item-done", "id": item["id"], "sha256": sha(data), "bytes": len(data)}, item["id"])\n        say("  %s  written (%d bytes), and recorded" % (item["id"], len(data)))',
     '        say("  %s  written (%d bytes), and recorded" % (item["id"], len(data)))'),
    ('F. A resumed run skips nothing: it does every item again (criterion 4)',
     '            if state == "same":\n                say("  %s  skipped',
     '            if False:\n                say("  %s  skipped'),
    ('G. A resumed run trusts the record without looking at the file (criterion 4, decision 2)',
     '    if not os.path.exists(path):\n        return "missing"\n    with open(path, "rb") as f:\n        return "same" if sha(f.read()) == wanted_sha else "differs"',
     '    return "same"'),
    ('H. A resumed run checks that the file is there and not what is in it (decision 2)',
     '        return "same" if sha(f.read()) == wanted_sha else "differs"',
     '        return "same"'),
    ('I. A card found with no record is taken as done (criterion 4)',
     '        elif os.path.exists(path) and events is not None:',
     '        elif os.path.exists(path) and events is not None and not skipped.append(item["id"]):\n            continue\n        elif False:'),
    ('J. A line of the record that fails its own check is believed (criterion 3)',
     '        event = json.loads(text) if check == sha(text.encode("utf-8"))[:16] else None\n    except (ValueError, UnicodeDecodeError):\n        return None\n    return event if isinstance(event, dict) else None',
     '        event = json.loads(text)\n    except (ValueError, UnicodeDecodeError):\n        return None\n    return event if isinstance(event, dict) else None'),
    ('K. A cut-short last line makes the whole record unreadable: the run refuses (criterion 4)',
     '    if bad:\n        size = sum(len(lines[n - 1]) for n in bad)',
     '    if bad:\n        raise Refused("the record is damaged")\n        size = sum(len(lines[n - 1]) for n in bad)'),
    ('L. A cut-short line is not closed off, so the next line runs into it (criterion 4)',
     '        if not ends_clean:\n            repair_tail(out)\n        if not finished:',
     '        if not finished:'),
    ('M. A record damaged in the middle is read past (the record)',
     '            if event.get("event") != "cut-short-line-closed":\n                raise Refused("line %d of the progress record is damaged',
     '            if False:\n                raise Refused("line %d of the progress record is damaged'),
    ('M2. An empty record, left by a kill at the first write, is refused for ever (a reader\'s finding)',
     '    elif not events:\n        say("RESUMING AN INTERRUPTED RUN. The progress record is there and has no whole line in it',
     '    elif not events:\n        raise Refused("the progress record does not begin with a run-started line")\n    elif False:\n        say("RESUMING AN INTERRUPTED RUN. The progress record is there and has no whole line in it'),
    ('M3. The closing line is written without the line end that must come before it (a reader\'s finding)',
     '    data = b"" if raw.endswith(b"\\n") or not raw else b"\\n"',
     '    data = b""'),
    ('M4. A write that the system cuts short is taken as done (a reader\'s finding)',
     '        count = os.write(fd, data)\n        if count <= 0:\n            raise OSError("the system wrote nothing")\n        data = data[count:]',
     '        os.write(fd, data)\n        data = b""'),
    ('M5. A finished run that is being put right still looks finished if it is stopped (a reader\'s finding)',
     '        if finished:\n            record(out, {"event": "run-reopened"',
     '        if False:\n            record(out, {"event": "run-reopened"'),
    ('M6. A finished run is judged by any run-finished line, not by the last line (a reader\'s finding)',
     '        finished = events[-1].get("event") == "run-finished"      # finished means: nothing was recorded after the finish',
     '        finished = any(e.get("event") == "run-finished" for e in events)'),
    ('M7. With no record, the run starts over on top of the cards that are there (a safety rule)',
     '        if there or os.path.exists(os.path.join(out, "index.md")):',
     '        if False:'),
    ('M8. A run started with another card format is resumed (criterion 5)',
     '        if started.get("card_format") != FORMAT:',
     '        if False:'),
    ('M9. A card is not pushed to the disk before it is renamed (criterion 3)',
     '        f.write(data[half:])\n        f.flush()\n        to_disk(f.fileno())',
     '        f.write(data[half:])\n        f.flush()'),
    ('M10. A line of the record is not pushed to the disk (criterion 3)',
     '        write_all(fd, data)\n        to_disk(fd)\n    finally:\n        os.close(fd)\n\n\ndef read_record',
     '        write_all(fd, data)\n    finally:\n        os.close(fd)\n\n\ndef read_record'),
    ('M11. The folder is not pushed to the disk after a rename (criterion 3)',
     '    os.replace(temporary, path)          # the one step in which the file becomes real\n    folder_to_disk(folder)',
     '    os.replace(temporary, path)          # the one step in which the file becomes real'),
    ('M12. An error from the system is reported as a refusal (exit codes)',
     '    except OSError as error:\n        say("")\n        say("STOPPED BY AN ERROR FROM THE SYSTEM',
     '    except ZeroDivisionError as error:\n        say("")\n        say("STOPPED BY AN ERROR FROM THE SYSTEM'),
    ('M13. Status does not say that a run is still working (criterion 6)',
     '            say("A RUN IS WORKING IN THIS FOLDER NOW',
     '            pass  # say("A RUN IS WORKING IN THIS FOLDER NOW'),
    ('N. A resume starts by deleting the progress record (a safety rule)',
     '        resumes = sum(1 for e in events if e.get("event") == "run-resumed")\n        if finished:',
     '        resumes = sum(1 for e in events if e.get("event") == "run-resumed")\n        if not finished:\n            os.remove(os.path.join(out, RECORD))\n            record(out, started)\n            done = {}\n        if finished:'),
    ('O. Temporary files left by the stopped run are kept (criterion 2)',
     '            os.remove(path)\n        if not left and not finished:',
     '        if not left and not finished:'),
    ('P. A temporary file left by the stopped run is finished off and used (criterion 2)',
     '            os.remove(path)\n        if not left and not finished:',
     '            os.replace(path, os.path.join(os.path.dirname(path), os.path.basename(path)[1:].split(".tmp-")[0]))\n        if not left and not finished:'),
    ('Q. The resumed run does not say it is resuming (criterion 6)',
     '            say("RESUMING AN INTERRUPTED RUN. The progress record does not end with a run-finished line.")',
     '            say("STARTING.")'),
    ('R. The resumed run does not say what the stopped run left behind (criterion 6)',
     '            say("  LEFT BY THE RUN THAT STOPPED: temporary file %s, %d bytes. Removed. It was never under a final name and is not used."\n                % (os.path.relpath(path, out), os.path.getsize(path)))\n',
     ''),
    ('S. The resume is not written into the record (criterion 6)',
     '            record(out, {"event": "run-resumed", "number": resumes + 1, "items_recorded_done": len(done)}, "resume")',
     '            pass'),
    ('T. Status calls an interrupted run finished (criterion 6)',
     '    finished = bool(events) and events[-1].get("event") == "run-finished"\n    resumes',
     '    finished = True\n    resumes'),
    ('U. Another input is accepted on resume (criterion 5)',
     '        if started.get("items_fingerprint") != items_sha:',
     '        if False:'),
    ('V. The index is not built again after a card was rewritten (criterion 5)',
     '    if index_done and not written and file_state(index_path, index_done["sha256"]) == "same" and sha(data) == index_done["sha256"]:',
     '    if index_done and file_state(index_path, index_done["sha256"]) == "same":'),
    ('W. The index is built from memory, not from the card files (the scenario)',
     '        with open(os.path.join(out, "cards", item["id"] + ".md"), "rb") as f:\n            data = f.read()\n        title',
     '        data = card_of(item)\n        open(os.path.join(out, "cards", item["id"] + ".md"), "rb").close()\n        title'),
    ('X. A second run does not check the lock (stretch goal)',
     '        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)\n    except BlockingIOError:',
     '        pass\n    except BlockingIOError:'),
    ('Y. Output is not sent line by line, so a killed run loses what it had said (criterion 6)',
     '    print(text, flush=True)',
     '    print(text)'),
    ('Z. A finished run that is run again writes every file again (criterion 4)',
     '            if state == "same":\n                say("  %s  skipped: recorded as done, and its card is there with the checksum recorded" % item["id"])',
     '            if state == "same" and not finished:\n                say("  %s  skipped: recorded as done, and its card is there with the checksum recorded" % item["id"])'),
    ('AA. Two items with one id are accepted (the input)',
     '        if not ok or item["id"].lower() in seen:      # ids that differ only in capitals would be one file on some disks',
     '        if not ok:'),
    ('AB. The stop hook does nothing, so no run is ever stopped (the tests themselves)',
     '        os.kill(os.getpid(), signal.SIGKILL)',
     '        pass'),
]


def run_tests():
    done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=ATTEMPT, capture_output=True, text=True)
    failed = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\w+) \((?:test_workflow\.)?(\w+)", done.stderr, re.M)))
    return done.stderr.strip().splitlines()[-1], ["%s.%s" % (group, name) for name, group in failed]


def main():
    with open(TARGET, encoding="utf-8") as f:
        good = f.read()
    out = ["Do the tests notice a broken workflow? base-camp-interruption-recovery, attempt base-attempt-007",
           "Recorded by scripts/planted_bugs.py.", "",
           "Each bug below was put into scripts/workflow.py, every test was run, and the bug was taken out again.", ""]
    last, failed = run_tests()
    out += ["Before any bug: %s" % last, ""]
    clean, missed = (not failed and last.startswith("OK")), []
    try:
        for title, old, new in BUGS:
            out += ["PLANTED BUG %s" % title]
            if good.count(old) != 1:
                out += ["  COULD NOT BE PLANTED: the text to replace was not found once", ""]
                missed.append(title)
                continue
            with open(TARGET, "w", encoding="utf-8") as f:
                f.write(good.replace(old, new))
            last, failed = run_tests()
            with open(TARGET, "w", encoding="utf-8") as f:
                f.write(good)
            out += ["  tests that failed: %d" % len(failed)] + ["    %s" % name for name in failed[:6]] + (["    ... and %d more" % (len(failed) - 6)] if len(failed) > 6 else [])
            if not failed:
                out += ["    NONE. THIS BUG WAS NOT CAUGHT."]
                missed.append(title)
            out += [""]
    finally:
        with open(TARGET, "w", encoding="utf-8") as f:
            f.write(good)
    with open(TARGET, encoding="utf-8") as f:
        restored = f.read() == good
    out += ["After the last bug was taken out: workflow.py is byte for byte what it was at the start. %s" % ("OK" if restored else "NOT RESTORED"), ""]
    ok = clean and restored and not missed
    out += ["RESULT: %s" % ("all %d planted bugs were caught by at least one test, and the file was restored." % len(BUGS) if ok
                            else "NOT ALL AS EXPECTED: %s" % ("; ".join(missed) or "the tests did not pass before any bug, or the file was not restored"))]
    os.makedirs(os.path.join(ATTEMPT, "logs"), exist_ok=True)
    with open(os.path.join(ATTEMPT, "logs", "planted-bugs.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print(out[-1])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
