
"""
code_style
~~~~~~~~~~

RST code style.
"""

import os
import re

import monostyle.util.monostylestd as monostylestd
from monostyle.util.report import Report, print_reports
from monostyle.util.fragment import Fragment
from monostyle.util.pos import PartofSpeech
from monostyle.util.char_catalog import CharCatalog
from monostyle.rst_parser.core import RSTParser
import monostyle.rst_parser.walker as rst_walker

POS = PartofSpeech()
CharCatalog = CharCatalog()


def eol_pre():
    """Note this tool can only be appplied on full files because the EOL is unknown in Diffs."""
    toolname = "EOF"

    re_lib = dict()
    pattern_str = r"\n{2}\Z"
    pattern = re.compile(pattern_str, re.MULTILINE)
    msg = "two+ lines at end of file"
    re_lib["trailingnl"] = (pattern, msg)

    pattern_str = r"(?<!\n)\Z"
    pattern = re.compile(pattern_str, re.MULTILINE)
    msg = "zero lines at end of file"
    re_lib["eofzero"] = (pattern, msg)

    args = dict()
    args["re_lib"] = re_lib
    args["config"] = {"severity": 'W', "toolname": toolname}

    return args


def search_code(document, reports, re_lib, config):
    """Iterate regex tools."""
    text = str(document.code)
    for pattern, msg in re_lib.values():
        for m in re.finditer(pattern, text):
            out = document.body.code.slice_match_obj(m, 0, True)
            line = monostylestd.getline_punc(document.body.code, m.start(),
                                             len(m.group(0)), 50, 0)

            reports.append(Report(config.get("severity"), config.get("toolname"),
                                  out, msg, line))

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
                out = node.name_start.code.copy()
                out.clear(True)
                msg = "too short/long horizontal line"
                reports.append(Report('W', toolname, out, msg))

            if node.name_start.code.content[0][0] != '-':
                out = node.name_start.code.copy()
                out.clear(True)
                msg = "bad char horizontal line"
                reports.append(Report('W', toolname, out, msg))

        if node.node_name in ("bullet", "enum"):
            if node.node_name == "bullet":
                if node.name_start.code.content[0][0] != '-':
                    par_node = node.parent_node.parent_node.parent_node.parent_node
                    if not rst_walker.is_of(par_node, "dir", "list-table"):
                        out = node.name_start.code.copy()
                        out.clear(True)
                        msg = "bad char bullet list"
                        reports.append(Report('W', toolname, out, msg))

            if (len(node.body.code) == 1 and
                    node.body.child_nodes.first().node_name == "text" and
                    is_nl_node(node.body.child_nodes.first())):
                out = node.name_start.code.copy()
                out.clear(True)
                msg = "empty list item without comment"
                reports.append(Report('W', toolname, out, msg))

        if node.node_name == "enum-list":
            first_node = node.body.child_nodes.first()
            if (str(first_node.name.code).strip() != "#" and
                    not rst_walker.is_of(node.parent_node, "dir", ("figure", "image"), "body")):

                out = first_node.name.code.copy()
                out.clear(True)
                msg = "not auto-named enumerated list"
                reports.append(Report('W', toolname, out, msg))

        if node.node_name == "text" and node.body.child_nodes.is_empty():
            node_content = str(node.body.code)
            for dash_m in re.finditer(dash_re, node_content):
                out = node.body.code.slice_match_obj(dash_m, 0, True)
                msg = "dash use en-dash instead"
                reports.append(Report('W', toolname, out, msg))

            for emdash_m in re.finditer(emdash_re, node_content):
                out = node.body.code.slice_match_obj(emdash_m, 0, True)
                msg = "em-dash use en-dash instead"
                reports.append(Report('W', toolname, out, msg))

    return reports


