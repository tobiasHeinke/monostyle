
"""
autofix
~~~~~~~

Apply autofixes to the working copy.

report.fix
Str name of the fixing tool or
Fragment or List of as replacements.
"""

import monostyle.reflow

import monostyle.util.monostylestd as monostylestd
from monostyle.util.editor import Editor
from monostyle.util.fragment import Fragment
from monostyle.util.report import print_reports


def run(reports, rst_parser):
    """Sort reports into groups for each fix tool."""
    print("autofix: ...", end="")

    group_fix = []
    for report in reports:
        if report.fix is not None:
            group_fix.append(report)

    if len(group_fix) == 0:
        print("\b" * 3 + "done")
        return None

    group_fn = {}
    for report in group_fix:
        fn = report.out.fn
        if fn not in group_fn.keys():
            group_fn.setdefault(fn, {})

        tool = report.fix if isinstance(report.fix, str) else "generic"
        if tool not in group_fn[fn].keys():
            group_fn[fn].setdefault(tool, [])

        group_fn[fn][tool].append(report)

    reports_unfixed = []
    for fn, tools in group_fn.items():
        reports_unfixed = apply(fn, tools, reports_unfixed, rst_parser)

    print("\b" * 3 + "done")
    if len(reports_unfixed) != 0:
        monostylestd.print_title("Conflicted/Unlocated Reports", underline='-')
        print_reports(reports_unfixed)


def apply(fn, tools, reports_unfixed, rst_parser):
    """Run the fix tool and apply the changes to the file."""
    def search_conflicted(fg_conflict, tools):
        for reports in tools.values():
            for report in reports:
                if isinstance(report.fix, list):
                    for change in report.fix:
                        if change is fg_conflict:
                            return report
                else:
                    if report.fix is fg_conflict:
                        return report


    fn, text = monostylestd.single_text(fn)
    if text is None:
        return reports_unfixed.extend(tools[1])

    changes_file = []
    fg = None
    for tool, reports in tools.items():
        if tool == "reflow":
            document = rst_parser.parse_full(rst_parser.document(fn, text))
            fg = document.code
            changes, unlocated = monostyle.reflow.fix(document.body, reports)

            changes_file.extend(changes)
            reports_unfixed.extend(unlocated)
        else:
            for report in reports:
                if isinstance(report.fix, list):
                    changes_file.extend(report.fix)
                else:
                    changes_file.append(report.fix)

    if len(changes_file) == 0:
        return reports_unfixed

    # filter out space at eol removed already by reflow
    new_changes = []
    for ent in changes_file:
        for ent_new in new_changes:
            if (ent.start_lincol == ent_new.start_lincol and
                    str(ent_new) == '\n' * len(ent_new) and
                    ent.isspace()):
                break
        else:
            new_changes.append(ent)

    changes_file = new_changes

    if fg is None:
        fg = Fragment(fn, text)
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
