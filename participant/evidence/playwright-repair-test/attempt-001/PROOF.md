# PROOF: Repair a Test Without Weakening Business Validation

Quest `playwright-repair-test`, attempt `playwright-attempt-006`.

## How this was made

The repaired test, the corrected application, the check program, the records and this document were written by
an AI assistant (Claude) at the participant's direction. The participant made two decisions.

**The first is a ruling.** The maintenance report from the earlier quest left one question open: the redesigned
checkout works tax out before the discount, 8.00, where the test expects it after, 7.20. The report said the
test must not decide which is right and that the owner of the tax rule must. In this made-up shop that is the
participant, who ruled: **it is a bug.** So the application is corrected and the repair is the report's six
lines, with no expected amount changed.

**The second:** the business rule is broken on purpose in three different ways, not one.

**The application is made up and ran on this computer only**, on 127.0.0.1. It holds invented products and
prices, no sign-in, no token, no cookie and no customer. Nothing else was contacted. No trace, screenshot or
video was taken.

**Nothing approved earlier was changed.** The test before the repair, the application in use and the earlier
settings file are byte for byte as they were. The repaired test, the corrected application and the settings
for this quest are new files beside them. The rule was broken only in copies in a scratch folder, which the
program deletes.

Words used below: **recorded** means the saved log shows it. **observed** means an independent reader's reply
shows it. **not assessed** means nobody checked it.

## The short version

- The repair is the six line changes of the maintenance report, each word for word, and nothing else.
- The repaired test passes against the corrected application and fails against each of three applications with
  the tax rule broken.
- A program compares the test before and after. It reports the real repair as sound and 22 deliberately weakened
  versions as weakened.
- **Two things came out worse than I expected, and both are in the records.** An independent reader wrote eight
  weakened tests to get past the part of the check that reads the test files, and as first built it missed all
  eight. And a second reader named five ways of breaking the tax rule that the test does not catch at all,
  before the repair or after it.

## Approach

**The repair.** The six changes were applied from part 4 of the report to a copy of the test, and saved as a new
file. The check then confirms the new file is the old one with exactly those six lines replaced.

**The weakening check** has two layers, and they are worth keeping apart.

| Layer | Reads | Reports |
|---|---|---|
| 1 | the two test files only | assertions removed, matchers changed, expected values loosened, conditions, skips, early exits, stubs and the like: rules A1 to A10 at the head of the program |
| 2 | the maintenance report | any changed line that is not a line the report lists, or does not read exactly as the report says |

A version of the test is sound only if Layer 1 reports nothing and Layer 2 accounts for every change.

**The mutation run** starts the corrected application and copies of it with one line of source changed, and
runs the repaired test against each. The amounts each copy sends are read back and recorded before the test
runs, so the record shows what a customer would see and not only which line was edited.

## How I chose the way to break the rule (criterion 5)

The rule, from line 10 of the test: tax is 20% of what the customer pays for the goods, after the discount.
36.00 at 20% is 7.20.

I wanted each way to be a mistake a developer could really make, and each to break a different part of the
rule.

| Way | What was changed | Why this one | The page then shows | The repaired test |
|---|---|---|---|---|
| 1 | tax worked out on the subtotal, before the discount | it is the fault the redesign actually shipped: one word, `goods`, became `subtotal` | tax £8.00, total £44.00 | fails at line 11, expecting £7.20, receiving £8.00 |
| 2 | the rate, 25% for 20% | the rule has a rate and a thing the rate is taken of. Way 1 breaks the second. This breaks the first | tax £9.00, total £45.00 | fails at line 11, expecting £7.20, receiving £9.00 |
| 3 | the tax shown correctly and left out of the total | the tax line on the page stays right, so the tax assertion cannot see it. It asks whether the test guards the rule or one figure | tax £7.20, total £36.00 | fails at line 12, expecting £43.20, receiving £36.00 |

A control changes the same tax line without breaking the rule, and the test passes. So a failure is the rule and
not the editing.

**These three were mine, and I knew what each would do before running it.** They demonstrate that the test has
teeth. They are not a search for where it has none. A reader did that search: see "What the test does not
catch".

## What the weakening check cannot see

This is what the quest asks the proof to explain. Each of these was tried and is in a record.

**1. A weakening that is not in the test file.** The repaired test, unchanged, run by a command that selects no
test and is told that is acceptable, exits 0 with the rule broken. The check reads the test file, finds it
identical, and reports nothing (`logs/weakening-check.txt` part 7). The same holds for the settings file, a
file the test imports, the packages the import resolves to, the application's markup, the port it is pointed
at, and a person running a different copy of the test.

**2. A trick that is not on Layer 1's list.** Layer 1 is a list of known tricks read out of text. A reader given
the first version wrote eight weakened tests and predicted it would report none. It reported none. Seven of
the eight ran green. Six let every broken rule through. They included a `return` hidden after a comment, six
lines of the test inside a template string, and `expect` replaced on the import line by a function that checks
nothing. Layer 1 was changed and now reports those eight (part 6B). That says nothing about a ninth. Known to
remain: a regular expression containing a quote throws the reading of its line off, and `page` or `test` given
another meaning is not noticed.

