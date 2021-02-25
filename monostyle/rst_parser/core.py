
"""
rst_parser.core
~~~~~~~~~~~~~~~

A RST parser.
"""

import re
from monostyle.util.fragment import Fragment, FragmentBundle
from monostyle.util.nodes import LinkedList
from monostyle.rst_parser.rst_node import NodeRST, NodePartRST

class RSTParser:

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
        'file', 'guilabel', 'index', 'kbd', 'keyword', 'mailheader', 'makevar',
        'manpage', 'math', 'menuselection', 'mimetype', 'mod', 'newsgroup',
        'numref', 'option', 'pep', 'program', 'ref', 'regexp', 'rfc', 'samp',
        'sub', 'sup', 'term', 'token'
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


    def _compile_re_lib(self):
        re_lib = dict()

        # Block
        ind = r"( *)"
        re_lib["ind"] = re.compile(ind + r"\S")
        space_end = r"(?: +|(?=\n)|\Z)"
        eol_end = r" *(?:\n)|\Z)"

        ref_name = r"(?:(?!_)\w)+(?:[-._+:](?:(?!_)\w)+)*"
        foot_name = "".join((r"(?:\d+)|[", "".join(self.foot_chars), r"]|(?:#", ref_name, r")"))
        mid_a = r"(\S.*?(?<![\s\\"
        mid_b = r"]))"
        option_arg = r"(?:[-/]\w|\-\-\w[\w-]+(?:[ =][\w.;:\\/\"'-]+)?)"
        expl = ''.join((ind, r"(\.\.", space_end, r")"))
        direc = ''.join((r"(", ref_name, r")(\:\:", space_end, r")"))

        blocks = (
            ("trans", (ind, r"(([", r''.join(map(re.escape, self.trans_chars)), r"])\3*",
                       eol_end)),
            ("bullet", (ind, r"([", r''.join(map(re.escape, self.bullet_chars)), r"]",
                        space_end, r")")),
            ("enum", (ind, r"(\()?([#\w]|\d+)([\.\)]", space_end, r")")),
            ("line", (ind, r"(\|", space_end, r")")),
            ("field", (ind, r"(\:(?!", ref_name, r"\:`))([^:].*?)((?<!\\)\:", space_end, r")")),
            ("option", (ind, r"(", option_arg, r"(?:, ", option_arg, r")*)( ", space_end, ")")),

            ("expl", (ind, r"((?:\.\.|__)", space_end, r")")),
            ("dftdir",(r"(\A *)?(?<![^\\]\\)(\:\:", space_end, ")")),
            ("dir", (expl, direc)),
            ("substdef", (expl, r"(\|)(", ref_name, r")(\|\s+)(?:", direc, r")?")),
            ("footdef", (expl, r"(\[)(", foot_name, r")(\]", space_end, r")")),
            ("citdef", (expl, r"(\[)(", ref_name, r")(\]", space_end, r")")),
            ("target", (expl, r"(_ *)(`)?(?(4)(?:((?:[^`]*?[^\\", mid_b, r"(`))|",
                        mid_a, mid_b, r")", r"(\:", space_end, r")")),
            ("target-anon", (expl, r"?(__ *)(\:", space_end, r")?")),
            ("quoted", (ind, r"[", r''.join(map(re.escape, self.trans_chars)), r"]")),
            ("doctest", (ind, r">>>\s")),

            ("grid_border", (ind, r"((?:\+\-+?)*\+\-+\+", eol_end)),
            ("grid_row_frame", (ind, r"[+|].+[+|]", space_end)),
            ("grid_cell_border", (r"[\+-]\Z",)),
            ("grid_head_border", (ind, r"((?:\+=+?)*\+=+\+", eol_end)),
            ("simple_row_border", (ind, r"((?:=+?\s+)*=+", eol_end)),
            ("simple_column_span", (ind, r"((?:\-+?\s+)*\-+", eol_end)),
        )
        for name, pattern_str in blocks:
            re_lib[name] = re.compile(''.join(pattern_str))

        # Inline
        before_a = r"(?:(?<=[^\w\\"
        before_b = r"])|\A)"
        after_a = r"(?:(?=[^\w"
        after_b = r"])|\Z)"
        url_chars = r"[-_.!~*'()[\];/:&=+$,%a-zA-Z0-9]"
        url = r"(?:\\[*_])?" + url_chars + r"*\b(?:\\[*_]" + url_chars + r"*)*"

        inlines = {
            ("literal", r"`", r"``", True, r"", r"``", r"`"),
            ("strong", r"\*", r"\*\*", True, r"*", r"\*\*", r"\*"),
            ("emphasis", r"\*", r"\*", True, r"*", r"\*", r"\*"),
            ("subst", "", r"\|", True, r"\|", r"\|_{0,2}", ""),
            ("int-target", "", r"_`", True, "", r"`", r"`"),
            ("dftrole", r"_:`", r"`", True, r"`", r"`", r"`"),
            ("hyperlink", r"`:_", r"`", True, r"`", r"`__?", ""),
            ("role-ft", "", r"\:)(" + ref_name + r")(\:)(`", True, "", r"`", ""),
            ("role-bk", "", r"`", True, "", r"`)(\:)(" + ref_name + r")(\:", ""),
            ("foot", "", r"\[", False, foot_name, r"\]_", ""),
            ("cit", "", r"\[", False, ref_name, r"\]_", ""),
            ("int-target-sw", "", r"_(?!_)", False, ref_name, "", ""),
            ("hyperlink-sw", "", "", False, ref_name, r"_(?!_)", ""),
            ("standalone", r"", "", False, r"\b(?<!\\)(?:https?\:\/\/|mailto\:)" + url, "", ""),
            ("mail", r"<`/", "", False, r"\b" + url + r"(?<!\\)@" + url + r"\." + url, "", ""),
            ("link", "", r"<", True, "", r">", ""),
            ("parenthesis", "", r"\(", True, "", r"\)", "")
            # ("arrow", r"-", "", False, r"\-{1,2}>", "", "")
            # ("dash", r"-", "", False, r"\-{2,3}", "", "")
        }
        for name, before_no, start, is_dot_mid, mid, end, after_no in inlines:
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
            re_lib[name] = re.compile(''.join(pattern_str), re.DOTALL)

        return re_lib


    # -----------------------------------------------------------------------------


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

            if m := re.match(ind_re, line_str):
                ind_abs = line.loc_to_abs((0, m.end(1)))[1]
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


            recorder = (({"block-quote",}, self.block_quote),
                        ({"field",}, self.field),
                        ({"bullet", "enum"}, self.be_list),
                        ({"line",}, self.line_block),
                        ({"option",}, self.option),
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
                if node.parent_node.node_name.endswith("-list") and root.active:
                    root.append_child(root.active)
            else:
                root.append_child(node.active)

        return root


    def parse_inline(self, node, name=None):
        new_node = NodeRST("text", node.code)
        new_node.append_part("body", node.code)
        node.child_nodes.append(new_node)

        recorder = ((("literal", "strong", "emphasis", "int-target"), self.inline),
            (("role-ft", "role-bk"), self.role),
            (("hyperlink", "dftrole", "subst", "foot", "cit"), self.inline),
            (("standalone", "mail", "int-target-sw", "hyperlink-sw"), self.single))
        if name:
            for names, node_typ in recorder:
                if name in names:
                    recorder = (((name,), node_typ),)
                    break
            else:
                recorder = (((name,), self.inline),)

        for names, node_typ in recorder:
            for name in names:
                node.is_parsing = True
                node.active = node.child_nodes.first()
                while node.active:
                    split = False
                    if not node.active.is_parsed and node.active.body:
                        node, split = node_typ(node, node.active.body.code, name)

                    if not split or node.active.is_parsed:
                        if name == node.active.node_name:
                            print("{0}:{1}: unclosed inline (within paragraph)"
                                  .format(node.active.code.filename,
                                          node.active.code.start_lincol[0]))

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


    # -----------------------------------------------------------------------------
    # Block

    def document(self, filename, text):
        fg = Fragment(filename, text)
        new_node = NodeRST("document", fg)
        new_node.append_part("body", fg)
        return new_node


    def snippet(self, fg):
        new_node = NodeRST("snippet", fg)
        new_node.append_part("body", fg)
        return new_node


    def transition(self, node, line, line_info):
        if not node.active:
            if line_info["is_block_start"]:
                if m := re.match(self.re_lib["trans"], line_info["line_str"]):
                    new_node = NodeRST("trans", line)
                    new_node.append_part("indent", line.slice_match_obj(m, 1, True))
                    new_node.append_part("name_start", line.slice_match_obj(m, 2, True))
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
                if not re.match(self.re_lib["trans"], line_info["line_str_next"]):
                    # only if short overline else warn
                    node.active.node_name = "text"
                    node.active.indent.code.combine(node.active.name_start.code)
                    node.active.body = node.active.indent
                    node.active.body.node_name = "body"
                    node.active.indent = None
                    node.active.name_start = None
                    return node

                node.active.append_part("name", line, True)
                node.active.node_name = "sect"

            elif node.active.node_name in {"text", "sect"}:
                if not line_info["indented"] and re.match(self.re_lib["trans"], line_info["line_str"]):
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
                        print("{0}:{1}: {2}".format(line.filename, line.start_lincol[0],
                                                    "section missing blank line"))

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
                if m := re.match(self.re_lib["doctest"], line_info["line_str"]):
                    new_node = NodeRST("doctest", line)
                    ind, after = line.slice(line.loc_to_abs(m.end(1)))
                    new_node.append_part("indent", ind)
                    new_node.append_part("body", after)
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
                            print("{0}:{1}: {2}".format(line.filename, line.start_lincol[0],
                                                        "wrong def start"))
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
                        print("{0}:{1}: {2}".format(line.filename, line.start_lincol[0],
                                                    "wrong def start"))
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


    def be_list(self, node, line, line_info):
        if (not line_info["indented"] and not line_info["is_blank"]) or not node.active:
            if m := re.match(self.re_lib["bullet"], line_info["line_str"]):
                new_node = NodeRST("bullet", line)
                new_node.append_part("indent", line.slice_match_obj(m, 1, True))
                _, fg, after_name = line.slice_match_obj(m, 2)
                new_node.append_part("name_start", fg)
                new_node.append_part("body", after_name)

            else:
                if m := re.match(self.re_lib["enum"], line_info["line_str"]):
                    new_node = NodeRST("enum", line)
                    new_node.append_part("indent", line.slice_match_obj(m, 1, True))
                    if m.group(2):
                        new_node.append_part("name_start", line.slice_match_obj(m, 2, True))
                    new_node.append_part("name", line.slice_match_obj(m, 3, True))
                    _, fg, after_name = line.slice_match_obj(m, 4)
                    new_node.append_part("name_end", fg)
                    new_node.append_part("body", after_name)

                else:
                    if node.active and node.active.node_name in {"bullet", "enum"}:
                        node.append_child(node.active)
                        node.active = None
                        if node.parent_node.parent_node:
                            node = node.parent_node.parent_node
                    return node

            if line_info["is_block_start"]:
                # different list type after another
                if node.active and node.active.node_name != new_node.node_name:
                    node.append_child(node.active)
                    node.active = None
                    node = node.parent_node.parent_node

                if node.parent_node.node_name != new_node.node_name + "-list":
                    prime = NodeRST(new_node.node_name + "-list", None)
                    prime.append_part("indent", new_node.indent.code.copy().clear(True))
                    prime.append_part("body", None)
                    node.append_child(prime)
                    node = prime.body

            if node.active:
                node.append_child(node.active)
            node.active = new_node

        elif node.active and node.active.node_name in {"bullet", "enum"}:
            node.active.body.append_code(line)

        return node


    def line_block(self, node, line, line_info):
        if (not line_info["indented"] and not line_info["is_blank"]) or not node.active:
            if m := re.match(self.re_lib["line"], line_info["line_str"]):
                new_node = NodeRST("line", line)
                new_node.append_part("indent", line.slice_match_obj(m, 1, True))
                _, fg, after_name = line.slice_match_obj(m, 2)
                new_node.append_part("name_start", fg)
                new_node.append_part("body", after_name)

                if line_info["is_block_start"] and node.parent_node.node_name != "line-list":
                    prime = NodeRST(new_node.node_name + "-list", None)
                    prime.append_part("indent", new_node.indent.code.copy().clear(True))
                    prime.append_part("body", None)
                    node.append_child(prime)
                    node = prime.body

                if node.active:
                    node.append_child(node.active)
                node.active = new_node

            elif node.active and node.active.node_name == "line":
                node.append_child(node.active)
                node.active = None
                if node.parent_node:
                    node = node.parent_node.parent_node

        elif node.active and node.active.node_name == "line":
            node.active.body.append_code(line)

        return node


    def field(self, node, line, line_info):
        if (not line_info["indented"] and not line_info["is_blank"]) or not node.active:
            if m := re.match(self.re_lib["field"], line_info["line_str"]):
                new_node = NodeRST("field", line)
                new_node.append_part("indent", line.slice_match_obj(m, 1, True))
                new_node.append_part("name_start", line.slice_match_obj(m, 2, True))
                new_node.append_part("name", line.slice_match_obj(m, 3, True))
                _, fg, after_name = line.slice_match_obj(m, 4)
                new_node.append_part("name_end", fg)
                new_node.append_part("body", after_name)

                if line_info["is_block_start"] and node.parent_node.node_name != "field-list":
                    prime = NodeRST(new_node.node_name + "-list", None)
                    prime.append_part("indent", new_node.indent.code.copy().clear(True))
                    prime.append_part("body", None)
                    node.append_child(prime)
                    node = prime.body

                if node.active:
                    node.append_child(node.active)
                node.active = new_node

            elif node.active and node.active.node_name == "field":
                node.append_child(node.active)
                node.active = None
                if node.parent_node:
                    node = node.parent_node.parent_node

        elif node.active and node.active.node_name == "field":
            node.active.body.append_code(line)

        return node


    def option(self, node, line, line_info):
        if (not line_info["indented"] and not line_info["is_blank"]) or not node.active:
            if m := re.match(self.re_lib["option"], line_info["line_str"]):
                new_node = NodeRST("option", line)
                new_node.append_part("indent", line.slice_match_obj(m, 1, True))
                new_node.append_part("name", line.slice_match_obj(m, 2, True))

                if m.group(3).startswith(" "):
                    new_node.append_part("name_end", line.slice_match_obj(m, 3, True))
                    new_node.append_part("body", line.slice(line.loc_to_abs(m.end(3)),
                                                           after_inner=True))
                else:
                    new_node.append_part("body", line.slice(line.loc_to_abs(m.end(2)),
                                                           after_inner=True))

                if line_info["is_block_start"] and node.parent_node.node_name != "option-list":
                    prime = NodeRST(new_node.node_name + "-list", None)
                    prime.append_part("indent", new_node.indent.code.copy().clear(True))
                    prime.append_part("body", None)
                    node.append_child(prime)
                    node = prime.body

                if node.active:
                    node.append_child(node.active)
                node.active = new_node

            elif node.active and node.active.node_name == "option":
                node.append_child(node.active)
                node.active = None
                if node.parent_node:
                    node = node.parent_node.parent_node

        elif node.active and node.active.node_name == "option":
            node.active.body.append_code(line)

        return node


    def explicit_block(self, node, line, line_info):
        def factory(line, line_info, new_node, is_anon_target):
            target_anon_m = re.match(self.re_lib["target-anon"], line_info["line_str"])
            if not (is_anon_target or target_anon_m):
                if sub_m := re.match(self.re_lib["substdef"], line_info["line_str"]):
                    new_node.node_name = "substdef"

                    new_node.append_part("id_start", line.slice_match_obj(sub_m, 3, True))
                    new_node.append_part("id", line.slice_match_obj(sub_m, 4, True))
                    _, fg, after_id = line.slice_match_obj(sub_m, 5)
                    new_node.append_part("id_end", fg)
                    if sub_m.group(5):
                        new_node.append_part("name", line.slice_match_obj(sub_m, 6, True))
                        _, fg, after_name = line.slice_match_obj(sub_m, 7)
                        new_node.append_part("name_end", fg)
                        new_node.append_part("head", after_name)
                    else:
                        new_node.append_part("head", after_id)
                    new_node.active = new_node.head
                    return new_node

                if foot_m := re.match(self.re_lib["footdef"], line_info["line_str"]):
                    new_node.node_name = "footdef"
                    new_node.append_part("id_start", line.slice_match_obj(foot_m, 3, True))
                    new_node.append_part("id", line.slice_match_obj(foot_m, 4, True))
                    _, fg, after_id = line.slice_match_obj(foot_m, 5)
                    new_node.append_part("id_end", fg)
                    new_node.append_part("head", after_id)
                    new_node.active = new_node.head
                    return new_node

                if cit_m := re.match(self.re_lib["citdef"], line_info["line_str"]):
                    new_node.node_name = "citdef"
                    new_node.append_part("id_start", line.slice_match_obj(cit_m, 3, True))
                    new_node.append_part("id", line.slice_match_obj(cit_m, 4, True))
                    _, fg, after_id = line.slice_match_obj(cit_m, 5)
                    new_node.append_part("id_end", fg)
                    new_node.append_part("head", after_id)
                    new_node.active = new_node.head
                    return new_node

                if target_m := re.match(self.re_lib["target"], line_info["line_str"]):
                    new_node.node_name = "target"
                    _, fg, after_id = line.slice_match_obj(target_m, 3)
                    new_node.name_start.code.combine(fg)
                    if target_m.group(4) is not None:
                        # has literal
                        new_node.append_part("id_start", line.slice_match_obj(target_m, 4, True))
                        new_node.append_part("id", line.slice_match_obj(target_m, 5, True))
                        new_node.append_part("id_end", line.slice_match_obj(target_m, 6, True))
                    else:
                        new_node.append_part("id", line.slice_match_obj(target_m, 7, True))

                    _, fg, after_name = line.slice_match_obj(target_m, 8)
                    new_node.append_part("name_end", fg)
                    new_node.append_part("head", after_name)
                    new_node.active = new_node.head
                    return new_node

                if dir_m := re.match(self.re_lib["dir"], line_info["line_str"]):
                    new_node.node_name = "dir"
                    new_node.append_part("name", line.slice_match_obj(dir_m, 3, True))
                    _, fg, after_name = line.slice_match_obj(dir_m, 4)
                    new_node.append_part("name_end", fg)
                    new_node.append_part("head", after_name)
                    new_node.active = new_node.head
                    return new_node

                new_node.node_name = "comment"
                new_node.append_part("body", after_starter)
                new_node.active = new_node.body
                return new_node
            else:
                if target_anon_m:
                    new_node.node_name = "target"
                    if target_anon_m.group(3) is None:
                        _, __, after_id = line.slice_match_obj(target_anon_m, 2)
                    else:
                        _, fg, after_id = line.slice_match_obj(target_anon_m, 3)
                        if target_anon_m.group(2) is not None:
                            # has double dot
                            new_node.name_start.code.combine(fg)
                    if target_anon_m.group(4) is not None:
                        # has double colon
                        _, fg, after_id = line.slice_match_obj(target_anon_m, 4)
                        new_node.append_part("name_end", fg)

                    new_node.append_part("head", after_id)
                    new_node.active = new_node.head
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
                new_node = NodeRST("expl", line)
                new_node.append_part("indent", line.slice_match_obj(starter_m, 1, True))
                _, fg, after_starter = line.slice_match_obj(starter_m, 2)
                new_node.append_part("name_start", fg)
                is_anon_target = bool(str(starter_m.group(2)).startswith("__"))
                new_node = factory(line, line_info, new_node, is_anon_target)

            else:
                if starter_m := re.search(self.re_lib["dftdir"], line_info["line_str"]):
                    new_node = NodeRST("dir", None)
                    if starter_m.group(1):
                        new_node.append_part("indent", line.slice_match_obj(starter_m, 1, True))
                    before_starter, fg, after_starter = line.slice_match_obj(starter_m, 2)
                    new_node.append_part("name_end", fg, True)
                    new_node.append_part("head", after_starter, True)
                    new_node.active = NodePartRST("body", None)
                    if starter_m.start(0) != 0:
                        if node.active and not is_text:
                            node.append_child(node.active)
                            node.active.active = None
                            node.active = None
                        self.paragraph(node, before_starter, line_info)

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
                    if re.match(self.re_lib["field"], line_info["line_str"]):
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
            last = row.body.code.start_lincol[1]
            for index, split_m in enumerate(re.finditer(r"(\+)([-=])?", line_info["line_str"])):
                if index == 0:
                    last = split_m.start(1)
                    continue
                border = line.slice(line.loc_to_abs(last),
                                    line.loc_to_abs(split_m.start(1)), True)
                if not split_m.group(2):
                    after = line.slice(line.loc_to_abs(split_m.start(1)), after_inner=True)
                    border.combine(after)
                if index == 1:
                    before, _ = line.slice(line.loc_to_abs(last))
                    border = before.combine(border)

                if top_bottom:
                    cell_node = NodeRST("cell", FragmentBundle([border]))
                else:
                    cell_node = row.body.child_nodes[index - 1]

                last = split_m.start(1)
                # double sep
                if top_bottom:
                    cell_node.append_part("name_start", border)
                    row.body.append_child(cell_node, False)
                else:
                    cell_node.append_part("name_end", border, True)

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

            for index, cell_def_node in enumerate(table_def.body.child_nodes):
                cols = (line.loc_to_abs(cell_def_node.name_start.code.start_lincol[1]),
                        line.loc_to_abs(cell_def_node.name_start.code.end_lincol[1]))
                is_last = bool(not cell_def_node.next)
                if index == 0:
                    first_m = re.search(r"(\s|\A)\+", str(cell_def_node.name_start.code))
                    cols = (line.loc_to_abs(cell_def_node.name_start.code
                                            .loc_to_abs((0, first_m.end(0)))[1]), cols[1])
                if is_last:
                    last_m = re.search(r"\+(\s|\Z)", str(cell_def_node.name_start.code))
                    cols = (cols[0], line.loc_to_abs(cell_def_node.name_start.code
                                                     .loc_to_abs((0, last_m.start(0)))[1]))

                border_right = line.slice(cols[1], cols[1] + 1, True)
                if str(border_right) in {"", "+", "|", "\n"}:
                    code = line.slice(cols[0] + 1, cols[1], True)
                    trim_m = re.match(r"\s*(.*?)\s*\Z", str(code))
                    left, inner, right = code.slice_match_obj(trim_m, 1)
                    if is_new:
                        new_cell = NodeRST("cell", FragmentBundle([code]))
                        row.body.append_child(new_cell, False)
                    else:
                        new_cell = row.body.child_nodes[index]
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

                else:
                    print("{0}:{1}: grid table columns not conforming"
                          .format(line.filename, line.start_lincol[0]))

        if not node.active or node.active.node_name != "grid-table":
            if m := re.match(self.re_lib["grid_border"], line_info["line_str"]):
                new_node = NodeRST("row", line)
                _, ind, after = line.slice_match_obj(m, 1)
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
            last = row.body.code.start_lincol[1]
            index_offset = 0
            for index, split_m in enumerate(re.finditer(r"\s+", line_info["line_str"])):
                if index == 0 and last == 0 and split_m.start() == 0:
                    index_offset = -1
                    continue
                border = line.slice(line.loc_to_abs(last),
                                    line.loc_to_abs(split_m.start(0)), True)
                if top_bottom:
                    cell_node = NodeRST("cell", FragmentBundle([border]))
                else:
                    cell_node = row.body.child_nodes[index + index_offset]
                last = split_m.end(0)
                # double sep
                if top_bottom:
                    cell_node.append_part("name_start", border)
                    row.body.append_child(cell_node, False)
                else:
                    cell_node.append_part("name_end", border, True)

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

            for index, cell_def_node in enumerate(table_def.body.child_nodes):
                cols = (line.loc_to_abs(cell_def_node.name_start.code.start_lincol[1]),
                        line.loc_to_abs(cell_def_node.name_start.code.end_lincol[1]))
                is_last = bool(not cell_def_node.next)
                if not is_last:
                    border_right = line.slice(cols[1], cols[1] + 1, True)
                else:
                    border_right = line.copy().clear(False)
                if str(border_right) in {"", " ", "\n"}:
                    if not is_last:
                        code = line.slice(cols[0], cols[1], True)
                    else:
                        code = line.slice(cols[0], after_inner=True)
                    trim_m = re.match(r"\s*(.*?)\s*\Z", str(code))
                    left, inner, right = code.slice_match_obj(trim_m, 1)
                    if is_new:
                        new_cell = NodeRST("cell", FragmentBundle([code]))
                        row.body.append_child(new_cell, False)
                    else:
                        new_cell = row.body.child_nodes[index]
                        new_cell.append_code(code)

                    if not new_cell.body:
                        new_cell.append_part("body_start", left)
                        new_cell.append_part("body", inner)
                        new_cell.append_part("body_end", right.combine(border_right))
                    else:
                        new_cell.body_start.code.combine(left)
                        new_cell.body.code.combine(inner)
                        new_cell.body_end.code.combine(right.combine(border_right))

                else:
                    print("{0}:{1}: simple table columns not conforming"
                          .format(line.filename, line.start_lincol[0]))

        if not node.active or node.active.node_name != "simple-table":
            if m := re.match(self.re_lib["simple_row_border"], line_info["line_str"]):
                new_node = NodeRST("row", line)
                _, ind, after = line.slice_match_obj(m, 1)
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


    # -----------------------------------------------------------------------------
    # Inline


    def inline(self, node, code, name):
        split = False

        if node.active.node_name == "text":
            if m := re.search(self.re_lib[name], str(code)):
                fg_before, fg_code, fg_after = node.active.body.code.slice(
                                                    code.loc_to_abs(m.start(1)),
                                                    code.loc_to_abs(m.end(3)))
                node.active.body.code = fg_before
                node.active.code = fg_before

                new_node = NodeRST(name, fg_code)
                new_node.append_part("body_start", code.slice_match_obj(m, 1, True))
                new_node.append_part("body", code.slice_match_obj(m, 2, True))
                if name == "hyperlink":
                    new_node = self.interpret_inline(new_node)
                elif name == "dftrole":
                    new_node.node_name = "role"
                elif name == "subst":
                    new_node.id = new_node.body
                    new_node.id.node_name = "id"
                    new_node.body = None
                new_node.append_part("body_end", code.slice_match_obj(m, 3, True))
                node.child_nodes.insert_after(node.active, new_node)
                new_node.is_parsed = True
                split = True

                text_after = NodeRST("text", fg_after)
                text_after.append_part("body", fg_after)
                node.child_nodes.insert_after(new_node, text_after)
                node.active = text_after

        return node, split


    def role(self, node, code, name):
        split = False

        if node.active.node_name == "text":
            if m := re.search(self.re_lib[name], str(code)):
                fg_before, fg_code, fg_after = node.active.body.code.slice(
                                                    code.loc_to_abs(m.start(0)),
                                                    code.loc_to_abs(m.end(6)))
                node.active.body.code = fg_before
                node.active.code = fg_before

                new_node = NodeRST("role", fg_code)
                if name == "role-ft":
                    new_node.append_part("name_start", code.slice_match_obj(m, 1, True))
                    new_node.append_part("name", code.slice_match_obj(m, 2, True))
                    new_node.append_part("name_end", code.slice_match_obj(m, 3, True))
                    new_node.append_part("body_start", code.slice_match_obj(m, 4, True))
                    new_node.append_part("body", code.slice_match_obj(m, 5, True))
                    new_node.append_part("body_end", code.slice_match_obj(m, 6, True))
                else:
                    new_node.append_part("body_start", code.slice_match_obj(m, 1, True))
                    new_node.append_part("body", code.slice_match_obj(m, 2, True))
                    new_node.append_part("body_end", code.slice_match_obj(m, 3, True))
                    new_node.append_part("name_start", code.slice_match_obj(m, 4, True))
                    new_node.append_part("name", code.slice_match_obj(m, 5, True))
                    new_node.append_part("name_end", code.slice_match_obj(m, 6, True))

                new_node = self.interpret_inline(new_node)
                node.child_nodes.insert_after(node.active, new_node)
                new_node.is_parsed = True
                split = True

                text_after = NodeRST("text", fg_after)
                text_after.append_part("body", fg_after)
                node.child_nodes.insert_after(new_node, text_after)
                node.active = text_after

        return node, split


    def single(self, node, code, name):
        split = False

        if node.active.node_name == "text":
            if m := re.search(self.re_lib[name], str(code)):
                fg_before, fg_code, fg_after = node.active.body.code.slice(
                                                    code.loc_to_abs(m.start(0)),
                                                    code.loc_to_abs(m.end(3)))
                node.active.body.code = fg_before
                node.active.code = fg_before

                if name in {"int-target-sw", "hyperlink-sw"}:
                    new_node = NodeRST(name[:-3], fg_code)
                    if name in "int-target-sw":
                        new_node.append_part("body_start", code.slice_match_obj(m, 1, True))
                        new_node.append_part("body", code.slice_match_obj(m, 2, True))
                    else:
                        new_node.append_part("id", code.slice_match_obj(m, 2, True))
                        new_node.append_part("body_end", code.slice_match_obj(m, 3, True))

                else:
                    if name == "mail":
                        name = "standalone"
                    new_node = NodeRST(name, fg_code)
                    new_node.append_part("body", fg_code)
                new_node.is_parsed = True

                node.child_nodes.insert_after(node.active, new_node)
                split = True

                after = NodeRST("text", fg_after)
                after.append_part("body", fg_after)
                node.child_nodes.insert_after(new_node, after)
                node.active = after

        return node, split


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
                        nn = id_node.next.next
                        print("{0}:{1}: {2}".format(nn.code.filename, nn.code.start_lincol[0],
                                                    "inline body unexpected content"))

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

        return node


# -----------------------------------------------------------------------------


def print_node(root, output=None, ind=-1, path="", show_loc=False, show_pos=False):
    if output is None:
        output = []
    ind += 1
    for node in root.child_nodes:
        output.append((" " * ind) + node.node_name)
        for part in node.child_nodes:
            if part.node_name in {"name", "head", "id", "attr", "body"}:
                if not part.child_nodes.is_empty():
                    ph = path + part.node_name[0]
                    output = print_node(part, output, ind, ph, show_loc, show_pos)
                else: #Fragment
                    if show_loc:
                        s = part.code.repr(show_pos)
                    else:
                        s = str(part.code).replace('\n', '¶')

                    output.append((" " * ind) + "{" + path + part.node_name[0] + "} " + s)

    return output
