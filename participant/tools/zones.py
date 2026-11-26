#!/usr/bin/env python3
"""The ownership zones of this repository, as rules a tool applies. For the quest base-camp-ownership-zones.

    zones.py where PATH [PATH ...]            say which zone each path is in, who writes there, and whether the agent may
    zones.py write --to PATH --text TEXT      check the path against the rules, and only then write the file
    zones.py audit                            list every file that is in no zone. Exit 1 if there is one
    zones.py rules --write | --check          write participant/context/zone-rules.md from the rules below, or compare
    zones.py hook                             the same check, for Claude Code to run before each of its file edits

--root DIR makes any command work on another folder laid out like the repository, such as a sandbox copy for tests.
A root that is a folder inside the real repository is refused: it would let a write into `content/` pass as a write
into `content/participant/`.

THE RULES ARE IN ONE PLACE: the lists below. The document a person reads is written from them.

HOW A PATH IS JUDGED. Never by the text it was given as.
  1. The path is made absolute.
  2. It is RESOLVED: every ".." is worked out and every symbolic link is followed, to the place a write would land.
  3. That place must be inside the root. "Inside" is decided by walking up from the place, folder by folder, until a
     folder IS the root: the same folder on the same disk, whatever it is called. So another spelling of the
     repository's path (other capitals, or another route to the same disk) is still the repository.
  4. The zone is the zone of that place, not of the path as written. A link in the participant's folder that leads
     into the curriculum is a write to the curriculum, and is refused.
  5. If a file is already there and has more than one name on the disk (a hard link), it is refused: its other name
     could be anywhere, and resolving a path cannot show where.

A WRITE THAT IS REFUSED CREATES NOTHING: no file, no temporary file. Nothing is created before the check. If the
path changes between the check and the write, the folders this run made for it are taken away again. A write that is
allowed goes to a temporary name beside the target and is renamed into place.

THE HOOK. Claude Code can run a command before each use of its file-editing tools and will not make the edit if the
command exits with 2. `zones.py hook` reads the tool's input and applies the same rules. It covers Edit, Write,
MultiEdit and NotebookEdit. A path that is not in the repository, as written or as resolved, is not the repository's
business and is let through.
    IT DOES NOT COVER what a shell command writes, or what any other tool writes. A command such as `echo x > file`
    is not a file edit to Claude Code and never reaches this check.
    The hook only APPROVES an edit. Claude Code then makes it, a moment later and in its own way. If the path is
    changed in that moment, the check has been made of something else.
    If the hook fails in any way it can catch, it refuses. The command it is installed with ends in `|| exit 2`, so
    that a failure it cannot catch, such as this file being broken, refuses too.

Exit codes: 0 allowed, written, or nothing found. 1 refused, or something found. 2 (hook only) refused.
"""
import argparse
import fnmatch
import json
import os
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
RULES_DOC = os.path.join("participant", "context", "zone-rules.md")

# ---------------------------------------------------------------- the rules, as data

PROGRAM_TOP = ["content", "schemas", "templates", "assets", "artifacts", "fixtures", "quest_app", "validators", "tests", "tools", "scripts", "vendor",
               "prototype", "deploy", "docs", ".github", ".claude", "README.md", "CONTRIBUTING.md", "CLAUDE.md", "HANDOFF-PROMPT.md",
               "PACKAGE-MANIFEST.md", "PLANNING-STATUS.md", "IMAGE-PLAN.md", "VALIDATION-REPORT.md", "LICENSE", "LICENSE-CONTENT", "Makefile",
               "pyproject.toml", "install.sh", ".env.example", ".gitignore", ".gitattributes", ".pre-commit-config.yaml"]
GENERATED_TOP = ["generated", "generated.lock", "generated.building", "generated.previous", "dist", ".venv", "venv", ".git", ".pytest_cache",
                 ".mypy_cache", ".ruff_cache", "*.egg-info"]
