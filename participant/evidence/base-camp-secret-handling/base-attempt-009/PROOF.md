# Proof · base-camp-secret-handling

Attempt: `base-attempt-009`

## How this was made

I worked with an AI assistant. I made the decisions; it wrote the tool, the tests, the scripts and the first draft
of the policy, and ran them. Two further AI readers, started fresh, read the work cold. **No person other than me
has read it.** No real credential was used at any point, by me or by the assistant.

## The short version

- **The policy** says where each credential comes from, where it must never be, what the scan can and cannot see,
  and what to do when one leaks: `participant/context/secret-handling.md`.
- **A small tool** uses a credential from an environment variable and masks it in everything it prints.
- **The program's own scanner,** unchanged, finds a planted fake credential and exits with failure, then passes
  once the line is removed, and passes on the whole repository.
- **Both stretch goals are done:** a pre-commit hook that blocks the commit, and a second pattern for a bare Trello
  API key.
- **One thing went wrong on the way and is recorded, not smoothed over:** the first version of the tool printed
  back a credential typed on the command line, and my recording script edited the record so it did not show. See
  "What the independent readers found".

## How the fake credential was made, where it was planted, what the scan reported

**How it was made.** The text `ghp_` followed by the word "example" repeated and cut to 36 characters: 40
characters, the shape of a GitHub token, and plainly not one. It is put together by the script when it runs. It is
not written in any file in the repository, this one included.

**Where it was planted.** In a settings file, `service-config.txt`, in a temporary folder **outside the
repository**, as the third of four lines, the way someone pastes a token in "just to test":

    # settings for the made-up service
    base_url = https://service.example.invalid
    api_token = <the fake token, 40 characters>
    timeout_seconds = 30

The folder is deleted when the script ends. The fake was never planted in a file Git could see.

**What the scan reported** (from `logs/leak-scan.txt`, part 1; TEMP is the temporary folder):

    TEMP/project/service-config.txt:3:13: [github-token] GitHub token — ghp… (40 chars)
    secret-scan: 1 files scanned, 1 finding(s)
    exit status: 1

It gives the file, line and column and the kind of credential. It does not print the value. **Exit status 1 is
failure.** With the line taken out, the same scan of the same file reports `0 finding(s)` and exits with 0.

## The criteria, one by one

| # | Criterion | Status | Where to look |
|---|---|---|---|
| 1 | Credentials come from environment variables or a signed-in CLI, and the policy says which | **Met** | Policy, first table: one row per credential, each marked "environment variable" or "the signed-in `gh` command". `logs/redacted-run.txt` parts 1 and 5: the tool says where it read the value, refuses when the variable is not set, and refuses a credential given on the command line |
| 2 | No tracked file, log or error message contains a credential value | **Met for what was scanned** | `logs/leak-scan.txt` part 3: 2785 tracked files and every not-yet-committed file, no finding. `logs/redacted-run.txt` parts 3, 4 and 5: an error from a service, a crash, and a refused command line, none holding the value. The scan sees known shapes only: see limitations |
| 3 | Output that would include a credential shows it masked | **Met** | `logs/redacted-run.txt` parts 1 to 4: `[REDACTED]` in the plain line, the web address, the `Authorization` header, the base64 form, the service's error and the crash report |
| 4 | A planted fake credential is found by a scan that exits with failure | **Met** | `logs/leak-scan.txt` part 1, quoted above. Exit status 1 |
| 5 | The policy says what to do when a real credential leaks, including rotating it | **Met** | Policy, "When a real credential leaks": eight steps. Rotating is step 2, within the hour and before the rest |
| 6 | The proof contains no real credential, and a reviewer can confirm that from the files | **Met** | `logs/records-scan.txt`: the finished records read back from disk and scanned by both scanners. To confirm by hand: every value in the records is `[REDACTED]` or a description in angle brackets, and the scripts build each fake from the word "example" |

**On criterion 2, plainly.** Two real Trello items left my terminal earlier in this pilot, into a chat and into
screenshots. Neither is in a tracked file, a log or an error message, so the criterion as written holds. They are
leaks by my own policy, they are written up there, and they are **not closed**.

## Where the important artifacts are

| File | What it is |
|---|---|
| `participant/context/secret-handling.md` | The policy |
| `logs/redacted-run.txt` | The command using a credential from the environment, value masked. 15 checks |
| `logs/leak-scan.txt` | Planted fake found, scan fails; removed, scan passes; whole repository clean; what the scan cannot see. 16 checks |
| `logs/pre-commit.txt` | Stretch goal: the hook blocking commits in a throwaway repository. 13 checks |
| `logs/records-scan.txt` | The three records above, scanned as saved. 6 checks |
| `logs/tests.txt` | 29 tests of the tool |
| `logs/planted-bugs.txt` | 27 bugs planted one at a time in a copy of the tool. 27 caught |
| `logs/independent-read.txt` | What the two AI readers found, what changed, what was not re-read |
| `participant/tools/use_credential.py` | The tool: `call` uses the credential, `scan` is the second pattern |
| `participant/tools/tests/test_use_credential.py` | Its tests |
| `participant/tools/pre-commit-secret-scan` | The hook |
| `scripts/record_evidence.py`, `scripts/planted_bugs.py` | The scripts that make the records |
| `../attempt-001/` | Copies of the files the quest asks for by that folder name, with a note |

