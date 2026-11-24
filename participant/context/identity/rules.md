# Identity rules: how a work item gets a local identity

Written by an AI assistant (Claude) at the participant's direction, for the quest `context-stable-identities`. This whole document is written out by
`participant/skills/context-stable-identities/identity.py rules`. Its tables come from the same tables the code applies. Its sentences are text in that file, and
it is the tests that hold the code to them.

These rules are meant to be followed by hand. Given a source record and this page, two people should write down the same identity.

## 1. What an identity is

    SYSTEM:IDENTIFIER

- **SYSTEM** is one of three words, exactly as written here, in lower case: `jira`, `trello`, `github`. A record from any other system,
  or whose system is written another way such as `Jira`, gets no identity. These rules do not cover it, and nothing is made up for it.
- **IDENTIFIER** is the value of one field of the source record, the one in the table below. It is the field the source system itself promises never to change.
  The field is at the top level of the record: Jira's `id` is the issue's own `id`, not the `id` of its project or of anything else inside it.
- Between them is one colon. Nothing else is in an identity.

| System | The identifier is the field | Why this field | Example |
|---|---|---|---|
| `jira` | `id` | Jira's issue id. Jira gives it when the issue is created and keeps it through every edit and every move between projects. | `jira:40003` |
| `trello` | `id` | Trello's card id. Trello gives it when the card is created and keeps it through every rename and every move between lists and boards. A real one is 24 characters of base 16. That is a description, not a test: an id of another shape is still used as it stands | `trello:6ae851100000000000000a02` |
| `github` | `node_id` | GitHub's global node ID. GitHub gives it when the issue is created. It is case-sensitive. | `github:I_kwFIX0303` |

## 2. Writing the identifier down

1. **If the identifier is text, use it character for character.** Do not change upper or lower case. Do not remove or add anything. `I_kwAB` and `I_kwab` are two
   different items. Text is never read as a number: the text `"0040003"` gives `jira:0040003`, and the text `"40003.0"` gives `jira:40003.0`.
2. **One conversion is allowed.** If the record has the identifier as a whole number that is zero or more, such as `40003`, write its digits: `40003`. So the number
   `40003` and the text `"40003"` give the same identity.
3. **Refuse everything else. Do not repair it.** A record gets no identity, and is reported, if its identifier is:
   - missing, or `null`;
   - a number with a fraction or an exponent, such as `40003.5`, `40003.0` or `4e4`, or a negative number;
   - `true` or `false`, a list, or an object;
   - empty text, or text longer than 200 characters;
   - text holding any character other than the letters `A` to `Z` and `a` to `z`, the digits `0` to `9`, and `_ - = + / .`. So no space, no colon, and no accented
     or non-Latin letter.

   Trimming a space or dropping a `.0` would be a guess about which item was meant.

**Text or number?** A source record is JSON. A value written inside double quotes is text. A value written without them is a number, `true`, `false` or `null`.
That is the only test. The text `"-7"` is an identifier, and the number `-7` is refused. The text forms are accepted as they stand, because text is never read for
what it might mean.

**Which system?** The system is not a field of the source record. It is which system's sync delivered the record, and a batch states it beside each record.

A record that gets no identity is called **refused** below, whether its identifier was refused or its system is not one of the three.

## 3. What an identity is never built from

For each system, the fields that look like an identity and are refused:

**jira**

| Field | Why it is refused |
|---|---|
| `key` | DEMO-42. It holds the project's key, so it changes when the issue moves to another project. |
| `fields.summary` | The title. Anyone can edit it, and two issues can share one. |
| `fields.project` | Where the issue lives now. It changes on a move. |
| `self` | An address. It holds the site's name, which changes if the site is renamed or moved. |

**trello**

| Field | Why it is refused |
|---|---|
| `shortLink` | The short link in the card's address. Stable in practice, and Trello does not promise it as the card's identity. |
| `idShort` | The card's number on its board. It is given again when the card moves to another board. |
| `name` | The title. Anyone can edit it, and two cards can share one. |
| `idBoard, idList` | Where the card is now. Both change on a move. |
| `pos` | The card's place in its list. It changes whenever anyone drags a card. |

**github**

