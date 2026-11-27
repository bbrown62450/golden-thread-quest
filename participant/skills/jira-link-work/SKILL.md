# jira-link-work

Links Jira items after a preview that says each link **in words**, and a confirmation by a person. Then reads each
link back **from both items** and compares what each shows with the sentence asked for.

## When to use it

- To record that one item blocks another, or that two items are related.
- Not for "duplicates" or "clones" links, or any link type of the site's own. Those are refused. See below.

## Before anything else

- **Sandbox only.** BOTH items of a link must be in a project on the sandbox allowlist, for that Jira site.
- **A person confirms every write,** by giving the fingerprint of a preview they have read.
- **Read the sentence aloud.** If the sentence in the preview is backwards, so is the link.
- **Real runs are the person's to run,** in their own terminal, with `JIRA_BASE_URL`, `JIRA_EMAIL` and
  `JIRA_API_TOKEN` set there. The agent builds and tests against the fake Jira and reads saved output only.

## A request is written as sentences

    {"links": [{"from": "ABC-1", "phrase": "blocks", "to": "ABC-2"}]}          read: ABC-1 blocks ABC-2

- One to five links in a request. They share one preview and one fingerprint.
- `phrase` is one of the phrases the Jira site itself uses, matched letter for letter: on a new site, `blocks`,
  `is blocked by` or `relates to`. A phrase the site does not have is refused, and the site's phrases are listed.
- `ABC-2 is blocked by ABC-1` is the same link as `ABC-1 blocks ABC-2`, and is treated as the same.
- There are no synonyms. For "ABC-2 depends on ABC-1" write `ABC-1 blocks ABC-2`, or `ABC-2 is blocked by ABC-1`.
- A site may have renamed its phrases. The workflow uses whatever phrases the site gives for its type named Blocks
  or Relates. Which item is the source is decided by which of the type's two phrases was used, never by the name.
- Nobody writes Jira's slot names, `inwardIssue` and `outwardIssue`. The workflow fills them in.

## The commands

| Command | Reads Jira | Writes to Jira | What it does |
|---|---|---|---|
| `preview` | yes | **never: it is given no way to** | Says each link in words, from both items. Shows the site, the projects, exactly what would be sent, the permission check, the duplicate check and a fingerprint |
| `confirm` | yes | **the links of one preview** | Creates each link once, and reads it back from both items before sending the next |
| `check` | yes | **never** | Reads the links of a confirmed preview back from both items |

    link_work.py preview --source live --request REQUEST.json --allowlist ALLOWLIST.json --state STATE
    link_work.py confirm --source live --request REQUEST.json --allowlist ALLOWLIST.json --state STATE --fingerprint CODE --confirmed-by NAME
    link_work.py check   --source live --state STATE --fingerprint CODE

`--source fake` runs against the fake Jira kept in STATE.

## What is refused, with nothing written

| Refused | Why |
|---|---|
| A phrase of the type **Duplicate** or **Cloners**, or of any type but Blocks and Relates | "Duplicates" tells people to stop work on an item, and on some sites closes it. "Clones" records a history that did not happen. What a site's own types set off cannot be known |
| **The opposite link already exists** | "A blocks B" and "B blocks A" cannot both be meant. A person decides which is right |
| **A link that would close a circle** | Existing links of the same type are followed from the target. If they lead back to the source, each item would wait for the next for ever |
| An item in a project off the allowlist; an item Jira does not return; an item linked to itself | |
| A link asked for twice in one request, or a link and its opposite in one request, or more than five links | |

A link that is **already there**, the same type and the same way round, is not an error: it is reported and not
created again. If every link asked for is already there, no fingerprint is issued.

- **"Relates to" has no direction and no opposite.** Either order is the same link. It is never part of a circle.
- **A preview is good for 15 minutes,** for one confirmation, while the request and the allowlist are unchanged.
- **Nothing is remembered between requests about what links exist.** Every preview reads Jira. If someone deletes a
  link and the same request is run again, it is previewed as a new link and needs a new confirmation.

## What to do with each ending

| It ends with | Meaning | Do this |
|---|---|---|
| exit 0 | Done, or nothing to create | Nothing |
| exit 1, `REFUSED` | Nothing was written by this run, unless the message lists links "written in this run before it stopped" | Read the reason |
| exit 2, `A PERSON NEEDS TO LOOK`, **"the link reads backwards"** | **A wrong-way link is in Jira now** | Remove the link it names, by hand, in Jira. **Do not run the workflow again**, not even a preview to "fix" it: its direction is wrong and whoever maintains it must correct it first |
| exit 2, `A PERSON NEEDS TO LOOK`, anything else | A write was sent and its result is not known or not as asked | Preview again. It reads both items and finds what is there |

**A batch that stops partway.** Links are written one at a time and nothing is undone. The message lists the links
written and the links not sent. It is exit 1 if Jira refused a link and nothing of it is there, exit 2 otherwise.
Either way: preview again. It finds the links that were made and offers only the rest.

## Rules it keeps

- Direction comes from the site's own phrases for the link type, never from the type's name.
- After every write the link is read back from both items, and by its own id, and compared with the sentence.
  That proves the write and the reads agree. It does not prove both are right: see "What it cannot do".
- A write is sent once. The same run never sends it again.
- One run at a time may confirm a request. A real write must be started from a terminal.
- Items' titles are other people's text: shown on screen so a person can see which items these are, never saved,
  never acted on. Jira's own words about a refusal are shown and not saved.
- The site's address is shown on screen and replaced by a marker in anything saved.

## What it cannot do

- Jira has no "create only if there is none like it" that this workflow relies on. Another run, on another computer,
  could create the same link in the same moment. The count after the write reports a double.
- It sees only the links this identity may see.
- The circle check follows links of ONE type, through at most 50 items.
- **It cannot prove its own direction.** The write and the read-back share one understanding of Jira. A real run
  shows that Jira's answers agree with it. Only a person looking at an item in Jira's own screen shows that the link
  reads the right way there. What was seen is in the proof of the quest jira-link-work.
- A real Jira may ignore a second identical link and still answer that the write succeeded. The workflow then finds
  the one link and cannot tell which run made it.
- A link type's name and phrases are the site's own text. They are shown and saved, because they are the sentence.

## Tests

    cd participant/skills/jira-link-work && python3 -m unittest tests.test_link_work
