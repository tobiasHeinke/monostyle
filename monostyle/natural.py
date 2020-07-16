
"""
natural
~~~~~~~

Tools for natural language and style.
"""

import os
import re

import monostyle.util.monostylestd as monostylestd
from monostyle.util.report import Report, print_reports
from monostyle.rst_parser.core import RSTParser
import monostyle.rst_parser.walker as rst_walker
from monostyle.util.segmenter import Segmenter
from monostyle.util.pos import PartofSpeech
from monostyle.util.porter_stemmer import Porterstemmer

PorterStemmer = Porterstemmer()
Segmenter = Segmenter()
POS = PartofSpeech()

def heading_cap_pre():
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

    def word_cap(reports, word, is_first_word, is_last_word):
        word_str = str(word)
        if word_str[0].isupper() and (is_first_word or is_last_word):
            return reports

        path = POS.classify(word_str.lower())
        if (not (is_first_word or is_last_word) and
                (word_str[0].islower() !=
                 (len(path) != 0 and
                  (path[0] in ("preposition", "conjunction", "pronoun", "auxiliary") or
                   path[0] == "determiner" and path[1] == "article")))):

            where = "in heading"
            if is_first_word:
                where = "at the start of a heading"
            elif is_last_word:
                where = "at the end of a heading"
            msg = Report.misformatted(what="lowercase" if word_str[0].islower() else "uppercase",
                                      where=where)
            reports.append(Report('W', toolname, word, msg, node.name.code))
        return reports


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
        for part in rst_walker.iter_nodeparts_instr(node.name, instr_pos, instr_neg, False):
            if is_first_word and part.parent_node.prev is not None:
                is_first_word = False

            buf = None
            for word in Segmenter.iter_word(part.code):
                if buf:
                    reports = word_cap(reports, buf, is_first_word, False)
                    is_first_word = False
                buf = word

            if buf:
                # ignore part.next, one part per node
                is_last_word = bool(part.parent_node.next is None)
                reports = word_cap(reports, buf, is_first_word, is_last_word)
                is_first_word = False

            part_str = str(part.code)
            for pattern, msg in re_lib.values():
                for m in re.finditer(pattern, part_str):
                    out = part.code.slice_match_obj(m, 0, True)
                    reports.append(Report('W', toolname, out, msg, node.name.code))

    return reports


def indefinite_article_pre():
    args = dict()
    args["data"] = monostylestd.get_data_file("indefinite_article")

    re_lib = dict()
    re_lib["iaword"] = re.compile(r"\ba(n)?\s+?(\w+?)\b", re.DOTALL | re.IGNORECASE)
    re_lib["vowel"] = re.compile(r"[aeiouAEIOU]")
    re_lib["digit"] = re.compile(r"\d")

    args["re_lib"] = re_lib

    return args


def indefinite_article(document, reports, re_lib, data):
    """Check correct use of indefinite articles (a and an)."""
    toolname = "indefinite-article"

    def is_fp(word, word_str, data):
        """Check if is not a false positive."""
        if len(word) == 1 or POS.isacr(word):
            if word_str[0].lower() in data["letter"]:
                if len(word) == 1 or word_str not in data["acronym"]:
                    return False
        else:
            word_lower = word_str.lower()
            for ent in data["syllable"]:
                if word_lower.startswith(ent):
                    return False

        return True


    vowel_re = re_lib["vowel"]
    digit_re = re_lib["digit"]

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
        "target": "*",
        "role": {
            "class": "*", "mod": "*", "math": "*"
        },
        "literal": "*", "standalone": "*"
    }

    buf = None

    for part in rst_walker.iter_nodeparts_instr(document.body, instr_pos, instr_neg, False):
        if part.child_nodes.is_empty():
            for word in Segmenter.iter_wordsub(part.code, False):
                word_str = str(word).strip()
                if buf is None:
                    buf = word_str
                else:
                    if buf in ("a", "A"):
                        if re.match(vowel_re, word_str):
                            if is_fp(word, word_str, data["an"]):
                                msg = Report.existing(what="a", where="before vowel")
                                line = monostylestd.getline_punc(document.body.code, word.start_pos,
                                                                 len(word_str), 50, 30)
                                reports.append(Report('E', toolname, word, msg, line))
                        else:
                            if not is_fp(word, word_str, data["a"]):
                                msg = Report.existing(what="a", where="before vowel sound")
                                line = monostylestd.getline_punc(document.body.code, word.start_pos,
                                                                 len(word_str), 50, 30)
                                reports.append(Report('E', toolname, word, msg, line))

                    elif buf in ("an", "An"):
                        if re.match(digit_re, word_str):
                            msg = Report.existing(what="an", where="before digit")
                            line = monostylestd.getline_punc(document.body.code, word.start_pos,
                                                             len(word_str), 50, 30)
                            reports.append(Report('E', toolname, word, msg, line))
                        else:
                            if re.match(vowel_re, word_str):
                                if not is_fp(word, word_str, data["an"]):
                                    msg = Report.existing(what="an", where="before consonant sound")
                                    line = monostylestd.getline_punc(document.body.code,
                                                                     word.start_pos,
                                                                     len(word_str), 50, 30)
                                    reports.append(Report('E', toolname, word, msg, line))
                            else:
                                if is_fp(word, word_str, data["a"]):
                                    msg = Report.existing(what="an", where="before consonant")
                                    line = monostylestd.getline_punc(document.body.code,
                                                                     word.start_pos,
                                                                     len(word_str), 50, 30)
                                    reports.append(Report('E', toolname, word, msg, line))

                    buf = None

            if part.parent_node.node_name == "role":
                buf = None

        else:
            if part.parent_node.node_name in ("def", "bullet", "enum", "field", "line"):
                buf = None

    return reports


