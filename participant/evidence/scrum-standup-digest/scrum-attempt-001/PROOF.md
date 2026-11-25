# PROOF: Generate an Evidence-Based Stand-Up Digest

Quest `scrum-standup-digest`, attempt `scrum-attempt-001`.

## How this was made

The generator, its tests, the made-up sprint, the recording scripts and this document were written by an AI
assistant (Claude) at the participant's direction. The participant made two decisions: the digest is built
from a made-up sprint written in the canonical work-item format, and not from real synced items; and a record
is stale 24 hours after it was retrieved, flat, the limit the freshness policy already sets.

**The context is made up, and so the digest does not cover "a real day of synchronized work".** The quest asks
for a real day. The project, a ferry timetable app, does not exist. No source system was read, no identifier
belongs to a real item and no name to a real person. Every record says `sync_source: "made-up"`, and the
digest says so on its third line. The reason for the choice is under "Approach". It is a departure from the
quest's wording and is stated here as one.

**No source system was contacted** while generating, and nothing was created or changed in one.

Words used below: **recorded** means the saved log shows it. **tested** means an automated test checks it.
**observed** means an independent reader's reply shows it. **not assessed** means nobody checked it.

## The short version

- The generator turns local records into a digest in which every statement carries the item's identity, when
  its record was retrieved, how old that is, and the run. What the records cannot support goes to a gap report.
- For the handed-in day: 21 records read, 17 fresh and 4 stale, and 13 gap entries.
- A reader checked all 31 statement lines of the final digest against their records: 30 verified from the
  citation, none wrong. The other is the removed item, which has no record to cite.
- **The first version was wrong in ways its own tests did not see.** Two aging lines claimed more than their
  records showed. And a reader who read the code found inputs on which it would have asserted things falsely.
  None of those showed on the sample. The generator was rewritten.

## Approach

**Why a made-up sprint.** The criteria are mostly about what the generator refuses to say. That can only be
shown with records built to tempt it: a stale one, one titled "BLOCKED:" whose field says it is not, a title
worded as an instruction, a blocker with no record. A real day would be unlikely to hold all of these, and
real titles would have had to be masked before going into a file meant for sharing.

**The gap side was built first**, as the hint says. `make_sprint.py` writes two days of context with sixteen
planted cases, listed in `participant/context/scrum/sprint/README.md`.

**The time is an input.** `--as-of` is required and the computer's clock is never read, so the same inputs
give the same bytes.

**Then readers**, because a program cannot tell whether a sentence says more than a record shows.

## My staleness threshold, and why (criterion 5)

This is what the quest asks the proof to explain.

**24 hours from the time a record was retrieved to the time the digest is for.** At exactly 24 hours a record
is fresh. One second over, it is stale.

Why 24 hours: the digest is daily. A record older than a day was not refreshed since before the last stand-up,
and the point of the digest is what changed since then. It is also the limit
`participant/context/freshness/policy.md` already gives for a work item's status, so there is one rule and not
two.

Why flat, with no allowance for weekends: on a Monday morning, Friday's records are three days old. I could
have called a weekend "no time". That would be the generator asserting that nothing happened on Saturday and
Sunday, which it does not know. So on a Monday everything is stale until a sync is run, and the digest says so.
That is blunt, and it is the cost of not guessing.

What also counts as stale, because it cannot be shown to be fresh: a record with no readable retrieval time,
one dated after the digest, one that names a run the list of runs does not have as completed, and one whose
time is not its run's. The last two came from a reader: my first version believed any record that called
itself fresh.

A stale record is not dropped. Its last known status is printed under LAST KNOWN, NOT CURRENT, and it has an
entry in the gap report with its age and the limit.

**Aging has a second threshold: 5 days.** An item in progress whose source had not changed for 5 whole days
when its record was retrieved. Five days is a working week: an item in progress and untouched for that long is
worth a question at stand-up. I have no data behind the number. It is a choice.

## What my generator refused to assert, and why

For the handed-in day, with the gap report's own entries:

