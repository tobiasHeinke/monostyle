
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
            output = document.code.slice_match_obj(char_m, 0, True)
            fix = output.copy().replace_fill(repl) if repl else None
            reports.append(Report('E', toolname, output, message, fix=fix))

    char_re = re.compile(r"[^\n -~À-ʨ©®°±€™\t" + explicits + r"]")
    for char_m in re.finditer(char_re, text):
        message = "uncommon char: {0}, 0x{0:04x}".format(ord(char_m.group(0)))
        output = document.code.slice_match_obj(char_m, 0, True)
        reports.append(Report('E', toolname, output, message))

    return reports


def encoding(toolname, reports):
    """Check text encoding."""

    # standard Unicode replace char <?>
    repchar_re = re.compile("\uFFFD")
    for filename in monostyle_io.doc_files():
        with open(filename, "r", encoding="utf-8", errors="replace") as f:
            try:
                text = f.read()

            except UnicodeEncodeError as err:
                output = Fragment(filename, "")
                message = "encode error: " + str(err)
                reports.append(Report('F', toolname, output, message))

            except:
                output = Fragment(filename, "")
                message = "unknown encode error"
                reports.append(Report('F', toolname, output, message))

            else:
                code = Fragment(filename, text)
                for repchar_m in re.finditer(repchar_re, text):
                    output = code.slice_match_obj(repchar_m, 0, True)
                    message = "unsupported character"
                    reports.append(Report('E', toolname, output, message))

    return reports


def eol(toolname, document, reports):
    """Check blank lines at end of file."""

    if m := re.search(r"\n{2}\Z|(?<!\n)\Z", str(document.code)):
        output = document.body.code.slice_match_obj(m, 0, True)
        message = Report.existing(what=Report.write_out_quantity(str(m.group(0)).count('\n'),
                                                                 "blank line"),
                                  where="at the end of file")
        fix = output.copy().replace('\n')
        output = output.clear(True)
        reports.append(Report('W', toolname, output, message, fix=fix))

    return reports



OPS = (
    ("char-search", char_search, None),
    ("encoding", encoding, None, False),
    ("EOF", eol, None),
)

if __name__ == "__main__":
    from monostyle.__main__ import main_mod
    main_mod(__doc__, OPS, __file__, do_parse=False)
