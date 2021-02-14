
# Tools

An overview of the modules and tools.


## Spelling

### new-word

Find rare or new words. This is a multi tool because it detects:

- Spelling errors, it also detects valid words e.g. 'which' vs. 'witch' and
  words that are not in a general dictionary like business and product names.
- Word choices like not simple words, interjection like 'heck', etc.
- Compounding/hyphenation (if the words are not used individually like 'well defined').
- Acronyms and capitalization within a word.
- Homophones (similar sounding words) when one of the pair is rare.


## List Search

Explicit search for terms and capitalization.

- avoid
  - vague: unspecific verbs like 'make'.
  - qualifier: requires the reader to make an assessment, e.g. 'very' can often be removed.
  - difficulty: simplicity is subjective. Can be condescending.
  - anthropomorphism: verbs that attribute programs or algorithms human qualities, e.g. 'wants' thus a will.
  - computer characteristic: adverbs that superficially describe expected characteristics of computer programs
    like speed thus 'instant' results.
  - voice: how to address the reader.
  - pronoun: non gender neutral pronouns.
  - uncertainty: requires the reader to make an assessment or the writer is unsure.
  - modal verb: same as uncertainty.
  - informal: words and phrases unsuited for docs.
  - syntactic expletive: superficial constructs.
  - style: miscellaneous rules.

- dev
  - development: wording for release nodes not belonging in docs and limitations that might be outdated.
  - CS technical term: software development jargon.

- simplify: complicated words (long, loan or uncommon words and official language).

- Blender
  - UI: correct names for user interface elements, hyphenation, capitalization
  - Editors: caps
  - Modes: caps of the main modes


## Markup

### directive

Find markup (directives and roles) that should not be used in the project.

### heading-level

Check the heading hierarchy.

### indention

Check the indention.

### kbd

Check the conformity of keyboard shortcuts.

### leak

Find parts of incomplete markup and versioning merge conflicts.


## Code Style

### blank-line

Blank line convention.

### flavor

Check markup conventions.

### heading-line-length

Check the length of heading over/underlines.

### line-style

Find badly wrapped lines.

### long-line

Find long lines.

### style-add

Additional markup conventions.


## Natural

### abbreviation

Find abbreviations/acronyms without an explanation.
(It will not find explanations that are split by phrases like 'stands for'.)

### article

Indefinite article a or an.

### collocation

Search for space-separated versions of compounds like 'may be' vs. 'maybe'.

### grammar

Grammar linting.

### hyphen

Search for space-separated or joined versions of hyphened compounds like 'sub step' vs. 'substep' vs. 'sub-step'.

### metric

Measures the length of segments like paragraphs, sentences and words.

### overuse

Find repetitive word usage on a broad scale. Mainly to find repeated transitions (e.g. 'however').

### passive

Detect the use of passive voice.

### repeated

Repeated words inside a small range of words.


## Punctuation

### number

Number and unit formatting.

### pairs

Check pairs of parenthesis/brackets, quote marks for not being matched.

### mark

Check punctuation marks placing, spacing and usage of specific marks like ampersand.

### whitespace

Find multiple spaces in continuous text.


## Char

### char-search

Find specified chars and chars outside of the defined Unicode region.

### encoding

Check files for Unicode encoding for errors.

### EOF

Check blank lines at the end of the file.


## Capitalization

### admonition-title

Check the titlecase convention of the first line of admonitions.

### heading-caps

Check the title capitalization convention of headings.

### pos-case

Find uppercase part of speech types in continuous text (either a typo or missing sentence punctuation).

### property-noun

Find lowercase versions of majority uppercase words (usually a property name or name of a person).

### start-case

Find lowercase at the start of paragraphs, sentences and parenthesis.

### type

Find lowercase versions of a type.

### ui

Check capitalization of user interface labels in definition terms.


## Markup 2

### glossary

Unused glossary terms.

### link-titles

Finds (ref) links where the title mismatches the targeted heading title.

### local-targets

Searches for (ref) target used only on same page.

### page-name

Compares the page title with the file name.

### tool-title

Check if a heading matches the tool name in the admonition reference box.

### unused-targets

Searches for unused (ref) targets.


## Monitor

### monitor

Monitor files/directories for changes.


# Missing Tools

- present tense
- positive language: explain what to do instead of what not to.
