#!/usr/bin/env python3
"""Generates a stand-up digest and its gap report from local context. It reads and writes local files only.

    python3 participant/skills/scrum-standup-digest/digest.py generate --context DIR --as-of TIME --previous STATE --out DIR [--scope all|mine]
    python3 participant/skills/scrum-standup-digest/digest.py check    --context DIR --as-of TIME --out DIR [--scope all|mine]

    --context   a folder of local context: items/*.md (canonical work-item records), notes/*.md, sync-runs.md, redaction.md
    --as-of     the time the digest is for, in UTC, such as 2026-11-24T09:00:00Z. REQUIRED. The computer's clock is never read:
                every age in the digest is counted from this time, so the same inputs always give the same bytes.
    --previous  the digest-state.json written by the previous digest, or the word "none". It must not be the file this run writes.
    --out       where to write standup-digest.md, standup-gaps.md and digest-state.json
    --scope     "all" (the default), or "mine": only items whose record says assigned_to_me is yes

`check` reads the finished digest and gap report back and compares them with the context. It shares the reading of the
context with the generator, so a fault in that reading is invisible to it. It does not use the generator's conclusions.
Exit code 0: no problem found. 1: problems, each printed.

THE RULES ARE IN SKILL.md, beside this file. The thresholds are the two constants below, and SKILL.md states the same
numbers: a test fails if they differ.

It imports nothing that can reach a network, and opens no file outside --context, --previous and --out.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import sys

STALE_AFTER_HOURS = 24   # a record retrieved more than this long before --as-of is stale. At exactly the limit it is fresh.
AGING_AFTER_DAYS = 5     # an item in progress whose source had not changed for this many whole days, or more, WHEN IT WAS RETRIEVED.
MODEL = "work-item/1"
STATUS_WORDS = {"open": "open, which is to say not started as far as the source says", "in_progress": "in progress", "done": "done", "dropped": "closed without being done"}
SHORT = {"open": "open", "in_progress": "in progress", "done": "done", "dropped": "closed without being done"}
TIME = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
IDENTITY = re.compile(r"^(jira|github|trello):[A-Za-z0-9_.-]+$")
RUN_NAME = re.compile(r"^[A-Za-z0-9_.:-]+$")
# What counts as a record in a person's note: exactly these two forms, alone on a line. Anything else in a note is prose.
NOTE_LINK = re.compile(r"^- (blocked_by|blocks): ((?:jira|github|trello):[A-Za-z0-9_.-]+)\s*$")
NOTE_HEAD = re.compile(r"^# Notes on ((?:jira|github|trello):[A-Za-z0-9_.-]+)\s*$", re.M)
# Taken out of any of other people's text before it is printed. Names come from redaction.md as well.
SHAPES = [("[email address]", re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")), ("[customer number]", re.compile(r"\bCUST-\d+\b")),
          ("[telephone number]", re.compile(r"(?<![\w.:-])\+?\d(?!\d{3}-\d\d-\d\d)[\d ()-]{8,}\d(?![\w.])"))]


def time_of(text):
    """A UTC time, or None if the text is not one. A month 13 is not one."""
    if not isinstance(text, str) or not TIME.match(text):
        return None
    try:
        return datetime.datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None


def age_words(seconds):
    days, hours, minutes = int(seconds // 86400), int(seconds % 86400 // 3600), int(seconds % 3600 // 60)
    if seconds >= 48 * 3600:
        return "%d days %d h %d min" % (days, hours, minutes)
    return "%d h %d min" % (int(seconds // 3600), minutes)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def write(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def file_name(identity):
    system, _, source_id = identity.partition(":")
    return "%s-%s.md" % (system, re.sub(r"[^A-Za-z0-9_.-]", "_", source_id))


def parse_record(text):
    """One canonical record into (canonical, provenance, source). Raises ValueError saying why it cannot be read."""
    head = re.match(r'---\nformat: (".*")\nidentity: (".*")\n---\n', text)
    blocks = re.findall(r"^## (Canonical fields|Provenance|Source fields: \w+)\n.*?^```text\n(.*?)^```\n", text, re.S | re.M)
    if not head or [name.split(":")[0] for name, _ in blocks] != ["Canonical fields", "Provenance", "Source fields"]:
        raise ValueError("it is not a canonical work-item record")
    if json.loads(head.group(1)) != MODEL:
        raise ValueError("it is of model version %s, and this generator reads %s" % (json.loads(head.group(1)), MODEL))
    parts = []
    for _, body in blocks:
        fields = {}
        for line in body.split("\n"):
            if line:
                name, _, value = line.partition(": ")
                fields[name] = json.loads(value)
        parts.append(fields)
    canonical, provenance, source = parts
    for name in ("identity", "system", "title", "status", "status_basis", "status_source", "assigned_to_me", "blocked", "source_updated_at"):
        if name not in canonical:
            raise ValueError("it has no field %s" % name)
    if json.loads(head.group(2)) != canonical["identity"] or not IDENTITY.match(str(canonical["identity"])):
        raise ValueError("its identity is missing, or is not the one at the top of the file")
    if canonical["status"] not in STATUS_WORDS:
        raise ValueError("its status is not one of open, in_progress, done, dropped")
    if canonical["status_basis"] not in ("stated", "inferred", "assumed"):
        raise ValueError("its status_basis is not one of stated, inferred, assumed")
    if canonical["blocked"] not in ("yes", "no", "unknown"):
        raise ValueError("its blocked field is not one of yes, no, unknown")
    return canonical, provenance, source


def load(context):
    """Everything the generator may know. Nothing else is read. `trouble` holds what could not be used, each with a reason."""
    items, trouble = {}, []
    folder = os.path.join(context, "items")
    seen = {}
    for name in sorted(os.listdir(folder)):
        if not name.endswith(".md"):
            continue
        try:
            canonical, provenance, source = parse_record(read(os.path.join(folder, name)))
        except (ValueError, KeyError, TypeError, AttributeError) as problem:
            trouble.append(("MISSING", "items/%s" % name, "the record file cannot be read: %s" % problem, "anything about the item in that file"))
            continue
        identity = canonical["identity"]
        if identity in seen:
            trouble.append(("MISSING", identity, "two record files, items/%s and items/%s, both say they are this item. Neither is used" % (seen[identity], name), "anything about it"))
            items.pop(identity, None)
            continue
        seen[identity] = name
        items[identity] = {"c": canonical, "p": provenance, "s": source, "file": name}
    notes, note_files = {}, {}
    folder = os.path.join(context, "notes")
    for name in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
        if not name.endswith(".md"):
            continue
        text = read(os.path.join(folder, name))
        about = NOTE_HEAD.search(text)
        if not about:
            trouble.append(("UNSUPPORTED", "notes/%s" % name, "the note's heading does not name an item in the form \"# Notes on IDENTITY\", so nothing in it is used", "anything it may record"))
            continue
        bullets = [line for line in text.split("\n") if line.startswith(("- ", "* "))]
        links = [(m.group(1), m.group(2)) for m in map(NOTE_LINK.match, bullets) if m]
        notes.setdefault(about.group(1), []).extend(links)
        note_files.setdefault(about.group(1), []).append(name)
        if len(bullets) > len(links):
            trouble.append(("UNSUPPORTED", about.group(1), "its note, notes/%s, has %d line%s that %s not in the form of a record. Prose in a note is not read. A person should read it"
                            % (name, len(bullets) - len(links), "" if len(bullets) - len(links) == 1 else "s", "is" if len(bullets) - len(links) == 1 else "are"), "whatever those lines say"))
    runs = []
    for run, body in re.findall(r"^## (\S+)\n(.*?)(?=^## |\Z)", read(os.path.join(context, "sync-runs.md")), re.S | re.M):
        field = lambda key: (re.search(r"^- %s: (.*)$" % key, body, re.M) or [None, ""])[1].strip()  # noqa: E731
        listed = [] if field("items") in ("", "none") else [one.strip() for one in field("items").split(",")]
        runs.append({"run": run, "system": field("system"), "retrieved_at": field("retrieved_at"), "result": field("result"), "items": listed})
    names = [n.strip() for n in re.findall(r"^- (.+)$", read(os.path.join(context, "redaction.md")), re.M)] if os.path.exists(os.path.join(context, "redaction.md")) else []
    return {"items": items, "trouble": trouble, "notes": notes, "note_files": note_files, "runs": runs, "names": names}


def safe(text, names):
    """Other people's text made fit to print: redacted, and with nothing in it that could end the quotation it sits in,
    start a line, or be taken for markup or for one of the generator's own citations. It is never read for meaning."""
    out = str(text)
    for name in sorted(names, key=len, reverse=True):
        out = re.sub(r"(?<!\w)%s(?!\w)" % re.escape(name), "[name]", out, flags=re.I)
    for word, shape in SHAPES:
        out = shape.sub(word, out)
    out = re.sub(r"[\x00-\x1f\x7f\u2028\u2029]", " ", out)
    for bad, good in (("`", "'"), ('"', "'"), ("|", "/"), ("<", "("), (">", ")"), ("[x]", "(x)")):
        out = out.replace(bad, good)
    out = re.sub(r"\[(?!name\]|email address\]|customer number\]|telephone number\])", "(", out)
    out = re.sub(r"(?<!\[name)(?<!\[email address)(?<!\[customer number)(?<!\[telephone number)\]", ")", out)
    return out if len(out) <= 90 else out[:87] + "..."


