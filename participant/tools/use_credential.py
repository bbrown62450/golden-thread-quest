#!/usr/bin/env python3
"""Uses a credential from the environment without ever printing it. For the quest base-camp-secret-handling.

    use_credential.py call [--verbose] [--rejected] [--crash]     use the credential against a made-up service
    use_credential.py scan PATH [PATH ...]                          look for one more shape of credential in files

THE CREDENTIAL COMES FROM ONE PLACE: the environment variable GTQ_DEMO_TOKEN. There is no option that takes it on the
command line, where it would be kept in the shell's history and shown to every program that lists processes. There
is no option that reads it from a file. If the variable is not set, the command refuses.

THIS IS A DEMONSTRATION, AND IT TAKES ONLY A MADE-UP VALUE. The value must contain the word "example". Anything else
is refused before it is used, so that a real credential is never put through it by mistake. The service it calls is
made up and lives inside this file: nothing is sent anywhere.

HOW THE VALUE IS KEPT OUT OF THE OUTPUT. Not by remembering not to print it. The value is read, and its forms are
written down, BEFORE the command line is even looked at. From then on every line this program writes goes through
one function, `masked`, which replaces the value wherever it appears: as it is, URL-encoded, and base64-encoded
alone or after "name:", as a sign-in header holds it. That covers the places a credential usually escapes:

    --verbose    the request is printed with its headers, as a debugging switch would
    --rejected   the made-up service refuses the credential and, as careless services do, repeats it in its error
    --crash      the program fails with an error whose message holds the credential, and the error is reported

A masked value is shown as [REDACTED], the marker the program's own tools use, so that the program's scanner does not
take a masked line for a leak. The length of the credential is said once, on the first line, and nothing else about it.

A COMMAND LINE THAT IS NOT UNDERSTOOD IS NEVER REPEATED. Python's usual complaint quotes back what was typed, such as
"unrecognized arguments: --token VALUE". If someone gave a credential on the command line by mistake, that complaint
would print it, and no mask could know it was one. So this program says only that the command was not understood.

WHAT MASKING BY VALUE CANNOT DO
    It replaces the value it was given. It does not know a credential it was not told about, such as one the service
    sends back, or one typed on the command line.
    It does not see a value that has been changed in a way it does not try: cut in two across lines, reversed,
    hashed, encoded some other way, or with only part of it printed.
    It can give the value away by what is missing. If the value were a piece of text this program prints anyway, the
    [REDACTED] in the middle of a familiar line would show what it was. A real credential is not such a piece of text.
    It covers what THIS program prints. A program started by this one, or a library that writes to the screen by
    itself, is not covered.

`scan` is a second pattern beside the program's own scanner, tools/secret_scan.py, which this file does not change
and does not replace. The program's scanner knows a Trello token. It does not know a bare Trello API KEY, which is
32 small hex characters with no prefix. `scan` reports such a run on a line that also says "trello", or that names a
key: a field whose name ends in "key" followed by : or =, or the option --key. It prints where, and never the value.
    It misses a key in capitals, a key whose name is on another line, and a key cut in two.
    It reports things that are not keys: an MD5 checksum on such a line, and the 32-hex hashes Trello itself puts in
    the addresses of pictures. It sees a shape, not a meaning.
A folder is looked into, file by file. A path that cannot be read is reported and counts as a failure: a file that was
not looked at is not passed as clean.

Exit codes. call: 0 used; 1 refused, or the service refused; 2 the command was not understood; 3 the program failed.
            scan: 0 nothing found; 1 found, or a path could not be read; 2 the command was not understood.
"""
import argparse
import base64
import os
import re
import sys
import traceback
import urllib.parse

VARIABLE = "GTQ_DEMO_TOKEN"
ACCOUNT = "demo-user"      # the made-up account name the made-up service signs in
SECRETS = []               # every form of the value that must not be printed. Filled in before anything else is done
MARKER = "[REDACTED]"
SHORTEST = 20              # a value shorter than this is refused, and is not masked: see read_credential