TOOL_NAMES_ANYWHERE = ["node_modules", "__pycache__", ".DS_Store"]
PRIVATE_TOP = ["local-data", ".claude/settings.local.json", ".claude/worktrees"]
# Names that are a credential's. The list is of names, not of contents: it misses a secret under any other name,
# and it refuses some harmless files, such as a presentation called deck.key.
CREDENTIAL_NAMES = [".env", ".env.*", ".env-*", "*.pem", "*.pem.*", "*.key", "*.key.*", "*.p12", "*.pfx", "*.jks", "*.token", "token.json", "id_rsa*",
                    "id_ed25519*", "id_ecdsa*", "id_dsa*", "credentials", "credentials.*", "secrets.json", "secrets.y*ml", "service-account*.json",
                    ".netrc", ".npmrc", ".pypirc", ".envrc", ".pgpass", ".git-credentials"]
# Inside the participant's folder: names that steer the agent or Git. The agent does not write what steers it.
CONTROL_NAMES = [".claude", "CLAUDE.md", "CLAUDE.local.md", ".mcp.json", ".git", ".gitattributes", ".gitmodules", ".pre-commit-config.yaml"]
THE_TOOL = "participant/tools/zones.py"
# Inside the participant's folder: what the application writes. Each is a file, or a folder and all in it.
APPLICATION_TOP = ["progress.yaml", "ACTIVITY.md", ".progress.lock"]
APPLICATION_IN_AN_ATTEMPT = ["manifest.yaml", "submission.yaml", "review.yaml", "validation"]     # participant/evidence/<quest>/<attempt>/<one of these>

ZONES = [
    {"id": "program", "name": "Program-owned",
     "what": "The curriculum, the application, its checks and its documentation.",
     "writer": "The program's maintainers, in the program's own repository. This repository is a copy of that one.",
     "agent": False,
     "git": "Tracked. It comes from the program's repository and is never part of a hand-in. A change to it here would show in `git status` and must not be committed.",
     "folders": ["`%s%s`" % (name, "" if "." in name[1:] or name.isupper() or name in ("LICENSE-CONTENT", "Makefile") else "/") for name in PROGRAM_TOP],
     "new": "Nothing new goes here. A correction or an idea for the program goes to its maintainers, as an issue in the program's repository."},
    {"id": "participant", "name": "Participant-owned",
     "what": "The participant's own work: notes, skills, tests, tools and evidence.",
     "writer": "The participant, and the AI agent when the participant asks. Some files in it are not the agent's to write: see the exceptions.",
     "agent": True,
     "git": "Tracked. `gtq hand-in` commits everything in this folder, and nothing else.",
     "folders": ["`participant/`"],
     "new": "Notes and decisions: `participant/context/`. A skill and its tests: `participant/skills/<name>/`. A test of an application: `participant/tests/`. "
            "A small tool and its tests: `participant/tools/`. Proof of a quest, its logs, screenshots and the scripts that made them: that quest's attempt folder, "
            "`participant/evidence/<quest>/<attempt>/`."},
    {"id": "generated", "name": "Generated and tool-managed",
     "what": "Files a tool makes and keeps. GENERATED: the built site, which can be thrown away and built again. TOOL-MANAGED: installed packages, caches, and Git's own folder, which their tools keep.",
     "writer": "The tool that makes each: `make build`, the package installers, Python, Git. Never a person or the agent by hand.",
     "agent": False,
     "git": "Not tracked. All but `.git/` are ignored by `.gitignore`. `.git/` is Git's own store, which Git never lists.",
     "folders": ["`%s%s`" % (name, "" if name == "generated.lock" else "/") for name in GENERATED_TOP] + ["and, anywhere: " + ", ".join("`%s`" % name for name in TOOL_NAMES_ANYWHERE)],
     "new": "Nothing by hand. MAY BE DELETED, because a tool makes it again: `generated/` and its `generated.*` neighbours (`make build`), `node_modules/` and the caches. "
            "NOT TO BE DELETED: `.git/`, which holds the history and cannot be made again. `.venv/` can be made again by the install script; ask before deleting it."},
    {"id": "private", "name": "Private data",
     "what": "Raw responses from outside systems, run-time state, real personal data, and anything that holds a credential.",
     "writer": "Programs the participant runs, at run time, and the participant by hand. Credentials: the participant alone, by hand. The agent may run such a program; it does not write these files itself.",
     "agent": False,
     "git": "Not tracked. Ignored by `.gitignore`. It must never be committed or leave this computer.",
     "folders": ["`%s%s`" % (name, "" if name.endswith(".json") else "/") for name in PRIVATE_TOP] + ["and, anywhere, a file with a credential's name: " + ", ".join("`%s`" % name for name in CREDENTIAL_NAMES) + " (but not `.env.example`)"],
     "new": "A raw response or a run's state: a folder named for the quest under `local-data/`. Real data about real people, if it cannot be avoided: the same. "
            "Only a redacted copy, with names, addresses and identifiers taken out, goes into `participant/`."},
]

