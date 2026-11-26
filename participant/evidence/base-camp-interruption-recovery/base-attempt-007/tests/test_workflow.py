"""Tests for scripts/workflow.py. Each test works in its own temporary folder. A "kill" here is the workflow's own
process killing itself with SIGKILL at a named point, or this test killing the workflow's process: never any other."""
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.abspath(os.path.join(HERE, "..", "scripts"))
WORKFLOW = os.path.join(SCRIPTS, "workflow.py")
ITEMS = os.path.join(SCRIPTS, "sample", "items.json")
sys.path.insert(0, SCRIPTS)
import workflow as wf   # noqa: E402

IDS = ["W-%02d" % n for n in range(1, 11)]


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


class Case(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="gtq-recovery-test-")
        self.out = os.path.join(self.root, "out")
        with open(ITEMS, encoding="utf-8") as f:
            self.items = json.load(f)["items"]

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def run_it(self, stop_at=None, out=None, items=ITEMS, command="run"):
        env = {k: v for k, v in os.environ.items() if not k.startswith("GTQ_")}
        if stop_at:
            env["GTQ_STOP_AT"] = stop_at
        args = [sys.executable, WORKFLOW, command, "--out", out or self.out] + (["--items", items] if command == "run" else [])
        done = subprocess.run(args, capture_output=True, text=True, env=env)
        return done.returncode, done.stdout + done.stderr

    def killed(self, stop_at, out=None):
        code, text = self.run_it(stop_at, out)
        self.assertEqual(code, -signal.SIGKILL, text)
        return text

    def results(self, out=None):
        """The checksum of every file a finished run is for: the cards and the index."""
        out = out or self.out
        names = ["index.md"] + sorted(os.path.join("cards", n) for n in os.listdir(os.path.join(out, "cards")))
        return {name: sha(os.path.join(out, name)) for name in names}

    def clean(self):
        """The results of a run that was never interrupted, in another folder."""
        other = os.path.join(self.root, "uninterrupted")
        if not os.path.exists(other):
            code, text = self.run_it(out=other)
            self.assertEqual(code, 0, text)
        return self.results(other)

    def finals(self, out=None):
        out = out or self.out
        return sorted(n for n in os.listdir(os.path.join(out, "cards")) if ".tmp-" not in n) + [n for n in os.listdir(out) if n == "index.md"]

    def assert_no_part_under_a_final_name(self, out=None):
        """Every file under a final name is whole: it is, byte for byte, what an uninterrupted run writes there."""
        out = out or self.out
        whole = self.clean()
        for name in os.listdir(os.path.join(out, "cards")):
            if ".tmp-" not in name:
                self.assertEqual(sha(os.path.join(out, "cards", name)), whole[os.path.join("cards", name)], "%s is under its final name and is not whole" % name)
        if os.path.exists(os.path.join(out, "index.md")):
            self.assertEqual(sha(os.path.join(out, "index.md")), whole["index.md"])

    def events(self, out=None):
        return wf.read_record(out or self.out)[0]

    def marks(self, out=None):
        """For each card: the file's own number on the disk (its inode) and when it was last changed. A file that is
        written again is a new file with a new number, since it arrives by a rename."""
        out = out or self.out
        return {n: (os.stat(os.path.join(out, "cards", n)).st_ino, os.stat(os.path.join(out, "cards", n)).st_mtime_ns)
                for n in os.listdir(os.path.join(out, "cards")) if ".tmp-" not in n}


