# PROOF: Make Tests Order-Neutral and Responsible for Their Own Data

Quest `playwright-data-isolation`, attempt `playwright-attempt-002`.

## How this was made

The tests, the made-up application they run against, the check script and this document were written by an AI
assistant (Claude) at the participant's direction. The participant chose the design in two decisions: test a
small demo application written for this quest; and give every record a random name and clean up by the
record's own id. The participant installed Playwright on their computer. The assistant ran the tests and the
check there. Nothing outside this computer was contacted by them, and no login or token is involved.

Words used below: **recorded** means a saved log shows it. **planted** means a fault was put in on purpose and
the check noticed it. **not assessed** means nobody checked it.

## Approach

- **The application under test** is a made-up customer directory, `participant/tests/playwright/demo-app/server.mjs`.
  It lists customers, adds one, upgrades one and removes one. It refuses a second customer with a name already
  in use. It has no "reset" and no "delete all". It starts with four customers, which stand for data that was
  there before any test.
- **`coupled.spec.ts`** is the fault, on purpose: one test adds "Test User", the next upgrades "Test User"
  without creating it.
- **`isolated.spec.ts`** is the same behaviour tested properly: five tests, each making its own customers and
  removing exactly those.
- **`tools/data-isolation-check.ts`** runs both, in several orders and in parallel, and compares the
  application's data before and after. It wrote the two logs.

## How names are made unique (criterion 2)

Every customer a test makes is called `<label> <run marker>-<random part>`, for example
`Ada fwd-3f9a1c2e-0b7e4d2a-6c1f-4a53-9e0b-5d2c8f7a1b34`.

- **The random part does the work.** It is a fresh UUID, drawn for every single customer, with 122 random
  bits. It does not depend on the time, a counter, the test's title or which worker runs the test. Each of
  those can repeat: two testers start in the same second, two runs both count from one.
- **The run marker makes nothing unique.** It is the same for every customer of one run. It is there so that a
  leftover can be traced to the run that left it.
- **The label** ("Ada") is only for a person reading the page.

The scenario's fault was planted to check this: every test was made to use a fixed name. Running forwards,
reversed, shuffled and in parallel all still passed, because each test cleaned up before the next used the
name. **Two runs at once failed.** That is exactly the scenario: fine alone and in the nightly run, broken when
two testers run together (`logs/planted-faults.txt`, fault A).

## How cleanup behaves when a test fails halfway (criterion 3)

When the application creates a customer it hands back an id. The test's `own` helper writes that id down at
once. After the test, it removes exactly those ids.

- **It removes by id only.** It never looks for customers by name or by pattern. So it cannot remove a
  customer it did not make. One of the customers that was there before is called "Test Userson" on purpose: a
  cleanup that deleted "everything starting with Test" would take it.
- **It runs whether the test passed or failed.** It is the part of a Playwright fixture after `use()`, which
  Playwright runs in both cases. It is not an "after a pass" step.
- **"Already gone" is fine.** A test whose subject is removing a customer has removed it already.
- **Any other answer fails the test.** A cleanup that did not work is never silent.

**Recorded.** One test is made to fail on purpose after it has created two customers (it only runs when asked
for). It fails at the line that says so. Afterwards the application holds no customer that was not there
before, and both of its two are gone (`logs/shuffle-run.txt` part 9, `logs/cleanup-check.txt` part 7).

**Planted.** The quest's hint was put in as a fault: cleanup only after a pass. The check failed on that same
test: two customers left behind (`logs/planted-faults.txt`, fault C).

**What cleanup cannot do.** If the whole test program is killed, for example the computer loses power, no
cleanup of any kind runs. Not assessed here. A test that runs out of time is a different case: Playwright
documents that fixture teardown still runs then. That was not tried here either.

## The criteria, one by one

