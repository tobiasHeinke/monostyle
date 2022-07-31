
"""
util.fragment
~~~~~~~~~~~~~

Text line container.
"""

class Fragment():
    """A substring with positional information."""

    __slots__ = ('filename', 'content', 'start_pos', 'end_pos', 'start_lincol', 'end_lincol')


    def __init__(self, filename, content, start_pos=None, end_pos=None,
                 start_lincol=None, end_lincol=None, use_lincol=True):
        """The content is split into lines.
        starts defaults to zero (because the start_lincol can not be measured).
        ends are measured/derived from content if None.

        filename -- absolute file path and name.
        content -- original text or replacement text as a list of string lines.
        start_pos/_end -- start/end as absolute char position (to the start of the file).
        start_lincol/_end -- start/end as line/column number (0-based).
                             Each added content (list entry) is treated as a line.
        """
        self.filename = filename

        start_pos = int(start_pos) if start_pos is not None else 0
        end_pos = int(end_pos) if end_pos is not None else None

        if content is None:
            content = []
        elif isinstance(content, str):
            content = [line for line in content.splitlines(keepends=True)]
        else:
            content = content.copy()

        self.content = content

        if end_pos is None:
            end_pos = start_pos + sum(map(len, content))

        if use_lincol:
            if start_lincol is None:
                start_lincol = (0, 0)
            if end_lincol is None:
                if len(content) == 0:
                    end_lincol = start_lincol
                elif len(content) == 1:
                    end_lincol = (start_lincol[0], start_lincol[1] + len(content[-1]))
                else:
                    end_lincol = (start_lincol[0] + max(0, len(content) - 1), len(content[-1]))

        self.start_pos = start_pos
        self.end_pos = end_pos
        self.start_lincol = start_lincol
        self.end_lincol = end_lincol


    def get_start(self, pos_lincol=True):
        return self.start_pos if pos_lincol else self.start_lincol

    def set_start(self, loc, lincol=None):
        """Note can impede a type error."""
        if lincol is not None:
            self.start_pos = loc
            self.start_lincol = lincol
        else:
            if isinstance(loc, int):
                self.start_pos = loc
                if self.start_lincol is not None:
                    self.start_lincol = self.pos_to_lincol(loc)
            else:
                self.start_pos = self.lincol_to_pos(loc)
                self.start_lincol = loc

    start = property(get_start, set_start)


    def get_end(self, pos_lincol=True):
        return self.end_pos if pos_lincol else self.end_lincol

    def set_end(self, loc, lincol=None):
        """Note can impede a type error."""
        if lincol is not None:
            self.end_pos = loc
            self.end_lincol = lincol
        else:
            if isinstance(loc, int):
                self.end_pos = loc
                if self.end_lincol is not None:
                    self.end_lincol = self.pos_to_lincol(loc)
            else:
                self.end_pos = self.lincol_to_pos(loc)
                self.end_lincol = loc

    end = property(get_end, set_end)


    # -- Filename ------------------------------------------------------------

    def has_consistent_filenames(self):
        return True


    # -- Content -------------------------------------------------------------

    def extend(self, new_content, keep_end=False):
        """Adds lines to the content. Join first with last if not newline end."""
        if len(new_content) == 0:
            return self

        self.rermove_zero_len_end()

        if isinstance(new_content, str):
            new_content = [line for line in new_content.splitlines(keepends=True)]

        is_empty = bool(not self.content)
        is_nl_end = bool(not is_empty and self.content[-1].endswith('\n'))
        if is_nl_end or is_empty:
            self.content.extend(new_content)
        else:
            self.content[-1] += new_content[0]
            self.content.extend(new_content[1:])

        if not keep_end:
            self.end_pos += sum(map(len, new_content))

            if self.end_lincol:
                self.end_lincol = (self.end_lincol[0] + len(new_content) -
                                   bool(not is_nl_end or is_empty), len(self.content[-1]))

        return self


    def rermove_zero_len_end(self):
        """Removes zero length line starts."""
        if (len(self.content) != 0 and len(self.content[-1]) == 0 and
                self.start_lincol and self.start_lincol[1] == 0):
            self.content = self.content[:-1]
            self.switch_lincol()
        return self


    def combine(self, other, check_align=True, pos_lincol=True, keep_end=False, merge=True):
        """Combines two aligned fragments into one."""
        if other.is_bundle():
            return self.to_bundle().combine(other, check_align, pos_lincol, keep_end, merge=False)

        if merge:
            if check_align and not self.is_aligned(other, pos_lincol):
                return self

            if pos_lincol or not self.end_lincol or not other.end_lincol:
                self.extend(other.content)
            else:
                if self.end_lincol == other.start_lincol:
                    if len(self.content) != 0 and len(other.content) != 0:
                        self.content[-1] += other.content[0]
                        if len(other.content) != 1:
                            self.content.extend(other.content[1:])
                    else:
                        self.content.extend(other.content)
                else:
                    self.content.extend(other.content)
        else:
            return self.to_bundle().combine(other, check_align, pos_lincol, keep_end, merge)

        if not keep_end:
            self.end_pos = other.end_pos
            if other.end_lincol:
                self.end_lincol = other.end_lincol

        return self


    def merge_inner(self, **_):
        return self


    def __add__(self, other):
        self_copy = self.copy()
        return (self_copy.combine(other) if isinstance(other, (Fragment, FragmentBundle))
                else self_copy.extend(other))


    def __iadd__(self, other):
        return (self.combine(other) if isinstance(other, (Fragment, FragmentBundle))
                else self.extend(other))


    def isdisjoint(self, other, pos_lincol):
        """Inverted is overlapped."""
        return not self.is_overlapped(other, pos_lincol)


    def issubset(self, other, pos_lincol):
        """Is within the spans of other."""
        if (not other.is_in_span(self.get_start(pos_lincol), False, True, True) or
                not other.is_in_span(self.get_end(pos_lincol), False, True, True)):
            return False

        for piece in other:
            if (piece.is_in_span(self.get_start(pos_lincol), False, True, True) and
                    piece.is_in_span(self.get_end(pos_lincol), False, True, True)):
                return True
        return False


    def issuperset(self, other, pos_lincol):
        """Other is within span."""
        if (not self.is_in_span(other.get_start(pos_lincol), False, True, True) or
                not self.is_in_span(other.get_end(pos_lincol), False, True, True)):
            return False

        for piece in other:
            if (not self.is_in_span(piece.get_start(pos_lincol), False, True, True) or
                    not self.is_in_span(piece.get_end(pos_lincol), False, True, True)):
                return False
        return True


    def union(self, other, pos_lincol):
        """Overlay other (A(B)B)."""
        new = FragmentBundle()
        before = other.slice(end=self.get_start(pos_lincol), output_zero=False)
        if before:
            new.combine(before, False, pos_lincol=pos_lincol)
        if (self.is_in_span(other.get_start(pos_lincol), False, True, True) or
                self.is_in_span(other.get_end(pos_lincol), False, True, True)):
            after = self
            for piece in other:
                if piece.get_end(pos_lincol) < self.get_start(pos_lincol):
                    continue
                if piece.get_start(pos_lincol) > self.get_end(pos_lincol):
                    break
                before, _, after = after.slice(piece.get_start(pos_lincol),
                                               piece.get_end(pos_lincol),
                                               plenary=True, output_zero=False)
                if before:
                    new.combine(before, False, pos_lincol=pos_lincol, merge=False)
                new.combine(piece, False, pos_lincol=pos_lincol, merge=False)

            if after:
                new.combine(after, False, pos_lincol=pos_lincol, merge=False)
        after = other.slice(self.get_end(pos_lincol), output_zero=False)
        if after:
            new.combine(after, False, pos_lincol=pos_lincol, merge=False)

        result = new.to_fragment()
        if result:
            return result
        return new


    def intersection(self, other, pos_lincol):
        """Cut out with other (_(A)_)."""
        if (not self.is_in_span(other.get_start(pos_lincol), False, True, True) and
                not self.is_in_span(other.get_end(pos_lincol), False, True, True)):
            return self

        new = FragmentBundle()
        for piece in other:
            if piece.get_start(pos_lincol) > self.get_end(pos_lincol):
                break
            if piece.get_end(pos_lincol) < self.get_start(pos_lincol):
                continue
            new.combine(self.slice(piece.get_start(pos_lincol), piece.get_end(pos_lincol),
                                   output_zero=True), pos_lincol=pos_lincol, merge=False)

        result = new.to_fragment()
        if result:
            return result
        return new


    def difference(self, other, pos_lincol):
        """Cut gaps with other (A(_)_)."""
        if (not self.is_in_span(other.get_start(pos_lincol), False, True, True) and
                not self.is_in_span(other.get_end(pos_lincol), False, True, True)):
            return self

        new = FragmentBundle()
        after = self
        for piece in other:
            if piece.get_end(pos_lincol) < self.get_start(pos_lincol):
                continue
            if piece.get_start(pos_lincol) > self.get_end(pos_lincol):
                break
            before, _, after = after.slice(piece.get_start(pos_lincol),
                                           piece.get_end(pos_lincol),
                                           plenary=True, output_zero=False)
            if before:
                new.combine(before, False, pos_lincol=pos_lincol, merge=False)

        if after:
            new.combine(after, False, pos_lincol=pos_lincol, merge=False)

        result = new.to_fragment()
        if result:
            return result
        return new


    def symmetric_difference(self, other, pos_lincol):
        """Cut gaps with overlaps of other (A(_)B)."""
        new = FragmentBundle()
        before = other.slice(end=self.get_start(pos_lincol), output_zero=False)
        if before:
            new.combine(before, False, pos_lincol=pos_lincol)
        if (self.is_in_span(other.get_start(pos_lincol), False, True, True) or
                self.is_in_span(other.get_end(pos_lincol), False, True, True)):
            after = self
            for piece in other:
                if piece.get_end(pos_lincol) < self.get_start(pos_lincol):
                    continue
                if piece.get_start(pos_lincol) > self.get_end(pos_lincol):
                    break
                before, _, after = after.slice(piece.get_start(pos_lincol),
                                               piece.get_end(pos_lincol),
                                               plenary=True, output_zero=False)
                if before:
                    new.combine(before, False, pos_lincol=pos_lincol, merge=False)

            if after:
                new.combine(after, False, pos_lincol=pos_lincol, merge=False)
        after = other.slice(self.get_end(pos_lincol), output_zero=False)
        if after:
            new.combine(after, False, pos_lincol=pos_lincol, merge=False)

        result = new.to_fragment()
        if result:
            return result
        return new


    def _transfere_attr(self, other):
        for prop in self.__slots__:
            setattr(self, prop, getattr(other, prop))


    def union_update(self, *args):
        result = self.union(*args)
        if not result.is_bundle():
            self._transfere_attr(result)
        else:
            raise ValueError("Fragment.union_update result is not complete")


    def intersection_update(self, *args):
        result = self.intersection(*args)
        if not result.is_bundle():
            self._transfere_attr(result)
        else:
            raise ValueError("Fragment.intersection_update result is not complete")


    def difference_update(self, *args):
        result = self.difference(*args)
        if not result.is_bundle():
            self._transfere_attr(result)
        else:
            raise ValueError("Fragment.difference_update result is not complete")


    def symmetric_difference_update(self, *args):
        result = self.symmetric_difference(*args)
        if not result.is_bundle():
            self._transfere_attr(result)
        else:
            raise ValueError("Fragment.symmetric_difference_update result is not complete")


    def __getitem__(self, key):
        if isinstance(key, int):
            key = slice(key, key + 1)

        return self.slice(start=key.start, end=key.stop, is_rel=True)


    def __setitem__(self, key, value):
        if isinstance(value, (Fragment, FragmentBundle)):
            value = value.copy()
        else:
            value = Fragment(self.filename, value)

        if isinstance(key, int):
            value.start_pos = key
            value.end_pos = key + 1
            pos_lincol = True
        else:
            pos_lincol = bool(isinstance(key.start, int))
            if pos_lincol:
                value.start_pos = key.start
                value.end_pos = key.stop
            else:
                value.start_lincol = key.start
                value.end_lincol = key.stop

        return self.union_update(value, pos_lincol)


    def __delitem__(self, key):
        return self.__setitem__(key, "")


    def slice_match(self, match_obj, group, plenary=False, output_zero=True, **_):
        """Slice by span defined by a regex match object."""
        if match_obj.group(group) is None:
            return None if not plenary else (None, None, None)

        return self.slice(match_obj.start(group), match_obj.end(group),
                          True, plenary, output_zero)


    def slice(self, start=None, end=None, is_rel=False, plenary=False, output_zero=True):
        """Cut span."""
        if start is None:
            if end is None:
                if not plenary:
                    return self.copy()
                if output_zero:
                    return self.copy().clear(True), self.copy(), self.copy().clear(False)
                return None, self.copy(), None

            start = self.get_start(isinstance(end, int))

        start_pos_abs = None
        if isinstance(start, int):
            if not is_rel:
                start_pos_abs = start
            start = self.pos_to_lincol(start, is_rel=is_rel, output_rel=is_rel, keep_bounds=True)
        if isinstance(end, int):
            end = self.pos_to_lincol(end, is_rel=is_rel, output_rel=is_rel, keep_bounds=True)

        if not is_rel:
            start_rel = self.loc_to_rel(start)
        else:
            start_rel = start
            start = self.loc_to_abs(start)

        if end is not None:
            if not is_rel:
                end_rel = self.loc_to_rel(end)
            else:
                end_rel = end
                end = self.loc_to_abs(end)

        self_start_rel = (0, 0)
        if self.end_lincol is not None:
            self_end_rel = self.loc_to_rel(self.end_lincol)
        else:
            self_end_rel = self.loc_to_rel(self.pos_to_lincol(self.end_pos, keep_bounds=True))

        cuts = []
        if plenary:
            cuts.append((self_start_rel, start_rel, self.start_pos, self.start_lincol))
        if end is None:
            cuts.append((start_rel, self_end_rel, start_pos_abs, start))
        else:
            cuts.append((start_rel, end_rel, start_pos_abs, start))
            if plenary:
                cuts.append((end_rel, self_end_rel, None, end))

        start_lincol_abs = start
        result = []
        for start, end, pos_abs, lincol_abs in cuts:
            if start <= self_start_rel and end <= self_start_rel:
                new = self.copy().clear(True) if output_zero else None
            elif end >= self_end_rel and start <= self_start_rel:
                new = self.copy()
            elif start >= self_end_rel:
                new = self.copy().clear(False) if output_zero else None
            elif start == end and not output_zero:
                new = None
            else:
                start = (max(start[0], 0), max(start[1], 0))
                end = (max(end[0], 0), max(end[1], 0))
                if start == end:
                    new_content = []
                else:
                    new_content = [self.content[start[0]][start[1]:]]
                    if start[0] == end[0]:
                        new_content = new_content[-1][:end[1] - start[1]]
                    else:
                        if start[0] + 1 < len(self.content):
                            new_content.extend(self.content[start[0]+1:end[0]])
                        if end[0] < len(self.content):
                            new_content.extend([self.content[end[0]][:end[1]]])

                if pos_abs is None:
                    if start_pos_abs is not None:
                        pos_abs = start_pos_abs
                    else:
                        pos_abs = self.lincol_to_pos(start_lincol_abs, keep_bounds=True)

                pos_abs = max(pos_abs, self.start_pos)
                if self.start_lincol:
                    lincol_abs = (lincol_abs if lincol_abs > self.start_lincol
                                  else self.start_lincol)
                else:
                    lincol_abs = None
                new = Fragment(self.filename, new_content, pos_abs, start_lincol=lincol_abs)
                start_pos_abs = new.end_pos

            result.append(new)

        return result[0] if len(result) == 1 else tuple(result)


    def slice_block(self, start=None, end=None, is_rel=False, plenary=False, output_zero=True,
                    include_before=False, include_after=False):
        """Returns a rectangular block defined by the start and end corners."""
        if start is None and end is None:
            if not plenary:
                return self.copy()
            elif not output_zero:
                return None, self.copy(), None

        if is_rel:
            start = self.loc_to_abs(start)
            if end is not None:
                end = self.loc_to_abs(end)

        if isinstance(start, int):
            start = self.pos_to_lincol(start)
        if isinstance(end, int):
            end = self.pos_to_lincol(end)

        if start is None:
            start = self.loc_to_abs((0, end[1] if end is not None else 0))
        if end is None:
            end = self.loc_to_abs((max(len(self.content) - 1, 0), start[1]))

        is_diff_column = bool(start[1] != end[1])

        cuts = [FragmentBundle()]
        if plenary:
            cuts.append(FragmentBundle())
        if is_diff_column:
            cuts.append(FragmentBundle())

        for line in self.slice(start if not include_before else (start[0], 0),
                               end if not include_after else (end[0]+1, 0)).splitlines():
            result = line.slice((line.start_lincol[0], start[1]),
                                (line.start_lincol[0], end[1]) if is_diff_column else None,
                                plenary, output_zero)
            for cut, piece in zip(cuts, result):
                if piece is not None:
                    cut.combine(piece, merge=False)

        return cuts[0] if len(cuts) == 1 else tuple(cuts)


    def splitlines(self, buffered=False):
        """Split the content into line Fragments per list item."""
        start_pos = self.start_pos
        apply_colno_offset = True
        lineno_offset = self.start_lincol[0] if self.start_lincol else 0
        for lineno, line_str in enumerate(self.content, lineno_offset):
            if self.start_lincol:
                if apply_colno_offset:
                    start_lincol = (lineno, self.start_lincol[1])
                    apply_colno_offset = False
                else:
                    start_lincol = (lineno, 0)
            else:
                start_lincol = None
            line = Fragment(self.filename, line_str, start_pos, start_lincol=start_lincol)
            yield line
            start_pos = line.end_pos

        if buffered:
            yield None


    def reversed_splitlines(self, buffered=False):
        """Split lines in reversed order."""
        start_pos = self.end_pos
        lineno_offset = self.end_lincol[0] if self.start_lincol else 0
        for index, line_str in enumerate(reversed(self.content)):
            start_pos -= len(line_str)
            if self.start_lincol:
                if index == 0 and self.end_lincol[1] == 0 and len(line_str) != 0:
                    lineno_offset -= 1
                lineno = lineno_offset - index
                if index == len(self.content) - 1:
                    start_lincol = (lineno, self.start_lincol[1])
                else:
                    start_lincol = (lineno, 0)
            else:
                start_lincol = None
            line = Fragment(self.filename, line_str, start_pos, start_lincol=start_lincol)
            yield line

        if buffered:
            yield None


    def iter_lines(self, buffered=False):
        """Yield content lines."""
        for line_str in self.content:
            yield line_str
        if buffered:
            yield None


    def replace(self, new_content, pos_lincol=True, open_end=True):
        if isinstance(new_content, (Fragment, FragmentBundle)):
            new = self.union(new_content, pos_lincol)
            if new.is_bundle():
                if not open_end:
                    return self
                new = new.bundle[0]
            self.content = new.content
        else:
            if isinstance(new_content, str):
                new_content = new_content.splitlines(keepends=True)
            else:
                if len(new_content) != 0 and isinstance(new_content[0], list):
                    if not open_end:
                        new_content = new_content[0]
                    else:
                        new = []
                        for content in new_content:
                            new.extend(content)
                        new_content = new

            self.content = new_content
        return self


    def replace_fill(self, new_content, open_end=True):
        if isinstance(new_content, str):
            if not open_end:
                new_content = new_content[:len(self)]
            new_content = new_content.splitlines(keepends=True)
        else:
            if not open_end:
                new_content = new_content[:len(self.content)]

        self.content = new_content
        return self


    def clear(self, start_end):
        """Remove content. Turn into zero-length Fragment at start or end."""
        self.content.clear()
        if start_end:
            self.end_pos = self.start_pos
            self.end_lincol = self.start_lincol
        else:
            self.start_pos = self.end_pos
            self.start_lincol = self.end_lincol

        return self


    def isspace(self):
        """The content is empty or contains only whitespaces."""
        if len(self.content) == 0:
            return True

        for line_str in self.content:
            if not line_str.isspace():
                return False

        return True


    def contains_line(self, line_str):
        """Shallow search content list."""
        return line_str in self.content


    def sort(self, *_):
        return None


    # -- Location ------------------------------------------------------------

    def move(self, pos=None, lincol=None, is_rel=False):
        """Moves the location."""
        if not is_rel:
            if pos:
                self.end_pos = pos + self.span_len(True)
                self.start_pos = pos

            if lincol and self.start_lincol:
                if self.start_lincol[0] == self.end_lincol[0]:
                    self.end_lincol = lincol + self.span_len(False)
                else:
                    self.end_lincol = (lincol[0] + self.span_len(False)[0], self.end_lincol[1])

                self.start_lincol = lincol

        else:
            if pos:
                self.start_pos += pos
                self.end_pos += pos

            if lincol and self.start_lincol:
                if self.start_lincol[0] == self.end_lincol[0]:
                    self.end_lincol = (self.end_lincol[0] + lincol[0],
                                       self.end_lincol[1] + lincol[1])
                else:
                    self.end_lincol = (self.end_lincol[0] + lincol[0], self.end_lincol[1])

                self.start_lincol = (self.start_lincol[0] + lincol[0],
                                     self.start_lincol[1] + lincol[1])

        return self


    def switch_lincol(self, before=None):
        """Moves the lincol end at column 0 to the previous line end and in reverse for start."""
        if before:
            if before.is_bundle():
                before = before.bundle[-1]
            if (self.start_lincol and before.is_aligned(self, False) and
                    before.content and before.content[-1].endswith('\n')):
                new_start = (self.start_lincol[0] + 1, 0)
                if self.start_lincol == self.end_lincol:
                    self.end_lincol = new_start
                self.start_lincol = new_start

        if (not self.end_lincol or not self.content or
                self.end_lincol[1] != 0 or self.end_lincol == self.start_lincol):
            return self
        if self.content[-1].endswith('\n'):
            self.end_lincol = (self.end_lincol[0] - 1, len(self.content[-1]))

        return self


    def loc_to_abs(self, loc_rel, **_):
        """Convert a location relative to the start to an absolute location."""
        if isinstance(loc_rel, int):
            return self.start_pos + loc_rel

        start_lincol = self.start_lincol if self.start_lincol else (0, 0)
        loc_abs_lineno = start_lincol[0] + loc_rel[0]
        if loc_rel[0] == 0:
            loc_abs_colno = start_lincol[1] + loc_rel[1]
        else:
            loc_abs_colno = loc_rel[1]

        return (loc_abs_lineno, loc_abs_colno)


    def loc_to_rel(self, loc_abs, **_):
        """Convert an absolute location to a location relative to the start."""
        if isinstance(loc_abs, int):
            return loc_abs - self.start_pos

        start_lincol = self.start_lincol if self.start_lincol else (0, 0)
        loc_rel_lineno = loc_abs[0] - start_lincol[0]
        if loc_rel_lineno == 0:
            loc_rel_colno = loc_abs[1] - start_lincol[1]
        else:
            loc_rel_colno = loc_abs[1]

        return (loc_rel_lineno, loc_rel_colno)


    def lincol_to_pos(self, lincol, is_rel=False, output_rel=False, keep_bounds=False):
        """Convert a lincol location to a pos location."""
        if not is_rel:
            lincol = self.loc_to_rel(lincol)
        if lincol < (0, 0):
            if keep_bounds:
                return self.start_pos if not output_rel else 0
            return None

        cursor = 0
        for index, line in enumerate(self.content):
            if lincol[0] == index:
                cursor += lincol[1]
                return self.loc_to_abs(cursor) if not output_rel else cursor

            cursor += len(line)

        if keep_bounds:
            return self.loc_to_abs(cursor) if not output_rel else cursor


    def pos_to_lincol(self, pos, is_rel=False, output_rel=False, keep_bounds=False):
        """Convert a pos location to a lincol location."""
        if not is_rel:
            pos = self.loc_to_rel(pos)
        if pos < 0:
            if keep_bounds:
                return self.start_lincol if not output_rel and self.start_lincol else (0, 0)
            return None

        cursor = 0
        for index, line in enumerate(self.content):
            # favor next line start over current end
            if pos >= cursor and pos - cursor < len(line):
                cursor = (index, pos - cursor)
                return self.loc_to_abs(cursor) if not output_rel else cursor

            cursor += len(line)

        if keep_bounds:
            if len(self.content) == 0:
                return self.loc_to_abs((0, 0)) if not output_rel else (0, 0)

            cursor = (len(self.content) - 1, len(self.content[-1]))
            return self.loc_to_abs(cursor) if not output_rel else cursor


    def is_in_span(self, loc, is_rel=False, include_start=True, include_end=True):
        """Check if the location is between start and end."""
        if is_rel:
            loc = self.loc_to_abs(loc)

        pos_lincol = bool(isinstance(loc, int))
        self_start = self.get_start(pos_lincol)
        self_end = self.get_end(pos_lincol)

        if self_start == self_end:
            if include_start and include_end and loc == self_start:
                return True
        else:
            if ((include_start and loc == self_start) or
                    (include_end and loc == self_end)):
                return True

        if loc > self_start and loc < self_end:
            return True

        return False


    def is_aligned(self, other, pos_lincol, **_):
        """Check if two fragments are aligned."""
        if pos_lincol or not self.end_lincol or not other.start_lincol:
            if self.end_pos == other.start_pos:
                return True
        else:
            if self.end_lincol == other.start_lincol:
                return True
            if (other.start_lincol[1] == 0 and self.end_lincol[0] + 1 == other.start_lincol[0] and
                    self.content and self.content[-1].endswith('\n')):
                return True

        return False


    def is_overlapped(self, other, pos_lincol, _is_recursive=False):
        """Check if two fragments overlap."""
        if not _is_recursive and other.is_bundle():
            return other.is_overlapped(self, pos_lincol)

        if not self.end_lincol or not other.start_lincol:
            pos_lincol = True
        if (other.get_start(pos_lincol) == other.get_end(pos_lincol) or
                self.get_start(pos_lincol) == self.get_end(pos_lincol)):
            if self.is_in_span(other.get_start(pos_lincol), False, False, False):
                return True
        elif (self.is_in_span(other.get_start(pos_lincol), False, True, False) or
                self.is_in_span(other.get_end(pos_lincol), False, False, True)):
            return True

        if not _is_recursive and other.is_overlapped(self, pos_lincol, _is_recursive=True):
            return True
        return False


    def is_self_overlapped(self, *_):
        return False


    def is_complete(self, *_):
        return True


    # -- Size ----------------------------------------------------------------

    def __len__(self):
        """Returns the content char length."""
        return sum(map(len, self.content))


    def span_len(self, pos_lincol):
        """Returns either the span char length or
        the line span and column span of the first and last line.
        """
        if pos_lincol:
            return self.end_pos - self.start_pos

        line_span = self.end_lincol[0] - self.start_lincol[0]
        if self.start_lincol != self.end_lincol:
            line_span += 1
        return (line_span, self.end_lincol[1] - self.start_lincol[1])


    def size(self, pos_lincol):
        """Returns the dimensions either the char length or the size of the bounding rectangle."""
        if pos_lincol:
            return len(self)

        if len(self.content) == 0:
            return (0, 0)
        if len(self.content) == 1:
            return (len(self.content), len(self.content[0]))

        max_len = self.start_lincol[1] + len(self.content[0])
        for line_str in self.content:
            max_len = max(max_len, len(line_str))
        return (len(self.content), max_len)


    def is_empty(self):
        return len(self.content) == 0


    # -- Iterate, Compare & Convert ------------------------------------------

    def __iter__(self):
        yield self


    def is_bundle(self):
        """Returns is FragmentBundle."""
        return False


    def __eq__(self, other):
        """Returns if the Fragment are the same."""
        if type(other) != Fragment:
            return False

        if self is other:
            return True

        for prop in self.__slots__:
            if getattr(self, prop) != getattr(other, prop):
                # one of the content is same list or str then compare the effective
                if (prop != "content" or
                        type(self.content) != type(other.content) or
                        ''.join(self.content) != ''.join(other.content)):
                    return False

        return True


    def __ne__(self, other):
        """Returns if the Fragment are not same."""
        return not self.__eq__(other)


    def __bool__(self):
        """Returns is not None."""
        return True


    def __contains__(self, other):
        return other is self


    def to_fragment(self, **_):
        return self


    def to_bundle(self):
        """Convert into FragmentBundle."""
        return FragmentBundle([self])


    def join(self, **_):
        return str(self)


    def __str__(self):
        """Returns the joined content list."""
        return str(''.join(self.content))


    def __repr__(self):
        return self.repr(bool(not self.end_lincol), True, False)


    def repr(self, show_pos, show_filename=False, show_content=True):
        """Shows the content with the location at start and end."""
        filename = self.filename + ":" if show_filename else ''
        if show_pos:
            start = str(self.get_start(show_pos))
            end = str(self.get_end(show_pos))
        else:
            start = '{0},{1}'.format(*self.get_start(show_pos))
            end = '{0},{1}'.format(*self.get_end(show_pos))

        if show_content:
            return '(' + filename + start + ')' + str(self).replace('\n', '¶') + '(' + end + ')'

        return filename + start + '-' + end


    def copy(self):
        """Returns a deep copy."""
        return Fragment(self.filename, self.content.copy(), self.start_pos,
                        self.end_pos, self.start_lincol, self.end_lincol,
                        bool(self.start_lincol is not None))


