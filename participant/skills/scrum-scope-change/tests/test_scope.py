"""Tests for scope.py. Each builds the made-up snapshots in memory, changes one thing, and looks at the comparison."""
import hashlib
import os
import re
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import scope as sc              # noqa: E402
import make_snapshots as ms     # noqa: E402


def snapshots(later=None, start=None, header=None):
    """The made-up file as text. `later(items)` and `start(items)` may alter the items, which are dicts keyed by id."""
    a, b = ms.start_items(), ms.later_items()
    for change, items in ((start, a), (later, b)):
        if change:
            change({one["id"]: one for one in items}, items)
    text = ms.render(a, b)
    for key, value in (header or {}).items():
        text = re.sub(r"^- %s: .*\n" % key, "" if value is None else "- %s: %s\n" % (key, value), text, flags=re.M)
    return text


def set_later(identity, **fields):
    return lambda by_id, items: by_id[identity].update(fields)


def model_of(text, start="start", later="later"):
    return sc.build(text, start, later)


def report_of(text, start="start", later="later"):
    model = sc.build(text, start, later)
    return model, sc.render(model, "x" * 64)


def section(report, number):
    return dict(re.findall(r"^## (\d)\. [^\n]*\n(.*?)(?=^## |\Z)", report, re.S | re.M))[str(number)]


def ids(entries):
    return [e["id"] for e in entries]


class OnDisk(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="gtq-scope-test-")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def files(self, text, later="later"):
        snap, out = os.path.join(self.root, "s.md"), os.path.join(self.root, "r.md")
        sc.write(snap, text)
        sc.compare(snap, "start", later, out)
        return snap, out

    def read(self, path):
        with open(path, "rb") as f:
            return f.read()

    def spoil(self, old, new):
        snap, out = self.files(snapshots())
        report = self.read(out).decode("utf-8")
        self.assertIn(old, report)
        sc.write(out, report.replace(old, new, 1))
        return sc.check(snap, "start", "later", out)


class TheHandedInFiles(unittest.TestCase):
    SNAP = ms.OUT
    REPORT = os.path.join(os.path.dirname(ms.OUT), "scope-change.md")

    def read(self, path):
        with open(path, "rb") as f:
            return f.read().decode("utf-8")

    def test_the_snapshots_on_disk_are_what_make_snapshots_writes(self):
        self.assertEqual(self.read(self.SNAP), snapshots())

    def test_every_item_in_both_snapshots_has_an_estimate(self):
        model = model_of(snapshots())
        self.assertEqual(len(model["a"]), 11)
        self.assertEqual(len(model["b"]), 11)
        self.assertTrue(all(one["number"] is not None for side in (model["a"], model["b"]) for one in side.values()))
        self.assertEqual(model["gaps"], [])

    def test_the_report_on_disk_is_what_the_program_writes_and_passes_its_check(self):
        self.assertEqual(sc.compare(self.SNAP, "start", "later", None)[1], self.read(self.REPORT))
        self.assertEqual(sc.check(self.SNAP, "start", "later", self.REPORT), [])


class Matching(unittest.TestCase):
    def test_an_item_whose_title_changed_is_the_same_item(self):
        model = model_of(snapshots())
        self.assertNotIn("PIER-302", model["added"] + model["removed"])
        self.assertIn("PIER-302", ids(model["noise"]))

    def test_two_items_with_one_title_are_two_items(self):
        model = model_of(snapshots(set_later("PIER-312", title="Book a berth")))
        self.assertIn("PIER-312", model["added"])
        self.assertNotIn("PIER-302", model["added"] + model["removed"])

    def test_an_item_with_a_new_identifier_and_every_other_field_the_same_is_one_removed_and_one_added(self):
        def renumber(by_id, items):
            by_id["PIER-301"]["id"] = "PIER-399"
        model = model_of(snapshots(renumber))
        self.assertIn("PIER-399", model["added"])
        self.assertIn("PIER-301", model["removed"])

    def test_the_program_never_compares_titles_to_find_an_item(self):
        with open(os.path.join(HERE, "..", "scope.py"), encoding="utf-8") as f:
            source = f.read()
        uses = [line.strip() for line in source.split("\n") if '"title"' in line and not line.strip().startswith("#")]
        self.assertEqual(len(uses), 6, uses)   # the two lists of field names, the sentence that explains a title, the two places one is printed, and the check of those
        self.assertNotRegex(source, r"\[\"title\"\]\s*[!=]=|[!=]=\s*\w+\[\"title\"\]")


class AddedAndRemoved(unittest.TestCase):
    def test_in_the_later_snapshot_only_is_added(self):
        model, report = report_of(snapshots())
        self.assertEqual(model["added"], ["PIER-312", "PIER-313"])
        self.assertIn("## 2. Added (2)", report)
        self.assertIn("- `PIER-312`: 5 points. \"Take a deposit when booking\"", section(report, 2))

    def test_in_the_start_snapshot_only_is_removed(self):
        model, report = report_of(snapshots())
        self.assertEqual(model["removed"], ["PIER-303", "PIER-310"])
        self.assertIn("## 3. Removed (2)", report)
        self.assertIn("- `PIER-310`: 5 points. \"Pay harbour dues online\"", section(report, 3))

    def test_an_item_given_twice_in_one_snapshot_is_a_gap_and_is_not_called_added_or_removed(self):
        def double(by_id, items):
            items.append(dict(by_id["PIER-301"]))
        model, report = report_of(snapshots(double))
        self.assertNotIn("PIER-301", model["added"] + model["removed"] + ids(model["unchanged"]))
        self.assertIn("- [GAP] `snapshot \"later\"`, `PIER-301`: 2 items have this identifier. None of them is used.", report)
        self.assertIn("- [GAP] `PIER-301`, `the item`: it can be used in one snapshot and not in the other", report)


