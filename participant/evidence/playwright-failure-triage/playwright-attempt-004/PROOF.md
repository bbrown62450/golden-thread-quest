# PROOF: Classify Failures as Bug, Test Defect, Environment, Data, or Inconclusive

Quest `playwright-failure-triage`, attempt `playwright-attempt-004`.

## How this was made

The rules, the made-up application and its planted faults, the tests, the evidence fixture, the check scripts,
the triage report and this document were written by an AI assistant (Claude) at the participant's direction.
The participant made three decisions: the failures are classified by blind classifiers and not by the one who
planted them; the failure that cannot be settled is one that two causes explain equally, not one with evidence
deleted; and a bundle holds every attempt, so that a pass on retry can be seen and explained.

Everything ran on the participant's computer against an application on 127.0.0.1. Every sign-in is made up
and redacted. Nothing outside that computer was contacted.

Words used below: **recorded** means a saved log shows it. **tested** means a planted fault showed the check
notices when it is broken. **not assessed** means nobody checked it.

## Approach, and the order things were done in

The order matters more than the code here, because the one who plants a fault knows its answer.
`logs/sequence.txt` records each step with the time and a checksum of the files as they then stood.

1. **The rules were written first**, before any failure existed: `participant/context/playwright/triage-rules.md`.
   For each class they give the signs, and separately what the evidence must show before the class may be given.
2. **The ground truth was written second**, before any bundle existed: `ground-truth.md`. It names the cause
   planted for each failure, and the mistakes a classifier was expected to make.
3. **The six failures were produced** against a made-up order desk, each leaving a bundle named `failure-01`
   to `failure-06` in an order that says nothing.
4. **Three fresh assistants classified them**, knowing none of the above. Two got the full bundles and the
   rules. One got only each failure's error text and one screenshot.
5. **Only after all three had answered** were their classes compared with the ground truth.
6. The triage report was written from the two full classifications, which agreed on all six.

The assistant who planted the faults did not classify anything. It checked the facts the classifiers cited
against the bundles, and wrote their classification up.

## The six failures

| Bundle | What was planted | True class | Classified as | How often it failed |
|---|---|---|---|---|
| `failure-01` | A line in the test data with a quantity of minus three. The application refuses it | data | data | 10 of 10 |
| `failure-02` | A race in the page: the total is drawn before the lines arrive, and not redrawn | product-bug | product-bug | failed, **passed on retry**. 3 of 10 |
| `failure-03` | The test reads a value once, without waiting | test-defect | test-defect | 10 of 10 |
| `failure-04` | The server process frozen for 3 seconds, from outside the application's code | environment | **inconclusive** | failed, passed on retry. 0 of 10 |
| `failure-05` | The server leaves a line out of an order's total | product-bug | product-bug | 10 of 10 |
| `failure-06` | The pricing service the application depends on is stopped | environment | environment | 10 of 10 |

## The failure first classified wrongly

The quest asks for one. **No full-bundle classification was wrong**: both blind classifiers gave the class the
ground truth calls correct, for all six. So there is no neat story of a wrong answer put right, and none is
made up here. What was wrong is this, and it is all about `failure-04`.

**The first-look reader's guess was wrong (criteria 1 and 4).** Given only the error text and one screenshot of
`failure-04`, it put down inconclusive, which is right. Asked what it would bet if forced, it said product-bug,
at about 40%. The true cause is environment. With two files, a forced answer was the wrong class. With fourteen,
two classifiers still could not tell, and said so. For this failure more evidence did not produce an answer. It
only made the reason for not having one clearer.

**The assistant who planted it was wrong about its own bundle (criterion 7).** The ground truth, written
first, expected `failure-04` to show one thing: a slow answer with no stated cause. It shows two. When the
frozen server recovered, its two answers arrived in the order that sets off the race of `failure-02`, and the
page ended on "Order total: 0.00" above lines adding up to 34.00. So the bundle holds a certain product bug
that nobody planned. Both classifiers found it. Both said it happened after the test had given up and was not
why the test failed. Both also said a reader could defend product-bug.

That is a real weakness in criterion 7 for this one failure. The class is inconclusive only if the reader
separates "what made the test fail" from "what else is wrong in this bundle". The rules said so in one
sentence, and both classifiers reported that it was not enough. A paragraph was added to the rules afterwards,
and `logs/sequence.txt` records that it was added after the classification and because of it.

