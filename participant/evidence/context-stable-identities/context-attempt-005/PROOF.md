# PROOF: Map Source Identifiers Without Relying on Filenames or Titles

Quest `context-stable-identities`, attempt `context-attempt-005`.

## How this was made

The rules, the made-up source records, the skill, its tests, the recording scripts and this document were
written by an AI assistant (Claude) at the participant's direction. The participant made two decisions: a
record whose identity is already held is told apart by a second thing the source promises never to change, its
creation time, and never by its title; and an identity is the source's own identifier, character for character,
with unclean identifiers refused and not repaired.

**Every item is made up**: 20 source records across three invented systems, with invented projects, boards and
repositories. No real item, and no real customer's identifier, is in any file. Nothing outside the participant's
computer was contacted.

Words used below: **recorded** means the saved log shows it. **tested** means an automated test checks it.
**not assessed** means nobody checked it.

## Approach

An identity is `SYSTEM:IDENTIFIER`. `SYSTEM` is `jira`, `trello` or `github`. `IDENTIFIER` is one field of the
source record, used character for character. Nothing else is in it.

Beside each identity the map keeps a **birth mark**: the moment the source says the item was created. It is not
part of the identity. It is what answers the quest's hard question, which is not "what is the identity" but
"a record has arrived whose identity is already held: is it the same item?"

| What arrives | What it is | What happens |
|---|---|---|
| the same birth mark | the same item, renamed or moved | updated in place |
| a different birth mark | the source reused the identifier | reported, nothing overwritten, the newcomer held aside |
| two different records in one batch | a collision | reported, neither written |

Five made-up batches are applied in order: a first sync, a rename and a move, a collision, a reused
identifier, and a changed identifier with six unusable ones. `participant/context/identity/map.md` is the map
after all five.

## The source field I trusted most, and the ones I refused

This is what the quest asks the proof to explain.

**Trusted most: Jira's issue `id`** (criterion 1). Of the three, it is the one whose promise I could state most
plainly: Jira gives the number when the issue is created and keeps it through every edit and every move between
projects. It is also the one the scenario is about. The scenario's story was renamed and moved to another
project, and in the run that story is `jira:40003` before and after.

For the other two systems I trusted the matching field: Trello's card `id` and GitHub's `node_id`. In each
case I chose **one** field per system and refused every other, including a second field that is also stable.
GitHub has a numeric `id` as well as a `node_id`. Using either would work. Allowing both would let one item get
two identities, so one was chosen and the other refused (criterion 7).

**Refused, and why** (criterion 2):

| Field | Why it looks like an identity | Why it is refused |
|---|---|---|
| Jira's `key`, such as DEMO-3 | It is what everyone says and types | It holds the project's key, so it changes on a move. In the run it became OPS-17 |
| The title | It is what people recognise | Anyone can edit it, and four of my 20 items share one title |
| GitHub's `number` | It is in every link | Every repository has its own issue 2, and it changes on a transfer. In the run it became 41 |
| Trello's short link | It is stable in practice | Trello does not promise it as the card's identity |
| The project, board, list or repository | It says where the item is | Where an item is, is exactly what a move changes |
| The position in a list, or in the file | It is how a program numbers things without thinking | It changes when anyone drags a card, or when the source sends the records in another order |

**The field I refused that tempted me most was the title, the second time.** Refusing it as the identity is
easy. The temptation comes back at the next step: when a record arrives with an identity already held, the
natural way to ask "is this the same item?" is to look at whether the title is similar. That uses the title to
decide identity after all, against criterion 2. So the rule is that titles are never compared. The log shows it
both ways: the same title with a different birth mark is reported as reuse, and a wholly different title,
project and key with the same birth mark is the same item.

**What a refused field would have done** is measured in `logs/identity-run.txt` part 2, on the same two batches:

| Identity built from | Items of 20 with a different identity after the rename and move |
|---|---|
| the title | 4, and one pair of different items share an identity from the start |
| the key, short link or number | 2 |
| where it lives and its title | 4 |
| its position in the batch | 20 |
| the system and its own identifier | 0 |

Under a title-based key the scenario happens exactly. The story's old title is taken over by another story, so
the old key now names a different item, and a note kept under it would follow the title to the wrong story.

## The criteria, one by one

