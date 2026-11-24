# Triage rules: what a failing test is, from its evidence

Written by an AI assistant (Claude) at the participant's direction, for the quest `playwright-failure-triage`. These
rules were written before any of the quest's failures was produced.

A failing test gets **exactly one** of five classes. The class says where the fault is, and so who has to act.

| Class | The fault is in | Who acts next |
|---|---|---|
| `product-bug` | the application: it does something its users should not get | the application's developers |
| `test-defect` | the test: the application behaves correctly and the test is wrong about it | the owner of the test |
| `environment` | where it ran: something the application depends on, or the machine, failed | the platform team |
| `data` | what it ran on: the data the test relies on is wrong or missing | the owner of the test data |
| `inconclusive` | not known: the evidence fits more than one of the above, or none | whoever can get the missing evidence |

**"Flaky" is not a class.** It describes how often a failure happens. It does not say where the fault is. A failure that
comes and goes still has one of the five classes.

## 1. The evidence

A failure's evidence is its bundle, one folder:

| File | What it tells you |
|---|---|
| `error.txt` | what the test expected and what it got, and the line that raised it |
| `test-source.txt` | the test's own code. Needed to judge whether the test is right |
| `screenshot.png` | the page when the test gave up |
| `screenshot-after-wait.png` | the page a little later, after the bundle waited for requests that were still unanswered |
| `page-text.txt` | the text a person could read on the page, at those same two moments |
| `console.log` | what the page wrote to the browser's console |
| `requests.txt` | every request, in order, with status and time taken |
| `failed-requests.json` | requests that failed or were answered 400 or above, with the answer's body |
| `api-responses.json` | the answers to the page's data requests, with their bodies. What the application was told |
| `server.log` | the application's own log for those seconds |
| `trace.zip` | each step of the test, and the page's HTML before and after it |
| `attempts.json` | each attempt of this test in the run, and how often the test failed when repeated |
| `bundle.json` | the test, the times, checksums |

A classification must **cite at least one of these files**, and say what in the file supports it. A class that no file
in the bundle supports may not be given. Give `inconclusive`.

The error message alone is never enough. "Timed out waiting for an element" is what four of the five classes look like.

## 2. What each class needs before you give it

For each class: the signs that suggest it, and what the evidence **must show**. Signs are where to look. Only the "must
show" list lets you classify.

### `product-bug`

Signs: the page shows something wrong, or contradicts itself; an answer from the application is wrong; a server error
with no outside cause; the page mishandles a correct answer.

The evidence must show **all** of:

1. **The application did something wrong**, and you can point at it: a wrong value, a missing or contradictory thing on
   the page, a wrong answer from the server, or a correct answer the page then mishandled.
2. **The test's expectation is right.** `test-source.txt` asks for what a user would reasonably expect, and it waits
   properly for it.
3. **What the application depends on was working.** No refused connection, no failing dependency, in `server.log` or
   `failed-requests.json`.
4. **The data was valid.** Nothing in the answers says the data was rejected as malformed.

If the application is wrong only some of the time, it is still a product bug. See section 4.

### `test-defect`

Signs: the page ends up right and the test still failed; the test reads a value without waiting for it; the test looks
for something by a name the page does not use; the expected value in the test disagrees with what the application was
correctly told to show.

The evidence must show **both** of:

1. **The application behaved correctly**: the page, when it had finished, showed what the data says it should
   (`screenshot-after-wait.png`, `page-text.txt`, `api-responses.json`), with no error in `console.log` or
   `server.log`.
2. **The fault is visible in the test's own code**: `test-source.txt` shows the step that is wrong, such as a value read
   with no wait, a wrong name, or a wrong expected value.

"The test is probably wrong" without point 2 is not enough. A test that fails because the application is slow or
wrong is not a test defect.

### `environment`

Signs: connection refused, a timeout reaching another service, a dependency reported as down, the disk or memory
exhausted, a certificate or DNS error; an error that names something outside the application.

The evidence must show **both** of:

1. **Something outside the application's own code failed, and it is named**: a refused or failed connection, or an error
   that identifies a dependency or the machine, in `server.log`, `failed-requests.json` or `console.log`.
