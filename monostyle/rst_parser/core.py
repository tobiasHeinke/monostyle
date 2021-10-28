
"""
rst_parser.core
~~~~~~~~~~~~~~~

Main module of the RST parser.
"""

import re
from monostyle.util.fragment import Fragment, FragmentBundle
from monostyle.util.nodes import LinkedList
from monostyle.rst_parser.rst_node import NodeRST, NodePartRST

class RSTParser:
    """An RST parser."""

    directives = (
        'admonition', 'attention', 'caution', 'class', 'code', 'compound',
        'container', 'contents', 'csv-table', 'danger', 'date', 'default-role', 'epigraph',
        'error', 'figure', 'footer', 'header', 'highlights', 'hint', 'image',
        'important', 'include', 'line-block', 'list-table', 'math', 'meta', 'note',
        'parsed-literal', 'pull-quote', 'raw', 'replace', 'restructuredtext-test-directive',
        'role', 'rubric', 'section-numbering', 'sectnum', 'sidebar', 'table', 'target-notes',
        'tip', 'title', 'topic', 'unicode', 'warning'
    )
    directives_sphinx = (
        'acks', 'centered', 'codeauthor', 'code-block', 'deprecated', 'glossary', 'highlight',
        'highlightlang', 'hlist', 'index', 'literalinclude', 'only', 'productionlist',
        'sectionauthor', 'seealso', 'tabularcolumns', 'toctree', 'versionadded', 'versionchanged'
    )

    roles = (
        'ab', 'abbreviation', 'ac', 'acronym', 'anonymous-reference', 'citation-reference', 'code',
        'emphasis', 'footnote-reference', 'i', 'index', 'literal', 'math', 'named-reference',
        'pep', 'pep-reference', 'raw', 'rfc', 'rfc-reference', 'strong', 'sub', 'subscript',
        'substitution-reference', 'sup', 'superscript', 't', 'target', 'title', 'title-reference',
        'uri', 'uri-reference', 'url'
    )
    roles_sphinx = (
        'abbr', 'any', 'class', 'command', 'dfn', 'doc', 'download', 'envvar', 'eq',
        'file', 'guilabel', 'kbd', 'keyword', 'mailheader', 'makevar', 'manpage',
        'menuselection', 'mimetype', 'mod', 'newsgroup', 'numref',
        'option', 'program', 'ref', 'regexp', 'samp', 'term', 'token'
    )

    substitution = {
        'release': Fragment('', ''),
        'version': Fragment('', ''),
        'today': Fragment('', ''),
    }

    trans_chars = ('!', '"', '#', '$', '%', '&', '\'', '(', ')', '*', '+', '-', ',', '.', '/',
                   ':', ';', '<', '=', '>', '?', '@', '[', ']', '^', '_', '`', '{', '|', '}', '~')
    bullet_chars = ('*', '-', '+', '•', '‣', '⁃')
    foot_chars = ('*', '†', '‡', '§', '¶', '#', '♠', '♥', '♦', '♣')


    def __init__(self):
        self.re_lib = self._compile_re_lib()
        self.warnings = []


    def _compile_re_lib(self):
        re_lib = dict()

        # Block
        ind = r"( *)"
        re_lib["ind"] = re.compile(ind + r"\S")
        space_end = r"(?: +|(?=\n)|\Z)"
        eol_end = r" *(?:\n|\Z))"

        ref_name = r"(?:(?!_)\w)+(?:[-._+:](?:(?!_)\w)+)*"
        foot_name = "".join((r"(?:\d+)|[", "".join(self.foot_chars), r"]|(?:#", ref_name, r")"))
        mid_a = r"(\S.*?(?<![\s\\"
        mid_b = r"]))"
        option_arg = r"(?:[-/]\w|\-\-\w[\w-]+(?:[ =][\w.;:\\/\"'-]+)?)"
        expl = ''.join((ind, r"(\.\.", space_end, r")"))
        direc = ''.join((r"(", ref_name, r")(\:\:", space_end, r")"))

        blocks = (
            ("trans", (ind, r"(([", r''.join(map(re.escape, self.trans_chars)), r"])\3*",
                       eol_end), ("indent", "name_start")),
            ("bullet", (ind, r"([", r''.join(map(re.escape, self.bullet_chars)), r"]",
                        space_end, r")"), ("indent", "name_start", "body")),
            ("enum", (ind, r"(\()?([#\w]|\d+)([\.\)]", space_end, r")"),
                ("indent", "name_start", "name", "name_end", "body")),
            ("line", (ind, r"(\|", space_end, r")"), ("indent", "name_start", "body")),
            ("field", (ind, r"(\:(?!", ref_name, r"\:`))([^:].*?)((?<!\\)\:", space_end, r")"),
                ("indent", "name_start", "name", "name_end", "body")),
            ("option", (ind, r"(", option_arg, r"(?:, ", option_arg, r")*)",
                        r"( ", space_end, r"|(?:", eol_end, r")"),
                ("indent", "name", "name_end", "body")),
            ("expl", (ind, r"((?:\.\.|__)", space_end, r")"), None),
            ("comment", (ind, r"(\.\.", space_end, r")"), ("indent", "name_start", "body")),
            ("dftdir",(r"(\A *)?(?<![^\\]\\)(\:\:", space_end, ")"),
                ("indent", "name_end", "head")),
            ("dir", (expl, direc), ("indent", "name_start", "name", "name_end", "head")),
            ("substdef", (expl, r"(\|)(", ref_name, r")(\|\s+)(?:", direc, r")?"),
                ("indent", "name_start", "id_start", "id", "id_end", "name", "name_end", "head")),
            ("footdef", (expl, r"(\[)(", foot_name, r")(\]", space_end, r")"),
                ("indent", "name_start", "id_start", "id", "id_end", "head")),
            ("citdef", (expl, r"(\[)(", ref_name, r")(\]", space_end, r")"),
                ("indent", "name_start", "id_start", "id", "id_end", "head")),
            ("target", (expl, r"(_ *(`)?)(?(4)(?:((?:[^`]*?[^\\", mid_b, r"(`))|",
                        mid_a, mid_b, r")", r"(\:", space_end, r")"),
                ("indent", "name_start", "id_start", None, "id", "id_end",
                 "id", "name_end", "head")),
            ("target-anon", (expl, r"?(__ *)(\:", space_end, r")?"),
                ("indent", "name_start", "id_start", "name_end", "head")),
            ("quoted", (ind, r"[", r''.join(map(re.escape, self.trans_chars)), r"]"), None),
            ("doctest", (ind, r">>>\s"), ("indent", "body")),

            ("grid_border", (ind, r"((?:\+\-+?)*\+\-+\+", eol_end), None),
            ("grid_row_frame", (ind, r"[+|].+[+|]", space_end), None),
            ("grid_cell_border", (r"[\+-]\Z",), None),
            ("grid_head_border", (ind, r"((?:\+=+?)*\+=+\+", eol_end), None),
            ("simple_row_border", (ind, r"((?:=+?\s+)*=+", eol_end), None),
            ("simple_column_span", (ind, r"((?:\-+?\s+)*\-+", eol_end), None),
        )
        for name, pattern_str, part_names in blocks:
            pattern = re.compile(''.join(pattern_str))
            re_lib[name] = (pattern, part_names) if part_names is not None else pattern

        # Inline
        before_a = r"(?:(?<=[^\w\\"
        before_b = r"])|\A)"
        after_a = r"(?:(?=[^\w"
        after_b = r"])|\Z)"
        url_chars = r"[-_.!?~#*'()[\];/:&=+$,%a-zA-Z0-9]"
        url = r"(?:\\[*_])?" + url_chars + r"*\b(?:\\[*_]" + url_chars + r"*)*"

        part_names_default =  ("body_start", "body", "body_end")
        inlines = {
            ("literal", (r"`", r"``", True, r"", r"``", r"`"), part_names_default),
            ("strong", (r"\*", r"\*\*", True, r"*", r"\*\*", r"\*"), part_names_default),
            ("emphasis", (r"\*", r"\*", True, r"*", r"\*", r"\*"), part_names_default),
            ("subst", ("", r"\|", True, r"\|", r"\|_{0,2}", ""), ("body_start", "id", "body_end")),
            ("int-target", ("", r"_`", True, "", r"`", r"`"), part_names_default),
            ("dftrole", (r"_:`", r"`", True, r"`", r"`", r"`"), part_names_default),
            ("hyperlink", (r"`:_", r"`", True, r"`", r"`__?", ""), part_names_default),
            ("role-ft", ("", r"\:)(" + ref_name + r")(\:)(`", True, "", r"`", ""),
                ("name_start", "name", "name_end", "body_start", "body", "body_end")),
            ("role-bk", ("", r"`", True, "", r"`)(\:)(" + ref_name + r")(\:", ""),
                ("body_start", "body", "body_end", "name_start", "name", "name_end")),
            ("foot", ("", r"\[", False, foot_name, r"\]_", ""), part_names_default),
            ("cit", ("", r"\[", False, ref_name, r"\]_", ""), part_names_default),
            ("int-target-sw", ("", r"_(?!_)", False, ref_name, "", ""), ("body_start", "body")),
            ("hyperlink-sw", ("", "", False, ref_name, r"_(?!_)", ""), ("id", "body_end")),
            ("standalone", (r"", "", False, r"\b(?<!\\)(?:https?\:\/\/|mailto\:)" + url, "", ""),
                ("body",)),
            ("mail", (r"<`/", "", False, r"\b" + url + r"(?<!\\)@" + url + r"\." + url, "", ""),
                ("body",)),
            ("link", ("", r"<", True, "", r">", ""), part_names_default),
            ("parenthesis", ("", r"\(", True, "", r"\)", ""), part_names_default),
            # ("arrow", r"-", "", False, r"\-{1,2}>", "", "")
            # ("dash", r"-", "", False, r"\-{2,3}", "", "")
        }
        for name, pattern_strs, part_names in inlines:
            before_no, start, is_dot_mid, mid, end, after_no = pattern_strs
            if name not in {"link", "parenthesis"}:
                before = (before_a, before_no, before_b)
            else:
                before = ()
                start = r"(?:\s+?|\A)" + start

            if is_dot_mid:
                mid = (mid_a if name != "literal" else mid_a[:-2], mid, mid_b)
            else:
                mid = (r"(", mid, r")")

            if name != {"standalone", "mail"}:
                after = (after_a, after_no, after_b)
            else:
                after = ()

            pattern_str = (*before, r"(", start, r")",
                           *mid,
                           r"(", end, r")", *after)
            re_lib[name] = (re.compile(''.join(pattern_str), re.DOTALL), part_names)

        return re_lib


    _key_node_name = {
        "target-anon": "target",
        "role-ft": "role", "role-bk": "role", "dftrole": "role",
        "int-target-sw": "int-target",
        "hyperlink-sw": "hyperlink",
        "mail": "standalone",
    }


    def warning(self, code, message):
        """Add warning to the log."""
        self.warnings.append("{0}:{1}: {2}".format(code.filename, code.start_lincol[0], message))


    # ------------------------------------------------------------------------

    def parse_block(self, node, ind_first_unknown=False):
        lines = []
        block_ind = None
        ind_re = self.re_lib["ind"]
        line_info_prev = None
        line_info = {"is_blank": True}
        for line in node.code.splitlines():
            line_str = str(line)
            line_info = {"is_block_start": line_info["is_blank"],
                         "line_str": line_str,
                         "line_str_next": None,
                         "indented": False,
                         "is_block_end": False}

            if ind_m := re.match(ind_re, line_str):
                ind_abs = line.loc_to_abs((0, ind_m.end(1)))[1]
                if block_ind is None:
                    block_ind = ind_abs
                else:
                    block_ind = min(block_ind, ind_abs)

                line_info["ind_cur"] = ind_abs
                line_info["is_blank"] = False
            else:
                line_info["ind_cur"] = 0
                line_info["is_blank"] = True
                if line_info_prev:
                    line_info_prev["is_block_end"] = True

            if line_info_prev:
                line_info_prev["line_str_next"] = line_str

            lines.append((line, line_info))
            line_info_prev = line_info

        line_info["is_block_end"] = True
        block_ind = block_ind if block_ind is not None and node.parent_node.parent_node else 0
        root = node

        is_first = True
        is_sec = True
        indented_prev = False
        node.is_parsing = True
        recorder = (({"block-quote",}, self.block_quote),
                    ({"field", "bullet", "enum", "line", "option"}, self.listing),
                    ({"dir", "target", "comment", "substdef", "footdef", "citdef"},
                     self.explicit_block),
                    ({"trans",}, self.transition),
                    ({"sect", "trans", "text"}, self.section),
                    ({"doctest",}, self.doctest),
                    ({"grid-table",}, self.grid_table),
                    ({"simple-table",}, self.simple_table),
                    ({"def", "text"}, self.def_list),
                    ({"text",}, self.explicit_block), # default dir
                    ({"text",}, self.paragraph))

        for line, line_info in lines:
            line_info["block_ind"] = block_ind
            if not line_info["is_blank"]:
                ind_cur = line_info["ind_cur"]
                if ind_cur == block_ind:
                    line_info["indented"] = False
                    if indented_prev:
                        line_info["is_block_start"] = True
                elif ind_cur > block_ind:
                    line_info["indented"] = True
                    line_info["is_block_start"] = True
                else:
                    line_info["indented"] = False
                    line_info["is_block_start"] = True

                if is_first and line.start_lincol[1] != 0:
                    line_info["indented"] = False
                if is_sec and not is_first:
                    # alternative when head first indent as unknown
                    if ind_first_unknown and (not node.active or node.active.node_name == "text"):
                        line_info["indented"] = False
                    is_sec = False
                is_first = False
            else:
                # blank line does not change indented
                line_info["indented"] = indented_prev

            indented_prev = line_info["indented"]

            free = True
            if node.active:
                free = False
                for names, node_typ in recorder:
                    if node.active.node_name in names:
                        node = node_typ(node, line, line_info)
                        if (node.active and
                                (node.active.node_name == "text" or
                                (node.active.node_name == "trans" and len(names) == 1))):
                            continue
                        break

            if not node.active and (not line_info["is_blank"] or free):
                if not free :
                    line_info["is_block_start"] = True
                for _, node_typ in recorder:
                    node = node_typ(node, line, line_info)
                    if node.active:
                        break


        if node.active:
            if (node.child_nodes.last() and
                    node.child_nodes.last().node_name == node.active.node_name or
                    node.parent_node.node_name == node.active.node_name + "-list"):
                node.append_child(node.active)
            elif (node.active.active and node.active.active.active and
                    node.active.active.active.node_name == "row"):
                node.active.active.append_child(node.active.active.active)
                root.append_child(root.active)
            else:
                root.append_child(root.active)

        return root


    def parse_inline(self, node, name=None):
        new_node = NodeRST("text", node.code)
        new_node.append_part("body", node.code)
        node.child_nodes.append(new_node)

        recorder = ("literal", "strong", "emphasis", "int-target",
                    "role-ft", "role-bk", "hyperlink", "dftrole", "subst", "foot", "cit",
                    "standalone", "mail", "int-target-sw", "hyperlink-sw")
        if name is not None:
            recorder = (name,)

        for name in recorder:
            node.active = node.child_nodes.first()
            while node.active:
                if node.active.node_name == "text":
                    node = self.inline(node, node.active.body.code, name)
                    if node.active and name == node.active.node_name:
                        self.warning(node.active.code, "unclosed inline (within paragraph)")
                else:
                    node.active = node.active.next

        return node


    def parse(self, doc):
        doc.is_parsing = True
        doc.body = self.parse_block(doc.body)
        doc.body = self.parse_node(doc.body)
        doc.body = self.parse_node_inline(doc.body)
        doc.is_parsed = True
        return doc


    def parse_node(self, root):
        for node in root.child_nodes:
            if (node.node_name != "text" and
                    node.node_name not in {"comment", "doctest"}):
                parts = ((node.head, node.attr, node.body)
                          if (node.node_name != "dir" or not(not node.name or
                              str(node.name.code).rstrip() in {"code-block", "math"}))
                          else (node.attr,))
                for part in parts:
                    if part:
                        if not part.child_nodes.is_empty():
                            self.parse_node(part)
                        else:
                            ind_first_unknown = False
                            if part.prev and part.prev.node_name != "indent":
                                ind_first_unknown = (lambda f, c: f[0] == c[0] and f[1] != c[1])(
                                                        node.child_nodes.first().code.start_lincol,
                                                        part.code.start_lincol)

                            part = self.parse_block(part, ind_first_unknown)
                            part.is_parsed = True
                            if not part.child_nodes.is_empty():
                                self.parse_node(part)

            node.is_parsed = True
        return root


    def parse_node_inline(self, root):
        for node in root.child_nodes:
            if ((node.node_name != "dir" or not(not node.name or
                    str(node.name.code).rstrip() in {"code-block", "math"})) and
                    node.node_name not in {"comment", "doctest"}):

                if node.node_name in {"sect", "field"} and node.name:
                    node.name = self.parse_inline(node.name)

                if node.head:
                    if not node.head.child_nodes.is_empty():
                        self.parse_node_inline(node.head)
                    else:
                        node.head = self.parse_inline(node.head)

                if node.body:
                    if not node.body.child_nodes.is_empty():
                        self.parse_node_inline(node.body)
                    else:
                        node.body = self.parse_inline(node.body)

        return root


    def _map_parts(self, node, code, match_obj, part_names, open_end=False):
        """Map the match groups to node parts."""
        index_last = 0
        for index, part_name in enumerate(part_names, 1):
            if part_name is None: # nested
                continue
            if open_end and index == len(part_names):
                code_part = code.slice(code.loc_to_abs(match_obj.end(index_last)), after_inner=True)
            else:
                if match_obj.group(index) is None:
                    continue
                code_part = code.slice_match(match_obj, index, True)
            node.append_part(part_name, code_part)
            index_last = index
        return node


    # -- Block ---------------------------------------------------------------

    def document(self, filename=None, text=None, code=None):
        if filename is None and text is None and code is None:
            print("RST document missing parameter")
            return None

        if code is None:
            code = Fragment(filename, text)
        new_node = NodeRST("document", code)
        new_node.append_part("body", code)
        return new_node


    def transition(self, node, line, line_info):
        if not node.active:
            if line_info["is_block_start"]:
                if m := re.match(self.re_lib["trans"][0], line_info["line_str"]):
                    new_node = NodeRST("trans", line)
                    new_node = self._map_parts(new_node, line, m, self.re_lib["trans"][1])
                    node.active = new_node

        elif line_info["is_blank"]:
            node.active.name_start.append_code(line)
            node.append_child(node.active)
            node.active = None

        return node


    def section(self, node, line, line_info):
        if node.active:
            if node.active.node_name == "trans":
                if line_info["is_block_end"]:
                    node.append_child(node.active)
                    node.active = None
                    return node
                if not re.match(self.re_lib["trans"][0], line_info["line_str_next"]):
                    # only if short overline else warn
                    node.active.node_name = "text"
                    node.active.body = node.active.name_start
                    node.active.body.node_name = "body"
                    node.active.name_start = None
                    return node

                node.active.append_part("name", line, True)
                node.active.node_name = "sect"

            elif node.active.node_name in {"text", "sect"}:
                if (not line_info["indented"] and
                        re.match(self.re_lib["trans"][0], line_info["line_str"])):
                    node.active.node_name = "sect"
                    if node.active.body:
                        # move inside node
                        node.active.name = node.active.body
                        node.active.name.node_name = "name"
                        node.active.body = None
                    node.active.append_part("name_end", line, True)

                elif node.active.node_name == "sect":
                    if line_info["is_blank"]:
                        node.active.name_end.append_code(line)
                    else:
                        self.warning(line, "section missing blank line")

                    node.append_child(node.active)
                    node.active = None

        return node


    def paragraph(self, node, line, line_info):
        if node.active:
            node.active.body.append_code(line)
            if line_info["is_blank"] and not line_info["is_block_end"]:
                node.append_child(node.active)
                node.active = None

        else:
            new_node = NodeRST("text", line)
            ind, after = line.slice((line.start_lincol[0], line_info["ind_cur"]))
            new_node.append_part("indent", ind)
            new_node.append_part("body", after)

            if not line_info["is_blank"] or line_info["is_block_end"]:
                node.active = new_node
            else:
                node.append_child(new_node)
                if node.active:
                    node.append_child(node.active)
                node.active = None

        return node


    def doctest(self, node, line, line_info):
        if not node.active:
            if line_info["is_block_start"]:
                if m := re.match(self.re_lib["doctest"][0], line_info["line_str"]):
                    new_node = NodeRST("doctest", line)
                    new_node = self._map_parts(new_node, line, m, self.re_lib["doctest"][1], True)
                    node.active = new_node
        else:
            node.active.body.append_code(line)
            if line_info["is_blank"]:
                node.append_child(node.active)
                node.active = None

        return node


    def def_list(self, node, line, line_info):
        if (not line_info["indented"] and not line_info["is_blank"]) or not node.active:
            if node.active and node.active.node_name != "text":
                if node.active and node.active.node_name != "def":
                    if node.parent_node and node.parent_node.node_name == "def-list":
                        active = node.active
                        node = node.parent_node.parent_node
                        if node.active:
                            self.warning(line, "wrong def start")
                        else:
                            node.active = active

                elif node.parent_node and node.parent_node.node_name == "def-list":
                    node.append_child(node.active)
                    node.active = None
                    if node.parent_node:
                        node = node.parent_node.parent_node

        else:
            if node.active:
                if node.active.node_name == "text" and not line_info["is_blank"]:
                    # only def node in def-list
                    # is_block_start info is lost with the text node
                    if node.node_name != "def-list":
                        if (not node.child_nodes.is_empty() and
                                node.child_nodes.last().node_name == "def-list"):
                            prime = node.child_nodes.last()
                        else:
                            prime = NodeRST("def-list", None)
                            prime.append_part("indent", node.active.indent.code.copy().clear(True))
                            prime.append_part("body", None)
                            node.append_child(prime)

                        new_node = node.active
                        node.active = None
                        node = prime.body
                        node.active = new_node

                    node.active.node_name = "def"
                    node.active.head = node.active.body
                    node.active.head.node_name = "head"
                    node.active.append_part("body", line, True)


                elif node.active.node_name == "def":
                    node.active.body.append_code(line)
                elif node.node_name == "def-list":
                    active = node.active
                    if node.parent_node:
                        node = node.parent_node.parent_node
                    if node.active:
                        self.warning(line, "wrong def start")
                    else:
                        node.active = active

            # > else block quote

        return node


    def block_quote(self, node, line, line_info):
        if line_info["indented"]:
            if node.active and node.active.node_name == "block-quote":
                if (line_info["is_blank"] and line_info["is_block_start"] and
                        not line_info["is_block_end"]):
                    node.append_child(node.active)
                    node.active = None
                    node = self.paragraph(node, line, line_info)
                else:
                    node.active.body.append_code(line)

            elif not node.active:
                new_node = NodeRST("block-quote", line)
                ind, after = line.slice((line.start_lincol[0], line_info["block_ind"]))
                new_node.append_part("indent", ind)
                new_node.append_part("body", after)
                node.active = new_node

        else:
            if node.active:
                node.append_child(node.active)
            node.active = None

        return node


    def listing(self, node, line, line_info):
        recorder = ("field", "bullet", "enum", "line", "option")
        if node.active and node.active.node_name in recorder:
            recorder = (node.active.node_name,)
        if (not line_info["indented"] and not line_info["is_blank"]) or not node.active:
            for name in recorder:
                if m := re.match(self.re_lib[name][0], line_info["line_str"]):
                    break
            else:
                if len(recorder) == 1:
                    node.append_child(node.active)
                    node.active = None
                    if node.parent_node.parent_node:
                        node = node.parent_node.parent_node
                return node

            new_node = NodeRST(name, line)
            new_node = self._map_parts(new_node, line, m, self.re_lib[name][1], True)

            if line_info["is_block_start"]:
                if node.parent_node.node_name != new_node.node_name + "-list":
                    prime = NodeRST(new_node.node_name + "-list", None)
                    prime.append_part("indent", new_node.indent.code.copy().clear(True))
                    prime.append_part("body", None)
                    node.append_child(prime)
                    node = prime.body

            if node.active:
                node.append_child(node.active)
            node.active = new_node

        elif node.active and node.active.node_name in recorder:
            node.active.body.append_code(line)

        return node


    def explicit_block(self, node, line, line_info):
        def factory(line, line_info, starter_m):
            is_anon_target = bool(str(starter_m.group(2)).startswith("__"))
            for name in ("target-anon", "substdef", "footdef", "citdef", "target", "dir"):
                if m := re.match(self.re_lib[name][0], line_info["line_str"]):
                    new_node = NodeRST(self._key_node_name.get(name, name), line)
                    new_node = self._map_parts(new_node, line, m, self.re_lib[name][1], True)
                    new_node.active = new_node.head
                    return new_node
                elif is_anon_target:
                    return

            new_node = NodeRST("comment", line)
            new_node = self._map_parts(new_node, line, starter_m, self.re_lib["comment"][1], True)
            new_node.active = new_node.body
            return new_node


        def quoted(node, line, line_info):
            if (not line_info["is_blank"] and
                    re.match(self.re_lib["quoted"], line_info["line_str"])):
                node.active.body.append_code(line)
            else:
                node.append_child(node.active)
                node.active = None

            return node

        is_text = bool(node.active and node.active.node_name == "text")
        if (((not line_info["indented"] and not line_info["is_blank"]) or not node.active) and
                (not is_text or line_info["is_block_end"])):

            if node.active and not is_text:
                if node.active.node_name == "dir" and node.active.name is None:
                    node = quoted(node, line, line_info)
                else:
                    if node.active:
                        node.append_child(node.active)
                    node.active.active = None
                    node.active = None
                return node

            if starter_m := re.match(self.re_lib["expl"], line_info["line_str"]):
                new_node = factory(line, line_info, starter_m)
            else:
                if starter_m := re.search(self.re_lib["dftdir"][0], line_info["line_str"]):
                    new_node = NodeRST("dir", None)
                    new_node = self._map_parts(new_node, line, starter_m,
                                               self.re_lib["dftdir"][1], True)
                    new_node.active = NodePartRST("body", None)
                    if starter_m.start(0) != 0:
                        if node.active and not is_text:
                            node.append_child(node.active)
                            node.active.active = None
                            node.active = None
                        self.paragraph(node, line.slice(
                            end=line.loc_to_abs(starter_m.start(2)), after_inner=True),
                            line_info)

                    if node.active:
                        node.append_child(node.active)
                        node.active.active = None
                        node.active = None

                else:
                    return node

            if node.active:
                node.append_child(node.active)
            node.active = new_node


        elif node.active and not is_text:
            if node.active.active.node_name == "head":
                if not line_info["is_blank"]:
                    if re.match(self.re_lib["field"][0], line_info["line_str"]):
                        node.active.append_part("attr", line, True)
                        node.active.active = node.active.attr
                        return node

                if not node.active.head:
                    node.active.head = node.active.active
                    node.active.child_nodes.append(node.active.head)
                    node.active.head.append_code(line)
                else:
                    node.active.head.append_code(line)

                if line_info["is_blank"]:
                    if node.active.node_name != "target":
                        node.active.active = NodePartRST("body", None)
                    else:
                        node.append_child(node.active)
                        node.active.active = None
                        node.active = None
                    return node

            elif node.active.active.node_name == "attr":
                node.active.attr.append_code(line)

                if line_info["is_blank"]:
                    node.active.active = NodePartRST("body", None)

            elif node.active.active.node_name == "body":
                if not node.active.body:
                    node.active.body = node.active.active
                    node.active.child_nodes.append(node.active.body)
                    node.active.body.append_code(line)
                else:
                    node.active.body.append_code(line)

        return node


    def grid_table(self, node, line, line_info):
        def row_sep(active, line, top_bottom):
            row = active.active.active
            # double sep
            is_new = False
            if (not row or (not row.body.child_nodes.is_empty() and
                            row.body.child_nodes.first().name_end)):
                row = NodeRST("row", line)
                row.append_part("body", line)
                active.active.active = row
                is_new = True

            col_prev = None
            new_cell = row.body.child_nodes.first()
            is_first = True
            for split_m in re.finditer(r"(\+)([-=])?", line_info["line_str"]):
                if col_prev is None:
                    col_prev = split_m.start(1)
                    continue
                border = line.slice(line.loc_to_abs(col_prev),
                                    line.loc_to_abs(split_m.start(1)), True)
                if not split_m.group(2):
                    after = line.slice(line.loc_to_abs(split_m.start(1)), after_inner=True)
                    border.combine(after)

                if is_first:
                    before = line.slice(end=line.loc_to_abs(col_prev), after_inner=True)
                    border = before.combine(border)
                    is_first = False

                if top_bottom or is_new:
                    new_cell = NodeRST("cell", FragmentBundle([border]))
                else:
                    if split_m.start(0) >= new_cell.body_end.code.end_lincol[1]:
                        new_cell = new_cell.next

                if top_bottom:
                    new_cell.append_part("name_start", border)
                    row.body.append_child(new_cell, False)
                else:
                    if is_new:
                        row.body.append_child(new_cell, False)
                    new_cell.append_part("name_end", border, True)

                col_prev = split_m.start(1)

            if not top_bottom:
                row.body.append_code(line)


        def cell(active, line):
            table_def = (active.head.child_nodes.first() if not active.head.child_nodes.is_empty()
                         else active.head.active)
            row = active.active.active
            if (not row or (not row.body.child_nodes.is_empty() and
                            row.body.child_nodes.first().name_end)):
                row = NodeRST("row", line)
                row.append_part("body", line)
                active.active.active = row
                is_new = True
            else:
                row.body.append_code(line)
                is_new = False

            def_start = table_def.body.child_nodes.first()
            new_cell = row.body.child_nodes.first()
            for def_end in table_def.body.child_nodes:
                col_start = line.loc_to_abs(def_start.name_start.code.start_lincol[1])
                col_end = line.loc_to_abs(def_end.name_start.code.end_lincol[1])
                is_last = bool(not def_end.next)
                if not def_start.prev:
                    first_m = re.search(r"(\s|\A)\+", str(def_start.name_start.code))
                    col_start = line.loc_to_abs(def_start.name_start.code
                                                .loc_to_abs((0, first_m.end(0)))[1])
                if is_last:
                    last_m = re.search(r"\+(\s|\Z)", str(def_end.name_start.code))
                    col_end = line.loc_to_abs(def_end.name_start.code
                                              .loc_to_abs((0, last_m.start(0)))[1])

                border_right = line.slice(col_end, col_end + 1, True)
                if str(border_right) not in {"", "+", "|", "\n"} and not is_last:
                    continue

                code = line.slice(col_start + 1, col_end, True)
                code_str = str(code)
                if re.search(r"(?!\\)\\\Z", code_str) and not is_last:
                    continue

                left, inner, right = code.slice_match(re.match(r"\s*(.*?)\s*\Z", code_str), 1)
                if is_new:
                    new_cell = NodeRST("cell", FragmentBundle([code]))
                    row.body.append_child(new_cell, False)
                else:
                    new_cell.append_code(code)

                if is_last:
                    after = line.slice(border_right.end_pos, after_inner=True)
                    border_right.combine(after)
                if not new_cell.body:
                    new_cell.append_part("body_start", left)
                    new_cell.append_part("body", inner)
                    new_cell.append_part("body_end", right.combine(border_right))
                else:
                    new_cell.body_start.code.combine(left)
                    new_cell.body.code.combine(inner)
                    new_cell.body_end.code.combine(right.combine(border_right))
                new_cell = new_cell.next
                def_start = def_start.next

        if not node.active or node.active.node_name != "grid-table":
            if m := re.match(self.re_lib["grid_border"], line_info["line_str"]):
                new_node = NodeRST("row", line)
                _, ind, after = line.slice_match(m, 1)
                new_node.append_part("indent", ind)
                new_node.append_part("body", after)

                prime = NodeRST("grid-table", None)
                prime.append_part("indent", new_node.indent.code.copy().clear(True))
                prime.append_part("head", None)
                prime.head.active = new_node

                if node.active:
                    node.append_child(node.active)
                node.active = prime
                node.active.active = prime.head

                row_sep(node.active, line, True)
        else:
            if node.active.active.node_name == "head":
                if re.match(self.re_lib["grid_head_border"], line_info["line_str"]):
                    row_sep(node.active, line, False)
                    node.active.active.append_child(node.active.active.active)
                    node.active.append_part("body", None)
                    node.active.active = node.active.body
                elif re.match(self.re_lib["grid_border"], line_info["line_str"]):
                    row_sep(node.active, line, False)
                    node.active.active.append_child(node.active.active.active)
                    if line_info["is_block_end"]:
                        # body only
                        node.active.body = node.active.head
                        node.active.head.node_name = "body"
                        node.active.body = None
                        line_info["is_blank"] = True
                        node.append_child(node.active)
                        node.active = None
                else:
                    cell(node.active, line)
            elif node.active.active.node_name == "body":
                if not re.match(self.re_lib["grid_border"], line_info["line_str"]):
                    cell(node.active, line)
                else:
                    row_sep(node.active, line, False)
                    node.active.active.append_child(node.active.active.active)
                    if line_info["is_block_end"]:
                        line_info["is_blank"] = True
                        node.append_child(node.active)
                        node.active = None

        return node


    def simple_table(self, node, line, line_info):
        def row_sep(active, line, top_bottom):
            row = active.active.active
            col_prev = row.body.code.start_lincol[1]
            new_cell = row.body.child_nodes.first()
            for split_m in re.finditer(r"\s+", line_info["line_str"]):
                if col_prev == 0 and split_m.start() == 0:
                    continue
                border = line.slice(line.loc_to_abs(col_prev),
                                    line.loc_to_abs(split_m.start(0)), True)
                if top_bottom:
                    new_cell = NodeRST("cell", FragmentBundle([border]))
                else:
                    if split_m.start(0) >= new_cell.body_end.code.end_lincol[1]:
                        new_cell = new_cell.next
                if top_bottom:
                    new_cell.append_part("name_start", border)
                    row.body.append_child(new_cell, False)
                else:
                    new_cell.append_part("name_end", border, True)
                col_prev = split_m.end(0)

            if not top_bottom:
                row.body.append_code(line)


        def cell(active, line):
            table_def = (active.head.child_nodes.first() if not active.head.child_nodes.is_empty()
                         else active.head.active)
            row = active.active.active
            if (not row or (not row.body.child_nodes.is_empty() and
                            row.body.child_nodes.first().body)):
                row = NodeRST("row", line)
                row.append_part("body", line)
                active.active.active = row
                is_new = True
            else:
                row.body.append_code(line)
                is_new = False

            def_start = table_def.body.child_nodes.first()
            new_cell = row.body.child_nodes.first()
            for def_end in table_def.body.child_nodes:
                col_end = line.loc_to_abs(def_end.name_start.code.end_lincol[1])
                is_last = bool(not def_end.next)
                if not is_last:
                    border_right = line.slice(col_end, col_end + 1, True)
                else:
                    border_right = line.copy().clear(False)
                if str(border_right) not in {"", " ", "\n"} and not is_last:
                    continue

                if is_last:
                    col_end = None
                code = line.slice(line.loc_to_abs(def_start.name_start.code
                                                  .start_lincol[1]), col_end, after_inner=True)
                code_str = str(code)
                if re.search(r"(?!\\)\\\Z", code_str) and not is_last:
                    continue

                left, inner, right = code.slice_match(re.match(r"\s*(.*?)\s*\Z", code_str), 1)
                if is_new:
                    new_cell = NodeRST("cell", FragmentBundle([code]))
                    row.body.append_child(new_cell, False)
                else:
                    new_cell.append_code(code)

                if not new_cell.body:
                    new_cell.append_part("body_start", left)
                    new_cell.append_part("body", inner)
                    new_cell.append_part("body_end", right.combine(border_right))
                else:
                    new_cell.body_start.code.combine(left)
                    new_cell.body.code.combine(inner)
                    new_cell.body_end.code.combine(right.combine(border_right))
                new_cell = new_cell.next
                def_start = def_start.next

        if not node.active or node.active.node_name != "simple-table":
            if m := re.match(self.re_lib["simple_row_border"], line_info["line_str"]):
                new_node = NodeRST("row", line)
                _, ind, after = line.slice_match(m, 1)
                new_node.append_part("indent", ind)
                new_node.append_part("body", after)

                prime = NodeRST("simple-table", None)
                prime.append_part("indent", new_node.indent.code.copy().clear(True))
                prime.append_part("head", None)
                prime.head.active = new_node

                if node.active:
                    node.append_child(node.active)
                node.active = prime
                node.active.active = prime.head

                row_sep(node.active, line, True)
        else:
            if node.active.active.node_name == "head":
                if re.match(self.re_lib["simple_row_border"], line_info["line_str"]):
                    row_sep(node.active, line, False)
                    node.active.active.append_child(node.active.active.active)
                    if not line_info["is_block_end"]:
                        node.active.append_part("body", None)
                        node.active.active = node.active.body
                    else:
                        # body only
                        node.active.body = node.active.head
                        node.active.head.node_name = "body"
                        node.active.body = None
                        line_info["is_blank"] = True
                        node.append_child(node.active)
                        node.active = None

                elif not re.match(self.re_lib["simple_column_span"], line_info["line_str"]):
                    if (node.active.active.active and
                            not node.active.active.active.body.child_nodes.is_empty() and
                            node.active.active.active.body.child_nodes.first().body):
                        node.active.active.append_child(node.active.active.active)
                    cell(node.active, line)
                else:
                    self.warning(line, "simple table column span not implemented")
            elif node.active.active.node_name == "body":
                if not re.match(self.re_lib["simple_row_border"], line_info["line_str"]):
                    if node.active.active.active:
                        node.active.active.append_child(node.active.active.active)
                    cell(node.active, line)
                else:
                    row_sep(node.active, line, False)
                    node.active.active.append_child(node.active.active.active)
                    line_info["is_blank"] = True
                    node.append_child(node.active)
                    node.active = None

        return node


    # -- Inline --------------------------------------------------------------

    def inline(self, node, code, name):
        if m := re.search(self.re_lib[name][0], str(code)):
            before, inner, after = node.active.body.code.slice_match(m, 0)
            node.active.body.code = before
            node.active.code = before

            new_node = NodeRST(self._key_node_name.get(name, name), inner)
            new_node = self._map_parts(new_node, code, m, self.re_lib[name][1])
            node.child_nodes.insert_after(node.active, new_node)

            if ((new_node.node_name == "hyperlink" and new_node.body) or
                    (new_node.node_name == "role" and new_node.name)):
                new_node = self.interpret_inline(new_node)
            new_node.is_parsed = True

            node_after = NodeRST("text", after)
            node_after.append_part("body", after)
            node.child_nodes.insert_after(new_node, node_after)
            node.active = node_after
        else:
            node.active = node.active.next
        return node


    def interpret_inline(self, node):
        name_str = None
        sub_name = None
        if node.node_name == 'hyperlink':
            sub_name = "link"
        else:
            name_str = str(node.name.code).strip()
            if name_str in {'doc', 'ref', 'term', 'any', 'download', 'numref'}:
                sub_name = "link"
            elif name_str == 'abbr':
                sub_name = "parenthesis"

        if sub_name is not None:
            sub_node = self.parse_inline(node.body, sub_name)

            if len(sub_node.child_nodes) > 1 and sub_node.child_nodes[1].node_name == sub_name:
                node.head = node.body
                node.head.node_name = "head"
                node.head.code = sub_node.child_nodes.first().body.code

                id_node = sub_node.child_nodes[1]
                node.insert_part("id_start", id_node.body_start.code, node.head)
                node.insert_part("id", id_node.body.code, node.id_start)
                node.insert_part("id_end", id_node.body_end.code, node.id)

                node.head.child_nodes = LinkedList(node.head)
                node.body = None
                if id_node.next and id_node.next.body:
                    if len(id_node.next.body.code) != 0:
                        node.insert_part("body", id_node.next.body.code, node.id_end)
                    if id_node.next.next:
                        self.warning(id_node.next.next.code, "inline body unexpected content")

            else:
                if name_str is None or name_str not in {"term", "abbr"}:
                    node.id = node.body
                    node.id.node_name = "id"
                    node.id.child_nodes = LinkedList(node.id)
                else:
                    node.head = node.body
                    node.head.node_name = "head"
                    node.head.child_nodes = LinkedList(node.head)
                node.body = None

        elif name_str in {"class", "func", "index", "mod", "meth"}:
            node.id = node.body
            node.id.node_name = "id"
            node.id.child_nodes = LinkedList(node.id)

        return node