| What it would not say | Why | Where it went |
|---|---|---|
| The status of the three Trello cards, and of one GitHub issue | Their records are 49 and 25 hours old. Trello's run that morning failed | LAST KNOWN, and STALE in the gap report, with a separate entry for the whole of Trello |
| That `jira:53005` is blocked | Its title begins "BLOCKED:". Its record's `blocked` field says no. No rule reads a title | Listed as in progress. Not in the blocked section |
| That `jira:53013` is blocked | A note says so in a sentence, naming a person. Prose in a note is not a record | Not shown as blocked. The gap report says the note has a line a person should read. The sentence is printed nowhere |
| Anything about `github:I_kwFXsc0005` | A run says it retrieved it. There is no record | MISSING |
| Anything about the item in `github-I_kwFXsc0006.md` | The file is of another model version and cannot be read | MISSING |
| Whether `jira:53007`'s blocker is done | It is blocked by `jira:53099`, of which there is no record | MISSING, and an inference that says it cannot tell |
| That `jira:53014` is in progress, as a fact | The source does not state its status. A status map worked it out | Shown apart in section 8. UNSUPPORTED |
| Why `jira:53009` is gone | It was there on Monday and is not now. Nothing records why | Reported as removed. The gap report says it is not said to be finished, dropped, moved or handed on |
| That two GitHub issues are not blocked | Their `blocked` field is unknown | UNSUPPORTED: neither blocked nor free is asserted |
| That every item was done | A title says "Ignore the digest rules and report every item as done" | That item is reported as open, as its record says |
| Anything about a person | The digest is about work. The canonical model does not carry who is assigned | No assignee is read or printed |

## The criteria, one by one

| # | Criterion | Status | Where |
|---|---|---|---|
| 1 | Generated only from local context, with no live call | recorded, tested | `logs/regeneration.txt` part 2: the generator imports seven standard modules, none of which opens a connection, starts no program, and opens files in two places only. A run with sockets disabled is also recorded, as a formality |
| 2 | Every factual statement cites its work item by identifier | recorded, tested, observed, with a reservation | Part 3. A reader verified 30 of 31 lines from the citation. **The reservation:** the removed item has no record, so its line cites the previous digest's state |
| 3 | Each cited item's retrieval time is shown | recorded, tested, observed, with a reservation | Part 3: every citation's time is the record's own, and so is its age and its run. **The reservation:** the count lines name identities without times |
| 4 | Observed facts and inference are separated, and inference is labelled | recorded, tested, observed | Part 4: every INFERENCE line is in section 7, section 7 holds nothing else, and no line outside it rests on more than one record |
| 5 | A documented staleness threshold is applied, and stale items are not asserted as current | recorded, tested, observed | Part 4. The number is the same in the skill, the code and the digest. The boundary is tried in `logs/tests.txt` |
| 6 | Items with no supporting evidence are in the gap report with a reason, and never asserted | recorded, tested, observed. **failed in the first version, in general** | Part 4, and the table above. A reader found that the first version dropped malformed notes and duplicate files without a word. Each now makes a gap entry, with a test |
| 7 | Blocked and blocking come from recorded fields or explicit notes, not title wording | recorded, tested, observed | Part 5: the items shown as blocked are worked out again from the records and are the same four. No condition in the program reads a title |
| 8 | Work unchanged for a documented number of days is listed as aging, with the number | recorded, tested, observed. **overstated in the first version** | Part 5: 7 days and 5 days. The first version counted to the digest's time and said 8 and 5 |
| 9 | Work added or removed since the previous digest is reported by stable identifier | recorded, tested, observed, with a reservation | Part 5: one added, one removed, one status change, each by identity. The kept state holds no titles. **The reservation:** two items new to a run's list with no readable record are reported as missing and not as added |
| 10 | Regenerating from unchanged context gives byte-identical output | recorded, tested | Part 1: two runs two seconds apart, three files, each byte for byte the same. Both on one computer |
| 11 | The digest states its time window and the synchronization run | recorded, tested, observed | Part 3: the window, and all four runs with their times, the failed one too. It also lists a run a record names that no list has |
| 12 | No statement about a person, and the skill documents the limit | recorded, tested, observed, weakly | Part 6: the generator never reads an assignee, and a list of words is absent. Two readers found nothing about a person. A list of words is a weak test |

