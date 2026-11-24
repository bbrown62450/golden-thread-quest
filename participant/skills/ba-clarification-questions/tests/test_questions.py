"""Tests for questions.py. They contact nothing and write only to a scratch folder.

    python3 -m unittest discover -s participant/skills/ba-clarification-questions/tests -v
"""
import copy
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import candidates   # noqa: E402
import questions    # noqa: E402

FINDINGS_TEXT = questions.read(questions.FINDINGS)
FINDINGS = questions.parse_findings(FINDINGS_TEXT)


def rendered(change=None, pieces=None):
    """The three files, after an optional change to a copy of the candidates."""
    cands = copy.deepcopy(candidates.CANDIDATES)
    if change:
        change({c["id"]: c for c in cands}, cands)
    return questions.render(cands, pieces or candidates.PIECES, candidates.SET_ASIDE, FINDINGS)


def problems(texts, findings_text=FINDINGS_TEXT):
    return questions.check(texts[0], texts[1], texts[2], findings_text)[0]


def edited(index, old, new):
    texts = list(rendered())
    assert old in texts[index], old
    texts[index] = texts[index].replace(old, new, 1)
    return texts


class Sound(unittest.TestCase):
    def test_the_candidates_as_written_pass(self):
        self.assertEqual(problems(rendered()), [])

    def test_ten_asked_six_dropped_sixteen_in_all(self):
        facts = questions.check(*rendered(), FINDINGS_TEXT)[1]
        self.assertEqual((len(facts["questions"]), len(facts["dropped"])), (11, 6))

    def test_the_handed_in_files_are_what_build_writes(self):
        for name, text in zip(("questions.md", "dropped.md", "work-pieces.md"), rendered()):
            self.assertEqual(questions.read(os.path.join(questions.FOLDER, name)), text, name)

    def test_what_is_read_back_is_what_was_written(self):
        facts = questions.check(*rendered(), FINDINGS_TEXT)[1]
        by_id = {e["id"]: e for e in facts["questions"] + facts["dropped"]}
        for c in candidates.CANDIDATES:
            got = by_id[c["id"]]
            self.assertEqual(got["question"], c["question"])
            self.assertEqual(got["finding"], c["finding"])
            self.assertEqual(got["from"], c["from"])
            self.assertEqual([(a["letter"], a["label"], a["work"], a["pieces"]) for a in got["answers"]],
                             [(a["letter"], a["label"], a["work"], a["pieces"]) for a in c["answers"]])
            self.assertEqual(got.get("only_if"), c.get("only_if"))

    def test_nine_findings_are_read_and_withdrawn_ones_are_not(self):
        self.assertEqual(sorted(FINDINGS), ["F-0%d" % n for n in range(1, 10)])
        self.assertEqual(FINDINGS["F-05"]["effort"], "small")
        self.assertEqual(FINDINGS["F-01"]["effort"], "large")


class Links(unittest.TestCase):
    def test_a_finding_that_does_not_exist(self):
        got = problems(edited(0, "- Finding: F-08 (", "- Finding: F-18 ("))
        self.assertTrue(any("C-13 links to F-18, which is not a finding" in p for p in got), got)

    def test_a_withdrawn_finding_is_not_a_finding(self):
        got = problems(edited(0, "- Finding: F-08 (", "- Finding: F-11 ("))
        self.assertTrue(any("C-13 links to F-11, which is not a finding" in p for p in got), got)

    def test_no_finding_at_all(self):
        got = problems(edited(0, "- Finding: F-08 (REQ-13, incomplete, effort medium)\n", ""))
        self.assertTrue(any("C-13 links to no finding" in p for p in got), got)

    def test_words_that_the_finding_does_not_say(self):
        got = problems(edited(0, '"what is to happen to those bookings"', '"what is to happen to those rooms"'))
        self.assertTrue(any("C-13 quotes words that are not in the question of F-08" in p for p in got), got)

    def test_words_from_another_finding(self):
        got = problems(edited(0, '"what is to happen to those bookings"', '"Over what period are no-shows counted"'))
        self.assertTrue(any("C-13 quotes words" in p for p in got), got)

    def test_a_dropped_question_needs_its_finding_too(self):
        got = problems(edited(1, "- Finding: F-06 (", "- Finding: F-55 ("))
        self.assertTrue(any("C-09 links to F-55" in p for p in got), got)

    def test_the_finding_removed_from_the_review(self):
        cut = FINDINGS_TEXT[:FINDINGS_TEXT.index("## F-09")] + FINDINGS_TEXT[FINDINGS_TEXT.index("## Unflagged"):]
        got = problems(rendered(), cut)
        self.assertTrue(any("C-15 links to F-09" in p for p in got) and any("C-16 links to F-09" in p for p in got), got)


