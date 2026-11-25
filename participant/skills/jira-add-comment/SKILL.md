# Skill: preview, then add, one approved comment on a Jira story

Adds one comment to one story in a Jira sandbox project, and only after a person has seen its exact text, its target
and who can see it, and has confirmed that preview by its fingerprint. Then it reads the comment back.

**This skill writes outside the repository.** A comment is public to whoever can see the story, Jira may email it to
the story's watchers, and it cannot be unsent. Use it on a sandbox project only.

## The three commands

    python3 participant/skills/jira-add-comment/comment.py preview --source live --change CHANGE.json --allowlist FILE --state DIR
    python3 participant/skills/jira-add-comment/comment.py confirm --source live --change CHANGE.json --allowlist FILE --state DIR --fingerprint CODE --confirmed-by NAME
    python3 participant/skills/jira-add-comment/comment.py check   --source live --change CHANGE.json --state DIR --fingerprint CODE

`--source fake` runs the same commands against `fake_jira.py`, a made-up Jira, with no network.
`--log FILE` saves what a command printed, with the site's address replaced by a marker.

A change file names the story, the file holding the text, and the visibility:

    {"story": "SAND-1", "text_file": "comment.txt", "visibility": "everyone"}
    {"story": "SAND-1", "text_file": "comment.txt", "visibility": {"role": "Administrators"}}

## What each command does

| Command | Reads Jira | Writes to Jira | What it is for |
|---|---|---|---|
| `preview` | yes | **never: it is given no way to** | Shows the site, the project, the story, the exact text, who can see it, where the text came from, the permission check, the duplicate check and a fingerprint |
| `confirm` | yes | **one comment, once, never retried** | Writes the comment of one preview, named by its fingerprint, after checking everything again |
| `check` | yes | never | Reads the story back and looks for the comment: same text, expected author, same visibility |

## The controls

**Preview first.** Nothing is written by a preview. It has no function that can send a write, and it lists every
request it sent. It reads the story and its comments before and after and prints a code for each: the same code means
Jira did not change while it looked.

**The visibility stands directly under the text.** "EVERYONE who can see the story", or "ONLY people in the project
role ...", with the story's security level beside it. The preview says plainly that it cannot list who that is.

**Sandbox allowlist.** The story's project must be in the allowlist file, by Jira's project id together with a
fingerprint of the site's address. Any other project is refused at the preview, after one read, and again at the
confirmation. There is no option that turns this off. The preview names the allowlist file it used, with a checksum
and the number of projects it lists, and a confirmation with another allowlist file is refused. **The allowlist is
whatever file the command is given.** Whoever runs the command chooses it, so the file itself is what a person
approves.

**No unrestricted comment on a service project.** Where Jira says the project is a service project, a comment with no
restriction can be seen by customers, and the workflow does not send one. Where Jira does not give the kind of
project, the preview says "not given" and the comment is not stopped on that ground.

**Permission check.** Jira is asked whether this identity may see the story and may comment on it. No answer is not
taken as yes.

**Duplicate check.** Every comment on the story is read, in pages, and compared with the text. If this identity has
already put a comment with the same text and the same visibility on the story, there is nothing to add and no
fingerprint is issued. That is what makes a second run harmless. Only comments this identity can see are compared: a
comment restricted to others is not among them.

**Confirmation by fingerprint.** A confirmation names the 12-character fingerprint of one preview and gives the name
of the person confirming. It is refused if either is missing, if the saved preview was altered, if it was used
before, if another run is confirming it at that moment, if it is more than 15 minutes old, or if the story, the text,
the file, the visibility or the allowlist file now is not exactly what that preview showed.

**What that does not prove.** The saved previews are plain files in the state folder, with no secret behind them.
Someone who can write that folder could mark a used preview as unused, or change its time. They could not make the
workflow post another text, or to another story, site or project: all of that is worked out again from the change
file and from Jira and compared. And the name given with a confirmation is not checked against anyone. The controls
stop mistakes and stale approvals. They do not stop a person, or a program, that sets out to get round them.

**Everything is checked again just before the write:** the allowlist, the permission, the story's project and
security level, and the comments. If this comment is there by then, the write is not sent.

**Read back.** After the write, the comment is read by the identifier Jira gave it. Its text must be the text
previewed, character for character. It must be plain text with nothing added, by this identity, with the visibility
previewed, and there must be exactly one comment with that text and that visibility by this identity. Anything else
ends with "A PERSON NEEDS TO LOOK" and exit code 2.

**After a write is sent, nothing is reported as "not written" unless Jira was read and shows it.** If a read fails
after the write, or the program itself fails, the run ends with "A PERSON NEEDS TO LOOK" and exit code 2, and what it
had already printed is still shown. The comment's identifier is saved to the state folder as soon as Jira gives it.
Two exceptions: a run stopped from the keyboard prints nothing, and so does one whose output is found to hold a
credential.

