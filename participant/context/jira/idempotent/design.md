# Design: creating a Jira item without creating it twice

**The problem.** A request to create an item times out. Jira may have created it anyway. Retrying blindly makes a
second item, and a third on the next retry.

**The rule this design follows.** A timeout is not a failure. It is "I do not know". When the workflow does not
know, it searches. When it cannot search, or the search does not settle it, it stops and asks a person.

**What it promises, and on what conditions.** Running the workflow again, or interrupting it at any point, does not
create a second item, **provided that** it is run on one computer, the local record is kept, the label is left on
the item, and Jira's search is no more than about a minute and a half behind. Outside those conditions a second
item is possible. "The limits", below, says how each case would be noticed.

The workflow is `participant/skills/jira-idempotent-create/create_once.py`. It creates one Task from one draft file.

Words used here:

- **Draft:** a small file giving the project and the title of the item wanted.
- **Key:** the made-up word that marks one intended creation. Not a Jira issue key such as `ABC-12`.
- **Preview:** what the workflow would send, shown before anything is sent.
- **Fingerprint:** a short code worked out from one preview: the project, the title, the draft file, the allowlist,
  the key, and the time. A person confirms a preview by giving its fingerprint. It is good for 15 minutes, for one
  write, and only while the draft and the allowlist are unchanged.
- **Sandbox allowlist:** the file listing the projects this workflow may write to.
- **State folder:** the folder where the workflow keeps its local records. Called `STATE` below.

## How a creation is keyed

- **One draft, one key.** The first time a draft is previewed, a key is made for it: `gtq-key-` and 16 random
  characters.
- **The key is saved before anything is asked of Jira,** and every later run reads it from that saved record.
- **The key is not worked out from the title.** Correcting a typo in the draft and retrying keeps the same key. Two
  drafts with the same words get different keys, so making two similar items on purpose still works.
- **The key is never replaced.** If a creation is tried a second time, after the checks below, it carries the same
  key. So if the first item turns up after all, two items carry one key, and that can be seen.

## Where the key is stored

| Place | What is there | Why there |
|---|---|---|
| **In Jira** | The key is a **label** on the item. It is part of the request that creates the item | A label is the one place on an item Jira can search for exactly. The item never exists without its key |
| **Locally** | `STATE/intents/DRAFT-NAME.json`: the key, the state of the creation, each request sent, the time of each empty search, and, once known, the item's issue id and issue key | It is what a rerun reads to learn that an earlier run may have written |
| **In the result record** | `participant/context/jira/results/idempotent-create.md`: the issue key, issue id, the key label, project, times and confirmer | The record a person reads. The workflow does not read it back |

For real runs `STATE` is under `local-data/`, which Git ignores. The local record is written whole or not at all,
and pushed to the disk before the workflow goes on.

## The states of a creation

The local record is always in one of five states.

| State | Meaning | What a run may do |
|---|---|---|
| `new` | Nothing has been sent, or Jira refused the request and created nothing | Preview, then confirm |
| `sending` | Written **just before** the request is sent | If a later run finds this, an earlier run ended without recording an answer. **Outcome not known.** Only `resolve`. A confirmation is refused |
| `uncertain` | The request was sent and no usable answer came back | **Outcome not known.** Only `resolve`. A confirmation is refused |
| `released` | The unknown outcome was looked into and nothing was found | A **new** preview and a **new** confirmation. The old fingerprint is void |
| `linked` | The item exists and its issue id is recorded | Nothing is created again. A preview says so, reads the item back, and issues no fingerprint |

Writing `sending` to disk before the request goes is what makes a crash safe: the next run can tell "nothing was
sent" from "something may have been sent".

**One run at a time.** A confirmation first takes a claim on the draft: a file made with "create only if absent".
A second confirmation started at the same moment is refused before it asks Jira anything. A claim left by a killed
run can be taken over after 10 minutes; the run that takes it reads the record afresh.

## How an uncertain outcome is resolved

`resolve` is the rerun after an interruption. **It can only read Jira. It is given no way to write.** It searches
Jira for items carrying the key.