| # | Criterion | Status | Where |
|---|---|---|---|
| 1 | An identity is built from the source system and its own immutable identifier | recorded, tested | `participant/context/identity/rules.md` sections 1 and 2. `logs/identity-run.txt` part 1. Tests `Deriving` |
| 2 | No identity depends on a title, filename, project name or position | recorded, tested | `rules.md` section 3. Part 1: four items called "Fix export" get four identities. Part 2: the table above. Part 4: titles decide nothing. Planted bugs A, B, C, N, P, T |
| 3 | Renaming an item leaves its identity unchanged | recorded, tested | Part 2: three items renamed, 20 identities before and after, none new |
| 4 | Moving an item between projects leaves its identity unchanged | recorded, tested | Part 2: a story moved project, a card moved board, an issue transferred. Each updated in place |
| 5 | Two records producing the same identity are reported as a collision and neither is overwritten | recorded, tested | Part 3: reported, neither written, and a collision on an identity already held leaves the held item exactly as it was. Planted bugs I, J, K |
| 6 | The rules say what to do when a source reuses an identifier | recorded, tested, with a stated limit | `rules.md` section 5. Part 4: Jira id 40007 arrives with another creation time. Reported, the held item untouched, the newcomer held aside. **Limit:** not detectable for Trello. See below |
| 7 | Another person can derive the same identity from the rules | recorded for two AI readers. **Not assessed for a person** | `logs/derive-by-hand.txt`. Part 1: a second derivation, sharing no code with the skill, gives the same 20 identities |

### Criterion 7: how far it was tested

Two fresh AI assistants were each given `rules.md` and a list of raw records, told to run no program and to
work each identity out by reading. Their answers were compared with the skill's.

- **Round 1**, the rules as first written: 15 of 16 matched. The 16th was a record from a system the rules did
  not name. The reader said the rules did not settle it. It also found twelve gaps, eight of which could have
  led a careful person to a different identity. The rules were rewritten for all twelve.
- **Round 2**, the revised rules, with six new records chosen to be hard: 22 of 22 matched, and nothing was
  unsettled.

So the first version of the rules did **not** fully meet criterion 7, and it took a reader who had only the
rules to show it. Five more sentences were added after round 2, and nobody has yet tried to follow those. A
person, as opposed to an AI assistant, has not tried either.

### Criterion 6: what "reused" can and cannot catch

The rule depends on a second promise from the source: that it states when an item was created, and does not
change that either. Three cases get past it, and the rules and the run say so:

- **Trello.** A card's creation time is read from its id. A reused id carries the same time. Reuse of a Trello
  card id cannot be detected at all by these rules.
- **No creation time.** If either record lacks one, the run says reuse could not be checked.
- **A source that reuses an identifier and repeats the creation time**, as a restore from a backup might.

## Artifacts

| Required item | File |
|---|---|
| The identity rules | `participant/context/identity/rules.md` |
| The identity map | `participant/context/identity/map.md`: 21 items across three systems |
| The identity run | `logs/identity-run.txt`, 34 checks |
| This narrative | `PROOF.md` |

Also here: `logs/derive-by-hand.txt` (the two blind readers), `logs/tests.txt` (34 tests),
`logs/planted-bugs.txt` (20 planted bugs), `scripts/record_evidence.py` and `scripts/planted_bugs.py`. The
skill is `participant/skills/context-stable-identities/`: `SKILL.md`, `identity.py`, `make_batches.py`,
`tests/test_identity.py`. The made-up source records are in `participant/context/identity/batches/`, and the
map's own state in `participant/context/identity/state.json`.

The map holds 21 items: the 20 of the first sync, and one more that arrived later with no creation time. It
also lists one alias, one reused identifier held aside, one collision and six refused records.

## Stretch goals

- **Record an alias when a source changes an identifier:** done. When the source's own record names the
  identifier an item had before, the old identity becomes an alias of the new and still resolves. It is made
  only on the source's statement, never from a matching title. Recorded in part 5, and planted bug P.
- **Show identities that survive an export and re-import:** done. Part 6: the map is exported to one file and
  imported into an empty folder, byte for byte the same. And the source records, read again in the opposite
  order, give the same 20 identities with the same birth marks.

## Reproduce

    python3 -m unittest discover -s participant/skills/context-stable-identities/tests -v
    python3 participant/evidence/context-stable-identities/context-attempt-005/scripts/record_evidence.py
    python3 participant/evidence/context-stable-identities/context-attempt-005/scripts/planted_bugs.py

