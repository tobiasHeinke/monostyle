
"""
natural
~~~~~~~

Tools for natural language and style.
"""

import re

import monostyle.util.monostylestd as monostylestd
from monostyle.util.report import Report, getline_punc
from monostyle.rst_parser.core import RSTParser
import monostyle.rst_parser.walker as rst_walker
from monostyle.util.segmenter import Segmenter
from monostyle.util.pos import PartofSpeech
from monostyle.util.porter_stemmer import Porterstemmer

PorterStemmer = Porterstemmer()
Segmenter = Segmenter()
POS = PartofSpeech()


def abbreviation_pre(_):
    """Search for abbreviation/acronyms without an explanation."""
    def is_explanation(abbr, desc):
        """Check if the words start with the letters of the abbreviation."""
        desc_split = []
        for lexeme in re.split(r"[\s-]", desc):
            for camel_m in re.finditer(r"([A-Z]+|\A)[^A-Z]+", lexeme):
                desc_split.append(camel_m.group(0)[0])

        return "".join(desc_split).upper().endswith(abbr.rstrip('s').upper())

    rst_parser = RSTParser()
    explanations = dict()
    ignore = monostylestd.get_data_file("common_abbr")

    for entry in POS.get(("abbreviation",), joined=True):
        if POS.isabbr(entry + "."):
            ignore.append(entry + ".")

    ignore = list(entry.upper() for entry in ignore)

    instr_pos = {
        "sect": {"*": ["name"]},
        "field": {"*": ["name", "body"]},
        "*": {"*": ["head", "body"]}
    }
    instr_neg = {
        "dir": {
            "figure": ["head"],
            "code-block": "*", "default": "*", "include": "*", "index": "*",
            "math": "*", "youtube": "*", "vimeo": "*"
        },
        "substdef": {"image": ["head"], "unicode": "*", "replace": "*"},
        "doctest": "*", "target": "*", "comment": "*",
        "role": {
            "kbd": "*", "class": "*", "mod": "*", "math": "*", "term": "*"
        },
        "literal": "*", "standalone": "*"
    }

    before_test_re = re.compile(r"\(\s*?\Z")
    after_test_re = re.compile(r"\A\s*?\(")
    after_re = re.compile(r"\A\s*?\(([^\)]+?)\)")

    for filename, text in monostylestd.rst_texts():
        document = rst_parser.parse(rst_parser.document(filename, text))

        # todo glossary terms as explanation?
        explanation_file = []
        for node in rst_walker.iter_node(document.body, ("role",), enter_pos=False):
            if not rst_walker.is_of(node, "role", "abbr"):
                continue

            explanation_file.append((str(node.head.code).strip(), node.head.code.start_pos))

        explanations[filename] = explanation_file

        # Plain text/no markup explanations.
        for part in rst_walker.iter_nodeparts_instr(document.body, instr_pos, instr_neg):
            for word in Segmenter.iter_word(part.code):
                if not POS.isacr(word) and not POS.isabbr(word):
                    continue

                word_str = str(word).strip()
                before, _, after = part.code.slice(word.start_pos, word.end_pos)
                if re.match(after_test_re, str(after)):
                    if after_m := re.match(after_re, str(after)):
                        if is_explanation(word_str, after_m.group(1)):
                            explanation_file.append((word_str, word.start_pos))

                elif re.search(before_test_re, str(before)):
                    before_pattern = (r"((?:\b[\w\d-]+ ){",
                                      str(sum(c.isupper() for c in word_str)),
                                      r"})\s*?\(\s*?\Z")
                    if before_m := re.search("".join(before_pattern), str(before)):
                        if is_explanation(word_str, before_m.group(1)):
                            explanation_file.append((word_str, word.start_pos))

    args = dict()
    args["data"] = {"explanations": explanations, "ignore": ignore}
    args["config"] = (instr_pos, instr_neg)
    return args


