# PROOF: Capture Trace, Screenshot, Log, Request, and Error Context on Failure

Quest `playwright-failure-evidence`, attempt `playwright-attempt-003`.

## How this was made

The configuration, the evidence fixture, the made-up application, the tests, the check scripts, the diagnosis and
this document were written by an AI assistant (Claude) at the participant's direction. The participant chose the
design in three decisions: the failure is a server error that looks like a page timeout; secrets are removed
before anything is saved and the result is then scanned, the trace included; and "another person can diagnose it"
is tested by giving the bundle to a fresh assistant that knows nothing else. Everything ran on the participant's
computer against an application on 127.0.0.1. Nothing outside that computer was contacted.

Words used below: **recorded** means a saved log shows it. **tested** means a planted fault showed that the check
notices when it is broken. **observed** means it was seen once, by hand. **not assessed** means nobody checked it.

## Approach

**The failure.** A made-up order desk, `demo-app/orders-server.mjs`, has two faults built in. Its server answers
500 for order ord-1003, because that order's region has no price list. Its page does not handle that: it writes
to the console and leaves "Loading order…" on screen. A test that waits for the order's total fails with a bare
timeout. The error names no cause, which is the quest's scenario. Every page also has one harmless 404, so that a
diagnosis has something to rule out.

**Capturing.** A test imports `test` from `support/evidence.ts` and gets a fixture that runs by itself. It
listens to the console and to every request, and records a Playwright trace. If the test fails, it writes one
folder, a failure bundle. If the test passes, it throws the trace away and writes one line.

**Why Playwright's own `trace: "retain-on-failure"` is not used.** Playwright saves its trace as it is, with
every cookie, Authorization header and typed password inside, and has no setting to remove them. So the built-in
trace, screenshot and video are off in `evidence.config.ts`, and the fixture records the trace itself, removes
the secrets from it, and only then saves it. The trace is a zip file and Node cannot read zip files, so
`support/zip.ts` is a small reader and writer made for this.

**Removing secrets, two ways.** By value: the fixture learns each cookie value, each Authorization header and
each value a test declares with `evidence.secret()`, and replaces that exact string everywhere. By place:
whatever the value, the content of a cookie or authorization header, of "Bearer …", of a password form field, of
a trace's own list of cookies, and of anything typed into a password field is replaced. Each can make good a
miss by the other. This computer's folder, user and machine names are replaced too, because a trace records the
path of the test file.

**Scanning.** The scan is in the check script and is written apart from the redaction. It does not know the
run's secret values. It looks for the shapes secrets have, in every file and in every entry inside `trace.zip`.

## The criteria, one by one

| # | Criterion | Status | Where |
|---|---|---|---|
| 1 | A failing test produces a trace, a screenshot, the console log, failed requests and the error text | recorded, tested | `logs/capture-check.txt` parts 2 and 3: each file is opened, not just found. The trace must hold steps, page snapshots and the 500. Planted faults A to F |
| 2 | A passing test does not keep heavy evidence by default | recorded, tested | `logs/passing-run.txt` part 1: every file the run left is listed. 147 bytes in all: one line, and Playwright's own 45-byte status file. Planted fault G |
| 3 | The bundle contains no token, cookie or credential, shown by a scan | recorded, tested, with a stated limit | `logs/redaction-check.txt` part 1: 16 files and trace entries searched, 0 findings. Part 2: the same test with redaction off gives 21 findings, and a password the script chose is found there and 0 times with redaction on. Planted faults H to N. **Limit:** `screenshot.png` is not searched. See below |
| 4 | The scan finds a planted fake value | recorded | `logs/redaction-check.txt` part 3: 7 fake values, 4 in plain files and 3 inside the trace, each found at its file and line, and nothing found elsewhere. Part 4: the report holds no value |
| 5 | The diagnosis cites a bundle file for each claim | recorded | `participant/context/playwright/diagnosis.md`: each claim names a file and line. One section says what the bundle cannot say, and cites nothing because nothing supports it |
| 6 | The configuration states how long evidence is kept | recorded, tested | `evidence.config.ts`: 14 days, in words and as a setting. `logs/passing-run.txt` part 2: a bundle past its date is deleted, one not yet due is kept, and two folders that are not bundles are left alone. Planted faults O, P, Q |
| 7 | Another person can diagnose the failure without rerunning the test | recorded for two AI readers. **Not assessed for a person** | `logs/blind-diagnosis.txt`. See below |

### Criterion 3: what "shown by a scan" covers and does not

The scan finding nothing would prove little by itself, so three things stand beside it. The bundle counts what
it replaced: 13 cookie values, 6 of the password, 2 of the token. The same test with redaction turned off, into
a scratch folder, gives 21 findings, inside the trace and outside it. And the check script chooses the password
the test types, so it can look for that exact string: it is in the unredacted trace, and nowhere in the redacted
bundle.

