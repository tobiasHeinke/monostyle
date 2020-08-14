
"""
config
~~~~~~

Project configuration.
"""

import os
import json
from monostyle.util.monostylestd import override_typecheck


def setup_config(root):
    """Create user config file or overide config."""
    global root_dir
    root_dir = root
    fn_default = os.path.normpath(os.path.join(os.path.dirname(__file__), "data", "config.json"))
    config_default, source_default = load_config(fn_default)
    for key, val in config_default.items():
        globals()[key] = val

    fn_user = os.path.normpath(os.path.join(root, "monostyle", "config.json"))
    if not os.path.isfile(fn_user):
        write_config_file(fn_user, source_default)
    else:
        config_user, _ = load_config(fn_user)
        if config_user is None:
            return False

        for key, val in config_user.items():
            if key in config_default.keys() and val is not None:
                globals()[key] = override_typecheck(val, globals()[key], "monostyle config")

    return True


def load_config(fn):
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
        text = read_config_file(fn)
        if text is not None:
            return json.loads(remove_comments(text)), text

    except json.JSONDecodeError as err:
        print("{0}: cannot decode user config: {1}".format(fn, err))

    return None, None


def read_config_file(fn):
    try:
        with open(fn, 'r', encoding='utf-8') as config_file:
            text = config_file.read()
            return text

    except IOError:
        print("config.json not found:", fn)


def write_config_file(fn, text):
    try:
        with open(fn, 'w', encoding='utf-8') as config_file:
            config_file.write(text)

    except (IOError, OSError) as err:
        print("{0}: cannot write: {1}".format(fn, err))
