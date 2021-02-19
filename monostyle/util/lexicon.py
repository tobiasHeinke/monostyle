
"""
util.lexicon
~~~~~~~~

List of words.
"""
import re
import csv
from difflib import SequenceMatcher

import monostyle.util.monostyle_io as monostyle_io
from monostyle.util.pos import PartofSpeech
from monostyle.util.char_catalog import CharCatalog

class Lexicon:
    """List of words."""

    __default__ = {}

    def __new__(cls, blank=True):
        if not blank and not cls.__default__:
            lexicon_flat = cls.read_csv(cls)
            if lexicon_flat:
                cls.__default__ = cls.split(cls, cls.add_charset(cls, lexicon_flat))

        if not hasattr(cls, 'inited'):
            char_catalog = CharCatalog()
            cls.hyphen_re = re.compile(r"[" + char_catalog.data["connector"]["hyphen"] + r"]")
            cls.apostrophe_re = re.compile(r"[" + char_catalog.data["connector"]["apostrophe"] + r"]")
            cls.part_of_speech = PartofSpeech()
            cls.inited = True

        return super().__new__(cls)


    def __init__(self, blank=True):
        if blank:
            self.data = dict()
        else:
            self.data = self.__default__


    def __bool__(self):
        """Has data."""
        return bool(self.data)


    def read_csv(self):
        lexicon_flat = []
        lex_filename = monostyle_io.path_to_abs("monostyle/lexicon.csv")
        try:
            with open(lex_filename, newline='', encoding='utf-8') as csvfile:
                csv_reader = csv.reader(csvfile)

                for row in csv_reader:
                    lexicon_flat.append(row)
            return lexicon_flat

        except IOError:
            print("lexicon not found")
            return None


    def write_csv(self):
        lex_filename = monostyle_io.path_to_abs("monostyle/lexicon.csv")
        count = 0
        try:
            with open(lex_filename, 'w', newline='', encoding='utf-8') as csvfile:
                csv_writer = csv.writer(csvfile)
                for entry in self.join():
                    csv_writer.writerow(entry)
                    count += 1

                print("wrote lexicon file with {0} words".format(count))

        except (IOError, OSError) as err:
            print("{0}: cannot write: {1}".format(lex_filename, err))


    def split(self, lexicon_flat):
        """Split lexicon by first char."""
        lexicon = dict()
        for entry in lexicon_flat:
            first_char = entry[0][0]
            if first_char not in lexicon.keys():
                lexicon.setdefault(first_char, [])
            lexicon[first_char].append(entry)

        return lexicon


    def join(self, do_sort=False):
        """Join lexicon to a list."""
        lexicon_flat = []
        for value in self.data.values():
            lexicon_flat.extend(value)

        if do_sort:
            # Sort list by highest occurrence.
            lexicon_flat.sort(key=lambda word: word[1], reverse=True)

        return lexicon_flat


    def add_charset(self, lexicon):
        for entry in lexicon:
            entry.append(set(ord(c) for c in entry[0].lower()))
        return lexicon


    def __iter__(self):
        for leaf in self.data.values():
            for entry in leaf:
                yield entry


    def iter_leaf(self, first_char):
        if first_char in self.data.keys():
            for entry in self.data[first_char]:
                yield entry


    def add(self, word_str):
        """Adds a word to the lexicon."""
        word_str = self.norm_punc(word_str)
        word_str = self.norm_case(word_str)
        first_char = word_str[0].lower()
        # tree with leafs for each first char.
        if first_char not in self.data.keys():
            self.data.setdefault(first_char, [])

        for entry in self.iter_leaf(first_char):
            if entry[0] == word_str:
                entry[1] += 1
                break
        else:
            new_word = [word_str, 0]
            self.data[first_char].append(new_word)


    def find(self, word_str):
        """Adds a word to the lexicon."""
        for entry in self.iter_leaf(word_str[0]):
            if word_str == str(entry[0]):
                return entry


    def find_similar(self, word_normed, word_str, count, sim_threshold):
        """Find similar words with adaptive filtering."""
        def iter_lexicon(word_str):
            first_char = word_str[0]
            if first_char in self.data.keys():
                value = self.data[first_char]
                yield from reversed(value)
            for key, value in self.data.items():
                if key != first_char:
                    yield from reversed(value)

        similars = []
        word_chars = set(ord(c) for c in word_str)
        for stored_word, _, stored_chars in iter_lexicon(word_str):
            len_deviation = abs(len(word_str) - len(stored_word)) / len(word_str)
            if len_deviation >= 2:
                continue
            sim_rough = len(word_chars.intersection(stored_chars)) / len(word_chars) - len_deviation
            is_not_full = bool(len(similars) < count)
            if is_not_full or sim_rough >= min_rough:
                matcher = SequenceMatcher(None, word_str, stored_word)
                sim_quick = matcher.quick_ratio()
                if is_not_full or sim_quick >= min_quick:
                    sim_slow = matcher.ratio()
                    if sim_slow == 1 and word_str == stored_word:
                        continue
                    if is_not_full:
                        similars.append((stored_word, sim_slow, sim_quick, sim_rough))
                    else:
                        min_value = None
                        min_index = 0
                        for index, entry in enumerate(similars):
                            if min_value is None or entry[1] <= min_value:
                                min_index = index
                                min_value = entry[1]

                        similars[min_index] = (stored_word, sim_slow, sim_quick, sim_rough)

                    min_quick = min(s[2] for s in similars)
                    min_rough = min(s[3] for s in similars)

        similars.sort(key=lambda key: key[1], reverse=True)
        return tuple(self.lower_first_reverse(entry[0], word_normed) for entry in similars
                     if entry[1] >= sim_threshold)


    def compare(self, other):
        """Show a difference the other lexicon."""
        data = set(entry[0] for entry in self)
        other = set(entry[0] for entry in other)

        return (tuple(sorted(other.difference(data))),
                    tuple(sorted(data.difference(other))))


    #------------------------


    def norm_punc(self, word_str):
        """Normalize the word's punctuation."""
        word_str = re.sub(self.hyphen_re, '-', word_str)
        word_str = re.sub(self.apostrophe_re, '\'', word_str)
        return word_str


    def norm_case(self, word_str):
        """Normalize the word's caps."""
        if not self.part_of_speech.isacr(word_str) and not self.part_of_speech.isabbr(word_str):
            word_str = self.lower_first(word_str)
        return word_str


    def lower_first(self, word_str):
        """Lower case of first char in hyphened compound."""
        new_word = []
        for compound in word_str.split('-'):
            if len(compound) != 0:
                new_word.append(compound[0].lower() + compound[1:])
            else:
                new_word.append(compound)

        return '-'.join(new_word)


    def lower_first_reverse(self, word_str, ref):
        """Upper case of first char in hyphened compound based on a reference word."""
        new_word = []
        word_spit = word_str.split('-')
        ref_split = ref.split('-')
        for compound_word, compound_ref in zip(word_spit, ref_split):
            if (len(compound_word) != 0 and len(compound_ref) != 0 and
                    compound_ref[0].isupper()):
                new_word.append(compound_word[0].upper() + compound_word[1:])
            else:
                new_word.append(compound_word)

        if len(word_spit) > len(ref_split):
            new_word.extend(word_spit[len(ref_split):])

        return '-'.join(new_word)