**3. Meaning.** Layer 1 can see that an assertion now looks at something else. It cannot tell whether the new
thing is the right element. It lists the change as "to be accounted for" and leaves it to Layer 2. Without a
written plan there would be nothing to hold it to (part 6, versions S1 and S2).

**4. A weak plan.** Layer 2 holds the repair to the report. Had the report proposed a weak change, Layer 2 would
have accepted it. The plan, the repair, the check and the corrected application have one author.

**5. Whether the test was any good to begin with.** The check compares before with after. A test that never
guarded the rule passes as "not weakened". See the next section.

What holds this repair is Layer 2: with every line fixed to the report word for word, there is no room for a
trick. Two readers looked for a way past it and found none.

## What the test does not catch

The application has one basket and one discount, so the test checks the tax rule at one point: 40.00 of goods,
10% off. A second reader listed faults that give the right figures at that point. Five were run
(`logs/mutation-run.txt` part 6):

| Fault | Tax shown | The repaired test | The test before the repair |
|---|---|---|---|
| a rate of 20.01% | £7.20 | passes | passes |
| 18% of the subtotal before the discount | £7.20 | passes | passes |
| the tax is always 7.20 | £7.20 | passes | passes |
| the discount taken off before tax is always 4.00 | £7.20 | passes | passes |
| the tax is never more than 7.20 | £7.20 | passes | passes |

So what is shown is this: **the repaired test is no weaker than the test it replaces.** It is not shown to guard
the rule for any basket but the one. Closing that gap needs a second basket or a second discount. That is a new
test, outside a repair whose brief was to change six lines and nothing else, and it is not done here.

## The criteria, one by one

| # | Criterion | Status | Where |
|---|---|---|---|
| 1 | The repair follows the maintenance report | recorded, observed | `logs/weakening-check.txt` part 2: all six changes made, each exactly as written. Part 3: every hunk of `repair.diff` is labelled with the report line that called for it, and each label is checked against that line of the report. A reader compared the two files itself and agreed |
| 2 | No assertion is removed, loosened or made conditional | recorded, observed | Part 2. Six before, six after, each paired on the same line. Same matcher, same number. Each expected value gained the one character £ and lost none. Each is still a plain awaited statement in the test's own body. A reader agreed: "None of the six is weaker" |
| 3 | The diff is limited to what the report said would change | recorded | Part 2: the lines that differ are 8, 9, 11, 12, 13 and 15, the lines the report lists, and the test has the same number of lines. Part 3: applying `repair.diff` to the old test with the system's patch program gives the repaired test byte for byte |
| 4 | The repaired test passes against the corrected application | recorded | `logs/mutation-run.txt` part 2. One test ran, exit code 0. The corrected application differs from the one in use in two lines of code, both the tax. The test before the repair fails there, so the repair is what makes it pass |
| 5 | The repaired test fails when the business rule is broken | recorded, with a limit | Part 3: three ways, each failing at a named line with the expected and received amounts. Part 5: eight more faults, each caught at the same line as before the repair. **The limit:** part 6, five ways it does not catch |
| 6 | The weakening check flags a deliberately weakened version | recorded, with a limit | `logs/weakening-check.txt` part 5: 22 of 22 reported by Layer 1, the scenario's "contains a number" among them. **The limit:** as first built, Layer 1 missed all eight of a reader's versions. Part 6B |
| 7 | The comparison lets a reviewer see each assertion before and after | recorded. not assessed by a person | `participant/context/playwright/assertion-comparison.md`. One section for each of the six assertions: the whole line before and after, then what it looks at, the matcher, the expected value, the number, and how it is called, each marked the same or changed. Part 4 confirms the file is what the program writes. A reader found its verdict sentences claimed more than the code worked out. They are now built from what was found. Nobody has read the document since |

## Artifacts

Start created the folder `playwright-attempt-006`, and the work is there. The quest text names `attempt-001`,
so copies of the files it names are in `participant/evidence/playwright-repair-test/attempt-001/`, with a note
saying where the originals are.

| Required item | File |
|---|---|
| The diff of the repair | `repair.diff` |
| The comparison of assertions | `participant/context/playwright/assertion-comparison.md` |
| The repaired test passing, and failing with the rule broken | `logs/mutation-run.txt`, 20 checks |
| The weakening check on the repair and on weakened versions | `logs/weakening-check.txt`, 61 checks |
| The script that produced the check output | `participant/tests/playwright/tools/repair-test-check.ts` |
| This narrative | `PROOF.md` |

Also: `logs/independent-read.txt`, what the readers found. And in `participant/tests/playwright/`:
`needs-maintenance.repaired.spec.ts`, the repaired test; `demo-app/checkout-server.corrected.mjs`, the corrected
application; `repair.config.ts`, the settings.

The diff and the comparison are written by the program from the two test files. The check fails if either has
been adjusted by hand.

