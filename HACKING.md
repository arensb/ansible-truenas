# Notes on hacking this collection

## Creating a new module

If you want to create a new module `foo`, start by copying the file
`extras/module-template` to `plugins/modules/foo.py`, then editing it.

Adapt `foo.py` to suit your purposes.

That template uses the generic term "resource" for the thing you're
managing. Change that to comething more descriptive: instead of
`resource_info`, use `user_info` in the user module, or `foo_info` in
the foo module, that sort of thing.

Be sure to fill in the `DOCUMENTATION`, `EXAMPLES`, and `RETURN`
strings. Documentation will be automatically generated from that,
using `make documentation`.

## Putting out a new release

1. Update `galaxy.yml` and update `version`.

1. Update `changelogs/changelog.yaml` and list changes the users care
about.

1. Run `antsibull-changelog lint` and `antsibull-changelog release`.

1. Commit changes.

1. Tag the git commit with the new release version, in the format
`v1.2.3`.

1. `git push`

1. `make tarball`. Upload the new tarball to Ansible Galaxy.

1. Toast!

## Documentation

`antsibull-docs` is used to create and populate the `docs` directory:

    antsibull-docs sphinx-init --use-current --dest-dir new-docs arensb.truenas

This creates the `docs/build.sh` script, which is used to generate
documentation: it uses `antsibull-docs collection` to convert Python
module files into RST files in `docs/`, and then `sphinx-build` to
convert those RST files into HTML.

The files generated by `sphinx-build` go in `docs/build/`. That
directory can safely be deleted. In fact, if you make major changes
(including deleting modules), it's probably a good idea to delete
`docs/build/` and rebuild the documentation.

The generated HTML files can then be copied to `docs-site/`, which is
just a git repository of the
[documentation website](https://arensb.github.io/truenas/index.html).
So to update the online documentation:

1. `make update-doc-site`
2. `cd docs-site`
3. `git add .; git checkin -m "Documentation update"; git push`