# The rules, in the order they are tried. The first that fits decides. Each refusal names its rule.
ALLOW = "R9"
RULES = [
    ("R1", "refused", "A write must land inside the repository. The path is resolved first: `..` is worked out and symbolic links are followed."),
    ("R2", "refused", "A file with a credential's name is private data wherever it is. Only the participant writes it, by hand."),
    ("R3", "refused", "Inside `participant/`, the agent does not write what steers the agent or Git, or this tool: %s, and `%s`. The participant changes those by hand."
     % (", ".join("`%s`" % name for name in CONTROL_NAMES), THE_TOOL)),
    ("R4", "refused", "%s are tool-managed wherever they are." % ", ".join("`%s`" % name for name in TOOL_NAMES_ANYWHERE)),
    ("R5", "refused", "%s are private data. Programs the participant runs write there; the agent's edits do not." % ", ".join("`%s`" % name for name in PRIVATE_TOP)),
    ("R6", "refused", "The built site, installed packages, caches and `.git/` are written only by the tool that makes them."),
    ("R7", "refused", "Inside `participant/`, what the application writes is not written by hand: %s, and in each attempt folder %s."
     % (", ".join("`%s`" % name for name in APPLICATION_TOP), ", ".join("`%s`" % name for name in APPLICATION_IN_AN_ATTEMPT))),
    ("R8", "refused", "A file that already exists with more than one name on the disk (a hard link) is refused: its other name could be in any zone."),
    ("R9", "**allowed**", "Everything else inside `participant/` is the participant's. The participant and the agent may write there. THIS IS THE ONLY RULE THAT ALLOWS A WRITE."),
    ("R10", "refused", "Everything listed as program-owned belongs to the program's maintainers and is not changed here."),
    ("R11", "refused", "A path that fits no zone, or that is not a place a file can be, is refused. A new kind of file needs a zone before it is written."),
]
RULE_TEXT = {rule: text for rule, _, text in RULES}
ZONE = {zone["id"]: zone for zone in ZONES}
NO_ZONE = {"outside": "outside the repository", "none": "no zone"}


class Verdict:
    def __init__(self, given, resolved, relative, zone, rule, why=""):
        self.given, self.resolved, self.relative, self.zone, self.rule, self.why = given, resolved, relative, zone, rule, why
        self.allowed = rule == ALLOW


def fold(text):
    """Text as a disk that sets capitals and the form of letters aside would compare it."""
    return unicodedata.normalize("NFKC", text).casefold()


def matches(name, patterns):
    return any(fnmatch.fnmatchcase(fold(name), fold(pattern)) for pattern in patterns)


