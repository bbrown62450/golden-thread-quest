#!/usr/bin/env python3
"""Records logs/planted-bugs.txt for the scrum-sprint-health quest.

Puts one bug at a time into participant/skills/scrum-sprint-health/health.py,
runs every test, notes which tests fail, and takes the bug out again. At the
end it checks that the file is the same as when it started, byte for byte.

It changes health.py while it runs. Do not run the skill at the same time.

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
SKILL = os.path.join(ROOT, "participant", "skills", "scrum-sprint-health")
TARGET = os.path.join(SKILL, "health.py")

# (what the bug is, the text to replace, what to replace it with)
BUGS = [
    ('A. An item with no status is counted as not started (criterion 6)',
     '        if row["status"] is None:\n            gap(identity, "status", "it is blank"',
     '        if row["status"] is None:\n            one["status"] = "todo"\n        elif False:\n            gap(identity, "status", "it is blank"'),
    ('B. A status that is not one of the three is taken as in progress (criterion 6)',
     '        elif row["status"] not in STATUSES:',
     '        elif row["status"] not in STATUSES and not setattr(sys, "_x", one.update(status="in_progress")):'),
    ('C. Aging is at the threshold and not older than it (criterion 2)',
     'info[i]["age"] is not None and info[i]["age"] > threshold',
     'info[i]["age"] is not None and info[i]["age"] >= threshold'),
    ("D. The aging threshold is a constant and not the snapshot's (criterion 2)",
     '    threshold, no_threshold = whole("aging_after_days", "aging")',
     '    threshold, no_threshold = 3, None'),
    ('E. The limit on work in progress is made up when none is recorded (criterion 4)',
     '    threshold, no_threshold = whole("aging_after_days", "aging")',
     '    threshold, no_threshold = whole("aging_after_days", "aging")\n    limit = 2 if limit is None else limit'),
    ('F. An item not in progress can be aging (criterion 2)',
     'can_age and info[i]["status"] == "in_progress" and info[i]["age"] is not None',
     'can_age and info[i]["status"] != "done" and info[i]["age"] is not None'),
    ('G. A missing update date is treated as the day of the snapshot (criterion 6)',
     '        if row["updated"] is None:\n            gap(identity, "updated", "it is blank", "aging: how long it has gone without an update is not known")',
     '        if row["updated"] is None:\n            one["age"], one["updated_day"] = 0, today'),
    ('H. An update after the snapshot is accepted',
     '        elif today is not None and updated > today:',
     '        elif False:'),
    ('I. An update before the item was created is accepted',
     '        elif created is not None and created > updated:',
     '        elif False:'),
    ('J. A title that says blocked makes an item blocked (criterion 3)',
     '    has_blocker = lambda i: info[i]["blocked_by"] is not None and bool(',
     '    has_blocker = lambda i: "BLOCKED" in info[i]["title"] or info[i]["blocked_by"] is not None and bool('),
    ('K. A blank blocked_by is read as none (criterion 6)',
     '            if found is None:\n                gap(identity, field, "it is blank. That is not the same as none", unsaid)',
     '            if found is None:\n                one[field] = []'),
    ('L. A blocker that is not in the snapshot drops out of the blocked list',
     'bool(info[i]["blocked_by"] or info[i]["unknown"]["blocked_by"])',
     'bool(info[i]["blocked_by"])'),
    ('M. A blank assignee is counted as a person (criterion 6)',
     '        if row["assignee"] is None:\n            gap(identity, "assignee", "it is blank. That is not the same as being recorded as unassigned", "work in progress for each person")',
     '        if row["assignee"] is None:\n            one["assigned"], one["assignee"] = True, ""'),
    ("N. Unassigned is treated as a person's name",
     '        elif row["assignee"].lower() == "unassigned":',
     '        elif False:'),
    ('O. A word such as TBD where a name belongs is counted as a person',
     '        elif row["assignee"].lower() in NOT_A_NAME:',
     '        elif False:'),
    ('P. Items not in progress count toward work in progress (criterion 4)',
     '    for i in by_status["in_progress"]:\n        if info[i]["assigned"]:',
     '    for i in order:\n        if info[i]["assigned"]:'),
    ('Q. Waiting on a done item is a wait (criterion 5)',
     '                elif info[y]["status"] != "done":\n                    waits.setdefault',
     '                else:\n                    waits.setdefault'),
    ('R. A done item still waits (criterion 5)',
     '        if info[x]["status"] == "done":\n            continue\n        for field in ("blocked_by", "depends_on"):',
     '        for field in ("blocked_by", "depends_on"):'),
    ('S. An unassigned item waited on is not a risk (criterion 5)',
     '            if info[y]["assigned"] is False:\n                why.append("D2:',
     '            if False:\n                why.append("D2:'),
    ('T. A blank assignee on the item waited on is called unassigned',
     '            if info[y]["assigned"] is False:\n                why.append("D2:',
     '            if not info[y]["assigned"]:\n                why.append("D2:'),
    ('U. A wait on an item whose assignee is blank is filed under "none of D1 to D4 holds"',
     '            elif info[y]["assigned"] is None:\n                unknown.append(',
     '            elif False:\n                unknown.append('),
    ('V. An aging item waited on is not a risk (criterion 5)',
     '            if is_aging(y):\n                why.append("D3:',
     '            if False:\n                why.append("D3:'),
    ('W. A wait on an item whose update date is blank is filed under "none of D1 to D4 holds"',
     '            elif info[y]["status"] == "in_progress" and (not can_age or info[y]["age"] is None):',
     '            elif False:'),
    ('X. An item waited on that is itself waiting is not a risk (criterion 5)',
     '            if waits.get(y):\n                why.append("D4:',
     '            if False:\n                why.append("D4:'),
    ('Y. A chain of three is not reported',
     'if len(c) >= 3})',
     'if len(c) >= 4})'),
    ('Z. Two items that wait on each other are not reported',
     '            if len(group) > 1:\n                found.append(sorted(group))',
     '            if len(group) > 2:\n                found.append(sorted(group))'),
    ('AA. A wait into a loop is reported as a chain',
     '            if y in path or y in in_loop:',
     '            if y in path:'),
    ('AB. An item two others wait on is not reported',
     'if len(xs) >= 2}',
     'if len(xs) >= 3}'),
    ('AC. Two rows with one identifier: the last is used',
     '        if seen[row["id"]] > 1:',
     '        if False:'),
    ('AD. A row with the wrong number of cells is dropped silently',
     '            trouble.append(("row %d of the table" % number, "the row", "it has %d cells and the table has %d columns. Its first cell is \\"%s\\"" % (len(cells), len(COLUMNS), safe(cells[0]))))\n',
     ''),
    ('AE. A blank line inside the table drops every row after it',
     '    lines = [l for l in tables[0].split("\\n") if l.strip()]',
     '    lines = [l for l in tables[0].strip().split("\\n\\n")[0].split("\\n") if l.strip()]'),
    ('AF. A line of prose inside the table is dropped silently',
     '    for line in stray:\n        trouble.append(',
     '    for line in []:\n        trouble.append('),
    ('AG. A table with no line of dashes: its first row is taken for that line and lost',
     '    if len(lines) < 2 or not re.match(r"^\\|(\\s*:?-+:?\\s*\\|)+$", lines[1]):',
     '    if False:'),
    ('AH. A threshold or limit that cannot be used is reported as "none is set", with no gap',
     '        if not re.match(r"^\\d+$", value):',
     '        if not re.match(r"^\\d+$", value):\n            return None, "none is set: the snapshot records no `%s`" % name\n        if False:'),
    ('AI. A header line given twice: the first value is used',
     '            if name in header or name in unusable:',
     '            if name in header:\n                pass\n            elif False:'),
    ('AJ. Header lines are read from the whole file and not from the section headed The sprint',
     'sprint[0], re.M):',
     'text, re.M):'),
    ("AK. The computer's clock is used and not the snapshot's date (criterion 7)",
     '    today = day_of(header.get("snapshot_date"))',
     '    today = datetime.date.today()'),
    ('AL. A date that is not a date is accepted',
     '    except ValueError:\n        return None\n\n\ndef dated',
     '    except ValueError:\n        return datetime.date(2026, 11, 17)\n\n\ndef dated'),
    ('AM. The checksum is of the text after its line endings are changed, and not of the bytes of the file',
     '    report = render(model, hashlib.sha256(raw).hexdigest(), previous)',
     '    report = render(model, hashlib.sha256(raw.decode("utf-8").replace("\\r\\n", "\\n").encode("utf-8")).hexdigest(), previous)'),
    ('AN. Only Sundays are counted as weekend days',
     '.weekday() >= 5)',
     '.weekday() >= 6)'),
    ('AO. An item that is done is listed as blocked',
     'info[i]["status"] in ("todo", "in_progress")]\n    blocked_unknown',
     'info[i]["status"] is not None]\n    blocked_unknown'),
    ('AP. An item that names itself in blocked_by is taken as not blocked, with no gap',
     '            elif identity in found:\n                gap(identity, field, "it names the item itself", unsaid)',
     '            elif identity in found:\n                one[field] = []'),
    ('AQ. A changed title is reported as a change',
     '        for field in ("blocked_by", "depends_on"):\n            a = None if was[field] is None',
     '        if was["title"] != cur["title"]:\n            say("TITLE: `%s` has another title." % i)\n        for field in ("blocked_by", "depends_on"):\n            a = None if was[field] is None'),
    ('AR. A removed item is not reported',
     '    for i in sorted(set(was_info) - set(info)):',
     '    for i in []:'),
    ('AS. A changed depends_on is not reported',
     '        for field in ("blocked_by", "depends_on"):\n            a = None if was[field] is None',
     '        for field in ("blocked_by",):\n            a = None if was[field] is None'),
    ('AT. A quote mark in a title is printed as it is',
     '(\'"\', "\'"), ("|", "/")',
     '("|", "/")'),
    ('AU. Any cell that says "Made up" makes the report call the snapshot made up',
     'if "**Made up.**" in model["front"] else',
     'if "**Made up.**" in model["front"] + "".join(one["title"] for one in info.values()) else'),
    ('AV. A threshold that changed between the two snapshots is not reported',
     '    if before["threshold_said"] != now["threshold_said"]:',
     '    if False:'),
    ('AW. The check lets a wrong count through',
     '            if len(named) != int(got.group(2)):',
     '            if False:'),
    ('AX. The check lets an item be listed under the wrong status',
     '        if line_ids("1", start) != sorted(model["by_status"][status]):',
     '        if False:'),
    ('AY. The check lets an item be left out of section 1',
     '    if seen != sorted(info):',
     '    if False:'),
    ('AZ. The check lets wrong totals through',
     '    if not totals or [int(n) for n in totals.groups()] != real:',
     '    if False:'),
    ('BA. The check lets a wrong aging list through',
     '        if line_ids("2", "- Aging (") != sorted(model["aging"]) or line_ids("2", "- In progress and not aging (") != fresh:',
     '        if line_ids("2", "- In progress and not aging (") != fresh:'),
    ('BB. The check lets a wrong list of what is not aging through',
     '        if line_ids("2", "- Aging (") != sorted(model["aging"]) or line_ids("2", "- In progress and not aging (") != fresh:',
     '        if line_ids("2", "- Aging (") != sorted(model["aging"]):'),
    ('BC. The check lets a wrong number of days through',
     'int(days) != info[identity]["age"] or info[identity]["updated"] != when',
     'info[identity]["updated"] != when'),
    ('BD. The check lets a wrong update date through',
     'int(days) != info[identity]["age"] or info[identity]["updated"] != when',
     'int(days) != info[identity]["age"]'),
    ('BE. The check lets a wrong blocked list through',
     '    if line_ids("3", "- Recorded as blocked, and not done (") != sorted(i for i, _ in model["blocked"]):',
     '    if False:'),
    ('BF. The check lets a wrong blocker through',
     '        if real is None or said != ", ".join(real):',
     '        if False:'),
    ('BG. The check lets work be counted for the wrong person',
     '    if counted != {safe(p): sorted(v) for p, v in model["people"].items()}:',
     '    if False:'),
    ('BH. The check lets a count be set wrongly beside the limit',
     '            if "The recorded limit is %d: %s." % (model["limit"], want) not in m.group(4):',
     '            if False:'),
    ('BI. The check lets a risk be taken out',
     '    if pairs != sorted((r["x"], r["y"]) for r in model["risks"]):',
     '    if False:'),
    ('BJ. The check lets a risk go without its reason',
     '        if not re.search(r"\\bD[1-4]: ", line):',
     '        if False:'),
    ('BK. The check lets a gap be taken out',
     '        if "- [GAP] `%s`, field `%s`:" % (g["what"], g["field"]) not in sections.get("6", ""):',
     '        if False:'),
    ('BL. The check lets a report of another snapshot through',
     '    if "sha256 is `%s`" % hashlib.sha256(raw).hexdigest() not in report.split("## How to read this")[0]:',
     '    if False:'),
    ('BM. The check lets a report compared with another previous snapshot through',
     '    if previous_path and "sha256 is `%s`" % hashlib.sha256(read_bytes(previous_path)).hexdigest() not in sections.get("7", ""):',
     '    if False:'),
    ('BN. The check lets a judgement of a person through',
     '        if re.search(r"(?<![a-z])%s" % re.escape(word), own_words.lower()):',
     '        if False:'),
    ('BO. The check reads titles for judging words and identifiers',
     '    own_words = re.sub(r\'"[^"\\n]*"\', "", report)',
     '    own_words = report'),
    ('BP. The check lets an item that is not in the snapshot be named',
     '        if identity not in known:',
     '        if False:'),
    ('BQ. The check lets a second section with a number already used through',
     '    if len({n for n, _ in found}) != len(found):',
     '    if False:'),
    ('BR. A count for a name says "Aging: none" and not which items cannot be told',
     '        unsure = [i for i in mine if info[i]["blocked_by"] is None or info[i]["age"] is None or not model["can_age"]]',
     '        unsure = []'),
    ('BS. A wait on an item whose own links cannot be assessed is filed under "none of D1 to D4 holds"',
     '            elif own_links_unsure(y):',
     '            elif False:'),
    ('BT. A header line with a name the report does not use is read, and printed',
     '            if name not in HEADER:\n                continue\n',
     ''),
    ('BU. Two sections headed The sprint: the first is read',
     '    if len(sprint) != 1:',
     '    if not sprint:'),
    ('BV. An item whose status cannot be used is listed as blocked and not done',
     'info[i]["status"] in ("todo", "in_progress")]\n    blocked_unknown',
     'info[i]["status"] != "done"]\n    blocked_unknown'),
    ('BW. A threshold that was not set is said to have been unusable',
     '"not usable" if name in header or name in unusable else "not set"',
     '"not usable"'),
    ('BX. An item whose row cannot be used is said not to be in the snapshot',
     '"whose row cannot be used" if other in spoiled else "which is not in the snapshot"',
     '"which is not in the snapshot"'),
    ('BY. An item whose row cannot be used is reported as removed',
     'if i in now["spoiled"] else "REMOVED',
     'if False else "REMOVED'),
    ('BZ. A chain that a loop member waits on is not reported',
     'for w in waits if w not in in_loop)]',
     'for w in waits)]'),
    ('CA. A created date after the snapshot is accepted',
     '        if created is not None and today is not None and created > today:',
     '        if False:'),
    ('CB. Curly quotation marks in a title are printed as they are',
     '    out = QUOTES.sub("\'", UNPRINTABLE.sub(" ", str(text)))',
     '    out = UNPRINTABLE.sub(" ", str(text))'),
    ('CC. A previous snapshot dated later is not remarked on',
     '    if before["today"] and now["today"] and before["today"] > now["today"]:',
     '    if False:'),
    ('CD. With no threshold, the days are not shown',
     '    elif threshold is None:\n        out += ["Nothing is called aging: no aging threshold can be used. The days are still given.", "",',
     '    elif threshold is None:\n        fresh = []\n        out += ["Nothing is called aging: no aging threshold can be used. The days are still given.", "",'),
    ('CE. The check fails a correct report whose previous snapshot names an item in neither',
     '    for m in (model, before) if before else (model,):',
     '    for m in (model,):'),
    ('CF. The check lets a wrong number of waits or of risks through',
     '    if "- Waits in all: %d, on %d different items:" % (total, len(model["waited_on"])) not in sections.get("5", "") or "- Waits that are a risk (%d):" % len(model["risks"]) not in sections.get("5", ""):',
     '    if False:'),
    ('CG. The check lets a threshold changed at the top of the report through',
     '"- Aging threshold: %d days," % model["threshold"] not in report.split("## How to read this")[0] or ',
     ''),
]

def run_tests():
    done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=SKILL,
                          capture_output=True, text=True)
    failed = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\w+) \((?:test_health\.)?(\w+)", done.stderr, re.M)))
    return done.stderr.strip().splitlines()[-1], ["%s.%s" % (group, name) for name, group in failed]


def main():
    with open(TARGET, encoding="utf-8") as f:
        good = f.read()
    out = ["Do the tests notice a broken report generator? scrum-sprint-health, attempt scrum-attempt-002",
           "Recorded by scripts/planted_bugs.py.", "",
           "Each bug below was put into participant/skills/scrum-sprint-health/health.py, every test was run, and the",
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
    out += ["After the last bug was taken out: health.py is %s it was at the start. %s"
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
