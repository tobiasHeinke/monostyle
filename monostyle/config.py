
"""
config
~~~~~~

Project configuration.
"""

import os
import json

tool_selection = None
project_dirs = None
console_options = None
config_override = None
template_override = None


def init(root, cwd):
    """Create user config file or override config."""
    config_default, source_default = read_file(root, True)
    for key, value in config_default.items():
        globals()[key] = value
    globals()["project_dirs"]["cwd"] = cwd

    try:
        config_user, _ = read_file(root, False)
    except IOError:
        write_file(root, source_default)
    except ValueError as err:
        print(err)
        return False
    else:
        for key, value in config_user.items():
            if key in config_default.keys() and value is not None:
                globals()[key] = override_typecheck(value, globals()[key], "monostyle config")
        globals()["project_dirs"]["cwd"] = cwd

    return True


def read_file(root, from_default):
    """Load default/user config file."""
    def remove_comments(text):
        lines = []
        for line in text.splitlines():
            if not line.lstrip().startswith("//"):
                lines.append(line)
            else:
                lines.append("")
        return '\n'.join(lines)

    if from_default:
        filename = os.path.normpath(os.path.join(os.path.dirname(__file__), "data", "config.json"))
    else:
        filename = os.path.normpath(os.path.join(root, "monostyle", "config.json"))

    with open(filename, 'r', encoding='utf-8') as config_file:
        text = config_file.read()

    text = remove_comments(text)
    try:
        return json.loads(text), text
    except json.JSONDecodeError as err:
        raise ValueError("{0}: cannot decode user config: {1}".format(filename, err)) from err


def write_file(root, text):
    """Write user config file."""
    filename = os.path.normpath(os.path.join(root, "monostyle", "config.json"))

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
    def remove_types(obj):
        """Remove types by recreating the object to support immutables."""
        if not hasattr(obj, "__iter__") or type(obj) == str:
            return obj

        new = list()
        if type(obj) == dict:
            for key, value in obj.items():
                if type(value) is not type:
                    new.append((key, remove_types(value))) # todo double
        else:
            for entry in obj:
                if type(entry) is not type:
                    new.append(remove_types(entry))

        return type(obj)(new)

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
    elif hasattr(obj, "__call__"):
        print_error(obj, (type(ref),), op_name, key_name)
        obj = remove_types(ref)
    elif hasattr(obj, "__iter__") and type(obj) != str:
        typs = list(set(type(entry) if type(entry) is not type else entry for entry in ref))
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
            obj = remove_types(ref)
    else:
        try:
            obj = type(ref)(obj)
        except (TypeError, ValueError):
            print_error(obj, (type(ref),), op_name, key_name)
            obj = remove_types(ref)

    return obj
