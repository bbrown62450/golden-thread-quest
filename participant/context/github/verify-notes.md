# Notes on verifying a GitHub connection

Written by an AI assistant (Claude) at the participant's direction, for the quest `github-verify-connection`.
The check is `participant/skills/github-verify-connection/verify.py`. These notes say what its result does and
does not mean.

## What the check does not prove

1. **That the token cannot write.** The check never tries a write, because trying one is the thing it must not
   do. For a fine-grained token, GitHub does not report the token's own permissions, so the check cannot read
   them either. A token that passes this check could still be able to push, close issues or delete things.
   Only the token's own page in GitHub's settings shows that.
2. **That a listed repository was granted to the token.** GitHub's list for a token holds the repositories the
   token was given **and every public repository of the account**. A public repository can be read by any
   token. Seen on real GitHub: a token given one repository listed nine. So the list shows what can be seen,
   not what was granted.
3. **Why a repository is inaccessible.** GitHub answers 404 both for a repository that does not exist and for
   one the connection may not see. The check reports "INACCESSIBLE (status 404)" and says the two cannot be
   told apart. A mistyped name and a lost permission look the same.
4. **Anything about repositories that were not named.** The check tries reads only on the repositories given
   with `--expect`. A repository a sync depends on, and that nobody named, is not checked.
5. **That every read a sync needs will work.** The check tries four reads on each expected repository: the
   repository, its issues, its pull requests, its files. It does not try comments, timelines, search, or
   anything else. It reads one page of issues, not all of them.
6. **That the result will still be true later.** It is true at the moment of the run. A permission can be
   taken away a minute afterwards. The check reports the token's expiry date, which is the one future change
   it can see coming.
7. **That what "the account may" do is what the token may do.** The list repeats what GitHub says the account
   may do in each repository: read, write, administer. That is the person's access. The token's is narrower,
   and GitHub does not state it there. The check says so on the line below.
8. **That the identity is the right one.** The check reports who the connection acts as. Whether that is the
   account the work should be done as is for a person to judge.

## Which scopes are broader than needed

The check needs the token to read a repository's own record and its issues. Nothing else.

**For a fine-grained token**, which is the kind used here:

| Permission | Needed by this check | Note |
|---|---|---|
| Metadata: read-only | yes | GitHub adds it by itself |
| Issues: read-only | yes | the one safe read |
| Pull requests: read-only | **no** | broader than this check needs. The earlier sync quests asked for it, so that a pull request mentioning an issue would be shown |
| Contents: read-only | **no** | broader than needed. Nothing in these quests reads files |
| any permission set to read and write | **no** | broader than needed, always. Every skill here only reads |
| "All repositories" as the repository access | **no** | broader than needed. Only the repositories a sync reads should be chosen |

The real token made for this quest had Issues and Metadata only. The check reported pull requests and files
as REFUSED (status 403), and still passed, which shows those two are not needed by it.

**For a classic token**, GitHub reports the scopes, and the check flags each one that allows more than reading:

- `repo` is the broadest and the most common. It is the only classic scope that reads private repositories,
  and it also allows writing to all of them. A classic token cannot be given read-only access to a private
  repository. This is the main reason to use a fine-grained token.
- `delete_repo`, `workflow`, `write:org`, `admin:org` and the like are never needed by anything here.
- A scope that begins `read:` is read-only.

The check treats a scope as read-only only when it begins with `read:` or is `repo:status`. That rule is the
assistant's own and is deliberately strict: a scope it does not know is flagged as broader than needed.

## How a changed permission would be noticed

The check is given the repositories the connection is **expected** to reach, by name. It asks for each one.

- **A repository taken out of the token:** the next run reports it as INACCESSIBLE (status 404) and exits with
  code 3. It does not report "0 issues".
- **The permission to read issues taken away:** the next run reports "issues: REFUSED (status 403)", says that
  this is not the same as having no issues, and exits with code 3.
- **The token expired or revoked:** the next run stops with "GitHub rejected the token (401)", exits with code
  1, and says that this is not the same as the connection being fine. Each run before that prints the expiry
  date and the days left.
- **The repository renamed or transferred:** the next run reports it as MOVED and exits with code 3.
- **A permission added, or widened to read and write:** for a classic token the new scope appears in the list
  and is flagged. **For a fine-grained token this is not noticed.** GitHub does not report it and the check
  does not try a write. This is the largest gap.
- **A repository added to the token:** it appears in GitHub's list. The check does not compare with an earlier
  run, so nobody is told unless they read the list.

A change is noticed only when the check is run. It keeps no memory of earlier runs: the expectation is in the
command, written down, not remembered. So it works from the first run, and it finds access that was already
missing when it first ran.

## Running it on a schedule

Not set up. The check is made for it: it writes no file, needs only `GITHUB_TOKEN` and the list of expected
repositories, and its exit code says the outcome (0 fine, 1 could not check, 3 something expected cannot be
read). A scheduler would run it before each sync and stop the sync on any code but 0. A token for a scheduled
job has to be stored somewhere, and where it is stored matters more than the check does.

## What a fine-grained token could restrict

From the assistant's knowledge of GitHub, and from the token forms the participant filled in. Not checked
against GitHub's documentation.

- **Which account owns the resources:** one person or one organization.
- **Which repositories:** public ones only, all of the owner's, or a chosen list. The tokens here were given
  one repository.
- **Which kind of thing, one by one:** issues, pull requests, contents, metadata, actions, and many others,
  each set separately.
- **How much:** no access, read-only, or read and write, for each kind.
- **How long:** an expiry date. The tokens here expire after 7 days.
- An organization can also require approval before a fine-grained token may reach its repositories.

What it cannot restrict, as far as was seen here: reading the account's public repositories. Every token can.
