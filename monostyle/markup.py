
"""
markup
~~~~~~

RST markup tools.
"""

import os
import re

import monostyle.util.monostylestd as monostylestd
from monostyle.util.report import Report, print_reports
from monostyle.util.fragment import Fragment
from monostyle.rst_parser.core import RSTParser
import monostyle.rst_parser.walker as rst_walker


def heading_level(document, reports):
    """Heading hierarchy defined by the under/overline char."""
    toolname = "heading-level"

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
            msg = Report.existing(what="unknown level: " + heading_char)
            reports.append(Report('W', toolname, out, msg))

        elif level_cur <= 2:
            if level_cur == 0:

                if not document.code.fn.endswith("manual/index.rst"):
                    out = node.name_end.code.copy()
                    out.content = node.name_end.code.content[0]
                    msg = Report.existing(what="main index title: " + heading_char,
                                          where="not on main")
                    reports.append(Report('W', toolname, out, msg))

            elif level_cur == 1:
                if not document.code.fn.endswith("index.rst"):
                    out = node.name_end.code.copy()
                    out.content = node.name_end.code.content[0]
                    msg = Report.existing(what="index title: " + heading_char,
                                          where="on page")
                    reports.append(Report('W', toolname, out, msg))

            elif document.code.fn.endswith("index.rst"):
                out = node.name_end.code.copy()
                out.content = heading_char
                msg = Report.existing(what="page title", where="on index")
                reports.append(Report('W', toolname, out, msg))

            title_count += 1
            if title_count > 1:
                msg = Report.over(what="title headings: " + str(title_count))
                out = node.name_end.code.copy()
                out.content = heading_char
                reports.append(Report('W', toolname, out, msg))

            level_prev = 2
        else:
            if title_count == 0:
                if document.body.code.start_lincol[0] == 0:
                    out = node.name_end.code.copy()
                    out.content = heading_char
                    msg = Report.missing(what="title heading")
                    reports.append(Report('W', toolname, out, msg))
                    # report only once
                    title_count = 1

            elif level_cur > level_prev + 1:
                msg = Report.substitution(what="wrong level: {0} > {1}".format(
                                          level_chars[level_prev], heading_char),
                                          with_what=level_chars[level_prev + 1])

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

            with_what = str(stack_prev[-1]) + " chars"
            if len(stack_prev) != 1:
                with_what += " or " + str(stack_prev[-2]) + " chars"
            msg = Report.substitution(what="wrong indent", with_what=with_what)
            out = Fragment(document.code.fn, "", -1,
                           start_lincol=(line.start_lincol[0], stack_cur[0]))
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
                    msg = Report.existing(what="target", where="not on same indent level")
                    reports.append(Report('W', toolname, node.id.code, msg))

        elif (rst_walker.is_of(node, "dir", "admonition") and
              str(rst_walker.get_attr(node, "class")).strip() == "refbox") and node.body:
            for node_field in rst_walker.iter_node(node.body, "field"):
                if node_field.name_end.code.end_lincol[1] != refbox_col:
                    msg = Report.substitution(what="ref-box wrong indent",
                                              with_what="{:+} chars".format(
                                              refbox_col - node_field.name_end.code.end_lincol[1]))

                    out = node_field.name_end.code.copy()
                    out.clear(False)
                    reports.append(Report('E', toolname, out, msg, line))

    return reports


