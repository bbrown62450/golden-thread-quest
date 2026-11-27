# Proof · base-camp-ownership-zones

Attempt: `base-attempt-008`

## How this was made

The participant made three decisions. Before the review: that the zone check is also installed as a hook on this
project's own agent, and not only shown in a sandbox. After the review: that the agent's shell is closed by a sandbox
kept by the operating system, and that `participant/` is the only place at the top where that shell may write. The
participant put the hook and each version of the sandbox settings in place by hand. An AI assistant (Claude) wrote
the rules, the tool, the tests, the scripts and this file, and ran them on the participant's computer. Three further
AI assistants read the work. No person other than the participant has read it.

**This is the second hand-in.** The first was returned with one blocking finding: shell commands went round the
check. The section "After the review" says what was done about it.

## The short version

- **The rules** name four zones, and for each its folders, who may write, and its Git status. They are written from
  the same lists the tool applies.
- **The tool** resolves a path first, then decides. One rule of eleven allows a write: inside `participant/`, and not
  a file the application writes, a file that steers the agent, or the tool itself.
- **Refused:** fifteen writes in a sandbox, among them the three the quest asks for. After all fifteen, every name and
  byte in the sandbox is what it was.
- **Allowed:** the same command, aimed at the participant's notes folder, succeeds and changes nothing else.
- **The hook is installed and live.** One edit by the agent in the real repository was refused and one was allowed.
- **A reader found two real ways past the first version.** Both are closed. See below.
- **The shell is now closed, by the operating system and not by the rules.** A shell write into `content/` was
  refused, with seventeen more like it. The shell can still write in `participant/`.
- **The first two lists of refused places were wrong.** A reader got past the first. My own check got past the
  second, and wrote about eleven stray files into the real repository doing it. They were removed at once.

## How the check handles a path that tries to leave the folder

**It never judges the path as written.** It works out where a write would really land, and judges that place.

1. **Make it absolute.** A relative path is taken from the repository's top, or, in the hook, from the folder the
   agent is working in.
2. **Resolve it.** Every `..` is worked out and every symbolic link is followed, links in the middle of the path and
   a link as the last name alike. A link whose target does not exist yet is followed too.
3. **Is that place inside the repository?** The check walks up from the place, folder by folder, until a folder *is*
   the repository's root: the same folder on the same disk. It does not compare text, so another spelling of the
   repository's path is still the repository. If the walk reaches the top of the disk without meeting the root, the
   place is outside, and the write is refused by rule R1.
4. **Which zone is that place in?** The zone of where it lands, not of how it began.
5. **Is there a file there with another name on the disk?** A hard link cannot be seen by resolving a path. If the
   file has more than one name, it is refused by rule R8.

| The path | What happens | Rule |
|---|---|---|
| `participant/context/../../../outside/escaped.txt` | Resolves outside the repository. Refused: "it uses `..` to climb out" | R1 |
| `participant/context/../../content/quests/new-quest.md` | Resolves to the curriculum. Refused: "as written it starts in the participant zone, and its `..` leads to" the curriculum | R10 |
| `participant/context/link-out/escaped.txt`, where `link-out` is a link to a folder outside | Refused: "it goes through a symbolic link that leads out of the repository" | R1 |
| `participant/context/link-to-curriculum/sample-quest.md` | Resolves to the curriculum. Refused: "a symbolic link on the way leads there" | R10 |
| a link to a file outside that does not exist yet | Refused. The file is not created | R1 |
| a second name, in the participant's folder, of a program file | Refused: "the file has 2 names on the disk" | R8 |
| `content/../participant/context/landed-here.md` | Resolves into the participant's folder. **Allowed**: it is judged by where it lands | R9 |
| a link in the participant's folder to another file in it | **Allowed.** The file it leads to is written, and the link is kept | R9 |

**A refusal creates nothing.** The check is made before any folder or file is created. A test replaces every way of
creating something with a recorder and confirms none is called. If the path changes between the check and the write,
the folders made for it are taken away again.

## A write that reached the real curriculum folder, during testing

**This happened, and the quest's safety rule against it was broken once.**

- One of my tests checked that the tool refuses to work on a folder inside the real repository. It did that by
  running a real `write` command aimed there, and trusting the tool to refuse.
