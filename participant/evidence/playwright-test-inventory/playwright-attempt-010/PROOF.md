# Proof · playwright-test-inventory

Attempt: `playwright-attempt-010`

## How this was made

The participant made two decisions: that the inventory covers a new, documented suite file and leaves the files of
earlier quests untouched, and that the value score is worked out by a rule and not typed by the author. An AI
assistant (Claude) wrote the suite file, the requirements, the generator, the check and this file, and ran them on the
participant's computer. Everything here uses a made-up application on that computer. Two further AI assistants read
the work. No person other than the participant has read it.

## The short version

- A **generator** reads test files as text and writes the inventory. It does not load, run or change a test file.
- The **inventory** has one row for each of 12 tests: identifier, purpose, tags, source requirement, value and place.
  It also has a table for finding the tests of a requirement.
- It shows **one requirement with no test** (DIR-09) and **one pair of possible duplicates** (DIR-T02 and DIR-T11).
- The **run record** passes 69 checks. It compares what the generator read with Playwright's own list of the same
  file, test by test.
- The first version's purposes mostly restated the titles. A reader said so, and all twelve were rewritten.

## Where purpose and source are written

**Beside the test, in the details Playwright itself takes**, in the same object as its tags:

    test(
      "upgrading one customer changes that customer and no other",
      {
        tag: ["@feature-upgrade", "@risk-high", "@write", "@layer-ui", "@fast"],
        annotation: [
          { type: "id", description: "DIR-T07" },
          { type: "purpose", description: "Catches an upgrade reaching the wrong customer, or more than one. It looks at one other customer, and on the page only." },
          { type: "source", description: "DIR-04" },
        ],
      },
      async ({ page, own }) => { ... },
    );

- **Why there.** Whoever changes the test has the purpose under their eyes in the same edit. Playwright also carries
  annotations into its own reports, so the same words appear there.
- **Identifier.** Written, not derived from the title or the line, so that renaming or moving a test does not change
  what it is called.
- **Source.** The number of a requirement in `participant/context/playwright/directory-requirements.md`. That list is
  made up, like the application, and was written for this quest.
- **Value is written nowhere.** The generator works it out: start from the requirement's importance (must, should,
  could), and go down one level for `@risk-medium` and two for `@risk-low`.
- **They must be plain quoted text.** A purpose in a variable is reported as unreadable, not guessed.

## One duplicate found

**DIR-T02 and DIR-T11 have the same purpose**, and the inventory reports them under "Possible duplicates".

- DIR-T02, "the list of customers comes back as data, each with an id, a name and a plan", checks one starting
  customer exactly and then the fields of every customer returned.
- DIR-T11, "each customer returned by the data interface has an id, a name and a plan, and nothing else", checks the
  fields of every customer returned, and that there are at least four.
- **How it came to be there, plainly:** I added DIR-T11 for this quest and gave it DIR-T02's purpose, so that the suite
  would hold a real duplicate for the inventory to find. It was not an accident found in the wild.
- **Is it a real duplicate?** A reader who opened both tests said DIR-T11 "is almost wholly redundant": DIR-T02
  already runs the same check. The inventory could not have told me that. It reports the pair, and a person looks.
- **What I would do:** delete DIR-T11. It is left in, so that the inventory handed in shows the report.

The generator finds duplicates by purpose only when the words match, capitals and punctuation aside. A second, weaker
report, "possible overlap", lists tests with the same source and the same tags. It also names DIR-T05 with DIR-T12,
which are one script with one change and are not duplicates.

## The criteria, one by one

All evidence is in `logs/inventory-run.txt`. "Tested" means the check made the comparison and a trial shows it failing
when it should.

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | The inventory is generated from the test files | Tested | Part 1: the inventory on disk is, byte for byte, what the generator gives today. The generator imports nothing that could load a test. Part 7: a copy edited by hand is reported |
| 2 | Each test has a unique identifier, purpose, tags, source and value | Tested | Part 2: 12 rows, none with a gap. Each row is compared with what Playwright reads for the test at that line: identifier, purpose, source, tags, title. Values are worked out again from a separate table |
| 3 | A test missing a purpose or a source is reported as incomplete | Tested | Part 5: a test added without a purpose, without a source, and with neither, each reported by identifier or place |
| 4 | Two tests with the same purpose are reported as possible duplicates | Tested | Part 4: the pair in the suite. Part 5: a test added with DIR-T04's purpose in other capitals and punctuation |
| 5 | The inventory is identical across two runs | Tested, on one computer | Part 1: two runs, the same 8918 bytes and the same sha256. It holds no date. **Not tried on another computer or operating system** |
| 6 | Adding a test changes the inventory without any hand edit | Tested | Part 5: a thirteenth test added to a copy. The new inventory has its row, every other row is unchanged, and DIR-09 now lists it |
| 7 | A new teammate can find the tests for a requirement | Recorded, and tried once by an AI reader | Part 3: each requirement's row lists exactly its tests, with file and line. An AI reader given only the inventory found the tests for a requirement in about 20 seconds. **No person new to the suite has tried it** |

Also in the record, because the quest asks for it: **two tests sharing an identifier are rejected** (Part 5). The
generator names both by file and line, exits with 1, and writes no inventory.

## Where the important artifacts are

