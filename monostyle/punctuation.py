
"""
punctuation
~~~~~~~~~~~

Punctuation style checks and number formatting.
"""

import re

import monostyle.util.monostylestd as monostylestd
from monostyle.util.report import Report, getline_punc
from monostyle.util.fragment import Fragment
import monostyle.rst_parser.walker as rst_walker
from monostyle.util.pos import PartofSpeech
from monostyle.util.char_catalog import CharCatalog

POS = PartofSpeech()
CharCatalog = CharCatalog()


def number_pre(_):
    re_lib = dict()
    # FP: code, literal, Years
    start = r"(?:(?<=[^\d,.])|\A)"
    pattern_str = start + r"[\d,]*\d{4}"
    pattern = re.compile(pattern_str)
    message = Report.missing(what="separator", where="between four digits")
    re_lib["digitsep"] = (pattern, message)

    pattern_str = start + r"\d,\d{1,2}\b"
    pattern = re.compile(pattern_str)
    message = Report.existing(what="separator", where="between less than four digits")
    re_lib["digitsepless"] = (pattern, message)

    pattern_str = start + r"0,\d"
    pattern = re.compile(pattern_str)
    message = Report.existing(what="separator", where="after zero")
    re_lib["digitsepzero"] = (pattern, message)

    pattern_str = r"\d \d"
    pattern = re.compile(pattern_str)
    message = Report.existing(what="space", where="between digits")
    re_lib["digitspace"] = (pattern, message)

    written_out = r"\b" + r"\b|\b".join(POS.data["determiner"]["numeral"]["cardinal"])
    written_out += r"\b|" + r"\b|\b".join(POS.data["determiner"]["numeral"]["ordinal"])
    written_out += r"\b|" + r"\b|\b".join(("half", "halves", "thirds?"))
    pattern_str = r"(?:" + written_out + r") (?:" + written_out + r")"
    pattern = re.compile(pattern_str)
    message = Report.missing(what="hyphen", where="between written-out numbers")
    re_lib["writtenoutspace"] = (pattern, message)

    # FP: math, code
    pattern_str = r"(?:\w |^)([0-9]|1[0-2])(?: \w|$)"
    pattern = re.compile(pattern_str)
    message = Report.existing(what="low digit", where="in continuous text")
    re_lib["lowdigit"] = (pattern, message)

    pattern_str = start + r"\.\d"
    pattern = re.compile(pattern_str)
    message = Report.missing(what="zero", where="in front of a decimal point")
    re_lib["nozero"] = (pattern, message)

    pattern_str = start + r"0[1-9]"
    pattern = re.compile(pattern_str)
    message = Report.existing(what="zero", where="at number start")
    re_lib["zeronodot"] = (pattern, message)

    pattern_str = start + r"\d\.\d*0{2,}(?=\D|\Z)"
    pattern = re.compile(pattern_str)
    message = Report.existing(what="zeros", where="at number end")
    re_lib["zerotrail"] = (pattern, message)


    pattern_str = r"\d ?x( ?\d)?"
    pattern = re.compile(pattern_str)
    message = Report.option(what="x letter", with_what="times or × sign")
    re_lib["times"] = (pattern, message)

    pattern_str = r"\d\.\.+\d"
    pattern = re.compile(pattern_str)
    message = Report.option(what="range separator", with_what="to or dash")
    re_lib["range"] = (pattern, message)

    pattern_str = r"\D(?:0|100)%"
    pattern = re.compile(pattern_str)
    message = Report.option(what="percentage limits", with_what="written out no or fully")
    re_lib["percentlimit"] = (pattern, message)

    #-----------------

    pattern_str = r"\b[0-9]d\b"
    pattern = re.compile(pattern_str)
    message = Report.misformatted(what="lowercase dimension letter")
    re_lib["dimension"] = (pattern, message)

    pattern_str = r"\d [%‰‱]"
    pattern = re.compile(pattern_str)
    message = Report.existing(what="space", where="before percentage sign")
    re_lib["percent"] = (pattern, message)

    pattern_str = r"\d °(?! ?C\b)"
    pattern = re.compile(pattern_str)
    message = Report.existing(what="space", where="before degree sign")
    re_lib["degree"] = (pattern, message)

    pattern_str = r"\d° ?C\b|° C\b"
    pattern = re.compile(pattern_str)
    message = Report.substitution(what="Celsius", with_what="°C")
    re_lib["celsius"] = (pattern, message)

    units = (
        'D', 'th', 'nd', 'st', 'rd', # math
        'px', 'p', 'bit', r'ki?', r'Mi?B', r'Gi?B', r'Ti?B' # digital
    )
    pattern_str = r"\d(?!\W|\d|" + r'\b|'.join(units) + r"\b|\Z)"
    pattern = re.compile(pattern_str)
    message = Report.missing(what="space", where="before physics unit")
    re_lib["nospaceunit"] = (pattern, message)

    args = dict()
    args["re_lib"] = re_lib

    return args


