
"""
markup
~~~~~~

RST markup tools.
"""

import re

from monostyle.util.report import Report
import monostyle.rst_parser.walker as rst_walker
from monostyle.rst_parser.core import RSTParser


def heading_level(toolname, document, reports):
    """Heading hierarchy defined by the under/overline char."""

    level_chars = ('%', '#', '*', '=', '-', '^', '"', "'")
    levels = {level_char: index for index, level_char in enumerate(level_chars)}
    title_count = 0
    level_prev = 0
    for node in rst_walker.iter_node(document.body, "sect", enter_pos=False):
        heading_char = str(node.name_end.code)[0]

        level_cur = -1
        # get list index
        if heading_char in levels.keys():
            level_cur = levels[heading_char]

        severity = 'W'
        message = None
        if level_cur == -1:
            severity = 'E'
            message = Report.existing(what="unknown level")

        elif level_cur <= 2:
            if level_cur == 0:
                if not document.code.filename.endswith("manual/index.rst"):
                    message = Report.existing(what="main index title", where="not on main")

            elif level_cur == 1:
                if not document.code.filename.endswith("index.rst"):
                    message = Report.existing(what="index title", where="on page")

            elif document.code.filename.endswith("index.rst"):
                message = Report.existing(what="page title", where="on index")

            title_count += 1
            if title_count > 1:
                message = Report.over(what="title headings: " + str(title_count))

            level_prev = 2
        else:
            if title_count == 0:
                if document.code.start_lincol[0] == 0:
                    message = Report.missing(what="title heading")
                    # report only once
                    title_count = 1

            elif level_cur > level_prev + 1:
                message = Report.substitution(what="wrong level: {0} > {1}".format(
                                              level_chars[level_prev], heading_char),
                                              with_what=level_chars[level_prev + 1])

            level_prev = level_cur

        if message is not None:
            output = node.name_end.code.copy().replace_fill(heading_char)
            reports.append(Report(severity, toolname, output, message))

    return reports


def indention(toolname, document, reports):
    """Check RST code line indention."""

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
                next_node = next_node.indent
                ind_trg_next = next_node
                # lists
                while (next_node and next_node.node_name == "indent"
                        and next_node.code.start_lincol[0] == ind_trg_next.code.start_lincol[0]):
                    ind_trg_next = next_node
                    next_node = next_node.next_leaf()

                if (ind_trg_next is not None and
                        node.indent.code.end_lincol[1] != ind_trg_next.code.end_lincol[1]):
                    # further intended
                    message = Report.existing(what="target", where="not on same indent level")
                    reports.append(Report('W', toolname, node.id.code, message))
            else:
                # unintended
                message = Report.missing(what="target", where="on same indent level")
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

            is_block_align = bool(score["block"]["hanging"] <= score["block"]["align"])
            if is_block_align:
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
                    if is_block_align:
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
                    rst_walker.is_of(node, {"sect", "comment", "field",
                                            "option", "row", "cell"}) or
                    rst_walker.is_of(node.parent_node, "text")):
                continue

            is_code = bool(rst_walker.is_of(node, "dir", {"code-block", "default", "math"}))
            offset = 0
            if ((not node.parent_node and node.node_name == "snippet") or
                    (node.node_name == "block-quote" and document.node_name == "snippet" and
                     ((not node.prev and
                       node.code.start_lincol[0] == document.code.start_lincol[0]) or
                      (node.prev and not node.prev.prev and
                       node.prev.code.start_lincol[0] == document.code.start_lincol[0] and
                       node.prev.node_name == "text" and node.prev.code.isspace())))):
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


def kbd_pre(_):
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


