
"""
monitor
~~~~~~~

Monitor files for changes.
"""

import re
import monostyle.util.monostyle_io as monostyle_io
from monostyle.util.report import Report


def check_pre(toolname):
    return {"config": dict(monostyle_io.get_override(__file__, toolname, "files", []))}


def check(toolname, document, reports, config):
    """"Report if monitored file is changed."""
    if len(config) == 0:
        return reports

    filename = monostyle_io.path_to_rel(document.code.filename).lstrip('/')

    for entry in config["files"]:
        entry = entry.lstrip('/')
        message = None
        if entry.endswith('/'):
            # match all subfolders
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

        if message and filename not in check.register:
            output = document.code.copy().clear(True)
            reports.append(Report('I', toolname, output, message))
            check.register.append(filename)

    return reports

check.register = []

OPS = (("monitor", check, check_pre),)
