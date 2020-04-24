
# Monostyle

Monostyle is a framework for style checking and linting covering all parts of a style guide.

Its tools are applied on new or changed content
which makes it fast and it allows a wider range of tools,
because they can have false positives. 
For example style guide rules that have exceptions which can't be filtered away.

Monostyle is build as a framework and not as a ready-made tool
because the tools require customization like markup filtering or you might not want to use Chicago style title case. 
It includes its own RST parser and a port of the [Reflow line wrapper](https://metacpan.org/pod/Text::Reflow).
Its utilities can also be used for text editing with scripts.


## Setup

Requirements: The SVN command line client tools need to be installed.

For the spell-checking a dictionary has to build.
On first run you have to confirm to start this (or also if the dictionary file is not found).

The dictionary has to be updated from time to time or after a bigger portion of content has been added
to include the new words (of cause the whole project has to be spell-checked).
To do this run the `spelling.py` script:
```sh
python spelling.py
```

## Running Monostyle

Monostyle has four modes:

<dl>
  <dt>internal -i</dt>
  <dd>To check your own changes.</dd>
  <dt>external -e</dt>
  <dd>
      To check changes by others made to the repository.
      Run this before you update your repository with SVN.
   </dd>
  <dt>patch -p</dt>
  <dd>To check changes in a patch-file.</dd>
  <dt>file -f</dt>
  <dd>To check whole files/directories.</dd>
  <dt>root -r</dt>
  <dd>
      The root is (absolute) path to where the diff is/was created usually the local project directory.
      If not set the directory where Monostyle is run from is used as a root.
      Leave it empty to use the root from the configuration or specify a path.
  </dd>
</dl>

Post processing:

<dl>
  <dt>update -u</dt>
  <dd>Update the local copy.</dd>
  <dt>autofix -a</dt>
  <dd>Apply autofixes. This also does an update if the changes are from external.</dd>
  <dt>open -o</dt>
  <dd>Open a file in a text editor if the report has a severity higher than specified.</dd>
</dl>

For more info on command line arguments use the `--help` command.
The tools can be applied individually by executing the script files. Then the tools will loop over the whole project.
Running Monostyle doesn't replaces building the project with Sphinx.
Markup errors can lead to false negatives, so Monostyle has to be run again or
the section has to be checked manually.


### Advanced

You can set a revision for internal, external and update.
It can be colon separated or dash separated for the "change" syntax.
When a side is kept empty e.g. ":ARG" it will default to BASE (your local copy) on the left and
on the right to HEAD (the latest revision in the repository).
External revision uses the "change" syntax for single arguments "ARG".
