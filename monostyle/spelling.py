
"""
spelling
~~~~~~~~

Create or compare words against a lexicon.
"""

import re

import monostyle.util.monostyle_io as monostyle_io
from monostyle.util.report import Report
from monostyle.util.fragment import Fragment

import monostyle.rst_parser.walker as rst_walker
from monostyle.util.segmenter import Segmenter
from monostyle.util.lexicon import Lexicon


def search_pre(toolname):
    config = dict(monostyle_io.get_override(__file__, toolname, "threshold", 3))
    return {"config": config}


def search(toolname, document, reports, config):
    """Search for rare or new words."""
    lexicon = Lexicon(False)

    # compare words in the text.
    text_words = Lexicon()
    for word in word_filtered(document):
        entry_hunk = text_words.add(str(word))
        if "word" not in entry_hunk.keys():
            entry_hunk["word"] = word

    threshold = config["threshold"]
    # compare words against the lexicon.
    lexicon_words = None
    for word_str, entry_hunk in text_words:
        frequency = -1
        if entry := lexicon.find(word_str):
            frequency = int(entry["_counter"])

        if frequency < threshold:
            if frequency != -1:
                severity = 'I'
                message = "rare word: hunk: {0} lex: {1}".format(str(entry_hunk["_counter"] + 1),
                                                                 str(frequency + 1))
            else:
                severity = 'W'
                message = "new word: hunk: " + str(entry_hunk["_counter"] + 1)
            suggestions, lexicon_words = lexicon.find_similar(lexicon.norm_punc(word_str),
                                                              str(entry_hunk["word"]),
                                                              5 + bool(frequency != -1), 0.6,
                                                              lexicon_words)
            if frequency != -1:
                suggestions = suggestions[1:]

            reports.append(
                Report(severity, toolname, entry_hunk["word"], message,
                       Fragment(document.code.filename, ", ".join(suggestions))
                       .add_offset(-len(entry_hunk["word"]) * 8, (-1,0))))

    return reports


def word_filtered(document):
    """Iterate over words in the filtered text."""
    segmenter = Segmenter()
    dev_re = re.compile(r"^(rBM|t)\d+?$", re.IGNORECASE)

    instr_pos = {
        "sect": {"*": ["name"]},
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
            "kbd": "*", "math": "*", "default": "*"
        },
        "literal": "*", "standalone": "*"
    }

    for part in rst_walker.iter_nodeparts_instr(document.body, instr_pos, instr_neg):
        par_node = part.parent_node
        while par_node.node_name == "text":
            par_node = par_node.parent_node.parent_node

        # refbox parts
        if (par_node.node_name == "field" and
                (str(par_node.name.code) in {"File", "Maintainer"} or
                    re.match(r"Author(?:[\(/]?s\)?)?", str(par_node.name.code)))):
            continue

        for word in segmenter.iter_word(part.code):
            if len(word) < 2:
                continue
            if re.search(dev_re, str(word)):
                continue
            yield word


OPS = (
    ("new-word", search, search_pre),
)

if __name__ == "__main__":
    from monostyle.__main__ import main_mod
    main_mod(__doc__, OPS, __file__)
