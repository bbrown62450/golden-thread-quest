# PROOF: Detect Work Added, Removed, or Materially Changed After Sprint Start

Quest `scrum-scope-change`, attempt `scrum-attempt-003`.

## How this was made

The snapshots, the program, its tests, the recording scripts and this document were written by an AI assistant
(Claude) at the participant's direction. The participant made one decision:

- **Any change of words in a scope entry or an acceptance criterion counts as material.** The report shows both
  versions and says that a person should read them. The other choice was to count a change only when an entry was
  added or taken out, and the participant turned it down because a changed number inside a criterion would then pass
  as noise.

**Everything in the snapshots is made up.** The project is a harbour booking app that does not exist. The 13 items,
the dates and the four people are invented. No real sprint was used.

**Nothing was posted anywhere.** The program reads one local file and writes one. No tracker, chat channel or email
was contacted, by the program or by the assistant.

Words used below: **recorded** means the saved log shows it. **tested** means an automated test checks it.
**observed** means an independent reader's reply shows it. **not assessed** means nobody checked it.

## The short version

- The report compares a start snapshot with a later one, by identifier, and puts every item in one list: added,
  removed, materially changed, noise, unchanged, or cannot be told.
- **For these snapshots:** 2 added, 2 removed, 4 materially changed, 4 noise, 1 unchanged.
- **Net change: 0 points. Points that moved: 22.** The sprint starts at 30 and is at 30 a week later, with 9 points
  added, 7 removed and 6 re-estimated up or down. That is the quest's scenario, and the report puts the second number
  beside the first.
- **Two readers compared the snapshots by hand**, one on each version, and agreed with the report on every item,
  field, quotation and number.
- **The program was wrong twice in ways its own tests did not see.** Readers of the code found inputs on which it
  would have asserted things the snapshots did not support. None showed on these snapshots. It was corrected both
  times.
- **Nobody has read the handed-in version.** What changed after the last read is listed below.

## Approach

**Match by identifier and by nothing else.** PIER-302 was given a new title. Matched on title it would be one item
removed and one added. It is one item, with a difference that is noise.

**Three fields are the commitment: the estimate, the scope list and the acceptance criteria.** A difference in one of
them is material. A difference in the title, the description or the assignee is noise.

**When unsure, report.** Very little is set aside as formatting. So a few changes that are only formatting are
reported as material, and a real change is not passed over for the sake of a quieter report.

**Show both versions of everything that differs,** noise included, so that a person can overrule the program.

**Say the number the net change hides.** A net change of 0 is not "no change", and the report gives the points that
moved in the line under it.

**Nothing is filled in.** An estimate that cannot be used is a gap. The item is then in no figure on either side, so
the parts always add up to the later total, and the section is marked NOT COMPLETE.

The rules are in `participant/skills/scrum-scope-change/SKILL.md`.

## What I count as material

By criterion 4, a change is material when one of three fields differs, and the report names the fields:

| Field | Material when | Why |
|---|---|---|
| `estimate` | the two numbers are not equal | It is the size of the commitment |
| `scope` | the two lists do not hold the same entries | It is what is to be built |
| `acceptance` | the same | It is what done means |

**What is set aside before two entries are compared, and nothing else:** the bullet or running number at the front,
capitals, spacing, whether a quote mark is curly, which dash is used, one full stop, comma or semicolon at the very
end, and the order of the entries. PIER-308 differs in exactly those and is noise.

**Everything else in an entry is kept.** A comma, a hyphen or a digit inside an entry makes it a different entry. The
first version set more aside, and a reader showed it made "1,5 seconds" and "15 seconds" the same. So less is set
aside now, and "sign-off" against "sign off" is reported as material. That is a false alarm, and the price of not
missing the first.

By criterion 5, noise is a difference in the title, the description or the assignee, or only in the formatting above.
It is listed with both versions and is in no figure.

## A change I was unsure about

**PIER-309.** One acceptance criterion read "An error message is shown when the file is too large". A week later it
reads "When the file is too large an error message is shown". The same words, in another order. The same test passes.

The report counts it as **material**, by the participant's decision and criterion 4: the acceptance criteria differ.
A reader said it would call it noise, by criterion 5: wording alone.

Both are fair. **A program can see that the words of a criterion changed. It cannot see whether the meaning did.**
PIER-307 looks the same to it: "within 2 seconds" became "within 10 seconds", which nobody would call a rewording.
The only rule that never passes over PIER-307 is one that also reports PIER-309. So the report says of both: "this
may be a rewording or a change of meaning. This report cannot tell which. A person should read both."

