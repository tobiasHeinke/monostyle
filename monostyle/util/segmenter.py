
"""
util.segmenter
~~~~~~~~~~~~~~

Text segmentation and tokenization.
"""

import re
from monostyle.util.char_catalog import CharCatalog
from monostyle.util.part_of_speech import PartofSpeech

class Segmenter:
    """Text segmentation and tokenization."""

    def __new__(cls):
        if not hasattr(cls, 'instance'):
            char_catalog = CharCatalog()
            part_of_speech = PartofSpeech()
            # paragraph
            cls.para_re = re.compile(r"\n\s*\n", re.MULTILINE)

            # sentence
            pattern_str = (r"([\w\.]+)?(?<!\.\.)([", char_catalog.data["terminal"]["final"],
                           r"])([\W\D]|\Z)")
            cls.sent_re = re.compile("".join(pattern_str))

            cls.linewrap_re = re.compile(r" *?\n *", re.MULTILINE)

            # clause
            cls.clause_re = re.compile(r"(,(?:\s+|\Z)(?!(?:and|or)))|(\s(?:and|or)\s)")
            cls.non_oxford_re = re.compile(r"")
            cls.ellipsis_re = re.compile(r"\b(etc\.|\.\.\.)\s*\Z")

            # parenthesis
            cls.parenthesis_re = re.compile(r"\([^)]+?(\).?\s*|\Z)")

            # word
            hyphen = char_catalog.data["connector"]["hyphen"]
            apostrophe = char_catalog.data["connector"]["apostrophe"]
            pattern_str = (
                # abbreviation
                r"(\b(?:(?:[", char_catalog.unicode_set("A-Za-z", 0, 7), r"]\.){2,})|",
                # compound: dash with letters on both sides and
                # one at start and end (for pre-/suffixes).
                r"(?:[", hyphen, r"]|\b)",
                r"[", char_catalog.unicode_set("A-Za-z0-9", 0, 7), r"](?:\w*",
                # contraction: with letters on both sides and after s at word end.
                r"(?<=\w)[", apostrophe, hyphen, r"]?(?=\w)\w*)*",
                r"(?:(?<=s)[", apostrophe, r"](?!\w)|\b)",
                r"[", hyphen, r"]?)"
            )

            cls.word_re = re.compile(''.join(pattern_str))
            # word only
            cls.wordsub_re = re.compile(r"\b(\w+?)\b")
            # numbers, ranges and units
            pattern_str = (r"\A[+-]?\d[\d,.", hyphen, r"]*",
                           r"(?:[", apostrophe, r"]?(?<![", hyphen, r"])\w+)?\Z")
            cls.number_filter_re = re.compile(''.join(pattern_str))

            # number
            pattern_str = (
                r"(?:(?<=[\W\D])|\A)",
                r"[", char_catalog.data["math"]["operator"]["sign"], r"]?\d(?:\d|[,.]\d)*",
                r"(?:(?=\D)|\Z)"
            )
            cls.number_re = re.compile(''.join(pattern_str))

            cls.abbr_re = part_of_speech.abbr_re
            cls.abbrs = []
            for entry in part_of_speech.get(("abbreviation",), joined=True):
                if not re.match(cls.abbr_re, entry):
                    cls.abbrs.append(entry)

            cls.instance = super().__new__(cls)
        return cls.instance


    def iter_paragraph(self, source):
        buf_start = 0
        para_re = self.para_re
        text = str(source)
        for para_m in re.finditer(para_re, text):
            yield (source.slice(source.loc_to_abs(buf_start),
                                source.loc_to_abs(para_m.end(0))),
                   source.slice_match(para_m, 0))
            buf_start = para_m.end(0)

        if source.loc_to_abs(buf_start) != source.end_pos:
            yield source.slice(source.loc_to_abs(buf_start)), None


    def iter_sentence(self, source, crop_start=False, crop_end=False):
        buf_start = 0
        sent_re = self.sent_re
        text = str(source)
        for sent_m in re.finditer(sent_re, text):
            if (sent_m.group(2) == "." and
                    sent_m.group(1) is not None and
                    (re.match(self.abbr_re, sent_m.group(1)) or
                     sent_m.group(1) in self.abbrs)):
                continue

            if crop_start and buf_start == 0:
                buf_start = sent_m.end(0)
                continue

            yield (source.slice(source.loc_to_abs(buf_start),
                                source.loc_to_abs(sent_m.end(0))),
                   source.slice_match(sent_m, 2))

            buf_start = sent_m.end(0)

        if not crop_end and buf_start != len(text):
            yield source.slice(source.loc_to_abs(buf_start)), None


    def iter_clause(self, source):
        # config: serial comma skip when less spaces
        threshold = 3

        def do_not_skip(source, clause_source, is_non_oxford, is_buffered, was_non_oxford):
            if is_non_oxford and is_buffered:
                return False
            if was_non_oxford:
                return True
            clause_str = str(clause_source)
            if re.match(r"\s*however,", clause_str):
                return False
            space_count = sum(1 for s in re.finditer(r"\S\s", clause_str)) -1
            if space_count <= threshold:
                if (source.start_pos != clause_source.start_pos and
                        source.end_pos != clause_source.end_pos):
                    return False
            if re.search(self.ellipsis_re, clause_str):
                return False
            return True

        clause_re = self.clause_re

        buf_start = 0
        buf = None
        text = str(source)
        was_non_oxford = False
        for clause_m in re.finditer(clause_re, text):
            clause_source = source.slice(source.loc_to_abs(buf_start),
                                         source.loc_to_abs(clause_m.end(0)))
            if do_not_skip(source, clause_source, bool(clause_m.group(2)),
                           bool(buf), was_non_oxford):
                if buf is not None:
                    yield buf
                    buf = None
                yield clause_source
            else:
                if buf is None:
                    buf = clause_source
                else:
                    buf.combine(clause_source)

            buf_start = clause_m.end(0)
            was_non_oxford = clause_m.group(2)

        if buf_start != len(text):
            clause_source = source.slice(source.loc_to_abs(buf_start))
            if do_not_skip(source, clause_source, False, bool(buf), was_non_oxford):
                if buf is not None:
                    yield buf
                yield clause_source
            else:
                if buf is None:
                    buf = clause_source
                else:
                    buf.combine(clause_source)
                yield buf


    def iter_parenthesis(self, source):
        # config: skip when less spaces
        text = str(source)
        threshold = 3
        buf_start = 0

        pare_re = self.parenthesis_re
        for pare_m in re.finditer(pare_re, text):
            space_count = sum(1 for s in re.finditer(r"\S\s", pare_m.group(0))) - 1
            if space_count > threshold:
                if buf_start != pare_m.start(0):
                    yield source.slice(source.loc_to_abs(buf_start),
                                       source.loc_to_abs(pare_m.start(0)))
                yield source.slice_match(pare_m, 0)
                buf_start = pare_m.end(0)

        if buf_start != len(text):
            yield source.slice(source.loc_to_abs(buf_start))


    def iter_word(self, source, filter_numbers=True):
        word_re = self.word_re
        number_filter_re = self.number_filter_re
        text = str(source)
        for word_m in re.finditer(word_re, text):
            if not filter_numbers or not re.match(number_filter_re, word_m.group(0)):
                yield source.slice_match(word_m, 1)


    def iter_wordsub(self, source, filter_numbers=True):
        wordsub_re = self.wordsub_re
        number_filter_re = self.number_filter_re
        text = str(source)
        for wordsub_m in re.finditer(wordsub_re, text):
            if not filter_numbers or not re.match(number_filter_re, wordsub_m.group(0)):
                yield source.slice_match(wordsub_m, 0)


    def iter_number(self, source):
        number_re = self.number_re
        text = str(source)
        for number_m in re.finditer(number_re, text):
            yield source.slice_match(number_m, 0)
