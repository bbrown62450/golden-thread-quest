# Triage report: six failed tests

Written by an AI assistant (Claude) at the participant's direction, for the quest `playwright-failure-triage`.

**How these classes were reached.** Two fresh assistants, who had not been told the causes, were each given the six bundles and
`triage-rules.md` and nothing else. They classified all six separately. They gave the same class for every failure, and those
are the classes below. A third, given only each failure's error text and one screenshot, gave a first-look class, also below.
The assistant who planted the faults then wrote this report from their answers, after checking each fact they cited against
the bundle. Only after all three had answered were their classes compared with the ground truth, which is kept in another
file. What that comparison showed is in the attempt's `PROOF.md` and `logs/blind-triage.txt`, not here.

The bundles are in `participant/evidence/playwright-failure-triage/playwright-attempt-004/failures/`. Every file cited is
in the bundle of the failure it is cited for. The application is made up.

| Failure | Class | First look, from the error and one screenshot only | Next action goes to |
|---|---|---|---|
| failure-01 | data | data | the owner of the test data |
| failure-02 | product-bug | product-bug | the application's developers |
| failure-03 | test-defect | inconclusive | the owner of the test |
| failure-04 | inconclusive | inconclusive | the platform team and the application's developers, together |
| failure-05 | product-bug | product-bug | the application's developers |
| failure-06 | environment | inconclusive | the platform team |

No failure is classed as "flaky". Two of the six passed when retried, failure-02 and failure-04. Each has a class of its own
and an account of the retry.

## failure-01

- class: data
- cites: error.txt, test-source.txt, failed-requests.json, server.log, page-text.txt, attempts.json
- next_action: Correct record 4 of the seed data, where line 2 of order ord-2004 has a quantity of -3, then run the test again.
- owner: the owner of the test data
- how_often: failed both attempts, and 10 of 10 when run again

The test, order ord-2004 shows its total, expected "Order total: 34.60" and saw "Order total: unavailable" for the whole two
seconds (error.txt). Its code waits properly, and its comment shows it assumed three brackets (test-source.txt). The request
for the order's lines was answered 422, and the answer names the record and the fault: order ord-2004, line 2, quantity -3,
"seed data, record 4" (failed-requests.json). The application's log says the same: "REFUSED invalid order data" (server.log).
The page told the person plainly, "This order cannot be priced: line 2 has a quantity of -3", and showed no wrong total
(page-text.txt). So the application rejected one named piece of data, and rejecting it is correct. It failed every time
(attempts.json).

Ruled out: product-bug, because refusing a negative quantity is right and it is reported clearly. Environment, because
nothing was refused or unreachable. Test-defect, because the test's code is sound.

A second, smaller fault, not the cause: the page leaves "Customer: loading…" for good, though the summary request was
answered. That goes to the application's developers.

## failure-02

- class: product-bug
- cites: error.txt, test-source.txt, api-responses.json, page-text.txt, requests.txt, attempts.json
- next_action: Change the order page so that the total is drawn again when the lines arrive, whichever of the two requests answers first. Add a test that makes the lines answer after the summary.
- owner: the application's developers
- how_often: failed, then passed on the retry. Failed 3 of 10 when run again
- retry_explained: In the failed attempt the summary answered in 151 ms and the lines in 206 ms, so the summary came first. In the attempt that passed, the lines answered in 128 ms and the summary in 150 ms, so the lines came first. Only the order of the two answers differed.

The test, order ord-2005 shows its total, expected "Order total: 119.00" and saw "Order total: 0.00", settled, for the rest of
the two seconds (error.txt). The test waits properly and its expectation is right (test-source.txt). The application was told
the right thing: the lines request was answered 200 with twelve lines and a total of 119 (api-responses.json). And the page
contradicts itself: it shows all twelve lines, whose amounts add up to 119.00, under a total of 0.00, both when the test gave
up and after the wait (page-text.txt). The summary answered before the lines (requests.txt). The page draws the total when
the summary arrives and does not draw it again.

**It passed on the retry, and that changes nothing** (attempts.json). The retry passed because the two answers happened to
come in the other order. A user gets whichever order the network gives them, about three times in ten here. This is a race
in the application.

Ruled out: test-defect, because the page was wrong and stayed wrong, and the test waited. Environment, because every data
request was answered 200 and nothing was unreachable. Data, because nothing was rejected.

## failure-03

- class: test-defect
- cites: test-source.txt, error.txt, requests.txt, api-responses.json, page-text.txt, attempts.json
- next_action: Replace lines 46 and 47 of the test with a waiting assertion: expect the total to have the text "Order total: 37.50".
- owner: the owner of the test
- how_often: failed both attempts, and 10 of 10 when run again

