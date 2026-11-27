# Proof · jira-read-attachments

Attempt: `jira-attempt-021`

## How this was made

The participant made five decisions: to use a made-up Jira for every record and the real sandbox for a
metadata-only sync, so that no real file is downloaded; that the tool refuses a download from a real Jira; an
allowed list of types and a 5 MB limit; that "author" is kept as "me", "someone else" or "unknown", with no person
kept; and to do both stretch goals. The participant ran every command that reached the real Jira, in their own
terminal. An AI assistant (Claude) wrote the tool, the made-up Jira, the tests, the scripts and this file. Two
further AI assistants read the work, one of them as a security review. No person other than the participant has
read it.

## The short version

- **A sync records what is attached and fetches none of it.** Sixteen made-up attachments recorded; the made-up
  Jira's own count of requests for a file's contents is zero.
- **A download needs one attachment named by its identifier.** There is no "all".
- **Six checks before a byte is saved.** Seven downloads are refused in the record, by five of the six checks.
- **The name Jira gives is never used as a path.** The tool builds the name the file is saved under.
- **A file is saved only outside source control,** and every attempt is in a log with its identifier and time.
- **No real file was downloaded, and the tool refuses to download one.** Criteria 3 to 7 are shown on the made-up
  Jira only.
- **Both readers found that the first version could save a file with no line in the log,** and one got a download
  staged for commit. Both are closed. See below.

## My size and type limits (criterion 4)

**Size: 5 MB.** Enforced three times, because the size Jira states is a claim.

1. Before anything is fetched: the size Jira states must be within the limit.
2. While the bytes arrive: they are counted, and the fetch stops as soon as they pass the limit **or pass the size
   Jira stated**. The file that says 200 bytes and sends 6 MB is stopped at its first piece.
3. At the end: the number that arrived must be the number stated.

5 MB is enough for a screenshot, a log extract or a short PDF, which is what a person usually wants from a ticket.
It is too small for a database dump or a video, and that is the point: those should not arrive through this door.

**Type: a list of what IS allowed.** Text (`.txt`, `.md`, `.log`), CSV, JSON, PNG, JPG and PDF. Everything else is
refused without being named: archives, programs, scripts, office documents, web pages, SVG, and a name with no
extension. I chose a list of what is allowed over a list of what is forbidden because the second is only as good as
my imagination. The cost is that a Word document or a spreadsheet is refused.

Three things must agree:

| What | Where it comes from | Example of a refusal |
|---|---|---|
| The **last** extension of the name | Jira's name | `invoice.pdf.exe` is a program, whatever Jira says its type is |
| The type Jira states | Jira | `photo.jpg` stated as `text/plain` |
| How the file's own bytes begin | The file | `notes.txt` that begins the way a zip archive begins |

**The third looks at the beginning only.** A reader showed that a file can begin as a PNG and carry anything after
it, and that my output said "they are what a .png file is". It now says the file *begins* as one, and that what
follows was not examined. Text is different: it is checked all through.

## How I handle a hostile file name (criterion 6)

**Two things, and the second does not depend on the first.**

1. **A name that looks like an attack is refused.** A slash, a backslash, a `..`, a character that cannot be seen,
   a space or dot at its end, or more than 255 characters. `../../.ssh/authorized_keys.txt` is refused by the name
   check, before the file is asked for.
2. **Whatever the name, it is never used as a path.** The file is saved under a name the tool builds:
   the identifier, then up to 40 small letters, digits and dashes taken from Jira's name, then the allowed
   extension. `Quarterly Report (final) v2!.PDF` becomes `41012-quarterly-report-final-v2.pdf`.

So if the first check were ever wrong, the second still holds. A test takes the name check away and asks for the
attachment called `../JIRA/planted.txt`, where `JIRA` is a real folder beside the downloads folder. It is saved as
`41016-jira-planted.txt` in the downloads folder, and nothing appears in `JIRA`.

- The identifier is in the name, so two attachments called `notes.txt` do not share a file.
- A file already there is never written over. The file gets its name by a step that fails if the name is taken,
  however lately it was taken.
- The saved name does carry letters from Jira's name, and is printed and logged. My first description said Jira's
  name is never printed. A reader pointed out that this was not true in substance.

