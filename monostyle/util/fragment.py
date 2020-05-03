
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


    def __init__(self, fn, content, start_pos, end_pos, start_lincol=None, end_lincol=None):
        self.fn = fn
        if isinstance(content, str):
            self.content = [str(content)]
        else:
            self.content = content.copy() if content else content

        self.start_pos = int(start_pos)
        self.end_pos = int(end_pos)

        self.start_lincol = start_lincol
        self.end_lincol = end_lincol


    def from_org_len(fn, content, start_pos, offset_pos=0, start_lincol=None, offset_lincol=(0, 0)):
        """Constructor from content length."""
        end_lincol = None

        if isinstance(content, str):
            end_pos = start_pos + len(content)
            if start_lincol:
                end_lincol = (start_lincol[0], start_lincol[1] + len(content))
        else:
            end_pos = start_pos
            line = ""
            for line in content:
                end_pos += len(line)

            if start_lincol:
                if len(content) == 1:
                    end_lincol = (start_lincol[0], start_lincol[1] + len(line))
                else:
                    end_lincol = (start_lincol[0] + max(0, len(content) - 1), len(line))

        return Fragment(fn, content, start_pos, end_pos,
                        start_lincol, end_lincol).add_offset(offset_pos, offset_lincol)


    def from_initial(fn, content, use_lincol=True):
        """Constructor from at zero and content length."""
        if isinstance(content, str):
            content = [l for l in content.splitlines(keepends=True)]
        start_lincol = (0, 0) if use_lincol else None
        return Fragment.from_org_len(fn, content, 0, start_lincol=start_lincol)


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


    def slice_match_obj(self, match_obj, groupno, right_inner=False):
        """Slice by span defined by a regex match object."""
        if len(match_obj.groups()) >= groupno and match_obj.group(groupno) is not None:
            at_start = self.loc_to_abs(match_obj.start(groupno))
            at_end = self.loc_to_abs(match_obj.end(groupno))

            return self.slice(at_start, at_end, right_inner)


    def slice(self, at_start, at_end=None, right_inner=False):# is_abs
        """Cut span."""
        if isinstance(at_start, int):
            # keep in bounds
            if at_start < self.start_pos:
                at_start = self.start_pos

            at_start_rel = self.loc_to_rel(at_start)
            if at_end is None:
                if at_start_rel == 0:
                    if not right_inner:
                        return None, self # copy?

                    return self

                if at_start >= self.end_pos:
                    if not right_inner:
                        return self, None

                    return None
            else:
                if at_end < at_start:
                    at_end = at_start

                # keep in bounds
                if at_end > self.end_pos:
                    at_end = self.end_pos

                at_end_rel = self.loc_to_rel(at_end)

                if at_end_rel == 0:
                    fg = Fragment(self.fn, [], self.start_pos, self.start_pos,
                                  self.start_lincol, self.start_lincol)
                    if not right_inner:
                        return None, fg, self

                    return fg

            cursor = 0
            on_start = True
            for index, line in enumerate(self.content):
                if on_start and at_start_rel >= cursor and at_start_rel <= cursor + len(line):
                    at_start_rel_lincol = (index, at_start_rel - cursor)
                    if not right_inner:
                        a_cont = self.content[:at_start_rel_lincol[0]]
                        a_cont.append(line[:at_start_rel_lincol[1]])
                        a = Fragment.from_org_len(self.fn, a_cont, self.start_pos,
                                                  start_lincol=self.start_lincol)
                    b_cont = [line[at_start_rel_lincol[1]:]]
                    at_start_abs_lincol = self.loc_to_abs(at_start_rel_lincol)
                    if at_end is None:
                        b_cont.extend(self.content[at_start_rel_lincol[0]+1:])
                        at_start_abs_lincol_set = at_start_abs_lincol if self.start_lincol else None
                        b = Fragment.from_org_len(self.fn, b_cont, at_start,
                                                  start_lincol=at_start_abs_lincol_set)
                        if not right_inner:
                            return a, b

                        return b

                    on_start = False

                if (at_end is not None and not on_start and
                        at_end_rel >= cursor and at_end_rel <= cursor + len(line)):
                    at_end_rel_lincol = (index, at_end_rel - cursor)
                    if at_start_rel_lincol[0] == at_end_rel_lincol[0]:
                        b_cont = [b_cont[0][:at_end_rel_lincol[1] - at_start_rel_lincol[1]]]
                    else:
                        b_cont.extend(self.content[at_start_rel_lincol[0]+1:at_end_rel_lincol[0]])
                        b_cont.extend([line[:at_end_rel_lincol[1]]])
                    at_start_abs_lincol_set = at_start_abs_lincol if self.start_lincol else None
                    b = Fragment.from_org_len(self.fn, b_cont, at_start,
                                              start_lincol=at_start_abs_lincol_set)
                    if not right_inner:
                        c_cont = [line[at_end_rel_lincol[1]:]]
                        if at_end_rel_lincol[0] < len(self.content) - 1:
                            c_cont.extend(self.content[at_end_rel_lincol[0]+1:])
                        at_end_abs_lincol = self.loc_to_abs(at_end_rel_lincol)
                        at_end_abs_lincol_set = at_end_abs_lincol if self.end_lincol else None
                        c = Fragment.from_org_len(self.fn, c_cont, at_end,
                                                  start_lincol=at_end_abs_lincol_set)
                        return a, b, c

                    return b

                cursor += len(line)
        else:
            # todo keep in bounds
            at_start_rel = self.loc_to_rel(at_start)
            if at_end is None:
                if at_start_rel[0] > len(self.content) - 1:
                    if not right_inner:
                        return self, None

                    return None
                if at_start_rel[0] < 0:
                    if not right_inner:
                        return None, self

                    return self
            else:
                if (at_end[0] < at_start[0] or
                        (at_end[0] == at_start[0] and at_end[1] < at_start[1])):
                    at_end = at_start

                at_end_rel = self.loc_to_rel(at_end)
                if at_end_rel[0] < 0:
                    if not right_inner:
                        return None, None, self

                    return None

            a_cont = self.content[:at_start_rel[0]]
            a_cont.append(self.content[at_start_rel[0]][:at_start_rel[1]])
            a = Fragment.from_org_len(self.fn, a_cont, self.start_pos,
                                      start_lincol=self.start_lincol)

            if at_end is None:
                b_cont = [self.content[at_start_rel[0]][at_start_rel[1]:]]
                if at_start_rel[0] + 1 < len(self.content):
                    b_cont.extend(self.content[at_start_rel[0]+1:])
                b = Fragment.from_org_len(self.fn, b_cont, a.end_pos, start_lincol=at_start)

                if not right_inner:
                    return a, b

                return b

            if at_start_rel[0] == at_end_rel[0]:
                b_cont = [self.content[at_start_rel[0]][at_start_rel[1]:at_end_rel[1]]]
            else:
                b_cont = [self.content[at_start_rel[0]][at_start_rel[1]:]]
                b_cont.extend(self.content[at_start_rel[0]+1:at_end_rel[0]])
                b_cont.extend([self.content[at_end_rel[0]][:at_end_rel[1]]])
            b = Fragment.from_org_len(self.fn, b_cont, a.end_pos, start_lincol=at_start)
            if not right_inner:
                c_cont = [self.content[at_end_rel[0]][at_end_rel[1]:]]
                if at_end_rel[0] < len(self.content) - 1:
                    c_cont.extend(self.content[at_end_rel[0]+1:])
                c = Fragment.from_org_len(self.fn, c_cont, b.end_pos, start_lincol=at_end)
                return a, b, c

            return b


    def splitlines(self, buffered=False):
        """Split the content into line Fragments per list item."""
        offset_pos = self.start_pos
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
            line = Fragment.from_org_len(self.fn, line_str, 0, offset_pos, start_lincol)
            yield line
            offset_pos = line.end_pos

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


    def lincol_to_pos(self, lincol):
        """Convert a lincol location to a pos location."""
        # todo bounds
        cursor = 0
        for index, line in enumerate(self.content):
            if lincol[0] == index:
                return cursor + lincol[1]

            cursor += len(line)


    def pos_to_lincol(self, pos):
        """Convert a pos location to a lincol location."""

        cursor = 0
        for index, line in enumerate(self.content):
            # favor next line start over current end
            if pos >= cursor and pos - cursor < len(line):
                return (index, pos - cursor)

            cursor += len(line)


    def is_in_span(self, loc, include_start=True, include_end=True):
        """Check if the location is between start and end."""

        if isinstance(loc, int):
            if self.start_pos == self.end_pos:
                if include_start and include_end and loc == self.start_pos:
                    return True
            else:
                if ((include_start and loc == self.start_pos) or
                        (include_end and loc == self.end_pos)):
                    return True

            if loc > self.start_pos and loc < self.end_pos:
                return True
        else:
            if self.start_lincol == self.end_lincol:
                if include_start and include_end and loc == self.start_lincol:
                    return True
            else:
                if ((include_start and loc == self.start_lincol) or
                        (include_end and loc == self.end_lincol)):
                    return True

            if (((loc[0] == self.start_lincol[0] and loc[1] > self.start_lincol[1]) or
                    loc[0] > self.start_lincol[0]) and
                    (loc[0] < self.end_lincol[0] or
                     (loc[0] == self.end_lincol[0] and loc[1] < self.end_lincol[1]))):
                return True

        return False


    def clear(self, start_end):
        """Remove content. Turn into zero-length Fragment at start or end."""
        self.content.clear()
        if start_end:
            self.start_pos = self.end_pos
            self.start_lincol = self.end_lincol
        else:
            self.end_pos = self.start_pos
            self.end_lincol = self.start_lincol

        return self


    def __contains__(self, term):
        """Search content list."""
        return term in self.content


    def __bool__(self):
        """Returns is not None."""
        return True


    def __eq__(self, other):
        """Returns if the Fragment are the same."""
        if not isinstance(other, Fragment):
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
        return self.repr(True, True, False)


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
