
"""
spelling
~~~~~~~~

Create or compare words against a lexicon.
"""

import os
import re
import csv

import monostyle.util.monostyle_io as monostyle_io
from monostyle.util.report import Report
from monostyle.util.fragment import Fragment

from monostyle.rst_parser.core import RSTParser
import monostyle.rst_parser.walker as rst_walker
from monostyle.util.segmenter import Segmenter
from monostyle.util.lexicon import Lexicon


def search_pre(op):
    config_dir = monostyle_io.path_to_abs("monostyle")
    if not os.path.isdir(config_dir):
        print("No user config found skipping spell checking")
        return None

    lexicon = Lexicon(False)
    if not lexicon:
        if monostyle_io.ask_user("The lexicon does not exist in the user config folder ",
                                 "do you want to build it"):
            lex_new = build_lexicon()
            lexicon_write_csv(lex_new)
        else:
            return None

    config = dict(monostyle_io.get_override(__file__, op[0], "threshold", 3))
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
                                                              str(entry_hunk["word"]), 5, 0.6,
                                                              lexicon_words)
            line = Fragment(document.code.filename, ", ".join(suggestions))
            line = line.add_offset(-line.end_pos, (-1,0))

            reports.append(Report(severity, toolname, entry_hunk["word"], message, line))

    return reports


def build_lexicon():
    """Build lexicon by looping over files."""
    rst_parser = RSTParser()
    lexicon = Lexicon()
    for filename, text in monostyle_io.rst_texts():
        document = rst_parser.parse(rst_parser.document(filename, text))
        for word in word_filtered(document):
            lexicon.add(str(word))

    return lexicon


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
            "parsed-literal": "*", "math": "*", "youtube": "*", "vimeo": "*"
        },
        "substdef": {"image": ["head"], "unicode": "*", "replace": "*"},
        "doctest": "*", "target": "*", "comment": "*",
        "role": {
            "kbd": "*", "class": "*", "mod": "*", "math": "*"
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


def lexicon_write_csv(lexicon):
    lex_filename = monostyle_io.path_to_abs("monostyle/lexicon.csv")
    count = 0
    try:
        with open(lex_filename, 'w', newline='', encoding='utf-8') as csvfile:
            csv_writer = csv.writer(csvfile)
            for entry in lexicon.join():
                csv_writer.writerow(entry)
                count += 1

            print("wrote lexicon file with {0} words".format(count))

    except (IOError, OSError) as err:
        print("{0}: cannot write: {1}".format(lex_filename, err))



def difference(lex_stored, lex_new):
    """Show a differential between the current texts and the stored lexicon."""
    added, removed = lex_stored.compare(lex_new)
    monostyle_io.print_title("Added", True)
    for word in added:
        print(word)

    monostyle_io.print_title("Removed", True)
    for word in removed:
        print(word)


OPS = (
    ("new-word", search, search_pre),
)


def main():
    import argparse
    from monostyle.__main__ import setup

    descr = "Write lexicon."
    parser = argparse.ArgumentParser(description=descr)
    # first char to lowercase
    doc_str = difference.__doc__[0].lower() + difference.__doc__[1:]
    parser.add_argument("-d", "--diff",
                        action="store_true", dest="diff", default=False,
                        help=doc_str)

    parser.add_argument("-r", "--root",
                        dest="root", nargs='?', const="",
                        help="defines the ROOT directory of the project")

    args = parser.parse_args()

    if args.root is None:
        root_dir = os.getcwd()
    else:
        root_dir = os.path.normpath(args.root)

        if not os.path.exists(root_dir):
            print('Error: root {0} does not exists'.format(args.root))
            return 2

    root_dir = monostyle_io.norm_path_sep(root_dir)
    setup_sucess = setup(root_dir)
    if not setup_sucess:
        return 2

    lex_new = build_lexicon()
    if not args.diff:
        lexicon_write_csv(lex_new)
    else:
        lex_stored = Lexicon(False)
        if lex_stored is not None:
            difference(lex_stored, lex_new)


if __name__ == "__main__":
    main()
