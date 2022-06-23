
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


    def detach(self):
        """Remove links of the node."""
        self.prev = None
        self.next = None
        self.parent_node = None
        return self


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


    def copy(self, linked=False):
        """Create a copy the node."""
        new = type(self)()
        for prop in self.__dict__.keys():
            if linked or prop not in self.__slots__.keys():
                setattr(new, prop, getattr(self, prop))
        return new


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
        items = type(self)(self.parent)
        for node in self:
            items.append(node.copy(linked=False))
        return items


    def clear(self):
        """Empty the list."""
        return self.__init__(self.parent)


    def is_linked(self, item):
        """Check if the node is connected with other nodes."""
        return not ((item and item.prev is None and item.next is None
                     and self._tail is not item and self._head is not item)
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


    def __contains__(self, item):
        """Checks if the node is in the list."""
        if not self.is_linked(item):
            return False

        for node in self:
            if node is item:
                return True

        return False


    def count(self, item):
        """Return count of the node."""
        if not hasattr(item, "__eq__"):
            raise NotImplementedError("Node requires an __eq__ method to check"
                                      "if payload is identical")

        counter = 0
        if not self.is_linked(item):
            return counter

        for node in self:
            if node is item:
                counter += 1

        return counter


    def index(self, item, start=None, end=None):
        """Return index of node."""
        if not self.is_linked(item):
            return None

        for index, node in enumerate(self):
            if ((start is None or index > start) and
                    (end is None or index < end) and
                    item is node):
                return index


    def __getitem__(self, key):
        """Return node at index."""
        if abs(key) >= self._list_size or not isinstance(key, int):
            raise IndexError()
        if key < 0:
            key = self._list_size - key

        for index, node in enumerate(self):
            if key == index:
                return node


    def __setitem__(self, key, value):
        """Insert node at index."""
        if abs(key) >= self._list_size or not isinstance(key, int):
            raise IndexError()
        if key < 0:
            key = self._list_size - key

        node = self.__getitem__(key)
        if node:
            self.insert_before(node, value)


    def __delitem__(self, key):
        """Remove node."""
        if abs(key) >= self._list_size or not isinstance(key, int):
            raise IndexError()
        if key < 0:
            key = self._list_size - key

        node = self.__getitem__(key)
        if node:
            self.remove(node)


    def insert_after(self, key, item):
        """Add node after reference node."""
        if not self.is_linked(key):
            return self

        item.parent_node = self.parent
        item.prev = key
        item.next = key.next
        if key.next is None:
            self._tail = item
        else:
            key.next.prev = item

        key.next = item
        self._list_size += 1
        return self


    def insert_before(self, key, item):
        """Add node before reference node."""
        if not self.is_linked(key):
            return self

        item.parent_node = self.parent
        item.prev = key.prev
        item.next = key
        if key.prev is None:
            self._head = item
        else:
            key.prev.next = item

        key.prev = item
        self._list_size += 1
        return self


    def append(self, item):
        """Add node at end."""
        if self._head is None:
            self.prepend(item)
        else:
            self.insert_after(self._tail, item)

        return self


    def prepend(self, item):
        """Add node at start."""
        if self._head is None:
            self._head = item
            self._tail = item
            item.parent_node = self.parent
            item.prev = None
            item.next = None
            self._list_size += 1
        else:
            self.insert_before(self._head, item)

        return self


    def extend(self, items):
        """Add list at end."""
        if self._head is None:
            self._head = items._head
            self._tail = items._tail
            self.parent = items.parent
            self._list_size = items._list_size
        else:
            items._head.prev = self._tail
            self._tail.next = items._head
            self._tail = items._tail
            items.parent = self.parent
            self._list_size += items._list_size

        for node in items:
            node.parent_node = self.parent

        return self



    def remove(self, item):
        """Remove node."""
        if not self.is_linked(item):
            return self

        if item.prev is None:
            self._head = item.next
        else:
            item.prev.next = item.next

        if item.next is None:
            self._tail = item.prev
        else:
            item.next.prev = item.prev

        self._list_size -= 1
        return self


    def pop(self):
        """Remove last."""
        if self.is_empty():
            return None
        item = self._tail
        if self._tail.prev is not None:
            self._tail.prev.next = None
        self._tail = self._tail.prev
        self._list_size -= 1
        item.prev = None
        item.next = None
        return item


    def shift(self):
        """Remove first."""
        if self.is_empty():
            return None
        item = self._head
        if self._head.next is not None:
            self._head.next.prev = None
        self._head = self._head.next
        self._list_size -= 1
        item.prev = None
        item.next = None
        return item
