
"""
util.monostylestd
~~~~~~~~~~~~~~~~~

Common utility for Monostyle.
"""

import os
from math import ceil
import re
import json

import monostyle.config as config

ROOT_DIR = None
RST_DIR = config.rst_dir
PO_DIR = config.po_dir
IMG_DIR = config.img_dir


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

    print('', *title, sep='\n')
    if underline is not None:
        print(underline * max(len(l) for l in title))


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
# Context


def getline_lineno(fg, lineno):
    """Extracts single line selected by its line number."""
    return fg.slice((lineno, 0), (lineno+1, 0), True)


def getline_newline(fg, loc, n):
    """Extracts line including lines around it.

    loc -- position within the line.
    n -- number of lines to include around the line (odds below).
    """
    start = (loc[0] - ceil(n / 2), 0)
    end = (loc[0] + (n // 2) + 1, 0)
    return fg.slice(start, end, True)


def getline_punc(fg, pos, match_len, min_chars, margin):
    """Extracts line limited by punctuation.

    pos -- position within the line.
    match_len -- length of the output.
    min_chars -- minimal amount of chars to extract on both sides.
    margin -- length of the outer margin within to search for punctuation marks.
    """
    start = pos - min_chars - margin
    end = pos + match_len + min_chars + margin
    buf = fg.slice(start, end, True)

    margin_start, _, margin_end = buf.slice(start + margin, end - margin)

    if margin_start and len(margin_start) != 0:
        margin_start_str = str(margin_start)
        start_m = None
        for start_m in re.finditer(r"[.?!:,;]", margin_start_str):
            pass
        if start_m:
            start = margin_start.loc_to_abs(start_m.end(0))

    if margin_end and len(margin_end) != 0:
        if end_m := re.search(r"[.?!:,;]", str(margin_end)):
            end = margin_end.loc_to_abs(end_m.end(0))

    return buf.slice(start, end, True)


#------------------------
# IO & data


def path_to_rel(fn, base=None):
    """Make path relative."""
    rel = ROOT_DIR
    if base is not None:
        bases = {"root": rel, "rst": RST_DIR, "po": PO_DIR, "img": IMG_DIR}
        if base in bases:
            rel = rel + '/' + bases[base]

    if fn.startswith(rel):
        fn = fn[len(rel) + 1:]

    return fn


def path_to_abs(fn, base=None):
    """Make path absolute."""
    root = ROOT_DIR
    if not fn.startswith(root):
        bases = {"root": root, "rst": RST_DIR, "po": PO_DIR, "img": IMG_DIR}
        if base is not None and base in bases and not fn.startswith(bases[base] + '/'):
            fn = '/'.join((root, bases[base], fn))
        else:
            fn = '/'.join((root, fn))
    return fn


def replace_windows_path_sep(fn):
    """Replace backslash in Windows path."""
    return re.sub(r"\\", "/", fn)


def get_data_file(path):
    """Read JSON data file.

    path -- filename without extension and path through the tree hierarchy. Slash separated.
    """
    data_path = re.split(r"[\\/]", path)
    data_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "data"))
    fn = os.path.join(data_dir, data_path[0] + ".json")
    try:
        with open(fn, "r", encoding="utf-8") as json_file:
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

    path --  path through the tree hierarchy.
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
        print("{0} unvalid type {1} expected {2}".format(op_name,
              type(obj).__name__, ", ".join(t.__name__ for t in typs)),
              "in " + key_name if key_name else "")

    if type(obj) == dict:
        ref_keys = ref.keys()
        invalid_keys = []
        for key in obj.keys():
            if key not in ref_keys:
                if len(ref_keys) != 0:
                    print("{0} unvalid key {1}".format(op_name, key),
                          "in " + key_name if key_name else "")
                    invalid_keys.append(key)
                continue

            obj[key] = override_typecheck(obj[key], ref[key], op_name, key)

        for key in invalid_keys:
            del obj[key]
    elif hasattr(obj, "__iter__") and type(obj) != str:
        typs = list(set(type(ent) for ent in ref))
        new = []
        for ent in obj:
            if len(typs) != 0 and type(ent) not in typs:
                print_error(ent, typs, op_name, key_name)
                continue
            if len(typs) == 1:
                try:
                    ent = typs[0](ent)
                except (TypeError, ValueError):
                    print_error(ent, (typs[0],), op_name, key_name)
                    continue

            new.append(ent)

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
        path = '/'.join((ROOT_DIR, RST_DIR))

    return files_recursive(path, ext_pos=(".rst",))


def rst_texts(path=None):
    """Yields the filename and text of RST files."""
    if path is None:
        path = '/'.join((ROOT_DIR, RST_DIR))

    return texts_recursive(path, ext_pos=(".rst",))


def po_files(path=None):
    """Yields the filename of PO files."""
    if path is None:
        path = '/'.join((ROOT_DIR, PO_DIR))

    return files_recursive(path, ext_pos=(".po",))


def po_texts(path=None):
    """Yields the filename and text of PO files."""
    if path is None:
        path = '/'.join((ROOT_DIR, PO_DIR))

    return texts_recursive(path, ext_pos=(".po",))


def img_files(path=None):
    """Yields the filename and extension of files in (by default) the image directory."""
    if path is None:
        path = '/'.join((ROOT_DIR, IMG_DIR))

    return files_recursive(path, ext_pos=(), split_output=True)


def texts_recursive(path=None, ext_pos=()):
    """Yields the filename and text of files."""
    if path is None:
        path = ROOT_DIR

    ext_names = '/'.join(ext[1:] for ext in ext_pos) # strip dot
    if not os.path.isdir(path):
        ext = os.path.splitext(path)[1]
        if len(ext_pos) != 0 and ext.lower() not in ext_pos:
            return None
        print("\rread {}-file".format(ext_names), end='', flush=True)
        yield single_text(path)
    else:
        file_count_total = sum(map(lambda _: 1, files_recursive(path, ext_pos)))
        counter = 0
        for fn in files_recursive(path, ext_pos):
            print("\rread {}-files: [{:4.0%}]".format(ext_names, counter / file_count_total),
                  end='', flush=True)
            counter += 1

            yield single_text(fn)


def single_text(fn):
    """Returns the filename and text of a single file."""
    try:
        with open(fn, "r", encoding="utf-8") as f:
            text = f.read()

        fn = replace_windows_path_sep(fn)
        return fn, text

    except (IOError, OSError) as err:
        print("{0}: cannot read: {1}".format(fn, err))
        return fn, None


def files_recursive(path=None, ext_pos=(), split_output=False):
    """Yield files in the sub-/directories."""
    if path is None:
        path = ROOT_DIR
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
        for dirpath, dirnames, filenames in os.walk(path):
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