TRELLO_KEY = re.compile(r"(?<![0-9A-Za-z])([0-9a-f]{32})(?![0-9A-Za-z])")
KEY_NAMED = re.compile(r"""(?i)(?:[A-Za-z0-9_-]*key["']?\s*[:=]|--(?:[a-z0-9-]*-)?key\b)""")


def forms_of(value):
    """The value, and the other shapes it takes when it is put in a web address or a sign-in header."""
    raw = value.encode("utf-8", "surrogateescape")       # a value that is not proper text is still a value
    paired = ("%s:" % ACCOUNT).encode("ascii") + raw
    encodings = [value, urllib.parse.quote_from_bytes(raw, safe=""), urllib.parse.quote_from_bytes(raw, safe="/"), urllib.parse.quote_plus(raw),
                 base64.b64encode(raw).decode("ascii"), base64.b64encode(paired).decode("ascii"),
                 base64.urlsafe_b64encode(raw).decode("ascii"), base64.urlsafe_b64encode(paired).decode("ascii")]
    encodings += [e.lower() for e in encodings[1:4]]     # percent-escapes are also written in small letters
    return sorted(set(e for e in encodings if e), key=len, reverse=True)     # longest first, so no form is cut by a shorter one


def remember(value):
    SECRETS[:] = sorted(set(SECRETS + forms_of(value)), key=len, reverse=True)


def masked(text):
    for secret in SECRETS:
        text = text.replace(secret, MARKER)
    return text


def say(text="", stream=None):
    (stream or sys.stdout).write(masked(str(text)) + "\n")


def report_failure(kind, error, trace):
    """What Python would print for an uncaught error, printed through the mask."""
    say("THE PROGRAM FAILED. What Python reported, with the credential masked:", sys.stderr)
    for line in "".join(traceback.format_exception(kind, error, trace)).rstrip("\n").split("\n"):
        say("  " + line, sys.stderr)


def masked_excepthook(kind, error, trace):
    report_failure(kind, error, trace)
    sys.exit(3)


class QuietParser(argparse.ArgumentParser):
    """A parser that never repeats what was typed."""

    def error(self, message):
        say("REFUSED: the command line was not understood. What was typed is not repeated here, in case part of it was a", sys.stderr)
        say("credential. A credential is never given on the command line. Run with --help to see what is accepted.", sys.stderr)
        raise SystemExit(2)


class MadeUpService:
    """Stands in for a service that takes a bearer credential. It is careless on purpose: when it refuses, its error
    repeats the header it was sent."""

    def __init__(self, good):
        self.good = good

    def get(self, path, headers):
        sent = headers.get("Authorization", "")
        if sent != "Bearer " + self.good:
            return 401, {"error": "the credential in the header '%s' is not valid for %s" % (sent, path)}
        return 200, {"account": ACCOUNT, "items": 3}


def load_credential():
    """Reads the variable and writes down every form of its value, so that nothing after this can print it.
    A value too short to be a credential is not written down: masking it would punch holes in ordinary text, and
    the holes would give it away. It is refused later with words that do not depend on it."""
    value = os.environ.get(VARIABLE)
    if value and len(value) >= SHORTEST:
        remember(value)
    return value


def check_credential(value):
    """True if the value may be used. Otherwise says why not, in words that hold nothing of the value."""
    if not value:
        say("REFUSED: the environment variable %s is not set. A credential comes from the environment, set by hand" % VARIABLE)
        say("for the session. It is never given on the command line and never read from a file.")
        return False
    if len(value) < SHORTEST or any(ch.isspace() for ch in value):
        sys.stdout.write("REFUSED: the value of %s is shorter than %d characters or has a space in it. Nothing was done with it.\n" % (VARIABLE, SHORTEST))
        return False
    if "example" not in value.lower():
        say("REFUSED: the value of %s does not contain the word \"example\". This demonstration takes a made-up value" % VARIABLE)
        say("only, so that a real credential is never put through it. Nothing was done with the value.")
        return False
    return True


