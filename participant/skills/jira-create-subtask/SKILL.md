# Skill: preview, then create, one approved subtask under an existing Jira story

Creates one subtask under one existing issue in a Jira sandbox project, and only after a person has seen which
parent it would go under and has confirmed that preview by its fingerprint. Then it reads the subtask back and
compares its parent with the parent intended.

**This skill writes outside the repository.** A created issue cannot be unsent, and Jira may email people about it.
Use it on a sandbox project only.

## The three commands

    python3 participant/skills/jira-create-subtask/subtask.py preview --source live --change CHANGE.json --allowlist FILE --state DIR
    python3 participant/skills/jira-create-subtask/subtask.py confirm --source live --change CHANGE.json --allowlist FILE --state DIR --fingerprint CODE --confirmed-by NAME
    python3 participant/skills/jira-create-subtask/subtask.py check   --source live --state DIR --fingerprint CODE

`--source fake` runs the same commands against `fake_jira.py`, a made-up Jira, with no network.
`--log FILE` saves what a command printed, with the site's address replaced by a marker and the parent's title left out.

A change file names the parent and gives the subtask's title:

    {"parent": "SAND-1", "summary": "Write the export query"}

| Command | Reads Jira | Writes to Jira | What it is for |
|---|---|---|---|
| `preview` | yes | **never: it is given no way to** | Shows the site, the project, the parent, exactly what would be sent, the permission check, the duplicate check and a fingerprint |
| `confirm` | yes | **one subtask, once, never retried** | Creates the subtask of one preview, named by its fingerprint, after checking everything again |
| `check` | yes | never | Reads the subtask back and compares its parent with the parent intended |

## How the parent is chosen

**By its identifier, never by its title.** `parent` is the issue's key or its numeric issue id. Anything else is refused
before Jira is asked. There is no search in this workflow at all: it asks Jira for that one issue.

**The key is pinned to the issue id.** The preview shows the key, the issue id, the type, the status and the title. The
fingerprint is tied to the issue id, which does not change when an issue is moved or renamed. A confirmation reads
the parent by that id, and is refused if the key in the change file now leads to a different issue. The write names
the parent by its id.

**The title is for the person to read.** It is shown on screen, marked as other people's text, so that a person can
see which story this is. Nothing is done with it, and it is not saved.

## What happens when the parent is ambiguous or unsuitable

