
"""
code_style
~~~~~~~~~~

RST code style.
"""

import re

from monostyle.util.report import Report, getline_punc
from monostyle.util.fragment import FragmentBundle
from monostyle.util.pos import PartofSpeech
from monostyle.util.char_catalog import CharCatalog
import monostyle.rst_parser.walker as rst_walker

POS = PartofSpeech()
CharCatalog = CharCatalog()


def eol_pre(_):
    """Note this tool can only be applied on full files because the EOL is unknown in Diffs."""
    toolname = "EOF"

    re_lib = dict()
    pattern_str = r"\n{2}\Z"
    pattern = re.compile(pattern_str, re.MULTILINE)
    message = Report.existing(what="two or more blank lines", where="at end of file")
    re_lib["trailingnl"] = (pattern, message)

    pattern_str = r"(?<!\n)\Z"
    pattern = re.compile(pattern_str, re.MULTILINE)
    message = Report.existing(what="zero blank lines", where="at end of file")
    re_lib["eofzero"] = (pattern, message)

    args = dict()
    args["re_lib"] = re_lib
    args["config"] = {"severity": 'W', "toolname": toolname}

    return args


def search_code(document, reports, re_lib, config):
    """Iterate regex tools."""
    text = str(document.code)
    for pattern, message in re_lib.values():
        for m in re.finditer(pattern, text):
            output = document.body.code.slice_match_obj(m, 0, True)
            line = getline_punc(document.body.code, m.start(), len(m.group(0)), 50, 0)
            reports.append(Report(config.get("severity"), config.get("toolname"),
                                  output, message, line))

    return reports


def flavor(document, reports):
    """Check if the preferred markup is used."""
    toolname = "flavor"

    dash_re = re.compile(r"(?:\D |\A)\-(?= \D|$|\Z)")
    emdash_re = re.compile(r"(?:[^-]|\A)\-{3}(?=[^-]|\Z)")

    for node in rst_walker.iter_node(document.body):
        if node.node_name == "trans":
            trans_len = len(str(node.name_start.code).strip())
            if trans_len < 12 and trans_len > 30:
                output = node.name_start.code.copy().clear(True)
                if trans_len < 12:
                    message = Report.under(what="dashes", where="in horizontal line")
                else:
                    message = Report.over(what="dashes", where="in horizontal line")

                reports.append(Report('W', toolname, output, message))

            if not str(node.name_start.code).startswith('-'):
                output = node.name_start.code.copy().clear(True)
                message = Report.misformatted(what="wrong char", where="horizontal line")
                reports.append(Report('W', toolname, output, message))

        if node.node_name in ("bullet", "enum"):
            if node.node_name == "bullet":
                if not str(node.name_start.code).startswith('-'):
                    par_node = node.parent_node.parent_node.parent_node.parent_node
                    if not rst_walker.is_of(par_node, "dir", "list-table"):
                        output = node.name_start.code.copy().clear(True)
                        message = Report.misformatted(what="wrong char", where="bullet list")
                        reports.append(Report('W', toolname, output, message))

            if (len(node.body.code) == 1 and
                    node.body.child_nodes.first().node_name == "text" and
                    is_blank_node(node.body.child_nodes.first())):
                output = node.name_start.code.copy().clear(True)
                message = Report.missing(what="empty comment", where="in empty list item")
                reports.append(Report('W', toolname, output, message))

        if node.node_name == "enum-list":
            first_node = node.body.child_nodes.first()
            if (str(first_node.name.code).strip() != "#" and
                    not rst_walker.is_of(node.parent_node, "dir", ("figure", "image"), "body")):
                output = first_node.name.code.copy().clear(True)
                message = Report.misformatted(what="not auto-named", where="enumerated list")
                reports.append(Report('W', toolname, output, message))

        if node.node_name == "text" and node.body.child_nodes.is_empty():
            node_content = str(node.body.code)
            for dash_m in re.finditer(dash_re, node_content):
                output = node.body.code.slice_match_obj(dash_m, 0, True)
                message = Report.substitution(what="dash", with_what="en-dash")
                reports.append(Report('W', toolname, output, message))

            for emdash_m in re.finditer(emdash_re, node_content):
                output = node.body.code.slice_match_obj(emdash_m, 0, True)
                message = Report.substitution(what="em-dash", with_what="en-dash")
                reports.append(Report('W', toolname, output, message))

    return reports


