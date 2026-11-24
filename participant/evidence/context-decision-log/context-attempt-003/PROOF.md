# PROOF: Distinguish Approved Decisions, Proposals, and Questions

Quest `context-decision-log`, attempt `context-attempt-003`.

## How this was made

The log, its rules, the skill that checks it, its tests, the recording scripts and this document were written
by an AI assistant (Claude) at the participant's direction. The participant made two decisions: an approval
needs four things written down, and agreement in conversation is not one of them; and the log only ever
grows, with the list of current decisions worked out from it by a script.

**Everything in the log is made up.** The project, its documents, its work items and its roles do not exist.
No real person approved, proposed or asked anything in it, and no entry records a decision on anyone's behalf.
Nothing outside the participant's computer was contacted.

Words used below: **recorded** means the saved log of the check shows it. **tested** means an automated test
checks it. **not assessed** means nobody checked it.

## Approach

`participant/context/decisions/log.md` holds 14 entries about a made-up "weekly export" project. Each is a
decision, a proposal or a question. An entry is never edited. A change of state is a new entry that points
back at the old one: `promotes`, `rejects`, `supersedes` or `answers`.

What became of an entry is never written into it. It is worked out from the entries that point at it, and
shown at the top of the log in a part a script writes: what is decided now, what is not, and what became of
every entry. The check fails if that part is not exactly what the entries say.

`rules.md` is written out from the tables in the checking code, so the rules and the check cannot disagree.

## How I tell an approval from agreement in conversation

This is what the quest asks the proof to explain.

**An approval is an act by one answerable person. Agreement is a mood in a room.** The log counts an entry as
a decision only if it records four things (criterion 2):

1. **An approver who may approve it.** A role, and the right one for the kind of decision. In this project
   the product owner approves what is built and when, the tech lead how it is built, and the security lead
   what data is kept and who sees it.
2. **The approver's own words, quoted, and they must be words of approval**: "approved", "go ahead with", "I
   sign this off", or "declined".
3. **The place** those words are, with a reference a reader can look up.
4. **The date.**

If one is missing, the entry is a proposal, however much people liked it (criterion 3). These are the cases
the rules name as **not** approval, and each is in the log or in the recorded check:

| What happened | Why it is not an approval | Where |
|---|---|---|
| "Sounds good", "makes sense", "+1" | The speaker likes the idea. They have not said yes to it as the person answerable | E-012: two engineers wrote "+1". `logs/log-check.txt` part 4 |
| Nobody objected | Silence is not an act. And the approver may not have been there | E-003: no objections at a meeting the product owner did not attend. It became a decision only with E-004 |
| The wrong role agreed | A tech lead who likes a retention period has not approved it. Retention is a security decision | E-005: the tech lead said "sounds good" |
| Someone reports the approval | "The security lead said it was fine" is somebody else's words | `logs/log-check.txt` part 4 |
| Another document calls it "the decision" | A ticket cannot approve anything | E-005: ticket WX-31 says "per the decision in DOC-4" |

Agreement is still worth keeping, so a proposal records it in `support`: who agreed, how, and where. That
keeps the fact without promoting it.

**The scenario is entry E-005.** A design document proposed keeping export files for 90 days. A ticket quoted
it as the decision, and three stories were built on it. In this log it is still a proposal. The top of the
log lists it under "Proposals that something else treats as decided", with the three stories, and the check
prints a warning. The log does not make it a decision because work has started, which is exactly how the
scenario went wrong.

**What this costs.** Things everybody treats as settled sit in the log as proposals until the right person
says so in writing. A team could find that slow. And the rule can be gamed: the check accepts any quoted
sentence with "approved" in it, and cannot open the document to see whether the approver wrote it.

## The criteria, one by one

| # | Criterion | Status | Where |
|---|---|---|---|
| 1 | Every entry has exactly one status | recorded, tested | `log.md`: the status is in each heading and each `status` field, and each statement opens with it. `logs/log-check.txt` part 1. Part 4: two statuses, and a heading and field that disagree, are reported. Tests `OneStatus` |
| 2 | A decision records its approver and where it was approved | recorded, tested | `logs/log-check.txt` part 1 lists all 7 decisions with approver, place and quoted words. Part 4: a decision missing either is reported. Tests `Approval` |
| 3 | A proposal is never shown as a decision | recorded, tested, with a stated limit | Part 1: no proposal has approval fields, and none is in the list of current decisions. Part 4: a proposal given an approver, worded "we will", opened with "Decision.", or written into the current list by hand, is reported. **Limit:** wording is checked against a short list of words. See limitations |
| 4 | Promoting a proposal adds an entry and keeps the history | recorded, tested | Part 2: E-003 and E-004 in the handed-in log. Part 3: E-012 is approved on a copy; 15 entries where there were 14, and the earlier 14 byte for byte the same. Part 4: editing a proposal into a decision in place is reported |
| 5 | A superseded decision links to the one that replaced it | recorded, tested | `log.md`: E-014 `supersedes: E-004`, E-009 `supersedes: E-007`, and the index shows each older one as "SUPERSEDED by" the newer. Part 1. Tests `Superseded` |
| 6 | Each entry cites its source | recorded, tested | Part 1: all 14 entries have a source with a reference. Part 4: an entry with none is reported. Tests `Sources` |
| 7 | A reader can find the current decisions without reading the history | recorded, tested | `log.md`, "What is decided now", at the top: 5 decisions. Part 1: it is before the first entry, holds exactly the decisions not superseded, and is what the script writes |

