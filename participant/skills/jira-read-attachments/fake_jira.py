#!/usr/bin/env python3
"""A made-up Jira for tests and records. It holds ONE made-up story, DEMO-7, with made-up attachments, and answers the
requests `attachments.py` makes, in the shape the real Jira Cloud gives them:

    GET /rest/api/3/myself                              {"accountId": ..}
    GET /rest/api/3/issue/{key}?fields=attachment       {"id", "key", "fields": {"attachment": [{"id", "filename", "mimeType",
                                                         "size", "created", "author": {"accountId", "displayName"}, "content": url}]}}
    GET /rest/api/3/attachment/{id}                     one attachment's details, or 404
    GET /rest/api/3/attachment/content/{id}             the file's bytes. ONLY THIS MADE-UP JIRA IS EVER ASKED FOR THIS.

IT IS A MODEL, AND IT CAN BE WRONG ABOUT THE REAL JIRA. In particular a real Jira does not hand over a file's bytes
itself: it sends the asker on to another server. This model does not copy that, because the tool does not download
from a real Jira at all.

EVERY FILE HERE IS MADE UP, AND IS MADE BY THIS PROGRAM WHEN ASKED. None is a real program, archive or document. The
"archive" and the "program" are a few bytes that begin the way such files begin, followed by filler. The file that
sets off the scan holds the test string antivirus makers publish for exactly this purpose, built here from two
halves so that this source file does not itself contain it.

Some attachments tell the truth about themselves and some do not, so that each check can be shown:

    41001 release-notes.txt     text, 3 lines, by someone else         honest
    41002 export.csv            a small table, by "me"                 honest
    41003 diagram.png           a 1 by 1 picture                       honest
    41004 backup.zip            an archive                             a type that is not allowed
    41005 huge-log.txt          says it is 9 MB                        larger than the limit, by its own account
    41006 ../../.ssh/authorized_keys.txt                               a name that tries to climb out of the folder
    41007 notes.txt             says text; its bytes begin as an archive does
    41008 small.txt             says 200 bytes; sends 6 MB             larger than the limit, though it says not
    41009 report.pdf            a PDF that runs a script when opened   the scan
    41010 invoice.pdf.exe       says application/pdf                   its last extension is a program's
    41011 readme.txt            holds the antivirus test string        the scan
    41012 Quarterly Report (final) v2!.PDF   an honest PDF with an awkward name
    41013 photo.jpg             says image/jpeg; its bytes are a PNG   the type and the bytes disagree
    41014 data.json             says JSON; is not                      the bytes are not what the name says
    41015 short.txt             says 500 bytes; sends 40               fewer bytes than it said
    41016 ../JIRA/planted.txt   a name that points into a folder that really is there, beside the downloads folder

People are account ids that are made up: "acct-ana", "acct-ben" (the account that reads), "acct-cho".
"""
import argparse
import json
import os
import re
import sys

SITE = "https://jira.example.test"
KEY, IDENT, ME = "DEMO-7", "20007", "acct-ben"
PNG = bytes.fromhex("89504e470d0a1a0a0000000d4948445200000001000000010806000000" "1f15c4890000000d49444154789c6360000002000001e221bc330000000049454e44ae426082")
PDF = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF\n"
TEST_STRING = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$" + b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"


def content_of(ident):
    """The bytes of a made-up attachment, made when asked."""
    return {
        "41001": b"Made-up release notes.\nNothing here is real.\nLine three.\n",
        "41002": b"item,count\nmade-up widget,3\nmade-up gadget,5\n",
        "41003": PNG,
        "41004": b"PK\x03\x04" + b"\x00" * 600,
        "41005": b"made-up log line\n" * 20,
        "41006": b"made-up text with a hostile name\n",
        "41007": b"PK\x03\x04" + b"made-up bytes that begin as an archive does" + b"\x00" * 60,
        "41008": b"made-up filler line that goes on and on\n" * 157286,          # a little over 6 MB
        "41009": PDF.replace(b"/Type /Catalog", b"/Type /Catalog /OpenAction << /S /JavaScript /JS (app.alert('made up');) >>"),
        "41010": b"MZ" + b"\x00" * 58 + b"This program cannot be run in DOS mode. (made up)",
        "41011": b"A made-up readme.\n" + TEST_STRING + b"\n",
        "41012": PDF,
        "41013": PNG,
        "41014": b"this is not JSON at all {\n",
        "41015": b"forty bytes of made-up text, no more!!!\n",
        "41016": b"made-up text whose name points at a real neighbouring folder\n",
    }[ident]


