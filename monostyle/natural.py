
"""
natural
~~~~~~~

Tools for natural language and style.
"""

import re

import monostyle.util.monostyle_io as monostyle_io
from monostyle.util.report import Report
from monostyle.rst_parser.core import RSTParser
import monostyle.rst_parser.walker as rst_walker
from monostyle.util.segmenter import Segmenter
from monostyle.util.part_of_speech import PartofSpeech
from monostyle.util.lexicon import Lexicon
from monostyle.util.porter_stemmer import Porterstemmer


def abbreviation_pre(_):
    def is_explanation(abbr, desc):
        """Check if the words start with the letters of the abbreviation."""
        desc_split = []
        for lexeme in re.split(r"[\s-]", desc):
            for camel_m in re.finditer(r"([A-Z]+|\A)[^A-Z]+", lexeme):
                desc_split.append(camel_m.group(0)[0])

        return "".join(desc_split).upper().endswith(abbr.rstrip('s').upper())

    rst_parser = RSTParser()
    segmenter = Segmenter()
    part_of_speech = PartofSpeech()
    explanations = dict()
    ignore = monostyle_io.get_data_file("common_abbr")

    for entry in part_of_speech.get(("abbreviation",), joined=True):
        if part_of_speech.isabbr(entry + "."):
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
            "kbd": "*", "math": "*", "term": "*"
        },
        "literal": "*", "standalone": "*"
    }

    before_test_re = re.compile(r"\(\s*?\Z")
    after_test_re = re.compile(r"\A\s*?\(")
    after_re = re.compile(r"\A\s*?\(([^\)]+?)\)")

    for filename, text in monostyle_io.doc_texts():
        document = rst_parser.parse(rst_parser.document(filename, text))

        # todo glossary terms as explanation?
        explanation_file = []
        for node in rst_walker.iter_node(document.body, "role", enter_pos=False):
            if not rst_walker.is_of(node, "role", "abbr"):
                continue

            explanation_file.append((str(node.head.code).strip(), node.head.code.start_pos))

        explanations[filename] = explanation_file

        # Plain text/no markup explanations.
        for part in rst_walker.iter_nodeparts_instr(document.body, instr_pos, instr_neg):
            for word in segmenter.iter_word(part.code):
                if not part_of_speech.isacr(word) and not part_of_speech.isabbr(word):
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


def abbreviation(toolname, document, reports, data, config):
    """Search for abbreviation/acronyms without an explanation."""
    segmenter = Segmenter()
    part_of_speech = PartofSpeech()

    for part in rst_walker.iter_nodeparts_instr(document.body, config[0], config[1]):
        for word in segmenter.iter_word(part.code):
            if not part_of_speech.isacr(word) and not part_of_speech.isabbr(word):
                continue
            if str(word).upper() in data["ignore"]:
                continue
            word_str = str(word)
            word_re = re.compile(word_str + r"s?\s*?\Z" if not word_str.endswith("s")
                                 else word_str + r"?\s*?\Z")
            for entry, loc in data["explanations"][document.code.filename]:
                if re.match(word_re, entry):
                    if word.start_pos < loc:
                        reports.append(
                            Report('I', toolname, word,
                                   Report.existing(what="abbreviation",
                                                   where="before its explanation"))
                            .set_line_punc(part.code, 50, 30))
                    break

            else:
                where = "on the same page"
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
                                where += " (same directory)"
                            elif dir_doc.startswith(dir_key):
                                where += " (above file)"
                            else:
                                severity = 'W'
                        else:
                            severity = 'W'
                            if dir_key.startswith(dir_doc):
                                where += " (below file)"
                        break
                if not found:
                    where = None
                    severity = 'W'

                reports.append(
                    Report(severity, toolname, word,
                           Report.missing(what="explanation", where=where))
                    .set_line_punc(part.code, 50, 30))

    return reports


def article_pre(_):
    args = dict()
    args["data"] = monostyle_io.get_data_file("indefinite_article")

    re_lib = dict()
    re_lib["vowel"] = re.compile(r"[aeiouAEIOU]")
    re_lib["digit"] = re.compile(r"\d")
    re_lib["token"] = re.compile(r"(\w+?)(?:_|\b)(?!\Z)")

    args["re_lib"] = re_lib

    return args


