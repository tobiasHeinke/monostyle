
"""
util.editor
~~~~~~~~~~~

Text editing utilities.
"""

from monostyle.util.fragment import Fragment, FragmentBundle
from monostyle.util.monostyle_io import split_path_appendix

class Editor:
    """Text editing and conflict handling."""

    def __init__(self, source, changes=None):
        """
        source -- Fragment as a virtual input used to apply edits on.
        changes -- FragmentBundle as starting changes.
        """
        self.source = source
        self._changes = FragmentBundle() if changes is None else changes
        self._status = True


    def from_file(filename, changes=None):
        """Read the source from file before applying."""
        return Editor(Fragment(filename, None), changes=changes)


    def __bool__(self):
        return self._status


    def _read(self):
        """Return stored text or read it from the file."""
        if self.source.is_empty():
            try:
                with open(self.source.filename, "r", encoding="utf-8") as text_file:
                    text = text_file.read()

            except (IOError, OSError) as err:
                self._status = False
                print("{0}: cannot read: {1}".format(self.source.filename, err))
                return None

            return Fragment(self.source.filename, text)

        return self.source


    def _write(self, text_dst):
        """Write output to the file."""
        try:
            with open(self.source.filename, "w", encoding="utf-8") as text_file:
                text_file.write(str(text_dst))

            return text_dst

        except (IOError, OSError):
            self._status = False
            return None


    def _write_diff(self, filename, text_dst):
        """Write diff output to the file."""
        try:
            with open(filename, "w", encoding="utf-8") as text_file:
                text_file.write(text_dst)

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
        if not self._changes or text_src is None:
            if not use_conflict_handling:
                return text_src
            return text_src, self._changes

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
                if not use_conflict_handling:
                    return None
                return text_src, self._changes.bundle

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
        self._changes.sort(pos_lincol, start_end=False)
        for index, pair in enumerate(self._changes.bundle):
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
        https://projects.blender.org/blender/blender-manual/src/branch/main/tools/utils_maintenance/rst_helpers/__init__.py
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
                                  m.end()).move(text_src.start_pos, is_rel=True))


    def is_conflicted(self, new_change, pos_lincol=True, ignore_filename=True):
        """Change is (self) overlapped."""
        return bool(not new_change.is_self_overlapped(pos_lincol) and
                    not self._changes.is_overlapped(new_change, pos_lincol) and
                    (ignore_filename or
                    (new_change.filename == self.source.filename and
                     new_change.has_consistent_filenames())))


    def is_in_change(self, loc):
        """Location is in changes."""
        return self._changes.is_in_span(loc)


    def add_diff(self, input, pos_lincol=True, use_git=True):
        """Input a unified diff."""
        if use_git:
            import monostyle.git_inter as vsn_inter
        else:
            import monostyle.svn_inter as vsn_inter

        found = False
        for source_diff, changes_diff in vsn_inter.difference(False, input):
            if self.source.filename == source_diff.filename:
                self.add(changes_diff, pos_lincol=pos_lincol)
                found = True
            else:
                if found:
                    break


    def to_diff(self, apply=None, diff=None, output=None):
        """Outputs a unified diff."""
        def add_offset(m):
            groups = list(m.groups())
            groups[1] = str(int(groups[1]) + self.source.start_lincol[0])
            groups[3] = str(int(groups[3]) + self.source.start_lincol[0])
            return "".join(groups)

        import difflib
        if apply is None:
            apply = {}
        if diff is None:
            diff = {}
        apply["virtual"] = True
        text_dst = self.apply(**apply)
        if apply.get("use_conflict_handling"):
            text_dst, conflicted = text_dst

        if not diff.get("fine", False):
            if (not self.source.is_empty() and
                self.source.start_lincol and self.source.start_lincol[1] != 0):
                raise ValueError("Editor: Unified diff not at start of line")

            result = "".join(difflib.unified_diff(
                         list(self.source.iter_lines()), list(text_dst.iter_lines()),
                         fromfile=self.source.filename, tofile=text_dst.filename,
                         fromfiledate=diff.get("fromfiledate", ""),
                         tofiledate=diff.get("tofiledate", ""),
                         n=diff.get("n", 3)))

            if (not self.source.is_empty() and
                    self.source.start_lincol and self.source.start_lincol[0] != 0):
                import re
                loc_re = re.compile(r"^(@@ \-)(\d+?)((?:,\d+?)? \+)(\d+?)((?:,\d+?)? @@)$",
                            re.MULTILINE)
                result = re.sub(loc_re, add_offset, result)
        else:
            result = ["--- {0}{2}\n+++ {1}{3}\n".format(self.source.filename, text_dst.filename,
                     "\t" + diff["fromfiledate"] if "fromfiledate" in diff.keys() else "",
                     "\t" + diff["tofiledate"] if "tofiledate" in diff.keys() else "")]
            result.append("@@@ {0}{1} @@@\n".format(self.source.start_pos + 1,
                     " ({0},{1})".format(self.source.start_lincol[0] + 1,
                        self.source.start_lincol[1] + 1)
                     if self.source.start_lincol else ""))
            result.extend(list(difflib.ndiff(list(self.source.iter_lines()),
                                             list(text_dst.iter_lines()))))
            result = "".join(result)

        if not output:
            if not apply.get("use_conflict_handling"):
                return result

            return result, conflicted

        if not apply.get("use_conflict_handling"):
            return self._write_diff(output, result)

        return self._write_diff(output, result), conflicted


