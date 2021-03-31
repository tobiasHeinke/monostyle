
"""
main
~~~~

Interface for applying tools on the differential of RST files.

Pipeline Overview:
[monostyle] -->
[Versioning diff] --text snippets--> [monostyle] --> [parser]
[parser] --nodes--> [monostyle] --> [tools]
[tools] --reports--> [monostyle] --> console print
   '--> [monostyle] --reports--> [autofix] --> files

"""

import sys
import os
import importlib.util

from . import config
from .util import monostyle_io
from .util.report import (Report, print_reports, print_report,
                          options_overide, reports_summary)
from .rst_parser.core import RSTParser
from .rst_parser import environment as env
from .rst_parser import hunk_post_parser
from . import autofix
from .util import file_opener


def init_tools():
    """Execute the init function of each module."""
    mods = []
    for module_name, value in config.tool_selection.items():
        if module := import_module(module_name):
            ops = init(module.OPS, value["tools"], module_name)
            if ops is not None and len(ops) != 0:
                mods.append((ops, value["ext"]))

    return mods


def import_module(name, dst=None):
    """Import module."""
    if dst is None:
        dst = name
    name = "monostyle." + name
    if name in sys.modules:
        # module already in sys.modules
        return sys.modules[name]

    if (spec := importlib.util.find_spec(name)) is not None:
        module = importlib.util.module_from_spec(spec)
        sys.modules[dst] = module
        spec.loader.exec_module(module)
        return module
    else:
        print("module import: can't find the {0} module".format(name))


def init(ops, op_names, mod_name):
    ops_sel = []
    if isinstance(op_names, str):
        op_names = [op_names]

    lexicon_exist = None
    for op_name in op_names:
        if op_name in {"collocation", "hyphen", "new-word"}:
            if lexicon_exist is None:
                lexicon_exist = import_module("update_lexicon").setup_lexicon()

        for op in ops:
            if op_name == op[0]:
                args = {}
                if len(op) > 2 and op[2] is not None:
                    # evaluate pre
                    args = op[2](op[0])

                ops_sel.append((op[0], op[1], args, bool(not(len(op) > 3 and not op[3]))))
                break
        else:
            print("{0}: unknown operation: {1}".format(mod_name, op_name))

    return ops_sel


def get_reports_version(mods, rst_parser, from_vsn, is_internal, path, rev=None, cached=False):
    """Gets text snippets (hunk) from versioning."""
    reports = []
    show_current = True
    filename_prev = None
    print_options = options_overide()
    parse_options = {"parse": True, "resolve": False, "post": True}
    for fg, context, message in vsn_inter.run_diff(from_vsn, is_internal, path, rev, cached):
        if message is not None:
            vsn_report = Report('W', "versioning-diff", fg, message, fix=fg.copy().replace('\n'))
            filename_prev = print_report(vsn_report, print_options, filename_prev)
            reports.append(vsn_report)
            continue

        if show_current:
            monostyle_io.print_over("processing:",
                                    "{0}[{1}-{2}]".format(monostyle_io.path_to_rel(fg.filename),
                                                          fg.start_lincol[0], fg.end_lincol[0]),
                                    is_temp=True)

        reports, filename_prev = apply(rst_parser, mods, reports, rst_parser.document(fg=fg),
                                       parse_options, print_options,
                                       filename_prev, filter_reports, context)

    if print_options["show_summary"]:
        reports_summary(reports, print_options)

    if show_current:
        monostyle_io.print_over("processing: done")

    return reports


