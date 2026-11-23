# PROOF: Save One Issue and Its Context as Local Markdown

Quest `github-read-issue`, attempt `github-attempt-004`.

## How this was made

The skill, its tests, the made-up GitHub, the recording scripts and this document were written by an AI
assistant (Claude) at the participant's direction. The participant chose the design in four decisions: build
against a made-up GitHub and run once for real; keep every field, but keep people by login only and list what
was left out; store the body word for word between marker lines with a checksum; and save the comments with
the issue. The participant edited the sandbox issue, made the token, and ran the real retrievals in their own
terminal. The assistant never saw the token and sent no request to GitHub.

Words used below: **recorded** means a saved log shows it. **tested** means an automated test checks it.
**observed** means it was seen on real GitHub. **not assessed** means nobody checked it.

## Approach

One script, `participant/skills/github-read-issue/read_issue.py`. It makes two kinds of request, both GET: the
issue, and its comments. It writes one Markdown file.

The rule it follows: what GitHub sent is either in the file, or on a list in the file that says it was left
out and why. The file has six parts, in this order:

1. front matter, one line per field, each value written as JSON;
2. "Fields kept in full": fields the format knows that have no line of their own, such as label records;
3. "Preserved fields": every field the format does **not** know, as GitHub sent it;
4. "Comment fields";
5. "Left out on purpose": API addresses, and all of each person's record but the login;
6. "Content from GitHub": the body and each comment, word for word.

What the skill wrote comes first and what other people wrote comes last, so text in a body cannot stand in for
the file's own parts.

Before it writes, the skill reads its own text back into fields and compares it with GitHub's answer, value by
value. If a value is in neither the file nor the left-out list, it stops and writes nothing.

## How the formatting was tested

"Survive" is tested as: **the characters are the same**, not "it looks about right".

1. **The whole body, compared.** The body is cut back out of the saved file and compared, character for
   character, with the body the made-up GitHub sent. 1,755 characters, the same SHA-256. Recorded in part 3 of
   `logs/fidelity-check.txt`. The recording script uses its own reader for this, not the skill's.
2. **The three structures, as whole lines.** The 5 lines of the task list, the 5 lines of the table and the 14
   lines of the code block are looked for in the file together, in order, each exactly as sent. The log shows
   them with their line numbers in the file.
3. **The things that tidying destroys.** Each has its own check and its own test: which boxes are ticked; a box
   indented under another; an empty table cell and an escaped pipe; the blank line and the tab inside the code
   block; two spaces at the end of a line; blank lines at the start and end of a text; text that is not plain
   ASCII; Windows line endings on disk; "no body" against an empty body.
4. **A body made to be hard.** As the hint asks. The made-up body also holds a code block that is never
   closed, a tilde fence, an HTML comment, a made-up front matter, a heading with the same name as one of the
   file's own sections, and a made-up end marker inside the code block.
5. **Bugs put in on purpose.** The quest's scenario, a flattened body, was planted in the skill, and so were
   trimming line ends, trimming blank lines, changing line endings and storing no body as an empty one. Each
   made tests fail (`logs/planted-bugs.txt`, bugs F to J).
6. **A real issue.** The participant pasted a task list, a table and a code block into a sandbox issue. The
   saved file has them line for line, including the blank line in the code block. Observed.

What this does not show: how the saved text **renders**. No Markdown renderer was used. The claim is that the
characters are kept, so anything that rendered them on GitHub has the same characters to render.

## The criteria, one by one