def role_kbd_pre():

    re_lib = dict()
    # config: allow "Regular key pressed as a modifier"
    regular_as_mod = True

    pattern_str = ''.join((
        # Keyboard
        # Modifier
        r"^(Shift(?:\-|\Z))?(Ctrl(?:\-|\Z))?(Alt(?:\-|\Z))?((?:Cmd|OSKey)(?:\-|\Z))?",

        # Alphanumeric
        # Note, shifted keys such as '!?:<>"' should not be included.
        r"((?:",
        r"[A-Z0-9]|",
        r"[=\[\];']|",

        # Named
        '|'.join((
            "Comma", "Period", "Slash", "Backslash", "Minus", "AccentGrave",
            # Editing
            "Tab", "Backspace", "Delete", "Return", "Spacebar",
            # Navigation
            "Esc", "PageUp", "PageDown", "Home", "End",
            "Up", "Down", "Left", "Right", "Menu",
        )), '|',
        # Numpad
        r"(?:Numpad(?:[0-9]|Plus|Minus|Delete|Slash|Period|Asterisk))|",
        # Function
        r"(?:F[1-9]|F1[0-2])",
        r")(?:\-|\Z))",
        r"{0,2}" if regular_as_mod else r"?",

        # Pointing Devices
        r"(",
        # Mouse
        # Wheel
        r"(?:Wheel(Up|Down|In|Out)?)|",
        # Buttons
        r"(?:(?:L|M|R)MB)|",
        # Stylus
        r"(?:Pen|Eraser)|",
        # NDOF
        r"(?:NDOF(?:",
        '|'.join((
            "Menu", "Fit", "Plus", "Minus",
            "Left", "Right", "Top", "Bottom", "Front", "Back",
        )), r"))",
        r")?$",
    ))

    re_lib["valid_kbd"] = re.compile(pattern_str)

    # Directly repeated pressed key e.g. A-A or Left-Left.
    re_lib["repeat_kbd"] = re.compile(r"(?:\-|\A)([^ \-]+?)\-\1")

    args = dict()
    args["re_lib"] = re_lib

    return args


def role_kbd(document, reports, re_lib):
    """Report non-conforming uses of the :kbd: role."""
    toolname = "role-kbd"

    valid_kbd = re_lib["valid_kbd"]
    repeat_kbd = re_lib["repeat_kbd"]

    for node in rst_walker.iter_node(document.body, ("role",), enter_pos=False):
        if rst_walker.is_of(node, "role", "kbd"):
            content = str(node.body.code)

            # chained (not pressed simultaneously): e.g. G X 5
            for k in content.split():
                if not re.match(valid_kbd, k) or re.search(repeat_kbd, k):
                    msg = "invalid keyboard shortcut"
                    if content != k:
                        msg += ": " + k
                    reports.append(Report('W', toolname, node.body.code, msg))

    return reports


