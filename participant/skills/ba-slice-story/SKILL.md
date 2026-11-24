# Skill: slice an oversized story

Cuts one story that is too large into slices that each give a user something, and checks the cut. It reads and
writes local files only. It creates nothing in any tracker.

## When to use it

A story has more acceptance criteria than fit in one iteration, and none of it would reach a user until all of it
does.

## What it needs

An original story whose criteria each state one result, numbered `OC-01` onward, each with a "Needs" line naming
the other criteria that must already hold. The story is held as tables in a Python module beside the skill:
`reporting_module.py` is the one worked example, and it is made up.

## Steps

1. Write the original's criteria as one result each. A criterion with two results cannot go to one slice.
2. For each criterion, write what it needs. This is a judgement, and the order check is only as good as it is.
3. Find the first slice: the smallest set of whole criteria that a user could be given and would use, needing
   nothing outside itself. Put in it anything that would make the release unsafe or untrue to leave for later.
4. Cut the rest by what a user is given, not by what is built. A slice that could be named for a layer is a layer.
5. Give every criterion to exactly one slice, word for word. Add nothing. Where the cutting shows that the
   original does not say something, list it as a gap and do not fill it in.
6. For each slice state: its value alone, what a user would notice, what it depends on and relies on, what it
   lacks if released before the later ones, and why it is where it is in the order.
7. Two candidate slices that cannot ship without each other are one slice. Say so.
8. Run `build`, then `check`. Then have somebody who did not write it read the slices: see "What it cannot tell".

## Commands

    python3 participant/skills/ba-slice-story/slice.py build      writes the three documents from the tables
    python3 participant/skills/ba-slice-story/slice.py check      checks the finished documents
    python3 participant/skills/ba-slice-story/slice.py coverage   prints the slice that covers each criterion
    python3 -m unittest discover -s participant/skills/ba-slice-story/tests

It writes `participant/context/slicing/original-story.md`, `slices.md` and `rejected-slicing.md`. `check` reads the
finished files and not the tables, so a file edited by hand is checked as it stands.

## What the check reports

- an original criterion in no slice, or in more than one;
- a criterion in a slice that is worded differently from the original, or is not from it at all;
- a slice that says it depends on a later slice, or on itself;
- a criterion that needs one in a later slice, by the original's "Needs" lines;
- a needed earlier slice that the slice does not name, directly or through another;
- a first slice that depends on anything, or whose criteria need something outside it;
- a slice that does not state its value, what a user would notice, what it relies on, what it lacks if released
  early, or why it is where it is;
- a slice whose title or value uses a word for a technical layer;
- slices cut from a different version of the original; counts or a coverage table that are not the real ones.

## What it cannot tell

- **Whether a slice is a slice.** A slicing by the original's own area headings passes every count the check
  makes, and its first release is a page with nothing on it. Coverage and order are necessary and are not enough.
- Whether a stated value is real, or a quality attribute under a friendly name.
- Whether a "Needs" line is right, or one is missing.
- Whether a commentary line promises something no criterion contains.
- Whether a slice could in fact be released. That needs a team and a product.

These need a reader. In the worked example a reader's findings changed the slicing from nine slices to seven.

## Safety

- Use a made-up story. Do not paste a real one, or real customer data, into the tables.
- Do not say a slice can be released without saying what it relies on. The check requires the line. It cannot
  judge whether the line is complete.
