
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


    def to_fragment(self, filler=None):
        return self


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


    def combine(self, fg, check_align=True):
        """Combines two aligned fragments into one."""
        if check_align and not self.is_aligned(fg, True):
            return self

        if not self.end_lincol or not fg.end_lincol:
            self.content.extend(fg.content)
        else:
            if fg.start_lincol == fg.end_lincol:
                return self
            if not check_align or self.is_aligned(fg, False):
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

        return False


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
        if not right_inner:
            cuts.append((start_rel, at_start_rel, self.start_pos, self.start_lincol))
        if at_end is None:
            cuts.append((at_start_rel, end_rel, start_pos_abs, at_start))
        else:
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
            line = Fragment(self.fn, line_str, start_pos, start_lincol=start_lincol)
            yield line

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


    def replace(self, new_content, open_end=True):
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


    def is_empty(self):
        return False


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
                # one of the content is same list or str then compare the effective
                if (prop != "content" or
                        type(self.content) != type(other.content) or
                        ''.join(self.content) != ''.join(other.content)):
                    return False

        return True


    def __ne__(self, other):
        """Returns if the Fragment are not same."""
        return not self.__eq__(other)


    def __len__(self):
        """Returns the content char length."""
        return sum(map(len, self.content))


    def span_len(self, pos_lincol):
        """Returns either the span char length or
           the line span and column span of the first and last line."""
        if pos_lincol:
            return self.end_pos - self.start_pos

        line_span = self.end_lincol[0] - self.start_lincol[0]
        if line_span == 0 and len(self.content) != 0:
            line_span = 1
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
                        self.end_pos, self.start_lincol, self.end_lincol,
                        bool(self.start_lincol is not None))


