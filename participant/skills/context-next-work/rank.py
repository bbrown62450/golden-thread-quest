#!/usr/bin/env python3
"""Ranks what to work on next from local records, with a cited reason for every place. Local files only.

    python3 participant/skills/context-next-work/rank.py rank [--inputs FILE] [--out FILE] [--now TIME] [--rule NAME]
    python3 participant/skills/context-next-work/rank.py rules

rank   reads the records in inputs.md and writes recommendation.md. It prints the ranking.
rules  writes rules.md.

It gives advice. It never starts, assigns or changes any work, and it never writes to the inputs. It contacts
nothing. It does not read the computer's clock: the clock value comes from the inputs file or from --now.
"""
import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
FOLDER = os.path.join(REPO, "participant", "context", "next-work")
POLICY = os.path.join(REPO, "participant", "context", "freshness", "policy.md")

IDENTITY = re.compile(r"^(jira|trello|github|decision):[A-Za-z0-9_\-=+/.]+$")
PRIORITIES = ["high", "medium", "low"]
# The criteria, in order, for each rule. The first one on which two items differ decides between them.
RULES = {"priority-first": ["priority", "due", "waiters", "created", "identity"],
         "due-first": ["due", "priority", "waiters", "created", "identity"]}
CRITERIA = {"priority": ("Priority, highest first", "`priority`", "high, then medium, then low"),
            "due": ("Due date, soonest first", "`due`", "the earlier date"),
            "waiters": ("Open items waiting on it, most first", "`blocks` on the item, and `blocked_by` on the items that name it", "the larger number"),
            "created": ("Created, oldest first", "`created`", "the earlier date"),
            "identity": ("Identity, as the last tie-break", "`identity`", "the one that sorts first as text")}
CONFIDENCE = ["high", "medium", "low"]
NOT_USED = ("votes",)


