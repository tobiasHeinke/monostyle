
"""
svn_inter
~~~~~~~~~

Interface to SVN.
"""
# Based on https://developer.blender.org/diffusion/BM/browse/trunk/blender_docs/tools/svn_commit.py


import os
import re
import subprocess

from monostyle.util.monostyle_io import print_over
from monostyle.util.fragment import Fragment


def get_revision(path):
    for line in info(path):
        line = line.decode("utf-8")
        if m := re.match(r"Revision\:\s(\d+)", line):
            return m.group(1)

    return "Unknown"


def unversioned_files(path, binary_ext):
    for line in status(True, path):
        line = line.decode('utf-8')
        if line.startswith('?'):
            filename = norm_path_sep(line[8:].strip())
            if filename.startswith('.') or os.path.isdir(filename):
                continue
            if binary_ext is not None and os.path.splitext(filename)[1] in binary_ext:
                continue

            yield filename


def difference(from_vsn, is_internal, filename_source, rev, binary_ext):
    op = diff if from_vsn else file_diff

    is_change = False
    if rev is None:
        rev = "BASE"
        if not is_internal:
            rev += ":HEAD"
    else:
        rev = rev.strip()
        is_change = bool(rev.find("-") != -1)
        if is_change:
            rev_split = rev.split('-')
            if is_internal:
                if not (len(rev_split) == 1 or rev_split[0].upper() != "BASE"):
                    print("svn diff internal use external for revision ranges instead")
                    return None
            else:
                if len(rev_split[1]) == 0:
                    rev += "HEAD"

        else:
            rev_split = rev.split(':')
            if len(rev_split) == 1:
                if is_internal:
                    rev = "BASE:" + rev
                else:
                    is_change = True
            else:
                if is_internal:
                    if len(rev_split[0]) == 0:
                        rev = "BASE" + rev
                    elif rev_split[0].upper() != "BASE":
                        print("svn diff internal use external for revision ranges instead")
                        return None
                else:
                    if len(rev_split[0]) == 0:
                        rev = "BASE" + rev
                    if len(rev_split[1]) == 0:
                        rev += "HEAD"

    lineno = 0
    context = []
    skip = False
    fg = None
    loc_re = re.compile(r"@@ \-\d+?(?:,\d+?)? \+(\d+?)(?:,\d+?)? @@")
    body = False
    for line in op(filename_source, rev, is_change):
        try:
            line = line.decode("utf-8")
        except:
            # binary: skip
            continue

        if line.startswith("Index: "):
            filename = line[len("Index: "):]
            filename = norm_path_sep(filename)
            # skip whole file
            skip = bool(binary_ext is not None and os.path.splitext(filename)[1] in binary_ext)
            body = False

        elif (line.startswith("Property changes on: ") or
                line.startswith("Cannot display: file marked as a binary type.")):
            # skip svn properties block at eof
            skip = True

        if skip:
            continue

        if line.startswith("@@"):
            if fg is not None and len(fg.content) != len(context):
                yield fg, context, None

            loc_m = re.match(loc_re, line)
            start_lincol = (int(loc_m.group(1)) - 1, 0)
            fg = Fragment(filename, [], 0, 0, start_lincol, start_lincol)
            context = []
            lineno = start_lincol[0]
            body = True

        elif body:
            if line.startswith(' '):
                fg.extend(line[1:] + '\n')
                context.append(lineno)
                lineno += 1
            elif line.startswith('+'):
                fg.extend(line[1:] + '\n')
                lineno += 1

            elif line.startswith('\\'):
                message = line[2:] # backslash + space
                fg_copy = fg.copy().clear(False)
                yield fg_copy, None, message

    if fg and len(fg.content) != len(context):
        yield fg, context, None