None of these contacts anything. The second works in a scratch folder and compares the handed-in map with what
it builds. The third changes `identity.py` while it runs and restores it. The blind reading cannot be
reproduced by a script.

## What was tested

| What | Result |
|---|---|
| Recorded checks | 34, all pass |
| Automated tests | 34, all pass (`logs/tests.txt`) |
| Planted bugs | 20 put into `identity.py` one at a time. Every one made at least one test fail (`logs/planted-bugs.txt`) |
| Blind readers | Round 1: 15 of 16. Round 2, revised rules: 22 of 22 |

Faults found while building:

- **The rules were not followable as first written.** See criterion 7. Twelve gaps, found by a reader and not
  by the tests, because the tests check the code and the gaps were in the words.
- **The assistant asked the first reader a wrong question:** to find three pairs of matching records where
  the list held two. The reader said so, which is some evidence it was not guessing.
- A check in the recording script tried to prove "titles are never compared" by searching the code for the
  word. It was fragile and failed. It was replaced by two direct trials of what decides reuse.
- Two tests held card identifiers the assistant had guessed and not looked up.
- A planted bug could not be planted after the rules were reworded, because it matched on the old wording.

## What could not be done, and limitations

- **A person has not tried the rules.** See criterion 7.
- **Reuse cannot be detected for Trello, without a creation time, or when the time is repeated.** See criterion 6.
- **Text is never read for meaning, so odd text is accepted.** The number `-7` is refused, and the text `"-7"`
  gives `jira:-7`. The text `"40003.0"` gives `jira:40003.0`, a separate identity beside `jira:40003`. A
  source that sometimes sends an id as text and sometimes as a decimal number would get a refusal one day and a
  second identity the next. Found by the second reader. Left as it is, because deciding that two such texts
  "mean" the same item is the kind of guess the rules exist to prevent.
- **A collision is decided inside one batch.** The same clash spread across two batches looks like an update
  or a reuse.
- **A newcomer held aside is kept thinly:** its title and creation time, not its whole record.
- **Nothing decides what to do with a reused identifier.** The rules say a person decides, and no tool here
  helps them do it or records what they chose.
- **The systems' promises are taken from memory of how those systems behave**, not checked against their
  documentation in this quest, and not tested against a real system. In particular, how GitHub treats a node ID
  when an issue is transferred is assumed, not verified.
- **The records are made up by the same assistant that wrote the rules.** A real export may hold a form these
  five batches do not.

## Reflection

*What happens to your identities if a source system is migrated and every identifier changes?*

Every item I hold becomes a stranger. The migrated system sends twenty records with twenty new identifiers, and
my rules do exactly what I told them to: twenty new identities, and nothing connecting them to the twenty I
already have. The old ones are not deleted. They just stop being seen. Every note I ever attached is still
there, attached to an item that will never appear again, and beside it sits a fresh copy with no notes.

That is the scenario at the top of this quest, the story whose notes "now belong to nothing", except that it
happens to everything at once. And it happens because my rule is strict, not in spite of it. I built identities
that survive any change a person can make to an item. A migration is not a person editing an item. It is the
source breaking the one promise the whole thing rests on.

The only clean way out is the stretch goal I nearly skipped. If the migration tells me, for each new
identifier, which old one it replaces, each old identity becomes an alias and everything follows. But that
has to come from the source. My rules refuse to work it out.

And that refusal is what I would find hard to hold to. After a migration I would be looking at an old story
and a new one with the same title, the same creation time and the same project, and a rule that says I may not
conclude they are the same. Everything in me would want to match them up. I think the rule is still right,
because the day I let titles and dates decide identity "just this once" is the day two different stories with
the same name get merged. But I would want to match them as a **proposal** a person approves, each one
recorded as an alias with the reason, and not as something the sync does quietly.

What I had not understood before this quest is that a stable identity is borrowed. I do not make it stable.
The source does, and I am only as safe as its promise. The best I can do is know which promise I am relying on,
keep a second one beside it to notice when the first breaks, and say plainly, as I had to for Trello, where I
have no second one at all.

## Sensitive values

- No token or credential was used. The quest reads and writes only local files.
- Every identifier is invented. No real project, customer, board, repository or person is in any file.
- The participant's real sandbox items, which are in this repository from earlier quests, were not used.
