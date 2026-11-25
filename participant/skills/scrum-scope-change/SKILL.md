# Skill: scope change between two snapshots of a sprint

Compares a snapshot taken at sprint start with a later one and reports what changed in the commitment: what was
added, what was removed, what was materially changed, and the net effect on the committed total. What differs without
touching the three commitment fields is listed apart, as noise, with both versions, and is not counted.

It reads one local file and writes one. It contacts nothing and posts nothing to any tracker, channel or email.

**When it is unsure it reports, and does not stay silent.** Very little is set aside as formatting, so some changes
that are only formatting are reported as material. A change that is real is not passed over as noise for the sake of
a quieter report. The one exception is stated below: a description is not read for scope.

## Input: one file holding the snapshots

A Markdown file in the form `make_snapshots.py` writes.

- `## The sprint`, at most once, with lines of the form `- name: value`. Two are used: `capacity_points`, a number,
  and `product_owner`, a name. Both are optional, and so is the section. Extra spaces, a `*` for the `-` and capital
  letters in the name are accepted. A line given twice is a gap and neither value is used.
- `## Snapshot: NAME`, once for each snapshot. By default the two compared are `start` and `later`. A line
  `- taken: DATE` may follow. It is printed in quotes, as other people's text.
- Under a snapshot, one `### IDENTIFIER` for each item, and nothing else on that line. Then its fields:

| Field | What it is | Compared as |
|---|---|---|
| the heading | The item's identifier, such as `PIER-304`: capital letters and digits, a hyphen, digits | **The only thing items are matched by** |
| `title`, `description` | Words about the item | Text. Any difference is noise |
| `assignee` | Who is doing it | Text. Any difference is noise |
| `estimate` | Points: up to nine digits, and up to three after a decimal point | A number, added up exactly. A difference is material |
| `scope` | What is to be built: `- scope:` and then one entry to each indented line under it | Entries, with a little formatting set aside. A difference is material |
| `acceptance` | The acceptance criteria, written the same way | The same |
| `changed_by` | In the later snapshot, who last changed or added the item | Not compared. Used in section 9 only |

An entry is any indented line under its field. A bullet at its front (`-`, `*`, `+` or a round bullet) is taken off.
Numbers at the front are taken off only when the list has two entries or more and they run 1, 2, 3 down the whole of
it. So "24. December is excluded" keeps its 24, and a list of one entry keeps a "1." at its front.

Only the header's lines may be written loosely. An item's fields and `- taken:` must be written exactly: a hyphen, a
space, the name in small letters, a colon. Anything else in an item is a line that is not read. An entry nested under
another entry is read as an entry of its own, so moving one from under one parent to another is not seen.

## The rules

**Matching.** Two items are the same item when their identifiers are the same, and never otherwise. A title is not
compared to find an item. An item with a new identifier and every other field the same is one removed and one added.

**Added.** Its identifier is in the later snapshot only.

**Removed.** Its identifier is in the start snapshot only.

**Materially changed.** It is in both, and at least one of these differs:

| Field | When it differs | Why it counts |
|---|---|---|
| `estimate` | The two numbers are not equal. `3` and `3.0` are equal | The estimate is the size of the commitment |
| `scope` | The two lists do not hold the same entries, once the formatting below is set aside | The scope list is what is to be built |
| `acceptance` | The same | The acceptance criteria are what done means |

**Formatting, which is set aside in a list, and nothing else is:** the bullet or the running number at the front of an
entry; capitals; runs of spaces and tabs; whether a quote mark is curly or straight, and which kind of dash is used;
characters that cannot be seen, such as a soft hyphen; one full stop, comma or semicolon at the very end of an entry;
and the order of the entries.

