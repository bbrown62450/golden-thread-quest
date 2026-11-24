# Business analysis: questions whose answers change the work

Written by an AI assistant (Claude) at the participant's direction.

## 1. Purpose

This skill turns the findings of an ambiguity review into a short, ordered list of questions for a person to
answer, and a list of the questions that were considered and dropped.

**It drafts. It sends nothing.** It writes three local files and reads one. It contacts nothing and names no
person.

    python3 participant/skills/ba-clarification-questions/questions.py build
    python3 participant/skills/ba-clarification-questions/questions.py check

Both take `--folder DIR` (where the three files are) and `--findings FILE`. Python standard library only.

## 2. What goes in

- `candidates.py`: the candidate questions, written by hand. Each has the finding it came from, some of that
  finding's own question quoted, its possible answers, and for each answer the work it leads to: a sentence,
  and the pieces of work it needs.
- `candidates.py` also holds the list of work pieces. A piece is something a developer would estimate on its
  own.
- `participant/context/ambiguity/findings.md`: the review. It is read and never written.

A candidate does not say whether it is kept or dropped. That is worked out.

## 3. The rule that sorts them

| Outcome | When |
|---|---|
| asked | no two of its answers need the same set of pieces |
| dropped | every answer needs the same set of pieces |
| neither | some answers need the same set and some do not. `build` stops. Merge the answers that are the same |

"The same work with another number in a setting" is the same set of pieces, so it is dropped. A dropped
question says what is still needed: a value before release, a choice by the test team, or nothing.

## 4. Order

The work that depends on a question is every piece that one of its answers needs and another does not, with
the same for any question that is asked only because of an answer to it. Most first. Equal counts go by the
finding's effort (large, medium, small), then by finding number.

## 5. Short enough

One sentence, one question mark, at most 25 words, at most 4 answers of at most 15 words each. The aim is a
question that can be answered by naming one letter.

## 6. What `check` reports

It reads the three files, not `candidates.py`, so a change made by hand is checked too. It reports:

- a question or dropped question whose finding is not in the review, or whose quoted words are not in that
  finding's question;
- fewer than two answers; an answer with no stated work; a piece that is not in the list;
- a question asked whose answers lead to the same pieces, and a dropped one whose answers do not;
- a candidate in both lists, or in neither;
- a question outside the limits in section 5;
- an order that is not the order in section 4; a question placed before the one it waits for;
- a default that is not one of the answers; a question with nobody named to answer it.

Exit code 0 only if there is nothing to report.

## 7. What it does not do

- **It cannot tell whether two answers really lead to different work.** It compares the pieces that a person
  wrote beside each answer. If the pieces are wrong, the check passes on wrong pieces.
- It does not know whether the listed answers are all the answers a person might give.
- It counts every piece of work as the same size.
- It does not send, post or email anything, and has no code that could.

## 8. Tests

    python3 -m unittest discover -s participant/skills/ba-clarification-questions/tests -v