class AnUninterruptedRun(Case):
    def test_it_writes_ten_cards_and_an_index_and_says_so(self):
        code, text = self.run_it()
        self.assertEqual(code, 0, text)
        self.assertIn("STARTING.", text)
        self.assertIn("FINISHED. Skipped as already done: 0. Written in this run: 11", text)
        self.assertEqual(self.finals(), [i + ".md" for i in IDS] + ["index.md"])
        self.assertEqual(wf.temporary_files(self.out), [])

    def test_the_record_has_a_line_for_each_item_in_order_then_the_index_then_the_end(self):
        self.run_it()
        self.assertEqual([e["event"] + ":" + e.get("id", "") for e in self.events()],
                         ["run-started:"] + ["item-done:" + i for i in IDS] + ["index-done:", "run-finished:"])

    def test_each_record_line_holds_the_checksum_of_the_card_on_disk(self):
        self.run_it()
        for event in self.events():
            if event["event"] == "item-done":
                self.assertEqual(event["sha256"], sha(os.path.join(self.out, "cards", event["id"] + ".md")))

    def test_two_uninterrupted_runs_give_the_same_files(self):
        self.run_it()
        self.assertEqual(self.results(), self.clean())

    def test_the_index_is_built_from_the_card_files(self):
        self.run_it()
        with open(os.path.join(self.out, "index.md"), encoding="utf-8") as f:
            index = f.read()
        for item in IDS:
            self.assertIn(sha(os.path.join(self.out, "cards", item + ".md")), index)


    def test_the_index_shows_what_is_in_a_card_file_and_not_what_should_be(self):
        """The scenario: a later step builds on a file. If a card were cut short, the index built from it would show it."""
        self.run_it()
        path = os.path.join(self.out, "cards", "W-02.md")
        with open(path, "wb") as f:
            f.write(b"# W-02: cut short\n")
        index = wf.index_of(self.out, self.items).decode("utf-8")
        self.assertIn("| W-02 | cut short | 1 | %s |" % sha(path), index)


class StoppedAtEveryPoint(Case):
    """Criteria 1, 2, 4 and 5, at each of the four points, for the first card, a middle card, the last card and the index."""

    def sweep(self, point):
        for target in ("W-01", "W-05", "W-10", "index"):
            with self.subTest(stopped=target + ":" + point):
                out = os.path.join(self.root, "%s-%s" % (target, point))
                self.killed("%s:%s" % (target, point), out)
                self.assert_no_part_under_a_final_name(out)
                self.assertFalse(any(e["event"] == "run-finished" for e in self.events(out)))
                before = self.marks(out)
                recorded = [e["id"] for e in self.events(out) if e["event"] == "item-done"]
                code, text = self.run_it(out=out)
                self.assertEqual(code, 0, text)
                self.assertIn("RESUMING AN INTERRUPTED RUN", text)
                self.assertEqual(self.results(out), self.clean())
                self.assertEqual(wf.temporary_files(out), [])
                for item in recorded:   # work that was finished and recorded is not done again: the file is not touched
                    self.assertIn("  %s  skipped" % item, text)
                    self.assertEqual(self.marks(out)[item + ".md"], before[item + ".md"], item)
                for item in IDS:
                    if item not in recorded:
                        self.assertIn("  %s  written" % item, text)

    def test_mid_write(self):
        self.sweep("mid-write")

    def test_before_rename(self):
        self.sweep("before-rename")

    def test_after_rename(self):
        self.sweep("after-rename")

    def test_mid_record(self):
        self.sweep("mid-record")