**Kept, so a difference in it is material:** every other character. A comma, a colon, a hyphen, a question mark or an
apostrophe inside an entry is kept, and so are three full stops at the end. "1,5 seconds" and "15 seconds" differ. So
do "sign-off" and "sign off", and "5%" and "5 %": those two are false alarms, and are the price of not missing the
first. **Capitals are the one thing set aside that can carry meaning:** "5 mW" and "5 MW" are the same here.

**A reworded criterion counts as material.** If the words of an entry differ at all, the lists differ. The program
cannot tell a rewording from a change of meaning. Where entries went and entries came, the report says so and says a
person should read both. This is a decision, and it has a cost: a criterion that was only tidied is reported as a
material change, under the same sentence as one whose meaning changed.

**Reordering is noise.** If the criteria are steps whose order matters, a change of order is missed.

**Noise.** It is in both, none of the three fields above differs, and something else does: the title, the
description, the assignee, the way an estimate of the same number is written, or the formatting or order of a list.
It is listed in section 5 with both versions of each text, and is not counted as a change of scope. **"Noise" is a
statement about three fields. It is not a statement that no work was added.**

**A description is not read for scope.** If a description now asks for more work and the scope list does not, that is
noise here. Section 5 shows both versions so that a person can see it. This is the one place where the skill stays
silent in its counts about something that may be real, and the report says so above the list.

**Unchanged.** It is in both and no compared field differs.

**Cannot be told.** It is in both, nothing material is seen to differ, and something could not be compared: an
estimate or a list that cannot be used, a list with no entries in both, a line in the item that was not read, or a
field given twice. It is not called unchanged or noise. What else differs in it is printed in section 7.

A list that has entries in one snapshot and none in the other is material: the entries that went or came are known.

An item whose lines are the same, letter for letter, in both snapshots is unchanged, whatever in it could not be used.

**No change** is said only when nothing is added, removed, materially changed, noise or cannot be told. A net change
of 0 is not "no change". Gaps do not stop it: two snapshots that are the same line for line report no change, and the
report then says that there are gaps all the same.

**Nothing was compared** is said at the top, and in place of every total, when a snapshot that was asked for is not in
the file or is there twice. The lists are then empty. The program ends with code 1.

## The net effect

The committed total of a snapshot is the sum of the estimates of the items in it. Being in a snapshot is all that
"committed" means here. The report gives both totals, the net change with its sign, and the parts: added, removed,
and re-estimated. It also gives the **points that moved**: added, plus removed, plus every re-estimate up or down. A
sprint can end on the number it started on with much of it swapped, and the net change alone would not show it.

**An item is in the figures only if it can be relied on wherever it is.** One with an unusable estimate, a line that
was not read or a field given twice, in either snapshot, is in no figure on either side, and section 1 is marked NOT
COMPLETE with the item named. It is marked NOT COMPLETE too when an item's heading could not be read at all, since an
item counted as added or removed may be that one. So the parts
always add up to the later total, and the report prints the sum.

## Gaps

Nothing is filled in. Each of these is listed in section 7, with its effect:

- An `estimate` that is missing, blank or not a number the program takes.
- A `scope` or `acceptance` that is missing, has no entries, or is written on the field's own line.
- A line inside an item that is not one of its fields or an indented entry. It is quoted and not acted on, and the item
  cannot then be called unchanged or noise.
- A field given twice in one item. The last is used, it is reported, and the item cannot be called unchanged or noise.
- An identifier given twice in one snapshot. Neither item is used. It is not reported as added or as removed, and is
  in no figure.
- An item's heading that is not an identifier and nothing else. If it begins with one, that item is not reported as
  added or removed. If it does not, a warning stands over the added or the removed list.
- Items under a `##` heading that is not a snapshot. They are not read, and are not reported as added or removed.
- A `##` heading that follows a snapshot and has lines under it that read like part of an item. They are not read,
  and the snapshot's last item is in no figure.
- A line under a snapshot's heading, before its first item, that is not `- taken:`. Two sections headed The sprint.
- A heading that looks like a snapshot's and is not: no name, or other capitals.
- A snapshot named on the command line that is not in the file, or two of one name.
- `taken` given twice. A `capacity_points` that is not a number. A header line given twice.