def number(document, reports, re_lib):
    """Check for numbers and units formatting."""
    toolname = "number"

    instr_pos = {
        "field": {"*": ["body"]},
        "*": {"*": ["head", "body"]}
    }
    instr_neg = {
        "dir": {
            "figure": ["head"],
            "code-block": "*", "default": "*", "youtube": "*", "vimeo": "*"
        },
        "substdef": {"image": ["head"], "unicode": "*", "replace": "*"},
        "doctest": "*", "comment": "*",
        "role": {"kbd": "*"},
        "literal": "*", "standalone": "*", "footref": "*", "citref": "*"
    }

    for part in rst_walker.iter_nodeparts_instr(document.body, instr_pos, instr_neg):
        part_str = str(part.code)
        for key, value in re_lib.items():
            pattern = value[0]
            for m in re.finditer(pattern, part_str):
                if (key == "lowdigit" and
                        (rst_walker.is_of(part, "role", {"math", "sub", "sup"}) or
                         rst_walker.is_of(part, "dir", "math"))):
                    continue

                output = part.code.slice_match_obj(m, 0, True)
                line = getline_punc(document.body.code, output.start_pos,
                                    output.span_len(True), 50, 0)
                reports.append(Report('W', toolname, output, value[1], line))

    return reports


def pairs_pre(_):
    toolname = "pairs"

    args = dict()
    re_lib = dict()

    # FP/FN: s' closing
    # FP: cut heading line
    pattern_str = r"[\(\[\{\)\]\}\]\"]|(?<!\w)'|(?<![sS])'(?!\w)"
    pattern = re.compile(pattern_str)
    re_lib["pairchar"] = pattern

    pattern_str = r"(?<!\\)([`*])\1*"
    pattern = re.compile(pattern_str)
    re_lib["markupchar"] = pattern

    args["re_lib"] = re_lib

    # Max number of lines between the open and close mark.
    line_span = monostylestd.get_override(__file__, toolname, "max_line_span", 2)
    args["config"] = {"max_line_span": line_span}

    return args


def pairs(document, reports, re_lib, config):
    """Check if pairs of inline markup, brackets, quote marks are closed."""
    toolname = "pairs"

    instr_pos = {
        "sect": {"*": ["name"]},
        "field": {"*": ["name", "body"]},
        "*": {"*": ["head", "body"]}
    }
    instr_neg = {
        "dir": {"code-block": "*", "default": "*", "math": "*", "youtube": "*", "vimeo": "*"},
        "substdef": {"unicode": "*", "replace": "*"},
        "doctest": "*", "target": "*", "comment": "*",
        "role": {"kbd": "*", "menuselection": "*", "class": "*", "mod": "*", "math": "*"},
        "literal": "*", "standalone": "*"
    }

    max_line_span = config.get("max_line_span")
    stack = []
    pair_re = re_lib["pairchar"]
    markup_re = re_lib["markupchar"]
    pairs_map = {')': '(', ']': '[', '}': '{'}

    for part in rst_walker.iter_nodeparts_instr(document.body, instr_pos, instr_neg):
        for line in part.code.splitlines():
            line_str = str(line)
            for pair_m in re.finditer(pair_re, line_str):
                pair_char = pair_m.group(0)
                for index, entry in enumerate(reversed(stack)):
                    if (entry[0] == pair_char or
                            (pair_char in pairs_map and entry[0] == pairs_map[pair_char])):

                        if (max_line_span is not None and
                                line.start_lincol[0] - entry[1][0] > max_line_span):
                            lincol_abs = line.loc_to_abs((0, pair_m.start(0)))
                            message = "long span"
                            message += " - " + str(lincol_abs[0] + 1) + ","
                            message += str(lincol_abs[1] + 1)
                            output = Fragment(document.code.filename, entry[0], -1,
                                              start_lincol=entry[1])
                            reports.append(Report('W', toolname, output, message))

                        # invert index
                        index = len(stack) - 1 - index
                        stack.pop(index)
                        break

                else:
                    stack.append((pair_char, line.loc_to_abs((0, pair_m.start(0)))))

            for markup_m in re.finditer(markup_re, line_str):
                output = line.slice_match_obj(markup_m, 0, True)
                reports.append(Report('E', toolname, output, "leaked markup char"))

    if len(stack) != 0:
        message = "unclosed pairs"
        for entry in stack:
            output = Fragment(document.code.filename, entry[0], -1, start_lincol=entry[1])
            reports.append(Report('W', toolname, output, message))

    if max_line_span is not None:
        for node in rst_walker.iter_node(document.body,
                                         ("literal", "strong", "emphasis", "int-target",
                                          "role", "hyperlink")):

            if not node.body_start or not node.body_end:
                # single word int-target or hyperlink
                continue

            if (node.body_start.code.end_lincol[0] - node.body_end.code.start_lincol[0] >
                    max_line_span):
                message = "long span"
                message += " - " + str(node.body_start.code.end_lincol[0] + 1)
                message += "," + str(node.body_end.code.start_lincol[1] + 1)
                reports.append(Report('W', toolname, node.body_start.code, message))

            if node.body_start.code.end_pos == node.body_end.code.start_pos:
                message = "zero span"
                reports.append(Report('W', toolname, node.code, message))

    return reports


