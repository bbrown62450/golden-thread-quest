#!/usr/bin/env python3
"""Before an issue is filed: look for issues that are likely the same thing. Reads local files only.

See SKILL.md in this folder for what it does and the rules it follows.

    search.py PROPOSAL [--index FILE] [--report FILE] [--equal-weights]

PROPOSAL is a draft of the issue somebody is about to file: a title, a repository, labels and a body. The search
starts from the local index, follows each row to its record, and compares. It recommends. A person decides. It
creates, links and closes nothing, and it never writes to the index or to a record.

Exit codes: 0 searched, and the result is in the output (candidates or none); 1 stopped, nothing was searched.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import re
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))

# The signals beyond the title, strongest first: (name, what it is called, points).
SIGNALS = (("error", "Error text", 4), ("named", "Named things", 3), ("wording", "Body wording", 3),
           ("labels", "Labels", 2), ("repository", "Repository", 1))
TITLE_POINTS = 1           # the title is the weakest signal, and never counts toward NEEDED
NEEDED = 3                 # an issue is a candidate only when this many signals beyond the title match
MOST = sum(points for _, _, points in SIGNALS) + TITLE_POINTS
SCALE = (("high", 11, MOST), ("medium", 9, 10), ("low", 6, 8))     # 6 is the least three signals beyond the title can add up to
NAMED_NEEDED = 2           # shared named things needed for that signal
WORDS_NEEDED, WORDS_SHARE = 6, 0.35
TITLE_SHARE = 0.6
# Labels that say what kind of issue it is, not what it is about. Sharing one of these is not a signal.
CATCH_ALL = frozenset(("bug", "enhancement", "question", "help wanted", "good first issue", "duplicate", "invalid", "wontfix"))
STOP_WORDS = frozenset("""a about after again all also an and any are as at be because been before but by can could did do does
    each for from had has have here how if in into is it its just more most no not now of on once one only or other our out
    over same seems should so some such than that the their them then there these they this those through to too under until
    up very was we were what when where which while who will with would you your""".split())
ERROR_CODE = re.compile(r"\b[A-Z]{1,6}(?:-[A-Z]{2,12})+-\d{2,5}\b")
EXCEPTION = re.compile(r"\b[A-Z][A-Za-z]*(?:Error|Exception)\b")
CODE_SPAN = re.compile(r"(?<!`)`([^`\n]{2,60})`(?!`)")
FILE_NAME = re.compile(r"(?<![\w.-])[\w-]+\.(?:csv|py|js|css|html|md|json|ya?ml|txt|pdf)\b")
OPTION = re.compile(r"(?<![\w-])--[a-z][\w-]+")
VERSION = re.compile(r"\bv\d+\.\d+(?:\.\d+)?\b")
INDEX_ROW = re.compile(r"\| \[(?:[^\]\\]|\\.)*\]\(([^)]*)\) \| [0-9a-f]{12} \|$")


class Stop(Exception):
    pass


def say(text):
    print("github-duplicates: " + text, flush=True)


def plural(count, word, many=None):
    return "%d %s" % (count, word if count == 1 else many or word + "s")


def shown_path(path):
    try:
        relative = os.path.relpath(path)
    except ValueError:
        return os.path.basename(path)
    return os.path.basename(path) if relative.startswith("..") else relative


def load_indexer():
    """The github-build-index generator, loaded from its folder and not changed. It reads the index and the records."""
    path = os.path.join(HERE, "..", "github-build-index", "index.py")
    if not os.path.isfile(path):
        raise Stop("the github-build-index skill is not beside this one, and the search reads the index with it")
    spec = importlib.util.spec_from_file_location("indexer_for_the_duplicate_search", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------- what is compared


def errors_in(text):
    """Error codes and the names of errors a text quotes."""
    return {found.lower() for found in ERROR_CODE.findall(text) + EXCEPTION.findall(text)}


def named_in(text):
    """Files, options, versions and anything written as code: the things a text names. Error names are not counted twice."""
    found = set(CODE_SPAN.findall(text)) | set(FILE_NAME.findall(text)) | set(OPTION.findall(text)) | set(VERSION.findall(text))
    return {one.strip().lower() for one in found if one.strip()} - errors_in(text)


def words_in(text):
    """The meaningful words of a text: lower case, without common words, with the commonest endings taken off."""
    words = set()
    for word in re.findall(r"[a-z]{3,}", text.lower()):
        if word in STOP_WORDS:
            continue
        for ending in ("ing", "ed", "es", "s"):
            stem = word[:-len(ending)]
            if not word.endswith(ending) or len(stem) < 4 or word.endswith("thing") or word.endswith("ss"):
                continue
            if ending == "es" and not stem.endswith(("s", "x", "z", "ch", "sh")):
                continue                     # "writes" loses its s, not its es
            word = stem
            break
        words.add(word)
    return words


def share(ours, theirs):
    """How many meaningful words two texts share, and what part that is of the shorter one."""
    both = ours & theirs
    least = min(len(ours), len(theirs))
    return both, (len(both) / float(least) if least else 0.0)


def some(values, most=6):
    values = sorted(values)
    return ", ".join(values[:most]) + (" and %d more" % (len(values) - most) if len(values) > most else "")


def compare(proposal, issue):
    """Every signal for one existing issue: {name: (result, what was found)}. result is "match", "no" or "not comparable"."""
    found = {}
    ours, theirs = errors_in(proposal["text"]), errors_in(issue["text"])
    found["error"] = ("not comparable", "one of the two quotes no error") if not ours or not theirs else (
        ("match", "both quote: " + some(ours & theirs)) if ours & theirs else ("no", "they quote different errors"))
    ours, theirs = named_in(proposal["text"]), named_in(issue["text"])
    both = ours & theirs
    found["named"] = ("not comparable", "one of the two names no file, option or version") if not ours or not theirs else (
        ("match", "both name: " + some(both)) if len(both) >= NAMED_NEEDED else
        ("no", "they share %d, and %d are needed%s" % (len(both), NAMED_NEEDED, ": " + some(both) if both else "")))
    both, part = share(words_in(proposal["text"]), words_in(issue["text"]))
    found["wording"] = ("not comparable", "one of the two has no text to compare") if not words_in(proposal["text"]) or not words_in(issue["text"]) else (
        ("match", "%d meaningful words in common, %d%% of the shorter text: %s" % (len(both), round(part * 100), some(both, 8)))
        if len(both) >= WORDS_NEEDED and part >= WORDS_SHARE else
        ("no", "%d meaningful words in common, %d%% of the shorter text. %d and %d%% are needed" % (len(both), round(part * 100), WORDS_NEEDED, round(WORDS_SHARE * 100))))
    telling = lambda labels: {name.casefold() for name in labels} - CATCH_ALL
    ours, theirs = telling(proposal["labels"]), telling(issue["labels"])
    found["labels"] = ("not comparable", "one of the two has no label that says what it is about") if not ours or not theirs else (
        ("match", "both have: " + some(ours & theirs)) if ours & theirs else ("no", "no label in common that says what it is about"))
    found["repository"] = ("not comparable", "the proposal names no repository") if not proposal["repository"] or not issue["repository"] else (
        ("match", "both are for %s" % issue["repository"]) if proposal["repository"].casefold() == issue["repository"].casefold()
        else ("no", "the proposal is for another repository"))
    both, part = share(words_in(proposal["title"]), words_in(issue["title"]))
    same = " ".join(proposal["title"].casefold().split()) == " ".join(issue["title"].casefold().split())
    found["title"] = ("match", "the titles are the same" if same else "the titles share %d%% of their words" % round(part * 100)) \
        if same or (both and part >= TITLE_SHARE) else ("no", "the titles are different")
    return found


def weigh(found, equal_weights=False):
    """Returns (signals beyond the title that matched, score, confidence or None when it is not a candidate)."""
    beyond = sum(found[name][0] == "match" for name, _, _ in SIGNALS)
    points = sum((1 if equal_weights else worth) for name, _, worth in SIGNALS if found[name][0] == "match")
    points += (1 if equal_weights else TITLE_POINTS) if found["title"][0] == "match" else 0
    if beyond < NEEDED:
        return beyond, points, None
    if equal_weights:
        return beyond, points, {5: "high", 4: "medium"}.get(beyond, "low")
    return beyond, points, next(name for name, low, high in SCALE if low <= points <= high)


def recommend(proposal, issue, confidence):
    """One of the three recommendations for one candidate, with the reason. A person decides."""
    same_repo = bool(proposal["repository"]) and proposal["repository"].casefold() == str(issue["repository"]).casefold()
    if confidence == "high" and issue["state"] == "open" and same_repo:
        return "close-as-duplicate", "high confidence, and the existing issue is open and in the same repository"
    why = ("the existing issue is %s, so if this is the same problem it has come back" % issue["state"] if issue["state"] != "open" else
           "the existing issue is in another repository" if not same_repo else "the confidence is %s, not high" % confidence)
    return "link", why


# ---------------------------------------------------------------- reading the proposal, the index and the records


def read_proposal(path):
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except (OSError, UnicodeDecodeError):
        raise Stop("the proposed issue %s cannot be read" % shown_path(path))
    if not text.startswith("---\n") or "\n---\n" not in text[3:]:
        raise Stop("the proposed issue needs a front matter with a title, a repository and labels")
    end = text.index("\n---\n", 3)
    front = {}
    for line in text[4:end].split("\n"):
        key, colon, value = line.partition(": ")
        try:
            front[key] = json.loads(value) if colon else None
        except ValueError:
            raise Stop("the proposed issue's line \"%s\" cannot be read" % key[:40])
    title, repo, labels = front.get("title"), front.get("repository"), front.get("labels", [])
    if not isinstance(title, str) or not title.strip():
        raise Stop("the proposed issue needs a title")
    if repo is not None and not isinstance(repo, str):
        raise Stop("the proposed issue's repository must be text")
    if not isinstance(labels, list) or any(not isinstance(one, str) for one in labels):
        raise Stop("the proposed issue's labels must be a list of names")
    return {"title": title, "repository": repo, "labels": labels, "text": text[end + 5:], "file": path}


def read_index(indexer, index_path):
    """The issues the index lists, each read from its record. Stops if the index is not what its records give."""
    try:
        with open(index_path, encoding="utf-8") as f:
            text = f.read()
    except (OSError, UnicodeDecodeError):
        raise Stop("there is no readable index at %s" % shown_path(index_path))
    where = re.search(r"issue records in `([^`]+)/`", text)
    mark = re.search(r"^- fingerprint of the records: `([0-9a-f]{64})`$", text, re.M)
    if not where or not mark:
        raise Stop("%s is not an index written by the github-build-index skill" % shown_path(index_path))
    folder = os.path.normpath(os.path.join(os.path.dirname(index_path), where.group(1)))
    try:
        records, unreadable = indexer.read_all(folder)
    except indexer.Stop as why:
        raise Stop(str(why))
    if indexer.render(records, unreadable, where.group(1)) != text:
        raise Stop("the index is NOT what its records give now: it is stale, or it was edited by hand. A search of it could miss an "
                   "issue. Run the github-build-index `check`, build the index again, and search again")
    listed = [os.path.basename(urllib.parse.unquote(found.group(1))) for found in (INDEX_ROW.search(line) for line in text.split("\n") if line.startswith("| ")) if found]
    by_file = {one["file"]: one for one in records}
    issues = []
    for name in listed:
        one = by_file.get(name)
        if one is None:
            continue                         # a row of "Could not be indexed": not an issue record
        usable = all(not isinstance(one[key], indexer.Gap) for key in ("repository", "number", "title", "state", "labels"))
        issues.append({"file": name, "usable": usable, "repository": one["repository"], "number": one["number"], "title": one["title"],
                       "state": one["state"], "labels": one["labels"],
                       "text": "\n\n".join(block for _, _, block in indexer.blocks(one["text"])) if usable else ""})
    return {"text": text, "folder": folder, "fingerprint": mark.group(1), "issues": issues, "unreadable": len(unreadable), "rel": where.group(1)}


def digests(index_path, folder):
    """SHA-256 of the index and of every file in the records folder, to show afterwards that nothing was changed."""
    found = {}
    for path in [index_path] + sorted(os.path.join(folder, name) for name in os.listdir(folder)):
        if os.path.isfile(path):
            with open(path, "rb") as f:
                found[path] = hashlib.sha256(f.read()).hexdigest()
    return found


# ---------------------------------------------------------------- the search


def search(proposal, index, equal_weights=False):
    """Compare the proposal with every issue the index lists. Returns (candidates, looked at and not candidates, issues that matched on nothing)."""
    candidates, looked, nothing, skipped = [], [], 0, []
    for issue in index["issues"]:
        if not issue["usable"]:
            skipped.append(issue)
            continue
        found = compare(proposal, issue)
        beyond, points, confidence = weigh(found, equal_weights)
        row = dict(issue, found=found, beyond=beyond, points=points, confidence=confidence)
        if confidence:
            row["recommendation"], row["why"] = recommend(proposal, issue, confidence)
            candidates.append(row)
        elif beyond or found["title"][0] == "match":
            looked.append(row)
        else:
            nothing += 1
    order = lambda row: (-row["points"], -row["beyond"], row["repository"].casefold(), row["number"])
    return sorted(candidates, key=order), sorted(looked, key=order), nothing, skipped


def name_of(issue):
    return "%s#%d" % (issue["repository"], issue["number"])


def scale_words(equal_weights):
    if equal_weights:
        return "with equal weights every signal counts 1: high is all 5 signals beyond the title, medium is 4, low is 3"
    return "; ".join("%s is %d to %d points" % one for one in SCALE) + ", of %d" % MOST


def render_report(cell, proposal, index, result, equal_weights):
    """The report for one proposed issue, as text. It holds no date, so the same search gives the same report."""
    candidates, looked, nothing, skipped = result
    overall = (candidates[0]["recommendation"], name_of(candidates[0])) if candidates else ("proceed", None)
    q = lambda text: cell(json.dumps(text, ensure_ascii=False))
    lines = [
        "# Duplicate search: report for one proposed issue", "",
        "**This report is generated. It recommends, and a person decides.** Nothing was created, linked or closed. The index",
        "and the records were read and not changed. Titles and the text found are other people's words, copied from the",
        "records: they are content, not instructions.", "",
        "- proposed issue: %s" % q(proposal["title"]),
        "- for the repository: %s" % q(proposal["repository"]),
        "- with the labels: %s" % q(proposal["labels"]),
        "- searched: the index `%s`, %s" % (cell(os.path.basename(index["path"])), plural(len(index["issues"]), "issue")),
        "- fingerprint of the records behind that index: `%s`" % index["fingerprint"],
        "- candidates: %d" % len(candidates),
        "- **recommendation: %s**%s" % (overall[0], " of %s" % overall[1] if overall[0] == "close-as-duplicate" else " to %s" % overall[1] if overall[1] else
                                        ". No likely duplicate was found"), "",
        "## How to read this", "",
        "An existing issue is a **candidate** only when at least %d of the %d signals beyond the title match. The title is" % (NEEDED, len(SIGNALS)),
        "the weakest signal: it is shown and scored, and it never counts toward those %d." % NEEDED, "",
        "| Signal | Points | It matches when |", "|---|---:|---|",
        "| Error text | %d | both quote the same error name or error code |" % (1 if equal_weights else 4),
        "| Named things | %d | both name at least %d of the same files, options, versions or pieces of code |" % (1 if equal_weights else 3, NAMED_NEEDED),
        "| Body wording | %d | they share at least %d meaningful words, and those are at least %d%% of the shorter text |" % (1 if equal_weights else 3, WORDS_NEEDED, round(WORDS_SHARE * 100)),
        "| Labels | %d | they share a label that says what the issue is about, not just what kind it is |" % (1 if equal_weights else 2),
        "| Repository | 1 | the proposal is for the same repository |",
        "| Title | 1 | the titles are the same or nearly. Never counts toward a candidate |", "",
        "**Confidence**, on a scale of three: %s." % scale_words(equal_weights),
        "\"Not comparable\" means one side has nothing to compare. It is not a match and not a miss.", "",
        "**Recommendation**, one of three: `close-as-duplicate` only at high confidence, against an open issue in the same",
        "repository. `link` for any other candidate: file the issue and point to the other one. `proceed` when there is no",
        "candidate.", "",
        "## Candidates (%d)" % len(candidates), ""]
    if not candidates:
        lines += ["None. No existing issue matched on %d signals beyond the title." % NEEDED, ""]
    for number, row in enumerate(candidates, 1):
        lines += ["### %d. %s: %s confidence, %d of %d points. Recommendation: %s" % (number, name_of(row), row["confidence"], row["points"],
                                                                                 (len(SIGNALS) + 1) if equal_weights else MOST, row["recommendation"]), "",
                  "- title of the existing issue: %s" % q(row["title"]),
                  "- state: %s. Labels: %s" % (cell(row["state"]), q(row["labels"])),
                  "- record: [%s](%s)" % (cell(row["file"]), urllib.parse.quote("%s/%s" % (index["rel"], row["file"]))),
                  "- signals beyond the title that matched: %d of %d" % (row["beyond"], len(SIGNALS)),
                  "- why this recommendation: %s" % row["why"], "",
                  "| Signal | Points | Result | What was found |", "|---|---:|---|---|"]
        for name, label, worth in SIGNALS + (("title", "Title", TITLE_POINTS),):
            result_word, evidence = row["found"][name]
            lines.append("| %s | %d | %s | %s |" % (label, (1 if equal_weights else worth) if result_word == "match" else 0, result_word.upper() if result_word == "match" else result_word, cell(evidence)))
        lines.append("")
    lines += ["## Looked at, and not candidates (%d)" % len(looked), "",
              "Issues that matched on something, and on fewer than %d signals beyond the title. They are not reported as duplicates." % NEEDED, ""]
    for row in looked:
        matched = [label for name, label, _ in SIGNALS if row["found"][name][0] == "match"]
        lines.append("- %s %s (%s): %d of the %d needed. Matched: %s%s" % (
            name_of(row), q(row["title"]), cell(row["state"]), row["beyond"], NEEDED, ", ".join(matched) or "nothing beyond the title",
            ". **The title matched (%s), and a title alone makes nothing a duplicate**" % row["found"]["title"][1] if row["found"]["title"][0] == "match" else ""))
    lines += [] if looked else ["None."]
    lines += ["", "## The rest", "",
              "- issues that matched on nothing at all: %d" % nothing,
              "- records the search could not compare, because a field is a gap: %d" % len(skipped),
              "- files in the records folder that are not issue records, and were not searched: %d" % index["unreadable"]]
    return "\n".join(lines) + "\n"


def run(args):
    indexer = load_indexer()
    here_index = os.path.normpath(args.index or os.path.join(HERE, "..", "..", "context", "github", "duplicates", "fixture.md"))
    proposal = read_proposal(args.proposal)
    index = read_index(indexer, here_index)
    index["path"] = here_index
    before = digests(here_index, index["folder"])
    say("proposed issue: %s, for %s, labels %s" % (json.dumps(proposal["title"], ensure_ascii=False), json.dumps(proposal["repository"]), json.dumps(proposal["labels"])))
    say("searching the index %s: %s. The index was checked first, and is what its records give" % (shown_path(here_index), plural(len(index["issues"]), "issue")))
    say("a candidate needs %d of the %d signals beyond the title. Confidence: %s" % (NEEDED, len(SIGNALS), scale_words(args.equal_weights)))
    result = search(proposal, index, args.equal_weights)
    candidates, looked, nothing, skipped = result
    for number, row in enumerate(candidates, 1):
        say("CANDIDATE %d: %s %s, %s" % (number, name_of(row), json.dumps(row["title"], ensure_ascii=False), row["state"]))
        say("    confidence %s, %d points. Signals beyond the title that matched: %d of %d. Recommendation: %s (%s)"
            % (row["confidence"], row["points"], row["beyond"], len(SIGNALS), row["recommendation"], row["why"]))
        for name, label, _ in SIGNALS + (("title", "Title", 1),):
            say("    %-13s %-15s %s" % (label, row["found"][name][0].upper() if row["found"][name][0] == "match" else row["found"][name][0], row["found"][name][1]))
    for row in looked:
        matched = [label for name, label, _ in SIGNALS if row["found"][name][0] == "match"]
        say("NOT A CANDIDATE: %s %s: %d of the %d signals needed (%s)%s" % (
            name_of(row), json.dumps(row["title"], ensure_ascii=False), row["beyond"], NEEDED, ", ".join(matched) or "nothing beyond the title",
            ". The title matched: %s. A title alone makes nothing a duplicate" % row["found"]["title"][1] if row["found"]["title"][0] == "match" else ""))
    say("issues that matched on nothing at all: %d. Records that could not be compared: %d" % (nothing, len(skipped)))
    if args.report:
        text = render_report(indexer.cell, proposal, index, result, args.equal_weights)
        os.makedirs(os.path.dirname(os.path.abspath(args.report)), exist_ok=True)
        if os.path.realpath(args.report) in {os.path.realpath(path) for path in before}:
            raise Stop("the report would be written over the index or a record. It was not written")
        with open(args.report + ".tmp", "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(args.report + ".tmp", args.report)
        say("report: written to %s" % shown_path(args.report))
    after = digests(here_index, index["folder"])
    say("unchanged: the index and the %s behind it have the same SHA-256 after the search as before it: %s"
        % (plural(len(before) - 1, "record file"), "yes" if before == after else "NO, SOMETHING CHANGED"))
    if not candidates:
        say("RESULT: NONE. No likely duplicate was found. Recommendation: proceed. A person decides")
    else:
        best = candidates[0]
        say("RESULT: %s. Strongest: %s, %s confidence. Recommendation: %s. A person decides"
            % (plural(len(candidates), "likely duplicate"), name_of(best), best["confidence"], best["recommendation"]))
    return 0 if before == after else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description="Look for likely duplicates of a proposed issue in the local index. Reads local files only.")
    parser.add_argument("proposal", help="the draft of the issue about to be filed")
    parser.add_argument("--index", help="the index to search (default: participant/context/github/duplicates/fixture.md)")
    parser.add_argument("--report", help="write the report for this proposal to this file")
    parser.add_argument("--equal-weights", action="store_true", help="count every signal as 1, to show what the weights change")
    args = parser.parse_args(argv)
    try:
        return run(args)
    except Stop as why:
        say("STOPPED: %s." % why)
        say("Nothing was searched and nothing was written.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
