#!/usr/bin/env python3
"""Records logs/regeneration.txt for the quest scrum-standup-digest. It contacts nothing.

    python3 participant/evidence/scrum-standup-digest/scrum-attempt-001/scripts/record_evidence.py

It generates the digest twice from unchanged context, into two scratch folders, SCRATCH/first and SCRATCH/second, and
compares every byte. Then it checks the handed-in digest against the context, criterion by criterion. The scratch
folders are deleted at the end. The handed-in files and the context are not changed, and it checks that.
"""
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
SKILL = os.path.join(REPO, "participant", "skills", "scrum-standup-digest")
sys.path.insert(0, SKILL)
import digest as dg  # noqa: E402

SCRUM = os.path.join(REPO, "participant", "context", "scrum")
CONTEXT = os.path.join(SCRUM, "sprint", "2026-11-24")
MONDAY = os.path.join(SCRUM, "sprint", "2026-11-23")
PREVIOUS = os.path.join(SCRUM, "archive", "2026-11-23", "digest-state.json")
AS_OF = "2026-11-24T09:00:00Z"
NAMES = ("standup-digest.md", "standup-gaps.md", "digest-state.json")
LOGS = os.path.join(HERE, "..", "logs")


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def tree(folder):
    out = {}
    for root, _, files in os.walk(folder):
        for name in files:
            path = os.path.join(root, name)
            out[os.path.relpath(path, REPO)] = hashlib.sha256(open(path, "rb").read()).hexdigest()
    return out


class Log:
    def __init__(self):
        self.lines = ["The regeneration record. scrum-standup-digest, attempt scrum-attempt-001",
                      "Recorded by scripts/record_evidence.py. Nothing was sent anywhere. No source system was read: the context is made up.",
                      "Paths are from the repository's top folder. SCRATCH is a temporary folder, deleted at the end."]
        self.failed, self.count = [], 0

    def out(self, *lines):
        self.lines.extend(lines or [""])

    def part(self, title, *lines):
        self.lines += ["", "=" * 78, title, *lines]

    def check(self, label, ok):
        self.count += 1
        self.lines.append("  %s %s" % ("ok  " if ok else "FAIL", label))
        if not ok:
            self.failed.append(label)


def section(text, number):
    return dict(re.findall(r"^## (\d+)\. [^\n]*\n(.*?)(?=^## |\Z)", text, re.S | re.M)).get(str(number), "")