| # | Criterion | Status | Where |
|---|---|---|---|
| 1 | Each test creates the data it needs | recorded | `isolated.spec.ts`: every test starts by creating its own customers. Each of the 5 passes when run entirely on its own, as the first thing against the application, in `shuffle-run.txt` parts 4 to 6 |
| 2 | Created data has a name that cannot collide with another run | recorded, planted | See above. `shuffle-run.txt` part 8: two whole runs at once, both pass. Fault A |
| 3 | A test removes only the data it created | recorded, planted | See above. `cleanup-check.txt`: 44 created, 44 removed, nothing else touched. Faults B, C and D |
| 4 | The tests pass in forward, reversed and random order | recorded | `shuffle-run.txt` parts 4, 5 and 6. The shuffle's seed is printed, so the order can be repeated |
| 5 | The tests pass when run in parallel | recorded | `shuffle-run.txt` part 7: 5 workers, all at once. Part 8: two runs at once |
| 6 | The coupled version is shown failing under reordering | recorded | `shuffle-run.txt` part 2: reversed, "upgrades Test User" fails, waiting for a button that never appears. Part 3: run twice, "adds Test User" fails the second time |
| 7 | No data present before the run is altered or removed | recorded, planted | `cleanup-check.txt`, every part: each of the 4 customers that were there is still there with the same name, plan and id. Fault D |

### Criterion 4: how the order is changed

Playwright runs the tests of a file in the order they are written, and has no shuffle. So the check script runs
the tests **one at a time, each in its own Playwright run**, in an order it chooses: as written, reversed, and
shuffled. All of those runs, and the parallel ones after them, are against **one running application with no
reset in between**. A test that left something behind, or leaned on another, would show in a later run.

### Criteria 3 and 7 are checked from outside the tests

The check script asks the application for every customer before the isolated runs, and again after each run,
and compares. It does not ask the tests whether they cleaned up. It also reads the application's own count of
customers created and removed, so that "nothing left behind" cannot be true only because nothing was made: 44
were made.

The same comparison is run after the coupled tests, and reports their leftover, "Test User"
(`cleanup-check.txt` part 8). So the check is able to say "not clean".

## Artifacts

| Required item | File |
|---|---|
| The coupled tests | `participant/tests/playwright/coupled.spec.ts`. The failure is in `logs/shuffle-run.txt` parts 2 and 3 |
| The isolated tests | `participant/tests/playwright/isolated.spec.ts` |
| The shuffle run | `logs/shuffle-run.txt`, 15 checks |
| The cleanup check | `logs/cleanup-check.txt`, 26 checks |
| The check script | `participant/tests/playwright/tools/data-isolation-check.ts` |
| This narrative | `PROOF.md` |

