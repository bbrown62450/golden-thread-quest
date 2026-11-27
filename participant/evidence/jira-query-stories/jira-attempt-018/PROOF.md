# Proof · jira-query-stories

Attempt: `jira-attempt-018`

## How this was made

The participant made four decisions: to use a made-up Jira for the required records and the real sandbox for one
read-only check; to ask Jira for its own count and compare; that an incomplete run leaves no result file; and to do
the date parameter and not the resumed run. The participant ran every command that reached the real Jira, in their
own terminal. An AI assistant (Claude) wrote the tool, the made-up Jira, the tests, the scripts and this file. Two
further AI assistants read the work. No person other than the participant has read it.

## The short version

- **Queries are settings.** Five saved queries, each with a name and a purpose, in one file. None is in the code.
- **Every page is fetched,** until Jira gives no marker for a further page.
- **Two numbers are reported:** the total Jira stated, and the number saved. If they differ the run fails.
- **An incomplete run leaves nothing.** No result file, no temporary file, and exit code 2.
- **Zero is an answer.** A query that matches nothing is complete, with zero items.
- **Checked once against the real sandbox:** Jira stated 25 and 25 were saved, in three pages.
- **Two readers found real faults in the first version.** One was a way for a saved filter to leave its project. All
  are fixed. See below.
- **"Complete" has a limit that no check here removes.** It is stated in the tool's own output.

## How I know pagination ended (criterion 2)

**Not by a short page, and not by an empty one.** Jira may send fewer items than were asked for on any page.

The pages have ended when a page carries **no marker for a next page**, and does not say otherwise. That is Jira's
own word for "this is the last". The tool takes nothing else for an end:

| What Jira sends | What the tool does |
|---|---|
| A page with a marker | Asks for the next page with that marker |
| A page with no marker, and `isLast` true or absent | The pages have ended |
| A page with no marker, and `isLast` anything else | Incomplete: Jira did not say it was the last |
| An empty page with a marker | Incomplete |
| The same marker it was asked with | Incomplete: the next page would be this one again |
| A page shorter than asked for, with a marker | Carries on. A short page is not an end |
| 500 pages | Incomplete: the tool's own limit |

**Jira's word is then checked against a second thing, its count** (criteria 3 and 4). The tool asks Jira how many
items the query matches, before the pages and again after. The result is written only if:

1. every page was answered and could be read;
2. the last page ended the pages, as above;
3. no item came twice, by id or by key;
4. every item is in the project asked for, and has the type, status and time that were asked for;
5. the number of items equals the count Jira stated, before **and** after.

The quest's scenario is trial 3 of `shortfall-run.txt`: the first page says it is the last, ten items arrive, and
Jira's count says 28. The run fails with "MISMATCH: Jira stated 28 and 10 arrived, 18 short".

**What this cannot show.** If one item leaves the query while the pages are being read and another joins it, the
count is the same before and after, the number saved matches, and one item is missing and one is extra. A reader
found this. I did not fix it, because I do not think it can be fixed from outside Jira. The tool prints it under
every complete result. Jira also calls its count approximate.

## The criteria, one by one

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Queries live in configuration with a name and a purpose | Tested | `participant/context/jira/queries.yaml`. `config-change-run.txt` part 1 lists each. A query with no purpose is refused |
| 2 | All pages are retrieved until Jira reports no more | Tested on the made-up Jira. Seen once on the real one, with no fault | `query-run.txt`: 3 pages, 28 of 28, compared key by key with the fixture. `live-all-items.txt`: 3 pages, 25 of 25 |
| 3 | The run reports the total Jira stated and the number saved | Tested. Seen on the real Jira | The lines "Total Jira stated" and "Items saved locally" in every record |
| 4 | A mismatch between them is reported as a failure | Tested on the made-up Jira only | `shortfall-run.txt` trial 3: exit code 2, MISMATCH. Tests cover more arriving than stated too. **A real Jira has never given this tool a mismatch** |
| 5 | A page failing partway does not produce a result that looks complete | Tested on the made-up Jira only | `shortfall-run.txt` trials 1 and 2: the third page fails; "Jira stated 28 and 20 arrived. 8 did not"; the results folder is empty. With an older result present, it is left byte for byte and called older. **A real Jira has never failed a page for this tool** |
| 6 | A query returning no results reports zero, not an error | Tested. Seen on the real Jira | `config-change-run.txt` part 3. `live-stories-with-no-such-label.txt`: stated 0, saved 0, complete |
| 7 | Changing a query needs no code change | Tested on the made-up Jira | `config-change-run.txt` part 2: one line of a copy of the configuration is edited; the query sent and the result both change; nothing else is touched |

