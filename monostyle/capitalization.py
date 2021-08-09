
"""
capitalization
~~~~~~~~~~~~~~

Capitalization tools.
"""

import re

import monostyle.util.monostyle_io as monostyle_io
from monostyle.util.report import Report
from monostyle.rst_parser.core import RSTParser
import monostyle.rst_parser.walker as rst_walker

from monostyle.util.char_catalog import CharCatalog
from monostyle.util.part_of_speech import PartofSpeech
from monostyle.util.segmenter import Segmenter
from monostyle.util.lexicon import Lexicon


def titlecase(part_of_speech, word, is_first_word, is_last_word, name):
    """Chicago style titlecase."""
    word_str = str(word)
    if is_first_word or is_last_word:
        if word_str[0].islower():
            if is_first_word:
                where = "at the start of a "
            elif is_last_word:
                where = "at the end of a "
            message = Report.misformatted(what="lowercase", where=where + name)

            fix = word.slice(end=word.start_pos + 1, after_inner=True)
            fix.replace(str(fix).swapcase())

            return message, fix
        return None

    tag = part_of_speech.tag(word_str.lower())
    if (word_str[0].islower() !=
            (len(tag) != 0 and
             (tag[0] in {"preposition", "conjunction", "pronoun", "auxiliary"} or
              tag[0] == "determiner" and tag[1] == "article"))):
        message = Report.misformatted(what="lowercase" if word_str[0].islower() else "uppercase",
                                      where="in " + name)

        fix = None
        if (not tag or (tag[0] != "preposition" and
                (tag[-1] != "article" or word_str != "A"))):
            fix = word.slice(end=word.start_pos + 1, after_inner=True)
            fix.replace(str(fix).swapcase())

        return message, fix


def admonition_title(toolname, document, reports):
    """Case of admonition titles."""
    segmenter = Segmenter()
    threshold = 0.2

    for node in rst_walker.iter_node(document.body, "dir"):
        if rst_walker.is_of(node, "*", ('admonition', 'hint', 'important',
                                        'note', 'tip', 'warning')):
            if node.head and node.body:
                word_all = 0
                word_low = 0

                for word in segmenter.iter_word(node.head.code):
                    word_str = str(word)
                    if len(word_str) >= 4:
                        word_all += 1
                        if word_str[0].islower():
                            word_low += 1
                if word_all > 1 and word_low/ word_all >= threshold:
                    reports.append(
                        Report('W', toolname, node.head.code.copy().clear(True),
                               "admonition caption titlecase: {:4.0%}"
                               .format(word_low/ word_all), node.head.code))

    return reports


def heading_caps_pre(_):
    re_lib = dict()

    re_lib["hyphen"] = (re.compile(r"\-[a-z]"),
        Report.misformatted(what="lowercase", where="in heading after hyphen"))

    re_lib["nonchar"] = (re.compile(r"[^\w \-&/()'\"\\?!:,\n]"),
        Report.existing(what="not allowed punctuation", where="in heading"))

    re_lib["and"] = (re.compile(r"\band\b", re.IGNORECASE),
        Report.substitution(what="and", where="in heading", with_what="an ampersand"))

    re_lib["or"] = (re.compile(r"\bor\b", re.IGNORECASE),
        Report.substitution(what="or", where="in heading", with_what="a slash"))

    return {"re_lib": re_lib}


def heading_caps(toolname, document, reports, re_lib):
    """Check the heading title capitalization."""
    segmenter = Segmenter()
    part_of_speech = PartofSpeech()
    instr_pos = {
        "*": {"*": ["head", "body"]}
    }
    instr_neg = {
        "role": {
            "kbd": "*", "menuselection": "*", "math": "*"
        },
        "literal": "*", "standalone": "*"
    }

    for node in rst_walker.iter_node(document.body, "sect", enter_pos=False):
        is_first_word = True
        is_faq = bool(re.search(r"\?\n", str(node.name.child_nodes.last().code)))
        for part in rst_walker.iter_nodeparts_instr(node.name, instr_pos, instr_neg, False):
            if is_first_word and part.parent_node.prev is not None:
                is_first_word = False

            buf = None
            for word in segmenter.iter_word(part.code):
                if buf:
                    if message_repl := titlecase(part_of_speech, buf, is_first_word,
                                                 False, "heading"):
                        reports.append(Report('W', toolname, buf, message_repl[0],
                                              node.name.code, message_repl[1]))
                    if is_faq:
                        break
                    is_first_word = False
                buf = word

            if buf and not is_faq:
                # ignore part.next, one part per node
                is_last_word = bool(part.parent_node.next is None)
                if message_repl := titlecase(part_of_speech, buf, is_first_word,
                                             is_last_word, "heading"):
                    reports.append(Report('W', toolname, buf, message_repl[0],
                                          node.name.code, message_repl[1]))
                is_first_word = False

            part_str = str(part.code)
            for pattern, message in re_lib.values():
                for m in re.finditer(pattern, part_str):
                    reports.append(Report('W', toolname, part.code.slice_match(m, 0, True),
                                          message, node.name.code))

    return reports


