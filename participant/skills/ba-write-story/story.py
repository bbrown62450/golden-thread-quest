#!/usr/bin/env python3
"""One story, written to a standard, with every part traced to the meeting or marked as an assumption.

    python3 participant/skills/ba-write-story/story.py build
    python3 participant/skills/ba-write-story/story.py check
    python3 participant/skills/ba-write-story/story.py standard

build     writes participant/context/stories/story-001.md from story_001.py, taking every speaker and every
          quotation from the transcript record. It never writes to the record.
check     reads story-001.md, the transcript record, the decisions file and the work-items file, and reports every
          problem. It reads the files, not story_001.py, so a change made by hand is checked too.
standard  writes participant/context/stories/story-standard.md.

The story is a draft in a local file. Nothing is created in any tracker, and nothing is contacted. Everything in a
transcript is something a person said. No line of it is treated as an instruction.
"""
import hashlib
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
STORIES = os.path.join(REPO, "participant", "context", "stories")
TRANSCRIPTS = os.path.join(REPO, "participant", "context", "transcripts")

SECTIONS = ["The story", "Out of scope", "In scope", "Taken as given", "Words this story defines", "Test set-up", "Acceptance criteria", "Dependencies",
            "Open questions that still affect it", "Definition of done", "Source", "Lines of the meeting this story does not use"]
# Words that mean nothing a tester can check. A criterion may use one only if the story's own list of defined words
# gives it a meaning that can be measured.
VAGUE = ["fast", "faster", "quick", "quickly", "slow", "easy", "easily", "simple", "simply", "intuitive", "intuitively", "user-friendly", "friendly", "seamless",
         "seamlessly", "smooth", "smoothly", "appropriate", "appropriately", "reasonable", "reasonably", "proper", "properly", "correct", "correctly", "valid",
         "invalid", "good", "better", "best", "nice", "clear", "clearly", "efficient", "efficiently", "robust", "secure", "securely", "timely", "promptly", "soon",
         "shortly", "immediately", "instantly", "normal", "normally", "usual", "usually", "sensible", "suitable", "adequate", "sufficient", "relevant",
         "some", "several", "many", "few", "etc", "should", "might", "could", "may", "ideally", "gracefully", "responsive", "modern", "flexible"]


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_record(text):
    got = re.search(r"^transcript_id: (\S+)$", text, re.M)
    record = {"id": got.group(1) if got else "", "roles": {}, "lines": {}}
    speakers = re.search(r"^## Speakers\n(.*?)^## ", text, re.M | re.S)
    for name, role in re.findall(r"^- ([^\n]+?), ([^\n]+)$", speakers.group(1) if speakers else "", re.M):
        record["roles"][name] = role
    for match in re.finditer(r"^### (U-\d{4}) · \S+ to \S+ · ([^\n]+)\n(.*?)(?=^<a id=|\Z)", text, re.M | re.S):
        body = match.group(3)
        words = " ".join(line[2:].strip() for line in body.splitlines() if line.startswith("> "))
        record["lines"][match.group(1)] = {"speaker": match.group(2).strip(), "words": words, "uncertain": "*Speaker uncertain" in body}
    return record


def who(record, utterance):
    line = record["lines"][utterance]
    role = record["roles"].get(line["speaker"], "")
    return line["speaker"] + (", identity uncertain" if line["uncertain"] else ", %s" % role if role else "")


def item_ids(text):
    return set(re.findall(r"^### ([A-Z]-\d+) · ", text, re.M))


def vague_in(text, defined):
    """The vague words in a piece of text that the story does not define. Words inside double quotes are what the
    product shows, not the criterion's own words, and are not looked at."""
    bare = re.sub(r"\"[^\"]*\"", " ", text).lower()
    found = []
    for word in VAGUE:
        if word in defined:
            continue
        if re.search(r"(?<![\w-])%s(?![\w-])" % re.escape(word), bare):
            found.append(word)
    return found


# ---------------------------------------------------------------- build

def cite(record, label, utterance):
    return "- %s: %s, in %s: \"%s\"" % (label, who(record, utterance), utterance, record["lines"][utterance]["words"])


def assumed_words(text, glossary):
    """The words of the glossary whose definition is assumed and that a piece of text uses."""
    low, found = text.lower(), set()
    for word, basis in sorted(glossary, key=lambda g: -len(g[0])):     # the longest first, so "not placed" is not also "placed"
        if word in low:
            low = low.replace(word, " ")
            if basis == "assumed":
                found.add(word)
    return [word for word, _ in glossary if word in found]


