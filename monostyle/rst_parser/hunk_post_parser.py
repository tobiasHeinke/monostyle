
"""
rst_parser.hunk_post_parser
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrofit cut off node parts in differential hunks after main parsing.
"""

import re
from monostyle.util.fragment import Fragment
from monostyle.rst_parser.rst_node import NodeRST, NodePartRST


def parse(rst_parser, document):
    """Find partial markup by deriving the node_name from the node's body."""
    document = toctree(rst_parser, document)
    document = refbox(rst_parser, document)

    return document


def toctree(rst_parser, document):
    """Find partial toctree directives."""
    doc_re = re.compile(r"\A *\S([^ \\/]+?[\\/])*[^ \\/]+?\.rst(?:$|\Z)")
    node = document.body.child_nodes.first()
    if node.node_name == "text" and node.code.isspace():
        node = node.next
    if not node or node.node_name != "block-quote":
        return document

    node_child = node.body.child_nodes.first()
    field_node = None
    if node_child and node_child.node_name == "field-list":
        field_node = node_child
        if first_field := node_child.body.child_nodes.first():
            if first_field.indent.code.end_pos == 0:
                return document

            node_child = node_child.next

    if node_child and node_child.node_name == "text":
        is_empty = True
        for line in node_child.code.splitlines():
            line_str = str(line)
            if len(line_str.strip()) != 0:
                is_empty = False
                sub_node = rst_parser.parse_inline(NodeRST("", line), "link")
                if (len(sub_node.child_nodes) > 1 and
                        sub_node.child_nodes[1].node_name == "link"):
                    line_str = str(sub_node.child_nodes[1].body.code)

                if not re.match(doc_re, line_str):
                    break

        else:
            if not is_empty:
                node.node_name = "dir"
                if field_node:
                    field_node.parent_node.child_nodes.remove(field_node)
                    node.attr = NodePartRST("attr", field_node.code)
                    node.attr.append_child(field_node, False)
                    node.child_nodes.prepend(node.attr)

                doc = rst_parser.parse(rst_parser.document(
                          code=Fragment(document.code.filename, [".. toctree::\n"],
                                        -1, -1, (-1, 0), (-1, 0))))
                part_transfer(node, doc.body.child_nodes.first())

    return document


def refbox(rst_parser, document):
    """Find partial reference directives."""
    node = document.body.child_nodes.first()
    if node.node_name == "text" and node.code.isspace():
        node = node.next
    if not node or node.node_name != "block-quote":
        return document

    node_child = node.body.child_nodes.first()
    if node_child and node_child.node_name == "field-list":
        for field_node in node_child.body.child_nodes:
            if (str(field_node.name).strip() not in
                    {"Shortcut", "Menu", "Panel", "Mode", "Tool",
                     "Editor", "Header", "Type", "Context"}):
                break
        else:
            node.node_name = "dir"
            doc = rst_parser.parse(rst_parser.document(
                      code=Fragment(document.code.filename, [".. reference::\n"],
                                    -1, -1, (-1, 0), (-1, 0))))
            part_transfer(node, doc.body.child_nodes.first())

    return document


def part_transfer(node, node_virtual):
    """Move node parts from one node to another."""
    for part in node_virtual.child_nodes:
        setattr(node, part.node_name, part)
