
"""
update_lexicon
~~~~~~~~~~~~~~

Update lexicon in the user configuration.
"""

import csv

import monostyle.util.monostyle_io as monostyle_io
from monostyle.rst_parser.core import RSTParser
from monostyle.spelling import word_filtered

from monostyle.util.lexicon import Lexicon


def setup_lexicon():
    """Build and save the lexicon."""
    lexicon = Lexicon(False)
    if not lexicon:
        if monostyle_io.ask_user("The lexicon does not exist in the user config folder ",
                                 "do you want to build it"):
            lexicon_write_csv(build_lexicon())
        else:
            return False

    return True


def build_lexicon():
    """Build lexicon by looping over files."""
    rst_parser = RSTParser()
    lexicon = Lexicon()
    for filename, text in monostyle_io.doc_texts():
        document = rst_parser.parse(rst_parser.document(filename, text))
        for word in word_filtered(document):
            lexicon.add(str(word))

    return lexicon


def lexicon_write_csv(lexicon):
    """Write lexicon to user config directory."""
    lex_filename = monostyle_io.path_to_abs("monostyle/lexicon.csv")
    count = 0
    try:
        with open(lex_filename, 'w', newline='', encoding='utf-8') as csvfile:
            csv_writer = csv.writer(csvfile)
            for entry in lexicon.join():
                csv_writer.writerow(entry)
                count += 1

            print("wrote lexicon file with {0} words".format(count))

    except (IOError, OSError) as err:
        print("{0}: cannot write: {1}".format(lex_filename, err))


def differential(lex_stored, lex_new):
    """Show a differential between the current texts and the stored lexicon."""
    added, removed = lex_stored.compare(lex_new)
    monostyle_io.print_title("Added", True)
    for word in added:
        print(word)

    monostyle_io.print_title("Removed", True)
    for word in removed:
        print(word)


def main():
    import argparse
    from monostyle.__main__ import setup

    descr = "Write lexicon."
    parser = argparse.ArgumentParser(description=descr)
    # first char to lowercase
    doc_str = differential.__doc__[0].lower() + differential.__doc__[1:]
    parser.add_argument("-d", "--diff",
                        action="store_true", dest="diff", default=False,
                        help=doc_str)

    parser.add_argument("-r", "--root",
                        dest="root", nargs='?', const="",
                        help="defines the ROOT directory of the project")

    args = parser.parse_args()

    setup_sucess = setup(args.root)
    if not setup_sucess:
        return 2

    lexicon_new = build_lexicon()
    if not args.diff:
        lexicon_write_csv(lexicon_new)
    else:
        lexicon_stored = Lexicon(False)
        if lexicon_stored is not None:
            differential(lexicon_stored, lexicon_new)


if __name__ == "__main__":
    main()