Paths without `participant/` are inside this attempt folder.

## Stretch goals

**The scan as a pre-commit hook that blocks the commit: done, in a throwaway repository.** `logs/pre-commit.txt`
shows the commit blocked for the fake token, for the fake Trello key, for a file cleaned on disk but not added
again, for a renamed file, and for a file with an awkward name; and stopped with a different message when the scan
could not run. **It is not installed in this repository.** `.git/` is not the assistant's to write to; installing
it is my step. `--no-verify` skips it, and part 8 shows that.

**A second pattern for a format the team uses: done.** A bare Trello API key, 32 hex characters with no prefix. The
program's scanner passes one written in a sentence (`logs/leak-scan.txt` 4a); the second pattern finds it. It runs
beside the program's scanner. **The program's scanner is not changed, and the second pattern is not in CI.**

## How to reproduce the behavior

From the top of the repository, with the project's virtual environment in place:

    python3 participant/evidence/base-camp-secret-handling/base-attempt-009/scripts/record_evidence.py
    python3 participant/evidence/base-camp-secret-handling/base-attempt-009/scripts/planted_bugs.py
    cd participant/tools && ../../.venv/bin/python -m unittest tests.test_use_credential -v

The first rewrites the four records and exits with 0 only if every check passed. Nothing in them needs a real
credential or a network.

## What was tested or validated

- **Read the RESULT line of each record.** All four say ALL CHECKS PASSED: 15, 16, 13 and 6 checks.
- **29 tests pass.** One compares against the program's scanner and needs the project's own Python.
- **27 of 27 planted bugs are caught.** The first run caught 25; the two misses were real gaps in the tests and a
  test was added. The hook has no planted bugs: it is exercised by `logs/pre-commit.txt` only.
- **The checks can fail.** Several did while I worked: the program's scanner flagged a line of my own recording
  script, and the record said FAILED until the line was fixed.

## What the independent readers found

Full account in `logs/independent-read.txt`. The two that matter most:

- **The tool printed back a credential typed on the command line, and the record hid it.** The refusal was Python's
  ordinary one, which repeats what was typed. The recording script then replaced the value in that line of the saved
  output, so the record looked clean. A reader caught it. **The tool was fixed, and the line that edited the record
  was deleted.** The record now checks the output exactly as printed.
- **The policy recommended a check that cannot fail.** It gave a command that scans a folder. The program's
  scanner, given a folder, scans no file and passes. The policy now says so.

**Neither reader has seen the corrected version.**

## A change outside this quest

The whole-repository scan first failed on three lines of an earlier, already verified skill of mine,
`participant/skills/jira-read-assigned/`. None was a credential: a variable named `token`, and a made-up test value
written as an assignment. I chose to fix the lines rather than work around the scanner: the variable is renamed and
the test values are set another way. The skill's behaviour is unchanged and its tests pass. **A verified quest's
files were edited after its review,** and that is said here so it is not found by surprise.

## Remaining limitations

- **A passing scan is about shapes.** A credential with no recognizable shape passes both scans: `logs/leak-scan.txt`
  4b shows it.
- **The scans did not look at:** files Git ignores (`.env`, `local-data/`), old commits, other branches, commit
  messages, pictures, or files that are not text.
- **The program's scanner, given a folder, scans nothing and passes.** That is the program's to fix, not mine.
- **The second pattern is narrow and noisy.** It misses a key in capitals, split, or named on another line, and it
  reports one made-up value in the program's own tests, and checksums.
- **Masking hides the value it was told about,** in the forms it tries. Not a credential the service sends back, not
  one split or re-encoded, not what another program prints.
- **The tool is a demonstration.** It calls a made-up service inside itself. My real skills were not rebuilt on it.
- **The hook is not installed here,** and a hook can be skipped.
- **The two Trello items from earlier in the pilot are not recorded as rotated.**

## Reflection

*If the scan passes, what has it told you, and what has it not?*

It has told me one narrow thing: in the files it actually opened, none of the shapes it knows is present. That is
worth having, because a pasted token is the commonest slip and it has a shape.

It has not told me there is no secret. It did not open ignored files, old commits or pictures. It cannot see a
passphrase of ordinary words, and it passed a bare Trello key until I taught a second pattern to look. It can also
pass having opened nothing at all: handed a folder, the program's scanner read no file and still said it passed, and
my own policy was recommending exactly that command. So the number of files scanned is part of the answer, and I
read it now.

The harder lesson was about my own record. My first tool leaked a value in a refusal message, and my script tidied
that line so the record looked clean. A scan of that record would have passed. A pass tells me about the text in
front of the scanner, not about how that text came to look that way. What keeps a secret out is where credentials
are allowed to be in the first place. The scan is there to catch the day I forget.

## Sensitive values

No real credential, token or key is in this folder, the policy, the tool or the tests. Every credential used is made
up from the word "example" and built when a script runs. No real name, email address, account, site address or
ticket text is here. The two Trello items mentioned are named by kind only.
