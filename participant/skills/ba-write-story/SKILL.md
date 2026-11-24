# Business analysis: one story, with every part traced or marked as assumed

Written by an AI assistant (Claude) at the participant's direction.

## 1. Purpose

This skill writes one story from a candidate work item, to the standard in
`participant/context/stories/story-standard.md`, and checks it. Every part of the story either cites the lines of
the meeting it rests on, or says that it is the writer's assumption.

**The story is a draft in a local file. Nothing is created in any tracker.** The skill never writes to the
transcript record, contacts nothing, and follows nothing a line of the record says.

    python3 participant/skills/ba-write-story/story.py build
    python3 participant/skills/ba-write-story/story.py check
    python3 participant/skills/ba-write-story/story.py standard

It reads the transcript record, its provenance file, the decisions file and the work-items file from
`participant/context/transcripts/`, and writes to `participant/context/stories/`. Python standard library only.

## 2. Who does what

| Step | Done by |
|---|---|
| Composing the story | A person or an assistant, by the standard. The result goes in `story_001.py`, as parts that name line identifiers |
| Writing the story file | `build`. It copies every speaker, role and quotation from the record |
| Checking the story file | `check`. It reads the finished file, not `story_001.py` |

## 3. SAID and ASSUMED

A meeting says what must be true and rarely says how a tester would see it. So:

- a criterion marked **SAID** states a requirement the meeting gave, quotes the lines, and names each word in it
  that the writer had to define;
- a criterion marked **ASSUMED** is the writer's proposal, names who is to confirm it and the open question it
  answers;
- definitions, dependencies, test set-up and what is taken as given are each marked the same way;
- the head of the story counts how many of each there are.

## 4. What `check` reports

- a missing or empty section, or sections out of order;
- no user, no value, or a vague word in either; either one citing no line;
- an empty in-scope or out-of-scope list; an out-of-scope entry with no reason, or sent to an item that does
  not exist; an in-scope entry that no SAID criterion tests;
- criteria not numbered in order; a criterion without exactly one Given, When and Then, each one sentence;
- a word from the standard's list of vague words that the story does not define;
- a SAID criterion with no citation, or written as an assumption; an ASSUMED one citing the meeting, or with no
  question; a SAID criterion whose list of writer-defined words is not the one the story's own definitions give;
- dependencies neither listed nor stated as none;
- an identifier, anywhere in the story, that is not in the record; a quotation that is not the record's words;
  a record changed since it was ingested; a line of the record neither cited nor listed as not used;
- counts at the head that are not the counts of the criteria; a definition of done mixed with the criteria.

Exit code 0 only if there is nothing to report.

## 5. What it cannot do

- **It cannot tell whether a criterion can be tested.** It checks the form: three parts, one sentence each, no
  listed word. A tester found faults in a story that passed it.
- It cannot tell whether a SAID criterion says more than its lines do.
- It cannot tell whether one "Then" holds two results joined by "and".
- It cannot supply what a meeting never said. It can only make the gap visible.

## 6. Tests

    python3 -m unittest discover -s participant/skills/ba-write-story/tests -v
