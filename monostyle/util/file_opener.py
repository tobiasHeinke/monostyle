
"""
util.file_opener
~~~~~~~~~~~~~~~~

Open files in a text editor.
"""

import os
import sys
import subprocess

from monostyle.util.monostylestd import print_over, path_to_rel
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
            for filename, _ in files:
                if filename == report.output.filename:
                    break
            else:
                files.append((report.output.filename, report.output.start_lincol))

    open_files(files, True)


def open_files(files, show_current=False):
    nonexistents = []
    for filename, lincol in files:
        if show_current:
            print_over("opening: {0}".format(path_to_rel(filename)), is_temp=True)

        # avoid all files in folder and "want to create file" dialog
        if os.path.isfile(filename):
            exitcode = run(filename, lincol)
            if exitcode is None:
                break
        else:
            nonexistents.append(filename + ":" + str(lincol[0] + 1) + ":" + str(lincol[1] + 1))

    if show_current:
        print_over("opening: done")

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
    for entry in files_str:
        colno = "0"
        lineno = "0"
        path = entry
        # search only after file extension
        dot_idx = entry.rfind('.')
        last_idx = entry.rfind(':', dot_idx)
        if last_idx != -1:
            penul_idx = entry.rfind(':', dot_idx, last_idx)
            if penul_idx != -1:
                path = entry[:penul_idx]
                lineno = entry[penul_idx+1:last_idx]
                colno = entry[last_idx+1:]
            else:
                path = entry[:last_idx]
                lineno = entry[last_idx+1:]

        files.append((path, (int(lineno) - 1, int(colno) - 1)))

    open_files(files)


if __name__ == "__main__":
    main()