class InputError(Exception):
    pass


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def moment(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", value):
        return None
    try:
        return datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None


def day(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d\d-\d\d", value):
        return None
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        return None


def limits(policy_text):
    """The freshness limits, in hours, from the approved freshness policy."""
    out = {}
    for kind, number, unit in re.findall(r"^\| `([\w-]+)` \| (\d+) (hours|days) \|", policy_text, re.M):
        out[kind] = int(number) * (24 if unit == "days" else 1)
    if "work-item-status" not in out or "decision" not in out:
        raise InputError("The freshness policy does not give a limit for work items and for decisions.")
    return out


def read_inputs(text):
    """Returns (records, clock value or None)."""
    records = {}
    for heading, body in re.findall(r"^### (\S+)\n+```json\n(.*?)\n```", text, re.M | re.S):
        try:
            record = json.loads(body)
        except ValueError as error:
            raise InputError("The record under %s is not valid JSON: %s" % (heading, error))
        if not isinstance(record, dict) or record.get("identity") != heading or not IDENTITY.match(heading):
            raise InputError("The record under %s does not carry that identity, or it is not an identity." % heading)
        if heading in records:
            raise InputError("Two records have the identity %s. Which one is meant cannot be told." % heading)
        if record.get("kind") not in ("work", "decision"):
            raise InputError("%s has no kind, or a kind that is neither work nor decision." % heading)
        records[heading] = record
    if not records:
        raise InputError("No records could be read.")
    clock = re.search(r"^- clock: `(\S+)`$", text, re.M)
    return records, clock.group(1) if clock else None


# ---------------------------------------------------------------- the ranking

def analyse(records, now_text, hours, rule="priority-first"):
    """Everything the recommendation says, as plain data. Nothing here reads a clock or depends on input order."""
    now = moment(now_text)
    if now is None:
        raise InputError("The clock value \"%s\" is not a time in UTC written like 2026-12-01T09:00:00Z." % now_text)
    if rule not in RULES:
        raise InputError("There is no rule called \"%s\"." % rule)

    def age(identity):
        """(stale, words) for a record's local copy."""
        record = records[identity]
        limit = hours["decision" if record["kind"] == "decision" else "work-item-status"]
        got = moment(record.get("retrieved_at"))
        if "retrieved_at" not in record:
            return True, "`retrieved_at` is not recorded, so the copy cannot be shown to be fresh"
        if got is None:
            return True, "`retrieved_at` is `%s`, which is not a time, so the copy cannot be shown to be fresh" % json.dumps(record["retrieved_at"])
        if got > now:
            return True, "`retrieved_at` is `%s`, later than the clock value, so the copy cannot be shown to be fresh" % record["retrieved_at"]
        old = (now - got).total_seconds() / 3600.0
        words = "%d days" % (old // 24) if old >= 48 else "%d hours" % old
        if old > limit:
            return True, "`retrieved_at` is `%s`, %s before the clock value. The limit is %d hours" % (record["retrieved_at"], words, limit)
        return False, "`retrieved_at` is `%s`, %s before the clock value" % (record["retrieved_at"], words)

    def finished(identity):
        record = records.get(identity)
        return record is not None and record.get("status") == ("decided" if record["kind"] == "decision" else "done")

    # Links, from the three fields that record one. A link is (waiter, target, field, record the field is on).
    links, unreadable = [], {}
    for identity in sorted(records):
        for field in ("blocked_by", "needs_decision", "blocks"):
            value = records[identity].get(field, [])
            for named in value if isinstance(value, list) else [value]:
                if not isinstance(named, str) or not IDENTITY.match(named):
                    unreadable.setdefault(identity, []).append("`%s` holds %s, which is not an identity. Nothing was guessed from it" % (field, json.dumps(named)))
                elif field == "blocks":
                    links.append((named, identity, field, identity))
                else:
                    links.append((identity, named, field, identity))

    items = {}
    for identity in sorted(records):
        record = records[identity]
        if record["kind"] != "work":
            continue
        stale, age_words = age(identity)
        item = {"identity": identity, "title": str(record.get("title", "")), "stale": stale, "age": age_words,
                "warnings": [], "reasons": [], "missing": [], "blockers": [], "votes": record.get("votes")}
        item["warnings"] += unreadable.get(identity, [])
        # Not offered: finished, under way, or somebody has it.
        status = record.get("status")
        if status != "open":
            item["list"], item["why"] = "not offered", "`status` is %s" % ("`%s`" % status if isinstance(status, str) else "not recorded")
        elif record.get("assigned_to"):
            item["list"], item["why"] = "not offered", "`assigned_to` is `%s`" % record["assigned_to"]
        else:
            for waiter, target, field, on in links:
                if waiter == identity and not finished(target):
                    if target not in records:
                        state = "has no record, so it cannot be shown to be finished"
                    else:
                        state = "is %s `%s`" % ("a decision whose `status` is" if records[target]["kind"] == "decision" else "a work item whose `status` is", records[target].get("status"))
                        target_stale, target_age = age(target)
                        if target_stale:
                            state += ". Its own copy is stale (%s), so this item may no longer be blocked" % target_age
                    known = next((b for b in item["blockers"] if b["identity"] == target), None)
                    if known is None:
                        item["blockers"].append({"identity": target, "state": state, "sources": ["`%s` on `%s`" % (field, on)]})
                    elif "`%s` on `%s`" % (field, on) not in known["sources"]:
                        known["sources"].append("`%s` on `%s`" % (field, on))
            item["list"] = "blocked" if item["blockers"] else "ranked"
        # The values the criteria read, whichever list the item is on.
        priority = record.get("priority")
        if priority in PRIORITIES:
            item["priority"] = PRIORITIES.index(priority)
            item["reasons"].append(("priority", "`priority` is `%s`" % priority))
        else:
            item["priority"] = len(PRIORITIES)
            item["missing"].append("priority")
            item["reasons"].append(("priority", "`priority` is %s. It is placed after every item that has one" % (
                "not recorded" if "priority" not in record else "`%s`, which is not high, medium or low" % json.dumps(priority))))
        for field, far in (("due", datetime.date.max), ("created", datetime.date.max)):
            got = day(record.get(field))
            item[field] = got or far
            if got is None:
                item["missing"].append(field)
                item["reasons"].append((field, "`%s` is %s. It is placed after every item that has one" % (
                    field, "not recorded" if field not in record else "`%s`, which is not a date" % json.dumps(record[field]))))
            elif field == "due":
                gap = (got - now.date()).days
                when = "the day of the clock value" if gap == 0 else "%d day%s %s the clock value%s" % (abs(gap), "" if abs(gap) == 1 else "s", "after" if gap > 0 else "before", "" if gap > 0 else ": overdue")
                item["reasons"].append((field, "`due` is `%s`, %s" % (record[field], when)))
            else:
                item["reasons"].append((field, "`created` is `%s`" % record[field]))
        waiting = {}
        for waiter, target, field, on in links:
            if target == identity and waiter in records and records[waiter].get("status") in ("open", "in_progress"):
                waiting.setdefault(waiter, []).append("`%s` on `%s`" % (field, on))
        item["waiters"] = len(waiting)
        item["reasons"].append(("waiters", "%d open item%s wait%s on it%s" % (
            len(waiting), "" if len(waiting) == 1 else "s", "s" if len(waiting) == 1 else "",
            ": " + "; ".join("`%s` (%s)" % (w, ", ".join(sorted(set(src)))) for w, src in sorted(waiting.items())) if waiting else
            ". `blocks` names none, and no open item's `blocked_by` names it")))
        item["reasons"].sort(key=lambda reason: RULES[rule].index(reason[0]))
        if stale:
            item["warnings"].insert(0, "STALE CONTEXT: %s. Its status, its blockers and who has it may have changed. Refresh it before relying on this" % age_words)
        drops = len(item["missing"]) + (1 if stale else 0) + (1 if unreadable.get(identity) else 0)
        item["confidence"] = CONFIDENCE[min(drops, len(CONFIDENCE) - 1)]
        item["confidence_why"] = (["`%s` is missing" % f for f in item["missing"]] + (["the copy is stale"] if stale else [])
                                  + (["a link could not be read"] if unreadable.get(identity) else [])) or ["every field the ranking reads is recorded, and the copy is fresh"]
        items[identity] = item

    def key(item):
        values = {"priority": item["priority"], "due": item["due"], "waiters": -item["waiters"], "created": item["created"], "identity": item["identity"]}
        return tuple(values[c] for c in RULES[rule])

    def decided(a, b):
        """The first criterion on which a and b differ, in the rule's order."""
        return next(c for c, x, y in zip(RULES[rule], key(a), key(b)) if x != y)

    ranked = sorted((i for i in items.values() if i["list"] == "ranked"), key=key)
    for place, item in enumerate(ranked, 1):
        item["place"] = place
        if place > 1:
            above = ranked[place - 2]
            item["below"] = (above["identity"], decided(above, item))
            item["not_first"] = (ranked[0]["identity"], decided(ranked[0], item))
    pick = next((i for i in ranked if not i["stale"]), None)
    return {"now": now_text, "rule": rule, "limit": hours["work-item-status"], "items": items, "ranked": ranked,
            "blocked": sorted((i for i in items.values() if i["list"] == "blocked"), key=key),
            "not_offered": sorted((i for i in items.values() if i["list"] == "not offered"), key=lambda i: i["identity"]),
            "pick": pick, "records": records}


def value_of(found, item, criterion):
    """The reason text of one criterion for one item."""
    return next(text for c, text in item["reasons"] if c == criterion) if criterion != "identity" else "`identity` is `%s`" % item["identity"]


def lines(found):
    """The ranking as short lines, for printing and for comparing two runs."""
    out = ["Clock value: %s. Rule: %s. A work item's copy is stale after %d hours." % (found["now"], found["rule"], found["limit"])]
    for item in found["ranked"]:
        out.append("  %2d. %-32s confidence %-6s %s" % (item["place"], item["identity"], item["confidence"], "STALE" if item["stale"] else ""))
    for item in found["blocked"]:
        out.append("  blocked      %-28s by %s" % (item["identity"], ", ".join(b["identity"] for b in item["blockers"])))
    for item in found["not_offered"]:
        out.append("  not offered  %-28s %s" % (item["identity"], item["why"]))
    pick = found["pick"]
    out.append("Start here: %s" % ("%s, place %d" % (pick["identity"], pick["place"]) if pick else "nothing. No ranked item has fresh context."))
    return [line.rstrip() for line in out]


def changes(before, after):
    """Why each item's place or list differs between two runs."""
    out = []
    fields = []
    for identity in sorted(set(before["records"]) | set(after["records"])):
        a, b = before["records"].get(identity, {}), after["records"].get(identity, {})
        for field in sorted(set(a) | set(b)):
            if a.get(field) != b.get(field):
                fields.append("`%s` of `%s`: %s -> %s" % (field, identity, json.dumps(a.get(field)), json.dumps(b.get(field))))
    out.append("Fields that differ between the two inputs: %s" % ("; ".join(fields) or "none"))

    def where(found, identity):
        item = found["items"].get(identity)
        if item is None:
            return "absent"
        return "place %d" % item["place"] if item["list"] == "ranked" else item["list"]
    for identity in sorted(set(before["items"]) | set(after["items"])):
        was, now = where(before, identity), where(after, identity)
        if was == now:
            continue
        item = after["items"].get(identity) or before["items"][identity]
        if was == "blocked" and now.startswith("place"):
            gone = [b["identity"] for b in before["items"][identity]["blockers"]]
            why = "it was blocked by %s, and %s finished in the second input" % (", ".join(gone), "that is" if len(gone) == 1 else "those are")
        elif now == "not offered":
            why = "in the second input its %s" % item["why"]
        elif now == "blocked":
            why = "in the second input it is blocked by %s" % ", ".join(b["identity"] for b in item["blockers"])
        else:
            entered = sorted(i for i in after["items"] if where(after, i).startswith("place") and not where(before, i).startswith("place") and after["items"][i]["place"] < item["place"])
            left = sorted(i for i in before["items"] if where(before, i).startswith("place") and not where(after, i).startswith("place") and before["items"][i]["place"] < before["items"][identity]["place"])
            why = "its own fields are unchanged. Above it, %s" % "; ".join(
                (["%s left the ranking" % ", ".join(left)] if left else []) + (["%s entered it" % ", ".join(entered)] if entered else [])) if (left or entered) else "its own fields changed"
        out.append("  %-32s %-12s -> %-12s because %s." % (identity, was, now, why))
    if before["pick"] is not after["pick"] and (before["pick"] or {}).get("identity") != (after["pick"] or {}).get("identity"):
        out.append("Start here: %s -> %s." % ((before["pick"] or {}).get("identity", "nothing"), (after["pick"] or {}).get("identity", "nothing")))
    return out


# ---------------------------------------------------------------- writing

def render(found):
    records = found["records"]

    def name(identity):
        return "`%s` %s" % (identity, "\"%s\"" % str(records[identity].get("title", "")).replace("|", "/") if identity in records else "(no record)")
    rule, ranked, pick = found["rule"], found["ranked"], found["pick"]
    out = ["# What to work on next", "",
           "Written by `participant/skills/context-next-work/rank.py rank` from `inputs.md`. Do not edit it: run it again. The",
           "data is made up.", "",
           "**This is advice.** Nothing here was started, assigned or changed, and no record was written to.", "",
           "- Clock value: `%s`, from the inputs. The computer's clock was not read." % found["now"],
           "- Rule: `%s`. The criteria, in order: %s. The first one on which two items differ decides between them." % (rule, ", ".join(RULES[rule])),
           "- A work item's local copy is stale when it was retrieved more than %d hours before the clock value. That limit is" % found["limit"],
           "  read from `participant/context/freshness/policy.md`.",
           "- Records: %d work items. Ranked: %d. Blocked: %d. Not offered: %d." % (len(found["items"]), len(ranked), len(found["blocked"]), len(found["not_offered"])), "",
           "## Start here", ""]
    if pick is None:
        out += ["**Nothing can be recommended.** No ranked item has fresh context. Refresh the records and run this again."]
    else:
        out += ["**%s**, place %d, confidence %s." % (name(pick["identity"]), pick["place"], pick["confidence"]), ""]
        ahead = [i for i in ranked if i["place"] < pick["place"]]
        if ahead:
            out += ["It is not first on the recorded fields. Ranked above it, and not to be started without a refresh:", ""]
            out += ["- %s, place %d. %s." % (name(i["identity"]), i["place"], i["warnings"][0]) for i in ahead] + [""]
        out += ["Why this one: %s." % "; ".join(text for _, text in pick["reasons"])]
    out += ["", "## Ranked", "",
            "Open, not blocked, and nobody has it. A stale item keeps the place its recorded fields give it, with a warning.", "",
            "| Place | Item | Confidence | Warning |", "|---|---|---|---|"]
    out += ["| %d | %s | %s | %s |" % (i["place"], name(i["identity"]), i["confidence"], "STALE" if i["stale"] else "-") for i in ranked]
    for item in ranked:
        out += ["", "### %d. %s" % (item["place"], name(item["identity"])), ""]
        out += ["- Reason, %s: %s." % (criterion, text) for criterion, text in item["reasons"]]
        if item["place"] > 1:
            above, criterion = item["below"]
            out += ["- Placed below `%s` by %s: %s, and for `%s` %s." % (above, criterion, value_of(found, item, criterion), above, value_of(found, found["items"][above], criterion))]
            first, criterion = item["not_first"]
            if first != above:
                out += ["- Why it is not first: %s decides against `%s`. %s, and for `%s` %s." % (criterion, first, value_of(found, item, criterion), first, value_of(found, found["items"][first], criterion))]
        else:
            out += ["- It is first because no other ranked item comes before it on %s." % ", then ".join(RULES[rule][:-1])]
        out += ["- Confidence: %s, because %s." % (item["confidence"], "; ".join(item["confidence_why"]))]
        out += ["- WARNING: %s." % w for w in item["warnings"]]
        out += ["- Not used: `votes` is %s." % json.dumps(item["votes"])]
    out += ["", "## Not recommended: blocked", "",
            "Each of these waits on something that is not finished. They are not ranked, because an order among blocked items",
            "says nothing about what can be done now. They are listed in the order the rule would give them.", ""]
    for item in found["blocked"]:
        out += ["### %s" % name(item["identity"]), ""]
        out += ["- BLOCKED BY %s, which %s. Recorded in %s." % (name(b["identity"]), b["state"], " and ".join(sorted(b["sources"]))) for b in item["blockers"]]
        out += ["- If unblocked, it would be ranked on: %s." % "; ".join(text for _, text in item["reasons"])]
        out += ["- Confidence: %s, because %s." % (item["confidence"], "; ".join(item["confidence_why"]))]
        out += ["- WARNING: %s." % w for w in item["warnings"]]
        out += ["- Not used: `votes` is %s." % json.dumps(item["votes"]), ""]
    if not found["blocked"]:
        out += ["None.", ""]
    out += ["## Not offered", "", "Finished, under way, or somebody already has it.", ""]
    out += ["- %s: %s.%s" % (name(i["identity"]), i["why"], " WARNING: %s." % i["warnings"][0] if i["warnings"] else "") for i in found["not_offered"]] or ["None."]
    voted = sorted((i for i in found["items"].values() if isinstance(i["votes"], int)), key=lambda i: (-i["votes"], i["identity"]))
    out += ["", "## Seen and not used: votes", "",
            "`votes` is recorded and plays no part in the ranking. Popularity is not priority. The five items with the most",
            "votes, and where each one is:", "",
            "| Votes | Item | Where it is |", "|---|---|---|"]
    out += ["| %d | %s | %s |" % (i["votes"], name(i["identity"]), "place %d" % i["place"] if i["list"] == "ranked" else
                                 "blocked by %s%s" % (", ".join("`%s`" % b["identity"] for b in i["blockers"]), ", and its copy is stale" if i["stale"] else "") if i["list"] == "blocked" else "not offered")
            for i in voted[:5]]
    out += ["", "## To disagree with a place", "",
            "Each reason above names the field it came from. Change that field in the record and run the ranking again.", "",
            "| If you think | Change |", "|---|---|",
            "| it matters more or less than its place says | `priority` on the item |",
            "| it is more or less urgent | `due` on the item |",
            "| more or fewer things wait on it | `blocks` on the item, or `blocked_by` on the items that wait |",
            "| it is not really blocked | `blocked_by` or `needs_decision` on the item, or the `status` of what it waits on |",
            "| the copy is fine | fetch the record again, so that `retrieved_at` is new. Do not edit `retrieved_at` by hand |",
            "| the whole order is wrong | the rule. `--rule due-first` puts the due date before priority |"]
    return "\n".join(out) + "\n"


def rules_text(hours):
    out = ["# Ranking rules: what to work on next", "",
           "Written by `participant/skills/context-next-work/rank.py rules`, at the participant's direction, for the quest",
           "`context-next-work`. The tables below are the tables the program applies.", "",
           "The ranking gives advice. It never starts, assigns or changes work, and it never writes to a record.", "",
           "## 1. Which items are ranked", "",
           "Every work item goes on exactly one of three lists.", "",
           "| List | When | What is cited |", "|---|---|---|",
           "| **Not offered** | `status` is anything but `open`, or `assigned_to` holds a value | that field |",
           "| **Blocked** | it is open and unassigned, and something it waits on is not finished | the field that records the link, the record that field is on, and the blocker's `status` |",
           "| **Ranked** | everything else | one reason for each criterion |", "",
           "An item waits on whatever its own `blocked_by` or `needs_decision` names, and on any record whose `blocks` names it.",
           "A work item is finished when its `status` is `done`. A decision is finished when its `status` is `decided`. A blocker",
           "that has no record cannot be shown to be finished, so the item is blocked, and the blocker is named.", "",
           "Blocked items are not given a place. They are listed with the blocker named.", "",
           "## 2. The criteria, and their order", "",
           "The first criterion on which two items differ decides between them. Later criteria are not looked at.", "",
           "| Order | Criterion | Field it reads | Which comes first |", "|---|---|---|---|"]
    out += ["| %d | %s | %s | %s |" % (n, CRITERIA[c][0], CRITERIA[c][1], CRITERIA[c][2]) for n, c in enumerate(RULES["priority-first"], 1)]
    out += ["", "This is the rule `priority-first`, and it is the one the recommendation uses. A second rule, `due-first`, puts the due",
            "date before priority and leaves the rest as it is: %s." % ", ".join(RULES["due-first"]), "",
            "**No weights and no score.** A high-priority item due next month is above a low-priority item due tomorrow, every",
            "time. That is blunt on purpose: the reason for any place is one field, and a person can say which.", "",
            "## 3. Ties", "",
            "Two items level on one criterion go to the next. Identity is last and no two records share one, so no tie is left.", "",
            "## 4. Missing data", "",
            "- A value is **missing** when the field is not there, or holds something that cannot be read: a `priority` that is not",
            "  high, medium or low, or a `due` or `created` that is not a date written like 2026-12-03.",
            "- A missing value is **never filled in**. No default is assumed.",
            "- On that criterion the item is placed **after every item that has a value**.",
            "- Each missing value is **reported** in the item's reasons, and **lowers its confidence** one step.", "",
            "## 5. Confidence", "",
            "Confidence starts at high and falls one step, to medium and then to low, for each of these:", "",
            "- each of `priority`, `due` and `created` that is missing;",
            "- a stale copy;",
            "- a link on the item that could not be read.", "",
            "It does not go below low. Confidence does not change an item's place. It says how far the place can be relied on.", "",
            "## 6. Stale context", "",
            "- A work item's copy is stale when `retrieved_at` is more than **%d hours** before the clock value. A decision's is stale" % hours["work-item-status"],
            "  after %d hours. Both limits are read from `participant/context/freshness/policy.md`." % hours["decision"],
            "- A copy with no `retrieved_at`, one that cannot be read, or one later than the clock value cannot be shown to be",
            "  fresh, and is stale.",
            "- A stale item **keeps its place and carries a warning**. Its confidence is lowered.",
            "- **\"Start here\" is the first ranked item whose copy is fresh.** A stale item ranked above it is named, with its",
            "  warning. If no ranked item is fresh, nothing is recommended.",
            "- If a blocker's own copy is stale, the blocked item says that it may no longer be blocked.", "",
            "## 7. The clock", "",
            "The clock value is part of the input: a line `- clock:` in the inputs file, or `--now`. The computer's clock is never",
            "read. With no clock value, the ranking stops and writes nothing. So the same input gives the same ranking on any day.", "",
            "## 8. What is not used", "",
            "`votes` is recorded, shown beside each item and not used. Titles and descriptions are never read for a reason.", "",
            "## 9. What the ranking refuses", "",
            "It stops, and writes nothing, when: there is no clock value, or it is not a time; two records share an identity; a",
            "record is not valid JSON or does not carry the identity of its heading; no record can be read; the freshness policy",
            "cannot be read; or it is told to write over the inputs file."]
    return "\n".join(out) + "\n"


def main(argv=None, say=print):
    argv = sys.argv[1:] if argv is None else argv

    def option(flag, default):
        return argv[argv.index(flag) + 1] if flag in argv else default
    try:
        hours = limits(read(option("--policy", POLICY)))
    except (OSError, InputError):
        say("NOT RANKED. The freshness policy could not be read, so no limit for stale context is known.")
        return 2
    if argv[:1] == ["rules"]:
        with open(os.path.join(FOLDER, "rules.md"), "w", encoding="utf-8") as f:
            f.write(rules_text(hours))
        say("Wrote rules.md.")
        return 0
    if argv[:1] != ["rank"]:
        say(__doc__.strip())
        return 2
    inputs = option("--inputs", os.path.join(FOLDER, "inputs.md"))
    out = option("--out", os.path.join(os.path.dirname(os.path.abspath(inputs)), "recommendation.md"))
    try:
        records, clock = read_inputs(read(inputs))
        now = option("--now", clock)
        if now is None:
            raise InputError("No clock value was given. The computer's clock is not read. Put a line \"- clock:\" in the inputs, or give --now.")
        found = analyse(records, now, hours, option("--rule", "priority-first"))
    except OSError:
        say("NOT RANKED. The inputs file could not be read.")
        return 2
    except InputError as error:
        say("NOT RANKED. %s" % error)
        return 2
    if os.path.realpath(out) == os.path.realpath(inputs):
        say("NOT RANKED. Refused to write the recommendation over the inputs file.")
        return 2
    with open(out, "w", encoding="utf-8") as f:
        f.write(render(found))
    for line in lines(found):
        say(line)
    say("Wrote %s. Nothing was started, assigned or changed." % os.path.basename(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
