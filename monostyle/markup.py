
"""
markup
~~~~~~

RST markup tools.
"""

import os
import re

import monostyle.util.monostylestd as monostylestd
from monostyle.util.monostylestd import Report
from monostyle.util.fragment import Fragment
from monostyle.rst_parser.core import RSTParser
import monostyle.rst_parser.walker as rst_walker


def heading_level(document, reports):
    """Heading hierarchy defined by the under/overline char."""
    toolname = "heading level"

    level_chars = ('%', '#', '*', '=', '-', '^', '"', "'")
    levels = {level_char: index for index, level_char in enumerate(level_chars)}
    title_count = 0
    level_prev = 0
    for node in rst_walker.iter_node(document.body, ("sect",), enter_pos=False):
        heading_char = node.name_end.code.content[0][0]

        level_cur = -1
        # get list index
        if heading_char in levels.keys():
            level_cur = levels[heading_char]

        if level_cur == -1:
            out = node.name_end.code.copy()
            out.content = node.name_end.code.content[0]
            msg = "unknown level: " + heading_char
            reports.append(Report('W', toolname, out, msg))

        elif level_cur <= 2:
            if level_cur == 0:

                if not document.code.fn.endswith("manual/index.rst"):
                    out = node.name_end.code.copy()
                    out.content = node.name_end.code.content[0]
                    msg = "main index char not on main" + heading_char
                    reports.append(Report('W', toolname, out, msg))

            elif level_cur == 1:
                if not document.code.fn.endswith("index.rst"):
                    out = node.name_end.code.copy()
                    out.content = node.name_end.code.content[0]
                    msg = "index title char on page" + heading_char
                    reports.append(Report('W', toolname, out, msg))

            elif document.code.fn.endswith("index.rst"):
                out = node.name_end.code.copy()
                out.content = heading_char
                msg = "page title char on index"
                reports.append(Report('W', toolname, out, msg))

            title_count += 1
            if title_count > 1:
                msg = "more than one title heading: " + str(title_count)
                out = node.name_end.code.copy()
                out.content = heading_char
                reports.append(Report('W', toolname, out, msg))

            level_prev = 2
        else:
            if title_count == 0:
                if document.body.code.start_lincol[0] == 0:
                    out = node.name_end.code.copy()
                    out.content = heading_char
                    msg = "no title heading"
                    reports.append(Report('W', toolname, out, msg))
                    # report only once
                    title_count = 1

            elif level_cur > level_prev + 1:
                msg = "wrong level: {0} > {1}  should be: {2}".format(level_chars[level_prev],
                          heading_char, level_chars[level_prev + 1])
                out = node.name_end.code.copy()
                out.content = node.name_end.code.content[0]
                reports.append(Report('W', toolname, out, msg))

            level_prev = level_cur

    return reports


