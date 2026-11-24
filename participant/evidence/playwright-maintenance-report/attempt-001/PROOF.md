# PROOF: Recommend Changes Before Modifying a Failed Test

Quest `playwright-maintenance-report`, attempt `playwright-attempt-005`.

## How this was made

The made-up checkout, the test, the report, the check script and this document were written by an AI assistant
(Claude) at the participant's direction. The participant made two decisions: the application's change is a
legitimate redesign with one unmentioned change to the tax figure behind it; and whether the proposed change
weakens the test is judged by applying the report's own change list to a copy and comparing what each version
of the test can catch.

**The application is made up and ran on this computer only**, on 127.0.0.1. It holds invented products and
prices, no sign-in, no token and no customer. Nothing else was contacted.

**The test was not edited.** Its checksum was taken before the report was written, and is the same now. The
proposed change has been made only to copies in a scratch folder, which the check deletes. The handed-in test
still fails, as it should.

Words used below: **recorded** means the saved log of the check shows it. **observed** means an independent
reader's reply shows it. **not assessed** means nobody checked it.

## Approach

**What was built, in order.**

1. A checkout page in two versions: before a redesign (`demo-app/checkout-server.before.mjs`) and after
   (`demo-app/checkout-server.mjs`, the one in use). The difference is `needs-maintenance.app-change.diff`,
   beside the test.
2. The test, `needs-maintenance.spec.ts`, written for the version before. It passes there.
3. `maintenance-report-check.ts --before`. It took the test's checksum, confirmed no report existed, and
   recorded the test passing before the redesign and failing after it, at line 8.
4. **The report**, written then, from that one failure and from reading the diff.
5. The check, run after. It took the checksum again, and tried the report's proposal on a copy.

**What the report says.** The failure is two things, and they must not be mixed.

- A **test change**: six lines of the test are out of date about how the page is built. The button was
  relabelled, the summary's markup changed, and amounts gained a currency sign. All three are in the
  redesign's change note.
- A **possible product bug**: behind that, the tax is worked out differently. The test expects 7.20 and the
  page shows 8.00. The change note does not mention it.

The report proposes the six line changes and nothing else, keeps the expected tax at 7.20, and says the tax
question goes to whoever owns the rule. After the change the test still fails, at the tax line. **The
recommendation does not end in a green test, and that is the point of it.**

## How I judged that the change did not weaken the test

This is what the quest asks the proof to explain. The judgment was made by running things, on a copy.

**The copy was made from the report.** The check reads the report's part 4, where each change gives a line
number, the line as it is now and the line to put there, and applies those to a copy of the test. If a "now"
line had not matched the file, it would have stopped. It did not (criteria 2 and 7).

**Then six signs, each written in the report before any was tried** (criterion 4):

| Sign | What it asks | Result on the copy |
|---|---|---|
| W1 | as many `expect()` calls as before | 6 and 6 |
| W2 | every amount still there, same line, same digits | all five |
| W3 | nothing loosening added: no contains or pattern match, `soft`, `skip`, longer timeout, negation, `try`, or assertion commented out | nothing |
| W4 | only the listed lines differ | only lines 8, 9, 11, 12, 13, 15 |
| W5 | against the checkout in use, it **fails at the tax line** | fails at line 11: expected `£7.20`, received `£8.00` |
| W6 | every deliberate fault the old test caught, the copy catches | 8 of 8, and 8 of 8 |

**W5 is the one that matters, and it runs backwards.** Here a changed test that passes is the weakened one.
The application's tax figure is not the one the business rule gives, so a test that still checks the rule has
to fail. The copy does, at exactly the line and with exactly the two figures the report predicted before
anything was run.

**W6 needed the tax question set aside**, because against the checkout in use the copy stops at line 11 and
never reaches the total, the button or the confirmation. So the check makes a scratch copy of the redesigned
checkout with its two tax lines put back, and runs the copy of the test against that. There it passes, all
the way through. Then eight faults are switched on one at a time: the tax left out of the total, a wrong tax
rate, a wrong tax figure shown, the discount ignored, and four more. The original test, against the old
checkout, catches all eight. The copy, against the new one, catches all eight, each at the same line.

**The contrast: three tempting fixes**, each applied to a further copy. All three make the test pass.

