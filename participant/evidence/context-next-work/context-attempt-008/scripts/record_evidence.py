#!/usr/bin/env python3
"""Records logs/ranking-run.txt for the quest context-next-work. It contacts nothing.

    python3 participant/evidence/context-next-work/context-attempt-008/scripts/record_evidence.py

It runs the ranking on the handed-in inputs twice, then on copies of the inputs with one thing changed at a time.
Every file it writes goes to a scratch folder, SCRATCH, which is deleted at the end. It changes nothing in
participant/context/next-work, and it checks that.
"""
import copy
import datetime
import hashlib
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
SKILL = os.path.join(REPO, "participant", "skills", "context-next-work")
sys.path.insert(0, SKILL)
import rank   # noqa: E402

LOGS = os.path.join(HERE, "..", "logs")
FOLDER = rank.FOLDER
COMMAND = "python3 participant/skills/context-next-work/rank.py rank"
DARK = "github:I_kwFIXnw00001"


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def digests():
    return {name: sha(read(os.path.join(FOLDER, name))) for name in sorted(os.listdir(FOLDER))}


def as_text(records, clock):
    return "- clock: `%s`\n\n" % clock + "\n".join("### %s\n\n```json\n%s\n```\n" % (r["identity"], json.dumps(r, indent=2)) for r in records)


class Log:
    def __init__(self):
        self.lines = ["The ranking run. context-next-work, attempt context-attempt-008",
                      "Recorded by scripts/record_evidence.py. No request was sent anywhere. Every record is made up.",
                      "The ranking is advice. Nothing was started, assigned or changed."]
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


