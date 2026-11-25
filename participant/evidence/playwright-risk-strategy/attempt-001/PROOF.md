# PROOF: Turn Requirements and Risk into a Layered Test Strategy

Quest `playwright-risk-strategy`, attempt `playwright-attempt-008`.

## How this was made

The requirements, the strategy, the check and this document were written by an AI assistant (Claude) at the
participant's direction. The participant made these decisions:

- **The feature is the checkout of the made-up demo shop** already in this repository.
- **Untested risks are accepted by the participant, by role**, as product owner of that shop. Each was put to them
  separately, in conversation, and recorded only after they said yes.
- **Four acceptances**, each given on 2026-11-25: R-13, R-15, R-19 and R-11. R-19 was asked twice, because its score
  changed after the first yes.

**Everything is made up.** The shop, its products, its prices, its code and its tax rule are invented. No rule in the
requirements is any real company's.

**This quest touches no application.** The check reads two files and writes a log. Nothing was started, and nothing
was contacted.

**The strategy is a plan. No test in it exists.**

Words used below: **recorded** means the saved log shows it. **observed** means an independent reader's reply shows
it. **not assessed** means nobody checked it.

## The short version

- 12 requirements, 19 risks. Each risk has a likelihood and an impact from a stated scale, a score, one layer and a
  reason. 8 are for unit tests, 3 for API tests, 4 for browser tests, none for a person, and 4 are left untested.
- **11 of the 15 planned tests need no browser.** The scenario's team tested everything through the page.
- **10 of the 15 cannot be written yet.** The demo's sums cannot be called directly, it keeps no orders and it takes
  no code. Each risk says what must be built first.
- **The ranked table can be rebuilt from the levels.** Two readers did it by hand and matched it row for row, and the
  check does it on every run.
- **The levels cannot be wholly rebuilt from the scales.** Each reader, from the clauses alone, put some risks at
  another level. The scales were tightened twice. The last tightening has not been tried by anyone.
- **Both versions that were read were wrong in ways the check did not see.** Both were corrected. Nobody has read the
  handed-in version.

## Approach

**Start from what could go wrong, not from what can be clicked.** Each requirement was read for the ways it could
break. Each way is a risk.

**Two scales, with lettered clauses.** A risk does not just say "likelihood 3". It says "3 (L3a)" and gives its own
ground. The clause is what another person would check the level against.

**One rule for the layer: the lowest at which the thing that could break can be seen.** A sum can be seen in a
function. Whether two answers agree can be seen at the server. What a press does can be seen only in a browser.

**Say what is not there.** Each risk has a "Needs first" line. The strategy lists the risks left untested, the parts
of requirements no test reaches, and what no requirement asks for.

**A check that reads the finished files.** It works the ranking out again from the risk blocks and compares it with
the table, and checks each of the seven criteria as far as a program can. What it cannot check is written at its top.

## One risk moved to a lower layer

**R-03: tax is worked out on the subtotal before the discount.** It is ranked second, with a score of 9, and it has
happened in this shop: a redesign of the demo did exactly this, and the owner ruled it a bug.

Earlier quests in this repository caught it **through the page**, with Playwright: a browser and a running server, to
test one multiplication. The strategy moves it to a **unit** test: call the function with a discounted basket and
compare the tax with 20% of the goods after discount.

Why, by criterion 4: the rule is one line of arithmetic, and the fault is which of two numbers that line uses. Nothing
about a page can make it right or wrong. At the unit layer a second case costs a millisecond, so the test can also
show it is testing the order of the two steps. By criterion 3 it has that one layer and no other.

It is not free. The sums have to be moved into a function that can be called first, and the block says so.

Two more were moved down after a reader's finding. The narrow-screen check, R-14, and the keyboard check, R-18, were
first given to a person. Both are facts a browser can see, so both are now browser tests.

## One risk accepted without testing

**R-15: the rate of tax changes in law, and the shop still charges 20%.** Likelihood 1, impact 3, score 3, on a must
requirement.