# ============================================================================


class FragmentBundle(Fragment):
    """A list of Fragments. Well formed if: sorted, non overlapping."""

    __slots__ = ('bundle',)


    def __init__(self, bundle=None):
        """bundle -- a list of Fragments."""
        if bundle is None:
            bundle = []

        self.bundle = bundle


    def get_filename(self):
        return self.bundle[0].filename if self else None

    def set_filename(self, value):
        for piece in self:
            piece.filename = value

    filename = property(get_filename, set_filename)


    def attr_content(self, *_):
        """Delete inherited content attribute by overriding it."""
        raise AttributeError("'FragmentBundle' object has no attribute 'content'")

    content = property(attr_content, attr_content, attr_content)


    def get_start_pos(self):
        return self.bundle[0].start_pos if self else None

    def set_start_pos(self, value):
        if not self:
            return
        self.bundle[0].start_pos = value

    start_pos = property(get_start_pos, set_start_pos)


    def get_end_pos(self):
        return self.bundle[-1].end_pos if self else None

    def set_end_pos(self, value):
        if not self:
            return
        self.bundle[-1].end_pos = value

    end_pos = property(get_end_pos, set_end_pos)


    def get_start_lincol(self):
        return self.bundle[0].start_lincol if self else None

    def set_start_lincol(self, value):
        if not self:
            return
        self.bundle[0].start_lincol = value

    start_lincol = property(get_start_lincol, set_start_lincol)


    def get_end_lincol(self):
        return self.bundle[-1].end_lincol if self else None

    def set_end_lincol(self, value):
        if not self:
            return
        self.bundle[-1].end_lincol = value

    end_lincol = property(get_end_lincol, set_end_lincol)


    # -- Filename ------------------------------------------------------------

    def has_consistent_filenames(self):
        """All filenames are the same."""
        prev = None
        for piece in self:
            if prev.filename != piece.filename:
                return False
            prev = piece
        return True


    # -- Content -------------------------------------------------------------

    def extend(self, new_content, keep_end=False):
        if not self:
            return self

        self.bundle[-1].extend(new_content, keep_end)
        return self


    def rermove_zero_len_end(self):
        if not self:
            return self

        self.bundle[-1].rermove_zero_len_end()
        return self


    def combine(self, other, check_align=True, pos_lincol=True, keep_end=False, merge=True):
        """Merge -- combine last and first if aligned."""
        if not other:
            return self

        is_before = bool(not self or other.get_start(pos_lincol) < self.get_end(pos_lincol))

        if keep_end and self:
            end_cur = self.get_end(pos_lincol)
            for piece in other:
                if piece.get_start(pos_lincol) > end_cur:
                    piece.start_pos = self.bundle[-1].end_pos
                    if self.bundle[-1].end_lincol:
                        piece.start_lincol = self.bundle[-1].end_lincol
                if piece.get_end(pos_lincol) > end_cur:
                    piece.end_pos = self.bundle[-1].end_pos
                    if self.bundle[-1].end_lincol:
                        piece.end_lincol = self.bundle[-1].end_lincol

        bundle = other.bundle if other.is_bundle() else (other,)
        if merge and self and (not check_align or self.is_aligned(other, pos_lincol)):
            if not self.is_overlapped(other, pos_lincol):
                self.bundle[-1].combine(bundle[0], check_align, pos_lincol, merge=merge)
                self.bundle.extend(bundle[1:])
        else:
            self.bundle.extend(bundle)

        if is_before:
            self.sort(pos_lincol)

        return self


    def merge_inner(self, pos_lincol=True):
        """Combine aligning Fragments within bundle."""
        prev = None
        new_bundle = []
        for piece in self:
            if prev and prev.is_aligned(piece, pos_lincol):
                prev.combine(piece, check_align=False, pos_lincol=pos_lincol)
            else:
                new_bundle.append(piece)
                prev = piece
        self.bundle = new_bundle
        return self


    def __add__(self, other):
        self_copy = self.copy()
        return (self_copy.combine(other) if isinstance(other, (Fragment, FragmentBundle))
                else self_copy.extend(other))


    def __iadd__(self, other):
        return (self.combine(other) if isinstance(other, (Fragment, FragmentBundle))
                else self.extend(other))


    def isdisjoint(self, other, pos_lincol):
        return not self.is_overlapped(other, pos_lincol)


    def issubset(self, other, pos_lincol):
        if (not other.is_in_span(self.get_start(pos_lincol), False, True, True) or
                not other.is_in_span(self.get_end(pos_lincol), False, True, True)):
            return False

        for piece_own in self:
            for piece_other in other:
                if (piece_other.is_in_span(piece_own.get_start(pos_lincol), False, True, True) and
                        piece_other.is_in_span(piece_own.get_end(pos_lincol), False, True, True)):
                    break
            else:
                return False
        return True


    def issuperset(self, other, pos_lincol):
        if (not self.is_in_span(other.get_start(pos_lincol), False, True, True) or
                not self.is_in_span(other.get_end(pos_lincol), False, True, True)):
            return False

        for piece_other in other:
            for piece_own in self:
                if (piece_own.is_in_span(piece_other.get_start(pos_lincol), False, True, True) and
                        piece_own.is_in_span(piece_other.get_end(pos_lincol), False, True, True)):
                    break
            else:
                return False
        return True


    def union(self, other, pos_lincol):
        new = FragmentBundle()
        before = other.slice(end=self.get_start(pos_lincol), output_zero=False)
        if before:
            new.combine(before, False, pos_lincol=pos_lincol)
        after = self
        for piece_own in self:
            other_cut = other.slice(new.get_end(pos_lincol) if new
                                    else other.get_start(pos_lincol),
                                    piece_own.get_end(pos_lincol),
                                    output_zero=False)
            if not other_cut:
                continue

            new.combine(piece_own.union(other_cut, pos_lincol), False, pos_lincol=pos_lincol,
                        merge=False)

        after = other.slice(self.get_end(pos_lincol), output_zero=False)
        if after:
            new.combine(after, False, pos_lincol=pos_lincol, merge=False)

        result = new.to_fragment()
        if result:
            return result
        return new


    def intersection(self, other, pos_lincol):
        if (not self.is_in_span(other.get_start(pos_lincol), False, True, True) and
                not self.is_in_span(other.get_end(pos_lincol), False, True, True)):
            return self

        new = FragmentBundle()
        for piece in self:
            new.combine(piece.intersection(other, pos_lincol), False, pos_lincol, merge=False)

        result = new.to_fragment()
        if result:
            return result
        return new


    def difference(self, other, pos_lincol):
        if (not self.is_in_span(other.get_start(pos_lincol), False, True, True) and
                not self.is_in_span(other.get_end(pos_lincol), False, True, True)):
            return self

        new = FragmentBundle()
        for piece in self:
            new.combine(piece.difference(other, pos_lincol), False, pos_lincol, merge=False)

        result = new.to_fragment()
        if result:
            return result
        return new


    def symmetric_difference(self, other, pos_lincol):
        new = FragmentBundle()
        before = other.slice(end=self.get_start(pos_lincol), output_zero=False)
        if before:
            new.combine(before, False, pos_lincol=pos_lincol)
        for piece in self:
            other_cut = other.slice(new.get_end(pos_lincol) if new
                                    else other.get_start(pos_lincol),
                                    piece.get_end(pos_lincol),
                                    output_zero=False)
            if not other_cut:
                continue

            new.combine(piece.symmetric_difference(other_cut, pos_lincol), False,
                        pos_lincol=pos_lincol, merge=False)

        after = other.slice(self.get_end(pos_lincol), output_zero=False)
        if after:
            new.combine(after, False, pos_lincol=pos_lincol, merge=False)

        result = new.to_fragment()
        if result:
            return result
        return new


    def _transfere_attr(self, other):
        for prop in super().__slots__ + self.__slots__:
            if prop == "content":
                continue
            setattr(self, prop, getattr(other, prop))


    def union_update(self, *args):
        result = self.union(*args)
        if not result.is_bundle():
            result = result.to_bundle()
        self._transfere_attr(result)


    def intersection_update(self, *args):
        result = self.intersection(*args)
        if not result.is_bundle():
            result = result.to_bundle()
        self._transfere_attr(result)


    def difference_update(self, *args):
        result = self.difference(*args)
        if not result.is_bundle():
            result = result.to_bundle()
        self._transfere_attr(result)


    def symmetric_difference_update(self, *args):
        result = self.symmetric_difference(*args)
        if not result.is_bundle():
            result = result.to_bundle()
        self._transfere_attr(result)


    def slice_match(self, match_obj, group, plenary=False, output_zero=True, filler=None):
        """relative to first."""
        if not self:
            return self.copy()

        if match_obj.group(group) is None:
            return None if not plenary else (None, None, None)

        return self.slice(self.loc_to_abs(match_obj.start(group), filler),
                          self.loc_to_abs(match_obj.end(group), filler),
                          plenary, output_zero)


    def slice(self, start=None, end=None, is_rel=False, plenary=False, output_zero=True):
        if not self or start is None:
            if not self or end is None:
                if not plenary:
                    return self.copy()
                if output_zero:
                    return self.copy().clear(True), self.copy(), self.copy().clear(False)
                return None, self.copy(), None

            start = self.get_start(isinstance(end, int))

        if end is not None and end < start:
            end = start

        if is_rel:
            start = self.loc_to_abs(start)
            if end is not None:
                end = self.loc_to_abs(end)

        pos_lincol = bool(isinstance(start, int))
        cuts = []
        start_index = self.index_clip(start, False)
        if plenary:
            cuts.append(((0, True), self.bundle[0].get_start(pos_lincol),
                         start_index, start))
        if not end:
            cuts.append((start_index, start,
                         (max(0, len(self.bundle) - 1), True),
                         self.bundle[-1].get_end(pos_lincol)))
        else:
            end_index = self.index_clip(end, True)
            cuts.append((start_index, start, end_index, end))
            if plenary:
                cuts.append((end_index, end,
                             (max(0, len(self.bundle) - 1), True),
                             self.bundle[-1].get_end(pos_lincol)))

        result = []
        for index_start, start, index_end, end in cuts:
            if start <= self.get_start(pos_lincol) and end <= self.get_start(pos_lincol):
                new = self.bundle[0].clear(True) if output_zero else None
            elif end >= self.get_end(pos_lincol) and start <= self.get_start(pos_lincol):
                new = self.copy()
            elif start >= self.get_end(pos_lincol):
                new = self.bundle[-1].clear(False) if output_zero else None
            elif start == end and not output_zero:
                new = None
            else:
                new = FragmentBundle()
                if index_start[1]:
                    if index_start[0] == index_end[0]:
                        piece_first = self.bundle[index_start[0]].slice(start, end)
                    else:
                        piece_first = self.bundle[index_start[0]].slice(start)

                    if piece_first is not None and len(piece_first) != 0:
                        new.bundle.append(piece_first)
                if index_start[0] == index_end[0] and not index_start[1] and not index_end[1]:
                    pieces_inner = self.bundle[index_start[0]]
                    new.bundle.append(pieces_inner.copy())
                elif index_start[0] != index_end[0]:
                    if not index_start[1] and not index_end[1]:
                        pieces_inner = self.bundle[index_start[0]]
                        new.bundle.append(pieces_inner.copy())
                    else:
                        for piece in self.bundle[min(len(self.bundle), index_start[0] + 1):
                                                 index_end[0]]:
                            new.bundle.append(piece.copy())
                    if index_end[1]:
                        piece_last = self.bundle[index_end[0]].slice(self.bundle[index_end[0]]
                                                                     .get_start(pos_lincol),
                                                                     end)
                        if piece_last is not None and len(piece_last) != 0:
                            new.bundle.append(piece_last)

            result.append(new)

        return result[0] if len(result) == 1 else tuple(result)


    def slice_block(self, start=None, end=None, is_rel=False, plenary=False, output_zero=True,
                    include_before=False, include_after=False):
        if not self or (start is None and end is None):
            if not plenary:
                return self.copy()
            elif not output_zero:
                return None, self.copy(), None

        if is_rel:
            start = self.loc_to_abs(start)
            if end is not None:
                end = self.loc_to_abs(end)

        if isinstance(start, int):
            start = self.pos_to_lincol(start)
        if isinstance(end, int):
            end = self.pos_to_lincol(end)

        if start is None:
            start = self.loc_to_abs((0, end[1] if end is not None else 0))
        if end is None:
            end = self.bundle[-1].loc_to_abs((sum(max(len(piece.content) - 1, 0)
                                                  for piece in self.bundle), start[1]))

        cuts = [FragmentBundle()]
        if plenary:
            cuts.append(FragmentBundle())
        if start[1] != end[1]:
            cuts.append(FragmentBundle())
        for index, piece in enumerate(self):
            result = piece.slice_block(start, end, plenary, output_zero,
                                       include_before or index != 0,
                                       include_after or index != len(self.bundle) - 1)
            for cut, bundle in zip(cuts, result):
                if bundle:
                    cut.combine(bundle, merge=False)

        return cuts[0] if len(cuts) == 1 else tuple(cuts)


    def splitlines(self, buffered=False):
        for piece in self:
            yield from piece.splitlines()
        if buffered:
            yield None


    def reversed_splitlines(self, buffered=False):
        for piece in self:
            yield from piece.reversed_splitlines()
        if buffered:
            yield None


    def iter_lines(self, buffered=False):
        for piece in self:
            yield from piece.iter_lines()
        if buffered:
            yield None


    def replace(self, new_content, pos_lincol=True, open_end=True):
        """Map list entry to entry in bundle."""
        if isinstance(new_content, (Fragment, FragmentBundle)):
            new = self.union(new_content, pos_lincol)
            if not new.is_bundle():
                new = new.to_bundle()
            self.bundle = new.bundle
        else:
            if not self:
                return self

            for piece, content in zip(self, new_content):
                piece.replace(content)

            for piece in self.bundle[len(new_content):]:
                piece.replace("")

            if open_end:
                for content in new_content[len(self.bundle):]:
                    self.bundle[-1].extend(content)

        return self


    def replace_fill(self, new_content, open_end=True):
        """Replace chars or lines distributed by current content length."""
        if not self:
            return self

        pos_lincol = bool(isinstance(new_content, str))
        prev_end = 0
        for index, piece in enumerate(self):
            if prev_end < len(new_content):
                length = len(piece) if pos_lincol else len(piece.content)
                if open_end and index == len(self.bundle) - 1:
                    piece.replace_fill(new_content[prev_end:], open_end=True)
                else:
                    piece.replace_fill(new_content[prev_end:prev_end + length])
                    prev_end += length
            else:
                piece.replace_fill("")
        return self


    def clear(self, start_end):
        if not self:
            return self
        if start_end:
            self.bundle = [self.bundle[0].clear(start_end)]
        else:
            self.bundle = [self.bundle[-1].clear(start_end)]

        return self


    def isspace(self):
        if not self:
            return True

        for piece in self:
            if not piece.isspace():
                return False

        return True


    def contains_line(self, line_str):
        if not self:
            return False

        for piece in self:
            if piece.contains_line(line_str):
                return True

        return False


    def sort(self, pos_lincol, start_end=False):
        """Sort bundle by location."""
        self.bundle.sort(key=(lambda piece: (piece.get_start(pos_lincol),
                                             piece.get_end(pos_lincol)))
                             if start_end else
                             (lambda piece: (piece.get_end(pos_lincol),
                                             piece.get_start(pos_lincol))))


    # -- Location ------------------------------------------------------------

    def move(self, pos=None, lincol=None, is_rel=False):
        if not is_rel:
            for piece in self:
                lincol_piece = None
                if lincol:
                    if piece.start_lincol[0] == self.start_lincol[0]:
                        lincol_piece = lincol[0] + self.loc_to_rel(piece.start_lincol)
                    else:
                        lincol_piece = (lincol[0] + self.loc_to_rel(piece.start_lincol)[0],
                                        piece.start_lincol[1])
                piece.move(pos + self.loc_to_rel(piece.start_pos), lincol_piece, is_rel=is_rel)

        else:
            first_line = True
            for piece in self:
                if lincol and first_line and piece.start_lincol[0] != self.start_lincol[0]:
                    lincol = (lincol[0], 0)
                    first_line = False
                piece.move(pos, lincol, is_rel=is_rel)

        return self


    def switch_lincol(self):
        if not self:
            return self

        self.bundle[-1].switch_lincol()
        return self


    def loc_to_abs(self, loc_rel, filler=None):
        if not self:
            return None

        if filler is None:
            return self.bundle[0].loc_to_abs(loc_rel)

        if isinstance(loc_rel, int):
            filler = len(filler) if filler else 0
            cursor = 0
            prev = None
            for piece in self:
                if prev is not None and prev != piece.start_pos:
                    if loc_rel <= cursor + filler:
                        return prev + loc_rel - cursor
                    cursor += filler
                if loc_rel <= cursor + piece.span_len(True):
                    return piece.loc_to_abs(loc_rel - cursor)
                cursor += piece.span_len(True)
                prev = piece.end_pos

        else:
            filler = ((filler.count('\n'), filler.rfind('\n'))
                      if filler and '\n' in filler else (0, 0))
            cursor = [0, 0]
            prev = None
            for piece in self:
                if prev is not None and prev != piece.start_pos:
                    cursor[0] += filler[0]
                    cursor[1] = filler[1] if filler[0] != 0 else cursor[1] + filler[1]
                span_len = piece.span_len(False)
                cursor_end = cursor.copy()
                cursor_end[0] += span_len[0] - 1
                cursor_end[1] = (piece.end_lincol[1] if span_len[0] > 1 else
                                 cursor[1] + piece.end_lincol[1])
                if loc_rel <= tuple(cursor_end):
                    return piece.loc_to_abs((loc_rel[0] - cursor[0], loc_rel[1] - cursor[1]))
                cursor = cursor_end
                if ((span_len[0] > 1 and piece.end_lincol[1] == 0) or
                        (piece.content and piece.content[-1].endswith('\n'))):
                    cursor[0] += 1
                    cursor[1] = 0

                prev = piece.end_pos


    def loc_to_rel(self, loc_abs, filler=None):
        if not self:
            return None

        if filler is None:
            return self.bundle[0].loc_to_rel(loc_abs)

        if isinstance(loc_abs, int):
            for piece in self:
                if piece.is_in_span(loc_abs):
                    filler = len(filler) if filler else 0
                    cursor = 0
                    prev = None
                    for rec in self:
                        if prev is piece:
                            break
                        if prev is not None and prev != rec.start_pos:
                            cursor += filler + rec.span_len(True)
                        prev = piece.end_pos
                    return cursor + loc_abs - piece.start_pos
        else:
            for piece in self:
                if piece.is_in_span(loc_abs):
                    filler = ((filler.count('\n'), filler.rfind('\n'))
                              if filler and '\n' in filler else (0, 0))
                    cursor = [0, 0]
                    prev = None
                    for rec in self:
                        if prev is not None and prev != rec.start_pos:
                            cursor[0] += filler[0]
                            cursor[1] = filler[1] if filler[0] != 0 else cursor[1] + filler[1]
                        span_len = rec.span_len(False)
                        if rec is piece:
                            break
                        cursor[0] += span_len[0] - 1
                        cursor[1] = (rec.end_lincol[1] if span_len[0] > 1 else
                                     cursor[1] + rec.end_lincol[1])
                        if ((span_len[0] > 1 and rec.end_lincol[1] == 0) or
                                (rec.content and rec.content[-1].endswith('\n'))):
                            cursor[0] += 1
                            cursor[1] = 0
                        prev = rec.end_pos
                    rel = piece.loc_to_rel(loc_abs)
                    return (cursor[0] + rel[0], rel[1] if span_len[0] > 1 else cursor[1] + rel[1])


    def lincol_to_pos(self, lincol, is_rel=False, output_rel=False, keep_bounds=False):
        if not self:
            return None

        if is_rel:
            lincol = self.loc_to_abs(lincol)
        if lincol < self.start_lincol:
            if keep_bounds:
                return self.start_pos if not output_rel else 0
            return None

        for piece in self:
            if piece.is_in_span(lincol):
                return piece.lincol_to_pos(lincol, False, output_rel, keep_bounds)

        if keep_bounds:
            return self.end_pos if not output_rel else self.loc_to_rel(self.end_pos)


    def pos_to_lincol(self, pos, is_rel=False, output_rel=False, keep_bounds=False):
        if not self:
            return None

        if is_rel:
            pos = self.loc_to_abs(pos)
        if pos < self.start_pos:
            if keep_bounds:
                return self.start_lincol if not output_rel else (0, 0)
            return None

        for piece in self:
            if piece.is_in_span(pos):
                return piece.pos_to_lincol(pos, False, output_rel, keep_bounds)

        if keep_bounds:
            return self.end_pos if not output_rel else self.loc_to_rel(self.end_lincol)


    def index_at(self, loc, is_rel=False, include_start=True, include_end=True):
        """Return index of the first Fragment which has the loc within it's span."""
        for index, piece in enumerate(self):
            if piece.is_in_span(loc, is_rel, include_start, include_end):
                return index


    def index_clip(self, loc, prev_next, is_rel=False):
        """Return index of the Fragment which has the loc within it's span or
        when in between the previous or next Fragment.
        """
        if is_rel:
            loc = self.loc_to_abs(loc)
        pos_lincol = bool(isinstance(loc, int))
        for index, piece in enumerate(self):
            if loc < piece.get_start(pos_lincol):
                return max(0, index - 1) if prev_next else index, False
            if piece.is_in_span(loc):
                return index, True

        return index, False


    def is_in_span(self, loc, is_rel=False, include_start=True, include_end=True):
        """include for each."""
        if not self:
            return False

        for piece in self:
            if piece.is_in_span(loc, is_rel, include_start, include_end):
                return True

        return False


    def is_aligned(self, other, pos_lincol, last_only=True):
        if not self or not other:
            return True

        piece_first = next(iter(other))

        if last_only:
            return self.bundle[-1].is_aligned(piece_first, pos_lincol)

        for piece in self:
            if piece.is_aligned(piece_first, pos_lincol):
                return True
        return False


    def is_overlapped(self, other, pos_lincol):
        if not self or not other:
            return False

        for piece_own in self:
            for piece_other in other:
                if piece_own.is_overlapped(piece_other, pos_lincol):
                    return True
        return False


    def is_self_overlapped(self, pos_lincol):
        """Check for overlaps within itself."""
        for piece in self.bundle:
            for rec in self.bundle:
                if rec is not piece and piece.is_overlapped(rec, pos_lincol):
                    return True

        return False


    def is_complete(self, pos_lincol):
        """Has no gaps thus all its Fragments are aligned."""
        if not self:
            return True

        prev = None
        for piece in self:
            if prev is not None:
                if not prev.is_aligned(piece, pos_lincol):
                    return False
            prev = piece
        return True


    # -- Size ----------------------------------------------------------------

    def __len__(self):
        if not self:
            return 0

        return sum(len(piece) for piece in self)


    def span_len(self, pos_lincol):
        if not self:
            return 0 if pos_lincol else (0, 0)

        if pos_lincol:
            return self.bundle[-1].end_pos - self.bundle[0].start_pos

        line_span = self.bundle[-1].end_lincol[0] - self.bundle[0].start_lincol[0]
        if self.bundle[0].start_lincol != self.bundle[-1].end_lincol:
            line_span += 1
        return (line_span, self.bundle[-1].end_lincol[1] - self.bundle[0].start_lincol[1])


    def size(self, pos_lincol):
        if not self:
            return 0 if pos_lincol else (0, 0)

        if pos_lincol:
            return len(self)

        if len(self.bundle) == 1:
            return self.bundle[0].size(pos_lincol)

        line_len = 0
        col_len = 0
        col_min = None
        for piece in self:
            if len(piece.content) == 0:
                continue
            piece_size = self.bundle[0].size(pos_lincol)
            line_len += piece_size[0]
            if col_min is None:
                col_min = piece.start_lincol[1]
            if len(piece.content) == 1:
                col_min = min(col_min, piece.start_lincol[1])
                col_len = max(col_len, piece_size[1] + piece.start_lincol[1])
            else:
                col_min = min(col_min, 0)
                col_len = max(col_len, piece_size[1])

        return (line_len, col_len - col_min)


    def is_empty(self):
        """Return if the Bundle list is empty or all its Fragments are empty."""
        if not self:
            return True

        for piece in self:
            if not piece.is_empty():
                return False
        return True


    # -- Iterate, Compare & Convert ------------------------------------------

    def __iter__(self):
        """Iterate over bundle list."""
        yield from self.bundle


    def is_bundle(self):
        return True


    def __eq__(self, other):
        """Returns if the Bundle are the same."""
        if not other.is_bundle():
            return False

        if self is other:
            return True

        index = 0
        for piece in self:
            # skip
            if len(piece) == 0:
                continue
            while len(other.bundle[index]) == 0:
                index += 1
                if index >= len(other.bundle):
                    return False

            if piece != other.bundle[index]:
                return False
            index += 1

        return True


    def __ne__(self, other):
        return not self.__eq__(other)


    def __bool__(self):
        return bool(self.bundle)


    def __contains__(self, other):
        return other in self.bundle


    def to_fragment(self, pos_lincol=True, filler=None, filler_mode=None):
        if not self:
            return None

        if filler is not None:
            return Fragment(self.bundle[0].filename, self.join(filler, filler_mode),
                            self.bundle[0].start_pos, self.bundle[-1].end_pos,
                            self.bundle[0].start_lincol, self.bundle[-1].end_lincol,
                            bool(self.bundle[0].start_lincol is not None))

        if len(self.bundle) == 1:
            return self.bundle[0]

        if self.is_complete(pos_lincol):
            return self.copy().merge_inner(pos_lincol).bundle[0]


    def to_bundle(self):
        return self


    def join(self, filler=None, filler_mode=None):
        if not self:
            return ''

        if not filler:
            return str(self)

        last = self.bundle[0].start_pos
        content = []
        for piece in self:
            if last != piece.start_pos:
                if filler_mode == "static":
                    content.append(filler)
                elif filler_mode == "extend":
                    content.append(filler[:piece.start_pos - last])
                    content.append(filler[-1] * (piece.start_pos - last - len(filler)))
                else: # repeat
                    content.append(filler * ((piece.start_pos - last) // len(filler)))
                    if len(filler) != 1:
                        content.append(filler[:(piece.start_pos - last) % len(filler)])
            content.append(str(piece))
            last = piece.end_pos

        return ''.join(content)


    def __str__(self):
        return ''.join([str(piece) for piece in self])


    def __repr__(self):
        return self.repr(bool(not(not self or self.bundle[0].end_lincol)), True, False)


    def repr(self, show_pos, show_filename=False, show_content=True):
        return '[' + ', '.join([piece.repr(show_pos, show_filename, show_content)
                               for piece in self]) + ']'


    def copy(self):
        return FragmentBundle(self.bundle.copy())