def render(content, record, record_text):
    said = [c for c in content.CRITERIA if c["basis"] == "SAID"]
    assumed = [c for c in content.CRITERIA if c["basis"] == "ASSUMED"]
    glossary = [(word, basis) for word, _, basis, _ in content.GLOSSARY]
    leaning = [c for c in said if assumed_words(" ".join((c["given"], c["when"], c["then"])), glossary)]
    cited = sorted({u for c in said for u in c["lines"]} | {u for _, lines, _ in content.IN_SCOPE for u in lines} | {u for o in content.OUT_OF_SCOPE for u in o["lines"]}
                   | set(content.STORY["user"][1]) | set(content.STORY["value"][1]) | {u for g in content.GLOSSARY for u in g[3]} | {u for d in content.DEPENDENCIES for u in d[2]})
    out = ["# Story 001: %s" % content.STORY["title"], "",
           "A draft for a person to decide on. **Nothing here was created in any tracker.** The meeting it comes from is made up.", "",
           "- source_record: `participant/context/transcripts/%s.md`" % content.SOURCE,
           "- transcript_id: `%s`" % record["id"], "- source_sha256: `%s`" % sha(record_text),
           "- work_item: %s of `participant/context/transcripts/%s.work-items.md`" % (content.WORK_ITEM, content.SOURCE),
           "- standard: `participant/context/stories/story-standard.md`", "",
           "Written by `participant/skills/ba-write-story/story.py build`. The story was composed by an AI assistant (Claude). Every",
           "speaker and every quotation is copied from the transcript record by the program.", "",
           "**How much of this is the meeting's.** Acceptance criteria: %d. SAID by the meeting: %d. ASSUMED by the writer: %d." % (len(content.CRITERIA), len(said), len(assumed)),
           "Of the %d SAID, %d use a word whose meaning the writer had to define." % (len(said), len(leaning)), "",
           "- A criterion marked **SAID** states a requirement the meeting gave, and quotes the lines. How a tester sees the result is",
           "  usually not something the meeting gave. Where a SAID criterion leans on a word the writer defined, it says which.",
           "- A criterion marked **ASSUMED** is the writer's proposal, put in so that the story can be tested. The meeting did not",
           "  decide it. It stands only until %s confirms or replaces it." % content.OWNER,
           "- The meeting gave no test data beyond agreeing that a test address may be used. Everything else under \"Test set-up\",",
           "  and everything under \"Taken as given\", is the writer's.",
           "- **One of the product owner's three acceptance criteria, the linking offer, is not in this story.** Taking it out is the",
           "  writer's choice and not the meeting's. See the first entry under \"Out of scope\", and open question Q-07.", "",
           "## The story", "",
           "- User: %s" % content.STORY["user"][0]] + [cite(record, "Source for the user", u) for u in content.STORY["user"][1]]
    out += ["- Value: %s" % content.STORY["value"][0]] + [cite(record, "Source for the value", u) for u in content.STORY["value"][1]]
    out += ["- Not said: %s" % content.STORY["value_note"], "",
            "## Out of scope", "",
            "Written first, before any criterion. Each says why it is out and where it went.", ""]
    for number, item in enumerate(content.OUT_OF_SCOPE, 1):
        out += ["%d. **%s**" % (number, item["text"]), "   - Why it is out: %s" % item["why"],
                "   - Where it went: %s" % (", ".join(item["where"]) if item["where"] else "nowhere. The meeting did not discuss it")]
        out += ["   " + cite(record, "The line it turns on", u) for u in item["lines"]]
    out += ["", "## In scope", "", "Each says which criteria test it.", ""]
    basis_of = {c["id"]: c["basis"] for c in content.CRITERIA}
    for number, (text, lines, tested) in enumerate(content.IN_SCOPE, 1):
        mine = [ac for ac in tested if basis_of.get(ac) != "ASSUMED"]
        theirs = [ac for ac in tested if basis_of.get(ac) == "ASSUMED"]
        out += ["%d. %s" % (number, text), "   - Tested by: %s" % ", ".join(mine)]
        out += ["   - And, on the writer's assumptions, by: %s" % ", ".join(theirs)] if theirs else []
        out += ["   " + cite(record, "Source", u) for u in lines]
    out += ["", "## Taken as given", "",
            "What the story takes as already there. **None of this was said in the meeting.** It is ASSUMED.", ""]
    out += ["%d. %s" % (number, text) for number, text in enumerate(content.TAKEN_AS_GIVEN, 1)]
    out += ["", "## Words this story defines", "",
            "A criterion uses these words in these meanings and no other.", ""]
    for word, meaning, basis, lines in content.GLOSSARY:
        out += ["- **%s**: %s. %s" % (word, meaning, "SAID." if basis == "said" else "ASSUMED: the meeting did not define it.")]
        out += ["  " + cite(record, "Source" if basis == "said" else "The line it is read from", u) for u in lines]
    out += ["", "## Test set-up", "",
            "The data a tester uses, by the names the criteria use. **ASSUMED**, all of it, except that a test address was agreed.", "",
            "| Name | What it is |", "|---|---|"]
    out += ["| %s | %s |" % row for row in content.TEST_SETUP]
    out += ["", "## Acceptance criteria", "",
            "Each is one starting state, one action and one result a person can see or read.", ""]
    for c in content.CRITERIA:
        out += ["### %s · %s" % (c["id"], c["basis"]), "", "- Given: %s." % c["given"], "- When: %s." % c["when"], "- Then: %s." % c["then"]]
        if c["basis"] == "SAID":
            out += [cite(record, "Source", u) for u in c["lines"]]
            words = assumed_words(" ".join((c["given"], c["when"], c["then"])), glossary)
            out += ["- The requirement is the meeting's. These words in it are defined by the writer: %s." % (", ".join(words) if words else "none")]
            out += ["- Note: %s" % c["note"]] if c.get("note") else []
        else:
            out += ["- ASSUMPTION, to be confirmed by: %s." % content.OWNER, "- Answers the open question: %s." % c["question"]]
        out += [""]
    out += ["## Dependencies", ""]
    for number, (text, basis, lines) in enumerate(content.DEPENDENCIES, 1):
        out += ["%d. %s %s" % (number, text, "SAID." if basis == "said" else "ASSUMED.")]
        out += ["   " + cite(record, "Source" if basis == "said" else "The line it is read from", u) for u in lines]
    out += ["", "## Open questions that still affect it", "",
            "None of these has been put to anyone. Where a criterion is marked ASSUMED, it answers one of them for the time being.",
            "The others bear on the story with nothing standing in for an answer.", "",
            "| Question | Asks | Criteria that depend on the answer | Open item it comes from |", "|---|---|---|---|"]
    out += ["| %s | %s | %s | %s |" % (q, text, ", ".join(acs) or "none. It affects the story as a whole", origin or "none: the meeting did not raise it") for q, text, acs, origin in content.QUESTIONS]
    out += ["", "## Definition of done", "",
            "Kept apart from the acceptance criteria. The criteria say what the product does. This says how the team would know the",
            "work is finished. None of it is from the meeting.", ""]
    out += ["- [ ] %s" % line for line in content.DEFINITION_OF_DONE]
    out += ["", "## Source", "",
            "The need comes from one meeting, `%s`. The story cites %d of its lines: %s." % (record["id"], len(cited), ", ".join(cited)),
            "In full, a line is cited as `%s#U-0001`. Open the record and find the heading with that number." % record["id"],
            "", "## Lines of the meeting this story does not use", "",
            "Every line of the record is cited above or listed here with the reason, so that nothing was passed over unseen.", ""]
    out += ["- %s · %s: %s." % (u, record["lines"][u]["speaker"], why) for u, why in sorted(content.NOT_USED.items())]
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------- check

