
"""
autofix
~~~~~~~

Apply autofixes to the working copy.
"""

import monostyle.util.monostylestd as monostylestd
import monostyle.reflow
from monostyle.util.editor import Editor


def run(reports, rst_parser):
    """Sort reports into groups for each fix tool."""
    group_tool = []
    for report in reports:
        if report.fix == "reflow":
            group_tool.append(report)

    if len(group_tool) != 0:
        group_tool.sort(key=lambda report: report.out.fn)
        group_fn = []
        for report_tool in group_tool:
            if len(group_fn) != 0 and group_fn[-1].out.fn != report_tool.out.fn:
                apply(group_fn, rst_parser)
                group_fn.clear()

            group_fn.append(report_tool)

        if len(group_fn) != 0:
            apply(group_fn, rst_parser)


def apply(group_fn, rst_parser):
    """Run the fix tool and apply the changes to the file."""
    fn, text = monostylestd.single_text(group_fn[0].out.fn)
    if text is not None:
        document = rst_parser.parse_full(rst_parser.document(fn, text))

        changes, unlocated = monostyle.reflow.fix(document.body, group_fn)
        if len(changes) != 0:
            editor = Editor(document.body.code)
            for change in changes:
                editor.add(change)

            editor.apply(False, pos_lc=False)

        if len(unlocated) != 0:
            monostylestd.print_title("Reflow Unlocated Reports", underline='-')
            monostylestd.print_reports(unlocated)
