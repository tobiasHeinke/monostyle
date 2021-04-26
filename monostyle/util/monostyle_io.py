
"""
util.monostyle_io
~~~~~~~~~~~~~~~~~

Input/Output utility for Monostyle.
"""

import sys
import os
import json

import monostyle.config as config


#------------------------
# Console


def print_over(*text, is_temp=False, ellipsis=None):
    """Print line overriding a previous temporary line."""
    text = " ".join(text)
    if ellipsis:
        text += ": " + ellipsis
        is_temp = True

    prev_len = getattr(print_over, "prev_len", 0)
    cur_len = len(text.splitlines()[-1]) if is_temp else 0
    if not getattr(print_over, "was_ellipsis", False):
        if cur_len < prev_len:
            sys.__stdout__.write("\033[2K\r")
        sys.__stdout__.write(text + ("" if ellipsis is not None else '\r' if is_temp else '\n'))
        sys.__stdout__.flush()
    else:
        sys.__stdout__.write('\b' * prev_len + "{0: <{1}}\n".format(text, prev_len))

    if not ellipsis:
        print_over.prev_len = cur_len
    else:
        print_over.prev_len = len(ellipsis)
    print_over.was_ellipsis = bool(ellipsis)


def print_title(title, to_upper=False, underline='='):
    """Print a title in the command line."""
    if isinstance(title, str):
        title = list(title.splitlines())
    else:
        title = list(l.strip('\n') for l in title)

    if to_upper:
        title = list(l.upper() for l in title)
    if not title[-1].endswith(':'):
        title[-1] += ':'

    print_over('')
    print_over('\n'.join(title))
    if underline is not None:
        print_over(underline * max(len(l) for l in title))


def ask_user(*question):
    """Get user confirmation via console input."""
    keys = {"pos": "yes", "neg": "nope", "help": "help"}
    retries = 0
    while True:
        ip = input("".join((*question, " ", keys["pos"][0], "/", keys["neg"][0], "?"))).lower()
        if not ip or keys["help"].startswith(ip) or ip in ("?", "¿"):
            print("confirm by entering:",
                  "'" + "', '".join(keys["pos"][:n] for n in range(1, len(keys["pos"]) + 1)) + "'")
            print("or chancel with:",
                  "'" + "', '".join(keys["neg"][:n] for n in range(1, len(keys["neg"]) + 1)) + "'")
        else:
            if keys["pos"].startswith(ip):
                return True
            if keys["neg"].startswith(ip):
                return False
            if retries > 3:
                break
            print("Invalid input, please try again! (or type '" + keys["help"] + "')")
            retries += 1

    return False


#------------------------
# Files & data


def path_to_rel(path, base=None):
    """Make path relative."""
    path = norm_path_sep(os.path.normpath(path))
    rel = path_to_abs("", base)
    if path.startswith(rel):
        path = path[len(rel) + 1:]

    return path


def path_to_abs(path, base=None):
    """Make path absolute."""
    path = norm_path_sep(os.path.normpath(path))
    root = norm_path_sep(os.getcwd())
    if not path.startswith(root):
        base = (norm_path_sep(os.path.normpath(config.project_dirs[base])).lstrip(".")
                if base in config.project_dirs else None)
        if base is not None and not path.startswith(base + '/'):
            path = '/'.join((root, base, path)).strip("/")
        else:
            path = '/'.join((root, path)).strip("/")
    return path


def norm_path_sep(path):
    """Replace backslash in Windows path and multiple slashes to one."""
    return '/'.join(s for s in path.replace("\\", "/").split("/")
                    if len(s) != 0 and (len(s) != 1 or s != "."))


def get_data_file(path):
    """Read JSON data file.

    path -- filename without extension and path through the tree hierarchy. Slash separated.
    """
    data_path = path.replace("\\", "/").split("/")
    data_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "data"))
    filename = os.path.join(data_dir, data_path[0] + ".json")
    try:
        with open(filename, "r", encoding="utf-8") as json_file:
            data = json.load(json_file)

    except (IOError, OSError) as err:
        print("{0}: cannot read data file: {1}".format(data_path[0], err))
        return None

    except json.JSONDecodeError as err:
        print("{0}: cannot decode data file: {1}".format(data_path[0], err))
        return None

    return get_branch(data, data_path, 1)


