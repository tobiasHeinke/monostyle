
"""
config
~~~~~~

Project configuration.
"""

import os
import json
from monostyle.util.monostylestd import override_typecheck


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
