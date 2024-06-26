
"""
punctuation
~~~~~~~~~~~

Punctuation style checks and number formatting.
"""

import re

import monostyle.util.monostyle_io as monostyle_io
from monostyle.util.report import Report
import monostyle.rst_parser.walker as rst_walker
from monostyle.util.part_of_speech import PartofSpeech
from monostyle.util.char_catalog import CharCatalog


def mark_pre(_):
    char_catalog = CharCatalog()

    re_lib = dict()
    punc = char_catalog.data["terminal"]["final"] + char_catalog.data["secondary"]["final"]
    punc_sent = char_catalog.data["terminal"]["final"] + ':'
    pare_open = char_catalog.data["bracket"]["left"]["normal"]
    pare_close = char_catalog.data["bracket"]["right"]["normal"]

    # limitation: not nested parenthesis
    # FN: inline markup
    re_lib["bracketpunc"] = (
        re.compile(''.join((r"[", punc_sent, r"]\s*?", r"[", pare_open, r"][^", pare_close, r"]+?",
                            r"[", pare_close, r"][", punc, r"]")), re.MULTILINE | re.DOTALL),
        Report.misplaced(what="punctuation mark", where="after closing bracket",
                         to_where="before"))

    # FP: code, literal
    re_lib["spacebracket"] = (
        re.compile(r"([" + pare_open + r"] )|( [" + pare_close + r"])", re.MULTILINE),
        Report.existing(what="space", where="after/before opening/closing bracket"))

    re_lib["puncend"] = (re.compile(r"[" + punc + r"][" + pare_close + r"]?\s*\Z"),
        (Report.missing(what="punctuation mark", where="at {0} end"),
        Report.existing(what="punctuation mark", where="at {0} end")))

    # FP: code
    re_lib["commaend"] = (re.compile(r"[,;]\s*\Z"),
        Report.existing(what="comma", where="at paragraph end"))

    # match: uppercase to not: ellipsis, directive starter, number, extensions...
    # FP: code, target
    re_lib["puncspaceend"] = (
        re.compile(''.join((r"[", punc.replace('.', '').replace(',', ''), r"][",
                            pare_close, r"]?\S|\.[A-Z]|,[^\s\d]"))),
        Report.missing(what="space", where="after punctuation mark"))

    re_lib["unquote"] = (re.compile(r"\w\"\w"),
        Report.missing(what="space", where="after/before quote mark"))

    # not match: 'a' article; more than two letters are detected as misspelling
    re_lib["aposspace"] = (re.compile(r"\w' +[b-zA-Z]\b"),
        Report.existing(what="space", where="after apostrophe"))

    re_lib["ellipsisspace"] = (re.compile(r"\.{3} +[" + punc + pare_close + r"]"),
        Report.existing(what="space", where="after ellipsis"))

    re_lib["double"] = (re.compile(r"([^\w\d\s\\.-])\1|(?<!\.)(?:\.{2}|\.{4})(?!\.)"),
        Report.existing(what="double punctuation"))

    # not match: indent, ellipsis
    re_lib["puncspacestart"] = (re.compile(r"\S( +[" + punc + r"])(?!\.\.)"),
        Report.existing(what="space", where="before punctuation mark"))

    # FP: code, literal, footnote
    re_lib["unbracket"] = (re.compile(r"\w[" + pare_open + r"](?!s\))|[" + pare_close + r"]\w"),
        Report.missing(what="space", where="after/before bracket"))

    # Line
    re_lib["closesol"] = (
        re.compile(r"^\s*[" + punc + char_catalog.get(("quote", "final")) + r"]", re.MULTILINE),
        Report.existing(what="closing punctuation", where="at line start"))

    re_lib["openeol"] = (
        re.compile(r"[" + pare_open + char_catalog.get(("quote", "initial")) + r"]\s*?\n"),
        Report.existing(what="opening punctuation", where="at line end"))

    # Style
    re_lib["optplur"] = (re.compile(r"\w/e?s\b"),
        Report.substitution(what="optional plural", with_what="(s)"))

    # FP: cut toctree
    re_lib["enumamp"] = (re.compile(r"&"),
        Report.substitution(what="Ampersand", where="in continuous text",
                                  with_what="written out and"))

    re_lib["enumslash"] = (re.compile(r"/"),
        Report.conditional(what="Slash", where="in continuous text",
                           with_what="written out or/per",
                           when="(if it not short for alias)"))

    re_lib["greater"] = (re.compile(r">"),
        Report.substitution(what="greater-than sign", with_what="written out"))

    re_lib["less"] = (re.compile(r"<"),
        Report.substitution(what="less-than sign", with_what="written out"))

    re_lib["about"] = (re.compile(r"~"),
        Report.substitution(what="about sign", with_what="written out"))

    args = dict()
    args["re_lib"] = re_lib

    return args