def line_style_pre(_):
    toolname = "linestyle"

    pare_close = CharCatalog.data["bracket"]["right"]["normal"]
    word_inter = CharCatalog.data["connector"]["hyphen"]
    word_inter += CharCatalog.data["connector"]["apostrophe"]

    re_lib = dict()
    pattern_str = (r"(?<=[", CharCatalog.data["terminal"]["final"], r"] )",
                   r"([\w" + word_inter + r"]+?)\n")
    pattern = re.compile(''.join(pattern_str), re.MULTILINE)
    message = Report.existing(what="first word of a sentence", where="at line end")
    re_lib["sentorphan"] = (pattern, message)

    # not match when oxford comma
    pattern_str = r"(?<!,)\b(?:and|or) ([\w" + word_inter + r"]+?)\n"
    pattern = re.compile(pattern_str, re.MULTILINE | re.IGNORECASE)
    message = Report.existing(what="first word of a clause", where="at line end")
    re_lib["clauseorphan"] = (pattern, message)

    pattern_str = (r"(\b[a-z][\w", CharCatalog.data["connector"]["apostrophe"], r"]*?)\n",
                   r"(?! *?[", pare_close, r"])")
    pattern = re.compile(''.join(pattern_str), re.MULTILINE)
    message = Report.existing(what="{0}", where="at line end")
    re_lib["lastword"] = (pattern, message)

    pattern_str = (r"(^[A-Za-z][\w", word_inter, r"]*?)",
                   r"(?=[", CharCatalog.data["terminal"]["final"], r"]\W)")
    pattern = re.compile(''.join(pattern_str), re.MULTILINE)
    message = Report.existing(what="last word of a sentence", where="at line start")
    re_lib["sentwidow"] = (pattern, message)

    args = dict()
    args["re_lib"] = re_lib
    args["config"] = {"severity": 'I', "toolname": toolname}

    return args


def line_style(document, reports, re_lib, config):
    """Check line wrapping."""
    for node in rst_walker.iter_node(document.body, ("text", "block-quote"), enter_pos=False):
        if node.parent_node.parent_node.node_name == "sect":
            continue

        text = str(node.code)
        for key, value in re_lib.items():
            is_lw = bool(key == "lastword")
            for m in re.finditer(value[0], text):
                message = value[1]
                if is_lw:
                    path = POS.tag(str(m.group(1).lower()))
                    if (len(path) != 0 and
                            (path[0] == "adjective" or
                             (path[0] == "determiner" and path[1] == "article"))):
                        message = message.format(path[-1])
                    else:
                        continue
                if m.start() == 0 and key == "sentwidow":
                    continue

                output = node.code.slice_match_obj(m, 0, True)
                line = getline_punc(node.code, output.start_pos,
                                    output.span_len(True), 50, 0)
                reports.append(Report(config.get("severity"), config.get("toolname"), output,
                                      message, line, "reflow"))

    return reports