def line_style_pre():
    toolname = "linestyle"

    pare_close = CharCatalog.data["bracket"]["right"]["normal"]
    word_inter = CharCatalog.data["connector"]["hyphen"]
    word_inter += CharCatalog.data["connector"]["apostrophe"]

    re_lib = dict()
    pattern_str = (r"(?<=[", CharCatalog.data["terminal"]["final"], r"] )",
                   r"([\w" + word_inter + r"]+?)\n")
    pattern = re.compile(''.join(pattern_str), re.MULTILINE)
    msg = "first word of a sentence at line end"
    re_lib["sentorphan"] = (pattern, msg)

    # not match when oxford comma
    pattern_str = r"(?<!,)\b(?:and|or) ([\w" + word_inter + r"]+?)\n"
    pattern = re.compile(pattern_str, re.MULTILINE | re.IGNORECASE)
    msg = "first word of a clause at line end"
    re_lib["clauseorphan"] = (pattern, msg)

    pattern_str = (r"(\b[a-z][\w", CharCatalog.data["connector"]["apostrophe"], r"]*?)\n",
                   r"(?! *?[", pare_close, r"])")
    pattern = re.compile(''.join(pattern_str), re.MULTILINE)
    msg = "{0} at line end"
    re_lib["lastword"] = (pattern, msg)

    pattern_str = (r"(^[A-Za-z][\w", word_inter, r"]*?)",
                   r"(?=[", CharCatalog.data["terminal"]["final"], r"]\W)")
    pattern = re.compile(''.join(pattern_str), re.MULTILINE)
    msg = "last word of a sentence at line start"
    re_lib["sentwidow"] = (pattern, msg)

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
                msg = value[1]
                if is_lw:
                    path = POS.classify(str(m.group(1)))
                    if (len(path) != 0 and
                            (path[0] == "adjective" or
                             (path[0] == "determiner" and path[1] == "article"))):
                        msg = msg.format(path[-1])
                    else:
                        continue
                if m.start() == 0 and key == "sentwidow":
                    continue

                out = node.code.slice_match_obj(m, 0, True)
                line = monostylestd.getline_punc(node.code, m.start(),
                                                 len(m.group(0)), 50, 0)
                reports.append(Report(config.get("severity"), config.get("toolname"), out,
                                      msg, line, "reflow"))

    return reports


def long_line(document, reports):
    """Finds overly long lines."""
    toolname = "long line"
    limit = 118

    found_lineno = -1

    for part in rst_walker.iter_nodeparts(document.body):
        for line in part.code.splitlines():
            if line.end_lincol[1] > limit:
                par_node = part
                up_counter = 0
                while up_counter < 4 and par_node.parent_node:
                    par_node = par_node.parent_node
                    up_counter += 1

                if (up_counter == 4 and
                        (rst_walker.is_of(par_node, "*", ("figure", "image"), "head") or
                         rst_walker.is_of(par_node, "dir", "parsed-literal"))):
                    continue

                if part.parent_node.node_name == "text" and len(str(part.code).strip()) == 0:
                    continue

                if part.parent_node.node_name in ("hyperlink", "standalone"):
                    if (part.parent_node.id and
                            part.parent_node.id.code.span_len() + 4 > limit):
                        continue
                    if (part.parent_node.body and
                            part.parent_node.body.code.span_len() + 4 > limit):
                        continue

                if line.end_lincol[0] == found_lineno:
                    continue

                out = Fragment.from_org_len(document.code.fn, "", line.end_pos,
                                            start_lincol=line.end_lincol)
                msg = "long line"
                reports.append(Report('W', toolname, out, msg, line, "reflow"))
                found_lineno = line.end_lincol[0]

    return reports



