# Diagnosis of one failed test, from its failure bundle alone

Written by an AI assistant (Claude) at the participant's direction, for the quest `playwright-failure-evidence`.

**The bundle:** `participant/evidence/playwright-failure-evidence/playwright-attempt-003/failure-bundle/`. Every claim
below names the file in that folder that supports it, with the line. `trace.zip!NAME` means the file `NAME` inside
`trace.zip`. Nothing here comes from running the test again, from the test's source, or from the application's source.

**A caution about this note.** The assistant that wrote it also built the application and its fault, so it knew the
answer. It kept to the bundle for every citation, but that is not a blind test. Two readers who knew nothing were given
the bundle and nothing else. Their findings are in `logs/blind-diagnosis.txt` and are compared with this note at the end.

## The failure, as reported

The test "FAILS ON PURPOSE: the total of order ord-1003 is shown" failed. It waited 5 seconds for the element with the
test id `total` to be visible, and no such element was found.

- `error.txt` lines 1 and 3: the test, and "Result: failed".
- `error.txt` lines 7 to 16: `expect(locator).toBeVisible() failed`, `getByTestId('total')`, `Timeout: 5000ms`,
  `element(s) not found`.
- `error.txt` line 19: raised at `failure-evidence.spec.ts:48:43`.

On its own this says "something was slow or missing". It does not say what.

## What happened

**1. The test did its steps correctly up to the wait.** It opened the sign-in page, filled in a name and a password,
signed in, saw that it was signed in, and clicked the link to order ord-1003.

- `trace.zip!trace.trace` lines 3 to 75: the steps `goto`, `fill`, `fill`, `click`, `expect toHaveText`, `click`, each
  with an "after" line and no error.
- `server.log` line 3: `POST /session 303 ... signed in`.
- `requests.txt` lines 1 to 6: each page answered 200, and the sign-in 303.

**2. The order page loaded, and its script asked the server for the order.**

- `requests.txt` line 6: `GET /orders/ord-1003 -> 200`. Line 8: `GET /api/orders/ord-1003`, of type `fetch`.
- `console.log` line 4: `[info] order page: asking for ord-1003`.

**3. The server answered that request with an error: status 500, "no price list for region north-2".** This is the
cause.

- `server.log` line 8: `GET /api/orders/ord-1003 500 0ms ERROR price_list_unavailable: no price list for region north-2,
  needed by ord-1003`.
- `failed-requests.json` lines 87 to 89: the request and its status, 500. Line 109: the answer's body,
  `{"error":"price_list_unavailable","detail":"no price list for region north-2","order":"ord-1003"}`.
- `requests.txt` line 8: `-> 500`.
- `trace.zip!trace.network` line 8: the same request and answer, as the browser recorded them.

**4. The page did not show the error. It wrote it to the console and stopped, leaving "Loading order…" on the screen.**
This is a second fault, in the page. It did not cause the failure, but it is why the failure looked like a timeout.

- `console.log` line 6: `[error] order page: could not load ord-1003. The server answered 500 ...`.
- `trace.zip!resources/7dd20f2e849d6858833a6d151aaf001ee2f24c47.html` lines 28 to 30: the page's script. When the
  answer is not OK it calls `console.error` and returns. Line 37 is the only place the `total` element is made, and it
  is reached only after a good answer.
- `screenshot.png`: the heading "Order ord-1003" and the words "Loading order…". No total, and no error message.
- `trace.zip!trace.trace` line 79: the page's HTML after the click. The order area holds only the "Loading order…"
  paragraph.

**5. So the element the test waited for could never appear, however long it waited.**

- `trace.zip!trace.trace` lines 82 to 88: the step `Expect "toBeVisible"` starts at 691 ms and ends at 5,694 ms with
  "Expect failed".
- `server.log` line 8 and `bundle.json` lines 13 and 14: the 500 was sent at 21:39:13.304, about 140 ms after the test
  started, and the test gave up at 21:39:18.316. Nothing happened in the five seconds between.

## Where the fault lies

| Suspect | Verdict | Supported by |
|---|---|---|
| The application's server, or its data | **The cause.** It could not price an order in region north-2 | `server.log` line 8; `failed-requests.json` line 109 |
| The page | **A second fault.** It hides the error from the person and from the test | `trace.zip!resources/7dd20f2e…html` lines 28 to 30; `screenshot.png` |
| The test | Not at fault. Its steps ran, and it waits for an element the page does make on success | `trace.zip!trace.trace` lines 3 to 75; the page's script, line 37 |
| The network | Not at fault. Every request was answered, in 0 to 2 ms | `requests.txt` lines 1 to 8; `failed-requests.json`: every `"failure"` is `null` |
| The sign-in | Not at fault. The answer was 500 with a pricing error, not 401 or 403 | `server.log` lines 3 and 8 |

## What looks like a problem and is not

The image `/static/promo.png` was answered 404 three times. It is not the cause.

- `requests.txt` lines 2, 5 and 7, and `console.log` lines 1 to 3: one 404 on each of the three pages.
- Two of those pages are the sign-in page and the list of orders, and the steps on both passed
  (`trace.zip!trace.trace` lines 3 to 56). So a page works with that 404.
- `screenshot.png`: the broken-image mark at the top left is this image.

## What the bundle cannot say

- **Why there is no price list for north-2.** It may be missing data, or a defect in how the server looks the list up.
  `server.log` has one line for the error and no more. Supported by: nothing in the bundle, which is the point.
- **Whether orders in the other region load.** The list of orders shows ord-1001 and ord-1002 in north-1
  (`trace.zip!resources/266a555a9d863be5a6abeb37c9e6a88dc95980be.html` lines 23 to 25), but this test did not open them.
- **Exactly what code ran.** `bundle.json` line 22 gives the commit, and line 23 says there were uncommitted changes.
  It gives a checksum of each file under test, which can confirm a file but cannot show it.

## Compared with the two blind readers

Both readers, working from the bundle alone, reached the same finding: the server's 500 for the missing north-2 price
list is the cause, the page's silence is a second fault, and the test, the network, the sign-in and the three 404s are
not at fault. Both were unsure of the same thing this note is unsure of: whether it is missing data or a server defect.
Neither needed to run the test. Where they found the bundle confusing is recorded in `logs/blind-diagnosis.txt`.
