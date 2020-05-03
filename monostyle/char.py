
"""
char
~~~~

Tools on char level and encoding.
"""

import os
import re

import monostyle.util.monostylestd as monostylestd
from monostyle.util.monostylestd import Report
from monostyle.util.fragment import Fragment
from monostyle.rst_parser.core import RSTParser


def char_expl(document, reports):
    """Explicit search for not allowed chars."""
    toolname = "char explicit"

    text = str(document.code)
    repchar_re = re.compile("\uFFFD")
    for repchar_m in re.finditer(repchar_re, text):
        out = document.code.slice_match_obj(repchar_m, 0, True)
        reports.append(Report('E', toolname, out, "replace char"))

    counter = 0
    return_re = re.compile("\r")
    for return_m in re.finditer(return_re, text):
        if counter == 0:
            out = document.code.slice_match_obj(return_m, 0, True)

        counter += 1

    if counter != 0:
        msg = "carriage return:" + str(counter) + " times"
        reports.append(Report('E', toolname, out, msg))

    tab_re = re.compile("\t")
    for tab_m in re.finditer(tab_re, text):
        out = document.code.slice_match_obj(tab_m, 0, True)
        reports.append(Report('E', toolname, out, "tab"))

    return reports


def char_region(document, reports):
    """All chars outside of the defined Unicode region."""
    toolname = "char region"

    text = str(document.code)
    parttern_str = r"[^\n -~À-ʨ" + ''.join(('©', '®', '°', '±', '€', '™')) + r"]"
    char_re = re.compile(parttern_str)
    for char_m in re.finditer(char_re, text):
        msg = "uncommon char: {0}, 0x{0:04x}".format(ord(char_m.group(0)))
        out = document.code.slice_match_obj(char_m, 0, True)
        reports.append(Report('E', toolname, out, msg))

    return reports


def file_encoding():
    """Check text encoding."""
    toolname = "file encoding"

    reports = []
    # standard Unicode replace char <?>
    repchar_re = re.compile("\uFFFD")
    # for fn in monostylestd.po_files():
    for fn in monostylestd.rst_files():
        with open(fn, "r", encoding="utf-8", errors="replace") as f:
            try:
                text = f.read()

            except UnicodeEncodeError as err:
                out = Fragment.from_org_len(fn, str(err), 0, start_lincol=-1)
                msg = "encode error"
                reports.append(Report('E', toolname, out, msg))

            except:
                out = Fragment.from_org_len(fn, "", 0, start_lincol=-1)
                msg = "unknown encode error"
                reports.append(Report('E', toolname, out, msg))

            else:
                document_fg = Fragment.from_initial(fn, text)
                for repchar_m in re.finditer(repchar_re, text):
                    out = document_fg.slice_match_obj(repchar_m, 0, True)
                    msg = "unsupported character"
                    reports.append(Report('E', toolname, out, msg))

    return reports


def init(op_names):
    ops = []
    for op in OPS:
        if op[0] in op_names:
            ops.append((op[1], {}))

    return ops


def hub(op_names):
    rst_parser = RSTParser()
    reports = []
    ops = init(op_names)

    for fn, text in monostylestd.rst_texts():
        document = rst_parser.document(fn, text)

        for op in ops:
            reports = op[0](document, reports)

    return reports


OPS = (
    ("char-expl", char_expl),
    ("char-region", char_region),
    ("encoding", file_encoding)
)

def main():
    import argparse

    descr = __doc__.replace('~', '')
    parser = argparse.ArgumentParser(description=descr)
    for op in OPS:
        doc_str = ''
        if op[1].__doc__ is not None:
            # first char to lowercase
            doc_str = op[1].__doc__[0].lower() + op[1].__doc__[1:]
        parser.add_argument("--" + op[0], dest="op_names",
                            action='store_const', const=op[0], metavar="",
                            help=doc_str)

    parser.add_argument("-r", "--root",
                        dest="root", nargs='?', const="",
                        help="defines the ROOT directory of the working copy or "
                             "if left empty the root defined in the config")

    args = parser.parse_args()

    if args.root is None:
        root_dir = os.getcwd()
    else:
        if len(args.root.strip()) == 0:
            root_dir = monostylestd.ROOT_DIR
        else:
            root_dir = os.path.normpath(args.root)

        if not os.path.exists(root_dir):
            print('Error: root {0} does not exists'.format(args.root))
            return 2

    root_dir = monostylestd.replace_windows_path_sep(root_dir)
    monostylestd.ROOT_DIR = root_dir

    if args.op_names == "encoding":
        for op in OPS:
            if op[0] == args.op_names:
                reports = op[1]()
    else:
        reports = hub(args.op_names)

    monostylestd.print_reports(reports)

if __name__ == "__main__":
    main()