def article(toolname, document, reports, re_lib, data):
    """Check correct use of indefinite articles (a and an)."""
    segmenter = Segmenter()
    part_of_speech = PartofSpeech()
    vowel_re = re_lib["vowel"]
    digit_re = re_lib["digit"]
    token_re = re_lib["token"]

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
        "role": {"math": "*"},
        "literal": "*", "standalone": "*"
    }

    is_a = None
    for part in rst_walker.iter_nodeparts_instr(document.body, instr_pos, instr_neg, False):
        if not part.child_nodes.is_empty():
            if part.parent_node.node_name in {"def", "bullet", "enum", "field", "line"}:
                is_a = None
            continue

        for sen, stop in segmenter.iter_sentence(part.code):
            for word in segmenter.iter_word(sen, filter_numbers=False):
                word_str = str(word).strip()
                if len(word) < 3 and word_str in {"a", "A", "an", "An"}:
                    is_a = bool(word_str in {"a", "A"})
                elif is_a is not None:
                    if re.match(digit_re, word_str):
                        if not is_a:
                            reports.append(
                                Report('E', toolname, word,
                                       Report.existing(what="an", where="before digit"))
                                .set_line_punc(document.body.code, 50, 30))
                    else:
                        is_cons =  bool(not re.match(vowel_re, word_str))
                        is_cons_sound = is_cons
                        key = "a" if is_cons else "an"
                        token = word
                        if token_m := re.match(token_re, word_str):
                            token = word.slice_match(token_m, 1, True)
                        if (len(token) == 1 or part_of_speech.isacr(token) or
                                part_of_speech.isabbr(token)):
                            if word_str[0].lower() in data[key]["letter"]:
                                if len(word) == 1 or word_str not in data[key]["acronym"]:
                                    is_cons_sound = not is_cons
                        else:
                            for entry in data[key]["syllable"]:
                                if re.match(entry, word_str, re.IGNORECASE):
                                    key = "a" if not is_cons else "an"
                                    for entry_converse in data[key]["syllable"]:
                                        if re.match(entry_converse, word_str, re.IGNORECASE):
                                            if not entry_converse.startswith(entry):
                                                is_cons_sound = not is_cons
                                            break
                                    else:
                                        is_cons_sound =  not is_cons
                                    break

                        if is_a != is_cons_sound:
                            reports.append(
                                Report('E', toolname, word,
                                       Report.existing(what="a" if is_a else "an",
                                           where=" ".join(("before",
                                                    "consonant" if is_cons_sound else "vowel",
                                                    "sound" if is_cons_sound != is_cons else ""))))
                                .set_line_punc(document.body.code, 50, 30))

                    is_a = None

            if stop:
                is_a = None

        if part.parent_node.node_name == "role":
            is_a = None

    return reports


def collocation_pre(_):
    """Find spaced versions of joined compounds."""
    global listsearch
    import monostyle.listsearch as listsearch

    def split_rec(lexicon, word, is_first_level, result=None, branch=None):
        if result is None:
            result = []
        if branch is None:
            branch = []

        for word_rec, _ in lexicon.iter_sections(word[0]):
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

    part_of_speech = PartofSpeech()
    lexicon = Lexicon(False)
    if not lexicon:
        return None

    # prefixes, file extensions (containing a vowel)
    ignore = {'ad', 'al', 'ati', 'de', 'ed', 'eg', 'el', 'es', 'ing', 'po', 'py', 're', 'un'}

    removals = set()
    for word, _ in lexicon:
        if ("-" in word or "." in word or part_of_speech.isacr(word) or
                re.search(r"\d", word) or
                (len(word) < 4 and not re.search(r"[aeiou]", word)) or
                word in ignore):
            removals.add(word)

    for word in removals:
        lexicon.remove(word)

    terms = []
    for word, _ in lexicon:
        if len(word) <= 4:
            continue

        result = split_rec(lexicon, word, True)
        if result:
            terms.append((list(" ".join(group) for group in result), word))

    args = dict()
    args["config"] = listsearch.parse_flags("BIO")
    args["data"] = listsearch.compile_terms(terms, {"flags": args["config"]})

    return args