class FilenameEditor(Editor):
    """File renaming with SVN."""

    def __init__(self, source, changes=None, use_git=True):
        super().__init__(source, changes=changes)
        global vsn_inter
        if use_git:
            import monostyle.git_inter as vsn_inter
        else:
            import monostyle.svn_inter as vsn_inter


    def from_file(filename, changes=None, use_git=True):
        return FilenameEditor(Fragment(filename, None), changes=changes, use_git=use_git)


    def add(self, new_change, pos_lincol=True):
        """Add replacement."""
        last = next(reversed(new_change))
        if last and last.content[-1].endswith('\n'):
            new_change = new_change.slice(
                end=new_change.rel_to_start(-2), is_rel=True)
        super().add(new_change, pos_lincol)


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


    def to_diff(self, apply=None, diff=None, output=None):
        """Outputs a ndiff with partial unified diff control lines."""
        import difflib
        if apply is None:
            apply = {}
        if diff is None:
            diff = {}
        apply["virtual"] = True
        text_dst = self.apply(**apply)
        if apply.get("use_conflict_handling"):
            text_dst, conflicted = text_dst

        if diff.get("fine", True):
            result = ["--- {0}{2}\n+++ {1}{3}\n".format(self.source.filename, text_dst,
                     "\t" + diff["fromfiledate"] if "fromfiledate" in diff.keys() else "",
                     "\t" + diff["tofiledate"] if "tofiledate" in diff.keys() else "")]
            result.extend(list(difflib.ndiff(list(line + '\n' for line in self.source.iter_lines()),
                                             list(line + '\n' for line in text_dst.iter_lines()))))
            result = "".join(result)
        else:
            result = "".join(difflib.unified_diff(
                         list(line + '\n' for line in self.source.iter_lines()),
                         list(line + '\n' for line in text_dst.iter_lines()),
                         fromfile=self.source.filename, tofile=text_dst.filename,
                         fromfiledate=diff.get("fromfiledate", ""),
                         tofiledate=diff.get("tofiledate", ""),
                         n=0))

        if not output:
            if not apply.get("use_conflict_handling"):
                return result

            return result, conflicted

        if not apply.get("use_conflict_handling"):
            return self._write_diff(output, result)

        return self._write_diff(output, result), conflicted


class PropEditor(Editor):
    """File properties editing with SVN.
    Note the file has to be versioned.
    The key/name has to be appended to the filename of the Fragment separated with a colon.
    Non-binary property values only.
    """

    def from_file(filename, changes=None):
        return PropEditor(Fragment(filename, None), changes=changes)


    def join_key(filename, key):
        """Join key with filename."""
        return ':'.join((filename, key))


    def split_key(filename):
        """Split key from filename."""
        return split_path_appendix(filename, sep=':')


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
    """Session with one editor per file."""

    def __init__(self, mode="text", **kwargs):
        """
        mode -- selects the type of editor.
        """
        if mode == "text":
            self._editor_class = Editor
        elif mode in {"filename", "file name"}:
            self._editor_class = FilenameEditor
        elif mode in {"prop", "props", "property", "properties",
                      "conf", "config", "configuration"}:
            self._editor_class = PropEditor
        else:
            raise ValueError("'EditorSession' unknown mode:", mode)

        self._kwargs = kwargs

        self._editors = []
        # Store the index of the last accessed editor for performance.
        self._last_index = None
        self._status = True


    def __bool__(self):
        return self._status


    def add(self, new_change, pos_lincol=True):
        """Store change in editor."""
        if (self._last_index is not None and
                self._editors[self._last_index].source.filename == new_change.filename):
            self._editors[self._last_index].add(new_change, pos_lincol)
        else:
            for index, editor in enumerate(reversed(self._editors)):
                if editor.source.filename == new_change.filename:
                    editor.add(new_change, pos_lincol)
                    self._last_index = len(self._editors) - 1 - index
                    break
            else:
                editor = self._editor_class.from_file(new_change.filename, **self._kwargs)
                editor.add(new_change, pos_lincol)
                self._editors.append(editor)
                self._last_index = len(self._editors) - 1


    def apply(self, virtual=False, pos_lincol=True, use_conflict_handling=False,
              ignore_filename=True, stop_on_conflict=False):
        """Apply each editor."""
        if virtual:
            result = []
        for editor in self._editors:
            output = editor.apply(virtual=virtual, pos_lincol=pos_lincol,
                                  use_conflict_handling=use_conflict_handling,
                                  ignore_filename=ignore_filename)
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


    def add_diff(self, input, pos_lincol=True, use_git=True):
        """Input a unified diff."""
        if use_git:
            import monostyle.git_inter as vsn_inter
        else:
            import monostyle.svn_inter as vsn_inter

        for _, changes_diff in vsn_inter.difference(False, input):
            self.add(changes_diff, pos_lincol=pos_lincol)


    def to_diff(self, apply=None, diff=None, output=None, stop_on_conflict=False):
        """Create a diff from the editors."""
        if apply is None:
            apply = {}
        if diff is None:
            diff = {}
        result = []
        apply["virtual"] = True
        for editor in self._editors:
            result.append(editor.to_diff(apply, diff))

            if not editor:
                print("Editor error: conflict in", editor.source.filename)
                self._status = False
                if stop_on_conflict:
                    break

        result = "".join(result)
        if not output:
            return result

        Editor._write_diff(self, output, result)