2. **The application reported or handled it as such.** What went wrong traces back to that outside failure, not to how
   the application treated a healthy answer.

A slow answer **with no stated cause** is not evidence of an environment problem. Slowness has many causes, and some of
them are in the application.

### `data`

Signs: an answer saying a record is invalid or missing; a "not found" for something the test assumed was there; a value
the application refuses; a duplicate that should be unique.

The evidence must show **both** of:

1. **The application rejected or lacked a specific piece of data, and says which**: the answer's body or `server.log`
   names the record and what is wrong with it.
2. **The application's refusal is the correct behaviour**: it reports the problem clearly, and does not crash or show
   something wrong.

If the application accepts bad data and shows nonsense, that is a product bug, not a data problem. If the data is fine
and the application rejects it, that is a product bug too.

### `inconclusive`

Give it when, after reading the whole bundle:

- the evidence fits **two or more** classes and nothing in the bundle chooses between them; or
- the "must show" list of **no** class is met.

An inconclusive classification must say:

1. **which classes are still possible**, and what in the bundle supports each;
2. **what would settle it**: the specific evidence that is missing, and how to get it.

Inconclusive is not a way to avoid reading. If the bundle holds the answer, it is not inconclusive.

## 3. The order to work in

1. Read `error.txt` and `test-source.txt`. Know what the test did and expected.
2. Read `requests.txt`, `failed-requests.json` and `server.log`. Did any request fail, and does anything name a cause?
3. Read `api-responses.json` and look at what the page showed when the test gave up and what it ended up showing
   (`page-text.txt`, the two screenshots). Was the application told the right thing, and did it show it?
4. Read `attempts.json`. Did it fail every time?
5. Try each class's "must show" list. Give the class whose whole list is met. If more than one is met, or none, give
   `inconclusive`.

Where a failure has two faults, give the class of the fault that **caused the test to fail**, and name the other in the
reason.

*Added after the six failures were classified, because both classifiers said the rules did not cover it:* a bundle can
show a fault that happened **after** the test had already given up, in `page-text.txt`'s second moment or in
`screenshot-after-wait.png`. Such a fault is real and must be reported to whoever owns it. It is not the class of this
failure, because it is not why the test failed. Class the failure by what the evidence shows up to the moment the test
gave up. If that is not enough for any class, the failure is `inconclusive`, however certain the later fault is.

## 4. Failures that pass on a retry

A failure that passes when run again has still failed. The retry is one more fact to explain, and it changes nothing
about which class the failure belongs to.

- Classify from the **failed attempt's** evidence, by the lists above.
- Then explain the retry: what differed between the attempt that failed and the one that passed? `attempts.json` holds
  both, and `requests.txt` shows the order things happened in.
- If the application is wrong in the failed attempt, and what differed is timing or order, it is a `product-bug`: a
  race in the application. It will happen to users too.
- If the test read too early in the failed attempt, and the page was right, it is a `test-defect`.
- If a dependency was down in one attempt and up in the next, it is `environment`.
- "It passed on retry" is never the reason for a class, and never a reason to close a failure.

How often it fails belongs in the report as a fact. It is not a class.

## 5. What every classification states

1. **The class**: one of the five.
2. **The evidence**: the files cited, and what in each supports the class.
3. **What was ruled out**, where another class was plausible.
4. **The next action**, concrete enough to start on.
5. **Who takes it**: the role from the table at the top.
6. For `inconclusive`: what is still possible, and what would settle it.

## 6. Traps

- **Calling a test defect because the test is the easiest thing to change.** A test defect needs the fault shown in the
  test's code and the application shown to be right. Both.
- **Reading the later screenshot as the moment of failure.** `screenshot-after-wait.png` is taken afterwards. A page that
  looks right there may have been wrong, or not ready, when the test looked. And a page that is right in the end can
  still have been right too late for a user.
- **Calling slowness "environment".** Unless something names an outside cause, slowness is unexplained.
- **Stopping at the first failed request.** A failed request may be harmless and present in passing runs too. Ask
  whether it is connected to what the test was checking.
- **Trusting the server's summary.** A log line saying what went wrong is evidence of what the application believed,
  which is usually, and not always, what happened.