| # | Criterion | Status | Where |
|---|---|---|---|
| 1 | Every field returned appears in the file | recorded, tested, observed, with a stated exception | `fidelity-check.txt` part 1: all 31 fields and all 187 single values are in the file or on its left-out list. Tests `EveryField`. Real run: 34 fields, the same check passed inside the skill. **Exception:** API addresses and all of a person's record but the login are left out, and listed in the file. See below |
| 2 | The task list, table and code block survive | recorded, tested, observed | `fidelity-check.txt` part 3. Tests `Formatting`. Real run, read by eye |
| 3 | Identified by repository and number, node identifier kept | recorded, tested, observed | Front matter and file name. Tests `Identity`: a pull request, a moved issue and a file holding another node ID are refused |
| 4 | An unknown field is kept in a preserved section | recorded, tested, observed | `fidelity-check.txt` part 2. Tests `Unknown`. Real run: five fields the assistant had not listed were preserved |
| 5 | Retrieving again leaves an unchanged file byte-identical | recorded, tested, observed | `issue-run.txt` part 2: same bytes, and not even written again. Tests `Unchanged`. Real runs: two separate retrievals gave the same 6,430 bytes |
| 6 | Issue text is stored as content and never executed | recorded, tested, observed in part | `fidelity-check.txt` part 4. Tests `ContentNotInstructions`. Real run: the line is in the body and 2 GET requests were made |
| 7 | No credential or private personal data stored | recorded, tested, observed in part | `fidelity-check.txt` part 5. Tests `NothingPrivate`. See "Sensitive values" |

### Criterion 1 against criterion 7

GitHub repeats a full record for every person: a user id, a node id, a picture address and about fifteen
other fields. In the made-up issue that is 114 of the 187 values. Keeping them would meet criterion 1 to the
letter and break criterion 7.

The participant's decision: keep each person by **login**, leave the rest out, and say so in the file. The
file's "Left out on purpose" section lists every place this was done, with the names of the fields left out.
The recording script checks that nothing is on that list except people's records and API addresses. So
criterion 1 is met in this sense: every field is in the file or named in it as left out. A reviewer who reads
criterion 1 as "every value, with no exception" should count it as partly met.

## Artifacts

| Required item | File |
|---|---|
| The saved issue | `participant/context/github/issues/issue-sample.md` |
| The run log | `logs/issue-run.txt`, 18 checks |
| The fidelity log | `logs/fidelity-check.txt`, 42 checks |
| This narrative | `PROOF.md` |

Also here: `logs/live-runs.txt` (the real runs, masked), `logs/tests.txt` (84 tests), `logs/planted-bugs.txt`
(42 planted bugs), `scripts/record_evidence.py` and `scripts/planted_bugs.py`. The skill is
`participant/skills/github-read-issue/`: `SKILL.md`, `read_issue.py`, `fake_github.py`,
`tests/test_read_issue.py`.

`issue-sample.md` and the two required logs come from the made-up GitHub, so that nothing real is shared. The
issue in it, its repository and its three people are invented.

## What the real runs showed

- GitHub returned **34 fields**, where the made-up GitHub sends 31. **Five were not known to the format**:
  `issue_dependencies_summary`, `issue_field_values`, `pinned_comment`, `sub_issues_summary` and `type`. The
  assistant had put one of them in the made-up GitHub and had not thought of the other four. The comment had
  two more, `minimized` and `pin`. All seven are in the saved file. This is criterion 4 met by fields nobody
  planned for, which is the case the criterion is about.
- Two retrievals a few minutes apart, into two folders, gave files that are the same byte for byte.
- One expectation was wrong: the assistant expected a body typed into GitHub's web page to have Windows line
  endings. The pasted body had none. Windows line endings are tested against the made-up GitHub only.
- The skill did not need changing after the real runs.

## Stretch goals

- **Preserve reactions as counts:** done. They are in "Fields kept in full", for the issue and each comment.
  Recorded in `fidelity-check.txt` part 1. On the real issue every count was 0.
- **Round-trip the Markdown back to the issue and compare:** done, twice over. The skill does it on every run
  before writing. `fidelity-check.txt` part 6 does it again from the file on disk and compares with what the
  made-up GitHub sent.

## Reproduce

    python3 -m unittest discover -s participant/skills/github-read-issue/tests -v
    python3 participant/evidence/github-read-issue/github-attempt-004/scripts/record_evidence.py
    python3 participant/evidence/github-read-issue/github-attempt-004/scripts/planted_bugs.py

None of these contacts GitHub. The second writes `issue-sample.md` again, with the same bytes. The third
changes `read_issue.py` while it runs and restores it.

## What was tested

| What | Result |
|---|---|
| Automated tests | 84, all pass (`logs/tests.txt`) |
| Planted bugs | 42 put into `read_issue.py` one at a time. Every one made at least one test fail (`logs/planted-bugs.txt`) |
| Recorded checks | 18 and 42, all pass |
| Real runs | 2 kept, both exit code 0. One wrote the file, one found it unchanged |