def mark(toolname, document, reports, re_lib):
    """Check for punctuation marks and parenthesis."""
    threshold_space = 2

    def is_sentence(part, par_node, instr_pos, instr_neg, space_re):
        if par_node.node_name == "row":
            par_node = par_node.parent_node.parent_node
        if not par_node or not par_node.parent_node:
            return True
        par_node = par_node.parent_node.parent_node
        if (not par_node.node_name.endswith("-list") and
                not par_node.node_name.endswith("-table")):
            return True

        space_counter = 0
        for part in rst_walker.iter_nodeparts_instr(part.parent_node.parent_node,
                                                    instr_pos, instr_neg):
            if rst_walker.is_of(part, "role", "menuselection"):
                space_counter += 1
                if space_counter > threshold_space:
                    return True
                continue

            for _ in re.finditer(space_re, str(part.code)):
                space_counter += 1
                if space_counter > threshold_space:
                    return True

        return False

    instr_pos = {
        "field": {"*": ["name", "body"]},
        "*": {"*": ["head", "body"]}
    }
    instr_neg = {
        "dir": {
            "figure": ["head"], "toctree": "*", "include": "*", "index": "*",
            "code-block": "*", "default": "*", "youtube": "*", "vimeo": "*", "peertube": "*"
        },
        "substdef": {"image": ["head"], "unicode": "*", "replace": "*"},
        "doctest": "*",
        "literal": "*", "standalone": "*"
    }

    for part in rst_walker.iter_nodeparts_instr(document.body, instr_pos, instr_neg):
        if part.parent_node.node_name == "text":
            part_str = str(part.code)
            for key, value in re_lib.items():
                if key in {"puncend", "commaend"}:
                    continue
                pattern = value[0]
                for m in re.finditer(pattern, part_str):
                    if m.start() == 0 and key == "closesol" and part.parent_node.prev:
                        continue
                    reports.append(
                        Report('W', toolname, part.code.slice_match(m, 0), value[1])
                        .set_line_punc(document.body.code, 50, 30))


    instr_pos = {
        "field": {"*": ["body"]},
        "*": {"*": ["head", "body"]}
    }
    instr_neg = {
        "dir": {
            "figure": ["head"], "toctree": "*", "include": "*", "index": "*",
            "hint": ["head"], "important": ["head"], "note": ["head"],
            "tip": ["head"], "warning": ["head"], "rubric": ["head"],
            "code-block": "*", "default": "*", "highlight": "*",
            "youtube": "*", "vimeo": "*", "peertube": "*"
        },
        "substdef": "*",
        "def": {"*": ["head"]}, "target": {"*": ["head"]},
        "doctest": "*",
        "standalone": "*",
        "grid-table": "*", "simple-table": "*"
    }

    punc_end_re = re_lib["puncend"][0]
    comma_re = re_lib["commaend"][0]
    space_re = re.compile(r"\S ")
    for part in rst_walker.iter_nodeparts_instr(document.body, instr_pos, instr_neg):
        if not part.parent_node.next:
            if part.parent_node.node_name == "text":
                part_str = str(part.code)
                if (not re.search(punc_end_re, part_str) and
                        (len(part_str.strip()) != 0 or
                         (part.parent_node.prev and
                          part.parent_node.prev.code.end_lincol[0] == part.code.start_lincol[0]))):
                    par_node = part.parent_node
                    while par_node.node_name == "text":
                        par_node = par_node.parent_node.parent_node

                    # refbox parts
                    if (rst_walker.is_of(par_node, "field",
                                         {"Shortcut", "Menu", "Panel", "Mode",
                                          "Tool", "Editor", "Header", "Type"})):
                        continue
                    if (rst_walker.is_of(part.next_leaf(), "dir", "default") and
                             not part_str.endswith(" ")):
                        continue
                    if not is_sentence(part, par_node, instr_pos, instr_neg, space_re):
                        continue
                    reports.append(
                        Report('W', toolname, part.code.copy().clear(False),
                               re_lib["puncend"][1][0].format("paragraph"))
                        .set_line_offset(document.body.code, 100, False))

                else:
                    if comma_m := re.search(comma_re, part_str):
                        reports.append(
                            Report('W', toolname, part.code.slice_match(comma_m, 0),
                                   re_lib["commaend"][1].format(
                                       rst_walker.write_out(part.parent_node.node_name) +
                                                            " " + part.node_name)))

        elif rst_walker.is_of(part, {"role", "hyperlink"}, "*", "head"):
            if re.search(punc_end_re, str(part.code)):
                reports.append(
                    Report('W', toolname, part.code.copy().clear(False),
                           re_lib["puncend"][1][1].format(
                               rst_walker.write_out(part.parent_node.node_name) +
                                                    " " + part.node_name)))

    return reports


