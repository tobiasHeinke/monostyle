
# Monostyle

[![PyPI version shields.io](https://img.shields.io/pypi/v/monostyle.svg)](https://pypi.python.org/pypi/monostyle/)
[![GPLv3 license](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://github.com/tobiasHeinke/monostyle/blob/master/LICENSE)

With Monostyle you can lint and style check your documentation covering all parts of a style guide.

Its tools are applied on new or changed content
which makes it fast and it allows a wider range of tools,
because they can have false positives.
For example exceptions to style guide rules that can't be filtered out.
Supported for version control are SVN and Git (experimental).

Monostyle is not a ready-made tool because its tools and data require customization.
For example you might not want to use Chicago style title case or
you might have different technical terms that are acceptable.
It includes its own RST parser and a port of the [Reflow line wrapper](https://metacpan.org/pod/Text::Reflow).
Its utilities can also be used for text editing with scripts.
Monostyle is customized for the [Blender manual](https://developer.blender.org/project/profile/53/).

Please refer to [Tools](/docs/tools.md) for a listing.


## Setup

Requirements: When using SVN the command line client tools need to be installed.

For spell checking a dictionary (aka lexicon) has to build.
On first run you have to confirm to start this (or also if the dictionary file is not found).

The dictionary has to be updated from time to time or after a new topic has been added
to include new words (of cause the whole project has to be spell-checked at this point).
To do this run the `update_lexicon` script:
```sh
python -m monostyle.update_lexicon
```

## Running Monostyle

Monostyle has four modes:

<dl>
   <dt>-i, --internal</dt>
   <dd>To check your own changes (the default).</dd>
   <dt>-e, --external</dt>
   <dd>
      To check changes made to the repository by others.
      Run this before you update your working copy with Git or SVN.
   </dd>
   <dt>-p, --patch</dt>
   <dd>To check changes in a patch-file.
      The directory from where Monostyle is run has to be same as
      where the patch-file was created.
   </dd>
   <dt>-f, --file</dt>
   <dd>To check a file or directory.
      Files can have a line selection at the end split with a colon and
      the span separated by a dash. For example `test.rst:10-25`.
      If the start or end are ommitted the start and end of the file are used accordingly.
   </dd>
</dl>

Options:

<dl>
   <dt>-r, --root</dt>
   <dd>
      The root is the absolute path to the top directory of your project.
      If not set the directory where Monostyle is run from is used.
   </dd>
   <dt>--cached, --staged</dt>
   <dd>Set the diff cached option (Git only).</dd>
   <dt>--unversioned, --untracked</dt>
   <dd>Include unversioned/untracked files.</dd>
   <dt>-s, --resolve</dt>
   <dd>Resolve link titles and substitutions
      (recommended only for file mode because it can take a few minutes
      and won't include newly created ones).
   </dd>
</dl>

Post processing:

<dl>
   <dt>-u, --update</dt>
   <dd>Update the working copy.</dd>
   <dt>-a, --autofix </dt>
   <dd>Apply autofixes. This also does an update if the changes are external.</dd>
   <dt>-o, --open</dt>
   <dd>Open the reported files in a text editor.
      Optionally only if the report has a severity higher than specified.
      Please check if your editor of choice is available (else please make a I/PR to add it).
   </dd>
</dl>

For more info on command line arguments use the `--help` command.
Individual tools can be selected by executing the modules.
By default the tools will then loop over the whole project.

Running Monostyle does not replace building the project with Sphinx.
Markup errors can lead to false negatives, so Monostyle has to be run again or
the affected section has to be checked manually.


### Advanced

You can set a commit/revision for internal, external and update (SVN only).
With Git these are passed unaltered to diff.
However, with SVN these can be colon separated or dash separated for the "change" syntax.
When a side is omitted e.g. ":ARG" it will default to BASE (your working copy) on the left and
on the right to HEAD (the latest revision in the repository).
For external revisions the "change" syntax is used for single arguments "ARG".


## Example Output

```
test.rst:
---------
1:20 ⚠️ 'static' repeated words 0 words in between
   Linter is a static static code analysis tool `source <https://en.wikipedia.org/wiki/Lint_(software)

2:9 ℹ️ 'flag' CS technical term
   en.wikipedia.org/wiki/Lint_(software)> `__¶used to flag programming errors, bugs, stylistic errors,

1:100 🛑 ' `__' space before body end of hyperlink
   ce <https://en.wikipedia.org/wiki/Lint_(software)> `__¶used to flag programming errors, bugs, styli
```