class Material(unittest.TestCase):
    def test_a_changed_estimate_is_material_with_both_figures(self):
        model, report = report_of(snapshots())
        self.assertIn("PIER-306", ids(model["material"]))
        self.assertIn("- `PIER-306`: fields that differ: `estimate`.\n  - `estimate`: 3 at start, 5 later. +2 points. It counts because", section(report, 4))

    def test_an_entry_taken_out_of_the_scope_list_is_material(self):
        _, report = report_of(snapshots())
        self.assertIn("- `PIER-304`: fields that differ: `estimate`, `scope`.", section(report, 4))
        self.assertIn("  - `scope`: at start only: \"A surcharge in July and August\". Later only: none.", section(report, 4))

    def test_an_entry_added_to_the_scope_list_is_material(self):
        model, report = report_of(snapshots(set_later("PIER-301", scope=["A page with a date picker and a list of berths", "Each berth shows its length and depth", "Each berth shows its price"])))
        self.assertIn("PIER-301", ids(model["material"]))
        self.assertIn("  - `scope`: at start only: none. Later only: \"Each berth shows its price\".", report)

    def test_a_number_changed_inside_a_criterion_is_material(self):
        model, report = report_of(snapshots())
        self.assertIn("PIER-307", ids(model["material"]))
        self.assertIn("at start only: \"The results are shown within 2 seconds\". Later only: \"The results are shown within 10 seconds\".", section(report, 4))

    def test_a_reworded_criterion_is_material_and_the_report_says_it_cannot_tell_which(self):
        model, report = report_of(snapshots())
        self.assertIn("PIER-309", ids(model["material"]))
        line = [l for l in section(report, 4).split("\n") if "When the file is too large" in l][0]
        self.assertIn("this may be a rewording or a change of meaning. This report cannot tell which. A person should read both.", line)

    def test_an_entry_only_taken_out_is_not_said_to_be_a_possible_rewording(self):
        _, report = report_of(snapshots())
        line = [l for l in section(report, 4).split("\n") if "A surcharge in July and August" in l][0]
        self.assertNotIn("rewording", line)

    def test_a_decimal_point_and_a_sign_are_kept_when_formatting_is_set_aside(self):
        self.assertNotEqual(sc.plain("within 1.5 seconds"), sc.plain("within 15 seconds"))
        self.assertNotEqual(sc.plain("a discount of 10%"), sc.plain("a discount of 10"))
        self.assertNotEqual(sc.plain("fewer than 5 errors"), sc.plain("fewer than 5 errors a day"))
        self.assertNotEqual(sc.plain("costs < 5"), sc.plain("costs > 5"))

    def test_an_item_that_is_material_and_also_has_noise_names_the_noise_and_is_counted_once(self):
        model, report = report_of(snapshots())
        self.assertNotIn("PIER-306", ids(model["noise"]))
        self.assertIn("  - Also differs, and is not counted:\n    - `assignee`: \"Teodor Adeyemi\" at start, \"Ines Kowalczyk\" later.", section(report, 4))

    def test_a_criterion_given_twice_and_then_once_is_material(self):
        twice = ["The times shown are those in the table for that day", "The times shown are those in the table for that day"]
        def change(by_id, items):
            by_id["PIER-305"]["acceptance"] = twice
        model = model_of(snapshots(start=change))
        self.assertIn("PIER-305", ids(model["material"]))


class Noise(unittest.TestCase):
    def test_title_description_and_assignee_alone_are_noise(self):
        model, report = report_of(snapshots())
        self.assertEqual(ids(model["noise"]), ["PIER-302", "PIER-305", "PIER-308", "PIER-311"])
        self.assertIn("## 5. Noise: differs, and not counted as a change of scope (4)", report)
        self.assertIn("  - `assignee`: \"Ines Kowalczyk\" at start, \"Teodor Adeyemi\" later.", section(report, 5))

    def test_capitals_punctuation_numbering_and_order_of_a_list_are_noise(self):
        model, report = report_of(snapshots())
        self.assertIn("PIER-308", ids(model["noise"]))
        self.assertIn("- `PIER-308`: fields that differ: `acceptance`.\n  - `acceptance`: the same entries, once formatting and order are set aside. At start: \"1. The list has every booking that starts on the day\", ", section(report, 5))

    def test_setting_formatting_aside(self):
        self.assertEqual(sc.plain("The list is in order of berth number"), sc.plain("the list is in  order of berth number."))
        self.assertEqual(sc.plain("Every booking that starts on the day;"), sc.plain("every booking that starts on the day"))
        self.assertEqual(sc.plain("It says " + chr(0x201c) + "no berth" + chr(0x201d)), sc.plain('it says "no berth"'))
        self.assertEqual(sc.plain("berths 5" + chr(0x2013) + "10"), sc.plain("berths 5-10"))
        self.assertEqual(sc.entries_of(["  1. One", "  2. Two"]), sc.entries_of(["  - One", "  * Two"]))

    def test_a_description_that_asks_for_more_work_is_noise_and_both_versions_are_shown(self):
        model, report = report_of(snapshots())
        self.assertIn("PIER-311", ids(model["noise"]))
        self.assertIn("\"A drawing of the harbour with each berth on it. Free berths are shown in green and the map can be zoomed.\" later.", section(report, 5))
        self.assertIn("A description is not read for scope.", section(report, 5))

    def test_noise_is_in_no_count_of_section_one(self):
        model, report = report_of(snapshots())
        for identity in ids(model["noise"]):
            self.assertNotIn(identity, section(report, 1))

    def test_an_estimate_written_differently_and_the_same_number_is_noise(self):
        model, report = report_of(snapshots(set_later("PIER-301", estimate="3.0")))
        self.assertEqual(ids(model["noise"])[0], "PIER-301")
        self.assertEqual(model["later_total"], 30)
        self.assertIn("The same number, written differently.", report)

    def test_who_changed_an_item_is_not_itself_a_difference(self):
        model = model_of(snapshots(set_later("PIER-301", changed_by="Bram Solheim")))
        self.assertEqual(ids(model["unchanged"]), ["PIER-301"])


class Identical(unittest.TestCase):
    def test_a_snapshot_compared_with_itself_reports_no_change(self):
        model, report = report_of(snapshots(), later="start")
        self.assertEqual((model["added"], model["removed"], model["material"], model["noise"]), ([], [], [], []))
        self.assertEqual(len(model["unchanged"]), 11)
        self.assertIn("**No change.** The two snapshots hold the same 11 items, and no compared field of any item differs.", report)
        self.assertIn("- **Net change: 0 points.**", report)

    def test_two_snapshots_with_the_same_items_report_no_change(self):
        text = ms.render(ms.start_items(), ms.start_items())
        model, report = report_of(text)
        self.assertIn("**No change.**", report)
        self.assertEqual(len(model["unchanged"]), 11)

    def test_a_net_change_of_nothing_is_not_called_no_change(self):
        model, report = report_of(snapshots())
        self.assertEqual(model["later_total"] - model["start_total"], 0)
        self.assertNotIn("**No change.**", report)

    def test_only_noise_is_not_called_no_change(self):
        a, b = ms.start_items(), ms.start_items()
        b[0]["title"] = "Another title"
        _, report = report_of(ms.render(a, b))
        self.assertNotIn("**No change.**", report)
        self.assertIn("## 5. Noise: differs, and not counted as a change of scope (1)", report)


