
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
        "tools": ("directive", "heading-level", "indent", "leak"),
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

root_dir = ""
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