| The search returns | What happens |
|---|---|
| **Exactly one item,** a Task, in the project the request was sent to | It is recorded locally (`linked`). Nothing is created |
| **None** | "Not found **yet**". Nothing is created and the state does not change. The time of the empty search is noted. See below |
| **More than one,** or one in another project, or one that is not a Task | It stops. Nothing is recorded. A person decides |
| **The search fails** | It stops. See the next section |

**"None" is not trusted at once.** Jira's search can be behind what Jira holds. The record is released only after
**two** empty searches that count:

- each **60 seconds or more after the request ended.** If the run was killed, when the request ended is not known,
  so it is taken to have lasted the full 30 seconds a request may wait;
- the two **30 seconds or more apart;**
- and each time Jira also says this identity may still see the project, and a search of the project returns
  something. An identity that has lost its access gets empty answers too, and those say nothing.

Even then the workflow says that this is not proof. Creating then needs a new preview, read and confirmed by a
person. The earlier confirmation is never reused for a second write.

**These numbers are choices, not measurements.** I do not know how far behind Jira's search can be. If it is
further behind than this, a second item is possible. It would carry the same key.

## What happens if the search itself fails

A search has failed when no answer comes back, Jira answers with an error, the answer cannot be read, the answer
says there are more results than it gave, it returns an item that does not show the key, or it is empty and Jira
does not confirm that this identity can still see the project.

**A failed search is never read as "nothing found".** What happens depends on where it fails:

| Where | What happens |
|---|---|
| In `resolve` | It stops with "not known". **Nothing is created. The record is left exactly as it was.** It does not count as an empty search. It prints the search to run by hand in Jira |
| In `preview` | No preview and no fingerprint are issued, so there is nothing to confirm |
| In `confirm`, just before the write | The write is not sent. The record stays `new` |
| In `confirm`, after Jira refused the write | The refusal is not believed. The record becomes `uncertain` |

In every case the next step is a person's: run `resolve` again later, or look in Jira by hand. There is no limit on
how often `resolve` may be run, and it never gives up by itself.

## When Jira's answer to the write is believed

- **Jira returns the new item:** recorded at once, then read back.
- **Jira answers 400, 401, 403 or 404:** this is Jira's own statement that it refused. It is believed unless a
  search for the key just afterwards fails or finds an item. If the search finds nothing, nothing was written.
  Here one empty search is enough, because it is not the evidence: the refusal is.
- **Anything else,** including a server error, "too many requests" or no answer: not known.

A write is sent once. The same run never sends it again.

## Who can confirm

A confirmation is the preview's fingerprint and a name, given to the `confirm` command. Against a real Jira the
command must also be started from a terminal. That keeps out a program that has no terminal. It does not prove who
typed. The real protection is the rule that a person runs real commands themselves.

## The limits, and how each would be noticed

| Limit | What can happen | How a person would notice |
|---|---|---|
| Jira cannot be asked to create "only if no item has this label" | A run on **another computer**, with a copy of the state folder, could create the same item in the same moment | Both items carry the key. `check`, and every read-back after a write, says "more than one" |
| Jira's search is further behind than the waits allow | The record is released while the item exists, and a second is created | The same: two items, one key |
| The local record is lost, the draft file is renamed, or another state folder is given | It is a new draft to the workflow, with a new key. The key search finds nothing | The preview's second check lists items in the project with the same title, by issue key. It only points: a person has to notice |
| Someone removes the label from the item | An unrecorded item is no longer found by its key | The same title check. A recorded item is still known by its issue id, and `check` says the label is gone |
| The search shows only what this identity may see | An item hidden from it is not found | The access check above catches a lost project. It does not catch one hidden item |
| The waits are measured by this computer's clock | A clock moved forward shortens them. A clock moved back is refused | Not noticed by the workflow |

## When the workflow stops and a person must decide

The workflow has no command that overrides it. What a person does:

- **An item with the key is in another project, or two carry the key:** put Jira right by hand (move it back, or
  delete the extra one), then run `resolve` again.
- **The label was removed:** put it back on the item by hand, then run `resolve`.
- **A recorded item was deleted in Jira:** the workflow will not create it again. To start over, a person removes
  the draft's record file from the state folder. The workflow never deletes a record.
