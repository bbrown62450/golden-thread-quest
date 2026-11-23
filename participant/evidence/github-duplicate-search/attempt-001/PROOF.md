# PROOF: Search for Likely Duplicates Before Issue Creation

Quest `github-duplicate-search`, attempt `github-attempt-007`.

## How this was made

The search, its tests, the made-up fixture, the recording scripts and this document were written by an AI
assistant (Claude) at the participant's direction. The participant chose the design in three decisions: search
a set of made-up records through an index built over them; use five weighted signals beyond the title and
require three of them; and treat a missed duplicate as worse than a false one, so the search reports
generously while the recommendation stays cautious. Nothing in this quest contacts GitHub, and no token was
used.

Words used below: **recorded** means the saved log shows it. **tested** means an automated test checks it.
**not assessed** means nobody checked it. Nothing here was observed on real GitHub or on real issues.

## Approach

One script, `participant/skills/github-duplicate-search/search.py`. It takes a draft of the issue about to be
filed, checks that the index is exactly what its records give, takes the list of issues from the index, follows
each row to its record for the body and comments, and compares.

Five signals beyond the title, each with points: error text 4, named things 3, body wording 3, labels 2,
repository 1. The title is worth 1 and never counts toward a candidate. An existing issue is a **candidate**
only when at least three of the five match (criterion 1).

## The confidence scale (criterion 2)

Three steps, set by the points a candidate scores, out of 14.

| Confidence | Points | What it takes |
|---|---|---|
| **high** | 11 to 14 | the three strong signals and at least one more. The same error, the same named things, similar wording, and the same repository or label |
| **medium** | 9 or 10 | two strong signals and a weaker one, or the three strong ones alone |
| **low** | 6 to 8 | three signals, most of them weak. 6 is the least three signals can add up to: repository, labels and one strong signal |

Why these numbers:

- **The bottom of the scale is the entry rule.** Below 6 points an issue cannot have three signals, so it is
  not a candidate and has no confidence at all. "Low" means "three things agree", not "something agrees".
- **High needs evidence that is hard to share by accident.** Two issues in one repository with one label
  already share 3 points. To reach 11 they must also share an error and named things or wording. The weak
  signals alone can never make "high", and neither can the title.
- **The title cannot move an issue across a step that matters.** It adds 1 point to an issue that is already a
  candidate. It cannot make one.
- **Not comparable is not a miss.** An issue with no error text is not marked down for having none. It simply
  cannot earn those 4 points, which is why the near duplicate in the fixture, which is slow and does not
  crash, tops out at low.

What the scale drives (criterion 6): `close-as-duplicate` is recommended only at **high**, and only against an
open issue in the same repository. Every other candidate is `link`. No candidate is `proceed`.

How it was checked: a test builds every combination that sits on a boundary and checks its step: 6 and 8 are
low, 9 and 10 medium, 11 and 14 high. Another checks that the three steps cover 6 to 14 with no gap. Two
planted bugs moved the boundaries and made every candidate high, and tests failed.

**What the scale is not.** The numbers are the assistant's own. They were chosen by reasoning, then tried on
a fixture the same assistant wrote. They have not been tried on real issues, and "high" has not been measured
against how often such a match is truly a duplicate. They are a starting point to be tuned.

## The criteria, one by one

| # | Criterion | Status | Where |
|---|---|---|---|
| 1 | The search uses at least three signals beyond the title | recorded, tested | `duplicate-run.txt` part 2: every candidate matched on at least 3. Tests `Signals` |
| 2 | Each match lists the signals and a confidence | recorded, tested | Part 2 and part 6, and `report.md`: all six signals with what was found, the points and the confidence. Tests `EachMatchExplained` |
| 3 | A same-title unrelated issue is not reported as a duplicate | recorded, tested | Part 3: the titles are the same character for character, and the issue is NOT A CANDIDATE. Tests `SameTitleUnrelated` |
| 4 | A true duplicate with a different title is found | recorded, tested | Part 2: first candidate, high confidence, and the two titles share no word. Tests `DifferentTitleDuplicate` |
| 5 | A proposal with no match reports none | recorded, tested | Part 4: "RESULT: NONE". Tests `NoMatch` |
| 6 | The recommendation is link, close-as-duplicate or proceed, and a person decides | recorded, tested | Parts 2 to 4 show all three. Tests `Recommendation` |
| 7 | The search does not change the index | recorded, tested | Part 5: the recording script's own SHA-256 and last-written time of the index and all 9 records, before and after. Tests `IndexUnchanged` |

### Criteria 3 and 4 pull against each other

Loosen the search and the same-title issue starts to match. Tighten it and the real duplicate slips through.
The rule that holds both is that the title is outside the count of three. The proposed "Login page is blank"
matches the existing "Login page is blank" on the title and on nothing else: 0 of 3. The proposed "Out of
memory when saving the March orders" matches "Export crashes on files over 2 GB" on all five signals and not
on the title.

Two tests push on the line between them. The same title with two more signals is still not a candidate. The
same title with three more is, and its title is then shown as a match.

### Criterion 5: "none" must be possible

A search that always returns its best match never says none. Here an issue is a candidate only at three
signals, so most searches of a small index find none. The issues that matched on one or two signals are shown
as "NOT A CANDIDATE", with the count, so that it can be seen they were looked at and rejected. A planted bug
that reported one-signal matches as low-confidence duplicates made fifteen tests fail.

## Artifacts

| Required item | File |
|---|---|
| The fixture | `participant/context/github/duplicates/fixture.md`, an index of the 9 records in `duplicates/records/` |
| The report | `participant/context/github/duplicates/report.md` |
| The run log | `logs/duplicate-run.txt`, 33 checks |
| This narrative | `PROOF.md` |

