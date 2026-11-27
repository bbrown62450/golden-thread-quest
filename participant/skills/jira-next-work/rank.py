#!/usr/bin/env python3
"""Ranks the open items of a Jira project from LOCAL RECORDS, and writes a recommendation a person can argue with.

    rank.py rank  --records RECORDS.json --now TIME [--rule priority-first|due-first] [--also-rule RULE] [--out FILE]
    rank.py rules [--out FILE]
    rank.py diff  --before RECORDS.json --now-before TIME --after RECORDS.json --now-after TIME [--rule RULE]

IT GIVES ADVICE. It starts nothing, assigns nothing and changes nothing. It contacts nothing: this file imports no
network code. It reads one records file, written earlier by `sync.py copy`, and writes one file, the recommendation.

THE CLOCK IS AN INPUT. --now is required, as 2026-12-01T09:00:00Z. The computer's clock is never read, so the same
records and the same --now always give the same recommendation, byte for byte.

THE THREE LISTS. Every item in the records goes in exactly one.

    Not offered   its `status` is in Jira's "done" category, or its `assignee` is someone else
    Blocked       open, not someone else's, and a link says it "is blocked by" an item that is not done
    Ranked        everything else: open, unblocked, and unassigned or assigned to me

THE ORDER of the ranked list. The first criterion on which two items differ decides. No weights, no score.

    1  priority   `priority`, in the order the site itself lists its priorities. No priority: after all that have one
    2  due        `duedate`, earliest first. No due date: after all that have one
    3  waiters    how many open items this one blocks, most first. From `issuelinks`
    4  created    `created`, oldest first. No created date: after all that have one
    5  key        the item's `key`: project, then number, then the key as written. Keys are never equal, so this always decides

    --rule due-first puts criterion 2 before criterion 1. Nothing else changes.

BLOCKED. A link counts when its type is the one named "Blocks" and this item is the link's TARGET, which is how Jira
shows "is blocked by". BOTH ENDS ARE READ: the item's own record, and every other record whose links name it. The
two can disagree, because the two records were copied at different times. An item is blocked if EITHER end says so.
    The blocker's status has up to two copies as well: its own record, and what Jira showed of it inside the blocked
    item's record. If they agree, that is its status. If one says done and the other does not, the item is treated
    as STILL BLOCKED, the reason gives both with their times, and confidence falls. So does it when a blocker's
    status is recorded nowhere, when the blocker's own record is stale, or when the newer of two records no longer
    shows the link.
    If the site has no link type named "Blocks", nothing can be shown as blocked, and the recommendation says so at
    the top instead of saying "Blocked: none".

STALE. An item's copy is stale when `copied_at` is more than 24 hours before --now. That is the same limit as the
one for a work item's status in participant/context/freshness/policy.md. It is written here, not read from there. A stale item KEEPS the place its recorded fields give it,
and carries a warning: its status, its blockers and who has it may have changed. "Start here" is the first ranked
item whose copy is not stale. `copied_at` is a field of the local record, not of Jira, and is said to be.

MISSING FIELDS. A missing `priority`, `duedate` or `created` is never filled in. The item goes after every item
that has a value, the reason says so, and its confidence falls one step for each: high, medium, low. A stale copy
costs one step too. Confidence says how complete and how fresh the data is. It does not say the advice is good.

STARTED WORK IS NOT RANKED FIRST. `status` is not a criterion. An item that is assigned to me and in progress is
listed at the top, under "Already started by you", so that it is seen, and keeps the place the criteria give it.

A DUE DATE is a date with no time. It is compared with the UTC date of the clock value. Near midnight, for someone
in another time zone, "overdue" can be a day out.

TITLES ARE NEVER READ: the records hold none. Items are named by key.

Exit codes: 0 written; 2 nothing written (no clock value, records that cannot be read, a clock earlier than a copy).
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import sys

FORMAT = "jira-next-work/1"
LIMIT_HOURS = 24
POLICY = "participant/context/freshness/policy.md"
RULES = {"priority-first": ("priority", "due", "waiters", "created", "key"), "due-first": ("due", "priority", "waiters", "created", "key")}
FIELD_OF = {"priority": "priority", "due": "duedate", "waiters": "issuelinks", "created": "created", "key": "key"}
LEVELS = ("high", "medium", "low")
REF = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,30}-[0-9]{1,9}")
NAME = re.compile(r"[A-Za-z0-9 ._/()'?-]{1,40}")       # a name the site chose, as sync.py leaves it
NEVER = "9999"
BLOCKS = "Blocks"
OPEN = ("new", "indeterminate", "undefined")
COPIED = "%Y-%m-%dT%H:%M:%SZ"


class Stopped(Exception):
    """Nothing was written. The message is the reason."""


def parse_now(text):
    try:
        return datetime.datetime.strptime(text or "", "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        raise Stopped("--now is the clock value, as 2026-12-01T09:00:00Z. It is required: the computer's clock is never read")


def load(path):
    """The records, checked field by field, so that nothing later meets a value it cannot handle."""
    def name(value, optional=False):
        return (optional and value is None) or (isinstance(value, str) and bool(NAME.fullmatch(value)))

    def moment(value):
        return value is None or (isinstance(value, str) and created_utc(value) is not None)

    def link(l):
        return (isinstance(l, dict) and name(l.get("type")) and name(l.get("says")) and l.get("this_item_is") in ("source", "target") and isinstance(l.get("other"), str)
                and bool(REF.fullmatch(l["other"])) and (l.get("other_status") is None or (name(l["other_status"].get("name")) and l["other_status"].get("category") in OPEN + ("done",))))

    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        items = data["items"]
        ok = (data["format"] == FORMAT and isinstance(items, list) and isinstance(data["priorities"], list) and all(name(p) for p in data["priorities"])
              and len(set(data["priorities"])) == len(data["priorities"]) and bool(REF.fullmatch(data["project"]["key"] + "-1"))
              and isinstance(data["link_types"], list) and all(name(k["name"]) and name(k["inward"]) and name(k["outward"]) for k in data["link_types"])
              and all(isinstance(i, dict) and REF.fullmatch(i["key"]) and i["status"]["category"] in OPEN + ("done",) and name(i["status"]["name"])
                      and i["assignee"] in ("me", "someone else", "nobody") and isinstance(i["links"], list) and all(link(l) for l in i["links"])
                      and name(i["priority"], optional=True) and name(i["issuetype"], optional=True) and moment(i["created"])
                      and (i["duedate"] is None or datetime.datetime.strptime(i["duedate"], "%Y-%m-%d"))
                      and datetime.datetime.strptime(i["copied_at"], COPIED) for i in items)
              and len(set(i["key"] for i in items)) == len(items))
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        ok = False
    if not ok:
        raise Stopped("the records file cannot be read as records of format %s: a field is missing or is not of the shape sync.py writes, or one key is there twice" % FORMAT)
    return data


def key_order(key):
    project, number = key.rsplit("-", 1)
    return project, int(number), key


def created_utc(value):
    """A recorded time as UTC text that sorts in time order, or None. sync.py writes UTC; Jira's own shapes are read too."""
    for shape in (COPIED, "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            read = datetime.datetime.strptime(value, shape)
            return (read if read.tzinfo is None else read.astimezone(datetime.timezone.utc)).strftime(COPIED)
        except (TypeError, ValueError):
            pass
    return None


def age_words(now, then):
    hours = int((now - then).total_seconds() // 3600)
    return "%d day%s" % (hours // 24, "" if hours // 24 == 1 else "s") if hours >= 48 else "%d hour%s" % (hours, "" if hours == 1 else "s")


class Ranking:
    """Everything worked out from one records file and one clock value. Nothing here reads a clock or a network."""

    def __init__(self, data, now, rule):
        self.data, self.now, self.rule = data, now, rule
        self.priorities = data["priorities"]
        self.items = {item["key"]: item for item in data["items"]}
        self.blocks = BLOCKS if any(kind["name"] == BLOCKS for kind in data["link_types"]) else None
        for item in self.items.values():
            if datetime.datetime.strptime(item["copied_at"], "%Y-%m-%dT%H:%M:%SZ") > now:
                raise Stopped("the clock value is earlier than the copy of %s (`copied_at` %s), so ages cannot be worked out" % (item["key"], item["copied_at"]))
        self.not_offered, self.blocked, self.ranked = [], [], []
        for key in sorted(self.items, key=key_order):
            item = self.items[key]
            if item["status"]["category"] == "done":
                self.not_offered.append((key, "`status` is `%s`, which Jira puts in its \"done\" category" % item["status"]["name"]))
            elif item["assignee"] == "someone else":
                self.not_offered.append((key, "`assignee` is someone else"))
            elif self.open_blockers(key):
                self.blocked.append(key)
            else:
                self.ranked.append(key)
        self.ranked.sort(key=self.sort_key)
        self.blocked.sort(key=self.sort_key)

    # ------------------------------------------------------------ facts about one item

    def stale(self, key):
        return self.now - datetime.datetime.strptime(self.items[key]["copied_at"], "%Y-%m-%dT%H:%M:%SZ") > datetime.timedelta(hours=LIMIT_HOURS)

    def stale_words(self, key):
        copied = datetime.datetime.strptime(self.items[key]["copied_at"], "%Y-%m-%dT%H:%M:%SZ")
        return ("STALE COPY: `copied_at` is `%s`, %s before the clock value. The limit is %d hours. Its status, its blockers and who has it may "
                "have changed since. `copied_at` is a field of the local record, not of Jira" % (self.items[key]["copied_at"], age_words(self.now, copied), LIMIT_HOURS))

    def copied(self, key):
        return datetime.datetime.strptime(self.items[key]["copied_at"], COPIED)

    def status_views(self, key, blocker):
        """Every copy there is of a blocker's status: [(when copied, status, where it was read)]."""
        views = []
        if blocker in self.items:
            views.append((self.items[blocker]["copied_at"], self.items[blocker]["status"], "`%s`'s own record, copied at `%s`" % (blocker, self.items[blocker]["copied_at"])))
        for link in self.items[key]["links"]:
            if link["type"] == self.blocks and link["this_item_is"] == "target" and link["other"] == blocker and link.get("other_status"):
                views.append((self.items[key]["copied_at"], link["other_status"], "what Jira showed of it inside `%s`'s record, copied at `%s`" % (key, self.items[key]["copied_at"])))
        return sorted(views, key=lambda view: (view[0], view[2]))

    def blockers(self, key):
        """Every item a Blocks link says this one is blocked by, read from BOTH ends of the link.
        Each is {"key", "blocking", "doubt", "words"}: whether it still blocks, whether that is in doubt, and the reason."""
        if self.blocks is None:
            return []
        mine = set(l["other"] for l in self.items[key]["links"] if l["type"] == self.blocks and l["this_item_is"] == "target")
        theirs = set(other["key"] for other in self.items.values() if other["key"] != key
                     and any(l["type"] == self.blocks and l["this_item_is"] == "source" and l["other"] == key for l in other["links"]))
        found = []
        for blocker in sorted(mine | theirs, key=key_order):
            views = self.status_views(key, blocker)
            doubt, said = False, []
            if blocker in mine and blocker in theirs:
                said.append("`issuelinks` says `%s` is blocked by it, in both records" % key)
            elif blocker in mine:
                said.append("`issuelinks` in `%s`'s own record says it is blocked by it" % key)
                if blocker in self.items:
                    newer = self.copied(blocker) > self.copied(key)
                    said.append("`%s`'s own record, copied %s, does not show the link%s" % (blocker, "LATER" if newer else "earlier", ", so it may have been removed" if newer else ""))
                    doubt = doubt or newer
            else:
                newer = self.copied(key) > self.copied(blocker)
                said.append("`issuelinks` in `%s`'s record says it blocks `%s`. `%s`'s own record, copied %s, does not show the link%s"
                            % (blocker, key, key, "LATER" if newer else "earlier", ", so it may have been removed" if newer else ""))
                doubt = doubt or newer
            done = set(view[1]["category"] == "done" for view in views)
            if not views:
                blocking, doubt = True, True
                said.append("its status is recorded nowhere, so it is treated as still blocking")
            elif len(done) > 1:
                blocking, doubt = True, True
                said.append("THE COPIES OF ITS STATUS DISAGREE: %s. It is treated as still blocking. Copy both items again"
                            % "; ".join("`status` `%s` in %s" % (view[1]["name"], view[2]) for view in views))
            else:
                blocking = not done.pop()
                said.append("its `status` is `%s`, read from %s" % (views[-1][1]["name"], " and from ".join(view[2] for view in views)))
            if blocker in self.items and self.stale(blocker):
                doubt = True
                said.append("`%s`'s own record IS STALE" % blocker)
            found.append({"key": blocker, "blocking": blocking, "doubt": doubt, "words": ". ".join(piece[0].upper() + piece[1:] if not piece.startswith("`") else piece for piece in said)})
        return found

    def open_blockers(self, key):
        return [blocker for blocker in self.blockers(key) if blocker["blocking"]]

    def status_of_other(self, key, link):
        """The other end of a link this item is the SOURCE of: its status, from its own record if there is one."""
        other = self.items.get(link["other"])
        return other["status"] if other is not None else link.get("other_status")

    def waiters(self, key):
        """Open items this one blocks: from its own links, and from other records' links that name it."""
        waiting = set()
        if self.blocks is None:
            return []
        for link in self.items[key]["links"]:
            if link["type"] == self.blocks and link["this_item_is"] == "source" and link["other"] != key:
                status = self.status_of_other(key, link)
                if status is None or status["category"] != "done":
                    waiting.add(link["other"])
        for other in self.items.values():
            if other["key"] != key and other["status"]["category"] != "done" and any(l["type"] == self.blocks and l["this_item_is"] == "target" and l["other"] == key for l in other["links"]):
                waiting.add(other["key"])
        return sorted(waiting, key=key_order)

    def missing(self, key):
        item, gone = self.items[key], []
        if item["priority"] is None:
            gone.append("priority")
        elif item["priority"] not in self.priorities:
            gone.append("priority (`%s` is not among the site's priorities as copied)" % item["priority"])
        if item["duedate"] is None:
            gone.append("duedate")
        if created_utc(item["created"]) is None:
            gone.append("created")
        return gone

    def confidence(self, key):
        return LEVELS[min(len(self.because(key)), 2)]

    def because(self, key):
        """Every reason confidence is lower than high, one step each."""
        why = ["`%s` is not recorded" % gone if " " not in gone else gone for gone in self.missing(key)]
        if self.stale(key):
            why.append("the copy is stale")
        if any(blocker["doubt"] for blocker in self.blockers(key)):
            why.append("what is recorded about a blocker is in doubt")
        return why

    def confidence_words(self, key):
        why = self.because(key)
        return "%s%s" % (self.confidence(key), ", because " + "; ".join(why) if why else "")

    def started(self):
        return [key for key in self.ranked if self.items[key]["assignee"] == "me" and self.items[key]["status"]["category"] == "indeterminate"]

    # ------------------------------------------------------------ the order

    def value(self, key, criterion):
        item = self.items[key]
        if criterion == "priority":
            return self.priorities.index(item["priority"]) if item["priority"] in self.priorities else len(self.priorities)
        if criterion == "due":
            return item["duedate"] or NEVER
        if criterion == "waiters":
            return -len(self.waiters(key))
        if criterion == "created":
            return created_utc(item["created"]) or NEVER
        return key_order(key)

    def sort_key(self, key):
        return tuple(self.value(key, criterion) for criterion in RULES[self.rule])

    def shown(self, key, criterion):
        """A criterion's value for an item, in words that name the field."""
        item = self.items[key]
        if criterion == "priority":
            if item["priority"] is None:
                return "`priority` is not recorded"
            if item["priority"] not in self.priorities:
                return "`priority` is `%s`, which is not among the site's priorities as copied" % item["priority"]
            return "`priority` is `%s`, number %d of the site's %d" % (item["priority"], self.priorities.index(item["priority"]) + 1, len(self.priorities))
        if criterion == "due":
            if item["duedate"] is None:
                return "`duedate` is not recorded"
            days = (datetime.datetime.strptime(item["duedate"], "%Y-%m-%d").date() - self.now.date()).days
            return "`duedate` is `%s`, %s" % (item["duedate"], "the UTC date of the clock value" if days == 0 else
                                             "%d day%s after the UTC date of the clock value" % (days, "" if days == 1 else "s") if days > 0 else
                                             "OVERDUE: %d day%s BEFORE the UTC date of the clock value" % (-days, "" if days == -1 else "s"))
        if criterion == "waiters":
            waiting = self.waiters(key)
            return "`issuelinks` shows %d open item%s waiting on it%s" % (len(waiting), "" if len(waiting) == 1 else "s", ": " + ", ".join("`%s`" % w for w in waiting) if waiting else "")
        if criterion == "created":
            return "`created` is `%s`" % item["created"] if created_utc(item["created"]) else "`created` is not recorded"
        return "`key` is `%s`" % key

    def decided(self, first, second):
        """The criterion that puts `first` before `second`, and both values."""
        for criterion in RULES[self.rule]:
            if self.value(first, criterion) != self.value(second, criterion):
                return criterion, self.shown(first, criterion), self.shown(second, criterion)
        return "key", self.shown(first, "key"), self.shown(second, "key")

    def start_here(self):
        for key in self.ranked:
            if not self.stale(key):
                return key
        return None


# ---------------------------------------------------------------- the recommendation


def write_recommendation(r, other_rule=None):
    out = []
    w = out.append
    items, data = r.items, r.data
    fields = ", then ".join("`%s`" % FIELD_OF[c] for c in RULES[r.rule])
    w("# What to work on next, from the local copy of Jira project %s" % data["project"]["key"])
    w("")
    w("Written by `participant/skills/jira-next-work/rank.py rank` from a records file. Do not edit it: run it again.")
    w("")
    w("**This is advice.** Nothing here was started, assigned or changed. Jira was not contacted to write this.")
    w("")
    w("- Clock value: `%s`, given with `--now`. The computer's clock was not read." % r.now.strftime(COPIED))
    w("- Rule: `%s`. The criteria, in order: %s. The first one on which two items differ decides between them." % (r.rule, ", ".join(RULES[r.rule])))
    w("- The site's priorities, in the order Jira listed them when copied, taken to be highest first: %s." % ", ".join("`%s`" % p for p in r.priorities))
    w("- A copy is stale when `copied_at` is more than %d hours before the clock value, the same limit as in `%s`." % (LIMIT_HOURS, POLICY))
    w("- A due date has no time of day. It is compared with the UTC date of the clock value.")
    w("- Records: %d items. Ranked: %d. Blocked: %d. Not offered: %d." % (len(items), len(r.ranked), len(r.blocked), len(r.not_offered)))
    w("- Items are named by key. The records hold no titles and no people.")
    w("- **Confidence is about the data, not the advice.** High means every field used was recorded and the copy is fresh. It does not mean the item is the right one to do.")
    kinds = ", ".join("`%s`" % kind["name"] for kind in data["link_types"]) or "none"
    if r.blocks is None:
        w("")
        w("**WARNING: NOTHING CAN BE SHOWN AS BLOCKED.** This site has no link type named `%s`. Its link types are: %s. The ranking takes only a link" % (BLOCKS, kinds))
        w("of the type named `%s` to mean that one item blocks another, so the Blocked list below is empty whatever the links say." % BLOCKS)
    else:
        w("- A link blocks when its type is the one named `%s`. The site's link types as copied: %s." % (BLOCKS, kinds))
    w("")
    w("## Start here")
    w("")
    start = r.start_here()
    if start is None:
        w("**Nothing.** %s" % ("No item is ranked." if not r.ranked else "Every ranked item's copy is stale. Copy the project again before starting anything."))
    else:
        place = r.ranked.index(start) + 1
        w("**`%s`**, place %d. Confidence in the data: %s." % (start, place, r.confidence_words(start)))
        w("")
        if place > 1:
            w("It is not first on the recorded fields. Ranked above it, on copies too old to act on. **Copy these again first: they may be the better choice.**")
            w("")
            for key in r.ranked[:place - 1]:
                w("- `%s`, place %d. %s." % (key, r.ranked.index(key) + 1, r.stale_words(key)))
            w("")
        w("Why this one: %s." % "; ".join(r.shown(start, c) for c in RULES[r.rule][:4]))
        later = [key for key in r.ranked[place:] if not r.stale(key)]
        if later:
            criterion, mine, theirs = r.decided(start, later[0])
            w("")
            w("Why it beat the next fresh item, `%s`: they first differ on **%s**. For `%s`, %s. For `%s`, %s." % (later[0], criterion, start, mine, later[0], theirs))
        ahead = [key for key in r.blocked if r.sort_key(key) < r.sort_key(start)]
        if ahead:
            w("")
            w("Blocked items that would rank above it if they were not blocked. Unblocking one may matter more than starting this:")
            w("")
            for key in ahead:
                w("- `%s`: %s; blocked by %s." % (key, "; ".join(r.shown(key, c) for c in RULES[r.rule][:2]), ", ".join("`%s`" % blocker["key"] for blocker in r.open_blockers(key))))
    w("")
    w("## Already started by you")
    w("")
    w("`assignee` is me and `status` is in Jira's in-progress category. `status` is not a ranking criterion, so these keep the place the criteria give them. They are listed here so that they are seen: whether to finish one before starting something new is for you to judge.")
    w("")
    if not r.started():
        w("None among the ranked items.")
    for key in r.started():
        waiting = r.waiters(key)
        w("- `%s`, place %d: `status` is `%s`; `issuelinks` shows %d open item%s waiting on it%s." % (key, r.ranked.index(key) + 1, items[key]["status"]["name"], len(waiting), "" if len(waiting) == 1 else "s",
                                                                                              ": " + ", ".join("`%s`" % k for k in waiting) if waiting else ""))
    w("")
    w("## Ranked")
    w("")
    w("Open, not blocked, and unassigned or assigned to me. A stale item keeps the place its recorded fields give it, with a warning.")
    w("")
    if r.ranked:
        w("| Place | Item | Confidence in the data | Warning |")
        w("|---|---|---|---|")
        for place, key in enumerate(r.ranked, 1):
            w("| %d | `%s` | %s | %s |" % (place, key, r.confidence(key), "STALE" if r.stale(key) else "-"))
    else:
        w("None.")
    for place, key in enumerate(r.ranked, 1):
        item = items[key]
        w("")
        w("### %d. `%s`" % (place, key))
        w("")
        for criterion in RULES[r.rule][:4]:
            w("- Reason, %s: %s." % (criterion, r.shown(key, criterion)))
        if place == 1:
            w("- It is first because no other ranked item comes before it on %s." % fields)
        else:
            above = r.ranked[place - 2]
            criterion, theirs, mine = r.decided(above, key)
            w("- It is below `%s` on **%s**: for `%s`, %s; for this one, %s.%s" % (above, criterion, above, theirs, mine,
                                                                               " Every earlier criterion was equal, so this is the tie-break." if criterion != RULES[r.rule][0] else ""))
        w("- Facts not used to rank: `status` is `%s`; `assignee` is %s; `issuetype` is `%s`; `copied_at` is `%s`." % (item["status"]["name"], item["assignee"], item["issuetype"], item["copied_at"]))
        for blocker in r.blockers(key):
            w("- No longer blocked by `%s`: %s." % (blocker["key"], blocker["words"]))
        w("- Confidence in the data: %s." % r.confidence_words(key))
        if r.stale(key):
            w("- WARNING: %s." % r.stale_words(key))
    w("")
    w("## Blocked")
    w("")
    w("Open and not someone else's, and waiting on an item that is not done. Not ranked. In the order the rule would give them.")
    w("")
    if not r.blocked:
        w("None.")
    for key in r.blocked:
        item = items[key]
        w("### `%s`" % key)
        w("")
        for blocker in r.blockers(key):
            w("- %s `%s`: %s." % ("BLOCKED BY" if blocker["blocking"] else "No longer blocked by", blocker["key"], blocker["words"]))
        for criterion in RULES[r.rule][:4]:
            w("- If it were not blocked, %s: %s." % (criterion, r.shown(key, criterion)))
        w("- Facts not used to rank: `status` is `%s`; `assignee` is %s; `issuetype` is `%s`; `copied_at` is `%s`." % (item["status"]["name"], item["assignee"], item["issuetype"], item["copied_at"]))
        w("- Confidence in the data: %s." % r.confidence_words(key))
        if r.stale(key):
            w("- WARNING: %s." % r.stale_words(key))
        w("")
    w("## Not offered")
    w("")
    if not r.not_offered:
        w("None.")
    for key, why in r.not_offered:
        w("- `%s`: %s.%s" % (key, why, " " + r.stale_words(key) + "." if r.stale(key) else ""))
    w("")
    w("## Missing fields")
    w("")
    lacking = [(key, r.missing(key)) for key in r.ranked + r.blocked if r.missing(key)]
    if not lacking:
        w("None among the ranked and blocked items.")
    else:
        w("A missing field is never filled in. On the criterion that uses it, the item goes after every item that has a value. Each missing field lowers confidence one step.")
        w("")
    for key, gone in lacking:
        w("- `%s`: %s." % (key, ", ".join("`%s`" % g if " " not in g else g for g in gone)))
    if other_rule:
        other = Ranking(r.data, r.now, other_rule)
        w("")
        w("## The same records under the rule `%s`" % other_rule)
        w("")
        w("The criteria, in order: %s. Blocked and not-offered items are the same under both rules." % ", ".join(RULES[other_rule]))
        w("")
        w("| Item | Place under `%s` | Place under `%s` | |" % (r.rule, other_rule))
        w("|---|---|---|---|")
        for key in other.ranked:
            a, b = r.ranked.index(key) + 1, other.ranked.index(key) + 1
            w("| `%s` | %d | %d | %s |" % (key, a, b, "-" if a == b else "moved %s" % ("up" if b < a else "down")))
        moved = [key for key in other.ranked if r.ranked.index(key) != other.ranked.index(key)]
        w("")
        w("%s" % ("Nothing moves: these records give the same order under both rules." if not moved else
                  "%d item%s move%s. Start here would be %s." % (len(moved), "" if len(moved) == 1 else "s", "s" if len(moved) == 1 else "", "`%s`" % other.start_here() if other.start_here() else "nothing")))
        for key in moved[:1]:
            first = other.ranked[0]
            if first != r.ranked[0]:
                w("")
                w("Why `%s` is first under `%s` and not under `%s`: %s, and under `%s` that is looked at before `%s`."
                  % (first, other_rule, r.rule, other.shown(first, RULES[other_rule][0]), other_rule, FIELD_OF[RULES[other_rule][1]]))
    w("")
    w("## What this does not know")
    w("")
    w("- Whether a recorded priority is right, how large an item is, or who is asking.")
    w("- Anything that changed in Jira after `copied_at`. It does not refresh a copy. It says the copy is stale.")
    w("- What an item is about. No title or description is in the records.")
    w("- Whether finishing started work should come before starting new work. It lists started work and leaves that to you.")
    return "\n".join(out) + "\n"


RULES_TEXT = """# Rules for recommending the next Jira item

Written by `participant/skills/jira-next-work/rank.py rules`. Do not edit it: run it again. These are the rules the
ranking follows, stated from the same file that does the ranking.

**The recommendation is advice.** It starts nothing, assigns nothing and changes nothing in Jira. It is worked out
from local records, copied from Jira earlier by `sync.py copy`, which only reads.

## What goes in

- **One records file.** For each item: `key`, `issuetype`, `status`, `priority`, `assignee`, `duedate`, `created`,
  `updated`, its links (`issuelinks`), and `copied_at`, the time that copy was taken. No titles. No people: `assignee`
  holds one of three words, "me", "someone else" or "nobody".
- **One clock value,** given with `--now`. The computer's clock is never read. The same records and the same clock
  value always give the same recommendation.

## The three lists

Every item goes in exactly one.

| List | When | Field |
|---|---|---|
| **Not offered** | The item is done, or someone else has it | `status` in Jira's "done" category, or `assignee` is someone else |
| **Blocked** | Open, not someone else's, and waiting on an item that is not done | `issuelinks`: a link of the type named "Blocks" in which this item is the one that "is blocked by" |
| **Ranked** | Everything else: open, not blocked, unassigned or assigned to me | |

A blocked item is **not ranked**. It is listed separately with **its blocker named** and the blocker's status.

**Started work is not ranked first.** `status` is not a criterion. An item that is assigned to me and in progress
is listed at the top, under "Already started by you", and keeps the place the criteria give it. Whether to finish
before starting is left to the person.

## The order of the ranked list

The first criterion on which two items differ decides. There are no weights and no score.

| # | Criterion | Field | Order |
|---|---|---|---|
| 1 | priority | `priority` | The site's own order of its priorities, highest first |
| 2 | due | `duedate` | Earliest first |
| 3 | waiters | `issuelinks` | The item that blocks the most open items first |
| 4 | created | `created` | Oldest first |
| 5 | key | `key` | By project, then by number, then by the key as written |

The rule `due-first` puts criterion 2 before criterion 1 and changes nothing else.

## Ties

**A tie on one criterion is broken by the next one.** Criterion 5, the key, always decides, because no two items
have the same key. So there is never an undecided tie, and the order never depends on the order of the records in
the file. Where a later criterion decided, the reason says "this is the tie-break".

## Missing fields

- A missing `priority`, `duedate` or `created` is **never filled in** and never guessed.
- On that criterion the item goes **after every item that has a value**.
- **Confidence falls one step for each missing field:** high, then medium, then low.
- Every missing field is listed under "Missing fields" in the recommendation, and in the item's own reasons.
- A priority name that is not among the site's priorities, as copied, is treated as missing and reported.

Confidence says how complete and how fresh the data is. **It does not say the advice is good.** The scale stops at
low: three or more steps is still low.

## Stale copies

- A copy is **stale** when its `copied_at` is more than **24 hours** before the clock value. The limit is the one for
  a work item's status in `participant/context/freshness/policy.md`.
- A stale item **keeps its place** and carries a **warning**: its status, its blockers and who has it may have changed.
- A copy exactly 24 hours old is not stale. One second more is.
- A stale copy costs one step of confidence.
- **"Start here" is the first ranked item whose copy is not stale.** A stale item is never offered as the thing to
  start. If every ranked item is stale, the recommendation is to copy again.
- `copied_at` is a field of the local record, not of Jira. Every other reason cites a Jira field.

## Blockers

A link has two ends, and each end is in a different record, copied at its own time. So the records can disagree.

- **Both ends are read.** An item is blocked if its own record says so, **or** if another item's record says it
  blocks this one. The reason says which record showed the link, and which did not.
- **The blocker's status can have two copies:** its own record, and what Jira showed of it inside the blocked
  item's record. If they agree, that is its status. A blocker that is done no longer blocks.
- **If the two copies disagree** about whether the blocker is done, the item is treated as **still blocked**. The
  reason gives both, with their times, and says to copy both again.
- A blocker whose status is recorded nowhere is treated as **still blocking**.
- **Confidence falls one step** when anything recorded about a blocker is in doubt: the copies disagree, the status
  is recorded nowhere, the blocker's own record is stale, or the newer of two records no longer shows the link.
- **If the site has no link type named "Blocks",** nothing can be shown as blocked, and the recommendation says so
  at the top. It does not say "Blocked: none".
- Which items are waiting on an item (the third criterion) is read from both ends in the same way. It counts every
  open item, whoever has it and whether or not it is itself blocked.

## Due dates

- A due date has no time of day. It is compared with the **UTC date** of the clock value.
- A due date before that is marked **OVERDUE**. Being overdue does not change the order: earliest first already
  puts it ahead.
- For someone far from UTC, near midnight, "overdue" can be a day out.

## What every reason must have

**Each reason names the recorded field it came from.** A reason with no field behind it is not written. Fields that
are recorded and not used to rank (`status`, `assignee`, `issuetype`) are shown as facts, and said to be unused.

## What the rules do not do

- They do not weigh priority against urgency. The order is strict, and another rule gives another answer.
- They do not decide whether to finish started work before starting new work.
- They do not know whether a recorded priority is right, how large an item is, or who is asking.
- They handle one list of priorities, the one copied from the site. A priority name not on it is treated as missing.
- They do not read titles or descriptions. The records hold none.
- They do not refresh a stale copy.
"""


def cmd_rank(args):
    ranking = Ranking(load(args.records), parse_now(args.now), args.rule)
    if args.also_rule == args.rule:
        raise Stopped("--also-rule must name the other rule")
    text = write_recommendation(ranking, args.also_rule)
    if args.out:
        if os.path.abspath(args.out) == os.path.abspath(args.records):
            raise Stopped("--out names the records file. The records are never written over")
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    start = ranking.start_here()
    print("RANKING under the rule %s, clock value %s. Nothing was changed anywhere but the recommendation file." % (args.rule, args.now))
    print("Start here: %s" % (start or "nothing"))
    if ranking.blocks is None:
        print("WARNING: the site has no link type named %s, so nothing can be shown as blocked." % BLOCKS)
    for place, key in enumerate(ranking.ranked, 1):
        print("  %2d. %-10s confidence in the data %-6s %s" % (place, key, ranking.confidence(key), "STALE" if ranking.stale(key) else ""))
    for key in ranking.blocked:
        print("  blocked      %-10s by %s" % (key, ", ".join(blocker["key"] for blocker in ranking.open_blockers(key))))
    for key, why in ranking.not_offered:
        print("  not offered  %-10s %s" % (key, "done" if "done" in why else "someone else has it"))
    print("sha256 of the recommendation: %s" % hashlib.sha256(text.encode("utf-8")).hexdigest())
    print("sha256 of the records file:   %s" % file_sha(args.records))
    return 0


def file_sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def where(ranking, key):
    if key in ranking.ranked:
        return "ranked, place %d" % (ranking.ranked.index(key) + 1)
    if key in ranking.blocked:
        return "blocked by %s" % ", ".join(blocker["key"] for blocker in ranking.open_blockers(key))
    return dict(ranking.not_offered).get(key, "not in the records").replace("`", "")


def cmd_diff(args):
    before = Ranking(load(args.before), parse_now(args.now_before), args.rule)
    after = Ranking(load(args.after), parse_now(args.now_after), args.rule)
    print("WHAT CHANGED between two rankings, under the rule %s. This reads two records files and changes nothing." % args.rule)
    print("Start here, before: %s. After: %s." % (before.start_here() or "nothing", after.start_here() or "nothing"))
    changed = 0
    for key in sorted(set(before.items) | set(after.items), key=key_order):
        was, now = where(before, key), where(after, key)
        if was == now:
            continue
        changed += 1
        print("")
        print("%s: was %s. Now %s." % (key, was, now))
        a, b = before.items.get(key), after.items.get(key)
        fields = [("status", lambda i: i["status"]["name"]), ("assignee", lambda i: i["assignee"]), ("priority", lambda i: i["priority"]), ("duedate", lambda i: i["duedate"]),
                  ("issuelinks", lambda i: sorted("%s %s" % (l.get("says"), l.get("other")) for l in i["links"])), ("copied_at", lambda i: i["copied_at"])]
        told = False
        for related in [key] + sorted(set(blocker["key"] for r, k in ((before, key), (after, key)) if k in r.items for blocker in r.blockers(k)), key=key_order):
            x, y = before.items.get(related), after.items.get(related)
            if x is None or y is None:
                continue
            for name, read in fields:
                if read(x) != read(y):
                    told = told or name != "copied_at"
                    print("  why: in the record of %s, `%s` was %s and is now %s." % (related, name, json.dumps(read(x)), json.dumps(read(y))))
        if a is None or b is None:
            print("  why: %s is in only one of the two records files." % key)
        elif not told:
            print("  why: none of its own fields changed. Its place changed because an item around it moved, or because its copy is now stale or fresh.")
    print("")
    print("%d item%s changed list or place. %d did not." % (changed, "" if changed == 1 else "s", len(set(before.items) | set(after.items)) - changed))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Rank the open items of a Jira project from local records. Advice only.")
    commands = parser.add_subparsers(dest="command", required=True)
    rank = commands.add_parser("rank")
    rank.add_argument("--records", required=True)
    rank.add_argument("--now", help="the clock value, as 2026-12-01T09:00:00Z")
    rank.add_argument("--rule", choices=sorted(RULES), default="priority-first")
    rank.add_argument("--also-rule", choices=sorted(RULES), help="also show the order under this other rule")
    rank.add_argument("--out", help="write the recommendation here")
    rules = commands.add_parser("rules")
    rules.add_argument("--out")
    diff = commands.add_parser("diff")
    for name in ("--before", "--now-before", "--after", "--now-after"):
        diff.add_argument(name, required=True)
    diff.add_argument("--rule", choices=sorted(RULES), default="priority-first")
    args = parser.parse_args(argv)
    try:
        if args.command == "rules":
            if args.out:
                os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
                with open(args.out, "w", encoding="utf-8", newline="\n") as f:
                    f.write(RULES_TEXT)
            else:
                sys.stdout.write(RULES_TEXT)
            return 0
        return cmd_rank(args) if args.command == "rank" else cmd_diff(args)
    except Stopped as reason:
        print("STOPPED: %s." % reason)
        print("Nothing was written.")
        return 2


if __name__ == "__main__":
    sys.exit(main())