| Case | What happens |
|---|---|
| Two stories have the same title | Nothing special, and that is the point: each has its own key and id, and only the one named is read. The preview shows its key, id and title |
| A title is given in place of a key | Refused before Jira is asked, if it has a space or any character a key cannot have. A title of one plain word is asked of Jira as a key, and comes back as not found |
| Jira does not return the parent | Refused before any preview. It does not exist, or this identity may not see it: Jira gives one answer |
| The parent is itself a subtask | Refused before any preview |
| **The parent is closed** (its status is in Jira's "done" category) | **Refused before any preview, with no override.** Reopen the story in Jira first |
| Jira does not say which category the status is in | Refused: whether it is closed is not known |
| The key now leads to another issue than the preview showed | Refused at the confirmation |
| The parent was closed, or turned into a subtask, after the preview | Refused at the confirmation |

**It does not require the parent to be a Story.** The preview shows the type's name, and the person judges. An epic, a
task or a bug is accepted if Jira accepts it. Its messages and the heading of its result record say "story" all the
same. In the real run of this quest the parent was a Task.

**Checked again at the confirmation:** that the parent is not a subtask and not closed. Not compared with the
preview: the parent's type otherwise, its status otherwise, and its title. Those can change after the preview
without a refusal.

## The other controls

**Preview first.** A preview has no function that can send a write, and lists every request it sent. It reads the
parent before and after and prints a code for each: the same code means Jira did not change while it looked.

**What is sent, and nothing else:** the project, the parent, the project's one subtask issue type and the title. No
description, assignee or estimate. A project with no subtask type, or with more than one, is refused.

**Sandbox allowlist.** The parent's project must be in the allowlist file, by Jira's project id together with a
fingerprint of the site's address. Any other project is refused at the preview, after one read, and again at the
confirmation. There is no option that turns this off. **The allowlist is whatever file the command is given.** The
workflow knows "listed", not "sandbox": the file itself is what a person approves.

**Permission check.** Jira is asked whether this identity may see the project and may create issues in it. No answer
is not taken as yes.

**Duplicate check.** The parent's subtasks are read, and the title of each is compared with the new title, with
capitals, spacing and the encoding of letters set aside, whoever made the subtask. If one matches there is nothing to
add and no fingerprint is issued. That is what makes a second run harmless. Only this parent's subtasks are compared:
the same title under another story is not a duplicate. Only subtasks this identity can see are compared.

**Confirmation by fingerprint.** A confirmation names the 12-character fingerprint of one preview and gives the name
of the person confirming. It is refused if either is missing, if the saved preview was altered, if it was used
before, if another run is confirming it at that moment, if it is more than 15 minutes old, or if the parent, the
title, the change file or the allowlist file now is not exactly what that preview showed.

**What that does not prove.** The saved previews are plain files in the state folder, with no secret behind them.
Someone, or a program, that can write that folder could make a preview no person saw, or mark a used one unused. They
could not make the workflow create a subtask under another parent, in another project or with another title than the
change file and Jira give: all of that is worked out again and compared. The name given with a confirmation is not
checked against anyone. The controls stop mistakes and stale approvals. They do not stop someone who sets out to get
round them.

**Read back.** After the write the subtask is read by the issue id Jira gave it. Its parent must be the parent
intended, by issue id. It must be a subtask, with the title previewed, in the parent's project, and the parent's own
list of subtasks must hold it. Anything else ends with "A PERSON NEEDS TO LOOK" and exit code 2.

**After a write is sent, "nothing was written" is said only when Jira answered 400, 401, 403 or 404 and the parent's
subtasks, read back, are unchanged.** Any other failure, a server error among them, ends with "A PERSON NEEDS TO
LOOK": Jira may still be creating the subtask. The new issue's id is saved to the state folder as soon as Jira gives
it.

**A result record** is printed, and saved as Markdown with `--result`: the subtask's key and issue id, the parent
intended and the parent read back, the project, the site's fingerprint, the title's checksum, when it was written,
who confirmed and when, and how to reverse it.

## The title, and private content

**Refused:** an empty title; more than one line; more than 200 characters; a space at either end; a tab; a character
that cannot be seen. **Refused, as a secret:** a title matching one of nine patterns for keys, tokens and passwords
written out. The refusal names the kind and does not print the match. These are patterns: they miss secrets of other
shapes.

**Pointed out, not refused:** an email address, a web address, what may be a telephone number, an `@name`, and words
such as "confidential". Whether a title is fit to be seen is the confirming person's decision.

What is printed from Jira: keys and ids, the names of the parent's type and status, the name of the subtask type, and
the parent's title on screen only. If Jira refuses a write, its own words are shown, quoted and cut short, as its
words. Those words are saved with `--log`.

## What it cannot do

- **Stop two runs at the same moment both writing.** Jira's request to create an issue has no "only if there is none
  like it" condition. The run counts subtasks with this title after it writes and stops with "MORE THAN ONE" if there
  are two.
- **Say what else Jira does when the subtask is created:** automation rules, notifications, a default assignee.
- **Delete or undo.** Deleting is done by hand.
- **Set any field but the title.** A project that requires another field will refuse the write.
- **Create several subtasks in one run,** or copy fields from the parent.
- **Know that the parent is the right story.** It shows which issue it is. A person decides.

## Limits a reader found before the real run, left as they are

- A run stopped from the keyboard after the write prints nothing. The new issue's id is in the state folder.
- If Jira is slow to show a new subtask, the read-back can fail and the run ends with "A PERSON NEEDS TO LOOK" although
  the subtask is fine. That is a false alarm in the safe direction.
- The result record is saved where `--result` says before the output is searched for credentials.
- `--pretend-minutes-later` is for tests and is not switched off for a live run. It can only make a preview look
  older, never newer.
- Not described above, and in the code: a confirming name is at most 60 characters and may not hold an `@`. A preview
  dated in the future is refused. A change file that gives a name twice is refused.
- Two previews of one change can both be open. The second confirmation is stopped by the duplicate check, unless both
  run at the same moment.
- Expiry goes by this computer's clock and by the time written in the saved preview.
- The duplicate check ignores capitals, spacing and encoding, and nothing else: "Fix login" and "Fix login." are two
  titles.
- Whether Jira ever shortens the list of an issue's subtasks was not established. If it did, the duplicate check
  would miss what was left out.
- The site fingerprint is not a secret: someone who guessed the site's name could confirm the guess from it.

## Exit codes

0, done. 1, refused, or `check` did not find the subtask as previewed: this run wrote nothing. 2, a write was sent and a
person needs to look.

## Connection and credentials

A live run reads `JIRA_BASE_URL`, `JIRA_EMAIL` and `JIRA_API_TOKEN` from the environment. None is stored.
`JIRA_BASE_URL` must be `https://` and the site's name, with no port and no path. Before anything is shown, the output
is searched for the token, the email address and their encoded form. If one is found, the output is not shown and the
log is not saved. The site's address is shown on screen and replaced by a marker in anything saved.

## Tests

    python3 -m unittest discover -s participant/skills/jira-create-subtask/tests

They run against the fake Jira. The fake is built from Jira's published API specification and is not Jira.
