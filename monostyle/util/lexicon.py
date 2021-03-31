
"""
util.lexicon
~~~~~~~~

List of words.
"""

import re
import csv
from difflib import get_close_matches

import monostyle.util.monostyle_io as monostyle_io
from monostyle.util.part_of_speech import PartofSpeech
from monostyle.util.char_catalog import CharCatalog

class Lexicon:
    """List of words."""

    __default__ = {}

    def __new__(cls, blank=True):
        if not blank and not cls.__default__:
            lexicon_flat = cls.read_csv(cls)
            if lexicon_flat:
                cls.__default__ = cls.add_charset(cls, cls.split(cls, lexicon_flat))

        if not hasattr(cls, '__loaded'):
            cls.__loaded = True
            char_catalog = CharCatalog()
            cls.hyphen_re = re.compile(r"[" + char_catalog.data["connector"]["hyphen"] + r"]")
            cls.apostrophe_re = re.compile(r"[" + char_catalog.data["connector"]["apostrophe"] + r"]")
            cls.part_of_speech = PartofSpeech()

        return super().__new__(cls)


    def __init__(self, blank=True):
        if blank:
            self.data = dict()
        else:
            self.data = self.__default__.copy()


    def __bool__(self):
        """Has data."""
        return bool(self.data)


    def __len__(self):
        """Number of words."""
        return sum(len(section) for section in self.data.values())


    def reset(self):
        """Clear data."""
        self.data.clear()


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


    def split(self, lexicon_flat):
        """Split lexicon by first char."""
        lexicon = dict()
        for entry in lexicon_flat:
            word = entry[0]
            if len(word) == 0:
                continue
            first_char = word[0].lower()
            if first_char not in lexicon.keys():
                lexicon.setdefault(first_char, dict())
            lexicon[first_char][word] = {"_counter": entry[1]}

        return lexicon


    def join(self, do_sort=False):
        """Join lexicon to a list."""
        lexicon_flat = []
        for section in self.data.values():
            for word, entry in section.items():
                lexicon_flat.append((word, entry["_counter"]))

        if do_sort:
            # Sort list by highest occurrence.
            lexicon_flat.sort(key=lambda word: word[1],
                              reverse=True)

        return lexicon_flat


    def add_charset(self, lexicon_split):
        for section in lexicon_split.values():
            for word, entry in section.items():
                entry["_charset"] = set(ord(c) for c in word.lower())
        return lexicon_split


    def __iter__(self):
        for section in self.data.values():
            yield from section.items()


    def iter_section(self, first_char):
        if len(first_char) == 0:
            return
        first_char = first_char.lower()
        if first_char in self.data.keys():
            yield from self.data[first_char].items()


    def add(self, word_str, do_norm=True):
        """Adds a word to the lexicon."""
        if len(word_str) == 0:
            return
        if do_norm:
            word_str = self.norm_punc(word_str)
            word_str = self.norm_case(word_str)
        first_char = word_str[0].lower()
        # tree with sections for each first char.
        if first_char not in self.data.keys():
            self.data.setdefault(first_char, dict())

        if entry := self.find(word_str):
            entry["_counter"] += 1
        else:
            entry = {"_counter": 0}
            self.data[first_char][word_str] = entry
        return entry


    def remove(self, word_str):
        """Removes a word from the lexicon."""
        if len(word_str) == 0:
            return
        first_char = word_str[0].lower()
        if first_char not in self.data.keys():
            return
        section = self.data[first_char]
        if word_str not in section:
            return
        del section[word_str]
        if len(section) == 0:
            del self.data[first_char]


    def find(self, word_str, do_norm=True):
        """Find exact word in lexicon."""
        if len(word_str) == 0:
            return
        first_char = word_str[0].lower()
        if first_char in self.data.keys():
            if do_norm:
                word_str = self.norm_punc(word_str)
                word_str = self.norm_case(word_str)
            if word_str in self.data[first_char].keys():
                return self.data[first_char][word_str]


    def find_similar(self, word_normed, word_str, count, sim_threshold, lexicon_words=None):
        if not lexicon_words:
            lexicon_words = list(entry[0] for entry in self.join())
        return tuple(self.lower_first_reverse(entry, word_str)
                     for entry in get_close_matches(word_normed, lexicon_words,
                                                    n=count, cutoff=sim_threshold)), lexicon_words


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
