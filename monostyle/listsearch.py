
"""
listsearch
~~~~~~~~~~

List based search tools.
"""

import re

import monostyle.util.monostyle_io as monostyle_io
from monostyle.util.report import Report
import monostyle.rst_parser.walker as rst_walker
from monostyle.util.segmenter import Segmenter
from monostyle.util.porter_stemmer import Porterstemmer


def compile_terms(terms, conf):
    """Make search list one dimensional.

    terms -- a list with one or two columns. The first column contains the pattern strings,
             the second the message outputted to the user.
             If only one column is given the message is
             either the "message" conf variable or is generated by joining the strings.

             Inline:
             If the first string starts with a '#' the entry is skipped.
             If a string starts with a '?' the term is skipped.
             These can be escaped with a backslash.
             If a string ends with a '|' the term will not be stemed.
    conf:flags -- regex flags.
        stem -- stem the pattern string.
        overline -- match over whitespace including line wraps.
        boundary -- pattern start and end with word boundaries.
    """
    def combine_message(message, has_message, conf):
        if "message" in conf and not has_message:
            message = conf["message"]
        else:
            if not isinstance(message, str):
                message = '/'.join(message)

        message = conf.get("message prefix", "") + message + conf.get("message suffix", "")
        return message

    def compile_pattern(pattern_str, conf, porter_stemmer):
        # ignore this single term
        if pattern_str == "" or pattern_str.startswith('?'):
            return None

        # remove escape
        if pattern_str.startswith('\\#') or pattern_str.startswith('\\?'):
            pattern_str = pattern_str[1:]

        if conf["flags"]["stem"]:
            if not pattern_str.endswith('|'):
                pattern_str = porter_stemmer.stem(pattern_str, 0, len(pattern_str)-1)
            else:
                pattern_str = pattern_str[:-1]
            pattern_str = (conf.get("pattern prefix", "") + pattern_str +
                           conf.get("pattern suffix", ""))
        else:
            pattern_str = (conf.get("pattern prefix", "") + pattern_str +
                           conf.get("pattern suffix", ""))

            if conf["flags"]["overline"]:
                pattern_str = re.sub(r" +", "\\\\s+?", pattern_str)
            if conf["flags"]["boundary"]:
                pattern_str = r'\b' + pattern_str + r'\b'

        if not conf["flags"]["word"]:
            pattern = re.compile(pattern_str, flags)
        else:
            pattern = pattern_str
        return pattern

    porter_stemmer = Porterstemmer()
    terms_compiled = []
    flags = 0
    if conf["flags"]["ignorecase"]:
        flags = re.IGNORECASE
    if conf["flags"]["mulitline"] or conf["flags"]["overline"]:
        flags = flags | re.MULTILINE
    if conf["flags"]["dotall"]:
        flags = flags | re.DOTALL

    for term in terms:
        if isinstance(term, str):
            pattern_strs = term
            message = combine_message(pattern_strs, False, conf)
        elif len(term) == 1:
            pattern_strs = term[0]
            message = combine_message(pattern_strs, False, conf)
        elif len(term) == 2:
            pattern_strs = term[0]
            message = combine_message(term[1], True, conf)
        else:
            print("list: wrong form:", term)
            continue

        if isinstance(pattern_strs, str):
            pattern_strs = (pattern_strs,)

        for pattern_str in pattern_strs:
            # comment skip entire entry
            if pattern_str.startswith('#'):
                break

            pattern = compile_pattern(pattern_str, conf, porter_stemmer)
            if not pattern:
                continue

            terms_compiled.append((pattern, message))

    return terms_compiled


def parse_flags(re_conf_str):
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