def collocation(toolname, document, reports, data, config):
    return listsearch.search(toolname, document, reports, data, config)


def grammar_pre(_):
    re_lib = dict()
    re_lib["sapos"] = (re.compile(r"s's"),
        Report.existing(what="s apostrophe", where="after s"))

    re_lib["aposcomp"] = (re.compile(r"'s\-"),
        Report.existing(what="apostrophe", where="in compound"))

    re_lib["comparethen"] = (
        re.compile(''.join((r"(?:'",
                            '|'.join((r"(?<!numb)er", "more", "less", "different(?:ly)?",
                                      "else", "otherwise")), r")\s+?then")), re.DOTALL),
        Report.substitution(what="then", where="after comparison", with_what="than"))

    # FP 'only', not match 'by'
    re_lib["adsuffix"] = (
        re.compile(''.join((r"\w(.)y\b\s+?\w[\w\-]+\1y\b")), re.DOTALL),
        Report.existing(what="two adverbs/adjectives with the same suffix"))

    args = dict()
    args["re_lib"] = re_lib
    args["config"] = {"severity": 'W'}

    return args


def hyphen_pre(_):
    """Find spaced or joined versions of hyphened compounds."""
    global listsearch
    import monostyle.listsearch as listsearch
    lexicon = Lexicon(False)
    if not lexicon:
        return None

    ratio_threshold = 0.55
    count_threshold_joined = 3
    # can be lower if the spelling is uniform
    count_threshold_spaced = 6


    terms = []
    dash_re = re.compile(r"(?<!\A)\-(?!\Z)")
    for word, entry in lexicon:
        if not re.search(dash_re, word):
            continue

        word_join = re.sub(r"\-", "", word)
        count = int(entry["_counter"]) + 1
        for word_rec, entry_rec in lexicon:
            if word_join != word_rec:
                continue

            count_rec = int(entry_rec["_counter"]) + 1
            if (count_rec / (count_rec + count) < ratio_threshold and
                    (count_rec + count / 2) > count_threshold_joined):
                terms.append([word_rec, word])
                break

        if count > count_threshold_spaced:
            terms.append([re.sub(dash_re, " ", word), word])

    args = dict()
    args["config"] = listsearch.parse_flags("BIO")
    args["data"] = listsearch.compile_terms(terms, {"flags": args["config"]})

    return args


def hyphen(toolname, document, reports, data, config):
    return listsearch.search(toolname, document, reports, data, config)


