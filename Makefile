COLLECTION = arensb.truenas
# Directory where generated HTML docs will go
DOCS_DIR = docs

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

# XXX - Ought to autogenerate this from `ls modules/plugins/*.py'
MODULES=\
	${COLLECTION}.filesystem \
	${COLLECTION}.group \
	${COLLECTION}.jail \
	${COLLECTION}.jails \
	${COLLECTION}.mail \
	${COLLECTION}.nfs \
	${COLLECTION}.plugin \
	${COLLECTION}.pool_snapshot_task \
	${COLLECTION}.service \
	${COLLECTION}.sharing_nfs \
	${COLLECTION}.sharing_smb \
	${COLLECTION}.systemdataset \
	${COLLECTION}.user

check-docs:	ansible_collections/arensb/truenas
	/usr/bin/env ANSIBLE_COLLECTIONS_PATH=. \
	ansible-doc \
		-M .\
		--json \
		--type module \
		${MODULES}

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
		docs/build/html/ docs-site/truenas/
	echo "Don't forget to git push the docs site."