def mark_pre(_):
    re_lib = dict()
    punc = CharCatalog.data["terminal"]["final"] + CharCatalog.data["secondary"]["final"]
    punc_sent = CharCatalog.data["terminal"]["final"] + ':'
    pare_open = CharCatalog.data["bracket"]["left"]["normal"]
    pare_close = CharCatalog.data["bracket"]["right"]["normal"]

    # limitation: not nested parenthesis
    # FN: inline markup
    pattern_str = (
        r"[", punc_sent, r"]\s*?",
        r"[", pare_open, r"][^", pare_close, r"]+?",
        r"[", pare_close, r"][", punc, r"]"
    )
    pattern = re.compile(''.join(pattern_str), re.MULTILINE | re.DOTALL)
    message = Report.misplaced(what="punctuation mark", where="after closing bracket",
                               to_where="before")
    re_lib["bracketpunc"] = (pattern, message)

    # FP: code, literal
    pattern_str = r"([" + pare_open + r"]\s)|(\s[" + pare_close + r"])"
    pattern = re.compile(pattern_str, re.MULTILINE)
    message = Report.existing(what="space", where="after/before opening/closing bracket")
    re_lib["spacebracket"] = (pattern, message)

    pattern_str = r"[" + punc + r"][" + pare_close + r"]?\s*\Z"
    pattern = re.compile(pattern_str)
    message = Report.missing(what="punctuation mark", where="at {0} end")
    re_lib["nopuncend"] = (pattern, message)

    # FP: code
    pattern_str = r"[,;]\s*\Z"
    pattern = re.compile(pattern_str)
    message = Report.existing(what="comma", where="at paragraph end")
    re_lib["commaend"] = (pattern, message)

    # match: uppercase to not: ellipsis, directive starter, number, extensions...
    # FP: code, target
    punc_nodot = punc.replace('.', '').replace(',', '')
    pattern_str = r"[" + punc_nodot + r"][" + pare_close + r"]?\S|\.[A-Z]|,[^\s\d]"
    pattern = re.compile(pattern_str)
    message = Report.missing(what="space", where="after punctuation mark")
    re_lib["puncspaceend"] = (pattern, message)

    pattern_str = r"\w\"\w"
    pattern = re.compile(pattern_str)
    message = Report.missing(what="space", where="after/before quote mark")
    re_lib["unquote"] = (pattern, message)

    # not match: 'a' article; more than two letters are detected as misspelling
    pattern_str = r"\w' +[b-zA-Z]\b"
    pattern = re.compile(pattern_str)
    message = Report.existing(what="space", where="after apostrophe")
    re_lib["spaceapos"] = (pattern, message)

    pattern_str = r"([^\w\d\s\-\.])\1|(?<!\.)(?:\.{2}|\.{4})(?!\.)"
    pattern = re.compile(pattern_str)
    message = Report.existing(what="double punctuation")
    re_lib["double"] = (pattern, message)

    # not match: ellipsis
    pattern_str = r"\s[" + punc + r"](?!\.\.)"
    pattern = re.compile(pattern_str)
    message = Report.existing(what="space", where="before punctuation mark")
    re_lib["puncspacestart"] = (pattern, message)

    # FP: code, literal, footnote
    pattern_str = r"\w[" + pare_open + r"](?!s\))|[" + pare_close + r"]\w"
    pattern = re.compile(pattern_str)
    message = Report.missing(what="space", where="after/before bracket")
    re_lib["unbracket"] = (pattern, message)

    # Style
    pattern_str = r"\w/s\b"
    pattern = re.compile(pattern_str)
    message = Report.substitution(what="optional plural", with_what="(s)")
    re_lib["optplur"] = (pattern, message)

    # FP: cut toctree
    pattern_str = r"&"
    pattern = re.compile(pattern_str)
    message = Report.substitution(what="Ampersand", where="in continuous text",
                                  with_what="written out and")
    re_lib["enumamp"] = (pattern, message)

    pattern_str = r"/"
    pattern = re.compile(pattern_str)
    message = Report.conditional(what="Slash", where="in continuous text",
                                 with_what="written out or/per", when="(if it not short for alias)")
    re_lib["enumslash"] = (pattern, message)

    pattern_str = r">"
    pattern = re.compile(pattern_str)
    message = Report.substitution(what="greater-than sign", with_what="written out")
    re_lib["greater"] = (pattern, message)

    pattern_str = r"<"
    pattern = re.compile(pattern_str)
    message = Report.substitution(what="less-than sign", with_what="written out")
    re_lib["less"] = (pattern, message)

    pattern_str = r"~"
    pattern = re.compile(pattern_str)
    message = Report.substitution(what="about sign", with_what="written out")
    re_lib["about"] = (pattern, message)

    args = dict()
    args["re_lib"] = re_lib

    return args


