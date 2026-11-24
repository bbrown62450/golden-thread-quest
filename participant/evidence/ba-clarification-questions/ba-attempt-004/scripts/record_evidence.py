#!/usr/bin/env python3
"""Records logs/question-check.txt for the quest ba-clarification-questions. It contacts nothing.

    python3 participant/evidence/ba-clarification-questions/ba-attempt-004/scripts/record_evidence.py

It runs the check on the handed-in files, then on copies with one thing spoiled at a time. The copies are held
in memory or in a scratch folder, SCRATCH, which is deleted at the end. No handed-in file is changed, and it
checks that.
"""
import hashlib
import os
import shutil
import socket
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
SKILL = os.path.join(REPO, "participant", "skills", "ba-clarification-questions")
sys.path.insert(0, SKILL)
import candidates   # noqa: E402
import questions    # noqa: E402

LOGS = os.path.join(HERE, "..", "logs")
FOLDER = questions.FOLDER
NAMES = ("questions.md", "dropped.md", "work-pieces.md")
COMMAND = "python3 participant/skills/ba-clarification-questions/questions.py"


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def digests():
    out = {name: hashlib.sha256(read(os.path.join(FOLDER, name)).encode()).hexdigest() for name in sorted(os.listdir(FOLDER))}
    out["../ambiguity/findings.md"] = hashlib.sha256(read(questions.FINDINGS).encode()).hexdigest()
    return out


