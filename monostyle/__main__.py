
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
from .util.fragment import Fragment
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

    print("module import: can't find the {0} module".format(name))


def init(ops, op_names, mod_name):
    """Execute the pre functions of the tools."""
    ops_sel = []
    if isinstance(op_names, str):
        op_names = [op_names]

    for op_name in op_names:
        if op_name in {"collocation", "hyphen", "new-word"}:
            if init.lexicon_exist is None:
                init.lexicon_exist = import_module("update_lexicon").setup_lexicon()
            if init.lexicon_exist is False:
                continue

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

init.lexicon_exist = None


def get_hunks_version(path, parse_options, version_options):
    """Gets text snippets (hunk) from versioning."""
    filter_options = {"tools": {"blank-line", "flavor", "indention", "heading-level",
                                "heading-line-length", "mark", "markup-names",
                                "start-case", "structure", "ui"}}
    for source, changes in vsn_inter.run_diff(path=path, **version_options):
        if not changes:
            continue
        code = source.union(changes)
        filter_options["changes"] = changes.correlate_len(other=source)
        config_dynamic = {"_at_eof": not code.content[-1].endswith('\n')}
        yield code, parse_options, filter_options, config_dynamic


def get_hunks_file(path, parse_options, *_):
    """Get working copy text files."""
    def split_span(path):
        """Split of span and make path absolute."""
        path, appendix = monostyle_io.split_path_appendix(path)
        path = monostyle_io.path_to_abs(path, "doc")

        if os.path.isfile(path) and appendix:
            start, _, end = appendix.partition('-')
            if start and start.isdigit():
                start = (int(start) - 1, 0)
            else:
                start = None
            if end and end.isdigit():
                if not start:
                    start = (0, 0)
                end = (int(end), 0)
            else:
                end = None
            return path, (start, end) if start or end else None

        return path, None

    path, span = split_span(path)
    config_dynamic = {"_at_eof": True}
    for filename, text in monostyle_io.doc_texts(path):
        code = Fragment(filename, text)
        if span:
            code = code.slice(span[0], span[1])
            if code.span_len(True) == 0:
                continue
            if code.start_pos != 0:
                parse_options["post"] = True
            if code.end_pos != len(text):
                config_dynamic["_at_eof"] = False

        yield code, parse_options, None, config_dynamic


def apply(mods, path, rst_parser, parse_options, version_options=None):
    """Parse the hunks and apply the tools."""
    def filter_reports(report, options):
        """Filter out reports in the diff context."""
        return bool(report.tool in options["tools"] and
                    report.output.start_lincol is not None and options["changes"] is not None and
                    not options["changes"].is_in_span(report.output.start_lincol))

    reports = []
    mods_loop = []
    for ops, ext_test in mods:
        ops_loop = []
        for op in ops:
            if not op[3]:
                reports = op[1](op[0], reports, **op[2])
            else:
                ops_loop.append(op)

        mods_loop.append((ops_loop, ext_test))

    if not mods_loop:
        print_reports(reports)
        return reports

    mods = mods_loop
    del mods_loop

    if not path:
        path = monostyle_io.path_to_abs("")
    print_options = options_overide()
    show_current = bool(version_options)
    filename_prev = None
    if parse_options["resolve"]:
        titles, targets = env.get_link_titles(rst_parser)
        parse_options["titles"] = titles
        parse_options["targets"] = targets

    reports_file = []
    for code, parse_options, filter_options, config_dynamic in \
                (get_hunks_version if version_options else get_hunks_file) \
                (path, parse_options, version_options):
        if filename_prev != code.filename:
            if print_options["sort_key"]:
                filename_prev = print_reports(reports_file, print_options,
                                              filename_prev, is_final=False)
            reports.extend(reports_file)
            reports_file = []

        if show_current:
            monostyle_io.print_over("processing:", "{0}[{1}-{2}]"
                                    .format(monostyle_io.path_to_rel(code.filename),
                                            code.start_lincol[0], code.end_lincol[0]),
                                    is_temp=True)

        document = rst_parser.document(code=code)
        if parse_options["parse"] and document.code.filename.endswith(".rst"):
            document = rst_parser.parse(document)
            if parse_options["post"]:
                document = hunk_post_parser.parse(rst_parser, document)
            if (parse_options["resolve"] and
                    "titles" in parse_options.keys() and "targets" in parse_options.keys()):
                document = env.resolve_link_title(document, parse_options["titles"],
                                                  parse_options["targets"])
                document = env.resolve_subst(document, rst_parser.substitution)

        do_sort = bool(print_options["sort_key"])
        for ops, ext_test in mods:
            if ext_test and not document.code.filename.endswith(ext_test):
                continue

            for op in ops:
                # init failed
                if op[2] is None:
                    continue

                if "config" in op[2]:
                    op[2]["config"].update(config_dynamic)

                reports_tool = []
                reports_tool = op[1](op[0], document, reports_tool, **op[2])

                for report in reports_tool:
                    if not filter_options or not filter_reports(report, filter_options):
                        if not do_sort:
                            filename_prev = print_report(report, print_options, filename_prev)
                        reports_file.append(report)

    reports.extend(reports_file)
    if print_options["sort_key"]:
        filename_prev = print_reports(reports_file, print_options, filename_prev, is_final=False)

    if print_options["show_summary"]:
        reports_summary(reports, print_options)

    if show_current:
        monostyle_io.print_over("processing: done")

    if rst_parser.warnings:
        print('\n'.join(rst_parser.warnings))
    return reports


