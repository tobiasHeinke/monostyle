
"""
image
~~~~~

Image tools.
"""

import re

import monostyle.util.monostyle_io as monostyle_io
from monostyle.util.report import Report
from monostyle.util.fragment import Fragment
from monostyle.rst_parser.core import RSTParser
import monostyle.rst_parser.walker as rst_walker


def duplicated_image(toolname, reports):
    """Duplicated images."""
    def uuid_from_file(filename, block_size=1 << 20):
        """
        Returns an arbitrary sized unique ASCII string based on the file contents.
        (exact hashing method may change).
        """
        # https://developer.blender.org/diffusion/BM/browse/trunk/blender_docs/tools_rst/rst_remap.py
        with open(filename, 'rb') as f:
            # first get the size
            import os
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(0, os.SEEK_SET)
            del os
            # done!

            import hashlib
            sha1 = hashlib.new('sha512')
            while True:
                data = f.read(block_size)
                if not data:
                    break
                sha1.update(data)
            # skip the '0x'
            return hex(size)[2:] + sha1.hexdigest()

    hashes = {}
    for dirpath, name, ext in monostyle_io.img_files():
        hashes[name + ext] = uuid_from_file(dirpath + "/" + name + ext)

    pairs_found = set()
    for key, value in hashes.items():
        for key_rec, value_rec in hashes.items():
            if key == key_rec:
                continue

            if value == value_rec and key_rec + key not in pairs_found:
                output = Fragment(key, key)
                message = "duplicated image " + key_rec
                reports.append(Report('W', toolname, output, message))
                pairs_found.add(key + key_rec)

    return reports


def image_filename(toolname, reports):
    """Image names and extensions."""
    pos = (".png", ".jpg", ".jpeg", ".svg")
    char_re = re.compile(r"[^a-z0-9_\-]")
    upper_re = re.compile(r"[A-Z]")
    imgs = list((name, ext.lower()) for _, name, ext in monostyle_io.img_files())

    pairs_found = set()
    for name, ext in imgs:
        name_lower = name.lower()
        for name_rec, ext_rec in imgs:
            if (name_lower == name_rec.lower() and
                    (name != name_rec or ext != ext_rec) and
                    ''.join((name_rec, ext_rec, name, ext)) not in pairs_found):
                output = Fragment(name + ext, name + ext)
                message = (("case collition" if name != name_rec else "") +
                           (" and " if name != name_rec and ext != ext_rec else "") +
                           ("extension collition" if ext != ext_rec else ""))
                reports.append(Report('W', toolname, output, message))
                pairs_found.add(''.join((name, ext, name_rec, ext_rec)))

        for char_m in re.finditer(char_re, name):
            severity = 'E' if not re.match(upper_re, char_m.group(0)) else 'I'
            output = Fragment(name + ext, name).slice_match_obj(char_m, 0, True)
            message = "not allowed char in image filename"
            reports.append(Report(severity, toolname, output, message))

        if ext not in pos:
            output = Fragment(name + ext, ext, len(name), start_lincol=(0, len(name)))
            message = "bad extension"
            reports.append(Report('E', toolname, output, message))

    return reports


def unused_image_pre(_):
    images = set()
    rst_parser = RSTParser()
    commented_out = True

    for filename, text in monostyle_io.doc_texts():
        document = rst_parser.parse(rst_parser.document(filename, text))
        if commented_out:
            for node in rst_walker.iter_node(document.body, "comment"):
                node.body = rst_parser.parse_block(node.body)
        for node in rst_walker.iter_node(document.body, "dir"):
            if rst_walker.is_of(node, "*", {"figure", "image"}):
                images.add(monostyle_io.path_to_rel(monostyle_io.path_to_abs(
                           str(node.head.code).strip(), "doc"), "img"))

    return {"data": images}


def unused_image(toolname, reports, data):
    """Unused images."""
    for _, name, ext in monostyle_io.img_files():
        if name + ext not in data:
            output = Fragment(name + ext, name + ext)
            message = "unused image"
            reports.append(Report('W', toolname, output, message))

    return reports


OPS = (
    ("duplicated-image", duplicated_image, None, False),
    ("image-filename", image_filename, None, False),
    ("unused-image", unused_image, unused_image_pre, False),
)


if __name__ == "__main__":
    from monostyle.__main__ import main_mod
    main_mod(__doc__, OPS, __file__)
