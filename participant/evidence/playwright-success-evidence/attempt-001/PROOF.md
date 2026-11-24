# PROOF: Capture Evidence at Meaningful Validation Points

Quest `playwright-success-evidence`, attempt `playwright-attempt-007`.

## How this was made

The test, its helper, its settings, the check program, the records and this document were written by an AI
assistant (Claude) at the participant's direction. The participant made two decisions: the test runs against
the corrected made-up checkout from the earlier quest, for its rules on discount, tax and charge; and each
piece of evidence is a small picture with a written record beside it.

**The application is made up and ran on this computer only**, on 127.0.0.1. It holds invented products and
prices. It has no sign-in, no account, no token, no cookie and no customer, and it takes no money. Nothing
else was contacted. The application file is the one approved earlier and was not changed.

Words used below: **recorded** means the saved log shows it. **observed** means an independent reader's reply
shows it. **not assessed** means nobody checked it.

## The short version

- The test has four business rules and one test for each. Every assertion in it is marked NAVIGATION,
  PRECONDITION or PROOF. Evidence is captured at the four PROOF points and nowhere else.
- A passing run leaves one record and one picture for each rule: eight files, against the scenario's forty.
- With a rule broken, that rule's own assertion fails, its record says DID NOT HOLD with the value that was
  there, and its picture differs.
- **What the evidence shows is narrower than "the rule holds".** It shows each rule's figure, for one basket, on
  a page. Two readers given only the evidence folder both said so. Each record now says so about itself.
- One of my marks was wrong, and eleven of my check's checks were weaker than their labels. A reader found both.

## Approach

A small helper gives the test three kinds of step.

| Step | What it is | Captures |
|---|---|---|
| `navigation()` | getting to where a rule can be checked. It may hold an assertion that the test arrived | nothing |
| `precondition()` | an assertion that the figures a rule starts from are the ones its arithmetic assumes | nothing |
| `proves()` | the assertion that a business rule held | a record and a picture |

`proves()` makes the assertion itself. Then, pass or fail, it reads the value from the page, takes a picture of
only the lines the rule is about, writes the record, attaches both to the test's report, and fails the test if
the assertion failed. The value the record calls "asserted" is the same variable the assertion used, so it is
not typed twice.

Playwright's own trace, screenshot and video are switched off. Nothing is captured unless the test asks.

## Which assertion I considered proof, and which only navigation

This is what the quest asks the proof to explain. The test has thirteen assertions.

**Navigation: two.** They show the test got somewhere. Passing them proves no rule.

- The heading "Checkout" is visible. The page opened.
- The heading "Order placed" is visible. This is the one most easily mistaken for proof. It shows an order went
  through. It says nothing of what was charged: a confirmation with the wrong amount on it has this heading too.

**Precondition: seven.** They check a figure that a rule's arithmetic starts from. "The discount is 4.00" means
nothing unless the subtotal was 40.00. Each is some other rule's business, proved in that rule's own test, or
is no rule at all (the subtotal). When one fails, the test stops before its rule is checked.

**Proof: four.** One for each rule (criterion 3).

| Rule | The assertion that is its proof | Why this one |
|---|---|---|
| R1 The discount is 10% of the subtotal | the discount line reads `-£4.00` | 10% of the 40.00 subtotal |
| R2 Tax is 20% of the goods after the discount | the tax line reads `£7.20` | 20% of 36.00. On the 40.00 before the discount it would be 8.00, so this figure tells the two apart |
| R3 The total is the subtotal, less the discount, plus the tax | the total line reads `£43.20` | this is where the discount is seen to be taken off, and not only printed |
| R4 The confirmation says the customer was charged the total they were shown | the confirmation's amount is the total the test read from the checkout page before pressing "Buy now" | it compares two pages, which is the rule |

**The mark I got wrong.** R4's proof first asserted the typed text £43.20. The "total they were shown" half of
the rule sat in a precondition, which captures nothing. A reader pointed out that with the tax left out of the
total, R4 as worded holds, 36.00 shown and 36.00 confirmed, and my test failed anyway. The proof now compares
the confirmation with the total actually read from the page.

## What the evidence shows, and what it does not (criteria 4 and 7)

Each record holds: the rule in words; the value asserted; the value read from the page at that moment; the
figures that value follows from, read at the same moment; the arithmetic; where in the test it was asserted;
the picture's checksum; and the text inside the picture.

Each record also holds a line beginning "What this does not show". Those lines were added after reading:

- **R1** does not show the discount was taken off what the customer pays. Its line reads the same when the
  discount is printed and then ignored.
- **R2** does not show the rate for any other basket.
- **R3** shows three figures add up. It does not show any of the three is right.
- **R4** does not show that money was taken. The application takes none. It shows what one page says against
  what another said.