def metric(toolname, document, reports):
    """Measure length of segments like paragraphs, sentences and words."""
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
                reports.append(
                    Report('I', toolname, node_cur.code.copy().clear(True),
                           Report.quantity(what="long heading",
                               how="{0}/{1} letters".format(
                                   counter["sect"], conf["sect_len"])),
                           node_cur.code))

        else:
            if counter["sen"] > conf["sen_len"]:
                reports.append(
                    Report('I', toolname, sen_full.copy().clear(True),
                           Report.quantity(what="long sentence",
                               how="{0}/{1} words".format(
                                   counter["sen"], conf["sen_len"])),
                           sen_full))
            if not sub_para:
                if counter["para"] > conf["para_long"]:
                    reports.append(
                        Report('I', toolname, node_cur.code.copy().clear(True),
                               Report.quantity(what="long paragraph",
                                   how="{0}/{1} sentences".format(
                                       counter["para"], conf["para_long"])),
                               node_cur.code))
                check = False
                if counter["para"] <= conf["para_short"] and counter["para"] != 0:
                    counter["para_short"] += 1
                else:
                    check = True
                if (check or is_last):
                    if counter["para_short"] > 1:
                        reports.append(
                            Report('I', toolname, node_cur.code.copy().clear(True),
                                   Report.quantity(what="multiple short paragraph",
                                       how="{0}/{1} paragraphs".format(
                                           counter["para_short"], 1)),
                                   node_cur.code
                                   if not (node_cur.code.isspace() and node_cur.prev)
                                   else node_cur.prev.code))
                        counter["para_short"] = 0
                    elif counter["para"] != 0:
                        counter["para_short"] = 0

        return reports

    segmenter = Segmenter()
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
            "kbd": "*", "menuselection": "*", "math": "*"
        },
        "standalone": "*", "literal": "*", "substitution": "*"
    }
    node_cur = None
    node_prev = None
    stop = None
    sen_full = None
    counter = dict.fromkeys({"sect", "sen", "para", "para_short"}, 0)

    for part in rst_walker.iter_nodeparts_instr(document.body, instr_pos, instr_neg, False):
        if node_cur is None or part.code.end_pos > node_cur.code.end_pos:
            if node_cur:
                if not stop and sen_full and not sen_full.isspace():
                    counter["para"] += 1
                node_prev = node_cur
                is_last = bool(rst_walker.is_of(node_cur.parent_node,
                                                {"def", "dir", "enum", "bullet",
                                                 "field", "cell"}) and
                               node_cur.next is None)
                reports = compare(node_cur, sen_full, counter, reports, is_last=is_last)
                if is_last:
                    counter["para_short"] = 0
                    node_prev = None
                    sen_full = None

                if (rst_walker.is_of(part, "dir", {"code-block", "default"}) or
                        rst_walker.is_of(part, "comment")):
                    counter["para_short"] = 0
                    continue

            if (part.parent_node.node_name == "sect" or
                    (part.parent_node.node_name == "text" and part.parent_node.indent)):
                node_cur = part.parent_node
            else:
                node_cur = None

            for key in counter:
                if key != "para_short":
                    counter[key] = 0

            if (node_cur and node_prev and
                    (node_cur.node_name == "sect" or
                     (rst_walker.is_of(node_cur.parent_node,
                                       {"def", "dir", "enum", "bullet", "field", "cell"}) and
                      node_cur.prev is None))):
                reports = compare(node_prev, sen_full, counter, reports, is_last=True)
                counter["para_short"] = 0
                node_prev = None
                sen_full = None

        if node_cur and part.child_nodes.is_empty():
            if part.code.end_pos <= node_cur.code.end_pos:
                if node_cur.node_name == "sect":
                    counter["sect"] += len(part.code)
                else:
                    for sen, stop in segmenter.iter_sentence(part.code):
                        for word in segmenter.iter_word(sen):
                            counter["sen"] += 1
                            if len(word) >= conf["word_len"]:
                                reports.append(
                                    Report('I', toolname, word,
                                           Report.quantity(what="long word",
                                               how="{0}/{1} letters".format(
                                                   len(word), conf["word_len"]))))

                        if not sen_full:
                            sen_full = sen
                        else:
                            sen_full = document.body.code.slice(
                                           sen_full.start_lincol, sen.end_lincol, True)

                        if stop:
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
        if not stop and sen_full and not sen_full.isspace():
            counter["para"] += 1
        reports = compare(node_cur, sen_full, counter, reports, is_last=True)

    return reports


def overuse_pre(toolname):
    config = dict()
    config.update(monostyle_io.get_override(__file__, toolname, "thresholds", (2.0, 3.1)))
    return {"config": config}