class WhatAStopLeaves(Case):
    def test_mid_write_leaves_a_temporary_file_and_nothing_under_the_final_name(self):
        self.killed("W-04:mid-write")
        self.assertEqual(self.finals(), ["W-01.md", "W-02.md", "W-03.md"])
        left = wf.temporary_files(self.out)
        self.assertEqual(len(left), 1)
        self.assertTrue(os.path.basename(left[0]).startswith(".W-04.md.tmp-"))
        self.assertLess(os.path.getsize(left[0]), len(wf.card_of(self.items[3])))
        self.assertGreater(os.path.getsize(left[0]), 0)

    def test_before_rename_leaves_a_whole_temporary_file_that_is_still_not_under_the_final_name(self):
        self.killed("W-04:before-rename")
        self.assertNotIn("W-04.md", self.finals())
        self.assertEqual(os.path.getsize(wf.temporary_files(self.out)[0]), len(wf.card_of(self.items[3])))

    def test_after_rename_leaves_the_whole_card_and_no_record_of_it(self):
        self.killed("W-04:after-rename")
        self.assertIn("W-04.md", self.finals())
        self.assertEqual(sha(os.path.join(self.out, "cards", "W-04.md")), hashlib.sha256(wf.card_of(self.items[3])).hexdigest())
        self.assertNotIn("W-04", [e.get("id") for e in self.events()])
        self.assertEqual(wf.temporary_files(self.out), [])

    def test_mid_record_leaves_a_last_line_cut_short_which_is_reported_and_not_believed(self):
        self.killed("W-04:mid-record")
        with open(os.path.join(self.out, "progress.jsonl"), "rb") as f:
            self.assertFalse(f.read().endswith(b"\n"))
        events, torn, clean = wf.read_record(self.out)
        self.assertIn("cut short", torn)
        self.assertFalse(clean)
        self.assertNotIn("W-04", [e.get("id") for e in events])
        code, text = self.run_it()
        self.assertIn("THE PROGRESS RECORD: line 5, the last, is cut short or fails the check", text)
        self.assertIn("W-04  a card is under its final name with no whole record of it", text)
        self.assertEqual(self.results(), self.clean())

    def test_the_output_of_a_killed_run_is_whole_up_to_the_kill(self):
        text = self.killed("W-04:mid-write")
        self.assertEqual(text.strip().splitlines()[-1], "  W-03  written (%d bytes), and recorded" % len(wf.card_of(self.items[2])))
        self.assertNotIn("FINISHED", text)

    def test_an_existing_whole_file_is_never_replaced_by_part_of_a_new_one(self):
        """Criterion 1, where a file is already there: the old whole file stays until the new whole file replaces it."""
        self.killed("W-06:mid-write")
        path = os.path.join(self.out, "cards", "W-02.md")
        with open(path, "wb") as f:
            f.write(b"an older, whole version of this card\n")
        self.killed("W-02:mid-write")       # the resume starts to write W-02 again, and is killed halfway
        with open(path, "rb") as f:
            self.assertEqual(f.read(), b"an older, whole version of this card\n")
        self.killed("W-02:before-rename")
        with open(path, "rb") as f:
            self.assertEqual(f.read(), b"an older, whole version of this card\n")
        code, text = self.run_it()
        self.assertEqual(code, 0, text)
        self.assertEqual(self.results(), self.clean())

    def test_write_whole_uses_a_temporary_name_in_the_same_folder(self):
        os.makedirs(self.out)
        seen = []
        real = os.replace
        try:
            os.replace = lambda a, b: (seen.append((a, b)), real(a, b))[1]
            wf.write_whole(os.path.join(self.out, "x.md"), b"whole", "x")
        finally:
            os.replace = real
        self.assertEqual(os.path.dirname(seen[0][0]), os.path.dirname(seen[0][1]))
        self.assertIn(".tmp-", os.path.basename(seen[0][0]))


