
# Monostyle

[![PyPI version shields.io](https://img.shields.io/pypi/v/monostyle.svg)](https://pypi.python.org/pypi/monostyle/)
[![GPLv3 license](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://github.com/tobiasHeinke/monostyle/blob/master/LICENSE)

With Monostyle you can lint and style check your documentation covering all parts of a style guide.

Its tools are applied on new or changed content
which makes it fast and it allows a wider range of tools,
because they can have false positives. 
For example style guide rules that have exceptions which can't be filtered out.
Supported for versioning are SVN and Git (experimental).

Monostyle is build as a framework and not as a ready-made tool
because the tools and data require customization.
For example you might not want to use Chicago style title case or you might have different technical terms that are acceptable.
It includes its own RST parser and a port of the [Reflow line wrapper](https://metacpan.org/pod/Text::Reflow).
Its utilities can also be used for text editing with scripts.
Monostyle is customized for the [Blender manual](https://developer.blender.org/project/profile/53/).

Please refer to [Tools](/docs/tools.md) for a listing.


## Setup

Requirements: When using SVN the command line client tools need to be installed.

For spell checking a dictionary has to build.
On first run you have to confirm to start this (or also if the dictionary file is not found).

The dictionary has to be updated from time to time or after a new topic has been added
to include new words (of cause the whole project has to be spell-checked at this point).
To do this run the `spelling` script:
```sh
python -m monostyle.spelling
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
  <dd>To check changes in a patch-file.</dd>
  <dt>-f, --file</dt>
  <dd>To check a file or directory.</dd>
  <dt>-r, --root</dt>
  <dd>
      The root is the absolute path to the project directory or where the patch file was created.
      If not set the directory where Monostyle is run from is used as the root.
  </dd>
  <dt>--cached, --staged</dt>
  <dd>
      Set the diff cached option (Git only).
  </dd>
</dl>

Post processing:

<dl>
  <dt>-u, --update</dt>
  <dd>Update the working copy.</dd>
  <dt>-a, --autofix </dt>
  <dd>Apply autofixes. This also does an update if the changes are external.</dd>
  <dt>-o, --open</dt>
  <dd>Open a file in a text editor if the report has a severity higher than specified.
      Please check if your editor of choice is available (else please make a I/PR to add it).
  </dd>
</dl>

For more info on command line arguments use the `--help` command.
The tools can be applied individually by executing the script files. Then the tools will loop over the whole project.

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