def heading_lines(document, reports):
    """Heading over/underline char count and indent."""
    toolname = "heading char count"

    for node in rst_walker.iter_node(document.body, ("sect",), enter_pos=False):
        heading_char = node.name_end.code.content[0][0]
        if node.name.code.content[0][-2] == ' ':
            out = node.name.code.copy()
            out.clear(True)
            msg = "heading end space"
            reports.append(Report('W', toolname, out, msg))

        if heading_char in ('%', '#', '*'):
            if not node.name_start:
                out = node.name_end.code.copy()
                out.content = out.content[0][0]
                msg = "missing overline"
                reports.append(Report('W', toolname, out, msg))

        if heading_char in ('%', '#'):
            if len(node.name_end.code.content[0]) - 2 != len(node.name.code.content[0]):
                out = node.name_end.code.copy()
                out.content = out.content[0][0]
                msg = "wrong underline length: {:+}".format(
                          (len(node.name.code.content[0]) + 2) - len(node.name_end.code.content[0]))
                reports.append(Report('W', toolname, out, msg))

            if (node.name.code.content[0][0] != ' ' or node.name.code.content[0][1] != ' '
                    or node.name.code.content[0][3] == ' '):
                out = node.name.code.copy()
                out.clear(True)
                msg = "title indent too few/far"
                reports.append(Report('W', toolname, out, msg))

        else:
            if len(node.name_end.code.content[0]) != len(node.name.code.content[0]):
                out = node.name_end.code.copy()
                out.content = out.content[0][0]
                msg = "wrong underline length: {:+}".format(
                          len(node.name.code.content[0]) - len(node.name_end.code.content[0]))
                reports.append(Report('W', toolname, out, msg))

            if node.name.code.content[0][0] == ' ':
                out = node.name.code.copy()
                out.clear(True)
                msg = "indent too far"
                reports.append(Report('W', toolname, out, msg))

    return reports


def is_nl_node(node):
    """The node is empty or contains only whitespaces."""
    if node.node_name == "text":
        return node.code.isspace()
    return False