It is left untested because **no test can catch it**. A test compares the shop with the requirement, and the
requirement says 20%. If the law changes, the requirement is what is wrong, and every test still passes. Writing one
would give a false sense that it is watched.

By criterion 6 it is listed in section 5 with that reason, with what is done instead, and with who accepted it: the
participant, as product owner, on 2026-11-25. What is done instead is that the owner checks the rate before each
release. No record of that check is kept, and the strategy says that is a weakness.

The other three accepted: R-19, the money a payment provider takes, because the shop has none. It scores 9, the
highest score left untested. R-11, what a screen reader reads, because there is no person, no screen reader and no
checklist. R-13, a slow page, because the requirement's reference connection is not defined.

## The criteria, one by one

| # | Criterion | Status | Where |
|---|---|---|---|
| 1 | Every requirement is covered by the strategy or listed as untested | **recorded, observed with reservations** | Section 6 of the strategy. The check finds each of the 12 named by a risk. Both readers found clauses inside requirements that no test reached and that were not listed. Those are now listed in section 5. Not read since |
| 2 | Each risk states likelihood and impact on a stated scale | **recorded, observed** | Section 1 and each block. The check compares each level with its clause |
| 3 | Each risk is assigned one test layer | **recorded, observed** | Each block has one layer line. Four risks have the layer "none": they are untested, and are in section 5 |
| 4 | Each layer choice gives a reason, not only a label | **recorded for length, observed for content** | The check counts words: the shortest reason is 30. Whether a reason is good is a reader's judgement. Reader 3 found no reason that was a label or circular, and two that were false. Both were rewritten |
| 5 | Risks that need a browser are separated from those that do not | **recorded, observed** | Section 4: 4 need one, 15 do not. The four untested risks are in the second group only because nothing is run for them, and the section says so |
| 6 | Untested risks are listed with the reason and who accepted them | **recorded** | Section 5. Reader 3 found one risk untested in practice with no acceptance. It is now listed and accepted. Not read since |
| 7 | Another person could rebuild the ranking from the stated scales | **recorded and observed for the ranking. Not shown for the levels** | From the levels to the table: two readers and the check. From the clauses to the levels: each reader differed on some, and the last wording is untried |

## Where the important artifacts are

Required by the quest:

| File | What it is |
|---|---|
| `participant/context/playwright/requirements.md` | 12 requirements: 7 must, 3 should, 2 could |
| `participant/context/playwright/strategy.md` | The strategy |
| `participant/evidence/playwright-risk-strategy/attempt-001/logs/strategy-check.txt` | The check's output. A copy: see below |
| `participant/tests/playwright/tools/risk-strategy-check.ts` | The script that produced it |
| `participant/evidence/playwright-risk-strategy/attempt-001/PROOF.md` | A copy of this file |

The quest text names `attempt-001`. The app's Start button made `playwright-attempt-008`, which is where the work is.
`attempt-001/` holds copies, so the path the quest names exists.

Nothing in the check's output needed redacting. It holds no credential and no name, and its paths are from the
repository's top folder.

The rest, in `playwright-attempt-008/logs/`:

| File | What it is |
|---|---|
| `strategy-check.txt` | The check on the handed-in files: 97 checks |
| `strategy-check.before-acceptance.txt` | The check on the FIRST version, before any risk was accepted. It fails, on the two acceptances then missing and on nothing else |
| `independent-read.txt` | What four readers found, and what was changed |

## Stretch goals

- **The run time of each layer.** Done, as estimates, in section 7: unit under a second, API about 2 seconds, UI about
  5. One figure in it was measured, in an earlier quest, on another demo. The rest are guesses and are called guesses.
  No estimate is made of how long the tests take to write.
- **If the release were next week.** Done, as a proposal, in section 8. Its first point is that three requirements are
  not built, two of them must, and no test strategy decides whether to release without them.

## How to reproduce

