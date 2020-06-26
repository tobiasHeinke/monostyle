
"""
svn_inter
~~~~~~~~~

Interface to SVN.
"""
# Based on https://developer.blender.org/diffusion/BM/browse/trunk/blender_docs/tools/svn_commit.py


import os
import re
import subprocess

from monostyle.util.fragment import Fragment


def added_files(is_internal, path):
    rev_max = 0
    for line in status(is_internal, path):
        line = line.decode('utf-8')
        if line.startswith("Status "):
            continue

        add_mod = bool(not line[0] in ('D', 'R')) #," "

        if is_internal:
            new = bool(line[0] in ('?', 'A'))

            fn = line[8:].rstrip()
            rev_file = "BASE"
        else:
            new = bool(line[8] != '*')

            fn = line[21:].rstrip()
            rev_file = line[12:18].lstrip()
            if rev_file.isdigit():
                rev_max = max(rev_max, int(rev_file))

        fn = replace_windows_path_sep(fn)
        if fn.startswith('.'):
            continue

        yield fn, new, add_mod, rev_file

    if not is_internal:
        print("Highest revision is", rev_max)


def difference(from_vsn, is_internal, fn_source, rev, changed_files):
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
    for line in op(fn_source, rev, is_change):
        try:
            line = line.decode("utf-8")
        except:
            # binary: skip
            continue

        if line.startswith("Index: "):
            fn = line[len("Index: "):]
            fn = replace_windows_path_sep(fn)
            # skip whole file
            skip = bool(not(changed_files is None or fn in changed_files))
            body = False

        elif line.startswith("Property changes on: "):
            # skip svn properties block at eof
            skip = True

        elif line.startswith("Cannot display: file marked as a binary type."):
            skip = True

        if skip:
            continue

        if line.startswith("@@"):
            if fg is not None and len(fg.content) != len(context):
                yield fg, context, None

            loc_m = re.match(loc_re, line)
            start_lincol = (int(loc_m.group(1)) - 1, 0)
            fg = Fragment(fn, [], 0, 0, start_lincol, start_lincol)
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
                msg = line[2:] # backslash + space
                out = fg.copy()
                out.clear(False)
                yield out, None, msg

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
                fn = line[5:].rstrip()
                fn = replace_windows_path_sep(fn)

                yield fn, conflict, rev_up


def status(is_internal, path):
    if path == "":
        print("svn status empty parameter")
        return None

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

    silent = bool(cmd_args[0] in ("propget", "proplist"))
    try:
        if not silent:
            print("fetching" if cmd_args[0] in ("status", "diff", "update") else "applying",
                  cmd_args[0] + ": ...", end="")
        output = subprocess.check_output(cmd)
    except OSError as err:
        print("svn", cmd_args[0], "error:", err)
    except ValueError as err:
        print("svn", cmd_args[0], "error:", err)
    except Exception as err:
        print("svn", cmd_args[0], "unexpected error", err)
    else:
        if not silent:
            print("\b" * 3 + "done")
        return output.splitlines()


def file_diff(fn, rev=None, is_change=False):
    if not (fn.endswith(".diff") or fn.endswith(".patch")):
        print("diff wrong file format:", fn)
        return None

    try:
        with open(fn, "rb") as f:
            text = f.read()

        return text.splitlines()

    except (IOError, OSError) as err:
        print("{0}: cannot open: {1}".format(fn, err))


def replace_windows_path_sep(fn):
    return re.sub(r"\\", "/", fn)


def run_diff(from_vsn, is_internal, path, rev):
    def read_file(fn):
        try:
            with open(fn, "r", encoding="utf-8") as f:
                text = f.read()

            return text

        except (IOError, OSError) as err:
            print("{0}: cannot open: {1}".format(fn, err))


    if from_vsn:
        changed_files = []
        binary_ext = (".png", ".jpg", ".jpeg", ".gif", ".pyc")
        for fn, new, add_mod, rev_file in added_files(is_internal, path):
            if add_mod and not os.path.isdir(fn):
                if os.path.splitext(fn)[1] not in binary_ext:
                    if new and is_internal:
                        # unversioned
                        text = read_file(fn)
                        fg = Fragment(fn, text)
                        yield fg, None, None
                    else:
                        changed_files.append(fn)
    else:
        changed_files = None

    yield from difference(from_vsn, is_internal, path, rev, changed_files)
