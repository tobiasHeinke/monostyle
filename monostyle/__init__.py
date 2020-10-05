
"""
monostyle
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
from .util import monostylestd
from .util.report import (Report, print_report,
                          options_overide, reports_summary)
from .rst_parser.core import RSTParser
from . import autofix
from .util import file_opener
from .cmd import init, apply

__version__ = "0.2.0"

RSTParser = RSTParser()


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
        print("module import: {0} already in sys.modules".format(name))
    elif (spec := importlib.util.find_spec(name)) is not None:
        module = importlib.util.module_from_spec(spec)
        sys.modules[dst] = module
        spec.loader.exec_module(module)
        return module
    else:
        print("module import: can't find the {0} module".format(name))


def get_reports_version(from_vsn, is_internal, path, rev=None, cached=False):
    """Gets text snippets (hunk) from versioning."""
    mods = init_tools()

    reports = []
    show_current = True
    filename_prev = None
    print_options = options_overide()
    parse_options = {"parse": True, "resolve": False, "post": True}
    for fg, context, msg in vsn_inter.run_diff(from_vsn, is_internal, path, rev, cached):
        if msg is not None:
            vsn_report = Report('W', "versioning-diff", fg, msg)
            filename_prev = print_report(vsn_report, print_options, filename_prev)
            reports.append(vsn_report)
            continue

        if show_current:
            monostylestd.print_over("processing:",
                                    "{0}[{1}-{2}]".format(monostylestd.path_to_rel(fg.filename),
                                                          fg.start_lincol[0], fg.end_lincol[0]),
                                    is_temp=True)

        reports, filename_prev = apply(RSTParser, mods, reports, RSTParser.snippet(fg),
                                       parse_options, print_options,
                                       filename_prev, filter_reports, context)

    if print_options["show_summary"]:
        reports_summary(reports, print_options)

    if show_current:
        monostylestd.print_over("processing: done")

    return reports


def get_reports_file(path):
    """Get working copy text files."""
    mods = init_tools()

    path = monostylestd.path_to_abs(path, "rst")
    reports = []
    show_current = True
    filename_prev = None
    print_options = options_overide()
    parse_options = {"parse": True, "resolve": False, "post": False}
    for filename, text in monostylestd.rst_texts(path):
        doc = RSTParser.document(filename, text)
        if show_current:
            monostylestd.print_over("processing:",
                                    "{0}[{1}-{2}]".format(monostylestd.path_to_rel(filename),
                                                          0, doc.code.end_lincol[0]),
                                    is_temp=True)

        reports, filename_prev = apply(RSTParser, mods, reports, doc,
                                       parse_options, print_options, filename_prev)

    if print_options["show_summary"]:
        reports_summary(reports, print_options)

    if show_current:
        monostylestd.print_over("processing: done")

    return reports


def filter_reports(report, context):
    """Filter out reports in the diff context."""
    return bool(report.tool in
                ("mark", "blank-line", "directive", "indention", "heading-level",
                 "heading-char-count", "starting", "flavor") and # "search-word",
                report.output.start_lincol is not None and context is not None and
                report.output.start_lincol[0] in context)


def update(path, rev=None):
    """Update the working copy."""
    fns_conflicted = []
    for filename, conflict, rev_up in vsn_inter.update_files(path, rev):
        # A conflict will be resolvable with versioning's command interface.
        if conflict and filename not in fns_conflicted:
            fns_conflicted.append(filename)
    return fns_conflicted

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
        if not monostylestd.ask_user(("Create user config folder in '", root, "'",
                                      "" if is_repo else " even though it's not the top folder "
                                      "of a repository")):
            # run with default config
            return True

        try:
            os.mkdir(config_dir)

        except (IOError, OSError) as err:
            print("{0}: cannot create: {1}".format(config_dir, err))
            return False

    success = config.setup_config(root)
    if success:
        Report.override_templates(config.template_override)
    return success


def main():
    import argparse

    descr = "Applies various tools on the differential of the manual."
    parser = argparse.ArgumentParser(description=descr)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-i", "--internal",
                       dest="internal", nargs='?', const="", metavar='REV',
                       help="check changes to the working copy (against REV)")
    group.add_argument("-e", "--external",
                       dest="external", nargs='?', const="", metavar='REV',
                       help="check changes to the repository (at REV)")
    group.add_argument("-p", "--patch",
                       dest="patch", help="read diff from PATCHFILE")
    group.add_argument("-f", "--file",
                       dest="filename", help="check working copy file or directory FILENAME")

    parser.add_argument("-r", "--root",
                        dest="root", nargs='?', const="",
                        help="defines the ROOT directory of the project")

    parser.add_argument("--cached", "--staged",
                        action='store_true', dest="cached", default=False,
                        help="set diff cached option (Git only)")

    parser.add_argument("-u", "--update",
                        dest="up", nargs='?', const=None, metavar='REV',
                        help="update the working copy (to REV)")
    parser.add_argument("-a", "--autofix",
                        action='store_true', dest="auto", default=False,
                        help="apply autofixes")
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
    setup_sucess = setup(root_dir, args.patch)
    if not setup_sucess:
        return 2

    if not args.auto and "console_options" in vars(config).keys():
        config.console_options["show_autofix"] = False

    if not args.filename and not args.patch:
        is_internal = bool(args.internal is not None)
        if is_internal:
            rev = args.internal if len(args.internal.strip()) != 0 else None
        else:
            rev = args.external if len(args.external.strip()) != 0 else None

        reports = get_reports_version(True, is_internal, root_dir, rev, args.cached)

    elif args.patch:
        if not os.path.exists(args.patch):
            print('Error: file {0} does not exists'.format(args.patch))
            return 2

        reports = get_reports_version(False, True,
                                      monostylestd.replace_windows_path_sep(args.patch))
        for report in reports:# custom root
            report.output.filename = monostylestd.path_to_abs(report.output.filename)
    else:
        reports = get_reports_file(monostylestd.replace_windows_path_sep(args.filename))

    fns_conflicted = None
    if args.up or (args.auto and args.external is not None):
        fns_conflicted = update(root_dir, args.up)

    if args.auto:
        if (not ((args.external and rev) or args.patch) or
                monostylestd.ask_user(("Apply autofix on possibly altered sources"))):

            autofix.run(reports, RSTParser, fns_conflicted)
    if args.min_severity:
        file_opener.open_reports_files(reports, args.min_severity)


if __name__ == "__main__":
    main()
