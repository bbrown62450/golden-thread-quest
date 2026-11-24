# Story standard

Written by `participant/skills/ba-write-story/story.py standard`, at the participant's direction, for the quest
`ba-write-story`. The lists below are the lists the program checks.

A story meets this standard when another person can tell, for every part of it, whether it came from the meeting or
from the writer, and can write a test for every criterion from what the story itself gives.

**What this standard cannot do.** A meeting that said little cannot be turned into a story that leaves nothing to ask.
The writer can supply what is missing, and this standard makes them say so each time. It does not make the supplied
parts right. A story that meets it is honest about its gaps. It may still have many.

## 1. The sections, in this order

| Section | What it holds |
|---|---|
| The story | the user, and the value they gain, each citing the meeting. And what the meeting did not say about the value |
| Out of scope | what is not built. **Written first.** Each entry says why it is out and where it went |
| In scope | what is built, each entry citing the meeting and naming the criteria that test it |
| Taken as given | what the story assumes is already there. Marked as the writer's |
| Words this story defines | any word a criterion uses in a particular meaning, each SAID or ASSUMED |
| Test set-up | the data a tester uses, under the names the criteria use. Marked as the writer's |
| Acceptance criteria | numbered AC-01, AC-02 and so on. Section 3 |
| Dependencies | what the story cannot be built or tested without, or the word None |
| Open questions that still affect it | every question an assumption answers for now, and any other that bears on the story |
| Definition of done | a checklist of how the team knows the work is finished. Kept apart from the criteria |
| Source | the meeting, and every line the story cites |
| Lines of the meeting this story does not use | every other line of the record, each with the reason |

## 2. The user and the value

- **The user** is a kind of person, described so that a tester could set one up. "A customer who does not have an
  account" is a user. "A user" is not.
- **The value** is what that person can do afterwards that they could not do before, in plain words.
- Each cites the line of the meeting that says it.
- If the meeting did not say why it matters to the business, the story says that it did not. It does not make up a
  reason.

## 3. What makes a criterion testable

A criterion is testable when a tester can write its test without asking anything. Here that means all of these.

1. **It has three parts and one of each.** *Given* a starting state a tester can set up from the story's own test
   set-up. *When* one thing a person does. That may be a journey of several steps, such as completing a checkout, if the
   story defines it. *Then* one result. Two results are two criteria.
2. **The result can be seen or read.** A page shown, a message with its exact words, an email received, a thing that did
   not happen. Not a state inside the system that nobody can look at.
3. **Every amount is a number**, and so is every wait. "5 minutes", never "promptly". "Not placed" needs a time after
   which the tester stops waiting.
4. **Every message is given word for word**, in double quotes, with where on the page it is shown.
5. **It uses no undefined word.** The list is in section 4.
6. **It says what it rests on.** Section 5.

## 4. Words a criterion may not use

These mean nothing a tester can check:

fast, faster, quick, quickly, slow, easy, easily, simple, simply, intuitive, intuitively, user-friendly, friendly, seamless, seamlessly, smooth, smoothly, appropriate, appropriately, reasonable, reasonably, proper, properly, correct, correctly, valid, invalid, good, better, best, nice, clear, clearly, efficient, efficiently, robust, secure, securely, timely, promptly, soon, shortly, immediately, instantly, normal, normally, usual, usually, sensible, suitable, adequate, sufficient, relevant, some, several, many, few, etc, should, might, could, may, ideally, gracefully, responsive, modern, flexible.

A criterion may use one of them only if the story's own "Words this story defines" gives it a meaning that can be
measured. So "valid" is allowed in a story that says exactly what a valid email address is, and in no other.
Words inside double quotes are what the product shows, and are not counted.

## 5. SAID and ASSUMED

A meeting rarely says enough to test from. It says "email is required" and does not say what the customer sees when
it is missing. To write a testable criterion, somebody has to supply that. This standard lets the writer supply it,
and never lets it pass as the meeting's.

| Basis | Meaning | What the criterion carries |
|---|---|---|
| **SAID** | the meeting stated it | each line it rests on, quoted with its speaker |
| **ASSUMED** | the meeting did not state it. The writer proposes it so that the story can be tested | the words "ASSUMPTION, to be confirmed by", who confirms it, and the open question it answers |

- A criterion is one or the other. Never both, and never neither.
- A criterion that mixes a said requirement with an assumed one is split in two.
- **A SAID criterion states the meeting's requirement in the meeting's sense.** If the meeting said "make them", the
  criterion does not say "ask them". If two readings are open, the story takes one, says which, and lists the question.
- **A SAID criterion may still lean on a word the writer defined**, because the meeting says what must be true and
  rarely says how a tester sees it. Then the criterion names each such word, and the head of the story counts how many
  SAID criteria do. The program works that list out from the story's own defined words.
- The head of the story counts how many criteria are SAID and how many ASSUMED.
- An assumption is a proposal. Nobody should build on one as if it had been decided.
- **Every assumption has an open question behind it**: an assumed criterion names its own, and an assumed definition or
  piece of test set-up is covered by one in the list.

## 6. Scope

- **Out of scope is written first.** What the story refuses to build is what gives it an edge.
- Each entry says **why** it is out, and **where it went**: another work item, an open question, a refusal, or
  nowhere, because the meeting did not discuss it.
- Something the meeting mentioned alongside the story and that is being left out is named, with the line. If leaving
  it out is the writer's choice and not the meeting's, the entry says so.
- **Each in-scope entry names the criteria that test it.** An entry no criterion tests is a promise nobody checks.

## 7. Dependencies, source, and the definition of done

- **Dependencies** are listed, each SAID or ASSUMED, or the section says None.
- **Source**: every line cited anywhere in the story exists in the transcript record, and every quotation is the
  record's own words. The story never changes the record.
- **The definition of done** is a checklist about the work. It is not a place to put a requirement that should have
  been a criterion.

## 8. What this standard leaves to judgment

- Whether a criterion marked SAID says no more than its lines do. A program cannot check that.
- Whether the assumptions are sensible ones.
- Whether the criteria, taken together, cover the story.
- Whether a "Then" is really one result.
- Whether the test set-up is enough to run a test. It names the data. It cannot name what the meeting never mentioned,
  such as the other fields of a checkout.