def get_branch(data, path, index=0, silent=False):
    """Walk through data object.

    path -- path through the tree hierarchy.
    """
    if index < len(path):
        if (data := data.get(path[index])) is not None:
            return get_branch(data, path, index + 1, silent)
        if not silent:
            print("Cannot find data segment: {0} of {1}".format(path[index], '/'.join(path)))
    else:
        return data


def get_override(file, toolname, varname, default, limits=None):
    """Override configuration variables."""
    file = os.path.splitext(os.path.basename(file))[0]

    if ((seg := get_branch(config.config_override, (file, toolname, varname), silent=True))
            is not None):
        value = config.override_typecheck(seg, default, "tool config override")
        if limits:
            if limits[0] is not None and value < limits[0]:
                value = limits[0]
                print("{0}.{1}: the '{2}' configuration option has a minimum of {3}."
                      .format(file, toolname, varname, limits[0]))
            elif limits[1] is not None and value > limits[1]:
                value = limits[1]
                print("{0}.{1}: the '{2}' configuration option has a maximum of {3}."
                      .format(file, toolname, varname, limits[1]))
        return ((varname, value),)

    return ((varname, default),)


def doc_files(path=None):
    """Yields the filename of RST files."""
    if path is None:
        path = path_to_abs("", "doc")

    return files_recursive(path, ext_pos=(".rst",))


def doc_texts(path=None):
    """Yields the filename and text of RST files."""
    if path is None:
        path = path_to_abs("", "doc")

    return texts_recursive(path, ext_pos=(".rst",))


def loc_files(path=None):
    """Yields the filename of PO files."""
    if path is None:
        path = path_to_abs("", "loc")

    return files_recursive(path, ext_pos=(".po",))


def loc_texts(path=None):
    """Yields the filename and text of PO files."""
    if path is None:
        path = path_to_abs("", "loc")

    return texts_recursive(path, ext_pos=(".po",))


def img_files(path=None):
    """Yields the filename and extension of files in (by default) the image directory."""
    if path is None:
        path = path_to_abs("", "img")

    return files_recursive(path, ext_pos=(), split_output=True)


def texts_recursive(path=None, ext_pos=()):
    """Yields the filename and text of files."""
    if path is None:
        path = path_to_abs("", "root")

    ext_names = '/'.join(ext[1:] for ext in ext_pos) # strip dot
    if not os.path.isdir(path):
        ext = os.path.splitext(path)[1]
        if len(ext_pos) != 0 and ext.lower() not in ext_pos:
            return None
        print_over("read {}-file".format(ext_names), is_temp=True)
        yield single_text(path)
    else:
        file_count_total = sum(1 for _ in files_recursive(path, ext_pos))
        counter = 0
        for filename in files_recursive(path, ext_pos):
            print_over("read {}-files: [{:4.0%}]".format(ext_names, counter / file_count_total),
                       is_temp=True)
            counter += 1

            yield single_text(filename)


def single_text(filename):
    """Returns the filename and text of a single file."""
    try:
        with open(filename, "r", encoding="utf-8") as f:
            text = f.read()

        filename = norm_path_sep(filename)
        return filename, text

    except (IOError, OSError) as err:
        print("{0}: cannot read: {1}".format(filename, err))
        return filename, None


def files_recursive(path=None, ext_pos=(), split_output=False):
    """Yield files in the sub-/directories."""
    if path is None:
        path = path_to_abs("", "root")
    else:
        path = norm_path_sep(path)

    if isinstance(ext_pos, str):
        ext_pos = (ext_pos,)

    if not os.path.isdir(path):
        name, ext = os.path.splitext(path)
        if len(ext_pos) != 0 and ext.lower() not in ext_pos:
            return None
        if not split_output:
            yield path
        else:
            dirpath, name = os.path.split(name)
            yield dirpath, name, ext

        yield single_text(path)
    else:
        for dirpath, _, filenames in os.walk(path):
            if dirpath.startswith("."):
                continue

            dirpath = norm_path_sep(dirpath)
            for filename in filenames:
                name, ext = os.path.splitext(filename)
                if len(ext_pos) == 0 or ext.lower() in ext_pos:
                    if not split_output:
                        yield '/'.join((dirpath, filename))
                    else:
                        yield dirpath, name, ext