| Path | What it is |
|---|---|
| `participant/tests/playwright/tools/inventory.ts` | The generator |
| `participant/context/playwright/inventory.md` | The generated inventory. Not to be edited |
| `participant/tests/playwright/inventoried.spec.ts` | The suite: 12 tests, each with identifier, purpose and source beside its tags |
| `participant/context/playwright/directory-requirements.md` | The made-up requirements: nine current, one withdrawn |
| `participant/tests/playwright/tools/inventory-check.ts` | Makes the run record |
| `participant/tests/playwright/inventory.config.ts` | Playwright settings for this suite |
| `logs/inventory-run.txt` | The run record: 69 checks |
| `logs/independent-read.txt` | What the two AI readers found, and what was changed |

The quest names the folder `attempt-001`. The application made `playwright-attempt-010`. The run record and this file
are copied to `participant/evidence/playwright-test-inventory/attempt-001/`, with a note there saying so.

## Stretch goals

- **Sorted by value and by age: half done.** The inventory lists the tests by value. Age is not done: it would come
  from the history of changes, and the generator reads test files only.
- **Tests whose source requirement no longer exists: done.** A requirement that is withdrawn keeps its number in the
  requirements document. A test naming it is reported, with why it was withdrawn, and is not scored. No test of the
  suite does; the run record shows it on a copy.

## How to reproduce the behavior

Node 22.18 or later.

    cd participant/tests/playwright
    node tools/inventory.ts            writes the inventory
    node tools/inventory.ts --check    writes nothing; says whether the inventory on disk is up to date
    node tools/inventory-check.ts      makes the run record. About a minute. Needs the Playwright of the earlier quests

The tests themselves run with `node ../../node_modules/@playwright/test/cli.js test -c inventory.config.ts`. All 12
pass against the local customer directory. The generator does not need them to.

## What was tested or validated

- **Two readers of one file.** The generator reads the test file as text. Playwright, asked to list the same file,
  reads it its own way. The check compares the two for every test. Playwright loads the file to list it, which runs
  the code at its top level. No test body runs. The generator never does this; only the check does.
- **A harder file.** Groups inside groups, tags in titles, a test inside a comment and inside a string, regular
  expressions with braces and quotes, a skipped group. The generator's reading matches Playwright's on all five tests.
- **Seven files written in ways the generator does not read:** a loop, `test` under another name, a renamed group, a
  group with no braces, details in a variable, a group's tags in a variable, a file with no test. For each it says so.
- **That nothing was changed.** All ten test files in the folder, the requirements and the inventory are byte for
  byte what they were before the check ran.
- **A fault found while building.** The first generator found no tests at all in a file holding a regular expression.
  The harder-file trial caught it.
- The project's secret scan, and a search for names and paths, over every file of this quest.

## What the independent readers found

Two AI readers, not people. The full account is in `logs/independent-read.txt`.

- **The new teammate** found the tests for a requirement, the untested requirement and the duplicate from the
  inventory alone. It also found that most purposes restated their titles and that three claimed more than the test
  checks. All twelve were rewritten to say what fault the test catches and what it does not look at, and one test was
  strengthened so that its purpose is true.
- **The second reader** found many ways of writing a test that the generator would have missed in silence, and checks
  that said more than they tested. The generator's reader was rewritten to report what it cannot read, and the checks
  were corrected. The record went from 53 checks to 69.
- **Neither reader saw the corrected versions.**

## Remaining limitations

- **The inventory covers one file of ten.** The other nine belong to verified quests and were not edited. Pointed at
  the whole folder, the generator counts 45 tests and reports 33 as incomplete. That count was not compared with
  Playwright's.
- **The generator has no TypeScript parser.** It reads tests written the ordinary way and reports the unusual ways it
  knows of. A file written unusually enough could still be misread without a report. A test with a plain title
  declared in a loop is read as one test.
- **A purpose can still say nothing.** The rule counts six words and compares with the title. "a b c d e f" passes,
  and the run record shows it passing. Whether a purpose is true is not checked at all.
- **Duplicates are found by matching words.** Two tests that check the same thing with differently worded purposes
  are not reported as duplicates. DIR-T06 and DIR-T10 run the same path and neither report names them.
- **The value says little here.** It is the lower of the requirement's importance and the test's risk, so "high" is
  the same six tests the smoke selection already gives.
- **"Serves a requirement" is not "covers it".** DIR-T09 looks at the answer only, and DIR-06 also says nothing
  changes. The inventory says to read the purpose; it does not measure coverage.
- **Identifiers are unique among the files given,** not across the folder.
- **Not tried on another computer.**
- **The requirements are made up for this quest.**

## Reflection

*What stops the purposes from becoming boilerplate?*

Not the tool, mostly. My first purposes all began "Show that" and then said the title again in slightly different
words. They passed every check I had written, because a rule can count words and compare a purpose with a title, and
mine were long enough and not identical. It took a reader pretending to be new to the team to say that ten of twelve
told them nothing the title had not. What changed them was a different question. "What is this test for?" invites the
title back. "What fault would this test catch, and what does it not look at?" cannot be answered by the title, and
answering it for DIR-T06 showed me the test did not check what its purpose claimed, so I fixed the test. So three
things help, in order of how much: asking for the fault and the blind spot, not the intent; keeping the purpose
beside the test so it is in front of whoever changes it; and having someone who did not write the test read the
purposes cold now and then. The generator's checks catch only the laziest cases, and the run record shows one empty
purpose getting through. I would not trust a suite's purposes because a tool passed them.

## Sensitive values

No secret, token, password or cookie is in any file of this quest. The application is made up and runs on this
computer only. Its four starting customers are invented, and so are the names the tests add. The requirements are
invented. No real person, site, account or home-folder path appears. Test results go to a folder that is not
committed.
