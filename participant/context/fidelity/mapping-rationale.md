# Mapping rationale: which source fields became canonical, and which were preserved

Written by an AI assistant (Claude) at the participant's direction, for the quest `context-preserve-source-fields`. The tables are written out from
`participant/skills/context-preserve-source-fields/fidelity.py` by its `rationale` command, so this document and the code that applies the mapping cannot disagree.

**Mapping version: 2.** Every record this mapping is applied to here is made up.

## How a field is decided

The rule is the quest's hint: **preserve first, promote later.** Nothing is dropped, so the only question for a field is whether a canonical field also carries it.
A field becomes canonical when **all three** of these hold:

1. **More than one system has it**, meaning the same thing.
2. **A question people ask across systems needs it**: what is open, what is mine, what is due.
3. **It can be given one meaning.** A status can, with the losses written down. A priority cannot yet: Jira names one, Trello has a position, GitHub has neither.

Otherwise it is preserved only. That costs nothing: it is still in the record, exactly as sent, and it can be promoted later without going back to the source.

Each field has one of three outcomes:

| Outcome | What happens to the field | How the original comes back |
|---|---|---|
| **copied** | A canonical field holds its value exactly | From the canonical field |
| **translated** | A canonical field is worked out from it. The original is also preserved, as sent | From the preserved section |
| **preserved only** | No canonical field uses it. It is preserved, as sent | From the preserved section |

A translated field is preserved as well as mapped because the canonical field cannot give it back: `in_progress` does not say whether Jira's status was
"In Review". And a copied field is checked for every record: if writing the canonical value back out would not give the source's exact characters, that
record keeps the original in its preserved section too. So "copied" in the tables below means "copied unless that would lose a character".

A field that is in a source record and in none of these tables is preserved all the same, and the check names it.

## The canonical fields

| Canonical field | Type | Meaning |
|---|---|---|
| `identity` | string | The source system, a colon, and the system's stable identifier. |
| `system` | jira, trello or github | The system the record came from. |
| `source_id` | string or number | The system's stable identifier, exactly as the source wrote it. |
| `reference` | string or number | How people refer to the item: a key, a short link, a number. It can change. |
| `title` | string | The item's name. Other people's text. |
| `status` | open, in_progress, done or dropped | Where the work stands, on four values. |
| `assignee_count` | whole number | How many people the item is assigned to. |
| `labels` | list of strings | The item's labels, by name. |
| `due_at` | UTC time or null | When the item is due. In the mapping from version 2. |
| `source_updated_at` | UTC time | When the source says the item last changed. |

`identity` and `system` are not taken from a field: `system` is which mapping was used, and `identity` is the system and `source_id`. The names, and the four
values of `status`, are those of the model `work-item/1` from the quest `context-canonical-work-item`, for the fields the two share. This mapping is a small one
of its own: that model reads records earlier skills had already tidied, and leaves out on purpose things this quest must keep.

## Jira: 19 fields considered

4 copied, 5 translated, 10 preserved only. A field inside `fields` is treated as a field of its own.

| Source field | Outcome | Canonical field | Why |
|---|---|---|---|
| `id` | copied | `source_id` | Jira's stable identifier. The identity is built from it. |
| `key` | copied | `reference` | What people call the issue. It changes when the issue moves project, so it is not the identity. |
| `self` | preserved only | none | The API address of the record. Nobody asks questions of it, but a re-sync may need it. |
| `fields.summary` | copied | `title` | Every system has a name for the item. |
| `fields.status` | translated | `status` | Jira's status object. Its category gives one of the four canonical values. The name, the id and the category are kept as sent. |
| `fields.resolution` | translated | `status` | A done issue with a resolution such as "Won't Do" is dropped, not done. Kept as sent. |
| `fields.assignee` | translated | `assignee_count` | Only the count is canonical. Who the person is, is kept as sent and never made canonical. |
| `fields.labels` | copied | `labels` | Jira's labels are already a list of names. |
| `fields.duedate` | translated | `due_at` | A day in Jira, a moment in the canonical field. The day is kept as sent. Canonical from version 2. |
| `fields.updated` | translated | `source_updated_at` | Jira writes +0000 and milliseconds. The canonical field is UTC to the second. Kept as sent. |
| `fields.created` | preserved only | none | No question asked so far needs it. Two other systems have the same thing. |
| `fields.description` | preserved only | none | Long text in another person's words. The canonical model does not carry the text of the work. |
| `fields.issuetype` | preserved only | none | Story, bug, epic. Only Jira has types, and each site names its own. |
| `fields.priority` | preserved only | none | A named priority. The other systems order work differently, so there is no one scale. |
| `fields.parent` | preserved only | none | The epic the story belongs to. Only Jira supplies a parent here. |
| `fields.timetracking` | preserved only | none | Estimates and time spent. Only Jira has them. |
| `fields.customfield_10016` | preserved only | none | Story points on this made-up site. A custom field: its number and meaning differ from site to site. |
| `fields.customfield_10020` | preserved only | none | The sprint, on this made-up site. A custom field. |
| `fields.components` | preserved only | none | Which part of the product. Only Jira has components. |

## Trello: 18 fields considered