def kbd(toolname, document, reports, re_lib):
    """Report non-conforming uses of the :kbd: role."""

    valid_kbd = re_lib["valid_kbd"]
    repeat_kbd = re_lib["repeat_kbd"]

    for node in rst_walker.iter_node(document.body, "role", enter_pos=False):
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
    def build_tree(data, root=None):
        def walk_branch(branch, sub, index=0):
            node = branch[index]
            if isinstance(node, str):
                node = (node,)
            for name in node:
                if name not in sub.keys():
                    sub.setdefault(name, dict())
                if index == len(branch) - 2:
                    if not sub[name]:
                        sub[name] = set()
                    sub[name].update(branch[-1])
                else:
                    sub[name] = walk_branch(branch, sub[name], index+1)
            return sub

        def wildcard(sub, trans=None):
            """Copy wildcard subtree to other siblings."""
            if trans is None:
                if isinstance(sub, dict):
                    for key, value in sub.items():
                        if key == "*":
                            wildcard(sub, sub["*"])
                        else:
                            wildcard(value)
            else:
                for key, value in sub.items():
                    if key == "*":
                        continue
                    if isinstance(value, dict):
                        for key_rec, value_rec in trans.items():
                            if key_rec in value.keys():
                                wildcard(value[key_rec], value_rec)
                            else:
                                value[key_rec] = value_rec
                    else:
                        value.update(trans)

            return sub

        if not root:
            root = dict()
        for branch in data:
            if len(branch) != 4:
                print("unexpected branch length", branch)
            root = walk_branch(branch, root)
        root = wildcard(root)
        return root


    re_lib = dict()
    rst_parser = RSTParser()
    start_ind = r"^ *"
    space_end = r"(?: +|(?=\n)|\Z)"
    ref_name = r"[A-Za-z0-9\-_.+]+"

    # BLOCK
    # Directive
    pattern_str = r"\A(?:" + r"|".join(RSTParser.directives) + r")\:\s"
    pattern = re.compile(pattern_str)
    message = Report.missing(what="second colon", where="after directive")
    re_lib["dirsingleend"] = (pattern, message)

    pattern_str = r"(?<=\w)\:\:\w"
    pattern = re.compile(pattern_str)
    message = Report.missing(what="space", where="after directive")
    re_lib["dirnoend"] = (pattern, message)

    pattern_str = start_ind + r"(?:\A|\s)\.\.[A-Za-z]"
    pattern = re.compile(pattern_str, re.MULTILINE)
    message = Report.missing(what="space", where="in middle of directive")
    re_lib["dirmid"] = (pattern, message)

    # Target
    pattern_str = r"\A[^_]\S*?(?<!\:)\: *?(?:\n|\Z)"
    pattern = re.compile(pattern_str, re.MULTILINE)
    message = Report.missing(what="underscore", where="before target")
    re_lib["targetstart"] = (pattern, message)

    pattern_str = r"\A_\S*?[^: \n] *?(?:\n|\Z)"
    pattern = re.compile(pattern_str, re.MULTILINE)
    message = Report.missing(what="colon", where="after target")
    re_lib["targetend"] = (pattern, message)

    # List
    pattern_str = r"\n *" + rst_parser.re_lib["bullet"].pattern.replace(space_end, r"[A-Za-z]")
    pattern = re.compile(pattern_str, re.MULTILINE)
    message = Report.missing(what="space", where="after unordered list")
    re_lib["unordend"] = (pattern, message)

    pattern_str = r"\n *" + rst_parser.re_lib["enum"].pattern.replace(space_end, r"[A-Za-z]") \
                                                             .replace(r"\w", "")
    pattern = re.compile(pattern_str, re.MULTILINE)
    message = Report.missing(what="space", where="after ordered list")
    re_lib["ordend"] = (pattern, message)

    # todo add line, field
    pattern_str = r"\n *(?:" + '|'.join((rst_parser.re_lib["bullet"].pattern,
                                         rst_parser.re_lib["enum"].pattern)) + r")"
    pattern = re.compile(pattern_str, re.MULTILINE)
    message = Report.missing(what="blank line", where="over list")
    re_lib["overlist"] = (pattern, message)


    # INLINE
    # Hyperlink, Internal Target
    pattern_str = r"(?:_')|(?:'_)"
    pattern = re.compile(pattern_str)
    message = Report.existing(what="wrong mark", where="hyperlink or internal target")
    re_lib["linkapos"] = (pattern, message)

    # Role
    pattern_str = r"(\:" + ref_name + r"[;,.|]\Z)|([;,.|]" + ref_name + r"\:\Z)"
    pattern = re.compile(pattern_str)
    message = Report.existing(what="wrong mark", where="role name")
    re_lib["rolesep"] = (pattern, message)

    pattern_str = r"(\:" + ref_name + r"\:')|('\:" + ref_name + r"\:)"
    pattern = re.compile(pattern_str)
    message = Report.existing(what="wrong mark", where="role body")
    re_lib["roleapos"] = (pattern, message)

    pattern_str = r"\A\S"
    pattern = re.compile(pattern_str)
    message = Report.missing(what="space", where="after link title")
    re_lib["linkspace"] = (pattern, message)

    pattern_str = r"\A[^/\\]"
    pattern = re.compile(pattern_str)
    message = Report.missing(what="slash", where="at internal link start")
    re_lib["docstart"] = (pattern, message)

    pattern_str = r"\A[A-Za-z]\:[/\\]"
    pattern = re.compile(pattern_str)
    message = Report.existing(what="drive", where="at internal link start")
    re_lib["docdrive"] = (pattern, message)

    pattern_str = r"\.[A-Za-z0-9]{1,4}\Z"
    pattern = re.compile(pattern_str)
    message = Report.existing(what="file extension", where="at internal link end")
    re_lib["docext"] = (pattern, message)

    pattern_str = r" <[^>]*?\Z"
    pattern = re.compile(pattern_str)
    message = Report.missing(what="closing bracket", where="at internal link end")
    re_lib["linkclose"] = (pattern, message)

    pattern_str = r" \([^)]*?\Z"
    pattern = re.compile(pattern_str)
    message = Report.missing(what="closing parenthesis", where="at abbreviation end")
    re_lib["abbrclose"] = (pattern, message)

    # FP: math
    inlines = {
         ("literal", r"``"),
         ("strong", r"\*\*"),
         ("emphasis", r"(?<!\*)\*(?!\*)"),
         ("subst", r"\|_{0,2}"),
         ("int-target", r"_`"),
         ("dftrole", r"(?<!_)`(?!_)"),
         ("hyperlink", r"`__?"),
         ("role-ft", r"\:" + ref_name + r"\: *`"),
         ("role-bk", r"` *\:" + ref_name + r"\:"),
         ("foot", r"\]_"), # same as cit
         # space underscore?
    }
    markup_keys = set()
    for name, pattern_str in inlines:
        markup_keys.add(name)
        re_lib[name] = (re.compile(r"(\A|^|.)((?<!\\)" + pattern_str + r")(.|$|\Z)", re.MULTILINE),
                        (name if name not in {"role-ft", "role-bk", "dftrole"} else "role",
                         False if name not in {"dftrole"} else None), True)

    # Arrow
    pattern_str = r"(?:[^ \-`]\-\->)|(?:\->[^ `|])"
    pattern = re.compile(pattern_str)
    message = Report.missing(what="space", where="before/after arrow")
    re_lib["arrow"] = (pattern, message, False)

    pattern_str = r"[^\-<]\->"
    pattern = re.compile(pattern_str)
    message = Report.under(what="dashes", where="in arrow")
    re_lib["arrowlen"] = (pattern, message, False)

    # Dash
    pattern_str = r"(?:\w(\-{2,3})(?![->]))|(?:(?<![<-])(\-{2,3})\w)"
    pattern = re.compile(pattern_str)
    message = Report.missing(what="space", where="before/after dash")
    re_lib["dash"] = (pattern, message, False)

    # Backslash
    # Not at block start/ after inline markup
    pattern_str = r"(?!\A)[^\\`*|_]\\[^\s\\`*|_]"
    pattern = re.compile(pattern_str)
    message = Report.existing(what="unnecessary escape")
    re_lib["escape"] = (pattern, message, False)

    markup_keys.update({"arrow", "arrowlen", "dash", "escape"})

    # Merge Conflict
    # FP = transition
    pattern_str = r"(?:[<>|]{7} \.(?:r\d+?|mine))|(?:^={7}\n)"
    pattern = re.compile(pattern_str, re.MULTILINE)
    message = Report.existing(what="merge conflict")
    re_lib["mc"] = (pattern, message)

    node_pattern_map = (
        ("comment", "*", "body", {"dirsingleend", "targetstart", "targetend"}),
        ("text", "*", "body", {"dirnoend", "dirmid", "unordend", "ordend", "overlist",
                               "linkapos", "rolesep", "roleapos", "mc"}),
        ("trans", "*", "name_start", {"mc",}),
        ("role", {"doc", "ref", "term", "any", "download", "numref"}, "id_start", {"linkspace",}),
        ("role", {"doc", "ref", "any", "download", "numref"}, "id", {"linkclose",}),
        ("role", "term", "head", {"linkclose",}),
        ("hyperlink", "*", "id_start", {"linkspace",}),
        ("hyperlink", "*", "body", {"linkclose"}),
        ("role", "abbr", "id_start", {"linkspace",}),
        ("role", "abbr", "head", {"abbrclose",}),
        ("role", "doc", "id", {"docstart", "docdrive", "docext"}),
    )
    node_pattern_map = build_tree(node_pattern_map)

    args = dict()
    args["re_lib"] = re_lib
    args["data"] = (node_pattern_map, markup_keys)
    return args


