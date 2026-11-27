#!/usr/bin/env python3
"""Runs the attachments tool against the made-up Jira and records what it printed. Makes two records in logs/:

    no-download-run.txt         a normal sync: every attachment's details recorded, and no file fetched or written
    explicit-download-run.txt   the limits; one explicit download that passes every check; one with an awkward name;
                                seven that are refused, by five of the six checks; a request for "all" refused; a
                                downloads folder inside a repository refused, two ways; a download from a real
                                Jira refused; the download log in full; and a listing of every file written

It also leaves the index where the quest asks for it: participant/context/jira/attachments.md, with the index it is
written from beside it, attachments.json. Both are deleted at the start, so that the sync below is a first sync.

Each command is run as a person would run it, from the `participant` folder, and its output is copied in whole.
JIRA is a temporary folder that holds the made-up Jira. DOWNLOADS is a temporary folder OUTSIDE ANY GIT REPOSITORY,
where a downloaded file is saved. Both are deleted afterwards, the two made-up files in DOWNLOADS with them.
NO REAL JIRA IS CONTACTED, and every file the made-up Jira serves is made up by it.

Every check reads the output or the folders. A record ends with RESULT: ALL CHECKS PASSED, or says which did not.

Run from anywhere:  python3 scripts/record_runs.py        Exit code 0 if every check passed, 1 if not.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ATTEMPT = os.path.dirname(HERE)
PARTICIPANT = os.path.abspath(os.path.join(ATTEMPT, "..", "..", ".."))
REPO = os.path.dirname(PARTICIPANT)
TOOL = "skills/jira-read-attachments/attachments.py"
FAKE = "skills/jira-read-attachments/fake_jira.py"
OUT = "context/jira"
NAME = "attachments"
LOG = "download-log.jsonl"
BAR = "-" * 78
sys.path.insert(0, os.path.join(PARTICIPANT, os.path.dirname(FAKE)))


def path_of(ending):
    return os.path.join(PARTICIPANT, OUT, NAME + ending)


def everything_under(folder):
    """{path from the folder: sha256} for every file in it and below."""
    out = {}
    for root, _, names in os.walk(folder):
        for name in names:
            path = os.path.join(root, name)
            with open(path, "rb") as f:
                out[os.path.relpath(path, folder)] = hashlib.sha256(f.read()).hexdigest()
    return out


class Record:
    def __init__(self, name, title, temp):
        self.name, self.temp, self.checks, self.failed = name, temp, 0, []
        self.jira, self.downloads = os.path.join(temp, "JIRA"), os.path.join(temp, "DOWNLOADS")
        self.lines = [title, "jira-read-attachments, attempt jira-attempt-021. Recorded by scripts/record_runs.py.",
                      "Read from the made-up Jira (skills/jira-read-attachments/fake_jira.py): one made-up story with 16 made-up attachments. No real Jira was contacted.",
                      "Commands are run from the `participant` folder. JIRA and DOWNLOADS are temporary folders outside the repository, deleted afterwards.", ""]

    def say(self, text=""):
        self.lines.append(text)

    def run(self, tool, arguments):
        real = [sys.executable, "-B", tool] + [a.replace("JIRA", self.jira).replace("DOWNLOADS", self.downloads) for a in arguments]
        done = subprocess.run(real, cwd=PARTICIPANT, capture_output=True, text=True, timeout=120)
        output = (done.stdout + done.stderr).replace(self.jira, "JIRA").replace(self.downloads, "DOWNLOADS")
        self.say("$ python3 %s %s" % (tool, " ".join(arguments)))
        self.say(BAR)
        self.lines += output.rstrip("\n").split("\n")
        self.say(BAR)
        self.say("exit code: %d" % done.returncode)
        return done.returncode, output

    def part(self, title):
        self.say("")
        self.say("=" * 78)
        self.say(title)

    def check(self, passed, what):
        self.checks += 1
        self.say("  %s %s" % ("ok  " if passed else "FAIL", what))
        if not passed:
            self.failed.append(what)

    def asked(self):
        with open(os.path.join(self.jira, "fake-jira.json"), encoding="utf-8") as f:
            return json.load(f)["asked"]

    def contents_asked_for(self):
        """The identifiers the made-up Jira was asked for the contents of, in order, as it wrote them down itself."""
        with open(os.path.join(self.jira, "fake-jira.json"), encoding="utf-8") as f:
            return json.load(f)["contents_asked_for"]

    def close(self):
        self.say("")
        self.say("RESULT: ALL CHECKS PASSED. %d checks." % self.checks if not self.failed else "RESULT: %d OF %d CHECKS FAILED: %s" % (len(self.failed), self.checks, "; ".join(self.failed)))
        with open(os.path.join(ATTEMPT, "logs", self.name), "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(self.lines) + "\n")
        print("%s: %s" % (self.name, self.lines[-1]))
        return not self.failed


def no_download(temp):
    import fake_jira
    r = Record("no-download-run.txt", "A normal sync: every attachment's details recorded, and no file fetched or written", temp)
    for ending in (".json", ".md"):
        if os.path.exists(path_of(ending)):
            os.unlink(path_of(ending))
    r.part("0. A FRESH MADE-UP STORY, AND AN EMPTY DOWNLOADS FOLDER. The index and its page were deleted first, so the sync below is a first sync.")
    r.run(FAKE, ["new", "--state", "JIRA"])
    os.makedirs(r.downloads)
    before_out, before_participant = everything_under(os.path.join(PARTICIPANT, OUT)), set(everything_under(PARTICIPANT))
    r.say("Files in DOWNLOADS: %d. Files in %s: %d." % (len(everything_under(r.downloads)), OUT, len(before_out)))

    r.part("1. THE SYNC")
    code, out = r.run(TOOL, ["sync", "--source", "fake", "--issue", "DEMO-7", "--out-dir", OUT, "--name", NAME, "--state", "JIRA"])
    with open(path_of(".json"), encoding="utf-8") as f:
        index = json.load(f)
    with open(path_of(".md"), encoding="utf-8") as f:
        page = f.read()
    made = {a["id"]: a for a in fake_jira.fresh()["attachments"]}
    got = {a["id"]: a for a in index["attachments"]}
    r.check(code == 0 and "RESULT: INDEX WRITTEN. 16 attachments recorded." in out, "exit code 0, and the output says 16 attachments were recorded")
    r.check(sorted(got) == sorted(made) and all((got[n]["name"], got[n]["stated_type"], got[n]["stated_size"]) == (made[n]["filename"], made[n]["mimeType"], made[n]["size"]) for n in made),
            "METADATA FOR EVERY ATTACHMENT (criterion 1): for each of the 16 identifiers the made-up Jira has, the index holds the name, type and size the made-up Jira states, compared one by one")
    r.check(all(got[n]["attached_by"] == ("me" if made[n]["author"] == fake_jira.ME else "someone else") and re.fullmatch(r"2026-11-0[2-7]T[0-9:]{8}Z", got[n]["attached"]) for n in made),
            "and for each, who attached it, as \"me\" or \"someone else\", worked out again here from the made-up Jira's accounts, and a date in UTC")
    rows = [line for line in page.split("\n") if re.match(r"\| 4[0-9]{4} \|", line)]
    r.check(len(rows) == 16 and all(any(row.startswith("| %s | `%s` | `%s` |" % (n, made[n]["filename"], made[n]["mimeType"])) for row in rows) for n in made),
            "the page has one row for each of the 16, beginning with its identifier, the name the made-up Jira gives it, and the stated type")
    r.check(not any(word in json.dumps(index) + page + out for word in ("acct-", "Made-up Person", "example.invalid", "displayName")),
            "no account, name or email address of a person is in the index, the page or the output: four words the made-up Jira sends were looked for")
    asked = r.asked()
    r.say("  note What the made-up Jira counted being asked for: %s" % json.dumps(asked, sort_keys=True))
    r.check(asked["content"] == 0 and asked["details"] == 0 and asked["issue"] == 1 and asked["myself"] == 1,
            "NO FILE WAS ASKED FOR (criterion 2): the made-up Jira's own count of requests for a file's contents is 0, and for one attachment's details 0. "
            "The made-up Jira keeps that count; it is not a line the tool prints. It would not see bytes fetched some other way: the two checks below look for those on disk")
    after_out = everything_under(os.path.join(PARTICIPANT, OUT))
    new = sorted(set(after_out) - set(before_out))
    r.check(new == [NAME + ".json", NAME + ".md"] and all(after_out[k] == v for k, v in before_out.items()),
            "NO ATTACHMENT FILE WAS WRITTEN: in %s the only new files are the index and its page, and every file that was there has the checksum it had" % OUT)
    r.check(everything_under(r.downloads) == {} and set(everything_under(PARTICIPANT)) - before_participant == {os.path.join(OUT, NAME + ".json"), os.path.join(OUT, NAME + ".md")}
            and sorted(everything_under(temp)) == [os.path.join("JIRA", "fake-jira.json")],
            "DOWNLOADS is still empty; in the whole `participant` folder the only new files are those two; and the temporary folder holds the made-up Jira's own file and nothing else. "
            "Those are the places this script can watch. It does not watch the rest of the disk")
    r.check("Requests that ask for a file's contents: 0." in out and "/content/" not in out, "the tool's own output says the same")

    r.part("2. THE SAME SYNC AGAIN")
    sums = everything_under(os.path.join(PARTICIPANT, OUT))
    code, out = r.run(TOOL, ["sync", "--source", "fake", "--issue", "DEMO-7", "--out-dir", OUT, "--name", NAME, "--state", "JIRA"])
    r.check(code == 0 and "RESULT: INDEX UNCHANGED" in out and everything_under(os.path.join(PARTICIPANT, OUT)) == sums and r.asked()["content"] == 0,
            "nothing was written, every checksum in the folder is the same, and still no file's contents were asked for")
    r.say("")
    r.say("WHAT THIS DOES NOT SHOW. What a real Jira sends for a story's attachments. That is one real run, of this command only.")
    return r.close()


def explicit_download(temp):
    import fake_jira
    r = Record("explicit-download-run.txt", "Explicit downloads: one that passes every check, and others that are refused", temp)
    dl = lambda number: ["download", "--source", "fake", "--issue", "DEMO-7", "--id", number, "--downloads", "DOWNLOADS", "--state", "JIRA"]       # noqa: E731

    def log_now():
        path = os.path.join(r.downloads, LOG)
        if not os.path.exists(path):
            return []
        with open(path, encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    r.part("0. THE LIMITS, as the tool states them")
    code, out = r.run(TOOL, ["limits"])
    r.check(code == 0 and "at most 5.0 MB" in out and all("  ." + e in out for e in ("csv", "jpg", "json", "md", "pdf", "png", "txt")), "the size limit and the allowed types are printed")

    r.part("1. WHERE DOWNLOADS GO. DOWNLOADS is a temporary folder. This script asks Git about it, itself.")
    asked = subprocess.run(["git", "-C", r.downloads, "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    r.say("$ git -C DOWNLOADS rev-parse --show-toplevel")
    r.say("  exit code %d: %s" % (asked.returncode, "Git says this folder is in no repository" if asked.returncode != 0 else "GIT SAYS IT IS IN A REPOSITORY"))
    r.say("  note This is about the folder this script made, and could not have come out otherwise. It shows where the files below are saved (criterion 5).")
    r.say("       That the TOOL refuses a folder inside a repository is parts 12 and 13.")
    if asked.returncode == 0 or os.path.realpath(r.downloads).startswith(os.path.realpath(REPO) + os.sep):
        r.check(False, "the downloads folder this script made is inside a repository")
    r.check(everything_under(r.downloads) == {}, "DOWNLOADS is empty to begin with")

    r.part("2. ONE EXPLICIT DOWNLOAD THAT PASSES: attachment 41001, named by its identifier.")
    before_requests = r.asked()["content"]
    code, out = r.run(TOOL, dl("41001"))
    files = everything_under(r.downloads)
    want = hashlib.sha256(fake_jira.content_of("41001")).hexdigest()
    r.check(code == 0 and "RESULT: SAVED. One file, after six checks, and its line is in the log." in out and out.count("passed:") == 6
            and all("%d. " % n in out for n in range(1, 7)), "exit code 0; each of the six numbered checks says passed (the size and the type among them)")
    r.check(sorted(files) == ["41001-release-notes.txt", LOG] and files.get("41001-release-notes.txt") == want,
            "SAVED: DOWNLOADS now holds one file besides the log, and its SHA-256 is that of the bytes the made-up Jira serves for 41001, taken by this script")
    saved = [name for name in files if name != LOG]
    r.check(len(saved) == 1 and re.fullmatch(r"41001-[a-z0-9]+(-[a-z0-9]+)*\.txt", saved[0]) is not None and os.stat(os.path.join(r.downloads, saved[0])).st_mode & 0o777 == 0o600,
            "the name of the file found in DOWNLOADS is the identifier, plain small letters and dashes, and the allowed extension; it is readable by its owner only and is not marked as a program")
    entry = log_now()[-1] if log_now() else {}
    r.check(entry.get("attachment") == "41001" and entry.get("outcome") == "saved" and entry.get("sha256") == want and entry.get("bytes") == 57
            and re.fullmatch(r"20[0-9]{2}-[0-9]{2}-[0-9]{2}T[0-9:]{8}Z", entry.get("time", "")) is not None and entry.get("saved_as") == "41001-release-notes.txt",
            "THE LOG (criterion 7): its last line has the identifier 41001, a time, the outcome, the name on disk, the size and the same checksum")
    r.check(r.asked()["content"] == before_requests + 1 and r.contents_asked_for() == ["41001"],
            "AN EXPLICIT REQUEST (criterion 3): the made-up Jira wrote down which identifiers it was asked for the contents of. The list is: 41001, once, the one named")

    r.part("3. AN AWKWARD NAME, SANITIZED: attachment 41012, which Jira calls \"Quarterly Report (final) v2!.PDF\".")
    code, out = r.run(TOOL, dl("41012"))
    r.check(code == 0 and "41012-quarterly-report-final-v2.pdf" in everything_under(r.downloads), "saved as 41012-quarterly-report-final-v2.pdf: no space, bracket, capital or mark from the name Jira gave (criterion 6)")
    r.check("the file BEGINS the way a .pdf file begins. Only its beginning was looked at" in out, "the output says the fifth check looked at how the file begins, and no further")

    refused = [("41004", "the type", "not on the allowed list", "A TYPE THAT IS NOT ALLOWED: attachment 41004, an archive.", False),
               ("41005", "the size", "Jira states a size of 9.0 MB, and the limit is 5.0 MB", "TOO LARGE BY ITS OWN ACCOUNT: attachment 41005, which Jira states is 9 MB.", False),
               ("41006", "the name", "the name has a path in it", "A HOSTILE NAME: attachment 41006, which Jira calls \"../../.ssh/authorized_keys.txt\".", False),
               ("41016", "the name", "the name has a path in it", "A HOSTILE NAME THAT POINTS AT A FOLDER WHICH IS REALLY THERE: attachment 41016, called \"../JIRA/planted.txt\". JIRA is beside DOWNLOADS.", False),
               ("41007", "what the bytes are", "begins the way an archive", "A FILE THAT IS NOT WHAT ITS NAME SAYS: attachment 41007, named as text, whose bytes begin as an archive does.", True),
               ("41008", "the size", "more arrived than the 200 bytes Jira stated", "A FILE THAT IS LARGER THAN IT SAID: attachment 41008, stated as 200 bytes, which sends over 6 MB.", True),
               ("41009", "the scan", "the PDF has", "A FILE THE SCAN STOPS: attachment 41009, an honest PDF by name, type and first bytes, that runs a script when opened.", True)]
    for number, (ident, check, words, title, fetched) in enumerate(refused, 4):
        r.part("%d. %s" % (number, title))
        before_files, before_asked, before_log = everything_under(r.downloads), r.asked()["content"], len(log_now())
        code, out = r.run(TOOL, dl(ident))
        after = everything_under(r.downloads)
        r.check(code == 2 and "REFUSED by %s: " % check in out and words in out and "RESULT: NOT SAVED." in out and "SAVED as" not in out,
                "REFUSED WITH THE REASON (criterion 4): exit code 2, refused by %s, and the output gives the reason: \"%s\"" % (check, words))
        r.check(sorted(after) == sorted(before_files) and all(after[k] == v for k, v in before_files.items() if k != LOG),
                "nothing was saved: DOWNLOADS holds the same files as before, with the same checksums, apart from one more line in the log")
        entry = log_now()[-1]
        r.check(len(log_now()) == before_log + 1 and (entry["attachment"], entry["outcome"], entry["check"], entry["saved_as"]) == (ident, "refused", check, None) and words[:20] in entry["reason"],
                "the refusal is in the log, with the identifier, a time, the check that refused it and the reason")
        r.check(r.asked()["content"] == before_asked + (1 if fetched else 0),
                "the made-up Jira was asked for the file's contents" if fetched else "the made-up Jira was NOT asked for the file's contents: what it stated was enough to refuse")
    r.say("")
    r.check(sorted(os.listdir(r.jira)) == ["fake-jira.json"] and sorted(os.listdir(temp)) == ["DOWNLOADS", "JIRA"],
            "THE HOSTILE NAMES WROTE NOTHING (criterion 6): the folder JIRA, which \"../JIRA/planted.txt\" points at from DOWNLOADS and which is really there, holds its one own file and no `planted.txt`; "
            "and the temporary folder holds DOWNLOADS and JIRA and nothing else")
    r.say("  note The other hostile name points two levels up at a folder that does not exist, so by itself it could not have shown much: a write there would have failed anyway.")

    r.part("11. THERE IS NO WAY TO ASK FOR MORE THAN ONE. `--id all`, and no --id at all.")
    before_files, before_ids = everything_under(r.downloads), r.contents_asked_for()
    code, out = r.run(TOOL, dl("all"))
    r.check(code == 1 and "--id is ONE attachment's identifier" in out and r.contents_asked_for() == before_ids and log_now()[-1]["attachment"] == "all" and log_now()[-1]["outcome"] == "refused",
            "`--id all` is refused with exit code 1, no file's contents were asked for, and the attempt is in the log")
    code, out = r.run(TOOL, ["download", "--source", "fake", "--issue", "DEMO-7", "--downloads", "DOWNLOADS", "--state", "JIRA"])
    after = everything_under(r.downloads)
    r.check(code == 2 and "--id" in out and r.contents_asked_for() == before_ids and sorted(k for k in after if k != LOG) == sorted(k for k in before_files if k != LOG),
            "with no --id the command does not run at all (the usage message), and nothing was asked for or saved (criterion 3)")

    r.part("12. A DOWNLOADS FOLDER INSIDE THIS REPOSITORY, where Git would pick the file up: refused.")
    before_tree = set(everything_under(PARTICIPANT))
    before_asked = r.asked()
    code, out = r.run(TOOL, ["download", "--source", "fake", "--issue", "DEMO-7", "--id", "41001", "--downloads", OUT, "--state", "JIRA"])
    r.check(code == 1 and "Git does not ignore that folder as a folder" in out and set(everything_under(PARTICIPANT)) == before_tree and r.asked() == before_asked,
            "refused with exit code 1; no file was added anywhere in `participant`; and the made-up Jira was asked nothing")

    r.part("13. A FOLDER GIT IGNORES THE CONTENTS OF, WITH TEXT FILES TAKEN BACK. A reader got a file committed this way from the first version.")
    repo = os.path.join(temp, "REPO")
    os.makedirs(os.path.join(repo, "dl"))
    subprocess.run(["git", "init", "-q", repo], check=True, capture_output=True)
    with open(os.path.join(repo, ".gitignore"), "w", encoding="utf-8") as f:
        f.write("dl/*\n!dl/*.txt\n")
    r.say("A temporary Git repository, REPO, made by this script, with a .gitignore of two lines:  dl/*  and  !dl/*.txt")
    probe = subprocess.run(["git", "-C", repo, "check-ignore", "-q", "--", "dl/probe"], capture_output=True).returncode
    r.say("$ git -C REPO check-ignore dl/probe      exit code %d: Git %s a file called `probe` there, which is what the first version asked about" % (probe, "ignores" if probe == 0 else "does not ignore"))
    code, out = r.run(TOOL, ["download", "--source", "fake", "--issue", "DEMO-7", "--id", "41001", "--downloads", "JIRA/../REPO/dl", "--state", "JIRA"])
    r.check(probe == 0 and code == 1 and "does not ignore that folder as a folder" in out and os.listdir(os.path.join(repo, "dl")) == [] and r.asked() == before_asked,
            "Git does ignore `dl/probe`, and the tool still refuses the folder: it asks about the folder itself. Nothing was saved in it, and the made-up Jira was asked nothing")
    shutil.rmtree(repo)

    r.part("14. A DOWNLOAD FROM A REAL JIRA: refused. No connection is made, so no credentials are needed to show it.")
    before_files = everything_under(r.downloads)
    code, out = r.run(TOOL, ["download", "--source", "live", "--issue", "DEMO-7", "--id", "41001", "--downloads", "DOWNLOADS"])
    r.check(code == 1 and "a download from a real Jira is not something this tool does" in out and "Nothing was asked of Jira" in out and everything_under(r.downloads) == before_files,
            "refused with exit code 1, saying nothing was asked of Jira; DOWNLOADS is unchanged, the log included")

    r.part("15. THE DOWNLOAD LOG, whole, as it stands in DOWNLOADS/%s" % LOG)
    with open(os.path.join(r.downloads, LOG), encoding="utf-8") as f:
        raw = f.read().rstrip("\n").split("\n")
    r.lines += raw
    entries = log_now()
    r.check([(e["attachment"], e["outcome"]) for e in entries] == [("41001", "saved"), ("41012", "saved")] + [(i, "refused") for i, _, _, _, _ in refused] + [("all", "refused")],
            "ten lines, in the order the ten attempts were made: two saved, eight refused. The refusals in parts 12, 13 and 14, and the command with no --id, came before there was "
            "a log to write to, and are not in it")
    r.check(all(re.fullmatch(r"20[0-9]{2}-[0-9]{2}-[0-9]{2}T[0-9:]{8}Z", e["time"]) and e["attachment"] for e in entries), "every line has an identifier and a time")
    r.check(not any(name in "\n".join(raw) for name in ("Quarterly Report (final) v2!.PDF", "../../.ssh/authorized_keys.txt", "../JIRA/planted.txt", "authorized_keys", "planted")),
            "the log does not hold the names Jira gave the hostile or the awkward files. It does hold the names files were SAVED under, which carry letters taken from Jira's names")

    r.say("")
    r.say("  note The identifiers the made-up Jira wrote down being asked for the contents of, over the whole of this record: %s" % ", ".join(r.contents_asked_for()))
    r.check(r.contents_asked_for() == ["41001", "41012", "41007", "41008", "41009"], "five: the two that were saved, and the three whose fault is inside the file. For the other five attempts the contents were never asked for")

    r.part("16. EVERY FILE IN DOWNLOADS, listed by this script")
    final = everything_under(r.downloads)
    for name in sorted(final):
        path = os.path.join(r.downloads, name)
        r.say("  %-40s %8d bytes   mode %o   sha256 %s" % (name, os.path.getsize(path), os.stat(path).st_mode & 0o777, final[name][:16]))
    r.check(sorted(final) == ["41001-release-notes.txt", "41012-quarterly-report-final-v2.pdf", LOG], "three files: the two that were saved, and the log. Nothing from the eight refused attempts, and no temporary file")
    r.check(all(os.stat(os.path.join(r.downloads, name)).st_mode & 0o111 == 0 for name in final), "none is marked as a program")
    r.say("")
    r.say("WHAT THIS DOES NOT SHOW. A download from a real Jira: this tool refuses one. The scan is a short list of patterns and not antivirus.")
    r.say("DOWNLOADS is deleted when this script ends, the two made-up files with it.")
    return r.close()


def main():
    temp = os.path.realpath(tempfile.mkdtemp(prefix="gtq-attachments-record-"))
    try:
        ok = [no_download(temp), explicit_download(temp)]
    finally:
        shutil.rmtree(temp, ignore_errors=True)
    return 0 if all(ok) else 1


if __name__ == "__main__":
    sys.exit(main())
