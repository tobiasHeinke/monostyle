
"""
char
~~~~

Tools on char level and encoding.
"""

import re

import monostyle.util.monostyle_io as monostyle_io
from monostyle.util.report import Report
from monostyle.util.fragment import Fragment
from monostyle.util.char_catalog import CharCatalog


def char_search(toolname, document, reports):
    """All chars outside of the defined Unicode region or explicit search."""
    char_catalog = CharCatalog()
    text = str(document.code)
    chars = (
        (r"\uFFFD", "replace char", None),
        (char_catalog.data["quote"]["initial"]["single"], "initial quote", "'"),
        (char_catalog.data["quote"]["initial"]["double"], "initial quote", "\""),
        (char_catalog.data["quote"]["final"]["single"], "final quote", "'"),
        (char_catalog.data["quote"]["final"]["double"], "final quote", "\""),
        (r"–", "en-dash", "--"),
        (r"—", "em-dash", "--"),
    )
    explicits = ""
    for pattern, message, repl in chars:
        char_re = re.compile(r"[" + pattern + r"]")
        explicits += pattern
        for char_m in re.finditer(char_re, text):
            output = document.code.slice_match(char_m, 0)
            reports.append(
                Report('E', toolname, output, message,
                       fix=output.copy().replace_fill(repl) if repl else None))

    char_re = re.compile(r"[^\n -~À-ʨ©®°±€™\t" + explicits + r"]")
    for char_m in re.finditer(char_re, text):
        reports.append(
            Report('E', toolname,
                   document.code.slice_match(char_m, 0),
                   "uncommon char: {0}, 0x{0:04x}".format(ord(char_m.group(0)))))

    return reports


def encoding(toolname, reports):
    """Check text encoding."""
    # standard Unicode replace char <?>
    repchar_re = re.compile("\uFFFD")
    for filename in monostyle_io.doc_files():
        with open(filename, "r", encoding="utf-8", errors="replace") as f:
            try:
                text = f.read()

            except UnicodeError as err:
                reports.append(
                    Report('F', toolname, Fragment(filename, ""), "encoding error: " + str(err)))

            except Exception as err:
                reports.append(
                    Report('F', toolname, Fragment(filename, ""), "unknown error: " + str(err)))

            else:
                code = Fragment(filename, text)
                for repchar_m in re.finditer(repchar_re, text):
                    reports.append(
                        Report('E', toolname, code.slice_match(repchar_m, 0),
                               "unsupported character"))

    return reports


def eof_pre(_):
    args = dict()
    char_catalog = CharCatalog()
    args["re_lib"] = {
        "end": re.compile("".join((r"\n{2,}\Z|",
                                   r"\n[", char_catalog.data["whitespace"]["inline"], r"]+\Z|"
                                   r"(?<!\n)\Z")))}
    args["config"] = dict()
    return args


def eof(toolname, document, reports, re_lib, config):
    """Check blank lines at end of file."""
    if "_at_eof" in config and config["_at_eof"]:
        if m := re.search(re_lib["end"], str(document.code)):
            output = document.body.code.slice_match(m, 0)
            reports.append(
                Report('W', toolname, output.copy().clear(True),
                       Report.existing(what=Report.write_out_quantity(
                                                str(m.group(0)).count('\n'), "blank line"),
                                       where="at the end of file"),
                       fix=output.replace('\n')))

    return reports



OPS = (
    ("char-search", char_search, None),
    ("encoding", encoding, None, False),
    ("EOF", eof, eof_pre),
)

if __name__ == "__main__":
    from monostyle.__main__ import main_mod
    main_mod(__doc__, OPS, __file__, do_parse=False)
