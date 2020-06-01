
"""
util.fragment
~~~~~~~~~~~~~

Text line container.
"""

class Fragment():
    """A substring with positional information.

    fn -- absolute file path and name.
    content -- original text or replacement text as a list of strings.
    start_pos/_end -- start/end as absolute char position (to the start of the file).
    start_lincol/_end -- start/end as line/column number (0-based).
                         Each added content (list entry) is treated as a line.
    """
    __slots__ = ('fn', 'content', 'start_pos', 'end_pos', 'start_lincol', 'end_lincol')


    def __init__(self, fn, content, start_pos=None, end_pos=None,
                 start_lincol=None, end_lincol=None, use_lincol=True):
        """content is split into lines if use_lincol.
        starts defaults to zero (because the start_lincol can not be measured).
        ends are measured/derived from content if None.
        """
        self.fn = fn

        start_pos = int(start_pos) if start_pos is not None else 0
        end_pos = int(end_pos) if end_pos is not None else None

        if content is None:
            content = []
        elif isinstance(content, str):
            if use_lincol:
                content = [l for l in content.splitlines(keepends=True)]
            else:
                content = [content]
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


    def add_offset(self, offset_pos=None, offset_lincol=None):
        """Adds an offset to the location."""

        if offset_pos:
            self.start_pos += offset_pos
            self.end_pos += offset_pos
        if offset_lincol and self.start_lincol:
            if self.start_lincol[0] == self.end_lincol[0]:
                self.end_lincol = (self.end_lincol[0] + offset_lincol[0],
                                   self.end_lincol[1] + offset_lincol[1])
            else:
                self.end_lincol = (self.end_lincol[0] + offset_lincol[0], self.end_lincol[1])

            self.start_lincol = (self.start_lincol[0] + offset_lincol[0],
                                 self.start_lincol[1] + offset_lincol[1])

        return self


    def get_start(self, pos_lincol):
        return self.start_pos if pos_lincol else self.start_lincol


    def get_end(self, pos_lincol):
        return self.end_pos if pos_lincol else self.end_lincol


    def extend(self, new_content):
        """Adds lines to the content."""
        self.rermove_zero_len_end()

        if isinstance(new_content, str):
            self.content.append(new_content)
            self.end_pos += len(new_content)
            if self.end_lincol:
                self.end_lincol = (self.end_lincol[0] + 1, len(new_content))
        else:
            self.content.extend(new_content)
            self.end_pos += sum(map(len, new_content))

            if self.end_lincol:
                self.end_lincol = (self.end_lincol[0] + max(0, len(new_content) - 1),
                                   len(new_content[-1]) if len(new_content) != 0 else 0)

        return self


    def rermove_zero_len_end(self):
        """Removes zero length line starts."""
        if (len(self.content) != 0 and len(self.content[-1]) == 0 and
                self.start_lincol and self.start_lincol[1] == 0):
            if len(self.content) == 1:
                self.end_lincol = self.start_lincol
            else:
                self.end_lincol = (max(0, self.end_lincol[0] - 1), len(self.content[-2]))
            self.content = self.content[:-1]

        return self


    def combine(self, fg):
        """Combines two aligned fragments into one."""
        if not self.is_aligned(fg, True):
            return self

        if not self.end_lincol or not fg.end_lincol:
            self.content.extend(fg.content)
        else:
            if fg.start_lincol == fg.end_lincol:
                return self
            if self.is_aligned(fg, False):
                if self.end_lincol == fg.start_lincol:
                    if len(self.content) != 0:
                        self.content[-1] += fg.content[0]
                        if len(fg.content) != 1:
                            self.content.extend(fg.content[1:])
                    else:
                        self.content.extend(fg.content)
                else:
                    self.content.extend(fg.content)

        self.end_pos = fg.end_pos
        if fg.end_lincol:
            self.end_lincol = fg.end_lincol

        return self


    def is_aligned(self, fg, pos_lincol):
        """Check if two  fragments are aligned."""
        if pos_lincol or not self.end_lincol or not fg.start_lincol:
            if self.end_pos == fg.start_pos:
                return True
        else:
            if self.end_lincol == fg.start_lincol:
                return True
            if ((self.end_lincol == self.start_lincol or self.content[-1][-1] == "\n") and
                    self.end_lincol[0] + 1 == fg.start_lincol[0] and fg.start_lincol[1] == 0):
                return True

        return self


    def slice_match_obj(self, match_obj, groupno, right_inner=False, output_zero=True):
        """Slice by span defined by a regex match object."""
        if len(match_obj.groups()) >= groupno and match_obj.group(groupno) is not None:
            at_start = self.loc_to_abs(match_obj.start(groupno))
            at_end = self.loc_to_abs(match_obj.end(groupno))

            return self.slice(at_start, at_end, right_inner, output_zero)


    def slice(self, at_start, at_end=None, right_inner=False, output_zero=True):
        """Cut span."""

        start_pos_abs = None
        if isinstance(at_start, int):
            start_pos_abs = at_start
            at_start = self.pos_to_lincol(at_start, True)
            if at_end is not None:
                at_end = self.pos_to_lincol(at_end, True)

        at_start_rel = self.loc_to_rel(at_start)
        if at_end is not None:
            at_end_rel = self.loc_to_rel(at_end)

        start_rel = (0, 0)
        if self.end_lincol is not None:
            end_rel = self.loc_to_rel(self.end_lincol)
        else:
            end_rel = self.loc_to_rel(self.pos_to_lincol(self.end_pos, True))

        cuts = []
        if at_end is None:
            if not right_inner:
                cuts.append((start_rel, at_start_rel, self.start_pos, self.start_lincol))
            cuts.append((at_start_rel, end_rel, start_pos_abs, at_start))
        else:
            if not right_inner:
                cuts.append((start_rel, at_start_rel, self.start_pos, self.start_lincol))
            cuts.append((at_start_rel, at_end_rel, start_pos_abs, at_start))
            if not right_inner:
                cuts.append((at_end_rel, end_rel, None, at_end))

        out = []
        for start, end, pos_abs, lincol_abs in cuts:
            if start <= start_rel and end <= start_rel:
                fg = self.copy().clear(True) if output_zero else None
            elif end >= end_rel and start <= start_rel:
                fg = self.copy()
            elif start >= end_rel:
                fg = self.copy().clear(False) if output_zero else None
            elif start == end and not output_zero:
                fg = None
            else:
                if start == end:
                    cont = []
                else:
                    cont = [self.content[start[0]][start[1]:]]
                    if start[0] == end[0]:
                        cont = cont[-1][:end[1] - start[1]]
                    else:
                        if start[0] + 1 < len(self.content):
                            cont.extend(self.content[start[0]+1:end[0]])
                        cont.extend([self.content[end[0]][:end[1]]])

                if pos_abs is None:
                    if start_pos_abs is not None:
                        pos_abs = start_pos_abs
                    else:
                        pos_abs = self.lincol_to_pos(at_start, True)

                lincol_abs = lincol_abs if self.start_lincol else None
                fg = Fragment(self.fn, cont, pos_abs, start_lincol=lincol_abs)
                start_pos_abs = fg.end_pos

            out.append(fg)

        return out[0] if len(out) == 1 else tuple(out)


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
            line = Fragment(self.fn, line_str, start_pos, start_lincol=start_lincol)
            yield line
            start_pos = line.end_pos

        if buffered:
            yield None


    def isspace(self):
        """The content is empty or contains only whitespaces."""
        if len(self.content) == 0:
            return True

        for line_str in self.content:
            if not line_str.isspace():
                return False

        return True


    def loc_to_abs(self, loc_rel):
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


    def loc_to_rel(self, loc_abs):
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


    def lincol_to_pos(self, lincol, keep_bounds=False):
        """Convert a lincol location to a pos location."""

        lincol = self.loc_to_rel(lincol)
        if lincol < (0, 0):
            if keep_bounds:
                return self.start_pos
            return None

        cursor = 0
        for index, line in enumerate(self.content):
            if lincol[0] == index:
                return self.loc_to_abs(cursor + lincol[1])

            cursor += len(line)

        if keep_bounds:
            return self.loc_to_abs(cursor)


    def pos_to_lincol(self, pos, keep_bounds=False):
        """Convert a pos location to a lincol location."""

        pos = self.loc_to_rel(pos)
        if pos < 0:
            if keep_bounds:
                return self.start_lincol if self.start_lincol else (0, 0)
            return None

        cursor = 0
        for index, line in enumerate(self.content):
            # favor next line start over current end
            if pos >= cursor and pos - cursor < len(line):
                return self.loc_to_abs((index, pos - cursor))

            cursor += len(line)

        if keep_bounds:
            if len(self.content) == 0:
                return self.loc_to_abs((0, 0))

            return self.loc_to_abs((len(self.content) - 1, len(self.content[-1])))


    def is_in_span(self, loc, include_start=True, include_end=True):
        """Check if the location is between start and end."""

        pos_lc = bool(isinstance(loc, int))
        self_start = self.get_start(pos_lc)
        self_end = self.get_end(pos_lc)

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


    def __contains__(self, term):
        """Search content list."""
        return term in self.content


    def __bool__(self):
        """Returns is not None."""
        return True


    def __eq__(self, other):
        """Returns if the Fragment are the same."""
        if type(other) != Fragment:
            return False

        if self is other:
            return True

        for prop in self.__slots__:
            if getattr(self, prop) != getattr(other, prop):
                return False

        return True


    def __ne__(self, other):
        """Returns if the Fragment are not same."""
        return not self.__eq__(other)


    def __len__(self):
        """Returns the content char length."""
        return sum(map(len, self.content))


    def span_len(self):
        """Returns the span char length."""
        return self.end_pos - self.start_pos


    def __iter__(self):
        """Iterate over content list."""
        yield from self.content


    def __str__(self):
        """Returns the joined content list."""
        return str(''.join(self.content))


    def __repr__(self):
        return self.repr(bool(not self.end_lincol), True, False)


    def repr(self, show_pos, show_fn=False, show_content=True):
        """Shows the content with the location at start and end."""
        fn = self.fn + ":" if show_fn else ''
        if show_pos:
            start = str(self.get_start(show_pos))
            end = str(self.get_end(show_pos))
        else:
            start = '{0},{1}'.format(*self.get_start(show_pos))
            end = '{0},{1}'.format(*self.get_end(show_pos))

        if show_content:
            return '(' + fn + start + ')' + str(self).replace('\n', '¶') + '(' + end + ')'

        return fn + start + '-' + end


    def copy(self):
        """Returns a deep copy."""
        return Fragment(self.fn, self.content.copy(), self.start_pos,
                        self.end_pos, self.start_lincol, self.end_lincol)