def zone_of(relative):
    """The zone and the rule for a path relative to the root, with forward slashes. It looks at names only and touches
    no disk. Capitals are set aside, because on many disks `Content/` and `content/` are one folder."""
    parts = [part for part in relative.split("/") if part]
    low = [fold(part) for part in parts]
    joined = "/".join(low)
    if not parts:
        return "none", "R11"
    if any(matches(part, CREDENTIAL_NAMES) and fold(part) != ".env.example" for part in parts):
        return "private", "R2"
    if low[0] == "participant" and (any(matches(part, CONTROL_NAMES) for part in parts[1:]) or joined == fold(THE_TOOL) or joined.startswith(fold(THE_TOOL) + "/")):
        return "participant", "R3"
    if any(matches(part, TOOL_NAMES_ANYWHERE) for part in parts):
        return "generated", "R4"
    if any(joined == fold(top) or joined.startswith(fold(top) + "/") for top in PRIVATE_TOP):
        return "private", "R5"
    if matches(parts[0], GENERATED_TOP):
        return "generated", "R6"
    if low[0] == "participant":
        application = (len(low) >= 2 and low[1] in [fold(name) for name in APPLICATION_TOP]) or (
            len(low) >= 5 and low[1] == "evidence" and low[4] in [fold(name) for name in APPLICATION_IN_AN_ATTEMPT])
        return ("participant", "R7") if application else ("participant", ALLOW)
    if low[0] in [fold(name) for name in PROGRAM_TOP]:
        return "program", "R10"
    return "none", "R11"


def same_folder(path, stat):
    try:
        return os.path.samestat(os.stat(path), stat)
    except OSError:
        return False


def below(path, root_stat):
    """The path relative to the root, with forward slashes, if walking up from it reaches a folder that IS the root.
    Otherwise None. The path need not exist: the walk starts at its nearest folder that does."""
    parts, here = [], path
    while True:
        if same_folder(here, root_stat):
            return "/".join(reversed(parts))
        parent = os.path.dirname(here)
        if parent == here:
            return None
        parts.append(os.path.basename(here))
        here = parent


def judge(given, root, cwd=None):
    """Resolves a path and decides whether the agent may write there. Touches nothing."""
    try:
        root_stat = os.stat(root)
        if not isinstance(given, str) or not given or "\x00" in given:
            return Verdict(given, None, None, "outside", "R1", "the path is empty or is not a path")
        absolute = given if os.path.isabs(given) else os.path.join(cwd or os.path.realpath(root), given)
        lexical = os.path.normpath(absolute)                 # the path as written, with its ".." worked out and no link followed
        resolved = os.path.realpath(absolute)                # where a write would really land
        relative = below(resolved, root_stat)
        as_written = below(lexical, root_stat)
        dots = ".." in given.replace("\\", "/").split("/")
        if relative is None or relative == "":
            how = ("it is the repository's own folder, not a file in it" if relative == "" else
                   "it goes through a symbolic link that leads out of the repository" if as_written is not None else
                   "it uses `..` to climb out of the repository" if dots else "it is outside the repository")
            return Verdict(given, resolved, None, "outside", "R1", how)
        zone, rule = zone_of(relative)
        why = ""
        if rule == ALLOW and relative.split("/")[0] != "participant":
            return Verdict(given, resolved, relative, "none", "R11", "its first folder is written `%s`, which is `participant` in other capitals. On some disks that is another folder" % relative.split("/")[0])
        if as_written is not None and fold(as_written) != fold(relative):
            seemed = zone_of(as_written)[0]
            why = "as written it %s, and it resolves to `%s`: a symbolic link on the way leads there" % (
                "seemed to be in the %s zone" % seemed if seemed != zone else "names `%s`" % as_written, relative)
        elif dots and not os.path.isabs(given):
            parts = given.replace("\\", "/").split("/")
            start = zone_of("/".join(parts[:parts.index("..")]))[0]
            if start not in (zone, "none"):
                why = "as written it starts in the %s zone, and its `..` leads to `%s`" % (start, relative)
        if rule == ALLOW:
            here = resolved
            while not same_folder(here, root_stat):          # every folder on the way down must be a folder, if it is there
                parent = os.path.dirname(here)
                if parent == here:                           # the top of the disk, and the root was not met: it is not inside after all
                    return Verdict(given, resolved, None, "outside", "R1", "it is outside the repository")
                if os.path.lexists(parent) and not os.path.isdir(parent):
                    return Verdict(given, resolved, relative, zone, "R11", "`%s`, on the way to it, is a file and not a folder" % below(parent, root_stat))
                here = parent
            if os.path.lexists(resolved):
                if os.path.isdir(resolved):
                    return Verdict(given, resolved, relative, zone, "R11", "it is a folder, not a file")
                if os.stat(resolved).st_nlink > 1:
                    return Verdict(given, resolved, relative, zone, "R8", "the file has %d names on the disk" % os.stat(resolved).st_nlink)
        return Verdict(given, resolved, relative, zone, rule, why)
    except (OSError, ValueError, RecursionError) as failure:      # a link that loops, a name too long, a folder that cannot be read
        return Verdict(given, None, None, "none", "R11", "the path could not be resolved (%s)" % type(failure).__name__)