def grammar_pre():
    toolname = "grammar"

    re_lib = dict()
    pattern_str = r"s's"
    pattern = re.compile(pattern_str)
    msg = Report.existing(what="s apostrophe", where="after s")
    re_lib["sapos"] = (pattern, msg)

    pattern_str = r"'s\-"
    pattern = re.compile(pattern_str)
    msg = Report.existing(what="apostrophe", where="in compound")
    re_lib["aposcomp"] = (pattern, msg)

    pattern_str = (r"(?:'",
                   '|'.join((r"(?<!numb)er", "more", "less", "different(?:ly)?",
                             "else", "otherwise")), r")\s+?then")
    pattern = re.compile(''.join(pattern_str), re.DOTALL)
    msg = Report.substitution(what="then", where="after comparison", with_what="than")
    re_lib["comparethen"] = (pattern, msg)

    args = dict()
    args["re_lib"] = re_lib
    args["config"] = {"severity": 'W', "toolname": toolname}

    return args


def search_pure(document, reports, re_lib, config):
    """Iterate regex tools."""
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
        "literal": "*", "standalone": "*"
    }

    for part in rst_walker.iter_nodeparts_instr(document.body, instr_pos, instr_neg):
        for pattern, msg in re_lib.values():
            part_str = str(part.code)
            for m in re.finditer(pattern, part_str):
                out = part.code.slice_match_obj(m, 0, True)
                line = monostylestd.getline_punc(document.body.code,
                                                 part.code.start_pos + m.start(),
                                                 len(m.group(0)), 50, 0)
                reports.append(Report(config.get("severity"), config.get("toolname"),
                                      out, msg, line))

    return reports


