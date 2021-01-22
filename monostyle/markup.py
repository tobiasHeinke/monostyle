
"""
markup
~~~~~~

RST markup tools.
"""

import re

from monostyle.util.report import Report, getline_punc
import monostyle.rst_parser.walker as rst_walker
from monostyle.rst_parser.core import RSTParser


def heading_level(document, reports):
    """Heading hierarchy defined by the under/overline char."""
    toolname = "heading-level"

    level_chars = ('%', '#', '*', '=', '-', '^', '"', "'")
    levels = {level_char: index for index, level_char in enumerate(level_chars)}
    title_count = 0
    level_prev = 0
    for node in rst_walker.iter_node(document.body, ("sect",), enter_pos=False):
        heading_char = str(node.name_end.code)[0]

        level_cur = -1
        # get list index
        if heading_char in levels.keys():
            level_cur = levels[heading_char]

        if level_cur == -1:
            output = node.name_end.code.copy().replace_fill(heading_char)
            message = Report.existing(what="unknown level")
            reports.append(Report('W', toolname, output, message))

        elif level_cur <= 2:
            if level_cur == 0:

                if not document.code.filename.endswith("manual/index.rst"):
                    output = node.name_end.code.copy().replace_fill(heading_char)
                    message = Report.existing(what="main index title", where="not on main")
                    reports.append(Report('W', toolname, output, message))

            elif level_cur == 1:
                if not document.code.filename.endswith("index.rst"):
                    output = node.name_end.code.copy().replace_fill(heading_char)
                    message = Report.existing(what="index title", where="on page")
                    reports.append(Report('W', toolname, output, message))

            elif document.code.filename.endswith("index.rst"):
                output = node.name_end.code.copy().replace_fill(heading_char)
                message = Report.existing(what="page title", where="on index")
                reports.append(Report('W', toolname, output, message))

            title_count += 1
            if title_count > 1:
                message = Report.over(what="title headings: " + str(title_count))
                output = node.name_end.code.copy().replace_fill(heading_char)
                reports.append(Report('W', toolname, output, message))

            level_prev = 2
        else:
            if title_count == 0:
                if document.body.code.start_lincol[0] == 0:
                    output = node.name_end.code.copy().replace_fill(heading_char)
                    message = Report.missing(what="title heading")
                    reports.append(Report('W', toolname, output, message))
                    # report only once
                    title_count = 1

            elif level_cur > level_prev + 1:
                message = Report.substitution(what="wrong level: {0} > {1}".format(
                                              level_chars[level_prev], heading_char),
                                              with_what=level_chars[level_prev + 1])

                output = node.name_end.code.copy().replace_fill(heading_char)
                reports.append(Report('W', toolname, output, message))

            level_prev = level_cur

    return reports