The cost is real. One of the four material changes here is a false alarm, and the same sentence sits on it and on a
true one. Neither moves the net change, since neither changed an estimate.

**The other side of the same line is PIER-311**, and both readers of the report named it first. Its description gained
a sentence: "Free berths are shown in green and the map can be zoomed." That is new work. Its scope list and its
criteria are as they were, so by the rule it is **noise**. The program does not read a description for scope, because
it could not tell that sentence from a tidier wording of the old one. The report shows both versions and says, above
the list, that noise "is not a statement that no work was added".

## The criteria, one by one

| # | Criterion | Status | Where |
|---|---|---|---|
| 1 | Items are matched by stable identifier, never by title | **recorded, tested, observed** | PIER-302 is noise with both titles. `logs/scope-run.txt` part 3 shows that matched on title there would be 3 "added". A test checks every place the program uses a title |
| 2 | An item present only in the later snapshot is reported as added | **recorded, tested, observed** | Section 2: PIER-312 and PIER-313. Part 3 finds them with its own code |
| 3 | An item present only in the start snapshot is reported as removed | **recorded, tested, observed** | Section 3: PIER-303 and PIER-310 |
| 4 | A change to estimate, scope or acceptance criteria is reported as material, with the fields that differ | **recorded, tested, observed** | Section 4: four items, each with its fields and both versions. Part 3 works the fields out again by a rule of its own |
| 5 | A change to formatting, wording or assignee alone is reported as noise and not counted | **recorded, tested, observed, with one reservation** | Section 5: four items, in no figure. The reservation: "wording" inside a criterion is counted as material, by decision. See above |
| 6 | Identical snapshots report no change | **recorded, tested** | Part 4: the start snapshot against itself, and a file whose two snapshots are separate copies. No reader could see these runs |
| 7 | The report states the net effect on the committed total | **recorded, tested, observed** | Section 1: both totals, the net change, its parts, the sum, and the points that moved. Part 3 adds them up again |

"Observed" is of the version each reader had. See "What independent readers found".

## Where the important artifacts are

Required by the quest:

| File | What it is |
|---|---|
| `participant/context/scrum/scope/snapshots.md` | Both made-up snapshots, in one file |
| `participant/context/scrum/scope/scope-change.md` | The report |
| `participant/evidence/scrum-scope-change/attempt-001/logs/scope-run.txt` | The comparison's output, with the noise left out, and the run on identical snapshots. A copy: see below |
| `participant/evidence/scrum-scope-change/attempt-001/PROOF.md` | A copy of this file |

The quest text names `attempt-001`. The app's Start button made `scrum-attempt-003`, which is where the work is.
`attempt-001/` holds copies, so the path the quest names exists.

Nothing in the run output needed redacting. The names in it are of invented people, and it holds no credential and no
path on anyone's computer.

The rest:

| File | What it is |
|---|---|
| `participant/skills/scrum-scope-change/scope.py` | The comparison and its check |
| `participant/skills/scrum-scope-change/SKILL.md` | The rules, and what the check does and does not look at |
| `participant/skills/scrum-scope-change/make_snapshots.py` | Writes the made-up snapshots |
| `participant/skills/scrum-scope-change/tests/test_scope.py` | 128 tests |
| `scrum-attempt-003/logs/scope-run.txt` | 68 recorded checks |
| `scrum-attempt-003/logs/tests.txt` | The test run |
| `scrum-attempt-003/logs/planted-bugs.txt` | 76 bugs put into the program one at a time. Each was caught by a test |
| `scrum-attempt-003/logs/independent-read.txt` | What three readers found, and what was changed |
| `scrum-attempt-003/scripts/` | The two scripts that wrote those logs |

## Stretch goals

- **The effect of each change on remaining capacity.** Done, in section 8, as "capacity not yet committed": the file's
  capacity of 32 less the committed total, 2 at start and 2 later, with the effect of each of the six changes of
  points. It takes no account of work done, and says so.
- **Changes made by someone other than the product owner.** Done, in section 9, with care. It sets each item's
  `changed_by` beside the file's `product_owner`, letter for letter: three are the same text and three are other
  text. `changed_by` is whoever last touched the item, which may not be who made the change. Who removed an item is in
  neither snapshot. The section says it is not a finding about anyone. A reader still thought names listed there
  could be read as a judgement.

## How to reproduce

