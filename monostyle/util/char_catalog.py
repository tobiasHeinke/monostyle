
"""
util.char_catalog
~~~~~~~~~~~~~~~~~

Unicode character categories.
"""

import re
from monostyle.util.monostylestd import get_data_file, get_branch

class CharCatalog:
    """Unicode character categories."""

    def __init__(self):
        self.data = get_data_file("char_catalog")


    def get(self, path, index=0, joined=True):
        """Return a data segment.
        joined -- join all subordinary leafs.
        """
        def iter_sub(obj):
            for value in obj.values():
                if not isinstance(value, str):
                    yield from iter_sub(value)
                else:
                    yield value

        obj = get_branch(self.data, path, index)
        if not joined or isinstance(obj, str):
            return obj

        return "".join(list(value for value in iter_sub(obj)))


    def tag(self, char):
        """Return the branch to the first leaf matching the char."""
        def search(obj, char):
            if not isinstance(obj, str):
                path = []
                for key, value in obj.items():
                    if isinstance(value, dict):
                        result = search(value, char)
                        if result and len(result) != 0:
                            path.append(key)
                            path.extend(result)
                            return path
                    else:
                        if len(value) == 0:
                            continue

                        if re.match(r"[" + value + r"]", char):
                            path.append(key)
                            return path

                return path

        return search(self.data, char)


    def _block(self, value):
        """hex string or number."""
        if isinstance(value, str):
            return int(value, 16)
        return 128 * value


    def unicode_set(self, pattern_str, start_block, end_block, store=True):
        """Generate a regex set over a range of Unicode blocks selected by its ASCII version."""
        def alnum(c):
            return c.isalnum()

        def alpha(c):
            return c.isalpha()

        def up(c):
            return c.isupper()

        def low(c):
            return c.islower()

        if len(self.unicode_set.storage) != 0:
            if (us := self.unicode_set.storage.get(pattern_str + str(start_block) + "-" +
                                                   str(end_block))):
                return us
        if pattern_str == "a-z":
            test_op = low
        elif pattern_str == "A-Z":
            test_op = up
        elif pattern_str in ("A-Za-z", "a-zA-Z"):
            test_op = alpha
        elif pattern_str in ("A-Za-z0-9", "a-z0-9A-Z", "0-9A-Za-z"):
            test_op = alnum
        else:
            print("char_catalog.py unicode range: unknown pattern", pattern_str)
            return pattern_str

        region = []
        for i in range(self._block(start_block), self._block(end_block)):
            c = chr(i)
            if test_op(c):
                region.append(c)

        region = self.contract(region)
        if store:
            self.unicode_set.storage[pattern_str + str(start_block) + "-" +
                                     str(end_block)] = region
        return region

    unicode_set.storage = {}



    def contract(self, chars, apply_escape=True):
        """Shorten a list of chars into dash ranges."""
        return self.stringify(self.join(chars), apply_escape)


    def stringify(self, chars, apply_escape=True):
        """Join a mixed list of single chars and tuble for ranges."""
        region = []
        for entry in chars:
            if isinstance(entry, tuple):
                if apply_escape:
                    for entry_range in entry:
                        if entry_range.endswith('-') and not entry_range.startswith('\\'):
                            entry_range = '\\' + entry_range
                region.append(entry[0] + '-' + entry[1])
            else:
                region.append(entry)

        return ''.join(region)


    def join(self, chars):
        """Find ranges and store them as tubles."""
        region = []
        buf = None
        last = ""
        was_esc = False
        was_adjoin = False
        for c in chars:
            if was_esc:
                c = '\\' + c
                was_esc = False
            elif c == '\\':
                was_esc = True
                continue

            if buf is not None:
                if ord(c[-1]) - ord(last[-1]) == 1:
                    was_adjoin = True
                else:
                    if was_adjoin:
                        region.append((buf, last))
                        buf = c
                        was_adjoin = False
                    else:
                        region.append(buf)
                        buf = c
            else:
                buf = c
            last = c

        if buf is not None:
            if was_adjoin:
                region.append((buf, c))
            else:
                region.append(c)

        return region


    def expand(self, pattern_str):
        """Expand a shorten set into a char list."""
        chars_ex = []
        for entry in self.split(pattern_str):
            if isinstance(entry, tuple):
                for range_char in range(ord(entry[0][-1]), ord(entry[1][-1]) + 1):
                    chars_ex.append(chr(range_char))
            else:
                chars_ex.append(entry)

        return chars_ex


    def split(self, pattern_str):
        """Parse the pattern for dashes and store them as tubles."""
        chars = []
        was_esc = False
        was_dash = False
        buf = None
        for c in pattern_str:
            if was_esc:
                c = '\\' + c
                was_esc = False
            elif c == "\\":
                was_esc = True
                continue

            if buf is not None:
                if was_dash:
                    chars.append((buf, c))
                    was_dash = False
                    buf = None
                elif c == "-":
                    was_dash = True
                else:
                    chars.append(buf)
                    buf = c
            else:
                buf = c

        if buf is not None:
            chars.append(buf)
            if was_dash:
                chars.append(c)

        return chars