## Stretch goals

- **Try three different ways of breaking the rule:** done, above. Five more, a reader's, were also run, and are
  not caught.
- **Automate the weakening check in the repository:** done. `tools/repair-test-check.ts` is in the repository
  and runs with one command. It is not wired into anything that runs it unasked.

## Reproduce

From `participant/tests/playwright`, with Node 22.18 or later and the Playwright browser already installed:

    node tools/repair-test-check.ts --write
    node tools/repair-test-check.ts

The first writes the diff and the comparison. The second writes the two logs and takes about a minute and a
half. It starts the made-up checkout on 127.0.0.1 and stops it, and contacts nothing else.

## What was tested

| What | Result |
|---|---|
| The repair, by both layers of the check | sound: nothing weakened, every change accounted for |
| The repaired test, corrected application | passes |
| The repaired test, three ways of breaking the rule | fails each time, at the line and with the amounts expected |
| The repaired test, eight harness faults | 8 of 8 caught, each at the line the old test caught it at |
| The repaired test, five faults that suit the one basket | 0 of 5 caught. The old test: 0 of 5 |
| 22 deliberately weakened versions | 22 reported by Layer 1. 14 of them run green and let a broken rule through |
| 4 changes the report did not ask for | 4 reported by Layer 2. One of them is harmless: the check is strict on purpose |
| 8 versions a reader wrote to beat Layer 1 | as first built, 0 reported by Layer 1 and 8 by Layer 2. Now 8 and 8 |
| That the check can fail | four spoiled inputs, each reported |

## What the readers found, and faults found while building

Three AI readers, no person. Full account in `logs/independent-read.txt`.

- **Reader 1** beat Layer 1 eight times out of eight, as told above.
- **Reader 2** confirmed the repair, found the five faults the test does not catch, and found nine of my checks
  looser than their labels. One counted any failure as "caught" without looking at where. One would have passed
  on a missing figure. Two could not fail at all. My control rewrote the rate as 1 / 5, which is the same
  number and proved nothing. Each was tightened.
- **Reader 3** was asked to beat Layer 1 as changed. **It returned no result:** its report did not arrive, and it
  was not asked again.

Faults I found myself:

- The check crashed on the one assertion that has no expected value, the heading check.
- A check for "no hunk is unlabelled" searched the whole diff for words that its own explanatory header
  contains.
- A stub in one of my weakened versions sent its page without saying how it was encoded, so the £ arrived
  garbled and the version failed for the wrong reason. It looked caught and was not.

## What could not be done, and limitations

- **Layer 1 as changed has not been read independently.** The first version was, and failed. The changes answer
  those eight tricks.
- **The test guards the rule at one point only.** Five faults pass. Not fixed here.
- **The three ways of breaking the rule were chosen by the author**, with known outcomes.
- **One author.** Plan, repair, check and corrected application. Layer 2 trusts the plan.
- **Line 3 of the repaired test is a comment that names the uncorrected application.** The report said to leave
  lines 1 to 7 alone, so it was left. It is now out of date.
- **The ruling that the tax is a bug** is the participant's, as owner of a made-up shop. In a real one it would
  be somebody else's to make, and the repair would wait for it.
- **The comparison reads text.** That each new locator finds the right element is shown by the runs, not by
  the comparison.
- **No person read any of it.** All readers were AI assistants, and their limits were given in words.

## Reflection

*Which kinds of weakening would your check miss?*

More than I thought when I started, and I only know that because somebody tried.

I built the check and gave it 22 weakened tests, every one I could think of. It caught all 22 and I was
pleased with it. Then a reader who had never seen it wrote eight more in a few minutes and it caught none.
Not one. A `return` tucked in after a comment. The whole middle of the test wrapped in a string. `expect`
itself swapped for a function that does nothing. Seven of them ran green.

The lesson I take is about what I had actually tested. My 22 were the weakenings I already knew about, so the
check was a list of my own ideas checking itself against my own ideas. It could not have failed.

So, the kinds it would miss. Anything outside the test file: the settings, the command line, the application.
Any trick not on its list, and I now believe there is always one more. A changed locator that points at the
wrong thing, because it reads text and not meaning. And a test that was never much good, because all it
compares is before and after.

That last one surprised me most. A second reader pointed out that the test only ever checks one basket. A tax
rate of 20.01% passes. A tax hard-coded to 7.20 passes. They passed before my repair too. So I can say
truthfully that I did not weaken the test, and that is a smaller claim than "the test protects the rule".

What actually protected this repair was the dull part. The report said which six lines and what each should
say, and the check holds the test to that, word for word. Nobody got past that. The clever part of the check,
the part that tries to recognise weakening on sight, is the part that failed. If I had no written plan to hold
a change to, I would not trust it by itself.

## Sensitive values

- No login, token, credential or session cookie was used or exists in the application.
- No trace, screenshot or video was recorded. The settings switch all three off.
- The application, its products, prices and discount code are invented. It listens on 127.0.0.1 only.
- Paths in the logs are shown from the repository's top folder.
