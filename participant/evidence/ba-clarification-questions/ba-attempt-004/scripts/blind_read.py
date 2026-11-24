#!/usr/bin/env python3
"""Writes logs/blind-read.txt: what three independent readers said, set beside what the question files say.

    python3 participant/evidence/ba-clarification-questions/ba-attempt-004/scripts/blind_read.py

The readers' verdicts below were copied by hand from their replies by the assistant that built this quest. Their
reasons are shortened. The sheets they were given are review/blind-sheet-1.md and review/blind-sheet-2.md.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "participant", "skills", "ba-clarification-questions"))
import candidates   # noqa: E402
import questions    # noqa: E402

# Sheet 1: the candidates as first written. D = answers lead to different work, S = the same. Y/N = could be answered without a meeting.
SHEET_1 = ["C-05", "C-12", "C-13", "C-07", "C-16", "C-04", "C-02", "C-09", "C-08", "C-10", "C-03", "C-15", "C-14", "C-01", "C-11", "C-06"]
ASKED_1 = {"C-01", "C-04", "C-05", "C-06", "C-10", "C-11", "C-12", "C-13", "C-14", "C-15"}
READER_1 = ("DDDSSDSSDSSDDDDD", "NYYYYNYNYYYYYYYY")
READER_2 = ("DDDSSDSSSSSDDDDD", "NYYYYNYNYYYYYYYY")
# Sheet 2: the candidates as handed in.
SHEET_2 = ["C-12", "C-16", "C-09", "C-01", "C-10", "C-14", "C-04", "C-06", "C-15", "C-11", "C-17", "C-02", "C-07", "C-08", "C-03", "C-05", "C-13"]
READER_3 = ("DSSDDDDDDDSSSDSDD", "YYNYYYYYYYYYYYYYY")

NOTES_1 = [
    "C-08 (reminder time, then dropped). Reader 1: different. \"The evening before\" is a fixed hour and needs a rule for bookings made after it,",
    "  so it is not only another number. Reader 2: the same, borderline, for the reason reader 1 gave.",
    "C-10 (staff functions in mobile browsers, asked). Both readers: the same, borderline. The same screens, rules and data, with more layout work.",
    "C-05. Both: cannot be answered alone, because \"that behaviour\" points at nothing in the question itself.",
    "C-04. Both: cannot be answered without a meeting. It is open-ended, and two of its answers could both be wanted.",
    "C-09 (dropped). Both: the answers speak of versions and name no browsers.",
    "C-12. Both: answerable, though \"both B and C\" is a likely answer that is not listed.",
]
NOTES_3 = [
    "C-09 (dropped). The answers give sizes of list and name no browsers. It is a dropped question, and dropped.md says a named list is still needed.",
    "C-10 (asked). Different, \"the mildest different on the sheet\".",
    "C-17 (dropped). It applies only if C-08 is answered A, and the sheet did not say so. dropped.md does.",
]


def main():
    now_asked = {c["id"] for c in candidates.CANDIDATES if questions.classify(c["answers"]) == "kept"}
    out = ["Three independent reads of the questions. ba-clarification-questions, attempt ba-attempt-004",
           "Written by scripts/blind_read.py from verdicts copied by hand out of the readers' replies.", "",
           "Who the readers were: three separate AI assistants (Claude), each started fresh, each told to read only the made-up",
           "requirements and a sheet of questions with their answers. No person read the questions. The readers were not shown",
           "the pieces of work, the work each answer leads to, which questions were dropped, or each other's replies. The",
           "instruction to read nothing else was given in words and was not enforced.", "",
           "Each was asked, for every item: would different answers make a developer build different things, or the same thing",
           "with at most a different number in a setting? And could the owner answer by naming one of the answers, without a meeting?",
           "The sheets were put together before any reply was read, and the replies were compared with the files only after all",
           "of a round's readers had answered.", ""]

    def table(title, sheet, asked, readers):
        agree = [0] * len(readers)
        out.extend([title, "  item  candidate  the files say  " + "  ".join("reader %d work / no meeting" % n for n, _ in readers)])
        for i, cand in enumerate(sheet):
            mine = "D" if cand in asked else "S"
            cells = []
            for k, (_, (work, meeting)) in enumerate(readers):
                agree[k] += work[i] == mine
                cells.append("%-9s / %-3s %s" % ("different" if work[i] == "D" else "same", "yes" if meeting[i] == "Y" else "no", " " if work[i] == mine else "*"))
            out.append("  %-4d  %-9s  %-13s  %s" % (i + 1, cand, "asked" if mine == "D" else "dropped", "        ".join(cells)))
        out.append("  * the reader's verdict on the work differs from the files.")
        for k, (n, (work, meeting)) in enumerate(readers):
            no = [sheet[i] for i in range(len(sheet)) if meeting[i] == "N"]
            out.append("  Reader %d agreed on the work for %d of %d. Said \"needs a meeting\" for: %s." % (n, agree[k], len(sheet), ", ".join(no) or "none"))
        out.append("")
        return agree

    first = table("ROUND 1. The 16 candidates as first written (review/blind-sheet-1.md)", SHEET_1, ASKED_1, [(1, READER_1), (2, READER_2)])
    out.extend(["What they said where they differed from the files, or found a question hard to answer:"] + ["  " + n for n in NOTES_1] + [""])
    out.extend(["What was changed after round 1, and what was not:",
                "  C-08 rewritten. It now asks which kind of timing is wanted, and is asked. The number of minutes became a new",
                "    candidate, C-17, which is dropped.",
                "  C-05 reworded so that it can be read alone.",
                "  C-04 reworded to \"which of these\", with a fourth answer, \"Both of these\".",
                "  C-12 given a fourth answer, for a suspension that ends by itself or sooner if staff lift it.",
                "  C-09's answers reworded. It stays dropped.",
                "  C-10 NOT changed. It stays in the question list, against both readers. PROOF.md says why.", ""])
    third = table("ROUND 2. The 17 candidates as handed in (review/blind-sheet-2.md), read by a third reader who had seen nothing before",
                  SHEET_2, now_asked, [(3, READER_3)])
    out.extend(["What the third reader said beyond the verdicts:"] + ["  " + n for n in NOTES_3] + [""])
    asked_no = [SHEET_2[i] for i in range(len(SHEET_2)) if READER_3[1][i] == "N" and SHEET_2[i] in now_asked]
    ok = sorted(SHEET_2) == sorted(c["id"] for c in candidates.CANDIDATES) and first == [14, 15] and third == [17] and not asked_no
    out.extend(["SUMMARY",
                "  Round 1: readers agreed with the files on the work for 14 and 15 of 16. Three questions asked were said to need a meeting",
                "  or a missing answer (C-04, C-05, C-12), and one dropped question was judged different by one reader (C-08).",
                "  Round 2: the third reader agreed on the work for all 17, and said all 11 questions asked could be answered without a meeting.",
                "  One reader in round 2 is one reader. The questions were changed to meet the first two readers' points, so agreement in",
                "  round 2 was the likely result, and it does not show that a person would agree.",
                "", "RESULT: %s" % ("the counts above match the verdicts recorded in this script, and sheet 2 lists the 17 handed-in candidates." if ok else "THE COUNTS DO NOT MATCH.")])
    with open(os.path.join(HERE, "..", "logs", "blind-read.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print(out[-1])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