class Answers(unittest.TestCase):
    def test_one_answer_is_too_few(self):
        got = problems(edited(0, "| A. As \"booked\" | Nothing is added. The slot uses the marking that REQ-02 already has. | none |\n", ""))
        self.assertTrue(any("C-15 lists 1 possible answer, fewer than two" in p for p in got), got)

    def test_no_answers(self):
        texts = edited(0, "| A. Staff functions too | The staff screens are laid out for a small screen as well as a desktop. | W-10 |\n", "")
        texts[0] = texts[0].replace("| B. Only the member functions | Nothing is added. Staff screens are built for a desktop browser, and NFR-03 says so. | none |\n", "")
        self.assertTrue(any("C-10 lists 0 possible answers" in p for p in problems(texts)))

    def test_two_answers_with_the_same_pieces_cannot_be_asked(self):
        got = problems(edited(0, "and nothing is stored for it. | W-12 |", "and nothing is stored for it. | W-11 |"))
        self.assertTrue(any("C-11 is in the question list, and every answer leads to the same pieces" in p for p in got), got)

    def test_three_answers_where_two_lead_to_the_same_pieces(self):
        got = problems(edited(0, "also get the action that lifts it. | W-13, W-14 |", "also get the action that lifts it. | W-13 |"))
        self.assertTrue(any("C-12 has answers that lead to the same pieces of work: B and D" in p for p in got), got)

    def test_two_answers_that_both_build_nothing(self):
        got = problems(edited(0, "The availability display gets a third marking, and REQ-02 is reworded to allow it. | W-20 |",
                              "The availability display gets a third marking, and REQ-02 is reworded to allow it. | none |"))
        self.assertTrue(any("C-15 is in the question list" in p for p in got), got)

    def test_an_answer_with_no_stated_work(self):
        got = problems(edited(0, "| A. It refuses the booking | The booking is refused with a message that says why. | W-05 |", "| A. It refuses the booking | Refused. | W-05 |"))
        self.assertTrue(any("C-05 answer A does not state the work" in p for p in got), got)

    def test_the_same_sentence_for_two_answers(self):
        got = problems(edited(0, "The booking goes through, and the member appears on a list that staff can open.", "The booking is refused with a message that says why."))
        self.assertTrue(any("C-05 states the same work, word for word" in p for p in got), got)

    def test_a_piece_that_is_not_in_the_list(self):
        got = problems(edited(0, "| W-05 |", "| W-55 |"))
        self.assertTrue(any("C-05 answer A names W-55, which is not in the list" in p for p in got), got)

    def test_a_piece_nobody_names(self):
        got = problems(rendered(pieces=candidates.PIECES + [("W-31", "A piece that no answer leads to")]))
        self.assertEqual(got, ["W-31 is in the list of work pieces and no answer names it."])

    def test_answers_not_lettered_in_order(self):
        got = problems(edited(0, "| B. It allows the booking and tells staff |", "| C. It allows the booking and tells staff |"))
        self.assertTrue(any("C-05 does not letter its answers" in p for p in got), got)