## Where the important artifacts are

| Path | What it is |
|---|---|
| `participant/context/jira/queries.yaml` | The saved queries, and how to write one |
| `participant/skills/jira-query-stories/run_query.py` | The tool: `list` and `run` |
| `participant/skills/jira-query-stories/SKILL.md` | When to use it, and the rules for whoever uses a result |
| `participant/skills/jira-query-stories/fake_jira.py`, `fixtures/demo.json` | The made-up Jira and its 40 made-up items |
| `participant/skills/jira-query-stories/tests/test_run_query.py` | 80 tests |
| `participant/context/jira/queries/` | The three results from the real sandbox: keys, types, statuses and times. No titles or people |

Under `participant/evidence/jira-query-stories/jira-attempt-018/`:

| Path | What it is |
|---|---|
| `logs/query-run.txt` | The three-page run. 8 checks |
| `logs/shortfall-run.txt` | A page failing partway, with and without an older result; the scenario; the right number of wrong items. 13 checks |
| `logs/config-change-run.txt` | The queries listed; a query changed with no code change; zero results; a date. 11 checks |
| `logs/live-all-items.txt`, `logs/live-stories-with-no-such-label.txt`, `logs/live-stories-updated-since.txt` | The real sandbox, read only, run by the participant with the final tool |
| `logs/live-run.txt` | The first real run, made with the tool **before** the readers' fixes. Kept as it was |
| `logs/tests.txt`, `logs/planted-bugs.txt` | 80 tests passing; 66 planted bugs, each caught |
| `logs/independent-read.txt` | What the two AI readers found, and what was changed. Written by hand |
| `scripts/record_runs.py`, `scripts/planted_bugs.py` | What made the records |

The quest names the folder `attempt-001`. The application made `jira-attempt-018`. The two required records and this
file are copied to `participant/evidence/jira-query-stories/attempt-001/`, with a note there saying so.

## Stretch goals

- **A query parameter such as a date: done.** `stories-updated-since` has a blank, `{since}`, filled with
  `--set since=2026-11-01`. The value must be a real date, in plain digits, and is put in quoted. Nothing else can
  be put into a query from the command line. The tests found a fault here in my first version: a date written in the
  digits of another script was accepted.
- **Cache a page and show a resumed run: not done.** The participant decided that an incomplete run keeps nothing,
  so there is nothing to resume from. A failed run starts again from the first page.

## How to reproduce the behavior

Python 3.9 or later, with nothing installed. From the `participant` folder:

    cd skills/jira-query-stories && python3 -m unittest tests.test_run_query
    python3 evidence/jira-query-stories/jira-attempt-018/scripts/record_runs.py
    python3 skills/jira-query-stories/run_query.py list --config context/jira/queries.yaml

One test compares my reading of the configuration with a full YAML reader, and is skipped if PyYAML is not installed.
`logs/tests.txt` was made with the project's own Python, which has it, so there the comparison ran.

Against a real Jira, by a person, with `JIRA_BASE_URL`, `JIRA_EMAIL` and `JIRA_API_TOKEN` set in their terminal:

    python3 skills/jira-query-stories/run_query.py run --config context/jira/queries.yaml \
        --query all-items --project SCRUM --source live --out RESULT.json

## What was tested or validated

- **80 tests.** The configuration and thirty-eight ways it can be wrong; a changed and an added query; the page size
  as a setting; three pages; a short page that is not the end; zero results; twenty faults in the pages and the
  count, each leaving nothing; an older result left alone; what is refused before Jira is asked; a real server's
  refusals (401, 403, 404, 429, 500, 502, a redirect) at each of the five requests; a dropped connection.
- **66 planted bugs,** each put into a copy of the tool and caught by at least one test. Thirty were added after the
  readers' reports. Three mistakes are not planted, with the reason for each, at the end of the record.
- **32 checks** in the three records.
- **Three runs against the real sandbox,** five requests, three and three: two kinds of request, both reads.
- The project's secret scan, and a search for names and paths, over every file of this quest.

