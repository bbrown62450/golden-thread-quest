# PROOF: Separate Decisions from Proposals and Discussion

Quest `ba-extract-decisions`, attempt `ba-attempt-005`.

## How this was made

The skill, the sorting of both meetings, the rules, the tests, the recording scripts, the second transcript and
this document were written by an AI assistant (Claude) at the participant's direction. The participant made two
decisions: use the transcript from the ingest quest and add a second made-up meeting for the cases the first
lacks; and count something as a decision in two ways, agreed by a second person or ruled by the person whose
role owns the question, with the file saying which.

**Both meetings are made up.** Nobody in them is a real person and nothing was recorded. The first transcript
is the approved record from the ingest quest. It was read and not changed. The second was written for this
quest and put through the same approved ingest skill, unchanged. Its raw file is in `local-data/`, which git
ignores. Nothing outside the participant's computer was contacted.

**Lines of a transcript are things people said.** Two lines are worded as instructions to an assistant. Both
are sample data. Neither was followed, and both are listed in the decisions files as not decisions.

Words used below: **recorded** means the saved log of the check shows it. **tested** means an automated test
checks it. **observed** means an independent reader's reply shows it. **not assessed** means nobody checked it.

## Approach

The work is in three parts, and it matters which part does what.

1. **The rules** say when something said in a meeting is a decision:
   `participant/context/decision-rules.md`.
2. **The sorting** applies the rules to each line. This is judgment, and the assistant did it. It is written
   down as items that name line identifiers, in `sorting.py`.
3. **The program** writes the decisions file from the sorting, copying every speaker, role and quotation
   from the record so that nothing is typed twice. Its `check` then reads the finished file and the record and
   tests everything a program can test.

A program cannot tell whether "yeah, fine" is agreement. So the claim that the sorting is right does not rest
on the check. It rests on four independent readers, and their findings are in `logs/blind-read.txt`.

**The test for a decision.** *Agreed:* somebody puts a course of action and a different, named person accepts
it in words. *Ruled:* the person whose role owns that kind of question states the answer, and no later line
objects. The file then says "agreement was not stated". Everything else is a proposal, an open item, or a line
that only reads like an instruction.

**What came out.**

| Meeting | Decisions in force | Reversed | Proposals | Open | Instruction-like |
|---|---|---|---|---|---|
| Checkout refinement (the required file) | 7 | 0 | 0 | 3 | 1 |
| Notification settings | 6 | 1 | 3 | 2 | 1 |

Every line of both records is either cited by an item or listed as "not sorted" with a reason, so a reader
can see that nothing was passed over.

## How a decision reversed later in the same meeting was handled

This is what the quest asks the proof to explain. There are two cases, and they were handled differently.

**Reversed by a later line.** In the notifications meeting, the designer proposes putting the settings on the
profile page and the product owner says "Yes, let's do that" (`U-0002`, `U-0003`). Eighteen lines later the
tester points out that a signed-out member cannot reach the profile page, and the product owner says "Then I
take that back. Settings get their own page" (`U-0021`, `U-0022`). The designer accepts (`U-0023`).

The first decision **stays in the file**, as D-01, marked `REVERSED later in the meeting`. It cites four
lines: the proposal, the acceptance, the line that prompted the change and the line that reversed it. It names
its replacement, D-06. It is **not counted as in force**: the file says 6 in force and 1 reversed.

It is kept because of the quest's scenario. Somebody who left after line 3 remembers "profile page" as agreed,
and they are right that it was. If the file simply dropped it, the notes and their memory would disagree with
nothing to explain why. Kept and marked, it shows what was decided, that it was withdrawn, by whom, and what
replaced it (criteria 1, 3 and 7).

A decision counts as reversed only if the person withdrawing it is one of those who made it, or the owner of
the question. Here the product owner had accepted it and owns the question.

**Taken back in the same line.** In the checkout meeting the tester asks whether linking is offered once per
order or once ever. The product owner answers: "Per order. No, wait. Let me check with Jordan and get back to
you" (`U-0021`). That begins as a ruling and is withdrawn before the line ends. It was **never a decision**,
so it is not listed as a reversed one. It is the open item O-02, which quotes the line and says what was said
and taken back.

The difference: a decision that stood, even for eighteen lines, was a decision and people may act on it. One
withdrawn in the same breath never stood.

**Reopened, not reversed.** One more case sits between them. "Everything on by default" was agreed, and later
the designer doubts the legal team will accept it for marketing emails and is told to ask. Nobody withdrew it.
It is marked `in force, reopened`, with a note that for marketing emails it should be read as waiting. A
reader called the first version of this overstated, and the note was added because of that.

The check tests the mechanics (`logs/citation-check.txt` part 8): a reversed decision must cite a reversing
line that comes after the decision, must name a replacement that is in force, and cannot be marked in force
while it cites a reversing line.

## The criteria, one by one