| Tempting fix | Faults it lets through, of 8 | Which signs catch it |
|---|---|---|
| Delete the tax assertion, set the totals to what the page shows | 1: a wrong tax figure shown | W1, W2, W4 |
| Set every expected amount to what the page shows | **none** | W2 only, and W5 |
| Keep the lines, only check that an amount is shown | 6 | W2, W3 |

The middle one is the instructive one. It lets no fault through. By W6 alone it is as strong as the original.
It is still wrong, because it has written the new tax figure into the test as correct, and that is the one
thing nobody has decided. Only W2 and W5 show it. So "does it catch as many faults" is not a sufficient test
of weakening, and I would not have known that without trying it.

## The criteria, one by one

| # | Criterion | Status | Where |
|---|---|---|---|
| 1 | The report states the cause of the failure and cites the evidence | recorded | `participant/context/playwright/maintenance-report.md` parts 1 and 2. `logs/unchanged-check.txt` part 2: every file it cites exists, and the failure it describes, line 8 and `#subtotal`, is the failure the test gives when run |
| 2 | The proposed change touches only the lines the evidence shows are affected, and the report lists each line | recorded, with a limit | Report part 4: six changes, and a line saying which of the 16 lines change and which do not. Log part 3 and sign W4: only those six differ. **The limit:** only line 8 was seen to fail. Lines 9 to 15 are judged affected from the diff. The log then confirms it: with the tax lines put back, the changed copy passes through all of them |
| 3 | The business assertion to preserve is named | recorded | Report part 5: the tax, line 11, 7.20, with the rule and the two totals that follow from it |
| 4 | The report says what would show that the change weakened the test | recorded | Report part 6, six signs. Log parts 4 and 5 try each one, on the proposed change and on three wrong ones |
| 5 | The test file is unchanged when the report is written | recorded | Log part 1. Checksum before the report, from `logs/before-report.txt`, taken when no report existed. The report's time of writing, later. Checksum after, the same. And the same again at the end of every run |
| 6 | The report distinguishes a test change from a possible product bug | recorded | Report part 7, and "in short" at its head |
| 7 | Another person could carry out the change from the report | recorded for a program. observed for an AI reader. not assessed for a person | Log part 3: a program applied the change from the report alone. `logs/independent-read.txt`: a reader given only the report and the test produced the same changed test, line for line |

## Artifacts

| Required item | File |
|---|---|
| The failing test | `participant/tests/playwright/needs-maintenance.spec.ts` |
| The application's change | `participant/tests/playwright/needs-maintenance.app-change.diff`, beside the test. Both versions are in `participant/tests/playwright/demo-app/` |
| The maintenance report | `participant/context/playwright/maintenance-report.md` |
| The unchanged check | `logs/unchanged-check.txt`, 37 checks |
| The check script | `participant/tests/playwright/tools/maintenance-report-check.ts` |
| This narrative | `PROOF.md` |

Also here: `logs/before-report.txt`, the checksum and the failure, taken before the report;
`logs/independent-read.txt`; and `participant/tests/playwright/maintenance.config.ts`, the settings the test
runs with.

## Stretch goals

- **Estimate the effort of each option:** done, in the report's part 8. Seven options, three of them the
  tempting ones. The times are estimates and the report says so.
- **Link the report to the triage that preceded it:** done, in part 9. By the earlier quest's rules the
  failure seen is a `test-defect`, and the one that follows is `inconclusive` between a product bug and an
  intended change, with what would settle it.

## Reproduce

From `participant/tests/playwright`, with Node 22.18 or later:

    node tools/maintenance-report-check.ts
    node tools/maintenance-report-check.ts --copy

The first runs the whole check and writes `logs/unchanged-check.txt`. It starts the checkout on this computer
and stops it. The second prints the test as it would read after the change, and writes nothing.

`--before` cannot be run again usefully: it records that no report exists, and one now does.

To see the failure by hand, start the application and run the test:

    node demo-app/checkout-server.mjs
    npx playwright test --config maintenance.config.ts

## What was tested

| What | Result |
|---|---|
| Before the report | 4 checks, all pass (`logs/before-report.txt`) |
| After the report | 37 checks, all pass (`logs/unchanged-check.txt`). They include 6 ways of spoiling the report, the test or the copy, each reported |
| Runs of a test against an application | 48 in the full check, all on this computer |
| Independent read | One AI reader. It made the same changed test as the program. It also found faults, below |

