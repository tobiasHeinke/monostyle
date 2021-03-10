
"""
rst_parser.rst_node
~~~~~~~~~~~~~~~~~~~
"""

from monostyle.util.nodes import Node

class NodeRST(Node):

    __slots__ = ('node_name',
                 'indent', 'name_start', 'name', 'name_end', 'id_start', 'id', 'id_end',
                 'head', 'attr', 'body_start', 'body', 'body_end', 'code',
                 'active', 'is_parsed', 'is_parsing')


    def __init__(self, node_name, code):
        super(NodeRST, self).__init__()

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
        if not is_full_line:
            new_part = NodePartRST(name, code)
        else:
            new_part = NodePartRST(name, None)

        self.child_nodes.append(new_part)

        if is_full_line:
            new_part.append_code(code)
        setattr(self, name, new_part)


    def insert_part(self, name, code, after):
        new_part = NodePartRST(name, code)
        self.child_nodes.insert_after(after, new_part)
        setattr(self, name, new_part)


    def append_code(self, code):
        if self.code is None:
            if code is None:
                self.code = code
            else:
                self.code = code.copy()
        else:
            if code is not None and not self.is_parsing:
                self.code.combine(code)


    def prev_leaf(self):
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

    __slots__ = ('node_name', 'code', 'active', 'is_parsed', 'is_parsing')


    def __init__(self, node_name, code):
        super(NodePartRST, self).__init__()

        self.node_name = node_name

        if code is not None:
            code = code.copy()
        self.code = code

        self.active = None
        self.is_parsed = False
        self.is_parsing = False


    def append_child(self, new_node, prop_code=True):
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
