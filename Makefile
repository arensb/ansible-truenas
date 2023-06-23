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
docs:
	/usr/bin/env ANSIBLE_COLLECTIONS_PATHS=. \
	ansible-doc \
		-M .\
		--json \
		--type module \
		${MODULES}
