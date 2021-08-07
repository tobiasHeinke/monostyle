
"""
git_inter
~~~~~~~~~

Interface to Git.
"""

import os
import re
import subprocess

from monostyle.util.monostyle_io import print_over, single_text
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
            filename = norm_path_sep(line[3:].strip())
            if filename.startswith('.') or os.path.isdir(filename):
                continue
            if binary_ext is not None and os.path.splitext(filename)[1] in binary_ext:
                continue

            yield path + "/" + filename


def difference(from_vsn, is_internal, path, rev, cached):
    if not rev:
        rev = "HEAD"
        if not is_internal:
            rev += "..remotes/origin/HEAD"

    loc_re = re.compile(r"@@ \-\d+?(?:,\d+?)? \+(\d+?)(?:,\d+?)? @@")
    code = None
    context = []
    skip = False
    body = False
    for line in (diff if from_vsn else file_diff)(path, rev, cached):
        try:
            line = line.decode("utf-8")
        except UnicodeError:
            # binary: skip
            continue

        if line.startswith("+++"):
            filename = norm_path_sep(line[len("+++ b/"):])
            skip = False
            body = False

        elif line.startswith("Binary files"):
            # skip whole file
            skip = True

        if skip:
            continue

        if line.startswith("@@"):
            if code and len(code.content) != len(context):
                yield code, context

            code = Fragment(filename, [],
                            start_lincol=(int(re.match(loc_re, line).group(1)) - 1, 0))
            context = []
            body = True

        elif body:
            if line.startswith(' '):
                code.extend(line[1:] + '\n')
                context.append(code.end_lincol[0])
            elif line.startswith('+'):
                code.extend(line[1:] + '\n')

            elif line.startswith('\\'):
                # backslash + space
                message = line[2:]
                if message == "No newline at end of file":
                    if code and code.content: # remove previously added newline
                        code = code.slice(end=code.end_pos - 1, after_inner=True)
                else:
                    print("{0}:{1}: unexpected version control message: {2}"
                          .format(code.filename, code.end_lincol[0], message))

    if code and len(code.content) != len(context):
        yield code, context


def update_files(path, rev=None):
    rev_up = ""
    on_merge = False
    for line in update(path):
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
                        # filename, conflict
                        yield line[1: m.start(0)], False, rev_up


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
    silent = bool(cmd_args[0] == "show")
    try:
        if not silent:
            print_over("fetching" if cmd_args[0] in {"status", "diff", "update", "remote"}
                       else "applying", cmd_args[0], ellipsis="...")
        output = subprocess.check_output(cmd, cwd=cwd)
    except (OSError, ValueError) as err:
        print("git", cmd_args[0], "error:", err)
    except subprocess.CalledProcessError as err:
        print("git", cmd_args[0], "error", err)
    else:
        if not silent:
            print_over("done")
        return output.splitlines()


def file_diff(filename, rev=None, cached=False):
    if not (filename.endswith(".diff") or filename.endswith(".patch")):
        print("diff wrong file format:", filename)
        return None

    try:
        with open(filename, "rb") as f:
            text = f.read()

        return text.splitlines()

    except (IOError, OSError) as err:
        print("{0}: cannot open: {1}".format(filename, err))


def norm_path_sep(filename):
    return re.sub(r"\\", "/", filename)


def run_diff(from_vsn, is_internal, path, rev, cached, unversioned=False):
    if from_vsn:
        remote_head = update_remotes(path)
        print("Current revision:", get_revision(path))

    if from_vsn and is_internal and unversioned:
        binary_ext = {".png", ".jpg", ".jpeg", ".gif", ".pyc"}
        for filename in unversioned_files(path, binary_ext):
            filename, text = single_text(filename)
            if text:
                yield Fragment(filename, text), None, None

    yield from difference(from_vsn, is_internal, path, rev, cached)