def search_free(toolname, document, reports, data):
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
            "code-block": "*", "default": "*", "include": "*", "index": "*",
            "math": "*", "toctree": "*", "youtube": "*", "vimeo": "*"
        },
        "substdef": {"image": ["head"], "unicode": "*", "replace": "*"},
        "comment": "*", "doctest": "*", "target": "*",
        "role": {
            "kbd": "*", "math": "*"
        },
        "standalone": "*"
    }

    for part in rst_walker.iter_nodeparts_instr(document.body, instr_pos, instr_neg):
        part_str = str(part.code)
        for pattern, message in data:
            for m in re.finditer(pattern, part_str):
                output = part.code.slice_match_obj(m, 0, True)
                line = Report.getline_punc(document.body.code, output, 50, 30)
                reports.append(Report('I', toolname, output, message, line))

    return reports


def search_word(toolname, document, reports, data, config):
    """Search terms in document within word boundaries."""
    toolname = "search-word"
    segmenter = Segmenter()
    porter_stemmer = Porterstemmer()

    instr_pos = {
        "sect": {"*": ["name"]},
        "field": {"*": ["name", "body"]},
        "*": {"*": ["head", "body"]}
    }
    instr_neg = {
        "dir": {
            "figure": ["head"],
            "code-block": "*", "default": "*", "include": "*", "index": "*",
            "math": "*", "toctree": "*", "youtube": "*", "vimeo": "*"
        },
        "substdef": {"image": ["head"], "unicode": "*", "replace": "*"},
        "comment": "*", "doctest": "*", "target": "*",
        "role": {
            "kbd": "*", "math": "*"
        },
        "standalone": "*"
    }

    for part in rst_walker.iter_nodeparts_instr(document.body, instr_pos, instr_neg):
        for word in segmenter.iter_word(part.code):
            word_str = str(word)
            if config["ignorecase"]:
                word_str = word_str.lower()
            if config["stem"]:
                word_stem = porter_stemmer.stem(word_str, 0, len(word_str)-1)

            for pattern, message in data:
                if config["stem"]:
                    if not pattern.endswith('|'):
                        if pattern != word_stem:
                            continue
                    else:
                        if pattern[:-1] != word_str:
                            continue

                if pattern != word_str:
                    continue

                line = Report.getline_punc(document.body.code, word, 50, 30)
                reports.append(Report('I', toolname, word, message, line))

    return reports


def search_pre(toolname):
    def wildcard_leaf(obj):
        for key, value in obj.items():
            if isinstance(value, dict):
                if "terms" in value.keys():
                    yield key, value
                else:
                    yield from wildcard_leaf(value)

    def split_obj(obj, toolname):
        """Split terms and config."""
        conf = {"message": toolname}
        for key in ("message", "message prefix", "message suffix",
                "pattern prefix", "pattern suffix"):
            if key in obj:
                conf[key] = obj[key]

        conf["flags"] = parse_flags(obj.get("flags", ""))
        return obj["terms"], conf

    if not toolname.endswith("/*"):
        # last path segment as default message.
        terms, conf = split_obj(monostyle_io.get_data_file(toolname), toolname.split('/')[-1])
        terms_compiled = compile_terms(terms, conf)
    else:
        terms_compiled = []
        for key, value in wildcard_leaf(monostyle_io.get_data_file(toolname[:-2])):
            # key as default message.
            terms, conf = split_obj(value, key)
            terms_compiled.extend(compile_terms(terms, conf))

    args = dict()
    args["data"] = terms_compiled
    args["config"] = conf["flags"]

    return args


def search(toolname, document, reports, data, config):
    """Switch between free and with boundary."""
    if not config["word"]:
        reports = search_free(toolname, document, reports, data)
    else:
        reports = search_word(toolname, document, reports, data, config)

    return reports


OPS = (
    ("avoid/*", search, search_pre, True),
    ("blender/Editors", search, search_pre, True),
    ("blender/Modes", search, search_pre, True),
    ("blender/UI", search, search_pre, True),
    ("dev/*", search, search_pre, True),
    ("simplify", search, search_pre, True)
)

if __name__ == "__main__":
    from monostyle.__main__ import main_mod
    main_mod(__doc__, OPS, __file__)