def abbreviation(document, reports, data, config):
    toolname = "abbreviation"

    for part in rst_walker.iter_nodeparts_instr(document.body, config[0], config[1]):
        for word in Segmenter.iter_word(part.code):
            if not POS.isacr(word) and not POS.isabbr(word):
                continue
            if str(word).upper() in data["ignore"]:
                continue
            word_str = str(word)
            word_re = re.compile(word_str + r"s?\s*?\Z" if not word_str.endswith("s")
                                 else word_str + r"?\s*?\Z")
            for entry, loc in data["explanations"][document.code.filename]:
                if re.match(word_re, entry):
                    if word.start_pos < loc:
                        msg = "abbreviation before its explanation"
                        line = getline_punc(part.code, word.start_pos, len(word), 50, 30)
                        reports.append(Report('I', toolname, word, msg, line))
                    break

            else:
                msg = "no explanation on same page"
                severity = 'I'
                found = False
                for key, value in data["explanations"].items():
                    if key == document.code.filename:
                        continue
                    for entry_rec, _ in value:
                        if re.match(word_re, entry_rec):
                            found = True
                            break
                    if found:
                        # Compare folder hierarchy.
                        dir_key = key.strip("/")
                        dir_key = dir_key[:dir_key.rfind("/")] if "/" in dir_key else ""
                        dir_doc = document.code.filename.strip("/")
                        dir_doc = dir_doc[:dir_doc.rfind("/")] if "/" in dir_doc else ""

                        if len(dir_key) <= len(dir_doc):
                            if dir_key == dir_doc:
                                msg += " (same directory)"
                            elif dir_doc.startswith(dir_key):
                                msg += " (above file)"
                            else:
                                severity = 'W'
                        else:
                            severity = 'W'
                            if dir_key.startswith(dir_doc):
                                msg += " (below file)"
                        break
                if not found:
                    msg = "no explanation"
                    severity = 'W'

                line = getline_punc(part.code, word.start_pos, len(word), 50, 30)
                reports.append(Report(severity, toolname, word, msg, line))

    return reports


def indefinite_article_pre(_):
    args = dict()
    args["data"] = monostylestd.get_data_file("indefinite_article")

    re_lib = dict()
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
            for entry in data["syllable"]:
                if word_lower.startswith(entry):
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
            "code-block": "*", "default": "*", "include": "*", "index": "*", "toctree": "*",
            "parsed-literal": "*", "math": "*", "youtube": "*", "vimeo": "*"
        },
        "substdef": {"image": ["head"], "unicode": "*", "replace": "*"},
        "doctest": "*", "target": "*",
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
                                message = Report.existing(what="a", where="before vowel")
                                line = getline_punc(document.body.code, word.start_pos,
                                                    len(word_str), 50, 30)
                                reports.append(Report('E', toolname, word, message, line))
                        else:
                            if not is_fp(word, word_str, data["a"]):
                                message = Report.existing(what="a", where="before vowel sound")
                                line = getline_punc(document.body.code, word.start_pos,
                                                    len(word_str), 50, 30)
                                reports.append(Report('E', toolname, word, message, line))

                    elif buf in ("an", "An"):
                        if re.match(digit_re, word_str):
                            message = Report.existing(what="an", where="before digit")
                            line = getline_punc(document.body.code, word.start_pos,
                                                len(word_str), 50, 30)
                            reports.append(Report('E', toolname, word, message, line))
                        else:
                            if re.match(vowel_re, word_str):
                                if not is_fp(word, word_str, data["an"]):
                                    message = Report.existing(what="an",
                                                              where="before consonant sound")
                                    line = getline_punc(document.body.code, word.start_pos,
                                                        len(word_str), 50, 30)
                                    reports.append(Report('E', toolname, word, message, line))
                            else:
                                if is_fp(word, word_str, data["a"]):
                                    message = Report.existing(what="an", where="before consonant")
                                    line = getline_punc(document.body.code, word.start_pos,
                                                        len(word_str), 50, 30)
                                    reports.append(Report('E', toolname, word, message, line))

                    buf = None

            if part.parent_node.node_name == "role":
                buf = None

        else:
            if part.parent_node.node_name in ("def", "bullet", "enum", "field", "line"):
                buf = None

    return reports


def collocation_pre(_):
    """Find spaced versions of joined compounds."""
    global listsearch
    import monostyle.listsearch as listsearch
    import monostyle.spelling as spelling

    def split_rec(lexicon, word, is_first_level, result=None, branch=None):
        if result is None:
            result = []
        if branch is None:
            branch = []

        c = word[0]
        if c in lexicon.keys():
            for word_rec in lexicon[c]:
                if len(word_rec) > len(word) or not word.startswith(word_rec):
                    continue

                if len(word_rec) != len(word):
                    branch_copy = branch.copy()
                    branch_copy.append(word_rec)
                    result = split_rec(lexicon, word[len(word_rec):], False, result, branch_copy)

                else:
                    if not is_first_level:
                        branch.append(word_rec)
                        result.append(branch)

        return result

    lexicon = spelling.read_csv_lexicon()
    if not lexicon:
        return None

    # prefixes, file extensions (containing a vowel)
    ignore = ('ad', 'al', 'ati', 'de', 'ed', 'eg', 'el', 'es', 'ing', 'po', 'py', 're', 'un')

    lexicon_new = []
    for word, _ in lexicon:
        if "-" in word or "." in word or POS.isacr(word):
            continue
        if re.search(r"\d", word):
            continue
        # non ASCII vowels
        if len(word) < 4 and not re.search(r"[aeiou]", word):
            continue
        if word in ignore:
            continue

        lexicon_new.append(word)

    lexicon = spelling.split_lexicon(lexicon_new)
    del lexicon_new

    searchlist = []
    for value in lexicon.values():
        for word in value:
            if len(word) <= 4:
                continue

            result = split_rec(lexicon, word, True)
            if result:
                terms = list(" ".join(group) for group in result)
                searchlist.append([terms, word])

    args = dict()
    args["config"] = listsearch.parse_config("BIO")
    args["data"] = listsearch.compile_searchlist(searchlist, args["config"])

    return args


