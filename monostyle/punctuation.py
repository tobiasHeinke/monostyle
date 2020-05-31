
"""
punctuation
~~~~~~~~~~~

Punctuation style checks and number formatting.
"""

import os
import re

import monostyle.util.monostylestd as monostylestd
from monostyle.util.report import Report, print_reports
from monostyle.util.fragment import Fragment
from monostyle.rst_parser.core import RSTParser
import monostyle.rst_parser.walker as rst_walker
from monostyle.util.pos import PartofSpeech
from monostyle.util.char_catalog import CharCatalog

POS = PartofSpeech()
CharCatalog = CharCatalog()


def number_pre():

    re_lib = dict()
    # FP: code, literal, Years
    start = r"(?:(?<=[^\d,.])|\A)"
    pattern_str = start + r"[\d,]*\d{4}"
    pattern = re.compile(pattern_str)
    msg = Report.missing(what="separator", where="between four digits")
    re_lib["digitsep"] = (pattern, msg)

    pattern_str = r"\d \d"
    pattern = re.compile(pattern_str)
    msg = Report.existing(what="space", where="between digits")
    re_lib["digitspace"] = (pattern, msg)

    spelled_out = r"\b" + r"\b|\b".join(POS.data["determiner"]["quantifier"]["number"])
    spelled_out += r"\b|" + r"\b|\b".join(POS.data["determiner"]["quantifier"]["ordinal"])
    spelled_out += r"\b|" + r"\b|\b".join(("half", "halves", "thirds?"))
    pattern_str = r"(?:" + spelled_out + r") (?:" + spelled_out + r")"
    pattern = re.compile(pattern_str)
    msg = Report.missing(what="hyphen", where="between spelled-out numbers")
    re_lib["spelloutspace"] = (pattern, msg)

    # FP: math, code
    pattern_str = r"(?:\w |^)([0-9]|1[0-2])(?: \w|$)"
    pattern = re.compile(pattern_str)
    msg = Report.existing(what="low digit", where="in continuous text")
    re_lib["lowdigit"] = (pattern, msg)

    pattern_str = start + r"\.\d"
    pattern = re.compile(pattern_str)
    msg = Report.missing(what="zero", where="in front of a decimal point")
    re_lib["nozero"] = (pattern, msg)

    pattern_str = start + r"0[1-9]"
    pattern = re.compile(pattern_str)
    msg = Report.existing(what="zero", where="at number start")
    re_lib["zeronodot"] = (pattern, msg)

    pattern_str = start + r"\d\.\d*0{2,}(?=\D|\Z)"
    pattern = re.compile(pattern_str)
    msg = Report.existing(what="zeros", where="at number end")
    re_lib["zerotrail"] = (pattern, msg)


    pattern_str = r"\d ?x( ?\d)?"
    pattern = re.compile(pattern_str)
    msg = Report.option(what="x letter", with_what="times or × sign")
    re_lib["times"] = (pattern, msg)

    pattern_str = r"\d\.\.+\d"
    pattern = re.compile(pattern_str)
    msg = Report.option(what="range separator", with_what="to or dash")
    re_lib["range"] = (pattern, msg)

    pattern_str = r"\D(?:0|100)%"
    pattern = re.compile(pattern_str)
    msg = Report.option(what="percentage limits", with_what="spelled out no or fully")
    re_lib["percentlimit"] = (pattern, msg)

    #-----------------

    pattern_str = r"\b[0-9]d\b"
    pattern = re.compile(pattern_str)
    msg = Report.misformatted(what="lowercase dimension letter")
    re_lib["dimension"] = (pattern, msg)

    pattern_str = r"\d [%‰‱]"
    pattern = re.compile(pattern_str)
    msg = Report.existing(what="space", where="before percentage sign")
    re_lib["percent"] = (pattern, msg)

    pattern_str = r"\d °(?! ?C\b)"
    pattern = re.compile(pattern_str)
    msg = Report.existing(what="space", where="before degree sign")
    re_lib["degree"] = (pattern, msg)

    pattern_str = r"\d° ?C\b|° C\b"
    pattern = re.compile(pattern_str)
    msg = Report.substitution(what="Celsius", with_what="°C")
    re_lib["celsius"] = (pattern, msg)

    units = (
        'D', 'th', 'nd', 'st', 'rd', # math
        'px', 'p', 'bit', r'ki?', r'Mi?B', r'Gi?B', r'Ti?B' # digital
    )
    pattern_str = r"\d(?!\W|\d|" + r'\b|'.join(units) + r"\b|\Z)"
    pattern = re.compile(pattern_str)
    msg = Report.missing(what="space", where="before physics unit")
    re_lib["nospaceunit"] = (pattern, msg)

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
            "figure": ["head", "attr"],
            "code-block": "*", "default":"*", "youtube":"*", "vimeo":"*"
        },
        "substdef": {"image": ["head", "attr"], "unicode":"*", "replace":"*"},
        "role": {"doc": ["id"], "ref": ["id"], "term": ["id"], "kbd": "*"},
        "hyperlink": {"*": ["id"]},
        "literal": "*", "standalone": "*",
        "footref": "*", "citref": "*"
    }

    for part in rst_walker.iter_nodeparts_instr(document.body, instr_pos, instr_neg):
        part_str = str(part.code)
        for value in re_lib.values():
            pattern = value[0]
            for m in re.finditer(pattern, part_str):
                out = part.code.slice_match_obj(m, 0, True)
                line = monostylestd.getline_punc(document.body.code,
                                                 part.code.start_pos + m.start(),
                                                 len(m.group(0)), 50, 0)
                reports.append(Report('W', toolname, out, value[1], line))

    return reports


