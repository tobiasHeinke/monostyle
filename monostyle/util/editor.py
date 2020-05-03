
"""
util.editor
~~~~~~~~~~~

Text editing utilities.
"""

from monostyle.util.fragment import Fragment


class Editor:
    """Text editing.

    fg -- Fragment as a virtual input used to apply edits on.
    """

    def __init__(self, fg):
        self.fg = fg
        self._changes = []
        self._status = True


    def form_file(self, fn):
        return Editor(Fragment(fn, None, 0, 0))


    def __bool__(self):
        return self._status


    def _read(self):
        """Return stored text or read it from the file."""
        if self.fg.content is None:
            try:
                with open(self.fg.fn, "r", encoding="utf-8") as f:
                    text = f.read()

            except (IOError, OSError) as err:
                print("{0}: cannot read: {1}".format(self.fg.fn, err))
                return None

            text = [l for l in text.splitlines(keepends=True)]
            text_src = Fragment.from_org_len(self.fg.fn, text, 0, start_lincol=(0, 0))
        else:
            text_src = self.fg

        return text_src


    def _write(self, text_dst):
        """Write output to the file."""
        try:
            with open(self.fg.fn, "w", encoding="utf-8") as f:
                f.write(str(text_dst))

            return text_dst

        except (IOError, OSError):
            self._status = False
            return None


    def add(self, fg):
        """Add replacement."""
        self._changes.append(fg)


    def apply(self, virtual=False, pos_lc=True):
        """Apply the edits to the input text.

        virtual -- return the output text or write it to the file.
        """

        text_src = self._read()
        if len(self._changes) == 0:
            return text_src

        self._remove_doubles()
        self._changes.sort(key=lambda ent: ent.get_start(pos_lc))
        if not self._check_integrity(pos_lc):
            return None

        text_dst = Fragment(text_src.fn, [], text_src.start_pos, text_src.start_pos,
                            text_src.start_lincol, text_src.start_lincol)
        after = text_src
        for ent in self._changes:
            before, _, after = after.slice(ent.get_start(pos_lc), ent.get_end(pos_lc))

            if before:
                text_dst.combine(before)

            text_dst.combine(ent)

        if after:
            text_dst.combine(after)

        self._changes.clear()
        if virtual:
            return text_dst

        return self._write(text_dst)


    def _remove_doubles(self):
        """Remove doublicated entries."""
        new_changes = []
        for ent in self._changes:
            for ent_new in new_changes:
                if ent == ent_new:
                    break
            else:
                new_changes.append(ent)

        self._changes = new_changes


    def _check_integrity(self, pos_lc):
        """Check for overlaps of the start to end span."""
        prev = None
        for ent in self._changes:
            if prev:
                if ent.is_in_span(prev.get_start(pos_lc)) or ent.is_in_span(prev.get_end(pos_lc)):
                    self._status = False
                    break

            prev = ent

        return self._status


    # Adapted from:
    # https://developer.blender.org/diffusion/BM/browse/trunk/blender_docs/tools_rst/rst_helpers/__init__.py

    def iter_edit(self, find_re):
        """Iterate over the text with a reg exp.
        Alteration to the yielded content of the list container is detected within the for-loop.

        find_re -- a reg exp pattern.
        """
        import re

        text_src = self._read()

        for m in re.finditer(find_re, str(text_src)):
            ls_orig = []
            # pack into container
            if len(m.groups()) == 0:
                ls_orig = list(m.group(0))
            else:
                ls_orig = list(m.groups())
            # store copy
            ls = ls_orig[:]
            yield ls
            # detect alterations
            if ls != ls_orig:
                self.add(Fragment(self.fg.fn, ''.join(ls), m.start(),
                                  m.end()).add_offset(text_src.start_pos))


    def is_in_fg(self, loc):
        for ent in self._changes:
            if ent.is_in_span(loc):
                return True

        return False

    def __iter(self):
        for ent in self._changes:
            yield ent


