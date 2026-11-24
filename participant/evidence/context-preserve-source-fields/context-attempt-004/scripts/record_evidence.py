#!/usr/bin/env python3
"""Records logs/roundtrip-check.txt for the quest context-preserve-source-fields. It contacts nothing.

    python3 participant/evidence/context-preserve-source-fields/context-attempt-004/scripts/record_evidence.py

Part 1 checks the handed-in files in participant/context/fidelity and changes none of them. Every other part works on text
in memory or in a scratch folder, SCRATCH, which is deleted at the end.
"""
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "participant", "skills", "context-preserve-source-fields"))
import fidelity      # noqa: E402

LOGS = os.path.join(HERE, "..", "logs")
COMMAND = "python3 participant/skills/context-preserve-source-fields/fidelity.py"


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class Log:
    def __init__(self):
        self.lines = ["The round-trip check. context-preserve-source-fields, attempt context-attempt-004",
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

    def run(self, args, shown):
        said = []
        code = fidelity.main(args, say=said.append)
        self.out("$ %s %s" % (COMMAND, shown), "-" * 78, *said, "-" * 78, "exit code: %d" % code)
        return code, said


def main():
    log = Log()
    sources = read(os.path.join(fidelity.FOLDER, "source-records.md"))
    normalized = read(os.path.join(fidelity.FOLDER, "normalized.md"))
    records = fidelity.source_records(sources)
    held = {record["source_record"]: record for record in fidelity.normalized_records(normalized)}
    scratch = tempfile.mkdtemp(prefix="gtq-fidelity-")
    try:
        log.part("PART 1. The handed-in files: participant/context/fidelity/source-records.md and normalized.md (criteria 4 and 6)",
                 "Each source record is rebuilt from its normalized record alone, and the rebuilt text is compared with the original, character for character.")
        code, said = log.run(["check"], "check")
        log.check("the check passes: exit code 0", code == 0)
        log.check("there are 6 source records, 2 each for jira, trello and github, and each has a normalized record", len(records) == 6 and sorted(set(s for _, s, _ in records)) == sorted(fidelity.SYSTEMS)
                  and all(heading in held for heading, _, _ in records))
        log.check("every one of the 6 was rebuilt and is identical to its original, character for character (criterion 6)",
                  len([line for line in said if "identical to the original, character for character" in line]) == 6
                  and all(fidelity.rebuild(system, held[heading]) == (block, []) for heading, system, block in records))
        log.check("normalized.md is exactly what the normalizer writes from source-records.md, so it was not adjusted by hand to pass",
                  normalized == fidelity.render([fidelity.normalize_one(h, s, b, fidelity.status_map_of(sources)) for h, s, b in records], fidelity.LATEST))
        fields = sum(1 for _, system, block in records for _, raw in fidelity.fields_of(system, block) if raw is not None)
        kept = sum(len(record["preserved"]) for record in held.values())
        back = sum(len(record["rebuilt_from_canonical"]) for record in held.values())
        log.out("Across the 6 records: %d source fields. %d are preserved as sent. %d are given back by a canonical field." % (fields, kept, back))
        log.check("every source field is accounted for: preserved, or given back by a canonical field, and never both or neither (criterion 2)", fields == kept + back and all(
            sorted([p for p, _ in held[h]["preserved"]] + list(held[h]["rebuilt_from_canonical"])) == sorted(p for p, raw in fidelity.fields_of(s, b) if raw is not None) for h, s, b in records))
        log.check("every record has the same canonical field names, in the same order (criterion 1)",
                  all(list(record["canonical"]) == [name for name, _, _ in fidelity.CANONICAL] for record in held.values()))
        log.check("every preserved value is the source's own characters: each one is found, as it stands, in its source record (criterion 3)",
                  all(raw == dict(fidelity.fields_of(s, b))[path] for h, s, b in records for path, raw in held[h]["preserved"]))
        listed = all(path in [row[0] for row in fidelity.CONSIDERED[s]] for _, s, b in records for path, raw in fidelity.fields_of(s, b) if raw is not None)
        log.check("every field in the source records is in the mapping's list of fields considered, with its outcome and a reason (criterion 7)",
                  listed and not any("NOTE: the field" in line for line in said) and read(os.path.join(fidelity.FOLDER, "mapping-rationale.md")) == fidelity.rationale_document())

        log.part("PART 2. Would a careless normalizer have changed anything? (criterion 3)",
                 "For each preserved value: what parsing it as JSON and writing it out again would give, in three common ways of writing. Nothing in the skill does this.",
                 "It is here to show what \"untouched\" protects, by measuring it on these records.")
        ways = [("written out with the defaults of the language's JSON library", lambda value: json.dumps(value)),
                ("written out without turning other alphabets into escapes", lambda value: json.dumps(value, ensure_ascii=False)),
                ("written out compactly, with no spaces", lambda value: json.dumps(value, separators=(",", ":")))]
        counts = []
        for name, write in ways:
            changed = [(heading, path, raw, write(json.loads(raw))) for heading, system, block in records for path, raw in held[heading]["preserved"] if write(json.loads(raw)) != raw]
            counts.append(len(changed))
            log.out("  %s: %d of the %d preserved values would come out different. For example:" % (name, len(changed), kept))
            for heading, path, raw, again in changed[:3]:
                log.out("      %s  %s" % (heading, path), "          as sent:   %s" % fidelity.show(raw), "          rewritten: %s" % fidelity.show(again))
        log.check("each of the three ways of rewriting would change at least one preserved value: %d, %d and %d of %d" % (counts[0], counts[1], counts[2], kept), min(counts) >= 1)
        log.check("the number sent as 1e3 would be changed by all three, and the escape in the Jira summary by the second",
                  json.dumps(json.loads("1e3")) != "1e3" and json.dumps(json.loads(dict(held["jira 10042"]["preserved"])["fields.summary"]), ensure_ascii=False) != dict(held["jira 10042"]["preserved"])["fields.summary"])
        log.check("3.0 and 65535.5 would survive all three in this language, and are preserved as sent all the same",
                  "\nfields.customfield_10016: 3.0\n" in normalized and "\npos: 65535.5\n" in normalized and json.dumps(json.loads("3.0")) == "3.0")

        log.part("PART 3. A field is dropped on purpose (criterion 5)",
                 "The scenario's field: the Trello board's custom field for customer impact. Its line is deleted from a copy of normalized.md, in SCRATCH, and the check is run on the copy.")
        line = [one for one in normalized.split("\n") if one.startswith("customFieldItems: [{")][0]
        log.out("The line deleted:", "  %s" % fidelity.show(line))
        copy = os.path.join(scratch, "normalized.md")
        with open(copy, "w", encoding="utf-8") as f:
            f.write(normalized.replace(line + "\n", "", 1))
        code, said = log.run(["check", "--normalized", copy], "check --normalized SCRATCH/normalized.md")
        log.check("the check fails: exit code 2", code == 2)
        log.check("it names the dropped field: customFieldItems, in the Trello card's record",
                  any("trello 62c0000000000000000000a1: NOT IDENTICAL" in one for one in said) and any("MISSING FIELD: customFieldItems" in one for one in said))
        log.check("it reports that one record and no other: the other 5 are still identical", len([one for one in said if "identical to the original, character for character" in one]) == 5)
        log.check("the handed-in normalized.md was not touched", read(os.path.join(fidelity.FOLDER, "normalized.md")) == normalized)

        log.part("PART 4. Other ways of losing something, one at a time",
                 "Each case changes the text of normalized.md in one place, in memory, and checks it. \"Reported\" is what the check then says about that record.")
        cases = [
            ("a translated field's original is dropped: Jira's status object, though the canonical status is still there (criterion 6)",
             [one for one in normalized.split("\n") if one.startswith('fields.status: {"id": "10003"')][0] + "\n", "", "MISSING FIELD: fields.status"),
            ("a copied field's canonical value is dropped: the Jira key", '\nreference: "DEMO-42"\n', "\n", "MISSING FIELD: key"),
            ("a number is tidied: 3.0 becomes 3 (criterion 3)", "fields.customfield_10016: 3.0", "fields.customfield_10016: 3", "CHANGED FIELD: fields.customfield_10016"),
            ("a number is tidied: 1e3 becomes 1000.0 (criterion 3)", "pos: 1e3", "pos: 1000.0", "CHANGED FIELD: pos"),
            ("a time is tidied to UTC seconds (criterion 3)", '"2026-11-17T09:30:00.000+0000"', '"2026-11-17T09:30:00Z"', "CHANGED FIELD: fields.updated"),
            ("trailing spaces are trimmed from a description (criterion 3)", 'See the runbook.  "', 'See the runbook."', "CHANGED FIELD: fields.description"),
            ("spaces inside an object are removed, leaving the same data (criterion 3)", '"key": "indeterminate", "name": "In Progress"}}', '"key":"indeterminate","name":"In Progress"}}', "CHANGED FIELD: fields.status"),
            ("a list is sorted (criterion 3)", 'idChecklists: ["65f0000000000000000000c2", "65f0000000000000000000c1"]', 'idChecklists: ["65f0000000000000000000c1", "65f0000000000000000000c2"]', "CHANGED FIELD: idChecklists"),
            ("a long value is summarised: the customer-impact text is cut to one word (criterion 3)", '{"text": "High: 3 enterprise accounts are waiting"}', '{"text": "High"}', "CHANGED FIELD: customFieldItems"),
            ("an empty string becomes null (criterion 3)", 'fields.description: ""', "fields.description: null", "CHANGED FIELD: fields.description"),
            ("trailing spaces are trimmed from a canonical title that a field is rebuilt from", 'title: "Export report as PDF  "', 'title: "Export report as PDF"', "CHANGED FIELD: name is rebuilt from the canonical field title"),
            ("the order of the fields is lost", 'field_order: ["id", "node_id", "number", ', 'field_order: ["node_id", "id", "number", ', "ORDER: the fields are all there"),
            ("a field is invented that the source never had", "pos: 1e3\n", 'pos: 1e3\ninvented: "x"\n', "EXTRA FIELD: invented"),
        ]
        for title, old, new, expected in cases:
            ok = normalized.count(old) >= 1
            said = []
            if ok:
                fidelity.check(sources, normalized.replace(old, new, 1), said.append)
            found = [one.replace("fidelity:     ", "") for one in said if one.startswith("fidelity:     ")]
            log.out("  CASE: %s" % title, *["    reported: %s" % fidelity.show(one) if len(one) < 200 else "    reported: %s" % one[:200] for one in found] or ["    reported: NOTHING"])
            log.check("%s: reported" % title.split(":")[0], ok and any(expected in one for one in found))
        cut = normalized[:normalized.index("## github:I_kwFIX0202")]
        said = []
        fidelity.check(sources, cut, said.append)
        log.out("  CASE: a whole normalized record is missing", *["    reported: %s" % one.replace("fidelity: ", "").strip() for one in said if "I_kwFIX0202" in one or "MISSING RECORD" in one])
        log.check("a whole normalized record missing: reported", any("MISSING RECORD" in one for one in said))
        said = []
        code = fidelity.check("# no records\n", "# no records either\n", said.append)
        log.check("a check given two files with no records in them does not pass. It says there is nothing to check", code != 0 and "nothing to check" in said[-1])

        log.part("PART 5. A field the mapping has never heard of",
                 "A new field, customerTier, is added to the Trello card's source record in memory. The mapping does not list it. The record is normalized and checked.")
        more = sources.replace('  "pos": 65535.5,\n', '  "pos": 65535.5,\n  "customerTier": "gold",\n')
        fresh = fidelity.render([fidelity.normalize_one(h, s, b, fidelity.status_map_of(more)) for h, s, b in fidelity.source_records(more)], fidelity.LATEST)
        said = []
        code = fidelity.check(more, fresh, said.append)
        log.out(*[one for one in said if "customerTier" in one or "62c0000000000000000000a1" in one])
        log.check("it is preserved as sent, the record still rebuilds identically, and the check names it as not yet considered (criterion 2)",
                  code == 0 and '\ncustomerTier: "gold"\n' in fresh and any("NOTE: the field trello customerTier" in one for one in said))

        log.part("PART 6. The mapping's two versions (stretch goal)",
                 "Version 1 had no canonical due date: every due date was preserved only. Version 2 made due_at canonical. The same sources are normalized under each.")
        for version in (1, 2):
            out = os.path.join(scratch, "normalized-v%d.md" % version)
            log.run(["normalize", "--out", out, "--mapping-version", str(version)], "normalize --out SCRATCH/normalized-v%d.md --mapping-version %d" % (version, version))
            code, said = log.run(["check", "--normalized", out], "check --normalized SCRATCH/normalized-v%d.md" % version)
            log.check("under version %d every record rebuilds identically" % version, code == 0 and len([one for one in said if "identical to the original, character for character" in one]) == 6)
        first, second = read(os.path.join(scratch, "normalized-v1.md")), read(os.path.join(scratch, "normalized-v2.md"))
        import re
        strip = lambda text: re.findall(r"### Preserved source fields.*?```text\n(.*?)```", text, re.S)
        log.check("version 1 has no canonical due_at, and version 2 has one for the Jira story and the Trello card", "\ndue_at:" not in first and second.count('\ndue_at: "2026-12-0') == 2)
        log.check("promoting the field changed nothing that is preserved: the preserved sections of the two versions are the same, line for line", strip(first) == strip(second) and len(strip(first)) == 6)

        log.part("PART 7. Preserved fields that more than one system has (stretch goal)", "From the check's output in part 1:")
        code, said = 0, []
        fidelity.check(sources, normalized, said.append)
        shared = [one.replace("fidelity: PRESERVED IN MORE THAN ONE SYSTEM: ", "  ") for one in said if "PRESERVED IN MORE THAN ONE SYSTEM" in one]
        log.out(*shared)
        log.check("the check reports them, and the one preserved in all three systems is the description", len(shared) >= 4 and any(one.count("`") == 6 and "description" in one for one in shared))
        log.check("the scenario's custom field is not among them: only Trello has it", not any("customFieldItems" in one for one in shared))
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    log.lines += ["", "RESULT: %s" % ("%d OF %d CHECKS FAILED." % (len(log.failed), log.count) if log.failed else "ALL CHECKS PASSED. %d checks." % log.count)]
    os.makedirs(LOGS, exist_ok=True)
    with open(os.path.join(LOGS, "roundtrip-check.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(log.lines) + "\n")
    print("roundtrip-check.txt: %s" % log.lines[-1])
    for label in log.failed:
        print("  FAILED: %s" % label)
    return 1 if log.failed else 0


if __name__ == "__main__":
    sys.exit(main())