def long_line(document, reports):
    """Finds overly long lines."""
    toolname = "long-line"
    limit = 118

    instr_pos = {
        "*": "*"
    }
    instr_neg = {
        "dir": {
            "figure": ["head"], "include": ["head"], "parsed-literal": "*",
            "code-block": "*", "default": "*",
        },
        "substdef": {"image": ["head"]},
        "doctest": "*",
    }
    line = None
    for part in rst_walker.iter_nodeparts_instr(document.body, instr_pos, instr_neg):
        is_last = bool(not part.parent_node.next and not part.next_leaf())
        for buf in part.code.splitlines(buffered=True):
            if (line and ((buf and buf.end_lincol[0] != line.end_lincol[0]) or
                          (not buf and is_last))):
                if line.end_lincol[1] > limit:
                    if rst_walker.is_of(part, "text") and re.match(r".?\n", str(line)):
                        prev_node = part.parent_node.prev
                        if prev_node and prev_node.code.end_lincol[0] == part.code.start_lincol[0]:
                            if prev_node.node_name in ("hyperlink", "standalone", "role"):
                                if (prev_node.id and
                                        prev_node.id.code.span_len(True) + 4 > limit):
                                    line = None
                                    continue
                                if (prev_node.body and
                                        prev_node.body.code.span_len(True) + 4 > limit):
                                    line = None
                                    continue

                    output = line.copy().clear(False)
                    message = "long line"
                    reports.append(Report('W', toolname, output, message, line, "reflow"))

            if buf or is_last:
                line = buf

    return reports


def heading_lines(document, reports):
    """Heading over/underline char count and indent."""
    toolname = "heading-line-length"

    for node in rst_walker.iter_node(document.body, ("sect",), enter_pos=False):
        heading_char = str(node.name_end.code)[0]
        ind = 0 if heading_char not in {'%', '#'} else 2
        title_len = len(str(node.name.code).strip()) + ind * 2

        if heading_char in {'%', '#', '*'} and not node.name_start:
            output = node.name_end.code.copy().replace_fill(heading_char)
            message = Report.missing(what="overline")
            fg_repl = node.name.code.copy().replace_fill([heading_char * title_len + "\n"])
            fg_repl = fg_repl.clear(True)
            reports.append(Report('W', toolname, output, message, fix=fg_repl))

        if (len(str(node.name_end.code).strip()) != title_len or
                (node.name_start and
                 len(str(node.name_start.code).strip()) != title_len)):
            output = node.name_end.code.copy().replace_fill(heading_char)
            if len(str(node.name_end.code).strip()) != title_len:
                message = Report.quantity(what="wrong underline length",
                                          how=": {:+}".format(
                                              title_len - len(str(node.name_end.code).strip())))
            else:
                message = Report.quantity(what="wrong overline length",
                                          how=": {:+}".format(
                                              title_len - len(str(node.name_start.code).strip())))

            bd = FragmentBundle()
            if node.name_start:
                lineno = node.name_start.code.start_lincol[0]
                fg_repl_over = node.name_start.code.slice((lineno, 0), (lineno + 1, 0), True)
                fg_repl_over = fg_repl_over.to_fragment()
                fg_repl_over.replace_fill([heading_char * title_len + "\n"])
                bd.bundle.append(fg_repl_over)
            lineno = node.name_end.code.start_lincol[0]
            fg_repl_under = node.name_end.code.slice((lineno, 0), (lineno + 1, 0), True)
            fg_repl_under = fg_repl_under.to_fragment()
            fg_repl_under.replace_fill([heading_char * title_len + "\n"])
            bd.bundle.append(fg_repl_under)
            reports.append(Report('W', toolname, output, message, fix=bd))

        titel_ind_m = re.match(r" *", str(node.name.code))
        if titel_ind_m and len(titel_ind_m.group(0)) != ind:
            output = node.name.code.copy().clear(True)
            message = Report.quantity(what="wrong title indent",
                                      how=": {:+}".format(ind - len(titel_ind_m.group(0))))

            fg_repl = node.name.code.slice_match_obj(titel_ind_m, 0, True)
            fg_repl.replace_fill([" " * ind])
            reports.append(Report('W', toolname, output, message, fix=fg_repl))

    return reports


def is_blank_node(node):
    """The node is empty or contains only whitespaces."""
    if node.node_name == "text":
        return node.code.isspace()
    return False