def pairs_pre():
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
        "dir": {"code-block": "*", "default":"*", "math":"*", "youtube":"*", "vimeo":"*"},
        "substdef": {"unicode":"*", "replace":"*"},
        "target": "*",
        "comment": "*",
        "role": {"kbd": "*", "menuselection": "*", "class": "*", "mod": "*", "math": "*"},
        "hyperlink": {"*": ["id"]}, "literal": "*",
        "standalone": "*"
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
                for index, ent in enumerate(reversed(stack)):
                    if (ent[0] == pair_char or
                            (pair_char in pairs_map and ent[0] == pairs_map[pair_char])):

                        if (max_line_span is not None and
                                line.start_lincol[0] - ent[1][0] > max_line_span):
                            lincol_abs = line.loc_to_abs((0, pair_m.start(0)))
                            msg = "long span"
                            msg += " - " + str(lincol_abs[0] + 1) + ","
                            msg += str(lincol_abs[1] + 1)
                            out = Fragment(document.code.fn, ent[0], -1, start_lincol=ent[1])
                            reports.append(Report('W', toolname, out, msg))

                        # invert index
                        index = len(stack) - 1 - index
                        stack.pop(index)
                        break

                else:
                    stack.append((pair_char, line.loc_to_abs((0, pair_m.start(0)))))

            for markup_m in re.finditer(markup_re, line_str):
                out = line.slice_match_obj(markup_m, 0, True)
                reports.append(Report('E', toolname, out, "leaked markup char"))

    if len(stack) != 0:
        msg = "unclosed pairs"
        for ent in stack:
            out = Fragment(document.code.fn, ent[0], -1, start_lincol=ent[1])
            reports.append(Report('W', toolname, out, msg))

    if max_line_span is not None:
        for node in rst_walker.iter_node(document.body,
                                         ("literal", "strong", "emphasis", "int-target",
                                          "role", "hyperlink")):

            if not node.body_start or not node.body_end:
                # single word int-target or hyperlink
                continue

            if (node.body_start.code.end_lincol[0] - node.body_end.code.start_lincol[0] >
                    max_line_span):
                msg = "long span"
                msg += " - " + str(node.body_start.code.end_lincol[0] + 1)
                msg += "," + str(node.body_end.code.start_lincol[1] + 1)
                reports.append(Report('W', toolname, node.body_start.code, msg))

            if node.body_start.code.end_pos == node.body_end.code.start_pos:
                msg = "zero span"
                reports.append(Report('W', toolname, node.code, msg))

    return reports


