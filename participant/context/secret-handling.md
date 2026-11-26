# Secret handling: where credentials come from, where they must never be, and what to do when one leaks

This is my policy for this repository. It covers the credentials my quest work uses.

Words used here:

- **Credential:** anything that lets a program act as me. A token, an API key, a password, a session cookie.
- **Rotate:** make the old credential stop working at the service that issued it, then make a new one.
- **Environment variable:** a named value a terminal holds in memory and hands to the programs started from it.
- **Tracked file:** a file Git has been told to keep. **Staged:** added with `git add`, waiting for the next commit.
- **The agent:** the AI assistant that works in this repository with me.

## Where each credential comes from

**Two sources: a command that is signed in, or an environment variable.** Never a file Git can see, never a
command line, never a chat. The one exception is at the end of the next section, and I have not used it.

| Credential | Used for | Where it comes from | How it gets there |
|---|---|---|---|
| GitHub sign-in | `gh`, and pushing my branch | **The signed-in `gh` command.** It keeps its own sign-in outside this repository | I ran `gh auth login` once, myself |
| `GITHUB_TOKEN` | the GitHub skills, when they call the API directly | **An environment variable**, for one terminal session | I set it by hand: `read -s GITHUB_TOKEN`, paste, then `export GITHUB_TOKEN` |
| `JIRA_API_TOKEN`, with `JIRA_EMAIL` and `JIRA_BASE_URL` | the Jira skills | **Environment variables**, for one terminal session | The same way, by hand |
| `TRELLO_API_KEY` and `TRELLO_API_TOKEN` | the Trello skills | **Environment variables**, for one terminal session | The same way, by hand |
| `GTQ_DEMO_TOKEN` | the demonstration in this quest only | **An environment variable** | A made-up value. It must contain the word "example" or the tool refuses it |
| The reviewer's sign-ins | the automatic review | Not mine. They are on the review server, in its own logins | I never hold them |

- **`read -s`** takes what I paste without showing it and without putting it in the shell's history.
- **A variable lives as long as its terminal.** When the job is done I run `unset` on it, or close the terminal. A
  token is made for one job and deleted at the service afterwards.
- **An exported variable can be read by every program started from that terminal.** That includes the agent, if it
  runs commands there: one `env` would print it. So I export a credential **only in a terminal the agent does not run
  commands in.** The agent gives me a command. I run it in my own terminal. The agent reads the saved output, which
  has the credential and the site's address taken out.
- **The agent is not meant to hold a credential, and I do not give it one.** That is a rule I keep, not a lock: see
  "What has happened in this pilot" for where it slipped.
- **The email address and the site address are not secrets, and are still private.** They are kept out of evidence.

## Where a credential must never appear

| Place | Why |
|---|---|
| Any file Git tracks, or could track: everything under `participant/`, and the program's own files | A commit is permanent and is pushed to a server. Deleting the line later leaves it in the history |
| `.env` files inside `participant/` | `participant/` is committed whole by `gtq hand-in` |
| A command line: `tool --token VALUE`, or `NAME=VALUE tool` | The shell keeps it in its history, and any program can list running commands |
| A log, a saved output, a screenshot, a trace | Evidence is committed, and a screenshot cannot be scanned for text |
| An error message | Services and libraries repeat what they were sent. A program must mask before it prints |
| A URL, as `?token=VALUE` | URLs are logged by every server and proxy on the way |
| What is left on the terminal's screen | Scrollback is kept, can be saved, and gets copied into chats and screenshots |
| A chat with an AI assistant or with a person, a ticket, an email | It has left this computer, and I do not control where it is kept |
| A test or a fixture | Tests are committed. A made-up value is built when the test runs |

**The one exception: if a tool insists on a file,** the only place is `.env` at the top of the repository, which Git
ignores, written by me and never by the agent. I have not needed one.

## What the demonstration tool does so that a credential is not printed

This describes `participant/tools/use_credential.py`. It is what I want from any program that holds a credential. I
have **not** checked my earlier skills against every point.

- It reads the credential from the environment, and refuses if it is not set.
- **Every line it prints goes through one masking step,** which replaces the value wherever it appears: as it is,
  URL-encoded, and base64-encoded as a sign-in header holds it. The mark is `[REDACTED]`.
- That covers a debugging print of a request, an error from a service that repeats the credential, and a crash.
- **It never repeats a command line it did not understand.** If I type a credential there by mistake, the usual
  complaint would print it back.

**What masking cannot do.** It hides the value it was told about. It does not know a credential the service sends
back, one typed on the command line, or one that was cut across two lines, reversed, hashed or encoded another way.
It does not cover what another program or a library prints by itself.

## What the scan sees, and what it does not

The scan is the program's own: `make secret-scan`, which runs `tools/secret_scan.py`. It runs in the program's CI
(the checks that run on the server after a push), and the application runs the same patterns over every evidence
folder before a hand-in.

**It sees shapes.**

