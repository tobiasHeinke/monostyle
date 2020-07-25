
"""
spelling
~~~~~~~~

Create or compare words against a lexicon.
"""

import os
import re
import csv

import monostyle.util.monostylestd as monostylestd
from monostyle.util.report import Report

from monostyle.rst_parser.core import RSTParser
import monostyle.rst_parser.walker as rst_walker
from monostyle.util.segmenter import Segmenter
from monostyle.util.pos import PartofSpeech
from monostyle.util.char_catalog import CharCatalog

Segmenter = Segmenter()
POS = PartofSpeech()


def search(document, reports, re_lib, data, config):
    """Search for rare or new words."""
    toolname = "new-word"
    # compare words in the text.
    text_words = []
    for word in word_filtered(document):
        word_cont = str(word)
        word_cont = norm_punc(word_cont, re_lib)
        if not POS.isacr(word) and not POS.isabbr(word):
            word_cont = lower_first(word_cont)
        for ent in text_words:
            if word_cont == ent[1]:
                ent[2] += 1
                break
        else:
            text_words.append([word, word_cont, 0])


    threshold = config["threshold"]
    # compare words against the lexicon.
    for word, word_cont, hunk_count in text_words:
        found_count = -1
        for stored_word, count in data:
            if word_cont == str(stored_word):
                found_count = int(count)
                break

        if found_count < threshold:
            if found_count != -1:
                severity = 'I'
                msg = "rare word: hunk: {0} lex: {1}".format(str(hunk_count + 1),
                                                             str(found_count + 1))
            else:
                severity = 'W'
                msg = "new word: hunk: " + str(hunk_count + 1)

            reports.append(Report(severity, toolname, word, msg))

    return reports


def build_lexicon(re_lib):
    """Build lexicon by looping over files."""
    rst_parser = RSTParser()
    lexicon = dict()
    for fn, text in monostylestd.rst_texts():
        document = rst_parser.parse_full(rst_parser.document(fn, text))
        lexicon = populate_lexicon(document, lexicon, re_lib)

    lexicon = join_sort(lexicon)

    return lexicon


def populate_lexicon(document, lexicon, re_lib):
    """Populate lexicon with transformed words."""

    for word in word_filtered(document):
        word_cont = str(word)
        word_cont = norm_punc(word_cont, re_lib)
        if not POS.isacr(word) and not POS.isabbr(word):
            word_cont = lower_first(word_cont)
        first_char = word_cont[0].lower()
        # tree with leafs for each first char.
        if first_char not in lexicon.keys():
            lexicon.setdefault(first_char, [])
        leaf = lexicon[first_char]
        for ent in leaf:
            if ent[0] == word_cont:
                ent[1] += 1
                break
        else:
            new_word = [word_cont, 0]
            leaf.append(new_word)

    return lexicon


def join_sort(lexicon):
    # Flatten tree to list.
    lexicon_flat = []
    for val in lexicon.values():
        lexicon_flat.extend(val)

    # Sort list by highest occurrence.
    lexicon_flat.sort(key=lambda word: word[1], reverse=True)
    return lexicon_flat


