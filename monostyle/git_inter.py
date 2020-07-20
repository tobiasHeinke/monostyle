
"""
git_inter
~~~~~~~~~

Interface to Git.
"""

import os
import re
import subprocess

from monostyle.util.fragment import Fragment


def get_revision(path):
    for line in info(path):
        line = line.decode("utf-8")
        if m := re.match(r"commit\s(\S+)", line):
            return m.group(1)

    return "Unknown"


def unversioned_files(path, binary_ext):
    for line in status(path):
        line = line.decode('utf-8')
        if line.startswith('?'):
            fn = replace_windows_path_sep(line[3:].strip())
            if fn.startswith('.') or os.path.isdir(fn):
                continue
            if binary_ext is not None and os.path.splitext(fn)[1] in binary_ext:
                continue

            yield  path + "/" + fn


def difference(from_vsn, is_internal, fn_source, rev, cached):
    op = diff if from_vsn else file_diff

    is_change = False
    if rev is None:
        rev = "HEAD"
        if not is_internal:
            rev += "..remotes/origin/HEAD"

    lineno = 0
    context = []
    skip = False
    fg = None
    loc_re = re.compile(r"@@ \-\d+?(?:,\d+?)? \+(\d+?)(?:,\d+?)? @@")
    body = False
    for line in op(fn_source, rev, cached):
        try:
            line = line.decode("utf-8")
        except:
            # binary: skip
            continue

        if line.startswith("+++"):
            fn = line[len("+++ b/"):]
            fn = replace_windows_path_sep(fn)
            # skip whole file
            skip = False
            body = False

        elif line.startswith("Binary files"):
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
    on_merge = False
    for line in pull(path):
        line = line.decode('utf-8')
        if len(line) != 0:
            if line.startswith("Updating "):
                if m := re.search(r"\.{2,3}", line):
                    rev_up = line[m.end(0):]
                print(line)

            elif line.startswith("Fast forward"):
                on_merge = True
            elif on_merge:
                if line[0] == ' ':
                    if m := re.search(r" +?\| ", line):
                        fn = line[1: m.start(0)]
                
                        yield fn, conflict, rev_up


def update_remotes(path):
    remote_head = ""
    for line in fetch(path):
        line = line.decode('utf-8')
        if line.startswith(' '):
            line = line.strip().split(' ')[0]
            if m := re.search(r"\.{2,3}", line):
                 remote_head = line[m.end(0):]

    return remote_head
            


def info(path):
    cmd = ["show", "--no-patch"]
    return exec_command(cmd, path)


def fetch(path):
    cmd = ["fetch", "origin", "--quiet"]
    return exec_command(cmd, path)


def status(path):
    cmd = ["status", "--porcelain=v1"]
    return exec_command(cmd, path)


def diff(path, rev, cached=False):
    cmd = ["diff"]
    if cached:
        cmd.append("--cached")

    cmd.append(rev)
    return exec_command(cmd, path)


def update(path):
    cmd = ["pull"]
    return exec_command(cmd, path)


# -------------


def add(path):
    if path == "":
        print("git add empty parameter")
        return None

    cmd = ["add", path]
    return exec_command(cmd)


def delete(path):
    if path == "":
        print("git rm empty parameter")
        return None

    cmd = ["rm", path]
    return exec_command(cmd)


def move(src, dst):
    if src == "" or dst == "":
        print("git mv empty parameter")
        return None

    cmd = ["mv", src, dst]
    return exec_command(cmd)


def exec_command(cmd_args, cwd=None):
    cmd = ["git"]
    cmd.extend(cmd_args)
    silent = bool(cmd_args[0] in ("show",))
    try:
        if not silent:
            print("fetching" if cmd_args[0] in ("status", "diff", "update", "remote") else "applying",
                 cmd_args[0] + ": ...", end="")
        output = subprocess.check_output(cmd, cwd=cwd)
    except OSError as err:
        print("git", cmd_args[0], "error:", err)
    except ValueError as err:
        print("git", cmd_args[0], "error:", err)
    except Exception as err:
        print("git", cmd_args[0], "unexpected error", err)
    else:
        if not silent:
            print("\b" * 3 + "done")
        return output.splitlines()


def file_diff(fn, rev=None, cached=False):
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


def run_diff(from_vsn, is_internal, path, rev, cached):
    if from_vsn:
        remote_head = update_remotes(path)
        print("Current revision: ", get_revision(path))

    if from_vsn and is_internal:
        binary_ext = (".png", ".jpg", ".jpeg", ".gif", ".pyc")
        for fn in unversioned_files(path, binary_ext):
            try:
                with open(fn, "r", encoding="utf-8") as f:
                    text = f.read()
            except (IOError, OSError) as err:
                print("{0}: cannot open: {1}".format(fn, err))
            else:
                yield Fragment(fn, text), None, None

    yield from difference(from_vsn, is_internal, path, rev, cached)