
"""
util.char_catalog
~~~~~~~~~~~~~~~~~

Unicode character categories.
"""

import re
from monostyle.util.monostyle_io import get_data_file, get_branch

class CharCatalog:
    """Unicode character categories."""

    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.data = get_data_file("char_catalog")
            cls.instance = super().__new__(cls)
        return cls.instance


    def get(self, branch, index=0, joined=True):
        """Return a data segment.
        joined -- join all subordinate leafs.
        """
        def iter_sub(obj):
            for value in obj.values():
                if not isinstance(value, str):
                    yield from iter_sub(value)
                else:
                    yield value

        obj = get_branch(self.data, branch, index)
        if not joined or isinstance(obj, str):
            return obj

        return "".join(iter_sub(obj))


    def tag(self, char):
        """Return the branch to the first leaf matching the char."""
        def search(obj, char):
            if not isinstance(obj, str):
                branch = []
                for key, value in obj.items():
                    if isinstance(value, dict):
                        result = search(value, char)
                        if result and len(result) != 0:
                            branch.append(key)
                            branch.extend(result)
                            return branch
                    else:
                        if len(value) == 0:
                            continue

                        if re.match(r"[" + value + r"]", char):
                            branch.append(key)
                            return branch

                return branch

        return search(self.data, char)


    def _block(self, value):
        """hex string or number."""
        if isinstance(value, str):
            return int(value, 16)
        return 128 * value


    def unicode_set(self, pattern_str, start_block, end_block, store=True):
        """Generate a regex set over a range of Unicode blocks selected by its ASCII version."""
        if len(self.unicode_set.storage) != 0:
            if (stored := self.unicode_set.storage.get(pattern_str + str(start_block) + "-" +
                                                       str(end_block))):
                return stored

        if pattern_str == "a-z":
            test_op = str.islower
        elif pattern_str == "A-Z":
            test_op = str.isupper
        elif pattern_str in {"A-Za-z", "a-zA-Z"}:
            test_op = str.isalpha
        elif pattern_str in {"A-Za-z0-9", "a-z0-9A-Z", "0-9A-Za-z"}:
            test_op = str.isalnum
        else:
            print("char_catalog.py unicode range: unknown pattern", pattern_str)
            return pattern_str

        regions = []
        for i in range(self._block(start_block), self._block(end_block)):
            char = chr(i)
            if test_op(char):
                regions.append(char)

        regions = self.contract(regions)
        # Memoize pattern
        if store:
            self.unicode_set.storage[pattern_str + str(start_block) + "-" +
                                     str(end_block)] = regions
        return regions

    unicode_set.storage = {}



    def contract(self, chars, apply_escape=True):
        """Shorten a list of chars into dash ranges."""
        return self.stringify(self.join(chars), apply_escape)


    def stringify(self, regions, apply_escape=True):
        """Join a mixed list of single chars and tuple for ranges."""
        pattern = []
        for entry in regions:
            if isinstance(entry, tuple):
                if apply_escape:
                    for entry_range in entry:
                        if entry_range.endswith('-') and not entry_range.startswith('\\'):
                            entry_range = '\\' + entry_range
                pattern.append(entry[0] + '-' + entry[1])
            else:
                pattern.append(entry)

        return ''.join(pattern)


    def join(self, chars):
        """Find ranges and store them as tuples."""
        regions = []
        buf = None
        last = ""
        was_esc = False
        was_adjoin = False
        for char in chars:
            if was_esc:
                char = '\\' + char
                was_esc = False
            elif char == '\\':
                was_esc = True
                continue

            if buf is not None:
                if ord(char[-1]) - ord(last[-1]) == 1:
                    was_adjoin = True
                else:
                    if was_adjoin:
                        regions.append((buf, last))
                        buf = char
                        was_adjoin = False
                    else:
                        regions.append(buf)
                        buf = char
            else:
                buf = char
            last = char

        if buf is not None:
            if was_adjoin:
                regions.append((buf, char))
            else:
                regions.append(char)

        return regions


    def expand(self, pattern_str):
        """Expand a shorten set into a char list."""
        chars = []
        for entry in self.split(pattern_str):
            if isinstance(entry, tuple):
                for range_char in range(ord(entry[0][-1]), ord(entry[1][-1]) + 1):
                    chars.append(chr(range_char))
            else:
                chars.append(entry)

        return chars


    def split(self, pattern_str):
        """Parse the pattern for dashes and store them as tuples."""
        regions = []
        was_esc = False
        was_dash = False
        buf = None
        for char in pattern_str:
            if was_esc:
                char = '\\' + char
                was_esc = False
            elif char == "\\":
                was_esc = True
                continue

            if buf is not None:
                if was_dash:
                    regions.append((buf, char))
                    was_dash = False
                    buf = None
                elif char == "-":
                    was_dash = True
                else:
                    regions.append(buf)
                    buf = char
            else:
                buf = char

        if buf is not None:
            regions.append(buf)
            if was_dash:
                regions.append(char)

        return regions
