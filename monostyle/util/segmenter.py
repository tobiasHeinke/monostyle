
"""
util.segmenter
~~~~~~~~~~~~~~

Text segmentation.
"""

import re
from monostyle.util.char_catalog import CharCatalog
from monostyle.util.pos import PartofSpeech

class Segmenter:

    def __init__(self):
        CC = CharCatalog()
        pos = PartofSpeech()
        # paragraph
        # self.para_re = re.compile(r"(?:\n|\r\n?)(?:\n|\r\n?)+?", re.MULTILINE)
        self.para_re = re.compile(r"\A\s+\Z")

        # sentence
        pattern_str = r"([\w\.]+)?(?<!\.\.)([" + CC.data["terminal"]["final"] + r"])([\W\D]|\Z)"
        self.sent_re = re.compile(pattern_str)

        self.linewrap_re = re.compile(r" *?\n *", re.MULTILINE)

        # clause
        self.clause_re = re.compile(r",(?:\s|\Z)")

        # parenthesis
        self.parenthesis_re = re.compile(r"\([^)]+?(\).?\s*|\Z)")

        # word
        hypen = CC.data["connector"]["hyphen"]
        apostrophe = CC.data["connector"]["apostrophe"]
        # abbreviation
        pattern_str = (
            r"(\b(?:(?:[", CC.unicode_set("A-Za-z", 0, 7), r"]\.){2,})|",
            # compound: dash with letters on both sides and
            # one at start and end (for pre-/suffixes).
            r"(?:[", hypen, r"]|\b)[", CC.unicode_set("A-Za-z", 0, 7), r"](?:\w*",
            # contraction: with letters on both sides and after s at word end.
            r"(?<=\w)[", apostrophe, hypen, r"]?(?=\w)\w*)*",
            r"(?:(?<=s)[" + apostrophe + r"](?!\w)|\b)",
            r"[", hypen, r"]?)"
        )

        self.word_re = re.compile(''.join(pattern_str))
        # word only
        self.wordsub_re = re.compile(r"\b(\w+?)\b")
        self.numbersub_re = re.compile(r"\A\d+\Z")

        # number
        pattern_str = (
            r"(?:(?<=[\W\D])|\A)",
            r"[", CC.data["math"]["operator"]["sign"], r"]?\d(?:\d|[,.]\d)*",
            r"(?:(?=\D)|\Z)"
        )
        self.number_re = re.compile(''.join(pattern_str))

        self.abbr_re = pos.abbr_re
        self.abbrs = self._join_abbr_data(pos.get(("abbreviation",)))


    def _join_abbr_data(self, data):
        abbrs = []
        for val in data.values():
            for ent in val:
                if not re.match(self.abbr_re, ent):
                    abbrs.append(ent)
        return abbrs


    # -----------------


    def iter_paragraph(self, fg):
        para_re = self.para_re
        buf_start = fg.start_lincol
        on_break = False

        for line in fg.splitlines():
            if re.match(para_re, str(line)):
                on_break = True
            else:
                if on_break:
                    yield fg.slice(buf_start, line.start_lincol, True)
                    buf_start = line.start_lincol

                on_break = False

        yield fg.slice(buf_start, right_inner=True)


    def iter_sentence(self, fg, crop_start=False, crop_end=False, output_openess=False):
        buf_start = 0
        sent_re = self.sent_re
        text = str(fg)
        for sent_m in re.finditer(sent_re, text):
            if (sent_m.group(2) == "." and
                    sent_m.group(1) is not None and
                    (re.match(self.abbr_re, sent_m.group(1)) or
                     sent_m.group(1) in self.abbrs)):
                continue

            if crop_start and buf_start == 0:
                buf_start = sent_m.end(0)
                continue

            sent_fg = fg.slice(buf_start + fg.start_pos, sent_m.end(0) + fg.start_pos, True)
            if not output_openess:
                yield sent_fg
            else:
                yield sent_fg, False

            buf_start = sent_m.end(0)

        if not crop_end and buf_start != len(text):
            sent_fg = fg.slice(buf_start + fg.start_pos, right_inner=True)
            if not output_openess:
                yield sent_fg
            else:
                yield sent_fg, True


    def iter_clause(self, fg):
        # todo detect oxford comma, etc, ellipsis, and/or, sentence start/end
        clause_re = self.clause_re

        # config: serial comma skip when less spaces
        threshold = 3 + 2
        buf_start = 0
        buf = None
        text = str(fg)
        for clause_m in re.finditer(clause_re, text):
            c = fg.slice(buf_start +  fg.start_pos, clause_m.end(0) +  fg.start_pos, True)
            space_count = 0
            for line in c:
                space_count += line.count(" ")
            if space_count > threshold:
                if buf is not None:
                    yield buf
                    buf = None
                yield c
            else:
                if buf is None:
                    buf = c
                else:
                    buf.combine(c)

            buf_start = clause_m.end(0)

        if buf_start != len(text):
            c = fg.slice(buf_start +  fg.start_pos, right_inner=True)
            space_count = 0
            for line in c:
                space_count += line.count(" ")
            if space_count > threshold:
                if buf is not None:
                    yield buf
                yield c
            else:
                if buf is None:
                    buf = c
                else:
                    buf.combine(c)
                yield buf


    def iter_parenthesis(self, fg):
        # config: skip when less spaces
        text = str(fg)
        threshold = 3 + 1
        buf_start = 0

        pare_re = self.parenthesis_re
        for pare_m in re.finditer(pare_re, text):
            if pare_m.group(0).count(" ") > threshold:
                if buf_start != pare_m.start(0):
                    yield fg.slice(buf_start + fg.start_pos, pare_m.start(0) + fg.start_pos, True)
                yield fg.slice_match_obj(pare_m, 0, True)
                buf_start = pare_m.end(0)

        if buf_start != len(text):
            yield fg.slice(buf_start + fg.start_pos, right_inner=True)


    def iter_word(self, fg):
        word_re = self.word_re
        fg_str = str(fg)
        for word_m in re.finditer(word_re, fg_str):
            yield fg.slice_match_obj(word_m, 1, True)


    def iter_wordsub(self, fg, filter_numbers=True):
        wordsub_re = self.wordsub_re
        nbrsub_re = self.numbersub_re
        fg_str = str(fg)
        for wordsub_m in re.finditer(wordsub_re, fg_str):
            if not filter_numbers or not re.match(nbrsub_re, wordsub_m.group(0)):
                yield fg.slice_match_obj(wordsub_m, 0, True)


    def iter_number(self, fg):
        number_re = self.number_re
        fg_str = str(fg)
        for number_m in re.finditer(number_re, fg_str):
            yield fg.slice_match_obj(number_m, 0, True)
