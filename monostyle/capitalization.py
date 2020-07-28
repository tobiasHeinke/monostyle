
"""
capitalization
~~~~~~~~~~~~~~

Capitalization tools.
"""

import re

import monostyle.util.monostylestd as monostylestd
from monostyle.util.report import Report, getline_punc
from monostyle.rst_parser.core import RSTParser
import monostyle.rst_parser.walker as rst_walker
from monostyle.util.char_catalog import CharCatalog
from monostyle.util.pos import PartofSpeech
from monostyle.util.segmenter import Segmenter


Segmenter = Segmenter()
POS = PartofSpeech()
CharCatalog = CharCatalog()


def titlecase(word, is_first_word, is_last_word, name):
    """Cicago style titlecase."""

    word_str = str(word)
    if is_first_word or is_last_word:
        if word_str[0].islower():
            if is_first_word:
                where = "at the start of a "
            elif is_last_word:
                where = "at the end of a "
            msg = Report.misformatted(what="lowercase", where=where + name)

            fg_repl = None
            fg_repl = word.slice(word.start_pos, word.start_pos + 1, True)
            fg_repl.content[0] = fg_repl.content[0].swapcase()

            return msg, fg_repl
        return None

    path = POS.classify(word_str.lower())
    if (word_str[0].islower() !=
            (len(path) != 0 and
             (path[0] in ("preposition", "conjunction", "pronoun", "auxiliary") or
              path[0] == "determiner" and path[1] == "article"))):

        msg = Report.misformatted(what="lowercase" if word_str[0].islower() else "uppercase",
                                  where="in " + name)

        fg_repl = None
        if not path or path[0] != "preposition":
            fg_repl = word.slice(word.start_pos, word.start_pos + 1, True)
            fg_repl.content[0] = fg_repl.content[0].swapcase()

        return msg, fg_repl


def admonition_title(document, reports):
    """Case of admonition titles."""
    toolname = "admonition-title"
    threshold = 0.2

    for node in rst_walker.iter_node(document.body, ("dir",)):
        if rst_walker.is_of(node, "*", ('admonition', 'hint', 'important',
                                        'note', 'tip', 'warning')):
            if node.head and node.body:
                word_all = 0
                word_low = 0

                for word in Segmenter.iter_word(node.head.code):
                    word_str = str(word)
                    if len(word_str) >= 4:
                        word_all += 1
                        if word_str[0].islower():
                            word_low += 1
                if word_all > 1 and word_low/ word_all >= threshold:
                    msg = "admonition caption titlecase"
                    msg += ":" + str(round((word_low/ word_all) *100))
                    out = node.head.code.copy()
                    out.content = []
                    reports.append(Report('W', toolname, out, msg, node.head.code))

    return reports


def heading_cap_pre(_):
    re_lib = dict()

    pattern_str = r"\-[a-z]"
    pattern = re.compile(pattern_str)
    msg = Report.misformatted(what="lowercase", where="in heading after hyphen")
    re_lib["hypen"] = (pattern, msg)

    pattern_str = r"[^\w \-&/()'\"\\?!:,\n]"
    pattern = re.compile(pattern_str)
    msg = Report.existing(what="not allowed punctuation", where="in heading")
    re_lib["nonchar"] = (pattern, msg)

    pattern_str = r"\band\b"
    pattern = re.compile(pattern_str, re.IGNORECASE)
    msg = Report.substitution(what="and", where="in heading", with_what="ampersand")
    re_lib["and"] = (pattern, msg)

    pattern_str = r"\bor\b"
    pattern = re.compile(pattern_str, re.IGNORECASE)
    msg = Report.substitution(what="or", where="in heading", with_what="slash")
    re_lib["or"] = (pattern, msg)

    return {"re_lib": re_lib}