def mark_pre():

    re_lib = dict()
    punc = CharCatalog.data["terminal"]["final"] + CharCatalog.data["secondary"]["final"]
    punc_sent = CharCatalog.data["terminal"]["final"] + ':'
    pare_open = CharCatalog.data["bracket"]["left"]["normal"]
    pare_close = CharCatalog.data["bracket"]["right"]["normal"]

    # limitation: not nested parenthesis
    # not match abbr
    pattern_str = r"(?<!\w\.\w)[" + punc_sent + r"]\s+?" + r"[" + pare_open + r"]?[a-z]"
    pattern = re.compile(pattern_str, re.MULTILINE | re.DOTALL)
    msg = Report.misformatted(what="lowercase", where="after punctuation mark")
    re_lib["punclower"] = (pattern, msg)

    # limitation: not nested parenthesis
    # FN: inline markup
    pattern_str = (
        r"[", punc_sent, r"]\s*?",
        r"[", pare_open, r"][^", pare_close, r"]+?",
        r"[", pare_close, r"][", punc, r"]"
    )
    pattern = re.compile(''.join(pattern_str), re.MULTILINE | re.DOTALL)
    msg = Report.misplaced(what="punctuation mark", where="after closing bracket",
                           to_where="before")
    re_lib["bracketpunc"] = (pattern, msg)

    # FP: code, container
    pattern_str = r"[" + pare_open + r"]?[a-z]"
    pattern = re.compile(pattern_str)
    msg = Report.misformatted(what="lowercase", where="at paragraph start")
    re_lib["lowerpara"] = (pattern, msg)

    # FP: code, literal
    pattern_str = r"([" + pare_open + r"]\s)|(\s[" + pare_close + r"])"
    pattern = re.compile(pattern_str, re.MULTILINE)
    msg = Report.existing(what="space", where="after/before opening/closing bracket")
    re_lib["spacebracket"] = (pattern, msg)

    # FP: abbr, menu, heading, code
    pattern_str = r"[^.\s]\s*?[" + pare_open + r"][A-Z][a-z ]"
    pattern = re.compile(pattern_str, re.MULTILINE)
    msg = Report.misformatted(what="uppercase", where="at bracket start")
    re_lib["upperbracket"] = (pattern, msg)

    pattern_str = r"[" + punc + r"][" + pare_close + r"]?\s*\Z"
    pattern = re.compile(pattern_str)
    msg = Report.missing(what="punctuation mark", where="at {0} end")
    re_lib["nopuncend"] = (pattern, msg)

    # FP: code
    pattern_str = r"[,;]\s*\Z"
    pattern = re.compile(pattern_str)
    msg = Report.existing(what="comma", where="at paragraph end")
    re_lib["commaend"] = (pattern, msg)

    # match: uppercase to not: ellipsis, directive starter, number, extensions...
    # FP: code, target
    # todo comma number
    punc_nodot = punc.replace('.', '')
    pattern_str = r"[" + punc_nodot + r"][" + pare_close + r"]?\S|\.[A-Z]"
    pattern = re.compile(pattern_str)
    msg = Report.missing(what="space", where="after punctuation mark")
    re_lib["puncspaceend"] = (pattern, msg)

    pattern_str = r"\w\"\w"
    pattern = re.compile(pattern_str)
    msg = Report.missing(what="space", where="after/before quote mark")
    re_lib["unquote"] = (pattern, msg)

    pattern_str = r"([^\w\d\s\-\.])\1|(?<!\.)\.\.(?!\.)"
    pattern = re.compile(pattern_str)
    msg = Report.existing(what="double punctuation")
    re_lib["double"] = (pattern, msg)

    # not match: ellipsis
    pattern_str = r"\s[" + punc + r"](?!\.\.)"
    pattern = re.compile(pattern_str)
    msg = Report.existing(what="space", where="before punctuation mark")
    re_lib["puncspacestart"] = (pattern, msg)

    # FP: code, literal, footnote
    pattern_str = r"\w[" + pare_open + r"](?!s\))|[" + pare_close + r"]\w"
    pattern = re.compile(pattern_str)
    msg = Report.missing(what="space", where="after/before bracket")
    re_lib["unbracket"] = (pattern, msg)

    # Style
    pattern_str = r"\w/s\b"
    pattern = re.compile(pattern_str)
    msg = Report.substitution(what="optional plural", with_what="(s)")
    re_lib["optplur"] = (pattern, msg)

    # FP: cut toctree
    pattern_str = r"&"
    pattern = re.compile(pattern_str)
    msg = Report.substitution(what="Ampersand", where="in continuous text",
                              with_what="spelled out and")
    re_lib["enumamp"] = (pattern, msg)

    pattern_str = r"/"
    pattern = re.compile(pattern_str)
    msg = Report.conditional(what="Slash", where="in continuous text",
                             with_what="spelled out or", when="(if it not short for alias)")
    re_lib["enumslash"] = (pattern, msg)

    pattern_str = r">"
    pattern = re.compile(pattern_str)
    msg = Report.substitution(what="greater-than sign", with_what="spelled out")
    re_lib["greater"] = (pattern, msg)

    pattern_str = r"<"
    pattern = re.compile(pattern_str)
    msg = Report.substitution(what="less-than sign", with_what="spelled out")
    re_lib["less"] = (pattern, msg)

    args = dict()
    args["re_lib"] = re_lib

    return args


