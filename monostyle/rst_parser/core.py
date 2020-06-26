
"""
rst_parser.core
~~~~~~~~~~~~~~~

A RST parser.
"""

import re
import monostyle.util.monostylestd as monostylestd
from monostyle.util.fragment import Fragment
from monostyle.util.nodes import LinkedList
from monostyle.rst_parser.rst_node import NodeRST, NodePartRST
import monostyle.rst_parser.walker as rst_walker

class RSTParser:

    roles = (
        'abbr', 'any', 'class', 'command', 'dfn', 'doc', 'download', 'envvar',
        'file', 'guilabel', 'index', 'kbd', 'keyword', 'mailheader', 'makevar',
        'manpage', 'math', 'menuselection', 'mimetype', 'mod', 'newsgroup',
        'numref', 'option', 'pep', 'program', 'ref', 'regexp', 'rfc', 'samp',
        'sub', 'sup', 'term', 'token'
    )

    directives = (
        'admonition', 'attention', 'caution', 'centered', 'class',
        'code-block', 'codeauthor', 'compound', 'container', 'contents',
        'csv-table', 'danger', 'default-role', 'deprecated', 'epigraph',
        'error', 'figure', 'footer', 'glossary', 'header', 'highlight',
        'highlights', 'hint', 'hlist', 'image', 'important', 'include',
        'index', 'list-table', 'literalinclude', 'math', 'meta', 'note',
        'only', 'parsed-literal', 'productionlist', 'pull-quote', 'raw',
        'replace', 'role', 'rubric', 'sectionauthor', 'sectnum', 'seealso',
        'sidebar', 'table', 'tip', 'title', 'toctree', 'topic', 'unicode',
        'versionadded', 'versionchanged', 'warning'
    )

    substitution = {'release':'', 'version':'', 'today':''}

    trans_chars = ('!', '"', '#', '$', '%', '&', '\'', '(', ')', '*', '+', '-', ',', '.', '/',
                   ':', ';', '<', '=', '>', '?', '@', '[', ']', '^', '_', '`', '{', '|', '}', '~')
    bullet_chars = ('*', '-', '+', '•', '‣', '⁃')
    foot_chars = ('*', '†', '‡', '§', '¶', '#', '♠', '♥', '♦', '♣')

    parse_block_quote = False


    def __init__(self):
        self.re_lib = self._compile_re_lib()


    def _compile_re_lib(self):
        re_lib = dict()

        # Block

        ind = r"( *)"
        space_end = r"(?: +|(?=\n)|\Z)"

        name_any = r"[A-Za-z0-9\-_.+]+?"
        foot_name = "".join((r"(?:\d+)|[", "".join(self.foot_chars), r"]|(?:#", name_any, r")"))

        mid_a = r"(.*?(?<![\s\\"
        mid_b = r"]))"

        pattern_str = (ind, r"(([", r''.join(map(re.escape, self.trans_chars)), r"])\3*",
                       r" *(?:\n|\Z))")
        re_lib["trans"] = re.compile(''.join(pattern_str))

        pattern_str = (ind, r"([", r''.join(map(re.escape, self.bullet_chars)), r"]",
                       space_end, r")")
        re_lib["bullet"] = re.compile(''.join(pattern_str))

        pattern_str = (ind, r"(\()?([#\w]|\d+)([\.\)]", space_end, r")")
        re_lib["enum"] = re.compile(''.join(pattern_str))

        pattern_str = (ind, r"(\|", space_end, r")")
        re_lib["line"] = re.compile(''.join(pattern_str))

        # not match role; name no colon!
        pattern_str = (ind, r"(\:)([^:]+?)(\:(?!`)", space_end, r")")
        re_lib["field"] = re.compile(''.join(pattern_str))

        pattern_str = (ind, r"((?:\.\.|__)", space_end, r")")
        re_lib["exp"] = re.compile(''.join(pattern_str))

        dd = ''.join((ind, r"(\.\.", space_end, r")"))

        pattern_str = (r"(\A +)?(?<![^\\]\\)(\:\: *)(?:\n|\Z)")
        re_lib["dftdir"] = re.compile(''.join(pattern_str), re.DOTALL)

        direc = ''.join((r"(", name_any, r")(\:\:", space_end, r")"))
        re_lib["dir"] = re.compile(dd + direc)

        pattern_str = (dd, r"(\|)(", name_any, r")(\|\s+)(?:", direc, r")?")
        re_lib["substdef"] = re.compile(''.join(pattern_str))

        pattern_str = (dd, r"(\[)(", foot_name, r")(\]", space_end, r")")
        re_lib["footdef"] = re.compile(''.join(pattern_str))

        pattern_str = (dd, r"(\[)(", name_any, r")(\]", space_end, r")")
        re_lib["citdef"] = re.compile(''.join(pattern_str))

        pattern_str = (dd, r"(_ *)(`)?(?(4)(?:((?:[^`]*?[^\\", mid_b, r"(`))|", mid_a, mid_b, r")",
                       r"(\:", space_end, r")")
        re_lib["target"] = re.compile(''.join(pattern_str))

        pattern_str = (dd, r"?(__ *)(\:", space_end, r")?")
        re_lib["target-anon"] = re.compile(''.join(pattern_str))

        # Inline

        before_a = r"(?:(?<=[^\w\\"
        before_b = r"])|\A)"
        after_a = r"(?:(?=[^\w"
        after_b = r"])|\Z)"

        inliners = {
            ("literal", r"`", r"``", True, r"", r"``", r"`"),
            ("strong", r"\*", r"\*\*", True, r"*", r"\*\*", r"\*"),
            ("emphasis", r"\*", r"\*", True, r"*", r"\*", r"\*"),
            ("subst", "", r"\|", True, r"\|", r"\|_{0,2}", ""),
            ("int-target", "", r"_`", True, "", r"`", r"`"),
            ("dftrole", r"_:`", r"`", True, r"`", r"`", r"`"),
            ("hyperlink", r"`:_", r"`", True, r"`", r"`__?", ""),
            ("role", "", r"\:)(" + name_any + r")(\:)(`", True, "", r"`", ""),
            ("foot", "", r"\[", False, foot_name, r"\]_", ""),
            ("cit", "", r"\[", False, name_any, r"\]_", ""),
            ("int-target-sw", "", r"_(?!_)", False, r"[\w'-]+", "", ""),
            ("hyperlink-sw", "", "", False, r"[\w'-]+?", r"_(?!_)", ""),
            ("standalone", r"<`/", "", False, r"\bhttps?\:\/\/[^ ]*?", "", ""),
            ("link", "", r"<", True, "", r">", ""),
            ("parenthesis", "", r"\(", True, "", r"\)", "")
            # ("arrow", r"-", "", False, r"\-{1,2}>", "", "")
            # ("dash", r"-", "", False, r"\-{2,3}", "", "")
        }
        for name, before_no, start, is_dot_mid, mid, end, after_no in inliners:
            if is_dot_mid:
                mid = (mid_a if name != "literal" else mid_a[:-2], mid, mid_b)
            else:
                mid = (r"(", mid, r")")
            if name not in {"link", "parenthesis"}:
                before = (before_a, before_no, before_b)
            else:
                before = ()
                start = r"(?:\s+?|\A)" + start

            if name != "standalone":
                after = (after_a, after_no, after_b)
            else:
                after = (r"(?:(?=[\s", after_b)

            pattern_str = (*before, r"(", start, r")",
                           *mid,
                           r"(", end, r")", *after)
            re_lib[name] = re.compile(''.join(pattern_str), re.DOTALL)

        return re_lib


    # -----------------------------------------------------------------------------


    def parse_block(self, node, ind_first_unkown=False):
        # indention
        ind_start = [0]
        ind_cur = 0
        on = False
        is_block_start = True
        sub = False
        root = node

        is_first_not_empty = True
        is_first = True
        is_sec = True

        node.is_parsing = True
        line = None
        for buf in node.code.splitlines(True):
            if line:
                line_strip = str(line).lstrip(' ')
                is_not_empty = bool(len(line_strip.strip()) != 0)

                was_on = on
                if is_not_empty:
                    ind_cur = line.start_lincol[1] + len(line) - len(line_strip)
                    if is_first_not_empty:
                        # first defines the base indent
                        # block-quote at start will be a text node
                        ind_start[0] = ind_cur
                        is_first_not_empty = False

                    if ind_cur == ind_start[-1]:
                        on = False
                    elif ind_cur > ind_start[-1]:
                        on = True
                        is_block_start = True
                    else:
                        on = False
                        is_block_start = True

                if is_sec and not is_first:
                    # alternative when head first indent as unknown
                    if ind_first_unkown: # only if text node x
                        if not was_on and not sub:
                            on = False

                            ind_start[0] = ind_cur
                    is_sec = False
                is_first = False


                if ind_start[-1] > ind_cur:
                    ind_start.clear()
                    ind_start.append(ind_cur)

                is_block_end = bool(not buf or len(str(buf).strip()) == 0)
                on, ind_start, node, sub = self.process_line(
                    line, is_not_empty, is_block_start, is_block_end,
                    on, ind_cur, ind_start, node, sub)

                is_block_start = not is_not_empty

            line = buf

        if node.active:
            if (node.child_nodes.last() and
                    node.child_nodes.last().node_name == node.active.node_name or
                    (sub and node.parent_node.node_name == node.active.node_name + "-list")):
                node.append_child(node.active)
                if sub and root.active:
                    root.append_child(root.active)
            else:
                root.append_child(node.active)

        return root


    def process_line(self, line, is_not_empty, is_block_start, is_block_end,
                     on, ind_cur, ind_start, node, sub):

        was_sub = sub
        free = True
        if not node.active:
            if is_not_empty:
                node, sub = self.field(line, is_not_empty, is_block_start, on, node, sub)
                if not node.active:
                    node, sub = self.be_list(line, is_block_start, on, node, sub)
                if not node.active:
                    node, sub = self.line_block(line, is_block_start, on, node, sub)
                if not node.active:
                    node, sub = self.explicit_block(line, is_not_empty, is_block_end, on, node, sub)
                if not node.active:
                    node = self.transition(line, is_not_empty, is_block_start, on, node)
                if not node.active:
                    node = self.block_quote(line, is_not_empty, is_block_start, on, node)

            if not node.active or (node.active and node.active.node_name == "text"):
                node = self.textnode(line, is_not_empty, on, node)
            if sub:
                node, sub = self.def_list(line, is_not_empty, is_block_start, on, node, sub)

        else:
            free = False

            if node.active.node_name == "field":
                node, sub = self.field(line, is_not_empty, is_block_start, on, node, sub)
            elif node.active.node_name in {"bullet", "enum"}:
                node, sub = self.be_list(line, is_block_start, on, node, sub)
            elif node.active.node_name == "line":
                node, sub = self.line_block(line, is_block_start, on, node, sub)
            elif node.active.node_name in {"dir", "target", "comment", "substdef",
                                           "footdef", "citdef"}:
                node, sub = self.explicit_block(line, is_not_empty, is_block_end, on, node, sub)
            elif node.active.node_name == "trans":
                node = self.transition(line, is_not_empty, is_block_start, on, node)
                if node.active:
                    node = self.section(line, is_not_empty, is_block_end, on, node)
            elif node.active.node_name == "sect":
                node = self.section(line, is_not_empty, is_block_end, on, node)
            elif node.active.node_name == "block-quote":
                node = self.block_quote(line, is_not_empty, is_block_start, on, node)
            else:
                node = self.section(line, is_not_empty, is_block_end, on, node)
                if (node.active and node.active.node_name != "sect") or sub:
                    node, sub = self.def_list(line, is_not_empty, is_block_start, on, node, sub)
                    if node.active and node.active.node_name == "text":
                        if is_block_end:
                            node, sub = self.explicit_block(line, is_not_empty, is_block_end,
                                                            on, node, sub)
                        if node.active.node_name == "text":
                            node = self.textnode(line, is_not_empty, on, node)

        rematch = False
        if node.active:
            on = True
        elif not free and is_not_empty:
            rematch = True

        if sub != was_sub:
            if sub and not was_sub:
                if node.active.node_name not in ("def", "block-quote"):
                    ind_start.append(ind_cur)
                else:
                    ind_start.append(ind_start[-1])
            else:
                if not node.active and is_not_empty and not free:
                    rematch = True
                if len(ind_start) > 1:
                    ind_start.pop(len(ind_start) - 1)

        if rematch:
            is_block_start = True
            on, ind_start, node, sub = self.process_line(
                line, is_not_empty, is_block_start, is_block_end,
                on, ind_cur, ind_start, node, sub)

        return on, ind_start, node, sub


    def parse_inline(self, node, name=None, recursive=False):
        if not recursive:
            newnode = NodeRST("text", node.code)
            newnode.append_part("body", node.code)
            node.child_nodes.append(newnode)

        recorder = (
            "literal", "strong", "emphasis",
            "int-target", "role", "hyperlink", "dftrole",
            "subst", "foot", "cit",
            "standalone", "int-target-sw", "hyperlink-sw"
        )

        if not name:
            name = recorder[0]
            name_next = recorder[1]
        elif name in recorder:
            n = recorder.index(name) + 1
            name_next = recorder[n] if n < len(recorder) else None
        else:
            name_next = None

        node.is_parsing = True
        node.active = node.child_nodes.first()
        while node.active:
            split = False
            if not node.active.is_parsed and node.active.body:
                if name == "role":
                    node, split = self.role(node.active.body.code, node)
                elif name in ("int-target-sw", "hyperlink-sw", "standalone"):
                    node, split = self.single(node.active.body.code, name, node)
                else:
                    node, split = self.inline(node.active.body.code, name, node)

            if not split or node.active.is_parsed:
                if name == node.active.node_name:
                    print("{0}:{1}: unclosed inline (within paragraph)".format(node.active.code.fn,
                              node.active.code.start_lincol[0]))

                node.active = node.active.next

        if name_next:
            node = self.parse_inline(node, name_next, True)

        return node


    def parse_full(self, doc):
        doc.is_parsing = True
        doc.body = self.parse_block(doc.body)
        doc.body = self.parse_node(doc.body)
        doc.body = self.parse_node_inline(doc.body)
        doc.is_parsed = True
        return doc


    def parse_node(self, root):
        for node in root.child_nodes:
            if (node.node_name != "text" and
                    (node.node_name != "dir" or not(not node.name or
                     str(node.name.code).rstrip() == "code-block")) and
                    node.node_name != "comment" and
                    (node.node_name != "block-quote" or self.parse_block_quote)):
                if node.head:
                    if not node.head.child_nodes.is_empty():
                        self.parse_node(node.head)
                    else:
                        ind_first_unkown = bool(node.child_nodes.first().code.start_lincol[1] !=
                                                node.head.code.start_lincol[1])
                        node.head = self.parse_block(node.head, ind_first_unkown)
                        node.head.is_parsed = True
                        if not node.head.child_nodes.is_empty():
                            self.parse_node(node.head)

                if node.body:
                    if not node.body.child_nodes.is_empty():
                        self.parse_node(node.body)
                    else:
                        ind_first_unkown = bool(node.child_nodes.first().code.start_lincol[1] !=
                                                node.body.code.start_lincol[1])
                        node.body = self.parse_block(node.body, ind_first_unkown)
                        node.body.is_parsed = True
                        if not node.body.child_nodes.is_empty():
                            self.parse_node(node.body)

            node.is_parsed = True
        return root


    def parse_node_inline(self, root):
        for node in root.child_nodes:
            if ((node.node_name != "dir" or not(not node.name or
                    str(node.name.code).rstrip() == "code-block")) and
                    node.node_name != "comment" and
                    (node.node_name != "block-quote" or self.parse_block_quote)):

                if node.node_name == "sect" and node.name:
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

    def document(self, fn, text):
        fg = Fragment(fn, text)
        newnode = NodeRST("document", fg)
        newnode.append_part("body", fg)
        return newnode


    def snippet(self, fg):
        newnode = NodeRST("snippet", fg)
        newnode.append_part("body", fg)
        return newnode


    def transition(self, line, is_not_empty, is_block_start, on, node):
        if not node.active:
            if is_block_start:
                if m := re.match(self.re_lib["trans"], str(line)):
                    newnode = NodeRST("trans", line)
                    newnode.append_part("indent", line.slice_match_obj(m, 1, True))
                    newnode.append_part("name_start", line.slice_match_obj(m, 2, True))
                    node.active = newnode

        elif not is_not_empty:
            node.active.name_start.append_code(line)
            node.append_child(node.active)
            node.active = None

        return node


    def section(self, line, is_not_empty, is_block_end, on, node):
        if node.active:
            if node.active.node_name == "trans":
                if is_block_end:
                    node.append_child(node.active)
                    node.active = None
                    return node

                node.active.append_part("name", line, True)
                node.active.node_name = "sect"

            elif node.active.node_name in {"text", "sect"}:
                if m := re.match(self.re_lib["trans"], str(line)):
                    node.active.node_name = "sect"
                    if node.active.body:
                        # move inside node
                        node.active.name = node.active.body
                        node.active.name.node_name = "name"
                        node.active.body = None
                    node.active.append_part("name_end", line, True)

                elif node.active.node_name == "sect":
                    if not is_not_empty:
                        node.active.name_end.append_code(line)
                    else:
                        print("{0}:{1}: {2}".format(line.fn, line.start_lincol[0],
                                                    "section missing blank line"))

                    node.append_child(node.active)
                    node.active = None


        return node


    def textnode(self, line, is_not_empty, on, node):

        if node.active:
            node.active.body.append_code(line)
            if not is_not_empty:
                node.append_child(node.active)
                node.active = None

        else:
            newnode = NodeRST("text", line)
            newnode.append_part("body", line)
            if is_not_empty:
                node.active = newnode
            else:
                node.append_child(newnode)
                if node.active:
                    node.append_child(node.active)
                node.active = None

        return node


    def def_list(self, line, is_not_empty, is_block_start, on, node, sub):
        if not on:
            if node.active and node.active.node_name != "text":
                if node.active and node.active.node_name != "def":
                    if (sub and node.parent_node and
                            node.parent_node.node_name == "def-list"):

                        active = node.active
                        node = node.parent_node.parent_node
                        if node.active:
                            print("{0}:{1}: {2}".format(line.fn, line.start_lincol[0],
                                                        "wrong def start"))
                        else:
                            node.active = active
                        sub = False
                elif node.parent_node and node.parent_node.node_name == "def-list":
                    node.append_child(node.active)
                    node.active = None
                    if node.parent_node:
                        node = node.parent_node.parent_node
                    sub = False

        else:
            if node.active:
                if node.active.node_name == "text" and is_not_empty:
                    # only def node in def-list
                    # is_block_start info is lost with the text node
                    if not sub:
                        if (not node.child_nodes.is_empty() and
                                node.child_nodes.last().node_name == "def-list"):
                            prime = node.child_nodes.last()
                        else:
                            prime = NodeRST("def-list", None)
                            prime.append_part("body", None)
                            node.append_child(prime)

                        newnode = node.active
                        node.active = None
                        node = prime.body
                        node.active = newnode
                        sub = True

                    node.active.node_name = "def"
                    node.active.head = node.active.body
                    node.active.head.node_name = "head"
                    node.active.append_part("body", line, True)


                elif node.active.node_name == "def":
                    node.active.body.append_code(line)
                elif sub:
                    if node.node_name == "def-list":
                        active = node.active
                        if node.parent_node:
                            node = node.parent_node.parent_node
                        if node.active:
                            print("{0}:{1}: {2}".format(line.fn, line.start_lincol[0],
                                                        "wrong def start"))
                        else:
                            node.active = active

                        sub = False

            # > else block quote

        return node, sub


    def block_quote(self, line, is_not_empty, is_block_start, on, node):
        if on:
            if node.active and node.active.node_name == "block-quote":
                node.active.body.append_code(line)

            elif not node.active:
                newnode = NodeRST("block-quote", line)
                newnode.append_part("body", line)
                node.active = newnode

        else:
            if node.active:
                node.append_child(node.active)
            node.active = None

        return node


    def be_list(self, line, is_block_start, on, node, sub):
        if not on:
            if m := re.match(self.re_lib["bullet"], str(line)):
                newnode = NodeRST("bullet", line)
                newnode.append_part("indent", line.slice_match_obj(m, 1, True))
                _, fg, after_name = line.slice_match_obj(m, 2)
                newnode.append_part("name_start", fg)
                newnode.append_part("body", after_name)

            else:
                if m := re.match(self.re_lib["enum"], str(line)):
                    newnode = NodeRST("enum", line)
                    newnode.append_part("indent", line.slice_match_obj(m, 1, True))
                    if m.group(2):
                        newnode.append_part("name_start", line.slice_match_obj(m, 2, True))
                    newnode.append_part("name", line.slice_match_obj(m, 3, True))
                    _, fg, after_name = line.slice_match_obj(m, 4)
                    newnode.append_part("name_end", fg)
                    newnode.append_part("body", after_name)

                else:
                    if node.active and node.active.node_name in {"bullet", "enum"}:
                        node.append_child(node.active)
                        node.active = None
                        if node.parent_node.parent_node:
                            node = node.parent_node.parent_node
                        sub = False
                    return node, sub

            if is_block_start:
                # different list type after another
                if (sub and (node.active and
                             node.active.node_name != newnode.node_name)):
                    node.append_child(node.active)
                    node.active = None
                    node = node.parent_node.parent_node
                    sub = False

                if not sub or node.parent_node.node_name != newnode.node_name + "-list":
                    prime = NodeRST(newnode.node_name + "-list", None)
                    prime.append_part("body", None)
                    node.append_child(prime)
                    node = prime.body
                    sub = True

            if node.active:
                node.append_child(node.active)
            node.active = newnode

        elif node.active and node.active.node_name in {"bullet", "enum"}:
            node.active.body.append_code(line)

        return node, sub


    def line_block(self, line, is_block_start, on, node, sub):
        if not on:
            if m := re.match(self.re_lib["line"], str(line)):
                newnode = NodeRST("line", line)
                newnode.append_part("indent", line.slice_match_obj(m, 1, True))
                _, fg, after_name = line.slice_match_obj(m, 2)
                newnode.append_part("name_start", fg)
                newnode.append_part("body", after_name)

                if is_block_start and (not sub or node.parent_node.node_name != "line-list"):
                    prime = NodeRST(newnode.node_name + "-list", None)
                    prime.append_part("body", None)
                    node.append_child(prime)
                    node = prime.body
                    sub = True

                if node.active:
                    node.append_child(node.active)
                node.active = newnode

            else:
                if node.active and node.active.node_name == "line":
                    node.append_child(node.active)
                    node.active = None
                    if node.parent_node:
                        node = node.parent_node.parent_node
                    sub = False

        elif node.active and node.active.node_name == "line":
            node.active.body.append_code(line)

        return node, sub


    def field(self, line, is_not_empty, is_block_start, on, node, sub):

        if not on:
            if m := re.match(self.re_lib["field"], str(line)):
                newnode = NodeRST("field", line)
                newnode.append_part("indent", line.slice_match_obj(m, 1, True))
                newnode.append_part("name_start", line.slice_match_obj(m, 2, True))
                newnode.append_part("name", line.slice_match_obj(m, 3, True))
                _, fg, after_name = line.slice_match_obj(m, 4)
                newnode.append_part("name_end", fg)
                newnode.append_part("body", after_name)

                if is_block_start and (not sub or node.parent_node.node_name != "field-list"):
                    prime = NodeRST(newnode.node_name + "-list", None)
                    prime.append_part("body", None)

                    node.append_child(prime)
                    node = prime.body
                    sub = True

                if node.active:
                    node.append_child(node.active)
                node.active = newnode

            elif sub:
                if node.active and node.active.node_name == "field":
                    node.append_child(node.active)
                    node.active = None
                    if node.parent_node:
                        node = node.parent_node.parent_node
                    sub = False

        elif node.active:
            node.active.body.append_code(line)

            # dir attr nl ends field
            if node.parent_node and node.parent_node.parent_node.node_name == "attr":
                node.append_child(node.active)
                node.active = None
                node = node.parent_node.parent_node.parent_node.parent_node
                sub = False

        return node, sub


    def explicit_block(self, line, is_not_empty, is_block_end, on, node, sub):
        def factory(line, line_str, newnode, is_anon_target):
            target_anon_m = re.match(self.re_lib["target-anon"], line_str)
            if not (is_anon_target or target_anon_m):
                if sub_m := re.match(self.re_lib["substdef"], line_str):
                    newnode.node_name = "substdef"

                    newnode.append_part("id_start", line.slice_match_obj(sub_m, 3, True))
                    newnode.append_part("id", line.slice_match_obj(sub_m, 4, True))
                    _, fg, after_id = line.slice_match_obj(sub_m, 5)
                    newnode.append_part("id_end", fg)
                    if sub_m.group(5):
                        newnode.append_part("name", line.slice_match_obj(sub_m, 6, True))
                        _, fg, after_name = line.slice_match_obj(sub_m, 7)
                        newnode.append_part("name_end", fg)
                        newnode.append_part("head", after_name)
                    else:
                        newnode.append_part("head", after_id)
                    newnode.active = newnode.head
                    return newnode

                if foot_m := re.match(self.re_lib["footdef"], line_str):
                    newnode.node_name = "footdef"
                    newnode.append_part("id_start", line.slice_match_obj(foot_m, 3, True))
                    newnode.append_part("id", line.slice_match_obj(foot_m, 4, True))
                    _, fg, after_id = line.slice_match_obj(foot_m, 5)
                    newnode.append_part("id_end", fg)
                    newnode.append_part("head", after_id)
                    newnode.active = newnode.head
                    return newnode

                if cit_m := re.match(self.re_lib["citdef"], line_str):
                    newnode.node_name = "citdef"
                    newnode.append_part("id_start", line.slice_match_obj(cit_m, 3, True))
                    newnode.append_part("id", line.slice_match_obj(cit_m, 4, True))
                    _, fg, after_id = line.slice_match_obj(cit_m, 5)
                    newnode.append_part("id_end", fg)
                    newnode.append_part("head", after_id)
                    newnode.active = newnode.head
                    return newnode

                if target_m := re.match(self.re_lib["target"], line_str):
                    newnode.node_name = "target"
                    _, fg, after_id = line.slice_match_obj(target_m, 3)
                    newnode.name_start.code.combine(fg)
                    if target_m.group(4) is not None:
                        # has literal
                        newnode.append_part("id_start", line.slice_match_obj(target_m, 4, True))
                        newnode.append_part("id", line.slice_match_obj(target_m, 5, True))
                        newnode.append_part("id_end", line.slice_match_obj(target_m, 6, True))
                    else:
                        newnode.append_part("id", line.slice_match_obj(target_m, 7, True))

                    _, fg, after_name = line.slice_match_obj(target_m, 8)
                    newnode.append_part("name_end", fg)
                    newnode.append_part("head", after_name)
                    newnode.active = newnode.head
                    return newnode

                if dir_m := re.match(self.re_lib["dir"], line_str):
                    newnode.node_name = "dir"
                    newnode.append_part("name", line.slice_match_obj(dir_m, 3, True))
                    _, fg, after_name = line.slice_match_obj(dir_m, 4)
                    newnode.append_part("name_end", fg)
                    newnode.append_part("head", after_name)
                    newnode.active = newnode.head
                    return newnode

                newnode.node_name = "comment"
                newnode.append_part("body", after_starter)
                newnode.active = newnode.body
                return newnode
            else:
                if target_anon_m:
                    newnode.node_name = "target"
                    if target_anon_m.group(3) is None:
                        _, __, after_id = line.slice_match_obj(target_anon_m, 2)
                    else:
                        _, fg, after_id = line.slice_match_obj(target_anon_m, 3)
                        if target_anon_m.group(2) is not None:
                            # has double dot
                            newnode.name_start.code.combine(fg)
                    if target_anon_m.group(4) is not None:
                        # has double colon
                        _, fg, after_id = line.slice_match_obj(target_anon_m, 4)
                        newnode.append_part("name_end", fg)

                    newnode.append_part("head", after_id)
                    newnode.active = newnode.head
                    return newnode


        if (not on or (is_block_end and
                       (not node.active or node.active.node_name == "text"))):
            if (node.active and
                    (not is_block_end or
                     node.active.node_name in {"dir", "target", "comment", "substdef",
                                               "footdef", "citdef"})):
                if node.active:
                    node.append_child(node.active)
                node.active.active = None
                node.active = None
                return node, sub

            if starter_m := re.match(self.re_lib["exp"], str(line)):
                newnode = NodeRST("exp", line)
                line_str = str(line)
                newnode.append_part("indent", line.slice_match_obj(starter_m, 1, True))
                _, fg, after_starter = line.slice_match_obj(starter_m, 2)
                newnode.append_part("name_start", fg)
                is_anon_target = bool(str(starter_m.group(2)).startswith("__"))
                newnode = factory(line, line_str, newnode, is_anon_target)

            else:
                if starter_m := re.search(self.re_lib["dftdir"], str(line)):
                    newnode = NodeRST("dir", None)
                    if starter_m.group(1):
                        newnode.append_part("indent", line.slice_match_obj(starter_m, 1, True))
                    before_starter, fg, after_starter = line.slice_match_obj(starter_m, 2)
                    newnode.append_part("name_end", fg, True)
                    newnode.append_part("head", after_starter, True)
                    newnode.active = NodePartRST("body", None)
                    if starter_m.start(0) != 0:
                        if node.active and node.active.node_name != "text":
                            node.append_child(node.active)
                            node.active.active = None
                            node.active = None
                        self.textnode(before_starter, is_not_empty, on, node)

                    if node.active:
                        node.append_child(node.active)
                        node.active.active = None
                        node.active = None


                else:
                    return node, sub

            if node.active:
                node.append_child(node.active)
            node.active = newnode
            newnode.parent_node = node


        elif node.active:
            if node.active.active.node_name == "head":
                if is_not_empty:
                    attr_part = NodePartRST("attr", None)
                    attr_part.parent_node = node.active
                    attr_node, sub = self.field(line, is_not_empty, True, False, attr_part, sub)
                    if sub:
                        node.active.attr = attr_part
                        node.active.child_nodes.append(attr_part)
                        node.active.append_code(attr_part.code)
                        node.active.active = node.active.attr
                        node = attr_node
                        return node, sub

                if not node.active.head:
                    node.active.head = node.active.active
                    node.active.child_nodes.append(node.active.head)
                    node.active.head.append_code(line)
                else:
                    node.active.head.append_code(line)

                if not is_not_empty:
                    if node.active.node_name != "target":
                        node.active.active = NodePartRST("body", None)
                    else:
                        node.append_child(node.active)
                        node.active.active = None
                        node.active = None
                    return node, sub

            elif node.active.active.node_name == "attr":
                node.active.active = NodePartRST("body", None)

            if node.active.active.node_name == "body":
                if not node.active.body:
                    node.active.body = node.active.active
                    node.active.child_nodes.append(node.active.body)
                    node.active.body.append_code(line)
                else:
                    node.active.body.append_code(line)

        return node, sub


    # -----------------------------------------------------------------------------
    # Inline


    def inline(self, code, name, node):
        split = False

        if node.active.node_name == "text":
            if m := re.search(self.re_lib[name], str(code)):
                start = code.loc_to_abs(m.start(1))
                end = code.loc_to_abs(m.end(3))
                fg_before, fg_code, fg_after = node.active.body.code.slice(start, end)
                node.active.body.code = fg_before
                node.active.code = fg_before

                newnode = NodeRST(name, fg_code)
                newnode.append_part("body_start", code.slice_match_obj(m, 1, True))
                newnode.append_part("body", code.slice_match_obj(m, 2, True))
                if name == "hyperlink":
                    newnode = self.interpret_inline(newnode)
                elif name == "dftrole":
                    newnode.node_name = "role"
                elif name == "subst":
                    newnode.id = newnode.body
                    newnode.id.node_name = "id"
                    newnode.body = None
                newnode.append_part("body_end", code.slice_match_obj(m, 3, True))
                node.child_nodes.insert_after(node.active, newnode)
                newnode.is_parsed = True
                split = True

                text_after = NodeRST("text", fg_after)
                text_after.append_part("body", fg_after)
                node.child_nodes.insert_after(newnode, text_after)
                node.active = text_after

        return node, split


    def role(self, code, node):
        split = False

        if node.active.node_name == "text":
            if m := re.search(self.re_lib["role"], str(code)):
                start = code.loc_to_abs(m.start(0))
                end = code.loc_to_abs(m.end(6))
                fg_before, fg_code, fg_after = node.active.body.code.slice(start, end)
                node.active.body.code = fg_before
                node.active.code = fg_before

                newnode = NodeRST("role", fg_code)
                newnode.append_part("name_start", code.slice_match_obj(m, 1, True))
                newnode.append_part("name", code.slice_match_obj(m, 2, True))
                newnode.append_part("name_end", code.slice_match_obj(m, 3, True))
                newnode.append_part("body_start", code.slice_match_obj(m, 4, True))
                newnode.append_part("body", code.slice_match_obj(m, 5, True))
                node.child_nodes.insert_after(node.active, newnode)
                if newnode.name:
                    newnode = self.interpret_inline(newnode)
                newnode.append_part("body_end", code.slice_match_obj(m, 6, True))
                newnode.is_parsed = True
                split = True

                text_after = NodeRST("text", fg_after)
                text_after.append_part("body", fg_after)
                node.child_nodes.insert_after(newnode, text_after)
                node.active = text_after

        return node, split


    def single(self, code, name, node):
        split = False

        if node.active.node_name == "text":
            if m := re.search(self.re_lib[name], str(code)):
                start = code.loc_to_abs(m.start(0))
                end = code.loc_to_abs(m.end(2))
                fg_before, fg_code, fg_after = node.active.body.code.slice(start, end)
                node.active.body.code = fg_before
                node.active.code = fg_before

                if name in ("int-target-sw", "hyperlink-sw"):
                    newnode = NodeRST(name[:-3], fg_code)
                    if name in "int-target-sw":
                        newnode.append_part("body_start", code.slice_match_obj(m, 1, True))
                        newnode.append_part("body", code.slice_match_obj(m, 2, True))
                    else:
                        newnode.append_part("id", code.slice_match_obj(m, 1, True))
                        newnode.append_part("body_end", code.slice_match_obj(m, 2, True))

                else:
                    newnode = NodeRST(name, fg_code)
                    newnode.append_part("body", fg_code)
                newnode.is_parsed = True

                node.child_nodes.insert_after(node.active, newnode)
                split = True

                after = NodeRST("text", fg_after)
                after.append_part("body", fg_after)
                node.child_nodes.insert_after(newnode, after)
                node.active = after

        return node, split


    def interpret_inline(self, node):
        sub = False
        name_str = None
        if node.node_name == 'hyperlink':
            sub_name = "link"
            sub = True
        else:
            name_str = str(node.name.code).strip()
            if name_str in ('doc', 'ref', 'term', 'any', 'download', 'numref'):
                sub_name = "link"
                sub = True
            elif name_str == 'abbr':
                sub_name = "parenthesis"
                sub = True

        if sub:
            sub_node = self.parse_inline(node.body, sub_name)

            if len(sub_node.child_nodes) > 1 and sub_node.child_nodes[1].node_name == sub_name:
                node.head = node.body
                node.head.node_name = "head"
                node.head.code = sub_node.child_nodes.first().body.code

                id_node = sub_node.child_nodes[1]
                node.append_part("id_start", id_node.body_start.code)
                node.append_part("id", id_node.body.code)
                node.append_part("id_end", id_node.body_end.code)

                node.head.child_nodes = LinkedList(node.head)
                node.body = None
                if id_node.next and id_node.next.body:
                    if len(id_node.next.body.code) != 0:
                        node.append_part("body", id_node.next.body.code)
                    if id_node.next.next:
                        nn = id_node.next.next
                        print("{0}:{1}: {2}".format(nn.code.fn, nn.code.start_lincol[0],
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
# Common Operations


def get_link_titles(rst_parser):
    """Get titles."""
    targets = []
    docs = []

    for fn, text in monostylestd.rst_texts():
        doc = rst_parser.document(fn, text)
        doc.body = rst_parser.parse_block(doc.body)
        is_first = True
        for node in rst_walker.iter_node(doc.body, ("sect",)):
            if is_first:
                fn = monostylestd.path_to_rel(fn, "rst")
                fn = '/' + fn[:-4]

                docs.append([fn, node.name.code])
                is_first = False

            p = node.prev
            while p and p.node_name == "target": # or empty
                targets.append([str(p.id.code).strip(), node.name.code])
                p = p.prev

    return docs, targets


def resolve_link_title(document, docs, targets):
    """Insert the link title (defined by section titles) if it is not set in the role."""

    for node in rst_walker.iter_node(document.body, ("role",)):
        name = str(node.name.code).strip() if node.name else ""
        if name == "doc":
            if not node.head:
                link_content = str(node.id.code).strip()

                for fn_doc, title_doc in docs:
                    if link_content == fn_doc:
                        node.append_part("head", title_doc) # order
                        break
                else:
                    print("{0}:{1}: {2}".format(node.id.code.fn, node.id.code.start_lincol[0],
                                                "resolve link titles: unknown doc:"))
                    print(link_content)


        elif name == "ref":
            if not node.head:
                link_content = str(node.id.code).strip()

                for target, title in targets:
                    if link_content == target:
                        node.append_part("head", title) # order
                        break
                else:
                    if not (link_content.startswith("fig-") or link_content.startswith("tab-")):
                        print("{0}:{1}: {2}".format(node.id.code.fn, node.id.code.start_lincol[0],
                                                    "resolve link titles: unknown ref:"))
                        print(link_content)

    return document





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
