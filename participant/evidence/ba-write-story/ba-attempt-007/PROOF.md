# PROOF: Write a Story with Value, Scope, Criteria, Dependencies, and Source

Quest `ba-write-story`, attempt `ba-attempt-007`.

## How this was made

The story, the standard, the skill, its tests, the recording scripts and this document were written by an AI
assistant (Claude) at the participant's direction. The participant made two decisions: the story is "guest
checkout without an account", from work item W-01 of the checkout meeting; and every criterion states its
basis, SAID by the meeting or ASSUMED by the writer, with the two never mixed.

**The meeting is made up.** Nobody in it is a real person, and no real customer's data is in the story. The
transcript record, the decisions file and the work-items file come from earlier quests. They were read and not
changed. **Nothing was created in any tracker**, and nothing outside the participant's computer was contacted.

**Lines of a transcript are things people said.** One line of this meeting is worded as an instruction to an
assistant. It is sample data. It was not followed, and the story lists it as a line it does not use.

Words used below: **recorded** means the saved log of the check shows it. **tested** means an automated test
checks it. **observed** means an independent reader's reply shows it. **not assessed** means nobody checked it.

## The short version, including what was not achieved

The story meets criteria 1 to 6. **It does not meet criterion 7 as the quest words it**, and I do not think
any story written from this meeting could.

Three independent testers each wrote a test for every criterion. The last of them then counted: none of the
18 could be run without asking something, nine could be run once the story's own listed questions were
answered, and nine needed something the story does not mention. The meeting named no test address, no payment
provider and no field of the checkout but two. No wording of a criterion can supply those.

What the story does is make every gap visible. Of its 18 criteria, 8 state something the meeting said and 10
are the writer's proposals, marked as such, each tied to an open question. There are 21 open questions.

## Approach

**The out-of-scope list was written first**, as the hint says, before any criterion.

Then each criterion was written as one starting state, one action and one result, and given a basis:

| Basis | Meaning | What it carries |
|---|---|---|
| **SAID** | the meeting stated the requirement | the lines, quoted with their speakers, and every word in it that the writer had to define |
| **ASSUMED** | the meeting did not state it. The writer proposes it so the story can be tested | who is to confirm it, and the open question it answers |

The program writes the story file, copying every quotation from the record, and its `check` reads the
finished file back. A program can check the form of a story. It cannot tell whether a criterion can be tested
or whether it says more than the meeting did. So five independent readers were asked, in two rounds, and what
they found is below.

## What I left out of scope, and why (criterion 2)

This is what the quest asks the proof to explain. Seven things are out. Each entry in the story says why, and
where it went.

**1. The offer to link a guest's order to an account they already have.** This is the one that matters, and
it is **my boundary, not the meeting's.** The product owner said: "Acceptance criteria: a guest can pay with a
card, gets an email receipt, and is offered account linking once, after the order is placed." Three criteria
of one story, and I took the third out.

Why: two parts of it are not settled. How often the offer is made was answered and taken back in one line.
Whether it times out was parked. A story with those in it could not be built yet, and this one can be built
and tested without them. That is a reason to split. It is not something the meeting decided. An earlier
version of the story called it "a separate work item", as if that settled it. A reader pointed out that the
separation came from my own earlier extraction and from nothing anyone said. So the entry now opens in
capitals, the head of the story says it, and it is open question Q-07.

**2. Any time-out on that offer.** It was asked about and parked. Nobody said one should be built.

**3. What is done with the phone number once given**: the shipping label, and keeping it out of marketing. The
earlier work-items file made that a separate item. This story only takes the number. The boundary is mine.

**4. Sending staging receipts to a test address.** It is test set-up. The story's tests use the address and
do not set it up.

**5. Any way of paying other than a card.** The meeting said a guest can pay with a card and named no other.
That no other is built is my reading.

**6. Offering a guest an account from the checkout.** Nothing was said about one. The story does not build an
offer. It also does not forbid one, which the first version did by accident: its criterion said "no step asked
them to create an account", and the meeting had only said nobody is made to.

**7. Checkout for a customer who is signed in.** Nothing was said about changing it.

The first version listed an eighth, "the size of the work". A reader said that is not a thing left unbuilt.
It is an open question, and it is now only that.

**One thing went the other way, into scope.** The first version left out a rule the meeting had decided: a
guest's order is not attached to the account "until they say yes". A build that attached the order by its
email address would have passed every criterion. It is now AC-07. Even so, a reader of the second version
called AC-07 the part with the most of its author in it: the story has no step that asks, so the criterion
tests "never attached", by a page the meeting never mentioned. Its note now says exactly that.

