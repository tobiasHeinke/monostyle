
"""
spelling
~~~~~~~~

Create or compare words against a lexicon.
"""

import os
import re
import csv
from difflib import SequenceMatcher

import monostyle.util.monostylestd as monostylestd
from monostyle.util.report import Report
from monostyle.util.fragment import Fragment

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
        for stored_word, count, _ in data[word_cont[0]]:
            if word_cont == str(stored_word):
                found_count = int(count)
                break

        if found_count < threshold:
            line = None
            if found_count != -1:
                severity = 'I'
                msg = "rare word: hunk: {0} lex: {1}".format(str(hunk_count + 1),
                                                             str(found_count + 1))
            else:
                severity = 'W'
                msg = "new word: hunk: " + str(hunk_count + 1)
                line = Fragment(word.fn, ", ".join(find_similar(norm_punc(str(word), re_lib),
                                                                word_cont,data, 5, 0.6)))

            reports.append(Report(severity, toolname, word, msg, line))

    return reports


def find_similar(word_str, word_cont, lexicon, count, sim_threshold):
    """Find similar words within a lexicon with adaptive filtering."""
    def iter_lexicon(word_cont, lexicon):
        first_char = word_cont[0]
        value = lexicon[first_char]
        yield from reversed(value)
        for key, value in lexicon.items():
            if key != first_char:
                yield from reversed(value)

    similars = []
    word_chars = set(ord(c) for c in word_cont)
    for stored_word, _, stored_chars in iter_lexicon(word_cont, lexicon):
        len_deviation = abs(len(word_cont) - len(stored_word)) / len(word_cont)
        if len_deviation >= 2:
            continue
        sim_rough = len(word_chars.intersection(stored_chars)) / len(word_chars) - len_deviation
        is_not_full = bool(len(similars) < count)
        if is_not_full or sim_rough >= min_rough:
            matcher = SequenceMatcher(None, word_cont, stored_word)
            sim_quick = matcher.quick_ratio()
            if is_not_full or sim_quick >= min_quick:
                sim_slow = matcher.ratio()
                if sim_slow == 1 and word_cont == stored_word:
                    continue
                if is_not_full:
                    similars.append((stored_word, sim_slow, sim_quick, sim_rough))
                else:
                    min_value = None
                    min_index = 0
                    for index, ent in enumerate(similars):
                        if min_value is None or ent[1] <= min_value:
                            min_index = index
                            min_value = ent[1]

                    similars[min_index] = (stored_word, sim_slow, sim_quick, sim_rough)

                min_quick = min(s[2] for s in similars)
                min_rough = min(s[3] for s in similars)

    similars.sort(key=lambda key: key[1], reverse=True)
    return tuple(lower_first_reverse(ent[0], word_str) for ent in similars
                 if ent[1] >= sim_threshold)


def build_lexicon(re_lib):
    """Build lexicon by looping over files."""
    rst_parser = RSTParser()
    lexicon = dict()
    for fn, text in monostylestd.rst_texts():
        document = rst_parser.parse(rst_parser.document(fn, text))
        lexicon = populate_lexicon(document, lexicon, re_lib)

    # Flatten tree to list.
    lexicon_flat = []
    for val in lexicon.values():
        lexicon_flat.extend(val)

    # Sort list by highest occurrence.
    lexicon_flat.sort(key=lambda word: word[1], reverse=True)
    return lexicon_flat


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


def split_lexicon(lexicon_flat):
    """Split lexicon by first char."""
    lexicon = dict()
    for ent in lexicon_flat:
        first_char = ent[0][0]
        if first_char not in lexicon.keys():
            lexicon.setdefault(first_char, [])
        lexicon[first_char].append(ent)

    return lexicon


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
    """Normalize the word's punctuation."""
    word_cont = re.sub(re_lib["hypen"], '-', word_cont)
    word_cont = re.sub(re_lib["apostrophe"], '\'', word_cont)
    return word_cont


def lower_first(word):
    """Lower case of first char in hypened compound."""
    new_word = []
    for compound in word.split('-'):
        if len(compound) != 0:
            new_word.append(compound[0].lower() + compound[1:])
        else:
            new_word.append(compound)

    return '-'.join(new_word)


def lower_first_reverse(word, ref):
    """Upper case of first char in hypened compound based on a reference word."""
    new_word = []
    for compound_word, compound_ref in zip(word.split('-'), ref.split('-')):
        if (len(compound_word) != 0 and len(compound_ref) != 0 and
                compound_ref[0].isupper()):
            new_word.append(compound_word[0].upper() + compound_word[1:])
        else:
            new_word.append(compound_word)

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


def search_pre(_):
    def add_charset(lexicon):
        for ent in lexicon:
            ent.append(set(ord(c) for c in ent[0].lower()))
        return lexicon

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
    args["data"] = split_lexicon(add_charset(data))
    args["config"] = {"threshold": threshold}

    return args


OPS = (
    ("search", search, search_pre),
)


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