**The mistakes predicted in advance did not happen.** The ground truth listed four: `failure-03` as a product
bug, `failure-02` as a test defect or as flaky, `failure-04` as environment, `failure-01` as a product bug.
Nobody made any of them. So the assistant was also wrong about where a classifier would go wrong.

## The criteria, one by one

| # | Criterion | Status | Where |
|---|---|---|---|
| 1 | Each failure has exactly one of the five classes | recorded, tested | `logs/triage-check.txt` part 2. Part 3: two classes, no class, and "flaky" are each reported. Planted faults A, B, O |
| 2 | Each classification cites a file in its evidence bundle | recorded, tested | Part 2: every cited file is in that failure's own bundle, and the written reason names each file it cites. Part 3: no citation, a file not in the bundle, and a file cited and never used are each reported. Planted faults C, D, E |
| 3 | A product bug is not classified as flaky because it passed on retry | recorded, tested | `triage-report.md`, failure-02: product-bug, with what differed between the attempts. `logs/blind-triage.txt`: both classifiers. Part 3 of the check. Planted faults A, F, G |
| 4 | Inconclusive is used where the evidence cannot settle it, with what would settle it | recorded, tested | `triage-report.md`, failure-04: the two classes still possible, and the evidence that would decide. Planted faults H, I |
| 5 | Each classification states the next action and who takes it | recorded, tested | `triage-report.md`: every entry. The check requires the role the rules give that class. Planted faults J, K, L |
| 6 | The rules say what evidence is needed for each class | recorded | `triage-rules.md` section 2: a list headed "The evidence must show" for each of the four classes with a cause, and the conditions for inconclusive |
| 7 | A reviewer can reach the same class for each failure from the bundle | recorded for two AI classifiers. **Not assessed for a person.** Weak for failure-04 | `logs/blind-triage.txt`: two classifiers, separately, the same class for 6 of 6. See "The failure first classified wrongly" |

## Artifacts

| Required item | File |
|---|---|
| The ground truth | `participant/context/playwright/ground-truth.md` |
| The failure set | `failures/failure-01` to `failures/failure-06`, 14 files each |
| The triage rules | `participant/context/playwright/triage-rules.md` |
| The triage report | `participant/context/playwright/triage-report.md` |
| The check's record | `logs/triage-check.txt`, 49 checks |
| The check script | `participant/tests/playwright/tools/failure-triage-check.ts` |
| This narrative | `PROOF.md` |

Also here: `logs/sequence.txt` (the order of the steps, with checksums), `logs/make-failures.txt` (what was
arranged for each failure), `logs/blind-triage.txt` (what the three classifiers said) and
`logs/planted-faults.txt` (16 faults). The other code is under `participant/tests/playwright/`:
`triage.spec.ts`, `triage.config.ts`, `support/triage-evidence.ts`, `demo-app/triage-server.mjs` and
`tools/failure-triage-planted-faults.ts`.

The fixture is a copy of the one approved in the last Playwright quest, which is left as it was. The copy adds
what triage needs: every attempt of a test in one bundle, the answers to the page's data requests, the test's
own source, and the page's text when the test gave up and again a little later.

## Stretch goals

- **How often a classification changes after more evidence:** done, once. From the error and one screenshot
  to the full bundle, 2 of 6 changed, both from inconclusive to a class. None changed from one class to
  another. That is six failures and one reader, so it is an observation and not a rate.
- **Track class counts across several runs:** not done. The check prints the counts for this one triage:
  product-bug 2, test-defect 1, environment 1, data 1, inconclusive 1. Nothing keeps them from run to run.

## Reproduce

From `participant/tests/playwright`, with Node 22.18 or later and Playwright installed as for the earlier
Playwright quests:

    node tools/failure-triage-check.ts
    node tools/failure-triage-planted-faults.ts

The first reads the bundles and the report and runs no test. The second changes the check script while it
runs and restores it. `node tools/failure-triage-check.ts --make-failures` produces six **new** bundles in
place of the handed-in ones. Their times would differ, and `failure-02` depends on chance, so the report's
figures would no longer fit. The blind classification cannot be reproduced by a script.

## What was tested

| What | Result |
|---|---|
| The check of the report | 49 checks, all pass. They include 16 ways of breaking the report, each reported |
| Planted faults | 16 put into the check script, one at a time. Each was noticed by the case it is about (`logs/planted-faults.txt`) |
| Blind classifiers | 2 with the full bundles: the same class for 6 of 6. 1 with two files each: 3 classed, 3 inconclusive |
| The bundles | Each scanned for cookies, tokens, passwords and this computer's names: none found |