def leak(toolname, document, reports, re_lib, data):
    """Find pieces of leaked markup and suspicious patterns."""

    names = set(data[0].keys()) if not "*" in data[0].keys() else None
    for node in rst_walker.iter_node(document.body, names, leafs_only=True):
        mapper_portion = (data[0][node.node_name] if node.node_name in data[0].keys()
                                else data[0]["*"])
        name_str = str(node.name.code).strip() if node.name is not None else "default"
        if name_str in mapper_portion.keys():
            mapper_portion = mapper_portion[name_str]
        elif not node.name and "*" in mapper_portion.keys():
            mapper_portion = mapper_portion["*"]
        else:
            continue
        names_part = set(mapper_portion.keys()) if not "*" in mapper_portion.keys() else None
        for part in rst_walker.iter_nodeparts(node, names_part):
            part_str = str(part.code)
            mapper_portion_part = (mapper_portion[part.node_name]
                                   if part.node_name in mapper_portion.keys()
                                   else mapper_portion["*"])
            for key in mapper_portion_part:
                # cut section
                on_mc_trans = bool(not node.prev and key == "mc" and node.node_name == "trans")
                for m in re.finditer(re_lib[key][0], part_str):
                    if on_mc_trans:
                        continue
                    output = part.code.slice_match_obj(m, 0, True)
                    line = Report.getline_offset(part.parent_node.code, output, 100)
                    reports.append(Report('F', toolname, output, re_lib[key][1], line))


    for node in rst_walker.iter_node(document.body, {"text", "sect", "field"}):
        if node.node_name == "text":
            if node.body.child_nodes.is_empty():
                continue
            part_parent = node.body
        else:
            part_parent = node.name

        for node_inline in rst_walker.iter_node(part_parent):
            if (node_inline.node_name == "literal" or
                    rst_walker.is_of(node_inline, "role", "math")):
                continue
            if node_inline.head:
                part = node_inline.head
            elif node_inline.body:
                part = node_inline.body
            else:
                continue

            is_text = bool(node_inline.node_name == "text")
            part_str = str(part.code)
            for key in data[1]:
                for m in re.finditer(re_lib[key][0], part_str):
                    output = part.code.slice_match_obj(m, 0, True)
                    if re_lib[key][2]:
                        message = "leaked "
                        if is_text:
                            direction = None
                            if m.group(2)[-1] in {"_", ":"}:
                                direction = False
                            elif m.group(2)[0] in {"_", ":"}:
                                direction = True
                            delim = (bool(re.match(r"[\W\s]", m.group(1))),
                                      bool(re.match(r"[\W\s]", m.group(3))))
                            whitespace = (bool(re.match(r"\s", m.group(1))),
                                      bool(re.match(r"\s", m.group(3))))
                            if direction is True:
                                if not delim[0]:
                                    message = "no delimiter at start of "
                                elif whitespace[1]:
                                    message = "space after body start of "
                            elif direction is False:
                                if whitespace[0]:
                                    message = "space before body end of "
                                elif not delim[1]:
                                    message = "no delimiter at end of "
                            else:
                                if whitespace[0] and whitespace[1]:
                                    message = "spaces around "
                                elif not delim[0] and not delim[1]:
                                    message = "no delimiter around "

                        message += rst_walker.write_out(re_lib[key][1][0], re_lib[key][1][1])
                    else:
                        message = re_lib[key][1]
                    line = Report.getline_offset(part.parent_node.parent_node.code, output, 100)
                    reports.append(Report('F', toolname, output, message, line))

    return reports


