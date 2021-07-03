
"""
monitor
~~~~~~~

Monitor files for changes.
"""

import re
import monostyle.util.monostyle_io as monostyle_io
from monostyle.util.report import Report


def check_pre(toolname):
    return {"config": dict(monostyle_io.get_override(__file__, toolname, "files", [str]))}


def check(toolname, document, reports, config):
    """"Report if monitored file is changed."""
    if len(config["files"]) == 0:
        return reports

    filename = monostyle_io.path_to_rel(document.code.filename).lstrip('/')
    if filename in check.register:
        return reports

    for entry in config["files"]:
        entry = entry.lstrip('/')
        where = None
        if entry.endswith('/'):
            # match all subfolders
            if re.match(entry, filename):
                where = "in " + entry
        else:
            # match file
            if re.match(r"\.[A-Za-z\d]*?$", entry):
                if filename == entry:
                    where = ""
            else:
                # match folder
                if re.match(entry + r"\/[^/]+?$", filename):
                    where = "in " + entry

        if where is not None:
            reports.append(Report('I', toolname, document.code.copy().clear(True),
                                  Report.existing(what="changed", where=where if where else None)))

            check.register.append(filename)
            break

    return reports

check.register = []

OPS = (("monitor", check, check_pre),)
