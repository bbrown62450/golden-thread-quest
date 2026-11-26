# Proof · base-camp-ownership-zones

Attempt: `base-attempt-008`

## How this was made

The participant made one decision: that the zone check is also installed as a hook on this project's own agent, and
not only shown in a sandbox. The participant installed that hook, in their own terminal. An AI assistant (Claude)
wrote the rules, the tool, the tests, the scripts and this file, and ran them on the participant's computer. Two
further AI assistants read the work. No person other than the participant has read it.

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
- **"Every write the agent performs" is not met, and cannot be by this tool:** a shell command is not checked.

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

## The criteria, one by one

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | The rules name four zones, with folders, permitted writer and Git status | Tested | `participant/context/zone-rules.md`. `hook-and-audit.txt`, last part: the page is what the tool writes from its lists; Git is asked which top-level names it tracks and which it ignores, and the answers match the rules |
| 2 | Every write the agent performs is checked before it happens | **Met in part. Stated limit** | Checked: every `zones.py write`, and, with the hook installed, every use of the agent's four file-editing tools (`live-hook.txt`, `hook-and-audit.txt`). **Not checked: anything a shell command writes, or any other tool.** The order, check before write, is tested |
| 3 | A path that escapes, by `..` or a symbolic link, is refused | Tested | `refused-write.txt`, trials 3 to 8: two by `..`, three through links, one hard link |
| 4 | A refused write creates no file and no partial file, and says which rule | Tested | `refused-write.txt`: after each of fifteen refusals every name and byte in the sandbox is compared with before. Each output names its rule and gives the rule's words in full |
| 5 | A write inside a participant-owned folder succeeds with the same command | Tested | `allowed-write.txt`: the same command and text, another path. It is the only thing that changes |
| 6 | Another person can tell from the rules alone where a new file should go | Tried once by an AI reader, on the first version | Given only the rules, it placed eleven of sixteen kinds of file and could not decide two. Rows were added for those. **The corrected page has not been read, and no person has tried it** |

## Where the important artifacts are

| Path | What it is |
|---|---|
| `participant/context/zone-rules.md` | The rules. Generated: not edited by hand |
| `participant/tools/zones.py` | The tool: `where`, `write`, `audit`, `rules`, `hook` |
| `participant/tools/tests/test_zones.py` | 71 tests, all against a sandbox but five that only read the real repository |

Under `participant/evidence/base-camp-ownership-zones/base-attempt-008/`:

| Path | What it is |
|---|---|
| `logs/refused-write.txt` | Fifteen refused writes, with the sandbox listed before and after. 48 checks |
| `logs/allowed-write.txt` | The same write, allowed, and three more. 8 checks |
| `logs/hook-and-audit.txt` | The hook given made-up tool calls, `where`, the audit, and what Git says. 22 checks |
| `logs/live-hook.txt` | The installed hook refusing one real edit by the agent and allowing another. Written by hand |
| `logs/tests.txt`, `logs/planted-bugs.txt` | 71 tests passing; 35 planted bugs, each caught |
| `logs/independent-read.txt` | What the two AI readers found, and what was changed |
| `scripts/record_evidence.py`, `scripts/planted_bugs.py` | What made the records |

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

Every write in the tests and the records is aimed at a temporary sandbox, which is deleted. Nothing is deleted to
show a refusal.

## What was tested or validated

- **71 tests.** Allowed writes; refusals in every zone; `..`; links to folders, to files, to nothing, and in a loop;
  a hard link; the repository named by another spelling; a folder swapped for a link between the check and the
  write; the hook's answers to good, bad and unreadable calls; the audit; what Git says about the folders.
- **35 planted bugs,** each put into the tool and caught by at least one test. Among them: judging the path as
  written, taking the zone from the path as written, letting the agent write what steers it, and letting the hook
  answer with a code that Claude Code does not treat as a refusal. One was not caught at first and a test was added.
  One made the tool loop without end, which showed a loop with no stopping point; it has one now.
- **78 checks** in the three records.
- The project's secret scan, and a search for names and paths, over every file of this quest.

## What the independent readers found

Two AI readers, not people. The full account is in `logs/independent-read.txt`.

- **Reader 1** had only the rules. It found the page contradicting itself about credentials, a rule that could never
  be reached, and nothing said about whether a person is held to the same rules, what may be deleted, or that the
  agent could rewrite the tool. The page was corrected in each place.
- **Reader 2** found **two real ways past the first version**. The hook decided "not in the repository" by comparing
  text, so the repository's path spelt in other capitals was let through. And the tool's own file and the agent's
  settings were in the zone the agent may write, so one allowed edit could switch the guard off. It found eight
  smaller holes and several checks that tested less than their labels said. All were changed.
- **Neither reader saw the corrected versions.**

## Remaining limitations

- **A shell command is not checked.** This is the large one. The hook sees the four file-editing tools. A command
  such as `echo x > file`, or a script the agent runs, writes wherever it likes, the tool and the rules included.
  While building this quest the assistant changed files in `participant/` with shell commands. Nothing checked those
  but the participant reading `git status`.
- **The hook approves; Claude Code then writes.** A path changed in that moment is not checked again.
- **Deletes, renames and moves** are not checked.
- **The hook's last line of defence has no test of its own.** The command turns any answer of the hook but 0 into a
  refusal at the very end. Nothing before that line gives another answer unless it is itself broken, so no test can
  see the line work.
- **The planted-bug run makes the tool wrong on purpose while the hook is installed.** For those minutes the guard
  on the real agent is the broken tool. The agent did edit files in those minutes, this one among them, all inside
  `participant/`; those edits were checked by whatever the tool was at that moment.
- **The private-data zone is defined by place and by name.** A raw response pasted into a note, or a secret in a file
  with an ordinary name, is in the right zone by these rules and is still private. The tool cannot see contents.
- **Some harmless names are refused,** such as a presentation called `deck.key`.
- **Only the private-data zone was tried against the real repository.** No write was aimed at a real program-owned
  file. The other zones are shown in the sandbox.
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
to ask where each piece of text came from. The scan for secrets helps, and it also only knows shapes. What surprised
me was a different weakness: the guard itself. In my first version the tool and the agent's settings were in the
folder the agent may write, so the rules could be switched off by one edit that the rules allowed. And the hook only
watches the editing tools; anything done through a shell command goes round it, which is how much of this quest was
built. So what I really rely on a person for is the thing no rule of mine can check: reading `git status` and the
changed files, every time, and not trusting that a refusal I never saw means nothing was written.

## Sensitive values

No secret, token, password or cookie is in any file of this quest. The sandbox holds made-up files only, and is
deleted. No real private response is in the proof. The records show the sandbox as SANDBOX, and `live-hook.txt`
shows the home folder as HOME. The settings file that installs the hook holds the path to the tool and no credential;
it is ignored by Git and is not part of the hand-in.