def markup_names(toolname, document, reports):
    """Find unknown/uncommon role and directive names."""

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

    for node in rst_walker.iter_node(document.body, {"dir", "role", "block-quote"}):
        if node.node_name == "role":
            if node.name:
                node_name_str = str(node.name.code).strip()
                if node_name_str not in roles:
                    message = ("uncommon role" if node_name_str in RSTParser.roles or
                               node_name_str in RSTParser.roles_sphinx else "unknown role")
                    reports.append(Report('E', toolname, node.name.code, message))
            else:
                reports.append(Report('E', toolname, node.body.code, "default role"))

        elif node.node_name == "dir":
            name = str(node.name.code).strip() if node.name else node.name
            if name and name not in directives:
                message = ("uncommon directive" if name in RSTParser.directives or
                           name in RSTParser.directives_sphinx else "unknown directive")
                reports.append(Report('E', toolname, node.name.code, message))

            if name == "raw":
                message = "raw directive"
                reports.append(Report('F', toolname, node.name.code, message))

        else:
            # not at diff hunk start can be cut off def list.
            if node.code.start_lincol[0] != document.code.start_lincol[0]:
                output = node.indent.code.copy().clear(False)
                message = "block quote"
                reports.append(Report('W', toolname, output, message))

    return reports


OPS = (
    ("heading-level", heading_level, None),
    ("indention", indention, None),
    ("kbd", kbd, kbd_pre),
    ("leak", leak, leak_pre),
    ("markup-names", markup_names, None),
)


if __name__ == "__main__":
    from monostyle.__main__ import main_mod
    main_mod(__doc__, OPS, __file__)