Also here: `logs/tests.txt` (55 tests), `logs/planted-bugs.txt` (25 planted bugs),
`scripts/record_evidence.py` and `scripts/planted_bugs.py`. The three proposed issues are in
`participant/context/github/duplicates/proposals/`. The skill is `participant/skills/github-duplicate-search/`:
`SKILL.md`, `search.py`, `make_fixture.py`, `tests/test_search.py`.

The fixture is a real index: the records were written by the `github-read-issue` skill's code and the index was
built by the `github-build-index` generator, neither of them changed. That skill's own check says the fixture
is up to date. In the fixture:

- **the true duplicate with a different title** is tracker issue 101, "Export crashes on files over 2 GB";
- **the near duplicate** is tracker issue 102, "Export is slow on large files";
- **the unrelated issue with the same title** is tracker issue 103, "Login page is blank".

Every repository, person, label and issue is invented.

## Stretch goals

- **Weight signals and show the effect:** done. The points are weights and the report shows each signal's
  points. `--equal-weights` counts every signal as 1. Part 7 of the log shows the effect: a match on the three
  strongest signals alone is medium with the weights and low without them. The weights change the confidence,
  not which issues are candidates.
- **Check the repository's issue templates for hints:** not done.

## Reproduce

    python3 -m unittest discover -s participant/skills/github-duplicate-search/tests -v
    python3 participant/evidence/github-duplicate-search/github-attempt-007/scripts/record_evidence.py
    python3 participant/evidence/github-duplicate-search/github-attempt-007/scripts/planted_bugs.py

None of these contacts anything. The second writes `report.md` again, with the same bytes. The third changes
`search.py` while it runs and restores it. To write the fixture again:

    python3 participant/skills/github-duplicate-search/make_fixture.py

## What was tested

| What | Result |
|---|---|
| Automated tests | 55, all pass (`logs/tests.txt`) |
| Planted bugs | 25 put into `search.py` one at a time. Every one made at least one test fail (`logs/planted-bugs.txt`) |
| Recorded checks | 33, all pass |

Faults found while building:

- **In the search, one, noticed by reading its first output.** The step that takes endings off words turned
  "anything" into "anyth" and "writes" into "writ". Harmless to the match, wrong to read. Corrected, with a
  test.
- **In the assistant's tests, three,** on first run: one searched for a word that is also inside "NOT A
  CANDIDATE", and two expected the wrong text.
- **A test that could not fail, found by a planted bug.** The bug wrote "what was found" into the report's
  table without making it safe, and no test noticed, because the test's odd file names were never among the
  things two issues shared. The test now makes them shared. The bug is caught.

## What could not be done, and limitations

- **The fixture and the thresholds have one author.** The made-up issues were written by the same assistant
  that chose the signals and the numbers. The fixture shows the search does what it was designed to do. It
  does not show that the design is right for real issues.
- **Real issues: not assessed.** No real index was searched.
- **It does not understand meaning.** "Out of memory" and "crashes" are different words to it. In the fixture
  the duplicate is found because both quote the same error and name the same files. A duplicate described in
  wholly different words, with no error text and nothing named, would be missed. By the participant's
  decision a miss is the worse mistake here, so this is the limit that matters most.
- **Error text is recognised narrowly:** an error name ending in Error or Exception, or a code shaped like
  `E-EXPORT-413`. Any other error message counts only as wording.
- **The word handling is for English,** and is crude: common words dropped, the commonest endings taken off.
- **A proposal is compared with existing issues only.** Two existing issues that duplicate each other are not
  found.
- **Labels on a draft are the filer's guess.** A proposal with no labels or the wrong ones loses that signal,
  and nothing warns.
- **It searches only what the local records hold.** An issue filed on GitHub since the last sync is not seen.
  The search does stop if the index does not match its records, but it cannot know the records are behind.
- The search, the recording script's own checks and the tests were written by the same assistant. They were
  written apart, and can still share a blind spot.

## Reflection

*Which is worse in your project, a missed duplicate or a false one?*

A missed duplicate. I decided that before the search was built, and it shaped the search more than any other
choice. If two people file the same crash and nobody notices, both get picked up and it is fixed twice, and I
only find out afterwards. If the search wrongly says "this looks like a duplicate", it costs me one look at
the other issue.

That only holds because the search does not act. If it closed issues by itself, a false duplicate would be
the worse mistake by far: a real problem would be waved away and might never be filed again. So the answer
has two halves. The search is generous about what it shows me: every issue with three signals, even at low
confidence, and the ones it rejected too. The recommendation is careful about what it tells me to do: close
only at high confidence, against an open issue in the same repository, and link for everything else.

What I did not expect was how much the title would have fooled me. I would have typed "Login page is blank",
seen an issue with exactly that title, and stopped. The search looked at that issue and found nothing in
common but the words in the title. And the real duplicate in the fixture shares no word of its title with the
proposal at all. Titles are what I read first and they are the weakest evidence.

The limit I would watch is the one that cuts against my own answer. I said a miss is worse, and the search
can still miss: it matches words, not meaning. A duplicate that quotes no error and names no file looks like
a stranger to it. So I would treat "none" as "none that this search could see", not as proof.

## Sensitive values

- No credential was used or needed. Nothing was contacted.
- Every record, proposed issue, title, label and login in the fixture, the report and the log is made up.
- The report and the log quote titles and words found in issues. On real issues those would be other people's
  text and could be private, so a report made from real records should be treated like the records.