def mark(document, reports, re_lib):
    """Check for punctuation marks and parenthesis."""
    toolname = "mark"

    instr_neg = {
        "dir": {
            "figure": ["head", "attr"], "toctree":"*",
            "code-block": "*", "default":"*", "youtube":"*", "vimeo":"*"
        },
        "substdef": {"image": ["head", "attr"], "unicode":"*", "replace":"*"},
        "role": {"doc": ["id"], "ref": ["id"], "term": ["id"], "abbr": ["id"]},
        "hyperlink": {"*": ["id"]},
        "standalone": "*"
    }
    instr_pos = {
        "field": {"*": ["name", "body"]},
        "*": {"*": ["head", "body"]}
    }

    for part in rst_walker.iter_nodeparts_instr(document.body, instr_pos, instr_neg):
        if part.parent_node.node_name == "text":
            part_str = str(part.code)
            for key, value in re_lib.items():
                if key not in ("lowerpara", "nopuncend", "commaend"):
                    pattern = value[0]
                    for m in re.finditer(pattern, part_str):
                        out = part.code.slice_match_obj(m, 0, True)
                        line = monostylestd.getline_punc(document.body.code,
                                                         part.code.start_pos + m.start(),
                                                         len(m.group(0)), 50, 0)
                        reports.append(Report('W', toolname, out, value[1], line))


    instr_pos = {
        "field": {"*": ["body"]},
        "*": {"*": ["head", "body"]}
    }
    instr_neg = {
        "dir": {
            "*": ["attr"], "figure": ["head", "attr"], "toctree": "*",
            "admonition": ["head"], "hint": ["head"], "important": ["head"],
            "note": ["head"], "tip": ["head"], "warning": ["head"], "rubric": ["head"],
            "code-block": "*", "default":"*", "youtube":"*", "vimeo":"*"
        },
        "substdef": "*",
        "def": {"*": ["head"]},
        "target": {"*": ["head"]},
        "role": {"doc": ["id"], "ref": ["id"], "term": ["id"]},
        "hyperlink": {"*": ["id"]},
        "standalone": "*"
    }

    start_re = re_lib["lowerpara"][0]
    noend_re = re_lib["nopuncend"][0]
    comma_re = re_lib["commaend"][0]
    was_empty = False
    for part in rst_walker.iter_nodeparts_instr(document.body, instr_pos, instr_neg):
        if not part.parent_node.prev or was_empty:
            if (part.parent_node.node_name == "text" or
                    part.parent_node.parent_node.parent_node.node_name == "text"):

                if re.match(start_re, str(part.code)):
                    out = part.code.copy()
                    out.clear(True)
                    line = monostylestd.getline_punc(document.body.code, part.code.start_pos,
                                                     0, 50, 0)
                    reports.append(Report('W', toolname, out, re_lib["lowerpara"][1], line))

                was_empty = bool(len(part.code) == 0)

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
                                              "Tool", "Editor", "Header", "Type"))):

                        out = part.code.copy().clear(False)
                        msg = re_lib["nopuncend"][1].format("paragraph")
                        line = monostylestd.getline_punc(document.body.code, part.code.end_pos,
                                                         0, 50, 0)
                        reports.append(Report('W', toolname, out, msg, line))

                else:
                    if comma_m := re.search(comma_re, part_str):
                        out = Fragment(document.code.fn, comma_m.group(0),
                                                    part.code.start_pos + comma_m.start(),
                                                    start_lincol=part.code.end_lincol)
                        msg = re_lib["commaend"][1].format(part.parent_node.node_name +
                                                           " " + part.node_name)
                        reports.append(Report('W', toolname, out, msg))

        elif rst_walker.is_of(part, ("role", "hyperlink"), "*", "head"):
            if noend_m := re.search(noend_re, str(part.code)):
                out = Fragment(document.code.fn, noend_m.group(0),
                                            part.code.start_pos + noend_m.start(),
                                            start_lincol=part.code.end_lincol)
                msg = re_lib["nopuncend"][1].format(part.parent_node.node_name + " " +
                                                    part.node_name)
                reports.append(Report('W', toolname, out, msg))

    return reports