3 copied, 6 translated, 9 preserved only.

| Source field | Outcome | Canonical field | Why |
|---|---|---|---|
| `id` | copied | `source_id` | Trello's stable identifier. The identity is built from it. |
| `shortLink` | copied | `reference` | What a card's address is built from. Not the identity. |
| `idShort` | preserved only | none | The card's number on its board. A second way people refer to it. |
| `name` | copied | `title` | Every system has a name for the item. |
| `closed` | translated | `status` | An archived card is dropped. Kept as sent. |
| `idList` | translated | `status` | The list a card is in is the only status Trello has. Which list means what is the status map's decision. Kept as sent. |
| `idMembers` | translated | `assignee_count` | Only the count is canonical. The member ids are kept as sent. |
| `labels` | translated | `labels` | Trello's labels are objects with a colour. Only the names are canonical. The objects are kept as sent, in their order. |
| `due` | translated | `due_at` | Trello writes milliseconds. The canonical field is UTC to the second. Kept as sent. Canonical from version 2. |
| `dateLastActivity` | translated | `source_updated_at` | Trello's only time of change. Kept as sent. |
| `dueComplete` | preserved only | none | A tick on the due date. It is not a status: a ticked card can sit in any list. |
| `desc` | preserved only | none | The card's description. The canonical model does not carry the text of the work. |
| `idBoard` | preserved only | none | The board. A canonical container may come later: all three systems have one. |
| `pos` | preserved only | none | The card's place in its list, which is how a Trello team says what comes first. No one scale across systems. |
| `customFieldItems` | preserved only | none | The board's own fields, such as customer impact. Each board defines its own, so there is nothing to map them to yet. |
| `idChecklists` | preserved only | none | The card's checklists, in order. A checklist item is not a work item here. |
| `badges` | preserved only | none | Counts Trello shows on the card's face. |
| `cover` | preserved only | none | How the card looks on the board. It says nothing about the work. |

## GitHub: 20 fields considered

4 copied, 4 translated, 12 preserved only.

| Source field | Outcome | Canonical field | Why |
|---|---|---|---|
| `node_id` | copied | `source_id` | GitHub's stable identifier. The identity is built from it. |
| `id` | preserved only | none | A second, numeric identifier of the same issue. |
| `number` | copied | `reference` | The issue's number in its repository. It changes on transfer, so it is not the identity. |
| `title` | copied | `title` | Every system has a name for the item. |
| `state` | translated | `status` | open or closed. Kept as sent. |
| `state_reason` | translated | `status` | Why it was closed: completed is done, not_planned is dropped. Kept as sent. |
| `assignees` | translated | `assignee_count` | Only the count is canonical. The people are kept as sent. |
| `labels` | translated | `labels` | GitHub's labels are objects. Only the names are canonical. The objects are kept as sent. |
| `updated_at` | copied | `source_updated_at` | GitHub already writes UTC to the second, so the canonical field holds it exactly. |
| `created_at` | preserved only | none | No question asked so far needs it. Two other systems have the same thing. |
| `closed_at` | preserved only | none | When it was closed. Only GitHub states this as a field. |
| `body` | preserved only | none | The issue's text. The canonical model does not carry the text of the work. |
| `repository_url` | preserved only | none | The repository. A canonical container may come later. |
| `url` | preserved only | none | The API address of the record. A re-sync may need it. |
| `milestone` | preserved only | none | A milestone, with its own due date. Not the issue's due date, so it is not mapped to due_at. |
| `locked` | preserved only | none | Whether people may still comment. |
| `author_association` | preserved only | none | The author's relation to the repository. |
| `reactions` | preserved only | none | Counts of reactions. Nobody plans work from them, and only GitHub has them. |
| `sub_issues_summary` | preserved only | none | Counts of sub-issues. A parent link may come from this later. |
| `type` | preserved only | none | GitHub's newer issue type. Jira has types too, each site naming its own. |

## Preserved fields that more than one system has

These are preserved only, and mean the same thing in more than one system. They meet the first of the three conditions above, so they are the fields most
likely to become canonical next. The check reports them from the records themselves.

| What it is | Where it is preserved |
|---|---|
| api address | jira `self`, github `url` |
| container | trello `idBoard`, github `repository_url` |
| created | jira `fields.created`, github `created_at` |
| description | jira `fields.description`, trello `desc`, github `body` |
| parent | jira `fields.parent`, github `sub_issues_summary` |
| priority or order | jira `fields.priority`, trello `pos` |
| type | jira `fields.issuetype`, github `type` |

## The mapping's versions

| Version | What changed |
|---|---|
| 1 | The first mapping. Nine canonical fields. Every due date was preserved only. |
| 2 | due_at became canonical, for Jira's `fields.duedate` and Trello's `due`. Both were preserved-only in version 1. Their original values are still preserved, because the canonical field holds a moment in UTC and neither source writes it that way. No record changed in what it preserves: a record normalized under version 1 and one under version 2 both rebuild to the same original. |

Each normalized record says which version of the mapping wrote it. Promoting a field changes which canonical fields a record has. It never changes what
can be rebuilt from the record, because the original was preserved before anyone decided it mattered.
