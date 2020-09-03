
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

    for ent in data:
        if ent.startswith('/'):
            ent = ent[1:]

        msg = ""
        # match all subfolders
        if ent.endswith('/'):
            if re.match(ent, filename):
                msg = "changed in " + ent
        else:
            # match file
            if re.match(r"\.[A-Za-z\d]*?$", ent):
                if filename == ent:
                    msg = "changed"
            else:
                # match folder
                if re.match(ent + r"\/[^/]+?$", filename):
                    msg = "changed in " + ent

        if msg != "" and filename not in check.reg:
            out = document.body.code.copy().clear(True)
            reports.append(Report('I', toolname, out, msg))
            check.reg.append(filename)

    return reports

check.reg = []

OPS = (("check", check, check_pre),)