## The criteria, one by one

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Metadata is recorded for every attachment | Tested on the made-up Jira. **The real story had none** | `no-download-run.txt` part 1: for each of 16 identifiers the name, stated type and stated size are compared with the made-up Jira's, and who attached it is worked out again by the script. `attachments.md` |
| 2 | A normal sync writes no attachment file | Tested. Seen on the real Jira, for a story with no attachments | `no-download-run.txt`: the made-up Jira's own count of requests for contents is 0; the only new files in the folders watched are the index and its page. `live-sync-1.txt`: two requests, neither for a file |
| 3 | A download needs an explicit request naming the attachment | Tested on the made-up Jira only | `explicit-download-run.txt` part 2: the made-up Jira wrote down which identifier it was asked for: 41001, once. Part 11: `--id all` refused; no `--id`, no run |
| 4 | A disallowed type or an oversize file is refused with the reason | Tested on the made-up Jira only | Parts 4, 5, 9: refused by the type, by the stated size, and by the size as it arrived, each with its reason in the output and the log |
| 5 | A downloaded file is saved outside source control | Tested on the made-up Jira only | Part 1: where the two files went. Part 12: a folder inside this repository refused. Part 13: a folder Git ignores the contents of, with text files taken back, refused |
| 6 | The file name is never used as a path without being sanitized | Tested on the made-up Jira only | Part 3: the awkward name. Parts 6 and 7: two hostile names refused, one pointing at a folder that is really there, which stays empty of it |
| 7 | The download is recorded in a log with the identifier and time | Tested on the made-up Jira only | Part 2: the line for the saved file, with identifier, time, name on disk, size and checksum. Part 15: the whole log, ten lines |

## Where the important artifacts are

| Path | What it is |
|---|---|
| `participant/context/jira/attachments.md` | The index: sixteen made-up attachments. No file was downloaded to make it |
| `participant/context/jira/attachments.json` | The index that page is written from |
| `participant/skills/jira-read-attachments/attachments.py` | The tool: `sync`, `download` and `limits` |
| `participant/skills/jira-read-attachments/SKILL.md` | When to use it, and the rules for whoever uses it |
| `participant/skills/jira-read-attachments/fake_jira.py` | The made-up Jira and its made-up files |
| `participant/skills/jira-read-attachments/tests/test_attachments.py` | 104 tests |

Under `participant/evidence/jira-read-attachments/jira-attempt-021/`:

| Path | What it is |
|---|---|
| `logs/no-download-run.txt` | A normal sync: metadata recorded, no file fetched or written. 10 checks |
| `logs/explicit-download-run.txt` | One download that passes, one with an awkward name, seven refused, the log and a listing of files written. 49 checks |
| `logs/live-sync-1.txt`, `logs/live-sync-2.txt` | The real sandbox, metadata only, twice in a row, with the final tool |
| `logs/before-readers/` | The first real run, made with the tool **before** the fixes. Kept as it was |
| `logs/tests.txt`, `logs/planted-bugs.txt` | 104 tests passing; 84 planted bugs, each caught |
| `logs/independent-read.txt` | What the two AI readers found, and what was changed. Written by hand |
| `scripts/record_runs.py`, `scripts/planted_bugs.py` | What made the records |

The quest names the folder `attempt-001`. The application made `jira-attempt-021`. The two required records and this
file are copied to `participant/evidence/jira-read-attachments/attempt-001/`, with a note there saying so.

The two made-up files that were saved in the record were in a temporary folder outside the repository, and were
deleted with it. **No downloaded file is in this hand-in.**

## Stretch goals

- **A checksum for each downloaded file: done.** The SHA-256 of the bytes is in the log line and the output. In the
  record, the script takes the checksum of the saved file itself and compares.
- **A scan for known patterns before saving: done, and it is not antivirus.** A short list: the test string
  antivirus makers publish; a program or zip archive inside an allowed type; a private key; in a PDF, a script,
  something set to run or to send, or another file inside; in text, a script's first line, a script tag, a frame or
  a `javascript:` address; in a CSV, a cell that begins as a formula begins. A reader dodged the first version of it
  in a dozen ways. Many are closed. It still misses things, and the tool's own description lists some.

## How to reproduce the behavior

Python 3.9 or later and Git, with nothing installed. From the `participant` folder:

    cd skills/jira-read-attachments && python3 -m unittest tests.test_attachments
    python3 evidence/jira-read-attachments/jira-attempt-021/scripts/record_runs.py
    python3 skills/jira-read-attachments/attachments.py limits

The second command deletes `attachments.json` and `attachments.md` and makes them again. It saves two made-up files
in a temporary folder outside the repository and deletes that folder when it ends.

Against a real Jira, by a person, metadata only:

    python3 skills/jira-read-attachments/attachments.py sync --source live --issue SCRUM-1 \
        --out-dir ../local-data/jira-read-attachments --name scrum-1

## What was tested or validated

- **104 tests.** The index against the made-up Jira; that a sync reaches no file's bytes by any road; one download
  per command and no way to ask for more; each of eleven refusals, with its check and reason; that what Jira states
  is checked before the file is asked for; nineteen hostile names; the saved name for thirty-six awkward ones;
  folders inside repositories of four kinds; a log that is a link, a folder, a pipe, a second name or read-only; a
  file appearing under the saved name mid-fetch; a real connection that cannot ask for a file; a real server's
  refusals.
- **84 planted bugs,** each put into a copy of the tool and caught by at least one test. Among them: a sync that
  fetches a file; a file saved under the name Jira gave; a saved file left when its log line cannot be written.
  Five mistakes are not planted, with the reason, at the end of the record.
