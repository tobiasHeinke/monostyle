
"""
markup
~~~~~~

RST markup tools.
"""

import re

import monostyle.util.monostyle_io as monostyle_io
from monostyle.util.report import Report
import monostyle.rst_parser.walker as rst_walker
from monostyle.rst_parser.core import RSTParser


def highlight_pre(toolname):
    config = dict()
    config.update(monostyle_io.get_override(__file__, toolname, "thresholds", (0.6, 1.0)))
    return {"config": config}


def highlight(toolname, document, reports, config):
    """Overuse of inline markup."""
    thresholds = config["thresholds"]
    average_ref = 14
    blank_line = 80

    def evaluate(reports, score_global, counter, score_cur, text_chars, is_final=False):
        distance = score_cur["before"]
        score_global += (0.75 * (-pow(min(distance, 100) / 100, 2) + 1) *
                         score_cur["category_change"] +
                         0.20 * (-pow(min(distance, 75) / 75, 2) + 1) * score_cur["name_change"] +
                         -pow(2 * pow(score_cur["light_len"] /
                                      (score_cur["light_len"] + min(distance, 200) +
                                       min(text_chars, 200)), 2) - 1, 2) + 1)

        counter += 1

        if text_chars > 100 or is_final:
            score_final = (score_global / counter) * (-(1 / (counter + (1 / 1.125))) + 1.125)
            if score_final > thresholds[0]:
                reports.append(
                    Report(Report.map_severity(thresholds, score_final), toolname,
                           score_cur["node"].code.copy().clear(True),
                           Report.quantity(what="highlight overuse",
                                           how=str(counter) + " times"),
                           score_cur["node"].parent_node.code))

            score_global = 0
            counter = 0

        return reports, score_global, counter

    categories = {
        "style": (("emphasis",), ("role", {"sub", "sup"}), ("strong",)),
        "decor": (("literal",),
                ("role", {"abbr", "class", "default", "download",
                          "guilabel", "kbd", "math", "menuselection"})),
        "color": (("cit",), ("foot",), ("hyperlink",), ("int-target",),
                ("role", {"doc", "index", "mod", "ref", "term"}), ("standalone",), ("subst",)),
    }

    score_cur = None
    score_global = 0
    counter = 0
    line_trim_re = re.compile(r"^\s*(\S.*?)\s*$", re.MULTILINE)
    text_chars = 0
    for node_parent in rst_walker.iter_node(document.body, {"text", "dir", "sect"}, False):
        if node_parent.node_name != "text":
            if score_cur:
                reports, score_global, counter = evaluate(reports, score_global, counter,
                                                          score_cur, text_chars, True)
            score_cur = None
            text_chars = average_ref + blank_line
            continue

        node_up = node_parent.parent_node.parent_node
        if rst_walker.is_of(node_up, "def", "*", "head"):
            continue

        for node in rst_walker.iter_node(node_parent.body):
            if node.node_name == "text":
                text_chars += sum(len(m.group(1))
                                  for m in re.finditer(line_trim_re, str(node.code)))
                if not node.next:
                    last_line = (next(node.code.reversed_splitlines())
                                 if node.code.span_len(True) != 0 else None)
                    if not last_line or last_line.isspace():
                        text_chars += blank_line
                continue

            category = None
            for key, value in categories.items():
                for typ in value:
                    if rst_walker.is_of(node, *typ):
                        category = key
                        break
                if category:
                    break
            else:
                continue

            if node.head:
                light_len = len(node.head.code)
            elif node.id:
                light_len = average_ref
            else:
                light_len = len(node.body.code)

            name = node.node_name + (str(node.name).strip() if node.name else "")
            score_next = {
                "before": text_chars / 2 if score_cur else text_chars,
                "category": category,
                "category_change": bool(score_cur is not None and
                                        score_cur["category"] != category),
                "light_len": light_len,
                "name": name,
                "name_change": bool(score_cur is not None and score_cur["name"] != name),
                "node": node,
            }
            if score_cur:
                text_chars = text_chars / 2
                reports, score_global, counter = evaluate(reports, score_global, counter,
                                                          score_cur, text_chars)
            score_cur = score_next
            text_chars = 0

    if score_cur:
        reports, score_global, counter = evaluate(reports, score_global, counter,
                                                  score_cur, text_chars, True)

    return reports


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
            reports.append(
                Report(severity, toolname,
                       node.name_end.code.copy().replace_fill(heading_char), message))

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

                reports.append(
                    Report('E', toolname, block_line.clear(True),
                           Report.substitution(what="wrong indent", with_what=with_what),
                           block_line_full))

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
                    reports.append(
                        Report('W', toolname, node.id.code,
                               Report.existing(what="target", where="not on same indent level")))
            else:
                # unintended
                reports.append(
                    Report('W', toolname, node.id.code,
                           Report.missing(what="target", where="on same indent level")))

        # limit: groups of aligned fields, todo favor fix on refbox
        elif node.node_name == "field-list":
            # if rst_walker.is_of(node.parent_node, "dir", "reference"):

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
                    reports.append(
                        Report('W', toolname, node_field.name_end.code.copy().clear(False),
                               Report.substitution(what="field wrong alignment",
                                   with_what="{:+} chars".format(ind_aim_first - ind_first)),
                               node_field.name.code))

                if ind_block is not None and ind_block != ind_aim_block:
                    reports.append(
                        Report('W', toolname, node_field.name_end.code.copy().clear(False),
                               Report.substitution(what="field wrong indent",
                                   with_what="{:+} chars".format(ind_aim_block - ind_block)),
                               node_field.name.code))

        else:
            if (node.node_name.endswith("-list") or
                    node.node_name.endswith("-table") or
                    rst_walker.is_of(node, {"sect", "comment", "field",
                                            "option", "row", "cell"}) or
                    rst_walker.is_of(node.parent_node, "text")):
                continue

            is_code = bool(rst_walker.is_of(node, "dir", {"code-block", "default", "math"}))
            offset = 0
            if ((not node.parent_node and node.code.start_lincol[0] != 0) or
                    (node.node_name == "block-quote" and document.code.start_lincol[0] != 0 and
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
                    elif markup_space_m := re.search(markup_space_re, str(part.code)):
                        if (len(markup_space_m.group(1)) != 1 and
                                not rst_walker.is_of(part, "substdef", "*", "id_end")):
                            reports.append(
                                Report('W', toolname, part.code,
                                       Report.substitution(what="wrong markup spacing",
                                           with_what="{:+} chars".format(
                                                     1 - len(markup_space_m.group(1)))),
                                       node.child_nodes[2].code if len(node.child_nodes) > 1
                                       else node.code))
                    continue

                for child in part.child_nodes:
                    if child.node_name.endswith("-list"):
                        child = child.body.child_nodes.first()
                    if (node.code.start_lincol[0] == child.code.start_lincol[0] and
                            child.node_name == "text" and node.node_name != "block-quote"):
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
                            reports.append(
                                Report('E', toolname, child.indent.code.copy().clear(False),
                                       Report.substitution(what="wrong indent",
                                                           with_what=with_what), child.code))

    return reports


def kbd_pre(_):
    re_lib = dict()
    # config: allow "Regular key pressed as a modifier"
    regular_as_mod = True

    pattern_str = ''.join((
        # Keyboard
        # Modifier
        r"^(Shift(?:\-|\Z))?(Ctrl(?:\-|\Z))?(Alt(?:\-|\Z))?((?:Cmd|OSKey)(?:\-|\Z))?",

        # Note, shifted keys such as '!?:<>"' should not be included.
        r"((?:",
        # Alphanumeric
        r"[A-Z0-9]|",
        # Symbols
        r"[=\[\];']|",

        # Named
        '|'.join((
            "Comma", "Period", "Slash", "Backslash",
            "Equals", "Minus", "AccentGrave",
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
    re_lib["dirsingleend"] = (
        re.compile(r"\A(?:" + r"|".join(RSTParser.directives) + r")\:\s"),
        Report.missing(what="second colon", where="after directive"))

    re_lib["dirnoend"] = (re.compile(r"(?<=\w)\:\:\w"),
        Report.missing(what="space", where="after directive"))

    re_lib["dirmid"] = (
        re.compile(start_ind + r"(?:\A|\s)\.\.[A-Za-z]", re.MULTILINE),
        Report.missing(what="space", where="in middle of directive"))

    # Target
    re_lib["targetstart"] = (
        re.compile(r"\A[^_]\S*?(?<!\:)\: *?(?:\n|\Z)", re.MULTILINE),
        Report.missing(what="underscore", where="before target"))

    re_lib["targetend"] = (
        re.compile(r"\A_\S*?[^: \n] *?(?:\n|\Z)", re.MULTILINE),
        Report.missing(what="colon", where="after target"))

    # List
    re_lib["unordend"] = (
        re.compile(r"\n *" + rst_parser.re_lib["bullet"].pattern
                   .replace(space_end, r"[A-Za-z]"), re.MULTILINE),
        Report.missing(what="space", where="after unordered list"))

    re_lib["ordend"] = (
        re.compile(r"\n *" + rst_parser.re_lib["enum"].pattern
                   .replace(space_end, r"[A-Za-z]").replace(r"\w", ""), re.MULTILINE),
        Report.missing(what="space", where="after ordered list"))

    # todo add line, field
    re_lib["overlist"] = (
        re.compile(r"\n *(?:" + '|'.join((rst_parser.re_lib["bullet"].pattern,
                                          rst_parser.re_lib["enum"].pattern)) + r")",
                   re.MULTILINE),
        Report.missing(what="blank line", where="over list"))


    # INLINE
    # Hyperlink, Internal Target
    re_lib["linkapos"] = (re.compile(r"(?:_')|(?:'_)"),
        Report.existing(what="wrong mark", where="hyperlink or internal target"))

    # Role
    re_lib["rolesep"] = (
        re.compile(r"(\:" + ref_name + r"[;,.|]\Z)|([;,.|]" + ref_name + r"\:\Z)"),
        Report.existing(what="wrong mark", where="role name"))

    re_lib["roleapos"] = (
        re.compile(r"(\:" + ref_name + r"\:')|('\:" + ref_name + r"\:)"),
        Report.existing(what="wrong mark", where="role body"))

    re_lib["linkspace"] = (re.compile(r"\A\S"),
        Report.missing(what="space", where="after link title"))

    re_lib["docstart"] = (re.compile(r"\A[^/\\]"),
        Report.missing(what="slash", where="at internal link start"))

    re_lib["docdrive"] = (
        re.compile(r"\A([A-Za-z]\:[/\\]|[/\\](?:home[/\\])?users?[/\\]|[.~]{1,2}[/\\])"),
        Report.existing(what="drive", where="at internal link start"))

    re_lib["docext"] = (re.compile(r"\.[A-Za-z0-9]{1,4}\Z"),
        Report.existing(what="file extension", where="at internal link end"))

    re_lib["linkclose"] = (re.compile(r" <[^>]*?\Z"),
        Report.missing(what="closing bracket", where="at internal link end"))

    re_lib["abbrclose"] = (re.compile(r" \([^)]*?\Z"),
        Report.missing(what="closing parenthesis", where="at abbreviation end"))

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
    re_lib["arrow"] = (re.compile(r"(?:[^ \-`]\-\->)|(?:\->[^ `|])"),
        Report.missing(what="space", where="before/after arrow"), False)

    re_lib["arrowlen"] = (re.compile(r"[^\-<]\->"),
        Report.under(what="dashes", where="in arrow"), False)

    # Dash
    re_lib["dash"] = (re.compile(r"(?:\w(\-{2,3})(?![->]))|(?:(?<![<-])(\-{2,3})\w)"),
        Report.missing(what="space", where="before/after dash"), False)

    # Backslash
    # Not at block start/ after inline markup
    re_lib["escape"] = (re.compile(r"(?!\A)[^\\`*|_]\\[^\s\\`*|_]"),
        Report.existing(what="unnecessary escape"), False)

    markup_keys.update({"arrow", "arrowlen", "dash", "escape"})

    # Merge Conflict
    # FP = transition
    re_lib["mc"] = (re.compile(r"(?:[<>|]{7} \.(?:r\d+?|mine))|(?:^={7}\n)", re.MULTILINE),
        Report.existing(what="merge conflict"))

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
                    reports.append(
                        Report('F', toolname, part.code.slice_match_obj(m, 0, True),
                               re_lib[key][1])
                        .set_line_offset(part.parent_node.code, 100))


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
                    if re_lib[key][2]:
                        where = rst_walker.write_out(re_lib[key][1][0], re_lib[key][1][1])
                        message = Report.existing(what="leaked", where=where)
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
                                    message = Report.missing(what="delimiter",
                                                             where="at start of " + where)
                                elif whitespace[1]:
                                    message = Report.existing(what="space",
                                                              where="after body start of " + where)
                            elif direction is False:
                                if whitespace[0]:
                                    message = Report.existing(what="space",
                                                              where="before body end of " + where)
                                elif not delim[1]:
                                    message = Report.missing(what="delimiter",
                                                             where="at end of " + where)
                            else:
                                if whitespace[0] and whitespace[1]:
                                    message = Report.existing(what="spaces",
                                                              where="around " + where)
                                elif not delim[0] and not delim[1]:
                                    message = Report.missing(what="delimiter",
                                                             where="around " + where)

                    else:
                        message = re_lib[key][1]
                    reports.append(
                        Report('F', toolname, part.code.slice_match_obj(m, 0, True), message)
                        .set_line_offset(part.parent_node.parent_node.code, 100))

    return reports


def markup_names(toolname, document, reports):
    """Find unknown/uncommon role and directive names."""
    roles = (
        # standard docutils
        'index', 'sub', 'sup', 'math',
        # Sphinx custom
        'abbr', 'doc', 'download', 'menuselection', 'ref', 'term', 'guilabel', 'kbd',
        #   Sphinx indexing
        'class', 'func', 'meth', 'mod'
    )

    directives = (
        # standard docutils
        #   admonition
        'hint', 'important', 'note', 'tip', 'warning',
        #    other
        'container', 'figure', 'image', 'include', 'list-table', 'math',
        'parsed-literal', 'replace', 'rubric', 'unicode',
        # Sphinx custom
        'code-block', 'glossary', 'highlight', 'hlist', 'index', 'only', 'seealso', 'toctree',
        # Sphinx extension
        'reference', 'vimeo', 'youtube'
    )

    for node in rst_walker.iter_node(document.body, {"dir", "role", "block-quote"}):
        if node.node_name == "role":
            if node.name:
                node_name_str = str(node.name.code).strip()
                if node_name_str not in roles:
                    reports.append(
                        Report('E', toolname, node.name.code,
                               "uncommon role" if node_name_str in RSTParser.roles or
                               node_name_str in RSTParser.roles_sphinx else "unknown role"))
            else:
                reports.append(Report('E', toolname, node.body.code, "default role"))

        elif node.node_name == "dir":
            name = str(node.name.code).strip() if node.name else node.name
            if name and name not in directives:
                reports.append(
                    Report('E', toolname, node.name.code,
                           "uncommon directive" if name in RSTParser.directives or
                           name in RSTParser.directives_sphinx else "unknown directive"))

            if name == "raw":
                reports.append(Report('F', toolname, node.name.code, "raw directive"))

        else:
            # not at diff hunk start can be cut off def list.
            if node.code.start_lincol[0] != document.code.start_lincol[0]:
                reports.append(
                    Report('W', toolname, node.indent.code.copy().clear(False), "block quote"))

    return reports


def structure_pre(_):
    """Match a node with a selector and then move to a next node or
    do a second check with an operator.
    The match of the last selector or after the == operator will result in a report.
    Selector: node_node_name(name)#id[attr_key: attr_value].part_node_name
    and curly brackets for a numeral input.
    ! to invert the individual selector parts, double !! at the start for the entire selector,
    * for a wildcard. 'None' for not existing, comma for an 'in' check.
    Operators need to be space separated on both sides.
    """
    # missing: /re group repetitions, greedy switch (always),
    # /css: child_nodes selection like first-of-type or only

    def new_waypoint(waypoint_str, operator, selector_re, is_start=False):
        """Parses the selector and creates a waypoint."""
        positive = bool(not waypoint_str.startswith("!!"))
        if selector_m := re.match(selector_re, waypoint_str):
            waypoint = {"operator": operator, "is_start": is_start, "is_input": False}
            for index, seg in enumerate(("node", "name", "id", "attr", "part", "node")):
                positive_seg = positive
                if value := selector_m.group(index+1):
                    if value.startswith("!"):
                        positive_seg = False
                        value = value[1:]

                    value = tuple(re.sub(r"\\,", ",", entry)
                                  for entry in re.split(r"(?<!\\),\s*", value))
                    if seg == "attr":
                        new_value = []
                        for entry in value:
                            if (colon_index := entry.find(":")) != -1:
                                new_value.append((entry[:colon_index].strip(),
                                                  entry[colon_index+1:].strip()))
                            else:
                                print("invalid attribute in:", waypoint_str)
                                continue
                        value = tuple(new_value)
                    elif seg == "node" and index > 4:
                        value = tuple(int(entry) if len(entry.strip()) != 0 else None
                                      for entry in value)
                        waypoint["is_input"] = True
                        if operator not in {"/", ">", "&", "&&"}:
                            print("invalid number input in selector:", waypoint_str)
                            return None

                    if operator == "/":
                        waypoint["is_input"] = True
                else:
                    if index > 4:
                        continue
                    value = "*"
                    positive_seg = True

                waypoint[seg] = (value, positive_seg)
        else:
            print("invalid selector in:", waypoint_str)
            return None
        return waypoint


    exprs = (
             ("trans - * == !text, def-list \\ * + !text, def-list",
              {"output": False, "message": "transition not between text"}),
             ("dir(figure, list-table) - def-list \\ * + dir(figure, list-table) & def-list",
              {"output": True, "message": "image splitting definition list"}),
             ("dir(reference) - !sect = !None",
              {"output": True, "message": "reference box not at section start"}),
             ("dir(reference) / head > !None",
              {"output": False, "message": "reference box head misplaced content"}),
             ("dir(reference) / body > * == !field-list + !None",
              {"output": False,
               "message": "reference box body should contain (only) a field-list"}),
             ("sect + dir(figure, reference, list-table, toctree) & !text, def-list, sect = !None",
              {"output": False, "message": "section not starting with a text"}),
             ("bullet-list, enum-list - !text = !None",
              {"output": True, "message": "list without an introductory text"}),
             ("dir(code) - !text",
              {"output": True, "message": "code without an introductory text"}),
             ("- dir(figure) & {1} = None \\ * + dir(figure) && {2} = !None",
              {"output": True, "message": "three or more figures in a row"
               " consider moving them into a list-table"}),
             ("- sect & {1} = None \\ * + sect && {2} = !None",
              {"output": True, "message": "three or more headings in a row"}),
             ("dir(figure) / body = None",
              {"output": True, "message": "figure without a caption"}),
             ("strong, emphasis << sect",
              {"output": True, "message": "font styling in heading"}),
             ("- {0} & {{1}} = None \\ * + {0} && {{2}} = !None"
              .format("dir(note, tip, important, hint, warning, seealso)"),
              {"output": True, "message": "three or more boxes in a row"}),
             ("+ emphasis, strong || !None",
              {"output": True, "message": "adjoined inline nodes of the same type"}),
             ("dir(seealso) + !None",
              {"output": True, "message": "seealso admonition not at section end"}),
             ("dir(index) - target, comment",
              {"output": True, "message": "index directive not at top"}),
            )
    operators_start = {
        "^": " + None \\ *",
        "^^": " ++ None \\ *",
        "$": " - None \\ *",
        "$$": " -- None \\ *",
    }
    ref = r"(\!?(?:\*|[\w.+:-]+)(?:, *(?:\*|[\w.+:-]+))*)"
    selector_re = re.compile("".join((r"(?:\!??", ref, r"(?:\(([^)]*?)\))?(?:#", ref,
                                      r")?(?:\[([^\]]*?)\])?(?:\.", ref,
                                      r")?)|(?:\{([+-]?\d+?(?: *, *[+-]?\d*?)?)\})")))
    operator_re = re.compile(r"(?:\A| +)(([\^$|=/\\+\-<>?&])\2?) +")
    operators = {";", "=", "==", "+", "-", "++", "--", "/", ">", ">>",
                 "<", "<<", "\\", "?", "&", "&&", "|", "||"}
    pos_names = set()
    routes = []
    for expr, report_info in exprs:
        if operator_m := re.match(operator_re, expr):
            if operator_m.group(1) in operators_start.keys():
                expr = expr[operator_m.end(0):]
                if selector_m := re.match(selector_re, expr):
                    expr = "".join((expr[:selector_m.end(0)],
                                    operators_start[operator_m.group(1)],
                                    expr[selector_m.end(0):]))
                else:
                    print("invalid first selector in:", expr)
                    continue

        route = []
        operator = None
        last = 0
        is_start = False
        success = True
        for operator_m in re.finditer(operator_re, expr):
            if operator_m.group(1) not in operators:
                print("invalid operator '{}' in: {}".format(operator_m.group(1), expr))
                break

            if last != operator_m.start(0):
                if waypoint := new_waypoint(expr[last:operator_m.start(0)], operator,
                                            selector_re, is_start):
                    route.append(waypoint)
                else:
                    success = False
                    break

            operator = operator_m.group(1)
            last = operator_m.end(0)
            is_start = bool(operator_m.start(0) == 0)

        if not success:
            break

        if last != len(expr):
            if waypoint := new_waypoint(expr[last:], operator, selector_re):
                route.append(waypoint)
            else:
                break

        for waypoint in route:
            if waypoint["operator"] not in (None, ";"):
                break
            if not waypoint["node"][1]:
                pos_names = None
            elif pos_names is not None:
                pos_names.update(waypoint["node"][0])

        routes.append((route, report_info))

    return {"data": (pos_names, routes)}


def structure(toolname, document, reports, data):
    """Inspect the document structure by matching a path."""
    def matcher(node, waypoint):
        """Matches the node with the names in the waypoint."""
        if node is None or node.code.isspace():
            return bool(("None" in waypoint["node"][0]) == waypoint["node"][1])
        if "None" in waypoint["node"][0] and not waypoint["node"][1]:
            return True

        if not(rst_walker.is_of(node, waypoint["node"][0]) == waypoint["node"][1]):
            return False
        if not(rst_walker.is_of(node, "*", waypoint["name"][0]) == waypoint["name"][1]):
            return False
        if not(rst_walker.is_of(node, "*", "*", waypoint["part"][0]) == waypoint["part"][1]):
            return False
        if waypoint["id"][0] != "*":
            if (not((node.id and
                    ("*" in waypoint["id"][0] or
                     str(node.id.code).strip() in waypoint["id"][0])) == waypoint["id"][1])):
                return False
        if waypoint["attr"][0] != "*":
            for entry in waypoint["attr"][0]:
                value = rst_walker.get_attr(node, entry[0])
                if value is None or value.code.isspace():
                    return bool((entry[1] == "None") == waypoint["node"][1])
                if (not((entry[1] == "*" or str(value.code).strip() == entry[1]) ==
                        waypoint["attr"][1])):
                    return False
        return True

    def matcher_duplicate(node_active, waypoint_active, node_con, waypoint_con):
        """Returns if the node matches a reference node with a waypoint as criterion."""
        def attr_value(node, key):
            value = rst_walker.get_attr(node, key)
            if value is None or value.code.isspace():
                return None
            return str(value.code).strip()

        if node_active is None or node_con is None:
            return bool(node_active == node_con)

        get_value = {
            "node": lambda node: rst_walker.to_node(node).node_name,
            "name": lambda node: str(node.name.code).strip() if node.name else None,
            "id": lambda node: str(node.id.code).strip() if node.id else None,
            "part": lambda node: node.node_name,
        }
        for seg in ("node", "name", "id", "attr", "part"):
            if waypoint_con[seg][0] == "*":
                continue
            if seg != "attr":
                if get_value[seg](node_active) != get_value[seg](node_con):
                    return False
            else:
                for entry in waypoint_con["attr"][0]:
                    if entry[1] == "*":
                        continue
                    if attr_value(node_active, entry[0]) != attr_value(node_con, entry[0]):
                        return False

        return True

    def operate(node_active, waypoint_active, node_con, waypoint_con, on_active=True):
        def skip(node_active, waypoint_active):
            waypoint = waypoint_active if not waypoint_con else waypoint_con
            if node_active.node_name == "text":
                return bool(node_active.code.isspace())
            for typ in (("target",), ("comment",), ("substdef",),
                        ("dir", "highlight"), ("dir", "index")):
                if rst_walker.is_of(node_active, *typ):
                    return bool(typ[0] != waypoint["node"] and
                            (len(typ) == 1 or typ[1] != waypoint["name"]))
            return False

        operators = {
            ";": lambda node_active, *_: node_active,
            "=": lambda node_active, *_: node_active,
            "==": lambda node_active, *_: node_active,
            # traversals
            "+": lambda node_active, *_: node_active.next,
            "-": lambda node_active, *_: node_active.prev,
            "++": lambda node_active, *_: node_active.next_leaf(),
            "--": lambda node_active, *_: node_active.prev_leaf(),
            "/": lambda node_active, waypoint_active, *_:
                 get_child_node(node_active, waypoint_active),
            ">": lambda node_active, *_: node_active.child_nodes.first(),
            ">>": lambda node_active, *_: node_active.child_nodes.last(),
            "<": lambda node_active, *_: node_active.parent_node,
            "<<": lambda node_active, *_: node_active.parent_node.parent_node
                                          if node_active.parent_node else None,
            "\\": lambda _, __, node_con, ___: node_con,
            # repetitions
            "?": lambda node_active, waypoint_active, node_con, waypoint_con:
                 repeat(node_active, waypoint_active, node_con, waypoint_con, (0, 1)),
            "&": lambda node_active, waypoint_active, node_con, waypoint_con:
                 repeat(node_active, waypoint_active, node_con, waypoint_con, (0, None)),
            "&&": lambda node_active, waypoint_active, node_con, waypoint_con:
                  repeat(node_active, waypoint_active, node_con, waypoint_con, (1, None)),
            "|": lambda node_active, waypoint_active, node_con, waypoint_con:
                 duplicate(node_active, waypoint_active, node_con, waypoint_con),
            "||": lambda node_active, waypoint_active, node_con, waypoint_con:
                  duplicate(node_active, waypoint_active, node_con, waypoint_con),
        }
        operator = waypoint_active["operator"] if on_active else waypoint_con["operator"]
        if not operator:
            print(waypoint_active["operator"] if not on_active else waypoint_con["operator"],
                " no operation to repeat")
            return None

        node_prev = node_active
        operation = operators[operator]
        node_active = operation(node_active, waypoint_active, node_con, waypoint_con)
        if node_active is not node_prev and operator != "\\":
            while node_active and skip(node_active, waypoint_active):
                node_active = operation(node_active, waypoint_active, node_con, waypoint_con)
        return node_active

    def repeat(node_active, waypoint_active, node_con, waypoint_con, span=None):
        """Repeats the previous the operation while the note matches the waypoint."""
        if waypoint_active["is_input"]:
            span = waypoint_active["node"][0]
        if waypoint_con["is_start"]:
            node_active = operate(node_active, waypoint_active, node_con, waypoint_con, False)
        counter = 0
        while node_active and matcher(node_active, waypoint_con):
            if (span and ((len(span) == 1 and counter == span[0]) or
                    (len(span) != 1 and counter == span[1]))):
                break
            node_active = operate(node_active, waypoint_active, node_con, waypoint_con, False)
            counter += 1

        if span and counter < span[0]:
            return None

        return node_active

    def duplicate(node_active, waypoint_active, node_con, waypoint_con):
        """Repeats the previous the operation if the node matches a reference node."""
        if node_active is None or node_con is None:
            return node_active if node_active == node_con else None

        node_active = operate(node_active, waypoint_active, node_con, waypoint_con, False)
        if not matcher_duplicate(node_active, waypoint_active, node_con, waypoint_con):
            return None
        return node_active

    def get_child_node(node_active, waypoint_active):
        """Returns child node by name or index."""
        if not isinstance(waypoint_active["node"][0][0], int):
            if (waypoint_active["node"][0] != "*" and
                    hasattr(node_active, waypoint_active["node"][0][0])):
                return getattr(node_active, waypoint_active["node"][0][0])
        else:
            if abs(waypoint_active["node"][0][0]) < len(node_active.child_nodes):
                return node_active.child_nodes[waypoint_active["node"][0][0]]

    routes = data[1]
    for node in rst_walker.iter_node(document, data[0]):
        for route, report_info in routes:
            waypoint_con = None
            node_con = None
            for index, waypoint_active in enumerate(route):
                if index == 0:
                    node_active = node
                    node_prev = node
                else:
                    node_prev = node_active
                    node_active = operate(node_active, waypoint_active, node_con, waypoint_con)

                operator_next = route[index+1]["operator"] if index != len(route) - 1 else None
                if not waypoint_active["is_input"]:
                    if matcher(node_active, waypoint_active):
                        if (not operator_next or
                                waypoint_active["operator"] == "==" or
                                (waypoint_con and waypoint_con["operator"] == "==")):
                            node_output = node
                            if report_info["output"]:
                                if node_active:
                                    node_output = node_active
                                elif node_con:
                                    node_output = node_con
                            reports.append(
                                Report(report_info.get("severity", 'I'), toolname,
                                       node_output.code.copy().clear(True),
                                       report_info["message"]))

                            break

                    elif (index == 0 or (operator_next not in {";", "?", "&"} and
                            waypoint_active["operator"] != "==")):
                        break

                if operator_next:
                    if node_active is None and operator_next not in {";", "=", "==", "\\"}:
                        break
                    if operator_next in {";", "=", "==", "?", "&", "&&", "|", "||", "\\"}:
                        if waypoint_con is None:
                            waypoint_con = waypoint_active
                            if operator_next in {"|", "||"} or index == 0:
                                node_con = node_active
                            else:
                                node_con = node_prev
                    elif waypoint_con:
                        waypoint_con = None
                        node_con = None

    return reports


OPS = (
    ("highlight", highlight, highlight_pre),
    ("heading-level", heading_level, None),
    ("indention", indention, None),
    ("kbd", kbd, kbd_pre),
    ("leak", leak, leak_pre),
    ("markup-names", markup_names, None),
    ("structure", structure, structure_pre),
)


if __name__ == "__main__":
    from monostyle.__main__ import main_mod
    main_mod(__doc__, OPS, __file__)