CITE = re.compile(r"^\s*- ([A-Z][^:\n]*?): ([^\n]+?), in (U-\d+): \"(.*)\"$", re.M)


def parse(text):
    """The parts of a story file, as written."""
    parts = {}
    chunks = re.split(r"^## (.+)$", text, flags=re.M)
    for title, body in zip(chunks[1::2], chunks[2::2]):
        parts[title.strip()] = body
    criteria = []
    for match in re.finditer(r"^### (\S+) · ([^\n]*)\n(.*?)(?=^### |\Z)", parts.get("Acceptance criteria", ""), re.M | re.S):
        body = match.group(3)

        def lines(label, body=body):
            return re.findall(r"^- %s: (.+)$" % label, body, re.M)
        question = re.search(r"^- Answers the open question: (Q-\d+)\.$", body, re.M)
        criteria.append({"id": match.group(1), "basis": match.group(2).strip(), "given": lines("Given"), "when": lines("When"), "then": lines("Then"),
                         "cites": [{"speaker": s, "u": u, "words": w} for _, s, u, w in CITE.findall(body)],
                         "confirm": bool(re.search(r"^- ASSUMPTION, to be confirmed by: \S", body, re.M)), "question": question.group(1) if question else "",
                         "leans": (re.search(r"^- The requirement is the meeting's\. These words in it are defined by the writer: (.+)\.$", body, re.M) or [None, None])[1]})
    glossary = [(w.lower(), "assumed" if "ASSUMED" in rest else "said") for w, rest in re.findall(r"^- \*\*(.+?)\*\*: (.+)$", parts.get("Words this story defines", ""), re.M)]
    defined = [w for w, _ in glossary]
    questions = {q: [a.strip() for a in acs.split(",") if a.strip().startswith("AC-")] for q, acs in re.findall(r"^\| (Q-\d+) \| [^|]+ \| ([^|]+) \|", parts.get("Open questions that still affect it", ""), re.M)}
    return parts, criteria, defined, questions, glossary