def explain(verdict):
    """One line saying what was decided, by which rule."""
    zone = ZONE[verdict.zone]["name"] if verdict.zone in ZONE else NO_ZONE[verdict.zone]
    where = "`%s`" % verdict.relative if verdict.relative else "no place in the repository"
    text = "%s rule %s. %s resolves to %s, which is in: %s. %s" % (
        "ALLOWED by" if verdict.allowed else "REFUSED by", verdict.rule, json.dumps(verdict.given), where, zone, RULE_TEXT[verdict.rule])
    return text + (" Here: %s." % verdict.why if verdict.why else "")


def root_problem(root):
    """Why this root cannot be used, or None."""
    if not os.path.isdir(root):
        return "the root is not a folder"
    inside = below(os.path.realpath(root), os.stat(REPO)) if os.path.isdir(REPO) else None
    if inside:
        return "the root is `%s`, a folder inside the real repository. Only the repository itself, or a folder outside it, can be a root" % inside
    return None


# ---------------------------------------------------------------- writing


def write_checked(given, root, data):
    """Checks, and only then writes. Returns (exit code, the lines to print)."""
    verdict = judge(given, root)             # THE CHECK. Nothing has been created or opened for writing yet
    lines = [explain(verdict)]
    if not verdict.allowed:
        return 1, lines + ["Nothing was written, and nothing was created."]
    target = verdict.resolved
    folder = os.path.dirname(target)
    made, here = [], folder                  # the folders this run has to make, so that they can be taken away again
    while not os.path.lexists(here):
        made.append(here)
        here = os.path.dirname(here)
    temporary = os.path.join(folder, ".%s.tmp-%d" % (os.path.basename(target), os.getpid()))
    wrote_temporary = False
    try:
        os.makedirs(folder, exist_ok=True)
        again = judge(target, root)          # the folders now exist. Resolve once more: has the path changed under us?
        if not again.allowed or again.resolved != target:
            raise OSError("the path changed between the check and the write")
        mode = os.stat(target).st_mode & 0o777 if os.path.exists(target) else 0o644
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), mode)
        wrote_temporary = True
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(temporary, target)
    except OSError as failure:
        if wrote_temporary and os.path.lexists(temporary):
            os.remove(temporary)
        for path in made:                    # deepest first. rmdir takes away an empty folder and nothing else
            try:
                os.rmdir(path)
            except OSError:
                pass
        return 1, lines + ["REFUSED after the check: the write could not be made safely (%s). Nothing was written, and what was made for it was taken away."
                           % (failure if str(failure).startswith("the path changed") else type(failure).__name__)]
    return 0, lines + ["WRITTEN: %d bytes to `%s`." % (len(data), verdict.relative)]


# ---------------------------------------------------------------- the commands