Faults found while building:

- In the skill: an issue that had been transferred was stopped with the wrong reason, "another number", because
  the checks were in the wrong order. Found by running it, and fixed.
- In the assistant's tests: four, on first run. One searched the code for a word that is also part of an
  ordinary function name. Three expected the wrong thing of the left-out list and of the file's own wording.
- In the recording script: one sentence counted a person's addresses wrongly.

## What could not be done, and limitations

- **How the saved Markdown renders: not assessed.** See "How the formatting was tested".
- **Personal data written in free text: not detected.** The scan looks for things shaped like a credential or
  an email address. A person's name, phone number or address written in a body is kept, and nothing warns.
  The patterns are the assistant's own.
- **A login is kept.** Whether a login counts as private personal data is a judgment. The participant chose to
  keep it, because it is what GitHub shows on the issue page. In the handed-in file every login is invented.
- **Text that trips the scan is kept, not removed.** The file is still written, with a warning and exit code
  3, because changing the text would make the copy unfaithful. Such a file must not be shared until read.
- **The very first real run's output was lost.** It was overwritten by the second. The "first write" kept in
  `logs/live-runs.txt` is a later run into an empty folder.
- **A real issue that changes between runs: not assessed.** Recorded against the made-up GitHub only.
- **On real GitHub, not assessed:** a pull request, a transferred or deleted issue, a rejected token, a rate
  limit, more than 100 comments, labels, a milestone, several people, reactions above zero, and text shaped
  like a credential.
- **Whether the real issue was left open** was not looked up after the runs. The skill has no code that could
  close it, and the state read during the run was open.
- **A new field inside a known record** (for example inside a label) is kept, but is not reported as new.
- **The timeline is not read:** who labelled, closed or linked the issue, and when. Pictures and attached
  files are not downloaded.
- The skill's reader, the recording script's reader and the tests were all written by the same assistant. They
  were written apart, and can still share a blind spot.

## Reflection

*What would you lose if you saved only the title and the body?*

I would lose everything that says what the text **means right now**. The body of my made-up issue has a box
that says the export must keep the customer reference. With only the title and body I cannot tell whether the
issue is open or closed, who it is assigned to, which sprint it belongs to, or when it last changed. The same
words mean "do this" on an open issue and "this was done" on a closed one.

I would lose the comments, which is where the answer usually is. In the sample the body states the problem.
A comment says it was reproduced, and a later one says it is fixed in a branch but not merged.

I would lose the identity. A title can be edited and two issues can share one. The repository, number and
node ID are what let a second run know it is looking at the same issue, and what stopped the skill from
overwriting a file that held a different one.

What surprised me was the part I would lose without knowing. Real GitHub sent five fields nobody had listed,
such as whether the issue is blocked by another one. A "title and body" copy would drop those silently, and so
would any copy built from a fixed list of fields. That is why the preserved section matters more than it
looked when I read the criteria.

The other thing I did not expect is that "keep everything" had a limit. Most of what GitHub sent was the same
few people's records, repeated. I chose to keep logins and leave the rest out, and to write that down in the
file. So the honest answer has two sides: saving too little loses the meaning, and saving everything keeps
things I should not hold.

## Sensitive values

- The token was typed by the participant into their own terminal and was never shown to the assistant. It is
  in no file. It is limited to one private sandbox repository, read-only for issues, and expires in 7 days.
- The real issue files were written to scratch folders outside the repository and are not handed in.
  `logs/live-runs.txt` is a masked copy of what the runs printed: the owner's login and the issue's node ID
  are replaced.
- The skill prints numbers, the node ID, checksums and field names. It never prints a title, a body, a label,
  a login or a comment. Tested.
- Every saved file is scanned for the token's own value. In the real runs nothing was found.
- Everything else in this attempt comes from the made-up GitHub. Its logins, such as `robin-fixture`, are
  invented. The credential-shaped and email-shaped text used to test the scan is put together inside the
  made-up GitHub when it runs, is written out in no file here, and is not real.
