# Read me first

This folder is a failure bundle. A Playwright test failed, and this is everything that was kept about
that one failure. It is meant to be enough to find out why, without running the test again.

Start with `bundle.json`: which test, when, and the commit of the code under test.

| File | What it is |
|---|---|
| `error.txt` | The error message, and the line of the test that raised it |
| `screenshot.png` | The page as it was when the test gave up |
| `console.log` | Everything the page wrote to the browser's console, oldest first, with times |
| `failed-requests.json` | Every request that failed, or was answered with status 400 or above, with the answer's body |
| `requests.txt` | Every request the page made, one line each, oldest first |
| `server.log` | The application's own log, for the time the test ran |
| `trace.zip` | The Playwright trace: every step of the test, the page's HTML before and after it, and the network |
| `bundle.json` | The test, the times, the commit, a checksum of each file here, and what was redacted |

All times are UTC, in the same form in every file, so that lines from different files can be put in order.

To open the trace: `npx playwright show-trace trace.zip`. It can also be opened as an ordinary zip file. It
was recorded without its film of screenshots, so the viewer shows the page's HTML at each step and no pictures.

Secrets were removed before these files were saved. Where one was, the text `[REDACTED ...]` stands in its
place. The names `HOME`, `REPO`, `[user]` and `[machine]` stand for the folder and names of the computer
the test ran on. `screenshot.png` is a picture and could not be searched: look at it before sharing it.

This folder is deleted on the date `bundle.json` gives as `deleteAfter`.
