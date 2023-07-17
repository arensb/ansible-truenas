COLLECTION = arensb.truenas
# Directory where generated HTML docs will go
DOCS_DIR = docs

# Root of the documentation web site repo.
#
# This can be either a relative or absolute path, and it may point to
# a subdirectory within a git repo: You might use /path/to/dir as the
# repo for an entire web site, and use /path/to/dir/truenas for that
# portion of the site that documents this collection. In this case you
# would use
# DOCS_SITE = /path/to/dir/truenas
DOCS_SITE = docs-site/truenas

RM = rm -rf

# See whether this is a dry run
ifneq (,$(findstring n,$(MAKEFLAGS)))
RSYNC_DRYRUN=-n
endif

all::

# Build a tarball that can be uploaded as an Ansible collection.
tarball:	docs
	ansible-galaxy collection build --force

clean::
	${RM} arensb-truenas-*.tar.gz

# Generate list of modules from plugins/modules/*.py:
# List the files, strip the directory name and .py suffix, then
# add the collection name in front, so
# plugins/modules/foo.py -> arensb.truenas.foo
MODULES = $(addprefix ${COLLECTION}., \
	$(basename \
	$(notdir \
	$(wildcard plugins/modules/*.py))))

check-docs:	ansible_collections/arensb/truenas
	/usr/bin/env ANSIBLE_COLLECTIONS_PATH=. \
	ansible-doc \
		-M .\
		--json \
		--type module \
		${MODULES} >/dev/null

# This is a crude hack: make a symlink to fool 'ansible-doc': it looks
# for module foo.bar.baz in
# $ANSIBLE_COLLECTIONS_PATH/ansible_collections/foo/bar/baz.py
compatibility-link:	ansible_collections/$(subst .,/,${COLLECTION})

ansible_collections/$(subst .,/,${COLLECTION}):
	install -d -m 775 `dirname "$@"`
	ln -s ../.. $@

documentation:	venv-docs compatibility-link plugins/modules/*.py
	(. venv-docs/bin/activate; \
	    cd ${DOCS_DIR}; \
	    pip install -r requirements.txt; \
	    ANSIBLE_COLLECTIONS_PATHS=.. ./build.sh; \
	)

venv-docs:	requirements.txt
	python3 -m venv venv-docs
	venv-docs/bin/pip install -r requirements.txt

clean::
	${RM} -r ${DOCS_DIR}/build/
	${RM} -r ${DOCS_DIR}/temp-rst/
	${RM} -r ${DOCS_DIR}/rst/

distclean::	clean
	${RM} venv-docs

# Copy the generated docs to the docs website repository.
update-doc-site:	documentation
	+rsync ${RSYNC_DRYRUN} \
		 -avi \
		--delete \
		docs/build/html/ ${DOCS_SITE}/
	(cd ${DOCS_SITE}; \
	 git add . ; \
	 git commit -m "Automatic update."; \
	)
	echo "Don't forget to git push the docs site."