def number_pre(_):
    part_of_speech = PartofSpeech()
    re_lib = dict()

    # FP: code, literal, Years
    start = r"(?:(?<=[^\d,.])|\A)"
    re_lib["digitsep"] = (re.compile(start + r"[\d,]*\d{4}"),
        Report.missing(what="separator", where="between four digits"))

    re_lib["digitsepless"] = (re.compile(start + r"\d,\d{1,2}\b"),
        Report.existing(what="separator", where="between less than four digits"))

    re_lib["digitsepzero"] = (re.compile(start + r"0,\d"),
        Report.existing(what="separator", where="after zero"))

    re_lib["digitspace"] = (re.compile(r"\d \d"),
        Report.existing(what="space", where="between digits"))

    written_out = r"\b" + r"\b|\b".join(part_of_speech.data["determiner"]["numeral"]["cardinal"])
    written_out += r"\b|" + r"\b|\b".join(part_of_speech.data["determiner"]["numeral"]["ordinal"])
    written_out += r"\b|" + r"\b|\b".join(("half", "halves", "thirds?"))
    re_lib["writtenoutspace"] = (
        re.compile(r"(?:" + written_out + r") (?:" + written_out + r")"),
        Report.missing(what="hyphen", where="between written-out numbers"))

    # FP: math, code
    re_lib["lowdigit"] = (
        re.compile(r"(?:(?<=\w )|^)([0-9]|1[0-2])(?:(?= \w)|$)", re.MULTILINE),
        Report.existing(what="low digit", where="in continuous text"))

    re_lib["nozero"] = (re.compile(start + r"\.\d"),
        Report.missing(what="zero", where="in front of a decimal point"))

    re_lib["zeronodot"] = (re.compile(start + r"0[1-9]"),
        Report.existing(what="zero", where="at number start"))

    re_lib["zerotrail"] = (re.compile(start + r"\d\.\d*0{2,}(?=\D|\Z)"),
        Report.existing(what="zeros", where="at number end"))

    re_lib["times"] = (re.compile(r"\d ?x( ?\d)?"),
        Report.option(what="x letter", with_what="times or × sign"))

    re_lib["range"] = (re.compile(r"\d\.\.+\d"),
        Report.option(what="range separator", with_what="to or dash"))

    re_lib["ratio"] = (re.compile(r"\d +:\d|\d: +\d"),
        Report.existing(what="space", where="around ratio separator"))

    re_lib["percentlimit"] = (re.compile(r"\D(?:0|100)%"),
        Report.option(what="percentage limits", with_what="written out no or fully"))

    # ------------------------------------------------------------------------

    re_lib["dimension"] = (re.compile(r"\b[0-9]d\b"),
        Report.misformatted(what="lowercase dimension letter"))

    re_lib["percent"] = (re.compile(r"\d [%‰‱]"),
        Report.existing(what="space", where="before percentage sign"))

    re_lib["degree"] = (re.compile(r"\d °(?! ?C\b)"),
        Report.existing(what="space", where="before degree sign"))

    re_lib["celsius"] = (re.compile(r"\d° ?C\b|° C\b"),
        Report.substitution(what="Celsius", with_what="°C"))

    re_lib["nospaceunit"] = (
        re.compile(r"\d(?!\W|\d|" + r'\b|'.join((
            'D', 'th', 'nd', 'st', 'rd', # math
            'px', 'p', 'bit', r'ki?', r'Mi?B', r'Gi?B', r'Ti?B' # digital
        )) + r"\b|\Z)"),
        Report.missing(what="space", where="before physics unit"))

    args = dict()
    args["re_lib"] = re_lib

    return args