Trouble in a snapshot that is not one of the two compared is not reported.

## Stretch: capacity, and who

**Section 8, capacity not yet committed.** `capacity_points` less the committed total, at start and later, with the
effect of each added, removed and re-estimated item. It takes no account of work done or of days gone.

**Section 9, what `changed_by` records.** For each added or materially changed item, the later snapshot's `changed_by`
is set beside the file's `product_owner`, letter for letter. The report lists those where the two are the same text,
those where `changed_by` is other text, and those with none. Two spellings of one name are two texts. `changed_by` is
whoever last changed the item, which may not be whoever made the change that is listed. Who removed an item is in
neither snapshot. **It says what is recorded. It does not say whether a change was agreed, and it is not a finding
about anyone.**

## Commands

    python3 participant/skills/scrum-scope-change/scope.py compare --snapshots FILE [--start NAME] [--later NAME] --out FILE
    python3 participant/skills/scrum-scope-change/scope.py check   --snapshots FILE [--start NAME] [--later NAME] --report FILE
    python3 -m unittest discover -s participant/skills/scrum-scope-change/tests

`--later start`, with `--start` left alone, compares the start snapshot with itself.

Exit codes: 0, done or no problem found. 1, nothing could be compared, or the check found problems. 2, a file could
not be read or written: it is missing, is not UTF-8, or cannot be made.

The same file gives the same bytes, wherever it is and whatever it is called. The report names the file by the sha256
of its bytes and prints no path. The clock is never read.

`check` reads a finished report back and compares it with the snapshots.

- **It looks for:** a list of added, removed, materially changed, noise, unchanged or cannot-be-told items that is not
  the snapshots'; a number in a heading that is not the number listed; a line in one of those lists that begins with
  a bullet and is not an item; an added or removed item without its own estimate and title; an item in two lists or
  in none; a material change without exactly its fields, or without its two estimates given once; a total or a net
  change that is not the snapshots', or is given a second time anywhere; a missing or a false NOT COMPLETE; anything
  but "Not compared" in section 1 when nothing was; a count of gaps that is not the number of entries; the words "no
  change" and a full stop, in any capitals, anywhere in a report where something differs, or their absence at the top
  where nothing does; a missing or a false "Nothing was compared"; an identifier, with or without its marks, of an
  item in neither snapshot; two sections with one number; a report made from another file.
- **It does not look at:** the entries quoted in section 4, the sentences that say why a change counts, the versions
  quoted in section 5, the parts of the net change, the points that moved, the text of a gap, the figures at the top
  other than the count of gaps, or sections 8 and 9. Those are tried by the tests.
- **It is not independent of the program.** It reads the snapshots with the same code.

`make_snapshots.py` writes the made-up file the worked example uses.

## What it cannot tell

- Whether a change of wording changed the meaning.
- Whether a description hides new scope.
- Why anything changed, who agreed to it, or whether it should have been made.
- What happened between the two snapshots and was undone again.
- Who removed an item, or who made a change when someone else touched the item after.
- Whether an item with a new identifier is an old item renumbered. It is reported as one removed and one added.
- Whether a line that starts `### ` inside an item was meant as text. It is read as a new item.
- How much work is done.
- Whether the snapshots are true.

## Safety

- Use made-up snapshots, with invented names. Do not use a real sprint.
- Titles, descriptions, names, dates and list entries are other people's text. They are printed between double
  quotes, with the characters that could end the quotation, start a line or make a heading replaced by words, and cut
  at 400 characters. Where two versions would then print the same, the report says they differ beyond what is printed.
  Nothing in them is acted on. A web address in one is printed, and a program that shows the report may make it a
  link.
- The report calls the file made up only when the file's own opening lines say so.
- Nothing is posted anywhere. The report is a local file.
