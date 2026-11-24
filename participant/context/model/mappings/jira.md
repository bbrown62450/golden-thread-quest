# Mapping: Jira to the canonical work-item model

Written out from `participant/skills/context-work-item-model/normalize.py` by its `--write-docs` command. Model version `work-item/1`.

## What is read

- `jira/stories/*.md`, written by the jira story skills, format `jira-story/1`
- `jira/assigned/stories.json`, written by jira-read-assigned

## The stable identifier

The issue `id`, a number Jira never changes. Not the `key` (DEMO-3), which changes when an issue moves to another project.

## Canonical fields, and where each comes from

| Canonical field | From Jira |
|---|---|
| `identity` | `jira:` + `id` |
| `title` | `summary` |
| `status` | `status.statusCategory.key`: `new` -> open, `indeterminate` -> in_progress, `done` -> done. If the `resolution` is one the status map lists as dropped, done becomes dropped. If no category was saved, the status `id` is looked up in the status map. |
| `status_basis` | stated when the category was saved. inferred when the status map was used. |
| `assigned_to_me` | `assignee.accountId` equals `jira.my_account_id` in the status map. unknown if that is not set. |
| `assignee_count` | 1 if `assignee` is set, else 0. Jira has one assignee. |
| `blocked` | yes if `issuelinks` holds a link whose type's inward name is one the status map lists (default "is blocked by") and that points inward to this issue. no if `issuelinks` was saved and holds none. unknown if `issuelinks` was not saved. |
| `container` | kind project, `project.id`, `project.name` |
| `parent` | `jira:` + `parent.id` |
| `labels` | `labels` |
| `due_at` | `duedate`, taken as the start of that day, UTC |
| `created_at` | `created` |
| `source_updated_at` | `updated` |
| `source_reference` | `key` |
| `source_url` | `source_url` if saved. Otherwise `jira.site_url` from the status map + `/browse/` + `key`, marked built. |
| `retrieved_at` | `retrieved_at` |
| `sync_run` | the skill and the run's `synced_at`, or `retrieved_at` when the record is a single read |

## Statuses, and what is lost

- A status's own name is lost from the canonical field. "In Review" and "In Progress" are both in_progress. The name is kept in `jira.status`.
- Jira's "done" category covers both finished and abandoned work. Only a resolution listed in the status map turns it into dropped. An abandoned issue with no resolution, or one not on the list, is counted as done.
- A due date is a day in Jira and becomes a moment: midnight UTC at the start of that day.

## Kept as source fields

These are kept in the record's source block, under the `jira.` prefix, as Jira has them.

- `jira.key`
- `jira.project`
- `jira.issuetype`
- `jira.status`
- `jira.resolution`
- `jira.priority`
- `jira.parent`
- `jira.issuelinks`
- `jira.components`
- `jira.fixVersions`
- `jira.preserved_fields`

## Source fields that are not mapped

| Jira has | Why it is not carried |
|---|---|
| `reporter`, `assignee` as a person | Non-goal: who the people are. |
| the description, the comments, `description_notes` | Non-goal: the text of the work. |
| `preserved_fields`: custom fields, `timetracking`, `votes`, `watches` | Their names are kept in `jira.preserved_fields`. Their values stay in the saved record. |
| `removed_before_saving` | It describes the saved file, not the work item. |

## Canonical fields Jira cannot supply

| Field or value | Why |
|---|---|
| a position in a list | Jira's rank is a custom field that differs from site to site. It was not saved. |
| links to the pull requests that delivered the work | They are in Jira's development panel, which the saved records do not hold. |
