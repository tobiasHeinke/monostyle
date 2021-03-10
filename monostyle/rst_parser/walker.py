
"""
rst_parser.walker
~~~~~~~~~~~~~~~~~

RST node tree walker.
"""

from monostyle.rst_parser.rst_node import NodeRST


def iter_node(root, names=None, enter_pos=True, leafs_only=False, output_root=False):
    """Iterate over nodes.
    names -- node.node_name must positive match.
    enter_pos -- iterate child nodes of positive matches.
    leafs_only -- yield only leaf nodes.
    output_root -- yield the root as first.
    """
    if isinstance(names, str):
        names = {names,}

    if isinstance(root, NodeRST):
        if output_root:
            yield root

        for part in root.child_nodes:
            yield from iter_node(part, names, enter_pos, leafs_only)
    else:
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
                        yield from iter_node(part, names, enter_pos, leafs_only)


def iter_nodeparts(root, names=None, enter_pos=True, leafs_only=True, output_root=False):
    """Iterate over node parts.
    names -- part.node_name must positive match.
    enter_pos -- iterate child nodes of positive matches.
    leafs_only -- yield only leaf nodes.
    output_root -- yield the root as first.
    """
    if isinstance(names, str):
        names = {names,}

    if not isinstance(root, NodeRST):
        for node in root.child_nodes:
            yield from iter_nodeparts(node, names, enter_pos, leafs_only)
    else:
        if output_root:
            yield root

        for part in root.child_nodes:
            enter = True
            if not names or part.node_name in names:
                enter = enter_pos

                if not leafs_only or part.child_nodes.is_empty():
                    yield part

            if enter and not part.child_nodes.is_empty():
                yield from iter_nodeparts(part, names, enter_pos, leafs_only)


def iter_nodeparts_instr(root, instr_pos, instr_neg, leafs_only=True, output_root=False):
    """Iterate over node parts.
    instruction format: node.node_name, node.name, part.node_name
    asterisk wildcards matches all or None
    default matches None for default directives or roles
    """
    def rules(name, instr):
        if instr is True or instr is False:
            return instr

        is_dict = bool(isinstance(instr, dict))
        if is_dict:
            keys = set(instr.keys())
        elif isinstance(instr, str):
            keys = {instr,}
        else:
            keys = instr

        if name is None:
            name = "default"
        if name not in keys:
            if "*" in keys:
                name = "*"
            else:
                return False

        if is_dict:
            return instr[name]
        return True

    if isinstance(root, NodeRST):
        for node in root.child_nodes:
            yield from iter_nodeparts_instr(node, instr_pos, instr_neg, leafs_only)
    else:
        if output_root:
            yield root

        for node in root.child_nodes:
            instr_portion_pos = rules(node.node_name, instr_pos)
            if not instr_portion_pos:
                continue
            instr_portion_neg = rules(node.node_name, instr_neg)
            if instr_portion_neg is True:
                continue

            name_str = str(node.name.code).strip() if node.name is not None else None
            instr_portion_pos = rules(name_str, instr_portion_pos)
            if not instr_portion_pos:
                continue
            instr_portion_neg = rules(name_str, instr_portion_neg)
            if instr_portion_neg is True:
                continue
            for part in node.child_nodes:
                if (rules(part.node_name, instr_portion_pos) and
                        not rules(part.node_name, instr_portion_neg)):
                    if not part.child_nodes.is_empty():
                        if not leafs_only:
                            yield part

                        yield from iter_nodeparts_instr(part, instr_pos, instr_neg, leafs_only)

                    else:
                        yield part


def is_of(node, node_name_rule, name_rule=None, part_node_name_rule=None):
    """Check if node and part node_name matches the rules.
    instruction format: node.node_name, node.name, part.node_name
    asterisk wildcard matches all or None
    default matches None thus for default directives or roles
    """
    if node is None:
        return False

    if isinstance(node, NodeRST):
        part = None
    else:
        part = node
        node = part.parent_node

    for name, rule in ((node.node_name, node_name_rule), (str(node.name.code).strip()
                       if name_rule is not None and node.name is not None else "default",
                       name_rule), (part.node_name if part else None, part_node_name_rule)):

        if rule is None:
            continue
        if not isinstance(rule, str):
            if not("*" in rule or name in rule):
                return False
        elif not(rule == "*" or rule == name):
            return False

    return True


def to_node(node):
    """Return part's parent if it's a part."""
    if not node:
        return node
    return node if isinstance(node, NodeRST) else node.parent_node


def get_attr(node, name):
    """Return the first attribute node's body with a matching lowercase name."""
    if node.attr and not node.attr.child_nodes.is_empty():
        field_list = node.attr.child_nodes.first()
        if not field_list.child_nodes.is_empty():
            for field_node in field_list.child_nodes.last().child_nodes:
                if str(field_node.name).strip().lower() == name:
                    return field_node.body


def write_out(node_name, name=False):
    """Write out shortened node_name and name."""
    node_name_map = {
        "enum": "enumeration",
        "dir": "directive",
        "substdef": "substitution definition",
        "footdef": "footnote definition",
        "citdef": "citation definition",
        "trans": "transition",
        "sect": "section",
        "def": "definition",
        "int-target": "internal target",
        "subst": "substitution reference",
        "foot": "footnote reference",
        "cit": "citation reference"
    }
    result = ""
    if name is not False and node_name in {"dir", "role"}:
        result = (str(name).strip() if name is not None else "default") + " "
    if not node_name.endswith("-list") and not node_name.endswith("-table"):
        result += node_name_map.get(node_name, node_name)
    else:
        node_name = node_name.split("-")
        result += node_name_map.get(node_name[0], node_name[0])
        result += " " + node_name[1]
    return result