From the repository's top folder, with Node 22.18 or later. Nothing to install.

    node participant/tests/playwright/tools/risk-strategy-check.ts

It rewrites `playwright-attempt-008/logs/strategy-check.txt`. It exits with 0 if every check passes.

## What was tested or validated

- **The check finds no problem** in the handed-in requirements and strategy. PART 2 of the log.
- **The check can fail.** PART 4 spoils the two documents 94 ways, one at a time and in memory, and each is reported
  with the message that only its rule produces. Two more trials change something that should not matter, and nothing
  is reported.
- **It failed when it should have.** The first version was run before any risk was accepted, and failed on exactly
  that. The same happened twice more as acceptances were reopened.
- **What the check does not show:** that a level is right, that a layer is the cheapest, that a reason is good, that
  the one named did accept, or that a risk given to a layer will ever be tested. It says so at its top.
- **No program tests the check itself.** The trials test its rules through the documents. A reader traced all 72
  trial outputs of the second version by hand against the code and found them right.

## What independent readers found

Four fresh AI assistants read the work, in two rounds. **No person read it.** They were told to read only what they
were given and to run nothing. Those limits were not enforced. The full account is in `logs/independent-read.txt`.

- **The ranking.** One reader on each version rebuilt it by hand. Both matched the table.
- **Round 1, the strategy.** The scales left choices open. Eight risks tied and were ordered by number. Six planned
  tests could not be run against the shop. Two layers were higher than needed. Parts of two must requirements were
  untested and not said to be. The strategy was rewritten.
- **Round 1, the check.** A requirement added after a blank line was never read. A risk written outside a block was
  invisible. The acceptor was a list of twelve words to refuse. Nine of its 40 checks restated another. It was
  rewritten.
- **Round 2, the strategy.** Two risks were scored below what the scales themselves gave, one of them the payment
  risk. The screen-reader check was untested in practice with no acceptance. "Several" tests that could not be written
  were eleven. All corrected.
- **Round 2, the check.** An identifier written another way, a second table, and an acceptor changed in two places
  all passed. All corrected, each with a trial.

**What changed after the last read, and was not read again.** In the strategy: four scores, one layer, the ranked
table and about thirty sentences. In the check: several new rules and 24 new trials. The check passes on the handed-in
documents. Nothing else has looked at them since.

## Remaining limitations

- **It is a plan.** No test exists, and 10 of the 15 cannot be written until more of the shop is built.
- **Likelihood and impact are judgements.** Each rests on a stated clause. Readers from the same clauses differed.
- **Fifteen of the 19 risks tie** with at least one other in score, impact and importance, and are then ordered by
  risk number, which means nothing.
- **Three levels on each scale** is coarse. It is why so many tie.
- **Four risks are untested**, one of them at the highest score in the strategy.
- **One exception to the layer rule.** R-09 is in a browser though it could be read without one today.
- **The check is written for this strategy's form.** It would report another layout as wrong.
- **The check cannot find a missing risk.** A reader found four. There may be more.
- **The acceptances are recorded, not proved.** The same conversation produced the strategy and the yes.
- **The requirements were written for this quest.** A real set would be longer and less tidy.

## Reflection

*Which risk in your strategy would you want a human to check even if a test existed?*

The rounding risk, R-05. A test for it compares the code with figures somebody worked out by hand, so a pass only
proves the code agrees with that person's reading of the rule. And the rule isn't settled. The requirement doesn't say
whether a half rounds up for a negative discount, which amounts count as "the end", or whether the amounts shown have
to add up to the total shown. Those are my calls as the owner, not the test's. So even with the test passing I'd want
a second person to work the half-penny cases on their own, and I'd want to sign the worked examples myself.

It's the same reason I accepted R-15. A test can tell me the shop matches the requirement. It can't tell me the
requirement is right.

## Sensitive values

None. The shop and its rules are made up. No real person, company, customer or system is named. There is no token,
password or key in any file here, and no path on anyone's computer.