def indention(document, reports):
    """Check RST code line indention."""
    toolname = "indention"

    default_indent = 3
    field_ind_hanging = 3
    field_ind_fix = 15

    def block_indention(reports, node, offset, is_hanging=True):
        ind_aim = offset + default_indent
        if node.code.span_len(False)[0] > 1:
            block_line = None
            block_line_full = None
            is_first_line = is_hanging
            for line in node.code.splitlines():
                if is_first_line or line.isspace():
                    is_first_line = False
                    continue

                ind_cur = len(line) - len(str(line).lstrip(' \n'))
                if block_line is None or ind_cur < block_line.start_lincol[1]:
                    block_line = line.slice(line.loc_to_abs(ind_cur), after_inner=True)
                    block_line_full = line

            if (block_line is not None and offset != block_line.start_lincol[1] and
                    ind_aim != block_line.start_lincol[1]):
                with_what = "{:+} chars (col: {})".format(ind_aim - block_line.start_lincol[1],
                                                          ind_aim + 1)
                if block_line.start_lincol[1] < ind_aim and offset != ind_aim:
                    with_what += (" or {:+} chars (col: {})"
                                  .format(offset - block_line.start_lincol[1], offset + 1))
                message = Report.substitution(what="wrong indent", with_what=with_what)
                output = block_line.clear(True)
                reports.append(Report('E', toolname, output, message, block_line_full))

        return reports

    markup_space_re = re.compile(r"\S( +)\Z")
    for node in rst_walker.iter_node(document, output_root=True):
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
                        # todo first line only
                        ind_trg_next = len(re.match(r" *", str(next_child.code)).group(0))

                if (ind_trg_next is not None and
                        node.name_start.code.start_lincol[1] != ind_trg_next):
                    message = Report.existing(what="target", where="not on same indent level")
                    reports.append(Report('W', toolname, node.id.code, message))

        # limit: groups of aligned fields, todo favor fix on refbox
        elif node.node_name == "field-list":
            # if (rst_walker.is_of(node.parent_node, "dir", "admonition") and
                  # str(rst_walker.get_attr(node.parent_node, "class")).strip() == "refbox"):

            inds = []
            for node_field in rst_walker.iter_node(node.body, "field"):
                # add one for colon
                ind_name = node_field.name_end.code.start_lincol[1] + 1
                ind_first = (node_field.name_end.code.end_lincol[1]
                            if len(node_field.name_end.code) != 1 else None)
                block_ind = None
                if node_field.body and node_field.body.code.span_len(False)[0] > 1:
                    is_first = True
                    for line in node_field.body.code.splitlines():
                        if is_first or line.isspace():
                            is_first = False
                            continue

                        ind_cur = len(line) - len(str(line).lstrip(' \n'))
                        if not block_ind:
                            block_ind = ind_cur
                        else:
                            block_ind = min(ind_cur, block_ind)

                inds.append((node_field, ind_name, ind_first, block_ind))

            max_name = None
            max_count = 0
            main_ind = 0
            for _, ind_name, ind_first, __ in inds:
                if max_name is None:
                    max_name = ind_name
                else:
                    max_name = max(ind_name, max_name)

                count_cur = sum(1 for _, __, ind_first_rec, ___ in inds
                                            if ind_first_rec == ind_first)
                if count_cur > max_count:
                    max_count = count_cur
                    main_ind = ind_first

            score = {"first": dict.fromkeys({"jag", "align", "fix"}, 0),
                  "block": dict.fromkeys({"hanging", "align"}, 0)}
            for _, ind_name, ind_first, ind_block in inds:
                if ind_first is not None:
                    if ind_first - ind_name == 1:
                        score["first"]["jag"] += 1
                    if ind_first - ind_name >= 1 and ind_first - max_name == 1:
                        score["first"]["align"] += 1
                    if ind_first - ind_name > 1 and ind_first == main_ind:
                        score["first"]["fix"] += 1

                if ind_block is not None:
                    if ind_block < ind_name + 1:
                        score["block"]["hanging"] += 1
                    else:
                        score["block"]["align"] += 1

            ind_aim_first = None
            is_jag = False
            if (score["first"]["align"] > score["first"]["jag"] and
                    score["first"]["align"] > score["first"]["fix"]):
                ind_aim_first = max_name + 1
            elif score["first"]["fix"] > score["first"]["jag"]:
                ind_aim_first = field_ind_fix
            else:
                is_jag = True

            if score["block"]["hanging"] < score["block"]["align"]:
                ind_aim_block = ind_aim_first
            else:
                # subtract colon
                ind_aim_block = (node.body.child_nodes.first().name.code
                                 .loc_to_abs((0, field_ind_hanging))[1] - 1)

            for node_field, ind_name, ind_first, ind_block in inds:
                if ind_first is None:
                    continue
                if is_jag:
                    # add one space
                    ind_aim_first = ind_name + 1
                    ind_aim_block = ind_aim_first

                if ind_first != ind_aim_first:
                    message = Report.substitution(what="field wrong alignment",
                                                  with_what="{:+} chars".format(
                                                  ind_aim_first - ind_first))

                    output = node_field.name_end.code.copy().clear(False)
                    reports.append(Report('W', toolname, output, message, node_field.name))

                if ind_block is not None and ind_block != ind_aim_block:
                    message = Report.substitution(what="field wrong indent",
                                                  with_what="{:+} chars".format(
                                                  ind_aim_block - ind_block))

                    output = node_field.name_end.code.copy().clear(False)
                    reports.append(Report('W', toolname, output, message, node_field.name))

        # todo allow nested block-quote, same line nested
        else:
            if (node.node_name.endswith("-list") or
                    node.node_name.endswith("-table") or
                    rst_walker.is_of(node, ("sect", "comment", "field", "option", "row", "cell")) or
                    rst_walker.is_of(node.parent_node, "text")):
                continue

            is_code = bool(rst_walker.is_of(node, "dir", ("code-block", "default")))
            offset = 0
            if ((not node.parent_node and node.node_name == "snippet") or
                    (not node.prev and
                     node.code.start_lincol[0] == document.code.start_lincol[0] and
                     document.node_name == "snippet" and
                     node.node_name == "block-quote")):
                if node.code.start_lincol[0] != 0:
                    # base indent is unknown
                    continue
            elif node.node_name != "document":
                if node.indent:
                    offset = node.indent.code.end_lincol[1]
                if node.name_start:
                    offset = node.name_start.code.end_lincol[1]
                if node.name_end and node.node_name == "enum":
                    offset = node.name_end.code.end_lincol[1]
                if (is_code and rst_walker.is_of(node, "dir", "default") and
                        node.name_end.code.start_lincol[1] != 0 and node.prev):
                    offset = (node.prev.indent.code.end_lincol[1] if node.prev.indent
                              else node.prev.code.start_lincol[1])

            for part in node.child_nodes:
                if part.child_nodes.is_empty():
                    if node.code.start_lincol[0] != part.code.end_lincol[0]:
                        if is_code:
                            reports = block_indention(reports, part, offset,
                                                      bool(node.code.start_lincol[0] ==
                                                           part.code.start_lincol[0]))
                    elif m := re.search(markup_space_re, str(part.code)):
                        if (len(m.group(1)) != 1 and
                                not rst_walker.is_of(part, "substdef", "*", "id_end")):
                            with_what = "{:+} chars".format(1 - len(m.group(1)))
                            message = Report.substitution(what="wrong markup spacing",
                                                          with_what=with_what)
                            line = (node.child_nodes[2].code if len(node.child_nodes) > 1
                                    else node.code)
                            reports.append(Report('W', toolname, part.code, message, line))
                    continue

                for child in part.child_nodes:
                    if child.node_name.endswith("-list"):
                        child = child.body.child_nodes.first()
                    if (node.code.start_lincol[0] == child.code.start_lincol[0] and
                            child.node_name == "text"):
                        # hanging indention of the first child
                        if node.node_name != "text":
                            reports = block_indention(reports, child, offset)
                    elif child.indent:                            
                        ind_aim = offset + default_indent
                        part_len = len(child.indent.code)
                        if part_len != 0 and part_len != offset and part_len != ind_aim:
                            with_what = "{:+} chars (col: {})".format(ind_aim - part_len,
                                                                      ind_aim + 1)
                            if part_len < ind_aim and offset != ind_aim:
                                with_what += " or {:+} chars (col: {})".format(offset - part_len,
                                                                               offset + 1)
                            message = Report.substitution(what="wrong indent", with_what=with_what)
                            output = child.indent.code.copy().clear(False)
                            reports.append(Report('E', toolname, output, message, child.code))

    return reports


