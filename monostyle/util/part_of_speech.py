
"""
util.part_of_speech
~~~~~~~~~~~~~~~~~~~

Data-driven part of speech tagging.
"""

import re
from monostyle.util.monostyle_io import get_data_file, get_branch
from monostyle.util.char_catalog import CharCatalog

class PartofSpeech:
    """Part of speech tagging."""

    def __new__(cls):
        if not hasattr(cls, '__loaded'):
            cls.__loaded = True
            char_catalog = CharCatalog()
            cls.data = get_data_file("part_of_speech")
            cls.remove_comments(cls, cls.data)

            # acronym
            pattern_str = (
                r"\b[", char_catalog.unicode_set("A-Z", 0, 7), r"]{2,}s?",
                # contraction
                r"(?:[", char_catalog.data["connector"]["apostrophe"], r"]",
                r"(?:", '|'.join(('ed', 's')), r"))?",
                r"(?:(?<=s)[", char_catalog.data["connector"]["apostrophe"], r"](?!\w)|\b)"
            )
            cls.acr_re = re.compile(''.join(pattern_str))

            # abbreviation
            cls.abbr_re = re.compile(r"\b([" + char_catalog.unicode_set("A-Za-z", 0, 7) +
                                     r"]\.){2,}(?:(?!\w)|\Z)")

        return super().__new__(cls)


    def __init__(self):
        self.prev = None


    def reset(self):
        """Empty buffer."""
        self.__init__()


    def remove_comments(cls, obj):
        """Remove commented out entries."""
        rem_keys = []
        for key, value in obj.items():
            if key.startswith("#"):
                rem_keys.append(key)
            elif isinstance(value, dict):
                cls.remove_comments(cls, value)

        for key in rem_keys:
            del obj[key]


    def get(self, branch, index=0, joined=False):
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

        obj = get_branch(self.data, branch, index)
        if not joined or isinstance(obj, (str, list)):
            return obj

        return list(value for value in iter_sub(obj))


    def tag(self, word):
        """Assign POS tag."""
        def search(obj, word):
            if not isinstance(obj, str):
                branch = []
                for key, value in obj.items():
                    if isinstance(value, dict):
                        result = search(value, word)
                        if result and len(result) != 0:
                            branch.append(key)
                            branch.extend(result)
                            return branch

                    elif isinstance(value, list):
                        if (key == "participle" and
                                (self.prev is None or len(self.prev) == 0 or
                                 self.prev[0] != "auxiliary")):
                            continue

                        is_suffix = bool(key == "_suffix")
                        for entry in value:
                            if ((is_suffix and word.endswith(entry)) or
                                    (not is_suffix and word == entry)):
                                if not key.startswith("_"):
                                    branch.append(key)
                                return branch

                return branch

        branch = search(self.data, word)
        self.prev = branch

        return branch


    def isacr(self, word):
        """The word is an acronym."""
        if acr_m := re.match(self.acr_re, str(word)):
            if acr_m.end() - acr_m.start() == len(word):
                return True
        return False


    def isabbr(self, word):
        """The word is an abbreviation."""
        if abbr_m := re.match(self.abbr_re, str(word)):
            if abbr_m.end() - abbr_m.start() == len(word):
                return True
        return False
