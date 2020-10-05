
"""
char
~~~~

Tools on char level and encoding.
"""

import re

import monostyle.util.monostylestd as monostylestd
from monostyle.util.report import Report
from monostyle.util.fragment import Fragment
from monostyle.util.char_catalog import CharCatalog

CharCatalog = CharCatalog()


def char_search(document, reports):
    """All chars outside of the defined Unicode region or explicit search."""
    toolname = "char-search"

    text = str(document.code)
    chars = (
        (r"\uFFFD", "replace char", None),
        (CharCatalog.data["quote"]["initial"]["single"], "initial quote", "'"),
        (CharCatalog.data["quote"]["initial"]["double"], "initial quote", "\""),
        (CharCatalog.data["quote"]["final"]["single"], "final quote", "'"),
        (CharCatalog.data["quote"]["final"]["double"], "final quote", "\""),
        (r"–", "en-dash", "--"),
        (r"—", "em-dash", "--"),
    )
    explicits = ""
    for pattern, msg, repl in chars:
        char_re = re.compile(r"[" + pattern + r"]")
        explicits += pattern
        for char_m in re.finditer(char_re, text):
            output = document.code.slice_match_obj(char_m, 0, True)
            fg_repl = output.copy().replace_fill(repl) if repl else None
            reports.append(Report('E', toolname, output, msg, fix=fg_repl))

    parttern_str = r"[^\n -~À-ʨ" + ''.join(('©', '®', '°', '±', '€', '™', "\t")) + explicits +  r"]"
    char_re = re.compile(parttern_str)
    for char_m in re.finditer(char_re, text):
        msg = "uncommon char: {0}, 0x{0:04x}".format(ord(char_m.group(0)))
        output = document.code.slice_match_obj(char_m, 0, True)
        reports.append(Report('E', toolname, output, msg))

    return reports


def file_encoding(reports):
    """Check text encoding."""
    toolname = "file-encoding"

    # standard Unicode replace char <?>
    repchar_re = re.compile("\uFFFD")
    for filename in monostylestd.rst_files():
        with open(filename, "r", encoding="utf-8", errors="replace") as f:
            try:
                text = f.read()

            except UnicodeEncodeError as err:
                output = Fragment(filename, "")
                msg = "encode error: " + str(err)
                reports.append(Report('E', toolname, output, msg))

            except:
                output = Fragment(filename, "")
                msg = "unknown encode error"
                reports.append(Report('E', toolname, output, msg))

            else:
                document_fg = Fragment(filename, text)
                for repchar_m in re.finditer(repchar_re, text):
                    output = document_fg.slice_match_obj(repchar_m, 0, True)
                    msg = "unsupported character"
                    reports.append(Report('E', toolname, output, msg))

    return reports


OPS = (
    ("char-search", char_search, None),
    ("encoding", file_encoding, None, False),
)

if __name__ == "__main__":
    from monostyle.cmd import main
    main(OPS, __doc__, __file__, do_parse=False)