def get_reports_file(mods, rst_parser, path, parse_options):
    """Get working copy text files."""
    reports = []
    ops_loop = []
    ext_test = None
    for ops, ext_test in mods:
        for op in ops:
            if not op[3]:
                reports = op[1](op[0], reports, **op[2])
            else:
                ops_loop.append(op)

    if not ops_loop:
        print_reports(reports)
        return reports

    print_options = options_overide()
    show_current = bool(path)
    if path:
        path = monostyle_io.path_to_abs(path, "rst")
    filename_prev = None
    if parse_options["resolve"]:
        titles, targets = env.get_link_titles(rst_parser)
        parse_options["titles"] = titles
        parse_options["targets"] = targets
    for filename, text in monostyle_io.rst_texts(path):
        doc = rst_parser.document(filename, text)
        if show_current:
            monostyle_io.print_over("processing:",
                                    "{0}[{1}-{2}]".format(monostyle_io.path_to_rel(filename),
                                                          0, doc.code.end_lincol[0]),
                                    is_temp=True)

        reports, filename_prev = apply(rst_parser, ((ops_loop, ext_test),), reports, doc,
                                       parse_options, print_options, filename_prev)

    if print_options["show_summary"]:
        reports_summary(reports, print_options)

    if show_current:
        monostyle_io.print_over("processing: done")

    return reports


def filter_reports(report, context):
    """Filter out reports in the diff context."""
    return bool(report.tool in
                {"blank-line", "flavor", "indention", "heading-level", "heading-line-length",
                 "mark", "markup-names", "start-case", "structure"} and # "search-word",
                report.output.start_lincol is not None and context is not None and
                report.output.start_lincol[0] in context)


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
            # init failed
            if op[2] is None:
                continue

            reports_tool = []
            reports_tool = op[1](op[0], document, reports_tool, **op[2])

            for report in reports_tool:
                if filter_func is None or not filter_func(report, context):
                    filename_prev = print_report(report, print_options, filename_prev)
                    reports.append(report)

    return reports, filename_prev


def update(path, rev=None):
    """Update the working copy."""
    filenames_conflicted = set()
    for filename, conflict, rev_up in vsn_inter.update_files(path, rev):
        # A conflict will be resolvable with versioning's command interface.
        if conflict:
            filenames_conflicted.add(filename)
    return filenames_conflicted

#------------------------


def patch_flavor(filename):
    """Detect whether the patch is Git flavor."""
    try:
        with open(filename, "r") as f:
            text = f.read()

    except (IOError, OSError) as err:
        print("{0}: cannot open: {1}".format(filename, err))
        return None

    for line in text.splitlines():
        if line.startswith("Index: "):
            return False
        if line.startswith("diff --git "):
            return True


def setup(root, patch=None):
    """Setup user config and file storage."""
    is_repo = False
    is_git = False
    if not patch:
        if os.path.isdir(os.path.normpath(os.path.join(root, ".svn"))):
            is_repo = True
        elif os.path.isdir(os.path.normpath(os.path.join(root, ".git"))):
            is_repo = True
            is_git = True
    else:
        is_git = patch_flavor(patch)
        if is_git is None:
            return False

    global vsn_inter
    vsn_inter = import_module("git_inter" if is_git else "svn_inter", "vsn_inter")

    config_dir = os.path.normpath(os.path.join(root, "monostyle"))
    if not os.path.isdir(config_dir):
        if not monostyle_io.ask_user("Create user config folder in '", root, "'",
                                     "" if is_repo else " even though it's not the top folder "
                                     "of a repository"):
            # run with default config
            return True

        try:
            os.mkdir(config_dir)

        except (IOError, OSError) as err:
            print("{0}: cannot create: {1}".format(config_dir, err))
            return False

    success = config.init(root)
    if success:
        Report.override_templates(config.template_override)
    return success


def main_mod(mod_doc, ops, mod_file, do_parse=True):
    """Wrapper for the individual module file entries."""
    main(mod_doc.replace('~', ''),
         (ops, ".rst", os.path.splitext(os.path.basename(mod_file))[0]),
         {"parse": do_parse, "resolve": False, "post": False})


