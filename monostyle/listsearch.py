
"""
listsearch
~~~~~~~~~~

List based search tools.
"""

import re

import monostyle.util.monostylestd as monostylestd
from monostyle.util.report import Report, getline_punc
import monostyle.rst_parser.walker as rst_walker
from monostyle.util.segmenter import Segmenter
from monostyle.util.porter_stemmer import Porterstemmer

PorterStemmer = Porterstemmer()
Segmenter = Segmenter()


def compile_searchlist(searchlist, re_conf):
    """Make search list one dimensional.

    searchlist -- a list with one or two columns. The first column contains the terms,
                  the second the message string(s) outputted to the user.
                  If only one column is given the message is
                  either the "message" conf variable or is generated by joining the terms.

                  Inline:
                  If the first terms starts with a '#' the entry is skipped.
                  If a terms starts with a '?' the term is skipped.
                  These can be escaped with a backslash.
                  If a terms ends with a '|' the term will not be stemed.
    re_conf -- regex flags.
        stem -- stem the terms.
        overline -- match over whitespace including line wraps.
        boundary -- pattern start and end with word boundaries.
    """
    comlist = []
    flags = 0
    if re_conf["ignorecase"]:
        flags = re.IGNORECASE
    if re_conf["mulitline"] or re_conf["overline"]:
        flags = flags | re.MULTILINE
    if re_conf["dotall"]:
        flags = flags | re.DOTALL

    for search_ent in searchlist:
        if isinstance(search_ent, str):
            terms = search_ent
            if "message" in re_conf:
                message = re_conf["message"]
            else:
                message = search_ent
        elif len(search_ent) == 1:
            terms = search_ent[0]
            if "message" in re_conf:
                message = re_conf["message"]
            else:
                message = search_ent[0]
        elif len(search_ent) == 2:
            terms = search_ent[0]
            message = search_ent[1]
        else:
            print("list: wrong form:", search_ent)
            continue

        if isinstance(terms, str):
            terms = [terms]

        for pattern_str in terms:
            if pattern_str == "":
                continue
            # comment
            if pattern_str.startswith('#'):
                # skip entire entry
                break
            # ignore this single term
            if pattern_str.startswith('?'):
                continue

            # remove escape
            if pattern_str.startswith('\\#') or pattern_str.startswith('\\?'):
                pattern_str = pattern_str[1:]

            if re_conf["stem"]:
                if not pattern_str.endswith('|'):
                    pattern_str = PorterStemmer.stem(pattern_str, 0, len(pattern_str)-1)
                else:
                    pattern_str = pattern_str[:-1]
            else:
                if re_conf["overline"]:
                    pattern_str = pattern_str.replace(' ', r'(?s\s+)')
                if re_conf["boundary"]:
                    pattern_str = r'\b' + pattern_str + r'\b'

            if not re_conf["word"]:
                pattern = re.compile(pattern_str, flags)
            else:
                pattern = pattern_str

            if not isinstance(message, str):
                message = '/'.join(message)

            comlist.append((pattern, message))

    return comlist


def parse_config(re_conf_str):
    """Parse config to Booleans."""
    re_conf_str = re_conf_str.upper()
    re_conf = {
        "boundary": "B",
        "dotall": "D",
        "ignorecase": "I",
        "mulitline": "M",
        "overline": "O",
        "stem": "S",
        "word": "W"
    }
    for key in re_conf.keys():
        re_conf[key] = bool(re_conf[key] in re_conf_str)

    return re_conf