def word_filtered(document):
    """Iterate over words in the filtered text."""

    dev_re = re.compile(r"^(rBM|t)\d+?$", re.IGNORECASE)

    instr_pos = {
        "sect": {"*": ["name"]},
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

    for part in rst_walker.iter_nodeparts_instr(document.body, instr_pos, instr_neg):

        par_node = part.parent_node
        while par_node.node_name == "text":
            par_node = par_node.parent_node.parent_node

        # refbox parts
        if (par_node.node_name != "field" or
                not(str(par_node.name.code) in ("File", "Maintainer") or
                    re.match(r"Author(?:[\(/]?s\)?)?", str(par_node.name.code)))):

            for line in part.code.splitlines():
                for word in Segmenter.iter_word(line):
                    word_cont = str(word)
                    if len(word) > 1:
                        if re.search(dev_re, word_cont):
                            continue
                        yield word


def norm_punc(word_cont, re_lib):
    """Iterate over words in the filtered text."""
    word_cont = re.sub(re_lib["hypen"], '-', word_cont)
    word_cont = re.sub(re_lib["apostrophe"], '\'', word_cont)
    return word_cont


def lower_first(word):
    new_word = []
    for compound in word.split('-'):
        if len(compound) != 0:
            new_word.append(compound[0].lower() + compound[1:])
        else:
            new_word.append(compound)

    return '-'.join(new_word)


def read_csv_lexicon():
    lexicon = []
    lex_fn = os.path.normpath(os.path.join(monostylestd.ROOT_DIR, "monostyle", "lexicon.csv"))
    try:
        with open(lex_fn, newline='', encoding='utf-8') as csvfile:
            csv_reader = csv.reader(csvfile)

            for row in csv_reader:
                lexicon.append(row)
        return lexicon

    except IOError:
        print("lexicon not found")
        return None


def write_csv_lexicon(lexicon):
    lex_fn = os.path.normpath(os.path.join(monostylestd.ROOT_DIR, "monostyle", "lexicon.csv"))
    count = 0
    try:
        with open(lex_fn, 'w', newline='', encoding='utf-8') as csvfile:
            csv_writer = csv.writer(csvfile)
            for ent in lexicon:
                csv_writer.writerow(ent)
                count += 1

            print("wrote lexicon file with {0} words".format(count))

    except (IOError, OSError) as err:
        print("{0}: cannot write: {1}".format(lex_fn, err))


def difference(lex_stored, lex_new):
    """Show a differential between the current texts and the stored lexicon."""

    lex_stored = set(ent[0] for ent in lex_stored)
    lex_new = set(ent[0] for ent in lex_new)

    monostylestd.print_title("Added", True)
    for word in sorted(lex_new.difference(lex_stored)):
        print(word + ', ', end="")

    monostylestd.print_title("Removed", True)
    for word in sorted(lex_stored.difference(lex_new)):
        print(word + ', ', end="")


def compile_lib():
    re_lib = dict()
    char_catalog = CharCatalog()
    re_lib["hypen"] = re.compile(r"[" + char_catalog.data["connector"]["hyphen"] + r"]")
    re_lib["apostrophe"] = re.compile(r"[" + char_catalog.data["connector"]["apostrophe"] + r"]")
    return re_lib


def pre():
    config_dir = os.path.normpath(os.path.join(monostylestd.ROOT_DIR, "monostyle"))
    if not os.path.isdir(config_dir):
        print("No user config found skipping spell checking")
        return None

    re_lib = compile_lib()

    data = read_csv_lexicon()
    if data is None:
        if monostylestd.ask_user(("The lexicon does not exist in the user config folder ",
                                  "do you want to build it")):
            lex_new = build_lexicon(re_lib)
            write_csv_lexicon(lex_new)
            data = lex_new
        else:
            return None

    threshold = monostylestd.get_override(__file__, "search", "threshold", 3)
    args = dict()
    args["re_lib"] = re_lib
    args["data"] = data
    args["config"] = {"threshold": threshold}

    return args


OPS = (
    ("search", search, pre),
)


def init(op_names):
    ops = []
    if isinstance(op_names, str):
        op_names = [op_names]

    for op_name in op_names:
        for op in OPS:
            if op_name == op[0]:
                args = {}
                if len(op) > 2:
                    # evaluate pre
                    args = op[2]()
                ops.append((op[1], args))
                break
        else:
            print("spelling: unknown operation: " + op_name)

    return ops


def main():

    import argparse
    from monostyle import setup

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

    root_dir = monostylestd.replace_windows_path_sep(root_dir)
    monostylestd.ROOT_DIR = root_dir

    setup_sucess = setup(root_dir)
    if not setup_sucess:
        return 2

    lex_new = build_lexicon(compile_lib())
    if not args.diff:
        write_csv_lexicon(lex_new)
    else:
        lex_stored = read_csv_lexicon()
        if lex_stored is not None:
            difference(lex_stored, lex_new)


if __name__ == "__main__":
    main()
