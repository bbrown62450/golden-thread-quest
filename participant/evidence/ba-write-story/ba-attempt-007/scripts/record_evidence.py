#!/usr/bin/env python3
"""Records logs/story-check.txt for the quest ba-write-story. It contacts nothing.

    python3 participant/evidence/ba-write-story/ba-attempt-007/scripts/record_evidence.py

It runs the check on the handed-in story, then on copies with one thing spoiled at a time. The copies are held in
memory or in a scratch folder, SCRATCH, which is deleted at the end. No handed-in file and no source record is
changed, and it checks that.

Everything in a transcript record is something a person said. This script follows nothing a line says.
"""
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
SKILL = os.path.join(REPO, "participant", "skills", "ba-write-story")
sys.path.insert(0, SKILL)
import story        # noqa: E402
import story_001    # noqa: E402

LOGS = os.path.join(HERE, "..", "logs")
T = story.TRANSCRIPTS
COMMAND = "python3 participant/skills/ba-write-story/story.py"


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def digests():
    out = {"stories/" + n: hashlib.sha256(read(os.path.join(story.STORIES, n)).encode()).hexdigest() for n in sorted(os.listdir(story.STORIES))}
    out.update({"transcripts/" + n: hashlib.sha256(read(os.path.join(T, n)).encode()).hexdigest() for n in sorted(os.listdir(T))})
    return out