def pos_case(toolname, document, reports):
    """Find Capitalized non-nouns (i.a.) which can be a typo or missing punctuation."""
    segmenter = Segmenter()
    part_of_speech = PartofSpeech()

    instr_pos = {
        "field": {"*": ["name", "body"]},
        "*": {"*": ["head", "body"]}
    }
    instr_neg = {
        "dir": {
            "figure": ["head"],
            "hint": ["head"], "important": ["head"], "note": ["head"],
            "tip": ["head"], "warning": ["head"], "rubric": ["head"],
            "code-block": "*", "default": "*", "include": "*", "index": "*", "toctree": "*",
            "parsed-literal": "*", "math": "*", "youtube": "*", "vimeo": "*", "peertube": "*"
        },
        "def": {"*": ["head"]},
        "substdef": {"image": ["head"], "unicode": "*", "replace": "*"},
        "doctest": "*", "target": "*", "comment": "*",
        "role": "*", "emphasis": "*", "int-target": "*", "hyperlink": "*",
        "literal": "*", "standalone": "*"
    }
    was_open = False
    for part in rst_walker.iter_nodeparts_instr(document.body, instr_pos, instr_neg):
        if rst_walker.is_of(part.parent_node.parent_node, "field"):
            node_par = part
            while node_par and node_par.node_name != "field-list":
                node_par = node_par.parent_node
            if (not rst_walker.is_of(node_par.parent_node, "*", "*", "attr") and
                    not rst_walker.is_of(node_par.parent_node, "document")):
                continue

        for sen, stop in segmenter.iter_sentence(part.code):
            is_first_word = not was_open
            for word in segmenter.iter_word(sen):
                if is_first_word:
                    is_first_word = False
                    continue

                word_str = str(word)
                if word_str[0].islower() or word_str in {"I", "Y"}:
                    continue

                tag = part_of_speech.tag(word_str.lower())
                if len(tag) != 0 and tag[0] not in {"noun", "abbreviation", "adjective", "verb"}:
                    reports.append(
                        Report('W', toolname, word,
                               Report.misformatted(what="uppercase " + tag[0]), sen))

            was_open = bool(stop is None)

        # paragraph end
        if not part.parent_node.next:
            was_open = False

    return reports


def proper_noun_pre(_):
    """Build lexicon with lower/uppercase counts."""
    segmenter = Segmenter()

    threshold = 0.8
    instr_pos = {
        "field": {"*": ["name", "body"]},
        "*": {"*": ["head", "body"]}
    }
    instr_neg = {
        "dir": {
            "figure": ["head"],
            "code-block": "*", "default": "*", "include": "*", "index": "*", "toctree": "*",
            "parsed-literal": "*", "math": "*", "youtube": "*", "vimeo": "*", "peertube": "*"
        },
        "substdef": {"image": ["head"], "unicode": "*", "replace": "*"},
        "doctest": "*", "target": "*", "comment": "*",
        "role": {
            "kbd": "*", "math": "*"
        },
        "literal": "*", "standalone": "*"
    }

    lexicon = Lexicon()
    rst_parser = RSTParser()
    for filename, text in monostyle_io.doc_texts():
        document = rst_parser.parse(rst_parser.document(filename, text))

        first = True
        for part in rst_walker.iter_nodeparts_instr(document.body, instr_pos, instr_neg):
            for sen, _ in segmenter.iter_sentence(part.code):
                for word in segmenter.iter_word(sen):
                    if first:
                        first = False
                        continue

                    word_str = str(word)
                    entry = lexicon.add(word_str)
                    if "up" not in entry.keys():
                        entry.update((("up", 0), ("low", 0)))
                    entry["up" if word_str[0].isupper() else "low"] += 1

                first = True
            first = True

    removals = set()
    for word, entry in lexicon:
        if entry["up"] == 0:
            removals.add(word)
            continue

        ratio = entry["up"] / (entry["up"] + entry["low"])
        if ratio < threshold:
            removals.add(word)
            continue

        entry["ratio"] = ratio
        del entry["up"], entry["low"]

    for word in removals:
        lexicon.remove(word)

    args = dict()
    args["config"] = {"instr_pos": instr_pos, "instr_neg": instr_neg}
    args["data"] = lexicon

    return args


def proper_noun(toolname, document, reports, data, config):
    """Find in minority lowercase words."""
    segmenter = Segmenter()

    for part in rst_walker.iter_nodeparts_instr(document.body, config["instr_pos"],
                                                config["instr_neg"]):
        for word in segmenter.iter_word(part.code):
            if entry := data.find(str(word)):
                reports.append(
                    Report('W', toolname, word, "proper noun: {:4.0%}".format(entry["ratio"]))
                    .set_line_punc(document.code, 50, 30))

    return reports