class Resuming(Case):
    """Criteria 3, 4 and 6."""

    def test_progress_is_on_disk_as_each_item_finishes_not_at_the_end(self):
        self.killed("W-06:mid-write")
        self.assertEqual([e["id"] for e in self.events() if e["event"] == "item-done"], IDS[:5])

    def test_the_resumed_run_says_it_was_interrupted_where_and_what_it_did(self):
        self.killed("W-06:mid-write")
        code, text = self.run_it()
        for part in ("RESUMING AN INTERRUPTED RUN.", "It was interrupted after 5 of 10 items were recorded as done. The last whole line recorded: item-done W-05",
                     "This is resume number 1 of this run.", "LEFT BY THE RUN THAT STOPPED: temporary file cards/.W-06.md.tmp-", "Removed.",
                     "FINISHED. Skipped as already done: 5 (W-01, W-02, W-03, W-04, W-05). Written in this run: 6 (W-06, W-07, W-08, W-09, W-10, index)."):
            self.assertIn(part, text)

    def test_the_record_keeps_the_history_of_the_interruption(self):
        self.killed("W-06:mid-write")
        self.run_it()
        names = [e["event"] for e in self.events()]
        self.assertEqual(names.count("run-started"), 1)
        self.assertEqual(names.count("run-resumed"), 1)
        self.assertEqual(names[-1], "run-finished")
        self.assertEqual(names.index("run-resumed"), 6)

    def test_a_run_interrupted_three_times_still_gives_the_same_result(self):
        for point in ("W-03:mid-write", "W-03:mid-record", "W-08:after-rename"):
            self.killed(point)
        code, text = self.run_it()
        self.assertEqual(code, 0, text)
        self.assertIn("This is resume number 3 of this run.", text)   # the first kill was of the run itself, the next two of resumes
        self.assertEqual(self.results(), self.clean())
        self.assertEqual(len([e for e in self.events() if e["event"] == "item-done" and e["id"] == "W-01"]), 1)

    def test_a_resume_that_is_itself_interrupted_while_closing_a_cut_short_line_recovers(self):
        self.killed("W-03:mid-record")
        self.killed("W-03:mid-record")
        self.killed("W-04:mid-record")
        code, text = self.run_it()
        self.assertEqual(code, 0, text)
        self.assertEqual(self.results(), self.clean())
        code, text = self.run_it()
        self.assertEqual(code, 0, text)

    def test_an_item_recorded_as_done_whose_card_is_missing_is_written_again(self):
        self.killed("W-06:mid-write")
        os.remove(os.path.join(self.out, "cards", "W-02.md"))
        code, text = self.run_it()
        self.assertIn("W-02  RECORDED AS DONE, and its card is missing. Written again.", text)
        self.assertEqual(self.results(), self.clean())

    def test_an_item_recorded_as_done_whose_card_was_cut_short_afterwards_is_written_again(self):
        """The quest's scenario: a file that looks complete and is not. The checksum in the record shows it."""
        self.killed("W-06:mid-write")
        path = os.path.join(self.out, "cards", "W-02.md")
        with open(path, "rb") as f:
            data = f.read()
        with open(path, "wb") as f:
            f.write(data[:len(data) // 2])
        code, text = self.run_it()
        self.assertIn("W-02  RECORDED AS DONE, and its card is not the file that was recorded. Written again.", text)
        self.assertEqual(self.results(), self.clean())

    def test_another_input_is_refused_and_the_record_is_left(self):
        self.killed("W-06:mid-write")
        other = os.path.join(self.root, "other.json")
        with open(other, "w", encoding="utf-8") as f:
            json.dump({"items": self.items[:3]}, f)
        with open(os.path.join(self.out, "progress.jsonl"), "rb") as f:
            before = f.read()
        code, text = self.run_it(items=other)
        self.assertEqual(code, 1)
        self.assertIn("REFUSED: the items are not the items this run started with", text)
        with open(os.path.join(self.out, "progress.jsonl"), "rb") as f:
            self.assertEqual(f.read(), before)

    def test_a_record_damaged_in_the_middle_is_refused_and_left(self):
        self.killed("W-06:mid-write")
        path = os.path.join(self.out, "progress.jsonl")
        with open(path, "rb") as f:
            lines = f.read().split(b"\n")
        lines[2] = lines[2][:20]
        with open(path, "wb") as f:
            f.write(b"\n".join(lines))
        code, text = self.run_it()
        self.assertEqual(code, 1)
        self.assertIn("REFUSED: line 3 of the progress record is damaged, and the lines after it do not close it off", text)
        with open(path, "rb") as f:
            self.assertEqual(f.read(), b"\n".join(lines))

    def test_a_record_line_changed_by_hand_fails_its_own_check(self):
        self.killed("W-06:mid-write")
        path = os.path.join(self.out, "progress.jsonl")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        with open(path, "w", encoding="utf-8") as f:
            f.write(text.replace('"id": "W-02"', '"id": "W-09"'))
        code, text = self.run_it()
        self.assertEqual(code, 1)
        self.assertIn("is damaged", text)

    def test_the_progress_record_is_never_deleted_or_made_shorter(self):
        self.killed("W-06:mid-write")
        with open(os.path.join(self.out, "progress.jsonl"), "rb") as f:
            before = f.read()
        self.run_it()
        with open(os.path.join(self.out, "progress.jsonl"), "rb") as f:
            self.assertTrue(f.read().startswith(before))

    def test_a_finished_run_run_again_writes_nothing(self):
        self.run_it()
        stamps = {n: (os.stat(os.path.join(self.out, n)).st_ino, os.stat(os.path.join(self.out, n)).st_mtime_ns) for n in self.results()}
        with open(os.path.join(self.out, "progress.jsonl"), "rb") as f:
            before = f.read()
        code, text = self.run_it()
        self.assertEqual(code, 0)
        self.assertIn("ALREADY FINISHED.", text)
        self.assertIn("Written in this run: 0.", text)
        self.assertEqual({n: (os.stat(os.path.join(self.out, n)).st_ino, os.stat(os.path.join(self.out, n)).st_mtime_ns) for n in self.results()}, stamps)
        with open(os.path.join(self.out, "progress.jsonl"), "rb") as f:
            self.assertEqual(f.read(), before)

    def test_a_finished_run_with_a_card_damaged_since_is_put_right_and_the_index_built_again(self):
        self.run_it()
        with open(os.path.join(self.out, "cards", "W-03.md"), "wb") as f:
            f.write(b"damaged")
        code, text = self.run_it()
        self.assertIn("W-03  RECORDED AS DONE, and its card is not the file that was recorded. Written again.", text)
        self.assertIn("index  recorded as done, and cards were written again since. Built again.", text)
        self.assertIn("THE RUN HAD FINISHED, and was reopened", text)
        self.assertEqual(self.results(), self.clean())
        names = [e["event"] for e in self.events()]
        self.assertEqual(names[-5:], ["run-finished", "run-reopened", "item-done", "index-done", "run-finished"])

    def test_a_repair_of_a_finished_run_that_is_itself_interrupted_is_seen_and_recovered(self):
        """Reader's finding: a kill while a finished run is being put right must not leave it looking finished."""
        for point in ("W-03:mid-write", "W-03:after-rename", "W-03:mid-record", "reopen:mid-record", "index:mid-write", "finish:mid-record"):
            with self.subTest(stopped=point):
                out = os.path.join(self.root, point.replace(":", "-"))
                self.run_it(out=out)
                with open(os.path.join(out, "cards", "W-03.md"), "wb") as f:
                    f.write(b"damaged")
                self.killed(point, out)
                status = self.run_it(out=out, command="status")[1]
                if point != "reopen:mid-record":
                    self.assertIn("INTERRUPTED:", status)
                    self.assertIn("To recover:", status)
                code, text = self.run_it(out=out)
                self.assertEqual(code, 0, text)
                self.assertEqual(self.results(out), self.clean())
                self.assertIn("FINISHED:", self.run_it(out=out, command="status")[1])
                self.assertEqual(self.events(out)[-1]["event"], "run-finished")

    def test_the_first_lines_of_the_record_can_be_interrupted_too(self):
        """Reader's finding: a kill while the record is created, or while its first line is written, must not leave a
        folder that every later run refuses."""
        for point in ("start:created", "start:mid-record"):
            with self.subTest(stopped=point):
                out = os.path.join(self.root, point.replace(":", "-"))
                self.killed(point, out)
                self.assertEqual(self.events(out), [])
                self.assertIn("INTERRUPTED:", self.run_it(out=out, command="status")[1])
                code, text = self.run_it(out=out)
                self.assertEqual(code, 0, text)
                self.assertIn("RESUMING AN INTERRUPTED RUN. The progress record is there and has no whole line in it", text)
                self.assertEqual(self.results(out), self.clean())
                self.assertEqual(self.events(out)[0]["event"], "run-started")

    def test_a_resume_interrupted_while_writing_its_own_lines_recovers(self):
        for first, second in (("W-03:mid-record", "close:mid-record"), ("W-03:mid-write", "resume:mid-record"), ("W-03:mid-record", "resume:mid-record"),
                              ("start:mid-record", "close:mid-record"), ("start:mid-record", "start:mid-record"), ("W-10:mid-record", "finish:mid-record")):
            with self.subTest(stopped=first + " then " + second):
                out = os.path.join(self.root, (first + "-" + second).replace(":", "-"))
                self.killed(first, out)
                self.killed(second, out)
                self.assert_no_part_under_a_final_name(out)
                code, text = self.run_it(out=out)
                self.assertEqual(code, 0, text)
                self.assertEqual(self.results(out), self.clean())
                code, text = self.run_it(out=out)
                self.assertEqual(code, 0, text)
                self.assertIn("ALREADY FINISHED.", text)

    def test_two_cut_short_lines_in_a_row_at_the_end_are_closed_off_and_not_refused(self):
        """A power cut could keep only part of the line that closes a cut-short line. Made here by hand."""
        self.killed("W-04:mid-record")
        closing = wf.line_of({"event": "cut-short-line-closed", "line": 5}).encode("utf-8")
        with open(os.path.join(self.out, "progress.jsonl"), "ab") as f:
            f.write(b"\n" + closing[:len(closing) // 2])
        code, text = self.run_it()
        self.assertEqual(code, 0, text)
        self.assertIn("lines 5 to 6, the last, are cut short", text)
        self.assertEqual(self.results(), self.clean())
        self.assertEqual(self.run_it()[0], 0)

    def test_a_whole_last_line_that_only_lacks_its_line_end_is_believed(self):
        self.killed("W-06:mid-write")
        path = os.path.join(self.out, "progress.jsonl")
        with open(path, "rb") as f:
            raw = f.read()
        with open(path, "wb") as f:
            f.write(raw[:-1])
        code, text = self.run_it()
        self.assertEqual(code, 0, text)
        self.assertIn("  W-05  skipped", text)
        self.assertNotIn("cut short", text)
        with open(path, encoding="utf-8") as f:
            self.assertNotIn("cut-short-line-closed", f.read())

    def test_cards_with_no_progress_record_are_not_started_over_on(self):
        """The safety rule: no recovering by deleting the record. Without a record the workflow refuses, and says why."""
        self.killed("W-06:mid-write")
        os.remove(os.path.join(self.out, "progress.jsonl"))
        code, text = self.run_it()
        self.assertEqual(code, 1)
        self.assertIn("REFUSED: there are 5 cards in this folder and no progress record", text)
        self.assertEqual(self.finals(), ["W-0%d.md" % n for n in range(1, 6)])

    def test_a_run_started_with_another_card_format_is_refused(self):
        self.killed("W-06:mid-write")
        code, text = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, %r); import workflow as w; w.FORMAT = 2; sys.exit(w.main(['run', '--items', %r, '--out', %r]))" % (SCRIPTS, ITEMS, self.out)],
                                    capture_output=True, text=True), None
        self.assertEqual(code.returncode, 1)
        self.assertIn("another format", code.stdout)

    def test_the_same_items_laid_out_differently_are_the_same_input(self):
        self.killed("W-06:mid-write")
        other = os.path.join(self.root, "tidy.json")
        with open(other, "w", encoding="utf-8") as f:
            json.dump({"items": self.items}, f, indent=8, sort_keys=True)
        code, text = self.run_it(items=other)
        self.assertEqual(code, 0, text)
        self.assertEqual(self.results(), self.clean())


class PushedToTheDisk(Case):
    """Criterion 3, as far as it can be tested without cutting the power: that the workflow ASKS for each thing to be
    kept. Whether the disk then keeps it is not tested here."""

    def test_every_card_the_index_every_record_line_and_every_folder_change_is_pushed_to_the_disk(self):
        files, folders = [], []
        real_file, real_folder = wf.to_disk, wf.folder_to_disk
        try:
            wf.to_disk = lambda fd: files.append(os.fstat(fd).st_ino)
            wf.folder_to_disk = lambda folder: folders.append(os.path.basename(folder))
            os.environ.pop("GTQ_STOP_AT", None)
            import contextlib
            import io
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(wf.main(["run", "--items", ITEMS, "--out", self.out]), 0)
        finally:
            wf.to_disk, wf.folder_to_disk = real_file, real_folder
        record = os.stat(os.path.join(self.out, "progress.jsonl")).st_ino
        self.assertEqual(files.count(record), 13)                    # one push for each of the 13 lines of the record
        for name in self.results():                                   # and one for each card and the index, made before its rename
            self.assertIn(os.stat(os.path.join(self.out, name)).st_ino, files, name)
        self.assertEqual(folders.count("cards"), 10)                  # each card's rename
        self.assertGreaterEqual(folders.count("out"), 3)              # the folder's creation, the record's creation, the index's rename

    def test_a_short_write_is_finished_and_a_write_of_nothing_is_an_error(self):
        calls = []
        real = os.write
        try:
            os.write = lambda fd, data: (calls.append(len(data)), real(fd, data[:3]))[1]
            read, write = os.pipe()
            wf.write_all(write, b"0123456789")
            os.write = real
            self.assertEqual(os.read(read, 20), b"0123456789")
            self.assertEqual(calls, [10, 7, 4, 1])
            os.write = lambda fd, data: 0
            with self.assertRaises(OSError):
                wf.write_all(write, b"x")
        finally:
            os.write = real
            os.close(read)
            os.close(write)

    def test_an_error_from_the_system_ends_with_exit_code_3_and_can_be_resumed(self):
        code = subprocess.run([sys.executable, "-c", "import sys, os; sys.path.insert(0, %r); import workflow as w\nreal = w.to_disk\ncount = [0]\ndef full(fd):\n    count[0] += 1\n    if count[0] == 9: raise OSError(28, 'made up: no space')\n    real(fd)\nw.to_disk = full\nsys.exit(w.main(['run', '--items', %r, '--out', %r]))" % (SCRIPTS, ITEMS, self.out)],
                              capture_output=True, text=True)
        self.assertEqual(code.returncode, 3, code.stdout + code.stderr)
        self.assertIn("STOPPED BY AN ERROR FROM THE SYSTEM", code.stdout)
        self.assert_no_part_under_a_final_name()
        code, text = self.run_it()
        self.assertEqual(code, 0, text)
        self.assertEqual(self.results(), self.clean())


class TheStatus(Case):
    def test_no_run(self):
        os.makedirs(self.out)
        self.assertIn("NO RUN", self.run_it(command="status")[1])

    def test_an_interrupted_run_is_called_interrupted_with_what_it_left(self):
        self.killed("W-04:mid-write")
        code, text = self.run_it(command="status")
        self.assertEqual(code, 0)
        for part in ("INTERRUPTED:", "Recorded as done: 3 (W-01, W-02, W-03).", "Temporary files left in the folder: 1 cards/.W-04.md.tmp-", "Do not delete the progress record."):
            self.assertIn(part, text)

    def test_status_changes_nothing(self):
        self.killed("W-04:mid-write")
        before = {n: sha(os.path.join(d, n)) for d, _, names in os.walk(self.out) for n in names}
        self.run_it(command="status")
        self.assertEqual({n: sha(os.path.join(d, n)) for d, _, names in os.walk(self.out) for n in names}, before)

    def test_a_card_with_no_record_is_pointed_out(self):
        self.killed("W-04:after-rename")
        self.assertIn("Cards under a final name with no record of them: W-04.", self.run_it(command="status")[1])

    def test_a_run_that_is_still_working_is_not_just_called_interrupted(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith("GTQ_")}
        env["GTQ_PAUSE_AT"] = "W-03:mid-write"
        child = subprocess.Popen([sys.executable, WORKFLOW, "run", "--items", ITEMS, "--out", self.out], stdout=subprocess.PIPE, text=True, env=env)
        try:
            for line in child.stdout:
                if line.startswith("PAUSED AT"):
                    break
            self.assertIn("A RUN IS WORKING IN THIS FOLDER NOW", self.run_it(command="status")[1])
        finally:
            child.kill()
            child.stdout.close()
            child.wait()
        self.assertNotIn("A RUN IS WORKING", self.run_it(command="status")[1])

    def test_a_finished_run_is_called_finished(self):
        self.run_it()
        text = self.run_it(command="status")[1]
        self.assertIn("FINISHED:", text)
        self.assertNotIn("INTERRUPTED", text)


class TheLock(Case):
    def paused(self, where):
        env = {k: v for k, v in os.environ.items() if not k.startswith("GTQ_")}
        env["GTQ_PAUSE_AT"] = where
        child = subprocess.Popen([sys.executable, WORKFLOW, "run", "--items", ITEMS, "--out", self.out], stdout=subprocess.PIPE, text=True, env=env)
        lines = []
        for line in child.stdout:
            lines.append(line)
            if line.startswith("PAUSED AT"):
                break
        return child, "".join(lines)

    def test_a_second_run_in_the_same_folder_is_refused_while_the_first_lives(self):
        child, _ = self.paused("W-03:mid-write")
        try:
            code, text = self.run_it()
            self.assertEqual(code, 1)
            self.assertIn("REFUSED: another run is working in this folder now", text)
            self.assertEqual(self.finals(), ["W-01.md", "W-02.md"])
            self.assertEqual(len(self.events()), 3)
        finally:
            child.kill()
            child.stdout.close()
            child.wait()

    def test_a_run_killed_from_outside_leaves_no_lock_and_resumes(self):
        child, text = self.paused("W-03:mid-write")
        os.kill(child.pid, signal.SIGKILL)      # this test's own child, and nothing else
        child.stdout.close()
        self.assertEqual(child.wait(), -signal.SIGKILL)
        self.assertIn("PAUSED AT W-03:mid-write", text)
        self.assert_no_part_under_a_final_name()
        code, text = self.run_it()
        self.assertEqual(code, 0, text)
        self.assertIn("RESUMING AN INTERRUPTED RUN", text)
        self.assertEqual(self.results(), self.clean())


class TheInput(Case):
    def refuse(self, content, part):
        path = os.path.join(self.root, "bad.json")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        code, text = self.run_it(items=path)
        self.assertEqual(code, 1, text)
        self.assertIn(part, text)

    def test_no_file(self):
        code, text = self.run_it(items=os.path.join(self.root, "none.json"))
        self.assertEqual(code, 1)
        self.assertIn("there is no items file", text)

    def test_not_json(self):
        self.refuse("{", "is not JSON")

    def test_no_items(self):
        self.refuse('{"items": []}', "lists no item")

    def test_two_items_with_one_id(self):
        item = dict(self.items[0])
        self.refuse(json.dumps({"items": [item, item]}), "two items share an id")

    def test_two_ids_that_differ_only_in_capitals(self):
        self.refuse(json.dumps({"items": [dict(self.items[0], id="W-01"), dict(self.items[0], id="w-01")]}), "capitals aside")

    def test_an_id_that_is_a_path(self):
        item = dict(self.items[0], id="../x")
        self.refuse(json.dumps({"items": [item]}), "no usable id")


if __name__ == "__main__":
    unittest.main()
