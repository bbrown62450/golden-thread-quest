# Transition rules

**Written by a tool** (`participant/skills/jira-transition-status/transition.py rules`). Read from a real Jira, site fingerprint 4aabe3d08fbad6b1. Nothing was written to Jira.

A move is what Jira calls a transition. **In the tables for each item below, the move, its id, the two statuses and the fields were read from Jira's workflow for the item named,** at the status
the item had when it was read. None of those is assumed. The two sections before those tables, and the last column of each table, are **this tool's own statements**, the same on every run.

## What Jira does and does not tell (this tool's statements, not read on this run)

- Jira lists the moves open **to this identity, from the item's present status**. To see the moves from another status, an item in that status must be read.
- **Conditions.** A move that a workflow condition hides from this identity is not listed at all, and Jira does not say why. So the condition for every move below is the same:
  Jira offered it. A move that is not listed is refused by this workflow, whatever the reason Jira left it out.
- **Required fields.** Jira says which fields a move's form asks for, and which are required. That is read, and shown for each move.
- **A required field is only seen if it is on the move's form.** A workflow can also reject a move with a rule of its own (a validator). Jira does not list those. Such a move is
  previewed, and Jira refuses it at the write. The tool then reads the item and reports that nothing was written.
- **Resolution.** Jira does not say whether a move will set or clear the resolution. It is read back after the move.
- **"Done" means the status's category is `done`,** as Jira gives it. The status's name is not looked at.
- **Subtasks are the ones Jira lists on the item for this identity.** One that Jira does not list is not seen. Stories under an epic are not subtasks, and are not looked at.

## What this workflow supports (this tool's rules)

It sends the move and nothing else: no field, no comment. So, for a move Jira offers:

| The move | Supported | Why |
|---|---|---|
| has no required field, and does not lead to a done status | yes | |
| has a **required field** | **no** | The workflow cannot fill it in. Make the move in Jira, where the form can be seen |
| has optional fields only | yes | They are listed in the preview as not sent |
| leads to a **done** status, and every subtask is done or there are none | yes | The resolution is read back, and an empty one is reported for a person to look at |
| leads to a **done** status while a **subtask is not done** | **no** | Refused before the preview. No override. Finish the subtasks first |
| leads to a **done** status and a subtask's status **cannot be read** | **no** | "Could not check" is not "none open" |
| is one of two offered moves to the same status | **no** | The request names a status, and would not say which move is meant |

## SCRUM-25, read at the status "In Progress"

Issue id 10024, project SCRUM, type "Task". Status category `indeterminate`. Resolution: none. Subtasks: 0, of which 0 not done.

| Move (Jira's id) | From | To (category) | Required fields | Optional fields | Supported here | What else it touches (this tool's expectation) |
|---|---|---|---|---|---|---|
| "To Do" (11) | "In Progress" | "To Do" (`new`) | none | none | yes | Neither status is a done status, so the resolution should stay as it is (empty). It is read back after the move. Subtasks: 0, of which 0 not done. A move of the parent does not move them |
| "In Progress" (21) | "In Progress" | "In Progress" (`indeterminate`) | none | none | yes | Neither status is a done status, so the resolution should stay as it is (empty). It is read back after the move. Subtasks: 0, of which 0 not done. A move of the parent does not move them |
| "In Review" (31) | "In Progress" | "In Review" (`indeterminate`) | none | none | yes | Neither status is a done status, so the resolution should stay as it is (empty). It is read back after the move. Subtasks: 0, of which 0 not done. A move of the parent does not move them |
| "Done" (41) | "In Progress" | "Done" (`done`) | none | none | yes | It leads to a done status: reports will count the item as finished. Jira may set a resolution; whether it does is not known before the move, and is read back after it. Subtasks: 0, of which 0 not done. A move of the parent does not move them |
