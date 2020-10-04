
"""
cmd
~~~

Standard tool init and execution.
"""

import os
import argparse

import monostyle.util.monostylestd as monostylestd
from monostyle.util.report import (Report, print_reports, print_report,
                                   options_overide, reports_summary)
from monostyle.rst_parser.core import RSTParser
import monostyle.rst_parser.environment as env
from .rst_parser import hunk_post_parser
from .util import file_opener


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


def apply(rst_parser, mods, reports, document, parse_options, print_options,
          filename_prev, filter_func=None, context=None):
    """Parse the hunks and apply the tools."""
    if parse_options["parse"] and document.code.filename.endswith(".rst"):
        document = rst_parser.parse(document)
        if parse_options["post"]:
            document = hunk_post_parser.parse(rst_parser, document)
        if (parse_options["resolve"] and
                "titles" in parse_options.keys() and "targets" in parse_options.keys()):
            document = env.resolve_link_title(document, parse_options["titles"],
                                              parse_options["targets"])
            document = env.resolve_subst(document, rst_parser.substitution)

    for ops, ext_test in mods:
        if ext_test and not document.code.filename.endswith(ext_test):
            continue

        for op in ops:
            reports_tool = []
            reports_tool = op[0](document, reports_tool, **op[1])

            for report in reports_tool:
                if filter_func is None or not filter_func(report, context):
                    filename_prev = print_report(report, print_options, filename_prev)
                    reports.append(report)

    return reports, filename_prev


def hub(ops_sel, do_parse=True, do_resolve=False):
    reports = []
    ops_loop = []
    for op in ops_sel:
        if not op[2]:
            reports = op[0](reports, **op[1])
        else:
            ops_loop.append(op)

    if not ops_loop:
        print_reports(reports)
        return reports

    rst_parser = RSTParser()
    filename_prev = None
    print_options = options_overide()
    parse_options = {"parse": do_parse, "resolve": do_resolve, "post": False}
    if do_resolve:
        titles, targets = env.get_link_titles(rst_parser)
        parse_options["titles"] = titles
        parse_options["targets"] = targets
    for filename, text in monostylestd.rst_texts():
        apply(rst_parser, ((ops_loop, None),), reports, rst_parser.document(filename, text),
              parse_options, print_options, filename_prev)

    if print_options["show_summary"]:
        reports_summary(reports, print_options)
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

    parser.add_argument("-s", "--resolve",
                        action='store_true', dest="do_resolve", default=False,
                        help="resolve links and substitutions")

    parser.add_argument("-o", "--open",
                        dest='min_severity', choices=Report.severities,
                        help="open files with report severity above")

    args = parser.parse_args()

    if args.root is None:
        root_dir = os.getcwd()
    else:
        root_dir = os.path.normpath(args.root)

        if not os.path.exists(root_dir):
            print('Error: root {0} does not exists'.format(args.root))
            return 2

    root_dir = monostylestd.replace_windows_path_sep(root_dir)
    setup_sucess = setup(root_dir)
    if not setup_sucess:
        return 2

    reports = hub(init(ops, args.op_names, mod_file), do_parse, args.do_resolve)

    if args.min_severity:
        file_opener.open_reports_files(reports, args.min_severity)
