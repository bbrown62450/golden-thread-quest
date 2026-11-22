# PROOF: Verify Authenticated Identity, Scopes, and Repository Access

Quest `github-verify-connection`, attempt `github-attempt-003`.

## How this was made

The check, its tests, the made-up GitHub, the notes and this document were written by an AI assistant (Claude)
at the participant's direction. The participant chose the design in two decisions: build against a made-up
GitHub and run once for real; and give the check the repositories the connection is expected to reach, so
that one it cannot read fails the check. The participant made the token, made a second private repository for
the denied case, and ran both real verifications in their own terminal. The assistant never saw the token and
sent no request to GitHub.

Words used below: **recorded** means a saved log shows it. **tested** means an automated test checks it.
**observed** means it was seen on real GitHub. **not assessed** means nobody checked it.

## Approach

One script, `participant/skills/github-verify-connection/verify.py`. It asks GitHub who the connection is,
reads what GitHub reports about the token, lists the repositories GitHub shows it, and then asks by name for
each repository it was told to expect, trying four reads on each. Every request is a GET, it writes no file,
and it holds its whole output back to scan it before printing.

The choice that matters is the named expectation. A check that only lists what is reachable cannot say that
something is missing, because it does not know what should be there. With `--expect`, a repository that
cannot be read is a failure with its own word, INACCESSIBLE, and an exit code of 3.

## How the check would reveal a permission lost next week

This is the quest's scenario: a token loses access to one repository, and a sync returns nothing for it for a
week, because an empty answer looks like an answer.

Run before each sync, with the repositories that sync reads given as `--expect`, the check fails on the first
run after the change (criterion 4):

- **The repository was taken out of the token.** Recorded in part 2 of `logs/denied-run.txt`, "a week later":
  the repository that was REACHABLE with 12 issues is now "INACCESSIBLE (status 404). Nothing in it could be
  read. This is NOT an empty repository", and the exit code is 3. It is not given a count of 0. Observed on
  real GitHub in run 2 of `logs/live-runs.txt`, with a private repository the token was never given.
- **The repository stayed and the permission to read issues went.** Recorded in part 3: "issues: REFUSED
  (status 403) ... This is not the same as having no issues", exit code 3. Observed for pull requests and
  files, which the real token was not given: both REFUSED (status 403).
- **The token expired.** Recorded in part 4 of `logs/verify-run.txt`: the check stops, exit code 1, and says
  "That is not the same as the connection being fine". Every run before that prints the expiry date and the
  days left (criterion 2), so this one can be seen coming. Observed: "7.0 days from now by GitHub's clock".

What it would **not** reveal is in the notes, and the largest gap is this: a fine-grained token that gains
write permission next week looks exactly the same to this check, because the check never tries a write and
GitHub does not report a fine-grained token's permissions.

## The criteria, one by one

| # | Criterion | Status | Where |
|---|---|---|---|
| 1 | The identity is read from the connection, not typed in | recorded, tested, observed | `verify-run.txt` part 1; tests `Who`; both real runs. No login is in `verify.py` or its arguments |
| 2 | The scopes or permissions are reported | recorded, tested, observed for a fine-grained token | `verify-run.txt` parts 1 and 2; tests `Scopes`. A classic token's scopes were not observed on real GitHub |
| 3 | The reachable repositories are listed by full name | recorded, tested, observed | `verify-run.txt` parts 1 and 2; tests `Reachable`; real runs, where the names are masked in the saved copy |
| 4 | A repository outside scope is reported as inaccessible, not as empty | recorded, tested, observed | `denied-run.txt` part 1: an inaccessible repository and a truly empty one, side by side; tests `Expected`; real run 2 |
| 5 | No write operation is attempted | recorded, tested, observed | every run lists its requests, all GET; tests `OnlyReads` |
| 6 | The credential appears in no output | recorded, tested, observed | `verify-run.txt` parts 1 and 3; tests `Credential`; real runs: "Nothing was found" |
| 7 | The notes say what the check does not prove and which scope is broader than needed | written | `participant/context/github/verify-notes.md` |

## Artifacts

| Required item | File |
|---|---|
| The verification run | `logs/verify-run.txt`, 20 checks |
| The denied run | `logs/denied-run.txt`, 17 checks |
| The notes | `participant/context/github/verify-notes.md` |
| This narrative | `PROOF.md` |

Also here: `logs/live-runs.txt` (the two real runs, masked), `logs/tests.txt` (51 tests),
`logs/planted-bugs.txt` (26 planted bugs), `scripts/record_evidence.py` and `scripts/planted_bugs.py`. The
skill is `participant/skills/github-verify-connection/`: `SKILL.md`, `verify.py`, `fake_github.py`,
`tests/test_verify.py`.