def search_free(document, reports, comlist):
    """Search terms in document."""
    toolname = "list-search"

    instr_pos = {
        "sect": {"*": ["name"]},
        "field": {"*": ["name", "body"]},
        "*": {"*": ["head", "body"]}
    }
    instr_neg = {
        "dir": {
            "figure": ["head"],
            "code-block": "*", "default": "*", "include": "*",
            "math": "*", "youtube": "*", "vimeo": "*"
        },
        "substdef": {"image": ["head"], "unicode": "*", "replace": "*"},
        "target": "*",
        "role": {
            "kbd": "*", "class": "*", "mod": "*", "math": "*"
        },
        "standalone": "*"
    }

    for part in rst_walker.iter_nodeparts_instr(document.body, instr_pos, instr_neg):
        part_str = str(part.code)
        for pattern, message in comlist:
            for m in re.finditer(pattern, part_str):
                output = part.code.slice_match_obj(m, 0, True)
                line = getline_punc(document.body.code, output.start_pos,
                                    output.span_len(True), 50, 30)
                reports.append(Report('I', toolname, output, message, line))

    return reports


def search_word(document, reports, comlist, config):
    """Search terms in document within word boundaries."""
    toolname = "search-word"

    instr_pos = {
        "sect": {"*": ["name"]},
        "field": {"*": ["name", "body"]},
        "*": {"*": ["head", "body"]}
    }
    instr_neg = {
        "dir": {
            "figure": ["head"],
            "code-block": "*", "default": "*", "include": "*",
            "math": "*", "youtube": "*", "vimeo": "*"
        },
        "substdef": {"image": ["head"], "unicode": "*", "replace": "*"},
        "target": "*",
        "role": {
            "kbd": "*", "class": "*", "mod": "*", "math": "*"
        },
        "standalone": "*"
    }

    for part in rst_walker.iter_nodeparts_instr(document.body, instr_pos, instr_neg):
        for word in Segmenter.iter_word(part.code):
            word_str = str(word)
            if config["ignorecase"]:
                word_str = word_str.lower()
            if config["stem"]:
                word_stem = PorterStemmer.stem(word_str, 0, len(word_str)-1)

            for pattern, message in comlist:
                if config["stem"]:
                    if not pattern.endswith('|'):
                        if pattern != word_stem:
                            continue
                    else:
                        if pattern[:-1] != word_str:
                            continue

                if pattern != word_str:
                    continue

                line = getline_punc(document.body.code, word.start_pos,
                                    word.span_len(True), 50, 30)
                reports.append(Report('I', toolname, word, message, line))

    return reports


def search_pre(op):
    def wildcard_leaf(data_src):
        for key, value in data_src.items():
            if isinstance(value, dict):
                yield from wildcard_leaf(value)
            elif isinstance(value, list):
                yield key, value

    config = parse_config(op[4])
    if not op[0].endswith("/*"):
        data_src = monostylestd.get_data_file(op[0])
        # last path segment as default message.
        config["message"] = op[0].split('/')[-1]
        data_comp = compile_searchlist(data_src, config)
    else:
        data_src = monostylestd.get_data_file(op[0][:-2])
        data_comp = []
        for key, value in wildcard_leaf(data_src):
            # key as default message.
            config["message"] = key
            data_comp.extend(compile_searchlist(value, config))

    args = dict()
    args["data"] = data_comp
    args["config"] = config

    return args


def search(document, reports, data, config):
    """Switch between free and with boundary."""
    if not config["word"]:
        reports = search_free(document, reports, data)
    else:
        reports = search_word(document, reports, data, config)

    return reports


OPS = (
    ("test", search, search_pre, True, "BIS"),
    ("be_eng/Be", search, search_pre, True, "BIS"),
    ("be_eng/Rules", search, search_pre, True, "IS"),
    ("confuse/Div", search, search_pre, True, "BIS"),
    ("blender/UI", search, search_pre, True, "I"),
    ("blender/Editors", search, search_pre, True, ""),
    ("blender/Modes", search, search_pre, True, ""),
    ("avoid/*", search, search_pre, True, "BI"),
    ("dev/*", search, search_pre, True, "BI"),
    ("simplify", search, search_pre, True, "BI")
)

if __name__ == "__main__":
    from monostyle.cmd import main
    main(OPS, __doc__, __file__)