- Credentials with a known look: a GitHub, GitLab, Slack, Google, Anthropic, OpenAI, Stripe, npm, Trello or
  Atlassian token; an AWS key; a private key block; a JSON web token.
- A name that says "secret" next to a value: `password = ...`, `api_key: ...`, `--token ...`, a credential in a URL.

**It does not see:**

- **A credential with no recognizable shape.** A door code, a passphrase of ordinary words, a short PIN.
- **A shape it was not taught.** A bare Trello API key is 32 hex characters with no prefix. In a sentence, or in a
  field named just `key`, the program's scanner passes it. I added a second pattern for it,
  `participant/tools/use_credential.py scan`. It runs beside the program's scanner, is not part of it, and **does
  not run in CI.** It misses a key in capitals, a key whose name is on another line, and a key cut in two. It also
  reports things that are not keys, such as an MD5 checksum on a line that says "Trello".
- **Anything in a picture.** A token in a screenshot is invisible to it.
- **Files that are not text:** an archive, a spreadsheet, a compiled file.
- **Files Git does not track yet.** With no path given, it looks at tracked files. A new file is not looked at until
  it is added, unless it is named.
- **A folder, if a folder is what it is given.** `tools/secret_scan.py SOME-FOLDER` scans no file and still passes.
  It must be given file names. The line it prints says how many files it scanned: **read that number.**
- **Files Git ignores:** `.env`, `local-data/`. These are where a real credential is most likely to be.
- **A file's history, other branches, and commit messages.** It looks at the files as they are now, on this branch.
- **Anything before it runs.** CI runs after a push. By then a credential is already on the server.
- **Whether a match is real.** It reported three findings in an earlier skill of mine that were not credentials: a
  variable called `token`, and a made-up test value.
- **Private things that are not credentials:** a real name, a real ticket's text.

**So a passing scan means: none of the shapes it knows is in the files it looked at.** It does not mean there is no
secret. The rules above are what keep a secret out. The scan is what catches a slip.

**A pre-commit hook** is a script Git runs before each commit; if it fails, Git makes no commit. One that runs both
scans on the staged files is in `participant/tools/pre-commit-secret-scan`. It is not installed in this repository
by default: a person copies it into `.git/hooks/`. It is a reminder, not a lock: `git commit --no-verify` skips it,
and Git does not run it for a rebase, a cherry-pick or a merge that completes by itself.

## When a real credential leaks

A leak is any time a real credential has been somewhere on the "never" list, **even for a moment, even if nobody
seems to have seen it.**

1. **Stop the task.** Make no new commit and no push that carries the value. Do not tidy up first.
2. **Rotate it at the service, now.** Revoke the leaked credential where it was issued (GitHub, Atlassian, Trello),
   then make a new one. This is the only step that makes the leaked value harmless. **Within the hour, and before
   any step below.** If other credentials were in the same file, message or screenshot, rotate those too.
3. **Check the old value is dead.** Use the service's own page: the old token is no longer listed. Do not test it
   by pasting it anywhere.
4. **Tell the program owner** what kind of credential leaked, where it went, and when. Never the value. Tell them
   even if it was rotated within a minute. In this pilot the program owner is me, so that tells nobody new: I also
   tell the maintainers of the program's repository, because my branch is pushed to a pull request there.
5. **Find everywhere it went.** The file, the commit, the push, the pull request, a log, a screenshot, a chat, the
   terminal's scrollback. If it was pushed, it is on a server and in every copy made since.
6. **Take it out where it can be taken out.** Remove it from the working files, and then commit that removal.
   Delete the chat message or the screenshot where the service allows it. Clear the terminal.
   **Removing it does not make it safe:** the earlier commit still holds it, and a chat may keep a copy. Rewriting
   history is the program owner's decision, and is never a substitute for step 2.
7. **Look at what the credential could do** between the leak and the rotation: check the service's own activity log.
8. **Write down what happened,** without the value: what kind of credential, where it went, when it was rotated,
   what will be done differently. The record goes in this file, under the next heading.

**Never** paste a real credential anywhere "to see if it works", and never commit one "just briefly".

### What has happened in this pilot

This policy was written after the fact, and two things earlier in my own pilot are leaks by the definition above:

- A Trello API key was pasted into a chat with the AI assistant.
- A Trello application secret appeared in screenshots shown to the assistant.

Neither was committed, and the assistant did not use or repeat either. They still left my terminal.

**This is not closed.** By step 2 both should have been rotated within the hour, and they were not: the policy did
not exist yet. Both are to be rotated at Trello, by me. **Whether that has been done is not recorded here,** and
until it is, steps 2, 3, 7 and 8 are open for both.

## Checking this policy is being followed

    make secret-scan                                                 the program's scan of every tracked file
    .venv/bin/python tools/secret_scan.py -- FILE [FILE ...]         the same, on named FILES. Not a folder: see above
    python3 participant/tools/use_credential.py scan FILE-OR-FOLDER  the second pattern. This one does look into a folder
    git status                                                       read before every hand-in: what is about to be committed?
