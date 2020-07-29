
"""
reflow
~~~~~~

Line wrapper.
Based on https://metacpan.org/pod/Text::Reflow
Data model based on https://github.com/bramstein/typeset
"""

# Original script written by Michael Larsen, larsen@edu.upenn.math
# Modified by Martin Ward, martin@gkc.org.uk
# Copyright 1994 Michael Larsen and Martin Ward
# Email: martin@gkc.org.uk
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of either the Artistic License or
# the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#


import re
from monostyle.util.pos import PartofSpeech
from monostyle.util.nodes import Node, LinkedList
import monostyle.rst_parser.walker as rst_walker

POS = PartofSpeech()

def reflow_trial(boxes, optimum, maximum, options):
    """Find best breaks."""

    best = options["penaltylimit"] * 21
    for opt in range(optimum[0], optimum[1], optimum[2]):

        # Optimize preceding break.
        for active_box in boxes:
            interval = 0
            active_box.totalpenalty = options["penaltylimit"] * 2

            box = active_box
            is_first = True
            while box:
                interval += box.word_len
                if not is_first and (interval > opt + 10 or interval >= maximum):
                    break
                penalty = (interval - opt) ** 2
                interval += box.space_len
                if box.prev:
                    penalty += box.prev.totalpenalty
                penalty -= (active_box.demerits * options["semantic"]) / 2

                if penalty < active_box.totalpenalty:
                    active_box.totalpenalty = penalty
                    active_box.linkbreak = box.prev

                is_first = False
                box = box.prev

        interval = 0
        bestsofar = options["penaltylimit"] * 20
        lastbreak = boxes.last().prev
        # Pick a break for the last line which gives
        # the least penalties for previous lines:
        box = lastbreak
        box_next = box.next
        # Break after node?
        while box_next:
            interval += box_next.word_len
            if interval > opt + 10 or interval > maximum:
                break
            if interval > opt:
                # Don't make last line too long.
                penalty = (interval - opt) ** 2
            else:
                penalty = 0

            interval += box_next.space_len
            if box:
                penalty += box.totalpenalty
            if box_next is boxes.last() or box_next.next is boxes.last():
                penalty += options["paraorphan"] * options["semantic"]
            if penalty <= bestsofar:
                bestsofar = penalty
                lastbreak = box

            box_next = box
            if box:
                box = box.prev


        # Save these breaks if they are an improvement:
        if bestsofar < best:
            best_lastbreak = lastbreak
            for box in boxes:
                box.best_linkbreak = box.linkbreak
            best = bestsofar


    # Return the best breaks:
    return boxes, best_lastbreak



def fix(root_rst, reports):
    """Search for the reports location in the full document."""
    changes = []
    unlocated = reports.copy()
    for node in rst_walker.iter_node(root_rst, ("text"), False):
        if node.body.code:
            is_first_report = True
            reports_pro = []
            for report in unlocated:
                if node.body.code.is_in_span(report.out.start_lincol):
                    reports_pro.append(report)
                    if is_first_report:
                        changes_para = reflow(node)
                        report.fix = changes_para
                        changes.extend(changes_para)
                        is_first_report = False

            for report in reports_pro:
                unlocated.remove(report)

    return changes, unlocated


def reflow(node):
    """Main function."""
    optimum_abs = (70, 110, 1)  # Best line length 65. [start, end, step]
    maximum_abs = 118           # Maximum possible line length 80
    options = {
        "semantic": 30,       # Extent to which semantic factors matter 20
        "namebreak": 20,      # Penalty for splitting up name 10
        "sentence": 20,       # Penalty for sentence widows and orphans 6
        "dosentence2": True,  # Apply sentence second word
        "sentence2": 5,       # Penalty for sentence second word
        "independent": 10,    # Penalty for independent clause w's & o's
        "dependent": 6,       # Penalty for dependent clause w's & o's
        "paraorphan": 5,      # Penalty for a short last line (1 or 2 words) in a paragraph
        "connpenalty": 1,     # Multiplier to avoid penalties at end of line
        "parenthesis": 40,    # Penalty for splitting up within parenthesis
        "quote": 40,          # Penalty for splitting up within quotes
        "math": 30,           # Penalty for digits and operators
        "markupbreak": 60,    # Penalty for splitting up markup at breaking point
        "markup": 70,         # Penalty for splitting up markup

        "penaltylimit": 33554432 #0x2000000
    }

    ind_first, ind_block = measure_indent(node)
    optimum = [optimum_abs[0] - ind_block, optimum_abs[1] - ind_block, optimum_abs[2]]
    maximum = maximum_abs - ind_block
    # print(show_limes(node, options["optimum"], options["maximum"]), end="\n")

    changes_para = []
    boxes = process_para(node, ind_first - ind_block, options)
    if len(boxes) > 1:
        boxes = reflow_penalties(boxes, options)
        # show_demerits(boxes)
        boxes, lastbreak = reflow_trial(boxes, optimum, maximum, options)
        changes_para = stringify_space(boxes, lastbreak)

    if len(changes_para) != 0:
        changes_para = add_indent(changes_para, ind_block)

    return changes_para