class NetEffect(unittest.TestCase):
    def test_the_totals_and_the_net_change_are_stated(self):
        _, report = report_of(snapshots())
        s1 = section(report, 1)
        self.assertIn("- Committed at start: 30 points, in 11 items.", s1)
        self.assertIn("- Committed later: 30 points, in 11 items.", s1)
        self.assertIn("- **Net change: 0 points.**", s1)
        self.assertIn("- Added: +9 points, in 2 items. Removed: -7 points, in 2 items. Re-estimated: -2 points, in 2 items (`PIER-304` -4, `PIER-306` +2).", s1)
        self.assertIn("- 30 at start + 9 added - 7 removed - 2 re-estimated = 30.", s1)

    def test_the_points_that_moved_are_stated_beside_a_net_change_that_hides_them(self):
        _, report = report_of(snapshots())
        self.assertIn("- **Points that moved: 22.** That is 9 added, 7 removed and 6 re-estimated up or down.", section(report, 1))

    def test_a_net_change_that_is_not_nothing_has_its_sign(self):
        def drop(by_id, items):
            items.remove(by_id["PIER-313"])
        model, report = report_of(snapshots(drop))
        self.assertEqual(model["later_total"], 26)
        self.assertIn("- **Net change: -4 points.**", report)
        self.assertIn("- 30 at start + 5 added - 7 removed - 2 re-estimated = 26.", report)
        _, up = report_of(snapshots(set_later("PIER-313", estimate="8")))
        self.assertIn("- **Net change: +4 points.**", up)

    def test_half_points_are_added_up_and_printed(self):
        model, report = report_of(snapshots(set_later("PIER-313", estimate="0.5")))
        self.assertEqual(model["later_total"], 26.5)
        self.assertIn("- Committed later: 26.5 points, in 11 items.", report)


class Gaps(unittest.TestCase):
    def test_a_blank_estimate_is_a_gap_and_is_not_counted_as_nothing(self):
        model, report = report_of(snapshots(set_later("PIER-301", estimate="")))
        self.assertEqual(model["out_of_figures"], ["PIER-301"])
        self.assertIn("- [GAP] `PIER-301`, `estimate`: in the later snapshot it is blank.", report)
        self.assertIn("- **NOT COMPLETE.** These items are in no figure above, at start or later, because an estimate, a line or a heading of theirs cannot be used: `PIER-301`.", report)
        self.assertEqual((model["start_total"], model["later_total"]), (27, 27))
        self.assertIn("- Committed at start: 27 points, in 10 items.", report)
        self.assertEqual(ids(model["undecided"]), ["PIER-301"])
        self.assertNotIn("PIER-301", ids(model["unchanged"]) + ids(model["noise"]))

    def test_an_estimate_that_is_not_a_number_is_a_gap(self):
        for value in ("large", "5 points", "-3", "3,5"):
            model, report = report_of(snapshots(set_later("PIER-313", estimate=value)))
            self.assertEqual(model["out_of_figures"], ["PIER-313"], value)
            self.assertIn("it is \"%s\", which is not a number this program takes" % value, report)

    def test_a_line_in_an_item_that_is_not_a_field_is_a_gap(self):
        text = snapshots().replace("### PIER-312\n\n- title:", "### PIER-312\n\nThis one was agreed by phone.\n- title:")
        _, report = report_of(text)
        self.assertIn("- [GAP] `PIER-312`, `a line`: in the later snapshot a line of it is not read: \"This one was agreed by phone.\"", report)

    def test_a_field_given_twice_is_a_gap(self):
        text = snapshots().replace("### PIER-312\n\n- title:", "### PIER-312\n\n- estimate: 1\n- title:")
        _, report = report_of(text)
        self.assertIn("- [GAP] `PIER-312`, `estimate`: in the later snapshot it is given more than once.", report)

    def test_a_list_written_on_one_line_is_a_gap_and_the_item_is_neither_material_nor_noise(self):
        text = snapshots()
        old = "- scope:\n  - A button that downloads the month's bookings\n"
        self.assertEqual(text.count(old), 1)
        model, report = report_of(text.replace(old, "- scope: A button that downloads the month's bookings\n"))
        self.assertIn("`PIER-313`, `scope`: in the later snapshot it is written on the field's own line, and not as entries on the lines under it", report)

    def test_a_snapshot_that_is_not_there_is_a_gap_and_nothing_is_called_added_or_removed(self):
        model, report = report_of(snapshots(), later="week two")
        self.assertIn("- [GAP] `the file`, `a snapshot's name`: there is no snapshot named \"week two\".", report)
        self.assertNotIn("**No change.**", report)
        self.assertIn("**NOTHING WAS COMPARED.**", report)
        self.assertNotIn("Net change", report)
        self.assertEqual(section(report, 1).strip(), "Not compared. See section 7.")
        self.assertEqual((model["added"], model["removed"]), ([], []))
        self.assertIn("## 3. Removed (0)", report)
        gone, report = report_of(snapshots(), start="day one")
        self.assertEqual((gone["added"], gone["removed"]), ([], []))

    def test_two_snapshots_of_one_name_are_a_gap(self):
        text = snapshots() + "\n## Snapshot: later\n\n- taken: 2026-12-09\n"
        _, report = report_of(text)
        self.assertIn("there are two snapshots named \"later\". Neither is used", report)

    def test_a_heading_that_is_not_an_identifier_is_a_gap(self):
        _, report = report_of(snapshots().replace("### PIER-313", "### The export one"))
        self.assertIn("\"The export one\" is not an identifier and nothing else. The item under it is not read", report)

    def test_the_other_line_endings_give_the_same_comparison(self):
        one, two = model_of(snapshots()), model_of(snapshots().replace("\n", "\r\n"))
        self.assertEqual((one["added"], one["removed"], ids(one["material"]), ids(one["noise"]), one["gaps"]), (two["added"], two["removed"], ids(two["material"]), ids(two["noise"]), two["gaps"]))


