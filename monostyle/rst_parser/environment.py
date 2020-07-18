
"""
rst_parser.environment
~~~~~~~~~~~~~~~~~~~~~~

Insert referenced content.
"""

import monostyle.util.monostylestd as monostylestd
import monostyle.rst_parser.walker as rst_walker


def get_link_titles(rst_parser):
    """Get titles."""
    targets = {}
    titles = {}

    for fn, text in monostylestd.rst_texts():
        doc = rst_parser.document(fn, text)
        doc.body = rst_parser.parse_block(doc.body)
        for node in rst_walker.iter_node(doc.body, ("sect",)):
            fn = monostylestd.path_to_rel(fn, "rst")
            fn = '/' + fn[:-4]

            titles[fn] = node.name
            break

        for node in rst_walker.iter_node(doc.body, ("target",)):
            node_next = node.next
            while node_next:
                if (node_next.node_name in {"target", "comment", "substdef"} or
                        (node_next.node_name == "text" and node_next.code.isspace()) or
                        rst_walker.is_of(node_next, "dir", "highlight")):
                    node_next = node_next.next
                else:
                    if node_next.node_name == "sect":
                        targeted = node_next.name
                    else:
                        targeted = node_next.body
                    targets[str(node.id.code).strip()] = targeted
                    break
        break

    return titles, targets


def resolve_link_title(document, titles, targets):
    """Insert the link title if it is not set in the role."""

    for node in rst_walker.iter_node(document.body, ("role",)):
        name = str(node.name.code).strip() if node.name else ""
        if name in {"doc", "ref", "any"} and  not node.head:
            link_content = str(node.id.code).strip()
            found = False
            if name in {"doc", "any"} and link_content in titles.keys():
                node.insert_part("head", titles[link_content].code)
                node.head.child_nodes = titles[link_content].child_nodes
                found = True
            if not found and name in {"ref", "any"} and link_content in targets.keys():
                node.insert_part("head", targets[link_content].code)
                node.head.child_nodes = targets[link_content].child_nodes
                found = True

            if not found:
                print("{0}:{1}: resolve link titles: unknown {2}:\n{3}".format(
                      node.id.code.fn, node.id.code.start_lincol[0], name, link_content))

    return document


def resolve_subst(document, gobal_substdef):
    """Insert the refenced content in substitutions.

    Iterative dependency graph resolution.

    Adapted from:
    Dependency resolution example in Python by Mario Vilas (mvilas at gmail dot com).
    https://breakingcode.wordpress.com/2013/03/11/an-example-dependency-resolution-algorithm-in-python/
    """

    graph = dict((key, {"content": val, "deps": set(), "global": True})
                 for key, val in gobal_substdef.items())

    refs = {}
    for node in rst_walker.iter_node(document.body, ("substdef", "subst")):
        id_str = str(node.id.code).strip() if node.id else ""
        if node.node_name == "subst":
            if id_str not in refs.keys():
                refs.setdefault(id_str, [])
            refs[id_str].append(node)
        else:
            deps = set()
            for node_subst in rst_walker.iter_node(node.head, ("subst",)):
                sub_id_str = str(node_subst.id.code).strip() if node.id else ""
                if sub_id_str not in refs.keys():
                    refs.setdefault(sub_id_str, [])
                refs[sub_id_str].append(node_subst)
                deps.add(sub_id_str)

            graph[id_str] = {
                "content": node.head,
                "deps": deps,
                "global": False
            }

    while graph:
        ready = dict((key, val) for key, val in graph.items() if not val["deps"])
        if not ready:
            print("{0}: Circular dependencies in substitutions".format(document.code.fn))
            break

        for key, ent in ready.items():
            if key in refs.keys():
                for node in refs[key]:
                    if not node.head:
                        if ent["global"]:
                            node.insert_part("head", ent["content"], node.body_start)
                        else:
                            node.insert_part("head", ent["content"].code, node.body_start)
                            node.head.child_nodes = ent["content"].child_nodes

                del refs[key]

            for val in graph.values():
                val["deps"].discard(key)
            del graph[key]

    return document
