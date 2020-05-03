
"""
rst_parser.hunk_post_parser
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Parse again nodes of differential hunks after main parsing
to derive cut off node_name from the nodes body.
"""

import re
from monostyle.util.fragment import Fragment
from monostyle.rst_parser.rst_node import NodeRST, NodePartRST

def parse(rst_parser, document):

    document = toctree(rst_parser, document)
    # document = refbox(document)

    return document


def toctree(rst_parser, document):
    doc_re = re.compile(r"\A *\S([^ \\/]+?[\\/])*[^ \\/]+?\.rst(?:$|\Z)")
    first_attr = True
    for node in document.body.child_nodes:
        if node.node_name == "text":
            is_empty = True
            for line in node.code.splitlines():
                line_str = str(line)
                if len(line_str.strip()) != 0:
                    is_empty = False
                    sub_node = NodeRST("", line)
                    sub_node = rst_parser.parse_inline(sub_node, "link")
                    if (len(sub_node.child_nodes) > 1 and
                            sub_node.child_nodes[1].node_name == "link"):
                        line_str = str(sub_node.child_nodes[1].code)

                    if not re.match(doc_re, line_str):
                        break

            else:
                if not is_empty:
                    node.node_name = "dir"
                    fg = Fragment(document.code.fn, ["toctree"], -1, -1, (-1, 0), (-1, 0))
                    node.name = NodePartRST("name", fg)
                    break

        elif node.node_name == "field-list":
            if first_attr:
                if first_field := node.body.child_nodes.first():
                    if first_field.indent.code.end_pos != 0:
                        first_attr = False
                        continue

            break

    return document


def refbox(document):
    def rename(node, add_class):
        node.node_name = "dir"
        fg = Fragment(document.code.fn, ["admonition"], -1, -1, (-1, 0), (-1, 0))
        node.name = NodePartRST("name", fg)
        node.attr = NodeRST("field-list", None)
        node.attr.body = NodePartRST("body", None)
        if not add_class:
            node.attr.body.child_nodes.append(node.body.child_nodes.shift())
        if add_class:
            newnode = NodeRST("field", None)
            fg = Fragment(document.code.fn, ["class"], -1, -1, (-1, 0), (-1, 0))
            newnode.name = NodePartRST("name", fg)
            fg = Fragment(document.code.fn, ["refbox"], -1, -1, (-1, 0), (-1, 0))
            newnode.body = NodePartRST("body", fg)
            node.attr.body.child_nodes.append(newnode)

    node = document.body.child_nodes.first()
    if node.node_name == "text" and node.code.isspace():
        node = node.next

    if node and node.node_name == "field-list":
        field_node = node.body.child_nodes.first()
        if (str(field_node.name).strip() == "class" and
                str(field_node.body).strip() == "refbox"):
            rename(node, False)

        else:
            for field_node in node.body.child_nodes:
                if (str(field_node.name).strip() not in ("Hotkey", "Menu", "Panel", "Mode", "Tool",
                                                         "Editor", "Header", "Type", "Context")):
                    break

            else:
                rename(node, True)

    return document
