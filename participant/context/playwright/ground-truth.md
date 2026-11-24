# Ground truth: the real cause planted for each failure

Written by an AI assistant (Claude) at the participant's direction, for the quest `playwright-failure-triage`.

**This file was written before any failure was classified, and before any failure bundle existed.** It is kept apart from
the triage report, `triage-report.md`, and was not given to whoever classified the failures. `logs/sequence.txt` in the
attempt folder records this file's checksum at the time it was written.

Each failure is produced on purpose, against the made-up order desk in `participant/tests/playwright/demo-app/`, by
`participant/tests/playwright/tools/failure-triage-check.ts`. The bundles are named `failure-01` to `failure-06` in an
order chosen so that the name says nothing about the cause.

## What was planted

| Failure | Order | The real cause | True class | Where the fault is planted |
|---|---|---|---|---|
| `failure-01` | ord-2004 | The test data holds an order whose second line has a quantity of minus three. The application refuses to price it, and says so | `data` | the seed data of the demo application: the record for ord-2004 |
| `failure-02` | ord-2005 | A race in the application's page. It asks for the order's summary and its lines at the same time, and works out the total when the summary arrives. If the lines arrive later, the total stays at 0.00 for good. It happens about one time in three, and usually passes on a retry | `product-bug` | the page script of the demo application |
| `failure-03` | ord-2002 | The test reads the total's text once, straight after opening the page, without waiting. The application always takes about 200 ms to load the order, so the test always reads "Loading order…". The page is right a moment later | `test-defect` | the test, in `triage.spec.ts` |
| `failure-04` | ord-2006 | The whole server process was frozen for about 3 seconds while it answered. The freeze is ordered from outside the application's code, by the check script, and stands for a machine that stalls. The application's own code for this order is as fast as for any other | `environment` | outside the application: the check script tells the demo server to block once |
| `failure-05` | ord-2001 | The application adds up an order wrongly: it leaves the last line out of the total. The page shows two lines and a total equal to the first line alone | `product-bug` | the server of the demo application, in how it totals an order |
| `failure-06` | ord-2003 | The pricing service the application depends on is not running, so the connection to it is refused. The application reports that prices are unavailable | `environment` | outside the application: the pricing service is stopped for the run |

## What a correct triage should say

| Failure | Should be classified | Why |
|---|---|---|
| `failure-01` | `data` | The answer names the record and the bad value, and the application's refusal is correct |
| `failure-02` | `product-bug` | The page contradicts itself: lines on the page, and a total of 0.00. Passing on retry does not change that |
| `failure-03` | `test-defect` | The page ends up right, and the test's own code shows a read with no wait |
| `failure-04` | **`inconclusive`** | The true cause is environment. But the bundle shows only that one answer was slow. It cannot show why. A slow piece of application code would leave exactly the same evidence. Classifying it `environment` would be right by luck, not by evidence |
| `failure-05` | `product-bug` | The application's own answer disagrees with itself: the lines do not add up to the total |
| `failure-06` | `environment` | The server log and the answer name a refused connection to a dependency |

`failure-04` is the one case where the true class and the correct classification differ. That is the point of it: the
honest answer from the evidence is "cannot tell", even though there is a truth to be told.

## What a classifier might get wrong, written down before anyone tried

- `failure-03` as `product-bug`: "the page was still loading" reads like a slow application.
- `failure-02` as `test-defect` or as "flaky": it passes on retry, and the test is the easy thing to blame.
- `failure-04` as `environment`: slowness is commonly blamed on the machine.
- `failure-01` as `product-bug`: an application that holds an order with a negative quantity could be blamed for
  accepting it.

Whether any of these happened is in the triage report and in the proof, not here.