def fresh():
    rows = [  # id, filename, mimeType, size said (None = the true size), author, created
        ("41001", "release-notes.txt", "text/plain", None, "acct-ana", "2026-11-02T09:15:00.000+0000"),
        ("41002", "export.csv", "text/csv", None, "acct-ben", "2026-11-03T14:40:00.000+0100"),
        ("41003", "diagram.png", "image/png", None, "acct-cho", "2026-11-04T08:05:00.000+0000"),
        ("41004", "backup.zip", "application/zip", 1258291, "acct-ana", "2026-11-05T16:20:00.000+0000"),
        ("41005", "huge-log.txt", "text/plain", 9437184, "acct-ana", "2026-11-06T11:00:00.000+0000"),
        ("41006", "../../.ssh/authorized_keys.txt", "text/plain", None, "acct-cho", "2026-11-06T12:00:00.000+0000"),
        ("41007", "notes.txt", "text/plain", None, "acct-cho", "2026-11-06T13:00:00.000+0000"),
        ("41008", "small.txt", "text/plain", 200, "acct-cho", "2026-11-06T14:00:00.000+0000"),
        ("41009", "report.pdf", "application/pdf", None, "acct-ana", "2026-11-07T09:00:00.000+0000"),
        ("41010", "invoice.pdf.exe", "application/pdf", None, "acct-cho", "2026-11-07T10:00:00.000+0000"),
        ("41011", "readme.txt", "text/plain", None, "acct-cho", "2026-11-07T11:00:00.000+0000"),
        ("41012", "Quarterly Report (final) v2!.PDF", "application/pdf", None, "acct-ben", "2026-11-07T12:00:00.000+0000"),
        ("41013", "photo.jpg", "image/jpeg", None, "acct-ana", "2026-11-07T13:00:00.000+0000"),
        ("41014", "data.json", "application/json", None, "acct-ana", "2026-11-07T14:00:00.000+0000"),
        ("41015", "short.txt", "text/plain", 500, "acct-ana", "2026-11-07T15:00:00.000+0000"),
        ("41016", "../JIRA/planted.txt", "text/plain", None, "acct-cho", "2026-11-07T16:00:00.000+0000"),
    ]
    return {"key": KEY, "id": IDENT, "me": ME, "asked": {"content": 0, "details": 0, "issue": 0, "myself": 0}, "contents_asked_for": [],
            "attachments": [{"id": i, "filename": name, "mimeType": kind, "size": len(content_of(i)) if said is None else said, "author": author, "created": created}
                            for i, name, kind, said, author, created in rows]}


class FakeJira:
    def __init__(self, data):
        self.data = data

    @classmethod
    def open(cls, path):
        with open(path, encoding="utf-8") as f:
            return cls(json.load(f))

    def save(self, path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=1)
            f.write("\n")

    def shaped(self, a):
        return {"id": a["id"], "filename": a["filename"], "mimeType": a["mimeType"], "size": a["size"], "created": a["created"],
                "author": {"accountId": a["author"], "displayName": "Made-up Person", "emailAddress": "made-up@example.invalid"} if a["author"] else None,
                "content": "%s/rest/api/3/attachment/content/%s" % (SITE, a["id"])}

    def get(self, path, params=None):
        if path == "/rest/api/3/myself":
            self.data["asked"]["myself"] += 1
            return 200, {}, {"accountId": self.data["me"], "displayName": "Made-up Person"}
        found = re.fullmatch(r"/rest/api/3/issue/([^/]+)", path)
        if found:
            self.data["asked"]["issue"] += 1
            if found.group(1).upper() not in (self.data["key"], self.data["id"]):
                return 404, {}, {"errorMessages": ["Issue does not exist or you do not have permission to see it."]}
            return 200, {}, {"id": self.data["id"], "key": self.data["key"], "fields": {"attachment": [self.shaped(a) for a in self.data["attachments"]]}}
        found = re.fullmatch(r"/rest/api/3/attachment/([0-9]+)", path)
        if found:
            self.data["asked"]["details"] += 1
            there = [a for a in self.data["attachments"] if a["id"] == found.group(1)]
            return (200, {}, self.shaped(there[0])) if there else (404, {}, {})
        return 404, {}, {}

    def content(self, ident):
        """(status, the bytes in pieces). The tool reads the pieces one at a time and may stop early."""
        self.data["asked"]["content"] += 1
        self.data["contents_asked_for"].append(ident)
        if not [a for a in self.data["attachments"] if a["id"] == ident]:
            return 404, iter(())
        whole = content_of(ident)
        return 200, (whole[at:at + 65536] for at in range(0, len(whole), 65536))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Make a fresh made-up Jira with one made-up story and its made-up attachments.")
    commands = parser.add_subparsers(dest="command", required=True)
    sub = commands.add_parser("new")
    sub.add_argument("--state", required=True)
    args = parser.parse_args(argv)
    os.makedirs(args.state, exist_ok=True)
    fake = FakeJira(fresh())
    fake.save(os.path.join(args.state, "fake-jira.json"))
    print("The made-up Jira has a fresh made-up story, %s, with %d made-up attachments." % (KEY, len(fake.data["attachments"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