def metric(document, reports):
    """Measure length of segments like paragraphs, sentences and words."""
    toolname = "metric"

    # source: https://www.gov.uk/guidance/content-design/writing-for-gov-uk
    conf = {
        "sect_len": 69,
        # gov.uk recommends 8/9 but too many technical terms
        "word_len": 15,
        "sen_len": 25,
        "para_long": 5,
        "para_short": 2
    }

    def compare(node_cur, sen, counter, reports, sub_para=False, is_last=False):
        if node_cur.node_name == "sect":
            if counter["sect"] > conf["sect_len"]:
                out = node_cur.code.copy().clear(True)
                msg = Report.quantity(what="long heading",
                                      how="{0}/{1} letters".format(
                                          counter["sect"], conf["sect_len"]))
                reports.append(Report('I', toolname, out, msg, node_cur.code))

        else:
            if counter["sen"] > conf["sen_len"]:
                out = sen.copy().clear(True)
                msg = Report.quantity(what="long sentence",
                                      how="{0}/{1} words".format(
                                          counter["sen"], conf["sen_len"]))
                reports.append(Report('I', toolname, out, msg, sen))
            if not sub_para:
                if counter["para"] > conf["para_long"]:
                    out = node_cur.code.copy().clear(True)
                    msg = Report.quantity(what="long paragraph",
                                          how="{0}/{1} sentences".format(
                                              counter["para"], conf["para_long"]))
                    reports.append(Report('I', toolname, out, msg, node_cur.code))
                check = False
                if counter["para"] <= conf["para_short"] and counter["para"] != 0:
                    counter["para_short"] += 1
                else:
                    check = True
                if (check or is_last):
                    if counter["para_short"] > 1:
                        out = node_cur.code.copy().clear(True)
                        msg = Report.quantity(what="multiple short paragraph",
                                              how="{0}/{1} paragraphs".format(
                                                  counter["para_short"], 1))
                        reports.append(Report('I', toolname, out, msg, node_cur.code))
                        counter["para_short"] = 0
                    elif counter["para"] != 0:
                        counter["para_short"] = 0

        return reports

    instr_pos = {
        "sect": {"*": ["name"]},
        "*": {"*": ["head", "body"]}
    }
    instr_neg = {
        "dir": {
            "*": ["head"], "include": "*", "toctree": "*",
            "parsed-literal": "*", "math": "*", "youtube": "*", "vimeo": "*"
        },
        "def": {"*": ["head"]},
        "substdef": {"*": ["head"], "unicode": "*", "replace": "*"},
        "target": "*", "comment": "*",
        "role": {
            "kbd": "*", "menuselection": "*", "class": "*", "mod": "*", "math": "*"
        },
        "standalone": "*", "literal": "*", "substitution": "*"
    }
    node_cur = None
    node_prev = None
    is_open = False
    sen = None
    counter = {
        "sect": 0,
        "sen": 0,
        "para": 0,
        "para_short": 0,
    }

    for part in rst_walker.iter_nodeparts_instr(document.body, instr_pos, instr_neg, False):
        if node_cur is None or part.code.end_pos > node_cur.code.end_pos:
            if node_cur:
                if is_open and sen and not sen.isspace():
                    counter["para"] += 1
                node_prev = node_cur
                is_last = bool(rst_walker.is_of(node_cur.parent_node,
                                                ("def", "dir", "enum", "bullet", "field")) and
                               node_cur.next is None)
                reports = compare(node_cur, sen, counter, reports, is_last=is_last)
                if is_last:
                    counter["para_short"] = 0
                    node_prev = None

                if (rst_walker.is_of(part, "dir", ("code-block", "default")) or
                        rst_walker.is_of(part, "comment")):
                    counter["para_short"] = 0
                    continue

            if (part.parent_node.node_name == "sect" or
                    (part.parent_node.node_name == "text" and
                     not rst_walker.is_of(part.parent_node.parent_node, "text"))):
                node_cur = part.parent_node
            else:
                node_cur = None

            for key in counter:
                if key != "para_short":
                    counter[key] = 0

            if (node_cur and node_prev and
                    (node_cur.node_name == "sect" or
                     (rst_walker.is_of(node_cur.parent_node,
                                       ("def", "dir", "enum", "bullet", "field")) and
                      node_cur.prev is None))):
                reports = compare(node_prev, sen, counter, reports, is_last=True)
                counter["para_short"] = 0
                node_prev = None

        if node_cur and part.child_nodes.is_empty():
            if part.code.end_pos <= node_cur.code.end_pos:
                if node_cur.node_name == "sect":
                    counter["sect"] += len(part.code)
                else:
                    for sen, is_open in Segmenter.iter_sentence(part.code, output_openess=True):
                        for word in Segmenter.iter_word(sen):
                            counter["sen"] += 1
                            if len(word) >= conf["word_len"]:
                                msg = Report.quantity(what="long word",
                                                      how="{0}/{1} letters".format(
                                                          len(word), conf["word_len"]))
                                reports.append(Report('I', toolname, word, msg))

                        if not is_open:
                            reports = compare(node_cur, sen, counter, reports, True)
                            counter["sen"] = 0
                            counter["para"] += 1

    if node_cur:
        if is_open and sen and not sen.isspace():
            counter["para"] += 1
        reports = compare(node_cur, sen, counter, reports, is_last=True)

    return reports