## Artifacts

| Required item | File |
|---|---|
| The log | `participant/context/decisions/log.md`: 14 entries, 7 decisions, 4 proposals, 3 questions |
| The rules | `participant/context/decisions/rules.md` |
| The check | `logs/log-check.txt`, 48 checks |
| This narrative | `PROOF.md` |

Also here: `logs/tests.txt` (50 tests), `logs/planted-bugs.txt` (26 planted bugs), `scripts/record_evidence.py`
and `scripts/planted_bugs.py`. The skill is `participant/skills/context-decision-log/`: `SKILL.md`,
`decisions.py`, `tests/test_decisions.py`. `participant/context/decisions/ledger.json` holds the checksum of
each entry.

In the log, 2 decisions are superseded (E-004 by E-014, E-007 by E-009), 1 proposal was approved (E-003 by
E-004), 1 was declined (E-008 by E-010), and 1 question was answered (E-001 by E-002).

## Stretch goals

- **Link decisions to the work items they affect:** done. Each entry has `affects`, and the list of current
  decisions shows it.
- **Report decisions with no downstream work:** done. The top of the log lists current decisions that name no
  work item: E-010 and E-013. E-010 declines something, so nothing follows from it. E-013 is a real gap.

## Reproduce

    python3 participant/skills/context-decision-log/decisions.py check
    python3 -m unittest discover -s participant/skills/context-decision-log/tests -v
    python3 participant/evidence/context-decision-log/context-attempt-003/scripts/record_evidence.py
    python3 participant/evidence/context-decision-log/context-attempt-003/scripts/planted_bugs.py

None of these contacts anything. The third leaves the handed-in log untouched and works on a copy in a scratch
folder. The fourth changes `decisions.py` while it runs and restores it.

## What was tested

| What | Result |
|---|---|
| The handed-in log | Keeps every rule. Exit code 0 |
| Recorded checks | 48, all pass. They include 20 ways of breaking the log, each reported, and one the check cannot see |
| Automated tests | 50, all pass (`logs/tests.txt`) |
| Planted bugs | 26 put into `decisions.py` one at a time. Every one made at least one test fail (`logs/planted-bugs.txt`) |

Faults found while building:

- **The check caught the assistant's own first draft of the log, twice.** A proposal's text said "nobody has
  approved it", which uses the word "approved" outside a quotation, and a decision had an empty `affects` line.
  Both were corrected before the log was sealed for hand-in. The first shows the wording rule's bluntness: it
  flagged a sentence saying something was *not* approved.
- **One planted bug did nothing.** It was meant to list a proposal as a current decision and changed nothing
  the tests could see. It was replaced by one that really does, which a test catches.

## What could not be done, and limitations

- **The check cannot open what an entry cites.** It checks that approval words are given, quoted and are words
  of approval. Whether the approver wrote them, at the place named, is **not assessed** and cannot be by this
  skill. In this log the cited documents do not exist at all.
- **"Never shown as a decision" is checked by a list of words.** A proposal may not say decided, approved,
  final, "we will", agreed, settled or confirmed outside a quotation. A proposal that says "the plan is to" or
  "going forward, exports are kept 90 days" passes. And the rule overreaches the other way: it flags "not
  approved".
- **Only this log is checked.** The scenario's fault was in a ticket, not in a log. The log can record that
  WX-31 misquotes a proposal, when someone notices and writes it down. It cannot find such a ticket.
- **A missing `supersedes` link is invisible.** Recorded in part 4: without it, the Friday and the Monday
  decision would both show as current. The check cannot know a link is missing.
- **The ledger can be edited along with the entry.** The check then sees nothing. The repository's history is
  what would show it.
- **One role approves each kind of decision.** A decision needing two approvers, or one approved by a
  deputy, cannot be expressed. The roles are fixed in the code.
- **Roles, not people.** The log says "product owner". It does not say who held that role on the day. A real
  log would need that, and would then hold personal names.
- **Nobody used the log.** No reader was asked to find the current decisions, so criterion 7 is shown by where
  the list is and what it holds, not by a person finding it.
- The log, the rules, the check and the tests were written by the same assistant and can share a blind spot.

## Reflection

*Which decision in your log would you least want to be asked about?*

E-013: "An export file holds no email addresses."

On paper it is the best decision in the log. The right person approved it, in clear words, in a place I can
point to. It passes every rule I wrote. And it names no work item. Nobody has been asked to make it true, and
nobody has been asked to check that it is. If someone asked me "so, do the exports hold email addresses?", the
honest answer is that it was decided they would not, and I have no idea whether they do.

That is the one I would least want to be asked about, because the log makes it look finished. The two
decisions I superseded are easy to talk about: we chose Friday, customers wanted Monday, we changed it, and the
trail is there. Even the 90-day proposal, which is the real mess in this log, is easy to explain, because the
log says plainly that it is not decided and shows who built on it anyway.

What I did not expect is that my rules cannot see the difference. I spent this quest on the line between a
proposal and a decision, and E-013 is on the right side of it. The gap is on the other side, between a
decision and anything actually happening. The log only caught it because of the extra report of decisions with
no work item, which I nearly left out as optional.

So what I learned is that "approved" was never the end of the question. A decision that is properly approved
and never acted on is, to the people downstream, hard to tell from one that was never made.

## Sensitive values

- No token or credential was used. The quest reads and writes only local files.
- The log holds no real person, customer, project or work item. People are roles only. Every identifier is
  invented.
- No entry records a decision on behalf of a real person.
