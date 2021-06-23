
"""
code_style
~~~~~~~~~~

RST code style.
"""

import re

from monostyle.util.report import Report
from monostyle.util.fragment import FragmentBundle
from monostyle.util.part_of_speech import PartofSpeech
from monostyle.util.char_catalog import CharCatalog
import monostyle.rst_parser.walker as rst_walker


def is_blank_node(node):
    """The node is empty or contains only whitespaces."""
    if node.node_name == "text":
        return node.code.isspace()
    return False


def blank_line(toolname, document, reports):
    """Blank line markup formatting."""

    def counter(node, skip=False, stop_cond=None, invert=False):
        count = 0
        node_walk = node.prev if not invert else node
        while node_walk:
            was_space = False
            for line in node_walk.code.reversed_splitlines():
                if len(line) == 0:
                    continue
                if line.start_lincol[1] == 0 and line.isspace():
                    count +=1
                else:
                    break
            else:
                was_space = True

            if stop_cond and count >= stop_cond:
                if invert:
                    node_walk = node_walk.next
                return count, node_walk, True

            if not was_space:
                if skip and skip_over_sect(node_walk):
                    count = 0
                else:
                    break

            node_walk = node_walk.prev if not invert else node_walk.next

        return count, node_walk, False

    def skip_over_sect(node):
        if not node:
            return False
        if node.node_name == "field-list":
            # Sphinx special metafields; check only first, flags only
            node = node.body.child_nodes.first()
            return bool(str(node.name.code) in {"tocdepth", "nocomments", "orphan", "nosearch"} and
                        node.body.code.isspace())

        for typ in (("target",), ("comment",), ("substdef",),
                    ("dir", "highlight"), ("dir", "index")):
            if rst_walker.is_of(node, *typ):
                return True

        return False

    def is_sect(node):
        return bool(node and (node.node_name == "sect" or
                              rst_walker.is_of(node, "dir", "rubric")))

    prime = None
    for node in rst_walker.iter_node(document.body):
        if is_blank_node(node) or not node.indent:
            continue

        aim = 1 if node.prev else 0
        aim_alt = None
        output_node = None
        is_between = False

        count, node_over, __ = counter(node)

        is_proxy = False
        if skip_over_sect(node):
            if skip_over_sect(node_over):
                aim_alt = 0

            _, node_under, __ = counter(node, True, invert=True)
            if node_under and node_under is not prime and is_sect(node_under):
                prime = node_under
                is_proxy = True
                if node.node_name == "comment" and not is_sect(node_over):
                    # find shorter span
                    _, node_under, stopped = counter(node, True, stop_cond=2, invert=True)
                    if node_under is not prime or stopped:
                        prime = None
                        is_proxy = False

        else:
            if node.parent_node:
                if (node.parent_node.parent_node.node_name.endswith("-list") or
                        node.parent_node.parent_node.node_name.endswith("-table")):
                    aim_alt = 0

                elif (node.parent_node.parent_node.node_name in {"field", "substdef"} and
                        node.prev and not node.prev.prev):
                    # hanging
                    aim_alt = 0

                elif rst_walker.is_of(node, "dir", "include"):
                    aim_alt = 0

                elif (rst_walker.is_of(node, "dir", {"figure", "image"}) and
                        rst_walker.is_of(node_over, "dir", {"figure", "image"}) and
                        not node_over.body and
                        (not node.body or node.body.code.isspace())):
                    aim_alt = 0

        if is_proxy or (node is not prime and is_sect(node)):
            if not prime:
                prime = node
            if (prime.node_name == "sect" and
                    str(prime.name_end.code)[0] in {'%', '#', '*'}):
                aim = 1 if node is prime else 0
            else:
                aim = 2

            if node_over and is_sect(node_over):
                aim = 1
                is_between = True

            if not is_proxy:
                output_node = prime.name if prime.node_name == "sect" else prime.head

        if node is prime:
            prime = None

        if count != aim and count != aim_alt:
            if aim_alt is not None and abs(aim - count) > abs(aim_alt - count):
                aim = aim_alt
            output = output_node.code if output_node else node.code.copy().clear(True)
            message = Report.quantity(what=Report.write_out_quantity(aim, "blank line"),
                                      where=(("over " if not is_between else "between ") +
                                            rst_walker.write_out(node.node_name, node.name)))
            message += ": {:+}".format(aim - count)

            fix = None
            if (rst_walker.is_of(node.parent_node, "dir",
                                {"admonition", "hint", "important", "note", "tip",
                                 "warning", "seealso", "code-block"}, "head") and
                 node.parent_node.code.start_lincol[0] - node.code.start_lincol[0] < 2):

                fix = node.parent_node.code.copy().clear(True).replace('\n')
            reports.append(Report('W', toolname, output, message, node.code, fix))

    count_end, _, __ = counter(node, invert=True)
    if count_end >= 3:
        output = node.code.copy().clear(True)
        message = Report.quantity(what="three or more blank lines")
        reports.append(Report('W', toolname, output, message))

    return reports


