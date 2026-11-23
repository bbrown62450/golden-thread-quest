# Event rules: which timeline events are material

Written by an AI assistant (Claude) at the participant's direction, for the quest `github-read-comments-events`. The two
tables are written out from the rules in `participant/skills/github-read-comments-events/sync.py` by its `--write-rules`
command, so this document and the sync cannot disagree. The choice of what is material is the participant's.

## The rule

A timeline event is **material** when it changes what the issue is, who owns it, or what it is tied to. It is **noise**
when nothing about the issue changed. Material events are recorded. Noise is counted in each sync's output and is not
recorded.

## Material: recorded

| Event | Why it is material |
|---|---|
| `closed` | the issue's state changed |
| `reopened` | the issue's state changed |
| `labeled` | how the issue is classified changed |
| `unlabeled` | how the issue is classified changed |
| `assigned` | who owns the issue changed |
| `unassigned` | who owns the issue changed |
| `milestoned` | when the issue is due changed |
| `demilestoned` | when the issue is due changed |
| `renamed` | what the issue is called changed |
| `transferred` | where the issue lives changed |
| `cross-referenced` | what the issue is tied to changed: another issue or pull request points at it |
| `connected` | what the issue is tied to changed |
| `disconnected` | what the issue is tied to changed |
| `marked_as_duplicate` | what the issue is tied to changed |
| `unmarked_as_duplicate` | what the issue is tied to changed |
| `locked` | whether people may still speak on the issue changed |
| `unlocked` | whether people may still speak on the issue changed |
| `comment_deleted` | something that was said is gone |

## Noise: not recorded

| Event | Why it is noise |
|---|---|
| `subscribed` | it says who gets emails. Nothing about the issue changed |
| `unsubscribed` | it says who gets emails. Nothing about the issue changed |
| `mentioned` | it repeats what is already in the comment that did the mentioning |
| `pinned` | it says where the issue shows on a page |
| `unpinned` | it says where the issue shows on a page |
| `referenced` | a commit named the issue. That belongs with the code, and it repeats on every push |
| `commented` | it is a comment, and comments are kept as comments, by their own identifier, not as events |

## A kind the rules do not name

GitHub has more kinds of event than these tables, and adds new ones. An event of a kind that is in neither table is
**kept, and marked UNCLASSIFIED**, so that a person can decide and extend the rules.
Dropping it would be a guess that it does not matter. The sync names each such kind in its output.

## What is kept of a material event

Its GitHub id, its kind, who did it, when it happened, when a sync first saw it, and a few named details: the label, the
assignee, the milestone, the old and new title, the reason for closing, the issue or pull request that points here.

## Comments are not events

GitHub's timeline also lists every comment, as an entry of the kind `commented`. Those entries are not recorded as events.
Comments are read from GitHub's list of comments and kept by their own node ID, so that an edit updates one entry in place.