def indention(document, reports):
    """Check RST code line indention."""
    toolname = "indention"

    default_indent = 3

    skip_linenos = []
    for node in rst_walker.iter_node(document.body):
        if rst_walker.is_of(node, "dir", ("code-block", "default")):
            if node.body.code.start_lincol[0] != node.body.code.end_lincol[0]:
                start = node.body.code.start_lincol[0]
                if node.code.start_lincol[0] == start:
                    start += 1
                skip_linenos.append(start)
                skip_linenos.append(node.body.code.end_lincol[0])

    code_on = False
    skip_index = 0

    stack_prev = []
    if document.code.start_lincol[0] == 0:
        stack_prev.append(0)
    stack_cur = []
    head = [r"(" + c + r")(" + c + r")" for c in ("#", "%")]
    block = [r"(" + c + r")( |\Z)" for c in map(re.escape, ("*", "-", "#.", "|", ".."))]
    block.append(r"(\:[^:]+\:)( +)")

    for line in document.body.code.splitlines():
        if len(skip_linenos) < skip_index and line.start_lincol[0] == skip_linenos[skip_index]:
            skip_index += 1
            code_on = not code_on

        if code_on:
            continue

        line_str = str(line)
        line_strip = line_str.lstrip(' \n')
        if len(line_strip) == 0:
            continue

        stack_cur.append(len(line) - len(line_strip))

        is_first_loop = True

        if len(line_strip) < 3:
            stack_cur.append(stack_cur[-1] + default_indent)

        while len(line_strip) > 3:
            matcher = block
            if is_first_loop:
                matcher = head.copy()
                matcher.extend(block)

            for match_char in matcher:
                if c_m := re.match(match_char, line_strip):
                    stack_cur.append(stack_cur[-1] + len(c_m[1]) + max(1, len(c_m[2])))
                    line_strip = line_strip[len(c_m[0]):]
                    break
            else:
                stack_cur.append(stack_cur[-1] + default_indent)
                break

            is_first_loop = False

        if (len(stack_prev) != 0 and stack_cur[0] not in stack_prev and
                stack_cur[0] > stack_prev[0]):
            msg = "wrong indent"
            msg += ": should be " + str(stack_prev[-1]) + " chars"
            if len(stack_prev) != 1:
                msg += " or " + str(stack_prev[-2]) + " chars"

            out = Fragment.from_org_len(document.code.fn, "", -1,
                                        start_lincol=(line.start_lincol[0],
                                                      stack_cur[0]))
            reports.append(Report('E', toolname, out, msg, line))

        if stack_cur[0] == 0:
            stack_prev.clear()
        else:
            for index, ent in enumerate(stack_prev):
                if ent >= stack_cur[0]:
                    stack_prev = stack_prev[:index]
                    break
        stack_prev.extend(stack_cur)
        stack_cur.clear()


    refbox_col = 15
    for node in rst_walker.iter_node(document.body, ("dir", "target")):
        if node.node_name == "target":
            next_node = node.next
            while (next_node and next_node.node_name == "text" and
                   next_node.code.isspace()):
                next_node = next_node.next
            if next_node:
                next_child = next_node.child_nodes.first()
                ind_trg_next = None
                if next_child:
                    if next_child.node_name == "indent":
                        next_child = next_child.next
                        if next_child:
                            ind_trg_next = next_child.code.start_lincol[1]
                    else:
                        ind_trg_next = len(re.match(r" *", next_child.code.content[0]).group(0))

                if (ind_trg_next is not None and
                        node.name_start.code.start_lincol[1] != ind_trg_next):
                    msg = "target not on same indent level"
                    reports.append(Report('W', toolname, node.id.code, msg))

        elif (rst_walker.is_of(node, "dir", "admonition") and
              str(rst_walker.get_attr(node, "class")).strip() == "refbox") and node.body:
            for node_field in rst_walker.iter_node(node.body, "field"):
                if node_field.name_end.code.end_lincol[1] != refbox_col:
                    msg = "ref-box wrong indent: should be {:+} chars".format(
                              refbox_col - node_field.name_end.code.end_lincol[1])
                    out = node_field.name_end.code.copy()
                    out.clear(False)
                    reports.append(Report('E', toolname, out, msg, line))

    return reports


