# Which changes in a story's history are kept

**Written by a tool** (`participant/skills/jira-read-comments-history/sync_comments.py rules --write`), from the same lists the sync applies.
To change a rule, change the list in the tool and write this file again.

## The rule in one sentence

**A change is material if it changes what the work is, where it stands, who has it, how urgent it is, when it is due, or what it depends on.**
Everything else in the history is noise for a reader.

- A field is known by the name Jira gives it, compared without regard to capitals: `Link` and `link` are the same field.
- **A field the site's administrators added is never material, whatever it is called.** Jira marks such a field "custom". Its values are
  free text, and a custom field someone named "Status" is not the story's status. It is reported as unlisted.

## Material: kept

| Jira's name for the field | Why | What is kept |
|---|---|---|
| `status` | Where the work stands. | The old and the new status are kept. |
| `assignee` | Who has the work. | Kept as assigned, reassigned or unassigned. No person is kept. |
| `priority` | How urgent it is. | The old and the new priority are kept. |
| `duedate` | When it is due. | The old and the new date are kept. |
| `issuetype` | What kind of work it is. | The old and the new type are kept. |
| `summary` | The title. | Kept as the fact that it changed. The old and new titles are not kept. |
| `description` | The description. | Kept as the fact that it changed. The texts are not kept. |
| `link` | What the work depends on: a link to another item was added or removed. | The other item's key is kept, if Jira gives one. |
| `parent` | The story was moved under another parent. | The keys are kept, if Jira gives keys. |
| `issueparentassociation` | Jira's other name for a move under another parent. | Kept as the fact that it changed. |

For each change kept: when Jira says it happened, when a sync first noticed it, the time between the two, and Jira's identifier
for the history entry with the place of the change inside it. That identifier is what stops a change being added twice.

## Noise: left out

| Jira's name for the field | Why it is left out |
|---|---|
| `rank` | The order of cards on a board. It changes every time someone drags a card. Urgency is kept from the priority field instead. |
| `labels` | Tags. Useful for finding things, and they do not change what the work is, who has it, or when. |
| `sprint` | Which sprint the card sits in. Planning moves it back and forth. The due date is what is kept for "when". |
| `attachment` | A file was added or removed. The file is not copied, and its name can be private. |
| `watchers` | Who is following the story. |
| `timespent` | Time logged. |
| `timeestimate` | The remaining estimate. |
| `timeoriginalestimate` | The original estimate. |
| `worklogid` | A work-log entry. |
| `resolution` | Set and cleared by the workflow when the status changes. The status change is what is kept. |
| `resolutiondate` | The same. |
| `comment` | Comments are kept in their own right, by identifier, not from the history. |
| `remoteissuelink` | A link to something outside Jira, such as a web page. |

A sync counts what it left out, by field, and prints the counts. It keeps nothing of them.

## A field on neither list

It is **not kept**, and it is **not hidden**: the sync prints it as UNLISTED, with its name and how many times it appeared.
That is the prompt to decide which list it belongs on. This page does not rule on a story-point estimate, a fix version, a component,
a reporter or a flag: by the sentence at the top a fix version or a component could well be material, and none of them is kept today.
The name printed is the field's name, as the site's administrators chose it.

## Three things this page does not hide

- **Two statuses with the same name.** Jira can record a change from one status to another of the same name. It is kept, and says so.
- **A story moved to another project** gets a new key. A sync asked for it by its old key is refused, and says the story has moved.
- **Rank on some teams is the priority.** Where the order of the backlog is how urgency is shown, leaving rank out loses that. Here urgency is
  taken from the priority field. A team that works the other way should move `rank` to the first list.

## People, and other people's words

- **No person is kept**: no name, email address or account identifier. A change of assignee is kept as assigned, reassigned or unassigned
  (or as "changed", if Jira gives neither an old nor a new assignee).
- **Whether a comment was edited by its author or by someone else** is kept, as those words, or as "unknown" if Jira does not say who.
  Two account identifiers are compared and dropped.
- **A link or a parent is kept by the other item's key only when Jira gives exactly a key.** Nothing is picked out of a sentence. Otherwise
  it is kept as "a link added", "a link removed", "a link changed" or "no key given".
- **A title or description is not kept.** Its change is kept as the fact that it changed.
- **A comment's text is kept**, because a copy of the comments is what this is for. A mention in it is kept as "[a person]".
- **Not always the whole comment.** Unseen characters are replaced by a question mark. Text over 8000 characters is cut. A date, a card or
  an image is kept as its kind in square brackets. In each case the page says so under the comment.

## Comments: what a sync does

| What Jira shows | What the copy does |
|---|---|
| A comment the copy does not have | Added, once, under Jira's identifier |
| A comment whose words differ from the copy's | The text is replaced in place. A note under it gives Jira's edit time, when it was noticed, the time between, a checksum of the text replaced, and whether its author or someone else edited it |
| A comment with the same words, changed in some other way (formatting, a link's target, only its edit time) | The text is left. A note under it says so. It is not called an edit |
| A comment the copy has and Jira no longer lists | It is asked for by its own identifier. If Jira answers 404 it is marked "not returned by Jira any more", with the sync that first found it missing. **Its last text is kept, and it is never taken out** |
| A marked comment that Jira lists again | The mark is taken off, and a note says when it came back |
| Nothing new | Nothing is written. The files are byte for byte what they were |

- **Comments are matched by identifier only.** Two comments with the same words are two comments.
- **Deleted text is retained.** That is a choice: the mark is only useful if it shows what went. It also means this copy holds words someone chose to remove.
- **"Not returned" is not always "deleted".** A comment hidden from the account that reads looks the same from here.
- **Only the latest text of an edited comment is kept,** with a checksum of what it replaced. Two edits between two syncs are seen as one.
- **A sync changes nothing unless it read everything.** A page that fails must not look like deleted comments.
- **The notes file is never written.** `NAME.notes.md` belongs to the person. The sync prints its checksum before and after. The tool
  refuses to write any file of its own to a place named like a notes file, or to a place that is the notes file under another spelling or name.