def cmd_where(args):
    for given in args.paths:
        verdict = judge(given, args.root)
        zone = ZONE.get(verdict.zone)
        print("%s" % given)
        print("  resolves to:  %s" % (verdict.relative or "no place in the repository"))
        print("  zone:         %s" % (zone["name"] if zone else {"outside": "none: it is outside the repository", "none": "NONE. It fits no zone"}[verdict.zone]))
        if zone:
            print("  written by:   %s" % zone["writer"])
            print("  Git:          %s" % zone["git"])
        print("  the agent:    %s" % explain(verdict))
    return 0


def cmd_write(args):
    code, lines = write_checked(args.to, args.root, (args.text + "\n").encode("utf-8"))
    print("\n".join(lines))
    return code


def all_files(root):
    """Every file under the root, as paths relative to it. Folders that are tool-managed or private are named once
    and not looked into: what is inside them is theirs."""
    found = []
    for folder, names, files in os.walk(root):
        relative_folder = os.path.relpath(folder, root).replace(os.sep, "/")
        relative_folder = "" if relative_folder == "." else relative_folder + "/"
        keep = []
        for name in sorted(names):
            zone, _ = zone_of(relative_folder + name)
            if zone in ("generated", "private"):
                found.append(relative_folder + name + "/")
            else:
                keep.append(name)
        names[:] = keep
        found += [relative_folder + name for name in sorted(files)]
    return found


def cmd_audit(args):
    files = all_files(os.path.realpath(args.root))
    counts, homeless = {}, []
    for relative in files:
        zone, _ = zone_of(relative.rstrip("/"))
        counts[zone] = counts.get(zone, 0) + 1
        if zone == "none":
            homeless.append(relative)
    print("Looked at %d files and tool-managed or private folders under the root." % len(files))
    for zone in ZONES:
        print("  %-28s %d" % (zone["name"] + ":", counts.get(zone["id"], 0)))
    print("  %-28s %d" % ("IN NO ZONE:", len(homeless)))
    for relative in homeless:
        print("    %s" % relative)
    print("EVERY FILE IS IN A ZONE." if not homeless else "FILES IN NO ZONE: %d. Each needs a zone in participant/tools/zones.py before anything writes there." % len(homeless))
    print("(This looks at the top of the repository. Anything inside `participant/` is in the participant's zone by being there, so the audit cannot fail for it.)")
    return 1 if homeless else 0