class Dropped(unittest.TestCase):
    def test_a_dropped_question_whose_answers_differ_must_be_asked(self):
        got = problems(edited(1, "with the lead time set to 120 minutes. | B-03 |", "with the lead time set to 120 minutes. | B-03, B-04 |"))
        self.assertTrue(any("C-17 is in the dropped list, and its answers lead to different pieces" in p for p in got), got)

    def test_a_candidate_in_both_lists(self):
        texts = list(rendered())
        start = texts[0].index("## 11. C-15")
        texts[1] += "\n" + texts[0][start:].replace("## 11. C-15", "## C-15").replace("**Question:**", "**Question considered:**")
        self.assertTrue(any("C-15 appears more than once" in p for p in problems(texts)))

    def test_a_candidate_in_neither_list(self):
        texts = list(rendered())
        start, end = texts[1].index("## C-09"), texts[1].index("## C-16")
        texts[1] = texts[1][:start] + texts[1][end:]
        self.assertTrue(any("Candidates are missing from both lists: C-09." in p for p in problems(texts)))

    def test_no_reason(self):
        got = problems(edited(1, "- Why it is dropped: Any number of minutes builds the same reminder. A booking made later than the lead time needs the same handling whatever the number is.", "- Why it is dropped: Not needed."))
        self.assertTrue(any("C-17 gives no reason" in p for p in got), got)

    def test_nothing_about_what_is_still_needed(self):
        got = problems(edited(1, "- Still needed: A value. The lead time", "- Still needed: The lead time"))
        self.assertTrue(any("C-17 does not say what is still needed" in p for p in got), got)

    def test_classify(self):
        def a(*sets):
            return [{"pieces": list(s)} for s in sets]
        self.assertEqual(questions.classify(a(["W-01"], [])), "kept")
        self.assertEqual(questions.classify(a(["W-01"], ["W-01"])), "dropped")
        self.assertEqual(questions.classify(a([], [])), "dropped")
        self.assertEqual(questions.classify(a(["W-01"], ["W-01"], ["W-02"])), "mixed")
        self.assertEqual(questions.classify(a(["W-01"])), "mixed")
        self.assertEqual(questions.classify(a(["W-01", "W-02"], ["W-02", "W-01"])), "dropped")

    def test_build_refuses_a_candidate_that_is_neither(self):
        def change(by_id, cands):
            by_id["C-12"]["answers"][2]["pieces"] = ["W-13"]
            by_id["C-12"]["answers"][3]["pieces"] = ["W-99"]
        with self.assertRaises(ValueError):
            rendered(change)

    def test_build_moves_a_candidate_whose_answers_stop_differing(self):
        def change(by_id, cands):
            by_id["C-10"]["answers"][0]["pieces"] = []
            by_id["C-10"]["why"], by_id["C-10"]["still"] = "Either answer builds the same screens for the staff.", ("nothing", "No more.")
        texts = rendered(change, [p for p in candidates.PIECES if p[0] != "W-10"])
        self.assertNotIn("C-10", texts[0])
        self.assertIn("## C-10", texts[1])
        self.assertEqual(problems(texts), [])


class Short(unittest.TestCase):
    def q(self, text, answers=2, label="Yes"):
        return {"question": text, "answers": [{"letter": "ABCDE"[i], "label": label} for i in range(answers)]}

    def test_every_question_asked_is_within_the_limits(self):
        for c in candidates.CANDIDATES:
            self.assertEqual(questions.shortness(c), [], c["id"])

    def test_twenty_five_words_pass_and_twenty_six_do_not(self):
        self.assertEqual(questions.shortness(self.q(" ".join(["word"] * 24) + " end?")), [])
        self.assertEqual(questions.shortness(self.q(" ".join(["word"] * 25) + " end?")), ["has 26 words, more than 25"])

    def test_two_questions_in_one(self):
        self.assertIn("is not one question ending in one question mark", questions.shortness(self.q("Is it kept? And for how long?")))

    def test_a_statement(self):
        self.assertIn("is not one question ending in one question mark", questions.shortness(self.q("Tell us how long it is kept.")))

    def test_two_sentences(self):
        self.assertIn("is more than one sentence", questions.shortness(self.q("Records are deleted. Is that right?")))

    def test_five_answers(self):
        self.assertEqual(questions.shortness(self.q("Which one?", answers=5)), ["has 5 answers, more than 4"])

    def test_a_long_answer(self):
        got = questions.shortness(self.q("Which one?", label=" ".join(["word"] * 16)))
        self.assertEqual(got, ["answer A has 16 words, more than 15", "answer B has 16 words, more than 15"])

    def test_the_findings_own_question_for_f03_is_not_short_enough(self):
        self.assertTrue(questions.shortness(self.q(FINDINGS["F-03"]["question"])))

    def test_a_long_question_in_the_file_is_reported(self):
        got = problems(edited(0, "**Question:** Which is the worst fault a confirmed booking must survive?",
                              "**Question:** Thinking about all the faults that there could be, which is the worst fault that a confirmed booking must in the end be able to survive without being lost?"))
        self.assertTrue(any("C-06 has 29 words, more than 25" in p for p in got), got)