def links_of(identity, entry, notes, note_files):
    """The recorded links of one item: (kind, other identity, where it is recorded). Never from a title."""
    found = []
    for link in entry["s"].get("jira.issuelinks") or []:
        kind = link.get("type") if isinstance(link, dict) else None
        kind = kind.get("inward") if isinstance(kind, dict) else None
        for end, word in (("inwardIssue", "blocked_by"), ("outwardIssue", "blocks")):
            other = link.get(end) if isinstance(link, dict) else None
            if kind == "is blocked by" and isinstance(other, dict) and IDENTITY.match("jira:%s" % other.get("id")):
                found.append((word, "jira:%s" % other.get("id"), "a Jira link saved with the record"))
    where = "a person's note, `notes/%s`, which carries no date" % "`, `notes/".join(note_files.get(identity, []))
    for kind, other in notes.get(identity, []):
        found.append((kind, other, where))
    return found


def build(context, as_of, previous, scope="all"):
    """Works everything out. Returns the model that the digest, the gap report and the state are written from."""
    now = time_of(as_of)
    data = load(context)
    items, notes = data["items"], data["notes"]
    in_scope = lambda i: scope == "all" or items[i]["c"].get("assigned_to_me") == "yes"  # noqa: E731
    gaps = []

    def gap(kind, what, reason, unsaid):
        gaps.append({"kind": kind, "what": what, "reason": reason, "unsaid": unsaid})

    for kind, what, reason, unsaid in data["trouble"]:
        gap(kind, what, reason, unsaid)

    runs = []
    for run in data["runs"]:
        at = time_of(run["retrieved_at"])
        age = (now - at).total_seconds() if at else None
        runs.append(dict(run, age=age, fresh=run["result"] == "completed" and age is not None and 0 <= age <= STALE_AFTER_HOURS * 3600))
    completed = {r["run"]: r for r in runs if r["result"] == "completed"}

    # Fresh or stale. What cannot be shown to be fresh is stale.
    fresh, stale = {}, {}
    for identity in sorted(items):
        if not in_scope(identity):
            continue
        entry = items[identity]
        retrieved, run = entry["p"].get("retrieved_at"), entry["p"].get("sync_run")
        at = time_of(retrieved)
        entry["age"] = (now - at).total_seconds() if at else None
        if at is None:
            stale[identity] = "its record gives no retrieval time that can be read, so it cannot be shown to be fresh"
        elif entry["age"] < 0:
            stale[identity] = "its record says it was retrieved at %s, after the time this digest is for" % retrieved
        elif entry["age"] > STALE_AFTER_HOURS * 3600:
            stale[identity] = "retrieved %s, which is %s before this digest. The limit is %d hours" % (retrieved, age_words(entry["age"]), STALE_AFTER_HOURS)
            latest = [r for r in runs if r["system"] == entry["c"]["system"] and r["fresh"]]
            if latest and all(identity not in r["items"] for r in latest):
                stale[identity] += ". The latest completed %s run does not list it, and nothing recorded says why" % entry["c"]["system"]
        elif run not in completed:
            stale[identity] = "its record names the run %s, which sync-runs.md does not list as completed, so its retrieval time cannot be confirmed" % safe(run, data["names"])
        elif completed[run]["retrieved_at"] != retrieved:
            stale[identity] = "its record says it was retrieved at %s, and the run it names says %s" % (retrieved, completed[run]["retrieved_at"])
        else:
            fresh[identity] = entry["age"]
        if identity in stale:
            gap("STALE", identity, stale[identity], "its status, or anything else of it, as current")

    listed = {}
    for run in runs:
        for identity in run["items"]:
            listed[identity] = run
    unreadable = {what[len("items/"):] for kind, what, _, _ in data["trouble"] if what.startswith("items/")}
    for identity, run in sorted(listed.items()):
        if identity not in items and file_name(identity) not in unreadable and not any(g["what"] == identity for g in gaps):
            gap("MISSING", identity, "the run %s says it retrieved this item, and there is no record of it in the local context%s" % (run["run"], "" if scope == "all" else ". Whether it is in this digest's scope cannot be told"), "anything about it")

    # Status: asserted only when the source states it and the record is fresh.
    stated = {i: items[i] for i in fresh if items[i]["c"]["status_basis"] == "stated"}
    for identity in sorted(fresh):
        c = items[identity]["c"]
        if c["status_basis"] != "stated":
            gap("UNSUPPORTED", identity, "its status, %s, is %s and not stated by the source" % (c["status"], c["status_basis"]), "its status, as a fact. It is shown in the digest apart")

    # Blocked and blocking: from recorded fields and explicit notes only.
    blocked_facts, blocking_facts, inferences, unknown_blocked, waiting, no_blocker_named = [], [], [], [], [], []
    for identity in sorted(fresh):
        entry = items[identity]
        c = entry["c"]
        links = links_of(identity, entry, notes, data["note_files"])
        blockers = [(other, where) for kind, other, where in links if kind == "blocked_by"]
        if c["blocked"] == "yes":
            basis = c.get("blocked_basis")
            blocked_facts.append((identity, "its record's `blocked` field says yes. The record gives as its basis: %s" % ("\"%s\"" % safe(basis, data["names"]) if basis else "nothing")))
            if not blockers:
                no_blocker_named.append(identity)
        for other, where in blockers:
            if c["blocked"] != "yes" or where.startswith("a person"):
                blocked_facts.append((identity, "recorded as blocked by `%s`, in %s%s" % (other, where, "" if c["blocked"] == "yes" else ". Its record's `blocked` field says %s" % c["blocked"])))
        if c["blocked"] == "unknown" and not blockers:
            unknown_blocked.append(identity)
        for kind, other, where in links:
            if kind == "blocks":
                blocking_facts.append((identity, other, where))
                if other not in items and not any(g["what"] == other for g in gaps):
                    gap("MISSING", other, "`%s` is recorded as blocking it, and there is no local record of it" % identity, "anything about it")
        not_done, done, unseen = [], [], []
        for other, where in blockers:
            if other not in items:
                if not any(g["what"] == other for g in gaps):
                    gap("MISSING", other, "`%s` is recorded as blocked by it, and there is no local record of it" % identity, "whether it is done, and so whether `%s` can proceed" % identity)
                unseen.append((other, "there is no local record of it"))
            elif not in_scope(other):
                unseen.append((other, "it is outside this digest's scope"))
            elif other in stale:
                unseen.append((other, "its record is stale"))
            elif other not in stated:
                unseen.append((other, "the source does not state its status"))
            elif stated[other]["c"]["status"] in ("done", "dropped"):
                done.append(other)
            else:
                not_done.append(other)
        for other in not_done:
            inferences.append(("I1", "`%s` is waiting on `%s`, which is %s." % (identity, other, SHORT[stated[other]["c"]["status"]]), [identity, other]))
        for other, why in unseen:
            inferences.append(("I3", "`%s` waits on `%s`, and whether that is done is not known here: %s." % (identity, other, why), [identity]))
        if blockers and not not_done and not unseen:
            inferences.append(("I2", "Every recorded blocker of `%s` is done or closed (%s). That does not say `%s` is free: its own record may still say blocked, and a blocker may not be recorded."
                               % (identity, ", ".join("`%s`" % o for o in done), identity), [identity] + done))
        if not_done or unseen:
            waiting.append(identity)
    if unknown_blocked:
        gap("UNSUPPORTED", ", ".join(unknown_blocked), "for each of these, the record's `blocked` field is unknown and no note records a blocker. Nothing else is read to decide it",
            "that they are blocked, or that they are not")

    # Aging: in progress, stated, fresh, and unchanged at the source for the threshold or longer WHEN RETRIEVED.
    aging = []
    for identity in sorted(stated):
        c = stated[identity]["c"]
        if c["status"] != "in_progress":
            continue
        changed = time_of(c["source_updated_at"])
        if changed is None:
            gap("UNSUPPORTED", identity, "its record gives no time of last change that can be read", "whether it is aging")
            continue
        days = int((time_of(stated[identity]["p"]["retrieved_at"]) - changed).total_seconds() // 86400)
        if days >= AGING_AFTER_DAYS:
            aging.append((identity, days, c["source_updated_at"]))

    # Changes since the previous digest, by identity.
    changes = []
    if previous is not None and previous.get("scope") != scope:
        gap("UNSUPPORTED", "changes since the previous digest", "the previous digest's scope was \"%s\" and this one's is \"%s\", so the two cannot be compared" % (safe(previous.get("scope"), []), scope), "what was added, removed or changed")
        previous = None
    elif previous is None:
        gap("UNSUPPORTED", "changes since the previous digest", "no previous digest's state was given", "what was added, removed or changed")
    if previous is not None:
        before = previous["items"]
        now_ids = set(i for i in items if in_scope(i))
        for identity in sorted(now_ids - set(before)):
            changes.append(("ADDED", identity, "it was not in the previous digest's context"))
        for identity in sorted(set(before) - now_ids):
            gone = "it is in the local context and outside this digest's scope" if identity in items else "there is no record of it now"
            run_says = [r for r in runs if r["fresh"] and r["system"] == identity.split(":")[0]]
            if identity not in items and run_says and all(identity not in r["items"] for r in run_says):
                gone += ", and the latest completed %s run does not list it" % identity.split(":")[0]
            changes.append(("REMOVED", identity, "it was in the previous digest's context, and %s" % gone))
            gap("UNSUPPORTED", identity, "it has gone from this digest's context since the previous digest, and nothing recorded says why", "that it was finished, dropped, moved or handed on")
        for identity in sorted(now_ids & set(before)):
            was = before[identity]
            if was.get("status") == items[identity]["c"]["status"]:
                continue
            if identity in stated and was.get("asserted"):
                changes.append(("STATUS", identity, "%s in the previous digest, %s now" % (SHORT.get(was["status"], "unknown"), SHORT[stated[identity]["c"]["status"]])))
            else:
                gap("UNSUPPORTED", identity, "its recorded status differs from the previous digest's, and one of the two could not be asserted (stale, or not stated by the source)", "that its status changed")

    for run in runs:
        run["used"] = sum(1 for i in fresh if items[i]["p"].get("sync_run") == run["run"])
    for system in sorted({entry["c"]["system"] for i, entry in items.items() if in_scope(i)}):
        done_runs = [r for r in runs if r["system"] == system and r["result"] == "completed"]
        if not any(r["fresh"] for r in done_runs):
            last = max(done_runs, key=lambda r: r["retrieved_at"])["run"] if done_runs else "none"
            gap("STALE", "the whole of %s" % system, "no completed %s run is within %d hours of this digest. The last completed run is %s" % (system, STALE_AFTER_HOURS, last), "anything current about %s work" % system)

    return {"as_of": as_of, "scope": scope, "data": data, "items": items, "fresh": fresh, "stale": stale, "stated": stated, "gaps": gaps, "blocked": blocked_facts,
            "blocking": blocking_facts, "inferences": inferences, "aging": aging, "changes": changes, "previous": previous, "runs": runs, "in_scope": in_scope,
            "waiting": waiting, "no_blocker_named": no_blocker_named}


def cite(model, identity):
    """The citation every statement carries: the identity, when it was retrieved, how old that is, and the run."""
    entry = model["items"][identity]
    run = entry["p"].get("sync_run")
    return "`%s`, retrieved %s (%s before this digest), run `%s`" % (identity, entry["p"]["retrieved_at"], age_words(entry["age"]), run if RUN_NAME.match(str(run)) else "unreadable")


def title_of(model, identity):
    return "title, redacted: \"%s\"" % safe(model["items"][identity]["c"]["title"], model["data"]["names"])


def render_digest(model):
    items, stated, names = model["items"], model["stated"], model["data"]["names"]
    previous = model["previous"]
    by_status = lambda status: [i for i in sorted(stated) if stated[i]["c"]["status"] == status]  # noqa: E731
    kinds = lambda kind: sum(1 for g in model["gaps"] if g["kind"] == kind)  # noqa: E731
    blocked_ids = sorted({i for i, _ in model["blocked"]})
    out = ["# Stand-up digest, as of %s" % model["as_of"], "",
           "**Built from made-up context.**" if items and all(e["p"].get("sync_source") == "made-up" for e in items.values()) else "**Built from local context.**",
           "Written by `participant/skills/scrum-standup-digest/digest.py`. No source system was contacted while it was written: it reads local files only.", "",
           "- Scope: %s" % ("every item in the local context" if model["scope"] == "all" else "only items whose record says `assigned_to_me` is yes. That is a field of the record. This digest says nothing about any person"),
           "- Window: %s" % ("from %s, the time the previous digest was for, to %s" % (previous["as_of"], model["as_of"]) if previous else "no previous digest could be compared with. This digest is for %s and reports no changes" % model["as_of"]),
           "- A record is **stale** if it was retrieved more than %d hours before %s, or cannot be shown to be fresh. A stale record is not stated as current." % (STALE_AFTER_HOURS, model["as_of"]),
           "- An item is **aging** if it is in progress and, when it was retrieved, its source had not changed for %d whole days or more." % AGING_AFTER_DAYS,
           "- **Every age here is counted to %s.** Read later than that, everything is older than it says." % model["as_of"],
           "- Gap report: `standup-gaps.md`, beside this file. It has %d entries: what this digest does not assert, and why." % len(model["gaps"]), "",
           "## At a glance", "",
           "Counts only. Each is of lines further down, where every item is cited.", "",
           "- In progress: %d. Recorded as blocked: %d. Aging: %d. Changes since the previous digest: %s." % (len(by_status("in_progress")), len(blocked_ids), len(model["aging"]), len(model["changes"]) if previous else "not compared"),
           "- Not asserted: %d stale records, and %d gap entries in all (%d stale, %d missing, %d unsupported)." % (len(model["stale"]), len(model["gaps"]), kinds("STALE"), kinds("MISSING"), kinds("UNSUPPORTED")), "",
           "## The synchronization runs this digest was built from", "",
           "| Run | System | Result | Retrieved at | Age at this digest | Fresh records used | Items the run lists | Verdict |", "|---|---|---|---|---|---|---|---|"]
    for run in model["runs"]:
        verdict = "failed: nothing was retrieved. The run's record gives no reason" if run["result"] != "completed" else "fresh" if run["fresh"] else "STALE"
        out.append("| `%s` | %s | %s | %s | %s | %d | %d | %s |" % (run["run"] if RUN_NAME.match(run["run"]) else "unreadable", safe(run["system"], names), safe(run["result"], names), safe(run["retrieved_at"], names),
                                                              age_words(run["age"]) if run["age"] is not None else "not known", run["used"], len(run["items"]), verdict))
    named = sorted({str(e["p"].get("sync_run")) for i, e in items.items() if model["in_scope"](i)} - {r["run"] for r in model["runs"]})
    for run in named:
        out.append("| `%s` | | | | | 0 | | NOT IN sync-runs.md. Records that name it are not asserted |" % (run if RUN_NAME.match(run) else "unreadable"))
    out += ["", "## How to read this", "",
            "- **OBSERVED** lines say what one fresh record says. An OBSERVED · CHANGE line compares that record with the state the previous digest kept. An OBSERVED · AGING line applies the %d-day threshold to two times in the record. An OBSERVED · COUNT line counts the lines above it." % AGING_AFTER_DAYS,
            "- **INFERENCE** lines are the generator's own conclusions, drawn from more than one record by one of the rules I1 to I4. They are all in section 7 and nowhere else.",
            "- **LAST KNOWN** lines are from stale records. They are what the record said when retrieved, and are not claims about now.",
            "- Each line ends with the item's identity, when its record was retrieved, how long before this digest that was, and the run.",
            "- Titles and the bases a record gives are **other people's text**. They are printed so that an item can be recognised, between double quotes, with names, email addresses, customer numbers and telephone numbers taken out. **No rule reads their wording.** A title may be worded as an instruction or a status. It is neither.",
            "- **This digest makes no statement about any person**: not who is doing what, how hard, how well, or whether they are available. \"A person's note\" means a file in the notes folder. Who wrote it is not known here.", "",
            "## 1. OBSERVED: changes since the previous digest", ""]
    if previous is None:
        out += ["Not compared. See the gap report.", ""]
    elif not model["changes"]:
        out += ["None that this digest can assert: the same identities, and no status change between two asserted statuses.", ""]
    for kind, identity, what in model["changes"]:
        if kind == "REMOVED":
            out.append("- [OBSERVED · CHANGE · REMOVED] `%s`: %s. Why is not recorded: see the gap report. Rests on the previous digest's state, where its record was retrieved %s. There is no record now to cite." % (identity, what, safe(previous["items"][identity].get("retrieved_at"), [])))
        else:
            out.append("- [OBSERVED · CHANGE · %s] %s; %s. %s." % (kind, what[0].upper() + what[1:], title_of(model, identity), cite(model, identity)))
    out += ["", "## 2. OBSERVED: in progress", ""]
    out += ["- [OBSERVED] In progress, stated by the source; %s. %s." % (title_of(model, i), cite(model, i)) for i in by_status("in_progress")] or ["None stated."]
    out += ["", "## 3. OBSERVED: blocked and blocking", "",
            "From the record's `blocked` field, from links saved with the record, and from lines of the form `- blocked_by: ID` in a person's note. Nothing else. An item can be in progress and blocked at once: both are what its record says.", ""]
    out += ["- [OBSERVED · BLOCKED] %s; %s. %s." % (why[0].upper() + why[1:], title_of(model, i), cite(model, i)) for i, why in model["blocked"]] or ["Nothing is recorded as blocked."]
    out += ["- [OBSERVED · BLOCKING] Recorded as blocking `%s`, in %s; %s. %s." % (other, where, title_of(model, i), cite(model, i)) for i, other, where in model["blocking"]]
    out += ["", "## 4. OBSERVED: aging", "",
            "Counted to the time each record was retrieved, not to the time of this digest: nothing here says what happened after retrieval.", ""]
    out += ["- [OBSERVED · AGING] In progress, and when retrieved its source had not changed for %d days (last change %s); %s. %s." % (days, changed, title_of(model, i), cite(model, i)) for i, days, changed in model["aging"]] or ["Nothing in progress had been unchanged for %d days or more when retrieved." % AGING_AFTER_DAYS]
    out += ["", "## 5. OBSERVED: done, closed, and open", ""]
    for status in ("done", "dropped", "open"):
        out += ["- [OBSERVED] %s, stated by the source; %s. %s." % (STATUS_WORDS[status][0].upper() + STATUS_WORDS[status][1:], title_of(model, i), cite(model, i)) for i in by_status(status)]
    out += ["", "## 6. OBSERVED: counts of the lines above", "",
            "- [OBSERVED · COUNT] Items with a fresh record whose status the source states: %d. In progress: %d. Open: %d. Done: %d. Closed without being done: %d."
            % (len(stated), len(by_status("in_progress")), len(by_status("open")), len(by_status("done")), len(by_status("dropped"))),
            "- [OBSERVED · COUNT] Work in progress: %d. They are: %s." % (len(by_status("in_progress")), ", ".join("`%s`" % i for i in by_status("in_progress")) or "none"),
            "- [OBSERVED · COUNT] Recorded as blocked: %d. They are: %s. Aging: %d." % (len(blocked_ids), ", ".join("`%s`" % i for i in blocked_ids) or "none", len(model["aging"])),
            "- [OBSERVED · COUNT] Not counted above, because this digest does not assert them: stale records, %d (%s); fresh records whose status the source does not state, %d. Items with no readable record are in the gap report and are in no count."
            % (len(model["stale"]), ", ".join("`%s`" % i for i in sorted(model["stale"])) or "none", len(model["fresh"]) - len(stated)), "",
            "## 7. INFERENCE: the generator's own conclusions", "",
            "**These are not observations.** Each is drawn by one of the rules I1 to I4 in the skill, from more than one record, and names every record it rests on.",
            "I1: waiting on a blocker that is not done. I2: every recorded blocker is done, which does not mean free. I3: waiting on a blocker this digest cannot see. I4: a count of I1 and I3.", ""]
    for rule, text, cites in model["inferences"]:
        out.append("- [INFERENCE %s] %s Rests on: %s." % (rule, text, "; ".join(cite(model, i) for i in cites)))
    out += ["- [INFERENCE I4] Items waiting on something that is not done, or that this digest cannot see: %d (%s). Recorded as blocked with no blocker named, and so in neither I1 nor I3: %d (%s). Rests on the I1 and I3 lines above and on section 3."
            % (len(model["waiting"]), ", ".join("`%s`" % i for i in model["waiting"]) or "none", len(model["no_blocker_named"]), ", ".join("`%s`" % i for i in model["no_blocker_named"]) or "none"), "",
            "## 8. Status the source does not state", "",
            "The record's `status_basis` is not `stated`. These are not counted as observed.", ""]
    unstated = [i for i in sorted(model["fresh"]) if i not in stated]
    out += ["- [NOT STATED] Its record gives the status %s, with the basis `%s`. The record's own account: \"%s\"; %s. %s."
            % (SHORT[items[i]["c"]["status"]], items[i]["c"]["status_basis"], safe(items[i]["c"]["status_source"], names), title_of(model, i), cite(model, i)) for i in unstated] or ["None."]
    out += ["", "## 9. LAST KNOWN, NOT CURRENT: stale records", "",
            "**None of this is a claim about now.** Why each is stale is in the gap report.", ""]
    for identity in sorted(model["stale"]):
        entry = items[identity]
        if entry["age"] is None:
            out.append("- [LAST KNOWN] `%s`: when it was retrieved cannot be read, so nothing of it is stated." % identity)
        else:
            out.append("- [LAST KNOWN] When retrieved, its record gave the status %s (basis `%s`) and `blocked` as %s; %s. %s."
                       % (SHORT[entry["c"]["status"]], entry["c"]["status_basis"], entry["c"]["blocked"], title_of(model, identity), cite(model, identity)))
    if not model["stale"]:
        out.append("None.")
    out += ["", "## 10. What this digest does not say", "",
            "`standup-gaps.md` lists each of these with its reason: %d stale, %d missing, %d unsupported." % (kinds("STALE"), kinds("MISSING"), kinds("UNSUPPORTED")),
            "An item that is absent from this digest is absent because nothing fresh and stated supports a statement about it. Its absence says nothing about the item, and nothing about anyone.",
            "The state kept for the next digest holds each item's status and nothing of whether it was blocked, so a change in that is not reported.", ""]
    return "\n".join(out)


def render_gaps(model):
    out = ["# Gap report for the stand-up digest of %s" % model["as_of"], "",
           "What `standup-digest.md` does not assert, and why. Written by `participant/skills/scrum-standup-digest/digest.py` from the same local context.", "",
           "- **STALE**: the record is older than %d hours, or cannot be shown to be fresh." % STALE_AFTER_HOURS,
           "- **MISSING**: something refers to it and there is no local record of it, or its record cannot be read.",
           "- **UNSUPPORTED**: there is a record, and it does not support the statement a digest would want to make.", "",
           "A gap is not a finding about the work or about a person. It says the local context cannot support a claim.",
           "An entry may be about one item, several items named together, a file, or a whole system. So the number of entries is not a number of items.", ""]
    for kind in ("STALE", "MISSING", "UNSUPPORTED"):
        mine = [g for g in model["gaps"] if g["kind"] == kind]
        out += ["## %s: %d" % (kind, len(mine)), ""]
        out += ["- [%s] %s. Reason: %s. Not asserted: %s." % (kind, g["what"] if g["what"].startswith(("the whole", "changes since")) else "`%s`" % "`, `".join(g["what"].split(", ")), g["reason"], g["unsaid"]) for g in mine] or ["None."]
        out += [""]
    return "\n".join(out)


def render_state(model):
    items = {i: {"status": e["c"]["status"], "asserted": i in model["stated"], "retrieved_at": e["p"].get("retrieved_at")} for i, e in sorted(model["items"].items()) if model["in_scope"](i)}
    return json.dumps({"as_of": model["as_of"], "scope": model["scope"], "items": items}, indent=2, sort_keys=True) + "\n"


def generate(context, as_of, previous_path, out, scope="all"):
    if time_of(as_of) is None:
        raise SystemExit("--as-of must be a time in UTC written like 2026-11-24T09:00:00Z.")
    previous = None
    if previous_path not in (None, "none"):
        if os.path.abspath(previous_path) == os.path.abspath(os.path.join(out, "digest-state.json")):
            raise SystemExit("--previous is the state file this run would write. Keep the previous digest's state somewhere else, or a second run will not see what the first saw.")
        previous = json.loads(read(previous_path))
        if not isinstance(previous.get("items"), dict) or time_of(previous.get("as_of")) is None:
            raise SystemExit("--previous is not a digest state: it has no items, or no time it was for.")
    model = build(context, as_of, previous, scope)
    os.makedirs(out, exist_ok=True)
    written = {"standup-digest.md": render_digest(model), "standup-gaps.md": render_gaps(model), "digest-state.json": render_state(model)}
    for name, text in written.items():
        write(os.path.join(out, name), text)
    return model, written


def check(context, as_of, out, scope="all"):
    """Reads the finished digest and gap report and compares them with the context. Returns a sorted list of problems."""
    problems = set()
    say = problems.add
    data = load(context)
    items = data["items"]
    digest, gaps = read(os.path.join(out, "standup-digest.md")), read(os.path.join(out, "standup-gaps.md"))
    now = time_of(as_of)
    completed = {r["run"]: r for r in data["runs"] if r["result"] == "completed"}
    wanted = lambda i: scope == "all" or items[i]["c"].get("assigned_to_me") == "yes"  # noqa: E731
    stale = set()
    for identity, entry in items.items():
        at = time_of(entry["p"].get("retrieved_at"))
        run = completed.get(entry["p"].get("sync_run"))
        if at is None or not 0 <= (now - at).total_seconds() <= STALE_AFTER_HOURS * 3600 or run is None or run["retrieved_at"] != entry["p"].get("retrieved_at"):
            stale.add(identity)
    found = re.findall(r"^## (\d+)\. [^\n]*\n(.*?)(?=^## |\Z)", digest, re.S | re.M)
    if len({number for number, _ in found}) != len(found):
        say("The digest has two sections with the same number.")
    sections = dict(found)
    for number, body in found:
        for line in [each for each in body.split("\n") if each.startswith("- ")]:
            tag = re.match(r"- \[([A-Z ]+)", line)
            if not tag:
                say("A line of section %s has no label: %s" % (number, line[:70]))
                continue
            tag = tag.group(1).strip()
            cited = re.findall(r"`((?:jira|github|trello):[A-Za-z0-9_.-]+)`, retrieved (\S+) \(([^)]*) before this digest\), run `([^`]*)`", line)
            exempt = "· COUNT]" in line or "· REMOVED]" in line or line.startswith("- [INFERENCE I4]")
            if not cited and not exempt:
                say("A line of section %s cites no item with its retrieval time: %s" % (number, line[:80]))
            for identity, retrieved, age, run in cited:
                if identity not in items:
                    say("Section %s cites %s, of which there is no local record." % (number, identity))
                    continue
                p = items[identity]["p"]
                at = time_of(p.get("retrieved_at"))
                if p.get("retrieved_at") != retrieved:
                    say("Section %s gives %s the retrieval time %s, and its record says %s." % (number, identity, retrieved, p.get("retrieved_at")))
                elif at is not None and age != age_words((now - at).total_seconds()):
                    say("Section %s gives %s the age \"%s\", and by its retrieval time it is \"%s\"." % (number, identity, age, age_words((now - at).total_seconds())))
                if p.get("sync_run") != run:
                    say("Section %s gives %s the run %s, and its record says %s." % (number, identity, run, p.get("sync_run")))
                if identity in stale and (tag != "LAST KNOWN" or number != "9"):
                    say("Section %s states something of %s as current, and its record is stale." % (number, identity))
            if cited and number in ("2", "5") and tag == "OBSERVED":
                c = items.get(cited[0][0], {}).get("c")
                word = line.split(",")[0][len("- [OBSERVED] "):].lower()
                if c and (c["status_basis"] != "stated" or not STATUS_WORDS[c["status"]].lower().startswith(word.split(",")[0])):
                    say("Section %s says %s is \"%s\", and its record says %s, %s." % (number, cited[0][0], word, c["status"], c["status_basis"]))
            if cited and "· AGING]" in line:
                c, p = items.get(cited[0][0], {}).get("c"), items.get(cited[0][0], {}).get("p")
                days = re.search(r"had not changed for (\d+) days", line)
                real = int((time_of(p["retrieved_at"]) - time_of(c["source_updated_at"])).total_seconds() // 86400) if c and time_of(c["source_updated_at"]) and time_of(p["retrieved_at"]) else None
                if not days or real is None or int(days.group(1)) != real or real < AGING_AFTER_DAYS or c["status"] != "in_progress":
                    say("Section %s says %s is aging, and by its record it is not, or not by that number of days." % (number, cited[0][0]))
            if (number == "7") != line.startswith("- [INFERENCE"):
                say("An inference is outside section 7, or a line in section 7 is not labelled as inference: %s" % line[:70])
    for identity in sorted(items):
        if not wanted(identity):
            continue
        c = items[identity]["c"]
        links = links_of(identity, items[identity], data["notes"], data["note_files"])
        recorded = c["blocked"] == "yes" or any(kind == "blocked_by" for kind, _, _ in links)
        shown = bool(re.search(r"^- \[OBSERVED · BLOCKED\][^\n]*`%s`, retrieved" % re.escape(identity), sections.get("3", ""), re.M))
        if shown and not recorded:
            say("%s is shown as blocked, and no recorded field, link or note says so." % identity)
        if recorded and not shown and identity not in stale:
            say("%s is recorded as blocked and is not shown as blocked." % identity)
        if identity in stale and not re.search(r"^- \[STALE\] `%s`" % re.escape(identity), gaps, re.M):
            say("%s is stale and is not in the gap report as stale." % identity)
        if identity not in stale and "`%s`, retrieved" % identity not in sections.get("2", "") + sections.get("5", "") + sections.get("8", ""):
            say("%s has a fresh record and its status is in none of sections 2, 5 and 8." % identity)
    progress = len(re.findall(r"^- \[OBSERVED\]", sections.get("2", ""), re.M))
    said = re.search(r"Work in progress: (\d+)\.", sections.get("6", ""))
    if not said or int(said.group(1)) != progress:
        say("Section 6 gives a count of work in progress that is not the number of lines in section 2.")
    entries = len(re.findall(r"^- \[(?:STALE|MISSING|UNSUPPORTED)\] ", gaps, re.M))
    said = re.search(r"It has (\d+) entries", digest)
    if not said or int(said.group(1)) != entries:
        say("The digest says the gap report has a number of entries that it does not have.")
    quiet = re.sub(r"`[^`\n]*`", "", digest + gaps)
    for name in data["names"]:
        if re.search(r"(?<!\w)%s(?!\w)" % re.escape(name), quiet, re.I):
            say("The name \"%s\", which redaction.md lists, is in the digest or the gap report." % name)
    for word, shape in SHAPES:
        if shape.search(re.sub(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", "", quiet)):
            say("The digest or the gap report holds something with the shape of %s." % word[1:-1])
    for field in ("assignee", "assigned to "):
        if field in quiet.lower():
            say("The digest or the gap report uses the word \"%s\", and it is to make no statement about a person." % field.strip())
    if not re.search(r"^- Window: ", digest, re.M) or "## The synchronization runs this digest was built from" not in digest or any("`%s`" % r["run"] not in digest for r in data["runs"] if RUN_NAME.match(r["run"])):
        say("The digest does not state its window, or does not list every run in sync-runs.md.")
    return sorted(problems)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate or check a stand-up digest from local context.")
    parser.add_argument("command", choices=["generate", "check"])
    parser.add_argument("--context", required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--previous", default="none")
    parser.add_argument("--out", required=True)
    parser.add_argument("--scope", choices=["all", "mine"], default="all")
    args = parser.parse_args(argv)
    if args.command == "generate":
        model, written = generate(args.context, args.as_of, args.previous, args.out, args.scope)
        for name in written:
            with open(os.path.join(args.out, name), "rb") as f:
                print("wrote %-18s sha256 %s" % (name, hashlib.sha256(f.read()).hexdigest()))
        print("%d records read. %d fresh, %d stale. %d gap entries. No source system was contacted." % (len(model["items"]), len(model["fresh"]), len(model["stale"]), len(model["gaps"])))
        return 0
    problems = check(args.context, args.as_of, args.out, args.scope)
    for problem in problems:
        print("PROBLEM: %s" % problem)
    print("CHECK FAILED. %d problems." % len(problems) if problems else
          "CHECK PASSED. None of the things this check looks for was found. What it looks for, and what it does not, is in SKILL.md.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