## What the independent readers found

Two AI readers, not people. The full account is in `logs/independent-read.txt`.

- **A saved filter could leave its project.** Both found it. A backslash before a quote made my check and Jira
  disagree about where a quoted value ends. Items of another project would have been fetched and counted, then
  rejected one by one. My statement that a filter "cannot reach outside the project" was untrue. A backslash in a
  filter is now refused, and the statement now says what is and is not guaranteed.
- **COMPLETE claimed more than it can.** The limit above. Stated now, in the output.
- **Wrong numbers when a page failed in its middle.** Items of the failing page were counted as arrived. Fixed.
- **The result was written before the search for credentials,** and `--log` could be aimed at the result file.
  Both fixed.
- **Items with missing fields were saved as blanks,** and names in other scripts were turned into question marks,
  under COMPLETE and with no warning. A missing field now fails the run. Letters of any script are kept.
- **Eight mistakes the tests would not have noticed,** most of them in the connection to a real Jira. Tests added.
- **Two of my reasons for not planting a bug were false.** Those bugs are planted now, with tests.
- **Five checks in the records claimed more than they tested.** One could not fail at all. Each was changed.
- **Neither reader saw the corrected version.**

## Remaining limitations

- **COMPLETE is not a frozen picture of Jira.** Changes that cancel out during a run are not seen.
- **Jira calls its count approximate.** In three real runs it equalled what arrived. I do not know when it would not.
- **No failure has been seen on a real Jira.** A failed page, a mismatch, a moved count, a 429: all are shown on the
  made-up Jira or a stand-in for the network, which are my models of it.
- **The real date run matched nothing.** It shows the real Jira accepts the query with a date in it. It does not
  show that the date selects the right items there.
- **The made-up Jira reads a small part of JQL.** A new query that uses `OR` or `in (...)` can only be tried against
  the real sandbox, by a person.
- **Keeping a filter inside its project rests on my reading of JQL.** I refuse what I know can break it. Every item
  that comes back is also checked to be in the project, so a filter that got out would fail the run, after the
  other project had been asked about.
- **The configuration reader takes a small, strict part of YAML.** It refuses some valid YAML, such as a comment
  after a value. The file's header says how to write it.
- **An older result is left in place when a run fails.** The output says it is older. A person who looks only at the
  folder, and not at the output or the exit code, could still take it for today's.
- **The live records have no command line, exit code or date in them.** The result files carry the time.
- **Two small changes were made after the last real runs.** The project's secret scan flagged a made-up value in
  the tests and a variable named `token` in the tool, which holds Jira's page marker. Both were renamed. The tool
  behaves the same, and the tests, planted bugs and made-up records were all run again afterwards. The real runs
  were not.
- **The site fingerprint is a short, unsalted hash of the site's name.** Someone who guesses the name can confirm it.
- **I believe Jira compares a date in the account's time zone.** Not checked.
- **A saved query that names the runner's own email address can never show its output,** because that address is one
  of the things the output is searched for.

## Reflection

*What would make your count wrong while looking right?*

The easy answer is the one in the quest: stopping at the first page. That one is caught, because Jira's own count
disagrees. The answers that worried me more are the ones where the numbers agree. The made-up Jira has a fault where
one page starts an item early. Twenty-eight items arrive and Jira states twenty-eight, and one item is there twice
and another is missing. Comparing two numbers passes that. Only looking at which items came catches it. Then a reader
showed me one I cannot catch at all: an item leaves the query while I am reading and another joins it. Same count
before, same count after, right number saved, wrong set. So a count can be wrong while every check I own says it is
right, and the honest thing was to print that under the word COMPLETE and not to pretend. The other thing that would
do it is me. An old result file sitting in the folder after a failed run looks exactly like today's unless I read
the output. And twice the tests agreed with my own idea of how something works, the date check and the filter check,
and both ideas were wrong. What I rely on now is that the tool says what it checked, and that I read the RESULT line
and not the file.

## Sensitive values

No token, password or cookie is in any file of this quest. The token was typed by the participant into their own
terminal and was not seen by the assistant. Every live output was searched for the token, the email address and
their encoded form before it was shown, and the site's address is replaced by a marker in the saved copies. The
results from the sandbox hold keys, type and status names and times, and no titles, descriptions or people. The
project key SCRUM and a short hash of the site's name do appear. The made-up items are made up.