Faults found while building:

- **Two faults in the application that nobody planted.** The race firing in `failure-04`, above. And the page
  leaving "Customer: loading…" for good whenever the lines fail, in `failure-01` and `failure-06`. The
  classifiers found both and reported them as second faults.
- The first run that made the failures stopped after three, on a stale connection to the demo application.
  A retry was added and all six were made again. Nothing had been classified.
- The rules' table of bundle files was wrong about the screenshot, and was corrected before classification.
- The last quest's fixture took its screenshot only at the end. Here the page is recorded when the test gives
  up and again after waiting, because a test defect and a slow application look the same at only one moment.

## What could not be done, and limitations

- **The classifiers were AI assistants, not people**, of the same kind as the one that wrote the rules and
  planted the faults. They may share its way of reading evidence. A person triaging was not assessed.
- **The limits on what they read were not enforced.** Each said it kept them and listed what it read.
- **The classifier could compare bundles.** Six failures of one application were handed over together, and
  both readers used one to explain another. A real failure usually arrives alone.
- **The assistant knew all six answers when it wrote the rules.** The rules came first in time, and still
  came from the same head that had already designed the failures. Whether they would hold for a failure
  nobody designed is not assessed.
- **Six failures, one application, one of each kind.** Agreement on 6 of 6 says little about a real suite.
- **The planted faults were clean.** Each bundle says a good deal: the server's log names the refused
  connection, and the answer names the bad record. Real evidence is seldom so helpful.
- **`failure-04` is inconclusive only by a fine distinction.** See above.
- **"How often it failed" is ten runs.** For `failure-02`, 3 of 10. An earlier, discarded run gave 8 of 10,
  and a separate count gave 6 of 16. Ten runs do not fix a rate.
- **The check does not judge whether a class is right.** It checks that a classification is complete and
  rests on files that exist. A confident, well-cited, wrong classification passes it.
- **A retry that passed leaves only its list of requests**, not its page. Both classifiers called that thin.
- **Nothing in a bundle can explain slowness.** That is why `failure-04` could not be settled, and it is the
  first thing to add: timing of the server's steps and of its calls to other services.

## Reflection

*How would you notice that your triage was biased toward test defect?*

By counting, and by checking the easy ones. On my six failures I would not have noticed anything, because I
planted them and one was a test defect and it was called one. The bias would show only over many failures
that nobody planted.

The first thing I would watch is the share. If most red tests come back "test defect", either the tests are
bad or the triage is, and the count alone cannot say which. So I would look at what happened next. A test
defect is fixed by changing the test. If the test was changed and the failure came back, or a customer
reported the thing the test had been complaining about, that classification was wrong. A triage that leans
toward test defect leaves a trail of tests that were "fixed" and bugs that shipped anyway. That is the
scenario this quest starts from.

The second thing is what each classification rests on. My rules say a test defect needs two things: the fault
visible in the test's own code, and the application shown to be right. The lazy version cites only the error
message, or only the test, and never shows the application was right. I would pull every test-defect
classification and count how many cite something that shows what the page ended up doing. The ones that do
not are guesses that happened to be convenient.

And convenient is the word. The test is the thing the person triaging can change by themselves, today. A
product bug means going to another team. I felt that pull even writing the rules: I had to put "the test is
the easiest thing to change" in the list of traps.

What surprised me was where my own blind spot was. I expected the classifiers to call the race a test defect
because it passed on retry. They did not. The thing I got wrong was my own failure-04: I planted one cause
and the bundle came out holding two, and I had not seen it. So the honest answer is that I would not notice
my own bias by thinking about it. I would notice it the way I noticed this: by writing down what I expected
first, and letting someone who did not know my answer look at the evidence.

## Sensitive values

- No real login, token or cookie was used. The application makes a random cookie and token at sign-in, and
  each test makes a random password. They are redacted from every bundle before it is saved.
- Each handed-in bundle was scanned, inside its trace as well: no cookie, token or password, and none of this
  computer's names. The screenshots are pictures and were not searched. There are 12, of which 8 differ.
  The assistant looked at 2 of them: each shows an order page of the made-up application and nothing else. For
  the others, `page-text.txt` holds the text that was on the page at the same moment, and that text was scanned.
- The customers and orders in the application are invented.
- The classifiers were given copies of the bundles in a scratch folder. Nothing was sent anywhere.