From the repository's top folder. Python 3.9 or later, and nothing to install.

    python3 participant/skills/scrum-scope-change/make_snapshots.py
    python3 participant/skills/scrum-scope-change/scope.py compare --snapshots participant/context/scrum/scope/snapshots.md --out participant/context/scrum/scope/scope-change.md
    python3 participant/skills/scrum-scope-change/scope.py check --snapshots participant/context/scrum/scope/snapshots.md --report participant/context/scrum/scope/scope-change.md
    python3 -m unittest discover -s participant/skills/scrum-scope-change/tests
    python3 participant/evidence/scrum-scope-change/scrum-attempt-003/scripts/record_evidence.py
    python3 participant/evidence/scrum-scope-change/scrum-attempt-003/scripts/planted_bugs.py

The first two rewrite files that are already there, with the same bytes. The last changes `scope.py` while it runs
and puts it back. It takes a few minutes.

## What was tested or validated

- **128 tests, all passing.** `logs/tests.txt`.
- **68 recorded checks, all passing.** `logs/scope-run.txt`. Part 3 works the classes, the fields and the sums out
  again from the snapshots with the script's own code, which sets formatting aside by a rule written differently from
  the program's. That code reads only this file's shape.
- **76 planted bugs, all caught.** `logs/planted-bugs.txt`.
- **The same file gives the same bytes.** Two runs 2 seconds apart, and a third from a copy under another name in
  another folder.
- **The check can fail.** Part 6 spoils the report 20 ways, and the snapshots once, and each is reported. A pass on the
  program's own output shows little: the check reads the snapshots with the program's code.
- **Snapshots wrong in their form.** Part 7 tries 14: a blank estimate, an item given twice, a snapshot's name
  missing, list entries with no indent, a heading in the wrong place, and others.
- **A fault the record found before any reader.** With the later snapshot missing, the first program reported every
  item as removed. The recording script caught it. A test had checked the added list and not the removed one.

## What independent readers found

Three fresh AI assistants read the work, in two rounds. **No person read it.** They were told to read only what they
were given and to run nothing. Those limits were not enforced. The full account is in `logs/independent-read.txt`.

- **The report against the snapshots.** One reader on each version compared them by hand. Both agreed with every
  class, field, quotation and number.
- **Round 1, the code.** A snapshot name typed wrongly gave a bold net change of -30. An estimate unusable on one side
  put points in the net that no part explained. List entries with no indent were dropped and the item called
  unchanged. Sums of decimals printed a net change of a tiny fraction. Too much was set aside as formatting. The
  program was rewritten.
- **Round 1, the report.** PIER-311 as noise, under a heading that said nothing of the commitment differed. "Material
  means the commitment changed", where it may not have. A last section that read as naming people. All reworded.
- **Round 2.** The formatting rule still made a few different meanings equal. A list that was emptied was "cannot be
  told". Identical snapshots with the same gap in both did not report "No change", so criterion 6 failed on that
  input. The check passed some wrong reports. All corrected, each with a test.

**What changed after the last read, and was not read again.** In the report: wording in five places, and the two
versions now shown for PIER-308. No class, field or number changed. In the program: every correction from round 2.
Those are covered by tests and planted bugs, and by no reader.

## Remaining limitations

- **A reworded criterion is reported as material.** One of the four here is a false alarm.
- **New work written only in a description is noise.** PIER-311 is the example. The report shows it and does not
  count it.
- **Capitals are set aside,** so "5 mW" and "5 MW" are the same entry.
- **Reordering is noise.** If the criteria are steps, a change of order is missed.
- **Points are counted, not work.** Being in a snapshot is all that "committed" means. Nothing says what is done.
- **Two snapshots only.** Something added and taken out again between them is not seen.
- **An item renumbered** is one removed and one added.
- **`changed_by` is one name for an item.** It is whoever touched it last.
- **The check is not independent of the program**, and has blind spots that SKILL.md lists.
- **One file, made up by the same assistant that wrote the program.** A real tracker's export would have cases nobody
  here thought of.

## Reflection

*Where does a clarification end and a scope change begin on your team?*

On the evidence of this quest, a clarification is a change that leaves what gets built and which tests pass exactly
the same. The moment either moves, it's a scope change, whatever field it was typed into. PIER-309 is a
clarification: the words moved around and the same test still passes. PIER-307 is a scope change: 2 seconds became
10. And PIER-311 is the one that worries me, because the new work went into the description, where my own rule calls
it noise.

So the honest answer is that the line isn't in the tool. The tool can tell me that words changed. It can't tell me
whether the meaning did. I chose to have it report every reworded criterion and let a person decide, and I'd want the
team to agree that new work goes in the scope list or the acceptance criteria, never only in the description, so the
tool is looking in the right place.

## Sensitive values

None. The snapshots are made up: no real person, project, item, sprint or tracker is named. There is no token,
password or key in any file here. No path on anyone's computer is in the logs: the scratch folder is written as
SCRATCH.
