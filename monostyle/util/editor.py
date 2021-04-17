
"""
util.editor
~~~~~~~~~~~

Text editing utilities.
"""

from monostyle.util.fragment import Fragment, FragmentBundle

class Editor:
    """Text editing.

    source -- Fragment as a virtual input used to apply edits on.
    """

    def __init__(self, source, changes=None):
        self.source = source
        self._changes = FragmentBundle() if changes is None else changes
        self._status = True


    def from_file(filename):
        return Editor(Fragment(filename, None))


    def __bool__(self):
        return self._status


    def _read(self):
        """Return stored text or read it from the file."""
        if self.source.is_empty():
            try:
                with open(self.source.filename, "r", encoding="utf-8") as f:
                    text = f.read()

            except (IOError, OSError) as err:
                self._status = False
                print("{0}: cannot read: {1}".format(self.source.filename, err))
                return None

            return Fragment(self.source.filename, text)

        return self.source


    def _write(self, text_dst):
        """Write output to the file."""
        try:
            with open(self.source.filename, "w", encoding="utf-8") as f:
                f.write(str(text_dst))

            return text_dst

        except (IOError, OSError):
            self._status = False
            return None


    def add(self, new_change, pos_lincol=True):
        """Add replacement."""
        self._changes.combine(new_change, check_align=False, pos_lincol=pos_lincol, merge=False)


    def apply(self, virtual=False, pos_lincol=True, use_conflict_handling=False,
              ignore_filename=True):
        """Apply the edits to the input text and conflict detection and handling.

        virtual -- return the output text or write it to the file.
        """

        text_src = self._read()
        if self._changes.is_empty() or text_src is None:
            return text_src

        self._remove_doubles()
        conflicted = []
        if not ignore_filename:
            self._status = (not self._changes.has_consistent_filenames(pos_lincol) and
                            not self._changes.filename == self.source.filename)
            if not self._status:
                if not use_conflict_handling:
                    return None
            conflicted.extend(self._handle_filename_conflicts())

        self._status = not self._changes.is_self_overlapped(pos_lincol)
        if not self._status:
            if not use_conflict_handling:
                return None

            conflicted.extend(self._handle_location_conflicts(pos_lincol))

        text_dst = text_src.union(self._changes, pos_lincol)
        if not virtual:
            self._status = text_dst.is_complete(pos_lincol)
            if not self._status:
                return None

        self._changes.bundle.clear()
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

        self._changes.bundle = new_changes


    def _handle_filename_conflicts(self):
        """Remove entries with a different filename than the source and return them."""
        new_changes = []
        conflicted = []
        filename_src = self.source.filename
        for change in self._changes:
            if change.filename == filename_src:
                new_changes.append(change)
            else:
                conflicted.append(change)

        self._changes.bundle = new_changes
        return conflicted


    def _handle_location_conflicts(self, pos_lincol):
        """Interval Scheduling: activity selection problem.
        With multiple zero-length the order is undefined.

        Adapted from:
        https://www.techiedelight.com/activity-selection-problem-using-dynamic-programming/
        """
        groups = [[] for _ in range(0, len(self._changes.bundle))]
        for index, pair in enumerate(sorted(self._changes.bundle,
                                            key=lambda change: change.get_end(pos_lincol))):
            for index_sub, pair_sub in enumerate(self._changes.bundle[:index]):
                if (pair_sub.get_end(pos_lincol) < pair.get_start(pos_lincol) or
                        (pair_sub.get_end(pos_lincol) == pair.get_start(pos_lincol) and
                        (pair_sub.get_start(pos_lincol) != pair.get_end(pos_lincol))) and
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

        self._changes.bundle = group_max
        self._changes.sort(pos_lincol)
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
                self.add(Fragment(self.source.filename, ''.join(ls), m.start(),
                                  m.end()).add_offset(text_src.start_pos))


    def is_in_change(self, loc):
        return self._changes.is_in_span(loc)


class FilenameEditor(Editor):
    """File renaming with SVN."""

    def __init__(self, source, use_git=True):
        super().__init__(source)
        global vsn_inter
        if use_git:
            import monostyle.git_inter as vsn_inter
        else:
            import monostyle.svn_inter as vsn_inter


    def from_file(filename, use_git=True):
        return FilenameEditor(Fragment(filename, None), use_git=use_git)


    def _read(self):
        """Check if the file exists and return source Fragment."""
        import os.path

        if not os.path.isfile(self.source.filename):
            self._status = False
            print("FilenameEditor error: file not found", self.source.filename)
            return None

        if self.source.is_empty():
            return Fragment(self.source.filename, self.source.filename)

        return self.source


    def _write(self, text_dst):
        """Check the new name is free and rename file."""
        import os.path

        if os.path.isfile(str(text_dst)):
            self._status = False
            print("FilenameEditor error: file already exists", str(text_dst))
            return None

        vsn_inter.move(self.source.filename, str(text_dst))
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

        filename, key = PropEditor.split_key(self.source.filename)
        if not key:
            self._status = False
            print("PropEditor error: no key", filename)
            return None

        if not os.path.isfile(filename):
            self._status = False
            print("PropEditor error: file not found", filename)
            return None

        if self.source.is_empty():
            content = []
            for line in monostyle.svn_inter.prop_get(filename, key):
                content.append(line.decode("utf-8"))
            return Fragment(self.source.filename, content)

        return self.source


    def _write(self, text_dst):
        """Change property in file."""
        import os.path
        import monostyle.svn_inter

        filename, key = PropEditor.split_key(self.source.filename)
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

    def __init__(self, mode="text", **kwargs):
        if mode == "text":
            self._editor_class = Editor
        elif mode in {"filename", "filename"}:
            self._editor_class = FilenameEditor
        elif mode in {"prop", "props", "property", "properties",
                      "conf", "config", "configuration"}:
            self._editor_class = PropEditor
        else:
            print("Unknown EditorSession mode:", mode)

        self._kwargs = kwargs

        self._editors = []
        # Store the index of the last accessed editor for performance.
        self._last_index = None
        self._status = True


    def __bool__(self):
        return self._status


    def add(self, new_change, pos_lincol=True):
        if (self._last_index is not None and
                self._editors[self._last_index].new_change.filename == new_change.filename):
            self._editors[self._last_index].add(new_change, pos_lincol)
        else:
            for index, editor in enumerate(reversed(self._editors)):
                if editor.new_change.filename == new_change.filename:
                    editor.add(new_change, pos_lincol)
                    self._last_index = len(self._editors) - 1 - index
                    break
            else:
                editor = self._editor_class.from_file(new_change.filename, **self._kwargs)
                editor.add(new_change, pos_lincol)
                self._editors.append(editor)
                self._last_index = len(self._editors) - 1


    def apply(self, virtual=False, pos_lincol=True, stop_on_conflict=False):
        if virtual:
            result = []
        for editor in self._editors:
            output = editor.apply(virtual=virtual, pos_lincol=pos_lincol)
            if virtual:
                result.append(output)

            if not editor:
                print("Editor error: conflict in", editor.source.filename)
                self._status = False
                if stop_on_conflict:
                    break

        self._editors.clear()
        if virtual:
            return result
