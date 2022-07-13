
"""
markup2
~~~~~~~~

RST markup tools.
"""

import re
from difflib import SequenceMatcher

import monostyle.util.monostyle_io as monostyle_io
from monostyle.util.fragment import Fragment
from monostyle.util.report import Report
from monostyle.rst_parser.core import RSTParser
import monostyle.rst_parser.environment as env
import monostyle.rst_parser.walker as rst_walker
from monostyle.util.porter_stemmer import Porterstemmer


def glossary_pre(_):
    rst_parser = RSTParser()
    terms = set()
    terms_glossary = set()
    glossary_code = None
    glossary_filenames = []
    for filename, text in monostyle_io.doc_texts():
        document = rst_parser.parse(rst_parser.document(filename, text))

        for node in rst_walker.iter_node(document.body, ("dir", "role",)):
            if rst_walker.is_of(node, "*", "glossary"):
                glossary_code = node.code
                glossary_filenames.append(glossary_code.filename)

            elif rst_walker.is_of(node, "*", "term"):
                if glossary_code and glossary_code.is_in_span(node.code.start_pos):
                    terms_glossary.add(str(node.head).strip())
                else:
                    terms.add(str(node.head).strip())

    terms_glossary -= terms
    terms.update(terms_glossary)
    args = dict()
    args["data"] = dict(terms=terms, terms_glossary=terms_glossary,
                        glossary_filenames=glossary_filenames)
    return args


def glossary(toolname, document, reports, data):
    """Unused glossary terms or within glossary only."""
    if document.code.filename not in data["glossary_filenames"]:
        return reports

    for node in rst_walker.iter_node(document.body, "dir", enter_pos=False):
        if rst_walker.is_of(node, "*", "glossary"):
            for def_node in rst_walker.iter_node(node.body, "def", enter_pos=False):
                for line in def_node.head.code.splitlines():
                    line_strip = str(line).strip()
                    if line_strip in data["terms_glossary"]:
                        reports.append(Report('I', toolname, def_node.head.code,
                                              "term used only within glossary"))
                        break
                    if line_strip in data["terms"]:
                        break
                else:
                    reports.append(Report('I', toolname, def_node.head.code, "unused term"))

    return reports


def link_titles_pre(_):
    _, targets = env.get_link_titles(RSTParser())

    return {"data": targets}


def link_titles(toolname, document, reports, data):
    """Find internal (ref) links title mismatches the heading title."""
    for node in rst_walker.iter_node(document.body, "role"):
        if rst_walker.is_of(node, "*", "ref") and node.head:
            id_str = str(node.id.code).strip()
            for target, title_head in data.items():
                if target == id_str:
                    sim = SequenceMatcher(lambda x: x == " ", str(title_head.code).lower(),
                                          str(node.head.code).lower()).ratio()
                    if sim < 0.9:
                        reports.append(
                            Report('W', toolname, node.head.code,
                                   "link title mismatches heading title: {:4.0%}".format(sim),
                                   title_head))

    return reports


def local_targets_pre(_):
    links = []
    targets = []
    rst_parser = RSTParser()

    for filename, text in monostyle_io.doc_texts():
        document = rst_parser.parse(rst_parser.document(filename, text))
        for node in rst_walker.iter_node(document.body, {"target", "role"}):
            if node.node_name == "target":
                if (document.code.filename.endswith("index.rst") or
                        str(node.id.code).startswith("bpy.")):
                    continue
                targets.append(node)
            elif rst_walker.is_of(node, "role", "ref"):
                links.append(node.id.code)

    args = dict()
    args["data"] = dict(targets=targets, links=links)
    return args


def local_targets(toolname, reports, data):
    """Find internal (ref) links used on same page only."""
    for node in data["targets"]:
        is_same_file = False
        is_multi = False
        id_str = str(node.id.code).strip()
        for link_code in data["links"]:
            if id_str == str(link_code).strip():
                if node.code.filename == link_code.filename:
                    is_same_file = True
                else:
                    is_multi = True
                    break

        # false positives: non heading targets, title not heading
        if is_same_file and not is_multi:
            if not id_str.startswith("fig-") and not id_str.startswith("tab-"):
                reports.append(Report('I', toolname, node.id.code, "local target"))

    return reports


