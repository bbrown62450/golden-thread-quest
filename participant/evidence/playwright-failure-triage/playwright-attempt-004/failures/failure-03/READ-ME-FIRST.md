# Read me first

This folder is a failure bundle. A Playwright test failed, and this is what was kept about it.

| File | What it is |
|---|---|
| `error.txt` | The error message of the first failed attempt, and the line of the test that raised it |
| `test-source.txt` | The code of the test, and of the helpers it calls |
| `screenshot.png` | The page when the test gave up |
| `screenshot-after-wait.png` | The page a little later, after waiting for requests that were still unanswered |
| `page-text.txt` | The text a person could read on the page, at those same two moments |
| `console.log` | Everything the page wrote to the browser's console, oldest first, with times |
| `requests.txt` | Every request the page made, one line each, oldest first, with status and time taken |
| `failed-requests.json` | Every request that failed, or was answered with status 400 or above, with the answer's body |
| `api-responses.json` | The answers to the page's data requests, with their bodies, whatever their status |
| `server.log` | The application's own log, for the time the attempt ran |
| `trace.zip` | The Playwright trace: every step of the test, the page's HTML before and after it, and the network |
| `attempts.json` | Every attempt of this test in the run, and how often it failed when it was run again |
| `bundle.json` | The test, the times, a checksum of each file here, and what was redacted |

All times are UTC. The browser's clock and the server's can differ by a few milliseconds.

After a failure, the bundle waits up to 5 seconds for requests that were still unanswered, so that `requests.txt` says how
they ended. A request marked "answered after the test gave up" finished during that wait.

To open the trace: `npx playwright show-trace trace.zip`. It can also be opened as an ordinary zip file. It has no
film of screenshots.

Secrets were removed before these files were saved. Where one was, the text `[REDACTED ...]` stands in its place. The
names `HOME`, `REPO`, `[user]` and `[machine]` stand for the folder and names of the computer the test ran on.
The two screenshots are pictures and could not be searched.
