
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


    def from_file(fn):
        return Editor(Fragment(fn, None))


    def __bool__(self):
        return self._status


    def _read(self):
        """Return stored text or read it from the file."""
        if len(self.fg.content) == 0:
            try:
                with open(self.fg.fn, "r", encoding="utf-8") as f:
                    text = f.read()

            except (IOError, OSError) as err:
                print("{0}: cannot read: {1}".format(self.fg.fn, err))
                return None

            return Fragment(self.fg.fn, text)

        return self.fg


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

        text_dst = text_src.copy().clear(True)
        after = text_src
        for ent in self._changes:
            before, _, after = after.slice(ent.get_start(pos_lc), ent.get_end(pos_lc),
                                           output_zero=True)

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


class FNEditor(Editor):
    """File renaming with SVN."""

    def from_file(fn):
        return FNEditor(Fragment(fn, None))


    def _read(self):
        """Check if the file exists and return source Fragment."""
        import os.path

        if not os.path.isfile(self.fg.fn):
            self._status = False
            print("FNEditor error: file not found", self.fg.fn)
            return None

        if self.fg.content is None:
            return Fragment(self.fg.fn, self.fg.fn)

        return self.fg


    def _write(self, text_dst):
        """Check the new name is free and rename file."""
        import os.path
        import monostyle.svn_inter

        if os.path.isfile(str(text_dst)):
            self._status = False
            print("FNEditor error: file already exists", str(text_dst))
            return None

        monostyle.svn_inter.move(self.fg.fn, str(text_dst))
        return text_dst


class EditorSession:
    """Session with one editor per file.

    mode -- selects the type of editor.
    """

    def __init__(self, mode="text"):
        if mode == "text":
            self._editor_class = Editor
        else:
            self._editor_class = FNEditor

        self._editor_stack = []
        # Store the index of the last accessed editor for performance.
        self._last_index = None
        self._status = True


    def __bool__(self):
        return self._status


    def add(self, fg):
        if (self._last_index is not None and
                self._editor_stack[self._last_index].fg.fn == fg.fn):
            self._editor_stack[self._last_index].add(fg)
        else:
            for index, editor in enumerate(reversed(self._editor_stack)):
                if editor.fg.fn == fg.fn:
                    editor.add(fg)
                    self._last_index = len(self._editor_stack) - 1 - index
                    break
            else:
                editor = self._editor_class.from_file(fg.fn)
                editor.add(fg)
                self._editor_stack.append(editor)
                self._last_index = len(self._editor_stack) - 1


    def apply(self, virtual=False, pos_lc=True, stop_on_conflict=False):
        if virtual:
            result = []
        for editor in self._editor_stack:
            out = editor.apply(virtual=virtual, pos_lc=pos_lc)
            if virtual:
                result.append(out)

            if not editor:
                print("Editor error: conflict in", editor.fg.fn)
                self._status = False
                if stop_on_conflict:
                    break

        self._editor_stack.clear()
        if virtual:
            return result