def overuse(toolname, document, reports, config):
    """Overuse of words. Filter with markup, subjects after an determiner,
    transitions at sentence start, the file path and stopwords.
    """
    thresholds = config["thresholds"]
    distance_min = 5
    distance_max = 80
    modifier_as_topic = True

    def add_topic(topics, word_str, words):
        topics.add(word_str)
        words.remove(word_str)

    def evaluate(document, reports, words):
        def add_report(document, reports, word, thresholds, score, count):
            reports.append(
                Report(Report.map_severity(thresholds, score), toolname, word,
                       Report.quantity(what="overused word",
                                       how=str(count) + " times " + str(score)))
                .set_line_punc(document.code, 50, 30))

            return reports

        for _, entry in words:
            value = entry["value"]
            if len(value) == 1:
                continue
            buf = None
            score = 0
            index_last = 0
            for index, instance in enumerate(value):
                if buf is None:
                    buf = instance
                distance = instance[2] - buf[2]
                if distance > distance_max:
                    if score >= thresholds[0]:
                        reports = add_report(document, reports, instance[0],
                                             thresholds, score, index - index_last + 1)
                    buf = None
                    score = 0
                    index_last = index
                else:
                    if distance == 0 or distance > distance_min:
                        score += instance[1] * (-(pow((1 / (distance_max - distance_min)) *
                                                      (distance - distance_min), 2)) + 1)
                    buf = instance

            if score >= thresholds[0]:
                reports = add_report(document, reports, instance[0], thresholds, score,
                                     index - index_last + 1)
        words.reset()
        return reports

    segmenter = Segmenter()
    part_of_speech = PartofSpeech()
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
            "kbd": "*", "math": "*"
        },
        "literal": "*", "standalone": "*"
    }
    topics = {'and', 'or'}
    for word in re.split(r"[/._-]", monostyle_io.path_to_rel(document.code.filename, 'doc')
                                                .replace(".rst", "")):
        topics.add(word)
    words = Lexicon()
    stopwords = {'to', 'of', 'in', 'as', 'on', 'by'}

    is_first = True
    was_determiner = False
    counter = -1
    word = None
    for part in rst_walker.iter_nodeparts_instr(document.body, instr_pos, instr_neg):
        is_title = False
        par_part = part.parent_node.parent_node
        while par_part and par_part.parent_node.node_name == "text":
            par_part = par_part.parent_node.parent_node

        if rst_walker.is_of(par_part, "sect"):
            reports = evaluate(document, reports, words)
            is_title = True
        elif (rst_walker.is_of(par_part, "dir", "rubric") or
                rst_walker.is_of(par_part, "def", "*", "head") or
                rst_walker.is_of(par_part, "field", "*", "name") or
                rst_walker.is_of(part, {"emphasis", "strong"}) or
                rst_walker.is_of(par_part, "role", {"term", "menuselection"})):
            is_title = True

        if not part.parent_node.prev:
            is_first = True
        if word:
            # add per average word length in skipped code
            counter += (part.code.start_pos - word.end_pos) // 6
        for sen, stop in segmenter.iter_sentence(part.code):
            for word in segmenter.iter_word(sen):
                counter += 1
                word_str = str(word).lower()
                tag = part_of_speech.tag(word_str)
                is_determiner = bool(tag and tag[0] == "determiner")

                if tag:
                    if is_determiner:
                        was_determiner = True
                        if not is_first:
                            continue
                    if not is_first:
                        if tag[0] in {"contraction", "auxiliary"}:
                            was_determiner = False
                            continue

                if not is_first and was_determiner:
                    if (is_determiner or (tag and tag[0] == "adjective") or
                            re.search(r"([^aeiou])\1er\Z", word_str) or word_str.endswith("ed")):
                        if modifier_as_topic and not is_determiner:
                            add_topic(topics, word_str, words)
                            is_first = False
                            continue
                    else:
                        was_determiner = False
                        if not tag or tag[0] == "noun":
                            add_topic(topics, word_str, words)
                            is_first = False
                            continue

                if is_title:
                    if not tag or not is_determiner:
                        add_topic(topics, word_str, words)
                    is_first = False
                    continue

                if is_first or word_str not in topics:
                    weight = 1
                    if not is_first and word_str in stopwords:
                        weight -= 0.6
                    else:
                        if not is_first:
                            weight -= 0.2
                        if not tag:
                            weight -= 0.1
                        elif tag[0] in {"noun", "verb", "participle", "pronoun"}:
                            weight -= 0.2

                    entry = words.add(word_str)
                    if "value" not in entry.keys():
                        entry["value"] = []
                    entry["value"].append((word, weight, counter))

                is_first = False

            if stop:
                is_first = True

        if not part.next and not part.parent_node.next:
            was_determiner = False

    reports = evaluate(document, reports, words)
    return reports