- **59 checks** in the two records.
- **Two metadata syncs of a real story,** two requests each, neither for a file.
- The project's secret scan, and a search for names and paths, over every file of this quest.

## What the independent readers found

Two AI readers, not people. The full account is in `logs/independent-read.txt`.

- **A file could be saved with no line in the log, and the output then said nothing was written.** Both found it.
  The line was written after the file. If the log was a link, a folder, a pipe or read-only, the file stayed and
  the line never came. Criterion 7 was not met in that case. **Now the log is opened before anything is asked of
  Jira, and a file whose line cannot be written is taken away again.**
- **The check for "outside source control" asked Git about a made-up file name.** A reader wrote a `.gitignore`
  that ignored that name and not the real file, and `git add` then staged the download. Criterion 5 was not met in
  that case. **Now Git is asked about the folder itself,** with its settings from the environment set aside, and a
  repository of another kind is refused.
- **Words that claimed more than was done:** "they are what a .png file is"; "every attempt is logged"; "Jira's name
  is never printed". Each was rewritten to say what is true.
- **The scan was dodged** by hidden marks in a PDF, a formula with a digit after its sign, a key inside a PDF, and
  more.
- **An index made from a real Jira said an attachment "could be asked for",** when a real download is always refused.
- **Sixteen mistakes the tests would not have noticed,** and **nine checks in the records that claimed more than they
  tested.** Two could not fail at all.
- **The test log held the home folder's path,** in a warning. The tests no longer leave files open, and it is gone.
- **Neither reader found** a way out of the downloads folder through a name, a way for a sync to fetch a file, or a
  way for a real connection to reach an attachment.
- **Neither reader saw the corrected version.**

## Remaining limitations

- **No real attachment has ever been seen by this tool.** The real story had none. The names of the fields a real
  attachment arrives with are my reading of Jira's interface, not something observed.
- **No real file has been downloaded, and the tool cannot download one.** A real Jira sends the asker on to another
  server for a file's bytes. That path is not built. Criteria 3 to 7 are shown on a model.
- **A private file passes every check.** A spreadsheet of customer data saved as CSV is the right type and a small
  size. The only protection is where it is saved, and that is a folder, not a lock.
- **The fifth check looks at how a picture or a PDF begins.** A file can begin rightly and carry something else.
- **The scan is a short list and is not antivirus.** It misses things, and it refuses some harmless files, such as a
  CSV with a cell that reads `- 4`, or a text file that happens to begin with the letters `MZ`.
- **"Outside source control" means** in no repository the tool can find, or in a folder Git ignores whole. A
  repository the tool does not know the marks of would not be found. For a live sync, `local-data` is matched by
  the folder's name, and Git is not asked.
- **Nothing in the tool can tell a person from an agent.** `--id` is the only gate. That a person must ask is a rule
  in SKILL.md, not something the code enforces.
- **A piece of a file is as large as the server makes it.** The fetch stops when the count passes the limit, and one
  very large piece would be in memory before it is counted.
- **The script that makes the records watches the folders it knows.** It would not see bytes written elsewhere on
  the disk.
- **Three refusals are not in the log,** because they come before there is a log: a refused downloads folder, a
  download from a real Jira, and a log that cannot be opened.
- **The live records have no command line or exit code in them.** The site fingerprint is a short, unsalted hash.

## Reflection

*Which attachment type would you never download automatically, and why?*

An archive. A zip file is the one type where nothing I can check before saving tells me what I am getting. Its
name, its type and its size describe the wrapper. Inside it can be a program, ten thousand files, a file that
unpacks to fill the disk, or a file whose own name climbs out of the folder it is unpacked in. Every check I built
for this quest looks at one file's name, one size and one beginning, and an archive has as many of each as it
likes, none of them visible until something opens it. That is the second reason: an archive is only useful if it is
opened, and opening is exactly what I decided this tool never does. So an archive is not on my list at all, and the
scan refuses a file that has one inside it. What I had not expected is how much of the danger was not in the file.
The first version could save a file and leave no record that it had, and it could be talked into saving one where
Git would pick it up, because I asked Git about a file name I had made up and not about the folder. Neither of
those is about a type. I would now say that "automatically" is the word that matters in the question: a person who
names one attachment, knows who attached it, and has it land somewhere it cannot be committed is a different act
from a sync that fetches whatever is there, whatever its type.

## Sensitive values

No token, password or cookie is in any file of this quest. The token was typed by the participant into their own
terminal and was not seen by the assistant. Every live output was searched for the token, the email address and their
encoded form before it was shown or anything was written, and the site's address is replaced by a marker in the
saved copies. No person is named: the tool keeps none. The real story had no attachments, so no real attachment's
name is anywhere; had there been any, the index would be in `local-data/`, which is not handed in. The antivirus
test string is not in any record or sample: the made-up Jira builds it from two halves when asked, and the file
holding it is refused before anything is written. The key SCRUM-1 and a short hash of the site's name do appear.
