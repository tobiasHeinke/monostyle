
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
from monostyle.util.fragment import Fragment
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
             Flags can be overridden per term with an initial '!' and delimited by a ':'.
             Following re group syntax: added flags and after '-' the removed ones.
             These can be escaped with a backslash.

    conf:flags -- regex flags.
        stem -- stem the pattern string.
        overline -- match over whitespace including line wraps.
        boundary -- pattern start and end with word boundaries.
    """
    def convert_flags(conf_flags):
        flags = 0
        if conf_flags["ignorecase"]:
            flags = re.IGNORECASE
        if conf_flags["mulitline"] or conf_flags["overline"]:
            flags = flags | re.MULTILINE
        if conf_flags["dotall"]:
            flags = flags | re.DOTALL
        return flags

    def combine_message(pattern_str, message, conf):
        has_default = False
        if not message:
            if "message" in conf:
                message = conf["message"]
                has_default = True
            else:
                message = pattern_str

        if not has_default and not isinstance(message, str):
            message = '/'.join(message)

        return (conf.get("message prefix", "") + message + conf.get("message suffix", ""),
                has_default)

    def compile_tokenized(pattern_str, conf_flags_local, porter_stemmer):
        segmenter = Segmenter()
        pattern = []
        for word in segmenter.iter_word(Fragment("", pattern_str)):
            if not conf_flags_local or conf_flags_local["stem"]:
                pattern.append(porter_stemmer.stem(str(word), 0, len(word)-1))
            else:
                pattern.append(str(word))

        return [tuple(pattern), 0, conf_flags_local, None]

    def combine_pattern(pattern_str, conf):
        # ignore this single term
        if pattern_str == "" or pattern_str.startswith('?'):
            return None

        if m := re.match(r"!([a-zA-Z]*)(?:\-([a-zA-Z]+))?\:", pattern_str):
            conf_flags_local = conf["flags"].copy()
            if m.group(1):
                conf_flags_local = parse_flags(m.group(1), conf_flags_local)
            if m.group(2):
                conf_flags_local = parse_flags(m.group(2), conf_flags_local, True)
            pattern_str = pattern_str[m.end(0):]
        else:
            conf_flags_local = conf["flags"]

        # remove escape
        if re.match(r"\\[#?!]", pattern_str):
            pattern_str = pattern_str[1:]

        pattern_str = (conf.get("pattern prefix", "") + pattern_str +
                       conf.get("pattern suffix", ""))

        if conf["flags"]["token"]:
            if conf["flags"]["ignorecase"]:
                pattern_str = pattern_str.lower()
        else:
            if conf_flags_local["overline"]:
                pattern_str = re.sub(r" +", "\\\\s+?", pattern_str)
            if conf_flags_local["boundary"]:
                pattern_str = r'\b' + pattern_str + r'\b'

        return pattern_str, conf_flags_local if conf_flags_local is not conf["flags"] else None

    porter_stemmer = Porterstemmer()
    terms_compiled = []
    flags = convert_flags(conf["flags"])

    pattern_str_default = []
    message_default = None
    for term in terms:
        message = None
        if isinstance(term, str):
            pattern_strs = term
        elif len(term) == 1:
            pattern_strs = term[0]
        elif len(term) == 2:
            pattern_strs = term[0]
            message = term[1]
        else:
            print("listsearch: misformatted list entry:", term)
            continue

        message, has_default = combine_message(pattern_strs, message, conf)

        if isinstance(pattern_strs, str):
            pattern_strs = (pattern_strs,)

        pattern_str_combined = []
        for pattern_str in pattern_strs:
            # comment skip entire entry
            if pattern_str.startswith('#'):
                break

            pattern_str, conf_flags_local = combine_pattern(pattern_str, conf)
            if not pattern_str:
                continue
            if conf["flags"]["token"]:
                terms_compiled.append((compile_tokenized(pattern_str, conf_flags_local,
                                       porter_stemmer), message))
            elif conf_flags_local:
                terms_compiled.append((re.compile(pattern_str, convert_flags(conf_flags_local)),
                                       message))
            else:
                pattern_str_combined.append(pattern_str)

        if has_default:
            pattern_str_default.extend(pattern_str_combined)
            message_default = message
        elif pattern_str_combined:
            terms_compiled.append((re.compile("|".join(pattern_str_combined), flags), message))

    if pattern_str_default:
        terms_compiled.append((re.compile("|".join(pattern_str_default), flags), message_default))

    return terms_compiled


def parse_flags(re_conf_str, override=None, negate=False):
    """Parse config to Boolean values."""
    re_conf_str = re_conf_str.upper()
    re_conf_map = {
        "boundary": "B",
        "dotall": "D",
        "ignorecase": "I",
        "mulitline": "M",
        "overline": "O",
        "stem": "S",
        "token": "T"
    }
    re_conf = re_conf_map if override is None else override
    for key in re_conf_map.keys():
        if re_conf_map[key] in re_conf_str:
            re_conf[key] = not negate
        elif override is None:
            re_conf[key] = False

    if re_conf["stem"]:
        re_conf["token"] = re_conf["stem"]
    return re_conf


def search_char(toolname, document, reports, data, config):
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
            "math": "*", "toctree": "*", "youtube": "*", "vimeo": "*", "peertube": "*"
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
                reports.append(
                    Report(config.get("severity", 'I'), toolname,
                           part.code.slice_match(m, 0, True), message)
                    .set_line_punc(document.body.code, 50, 30))

    return reports


def search_token(toolname, document, reports, data, config):
    """Search terms in document within word boundaries."""
    toolname = "search-token"
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
            "math": "*", "toctree": "*", "youtube": "*", "vimeo": "*", "peertube": "*"
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
            if config["flags"]["ignorecase"]:
                word_str = word_str.lower()
            if config["flags"]["stem"]:
                word_stem = porter_stemmer.stem(word_str, 0, len(word_str)-1)

            for pattern, message in data:
                word_match = word_str
                if not pattern[2] or pattern[2]["stem"]:
                    word_match = word_stem

                if pattern[0][pattern[1]] == word_match:
                    pattern[1] += 1
                elif pattern[0][0] == word_match:
                    pattern[1] = 1
                else:
                    continue

                if pattern[1] == 1:
                    pattern[3] = word.start_pos
                if pattern[1] == len(pattern[0]):
                    reports.append(
                        Report(config.get("severity", 'I'), toolname,
                               document.code.slice(pattern[3], word.end_pos, True),
                               message).set_line_punc(document.code, 50, 30))
                    pattern[1] = 0

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
                "pattern prefix", "pattern suffix", "severity"):
            if key in obj:
                conf[key] = obj[key]

        conf["flags"] = parse_flags(obj.get("flags", ""))
        return obj["terms"], conf

    data = []
    if not toolname.endswith("/*"):
        # last path segment as default message.
        terms, conf = split_obj(monostyle_io.get_data_file(toolname), toolname.split('/')[-1])
        data.append((compile_terms(terms, conf), conf))
    else:
        for key, value in wildcard_leaf(monostyle_io.get_data_file(toolname[:-2])):
            # key as default message.
            terms, conf = split_obj(value, key)
            data.append((compile_terms(terms, conf), conf))

    return {"data": data}


def search(toolname, document, reports, data):
    """Switch between on char or token level search."""
    for terms, conf in data:
        if not conf["flags"]["token"]:
            reports = search_char(toolname, document, reports, terms, conf)
        else:
            reports = search_token(toolname, document, reports, terms, conf)

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
