
"""
rst_parser.environment
~~~~~~~~~~~~~~~~~~~~~~

Insert referenced content.
"""

import monostyle.util.monostyle_io as monostyle_io
import monostyle.rst_parser.walker as rst_walker


def get_link_titles(rst_parser):
    """Get titles."""
    def detach(node, child):
        node.child_nodes.remove(child)
        child.detach()
        return child

    targets = {}
    titles = {}

    for filename, text in monostyle_io.doc_texts():
        doc = rst_parser.document(filename, text)
        doc.body = rst_parser.parse_block(doc.body)
        for node in rst_walker.iter_node(doc.body, "sect"):
            filename = monostyle_io.path_to_rel(filename, "doc")
            filename = '/' + filename[:-4]

            titles[filename] = detach(node, node.name)
            break

        for node in rst_walker.iter_node(doc.body, "target"):
            node_next = node.next
            while node_next:
                if (node_next.node_name in {"target", "comment", "substdef"} or
                        rst_walker.is_blank_text(node_next) or
                        rst_walker.is_of(node_next, "dir", "highlight")):
                    node_next = node_next.next
                else:
                    if node_next.node_name == "sect":
                        targeted = detach(node_next, node_next.name)
                    else:
                        targeted = detach(node_next, node_next.body)
                    targets[str(node.id.code).strip()] = targeted
                    break

    return titles, targets


def resolve_link_title(document, titles, targets):
    """Insert the link title if it is not set in the role."""
    for node in rst_walker.iter_node(document.body, "role"):
        name = str(node.name.code).strip() if node.name else ""
        if name in {"doc", "ref", "any"} and not node.head:
            link_content = str(node.id.code).strip()
            found = False
            if name in {"doc", "any"} and link_content in titles.keys():
                node.insert_part("head", titles[link_content].code, node.body_start)
                node.head.child_nodes = titles[link_content].child_nodes
                found = True
            if not found and name in {"ref", "any"} and link_content in targets.keys():
                node.insert_part("head", targets[link_content].code, node.body_start)
                node.head.child_nodes = targets[link_content].child_nodes
                found = True

            if not found:
                print("{0}:{1}: resolve link titles: unknown {2}:\n{3}"
                      .format(node.id.code.filename, node.id.code.start_lincol[0],
                              name, link_content))

    return document


def resolve_subst(document, gobal_substdef):
    """Insert the referenced content in substitutions.

    Iterative dependency graph resolution.

    Adapted from:
    Dependency resolution example in Python by Mario Vilas (mvilas at gmail dot com).
    https://breakingcode.wordpress.com/2013/03/11/an-example-dependency-resolution-algorithm-in-python/
    """
    graph = dict((key, {"content": value, "deps": set(), "global": True})
                 for key, value in gobal_substdef.items())

    refs = {}
    for node in rst_walker.iter_node(document.body, {"substdef", "subst"}):
        id_str = str(node.id.code).strip() if node.id else ""
        if node.node_name == "subst":
            if id_str not in refs.keys():
                refs.setdefault(id_str, [])
            refs[id_str].append(node)
        else:
            deps = set()
            for node_subst in rst_walker.iter_node(node.head, "subst"):
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
        ready = dict((key, value) for key, value in graph.items() if not value["deps"])
        if not ready:
            print("{0}: Circular dependencies in substitutions".format(document.code.filename))
            break

        for key, entry in ready.items():
            if key in refs.keys():
                for node in refs[key]:
                    if not node.head:
                        if entry["global"]:
                            node.insert_part("head", entry["content"], node.body_start)
                        else:
                            node.insert_part("head", entry["content"].code, node.body_start)
                            node.head.child_nodes = entry["content"].child_nodes

                del refs[key]

            for value in graph.values():
                value["deps"].discard(key)
            del graph[key]

    return document
