# Extraction rules: candidate work items from a meeting record

Written by `participant/skills/ba-extract-work-items/extract.py rules`, at the participant's direction, for the quest
`ba-extract-work-items`.

An item is a draft for a person to decide on. Nothing is created in any tracker.

## 1. How an item is recognized

A line gives an item when it states something to **build, change or do**. Three kinds of line do that:

- a line that says what the product will do, or must do;
- a line that proposes a change, whether or not anyone accepted it;
- a line in which a person takes a task on, in words such as "I'll" or "let me".

The item's title and its one sentence of intent hold **only what the cited lines say**. A word that is in no cited line
is not in the item. Where the meeting used a word and left its meaning open, the item leaves it out and says so.

## 2. How settled an item is

Every item carries one mark, taken from the decisions file for the same meeting, and names the item there it rests on.

| Mark | Meaning | Rests on |
|---|---|---|
| `decided` | rests on a decision in force | a decision in force |
| `PROPOSED, NOT DECIDED` | somebody proposed it and it did not become a decision | a proposal |
| `OPEN, NOT SETTLED` | the meeting left the matter undecided | an open item |
| `follow-up` | a task one person took on in words | a decision or an open item |

An item that is proposed or open is still listed, so that a person planning from the file knows it was raised. Its note
says, in capitals, that it is not decided.

## 3. One item or two

- **One item** when two mentions describe the same change to the same thing. Both mentions are cited, and the heading says
  "merged from 2 mentions". Saying a thing again later, restating it as an acceptance criterion, or adding a detail to it
  is the same work.
- **Two items** when one could be finished and delivered without the other.
- **A detail is not an item.** A rule the work must follow, such as a required field, is cited inside the item it belongs to,
  as a line that supports part of the intent.
- **One line can hold two pieces of work.** Then each item cites it, and the first item's note says which other item shares
  the line.
- **A later version replaces an earlier one.** If the meeting changed its mind, there is one item, for what stood at the
  end. The earlier lines are cited as history.

## 4. What the meeting did not say

Six things are asked of every item. For each, the item cites the line that says it, or says NOT SAID.

| Asked | Meaning |
|---|---|
| Owner | who will do it |
| Size | how large it is |
| Due | when it is wanted |
| Done | what finished looks like |
| Depends on | what it waits for |
| Condition | anything it is subject to |

**Nothing is filled in.** No owner is inferred from who spoke most. No size is inferred from how the work sounds. A date
is given only if a line gives one. A partial answer is recorded as what was said, in the meeting's own terms, with its
limits: "a rough guess only".

## 5. What is left out

No item is made from:

- **a question nobody turned into work.** Asking whether something should happen is not saying that it should;
- **an answer its speaker took back**, or a decision the meeting reversed;
- **an objection or an expectation** that nobody stated as work;
- **an estimate, a fact or a contact detail;**
- **a wish with no commitment.** Saying what one would want to do first takes nothing on;
- **a line that reads like an instruction** to a tool or a reader. It is something a person said;
- **anything the extractor thinks the work will need** and no line says.

The ones a person writing from memory would most likely have written are listed in the file under "Not created", each
with the lines that could tempt and the reason. Every other line of the record is listed with why it gave no item.

## 6. What these rules leave to judgment

- Whether two mentions are the same work, or a detail of it, or separate work.
- Whether the item's sentence says more than its lines do. A program cannot check this.
- Whether a person took a task on, or only said what they might do.
- How much of a partly answered question counts as said.
