#!/usr/bin/env python3
"""Records logs/planted-bugs.txt for the scrum-scope-change quest.

Puts one bug at a time into participant/skills/scrum-scope-change/scope.py,
runs every test, notes which tests fail, and takes the bug out again. At the
end it checks that the file is the same as when it started, byte for byte.

It changes scope.py while it runs. Do not run the skill at the same time.

Run from anywhere:  python3 scripts/planted_bugs.py
Exit code 0 if every bug was caught and the file was restored, 1 if not.
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ATTEMPT = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(ATTEMPT, "..", "..", "..", ".."))
SKILL = os.path.join(ROOT, "participant", "skills", "scrum-scope-change")
TARGET = os.path.join(SKILL, "scope.py")

# (what the bug is, the text to replace, what to replace it with)
BUGS = [
    ('A. Items are matched by title, so a renamed item is reported as added (criterion 1)',
     '    added = sorted(i for i in b if i not in a and i not in spoiled)',
     '    added = sorted(i for i in b if b[i].get("title") not in [o.get("title") for o in a.values()] and i not in spoiled)'),
    ('B. An item in the later snapshot only is not reported as added (criterion 2)',
     '    added = sorted(i for i in b if i not in a and i not in spoiled)',
     '    added = []'),
    ('C. An item in the start snapshot only is not reported as removed (criterion 3)',
     '    removed = sorted(i for i in a if i not in b and i not in spoiled)',
     '    removed = []'),
    ('D. A changed estimate is not material (criterion 4)',
     '        elif was["number"] != now["number"]:',
     '        elif False:'),
    ('E. A changed scope list is not material (criterion 4)',
     '        for key in LISTS:\n            if was.get(key) is None or now.get(key) is None or (not was[key]',
     '        for key in ("acceptance",):\n            if was.get(key) is None or now.get(key) is None or (not was[key]'),
    ('F. Changed acceptance criteria are not material (criterion 4)',
     '        for key in LISTS:\n            if was.get(key) is None or now.get(key) is None or (not was[key]',
     '        for key in ("scope",):\n            if was.get(key) is None or now.get(key) is None or (not was[key]'),
    ('G. A criterion whose words changed is noise unless one was added or taken out',
     '            elif multiset(was[key]) != multiset(now[key]):',
     '            elif multiset(was[key]) != multiset(now[key]) and len(was[key]) != len(now[key]):'),
    ('H. Capitals in a list entry count as a change (criterion 5)',
     '    return text.casefold()',
     '    return text'),
    ('I. A full stop at the end of a list entry counts as a change (criterion 5)',
     '    if text[-1:] in (".", ";", ",") and text[-2:-1] not in (".", ";", ","):',
     '    if False:'),
    ('J. A comma inside an entry is set aside, so 1,5 and 15 are the same',
     '    return text.casefold()',
     '    return re.sub(r"[.;,]", "", text).casefold()'),
    ('K. A dash becomes a space, so a range and a pair are the same',
     'DASHES.sub("-", ',
     'DASHES.sub(" ", '),
    ('L. Every difference is material: a title, a description or an assignee counts (criterion 5)',
     '(material if differs else undecided if untold else noise if also else unchanged).append(entry)',
     '(material if differs or also else undecided if untold else unchanged).append(entry)'),
    ('M. A change of assignee is not listed at all',
     '        for key in NOISE:',
     '        for key in ("title", "description"):'),
    ('N. A blank estimate is counted as nothing',
     'return Decimal(text) if isinstance(text, str) and NUMBER.match(text) else None',
     'return Decimal(text) if isinstance(text, str) and NUMBER.match(text) else Decimal(0) if text == "" else None'),
    ('O. An estimate written differently, and the same number, is material',
     '        elif was["number"] != now["number"]:',
     '        elif was.get("estimate") != now.get("estimate"):'),
    ('P. An identifier given twice in one snapshot: the last item is used',
     '            del items[identity]\n            spoiled.add(identity)',
     '            spoiled.add(identity)'),
    ('Q. An item given twice in one snapshot is reported as removed',
     '    removed = sorted(i for i in a if i not in b and i not in spoiled)',
     '    removed = sorted(i for i in a if i not in b)'),
    ('R. With a snapshot missing, every item is reported as removed',
     '    a = usable(start, start_name) if comparable else {}',
     '    a = usable(start, start_name)'),
    ('S. With a snapshot missing, totals and a net change are still printed',
     '    if not model["comparable"]:\n        out += ["Not compared. See section 7."]\n    else:\n        out += ["The committed total',
     '    if False:\n        out += ["Not compared. See section 7."]\n    else:\n        out += ["The committed total'),
    ('T. The net change loses its sign (criterion 7)',
     '"- **Net change: %s points.**" % (signed(net) if net else "0"),\n                "- **Points that moved',
     '"- **Net change: %s points.**" % points(abs(net)),\n                "- **Points that moved'),
    ('U. The points that moved leave out the re-estimates',
     'moved = model["added_sum"] + model["removed_sum"] + sum((abs(now - was) for _, was, now in model["reest"]), Decimal(0))',
     'moved = model["added_sum"] + model["removed_sum"]'),
    ('V. "No change" is said whenever the net change is nothing (criterion 6)',
     '"nothing": comparable and not (added or removed or material or noise or undecided)}',
     '"nothing": later_total == start_total}'),
    ('W. "No change" is said when only noise differs',
     '"nothing": comparable and not (added or removed or material or noise or undecided)}',
     '"nothing": comparable and not (added or removed or material or undecided)}'),
    ("X. An item with an unusable estimate on one side stays in the other side's total",
     '(i in a and (a[i]["number"] is None or a[i]["doubt"])) or (i in b and (b[i]["number"] is None or b[i]["doubt"])) or (i in spoiled',
     '(i in a and a[i]["number"] is None and i in b and b[i]["number"] is None) or (i in spoiled'),
    ("Y. An item given twice in one snapshot stays in the other snapshot's total",
     ' or (i in spoiled and (i in a) != (i in b)))',
     ')'),
    ('Z. A line in an item that is not a field is dropped silently',
     '                else:\n                    current = None\n                    one["unread"].append(line.strip())',
     '                else:\n                    current = None'),
    ('AA. An item with a line that was not read can still be called unchanged',
     'doubt=bool(one["unread"] or one["repeated"])',
     'doubt=False'),
    ('AB. A field given twice is not reported',
     '                    if key in one:\n                        one["repeated"].append(key)',
     '                    if False:\n                        one["repeated"].append(key)'),
    ('AC. A number at the front of an entry is always taken for numbering',
     '    if len(out) > 1 and all(numbers) and [int(m.group(1)) for m in numbers] == list(range(1, len(out) + 1)):',
     '    if out and all(numbers):'),
    ('AD. Items under a heading that is not a snapshot are reported as added',
     ' | read_in["orphans"]',
     ''),
    ('AE. An item whose heading has more than its identifier is reported as added',
     '                if inside:\n                    spoiled.add(inside.group(0))',
     '                if False:\n                    spoiled.add(inside.group(0))'),
    ('AF. The effect of an added item on uncommitted capacity has the wrong sign',
     '"%s points of uncommitted capacity" % signed(-b[i]["number"])',
     '"%s points of uncommitted capacity" % signed(b[i]["number"])'),
    ('AG. A change whose changed_by is the product owner is listed as other text',
     'other = [(i, kind, who) for i, kind, who in changed if who and who != model["owner"]]',
     'other = [(i, kind, who) for i, kind, who in changed if who]'),
    ('AH. A change with nobody recorded is not listed',
     'unsaid = [(i, kind) for i, kind, who in changed if not who]',
     'unsaid = []'),
    ('AI. Any cell that says "Made up" makes the report call the file made up',
     'if "**Made up.**" in model["read"]["front"] else',
     'if "**Made up.**" in str(model["a"]) + str(model["b"]) + model["read"]["front"] else'),
    ('AJ. An entry that was only taken out is said to be a possible rewording',
     'both = bool(d["gone"]) and bool(d["came"])',
     'both = True'),
    ('AK. A reworded criterion is not said to need a person',
     'both = bool(d["gone"]) and bool(d["came"])',
     'both = False'),
    ('AL. A quote mark in a title is printed as it is',
     '(\'"\', "\'"), ("|", "/")',
     '("|", "/")'),
    ('AM. A criterion given twice counts as given once',
     '        out[plain(entry)] = out.get(plain(entry), 0) + 1',
     '        out[plain(entry)] = 1'),
    ('AN. An entry given twice and then once is not shown as gone',
     '        if left.get(plain(entry), 0) > 0:\n            left[plain(entry)] -= 1',
     '        if left.get(plain(entry), 0) > 0:\n            pass'),
    ("AO. A list written on the field's own line is read as a list",
     '                        one[key] = [] if not value else None',
     '                        one[key] = []'),
    ('AP. A list with no entries is not a gap',
     '                elif not one[key]:\n                    gap(identity, key, "in the %s snapshot it has no entries"',
     '                elif False:\n                    gap(identity, key, "in the %s snapshot it has no entries"'),
    ('AQ. A capacity that is not a number is not reported',
     '    if "capacity_points" in read_in["header"] and capacity is None:',
     '    if False:'),
    ('AR. The day a snapshot was taken, given twice, is not reported',
     '        if len(taken) > 1:',
     '        if False:'),
    ('AS. Two versions that print the same are not said to differ',
     '% LIMIT if a == b else "")',
     '% LIMIT if False else "")'),
    ('AT. The program ends as if all was well when nothing was compared',
     '        return 1\n    net = model["later_total"]',
     '        return 0\n    net = model["later_total"]'),
    ('AU. The check lets a wrong list of added, removed, material or noise through',
     '        if ids_in(n) != ids:',
     '        if False:'),
    ('AV. The check lets a wrong number in a heading through',
     '        if heads.get(n) != str(len(ids_in(n))):',
     '        if False:'),
    ('AW. The check lets an item written without its marks through',
     '        if stray:',
     '        if False:'),
    ('AX. The check lets a field be left out of a material change',
     '        if not block or re.findall(r"`(\\w+)`", block.group(1)) != [d["field"] for d in m["differs"]]:',
     '        if False:'),
    ('AY. The check lets a wrong estimate through',
     '            if d["field"] == "estimate" and (not block or',
     '            if False and (not block or'),
    ('AZ. The check lets a wrong or second total or net change through',
     '            if len(got) != 1 or not got[0].startswith(want):',
     '            if False:'),
    ('BA. The check lets "No change" stand anywhere in a report of changes',
     '    if len(re.findall(r"(?i)\\bno change\\.", report)) != (1 if model["nothing"] else 0) or ("**No change.**" in top) != model["nothing"]:',
     '    if False:'),
    ('BB. The check lets a report that compared nothing go without saying so',
     '    if ("**NOTHING WAS COMPARED.**" in top) != (not model["comparable"]):',
     '    if False:'),
    ('BC. The check lets a report of another file through',
     '    if "sha256 is `%s`" % hashlib.sha256(raw).hexdigest() not in top:',
     '    if False:'),
    ('BD. The check lets an item in neither snapshot be named',
     '        if identity not in known:',
     '        if False:'),
    ('BE. The check lets the unchanged list be wrong',
     '    if unchanged != [u["id"] for u in model["unchanged"]] or heads.get("6") != str(len(unchanged)):',
     '    if False:'),
    ('BF. The check lets an item be in no list',
     '    if sorted(placed) != sorted(set(model["a"]) | set(model["b"])):',
     '    if False:'),
    ("BG. The check fails the program's own report of an item given twice",
     ' | {g["field"] for g in model["gaps"]}',
     ''),
    ('BH. A run of full stops at the end of an entry is set aside, so an open list equals a closed one',
     '    if text[-1:] in (".", ";", ",") and text[-2:-1] not in (".", ";", ","):\n        text = text[:-1].rstrip()',
     '    text = text.rstrip(".;, ")'),
    ('BI. Compatibility forms are folded, so a raised 2 is a 2',
     'unicodedata.normalize("NFC", entry)',
     'unicodedata.normalize("NFKC", entry)'),
    ('BJ. A double quote mark and a single one are the same',
     'SINGLE_QUOTES.sub("\'", DOUBLE_QUOTES.sub(\'"\', INVISIBLE.sub("", text)))',
     'SINGLE_QUOTES.sub("\'", DOUBLE_QUOTES.sub("\'", INVISIBLE.sub("", text))).replace(\'"\', "\'")'),
    ('BK. A list of one entry loses a number at its front',
     '    if len(out) > 1 and all(numbers) and',
     '    if out and all(numbers) and'),
    ('BL. A list that was emptied cannot be told, and is not material',
     'or (not was[key] and not now[key]):',
     'or not was[key] or not now[key]:'),
    ('BM. An item with a field given twice stays in the figures',
     '(a[i]["number"] is None or a[i]["doubt"])) or (i in b and (b[i]["number"] is None or b[i]["doubt"]))',
     'a[i]["number"] is None) or (i in b and b[i]["number"] is None)'),
    ('BN. A heading that cuts a list short is not reported',
     '                cut_off.add(last_snapshot)',
     '                pass'),
    ('BO. A heading that could not be read does not mark the net effect',
     '        if sum(model["unnamed"]):\n            out.append("- **NOT COMPLETE.**',
     '        if False:\n            out.append("- **NOT COMPLETE.**'),
    ('BP. What else differs in an item that cannot be told is not printed',
     '        if u["also"]:',
     '        if False:'),
    ('BQ. Identical items with a gap are not called unchanged',
     '        if was["block"] == now["block"] and was["doubt"] == now["doubt"]:',
     '        if False:'),
    ('BR. Entries that print the same are not said to differ',
     'if both and quoted(d["gone"]) == quoted(d["came"]) else ""))',
     'if False else ""))'),
    ('BS. List noise shows no versions',
     'At start: %s. Later: %s." % (x["field"], quoted(x["was"]), quoted(x["now"])))',
     'At start: %s. Later: %s." % (x["field"], "", ""))'),
    ('BT. The check lets a net change stand in a report that compared nothing',
     '    if not model["comparable"] and sections.get("1", "").strip() != "Not compared. See section 7.":',
     '    if False:'),
    ('BU. The check lets a wrong estimate or title on an added or removed item through',
     '            if "- `%s`: %s. \\"%s\\"" % (i, said, safe(side[i].get("title") or "")) not in sections.get(n, "").split("\\n"):',
     '            if False:'),
    ('BV. The check lets a missing NOT COMPLETE through',
     '        if ("**NOT COMPLETE.**" in sections.get("1", "")) != bool(model["out_of_figures"] or sum(model["unnamed"])):',
     '        if False:'),
    ('BW. The check does not see an identifier written without its marks',
     're.sub(r\'"[^"\\n]*"\', "", report)))):',
     '" ".join(re.findall(r"`[^`\\n]*`", report))))):'),
    ('BX. A report that cannot be written ends in an error and not a message',
     '    except (OSError, UnicodeDecodeError) as error:',
     '    except UnicodeDecodeError as error:'),
]

def run_tests():
    done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=SKILL,
                          capture_output=True, text=True)
    failed = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\w+) \((?:test_scope\.)?(\w+)", done.stderr, re.M)))
    return done.stderr.strip().splitlines()[-1], ["%s.%s" % (group, name) for name, group in failed]


def main():
    with open(TARGET, encoding="utf-8") as f:
        good = f.read()
    out = ["Do the tests notice a broken comparison? scrum-scope-change, attempt scrum-attempt-003",
           "Recorded by scripts/planted_bugs.py.", "",
           "Each bug below was put into participant/skills/scrum-scope-change/scope.py, every test was run, and the",
           "bug was taken out again. Only local files are used.", ""]
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
            out += ["  unittest result: %s" % last, "  tests that failed (%d):" % len(failed)]
            out += ["    " + test for test in failed] or ["    NONE. THIS BUG WAS NOT CAUGHT."]
            out += [""]
            if not failed:
                missed.append(title)
    finally:
        with open(TARGET, "w", encoding="utf-8") as f:
            f.write(good)
    with open(TARGET, encoding="utf-8") as f:
        restored = f.read() == good
    last, failed = run_tests()
    out += ["After the last bug was taken out: scope.py is %s it was at the start. %s"
            % ("byte for byte what" if restored else "NOT what", last), ""]
    ok = clean and restored and not missed and not failed
    out += ["RESULT: %s" % ("all %d planted bugs were caught by at least one test, and the file was restored."
                            % len(BUGS) if ok else "NOT ALL AS EXPECTED: %s" % ("; ".join(missed) or "see above"))]
    os.makedirs(os.path.join(ATTEMPT, "logs"), exist_ok=True)
    with open(os.path.join(ATTEMPT, "logs", "planted-bugs.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print(out[-1])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