- The planted-bug run then took that refusal out, on purpose, to see whether the tests would notice. With the
  refusal gone, the write went through. It created a 2-byte file, `content/participant/x.md`, in the program-owned
  zone of the real repository.
- It was found in the final check, as an untracked folder in `git status`. It had never been committed. The
  assistant deleted that one file and its empty folder, and Git then showed nothing changed outside `participant/`.
- **The fault was in the test, not in the tool as it stands.** A test must not prove a refusal by attempting the
  thing for real. The test now asks the tool what it thinks of such a root, and runs only a command that reads.
- The planted-bug run now asks Git, before and after, what it sees outside `participant/`, and fails if that changed.
- The stray folder also hid something. While it was there one test failed under every later planted bug, so two
  bugs in the hook's exit code looked caught when they were not. One has a test of its own now. The other is not
  planted any more: see the limitations.
- For a while the saved test log recorded that one failing test, and the assistant reported "70 tests pass" from the
  line that counts tests and not from the line that gives the result. That was corrected.

## After the review: the shell

**The finding.** "Not every write the agent makes is checked: shell commands bypass the zone check." It was true.

**What was decided.** The reviewer offered two ways: deny the shell, or add a hook that reads each command. The
participant chose a third, and I recommended it: run the shell inside a sandbox kept by the operating system.

- A hook that reads a command's text cannot know what a program does once it is running. `python3 x.py` says
  nothing about where `x.py` writes.
- The sandbox does not read the command. It refuses the write itself, whatever program makes it.
- Denying the shell outright would have closed the path too. The cost was every test run and record in this quest.

**What it is.** Claude Code's own sandbox for its shell, switched on in the participant's settings, with a list of
places the shell may not write. `zones.py sandbox` works that list out from the same lists the rules are written
from. `zones.py sandbox --check FILE` says whether a settings file has every place.

**What was shown, against the real repository** (`logs/shell-sandbox.txt`, 25 checks):

| What the shell tried | What happened |
|---|---|
| The harmless question first: open each of 18 protected files for writing, and write nothing | All 18 refused by the operating system. None changed |
| `echo x > content/...`, as the reviewer asked | "Operation not permitted". No file made |
| A Python program writing into `quest_app/`; `touch`, `mkdir`, `cp` | Refused. Nothing made |
| New files in `.git/`, `local-data/`, `generated/`, `.venv/`, an attempt's `validation/` | Refused |
| `.env`, a `.pem`, `CLAUDE.md` and a `.claude` folder inside `participant/` | Refused |
| A new file and a new folder at the top; `conftest.py`; a name that starts like `participant` | Refused |
| Renaming this attempt folder, and the quest folder above it | Refused |
| A file in this attempt's own `logs/` | **Written, read back, removed** |

Git lists the same files outside `participant/` after the run as before, ignored ones included.

**No real protected file was written, deleted or renamed to show a refusal.** Every attempt was to create a new
name, or to rename a folder and move it back if the rename went through. Deleting and renaming a protected *file*
were tried on made-up files outside the repository: `logs/sandbox-trials.txt`.

**It is not the rules.** The tool resolves a path and judges where it lands. The sandbox refuses listed places. The
rules page now has a table, rule by rule, of what the shell gets:

| Rule | For the shell |
|---|---|
| R10 program-owned, R6 generated, R5 private data | Refused, by name |
| R11 no zone | Refused at the top, by patterns for every name but `participant` |
| R7 the application's files | Refused. In each attempt folder, each file by its exact path |
| R3 what steers the agent, R2 a credential's name, R4 tool-managed names | Refused, by name, anywhere |
| R8 a hard link | Partly: one cannot be made to a refused file. A file that already has two names is not noticed |
| R1 outside the repository | Refused, except two temporary folders |
| R9 the participant's | Allowed |

**Three lists, and two of them were wrong.**

1. **The first** left rule R3's names writable inside `participant/`, left `.venv/` writable, and had not tried
   renaming. A third AI reader found all three. `.venv/` was an escape: the hook ran that Python.