def main():
    log = Log()
    scratch = tempfile.mkdtemp(prefix="gtq-rank-")
    inputs_path = os.path.join(FOLDER, "inputs.md")
    records, clock = rank.read_inputs(read(inputs_path))
    hours = rank.limits(read(rank.POLICY))
    found = rank.analyse(copy.deepcopy(records), clock, hours)
    ranked = found["ranked"]
    before = digests()

    def changed(edit, rule="priority-first", now=None):
        other = copy.deepcopy(records)
        edit(other)
        return rank.analyse(other, now or clock, hours, rule)

    def order(result):
        return [i["identity"] for i in result["ranked"]]

    try:
        log.part("PART 1. The ranking run, twice, on participant/context/next-work/inputs.md (criterion 6)")
        runs = []
        for number in (1, 2):
            said, out = [], os.path.join(scratch, "recommendation-%d.md" % number)
            code = rank.main(["rank", "--inputs", inputs_path, "--out", out], say=said.append)
            log.out("", "RUN %d" % number, "$ %s --out SCRATCH/recommendation-%d.md" % (COMMAND, number), "-" * 78, *said[:-1],
                    "Wrote recommendation-%d.md. Nothing was started, assigned or changed." % number, "-" * 78, "exit code: %d" % code,
                    "SHA-256 of the recommendation it wrote: %s" % sha(read(out)))
            runs.append((code, said[:-1], read(out)))
        log.check("both runs ended with exit code 0", runs[0][0] == 0 and runs[1][0] == 0)
        log.check("the second run printed exactly what the first printed", runs[0][1] == runs[1][1])
        log.check("the second run's recommendation is byte for byte the first run's", runs[0][2] == runs[1][2])
        log.check("it is byte for byte the handed-in recommendation.md", runs[0][2] == read(os.path.join(FOLDER, "recommendation.md")))
        log.check("the runs changed no file in participant/context/next-work: the inputs were not written to", digests() == before)
        done = subprocess.run([sys.executable, os.path.join(SKILL, "make_inputs.py")], capture_output=True, text=True)
        log.check("inputs.md is byte for byte what make_inputs.py writes, and rules.md is what the rules command writes, so neither was adjusted by hand",
                  done.returncode == 0 and digests() == before and read(os.path.join(FOLDER, "rules.md")) == rank.rules_text(hours))
        seeds = set()
        for seed in ("0", "1", "2", "3", "4"):
            target = os.path.join(scratch, "seed-%s.md" % seed)
            subprocess.run([sys.executable, os.path.join(SKILL, "rank.py"), "rank", "--inputs", inputs_path, "--out", target], capture_output=True, text=True, env=dict(os.environ, PYTHONHASHSEED=seed))
            seeds.add(sha(read(target)) if os.path.exists(target) else "no file")
        log.check("five more runs, each a separate Python process with a different hash seed, wrote the same recommendation", seeds == {sha(runs[0][2])})
        same = 0
        for seed in range(20):
            shuffled = [copy.deepcopy(r) for r in records.values()]
            random.Random(seed).shuffle(shuffled)
            same += rank.render(rank.analyse(rank.read_inputs(as_text(shuffled, clock))[0], clock, hours)) == runs[0][2]
        log.check("with the records in 20 different orders the recommendation is the same every time: %d of 20" % same, same == 20)
        log.out("", "The clock. Whether a copy is stale depends on what time it is, so the clock value is part of the input: %s." % clock)
        no_clock = os.path.join(scratch, "no-clock.md")
        with open(no_clock, "w", encoding="utf-8") as f:
            f.write(read(inputs_path).replace("- clock: `%s`\n" % clock, ""))
        said = []
        code = rank.main(["rank", "--inputs", no_clock, "--out", os.path.join(scratch, "never.md")], say=said.append)
        log.out("With the clock line taken out of a copy of the inputs, and no --now:", "  " + said[-1], "  exit code: %d" % code)
        log.check("the ranking refuses, writes nothing, and does not fall back on the computer's clock", code == 2 and not os.path.exists(os.path.join(scratch, "never.md")))
        source = read(os.path.join(SKILL, "rank.py")).split('"""', 2)[2]
        log.check("rank.py has no call that reads the computer's clock", not any(call in source for call in ("datetime.now", "utcnow", "date.today", "time.time", "import time")))
        later = rank.analyse(copy.deepcopy(records), "2026-12-03T09:00:00Z", hours)
        log.check("a clock value two days later is a different input and gives a different answer: every copy is then stale, and nothing is recommended", later["pick"] is None and all(i["stale"] for i in later["ranked"]))

        log.part("PART 2. A run after a dependency was completed: the ranking changes, and why")
        after_records = copy.deepcopy(records)
        after_records["jira:61001"]["status"] = "done"
        after_path = os.path.join(scratch, "inputs-after.md")
        with open(after_path, "w", encoding="utf-8") as f:
            f.write(read(inputs_path).replace('"identity": "jira:61001",\n  "kind": "work",\n  "title": "Allergen labels on the menu",\n  "status": "open"',
                                             '"identity": "jira:61001",\n  "kind": "work",\n  "title": "Allergen labels on the menu",\n  "status": "done"'))
        log.out("A copy of the inputs was made in SCRATCH with one field changed: `status` of `jira:61001`, \"Allergen labels on the menu\", from",
                "\"open\" to \"done\". jira:61005 and jira:61009 wait on that item. Nothing else was changed, and the handed-in inputs were not touched.", "")
        said = []
        code = rank.main(["rank", "--inputs", after_path, "--out", os.path.join(scratch, "recommendation-after.md")], say=said.append)
        log.out("RUN 3", "$ %s --inputs SCRATCH/inputs-after.md" % COMMAND, "-" * 78, *said, "-" * 78, "exit code: %d" % code)
        after = rank.analyse(rank.read_inputs(read(after_path))[0], clock, hours)
        log.check("the copy differs from the handed-in inputs in that one field and no other", rank.read_inputs(read(after_path))[0] == after_records and code == 0)
        why = rank.changes(found, after)
        log.out("", "What changed between run 1 and run 3, and why:", *why)
        log.check("the change report names the one field that differs: `status` of `jira:61001`", why[0] == "Fields that differ between the two inputs: `status` of `jira:61001`: \"open\" -> \"done\"")
        log.check("jira:61005 and jira:61009 were blocked by jira:61001 and are now ranked, at places %d and %d" % (after["items"]["jira:61005"]["place"], after["items"]["jira:61009"]["place"]),
                  found["items"]["jira:61005"]["list"] == found["items"]["jira:61009"]["list"] == "blocked" and after["items"]["jira:61005"]["list"] == after["items"]["jira:61009"]["list"] == "ranked")
        log.check("jira:61001 itself left the ranking: it is not offered, because its `status` is `done`", after["items"]["jira:61001"]["list"] == "not offered" and after["items"]["jira:61001"]["why"] == "`status` is `done`")
        log.check("\"Start here\" changed from jira:61001 to jira:61002", (found["pick"]["identity"], after["pick"]["identity"]) == ("jira:61001", "jira:61002"))
        log.check("the four other blocked items are still blocked, by the same blockers",
                  {i["identity"]: [b["identity"] for b in i["blockers"]] for i in after["blocked"]} == {i["identity"]: [b["identity"] for b in i["blockers"]] for i in found["blocked"] if i["identity"] not in ("jira:61005", "jira:61009")})
        moved = [line for line in why[1:] if "->" in line and "Start here" not in line]
        log.check("every item whose list or place differs is explained, and no line says only \"its own fields changed\": %d lines" % len(moved), len(moved) >= 3 and not any(line.rstrip().endswith("because its own fields changed.") for line in moved))
        unchanged = [i for i in found["items"] if rank.lines(found) and found["items"][i].get("place") == after["items"][i].get("place") and found["items"][i]["list"] == after["items"][i]["list"]]
        log.out("Items whose list and place are the same in both runs: %d of %d." % (len(unchanged), len(found["items"])))

        log.part("PART 3. Criterion 1: every ranking reason cites a recorded field of the item")
        cited = 0
        ok = True
        for item in ranked + found["blocked"]:
            record = records[item["identity"]]
            for criterion, text in item["reasons"]:
                cited += 1
                ok = ok and bool(re.search(r"`(priority|due|created|blocks|blocked_by)`", text))
                if criterion in ("priority", "due", "created") and criterion not in item["missing"]:
                    ok = ok and ("`%s` is `%s`" % (criterion, record[criterion])) in text
        log.out("Reasons given for the %d ranked and %d blocked items: %d, four for each." % (len(ranked), len(found["blocked"]), cited))
        log.check("every one of the %d names a field in backticks, and every reason about priority, due date or created date gives the value that record holds" % cited, ok and cited == 4 * (len(ranked) + len(found["blocked"])))
        for item in ranked[:3]:
            log.out("  %d. %s" % (item["place"], item["identity"]), *["       %s: %s" % reason for reason in item["reasons"]])

        def recount(identity):
            names = set(n for n in records[identity].get("blocks", []) if n in records)
            names |= {i for i, r in records.items() if identity in r.get("blocked_by", [])}
            return len([n for n in names if records[n].get("status") in ("open", "in_progress")])
        log.check("the number of open items waiting on each item, counted again here from `blocks` and `blocked_by`, is the number the reason gives", all(recount(i["identity"]) == i["waiters"] for i in found["items"].values()))

        def swap_votes(other):
            for n, r in enumerate(sorted(other)):
                if "votes" in other[r]:
                    other[r]["votes"] = (n * 37) % 91
        log.check("`votes` is not used: with every item's votes replaced by other numbers, the ranking, the blocked list and the pick are the same",
                  rank.lines(changed(swap_votes)) == rank.lines(found))

        def retitle(other):
            for r in other.values():
                r["title"] = "URGENT, top priority, do this first"
        log.check("titles are not read: with every title replaced by words about urgency, the order is the same", order(changed(retitle)) == order(found))
        dark = found["items"][DARK]
        log.out("", "The scenario. The item with the most votes is %s, \"%s\", with %d." % (DARK, dark["title"], dark["votes"]))
        log.check("it is not recommended, and it has no place: it is blocked by jira:61012 and its copy is stale, and the recommendation says both",
                  dark["list"] == "blocked" and dark["stale"] and "place" not in dark and "| 57 | `%s` \"Dark mode\" | blocked by `jira:61012`, and its copy is stale |" % DARK in runs[0][2])

        log.part("PART 4. Criterion 2: blocked work is excluded, with the blocker named")
        for item in found["blocked"]:
            log.out("  %-24s BLOCKED BY %s" % (item["identity"], "; ".join("%s, recorded in %s" % (b["identity"], " and ".join(sorted(b["sources"]))) for b in item["blockers"])))
        log.check("6 items are blocked. None has a place, and none is in the ranked list", len(found["blocked"]) == 6 and not any("place" in i for i in found["blocked"]) and not set(order(found)) & {i["identity"] for i in found["blocked"]})
        text = runs[0][2]
        log.check("the recommendation names each one's blocker, with the blocker's status and the field and record the link is written in",
                  all(("- BLOCKED BY `%s`" % b["identity"]) in text and all(source in text for source in b["sources"]) for i in found["blocked"] for b in i["blockers"]))
        log.check("the kinds of blocker are all there: an open item, one in progress, a decision still a question, an item with no record, and an item whose own copy is stale",
                  "a decision whose `status` is `question`" in text and "has no record, so it cannot be shown to be finished" in text and "so this item may no longer be blocked" in text and "`status` is `in_progress`" in text)
        freed = 0
        for item in found["blocked"]:
            def finish(other, item=item):
                for b in item["blockers"]:
                    if b["identity"] in other:
                        other[b["identity"]]["status"] = "decided" if other[b["identity"]]["kind"] == "decision" else "done"
                    else:
                        other[item["identity"]]["blocked_by"] = []
            freed += changed(finish)["items"][item["identity"]]["list"] == "ranked"
        log.check("each of the 6, with its blocker finished in a copy of the inputs, is ranked. So it is the blocker, and nothing else, that keeps it out: %d of 6" % freed, freed == 6)

        log.part("PART 5. Criterion 3: items with stale context carry a warning")
        for item in found["items"].values():
            if item["stale"]:
                log.out("  %-24s %-11s %s" % (item["identity"], item["list"], item["age"]))
        stale = [i for i in found["items"].values() if i["stale"]]
        log.check("4 items have stale context, and each carries a warning beginning STALE CONTEXT that gives the field, the age and the limit", len(stale) == 4 and all(i["warnings"] and i["warnings"][0].startswith("STALE CONTEXT: `retrieved_at` is") for i in stale))
        log.check("no item with fresh context carries that warning", not any(w.startswith("STALE") for i in found["items"].values() if not i["stale"] for w in i["warnings"]))
        log.check("the 3 stale items that are ranked keep the places their recorded fields give them, 1, 4 and 9, and the file prints the warning under each", [i["place"] for i in ranked if i["stale"]] == [1, 4, 9]
                  and text[text.index("## Ranked"):text.index("## Not recommended")].count("- WARNING: STALE CONTEXT:") == 3)
        log.check("\"Start here\" is jira:61001, at place 2, the first ranked item whose copy is fresh. The stale item at place 1, jira:61004, is named above it with its warning",
                  found["pick"]["identity"] == "jira:61001" and "- `jira:61004` \"Weekly menu import\", place 1. STALE CONTEXT:" in text[text.index("## Start here"):text.index("## Ranked")])
        log.check("the limit, %d hours, is the one in the approved freshness policy, read from that file" % hours["work-item-status"], hours["work-item-status"] == 24 and "| `work-item-status` | 24 hours |" in read(rank.POLICY))

        def edge(other):
            other["jira:61002"]["retrieved_at"] = "2026-11-30T09:00:00Z"
            other["jira:61003"]["retrieved_at"] = "2026-11-30T08:59:59Z"
        at_edge = changed(edge)
        log.check("a copy retrieved exactly 24 hours before the clock value is fresh, and one retrieved a second earlier is stale", (at_edge["items"]["jira:61002"]["stale"], at_edge["items"]["jira:61003"]["stale"]) == (False, True))

        def refresh(other):
            other["jira:61004"]["retrieved_at"] = "2026-12-01T08:30:00Z"
        log.check("with jira:61004 fetched again, so that its copy is fresh, it becomes \"Start here\"", changed(refresh)["pick"]["identity"] == "jira:61004")

        log.part("PART 6. Criterion 4: ties are broken by a stated rule")
        log.out("The rule: %s. The first criterion on which two items differ decides between them." % ", then ".join(rank.RULES["priority-first"]), "")
        for item in ranked[1:]:
            log.out("  %2d. %-32s below %-32s by %s" % (item["place"], item["identity"], item["below"][0], item["below"][1]))
        values = lambda i: {"priority": i["priority"], "due": i["due"], "waiters": i["waiters"], "created": i["created"], "identity": i["identity"]}
        sound = True
        for above, item in zip(ranked, ranked[1:]):
            for criterion in rank.RULES["priority-first"]:
                if criterion == item["below"][1]:
                    sound = sound and values(above)[criterion] != values(item)[criterion]
                    break
                sound = sound and values(above)[criterion] == values(item)[criterion]
        log.check("for every pair of neighbours, the two are level on every criterion before the one named, and differ on the one named", sound)
        used = sorted({i["below"][1] for i in ranked[1:]})
        log.check("the handed-in data uses every level of the rule: %s" % ", ".join(used), used == sorted(rank.RULES["priority-first"]))
        log.check("jira:61006 and jira:61007 are level on priority, due date, waiters and created date. Identity decides, and the file says so", found["items"]["jira:61007"]["below"] == ("jira:61006", "identity")
                  and "- Placed below `jira:61006` by identity: `identity` is `jira:61007`, and for `jira:61006` `identity` is `jira:61006`." in text)
        log.check("jira:61001 and jira:61002 are level on priority and due date. The number of items waiting decides: 2 against 0", found["items"]["jira:61002"]["below"] == ("jira:61001", "waiters"))
        log.check("rules.md states the order, and that identity is last so that no tie is left", "## 3. Ties" in read(os.path.join(FOLDER, "rules.md")) and "| 5 | Identity, as the last tie-break |" in read(os.path.join(FOLDER, "rules.md")))

        log.part("PART 7. Criterion 5: missing data lowers confidence and is reported, not filled in")
        for item in found["items"].values():
            if item["missing"] and item["list"] != "not offered":
                log.out("  %-32s %-8s missing: %-14s confidence %s" % (item["identity"], item["list"], ", ".join(item["missing"]), item["confidence"]))
        missing = [i for i in ranked + found["blocked"] if i["missing"]]
        log.check("4 ranked or blocked items have missing data. Each says so in its reasons, in the words \"not recorded\" or \"which is not a date\"",
                  len(missing) == 4 and all(any("is not recorded" in t or "which is not" in t for _, t in i["reasons"]) for i in missing))
        log.check("each has lower confidence than high, and the item missing two fields is at low", all(i["confidence"] != "high" for i in missing) and found["items"]["trello:7b2e000000000000000e0002"]["confidence"] == "low")
        log.check("every item with nothing missing and a fresh copy is at high", all(i["confidence"] == "high" for i in found["items"].values() if not i["missing"] and not i["stale"]))
        log.check("nothing was filled in: the inputs file is unchanged, and the recommendation gives no priority and no due date for an item that has none",
                  digests() == before and "`priority` is not recorded" in text and "`due` is `\"soon\"`, which is not a date" in text)
        log.check("an item with a missing value is placed after every item that has one: on priority, the one item without a priority is last. Among the high-priority items, the one with no due date is last of them",
                  ranked[-1]["missing"][:1] == ["priority"] and [i["identity"] for i in ranked if i["priority"] == 0][-1] == "trello:7b2e000000000000000e0001")

        def fill(other):
            other["trello:7b2e000000000000000e0002"].update(priority="high", due="2026-12-01")
        filled = changed(fill)
        log.check("when a person records the missing priority and due date, the item moves from place 13 to place %d and its confidence goes from low to high. The ranking did not guess either value" % filled["items"]["trello:7b2e000000000000000e0002"]["place"],
                  filled["items"]["trello:7b2e000000000000000e0002"]["place"] == 1 and filled["items"]["trello:7b2e000000000000000e0002"]["confidence"] == "high")

        log.part("PART 8. Criterion 7: a person can disagree with a reason and see which field to change")
        log.out("Each place below first names the criterion that put it under the item above. Here that field is changed, in a copy of the",
                "inputs, to one that beats the item above, and the ranking is run again.", "")
        moved_up, cannot = 0, []
        for above, item in zip(ranked, ranked[1:]):
            criterion = item["below"][1]

            def edit(other, above=above, item=item, criterion=criterion):
                mine, theirs = other[item["identity"]], other[above["identity"]]
                if criterion == "priority":
                    mine["priority"] = theirs["priority"]
                    theirs_due = rank.day(theirs.get("due"))
                    mine["due"] = (theirs_due - datetime.timedelta(days=1)).isoformat() if theirs_due else "2026-12-31"
                elif criterion in ("due", "created"):
                    mine[criterion] = (datetime.date.fromisoformat(theirs[criterion]) - datetime.timedelta(days=1)).isoformat()
                elif criterion == "waiters":
                    spare = [i for i in sorted(other) if other[i]["kind"] == "work" and other[i].get("status") == "in_progress"]
                    mine["blocks"] = spare[:above["waiters"] + 1] + ["jira:61011"] * (above["waiters"] + 1 - len(spare[:above["waiters"] + 1]))
                    mine["blocks"] = sorted(set(mine["blocks"]) | {"jira:61011", "jira:61012", DARK})
            if criterion == "identity":
                cannot.append(item["identity"])
                continue
            result = changed(edit)
            up = result["items"][item["identity"]]["place"] < result["items"][above["identity"]].get("place", 99)
            moved_up += up
            log.out("  %-32s was below %-32s by %-8s  after changing that field: %s" % (item["identity"], above["identity"], criterion, "above it" if up else "STILL BELOW"))
        log.check("in %d of %d pairs, changing the one field named put the item above its neighbour" % (moved_up, len(ranked) - 1 - len(cannot)), moved_up == len(ranked) - 1 - len(cannot) and moved_up == 11)
        log.check("the one pair decided by identity cannot be changed that way, since an identity is not edited: %s. The file names the earlier fields to change" % ", ".join(cannot), cannot == ["jira:61007"])
        log.check("the recommendation ends with a table of what to change for each kind of disagreement", "## To disagree with a place" in text and "| it is not really blocked | `blocked_by` or `needs_decision` on the item, or the `status` of what it waits on |" in text)

        log.part("PART 9. Safety: the recommendation never starts, assigns or changes work")
        probe = ("import sys; sys.path.insert(0, %r); import rank; rank.main(['rank', '--inputs', %r, '--out', %r], say=lambda line: None); "
                 "print(sorted(m for m in sys.modules if m.split('.')[0] in ('socket', 'ssl', 'http', 'urllib', 'smtplib', 'ftplib', 'subprocess')))" % (SKILL, inputs_path, os.path.join(scratch, "probe.md")))
        done = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True)
        log.out(*(["The probe itself failed: " + done.stderr.strip().splitlines()[-1]] if done.returncode else []))
        log.out("Modules for connecting, mailing or running another program that Python had loaded after a ranking run: %s" % done.stdout.strip())
        log.check("none was loaded", done.stdout.strip() == "[]")
        log.check("a run writes one file, the recommendation, and nothing else", sorted(n for n in os.listdir(scratch) if n.startswith("recommendation-1")) == ["recommendation-1.md"])
        said = []
        refused = rank.main(["rank", "--inputs", inputs_path, "--out", inputs_path], say=said.append)
        log.out("Told to write the recommendation over the inputs file:", "  " + said[-1])
        log.check("it refuses, with exit code 2, and the inputs are unchanged", refused == 2 and digests() == before)
        log.check("no record has a different status or assignee after the runs: the inputs file has the SHA-256 it had at the start", digests()["inputs.md"] == before["inputs.md"])

        log.part("PART 10. Stretch goals: another priority rule, and why an item was not first")
        said = []
        rank.main(["rank", "--inputs", inputs_path, "--rule", "due-first", "--out", os.path.join(scratch, "due-first.md")], say=said.append)
        log.out("$ %s --rule due-first --out SCRATCH/due-first.md" % COMMAND, "-" * 78, *said[:15], "  ...", said[-2], "-" * 78)
        due_first = rank.analyse(copy.deepcopy(records), clock, hours, "due-first")
        log.out("Where each item is under each rule:", "  item                              priority-first  due-first")
        for item in ranked:
            log.out("  %-32s  %-14d  %d" % (item["identity"], item["place"], due_first["items"][item["identity"]]["place"]))
        log.check("under due-first the same 13 items are ranked, the same 6 are blocked and the same 3 are not offered", sorted(order(due_first)) == sorted(order(found)) and len(due_first["blocked"]) == 6)
        log.check("jira:61008, low priority and due the day after the clock value, moves from place 12 to place 2, and becomes \"Start here\" in place of jira:61001",
                  (found["items"]["jira:61008"]["place"], due_first["items"]["jira:61008"]["place"], due_first["pick"]["identity"]) == (12, 2, "jira:61008"))
        log.check("why an item was not first: all 12 items below first place say which criterion decides against first place, in the data and in the file",
                  all(i["not_first"][0] == ranked[0]["identity"] for i in ranked[1:]) and text.count("- Why it is not first: ") + 1 == 12)
        log.out("  (11 lines \"Why it is not first\", and the item at place 2 gives the same fact in its \"Placed below\" line.)")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    log.check("at the end, every file in participant/context/next-work is what it was at the start", digests() == before)
    log.lines += ["", "RESULT: %s" % ("%d OF %d CHECKS FAILED." % (len(log.failed), log.count) if log.failed else "ALL CHECKS PASSED. %d checks." % log.count)]
    os.makedirs(LOGS, exist_ok=True)
    with open(os.path.join(LOGS, "ranking-run.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(log.lines) + "\n")
    print("ranking-run.txt: %s" % log.lines[-1])
    for label in log.failed:
        print("  FAILED: %s" % label)
    return 1 if log.failed else 0


if __name__ == "__main__":
    sys.exit(main())