def cmd_call(args, value):
    if not check_credential(value):
        return 1
    say("Credential: read from the environment variable %s. Its value: %s (%d characters)" % (VARIABLE, value, len(value)))
    say("            It was not given on the command line and was not read from a file.")
    service = MadeUpService(value)
    sending = value + "-out-of-date" if args.rejected else value
    remember(sending)                      # before anything that holds what is sent can be printed
    headers = {"Accept": "application/json", "Authorization": "Bearer " + sending}
    if args.verbose:
        say("Request, as a debugging switch would print it:")
        say("  GET https://service.example.invalid/items?access_token=%s" % urllib.parse.quote(sending, safe=""))
        for name in sorted(headers):
            say("  %s: %s" % (name, headers[name]))
        say("  The same credential as a Basic sign-in header would hold it: Basic %s" % base64.b64encode(("%s:%s" % (ACCOUNT, sending)).encode("utf-8", "surrogateescape")).decode("ascii"))
    if args.crash:
        raise RuntimeError("could not read the reply to the request made with %s" % headers["Authorization"])
    status, body = service.get("/items", headers)
    if status != 200:
        say("THE SERVICE REFUSED (status %d). Its own words, which repeat what it was sent: %s" % (status, body.get("error")), sys.stderr)
        return 1
    say("The made-up service accepted the credential: status %d, signed in as %s, %d items." % (status, body["account"], body["items"]))
    return 0


def scan_text(text):
    """Places in a text where a bare Trello API key may be: [(line, column)]. Never the value."""
    found = []
    for number, line in enumerate(text.split("\n"), 1):
        if "trello" not in line.lower() and not KEY_NAMED.search(line):
            continue
        for match in TRELLO_KEY.finditer(line):
            found.append((number, match.start(1) + 1))
    return found


def files_under(path):
    if not os.path.isdir(path):
        return [path]
    return sorted(os.path.join(folder, name) for folder, _, names in os.walk(path) for name in names)


def cmd_scan(args):
    findings, unread, files = 0, 0, 0
    for given in args.paths:
        for path in files_under(given):
            try:
                with open(path, "rb") as f:
                    raw = f.read()
            except OSError:
                say("%s: COULD NOT BE READ, so it was not scanned" % path)
                unread += 1
                continue
            if b"\x00" in raw[:4096]:
                continue                   # a picture or another file that is not text: nothing here can read it
            files += 1
            for line, column in scan_text(raw.decode("utf-8", "replace")):
                findings += 1
                say("%s:%d:%d: [trello-api-key] what may be a Trello API key: 32 hex characters (not shown)" % (path, line, column))
    say("second-pattern scan: %d file%s scanned, %d finding%s%s" % (files, "" if files == 1 else "s", findings, "" if findings == 1 else "s",
                                                                    ", %d path%s could not be read" % (unread, "" if unread == 1 else "s") if unread else ""))
    if not files and not unread:
        say("NOTHING WAS SCANNED: no file was found at the paths given. That is not a pass.")
        return 1
    return 1 if findings or unread else 0


def main(argv=None):
    """Runs one command. Whatever goes wrong inside, what is printed has been through the mask."""
    value = load_credential()              # FIRST: so that nothing below, the reading of the command line included, can print it
    try:
        parser = QuietParser(description="Use a credential from the environment without printing it.")
        commands = parser.add_subparsers(dest="command", required=True, parser_class=QuietParser)
        call = commands.add_parser("call")
        call.add_argument("--verbose", action="store_true", help="print the request and its headers, masked")
        call.add_argument("--rejected", action="store_true", help="send a credential the service refuses, to see its error masked")
        call.add_argument("--crash", action="store_true", help="fail with an error that holds the credential, to see it masked")
        scan = commands.add_parser("scan")
        scan.add_argument("paths", nargs="+")
        args = parser.parse_args(argv)
        return cmd_call(args, value) if args.command == "call" else cmd_scan(args)
    except SystemExit as leaving:
        return leaving.code if isinstance(leaving.code, int) else 2
    except BaseException:                  # an error's message may hold the credential: it is reported here, masked, and goes no further
        report_failure(*sys.exc_info())
        return 3


if __name__ == "__main__":
    sys.excepthook = masked_excepthook     # a backstop. main() reports its own failures
    sys.exit(main())
