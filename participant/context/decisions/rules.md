# The rules of the decision log

Written by an AI assistant (Claude) at the participant's direction, for the quest `context-decision-log`. The tables in this document are written out from
`participant/skills/context-decision-log/decisions.py` by its `rules` command, and that file is what checks the log. So the rules and the check cannot disagree.

The log is `log.md`, beside this file. The project in it is made up.

## 1. Every entry is one of three things

An entry has exactly one status, written in its heading and again in its `status` field:

- a **decision**: someone with the right to approve has approved it, and the entry shows who, where and in what words;
- a **proposal**: someone has suggested it. It may be widely liked. It is not approved;
- a **question**: someone has asked. Nobody has answered with a decision.

So that an entry still says what it is when one sentence of it is copied into a ticket, its statement begins with a fixed opening:

- a decision begins `**Decision.**`
- a proposal begins `**Proposal, not decided.**`
- a question begins `**Question, not answered.**`

## 2. What makes an entry a decision

An entry is a decision only if it records all four of these. If one is missing, it is a proposal.

1. **An approver who may approve it.** A role, and the right role for the kind of decision:

   | Kind of decision | What it covers | Approved by |
   |---|---|---|
   | product | What is built, for whom, and when it is delivered. | the product owner |
   | technical | How it is built: the design, the tools, where it runs. | the tech lead |
   | security | What data is kept, for how long, and who may see it. | the security lead |

2. **An act of approval, in the approver's own words**, quoted in `approval_words`. The words must say that this is approved or declined: one of
   "approved", "i approve", "we approve", "i sign this off", "signed off", "go ahead with", "not approved", "declined", "i decline".
3. **The place** those words are recorded, in `approved_in`, with a reference a reader can look up.
4. **The date.**

### What is not an approval

- **Agreement in conversation.** Words such as "sounds good", "makes sense", "no objection", "no objections", "fine by me", "fine with me", "looks good", "ok". They show that people like an idea. They do
  not show that the person answerable for it has said yes to it.
- **Silence**, or nobody objecting.
- **Agreement from a role that cannot approve that kind of decision.** A tech lead who likes a retention period has not approved it: retention is a security
  decision.
- **A report of an approval.** "The product owner said it was fine" is somebody else's words. The entry needs the approver's own, and where they are.
- **Approval of something nearby.** The words must be about this decision.

Agreement is still worth keeping. A proposal records it in `support`: who agreed, how, and where. It stays a proposal.

## 3. How a proposal becomes a decision

The proposal's entry is not changed. A **new entry** is added, with the status decision, the four things in section 2, and `promotes:` naming the proposal.
From then on the proposal is shown as "approved, by" that entry. A proposal that the approver declines gets a new decision entry with `rejects:`.
A proposal is approved or declined once.

## 4. How a decision is superseded

The decision's entry is not changed. A **new decision** is added, approved in the same way, with `supersedes:` naming the decision it replaces. From then on
the older one is shown as "SUPERSEDED by" the newer, and drops out of the list of current decisions. A decision is superseded once: a third decision
supersedes the second, not the first. To withdraw a decision without replacing it, the approver approves a new decision that says so, and it supersedes the old one.

## 5. How a question is answered

By a decision with `answers:` naming the question. A proposal may also name a question it offers an answer to. The question stays open until a decision answers it.

## 6. The log only grows

- Entries are numbered `E-001`, `E-002` and so on, with no gaps, in the order they were written. Dates never go backwards.
- An entry is never edited and never removed. `ledger.json` holds a checksum of each entry from the moment it is sealed, and the check reports an entry whose
  text no longer matches, or that has gone.
- Whether an entry still stands is never written into it. It is worked out from the entries that point at it.

## 7. Finding what is decided now

The top of `log.md` holds a part that `decisions.py view` writes from the entries: the current decisions, what is not decided, proposals that something else
treats as decided, current decisions with no work item, and what became of every entry. Nobody edits it. The check fails if it is not exactly what the entries say.

## 8. A proposal is never shown as a decision

- A proposal or a question may not have the fields `approver`, `approved_in` or `approval_words`.
- Its title and statement may not use wording that presents it as settled, outside a quotation: decided, approved, signed off, final, "we will", agreed,
  "the decision", settled, confirmed.
- If another document presents a proposal as decided, the proposal says so in `treated_as_decided_in`, and lists in `built_on_it` the work started on it. The
  log reports these at the top. It does not turn the proposal into a decision.

## 9. Every entry cites its source

`source` says where the entry comes from, with a reference a reader can look up, such as `DOC-4, section 2`. A decision also has `approved_in`.

## 10. The fields

| Field | May appear on | Required on | Meaning |
|---|---|---|---|
| `status` | decision, proposal, question | decision, proposal, question | decision, proposal or question. Exactly one, and the same word as in the entry's heading. |
| `date` | decision, proposal, question | decision, proposal, question | The day the entry was written, YYYY-MM-DD. |
| `title` | decision, proposal, question | decision, proposal, question | One line. A question's title ends with a question mark. |
| `source` | decision, proposal, question | decision, proposal, question | Where the entry comes from: a document, ticket or meeting record, with its reference. |
| `raised_by` | decision, proposal, question | proposal, question | The role of whoever proposed or asked. A role, not a person's name. |
| `kind` | decision, proposal | decision | product, technical or security. It settles who may approve. |
| `approver` | decision | decision | The role that approved. It must be the role the rules allow for this kind. |
| `approved_in` | decision | decision | Where the approval is recorded, with its reference. |
| `approval_words` | decision | decision | The approver's own words of approval, quoted from that place. |
| `support` | proposal, question | none | Agreement that is not approval: who agreed, how, and where. Recorded so that it is not lost, and not mistaken. |
| `treated_as_decided_in` | proposal | none | A place that wrongly presents this proposal as decided. |
| `built_on_it` | proposal | none | Work items that were started on this proposal as if it were decided. |
| `affects` | decision, proposal, question | none | The work items the entry affects. |
| `promotes` | decision | none | The proposal this decision approves. |
| `rejects` | decision | none | The proposal this decision declines. |
| `supersedes` | decision | none | The earlier decision this one replaces. |
| `answers` | decision, proposal | none | The question this entry answers. A proposal only offers an answer: the question stays open. |

## 11. What the check cannot know

The check reads the log. It cannot open the document an entry cites, so it cannot tell whether the approver really wrote those words there. It checks that the
words are given, quoted, and are words of approval. Whether they are true is for a person to check, by following the reference.

This log is kept by a person. The skill adds no entry and approves nothing. **Nobody records a decision on someone else's behalf**: an entry is a decision
because the approver's own words exist at the place it names.