def leak_pre():
    toolname = "leak"

    re_lib = dict()

    # BODY
    # Directive
    pattern_str = r"\:\:[A-Za-z\d_-]"
    pattern = re.compile(pattern_str)
    msg = "no space after directive"
    re_lib["dirend"] = (pattern, msg)

    pattern_str = r"\s\.\.[A-Za-z]"
    pattern = re.compile(pattern_str)
    msg = "no space in middle directive"
    re_lib["dirmid"] = (pattern, msg)

    # List
    pattern_str = r"^ *\-[A-Za-z]"
    pattern = re.compile(pattern_str)
    msg = "no space after unordered list"
    re_lib["unordend"] = (pattern, msg)

    pattern_str = r"^ *#\.[A-Za-z]"
    pattern = re.compile(pattern_str)
    msg = "no space after ordered list"
    re_lib["ordend"] = (pattern, msg)

    pattern_str = r"^( *)\b(?!(\-|\#\.) ).*\n" # capture indent, not list
    pattern_str += r"\1(\-|\#\.) " # same indent, list
    pattern = re.compile(pattern_str, re.MULTILINE)
    msg = "no empty line over list"
    re_lib["overlist"] = (pattern, msg)

    # INLINE
    # Literal, Strong, Emphasis
    # FP: list, code
    pattern_str = r"(?<=\s)(\*\*?|``?)\s[^\-]"
    pattern = re.compile(pattern_str)
    msg = "spaced inline markup"
    re_lib["spaceinline"] = (pattern, msg)

    # FP: target, math
    pattern_str = r"(?<=[A-Za-z])(\*\*?|``?)[A-Za-z]"
    pattern = re.compile(pattern_str)
    msg = "unspaced inline markup"
    re_lib["unspaceinline"] = (pattern, msg)

    # Role
    pattern_str = r"\w\:(?:[\w_-]+?)\:`"
    pattern = re.compile(pattern_str)
    msg = "no space before role"
    re_lib["rolestart"] = (pattern, msg)

    pattern_str = r"\:(?:[\w_-]+?)\:[ `\:]`"
    pattern = re.compile(pattern_str)
    msg = "spaced middle role"
    re_lib["rolemid"] = (pattern, msg)

    pattern_str = r"\:(?:[\w_-]+?)\:`[^`]+?`\w"
    pattern = re.compile(pattern_str)
    msg = "no space after role"
    re_lib["roleend"] = (pattern, msg)

    pattern_str = r"(\:[\w_-]+?[;,.|]`)|([;,.|][\w\-]+?\:`)"
    pattern = re.compile(pattern_str)
    msg = "wrong separator role"
    re_lib["rolesep"] = (pattern, msg)

    pattern_str = r"\:(?:doc|ref)\:`[\w\/ _&]+?[^ ]<[\w>\/ _]+?`"
    pattern = re.compile(pattern_str)
    msg = "no space after link title"
    re_lib["linkaddr"] = (pattern, msg)

    pattern_str = r"\:(?:abbr)\:`[\w\/ _&.]+?[^ ]\([\w _.]+?\)`"
    pattern = re.compile(pattern_str)
    msg = "no space after abbreviation title"
    re_lib["abbr"] = (pattern, msg)

    # internal links not starting with slash
    # -with title
    pattern_str = r"\:doc\:`[\w _]+?\/[\w_\/]+?`"
    pattern = re.compile(pattern_str)
    msg = "internal link no slash start"
    re_lib["inlinkstart"] = (pattern, msg)

    # -no title
    pattern_str = r"\:doc\:`[\w\/ _&]+?<\w"
    pattern = re.compile(pattern_str)
    msg = "internal link no slash start"
    re_lib["inlinkslash"] = (pattern, msg)

    # internal links ending with file extention
    pattern_str = r"\:doc\:`[^`]+?\.rst>?`"
    pattern = re.compile(pattern_str)
    msg = "internal link with file extention"
    re_lib["inlinkext"] = (pattern, msg)

    # internal links with title and no closing bracket
    pattern_str = r"\:doc\:`[^`]+? <[^`]*?[^>]`"
    pattern = re.compile(pattern_str)
    msg = "internal link no closing >"
    re_lib["inlinkclose"] = (pattern, msg)

    # Hyperlink
    pattern_str = r"[A-Za-z]_`[^`]"
    pattern = re.compile(pattern_str)
    msg = "no space before hyperlink"
    re_lib["loclinkstart"] = (pattern, msg)

    pattern_str = r"[^`]`__?[A-Za-z]"
    pattern = re.compile(pattern_str)
    msg = "no space after link"
    re_lib["linkend"] = (pattern, msg)

    pattern_str = r"https?\:\/\/[^`]+?>`(?!_)"
    pattern = re.compile(pattern_str)
    msg = "no underscore after external link"
    re_lib["exlinkend"] = (pattern, msg)

    # Substitution
    pattern_str = r"\w\|\w"
    pattern = re.compile(pattern_str)
    msg = "no space after substitution"
    re_lib["subst"] = (pattern, msg)

    pattern_str = r"[A-Za-z]_\|"
    pattern = re.compile(pattern_str)
    msg = "no space before substitution"
    re_lib["subststart"] = (pattern, msg)

    pattern_str = r"\|_[A-Za-z]"
    pattern = re.compile(pattern_str)
    msg = "no space after substitution"
    re_lib["substend"] = (pattern, msg)


    # Arrow
    pattern_str = r"[^ \-`]\-\->"
    pattern = re.compile(pattern_str)
    msg = "no space before arrow"
    re_lib["arrowstart"] = (pattern, msg)

    pattern_str = r"[^\-<]\->"
    pattern = re.compile(pattern_str)
    msg = "bad length arrow"
    re_lib["arrowlen"] = (pattern, msg)

    pattern_str = r"\->[^ `|]"
    pattern = re.compile(pattern_str)
    msg = "no space after arrow"
    re_lib["arrowend"] = (pattern, msg)

    # En-dash
    # min 1 letter in line to not match heading underline
    pattern_str = r"(\w.*([^\s\-]\-{2}[^\->]))|(([^\s\-]\-{2}[^\->]).*\w)"
    pattern = re.compile(pattern_str)
    msg = "no space before en-dash"
    re_lib["endashstart"] = (pattern, msg)

    # not match: arrow
    # FP: code, literal
    # min 1 letter in line to not match heading underline
    pattern_str = r"(\w.*\-{2}[^\s\->])|(\-{2}[^\s\->].*\w)"
    pattern = re.compile(pattern_str)
    msg = "no space after en-dash"
    re_lib["endashend"] = (pattern, msg)

    args = dict()
    args["re_lib"] = re_lib
    args["config"] = {"severity": 'E', "toolname": toolname}

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


