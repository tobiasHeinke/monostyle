
"""
util.editor
~~~~~~~~~~~

Text editing utilities.
"""

from monostyle.util.fragment import Fragment, FragmentBundle


class Editor:
    """Text editing.

    fg -- Fragment as a virtual input used to apply edits on.
    """

    def __init__(self, fg):
        self.fg = fg
        self._changes = []
        self._status = True


    def from_file(filename):
        return Editor(Fragment(filename, None))


    def __bool__(self):
        return self._status


    def _read(self):
        """Return stored text or read it from the file."""
        if len(self.fg.content) == 0:
            try:
                with open(self.fg.filename, "r", encoding="utf-8") as f:
                    text = f.read()

            except (IOError, OSError) as err:
                self._status = False
                print("{0}: cannot read: {1}".format(self.fg.filename, err))
                return None

            return Fragment(self.fg.filename, text)

        return self.fg


    def _write(self, text_dst):
        """Write output to the file."""
        try:
            with open(self.fg.filename, "w", encoding="utf-8") as f:
                f.write(str(text_dst))

            return text_dst

        except (IOError, OSError):
            self._status = False
            return None


    def add(self, fg):
        """Add replacement."""
        if isinstance(fg, FragmentBundle):
            self._changes.extend(fg.bundle)
        else:
            self._changes.append(fg)


    def apply(self, virtual=False, pos_lc=True, use_conflict_handling=False):
        """Apply the edits to the input text.

        virtual -- return the output text or write it to the file.
        """

        text_src = self._read()
        if len(self._changes) == 0 or text_src is None:
            return text_src

        self._remove_doubles()
        self._changes.sort(key=lambda change: (change.get_start(pos_lc), change.get_end(pos_lc)))
        conflicted = []
        if not self._check_integrity(pos_lc):
            if not use_conflict_handling:
                return None

            conflicted = self.handle_conflicts(pos_lc)
            self._changes.sort(key=lambda change: (change.get_start(pos_lc),
                                                   change.get_end(pos_lc)))

        text_dst = text_src.copy().clear(True)
        after = text_src
        for change in self._changes:
            before, _, after = after.slice(change.get_start(pos_lc), change.get_end(pos_lc),
                                           output_zero=True)

            if before:
                text_dst.combine(before, False)

            text_dst.combine(change, False)

        if after:
            text_dst.combine(after, False)

        self._changes.clear()
        if virtual:
            if not use_conflict_handling:
                return text_dst

            return text_dst, conflicted

        if not use_conflict_handling:
            return self._write(text_dst)

        return self._write(text_dst), conflicted


    def _remove_doubles(self):
        """Remove duplicated entries."""
        new_changes = []
        for change in self._changes:
            for change_new in new_changes:
                if change == change_new:
                    break
            else:
                new_changes.append(change)

        self._changes = new_changes


    def _check_integrity(self, pos_lc):
        """Check for overlaps of the start to end span."""
        prev = None
        for change in self._changes:
            if prev:
                if (change.is_in_span(prev.get_start(pos_lc)) or
                        change.is_in_span(prev.get_end(pos_lc))):
                    self._status = False
                    break

            prev = change

        return self._status


    def handle_conflicts(self, pos_lc):
        """Interval Scheduling: activity selection problem.
        With multiple zero-length the order is undefined.

        Adapted from:
        https://www.techiedelight.com/activity-selection-problem-using-dynamic-programming/
        """
        groups = [[] for _ in range(0, len(self._changes))]
        for index, pair in enumerate(sorted(self._changes,
                                            key=lambda change: change.get_end(pos_lc))):
            for index_sub, pair_sub in enumerate(self._changes[:index]):
                if (pair_sub.get_end(pos_lc) < pair.get_start(pos_lc) or
                        (pair_sub.get_end(pos_lc) == pair.get_start(pos_lc) and
                        (pair_sub.get_start(pos_lc) != pair.get_end(pos_lc))) and
                        len(groups[index]) < len(groups[index_sub])):
                    groups[index] = groups[index_sub].copy()

            groups[index].append(pair)

        group_max = []
        for pair in groups:
            if len(group_max) < len(pair):
                group_max = pair

        conflicted = []
        for change in self._changes:
            if change not in group_max:
                conflicted.append(change)
                self._status = False

        self._changes = group_max
        return conflicted


    def iter_edit(self, find_re):
        """Iterate over the text with a reg exp.
        Alteration to the yielded content of the list container is detected within the for-loop.

        find_re -- a reg exp pattern.

        Adapted from:
        https://developer.blender.org/diffusion/BM/browse/trunk/blender_docs/tools_rst/rst_helpers/__init__.py
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
                self.add(Fragment(self.fg.filename, ''.join(ls), m.start(),
                                  m.end()).add_offset(text_src.start_pos))


    def is_in_fg(self, loc):
        for change in self._changes:
            if change.is_in_span(loc):
                return True

        return False


class FNEditor(Editor):
    """File renaming with SVN."""

    def __init__(self, fg, use_git=True):
        super().__init__(fg)
        global vsn_inter
        if use_git:
            import monostyle.git_inter as vsn_inter
        else:
            import monostyle.svn_inter as vsn_inter


    def from_file(filename):
        return FNEditor(Fragment(filename, None))


    def _read(self):
        """Check if the file exists and return source Fragment."""
        import os.path

        if not os.path.isfile(self.fg.filename):
            self._status = False
            print("FNEditor error: file not found", self.fg.filename)
            return None

        if len(self.fg.content) == 0:
            return Fragment(self.fg.filename, self.fg.filename)

        return self.fg


    def _write(self, text_dst):
        """Check the new name is free and rename file."""
        import os.path

        if os.path.isfile(str(text_dst)):
            self._status = False
            print("FNEditor error: file already exists", str(text_dst))
            return None

        vsn_inter.move(self.fg.filename, str(text_dst))
        return text_dst


class PropEditor(Editor):
    """File properties editing with SVN.
    Note the file has to be versioned.
    The key/name has to be appended to the filename of the Fragment separated with a colon.
    Non-binary property values only.
    """

    def from_file(filename):
        return PropEditor(Fragment(filename, None))


    def join_key(filename, key):
        return ':'.join((filename, key))


    def split_key(filename):
        if (dot_idx := filename.rfind('.')) != -1:
            if (colon_idx := filename.find(':', dot_idx)) != -1:
                return filename[:colon_idx], filename[colon_idx + 1:]

        return filename, None


    def _read(self):
        """Get file property."""
        import os.path
        import monostyle.svn_inter

        filename, key = PropEditor.split_key(self.fg.filename)
        if not key:
            self._status = False
            print("PropEditor error: no key", filename)
            return None

        if not os.path.isfile(filename):
            self._status = False
            print("PropEditor error: file not found", filename)
            return None

        if len(self.fg.content) == 0:
            content = []
            for line in monostyle.svn_inter.prop_get(filename, key):
                content.append(line.decode("utf-8"))
            return Fragment(self.fg.filename, content)

        return self.fg


    def _write(self, text_dst):
        """Change property in file."""
        import os.path
        import monostyle.svn_inter

        filename, key = PropEditor.split_key(self.fg.filename)
        if not key:
            self._status = False
            print("PropEditor error: no key", filename)
            return None

        if not os.path.isfile(filename):
            self._status = False
            print("PropEditor error: file not found", filename)
            return None

        monostyle.svn_inter.prop_set(filename, key, str(text_dst))
        return text_dst


class EditorSession:
    """Session with one editor per file.

    mode -- selects the type of editor.
    """

    def __init__(self, mode="text"):
        if mode == "text":
            self._editor_class = Editor
        elif mode in ("filename", "filename"):
            self._editor_class = FNEditor
        elif mode in ("prop", "props", "property", "properties",
                      "conf", "config", "configuration"):
            self._editor_class = PropEditor
        else:
            print("Unknown EditorSession mode:", mode)

        self._editor_stack = []
        # Store the index of the last accessed editor for performance.
        self._last_index = None
        self._status = True


    def __bool__(self):
        return self._status


    def add(self, fg):
        if (self._last_index is not None and
                self._editor_stack[self._last_index].fg.filename == fg.filename):
            self._editor_stack[self._last_index].add(fg)
        else:
            for index, editor in enumerate(reversed(self._editor_stack)):
                if editor.fg.filename == fg.filename:
                    editor.add(fg)
                    self._last_index = len(self._editor_stack) - 1 - index
                    break
            else:
                editor = self._editor_class.from_file(fg.filename)
                editor.add(fg)
                self._editor_stack.append(editor)
                self._last_index = len(self._editor_stack) - 1


    def apply(self, virtual=False, pos_lc=True, stop_on_conflict=False):
        if virtual:
            result = []
        for editor in self._editor_stack:
            output = editor.apply(virtual=virtual, pos_lc=pos_lc)
            if virtual:
                result.append(output)

            if not editor:
                print("Editor error: conflict in", editor.fg.filename)
                self._status = False
                if stop_on_conflict:
                    break

        self._editor_stack.clear()
        if virtual:
            return result