def check(story_text, record_text, provenance_text, decisions_text, items_text):
    """Returns (problems, facts). An empty list of problems means the check passes."""
    problems, record = [], read_record(record_text)
    lines = record["lines"]
    parts, criteria, defined, questions, glossary = parse(story_text)
    known = item_ids(decisions_text) | item_ids(items_text)

    def say(text):
        problems.append(text)

    # Every required section, in order.
    order = [title for title in re.findall(r"^## (.+)$", story_text, re.M)]
    for title in SECTIONS:
        if title not in parts:
            say("The story has no section \"%s\"." % title)
        elif not parts[title].strip():
            say("The section \"%s\" is empty." % title)
    if [t for t in order if t in SECTIONS] != [t for t in SECTIONS if t in order]:
        say("The story's sections are not in the order the standard gives.")

    # Criterion 1: the user and the value.
    story = parts.get("The story", "")
    for label in ("User", "Value"):
        got = re.search(r"^- %s: (.+)$" % label, story, re.M)
        if not got or len(got.group(1).split()) < 3:
            say("The story does not name the %s." % label.lower())
        elif vague_in(got.group(1), defined):
            say("The story's %s uses a word nobody can check: %s." % (label.lower(), ", ".join(vague_in(got.group(1), defined))))
        if not re.search(r"^- Source for the %s: " % label.lower(), story, re.M):
            say("The story's %s cites no line of the meeting." % label.lower())

    # Criterion 2: both lists, and every out-of-scope entry says why and where.
    for title in ("In scope", "Out of scope"):
        entries = re.findall(r"^\d+\. ", parts.get(title, ""), re.M)
        if not entries:
            say("\"%s\" lists nothing." % title)
    ids = [c["id"] for c in criteria]
    for entry in re.split(r"^(?=\d+\. )", parts.get("In scope", ""), flags=re.M)[1:]:
        number = entry.split(".")[0]
        tested = re.search(r"^   - Tested by: (.+)$", entry, re.M)
        also = re.search(r"^   - And, on the writer's assumptions, by: (.+)$", entry, re.M)
        named = [a.strip() for a in tested.group(1).split(",") if a.strip()] if tested else []
        extra = [a.strip() for a in also.group(1).split(",") if a.strip()] if also else []
        if not named:
            say("In-scope entry %s does not say which criteria test it." % number)
        basis = {c["id"]: c["basis"] for c in criteria}
        for ac in named + extra:
            if ac not in ids:
                say("In-scope entry %s says it is tested by %s, which is not a criterion of this story." % (number, ac))
            elif (basis[ac] == "ASSUMED") != (ac in extra):
                say("In-scope entry %s lists %s on the wrong line. A criterion marked ASSUMED is listed apart, as testing it on the writer's assumptions." % (number, ac))
        if not re.search(r"^   - Source: ", entry, re.M):
            say("In-scope entry %s cites no line of the meeting." % number)
    out_entries = re.split(r"^(?=\d+\. )", parts.get("Out of scope", ""), flags=re.M)[1:]
    for entry in out_entries:
        number = entry.split(".")[0]
        if not re.search(r"^   - Why it is out: \S", entry, re.M):
            say("Out-of-scope entry %s does not say why it is out." % number)
        where = re.search(r"^   - Where it went: (.+)$", entry, re.M)
        if not where:
            say("Out-of-scope entry %s does not say where it went." % number)
        else:
            for ref in re.findall(r"\b[A-Z]-\d+\b", where.group(1)):
                if ref not in known:
                    say("Out-of-scope entry %s says it went to %s, which is in neither the work-items file nor the decisions file." % (number, ref))

    # Criterion 3: numbered, and each one state, one action, one result. Criterion 6: no undefined vague word.
    if not criteria:
        say("The story has no acceptance criteria that could be read.")
    expected = ["AC-%02d" % n for n in range(1, len(criteria) + 1)]
    if [c["id"] for c in criteria] != expected:
        say("The acceptance criteria are not numbered AC-01, AC-02 and so on, in order with none missing: %s." % ", ".join(c["id"] for c in criteria))
    for c in criteria:
        for label, key in (("Given", "given"), ("When", "when"), ("Then", "then")):
            if len(c[key]) != 1:
                say("%s has %d \"%s\" lines. A criterion has exactly one." % (c["id"], len(c[key]), label))
            elif c[key][0].rstrip(".").count(". ") or not c[key][0].endswith("."):
                say("%s: its \"%s\" is not one sentence." % (c["id"], label))
        words = " ".join(c["given"] + c["when"] + c["then"])
        for word in vague_in(words, defined):
            say("%s uses the word \"%s\", which the story does not define. A tester cannot check it." % (c["id"], word))
        # Criterion 5 and the basis.
        if c["basis"] == "SAID":
            if not c["cites"]:
                say("%s is marked SAID and cites no line of the meeting." % c["id"])
            if c["confirm"] or c["question"]:
                say("%s is marked SAID and is also written as an assumption. It is one or the other." % c["id"])
            leaning = assumed_words(words, glossary)
            if c["leans"] is None:
                say("%s is marked SAID and does not say which of its words the writer defined." % c["id"])
            elif [w.strip() for w in c["leans"].split(",")] != (leaning or ["none"]):
                say("%s says the writer defined \"%s\" in it. By the story's own list of words it is: %s." % (c["id"], c["leans"], ", ".join(leaning) or "none"))
        elif c["basis"] == "ASSUMED":
            if c["cites"]:
                say("%s is marked ASSUMED and cites a line of the meeting as its source. It is one or the other." % c["id"])
            if not c["confirm"]:
                say("%s is marked ASSUMED and does not say who is to confirm it." % c["id"])
            if not c["question"]:
                say("%s is marked ASSUMED and does not name the open question it answers." % c["id"])
            elif c["question"] not in questions:
                say("%s answers %s, which is not in the list of open questions." % (c["id"], c["question"]))
            elif c["id"] not in questions[c["question"]]:
                say("%s answers %s, and %s does not list %s among the criteria that depend on it." % (c["id"], c["question"], c["question"], c["id"]))
        else:
            say("%s does not say whether it is SAID or ASSUMED." % c["id"])
    for q, acs in questions.items():
        for ac in acs:
            if ac not in [c["id"] for c in criteria]:
                say("%s names %s, which is not a criterion of this story." % (q, ac))

    # Criterion 4: dependencies listed, or stated as none.
    deps = parts.get("Dependencies", "")
    if not re.search(r"^\d+\. ", deps, re.M) and not re.search(r"^None\.", deps.strip(), re.M):
        say("\"Dependencies\" neither lists one nor says None.")
    for entry in re.findall(r"^\d+\. (.+)$", deps, re.M):
        if not entry.endswith(("SAID.", "ASSUMED.")):
            say("A dependency does not say whether it is SAID or ASSUMED: \"%s\"." % entry[:50])

    # Criterion 5: every identifier anywhere exists, every quotation is the record's, the record is as ingested.
    cites = [{"speaker": s, "u": u, "words": w} for _, s, u, w in CITE.findall(story_text)]
    everywhere = set(re.findall(r"\bU-\d+\b", story_text)) - {"U-0001"} | {c["u"] for c in cites}
    for utterance in sorted(everywhere):
        if utterance not in lines:
            say("%s is cited and is not in the source record." % utterance)
    for other in sorted(set(re.findall(r"\b(tr-[\w-]+)#U-\d+", story_text)) - {record["id"]}):
        say("A line is cited from %s, which is not this record." % other)
    for c in cites:
        if c["u"] in lines:
            if c["speaker"] != who(record, c["u"]):
                say("%s is given to \"%s\". The record gives it to \"%s\"." % (c["u"], c["speaker"], who(record, c["u"])))
            if c["words"] != lines[c["u"]]["words"]:
                say("%s is quoted in words that are not the record's." % c["u"])
    if not cites:
        say("The story cites no line of the meeting at all.")
    recorded = re.search(r"^record_sha256: (\S+)$", provenance_text, re.M)
    if not recorded or recorded.group(1) != sha(record_text):
        say("The source record has been changed since it was ingested: its SHA-256 is not the one in its provenance file.")
    stated = re.search(r"^- source_sha256: `(\S+)`$", story_text, re.M)
    if not stated or stated.group(1) != sha(record_text):
        say("The story was not made from the source record as it is now: the SHA-256 it states is not the record's.")
    item = re.search(r"^- work_item: (\S+) of ", story_text, re.M)
    if not item or item.group(1) not in item_ids(items_text):
        say("The story does not name a work item that is in the work-items file.")
    listed = re.search(r"The story cites (\d+) of its lines: ([U\-\d, ]+)\.", parts.get("Source", ""))
    used = sorted({c["u"] for c in cites})
    if not listed or int(listed.group(1)) != len(used) or listed.group(2).split(", ") != used:
        say("The \"Source\" section does not list exactly the lines the story cites: %s." % ", ".join(used))

    # The count at the head, and the definition of done kept apart.
    said_count = sum(1 for c in criteria if c["basis"] == "SAID")
    assumed_count = sum(1 for c in criteria if c["basis"] == "ASSUMED")
    if "Acceptance criteria: %d. SAID by the meeting: %d. ASSUMED by the writer: %d." % (len(criteria), said_count, assumed_count) not in story_text:
        say("The count at the head of the story is not the count of its criteria: %d, of which %d SAID and %d ASSUMED." % (len(criteria), said_count, assumed_count))
    leaning_count = sum(1 for c in criteria if c["basis"] == "SAID" and assumed_words(" ".join(c["given"] + c["when"] + c["then"]), glossary))
    if "Of the %d SAID, %d use a word whose meaning the writer had to define." % (said_count, leaning_count) not in story_text:
        say("The head of the story does not say that %d of its %d SAID criteria use a word the writer defined." % (leaning_count, said_count))
    # Every line of the record is cited or listed as not used, and never both.
    not_used = re.findall(r"^- (U-\d{4}) · (.+?): ", parts.get("Lines of the meeting this story does not use", ""), re.M)
    listed = [u for u, _ in not_used]
    for u in sorted(set(lines) - set(used) - set(listed)):
        say("%s is in the source record, and the story neither cites it nor lists it as not used." % u)
    for u in sorted(set(listed) & set(used)):
        say("%s is cited by the story and also listed as not used." % u)
    for u, speaker in not_used:
        if u in lines and speaker != lines[u]["speaker"]:
            say("%s is listed as not used under \"%s\". The record gives it to \"%s\"." % (u, speaker, lines[u]["speaker"]))
    if not [row for row in re.findall(r"^\| ([^|]+) \|", parts.get("Test set-up", ""), re.M) if row.strip() not in ("Name", "---")]:
        say("\"Test set-up\" gives no data.")
    done = parts.get("Definition of done", "")
    if not re.search(r"^- \[ \] ", done, re.M):
        say("\"Definition of done\" has no checklist.")
    if re.search(r"^### AC-", done, re.M) or re.search(r"^- \[ \] ", parts.get("Acceptance criteria", ""), re.M):
        say("The definition of done and the acceptance criteria are mixed together.")
    return problems, {"record": record, "criteria": criteria, "defined": defined, "questions": questions, "cites": cites, "parts": parts, "glossary": glossary, "not_used": listed,
                      "out": len(out_entries), "in": len(re.findall(r"^\d+\. ", parts.get("In scope", ""), re.M)), "deps": len(re.findall(r"^\d+\. ", deps, re.M))}