def flavor(toolname, document, reports):
    """Check if the preferred markup is used."""

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

        if node.node_name in {"bullet", "enum"}:
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
                    not rst_walker.is_of(node.parent_node, "dir", {"figure", "image"}, "body")):
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


def heading_lines(toolname, document, reports):
    """Heading over/underline char count and indent."""

    for node in rst_walker.iter_node(document.body, "sect", enter_pos=False):
        heading_char = str(node.name_end.code)[0]
        ind = 0 if heading_char not in {'%', '#'} else 2
        title_len = len(str(node.name.code).strip()) + ind * 2

        if heading_char in {'%', '#', '*'} and not node.name_start:
            output = node.name_end.code.copy().replace_fill(heading_char)
            message = Report.missing(what="overline")
            fix = node.name.code.copy().replace_fill([heading_char * title_len + "\n"])
            fix = fix.clear(True)
            reports.append(Report('W', toolname, output, message, fix=fix))

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

            fix = FragmentBundle()
            if node.name_start:
                lineno = node.name_start.code.start_lincol[0]
                fix_over = node.name_start.code.slice((lineno, 0), (lineno + 1, 0), True)
                fix_over.replace_fill([heading_char * title_len + "\n"])
                fix.combine(fix_over)
            lineno = node.name_end.code.start_lincol[0]
            fix_under = node.name_end.code.slice((lineno, 0), (lineno + 1, 0), True)
            fix_under.replace_fill([heading_char * title_len + "\n"])
            fix.combine(fix_under)
            reports.append(Report('W', toolname, output, message, fix=fix))

        title_ind_m = re.match(r" *", str(node.name.code))
        if title_ind_m and len(title_ind_m.group(0)) != ind:
            output = node.name.code.copy().clear(True)
            message = Report.quantity(what="wrong title indent",
                                      how=": {:+}".format(ind - len(title_ind_m.group(0))))

            fix = node.name.code.slice_match_obj(title_ind_m, 0, True)
            fix.replace_fill([" " * ind])
            reports.append(Report('W', toolname, output, message, fix=fix))

    return reports


def line_style_pre(_):
    char_catalog = CharCatalog()

    pare_close = char_catalog.data["bracket"]["right"]["normal"]
    word_inter = char_catalog.data["connector"]["hyphen"]
    word_inter += char_catalog.data["connector"]["apostrophe"]

    re_lib = dict()
    eol = r"\s*$"
    re_lib["sentorphan"] = (
        re.compile(''.join((r"(?<=[", char_catalog.data["terminal"]["final"], r"] )",
                   r"([\w" + word_inter + r"]+?)", eol)), re.MULTILINE),
        Report.existing(what="first word of a sentence", where="at line end"))

    # not match when oxford comma
    re_lib["clauseorphan"] = (
        re.compile(r"(?<!,)\b(?:and|or) ([\w" + word_inter + r"]+?)" + eol,
                   re.MULTILINE | re.IGNORECASE),
        Report.existing(what="first word of a clause", where="at line end"))

    re_lib["lastword"] = (
        re.compile(''.join((r"(\b[a-z][\w", char_catalog.data["connector"]["apostrophe"],
                            r"]*?)", eol, r"(?! *?[", pare_close, r"])")), re.MULTILINE),
        Report.existing(what="{0}", where="at line end"))

    re_lib["sentwidow"] = (
        re.compile(''.join((r"(^[A-Za-z][\w", word_inter, r"]*?)",
                            r"(?=[", char_catalog.data["terminal"]["final"], r"]\W)")),
                   re.MULTILINE),
        Report.existing(what="last word of a sentence", where="at line start"))

    args = dict()
    args["re_lib"] = re_lib

    return args