def start_case_pre(_):
    char_catalog = CharCatalog()

    re_lib = dict()
    punc_sent = char_catalog.data["terminal"]["final"] + ':'
    pare_open = char_catalog.data["bracket"]["left"]["normal"]

    # FP: code, container
    re_lib["lowerpara"] = (
        re.compile(r"[" + pare_open + r"]?[a-z]"),
        Report.misformatted(what="lowercase", where="at paragraph start"))

    # todo? split sentence
    # limitation: not nested parenthesis
    # not match abbr
    re_lib["punclower"] = (
        re.compile("".join((r"(?<!\w\.\w)[", punc_sent, r"]\s+?", r"[", pare_open, r"]?[a-z]")),
                    re.MULTILINE | re.DOTALL),
        Report.misformatted(what="lowercase", where="after sentence start"))

    # FP: abbr, menu, heading, code
    re_lib["upperbracket"] = (
        re.compile(r"[^.\s]\s*?[" + pare_open + r"][A-Z][a-z ]", re.MULTILINE),
        Report.misformatted(what="uppercase", where="at bracket start"))

    args = dict()
    args["re_lib"] = re_lib

    return args


def start_case(toolname, document, reports, re_lib):
    """Check case at the start of paragraphs, sentences and parenthesis."""
    instr_pos = {
        "field": {"*": ["name", "body"]},
        "*": {"*": ["head", "body"]}
    }
    instr_neg = {
        "dir": {
            "figure": ["head"], "toctree": "*", "include": "*", "index": "*", "highlight": "*",
            "code-block": "*", "default": "*", "youtube": "*", "vimeo": "*", "peertube": "*"
        },
        "substdef": {"image": ["head"], "unicode": "*", "replace": "*"},
        "doctest": "*",
        "literal": "*", "standalone": "*"
    }

    start_re = re_lib["lowerpara"][0]
    was_empty = False
    for part in rst_walker.iter_nodeparts_instr(document.body, instr_pos, instr_neg):
        if not part.parent_node.prev or was_empty:
            if (part.parent_node.node_name == "text" or
                    part.parent_node.parent_node.parent_node.node_name == "text"):

                if re.match(start_re, str(part.code)):
                    reports.append(
                        Report('W', toolname, part.code.copy().clear(True), re_lib["lowerpara"][1])
                        .set_line_offset(document.body.code, 100, True))

                was_empty = bool(len(part.code) == 0)

        if part.parent_node.node_name == "text":
            part_str = str(part.code)
            for key, value in re_lib.items():
                if key == "lowerpara":
                    continue
                pattern = value[0]
                for m in re.finditer(pattern, part_str):
                    reports.append(
                        Report('W', toolname, part.code.slice_match(m, 0, True), value[1])
                        .set_line_offset(document.body.code, 100, True))

    return reports


def typ_case_pre(_):
    """Find lowercase types."""
    global listsearch
    import monostyle.listsearch as listsearch
    rst_parser = RSTParser()

    def typ_titles(document, b_type, terms):
        """Get page title and create versions where one word is not uppercase."""
        for node in rst_walker.iter_node(document.body, "sect", enter_pos=False):
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
            term.append(r"\b" + " ".join(pattern_str))

            if len(splitter) > 2:
                for index in range(0, len(words)):
                    if index < len(words) - 1:
                        pattern_str = words[:index]
                        pattern_str.append(re.escape(splitter[index]))
                        pattern_str.extend(words[index + 1:])
                        term.append(r"\b" + " ".join(pattern_str))

            terms.append([term, head])

            break

        return terms

    typs = (
        ("Modifier", "modeling/modifiers/", ["common_options"]),
        ("Constraint", "animation/constraints/", ["adding_removing", "common", "header", "stack"]),
        ("Node", "compositing/types/", ["groups"]),
        ("Node", "render/shader_nodes/", ["osl"]),
        ("Node", "editors/texture_node/types/", []),
        ("Node", "modeling/modifiers/nodes/", []),
        ("Strip", "video_editing/sequencer/strips/", [])
    )
    terms = []
    for kind, path, ignore in typs:
        ignore.extend(("index", "introduction"))

        for filename, text in monostyle_io.doc_texts(monostyle_io.path_to_abs(path, "doc")):
            skip = False
            for skip_filename in ignore:
                if filename.endswith(skip_filename + ".rst"):
                    skip = True
                    break

            # is not nested
            filename_rel = monostyle_io.path_to_rel(filename, "doc")
            for _, path_rec, __ in typs:
                if (path != path_rec and len(path) < len(path_rec) and
                        filename_rel.startswith(path_rec)):
                    skip = True
                    break
            if not skip:
                document = rst_parser.parse(rst_parser.document(filename, text))
                terms = typ_titles(document, kind, terms)

    args = dict()
    args["config"] = {}
    args["data"] = listsearch.compile_terms(terms, {"flags": listsearch.parse_flags("")})

    return args


