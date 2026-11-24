# PROOF: Split Oversized Work into Independently Valuable Increments

Quest `ba-slice-story`, attempt `ba-attempt-008`.

## How this was made

The original story, the slices, the skill, its tests, the recording scripts and this document were written by an
AI assistant (Claude) at the participant's direction. The participant made two decisions: the story to slice is
a new made-up one, the scenario's "Build the reporting module"; and a slice may hold only whole criteria of the
original, word for word, with nothing added.

**The story is made up.** There is no meeting, no shop, no manager and no team behind it. Everything said about
value, risk and what a manager would ask for is the writer's invention. **Nothing was created in any tracker**,
and nothing outside the participant's computer was contacted.

Words used below: **recorded** means the saved log of the check shows it. **tested** means an automated test
checks it. **observed** means an independent reader's reply shows it. **not assessed** means nobody checked it.

## The short version

- The original story has 20 acceptance criteria, each with one result. It is cut into 7 slices.
- Every criterion is in exactly one slice, word for word. A program counts that, and a reader counted it by
  hand and got the same.
- **The first version was wrong, and the program passed it.** It had 9 slices. One was a quality attribute
  dressed as a slice, and the first slice released a sum known to be wrong. A reader found both.
- The check counts coverage and order. It cannot tell whether a slice is a slice. A slicing by the story's own
  area headings passes every count it makes, and its first release is a page with nothing on it.

## Approach

**The original** was written first: 20 criteria in seven areas, each one result, each with a "Needs" line
naming the criteria that must already hold before it can be seen to hold.

**The rule for a slice**, from the participant's second decision: its criteria are original criteria, copied,
and nothing else. So coverage is a matter of counting, and "nothing added" is a matter of comparing text.
Where the cutting showed that the original does not say something, it is listed as a gap and not filled in.
There are 14 such gaps at the end of `slices.md`.

**The program** writes the documents from tables and then checks the finished files, not the tables. It works
the order out twice: from each slice's own "Depends on" line, and from the "Needs" lines of the original.

**Readers** did what the program cannot. Four, in three rounds. They changed the slicing twice.

## How I chose the first slice (criterion 5)

This is what the quest asks the proof to explain.

The first slice is **"See the last 7 days' orders and what they come to"**: OC-01, 02, 03, 04, 07, 08, 09 and 10.

I asked what the smallest thing is that answers the manager's actual question, "what did we sell, and what
did it come to?". That gave the page, the list, the default period, the count and the sum: six criteria.

Two more went in, and neither is "value" in the usual sense.

- **OC-02, refusing staff who are not managers.** A page of sales figures cannot be released to everyone first
  and locked afterwards. It looks like a security layer to do later. It has to be in the first release.
- **OC-09 and OC-10, the refunds.** My first version left these for a second slice, with a note that a manager
  "must be told" the sum counts refunded orders. A reader pointed out that the telling had no channel: no
  criterion puts a warning on the page, and I had ruled that nothing may be added. So the first release would
  have shown a wrong sum with nothing to say so. I had called this "the closest call of all" and then called it
  the wrong way.

**A thinner first slice exists and I did not take it.** A second reader proposed the list alone with refunds
marked, OC-01 to 04 and 09, with the count and the sum to follow. It would be honest to release: it states
nothing false. I kept the eight because a list with no sum does not answer "what did it come to", and that
question is what the story is for. A product owner could fairly choose the other.

It relies on three things the original takes as given: sign-in with roles, stored orders, and a staff menu.
It relies on no other slice. What it lacks, because the original does not ask for it: the page does not say
which days it shows, and an order refunded in part is not handled.

## Slicings I rejected (criterion 2)

**1. By technical layer:** data, server, screens, background job. This is the scenario's own mistake. Counted
by the program: no criterion belongs to one layer, 0 of 20, and nothing a manager could use exists until the
third layer of four is finished. A reader called it a straw man, and it is. It loses by construction.

**2. By the story's own seven areas:** the page, the list, the figures, the export, saved reports, the weekly
email, speed. This is the one worth rejecting, because it looks like slicing by value. Each area sounds like
a feature. **It passes every count my check makes:** each criterion is in exactly one area, and no area needs
a later one. It fails on judgement. Its first release is "the page": a heading and a refusal, with no order on
it. "The figures" bundles what the first release needs with a chart it does not. "Speed" is released last and
gives a manager nothing.

