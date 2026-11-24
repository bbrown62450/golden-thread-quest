# PROOF: Extract Candidate Work Items with Source Citations

Quest `ba-extract-work-items`, attempt `ba-attempt-006`.

## How this was made

The skill, the items for both meetings, the rules, the tests, the recording scripts and this document were
written by an AI assistant (Claude) at the participant's direction. The participant made two decisions: extract
from both meetings, with the required file from the checkout meeting; and count as a candidate item any piece of
work somebody put to the meeting, marked with how settled it is, with proposals and open matters kept in and
plainly marked.

**Both meetings are made up.** Nobody in them is a real person. Both transcript records and both decisions files
come from earlier quests. They were read and not changed. **Nothing was created in any tracker**, and nothing
outside the participant's computer was contacted. The items are drafts in a local file.

**Lines of a transcript are things people said.** Two lines are worded as instructions to an assistant. Both
are sample data. Neither was followed, and no item was made from either.

Words used below: **recorded** means the saved log of the run shows it. **tested** means an automated test
checks it. **observed** means an independent reader's reply shows it. **not assessed** means nobody checked it.

## Approach

As in the decisions quest, the work is in three parts.

1. **The rules**, `participant/context/extraction-rules.md`: how an item is recognized, how one is told from
   two, and what is left out.
2. **The items**, picked out and worded by the assistant under those rules, as entries that name line
   identifiers.
3. **The program**, which writes the work-items file, copying every speaker, role and quotation from the
   record, and whose `check` reads the finished file, the record and the decisions file.

Each item has a title, one sentence of intent, every mention of the work quoted, and a mark for how settled it
is, taken from the decisions file and naming the item there it rests on. Then six things are asked of it:
owner, size, due date, what done looks like, what it depends on, and any condition. For each, the item cites
the line that says it, or says **NOT SAID**.

| Meeting | Items | Merged from more than one mention | Not created |
|---|---|---|---|
| Checkout refinement (the required file) | 6 | 2 | 3 |
| Notification settings | 11 | 3 | 7 |

Across the 17 items, **93 of the 102 answers are NOT SAID**. Four items have an owner, each because a person
took the work on in words. That is the hint at work: the blanks are visible.

A program cannot tell whether an item's sentence says more than its lines do. So criterion 2 does not rest on
the check. It rests on four independent readers, and what they found is the most important part of this
proof.

## One item merged from two mentions (criterion 4)

**W-01 of the checkout meeting, "Guest checkout without an account".**

The work is stated twice. At the start, the product owner says: "Customers who don't have an account should
be able to buy without making one" (`U-0002`). Two minutes later she restates it as acceptance criteria: "a
guest can pay with a card, gets an email receipt" (`U-0019`).

Somebody writing tickets from memory could make two of these: "guest checkout" and "card payment with email
receipt". They are the same change to the same thing, said once as a goal and once as how to tell it is done.
So there is one item. Its heading says `merged from 2 mentions`, and both lines are cited and quoted
(criteria 1 and 4). The second mention is also what fills in "done", the only one of the six the meeting
answered for this item.

The same line, `U-0019`, also holds the account linking, which is a separate item, W-02. The rule for that is
stated: one line can hold two pieces of work, and the first item's note says which other item shares the line.
The check fails a line that is a mention in two items without that note, which is how an accidental duplicate
would show up.

Both independent extractors merged these two mentions the same way.

## One item I refused to create (criterion 2)

**R-01 of the checkout meeting: "Add a time-out to the offer to link an order."**

An unidentified speaker asks: "Should it time out? If they never answer the link offer?" (`U-0011`). The
developer answers: "Let's park that. I don't know the answer and I'd rather not guess" (`U-0012`).

It is the easiest ticket in the meeting to write. It sounds like a requirement, and it is a sensible one.
But nobody said a time-out should be built. Nobody said how long, or what happens when it runs out. A ticket
would be scope taken from a question, and the developer's own words are "I'd rather not guess".

