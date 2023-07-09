COLLECTION = arensb.truenas
# Directory where generated HTML docs will go
DOCS_DIR = docs

RM = rm -rf

all::

# Build a tarball that can be uploaded as an Ansible collection.
tarball:	docs
	ansible-galaxy collection build --force

clean::
	${RM} arensb-truenas-*.tar.gz

# XXX - Ought to autogenerate this from `ls modules/plugins/*.py'
MODULES=\
	arensb.truenas.filesystem \
	arensb.truenas.group \
	arensb.truenas.jail \
	arensb.truenas.jails \
	arensb.truenas.mail \
	arensb.truenas.nfs \
	arensb.truenas.plugin \
	arensb.truenas.pool_snapshot_task \
	arensb.truenas.service \
	arensb.truenas.sharing_nfs \
	arensb.truenas.sharing_smb \
	arensb.truenas.systemdataset \
	arensb.truenas.user
# XXX - Need to create a directory 'ansible_collections/arensb' with
# symlink 'truenas' that points to the current directory.
check-docs:
	/usr/bin/env ANSIBLE_COLLECTIONS_PATHS=. \
	ansible-doc \
		-M .\
		--json \
		--type module \
		${MODULES}

docs:	venv-docs plugins/modules/*.py
	if [ ! -d "${DOCS_DIR}" ]; then \
	    install -m 0755 -d ${DOCS_DIR}; \
	fi
	venv-docs/bin/antsibull-docs sphinx-init \
	    --use-current \
	    --dest-dir ${DOCS_DIR} \
	    ${COLLECTION}
	(cd ${DOCS_DIR}; \
	    python3 -m venv venv; \
	    . venv/bin/activate; \
	    pip install -r ../extra-requirements.txt; \
	    pip install -r requirements.txt; \
	    ANSIBLE_COLLECTIONS_PATHS=.. ./build.sh; \
	)

clean::
	${RM} -r ${DOCS_DIR}

venv-docs:	requirements.txt
	python3 -m venv venv-docs
	venv-docs/bin/pip install -r requirements.txt

distclean::	clean
	${RM} docs-venv