I would not have found the second if a reader had not named it. The same reader said my own slices still carry
its residue, and they do: three of the seven areas survive as slices, because those three were already
something a manager is given.

**3. My own first version, with nine slices.** Rejected after reading, as told above. It is kept in `review/`.

## The criteria, one by one

| # | Criterion | Status | Where |
|---|---|---|---|
| 1 | Each slice states the value it delivers on its own | recorded and tested that each states one. observed, with a reservation | `logs/coverage-check.txt` part 6. The last reader: holds, with Slice 6 "thin" by its own admission. Readers found value lines that claimed more than the criteria give in every round, and those were corrected |
| 2 | Slices are cut by user-visible value, not by technical layer | observed. recorded only as a list of words | The last reader: "All seven are things a manager is given." The first version failed this: one slice was a quality attribute. Part 6 checks titles and values against 24 words for a layer, which is a rough test and says so |
| 3 | Every original criterion is covered by exactly one slice | recorded, tested, observed | Part 2: a grid of 20 criteria against 7 slices, 20 covered once, none twice, none missed. A reader counted by hand and two critics counted again: the same |
| 4 | No slice depends on a slice that comes after it | recorded, tested, observed, with a limit | Part 4, by the "Depends on" lines and again by the original's "Needs" lines. **The limit:** the "Needs" lines are my judgement. Readers argued with several. None of their corrections would make a slice depend on a later one, by their own account |
| 5 | The first slice can be released alone | recorded, observed. not assessed in fact | Part 5: it depends on no slice, and every criterion its criteria need is inside it. The last reader: holds. That it could really be released needs a team and a product, and there is neither |
| 6 | Nothing is added that the original story did not contain | recorded and tested for the criteria. observed, with a reservation, for the rest | Part 3: 20 criteria written under the slices, 20 identical to the original character for character. **The reservation:** the lines that are not criteria invent detail, such as "two date boxes", and guess at what a manager asks for most. They are marked as commentary |
| 7 | A reviewer can recompute the coverage from the files | recorded, observed | Part 2 says how, in two sentences. A reader given the two files with the coverage table and counts removed did it by hand and matched the program |

## Artifacts

Start created the folder `ba-attempt-008`, and the work is there. The quest text names `attempt-001`, so
copies of the files it names are in `participant/evidence/ba-slice-story/attempt-001/`, with a note saying
where the originals are.

| Required item | File |
|---|---|
| The original story | `participant/context/slicing/original-story.md` |
| The slices | `participant/context/slicing/slices.md` |
| The coverage check | `logs/coverage-check.txt`, 39 checks |
| This narrative | `PROOF.md` |

Also here: `participant/context/slicing/rejected-slicing.md`; `logs/independent-read.txt`; `logs/tests.txt`
(59 tests); `logs/planted-bugs.txt` (35 planted bugs); `review/`, the first version as two readers read it;
and `scripts/`. The skill is `participant/skills/ba-slice-story/`: `SKILL.md`, `slice.py`,
`reporting_module.py`, `tests/test_slice.py`.

The three documents are written by the skill. A test and a log check compare each with what the code writes.

## Stretch goals

- **Order the slices by value and risk and justify the order:** done. Each slice has a line saying why it is
  where it is, by both. A reader changed the order once: the CSV file moved from seventh to third, because my
  reason for putting it late was about dependency and not about value.
- **Find a dependency that forces two slices to ship together:** done, three times, and each pair became one
  slice. Saving a report and opening one: saving alone cannot even be tested. The weekly email and its
  attachment. And the first slice with the refunds, which I first got wrong. `slices.md` also lists three
  pairs that share a slice by choice and could be cut apart.

## Reproduce

    python3 participant/skills/ba-slice-story/slice.py check
    python3 participant/skills/ba-slice-story/slice.py coverage
    python3 -m unittest discover -s participant/skills/ba-slice-story/tests -v
    python3 participant/evidence/ba-slice-story/ba-attempt-008/scripts/record_evidence.py
    python3 participant/evidence/ba-slice-story/ba-attempt-008/scripts/planted_bugs.py

None of these contacts anything. The last changes `slice.py` while it runs and restores it. The independent
reads cannot be run again from a script.

## What was tested