def main():
    log = Log()
    scratch = tempfile.mkdtemp(prefix="gtq-digest-")
    before = tree(os.path.join(SCRUM))
    handed = {name: dg.read(os.path.join(SCRUM, name)) for name in NAMES}
    command = ["participant/skills/scrum-standup-digest/digest.py", "generate", "--context", "participant/context/scrum/sprint/2026-11-24", "--as-of", AS_OF,
               "--previous", "participant/context/scrum/archive/2026-11-23/digest-state.json"]

    log.part("PART 1. The digest generated twice from unchanged context (criterion 10)")
    runs = []
    for which in ("first", "second"):
        out = os.path.join(scratch, which)
        done = subprocess.run([sys.executable] + command + ["--out", out], cwd=REPO, capture_output=True, text=True)
        log.out("$ python3 %s --out SCRATCH/%s" % (" ".join(command), which), *("  " + line for line in done.stdout.rstrip().splitlines()), "  exit code %d" % done.returncode, "")
        runs.append({name: open(os.path.join(out, name), "rb").read() for name in NAMES})
        if which == "first":
            time.sleep(2)   # so that the two runs are at different times by the computer's clock
    log.out("The two runs were started 2 seconds apart. The computer's clock is not an input: the time the digest is for is given with --as-of.", "")
    for name in NAMES:
        a, b = runs[0][name], runs[1][name]
        log.out("  %-18s first: %d bytes, sha256 %s" % (name, len(a), hashlib.sha256(a).hexdigest()), "  %-18s second: %d bytes, sha256 %s" % ("", len(b), hashlib.sha256(b).hexdigest()))
        log.check("%s is byte for byte the same in both runs" % name, a == b and len(a) > 0)
    log.check("the handed-in digest, gap report and state are byte for byte what these runs wrote", all(handed[name].encode("utf-8") == runs[0][name] for name in NAMES))
    log.check("the context was not changed by generating: every file under participant/context/scrum has the checksum it had before", tree(SCRUM) == before)
    other = os.path.join(scratch, "later")
    dg.generate(CONTEXT, "2026-11-24T09:30:00Z", PREVIOUS, other)
    log.out("", "A contrast: the same context with --as-of 2026-11-24T09:30:00Z, half an hour later.")
    log.check("a different --as-of gives a different digest, in which the Jira records are 2 h 0 min old and not 1 h 30 min. So the time the digest is for is an input",
              dg.read(os.path.join(other, "standup-digest.md")) != handed["standup-digest.md"] and "(2 h 0 min before this digest)" in dg.read(os.path.join(other, "standup-digest.md")))
    source = dg.read(os.path.join(SKILL, "digest.py"))
    log.check("digest.py never asks for the time: it has no datetime.now, utcnow, time.time or today()", not any(call in source for call in ("datetime.now", "utcnow", "time.time", "today()")))

    log.part("PART 2. Local context only (criterion 1)")
    model, written = dg.generate(CONTEXT, AS_OF, PREVIOUS, os.path.join(scratch, "in-process"))
    imports = sorted(set(re.findall(r"^(?:import|from) (\w+)", source, re.M)))
    log.out("Modules digest.py imports: %s." % ", ".join(imports))
    log.check("digest.py imports only these seven, none of which opens a network connection: argparse, datetime, hashlib, json, os, re, sys", imports == ["argparse", "datetime", "hashlib", "json", "os", "re", "sys"])
    log.check("it uses nothing of os that starts a program, and loads no module by name at run time: no os.system, popen, exec, spawn or fork, no __import__ and no importlib",
              not re.search(r"os\.(system|popen|exec\w*|spawn\w*|fork|startfile)|__import__|importlib|eval\(|exec\(", source))
    opens = re.findall(r"\bopen\(([^,)]*)", source)
    log.out("Every place digest.py opens a file: %s." % "; ".join(sorted(set(opens))))
    log.check("it opens files in two places only, its own read() and write(), and those are given paths under --context, --previous and --out", sorted(set(opens)) == ["os.path.join(args.out", "path"])
    real, opened = socket.socket, []
    socket.socket = lambda *a, **k: opened.append(1) or (_ for _ in ()).throw(OSError("no network in this run"))
    try:
        again = dg.generate(CONTEXT, AS_OF, PREVIOUS, os.path.join(scratch, "no-network"))[1]
    finally:
        socket.socket = real
    log.out("The generator was also run with every attempt to open a network socket made to fail. Since it imports nothing that could try, this run is a formality, and is recorded as one.")
    log.check("that run wrote the same three files byte for byte, and no socket was asked for", not opened and all(again[name] == handed[name] for name in NAMES))
    log.check("every record it read says sync_source is \"made-up\", and the digest says so on its third line. That line repeats what the records say of themselves",
              all(e["p"].get("sync_source") == "made-up" for e in model["items"].values()) and handed["standup-digest.md"].split("\n")[2] == "**Built from made-up context.**")

    digest, gaps = handed["standup-digest.md"], handed["standup-gaps.md"]
    items = model["items"]
    log.part("PART 3. Citations, retrieval times, the window and the runs (criteria 2, 3 and 11)")
    done = subprocess.run([sys.executable, os.path.join(SKILL, "digest.py"), "check", "--context", CONTEXT, "--as-of", AS_OF, "--out", SCRUM], capture_output=True, text=True)
    log.out("$ python3 participant/skills/scrum-standup-digest/digest.py check --context participant/context/scrum/sprint/2026-11-24 --as-of %s --out participant/context/scrum" % AS_OF,
            *("  " + line for line in done.stdout.rstrip().splitlines()), "  exit code %d" % done.returncode, "")
    log.check("the check reports no problem. It reads the finished files back and compares them with the records. It shares the reading of the records with the generator", done.returncode == 0)
    lines = [l for l in digest.split("\n") if l.startswith("- [")]
    cited = [(l, re.findall(r"`((?:jira|github|trello):[A-Za-z0-9_.-]+)`, retrieved (\S+) \(([^)]*) before this digest\), run `([^`]+)`", l)) for l in lines]
    plain = [l for l, c in cited if not c]
    log.out("Statement lines in the digest: %d. With at least one citation of the form identity, retrieval time, age, run: %d." % (len(lines), len(lines) - len(plain)),
            "Lines with none, and why each needs none:", *("  " + l[:150] for l in plain))
    log.check("criterion 2: every statement line cites an item by identity, retrieval time, age and run, except %d: the counts, the summary of the inferences, and the removed item, which has no record to cite" % len(plain),
              all("· COUNT]" in l or "· REMOVED]" in l or l.startswith("- [INFERENCE I4]") for l in plain) and len(lines) - len(plain) > 20)
    in_progress = [l for l in section(digest, 2).split("\n") if l.startswith("- [OBSERVED]")]
    counted = re.search(r"Items with a fresh record whose status the source states: (\d+)\. In progress: (\d+)\. Open: (\d+)\. Done: (\d+)\. Closed without being done: (\d+)\.", section(digest, 6))
    five = [l for l in section(digest, 5).split("\n") if l.startswith("- [OBSERVED]")]
    recount = [len(in_progress) + len(five), len(in_progress), sum(l.startswith("- [OBSERVED] Open") for l in five), sum(l.startswith("- [OBSERVED] Done") for l in five), sum(l.startswith("- [OBSERVED] Closed") for l in five)]
    log.out("The counts in section 6, and the same counted here from the cited lines of sections 2 and 5: %s and %s." % (counted.groups() if counted else None, tuple(str(n) for n in recount)))
    log.check("the counts in section 6 are the numbers of cited lines above them, counted again here", bool(counted) and [int(n) for n in counted.groups()] == recount)
    pairs = [(i, at, run) for _, c in cited for i, at, _, run in c]
    log.check("criterion 3: every citation gives a retrieval time, and it is the time in that item's own record: %d of %d" % (sum(1 for i, at, _ in pairs if items[i]["p"]["retrieved_at"] == at), len(pairs)),
              bool(pairs) and all(i in items and items[i]["p"]["retrieved_at"] == at and items[i]["p"]["sync_run"] == run for i, at, run in pairs))
    log.check("criterion 11: the digest states its window, from the previous digest's time to this one's", "- Window: from 2026-11-23T09:00:00Z, the time the previous digest was for, to 2026-11-24T09:00:00Z" in digest)
    log.check("criterion 11: it lists every synchronization run in sync-runs.md, the failed one too, each with the time the run gives",
              len(model["runs"]) == 4 and all(re.search(r"^\| `%s` \| %s \| %s \| %s \|" % (re.escape(r["run"]), r["system"], r["result"], r["retrieved_at"]), digest, re.M) for r in model["runs"]))
    log.check("it also lists a run that a record names and sync-runs.md does not, and says records naming it are not asserted", "| `github-read-assigned:2026-11-23T07:35:00Z` | | | | | 0 | | NOT IN sync-runs.md." in digest)

    log.part("PART 4. Observed, inference, stale and gaps kept apart (criteria 4, 5 and 6)")
    tags = {}
    for l in lines:
        tags.setdefault(re.match(r"- \[([A-Z ]+?)(?: ·| I\d|\])", l).group(1), []).append(l)
    log.out("Statement lines by their label: %s." % ", ".join("%s %d" % (tag, len(found)) for tag, found in sorted(tags.items())))
    multi = [l for l in lines if len(set(re.findall(r"`((?:jira|github|trello):[A-Za-z0-9_.-]+)`, retrieved", l))) > 1]
    log.out("Statement lines that cite more than one record, which is what makes a conclusion and not an observation: %d. All of them are in section 7: %s." % (len(multi), all(l in section(digest, 7) for l in multi)))
    log.check("criterion 4: every line labelled INFERENCE is in section 7, section 7 holds no other statement line, and no line outside it rests on more than one record",
              digest.count("[INFERENCE") == section(digest, 7).count("[INFERENCE") > 0 and all(l.startswith("- [INFERENCE I") for l in section(digest, 7).split("\n") if l.startswith("- [")) and all(l in section(digest, 7) for l in multi))
    log.check("criterion 4: every inference but the count cites, after the words \"Rests on\", a record that exists, with that record's retrieval time",
              all(re.findall(r"`([^`]+)`, retrieved (\S+) ", l.split("Rests on: ")[1]) and all(i in items and items[i]["p"]["retrieved_at"] == at for i, at in re.findall(r"`([^`]+)`, retrieved (\S+) ", l.split("Rests on: ")[1])) for l in tags["INFERENCE"] if "I4" not in l))
    stale = sorted(model["stale"])
    log.out("Stale records, older than %d hours at %s: %s." % (dg.STALE_AFTER_HOURS, AS_OF, ", ".join(stale)))
    current = "".join(section(digest, n) for n in (1, 2, 3, 4, 5, 6, 7, 8))
    log.check("criterion 5: no stale record is cited in any section that states something as current", stale and not any("`%s`, retrieved" % i in current for i in stale))
    log.check("criterion 5: each stale record is under LAST KNOWN in the digest and under STALE in the gap report, with its age and the limit",
              all("`%s`, retrieved" % i in section(digest, 9) and re.search(r"^- \[STALE\] `%s`\. Reason: retrieved \S+, which is .* before this digest\. The limit is 24 hours" % re.escape(i), gaps, re.M) for i in stale))
    skill = dg.read(os.path.join(SKILL, "SKILL.md"))
    log.check("criteria 5 and 8: the two thresholds in the digest, in the skill and in the code are the same numbers, %d hours and %d days. The boundaries themselves are tried in the tests: logs/tests.txt" % (dg.STALE_AFTER_HOURS, dg.AGING_AFTER_DAYS),
              "more than %d hours" % dg.STALE_AFTER_HOURS in digest and "**%d hours**" % dg.STALE_AFTER_HOURS in skill and "for %d whole days or more" % dg.AGING_AFTER_DAYS in digest and "**%d days**" % dg.AGING_AFTER_DAYS in skill)
    for what in ("github:I_kwFXsc0005", "items/github-I_kwFXsc0006.md", "jira:53099"):
        log.out("  %s: in the gap report as MISSING %s; in the digest as a statement: %s" % (what, "yes" if "[MISSING] `%s`" % what in gaps else "NO", "YES" if "`%s`, retrieved" % what in digest else "no"))
    log.check("criterion 6: the item a run retrieved with no record, the record that cannot be read, and the blocker with no record are each in the gap report with a reason, and none is cited as a statement",
              all("[MISSING] `%s`. Reason: " % w in gaps for w in ("github:I_kwFXsc0005", "items/github-I_kwFXsc0006.md", "jira:53099")) and "I_kwFXsc0005" not in digest and "I_kwFXsc0006" not in digest and "`jira:53099`, retrieved" not in digest)
    log.check("criterion 6: the one fresh item whose status the source does not state is in section 8, apart, and in the gap report, and not among the observed statuses", "jira:53014" in section(digest, 8) and "jira:53014" not in section(digest, 2) and "[UNSUPPORTED] `jira:53014`" in gaps)
    log.check("the number of gaps the digest says the report holds is the number of entries in it: %d" % len(model["gaps"]), "It has %d entries" % len(model["gaps"]) in digest and gaps.count("\n- [") == len(model["gaps"]))

    log.part("PART 5. Blocked, aging and changes (criteria 7, 8 and 9)")
    log.out("jira:53005 is titled \"%s\". Its record says blocked: %s." % (items["jira:53005"]["c"]["title"], items["jira:53005"]["c"]["blocked"]))
    log.check("criterion 7: the item whose TITLE begins \"BLOCKED:\" is not in the blocked section. Its record says it is not blocked", "jira:53005" not in section(digest, 3) and "jira:53005" in section(digest, 2))
    shown = re.findall(r"^- \[OBSERVED · BLOCKED\][^\n]*`((?:jira|github|trello):[^`]+)`, retrieved", section(digest, 3), re.M)
    real = sorted(i for i in model["fresh"] if items[i]["c"]["blocked"] == "yes" or any(k == "blocked_by" for k, _, _ in dg.links_of(i, items[i], model["data"]["notes"], model["data"]["note_files"])))
    log.out("Shown as blocked: %s." % ", ".join(sorted(set(shown))), "Blocked by a recorded field, link or note, worked out here from the records: %s." % ", ".join(real))
    log.check("criterion 7: the items shown as blocked are exactly the fresh items whose record's blocked field says yes, or that have a saved link or a note line saying blocked_by. Worked out here from the records", sorted(set(shown)) == real and len(real) == 4)
    log.check("criterion 7: a note written as prose, saying an item is blocked on a named person, records nothing: that item is not shown as blocked and the note's words are nowhere", "jira:53013" not in section(digest, 3) and "Okafor" not in digest + gaps and "Thursday" not in digest + gaps)
    log.out("", *[l[:170] for l in section(digest, 4).split("\n") if l.startswith("- [")])
    log.check("criterion 8: the two items in progress whose source had not changed for %d days or more when retrieved are listed as aging, each with its number of days: 7 and 5" % dg.AGING_AFTER_DAYS, "for 7 days" in section(digest, 4) and "for 5 days" in section(digest, 4) and section(digest, 4).count("[OBSERVED · AGING]") == 2)
    log.check("criterion 8: the item unchanged for 3 days when retrieved is not listed", "jira:53013" not in section(digest, 4))
    log.out("", *[l[:170] for l in section(digest, 1).split("\n") if l.startswith("- [")])
    log.check("criterion 9: the digest's own lines report one item added, one removed and one status change, each by its identity",
              re.findall(r"^- \[OBSERVED · CHANGE · (\w+)\][^\n]*?`((?:jira|github|trello):[^`]+)`", section(digest, 1), re.M) == [("ADDED", "jira:53008"), ("REMOVED", "jira:53009"), ("STATUS", "jira:53004")])
    log.check("criterion 9: the removed item is not said to be done. The gap report says why it went is not recorded", "Why is not recorded" in section(digest, 1) and "[UNSUPPORTED] `jira:53009`" in gaps)
    state = json.loads(handed["digest-state.json"])
    log.check("criterion 9: the state kept for the next digest holds identities and no titles", "jira:53001" in state["items"] and not any(e["c"]["title"] in handed["digest-state.json"] for e in items.values()))

    log.part("PART 6. No person, and nothing that should not be shared (criterion 12, and the safety rules)")
    both = digest + gaps
    words = ("assignee", "assigned to ", "is working", "is busy", "behind", "on leave", "velocity", "productiv", "available today")
    log.check("criterion 12: neither file uses any of these words: %s. A list of words is a weak test: it would miss a statement about a person worded another way" % ", ".join(w.strip() for w in words),
              not any(w in both.lower() for w in words))
    log.check("criterion 12: the generator never reads who an item is assigned to. The only field about assignment it reads is assigned_to_me, for --scope", not re.search(r"(\[|get\()\"assignee", source) and len(re.findall(r"get\(\"assigned_to_me\"\)", source)) >= 2)
    log.check("criterion 12: the digest says in its own words that it makes no statement about any person, and the skill documents the limit", "**This digest makes no statement about any person**" in digest and "**Nothing about a person.**" in dg.read(os.path.join(SKILL, "SKILL.md")))
    log.out("jira:53010's title in the record holds a made-up customer number, name and email address. In the digest it reads:", *["  " + l[:140] for l in digest.split("\n") if "`jira:53010`" in l])
    log.check("the made-up name, email address and customer number in a title are not in the digest or the gap report", not any(s in both for s in ("Whitlock", "CUST-20417", "@")) and "Refund [customer number] for [name] ([email address])" in digest)
    uses = sorted(set(re.findall(r"\[\"title\"\]|title_of\(|safe\([^)]*title", source)))
    log.out("Every place digest.py touches a title: %s. Each prints it, through safe(). No condition in the program reads one." % ", ".join(uses))
    log.check("no branch of the generator reads a title: the word title appears in no if, elif, while or comparison in digest.py", not re.search(r"^\s*(if|elif|while)\b[^\n]*title", source, re.M))
    log.check("the item whose title is worded as an instruction is reported as open, as its record says", any("`jira:53006`" in l and l.startswith("- [OBSERVED] Open") for l in section(digest, 5).split("\n")))

    log.part("PART 7. That these checks can fail", "The handed-in digest is spoiled in memory, one thing at a time, written to SCRATCH, and the check is run on it.")

    def trial(label, expect, old, new, where="digest"):
        base = digest if where == "digest" else gaps
        found = old in base
        folder = os.path.join(scratch, "spoiled")
        os.makedirs(folder, exist_ok=True)
        dg.write(os.path.join(folder, "standup-digest.md"), base.replace(old, new, 1) if where == "digest" else digest)
        dg.write(os.path.join(folder, "standup-gaps.md"), base.replace(old, new, 1) if where == "gaps" else gaps)
        got = dg.check(CONTEXT, AS_OF, folder)
        log.out("Spoiled: %s" % label, *(["    THE TEXT TO SPOIL WAS NOT FOUND"] if not found else []), *("    PROBLEM: %s" % p for p in got[:2]))
        log.check("reported: \"%s\"" % expect, found and any(expect in p for p in got))

    stale_line = [l for l in digest.split("\n") if l.startswith("- [LAST KNOWN]") and "I_kwFXsc0004" in l][0]
    line_53001 = [l for l in digest.split("\n") if l.startswith("- [OBSERVED] In progress") and "`jira:53001`" in l][0]
    line_53013 = [l for l in digest.split("\n") if l.startswith("- [OBSERVED] In progress") and "`jira:53013`" in l][0]
    missing_line = [l for l in gaps.split("\n") if l.startswith("- [MISSING]")][0]
    trial("a confident sentence with no citation added to the observed lines", "cites no item with its retrieval time", "## 2. OBSERVED: in progress\n\n", "## 2. OBSERVED: in progress\n\n- [OBSERVED] Search work is progressing well.\n")
    trial("one citation's retrieval time changed by a minute", "and its record says", "`jira:53001`, retrieved 2026-11-24T07:30:00Z", "`jira:53001`, retrieved 2026-11-24T07:31:00Z")
    trial("one citation's age changed", "the age \"0 h 5 min\"", "(1 h 25 min before this digest)", "(0 h 5 min before this digest)")
    trial("a stale record's line moved up among the current ones", "as current, and its record is stale", "## 2. OBSERVED: in progress\n\n", "## 2. OBSERVED: in progress\n\n" + stale_line.replace("[LAST KNOWN]", "[OBSERVED]") + "\n")
    trial("an item in progress said to be done, with its citation left right", "says jira:53001 is", line_53001, line_53001.replace("In progress, stated", "Done, stated"))
    trial("a fresh item left out of the digest altogether", "has a fresh record and its status is in none of sections", line_53013 + "\n", "")
    trial("the number of days on an aging line changed", "is aging, and by its record it is not, or not by that number of days", "had not changed for 7 days", "had not changed for 9 days")
    trial("the item with BLOCKED in its title added to the blocked section", "is shown as blocked, and no recorded field, link or note says so", "- [OBSERVED · BLOCKING]",
          "- [OBSERVED · BLOCKED] Blocked; title, redacted: \"x\". `jira:53005`, retrieved 2026-11-24T07:30:00Z (1 h 30 min before this digest), run `jira-read-assigned:2026-11-24T07:30:00Z`.\n- [OBSERVED · BLOCKING]")
    trial("an inference moved out of the inference section", "An inference is outside section 7", "## 4. OBSERVED: aging\n\n", "## 4. OBSERVED: aging\n\n" + tags["INFERENCE"][0] + "\n")
    trial("a name from the redaction list put back", "which redaction.md lists", "[name]", "Dana Whitlock")
    trial("an item that has no record cited", "of which there is no local record", "`jira:53001`, retrieved", "`jira:59999`, retrieved")
    trial("the count of work in progress changed", "a count of work in progress that is not the number of lines", "Work in progress: 6.", "Work in progress: 5.")
    trial("an entry taken out of the gap report", "number of entries", missing_line + "\n", "", where="gaps")
    trial("a stale item taken out of the gap report", "is stale and is not in the gap report as stale", [l for l in gaps.split("\n") if l.startswith("- [STALE] `github:I_kwFXsc0004`")][0], "- [STALE] the whole of github. Reason: x. Not asserted: y.", where="gaps")
    log.out("What the check does not look at: whether a BLOCKING line, a CHANGE line or an INFERENCE line says what the records say, and the verdicts in the table of runs.",
            "Those are tried by the tests in logs/tests.txt, on the generator, and not by this check on the finished files.")

    shutil.rmtree(scratch, ignore_errors=True)
    log.part("AT THE END")
    log.check("the handed-in files and the whole of the context are byte for byte what they were at the start, and the scratch folder is gone", tree(SCRUM) == before and not os.path.exists(scratch))
    log.lines += ["", "RESULT: %s" % ("%d OF %d CHECKS FAILED." % (len(log.failed), log.count) if log.failed else "ALL CHECKS PASSED. %d checks." % log.count)]
    os.makedirs(LOGS, exist_ok=True)
    with open(os.path.join(LOGS, "regeneration.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(line.replace(scratch, "SCRATCH") for line in log.lines) + "\n")
    print("regeneration.txt: " + log.lines[-1])
    for label in log.failed:
        print("  FAILED: " + label)
    return 1 if log.failed else 0


if __name__ == "__main__":
    sys.exit(main())
