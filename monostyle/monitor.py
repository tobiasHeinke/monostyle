
"""
monitor
~~~~~~~

Monitor files for changes.
"""

import re
import monostyle.util.monostylestd as monostylestd
from monostyle.util.report import Report

def init(_):
    fns = monostylestd.get_override(__file__, "init", "fns", [])
    return ((check, {"data": fns}),)


def check(document, reports, data):
    toolname = "monitor"

    if len(data) == 0:
        return reports

    fn = monostylestd.path_to_rel(document.code.fn)
    if fn.startswith('/'):
        fn = fn[1:]

    for ent in data:
        if ent.startswith('/'):
            ent = ent[1:]

        msg = ""
        # match all subfolders
        if ent.endswith('/'):
            if re.match(ent, fn):
                msg = "changed in " + ent
        else:
            # match file
            if re.match(r"\.[A-Za-z\d]*?$", ent):
                if fn == ent:
                    msg = "changed"
            else:
                # match folder
                if re.match(ent + r"\/[^/]+?$", fn):
                    msg = "changed in " + ent

        if msg != "" and fn not in check.reg:
            out = document.body.code.copy()
            out.clear(True)
            reports.append(Report('I', toolname, out, msg))
            check.reg.append(fn)

    return reports

check.reg = []
