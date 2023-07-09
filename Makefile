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
ansible_collections/arensb/truenas:
	install -d -m 775 ansible_collections/arensb
	ln -s ../.. $@

docs:	venv-docs plugins/modules/*.py
	if [ ! -d "${DOCS_DIR}" ]; then \
	    install -m 0755 -d ${DOCS_DIR}; \
	fi
	venv-docs/bin/antsibull-docs sphinx-init \
	    --use-current \
	    --dest-dir ${DOCS_DIR} \
	    ${COLLECTION}
	(. venv-docs/bin/activate; \
	    cd ${DOCS_DIR}; \
	    pip install -r requirements.txt; \
	    ANSIBLE_COLLECTIONS_PATHS=.. ./build.sh; \
	)

clean::
	${RM} -r ${DOCS_DIR}

venv-docs:	requirements.txt
	python3 -m venv venv-docs
	venv-docs/bin/pip install -r requirements.txt

distclean::	clean
	${RM} venv-docs