def process_para(node, ind_offset, options):
    """Iterate over paragraph nodes."""
    def iter_para_parts(node):
        if node.child_nodes.is_empty():
            yield node
        else:
            yield from rst_walker.iter_nodeparts(node, ("head", "body", "id_start"),
                                                 leafs_only=True)

    boxes = LinkedList()
    is_first = True
    last = node.code.start_pos
    extra_len = node.code.start_lincol[1] + ind_offset

    for part in iter_para_parts(node.body):
        code_str = str(part.code)
        for m in re.finditer(r"\s+", code_str, re.DOTALL):
            if is_first:
                is_first = False
                if m.start() == 0:
                    continue

            space = part.code.slice_match_obj(m, 0, True)
            word = node.code.slice(last, space.start_pos, True)
            demerits = 0
            if part.node_name == "id_start":
                demerits = -options["markupbreak"]
            elif part.parent_node.node_name != "text":
                demerits = -options["markup"]
            boxes.append(Box(str(word), space, demerits, extra_len))
            last = space.end_pos
            extra_len = 0

    if last != node.code.end_pos:
        space = node.code.copy().clear(False)
        word = node.code.slice(last, space.start_pos, True)
        boxes.append(Box(str(word), space, 0, extra_len))

    return boxes



class Box(Node):
    """Text container.

    content -- text.
    space -- following spaces as Fragment.
    demerits -- weight of breaks after the Box.
    extra_len -- length of whitespaces before the Box e.g. a first line indent.
    """

    __slots__ = (
        'content', 'space', 'demerits', 'totalpenalty', 'linkbreak',
        'best_linkbreak', 'word_len', 'space_len')

    def __init__(self, content, space, demerits, extra_len=0):
        super(Box, self).__init__()

        self.content = content
        self.space = space
        self.demerits = demerits
        self.totalpenalty = 0
        self.linkbreak = None
        self.best_linkbreak = None

         # word_len: length of each word (excluding spaces)
        self.word_len = len(content) + extra_len
         # space_len: length the space after this word
         # Ignore length set to always 1
        self.space_len = 1


    def __str__(self):
        return "[c {0}, d {1}, t {2}]".format(self.content, self.demerits, self.totalpenalty)


