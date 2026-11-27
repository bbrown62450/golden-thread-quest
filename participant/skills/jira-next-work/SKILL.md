# jira-next-work

Recommends which Jira item to work on next, from **local copies** of a project's items. Every reason names the
recorded field it came from. Blocked items are listed apart with the blocker named. Stale copies are warned about
and never offered as the thing to start.

**It gives advice. It changes nothing in Jira.** The copy step only reads. The ranking step contacts nothing.

The rules, in full, are written by the skill itself: `participant/context/jira/next-work/rules.md`.

## Two steps

| Step | Command | Reads Jira | Writes to Jira | Writes locally |
|---|---|---|---|---|
| 1. Copy | `sync.py copy` | yes | **never: it has no code that can** | one records file |
| 2. Rank | `rank.py rank` | **no** | **never** | one recommendation file |

    sync.py copy --source live --project KEY --out RECORDS.json
    sync.py copy --source live --project KEY --out RECORDS.json --refresh KEY-1 KEY-2      copy only these again
    rank.py rank --records RECORDS.json --now 2026-12-01T09:00:00Z --out RECOMMENDATION.md
    rank.py rank ... --rule due-first            or   --also-rule due-first   to show both orders
    rank.py diff --before A.json --now-before TIME --after B.json --now-after TIME        what moved, and which field changed
    rank.py rules --out RULES.md

- **A real copy is the person's to run,** in their own terminal, with `JIRA_BASE_URL`, `JIRA_EMAIL` and
  `JIRA_API_TOKEN` set there. `--source fake` copies from the fake Jira.
- **`--now` is required.** The ranking never reads the computer's clock, so the same records and the same clock
  value always give the same recommendation, byte for byte.

## What is copied, and what is not

- **Copied:** key, id, type, status and its category, priority, due date, created, updated, links, and `copied_at`.
  Also the site's priorities, in Jira's order, and its link types.
- **Who has an item** is kept as one of three words: `me`, `someone else`, `nobody`. Never an account or a name.
- **Not copied:** titles, descriptions, comments, people. Jira's answers carry the titles of linked items and the
  person who has each item; both are dropped as they are read.
- **Times are rewritten in UTC,** so the site's own time zone is not kept.
- **Names the site's administrators chose** (statuses, priorities, types) are cut to 40 characters and stripped of
  anything that could break a Markdown table.
- **A short fingerprint of the site's address is kept.** Someone who guesses the address can confirm it from that.

So a recommendation names items by key. To see what an item is about, open it in Jira.

## Reading a recommendation

| Part | What it is |
|---|---|
| **Start here** | The first ranked item whose copy is not stale. Items standing above it on stale copies are named: copy those again first. Blocked items that would outrank it are named with their blockers |
| **Already started by you** | Items that are yours and in progress. Listed so they are seen. They keep their place: finishing before starting is your call |
| **Ranked** | Open, not blocked, unassigned or mine. Each with its reasons, its confidence and any warning |
| **Blocked** | Not ranked. Each with its blocker named, the blocker's status, and which record showed the link and the status |
| **Not offered** | Done, or someone else has it |
| **Missing fields** | What was not recorded, per item |

**Argue with it.** Each reason names a field. If the field is wrong in Jira, the reason is wrong.

**Confidence is about the data, not the advice.** "High" means the fields were all recorded and the copy is fresh.
It does not mean the item is the right one to do.

## Blocked: both ends of a link are read

A link sits in two records, copied at two times, so they can disagree. An item is blocked if **either** record says
so. If the two copies of a blocker's status disagree about whether it is done, the item is treated as **still
blocked**, and the recommendation says to copy both again.

If the site has no link type named "Blocks", nothing can be shown as blocked, and the recommendation says so at the
top in capitals. It does not say "Blocked: none".

## When not to trust it

- **An item marked STALE.** Its place comes from old fields. Copy it again before acting on it.
- **Low confidence.** Fields were missing, so its place says little.
- **"Copies disagree" or "may have been removed".** Copy both items again.
- **Any copy at all, a little.** A copy is what Jira said when it was read, and Jira's search can itself be behind.

## Refreshing

`--refresh` copies the named items again, one request each. It then says which **other** items have changed in
Jira since their copy and were not copied again. Refresh those too, or copy the whole project.

## What it does not know

- Whether a recorded priority is right, how large an item is, or who is asking and what they can do.
- What an item is about.
- A blocker the copying identity could not see.
- Whether two "blocks" links make a circle. It reads links; it does not judge them. Two items that block each
  other are both listed as blocked.
- Whether to finish started work before starting new work.
- A site with two lists of priorities, or a "blocks" link type under another name.

## Tests

    cd participant/skills/jira-next-work && python3 -m unittest tests.test_next_work