def typ_case(toolname, document, reports, data, config):
    return listsearch.search_char(toolname, document, reports, data, config)


def ui_case(toolname, document, reports):
    """Check the capitalization of UI terms in reference lists."""
    def check_words(part, code, is_first_word, part_name, line, is_field=False):
        buf = None
        do_fix = False
        ui_terms = {"menu", "context", "node", "tab", "panel", "region", "editor", "editors"}
        attr_terms = {
            "align", "alt", "class", "encoding", "end-before", "end-line", "figclass", "figwidth",
            "header-rows", "height", "literal", "name", "number-lines", "parser",
            "scale", "start-after", "start-line", "stub-columns", "subtitle", "tab-width",
            "target", "width", "widths",
        }
        if is_field and str(code) not in attr_terms:
            do_fix = True

        for word in segmenter.iter_word(code):
            if buf:
                if str(buf) in ui_terms:
                    continue
                if message_repl := titlecase(part_of_speech, buf, is_first_word,
                                             False, part_name):
                    reports.append(Report('W', toolname, buf, message_repl[0],
                                          line, message_repl[1] if do_fix else None))
                is_first_word = False
            buf = word

        if buf and str(buf) not in ui_terms:
            # ignore part.next, one part per node
            is_last_word = bool(rst_walker.is_of(part, "role", "menuselection") or
                                part.parent_node.next is None or
                                rst_walker.is_of(part.parent_node.next, "role",
                                                 {"kbd", "guilabel"}))

            if message_repl := titlecase(part_of_speech, buf, is_first_word,
                                         is_last_word, part_name):
                reports.append(Report('W', toolname, buf, message_repl[0],
                                      line, message_repl[1] if do_fix else None))
            is_first_word = False

        return reports, is_first_word

    segmenter = Segmenter()
    part_of_speech = PartofSpeech()
    instr_pos = {
        "*": {"*": ["head", "body"]}
    }
    instr_neg = {
        "role": {
            "kbd": "*", "menuselection": "*", "math": "*"
        },
        "standalone": "*", "literal": "*", "substitution": "*"
    }
    icon_re = re.compile(r"\([^\)]*?\)\s*\Z")
    arrow_re = re.compile(r"\s*\-+>\s*\b")
    for node in rst_walker.iter_node(document.body, {"def", "field", "role"}):
        if node.node_name ==  "role":
            if rst_walker.is_of(node, "role", "menuselection"):
                body_str = str(node.body.code)
                last = 0
                for arrow_m in re.finditer(arrow_re, body_str):
                    entry_code = node.body.code.slice(node.body.code.loc_to_abs(last),
                                                      node.body.code.loc_to_abs(arrow_m.start()),
                                                      after_inner=True)
                    last = arrow_m.end()
                    reports, _ = check_words(node.body, entry_code, True,
                                             "menuselection item", node.body.code)
                if last != len(body_str):
                    entry_code = node.body.code.slice(node.body.code.loc_to_abs(last),
                                                      after_inner=True)
                    reports, _ = check_words(node.body, entry_code, True,
                                             "menuselection item", node.body.code)

            continue

        is_field = bool(node.node_name == "field")
        if is_field:
            if not rst_walker.is_of(node.parent_node.parent_node.parent_node,
                                    {"def", "block-quote"}):
                continue
            child = node.name
            part_name = "field name"
        else:
            child = node.head.child_nodes.first().body
            part_name = "definition term"

        is_first_word = True
        for part in rst_walker.iter_nodeparts_instr(child, instr_pos, instr_neg, False):
            if is_first_word and part.parent_node.prev is not None:
                is_first_word = False

            part_code = part.code
            if not is_field:
                if icon_m := re.search(icon_re, str(part.code)):
                    part_code = part.code.slice(part.code.start_pos,
                                                part.code.loc_to_abs(icon_m.start(0)), True)

            reports, is_first_word = check_words(part, part_code, is_first_word, part_name,
                                                 child.code, is_field)

    return reports


OPS = (
    ("admonition-title", admonition_title, None),
    ("heading-caps", heading_caps, heading_caps_pre),
    ("pos-case", pos_case, None),
    ("proper-noun", proper_noun, proper_noun_pre),
    ("start-case", start_case, start_case_pre),
    ("type", typ_case, typ_case_pre),
    ("ui", ui_case, None),
)


if __name__ == "__main__":
    from monostyle.__main__ import main_mod
    main_mod(__doc__, OPS, __file__)