def heading_cap(document, reports, re_lib):
    """Check the heading title capitalization."""
    toolname = "heading-capitalization"

    instr_pos = {
        "*": {"*": ["head", "body"]}
    }
    instr_neg = {
        "role": {
            "kbd": "*", "menuselection": "*", "class": "*", "mod": "*", "math": "*"
        },
        "literal": "*", "standalone": "*"
    }

    for node in rst_walker.iter_node(document.body, ("sect",), enter_pos=False):
        is_first_word = True
        is_faq = bool(re.search(r"\?\n", str(node.name.child_nodes.last().code)))
        for part in rst_walker.iter_nodeparts_instr(node.name, instr_pos, instr_neg, False):
            if is_first_word and part.parent_node.prev is not None:
                is_first_word = False

            buf = None
            for word in Segmenter.iter_word(part.code):
                if buf:
                    if msg_repl := titlecase(buf, is_first_word, False, "heading"):
                        reports.append(Report('W', toolname, buf, msg_repl[0], node.name.code,
                                              msg_repl[1]))
                    if is_faq:
                        break
                    is_first_word = False
                buf = word

            if buf and not is_faq:
                # ignore part.next, one part per node
                is_last_word = bool(part.parent_node.next is None)
                if msg_repl := titlecase(buf, is_first_word, is_last_word, "heading"):
                    reports.append(Report('W', toolname, buf, msg_repl[0], node.name.code,
                                          msg_repl[1]))
                is_first_word = False

            part_str = str(part.code)
            for pattern, msg in re_lib.values():
                for m in re.finditer(pattern, part_str):
                    out = part.code.slice_match_obj(m, 0, True)
                    reports.append(Report('W', toolname, out, msg, node.name.code))

    return reports


def pos_case(document, reports):
    """Find Capitalized non-nouns (i.a.) which can be a typo or missing punctuation."""
    toolname = "pos-case"

    instr_pos = {
        "field": {"*": ["name", "body"]},
        "*": {"*": ["head", "body"]}
    }
    instr_neg = {
        "dir": {
            "figure": ["head"],
            "admonition": ["head"], "hint": ["head"], "important": ["head"],
            "note": ["head"], "tip": ["head"], "warning": ["head"], "rubric": ["head"],
            "code-block": "*", "default": "*", "include": "*", "toctree": "*",
            "parsed-literal": "*", "math": "*", "youtube": "*", "vimeo": "*"
        },
        "def": {"*": ["head"]},
        "substdef": {"image": ["head"], "unicode": "*", "replace": "*"},
        "target": "*", "comment": "*",
        "role": "*", "emphasis": "*", "int-target": "*", "hyperlink": "*",
        "literal": "*", "standalone": "*"
    }
    for part in rst_walker.iter_nodeparts_instr(document.body, instr_pos, instr_neg):
        for sen in Segmenter.iter_sentence(part.code):
            is_first_word = True
            for word in Segmenter.iter_word(sen):
                if is_first_word:
                    is_first_word = False
                    continue

                word_str = str(word)
                if word_str[0].islower() or word_str in ("I", "Y"):
                    continue

                path = POS.classify(word_str.lower())
                if len(path) != 0 and path[0] not in ("noun", "abbreviation", "adjective", "verb"):
                    msg = Report.misformatted(what="uppercase " + path[0])
                    reports.append(Report('W', toolname, word, msg, sen))

    return reports


def starting_pre(_):

    re_lib = dict()
    punc_sent = CharCatalog.data["terminal"]["final"] + ':'
    pare_open = CharCatalog.data["bracket"]["left"]["normal"]

    # FP: code, container
    pattern_str = r"[" + pare_open + r"]?[a-z]"
    pattern = re.compile(pattern_str)
    msg = Report.misformatted(what="lowercase", where="at paragraph start")
    re_lib["lowerpara"] = (pattern, msg)

    # todo? split sentence
    # limitation: not nested parenthesis
    # not match abbr
    pattern_str = r"(?<!\w\.\w)[" + punc_sent + r"]\s+?" + r"[" + pare_open + r"]?[a-z]"
    pattern = re.compile(pattern_str, re.MULTILINE | re.DOTALL)
    msg = Report.misformatted(what="lowercase", where="after sentence start")
    re_lib["punclower"] = (pattern, msg)

    # FP: abbr, menu, heading, code
    pattern_str = r"[^.\s]\s*?[" + pare_open + r"][A-Z][a-z ]"
    pattern = re.compile(pattern_str, re.MULTILINE)
    msg = Report.misformatted(what="uppercase", where="at bracket start")
    re_lib["upperbracket"] = (pattern, msg)

    args = dict()
    args["re_lib"] = re_lib

    return args