def mark(document, reports, re_lib):
    """Check for punctuation marks and parenthesis."""
    toolname = "mark"

    instr_pos = {
        "field": {"*": ["name", "body"]},
        "*": {"*": ["head", "body"]}
    }
    instr_neg = {
        "dir": {
            "figure": ["head"], "toctree": "*", "include": "*", "index": "*",
            "code-block": "*", "default": "*", "youtube": "*", "vimeo": "*"
        },
        "substdef": {"image": ["head"], "unicode": "*", "replace": "*"},
        "doctest": "*",
        "literal": "*", "standalone": "*"
    }

    for part in rst_walker.iter_nodeparts_instr(document.body, instr_pos, instr_neg):
        if part.parent_node.node_name == "text":
            part_str = str(part.code)
            for key, value in re_lib.items():
                if key in {"nopuncend", "commaend"}:
                    continue
                pattern = value[0]
                for m in re.finditer(pattern, part_str):
                    output = part.code.slice_match_obj(m, 0, True)
                    line = getline_punc(document.body.code, output.start_pos,
                                        output.span_len(True), 50, 0)
                    reports.append(Report('W', toolname, output, value[1], line))


    instr_pos = {
        "field": {"*": ["body"]},
        "*": {"*": ["head", "body"]}
    }
    instr_neg = {
        "dir": {
            "figure": ["head"], "toctree": "*", "include": "*", "index": "*",
            "admonition": ["head"], "hint": ["head"], "important": ["head"],
            "note": ["head"], "tip": ["head"], "warning": ["head"], "rubric": ["head"],
            "code-block": "*", "default": "*", "youtube": "*", "vimeo": "*"
        },
        "substdef": "*",
        "def": {"*": ["head"]}, "target": {"*": ["head"]},
        "doctest": "*",
        "standalone": "*",
        "grid-table": "*", "simple-table": "*"
    }

    noend_re = re_lib["nopuncend"][0]
    comma_re = re_lib["commaend"][0]
    for part in rst_walker.iter_nodeparts_instr(document.body, instr_pos, instr_neg):
        if not part.parent_node.next:
            if part.parent_node.node_name == "text":
                part_str = str(part.code)
                if (not re.search(noend_re, part_str) and
                        (len(part_str.strip()) != 0 or
                         (part.parent_node.prev and
                          part.parent_node.prev.code.end_lincol[0] == part.code.start_lincol[0]))):
                    par_node = part.parent_node
                    while par_node.node_name == "text":
                        par_node = par_node.parent_node.parent_node

                    # refbox parts
                    if (not rst_walker.is_of(par_node, "field",
                                             ("Hotkey", "Menu", "Panel", "Mode",
                                              "Tool", "Editor", "Header", "Type")) and
                            (not rst_walker.is_of(part.next_leaf(), "dir", "default") or
                             part_str.endswith(" "))):
                        output = part.code.copy().clear(False)
                        message = re_lib["nopuncend"][1].format("paragraph")
                        line = getline_punc(document.body.code, part.code.end_pos, 0, 50, 0)
                        reports.append(Report('W', toolname, output, message, line))

                else:
                    if comma_m := re.search(comma_re, part_str):
                        output = part.code.slice_match_obj(comma_m, 0, True)
                        message = re_lib["commaend"][1].format(part.parent_node.node_name +
                                                               " " + part.node_name)
                        reports.append(Report('W', toolname, output, message))

        elif rst_walker.is_of(part, ("role", "hyperlink"), "*", "head"):
            if re.search(noend_re, str(part.code)):
                output = part.code.copy().clear(False)
                message = re_lib["nopuncend"][1].format(part.parent_node.node_name + " " +
                                                        part.node_name)
                reports.append(Report('W', toolname, output, message))

    return reports


