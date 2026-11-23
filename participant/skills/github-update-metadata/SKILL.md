# GitHub: update an issue's labels, assignees or milestone

Written by an AI assistant (Claude) at the participant's direction.

## 1. Purpose

This skill changes a small, fixed set of metadata on **one** GitHub issue: its labels, its assignees and its
milestone. It writes to GitHub, so it works in two steps that are two separate commands:

- `preview` shows the old and new values and the exact requests. It only reads. It has no way to write.
- `confirm` makes the update of one preview, named by its fingerprint, when a person confirms it.

Its rule: **update only what was asked, and only if nothing moved since the person saw the preview.**

    python3 participant/skills/github-update-metadata/update.py preview --source live --repo OWNER/NAME --issue N \
        --change FIELD=VALUE [--change ...] --allowlist FILE --state FOLDER
    python3 participant/skills/github-update-metadata/update.py confirm (the same arguments) \
        --fingerprint F --confirmed-by NAME --results FOLDER

`--source fake --fake-store FILE` uses the made-up GitHub in `fake_github.py` in place of GitHub. The skill uses
the Python standard library only.

## 2. Credentials

A live run needs one environment variable, `GITHUB_TOKEN`. Set it in your own terminal with `read -s`, then
`export` it. It is sent in a request header and never put in an address or a file. The narrowest token that
works is a fine-grained one, on the one sandbox repository, with **Issues: read and write** and **Metadata:
read-only**.

Unset the variable afterwards. Git's GitHub sign-in can pick it up, and a push then fails.

## 3. What may be changed

Six kinds of change, and no others. The full list, the allowed values and what is refused are in
`participant/context/github/update/supported-fields.md`.

    label.add=NAME        label.remove=NAME
    assignee.add=LOGIN    assignee.remove=LOGIN
    milestone.set=TITLE   milestone.clear=yes

Labels and assignees are added and removed **one at a time**. The skill never sends a whole list, so a label
it was not asked about cannot be removed by it. Title, body, state, project fields and everything else are
refused. One refused change stops the whole preview.

## 4. The sandbox allowlist

`--allowlist` names a JSON file with the repositories the skill may write to:

    {"sandbox_repositories": ["OWNER/NAME"]}

A repository that is not on it is refused by `preview` and by `confirm` **before any request is sent**. A list
that cannot be read allows nothing. The name must be exactly as GitHub writes it.

## 5. The preview

It reads the account, the repository, the issue, the repository's labels and milestones, and shows:

1. **WHERE**: repository, its id, the issue, its node ID, the account the connection acts as.
2. **ALLOWLIST**.
3. **WHAT WAS ASKED**, change by change: WILL CHANGE, ALREADY SO, or REFUSED with the reason.
4. **OLD AND NEW VALUES** of labels, assignees and milestone, including a field that stays the same.
5. **EXACT REQUESTS** a confirmation would send.
6. **PERMISSION CHECK**: what GitHub says the account may do. GitHub does not say what a fine-grained token may
   do, and the preview says so.
7. **DUPLICATE CHECK**: changes that are already so are not sent.
8. **NOTHING WAS WRITTEN**: the issue is read again at the end and compared.
9. **FINGERPRINT**, if the preview is READY.

It ends READY, NOT READY or NOTHING TO CHANGE. Only a READY preview is saved and has a fingerprint.

## 6. The confirmation

`confirm` takes the same arguments again, with `--fingerprint` and `--confirmed-by`. It refuses, and writes
nothing, when:

- either of the two is missing;
- the repository is not on the allowlist;
- there is no saved preview with that fingerprint, or the saved preview was altered;
- the changes given now are not exactly the changes of the preview;
- the preview was already used. A preview can be confirmed once;
- the preview is more than **15 minutes** old, by GitHub's clock;
- the account, repository or issue is not the one of the preview;
- **anything moved**: the issue's labels, assignees or milestone on GitHub are not what the preview showed.
  This is the stale check. It covers all three fields, whichever one is being changed. A new comment or an
  edited body does not count.

Then it marks the preview as used, sends the requests of the preview in order, reads the issue back, and
compares it with what the preview promised.

## 7. How it ends

- **DONE** (exit 0): the issue was read back and is what the preview promised.
- **NOT DONE** (exit 1): GitHub refused the first write and the issue is as it was.
- **NEEDS LOOKING** (exit 3): something was written and the issue is not what the preview promised. Either
  someone changed it in the moment between the check and the write, or GitHub refused part of the update.
- **REFUSED** or **STOPPED** (exit 1): nothing was written.
- Rate-limited before any write (exit 2): nothing was written.

## 8. The result record

Each confirmed update adds a section to `update-metadata.md` in the `--results` folder: outcome, repository,
issue number and node ID, who confirmed, the account, the fingerprint, GitHub's time, old value, promised value
and read-back value of each field, the requests sent with their status, the ids of the events GitHub recorded
and of the labels added, and the changes that would put the old values back.

## 9. Running it again

- The same confirmation again: refused, the preview was already used.
- A new preview of the same changes: every change is ALREADY SO, there is no fingerprint, nothing to confirm.

## 10. Tests

    python3 -m unittest discover -s participant/skills/github-update-metadata/tests -v

Every test runs against `fake_github.py`. None contacts GitHub.

## 11. What it does not do, and its limits

- **The gap between the check and the write.** They are separate requests, and GitHub offers no way to make
  them one for these fields. A change made in that moment is not seen by the check. Because labels and
  assignees are never sent as a whole list, such a change is not overwritten, and the read-back reports it.
  A milestone set by someone in that moment **would** be replaced. The read-back cannot tell.
- It cannot know who typed the confirmation. It records the name it is given.
- It does not know what a fine-grained token may do until GitHub refuses a write.
- It does not create labels or milestones, and does not change project fields, title, body or state.
- A live run must keep its previews and its result record in folders outside this repository.
