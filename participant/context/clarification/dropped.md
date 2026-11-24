# Questions considered and dropped

Each of these came from a finding of the ambiguity review, the same way the questions in `questions.md` did.
Each was dropped for one reason: every answer it could get leads to the same pieces of work. Written by
`questions.py build` and tested by its `check`.

Dropped means that building does not wait for the answer. It does not mean that nobody needs to know. Where
something is still needed, the entry says what and by when.

| Dropped | From | Question | Still needed |
|---|---|---|---|
| C-02 | F-02 | Are booking records deleted after 12 months or after 24? | A value |
| C-03 | F-02 | Must a staff user's history cover the whole period for which records are kept? | A value |
| C-07 | F-04 | Is a booking's survival after a fault checked by an automated test or by hand? | A choice by the test team |
| C-09 | F-06 | Which browsers and versions must the website support? | A value |
| C-17 | F-05 | If the reminder is timed from each booking, how many minutes before the start is it sent? | A value |
| C-16 | F-09 | If the slot has its own marking, is REQ-02 reworded to list three markings? | Nothing |

## C-02

**Question considered:** Are booking records deleted after 12 months or after 24?

- Finding: F-02 (REQ-14 and NFR-04, contradictory, effort large)
- From the finding's question: "For how long are booking records kept"

| Answer | Work it leads to | Pieces |
|---|---|---|
| A. After 12 months | The deletion job and the history view are built, with the period set to 12 months. | B-01, B-02 |
| B. After 24 months | The deletion job and the history view are built, with the period set to 24 months. | B-01, B-02 |

- Why it is dropped: Either answer builds the same deletion job and the same history view. Only a number in a setting differs.
- Still needed: A value. The retention period, before release. There is no safe value to work with meanwhile: 12 months breaks REQ-14 as written and 24 months breaks NFR-04 as written. One of the two requirements has to be reworded by whoever owns them.

## C-03

**Question considered:** Must a staff user's history cover the whole period for which records are kept?

- Finding: F-02 (REQ-14 and NFR-04, contradictory, effort large)
- From the finding's question: "is that the period a staff user's history must cover?"

| Answer | Work it leads to | Pieces |
|---|---|---|
| A. Yes, all of it | The history view lists every record that still exists. | B-02 |
| B. No, a shorter period | The history view lists records back to its own number of months. | B-02 |

- Why it is dropped: Either answer builds the same history view. A shorter period is a second number in a setting.
- Still needed: A value. The history period, before release. Until then it is taken to be the retention period, whatever that turns out to be.

## C-07

**Question considered:** Is a booking's survival after a fault checked by an automated test or by hand?

- Finding: F-04 (NFR-05, untestable, effort medium)
- From the finding's question: "how is its survival to be checked after each?"

| Answer | Work it leads to | Pieces |
|---|---|---|
| A. By an automated test | Nothing in the product changes. A test stops the server and looks for the booking. | none |
| B. By hand, in the quarterly restore test | Nothing in the product changes. A step is added to the restore test. | none |

- Why it is dropped: Neither answer changes what is built. It decides how the built thing is tested, which the test team can settle without the product owner.
- Still needed: A choice by the test team. The test method, once C-06 is answered.

## C-09

**Question considered:** Which browsers and versions must the website support?

- Finding: F-06 (NFR-03, vague, effort medium)
- From the finding's question: "Which browsers and which versions must the website support"

| Answer | Work it leads to | Pieces |
|---|---|---|
| A. Two desktop and two mobile browsers, current version only | The same pages are built. The list of browsers they are tested in is shorter. | B-04 |
| B. A longer list, with the previous version of each | The same pages are built. The list of browsers they are tested in is longer. | B-04 |

- Why it is dropped: Any list builds the same pages. The list changes how much is tested, and it is a list that can be written down without a design decision.
- Still needed: A value. The named list of browsers and versions, before testing starts. Until then: the current and previous version of each browser the test team already has.

## C-17

**Question considered:** If the reminder is timed from each booking, how many minutes before the start is it sent?

- Finding: F-05 (REQ-06, vague, effort small)
- From the finding's question: "How long before a booking's start time"

| Answer | Work it leads to | Pieces |
|---|---|---|
| A. 30 minutes | The reminder is built, with the lead time set to 30 minutes. | B-03 |
| B. 120 minutes | The reminder is built, with the lead time set to 120 minutes. | B-03 |

- Why it is dropped: Any number of minutes builds the same reminder. A booking made later than the lead time needs the same handling whatever the number is.
- Still needed: A value. The lead time, before release, if C-08 is answered A. Until then: 60 minutes.

## C-16

**Question considered:** If the slot has its own marking, is REQ-02 reworded to list three markings?

- Finding: F-09 (REQ-13, vague, effort small)
- From the finding's question: "is that a third marking beside the two in REQ-02?"

| Answer | Work it leads to | Pieces |
|---|---|---|
| A. Yes, REQ-02 lists three | The availability display gets a third marking. | W-20 |
| B. No, REQ-02 is left as it is | The availability display gets a third marking, and the two requirements go on disagreeing on paper. | W-20 |

- Why it is dropped: A marking of its own is a third marking whatever REQ-02 says. Both answers build the same display. C-15 already asks the part that changes the work.
- Still needed: Nothing. If C-15 is answered B, rewording REQ-02 follows from it.

# Considered and set aside: not from a finding

A question has to come from a finding. These came up in the ambiguity review and are not findings, so no
question was written for them.

- **Whether a slot earlier today, already past, can be booked.** Not a finding: the review lists it under "Gaps in the set". It was raised as F-10 and withdrawn.
- **How often each of the 50 members makes a request in the load test.** Not a finding: it was raised as F-11 and withdrawn, because its type could not be reproduced.
- **How long a backup is kept.** Not a finding: the review lists it under "Gaps in the set".
