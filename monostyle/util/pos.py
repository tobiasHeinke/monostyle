
"""
util.pos
~~~~~~~~

Data-driven part of speech classification.
"""

import re
from monostyle.util.monostylestd import get_data_file, get_branch
from monostyle.util.char_catalog import CharCatalog

class PartofSpeech:
    """Part of speech classification."""

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


    def get(self, path, index=0):
        return get_branch(self.data, path, index)


    def classify(self, word):
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

                        for ent in value:
                            if ((re.match(r"\-", ent) and re.search(ent[1:] + r"$", word)) or
                                    word == ent):
                                path.append(key)
                                return path

                return path

        path = search(self.data, word)
        self.prev = path

        return path


    def isacr(self, word):
        return bool(re.match(self.acr_re, str(word)))


    def isabbr(self, word):
        return bool(re.match(self.abbr_re, str(word)))
