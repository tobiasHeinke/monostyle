
"""
monostyle
~~~~

Interface for applying tools on the differential of RST files.

Pipeline Overview:
[monostyle] -->
[SVN diff] --text snippets--> [monostyle] --> [parser]
[parser] --nodes--> [monostyle] --> [tools]
[tools] --reports--> [monostyle] --> console print
   '--> [monostyle] --reports--> [autofix] --> files

"""

import sys
import os
import importlib.util

from . import config
from .util import monostylestd
from .util.report import Report, print_reports
from .rst_parser.core import RSTParser
from .rst_parser import hunk_post_parser
from . import autofix
from .util import file_opener
from .cmd import init

__version__ = "0.2.0"

RSTParser = RSTParser()


def init_tools():
    """Execute the init function of each module."""
    mods = []
    for module_name, val in config.tool_selection.items():
        if module := import_module(module_name):
            ops = init(module.OPS, val["tools"], module_name)
            if ops is not None and len(ops) != 0:
                mods.append((ops, val["ext"]))

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
    """Gets text snippets (hunk) from SVN."""
    mods = init_tools()

    reports = []
    show_current = True
    for fg, context, msg in vsn_inter.run_diff(from_vsn, is_internal, path, rev, cached):
        if msg is not None:
            reports.append(Report('W', "svn diff", fg, msg))
            continue

        if show_current:
            print("\rprocessing: {0}[{1}-{2}]".format(
                      monostylestd.path_to_rel(fg.fn), fg.start_lincol[0], fg.end_lincol[0]),
                  end='', flush=True)
        reports_hunk = apply_tools(mods, fg)

        if context is not None:
            reports = filter_reports(reports_hunk, context, reports)
        else:
            reports.extend(reports_hunk)

    if show_current:
        print("processing: done")

    return reports


def get_reports_file(path):
    """Get working copy text files."""
    mods = init_tools()

    path = monostylestd.path_to_abs(path, "rst")
    reports = []
    show_current = True
    for fn, text in monostylestd.rst_texts(path):
        doc = RSTParser.document(fn, text)
        if show_current:
            print("\rprocessing: {0}[{1}-{2}]".format(
                      monostylestd.path_to_rel(fn), 0, doc.code.end_lincol[0]),
                  end='', flush=True)

        reports.extend(apply_tools(mods, doc.code))

    if show_current:
        print("processing: done")

    return reports


def apply_tools(mods, fg):
    """Parse the hunks and apply the tools."""
    reports_hunk = []

    if fg.fn.endswith(".rst"):
        document = RSTParser.parse(RSTParser.snippet(fg))
        document = hunk_post_parser.parse(RSTParser, document)
    else:
        document = RSTParser.snippet(fg)

    for ops, ext_test in mods:
        if len(ext_test) != 0 and not fg.fn.endswith(ext_test):
            continue

        for op in ops:
            if not isinstance(op, tuple):
                print(op.__name__)
            reports_hunk = op[0](document, reports_hunk, **op[1])

    return reports_hunk


def filter_reports(reports_hunk, context, reports):
    """Filter out reports in the diff context else add to final reports."""
    for report in reports_hunk:
        if (report.tool in
                ("mark", "blank-line", "directive", "indention", "heading-level",
                 "heading-char-count", "starting", "flavor") and # "search-word",
                report.out.start_lincol is not None and report.out.start_lincol[0] in context):
            continue

        reports.append(report)

    return reports


def update(path, rev=None):
    """Update the working copy."""
    fns_conflicted = []
    for fn, conflict, rev_up in vsn_inter.update_files(path, rev):
        # A conflict will be resolvable with SVN's command interface.
        if conflict and fn not in fns_conflicted:
            fns_conflicted.append(fn)
    return fns_conflicted

#------------------------


def patch_flavor(fn):
    """Detect whether the patch is Git flavor."""
    try:
        with open(fn, "r") as f:
            text = f.read()

    except (IOError, OSError) as err:
        print("{0}: cannot open: {1}".format(fn, err))
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
            report.out.fn = monostylestd.path_to_abs(report.out.fn)
    else:
        reports = get_reports_file(monostylestd.replace_windows_path_sep(args.filename))

    if not args.auto and "console_options" in vars(config).keys():
        config.console_options["show_autofix"] = False
    print_reports(reports)

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