def update(path=None, rev=None):
    """Update the working copy."""
    if not path:
        path = monostyle_io.path_to_abs("")
    filenames_conflicted = set()
    for filename, conflict, rev_up in vsn_inter.update_files(path, rev):
        # A conflict will be resolvable with versioning's command interface.
        if conflict:
            filenames_conflicted.add(filename)
    return filenames_conflicted


# ----------------------------------------------------------------------------

def patch_flavor(filename):
    """Detect whether the patch is Git flavor."""
    try:
        with open(filename, "r") as patch_file:
            for line in patch_file:
                if line.startswith("Index: "):
                    return False
                if line.startswith("diff --git "):
                    return True

    except (IOError, OSError) as err:
        print("{0}: cannot open: {1}".format(filename, err))

    except UnicodeError as err:
        print("{0}: encoding error: {1}".format(filename, err))



def setup(root, patch=None):
    """Setup user config and file storage."""
    cwd = monostyle_io.norm_path_sep(os.getcwd())
    if root is not None:
        if not os.path.exists(os.path.normpath(root)):
            print('Error: root {0} does not exists'.format(root))
            return False, False

        root = monostyle_io.norm_path_sep(root)
        if len(cwd) < len(root) and root.startswith(cwd):
            cwd, root = root, cwd

        if not cwd.startswith(root):
            cwd = root
    else:
        root = cwd

    os.chdir(root)

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
            return False, is_repo

    global vsn_inter
    vsn_inter = import_module("git_inter" if is_git else "svn_inter", "vsn_inter")

    config_dir = os.path.normpath(os.path.join(root, "monostyle"))
    use_default_config = False
    if not os.path.isdir(config_dir):
        if monostyle_io.ask_user(
                "Create user config folder in '", root, "'",
                "" if is_repo else
                " even though it's not the top folder of a repository"):

            try:
                os.mkdir(config_dir)

            except (IOError, OSError) as err:
                print("{0}: cannot create: {1}".format(config_dir, err))
                return False, is_repo
        else:
            use_default_config = True

    success = config.init(root, cwd[len(root):], use_default_config)
    if success:
        Report.override_templates(config.template_override)
    return success, is_repo


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
                       dest="filename", nargs='?', const="",
                       help="check working copy file or directory FILENAME")

    parser.add_argument("-r", "--root",
                        dest="root", nargs='?', const="",
                        help="defines the ROOT directory of the project")

    if not is_selection:
        parser.add_argument("--cached", "--staged",
                            action="store_true", dest="cached", default=False,
                            help="set diff cached option (Git only)")

        parser.add_argument("--unversioned", "--untracked",
                            action="store_true", dest="unversioned", default=False,
                            help="include unversioned files")

    parser.add_argument("-s", "--resolve",
                        action="store_true", dest="do_resolve", default=False,
                        help="resolve link titles and substitutions")


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

    setup_sucess, is_repo = setup(args.root, args.patch)
    if not setup_sucess:
        return 2

    if not args.auto and "console_options" in vars(config).keys():
        config.console_options["show_autofix"] = False

    if mod_selection is None:
        mods = init_tools()
    else:
        mods = ((init(mod_selection[0], args.op_names, mod_selection[2]), mod_selection[1]),)
    rst_parser = RSTParser()
    if not parse_options:
        parse_options = {"parse": True, "resolve": False, "post": False}
    parse_options["resolve"] = args.do_resolve
    version_options = None
    path = None
    if args.filename is None and (mod_selection is None or args.patch is not None):
        parse_options["post"] = True
        version_options = {
            "from_vsn": bool(args.patch is None),
            "is_internal": bool(args.internal is not None or args.external is None),
            "rev" : None,
            "cached": args.cached,
            "unversioned": args.unversioned}
        if args.patch is None:
            if args.internal:
                version_options["rev"] = args.internal.strip()
            elif args.external:
                version_options["rev"] = args.external.strip()
        else:
            path = args.patch
            if not os.path.exists(path):
                print('Error: file {0} does not exists'.format(path))
                return 2
    else:
        path = args.filename

    if path:
        path = monostyle_io.norm_path_sep(path)
    if version_options and version_options["from_vsn"] and not is_repo:
        print("error: directory is not a repository")
        return 2

    reports = apply(mods, path, rst_parser, parse_options, version_options)
    if args.patch is not None:
        for report in reports:# custom root
            report.output.filename = monostyle_io.path_to_abs(report.output.filename, "cwd")

    filenames_conflicted = None
    if not is_selection:
        if args.up or (args.auto and args.external is not None):
            filenames_conflicted = update(rev=args.up)

    if args.auto:
        if ((is_selection or not (args.external or args.patch) or
                monostyle_io.ask_user("Apply autofix on possibly altered sources")) and
                (not is_selection or args.filename or
                 monostyle_io.ask_user("Apply autofix on the entire project"))):
            autofix.run(reports, rst_parser, filenames_conflicted)
    if args.min_severity:
        file_opener.open_reports_files(reports, args.min_severity)


if __name__ == "__main__":
    main()