def role_kbd_pre(_):
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
                    message = "invalid keyboard shortcut"
                    if content != k:
                        message += ": " + k
                    reports.append(Report('W', toolname, node.body.code, message))

    return reports


def leak_pre(_):
    toolname = "leak"

    re_lib = dict()

    # BLOCK
    # Directive
    pattern_str = r"^ *\.\. +(?:" + r"|".join(RSTParser.directives) + r")\:\s"
    pattern = re.compile(pattern_str)
    message = Report.existing(what="suspicious comment")
    re_lib["dirsingleend"] = (pattern, message)

    pattern_str = r"(?<=\w)\:\:\w"
    pattern = re.compile(pattern_str)
    message = Report.missing(what="space", where="after directive")
    re_lib["dirnoend"] = (pattern, message)

    pattern_str = r"^ *\.\.[A-Za-z]"
    pattern = re.compile(pattern_str)
    message = Report.missing(what="space", where="in middle of directive")
    re_lib["dirmid"] = (pattern, message)

    # Target
    pattern_str = r"^ *\.\. +[^_ ]\S*?(?<!\:)\: *?$"
    pattern = re.compile(pattern_str, re.MULTILINE)
    message = Report.missing(what="underscore", where="before target")
    re_lib["targetstart"] = (pattern, message)

    pattern_str = r"^ *\.\. +_\S*?[^: \n] *?$"
    pattern = re.compile(pattern_str, re.MULTILINE)
    message = Report.missing(what="colon", where="after target")
    re_lib["targetend"] = (pattern, message)

    # List
    pattern_str = r"^ *\-[A-Za-z]"
    pattern = re.compile(pattern_str)
    message = Report.missing(what="space", where="after unordered list")
    re_lib["unordend"] = (pattern, message)

    pattern_str = r"^ *#\.[A-Za-z]"
    pattern = re.compile(pattern_str)
    message = Report.missing(what="space", where="after ordered list")
    re_lib["ordend"] = (pattern, message)

    pattern_str = r"^( *)\b(?!(\-|\#\.) ).*\n" # capture indent, not list
    pattern_str += r"\1(\-|\#\.) " # same indent, list
    pattern = re.compile(pattern_str, re.MULTILINE)
    message = Report.missing(what="blank line", where="over list")
    re_lib["overlist"] = (pattern, message)

    # INLINE
    # Literal, Strong, Emphasis
    # FP: list, code
    pattern_str = r"(?<=\s)(\*\*?|``?)\s[^\-]"
    pattern = re.compile(pattern_str)
    message = Report.existing(what="spaces", where="around inline markup char")
    re_lib["spaceinline"] = (pattern, message)

    # FP: target, math
    pattern_str = r"(?<=[A-Za-z])(\*\*?|``?)[A-Za-z]"
    pattern = re.compile(pattern_str)
    message = Report.missing(what="space", where="before/after inline markup char")
    re_lib["unspaceinline"] = (pattern, message)

    # Role
    pattern_str = r"\w\:(?:[\w_-]+?)\:`"
    pattern = re.compile(pattern_str)
    message = Report.missing(what="space", where="before role")
    re_lib["rolestart"] = (pattern, message)

    pattern_str = r"\:(?:[\w_-]+?)\:[ `\:]`"
    pattern = re.compile(pattern_str)
    message = Report.existing(what="space", where="between role type and body")
    re_lib["rolemid"] = (pattern, message)

    pattern_str = r"\:(?:[\w_-]+?)\:`[^`]+?`\w"
    pattern = re.compile(pattern_str)
    message = Report.missing(what="space", where="after role")
    re_lib["roleend"] = (pattern, message)

    pattern_str = r"(\:[\w_-]+?[;,.|]`)|([;,.|][\w\-]+?\:`)"
    pattern = re.compile(pattern_str)
    message = Report.existing(what="wrong mark", where="role body")
    re_lib["rolesep"] = (pattern, message)

    pattern_str = r"\:(?:doc|ref)\:`[^`<]+?\S<[^`]+?>`"
    pattern = re.compile(pattern_str)
    message = Report.missing(what="space", where="after link title")
    re_lib["linkaddr"] = (pattern, message)

    pattern_str = r"\:(?:abbr)\:`[^`(]+?\S\([^`)]+?\)`"
    pattern = re.compile(pattern_str)
    message = Report.missing(what="space", where="after abbreviation title")
    re_lib["abbr"] = (pattern, message)

    pattern_str = r"\:doc\:`(?:[^/\\][^<>]+?`|[^`]+?<[^/\\])"
    pattern = re.compile(pattern_str)
    message = Report.missing(what="slash", where="at internal link start")
    re_lib["docstart"] = (pattern, message)

    pattern_str = r"\:doc\:`([^`]+?\s<)?[A-Za-z]\:[/\\]"
    pattern = re.compile(pattern_str)
    message = Report.existing(what="drive", where="at internal link start")
    re_lib["docdrive"] = (pattern, message)

    pattern_str = r"\:doc\:`[^`]+?\.rst>?`"
    pattern = re.compile(pattern_str)
    message = Report.existing(what="file extension", where="at internal link end")
    re_lib["docext"] = (pattern, message)

    pattern_str = r"\:doc\:`[^`]+? <[^`]*?[^>]`"
    pattern = re.compile(pattern_str)
    message = Report.missing(what="closing bracket", where="at internal link end")
    re_lib["docclose"] = (pattern, message)

    # Internal target
    pattern_str = r"[A-Za-z]_`[^`]"
    pattern = re.compile(pattern_str)
    message = Report.missing(what="space", where="before internal target")
    re_lib["intrgtstart"] = (pattern, message)

    # Hyperlink
    pattern_str = r"[^`]`__?[A-Za-z]"
    pattern = re.compile(pattern_str)
    message = Report.missing(what="space", where="after hyperlink")
    re_lib["linkend"] = (pattern, message)

    pattern_str = r"https?\:\/\/[^`]+?>`(?!_)"
    pattern = re.compile(pattern_str)
    message = Report.missing(what="underscore", where="after external hyperlink")
    re_lib["exlinkend"] = (pattern, message)

    # Substitution
    pattern_str = r"[A-Za-z]\|[A-Za-z]|[A-Za-z]\|_{0,2}[A-Za-z]"
    pattern = re.compile(pattern_str)
    message = Report.missing(what="space", where="before/after substitution")
    re_lib["subst"] = (pattern, message)

    # Arrow
    pattern_str = r"(?:[^ \-`]\-\->)|(?:\->[^ `|])"
    pattern = re.compile(pattern_str)
    message = Report.missing(what="space", where="before/after arrow")
    re_lib["arrow"] = (pattern, message)

    pattern_str = r"[^\-<]\->"
    pattern = re.compile(pattern_str)
    message = Report.under(what="dashes", where="in arrow")
    re_lib["arrowlen"] = (pattern, message)

    # Dash
    pattern_str = r"(?:\w(\-{2,3})(?![->]))|(?:(?<![<-])(\-{2,3})\w)"
    pattern = re.compile(pattern_str)
    message = Report.missing(what="space", where="before/after dash")
    re_lib["dash"] = (pattern, message)


    # Merge Conflict
    # = nl to not match heading underline
    # FP = transition
    pattern_str = r"(?:[<>|]{7} \.(?:r\d+?|mine))|(?:\n{2}={7}\n{2})"
    pattern = re.compile(pattern_str, re.MULTILINE)
    message = Report.existing(what="merge conflict")
    re_lib["mc"] = (pattern, message)

    args = dict()
    args["re_lib"] = re_lib
    args["config"] = {"severity": 'E', "toolname": toolname}

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


