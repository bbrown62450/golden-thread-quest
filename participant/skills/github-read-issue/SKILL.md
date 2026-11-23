# GitHub: save one issue as Markdown

Written by an AI assistant (Claude) at the participant's direction.

## 1. Purpose

This skill reads **one** GitHub issue, with its comments, and saves it as one Markdown file that loses nothing.

Its one rule: **what GitHub sent is either in the file, or on a list in the file that says it was left out and
why.** Nothing goes missing silently.

It only reads GitHub. Every request is a GET. It runs no command, and it never reads an issue's text for
meaning: the text is copied.

    python3 participant/skills/github-read-issue/read_issue.py --source fake [--issue N] [--fake-step 1|2] [--save-as NAME.md]
    python3 participant/skills/github-read-issue/read_issue.py --source live --repo OWNER/NAME --issue N --out FOLDER
    python3 participant/skills/github-read-issue/read_issue.py --check FILE

`--source fake` uses the made-up GitHub in `fake_github.py`, beside this file. `--source live` uses GitHub.
`--check` reads a saved file back and contacts nothing. The skill uses the Python standard library only.

## 2. Credentials

A live run needs one environment variable, `GITHUB_TOKEN`. Set it in your own terminal with `read -s`, then
`export` it. It is sent in a request header and is never put in an address. The narrowest token that works is
a fine-grained one, on the one repository, with **Issues: read-only** and **Metadata: read-only**.

Unset the variable afterwards. Git's GitHub sign-in can pick it up, and a push then fails.

## 3. What it reads

Two things, and nothing else:

1. the issue: `GET /repos/OWNER/NAME/issues/N`
2. its comments, page after page until GitHub reports no further page

It stops, and writes nothing, when:

- the number is a pull request. The rule: an item is a pull request when it carries a `pull_request` key;
- GitHub answers from another repository, because the issue was transferred or the repository renamed;
- the issue was deleted (410), or cannot be seen (403 or 404, which cannot be told apart);
- the comments cannot be read. An issue is never saved with part of it missing;
- GitHub keeps rate-limiting after three short waits (exit code 2).

## 4. The file

The file is named `OWNER__NAME__issue-N.md`, unless `--save-as` gives another name. From top to bottom:

1. **Front matter.** `format`, `source`, `repository`, `number`, `node_id`, `title`, `state`, `state_reason`,
   `labels`, `assignees`, `milestone`, `author`, `created_at`, `updated_at`, `closed_at`, `locked`, `comments`,
   `comments_saved`, `body_sha256`, `body_bytes`. Every value is JSON on one line, so a title cannot add a line.
2. **Fields kept in full.** The fields the format knows that have no line of their own: the full label and
   milestone records, reactions as counts, who closed it, and so on.
3. **Preserved fields.** Every field GitHub sent that the format does **not** know, as GitHub sent it. A field
   GitHub adds next year lands here without any change to the skill.
4. **Comment fields.** One entry for each comment, in GitHub's order, naming any field not known.
5. **Left out on purpose.** The only things not in the file, each with its reason. There are two kinds:
   - an address on `api.github.com`, which can be worked out again from the repository and number;
   - a person's record, of which only the **login** is kept. User ids, picture addresses and everything else
     in the record are left out.
6. **Content from GitHub.** The body, then each comment, **word for word**, each between two marker lines.

Everything the skill wrote comes first. Everything other people wrote comes last. So nothing in a body or a
comment can stand in for the file's own parts, and a code block left open in a body cannot swallow them.

The file holds no time of retrieval. The same answer from GitHub always gives the same bytes.

## 5. How the text is kept

- The body is written exactly as GitHub sent it: line endings, tabs, spaces at the end of a line, blank lines
  at the start and end. Nothing is tidied.
- The marker lines carry the start of the text's own SHA-256. A line inside the text cannot pass for the end
  marker. If a text did hold its own end marker, the run stops.
- The front matter records the body's SHA-256 and size. Reading the file back cuts the body out and checks it.
- "No body" (GitHub sends null) and an empty body are kept apart.

## 6. The check before writing

Before anything is written, the skill reads its own text back into fields and compares it, value by value,
with GitHub's answer. If any value is in neither the file nor the left-out list, it stops and writes nothing.

## 7. Running it again

- Nothing changed on GitHub: the file is not written again. The run says UNCHANGED.
- Something changed: the file is rewritten whole, and the run says which parts differ.
- The file already there holds another issue (another node ID), comes from another source, or was not written
  by this skill: it is not overwritten.
- The run fails: the file is left as it was.

## 8. Text that should not be shared

The skill scans what it saves for the token's own value, for anything shaped like a credential, and for
anything shaped like an email address.

- The token's own value: the run stops and writes nothing.
- Anything else: the text is **kept as it is**, because changing it would make the copy unfaithful. The run
  warns, says where and how many without showing them, and ends with exit code 3. Do not share or commit such
  a file until a person has read it.

A live run must be given `--out`, a folder outside this repository. A real issue holds real people's logins
and words.

Exit codes: 0 saved or unchanged. 1 stopped, nothing written. 2 rate-limited, nothing written. 3 saved, with a
warning.

## 9. What is printed

Numbers, the node ID, counts, checksums and the names of fields. Never the title, the body, a label, a login
or a comment.

## 10. Tests

    python3 -m unittest discover -s participant/skills/github-read-issue/tests -v

Every test runs against `fake_github.py`. None contacts GitHub.

## 11. What it does not do

- It does not change anything in GitHub.
- It does not read the issue's timeline: who labelled it, closed it or linked to it, and when.
- It does not download pictures or files attached to the issue. Their addresses stay in the text.
- It does not render Markdown or judge whether it is well formed. It keeps the characters.
- It does not know the names of fields inside a known record. A new field inside a label is kept, in "Fields
  kept in full", and is not reported as new.
- It saves one issue per run, and keeps no history: the file holds the issue as it was at the last run.
