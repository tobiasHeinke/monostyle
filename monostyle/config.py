
"""
config
~~~~~~

Project configuration.
"""

import os
import json

tool_selection = None
root_dir = None
rst_dir = None
po_dir = None
build_dir = None
img_dir = None
console_options = None
config_override = None
template_override = None


def setup_config(root):
    """Create user config file or override config."""
    global root_dir
    root_dir = root
    filename_default = os.path.normpath(os.path.join(os.path.dirname(__file__), "data", "config.json"))
    config_default, source_default = load_config(filename_default)
    for key, value in config_default.items():
        globals()[key] = value

    filename_user = os.path.normpath(os.path.join(root, "monostyle", "config.json"))
    if not os.path.isfile(filename_user):
        write_config_file(filename_user, source_default)
    else:
        config_user, _ = load_config(filename_user)
        if config_user is None:
            return False

        for key, value in config_user.items():
            if key in config_default.keys() and value is not None:
                globals()[key] = override_typecheck(value, globals()[key], "monostyle config")

    return True


def load_config(filename):
    """Load default/user config file."""
    def remove_comments(text):
        lines = []
        for line in text.splitlines():
            if not line.lstrip().startswith("//"):
                lines.append(line)
            else:
                lines.append("")
        return '\n'.join(lines)

    try:
        text = read_config_file(filename)
        if text is not None:
            return json.loads(remove_comments(text)), text

    except json.JSONDecodeError as err:
        print("{0}: cannot decode user config: {1}".format(filename, err))

    return None, None


def read_config_file(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as config_file:
            text = config_file.read()
            return text

    except IOError:
        print("config.json not found:", filename)


def write_config_file(filename, text):
    try:
        with open(filename, 'w', encoding='utf-8') as config_file:
            config_file.write(text)

    except (IOError, OSError) as err:
        print("{0}: cannot write: {1}".format(filename, err))


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
