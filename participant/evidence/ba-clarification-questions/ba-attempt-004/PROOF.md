# PROOF: Produce Focused Questions That Change the Implementation

Quest `ba-clarification-questions`, attempt `ba-attempt-004`.

## How this was made

The candidate questions, the skill, its tests, the recording scripts and this document were written by an AI
assistant (Claude) at the participant's direction. The participant made three decisions: split each finding
into its single questions and test every one; have each answer name its pieces of work from one fixed list,
with independent readers to test that list; and order the questions by a count of the work that depends on
each.

**The requirements are made up.** RoomSlot is an invented booking system for an invented library. The findings
are those of the participant's approved ambiguity review, which was read and not changed. **Nothing was sent
to anyone.** Every question here is a draft in a file. Nothing outside the participant's computer was
contacted.

Words used below: **recorded** means the saved log of the check shows it. **tested** means an automated test
checks it. **observed** means an independent reader's reply shows it. **not assessed** means nobody checked it.

## Approach

The review has nine findings. Each ends in a question, and several of those hold two questions in one. Split
apart, they gave 16 candidates. A 17th was added later, for a reason given below.

Each candidate lists the answers it could get. Each answer states the work it leads to twice: in a sentence,
and as pieces from one list, `participant/context/clarification/work-pieces.md`. A piece is something a
developer would estimate on its own.

One rule then sorts the candidates, and the program applies it, not the author:

- **asked**, if no two of its answers need the same set of pieces;
- **dropped**, if every answer needs the same set.

The same thing built with another number in a setting is the same set of pieces. That is the quest's hint:
both answers lead to the same code.

The result: **11 questions to ask and 6 dropped**, from 17 candidates.

`questions.py check` reads the finished files, not the tables they were written from, and tests each
criterion that can be tested by a program.

## How the questions were ordered (criterion 6)

This is the first thing the quest asks the proof to explain.

The work that depends on a question is every piece that one of its answers needs and another does not. A
piece every answer needs does not depend on the answer, so it is left out.

Two questions are asked only if another question is answered a certain way. C-14, who tells the members,
arises only if C-13 is answered with bookings being cancelled or moved. So C-13's answer decides C-14's work
as well as its own, and C-13 carries both: 3 pieces of its own and 2 through C-14.

Most first. Where counts are equal, the finding's effort decides (large, then medium, then small), then the
finding's number.

| Place | Question | Depends on it |
|---|---|---|
| 1 | C-13 What happens to bookings in a room that goes out of service | 5 pieces |
| 2 | C-04 What else the system limits to discourage unused bookings | 4 pieces |
| 3 to 9 | C-01, C-05, C-06, C-11, C-12, C-14, C-08 | 2 pieces each |
| 10, 11 | C-10, C-15 | 1 piece each |

The scenario's product owner answers four questions. Here the first four carry 11 of the 21 pieces that
depend on any answer.

**What this order is not.** It is not the order of seriousness. The review ranks a contradiction as the most
serious kind of finding, and it has two. One, F-01, gives the question in third place. The other, F-02, gives
no question at all: both of its candidates were dropped. And the question in first place comes from a finding
of medium effort.

**Its weakness.** Seven questions are level on 2 pieces, so more than half the order is settled by the
tie-break. And every piece counts as one. A second copy of the database on another machine (W-08) counts the
same as a third marking on a slot (W-20). C-06 is in fifth place and may well be the largest decision on the
list. A person reading the list should treat places 3 to 9 as one group.

## One question that was rewritten

This is the second thing the quest asks for. The one chosen is the one that was rewritten because it was
wrong, not only because it was long.

**C-08, as first written:** "How long before a booking starts is the reminder email sent?" with the answers
"About an hour before" and "The evening before". Both were given the same piece of work, a reminder with its
lead time as a setting. So the rule dropped it.

Two independent readers were given the questions and answers without the pieces. One judged C-08's answers
different: the evening before is a fixed hour, sent in one run, and it needs a rule for a booking made after
that run. The other called it the same, borderline, and named the same point. The first reader was right. The
two answers were of different kinds, and the piece of work written beside them had hidden that.

**C-08, as handed in:** "Is the reminder sent a set time before each booking, or at a fixed hour the day
before?" The two answers lead to different pieces, and it is asked, in ninth place. What was left of the old
question, the number of minutes, became candidate C-17, which is dropped: any number builds the same thing.

So the first version dropped a question whose answer changes the work. That is the fault in the quest's
scenario, made here, and it was found by a reader, not by the check. The check compared the pieces as they
were written and passed.

Three more were reworded after the same read, each for criterion 5:

| Question | What the readers said | What changed |
|---|---|---|
| C-04 | Open-ended. Two of its answers could both be wanted | Now "which of these", with a fourth answer, "Both of these" |
| C-05 | "That behaviour" points at nothing when the question is read alone | Now "When a member goes over such a limit" |
| C-12 | A likely answer is missing: after a time, or sooner if staff lift it | A fourth answer added |