class Log:
    def __init__(self):
        self.lines = ["The question check. ba-clarification-questions, attempt ba-attempt-004",
                      "Recorded by scripts/record_evidence.py. Nothing was sent anywhere. The product and its requirements are made up."]
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
    good = [read(os.path.join(FOLDER, name)) for name in NAMES]
    findings_text = read(questions.FINDINGS)
    scratch = tempfile.mkdtemp(prefix="gtq-questions-")

    def trial(label, index, old, new, expect, findings=None):
        """Spoil one thing in a copy, run the check, and require the named problem."""
        texts = list(good)
        found = index is None or old in texts[index]
        if index is not None:
            texts[index] = texts[index].replace(old, new, 1)
        got = questions.check(texts[0], texts[1], texts[2], findings or findings_text)[0]
        log.out("Spoiled: %s" % label, *["    PROBLEM: " + p for p in got] or ["    no problem reported"])
        log.check("reported: \"%s\"" % expect, found and any(expect in p for p in got))

    try:
        log.part("PART 1. The check, on the handed-in files (the record the quest asks for)")
        before = digests()
        said = []
        code = questions.main(["check"], say=said.append)
        log.out("$ %s check" % COMMAND, "-" * 78, *said, "-" * 78, "exit code: %d" % code)
        log.check("the check passed: exit code 0", code == 0 and said[-1].startswith("CHECK PASSED."))
        problems, facts = questions.check(good[0], good[1], good[2], findings_text)
        asked, gone, findings = facts["questions"], facts["dropped"], facts["findings"]
        log.check("no problem at all was reported", problems == [])
        log.check("the check changed no file: every file in participant/context/clarification, and the review's findings.md, has the same SHA-256 as before", digests() == before)
        done = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", "participant/context/ambiguity"], cwd=REPO)
        log.check("the approved ambiguity review is as it was committed: git reports no change under participant/context/ambiguity", done.returncode == 0)
        questions.build(scratch)
        log.out("$ %s build --folder SCRATCH" % COMMAND)
        log.check("the three handed-in files are byte for byte what build writes from the candidates, so none was adjusted by hand",
                  [read(os.path.join(scratch, name)) for name in NAMES] == good)

        log.part("PART 2. Criterion 1: each question links to a finding from the ambiguity review")
        log.out("The link is the finding's number and some of the finding's own question, quoted. Both are looked up in findings.md.", "")
        for entry in asked + gone:
            log.out("  %s -> %s  \"%s\"" % (entry["id"], entry["finding"], entry["from"]))
        log.check("all %d questions asked link to one of the review's 9 findings" % len(asked), len(findings) == 9 and all(q["finding"] in findings for q in asked))
        log.check("each quotes words that are found in that finding's question, and in no other finding's question",
                  all(q["from"] in findings[q["finding"]]["question"] and not any(q["from"] in f["question"] for n, f in findings.items() if n != q["finding"]) for q in asked + gone))
        log.check("the same holds for all %d dropped questions" % len(gone), all(d["finding"] in findings for d in gone))
        trial("C-13 linked to F-18, which does not exist", 0, "- Finding: F-08 (", "- Finding: F-18 (", "C-13 links to F-18, which is not a finding")
        trial("C-13 linked to F-11, which the review raised and withdrew", 0, "- Finding: F-08 (", "- Finding: F-11 (", "C-13 links to F-11, which is not a finding")
        trial("C-01 with its finding line removed", 0, "- Finding: F-01 (REQ-04 and REQ-12, contradictory, effort large)\n", "", "C-01 links to no finding")
        trial("C-13 quoting words the finding does not say", 0, '"what is to happen to those bookings"', '"what is to happen to those rooms"', "C-13 quotes words that are not in the question of F-08")
        trial("C-13 quoting another finding's words", 0, '"what is to happen to those bookings"', '"Over what period are no-shows counted"', "C-13 quotes words that are not in the question of F-08")
        cut = findings_text[:findings_text.index("## F-09")] + findings_text[findings_text.index("## Unflagged"):]
        trial("finding F-09 taken out of the review, the question files left alone", None, "", "", "C-15 links to F-09, which is not a finding", findings=cut)

        log.part("PART 3. Criteria 2 and 3: at least two answers, and each answer leads to different work")
        log.out("Each answer names its work in a sentence and as pieces from work-pieces.md. A question may be asked only if no",
                "two of its answers name the same set of pieces.", "")
        for q in asked:
            log.out("  %s  %s" % (q["id"], "   ".join("%s: %s" % (a["letter"], ", ".join(a["pieces"]) or "none") for a in q["answers"])))
        log.check("every question asked has between 2 and 4 answers", all(2 <= len(q["answers"]) <= 4 for q in asked))
        log.check("in every question asked, no two answers name the same set of pieces",
                  all(len(set(questions.piece_sets(q["answers"]))) == len(q["answers"]) for q in asked))
        log.check("every answer states its work in a sentence, and no two answers to one question share a sentence",
                  all(questions.words(a["work"]) >= 5 for q in asked for a in q["answers"]) and all(len({a["work"] for a in q["answers"]}) == len(q["answers"]) for q in asked))
        log.check("every piece an answer names is in work-pieces.md, and every piece in work-pieces.md is named by some answer",
                  {p for e in asked + gone for a in e["answers"] for p in a["pieces"]} == set(facts["pieces"]))
        trial("C-15 left with one answer", 0, "| A. As \"booked\" | Nothing is added. The slot uses the marking that REQ-02 already has. | none |\n", "", "C-15 lists 1 possible answer, fewer than two")
        trial("C-11 with both answers leading to the same piece", 0, "and nothing is stored for it. | W-12 |", "and nothing is stored for it. | W-11 |", "C-11 is in the question list, and every answer leads to the same pieces of work")
        trial("C-12 with two of its four answers leading to the same piece", 0, "also get the action that lifts it. | W-13, W-14 |", "also get the action that lifts it. | W-13 |", "C-12 has answers that lead to the same pieces of work: B and D")
        trial("C-05 with an answer that states no work", 0, "| A. It refuses the booking | The booking is refused with a message that says why. | W-05 |", "| A. It refuses the booking | Refused. | W-05 |", "C-05 answer A does not state the work it leads to")
        trial("C-05 with one sentence used for both answers", 0, "The booking goes through, and the member appears on a list that staff can open.", "The booking is refused with a message that says why.", "C-05 states the same work, word for word, for two answers")
        trial("C-05 naming a piece that is not in the list", 0, "| W-05 |", "| W-55 |", "C-05 answer A names W-55, which is not in the list of work pieces")

        log.part("PART 4. Criterion 4: a question whose answers lead to the same work is dropped, and listed as dropped")
        for d in gone:
            log.out("  %s  %s  every answer: %s" % (d["id"], d["finding"], ", ".join(sorted(questions.piece_sets(d["answers"])[0])) or "none"))
        log.check("every dropped question has at least two answers, and all of them name the same set of pieces",
                  all(len(d["answers"]) >= 2 and len(set(questions.piece_sets(d["answers"]))) == 1 for d in gone))
        log.check("every dropped question gives a reason and says what is still needed", all(questions.words(d["why"]) >= 5 and d["still"] for d in gone))
        ids = sorted(e["id"] for e in asked + gone)
        log.check("the %d candidates C-01 to C-%02d are each in exactly one of the two lists" % (len(ids), len(ids)), ids == ["C-%02d" % n for n in range(1, len(ids) + 1)])
        log.check("candidates.py does not say which candidates are kept: no candidate carries a field for it, and build decides from the pieces",
                  all(not any(key in c for key in ("kept", "dropped", "keep", "drop", "status")) for c in candidates.CANDIDATES)
                  and sorted(c["id"] for c in candidates.CANDIDATES if questions.classify(c["answers"]) == "dropped") == sorted(d["id"] for d in gone))
        start = good[1].index("## C-17")
        moved = good[1][start:good[1].index("## C-16")].replace("## C-17", "## 12. C-17").replace("**Question considered:**", "**Question:**")
        texts = [good[0] + "\n" + moved, good[1][:start] + good[1][good[1].index("## C-16"):], good[2]]
        got = questions.check(texts[0], texts[1], texts[2], findings_text)[0]
        log.out("Spoiled: dropped question C-17 moved into the question list", *["    PROBLEM: " + p for p in got])
        log.check("reported: \"C-17 is in the question list, and every answer leads to the same pieces of work. It belongs in the dropped list\"",
                  any("C-17 is in the question list, and every answer leads to the same pieces of work. It belongs in the dropped list" in p for p in got))
        trial("dropped question C-17 given answers that differ", 1, "with the lead time set to 120 minutes. | B-03 |", "with the lead time set to 120 minutes. | B-03, B-04 |", "C-17 is in the dropped list, and its answers lead to different pieces of work. It is a question to ask")
        trial("dropped question C-17 with its reason cut to two words", 1, "- Why it is dropped: Any number of minutes builds the same reminder. A booking made later than the lead time needs the same handling whatever the number is.", "- Why it is dropped: Not needed.", "C-17 gives no reason why its answers would not change the work")
        start = good[1].index("## C-09")
        texts = [good[0], good[1][:start] + good[1][good[1].index("## C-17"):], good[2]]
        got = questions.check(texts[0], texts[1], texts[2], findings_text)[0]
        log.out("Spoiled: C-09 taken out of the dropped list and put nowhere", *["    PROBLEM: " + p for p in got])
        log.check("reported: \"Candidates are missing from both lists: C-09.\"", "Candidates are missing from both lists: C-09." in got)

        log.part("PART 5. Criterion 5: short enough to answer without a meeting",
                 "The rule used: one sentence, one question mark, at most %d words, at most %d answers of at most %d words each," % (questions.MAX_WORDS, questions.MAX_ANSWERS, questions.MAX_LABEL_WORDS),
                 "so that the question can be answered by naming one letter. Whether a person could in fact answer without a",
                 "meeting is a judgment. logs/blind-read.txt records what three independent readers said.", "")
        for q in asked:
            log.out("  %s  %2d words  %d answers  longest answer %2d words" % (q["id"], questions.words(q["question"]), len(q["answers"]), max(questions.words(a["label"]) for a in q["answers"])))
        log.check("all %d questions asked are inside every limit" % len(asked), all(questions.shortness(q) == [] for q in asked))
        log.check("the longest is %d words" % max(questions.words(q["question"]) for q in asked), max(questions.words(q["question"]) for q in asked) <= questions.MAX_WORDS)
        log.out("", "The findings' own questions, measured by the same rule, with two answers supposed for each:")
        failing = []
        for number in sorted(findings):
            reasons = questions.shortness({"question": findings[number]["question"], "answers": [{"letter": "A", "label": "x"}, {"letter": "B", "label": "y"}]})
            failing += [number] if reasons else []
            log.out("  %s  %2d words  %s" % (number, questions.words(findings[number]["question"]), "; ".join(reasons) or "inside the limits"))
        log.check("the rule is not one that everything passes: %d of the 9 findings' own questions fall outside it (%s)" % (len(failing), ", ".join(failing)), 0 < len(failing) < 9)
        trial("C-06 padded to 29 words", 0, "**Question:** Which is the worst fault a confirmed booking must survive?",
              "**Question:** Thinking about all the faults that there could be, which is the worst fault that a confirmed booking must in the end be able to survive without being lost?", "C-06 has 29 words, more than 25")
        trial("C-01 turned into two questions", 0, "**Question:** In the two hours before a booking starts, can the member cancel it themselves?", "**Question:** In the two hours before a booking starts, can the member cancel it themselves? And can staff?", "C-01 is not one question ending in one question mark")

        log.part("PART 6. Criterion 6: ordered by how much of the work depends on them")
        log.out("The work that depends on a question: the pieces one of its answers needs and another does not, with the same",
                "for any question asked only because of an answer to it. Equal counts: the finding's effort, then its number.", "")
        for place, q in enumerate(asked, 1):
            own, total = questions.own_dependent(q["answers"]), questions.all_dependent(q, asked)
            log.out("  %2d. %s  %d  own: %-22s through another: %-12s effort of %s: %s" % (
                place, q["id"], len(total), ", ".join(sorted(own)), ", ".join(sorted(total - own)) or "-", q["finding"], findings[q["finding"]]["effort"]))
        counts = [len(questions.all_dependent(q, asked)) for q in asked]
        log.check("the counts never rise down the list: %s" % ", ".join(str(c) for c in counts), counts == sorted(counts, reverse=True))
        log.check("the order in the file is the order the check works out for itself from the answers", [q["id"] for q in facts["ordered"]] == [q["id"] for q in asked])
        log.check("where counts are equal, a finding of larger effort is never below one of smaller effort",
                  all(questions.EFFORT[findings[a["finding"]]["effort"]] <= questions.EFFORT[findings[b["finding"]]["effort"]]
                      for a, b in zip(asked, asked[1:]) if len(questions.all_dependent(a, asked)) == len(questions.all_dependent(b, asked))))
        log.check("no question comes before the question it waits for", all(
            [x["id"] for x in asked].index(q["only_if"][0]) < [x["id"] for x in asked].index(q["id"]) for q in asked if q.get("only_if")))
        every = set().union(*[questions.own_dependent(q["answers"]) for q in asked])
        first = set().union(*[questions.all_dependent(q, asked) for q in asked[:4]])
        log.out("", "The scenario's product owner answers four questions. Here the first four carry %d of the %d pieces that depend on any answer." % (len(first), len(every)))
        log.check("the first four questions carry more than half of the work that depends on any answer", len(first) * 2 > len(every))
        a, b, c = good[0].index("## 1. C-13"), good[0].index("## 2. C-04"), good[0].index("## 3. C-01")
        swapped = good[0][:a] + good[0][b:c].replace("## 2.", "## 1.") + good[0][a:b].replace("## 1.", "## 2.") + good[0][c:]
        got = questions.check(swapped, good[1], good[2], findings_text)[0]
        log.out("Spoiled: the first two questions swapped", *["    PROBLEM: " + p for p in got])
        log.check("reported: \"The questions are not in order of how much work depends on them\"", any("not in order of how much work depends on them" in p for p in got))
        trial("C-13 claiming 7 pieces", 0, "- Work that depends on the answer: 5 pieces", "- Work that depends on the answer: 7 pieces", "the answers give 5")
        trial("C-14 no longer waiting for C-13, so C-13's count should fall", 0, "- Asked only if: C-13 is answered A or C\n", "", "the answers give 3")

        log.part("PART 7. Criterion 7: nothing is sent to anyone")
        real = socket.socket

        def refuse(*args, **kwargs):
            raise OSError("a connection was attempted")
        socket.socket = refuse
        try:
            said = []
            blocked_build = questions.main(["build", "--folder", scratch], say=said.append)
            blocked_check = questions.main(["check", "--folder", scratch], say=said.append)
        finally:
            socket.socket = real
        log.check("with every network connection made to fail, build and check both still finish with exit code 0", (blocked_build, blocked_check) == (0, 0))
        probe = ("import sys; sys.path.insert(0, %r); import questions; questions.main(['check'], say=lambda line: None); "
                 "print(sorted(m for m in sys.modules if m.split('.')[0] in ('socket', 'ssl', 'http', 'urllib', 'smtplib', 'email', 'ftplib', 'subprocess')))" % SKILL)
        done = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True)
        log.out(*(["The probe itself failed: " + done.stderr.strip().splitlines()[-1]] if done.returncode else []))
        log.out("Modules for connecting, mailing or running other programs that Python had loaded after a run of the check: %s" % done.stdout.strip())
        log.check("none was loaded", done.stdout.strip() == "[]")
        log.check("the three files hold no email address and no web address", not any(mark in text for text in good for mark in ("@", "http:", "https:", "mailto:")))
        log.check("the people best placed to answer are roles from a list of %d, and no person is named" % len(candidates.ROLES), all(q["role"] in candidates.ROLES for q in asked))

        log.part("PART 8. Stretch goals: a default for each question, and questions grouped by who can answer")
        for q in asked:
            log.out("  %s  default %s. Assumes %s" % (q["id"], q["default"][0], q["default"][1]))
        log.check("every question asked suggests one of its own answers as the default, and states what that assumes",
                  all(q["default"] and q["default"][0] in [a["letter"] for a in q["answers"]] and questions.words(q["default"][1]) >= 5 for q in asked))
        trial("C-10 with a default that is not one of its answers", 0, "- Suggested default: B. This assumes that staff work at a desk", "- Suggested default: C. This assumes that staff work at a desk", "C-10 suggests default C, which is not one of its answers")
        groups = dict(line[4:].split(":** ") for line in good[0].splitlines() if line.startswith("- **") and ":** C-" in line)
        log.out("", *["  %s: %s" % pair for pair in groups.items()])
        log.check("the grouping lists every question asked once, under the role its own entry names",
                  sorted(i for ids in groups.values() for i in ids.split(", ")) == sorted(q["id"] for q in asked)
                  and all(q["id"] in groups.get(q["role"], "").split(", ") for q in asked))
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    log.check("at the end, every handed-in file and the review's findings.md are still what they were at the start", digests() == before)
    log.lines += ["", "RESULT: %s" % ("%d OF %d CHECKS FAILED." % (len(log.failed), log.count) if log.failed else "ALL CHECKS PASSED. %d checks." % log.count)]
    os.makedirs(LOGS, exist_ok=True)
    with open(os.path.join(LOGS, "question-check.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(log.lines) + "\n")
    print("question-check.txt: %s" % log.lines[-1])
    for label in log.failed:
        print("  FAILED: %s" % label)
    return 1 if log.failed else 0


if __name__ == "__main__":
    sys.exit(main())
