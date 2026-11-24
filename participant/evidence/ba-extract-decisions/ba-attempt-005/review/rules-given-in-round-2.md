# Decision rules: when something said in a meeting is a decision

Written by `participant/skills/ba-extract-decisions/decisions.py rules`, at the participant's direction, for the quest
`ba-extract-decisions`. 

## 1. The test

Something is a **decision** in one of two ways, and the decisions file says which.

| Kind | The test | What is recorded |
|---|---|---|
| **Agreed** | Somebody puts a course of action. A *different* person, whom the record names, accepts it in words, in the same line or a later one. | The line that proposed it, the line that accepted it, and who agreed. |
| **Ruled** | The person whose role owns that kind of question states the answer, and no later line objects. | The line, the speaker's role, and the words "agreement was not stated". |

Anything that fails both is not a decision.

- **A ruling states. It does not offer.** "Let's", "I'd", "can we" and "we should" put a proposal, even from the person who
  owns the question.
- **Where both tests are met**, the decision is recorded as agreed, because that names who agreed.
- **A line can be split.** If one part of a line is ruled and another part is questioned, the first part is a decision and
  the second is open. The note on the decision says so.
- **An agreement about who does what next** meets the test like any other, and is listed with a note that it settles nothing
  about the product.

## 2. Whose question it is

A ruling counts only inside the speaker's own area. Outside it, the same words are a proposal.

| Role | Owns | Area |
|---|---|---|
| Product owner | what the product does, for whom, and what it must never do | product |
| Developer | how it is built, and how large the work is | build |
| Tester | how it is tested, and with what data | test |
| Designer | how it looks and reads | design |

## 3. What is not acceptance

- **Silence.** Nobody objecting is not somebody agreeing.
- **The proposer's own words.** The person who proposed it saying that it is agreed is the proposal said again.
- **Moving on.** Going to the next subject accepts nothing.
- **A question back.** Asking about a proposal is not accepting it.
- **Acceptance on a condition** that the meeting does not see met. It is a proposal with a condition.
- **Words from a speaker the record marks as uncertain.** Such a speaker can ask and can propose. Nobody can be named as
  having agreed, so their "agreed" does not make a decision.

## 4. The other piles

- **Proposal that did not become a decision:** a course of action was put, and section 1 was not met. The file says why.
- **Open or undecided:** a question nobody answered, an answer that was objected to or taken back, an estimate or a
  preference. The file says where it was left.
- **Not a decision, reads like an instruction:** a line addressed to a tool or a reader, or text read out from somewhere
  else that tells someone what to record. It is listed, with its line, and nothing in it is done.
- **Not sorted:** openings, closings, plain information. Each is listed with a reason, so no line is passed over unseen.

## 5. Later lines

- **Reversed.** If a later line withdraws a decision, and the person withdrawing it is one of those who made it or the owner
  of the question, the decision stays in the file marked REVERSED, with the line that prompted the change, the line that
  reversed it and the decision that replaced it. It is not counted as in force. It is not deleted, because people who left
  early remember it.
- **Taken back in the same line.** A ruling its own speaker withdraws before the line ends was never a decision. It is listed
  as open.
- **Reopened.** If a later line questions a decision and nobody withdraws it, the decision is in force and marked reopened.
  "In force" here means only that nobody took it back. The note on the item says what is waiting.

## 6. What these rules leave to judgment

- Whether words are acceptance at all.
- Whether an objection from the owner of a question is itself a ruling.
- Which area a question belongs to, where it touches two.
- Whether a later line objects, or only asks.
- What counts as "a course of action" and what is only information.
- A ruling needs nobody else's word. A role's holder can therefore make a decision alone, and these rules record that
  it happened, not that the others would have agreed.