## The criteria, one by one

| # | Criterion | Status | Where |
|---|---|---|---|
| 1 | The story names the user and the value they gain | recorded, tested, with a limit | `participant/context/stories/story-001.md`, "The story". Each cites the meeting. `logs/story-check.txt` part 3. **The limit:** the "value" is what the customer can then do. The meeting did not say why that matters, and the story says it did not, without inventing a reason |
| 2 | In-scope and out-of-scope are both listed | recorded, tested | 7 and 7. Part 4. Each out-of-scope entry says why and where it went. Each in-scope entry names the criteria that test it |
| 3 | Each acceptance criterion is numbered and observable | recorded and tested for the numbering and the form. observed for "observable", with faults | AC-01 to AC-18, in order. Part 5: each has one Given, one When, one Then. Readers found that the first version's criteria were often not one result. The second version's mostly are. Two still check two things |
| 4 | Dependencies are listed or stated as none | recorded, tested | Four, each SAID or ASSUMED. Part 9. All four are marked ASSUMED: the meeting agreed a test address, and did not say this story waits on anything |
| 5 | The source of the need is cited to utterance identifiers | recorded, tested | Part 7. 47 citations to 17 lines. Every identifier exists, every quotation is the record's own words, and every line of the meeting is cited or listed with why it is not used |
| 6 | No criterion uses an undefined word such as fast, easy or intuitive | recorded and tested against a list. observed to be insufficient | Part 6. The standard lists 67 words. The only one any criterion uses is "valid", which the story defines. **Readers found words that are not on any list and still cannot be measured**, such as "directly below" |
| 7 | A tester could write a test for each criterion without further questions | **not met.** observed | `logs/blind-read.txt`. Three testers wrote a test for every criterion. None could run them without questions: 0 of 18 with none, 9 once the story's listed questions are answered, 9 needing something the story does not mention |

## Artifacts

| Required item | File |
|---|---|
| The story | `participant/context/stories/story-001.md` |
| The story standard | `participant/context/stories/story-standard.md`. Section 3 says what makes a criterion testable |
| The story check | `logs/story-check.txt`, 59 checks |
| This narrative | `PROOF.md` |

Also here: `logs/blind-read.txt`; `logs/tests.txt` (94 tests); `logs/planted-bugs.txt` (33 planted bugs);
`review/story-as-first-read.md`, the first version, as three readers read it; and `scripts/`. The skill is
`participant/skills/ba-write-story/`: `SKILL.md`, `story.py`, `story_001.py`, `tests/test_story.py`.

The story and the standard are written by the skill. A test and a log check compare each with what the code
writes, so neither was adjusted by hand.

## Stretch goals

- **A definition-of-done checklist separate from the criteria:** done. Five lines in their own section. The
  check fails a story that mixes the two. None of it is from the meeting, and it says so.
- **Link the story to the open questions that still affect it:** done. 21 questions, each listing the criteria
  that depend on it. One comes from an open item of the decisions file. The rest the meeting never raised.

## Reproduce

    python3 participant/skills/ba-write-story/story.py check
    python3 -m unittest discover -s participant/skills/ba-write-story/tests -v
    python3 participant/evidence/ba-write-story/ba-attempt-007/scripts/record_evidence.py
    python3 participant/evidence/ba-write-story/ba-attempt-007/scripts/planted_bugs.py

None of these contacts anything or changes a record. The fourth changes `story.py` while it runs and restores
it. The independent reads cannot be run again from a script: `scripts/blind_read.py` only writes out findings
copied by hand from the readers' replies.

## What was tested

| What | Result |
|---|---|
| The handed-in story | No problem reported. Exit code 0 |
| Recorded checks | 59, all pass. They include 24 ways of spoiling the story or the record, each reported |
| Automated tests | 94, all pass (`logs/tests.txt`) |
| Planted bugs | 33 put into `story.py` one at a time. Every one made at least one test fail (`logs/planted-bugs.txt`) |
| Independent reads | Three testers and two scope checkers, all AI assistants, in two rounds. Below |

## What the readers found

**The first version passed its own check and failed its own standard.** It had 12 criteria. Both testers said
flatly that the claim in criterion 7 was false. Six criteria had two or three results where the standard says
one. Three had no action. There was no test data at all. "Guest" was defined one way and used another. Three
criteria were the same test. And the check had passed, because the only listed word in any criterion was
"valid", and it was defined.

