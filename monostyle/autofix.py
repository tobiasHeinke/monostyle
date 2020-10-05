
"""
autofix
~~~~~~~

Apply autofixes to the working copy.

report.fix
Str name of the fixing tool or
Fragment or FragmentBundle.
"""

import monostyle.reflow

import monostyle.util.monostylestd as monostylestd
from monostyle.util.editor import Editor
from monostyle.util.fragment import Fragment, FragmentBundle
from monostyle.util.report import print_reports


def run(reports, rst_parser, fns_conflicted=None):
    """Sort reports into groups for each fix tool."""
    monostylestd.print_over("autofix", ellipsis="...")

    group_fix = []
    for report in reports:
        if report.fix is not None:
            group_fix.append(report)

    if len(group_fix) == 0:
        monostylestd.print_over("done")
        return None

    group_file = {}
    for report in group_fix:
        filename = report.output.filename
        if filename not in group_file.keys():
            group_file.setdefault(filename, {})

        tool = report.fix if isinstance(report.fix, str) else "generic"
        if tool not in group_file[filename].keys():
            group_file[filename].setdefault(tool, [])

        group_file[filename][tool].append(report)

    reports_unfixed = []
    for filename, tools in group_file.items():
        if not fns_conflicted or filename not in fns_conflicted:
            reports_unfixed = apply(filename, tools, reports_unfixed, rst_parser)
        else:
            for reports_tool in tools.values():
                reports_unfixed.extend(reports_tool)

    monostylestd.print_over("done")
    if len(reports_unfixed) != 0:
        monostylestd.print_title("Conflicted/Unlocated Reports", underline='-')
        print_reports(reports_unfixed)


def apply(filename, tools, reports_unfixed, rst_parser):
    """Run the fix tool and apply the changes to the file."""
    def search_conflicted(fg_conflict, tools):
        for reports in tools.values():
            for report in reports:
                if isinstance(report.fix, FragmentBundle):
                    for change in report.fix:
                        if change is fg_conflict:
                            return report
                else:
                    if report.fix is fg_conflict:
                        return report


    filename, text = monostylestd.single_text(filename)
    if text is None:
        return reports_unfixed.extend(tools[1])

    changes_file = []
    fg = None
    for tool, reports in tools.items():
        if tool == "reflow":
            document = rst_parser.parse(rst_parser.document(filename, text))
            fg = document.code
            changes, unlocated = monostyle.reflow.fix(document.body, reports)

            changes_file.extend(changes)
            reports_unfixed.extend(unlocated)
        else:
            for report in reports:
                changes_file.append(report.fix)

    if len(changes_file) == 0:
        return reports_unfixed

    # filter out space at eol removed already by reflow
    new_changes = []
    for entry in changes_file:
        for entry_new in new_changes:
            if (entry.start_lincol == entry_new.start_lincol and
                    str(entry_new) == '\n' * len(entry_new) and
                    entry.isspace()):
                break
        else:
            new_changes.append(entry)

    changes_file = new_changes

    if fg is None:
        fg = Fragment(filename, text)
    editor = Editor(fg)
    for change in changes_file:
        editor.add(change)

    _, conflicted = editor.apply(False, pos_lc=False, use_conflict_handling=True)

    if len(conflicted) != 0:
        for fg_conflict in conflicted:
            report_conflict = search_conflicted(fg_conflict, tools)
            if report_conflict:
                reports_unfixed.append(report_conflict)

    return reports_unfixed