Also here: `logs/planted-faults.txt` (4 planted faults) and, beside the tests, `demo-app/server.mjs` (the
application), `playwright.isolation.config.ts` (this quest's settings) and `tools/planted-faults.ts`.

**Where the files are.** The quest names `attempt-001` for the two logs and this document. The app's Start
button made the attempt folder `playwright-attempt-002`, and the work is there. `attempt-001/` holds copies,
with a README that says so, so that the paths the quest names exist.

Nothing of the earlier Playwright quest was changed: its test, its settings file and its server script are as
they were approved.

## Stretch goals

- **Run the suite twice in parallel against the same environment:** done. `shuffle-run.txt` part 8: two
  separate runs started together against one application, both pass, and nothing is left afterwards.
- **Add a check that reports leftover data:** done. It is the comparison in `cleanup-check.txt`. It lists each
  leftover by name and id. It only reports. It removes nothing.

## Reproduce

From `participant/`, with Node 22.18 or later:

    npm ci && npx playwright install chromium
    cd tests/playwright
    npx playwright test -c playwright.isolation.config.ts isolated.spec.ts
    node tools/data-isolation-check.ts
    node tools/planted-faults.ts

The third line runs the isolated tests once. The fourth is the whole check, and writes the two logs again. The
fifth changes `isolated.spec.ts` while it runs and restores it. Each run draws new random names and a new
shuffle seed, so the logs differ in those and in the timings, and in nothing else.

## What was tested

| What | Result |
|---|---|
| Isolated tests | 5, passing in the order written, reversed, shuffled, in parallel, and twice at once |
| Coupled tests | 2, passing in the order written on a fresh application, and failing reversed and on a second run, as intended |
| Recorded checks | 15 and 26, all pass |
| Planted faults | 4 put into `isolated.spec.ts` one at a time. The check failed for each, on the check it should trip |

**The planted faults found three weaknesses, all in the check script and none in the tests.** The first time
they were planted, every fault made the check fail, but reading which checks failed showed:

- **A check that did not check what it said.** One line read "that test created 2 customers before it failed,
  and both are gone". It counted the two created. It never looked whether they were gone. The fault "cleanup
  only after a pass" got past that line and was caught by others. It now looks.
- **A check that could fail by bad luck.** "The shuffled order is neither the order written nor its reverse"
  failed once, because a shuffle of five lands on one of those two about one time in sixty. A seed that gives
  either is now passed over and the next is tried, and the log says so when it happens.
- **A blurred check.** "No data that existed before was removed or altered" also failed when the only problem
  was leftovers. It now fails only when one of the four earlier customers is missing or different.

They were corrected, and the four faults were planted again against the corrected check.

## What could not be done, and limitations

- **The application is a toy, and has one author with the tests.** It was written by the same assistant, to
  be easy to collide in. It keeps data in memory, handles one request at a time, and has no login. Real
  applications fail in ways it cannot: two requests truly at the same instant, data kept in a database, data
  made by one user and not visible to another.
- **A killed test program, and a test that runs out of time: not assessed.** See above.
- **Reordering is done between Playwright runs, not inside one.** Each test in an ordered run is its own
  Playwright run. The tests share nothing inside the program anyway, and the parallel run covers them running
  in one. But "any order within one run" was not shown as such.
- **One shuffle per check run.** Five tests have 120 orders. Three were run.
- **One browser, Chromium,** and Playwright 1.63.0.
- **The check script needs Node 22.18 or later,** because it is TypeScript run directly by Node.
- **The uniqueness of names rests on the random UUID.** It is as good as the computer's source of randomness.
- **Leftovers are found by comparing with the list taken before the runs,** not by searching for the run
  marker. That is the stronger test here, where the script knows what was there before. On a shared
  environment nobody has that list, and the marker would be what there is to search for.

## Reflection

*What data could a test still leak that your cleanup does not know about?*

Anything the test caused but did not create by name. My cleanup knows the ids it was handed, and nothing else.

The clearest case is in my own tests. One of them adds a customer through the page, not through the direct
interface, because adding through the page is what it is testing. The id comes back on the page a moment
later, and the test writes it down then. If the test died between the click and reading the id, the customer
would exist and nobody would know its id. It is a small gap. It is still a gap, and it is in the one test that
creates data the way a real person does.

The second is data the application makes by itself. The demo application counts how many customers were ever
created. After my runs that number is 44 and it will never go back. Nothing a test did by name, but the
application is not as it was. In a real system that is the audit log, the welcome email, the search index, the
invoice number that was used up. My check says the customer list is the same as before, and that is true, and
it is not the same as "nothing changed".

The third is changes, as against creations. None of my tests edits a customer that was there before. If one
did, upgrading Asha Verma to test the upgrade button, my cleanup would not put her back, because it only
removes what it made. The outside check would catch it. The cleanup would not know.

And the plain one: if the test program is killed, nothing runs. That is why the check that reports leftovers
is separate from the cleanup and does not trust it.

What I did not expect was where the three real faults turned up. The tests were right the first time. The
check that was supposed to prove it had a line that only counted, a line that could fail by luck, and a line
that mixed two things up. I only found out by breaking the tests on purpose and reading which lines objected.

## Sensitive values

- No login, token or session cookie is used anywhere. The application has no login.
- Every customer is invented: the four the application starts with, and the ones the tests make.
- Nothing outside this computer was contacted by the tests or the check. The application listens only on this
  computer's own address.
- The logs are Playwright's output with this computer's folder names replaced by REPO and HOME.