C-04 began further back still. The finding's own question is "What that the system can observe would count
as a member not intending to use a room, and what is the system to do when it sees it?" That is two questions
and 30 words, and no list of answers fits it.

## The criteria, one by one

| # | Criterion | Status | Where |
|---|---|---|---|
| 1 | Each question links to a finding from the ambiguity review | recorded, tested | `logs/question-check.txt` part 2. Each entry gives the finding's number and quotes some of that finding's own question. Both are looked up in the review. Six spoiled links are each reported, including a link to F-11, which the review raised and withdrew |
| 2 | Each lists at least two possible answers | recorded, tested | Part 3. Between 2 and 4 answers each |
| 3 | Each possible answer leads to a stated difference in the work | recorded, tested, observed, with a limit | Part 3: in every question asked, no two answers name the same set of pieces, and each states its work in a sentence. `logs/blind-read.txt`: a reader who saw no pieces judged all 11 to lead to different work. **The limit:** the check compares pieces a person wrote. It cannot know they are right. Round 1 of the read shows a case where they were not |
| 4 | A question whose answers lead to the same work is dropped and listed as dropped | recorded, tested, observed | `participant/context/clarification/dropped.md`, 6 questions. Part 4: every answer of each names one and the same set of pieces. A dropped question put in the question list is reported, and so is a candidate that is in neither list. The third reader judged all 6 to lead to the same work |
| 5 | Questions are short enough to answer without a meeting | recorded and tested for the rule. observed, by AI readers only, for the claim | Part 5: one sentence, one question mark, at most 25 words, at most 4 answers. The longest is 19 words. Three of the nine findings' own questions fall outside the rule. The third reader said all 11 could be answered by naming one answer. **No person was asked**, so whether a product owner could answer without a meeting is not assessed |
| 6 | The questions are ordered by how much of the work depends on them | recorded, tested | Part 6. The check works the order out from the answers and compares it with the file. Two questions swapped is reported |
| 7 | Nothing is sent to anyone | recorded | Part 7: with every network connection made to fail, build and check still finish. After a run, Python has loaded no module for connecting, mailing or running another program. The files hold no address. The people best placed to answer are roles, and nobody is named |

## Artifacts

| Required item | File |
|---|---|
| The question list | `participant/context/clarification/questions.md`, 11 questions |
| The dropped list | `participant/context/clarification/dropped.md`, 6 questions, and 3 matters set aside because they are not findings |
| The check | `logs/question-check.txt`, 53 checks |
| This narrative | `PROOF.md` |

Also here: `participant/context/clarification/work-pieces.md`; `logs/blind-read.txt`; `logs/tests.txt` (64
tests); `logs/planted-bugs.txt` (32 planted bugs); `review/`, the two sheets the readers were given and the
key to each; and `scripts/`. The skill is `participant/skills/ba-clarification-questions/`: `SKILL.md`,
`questions.py`, `candidates.py`, `tests/test_questions.py`.

The three files in `participant/context/clarification/` are written by the skill from `candidates.py`. A test
and a log check compare each with what the code writes, so none was adjusted by hand.

## Stretch goals

- **A default for each question, and what it assumes:** done. Each question asked suggests one of its own
  answers and states the assumption. A default is a suggestion to whoever answers. It records no decision.
  They are the assistant's suggestions and nobody who knows a library chose them.
- **Group questions by the person best placed to answer:** done, by role. The library service manager has 7,
  the front-desk supervisor 2 and the technical lead 2. The roles are invented with the product. That one
  role has 7 of 11 is a warning in itself: it is the scenario again, on a smaller scale.

## Reproduce

    python3 participant/skills/ba-clarification-questions/questions.py check
    python3 -m unittest discover -s participant/skills/ba-clarification-questions/tests -v
    python3 participant/evidence/ba-clarification-questions/ba-attempt-004/scripts/record_evidence.py
    python3 participant/evidence/ba-clarification-questions/ba-attempt-004/scripts/planted_bugs.py
    python3 participant/evidence/ba-clarification-questions/ba-attempt-004/scripts/blind_read.py

None of these contacts anything. The third leaves the handed-in files untouched. The fourth changes
`questions.py` while it runs and restores it. The fifth writes out verdicts that were copied by hand from the
readers' replies. The reads themselves cannot be run again from a script.

## What was tested

| What | Result |
|---|---|
| The handed-in files | 17 candidates, 11 asked, 6 dropped. No problem reported. Exit code 0 |
| Recorded checks | 53, all pass. They include 22 ways of spoiling the files, each reported |
| Automated tests | 64, all pass (`logs/tests.txt`) |
| Planted bugs | 32 put into `questions.py` one at a time. Every one made at least one test fail (`logs/planted-bugs.txt`) |
| Independent reads | Round 1, two readers, 16 candidates: agreed with the files on 14 and 15. Round 2, one new reader, 17 candidates: agreed on all 17 |