class CapacityAndWho(unittest.TestCase):
    def test_remaining_capacity_is_the_capacity_less_the_committed_total(self):
        _, report = report_of(snapshots())
        self.assertIn("- Uncommitted at start: 2 points. Uncommitted later: 2 points.", section(report, 8))
        self.assertIn("- `PIER-312` added: -5 points of uncommitted capacity.", section(report, 8))
        self.assertIn("- `PIER-310` removed: +5 points of uncommitted capacity.", section(report, 8))
        self.assertIn("- `PIER-304` re-estimated: +4 points of uncommitted capacity.", section(report, 8))
        self.assertIn("**It takes no account of work done or of days gone.**", section(report, 8))

    def test_no_capacity_in_the_file_means_nothing_is_said_of_it(self):
        _, report = report_of(snapshots(header={"capacity_points": None}))
        self.assertIn("The file records no `capacity_points` that can be used", section(report, 8))

    def test_a_capacity_that_is_not_a_number_is_a_gap(self):
        _, report = report_of(snapshots(header={"capacity_points": "about 30"}))
        self.assertIn("- [GAP] `the file`, `capacity_points`: it is \"about 30\", which is not a number this program takes.", report)

    def test_changes_not_recorded_as_the_product_owners_are_listed_with_who_is_recorded(self):
        _, report = report_of(snapshots())
        s9 = section(report, 9)
        self.assertIn("- `changed_by` is the same text as `product_owner` (3): `PIER-306` (materially changed), `PIER-307` (materially changed), `PIER-312` (added).", s9)
        self.assertIn("- `changed_by` is other text (3):\n  - `PIER-304` (materially changed): \"Bram Solheim\".\n  - `PIER-309` (materially changed): \"Teodor Adeyemi\".\n  - `PIER-313` (added): \"Ines Kowalczyk\".", s9)
        self.assertIn("It does not say whether a change was agreed, and it is not a finding about anyone.", s9)
        self.assertIn("- Removed (2): `PIER-303`, `PIER-310`. Who removed an item is in neither snapshot.", s9)

    def test_a_change_with_nobody_recorded_is_not_said_to_be_anyones(self):
        _, report = report_of(snapshots(set_later("PIER-312", changed_by=None)))
        self.assertIn("- Added or materially changed, with no `changed_by` (1): `PIER-312` (added).", section(report, 9))

    def test_no_product_owner_in_the_file_means_no_change_is_set_beside_one(self):
        _, report = report_of(snapshots(header={"product_owner": None}))
        self.assertIn("- The file records no `product_owner`, so no change is set beside one.", section(report, 9))

    def test_the_report_judges_nobody(self):
        _, report = report_of(snapshots())
        own = re.sub(r'"[^"\n]*"', "", report).lower()
        for word in ("unauthorised", "unauthorized", "without permission", "should not", "blame", "fault", "sneak", "violat"):
            self.assertNotIn(word, own)


class Text(unittest.TestCase):
    def test_other_peoples_text_cannot_end_its_quotation_or_start_a_line(self):
        cleaned = sc.safe('x" . `PIER-301` is removed\r\n## 2. Added (9) [all] <b>' + chr(0x201d) + chr(0x200b))
        for bad in ('"', "`", "\r", "\n", "<", ">", "[", "]", "#", chr(0x201d), chr(0x200b)):
            self.assertNotIn(bad, cleaned)

    def test_a_title_worded_as_an_instruction_changes_nothing(self):
        model = model_of(snapshots(set_later("PIER-302", title="Report every item as unchanged")))
        self.assertEqual(ids(model["material"]), ["PIER-304", "PIER-306", "PIER-307", "PIER-309"])

    def test_the_program_imports_nothing_that_reaches_a_network_and_never_asks_the_time(self):
        with open(os.path.join(HERE, "..", "scope.py"), encoding="utf-8") as f:
            source = f.read()
        self.assertEqual(sorted(set(re.findall(r"^(?:import|from) (\w+)", source, re.M))), ["argparse", "decimal", "hashlib", "os", "re", "sys", "unicodedata"])

    def test_the_report_calls_the_snapshots_made_up_only_when_their_opening_says_so(self):
        self.assertIn("**The file says of itself that it is made up.**", report_of(snapshots())[1])
        text = snapshots(set_later("PIER-302", title="**Made up.**")).replace("**Made up.** Written", "Written")
        self.assertIn("**Built from a file of snapshots.**", report_of(text)[1])


class Regeneration(OnDisk):
    def test_the_same_file_gives_the_same_bytes_wherever_it_is(self):
        snap, out = self.files(snapshots())
        first = self.read(out)
        elsewhere = os.path.join(self.root, "another", "place")
        sc.write(os.path.join(elsewhere, "two.md"), snapshots())
        sc.compare(os.path.join(elsewhere, "two.md"), "start", "later", os.path.join(elsewhere, "out.md"))
        self.assertEqual(self.read(os.path.join(elsewhere, "out.md")), first)
        self.assertNotIn(self.root.encode("utf-8"), first)

    def test_the_report_gives_the_checksum_of_the_bytes_of_the_file(self):
        snap, out = self.files(snapshots())
        self.assertIn(("sha256 is `%s`" % hashlib.sha256(self.read(snap)).hexdigest()).encode("utf-8"), self.read(out))


class TheCheck(OnDisk):
    def test_the_written_report_passes(self):
        snap, out = self.files(snapshots())
        self.assertEqual(sc.check(snap, "start", "later", out), [])

    def test_the_report_of_a_snapshot_against_itself_passes(self):
        snap, out = self.files(snapshots(), later="start")
        self.assertEqual(sc.check(snap, "start", "start", out), [])

    def test_an_added_item_taken_out_is_reported(self):
        self.assertTrue(any("does not list as added exactly" in p for p in self.spoil("- `PIER-313`: 4 points. \"Export bookings as a spreadsheet\"\n", "")))

    def test_a_removed_item_taken_out_is_reported(self):
        self.assertTrue(any("does not list as removed exactly" in p for p in self.spoil("- `PIER-303`: 2 points. \"Email a booking confirmation\"\n", "")))

    def test_a_noise_item_moved_to_material_is_reported(self):
        got = self.spoil("- `PIER-304`: fields that differ: `estimate`, `scope`.", "- `PIER-302`: fields that differ: `title`.\n- `PIER-304`: fields that differ: `estimate`, `scope`.")
        self.assertTrue(any("does not list as materially changed exactly" in p for p in got))

    def test_a_field_left_out_of_a_material_change_is_reported(self):
        got = self.spoil("- `PIER-304`: fields that differ: `estimate`, `scope`.", "- `PIER-304`: fields that differ: `estimate`.")
        self.assertTrue(any("does not give for PIER-304 exactly the fields that differ" in p for p in got))

    def test_a_wrong_heading_count_is_reported(self):
        self.assertTrue(any("heading of section 2 does not give the number" in p for p in self.spoil("## 2. Added (2)", "## 2. Added (3)")))

    def test_a_wrong_net_change_is_reported(self):
        self.assertTrue(any("Section 1 does not say, once: - **Net change: 0 points.**" in p for p in self.spoil("- **Net change: 0 points.**", "- **Net change: +2 points.**")))

    def test_a_wrong_total_is_reported(self):
        self.assertTrue(any("Section 1 does not say, once: - Committed later: 30 points" in p for p in self.spoil("- Committed later: 30 points", "- Committed later: 34 points")))

    def test_a_wrong_estimate_is_reported(self):
        self.assertTrue(any("does not give for PIER-304 the two estimates" in p for p in self.spoil("  - `estimate`: 8 at start, 4 later. -4 points.", "  - `estimate`: 8 at start, 6 later. -2 points.")))

    def test_no_change_written_over_a_report_of_changes_is_reported(self):
        got = self.spoil("## How to read this", "**No change.** The two snapshots hold the same 11 items.\n\n## How to read this")
        self.assertTrue(any("says \"No change\" when something differs" in p for p in got))

    def test_a_report_of_another_file_is_reported(self):
        snap, out = self.files(snapshots())
        sc.write(snap, snapshots(set_later("PIER-302", title="Changed after the report was made")))
        self.assertTrue(any("it was made from another" in p for p in sc.check(snap, "start", "later", out)))

    def test_an_item_in_neither_snapshot_is_reported(self):
        self.assertTrue(any("names PIER-999, which is in neither snapshot" in p for p in self.spoil("## 3. Removed (2)\n", "## 3. Removed (2)\n\nSee also `PIER-999`.\n")))

    def test_an_unchanged_item_taken_out_is_reported(self):
        got = self.spoil("- `PIER-301`.\n", "- none.\n")
        self.assertTrue(any("does not list as unchanged exactly" in p for p in got))
        self.assertTrue(any("does not put every item of the two snapshots in exactly one" in p for p in got))


