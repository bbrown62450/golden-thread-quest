# GitHub: preview a new issue

Written by an AI assistant (Claude) at the participant's direction.

## 1. Purpose

This skill prepares a new GitHub issue completely and stops just before creating it. It checks a draft against
the repository's own conventions, runs the duplicate search and a permission check, and shows the exact
payload that a later write would send.

Its rule: **show the whole write before it is made, in the shape the repository expects, and write nothing.**

It only reads GitHub. Every request is a GET, and there is no code in it that could send anything else.

    python3 participant/skills/github-create-issue-preview/preview.py --source live --draft DRAFT.md \
        --index INDEX.md --allowlist FILE [--despite-duplicate OWNER/NAME#N] [--payload-out FILE] [--state FOLDER]

`--source fake` uses the made-up GitHub in `fake_github.py` in place of GitHub. The skill uses the Python
standard library only. It needs the `github-duplicate-search` and `github-build-index` skills' folders beside
it, and uses them as they are.

## 2. Credentials

A live run needs one environment variable, `GITHUB_TOKEN`, set in your own terminal with `read -s` and then
`export`. The narrowest token that works is a fine-grained one, on the one sandbox repository, with **Issues:
read-only**, **Contents: read-only** (to read the template) and **Metadata: read-only**. It needs no write
permission, and should have none.

Unset the variable afterwards.

## 3. The draft

One Markdown file, in the format `github-issue-draft/1`:

    ---
    format: "github-issue-draft/1"
    repository: "OWNER/NAME"
    template: "bug_report.md"
    title: "One line"
    labels: ["bug", "export"]
    assignees: ["a-login"]
    milestone: "Sprint 13"
    ---

    ## Body

    ### What happened

    ...the template's sections, each under its own heading...

    ## Sources

    - title: sources/notes.md line 7: "the words quoted"
    - body: sources/notes.md lines 8-9: "more words"

Every value in the front matter is written as JSON. `milestone` may be `null`. The body that would be sent is
everything from the first section heading to the line before `## Sources`, character for character.

## 4. The template

The preview reads the template named in the draft from the repository itself: the file
`.github/ISSUE_TEMPLATE/NAME` on GitHub. It reads Markdown templates, whose sections are level-3 headings
(`### ...`). Issue forms, which are YAML files, are not read.

- **Every section is required, unless its heading ends with "(optional)".** A Markdown template cannot say
  which sections are required, so this rule is the skill's own.
- A section is **empty** when it holds nothing but blank lines, an HTML comment, or the template's own
  placeholder text.
- The draft's sections must be the template's, in the template's order. A section the template does not have
  is refused. A heading inside a code block is not a section.
- If the template names labels for issues of its kind, the draft must have them.

GitHub applies a template only in its web page. An issue created by a program gets none. So nothing on GitHub's
side enforces any of this. This preview does.

## 5. Labels, assignees and milestone

Each is looked up in the repository. A label must already exist, and is written as the repository writes it. An
assignee must be someone GitHub says can be assigned there. A milestone must exist, be open, and be the only
one with that title. Nothing is invented: GitHub would create an unknown label without saying, so the preview
stops first.

## 6. Sources

Under `## Sources` is one line for each citation: the field, a file, the line or lines, and the words quoted.
Each is checked: the file must be in the draft's folder or below it, and the quoted words must be on the lines
named. A title and a body must each have a source, and so must the labels, assignees and milestone if the draft
sets them. A source that was changed after the draft was written fails.

## 7. The duplicate check

The preview runs the `github-duplicate-search` on the local index named with `--index`, and shows its result.

| The search recommends | The preview |
|---|---|
| `proceed` | says no likely duplicate was found |
| `link` | is ready. It names the candidates and says the new issue should point to them. It does not add that to the issue's text |
| `close-as-duplicate` | is **NOT READY**, and names the existing issue |

To go on despite a likely duplicate, a person runs the preview again with `--despite-duplicate OWNER/NAME#N`,
naming that issue. The preview then says it was overridden, and records it. The override must name the issue
the search reported: it is not a way to skip the check.

If the index is stale or was edited, the search stops, and so does the preview.

## 8. The permission check

The preview shows what GitHub says the **account** may do in the repository, whether issues are turned on, and
whether the repository is archived. If the draft sets labels, assignees or a milestone and the account may not
triage, the preview is not ready: GitHub would create the issue and drop those fields without saying.

GitHub does not say what a fine-grained **token** may do. The preview says so. Whether the token may create an
issue is known only when a write is tried, and the preview does not try one.

## 9. The payload

When every check passes, the preview builds the payload: `title`, `body`, and `labels`, `assignees` and
`milestone` if the draft sets them. The milestone is sent as its number. It is built in one place, once.

The preview shows it field by field and as the **exact bytes**, with their SHA-256. With `--payload-out` it
writes the same to a file. With `--state` it saves the preview, payload included, under its fingerprint, for a
later write to send. The bytes are written in one fixed field order, so a payload saved and read back gives the
same bytes.

## 10. How it ends

- **READY** (exit 0): every check passed. The payload and a fingerprint are shown.
- **NOT READY** (exit 1): every reason is listed, not only the first. No payload is shown, no fingerprint is
  given and nothing is saved.
- **STOPPED** (exit 1): the draft could not be read, the repository is not on the allowlist, or GitHub could not
  be read.

Before it ends, the preview reads the repository again and compares: newest issue number, labels, milestones.

## 11. The sandbox allowlist

`--allowlist` names a JSON file, `{"sandbox_repositories": ["OWNER/NAME"]}`. A repository that is not on it is
refused before any request is sent.

## 12. Tests

    python3 -m unittest discover -s participant/skills/github-create-issue-preview/tests -v

Every test runs against `fake_github.py`. None contacts GitHub.

## 13. What it does not do

- It does not create the issue. There is no code here that could.
- It does not read issue forms (YAML templates), or templates whose sections are not level-3 headings.
- It cannot know whether the token may write.
- Its duplicate check sees only what the local index holds. An issue filed since the last sync is not seen.
- It does not check that the body renders as intended, or that a citation's words mean what the draft says.
- A live run must keep its draft, its saved preview and its payload file outside this repository.
