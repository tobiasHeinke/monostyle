
"""
util.pos
~~~~~~~~

Data-driven part of speech tagging.
"""

import re
from monostyle.util.monostylestd import get_data_file, get_branch
from monostyle.util.char_catalog import CharCatalog

class PartofSpeech:
    """Part of speech tagging."""

    def __init__(self):
        CC = CharCatalog()
        self.data = get_data_file("pos")
        self.remove_comments(self.data)
        self.prev = None

        # acronym
        pattern_str = (
            r"\b[", CC.unicode_set("A-Z", 0, 7), r"]{2,}s?",
            # contraction
            r"(?:[", CC.data["connector"]["apostrophe"], r"]",
            r"(?:", '|'.join(('ed', 's')), r"))?",
            r"(?:(?<=s)[", CC.data["connector"]["apostrophe"], r"](?!\w)|\b)"
        )
        self.acr_re = re.compile(''.join(pattern_str))

        # abbreviation
        pattern_str = r"\b([" + CC.unicode_set("A-Za-z", 0, 7) + r"]\.){2,}(?:(?!\w)|\Z)"
        self.abbr_re = re.compile(pattern_str)


    def clear(self):
        """Empty buffer."""
        self.prev = None


    def remove_comments(self, obj):
        rem_keys = []
        for key, value in obj.items():
            if key.startswith("#"):
                rem_keys.append(key)
            elif isinstance(value, dict):
                self.remove_comments(value)

        for key in rem_keys:
            del obj[key]


    def get(self, path, index=0, joined=False):
        """
        joined -- join all subordinate leafs.
        """
        def iter_sub(obj):
            if isinstance(obj, dict):
                for value in obj.values():
                    if not isinstance(value, str):
                        yield from iter_sub(value)
                    else:
                        yield value
            else:
                for entry in obj:
                    yield entry

        obj = get_branch(self.data, path, index)
        if not joined or isinstance(obj, str) or isinstance(obj, list):
            return obj

        return list(value for value in iter_sub(obj))


    def tag(self, word):
        def search(obj, word):
            if not isinstance(obj, str):
                path = []
                for key, value in obj.items():
                    if isinstance(value, dict):
                        result = search(value, word)
                        if result and len(result) != 0:
                            path.append(key)
                            path.extend(result)
                            return path

                    elif isinstance(value, list):
                        if (key == "participle" and
                                (self.prev is None or len(self.prev) == 0 or
                                 self.prev[0] != "auxiliary")):
                            continue

                        for entry in value:
                            if ((re.match(r"\-", entry) and re.search(entry[1:] + r"$", word)) or
                                    word == entry):
                                path.append(key)
                                return path

                return path

        path = search(self.data, word)
        self.prev = path

        return path


    def isacr(self, word):
        if acr_m := re.match(self.acr_re, str(word)):
            if acr_m.end() - acr_m.start() == len(word):
                return True
        return False


    def isabbr(self, word):
        if abbr_m := re.match(self.abbr_re, str(word)):
            if abbr_m.end() - abbr_m.start() == len(word):
                return True
        return False
