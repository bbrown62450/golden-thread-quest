# Proof · playwright-tagging

Attempt: `playwright-attempt-009`

## How this was made

The participant chose the approach to duration tags: two tags, with limits taken from measurement and enforced. An AI
assistant (Claude) wrote the vocabulary, the tests, the check and this file, and ran the check on the participant's
computer against a made-up application running on that computer. Two further AI assistants read the work. No person
other than the participant has read it.

## The short version

- A vocabulary of 13 tags in five dimensions, kept in one file. The scheme document is written from that file.
- Ten tests of a made-up customer directory, each with exactly one tag from each dimension.
- A check that reads the tags as Playwright reads them, rejects any tag outside the vocabulary, names any test that is
  missing a dimension, and then **runs each test three times and compares what it did with what its tags say**: the
  requests it sent for read or write and for layer, and its slowest time for duration.
- 59 checks pass. 30 of them come from 29 trials in which something is spoiled on purpose and the check must report it.

## Approach

**A tag nobody could be wrong about.** Three of the five dimensions are decided by something that can be measured, and
the check measures it. Read or write is the methods of the requests a test sends. Layer is whether any request comes
from a browser. Duration is the slowest of three timed runs. The other two, feature and risk, are judgements. Their
rules were rewritten after a reader tagged the tests differently from the file, so that each goes by what the test does
and asserts and not by an opinion about importance.

**One place for the vocabulary.** `support/tags.ts` holds every tag, its meaning and, for duration, its limit. The check
reads it, and writes `tag-scheme.md` from it, then compares the file on disk with what it would write.

## How the duration limits were chosen

By measurement on this computer, then rounded up to a number a person can remember.

| Tag | Limit | What was measured (slowest of three runs, each test alone) | Room |
|---|---|---|---|
| `@fast` | 2 seconds | The slowest of the nine fast tests took 0.17 s in the recorded run, and 0.21 s in an earlier one | About ten times |
| `@slow` | 10 seconds | The sixty-customer test took 3.85 s | About two and a half times |

- 2 seconds was chosen so that an ordinary test with a browser passes with room for a slower computer, and so that a
  test that drives the page sixty times does not. Tagged `@fast` on purpose in a trial, that test is reported: 3.79 s
  against 2.00 s.
- 10 seconds is a ceiling. A test over it gets no tag. It is to be split or rewritten.
- The check also fails a test tagged `@slow` that ran within the `@fast` limit, so a test cannot carry a looser tag
  than it needs.
- **These limits belong to this application on this computer.** The application is small and in memory. On another
  application the same method would give other numbers.
- Not established: whether the time Playwright reports for a test includes starting the browser.

## The tag that was removed: `@smoke`

The first vocabulary had a sixth kind of tag, `@smoke`, for "the tests to run first". It was removed, for three reasons.

1. **It did not belong to a dimension.** A test would carry it in addition to its five tags, and nothing said when.
2. **Two testers would not agree on it.** "Important enough to run first" is exactly the clever tag the quest warns of.
3. **It said nothing the other tags did not.** What a smoke run needs is tests that catch the worst faults and finish
   quickly. That is `@risk-high` together with `@fast`.

So smoke is now a **selection**, written in the scheme: `--grep "(?=.*@risk-high)(?=.*@fast)"`. It lists five tests. A
test joins or leaves the smoke run because its risk or its measured duration changed, not because someone decided.
The check rejects `@smoke` if it is put on a test: it is outside the vocabulary.

One cost, stated in the scheme: all five smoke tests write. The smoke run cannot be used where writing is not allowed.

## The criteria, one by one

All evidence is in `logs/tag-check.txt`. "Tested" means the check made the comparison and has a trial showing that it
can fail.

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | The scheme defines each tag in all five dimensions | Tested | Part 1. The five dimensions are the five asked for, each with a rule and two or more tags, each tag with a meaning. Seven trials in Part 5 |
| 2 | Every test carries one tag from each dimension | Tested | Part 2 lists the ten tests with the tag found for each dimension. "Every test" means every test of `tagged.spec.ts` |
| 3 | A tag outside the vocabulary is rejected by a check | Tested | Part 5: `@smoke`, a misspelt tag, a tag with a capital, a tag written into a title, and a tag on a group of tests are each reported. The check then exits with status 1 |
| 4 | A test missing a dimension is reported by name | Tested | Part 5: with the risk tag taken off, the report is `"the page lists a customer that was there before, with its plan" has no tag for the dimension Risk.` |
| 5 | Write tests are distinguishable from read-only tests by tag | Tested | Part 3: each `@read` test sent only reads and each `@write` test sent a write, by recorded requests. Part 4: `@read` and `@write` between them select every test once, and the `@read` selection, run together, sent three GETs and nothing else |
| 6 | Duration tags have stated limits | Tested | Part 1: each has a limit, written once. Part 3: every test ran within the limit of its tag |
| 7 | The vocabulary fits on one page | Recorded | Part 1: the file on disk is 60 lines and 3279 characters, against a limit of 66 lines and 3600 characters. **This is a count, not a printed page** |