def blank_line(document, reports):
    """Blank line markup formatting."""
    toolname = "blank-line"

    def count_trailnl(node, nl_count):
        newline_re = re.compile(r"\s*\Z", re.DOTALL)
        for line in node.code.reversed_splitlines():
            if line.span_len(True) == 0:
                continue
            if newline_m := re.search(newline_re, str(line)):
                nl_count += str(newline_m.group(0)).count('\n')

                if newline_m.start(0) != 0:
                    return nl_count, True
            else:
                return nl_count, True

        return nl_count, False


    def count_nl(node, stop_cond=None, skip_names=None):
        if skip_names is None:
            skip_names = tuple()
        nl_count = 0
        over = False
        prev_node = node.prev
        while prev_node:
            nl_count, stop = count_trailnl(prev_node, nl_count)

            if stop:
                for typ in skip_names:
                    if rst_walker.is_of(prev_node, *typ):
                        if stop_cond is not None and nl_count >= stop_cond and not over:
                            return nl_count, prev_node, True
                        break
                else:
                    return nl_count, prev_node, False

                over = True
                nl_count = 0

            prev_node = prev_node.prev

        return nl_count, prev_node, False


    pos_over_heading = (("target",), ("comment",), ("substdef",),
                        ("dir", "highlight"), ("dir", "index"))
    for node in rst_walker.iter_node(document.body):
        if node.node_name == "sect" or rst_walker.is_of(node, "dir", "rubric"):
            display_name = "heading" if node.node_name == "sect" else "rubric"
            if (node.node_name == "sect" and
                    str(node.name_end.code)[0] in {'%', '#', '*'}):
                cond_plain = 1
                message_plain = Report.quantity(what="one blank line", where="over title heading")
                cond_between = 2
                message_between = message_plain
                cond_over = 0
                message_over = Report.missing(what="blank line", where="over title heading")
            else:
                cond_plain = 3
                message_plain = Report.quantity(what="two blank line", where="over " + display_name)
                cond_between = 2
                message_between = Report.quantity(what="one blank line",
                                                  where="over " + display_name)
                cond_over = cond_plain
                message_over = message_plain

            nl_count, prev_node, go_on = count_nl(node, cond_plain, pos_over_heading)

            is_same = bool(prev_node and
                           (prev_node.node_name == "sect" or
                            rst_walker.is_of(prev_node, "dir", "rubric")))
            if not is_same and not go_on and nl_count != cond_plain:
                output = node.name.code.copy()
                message = message_plain + ": {:+}".format(cond_plain - nl_count)
                reports.append(Report('W', toolname, output, message, node.name.code))

            if (is_same or go_on) and nl_count != cond_between:
                output = node.name.code.copy()
                message = message_between + ": {:+}".format(cond_between - nl_count)
                reports.append(Report('W', toolname, output, message, node.name.code))

            if go_on:
                nl_count, prev_node, _ = count_nl(prev_node, skip_names=pos_over_heading)

                if (not prev_node or
                        not (prev_node.node_name == "sect" or
                             rst_walker.is_of(prev_node, "dir", "rubric"))):
                    if nl_count != cond_over:
                        output = node.name.code.copy()
                        message = message_over + ": {:+}".format(cond_over - nl_count)
                        reports.append(Report('W', toolname, output, message, node.name.code))

                elif nl_count != cond_between:
                    output = node.name.code.copy()
                    message = message_between + ": {:+}".format(cond_between - nl_count)
                    reports.append(Report('W', toolname, output, message, node.name.code))


        elif node.node_name in ("target", "comment"):
            cond_plain = 2
            message = Report.quantity(what="one blank line", where="over " + node.node_name)
            nl_count, _, __ = count_nl(node, cond_plain)

            if nl_count > cond_plain:
                next_node = node.next
                while (next_node and
                       (next_node.node_name in ("target", "comment") or
                        is_blank_node(next_node))):
                    next_node = next_node.next

                if not next_node or next_node.node_name not in ("sect", "rubric"):
                    message += ": {:+}".format(cond_plain - nl_count)
                    output = node.code.copy().clear(True)
                    reports.append(Report('W', toolname, output, message, node.code))

        elif node.prev and not is_blank_node(node):
            if rst_walker.is_of(node, "dir",
                                ("admonition", "hint", "important", "note", "tip",
                                 "warning", "seealso", "code-block")):

                if node.head is not None and re.match(r"\n ", str(node.head.code)):
                    output = node.head.code.copy().clear(True)
                    message = Report.missing(what="blank line",
                                             where="after head " + node.node_name +
                                                   " " + str(node.name.code))
                    reports.append(Report('W', toolname, output, message))


            cond_plain = 2
            nl_count, _, __ = count_nl(node, cond_plain)

            if nl_count > cond_plain:
                naming = node.node_name
                if node.name:
                    naming += " " + str(node.name.code).strip()
                message = Report.quantity(what="one blank line", where="over " + naming,
                                          how=": {:+}".format(cond_plain - nl_count))
                output = node.code.copy().clear(True)
                reports.append(Report('W', toolname, output, message))

    if is_blank_node(node):
        while node and not node.prev and node.parent_node:
            node = node.parent_node

        cond_plain = 2
        message = Report.quantity(what="three or more blank lines")
        nl_count, _, __ = count_nl(node, cond_plain)

        if nl_count >= cond_plain:
            output = node.code.copy().clear(True)
            reports.append(Report('W', toolname, output, message))

    return reports