def main(descr=None, mod_selection=None, parse_options=None):
    import argparse

    if descr is None:
        descr = "Applies various tools on the differential of the documentation."
    is_selection = bool(mod_selection is not None)

    parser = argparse.ArgumentParser(description=descr)
    if is_selection:
        tools = parser.add_argument_group(title="Tools")
        for op in mod_selection[0]:
            doc_str = ''
            if op[1].__doc__ is not None:
                # first char to lowercase
                doc_str = op[1].__doc__[0].lower() + op[1].__doc__[1:]
            tools.add_argument("--" + op[0], dest="op_names",
                                action="append_const", const=op[0], metavar="",
                                help=doc_str)

    group = parser.add_mutually_exclusive_group()
    if not is_selection:
        group.add_argument("-i", "--internal",
                           dest="internal", nargs='?', const="", metavar="REV",
                           help="check changes to the working copy (against REV)")
        group.add_argument("-e", "--external",
                           dest="external", nargs='?', const="", metavar="REV",
                           help="check changes to the repository (at REV)")

    group.add_argument("-p", "--patch",
                       dest="patch", help="read diff from PATCHFILE")
    group.add_argument("-f", "--file",
                       dest="filename", help="check working copy file or directory FILENAME")

    parser.add_argument("-r", "--root",
                        dest="root", nargs='?', const="",
                        help="defines the ROOT directory of the project")

    if not is_selection:
        parser.add_argument("--cached", "--staged",
                            action="store_true", dest="cached", default=False,
                            help="set diff cached option (Git only)")

    if is_selection:
        parser.add_argument("-s", "--resolve",
                            action="store_true", dest="do_resolve", default=False,
                            help="resolve links and substitutions")


    if not is_selection:
        parser.add_argument("-u", "--update",
                            dest="up", nargs='?', const=None, metavar="REV",
                            help="update the working copy (to REV)")
    parser.add_argument("-a", "--autofix",
                        action="store_true", dest="auto", default=False,
                        help="apply autofixes")
    parser.add_argument("-o", "--open",
                        dest="min_severity", nargs='?',
                        choices=Report.severities, const=Report.severities[-1],
                        help="open files with report severity above")

    args = parser.parse_args()

    if args.root is None:
        root_dir = os.getcwd()
    else:
        root_dir = os.path.normpath(args.root)

        if not os.path.exists(root_dir):
            print('Error: root {0} does not exists'.format(args.root))
            return 2

    root_dir = monostyle_io.norm_path_sep(root_dir)
    setup_sucess = setup(root_dir, args.patch)
    if not setup_sucess:
        return 2

    if not args.auto and "console_options" in vars(config).keys():
        config.console_options["show_autofix"] = False

    if mod_selection is None:
        mods = init_tools()
    else:
        mods = ((init(mod_selection[0], args.op_names, mod_selection[2]), mod_selection[1]),)
    rst_parser = RSTParser()
    if not is_selection and not args.filename and not args.patch:
        is_internal = bool(args.internal is not None)
        if is_internal:
            rev = args.internal if len(args.internal.strip()) != 0 else None
        else:
            rev = args.external if len(args.external.strip()) != 0 else None

        reports = get_reports_version(mods, rst_parser, True, is_internal, root_dir,
                                      rev, args.cached)

    elif args.patch:
        if not os.path.exists(args.patch):
            print('Error: file {0} does not exists'.format(args.patch))
            return 2

        reports = get_reports_version(mods, rst_parser, False, True,
                                      monostyle_io.norm_path_sep(args.patch))
        for report in reports:# custom root
            report.output.filename = monostyle_io.path_to_abs(report.output.filename)
    else:
        if not parse_options:
            parse_options = {"parse": True, "resolve": False, "post": False}
        if is_selection and args.do_resolve:
            parse_options["resolve"] = args.do_resolve
        reports = get_reports_file(mods, rst_parser,
                                   monostyle_io.norm_path_sep(args.filename)
                                   if args.filename else None,
                                   parse_options)

    filenames_conflicted = None
    if not is_selection:
        if args.up or (args.auto and args.external is not None):
            filenames_conflicted = update(root_dir, args.up)

    if args.auto:
        if ((is_selection or not ((args.external and rev) or args.patch) or
                monostyle_io.ask_user("Apply autofix on possibly altered sources")) and
                (not is_selection or args.filename or
                 monostyle_io.ask_user("Apply autofix on the entire project"))):
            autofix.run(reports, rst_parser, filenames_conflicted)
    if args.min_severity:
        file_opener.open_reports_files(reports, args.min_severity)


if __name__ == "__main__":
    main()