def passive_pre(_):
    re_lib = dict()

    re_lib["passive"] = (
        re.compile(''.join((r"(\b", r"\b|\b".join(("be", "being", "been", "am", "is",
                                                   "are", "was", "were")), r"\b|",
                            r"\bg[eo]t(?:s|ten)?\b)", # get
                            r"\s+", r"(\b[\w-]+e[dn]\b|\b",
                            r"\b|\b".join(monostyle_io.get_data_file("irregular_participle")),
                            r"\b)")), re.DOTALL),
        Report.existing(what="passive voice"))

    args = dict()
    args["re_lib"] = re_lib
    args["config"] = {"severity": 'I'}

    return args


def search_pure(toolname, document, reports, re_lib, config):
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
            "kbd": "*", "math": "*"
        },
        "literal": "*", "standalone": "*"
    }

    for part in rst_walker.iter_nodeparts_instr(document.body, instr_pos, instr_neg):
        for pattern, message in re_lib.values():
            part_str = str(part.code)
            for m in re.finditer(pattern, part_str):
                reports.append(
                    Report(config.get("severity"), toolname,
                           part.code.slice_match(m, 0, True), message)
                    .set_line_punc(document.body.code, 50, 30))

    return reports


def repeated_pre(toolname):
    # Number of the word within to run the detection.
    config = dict(monostyle_io.get_override(__file__, toolname, "buf_size", 3, (1, None)))
    return {"config": config}


def repeated(toolname, document, reports, config):
    """Find repeated words e.g. the the example."""
    def stemmer_patch(porter_stemmer, word_lower):
        """Distinguish some words."""
        # on vs. one
        if word_lower in {"one", "ones"}:
            return "one"
        # us vs. use
        if word_lower in {"use", "uses", "used"}:
            return "use"

        return porter_stemmer.stem(word_lower, 0, len(word_lower)-1)

    porter_stemmer = Porterstemmer()
    segmenter = Segmenter()
    buf_size = config["buf_size"]

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
            "kbd": "*", "menuselection": "*", "math": "*"
        },
        "literal": "*", "standalone": "*"
    }

    buf = []
    # config: min distance from where on to apply filter
    ignore_article = ({"a", "an", "the"}, 2)
    ignore_pre_pro = ({"and", "or", "to", "as", "of"}, 1)
    prev_parent = None

    for part in rst_walker.iter_nodeparts_instr(document.body, instr_pos, instr_neg, False):
        if part.child_nodes.is_empty():
            # add one placeholder word for skipped code
            if len(buf) != 0 and part.parent_node.prev is not prev_parent:
                if len(buf) == buf_size:
                    buf.pop(0)

                buf.append("")

            for sen, stop in segmenter.iter_sentence(part.code):
                for word in segmenter.iter_word(sen):
                    word_lower = str(word).lower()
                    word_stem = stemmer_patch(porter_stemmer, word_lower)

                    for distance, word_buf in enumerate(reversed(buf)):
                        if word_buf == word_stem:
                            if word_lower == "rst":
                                continue
                            if distance >= ignore_article[1] and word_stem in ignore_article[0]:
                                continue
                            if distance >= ignore_pre_pro[1] and word_stem in ignore_pre_pro[0]:
                                continue

                            reports.append(
                                Report('W' if distance == 0 else 'I', toolname, word,
                                       Report.quantity(what="repeated words",
                                                       how=str(distance) + " words in between"))
                                .set_line_punc(document.body.code, 50, 30))
                            break

                    if len(buf) == buf_size:
                        buf.pop(0)

                    buf.append(word_stem)

                if stop:
                    buf.clear()

            if rst_walker.is_of(part, "text") and part.parent_node.indent:
                buf.clear()

            prev_parent = part.parent_node

        else:
            if rst_walker.is_of(part, {"sect", "bullet", "enum", "line", "def", "field"}):
                buf.clear()

    return reports


OPS = (
    ("abbreviation", abbreviation, abbreviation_pre, True),
    ("article", article, article_pre),
    ("collocation", collocation, collocation_pre),
    ("grammar", search_pure, grammar_pre),
    ("hyphen", hyphen, hyphen_pre),
    ("metric", metric, None),
    ("overuse", overuse, overuse_pre),
    ("passive", search_pure, passive_pre),
    ("repeated", repeated, repeated_pre),
)


if __name__ == "__main__":
    from monostyle.__main__ import main_mod
    main_mod(__doc__, OPS, __file__)