| Field | Why it is refused |
|---|---|
| `number` | The issue's number in its repository. Another repository has its own issue 12, and the number changes on a transfer. |
| `title` | Anyone can edit it, and two issues can share one. |
| `repository` | Where the issue lives now. It changes on a transfer, and a repository can be renamed. |
| `html_url` | An address built from the owner, the repository and the number, all of which can change. |
| `id` | A second, numeric id. Also stable, and the node ID is the one GitHub's newer interface uses, so one field was chosen and this one refused, so that no item can get two identities. |

And for every system, never:

- the position of a record in a file or a batch
- the name of the file a record came from
- the order records are processed in
- the time of the sync
- any text a person can edit

The map shows an item's title, where it lives and its reference, beside its identity. That is so a reader can find the item. They are what is true **now**, they are
expected to change, and no identity is worked out from them.

## 4. A record whose identity is already held

Beside each identity the map keeps a **birth mark**: the moment the source says the item was created, in UTC. It is not part of the identity.

| System | The birth mark is |
|---|---|
| `jira` | the field `fields.created`: the creation time Jira states |
| `trello` | the first 8 characters of the card `id`, which are the creation time in seconds since 1970, written in base 16. The id carries its own birth. An id that is not 24 characters of base 16 has no birth mark |
| `github` | the field `created_at`: the creation time GitHub states |

A birth mark is a moment, not a piece of text. `2026-11-06T09:00:00.000+0000` and `2026-11-06T04:00:00-05:00` are the same moment and the same birth mark.

A **batch** is the set of records one sync delivered together, in one file. The map is built by applying batches one after another.

When a record arrives whose identity is already in the map **from an earlier batch**, compare birth marks. **Do not compare titles.** (Two records with one identity
inside the **same** batch are a different matter: see section 6.)

| What is found | What it is | What is done |
|---|---|---|
| The same birth mark | **The same item**, perhaps renamed or moved | It is updated in place. Each change of title, place or reference is recorded. The identity does not change |
| A different birth mark | **The source reused the identifier** for another item | It is reported. The item held is left exactly as it was. The newcomer is held aside for a person to decide |
| No birth mark on one side, or on both | Cannot be told | It is taken to be the same item, and the run says that reuse could not be checked |

## 5. When a source reuses an identifier

A source system promises not to. Some break the promise: after a restore from a backup, after a project is deleted and made again, or when two installations are
merged. When a different birth mark shows it has happened:

1. **Nothing is overwritten.** The item already held keeps its identity, its record and whatever is attached to it.
2. **The newcomer gets no identity yet.** It is held aside, with both birth marks, and listed in the map under "Reused identifiers".
3. **A person decides.** Either the old item is gone at the source and should be retired, or the two are separate and the newcomer needs an identity that says so.
   The skill does neither by itself, because either choice discards or renames something a person may depend on.

**For Trello this check has nothing to work with.** A card's birth mark is taken from its id. A reused id carries the same birth mark, so it looks like the same card.
Reuse of a Trello card id cannot be detected by these rules.

## 6. Two records in one batch with the same identity

A **collision**. If the records are the same in every field, it is one record delivered twice, and it is applied once. If they differ in any field, nobody can say which is
right. It is reported, **neither is written**, and the item already held under that identity, if there is one, is left as it was.

## 7. When a source changes an identifier

If the source's own record states the identifier the item had before, in the field `previous_identifier`, the old identity becomes an **alias** of the new one: it still
resolves, to the new identity, and what was kept under it follows. An alias is made only on the source's own statement. It is never worked out from a title that matches.

- `previous_identifier` is a field at the top level of the record. If it is absent or `null`, the source states no previous identifier, and this section does not apply.
- Otherwise it is written down by section 2, like any other identifier. If it is refused, the record is refused.
- If the map has never held the previous identity, no alias is made, and the record is simply a new item. The run says so.
- If the map holds an item under the old identity **and** one under the new, nothing is merged. The run says so, and a person decides.

## 8. Deriving an identity by hand

1. Which system is the record from? Write its word: `jira`, `trello` or `github`. If it is none of these, stop: the record has no identity.
2. Find the one field in the table of section 1. For the identity, ignore every other field. (The creation time is read for the birth mark, and `previous_identifier`
   for an alias. Neither goes into the identity.)
3. Apply section 2. If the identifier is refused, stop: the record has no identity.
4. Write the system, a colon, and the identifier.

The order of the records, the file they are in, and their titles play no part. Two records with the same title get two identities. One record, renamed and moved,
gets the identity it always had.