def starting(document, reports, re_lib):
    """Check case at the start of paragraphs, sentences and parenthesis."""
    toolname = "starting"

    instr_pos = {
        "field": {"*": ["name", "body"]},
        "*": {"*": ["head", "body"]}
    }
    instr_neg = {
        "dir": {
            "figure": ["head"], "toctree": "*", "include": "*",
            "code-block": "*", "default": "*", "youtube": "*", "vimeo": "*"
        },
        "substdef": {"image": ["head"], "unicode": "*", "replace": "*"},
        "literal": "*", "standalone": "*"
    }

    start_re = re_lib["lowerpara"][0]
    was_empty = False
    for part in rst_walker.iter_nodeparts_instr(document.body, instr_pos, instr_neg):
        if not part.parent_node.prev or was_empty:
            if (part.parent_node.node_name == "text" or
                    part.parent_node.parent_node.parent_node.node_name == "text"):

                if re.match(start_re, str(part.code)):
                    out = part.code.copy()
                    out.clear(True)
                    line = getline_punc(document.body.code, out.start_pos, 0, 50, 0)
                    reports.append(Report('W', toolname, out, re_lib["lowerpara"][1], line))

                was_empty = bool(len(part.code) == 0)

        if part.parent_node.node_name == "text":
            part_str = str(part.code)
            for key, value in re_lib.items():
                if key == "lowerpara":
                    continue
                pattern = value[0]
                for m in re.finditer(pattern, part_str):
                    out = part.code.slice_match_obj(m, 0, True)
                    line = getline_punc(document.body.code, out.start_pos, out.span_len(), 50, 0)
                    reports.append(Report('W', toolname, out, value[1], line))

    return reports

def property_noun_pre(_):
    """Build lexicon with lower/uppercase counts."""
    threshold = 0.8
    instr_pos = {
        "field": {"*": ["name", "body"]},
        "*": {"*": ["head", "body"]}
    }
    instr_neg = {
        "dir": {
            "figure": ["head"],
            "code-block": "*", "default": "*", "include": "*", "toctree": "*",
            "parsed-literal": "*", "math": "*", "youtube": "*", "vimeo": "*"
        },
        "substdef": {"image": ["head"], "unicode": "*", "replace": "*"},
        "target": "*", "comment": "*",
        "role": {
            "kbd": "*", "class": "*", "mod": "*", "math": "*"
        },
        "literal": "*", "standalone": "*"
    }

    lexicon = dict()
    rst_parser = RSTParser()
    for fn, text in monostylestd.rst_texts():
        document = rst_parser.parse_full(rst_parser.document(fn, text))

        first = True
        for part in rst_walker.iter_nodeparts_instr(document.body, instr_pos, instr_neg):
            for sen in Segmenter.iter_sentence(part.code):
                for word in Segmenter.iter_word(sen):
                    if first:
                        first = False
                        continue

                    word_str = str(word)
                    word_lower = word_str.lower()
                    first_letter = word_lower[0]
                    # tree with leafs for each first char
                    if first_letter not in lexicon.keys():
                        lexicon.setdefault(first_letter, [])
                    leaf = lexicon[first_letter]
                    for ent in leaf:
                        if ent[0] == word_lower:
                            break
                    else:
                        ent = [word_lower, 0, 0]
                        leaf.append(ent)

                    if word_str[0].isupper():
                        ent[1] += 1
                    else:
                        ent[2] += 1

                first = True
            first = True

    for key, val in lexicon.items():
        new = []
        for ent in val:
            if ent[2] != 0:
                ratio = ent[1] / (ent[1] + ent[2])
                if ratio >= threshold:
                    new.append((ent[0], ratio))

        lexicon[key] = new

    args = dict()
    args["config"] = {"instr_pos": instr_pos, "instr_neg": instr_neg}
    args["data"] = lexicon

    return args


def property_noun(document, reports, data, config):
    """Find in minority lowercase words."""
    toolname = "property-noun"

    for part in rst_walker.iter_nodeparts_instr(document.body, config["instr_pos"],
                                                config["instr_neg"]):
        for word in Segmenter.iter_word(part.code):
            word_str = str(word)
            first_letter = word_str[0].lower()
            if first_letter not in data.keys():
                continue
            for ent in data[first_letter]:
                if ent[0] == word_str:
                    msg = "property noun: {:4.0%}".format(ent[1])
                    line = getline_punc(document.code, word.start_pos, word.span_len(), 50, 30)
                    reports.append(Report('W', toolname, word, msg, line))
                    break

    return reports