## Where the important artifacts are

| Path | What it is |
|---|---|
| `participant/context/playwright/tag-scheme.md` | The scheme: five dimensions, 13 tags, the limits, the two selections |
| `participant/tests/playwright/support/tags.ts` | The vocabulary as data. The one place it is written |
| `participant/tests/playwright/tagged.spec.ts` | The ten tagged tests |
| `participant/tests/playwright/tools/tagging-check.ts` | The check |
| `participant/tests/playwright/tagging.config.ts` | Playwright settings for this quest: one file, one worker, no retries |
| `participant/evidence/playwright-tagging/playwright-attempt-009/logs/tag-check.txt` | The check's saved output |
| `participant/evidence/playwright-tagging/playwright-attempt-009/logs/independent-read.txt` | What the two AI readers found and what was changed |

## Stretch goals

- **Generate the scheme document from the check: done.** `tagging-check.ts --write-scheme` writes it from
  `support/tags.ts`. Every run compares the file on disk with what would be written, byte for byte.
- **Add a requirement tag: not done.** The application has no written requirements to point a tag at. A tag that named
  invented ones would be a tag anyone could be wrong about.

## How to reproduce the behavior

Node 22.18 or later, and the Playwright browser already installed for the earlier Playwright quests.

    cd participant/tests/playwright
    node tools/tagging-check.ts

It starts the made-up customer directory on this computer, runs the tests, stops it, and writes `logs/tag-check.txt`.
It takes about two minutes. The last line is the result. Times will differ on another computer.

    node tools/tagging-check.ts --write-scheme

writes the scheme document again from the vocabulary.

## What was tested or validated

- **The tags are read the way Playwright reads them.** The check asks Playwright to list the tests with their tags, so
  a tag in a title or on a group of tests is seen too.
- **What each test does.** Thirty runs, each test alone three times, through a recorder in front of the application.
  All passed.
- **That the check can fail.** 29 trials. Fifteen change a copy of the test file and fourteen change a copy of the
  vocabulary or of the document. Each must be reported, and the trials on tests must name the test.
- **Nothing left behind.** At the end the application holds its four starting customers, the test file is byte for byte
  what it was, and no changed copy remains.
- The project's secret scan and a search for names and paths, over every file of this quest: nothing found.

## What the independent readers found

Two AI readers, not people. Full account in `logs/independent-read.txt`.

- **Reader 1** tagged the ten tests from the scheme alone. It differed from the file on one risk tag and had a real
  choice on four more, and on feature for two. It found no room to disagree on read or write, or on layer. It also
  found four weak places in the tests. The risk and feature rules were rewritten, one tag moved, and the tests fixed.
- **Reader 2** found that a failed run left an old passing log in place, that the scheme checks could not be shown
  failing, that the page limit looked fitted to the document, and that labels said "browser" where a header was read.
  All were corrected. The check grew from 41 checks to 59.
- **Neither reader saw the corrected version.**

## Remaining limitations

- **Feature and risk are still judgements.** The check sees that a test has one tag for each. It cannot see that the
  tag is true. Whether two testers would now agree on risk has not been tried again.
- **The check sees one file.** A test in another file is not checked.
- **It sees requests to one address.** A write sent elsewhere, a change made with a GET, or a write made only on some
  runs would not be seen.
- **Layer is read from a header.** A test that takes a page and never loads the application would read as having no
  browser.
- **Durations are of this computer.** A slower one could fail a `@fast` test that is tagged correctly.
- **One page is a count of lines and characters.**
- **Nothing stops Playwright running a wrongly tagged test.** The check reports it when the check is run. It is not
  wired into the test run.
- Left as they are in the tests: clean-up accepts "not found", and "no other customer" is checked against one other.

## Reflection

*Which dimension was hardest to keep consistent across testers?*

Risk. I thought I had defined it clearly: high if stored data is wrong, medium if only what is shown is wrong, low if
it is an inconvenience. A second reader, given only my scheme, tagged the tests differently, and was right to. A test
that reads the list cannot tell whether a wrong plan was stored wrongly or shown wrongly, so my definition asked the
tester to guess a cause the test never sees. Read or write, layer and duration gave no trouble because each is a fact
about the test that a program can measure. Risk only became steady when I stopped asking "how bad would this be?" and
asked "what does this test do, and what does it assert?" Even now it is the one I trust least, because nothing checks
it but a person reading the rule. If I did this with a team I would have two people tag the same ten tests apart
before agreeing the scheme, because that is what showed me the problem.

## Sensitive values

No secret, token, password or cookie is in any file of this quest. The application is made up and runs on this
computer only. The four customers in it are invented, and so are the names the tests add. No real person, site, account
or home-folder path appears. Test results and traces go to a folder that is not committed.