def line_style(toolname, document, reports, re_lib):
    """Check line wrapping."""
    part_of_speech = PartofSpeech()

    for node in rst_walker.iter_node(document.body, {"text", "block-quote"}, enter_pos=False):
        if (rst_walker.is_of(node.parent_node, "sect") or
                rst_walker.is_of(node.parent_node, "def", "*", "head")):
            continue

        text = str(node.code)
        for key, value in re_lib.items():
            is_lastword = bool(key == "lastword")
            for m in re.finditer(value[0], text):
                message = value[1]
                if is_lastword:
                    tag = part_of_speech.tag(str(m.group(1).lower()))
                    if (len(tag) != 0 and
                            (tag[0] == "adjective" or
                             (tag[0] == "determiner" and tag[1] == "article"))):
                        message = message.format(tag[-1])
                    else:
                        continue
                if m.start() == 0 and (key == "sentwidow" or is_lastword):
                    continue

                output = node.code.slice_match_obj(m, 0, True)
                line = Report.getline_offset(node.code, output, 100)
                reports.append(Report('I', toolname, output, message, line, "reflow"))

    return reports


def long_line(toolname, document, reports):
    """Finds overly long lines."""
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
                            if prev_node.node_name in {"hyperlink", "standalone", "role"}:
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


def style_extra(toolname, document, reports):
    """Check for additional markup style."""

    for node in rst_walker.iter_node(document.body):
        if node.node_name == "hyperlink":
            if (re.match(r"https?\:\/\/", str(node.id.code)) and
                    not re.match(r"`__", str(node.body_end.code))):
                message = Report.missing(what="underscore", where="after external link (same tab)")
                fix = node.body_end.code.copy().clear(True).replace("_")
                reports.append(Report('W', toolname, node.id.code, message, fix=fix))

        elif node.node_name == "target":
            next_node = node.next

            while next_node and (next_node.node_name == "target" or is_blank_node(next_node)):
                next_node = next_node.next

            if rst_walker.is_of(next_node, "dir", {"figure", "image", "list-table"}):
                is_tab = False
                if rst_walker.is_of(next_node, "*", "list-table"):
                    is_tab = True
                    first_node = None
                    if next_node.body:
                        first_node = next_node.body.child_nodes.first()
                        while first_node and first_node.node_name in {"bullet", "bullet-list"}:
                            if first_node.body.child_nodes.is_empty():
                                break
                            first_node = first_node.body.child_nodes.first()

                    is_fig = bool(rst_walker.is_of(first_node, "dir", {"figure", "image"}))
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

        elif rst_walker.is_of(node, "role", "menuselection"):
            dash_re = re.compile(r"(?:\A| )(\-{1,3}|\->|\-{3}>)(?: |\Z)")
            node_str = str(node.body.code)
            for dash_m in re.finditer(dash_re, node_str):
                if '>' not in dash_m.group(1):
                    message = Report.missing(what="arrow peak" ,
                                             where="in " + rst_walker.write_out(node.node_name,
                                                                                node.name))
                else:
                    message = Report.misformatted(what="arrow length" ,
                                             where="in " + rst_walker.write_out(node.node_name,
                                                                                node.name))
                fix = node.body.code.slice_match_obj(dash_m, 1, True).replace("-->")
                reports.append(Report('W', toolname, node.body.code, message, fix=fix))

    return reports


OPS = (
    ("blank-line", blank_line, None),
    ("flavor", flavor, None),
    ("heading-line-length", heading_lines, None),
    ("line-style", line_style, line_style_pre),
    ("long-line", long_line, None),
    ("style-extra", style_extra, None)
)


if __name__ == "__main__":
    from monostyle.__main__ import main_mod
    main_mod(__doc__, OPS, __file__)
