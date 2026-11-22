# GitHub: verify a connection

Written by an AI assistant (Claude) at the participant's direction.

## 1. Purpose

This skill checks a GitHub connection before anything trusts it. It says who the connection acts as, what
GitHub reports it may do, which repositories it can see, and whether each repository it is **expected** to
reach can in fact be read.

Its one rule: **"I cannot see this" must never look the same as "there is nothing here".**

It only reads GitHub. Every request is a GET. It never tries a write, not even to see whether one would be
refused. It writes no file.

    python3 participant/skills/github-verify-connection/verify.py --source fake --expect OWNER/NAME [--fake-case CASE]
    python3 participant/skills/github-verify-connection/verify.py --source live --expect OWNER/NAME [--expect OWNER/NAME ...]

`--source fake` uses the made-up GitHub in `fake_github.py`, beside this file. `--source live` uses GitHub. The
check uses the Python standard library only.

## 2. Credentials

A live run needs one environment variable, `GITHUB_TOKEN`. Set it in your own terminal with `read -s`, then
`export` it. It is sent in a request header and is never put in an address. The narrowest token that passes is
a fine-grained one, on the chosen repositories, with **Issues: read-only** and **Metadata: read-only**.

Unset the variable afterwards. Git's GitHub sign-in can pick it up, and a push then fails.

## 3. What you give it

`--expect OWNER/NAME`, once for each repository the connection should be able to read. At least one is
required. Without a named expectation, a lost permission could not be told from nothing being there.

No login is given. The identity is read from the connection.

## 4. What it reports

1. **WHO.** The login and user id GitHub answers "who am I?" with.
2. **WHAT IT MAY DO.** For a classic token, each scope GitHub reports, marked read-only or ALLOWS MORE THAN
   READING. For a fine-grained token, GitHub reports nothing, and the check says so. Then the token's expiry
   date, and the days left by GitHub's clock.
3. **REPOSITORIES GITHUB LISTS.** By full name, with public or private, and what GitHub says the account may do
   there. A public repository is listed whatever the token was given, and the check says so.
4. **EXPECTED REPOSITORIES.** Each one asked for by name, and four reads tried on it: the repository, its
   issues, its pull requests, its files.
   - **REACHABLE**, with what each read found. "issues (0)" means GitHub answered and there are none.
   - **INACCESSIBLE (status N)**. Nothing could be read. No count is given.
   - **REFUSED (status N)** for a single read. If the check needs that read (the repository, or its issues),
     the repository counts as not readable.
   - **MOVED**, when GitHub redirects the name. The check does not follow it.
5. **ONE SAFE READ.** The issues of the first readable expected repository. Only the count is used.
6. **ONLY READS.** Every request made, listed, each one a GET.
7. **SCAN OF THIS OUTPUT.** See section 5.

Exit codes: 0 every expected repository can be read. 1 the check could not be made, for example because the
token was rejected. 3 an expected repository cannot be read, or the output had to be redacted.

## 5. The credential and the output

Nothing is printed as the check runs. Every line is held until the end, scanned for the token's own value and
for anything shaped like a GitHub token, and only then printed. If either is found it is replaced with
`[REDACTED]`, the run says so, and the exit code is 3.

## 6. Names in the output

The check prints repository full names, because that is what it is for. On a real account those names can be
private. Do not commit or share a live run's output without masking them.

## 7. Tests

    python3 -m unittest discover -s participant/skills/github-verify-connection/tests -v

Every test runs against `fake_github.py`. None contacts GitHub.

## 8. What it does not do

See `participant/context/github/verify-notes.md` for the full list. In short:

- It does not change anything in GitHub, and so it cannot say whether the token could.
- It cannot say why a repository is inaccessible: GitHub gives the same answer for "does not exist" and "may
  not be seen".
- It checks only the repositories named with `--expect`.
- It keeps no memory between runs, and does not run on a schedule by itself.