So no item was made. It is listed under "Not created" with both lines quoted and the reason, and it appears
again on W-02, the linking offer, as a part that is **not settled**. That item's heading says `DECIDED IN
PART`. A person planning the work sees the question. They do not see an answer that nobody gave.

Both extractors refused it too.

## What the readers found, and what was done about it

The first version of the items was finished before any reader replied. It said more than the meetings did, in
ways the program could not see.

**Which items there are held up.** Two readers, given only the rules and the transcripts, produced the same 6
items for the checkout meeting (one produced 5, folding one in as a detail) and the same 11 for the
notifications meeting. Nobody found work the files had missed.

**What the items said did not.**

- **An alternative nobody named.** The item about storing settings said they are stored "for each device or
  for the account". Nobody in the meeting said "account". The developer proposed per device, the product
  owner refused it, and that was all. The either/or was the assistant's own framing, and it presented a
  refused option as still live. The item now says what was proposed and refused, and names no alternative.
- **A remark nobody ruled on.** The unsubscribe item said the link "works for a member who is signed out".
  That was the tester's remark while arguing about something else. No decision holds it. It sat under a
  `decided` heading. It is now out of the item and listed as not created, with the reason.
- **Seven answers marked "said" that were not.** A size taken from a guess its speaker disowned in the same
  line. A size taken from "a day each", which was the size of what was left out. A size taken from "a bigger
  job". A condition, "waits on the legal team", that nobody stated. Two "done" answers that only repeated the
  item's own intent. All seven are now NOT SAID, with a note saying what was actually said.
- **Words in no cited line**, such as "a customer's" and "notification", and a title that leaned on a line the
  item did not cite.
- **Headings firmer than the items.** Plain `decided` stood on an item with two parts not settled, and on one
  resting on a reopened decision. There are now two more marks, `DECIDED IN PART` and `decided, REOPENED`, and
  the check fails a plain `decided` on either.

One correction went against two readers. Both extractors had put the signed-out clause into the unsubscribe
item, as the assistant had. A checker pointed out that no one ruled on it. The checker's reading was taken.

What was **not** changed, and a reader may fairly disagree:

- **Guest checkout and the linking offer are two items.** The meeting spoke of one story. The developer's
  guess prices it with and without the linking, which is why it was split. Every reader called this a judgment.
- **The phone number on the shipping label is its own item.** One extractor and one checker would fold it into
  guest checkout as a rule.
- **"Test on the two newest versions" is marked decided**, as the verified decisions file has it. Both
  extractors, with no decisions file, called it proposed. Its note says how weak the agreement was.

**The files as handed in were not read again by a reader** after the last corrections. The final state of the
unsubscribe item, the two new marks and the reworded notes are checked by the program and by nobody else.

## The criteria, one by one

| # | Criterion | Status | Where |
|---|---|---|---|
| 1 | Every item cites at least one utterance identifier that exists in the source record | recorded, tested | `logs/extraction-run.txt` parts 1 and 2. All 17 items cite between 1 and 9 lines, and every identifier anywhere in either file is in its record. An item with every citation taken away is reported |
| 2 | No item contains scope that no cited utterance supports | observed, with faults found and corrected. not assessed for a person | `logs/blind-read.txt`. The first files did contain such scope. Readers found it and it was removed. The program cannot check this: part 5 of the run log adds an invented clause to an item, and the check passes it. What the program does check is that each mark fits the decisions-file item it rests on |
| 3 | An item lists what the meeting did not say, such as an owner, a size or a condition | recorded, tested | Part 3. Every item answers all six, and every item has at least one NOT SAID. An owner written in with no line behind it is reported as a gap filled in |
| 4 | Two mentions of the same work produce one item with both citations | recorded, tested, observed | Part 4. 5 items are merged, and each cites every mention. A second item made from another's lines is reported. Both extractors made the same merges for the required file |
| 5 | Items are stored apart from the source record, which is not edited | recorded, tested | Part 6. Each record's SHA-256 is the one its provenance file recorded. git reports no change to any earlier file. The only new files beside the records are the two work-items files |
| 6 | Nothing is written to an external tracker | recorded, tested | Part 7. After a build and a check of both meetings, Python has loaded no module for connecting or for running another program. The files hold no address |
| 7 | A reviewer can trace each item to a line in the transcript | recorded, tested, observed by AI readers | Part 2: every quotation is the record's own words for the line cited, with its speaker. Both checkers traced every citation. No person was asked |

## Artifacts

| Required item | File |
|---|---|
| The candidate items | `participant/context/transcripts/sample-meeting.work-items.md` |
| The extraction rules | `participant/context/extraction-rules.md` |
| The extraction run | `logs/extraction-run.txt`, 60 checks. The run and the check for the required file are in part 1 |
| This narrative | `PROOF.md` |

Also here: `participant/context/transcripts/notifications-meeting.work-items.md`; `logs/blind-read.txt`;
`logs/tests.txt` (75 tests); `logs/planted-bugs.txt` (34 planted bugs); `review/`, the rules as the extractors
were given them; and `scripts/`. The skill is `participant/skills/ba-extract-work-items/`: `SKILL.md`,
`extract.py`, `items.py`, `tests/test_extract.py`.

Both work-items files and the rules file are written by the skill. A test and a log check compare each with
what the code writes, so none was adjusted by hand.

## Stretch goals

- **Rank items by how much of them the meeting specified:** done. Each file opens with a table, most said
  first. In the required file the most any item has is 2 of 6. After the readers' corrections the numbers went
  down, which is the honest direction.
- **Flag items whose citations all come from one speaker:** done. Three items are flagged. One is the
  proposal to drop text messages: every line behind it is its proposer's.

## Reproduce

    python3 participant/skills/ba-extract-work-items/extract.py check sample-meeting
    python3 participant/skills/ba-extract-work-items/extract.py check notifications-meeting
    python3 -m unittest discover -s participant/skills/ba-extract-work-items/tests -v
    python3 participant/evidence/ba-extract-work-items/ba-attempt-006/scripts/record_evidence.py
    python3 participant/evidence/ba-extract-work-items/ba-attempt-006/scripts/planted_bugs.py

None of these contacts anything or changes a record. The fifth changes `extract.py` while it runs and restores
it. The independent reads cannot be run again from a script: `scripts/blind_read.py` only writes out findings
copied by hand from the readers' replies.

## What was tested

| What | Result |
|---|---|
| The two handed-in work-items files | No problem reported. Exit code 0 for each |
| Recorded checks | 60, all pass. They include 21 ways of spoiling a file or a record, each reported |
| Automated tests | 75, all pass (`logs/tests.txt`) |
| Planted bugs | 34 put into `extract.py` one at a time. Every one made at least one test fail (`logs/planted-bugs.txt`) |
| Independent reads | Two extractors and two checkers, all AI assistants. Told above |

Faults found while building, apart from the readers:

- The first build of the notifications file failed the check on its own: one line was a mention in two items
  with no note saying so. That is the guard against duplicates doing its job on the assistant's own items.
- The first draft of the rules quoted two lines of the meetings as examples of what to leave out. Extractors
  given those rules would have been handed two answers. The rules were reworded before any reader saw them.
- A planted bug showed that no test covered an intent written as two sentences. A test was added.
- A script that applied several corrections at once stopped part-way on a mistyped match and changed nothing.
  The next build passed, because nothing had changed, and for a moment that looked like the corrections
  passing. It was noticed from the counts, which had not moved.

## What could not be done, and limitations

- **Criterion 2 is not something this program can check.** It is the criterion that matters most, and it
  rests on readers. The run log shows the gap in plain sight.
- **No person read anything.** All four readers were AI assistants, and the limit on what each could read was
  given in words and not enforced.
- **The handed-in files were not re-read** after the last round of corrections.
- **How settled an item is comes from the decisions file.** If that file is wrong about a decision, every item
  resting on it is wrong the same way. Two extractors, without it, marked two items differently.
- **One story or two items is a judgment** the rules do not settle, and every reader said so.
- **Proposed and open items are in the list.** That was a decision, and it carries a risk: somebody skims the
  titles and builds one. The mark is in capitals in the heading, the table and the note.
- **"Not said" means not said in this meeting.** An owner or a date may be well known and recorded elsewhere.
- **A one-person commitment is an item only if taken on in words** such as "I'll". "I'd want to look at it
  first" is not. That line was drawn by the assistant.
- **An error in the transcript, or in a speaker's label, is carried through.**
- Both meetings were written by an AI assistant, the second one by this one, knowing roughly what a later
  quest would ask of it.

## Reflection

*Which item came closest to containing your own idea rather than the meeting's?*

The one about how settings are stored, in the notifications meeting.

My first version said settings are stored "either for each device or for the account, and the meeting did not
settle which". It read well. It was balanced and it sounded like analysis. And nobody in the meeting said the
word "account". The developer proposed per device. The product owner said that will not work for her, because
what she turns off on her phone she expects to be off on her laptop. The developer said that is a bigger job
and he would need to think. That is all that was said.

I supplied the other option myself, because the two-sided question is the tidy way to write up a
disagreement, and then I reported the meeting as undecided between my two options. One of them had been
refused out loud. A reader caught it and called it the worst item in either file. They were right. The item
now says what was proposed and refused, and stops.

The second closest was the unsubscribe link. I wrote that it "works for a member who is signed out", under a
decided heading. That was the tester's remark while she was arguing about something else. I am less
embarrassed by that one, because two other readers made the same move, but it was the same fault: something
sensible, sitting next to a decision, quietly joining it.

What both have in common is that neither felt like inventing. I was not adding features. I was making the
item complete. The six "said or not said" answers were meant to stop that, and they did stop me writing in an
owner or a date. They did not stop me, because the idea went into the sentence, not into a blank. Seven of
my answers were also marked "said" on words that did not say it, a size from "a bigger job" among them.

So what I take from this is narrower than I expected. A visible blank does get answered, as the hint says.
But I only leave a blank where I notice I do not know. The scope I added was in the places where I thought I
did.

## Sensitive values

- No token or credential was used. The quest reads and writes only local files.
- Both meetings are invented, and so is everyone in them. No real customer or personal detail is in any item.
- The first record's redaction markers are as the ingest skill left them. The redacted address is not known to
  the work-items file, and its item says so.