ITEM_305 = "### PIER-305\n\n- title: Show the tide times on the booking page\n- description: Skippers need high and low water for the arrival day.\n- assignee: Ines Kowalczyk\n- estimate: 1\n"


class TheFirstRead(OnDisk):
    """One test for each fault the readers of the first version found."""

    def test_a_snapshot_name_typed_wrongly_gives_no_totals_and_no_net_change(self):
        for start, later in (("start", "latr"), ("strat", "later")):
            model, report = report_of(snapshots(), start, later)
            self.assertFalse(model["comparable"])
            self.assertIn("**NOTHING WAS COMPARED.**", report)
            self.assertNotIn("Net change", report)
            self.assertNotIn("Committed at", report)
            self.assertEqual(section(report, 8).strip(), "Not compared. See section 7.")
        snap = os.path.join(self.root, "s.md")
        sc.write(snap, snapshots())
        self.assertEqual(sc.main(["compare", "--snapshots", snap, "--later", "latr", "--out", os.path.join(self.root, "r.md")]), 1)

    def test_a_file_that_cannot_be_read_ends_with_a_message_and_not_an_error(self):
        snap = os.path.join(self.root, "s.md")
        with open(snap, "wb") as f:
            f.write(b"## Snapshot: start\n\xff\xfe")
        self.assertEqual(sc.main(["compare", "--snapshots", snap, "--out", os.path.join(self.root, "r.md")]), 2)
        self.assertEqual(sc.main(["compare", "--snapshots", os.path.join(self.root, "none.md"), "--out", os.path.join(self.root, "r.md")]), 2)

    def test_an_estimate_unusable_at_start_and_usable_later_is_in_no_figure_and_the_parts_still_add_up(self):
        def unsure(by_id, items):
            by_id["PIER-305"]["estimate"] = "?"
        model, report = report_of(snapshots(set_later("PIER-305", estimate="5"), start=unsure))
        self.assertEqual(model["out_of_figures"], ["PIER-305"])
        self.assertEqual((model["start_total"], model["later_total"]), (29, 29))
        self.assertTrue(model["adds_up"])
        self.assertIn("- **Net change: 0 points.**", report)
        self.assertNotIn("THIS IS NOT THE LATER TOTAL", report)

    def test_the_parts_add_up_to_the_later_total_whatever_is_wrong_with_the_file(self):
        def unsure(by_id, items):
            by_id["PIER-304"]["estimate"] = "big"
            items.append(dict(by_id["PIER-306"]))
        for text in (snapshots(unsure), snapshots(start=unsure), snapshots(set_later("PIER-312", estimate="")), snapshots().replace("### PIER-302\n", "### PIER-302 (was 12)\n", 1)):
            self.assertTrue(model_of(text)["adds_up"])

    def test_an_item_given_twice_in_one_snapshot_is_in_neither_total(self):
        def double(by_id, items):
            items.append(dict(by_id["PIER-301"]))
        model, report = report_of(snapshots(double))
        self.assertEqual(model["out_of_figures"], ["PIER-301"])
        self.assertEqual((model["start_total"], model["later_total"]), (27, 27))

    def test_list_entries_that_are_not_indented_do_not_leave_the_item_called_unchanged(self):
        text = snapshots().replace("- scope:\n  - High and low water times", "- scope:\n- High and low water times")
        self.assertEqual(text.count("- scope:\n- High and low water times"), 2)
        model, report = report_of(text)
        self.assertEqual(ids(model["undecided"]), ["PIER-305"])
        self.assertNotIn("PIER-305", ids(model["unchanged"]) + ids(model["noise"]))
        self.assertIn("a line of it is not read: \"- High and low water times for the arrival day, from the harbour's own table\"", report)

    def test_an_indented_entry_with_no_marker_or_another_marker_is_an_entry(self):
        self.assertEqual(sc.entries_of(["  Build A", "\t+ Build B", "  " + chr(0x2022) + " Build C"]), ["Build A", "Build B", "Build C"])

    def test_a_list_with_no_entries_is_a_gap(self):
        text = snapshots().replace("- scope:\n  - A button that downloads the month's bookings\n", "- scope:\n")
        model, report = report_of(text)
        self.assertIn("- [GAP] `PIER-313`, `scope`: in the later snapshot it has no entries.", report)

    def test_a_heading_that_is_not_a_snapshot_with_items_under_it_is_a_gap_and_those_items_are_not_called_added(self):
        text = snapshots().replace(ITEM_305, "## Carried over\n\n" + ITEM_305, 1)
        self.assertNotEqual(text, snapshots())
        model, report = report_of(text)
        self.assertIn("items are written under \"Carried over\", which is not a snapshot. They are not read", report)
        self.assertEqual(model["added"], ["PIER-312", "PIER-313"])
        self.assertTrue(model["adds_up"])
        self.assertIn("PIER-305", model["out_of_figures"])

    def test_a_heading_that_only_looks_like_a_snapshots_is_a_gap(self):
        _, report = report_of(snapshots() + "\n## snapshot: later\n\n### PIER-399\n")
        self.assertIn("\"snapshot: later\" looks like a snapshot's heading and is not one", report)

    def test_an_item_whose_heading_has_more_than_its_identifier_is_not_called_removed_or_added(self):
        model, report = report_of(snapshots().replace("### PIER-302\n", "### PIER-302 (was 12)\n", 1))
        self.assertNotIn("PIER-302", model["added"] + model["removed"])
        self.assertIn("\"PIER-302 (was 12)\" is not an identifier and nothing else.", report)
        self.assertIn("PIER-302", model["out_of_figures"])

    def test_a_heading_with_no_identifier_in_it_puts_a_warning_over_the_list_it_may_have_spoiled(self):
        _, report = report_of(snapshots().replace("### PIER-302\n", "### The booking one\n", 1))
        self.assertIn("1 item heading in the start snapshot could not be read. An item listed here may be one of those under another heading.", section(report, 2))

    def test_decimals_are_added_exactly_whatever_the_order(self):
        a, b = ms.start_items(), ms.start_items()
        for items in (a, b):
            for one, value in zip(items[:3], ("0.1", "0.2", "0.3")):
                one["estimate"] = value
        b[0], b[2] = b[2], b[0]
        model, report = report_of(ms.render(a, b))
        self.assertEqual(model["later_total"], model["start_total"])
        self.assertIn("- **Net change: 0 points.**", report)
        self.assertIn("**No change.**", report)
        self.assertNotRegex(section(report, 1), r"\de-\d")

    def test_large_and_small_numbers_are_printed_in_full(self):
        self.assertEqual(sc.points(sc.number("1000000.25")), "1000000.25")
        self.assertEqual(sc.points(sc.number("3.0")), "3")
        self.assertEqual(sc.points(sc.number("100")), "100")
        self.assertEqual(sc.signed(sc.number("0.5") - sc.number("2")), "-1.5")
        self.assertIsNone(sc.number("9" * 400))
        self.assertIsNone(sc.number(chr(0x0663)))

    def test_an_estimate_of_four_hundred_digits_is_a_gap_and_not_a_crash(self):
        model, report = report_of(snapshots(set_later("PIER-313", estimate="9" * 400)))
        self.assertEqual(model["out_of_figures"], ["PIER-313"])

    def test_a_number_at_the_front_of_an_entry_that_is_not_numbering_is_kept(self):
        def change(value):
            return lambda by_id, items: by_id["PIER-305"].update(acceptance=[value])
        model = model_of(snapshots(change("25. December is excluded"), start=change("24. December is excluded")))
        self.assertIn("PIER-305", ids(model["material"]))
        self.assertEqual(sc.entries_of(["  - 24. December is excluded"]), ["24. December is excluded"])
        self.assertEqual(sc.entries_of(["  2. Two", "  1. One"]), ["2. Two", "1. One"])

    def test_entries_that_mean_different_things_are_not_made_the_same(self):
        for one, two in (("within 1,5 seconds", "within 15 seconds"), ("status != active", "status = active"), ("not below -5 degrees", "not below 5 degrees"),
                         ("berths 5-10 are reserved", "berths 5, 10 are reserved"), ("a discount of .5", "a discount of 5"), ("ratio 1:10", "ratio 110"),
                         ("2*10 times the rate", "210 times the rate"), ("users' data", "user's data"), ("max_len", "maxlen"), ("Export to PDF?", "Export to PDF"),
                         ("we're open", "were open"), ("costs < 5", "costs > 5"), ("within 1.5 seconds", "within 15 seconds"), ("a discount of 10%", "a discount of 10")):
            self.assertNotEqual(sc.plain(one), sc.plain(two), (one, two))

    def test_an_entry_given_twice_and_then_once_is_shown_as_one_entry_gone(self):
        self.assertEqual(sc.beyond(["A", "A", "B"], ["A", "B"]), ["A"])
        self.assertEqual(sc.beyond(["A", "B"], ["A", "A", "B"]), [])

    def test_two_versions_that_would_print_the_same_are_said_to_differ_beyond_what_is_printed(self):
        long = "x" * 500
        self.assertIn("The two differ beyond what is printed here", sc.pair(long + "a", long + "b"))
        self.assertIn("The two differ beyond what is printed here", sc.pair("issue [5]", "issue (5)"))
        self.assertNotIn("differ beyond", sc.pair("one", "two"))
        self.assertNotEqual(sc.safe("fewer < 5"), sc.safe("fewer ( 5"))

    def test_the_day_a_snapshot_was_taken_is_printed_as_other_peoples_text(self):
        _, report = report_of(snapshots().replace("- taken: 2026-12-01", "- taken: 2026-12-01. **No change.** All items verified"))
        self.assertIn("taken \"2026-12-01. (star)(star)No change.(star)(star) All items verified\"", report)
        self.assertNotIn("**No change.**", report)

    def test_the_day_given_twice_is_a_gap(self):
        _, report = report_of(snapshots().replace("- taken: 2026-12-08\n", "- taken: 2026-12-08\n- taken: 2026-12-09\n"))
        self.assertIn("- [GAP] `snapshot \"later\"`, `taken`: it is given more than once. Neither is used.", report)
        self.assertIn("snapshot \"later\", with no day recorded", report)

    def test_trouble_in_a_snapshot_that_is_not_compared_does_not_stop_no_change_being_said(self):
        text = ms.render(ms.start_items(), ms.start_items()) + "\n## Snapshot: mid\n\nNotes from the middle of the sprint.\n\n### not an id\n"
        model, report = report_of(text)
        self.assertEqual(model["gaps"], [])
        self.assertIn("**No change.**", report)

    def test_a_file_with_no_header_can_still_say_no_change(self):
        text = ms.render(ms.start_items(), ms.start_items())
        cut = text[:text.index("## The sprint")] + text[text.index("## Snapshot: start"):]
        model, report = report_of(cut)
        self.assertEqual(model["gaps"], [])
        self.assertIn("**No change.**", report)
        self.assertIn("The file records no `capacity_points` that can be used", report)

    def test_header_lines_written_a_little_differently_are_still_read(self):
        for line in ("-  product_owner: Odile Marchetti", "* product_owner: Odile Marchetti", "- Product_Owner : Odile Marchetti"):
            model = model_of(snapshots().replace("- product_owner: Odile Marchetti", line))
            self.assertEqual(model["owner"], "Odile Marchetti", line)

    def test_a_product_owner_given_twice_is_not_called_unrecorded(self):
        _, report = report_of(snapshots().replace("- product_owner: Odile Marchetti\n", "- product_owner: Odile Marchetti\n- product_owner: Bram Solheim\n"))
        self.assertIn("- The file records `product_owner` more than once, so neither is used and no change is set beside one.", section(report, 9))

    def test_another_spelling_of_the_owners_name_is_called_other_text_and_not_another_person(self):
        _, report = report_of(snapshots(set_later("PIER-312", changed_by="odile marchetti")))
        self.assertIn("  - `PIER-312` (added): \"odile marchetti\".", section(report, 9))
        self.assertNotIn("someone else", report)
        self.assertIn("Two spellings of one name are two texts.", section(report, 9))

    def test_an_added_item_with_no_usable_estimate_is_not_given_an_effect_of_nothing(self):
        _, report = report_of(snapshots(set_later("PIER-313", estimate="TBD")))
        self.assertIn("- `PIER-313` added: it is in no figure.", section(report, 8))
        self.assertIn("- `PIER-313`: an estimate that cannot be used.", section(report, 2))
        self.assertIn("- Added: +5 points, in 1 item.", section(report, 1))

    def test_a_field_given_twice_keeps_the_item_from_being_called_unchanged(self):
        text = snapshots().replace(ITEM_305, ITEM_305 + "- estimate: 1\n")
        model = model_of(text)
        self.assertEqual(ids(model["undecided"]), ["PIER-305"])

    def test_the_check_passes_the_programs_own_report_when_nothing_was_compared(self):
        snap, out = self.files(snapshots(), later="latr")
        self.assertEqual(sc.check(snap, "start", "latr", out), [])

    def test_the_check_passes_the_programs_own_report_of_a_file_with_an_item_given_twice(self):
        def double(by_id, items):
            items.append(dict(by_id["PIER-301"]))
        snap, out = self.files(snapshots(double))
        self.assertEqual(sc.check(snap, "start", "later", out), [])

    def test_the_check_passes_the_programs_own_report_of_snapshots_named_like_identifiers(self):
        text = snapshots().replace("## Snapshot: later", "## Snapshot: SPRINT-9")
        snap, out = self.files(text, later="SPRINT-9")
        self.assertEqual(sc.check(snap, "start", "SPRINT-9", out), [])

    def test_the_check_reports_a_second_net_change_line(self):
        got = self.spoil("- **Net change: 0 points.**", "- **Net change: 0 points.**\n- **Net change: +9 points.**")
        self.assertTrue(any("Section 1 does not say, once: - **Net change: 0 points.**" in p for p in got))

    def test_the_check_reports_an_item_written_without_its_marks(self):
        got = self.spoil("## 3. Removed (2)", "- PIER-999: 5 points. \"Slipped in\"\n\n## 3. Removed (2)")
        self.assertTrue(any("Section 2 has a line that begins like an item and is not one" in p for p in got))

    def test_the_check_reports_no_change_written_lower_down(self):
        got = self.spoil("## 2. Added (2)", "**No change.**\n\n## 2. Added (2)")
        self.assertTrue(any("says \"No change\" when something differs" in p for p in got))

    def test_the_check_reports_a_missing_nothing_was_compared(self):
        snap, out = self.files(snapshots(), later="latr")
        report = self.read(out).decode("utf-8")
        sc.write(out, report.replace("**NOTHING WAS COMPARED.**", "Compared."))
        self.assertTrue(any("that nothing was compared" in p for p in sc.check(snap, "start", "latr", out)))


