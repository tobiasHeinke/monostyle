
"""
autofix
~~~~~~~

Apply autofixes to the working copy.

report.fix
Str name of the fixing tool or
Fragment or FragmentBundle.
"""

import monostyle.reflow

import monostyle.util.monostyle_io as monostyle_io
from monostyle.util.editor import Editor
from monostyle.util.fragment import Fragment, FragmentBundle
from monostyle.util.report import print_reports


def run(reports, rst_parser, filenames_conflicted=None):
    """Sort reports into groups for each fix tool."""
    monostyle_io.print_over("autofix", ellipsis="...")

    group_fix = []
    for report in reports:
        if report.fix is not None:
            group_fix.append(report)

    if len(group_fix) == 0:
        monostyle_io.print_over("done")
        return None

    group_file = {}
    for report in group_fix:
        filename = monostyle_io.path_to_abs(report.output.filename, "doc")
        if filename not in group_file.keys():
            group_file.setdefault(filename, {})

        tool = report.fix if isinstance(report.fix, str) else "generic"
        if tool not in group_file[filename].keys():
            group_file[filename].setdefault(tool, [])

        group_file[filename][tool].append(report)

    reports_unfixed = []
    for filename, tools in group_file.items():
        if not filenames_conflicted or filename not in filenames_conflicted:
            reports_unfixed = apply(filename, tools, reports_unfixed, rst_parser)
        else:
            for reports_tool in tools.values():
                reports_unfixed.extend(reports_tool)

    monostyle_io.print_over("done")
    if len(reports_unfixed) != 0:
        monostyle_io.print_title("Conflicted/Unlocated Reports", underline='-')
        print_reports(reports_unfixed)


def apply(filename, tools, reports_unfixed, rst_parser):
    """Run the fix tool and apply the changes to the file."""
    def search_conflicted(fg_conflict, tools):
        for reports in tools.values():
            for report in reports:
                for change in report.fix:
                    if change is fg_conflict:
                        return report

    def filter_tool_overlap(changes_file, changes):
        """Filter out space at eol also removed by reflow."""
        new_changes = FragmentBundle()
        for entry_old in changes_file:
            for entry in changes:
                if entry.start_lincol == entry_old.start_lincol and len(entry_old) == 0:
                    break
            else:
                new_changes.combine(entry_old, check_align=False, merge=False)

        return new_changes.combine(changes, check_align=False, merge=False)

    filename = monostyle_io.path_to_abs(filename, "doc")
    filename, text = monostyle_io.single_text(filename)
    if text is None:
        return reports_unfixed.extend(tools[1])

    changes_file = FragmentBundle()
    fg = None
    for tool, reports in tools.items():
        if tool == "reflow":
            document = rst_parser.parse(rst_parser.document(filename, text))
            fg = document.code
            changes, unlocated = monostyle.reflow.fix(document.body, reports)

            changes_file = filter_tool_overlap(changes_file, changes)
            reports_unfixed.extend(unlocated)
        else:
            for report in reports:
                changes_file.combine(report.fix, check_align=False, merge=False)

    if changes_file.is_empty():
        return reports_unfixed

    editor = Editor(fg if fg is not None else Fragment(filename, text), changes_file)
    _, conflicted = editor.apply(False, pos_lincol=False, use_conflict_handling=True)

    if len(conflicted) != 0:
        for fg_conflict in conflicted:
            report_conflict = search_conflicted(fg_conflict, tools)
            if report_conflict:
                reports_unfixed.append(report_conflict)

    return reports_unfixed