class Order(unittest.TestCase):
    def test_own_dependent_leaves_out_what_every_answer_needs(self):
        c = next(c for c in candidates.CANDIDATES if c["id"] == "C-06")
        self.assertEqual(questions.own_dependent(c["answers"]), {"W-08", "W-09"})

    def test_a_question_carries_the_work_of_the_question_that_waits_for_it(self):
        facts = questions.check(*rendered(), FINDINGS_TEXT)[1]
        by_id = {q["id"]: q for q in facts["questions"]}
        self.assertEqual(questions.all_dependent(by_id["C-13"], facts["questions"]), {"W-15", "W-16", "W-17", "W-18", "W-19"})
        self.assertEqual(questions.all_dependent(by_id["C-14"], facts["questions"]), {"W-18", "W-19"})
        self.assertEqual(questions.all_dependent(by_id["C-04"], facts["questions"]), {"W-03", "W-04", "W-05", "W-06"})

    def test_the_order_as_built(self):
        facts = questions.check(*rendered(), FINDINGS_TEXT)[1]
        self.assertEqual([q["id"] for q in facts["questions"]],
                         ["C-13", "C-04", "C-01", "C-05", "C-06", "C-11", "C-12", "C-14", "C-08", "C-10", "C-15"])

    def test_counts_never_rise_down_the_list(self):
        facts = questions.check(*rendered(), FINDINGS_TEXT)[1]
        counts = [len(questions.all_dependent(q, facts["questions"])) for q in facts["questions"]]
        self.assertEqual(counts, sorted(counts, reverse=True))
        self.assertEqual(counts, [5, 4, 2, 2, 2, 2, 2, 2, 2, 1, 1])

    def test_two_entries_swapped_is_reported(self):
        texts = list(rendered())
        a, b, c = texts[0].index("## 1. C-13"), texts[0].index("## 2. C-04"), texts[0].index("## 3. C-01")
        texts[0] = texts[0][:a] + texts[0][b:c].replace("## 2.", "## 1.") + texts[0][a:b].replace("## 1.", "## 2.") + texts[0][c:]
        got = problems(texts)
        self.assertTrue(any("not in order of how much work depends on them" in p and "should be C-13, C-04" in p for p in got), got)

    def test_equal_counts_go_by_effort_then_finding(self):
        def change(by_id, cands):
            cands.remove(by_id["C-05"])
            cands.remove(by_id["C-14"])
        texts = rendered(change, [p for p in candidates.PIECES if p[0] not in ("W-05", "W-06", "W-18", "W-19")])
        facts = questions.check(*texts, FINDINGS_TEXT)[1]
        self.assertEqual([q["id"] for q in facts["questions"]], ["C-13", "C-01", "C-04", "C-06", "C-11", "C-12", "C-08", "C-10", "C-15"])

    def test_effort_decides_between_equal_counts_before_finding_number(self):
        two = [{"id": "C-01", "finding": "F-02", "answers": [{"pieces": ["W-01"]}, {"pieces": []}]},
               {"id": "C-02", "finding": "F-05", "answers": [{"pieces": ["W-02"]}, {"pieces": []}]}]
        efforts = {"F-02": {"effort": "small"}, "F-05": {"effort": "large"}}
        self.assertEqual([q["id"] for q in sorted(two, key=lambda q: questions.order_key(q, two, efforts))], ["C-02", "C-01"])

    def test_a_wrong_stated_count_is_reported(self):
        got = problems(edited(0, "- Work that depends on the answer: 5 pieces", "- Work that depends on the answer: 7 pieces"))
        self.assertTrue(any('C-13 says "7 pieces' in p and "the answers give 5" in p for p in got), got)

    def test_wrong_numbering_is_reported(self):
        got = problems(edited(0, "## 3. C-01", "## 4. C-01"))
        self.assertIn("The question list is numbered 4 where 3 is expected.", got)


class OnlyIf(unittest.TestCase):
    def test_waiting_for_a_question_that_is_not_asked(self):
        got = problems(edited(0, "- Asked only if: C-13 is answered A or C", "- Asked only if: C-02 is answered A"))
        self.assertTrue(any("C-14 is asked only if C-02 is answered a certain way, and C-02 is not in the question list" in p for p in got), got)

    def test_waiting_for_an_answer_that_does_not_exist(self):
        got = problems(edited(0, "- Asked only if: C-04 is answered B or C or D", "- Asked only if: C-04 is answered B or E"))
        self.assertTrue(any("C-05 is asked only for answers of C-04" in p for p in got), got)

    def test_waiting_for_every_answer_is_not_waiting(self):
        got = problems(edited(0, "- Asked only if: C-04 is answered B or C or D", "- Asked only if: C-04 is answered A or B or C or D"))
        self.assertTrue(any("C-05 is asked only for answers of C-04" in p for p in got), got)

    def test_a_question_placed_before_the_one_it_waits_for(self):
        texts = list(rendered())
        a, b, c = texts[0].index("## 2. C-04"), texts[0].index("## 4. C-05"), texts[0].index("## 5. C-06")
        texts[0] = texts[0][:a] + texts[0][b:c] + texts[0][a:b] + texts[0][c:]
        got = problems(texts)
        self.assertTrue(any("C-05 comes before C-04, the question it waits for" in p for p in got), got)

    def test_without_its_condition_the_parent_count_falls_and_is_reported(self):
        got = problems(edited(0, "- Asked only if: C-13 is answered A or C\n", ""))
        self.assertTrue(any('C-13 says "5 pieces' in p and "the answers give 3" in p for p in got), got)


