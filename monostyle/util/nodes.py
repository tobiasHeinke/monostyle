
"""
util.nodes
~~~~~~~~~~

Generic node container.
"""

class Node:
    """Node base class."""

    __slots__ = ('prev', 'next', 'parent_node', 'child_nodes')


    def __init__(self):
        self.prev = None
        self.next = None
        self.parent_node = None
        self.child_nodes = LinkedList(self)


    def prev_leaf(self):
        """Return the previous leaf node."""
        node = self
        while not node.prev:
            if node.parent_node:
                node = node.parent_node
            else: #root
                return None

        node = node.prev
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

        node = node.next
        while node:
            if node.child_nodes.first():
                node = node.child_nodes.first().child_nodes.first()
            else:
                return node


class LinkedList:
    """Container for interconnected nodes."""

    __slots__ = ('_head', '_tail', '_list_size', 'parent')

    def __init__(self, parent=None):
        self._head = None
        self._tail = None
        self._list_size = 0

        self.parent = parent


    def copy(self):
        """Create a copy."""
        new_list = type(self)(self.parent)
        new_list._head = self._head
        new_list._tail = self._tail
        new_list._list_size = self._list_size

        return new_list


    def clear(self):
        """Empty the list."""
        return self.__init__(self.parent)


    def is_linked(self, node):
        """Check if the node is connected with other nodes."""
        return not ((node and node.prev is None and node.next is None
                     and self._tail is not node and self._head is not node)
                    or self.is_empty())


    def __len__(self):
        return self._list_size


    def is_empty(self):
        """Check if the list is empty."""
        return bool(self._list_size == 0)


    def first(self):
        """Return the first node."""
        return self._head


    def last(self):
        """Return the last node."""
        return self._tail


    def __str__(self):
        result = []
        for node in self:
            result.append(str(node))

        return str(result)


    def __repr__(self):
        return str(self)


    def to_list(self):
        """Convert to list."""
        result = []
        for node in self:
            result.append(node)

        return result


    # Note that modifying the list during
    # iteration is not safe.
    def __iter__(self):
        node = self._head
        while node:
            yield node
            node = node.next


    # A reverse function would require a node.copy()
    # which is not implemented.
    def __reversed__(self):
        node = self._tail
        while node:
            yield node
            node = node.prev


    def __contains__(self, ref_node):
        """Checks if the node is in the list."""
        if not self.is_linked(ref_node):
            return False

        for node in self:
            if node is ref_node:
                return True

        return False


    def count(self, ref_node):
        """Return count of the node."""
        if not hasattr(ref_node, "__eq__"):
            raise NotImplementedError("Node requires an __eq__ method to check"
                                      "if payload is identical")

        counter = 0
        if not self.is_linked(ref_node):
            return counter

        for node in self:
            if node is ref_node:
                counter += 1

        return counter


    def index(self, ref_node, start=None, end=None):
        """Return index of node."""
        if not self.is_linked(ref_node):
            return None

        for index, node in enumerate(self):
            if ((start is None or index > start) and
                    (end is None or index < end) and
                    ref_node is node):
                return index


    def __getitem__(self, at):
        """Return node at index."""
        if abs(at) >= self._list_size or not isinstance(at, int):
            raise IndexError()
        if at < 0:
            at = self._list_size - at

        for index, node in enumerate(self):
            if at == index:
                return node


    def __setitem__(self, at, new_node):
        """Insert node at index."""
        if abs(at) >= self._list_size or not isinstance(at, int):
            raise IndexError()
        if at < 0:
            at = self._list_size - at

        node = self.__getitem__(at)
        if node:
            self.insert_before(node, new_node)


    def __delitem__(self, at):
        """Remove node."""
        if abs(at) >= self._list_size or not isinstance(at, int):
            raise IndexError()
        if at < 0:
            at = self._list_size - at

        node = self.__getitem__(at)
        if node:
            self.remove(node)


    def insert_after(self, node, new_node):
        """Add node after reference node."""
        if not self.is_linked(node):
            return self

        new_node.parent_node = self.parent
        new_node.prev = node
        new_node.next = node.next
        if node.next is None:
            self._tail = new_node
        else:
            node.next.prev = new_node

        node.next = new_node
        self._list_size += 1
        return self


    def insert_before(self, node, new_node):
        """Add node before reference node."""
        if not self.is_linked(node):
            return self

        new_node.parent_node = self.parent
        new_node.prev = node.prev
        new_node.next = node
        if node.prev is None:
            self._head = new_node
        else:
            node.prev.next = new_node

        node.prev = new_node
        self._list_size += 1
        return self


    def append(self, new_node):
        """Add node at end."""
        if self._head is None:
            self.prepend(new_node)
        else:
            self.insert_after(self._tail, new_node)

        return self


    def prepend(self, new_node):
        """Add node at start."""
        if self._head is None:
            self._head = new_node
            self._tail = new_node
            new_node.parent_node = self.parent
            new_node.prev = None
            new_node.next = None
            self._list_size += 1
        else:
            self.insert_before(self._head, new_node)

        return self


    def extend(self, new_list):
        """Add list at end."""
        if self._head is None:
            self._head = new_list._head
            self._tail = new_list._tail
            self.parent = new_list.parent
            self._list_size = new_list._list_size
        else:
            new_list._head.prev = self._tail
            self._tail.next = new_list._head
            self._tail = new_list._tail
            new_list.parent = self.parent
            self._list_size += new_list._list_size

        for node in new_list:
            node.parent_node = self.parent

        return self



    def remove(self, node):
        """Remove node."""
        if not self.is_linked(node):
            return self

        if node.prev is None:
            self._head = node.next
        else:
            node.prev.next = node.next

        if node.next is None:
            self._tail = node.prev
        else:
            node.next.prev = node.prev

        self._list_size -= 1
        return self


    def pop(self):
        """Remove last."""
        if self.is_empty():
            return None
        node = self._tail
        if self._tail.prev is not None:
            self._tail.prev.next = None
        self._tail = self._tail.prev
        self._list_size -= 1
        node.prev = None
        node.next = None
        return node


    def shift(self):
        """Remove first."""
        if self.is_empty():
            return None
        node = self._head
        if self._head.next is not None:
            self._head.next.prev = None
        self._head = self._head.next
        self._list_size -= 1
        node.prev = None
        node.next = None
        return node
