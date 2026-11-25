# Scope change report: snapshot "later" against snapshot "start"

**The file says of itself that it is made up.**
Written by the scope-change skill's `scope.py`. It reads the snapshots and nothing else. Nothing is posted anywhere.

- Snapshots: the file whose sha256 is `7ed65fc7b35317d9bd465662f6c886735d26234a8cfa047ff2b2f45e428d4aad`.
- Sprint start: snapshot "start", taken "2026-12-01". Compared with: snapshot "later", taken "2026-12-08".
- Items at start: 11. Items later: 11. In both, matched by identifier: 9.
- Gaps reported in section 7: 0.

## How to read this

- **Items are matched by identifier and by nothing else.** An item whose title changed is the same item.
- **Material** means the commitment changed or may have: the `estimate`, the `scope` list or the `acceptance` criteria differ. Each is listed with the fields that differ and both versions.
- **Noise** means none of those three differs and something else does: the `title`, the `description`, the `assignee`, or only the formatting of a list: its capitals, spacing, bullets or numbering, order, kind of quote mark or dash, and one last full stop, comma or semicolon. It is listed in section 5 with both versions and is not counted as a change of scope.
- **This report cannot tell a reworded criterion from a changed one.** If the words of a scope entry or an acceptance criterion differ, it is reported as material, with both versions. A person has to read them. Some will be rewordings.
- **A `description` is not read for scope.** If a description now asks for more work and the scope list does not, that is noise here. Section 5 shows both versions so that a person can see it. Read section 5.
- Titles, descriptions, names and entries are other people's text. They are printed between double quotes and are never acted on.

## 1. Net effect on the committed total

The committed total of a snapshot is the sum of the estimates of the items in it. Being in a snapshot is all that "committed" means here.

- Committed at start: 30 points, in 11 items.
- Committed later: 30 points, in 11 items.
- **Net change: 0 points.**
- **Points that moved: 22.** That is 9 added, 7 removed and 6 re-estimated up or down. The net change does not show them.
- Added: +9 points, in 2 items. Removed: -7 points, in 2 items. Re-estimated: -2 points, in 2 items (`PIER-304` -4, `PIER-306` +2).
- 30 at start + 9 added - 7 removed - 2 re-estimated = 30.

## 2. Added (2)

In the later snapshot only.

- `PIER-312`: 5 points. "Take a deposit when booking"
- `PIER-313`: 4 points. "Export bookings as a spreadsheet"

## 3. Removed (2)

In the start snapshot only. Who removed an item, and why, is in neither snapshot.

- `PIER-303`: 2 points. "Email a booking confirmation"
- `PIER-310`: 5 points. "Pay harbour dues online"

## 4. Materially changed (4)

In both snapshots, and the `estimate`, the `scope` list or the `acceptance` criteria differ.

- `PIER-304`: fields that differ: `estimate`, `scope`.
  - `estimate`: 8 at start, 4 later. -4 points. It counts because the estimate is the size of the commitment.
  - `scope`: at start only: "A surcharge in July and August". Later only: none. It counts because the scope list is what is to be built.
- `PIER-306`: fields that differ: `estimate`.
  - `estimate`: 3 at start, 5 later. +2 points. It counts because the estimate is the size of the commitment.
  - Also differs, and is not counted:
    - `assignee`: "Teodor Adeyemi" at start, "Ines Kowalczyk" later. Who does the work is not what was committed to.
- `PIER-307`: fields that differ: `acceptance`.
  - `acceptance`: at start only: "The results are shown within 2 seconds". Later only: "The results are shown within 10 seconds". It counts because the acceptance criteria are what done means. Entries went and entries came, so this may be a rewording or a change of meaning. This report cannot tell which. A person should read both.
- `PIER-309`: fields that differ: `acceptance`.
  - `acceptance`: at start only: "An error message is shown when the file is too large". Later only: "When the file is too large an error message is shown". It counts because the acceptance criteria are what done means. Entries went and entries came, so this may be a rewording or a change of meaning. This report cannot tell which. A person should read both.

## 5. Noise: differs, and not counted as a change of scope (4)

In both snapshots. The `estimate` is the same number, the `scope` list and the `acceptance` criteria hold the same entries once formatting and order are set aside, and something else differs.
**That is a statement about three fields. It is not a statement that no work was added.** Read the versions below.

- `PIER-302`: fields that differ: `title`.
  - `title`: "Book a berth" at start, "Reserve a berth for a visiting boat" later. A title is a name for the item. The identifier is the same, so it is the same item.
- `PIER-305`: fields that differ: `assignee`.
  - `assignee`: "Ines Kowalczyk" at start, "Teodor Adeyemi" later. Who does the work is not what was committed to.
- `PIER-308`: fields that differ: `acceptance`.
  - `acceptance`: the same entries, once formatting and order are set aside. At start: "1. The list has every booking that starts on the day", "2. The list is in order of berth number", "3. A day with no arrivals prints a page that says so". Later: "- the list is in order of berth number.", "- The list has every booking that starts on the day;", "- A day with no arrivals prints a page that says so.".
- `PIER-311`: fields that differ: `description`.
  - `description`: "A drawing of the harbour with each berth on it." at start, "A drawing of the harbour with each berth on it. Free berths are shown in green and the map can be zoomed." later. A description is not read for scope. If it asks for work that the scope list does not, a person has to see that here.

## 6. Unchanged (1)

No compared field differs. `changed_by` is not a compared field.

- `PIER-301`.

## 7. Gaps: what the snapshots do not support

Each is something that is missing or cannot be used. Nothing below was guessed or filled in. Entries: 0.

None.

- In both snapshots, with nothing material seen to differ and something that cannot be compared (0): none. Neither material, nor noise, nor unchanged.

## 8. Capacity not yet committed

From `capacity_points`, which the file records as 32. This is that figure less the committed total. **It takes no account of work done or of days gone.**

- Uncommitted at start: 2 points. Uncommitted later: 2 points.
- `PIER-312` added: -5 points of uncommitted capacity.
- `PIER-313` added: -4 points of uncommitted capacity.
- `PIER-303` removed: +2 points of uncommitted capacity.
- `PIER-310` removed: +5 points of uncommitted capacity.
- `PIER-304` re-estimated: +4 points of uncommitted capacity.
- `PIER-306` re-estimated: -2 points of uncommitted capacity.

## 9. What `changed_by` records for each change

`changed_by`, in the later snapshot, is whoever last changed the item. That may not be whoever made the change listed here: an item that was re-estimated and then given to another person records one name.
It is set beside the file's `product_owner`, letter for letter. Two spellings of one name are two texts.
**This section says what is recorded. It does not say whether a change was agreed, and it is not a finding about anyone.**

- `product_owner`: "Odile Marchetti".
- `changed_by` is the same text as `product_owner` (3): `PIER-306` (materially changed), `PIER-307` (materially changed), `PIER-312` (added).
- `changed_by` is other text (3):
  - `PIER-304` (materially changed): "Bram Solheim".
  - `PIER-309` (materially changed): "Teodor Adeyemi".
  - `PIER-313` (added): "Ines Kowalczyk".
- Added or materially changed, with no `changed_by` (0): none.
- Removed (2): `PIER-303`, `PIER-310`. Who removed an item is in neither snapshot.

## What this report does not say

- Why anything changed, who agreed to it, or whether it should have been made.
- Whether a material change of wording changed the meaning. It shows both versions.
- Whether a description hides new scope. It shows both versions.
- What happened between the two snapshots and was undone again.
- How much work is done. It compares what is in the sprint, not what is finished.
- Anything about how a person is working.