def rules_document():
    out = ["# Zone rules: who may change which files", "",
           "**Written by `participant/tools/zones.py` from the lists and rules inside it. Do not edit this file by hand:** change them there and run",
           "`python3 participant/tools/zones.py rules --write`. The folders, the names and the rules on this page are the ones the tool applies.", "",
           "The repository has four zones. A file's zone is decided by the rules at the end of this page, tried in order. **The AI agent may write in one",
           "zone only: the participant's.** The tool checks the agent. A person is held to the same table by the \"Who may write\" column and by",
           "reading `git status` before a hand-in, not by the tool.", "",
           "| Zone | What it holds | Who may write | May the agent write? | Git |", "|---|---|---|---|---|"]
    for zone in ZONES:
        out.append("| **%s** | %s | %s | %s | %s |" % (zone["name"], zone["what"], zone["writer"], "**Yes**, with the exceptions in rules R2, R3, R4, R7 and R8" if zone["agent"] else "**No**", zone["git"]))
    out += ["", "## The folders of each zone", ""]
    for zone in ZONES:
        out += ["### %s" % zone["name"], "", ", ".join(zone["folders"]), "", "**A new file:** %s" % zone["new"], ""]
    out += ["## Where does a new file go?", "",
            "| I have | It goes | Zone |", "|---|---|---|",
            "| a note or a decision | `participant/context/` | Participant-owned |",
            "| a skill, with its tests | `participant/skills/<name>/` | Participant-owned |",
            "| a test of an application | `participant/tests/` | Participant-owned |",
            "| a small tool of my own, with its tests | `participant/tools/` | Participant-owned |",
            "| proof for a quest: `PROOF.md`, logs, screenshots, and the scripts that made them | that quest's attempt folder, `participant/evidence/<quest>/<attempt>/` | Participant-owned |",
            "| a lock file an installer wrote inside `participant/`, such as `package-lock.json` | where the installer put it. It is tracked | Participant-owned |",
            "| a raw response from Jira, GitHub or another outside system | `local-data/<quest>/`, written by the program that fetched it, or by me by hand | Private data |",
            "| real data about real people, needed as input | `local-data/<quest>/`, by me by hand. Made-up data is better, and can go in `participant/` | Private data |",
            "| a redacted copy of a response, as evidence | the quest's attempt folder | Participant-owned |",
            "| a token, a password, a key | **best: nowhere in the repository**, in an environment variable set by hand. If a tool insists on a file: `.env` at the top of the repository, which Git ignores, written by me and never by the agent | Private data |",
            "| a temporary experiment | the system's temporary folder, outside the repository. Not a new folder at the top | none |",
            "| the built site | nothing to do: `make build` puts it in `generated/` | Generated and tool-managed |",
            "| a correction to the curriculum, the application or a guide | not here. An issue in the program's repository | Program-owned |",
            "| a change to how the agent behaves in this project | by me, by hand: `.claude/settings.local.json`. The agent does not write what steers it | Private data |",
            "| a quest marked as started or done | nothing by hand: the application writes `participant/progress.yaml` when I use its pages | Participant-owned |",
            "| something that fits none of these | **nowhere yet.** A zone is added to the lists in the tool first, by me | none |", "",
            "## The rules the tool applies, in order", "",
            "A path is **resolved** first: every `..` is worked out and every symbolic link (a file that only points at another place) is followed, to the",
            "place a write would really land. The rules are then tried from the top, and the first that fits decides. A refusal names its rule.", "",
            "| Rule | Result | What it says |", "|---|---|---|"]
    for rule, result, text in RULES:
        out.append("| %s | %s | %s |" % (rule, result, text))
    out += ["", "Deleting, renaming and moving a file are writes: the same table says who may. The tool does not check them.", "",
            "## Words used on this page", "",
            "- **The application**: the Golden Thread Quest program in `quest_app/`, started with `gtq start`, and its web pages.",
            "- **`gtq hand-in`**: the command the participant runs to commit `participant/` and send it for review.",
            "- **Attempt folder**: the folder the application makes when a quest is started, `participant/evidence/<quest>/<attempt>/`.",
            "- **Tracked**: Git records the file and its changes. **Ignored**: Git is told, in `.gitignore`, to leave it alone.",
            "- **Redacted**: with names, addresses, identifiers and credentials taken out.",
            "- **Hook**: a command Claude Code runs before one of its tools, which can stop that tool.",
            "- **Hard link**: a second name for the same file on the disk. Writing to either name changes both.", "",
            "## What the tool does not see", "",
            "- **A write made by a shell command, or by any tool but the file-editing ones.** The check covers `zones.py write` and, where the hook is installed,",
            "  Claude Code's Edit, Write, MultiEdit and NotebookEdit. A command such as `echo x > file`, a program the agent runs, and tools added to the agent",
            "  from outside are not checked. That includes a shell command that changes this tool or these rules.",
            "- **Deletes, renames and moves,** and what Git itself changes: a pull, a merge, `git add -f` of an ignored file.",
            "- **What a person does in an editor.**",
            "- **Whether the hook is installed.** It is, if `.claude/settings.local.json` has a `PreToolUse` entry that runs `zones.py hook`. The tool cannot tell.",
            "- **What a file contains.** A raw response pasted into a note in `participant/context/` is in the right zone and is still private data. So is a",
            "  screenshot with a real name in it. The rule for names catches `.env` and key files. It cannot catch a secret inside an ordinary file, and",
            "  `gtq hand-in` commits everything in `participant/`. A person reads `git status` and the changed files before a hand-in.",
            "- **Whether `.gitignore` says what this page says.** The Git column is written here by hand. `git status` is the check.",
            "- **The moment between the hook's approval and the edit.** The hook approves; Claude Code then writes. A path changed in between is not re-checked.",
            "- **Whether a write the participant asked for was wise.** The zone says who may write. It does not say the write is right.", ""]
    return "\n".join(out)