2. **The second** said "every name but participant" with square brackets. The tests passed, because the tests held my
   own model of how a pattern matches. The real sandbox does not match brackets. I found out by creating files at
   the top of the real repository and expecting each to be refused. **About eleven were created.** I removed them
   at once. None was committed, and no existing file was touched.
3. **The third** uses `*` only: 467 patterns. Nineteen new names at the top were then tried, and all were refused.

That second failure is the same mistake as the one in the next section: a check that proves a refusal by attempting
the real thing. The recording script now asks the harmless question first, and stops if any file opens.

**What it costs.** The agent's shell can no longer run `make build` or `git fetch`: both write outside
`participant/`. The participant runs them. The agent also lost the two tools that run a command in the
participant's own terminal. The participant accepted both.

**The probe was also run outside the sandbox,** by the participant in their own terminal. Four protected files
opened for writing, unchanged (`logs/probe-outside-the-sandbox.txt`). So the refusals above come from the sandbox,
and not from the files being read-only.

## The criteria, one by one

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | The rules name four zones, with folders, permitted writer and Git status | Tested | `participant/context/zone-rules.md`. `hook-and-audit.txt`, last part: the page is what the tool writes from its lists; Git is asked which top-level names it tracks and which it ignores, and the answers match the rules |
| 2 | Every write the agent performs is checked before it happens | **Changed after the review. Both ways this agent writes are now stopped before the write, in two different ways. Stated limits** | **File edits: judged by the rules.** Every `zones.py write`, and every use of the four file-editing tools (`live-hook.txt`, `hook-and-audit.txt`). **Shell: refused by the operating system for listed places, and not judged by the rules** (`shell-sandbox.txt`, 25 checks). The list is worked out from the rules and compared with them in tests. **Not covered: a tool added to the agent from outside, other than the two denied by name** |
| 3 | A path that escapes, by `..` or a symbolic link, is refused | Tested | `refused-write.txt`, trials 3 to 8: two by `..`, three through links, one hard link |
| 4 | A refused write creates no file and no partial file, and says which rule | Tested | `refused-write.txt`: after each of fifteen refusals every name and byte in the sandbox is compared with before. Each output names its rule and gives the rule's words in full |
| 5 | A write inside a participant-owned folder succeeds with the same command | Tested | `allowed-write.txt`: the same command and text, another path. It is the only thing that changes |
| 6 | Another person can tell from the rules alone where a new file should go | Tried once by an AI reader, on the first version | Given only the rules, it placed eleven of sixteen kinds of file and could not decide two. Rows were added for those. **The corrected page has not been read, and no person has tried it** |

## Where the important artifacts are

| Path | What it is |
|---|---|
| `participant/context/zone-rules.md` | The rules. Generated: not edited by hand |
| `participant/tools/zones.py` | The tool: `where`, `write`, `audit`, `rules`, `hook`, and now `sandbox` |
| `participant/tools/zone_probe.py` | Asks whether a file can be opened for writing. Writes nothing |
| `participant/tools/tests/test_zones.py` | 84 tests, all against a sandbox but five that only read the real repository |

Under `participant/evidence/base-camp-ownership-zones/base-attempt-008/`:

| Path | What it is |
|---|---|
| `logs/refused-write.txt` | Fifteen refused writes, with the sandbox listed before and after. 48 checks |
| `logs/allowed-write.txt` | The same write, allowed, and three more. 8 checks |
| `logs/hook-and-audit.txt` | The hook given made-up tool calls, `where`, the audit, and what Git says. 22 checks |
| `logs/live-hook.txt` | The installed hook refusing one real edit by the agent and allowing another. Written by hand |
| `logs/shell-sandbox.txt` | **New.** The refused shell writes, against the real repository. 25 checks |
| `logs/sandbox-trials.txt` | **New.** The trials on made-up files, and the two lists that failed. Written by hand |
| `logs/probe-outside-the-sandbox.txt` | **New.** The probe run by the participant in their own terminal |
| `logs/planted-bugs-sandbox.txt` | **New.** 39 bugs planted in a copy of the new part of the tool, each caught |
| `logs/tests.txt` | 84 tests passing |
| `logs/planted-bugs.txt` | 35 planted bugs, each caught. From before the review: it cannot be run by the agent now |
| `logs/independent-read.txt` | What the three AI readers found, and what was changed |
| `scripts/record_evidence.py`, `scripts/planted_bugs.py` | What made the first records |
| `scripts/record_shell_sandbox.py`, `scripts/planted_bugs_sandbox.py` | **New.** What made the new ones |