What it does not cover: **`screenshot.png` is a picture and is not searched.** The assistant looked at it. It
shows the heading "Order ord-1003", the words "Loading order…" and a broken-image mark. The trace is recorded
without its film of screenshots for the same reason. A secret shown on a real application's screen would be in
the screenshot, and nothing here would find it.

### Criterion 7: how far it was tested

Two fresh AI assistants were each given the bundle folder and nothing else, with rules not to read anything
else or run the test. Neither was told the cause. Both found it: the server's 500 for the missing price list is
the cause, the page's silence is a second fault, and the test, the network, the sign-in and the 404s are not at
fault. Both gave a file and line for each claim. Neither ran the test.

The first reader's bundle had a hint in it: the application's log called the 404 "Harmless". That was removed,
and the second reader read the bundle that is handed in.

What this does not show: the readers were AI assistants of the same kind as the one that built the bundle, not
people. The rules were given in words and nothing enforced them. The test's title told both readers the failure
was staged. **A person diagnosing from the bundle was not assessed.**

## What the bundle did not contain that I wished it had

This is what the quest asks for. Most of it came from the two blind readers, who wanted things the assistant
had not thought to give them.

1. **A passing run to compare with (criteria 2 and 7).** Both readers asked whether an order in the other
   region loads. The bundle cannot say, because a passing test keeps one line. Criterion 2 is why it is missing:
   the two criteria pull against each other here, and criterion 2 won.
2. **Why the server failed, below the one log line (criterion 7).** The server log says "no price list for
   region north-2" and no more: no stack trace, nothing about the data. So neither reader, nor the diagnosis,
   can say whether it is missing data or a defect. The bundle stops one layer above the root cause.
3. **The test's source (criteria 1 and 7).** `error.txt` gives a file and line number, not the line. Both
   readers rebuilt the steps from the trace.
4. **The Cookie header on the failed request (criteria 1 and 3).** `failed-requests.json` leaves it out
   altogether, where the trace shows it redacted. A reader of the JSON alone could suspect a missing session.
   Here criterion 3's caution took something from criterion 1 by accident, not by design: Playwright's quick
   list of headers omits cookies.
5. **Times that line up exactly (criterion 7).** The browser's and the server's times for one request differ by
   2 to 5 ms, so the server seems to answer before the request starts. The bundle's read-me promises more.
6. **Less noise (criterion 7).** Three of the four failed requests are the harmless 404.

None of these was fixed before hand-in. The bundle handed in is the one the second reader read, so that the
blind test describes the evidence as it is.

## Artifacts

| Required item | File |
|---|---|
| The configuration | `participant/tests/playwright/evidence.config.ts`, with `logs/passing-run.txt` for the passing run |
| The failure bundle | `failure-bundle/`, 9 files |
| The redaction check | `logs/redaction-check.txt`, 27 checks |
| The diagnosis | `participant/context/playwright/diagnosis.md` |
| The check script | `participant/tests/playwright/tools/failure-evidence-check.ts` |
| This narrative | `PROOF.md` |

Also here: `logs/capture-check.txt` (35 checks), `logs/passing-run.txt` (13 checks), `logs/planted-faults.txt`
(18 faults) and `logs/blind-diagnosis.txt`. The other code is under `participant/tests/playwright/`:
`failure-evidence.spec.ts`, `support/evidence.ts`, `support/zip.ts`, `support/retention.ts`,
`support/evidence-global-setup.ts`, `demo-app/orders-server.mjs` and
`tools/failure-evidence-planted-faults.ts`.

## Stretch goals

- **The application's server log for the same time window:** done. `server.log` in the bundle holds the
  application's lines from the test's start to its end, and no others. Recorded, and tested by planted fault R.
- **Link each bundle to the commit under test:** done, with a limit. `bundle.json` gives the commit and says
  whether the tests folder had uncommitted changes. For the handed-in bundle it did, because this work was not
  yet committed, so the commit alone does not say what ran. For that case the bundle also gives a checksum of
  the test, the fixture and the application. Those checksums are of the files as they were when the handed-in
  bundle was made. Three of the files were changed afterwards, to rename the flagged names (see "Faults found"),
  so they no longer match the files in the repository. The bundle was not made again, so that it stays the one
  the second blind reader read.

## Reproduce

From `participant/tests/playwright`, with Node 22.18 or later and Playwright installed as for the earlier
Playwright quests:

    node tools/failure-evidence-check.ts
    node tools/failure-evidence-planted-faults.ts

The first writes the three logs again and reads the handed-in bundle without changing it. With `--save-bundle`
it replaces the bundle with a new one, whose times and trace differ, so the line numbers in the diagnosis would
no longer fit. The second changes source files while it runs and restores them. Neither contacts anything but
127.0.0.1.