The scenario's complaint was that nobody could point to a capture showing the discount was applied. My first
answer would have been R1, the discount line, and **it would have been the wrong capture**. The contrast run
shows it: with the discount printed and not taken off, R1's record and picture are byte for byte the same as
in a passing run. R3 is the capture that shows the discount applied.

## The criteria, one by one

| # | Criterion | Status | Where |
|---|---|---|---|
| 1 | Each business rule has one captured piece of evidence at its validation point | recorded | `logs/contrast-run.txt` part 1: exactly one record and one picture for each of four rules, and nothing else captured. The helper fails a test that captures the same rule twice |
| 2 | Navigation steps do not produce evidence by default | recorded | Part 1: after the run Playwright's own folder holds only its copies of the eight attached files: no trace, no video, no screenshot. The folder of evidence holds nothing but the four pairs. The run's own list also says "Nothing captured" at nine steps, and that is the helper's word, labelled as such |
| 3 | The test marks which assertions prove a business rule | recorded, observed | Part 2 lists all thirteen with their marks. Every `expect()` is marked NAVIGATION or PRECONDITION, and every `proves()` has "PROOF of R" and its number directly above. Whether the marks are right is a judgement. A reader agreed with twelve and corrected one |
| 4 | Evidence shows the specific value or state the rule is about | recorded, observed | Part 1: each record gives the value asserted and the same value read from the page, and its picture's text includes it. Two readers opened the pictures and read the same values in them |
| 5 | Breaking the rule changes the evidence or fails the assertion | recorded, with limits | Part 3: ten broken applications. For each rule at least one makes that rule's own assertion fail with its record and picture changed. **Three limits are recorded as limits:** see "What looks the same when a rule is broken" |
| 6 | No evidence contains personal data or a credential | recorded, observed. met mostly by there being nothing to leak | Part 4: a scan of the seven text files finds nothing, the pictures hold no chunk but the image, and each of the scan's ten patterns is shown to fire on a planted line. Two readers found nothing. The application has no sign-in and no customer |
| 7 | A reader can tell what was verified from the evidence alone | observed, with a reservation | Two readers were given the folder and nothing else. Each stated the rule, the exact value and what it followed from for all four. **The reservation is theirs:** it shows "four strings appeared on screen rather than that the rules hold" |

## What looks the same when a rule is broken

Part 3 of the log lists every capture that was identical to the passing run's while something was broken. Most
are right to be identical: the thing broken was another rule's, and this rule did hold. Three are limits.

- **The discount shown and not taken off.** R1's capture is unchanged, in both ways this was tried. R2 or R3
  fails instead.
- **A rate that suits the one basket.** With the tax at 20.01%, or the discount at 10.01%, all four captures are
  unchanged and every test passes. The checkout has one basket.
- **A wrong starting figure.** With the subtotal wrong, R1, R2 and R3 stop at their preconditions and leave no
  record at all, though 10% of the wrong subtotal may still have been taken off correctly.

Not tried: an element missing from the page, a wrong sign or format of amount, and any basket but the one.

## Artifacts

Start created the folder `playwright-attempt-007`, and the work is there. The quest text names `attempt-001`,
so copies of the items it names are in `participant/evidence/playwright-success-evidence/attempt-001/`, with a
note saying where the originals are.

| Required item | File |
|---|---|
| The annotated test | `participant/tests/playwright/meaningful-evidence.spec.ts` |
| The evidence of a passing run, and the run's output | `validated/`: `R1-discount` to `R4-charge`, each `.md` and `.png`; `run-output.txt`; `runner-output.txt`; `README.md` |
| The contrast run and the scan | `logs/contrast-run.txt`, 55 checks |
| This narrative | `PROOF.md` |

Also: `logs/independent-read.txt`. And in `participant/tests/playwright/`: `support/proof.ts`, the helper;
`support/proof-global-setup.ts`, which empties the capture folder before a run; `success.config.ts`, the
settings; `tools/success-evidence-check.ts`, the check.

## Stretch goals

- **Attach the evidence to the report automatically:** done. `proves()` attaches the record and the picture to
  the test's report. Part 1 checks that Playwright's report lists exactly those two for each test.
- **Record the exact value asserted next to each capture:** done. It is in the record beside each picture, and
  is the value the assertion itself was given.

## Reproduce

From `participant/tests/playwright`, with Node 22.18 or later and the Playwright browser installed:

    node tools/success-evidence-check.ts

It takes under a minute. It starts the made-up checkout on 127.0.0.1 and stops it. It empties `validated/`
and fills it again, so the times in the records will be new.

## What was tested