class EditorSession:
    """Session with one editor per file."""

    def __init__(self):
        self._editor_stack = []
        # Store the index of the last accessed editor for performance.
        self._last_index = None
        self._status = True


    def __bool__(self):
        return self._status


    def add(self, fg):
        if (self._last_index is not None and
                self._editor_stack[self._last_index].fn == fg.fn):
            self._editor_stack[self._last_index].add(fg)
        else:
            for index, ed in enumerate(reversed(self._editor_stack)):
                if ed.fn == fg.fn:
                    ed.add(fg)
                    self._last_index = len(self._editor_stack) - 1 - index
                    break
            else:
                ed = Editor(fg.fn)
                ed.add(fg)
                self._editor_stack.append(ed)
                self._last_index = len(self._editor_stack) - 1


    def apply(self, pos_lc=True):
        for ed in self._editor_stack:
            ed.apply(False, pos_lc)
            if not ed:
                print("Editor error: overlap in " + ed.fn)
                self._status = False

        self._editor_stack.clear()


class FNEditor:
    """File renaming session with SVN."""

    def __init__(self):
        self._changes = []
        self._status = True


    def __bool__(self):
        return self._status


    def add(self, fg):
        self._changes.append(fg)


    def apply(self, virtual, pos_lc=True):
        import monostyle.svn_inter

        if len(self._changes) == 0:
            return True

        self._remove_doubles()
        self._changes.sort(key=lambda ent: (ent.fn, ent.get_start(pos_lc)))
        if not self._check_integrity_replace(pos_lc):
            return None
        self._replace(pos_lc)

        if not self._check_integrity_join():
            return None
        self._join()

        if not self._check_existence():
            return None
        for ent in self._changes:
            if virtual:
                print(ent.fn, "->", str(ent))
            else:
                monostyle.svn_inter.svn_move(ent.fn, str(ent))

        self._changes.clear()


    def _remove_doubles(self):
        """Remove doublicated entries."""
        new_changes = []
        for ent in self._changes:
            for ent_new in new_changes:
                if ent == ent_new:
                    break
            else:
                new_changes.append(ent)

        self._changes = new_changes


    def _replace(self, pos_lc):
        """Apply replacement changes with same fn."""

        stack_join = []
        text_dst = None
        after = None
        is_first = True
        for ent in self._changes:
            if not is_first and ent.fn != text_dst.fn:
                if after:
                    text_dst.combine(after)

                stack_join.append(text_dst)
                is_first = True

            if is_first:
                text_dst = Fragment(ent.fn, [], 0, 0)
                after = Fragment.from_org_len(ent.fn, ent.fn, 0)
                is_first = False

            before, _, after = after.slice(ent.get_start(pos_lc), ent.get_end(pos_lc))

            if before:
                text_dst.combine(before)

            text_dst.combine(ent)

        if after:
            text_dst.combine(after)

        stack_join.append(text_dst)
        self._changes = stack_join


    def _join(self):
        """Join chain of changes."""

        stack_join = []
        for ent in self._changes:
            for rec in stack_join:
                if ent.fn == str(rec):
                    rec.content = ent.content
                    break
            else:
                stack_join.append(ent)

        self._changes = stack_join


    def _check_integrity_replace(self, pos_lc):
        """Check for overlaps of the start to end span."""
        prev = None
        for ent in self._changes:
            if prev and prev.fn == ent.fn:
                if ent.is_in_span(prev.get_start(pos_lc)) or ent.is_in_span(prev.get_end(pos_lc)):
                    self._status = False
                    break

            prev = ent

        return self._status


    def _check_integrity_join(self):
        """Check for more than one rename of the same file."""
        for ent in self._changes:
            for rec in self._changes:
                if ent.fn == rec.fn and str(ent) != str(rec):
                    self._status = False
                    print("FNEditor error: file same old {0} -> ({1}, {2})".format(
                        ent.fn, str(ent), str(rec)))

                if (ent.fn != rec.fn and str(ent) == str(rec)):
                    self._status = False
                    print("FNEditor error: file same new  {0} -> ({1}, {2})".format(
                        ent.fn, rec.fn, str(ent)))

        return self._status


    def _check_existence(self):
        """Check if the file exists and the new name is free."""
        import os.path

        for ent in self._changes:
            if not os.path.isfile(ent.fn):
                self._status = False
                print("FNEditor error: file not found " + ent.fn)

            if os.path.isfile(ent["new"]):
                self._status = False
                print("FNEditor error: file already exists " + ent["new"])

        return self._status


    def __iter(self):
        for ent in self._changes:
            yield ent