def search_directive(document, reports):
    """Find unknown/uncommon roles and directives names."""
    toolname = "directive"


    roles = (
        'abbr', 'class', 'doc', 'download', 'guilabel', 'kbd', 'math',
        'menuselection', 'mod', 'ref', 'sub', 'sup', 'term'
    )

    directives = (
        # standard docutils ones
        #   admonition
        'admonition', 'hint', 'important', 'note', 'tip', 'warning',
        #    other
        'container', 'figure', 'image', 'include', 'list-table', 'parsed-literal',
        'replace', 'rubric', 'unicode', 'math',
        # Sphinx custom ones
        'code-block', 'glossary', 'highlight', 'only', 'seealso', 'toctree', 'hlist',
        # Sphinx extension
        'youtube', 'vimeo'
    )


    for node in rst_walker.iter_node(document.body, ("dir", "role", "block-quote")):
        if node.node_name == "role":
            if node.name:
                if str(node.name.code).strip() not in roles:
                    msg = "unknown/uncommon role"
                    reports.append(Report('E', toolname, node.name.code, msg))
            else:
                reports.append(Report('E', toolname, node.body.code, "default role"))

        elif node.node_name == "dir":
            name = str(node.name.code).strip() if node.name else node.name
            if name and name not in directives:
                msg = "unknown/uncommon directive"
                reports.append(Report('E', toolname, node.name.code, msg))

            if name == "raw":
                msg = "raw directive"
                reports.append(Report('E', toolname, node.name.code, msg))

        else:
            # not at diff hunk can be cut off def list
            if node.code.start_pos != document.code.start_pos:
                out = node.code.copy()
                out.clear(True)
                msg = "block quote"
                reports.append(Report('W', toolname, out, msg))

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
    ("directive", search_directive),
    ("heading-level", heading_level),
    ("indent", indention),
    ("leak", search_code, leak_pre)
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
                        help="defines the ROOT directory of the working copy or "
                             "if left empty the root defined in the config")

    args = parser.parse_args()

    if args.root is None:
        root_dir = os.getcwd()
    else:
        if len(args.root.strip()) == 0:
            root_dir = monostylestd.ROOT_DIR
        else:
            root_dir = os.path.normpath(args.root)

        if not os.path.exists(root_dir):
            print('Error: root {0} does not exists'.format(args.root))
            return 2

    root_dir = monostylestd.replace_windows_path_sep(root_dir)
    monostylestd.ROOT_DIR = root_dir

    reports = hub(args.op_names)
    monostylestd.print_reports(reports)


if __name__ == "__main__":
    main()