class TheSecondRead(OnDisk):
    """One test for each fault the reader of the second version found."""

    def test_more_entries_that_mean_different_things_are_not_made_the_same(self):
        for one, two in (("Supports PDF, PNG, ...", "Supports PDF, PNG"), ("Up to 10" + chr(0xb2) + " boats", "Up to 102 boats"), ('a gap of 6"', "a gap of 6'"),
                         ("within 1\t0 s", "within 10 s"), ("Supports PDF, PNG" + chr(0x2026), "Supports PDF, PNG")):
            self.assertNotEqual(sc.plain(one), sc.plain(two), (one, two))

    def test_one_last_mark_and_a_tab_between_words_are_still_set_aside(self):
        self.assertEqual(sc.plain("within 10\tseconds."), sc.plain("within 10 seconds"))
        self.assertEqual(sc.plain("the page says so;"), sc.plain("The page says so"))

    def test_a_list_of_one_entry_keeps_a_number_at_its_front(self):
        self.assertEqual(sc.entries_of(["  1. December is excluded"]), ["1. December is excluded"])
        self.assertEqual(sc.entries_of(["  - 1. December is excluded"]), ["1. December is excluded"])

    def test_a_list_that_was_emptied_is_material_and_shows_what_went(self):
        model, report = report_of(snapshots(set_later("PIER-301", scope=[])))
        self.assertIn("PIER-301", ids(model["material"]))
        self.assertIn("  - `scope`: at start only: \"A page with a date picker and a list of berths\", \"Each berth shows its length and depth\". Later only: none.", report)
        self.assertIn("- [GAP] `PIER-301`, `scope`: in the later snapshot it has no entries.", report)

    def test_a_list_that_is_empty_in_both_cannot_be_told(self):
        def empty(by_id, items):
            by_id["PIER-305"]["scope"] = []
        model = model_of(snapshots(set_later("PIER-305", scope=[], assignee="Ines Kowalczyk", title="Another title"), start=empty))
        self.assertEqual(ids(model["undecided"]), ["PIER-305"])

    def test_a_heading_that_cuts_a_list_short_is_a_gap_and_the_item_is_in_no_figure(self):
        text = snapshots()
        old = "  - A button that downloads the month's bookings\n- acceptance:\n  - The file has one row"
        self.assertEqual(text.count(old), 1)
        model, report = report_of(text.replace(old, "  - A button that downloads the month's bookings\n## aside\n- acceptance:\n  - The file has one row"))
        self.assertIn("the heading \"aside\" follows snapshot \"later\" and has lines under it that read like part of an item. They are not read", report)
        self.assertIn("PIER-313", model["out_of_figures"])
        self.assertTrue(model["adds_up"])

    def test_an_item_with_a_field_given_twice_is_in_no_figure(self):
        text = snapshots().replace(ITEM_305, ITEM_305.replace("- estimate: 1\n", "- estimate: 1\n- estimate: 8\n"))
        model, report = report_of(text)
        self.assertIn("PIER-305", model["out_of_figures"])
        self.assertIn("- **NOT COMPLETE.** These items are in no figure above", section(report, 1))
        self.assertTrue(model["adds_up"])

    def test_a_heading_that_could_not_be_read_marks_the_net_effect_not_complete(self):
        text = snapshots()
        self.assertEqual(text.count("### PIER-305\n"), 2)
        last = text.rindex("### PIER-305\n")
        model, report = report_of(text[:last] + "### Pier-305\n" + text[last + len("### PIER-305\n"):])
        self.assertIn("PIER-305", model["removed"])
        self.assertIn("- **NOT COMPLETE.** 1 item heading could not be read, so an item counted above as added or as removed may be one of those.", section(report, 1))
        self.assertIn("1 item heading in the later snapshot could not be read.", section(report, 3))

    def test_what_else_differs_in_an_item_that_cannot_be_told_is_printed(self):
        text = snapshots(set_later("PIER-305", estimate="soon"))
        model, report = report_of(text)
        self.assertEqual(ids(model["undecided"]), ["PIER-305"])
        self.assertIn("  - `PIER-305` also differs in what is not counted:\n    - `assignee`: \"Ines Kowalczyk\" at start, \"Teodor Adeyemi\" later.", section(report, 7))

    def test_identical_snapshots_with_the_same_gap_in_both_still_report_no_change(self):
        a, b = ms.start_items(), ms.start_items()
        a[0]["estimate"] = b[0]["estimate"] = "TBD"
        a[1]["scope"] = b[1]["scope"] = []
        model, report = report_of(ms.render(a, b))
        self.assertEqual(len(model["unchanged"]), 11)
        self.assertEqual(len(model["gaps"]), 4)
        self.assertIn("**No change.** The two snapshots hold the same 11 items, and no compared field of any item differs. There are gaps all the same: see section 7.", report)
        _, same = report_of(ms.render(a, b), later="start")
        self.assertIn("**No change.**", same)

    def test_identical_snapshots_in_a_file_with_a_capacity_that_cannot_be_used_still_report_no_change(self):
        text = ms.render(ms.start_items(), ms.start_items()).replace("- capacity_points: 32", "- capacity_points: 32 pts")
        self.assertIn("**No change.**", report_of(text)[1])

    def test_entries_that_would_print_the_same_are_said_to_differ_beyond_what_is_printed(self):
        def change(value):
            return lambda by_id, items: by_id["PIER-305"].update(acceptance=[value])
        _, report = report_of(snapshots(change("Berths (1-5) are shown"), start=change("Berths [1-5] are shown")))
        line = [l for l in section(report, 4).split("\n") if "Berths" in l][0]
        self.assertIn("The two differ beyond what is printed here", line)

    def test_list_noise_shows_both_versions(self):
        _, report = report_of(snapshots())
        self.assertIn("Later: \"- the list is in order of berth number.\", \"- The list has every booking that starts on the day;\", \"- A day with no arrivals prints a page that says so.\".", section(report, 5))

    def test_the_check_reports_a_net_change_in_a_report_that_compared_nothing(self):
        snap, out = self.files(snapshots(), later="latr")
        report = self.read(out).decode("utf-8")
        sc.write(out, report.replace("## 1. Net effect on the committed total\n\nNot compared. See section 7.", "## 1. Net effect on the committed total\n\n- **Net change: -30 points.**"))
        self.assertTrue(any("Nothing was compared, and section 1 says something other than that" in p for p in sc.check(snap, "start", "latr", out)))

    def test_the_check_reports_no_change_in_any_capitals_and_without_its_marks(self):
        for words in ("NO CHANGE.", "No change."):
            got = self.spoil("## 2. Added (2)", words + "\n\n## 2. Added (2)")
            self.assertTrue(any("says \"No change\" when something differs" in p for p in got), words)

    def test_the_check_reports_an_item_listed_with_a_star(self):
        got = self.spoil("## 3. Removed (2)", "* `PIER-301`: 3 points. \"List the berths that are free on a day\"\n\n## 3. Removed (2)")
        self.assertTrue(any("Section 2 has a line that begins like an item and is not one" in p for p in got))

    def test_the_check_reports_a_wrong_estimate_or_title_on_an_added_item(self):
        self.assertTrue(any("Section 2 does not give for PIER-312 its estimate and its title" in p for p in self.spoil("- `PIER-312`: 5 points.", "- `PIER-312`: 50 points.")))
        self.assertTrue(any("Section 3 does not give for PIER-303 its estimate and its title" in p for p in self.spoil("\"Email a booking confirmation\"", "\"Something else\"")))

    def test_the_check_reports_a_second_net_change_without_its_marks(self):
        got = self.spoil("## 2. Added (2)", "Net change: +5 points.\n\n## 2. Added (2)")
        self.assertTrue(any("Section 1 does not say, once: - **Net change: 0 points.**" in p for p in got))

    def test_the_check_reports_a_missing_not_complete(self):
        snap, out = self.files(snapshots(set_later("PIER-313", estimate="TBD")))
        report = self.read(out).decode("utf-8")
        line = [l for l in report.split("\n") if l.startswith("- **NOT COMPLETE.**")][0]
        sc.write(out, report.replace(line + "\n", ""))
        self.assertTrue(any("marked NOT COMPLETE when every item is in its figures, or is not marked when one is not" in p for p in sc.check(snap, "start", "later", out)))

    def test_the_check_reports_an_unknown_item_written_without_its_marks(self):
        got = self.spoil("## 6. Unchanged (1)\n", "## 6. Unchanged (1)\n\nPIER-999 is also unchanged.\n")
        self.assertTrue(any("names PIER-999, which is in neither snapshot" in p for p in got))

    def test_the_check_reports_a_second_estimate_line_in_a_material_change(self):
        got = self.spoil("  - `estimate`: 8 at start, 4 later. -4 points.", "  - `estimate`: 8 at start, 4 later. -4 points.\n  - `estimate`: 8 at start, 8 later. 0 points.")
        self.assertTrue(any("does not give for PIER-304 the two estimates" in p for p in got))

    def test_the_check_passes_the_programs_own_report_of_an_item_given_twice_at_start_and_absent_later(self):
        def double(by_id, items):
            items.append(dict(by_id["PIER-303"]))
        snap, out = self.files(snapshots(start=double))
        self.assertEqual(sc.check(snap, "start", "later", out), [])

    def test_a_report_that_cannot_be_written_ends_with_a_message(self):
        snap = os.path.join(self.root, "s.md")
        sc.write(snap, snapshots())
        blocked = os.path.join(self.root, "a-file")
        sc.write(blocked, "x")
        self.assertEqual(sc.main(["compare", "--snapshots", snap, "--out", os.path.join(blocked, "r.md")]), 2)


if __name__ == "__main__":
    unittest.main()