def summary(facts):
    record, criteria = facts["record"], facts["criteria"]
    out = ["Source record: transcript %s, %d utterances." % (record["id"], len(record["lines"])),
           "Sections required: %d. Found: %d." % (len(SECTIONS), sum(1 for s in SECTIONS if s in facts["parts"])),
           "In scope: %d entries. Out of scope: %d entries. Dependencies: %d. Open questions: %d. Words defined: %s." % (
               facts["in"], facts["out"], facts["deps"], len(facts["questions"]), ", ".join(facts["defined"]) or "none"),
           "Citations: %d, to %d different lines. Lines listed as not used: %d. Lines of the record neither cited nor listed: %d." % (
               len(facts["cites"]), len({c["u"] for c in facts["cites"]}), len(facts["not_used"]),
               len(set(record["lines"]) - {c["u"] for c in facts["cites"]} - set(facts["not_used"]))), "",
           "Acceptance criteria:"]
    for c in criteria:
        out.append("  %s  %-8s %s" % (c["id"], c["basis"], "cites " + ", ".join(x["u"] for x in c["cites"]) if c["cites"] else "answers %s" % (c["question"] or "NOTHING")))
    return out


# ---------------------------------------------------------------- the standard

def standard_text():
    out = ["# Story standard", "",
           "Written by `participant/skills/ba-write-story/story.py standard`, at the participant's direction, for the quest",
           "`ba-write-story`. The lists below are the lists the program checks.", "",
           "A story meets this standard when another person can tell, for every part of it, whether it came from the meeting or",
           "from the writer, and can write a test for every criterion from what the story itself gives.", "",
           "**What this standard cannot do.** A meeting that said little cannot be turned into a story that leaves nothing to ask.",
           "The writer can supply what is missing, and this standard makes them say so each time. It does not make the supplied",
           "parts right. A story that meets it is honest about its gaps. It may still have many.", "",
           "## 1. The sections, in this order", "",
           "| Section | What it holds |", "|---|---|",
           "| The story | the user, and the value they gain, each citing the meeting. And what the meeting did not say about the value |",
           "| Out of scope | what is not built. **Written first.** Each entry says why it is out and where it went |",
           "| In scope | what is built, each entry citing the meeting and naming the criteria that test it |",
           "| Taken as given | what the story assumes is already there. Marked as the writer's |",
           "| Words this story defines | any word a criterion uses in a particular meaning, each SAID or ASSUMED |",
           "| Test set-up | the data a tester uses, under the names the criteria use. Marked as the writer's |",
           "| Acceptance criteria | numbered AC-01, AC-02 and so on. Section 3 |",
           "| Dependencies | what the story cannot be built or tested without, or the word None |",
           "| Open questions that still affect it | every question an assumption answers for now, and any other that bears on the story |",
           "| Definition of done | a checklist of how the team knows the work is finished. Kept apart from the criteria |",
           "| Source | the meeting, and every line the story cites |",
           "| Lines of the meeting this story does not use | every other line of the record, each with the reason |", "",
           "## 2. The user and the value", "",
           "- **The user** is a kind of person, described so that a tester could set one up. \"A customer who does not have an",
           "  account\" is a user. \"A user\" is not.",
           "- **The value** is what that person can do afterwards that they could not do before, in plain words.",
           "- Each cites the line of the meeting that says it.",
           "- If the meeting did not say why it matters to the business, the story says that it did not. It does not make up a",
           "  reason.", "",
           "## 3. What makes a criterion testable", "",
           "A criterion is testable when a tester can write its test without asking anything. Here that means all of these.", "",
           "1. **It has three parts and one of each.** *Given* a starting state a tester can set up from the story's own test",
           "   set-up. *When* one thing a person does. That may be a journey of several steps, such as completing a checkout, if the",
           "   story defines it. *Then* one result. Two results are two criteria.",
           "2. **The result can be seen or read.** A page shown, a message with its exact words, an email received, a thing that did",
           "   not happen. Not a state inside the system that nobody can look at.",
           "3. **Every amount is a number**, and so is every wait. \"5 minutes\", never \"promptly\". \"Not placed\" needs a time after",
           "   which the tester stops waiting.",
           "4. **Every message is given word for word**, in double quotes, with where on the page it is shown.",
           "5. **It uses no undefined word.** The list is in section 4.",
           "6. **It says what it rests on.** Section 5.", "",
           "## 4. Words a criterion may not use", "",
           "These mean nothing a tester can check:", "",
           ", ".join(VAGUE) + ".", "",
           "A criterion may use one of them only if the story's own \"Words this story defines\" gives it a meaning that can be",
           "measured. So \"valid\" is allowed in a story that says exactly what a valid email address is, and in no other.",
           "Words inside double quotes are what the product shows, and are not counted.", "",
           "## 5. SAID and ASSUMED", "",
           "A meeting rarely says enough to test from. It says \"email is required\" and does not say what the customer sees when",
           "it is missing. To write a testable criterion, somebody has to supply that. This standard lets the writer supply it,",
           "and never lets it pass as the meeting's.", "",
           "| Basis | Meaning | What the criterion carries |", "|---|---|---|",
           "| **SAID** | the meeting stated it | each line it rests on, quoted with its speaker |",
           "| **ASSUMED** | the meeting did not state it. The writer proposes it so that the story can be tested | the words \"ASSUMPTION, to be confirmed by\", who confirms it, and the open question it answers |", "",
           "- A criterion is one or the other. Never both, and never neither.",
           "- A criterion that mixes a said requirement with an assumed one is split in two.",
           "- **A SAID criterion states the meeting's requirement in the meeting's sense.** If the meeting said \"make them\", the",
           "  criterion does not say \"ask them\". If two readings are open, the story takes one, says which, and lists the question.",
           "- **A SAID criterion may still lean on a word the writer defined**, because the meeting says what must be true and",
           "  rarely says how a tester sees it. Then the criterion names each such word, and the head of the story counts how many",
           "  SAID criteria do. The program works that list out from the story's own defined words.",
           "- The head of the story counts how many criteria are SAID and how many ASSUMED.",
           "- An assumption is a proposal. Nobody should build on one as if it had been decided.",
           "- **Every assumption has an open question behind it**: an assumed criterion names its own, and an assumed definition or",
           "  piece of test set-up is covered by one in the list.", "",
           "## 6. Scope", "",
           "- **Out of scope is written first.** What the story refuses to build is what gives it an edge.",
           "- Each entry says **why** it is out, and **where it went**: another work item, an open question, a refusal, or",
           "  nowhere, because the meeting did not discuss it.",
           "- Something the meeting mentioned alongside the story and that is being left out is named, with the line. If leaving",
           "  it out is the writer's choice and not the meeting's, the entry says so.",
           "- **Each in-scope entry names the criteria that test it.** An entry no criterion tests is a promise nobody checks.", "",
           "## 7. Dependencies, source, and the definition of done", "",
           "- **Dependencies** are listed, each SAID or ASSUMED, or the section says None.",
           "- **Source**: every line cited anywhere in the story exists in the transcript record, and every quotation is the",
           "  record's own words. The story never changes the record.",
           "- **The definition of done** is a checklist about the work. It is not a place to put a requirement that should have",
           "  been a criterion.", "",
           "## 8. What this standard leaves to judgment", "",
           "- Whether a criterion marked SAID says no more than its lines do. A program cannot check that.",
           "- Whether the assumptions are sensible ones.",
           "- Whether the criteria, taken together, cover the story.",
           "- Whether a \"Then\" is really one result.",
           "- Whether the test set-up is enough to run a test. It names the data. It cannot name what the meeting never mentioned,",
           "  such as the other fields of a checkout."]
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------- command

