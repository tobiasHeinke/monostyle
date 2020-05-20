
"""
config
~~~~~~

Project configuration.
"""

tool_selection = {
    "listsearch": {
        "tools": ("simplify", "blender/UI", "blender/Editors", "blender/Modes", "avoid/*"),
        "ext": ".rst"
    },
    "markup": {
        "tools": ("directive", "heading-level", "indent", "kbd", "leak"),
        "ext": ".rst"
    },
    "code_style": {
        "tools": ("heading-char-count", "flavor", "line-style", "long-line", "newline", "style-add"),
        "ext": ".rst"
    },
    "natural": {
        "tools": ("article", "grammar", "heading-cap", "repeated"),
        "ext": ".rst"
    },
    "spelling": {
        "tools": ("search"),
        "ext": ".rst"
    },
    "punctuation": {
        "tools": ("number", "pairs", "mark", "whitespace"),
        "ext": ".rst"
    },
    "char": {
        "tools": ("char-region"),
        "ext": ".rst"
    },
    "monitor": {
        "tools": ("check"),
        "ext": ""
    }
}

# Project Directories
# -------------------

rst_dir = "manual"
po_dir = "locale"
build_dir = "build"
img_dir = '/'.join((rst_dir, "images"))


# Console Output
# --------------

console_options = {

    "file_title": True,
    "file_title_underline": '-',
    "show_summary": True,
    "summary_overline": "_",

    "format_str": "{fn}{loc} {severity} {out} {msg} {fix}{line}",
    "show_filename":True,
    "show_end": False,

    # options: 'long', 'char', 'icon',
    "severity_display": "long",

    "out_sep_start": "´",
    "out_sep_end": "´",
    "out_max_len": 100,
    "out_ellipse": "…",

    "show_line":True,
    "line_max_len": 200,
    "line_indent": ">>>",
    "line_ellipse": "…",

    "autofix_mark": "/autofixed/"
}

# Tool Config Override
# --------------------

# module name : {function name : {variable name: variable value}}
config_override = {
}

# Message Template Override
# -------------------------

# template name : string
template_override = {
}
# --- END ---


import os

def setup_config(root):
    """Create user config file or overide config."""
    config_fn = os.path.normpath(os.path.join(root, "monostyle", "config.py"))
    if not os.path.isfile(config_fn):
        text = read_config_file(__file__)
        text = text[:text.find("# --- END ---")]
        write_config_file(config_fn, text)
    else:
        text = read_config_file(config_fn)
        if text is None:
            return False

        try:
            code = compile(text, config_fn, 'exec')
        except SyntaxError:
            print("Syntax error in config.py")
            return False

        namespace = {"__file__": config_fn}
        exec(code, namespace)

        config_options = ("tool_selection", "rst_dir", "po_dir", "build_dir", "img_dir",
                          "console_options", "config_override", "template_override")
        for key, val in namespace.items():
            if key in config_options and val is not None:
                globals()[key] = val

    return True


def read_config_file(config_fn):
    try:
        with open(config_fn, 'r', encoding='utf-8') as config_file:
            text = config_file.read()

        return text

    except IOError:
        print("config.py not found:", config_fn)


def write_config_file(config_fn, text):
    try:
        with open(config_fn, 'w', encoding='utf-8') as config_file:
            config_file.write(text)

    except (IOError, OSError) as err:
        print("{0}: cannot write: {1}".format(config_fn, err))