def search_directive(document, reports):
    """Find unknown/uncommon roles and directives names."""
    toolname = "directive"

    roles = (
        'abbr', 'class', 'doc', 'download', 'guilabel', 'index', 'kbd', 'math',
        'menuselection', 'mod', 'ref', 'sub', 'sup', 'term'
    )

    directives = (
        # standard docutils ones
        #   admonition
        'admonition', 'hint', 'important', 'note', 'tip', 'warning',
        #    other
        'container', 'figure', 'image', 'include', 'list-table', 'math',
        'parsed-literal', 'replace', 'rubric', 'unicode',
        # Sphinx custom ones
        'code-block', 'glossary', 'highlight', 'hlist', 'index', 'only', 'seealso', 'toctree',
        # Sphinx extension
        'vimeo', 'youtube'
    )

    for node in rst_walker.iter_node(document.body, ("dir", "role", "block-quote")):
        if node.node_name == "role":
            if node.name:
                node_name_str = str(node.name.code).strip()
                if node_name_str not in roles:
                    message = ("uncommon role" if node_name_str in RSTParser.roles
                               else "unknown role")
                    reports.append(Report('E', toolname, node.name.code, message))
            else:
                reports.append(Report('E', toolname, node.body.code, "default role"))

        elif node.node_name == "dir":
            name = str(node.name.code).strip() if node.name else node.name
            if name and name not in directives:
                message = ("uncommon directive" if name in RSTParser.directives
                           else "unknown directive")
                reports.append(Report('E', toolname, node.name.code, message))

            if name == "raw":
                message = "raw directive"
                reports.append(Report('E', toolname, node.name.code, message))

        else:
            # not at diff hunk can be cut off def list
            if node.code.start_lincol[0] != document.code.start_lincol[0]:
                output = node.code.copy().clear(True)
                message = "block quote"
                reports.append(Report('W', toolname, output, message))

    return reports


OPS = (
    ("directive", search_directive, None),
    ("heading-level", heading_level, None),
    ("indent", indention, None),
    ("kbd", role_kbd, role_kbd_pre),
    ("leak", search_code, leak_pre)
)


if __name__ == "__main__":
    from monostyle.cmd import main
    main(OPS, __doc__, __file__)