The readers were AI assistants, each started fresh and told to read only the requirements and a sheet. That
limit was given in words and not enforced. No person read the questions.

Faults found while building:

- **A question was dropped that should have been asked.** C-08, told above.
- **The first order the program wrote was wrong, and the check caught it.** The program sorted a list while
  reading that same list to count dependent work, so every count came out as the question's own. C-04 was
  placed below C-01. The check, which works the order out separately, reported it on the first run.
- A planted bug showed that no test covered the tie-break by effort. In the real data, effort and finding
  number happen to fall in the same order, so ignoring effort changed nothing. A test with made-up findings
  was added.
- A check in the recording script passed for the wrong reason at first: its probe for loaded network modules
  had a syntax error, printed nothing, and "nothing" was not what the check expected, so it failed. Had the
  check been written as "no module name was printed", a broken probe would have passed it.
- One trial spoiled the wrong line: it changed the question in the summary table, where nothing is checked,
  and reported no problem. It was pointed at the question's own line.

## What could not be done, and limitations

- **One question stays in the list against two readers.** Both round 1 readers judged C-10, whether staff
  functions must work in mobile browsers, to lead to the same work: the same screens, rules and data, with
  more layout effort. It was kept, because laying the staff screens out for a small screen is work a
  developer would estimate on its own, which is this quest's definition of a piece. The third reader called
  it different, "the mildest different on the sheet". It is in tenth place of eleven. A reader who sides with
  the first two would drop it, and would not be wrong.
- **The answers listed may not be all the answers.** A question with two answers is only as good as the claim
  that there are two. C-08 and C-12 each gained an answer or a kind of answer after a reader pointed at it.
  Others may be missing one still.
- **Round 2 was one reader, after the questions had been changed to meet the first two.** Agreement was the
  likely result. It does not show a person would agree.
- **Some answers affect each other, and the files say so only for two pairs.** A reader noted that counting
  no-shows over a recent period (C-11, answer B) already lets a suspended member recover with time, which is
  most of what C-12's answer B asks for. The files treat C-11 and C-12 as separate.
- **"Work" leaves out testing and the wording of the requirements.** That is why C-07, how survival is
  checked, and C-16, whether REQ-02 is reworded, are dropped. On a team where test effort is the scarce
  thing, C-07 would be a real question.
- **Dropped does not mean answered.** Four of the six dropped questions still need a value before release,
  and for one of them, C-02, there is no safe value to work with meanwhile. `dropped.md` says so for each.
- **A question still needs a number after it is answered** in four cases: the limits in C-04, the period in
  C-11, the set time in C-12 and the lead time in C-08. Each is a setting, so none changes the work, and each
  is one more thing to ask.
- The pieces of work, the answers and the defaults were all written by one assistant. Nobody who builds
  software for a library, or runs one, has seen them.
- The findings came from an earlier quest's review of requirements written for that quest. No question here
  was tried on requirements somebody needs built.

## Reflection

*Which dropped question do you most expect to be asked anyway, and what would you say?*

C-02: are booking records deleted after 12 months or after 24?

I expect it to be asked because it comes from a contradiction, and a contradiction looks like the most
urgent thing on any list. Two documents say opposite things about the same records. Anyone who reads the
review will see F-02 near the top, see that I am asking about slot markings and not about that, and ask it
for me.

What I would say is: yes, it has to be answered, and no, the build does not wait for it. Whichever number
wins, the same deletion job gets built and the same history screen. What I need is the number before
release, and a decision about which of the two requirements gets reworded. That is not mine to make, and I
cannot even pick a safe value to work with in the meantime, because 12 breaks one requirement and 24 breaks
the other. So it goes to the person who owns the records, as a value with a date on it, and it does not take
one of the few answers I can expect from the person who owns the rules.

I did not expect that. I assumed the contradictions would lead the list. One is third and the other is not
on it, and the question in first place comes from a finding the review rated medium. How serious a defect is
and how much work hangs on its answer turned out to be two different orders.

The part I am less comfortable with is C-08. I dropped the reminder question with a clear conscience: any
lead time, one setting. A reader looked at my two answers and saw that "the evening before" is not a lead
time at all. It is a different way of sending. I had written two answers of different kinds and then
described them as the same work, and my check agreed with me because it checks what I wrote. So "dropped"
is only ever a claim about the answers I managed to imagine. If I were asked about any dropped question, I
would now show the answers I considered along with the reason, so the other person can see the one I missed.

## Sensitive values

- No token or credential was used. The quest reads and writes only local files.
- No real person, library, product or requirement is in any file. The people best placed to answer are roles
  invented with the product.
- No question was sent, posted or shown to anyone outside this computer.