The quest names the folder `attempt-001`. The application made `base-attempt-008`. The two required records and this
file are copied to `participant/evidence/base-camp-ownership-zones/attempt-001/`, with a note there saying so.

## Stretch goals

- **A check that fails when a file is in no zone: done.** `zones.py audit`. It passes on the real repository and
  fails, naming the file, when a stray file is put in the sandbox. It looks at the top of the repository: anything
  inside `participant/` is in the participant's zone by being there, so the audit cannot fail for it.
- **Report which zone a path belongs to: done.** `zones.py where PATH` gives the place it resolves to, the zone, who
  writes there, its Git status, and the rule that decides.

## How to reproduce the behavior

Python 3.9 or later, with nothing installed.

    cd participant/tools && python3 -m unittest discover -s tests
    python3 participant/evidence/base-camp-ownership-zones/base-attempt-008/scripts/record_evidence.py
    python3 participant/tools/zones.py where participant/context/notes.md content/x.md
    python3 participant/tools/zones.py audit

For the shell, on a Mac with Claude Code, and with a person to put the settings in place:

    python3 participant/tools/zones.py sandbox
    python3 participant/tools/zones.py sandbox --check .claude/settings.local.json
    python3 participant/evidence/base-camp-ownership-zones/base-attempt-008/scripts/record_shell_sandbox.py

The first prints the settings; a person merges them into `.claude/settings.local.json`. The third must be run by the
agent, in its own shell. Run in an ordinary terminal it stops at the harmless question, because there the files open.

Every write in the tests and the first three records is aimed at a temporary sandbox, which is deleted. Nothing is
deleted to show a refusal. The shell record is the exception: its attempts are aimed at the real repository, after
the harmless question, and each creates a new name or nothing.

## What was tested or validated

- **84 tests.** Thirteen are new, for the shell's list: about sixty paths the rules refuse must be refused by the list;
  paths the rules allow must be left alone; each named place must be on the list by its own name; a settings file
  with a switch off, a place missing, an extra allowed place or an unknown setting must fail the check.
- **39 planted bugs in the new part,** in a copy of the tool, each caught. Two were missed at first: with the named
  generated and private places left off, the patterns still covered them, so nothing failed. Since the patterns had
  already failed once for real, a test now requires each named place by its own name.
- **25 checks** in the shell record.
- **Before the review:** allowed writes; refusals in every zone; `..`; links to folders, to files, to nothing, and in a loop;
  a hard link; the repository named by another spelling; a folder swapped for a link between the check and the
  write; the hook's answers to good, bad and unreadable calls; the audit; what Git says about the folders.
- **35 planted bugs,** each put into the tool and caught by at least one test. Among them: judging the path as
  written, taking the zone from the path as written, letting the agent write what steers it, and letting the hook
  answer with a code that Claude Code does not treat as a refusal. One was not caught at first and a test was added.
  One made the tool loop without end, which showed a loop with no stopping point; it has one now.
- **78 checks** in the three first records. They were not made again: the tool's older parts did not change.
- The project's secret scan, and a search for names and paths, over every file of this quest.

## What the independent readers found

Three AI readers, not people. The full account is in `logs/independent-read.txt`.

- **Reader 1** had only the rules. It found the page contradicting itself about credentials, a rule that could never
  be reached, and nothing said about whether a person is held to the same rules, what may be deleted, or that the
  agent could rewrite the tool. The page was corrected in each place.
- **Reader 2** found **two real ways past the first version**. The hook decided "not in the repository" by comparing
  text, so the repository's path spelt in other capitals was let through. And the tool's own file and the agent's
  settings were in the zone the agent may write, so one allowed edit could switch the guard off. It found eight
  smaller holes and several checks that tested less than their labels said. All were changed.
- **Reader 3,** after the review, was given the first sandbox list and asked to get past it. It found rule R3's names
  writable inside `participant/`, `.venv/` writable, renaming untried, a check of the settings file that passed files
  it should not, labels that claimed more than they tested, and two tools that run a command outside the sandbox.
  All were changed.