def page_name(toolname, document, reports):
    """Compare page title and file name."""
    porter_stemmer = Porterstemmer()

    page = re.search(r"/([\w\-_]+?)(?:/index)?\.rst$", document.code.filename).group(1)
    page_split = []
    for word in re.split(r"[_-]", page):
        page_split.append(porter_stemmer.stem(word, 0, len(word)-1))

    threshold = (0.5, 0.33, 0.25)
    for node in rst_walker.iter_node(document.body, "sect", enter_pos=False):
        head = str(node.name.code).lower().strip()
        head = re.sub(r"\b(\w)\-", r"\1", head)
        head = re.sub(r"[&/,-]", " ", head)
        head_split = []
        for word in re.split(r"\s+", head):
            head_split.append(porter_stemmer.stem(word, 0, len(word)-1))

        acronym = []
        match_count = 0
        was_kind = True
        for word in reversed(head_split):
            if word in {"the", "a", "an", "to", "in", "on", "from"}:
                match_count += 1
                continue

            acronym.insert(0, word[0])

            if was_kind:
                found = False
                for kind in {"node", "texture", "strip", "effect", "constraint", "modifier",
                             "physics", "editor", "panel"}:
                    if kind.startswith(word):
                        match_count += 1
                        found = True
                        break
                else:
                    was_kind = False

                if found:
                    continue

            if word in page_split:
                match_count += 1

        sim = match_count / max(1, len(head_split))
        if page == ''.join(acronym):
            sim = 1

        if sim < threshold[0]:
            reports.append(
                Report(Report.map_severity(threshold, sim), toolname, node.name.code,
                       "page title - filename mismatch {:4.0%}".format(sim),
                       Fragment(document.code.filename, page)))

        # break to only process only the first heading
        break

    return reports


def tool_title(toolname, document, reports):
    """Check if a heading matches the tool name in the ref box."""
    last_re = re.compile(r"(?:\-> |\A)([^>]*?)(?:\.\.\.)?\Z")
    for node in rst_walker.iter_node(document.body, "sect", enter_pos=False):
        node_next = node.next
        if node_next.node_name == "text" and node.code.isspace():
            node_next = node_next.next
        if not rst_walker.is_of(node_next, "dir", "reference"):
            continue

        heading_str = str(node.name.code).strip()
        sim_max = -0.001
        tool_max = None
        for node_role in rst_walker.iter_node(node_next.body, ("role", ), False):
            if rst_walker.is_of(node_role, "role", "menuselection"):
                if last_m := re.search(last_re, str(node_role.body.code)):
                    if last_m.group(1) == heading_str:
                        break

                    sim = SequenceMatcher(lambda x: x == " ", last_m.group(1),
                                          heading_str).ratio()
                    if max(sim, 0) > sim_max:
                        tool_max = node_role.body.code.slice_match(last_m, 1)
                        sim_max = sim

        else:
            reports.append(
                Report('W', toolname, node.name.code,
                       Report.missing(what="tool name match", where="in ref box") +
                       ":{:4.0%}".format(sim_max), tool_max))

    return reports


def unused_targets_pre(_):
    links = []
    targets = []
    rst_parser = RSTParser()

    for filename, text in monostyle_io.doc_texts():
        document = rst_parser.parse(rst_parser.document(filename, text))
        for node in rst_walker.iter_node(document.body, {"target", "role", "subst"}):
            if node.node_name == "target":
                if (document.code.filename.endswith("index.rst") or
                        str(node.id.code).startswith("bpy.")):
                    continue
                targets.append(node)
            elif (rst_walker.is_of(node, "role", "ref") or
                    (node.node_name == "subst" and
                     str(node.body_end.code).strip().endswith("_"))):
                links.append(str(node.id.code).strip())

    args = dict()
    args["data"] = dict(targets=targets, links=links)
    return args


def unused_targets(toolname, reports, data):
    """Find unused internal (ref) targets."""
    for node in data["targets"]:
        if str(node.id.code).strip() not in data["links"]:
            reports.append(Report('W', toolname, node.id.code, "unused target"))

    return reports


OPS = (
    ("glossary", glossary, glossary_pre, True),
    ("link-titles", link_titles, link_titles_pre, True),
    ("local-targets", local_targets, local_targets_pre, False),
    ("page-name", page_name, None, True),
    ("tool-title", tool_title, None, True),
    ("unused-targets", unused_targets, unused_targets_pre, False),
)

if __name__ == "__main__":
    from monostyle.__main__ import main_mod
    main_mod(__doc__, OPS, __file__)