def leak_pre():
    toolname = "leak"

    re_lib = dict()

    # BODY
    # Directive
    pattern_str = r"\:\:[A-Za-z\d_-]"
    pattern = re.compile(pattern_str)
    msg = Report.missing(what="space", where="after directive")
    re_lib["dirend"] = (pattern, msg)

    pattern_str = r"\s\.\.[A-Za-z]"
    pattern = re.compile(pattern_str)
    msg = Report.missing(what="space", where="in middle of directive")
    re_lib["dirmid"] = (pattern, msg)

    # List
    pattern_str = r"^ *\-[A-Za-z]"
    pattern = re.compile(pattern_str)
    msg = Report.missing(what="space", where="after unordered list")
    re_lib["unordend"] = (pattern, msg)

    pattern_str = r"^ *#\.[A-Za-z]"
    pattern = re.compile(pattern_str)
    msg = Report.missing(what="space", where="after ordered list")
    re_lib["ordend"] = (pattern, msg)

    pattern_str = r"^( *)\b(?!(\-|\#\.) ).*\n" # capture indent, not list
    pattern_str += r"\1(\-|\#\.) " # same indent, list
    pattern = re.compile(pattern_str, re.MULTILINE)
    msg = Report.missing(what="blank line", where="over list")
    re_lib["overlist"] = (pattern, msg)

    # INLINE
    # Literal, Strong, Emphasis
    # FP: list, code
    pattern_str = r"(?<=\s)(\*\*?|``?)\s[^\-]"
    pattern = re.compile(pattern_str)
    msg = Report.existing(what="spaces", where="around inline markup char")
    re_lib["spaceinline"] = (pattern, msg)

    # FP: target, math
    pattern_str = r"(?<=[A-Za-z])(\*\*?|``?)[A-Za-z]"
    pattern = re.compile(pattern_str)
    msg = Report.missing(what="space", where="before/after inline markup char")
    re_lib["unspaceinline"] = (pattern, msg)

    # Role
    pattern_str = r"\w\:(?:[\w_-]+?)\:`"
    pattern = re.compile(pattern_str)
    msg = Report.missing(what="space", where="before role")
    re_lib["rolestart"] = (pattern, msg)

    pattern_str = r"\:(?:[\w_-]+?)\:[ `\:]`"
    pattern = re.compile(pattern_str)
    msg = Report.existing(what="space", where="between role type and body")
    re_lib["rolemid"] = (pattern, msg)

    pattern_str = r"\:(?:[\w_-]+?)\:`[^`]+?`\w"
    pattern = re.compile(pattern_str)
    msg = Report.missing(what="space", where="after role")
    re_lib["roleend"] = (pattern, msg)

    pattern_str = r"(\:[\w_-]+?[;,.|]`)|([;,.|][\w\-]+?\:`)"
    pattern = re.compile(pattern_str)
    msg = Report.existing(what="wrong mark", where="role body")
    re_lib["rolesep"] = (pattern, msg)

    pattern_str = r"\:(?:doc|ref)\:`[\w\/ _&]+?[^ ]<[\w>\/ _]+?`"
    pattern = re.compile(pattern_str)
    msg = Report.missing(what="space", where="after link title")
    re_lib["linkaddr"] = (pattern, msg)

    pattern_str = r"\:(?:abbr)\:`[\w\/ _&.]+?[^ ]\([\w _.]+?\)`"
    pattern = re.compile(pattern_str)
    msg = Report.missing(what="space", where="after abbreviation title")
    re_lib["abbr"] = (pattern, msg)

    pattern_str = r"\:doc\:`(?:[^/\\][^<>]+?`|[^`]+?<[^/\\])"
    pattern = re.compile(pattern_str)
    msg = Report.missing(what="slash", where="at internal link start")
    re_lib["docstart"] = (pattern, msg)

    pattern_str = r"\:doc\:`([^`]+?\s<)?[A-Za-z]\:[/\\]"
    pattern = re.compile(pattern_str)
    msg = Report.existing(what="drive", where="at internal link start")
    re_lib["docdrive"] = (pattern, msg)

    pattern_str = r"\:doc\:`[^`]+?\.rst>?`"
    pattern = re.compile(pattern_str)
    msg = Report.existing(what="file extension", where="at internal link end")
    re_lib["docext"] = (pattern, msg)

    pattern_str = r"\:doc\:`[^`]+? <[^`]*?[^>]`"
    pattern = re.compile(pattern_str)
    msg = Report.missing(what="closing bracket", where="at internal link end")
    re_lib["docclose"] = (pattern, msg)

    # Internal target
    pattern_str = r"[A-Za-z]_`[^`]"
    pattern = re.compile(pattern_str)
    msg = Report.missing(what="space", where="before internal target")
    re_lib["intrgtstart"] = (pattern, msg)

    # Hyperlink
    pattern_str = r"[^`]`__?[A-Za-z]"
    pattern = re.compile(pattern_str)
    msg = Report.missing(what="space", where="after hyperlink")
    re_lib["linkend"] = (pattern, msg)

    pattern_str = r"https?\:\/\/[^`]+?>`(?!_)"
    pattern = re.compile(pattern_str)
    msg = Report.missing(what="underscore", where="after external hyperlink")
    re_lib["exlinkend"] = (pattern, msg)

    # Substitution
    pattern_str = r"[A-Za-z]\|[A-Za-z]|[A-Za-z]\|_{0,2}[A-Za-z]"
    pattern = re.compile(pattern_str)
    msg = Report.missing(what="space", where="before/after substitution")
    re_lib["subst"] = (pattern, msg)

    # Arrow
    pattern_str = r"(?:[^ \-`]\-\->)|(?:\->[^ `|])"
    pattern = re.compile(pattern_str)
    msg = Report.missing(what="space", where="before/after arrow")
    re_lib["arrow"] = (pattern, msg)

    pattern_str = r"[^\-<]\->"
    pattern = re.compile(pattern_str)
    msg = Report.under(what="dashes", where="in arrow")
    re_lib["arrowlen"] = (pattern, msg)

    # Dash
    pattern_str = r"(?:\w(\-{2,3})(?![->]))|(?:(?<![<-])(\-{2,3})\w)"
    pattern = re.compile(pattern_str)
    msg = Report.missing(what="space", where="before/after dash")
    re_lib["dash"] = (pattern, msg)

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
            print("markup: unknown operation: " + op_name)

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
    ("kbd", role_kbd, role_kbd_pre),
    ("leak", search_code, leak_pre)
)

def main():
    import argparse
    from monostyle import setup

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

    setup_sucess = setup(root_dir)
    if not setup_sucess:
        return 2

    reports = hub(args.op_names)
    print_reports(reports)


if __name__ == "__main__":
    main()