def typ_caps_pre(_):
    """Find lowercase types."""
    global listsearch
    import monostyle.listsearch as listsearch
    rst_parser = RSTParser()

    def typ_titles(document, b_type, searchlist):
        """Get page title and create versions where one word is not uppercase."""
        for node in rst_walker.iter_node(document.body, ("sect",), enter_pos=False):
            head = str(node.name.code).strip()
            head = head.replace('\n', '')

            # todo add r"s?" and word boundaries
            if not head.endswith(b_type):
                head += " " + b_type

            splitter = re.split(" ", head.lower())
            words = []
            for word in splitter:
                if re.match(r"^\w", word):
                    word = r"[" + word[0] + word[0].upper() + r"]" + word[1:]
                elif re.match(r"^\d", word):
                    # n D
                    word = word.upper()
                else:
                    word = re.escape(word)

                words.append(word)

            term = []
            # all lower except last
            pattern_str = splitter[:-1]
            pattern_str.append(words[-1])
            term.append(" ".join(pattern_str))

            if len(splitter) > 2:
                for index in range(0, len(words)):
                    if index < len(words) - 1:
                        pattern_str = words[:index]
                        pattern_str.append(re.escape(splitter[index]))
                        pattern_str.extend(words[index + 1:])
                        term.append(" ".join(pattern_str))

            searchlist.append([term, head])

            break

        return searchlist

    typs = (
        ("Modifier", "/modeling/modifiers/", ["common_options"]),
        ("Constraint", "/animation/constraints/", ["adding_removing", "common", "header", "stack"]),
        ("Node", "/compositing/types", ["groups"]),
        ("Node", "/render/shader_nodes", ["osl"]),
        ("Node", "/editors/texture_node/types", []),
        ("Strip", "/video_editing/sequencer/strips", [])
    )
    searchlist = []
    for kind, path, ignore in typs:
        ignore.append("index")
        ignore.append("introduction")

        for fn, text in monostylestd.rst_texts(monostylestd.path_to_abs(path, "rst")):
            for skip_fn in ignore:
                if fn.endswith(skip_fn + ".rst"):
                    break
            else:
                document = rst_parser.parse_full(rst_parser.document(fn, text))
                searchlist = typ_titles(document, kind, searchlist)

    args = dict()
    args["config"] = listsearch.parse_config("")
    args["data"] = listsearch.compile_searchlist(searchlist, args["config"])

    return args


def typ_caps(document, reports, data, config):
    return listsearch.search(document, reports, data, config)


def ui_case(document, reports):
    """Check caps in definition list terms."""
    toolname = "ui-case"

    instr_pos = {
        "*": {"*": ["head", "body"]}
    }
    instr_neg = {
        "role": {
            "kbd": "*", "menuselection": "*", "class": "*", "mod": "*", "math": "*"
        },
        "standalone": "*", "literal": "*", "substitution": "*"
    }
    icon_re = re.compile(r"\([^\)]*?\)\s*\Z")
    for node in rst_walker.iter_node(document.body, ("def",)):
        is_first_word = True
        for part in rst_walker.iter_nodeparts_instr(node.head.child_nodes.first().body,
                                                    instr_pos, instr_neg, False):
            if is_first_word and part.parent_node.prev is not None:
                is_first_word = False

            part_code = part.code
            if icon_m := re.search(icon_re, str(part.code)):
                part_code = part.code.slice(part.code.start_pos,
                                            part.code.loc_to_abs(icon_m.start(0)), True)

            buf = None
            for word in Segmenter.iter_word(part_code):
                if buf:
                    if msg_repl := titlecase(buf, is_first_word, False, "definition term"):
                        reports.append(Report('W', toolname, buf, msg_repl[0], node.head.code,
                                              msg_repl[1]))
                    is_first_word = False
                buf = word

            if buf:
                # ignore part.next, one part per node
                is_last_word = bool(part.parent_node.next is None or
                                    rst_walker.is_of(part.parent_node.next, "role", "kbd"))
                if msg_repl := titlecase(buf, is_first_word, is_last_word, "definition term"):
                    reports.append(Report('W', toolname, buf, msg_repl[0], node.head.code,
                                          msg_repl[1]))
                is_first_word = False

    return reports


OPS = (
    ("admonition-title", admonition_title, None),
    ("heading", heading_cap, heading_cap_pre),
    ("pos", pos_case, None),
    ("property", property_noun, property_noun_pre),
    ("starting", starting, starting_pre),
    ("type", typ_caps, typ_caps_pre),
    ("ui", ui_case, None),
)


if __name__ == "__main__":
    from monostyle.cmd import main
    main(OPS, __doc__, __file__)