def cmd_rules(args):
    path = os.path.join(args.root, RULES_DOC)
    text = rules_document()
    if args.check:
        on_disk = None
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                on_disk = f.read()
        ok = on_disk == text
        print("UP TO DATE: %s is what the rules give." % RULES_DOC if ok else "NOT UP TO DATE: %s is not what the rules give. Write it again with --write." % RULES_DOC)
        return 0 if ok else 1
    code, lines = write_checked(path, args.root, text.encode("utf-8"))
    print("\n".join(lines))
    return code


def cmd_hook(args):
    """For Claude Code's PreToolUse hook. Reads the tool call on standard input. Exit 2, with the reason on standard
    error, stops the edit. Any failure in here also stops it."""
    try:
        call = json.load(sys.stdin)
        tool = call.get("tool_name", "") if isinstance(call, dict) else None
        if tool is None:
            raise ValueError("the call is not an object")
        if tool not in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
            return 0
        tool_input = call.get("tool_input") if isinstance(call.get("tool_input"), dict) else {}
        given = tool_input.get("file_path") or tool_input.get("notebook_path")
        if not isinstance(given, str) or not given:
            sys.stderr.write("zones: REFUSED. The %s call names no file, so its zone cannot be checked.\n" % tool)
            return 2
        cwd = call.get("cwd") if isinstance(call.get("cwd"), str) else None
        verdict = judge(given, args.root, cwd)
        if verdict.allowed:
            return 0
        if verdict.zone == "outside" and verdict.resolved is not None:
            absolute = given if os.path.isabs(given) else os.path.join(cwd or os.path.realpath(args.root), given)
            if below(os.path.normpath(absolute), os.stat(args.root)) is None:
                return 0                           # not in the repository, as written or as resolved: not this repository's business
        sys.stderr.write("zones: %s The edit was not made. The zone rules are in participant/context/zone-rules.md.\n" % explain(verdict))
        return 2
    except BaseException as failure:   # a guard that cannot decide refuses
        sys.stderr.write("zones: REFUSED. The zone check itself failed (%s), so the edit was not made.\n" % type(failure).__name__)
        return 2


def main(argv=None):
    parser = argparse.ArgumentParser(description="The ownership zones of this repository, as rules a tool applies.")
    parser.add_argument("--root", default=REPO, help="another folder laid out like the repository, for tests")
    commands = parser.add_subparsers(dest="command", required=True)
    where = commands.add_parser("where")
    where.add_argument("paths", nargs="+")
    write = commands.add_parser("write")
    write.add_argument("--to", required=True)
    write.add_argument("--text", required=True)
    commands.add_parser("audit")
    rules = commands.add_parser("rules")
    mode = rules.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    commands.add_parser("hook")
    args = parser.parse_args(argv)
    problem = root_problem(args.root)
    if problem:
        (sys.stderr if args.command == "hook" else sys.stdout).write("REFUSED: %s.\n" % problem)
        return 2 if args.command == "hook" else 1
    return {"where": cmd_where, "write": cmd_write, "audit": cmd_audit, "rules": cmd_rules, "hook": cmd_hook}[args.command](args)


if __name__ == "__main__":
    if "hook" in sys.argv[1:]:
        try:
            code = main()
        except BaseException:      # argparse leaving, or anything else: the hook's only answers are 0 and 2
            code = 2
        sys.exit(code if code in (0, 2) else 2)
    sys.exit(main())
