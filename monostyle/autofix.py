
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

    group_file = {}
    for report in reports:
        if report.fix is None:
            continue

        filename = monostyle_io.path_to_abs(report.output.filename, "doc")
        if filename not in group_file.keys():
            group_file.setdefault(filename, {})

        tool = report.fix if isinstance(report.fix, str) else "generic"
        if tool not in group_file[filename].keys():
            group_file[filename].setdefault(tool, [])

        group_file[filename][tool].append(report)

    if not group_file:
        monostyle_io.print_over("done")
        return

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
    def search_conflicted(change_conflicted, tools):
        for reports in tools.values():
            for report in reports:
                for change in report.fix:
                    if change is change_conflicted:
                        return report

    def filter_tool_overlap(changes_file, changes):
        """Filter out space at eol also removed by reflow."""
        new_changes = FragmentBundle()
        for entry_old in changes_file:
            for entry in changes:
                if entry_old.is_overlapped(entry, False) and entry_old.isspace():
                    break
            else:
                new_changes.combine(entry_old, check_align=False, merge=False)

        return new_changes.combine(changes, check_align=False, merge=False)

    filename = monostyle_io.path_to_abs(filename, "doc")
    filename, text = monostyle_io.single_text(filename)
    if text is None:
        return reports_unfixed.extend(tools[1])

    changes_file = FragmentBundle()
    source = None
    for tool, reports in tools.items():
        if tool == "reflow":
            continue
        for report in reports:
            changes_file.combine(report.fix, check_align=False, merge=False)

    if "reflow" in tools.keys():
        document = rst_parser.parse(rst_parser.document(filename, text))
        source = document.code
        changes, unlocated = monostyle.reflow.fix(document.body, tools["reflow"])

        changes_file = filter_tool_overlap(changes_file, changes)
        reports_unfixed.extend(unlocated)

    if not changes_file:
        return reports_unfixed

    editor = Editor(source if source is not None else Fragment(filename, text), changes_file)
    _, conflicted = editor.apply(False, pos_lincol=False, use_conflict_handling=True)

    if len(conflicted) != 0:
        for change_conflicted in conflicted:
            report_conflict = search_conflicted(change_conflicted, tools)
            if report_conflict and report_conflict not in reports_unfixed:
                reports_unfixed.append(report_conflict)

    return reports_unfixed