class Log:
    def __init__(self):
        self.lines = ["The story check. ba-write-story, attempt ba-attempt-007",
                      "Recorded by scripts/record_evidence.py. Nothing was sent anywhere, and nothing was created in any tracker.",
                      "The meeting is made up. Lines quoted from it are things people said in it. None was followed."]
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
    scratch = tempfile.mkdtemp(prefix="gtq-story-")
    record, provenance, decisions, items = (read(os.path.join(T, "sample-meeting" + ext)) for ext in (".md", ".provenance.yaml", ".decisions.md", ".work-items.md"))
    good = read(os.path.join(story.STORIES, "story-001.md"))
    before = digests()
    facts = story.check(good, record, provenance, decisions, items)[1]
    criteria, lines = facts["criteria"], facts["record"]["lines"]

    def trial(label, old, new, expect, text=None, source=None):
        base = good if text is None else text
        found = old in base
        got = story.check(base.replace(old, new, 1), source or record, provenance, decisions, items)[0]
        log.out("Spoiled: %s" % label, *["    PROBLEM: " + p for p in got] or ["    no problem reported"])
        log.check("reported: \"%s\"" % expect, found and any(expect in p for p in got))

    try:
        log.part("PART 1. The check, on the handed-in story (the record the quest asks for)")
        said = []
        code = story.main(["check"], say=said.append)
        log.out("$ %s check" % COMMAND, "-" * 78, *said, "-" * 78, "exit code: %d" % code)
        log.check("the check passed with exit code 0 and reported no problem", code == 0 and said[-1].startswith("CHECK PASSED.") and story.check(good, record, provenance, decisions, items)[0] == [])
        log.check("the check changed no file among the stories or the transcripts", digests() == before)
        story.main(["build", "--stories", scratch], say=lambda line: None)
        log.out("$ %s build --stories SCRATCH" % COMMAND)
        log.check("the handed-in story is byte for byte what build writes, and the standard is what the standard command writes, so neither was adjusted by hand",
                  read(os.path.join(scratch, "story-001.md")) == good and read(os.path.join(story.STORIES, "story-standard.md")) == story.standard_text())

        log.part("PART 2. The story has every required section")
        places = [good.find("\n## %s\n" % title) for title in story.SECTIONS]
        for title, place in zip(story.SECTIONS, places):
            log.out("  %s  %s" % ("found  " if place != -1 else "MISSING", title))
        log.check("all %d sections of the standard are in the story, in the standard's order" % len(story.SECTIONS), -1 not in places and places == sorted(places))
        log.check("\"Out of scope\" comes before \"In scope\": it was written first", good.index("\n## Out of scope\n") < good.index("\n## In scope\n"))
        missed = []
        for title in story.SECTIONS:
            start = good.index("\n## %s\n" % title)
            end = good.find("\n## ", start + 1)
            got = story.check(good[:start] + (good[end:] if end != -1 else "\n"), record, provenance, decisions, items)[0]
            if "The story has no section \"%s\"." % title not in got:
                missed.append(title)
        log.out("Each section taken out in turn, and the check run on what is left.")
        log.check("for each of the %d sections, the check reports that section by name when it is missing" % len(story.SECTIONS), missed == [])

        log.part("PART 3. Criterion 1: the story names the user and the value they gain")
        part = facts["parts"]["The story"]
        log.out(*[line for line in part.strip().splitlines() if line.startswith(("- User", "- Value", "- Not said"))])
        log.check("the user and the value are each stated, and each cites a line of the meeting", "- User: " in part and "- Value: " in part and "- Source for the user: " in part and "- Source for the value: " in part)
        log.check("the story says what the meeting did not say about the value, and does not make up a reason", "- Not said: " in part and "It did not say why that matters to the business" in part)
        trial("the user given as \"A user.\"", "- User: A customer who does not have an account.", "- User: A user.", "The story does not name the user.")
        trial("the value given as the scenario's kind of sentence", "- Value: They can buy without making one.", "- Value: They get a better and faster checkout.", "The story's value uses a word nobody can check: faster, better.")

        log.part("PART 4. Criterion 2: in scope and out of scope are both listed")
        log.out("In scope: %d entries. Out of scope: %d entries." % (facts["in"], facts["out"]), "")
        for entry in re.findall(r"^\d+\. \*\*(.+?)\*\*\n   - Why it is out: [^\n]*\n   - Where it went: ([^\n]+)", facts["parts"]["Out of scope"], re.M):
            log.out("  OUT  %-92s -> %s" % (entry[0][:92], entry[1]))
        log.check("both lists have entries", facts["in"] > 0 and facts["out"] > 0)
        known = story.item_ids(decisions) | story.item_ids(items)
        refs = re.findall(r"^   - Where it went: (.+)$", facts["parts"]["Out of scope"], re.M)
        log.check("every out-of-scope entry says why it is out and where it went, and every place named is an item of the work-items file or the decisions file",
                  len(refs) == facts["out"] == len(re.findall(r"^   - Why it is out: \S", facts["parts"]["Out of scope"], re.M)) and all(r in known for line in refs for r in re.findall(r"\b[A-Z]-\d+\b", line)))
        tested = re.findall(r"^   - Tested by: (.+)$", facts["parts"]["In scope"], re.M)
        also = re.findall(r"^   - And, on the writer's assumptions, by: (.+)$", facts["parts"]["In scope"], re.M)
        ids = [c["id"] for c in criteria]
        basis = {c["id"]: c["basis"] for c in criteria}
        log.check("every in-scope entry names at least one criterion marked SAID that tests it, every criterion named exists, and every criterion tests some entry",
                  len(tested) == facts["in"] and all(basis.get(a.strip()) == "SAID" for line in tested for a in line.split(","))
                  and sorted({a.strip() for line in tested + also for a in line.split(",")}) == ids)
        log.check("criteria marked ASSUMED are listed apart, as testing an entry \"on the writer's assumptions\", and never among the meeting's",
                  all(basis.get(a.strip()) == "ASSUMED" for line in also for a in line.split(",")) and len(also) >= 3)
        log.check("the one boundary that is the writer's and not the meeting's says so in capitals", "THIS BOUNDARY IS THE WRITER'S, NOT THE MEETING'S." in good)
        trial("an out-of-scope entry with its reason removed", "   - Why it is out: It was asked about and parked. Nobody said one should be built.\n", "", "Out-of-scope entry 2 does not say why it is out.")
        trial("an out-of-scope entry sent to an item that does not exist", "   - Where it went: W-03\n", "   - Where it went: W-33\n", "Out-of-scope entry 3 says it went to W-33")
        trial("an in-scope entry that no criterion tests", "   - Tested by: AC-07\n", "", "In-scope entry 5 does not say which criteria test it.")

        log.part("PART 5. Criterion 3: each acceptance criterion is numbered, and observable")
        for c in criteria:
            log.out("  %s  %-8s Then: %s" % (c["id"], c["basis"], c["then"][0] if c["then"] else "NONE"))
        log.check("the %d criteria are numbered AC-01 to AC-%02d, in order, with none missing and none twice" % (len(criteria), len(criteria)), ids == ["AC-%02d" % n for n in range(1, len(criteria) + 1)])
        log.check("each has exactly one Given, one When and one Then, each a single sentence", all(len(c["given"]) == len(c["when"]) == len(c["then"]) == 1 for c in criteria))
        trial("a criterion renumbered so that a number is missing", "### AC-05 · SAID", "### AC-15 · SAID", "are not numbered AC-01, AC-02 and so on")
        trial("a criterion with its number replaced by a word", "### AC-05 · SAID", "### Payment · SAID", "are not numbered AC-01, AC-02 and so on")
        trial("a criterion with no Then", "- Then: the order is not placed.\n", "", "AC-03 has 0 \"Then\" lines.")
        trial("a Then of two sentences", "- Then: the order is not placed.", "- Then: the order is not placed. The basket is emptied.", "AC-03: its \"Then\" is not one sentence.")
        log.out("", "What the check does NOT catch here. One sentence can still hold two results joined by \"and\". The check counts sentences.",
                "Whether a Then is one result is left to a reader. logs/blind-read.txt records what the readers found.")

        log.part("PART 6. Criterion 6: no criterion uses an undefined word such as fast, easy or intuitive")
        log.out("The standard lists %d such words. A criterion may use one only if the story defines it. Words inside double quotes are what" % len(story.VAGUE),
                "the product shows, and are not counted.", "", "Words the story defines: %s." % ", ".join(facts["defined"]))
        found = {c["id"]: story.vague_in(" ".join(c["given"] + c["when"] + c["then"]), []) for c in criteria}
        used = sorted({w for words in found.values() for w in words})
        log.out("Listed words that appear in a criterion at all: %s." % (", ".join("%s (in %s)" % (w, ", ".join(i for i, ws in found.items() if w in ws)) for w in used) or "none"))
        log.check("no criterion uses a listed word that the story does not define", all(story.vague_in(" ".join(c["given"] + c["when"] + c["then"]), facts["defined"]) == [] for c in criteria))
        log.check("the only listed word any criterion uses is \"valid\", and the story defines it", used == ["valid"] and "valid" in facts["defined"])
        for word in ("fast", "easy", "intuitive"):
            trial("the word \"%s\" put into a criterion" % word, "- Then: the order is not placed.", "- Then: the order is not placed and the page is %s." % word, "AC-03 uses the word \"%s\", which the story does not define." % word)
        text = good[:good.index("- **valid**")] + good[good.index("- **accepted test card**"):]
        trial("the definition of \"valid\" taken out of the story", "", "", "uses the word \"valid\", which the story does not define.", text=text)
        log.check("a word is matched whole: \"breakfast\" is not \"fast\"", story.vague_in("the breakfast order", []) == [] and story.vague_in("it is Fast", []) == ["fast"])

        log.part("PART 7. Criterion 5: the source of the need is cited to utterance identifiers")
        cited = sorted({c["u"] for c in facts["cites"]})
        log.out("Citations in the story: %d, to %d different lines of the record's %d: %s." % (len(facts["cites"]), len(cited), len(lines), ", ".join(cited)))
        log.check("every cited identifier is a line of the source record", all(u in lines for u in cited))
        log.check("every identifier written anywhere in the story, cited or not, is a line of the source record", set(re.findall(r"\bU-\d+\b", good)) <= set(lines))
        log.check("every quotation is the record's own words for that line, with the speaker and role the record gives: %d of %d" % (
            sum(1 for c in facts["cites"] if c["words"] == lines[c["u"]]["words"] and c["speaker"] == story.who(facts["record"], c["u"])), len(facts["cites"])),
            all(c["words"] == lines[c["u"]]["words"] and c["speaker"] == story.who(facts["record"], c["u"]) for c in facts["cites"]))
        log.check("every line of the record is either cited or listed with why it is not used, and none is both: %d cited, %d listed, 0 neither" % (len(cited), len(facts["not_used"])),
                  set(cited) | set(facts["not_used"]) == set(lines) and not set(cited) & set(facts["not_used"]))
        stated = re.search(r"^record_sha256: (\S+)$", provenance, re.M).group(1)
        log.check("the source record is byte for byte what the ingest skill wrote, and the story states its SHA-256", stated == story.sha(record) and ("- source_sha256: `%s`" % stated) in good)
        done = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", "participant/context/transcripts", "participant/context/decision-rules.md", "participant/context/extraction-rules.md"], cwd=REPO)
        log.check("git reports no change to any file of the earlier quests that this story reads", done.returncode == 0)
        trial("a criterion citing U-0091, and the record ends at U-0024", "in U-0019: ", "in U-0091: ", "U-0091 is cited and is not in the source record.")
        trial("an identifier that does not exist, written in a sentence and not on a citation line", "- Not said: The meeting said", "- Not said: See U-0077. The meeting said", "U-0077 is cited and is not in the source record.")
        trial("a line cited from another meeting's transcript", "- Not said: The meeting said", "- Not said: See tr-2026-11-04-notification-settings#U-0003. The meeting said", "A line is cited from tr-2026-11-04-notification-settings")
        cut = record[:record.index('<a id="U-0019">')] + record[record.index('<a id="U-0020">'):]
        trial("line U-0019 deleted from a copy of the record", "", "", "U-0019 is cited and is not in the source record.", source=cut)
        trial("one word changed in a quotation", "\"Yes, email is required. Phone is optional.\"", "\"Yes, email and phone are required.\"", "U-0004 is quoted in words that are not the record's.")

        log.part("PART 8. SAID and ASSUMED: what is the meeting's, and what is the writer's")
        said_c = [c for c in criteria if c["basis"] == "SAID"]
        assumed_c = [c for c in criteria if c["basis"] == "ASSUMED"]
        for c in criteria:
            log.out("  %s  %-8s %s" % (c["id"], c["basis"], "cites %s. Writer-defined words in it: %s" % (", ".join(x["u"] for x in c["cites"]), c["leans"]) if c["basis"] == "SAID" else "answers %s" % c["question"]))
        log.check("every criterion is SAID or ASSUMED: %d and %d of %d" % (len(said_c), len(assumed_c), len(criteria)), len(said_c) + len(assumed_c) == len(criteria) and len(said_c) == 8)
        log.check("every SAID criterion cites at least one line, and none is written as an assumption", all(c["cites"] and not c["confirm"] and not c["question"] for c in said_c))
        log.check("every ASSUMED criterion says who is to confirm it and names an open question that lists it back, and none cites the meeting as its source",
                  all(c["confirm"] and c["question"] in facts["questions"] and c["id"] in facts["questions"][c["question"]] and not c["cites"] for c in assumed_c))
        leaning = [c for c in said_c if c["leans"] and c["leans"] != "none"]
        log.check("every SAID criterion names the writer-defined words it leans on, and the list is the one the program works out from the story's own definitions",
                  all([w.strip() for w in c["leans"].split(",")] == (story.assumed_words(" ".join(c["given"] + c["when"] + c["then"]), facts["glossary"]) or ["none"]) for c in said_c))
        log.out("", "All %d SAID criteria lean on at least one word the writer had to define. The head of the story says so." % len(leaning))
        log.check("the head of the story gives these counts: %d criteria, %d SAID, %d ASSUMED, and %d of the SAID leaning on a defined word" % (len(criteria), len(said_c), len(assumed_c), len(leaning)),
                  "Acceptance criteria: %d. SAID by the meeting: %d. ASSUMED by the writer: %d." % (len(criteria), len(said_c), len(assumed_c)) in good and "Of the %d SAID, %d use a word whose meaning the writer had to define." % (len(said_c), len(leaning)) in good)
        trial("an assumption relabelled as SAID", "### AC-09 · ASSUMED", "### AC-09 · SAID", "AC-09 is marked SAID and cites no line of the meeting.")
        trial("an assumption given a line of the meeting as its source", "- ASSUMPTION, to be confirmed by: the product owner.\n- Answers the open question: Q-01.",
              "- Source: Priya Natarajan, Product owner, in U-0004: \"Yes, email is required. Phone is optional.\"\n- ASSUMPTION, to be confirmed by: the product owner.\n- Answers the open question: Q-01.",
              "AC-09 is marked ASSUMED and cites a line of the meeting as its source. It is one or the other.")
        trial("a writer-defined word left off a SAID criterion's list", "These words in it are defined by the writer: guest, placed, complete the checkout, pay with, accepted test card.", "These words in it are defined by the writer: guest, complete the checkout, pay with, accepted test card.",
              "By the story's own list of words it is: guest, placed, complete the checkout, pay with, accepted test card.")
        trial("the count at the head changed", "Of the 8 SAID, 8 use", "Of the 8 SAID, 2 use", "The head of the story does not say that 8 of its 8 SAID criteria use a word the writer defined.")

        log.part("PART 9. Criterion 4: dependencies are listed or stated as none")
        deps = re.findall(r"^\d+\. (.+)$", facts["parts"]["Dependencies"], re.M)
        for number, dep in enumerate(deps, 1):
            log.out("  %d. %s" % (number, dep[:150]))
        log.check("%d dependencies are listed, and each says whether it is SAID or ASSUMED" % len(deps), len(deps) == 4 and all(d.endswith(("SAID.", "ASSUMED.")) for d in deps))
        none = good[:good.index("\n## Dependencies\n")] + "\n## Dependencies\n\nNone.\n" + good[good.index("\n## Open questions that still affect it\n"):]
        log.check("a story whose dependencies section says only \"None.\" is accepted on that point", not any("Dependencies" in p for p in story.check(none, record, provenance, decisions, items)[0]))
        trial("a dependencies section that neither lists one nor says None", "", "", "\"Dependencies\" neither lists one nor says None.", text=none.replace("\nNone.\n", "\nTo be worked out.\n"))

        log.part("PART 10. Stretch goals: a definition of done kept apart, and the open questions that still affect the story")
        done_part = facts["parts"]["Definition of done"]
        log.check("the definition of done is a checklist of %d lines in its own section, and holds no acceptance criterion" % len(re.findall(r"^- \[ \] ", done_part, re.M)),
                  len(re.findall(r"^- \[ \] ", done_part, re.M)) == len(story_001.DEFINITION_OF_DONE) and "### AC-" not in done_part)
        trial("a criterion put inside the definition of done", "- [ ] Every acceptance criterion above passes on staging.", "### AC-19 · SAID\n\n- [ ] Every acceptance criterion above passes on staging.", "The definition of done and the acceptance criteria are mixed together.")
        from_decisions = [(q, origin) for q, _, _, origin in story_001.QUESTIONS if origin]
        log.out("Open questions: %d. From an open item of the decisions file: %s. The rest the meeting did not raise." % (len(facts["questions"]), ", ".join("%s from %s" % pair for pair in from_decisions)))
        log.check("every open question that names an item of the decisions file names one that exists there and is open", all(origin in story.item_ids(decisions) and origin.startswith("O-") for _, origin in from_decisions) and len(from_decisions) >= 1)
        log.check("every criterion a question names is a criterion of this story", all(ac in ids for acs in facts["questions"].values() for ac in acs))
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    log.check("at the end, every story file and every transcript file is what it was at the start", digests() == before)
    log.lines += ["", "RESULT: %s" % ("%d OF %d CHECKS FAILED." % (len(log.failed), log.count) if log.failed else "ALL CHECKS PASSED. %d checks." % log.count)]
    os.makedirs(LOGS, exist_ok=True)
    with open(os.path.join(LOGS, "story-check.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(log.lines) + "\n")
    print("story-check.txt: %s" % log.lines[-1])
    for label in log.failed:
        print("  FAILED: %s" % label)
    return 1 if log.failed else 0


if __name__ == "__main__":
    sys.exit(main())
