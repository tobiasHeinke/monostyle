
"""
rst_parser.hunk_post_parser
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Parse again nodes of differential hunks after main parsing
to derive cut off node_name from the nodes body.
"""

import re
from monostyle.util.fragment import Fragment
from monostyle.rst_parser.rst_node import NodeRST

def parse(rst_parser, document):

    document = toctree(rst_parser, document)
    document = refbox(rst_parser, document)

    return document


def toctree(rst_parser, document):
    doc_re = re.compile(r"\A *\S([^ \\/]+?[\\/])*[^ \\/]+?\.rst(?:$|\Z)")
    node = document.body.child_nodes.first()
    if node.node_name == "text" and node.code.isspace():
        node = node.next
    if node and node.node_name == "block-quote":
        node = node.body.child_nodes.first()

    if node and node.node_name == "field-list":
        if first_field := node.body.child_nodes.first():
            if first_field.indent.code.end_pos == 0:
                return document

            node = node.next

    if node and node.node_name == "text":
        is_empty = True
        for line in node.code.splitlines():
            line_str = str(line)
            if len(line_str.strip()) != 0:
                is_empty = False
                sub_node = rst_parser.parse_inline(NodeRST("", line), "link")
                if (len(sub_node.child_nodes) > 1 and
                        sub_node.child_nodes[1].node_name == "link"):
                    line_str = str(sub_node.child_nodes[1].code)

                if not re.match(doc_re, line_str):
                    break

        else:
            if not is_empty:
                node.node_name = "dir"
                fg = Fragment(document.code.fn, [".. toctree::\n"], -1, -1, (-1, 0), (-1, 0))
                doc = rst_parser.parse_full(rst_parser.snippet(fg))
                part_transfer(node, doc.body.child_nodes.first())
                # the field-list is not made attr

    return document


def refbox(rst_parser, document):
    def rename(rst_parser, node, add_class):
        node.node_name = "dir"
        fg = Fragment(document.code.fn,
                      [".. admonition:: Reference\n"
                       "   :class: refbox\n" if add_class else ""],
                      -1, -1, (-1, 0), (-1, 0))
        doc = rst_parser.parse_full(rst_parser.snippet(fg))
        part_transfer(node, doc.body.child_nodes.first())

    node = document.body.child_nodes.first()
    if node.node_name == "text" and node.code.isspace():
        node = node.next
    if node and node.node_name == "block-quote":
        node = node.body.child_nodes.first()

    if node and node.node_name == "field-list":
        field_node = node.body.child_nodes.first()
        if (str(field_node.name).strip() == "class" and
                str(field_node.body).strip() == "refbox"):
            rename(rst_parser, node, False)

        else:
            for field_node in node.body.child_nodes:
                if (str(field_node.name).strip() not in ("Hotkey", "Menu", "Panel", "Mode", "Tool",
                                                         "Editor", "Header", "Type", "Context")):
                    break

            else:
                rename(rst_parser, node, True)

    return document


def part_transfer(node, virt):
    for part in virt.child_nodes:
        setattr(node, part.node_name, part)