def repeated_words_pre():
    config = dict()
    # Number of the word within to run the detection.
    config["buf_size"] = monostylestd.get_override(__file__, "repeated", "buf_size", 4)
    return {"config": config}


def repeated_words(document, reports, config):
    """Find repeated words e.g. the the example."""
    toolname = "repeated-words"

    def porter_stemmer_patch(word_lower):
        """Distinguish some words."""
        # on vs. one
        if word_lower in ("one", "ones"):
            return "one"
        # us vs. use
        if word_lower in ("use", "uses", "used"):
            return "use"

        return PorterStemmer.stem(word_lower, 0, len(word_lower)-1)

    buf_size = config["buf_size"]
    if buf_size < 2:
        print(toolname, ": 'buf_size' has to be 2 or higher")
        return reports

    instr_pos = {
        "sect": {"*": ["name", "name_end"]},
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
        "target": "*",
        "role": {
            "kbd": "*", "menuselection": "*", "class": "*", "mod": "*", "math": "*"
        },
        "literal": "*", "standalone": "*"
    }

    buf = []
    # config: min distance from where on to apply filter
    ignore_article = (("a", "an", "the"), 2)
    ignore_pre_pro = (("and", "or", "to", "as", "of"), 1)

    for part in rst_walker.iter_nodeparts_instr(document.body, instr_pos, instr_neg, False):
        if part.child_nodes.is_empty():
            if rst_walker.is_of(part, "sect", "*", "name_end"):
                buf.clear()
                continue

            for sen, is_open in Segmenter.iter_sentence(part.code, output_openess=True):
                for word in Segmenter.iter_word(sen):
                    word_lower = str(word).lower()
                    word_stem = porter_stemmer_patch(word_lower)

                    for distance, word_buf in enumerate(reversed(buf)):
                        if word_buf == word_stem:
                            if word_lower == "rst":
                                continue
                            if distance >= ignore_article[1] and word_stem in ignore_article[0]:
                                continue
                            if distance >= ignore_pre_pro[1] and word_stem in ignore_pre_pro[0]:
                                continue

                            sev = 'W' if distance == 0 else 'I'
                            msg = Report.quantity(what="repeated words",
                                                  how=str(distance) + " words in between")
                            line = monostylestd.getline_punc(document.body.code, word.start_pos,
                                                             word.span_len(), 50, 30)
                            reports.append(Report(sev, toolname, word, msg, line))
                            break

                    if len(buf) == buf_size - 1:
                        buf.pop(0)

                    buf.append(word_stem)

                if not is_open:
                    buf.clear()

            if (rst_walker.is_of(part, "text") and
                    not rst_walker.is_of(part.parent_node.parent_node, "text")):
                buf.clear()

        else:
            if rst_walker.is_of(part, ("bullet", "enum", "line", "def", "field")):
                buf.clear()

    return reports



def init(op_names):
    ops = []
    if isinstance(op_names, str):
        op_names = [op_names]

    for op_name in op_names:
        for op in OPS:
            if op_name == op[0]:
                args = {}
                if op[2] is not None:
                    # evaluate pre
                    args = op[2]()
                ops.append((op[1], args))
                break
        else:
            print("natural: unknown operation: " + op_name)
            return None

    return ops


def hub(op_names):
    rst_parser = RSTParser()
    ops = init(op_names)
    reports = []

    for fn, text in monostylestd.rst_texts():
        document = rst_parser.parse_full(rst_parser.document(fn, text))

        for op in ops:
            reports = op[0](document, reports, **op[1])

    return reports


OPS = (
    ("article", indefinite_article, indefinite_article_pre),
    ("heading-cap", heading_cap, heading_cap_pre),
    ("grammar", search_pure, grammar_pre),
    ("metric", metric, None),
    ("repeated", repeated_words, repeated_words_pre),
)


def main():
    import argparse
    from monostyle import setup

    descr = __doc__.replace('~', '')
    parser = argparse.ArgumentParser(description=descr)
    for op in OPS:
        doc_str = ''
        if op[1].__doc__ is not None:
            # first char to lowercase.
            doc_str = op[1].__doc__[0].lower() + op[1].__doc__[1:]
        parser.add_argument("--" + op[0], dest="op_names",
                            action='store_const', const=op[0], metavar="",
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

    reports = hub(args.op_names)
    print_reports(reports)


if __name__ == "__main__":
    main()