| What | Result |
|---|---|
| The passing run | 4 tests pass. 8 captures, one record and one picture for each rule |
| Each rule broken in a way that rule's assertion sees | R1: 1 way. R2: 2. R3: 2. R4: 1. Each fails at PROOF with changed evidence |
| A dead button | R4 fails at NAVIGATION and leaves no record. The other three hold |
| A wrong subtotal | R1 to R3 fail at PRECONDITION and leave no record |
| Two rates that suit the one basket | nothing changes. Recorded as a limit |
| The scan | nothing found in 7 text files. 11 planted lines, each reported |
| That the check can fail | 7 spoiled records, each reported |

## What the readers found, and faults found while building

Three AI readers, no person. Full account in `logs/independent-read.txt`.

- **Reader 1, the folder alone:** told what was verified for each rule, "partly". Pictures matched their records.
  It would not accept "HELD" beside a rule as showing the rule, called R4 "the weakest overall", and noted that
  nothing in the folder came from the test runner.
- **Reader 2, the test and the check:** found the wrong mark on R4. Found a comment in my test that the log
  contradicted. Found eleven checks that claimed more than they tested, the plainest being one that compared a
  table I had typed with itself. Found four weak points in the helper, one of which let a failed picture hide
  the rule's own failure.
- **Reader 3, the final folder alone:** YES for the value of every rule, PARTLY for R1's, R2's and R4's rule.
  "The records are mostly careful." It listed three sentences that still say more than the folder supports and
  some gaps the "does not show" lines leave out.

**Nothing in the test, the helper or the evidence was changed after reader 3**, so its findings stand. The check
was run once more afterwards, for the reason given just below, and that writes the folder again. The four
pictures are byte for byte the ones reader 3 saw. The seven text files differ only in the time of the run and
the milliseconds each test took.

Faults I found myself:

- The first pictures were as wide as the page, and let the top of the next line show at the bottom edge. The
  record's "text inside the picture" would then have been untrue. The picture is now cut to the text itself.
- My stricter scan reported a key in my own README. It was a long file path. The pattern now wants a digit.
- The project's own secret scanner reported a credential in my check program and in its log. It was the made-up
  one I plant to show my scan can find one. The scanner was right to report it and was not touched. The planted
  lines are now put together when the check runs, and the log describes each one without printing it.

## What could not be done, and limitations

- **One basket.** Every figure is for 40.00 of goods and one discount code. The expected values are typed, not
  worked out from the page.
- **"Charged" is a label on a page.** No payment exists to check.
- **The evidence is the test's own account** of one passing run. The checksums show the folder agrees with
  itself. `runner-output.txt` is a summary this program wrote from Playwright's report, and the report itself
  is not kept.
- **A folder cannot show what was not put in it.** That nothing else was captured rests on Playwright's
  settings and on its output folder after the run.
- **The pictures are not read by the check.** Two readers looked at them.
- **The scan is a list of patterns.** It would miss a name with no title, an address, and anything encoded.
- **Three sentences in the folder still say a little too much**, by the last reader's account, and are left as
  it read them.
- **No person read any of it.**

## Reflection

*Which of your captures would still look the same if the rule were broken?*

The one I would have pointed to first.

The scenario is about a discount. So the capture that matters is obviously the discount line, minus four
pounds, right there on the page. I built that as R1 and was satisfied with it.

Then I ran the checkout with the discount printed on the page and not taken off the price. R1's picture came
out identical. Same bytes. The record said HELD. Everything about that piece of evidence was true and it
showed nothing about whether the customer got their discount. The capture that changed was the total, three
lines further down, which I had thought of as a different rule.

So the honest answer has three parts. R1 looks the same whenever the discount is shown and ignored. All four
look the same if the rate is off by a hundredth of a percent, because there is only one basket. And when the
starting figure is wrong there is no capture at all, which is its own kind of looking the same: silence.

What I did not expect was how much of this I could only see from outside. I gave one reader just the folder,
no test, no explanation. It read every value correctly and then said, more or less, that all I had shown was
four numbers appearing on a screen. I wanted to argue and could not. That is what a screenshot is. The record
beside it can say what the number was supposed to mean, and after that reader it also says what the number
does not mean, which I think is the more useful half.

Forty screenshots of pages loading prove nothing. Four screenshots of the right lines prove a little more than
nothing, and I now know roughly how much.

## Sensitive values

- No login, token, credential or session cookie was used or exists in the application.
- No trace or video was recorded. The only pictures are the four in `validated/`, each of a few lines of an
  order summary: labels and amounts of money.
- The application, its products, prices and discount code are invented. It listens on 127.0.0.1 only.
- Paths in the logs are shown from the repository's top folder.
