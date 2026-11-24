# Context: identities that survive a rename and a move

Written by an AI assistant (Claude) at the participant's direction.

## 1. Purpose

This skill gives every work item from Jira, Trello or GitHub a local identity that does not change when its
title, its project or its place changes, and keeps a map of them. It reports two records that claim one
identity, and an identifier the source has reused, without overwriting anything.

It reads and writes local files only. It contacts nothing.

    python3 participant/skills/context-stable-identities/identity.py derive SYSTEM IDENTIFIER
    python3 participant/skills/context-stable-identities/identity.py sync --batch FILE
    python3 participant/skills/context-stable-identities/identity.py map
    python3 participant/skills/context-stable-identities/identity.py rules --out FILE
    python3 participant/skills/context-stable-identities/identity.py export --out FILE
    python3 participant/skills/context-stable-identities/identity.py import --from FILE --folder DIR

`--folder DIR` works on a map somewhere other than `participant/context/identity`. Python standard library only.

## 2. The rule

An identity is `SYSTEM:IDENTIFIER`: `jira`, `trello` or `github`, a colon, and the one field the source promises
never to change, character for character. For Jira and Trello that field is `id`. For GitHub it is `node_id`.

Nothing else goes into an identity: no title, key, number, short link, project, board, position, file name or
order. The full rules, written to be followed by hand, are in `participant/context/identity/rules.md`. That
document is written out from the tables in `identity.py`.

## 3. A record whose identity is already held

Beside each identity the map keeps a birth mark: the moment the source says the item was created.

| What arrives | What it is | What happens |
|---|---|---|
| the same birth mark | the same item, perhaps renamed or moved | updated in place. Each change is recorded |
| a different birth mark | the source reused the identifier | reported. The item held is untouched. The newcomer is held aside |
| two different records in one batch | a collision | reported. Neither is written |
| the same record twice in one batch | one delivery, repeated | applied once |

A title is never compared to decide any of these.

## 4. The files

In the map's folder: `state.json`, the map itself; `map.md`, written from it for people to read; `rules.md`;
and `batches/`, the made-up source records. `sync` applies one batch, once: a batch's name cannot be applied twice.

## 5. Exit codes

0 done. 1 the command could not run, and nothing was written. 3 done, and something was reported.

## 6. Tests

    python3 -m unittest discover -s participant/skills/context-stable-identities/tests -v

## 7. Limits

- **Reuse of a Trello card id cannot be detected.** A card's birth mark is read from the id itself, so a reused
  id has the same birth mark.
- **Reuse is detected only where both records state a creation time.** Otherwise the run says it could not check.
- **A source that reuses an identifier and repeats the creation time is not detected.**
- An identity is only as stable as the source's promise. If a source is migrated and every identifier changes,
  every item looks new, unless the source states each previous identifier.
- A newcomer held aside is recorded with its title and creation time, and not with its whole record.
- A collision is decided inside one batch. The same clash spread over two batches is treated as an update or a reuse.