class DefaultsAndRoles(unittest.TestCase):
    def test_no_default(self):
        got = problems(edited(0, "- Suggested default: B. This assumes that staff work at a desk with a desktop browser.\n", ""))
        self.assertTrue(any("C-10 suggests no default" in p for p in got), got)

    def test_a_default_that_is_not_an_answer(self):
        got = problems(edited(0, "- Suggested default: B. This assumes that staff work at a desk", "- Suggested default: C. This assumes that staff work at a desk"))
        self.assertTrue(any("C-10 suggests default C, which is not one of its answers" in p for p in got), got)

    def test_a_default_with_no_assumption(self):
        got = problems(edited(0, "- Suggested default: B. This assumes that staff work at a desk with a desktop browser.", "- Suggested default: B."))
        self.assertTrue(any("C-10 suggests no default" in p for p in got), got)

    def test_nobody_to_answer(self):
        got = problems(edited(0, "- Best placed to answer: Technical lead\n- Work that depends on the answer: 1 piece", "- Work that depends on the answer: 1 piece"))
        self.assertTrue(any("names nobody best placed to answer" in p for p in got), got)

    def test_every_role_is_from_the_list_and_no_file_holds_an_address(self):
        for c in candidates.CANDIDATES:
            self.assertIn(c["role"], candidates.ROLES)
        for text in rendered():
            self.assertNotIn("@", text)


class Command(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.mkdtemp(prefix="gtq-questions-")
        self.addCleanup(shutil.rmtree, self.scratch, True)

    def run_main(self, *argv):
        said = []
        return questions.main(list(argv), say=said.append), said

    def test_build_then_check_in_a_scratch_folder(self):
        self.assertEqual(self.run_main("build", "--folder", self.scratch)[0], 0)
        code, said = self.run_main("check", "--folder", self.scratch)
        self.assertEqual(code, 0)
        self.assertTrue(said[-1].startswith("CHECK PASSED."))

    def test_check_fails_with_exit_code_1_and_names_the_problem(self):
        self.run_main("build", "--folder", self.scratch)
        path = os.path.join(self.scratch, "questions.md")
        text = questions.read(path).replace("- Finding: F-09 (", "- Finding: F-91 (")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        code, said = self.run_main("check", "--folder", self.scratch)
        self.assertEqual(code, 1)
        self.assertIn("PROBLEM: C-15 links to F-91, which is not a finding in the ambiguity review.", said)
        self.assertEqual(said[-1], "CHECK FAILED. 1 problem.")

    def test_check_with_a_file_missing_does_not_pass(self):
        code, said = self.run_main("check", "--folder", self.scratch)
        self.assertEqual(code, 1)
        self.assertIn("questions.md", said[-1])

    def test_an_empty_question_list_does_not_pass(self):
        self.run_main("build", "--folder", self.scratch)
        with open(os.path.join(self.scratch, "questions.md"), "w", encoding="utf-8") as f:
            f.write("# Questions\n")
        code, said = self.run_main("check", "--folder", self.scratch)
        self.assertEqual(code, 1)
        self.assertTrue(any("no questions that could be read" in line for line in said))

    def test_no_command_explains_itself(self):
        self.assertEqual(self.run_main()[0], 2)

    def test_check_changes_no_file(self):
        self.run_main("build", "--folder", self.scratch)
        before = {n: questions.read(os.path.join(self.scratch, n)) for n in os.listdir(self.scratch)}
        self.run_main("check", "--folder", self.scratch)
        self.assertEqual({n: questions.read(os.path.join(self.scratch, n)) for n in os.listdir(self.scratch)}, before)


if __name__ == "__main__":
    unittest.main()
