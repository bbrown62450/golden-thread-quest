# jira-idempotent-create

Creates one Jira Task from one draft file, built so that running it again or interrupting it does not create a
second one. That holds on one computer, with the local record kept and the label left on the item. The design, its
conditions and its limits are in `participant/context/jira/idempotent/design.md`. Read "The limits" there.

## When to use it

- To create a Jira item from a draft, when a timeout or a crash must not produce a second item.
- After a creation that ended without an answer: run `resolve`, never `confirm` again.

## Before anything else

- **Sandbox only.** The project must be on the sandbox allowlist, for that Jira site. Any other is refused.
- **A person confirms every write,** by typing the fingerprint of a preview they have read.
- **Real runs are the person's to run,** in their own terminal, with `JIRA_BASE_URL`, `JIRA_EMAIL` and
  `JIRA_API_TOKEN` set there. The agent builds and tests against the fake Jira and reads saved output only.

## The commands

| Command | Reads Jira | Writes to Jira | What it does |
|---|---|---|---|
| `preview` | yes | **never: it is given no way to** | Makes or reads the draft's key. Shows the site, the project, exactly what would be sent, the permission check, both duplicate checks and a fingerprint |
| `confirm` | yes | **one new Task** | Creates the Task of one preview, named by its fingerprint. Marks the record `sending` before the request goes |
| `resolve` | yes | **never** | The rerun after an interruption. Searches for the key. Records the item if exactly one carries it |
| `check` | yes | **never** | Reads a recorded item back. Says whether it still carries the key |

    create_once.py preview --source live --draft DRAFT.json --allowlist ALLOWLIST.json --state STATE
    create_once.py confirm --source live --draft DRAFT.json --allowlist ALLOWLIST.json --state STATE --fingerprint CODE --confirmed-by NAME
    create_once.py resolve --source live --draft DRAFT.json --state STATE
    create_once.py check   --source live --draft DRAFT.json --state STATE

A draft is `{"project": "KEY", "summary": "the title"}`. `--source fake` runs against the fake Jira kept in STATE.

## What to do with each ending

| It ends with | Meaning | Do this |
|---|---|---|
| exit 0 | Done, or nothing to do | Nothing |
| exit 1, `REFUSED` | Nothing was written by this run | **Read the reason.** If it says an outcome is not known, run `resolve`. Otherwise it says what to do, usually a new preview |
| exit 1, `NOT FOUND YET` | An empty search is not trusted yet | Run `resolve` again at the time it prints |
| exit 1 from `check` | The item is there and was not found by its key, or is not as recorded | Read the lines above it |
| exit 2, `A PERSON NEEDS TO LOOK` | The outcome is not known, or the search failed, or more than one item carries the key | **Do not confirm again.** Run `resolve`, or look in Jira by hand |
| exit 3 | Stopped on purpose by the test switch `--interrupt-at` | Tests only |

## Rules it keeps

- The key is made once per draft, saved before anything is asked of Jira, and sent as the item's one label.
- A write is sent once. The same run never sends it again.
- A timeout, a server error or a crash after sending is "not known", never "failed".
- A failed search is never read as "nothing found".
- After "not known", creating again needs two empty searches, each 60 seconds or more after the request ended and
  30 seconds or more apart, then a new preview and a new confirmation by a person. It carries the same key.
- One run at a time may confirm a draft. A real write must be started from a terminal.
- The test switches: `--pretend-seconds-later` is refused against a real Jira. `--pretend-minutes-later` can only
  make a preview older. `--interrupt-at` ends a run early and can send nothing extra.
- Other people's text from Jira is not acted on. Titles of other items are never shown: items are named by issue
  key and issue id. Jira's own words about a refusal are shown on screen and not saved.
- The site's address is shown on screen and replaced by a marker in anything saved.

## What it cannot do

See "The limits" in the design. In short: Jira has no "create only if absent"; its search can be behind; a lost
local record, a renamed draft or another state folder means a new key; a removed label makes the item unfindable by
key; nothing stops a second computer.

## Tests

    cd participant/skills/jira-idempotent-create && python3 -m unittest tests.test_create_once