def newline(document, reports):
    """Newline markup formatting."""
    toolname = "newline"

    def count_trailnl(node, nl_count):
        newline_re = re.compile(r"\s*\Z", re.DOTALL)
        for line_str in reversed(node.code.content):
            if len(line_str) == 0:
                continue
            if newline_m := re.search(newline_re, line_str):
                nl_count += str(newline_m.group(0)).count('\n')

                if newline_m.start(0) != 0:
                    return nl_count, True
            else:
                return nl_count, True

        return nl_count, False


    def count_nl(node, stop_cond=None, skip_names=None):
        nl_count = 0
        over = False
        prev_node = node.prev
        while prev_node:
            nl_count, stop = count_trailnl(prev_node, nl_count)

            if stop:
                if skip_names and prev_node.node_name in skip_names:
                    if stop_cond is not None and nl_count >= stop_cond and not over:
                        return nl_count, prev_node, True

                else:
                    return nl_count, prev_node, False

                over = True
                nl_count = 0

            prev_node = prev_node.prev

        return nl_count, prev_node, False


    pos_over_heading = ("target", "comment", "substdef", "highlight")
    for node in rst_walker.iter_node(document.body):
        if node.node_name == "sect" or rst_walker.is_of(node, "dir", "rubric"):
            display_name = "heading" if node.node_name == "sect" else "rubric"
            if (node.node_name == "sect" and
                    node.name_end.code.content[0][0] in ('%', '#', '*')):
                cond_plain = 1
                msg_plain = "one line over title heading"
                cond_between = 2
                msg_between = msg_plain + "|"
                cond_over = 0
                msg_over = "no line over title heading"
            else:
                cond_plain = 3
                msg_plain = "two lines over " + display_name
                cond_between = 2
                msg_between = "one line over " + display_name
                cond_over = cond_plain
                msg_over = msg_plain + "|"

            nl_count, prev_node, go_on = count_nl(node, cond_plain, pos_over_heading)

            is_same = bool(prev_node and
                           (prev_node.node_name == "sect" or
                            rst_walker.is_of(prev_node, "dir", "rubric")))
            if not is_same and not go_on and nl_count != cond_plain:
                out = node.name.code.copy()
                msg = msg_plain + ": {:+}".format(cond_plain - nl_count)
                reports.append(Report('W', toolname, out, msg, node.name.code))

            if (is_same or go_on) and nl_count != cond_between:
                out = node.name.code.copy()
                msg = msg_between + ": {:+}".format(cond_between - nl_count)
                reports.append(Report('W', toolname, out, msg, node.name.code))

            if go_on:
                nl_count, prev_node, _ = count_nl(prev_node, skip_names=pos_over_heading)

                if (not prev_node or
                        not (prev_node.node_name == "sect" or
                             rst_walker.is_of(prev_node, "dir", "rubric"))):
                    if nl_count != cond_over:
                        out = node.name.code.copy()
                        msg = msg_over + ": {:+}".format(cond_over - nl_count)
                        reports.append(Report('W', toolname, out, msg, node.name.code))

                elif nl_count != cond_between:
                    out = node.name.code.copy()
                    msg = msg_between + ": {:+}".format(cond_between - nl_count)
                    reports.append(Report('W', toolname, out, msg, node.name.code))


        elif node.node_name in ("target", "comment"):
            cond_plain = 2
            msg = "no/one line over" + node.node_name
            nl_count, _, __ = count_nl(node, cond_plain)

            if nl_count > cond_plain:
                next_node = node.next
                while (next_node and
                       (next_node.node_name in ("target", "comment") or is_nl_node(next_node))):
                    next_node = next_node.next

                if not next_node or next_node.node_name not in ("sect", "rubric"):
                    msg += ": {:+}".format(cond_plain - nl_count)
                    out = node.code.copy()
                    out.clear(True)
                    reports.append(Report('W', toolname, out, msg, node.code))

        elif node.prev and not is_nl_node(node):
            if rst_walker.is_of(node, "dir",
                                ("admonition", "hint", "important", "note", "tip",
                                 "warning", "seealso", "code-block")):
                first_node = node.head.child_nodes.first()
                while first_node and not first_node.child_nodes.is_empty():
                    first_node = first_node.child_nodes.first()

                if first_node is not None and re.match(r"\n ", str(first_node.code)):
                    out = first_node.code.copy()
                    out.clear(True)
                    msg = "no line after head " + node.node_name + " "+ str(node.name.code)
                    reports.append(Report('W', toolname, out, msg))


            cond_plain = 2
            nl_count, _, __ = count_nl(node, cond_plain)

            if nl_count > cond_plain:
                msg = "one line over " + node.node_name
                if node.name:
                    msg += " " + str(node.name.code).strip()
                msg += ": {:+}".format(cond_plain - nl_count)
                out = node.code.copy()
                out.clear(True)
                reports.append(Report('W', toolname, out, msg))

    if is_nl_node(node):
        while node and not node.prev and node.parent_node:
            node = node.parent_node

        cond_plain = 2
        msg = "three+ empty lines"
        nl_count, _, __ = count_nl(node, cond_plain)

        if nl_count >= cond_plain:
            out = node.code.copy()
            out.clear(True)
            reports.append(Report('W', toolname, out, msg))

    return reports


def style_add(document, reports):
    """Check for additional markup style."""
    toolname = "styleadd"

    for node in rst_walker.iter_node(document.body):
        if node.node_name == "hyperlink":
            proto_re = re.compile(r"https?\:\/\/")
            if (re.match(proto_re, str(node.id.code)) and
                    not re.match(r"`__", str(node.body_end.code))):
                msg = "external link same tab"
                reports.append(Report('W', toolname, node.body.code, msg))

        if node.node_name == "target":
            next_node = node.next

            while next_node and (next_node.node_name == "target" or is_nl_node(next_node)):
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
                    msg = "figure ref. without prefix"
                    reports.append(Report('W', toolname, node.id.code, msg))
                else:
                    if not is_fig and str(node.id.code).lstrip().startswith("tab-") != is_tab:
                        msg = "table ref. without prefix"
                        reports.append(Report('W', toolname, node.id.code, msg))

    return reports



def init(op_names):
    ops = []
    if isinstance(op_names, str):
        op_names = [op_names]

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
            print("research: unknown operation: " + op_name)

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


OPS = (
    ("EOF", search_code, eol_pre),
    ("flavor", flavor),
    ("heading-char-count", heading_lines),
    ("line-style", line_style, line_style_pre),
    ("long-line", long_line),
    ("newline", newline),
    ("style-add", style_add)
)

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