## What was tested

| What | Result |
|---|---|
| Recorded checks | 35, 13 and 27, all pass |
| Planted faults | 18 put into the capture, redaction and retention code, one at a time. Each was noticed by the check it is about (`logs/planted-faults.txt`) |
| Blind readers | 2, both correct |
| The rewritten trace | Tested by the system's `unzip` (recorded). Opened once in Playwright's own trace viewer, which listed the steps and showed the password as redacted (observed) |

Faults found while building:

- **The scan and the redaction shared two blind spots.** A trace lists each request's cookies apart from its
  headers, and writes form fields as name and value pairs. Neither was redacted by place, and the scan had no
  shape for either, so an unlearned cookie there would have passed both. Found while writing planted fault K.
  Both now cover them.
- **A password typed by a test that never declared it would have stayed in the trace,** and the scan could not
  have seen it, because a typed value has no shape. Two things were added: redaction of whatever is typed into a
  password field, and the check that looks for a password the script itself chose. Planted fault M.
- A planted fake key was badly formed, so the scan rightly did not find it. The fake was corrected.
- The check picked a test by a pattern that matched no test. Its log helper dropped lines.
- The application's log gave away one answer of the diagnosis. Removed after the first blind reader.
- The repository's own secret scan flagged six lines of the new source, for names such as `password` given a
  made-up value. The names were changed. The scan was not.

## What could not be done, and limitations

- **A person as the reader: not assessed.** See criterion 7.
- **The screenshot is not searched.** See criterion 3.
- **The scan knows shapes, not secrets.** A secret with no known shape, in a place redaction does not know,
  passes both. An encoded secret (base64, or URL-encoded with characters that change) is not replaced by value.
  A secret under 8 characters is not replaced by value.
- **Redaction can remove too much.** Any text equal to a learned value is replaced, and the user name is
  replaced wherever it appears, even inside another word.
- **Every secret here is made up.** The application accepts any password. No real login, token or cookie was
  used, so redaction of real ones is not assessed.
- **One browser, one failure.** Chromium only. A test that times out as a whole, a crashed page, a failure with
  retries, several tests failing at once, and a failure before the page opens: not assessed.
- **The retention check uses made-up bundles with made-up dates.** No bundle was really kept 14 days.
- **Playwright itself still writes `error-context.md`** for a failed test, in its scratch folder. It holds the
  error and an outline of the page. It is not copied into the bundle and is not redacted. For this application
  it holds no secret. For another it might.
- **The trace viewer was opened once,** by hand, and that is not in the check script.
- The fixture, the scan, the application and the faults were written by the same assistant. The blind readers
  and the planted faults are the two checks on that.

## Reflection

*What is the most useful thing your bundle leaves out?*

A run that worked. Everything in my bundle describes the one moment something went wrong. Both blind readers
asked the same question I could not answer from it: do the other orders load? If they do, the fault is in one
region's data. If they do not, the whole API is down. That single comparison would have told them which, and it
is exactly what I chose to throw away, because the quest says a passing test should keep almost nothing.

I did not see that when I made the decision. Keeping one line for a passing test felt obviously right: less to
store, less to leak. It took a reader who had only the bundle to show me the cost. The evidence of failure is
much easier to read next to evidence of success, and I only kept one of the two.

The second thing left out is the reason underneath the reason. My server log says "no price list for region
north-2". That sounds like an answer, and it stopped me looking further. But it does not say whether the data
is missing or the code is wrong, and neither reader could say either. I think that is the trap in this whole
quest: a bundle can look complete because it explains the symptom, and still stop one layer above the cause.

What I did not expect was the thing I left out by accident. I worked hard to take cookies out of the evidence,
and in one file the cookie header is simply gone, with no mark that it was ever there. A reader could have
decided the session was missing. Removing a secret and removing the fact that a secret was sent are different
things, and I only meant to do the first.

If I did it again I would keep a very small record from the last passing run of the same test, with the same
redaction, and put it in the bundle beside the failure.

## Sensitive values

- No real login, token or session cookie was used anywhere. The application makes a random cookie and token when
  a test signs in, and the test makes a random password. They open only that application, on that computer,
  until it stops.
- The handed-in bundle was scanned: 0 findings in 16 files and trace entries. `screenshot.png` was not searched
  and was looked at by the assistant.
- The unredacted bundle used to test the scan was written to a scratch folder and deleted by the same script.
  Its secrets were as made up as the others.
- This computer's home folder, user name and machine name are replaced in the bundle by `HOME`, `REPO`,
  `[user]` and `[machine]`. The scan looks for them and finds none.
- The scan's report gives a file, a line and a kind. It has no field for a value.
- The names in the application, such as "Fixture Freight Ltd" and "Fixture Clerk", are invented.