def update_files(path, rev=None):
    rev_up = ""
    for line in update(path, rev):
        line = line.decode('utf-8')
        if len(line) != 0:
            if line.startswith("Updating "):
                continue
            if line.startswith("Updated to"):
                rev_up = line.replace("Updated to revision ", "").strip()
                if rev_up.endswith('.'):
                    rev_up = rev_up[:-1]
                print(line)
            else:
                conflict = bool(line[0] == 'C')
                filename = line[5:].rstrip()
                filename = norm_path_sep(filename)

                yield filename, conflict, rev_up


def info(path):
    cmd = ["info", path]
    return exec_command(cmd)


def status(is_internal, path):
    cmd = ["status"]
    if not is_internal:
        cmd.append("-u")# --show-updates

    cmd.append(path)
    return exec_command(cmd)


def diff(path, rev, is_change=False):
    cmd = ["diff"]
    if not is_change:
        cmd.append("-r")
    else:
        cmd.append("-c")
    cmd.append(rev)

    cmd.append("--non-interactive")
    cmd.append(path)
    return exec_command(cmd)


def update(path, rev=None):
    if path == "":
        print("svn update empty parameter")
        return None

    cmd = ["update", path]
    if rev:
        cmd.append("-r")
        cmd.append(rev)
    return exec_command(cmd)


# -------------


def add(path):
    if path == "":
        print("svn add empty parameter")
        return None

    cmd = ["add", path]
    return exec_command(cmd)


def delete(path):
    if path == "":
        print("svn delete empty parameter")
        return None

    cmd = ["delete", path]
    return exec_command(cmd)


def move(src, dst):
    if src == "" or dst == "":
        print("svn move empty parameter")
        return None

    cmd = ["move", src, dst]
    return exec_command(cmd)


# -------------


def prop_get(path, name):
    if path == "":
        print("svn propget empty parameter")
        return None

    cmd = ["propget", name, path]
    return exec_command(cmd)


def prop_set(path, name, value):
    if path == "":
        print("svn propset empty parameter")
        return None

    cmd = ["propset", name, value, path]
    return exec_command(cmd)


def prop_delete(path, name):
    if path == "":
        print("svn propdel empty parameter")
        return None

    cmd = ["propdel", name, path]
    return exec_command(cmd)


def prop_keys(path):
    if path == "":
        print("svn proplist empty parameter")
        return None

    cmd = ["proplist", path]
    return exec_command(cmd)


def exec_command(cmd_args):
    cmd = ["svn"]
    cmd.extend(cmd_args)

    silent = bool(cmd_args[0] in {"info", "propget", "proplist"})
    try:
        if not silent:
            print_over("fetching" if cmd_args[0] in {"status", "diff", "update"}
                       else "applying", cmd_args[0], ellipsis="...")
        output = subprocess.check_output(cmd)
    except OSError as err:
        print("svn", cmd_args[0], "error:", err)
    except ValueError as err:
        print("svn", cmd_args[0], "error:", err)
    except Exception as err:
        print("svn", cmd_args[0], "unexpected error", err)
    else:
        if not silent:
            print_over("done")
        return output.splitlines()


def file_diff(filename, rev=None, is_change=False):
    if not (filename.endswith(".diff") or filename.endswith(".patch")):
        print("diff wrong file format:", filename)
        return None

    try:
        with open(filename, "rb") as f:
            text = f.read()

        return text.splitlines()

    except (IOError, OSError) as err:
        print("{0}: cannot open: {1}".format(filename, err))


def norm_path_sep(path):
    path = re.sub(r"\\", "/", path)
    return re.sub(r"//+", "/", path)


def run_diff(from_vsn, is_internal, path, rev, cached=None):
    if from_vsn:
        print("Current revision:", get_revision(path))

    binary_ext = {".png", ".jpg", ".jpeg", ".gif", ".pyc"}
    if from_vsn and is_internal:
        for filename in unversioned_files(path, binary_ext):
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    text = f.read()
            except (IOError, OSError) as err:
                print("{0}: cannot open: {1}".format(filename, err))
            else:
                yield Fragment(filename, text), None, None

    yield from difference(from_vsn, is_internal, path, rev, binary_ext)
