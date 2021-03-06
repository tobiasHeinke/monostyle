
"""
monitor
~~~~~~~

Monitor files for changes.
"""

import re
import monostyle.util.monostylestd as monostylestd
from monostyle.util.report import Report


def check_pre(_):
    args = dict()
    args["data"] = monostylestd.get_override(__file__, "check", "fns", [])
    return args


def check(document, reports, data):
    toolname = "monitor"

    if len(data) == 0:
        return reports

    filename = monostylestd.path_to_rel(document.code.filename)
    if filename.startswith('/'):
        filename = filename[1:]

    for entry in data:
        if entry.startswith('/'):
            entry = entry[1:]

        message = ""
        # match all subfolders
        if entry.endswith('/'):
            if re.match(entry, filename):
                message = "changed in " + entry
        else:
            # match file
            if re.match(r"\.[A-Za-z\d]*?$", entry):
                if filename == entry:
                    message = "changed"
            else:
                # match folder
                if re.match(entry + r"\/[^/]+?$", filename):
                    message = "changed in " + entry

        if message != "" and filename not in check.reg:
            output = document.body.code.copy().clear(True)
            reports.append(Report('I', toolname, output, message))
            check.reg.append(filename)

    return reports

check.reg = []

OPS = (("check", check, check_pre),)
