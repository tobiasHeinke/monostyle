
"""
cmd
~~~

Standard tool init and execution.
"""

import os
import argparse

import monostyle.util.monostylestd as monostylestd
from monostyle.util.report import Report, print_reports
from monostyle.rst_parser.core import RSTParser


def init(ops, op_names, mod_name):
    ops_sel = []
    if isinstance(op_names, str):
        op_names = [op_names]

    for op_name in op_names:
        for op in ops:
            if op_name == op[0]:
                args = {}
                if len(op) > 2 and op[2] is not None:
                    # evaluate pre
                    args = op[2](op)

                ops_sel.append((op[1], args, bool(not(len(op) > 3 and not op[3]))))
                break
        else:
            print("{0}: unknown operation: {1}".format(mod_name, op_name))

    return ops_sel


def hub(ops_sel, do_parse=True):
    reports = []
    ops_loop = []
    for op in ops_sel:
        if not op[2]:
            reports = op[0](reports)
        else:
            ops_loop.append(op)

    if not ops_loop:
        return reports

    rst_parser = RSTParser()
    for fn, text in monostylestd.rst_texts():
        document = rst_parser.document(fn, text)
        if do_parse:
            document = rst_parser.parse_full(document)

        for op in ops_loop:
            reports = op[0](document, reports, **op[1])

    return reports


def main(ops, mod_doc, mod_file, do_parse=True):
    from monostyle import setup

    mod_file = os.path.splitext(os.path.basename(mod_file))[0]

    parser = argparse.ArgumentParser(description=mod_doc.replace('~', ''))
    for op in ops:
        doc_str = ''
        if op[1].__doc__ is not None:
            # first char to lowercase
            doc_str = op[1].__doc__[0].lower() + op[1].__doc__[1:]
        parser.add_argument("--" + op[0], dest="op_names",
                            action='store_const', const=op[0], metavar="",
                            help=doc_str)

    parser.add_argument("-r", "--root",
                        dest="root", nargs='?', const="",
                        help="defines the ROOT directory of the project")

    args = parser.parse_args()

    if args.root is None:
        root_dir = os.getcwd()
    else:
        root_dir = os.path.normpath(args.root)

        if not os.path.exists(root_dir):
            print('Error: root {0} does not exists'.format(args.root))
            return 2

    root_dir = monostylestd.replace_windows_path_sep(root_dir)
    monostylestd.ROOT_DIR = root_dir

    setup_sucess = setup(root_dir)
    if not setup_sucess:
        return 2

    reports = hub(init(ops, args.op_names, mod_file), do_parse)
    print_reports(reports)