| What | Result |
|---|---|
| The handed-in files | No problem reported. Exit code 0 |
| Recorded checks | 39, all pass. They include 15 ways of spoiling the files, each reported |
| Automated tests | 59, all pass (`logs/tests.txt`) |
| Planted bugs | 35 put into `slice.py` one at a time. Every one made at least one test fail |
| The slicing by layer | counted: 0 of 20 criteria in one layer, nothing usable before the third layer |
| The slicing by area | counted: passes coverage and order. Rejected on judgement |
| Independent reads | one recount by hand and three critics, all AI assistants, in three rounds |

## What the readers found, and faults found while building

Full account in `logs/independent-read.txt`.

- **Round 1, nine slices.** The recount matched. The critic found the wrong first slice and the slice that was
  a quality attribute, and named the area slicing.
- **Round 2, seven slices.** A fresh critic found three commentary lines that promised more than their
  criteria. One was simply false: I had written that a manager could work out per-product figures from the CSV
  file, which has no product in it, and had used that as my reason for the file's place in the order. It also
  found a missing dependency: choosing a product presses a button that only the dates slice introduces.
- **Round 3.** A third critic: "The slicing is sound." Six criteria hold, three with a reservation. It found five
  more sentences false or unsupported.

**After round 3 those five sentences were reworded and not read again.** Nothing else changed: no criterion, no
coverage, no dependency. The counts are the same.

Faults I found myself:

- The check for needs that go round in a circle could not find one. It refused to follow a need back to where
  it started, which is the only way to see a circle. A test showed it.
- Two trials in the recording script spoiled a slice's written-out criteria and expected a coverage problem.
  Coverage is read from the "Covers" line, so the wrong problem was reported and the trials failed, rightly.
- A planted bug showed that no test covered a criterion counted as "covered once" when it was covered twice.
  A test was added.

## What could not be done, and limitations

- **The check cannot tell a slice from a non-slice.** The area slicing passes it. So did my first version.
- **The "Needs" lines are mine.** The order check rests on them. Readers argued with several.
- **OC-20, the 5 seconds, is the weak point of the order.** It is accepted in Slice 2, and Slices 4 and 5 make
  the same button do more. The original does not say it must still hold then. A reader called an honest
  "Needs" line for it one that would break the order. It is listed as a gap.
- **Commentary lines may still overstate.** Every round of reading found some. Five were changed after the last
  read and have not been read since.
- **The commentary invents detail**: boxes, buttons beyond those the criteria name, and how often a manager
  asks for what.
- **Whether each slice fits in one iteration is not assessed.** There is no team to estimate it. Slice 1 holds
  8 of the 20 criteria and may itself be too large.
- **The original was written by the person who sliced it.** Its criteria were already one result each, which
  made whole-criterion slicing possible. A real oversized story would need its criteria split first.
- **No person read any of it.** All four readers were AI assistants, with limits given in words.

## Reflection

*Which slice would stakeholders ask to drop, and what would that cost the others?*

Saved reports, Slice 6. I called it a convenience myself, in writing, so I can hardly be surprised.

On paper it costs nothing to the five slices before it. In fact it costs the last one everything. The weekly
email is defined on a saved report. Drop saving, and "have it sent every Monday" cannot be built as the story
words it. Somebody would have to write a new criterion, and that is a change of scope and not a cut.

What I notice is that the dependency points the wrong way for the value. The email is probably the thing a
busy manager wants most, and it sits last, behind a slice nobody would fight for. That is not something my
slicing did. It is in the original story, where the email was tied to saved reports before I touched it.
Slicing only made it visible. I think that is half of what slicing is for.

The other thing I take from this is about my own first attempt. I had a first slice I liked: small, clean, six
criteria. It showed a sum that was wrong whenever there had been a refund, and my answer was a note saying the
manager "must be told". A reader asked how. There was nowhere on the page to tell them, and I had already
ruled that nothing could be added. I had cut the slice thin enough to look good and then covered the hole
with a sentence.

My check passed that version. It counts, and the counts were right. It also passes a slicing whose first
release is a blank page. So I trust it for what it counts, which is whether anything was lost or added, and
for nothing else. Whether a slice is worth releasing took a reader, three times.

## Sensitive values

- No token or credential was used. The quest reads and writes only local files.
- The story is invented, and so is everyone in it. No real customer's data and no real story is in any file.