**What the reader found, and what was done.** The reader was asked to carry out the change and then to push
back. Its sharpest point was about how the quest was built.

- **A test switch had been put inside the application.** To run "the redesign with the old tax", the first
  version of the redesigned checkout read a setting and worked the tax out either way. So the application's
  own diff showed a named, deliberate, two-way switch on the tax line. The reader read the report's quotation
  of it and said: nobody writes that by accident, so calling it a possible mistake is the weaker reading, and
  "nothing says which" is false. It was right. The evidence for the central question had been bent by the
  apparatus built to test it. The switch was taken out of the application. The check now makes its own scratch
  copy of the checkout with the tax lines put back. The handed-in diff shows one word changed on the tax line.
- **The report stated a prediction as a finding.** It said the tax "is now 8.00". When that was written the
  test had stopped at line 8, and 8.00 had only been read from the diff. The report now says at its head what
  was seen and what was predicted, and its part 10 says what was observed afterwards.
- **A fair alternative had been ruled out without argument**: marking the test as an expected failure, with a
  ticket. It is now option G, with the reason it is not the proposal.
- Smaller points, all taken: quote the diff, give the checksum, list the faults, say which file to edit and
  when, and do not call a test "sound" on one pass.

Faults found while building, apart from the reader:

- A check in the script looked for the words "line 11" in the report and failed, because the report says
  "Line 11". The check was wrong, not the report. It was made to ignore capitals.

## What could not be done, and limitations

- **Whether the tax figure is a bug is not known, and cannot be.** The shop is made up, so nobody owns its tax
  rule. The report records the question and it goes no further. In a real team that is the step that matters
  most, and it is the one this exercise cannot do.
- **The report was revised after the check and the read.** Its part 4, the changes, was not altered, and the
  test was never touched. But "written before the test was touched" is true of the first writing, and of every
  later one only because the test was still untouched. The log's "report last written at" is the last
  revision. The checksum before it is from the start.
- **The application was changed after the report was first written**, to take the switch out. Its behaviour
  as run is the same: the check shows the test failing at the same line and the copy receiving the same
  figure. `logs/before-report.txt` was recorded against the first version.
- **Only line 8 was ever seen to fail in the handed-in test.** Everything about lines 9 to 15 comes from the
  diff, then from copies.
- **"Weakened" is measured against eight faults** that the assistant chose, in an application the assistant
  wrote. A fault of another kind could pass both tests.
- **The handed-in test fails.** That is deliberate. Anyone running the suite will see it red until the tax is
  ruled on.
- One reader, an AI assistant, and the revised report was not read again. No person carried out the change.
- The check's own faults were tried six ways in memory. There is no separate file of planted faults for it,
  as the earlier Playwright quests had.

## Reflection

*What change would be tempting here and wrong?*

Setting the expected amounts to what the page shows now.

Not deleting the tax assertion. That one is the quest's scenario, and it is obviously wrong the moment you
say it out loud. The one I would actually have made is quieter. The test says 7.20, the page says 8.00, the
redesign changed everything else on the page, so update the number along with the locator and move on. It
takes five minutes. Every assertion is still there. Every one is still exact. It looks like the careful
version of the fix.

And when I tried it on a copy, it passed every test of strength I had. Eight deliberate faults, and it caught
all eight, the same as the original. If "does it still catch the bugs" had been my only question, I would
have called it sound. It is wrong for a reason none of those faults can show: it writes down, in the one
place meant to check the rule, that the rule has changed. Nobody decided that.

What caught it was the dullest sign on the list, that the digits of an amount had changed, and the strangest
one, that the test passes. I did not expect "the test passes" to be the warning. I had it in my head that a
maintenance job ends in green. Here the honest end is a test that fails at one line, and a question for
somebody else.

The other thing I take from this is about my own evidence. To run my comparison I had put a switch in the
application, and it showed up in the diff looking like a deliberate change. A reader looked at the diff I was
quoting and told me the bug theory was the weak one. They were reading my scaffolding. I had built the thing
I was investigating, and I still managed to plant misleading evidence in it without noticing.

## Sensitive values

- No sign-in, token, cookie or credential exists in the application, the test, a log or the report.
- The application is made up, and so are its products, prices and discount code. It listens on 127.0.0.1 only.
- No real site or system was contacted.
