
"""
util.file_opener
~~~~~~~~~~~~~~~~

Open files in a text editor.
"""

import os.path
import subprocess

from monostyle.util.monostyle_io import ask_user, print_over, path_to_rel, split_path_appendix
from monostyle.util.report import Report


# For other text editors see:
# https://developer.blender.org/diffusion/BM/browse/trunk/blender_docs/tools/open_quickfix_in_editor.py

def run(path, lincol):
    """Open the editor via cmd."""
    cmd = ("notepad++",
           "-n" + str(lincol[0] + 1),
           "-c" + str(lincol[1] + 1), path)
    try:
        with subprocess.Popen(cmd, shell=False) as proc:
            proc.wait()
            return proc.returncode
    except OSError:
        print("text editor to open not found")
    except ValueError as err:
        print("open text editor:", err)


def open_reports_files(reports, min_severity=None):
    """Create a list of files in the reports."""
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
    """Opens a list of files."""
    nonexistents = []
    warning_limit = 100
    count = 0
    for filename, lincol in files:
        if show_current:
            print_over("opening: {0}".format(path_to_rel(filename)), is_temp=True)

        # avoid all files in folder and "want to create file" dialog
        if os.path.isfile(filename):
            exitcode = run(filename, lincol)
            if exitcode is None:
                break

            if count > warning_limit:
                if ask_user("Opened more than {0} files ".format(warning_limit),
                            "do you want to continue"):
                    count = 0
                else:
                    break
            count += 1
        else:
            nonexistents.append(filename + ":" + str(lincol[0] + 1) + ":" + str(lincol[1] + 1))

    if show_current:
        print_over("opening: done")

    if len(nonexistents) != 0:
        print("Failed to open {0} of {1} files.".format(len(nonexistents), len(files)))
        print("Enter this command to retry:")
        print("python file_opener.py", '"' + ','.join(nonexistents) + '"')


def main(argv=None):
    """Inputs a comma-separated list of filenames
    with optional lineno and colno split by double colons.
    """
    import sys
    if argv is None:
        argv = sys.argv[1:]
    del sys

    if len(argv) == 0 or argv[0] == "":
        print("No files given")
        return None

    files = []
    for entry in argv[0].split(','):
        path, appendix = split_path_appendix(entry)
        lineno = 1
        colno = 1
        if appendix:
            lineno, _, colno = appendix.partition(':')
            if not colno:
                colno = 1

        files.append((path, (int(lineno) - 1, int(colno) - 1)))

    open_files(files)


if __name__ == "__main__":
    main()
