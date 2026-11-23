# GitHub: search for likely duplicates before an issue is filed

Written by an AI assistant (Claude) at the participant's direction.

## 1. Purpose

Before anyone files a new issue, this skill asks "have we already got this?" and answers with reasons.

It takes a draft of the issue about to be filed, searches the local index of issue records, and reports each
existing issue that is likely the same thing: which signals matched, how confident it is, and what it
recommends.

Its rule: **a title alone makes nothing a duplicate, and the skill only recommends. A person decides.**

It reads local files only. It contacts nothing, needs no token, and creates, links and closes nothing.

    python3 participant/skills/github-duplicate-search/search.py PROPOSAL [--index FILE] [--report FILE] [--equal-weights]

The skill uses the Python standard library only. It needs the `github-build-index` skill's folder beside it,
because it reads the index and the records with that skill's code.

## 2. The proposed issue

A small draft file: a front matter with a title, a repository and labels, each written as JSON, then the body.

    ---
    title: "Out of memory when saving the March orders"
    repository: "acme-fixture/tracker"
    labels: ["bug", "export"]
    ---
    What happened, with any error text, file names and versions.

Only the title is required. The more the body says, the more there is to compare.

## 3. What it searches

The index named with `--index`, by default `participant/context/github/duplicates/fixture.md`. The search:

1. checks first that the index is exactly what its records give now. If the index is stale or was edited by
   hand, the search **stops**: a search of it could miss an issue;
2. takes the list of issues from the index's rows;
3. follows each row to its record, for the body and the comments.

A record with a gap in a field the search needs is not compared, and is counted in the output.

## 4. The signals

Five signals beyond the title. Each matches, does not match, or is **not comparable** when one side has
nothing to compare. Not comparable is neither a match nor a miss.

| Signal | Points | It matches when |
|---|---:|---|
| Error text | 4 | both quote the same error name (such as `MemoryError`) or error code (such as `E-EXPORT-413`) |
| Named things | 3 | both name at least 2 of the same files, options, versions or pieces of code |
| Body wording | 3 | they share at least 6 meaningful words, and those are at least 35% of the shorter text |
| Labels | 2 | they share a label that says what the issue is about. `bug`, `enhancement` and the like do not count |
| Repository | 1 | the proposal is for the same repository |
| *Title* | 1 | the titles are the same or nearly. **Never counts toward a candidate** |

"Meaningful words" are the words of a text in lower case, without common words such as "the" and "when", and
with the commonest endings taken off, so that "crashes" and "crash" are one word.

The text of an existing issue is its body and its comments together.

## 5. Candidates and confidence

An existing issue is a **candidate** only when **at least 3 of the 5 signals beyond the title match**. So:

- an issue with the same title and nothing else in common is not a candidate;
- an issue with the same title and two other signals is still not a candidate;
- an issue with a different title and three other signals is one.

The confidence is on a scale of three, from the points:

| Confidence | Points, of 14 |
|---|---|
| high | 11 to 14 |
| medium | 9 or 10 |
| low | 6 to 8. 6 is the least that three signals beyond the title can add up to |

Candidates are listed strongest first. Each shows all six signals with what was found.

Issues that matched on something, and on fewer than three signals, are listed too, as **NOT A CANDIDATE**, with
how many they matched. They are never called duplicates. If a search finds no candidate it says **NONE**: it
does not offer the nearest issue just for being nearest.

## 6. The recommendation

One of three, for each candidate and for the search as a whole:

| When | Recommendation |
|---|---|
| high confidence, and the existing issue is open and in the same repository | `close-as-duplicate`: do not file a second issue, or close it if it was filed, and add what is new to the existing one |
| any other candidate: lower confidence, a closed issue, or another repository | `link`: file the issue and point to the other one |
| no candidate | `proceed` |

A closed issue with the same error is linked, not treated as a duplicate: if it is the same problem, it has
come back, and that is worth an issue.

The skill never acts on this. Every result ends "A person decides".

## 7. The report

With `--report FILE` the search writes a report for the one proposed issue: the recommendation, how to read it,
the scale, each candidate with its table of signals, the issues looked at and not candidates, and the counts.
It holds no date, so the same search gives the same report. The report cannot be written over the index or a
record.

## 8. The index is not changed

The search opens the index and the records for reading only. It takes the SHA-256 of the index and of every
record before and after, and says whether they are the same.

## 9. Weights

The points are weights. `--equal-weights` counts every signal as 1, to show what the weights change: the
confidence of a match, not which issues are candidates. With equal weights high is all five signals, medium
four, low three.

## 10. The made-up fixture

`make_fixture.py` writes nine made-up issue records, builds their index with the `github-build-index`
generator, and writes three proposed issues. The fixture holds a true duplicate with a different title, a near
duplicate, and an unrelated issue with the same title.

## 11. Tests

    python3 -m unittest discover -s participant/skills/github-duplicate-search/tests -v

The tests work on a fixture in a scratch folder. Nothing is contacted.

## 12. What it does not do

- It does not understand meaning. "Out of memory" and "crashes" are different words to it. A duplicate written
  in wholly different words, with no error text and nothing named, is missed.
- It recognises error text only as an error name ending in Error or Exception, or a code shaped like
  `E-EXPORT-413`. Other kinds of error message count only as wording.
- Its word handling is for English.
- It compares a proposal with existing issues, not existing issues with each other.
- It does not read the repository's issue templates.
- It does not contact GitHub, so it knows only what the local records hold.