def collocation(document, reports, data, config):
    return listsearch.search(document, reports, data, config)


def grammar_pre(_):
    toolname = "grammar"

    re_lib = dict()
    pattern_str = r"s's"
    pattern = re.compile(pattern_str)
    message = Report.existing(what="s apostrophe", where="after s")
    re_lib["sapos"] = (pattern, message)

    pattern_str = r"'s\-"
    pattern = re.compile(pattern_str)
    message = Report.existing(what="apostrophe", where="in compound")
    re_lib["aposcomp"] = (pattern, message)

    pattern_str = (r"(?:'",
                   '|'.join((r"(?<!numb)er", "more", "less", "different(?:ly)?",
                             "else", "otherwise")), r")\s+?then")
    pattern = re.compile(''.join(pattern_str), re.DOTALL)
    message = Report.substitution(what="then", where="after comparison", with_what="than")
    re_lib["comparethen"] = (pattern, message)

    # FP 'only', not match 'by'
    pattern_str = (r"\w(.)y\b\s+?\w[\w\-]+\1y\b")
    pattern = re.compile(''.join(pattern_str), re.DOTALL)
    message = Report.existing(what="two adverbs/adjectives with the same suffix")
    re_lib["adsuffix"] = (pattern, message)

    args = dict()
    args["re_lib"] = re_lib
    args["config"] = {"severity": 'W', "toolname": toolname}

    return args


def hyphen_pre(_):
    """Find spaced or joined versions of hyphened compounds."""
    global listsearch
    import monostyle.listsearch as listsearch
    import monostyle.spelling as spelling

    ratio_threshold = 0.55
    count_threshold_joined = 3
    # can be lower if the spelling is uniform
    count_threshold_spaced = 6

    lexicon = spelling.read_csv_lexicon()
    if not lexicon:
        return None

    searchlist = []
    dash_re = re.compile(r"(?<!\A)\-(?!\Z)")
    for word, count in lexicon:
        if not re.search(dash_re, word):
            continue

        word_join = re.sub(r"\-", "", word)
        count = int(count) + 1
        for word_rec, count_rec in lexicon:
            if word_join != word_rec:
                continue

            count_rec = int(count_rec) + 1
            if (count_rec / (count_rec + count) < ratio_threshold and
                    (count_rec + count / 2) > count_threshold_joined):
                searchlist.append([word_rec, word])
                break

        if count > count_threshold_spaced:
            searchlist.append([re.sub(dash_re, " ", word), word])

    args = dict()
    args["config"] = listsearch.parse_config("BIO")
    args["data"] = listsearch.compile_searchlist(searchlist, args["config"])

    return args


def hyphen(document, reports, data, config):
    return listsearch.search(document, reports, data, config)