def number(toolname, document, reports, re_lib):
    """Check for numbers and units formatting."""
    instr_pos = {
        "field": {"*": ["body"]},
        "*": {"*": ["head", "body"]}
    }
    instr_neg = {
        "dir": {
            "figure": ["head"],
            "code-block": "*", "default": "*", "youtube": "*", "vimeo": "*", "peertube": "*"
        },
        "substdef": {"image": ["head"], "unicode": "*", "replace": "*"},
        "comment": "*", "doctest": "*", "target": "*",
        "role": {"kbd": "*", "default": "*"},
        "literal": "*", "standalone": "*", "foot": "*", "cit": "*"
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

                reports.append(
                    Report('W', toolname, part.code.slice_match(m, 0), value[1])
                    .set_line_punc(document.body.code, 50, 30))

    return reports


def pairs_pre(toolname):
    args = dict()
    # FP/FN: s' closing
    # FP: cut heading line
    args["re_lib"] = {"pairchar": re.compile(r"[\(\[\{\)\]\}\]\"]|(?<!\w)'|(?<![sS])'(?!\w)")}

    # Max number of lines between the open and close mark.
    args["config"] = dict(monostyle_io.get_override(__file__, toolname, "max_line_span", 2))

    return args


def pairs(toolname, document, reports, re_lib, config):
    """Check if pairs of inline markup, brackets, quote marks are closed."""
    instr_pos = {
        "sect": {"*": ["name"]},
        "field": {"*": ["name", "body"]},
        "*": {"*": ["head", "body"]}
    }
    instr_neg = {
        "dir": {"code-block": "*", "default": "*", "math": "*",
                "youtube": "*", "vimeo": "*", "peertube": "*"},
        "substdef": {"unicode": "*", "replace": "*"},
        "comment": "*", "doctest": "*", "target": "*",
        "role": {"kbd": "*", "menuselection": "*", "math": "*", "default": "*"},
        "literal": "*", "standalone": "*"
    }

    max_line_span = config.get("max_line_span")
    stack = []
    pair_re = re_lib["pairchar"]
    pairs_map = {')': '(', ']': '[', '}': '{'}

    for part in rst_walker.iter_nodeparts_instr(document.body, instr_pos, instr_neg):
        part_str = str(part.code)
        for pair_m in re.finditer(pair_re, part_str):
            pair_char = part.code.slice_match(pair_m, 0)
            pair_char_str = pair_m.group(0)
            for index, entry in enumerate(reversed(stack)):
                if (entry[0] == pair_char_str or
                        (pair_char_str in pairs_map and entry[0] == pairs_map[pair_char_str])):

                    if (max_line_span is not None and
                            pair_char.start_lincol[0] - entry[1].start_lincol[0] > max_line_span):
                        reports.append(
                            Report('W', toolname, entry[1], "long span - {0},{1}"
                                   .format(pair_char.start_lincol[0] + 1,
                                           pair_char.start_lincol[1] + 1)))

                    # invert index
                    stack.pop(len(stack) - 1 - index)
                    break

            else:
                stack.append((pair_char_str, pair_char))

    if len(stack) != 0:
        for entry in stack:
            reports.append(Report('W', toolname, entry[1], "unclosed pairs"))

    if max_line_span is not None:
        for node in rst_walker.iter_node(document.body,
                                         ("literal", "strong", "emphasis", "int-target",
                                          "role", "hyperlink")):

            if not node.body_start or not node.body_end:
                # single word int-target or hyperlink
                continue

            if (node.body_start.code.end_lincol[0] - node.body_end.code.start_lincol[0] >
                    max_line_span):
                reports.append(
                    Report('W', toolname, node.body_start.code,
                           "long span - {0},{1}".format(
                                node.body_end.code.start_lincol[0] + 1,
                                node.body_end.code.start_lincol[1] + 1)))

            if node.body_start.code.end_pos == node.body_end.code.start_pos:
                reports.append(Report('W', toolname, node.code, "zero span"))

    return reports


def whitespace_pre(_):
    re_lib = dict()
    re_lib["tab"] = (re.compile(r"(\t)"), Report.existing(what="tab char"), "   ")

    re_lib["spaceeol"] = (re.compile(r"( +?)\n"),
        Report.existing(what="spaces", where="at line end"), "")

    # not match: indent at start, trailing at eol
    re_lib["multispace"] = (re.compile(r"\S(  +)(?:\S|\Z)"),
        Report.existing(what="multiple spaces", where="in text"), " ")

    # match: at start (when not line start), trailing at eol
    re_lib["multispacestart"] = (re.compile(r"\A(  +)(?:\S|\Z)"),
        Report.existing(what="multiple spaces", where="in text"), " ")

    args = dict()
    args["re_lib"] = re_lib

    return args


def whitespace(toolname, document, reports, re_lib):
    """Check whitespace chars."""
    text = str(document.code)
    for key, value in re_lib.items():
        if key in {"multispace", "multispacestart"}:
            continue
        pattern = value[0]
        for m in re.finditer(pattern, text):
            fix = document.body.code.slice_match(m, 1)
            fix.replace_over(value[2])
            reports.append(
                Report('W', toolname, document.body.code.slice_match(m, 0),
                       value[1], fix=fix)
                .set_line_punc(document.body.code, 50, 30))

    multi_start_re = re_lib["multispacestart"][0]
    multi_re = re_lib["multispace"][0]
    for node in rst_walker.iter_node(document.body, "text", leafs_only=True):
        is_cell = bool(rst_walker.is_of(node.parent_node.parent_node.parent_node, "cell"))

        node_str = str(node.code)
        if node.prev:
            if multi_start_m := re.match(multi_start_re, node_str):
                output = node.code.slice_match(multi_start_m, 1)
                reports.append(
                    Report('W', toolname, output, re_lib["multispacestart"][1],
                           fix=output.copy().replace_over(value[2]) if not is_cell else None)
                    .set_line_punc(document.body.code, 50, 30))

        for multi_m in re.finditer(multi_re, node_str):
            output = node.code.slice_match(multi_m, 1)
            reports.append(
                Report('W', toolname, output, re_lib["multispace"][1],
                       fix=output.copy().replace_over(value[2]) if not is_cell else None)
                .set_line_punc(document.body.code, 50, 30))

    return reports



OPS = (
    ("mark", mark, mark_pre, None),
    ("number", number, number_pre, None),
    ("pairs", pairs, pairs_pre, None),
    ("whitespace", whitespace, whitespace_pre, None)
)


if __name__ == "__main__":
    from monostyle.__main__ import main_mod
    main_mod(__doc__, OPS, __file__)
