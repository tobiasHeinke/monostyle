
"""
rst_parser.rst_node
~~~~~~~~~~~~~~~~~~~
"""

from monostyle.util.nodes import Node

class NodeRST(Node):
    """Universal node for RST."""

    __slots__ = ('node_name',
                 'indent', 'name_start', 'name', 'name_end', 'id_start', 'id', 'id_end',
                 'head', 'attr', 'body_start', 'body', 'body_end', 'code',
                 'active', 'is_parsed', 'is_parsing')


    def __init__(self, node_name, code):
        """
        node_name -- node type.
        code -- source of the node.
        """
        super().__init__()

        self.node_name = node_name

        self.indent = None
        self.name_start = None
        self.name = None
        self.name_end = None
        self.id_start = None
        self.id = None
        self.id_end = None
        self.head = None
        self.attr = None
        self.body_start = None
        self.body = None
        self.body_end = None

        if code is not None:
            code = code.copy()
        self.code = code

        self.active = None
        self.is_parsed = False
        self.is_parsing = False


    def append_part(self, name, code, is_full_line=False):
        """Append a newly created part child."""
        if not is_full_line:
            new_part = NodePartRST(name, code)
        else:
            new_part = NodePartRST(name, None)

        self.child_nodes.append(new_part)

        if is_full_line:
            new_part.append_code(code)
        setattr(self, name, new_part)


    def insert_part(self, name, code, after):
        """Insert newly created part child after a reference node."""
        new_part = NodePartRST(name, code)
        self.child_nodes.insert_after(after, new_part)
        setattr(self, name, new_part)


    def append_code(self, code):
        """Extent the node's code."""
        if self.code is None:
            if code is None:
                self.code = code
            else:
                self.code = code.copy()
        else:
            if code is not None and not self.is_parsing:
                self.code.combine(code)


    def prev_leaf(self):
        """Return the previous leaf node."""
        if self.prev:
            return self.prev
        node = self
        while not node.prev:
            if node.parent_node:
                node = node.parent_node.parent_node
            else: #root
                return None

        node = node.prev
        while node:
            if node.head and not node.head.child_nodes.is_empty():
                node = node.head.child_nodes.last()
            elif node.body and not node.body.child_nodes.is_empty():
                node = node.body.child_nodes.last()
            else:
                return node


    def next_leaf(self):
        """Return the next leaf node."""
        if self.next:
            return self.next
        node = self
        while not node.next:
            if node.parent_node:
                node = node.parent_node.parent_node
            else: #root
                return None

        node = node.next
        while node:
            if node.head and not node.head.child_nodes.is_empty():
                node = node.head.child_nodes.first()
            elif node.body and not node.body.child_nodes.is_empty():
                node = node.body.child_nodes.first()
            else:
                return node


    def __repr__(self):
        child_names = list(repr(child) for child in self.child_nodes)
        return self.node_name + ": " + ','.join(child_names)


    def __str__(self):
        return str(self.code)


class NodePartRST(Node):
    """Child node parts of RST nodes."""

    __slots__ = ('node_name', 'code', 'active', 'is_parsed', 'is_parsing')


    def __init__(self, node_name, code):
        """
        node_name -- node part type.
        code -- source of the node.
        """
        super().__init__()

        self.node_name = node_name

        if code is not None:
            code = code.copy()
        self.code = code

        self.active = None
        self.is_parsed = False
        self.is_parsing = False


    def append_child(self, new_node, prop_code=True):
        """Append a node as a child.
        prop_code -- propagate code to parent.
        """
        self.child_nodes.append(new_node)
        if prop_code:

            if not self.is_parsing:
                self.append_code(new_node.code)

            if (new_node.code is not None and
                    (self.parent_node.node_name.endswith("-list") or
                     self.parent_node.node_name.endswith("-table")) and
                    self.parent_node.parent_node is not None and
                    not self.parent_node.is_parsing and
                    not self.parent_node.parent_node.is_parsing):
                self.parent_node.parent_node.append_code(new_node.code)


    def append_code(self, code):
        """Extent the node's code and of its parents."""
        if self.code is None:
            if code is None:
                self.code = code
            else:
                self.code = code.copy()
        else:
            if code is not None and not self.is_parsing:
                self.code.combine(code)

        if code is not None and self.parent_node is not None and not self.parent_node.is_parsing:
            self.parent_node.append_code(code)


    def prev_leaf(self):
        """Return the previous leaf node."""
        node = self
        while not node.prev:
            if node.parent_node:
                node = node.parent_node
            else: #root
                return None

        if isinstance(node, NodePartRST):
            node = node.prev
        else:
            node = node.prev.child_nodes.last()
        while node:
            if node.child_nodes.last():
                node = node.child_nodes.last().child_nodes.last()
            else:
                return node


    def next_leaf(self):
        """Return the next leaf node."""
        node = self
        while not node.next:
            if node.parent_node:
                node = node.parent_node
            else: #root
                return None

        if isinstance(node, NodePartRST):
            node = node.next
        else:
            node = node.next.child_nodes.first()
        while node:
            if node.child_nodes.first():
                node = node.child_nodes.first().child_nodes.first()
            else:
                return node


    def __repr__(self):
        return self.node_name


    def __str__(self):
        return str(self.code)


# -----------------------------------------------------------------------------


def print_node(root, output=None, ind=-1, branch=None, show_loc=False, show_pos=False):
    if output is None:
        output = []
    if branch is None:
        branch = ""

    ind += 1
    for node in root.child_nodes:
        output.append((" " * ind) + node.node_name)
        for part in node.child_nodes:
            if part.node_name in {"name", "head", "id", "attr", "body"}:
                if not part.child_nodes.is_empty():
                    branch_new = branch + part.node_name[0]
                    output = print_node(part, output, ind, branch_new, show_loc, show_pos)
                else:
                    if show_loc:
                        code_str = part.code.repr(show_pos)
                    else:
                        code_str = str(part.code).replace('\n', '¶')

                    output.append(''.join((" " * ind,"{", branch, part.node_name[0], "} ",
                                           code_str)))

    return output