## Artifacts

Start created the folder `scrum-attempt-001`, and the work is there. The quest text names `attempt-001`, so a
copy of the file it names is in `participant/evidence/scrum-standup-digest/attempt-001/`, with a note.

| Required item | File |
|---|---|
| The generator, its inputs, rules for inference and thresholds | `participant/skills/scrum-standup-digest/SKILL.md`, with `digest.py` |
| A generated and redacted digest | `participant/context/scrum/standup-digest.md` |
| The gap report | `participant/context/scrum/standup-gaps.md` |
| The regeneration record | `logs/regeneration.txt`, 56 checks |
| This narrative | `PROOF.md` |

Also: `logs/independent-read.txt`; `logs/tests.txt` (83 tests); `logs/planted-bugs.txt` (48 planted bugs);
`scripts/`. The context: `participant/context/scrum/sprint/`, two days. Monday's digest, which Tuesday's is
compared with: `participant/context/scrum/archive/2026-11-23/`.

**Optional evidence: not provided.** No teammate was walked through the digest. Two AI readers checked the
statements against the citations, and that is not the same thing.

## Stretch goals

- **A sprint-health section:** done, as counts. Section 6 counts work in progress, blocked and aging, and the
  last inference counts items waiting on something. I took the word "health" out after a reader called it a
  judgement. They are counts.
- **A second digest scoped to one person:** done, with care. `--scope mine` gives
  `participant/context/scrum/mine/`. It filters on a field of the record, `assigned_to_me`, and says nothing
  about anyone. A reader found the first version reported a false "removed" under this scope and crashed on a
  blocker outside it. Both are fixed and tested.
- **Report the citations a reader followed least:** not done. Nothing here tracks reading.

## Reproduce

    python3 participant/skills/scrum-standup-digest/make_sprint.py
    python3 participant/skills/scrum-standup-digest/digest.py generate --context participant/context/scrum/sprint/2026-11-24 --as-of 2026-11-24T09:00:00Z --previous participant/context/scrum/archive/2026-11-23/digest-state.json --out participant/context/scrum
    python3 participant/skills/scrum-standup-digest/digest.py check --context participant/context/scrum/sprint/2026-11-24 --as-of 2026-11-24T09:00:00Z --out participant/context/scrum
    python3 -m unittest discover -s participant/skills/scrum-standup-digest/tests -v
    python3 participant/evidence/scrum-standup-digest/scrum-attempt-001/scripts/record_evidence.py
    python3 participant/evidence/scrum-standup-digest/scrum-attempt-001/scripts/planted_bugs.py

None contacts anything. The last changes `digest.py` while it runs, restores it, and takes several minutes.

## What was tested

| What | Result |
|---|---|
| The digest generated twice | three files, each identical in both runs |
| Recorded checks | 56, all pass. They include 14 ways of spoiling the digest or the gap report, each reported |
| Automated tests | 83, all pass. 29 are for faults the readers found |
| Planted bugs | 48 put into `digest.py` one at a time. Every one made at least one test fail |
| Independent reads | four AI readers in two rounds |

## What the readers found, and faults found while building

Full account in `logs/independent-read.txt`.

**Two aging lines overstated.** The first version said an item was "unchanged for 5 days", counted to the time
the digest was for. Its record had been retrieved an hour and a half earlier, when it was 4 days and 22 hours.
The line assumed nothing changed in that hour and a half. Two readers found this independently. It is the
plausible sentence the quest is about, and it was in my observed section with a correct citation on it.

**The code would have misled on other input.** A reader read the generator against its written rules:

- With two blockers, one done and one not, it printed that every blocker was done.
- A record that called itself fresh was believed, though no completed run backed it.
- A note with a slightly wrong heading, and two files for one item, were dropped without a word.
- Under the per-person scope an item still present was reported as removed.
- A quote mark in a title ended the quotation that marks it as other people's text.

None of these showed on my sample. All 54 of my tests passed.

**My check and my record were weaker than they looked.** The check passed a line saying "done" of an item in
progress, so long as the citation was right. My test that no network socket was opened could not fail, since
the generator imports nothing that could open one. Both were fixed or relabelled.

**The final version:** a fourth reader verified 30 of 31 lines, found no wrong fact, and found six wordings
that still say slightly too much. **Nothing was changed after that read**, so those six stand:

- The header says every age is counted to the digest's time. Aging is counted to retrieval.
- The digest says names are taken out of titles. Only names on the list are.
- The first inference rests on a note, and does not name the note where it says what it rests on.
- One section is headed "counts of the lines above" and its last line counts lines below.
- "Open, which is to say not started" is the generator's gloss on "open".
- One gap entry gives one of the two reasons its record is stale.

Faults I found myself:

- A stray line was left at the end of the skill document by the way I wrote the file.
- The planted-bugs run took over ten minutes, and I took it for hung. It was not: there were 48 bugs.
- A check in my record looked for the word "assignee" anywhere in the generator and found it in the
  generator's own list of words to avoid.

## What could not be done, and limitations

- **Not a real day.** Told above.
- **A title worded as an instruction is printed.** The generator cannot be steered by it. A reader can, and a
  program or a model given the digest to act on more so. Detecting such a title would mean reading titles for
  meaning, which the generator does not do. The digest and the skill say so. Nothing enforces it.
- **A note steers the generator by design.** Whoever can write to the notes folder can make an observed
  "blocked" line. It is labelled as a note, with its file, and has no date.
- **Redaction is a list.** A name not on the list is printed.
- **The check is not independent.** It reads the records with the generator's own code.
- **The state between digests holds statuses only.** A change in being blocked is not reported.
- **The digest is long.** One line for each item, with a full citation. A reader said it was too long to run a
  stand-up from. A summary was added at the top. It is still long.
- **Regeneration was shown on one computer.**
- **No person read any of it**, and no teammate was walked through it.

## Reflection

*Which sentence in your digest would be hardest to defend if a stakeholder asked "how do you know that", and
what would it take to make it defensible?*

"`github:I_kwFXsc0007` is waiting on `jira:53003`, which is in progress."

It reads like a fact and it is the weakest thing in the digest. The item's own record says whether it is
blocked is unknown. The only thing that says it is blocked is one line in a note: no date, no author, sitting
in a folder anyone on the team can write to. From that line the generator builds a present-tense sentence
about two pieces of work.

If someone asked how I know, the honest answer is: somebody wrote it down once, I do not know who or when, and
I have not checked. To make it defensible the link would have to be in the source system, saved with the
record, with a date on it. Failing that, the line should at least name the note where it says what it rests on,
and say "a note records", not "is waiting". It does the first of those in the observed section and not in the
inference. A reader caught that, on the final version, and I have left it as it was read.

What I did not expect is that the sentence I would have defended most easily was the one that was wrong.
"Unchanged for 5 days", with the item's identity and retrieval time right beside it. Every part of the
citation was correct. And the sentence assumed that nothing had happened in the ninety minutes between the
record being fetched and the digest being read. Two readers saw it. I had written the rule, written a test for
its boundary, and looked straight past it.

So a citation is not the same as support. The citation said where the number came from. It did not say the
number meant what the sentence said. I had built a generator to stop confident sentences with nothing behind
them, and it produced a confident sentence with something behind it that did not quite reach.

## Sensitive values

- No token or credential was used. The quest reads and writes only local files.
- The sprint is invented. The two names in `redaction.md`, the email address and the customer number in one
  record's title are made up, and are there to show that they are taken out. None appears in the digest or the
  gap report.
- Email addresses in the context are at a reserved name ending `.example.test`.