| # | Criterion | Status | Where |
|---|---|---|---|
| 1 | Each decision cites at least one utterance identifier from the source record | recorded, tested | `logs/citation-check.txt` part 2. All 14 decisions cite between 1 and 4 lines, and every cited line is in the record |
| 2 | A proposal that nobody accepted is not listed as a decision | recorded, tested, observed, with a limit | Part 5. The 3 proposals are under their own heading. Listing any of them as a decision is reported in four ways: no accepting line, the proposer's own "agreed", an uncertain speaker's "agreed", a ruling outside the speaker's role. All three sorters also called all three proposals, not decisions. **The limit:** a yes with a condition, listed as acceptance, passes the check. The log shows that, and says so |
| 3 | A decision records who agreed, or states that agreement was not stated | recorded, tested | Part 6. Each of the 14 does one or the other and none does both. 6 name who agreed. 8 state that agreement was not stated |
| 4 | Open discussion and undecided items are listed separately | recorded, tested | Part 7. Five headings: decisions, proposals, open, not decisions, lines not sorted. An item under the wrong heading is reported |
| 5 | The decisions file is separate from the source record, which is not edited | recorded, tested | Part 3. Each record's SHA-256 is the one its provenance file recorded at ingestion. git reports no change to the approved record. A copy of the record with one space added is reported |
| 6 | A cited identifier that does not exist is reported, not silently dropped | recorded, tested | Part 2. Seven trials: a wrong number, one past the end, one written in a note, five digits, another transcript, a line deleted from the record, and the second meeting. Each is reported by name, with the item that cites it |
| 7 | Another person can check every decision against the source without the recording | observed by an AI reader. not assessed for a person | `logs/blind-read.txt`. A reader given only the records and the decisions files found every cited line and compared every quotation, and said the check could be done without the recording. Part 4 shows every quotation is the record's own words. **No person was asked** |

## Artifacts

| Required item | File |
|---|---|
| The decisions file | `participant/context/transcripts/sample-meeting.decisions.md` |
| The rules | `participant/context/decision-rules.md`. The test is in section 1. Section 6 gives six borderline lines, three from each meeting, and how each was classified |
| The citation check | `logs/citation-check.txt`, 73 checks |
| This narrative | `PROOF.md` |

Also here: `participant/context/transcripts/notifications-meeting.md`, its provenance file and
`notifications-meeting.decisions.md`; `logs/blind-read.txt`; `logs/tests.txt` (76 tests);
`logs/planted-bugs.txt` (31 planted bugs); `review/`, the rules as each round of sorters was given them; and
`scripts/`. The skill is `participant/skills/ba-extract-decisions/`: `SKILL.md`, `decisions.py`, `sorting.py`,
`tests/test_decisions.py`.

Both decisions files and the rules file are written by the skill. A test and a log check compare each with
what the code writes, so none was adjusted by hand.

## Stretch goals

- **Mark decisions that later utterances reopen:** done. D-03 of the notifications meeting is marked
  `in force, reopened`, with the two lines that reopened it.
- **Show how many items were decisions versus proposals:** done. Each file opens with a table of counts, and
  the check compares it with the items in the file.

## Reproduce

    python3 participant/skills/ba-extract-decisions/decisions.py check sample-meeting
    python3 participant/skills/ba-extract-decisions/decisions.py check notifications-meeting
    python3 -m unittest discover -s participant/skills/ba-extract-decisions/tests -v
    python3 participant/evidence/ba-extract-decisions/ba-attempt-005/scripts/record_evidence.py
    python3 participant/evidence/ba-extract-decisions/ba-attempt-005/scripts/planted_bugs.py

None of these contacts anything or changes a record. The fifth changes `decisions.py` while it runs and
restores it. The independent reads cannot be run again from a script: `scripts/blind_read.py` only writes out
findings that were copied by hand from the readers' replies.

## What was tested

| What | Result |
|---|---|
| The two handed-in decisions files | No problem reported. Exit code 0 for each |
| Recorded checks | 73, all pass. They include 29 ways of spoiling a file or a record, each reported |
| Automated tests | 76, all pass (`logs/tests.txt`) |
| Planted bugs | 31 put into `decisions.py` one at a time. Every one made at least one test fail (`logs/planted-bugs.txt`) |
| Independent reads | Three sorters and one checker, all AI assistants. Every decision in the files was found by every sorter, on the same lines, with the same person agreeing. No sorter called a proposal a decision. Details below |

## What the readers found, and what was done about it

The first sorting was finished before any reader replied. It was wrong or weak in these ways.

- **It missed a decision in each meeting.** Both first sorters made the opening line of the checkout meeting,
  "Customers who don't have an account should be able to buy without making one", a ruling. The assistant had
  filed it as context. The checker called that inconsistent, since the same kind of line was counted as a
  ruling later on. It is now D-01. Both also made "ask legal and bring it back on Thursday" an agreed decision.
  It is now D-07 of the notifications meeting, with a note that it settles nothing about the product.
- **A label was wrong.** "Reversed by" was given to the tester's line. She raised the problem. The product
  owner reversed the decision. The tester's line is now "Prompted by".