The scope checker found the same fault I made in the last quest, in a new place. A criterion marked SAID
said "no step asked them to create an account or to sign in". The meeting had said nobody is *made* to log
in. My wording also forbade an optional invitation, which nobody had discussed. And it found the missing
rule, told above.

**The second version** has 18 criteria, one result each, a test set-up, and names for what it takes as given.
A third tester still could not run any of them unaided, and found three criteria that cannot fail on their
own. A second scope checker called it "mostly honest" and found my reading still standing in for the
meeting's in a few places, all since corrected or noted.

**After the second round the story was changed again and not re-read.** The counts 0, 9 and 9 are for the
version before those changes.

Faults found while building, apart from the readers:

- A check in the recording script counted open questions that come from the decisions file and required at
  least two. After a reader showed that one of the two was my own question with the meeting's label on it,
  there was one. The check failed, rightly, on my earlier mistake.
- A criterion said "a not-valid email address". The check for vague words reads whole words, and "not-valid"
  with a hyphen is not the word "valid". So taking the definition of "valid" out of the story changed nothing,
  and a test said so. The criterion now says "an email address that is not valid".
- A check that the test set-up holds data passed on a table with only its heading row.

## What could not be done, and limitations

- **Criterion 7 is not met.** Told above. The gap is in the meeting, and the story shows it.
- **The check tests form.** A story can pass it and be untestable. The first version did.
- **The list of vague words catches only listed words.** "Directly below", "at the top of the page" and "as it
  was typed" are not on it, and a tester could not measure any of them.
- **"SAID" does not mean the whole criterion is the meeting's.** All 8 SAID criteria lean on at least one word
  the writer defined, and the head of the story says so. Two of them, AC-07 and AC-08, carry a requirement of
  the writer's inside a definition. Their notes say which part.
- **AC-02 and AC-06 cannot fail apart from AC-01 and AC-05.** They are the meeting's requirements, seen in the
  same run. A stricter count would call the 18 criteria 16 tests.
- **AC-14 and AC-17 each check two things, and AC-10 and AC-11 each use three values.**
- **The user statement does not cover the whole story.** It says "a customer who does not have an account".
  Three criteria are about an email address that has one. The story admits it and does not resolve it.
- **Ten of 18 criteria are mine.** A product owner might replace every one. They are proposals.
- **No person read the story.** All five readers were AI assistants. The handed-in version was not re-read.
- **The split from the linking offer may simply be wrong.** If the product owner wants one story, most of
  the out-of-scope list goes.

## Reflection

*Which criterion would a developer most likely read two different ways?*

AC-06: when a guest uses an email address that already has an account, "the checkout did not require them to
log in".

One developer reads that as: no step blocks them. A notice saying "you already have an account, log in?" is
fine, as long as they can carry on past it. Another reads it as: the checkout behaves exactly as it would for
an address it has never seen. No prompt, no hint. Those are two different products, and the second one also
decides something nobody in the meeting mentioned, which is whether the checkout tells a stranger that an
address has an account.

All three testers picked this one, without being shown each other's answers. In the meeting it was a
five-word exchange. "Do we make them log in?" "No."

My first version made it worse without my noticing. I wrote "no step asked them to log in". That quietly
chose the second reading, and I filed it under what the meeting said. The meeting said "make". I had changed
one verb and with it the product. The story now takes the first reading, says that it is taking it, defines
"require" so a tester knows what counts, and puts the other reading down as an open question for the person
whose call it is.

What I did not expect from this quest is how little of a story the meeting actually contains. I went in
thinking the job was to write it up well. Ten of my eighteen criteria are things nobody said. What the card
decline looks like, what the receipt holds, how long anyone waits. I had to make them up for the story to be
testable at all, and after two rounds of readers a tester still could not run one of them without asking
somebody something.

So I do not think the standard I wrote makes a story complete. It makes a story honest about what it is
missing, and that turned out to be a different thing and a more useful one. A story that says "ten of these
are my guesses, and here are the twenty-one questions" is less comfortable to hand over than "as a user I
want a better dashboard". Nobody can argue with the dashboard one. Anybody can argue with mine, line by line,
and I think that is what it is for.

## Sensitive values

- No token or credential was used. The quest reads and writes only local files.
- The meeting is invented, and so is everyone in it. No real customer's data is in the story.
- The staging test address is redacted in the transcript record. The story refers to it by a name, E1, and
  does not hold it. The phone number in the test set-up is from a range kept for made-up use.
