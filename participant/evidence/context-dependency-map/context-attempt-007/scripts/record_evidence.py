#!/usr/bin/env python3
"""Records logs/dependency-run.txt for the quest context-dependency-map. It contacts nothing.

    python3 participant/evidence/context-dependency-map/context-attempt-007/scripts/record_evidence.py

It builds the index from the handed-in data into a scratch folder, SCRATCH, which is deleted at the end, and then
builds from copies of the data with one thing changed at a time. It changes nothing in
participant/context/dependencies, and it checks that.
"""
import copy
import hashlib
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
SKILL = os.path.join(REPO, "participant", "skills", "context-dependency-map")
sys.path.insert(0, SKILL)
import depmap      # noqa: E402

LOGS = os.path.join(HERE, "..", "logs")
FOLDER = depmap.FOLDER
COMMAND = "python3 participant/skills/context-dependency-map/depmap.py"


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def digests():
    return {name: sha(read(os.path.join(FOLDER, name))) for name in sorted(os.listdir(FOLDER))}


def as_text(records):
    return "\n".join("### %s\n\n```json\n%s\n```\n" % (r["identity"], json.dumps(r, indent=2)) for r in records)


class Log:
    def __init__(self):
        self.lines = ["The dependency run. context-dependency-map, attempt context-attempt-007",
                      "Recorded by scripts/record_evidence.py. No request was sent anywhere. Every record is made up."]
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
    scratch = tempfile.mkdtemp(prefix="gtq-depmap-")
    data_path = os.path.join(FOLDER, "data.md")
    data_text = read(data_path)
    records = depmap.read_records(data_text)
    found = depmap.analyse(records)
    links, state, problems = found["links"], found["state"], found["problems"]

    def changed(edit):
        other = copy.deepcopy(records)
        edit(other)
        return depmap.analyse(other)

    try:
        log.part("PART 1. The build, on participant/context/dependencies/data.md")
        before = digests()
        said, out = [], os.path.join(scratch, "index.md")
        code = depmap.main(["build", "--data", data_path, "--out", out], say=said.append)
        log.out("$ %s build --out SCRATCH/index.md" % COMMAND, "-" * 78, *said, "-" * 78, "exit code: %d" % code,
                "Exit code 1 means: the index was built, and problems are reported. The data holds problems on purpose.")
        first = read(out)
        log.check("the index was built and the build ended with exit code 1, because it has problems to report", code == 1 and said[-1] == "Wrote index.md. PROBLEMS REPORTED: 16.")
        log.check("the build changed no file in participant/context/dependencies", digests() == before)
        refused = depmap.main(["build", "--data", data_path, "--out", data_path], say=said.append)
        log.out("Told to write the index over the data file:", "  " + said[-1])
        log.check("it refuses, with exit code 2, and the data file is unchanged", refused == 2 and digests() == before)
        log.check("the index it wrote is the handed-in index.md, byte for byte", first == read(os.path.join(FOLDER, "index.md")))
        done = subprocess.run([sys.executable, os.path.join(SKILL, "make_data.py")], capture_output=True, text=True)
        log.check("data.md is byte for byte what make_data.py writes, so it was not adjusted by hand", done.returncode == 0 and digests() == before)

        log.part("PART 2. Criterion 7: the index is identical across two runs on the same input")
        said2, out2 = [], os.path.join(scratch, "index-2.md")
        code2 = depmap.main(["build", "--data", data_path, "--out", out2], say=said2.append)
        log.out("$ %s build --out SCRATCH/index-2.md" % COMMAND, "exit code: %d" % code2, "",
                "SHA-256 of the first run's index:  %s" % sha(first), "SHA-256 of the second run's index: %s" % sha(read(out2)))
        log.check("the second run's index is byte for byte the first run's", read(out2) == first)
        log.check("the second run printed exactly what the first printed", said2 == said[:len(said2)])
        seeds = {}
        for seed in ("0", "1", "2", "3", "4"):
            target = os.path.join(scratch, "seed-%s.md" % seed)
            done = subprocess.run([sys.executable, os.path.join(SKILL, "depmap.py"), "build", "--data", data_path, "--out", target],
                                  capture_output=True, text=True, env=dict(os.environ, PYTHONHASHSEED=seed))
            seeds[seed] = sha(read(target)) if os.path.exists(target) else done.stderr
        log.out("Five more runs, each a separate Python process with a different hash seed, which changes the order Python keeps sets in:",
                *["  seed %s  %s" % pair for pair in seeds.items()])
        log.check("all five give the same index as the first run", set(seeds.values()) == {sha(first)})
        same = 0
        for seed in range(20):
            rng = random.Random(seed)
            shuffled = [copy.deepcopy(records[k]) for k in records]
            rng.shuffle(shuffled)
            for r in shuffled:
                for field in depmap.LINK_FIELDS:
                    if isinstance(r.get(field), list):
                        r[field] = rng.sample(r[field], len(r[field]))
            same += depmap.render(depmap.analyse(depmap.read_records(as_text(shuffled)))) == first
        log.check("with the records in 20 different orders, and each list of links shuffled, the index is the same every time: %d of 20" % same, same == 20)
        log.check("the index does not hold the date of this run", __import__("datetime").date.today().isoformat() not in first)

        log.part("PART 3. Criterion 1: dependencies come from recorded fields, not from words in a title")
        log.out("Every link, with the field and the record it was read from:", "")
        for (waiter, target) in sorted(links):
            log.out("  %-32s waits on %-32s %s" % (waiter, target, "; ".join("%s on %s" % s for s in sorted(links[(waiter, target)]))))
        log.check("all %d links come from blocked_by, blocks or needs_decision, and from no other field" % len(links),
                  len(links) == 28 and all(field in depmap.LINK_FIELDS for sources in links.values() for field, _ in sources))
        recorded = set()
        for identity, record in records.items():
            for field in depmap.LINK_FIELDS:
                for named in record.get(field, []):
                    if depmap.IDENTITY.match(named):
                        recorded.add((named, identity) if field == "blocks" else (identity, named))
        log.check("the links are exactly the pairs written in those three fields in data.md, read here separately", recorded == set(links))
        title = records["jira:52023"]
        log.out("", "jira:52023 has the title \"%s\"" % title["title"], "and the description \"%s\"" % title["description"])
        log.check("jira:52023 names jira:52003 and jira:52002 in words only, and the index gives it no link", found["waits_on"]["jira:52023"] == [] and "jira:52023" not in found["waited_by"]["jira:52003"] + found["waited_by"]["jira:52002"])
        log.check("jira:52024 has a parent and a related item, and the index gives it no link. Both fields are listed under \"Seen and not counted\"",
                  found["waits_on"]["jira:52024"] == [] and "- `parent` on `jira:52024`" in first and "- `related` on `jira:52024`" in first)

        def reword(other):
            for r in other.values():
                r["title"], r["description"], r["labels"] = "Blocked by jira:52001, depends on decision:E-209", "Cannot start until jira:52010 is done", ["jira:52001"]
        log.check("with every title, description and label replaced by words that name other items, the links are the same %d" % len(links), changed(reword)["links"] == links)

        def strip(other):
            for r in other.values():
                for field in depmap.LINK_FIELDS:
                    r.pop(field, None)
        log.check("with the three fields taken off every record and the titles left as they are, there are no links at all", changed(strip)["links"] == {})
        log.out("", "Links written at one end only: %d of %d." % (len(found["one_sided"]), len(links)))

        log.part("PART 4. Criterion 2: a forward and a reverse index are both generated")
        forward = first[first.index("## Forward index"):first.index("## Reverse index")]
        reverse = first[first.index("## Reverse index"):first.index("## Links written at one end only")]
        log.out("Entries in the forward index: %d. In the reverse index: %d. Records: %d, and 2 more named and not found." % (forward.count("\n### "), reverse.count("\n### "), len(records)))
        log.check("each index has an entry for every one of the 41 items", forward.count("\n### ") == 41 and reverse.count("\n### ") == 41)
        log.check("each index holds every one of the 28 links once: %d lines \"Waits on\" and %d lines \"Waited on by\"" % (forward.count("\n- Waits on "), reverse.count("\n- Waited on by ")),
                  forward.count("\n- Waits on ") == 28 and reverse.count("\n- Waited on by ") == 28)
        log.check("the reverse index is the forward index turned round: A is waited on by B exactly when B waits on A",
                  sorted((a, b) for a in found["waits_on"] for b in found["waits_on"][a]) == sorted((a, b) for b in found["waited_by"] for a in found["waited_by"][b]))
        log.out("", "\"Who is waiting on jira:52001?\", from the reverse index:", *["  " + line for line in reverse[reverse.index("### `jira:52001`"):].split("\n\n### ")[0].splitlines() if line.startswith("- ")])

        log.part("PART 5. Criterion 3: a cycle is reported with the items in it")
        for members, way in problems["cycles"]:
            log.out("  CYCLE of %d: %s" % (len(members), ", ".join(members)), "    one way round: %s" % " waits on ".join(way))
        log.check("two cycles are reported: jira:52010 with jira:52011, and decision:E-203 with jira:52014 and jira:52015",
                  found["cycles"] == [["decision:E-203", "jira:52014", "jira:52015"], ["jira:52010", "jira:52011"]])
        log.check("each way round is real: every step in it is a recorded link, and it ends where it starts",
                  all(way[0] == way[-1] and all((a, b) in links for a, b in zip(way, way[1:])) for _, way in problems["cycles"]))

        def reaches_itself(n):
            seen, stack = set(), list(found["waits_on"][n])
            while stack:
                t = stack.pop()
                if t == n:
                    return True
                if t not in seen:
                    seen.add(t)
                    stack.extend(found["waits_on"][t])
            return False
        by_walking = sorted(n for n in found["nodes"] if reaches_itself(n))
        log.out("Checked another way, by following links from each item to see whether it comes back to itself: %s" % ", ".join(by_walking))
        log.check("that gives the same items: the five in the two cycles, and the one that names itself", by_walking == sorted(found["in_cycle"]) and len(by_walking) == 6)
        log.check("the item that names itself, trello:6a1f000000000000000d0003, is reported on its own line and not as a cycle", problems["self"] == ["trello:6a1f000000000000000d0003"])
        log.check("jira:52012 waits on a cycle and is not reported as part of it", "jira:52012" not in found["in_cycle"] and "jira:52010" in found["waits_on"]["jira:52012"])

        def cut(other):
            other["jira:52011"]["blocked_by"] = []
        log.check("with one of its two links removed, that cycle is no longer reported, and the other still is", changed(cut)["cycles"] == [["decision:E-203", "jira:52014", "jira:52015"]])

        def close(other):
            other["jira:52001"]["blocked_by"] = ["trello:6a1f000000000000000d0001"]
        log.check("with one link added from the bottom of the long chain to its top, a third cycle of 6 is reported",
                  [len(c) for c in changed(close)["cycles"]] == [3, 6, 2])
        log.check("the build printed both cycles by name", "CYCLE: jira:52010 waits on jira:52011 waits on jira:52010" in said
                  and "CYCLE: decision:E-203 waits on jira:52015 waits on jira:52014 waits on decision:E-203" in said)

        log.part("PART 6. Criterion 4: a link to a missing item is reported by name, not dropped")
        for n, waiters in problems["missing"]:
            log.out("  NOT FOUND: %s, named by %s" % (n, ", ".join(waiters)))
        log.check("decision:E-209 and jira:52999 are reported by name, each with the records that name it",
                  problems["missing"] == [("decision:E-209", ["jira:52013", "jira:52027"]), ("jira:52999", ["trello:6a1f000000000000000d0002"])])
        log.check("neither link was dropped: each is in the forward index of the record that wrote it, and each missing item has its own entry in both indexes",
                  "decision:E-209" in found["waits_on"]["jira:52013"] and "jira:52999" in found["waits_on"]["trello:6a1f000000000000000d0002"]
                  and forward.count("**NOT FOUND: nothing in the data has this identity.**") == 2 and reverse.count("**NOT FOUND: nothing in the data has this identity.**") == 2)
        log.check("the build printed both by name", "NOT FOUND: decision:E-209, named by jira:52013, jira:52027" in said and "NOT FOUND: jira:52999, named by trello:6a1f000000000000000d0002" in said)

        def add(other):
            other["decision:E-209"] = {"identity": "decision:E-209", "kind": "decision", "title": "Live delays come from the operators' feed", "status": "decided"}
        log.check("with a record for decision:E-209 added, it is no longer reported, and jira:52999 still is", [n for n, _ in changed(add)["problems"]["missing"]] == ["jira:52999"])

        def remove(other):
            del other["jira:52002"]
        gone = changed(remove)["problems"]["missing"]
        log.out("With the record of jira:52002 deleted: %s" % "; ".join("%s, named by %s" % (n, ", ".join(w)) for n, w in gone))
        log.check("with the record of jira:52002 deleted, it is reported by name with the two records that wait on it", ("jira:52002", ["jira:52003", "jira:52025"]) in gone)
        log.check("the link that is not an identity, \"52001\" on github:I_kwFIXdep0003, is reported as unreadable and no link is guessed from it",
                  [(n, value) for n, _, value, _ in problems["unreadable"]] == [("github:I_kwFIXdep0003", '"52001"')] and found["waits_on"]["github:I_kwFIXdep0003"] == [])

        log.part("PART 7. Criterion 5: a dependency on a decision is represented like one on a work item")
        on_decisions = sorted(pair for pair in links if pair[1].startswith("decision:"))
        for pair in on_decisions:
            log.out("  %-28s waits on %-16s %s, %s" % (pair[0], pair[1], depmap.STATE_WORDS[state[pair[1]]], "; ".join("%s on %s" % s for s in sorted(links[pair]))))
        log.check("%d links are to a decision. They are in the same table of links, the same forward index and the same reverse index as the others" % len(on_decisions),
                  len(on_decisions) == 6 and all(t in found["waits_on"][w] and w in found["waited_by"][t] for w, t in on_decisions))
        log.check("a decision is waited on, ranked and counted like a work item: decision:E-209 is third among those blocking the most", found["top"][2] == "decision:E-209")
        log.check("a decision can wait on work: decision:E-203 waits on jira:52015, and is in a cycle with it", "jira:52015" in found["waits_on"]["decision:E-203"])

        def swap(other):
            for r in other.values():
                if "needs_decision" in r and r["identity"] != "jira:52025":
                    r["blocked_by"] = r.get("blocked_by", []) + r.pop("needs_decision")
        swapped = changed(swap)
        log.check("written as blocked_by in place of needs_decision, the same links, cycles, counts and top five result",
                  set(swapped["links"]) == set(links) and swapped["cycles"] == found["cycles"] and swapped["blocked"] == found["blocked"] and swapped["top"] == found["top"])
        log.check("a decided decision holds nothing up, and waiting on a proposal or a question is reported: %s" % ", ".join("%s on %s" % pair for pair in problems["undecided"]),
                  state["decision:E-201"] == "finished" and problems["undecided"] == [("jira:52014", "decision:E-203"), ("jira:52016", "decision:E-202")])

        log.part("PART 8. Criterion 6: the five items blocking the most other items, with their counts")
        log.out("  place  item                              blocks in all  directly  the items")
        for place, n in enumerate(found["top"], 1):
            log.out("  %-5d  %-32s  %-13d  %-8d  %s" % (place, n, len(found["blocked"][n]), len(found["direct"][n]), ", ".join(found["blocked"][n])))

        def recount(n):
            reach, grew = {n}, True
            while grew:
                grew = False
                for (waiter, target) in links:
                    if target in reach and waiter not in reach and state[waiter] in ("waiting", "undecided") and state[target] != "finished":
                        reach.add(waiter)
                        grew = True
            return sorted(reach - {n})
        log.check("five items are listed, with the counts 8, 5, 3, 3 and 2", [len(found["blocked"][n]) for n in found["top"]] == [8, 5, 3, 3, 2])
        log.check("counted again by a different method, sweeping the whole list of links until nothing more is added, every item in the data gets the same set",
                  all(recount(n) == found["blocked"][n] for n in found["blocked"]))
        log.check("no item outside the five blocks more than the fifth", max(len(v) for n, v in found["blocked"].items() if n not in found["top"]) <= 2)
        log.check("the index says that 6 more items are level with fifth place, and names them", "6 more items have the same total as fifth place and are not listed" in first and len(found["level"]) == 6)
        log.check("a finished item is not counted as blocking: jira:52019 is done, jira:52018 waits on it, and it is in no count", "jira:52019" not in found["blocked"])
        log.check("the table in the index gives the same five and the same counts",
                  all("| %d | `%s`" % (place, n) in first and "| %d | %d |" % (len(found["blocked"][n]), len(found["direct"][n])) in first for place, n in enumerate(found["top"], 1)))

        log.part("PART 9. Stretch goals: the longest chain, and what a slip does")
        log.out("Longest chain, %d items: %s" % (len(found["longest"]), " waits on ".join(found["longest"])))
        log.check("every step of the chain is a recorded link", all((a, b) in links for a, b in zip(found["longest"], found["longest"][1:])))

        def deepest(n, path):
            best = len(path)
            for t in found["waits_on"][n]:
                if t not in path and t not in found["in_cycle"] and state[t] not in ("finished", "gone"):
                    best = max(best, deepest(t, path + [t]))
            return best
        longest = max(deepest(n, [n]) for n in found["nodes"] if n not in found["in_cycle"] and state[n] in ("waiting", "undecided"))
        log.check("trying every path outside the cycles, none is longer than %d" % len(found["longest"]), longest == len(found["longest"]) == 6)
        rows = depmap.slip(found, "jira:52001", 5)
        log.out("", "$ %s slip jira:52001 5" % COMMAND, *["  %-32s %s" % (n, "cannot be dated" if d is None else "earliest start %s -> %s, pushed %d" % (a, b, d)) for n, a, b, d in rows])
        log.check("the slip reaches all 8 items that jira:52001 blocks, and no other", [n for n, _, _, _ in rows] == found["blocked"]["jira:52001"])
        log.check("no item is pushed by more than the 5 days of the slip, and the ones with room in the plan are pushed by less or not at all",
                  all(0 <= d <= 5 for _, _, _, d in rows) and sorted(d for _, _, _, d in rows) == [0, 0, 0, 1, 1, 3, 3, 3])
        log.check("a slip of 0 days moves nothing", all(d == 0 for _, _, _, d in depmap.slip(found, "jira:52001", 0)))
        log.check("an item that waits on a cycle cannot be dated, and the slip says so: jira:52012", depmap.slip(found, "jira:52010", 2) == [("jira:52011", None, None, None), ("jira:52012", None, None, None)])
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    log.check("at the end, every file in participant/context/dependencies is what it was at the start", digests() == before)
    log.lines += ["", "RESULT: %s" % ("%d OF %d CHECKS FAILED." % (len(log.failed), log.count) if log.failed else "ALL CHECKS PASSED. %d checks." % log.count)]
    os.makedirs(LOGS, exist_ok=True)
    with open(os.path.join(LOGS, "dependency-run.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(log.lines) + "\n")
    print("dependency-run.txt: %s" % log.lines[-1])
    for label in log.failed:
        print("  FAILED: %s" % label)
    return 1 if log.failed else 0


if __name__ == "__main__":
    sys.exit(main())
