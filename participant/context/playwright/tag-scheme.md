# Tag scheme for the Playwright tests of the customer directory

**Every test carries exactly one tag from each of the five dimensions below, and no other tag.** Written by `participant/tests/playwright/tools/tagging-check.ts` from `support/tags.ts`. Do not edit it by hand: the check compares the two.

## Feature: Which of the directory's four functions is the test about?

Rule: The last thing the test itself does before its assertions: add, upgrade or remove. Set-up does not count, so a test that adds a customer only to upgrade it is an upgrade test. A test that only looks is a list test, unless all it looks at is the controls of one function.

| Tag | Meaning |
|---|---|
| `@feature-list` | The test only looks at the customers that exist |
| `@feature-add` | The test adds a customer, or tries to, or looks only at the form for adding one |
| `@feature-upgrade` | The test changes a customer's plan to plus |
| `@feature-remove` | The test removes a customer, or tries to |

## Risk: What could this test catch going wrong?

Rule: Decided by what the test does and asserts, not by a guess at the cause. Take the first of the three that fits, from the top.

| Tag | Meaning |
|---|---|
| `@risk-high` | A change went wrong. The test sends an add, an upgrade or a remove, and then asserts which customers exist or what plan one has |
| `@risk-medium` | What is there is shown or returned wrongly. The test changes nothing, and asserts which customers exist or what plan one has |
| `@risk-low` | Anything else: the test asserts only controls, labels or the status of an answer |

## Read or write: Does running the test send the application anything but a read?

Rule: Counted over every request the test sends, set-up and clean-up included. The check watches the requests.

| Tag | Meaning |
|---|---|
| `@read` | Every request is a GET or a HEAD. The test changes nothing. It can still fail if someone else changes the data it reads |
| `@write` | At least one request is a POST, PUT, PATCH or DELETE. Not for a shared environment |

## Layer: Does the test open the page in a browser?

Rule: The check tells the two apart by what sent each request.

| Tag | Meaning |
|---|---|
| `@layer-api` | No browser: every request comes from the test runner's own request client |
| `@layer-ui` | A browser opens the page at least once |

## Duration: How long does the test take, run on its own?

Rule: The slowest of three runs, each alone, by the time Playwright reports for the test. The limits are written once, as numbers, and the check measures against them.

| Tag | Meaning |
|---|---|
| `@fast` | Quick enough to run on every change. **Limit: at most 2 seconds** |
| `@slow` | Too slow for @fast. A test over this limit gets no tag: it is split or rewritten. **Limit: at most 10 seconds** |

## Selections: runs made by combining tags, not by adding one

| Run | Playwright's `--grep` | What it is |
|---|---|---|
| smoke | `(?=.*@risk-high)(?=.*@fast)` | High risk and fast: what must hold before anything else is worth running |
| changes nothing | `@read` | Every test that only reads. None of the smoke tests is among them: each of those writes |

There is no `@smoke` tag. "Smoke" is the first selection above, so what it promises is what its two tags promise.