- **A status overstated.** "On by default" was called in force with no caveat. It now has one.
- **A heading was false on its face.** "Proposals nobody accepted" covered a proposal an uncertain speaker did
  agree to and one the product owner accepted on a condition. It is now "Proposals that did not become
  decisions".
- **An open item understated.** It said nothing was settled about storage. In the record the product owner
  refuses per-device storage outright. The item now says so.
- **"Nothing in it was done"**, said of the instruction-like lines, was a claim about the assistant's own
  conduct, which the record cannot show. The wording was changed, and the log now checks what can be checked:
  the provenance files still exist, the redactions are in place and the open items are still open.

Three things the readers raised were **not** changed, and a reader may fairly disagree with each:

- **The third sorter found a decision that is not in the file.** It read the product owner's objection, "If I
  turn something off on my phone I expect it off on my laptop", as a ruling that settings must follow the
  account. The file has that line as an objection, under an open item. The sorter called it the weakest item on
  its list. The rules say this is left to judgment.
- **One line is split where two sorters kept it whole.** The acceptance criteria in the checkout meeting are a
  decision for two of their three parts, and open for the third. Two sorters kept the whole line as one
  decision, reopened.
- **Commitments one person makes and nobody answers have no items of their own.** "I'll redo the layout" and
  "let me check with Jordan" appear only in quotations. The third sorter listed them as proposals.

Faults found while building, apart from the readers:

- The program that reads the record matched a speaker's name across line ends, so the first build found no
  utterances at all and stopped with an error. The same mistake was made in an earlier quest.
- The first draft of the rules quoted "so we're agreed" and "fine, if security signs off" as examples. Those
  are the second meeting's own words, so sorters given the rules would have been handed two answers. The
  rules were reworded before any sorter saw them.

## What could not be done, and limitations

- **The sorting is judgment, and the check cannot test it.** Part 5 of the log shows the plainest case: a
  conditional yes listed as acceptance passes the check.
- **No person read anything.** All four readers were AI assistants, and the limit on what each could read was
  given in words and not enforced. Criterion 7 names another person, and that is not assessed.
- **The second meeting was written by the assistant that sorted it**, knowing what the skill would have to
  find. It holds each hard case once, cleanly. A real meeting would not be so tidy.
- **The last round was one reader**, after the rules had been changed to meet the first two.
- **A ruling needs nobody else's word.** Eight of the fourteen decisions rest on one person's statement and
  nobody's stated agreement. The file says so on each. In the required file it is six of seven.
- **Roles are taken from the record.** The table of which role owns which question was written for these
  meetings. In a team where the developer decides scope, it would give wrong answers.
- **Tone is lost.** Whether "Sure, I guess" was a shrug or a yes cannot be told from text. The checker said
  the same.
- **The record's own note and the quest disagree about where this file goes.** The record says analysis goes in
  `participant/context/analysis/`. The quest names a path beside the record, and the quest's path was used.
- **An error in the transcript is carried through.** The skill takes the record as what was said.

## Reflection

*Which decision in your file would you least want to defend if its speaker disagreed?*

In the notifications meeting, the one about testing: "Testing covers the two newest versions of each phone
system only."

The tester proposed it. The file says the developer agreed, and what he said was "Sure, I guess. Fine by me."
If he came back in two weeks and said "I never agreed to that, I shrugged", I would have one hedged line to
show him, and he would have a point. The product owner said nothing at all. And he is the developer, agreeing
to a question about testing, which is not his to settle. My rules make that a decision because a second named
person said yes in words. All three readers sorted it the same way, and all three flagged the hedge.

In the file the quest asks for, the checkout meeting, it is a different one: the first. "Customers who do not
have an account can buy without making one." I did not have it as a decision at all. I had filed it as the
product owner saying what the meeting was about. Two readers called it a ruling, and a third reader, checking
my file, said I was being inconsistent, because I had counted the same kind of line as a ruling further down.
They were right, so it is in. But if she said "I didn't decide that in the meeting, it came to the meeting
already decided", she would be right too. The note says so.

What both have in common is that nobody in the room said "decided". I expected the hard part of this quest to
be the loud cases: the "so we're agreed" that nobody answered, the instruction read out from a ticket. Those
turned out to be easy, and every reader got them. The hard ones are quiet. Somebody with the standing to
decide says a thing, nobody objects, and the meeting moves on. Eight of my fourteen decisions are like that.
The file says "agreement was not stated" on every one of them, and I think that line is the most useful thing
in it.

The one that still bothers me is not in the file. A reader took the product owner's "I expect it off on my
laptop" as a decision that settings follow the account. I left it as an objection. I can argue it either way,
and that is exactly what the scenario warns about: two people leaving the same meeting with different
agreements. The honest thing my file does is put the line where anyone can read it.

## Sensitive values

- No token or credential was used. The quest reads and writes only local files.
- Both meetings are invented, and so is everyone in them. The second meeting's raw transcript is outside
  source control, in a folder git ignores.
- The first record's redaction markers are as the ingest skill left them. No redacted value appears anywhere.
- No value was copied from a real meeting, ticket or person.