def whitespace_pre(_):
    re_lib = dict()
    pattern_str = r"(\t)"
    pattern = re.compile(pattern_str)
    message = Report.existing(what="tab char")
    repl = "   "
    re_lib["tab"] = (pattern, message, repl)

    pattern_str = r"( +?)\n"
    pattern = re.compile(pattern_str)
    message = Report.existing(what="spaces", where="at line end")
    repl = ""
    re_lib["spaceeol"] = (pattern, message, repl)

    # FP: code, unicode, comment
    # not match: indent at start, trailing at eol
    pattern_str = r"\S(  +)(?:\S|\Z)"
    pattern = re.compile(pattern_str)
    message = Report.existing(what="multiple spaces", where="in text")
    repl = " "
    re_lib["multispace"] = (pattern, message, repl)

    # match: at start (when not line start), trailing at eol
    pattern_str = r"\A(  +)(?:\S|\Z)"
    pattern = re.compile(pattern_str)
    message = Report.existing(what="multiple spaces", where="at start")
    repl = " "
    re_lib["multispacestart"] = (pattern, message, repl)

    args = dict()
    args["re_lib"] = re_lib

    return args


def whitespace(document, reports, re_lib):
    """Check whitespace chars."""
    toolname = "whitespace"

    text = str(document.code)
    for key, value in re_lib.items():
        if key in {"multispace", "multispacestart"}:
            continue
        pattern = value[0]
        for m in re.finditer(pattern, text):
            output = document.body.code.slice_match_obj(m, 0, True)
            line = getline_punc(document.body.code, m.start(), len(m.group(0)), 50, 0)
            fg_repl = document.body.code.slice_match_obj(m, 1, True)
            fg_repl.replace_fill(value[2])
            reports.append(Report('W', toolname, output, value[1], line, fg_repl))

    instr_pos = {
        "field": {"*": ["name", "body"]},
        "*": {"*": "*"}
    }
    instr_neg = {
        "dir": {"code-block": "*", "default": "*"},
        "substdef": {"image": ["head"], "unicode": "*"},
        "doctest": "*", "comment": "*",
        "grid-table": "*", "simple-table": "*"
    }

    multi_start_re = re_lib["multispacestart"][0]
    multi_re = re_lib["multispace"][0]
    for part in rst_walker.iter_nodeparts_instr(document.body, instr_pos, instr_neg):
        if part.child_nodes.is_empty:
            part_str = str(part.code)
            if part.code.start_lincol[1] != 0:
                if multi_start_m := re.match(multi_start_re, part_str):
                    output = part.code.slice_match_obj(multi_start_m, 1, True)
                    line = getline_punc(document.body.code, output.start_pos,
                                        output.span_len(True), 50, 0)
                    fg_repl = output.copy().replace_fill(value[2])
                    reports.append(Report('W', toolname, output, re_lib["multispacestart"][1],
                                          line, fg_repl))

            for multi_m in re.finditer(multi_re, part_str):
                output = part.code.slice_match_obj(multi_m, 1, True)
                line = getline_punc(document.body.code, output.start_pos,
                                    output.span_len(True), 50, 0)
                fg_repl = output.copy().replace_fill(value[2])
                reports.append(Report('W', toolname, output, re_lib["multispace"][1],
                                      line, fg_repl))

    return reports



OPS = (
    ("number", number, number_pre),
    ("pairs", pairs, pairs_pre),
    ("mark", mark, mark_pre),
    ("whitespace", whitespace, whitespace_pre)
)


if __name__ == "__main__":
    from monostyle.cmd import main
    main(OPS, __doc__, __file__)