**A result record** is printed, and saved as Markdown with `--result`: the issue key and id, the comment's
identifier, the project, the site's fingerprint, the visibility, the text's checksum and source, when it was written,
who confirmed and when, and how to reverse it.

## The text, and private content

The text is read from a file beside the change file. Who or what put it there is not known to the workflow, and the
preview says so. The workflow does not write the file and does not take the text from Jira.

It is sent as plain text, one paragraph to a line. Nothing in it is formatting, a link or a mention. An `@name` is
text and notifies nobody.

**Refused:** an empty text; more than 2000 characters or 40 lines; an empty line; a line that begins or ends with a
space; a tab; a character that cannot be seen.

**Refused, as a secret:** text matching one of nine patterns: an AWS access key, a private key, a GitHub token, a
Slack token, an Atlassian API token, a JSON web token, a web address with a password in it, a password or key written
out ("password is ...", "API_KEY=..."), or a run of 32 or more letters, digits and the signs `+ / _ -` that holds at
least one letter and one digit. That last one also refuses a long hash or a long path. The refusal names the kind and the line and does not print the match. These are patterns.
They miss secrets of other shapes and can refuse text that is not a secret.

**Pointed out, not refused:** an email address, a web address, what may be a telephone number, an `@name`, and words
such as "confidential". They are listed above the fingerprint for the person confirming to judge. Whether a text is
fit to be seen is that person's decision, and the preview says so.

Nothing in the story's text, or in the comments already on it, is printed or acted on. What is printed from Jira: the
kind of project, the name of the story's security level, a role's name and number, the names of the project's roles
when a role asked for is not among them, the kinds of thing found in a comment read back that are not plain text,
and, in `check`, the text of the one comment this workflow wrote, with unseen characters replaced. If Jira
refuses a write, its own words are shown, quoted and cut short, as its words.

## What it cannot do

- **Say who can see the comment.** It shows the comment's restriction and the story's security level. It cannot list
  the people who can see the story, and does not know whether the project is open to customers or to the public.
- **Say who Jira will email.** Watchers and others may be sent the whole text.
- **Stop two runs at the same moment both writing.** Jira's request to add a comment has no "only if there is none
  like it" condition. The run counts such comments after it writes and stops with "MORE THAN ONE" if there are two.
- **Unsend or delete a comment.** Deleting is done by hand, and emails already sent stay sent.
- **Restrict a comment to a group,** or to anything but one project role. The role path was tried on the fake Jira
  only. On a real site, listing a project's roles may need an administrator's permission, and Jira may refuse a role
  the commenter is not in. Both would be refusals with nothing written.
- **Send formatting, links or mentions.**
- **Know that the text is true, kind or wanted.**

## Limits a reader found after the real run, left as they are

The workflow file is the one that made the real runs, unchanged since. A reader of that version found these, and they
are not corrected:

- **The allowlist file is read twice in a run:** once for the list that is enforced, and again for the checksum that
  is shown. If the file changed between the two, the checksum would be of a list other than the one enforced.
- **Two open previews of the same comment** can each be confirmed. The second confirmation is stopped by the duplicate
  check, unless both run at the same moment.
- **A 5xx answer to the write, with the comments unchanged when read back, is reported as "nothing was written".** If
  Jira took the write and its list lagged, that would be wrong.
- **If the state folder cannot be written just after the write,** the comment's identifier is neither saved nor
  printed.
- **A security level that Jira does not report** is shown as "Jira did not say", and does not stop a write.
- **`check` trusts the record of the write** in the state folder as it finds it.
- **Secrets of more shapes are missed:** a quoted name such as `"password": "..."`, `pw=`, `pass=`, a value under four
  characters.
- **The confirmation's output does not list the requests it sent.** The preview's and the check's do.

## Exit codes

0, done. 1, refused or not found: nothing was written. 2, a write was sent and a person needs to look.

## Connection and credentials

A live run reads `JIRA_BASE_URL`, `JIRA_EMAIL` and `JIRA_API_TOKEN` from the environment. None is stored.
`JIRA_BASE_URL` must be `https://` and the site's name, with no port and no path. Before
anything is shown, the output is searched for the token, the email address and their encoded form. If one is found,
the output is not shown and the log is not saved. The state files and the result record are written before that
search. The site's address is shown on screen, so that the person confirming can see where the
write would go, and is replaced by a marker in anything saved. The account's identifier and name are never printed.
What is saved is a 16-character fingerprint of the site's name. It is not a secret: someone who guessed the name could
confirm the guess from it.

## Tests

    python3 -m unittest discover -s participant/skills/jira-add-comment/tests

They run against the fake Jira. The fake is built from Jira's published API specification and is not Jira.