The two required logs come from the made-up GitHub. That is why they can show repository full names, as
criterion 3 asks. The recording script does not take the check's word: it reads from the made-up GitHub what
the token was granted and how many issues a repository holds, counts the request lines itself, and scans each
output with a pattern of its own.

## What the real runs changed

The first real run showed that the made-up GitHub was wrong in one respect, and the check was missing a
warning because of it.

- The assistant had assumed that GitHub's list for a fine-grained token holds only the repositories the token
  was given. On real GitHub it held nine: the one given, and all eight public repositories of the account.
- The second repository named as "outside the token" turned out to be public, so it was REACHABLE. Any token
  can read a public repository.

The made-up GitHub now behaves this way, and the check now says: "A public repository is listed, and can be
read, whatever the token was given. Being listed here does not show that the token was granted it". One test
was added. The participant then made a private repository the token was not given, and run 2 shows it as
INACCESSIBLE.

Run 1 is kept in `logs/live-runs.txt` as it was, without that note, because it is what was seen.

## Stretch goals

- **Run the check on a schedule and report a change:** not done. The notes say how its exit code would be used.
- **List what a fine-grained token could restrict:** done, in the notes, from the assistant's knowledge and
  the token forms the participant filled in. Not checked against GitHub's documentation.

## Reproduce

    python3 -m unittest discover -s participant/skills/github-verify-connection/tests -v
    python3 participant/evidence/github-verify-connection/github-attempt-003/scripts/record_evidence.py
    python3 participant/evidence/github-verify-connection/github-attempt-003/scripts/planted_bugs.py

None of these contacts GitHub. The third changes `verify.py` while it runs and restores it.

## What was tested

| What | Result |
|---|---|
| Automated tests | 51, all pass (`logs/tests.txt`) |
| Planted bugs | 26 put into `verify.py` one at a time. Every one made at least one test fail (`logs/planted-bugs.txt`) |
| Recorded checks | 20 and 17, all pass |
| Real runs | 2. Run 1 ended "every expected repository can be read". Run 2 ended "1 expected repository CANNOT be read", as intended |

The planted bugs include the quest's own scenario: a refused read reported as a read that found nothing.

Two faults were found while building, both in the assistant's tests and not in the check: one compared lines
without trimming spaces, and one looked for the word PUT and found it inside OUTPUT.

## What could not be done, and limitations

- **Whether the token can write: not assessed, by design.** See above and the notes.
- **A classic token on real GitHub: not assessed.** The scope report was tested against the made-up GitHub
  only. Which scopes count as read-only is the assistant's own rule.
- **A permission actually lost over time on real GitHub: not assessed.** What was observed is a repository the
  token never had, which GitHub answers the same way.
- **A rejected or expired token, a renamed repository, and a rate limit on real GitHub: not assessed.**
- **The exit codes of the real runs were not saved.** They are inferred from the RESULT lines.
- The check cannot tell a repository that does not exist from one it may not see. It says so each time.
- The token-expiry header is read as GitHub sent it in the real runs. Its name and format in the made-up
  GitHub were the assistant's assumption, and the real runs matched it.

## Reflection

*Which scope would you remove first, and what would break?*

Pull requests, read-only. I added it to the tokens for the two sync quests so GitHub would show the pull
request that mentions an issue. For this quest I left it off, and the real run answered the second half of
the question for me: the check reported "pull requests: REFUSED (status 403)", said it was not needed, and
passed. So for verifying a connection, nothing breaks.

What would break is elsewhere. The assigned-issues sync would probably lose its links from issues to pull
requests, and I would want it to say "refused", not quietly show no links. I have not tried that, so I do not
know which it does. That is the same failure this quest is about, one level down: a missing permission that
looks like missing data.

What surprised me is what I could not remove. I assumed a token limited to one repository could see one
repository. It listed nine, because every public repository is visible to any token. Narrowing a token limits
what it can reach in private. It does not make the public part of the account smaller, and the list GitHub
gives back is not a list of what I granted.

## Sensitive values

- The token was typed by the participant into their own terminal and was never shown to the assistant. It is
  in no file. It is limited to one private sandbox repository, read-only for issues, and expires in 7 days.
- The check writes no file. Its real output was saved by the participant to a scratch file outside the
  repository. `logs/live-runs.txt` is a masked copy: the login, user id, repository ids and the names of the
  account's other public repositories are replaced.
- The output of every run was scanned for the token before printing, and nothing was found.
- Everything else in this attempt comes from the made-up GitHub. Its logins, such as `robin-fixture`, are
  invented. The token-shaped values used to test the scan are made up in the tests and are not tokens.