The fault is in the test's own code. Lines 46 and 47 read the total's text once and compare it straight away, with no wait,
where the other five tests use an assertion that waits (test-source.txt). So it read "Order total: loading…" (error.txt), and
the whole attempt lasted 154 ms (attempts.json). The summary request, which takes about 150 ms in every bundle, is marked
"answered after the test gave up" (requests.txt). The application was told the right thing, a total of 37.5
(api-responses.json), and 357 ms later the page showed "Order total: 37.50" and the customer's name (page-text.txt).

Ruled out: product-bug, because the page was right about 150 ms after it opened, which is not late for a person, and
nothing was slow by this application's own measure. Environment and data, because nothing failed or was rejected.

## failure-04

- class: inconclusive
- cites: error.txt, test-source.txt, requests.txt, server.log, page-text.txt, attempts.json
- still_possible: product-bug (the application's own request handling stalled), environment (the machine, or something the application depends on, stalled)
- would_settle: What the server was doing in those three seconds: the time each step of the two request handlers took, the time of its call to the pricing service, and the machine's load and any pause of the process. None of that is in the bundle.
- next_action: Add step-by-step timing to the server's log for the two order requests, and record the machine's load in the bundle. Run the test repeatedly until a slow answer comes again.
- owner: the platform team and the application's developers, together
- how_often: failed, then passed on the retry. Failed 0 of 10 when run again
- retry_explained: In the failed attempt both data requests took about 3.2 seconds, 3199 ms and 3211 ms, and were answered after the test had given up. In the attempt that passed they took 152 ms and 11 ms. Nothing else differed.

The test, order ord-2006 shows its total, waited the full two seconds and the total was still "Order total: loading…"
(error.txt). Its code is sound and waits properly (test-source.txt). Both data requests took about 3.2 seconds and were
answered after the test gave up (requests.txt). The application's log records the same two durations, as ordinary 200
answers, with no reason (server.log). When run again it did not happen (attempts.json).

So what failed the test is a slow answer with no stated cause. That meets no class's list. It is not shown to be the
environment: nothing names a machine or a dependency. It is not shown to be the application: nothing shows where in the
application the time went. Both requests finished 12 ms apart, which looks like one stall of the whole server, and that fits
either story.

**A second fault is in this bundle, and it is certain, and it is not why the test failed.** When the answers did arrive,
the page showed "Order total: 0.00" above lines of 16.00 and 18.00 (page-text.txt, the second moment). That is the race of
failure-02. It happened after the test had already given up. It goes to the application's developers with failure-02.
It does not make this failure a product-bug: the rules class the fault that made the test fail.

Ruled out: test-defect, because the test's code shows no fault. Data, because nothing was rejected.

## failure-05

- class: product-bug
- cites: error.txt, test-source.txt, api-responses.json, page-text.txt, server.log, attempts.json
- next_action: Correct how the server totals an order's lines: for ord-2001 it leaves the second line, 20.00, out of the sum. Find out whether it drops the last line of every order or only some.
- owner: the application's developers
- how_often: failed both attempts, and 10 of 10 when run again

The test, order ord-2001 shows its total, expected "Order total: 120.00" and saw "Order total: 100.00", settled (error.txt).
The expectation is right, eight widgets at 12.50 and one toolkit at 20.00, and the test waits (test-source.txt). The
server's own answer contradicts itself: two lines, of 100 and 20, and a total of 100 (api-responses.json). The page shows
exactly that, faithfully (page-text.txt). The application's log calls it a success, "priced 2 lines", with no error
(server.log), which is the application being wrong about itself. It failed every time (attempts.json).

Ruled out: test-defect, because the expected value agrees with the lines the application itself returned. Data, because
nothing was rejected and both lines are valid. Environment, because nothing failed. The race of failure-02, because here
the lines answered first and the total shown is the server's 100, not 0.

## failure-06

- class: environment
- cites: error.txt, test-source.txt, server.log, failed-requests.json, page-text.txt, attempts.json
- next_action: Find out why nothing is listening on 127.0.0.1:4798, where the pricing service should be, restore it, and run the test again.
- owner: the platform team
- how_often: failed both attempts, and 10 of 10 when run again

The test, order ord-2003 shows its total, expected "Order total: 67.00" and saw "Order total: unavailable" for the whole two
seconds (error.txt). Its code is sound (test-source.txt). The application's log names something outside its own code that
failed: "ERROR pricing service unreachable at 127.0.0.1:4798: connect ECONNREFUSED" (server.log). The request for the lines
was answered 503, "pricing_unavailable", with the same refused connection in its detail (failed-requests.json). And the
application handled it as such: the page says "Prices are unavailable right now. Try again later." and shows no wrong total
(page-text.txt). The dependency was down throughout: it failed every time (attempts.json).

Ruled out: product-bug, because a dependency was refusing connections and the application reported that sensibly. Data,
because no record was rejected. Test-defect, because the test is right.

The same smaller fault as in failure-01: "Customer: loading…" stays for good.
