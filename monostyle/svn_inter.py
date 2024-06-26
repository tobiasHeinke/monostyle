
"""
svn_inter
~~~~~~~~~

Interface to SVN.
"""
# Based on https://projects.blender.org/blender/blender-manual/src/branch/blender-v3.3-release/tools/svn_commit.py


import os
import re
import subprocess

from monostyle.util.monostyle_io import print_over, single_text
from monostyle.util.fragment import Fragment, FragmentBundle


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


def difference(from_vsn, path, is_internal=True, rev=None, binary_ext=None):
    is_change = False
    if not rev:
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

    loc_re = re.compile(r"@@ \-\d+?(?:,\d+?)? \+(\d+?)(?:,\d+?)? @@")
    source_all = None
    changes_all = None
    skip = False
    body = False
    control_prev = None
    for line in (diff if from_vsn else file_diff)(path, rev, is_change):
        try:
            line = line.decode("utf-8")
        except UnicodeError:
            # binary: skip
            continue

        if line.startswith("Index: "):
            filename = norm_path_sep(line[len("Index: "):])
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
            if source_all is not None:
                yield source_all, changes_all

            source_all = Fragment(filename, [],
                                  start_lincol=(int(re.match(loc_re, line).group(1)) - 1, 0))
            changes_all = FragmentBundle()
            source = None
            changes = None
            body = True

        elif body:
            control, line = ((line[:1], line[1:] + '\n') if not line.startswith('\\') else
                             (line[:2], line[2:] + '\n'))
            if control == '+':
                if changes is None:
                    changes = Fragment(filename, line)
                    if source:
                        changes.copy_loc(source)
                    else:
                        changes.set_start(source_all.end_pos, source_all.end_lincol)
                        changes.set_end(source_all.end_pos, source_all.end_lincol)
                else:
                    changes.extend(line, keep_end=True)
            elif control == '-':
                if source is None:
                    source = Fragment(filename, line, source_all.end_pos,
                                      start_lincol=source_all.end_lincol)
                else:
                    source.extend(line)
                    if changes is not None:
                        changes.set_end(source.end_pos, source.end_lincol)
            elif control == ' ':
                if source is not None:
                    source_all.combine(source)
                    source = None
                if changes is not None:
                    changes_all.combine(changes, merge=False)
                    changes = None

                source_all.extend(line)
            elif control == '\\':
                if line == "No newline at end of file\n":
                    if control_prev == '+':
                        changes = changes.slice(
                            end=changes.rel_to_start(-2), is_rel=True)
                    elif control_prev == '-':
                        source = source.slice(
                            end=source.rel_to_start(-2), is_rel=True)
                    elif control_prev == ' ':
                        source_all = source_all.slice(
                            end=source_all.rel_to_start(-2), is_rel=True)
                else:
                    print("{0}:{1}: unexpected version control message: {2}"
                          .format(source_all.filename, source_all.end_lincol[0], line))
            control_prev = control if control in "+- " else control_prev

    if source is not None:
        source_all.combine(source)
    if changes is not None:
        changes_all.combine(changes, merge=False)
    if changes_all:
        yield source_all, changes_all


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
                # filename, conflict
                yield norm_path_sep(line[5:].rstrip()), bool(line[0] == 'C'), rev_up


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


# ----------------------------------------------------------------------------

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


# ----------------------------------------------------------------------------

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
    except (OSError, ValueError) as err:
        print("svn", cmd_args[0], "error:", err)
    except subprocess.CalledProcessError as err:
        print("svn", cmd_args[0], "error:", err)
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


def run_diff(from_vsn, is_internal, path, rev, cached=None, unversioned=False):
    if from_vsn:
        print("Current revision:", get_revision(path))

    binary_ext = {".png", ".jpg", ".jpeg", ".gif", ".pyc"}
    if from_vsn and is_internal and unversioned:
        for filename in unversioned_files(path, binary_ext):
            filename, text = single_text(filename)
            if text:
                yield Fragment(filename, text), None

    yield from difference(from_vsn, path, is_internal, rev, binary_ext)