def passive_pre(_):
    toolname = "passive"

    re_lib = dict()
    pattern_str = (r"(\b", r"\b|\b".join(("be", "being", "been", "am", "is",
                                          "are", "was", "were")), r"\b|",
                   r"\bg[eo]t(?:s|ten)?\b)", # get
                   r"\s+",
                   r"(\b[\w-]+e[dn]\b|\b",
                   r"\b|\b".join(monostylestd.get_data_file("irregular_participle")), r"\b)")

    pattern = re.compile(''.join(pattern_str), re.DOTALL)
    message = Report.existing(what="passive voice")
    re_lib["passive"] = (pattern, message)

    args = dict()
    args["re_lib"] = re_lib
    args["config"] = {"severity": 'I', "toolname": toolname}

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
            "code-block": "*", "default": "*", "include": "*", "index": "*",
            "math": "*", "youtube": "*", "vimeo": "*"
        },
        "substdef": {"image": ["head"], "unicode": "*", "replace": "*"},
        "doctest": "*", "target": "*",
        "role": {
            "kbd": "*", "class": "*", "mod": "*", "math": "*"
        },
        "literal": "*", "standalone": "*"
    }

    for part in rst_walker.iter_nodeparts_instr(document.body, instr_pos, instr_neg):
        for pattern, message in re_lib.values():
            part_str = str(part.code)
            for m in re.finditer(pattern, part_str):
                output = part.code.slice_match_obj(m, 0, True)
                line = getline_punc(document.body.code, output.start_pos,
                                    output.span_len(True), 50, 0)
                reports.append(Report(config.get("severity"), config.get("toolname"),
                                      output, message, line))

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

    def compare(node_cur, sen_full, counter, reports, sub_para=False, is_last=False):
        if node_cur.node_name == "sect":
            if counter["sect"] > conf["sect_len"]:
                output = node_cur.code.copy().clear(True)
                message = Report.quantity(what="long heading",
                                          how="{0}/{1} letters".format(
                                              counter["sect"], conf["sect_len"]))
                reports.append(Report('I', toolname, output, message, node_cur.code))

        else:
            if counter["sen"] > conf["sen_len"]:
                output = sen_full.copy().clear(True)
                message = Report.quantity(what="long sentence",
                                          how="{0}/{1} words".format(
                                              counter["sen"], conf["sen_len"]))
                reports.append(Report('I', toolname, output, message, sen_full))
            if not sub_para:
                if counter["para"] > conf["para_long"]:
                    output = node_cur.code.copy().clear(True)
                    message = Report.quantity(what="long paragraph",
                                              how="{0}/{1} sentences".format(
                                                  counter["para"], conf["para_long"]))
                    reports.append(Report('I', toolname, output, message, node_cur.code))
                check = False
                if counter["para"] <= conf["para_short"] and counter["para"] != 0:
                    counter["para_short"] += 1
                else:
                    check = True
                if (check or is_last):
                    if counter["para_short"] > 1:
                        output = node_cur.code.copy().clear(True)
                        message = Report.quantity(what="multiple short paragraph",
                                                  how="{0}/{1} paragraphs".format(
                                                      counter["para_short"], 1))

                        reports.append(Report('I', toolname, output, message, node_cur.code
                                              if not (node_cur.code.isspace() and node_cur.prev)
                                              else node_cur.prev.code))
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
            "*": ["head"], "include": "*", "index": "*", "toctree": "*",
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
    sen_full = None
    counter = dict.fromkeys({"sect", "sen", "para", "para_short"}, 0)

    for part in rst_walker.iter_nodeparts_instr(document.body, instr_pos, instr_neg, False):
        if node_cur is None or part.code.end_pos > node_cur.code.end_pos:
            if node_cur:
                if is_open and sen_full and not sen_full.isspace():
                    counter["para"] += 1
                node_prev = node_cur
                is_last = bool(rst_walker.is_of(node_cur.parent_node,
                                                ("def", "dir", "enum", "bullet", "field")) and
                               node_cur.next is None)
                reports = compare(node_cur, sen_full, counter, reports, is_last=is_last)
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
                reports = compare(node_prev, sen_full, counter, reports, is_last=True)
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
                                message = Report.quantity(what="long word",
                                                          how="{0}/{1} letters".format(
                                                              len(word), conf["word_len"]))
                                reports.append(Report('I', toolname, word, message))

                        if not sen_full:
                            sen_full = sen
                        else:
                            sen_full = document.body.code.slice(
                                           sen_full.start_lincol, sen.end_lincol, True)

                        if not is_open:
                            reports = compare(node_cur, sen_full, counter, reports, True)
                            counter["sen"] = 0
                            counter["para"] += 1
                            sen_full = None

                    # paragraph end
                    if (not part.parent_node.next and
                            part.parent_node.parent_node.parent_node.next):
                        reports = compare(node_cur, sen_full, counter, reports, True)
                        counter["sen"] = 0
                        sen_full = None

    if node_cur:
        if is_open and sen_full and not sen_full.isspace():
            counter["para"] += 1
        reports = compare(node_cur, sen_full, counter, reports, is_last=True)

    return reports


def repeated_words_pre(_):
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
        "doctest": "*", "target": "*",
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
                            message = Report.quantity(what="repeated words",
                                                      how=str(distance) + " words in between")
                            line = getline_punc(document.body.code, word.start_pos,
                                                word.span_len(True), 50, 30)
                            reports.append(Report(sev, toolname, word, message, line))
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
            if rst_walker.is_of(part, ("sect", "bullet", "enum", "line", "def", "field")):
                buf.clear()

    return reports


OPS = (
    ("abbreviation", abbreviation, abbreviation_pre, True),
    ("article", indefinite_article, indefinite_article_pre),
    ("collocation", collocation, collocation_pre),
    ("grammar", search_pure, grammar_pre),
    ("hyphen", hyphen, hyphen_pre),
    ("metric", metric, None),
    ("passive", search_pure, passive_pre),
    ("repeated", repeated_words, repeated_words_pre),
)


if __name__ == "__main__":
    from monostyle.cmd import main
    main(OPS, __doc__, __file__)