def reflow_penalties(boxes, options):
    """Add spaces to ends of sentences and calculate @extra array of penalties."""
    pare_open_re = re.compile(r"[\(\[\{]")
    pare_close_re = re.compile(r"[\)\]\}]")
    pare_level = 0

    quote_open_re = re.compile(r"^\W*?(['\'']+)")
    quote_close_re = re.compile(r"(['\'']+)\W*?$")
    quote_level = 0

    for box in boxes:
        pare_level += len(re.findall(pare_open_re, box.content))
        pare_level -= len(re.findall(pare_close_re, box.content))

        pare_level = max(0, pare_level)
        if pare_level != 0:
            box.demerits -= options["parenthesis"]

        if quote_m := re.match(quote_open_re, box.content):
            quote_level += len(quote_m.group(1))

        if quote_m := re.search(quote_close_re, box.content):
            quote_level -= len(quote_m.group(1))

        quote_level = max(0, quote_level)
        if quote_level != 0:
            box.demerits -= options["quote"]

        # Period or colon
        if punc_m := re.match(r"^([A-Za-z0-9-]+)[\"')]*([\.\:])[\"')]*$", box.content):
            path = pos_weight(punc_m.group(1))
            # End of sentence
            if (not path or path[0] != "abbreviation") or punc_m.group(2) == ":":
                box.demerits += options["sentence"] / 2
                if box.prev:
                    box.prev.demerits -= options["sentence"]
                    if options["dosentence2"] and box.prev.prev:
                        box.prev.prev.demerits -= options["sentence2"]
                if box.next:
                    box.next.demerits -= options["sentence"]
                    if options["dosentence2"] and box.next.next:
                        box.next.next.demerits -= options["sentence2"]

            elif path:
                # Don't break "Mr. X"
                if path[0] == "abbreviation" and path[1] == "title":
                    box.demerits -= options["namebreak"]

        # !? after word
        if (re.search(r"[\?\!][\"')]*$", box.content) and
                (box.next and re.match(r"^[^A-Za-z]*[A-Z]", box.next.content))):
            box.demerits += options["sentence"] / 2
            if box.prev: box.prev.demerits -= options["sentence"]
            if box.next: box.next.demerits -= options["sentence"]

        if re.search(r"\,$", box.content): # Comma after word
            box.demerits += options["dependent"] / 2
            if box.prev: box.prev.demerits -= options["dependent"]
            if box.next: box.next.demerits -= options["dependent"]

        if re.search(r"[\;\"\'\)]$|--$", box.content): # Punctuation after word
            box.demerits += options["independent"] / 2
            if box.prev: box.prev.demerits -= options["independent"]
            if box.next: box.next.demerits -= options["independent"]

        if box.next and re.match(r"^\(", box.next.content): # Next word has opening parenthesis
            box.demerits += options["independent"] / 2
            if box.prev: box.prev.demerits -= options["independent"]
            if box.next: box.next.demerits -= options["independent"]

        if (box.next and re.match(r"[A-Z]", box.content) and
                not re.search(r"\.", box.content) and re.match(r"[A-Z]", box.next.content)):
            box.demerits -= options["namebreak"] # Don't break "United States"

        if box.next and re.search(r"('s|s')$", box.content):
            box.demerits -= options["namebreak"] # possessive

        if re.match(r"\d", box.content):
            box.demerits -= options["math"]
            if box.prev: box.prev.demerits -= options["math"]

        if single_char_m := re.match(r"\\?(.)$", box.content):
            if single_char_m.group(1) != "a":
                box.demerits -= options["math"]
                if box.prev: box.prev.demerits -= options["math"]

        path = pos_weight(box.content)
        if path and path[0] != "abbreviation":
            box.demerits += path[-1][1] * options["connpenalty"]
            if box.prev: box.prev.demerits += path[-1][0] * options["connpenalty"]

    return boxes


def pos_weight(word):
    """ Discourage a break have the value 1
    The value is the relative effort to avoid breaking
    a line before/after this part of speech tag,
    The structure has to by the same as the pos data.
    """

    weights = {
        "noun": [0, 0],
        "verb": [0, 0],
        "auxiliary": [-2, -3],
        "adjective": [-1, -3],
        "adverb": [-2, -1],
        "pronoun": [1, -3],
        "participle": [-1, 0],
        "preposition": {
            "one": [-2, 2],
            "two": [-3, 2]
        },
        "conjunction": {
            "coordinating": [3, -3],
            "correlative": [-2, -2],
            "subordinate": [3, -3]
        },
        "interjection": [0, 0],
        "determiner": {
            "article": [2, -5],
            "demonstrative": [0, 0],
            "possessive": [0, 0],
            "quantifier": [0, -3],
            "numeral": {
                "cardinal": [-1, -3],
                "ordinal": [-1, -3],
                "nonspecific": [-1, -2],
            },
            "distributive": [2, -2],
            "interrogative": [2, -2]
        },
        "abbreviation": {
            "title": {
                "civil": [0, -4],
                "military": [0, -4],
                "nobility_cleric": [0, -4]
            },
            "road_signs": [0, -4],
            "month": [-2, -2],
            "phrase": [1, -2],
            "doc": [0, -3]
        }
    }
    if path := POS.classify(word):
        weight = weights.copy()
        for seg in path:
            if seg in weight:
                weight = weight[seg]
            else:
                print("reflow weight key error: ", seg)

        path.append(weight)
        return path