- **No reader saw the corrected versions.** The second and third lists were checked by me, by trying, and the
  second failed.

## Remaining limitations

- **The shell is refused places. It is not judged by the rules.** A path is not resolved and judged. Inside
  `participant/` the shell writes what it likes, apart from the listed names. That is the zone the agent may write.
- **A new attempt folder is half protected.** Its four files cannot be written, but the folder can be renamed, until
  the settings are made again and the participant copies them. The check says so. That is after every quest started.
- **A name at the top beginning with an unusual character,** such as a space or an accented letter, is matched by no
  pattern, so the shell could create it.
- **The sandbox restricts writing, not reading.** The shell can read `local-data/` and a file named `.env`.
- **Other tools.** Two tools that run a command elsewhere are denied by name. A tool added to the agent from
  outside is covered by neither the hook nor the sandbox.
- **It is the app's sandbox, and one settings file on one computer.** I tried cases. I did not read how it is built,
  and a later version of the app may match patterns differently. Not tried on Linux or Windows.
- **The trials on made-up files were not recorded as they ran.** `logs/sandbox-trials.txt` is an account by hand.
- **The outside-the-sandbox probe was run once,** on four files, with an earlier wording of the probe's output.
- **The hook approves; Claude Code then writes.** A path changed in that moment is not checked again.
- **Deletes, renames and moves** are not checked by the hook. The sandbox refuses them, for the listed places.
- **The hook's last line of defence has no test of its own.** The command turns any answer of the hook but 0 into a
  refusal at the very end. Nothing before that line gives another answer unless it is itself broken, so no test can
  see the line work.
- **The first planted-bug run made the real tool wrong on purpose while the hook was installed.** For those minutes
  the guard on the real agent was the broken tool. The agent can no longer run it. The new run plants bugs in a copy.
- **The private-data zone is defined by place and by name.** A raw response pasted into a note, or a secret in a file
  with an ordinary name, is in the right zone by these rules and is still private. The tool cannot see contents.
- **Some harmless names are refused,** such as a presentation called `deck.key`.
- **No write was aimed at an existing program-owned file.** By the tool, the zones are shown in a temporary sandbox.
  By the shell, new names were tried in the real folders, and existing files were only asked the harmless question.
- **This kind of disk only.** Not tried on Linux or Windows. Two findings that depend on how the disk treats names
  were closed by reading, and one of them has no test.
- **The hook is in the participant's own settings on this computer.** Another copy of the repository has no hook
  until someone installs it there.

## Reflection

*Which of your four zones is hardest to enforce with a tool, and what do you rely on a person to catch?*

Private data. The other three are places: a file is in the curriculum, or in my folder, or in the built site, and a
tool can work out which by resolving the path. Private data is partly a place, `local-data/`, and partly a kind of
content, and the tool can only see the place and the name. It will refuse a file called `.env`. It will happily let a
raw response with real names in it be pasted into a note in my own folder, because that note is in the right zone,
and my hand-in then commits it. So for that zone I rely on a person, me, to read what changed before handing in and
to ask where each piece of text came from. The scan for secrets helps, and it also only knows shapes. The review
taught me the second thing I rely on a person for. My first hand-in said the shell was not checked, and the reviewer
was right to send it back. Closing it took three tries. A reader got past my first list. My own check got past the
second, and left stray files in the real repository, because the tests agreed with my idea of the sandbox and the
sandbox did not. So a guard is not shown by its tests passing. It is shown by trying the thing it is meant to stop,
carefully, and looking at what is on the disk afterwards. And the settings that hold all this are one file that only
I can change, which has to be made again after every quest I start. A tool cannot remind me to do that for it.
So I still read `git status` and the changed files, every time, and I do not trust a refusal I have not seen.

## Sensitive values

No secret, token, password or cookie is in any file of this quest. The sandbox holds made-up files only, and is
deleted. No real private response is in the proof. The records show the sandbox as SANDBOX, and `live-hook.txt`
shows the home folder as HOME. The settings file that installs the hook and the sandbox holds full paths on this
computer and no credential; it is ignored by Git and is not part of the hand-in. The shell record shows paths from
the repository's top only.
