
"""
util.file_opener
~~~~~~~~~~~~~~~~

Open files in a text editor.
"""

import os
import sys
import subprocess

from monostyle.util.monostylestd import path_to_rel
from monostyle.util.report import Report


# For other text editors see:
# https://developer.blender.org/diffusion/BM/browse/trunk/blender_docs/tools/open_quickfix_in_editor.py

def run(path, lincol):
    cmd = ("notepad++",
           "-n" + str(lincol[0] + 1),
           "-c" + str(lincol[1] + 1), path)
    try:
        proc = subprocess.Popen(cmd, shell=False)
        proc.wait()
        return proc.returncode
    except OSError:
        print("text editor to open not found")
    except ValueError as err:
        print("open text editor:", err)


def open_reports_files(reports, min_severity=None):
    levels = list(Report.severities)
    if min_severity is not None:
        levels = levels[:levels.index(min_severity.upper()) +1]

    files = []
    for report in reports:
        if report.severity in levels:
            for fn, _ in files:
                if fn == report.out.fn:
                    break
            else:
                files.append((report.out.fn, report.out.start_lincol))

    open_files(files, True)


def open_files(files, show_current=False):
    nonexistents = []
    for fn, lincol in files:
        if show_current:
            print("\ropening: {0}".format(path_to_rel(fn)), end='', flush=True)

        # avoid all files in folder and "want to create file" dialog
        if os.path.isfile(fn):
            exitcode = run(fn, lincol)
            if exitcode is None:
                break
        else:
            nonexistents.append(fn + ":" + str(lincol[0] + 1) + ":" + str(lincol[1] + 1))

    if show_current:
        print("\ropening: done")

    if len(nonexistents) != 0:
        print("Failed to open {0} of {1} files.".format(len(nonexistents), len(files)))
        print("Enter this command to retry:")
        print("python file_opener.py", '"' + ','.join(nonexistents) + '"')


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    if len(argv) == 0 or argv[0] == "":
        print("No files given")
        return None


    files_str = argv[0].split(',')
    files = []
    for ent in files_str:
        colno = "0"
        lineno = "0"
        path = ent
        # search only after file extension
        dot_idx = ent.rfind('.')
        last_idx = ent.rfind(':', dot_idx)
        if last_idx != -1:
            penul_idx = ent.rfind(':', dot_idx, last_idx)
            if penul_idx != -1:
                path = ent[:penul_idx]
                lineno = ent[penul_idx+1:last_idx]
                colno = ent[last_idx+1:]
            else:
                path = ent[:last_idx]
                lineno = ent[last_idx+1:]

        files.append((path, (int(lineno) - 1, int(colno) - 1)))

    open_files(files)


if __name__ == "__main__":
    main()