def style_add(document, reports):
    """Check for additional markup style."""
    toolname = "styleadd"

    for node in rst_walker.iter_node(document.body):
        if node.node_name == "hyperlink":
            proto_re = re.compile(r"https?\:\/\/")
            if (re.match(proto_re, str(node.id.code)) and
                    not re.match(r"`__", str(node.body_end.code))):
                message = Report.missing(what="underscore", where="after external link (same tab)")
                fg_repl = node.body_end.code.copy().clear(True).replace("_")
                reports.append(Report('W', toolname, node.id.code, message, fix=fg_repl))

        if node.node_name == "target":
            next_node = node.next

            while next_node and (next_node.node_name == "target" or is_blank_node(next_node)):
                next_node = next_node.next

            if rst_walker.is_of(next_node, "dir", ("figure", "image", "list-table")):
                is_tab = False
                if rst_walker.is_of(next_node, "*", "list-table"):
                    is_tab = True
                    first_node = None
                    if next_node.body:
                        first_node = next_node.body.child_nodes.first()
                        while first_node and first_node.node_name in ("bullet", "bullet-list"):
                            if first_node.body.child_nodes.is_empty():
                                break
                            first_node = first_node.body.child_nodes.first()

                    is_fig = bool(rst_walker.is_of(first_node, "dir", ("figure", "image")))
                else:
                    is_fig = True

                if str(node.id.code).lstrip().startswith("fig-") != is_fig:
                    message = Report.missing(what="'fig-' prefix", where="at start of figure ref.")
                    reports.append(Report('W', toolname, node.id.code, message))
                else:
                    if not is_fig and str(node.id.code).lstrip().startswith("tab-") != is_tab:
                        message = Report.missing(what="'tab-' prefix",
                                                 where="at start of table ref.")
                        reports.append(Report('W', toolname, node.id.code, message))

    return reports


OPS = (
    ("blank-line", blank_line, None),
    ("EOF", search_code, eol_pre),
    ("flavor", flavor, None),
    ("heading-line-length", heading_lines, None),
    ("line-style", line_style, line_style_pre),
    ("long-line", long_line, None),
    ("style-add", style_add, None)
)


if __name__ == "__main__":
    from monostyle.cmd import main
    main(OPS, __doc__, __file__)
