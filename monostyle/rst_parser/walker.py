
"""
rst_parser.walker
~~~~~~~~~~~~~~~~~

RST node tree walker.
"""

from monostyle.util.nodes import Node, LinkedList
from monostyle.rst_parser.rst_node import NodeRST, NodePartRST


def iter_node(root, names=None, enter_pos=True, leafs_only=False):
    for node in root.child_nodes:
        enter = True
        if not names or node.node_name in names:
            enter = enter_pos
            if leafs_only:
                for part in node.child_nodes:
                    if not part.child_nodes.is_empty():
                        break
                else:
                    yield node
            else:
                yield node

        if enter:
            for part in node.child_nodes:
                if not part.child_nodes.is_empty():
                    yield from iter_node(part, names, enter_pos)


def iter_nodeparts(root, leafs_only=True):
    for node in root.child_nodes:
        for part in node.child_nodes:
            if not part.child_nodes.is_empty():
                if not leafs_only:
                    yield part
                yield from iter_nodeparts(part)
            else:
                yield part


def iter_nodeparts_instr(root, instr_pos, instr_neg, leafs_only=True):
    """Iterate over node parts.
    instruction format: node.node_name, node.name, part.node_name
    asterisk wildcards matches all or None
    node.name: default for default directive or role
    """
    def rules(node, instr, posneg):
        enter = False
        part_node_name_rule = None

        if node.node_name in instr.keys():
            node_name_rule = instr[node.node_name]
            enter = posneg
        elif "*" in instr.keys():
            node_name_rule = instr["*"]
            enter = posneg
        else:
            node_name_rule = None
            enter = not posneg

        if enter == posneg:
            node_name = str(node.name.code).strip() if node.name is not None else None

            if node_name_rule and not isinstance(node_name_rule, str):
                if node_name in node_name_rule.keys():
                    part_node_name_rule = node_name_rule[node_name]
                    enter = True
                elif node_name is None and "default" in node_name_rule.keys():
                    part_node_name_rule = node_name_rule["default"]
                    enter = True
                elif "*" in node_name_rule.keys():
                    part_node_name_rule = node_name_rule["*"]
                    enter = True
                else:
                    enter = not posneg
            else:
                if node_name == node_name_rule:
                    enter = posneg
                elif "*" == node_name_rule:
                    enter = posneg
                else:
                    enter = not posneg

        return enter, part_node_name_rule


    for node in root.child_nodes:
        enter, part_node_name_rule_pos = rules(node, instr_pos, True)
        if not enter:
            continue

        enter, part_node_name_rule_neg = rules(node, instr_neg, False)
        if enter:
            for part in node.child_nodes:
                if ((part_node_name_rule_pos is None or part_node_name_rule_pos == "*" or
                         part.node_name in part_node_name_rule_pos) and
                        (part_node_name_rule_neg is None or
                         not (part_node_name_rule_neg == "*" or
                              part.node_name in part_node_name_rule_neg))):

                    if not part.child_nodes.is_empty():
                        if not leafs_only:
                            yield part

                        yield from iter_nodeparts_instr(part, instr_pos, instr_neg, leafs_only)

                    else:
                        yield part


def is_of(node, node_name_rule, name_rule=None, part_node_name_rule=None):
    """Iter over node parts.
    instruction format: node.node_name, node.name, part.node_name
    asterisk wildcards matches all or None
    node.name: default for default directive or role
    """
    if node is None:
        return False

    if isinstance(node, NodeRST):
        part = None
    else:
        part = node
        node = part.parent_node

    if not isinstance(node_name_rule, str):
        if (not("*" in node_name_rule or
                node.node_name in node_name_rule)):
            return False
    elif (not("*" == node_name_rule or
              node.node_name == node_name_rule)):
        return False

    if name_rule is not None:
        if not isinstance(name_rule, str):
            if (not("*" in name_rule or
                    (not node.name and "default" in name_rule) or
                    (node.name and str(node.name.code).strip() in name_rule))):
                return False
        elif (not("*" == name_rule or
                  (not node.name and "default" == name_rule) or
                  (node.name and str(node.name.code).strip() == name_rule))):
            return False

    if part and part_node_name_rule is not None:
        if not isinstance(part_node_name_rule, str):
            if (not("*" in part_node_name_rule or
                    part.node_name in part_node_name_rule)):
                return False
        elif (not("*" == part_node_name_rule or
                  part.node_name == part_node_name_rule)):
            return False

    return True


def get_attr(node, name):
    """Return the first attribute node's body with a matching lowercase name."""
    if node.attr and not node.attr.child_nodes.is_empty():
        field_list = node.attr.child_nodes.first()
        if not field_list.child_nodes.is_empty():
            for field_node in field_list.child_nodes.last().child_nodes:
                if str(field_node.name).strip().lower() == name:
                    return field_node.body
