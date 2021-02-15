
"""
util.monostyle_io
~~~~~~~~~~~~~~~~~

Input/Output utility for Monostyle.
"""

import sys
import os
import re
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


def ask_user(question):
    """Get user confirmation via console input."""
    pos = ("y", "yes")
    neg = ("n", "no")
    ip = input("".join(question) + " (y/n)?")
    while (True):
        if ip in ("h", "help"):
            print("confirm by entering:", "'" + "', '".join(pos) + "'")
            print("or chancel with:", "'" + "', '".join(neg) + "'")
            ip = input("input: ")
        else:
            return ip in pos


#------------------------
# Files & data


def path_to_rel(filename, base=None):
    """Make path relative."""
    rel = config.root_dir
    if base is not None:
        bases = {"root": rel, "rst": config.rst_dir, "po": config.po_dir, "img": config.img_dir}
        if base in bases:
            rel = rel + '/' + bases[base]

    if filename.startswith(rel):
        filename = filename[len(rel) + 1:]

    return filename


def path_to_abs(filename, base=None):
    """Make path absolute."""
    root = config.root_dir
    if not filename.startswith(root):
        bases = {"root": root, "rst": config.rst_dir, "po": config.po_dir, "img": config.img_dir}
        if base is not None and base in bases and not filename.startswith(bases[base] + '/'):
            filename = '/'.join((root, bases[base], filename))
        else:
            filename = '/'.join((root, filename))
    return filename


def replace_windows_path_sep(filename):
    """Replace backslash in Windows path."""
    return re.sub(r"\\", "/", filename)


def get_data_file(path):
    """Read JSON data file.

    path -- filename without extension and path through the tree hierarchy. Slash separated.
    """
    data_path = re.split(r"[\\/]", path)
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
            return get_branch(data, path, index + 1)
        if not silent:
            print("Cannot find data segment: {0} of {1}".format(path[index], '/'.join(path)))
    else:
        return data


def override_typecheck(obj, ref, op_name, key_name=None):
    """Check if an object matches the reference object's types.
    Sequence entries are not deep checked.
    Empty reference sequences/dicts are not checked.
    Sequence entries with mixed types must exactly match one of these types.
    No callables.
    """
    def print_error(obj, typs, op_name, key_name):
        print("{0} invalid type {1} expected {2}".format(op_name,
              type(obj).__name__, ", ".join(t.__name__ for t in typs)),
              "in " + key_name if key_name else "")

    if type(obj) == dict:
        ref_keys = ref.keys()
        invalid_keys = []
        for key in obj.keys():
            if key not in ref_keys:
                if len(ref_keys) != 0:
                    print("{0} invalid key {1}".format(op_name, key),
                          "in " + key_name if key_name else "")
                    invalid_keys.append(key)
                continue

            obj[key] = override_typecheck(obj[key], ref[key], op_name, key)

        for key in invalid_keys:
            del obj[key]
    elif hasattr(obj, "__iter__") and type(obj) != str:
        typs = list(set(type(entry) for entry in ref))
        new = []
        for entry in obj:
            if len(typs) != 0 and type(entry) not in typs:
                print_error(entry, typs, op_name, key_name)
                continue
            if len(typs) == 1:
                try:
                    entry = typs[0](entry)
                except (TypeError, ValueError):
                    print_error(entry, (typs[0],), op_name, key_name)
                    continue

            new.append(entry)

        try:
            obj = type(ref)(new)
        except (TypeError, ValueError):
            print_error(new, (type(ref),), op_name, key_name)
            obj = ref
    elif hasattr(obj, "__call__"):
        print_error(obj, (type(ref),), op_name, key_name)
        obj = ref
    else:
        try:
            obj = type(ref)(obj)
        except (TypeError, ValueError):
            print_error(obj, (type(ref),), op_name, key_name)
            obj = ref

    return obj


def get_override(file, toolname, varname, default):
    """Override configuration variables."""
    file = os.path.splitext(os.path.basename(file))[0]

    if ((seg := get_branch(config.config_override, (file, toolname, varname), silent=True))
            is not None):
        return override_typecheck(seg, default, "tool config override")

    return default


def rst_files(path=None):
    """Yields the filename of RST files."""
    if path is None:
        path = '/'.join((config.root_dir, config.rst_dir))

    return files_recursive(path, ext_pos=(".rst",))


def rst_texts(path=None):
    """Yields the filename and text of RST files."""
    if path is None:
        path = '/'.join((config.root_dir, config.rst_dir))

    return texts_recursive(path, ext_pos=(".rst",))


def po_files(path=None):
    """Yields the filename of PO files."""
    if path is None:
        path = '/'.join((config.root_dir, config.po_dir))

    return files_recursive(path, ext_pos=(".po",))


def po_texts(path=None):
    """Yields the filename and text of PO files."""
    if path is None:
        path = '/'.join((config.root_dir, config.po_dir))

    return texts_recursive(path, ext_pos=(".po",))


def img_files(path=None):
    """Yields the filename and extension of files in (by default) the image directory."""
    if path is None:
        path = '/'.join((config.root_dir, config.img_dir))

    return files_recursive(path, ext_pos=(), split_output=True)


def texts_recursive(path=None, ext_pos=()):
    """Yields the filename and text of files."""
    if path is None:
        path = config.root_dir

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

        filename = replace_windows_path_sep(filename)
        return filename, text

    except (IOError, OSError) as err:
        print("{0}: cannot read: {1}".format(filename, err))
        return filename, None


def files_recursive(path=None, ext_pos=(), split_output=False):
    """Yield files in the sub-/directories."""
    if path is None:
        path = config.root_dir
    path = replace_windows_path_sep(path)

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

            dirpath = replace_windows_path_sep(dirpath)
            for filename in filenames:
                name, ext = os.path.splitext(filename)
                if len(ext_pos) == 0 or ext.lower() in ext_pos:
                    if not split_output:
                        yield '/'.join((dirpath, filename))
                    else:
                        yield dirpath, name, ext