def stringify_space(boxes, lastbreak):
    """Find changes turning spaces into newlines (or vice versa)."""
    changes_para = []
    box = boxes.last()
    while box:
        is_last = True
        while box and box is not lastbreak:
            space_str = str(box.space)
            if is_last:
                if len(space_str) != 0:
                    nl_count = space_str.count('\n')
                    if nl_count != len(space_str):
                        new_content = []
                        for _ in range(max(1, nl_count)):
                            new_content.append('\n')
                        box.space.content = new_content
                        changes_para.append(box.space)
                is_last = False
            elif len(space_str) != 0 and (len(space_str) != 1 or space_str == '\n'):
                box.space.content = ' '
                changes_para.append(box.space)
            box = box.prev

        box = lastbreak
        if lastbreak:
            lastbreak = lastbreak.best_linkbreak

    return changes_para


def stringify_word(boxes, lastbreak):
    """Legacy for debugging."""
    lines = []
    box = boxes.last()
    while box:
        line = []
        while box and box is not lastbreak:
            line.append(box.content)
            box = box.prev

        line.reverse()
        lines.append(' '.join(line) + "\n")

        box = lastbreak
        if lastbreak:
            lastbreak = lastbreak.best_linkbreak

    lines.reverse()
    return lines


def show_limes(node, optimum, maximum):
    """Visualize optimum and maximum."""
    lines_alt = []
    for line in node.code.content:
        line = line[:-1] + ' ' * ((maximum - len(line)) + 1) + '\n'
        line = line[:optimum[0]] + '¦' + line[optimum[0]:optimum[1]]
        line += '¦' + line[optimum[1]:maximum] + '|' + line[maximum:]
        lines_alt.append(line)

    return lines_alt


def show_demerits(boxes):
    """Visualize demerits."""
    output = []
    for box in boxes:
        if box.demerits == 0:
            demerit_char = "°"
        elif box.demerits > 0:
            demerit_char = "^"
        else:
            demerit_char = "¯"
        output.append(box.content + demerit_char)

    print(" ".join(output))


def measure_indent(node):
    """Measure the indent."""
    is_first = True
    ind_re = re.compile(r"\A +")
    ind_first = 0
    ind_cur = 0
    ind_prev = None
    for line in node.code.content:
        if len(line.strip()) == 0:
            is_first = False
            continue

        ind_cur = 0
        if ind_m := re.match(ind_re, line):
            ind_cur = ind_m.end(0)

        if ind_prev and ind_prev != ind_cur:
            print("reflow: paragraph uneven indent")

        if is_first:
            ind_first = ind_cur
            if not ind_m:
                par_node = node.parent_node
                while par_node and par_node.node_name in ("text", "body"):
                    par_node = par_node.parent_node

                # indent style
                if (rst_walker.is_of(par_node,
                        ("dir", "target", "substdef", "footdef", "citdef"), "*", "head")):
                    ind_cur = par_node.parent_node.name_start.code.start_lincol[1] + 3
                else:
                    ind_cur = node.code.start_lincol[1]
        else:
            ind_prev = ind_cur

        is_first = False

    return ind_first, ind_cur


def add_indent(changes_para, ind_block):
    """Add indent spaces after newlines."""
    ind_block_str = ' ' * ind_block
    for change in changes_para:
        if str(change) == '\n':
            change.content.append(ind_block_str)

    return changes_para


def froschkoenig():
    """Test text."""
    text = (
        "In olden times when wishing still helped one, "
        "there lived a king whose daughters were all beautiful;",
        "and the youngest was so beautiful that the sun itself,",
        "which has seen so much, was astonished whenever it shone in her face.",
        "Close by the king's castle lay a great dark forest, "
        "and under an old lime-tree in the forest was a well,",
        "and when the day was very warm, the king's child "
        "went out to the forest and sat down by the fountain;",
        "and when she was bored she took a golden ball, "
        "and threw it up on high and caught it; "
        "and this ball was her favorite plaything.")

    return '\n'.join(text)