def main(argv=None, say=print):
    argv = sys.argv[1:] if argv is None else argv
    stories = argv[argv.index("--stories") + 1] if "--stories" in argv else STORIES
    if argv[:1] == ["standard"]:
        os.makedirs(stories, exist_ok=True)
        with open(os.path.join(stories, "story-standard.md"), "w", encoding="utf-8") as f:
            f.write(standard_text())
        say("Wrote story-standard.md.")
        return 0
    if argv[:1] not in (["build"], ["check"]):
        say(__doc__.strip())
        return 2
    import story_001 as content
    try:
        record_text = read(os.path.join(TRANSCRIPTS, content.SOURCE + ".md"))
        provenance_text = read(os.path.join(TRANSCRIPTS, content.SOURCE + ".provenance.yaml"))
        decisions_text = read(os.path.join(TRANSCRIPTS, content.SOURCE + ".decisions.md"))
        items_text = read(os.path.join(TRANSCRIPTS, content.SOURCE + ".work-items.md"))
    except OSError:
        say("NOT DONE. The source record, its provenance file, its decisions file or its work-items file could not be read.")
        return 2
    path = os.path.join(stories, "story-001.md")
    if argv[0] == "build":
        os.makedirs(stories, exist_ok=True)
        before = sha(record_text)
        with open(path, "w", encoding="utf-8") as f:
            f.write(render(content, read_record(record_text), record_text))
        say("Wrote story-001.md. The source record was %s. Nothing was sent to any tracker." % ("not changed" if sha(read(os.path.join(TRANSCRIPTS, content.SOURCE + ".md"))) == before else "CHANGED"))
        return 0
    try:
        story_text = read(path)
    except OSError:
        say("CHECK FAILED. story-001.md could not be read.")
        return 1
    problems, facts = check(story_text, record_text, provenance_text, decisions_text, items_text)
    for line in summary(facts):
        say(line)
    say("")
    if problems:
        for problem in problems:
            say("PROBLEM: " + problem)
        say("CHECK FAILED. %d problem%s." % (len(problems), "" if len(problems) == 1 else "s"))
        return 1
    say("CHECK PASSED. The story has every required section, each criterion is numbered, and each cited source identifier exists.")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, HERE)
    sys.exit(main())
