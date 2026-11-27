---
name: jira-query-stories
description: Run a saved Jira query from configuration, fetch every page, and report the total Jira stated against the number saved. Use when someone needs a count or a list from Jira that must be known to be whole. Reads only.
---

# Run a saved Jira query, every page of it

Use this when a count or list from Jira will be relied on, and "the first page" would be a wrong answer.

## What it does

1. Reads the saved queries from `participant/context/jira/queries.yaml`. Each has a name, a purpose and a filter.
2. Asks Jira how many items the query matches.
3. Fetches every page, until Jira gives no marker for a further page.
4. Asks for the count again, and compares.
5. Writes the result file only if every page arrived, no item came twice, every item is in the project asked for, and
   the number saved equals the count Jira stated before and after.

Anything else is `RESULT: INCOMPLETE`, exit code 2, and no result file.

## Commands

From the `participant` folder:

    python3 skills/jira-query-stories/run_query.py list --config context/jira/queries.yaml

    python3 skills/jira-query-stories/run_query.py run --config context/jira/queries.yaml \
        --query all-stories --project DEMO --source fake \
        --fixture skills/jira-query-stories/fixtures/demo.json --out RESULT.json

For a real Jira, `--source live`, with `JIRA_BASE_URL`, `JIRA_EMAIL` and `JIRA_API_TOKEN` set in the terminal by the
person running it. The agent does not run live commands and does not handle the token.

## Rules for whoever uses the result

- **Read the RESULT line.** Only `RESULT: COMPLETE` means every check held: every page answered, no item twice,
  every item in the project, and the number saved equal to Jira's count before and after.
- **COMPLETE is not a frozen picture.** If one item left the query and another joined it while the pages were read,
  every check would still hold. For a number that matters, run it twice.
- **Exit code 2 means there is no result.** Do not report a number from an incomplete run, and do not fall back to a
  file left by an older run: the output says when one is there, and that it is not this run's.
- **Zero is an answer.** A query that matches nothing is complete, with zero items.
- **To change a query, edit the configuration.** Not the code. The file's own header says how it must be written. A
  filter cannot carry `ORDER BY` or a backslash. The tool wraps it to keep it inside the project named with
  `--project`, which must be on the configuration's `allowed_projects`, and checks every item that comes back.
- **A date goes in with `--set name=2026-11-01`.** Nothing else can be put into a query from the command line.
- **What is saved** for each item: key, id, type, status, status category, last-updated time in UTC. No titles,
  descriptions or people. Status and type names are other people's text: they are cut short and cleaned, and the
  output says how many were changed.
- **`--log` and `--out` must be different files.**

## Limits

- Jira calls its count approximate. A mismatch may be Jira's doing. It is reported either way.
- I believe Jira compares a date in the time zone of the account, not in UTC. This was not checked.
- The site fingerprint is a short, unsalted hash of the site's name. Someone who guesses the name can confirm it.
- A new query that uses more of JQL than the made-up Jira reads can only be tried against a real Jira, by a person.
- An incomplete run starts again from the first page. Nothing is resumed.
- The made-up Jira understands a small part of JQL. It is a model for tests.