def whitespace_pre():

    re_lib = dict()
    pattern_str = r"\t"
    pattern = re.compile(pattern_str)
    msg = Report.existing(what="tab char")
    re_lib["tab"] = (pattern, msg)

    pattern_str = r" +?\n"
    pattern = re.compile(pattern_str)
    msg = Report.existing(what="spaces", where="at line end")
    re_lib["spaceeol"] = (pattern, msg)

    # FP: code, unicode, comment
    # not match: indent at start, trailing at eol
    pattern_str = r"\S(  +)(?:\S|\Z)"
    pattern = re.compile(pattern_str)
    msg = Report.existing(what="multiple spaces", where="in text")
    re_lib["multispace"] = (pattern, msg)

    # match: at start (when not line start), trailing at eol
    pattern_str = r"\A(  +)(?:\S|\Z)"
    pattern = re.compile(pattern_str)
    msg = Report.existing(what="multiple spaces", where="at start")
    re_lib["multispacestart"] = (pattern, msg)

    args = dict()
    args["re_lib"] = re_lib

    return args


def whitespace(document, reports, re_lib):
    """Check whitespace chars."""
    toolname = "whitespace"

    text = str(document.code)
    for key, value in re_lib.items():
        if key not in ("multispace", "multispacestart"):
            pattern = value[0]
            for m in re.finditer(pattern, text):
                out = document.body.code.slice_match_obj(m, 0, True)
                line = monostylestd.getline_punc(document.body.code, m.start(),
                                                 len(m.group(0)), 50, 0)
                reports.append(Report('W', toolname, out, value[1], line))

    instr_pos = {
        "field": {"*": ["name", "body"]},
        "*": {"*": "*"}
    }
    instr_neg = {
        "dir": {"code-block": "*", "default":"*"},
        "substdef": {"image": ["head", "attr"], "unicode":"*"},
        "comment": "*"
    }

    multi_start_re = re_lib["multispacestart"][0]
    multi_re = re_lib["multispace"][0]
    for part in rst_walker.iter_nodeparts_instr(document.body, instr_pos, instr_neg):
        if part.child_nodes.is_empty:
            part_str = str(part.code)
            if part.code.start_lincol[1] != 0:
                if multi_start_m := re.match(multi_start_re, part_str):
                    out = part.code.slice_match_obj(multi_start_m, 1, True)
                    line = monostylestd.getline_punc(document.body.code,
                                                     part.code.start_pos + multi_start_m.start(),
                                                     len(multi_start_m.group(1)), 50, 0)
                    reports.append(Report('W', toolname, out, re_lib["multispacestart"][1], line))

            for multi_m in re.finditer(multi_re, part_str):
                out = part.code.slice_match_obj(multi_m, 1, True)
                line = monostylestd.getline_punc(document.body.code,
                                                 part.code.start_pos + multi_m.start(),
                                                 len(multi_m.group(1)), 50, 0)
                reports.append(Report('W', toolname, out, re_lib["multispace"][1], line))

    return reports




OPS = (
    ("number", number, number_pre),
    ("pairs", pairs, pairs_pre),
    ("mark", mark, mark_pre),
    ("whitespace", whitespace, whitespace_pre)
)


def init(op_names):
    if isinstance(op_names, str):
        op_names = [op_names]

    ops = []
    for op_name in op_names:
        for op in OPS:
            if op_name == op[0]:
                args = {}
                if len(op) > 2:
                    # evaluate pre
                    args = op[2]()

                ops.append((op[1], args))
                break
        else:
            print("repattern: unknown operation: " + op_name)

    return ops


def hub(op_names):
    rst_parser = RSTParser()
    ops = init(op_names)
    reports = []

    for fn, text in monostylestd.rst_texts():
        document = rst_parser.parse_full(rst_parser.document(fn, text))

        for op in ops:
            reports = op[0](document, reports, **op[1])

    return reports


def main():

    import argparse

    descr = __doc__.replace('~', '')
    parser = argparse.ArgumentParser(description=descr)
    for op in OPS:
        doc_str = ''
        if op[1].__doc__ is not None:
            # first char to lowercase
            doc_str = op[1].__doc__[0].lower() + op[1].__doc__[1:]
        parser.add_argument("--" + op[0], dest="op_names",
                            action='store_const', const=op[0], metavar="",
                            help=doc_str)

    parser.add_argument("-r", "--root",
                        dest="root", nargs='?', const="",
                        help="defines the ROOT directory of the project")

    args = parser.parse_args()

    if args.root is None:
        root_dir = os.getcwd()
    else:
        root_dir = os.path.normpath(args.root)

        if not os.path.exists(root_dir):
            print('Error: root {0} does not exists'.format(args.root))
            return 2

    root_dir = monostylestd.replace_windows_path_sep(root_dir)
    monostylestd.ROOT_DIR = root_dir

    reports = hub(args.op_names)
    print_reports(reports)


if __name__ == "__main__":
    main()