class FragmentBundle():
    """A list of Fragments. sorted, non overlapping."""

    __slots__ = ('bundle',)


    def __init__(self, bundle=None):
        """bundle -- a list of Fragments."""
        if bundle is None:
            bundle = []

        self.bundle = bundle


    def get_fn(self):
        return self.bundle[0].fn if self else None

    def set_fn(self, value):
        for fg in self:
            fg.fn = value

    fn = property(get_fn, set_fn)


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


    def to_fragment(self, pos_lincol=True, filler=None):
        if not self:
            return None

        if filler is not None:
            return Fragment(self.bundle[0].fn, self.join(filler),
                            self.bundle[0].start_pos, self.bundle[-1].end_pos,
                            self.bundle[0].start_lincol, self.bundle[-1].end_lincol,
                            bool(self.bundle[0].start_lincol is not None))

        if len(self.bundle) == 1:
            return self.bundle[0]

        out = None
        for fg in self:
            if not out:
                out = fg
                continue
            if not out.is_aligned(fg, pos_lincol):
                return None
            out.combine(fg, check_align=False)

        return out


    def join(self, filler=None):
        if not self:
            return ''

        if not filler:
            return str(self)

        last = self.bundle[0].start_pos
        content = []
        for fg in self:
            if last != fg.start_pos:
                content.append(filler * ((fg.start_pos - last) // len(filler)))
                if len(filler) != 1:
                    content.append(filler[:(fg.start_pos - last) % len(filler)])
            content.append(str(fg))
            last = fg.end_pos

        return ''.join(content)


    def add_offset(self, offset_pos=None, offset_lincol=None):
        for fg in self:
            fg.add_offset(offset_pos, offset_lincol)
        return self


    def get_start(self, pos_lincol):
        return self.start_pos if pos_lincol else self.start_lincol


    def get_end(self, pos_lincol):
        return self.end_pos if pos_lincol else self.end_lincol


    def extend(self, new_content):
        if not self:
            return self
        self.bundle[-1].extend(new_content)
        return self


    def rermove_zero_len_end(self):
        if not self:
            return self
        if len(self.bundle[-1]) == 0:
            self.bundle = self.bundle[0:-1]
        return self


    def combine(self, bd, pos_lincol=True, merge=False):
        """Merge -- combine last and first if aligned."""
        if merge and self and bd:
            if self.is_aligned(bd, pos_lincol):
                self.bundle[-1].combine(bd.bundle[0])
                self.bundle.extend(bd.bundle[1:])
        else:
            self.bundle.extend(bd.bundle)
        return self


    def merge_inner(self, pos_lincol=True):
        """Combine aligning Fragments within bundle."""
        prev = None
        new_bundle = []
        for fg in self:
            print(type(fg))
            if prev and prev.is_aligned(fg, pos_lincol):
                prev.combine(fg)
            else:
                new_bundle.append(fg)
                prev = fg
        self.bundle = new_bundle
        return self


    def is_aligned(self, bd, pos_lincol):
        if not self or not bd:
            return True

        return self.bundle[-1].is_aligned(bd.bundle[0], pos_lincol)


    def slice_match_obj(self, match_obj, groupno, right_inner=False, output_zero=True):
        """relative to first."""
        if not self:
            return self
        if len(match_obj.groups()) >= groupno and match_obj.group(groupno) is not None:
            at_start = self.loc_to_abs(match_obj.start(groupno))
            at_end = self.loc_to_abs(match_obj.end(groupno))

            return self.slice(at_start, at_end, right_inner, output_zero)


    def slice(self, at_start, at_end=None, right_inner=False, output_zero=True):
        if not self:
            if right_inner:
                return None
            if not at_end:
                return None, None
            return None, None, None

        if at_end is not None and at_end < at_start:
            at_end = at_start

        pos_lincol = bool(isinstance(at_start, int))
        cuts = []
        at_start_index = self.index_clip(at_start, False)
        if not right_inner:
            cuts.append(((0, True), self.bundle[0].get_start(pos_lincol),
                         at_start_index, at_start))
        if not at_end:
            cuts.append((at_start_index, at_start,
                         (max(0, len(self.bundle) - 1), True),
                         self.bundle[-1].get_end(pos_lincol)))
        else:
            at_end_index = self.index_clip(at_end, True)
            cuts.append((at_start_index, at_start, at_end_index, at_end))
            if not right_inner:
                cuts.append((at_end_index, at_end,
                             (max(0, len(self.bundle) - 1), True),
                             self.bundle[-1].get_end(pos_lincol)))

        out = []
        for index_start, start, index_end, end in cuts:
            if start <= self.get_start(pos_lincol) and end <= self.get_start(pos_lincol):
                bd = self.bundle[0].clear(True) if output_zero else None
            elif end >= self.get_end(pos_lincol) and start <= self.get_start(pos_lincol):
                bd = self.copy()
            elif start >= self.get_end(pos_lincol):
                bd = self.bundle[-1].clear(False) if output_zero else None
            elif start == end and not output_zero:
                bd = None
            else:
                bd = FragmentBundle()
                if index_start[1]:
                    if index_start[0] == index_end[0]:
                        fg_first = self.bundle[index_start[0]].slice(start, end, True)
                    else:
                        fg_first = self.bundle[index_start[0]].slice(start, right_inner=True)

                    if fg_first:
                        bd.bundle.append(fg_first)
                if index_start[0] == index_end[0] and not index_start[1] and not index_end[1]:
                    fgs_inner = self.bundle[index_start[0]]
                    bd.bundle.append(fgs_inner.copy())
                elif index_start[0] != index_end[0]:
                    if not index_start[1] and not index_end[1]:
                        fgs_inner = self.bundle[index_start[0]]
                        bd.bundle.append(fgs_inner.copy())
                    else:
                        for fg in self.bundle[min(len(self.bundle), index_start[0] + 1):index_end[0]]:
                            bd.bundle.append(fg.copy())
                    if index_end[1]:
                        fg_last = self.bundle[index_end[0]].slice(self.bundle[index_end[0]]
                                                                  .get_start(pos_lincol), end, True)
                        if fg_last:
                            bd.bundle.append(fg_last)

            out.append(bd)

        return out[0] if len(out) == 1 else tuple(out)


    def splitlines(self, buffered=False):
        for fg in self:
            yield from fg.splitlines()
        if buffered:
            yield None


    def reversed_splitlines(self, buffered=False):
        for fg in self:
            yield from fg.reversed_splitlines()
        if buffered:
            yield None


    def isspace(self):
        if not self:
            return True

        for fg in self:
            if not fg.isspace():
                return False

        return True


    def loc_to_abs(self, loc_rel, filled=False):
        if not self:
            return None

        if isinstance(loc_rel, int):
            cursor = 0
            prev = None
            for fg in self:
                if filled and prev is not None:
                    if loc_rel <= cursor + fg.start_pos - prev:
                        return prev + loc_rel - cursor
                    cursor += fg.start_pos - prev
                if loc_rel <= cursor + fg.span_len(True):
                    return fg.loc_to_abs(loc_rel - cursor)
                cursor += fg.span_len(True)
                prev = fg.end_pos

        else:
            cursor = 1
            prev = None
            for fg in self:
                if filled and prev is not None:
                    cursor += fg.start_lincol[0] - prev
                if loc_rel[0] <= cursor + len(fg.content):
                    if cursor + self.start_lincol[0] == fg.start_lincol[0]:
                        return fg.loc_to_abs((loc_rel[0] - cursor - 1,
                                              loc_rel[1] - fg.start_lincol[1]))

                    return fg.loc_to_abs((loc_rel[0] - cursor - 1, loc_rel[1]))
                cursor += len(fg.content)
                prev = fg.end_lincol[0]


    def loc_to_rel(self, loc_abs, filled=False):
        if not self:
            return None

        if isinstance(loc_abs, int):
            for fg in self:
                if fg.is_in_span(loc_abs):
                    if filled:
                        return self.bundle[0].loc_to_rel(loc_abs)
                    else:
                        cursor = 0
                        for rec in self:
                            if rec is not fg:
                                cursor += rec.span_len(True)
                            else:
                                break
                        return cursor + loc_abs - fg.start_pos
        else:
            for fg in self:
                if fg.is_in_span(loc_abs):
                    if filled:
                        return self.bundle[0].loc_to_rel(loc_abs)

                    cursor = 0
                    for rec in self:
                        if rec is not fg:
                            cursor += len(rec.content)
                        else:
                            break
                    rel = fg.loc_to_rel(loc_abs)
                    return (rel[0] + cursor, rel[1])


    def lincol_to_pos(self, lincol, keep_bounds=False):
        if not self:
            return None

        if lincol < self.start_lincol:
            if keep_bounds:
                return self.start_pos
            return None

        for fg in self:
            if fg.is_in_span(lincol):
                return fg.lincol_to_pos(lincol, keep_bounds)

        if keep_bounds:
            return self.end_pos


    def pos_to_lincol(self, pos, keep_bounds=False):
        if not self:
            return None

        if pos < self.start_pos:
            if keep_bounds:
                return self.start_lincol
            return None

        for fg in self:
            if fg.is_in_span(pos):
                return fg.pos_to_lincol(pos, keep_bounds)

        if keep_bounds:
            return self.end_lincol


    def is_in_span(self, loc, include_start=True, include_end=True):
        """include for each."""
        if not self:
            return False

        for fg in self:
            if fg.is_in_span(loc, include_start, include_end):
                return True

        return False


    def index_at(self, loc, include_start=True, include_end=True):
        """Return index of the first Fragment which has the loc within it's span."""
        for index, fg in enumerate(self):
            if fg.is_in_span(loc, include_start, include_end):
                return index


    def index_clip(self, loc, prev_next):
        """Return index of the Fragment which has the loc within it's span or
           when in between the previous or next Fragment."""
        pos_lincol = bool(isinstance(loc, int))
        for index, fg in enumerate(self):
            if loc < fg.get_start(pos_lincol):
                return max(0, index - 1) if prev_next else index, False
            if fg.is_in_span(loc):
                return index, True

        return index, False


    def replace(self, new_content, open_end=True):
        """Map list entry to entry in bundle."""
        if not self:
            return self

        for fg, content in zip(self, new_content):
            fg.replace(content)

        for fg in self.bundle[len(new_content):]:
            fg.replace("")

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
        for index, fg in enumerate(self):
            if prev_end < len(new_content):
                l = len(fg) if pos_lincol else len(fg.content)
                if open_end and index == len(self.bundle) - 1:
                    fg.replace_fill(new_content[prev_end:], open_end=True)
                else:
                    fg.replace_fill(new_content[prev_end:prev_end + l])
                    prev_end += l
            else:
                fg.replace_fill("")
        return self


    def clear(self, start_end):
        if not self:
            return self
        if start_end:
            self.bundle = [self.bundle[0].clear(start_end)]
        else:
            self.bundle = [self.bundle[-1].clear(start_end)]

        return self


    def is_empty(self):
        """Return if the Bundle list is empty."""
        return len(self.bundle) == 0


    def __contains__(self, term):
        if not self:
            return False

        for fg in self:
            if term in fg:
                return True

        return False


    def __bool__(self):
        return bool(self.bundle)


    def __eq__(self, other):
        """Returns if the Bundle are the same."""
        if type(other) != FragmentBundle:
            return False

        if self is other:
            return True

        index = 0
        for fg in self:
            # skip
            if len(fg) == 0:
                continue
            while len(other.bundle[index]) == 0:
                index += 1
                if index >= len(other.bundle):
                    return False

            if fg != other.bundle[index]:
                return False
            index += 1

        return True


    def __ne__(self, other):
        return not self.__eq__(other)


    def __len__(self):
        if not self:
            return 0

        return sum(len(fg) for fg in self)


    def span_len(self, pos_lincol):
        if not self:
            return 0 if pos_lincol else (0, 0)

        if pos_lincol:
            return self.bundle[-1].end_pos - self.bundle[0].start_pos

        line_span = self.bundle[-1].end_lincol[0] - self.bundle[0].start_lincol[0]
        if line_span == 0 and len(self.bundle[0].content) != 0:
            line_span = 1
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
        for fg in self:
            if len(fg.content) == 0:
                continue
            fg_size = self.bundle[0].size(pos_lincol)
            line_len += fg_size[0]
            if col_min is None:
                col_min = fg.start_lincol[1]
            if len(fg.content) == 1:
                col_min = min(col_min, fg.start_lincol[1])
                col_len = max(col_len, fg_size[1] + fg.start_lincol[1])
            else:
                col_min = min(col_min, 0)
                col_len = max(col_len, fg_size[1])

        return (line_len, col_len - col_min)


    def __iter__(self):
        """Iterate over bundle list."""
        yield from self.bundle


    def __str__(self):
        return str(''.join([str(fg) for fg in self]))


    def __repr__(self):
        return self.repr(bool(not(not self or self.bundle[0].end_lincol)), True, False)


    def repr(self, show_pos, show_fn=False, show_content=True):
        return str(', '.join([fg.repr(show_pos, show_fn, show_content) for fg in self]))


    def copy(self):
        return FragmentBundle(self.bundle.copy())
